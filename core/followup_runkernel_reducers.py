"""Mechanical follow-up reducer helpers used only by RunKernel.

These helpers validate already-authorized follow-up fixture bindings, build
projections from RunKernel-owned canonical state, and derive fixture ledger
observations. They do not own policy and they do not mutate RunState.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.evidence_ledger_intake_adapter import (
    build_evidence_ledger_intake_observation_from_admission_review,
)
from core.followup_author_gate_runtime import FOLLOWUP_AUTHOR_GATE_MODE
from core.followup_author_observation_runtime import FOLLOWUP_AUTHOR_OBSERVATION_MODE
from core.followup_final_answer_packet_runtime import FOLLOWUP_FINAL_ANSWER_PACKET_MODE
from core.followup_fixture_boundaries import (
    FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
    FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS,
    FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
)
from core.followup_provider_job_execution_runtime import (
    FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND,
    FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
)
from core.followup_sufficiency_recheck_runtime import FOLLOWUP_SUFFICIENCY_RECHECK_MODE


class FollowupRunKernelReducerError(ValueError):
    """Raised by mechanical helpers for RunKernel to translate."""


FOLLOWUP_NO_LIVE_FALSE_FLAGS = FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS[1:]
FOLLOWUP_EXECUTION_FALSE_FLAGS = (
    "live_provider_call_executed",
    "search_executed",
    "retrieval_executed",
    "fetch_executed",
    "model_called",
    "evidence_ledger_mutated",
)
FOLLOWUP_PROVIDER_JOB_EXECUTION_FALSE_FLAGS = (
    *FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    "evidence_ledger_mutated",
    "sufficiency_judgment_rechecked",
    "final_answer_packet_updated",
    *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
)
FOLLOWUP_INTAKE_FALSE_FLAGS = (
    *FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    "sufficiency_judgment_rechecked",
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    "final_answer_packet_updated",
    "final_answer_behavior_changed",
    "author_prose_behavior_changed",
    "citation_behavior_changed",
)
FOLLOWUP_RECHECK_FALSE_FLAGS = (
    *FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    "final_answer_packet_updated",
    "final_answer_behavior_changed",
    "author_prose_behavior_changed",
    "citation_behavior_changed",
)
FOLLOWUP_PACKET_FALSE_FLAGS = (
    *FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
)
FOLLOWUP_AUTHOR_GATE_FALSE_FLAGS = (
    *FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    "sufficiency_judgment_rechecked",
    "final_answer_packet_rebuilt",
    "final_answer_packet_updated",
    *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
)
FOLLOWUP_AUTHOR_OBSERVATION_FALSE_FLAGS = (
    *FOLLOWUP_NO_LIVE_FALSE_FLAGS,
    *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    "sufficiency_judgment_rechecked",
    "final_answer_packet_rebuilt",
    "final_answer_packet_updated",
    *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
    "final_text_included",
)

AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE = (
    "ag96i3m2_admission_review_followup_intake"
)


def require_followup_flags_false(
    flags: Mapping[str, Any],
    flag_names: Sequence[str],
    *,
    context: str,
) -> None:
    for flag in flag_names:
        if flags.get(flag) is not False:
            raise FollowupRunKernelReducerError(
                f"{context} requires {flag}=False"
            )


def followup_sealed_candidate(
    followup_state: Mapping[str, Any],
    candidate_id: str,
) -> Mapping[str, Any]:
    expected = _followup_token(candidate_id, limit=160)
    expected = expected.casefold().replace("-", "_").replace(" ", "_") if expected else ""
    for candidate in followup_state.get("sealed_candidates", []) or []:
        if not isinstance(candidate, Mapping):
            continue
        actual = _followup_token(candidate.get("candidate_id"), limit=160)
        actual = actual.casefold().replace("-", "_").replace(" ", "_") if actual else ""
        if actual == expected:
            return candidate
    raise FollowupRunKernelReducerError(
        f"follow-up fixture execution candidate {candidate_id!r} is not sealed"
    )


def validate_followup_execution_action_binding(
    *,
    action_inputs: Mapping[str, Any],
    execution_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "fixture_execution_mode",
    ):
        if execution_state.get(binding_field) != action_inputs.get(binding_field):
            raise FollowupRunKernelReducerError(
                "follow-up execution observation "
                f"{binding_field} does not match authorized action"
            )
    if action_inputs.get("fixture_execution_mode") != "fixture_only":
        raise FollowupRunKernelReducerError(
            "follow-up fixture execution action must be bound to fixture_only mode"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up fixture execution action must keep provider execution unlicensed"
        )
    if list(execution_state.get("requirement_ids", []) or []) != list(
        action_inputs.get("requirement_ids", []) or []
    ):
        raise FollowupRunKernelReducerError(
            "follow-up execution observation requirement_ids does not match authorized action"
        )
    action_job_kind = action_inputs.get("provider_job_kind")
    execution_job_kind = execution_state.get("provider_job_kind")
    if (action_job_kind or execution_job_kind) and action_job_kind != execution_job_kind:
        raise FollowupRunKernelReducerError(
            "follow-up execution observation provider_job_kind does not match authorized action"
        )


def validate_followup_provider_job_execution_action_binding(
    *,
    action_inputs: Mapping[str, Any],
    execution_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "execution_mode",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "authorized_query_ref",
        "authorized_query",
    ):
        if execution_state.get(binding_field) != action_inputs.get(binding_field):
            raise FollowupRunKernelReducerError(
                "follow-up provider-job execution observation "
                f"{binding_field} does not match authorized action"
            )
    if action_inputs.get("execution_mode") != FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        raise FollowupRunKernelReducerError(
            "follow-up provider-job execution action must be offline live-shaped"
        )
    if action_inputs.get("provider_job_kind") != FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND:
        raise FollowupRunKernelReducerError(
            "follow-up provider-job execution action kind is not allowlisted"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up provider-job execution must keep provider execution unlicensed"
        )
    if not (
        action_inputs.get("authorized_query_ref")
        or action_inputs.get("authorized_query")
    ):
        raise FollowupRunKernelReducerError(
            "follow-up provider-job execution requires authorized query/ref"
        )
    for list_field in ("requirement_ids", "expected_source_classes"):
        if list(execution_state.get(list_field, []) or []) != list(
            action_inputs.get(list_field, []) or []
        ):
            raise FollowupRunKernelReducerError(
                "follow-up provider-job execution observation "
                f"{list_field} does not match authorized action"
            )
    if _contains_sensitive_payload_field(execution_state):
        raise FollowupRunKernelReducerError(
            "follow-up provider-job execution observation contains raw/private payload fields"
        )


def validate_followup_evidence_intake_action_binding(
    *,
    action_inputs: Mapping[str, Any],
    execution_state: Mapping[str, Any],
    intake_state: Mapping[str, Any],
) -> None:
    binding_fields = [
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "result_status",
        "bridge_only",
    ]
    if action_inputs.get("execution_mode") == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        binding_fields.extend(
            [
                "execution_mode",
                "authorized_query_ref",
                "authorized_query",
            ]
        )
    else:
        binding_fields.append("fixture_execution_mode")
    for binding_field in binding_fields:
        if intake_state.get(binding_field) != action_inputs.get(binding_field):
            raise FollowupRunKernelReducerError(
                "follow-up evidence intake observation "
                f"{binding_field} does not match authorized action"
            )
        if intake_state.get(binding_field) != execution_state.get(binding_field):
            raise FollowupRunKernelReducerError(
                "follow-up evidence intake observation "
                f"{binding_field} does not match execution state"
            )
    if list(intake_state.get("requirement_ids", []) or []) != list(
        action_inputs.get("requirement_ids", []) or []
    ):
        raise FollowupRunKernelReducerError(
            "follow-up evidence intake observation requirement_ids do not match "
            "authorized action"
        )
    if list(intake_state.get("requirement_ids", []) or []) != list(
        execution_state.get("requirement_ids", []) or []
    ):
        raise FollowupRunKernelReducerError(
            "follow-up evidence intake observation requirement_ids do not match "
            "execution state"
        )
    if list(intake_state.get("expected_source_classes", []) or []) != list(
        action_inputs.get("expected_source_classes", []) or []
    ):
        raise FollowupRunKernelReducerError(
            "follow-up evidence intake observation expected_source_classes do not "
            "match authorized action"
        )
    if list(intake_state.get("expected_source_classes", []) or []) != list(
        execution_state.get("expected_source_classes", []) or []
    ):
        raise FollowupRunKernelReducerError(
            "follow-up evidence intake observation expected_source_classes do not "
            "match execution state"
        )
    for action_field, state_field in (
        ("followup_execution_id", "execution_id"),
        ("execution_id", "execution_id"),
        ("followup_execution_observation_id", "observation_id"),
    ):
        if intake_state.get(action_field) != action_inputs.get(action_field):
            raise FollowupRunKernelReducerError(
                "follow-up evidence intake observation "
                f"{action_field} does not match authorized action"
            )
        if intake_state.get(action_field) != execution_state.get(state_field):
            raise FollowupRunKernelReducerError(
                "follow-up evidence intake observation "
                f"{action_field} does not match execution state"
            )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up evidence intake action must keep provider execution unlicensed"
        )
    intake_mode = action_inputs.get("evidence_ledger_intake_mode")
    if intake_mode == AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE:
        _validate_ag96i3m2_reduced_intake_binding(
            action_inputs=action_inputs,
            intake_state=intake_state,
        )
    elif action_inputs.get("execution_mode") == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        if intake_mode != "bounded_provider_job_offline_followup_intake":
            raise FollowupRunKernelReducerError(
                "follow-up evidence intake action must consume offline provider-job state"
            )
    else:
        if action_inputs.get("fixture_execution_mode") != "fixture_only":
            raise FollowupRunKernelReducerError(
                "follow-up evidence intake action must be bound to fixture_only mode"
            )
        if intake_mode != "fixture_only_followup_intake":
            raise FollowupRunKernelReducerError(
                "follow-up evidence intake action must be fixture-only"
            )


def validate_followup_sufficiency_recheck_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_recheck_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_evidence_intake_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "result_status",
        "bridge_only",
        "execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "evidence_ledger_projection_digest",
    ):
        if observed_recheck_state.get(binding_field) != action_inputs.get(binding_field):
            raise FollowupRunKernelReducerError(
                "follow-up sufficiency recheck observation "
                f"{binding_field} does not match authorized action"
            )
    if action_inputs.get("execution_mode") == "fixture_only" and (
        observed_recheck_state.get("fixture_execution_mode")
        != action_inputs.get("fixture_execution_mode")
    ):
        raise FollowupRunKernelReducerError(
            "follow-up sufficiency recheck observation fixture_execution_mode "
            "does not match authorized action"
        )
    if followup_token_list(
        observed_recheck_state.get("requirement_ids")
    ) != followup_token_list(action_inputs.get("requirement_ids")):
        raise FollowupRunKernelReducerError(
            "follow-up sufficiency recheck observation requirement_ids do not "
            "match authorized action"
        )
    if followup_token_list(
        observed_recheck_state.get("expected_source_classes")
    ) != followup_token_list(action_inputs.get("expected_source_classes")):
        raise FollowupRunKernelReducerError(
            "follow-up sufficiency recheck observation expected_source_classes do "
            "not match authorized action"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up sufficiency recheck action must keep provider unlicensed"
        )
    if action_inputs.get("sufficiency_recheck_mode") != (
        FOLLOWUP_SUFFICIENCY_RECHECK_MODE
    ):
        raise FollowupRunKernelReducerError(
            "follow-up sufficiency recheck action must be fixture-only"
        )
    if action_inputs.get("final_answer_packet_deferred") is not True:
        raise FollowupRunKernelReducerError(
            "follow-up sufficiency recheck action must defer FinalAnswerPacket"
        )
    if action_inputs.get("author_activation_allowed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up sufficiency recheck action must keep Author closed"
        )
    if action_inputs.get("citation_behavior_changed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up sufficiency recheck action must not change citations"
        )


def validate_followup_final_answer_packet_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_packet_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_evidence_intake_observation_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_sufficiency_recheck_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "final_answer_packet_mode",
        "evidence_ledger_projection_digest",
        "sufficiency_judgment_digest",
        "followup_sufficiency_recheck_digest",
    ):
        if observed_packet_state.get(binding_field) != action_inputs.get(
            binding_field
        ):
            raise FollowupRunKernelReducerError(
                "follow-up FinalAnswerPacket observation "
                f"{binding_field} does not match authorized action"
            )
    if action_inputs.get("execution_mode") == "fixture_only" and (
        observed_packet_state.get("fixture_execution_mode")
        != action_inputs.get("fixture_execution_mode")
    ):
        raise FollowupRunKernelReducerError(
            "follow-up FinalAnswerPacket observation fixture_execution_mode "
            "does not match authorized action"
        )
    if followup_token_list(
        observed_packet_state.get("requirement_ids")
    ) != followup_token_list(action_inputs.get("requirement_ids")):
        raise FollowupRunKernelReducerError(
            "follow-up FinalAnswerPacket observation requirement_ids do not "
            "match authorized action"
        )
    if followup_token_list(
        observed_packet_state.get("expected_source_classes")
    ) != followup_token_list(action_inputs.get("expected_source_classes")):
        raise FollowupRunKernelReducerError(
            "follow-up FinalAnswerPacket observation expected_source_classes do "
            "not match authorized action"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up FinalAnswerPacket action must keep provider unlicensed"
        )
    if action_inputs.get("final_answer_packet_mode") != (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    ):
        raise FollowupRunKernelReducerError(
            "follow-up FinalAnswerPacket action must be fixture-only"
        )
    if action_inputs.get("author_activation_allowed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up FinalAnswerPacket action must keep Author closed"
        )
    if action_inputs.get("citation_rendering_changed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up FinalAnswerPacket action must not render citations"
        )
    if action_inputs.get("product_answer_behavior_changed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up FinalAnswerPacket action must not change product answers"
        )
    if action_inputs.get("live_validation_not_run") is not True:
        raise FollowupRunKernelReducerError(
            "follow-up FinalAnswerPacket action must not run live validation"
        )


def validate_followup_author_gate_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_gate_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_final_answer_packet_id",
        "packet_preparation_id",
        "packet_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "final_answer_packet_mode",
        "author_gate_mode",
        "final_answer_packet_digest",
        "final_answer_authority_projection_digest",
    ):
        if observed_gate_state.get(binding_field) != action_inputs.get(
            binding_field
        ):
            raise FollowupRunKernelReducerError(
                "follow-up Author gate observation "
                f"{binding_field} does not match authorized action"
            )
    if followup_token_list(
        observed_gate_state.get("requirement_ids")
    ) != followup_token_list(action_inputs.get("requirement_ids")):
        raise FollowupRunKernelReducerError(
            "follow-up Author gate observation requirement_ids do not match "
            "authorized action"
        )
    if followup_token_list(
        observed_gate_state.get("expected_source_classes")
    ) != followup_token_list(action_inputs.get("expected_source_classes")):
        raise FollowupRunKernelReducerError(
            "follow-up Author gate observation expected_source_classes do not "
            "match authorized action"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up Author gate action must keep provider unlicensed"
        )
    if action_inputs.get("final_answer_packet_mode") != (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    ):
        raise FollowupRunKernelReducerError(
            "follow-up Author gate action must consume fixture-only packet"
        )
    if action_inputs.get("author_gate_mode") != FOLLOWUP_AUTHOR_GATE_MODE:
        raise FollowupRunKernelReducerError(
            "follow-up Author gate action must be fixture-only"
        )
    for flag in (
        "author_activation_allowed",
        "author_executor_invoked",
        "author_prompt_changed",
        "author_prose_behavior_changed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
    ):
        if action_inputs.get(flag) is not False:
            raise FollowupRunKernelReducerError(
                f"follow-up Author gate action must keep {flag}=False"
            )
    if action_inputs.get("author_execution_deferred") is not True:
        raise FollowupRunKernelReducerError(
            "follow-up Author gate action must defer Author execution"
        )
    if action_inputs.get("live_validation_not_run") is not True:
        raise FollowupRunKernelReducerError(
            "follow-up Author gate action must not run live validation"
        )


def validate_followup_author_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_author_state: Mapping[str, Any],
) -> None:
    for binding_field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_final_answer_packet_id",
        "packet_preparation_id",
        "followup_author_gate_id",
        "author_gate_id",
        "packet_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "final_answer_packet_mode",
        "author_gate_mode",
        "fixture_author_observation_mode",
        "final_answer_packet_digest",
        "final_answer_authority_projection_digest",
        "followup_author_gate_digest",
    ):
        if observed_author_state.get(binding_field) != action_inputs.get(
            binding_field
        ):
            raise FollowupRunKernelReducerError(
                "follow-up Author observation "
                f"{binding_field} does not match authorized action"
            )
    if followup_token_list(
        observed_author_state.get("requirement_ids")
    ) != followup_token_list(action_inputs.get("requirement_ids")):
        raise FollowupRunKernelReducerError(
            "follow-up Author observation requirement_ids do not match "
            "authorized action"
        )
    if followup_token_list(
        observed_author_state.get("expected_source_classes")
    ) != followup_token_list(action_inputs.get("expected_source_classes")):
        raise FollowupRunKernelReducerError(
            "follow-up Author observation expected_source_classes do not match "
            "authorized action"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise FollowupRunKernelReducerError(
            "follow-up Author observation action must keep provider unlicensed"
        )
    if action_inputs.get("final_answer_packet_mode") != (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    ):
        raise FollowupRunKernelReducerError(
            "follow-up Author observation action must consume fixture-only packet"
        )
    if action_inputs.get("author_gate_mode") != FOLLOWUP_AUTHOR_GATE_MODE:
        raise FollowupRunKernelReducerError(
            "follow-up Author observation action must consume fixture-only gate"
        )
    if action_inputs.get("fixture_author_observation_mode") != (
        FOLLOWUP_AUTHOR_OBSERVATION_MODE
    ):
        raise FollowupRunKernelReducerError(
            "follow-up Author observation action must be fixture-only"
        )
    for flag in (
        "author_activation_allowed",
        "author_executor_invoked",
        "model_called",
        "author_prompt_changed",
        "author_prose_behavior_changed",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
        "final_text_included",
    ):
        if action_inputs.get(flag) is not False:
            raise FollowupRunKernelReducerError(
                f"follow-up Author observation action must keep {flag}=False"
            )
    if action_inputs.get("author_execution_deferred") is not True:
        raise FollowupRunKernelReducerError(
            "follow-up Author observation action must defer Author execution"
        )
    if action_inputs.get("live_validation_not_run") is not True:
        raise FollowupRunKernelReducerError(
            "follow-up Author observation action must not run live validation"
        )


def build_followup_authorization_projection(
    *,
    followup_state: Mapping[str, Any],
    execution_gate: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupAuthorization",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": followup_state.get("schema_version"),
        "consumption_id": followup_state.get("consumption_id"),
        "checkpoint_id": followup_state.get("checkpoint_id"),
        "run_id": followup_state.get("run_id"),
        "mode": followup_state.get("mode"),
        "input_checkpoint_hash": followup_state.get("input_checkpoint_hash"),
        "validation_status": _mapping(followup_state.get("validation")).get(
            "status"
        ),
        "status": followup_state.get("status"),
        "selected_authorization_candidate_ids": followup_state.get(
            "selected_authorization_candidate_ids",
            [],
        ),
        "denied_candidate_ids": followup_state.get("denied_candidate_ids", []),
        "sealed_candidate_count": followup_state.get("sealed_candidate_count", 0),
        "selected_mode_insufficient": followup_state.get(
            "selected_mode_insufficient"
        ),
        "needs_balanced_or_deep": followup_state.get("needs_balanced_or_deep"),
        "needs_deep": followup_state.get("needs_deep"),
        "execution_gate": dict(execution_gate),
        "behavior_boundary_flags": dict(behavior_boundary_flags),
    }


def build_followup_execution_projection(
    *,
    execution_state: Mapping[str, Any],
    execution_gate: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    budget_semantics: Mapping[str, Any],
) -> dict[str, Any]:
    execution_mode = (
        execution_state.get("execution_mode")
        or execution_state.get("fixture_execution_mode")
    )
    return {
        "owner": execution_state.get("owner") or "RunKernel.FollowupFixtureExecution",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": execution_state.get("schema_version"),
        "execution_id": execution_state.get("execution_id"),
        "observation_id": execution_state.get("observation_id"),
        "run_id": execution_state.get("run_id"),
        "checkpoint_id": execution_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": execution_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": execution_state.get("sealed_candidate_id"),
        "provider_job_kind": execution_state.get("provider_job_kind"),
        "component_id": execution_state.get("component_id"),
        "source_obligation_id": execution_state.get("source_obligation_id"),
        "requirement_ids": execution_state.get("requirement_ids", []),
        "expected_source_classes": execution_state.get("expected_source_classes", []),
        "result_status": execution_state.get("result_status"),
        "execution_mode": execution_mode,
        "fixture_execution_mode": execution_state.get("fixture_execution_mode"),
        "authorized_query_ref": execution_state.get("authorized_query_ref"),
        "authorized_query": execution_state.get("authorized_query"),
        "offline_live_shaped_execution": execution_state.get(
            "offline_live_shaped_execution"
        ),
        "adapter_result_injected": execution_state.get("adapter_result_injected"),
        "live_validation_not_run": execution_state.get("live_validation_not_run"),
        "bridge_only": execution_state.get("bridge_only"),
        "final_evidence_satisfied": execution_state.get("final_evidence_satisfied"),
        "citation_eligible": execution_state.get("citation_eligible"),
        "evidence_ledger_intake_deferred": execution_state.get(
            "evidence_ledger_intake_deferred"
        ),
        "budget_semantics": dict(budget_semantics),
        "execution_gate": dict(execution_gate),
        "behavior_boundary_flags": dict(behavior_boundary_flags),
    }


def build_followup_evidence_intake_projection(
    *,
    intake_state: Mapping[str, Any],
    ledger_observation: Mapping[str, Any],
    ledger_projection: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupEvidenceIntake",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": intake_state.get("schema_version"),
        "intake_id": intake_state.get("intake_id"),
        "observation_id": intake_state.get("observation_id"),
        "run_id": intake_state.get("run_id"),
        "checkpoint_id": intake_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": intake_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": intake_state.get("sealed_candidate_id"),
        "followup_execution_id": intake_state.get("followup_execution_id"),
        "execution_id": intake_state.get("execution_id"),
        "followup_execution_observation_id": intake_state.get(
            "followup_execution_observation_id"
        ),
        "provider_job_kind": intake_state.get("provider_job_kind"),
        "component_id": intake_state.get("component_id"),
        "source_obligation_id": intake_state.get("source_obligation_id"),
        "requirement_ids": intake_state.get("requirement_ids", []),
        "expected_source_classes": intake_state.get("expected_source_classes", []),
        "result_status": intake_state.get("result_status"),
        "bridge_only": intake_state.get("bridge_only"),
        "execution_mode": intake_state.get("execution_mode"),
        "authorized_query_ref": intake_state.get("authorized_query_ref"),
        "authorized_query": intake_state.get("authorized_query"),
        "evidence_ledger_intake_mode": intake_state.get(
            "evidence_ledger_intake_mode"
        ),
        "runtime_evidence_intake_occurred": intake_state.get(
            "runtime_evidence_intake_occurred"
        ),
        "ag96i3m1_adapter_status": _mapping(
            intake_state.get("ag96i3m1_adapter_projection")
        ).get("intake_status"),
        "ag96i3m2_admission_review_candidate": _mapping(
            intake_state.get("ag96i3m2_admission_review_candidate")
        ),
        "ag96i3m2_evidence_ledger_intake_binding": _mapping(
            intake_state.get("ag96i3m2_evidence_ledger_intake_binding")
        ),
        "evidence_ledger_observation_id": ledger_observation.get("observation_id"),
        "evidence_ledger_candidate_count": ledger_projection.get("candidate_count"),
        "evidence_ledger_requirement_count": ledger_projection.get(
            "requirement_count"
        ),
        "evidence_ledger_custody_record_count": ledger_projection.get(
            "custody_record_count"
        ),
        "source_obligation_satisfied": intake_state.get(
            "source_obligation_satisfied"
        ),
        "final_evidence_satisfied": intake_state.get("final_evidence_satisfied"),
        "citation_eligible": intake_state.get("citation_eligible"),
        "author_activation_allowed": intake_state.get("author_activation_allowed"),
        "final_answer_packet_updated": intake_state.get("final_answer_packet_updated"),
        "sufficiency_judgment_recheck_deferred": intake_state.get(
            "sufficiency_judgment_recheck_deferred"
        ),
        "behavior_boundary_flags": dict(behavior_boundary_flags),
    }


def _validate_ag96i3m2_reduced_intake_binding(
    *,
    action_inputs: Mapping[str, Any],
    intake_state: Mapping[str, Any],
) -> None:
    if intake_state.get("evidence_ledger_intake_mode") != (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    ):
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 follow-up intake observation mode mismatch"
        )
    expected_candidate = _mapping(
        action_inputs.get("ag96i3m2_admission_review_candidate")
    )
    expected_binding = _mapping(
        action_inputs.get("ag96i3m2_evidence_ledger_intake_binding")
    )
    observed_candidate = _mapping(
        intake_state.get("ag96i3m2_admission_review_candidate")
    )
    observed_binding = _mapping(
        intake_state.get("ag96i3m2_evidence_ledger_intake_binding")
    )
    payload_candidate = ag96i3m2_admission_review_authorization_projection(
        intake_state.get("ag96i3m2_admission_review_candidate_payload")
    )
    payload_binding = ag96i3m2_intake_binding_authorization_projection(
        intake_state.get("ag96i3m2_evidence_ledger_intake_binding_payload")
    )
    if not expected_candidate or not expected_binding:
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 follow-up intake requires authorized candidate and binding"
        )
    if observed_candidate != expected_candidate or payload_candidate != expected_candidate:
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 admission-review candidate does not match authorized action"
        )
    if observed_binding != expected_binding or payload_binding != expected_binding:
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 EvidenceLedgerIntakeBinding does not match authorized action"
        )
    _validate_ag96i3m2_candidate_binding_pair(
        candidate_projection=observed_candidate,
        binding_projection=observed_binding,
    )
    adapter_projection = _mapping(intake_state.get("ag96i3m1_adapter_projection"))
    if adapter_projection.get("accepted") is not True:
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 follow-up intake requires accepted AG-96I3M1 adapter result"
        )
    if intake_state.get("runtime_evidence_intake_occurred") is not True:
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 follow-up intake must record runtime EvidenceLedger intake"
        )


def build_followup_sufficiency_recheck_projection(
    *,
    recheck_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupSufficiencyRecheck",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": recheck_state.get("schema_version"),
        "recheck_id": recheck_state.get("recheck_id"),
        "observation_id": recheck_state.get("observation_id"),
        "run_id": recheck_state.get("run_id"),
        "checkpoint_id": recheck_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": recheck_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": recheck_state.get("sealed_candidate_id"),
        "followup_execution_id": recheck_state.get("followup_execution_id"),
        "execution_id": recheck_state.get("execution_id"),
        "followup_execution_observation_id": recheck_state.get(
            "followup_execution_observation_id"
        ),
        "followup_evidence_intake_id": recheck_state.get(
            "followup_evidence_intake_id"
        ),
        "intake_id": recheck_state.get("intake_id"),
        "followup_evidence_intake_observation_id": recheck_state.get(
            "followup_evidence_intake_observation_id"
        ),
        "provider_job_kind": recheck_state.get("provider_job_kind"),
        "component_id": recheck_state.get("component_id"),
        "source_obligation_id": recheck_state.get("source_obligation_id"),
        "requirement_ids": recheck_state.get("requirement_ids", []),
        "expected_source_classes": recheck_state.get("expected_source_classes", []),
        "result_status": recheck_state.get("result_status"),
        "bridge_only": recheck_state.get("bridge_only"),
        "execution_mode": recheck_state.get("execution_mode"),
        "evidence_ledger_intake_mode": recheck_state.get(
            "evidence_ledger_intake_mode"
        ),
        "sufficiency_recheck_mode": recheck_state.get("sufficiency_recheck_mode"),
        "evidence_ledger_projection_digest": recheck_state.get(
            "evidence_ledger_projection_digest"
        ),
        "evidence_ledger_observation_id": recheck_state.get(
            "evidence_ledger_observation_id"
        ),
        "evidence_ledger_counts": recheck_state.get(
            "evidence_ledger_counts",
            {},
        ),
        "ag96i3m2_admission_review_candidate": _mapping(
            recheck_state.get("ag96i3m2_admission_review_candidate")
        ),
        "ag96i3m2_evidence_ledger_intake_binding": _mapping(
            recheck_state.get("ag96i3m2_evidence_ledger_intake_binding")
        ),
        "official_current_custody_status": recheck_state.get(
            "official_current_custody_status",
            {},
        ),
        "source_requirement_status_summary": recheck_state.get(
            "source_requirement_status_summary",
            {},
        ),
        "fixture_sufficiency_posture": recheck_state.get(
            "fixture_sufficiency_posture"
        ),
        "sufficiency_judgment_ref": recheck_state.get(
            "sufficiency_judgment_ref",
            {},
        ),
        "final_answer_packet_deferred": recheck_state.get(
            "final_answer_packet_deferred"
        ),
        "author_activation_allowed": recheck_state.get(
            "author_activation_allowed"
        ),
        "citation_behavior_changed": recheck_state.get("citation_behavior_changed"),
        "citation_eligible": recheck_state.get("citation_eligible"),
        "live_validation_not_run": recheck_state.get("live_validation_not_run"),
        "behavior_boundary_flags": dict(behavior_boundary_flags),
    }


def build_final_answer_authority_projection(
    *,
    packet_state: Mapping[str, Any],
    packet_projection: Mapping[str, Any],
    author_payload_ref: Mapping[str, Any],
    citation_eligible_source_ids: Sequence[Any],
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FinalAnswerPacket",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "packet_id": packet_projection.get("packet_id"),
        "readiness_status": packet_projection.get("readiness_status"),
        "readiness_reasons": packet_projection.get("readiness_reasons", []),
        "author_payload_ref": dict(author_payload_ref),
        "citation_eligible_source_ids": list(citation_eligible_source_ids),
        "citation_eligibility_refs": packet_state.get(
            "citation_eligibility_refs",
            [],
        ),
        "missing_source_obligation_count": len(
            packet_state.get("missing_required_obligations", []) or []
        ),
        "partial_source_obligation_count": len(
            packet_state.get("partial_obligations", []) or []
        ),
        "satisfied_source_obligation_count": len(
            packet_state.get("satisfied_obligations", []) or []
        ),
        "source_bound_numeric_unknown_count": len(
            packet_state.get("source_bound_unknowns", []) or []
        ),
        "mandatory_caveat_count": len(
            packet_state.get("mandatory_caveats", []) or []
        ),
        "prohibited_upgrade_count": len(
            packet_state.get("prohibited_upgrades", []) or []
        ),
        "author_authority_payload_ref": packet_state.get(
            "packet_authority_payload",
            {},
        ),
        "final_answer_packet_prepared": True,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "citation_rendering_changed": False,
        "citation_formatter_invoked": False,
        "product_answer_behavior_changed": False,
        "live_validation_not_run": True,
        "followup_packet_preparation_id": packet_state.get("packet_preparation_id"),
        "followup_recheck_id": packet_state.get("recheck_id"),
    }


def build_followup_final_answer_packet_projection(
    *,
    packet_state: Mapping[str, Any],
    packet_projection: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupFinalAnswerPacket",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": packet_state.get("schema_version"),
        "packet_preparation_id": packet_state.get("packet_preparation_id"),
        "observation_id": packet_state.get("observation_id"),
        "run_id": packet_state.get("run_id"),
        "checkpoint_id": packet_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": packet_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": packet_state.get("sealed_candidate_id"),
        "followup_execution_id": packet_state.get("followup_execution_id"),
        "execution_id": packet_state.get("execution_id"),
        "followup_execution_observation_id": packet_state.get(
            "followup_execution_observation_id"
        ),
        "followup_evidence_intake_id": packet_state.get(
            "followup_evidence_intake_id"
        ),
        "intake_id": packet_state.get("intake_id"),
        "followup_evidence_intake_observation_id": packet_state.get(
            "followup_evidence_intake_observation_id"
        ),
        "followup_sufficiency_recheck_id": packet_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": packet_state.get("recheck_id"),
        "followup_sufficiency_recheck_observation_id": packet_state.get(
            "followup_sufficiency_recheck_observation_id"
        ),
        "provider_job_kind": packet_state.get("provider_job_kind"),
        "component_id": packet_state.get("component_id"),
        "source_obligation_id": packet_state.get("source_obligation_id"),
        "requirement_ids": packet_state.get("requirement_ids", []),
        "expected_source_classes": packet_state.get("expected_source_classes", []),
        "final_answer_packet_mode": packet_state.get("final_answer_packet_mode"),
        "packet_id": packet_projection.get("packet_id"),
        "readiness_status": packet_projection.get("readiness_status"),
        "final_evidence_refs": packet_state.get("final_evidence_refs", []),
        "citation_eligibility_refs": packet_state.get(
            "citation_eligibility_refs",
            [],
        ),
        "mandatory_caveats": packet_state.get("mandatory_caveats", []),
        "prohibited_upgrades": packet_state.get("prohibited_upgrades", []),
        "missing_required_obligations": packet_state.get(
            "missing_required_obligations",
            [],
        ),
        "partial_obligations": packet_state.get("partial_obligations", []),
        "satisfied_obligations": packet_state.get("satisfied_obligations", []),
        "source_bound_unknowns": packet_state.get("source_bound_unknowns", []),
        "unresolved_conflicts": packet_state.get("unresolved_conflicts", []),
        "final_answer_packet_prepared": True,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "citation_rendering_changed": False,
        "citation_formatter_invoked": False,
        "product_answer_behavior_changed": False,
        "live_validation_not_run": True,
        "behavior_boundary_flags": dict(behavior_boundary_flags),
        "canonical_final_answer_packet_ref": {
            "owner": "RunKernel.FinalAnswerPacket",
            "canonical_state": True,
            "packet_id": packet_projection.get("packet_id"),
            "projection_stage": final_answer_packet_stage,
        },
    }


def build_followup_author_gate_projection(
    *,
    gate_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupAuthorGate",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": gate_state.get("schema_version"),
        "author_gate_id": gate_state.get("author_gate_id"),
        "observation_id": gate_state.get("observation_id"),
        "run_id": gate_state.get("run_id"),
        "checkpoint_id": gate_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": gate_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": gate_state.get("sealed_candidate_id"),
        "followup_execution_id": gate_state.get("followup_execution_id"),
        "execution_id": gate_state.get("execution_id"),
        "followup_evidence_intake_id": gate_state.get("followup_evidence_intake_id"),
        "intake_id": gate_state.get("intake_id"),
        "followup_sufficiency_recheck_id": gate_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": gate_state.get("recheck_id"),
        "followup_final_answer_packet_id": gate_state.get(
            "followup_final_answer_packet_id"
        ),
        "packet_preparation_id": gate_state.get("packet_preparation_id"),
        "packet_id": gate_state.get("packet_id"),
        "provider_job_kind": gate_state.get("provider_job_kind"),
        "component_id": gate_state.get("component_id"),
        "source_obligation_id": gate_state.get("source_obligation_id"),
        "requirement_ids": gate_state.get("requirement_ids", []),
        "expected_source_classes": gate_state.get("expected_source_classes", []),
        "final_answer_packet_mode": gate_state.get("final_answer_packet_mode"),
        "author_gate_mode": gate_state.get("author_gate_mode"),
        "final_answer_packet_digest": gate_state.get("final_answer_packet_digest"),
        "final_answer_authority_projection_digest": gate_state.get(
            "final_answer_authority_projection_digest"
        ),
        "author_gate_decision": gate_state.get("author_gate_decision"),
        "author_gate_reason": gate_state.get("author_gate_reason"),
        "packet_authority_consumed": True,
        "answer_readiness_posture": gate_state.get("answer_readiness_posture", {}),
        "author_payload_ref": gate_state.get("author_payload_ref", {}),
        "final_answer_authority_payload_ref": gate_state.get(
            "final_answer_authority_payload_ref",
            {},
        ),
        "mandatory_caveats": gate_state.get("mandatory_caveats", []),
        "prohibited_upgrades": gate_state.get("prohibited_upgrades", []),
        "missing_required_obligations": gate_state.get(
            "missing_required_obligations",
            [],
        ),
        "partial_obligations": gate_state.get("partial_obligations", []),
        "satisfied_obligations": gate_state.get("satisfied_obligations", []),
        "source_bound_unknowns": gate_state.get("source_bound_unknowns", []),
        "unresolved_conflicts": gate_state.get("unresolved_conflicts", []),
        "citation_eligibility_refs": gate_state.get("citation_eligibility_refs", []),
        "citation_eligible_source_ids": gate_state.get(
            "citation_eligible_source_ids",
            [],
        ),
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_executor_invoked": False,
        "author_prompt_changed": False,
        "author_prose_behavior_changed": False,
        "citation_rendering_changed": False,
        "citation_formatter_invoked": False,
        "product_answer_behavior_changed": False,
        "final_text_included": False,
        "live_validation_not_run": True,
        "behavior_boundary_flags": dict(behavior_boundary_flags),
        "canonical_final_answer_packet_ref": {
            "owner": "RunKernel.FinalAnswerPacket",
            "canonical_state": True,
            "packet_id": gate_state.get("packet_id"),
            "projection_stage": final_answer_packet_stage,
        },
    }


def build_followup_author_observation_projection(
    *,
    author_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
    followup_author_gate_stage: str,
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupAuthorObservation",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": author_state.get("schema_version"),
        "author_observation_id": author_state.get("author_observation_id"),
        "observation_id": author_state.get("observation_id"),
        "run_id": author_state.get("run_id"),
        "checkpoint_id": author_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": author_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": author_state.get("sealed_candidate_id"),
        "followup_execution_id": author_state.get("followup_execution_id"),
        "execution_id": author_state.get("execution_id"),
        "followup_evidence_intake_id": author_state.get("followup_evidence_intake_id"),
        "intake_id": author_state.get("intake_id"),
        "followup_sufficiency_recheck_id": author_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": author_state.get("recheck_id"),
        "followup_final_answer_packet_id": author_state.get(
            "followup_final_answer_packet_id"
        ),
        "packet_preparation_id": author_state.get("packet_preparation_id"),
        "followup_author_gate_id": author_state.get("followup_author_gate_id"),
        "author_gate_id": author_state.get("author_gate_id"),
        "packet_id": author_state.get("packet_id"),
        "provider_job_kind": author_state.get("provider_job_kind"),
        "component_id": author_state.get("component_id"),
        "source_obligation_id": author_state.get("source_obligation_id"),
        "requirement_ids": author_state.get("requirement_ids", []),
        "expected_source_classes": author_state.get("expected_source_classes", []),
        "final_answer_packet_mode": author_state.get("final_answer_packet_mode"),
        "author_gate_mode": author_state.get("author_gate_mode"),
        "fixture_author_observation_mode": author_state.get(
            "fixture_author_observation_mode"
        ),
        "final_answer_packet_digest": author_state.get("final_answer_packet_digest"),
        "final_answer_authority_projection_digest": author_state.get(
            "final_answer_authority_projection_digest"
        ),
        "followup_author_gate_digest": author_state.get("followup_author_gate_digest"),
        "author_output_observed": True,
        "packet_authority_consumed": True,
        "packet_authority_compliance_status": author_state.get(
            "packet_authority_compliance_status"
        ),
        "citation_compliance_status": author_state.get(
            "citation_compliance_status"
        ),
        "caveat_compliance_status": author_state.get("caveat_compliance_status"),
        "prohibited_upgrade_compliance_status": author_state.get(
            "prohibited_upgrade_compliance_status"
        ),
        "source_bound_unknown_compliance_status": author_state.get(
            "source_bound_unknown_compliance_status"
        ),
        "missing_obligation_compliance_status": author_state.get(
            "missing_obligation_compliance_status"
        ),
        "citation_eligible_source_ids": author_state.get(
            "citation_eligible_source_ids",
            [],
        ),
        "cited_source_ids": author_state.get("cited_source_ids", []),
        "unauthorized_citation_source_ids": author_state.get(
            "unauthorized_citation_source_ids",
            [],
        ),
        "missing_mandatory_caveats": author_state.get(
            "missing_mandatory_caveats",
            [],
        ),
        "prohibited_upgrade_violations": author_state.get(
            "prohibited_upgrade_violations",
            [],
        ),
        "unacknowledged_source_bound_unknowns": author_state.get(
            "unacknowledged_source_bound_unknowns",
            [],
        ),
        "unacknowledged_missing_obligations": author_state.get(
            "unacknowledged_missing_obligations",
            [],
        ),
        "report_hash": author_state.get("report_hash"),
        "report_length": author_state.get("report_length"),
        "final_text_hash": author_state.get("final_text_hash"),
        "final_text_length": author_state.get("final_text_length"),
        "final_text_included": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_executor_invoked": False,
        "model_called": False,
        "author_prompt_changed": False,
        "author_prose_behavior_changed": False,
        "citation_rendering_changed": False,
        "citation_formatter_invoked": False,
        "product_answer_behavior_changed": False,
        "live_validation_not_run": True,
        "behavior_boundary_flags": dict(behavior_boundary_flags),
        "canonical_final_answer_packet_ref": {
            "owner": "RunKernel.FinalAnswerPacket",
            "canonical_state": True,
            "packet_id": author_state.get("packet_id"),
            "projection_stage": final_answer_packet_stage,
        },
        "canonical_followup_author_gate_ref": {
            "owner": "RunKernel.FollowupAuthorGate",
            "canonical_state": True,
            "author_gate_id": author_state.get("author_gate_id"),
            "projection_stage": followup_author_gate_stage,
        },
    }


def build_followup_evidence_intake_ledger_observation(
    *,
    intake_state: Mapping[str, Any],
    execution_state: Mapping[str, Any],
) -> dict[str, Any]:
    if intake_state.get("evidence_ledger_intake_mode") == (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    ):
        adapter_result = build_evidence_ledger_intake_observation_from_admission_review(
            admission_review_candidate=intake_state.get(
                "ag96i3m2_admission_review_candidate_payload"
            ),
            binding=intake_state.get(
                "ag96i3m2_evidence_ledger_intake_binding_payload"
            ),
        )
        if not adapter_result.accepted or adapter_result.observation is None:
            blockers = [
                blocker.value for blocker in adapter_result.blocker_codes
            ]
            raise FollowupRunKernelReducerError(
                "AG-96I3M2 adapter rejected follow-up EvidenceLedger intake: "
                + ", ".join(blockers)
            )
        return adapter_result.observation.to_dict()

    execution_mode = (
        execution_state.get("execution_mode")
        or execution_state.get("fixture_execution_mode")
        or "fixture_only"
    )
    provider_job_offline = execution_mode == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
    summary = _mapping(
        execution_state.get("sanitized_candidate_summary")
        or execution_state.get("sanitized_fixture_result_summary")
    )
    requirement_id = followup_intake_requirement_id(execution_state)
    expected_source_classes = followup_expected_source_classes(execution_state)
    required_source_class = followup_required_source_class(expected_source_classes)
    candidate_id = followup_intake_candidate_id(execution_state)
    disposition = followup_intake_candidate_disposition(
        result_status=execution_state.get("result_status"),
        bridge_only=bool(execution_state.get("bridge_only")),
        source_class=summary.get("source_class"),
        expected_source_classes=expected_source_classes,
        currentness_signal=summary.get("currentness_signal"),
        readable_status=summary.get("readable_status"),
        fetchable_status=summary.get("fetchable_status"),
        aggregate_only=bool(summary.get("aggregate_only")),
    )
    observation_source = (
        "followup_provider_job_offline_evidence_intake"
        if provider_job_offline
        else "followup_fixture_evidence_intake"
    )
    origin_ref = (
        f"followup_provider_job_execution:{execution_state.get('execution_id')}"
        if provider_job_offline
        else f"followup_fixture_execution:{execution_state.get('execution_id')}"
    )
    link_reason = (
        "followup_provider_job_execution_binding"
        if provider_job_offline
        else "followup_fixture_execution_binding"
    )
    provider_name = (
        summary.get("provider_name")
        if provider_job_offline
        else "followup_fixture"
    )
    query_ref = (
        execution_state.get("authorized_query_ref")
        or summary.get("authorized_query_ref")
        or (
            "fixture_only_followup_intake"
            if not provider_job_offline
            else "authorized_query_ref_absent"
        )
    )
    candidate = {
        "candidate_id": candidate_id,
        "url": summary.get("url"),
        "title": summary.get("title") or summary.get("summary"),
        "domain": summary.get("domain"),
        "source_label": (
            (
                "offline provider-job follow-up intake "
                if provider_job_offline
                else "fixture follow-up intake "
            )
            + f"{execution_state.get('component_id')} "
            f"{execution_state.get('source_obligation_id')} "
            f"{execution_state.get('sealed_candidate_id')}"
        ),
        "provider_name": provider_name,
        "provider_role": execution_state.get("provider_job_kind"),
        "retrieval_pass_id": execution_state.get("observation_id"),
        "query_ref": query_ref,
        "action_ref": execution_state.get("execution_id"),
        "source_tier": summary.get("source_tier")
        or followup_default_source_tier(required_source_class),
        "source_class": summary.get("source_class") or "unknown",
        "currentness_signal": summary.get("currentness_signal") or "fixture_current",
        "readable_status": summary.get("readable_status")
        or (
            "readable"
            if execution_state.get("result_status") == "fixture_success"
            else "not_readable"
        ),
        "fetchable_status": summary.get("fetchable_status")
        or (
            "fetchable"
            if execution_state.get("result_status") == "fixture_success"
            else "not_fetchable"
        ),
        "disposition": disposition,
        "record_kind": "fact",
        "requirement_id": requirement_id,
        "eligible_for_stronger_obligation": (
            disposition == "accepted"
            and bool(
                summary.get("eligible_for_stronger_obligation")
                or summary.get("source_tier") in {"official", "primary", "canonical"}
            )
        ),
        "final_evidence_eligible": False,
        "reason": followup_intake_candidate_reason(
            result_status=execution_state.get("result_status"),
            bridge_only=bool(execution_state.get("bridge_only")),
            disposition=disposition,
            provider_job_offline=provider_job_offline,
        ),
        "followup_execution_id": execution_state.get("execution_id"),
        "followup_execution_observation_id": execution_state.get("observation_id"),
        "sealed_candidate_id": execution_state.get("sealed_candidate_id"),
        "component_id": execution_state.get("component_id"),
        "source_obligation_id": execution_state.get("source_obligation_id"),
        "provider_job_kind": execution_state.get("provider_job_kind"),
        "authorized_query_ref": execution_state.get("authorized_query_ref"),
        "authorized_query": execution_state.get("authorized_query"),
    }
    intake_metadata = {
        "schema_version": intake_state.get("schema_version"),
        "run_id": execution_state.get("run_id"),
        "checkpoint_id": execution_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": execution_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": execution_state.get("sealed_candidate_id"),
        "followup_execution_id": execution_state.get("execution_id"),
        "followup_execution_observation_id": execution_state.get("observation_id"),
        "provider_job_kind": execution_state.get("provider_job_kind"),
        "component_id": execution_state.get("component_id"),
        "source_obligation_id": execution_state.get("source_obligation_id"),
        "requirement_ids": list(execution_state.get("requirement_ids", []) or []),
        "expected_source_classes": list(expected_source_classes),
        "result_status": execution_state.get("result_status"),
        "bridge_only": bool(execution_state.get("bridge_only")),
        "execution_mode": execution_mode,
    }
    if provider_job_offline:
        intake_metadata.update(
            {
                "offline_live_shaped_execution": True,
                "adapter_result_injected": True,
                "live_provider_call_executed": False,
                "authorized_query_ref": execution_state.get("authorized_query_ref"),
                "authorized_query": execution_state.get("authorized_query"),
            }
        )
    else:
        intake_metadata["fixture_only_provenance"] = {
            "origin": "ag96i2b_followup_fixture_execution",
            "intake_bridge": "ag96i2c_followup_evidence_ledger_intake",
            "fixture_only": True,
            "live_provider_result": False,
            "provider_job_executor_connected": False,
        }
    payload = {
        "observation_id": f"ledger:{execution_state.get('execution_id')}",
        "observation_source": observation_source,
        "requirements": [
            {
                "requirement_id": requirement_id,
                "requirement_kind": followup_requirement_kind(required_source_class),
                "origin_ref": origin_ref,
                "required_source_class": required_source_class,
                "required_source_tier": followup_default_source_tier(
                    required_source_class
                ),
                "required_currentness": summary.get("required_currentness")
                or summary.get("currentness_signal")
                or "current",
            }
        ],
        "candidates": [candidate],
        "requirement_links": [
            {
                "requirement_id": requirement_id,
                "candidate_id": candidate_id,
                "link_reason": link_reason,
                "link_status": disposition,
            }
        ],
    }
    if provider_job_offline:
        payload["followup_provider_job_intake"] = intake_metadata
    else:
        payload["followup_fixture_intake"] = intake_metadata
    return payload


def followup_evidence_intake_outcome(
    ledger_observation: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = list(ledger_observation.get("candidates", []) or [])
    candidate = _mapping(next(iter(candidates), {}))
    disposition = candidate.get("disposition")
    admitted = disposition == "accepted"
    bridge_only = disposition == "contextual"
    if ledger_observation.get("ag96i3m1_intake_adapter"):
        return {
            "intake_status": (
                "admission_review_intake_admitted"
                if admitted
                else "admission_review_intake_rejected"
            ),
            "evidence_ledger_candidate_admitted": admitted,
            "source_obligation_satisfied": admitted,
        }
    return {
        "intake_status": (
            "provider_job_intake_admitted"
            if admitted and _is_provider_job_offline_ledger_observation(ledger_observation)
            else "fixture_intake_admitted"
            if admitted
            else (
                "provider_job_bridge_only_recorded"
                if bridge_only
                and _is_provider_job_offline_ledger_observation(ledger_observation)
                else "fixture_bridge_only_recorded"
                if bridge_only
                else (
                    "provider_job_no_admission_recorded"
                    if _is_provider_job_offline_ledger_observation(ledger_observation)
                    else "fixture_no_admission_recorded"
                )
            )
        ),
        "evidence_ledger_candidate_admitted": admitted,
        "source_obligation_satisfied": admitted,
    }


def followup_intake_requirement_id(execution_state: Mapping[str, Any]) -> str:
    requirement_ids = list(execution_state.get("requirement_ids", []) or [])
    requirement_id = next(iter(requirement_ids), None) or execution_state.get(
        "source_obligation_id"
    )
    text = _followup_token(requirement_id) or "followup_requirement"
    if ":" not in text:
        return f"source_requirement:{text}"
    return text


def followup_intake_candidate_id(execution_state: Mapping[str, Any]) -> str:
    prefix = (
        "followup_provider_job"
        if (
            execution_state.get("execution_mode")
            == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
        )
        else "followup_fixture"
    )
    return _followup_token(
        f"{prefix}:"
        f"{execution_state.get('sealed_candidate_id')}:"
        f"{execution_state.get('execution_id')}"
    )


def followup_expected_source_classes(
    execution_state: Mapping[str, Any],
) -> tuple[str, ...]:
    expected = [
        _followup_token(item)
        for item in list(execution_state.get("expected_source_classes", []) or [])
    ]
    expected = [item for item in expected if item and item != "[redacted]"]
    if expected:
        return tuple(expected)
    job_kind = _followup_token(execution_state.get("provider_job_kind"))
    by_job = {
        "official_current_candidate_acquisition": (
            "official_government",
            "official_current_rules",
        ),
        "legal_current_primary_acquisition": (
            "primary_legal",
            "legal_or_regulatory_text",
        ),
        "canonical_doc_acquisition": ("canonical", "primary_source_documents"),
        "source_bound_numeric_extraction_calculation_support": (
            "sourced_numeric_values",
        ),
        "conflict_currentness_check": ("current_primary_or_official",),
        "reconciliation_support": ("source_family_map",),
        "fetch_read_extract": ("answer_bearing_extract",),
    }
    return by_job.get(job_kind, ("answer_bearing_candidate",))


def followup_required_source_class(expected_source_classes: Sequence[str]) -> str:
    preferred = (
        "official_current_rules",
        "legal_or_regulatory_text",
        "primary_source_documents",
        "current_primary_or_official",
        "sourced_numeric_values",
    )
    for item in preferred:
        if item in expected_source_classes:
            return item
    return next(iter(expected_source_classes), "unknown")


def followup_intake_candidate_disposition(
    *,
    result_status: Any,
    bridge_only: bool,
    source_class: Any,
    expected_source_classes: Sequence[str],
    currentness_signal: Any = None,
    readable_status: Any = None,
    fetchable_status: Any = None,
    aggregate_only: bool = False,
) -> str:
    if bridge_only:
        return "contextual"
    if aggregate_only:
        return "rejected"
    if _followup_token(currentness_signal) in {
        "stale",
        "outdated",
        "historical_only",
        "off_topic",
        "not_current",
    }:
        return "rejected"
    if _followup_token(readable_status) in {
        "unreadable",
        "fetch_failed",
        "not_readable",
        "blocked",
        "unfetchable",
        "no_readable_text",
    }:
        return "rejected"
    if _followup_token(fetchable_status) in {
        "unfetchable",
        "fetch_failed",
        "not_fetchable",
        "blocked",
    }:
        return "rejected"
    if (
        _followup_token(result_status) in {"fixture_success", "candidate_acquired"}
        and _followup_token(source_class) in expected_source_classes
    ):
        return "accepted"
    return "rejected"


def followup_intake_candidate_reason(
    *,
    result_status: Any,
    bridge_only: bool,
    disposition: str,
    provider_job_offline: bool = False,
) -> str:
    if bridge_only:
        return (
            "bridge_only_provider_job_result_not_satisfying"
            if provider_job_offline
            else "bridge_only_fixture_result_not_satisfying"
        )
    success_statuses = {"fixture_success", "candidate_acquired"}
    status = _followup_token(result_status)
    if status in success_statuses and disposition != "accepted":
        return (
            "provider_job_candidate_outside_sealed_contract"
            if provider_job_offline
            else "fixture_success_source_class_outside_sealed_contract"
        )
    if status in success_statuses:
        return (
            "provider_job_offline_followup_evidence_intake"
            if provider_job_offline
            else "fixture_success_followup_evidence_intake"
        )
    return f"{_followup_token(result_status)}_not_admitted_as_satisfying_evidence"


def _is_provider_job_offline_ledger_observation(
    ledger_observation: Mapping[str, Any],
) -> bool:
    return bool(ledger_observation.get("followup_provider_job_intake"))


def followup_default_source_tier(required_source_class: str) -> str | None:
    if required_source_class in {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
    }:
        return "official"
    return None


def followup_requirement_kind(required_source_class: str) -> str:
    if required_source_class in {"official_current_rules", "current_primary_or_official"}:
        return "official_current"
    if required_source_class == "legal_or_regulatory_text":
        return "legal"
    if required_source_class in {"primary_source_documents", "archival_primary_text"}:
        return "canonical"
    return "general"


def followup_token_list(value: Any) -> list[str]:
    if value is None or isinstance(value, str):
        values = [value] if value else []
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = list(value)
    else:
        values = [value]
    out: list[str] = []
    for item in values:
        token = _followup_token(item)
        if token and token not in out:
            out.append(token)
    return out


def ag96i3m2_validate_authorized_intake_materials(
    *,
    action_inputs: Mapping[str, Any],
    admission_review_candidate: Any,
    binding: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_candidate = _mapping(
        action_inputs.get("ag96i3m2_admission_review_candidate")
    )
    expected_binding = _mapping(
        action_inputs.get("ag96i3m2_evidence_ledger_intake_binding")
    )
    observed_candidate = ag96i3m2_admission_review_authorization_projection(
        admission_review_candidate
    )
    observed_binding = ag96i3m2_intake_binding_authorization_projection(binding)
    if not expected_candidate or not expected_binding:
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 follow-up intake requires authorized candidate and binding"
        )
    if observed_candidate != expected_candidate:
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 admission-review candidate does not match authorized action"
        )
    if observed_binding != expected_binding:
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 EvidenceLedgerIntakeBinding does not match authorized action"
        )
    _validate_ag96i3m2_candidate_binding_pair(
        candidate_projection=observed_candidate,
        binding_projection=observed_binding,
    )
    return observed_candidate, observed_binding


def ag96i3m2_admission_review_authorization_projection(value: Any) -> dict[str, Any]:
    candidate = _mapping_or_to_dict(value)
    identity = _mapping(candidate.get("candidate_identity_summary"))
    verification = _mapping(candidate.get("verification_summary"))
    read_summary = _mapping(candidate.get("read_observation_summary"))
    return _compact_mapping(
        {
            "candidate_id": _followup_token(
                candidate.get("candidate_id")
                or candidate.get("admission_review_candidate_id")
            ),
            "observation_id": _followup_token(candidate.get("observation_id")),
            "observation_ref": _clean_text(
                candidate.get("observation_ref")
                or candidate.get("admission_review_candidate_ref"),
                limit=220,
            ),
            "admission_review_status": _followup_token(
                candidate.get("admission_review_status")
            ),
            "admission_review_candidate_ready": (
                candidate.get("admission_review_candidate_ready") is True
            ),
            "recommended_next_step": _followup_token(
                candidate.get("recommended_next_step")
            ),
            "source_obligation": _followup_token(
                candidate.get("source_obligation")
                or verification.get("source_obligation")
            ),
            "source_identity_status": _followup_token(
                identity.get("source_identity_status")
                or verification.get("source_identity_status")
            ),
            "url_domain_comparison_posture": _followup_token(
                identity.get("url_domain_comparison_posture")
            ),
            "verification_status": _followup_token(
                verification.get("verification_status")
            ),
            "official_source_status": _followup_token(
                verification.get("official_source_status")
            ),
            "currentness_posture": _followup_token(
                verification.get("currentness_posture")
            ),
            "relevance_posture": _followup_token(
                verification.get("relevance_posture")
            ),
            "read_posture": _followup_token(read_summary.get("read_posture")),
            "raw_page_text_retained": (
                read_summary.get("raw_page_text_retained")
                if isinstance(read_summary.get("raw_page_text_retained"), bool)
                else None
            ),
        }
    )


def ag96i3m2_intake_binding_authorization_projection(value: Any) -> dict[str, Any]:
    binding = _mapping_or_to_dict(value)
    official_current_rules = _mapping(
        binding.get("official_current_rules")
        or binding.get("official_current_rules_mapping")
    )
    return _compact_mapping(
        {
            "requirement_id": _followup_token(binding.get("requirement_id")),
            "candidate_id": _followup_token(binding.get("candidate_id")),
            "observation_id": _followup_token(binding.get("observation_id")),
            "observation_ref": _clean_text(
                binding.get("observation_ref"),
                limit=220,
            ),
            "source_obligation": _followup_token(
                binding.get("source_obligation")
            ),
            "required_source_class": _followup_token(
                binding.get("required_source_class")
                or binding.get("source_class_requirement")
            ),
            "required_source_tier": _followup_token(
                binding.get("required_source_tier")
            ),
            "required_currentness": _followup_token(
                binding.get("required_currentness")
            ),
            "origin_phase": _followup_token(binding.get("origin_phase")),
            "origin_action": _followup_token(binding.get("origin_action")),
            "origin_record_type": _followup_token(
                binding.get("origin_record_type")
            ),
            "origin_schema_version": _followup_token(
                binding.get("origin_schema_version")
            ),
            "idempotency_key": _clean_text(
                binding.get("idempotency_key"),
                limit=220,
            ),
            "deduplication_basis": followup_token_list(
                binding.get("deduplication_basis")
            ),
            "official_current_rules": _official_current_rules_binding_projection(
                official_current_rules,
                binding,
            ),
            "final_evidence": bool(binding.get("final_evidence")),
            "citation_eligible": bool(binding.get("citation_eligible")),
            "author_activation_allowed": bool(
                binding.get("author_activation_allowed")
            ),
        }
    )


def _validate_ag96i3m2_candidate_binding_pair(
    *,
    candidate_projection: Mapping[str, Any],
    binding_projection: Mapping[str, Any],
) -> None:
    for field in ("candidate_id", "source_obligation"):
        if not candidate_projection.get(field) or not binding_projection.get(field):
            raise FollowupRunKernelReducerError(
                f"AG-96I3M2 intake requires bound {field}"
            )
        if candidate_projection.get(field) != binding_projection.get(field):
            raise FollowupRunKernelReducerError(
                f"AG-96I3M2 {field} mismatch"
            )
    for field in ("requirement_id", "observation_id"):
        if not binding_projection.get(field):
            raise FollowupRunKernelReducerError(
                f"AG-96I3M2 intake requires bound {field}"
            )
    if (
        candidate_projection.get("observation_ref")
        and binding_projection.get("observation_ref")
        and candidate_projection.get("observation_ref")
        != binding_projection.get("observation_ref")
    ):
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 observation_ref mismatch"
        )
    if not _mapping(binding_projection.get("official_current_rules")):
        raise FollowupRunKernelReducerError(
            "AG-96I3M2 intake requires official_current_rules mapping"
        )
    for field in (
        "origin_phase",
        "origin_action",
        "origin_record_type",
        "origin_schema_version",
    ):
        if not binding_projection.get(field):
            raise FollowupRunKernelReducerError(
                f"AG-96I3M2 intake requires binding {field}"
            )
    for flag in ("final_evidence", "citation_eligible", "author_activation_allowed"):
        if binding_projection.get(flag) is not False:
            raise FollowupRunKernelReducerError(
                f"AG-96I3M2 intake requires {flag}=False"
            )


def _official_current_rules_binding_projection(
    mapping: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    return _compact_mapping(
        {
            "source_obligation": _followup_token(
                mapping.get("source_obligation")
                or binding.get("source_obligation")
            ),
            "requirement_kind": _followup_token(
                mapping.get("requirement_kind") or mapping.get("kind")
            ),
            "required_source_class": _followup_token(
                mapping.get("required_source_class")
                or mapping.get("source_class")
            ),
            "required_source_tier": _followup_token(
                mapping.get("required_source_tier") or mapping.get("source_tier")
            ),
            "required_currentness": _followup_token(
                mapping.get("required_currentness") or mapping.get("currentness")
            ),
            "requirement_id": _followup_token(
                mapping.get("requirement_id") or binding.get("requirement_id")
            ),
        }
    )


def _mapping_or_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        mapped = to_dict()
        return dict(mapped) if isinstance(mapped, Mapping) else {}
    return {}


def _compact_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


_FOLLOWUP_SENSITIVE_PAYLOAD_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_text",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "snippet",
        "snippets",
        "text",
        "token",
    }
)


def _contains_sensitive_payload_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _followup_token(key, limit=120)
            if token in {
                "budget_semantics",
                "execution_gate",
                "redaction_posture",
            }:
                continue
            if token in _FOLLOWUP_SENSITIVE_PAYLOAD_KEYS or token.startswith("raw_"):
                return True
            if _contains_sensitive_payload_field(item):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return any(_contains_sensitive_payload_field(item) for item in value)
    return False


def _followup_token(value: Any, *, limit: int = 220) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        return ""
    return text.casefold().replace("-", "_").replace(" ", "_")[:limit]


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    return text[:limit]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE",
    "FOLLOWUP_AUTHOR_GATE_FALSE_FLAGS",
    "FOLLOWUP_AUTHOR_OBSERVATION_FALSE_FLAGS",
    "FOLLOWUP_EXECUTION_FALSE_FLAGS",
    "FOLLOWUP_INTAKE_FALSE_FLAGS",
    "FOLLOWUP_NO_LIVE_FALSE_FLAGS",
    "FOLLOWUP_PACKET_FALSE_FLAGS",
    "FOLLOWUP_PROVIDER_JOB_EXECUTION_FALSE_FLAGS",
    "FOLLOWUP_RECHECK_FALSE_FLAGS",
    "FollowupRunKernelReducerError",
    "ag96i3m2_admission_review_authorization_projection",
    "ag96i3m2_intake_binding_authorization_projection",
    "ag96i3m2_validate_authorized_intake_materials",
    "build_final_answer_authority_projection",
    "build_followup_author_gate_projection",
    "build_followup_authorization_projection",
    "build_followup_author_observation_projection",
    "build_followup_evidence_intake_ledger_observation",
    "build_followup_evidence_intake_projection",
    "build_followup_execution_projection",
    "build_followup_final_answer_packet_projection",
    "build_followup_sufficiency_recheck_projection",
    "followup_evidence_intake_outcome",
    "followup_expected_source_classes",
    "followup_sealed_candidate",
    "require_followup_flags_false",
    "validate_followup_author_gate_observation_binding",
    "validate_followup_author_observation_binding",
    "validate_followup_evidence_intake_action_binding",
    "validate_followup_execution_action_binding",
    "validate_followup_final_answer_packet_observation_binding",
    "validate_followup_provider_job_execution_action_binding",
    "validate_followup_sufficiency_recheck_observation_binding",
]
