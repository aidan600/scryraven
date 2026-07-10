from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.evidence_ledger import (
    FETCH_READ_CANDIDATE_CUSTODY_SCHEMA_VERSION,
    EvidenceCustodyGapType,
)
from core.evidence_ledger_candidate_custody import (
    EvidenceLedgerCandidateCustodyError,
    build_evidence_ledger_observation_from_fetch_read_content_packet,
)
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.fetch_read_content_reference import (
    FetchReadContentReferenceError,
    build_fetch_read_content_packet_from_candidate_packet,
)
from core.run_kernel import EVIDENCE_LEDGER_STAGE
from tests.test_ag_fetch_read_content_reference_01 import (
    _failed_material,
    _readable_material,
)
from tests.test_ag_search_result_candidate_packet_01 import _packet_from_state

ROOT = Path(__file__).resolve().parents[1]
BUILDER_MODULE = ROOT / "core" / "evidence_ledger_candidate_custody.py"
LEDGER_MODULE = ROOT / "core" / "evidence_ledger.py"


def _packet(
    *,
    readable: bool = True,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    kernel, candidate_packet = _packet_from_state()
    material = (
        _readable_material(candidate_packet)
        if readable
        else _failed_material(candidate_packet)
    )
    fetch_read_packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        [material],
    )
    return kernel, candidate_packet, fetch_read_packet


def _fetch_read_custody(projection: Mapping[str, Any]) -> dict[str, Any]:
    return dict(projection["fetch_read_candidate_custody"])


def _single_fetch_read_record(projection: Mapping[str, Any]) -> dict[str, Any]:
    records = _fetch_read_custody(projection)["fetch_read_candidate_custody_records"]
    assert len(records) == 1
    return records[0]


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


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
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


def test_fetch_read_packet_reduces_through_runkernel_authorized_candidate_custody() -> None:
    kernel, _candidate_packet, fetch_read_packet = _packet()

    projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=kernel,
        fetch_read_content_packet=fetch_read_packet,
    )

    assert projection == kernel.state.evidence_ledger.to_projection().to_dict()
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE] == projection
    custody = _fetch_read_custody(projection)
    assert custody["schema_version"] == FETCH_READ_CANDIDATE_CUSTODY_SCHEMA_VERSION
    assert custody["owner"] == "RunKernel.EvidenceLedger"
    assert custody["candidate_content_custody_visible"] is True
    assert custody["custody_record_count"] == 1


def test_readable_reference_becomes_observed_content_custody_with_lineage() -> None:
    kernel, candidate_packet, fetch_read_packet = _packet()
    projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=kernel,
        fetch_read_content_packet=fetch_read_packet,
    )

    reference = fetch_read_packet["reference_records"][0]
    record = _single_fetch_read_record(projection)
    assert projection["candidate_records"][0]["fact_disposition"] == "observed"
    assert projection["custody_records"][0]["disposition"] == "observed"
    assert record["disposition"] == "observed"
    assert record["fetch_read_status"] == "readable"
    assert record["run_id"] == kernel.state.run_id
    assert record["request_id"] == kernel.state.request_id
    assert record["current_answer_contract_digest"] == (
        candidate_packet["current_answer_contract_digest"]
    )
    assert record["search_executor_handoff_digest"] == (
        candidate_packet["search_executor_handoff_digest"]
    )
    assert record["search_result_candidate_packet_id"] == candidate_packet["packet_id"]
    assert record["search_result_candidate_packet_digest"] == (
        candidate_packet["packet_digest"]
    )
    assert record["fetch_read_content_packet_id"] == fetch_read_packet["packet_id"]
    assert record["fetch_read_content_packet_digest"] == (
        fetch_read_packet["packet_digest"]
    )
    assert record["candidate_id"] == reference["candidate_id"]
    assert record["candidate_digest"] == reference["candidate_digest"]
    assert record["search_result_candidate_record_digest"] == (
        reference["search_result_candidate_record_digest"]
    )
    assert record["reference_id"] == reference["reference_id"]
    assert record["reference_digest"] == reference["reference_digest"]
    assert record["search_task_id"] == reference["search_task_id"]
    assert record["query_intent_id"] == reference["query_intent_id"]
    assert record["component_id"] == reference["component_id"]
    assert record["candidate_url"] == reference["candidate_url"]
    assert record["candidate_domain"] == reference["candidate_domain"]
    assert record["candidate_title"] == reference["candidate_title"]
    assert record["resolved_url"] == reference["resolved_url"]
    assert record["resolved_domain"] == reference["resolved_domain"]
    assert record["bounded_content_present"] is True
    assert record["bounded_character_count"] == reference["bounded_character_count"]
    assert record["excerpt_digest"] == reference["excerpt_digest"]


