from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.evidence_relative_analysis_packet import (
    ANALYST_REPORT_POSTURE,
    EVIDENCE_RELATIVE_ANALYSIS_PACKET_OWNER,
    EVIDENCE_RELATIVE_ANALYSIS_PACKET_SCHEMA_VERSION,
    EvidenceRelativeAnalysisPacketError,
    build_evidence_relative_analysis_packet,
    evidence_relative_analysis_packet_ref_from_packet,
    validate_evidence_relative_analysis_packet,
)
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
)
from tests.test_ag_fetch_read_content_reference_01 import (
    _failed_material,
    _readable_material,
)
from tests.test_ag_search_executor_handoff_01 import _initial_only_kernel
from tests.test_ag_search_result_candidate_packet_01 import _packet_from_state

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "evidence_relative_analysis_packet.py"
DOCS = (
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
)
LEGACY_AUDIT_DOC = ROOT / "docs" / "architecture" / "AG_ANALYST_EVIDENCE_RELATIVE_REPORT_01.md"

FALSE_FLAGS = {
    "semantic_observation_admitted": False,
    "component_coverage_created": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "citation_created": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
    "provider_called": False,
    "broker_called": False,
    "retrieval_executed": False,
    "model_called": False,
    "search_dispatched": False,
    "query_plan_created": False,
    "search_executor_handoff_created": False,
}


def _analysis_fixture(
    *,
    readable_count: int = 1,
    failed_count: int = 1,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    candidate_count = readable_count + failed_count
    _candidate_kernel, candidate_packet = _packet_from_state(candidate_count=candidate_count)
    kernel = _initial_only_kernel()
    materials = [_readable_material(candidate_packet, index=index) for index in range(readable_count)]
    materials.extend(_failed_material(candidate_packet, index=readable_count + index) for index in range(failed_count))
    fetch_read_packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        materials,
    )
    projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=kernel,
        fetch_read_content_packet=fetch_read_packet,
    )
    return kernel, fetch_read_packet, projection


