"""RunKernel-owned Author prose-only finalization.

This reducer consumes hardened FinalAnswerPacket state/projection and
AuthorProsePolicy only. It formats safe, human-readable prose while preserving
FAP truth/status/citation/source-obligation posture.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from core.author_prose_policy import (
    AuthorProsePolicy,
    AuthorProsePolicyError,
    BlockedAnswerProfile,
    BrevityProfile,
    FormatProfile,
    PartialAnswerProfile,
    SourcePassThroughProfile,
    StyleProfile,
    UncertaintyProfile,
    author_prose_policy_digest,
    author_prose_policy_ref,
    normalize_author_prose_policy,
)

AUTHOR_PROSE_FINALIZATION_SCHEMA_VERSION = (
    "author_prose_finalization_author_prose_only_finalization_01_v1"
)
AUTHOR_PROSE_FINALIZATION_ACTION_SCHEMA_VERSION = (
    "author_prose_finalization_action_author_prose_only_finalization_01_v1"
)
AUTHOR_PROSE_FINALIZATION_OBSERVATION_SCHEMA_VERSION = (
    "author_prose_finalization_observation_author_prose_only_finalization_01_v1"
)
AUTHOR_PROSE_FINALIZATION_STAGE = "author_prose_finalization"
AUTHOR_PROSE_FINALIZATION_REASON = "author_prose_only_finalization_from_hardened_fap"
AUTHOR_PROSE_FINALIZATION_TRACE_KEY = "author_prose_finalization"
AUTHOR_PROSE_OWNER = "RunKernel.AuthorProseFinalization"
AUTHOR_PROSE_STATE_KIND = "author_prose_finalization_state"

FAP_TO_AUTHOR_PROSE_STATUS = {
    "full_answer_packet_ready": "full_answer_prose_created",
    "partial_answer_packet_ready": "partial_answer_prose_created",
    "blocked_answer_packet": "blocked_answer_prose_created",
    "followup_required_packet": "followup_required_prose_created",
    "contested_answer_packet": "contested_answer_prose_created",
    "insufficient_evidence_packet": "insufficient_evidence_prose_created",
    "not_applicable": "not_applicable_no_answer",
}
FAP_STATUSES = frozenset(FAP_TO_AUTHOR_PROSE_STATUS)
AUTHOR_PROSE_STATUSES = frozenset(FAP_TO_AUTHOR_PROSE_STATUS.values())
PACKET_CREATED_FAP_STATUSES = FAP_STATUSES - {"not_applicable"}

_CLOSED_SURFACE_FLAGS = {
    "author_input_created": False,
    "author_payload_created": False,
    "author_input_materialized": False,
    "author_execution_allowed": False,
    "author_called": False,
    "old_author_runtime_called": False,
    "old_author_prompt_assembly_called": False,
    "citation_eligible": False,
    "citation_eligibility_created": False,
    "citations_rendered": False,
    "citation_rendering_changed": False,
    "source_obligation_satisfied": False,
    "source_obligation_satisfaction_claimed": False,
    "product_correctness_claimed": False,
    "current_answer_contract_mutated": False,
    "model_called": False,
    "provider_called": False,
    "live_provider_called": False,
    "broker_called": False,
    "search_executed": False,
    "retrieval_executed": False,
    "fetch_read_executed": False,
    "pipeline_orchestrator_called": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "raw_provider_payload_retained": False,
    "raw_source_text_retained": False,
    "bounded_source_text_retained": False,
    "db_rows_retained": False,
    "cache_rows_retained": False,
    "private_logs_retained": False,
}
_DANGEROUS_TRUE_KEYS = frozenset(_CLOSED_SURFACE_FLAGS) | {
    "author_prose_is_product_correctness",
}
_RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "body",
        "bounded_source_text",
        "bounded_text",
        "cache",
        "cookie",
        "db",
        "full_prompt",
        "full_text",
        "full_trace",
        "headers",
        "html",
        "log",
        "logs",
        "model_request",
        "model_response",
        "old_author_payload",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_source_text",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "source_text",
        "token",
        "unbounded_content",
        "unbounded_text",
    }
)
_SAFE_FALSE_RAW_KEYS = {
    "raw_prompt_retained",
    "raw_model_response_retained",
    "raw_provider_payload_retained",
    "raw_source_text_retained",
}


class AuthorProseFinalizationRuntimeError(ValueError):
    """Raised when Author prose finalization cannot reduce safely."""


@dataclass(frozen=True, slots=True)
class AuthorProseFinalizationResult:
    """Compact result for one RunKernel-reduced Author prose transition."""

    author_prose_state: Mapping[str, Any]
    author_prose_projection: Mapping[str, Any]
    authorization_action_id: str

    def to_dict(self) -> dict[str, Any]:
        projection = dict(self.author_prose_projection)
        return {
            "result_kind": "author_prose_finalization_result",
            "helper": "author_prose_finalization_runtime",
            "authorization_action_id": self.authorization_action_id,
            "author_prose_status": projection.get("author_prose_status"),
            "fap_status": projection.get("fap_status"),
            "author_prose_ref": _author_prose_ref(projection),
            "author_prose_projection": projection,
            **_CLOSED_SURFACE_FLAGS,
        }


def build_author_prose_finalization_action_inputs(
    *,
    run_id: str,
    request_id: str,
    final_answer_packet_state: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    policy: AuthorProsePolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build action inputs bound to the current hardened FAP and policy."""

    clean_run_id = _required_token(run_id, "Author prose action requires run_id")
    clean_request_id = _required_token(
        request_id,
        "Author prose action requires request_id",
    )
    fap_context = _validate_fap_context(
        final_answer_packet_state=final_answer_packet_state,
        final_answer_authority_projection=final_answer_authority_projection,
        run_id=clean_run_id,
        request_id=clean_request_id,
    )
    normalized_policy = _normalize_policy(policy, mode=fap_context["mode"])
    policy_digest = author_prose_policy_digest(normalized_policy)
    return {
        "schema_version": AUTHOR_PROSE_FINALIZATION_ACTION_SCHEMA_VERSION,
        "owner": AUTHOR_PROSE_OWNER,
        "trace_key": AUTHOR_PROSE_FINALIZATION_TRACE_KEY,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "mode": fap_context["mode"],
        "fap_status": fap_context["fap_status"],
        "author_prose_status": _author_prose_status(fap_context["fap_status"]),
        "fap_ref": dict(fap_context["fap_ref"]),
        "packet_created": fap_context["packet_created"],
        "packet_id": fap_context.get("packet_id"),
        "packet_digest": fap_context.get("packet_digest"),
        "no_packet_record_digest": fap_context.get("no_packet_record_digest"),
        "final_answer_authority_projection_digest": fap_context[
            "final_answer_authority_projection_digest"
        ],
        "fap_context_digest": fap_context["fap_context_digest"],
        "policy": normalized_policy.to_dict(),
        "policy_ref": author_prose_policy_ref(normalized_policy),
        "policy_digest": policy_digest,
        "author_prose_requested": True,
        "hardened_fap_only": True,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def build_author_prose_finalization_observation_payload(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the observation payload that asks RunKernel to finalize prose."""

    inputs = _safe_mapping(action_inputs)
    if inputs.get("schema_version") != AUTHOR_PROSE_FINALIZATION_ACTION_SCHEMA_VERSION:
        raise AuthorProseFinalizationRuntimeError(
            "Author prose action schema mismatch"
        )
    _validate_closed_flags(inputs, context="Author prose action inputs")
    return {
        "schema_version": AUTHOR_PROSE_FINALIZATION_OBSERVATION_SCHEMA_VERSION,
        "owner": AUTHOR_PROSE_OWNER,
        "trace_key": AUTHOR_PROSE_FINALIZATION_TRACE_KEY,
        "authorized_action_id": _required_token(
            action_id,
            "Author prose observation requires action_id",
            limit=220,
        ),
        "fap_status": inputs.get("fap_status"),
        "author_prose_status": inputs.get("author_prose_status"),
        "fap_ref": _safe_mapping(inputs.get("fap_ref")),
        "packet_created": inputs.get("packet_created") is True,
        "packet_id": inputs.get("packet_id"),
        "packet_digest": inputs.get("packet_digest"),
        "no_packet_record_digest": inputs.get("no_packet_record_digest"),
        "final_answer_authority_projection_digest": inputs.get(
            "final_answer_authority_projection_digest"
        ),
        "fap_context_digest": inputs.get("fap_context_digest"),
        "policy_ref": _safe_mapping(inputs.get("policy_ref")),
        "policy_digest": inputs.get("policy_digest"),
        "author_prose_requested": True,
        "hardened_fap_only": True,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def build_author_prose_finalization_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    final_answer_packet_state: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate bindings and build canonical Author prose state."""

    clean_action_id = _required_token(
        action_id,
        "Author prose reduction requires action_id",
        limit=220,
    )
    clean_run_id = _required_token(run_id, "Author prose reduction requires run_id")
    clean_request_id = _required_token(
        request_id,
        "Author prose reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    if inputs.get("schema_version") != AUTHOR_PROSE_FINALIZATION_ACTION_SCHEMA_VERSION:
        raise AuthorProseFinalizationRuntimeError(
            "Author prose action schema mismatch"
        )
    payload = _safe_mapping(observation_payload)
    if (
        payload.get("schema_version")
        != AUTHOR_PROSE_FINALIZATION_OBSERVATION_SCHEMA_VERSION
    ):
        raise AuthorProseFinalizationRuntimeError(
            "Author prose observation schema mismatch"
        )
    if payload.get("authorized_action_id") != clean_action_id:
        raise AuthorProseFinalizationRuntimeError(
            "Author prose observation action_id binding mismatch"
        )
    if inputs.get("run_id") != clean_run_id or inputs.get("request_id") != (
        clean_request_id
    ):
        raise AuthorProseFinalizationRuntimeError(
            "Author prose action run/request binding mismatch"
        )
    if payload.get("author_prose_requested") is not True:
        raise AuthorProseFinalizationRuntimeError(
            "Author prose observation must request finalization"
        )
    _validate_closed_flags(inputs, context="Author prose action inputs")
    _validate_closed_flags(payload, context="Author prose observation payload")

    fap_context = _validate_fap_context(
        final_answer_packet_state=final_answer_packet_state,
        final_answer_authority_projection=final_answer_authority_projection,
        run_id=clean_run_id,
        request_id=clean_request_id,
    )
    policy = _normalize_policy(inputs.get("policy"), mode=fap_context["mode"])
    actual_policy_digest = author_prose_policy_digest(policy)
    for source, label in ((inputs, "action"), (payload, "observation")):
        _validate_bound_source(
            source=source,
            label=label,
            fap_context=fap_context,
            policy_digest=actual_policy_digest,
        )

    prose = _build_prose_payload(
        fap_state=_safe_mapping(final_answer_packet_state),
        fap_projection=_safe_mapping(final_answer_authority_projection),
        fap_context=fap_context,
        policy=policy,
    )
    state_base = {
        "schema_version": AUTHOR_PROSE_FINALIZATION_SCHEMA_VERSION,
        "record_kind": AUTHOR_PROSE_STATE_KIND,
        "trace_key": AUTHOR_PROSE_FINALIZATION_TRACE_KEY,
        "owner": AUTHOR_PROSE_OWNER,
        "canonical_state": True,
        "reduced_state": True,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "mode": fap_context["mode"],
        "author_prose_status": _author_prose_status(fap_context["fap_status"]),
        "fap_status": fap_context["fap_status"],
        "fap_ref": dict(fap_context["fap_ref"]),
        "packet_created": fap_context["packet_created"],
        "packet_id": fap_context.get("packet_id"),
        "packet_digest": fap_context.get("packet_digest"),
        "no_packet_record_digest": fap_context.get("no_packet_record_digest"),
        "final_answer_authority_projection_digest": fap_context[
            "final_answer_authority_projection_digest"
        ],
        "fap_context_digest": fap_context["fap_context_digest"],
        "policy_ref": author_prose_policy_ref(policy),
        "policy_digest": actual_policy_digest,
        "policy": policy.to_dict(),
        "answer_text": prose["answer_text"],
        "answer_blocks": prose["answer_blocks"],
        "component_prose_entries": prose["component_prose_entries"],
        "source_ref_presentation": prose["source_ref_presentation"],
        "mandatory_caveats": prose["mandatory_caveats"],
        "prohibited_claims": prose["prohibited_claims"],
        "prohibited_upgrades": prose["prohibited_upgrades"],
        "citation_posture": prose["citation_posture"],
        "source_obligation_posture": prose["source_obligation_posture"],
        "full_answer_implication_allowed": prose[
            "full_answer_implication_allowed"
        ],
        "supported_claims_created": prose["supported_claims_created"],
        "supported_component_ids": prose["supported_component_ids"],
        "unresolved_component_ids": prose["unresolved_component_ids"],
        "must_not_answer_component_ids": prose["must_not_answer_component_ids"],
        "contested_posture_preserved": prose["contested_posture_preserved"],
        "followup_authorized_by_author_prose": False,
        "remediation_completed_claimed": False,
        "author_prose_is_product_correctness": False,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }
    prose_digest = _digest_json(_state_digest_payload(state_base))
    prose_id = (
        "author-prose-finalization:"
        f"{clean_request_id}:{state_base['author_prose_status']}:{prose_digest[:16]}"
    )
    state = {
        **state_base,
        "author_prose_id": prose_id,
        "author_prose_digest": prose_digest,
    }
    return validate_author_prose_finalization_state(state)


def build_author_prose_finalization_projection(
    *,
    author_prose_state: Mapping[str, Any],
    existing_author_prose_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project canonical Author prose state into the RunKernel projection slot."""

    state = validate_author_prose_finalization_state(author_prose_state)
    projection = {
        "schema_version": state.get("schema_version"),
        "record_kind": "author_prose_finalization_projection",
        "trace_key": AUTHOR_PROSE_FINALIZATION_TRACE_KEY,
        "owner": AUTHOR_PROSE_OWNER,
        "canonical_state": True,
        "reduced_state": True,
        "stage": AUTHOR_PROSE_FINALIZATION_STAGE,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "mode": state.get("mode"),
        "authorized_action_id": state.get("authorized_action_id"),
        "author_prose_id": state.get("author_prose_id"),
        "author_prose_digest": state.get("author_prose_digest"),
        "author_prose_status": state.get("author_prose_status"),
        "fap_status": state.get("fap_status"),
        "fap_ref": _safe_mapping(state.get("fap_ref")),
        "packet_created": state.get("packet_created") is True,
        "packet_id": state.get("packet_id"),
        "packet_digest": state.get("packet_digest"),
        "no_packet_record_digest": state.get("no_packet_record_digest"),
        "final_answer_authority_projection_digest": state.get(
            "final_answer_authority_projection_digest"
        ),
        "fap_context_digest": state.get("fap_context_digest"),
        "policy_ref": _safe_mapping(state.get("policy_ref")),
        "policy_digest": state.get("policy_digest"),
        "answer_text": state.get("answer_text"),
        "answer_blocks": _safe_list(state.get("answer_blocks")),
        "component_prose_entries": _safe_list(
            state.get("component_prose_entries")
        ),
        "source_ref_presentation": _safe_mapping(
            state.get("source_ref_presentation")
        ),
        "mandatory_caveats": _text_list(state.get("mandatory_caveats"), limit=800),
        "prohibited_claims": _text_list(state.get("prohibited_claims"), limit=800),
        "prohibited_upgrades": _text_list(
            state.get("prohibited_upgrades"),
            limit=800,
        ),
        "citation_posture": state.get("citation_posture"),
        "source_obligation_posture": state.get("source_obligation_posture"),
        "full_answer_implication_allowed": (
            state.get("full_answer_implication_allowed") is True
        ),
        "supported_claims_created": state.get("supported_claims_created") is True,
        "supported_component_ids": _text_list(
            state.get("supported_component_ids"),
            limit=260,
        ),
        "unresolved_component_ids": _text_list(
            state.get("unresolved_component_ids"),
            limit=260,
        ),
        "must_not_answer_component_ids": _text_list(
            state.get("must_not_answer_component_ids"),
            limit=260,
        ),
        "contested_posture_preserved": state.get(
            "contested_posture_preserved"
        )
        is True,
        "followup_authorized_by_author_prose": False,
        "remediation_completed_claimed": False,
        "author_prose_is_product_correctness": False,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }
    projection["author_prose_history"] = _projection_history(
        existing_author_prose_projection,
        projection,
    )
    projection["author_prose_count"] = len(projection["author_prose_history"])
    _validate_closed_flags(projection, context="Author prose projection")
    return _without_none(projection)


def reduce_author_prose_finalization(
    *,
    run_kernel: Any,
    policy: AuthorProsePolicy | Mapping[str, Any] | None = None,
) -> AuthorProseFinalizationResult:
    """Authorize and reduce Author prose-only finalization through RunKernel."""

    try:
        action = run_kernel.authorize_author_prose_finalization(policy=policy)
        from core.run_kernel import Observation, ObservationType, RunStageStatus

        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.AUTHOR_PROSE_FINALIZED,
                status=RunStageStatus.COMPLETED,
                payload=build_author_prose_finalization_observation_payload(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                ),
            )
        )
    except Exception as exc:  # pragma: no cover - translated for callers/tests.
        if exc.__class__.__name__ == "RunKernelTransitionError":
            raise AuthorProseFinalizationRuntimeError(str(exc)) from exc
        raise
    return AuthorProseFinalizationResult(
        author_prose_state=dict(run_kernel.state.author_prose_state),
        author_prose_projection=dict(run_kernel.state.author_prose_projection),
        authorization_action_id=action.action_id,
    )


def validate_author_prose_finalization_state(
    state: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate canonical Author prose state."""

    safe = _safe_mapping(state)
    if not safe:
        raise AuthorProseFinalizationRuntimeError("Author prose state is required")
    if safe.get("owner") != AUTHOR_PROSE_OWNER:
        raise AuthorProseFinalizationRuntimeError("Author prose owner mismatch")
    if safe.get("schema_version") != AUTHOR_PROSE_FINALIZATION_SCHEMA_VERSION:
        raise AuthorProseFinalizationRuntimeError("Author prose schema mismatch")
    if safe.get("canonical_state") is not True or safe.get("reduced_state") is not True:
        raise AuthorProseFinalizationRuntimeError(
            "Author prose state must be canonical"
        )
    fap_status = _normalized_token(safe.get("fap_status"))
    if fap_status not in FAP_STATUSES:
        raise AuthorProseFinalizationRuntimeError("unsupported FAP status")
    if safe.get("author_prose_status") != _author_prose_status(fap_status):
        raise AuthorProseFinalizationRuntimeError("Author prose status mismatch")
    _validate_closed_flags(safe, context="Author prose state")
    if fap_status == "not_applicable":
        if safe.get("packet_id") or safe.get("packet_digest"):
            raise AuthorProseFinalizationRuntimeError(
                "not_applicable Author prose must not carry packet identity"
            )
        if safe.get("supported_claims_created") is True:
            raise AuthorProseFinalizationRuntimeError(
                "not_applicable Author prose must not create supported claims"
            )
    else:
        _required_token(
            safe.get("packet_id"),
            "Author prose state requires packet_id",
            limit=260,
        )
        _required_token(
            safe.get("packet_digest"),
            "Author prose state requires packet_digest",
            limit=128,
        )
    declared = _required_token(
        safe.get("author_prose_digest"),
        "Author prose state requires digest",
        limit=128,
    )
    if declared != _digest_json(_state_digest_payload(safe)):
        raise AuthorProseFinalizationRuntimeError("Author prose digest mismatch")
    _required_token(
        safe.get("author_prose_id"),
        "Author prose state requires author_prose_id",
        limit=260,
    )
    answer_text = _clean_text(safe.get("answer_text"), limit=8_000)
    if not answer_text:
        raise AuthorProseFinalizationRuntimeError("Author prose requires answer_text")
    return safe


def _validate_fap_context(
    *,
    final_answer_packet_state: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    run_id: str,
    request_id: str,
) -> dict[str, Any]:
    projection = _safe_mapping(final_answer_authority_projection)
    if not projection:
        raise AuthorProseFinalizationRuntimeError(
            "Author prose requires final_answer_authority_projection"
        )
    if projection.get("owner") != "RunKernel.FinalAnswerPacket":
        raise AuthorProseFinalizationRuntimeError(
            "Author prose FAP projection owner mismatch"
        )
    if projection.get("run_id") != run_id or projection.get("request_id") != request_id:
        raise AuthorProseFinalizationRuntimeError(
            "Author prose FAP projection run/request mismatch"
        )
    fap_status = _normalized_token(projection.get("fap_status"))
    if fap_status not in FAP_STATUSES:
        raise AuthorProseFinalizationRuntimeError(
            "Author prose requires hardened FAP status"
        )
    packet_created = projection.get("packet_created") is True
    state = _safe_mapping(final_answer_packet_state)
    packet_id = _clean_text(projection.get("packet_id"), limit=260)
    packet_digest = _clean_text(projection.get("packet_digest"), limit=128)
    no_packet_digest = _clean_text(
        projection.get("no_packet_record_digest"),
        limit=128,
    )
    if fap_status == "not_applicable":
        if packet_created or packet_id or packet_digest or state:
            raise AuthorProseFinalizationRuntimeError(
                "not_applicable Author prose requires no-packet FAP posture"
            )
        if not no_packet_digest:
            raise AuthorProseFinalizationRuntimeError(
                "not_applicable Author prose requires no_packet_record_digest"
            )
    else:
        if not packet_created or not state:
            raise AuthorProseFinalizationRuntimeError(
                "Author prose requires hardened FAP packet state"
            )
        if state.get("run_id") != run_id or state.get("request_id") != request_id:
            raise AuthorProseFinalizationRuntimeError(
                "Author prose FAP state run/request mismatch"
            )
        if state.get("fap_status") != fap_status:
            raise AuthorProseFinalizationRuntimeError(
                "Author prose FAP state/projection status mismatch"
            )
        if state.get("packet_id") != packet_id or state.get("packet_digest") != (
            packet_digest
        ):
            raise AuthorProseFinalizationRuntimeError(
                "Author prose FAP state/projection packet binding mismatch"
            )
    projection_digest = _digest_json(projection)
    fap_ref = _without_empty(
        {
            "fap_status": fap_status,
            "packet_created": packet_created,
            "packet_id": packet_id,
            "packet_digest": packet_digest,
            "no_packet_record_digest": no_packet_digest,
            "final_answer_authority_projection_digest": projection_digest,
        }
    )
    context_payload = {
        "fap_ref": fap_ref,
        "fap_projection_digest": projection_digest,
        "state_packet_digest": state.get("packet_digest"),
        "state_digest": _digest_json(state) if state else None,
    }
    return {
        "mode": _mode_label(projection.get("mode")),
        "fap_status": fap_status,
        "author_prose_status": _author_prose_status(fap_status),
        "packet_created": packet_created,
        "packet_id": packet_id,
        "packet_digest": packet_digest,
        "no_packet_record_digest": no_packet_digest,
        "fap_ref": fap_ref,
        "final_answer_authority_projection_digest": projection_digest,
        "fap_context_digest": _digest_json(context_payload),
    }


def _validate_bound_source(
    *,
    source: Mapping[str, Any],
    label: str,
    fap_context: Mapping[str, Any],
    policy_digest: str,
) -> None:
    expected = {
        "fap_status": fap_context.get("fap_status"),
        "author_prose_status": fap_context.get("author_prose_status"),
        "packet_created": fap_context.get("packet_created"),
        "packet_id": fap_context.get("packet_id"),
        "packet_digest": fap_context.get("packet_digest"),
        "no_packet_record_digest": fap_context.get("no_packet_record_digest"),
        "final_answer_authority_projection_digest": fap_context.get(
            "final_answer_authority_projection_digest"
        ),
        "fap_context_digest": fap_context.get("fap_context_digest"),
        "policy_digest": policy_digest,
    }
    for key, value in expected.items():
        if source.get(key) != value:
            raise AuthorProseFinalizationRuntimeError(
                f"Author prose {label} {key} binding is stale"
            )


def _build_prose_payload(
    *,
    fap_state: Mapping[str, Any],
    fap_projection: Mapping[str, Any],
    fap_context: Mapping[str, Any],
    policy: AuthorProsePolicy,
) -> dict[str, Any]:
    fap_status = str(fap_context["fap_status"])
    component_entries = _component_entries(fap_state, fap_projection)
    supported = [
        entry
        for entry in component_entries
        if entry.get("supported_claim_allowed") is True
        and fap_status in {
            "full_answer_packet_ready",
            "partial_answer_packet_ready",
        }
    ]
    unresolved = [
        entry for entry in component_entries if entry.get("component_id") not in {
            item.get("component_id") for item in supported
        }
    ]
    source_refs = _source_refs(fap_state, fap_projection)
    mandatory_caveats = _dedupe_text(
        [
            *_text_list(fap_projection.get("mandatory_caveats"), limit=800),
            *_component_text(component_entries, "mandatory_caveats"),
            *_component_text(component_entries, "caveats"),
        ]
    )
    prohibited_claims = _dedupe_text(
        [
            *_text_list(fap_projection.get("author_prohibited_claims"), limit=800),
            *_text_list(fap_projection.get("prohibited_claims"), limit=800),
        ]
    )
    prohibited_upgrades = _dedupe_text(
        [
            *_text_list(fap_projection.get("prohibited_upgrades"), limit=800),
            *_component_text(component_entries, "prohibited_upgrades"),
        ]
    )
    component_prose_entries = _component_prose_entries(
        fap_status=fap_status,
        component_entries=component_entries,
        source_refs=source_refs,
        policy=policy,
    )
    source_ref_presentation = _source_ref_presentation(source_refs, policy)
    blocks = _answer_blocks(
        fap_status=fap_status,
        supported=supported,
        unresolved=unresolved,
        component_prose_entries=component_prose_entries,
        mandatory_caveats=mandatory_caveats,
        source_ref_presentation=source_ref_presentation,
        policy=policy,
    )
    answer_text = _format_answer_text(blocks, policy)
    return {
        "answer_text": answer_text,
        "answer_blocks": blocks,
        "component_prose_entries": component_prose_entries,
        "source_ref_presentation": source_ref_presentation,
        "mandatory_caveats": mandatory_caveats,
        "prohibited_claims": prohibited_claims,
        "prohibited_upgrades": prohibited_upgrades,
        "citation_posture": fap_projection.get("citation_posture"),
        "source_obligation_posture": fap_projection.get(
            "source_obligation_posture"
        ),
        "full_answer_implication_allowed": (
            fap_status == "full_answer_packet_ready"
        ),
        "supported_claims_created": bool(supported)
        and fap_status in {
            "full_answer_packet_ready",
            "partial_answer_packet_ready",
        },
        "supported_component_ids": [
            item.get("component_id") for item in supported if item.get("component_id")
        ],
        "unresolved_component_ids": [
            item.get("component_id")
            for item in unresolved
            if item.get("component_id")
        ],
        "must_not_answer_component_ids": [
            item.get("component_id")
            for item in component_entries
            if item.get("must_not_answer") is True and item.get("component_id")
        ],
        "contested_posture_preserved": fap_status == "contested_answer_packet",
    }


def _answer_blocks(
    *,
    fap_status: str,
    supported: Sequence[Mapping[str, Any]],
    unresolved: Sequence[Mapping[str, Any]],
    component_prose_entries: Sequence[Mapping[str, Any]],
    mandatory_caveats: Sequence[str],
    source_ref_presentation: Mapping[str, Any],
    policy: AuthorProsePolicy,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if fap_status == "full_answer_packet_ready":
        items = [_component_sentence(entry, policy) for entry in supported]
        if not items:
            items = ["The hardened packet marks the answer ready but carries no safe component claim text."]
        blocks.append(
            _block(
                "answer",
                "Answer",
                _full_answer_intro(policy),
                items,
            )
        )
        blocks.append(_claim_text_limitation_block())
    elif fap_status == "partial_answer_packet_ready":
        partial_blocks = _partial_blocks(
            supported=supported,
            unresolved=unresolved,
            policy=policy,
        )
        blocks.extend(partial_blocks)
        blocks.append(_claim_text_limitation_block())
    elif fap_status == "blocked_answer_packet":
        blocks.append(_blocked_block(unresolved, policy))
    elif fap_status == "followup_required_packet":
        blocks.append(_followup_block(unresolved, policy))
    elif fap_status == "contested_answer_packet":
        blocks.append(_contested_block(unresolved or supported, policy))
    elif fap_status == "insufficient_evidence_packet":
        blocks.append(_insufficient_evidence_block(unresolved, policy))
    elif fap_status == "not_applicable":
        blocks.append(
            _block(
                "not_applicable",
                "No Answer",
                "No answer is applicable for this run posture.",
                [],
            )
        )
    if source_ref_presentation.get("items"):
        blocks.append(
            _block(
                "support_refs",
                "Support Refs",
                "Support refs are shown as refs/digests only, not rendered citations.",
                [
                    item.get("display")
                    for item in source_ref_presentation.get("items", [])
                    if item.get("display")
                ],
            )
        )
    if mandatory_caveats and policy.format_profile is not FormatProfile.CAVEATS_AT_END:
        blocks.append(_block("caveats", "Caveats", None, list(mandatory_caveats)))
    if policy.format_profile is FormatProfile.CAVEATS_AT_END and mandatory_caveats:
        blocks.append(_block("caveats", "Caveats", None, list(mandatory_caveats)))
    blocks.append(
        _block(
            "boundary",
            "Boundary",
            (
                "This prose does not render citations, satisfy source obligations, "
                "or claim product correctness."
            ),
            [],
        )
    )
    return [_without_empty(block) for block in blocks]


def _partial_blocks(
    *,
    supported: Sequence[Mapping[str, Any]],
    unresolved: Sequence[Mapping[str, Any]],
    policy: AuthorProsePolicy,
) -> list[dict[str, Any]]:
    supported_items = [_component_sentence(entry, policy) for entry in supported]
    unresolved_items = [_unresolved_sentence(entry, policy) for entry in unresolved]
    supported_block = _block(
        "supported_parts",
        "Supported Parts",
        "This is a partial answer from the hardened packet.",
        supported_items or ["No supported component claim text is available in FAP."],
    )
    unresolved_block = _block(
        "unresolved_parts",
        "Unresolved Parts",
        "The unresolved parts remain outside the supported answer.",
        unresolved_items or ["No unresolved component entries are present."],
    )
    if (
        policy.partial_answer_profile
        is PartialAnswerProfile.UNRESOLVED_FIRST
    ):
        return [unresolved_block, supported_block]
    return [supported_block, unresolved_block]


def _blocked_block(
    unresolved: Sequence[Mapping[str, Any]],
    policy: AuthorProsePolicy,
) -> dict[str, Any]:
    items = [_blocker_sentence(entry, policy) for entry in unresolved]
    if not items:
        items = ["The hardened packet reports a blocked answer posture."]
    intro = "The answer is blocked by the hardened packet."
    if policy.blocked_answer_profile is BlockedAnswerProfile.SHORT_BLOCKED:
        intro = "The hardened packet blocks this answer."
    elif (
        policy.blocked_answer_profile
        is BlockedAnswerProfile.EXPLAIN_NEXT_NEEDED_EVIDENCE
    ):
        intro = (
            "The answer is blocked until the missing or unresolved evidence "
            "posture changes in a future authorized phase."
        )
    return _block("blocked", "Blocked", intro, items)


def _followup_block(
    unresolved: Sequence[Mapping[str, Any]],
    policy: AuthorProsePolicy,
) -> dict[str, Any]:
    items = [_unresolved_sentence(entry, policy) for entry in unresolved]
    if not items:
        items = ["The hardened packet says follow-up remediation is still required."]
    return _block(
        "followup_required",
        "Follow-Up Required",
        (
            "Follow-up or remediation is still required; this prose does not "
            "authorize follow-up or mark remediation complete."
        ),
        items,
    )


def _contested_block(
    entries: Sequence[Mapping[str, Any]],
    policy: AuthorProsePolicy,
) -> dict[str, Any]:
    items = [_unresolved_sentence(entry, policy) for entry in entries]
    if not items:
        items = ["The hardened packet preserves a contested answer posture."]
    intro = "The answer remains contested in the hardened packet."
    if policy.uncertainty_profile is UncertaintyProfile.CONTESTED_FIRST:
        intro = "Contested posture comes first: the packet does not resolve the disagreement."
    return _block("contested", "Contested", intro, items)


def _insufficient_evidence_block(
    unresolved: Sequence[Mapping[str, Any]],
    policy: AuthorProsePolicy,
) -> dict[str, Any]:
    items = [_unresolved_sentence(entry, policy) for entry in unresolved]
    if not items:
        items = ["The hardened packet contains no supported component claims."]
    return _block(
        "insufficient_evidence",
        "Insufficient Evidence",
        "Evidence is insufficient to support an answer from this packet.",
        items,
    )


def _full_answer_intro(policy: AuthorProsePolicy) -> str:
    if policy.style_profile is StyleProfile.EXECUTIVE_SUMMARY:
        return "Summary: the hardened packet supports the answer posture."
    if policy.style_profile is StyleProfile.TECHNICAL:
        return "The hardened FAP authorizes supported-component prose only."
    if policy.style_profile is StyleProfile.RESEARCH_NOTE:
        return "Research note: the hardened packet supports the answer posture."
    return "The hardened packet supports the answer posture."


def _claim_text_limitation_block() -> dict[str, Any]:
    return _block(
        "claim_text_limitation",
        "Claim Text Boundary",
        (
            "The packet does not provide safe free-form claim text, so this "
            "prose preserves component posture instead of reconstructing richer claims."
        ),
        [],
    )


def _component_prose_entries(
    *,
    fap_status: str,
    component_entries: Sequence[Mapping[str, Any]],
    source_refs: Sequence[Mapping[str, Any]],
    policy: AuthorProsePolicy,
) -> list[dict[str, Any]]:
    refs_by_component: dict[str, list[dict[str, Any]]] = {}
    for ref in source_refs:
        component_id = _clean_text(ref.get("component_id"), limit=260)
        if component_id:
            refs_by_component.setdefault(component_id, []).append(dict(ref))
    out = []
    for entry in component_entries:
        component_id = _clean_text(entry.get("component_id"), limit=260)
        if not component_id:
            continue
        supported = (
            entry.get("supported_claim_allowed") is True
            and fap_status
            in {"full_answer_packet_ready", "partial_answer_packet_ready"}
        )
        treatment = "supported_component" if supported else "unresolved_component"
        if entry.get("allowed_author_treatment") == "must_state_as_contested":
            treatment = "contested_component"
        elif fap_status == "blocked_answer_packet":
            treatment = "blocked_component"
        elif fap_status == "insufficient_evidence_packet":
            treatment = "insufficient_evidence_component"
        elif fap_status == "followup_required_packet":
            treatment = "followup_required_component"
        out.append(
            _without_empty(
                {
                    "component_id": component_id,
                    "fap_component_status": entry.get("fap_component_status"),
                    "component_readiness_status": entry.get(
                        "component_readiness_status"
                    ),
                    "prose_treatment": treatment,
                    "supported_in_prose": supported,
                    "must_not_answer": entry.get("must_not_answer") is True,
                    "text": (
                        _component_sentence(entry, policy)
                        if supported
                        else _unresolved_sentence(entry, policy)
                    ),
                    "support_ref_labels": [
                        _support_ref_label(ref, index)
                        for index, ref in enumerate(
                            refs_by_component.get(component_id, []),
                            start=1,
                        )
                    ],
                    "citation_rendered": False,
                    "source_obligation_satisfied": False,
                    "product_correctness_claimed": False,
                }
            )
        )
    return out


def _component_sentence(entry: Mapping[str, Any], policy: AuthorProsePolicy) -> str:
    label = _component_label(entry)
    suffix = ""
    if policy.source_pass_through_profile is SourcePassThroughProfile.INLINE_SOURCE_REFS:
        labels = _inline_ref_labels(entry)
        if labels:
            suffix = f" Support refs: {', '.join(labels)}."
    if policy.brevity_profile is BrevityProfile.TERSE:
        return f"{label} is supported by the hardened packet.{suffix}"
    if policy.brevity_profile is BrevityProfile.DETAILED:
        return (
            f"{label} is supported as an answer component by the hardened packet; "
            "the prose does not add claim detail beyond that posture."
            f"{suffix}"
        )
    return f"{label} is supported by the hardened packet for this answer.{suffix}"


def _unresolved_sentence(entry: Mapping[str, Any], policy: AuthorProsePolicy) -> str:
    label = _component_label(entry)
    status = entry.get("component_readiness_status") or entry.get(
        "fap_component_status"
    )
    blockers = _text_list(entry.get("blockers"), limit=500)
    if policy.brevity_profile is BrevityProfile.TERSE or not blockers:
        return f"{label} remains unresolved ({status})."
    return f"{label} remains unresolved ({status}): {'; '.join(blockers)}."


def _blocker_sentence(entry: Mapping[str, Any], policy: AuthorProsePolicy) -> str:
    label = _component_label(entry)
    blockers = _text_list(entry.get("blockers"), limit=500)
    if policy.blocked_answer_profile is BlockedAnswerProfile.SHORT_BLOCKED:
        return f"{label} is blocked."
    if blockers:
        return f"{label} is blocked: {'; '.join(blockers)}."
    return f"{label} is blocked by the hardened packet posture."


def _format_answer_text(
    blocks: Sequence[Mapping[str, Any]],
    policy: AuthorProsePolicy,
) -> str:
    if policy.format_profile is FormatProfile.BULLETS:
        lines: list[str] = []
        for block in blocks:
            title = block.get("title")
            body = block.get("body")
            items = _text_list(block.get("items"), limit=1_000)
            if title:
                lines.append(f"{title}:")
            if body:
                lines.append(f"- {body}")
            lines.extend(f"- {item}" for item in items)
        return "\n".join(lines)

    paragraphs: list[str] = []
    for block in blocks:
        title = block.get("title")
        body = _clean_text(block.get("body"), limit=2_000)
        items = _text_list(block.get("items"), limit=1_000)
        if policy.format_profile is FormatProfile.ANSWER_THEN_EVIDENCE and title:
            prefix = f"{title}: "
        elif policy.format_profile is FormatProfile.CAVEATS_AT_END and title:
            prefix = f"{title}: "
        else:
            prefix = ""
        text_parts = []
        if body:
            text_parts.append(body)
        text_parts.extend(items)
        if text_parts:
            paragraphs.append(prefix + " ".join(text_parts))
    return "\n\n".join(paragraphs)


def _source_ref_presentation(
    source_refs: Sequence[Mapping[str, Any]],
    policy: AuthorProsePolicy,
) -> dict[str, Any]:
    profile = policy.source_pass_through_profile
    if not source_refs:
        return {
            "profile": profile.value,
            "support_ref_count": 0,
            "presentation_note": "No source support refs are present in FAP.",
            "citations_rendered": False,
        }
    if profile is SourcePassThroughProfile.MINIMAL_REFS:
        return {
            "profile": profile.value,
            "support_ref_count": len(source_refs),
            "presentation_note": "Support refs retained by count only.",
            "citations_rendered": False,
        }
    items = []
    for index, ref in enumerate(source_refs, start=1):
        label = _support_ref_label(ref, index)
        digest = (
            ref.get("content_digest")
            or ref.get("coverage_record_digest")
            or ref.get("observation_digest")
        )
        display = label
        if digest:
            display = f"{label} ({str(digest)[:16]})"
        items.append(
            _without_empty(
                {
                    "label": label,
                    "display": display,
                    "component_id": ref.get("component_id"),
                    "content_digest": ref.get("content_digest"),
                    "coverage_record_id": ref.get("coverage_record_id"),
                    "coverage_record_digest": ref.get("coverage_record_digest"),
                    "citation_rendered": False,
                    "source_obligation_satisfied": False,
                }
            )
        )
    return {
        "profile": profile.value,
        "support_ref_count": len(source_refs),
        "items": items,
        "presentation_note": "Support refs are refs/digests only, not citations.",
        "citations_rendered": False,
    }


def _component_entries(
    fap_state: Mapping[str, Any],
    fap_projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    entries = _safe_list(fap_state.get("component_packet_entries"))
    if not entries:
        entries = _safe_list(fap_projection.get("component_packet_entries"))
    return [_safe_mapping(item) for item in entries]


def _source_refs(
    fap_state: Mapping[str, Any],
    fap_projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    refs = _safe_list(fap_state.get("source_support_refs"))
    if not refs:
        refs = _safe_list(fap_projection.get("source_support_refs"))
    return _dedupe_refs([_safe_mapping(ref) for ref in refs])


def _inline_ref_labels(entry: Mapping[str, Any]) -> list[str]:
    refs = _safe_list(entry.get("safe_source_content_refs"))
    return [_support_ref_label(_safe_mapping(ref), index) for index, ref in enumerate(refs, 1)]


def _support_ref_label(ref: Mapping[str, Any], index: int) -> str:
    label = (
        _clean_text(ref.get("support_ref_label"), limit=120)
        or _clean_text(ref.get("content_reference_id"), limit=120)
        or _clean_text(ref.get("content_ref_id"), limit=120)
        or _clean_text(ref.get("coverage_record_id"), limit=120)
        or f"support-ref-{index}"
    )
    return str(label)


def _component_label(entry: Mapping[str, Any]) -> str:
    return (
        _clean_text(entry.get("component_label"), limit=260)
        or _clean_text(entry.get("component_id"), limit=260)
        or "answer component"
    )


def _block(
    block_type: str,
    title: str,
    body: str | None,
    items: Sequence[str],
) -> dict[str, Any]:
    return {
        "block_type": block_type,
        "title": title,
        "body": body,
        "items": list(items),
    }


def _projection_history(
    existing_projection: Mapping[str, Any] | None,
    projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    existing = _safe_mapping(existing_projection)
    history = [
        _safe_mapping(item)
        for item in _safe_list(existing.get("author_prose_history"))
    ]
    history.append(
        _without_empty(
            {
                "author_prose_id": projection.get("author_prose_id"),
                "author_prose_digest": projection.get("author_prose_digest"),
                "author_prose_status": projection.get("author_prose_status"),
                "fap_status": projection.get("fap_status"),
                "policy_digest": projection.get("policy_digest"),
                "authorized_action_id": projection.get("authorized_action_id"),
            }
        )
    )
    return history


def _author_prose_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    mapped = _safe_mapping(value)
    return _without_empty(
        {
            "author_prose_id": mapped.get("author_prose_id"),
            "author_prose_digest": mapped.get("author_prose_digest"),
            "author_prose_status": mapped.get("author_prose_status"),
            "fap_status": mapped.get("fap_status"),
            "policy_digest": mapped.get("policy_digest"),
        }
    )


def _author_prose_status(fap_status: str) -> str:
    status = FAP_TO_AUTHOR_PROSE_STATUS.get(_normalized_token(fap_status))
    if not status:
        raise AuthorProseFinalizationRuntimeError(
            "unsupported FAP to Author prose status mapping"
        )
    return status


def _normalize_policy(
    policy: AuthorProsePolicy | Mapping[str, Any] | None,
    *,
    mode: Any,
) -> AuthorProsePolicy:
    try:
        return normalize_author_prose_policy(policy, mode=mode)
    except AuthorProsePolicyError as exc:
        raise AuthorProseFinalizationRuntimeError(str(exc)) from exc


def _validate_closed_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if value.get(key) is not expected:
            raise AuthorProseFinalizationRuntimeError(
                f"{context} must keep {key}=False"
            )
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if flags.get(key) is not expected:
            raise AuthorProseFinalizationRuntimeError(
                f"{context} closed_surface_flags must keep {key}=False"
            )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise AuthorProseFinalizationRuntimeError(
            f"{context} opens closed surfaces: " + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _normalize_key(key)
            if token in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(token)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _state_digest_payload(state: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(state)
    for key in (
        "author_prose_id",
        "author_prose_digest",
        "author_prose_history",
        "author_prose_count",
    ):
        payload.pop(key, None)
    return payload


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return []
    safe = _json_safe(list(value))
    return list(safe) if isinstance(safe, list) else []


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=8_000)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=140)
            if not clean_key:
                continue
            if _is_raw_or_private_key(clean_key):
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, (tuple, list, set, frozenset)):
        items = list(value)
        if isinstance(value, (set, frozenset)):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=300)


def _is_raw_or_private_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in _SAFE_FALSE_RAW_KEYS:
        return False
    return normalized.startswith("raw_") or normalized in _RAW_OR_PRIVATE_KEYS


def _dedupe_refs(refs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in refs:
        mapped = _safe_mapping(ref)
        key = (
            _clean_token(mapped.get("content_digest"), limit=128)
            or _clean_token(mapped.get("coverage_record_digest"), limit=128)
            or _clean_token(mapped.get("observation_digest"), limit=128)
            or _digest_json(mapped)
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(mapped)
    return out


def _component_text(
    component_entries: Sequence[Mapping[str, Any]],
    key: str,
) -> list[str]:
    out: list[str] = []
    for entry in component_entries:
        out.extend(_text_list(entry.get(key), limit=800))
    return out


def _dedupe_text(values: Sequence[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_text(item, limit=800)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _text_list(value: Any, *, limit: int = 260) -> list[str]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return [text] if text else []
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise AuthorProseFinalizationRuntimeError(message)
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _normalized_token(value: Any) -> str:
    text = _clean_token(value, limit=180) or ""
    return text.casefold().replace("-", "_").replace(" ", "_")


def _mode_label(mode: Any) -> str:
    labels = {"fast": "Fast", "balanced": "Balanced", "deep": "Deep"}
    label = labels.get(_normalized_token(mode))
    if not label:
        raise AuthorProseFinalizationRuntimeError(
            "Author prose mode must be Fast, Balanced, or Deep"
        )
    return label


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def _without_none(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != ""
    }


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "AUTHOR_PROSE_FINALIZATION_ACTION_SCHEMA_VERSION",
    "AUTHOR_PROSE_FINALIZATION_OBSERVATION_SCHEMA_VERSION",
    "AUTHOR_PROSE_FINALIZATION_REASON",
    "AUTHOR_PROSE_FINALIZATION_SCHEMA_VERSION",
    "AUTHOR_PROSE_FINALIZATION_STAGE",
    "AUTHOR_PROSE_FINALIZATION_TRACE_KEY",
    "AUTHOR_PROSE_OWNER",
    "AUTHOR_PROSE_STATE_KIND",
    "AUTHOR_PROSE_STATUSES",
    "AuthorProseFinalizationResult",
    "AuthorProseFinalizationRuntimeError",
    "FAP_STATUSES",
    "FAP_TO_AUTHOR_PROSE_STATUS",
    "build_author_prose_finalization_action_inputs",
    "build_author_prose_finalization_observation_payload",
    "build_author_prose_finalization_projection",
    "build_author_prose_finalization_state",
    "reduce_author_prose_finalization",
    "validate_author_prose_finalization_state",
]