def test_failed_reference_becomes_custody_gap_posture_not_support() -> None:
    _kernel, _candidate_packet, fetch_read_packet = _packet(readable=False)
    observation = build_evidence_ledger_observation_from_fetch_read_content_packet(
        fetch_read_packet
    )
    projection = _reduce_observation(observation.to_dict())

    record = _single_fetch_read_record(projection)
    assert record["fetch_read_status"] == "failed"
    assert record["disposition"] == "unfetchable"
    assert record["read_error_code"] == "timeout"
    assert record["failure_reason"] == "timeout"
    assert record["semantic_support_created"] is False
    assert record["citation_eligible"] is False
    assert record["source_obligation_satisfied"] is False
    gap_types = {
        gap["gap_type"]
        for gap in projection["custody_gaps"]
        if isinstance(gap, Mapping)
    }
    assert EvidenceCustodyGapType.MISSING_READABLE_SOURCE.value in gap_types


def test_later_satisfaction_reconciles_prior_requirement_custody_gap() -> None:
    from core.evidence_ledger import EvidenceCustodyGap, EvidenceLedger

    requirement = {
        "requirement_id": "provider_job_requirement:official_current",
        "requirement_kind": "official_current",
        "required_source_class": "official_current_rules",
        "required_source_tier": "official",
        "required_currentness": "current",
        "strictness": "required",
    }
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        {
            "observation_id": "observation:missing",
            "observation_source": "test",
            "requirements": [requirement],
        }
    )
    ledger.gaps.append(
        EvidenceCustodyGap(
            gap_type=EvidenceCustodyGapType.MISSING_OFFICIAL_CURRENT_CANDIDATE,
            requirement_id=requirement["requirement_id"],
            reason="candidate not yet linked",
        )
    )
    assert ledger.gaps

    ledger.reduce_observation(
        {
            "observation_id": "observation:satisfied",
            "observation_source": "test",
            "requirements": [requirement],
            "candidates": [
                {
                        "candidate_id": "candidate:official_current",
                    "url": "https://example.gov/current",
                    "title": "Current official rule",
                    "source_class": "official_current_rules",
                    "source_tier": "official",
                    "currentness_signal": "current",
                    "readable_status": "readable",
                    "disposition": "accepted",
                    "eligible_for_stronger_obligation": True,
                }
            ],
            "requirement_links": [
                {
                    "requirement_id": requirement["requirement_id"],
                    "candidate_id": "candidate:official_current",
                    "link_status": "fixture_link",
                }
            ],
        }
    )
    projection = ledger.to_projection().to_dict()
    resolved = next(
        item
        for item in projection["source_requirements"]
        if item["requirement_id"] == requirement["requirement_id"]
    )
    assert resolved["status"] == "satisfied"
    assert not any(
        gap.get("requirement_id") == requirement["requirement_id"]
        for gap in projection["custody_gaps"]
    )


def test_source_obligation_candidate_ids_remain_lineage_only() -> None:
    _kernel, _candidate_packet, fetch_read_packet = _packet()
    observation = build_evidence_ledger_observation_from_fetch_read_content_packet(
        fetch_read_packet
    )
    projection = _reduce_observation(observation.to_dict())

    reference = fetch_read_packet["reference_records"][0]
    record = _single_fetch_read_record(projection)
    custody = _fetch_read_custody(projection)
    assert record["source_obligation_candidate_ids"] == (
        reference["source_obligation_candidate_ids"]
    )
    assert custody["source_obligation_candidate_ids_are_lineage_only"] is True
    assert custody["source_obligation_candidate_ids_satisfy_requirements"] is False
    assert projection["source_requirements"] == []
    assert projection["requirement_links"] == []
    assert record["source_obligation_satisfied"] is False
    forbidden_requirement_keys = {
        "requirement_id",
        "linked_requirement_ids",
        "requirement_links",
        "satisfied_requirements",
    }
    assert _all_keys(record).isdisjoint(forbidden_requirement_keys)


