from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.live_search_validation_invocation_runtime import (
    AG_LIVE_XAXIS_SEARCH_PROFILE,
    AG_LIVE_XAXIS_SEARCH_REQUEST_KIND,
    LiveSearchValidationCaps,
    LiveSearchValidationInvocationError,
    build_live_search_validation_request_packet,
    execution_facts_for_mode,
    normalize_provider_result,
    normalize_provider_results_by_task,
    reduce_provider_results_through_run_kernel,
    validate_cap_policy,
    validate_provider_authorized,
    validate_safe_output_packet_path,
)
from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE,
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
)
from tests import test_ag_live_xaxis_validation_01a as pr1

ROOT = Path(__file__).resolve().parents[1]
INVOCATION_RUNTIME = ROOT / "core" / "live_search_validation_invocation_runtime.py"
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


def _ready_kernel():
    return pr1._ready_kernel()


def _request_packet(kernel, *, provider: str = "serper") -> dict[str, Any]:
    return build_live_search_validation_request_packet(
        current_answer_contract=kernel.state.current_answer_contract,
        search_executor_handoff_state=kernel.state.search_executor_handoff_state,
        selected_search_task_ids=pr1._selected_task_ids(kernel),
        provider_authorized=provider,
        output_packet_path=ROOT / "output" / "ag_live_xaxis_pr2_packet.json",
        root=ROOT,
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
    )


def _provider_results(kernel) -> dict[str, list[dict[str, Any]]]:
    task_id = pr1._selected_task_ids(kernel)[0]
    return {
        task_id: [
            {
                "title": "Official Example Search Result",
                "url": "https://official.example.gov/current/result",
                "domain": "official.example.gov",
                "snippet": "Official current result candidate.",
                "date": "2026-01-01",
                "rank": 1,
                "call_index": 1,
            }
        ]
    }


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


def test_request_schema_binds_current_contract_and_handoff_refs() -> None:
    kernel = _ready_kernel()

    packet = _request_packet(kernel)

    assert packet["request_kind"] == AG_LIVE_XAXIS_SEARCH_REQUEST_KIND
    assert packet["profile"] == AG_LIVE_XAXIS_SEARCH_PROFILE
    assert packet["current_answer_contract_ref"]["contract_digest"] == (
        kernel.state.current_answer_contract["accepted_contract_digest"]
    )
    assert packet["search_executor_handoff_ref"]["handoff_digest"] == (
        kernel.state.search_executor_handoff_state["handoff_digest"]
    )
    assert packet["selected_search_task_ids"] == pr1._selected_task_ids(kernel)
    assert packet["confirm_live_provider_call_required"] is True


def test_request_schema_copies_selected_task_refs_without_raw_private_fields() -> None:
    kernel = _ready_kernel()
    handoff = dict(kernel.state.search_executor_handoff_state)
    task = dict(handoff["search_task_records"][0])
    task.update(
        {
            "raw_provider_payload": {"private": True},
            "auth_header": "Bearer private",
            "full_trace": "private",
        }
    )
    handoff["search_task_records"] = [task]

    packet = build_live_search_validation_request_packet(
        current_answer_contract=kernel.state.current_answer_contract,
        search_executor_handoff_state=handoff,
        selected_search_task_ids=[task["search_task_id"]],
        provider_authorized="serper",
        output_packet_path=ROOT / "output" / "ag_live_xaxis_pr2_packet.json",
        root=ROOT,
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
    )

    selected_ref = packet["selected_search_task_refs"][0]
    assert selected_ref["search_task_id"] == task["search_task_id"]
    assert "provider_preference_hint" in selected_ref
    assert _all_keys(selected_ref).isdisjoint(
        {"raw_provider_payload", "auth_header", "full_trace"}
    )


def test_provider_authorized_required_even_when_provider_preference_hint_exists() -> None:
    kernel = _ready_kernel()
    task = kernel.state.search_executor_handoff_state["search_task_records"][0]
    assert task["provider_preference_hint"] == "serper"

    with pytest.raises(
        LiveSearchValidationInvocationError,
        match="provider_authorized",
    ):
        _request_packet(kernel, provider="")


