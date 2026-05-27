from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.authority_lifecycle_compatibility_fields import (
    AUTHORITY_LIFECYCLE_COMPATIBILITY_FIELDS,
)
from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
    sync_authority_lifecycle_execution_from_source_class_trace,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    build_controller_loop_spine_result,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"
_VISIBILITY_PATH = _ROOT / "core" / "recovered_evidence_visibility.py"
_EXECUTION_PATH = _ROOT / "core" / "authority_lifecycle_execution.py"
_CANDIDATE_VISIBILITY_PATH = (
    _ROOT / "core" / "authority_lifecycle_candidate_visibility.py"
)


def _authority_trace(
    *,
    result_count: int = 1,
    accepted_url_count: int = 1,
) -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id="official_current_rules",
        required_authority="official_current_rules",
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=("agency official current rules",),
        required_source_classes=("official_current_rules",),
        recovery_action_allowed=True,
        terminal_stop_approved=True,
        weak_corpus_recovery_used=True,
        corpus_weak=True,
    ).to_trace_fields()
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=result_count,
        recovered_result_count=result_count,
        accepted_url_count=accepted_url_count,
    )
    trace.update(
        {
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_missing_classes": [
                "official_current_rules"
            ],
            "active_source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:"
                "official_current_rules"
            ),
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": ["official_current_rules"],
                "allowed_action": True,
            },
        }
    )
    return trace


def _official_source() -> dict[str, Any]:
    return {
        "title": "Agency official current rules",
        "url": "https://agency.example/current-rules",
        "text": "Official current rules fixture.",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
    }


def _existing_secondary() -> dict[str, Any]:
    return {
        "title": "Existing secondary context",
        "url": "https://analysis.example/context",
        "text": "Secondary context fixture.",
        "source_tier": "secondary",
    }


def test_ag69e_terminal_stop_cannot_control_when_lifecycle_allows_recovery() -> None:
    trace = _authority_trace()
    trace["active_source_class_recovery_eligible"] = False
    trace["active_source_class_recovery_official_canonical_admitted"] = False
    trace["active_source_class_recovery_action_envelope"] = {
        "action_type": "recover_missing_source_class",
        "required_source_class": [],
        "allowed_action": False,
    }
    spine = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": {"action_name": STOP_INSUFFICIENT_WITH_CAVEAT},
            "recommended_action_name": STOP_INSUFFICIENT_WITH_CAVEAT,
        },
        source_class_lifecycle_trace=trace,
    )

    assert trace["authority_lifecycle_required_recovery_allowed"] is True
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert spine.trace_packet["blocked_or_skipped_actions"][
        STOP_INSUFFICIENT_WITH_CAVEAT
    ] == "authority_lifecycle_preserved_required_recovery"


def test_ag69e_weak_corpus_cannot_control_when_lifecycle_allows_recovery() -> None:
    trace = _authority_trace()
    trace["active_source_class_recovery_eligible"] = False
    trace["active_source_class_recovery_blockers"] = [
        "blocked_by_weak_corpus_recovery"
    ]
    spine = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": {"action_name": RECOVER_WEAK_CORPUS},
            "recommended_action_name": RECOVER_WEAK_CORPUS,
        },
        source_class_lifecycle_trace=trace,
        weak_corpus_lifecycle_trace={"approved": True, "reason": "weak", "blockers": []},
    )

    assert trace["authority_lifecycle_weak_corpus_may_own_path"] is False
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert spine.weak_corpus_executor_dispatched is False


def test_ag69e_legacy_execution_and_candidate_return_fields_are_projections() -> None:
    trace = build_authority_runtime_arbitration(
        requirement_id="official_current_rules",
        required_authority="official_current_rules",
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=("agency official current rules",),
        required_source_classes=("official_current_rules",),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace["active_source_class_recovery_execution_attempted"] = True
    trace["candidate_return_status"] = "candidates_returned"
    trace["active_source_class_recovery_result_count"] = 0
    trace["accepted_url_count"] = 0

    sync_authority_lifecycle_execution_from_source_class_trace(trace)

    assert trace["authority_lifecycle"]["execution_state"]["state"] == (
        "approved_pending_execution"
    )
    assert trace["active_source_class_recovery_execution_attempted"] is False

    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=0,
        recovered_result_count=0,
        accepted_url_count=0,
    )
    sync_authority_lifecycle_execution_from_source_class_trace(trace)

    assert trace["authority_lifecycle_execution_attempted"] is True
    assert trace["authority_lifecycle"]["candidate_return_status"] == "no_candidates"
    assert trace["authority_lifecycle"]["candidate_fit"][
        "candidate_return_status"
    ] == "no_candidates"