def _custody_records(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = projection["fetch_read_candidate_custody"]["fetch_read_candidate_custody_records"]
    return [dict(record) for record in records]


def _records_by_status(
    projection: Mapping[str, Any],
    status: str,
) -> list[dict[str, Any]]:
    return [record for record in _custody_records(projection) if record["fetch_read_status"] == status]


def _support_proposal(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal_kind": "possible_support_proposal",
        "reference_id": record["reference_id"],
        "reference_digest": record["reference_digest"],
        "candidate_id": record["candidate_id"],
        "candidate_digest": record["candidate_digest"],
        "fetch_read_content_packet_digest": record["fetch_read_content_packet_digest"],
        "search_result_candidate_packet_digest": record["search_result_candidate_packet_digest"],
        "component_id": record["component_id"],
        "proposal_summary": "Appears relevant to the requested component.",
        "reason": "offline analyst proposal over custody identity only",
    }


def _packet() -> tuple[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    kernel, fetch_read_packet, projection = _analysis_fixture()
    readable = _records_by_status(projection, "readable")
    packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[_support_proposal(readable[0])],
    )
    return kernel, fetch_read_packet, projection, packet


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


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(_text(path))
    imported_names: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
    return imported_names, called_names


def test_happy_path_packet_report_construction_from_evidence_ledger_custody() -> None:
    _kernel, _fetch_read_packet, projection, packet = _packet()
    report = packet["analyst_report"]
    readable_records = _records_by_status(projection, "readable")
    failed_records = _records_by_status(projection, "failed")

    assert packet["owner"] == EVIDENCE_RELATIVE_ANALYSIS_PACKET_OWNER
    assert packet["schema_version"] == EVIDENCE_RELATIVE_ANALYSIS_PACKET_SCHEMA_VERSION
    assert packet["packet_posture"] == ANALYST_REPORT_POSTURE
    assert packet["canonical_state"] is False
    assert packet["reduced_state"] is False
    assert packet["fetch_read_candidate_custody_count"] == 2
    assert report["report_posture"] == ANALYST_REPORT_POSTURE
    assert report["finding_count"] == 1
    assert report["analyzed_custody_record_count"] == 1
    assert report["unanalyzed_custody_record_count"] == 0
    assert report["unreadable_custody_gap_count"] == 1

    finding = report["findings"][0]
    assert finding["proposal_kind"] == "possible_support_proposal"
    assert finding["reference_id"] == readable_records[0]["reference_id"]
    assert finding["reference_digest"] == readable_records[0]["reference_digest"]
    assert finding["fetch_read_content_packet_id"] == (readable_records[0]["fetch_read_content_packet_id"])
    assert (
        finding["search_result_candidate_packet_digest"]
        == (readable_records[0]["search_result_candidate_packet_digest"])
    )
    assert finding["candidate_url"] == readable_records[0]["candidate_url"]
    assert finding["candidate_domain"] == readable_records[0]["candidate_domain"]
    assert finding["candidate_title"] == readable_records[0]["candidate_title"]
    assert finding["excerpt_digest"] == readable_records[0]["excerpt_digest"]
    assert finding["bounded_character_count"] == (readable_records[0]["bounded_character_count"])

    gaps_by_ref = {gap["trigger_reference_id"]: gap for gap in report["analysis_gap_proposals"]}
    assert gaps_by_ref[failed_records[0]["reference_id"]]["gap_kind"] == ("missing_readable_source")


def test_packet_report_finding_and_gap_ids_and_digests_are_stable() -> None:
    _kernel, _fetch_read_packet, projection = _analysis_fixture()
    proposal = _support_proposal(_records_by_status(projection, "readable")[0])

    first = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=deepcopy(projection),
        analyst_proposal_records=[deepcopy(proposal)],
    )
    second = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=deepcopy(projection),
        analyst_proposal_records=[deepcopy(proposal)],
    )
    rebuilt = validate_evidence_relative_analysis_packet(deepcopy(first))

    assert second["packet_id"] == first["packet_id"]
    assert second["packet_digest"] == first["packet_digest"]
    assert second["analyst_report"]["report_id"] == first["analyst_report"]["report_id"]
    assert second["analyst_report"]["report_digest"] == (first["analyst_report"]["report_digest"])
    assert (
        second["analyst_report"]["findings"][0]["finding_id"] == (first["analyst_report"]["findings"][0]["finding_id"])
    )
    assert (
        second["analyst_report"]["analysis_gap_proposals"][0]["gap_id"]
        == (first["analyst_report"]["analysis_gap_proposals"][0]["gap_id"])
    )
    assert rebuilt == first


def test_findings_reference_custody_by_ids_and_digests_without_bounded_text() -> None:
    _kernel, fetch_read_packet, _projection, packet = _packet()
    assert "bounded_text" in fetch_read_packet["reference_records"][0]
    encoded = json.dumps(packet, sort_keys=True)

    for sentinel in (
        "bounded_text",
        "Bounded sanitized excerpt about the permit threshold.",
        "raw_provider_payload",
        "raw_search_response",
        "raw_page_content",
        "private_logs",
        "full_trace",
        "author_material",
    ):
        assert sentinel not in encoded

    finding = packet["analyst_report"]["findings"][0]
    expected_keys = {
        "candidate_id",
        "candidate_digest",
        "reference_id",
        "reference_digest",
        "fetch_read_content_packet_id",
        "fetch_read_content_packet_digest",
        "search_result_candidate_packet_id",
        "search_result_candidate_packet_digest",
        "evidence_ledger_custody_projection_ref",
        "excerpt_digest",
        "bounded_character_count",
    }
    assert expected_keys <= set(finding)


def test_readable_custody_can_produce_proposal_only_support() -> None:
    _kernel, _fetch_read_packet, _projection, packet = _packet()
    report = packet["analyst_report"]
    finding = report["findings"][0]
    per_component = report["per_component_relevance_proposals"][0]

    assert finding["proposal_kind"] == "possible_support_proposal"
    assert finding["semantic_observation_admitted"] is False
    assert finding["component_coverage_created"] is False
    assert finding["source_obligation_satisfied"] is False
    assert finding["citation_eligible"] is False
    assert finding["sufficiency_decided"] is False
    assert finding["final_answer_packet_created"] is False
    assert finding["author_input_created"] is False

    assert per_component["component_satisfied"] is False
    assert per_component["component_coverage_created"] is False
    assert per_component["source_obligation_satisfied"] is False
    assert per_component["citation_eligible"] is False
    assert per_component["sufficiency_decided"] is False