def test_provider_preference_hint_mismatch_does_not_override_authorized_provider() -> None:
    kernel = _ready_kernel()

    packet = _request_packet(kernel, provider="brave")

    assert packet["provider_authorized"] == "brave"
    assert packet["selected_search_task_refs"][0]["provider_preference_hint"] == "serper"


def test_provider_allowlist_rejects_unknown_provider() -> None:
    with pytest.raises(LiveSearchValidationInvocationError, match="allowlisted"):
        validate_provider_authorized("unknown")


def test_cap_policy_rejects_provider_calls_above_cap() -> None:
    with pytest.raises(LiveSearchValidationInvocationError, match="provider_call_cap"):
        LiveSearchValidationCaps(provider_call_cap=2).to_payload()


def test_cap_policy_rejects_results_per_task_above_cap() -> None:
    with pytest.raises(LiveSearchValidationInvocationError, match="results_per_task"):
        LiveSearchValidationCaps(results_per_task_cap=3).to_payload()


def test_non_search_caps_must_be_zero() -> None:
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
        caps = LiveSearchValidationCaps().to_payload()
        caps[key] = 1
        with pytest.raises(LiveSearchValidationInvocationError, match=key):
            validate_cap_policy(caps)


def test_safe_output_path_must_stay_under_output(tmp_path: Path) -> None:
    output_path = tmp_path / "output" / "packet.json"

    assert validate_safe_output_packet_path(output_path, root=tmp_path) == output_path

    for raw_path in (
        tmp_path / "not-output" / "packet.json",
        "output/../packet.json",
    ):
        with pytest.raises(LiveSearchValidationInvocationError, match="output"):
            validate_safe_output_packet_path(raw_path, root=tmp_path)


def test_normalizer_accepts_only_sanitized_result_fields() -> None:
    normalized = normalize_provider_result(
        {
            "title": "Official Result",
            "url": "https://official.example.gov/result",
            "domain": "official.example.gov",
            "snippet": "bounded snippet",
            "date": "2026-01-01",
            "rank": 1,
            "call_index": 1,
        }
    )

    assert normalized == {
        "title": "Official Result",
        "url": "https://official.example.gov/result",
        "domain": "official.example.gov",
        "snippet": "bounded snippet",
        "published_or_observed_date": "2026-01-01",
        "result_rank": 1,
        "provider_call_index": 1,
    }


def test_normalizer_rejects_raw_private_or_unknown_result_fields() -> None:
    for forbidden in (
        "raw_provider_payload",
        "raw_search_response",
        "raw_content",
        "auth",
        "log",
        "prompt",
        "full_trace",
    ):
        payload = {
            "title": "Official Result",
            "url": "https://official.example.gov/result",
            forbidden: "private",
        }
        with pytest.raises(LiveSearchValidationInvocationError):
            normalize_provider_result(payload)


def test_broker_request_wrapper_is_inert_without_confirmation(monkeypatch, capsys) -> None:
    kernel = _ready_kernel()
    packet = _request_packet(kernel)
    from scripts import request_live_search_validation_broker as broker_script

    monkeypatch.setattr(broker_script, "_load_request_packet", lambda _path: packet)

    assert broker_script.main(["--request", "output/request.json"]) == 2
    captured = capsys.readouterr()
    assert "--confirm-live-provider-call" in captured.err


def test_direct_runner_is_offline_dry_run_without_confirmation(
    monkeypatch,
    capsys,
) -> None:
    kernel = _ready_kernel()
    packet = _request_packet(kernel)
    from scripts import ag_live_xaxis_validation_01a_search_runner as runner

    monkeypatch.setattr(runner, "_load_request_packet", lambda _path: packet)

    assert runner.main(["--request", "output/request.json"]) == 0
    captured = capsys.readouterr()
    assert "direct_runner_dry_run_no_live_provider_call" in captured.out
    assert '"live_provider_called": false' in captured.out


def test_fake_broker_response_normalizes_and_reduces_through_run_kernel() -> None:
    kernel = _ready_kernel()
    request = _request_packet(kernel)
    facts = execution_facts_for_mode(LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE)

    packet = reduce_provider_results_through_run_kernel(
        kernel=kernel,
        request_packet=request,
        provider_results_by_task=_provider_results(kernel),
        root=ROOT,
        **facts,
    )

    state = kernel.state.live_search_validation_state
    assert state["execution_mode"] == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE
    assert state["broker_invoked"] is True
    assert state["live_provider_called"] is True
    assert state["candidate_count"] == 1
    assert packet["candidate_count"] == 1
    assert packet["broker_invoked"] is True
    assert packet["live_provider_called"] is True


