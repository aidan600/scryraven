"""Canonical initial answer-component contract acceptance runtime for AG-SEM-05.

This module is the first canonical semantic authority bridge. It provides the
bounded, pure helpers a RunKernel/RunAuthority-authorized reducer uses to accept
exactly one validated passive ``QuestionMeaningRecord`` proposal and create
canonical initial answer-component contract state.

It only accepts the initial answer contract. It does not interpret the question,
invent answer components, resolve material ambiguity, add assumptions, weaken
requirements, create coverage, create amendments, decide Sufficiency, authorize
follow-up, or create Author input. It performs no live, provider, search,
retrieval, fetch/read, or citation behavior.

The helpers here are imported by ``core.run_kernel``; to keep the import graph
acyclic this module must not import ``core.run_kernel``.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.semantic_contract_foundation import (
    QUESTION_MEANING_TRACE_KEY,
    SEMANTIC_CONTRACT_FOUNDATION_SCHEMA_VERSION,
)

INITIAL_ANSWER_CONTRACT_ACCEPTANCE_SCHEMA_VERSION = "initial_answer_contract_acceptance_ag_sem_05_v1"
INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE = "initial_answer_contract_acceptance"
INITIAL_ANSWER_CONTRACT_ACCEPTANCE_REASON = "initial_answer_contract_acceptance_from_validated_passive_proposal"
INITIAL_ANSWER_CONTRACT_ACCEPTANCE_TRACE_KEY = "initial_answer_contract_acceptance"
INITIAL_ANSWER_CONTRACT_ACCEPTANCE_OWNER = "RunKernel.InitialAnswerContract"

_PARENT_PROPOSAL_TRACE_KEY = QUESTION_MEANING_TRACE_KEY
_EXPECTED_PROPOSAL_SCHEMA_VERSION = SEMANTIC_CONTRACT_FOUNDATION_SCHEMA_VERSION

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db_row",
        "full_trace",
        "logs",
        "model_response",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_prompt",
        "raw_provider_payload",
        "raw_trace",
        "secret",
        "token",
        "unbounded_text",
    }
)

# Closed surfaces this acceptance bridge must never create or decide.
_FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "author_input",
        "canonical_coverage",
        "component_coverage_record",
        "contract_amendment_record",
        "coverage_decision",
        "coverage_invalidation_applied",
        "final_answer",
        "final_answer_packet",
        "followup_activation",
        "query_plan_activation",
        "search_judgment_decision",
        "search_work_plan_activation",
        "semantic_observation_admission",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_MATERIAL_UNRESOLVED_STATUSES = frozenset({"ambiguous", "unresolved"})
_MATERIAL_MATERIALITY = "material"


class InitialAnswerContractAcceptanceError(ValueError):
    """Raised when a passive proposal cannot be accepted as canonical state."""


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key or _is_sensitive_key(clean_key):
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=300)


def _text_tuple(value: Any, *, limit: int = 160) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    out: list[str] = []
    for item in value:
        text = _clean_token(item, limit=limit)
        if text:
            out.append(text)
    return out


def _digest_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _safe_proposal_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _accepted_component_ref(component: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "component_id": _clean_token(component.get("component_id")),
        "component_revision": _clean_token(component.get("component_revision")),
        "component_digest": _clean_token(component.get("component_digest"), limit=128),
        "user_facing_label": _clean_text(
            component.get("user_facing_label"), limit=220
        ),
        "user_facing_question": _clean_text(
            component.get("user_facing_question"), limit=500
        ),
        "requirement_posture": _clean_token(component.get("requirement_posture")),
        "materiality": _clean_token(component.get("materiality")),
        "allowed_support_kinds": _text_tuple(component.get("allowed_support_kinds")),
        "source_obligation_candidate_ids": _text_tuple(component.get("source_obligation_candidate_ids")),
        "source_obligation_candidate_refs": _text_tuple(component.get("source_obligation_candidate_refs")),
        "dependency_component_ids": _text_tuple(
            component.get("dependency_component_ids")
        ),
        "mandatory_caveats": _text_tuple(component.get("mandatory_caveats"), limit=260),
        "prohibited_upgrades": _text_tuple(component.get("prohibited_upgrades"), limit=260),
    }


def _accepted_slot_ref(slot: Mapping[str, Any]) -> dict[str, Any]:
    status = _clean_token(slot.get("status")) or "unresolved"
    materiality = _clean_token(slot.get("materiality")) or "unknown"
    selected_value = _clean_text(slot.get("selected_value"), limit=220)
    unresolved_material = materiality == _MATERIAL_MATERIALITY and status in _MATERIAL_UNRESOLVED_STATUSES
    projection: dict[str, Any] = {
        "slot_id": _clean_token(slot.get("slot_id")),
        "slot_kind": _clean_token(slot.get("slot_kind")),
        "status": status,
        "materiality": materiality,
        "unresolved_material": unresolved_material,
    }
    # Selected value is preserved only when the proposal already selected it.
    # Material unresolved/ambiguous slots are never resolved here.
    if selected_value is not None and not unresolved_material:
        projection["selected_value"] = selected_value
    return projection


def _contract_content_digest_payload(state_core: Mapping[str, Any]) -> dict[str, Any]:
    lineage = dict(state_core.get("lineage") or {})
    lineage.pop("reducer_action_id", None)
    return {
        "schema_version": state_core.get("schema_version"),
        "accepted_contract_version": state_core.get("accepted_contract_version"),
        "parent_question_meaning_record_id": state_core.get("parent_question_meaning_record_id"),
        "parent_question_meaning_record_digest": state_core.get("parent_question_meaning_record_digest"),
        "parent_proposal_schema_version": state_core.get("parent_proposal_schema_version"),
        "accepted_answer_component_refs": state_core.get("accepted_answer_component_refs"),
        "accepted_semantic_slot_refs": state_core.get("accepted_semantic_slot_refs"),
        "materiality_policy": state_core.get("materiality_policy"),
        "question_meaning_metadata": state_core.get("question_meaning_metadata", {}),
        "lineage": lineage,
    }


def _proposal_record_digest_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild the content-derived digest payload of a QuestionMeaningRecord.

    This mirrors ``QuestionMeaningRecord._record_digest``: it covers the same
    semantic-contract fields, excludes volatile wrapper fields (``trace_key``,
    ``record_digest``, ``validation``), and drops ``contract_lineage``'s
    ``proposal_digest``. Keys absent from the trimmed ``to_dict`` payload fall
    back to the defaults the record digest was computed over.
    """

    lineage = dict(record.get("contract_lineage") or {})
    lineage.pop("proposal_digest", None)
    return {
        "schema_version": record.get("schema_version"),
        "record_id": record.get("record_id"),
        "run_id": record.get("run_id"),
        "request_id": record.get("request_id"),
        "request_digest": record.get("request_digest"),
        "requested_mode": record.get("requested_mode"),
        "resolver_kind": record.get("resolver_kind"),
        "resolver_version": record.get("resolver_version"),
        "intent": record.get("intent"),
        "requested_output": record.get("requested_output"),
        "semantic_slots": record.get("semantic_slots", []),
        "answer_components": record.get("answer_components", []),
        "source_obligation_candidate_refs": record.get("source_obligation_candidate_refs", []),
        "query_shape_assessment_ref": record.get("query_shape_assessment_ref"),
        "search_work_plan_ref": record.get("search_work_plan_ref"),
        "material_ambiguity_count": record.get("material_ambiguity_count", 0),
        "user_confirmation_required": record.get("user_confirmation_required", False),
        "contract_lineage": lineage,
        "materiality_policy": record.get("materiality_policy", {}),
        "metadata": record.get("metadata", {}),
        "passive": record.get("passive", True),
        "canonical_state": record.get("canonical_state", False),
        "runtime_behavior_changed": record.get("runtime_behavior_changed", False),
        "accepted_authority": record.get("accepted_authority", False),
        "runtime_consumed": record.get("runtime_consumed", False),
        "constructs_search_work_plan": record.get("constructs_search_work_plan", False),
        "provider_search_behavior_changed": record.get("provider_search_behavior_changed", False),
    }


