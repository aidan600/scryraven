from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.run_kernel import RunKernel
from scripts import ag_live_semantic_support_coverage_01 as semantic_harness
from scripts import ag_live_semantic_support_runkernel_handoff_repair_01 as repair
from scripts import ag_live_source_survival_fetch_read_custody_01 as source_harness
from tests.test_ag_live_source_survival_fetch_read_custody_01 import (
    FakeFetcher,
    _fake_fetch_result,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ag_live_semantic_support_runkernel_handoff_repair_01.py"
DOC = (
    ROOT
    / "docs"
    / "architecture"
    / "AG_LIVE_SEMANTIC_SUPPORT_RUNKERNEL_HANDOFF_REPAIR_01.md"
)

SUPPORT_TEXT = (
    "Passport Fees Travel.gov. Adult applicants age 16 and older who use DS-82 "
    "renewal for a U.S. passport book pay the passport book fee $130. This "
    "bounded sanitized source region is only for the component under test."
)


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _provider_results_path(name: str) -> Path:
    return (
        ROOT
        / "output"
        / "ag_limited_live_search_candidate_01"
        / f"runkernel-handoff-{name}"
        / "sanitized_provider_results.json"
    )


def _output_dir(name: str) -> Path:
    return repair.DEFAULT_OUTPUT_DIR / name


def _source_output_dir(name: str) -> Path:
    return (
        source_harness.DEFAULT_OUTPUT_DIR
        / f"runkernel-handoff-source-{name}"
    )


def _provider_results(name: str) -> Path:
    return _write_json(
        _provider_results_path(name),
        {
            "schema_version": "2",
            "proof_kind": "scryraven_search_query_proof_v2",
            "provider": "serper",
            "operation": "search.query",
            "status": "ok",
            "result_count": 1,
            "results": [
                {
                    "title": "Passport Fees - Travel.gov - State Department",
                    "url": "https://travel.state.gov/en/passports/apply/help/fees.html",
                    "domain": "travel.state.gov",
                    "snippet": "Official passport book renewal fee information.",
                    "published_or_observed_date": "Mar 19, 2026",
                    "result_rank": 1,
                    "provider_call_index": 1,
                }
            ],
            "physical_attempt_count": 1,
            "provider_elapsed_milliseconds_total": 5,
            "caller_authorized_cost_ceiling_usd": "0.05",
            "raw_provider_payload_retained": False,
            "raw_request_material_retained": False,
            "raw_response_material_retained": False,
            "raw_search_response_retained": False,
        },
    )


def _candidate_handoff(name: str) -> Any:
    return repair.candidate_harness.reduce_existing_sanitized_provider_results_in_process(
        query=repair.candidate_harness.DEFAULT_QUERY,
        provider_results_path=_provider_results(name),
        output_dir=repair.candidate_harness.DEFAULT_OUTPUT_DIR
        / f"runkernel-handoff-{name}",
    )


def _source_handoff(name: str, candidate_handoff: Any) -> Any:
    return source_harness.fetch_read_custody_in_process(
        candidate_handoff=candidate_handoff,
        output_dir=_source_output_dir(name),
        confirm_fetch_read=True,
        fetcher=FakeFetcher(_fake_fetch_result(text=SUPPORT_TEXT)),
    )


def _run_repair(name: str) -> dict[str, Any]:
    return repair.verify_live_runkernel_handoff(
        sanitized_provider_results_path=_provider_results(name),
        output_dir=_output_dir(name),
        confirm_fetch_read_runkernel_handoff=True,
        fetcher=FakeFetcher(_fake_fetch_result(text=SUPPORT_TEXT)),
    )


def _imports_calls_assignments(path: Path) -> tuple[set[str], set[str], list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
        elif isinstance(node, ast.Assign):
            targets.extend(ast.unparse(target) for target in node.targets)
    return imported, called, targets


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


def test_in_process_replay_starts_from_sanitized_records_and_preserves_runkernel() -> None:
    handoff = _candidate_handoff("candidate")

    assert isinstance(handoff.run_kernel, RunKernel)
    assert handoff.candidate_packet["candidate_count"] == 1
    assert handoff.validation_packet["provider_search_calls_performed_by_replay"] == 0
    assert handoff.validation_packet["broker_calls_performed_by_replay"] == 0
    assert handoff.validation_packet["runkernel_preserved_for_handoff"] is True
    assert handoff.provider_results_ref["result_count"] == 1
    assert handoff.run_kernel.state.live_search_validation_state


def test_candidate_packet_json_is_cross_check_only_not_state_source() -> None:
    handoff = _candidate_handoff("cross-check")
    cross_dir = _provider_results_path("cross-check").parent
    candidate_path = _write_json(
        cross_dir / "search_result_candidate_packet.json",
        handoff.candidate_packet,
    )
    validation_path = _write_json(
        cross_dir / "validation_packet.json",
        handoff.validation_packet,
    )

    packet = repair.verify_live_runkernel_handoff(
        sanitized_provider_results_path=_provider_results_path("cross-check"),
        candidate_packet_cross_check_path=candidate_path,
        validation_packet_cross_check_path=validation_path,
        output_dir=_output_dir("cross-check"),
        confirm_fetch_read_runkernel_handoff=True,
        fetcher=FakeFetcher(_fake_fetch_result(text=SUPPORT_TEXT)),
    )

    assert packet["candidate_packet_json_used_only_as_cross_check_not_state_source"] is True
    assert packet["serialized_candidate_packet_used_as_state_source"] is False
    assert packet["optional_cross_check_inputs"]["candidate_packet"][
        "used_as_runkernel_state_source"
    ] is False


def test_source_survival_handoff_keeps_same_runkernel_through_evidence_ledger() -> None:
    candidate = _candidate_handoff("source")
    source = _source_handoff("source", candidate)

    assert source.run_kernel is candidate.run_kernel
    assert source.source_survival_packet["selected_source_survived"] == "source_survival_pass"
    assert source.evidence_ledger_projection["fetch_read_candidate_custody"][
        "custody_record_count"
    ] == 1
    assert source.run_kernel.state.evidence_ledger.to_projection().to_dict()[
        "fetch_read_candidate_custody"
    ]["custody_record_count"] == 1


def test_handoff_objects_are_not_serialized_or_projection_rehydrated() -> None:
    packet = _run_repair("serialization")

    assert packet["handoff_objects_serialized"] is False
    assert packet["projection_rehydration_avoided"] is True
    assert "run_kernel" not in _all_keys(packet)
    assert "RunKernel(" not in json.dumps(packet, sort_keys=True)


def test_no_direct_runkernel_state_assignments_are_used() -> None:
    _imported, called, targets = _imports_calls_assignments(SCRIPT)
    forbidden_targets = (
        ".state.semantic_observation_admission",
        ".state.component_coverage",
        ".state.evidence_ledger",
        ".state.current_answer_contract",
        ".state.initial_answer_contract",
    )
    forbidden_calls = {"asdict"}

    assert called.isdisjoint(forbidden_calls)
    assert not any(
        fragment in target for target in targets for fragment in forbidden_targets
    )


def test_repaired_bounded_content_contains_all_target_anchors() -> None:
    candidate = _candidate_handoff("anchors")
    source = _source_handoff("anchors", candidate)
    selector = source.source_survival_packet["bounded_text_selection"]

    assert selector["missing_anchors"] == []
    assert selector["matched_anchor_count"] == len(source_harness.TARGET_COMPONENT_ANCHOR_GROUPS)
    assert selector["selection_strategy"] == "full_text_within_cap"
    assert selector["local_context_posture"] == "single_contiguous_window"


def test_analysis_packet_builds_semantic_observation_admits_and_coverage_reduces() -> None:
    packet = _run_repair("pass")

    assert packet["replay_result"] == "runkernel_handoff_repair_pass"
    assert packet["evidence_relative_analysis_packet_id"]
    assert packet["semantic_observation_attempted_count"] == 1
    assert packet["semantic_observation_admitted_count"] == 1
    assert packet["component_coverage_attempted_count"] == 1
    assert packet["component_coverage_reduced_count"] == 1
    assert packet["runkernel_preserved_in_process_not_rehydrated"] is True


def test_missing_runkernel_still_fails_honestly_at_gate_6() -> None:
    candidate = _candidate_handoff("missing-runkernel")
    source = _source_handoff("missing-runkernel", candidate)
    source_dir = _source_output_dir("missing-runkernel")

    packet = semantic_harness.reduce_semantic_coverage(
        source_survival_packet_path=source_dir / source_harness.SOURCE_PACKET_NAME,
        fetch_read_content_packet_path=source_dir / source_harness.FETCH_READ_PACKET_NAME,
        sanitized_content_reference_path=source_dir / source_harness.CONTENT_REFERENCE_NAME,
        evidence_ledger_projection_path=source_dir / source_harness.LEDGER_PROJECTION_NAME,
        output_dir=_output_dir("missing-runkernel") / "standalone-359",
        confirm_semantic_coverage=True,
        run_kernel=None,
    )

    assert source.run_kernel is candidate.run_kernel
    assert packet["semantic_support_result"] == (
        "semantic_support_fail_semantic_observation_admission"
    )
    assert packet["first_failed_gate"] == "gate_6_semantic_observation_admission"
    assert packet["semantic_observation_attempted_count"] == 1
    assert packet["component_coverage_reduced_count"] == 0


def test_closed_surfaces_remain_zero_after_pass() -> None:
    packet = _run_repair("closed-surfaces")

    assert packet["provider_search_calls"] == 0
    assert packet["broker_calls"] == 0
    assert packet["model_calls"] == 0
    assert packet["retrieval_calls"] == 0
    assert packet["fetch_read_calls_attempted"] == 1
    assert packet["fetch_read_calls_completed"] == 1
    assert "citation" not in packet["component_coverage_ref"]


def test_no_live_network_runs_without_confirmation() -> None:
    fetcher = FakeFetcher(_fake_fetch_result(text=SUPPORT_TEXT))

    with pytest.raises(repair.RunKernelHandoffRepairError) as exc_info:
        repair.verify_live_runkernel_handoff(
            sanitized_provider_results_path=_provider_results("no-confirm"),
            output_dir=_output_dir("no-confirm"),
            confirm_fetch_read_runkernel_handoff=False,
            fetcher=fetcher,
        )

    assert exc_info.value.code == "confirm_fetch_read_runkernel_handoff_required"
    assert fetcher.calls == []


def test_no_provider_broker_model_or_search_transport_imports_are_added() -> None:
    imported, called, _targets = _imports_calls_assignments(SCRIPT)
    forbidden_imports = {
        "core.search_providers",
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "scripts.run_provider_proxy_broker_once",
    }
    forbidden_calls = {
        "call_broker",
        "invoke_broker",
        "search_web",
        "ask_model",
        "execute_author",
        "create_final_answer_packet",
    }

    assert imported.isdisjoint(forbidden_imports)
    assert called.isdisjoint(forbidden_calls)


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "raw_html",
        "headers",
        "unbounded_text",
        "answer_text",
        "citations",
        "final_answer_packet",
        "author_material",
        "prompt",
        "model_response",
        "provider_payload",
        "secret",
    ],
)
def test_output_rejects_raw_unbounded_answer_citation_fap_author_prompt_model_provider_secret_fields(
    forbidden_key: str,
) -> None:
    packet = _run_repair(f"reject-{forbidden_key}")
    spoofed = deepcopy(packet)
    spoofed[forbidden_key] = "forbidden"

    with pytest.raises(repair.RunKernelHandoffRepairError):
        repair.validate_repair_packet(spoofed)


def test_written_repair_packet_contains_no_raw_bounded_text_or_author_material() -> None:
    packet = _run_repair("written")
    output_dir = _output_dir("written")
    written = json.loads((output_dir / repair.REPAIR_PACKET_NAME).read_text(encoding="utf-8"))

    assert written == packet
    forbidden = {
        "bounded_text",
        "raw_html",
        "raw_page_text",
        "unbounded_text",
        "answer_text",
        "citations",
        "final_answer_packet",
        "author_material",
        "prompt",
        "model_response",
        "provider_payload",
        "secret",
    }
    assert _all_keys(written).isdisjoint(forbidden)
    assert (output_dir / repair.REPAIR_MARKDOWN_NAME).exists()


def test_docs_record_repair_mode_defect_budget_closed_surfaces_and_next_checkpoint() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "Mode: REPAIR",
        "semantic_support_fail_semantic_observation_admission",
        "gate 6",
        "serialized packets/projections are insufficient",
        "provider/search/broker calls: 0",
        "model calls: 0",
        "URL fetch/read calls: max 1",
        "Closed Surfaces",
        "Explicit Non-Proofs",
        "AG-LIVE-SUFFICIENCY-FAP-AUTHORPROSE-01",
    )
    for needle in required:
        assert needle in text
