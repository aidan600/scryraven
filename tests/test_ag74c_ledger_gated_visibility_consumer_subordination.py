from __future__ import annotations

import ast
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
    OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY,
    build_official_canonical_recovery_visibility_export,
    format_official_canonical_recovery_diagnostics_markdown,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_EXPORT_PATH = _ROOT / "core" / "official_canonical_recovery_visibility_export.py"
_ASSEMBLY_PATH = _ROOT / "core" / "runtime_trace_projection_assembly.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _admission(*, used: bool = True) -> dict[str, Any]:
    return {
        OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY: {
            "schema_version": "official_canonical_recovery_execution_admission_ag50b_v1",
            "trace_mode": "recovery_execution_admission",
            "OfficialCanonicalRecoveryExecutionAdmission": {
                "admission_considered": True,
                "admission_eligible": used,
                "admission_used": used,
                "admission_skip_reason": None if used else "not_required",
                "admission_blockers": [],
            },
        }
    }


def _ledger_trace(
    *,
    status: str,
    custody_complete: bool,
    legacy_gap_types: list[str] | None = None,
) -> dict[str, Any]:
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
                "final_evidence_observed_count": 2,
                "final_citation_observed_count": 1,
                "represented_authority_candidate_count": (
                    1 if custody_complete else 0
                ),
                "candidate_disposition_count": 1 if custody_complete else 0,
                "selected_authority_evidence_count": 1 if custody_complete else 0,
                "legacy_gap_types": legacy_gap_types or [],
                "legacy_success_counts_are_authoritative": False,
                "old_path_classification": (
                    "final evidence/citation counts are subordinate to "
                    "ControllerEvidenceLedger custody"
                ),
            },
        },
    }


def _trace(
    *,
    admission_used: bool = True,
    ledger_status: str = "legacy_gap_observed",
    custody_complete: bool = False,
) -> dict[str, Any]:
    return {
        **_admission(used=admission_used),
        "active_source_class_recovery_eligible": admission_used,
        "active_source_class_recovery_used": admission_used,
        "active_source_class_recovery_execution_attempted": admission_used,
        "active_source_class_recovery_result_count": 0,
        "recovered_accepted_url_count": 0,
        "final_selected_authority_evidence_count": 0,
        "source_survival_final_evidence_official_or_canonical_count": 2,
        "source_survival_final_citation_official_or_canonical_count": 1,
        CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY: _ledger_trace(
            status=ledger_status,
            custody_complete=custody_complete,
            legacy_gap_types=(
                [
                    "final_evidence_or_citation_without_candidate_passport_custody",
                    "final_evidence_or_citation_without_final_selected_authority_evidence",
                ]
                if ledger_status == "legacy_gap_observed"
                else []
            ),
        ),
    }


def test_ag74c_export_counts_are_observational_until_ledger_controller_complete() -> None:
    packet = build_official_canonical_recovery_visibility_export(_trace())
    rendered = format_official_canonical_recovery_diagnostics_markdown(packet)

    assert packet["final_evidence_official_or_canonical_count"] == 2
    assert packet["final_citation_official_or_canonical_count"] == 1
    assert packet["final_evidence_observed"] is True
    assert packet["final_citation_observed"] is True
    assert packet["final_evidence_citation_custody_owner"] == (
        "ControllerEvidenceLedger"
    )
    assert packet["final_evidence_citation_custody_status"] == (
        "legacy_gap_observed"
    )
    assert packet["final_evidence_citation_custody_complete"] is False
    assert packet["legacy_gap_observed"] is True
    assert packet["aggregate_success_counts_are_authoritative_for_custody"] is False
    assert packet["aggregate_success_custody_interpretation"] == (
        "legacy_gap_observed_counts_remain_observational"
    )
    assert "`final_evidence_citation_custody_status`: legacy_gap_observed" in rendered
    assert "`legacy_gap_observed`: true" in rendered


def test_ag74c_controller_complete_is_only_exported_custody_completion() -> None:
    legacy_gap = build_official_canonical_recovery_visibility_export(_trace())
    missing_disposition = build_official_canonical_recovery_visibility_export(
        _trace(
            ledger_status="missing_controller_disposition",
            custody_complete=False,
        )
    )
    complete = build_official_canonical_recovery_visibility_export(
        _trace(
            ledger_status="controller_complete",
            custody_complete=True,
        )
    )

    assert legacy_gap["final_evidence_citation_custody_complete"] is False
    assert missing_disposition["final_evidence_citation_custody_complete"] is False
    assert complete["final_evidence_citation_custody_status"] == "controller_complete"
    assert complete["final_evidence_citation_custody_complete"] is True
    assert complete["aggregate_success_custody_interpretation"] == (
        "custody_complete_by_controller_evidence_ledger"
    )


def test_ag74c_admission_not_used_does_not_override_ledger_gap() -> None:
    packet = build_official_canonical_recovery_visibility_export(
        _trace(admission_used=False)
    )

    assert packet["final_evidence_survival_status"] == "visible"
    assert packet["final_citation_survival_status"] == "visible"
    assert packet["next_failure_layer"] == "admission_not_used"
    assert packet["next_failure_layer_custody_interpretation"] == (
        "recovery_lane_observation_not_controller_custody_status"
    )
    assert packet["final_evidence_citation_custody_status"] == (
        "legacy_gap_observed"
    )
    assert packet["legacy_gap_observed"] is True


def test_ag74c_runtime_projection_refreshes_export_with_ledger_and_preserves_outputs() -> None:
    final_top_evidence = [
        {
            "source_id": 1,
            "url": "https://www.irs.gov/newsroom/example",
            "source_tier": "official",
            "source_class": "official_current_rules",
        }
    ]
    original_final_top_evidence = copy.deepcopy(final_top_evidence)
    execution_trace = {
        **_admission(used=False),
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
        "source_survival_final_evidence_official_or_canonical_count": 1,
        "source_survival_final_citation_official_or_canonical_count": 1,
        "final_answer_source_ids_used": ["1"],
    }

    returned = attach_passive_runtime_projection_traces(
        execution_trace,
        recovered_passages=[],
        final_top_evidence=final_top_evidence,
    )
    export = returned[OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY][
        "OfficialCanonicalRecoveryVisibility"
    ]

    assert returned is execution_trace
    assert final_top_evidence == original_final_top_evidence
    assert returned["final_answer_source_ids_used"] == ["1"]
    assert export["controller_evidence_ledger_available"] is True
    assert export["final_evidence_citation_custody_status"] == (
        returned[CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY]["ControllerEvidenceLedger"][
            "final_evidence_citation_custody"
        ]["status"]
    )
    assert (
        returned[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY
        ]["OfficialCanonicalRecoveryVisibility"]
        == export
    )


def test_ag74c_static_subordinates_aggregate_success_path_without_protected_drift() -> None:
    export_source = _EXPORT_PATH.read_text(encoding="utf-8")
    assembly_source = _ASSEMBLY_PATH.read_text(encoding="utf-8")
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    export_imports = {
        node.module
        for node in ast.walk(ast.parse(export_source))
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert "core.controller_evidence_ledger" in export_imports
    assert "aggregate_success_counts_are_authoritative_for_custody" in export_source
    assert "next_failure_layer_custody_interpretation" in export_source
    assert "build_official_canonical_recovery_visibility_trace" in assembly_source
    assert "build_controller_evidence_ledger_trace" not in orchestrator_source
    for forbidden in (
        "select_providers",
        "provider_depth",
        "linkup",
        "source_classifier",
        "author_prompt",
        "ask_model",
        "final_answer(",
        "scrutineer",
    ):
        assert forbidden not in export_source.casefold()