def _recompute_proposal_digest(record: Mapping[str, Any]) -> str:
    """Recompute the content-derived proposal digest from the payload itself."""

    return _digest_json(_proposal_record_digest_payload(record))


def build_initial_answer_contract_acceptance_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    question_meaning_record: Mapping[str, Any] | Any,
    run_id: str,
    request_id: str,
) -> dict[str, Any]:
    """Validate one passive proposal and build canonical acceptance state.

    Raises ``InitialAnswerContractAcceptanceError`` on any binding, payload, or
    closed-surface violation. The returned mapping is canonical RunKernel state.
    """

    clean_action_id = _clean_token(action_id, limit=200)
    if not clean_action_id:
        raise InitialAnswerContractAcceptanceError(
            "initial answer contract acceptance requires an authorized action id"
        )
    clean_run_id = _clean_token(run_id)
    clean_request_id = _clean_token(request_id)
    if not clean_run_id or not clean_request_id:
        raise InitialAnswerContractAcceptanceError("initial answer contract acceptance requires run_id and request_id")

    record = _safe_proposal_mapping(question_meaning_record)
    if not record:
        raise InitialAnswerContractAcceptanceError(
            "initial answer contract acceptance requires a passive question-meaning proposal payload"
        )

    forbidden = sorted(_collect_keys(record) & _FORBIDDEN_AUTHORITY_FIELDS)
    if forbidden:
        raise InitialAnswerContractAcceptanceError(
            "passive proposal includes closed authority fields: " + ", ".join(forbidden)
        )

    if record.get("passive") is not True:
        raise InitialAnswerContractAcceptanceError("initial answer contract acceptance requires a passive proposal")
    if record.get("canonical_state") is True:
        raise InitialAnswerContractAcceptanceError("passive proposal cannot already be canonical state")
    if record.get("runtime_behavior_changed") is True:
        raise InitialAnswerContractAcceptanceError("passive proposal must not have changed runtime behavior")
    if record.get("accepted_authority") is True:
        raise InitialAnswerContractAcceptanceError("passive proposal must not already be accepted authority")

    validation = record.get("validation")
    if isinstance(validation, Mapping) and validation.get("ok") is False:
        raise InitialAnswerContractAcceptanceError("passive proposal failed its own validation and cannot be accepted")

    parent_schema_version = _clean_token(record.get("schema_version"))
    if not parent_schema_version:
        raise InitialAnswerContractAcceptanceError("passive proposal requires a schema_version")
    parent_record_id = _clean_token(record.get("record_id"))
    if not parent_record_id:
        raise InitialAnswerContractAcceptanceError("passive proposal requires a record_id")
    parent_digest = _clean_token(record.get("record_digest"), limit=128)
    if not parent_digest:
        raise InitialAnswerContractAcceptanceError("passive proposal requires a record_digest")

    inputs = dict(action_inputs or {})
    expected_parent_id = _clean_token(inputs.get("parent_question_meaning_record_id"))
    expected_parent_digest = _clean_token(inputs.get("parent_proposal_digest"), limit=128)
    if not expected_parent_id or not expected_parent_digest:
        raise InitialAnswerContractAcceptanceError("authorized action must bind parent proposal id and digest")
    if expected_parent_id != parent_record_id:
        raise InitialAnswerContractAcceptanceError("parent proposal id binding does not match the proposal record_id")
    if expected_parent_digest != parent_digest:
        raise InitialAnswerContractAcceptanceError("parent proposal digest binding does not match the proposal digest")

    # The proposal digest is content-derived; recompute it from the payload to
    # reject a stale or tampered proposal that keeps the declared record_digest
    # while altering answer components, slots, caveats, or other content.
    recomputed_digest = _recompute_proposal_digest(record)
    if recomputed_digest != parent_digest:
        raise InitialAnswerContractAcceptanceError(
            "stale proposal payload: proposal digest does not match payload content"
        )
    if recomputed_digest != expected_parent_digest:
        raise InitialAnswerContractAcceptanceError(
            "parent proposal digest binding does not match recomputed proposal digest"
        )

    record_run_id = _clean_token(record.get("run_id"))
    if record_run_id and record_run_id != clean_run_id:
        raise InitialAnswerContractAcceptanceError("passive proposal run_id does not match the run")
    record_request_id = _clean_token(record.get("request_id"))
    if record_request_id and record_request_id != clean_request_id:
        raise InitialAnswerContractAcceptanceError("passive proposal request_id does not match the request")
    bound_request_id = _clean_token(inputs.get("request_id"))
    if bound_request_id and bound_request_id != clean_request_id:
        raise InitialAnswerContractAcceptanceError("authorized action request_id binding does not match the request")

    components = record.get("answer_components")
    if not isinstance(components, Sequence) or isinstance(components, str | bytes) or not components:
        raise InitialAnswerContractAcceptanceError("passive proposal requires at least one accepted answer component")

    accepted_components: list[dict[str, Any]] = []
    seen_component_ids: set[str] = set()
    for component in components:
        if not isinstance(component, Mapping):
            raise InitialAnswerContractAcceptanceError("answer component proposal must be a mapping")
        component_id = _clean_token(component.get("component_id"))
        component_revision = _clean_token(component.get("component_revision"))
        component_digest = _clean_token(component.get("component_digest"), limit=128)
        if not component_id or not component_revision or not component_digest:
            raise InitialAnswerContractAcceptanceError(
                "answer component requires component_id, component_revision, and component_digest"
            )
        if component_id in seen_component_ids:
            raise InitialAnswerContractAcceptanceError(f"duplicate answer component ref: {component_id}")
        seen_component_ids.add(component_id)
        accepted_components.append(_accepted_component_ref(component))

    for component in accepted_components:
        component_id = str(component["component_id"])
        for dependency_id in component.get("dependency_component_ids") or ():
            if dependency_id not in seen_component_ids:
                raise InitialAnswerContractAcceptanceError(
                    f"answer component {component_id} depends on missing accepted component {dependency_id}"
                )
            if dependency_id == component_id:
                raise InitialAnswerContractAcceptanceError(
                    f"answer component {component_id} cannot depend on itself"
                )

    accepted_slots: list[dict[str, Any]] = []
    for slot in record.get("semantic_slots") or ():
        if isinstance(slot, Mapping):
            accepted_slots.append(_accepted_slot_ref(slot))
    material_ambiguity_count = sum(1 for slot in accepted_slots if slot.get("unresolved_material"))

    contract_lineage = record.get("contract_lineage")
    contract_version = "0.1-passive"
    if isinstance(contract_lineage, Mapping):
        contract_version = _clean_token(contract_lineage.get("contract_version")) or contract_version

    materiality_policy = record.get("materiality_policy")
    materiality_policy = _json_safe(materiality_policy) if isinstance(materiality_policy, Mapping) else {}
    question_meaning_metadata = record.get("metadata")
    question_meaning_metadata = (
        _json_safe(question_meaning_metadata)
        if isinstance(question_meaning_metadata, Mapping)
        else {}
    )

    lineage = {
        "created_by": INITIAL_ANSWER_CONTRACT_ACCEPTANCE_OWNER,
        "created_from": ["passive_question_meaning_proposal"],
        "parent_proposal_digest": parent_digest,
        "reducer_action_id": clean_action_id,
    }

    state_core: dict[str, Any] = {
        "schema_version": INITIAL_ANSWER_CONTRACT_ACCEPTANCE_SCHEMA_VERSION,
        "owner": INITIAL_ANSWER_CONTRACT_ACCEPTANCE_OWNER,
        "trace_key": INITIAL_ANSWER_CONTRACT_ACCEPTANCE_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "accepted_contract_version": contract_version,
        "parent_question_meaning_record_id": parent_record_id,
        "parent_question_meaning_record_digest": parent_digest,
        "parent_proposal_schema_version": parent_schema_version,
        "accepted_answer_component_refs": accepted_components,
        "accepted_answer_component_count": len(accepted_components),
        "accepted_semantic_slot_refs": accepted_slots,
        "accepted_semantic_slot_count": len(accepted_slots),
        "material_ambiguity_count": material_ambiguity_count,
        "material_ambiguity_preserved": True,
        "materiality_policy": materiality_policy,
        "question_meaning_metadata": question_meaning_metadata,
        "lineage": lineage,
        # Closed surfaces remain closed for this acceptance bridge.
        "question_interpreted": False,
        "components_invented": False,
        "assumptions_added": False,
        "requirements_weakened": False,
        "material_ambiguity_resolved": False,
        "coverage_created": False,
        "amendment_created": False,
        "semantic_observation_admitted": False,
        "sufficiency_decided": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }
    accepted_contract_digest = _digest_json(_contract_content_digest_payload(state_core))
    return {**state_core, "accepted_contract_digest": accepted_contract_digest}


