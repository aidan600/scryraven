from __future__ import annotations

import ast
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.live_search_validation_invocation_runtime import (
    LiveSearchValidationInvocationError,
    build_live_search_validation_request_packet,
    reduce_provider_results_through_run_kernel,
)
from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
)
from scripts import ag_live_xaxis_validation_01a_live_run_01_harness as harness

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "ag_live_xaxis_validation_01a_live_run_01_harness.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"

DOWNSTREAM_FALSE_FLAGS = {
    "fetch_read_executed": False,
    "fetch_read_retrieval_executed": False,
    "evidence_ledger_admitted": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
}


def _output_path(name: str) -> Path:
    return ROOT / "output" / name


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _prepared_request(name: str = "ag_live_xaxis_live_run_01_test_request.json") -> dict[str, Any]:
    return harness.prepare_request_packet(output_path=_output_path(name))


def _selected_task_id(request: Mapping[str, Any]) -> str:
    return request["selected_search_task_ids"][0]


def _candidate_result() -> dict[str, Any]:
    return {
        "title": "Passport Fees",
        "url": "https://travel.state.gov/content/travel/en/passports/how-apply/fees.html",
        "domain": "travel.state.gov",
        "snippet": "Official passport fee information.",
        "date": "2026-06-01",
        "rank": 1,
        "call_index": 1,
    }


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()


def test_prepare_request_writes_sanitized_packet_under_output() -> None:
    output = _output_path("ag_live_xaxis_live_run_01_prepare_request.json")

    packet = harness.prepare_request_packet(output_path=output)

    assert output.exists()
    assert _read_json(output) == packet
    assert packet["request_kind"] == "ag_live_xaxis_search_validation"
    assert packet["output_packet_path"].startswith("output")
    assert _all_keys(packet).isdisjoint(
        {"raw_provider_payload", "raw_search_response", "raw_content", "auth"}
    )


def test_prepared_request_binds_current_contract_handoff_and_one_task() -> None:
    packet = _prepared_request("ag_live_xaxis_live_run_01_refs.json")

    assert packet["current_answer_contract_ref"]["source"] == "current_answer_contract"
    assert packet["current_answer_contract_ref"]["contract_digest"]
    assert packet["search_executor_handoff_ref"]["handoff_digest"]
    assert len(packet["selected_search_task_ids"]) == 1
    assert len(packet["selected_search_task_refs"]) == 1


def test_provider_default_caps_and_hint_non_authority() -> None:
    packet = _prepared_request("ag_live_xaxis_live_run_01_caps.json")

    assert packet["provider_authorized"] == "serper"
    assert packet["selected_search_task_refs"][0]["provider_preference_hint"] == "serper"
    assert packet["provider_preference_hint_authority"] == "diagnostic_only"
    assert packet["provider_call_cap"] == 1
    assert packet["results_per_task_cap"] == 2
    for key in (
        "retry_cap",
        "fetch_read_cap",
        "retrieval_cap",
        "evidence_ledger_admission_cap",
        "citation_eligibility_cap",
        "sufficiency_cap",
        "final_answer_packet_cap",
        "author_cap",
    ):
        assert packet[key] == 0


def test_output_path_outside_output_is_rejected() -> None:
    with pytest.raises(LiveSearchValidationInvocationError, match="output"):
        harness.prepare_request_packet(output_path=ROOT / "not-output" / "request.json")


def test_broker_envelope_emission_is_file_only() -> None:
    request_path = _output_path("ag_live_xaxis_live_run_01_envelope_request.json")
    envelope_path = _output_path("ag_live_xaxis_live_run_01_broker_envelope.json")
    request = harness.prepare_request_packet(output_path=request_path)

    envelope = harness.emit_broker_envelope(
        request_path=request_path,
        output_path=envelope_path,
        confirm_live_provider_call=True,
    )

    assert envelope_path.exists()
    assert envelope["broker_request"] == request
    assert envelope["confirm_live_provider_call"] is True


def test_broker_envelope_requires_confirmation() -> None:
    request_path = _output_path("ag_live_xaxis_live_run_01_envelope_confirm_request.json")
    harness.prepare_request_packet(output_path=request_path)

    with pytest.raises(harness.HarnessError, match="confirm-live-provider-call"):
        harness.emit_broker_envelope(
            request_path=request_path,
            output_path=_output_path("ag_live_xaxis_live_run_01_no_confirm.json"),
            confirm_live_provider_call=False,
        )


def test_sanitized_provider_result_reduces_to_one_candidate() -> None:
    request_path = _output_path("ag_live_xaxis_live_run_01_reduce_request.json")
    output_path = _output_path("ag_live_xaxis_live_run_01_output_packet.json")
    request = harness.prepare_request_packet(output_path=request_path)
    results_path = _write_json(
        _output_path("ag_live_xaxis_live_run_01_results_one.json"),
        {_selected_task_id(request): [_candidate_result()]},
    )

    packet = harness.reduce_sanitized_results(
        request_path=request_path,
        provider_results_path=results_path,
        output_path=output_path,
    )

    assert output_path.exists()
    assert packet["candidate_count"] == 1
    assert packet["provider_calls_attempted"] == 1
    assert packet["provider_calls_completed"] == 1
    assert packet["live_provider_called"] is True
    assert packet["broker_invoked"] is False


def test_empty_selected_result_list_reduces_to_zero_candidates() -> None:
    request_path = _output_path("ag_live_xaxis_live_run_01_reduce_empty_request.json")
    output_path = _output_path("ag_live_xaxis_live_run_01_output_empty.json")
    request = harness.prepare_request_packet(output_path=request_path)
    results_path = _write_json(
        _output_path("ag_live_xaxis_live_run_01_results_empty.json"),
        {_selected_task_id(request): []},
    )

    packet = harness.reduce_sanitized_results(
        request_path=request_path,
        provider_results_path=results_path,
        output_path=output_path,
    )

    assert packet["candidate_count"] == 0
    assert packet["search_result_candidates"] == []
    assert packet["provider_calls_attempted"] == 1
    assert packet["provider_calls_completed"] == 1