def test_fake_direct_response_normalizes_and_reduces_through_run_kernel() -> None:
    kernel = _ready_kernel()
    request = _request_packet(kernel)
    facts = execution_facts_for_mode(LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE)

    packet = reduce_provider_results_through_run_kernel(
        kernel=kernel,
        request_packet=request,
        provider_results_by_task=_provider_results(kernel),
        root=ROOT,
        **facts,
    )

    state = kernel.state.live_search_validation_state
    assert state["execution_mode"] == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE
    assert state["broker_invoked"] is False
    assert state["live_provider_called"] is True
    assert packet["execution_mode"] == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE


def test_pr1_offline_fake_expectations_still_hold() -> None:
    kernel = _ready_kernel()

    pr1._reduce_validation(kernel)

    state = kernel.state.live_search_validation_state
    assert state["execution_mode"] == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE
    assert state["broker_invoked"] is False
    assert state["live_provider_called"] is False
    assert state["not_live_executed_by_pr1"] is True
    assert state["fake_provider_used"] is True


def test_execution_facts_are_not_downstream_closed_surface_flags() -> None:
    kernel = _ready_kernel()
    request = _request_packet(kernel)
    facts = execution_facts_for_mode(LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE)

    reduce_provider_results_through_run_kernel(
        kernel=kernel,
        request_packet=request,
        provider_results_by_task=_provider_results(kernel),
        root=ROOT,
        **facts,
    )

    flags = kernel.state.live_search_validation_state["closed_surface_flags"]
    assert "broker_invoked" not in flags
    assert "live_provider_called" not in flags
    assert kernel.state.live_search_validation_state["broker_invoked"] is True
    assert kernel.state.live_search_validation_state["live_provider_called"] is True


def test_downstream_closed_surface_flags_remain_false_in_all_modes() -> None:
    kernel = _ready_kernel()
    pr1._reduce_validation(kernel)
    offline_state = kernel.state.live_search_validation_state

    for mode in (
        LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
        LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE,
        LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
    ):
        mode_kernel = _ready_kernel()
        if mode == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE:
            state = offline_state
        else:
            reduce_provider_results_through_run_kernel(
                kernel=mode_kernel,
                request_packet=_request_packet(mode_kernel),
                provider_results_by_task=_provider_results(mode_kernel),
                root=ROOT,
                **execution_facts_for_mode(mode),
            )
            state = mode_kernel.state.live_search_validation_state
        for key, expected in DOWNSTREAM_FALSE_FLAGS.items():
            assert state[key] is expected
            assert state["closed_surface_flags"][key] is expected


def test_invocation_runtime_has_no_env_secret_or_network_imports() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "urllib.request",
    }
    imported = _imports(INVOCATION_RUNTIME)
    assert imported.isdisjoint(forbidden_imports)
    source = INVOCATION_RUNTIME.read_text(encoding="utf-8")
    for token in (
        "load_dotenv",
        "dotenv_values",
        "SERPER_API_KEY",
        "BRAVE_API_KEY",
        "requests.",
        "httpx.",
        "openai.",
        "urlopen(",
        "core.pipeline_orchestrator",
    ):
        assert token not in source, token


def test_pipeline_orchestrator_line_delta_remains_zero() -> None:
    diff = subprocess.run(
        ["git", "diff", "--numstat", "--", str(PIPELINE.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert diff.stdout.strip() == ""


def test_result_count_above_request_cap_is_rejected() -> None:
    kernel = _ready_kernel()
    request = _request_packet(kernel)
    task_id = pr1._selected_task_ids(kernel)[0]

    with pytest.raises(LiveSearchValidationInvocationError, match="results_per_task"):
        normalize_provider_results_by_task(
            request_packet=request,
            provider_results_by_task={
                task_id: [
                    {
                        "title": "One",
                        "url": "https://official.example.gov/one",
                    },
                    {
                        "title": "Two",
                        "url": "https://official.example.gov/two",
                    },
                    {
                        "title": "Three",
                        "url": "https://official.example.gov/three",
                    },
                ]
            },
            root=ROOT,
        )


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