def test_custody_does_not_create_semantic_citation_coverage_readiness_or_author_material() -> None:
    kernel, _candidate_packet, fetch_read_packet = _packet()
    projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=kernel,
        fetch_read_content_packet=fetch_read_packet,
    )
    custody = _fetch_read_custody(projection)
    record = _single_fetch_read_record(projection)

    for field in (
        "candidate_content_custody_is_semantic_support",
        "citation_eligible",
        "source_obligation_satisfied",
        "component_coverage_created",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "partial_answer_ready",
        "product_correctness_claimed",
    ):
        assert custody[field] is False
    for field in (
        "semantic_support_created",
        "citation_eligible",
        "source_obligation_satisfied",
        "component_coverage_created",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "partial_answer_ready",
        "product_correctness_claimed",
    ):
        assert record[field] is False
    assert projection["final_evidence_refs"] == []


def test_tampered_fetch_read_packet_is_rejected() -> None:
    _kernel, _candidate_packet, fetch_read_packet = _packet()
    tampered = deepcopy(fetch_read_packet)
    tampered["reference_records"][0]["reference_digest"] = "0" * 64

    with pytest.raises(FetchReadContentReferenceError, match="digest"):
        build_evidence_ledger_observation_from_fetch_read_content_packet(tampered)


def test_spoofed_authority_readiness_citation_and_obligation_claims_are_rejected() -> None:
    _kernel, _candidate_packet, fetch_read_packet = _packet()

    spoofed_readiness = deepcopy(fetch_read_packet)
    spoofed_readiness["final_evidence_eligible"] = True
    with pytest.raises(EvidenceLedgerCandidateCustodyError, match="upgrade claims"):
        build_evidence_ledger_observation_from_fetch_read_content_packet(
            spoofed_readiness
        )

    spoofed_obligation = deepcopy(fetch_read_packet)
    spoofed_obligation["requirement_links"] = [
        {"requirement_id": "source-obligation:1", "candidate_id": "candidate:1"}
    ]
    with pytest.raises(EvidenceLedgerCandidateCustodyError, match="upgrade fields"):
        build_evidence_ledger_observation_from_fetch_read_content_packet(
            spoofed_obligation
        )


def test_projection_omits_raw_private_fields_and_bounded_text_payload() -> None:
    _kernel, _candidate_packet, fetch_read_packet = _packet()
    assert "bounded_text" in fetch_read_packet["reference_records"][0]

    observation = build_evidence_ledger_observation_from_fetch_read_content_packet(
        fetch_read_packet
    )
    projection = _reduce_observation(observation.to_dict())
    encoded = json.dumps(projection, sort_keys=True)
    observation_encoded = json.dumps(observation.to_dict(), sort_keys=True)

    forbidden = (
        "bounded_text",
        "Bounded sanitized excerpt about the permit threshold.",
        "raw_provider_payload",
        "raw_search_response",
        "raw_page_content",
        "raw_headers",
        "raw_prompt",
        "private_logs",
        "db_cache_rows",
        "full_trace",
    )
    for sentinel in forbidden:
        assert sentinel not in encoded
        assert sentinel not in observation_encoded


def test_static_closed_surface_guard_for_fetch_read_candidate_custody() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.semantic_observation_foundation",
        "core.semantic_observation_admission_runtime",
        "core.component_coverage_record",
        "core.component_coverage_reduction_runtime",
        "core.run_authority_sufficiency",
        "core.run_authority_sufficiency_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.private_broker",
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
    }
    for path in (BUILDER_MODULE, LEDGER_MODULE):
        imported_names, called_names = _imports_and_calls(path)
        assert imported_names.isdisjoint(forbidden_imports)
        assert called_names.isdisjoint(forbidden_calls)


def _reduce_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    from core.evidence_ledger import EvidenceLedger

    ledger = EvidenceLedger()
    ledger.reduce_observation(observation)
    return ledger.to_projection().to_dict()
