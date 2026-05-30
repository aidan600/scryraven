from __future__ import annotations

import ast
import copy
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
    AUTHORITY_EVIDENCE_SELECTED,
    CANDIDATE_DISPOSITIONED,
    CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY,
    FINAL_CITATION_OBSERVED,
    FINAL_EVIDENCE_OBSERVED,
    LEGACY_CUSTODY_GAP_OBSERVED,
    assert_controller_evidence_ledger_integrity,
    build_controller_evidence_ledger,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_LEDGER_PATH = _ROOT / "core" / "controller_evidence_ledger.py"
_ASSEMBLY_PATH = _ROOT / "core" / "runtime_trace_projection_assembly.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

_REQUIREMENT = "official_current_rules"
_QUERY = "official current source fixture query"
_FIXTURE_URL = "https://agency.gov/current-rule"


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
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
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
        "candidate_id": "official-current-candidate",
        "title": "Official current rule",
        "url": _FIXTURE_URL,
        "text": "Official current guidance states the current rule.",
        "source_tier": "official",
        "source_class": _REQUIREMENT,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "provider_name": "offline-fixture",
        "provider_rank_or_position": 1,
        "classification_reason": "declared_source_class",
        "currentness_signal": "current observed",
        "claim_value_extraction_status": "extracted",
        "fit_state": "matched_selected",
        "source_id": 1,
    }
    candidate.update(overrides)
    return candidate


def _events(ledger: dict[str, Any], event_type: str) -> list[dict[str, Any]]:
    return [
        event
        for event in ledger["events"]
        if event["event_type"] == event_type
    ]


def test_ag74b_final_evidence_citation_custody_is_controller_complete_when_dispositioned() -> None:
    candidate = _official_candidate()
    passport = build_authority_candidate_passport_projection(
        lifecycle_trace=_trace(),
        recovered_passages=[candidate],
        final_top_evidence=[candidate],
        surface_visibility={
            "answer_contract_visible_candidate_ids": ["official-current-candidate"],
            "context_packet_visible_candidate_ids": ["official-current-candidate"],
            "analyst_visible_candidate_ids": ["official-current-candidate"],
            "author_visible_candidate_ids": ["official-current-candidate"],
            "cited_in_final_answer_candidate_ids": ["official-current-candidate"],
        },
    )

    ledger = build_controller_evidence_ledger(
        runtime_trace=_trace(),
        passport_projection=passport,
        visibility_export={
            "final_selected_authority_evidence_count": 0,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
        },
        final_top_evidence=[candidate],
        final_citations=[{"citation_id": "source:1", "url": _FIXTURE_URL}],
    )
    custody = ledger["final_evidence_citation_custody"]

    assert len(_events(ledger, CANDIDATE_DISPOSITIONED)) == 1
    assert len(_events(ledger, AUTHORITY_EVIDENCE_SELECTED)) == 1
    assert len(_events(ledger, FINAL_EVIDENCE_OBSERVED)) == 1
    assert len(_events(ledger, FINAL_CITATION_OBSERVED)) == 1
    assert _events(ledger, LEGACY_CUSTODY_GAP_OBSERVED) == []
    assert custody["owner"] == "ControllerEvidenceLedger"
    assert custody["status"] == "controller_complete"
    assert custody["custody_complete"] is True
    assert_controller_evidence_ledger_integrity(ledger)


def test_ag74b_final_success_without_candidate_custody_is_legacy_gap_not_complete() -> None:
    ledger = build_controller_evidence_ledger(
        runtime_trace=_trace(result_count=0),
        passport_projection={"passport_count": 0, "passports": []},
        provider_result_bridge={
            "bridge_record_count": 0,
            "bridge_records": [],
        },
        visibility_export={
            "final_selected_authority_evidence_count": 0,
            "final_evidence_official_or_canonical_count": 2,
            "final_citation_official_or_canonical_count": 1,
        },
    )
    custody = ledger["final_evidence_citation_custody"]
    gap_types = {
        event["gap_type"] for event in _events(ledger, LEGACY_CUSTODY_GAP_OBSERVED)
    }

    assert custody["status"] == "legacy_gap_observed"
    assert custody["custody_complete"] is False
    assert "final_evidence_or_citation_without_candidate_passport_custody" in gap_types
    assert "final_evidence_or_citation_without_final_selected_authority_evidence" in gap_types


def test_ag74b_runtime_projection_attaches_ledger_and_preserves_final_outputs() -> None:
    candidate = _official_candidate()
    final_top_evidence = [dict(candidate)]
    original_final_top_evidence = copy.deepcopy(final_top_evidence)
    execution_trace = {
        **_trace(),
        "source_survival_final_evidence_official_or_canonical_count": 1,
        "source_survival_final_citation_official_or_canonical_count": 1,
        "final_answer_source_ids_used": ["1"],
    }

    returned = attach_passive_runtime_projection_traces(
        execution_trace,
        recovered_passages=[candidate],
        final_top_evidence=final_top_evidence,
    )
    ledger_trace = returned[CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY]
    ledger = ledger_trace["ControllerEvidenceLedger"]

    assert returned is execution_trace
    assert final_top_evidence == original_final_top_evidence
    assert returned["final_answer_source_ids_used"] == ["1"]
    assert ledger["final_evidence_citation_custody"]["status"] in {
        "controller_complete",
        "legacy_gap_observed",
    }
    assert (
        returned[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY
        ]
        == ledger_trace
    )


def test_ag74b_runtime_aggregate_success_has_explicit_ledger_gap() -> None:
    execution_trace = {
        **_trace(result_count=0),
        "source_survival_final_evidence_official_or_canonical_count": 1,
        "source_survival_final_citation_official_or_canonical_count": 1,
        "final_answer_source_ids_used": ["1"],
    }

    attach_passive_runtime_projection_traces(
        execution_trace,
        recovered_passages=[],
        final_top_evidence=[],
    )
    ledger = execution_trace[CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY][
        "ControllerEvidenceLedger"
    ]
    gap_types = {
        event["gap_type"] for event in _events(ledger, LEGACY_CUSTODY_GAP_OBSERVED)
    }

    assert ledger["final_evidence_citation_custody"]["status"] == (
        "legacy_gap_observed"
    )
    assert ledger["final_evidence_citation_custody"]["custody_complete"] is False
    assert "final_evidence_or_citation_without_candidate_passport_custody" in gap_types


def test_ag74b_static_subordinates_old_path_without_protected_surface_drift() -> None:
    assembly_source = _ASSEMBLY_PATH.read_text(encoding="utf-8")
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    ledger_source = _LEDGER_PATH.read_text(encoding="utf-8")
    assembly_imports = {
        node.module
        for node in ast.walk(ast.parse(assembly_source))
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert "core.controller_evidence_ledger" in assembly_imports
    assert "build_controller_evidence_ledger" not in orchestrator_source
    assert "build_controller_evidence_ledger_trace" not in orchestrator_source
    assert "attach_runtime_trace_export_compatibility_payloads" in orchestrator_source
    assert "select_providers" not in ledger_source
    assert "search_web_results(" not in ledger_source
    assert "author_prompt" not in ledger_source
    assert "final_answer(" not in ledger_source
