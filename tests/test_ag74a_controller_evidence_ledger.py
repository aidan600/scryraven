from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.authority_candidate_passport import (
    build_authority_candidate_passport_projection,
)
from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.controller_evidence_ledger import (
    ANSWER_CONTRACT_UPDATED,
    AUTHORITY_EVIDENCE_SELECTED,
    AUTHORITY_REQUIREMENT_DECLARED,
    CANDIDATE_DISPOSITIONED,
    CANDIDATE_REPRESENTED,
    CONTROLLER_EVIDENCE_LEDGER_SCHEMA_VERSION,
    FINAL_CITATION_OBSERVED,
    FINAL_EVIDENCE_OBSERVED,
    LEDGER_EVENT_TYPES,
    LEGACY_CUSTODY_GAP_OBSERVED,
    PROVIDER_RESULT_OBSERVED,
    assert_controller_evidence_ledger_integrity,
    build_controller_evidence_ledger,
)
from core.provider_result_represented_visibility import (
    build_provider_result_represented_visibility_projection,
)

_ROOT = Path(__file__).resolve().parents[1]
_LEDGER_PATH = _ROOT / "core" / "controller_evidence_ledger.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

_REQUIREMENT = "official_current_rules"
_QUERY = "IRS 2026 standard mileage rate official current source"
_IRS_URL = "https://www.irs.gov/newsroom/irs-issues-standard-mileage-rates-for-2026"


def _trace(*, result_count: int = 1) -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id=_REQUIREMENT,
        required_authority=_REQUIREMENT,
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=(_QUERY,),
        required_source_classes=(_REQUIREMENT,),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace.update(
        {
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_missing_classes": [_REQUIREMENT],
            "active_source_class_recovery_result_count": result_count,
            "candidate_acquisition_provider_result_count": result_count,
            "recovered_accepted_url_count": result_count,
        }
    )
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=result_count,
        recovered_result_count=result_count,
        accepted_url_count=result_count,
    )
    return trace


def _official_candidate(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "candidate_id": "irs-2026-official",
        "title": "IRS issues standard mileage rates for 2026",
        "url": _IRS_URL,
        "text": "Official IRS current guidance states the 2026 business rate.",
        "source_tier": "official",
        "source_class": _REQUIREMENT,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "provider_name": "offline-fixture",
        "provider_rank_or_position": 1,
        "classification_reason": "declared_source_class",
        "currentness_signal": "2026 observed",
        "claim_value_extraction_status": "extracted",
    }
    candidate.update(overrides)
    return candidate


def _provider_result(**overrides: Any) -> dict[str, Any]:
    result = {
        "provider_result_id": "provider-result-irs-1",
        "provider_name": "offline-provider",
        "provider_role": "source_class_recovery",
        "retrieval_pass_id": "source_class_recovery:1",
        "query_preview": _QUERY,
        "provider_rank_or_position": 1,
        "source_url": _IRS_URL,
        "normalized_domain": "irs.gov",
        "title": "IRS issues standard mileage rates for 2026",
        "source_tier": "official",
        "source_class": _REQUIREMENT,
        "provider_returned": True,
    }
    result.update(overrides)
    return result


def _event_types(ledger: dict[str, Any], event_type: str) -> list[dict[str, Any]]:
    return [
        event
        for event in ledger["events"]
        if event["event_type"] == event_type
    ]


def test_ag74a_ledger_contract_declares_required_event_vocabulary() -> None:
    ledger = build_controller_evidence_ledger(runtime_trace=_trace(result_count=0))

    assert ledger["schema_version"] == CONTROLLER_EVIDENCE_LEDGER_SCHEMA_VERSION
    assert ledger["controller_owned"] is True
    assert ledger["event_types"] == list(LEDGER_EVENT_TYPES)
    assert _event_types(ledger, AUTHORITY_REQUIREMENT_DECLARED)
    assert ledger["decision_authority"]["controller_decides"] is True
    assert ledger["decision_authority"]["legacy_orchestrator_decides"] is False


def test_ag74a_maps_provider_bridge_passport_final_surfaces_and_answer_contract() -> None:
    candidate = _official_candidate(
        fit_state="matched_selected",
        controller_visible=True,
        answer_contract_visible=True,
        context_packet_visible=True,
        analyst_visible=True,
        author_visible=True,
        cited_in_final_answer=True,
    )
    passport = build_authority_candidate_passport_projection(
        lifecycle_trace=_trace(),
        recovered_passages=[candidate],
        final_top_evidence=[candidate],
    )
    bridge = build_provider_result_represented_visibility_projection(
        runtime_trace={"provider_result_summary_count": 1},
        provider_results=[_provider_result()],
        passport_projection=passport,
    )
    handoff = {
        "schema_version": "answer_contract_fulfillment_v1",
        "fulfilled_items": ["identify the current official rule or policy"],
        "partial_items": [],
        "unfulfilled_items": [],
        "source_obligation_status": "fulfilled",
        "unfulfilled_source_classes": [],
        "partial_source_classes": [],
        "evidence_used": [
            {
                "reference": "source:irs-2026-official",
                "source_class": _REQUIREMENT,
                "summary": "IRS current source",
            }
        ],
    }

    ledger = build_controller_evidence_ledger(
        runtime_trace=_trace(),
        provider_result_bridge=bridge,
        passport_projection=passport,
        visibility_export={
            "final_selected_authority_evidence_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
        },
        final_top_evidence=[candidate],
        final_citations=[{"citation_id": "irs-citation", "url": _IRS_URL}],
        answer_contract_handoff=handoff,
    )

    assert len(_event_types(ledger, PROVIDER_RESULT_OBSERVED)) == 1
    assert len(_event_types(ledger, CANDIDATE_REPRESENTED)) == 1
    assert len(_event_types(ledger, CANDIDATE_DISPOSITIONED)) == 1
    assert len(_event_types(ledger, AUTHORITY_EVIDENCE_SELECTED)) == 1
    assert len(_event_types(ledger, FINAL_EVIDENCE_OBSERVED)) == 1
    assert len(_event_types(ledger, FINAL_CITATION_OBSERVED)) == 1
    assert _event_types(ledger, ANSWER_CONTRACT_UPDATED)[0][
        "source_obligation_status"
    ] == "fulfilled"
    assert ledger["integrity"]["status"] == "complete"
    assert_controller_evidence_ledger_integrity(ledger)


