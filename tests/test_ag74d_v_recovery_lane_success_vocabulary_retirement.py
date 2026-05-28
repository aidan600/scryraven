from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from core.controller_evidence_ledger import (
    CONTROLLER_EVIDENCE_LEDGER_SCHEMA_VERSION,
    CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.official_canonical_recovery_execution_admission import (
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
    format_official_canonical_recovery_diagnostics_markdown,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_EXPORT_PATH = _ROOT / "core" / "official_canonical_recovery_visibility_export.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_CUSTODY_INTERPRETATION = (
    "recovery_lane_observation_not_controller_custody_status"
)


def _admission() -> dict[str, Any]:
    return {
        OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY: {
            "schema_version": "official_canonical_recovery_execution_admission_ag50b_v1",
            "trace_mode": "recovery_execution_admission",
            "OfficialCanonicalRecoveryExecutionAdmission": {
                "admission_considered": True,
                "admission_eligible": True,
                "admission_used": True,
                "admission_skip_reason": None,
                "admission_blockers": [],
            },
        }
    }


def _ledger_trace(*, status: str, custody_complete: bool) -> dict[str, Any]:
    legacy_gap_types = (
        ["final_evidence_or_citation_without_candidate_passport_custody"]
        if status == "legacy_gap_observed"
        else []
    )
    return {
        "schema_version": "controller_evidence_ledger_runtime_custody_ag74b_v1",
        "trace_key": CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY,
        "trace_mode": "controller_owned_authority_custody",
        "diagnostic_only": False,
        "sanitized": True,
        "behavior_changed": False,
        "runtime_behavior_changed": False,
        "ControllerEvidenceLedger": {
            "schema_version": CONTROLLER_EVIDENCE_LEDGER_SCHEMA_VERSION,
            "owner": "ControllerEvidenceLedger",
            "controller_owned": True,
            "diagnostic_only": False,
            "sanitized": True,
            "behavior_changed": False,
            "runtime_behavior_changed": False,
            "final_evidence_citation_custody": {
                "owner": "ControllerEvidenceLedger",
                "status": status,
                "custody_complete": custody_complete,
                "final_evidence_observed_count": 1,
                "final_citation_observed_count": 1,
                "represented_authority_candidate_count": (
                    1 if custody_complete else 0
                ),
                "candidate_disposition_count": 1 if custody_complete else 0,
                "selected_authority_evidence_count": 1 if custody_complete else 0,
                "legacy_gap_types": legacy_gap_types,
                "legacy_success_counts_are_authoritative": False,
            },
        },
    }


def _trace(
    *,
    ledger_status: str = "legacy_gap_observed",
    custody_complete: bool = False,
) -> dict[str, Any]:
    return {
        **_admission(),
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_execution_attempted": True,
        "active_source_class_recovery_result_count": 3,
        "recovered_accepted_url_count": 1,
        "recovered_source_class_counts": {"primary_source_documents": 1},
        "recovered_source_tier_counts": {"canonical": 1},
        "recovered_official_or_primary_count": 1,
        "source_survival_final_evidence_official_or_canonical_count": 1,
        "source_survival_final_citation_official_or_canonical_count": 1,
        CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY: _ledger_trace(
            status=ledger_status,
            custody_complete=custody_complete,
        ),
    }


def test_ag74d_v_renames_success_labels_to_recovery_lane_observations() -> None:
    packet = build_official_canonical_recovery_visibility_export(_trace())
    rendered = format_official_canonical_recovery_diagnostics_markdown(packet)

    assert packet["likely_next_failure_layer"] == (
        "recovery_lane_source_citation_observed"
    )
    assert packet["next_failure_layer"] == (
        "recovery_lane_canonical_citation_observed"
    )
    assert "source_survived_to_citation" not in rendered
    assert "canonical_source_cited" not in rendered
    assert packet["final_evidence_citation_custody_status"] == "legacy_gap_observed"
    assert packet["final_evidence_citation_custody_complete"] is False
    assert packet["legacy_gap_observed"] is True
    assert "`legacy_gap_observed`: true" in rendered


def test_ag74d_v_retained_survival_fields_require_ledger_custody_interpretation() -> None:
    packet = build_official_canonical_recovery_visibility_export(_trace())
    complete = build_official_canonical_recovery_visibility_export(
        _trace(ledger_status="controller_complete", custody_complete=True)
    )

    assert packet["final_evidence_survival_status"] == "visible"
    assert packet["final_citation_survival_status"] == "visible"
    assert packet["final_evidence_survival_status_custody_interpretation"] == (
        _CUSTODY_INTERPRETATION
    )
    assert packet["final_citation_survival_status_custody_interpretation"] == (
        _CUSTODY_INTERPRETATION
    )
    assert packet["likely_next_failure_layer_custody_interpretation"] == (
        _CUSTODY_INTERPRETATION
    )
    assert packet["next_failure_layer_custody_interpretation"] == (
        _CUSTODY_INTERPRETATION
    )
    assert packet["final_evidence_citation_custody_complete"] is False
    assert complete["final_evidence_citation_custody_status"] == (
        "controller_complete"
    )
    assert complete["final_evidence_citation_custody_complete"] is True


def test_ag74d_v_static_export_deletes_old_terminal_success_values() -> None:
    export_source = _EXPORT_PATH.read_text(encoding="utf-8")
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert "source_survived_to_citation" not in export_source
    assert "canonical_source_cited" not in export_source
    assert "recovery_lane_source_citation_observed" in export_source
    assert "recovery_lane_canonical_citation_observed" in export_source
    assert "build_official_canonical_recovery_visibility_export" not in (
        orchestrator_source
    )
    for forbidden in (
        "select_providers",
        "provider_depth",
        "linkup",
        "source_classifier",
        "author_prompt",
        "ask_model",
        "final_answer(",
    ):
        assert forbidden not in export_source.casefold()


def test_ag74d_v_runtime_projection_preserves_final_answer_citation_surfaces() -> None:
    final_top_evidence = [
        {
            "source_id": 1,
            "url": "https://example.com/canonical-doc",
            "source_tier": "canonical",
            "source_class": "primary_source_documents",
        }
    ]
    original_final_top_evidence = copy.deepcopy(final_top_evidence)
    execution_trace = {
        **_admission(),
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
        "source_survival_final_evidence_official_or_canonical_count": 1,
        "source_survival_final_citation_official_or_canonical_count": 1,
        "final_answer_source_ids_used": ["1"],
        "final_output_preview": "Existing answer body with [1].",
    }

    returned = attach_passive_runtime_projection_traces(
        execution_trace,
        recovered_passages=[],
        final_top_evidence=final_top_evidence,
    )

    assert returned is execution_trace
    assert final_top_evidence == original_final_top_evidence
    assert returned["final_answer_source_ids_used"] == ["1"]
    assert returned["final_output_preview"] == "Existing answer body with [1]."