def test_readable_but_unanalyzed_custody_produces_analysis_missing_gap_not_support() -> None:
    _kernel, _fetch_read_packet, projection = _analysis_fixture(
        readable_count=2,
        failed_count=0,
    )
    readable = _records_by_status(projection, "readable")
    packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[_support_proposal(readable[0])],
    )
    unanalyzed = readable[1]
    report = packet["analyst_report"]

    assert all(finding["reference_id"] != unanalyzed["reference_id"] for finding in report["findings"])
    gap = next(
        gap for gap in report["analysis_gap_proposals"] if gap["trigger_reference_id"] == unanalyzed["reference_id"]
    )
    assert gap["gap_kind"] == "analysis_missing"
    assert gap["source_obligation_satisfied"] is False
    assert gap["citation_eligible"] is False


def test_failed_or_unreadable_custody_produces_gap_not_support() -> None:
    _kernel, _fetch_read_packet, projection, packet = _packet()
    failed = _records_by_status(projection, "failed")[0]
    report = packet["analyst_report"]

    assert all(finding["reference_id"] != failed["reference_id"] for finding in report["findings"])
    gap = next(gap for gap in report["analysis_gap_proposals"] if gap["trigger_reference_id"] == failed["reference_id"])
    assert gap["gap_kind"] == "missing_readable_source"
    assert gap["fetch_read_status"] == "failed"
    assert gap["reason"] == "timeout"
    assert gap["source_obligation_satisfied"] is False
    assert gap["citation_eligible"] is False


def test_possible_support_does_not_create_downstream_authority_or_author_state() -> None:
    kernel, _fetch_read_packet, _projection, packet = _packet()

    assert kernel.state.semantic_observation_admission_state == {}
    assert kernel.state.component_coverage_state == {}
    assert kernel.state.component_coverage_projection == {}
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.sufficiency_judgment_projection == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}

    for surface in (
        packet,
        packet["analyst_report"],
        packet["analyst_report"]["findings"][0],
    ):
        for key, expected in FALSE_FLAGS.items():
            assert surface[key] is expected


def test_analysis_gap_proposals_do_not_dispatch_search_or_query_plan() -> None:
    _kernel, _fetch_read_packet, _projection, packet = _packet()

    for gap in packet["analyst_report"]["analysis_gap_proposals"]:
        assert gap["search_dispatched"] is False
        assert gap["query_plan_created"] is False
        assert gap["search_executor_handoff_created"] is False
        assert gap["provider_called"] is False
        assert gap["broker_called"] is False
        assert gap["retrieval_executed"] is False
        assert gap["model_called"] is False


def test_tampered_custody_refs_or_digests_are_rejected() -> None:
    _kernel, _fetch_read_packet, projection = _analysis_fixture()
    readable = _records_by_status(projection, "readable")[0]

    proposal = _support_proposal(readable)
    proposal["reference_digest"] = "0" * 64
    with pytest.raises(EvidenceRelativeAnalysisPacketError, match="reference_digest"):
        build_evidence_relative_analysis_packet(
            evidence_ledger_projection=projection,
            analyst_proposal_records=[proposal],
        )

    tampered_projection = deepcopy(projection)
    tampered_projection["fetch_read_candidate_custody"]["custody_record_count"] = 99
    with pytest.raises(EvidenceRelativeAnalysisPacketError, match="count mismatch"):
        build_evidence_relative_analysis_packet(
            evidence_ledger_projection=tampered_projection,
            analyst_proposal_records=[],
        )

    packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[_support_proposal(readable)],
    )
    tampered_packet = deepcopy(packet)
    tampered_packet["analyst_report"]["findings"][0]["reference_digest"] = "1" * 64
    with pytest.raises(EvidenceRelativeAnalysisPacketError, match="finding digest"):
        validate_evidence_relative_analysis_packet(tampered_packet)