def test_missing_selected_task_id_fails_closed() -> None:
    request_path = _output_path("ag_live_xaxis_live_run_01_missing_request.json")
    harness.prepare_request_packet(output_path=request_path)
    results_path = _write_json(
        _output_path("ag_live_xaxis_live_run_01_missing_results.json"),
        {},
    )

    with pytest.raises(LiveSearchValidationInvocationError, match="missing selected"):
        harness.reduce_sanitized_results(
            request_path=request_path,
            provider_results_path=results_path,
            output_path=_output_path("ag_live_xaxis_live_run_01_missing_output.json"),
        )


def test_extra_unselected_task_id_fails_closed() -> None:
    request_path = _output_path("ag_live_xaxis_live_run_01_extra_request.json")
    request = harness.prepare_request_packet(output_path=request_path)
    results_path = _write_json(
        _output_path("ag_live_xaxis_live_run_01_extra_results.json"),
        {
            _selected_task_id(request): [],
            "search-task:extra": [],
        },
    )

    with pytest.raises(LiveSearchValidationInvocationError, match="unselected"):
        harness.reduce_sanitized_results(
            request_path=request_path,
            provider_results_path=results_path,
            output_path=_output_path("ag_live_xaxis_live_run_01_extra_output.json"),
        )


def test_raw_or_private_provider_result_fields_are_rejected() -> None:
    request_path = _output_path("ag_live_xaxis_live_run_01_raw_request.json")
    request = harness.prepare_request_packet(output_path=request_path)
    for forbidden in (
        "raw_provider_payload",
        "raw_search_response",
        "raw_content",
        "auth",
        "log",
        "prompt",
        "full_trace",
    ):
        payload = _candidate_result()
        payload[forbidden] = "private"
        results_path = _write_json(
            _output_path(f"ag_live_xaxis_live_run_01_raw_{forbidden}.json"),
            {_selected_task_id(request): [payload]},
        )
        with pytest.raises(LiveSearchValidationInvocationError):
            harness.reduce_sanitized_results(
                request_path=request_path,
                provider_results_path=results_path,
                output_path=_output_path(f"ag_live_xaxis_live_run_01_raw_{forbidden}_out.json"),
            )


def test_downstream_and_retention_flags_remain_false() -> None:
    request_path = _output_path("ag_live_xaxis_live_run_01_flags_request.json")
    request = harness.prepare_request_packet(output_path=request_path)
    results_path = _write_json(
        _output_path("ag_live_xaxis_live_run_01_flags_results.json"),
        {_selected_task_id(request): [_candidate_result()]},
    )

    packet = harness.reduce_sanitized_results(
        request_path=request_path,
        provider_results_path=results_path,
        output_path=_output_path("ag_live_xaxis_live_run_01_flags_output.json"),
    )

    for key, expected in DOWNSTREAM_FALSE_FLAGS.items():
        assert packet[key] is expected
    assert packet["raw_provider_payload_retained"] is False
    assert packet["raw_search_response_retained"] is False


def test_closed_runtime_state_surfaces_do_not_change() -> None:
    kernel = harness.build_front_half_kernel()
    request = build_live_search_validation_request_packet(
        current_answer_contract=kernel.state.current_answer_contract,
        search_executor_handoff_state=kernel.state.search_executor_handoff_state,
        selected_search_task_ids=[
            kernel.state.search_executor_handoff_state["search_task_records"][0][
                "search_task_id"
            ]
        ],
        provider_authorized="serper",
        output_packet_path=_output_path("ag_live_xaxis_live_run_01_state_request.json"),
        root=ROOT,
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
    )
    task_id = request["selected_search_task_ids"][0]
    evidence_before = deepcopy(kernel.state.evidence_ledger.to_projection().to_dict())
    citation_before = deepcopy(kernel.state.followup_citation_eligibility_history)
    sufficiency_before = deepcopy(kernel.state.sufficiency_judgment)
    fap_before = deepcopy(kernel.state.final_answer_packet)
    author_before = deepcopy(kernel.state.author_observation)

    reduce_provider_results_through_run_kernel(
        kernel=kernel,
        request_packet=request,
        provider_results_by_task={task_id: [_candidate_result()]},
        root=ROOT,
        execution_mode=LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
        broker_invoked=False,
        live_provider_called=True,
    )

    assert kernel.state.evidence_ledger.to_projection().to_dict() == evidence_before
    assert kernel.state.followup_citation_eligibility_history == citation_before
    assert kernel.state.sufficiency_judgment == sufficiency_before
    assert kernel.state.final_answer_packet == fap_before
    assert kernel.state.author_observation == author_before


def test_harness_has_no_secret_network_or_provider_transport_imports() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "urllib.request",
    }
    assert _imports(HARNESS).isdisjoint(forbidden_imports)
    source = HARNESS.read_text(encoding="utf-8")
    for token in (
        "SERPER_API_KEY",
        "BRAVE_API_KEY",
        "load_dotenv",
        "requests.",
        "httpx.",
        "openai.",
        "urlopen(",
        "search_scout_results(",
        "brave_reconnaissance(",
    ):
        assert token not in source


def test_pipeline_orchestrator_line_delta_remains_zero() -> None:
    diff = subprocess.run(
        ["git", "diff", "--numstat", "--", str(PIPELINE.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert diff.stdout.strip() == ""
