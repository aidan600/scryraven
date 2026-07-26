"""RunKernel-owned contract amendment application runtime.

AG-RUN-CONTRACT-MUTATION-LOOP-01 applies already admitted contract
amendments into a versioned current accepted answer contract. Workers may
propose and admission may record, but this module performs the reducer-owned
application step.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.semantic_contract_foundation import (
    AnswerComponentContract,
    validate_answer_component_contract_set,
)

CONTRACT_AMENDMENT_APPLICATION_SCHEMA_VERSION = (
    "contract_amendment_application_ag_run_contract_mutation_loop_01_v1"
)
CURRENT_ANSWER_CONTRACT_SCHEMA_VERSION = (
    "current_answer_contract_ag_run_contract_mutation_loop_01_v1"
)
CONTRACT_AMENDMENT_APPLICATION_STAGE = "contract_amendment_application"
CONTRACT_AMENDMENT_APPLICATION_REASON = (
    "contract_amendment_application_from_admitted_contract_amendment"
)
CONTRACT_AMENDMENT_APPLICATION_TRACE_KEY = "contract_amendment_application"
CONTRACT_AMENDMENT_APPLICATION_OWNER = "RunKernel.ContractAmendmentApplication"
CURRENT_ANSWER_CONTRACT_OWNER = "RunKernel.CurrentAnswerContract"

REQUIREMENT_LIFECYCLE_STATUSES = (
    "pending",
    "satisfied",
    "failed",
    "blocked",
    "not_applicable",
    "superseded",
)

REQUIREMENT_LIFECYCLE_STATUS_DEFINITIONS = {
    "pending": (
        "the requirement remains active and needs semantic coverage before "
        "readiness may pass"
    ),
    "satisfied": (
        "the requirement is covered by matching semantic coverage and "
        "qualified EvidenceLedger custody"
    ),
    "failed": "the requirement is active but known not to be satisfiable",
    "blocked": "the requirement is active but an explicit blocker prevents use",
    "not_applicable": (
        "explicit authority marks the requirement outside the accepted answer "
        "contract for this run"
    ),
    "superseded": (
        "explicit authority replaces the requirement with a later accepted "
        "requirement"
    ),
}

_REQUIRED_INPUT_KEYS = frozenset(
    {
        "parent_contract_version",
        "parent_contract_digest",
        "amendment_record_id",
        "amendment_record_digest",
        "admission_digest",
        "request_id",
    }
)
_ALLOWED_USER_AUTHORITY = frozenset(
    {
        "explicit_user_confirmation",
        "labeled_scenario_treatment",
        "explicit_user_authority",
        "required_to_fulfill_existing_accepted_user_obligation",
    }
)
_BLOCKING_DISPOSITIONS = frozenset({"rejected", "blocked"})
_UNCONFIRMED_POSTURES = frozenset(
    {"requires_user_confirmation", "unknown", "missing"}
)
_STATUS_REQUIRING_EXPLICIT_AUTHORITY = frozenset(
    {"not_applicable", "superseded"}
)
_SATISFIED_REQUIRED_BASIS = frozenset(
    {
        "semantic_observation",
        "answer_bearing_content",
        "evidence_ledger_custody",
    }
)
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
_FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "author_input",
        "canonical_coverage",
        "coverage_decision",
        "final_answer",
        "final_answer_packet",
        "followup_activation",
        "query_plan_activation",
        "search_judgment_decision",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)
_FALSE_CLOSED_SURFACE_FLAGS = {
    "planner_runtime_activated": False,
    "scout_runtime_activated": False,
    "search_executor_runtime_activated": False,
    "provider_search_behavior_changed": False,
    "fetch_read_retrieval_behavior_changed": False,
    "author_behavior_changed": False,
    "citation_behavior_changed": False,
    "prompt_behavior_changed": False,
    "partial_answer_readiness_changed": False,
    "live_validation_run": False,
    "initial_answer_contract_mutated": False,
    "admission_record_mutated": False,
    "coverage_invalidation_applied": False,
    "coverage_marked_stale": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "search_judgment_decided": False,
    "query_plan_activated": False,
    "search_work_plan_activated": False,
    "followup_authorized": False,
    "runtime_behavior_changed": False,
}


class ContractAmendmentApplicationError(ValueError):
    """Raised when an admitted amendment cannot be applied."""


def _clean_text(value: Any, *, limit: int = 1000) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\x00", "").strip()
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 200) -> str | None:
    text = _clean_text(value, limit=limit)
    if text is None:
        return None
    return " ".join(text.split())


def _normalized_token(value: Any) -> str:
    return (_clean_token(value) or "").casefold()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            clean_key = _clean_token(key, limit=160)
            if not clean_key or clean_key.casefold() in _SENSITIVE_KEYS:
                continue
            result[clean_key] = _json_safe(item)
        return result
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str):
            return _clean_text(value, limit=1000)
        return value
    return _clean_text(value, limit=400)


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return dict(_json_safe(value))


def _safe_list(value: Any) -> list[Any]:
    if not isinstance(value, (list, tuple)):
        return []
    return list(_json_safe(value))


def _text_list(value: Any, *, limit: int = 240) -> list[str]:
    items: list[str] = []
    if isinstance(value, str):
        iterable: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        iterable = value
    else:
        iterable = ()
    for item in iterable:
        clean = _clean_text(item, limit=limit)
        if clean and clean not in items:
            items.append(clean)
    return items


def _token_list(value: Any, *, limit: int = 200) -> list[str]:
    items: list[str] = []
    if isinstance(value, str):
        iterable: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        iterable = value
    else:
        iterable = ()
    for item in iterable:
        clean = _clean_token(item, limit=limit)
        if clean and clean not in items:
            items.append(clean)
    return items


def _dedupe_mapping_list(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        safe = _safe_mapping(item)
        key = json.dumps(safe, sort_keys=True, separators=(",", ":"))
        if key not in seen:
            result.append(safe)
            seen.add(key)
    return result


def _collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            clean = _clean_token(key, limit=160)
            if clean:
                keys.add(clean.casefold())
            keys.update(_collect_keys(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            keys.update(_collect_keys(item))
    return keys


def _digest_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractAmendmentApplicationError(message)


def _contract_version_digest(contract: Mapping[str, Any]) -> tuple[str, str]:
    return (
        _clean_token(contract.get("accepted_contract_version")) or "",
        _clean_token(contract.get("accepted_contract_digest"), limit=128) or "",
    )


def _component_index(
    components: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        component_id: component
        for component in components
        if isinstance(component, dict)
        and (component_id := _clean_token(component.get("component_id")))
    }


def _component_ref_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    component_id = _clean_token(payload.get("component_id"))
    revision = _clean_token(
        payload.get("component_revision") or payload.get("revision")
    )
    digest = _clean_token(
        payload.get("component_digest")
        or payload.get("contract_digest")
        or payload.get("digest"),
        limit=128,
    )
    _require(bool(component_id), "add_component requires component_id")
    _require(bool(revision), "add_component requires component_revision")
    _require(bool(digest), "add_component requires component_digest")
    return {
        "component_id": component_id,
        "component_revision": revision,
        "component_digest": digest,
        "component_purpose": _clean_token(payload.get("component_purpose"))
        or "user_facing_answer_target",
        "user_facing_label": _clean_text(
            payload.get("user_facing_label"), limit=240
        ),
        "user_facing_question": _clean_text(
            payload.get("user_facing_question"), limit=600
        ),
        "acceptance_criteria": _text_list(payload.get("acceptance_criteria")),
        "semantic_slot_ids": _token_list(payload.get("semantic_slot_ids")),
        "max_inference_depth": int(payload.get("max_inference_depth") or 0),
        "requirement_posture": _clean_token(
            payload.get("requirement_posture"),
        )
        or "required",
        "materiality": _clean_token(payload.get("materiality")) or "material",
        "allowed_support_kinds": _token_list(payload.get("allowed_support_kinds")),
        "source_obligation_candidate_ids": _token_list(
            payload.get("source_obligation_candidate_ids")
        ),
        "source_obligation_candidate_refs": _safe_list(
            payload.get("source_obligation_candidate_refs")
        ),
        "dependency_component_ids": _token_list(
            payload.get("dependency_component_ids")
        ),
        "normalization_policy": _clean_text(
            payload.get("normalization_policy"), limit=300
        ),
        "calculation_policy": _clean_text(
            payload.get("calculation_policy"), limit=300
        ),
        "partial_answer_policy": _clean_token(
            payload.get("partial_answer_policy")
        )
        or "qualify_visible_gap",
        "mandatory_caveats": _text_list(
            payload.get("mandatory_caveats") or payload.get("required_caveats")
        ),
        "prohibited_upgrades": _text_list(payload.get("prohibited_upgrades")),
        "metadata": _safe_mapping(payload.get("metadata")),
        "lifecycle_status": "pending",
        "lifecycle_status_authority": "contract_amendment_application_default",
    }


def _extract_component_payload(operation: Mapping[str, Any]) -> dict[str, Any]:
    operation_payload = _safe_mapping(operation.get("operation_payload"))
    after_payload = _safe_mapping(operation.get("after_payload"))
    before_payload = _safe_mapping(operation.get("before_payload"))
    candidates = (
        _safe_mapping(operation_payload.get("component")),
        _safe_mapping(after_payload.get("component")),
        operation_payload,
        after_payload,
        before_payload,
    )
    for candidate in candidates:
        if candidate.get("component_id"):
            return candidate
    return {}


def _operation_kind(operation: Mapping[str, Any]) -> str:
    payload = _safe_mapping(operation.get("operation_payload"))
    return _normalized_token(
        payload.get("normalized_operation_kind")
        or payload.get("operation")
        or operation.get("operation_kind")
    )


def _target_component_ids(
    operation: Mapping[str, Any],
    admission: Mapping[str, Any],
) -> list[str]:
    payload = _safe_mapping(operation.get("operation_payload"))
    targets = _token_list(
        payload.get("component_ids")
        or payload.get("target_component_ids")
        or payload.get("target_requirement_ids")
    )
    target = _clean_token(
        payload.get("component_id")
        or payload.get("target_component_id")
        or payload.get("requirement_id")
        or payload.get("target_requirement_id")
    )
    if target and target not in targets:
        targets.append(target)
    for ref in _safe_list(admission.get("affected_component_refs")):
        if isinstance(ref, Mapping):
            component_id = _clean_token(ref.get("component_id"))
            if component_id and component_id not in targets:
                targets.append(component_id)
    return targets


def _append_unique_text(target: list[str], values: Sequence[str]) -> None:
    for value in values:
        clean = _clean_text(value, limit=500)
        if clean and clean not in target:
            target.append(clean)


def _append_unique_mapping(
    target: list[dict[str, Any]],
    values: Sequence[Mapping[str, Any]],
) -> None:
    target[:] = _dedupe_mapping_list([*target, *values])


def _operation_has_explicit_authority(
    operation: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> bool:
    payload = _safe_mapping(operation.get("operation_payload"))
    if _normalized_token(operation.get("user_authority_ref")):
        return True
    if bool(operation.get("labeled_scenario_treatment")):
        return True
    if _normalized_token(payload.get("user_authority_ref")):
        return True
    if _normalized_token(action_inputs.get("user_authority_ref")):
        return True
    return (
        _normalized_token(action_inputs.get("user_confirmation_posture"))
        in _ALLOWED_USER_AUTHORITY
    )


def _admission_has_application_authority(
    admission: Mapping[str, Any],
    operations: Sequence[Mapping[str, Any]],
    action_inputs: Mapping[str, Any],
) -> bool:
    user_confirmation = _normalized_token(admission.get("user_confirmation_posture"))
    if user_confirmation in _ALLOWED_USER_AUTHORITY:
        return True
    if _normalized_token(action_inputs.get("user_confirmation_posture")) in (
        _ALLOWED_USER_AUTHORITY
    ):
        return True
    if _normalized_token(action_inputs.get("user_authority_ref")):
        return True
    return any(
        _operation_has_explicit_authority(operation, action_inputs)
        for operation in operations
    )


def _latest_coverage_by_component(
    component_coverage_history: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for item in component_coverage_history:
        if not isinstance(item, Mapping):
            continue
        component_id = _clean_token(item.get("answer_component_id"))
        if component_id:
            latest[component_id] = _safe_mapping(item)
    return latest


def _require_satisfied_coverage(
    *,
    component: Mapping[str, Any],
    parent_contract: Mapping[str, Any],
    component_coverage_history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    component_id = _clean_token(component.get("component_id")) or ""
    component_digest = _clean_token(component.get("component_digest"), limit=128)
    parent_version, parent_digest = _contract_version_digest(parent_contract)
    coverage = _latest_coverage_by_component(component_coverage_history).get(
        component_id,
        {},
    )
    if not coverage:
        raise ContractAmendmentApplicationError(
            "satisfied status requires matching semantic coverage; "
            f"no coverage exists for {component_id}"
        )
    coverage_state = _normalized_token(coverage.get("coverage_state"))
    if coverage_state != "satisfied":
        raise ContractAmendmentApplicationError(
            "satisfied status requires semantic coverage in satisfied state"
        )
    if _clean_token(coverage.get("accepted_contract_version")) != parent_version:
        raise ContractAmendmentApplicationError(
            "satisfied status requires coverage bound to the parent contract version"
        )
    if (
        _clean_token(coverage.get("accepted_contract_digest"), limit=128)
        != parent_digest
    ):
        raise ContractAmendmentApplicationError(
            "satisfied status requires coverage bound to the parent contract digest"
        )
    if _clean_token(coverage.get("component_digest"), limit=128) != component_digest:
        raise ContractAmendmentApplicationError(
            "satisfied status requires coverage bound to the component digest"
        )
    if _normalized_token(coverage.get("evidence_custody_status")) != "custodied":
        raise ContractAmendmentApplicationError(
            "satisfied status requires qualified EvidenceLedger custody"
        )
    evidence_basis = {
        _normalized_token(item) for item in _safe_list(coverage.get("evidence_basis"))
    }
    if not _SATISFIED_REQUIRED_BASIS.issubset(evidence_basis):
        raise ContractAmendmentApplicationError(
            "satisfied status requires semantic observation, answer-bearing "
            "content, and EvidenceLedger custody basis"
        )
    if _normalized_token(coverage.get("source_obligation_status")) in {
        "unsatisfied",
        "partial",
        "unknown",
        "stale",
    }:
        raise ContractAmendmentApplicationError(
            "satisfied status requires source obligations to be qualified or "
            "not applicable"
        )
    return _safe_mapping(coverage)


def _set_component_status(
    component_index: dict[str, dict[str, Any]],
    component_id: str,
    status: str,
    *,
    authority: str,
    reason: str | None = None,
    superseded_by: str | None = None,
) -> None:
    component = component_index.get(component_id)
    if component is None:
        raise ContractAmendmentApplicationError(
            f"lifecycle status target {component_id} is not in current contract"
        )
    if status not in REQUIREMENT_LIFECYCLE_STATUSES:
        raise ContractAmendmentApplicationError(
            f"unsupported requirement lifecycle status: {status}"
        )
    component["lifecycle_status"] = status
    component["lifecycle_status_authority"] = authority
    if reason:
        component["lifecycle_status_reason"] = _clean_text(reason, limit=360)
    if superseded_by:
        component["superseded_by_requirement_id"] = _clean_token(superseded_by)


def _current_contract_digest_payload(state_core: Mapping[str, Any]) -> dict[str, Any]:
    lineage = dict(state_core.get("lineage") or {})
    lineage.pop("reducer_action_id", None)
    lineage.pop("application_digest", None)
    lineage.pop("current_contract_digest", None)
    return {
        "schema_version": state_core.get("schema_version"),
        "accepted_contract_version": state_core.get("accepted_contract_version"),
        "previous_contract_version": state_core.get("previous_contract_version"),
        "previous_contract_digest": state_core.get("previous_contract_digest"),
        "initial_contract_version": state_core.get("initial_contract_version"),
        "initial_contract_digest": state_core.get("initial_contract_digest"),
        "parent_question_meaning_record_id": state_core.get(
            "parent_question_meaning_record_id"
        ),
        "parent_question_meaning_record_digest": state_core.get(
            "parent_question_meaning_record_digest"
        ),
        "parent_proposal_schema_version": state_core.get(
            "parent_proposal_schema_version"
        ),
        "accepted_answer_component_refs": state_core.get(
            "accepted_answer_component_refs"
        ),
        "accepted_semantic_slot_refs": state_core.get(
            "accepted_semantic_slot_refs"
        ),
        "materiality_policy": state_core.get("materiality_policy"),
        "mandatory_caveats": state_core.get("mandatory_caveats"),
        "prohibited_upgrades": state_core.get("prohibited_upgrades"),
        "normalization_obligations": state_core.get("normalization_obligations"),
        "assumptions": state_core.get("assumptions"),
        "review_obligations": state_core.get("review_obligations"),
        "irreducible_unknowns": state_core.get("irreducible_unknowns"),
        "requirement_lifecycle": state_core.get("requirement_lifecycle"),
        "applied_amendment_refs": state_core.get("applied_amendment_refs"),
        "lineage": lineage,
    }


def _application_digest_payload(state_core: Mapping[str, Any]) -> dict[str, Any]:
    lineage = dict(state_core.get("lineage") or {})
    lineage.pop("reducer_action_id", None)
    return {
        "schema_version": state_core.get("schema_version"),
        "run_id": state_core.get("run_id"),
        "request_id": state_core.get("request_id"),
        "amendment_record_id": state_core.get("amendment_record_id"),
        "amendment_record_digest": state_core.get("amendment_record_digest"),
        "admission_digest": state_core.get("admission_digest"),
        "parent_contract_version": state_core.get("parent_contract_version"),
        "parent_contract_digest": state_core.get("parent_contract_digest"),
        "current_contract_version": state_core.get("current_contract_version"),
        "current_contract_digest": state_core.get("current_contract_digest"),
        "applied_operation_kinds": state_core.get("applied_operation_kinds"),
        "requirement_lifecycle_summary": state_core.get(
            "requirement_lifecycle_summary"
        ),
        "lineage": lineage,
    }


def _build_requirement_lifecycle(
    components: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    statuses = []
    for component in components:
        component_id = _clean_token(component.get("component_id")) or ""
        status = _normalized_token(component.get("lifecycle_status")) or "pending"
        if status not in REQUIREMENT_LIFECYCLE_STATUSES:
            status = "pending"
        statuses.append(
            {
                "requirement_id": component_id,
                "component_id": component_id,
                "status": status,
                "status_authority": _clean_token(
                    component.get("lifecycle_status_authority")
                )
                or "contract_amendment_application_default",
                "reason": _clean_text(component.get("lifecycle_status_reason")),
                "superseded_by_requirement_id": _clean_token(
                    component.get("superseded_by_requirement_id")
                ),
                "satisfied_requires_semantic_coverage": True,
                "satisfied_requires_ledger_qualification": True,
            }
        )
    return {
        "statuses": list(REQUIREMENT_LIFECYCLE_STATUSES),
        "status_definitions": dict(REQUIREMENT_LIFECYCLE_STATUS_DEFINITIONS),
        "component_statuses": statuses,
    }


def _require_current_contract_ref(
    *,
    current_answer_contract: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> None:
    current_version, current_digest = _contract_version_digest(current_answer_contract)
    _require(bool(current_version and current_digest), "parent contract requires version/digest")
    bound_version = _clean_token(action_inputs.get("parent_contract_version"))
    bound_digest = _clean_token(action_inputs.get("parent_contract_digest"), limit=128)
    if bound_version != current_version:
        raise ContractAmendmentApplicationError(
            "stale parent contract version: action binding does not match "
            "current accepted answer contract"
        )
    if bound_digest != current_digest:
        raise ContractAmendmentApplicationError(
            "stale parent contract digest: action binding does not match "
            "current accepted answer contract"
        )


def _validate_application_bindings(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any],
    admitted_amendment: Mapping[str, Any],
    parent_contract: Mapping[str, Any],
    initial_contract: Mapping[str, Any],
    run_id: str,
    request_id: str,
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    clean_action_id = _clean_token(action_id, limit=200)
    if not clean_action_id:
        raise ContractAmendmentApplicationError(
            "contract amendment application requires an authorized action id"
        )
    clean_run_id = _clean_token(run_id)
    clean_request_id = _clean_token(request_id)
    if not clean_run_id or not clean_request_id:
        raise ContractAmendmentApplicationError(
            "contract amendment application requires run_id and request_id"
        )
    inputs = _safe_mapping(action_inputs)
    missing_inputs = sorted(
        key for key in _REQUIRED_INPUT_KEYS if not _clean_token(inputs.get(key))
    )
    if missing_inputs:
        raise ContractAmendmentApplicationError(
            "authorized action must bind: " + ", ".join(missing_inputs)
        )
    if _clean_token(inputs.get("request_id")) != clean_request_id:
        raise ContractAmendmentApplicationError(
            "authorized action request_id binding does not match the request"
        )
    initial = _safe_mapping(initial_contract)
    if not initial or initial.get("canonical_state") is not True:
        raise ContractAmendmentApplicationError(
            "contract amendment application requires initial_answer_contract"
        )
    parent = _safe_mapping(parent_contract)
    if not parent or parent.get("canonical_state") is not True:
        raise ContractAmendmentApplicationError(
            "contract amendment application requires a current accepted parent "
            "contract"
        )
    admission = _safe_mapping(admitted_amendment)
    if not admission or admission.get("canonical_state") is not True:
        raise ContractAmendmentApplicationError(
            "contract amendment application requires canonical admitted amendment"
        )
    forbidden = sorted(_collect_keys(inputs) & _FORBIDDEN_AUTHORITY_FIELDS)
    if forbidden:
        raise ContractAmendmentApplicationError(
            "application inputs include closed authority fields: "
            + ", ".join(forbidden)
        )

    _require_current_contract_ref(
        current_answer_contract=parent,
        action_inputs=inputs,
    )
    if _clean_token(admission.get("run_id")) != clean_run_id:
        raise ContractAmendmentApplicationError(
            "admitted amendment run_id does not match the run"
        )
    if _clean_token(admission.get("request_id")) != clean_request_id:
        raise ContractAmendmentApplicationError(
            "admitted amendment request_id does not match the request"
        )
    for key in (
        "amendment_record_id",
        "amendment_record_digest",
        "admission_digest",
    ):
        limit = 128 if key.endswith("digest") else 200
        if _clean_token(inputs.get(key), limit=limit) != _clean_token(
            admission.get(key),
            limit=limit,
        ):
            raise ContractAmendmentApplicationError(
                f"action {key} binding does not match the admitted amendment"
            )
    return clean_action_id, inputs, admission, parent


def _require_admission_parent_matches(
    *,
    admitted_amendment: Mapping[str, Any],
    parent_contract: Mapping[str, Any],
) -> None:
    parent_version, parent_digest = _contract_version_digest(parent_contract)
    if _clean_token(admitted_amendment.get("parent_contract_version")) != parent_version:
        raise ContractAmendmentApplicationError(
            "admitted amendment parent contract version does not match current "
            "accepted answer contract"
        )
    if (
        _clean_token(admitted_amendment.get("parent_contract_digest"), limit=128)
        != parent_digest
    ):
        raise ContractAmendmentApplicationError(
            "admitted amendment parent contract digest does not match current "
            "accepted answer contract"
        )


def _reject_duplicate_application(
    *,
    action_id: str,
    admitted_amendment: Mapping[str, Any],
    parent_contract: Mapping[str, Any],
    application_history: Sequence[Mapping[str, Any]],
) -> None:
    amendment_id = _clean_token(admitted_amendment.get("amendment_record_id"))
    amendment_digest = _clean_token(
        admitted_amendment.get("amendment_record_digest"),
        limit=128,
    )
    admission_digest = _clean_token(admitted_amendment.get("admission_digest"), limit=128)
    candidates = [
        *_safe_list(parent_contract.get("applied_amendment_refs")),
        *_safe_list(application_history),
    ]
    for item in candidates:
        if not isinstance(item, Mapping):
            continue
        if _clean_token(item.get("authorized_action_id")) == action_id:
            raise ContractAmendmentApplicationError(
                "duplicate contract amendment application action"
            )
        if amendment_id and _clean_token(item.get("amendment_record_id")) == amendment_id:
            raise ContractAmendmentApplicationError(
                "duplicate contract amendment application for admitted amendment id"
            )
        if (
            amendment_digest
            and _clean_token(item.get("amendment_record_digest"), limit=128)
            == amendment_digest
        ):
            raise ContractAmendmentApplicationError(
                "duplicate contract amendment application for amendment digest"
            )
        if (
            admission_digest
            and _clean_token(item.get("admission_digest"), limit=128)
            == admission_digest
        ):
            raise ContractAmendmentApplicationError(
                "duplicate contract amendment application for admission digest"
            )


def _reject_unapplicable_admission(
    *,
    admitted_amendment: Mapping[str, Any],
    operations: Sequence[Mapping[str, Any]],
    action_inputs: Mapping[str, Any],
) -> None:
    disposition = _normalized_token(admitted_amendment.get("disposition"))
    if disposition in _BLOCKING_DISPOSITIONS:
        raise ContractAmendmentApplicationError(
            f"cannot apply {disposition} contract amendment admission"
        )
    if _safe_list(admitted_amendment.get("blocking_reasons")):
        raise ContractAmendmentApplicationError(
            "cannot apply contract amendment admission with blocking reasons"
        )
    has_application_authority = _admission_has_application_authority(
        admitted_amendment,
        operations,
        action_inputs,
    )
    user_confirmation = _normalized_token(
        admitted_amendment.get("user_confirmation_posture")
    )
    materiality = _normalized_token(admitted_amendment.get("materiality"))
    needs_confirmation = (
        disposition == "requires_user_confirmation"
        or user_confirmation in _UNCONFIRMED_POSTURES
        or materiality == "material"
        or any(bool(operation.get("user_confirmation_required")) for operation in operations)
    )
    if needs_confirmation and not has_application_authority:
        raise ContractAmendmentApplicationError(
            "material or confirmation-gated amendment requires explicit user "
            "confirmation or authority before application"
        )
    if disposition != "eligible_for_future_acceptance" and not (
        has_application_authority
    ):
        raise ContractAmendmentApplicationError(
            "contract amendment application requires eligible future "
            "acceptance disposition or explicit user authority"
        )


def _apply_operations(
    *,
    parent_contract: Mapping[str, Any],
    admitted_amendment: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
    component_coverage_history: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    components = [
        _safe_mapping(component)
        for component in _safe_list(parent_contract.get("accepted_answer_component_refs"))
        if isinstance(component, Mapping)
    ]
    for component in components:
        component.setdefault("lifecycle_status", "pending")
        component.setdefault(
            "lifecycle_status_authority",
            "contract_amendment_application_default",
        )
    slots = [
        _safe_mapping(slot)
        for slot in _safe_list(parent_contract.get("accepted_semantic_slot_refs"))
        if isinstance(slot, Mapping)
    ]
    component_index = _component_index(components)
    contract_caveats = _text_list(parent_contract.get("mandatory_caveats"))
    contract_prohibited_upgrades = _text_list(
        parent_contract.get("prohibited_upgrades")
    )
    normalization_obligations = _safe_list(
        parent_contract.get("normalization_obligations")
    )
    assumptions = _safe_list(parent_contract.get("assumptions"))
    review_obligations = _safe_list(parent_contract.get("review_obligations"))
    irreducible_unknowns = _safe_list(parent_contract.get("irreducible_unknowns"))
    applied_operations: list[dict[str, Any]] = []
    unsupported_operations: list[str] = []
    operations = [
        _safe_mapping(operation)
        for operation in _safe_list(admitted_amendment.get("operations"))
        if isinstance(operation, Mapping)
    ]

    for operation in operations:
        kind = _operation_kind(operation)
        operation_id = _clean_token(operation.get("operation_id")) or kind
        payload = _safe_mapping(operation.get("operation_payload"))
        target_ids = _target_component_ids(operation, admitted_amendment)
        operation_summary = {
            "operation_id": operation_id,
            "operation_kind": kind,
            "target_component_ids": target_ids,
        }

        if kind in {"add_component", "add_requirement"}:
            component_payload = _extract_component_payload(operation)
            if not component_payload:
                unsupported_operations.append(f"{operation_id}:missing_component")
                continue
            component_ref = _component_ref_from_payload(component_payload)
            component_id = component_ref["component_id"]
            if component_id in component_index:
                raise ContractAmendmentApplicationError(
                    f"add_component target {component_id} already exists"
                )
            component_index[component_id] = component_ref
            components.append(component_ref)
            operation_summary["created_component_id"] = component_id
        elif kind == "revise_component":
            component_payload = _extract_component_payload(operation)
            component_ref = _component_ref_from_payload(component_payload)
            component_id = component_ref["component_id"]
            if component_id not in component_index:
                raise ContractAmendmentApplicationError(
                    f"revise_component target {component_id} is not present"
                )
            original = component_index[component_id]
            component_ref["previous_component_digest"] = original.get(
                "component_digest"
            )
            component_ref["lifecycle_status"] = (
                _clean_token(original.get("lifecycle_status")) or "pending"
            )
            component_index[component_id] = component_ref
            components[:] = [
                component_ref if item.get("component_id") == component_id else item
                for item in components
            ]
            operation_summary["revised_component_id"] = component_id
        elif kind == "resolve_slot":
            slot_id = _clean_token(payload.get("slot_id"))
            if not slot_id:
                unsupported_operations.append(f"{operation_id}:missing_slot_id")
                continue
            selected_value = _clean_text(payload.get("selected_value"), limit=500)
            found = False
            for slot in slots:
                if _clean_token(slot.get("slot_id")) == slot_id:
                    slot["status"] = _clean_token(payload.get("status")) or "selected"
                    if selected_value is not None:
                        slot["selected_value"] = selected_value
                    slot["unresolved_material"] = False
                    found = True
            if not found:
                slots.append(
                    {
                        "slot_id": slot_id,
                        "slot_kind": _clean_token(payload.get("slot_kind")),
                        "status": _clean_token(payload.get("status")) or "selected",
                        "selected_value": selected_value,
                        "materiality": _clean_token(payload.get("materiality")),
                        "unresolved_material": False,
                    }
                )
            operation_summary["resolved_slot_id"] = slot_id
        elif kind in {
            "strengthen_source_obligation",
            "add_source_obligation",
            "add_fetch_read_obligation",
        }:
            refs = [
                _safe_mapping(ref)
                for ref in _safe_list(
                    payload.get("source_obligation_candidate_refs")
                    or payload.get("source_obligation_refs")
                    or payload.get("fetch_read_obligation_refs")
                )
                if isinstance(ref, Mapping)
            ]
            ids = _token_list(
                payload.get("source_obligation_candidate_ids")
                or payload.get("source_obligation_ids")
                or payload.get("fetch_read_obligation_ids")
            )
            if not refs and not ids:
                unsupported_operations.append(f"{operation_id}:missing_obligation")
                continue
            targets = target_ids or list(component_index)
            for component_id in targets:
                component = component_index.get(component_id)
                if component is None:
                    raise ContractAmendmentApplicationError(
                        f"source obligation target {component_id} is not present"
                    )
                existing_ids = _token_list(
                    component.get("source_obligation_candidate_ids")
                )
                _append_unique_text(existing_ids, ids)
                component["source_obligation_candidate_ids"] = existing_ids
                existing_refs = [
                    _safe_mapping(ref)
                    for ref in _safe_list(
                        component.get("source_obligation_candidate_refs")
                    )
                    if isinstance(ref, Mapping)
                ]
                _append_unique_mapping(existing_refs, refs)
                component["source_obligation_candidate_refs"] = existing_refs
            operation_summary["obligation_count"] = len(refs) + len(ids)
        elif kind == "add_caveat":
            caveats = _text_list(
                payload.get("caveats")
                or payload.get("required_caveats")
                or payload.get("mandatory_caveats")
                or payload.get("caveat")
            )
            if not caveats:
                caveats = _text_list(admitted_amendment.get("required_caveats"))
            _append_unique_text(contract_caveats, caveats)
            for component_id in target_ids:
                component = component_index.get(component_id)
                if component is None:
                    continue
                existing = _text_list(component.get("mandatory_caveats"))
                _append_unique_text(existing, caveats)
                component["mandatory_caveats"] = existing
            operation_summary["caveat_count"] = len(caveats)
        elif kind in {"change_answer_posture", "change_requirement_posture"}:
            posture = _clean_token(
                payload.get("requirement_posture")
                or payload.get("answer_posture")
                or payload.get("posture")
            )
            if not posture:
                unsupported_operations.append(f"{operation_id}:missing_posture")
                continue
            if _normalized_token(posture) in {"optional", "removed"} and not (
                _operation_has_explicit_authority(operation, action_inputs)
            ):
                raise ContractAmendmentApplicationError(
                    "meaning-changing or weakening posture change requires "
                    "explicit authority"
                )
            for component_id in target_ids:
                component = component_index.get(component_id)
                if component is None:
                    raise ContractAmendmentApplicationError(
                        f"posture target {component_id} is not present"
                    )
                component["requirement_posture"] = posture
            operation_summary["posture"] = posture
        elif kind in {
            "mark_requirement_satisfied",
            "mark_requirement_failed",
            "mark_requirement_blocked",
            "mark_requirement_not_applicable",
            "supersede_requirement",
        }:
            if kind == "mark_requirement_satisfied":
                status = "satisfied"
            elif kind == "mark_requirement_failed":
                status = "failed"
            elif kind == "mark_requirement_blocked":
                status = "blocked"
            elif kind == "mark_requirement_not_applicable":
                status = "not_applicable"
            else:
                status = "superseded"
            if status in _STATUS_REQUIRING_EXPLICIT_AUTHORITY and not (
                _operation_has_explicit_authority(operation, action_inputs)
            ):
                raise ContractAmendmentApplicationError(
                    f"{status} lifecycle status requires explicit authority"
                )
            for component_id in target_ids:
                component = component_index.get(component_id)
                if component is None:
                    raise ContractAmendmentApplicationError(
                        f"lifecycle target {component_id} is not present"
                    )
                if status == "satisfied":
                    _require_satisfied_coverage(
                        component=component,
                        parent_contract=parent_contract,
                        component_coverage_history=component_coverage_history,
                    )
                _set_component_status(
                    component_index,
                    component_id,
                    status,
                    authority="explicit_contract_amendment_application",
                    reason=_clean_text(payload.get("reason"), limit=360),
                    superseded_by=_clean_token(
                        payload.get("superseded_by_requirement_id")
                        or payload.get("superseded_by_component_id")
                    ),
                )
            operation_summary["lifecycle_status"] = status
        elif kind in {"add_review_or_redteam_obligation", "add_review_obligation"}:
            obligation = _safe_mapping(payload.get("review_obligation") or payload)
            if not obligation:
                unsupported_operations.append(f"{operation_id}:missing_review")
                continue
            review_obligations = _dedupe_mapping_list(
                [*review_obligations, obligation]
            )
            operation_summary["review_obligation_added"] = True
        elif kind == "prohibit_upgrade":
            upgrades = _text_list(
                payload.get("prohibited_upgrades")
                or payload.get("prohibit")
                or payload.get("upgrade")
            )
            _append_unique_text(contract_prohibited_upgrades, upgrades)
            operation_summary["prohibited_upgrade_count"] = len(upgrades)
        elif kind in {"add_normalization", "add_assumption"}:
            target = normalization_obligations if kind == "add_normalization" else assumptions
            target.append(_safe_mapping(payload) or {"operation_id": operation_id})
            operation_summary["recorded_as_contract_obligation"] = True
        elif kind == "mark_irreducible_unknown":
            unknown = _safe_mapping(payload) or {"operation_id": operation_id}
            irreducible_unknowns = _dedupe_mapping_list(
                [*irreducible_unknowns, unknown]
            )
            operation_summary["irreducible_unknown_recorded"] = True
        elif kind == "remove_or_weaken_requirement":
            if not _operation_has_explicit_authority(operation, action_inputs):
                raise ContractAmendmentApplicationError(
                    "remove_or_weaken_requirement requires explicit authority"
                )
            unsupported_operations.append(f"{operation_id}:deferred_weakening")
            continue
        else:
            unsupported_operations.append(f"{operation_id}:{kind or 'unknown'}")
            continue
        applied_operations.append(operation_summary)

    if unsupported_operations:
        raise ContractAmendmentApplicationError(
            "unsupported or deferred amendment operations: "
            + ", ".join(unsupported_operations)
        )

    _append_unique_text(contract_caveats, _text_list(admitted_amendment.get("required_caveats")))
    _append_unique_text(
        contract_prohibited_upgrades,
        _text_list(admitted_amendment.get("prohibited_upgrades")),
    )
    mutations = {
        "mandatory_caveats": contract_caveats,
        "prohibited_upgrades": contract_prohibited_upgrades,
        "normalization_obligations": normalization_obligations,
        "assumptions": assumptions,
        "review_obligations": review_obligations,
        "irreducible_unknowns": irreducible_unknowns,
        "applied_operations": applied_operations,
    }
    return components, slots, mutations


def build_current_answer_contract_projection(
    *,
    current_answer_contract: Mapping[str, Any],
) -> dict[str, Any]:
    contract = _safe_mapping(current_answer_contract)
    components = []
    for ref in _safe_list(contract.get("accepted_answer_component_refs")):
        if not isinstance(ref, Mapping):
            continue
        components.append(
            {
                "component_id": ref.get("component_id"),
                "component_revision": ref.get("component_revision"),
                "component_digest": ref.get("component_digest"),
                "component_purpose": ref.get("component_purpose"),
                "requirement_posture": ref.get("requirement_posture"),
                "materiality": ref.get("materiality"),
                "allowed_support_kinds": _token_list(
                    ref.get("allowed_support_kinds")
                ),
                "max_inference_depth": int(
                    ref.get("max_inference_depth") or 0
                ),
                "dependency_component_ids": _token_list(
                    ref.get("dependency_component_ids")
                ),
                "lifecycle_status": ref.get("lifecycle_status", "pending"),
                "source_obligation_candidate_ids": _token_list(
                    ref.get("source_obligation_candidate_ids")
                ),
                "mandatory_caveats": _text_list(ref.get("mandatory_caveats")),
                "prohibited_upgrades": _text_list(ref.get("prohibited_upgrades")),
            }
        )
    slots = []
    for ref in _safe_list(contract.get("accepted_semantic_slot_refs")):
        if not isinstance(ref, Mapping):
            continue
        slots.append(
            {
                "slot_id": ref.get("slot_id"),
                "slot_kind": ref.get("slot_kind"),
                "status": ref.get("status"),
                "materiality": ref.get("materiality"),
                "unresolved_material": ref.get("unresolved_material"),
            }
        )
    return {
        "owner": CURRENT_ANSWER_CONTRACT_OWNER,
        "schema_version": contract.get("schema_version"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": contract.get("run_id"),
        "request_id": contract.get("request_id"),
        "authorized_action_id": contract.get("authorized_action_id"),
        "accepted_contract_version": contract.get("accepted_contract_version"),
        "accepted_contract_digest": contract.get("accepted_contract_digest"),
        "previous_contract_version": contract.get("previous_contract_version"),
        "previous_contract_digest": contract.get("previous_contract_digest"),
        "initial_contract_version": contract.get("initial_contract_version"),
        "initial_contract_digest": contract.get("initial_contract_digest"),
        "accepted_answer_component_refs": components,
        "accepted_answer_component_count": len(components),
        "accepted_semantic_slot_refs": slots,
        "accepted_semantic_slot_count": len(slots),
        "mandatory_caveats": _text_list(contract.get("mandatory_caveats")),
        "prohibited_upgrades": _text_list(contract.get("prohibited_upgrades")),
        "requirement_lifecycle": _safe_mapping(
            contract.get("requirement_lifecycle")
        ),
        "applied_amendment_refs": _safe_list(contract.get("applied_amendment_refs")),
        "lineage": _safe_mapping(contract.get("lineage")),
        "closed_surface_flags": _safe_mapping(contract.get("closed_surface_flags")),
        "initial_answer_contract_mutated": False,
        "admission_record_mutated": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "provider_search_behavior_changed": False,
        "fetch_read_retrieval_behavior_changed": False,
        "planner_runtime_activated": False,
        "scout_runtime_activated": False,
        "search_executor_runtime_activated": False,
        "author_behavior_changed": False,
        "citation_behavior_changed": False,
        "prompt_behavior_changed": False,
        "partial_answer_readiness_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }


def build_contract_amendment_application_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    admitted_amendment: Mapping[str, Any] | None,
    parent_contract: Mapping[str, Any] | None,
    initial_contract: Mapping[str, Any] | None,
    component_coverage_history: Sequence[Mapping[str, Any]] = (),
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    application_history: Sequence[Mapping[str, Any]] = (),
    run_id: str,
    request_id: str,
) -> dict[str, Any]:
    """Apply one canonical admitted amendment into current_answer_contract."""

    clean_action_id, inputs, admission, parent = _validate_application_bindings(
        action_id=action_id,
        action_inputs=action_inputs or {},
        admitted_amendment=admitted_amendment or {},
        parent_contract=parent_contract or {},
        initial_contract=initial_contract or {},
        run_id=run_id,
        request_id=request_id,
    )
    initial = _safe_mapping(initial_contract)
    operations = [
        _safe_mapping(operation)
        for operation in _safe_list(admission.get("operations"))
        if isinstance(operation, Mapping)
    ]
    if not operations:
        raise ContractAmendmentApplicationError(
            "admitted amendment has no operations to apply"
        )
    _reject_duplicate_application(
        action_id=clean_action_id,
        admitted_amendment=admission,
        parent_contract=parent,
        application_history=application_history,
    )
    _require_admission_parent_matches(
        admitted_amendment=admission,
        parent_contract=parent,
    )
    _reject_unapplicable_admission(
        admitted_amendment=admission,
        operations=operations,
        action_inputs=inputs,
    )

    components, slots, mutations = _apply_operations(
        parent_contract=parent,
        admitted_amendment=admission,
        action_inputs=inputs,
        component_coverage_history=component_coverage_history,
    )
    try:
        component_contracts = [
            AnswerComponentContract(
                component_id=str(component.get("component_id") or ""),
                component_revision=str(
                    component.get("component_revision") or "1"
                ),
                component_digest=component.get("component_digest"),
                component_purpose=component.get("component_purpose")
                or "user_facing_answer_target",
                user_facing_label=str(
                    component.get("user_facing_label") or ""
                ),
                user_facing_question=str(
                    component.get("user_facing_question") or ""
                ),
                requirement_posture=component.get("requirement_posture")
                or "required",
                acceptance_criteria=tuple(
                    component.get("acceptance_criteria") or ()
                ),
                semantic_slot_ids=tuple(
                    component.get("semantic_slot_ids") or ()
                ),
                source_obligation_candidate_ids=tuple(
                    component.get("source_obligation_candidate_ids") or ()
                ),
                source_obligation_candidate_refs=tuple(
                    component.get("source_obligation_candidate_refs") or ()
                ),
                allowed_support_kinds=tuple(
                    component.get("allowed_support_kinds") or ("direct",)
                ),
                max_inference_depth=int(
                    component.get("max_inference_depth") or 0
                ),
                normalization_policy=component.get("normalization_policy"),
                calculation_policy=component.get("calculation_policy"),
                dependency_component_ids=tuple(
                    component.get("dependency_component_ids") or ()
                ),
                partial_answer_policy=component.get("partial_answer_policy")
                or "qualify_visible_gap",
                mandatory_caveats=tuple(
                    component.get("mandatory_caveats") or ()
                ),
                prohibited_upgrades=tuple(
                    component.get("prohibited_upgrades") or ()
                ),
                materiality=component.get("materiality") or "material",
                metadata=_safe_mapping(component.get("metadata")),
            )
            for component in components
        ]
        matrix = validate_answer_component_contract_set(
            component_contracts,
            requested_mode=(
                parent.get("requested_mode")
                or _safe_mapping(parent.get("question_meaning_metadata")).get(
                    "requested_mode"
                )
                or action_inputs.get("requested_mode")
                or "balanced"
            ),
        )
        matrix.raise_for_errors()
    except (TypeError, ValueError) as exc:
        raise ContractAmendmentApplicationError(
            f"applied amendment violates the answer-component contract matrix: {exc}"
        ) from exc
    parent_version, parent_digest = _contract_version_digest(parent)
    initial_version, initial_digest = _contract_version_digest(initial)
    existing_applied = [
        _safe_mapping(item)
        for item in _safe_list(parent.get("applied_amendment_refs"))
        if isinstance(item, Mapping)
    ]
    application_index = len(existing_applied) + 1
    candidate_version = _clean_token(admission.get("candidate_new_contract_version"))
    current_version = candidate_version or (
        f"{parent_version}+amendment-{application_index}"
    )
    if current_version == parent_version:
        current_version = f"{parent_version}+amendment-{application_index}"

    lifecycle = _build_requirement_lifecycle(components)
    applied_ref = {
        "amendment_record_id": admission.get("amendment_record_id"),
        "amendment_record_digest": admission.get("amendment_record_digest"),
        "admission_digest": admission.get("admission_digest"),
        "authorized_action_id": clean_action_id,
        "parent_contract_version": parent_version,
        "parent_contract_digest": parent_digest,
        "applied_operation_kinds": [
            item.get("operation_kind") for item in mutations["applied_operations"]
        ],
        "search_planner_revision_lineage": _safe_mapping(
            admission.get("search_planner_revision_lineage")
        ),
    }
    lineage = {
        "created_by": CURRENT_ANSWER_CONTRACT_OWNER,
        "created_from": [
            "initial_answer_contract",
            "current_answer_contract_parent",
            "admitted_contract_amendment",
        ],
        "reducer_action_id": clean_action_id,
        "previous_contract_version": parent_version,
        "previous_contract_digest": parent_digest,
        "initial_contract_version": initial_version,
        "initial_contract_digest": initial_digest,
        "admission_digest": admission.get("admission_digest"),
        "amendment_record_digest": admission.get("amendment_record_digest"),
    }
    current_core: dict[str, Any] = {
        "schema_version": CURRENT_ANSWER_CONTRACT_SCHEMA_VERSION,
        "owner": CURRENT_ANSWER_CONTRACT_OWNER,
        "trace_key": "current_answer_contract",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": run_id,
        "request_id": request_id,
        "authorized_action_id": clean_action_id,
        "accepted_contract_version": current_version,
        "previous_contract_version": parent_version,
        "previous_contract_digest": parent_digest,
        "initial_contract_version": initial_version,
        "initial_contract_digest": initial_digest,
        "parent_question_meaning_record_id": parent.get(
            "parent_question_meaning_record_id"
        )
        or initial.get("parent_question_meaning_record_id"),
        "parent_question_meaning_record_digest": parent.get(
            "parent_question_meaning_record_digest"
        )
        or initial.get("parent_question_meaning_record_digest"),
        "parent_proposal_schema_version": parent.get(
            "parent_proposal_schema_version"
        )
        or initial.get("parent_proposal_schema_version"),
        "accepted_answer_component_refs": components,
        "accepted_answer_component_count": len(components),
        "accepted_semantic_slot_refs": slots,
        "accepted_semantic_slot_count": len(slots),
        "material_ambiguity_count": parent.get("material_ambiguity_count", 0),
        "material_ambiguity_preserved": True,
        "materiality_policy": _safe_mapping(parent.get("materiality_policy"))
        or _safe_mapping(initial.get("materiality_policy")),
        "mandatory_caveats": mutations["mandatory_caveats"],
        "prohibited_upgrades": mutations["prohibited_upgrades"],
        "normalization_obligations": mutations["normalization_obligations"],
        "assumptions": mutations["assumptions"],
        "review_obligations": mutations["review_obligations"],
        "irreducible_unknowns": mutations["irreducible_unknowns"],
        "requirement_lifecycle_statuses": list(REQUIREMENT_LIFECYCLE_STATUSES),
        "requirement_lifecycle_status_definitions": dict(
            REQUIREMENT_LIFECYCLE_STATUS_DEFINITIONS
        ),
        "requirement_lifecycle": lifecycle,
        "applied_amendment_refs": [*existing_applied, applied_ref],
        "closed_surface_flags": dict(_FALSE_CLOSED_SURFACE_FLAGS),
        "lineage": lineage,
        "question_interpreted": False,
        "components_invented": False,
        "assumptions_added": bool(mutations["assumptions"]),
        "requirements_weakened": False,
        "material_ambiguity_resolved": False,
        "coverage_created": False,
        "amendment_created": False,
        "semantic_observation_admitted": False,
        "contract_mutation_applied": True,
        "current_answer_contract_created": True,
        "admission_record_mutated": False,
        "initial_answer_contract_mutated": False,
        "coverage_invalidation_applied": False,
        "coverage_marked_stale": False,
        "sufficiency_decided": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "fetch_read_retrieval_behavior_changed": False,
        "planner_runtime_activated": False,
        "scout_runtime_activated": False,
        "search_executor_runtime_activated": False,
        "author_behavior_changed": False,
        "prompt_behavior_changed": False,
        "partial_answer_readiness_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }
    current_digest = _digest_json(_current_contract_digest_payload(current_core))
    current_contract = {
        **current_core,
        "accepted_contract_digest": current_digest,
    }

    status_counts: dict[str, int] = {status: 0 for status in REQUIREMENT_LIFECYCLE_STATUSES}
    for item in lifecycle["component_statuses"]:
        status = _normalized_token(item.get("status")) or "pending"
        if status in status_counts:
            status_counts[status] += 1
    application_lineage = {
        "created_by": CONTRACT_AMENDMENT_APPLICATION_OWNER,
        "created_from": [
            "canonical_contract_amendment_admission",
            "current_answer_contract_parent",
        ],
        "reducer_action_id": clean_action_id,
        "previous_contract_version": parent_version,
        "previous_contract_digest": parent_digest,
        "initial_contract_version": initial_version,
        "initial_contract_digest": initial_digest,
        "admission_digest": admission.get("admission_digest"),
        "amendment_record_digest": admission.get("amendment_record_digest"),
        "current_contract_version": current_version,
        "current_contract_digest": current_digest,
    }
    state_core: dict[str, Any] = {
        "schema_version": CONTRACT_AMENDMENT_APPLICATION_SCHEMA_VERSION,
        "owner": CONTRACT_AMENDMENT_APPLICATION_OWNER,
        "trace_key": CONTRACT_AMENDMENT_APPLICATION_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": run_id,
        "request_id": request_id,
        "authorized_action_id": clean_action_id,
        "amendment_record_id": admission.get("amendment_record_id"),
        "amendment_record_digest": admission.get("amendment_record_digest"),
        "admission_digest": admission.get("admission_digest"),
        "parent_contract_version": parent_version,
        "parent_contract_digest": parent_digest,
        "initial_contract_version": initial_version,
        "initial_contract_digest": initial_digest,
        "current_contract_version": current_version,
        "current_contract_digest": current_digest,
        "candidate_new_contract_version": admission.get(
            "candidate_new_contract_version"
        ),
        "candidate_new_contract_digest": admission.get("candidate_new_contract_digest"),
        "applied_operation_kinds": [
            item.get("operation_kind") for item in mutations["applied_operations"]
        ],
        "applied_operations": mutations["applied_operations"],
        "requirement_lifecycle_summary": status_counts,
        "lineage": application_lineage,
        "current_answer_contract": current_contract,
        "evidence_ledger_projection_digest": (
            _digest_json(_safe_mapping(evidence_ledger_projection))
            if isinstance(evidence_ledger_projection, Mapping)
            else None
        ),
        "contract_mutation_applied": True,
        "current_answer_contract_created": True,
        "admission_record_mutated": False,
        "initial_answer_contract_mutated": False,
        "coverage_invalidation_applied": False,
        "coverage_marked_stale": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "fetch_read_retrieval_behavior_changed": False,
        "planner_runtime_activated": False,
        "scout_runtime_activated": False,
        "search_executor_runtime_activated": False,
        "author_behavior_changed": False,
        "prompt_behavior_changed": False,
        "partial_answer_readiness_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }
    application_digest = _digest_json(_application_digest_payload(state_core))
    current_contract["lineage"] = {
        **_safe_mapping(current_contract.get("lineage")),
        "application_digest": application_digest,
        "current_contract_digest": current_digest,
    }
    state = {
        **state_core,
        "application_digest": application_digest,
        "current_answer_contract": current_contract,
    }
    existing_application_digests = {
        _clean_token(item.get("application_digest"), limit=128)
        for item in application_history
        if isinstance(item, Mapping)
    }
    if application_digest in existing_application_digests:
        raise ContractAmendmentApplicationError(
            "duplicate contract amendment application digest"
        )
    return state


def build_contract_amendment_application_projection(
    *,
    application_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project contract amendment application state without raw/private data."""

    state = _safe_mapping(application_state)
    current_contract = _safe_mapping(state.get("current_answer_contract"))
    return {
        "owner": CONTRACT_AMENDMENT_APPLICATION_OWNER,
        "schema_version": state.get("schema_version"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "amendment_record_id": state.get("amendment_record_id"),
        "amendment_record_digest": state.get("amendment_record_digest"),
        "admission_digest": state.get("admission_digest"),
        "application_digest": state.get("application_digest"),
        "parent_contract_version": state.get("parent_contract_version"),
        "parent_contract_digest": state.get("parent_contract_digest"),
        "initial_contract_version": state.get("initial_contract_version"),
        "initial_contract_digest": state.get("initial_contract_digest"),
        "current_contract_version": state.get("current_contract_version"),
        "current_contract_digest": state.get("current_contract_digest"),
        "candidate_new_contract_version": state.get("candidate_new_contract_version"),
        "candidate_new_contract_digest": state.get("candidate_new_contract_digest"),
        "applied_operation_kinds": _token_list(state.get("applied_operation_kinds")),
        "applied_operations": _safe_list(state.get("applied_operations")),
        "requirement_lifecycle_summary": _safe_mapping(
            state.get("requirement_lifecycle_summary")
        ),
        "lineage": _safe_mapping(state.get("lineage")),
        "current_answer_contract_projection": build_current_answer_contract_projection(
            current_answer_contract=current_contract
        ),
        "contract_mutation_applied": True,
        "current_answer_contract_created": True,
        "admission_record_mutated": False,
        "initial_answer_contract_mutated": False,
        "coverage_invalidation_applied": False,
        "coverage_marked_stale": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "fetch_read_retrieval_behavior_changed": False,
        "planner_runtime_activated": False,
        "scout_runtime_activated": False,
        "search_executor_runtime_activated": False,
        "author_behavior_changed": False,
        "prompt_behavior_changed": False,
        "partial_answer_readiness_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }


__all__ = [
    "CONTRACT_AMENDMENT_APPLICATION_OWNER",
    "CONTRACT_AMENDMENT_APPLICATION_REASON",
    "CONTRACT_AMENDMENT_APPLICATION_SCHEMA_VERSION",
    "CONTRACT_AMENDMENT_APPLICATION_STAGE",
    "CONTRACT_AMENDMENT_APPLICATION_TRACE_KEY",
    "CURRENT_ANSWER_CONTRACT_OWNER",
    "CURRENT_ANSWER_CONTRACT_SCHEMA_VERSION",
    "REQUIREMENT_LIFECYCLE_STATUS_DEFINITIONS",
    "REQUIREMENT_LIFECYCLE_STATUSES",
    "ContractAmendmentApplicationError",
    "build_contract_amendment_application_projection",
    "build_contract_amendment_application_state",
    "build_current_answer_contract_projection",
]
