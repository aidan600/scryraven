"""Sanitized forced-corridor classification for AuthorityLifecycle traces.

This module consumes already-built lifecycle traces. It does not retrieve,
rank, route providers, build prompts, cite sources, or affect final answers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

AUTHORITY_LIFECYCLE_FORCED_CORRIDOR_CLASSIFICATION_SCHEMA_VERSION = (
    "authority_lifecycle_forced_corridor_classification_ag69f_v1"
)

_EXECUTION_BLOCKER_KIND = "recovery_execution_blocked"


def classify_authority_lifecycle_forced_corridor(
    lifecycle_trace: Mapping[str, Any] | None,
    *,
    corridor_name: str,
) -> dict[str, Any]:
    """Return a compact lifecycle packet for one forced authority corridor."""

    trace = _mapping(lifecycle_trace)
    authority = _authority(trace)
    action = _mapping(authority.get("recovery_action"))
    execution = _mapping(authority.get("execution_state"))
    candidate_fit = _mapping(authority.get("candidate_fit"))
    blockers = _list_of_mappings(authority.get("explicit_blockers"))
    projections = _list_of_mappings(authority.get("projections"))
    selected_evidence = _list_of_mappings(
        candidate_fit.get("selected_authority_evidence")
    )
    structured_rejections = _list_of_mappings(
        candidate_fit.get("structured_rejections")
    )
    execution_blockers = [
        blocker
        for blocker in blockers
        if blocker.get("kind") == _EXECUTION_BLOCKER_KIND
    ]
    projection_used_as_control_input = any(
        projection.get("control_input") is True for projection in projections
    ) or trace.get("authority_lifecycle_projection_used_as_control_input") is True
    terminal_paths = _terminal_paths(
        authority=authority,
        action=action,
        execution=execution,
        blockers=blockers,
        selected_evidence=selected_evidence,
    )
    violations = _forbidden_state_codes(
        authority=authority,
        action=action,
        execution=execution,
        candidate_fit=candidate_fit,
        blockers=blockers,
        projections=projections,
        selected_evidence=selected_evidence,
        structured_rejections=structured_rejections,
        terminal_paths=terminal_paths,
        projection_used_as_control_input=projection_used_as_control_input,
    )
    remaining_failure_layer = _remaining_failure_layer(
        authority=authority,
        action=action,
        execution=execution,
        candidate_fit=candidate_fit,
        blockers=blockers,
        selected_evidence=selected_evidence,
        structured_rejections=structured_rejections,
        terminal_paths=terminal_paths,
        violations=violations,
    )

    return {
        "schema_version": (
            AUTHORITY_LIFECYCLE_FORCED_CORRIDOR_CLASSIFICATION_SCHEMA_VERSION
        ),
        "corridor_name": _text(corridor_name) or "forced_corridor",
        "required_authority": _text(authority.get("required_authority")),
        "requirement_id": _text(authority.get("requirement_id")),
        "existing_evidence_fit": _text(authority.get("existing_evidence_fit")),
        "lower_tier_context_state": _text(
            authority.get("lower_tier_context_state")
        ),
        "recovery_needed": _text(authority.get("recovery_needed")),
        "recovery_action_state": _recovery_action_state(action),
        "terminal_stop_state": _text(authority.get("terminal_stop_state")),
        "weak_corpus_state": _text(authority.get("weak_corpus_state")),
        "execution_state": _text(execution.get("state")) or "not_requested",
        "execution_attempted": execution.get("state") == "attempted",
        "structured_execution_blocker": (
            dict(execution_blockers[0]) if execution_blockers else None
        ),
        "candidate_acquisition_state": _text(
            authority.get("candidate_acquisition_state")
        ),
        "candidate_return_status": _candidate_return_status(
            authority,
            candidate_fit,
        ),
        "candidate_fit_state": _text(candidate_fit.get("fit_state")),
        "selected_authority_evidence": [dict(item) for item in selected_evidence],
        "structured_candidate_rejections": [
            dict(item) for item in structured_rejections
        ],
        "final_evidence_state": _text(authority.get("final_evidence_state")),
        "final_evidence_explanation": _text(
            authority.get("final_evidence_explanation")
        ),
        "citation_eligibility_projection": _text(
            authority.get("citation_eligibility_state")
        ),
        "final_posture": _text(authority.get("final_posture")),
        "terminal_paths": terminal_paths,
        "exactly_one_terminal_path": len(terminal_paths) == 1,
        "forbidden_state_codes": violations,
        "lifecycle_contract_valid": not violations,
        "remaining_failure_layer": remaining_failure_layer,
        "projection_used_as_control_input": projection_used_as_control_input,
        "classification_compact": True,
        "sanitized": True,
        "protected_surface": {
            "provider_routing_changed": False,
            "provider_selection_changed": False,
            "retrieval_ranking_filtering_changed": False,
            "prompt_changed": False,
            "citation_behavior_changed": False,
            "final_answer_behavior_changed": False,
            "author_behavior_changed": False,
            "live_validation_used": False,
        },
    }


def _authority(trace: Mapping[str, Any]) -> dict[str, Any]:
    authority = trace.get("authority_lifecycle")
    if isinstance(authority, Mapping):
        return dict(authority)
    return dict(trace)


def _terminal_paths(
    *,
    authority: Mapping[str, Any],
    action: Mapping[str, Any],
    execution: Mapping[str, Any],
    blockers: list[Mapping[str, Any]],
    selected_evidence: list[Mapping[str, Any]],
) -> list[str]:
    requirement_id = _text(authority.get("requirement_id"))
    paths: list[str] = []
    if (
        authority.get("satisfaction_state") == "satisfied"
        and authority.get("existing_evidence_fit") == "authority_satisfying"
    ):
        paths.append("satisfied_by_existing_evidence")
    if any(_controller_hard_blocker(blocker, requirement_id) for blocker in blockers):
        paths.append("controller_hard_blocker")
    if (
        action.get("approved") is True
        and action.get("requirement_id") == requirement_id
        and execution.get("state") == "attempted"
    ):
        paths.append("approved_action_executed")
    if (
        authority.get("final_posture") == "insufficient_partial"
        and not any(
            _controller_hard_blocker(blocker, requirement_id) for blocker in blockers
        )
        and not selected_evidence
    ):
        paths.append("controller_insufficient_partial_posture")
    return paths


def _forbidden_state_codes(
    *,
    authority: Mapping[str, Any],
    action: Mapping[str, Any],
    execution: Mapping[str, Any],
    candidate_fit: Mapping[str, Any],
    blockers: list[Mapping[str, Any]],
    projections: list[Mapping[str, Any]],
    selected_evidence: list[Mapping[str, Any]],
    structured_rejections: list[Mapping[str, Any]],
    terminal_paths: list[str],
    projection_used_as_control_input: bool,
) -> list[str]:
    requirement_id = _text(authority.get("requirement_id"))
    has_blocker = any(_controller_hard_blocker(blocker, requirement_id) for blocker in blockers)
    action_approved = action.get("approved") is True
    execution_state = _text(execution.get("state")) or "not_requested"
    candidate_returned = _candidate_returned(authority, candidate_fit)
    final_evidence_state = _text(authority.get("final_evidence_state"))
    codes: list[str] = []

    if authority.get("required", True) is True:
        if len(terminal_paths) == 0:
            codes.append("missing_terminal_path")
        elif len(terminal_paths) > 1:
            codes.append("multiple_terminal_paths")
    if _int(authority.get("recovery_query_count")) > 0 and not (
        action_approved or has_blocker
    ):
        codes.append("queries_without_action_or_blocker")
    if action_approved and execution_state == "approved_pending_execution" and not has_blocker:
        codes.append("approved_action_without_execution_or_blocker")
    if (
        authority.get("admission_used") is True
        and authority.get("eligible") is True
        and execution_state != "attempted"
        and not has_blocker
    ):
        codes.append("admitted_eligible_without_execution_or_blocker")
    if (
        authority.get("terminal_stop_state") == "approved"
        and authority.get("recovery_needed") == "required"
        and not has_blocker
        and execution_state != "attempted"
    ):
        codes.append("terminal_stop_preempts_required_recovery")
    if (
        authority.get("weak_corpus_state") == "owns_path"
        and authority.get("recovery_needed") == "required"
        and not has_blocker
        and execution_state != "attempted"
    ):
        codes.append("weak_corpus_preempts_authority_recovery")
    if candidate_returned and not _has_fit_or_rejection(
        candidate_fit,
        structured_rejections,
    ):
        codes.append("candidate_returned_without_fit_or_rejection")
    if (
        _int(execution.get("recovered_result_count")) > 0
        and final_evidence_state == "not_visible"
        and not _text(authority.get("final_evidence_explanation"))
    ):
        codes.append("recovered_results_not_visible_without_explanation")
    if (
        projection_used_as_control_input
        or any(projection.get("control_input") is True for projection in projections)
    ):
        codes.append("projection_used_as_control_input")
    if (
        authority.get("satisfaction_state") == "satisfied"
        and authority.get("existing_evidence_fit") != "authority_satisfying"
        and not selected_evidence
    ):
        codes.append("satisfaction_without_authority_evidence_fit")
    if (
        authority.get("existing_evidence_fit") == "lower_tier_context_only"
        and authority.get("lower_tier_context_state") != "absent"
        and authority.get("satisfaction_state") == "satisfied"
    ):
        codes.append("lower_tier_context_not_authority_satisfaction")
    return codes


def _remaining_failure_layer(
    *,
    authority: Mapping[str, Any],
    action: Mapping[str, Any],
    execution: Mapping[str, Any],
    candidate_fit: Mapping[str, Any],
    blockers: list[Mapping[str, Any]],
    selected_evidence: list[Mapping[str, Any]],
    structured_rejections: list[Mapping[str, Any]],
    terminal_paths: list[str],
    violations: list[str],
) -> str:
    if violations:
        if "approved_action_without_execution_or_blocker" in violations:
            return "executor_handoff_failed"
        if "candidate_returned_without_fit_or_rejection" in violations:
            return "candidate_fit_visibility_layer"
        if "recovered_results_not_visible_without_explanation" in violations:
            return "final_evidence_visibility_layer"
        if (
            "terminal_stop_preempts_required_recovery" in violations
            or "weak_corpus_preempts_authority_recovery" in violations
        ):
            return "controller_arbitration_layer"
        return "lifecycle_invariant_failure"
    if terminal_paths == ["satisfied_by_existing_evidence"]:
        return "none_existing_authority_satisfied"
    if any(_controller_hard_blocker(blocker, _text(authority.get("requirement_id"))) for blocker in blockers):
        return "blocked_by_controller_lifecycle"
    if terminal_paths == ["controller_insufficient_partial_posture"]:
        return "controller_insufficient_partial"
    execution_state = _text(execution.get("state")) or "not_requested"
    if action.get("approved") is True and execution_state == "blocked":
        return "blocked_by_controller_lifecycle"
    if action.get("approved") is True and execution_state != "attempted":
        return "executor_handoff_failed"
    if execution_state != "attempted":
        return "recovery_not_requested_or_not_needed"
    candidate_status = _candidate_return_status(authority, candidate_fit)
    if candidate_status in {"no_candidates", "zero_candidates"}:
        return "candidate_acquisition_or_provider_result_layer"
    fit_state = _text(candidate_fit.get("fit_state"))
    if fit_state in {"rejected_with_reason", "no_matching_source_fit"}:
        return "candidate_fit_visibility_layer"
    if fit_state == "matched_not_selected":
        return "final_evidence_visibility_layer"
    if selected_evidence and authority.get("final_evidence_state") == "visible":
        if authority.get("citation_eligibility_state") == "eligible":
            return "none_lifecycle_succeeded"
        return "citation_survival_or_source_claim_fit"
    if structured_rejections:
        return "candidate_fit_visibility_layer"
    return "none_lifecycle_succeeded"


def _recovery_action_state(action: Mapping[str, Any]) -> str:
    if not action:
        return "none"
    if action.get("approved") is True:
        return "approved"
    return "not_approved"


def _candidate_return_status(
    authority: Mapping[str, Any],
    candidate_fit: Mapping[str, Any],
) -> str | None:
    return _text(
        candidate_fit.get("candidate_return_status")
        or authority.get("candidate_return_status")
    )


def _candidate_returned(
    authority: Mapping[str, Any],
    candidate_fit: Mapping[str, Any],
) -> bool:
    return (
        _candidate_return_status(authority, candidate_fit) == "candidates_returned"
        or _int(candidate_fit.get("accepted_url_count")) > 0
        or _int(authority.get("accepted_url_count")) > 0
    )


def _has_fit_or_rejection(
    candidate_fit: Mapping[str, Any],
    structured_rejections: list[Mapping[str, Any]],
) -> bool:
    fit_state = _text(candidate_fit.get("fit_state"))
    if fit_state in {
        "matched_selected",
        "matched_not_selected",
        "no_matching_source_fit",
    }:
        return True
    if fit_state == "rejected_with_reason":
        return bool(structured_rejections or candidate_fit.get("rejection_reasons"))
    return False


def _controller_hard_blocker(
    blocker: Mapping[str, Any],
    requirement_id: str | None,
) -> bool:
    return (
        blocker.get("requirement_id") == requirement_id
        and blocker.get("hard") is True
        and blocker.get("owner") in {"controller", "controller/lifecycle"}
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    return text or None


def _int(value: Any) -> int:
    if value is None or isinstance(value, bool):
        return 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "AUTHORITY_LIFECYCLE_FORCED_CORRIDOR_CLASSIFICATION_SCHEMA_VERSION",
    "classify_authority_lifecycle_forced_corridor",
]