def test_ag69e_legacy_candidate_counters_do_not_create_lifecycle_truth() -> None:
    trace = _authority_trace(result_count=0, accepted_url_count=0)
    trace["accepted_url_count"] = 99
    trace["recovered_result_count"] = 99
    trace["recovered_visibility_source_fit_candidate_count"] = 99

    _final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_existing_secondary()],
        recovered_passages=[],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())

    assert trace["authority_lifecycle_candidate_return_status"] == "no_candidates"
    assert trace["authority_lifecycle"]["candidate_fit"]["fit_state"] == (
        "no_matching_source_fit"
    )
    assert trace["authority_lifecycle"]["candidate_fit"]["accepted_url_count"] == 0


def test_ag69e_recovered_visibility_uses_lifecycle_not_legacy_local_gates() -> None:
    trace = _authority_trace()
    trace.update(
        {
            "active_source_class_recovery_used": False,
            "active_source_class_recovery_provider_role": "ordinary",
            "active_source_class_recovery_reason": "ordinary_retrieval",
            "active_source_class_recovery_blockers": [
                "blocked_by_weak_corpus_recovery"
            ],
            "active_source_class_recovery_skip_reason": "already_attempted",
            "active_source_class_recovery_attempt_count": 2,
            "recovery_source_quality_status": "secondary_only",
        }
    )

    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_existing_secondary()],
        recovered_passages=[_official_source()],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )

    assert decision.used is True
    assert final[-1]["url"] == "https://agency.example/current-rules"
    assert trace["authority_lifecycle"]["candidate_fit"]["fit_state"] == (
        "matched_selected"
    )


def test_ag69e_visibility_export_remains_diagnostic_not_control() -> None:
    trace = _authority_trace()
    _final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_existing_secondary()],
        recovered_passages=[_official_source()],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())
    export = build_official_canonical_recovery_visibility_export(trace)

    assert export["diagnostic_only"] is True
    assert export["behavior_changed"] is False
    assert export["recovered_candidate_source_fit_status"] == "matched_selected"
    assert trace["authority_lifecycle_projection_used_as_control_input"] is False


def test_ag69e_retained_legacy_fields_have_named_consumers_and_retirement_rule() -> None:
    assert AUTHORITY_LIFECYCLE_COMPATIBILITY_FIELDS
    for field in AUTHORITY_LIFECYCLE_COMPATIBILITY_FIELDS:
        assert field.replacement.startswith("authority_lifecycle")
        assert field.classification
        assert field.named_consumers
        assert field.deletion_or_promotion_criterion.startswith("Retire after")
        assert field.control_input is False


def test_ag69e_no_trace_projection_export_field_is_marked_control_input() -> None:
    trace = _authority_trace()
    projections = trace["authority_lifecycle"].get("projections") or []

    assert trace["authority_lifecycle_projection_used_as_control_input"] is False
    assert all(item.get("control_input") is not True for item in projections)
    assert all(
        field.control_input is False
        for field in AUTHORITY_LIFECYCLE_COMPATIBILITY_FIELDS
    )


def test_ag69e_static_guard_keeps_projection_control_out_of_runtime_authority() -> None:
    for path in (
        _SPINE_PATH,
        _VISIBILITY_PATH,
        _EXECUTION_PATH,
        _CANDIDATE_VISIBILITY_PATH,
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imports.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert imports.isdisjoint(
            {
                "openai",
                "requests",
                "core.prompts",
                "core.routing",
                "core.search_providers",
                "core.author",
                "core.economist",
            }
        )

    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert pipeline_source.count("execute_source_class_recovery_action(") == 1
    assert pipeline_source.count("apply_recovered_evidence_visibility_boundary(") == 1
    assert "authority_lifecycle_compatibility_fields" not in pipeline_source
    assert "standard mileage rate" not in pipeline_source.casefold()
    assert "taxable maximum" not in pipeline_source.casefold()