def build_initial_answer_contract_acceptance_projection(
    *,
    acceptance_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project canonical acceptance state with no raw or private data."""

    component_refs = [
        {
            "component_id": ref.get("component_id"),
            "component_revision": ref.get("component_revision"),
            "component_digest": ref.get("component_digest"),
            "requirement_posture": ref.get("requirement_posture"),
            "materiality": ref.get("materiality"),
            "dependency_component_ids": list(
                ref.get("dependency_component_ids") or ()
            ),
        }
        for ref in acceptance_state.get("accepted_answer_component_refs", [])
        if isinstance(ref, Mapping)
    ]
    slot_refs = [
        {
            "slot_id": ref.get("slot_id"),
            "slot_kind": ref.get("slot_kind"),
            "status": ref.get("status"),
            "materiality": ref.get("materiality"),
            "unresolved_material": ref.get("unresolved_material"),
        }
        for ref in acceptance_state.get("accepted_semantic_slot_refs", [])
        if isinstance(ref, Mapping)
    ]
    return {
        "owner": INITIAL_ANSWER_CONTRACT_ACCEPTANCE_OWNER,
        "schema_version": acceptance_state.get("schema_version"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": acceptance_state.get("run_id"),
        "request_id": acceptance_state.get("request_id"),
        "authorized_action_id": acceptance_state.get("authorized_action_id"),
        "accepted_contract_version": acceptance_state.get("accepted_contract_version"),
        "accepted_contract_digest": acceptance_state.get("accepted_contract_digest"),
        "parent_question_meaning_record_id": acceptance_state.get("parent_question_meaning_record_id"),
        "parent_question_meaning_record_digest": acceptance_state.get("parent_question_meaning_record_digest"),
        "parent_proposal_schema_version": acceptance_state.get("parent_proposal_schema_version"),
        "accepted_answer_component_refs": component_refs,
        "accepted_answer_component_count": len(component_refs),
        "accepted_semantic_slot_refs": slot_refs,
        "accepted_semantic_slot_count": len(slot_refs),
        "material_ambiguity_count": acceptance_state.get("material_ambiguity_count", 0),
        "material_ambiguity_preserved": acceptance_state.get("material_ambiguity_preserved", True),
        "question_meaning_metadata": acceptance_state.get(
            "question_meaning_metadata", {}
        ),
        "lineage": acceptance_state.get("lineage", {}),
        "coverage_created": False,
        "amendment_created": False,
        "semantic_observation_admitted": False,
        "sufficiency_decided": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "runtime_behavior_changed": False,
        "material_ambiguity_resolved": False,
        "requirements_weakened": False,
        "live_validation_not_run": True,
    }


__all__ = [
    "INITIAL_ANSWER_CONTRACT_ACCEPTANCE_OWNER",
    "INITIAL_ANSWER_CONTRACT_ACCEPTANCE_REASON",
    "INITIAL_ANSWER_CONTRACT_ACCEPTANCE_SCHEMA_VERSION",
    "INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE",
    "INITIAL_ANSWER_CONTRACT_ACCEPTANCE_TRACE_KEY",
    "InitialAnswerContractAcceptanceError",
    "build_initial_answer_contract_acceptance_projection",
    "build_initial_answer_contract_acceptance_state",
]