def test_ag74a_final_evidence_and_citations_survive_with_zero_passport_custody_gap() -> None:
    ledger = build_controller_evidence_ledger(
        runtime_trace=_trace(result_count=0),
        provider_result_bridge={
            "schema_version": "provider_result_represented_visibility_ag73d_v1",
            "bridge_record_count": 0,
            "bridge_records": [],
            "aggregate_reconciliation_status": (
                "aggregate_provider_count_exceeds_visible_bridge_records"
            ),
        },
        passport_projection={
            "schema_version": "authority_candidate_passport_ag73a_v1",
            "passport_count": 0,
            "passports": [],
            "passport_integrity_status": "complete",
        },
        visibility_export={
            "final_selected_authority_evidence_count": 0,
            "final_evidence_official_or_canonical_count": 5,
            "final_citation_official_or_canonical_count": 2,
            "final_evidence_survival_status": "visible",
            "final_citation_survival_status": "visible",
        },
    )
    gap_types = {
        event["gap_type"] for event in _event_types(ledger, LEGACY_CUSTODY_GAP_OBSERVED)
    }

    assert len(_event_types(ledger, FINAL_EVIDENCE_OBSERVED)) == 5
    assert len(_event_types(ledger, FINAL_CITATION_OBSERVED)) == 2
    assert "final_evidence_or_citation_without_candidate_passport_custody" in gap_types
    assert "final_evidence_or_citation_without_final_selected_authority_evidence" in gap_types
    assert "provider_result_bridge_aggregate_not_reconciled" in gap_types
    assert ledger["integrity"]["status"] == "complete"


def test_ag74a_represented_official_candidate_gets_controller_visible_disposition() -> None:
    bridge = build_provider_result_represented_visibility_projection(
        runtime_trace={"provider_result_summary_count": 1},
        provider_results=[_provider_result()],
        passport_projection={"passports": []},
        represented_candidates=[
            {
                "candidate_id": "irs-2026-official",
                "url": _IRS_URL,
                "source_tier": "official",
                "source_class": _REQUIREMENT,
            }
        ],
    )

    ledger = build_controller_evidence_ledger(
        runtime_trace=_trace(),
        provider_result_bridge=bridge,
        passport_projection={"passport_count": 0, "passports": []},
    )
    dispositions = _event_types(ledger, CANDIDATE_DISPOSITIONED)

    assert dispositions[0]["candidate_id"] == "irs-2026-official"
    assert dispositions[0]["disposition"] == "represented_candidate_without_passport"
    assert ledger["integrity"]["represented_candidates_missing_disposition"] == []
    assert_controller_evidence_ledger_integrity(ledger)


def test_ag74a_ledger_sanitizes_protected_material_and_does_not_change_behavior() -> None:
    ledger = build_controller_evidence_ledger(
        runtime_trace={
            **_trace(),
            "raw_prompt": "do not leak",
            "raw_provider_payload": "do not leak",
        },
        final_top_evidence=[
            _official_candidate(
                raw_prompt="do not leak",
                raw_provider_payload="do not leak",
            )
        ],
    )
    payload = json.dumps(ledger, sort_keys=True)

    assert "do not leak" not in payload
    assert ledger["behavior_changed"] is False
    assert ledger["runtime_behavior_changed"] is False


def test_ag74a_static_guards_keep_protected_surfaces_closed() -> None:
    forbidden_import_prefixes = {
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.db",
        "core.llm",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.provider",
        "core.providers",
        "core.routing",
        "core.run_logging",
        "core.search_providers",
        "core.source_classifier",
        "core.author",
        "core.economist",
        "core.final_answer",
    }
    forbidden_terms = {
        "select_providers",
        "search_web_results(",
        "ask_model",
        "author_prompt",
        "final_answer(",
        "process_search_queries(",
    }
    tree = ast.parse(_LEDGER_PATH.read_text(encoding="utf-8"))
    imported = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    imported.extend(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    violations = [
        name
        for name in imported
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    ledger_source = _LEDGER_PATH.read_text(encoding="utf-8")
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in ledger_source for term in forbidden_terms)
    assert "controller_evidence_ledger" not in orchestrator_source
    assert "ControllerEvidenceLedger" not in orchestrator_source