def test_raw_private_bounded_text_and_authority_fields_are_rejected() -> None:
    _kernel, _fetch_read_packet, projection = _analysis_fixture()
    readable = _records_by_status(projection, "readable")[0]

    bounded = _support_proposal(readable)
    bounded["bounded_text"] = "do not copy this"
    with pytest.raises(EvidenceRelativeAnalysisPacketError, match="raw/private"):
        build_evidence_relative_analysis_packet(
            evidence_ledger_projection=projection,
            analyst_proposal_records=[bounded],
        )

    authority = _support_proposal(readable)
    authority["final_answer_packet"] = {"packet_id": "forbidden"}
    with pytest.raises(EvidenceRelativeAnalysisPacketError, match="closed authority"):
        build_evidence_relative_analysis_packet(
            evidence_ledger_projection=projection,
            analyst_proposal_records=[authority],
        )

    dangerous = _support_proposal(readable)
    dangerous["citation_eligible"] = True
    with pytest.raises(EvidenceRelativeAnalysisPacketError, match="closed runtime"):
        build_evidence_relative_analysis_packet(
            evidence_ledger_projection=projection,
            analyst_proposal_records=[dangerous],
        )


def test_closed_flags_stay_false_at_packet_report_finding_and_gap_levels() -> None:
    _kernel, _fetch_read_packet, _projection, packet = _packet()
    report = packet["analyst_report"]
    surfaces: list[Mapping[str, Any]] = [
        packet,
        report,
        *report["findings"],
        *report["analysis_gap_proposals"],
        *report["per_component_relevance_proposals"],
    ]

    for surface in surfaces:
        flags = surface["closed_surface_flags"]
        for key, expected in FALSE_FLAGS.items():
            assert flags[key] is expected
            if key in surface:
                assert surface[key] is expected


def test_no_downstream_runkernel_state_is_created() -> None:
    kernel, _fetch_read_packet, _projection, packet = _packet()

    assert evidence_relative_analysis_packet_ref_from_packet(packet)["packet_id"] == (packet["packet_id"])
    assert "evidence_relative_analysis_packet" not in kernel.state.projections
    assert kernel.state.component_coverage_state == {}
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.followup_authorization_state == {}
    assert kernel.state.followup_final_answer_packet_readiness_state == {}
    assert kernel.state.followup_author_observation_state == {}


def test_static_import_and_call_guards_keep_closed_surfaces_closed() -> None:
    forbidden_imports = {
        "core.analyst_runtime_stage",
        "core.analyst_quant_packet_runtime",
        "core.economist_handoff_contract",
        "core.scrutineer_remediation_handoff_contract",
        "core.semantic_observation_foundation",
        "core.semantic_observation_admission_runtime",
        "core.component_coverage_record",
        "core.component_coverage_reduction_runtime",
        "core.run_authority_sufficiency",
        "core.run_authority_sufficiency_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "dotenv",
        "openai",
        "requests",
        "httpx",
    }
    forbidden_calls = {
        "ask_model",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "brave_reconnaissance",
        "fetch_page",
        "fetch_url_text",
        "urlopen",
        "execute_author_action",
        "derive_author_input_payload",
        "format_citation",
        "render_citations",
        "build_semantic_observation_admission_state",
        "build_component_coverage_reduction_state",
        "FinalAnswerPacket",
    }

    imported_names, called_names = _imports_and_calls(RUNTIME_MODULE)

    assert imported_names.isdisjoint(forbidden_imports)
    assert called_names.isdisjoint(forbidden_calls)


def test_docs_record_evidence_relative_analysis_packet_posture() -> None:
    required = (
        "EvidenceRelativeAnalysisPacket",
        "analyst_report",
        "proposal-only evidence-relative meaning",
        "after EvidenceLedger custody",
        "not SemanticObservation admission",
        "does not create ComponentCoverage",
        "citation eligibility",
        "source-obligation satisfaction",
        "Sufficiency",
        "FinalAnswerPacket",
        "Author input",
        "readiness",
    )
    for path in DOCS:
        text = " ".join(_text(path).replace("`", "").split())
        for needle in required:
            assert needle in text, (path, needle)


def test_legacy_surface_audit_is_documented() -> None:
    text = _text(LEGACY_AUDIT_DOC)
    required = (
        "Legacy surface audit",
        "analyst_runtime_stage.py",
        "semantic_observation_foundation.py",
        "economist_handoff_contract.py",
        "scrutineer_remediation_handoff_contract.py",
        "ComponentCoverage",
        "Sufficiency",
        "FinalAnswerPacket",
        "Author",
        "intentionally avoided",
        "legacy/passive/downstream",
    )
    for needle in required:
        assert needle in text, needle
