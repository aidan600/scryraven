"""Canonical Sufficiency semantic-consumption runtime for AG-SEM-09.

This module is the fifth canonical semantic authority bridge. It provides the
bounded, pure helpers a RunKernel/RunAuthority-authorized reducer uses to bind
the accepted initial answer contract, admitted SemanticObservation history,
reduced component coverage history, and optional admitted ContractAmendmentRecord
candidates into canonical Sufficiency semantic-consumption state.

It records semantic consumption only. It does not mutate the accepted initial
answer contract, apply amendment candidates, mark coverage stale, invalidate
coverage, decide SufficiencyJudgment, decide SearchJudgment, activate
QueryPlan/SearchWorkPlan, authorize follow-up, create Author input, create a
FinalAnswerPacket, or perform any provider, search, retrieval, fetch/read,
citation, or live validation behavior.

The helpers here are imported by ``core.run_kernel``; to keep the import graph
acyclic this module must not import ``core.run_kernel``.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_coverage_reduction_runtime import evidence_ledger_projection_digest
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION

SUFFICIENCY_SEMANTIC_CONSUMPTION_SCHEMA_VERSION = (
    "sufficiency_semantic_consumption_ag_sem_09_v1"
)
SUFFICIENCY_SEMANTIC_CONSUMPTION_STAGE = "sufficiency_semantic_consumption"
SUFFICIENCY_SEMANTIC_CONSUMPTION_REASON = (
    "sufficiency_semantic_consumption_from_canonical_semantic_stack"
)
SUFFICIENCY_SEMANTIC_CONSUMPTION_TRACE_KEY = "sufficiency_semantic_consumption"
SUFFICIENCY_SEMANTIC_CONSUMPTION_OWNER = "RunKernel.SufficiencySemanticConsumption"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db_row",
        "full_trace",
        "logs",
        "model_response",
        "page_corpus",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
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
        "accepted_amendment",
        "author_input",
        "canonical_coverage",
        "component_coverage_record",
        "contract_amendment_record",
        "coverage_decision_applied",
        "final_answer",
        "final_answer_packet",
        "followup_activation",
        "query_plan_activation",
        "search_judgment_decision",
        "search_work_plan_activation",
        "sufficiency_decision_applied",
        "sufficiency_judgment",
    }
)

_CONSUMPTION_UNSAFE_IF_TRUE = (
    "accepted_authority",
    "amendment_applied",
    "author_input_created",
    "canonical_state",
    "citation_behavior_changed",
    "component_satisfied",
    "contract_mutation_applied",
    "coverage_invalidation_applied",
    "coverage_marked_stale",
    "final_answer_authority",
    "final_answer_decision",
    "final_answer_packet",
    "final_answer_packet_created",
    "followup_authorized",
    "initial_answer_contract_mutated",
    "provider_search_behavior_changed",
    "query_plan_activated",
    "runtime_behavior_changed",
    "search_judgment_decided",
    "search_work_plan_activated",
    "sufficiency_decided",
    "sufficiency_judgment",
)

_REQUIRED_INPUT_KEYS = (
    "semantic_consumption_id",
    "accepted_contract_digest",
    "accepted_contract_version",
)


class SufficiencySemanticConsumptionError(ValueError):
    """Raised when canonical semantic consumption cannot be recorded."""


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


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value for key, value in value.items() if not _is_sensitive_key(key)}


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    items: list[str] = []
    for item in value:
        token = _clean_token(item)
        if token:
            items.append(token)
    return items


def _require_match(condition: bool, message: str) -> None:
    if not condition:
        raise SufficiencySemanticConsumptionError(message)


def _digest_json(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _scan_payload_for_taint(payload: Mapping[str, Any], *, path: str = "") -> None:
    for key, value in payload.items():
        key_text = str(key)
        current_path = f"{path}.{key_text}" if path else key_text
        if _is_sensitive_key(key_text):
            raise SufficiencySemanticConsumptionError(
                f"consumption payload contains sensitive field {current_path}"
            )
        if key_text in _FORBIDDEN_AUTHORITY_FIELDS:
            raise SufficiencySemanticConsumptionError(
                f"consumption payload contains forbidden authority field {current_path}"
            )
        if key_text in _CONSUMPTION_UNSAFE_IF_TRUE and value is True:
            raise SufficiencySemanticConsumptionError(
                f"consumption payload has unsafe true flag {current_path}"
            )
        if isinstance(value, Mapping):
            _scan_payload_for_taint(value, path=current_path)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for index, item in enumerate(value):
                if isinstance(item, Mapping):
                    _scan_payload_for_taint(item, path=f"{current_path}[{index}]")


def _expected_accepted_contract_ref(version: str) -> str:
    return f"contract:{version}:accepted"


def _component_index(accepted_contract: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in accepted_contract.get("accepted_answer_component_refs") or ():
        mapping = _safe_mapping(item)
        component_id = _clean_token(mapping.get("component_id"))
        if component_id:
            index[component_id] = mapping
    return index


def _admission_index(
    admission_history: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in admission_history:
        mapping = _safe_mapping(item)
        observation_id = _clean_token(mapping.get("observation_id"))
        if observation_id:
            index[observation_id] = mapping
    return index


def _coverage_history_index(
    coverage_history: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in coverage_history:
        mapping = _safe_mapping(item)
        coverage_record_id = _clean_token(mapping.get("coverage_record_id"))
        if coverage_record_id:
            index[coverage_record_id] = mapping
    return index


def _amendment_history_index(
    amendment_history: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in amendment_history:
        mapping = _safe_mapping(item)
        amendment_record_id = _clean_token(mapping.get("amendment_record_id"))
        if amendment_record_id:
            index[amendment_record_id] = mapping
    return index


def _build_evidence_ledger_binding(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    projection = _safe_mapping(evidence_ledger_projection)
    digest = evidence_ledger_projection_digest(projection)
    return {
        "ledger_snapshot_id": f"evidence-ledger:{digest[:32]}",
        "ledger_schema_version": EVIDENCE_LEDGER_SCHEMA_VERSION,
        "ledger_digest": digest,
    }


def _consumption_digest_payload(state_core: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": state_core.get("schema_version"),
        "semantic_consumption_id": state_core.get("semantic_consumption_id"),
        "accepted_contract_digest": state_core.get("accepted_contract_digest"),
        "accepted_contract_version": state_core.get("accepted_contract_version"),
        "consumed_observation_refs": state_core.get("consumed_observation_refs", []),
        "consumed_coverage_refs": state_core.get("consumed_coverage_refs", []),
        "consumed_amendment_admission_refs": state_core.get(
            "consumed_amendment_admission_refs",
            [],
        ),
        "evidence_ledger_binding": state_core.get("evidence_ledger_binding", {}),
        "component_coverage_summary": state_core.get("component_coverage_summary", {}),
    }


def build_sufficiency_semantic_consumption_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any],
    consumption_payload: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    admission_history: Sequence[Mapping[str, Any]],
    coverage_history: Sequence[Mapping[str, Any]],
    amendment_admission_history: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any],
    existing_semantic_consumption_ids: Sequence[str],
    existing_semantic_consumption_digests: Sequence[str],
    run_id: str,
    request_id: str,
) -> dict[str, Any]:
    """Bind canonical semantic stack refs for later Sufficiency input assembly."""

    clean_action_id = _clean_token(action_id, limit=200)
    clean_run_id = _clean_token(run_id, limit=200)
    clean_request_id = _clean_token(request_id, limit=200)
    if not clean_action_id or not clean_run_id or not clean_request_id:
        raise SufficiencySemanticConsumptionError(
            "semantic consumption requires action_id, run_id, and request_id"
        )

    payload = _safe_mapping(consumption_payload)
    _scan_payload_for_taint(payload)

    contract = _safe_mapping(accepted_contract)
    if not contract:
        raise SufficiencySemanticConsumptionError(
            "semantic consumption requires an accepted initial answer contract"
        )
    accepted_contract_digest = _clean_token(contract.get("accepted_contract_digest"), limit=128)
    accepted_contract_version = _clean_token(contract.get("accepted_contract_version"))
    if not accepted_contract_digest or not accepted_contract_version:
        raise SufficiencySemanticConsumptionError(
            "accepted initial answer contract is missing version or digest"
        )

    inputs = dict(action_inputs or {})
    missing_inputs = [
        key for key in _REQUIRED_INPUT_KEYS if not _clean_token(inputs.get(key), limit=200)
    ]
    if missing_inputs:
        raise SufficiencySemanticConsumptionError(
            "authorized action must bind: " + ", ".join(missing_inputs)
        )

    semantic_consumption_id = _clean_token(inputs.get("semantic_consumption_id"), limit=200)
    _require_match(
        semantic_consumption_id is not None,
        "semantic consumption requires semantic_consumption_id binding",
    )
    bound_request_id = _clean_token(inputs.get("request_id"))
    if bound_request_id and bound_request_id != clean_request_id:
        raise SufficiencySemanticConsumptionError(
            "authorized action request_id binding does not match the request"
        )
    _require_match(
        _clean_token(inputs.get("accepted_contract_digest"), limit=128)
        == accepted_contract_digest,
        "action accepted_contract_digest binding does not match the accepted contract digest",
    )
    _require_match(
        _clean_token(inputs.get("accepted_contract_version")) == accepted_contract_version,
        "action accepted_contract_version binding does not match the accepted contract version",
    )

    if not admission_history:
        raise SufficiencySemanticConsumptionError(
            "semantic consumption requires at least one admitted SemanticObservation"
        )
    if not coverage_history:
        raise SufficiencySemanticConsumptionError(
            "semantic consumption requires at least one reduced ComponentCoverageRecord"
        )

    if semantic_consumption_id in {
        _clean_token(item, limit=200) for item in existing_semantic_consumption_ids if item
    }:
        raise SufficiencySemanticConsumptionError(
            f"semantic consumption id {semantic_consumption_id} is already recorded"
        )

    admission_by_id = _admission_index(admission_history)
    component_index = _component_index(contract)
    consumed_observation_refs: list[dict[str, Any]] = []
    seen_observation_ids: set[str] = set()

    consumed_coverage_refs: list[dict[str, Any]] = []
    satisfied_count = 0
    unsatisfied_count = 0
    stale_present = False

    for coverage_item in coverage_history:
        coverage = _safe_mapping(coverage_item)
        coverage_record_id = _clean_token(coverage.get("coverage_record_id"), limit=200)
        coverage_record_digest = _clean_token(
            coverage.get("coverage_record_digest"),
            limit=128,
        )
        answer_component_id = _clean_token(coverage.get("answer_component_id"), limit=200)
        component_revision = _clean_token(coverage.get("component_revision"))
        component_digest = _clean_token(coverage.get("component_digest"), limit=128)
        if not all(
            (
                coverage_record_id,
                coverage_record_digest,
                answer_component_id,
                component_revision,
                component_digest,
            )
        ):
            raise SufficiencySemanticConsumptionError(
                "coverage history entry is missing required consumption bindings"
            )
        _require_match(
            _clean_token(coverage.get("accepted_contract_digest"), limit=128)
            == accepted_contract_digest,
            f"coverage record {coverage_record_id} accepted_contract_digest mismatch",
        )
        _require_match(
            _clean_token(coverage.get("accepted_contract_version"))
            == accepted_contract_version,
            f"coverage record {coverage_record_id} accepted_contract_version mismatch",
        )
        accepted_component = component_index.get(answer_component_id or "")
        if accepted_component is None:
            raise SufficiencySemanticConsumptionError(
                f"coverage record {coverage_record_id} answer_component_id is not accepted"
            )
        _require_match(
            _clean_token(accepted_component.get("component_revision")) == component_revision,
            f"coverage record {coverage_record_id} component_revision mismatch",
        )
        _require_match(
            _clean_token(accepted_component.get("component_digest"), limit=128) == component_digest,
            f"coverage record {coverage_record_id} component_digest mismatch",
        )

        observation_refs = coverage.get("accepted_observation_refs") or ()
        if not observation_refs:
            raise SufficiencySemanticConsumptionError(
                f"coverage record {coverage_record_id} has no accepted observation refs"
            )
        for obs_ref in observation_refs:
            obs_mapping = _safe_mapping(obs_ref)
            observation_id = _clean_token(obs_mapping.get("observation_id"), limit=200)
            observation_digest = _clean_token(
                obs_mapping.get("observation_digest"),
                limit=128,
            )
            if not observation_id or not observation_digest:
                raise SufficiencySemanticConsumptionError(
                    f"coverage record {coverage_record_id} has malformed observation ref"
                )
            admission = admission_by_id.get(observation_id)
            if admission is None:
                raise SufficiencySemanticConsumptionError(
                    f"semantic observation ref {observation_id} is not admitted"
                )
            admitted_digest = _clean_token(admission.get("observation_digest"), limit=128)
            if observation_digest != admitted_digest:
                raise SufficiencySemanticConsumptionError(
                    f"semantic observation ref {observation_id} has stale observation digest"
                )
            if observation_id not in seen_observation_ids:
                seen_observation_ids.add(observation_id)
                consumed_observation_refs.append(
                    {
                        "observation_id": observation_id,
                        "observation_digest": observation_digest,
                        "answer_component_id": answer_component_id,
                        "component_revision": component_revision,
                        "component_contract_digest": component_digest,
                    }
                )

        coverage_state = _clean_token(coverage.get("coverage_state"))
        if coverage_state == "satisfied":
            satisfied_count += 1
        else:
            unsatisfied_count += 1
        stale_flag = bool(coverage.get("stale"))
        stale_present = stale_present or stale_flag
        consumed_coverage_refs.append(
            {
                "coverage_record_id": coverage_record_id,
                "coverage_record_digest": coverage_record_digest,
                "answer_component_id": answer_component_id,
                "component_revision": component_revision,
                "component_digest": component_digest,
                "coverage_state": coverage_state,
                "semantic_support_status": _clean_token(
                    coverage.get("semantic_support_status")
                ),
                "stale": stale_flag,
                "coverage_marked_stale": False,
                "coverage_invalidation_applied": False,
            }
        )

    consumed_amendment_admission_refs: list[dict[str, Any]] = []
    for amendment_item in amendment_admission_history:
        amendment = _safe_mapping(amendment_item)
        amendment_record_id = _clean_token(amendment.get("amendment_record_id"), limit=200)
        amendment_record_digest = _clean_token(
            amendment.get("amendment_record_digest"),
            limit=128,
        )
        if not amendment_record_id or not amendment_record_digest:
            raise SufficiencySemanticConsumptionError(
                "amendment admission history entry is missing required bindings"
            )
        _require_match(
            _clean_token(amendment.get("accepted_contract_digest"), limit=128)
            == accepted_contract_digest,
            f"amendment admission {amendment_record_id} accepted_contract_digest mismatch",
        )
        consumed_amendment_admission_refs.append(
            {
                "amendment_record_id": amendment_record_id,
                "amendment_record_digest": amendment_record_digest,
                "amendment_applied": False,
                "represented_only": True,
                "disposition": _clean_token(amendment.get("disposition")),
            }
        )

    evidence_ledger_binding = _build_evidence_ledger_binding(evidence_ledger_projection)
    component_coverage_summary = {
        "total": len(consumed_coverage_refs),
        "satisfied": satisfied_count,
        "unsatisfied": unsatisfied_count,
        "stale_present": stale_present,
    }

    lineage = {
        "created_by": SUFFICIENCY_SEMANTIC_CONSUMPTION_OWNER,
        "created_from": [
            "accepted_initial_answer_contract",
            "semantic_observation_admission_history",
            "component_coverage_history",
        ],
        "reducer_action_id": clean_action_id,
        "accepted_contract_digest": accepted_contract_digest,
    }
    if consumed_amendment_admission_refs:
        lineage["created_from"].append("contract_amendment_admission_history")

    state_core: dict[str, Any] = {
        "schema_version": SUFFICIENCY_SEMANTIC_CONSUMPTION_SCHEMA_VERSION,
        "owner": SUFFICIENCY_SEMANTIC_CONSUMPTION_OWNER,
        "trace_key": SUFFICIENCY_SEMANTIC_CONSUMPTION_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "semantic_consumption_id": semantic_consumption_id,
        "accepted_contract_version": accepted_contract_version,
        "accepted_contract_digest": accepted_contract_digest,
        "accepted_contract_ref": _expected_accepted_contract_ref(accepted_contract_version),
        "parent_question_meaning_record_id": _clean_token(
            contract.get("parent_question_meaning_record_id"),
            limit=200,
        ),
        "parent_question_meaning_record_digest": _clean_token(
            contract.get("parent_question_meaning_record_digest"),
            limit=128,
        ),
        "consumed_observation_refs": consumed_observation_refs,
        "consumed_coverage_refs": consumed_coverage_refs,
        "consumed_amendment_admission_refs": consumed_amendment_admission_refs,
        "evidence_ledger_binding": evidence_ledger_binding,
        "component_coverage_summary": component_coverage_summary,
        "consumption_posture": "semantic_stack_bound",
        "recommended_next_step": "sufficiency_judgment_input_assembly",
        "lineage": lineage,
        "initial_answer_contract_mutated": False,
        "amendment_applied": False,
        "coverage_marked_stale": False,
        "coverage_invalidation_applied": False,
        "contract_mutation_applied": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }
    semantic_consumption_digest = _digest_json(_consumption_digest_payload(state_core))
    if semantic_consumption_digest in {
        _clean_token(item, limit=128) for item in existing_semantic_consumption_digests if item
    }:
        raise SufficiencySemanticConsumptionError(
            "semantic consumption digest is already recorded"
        )
    return {**state_core, "semantic_consumption_digest": semantic_consumption_digest}


def build_sufficiency_semantic_consumption_projection(
    *,
    consumption_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project canonical semantic consumption state with no raw or private data."""

    state = _safe_mapping(consumption_state)
    return {
        "owner": SUFFICIENCY_SEMANTIC_CONSUMPTION_OWNER,
        "schema_version": state.get("schema_version"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "semantic_consumption_id": state.get("semantic_consumption_id"),
        "semantic_consumption_digest": state.get("semantic_consumption_digest"),
        "accepted_contract_version": state.get("accepted_contract_version"),
        "accepted_contract_digest": state.get("accepted_contract_digest"),
        "accepted_contract_ref": state.get("accepted_contract_ref"),
        "parent_question_meaning_record_id": state.get("parent_question_meaning_record_id"),
        "parent_question_meaning_record_digest": state.get(
            "parent_question_meaning_record_digest"
        ),
        "consumed_observation_refs": list(state.get("consumed_observation_refs", [])),
        "consumed_coverage_refs": list(state.get("consumed_coverage_refs", [])),
        "consumed_amendment_admission_refs": list(
            state.get("consumed_amendment_admission_refs", [])
        ),
        "evidence_ledger_binding": dict(state.get("evidence_ledger_binding") or {}),
        "component_coverage_summary": dict(state.get("component_coverage_summary") or {}),
        "consumption_posture": state.get("consumption_posture"),
        "recommended_next_step": state.get("recommended_next_step"),
        "lineage": dict(state.get("lineage") or {}),
        "initial_answer_contract_mutated": False,
        "amendment_applied": False,
        "coverage_marked_stale": False,
        "coverage_invalidation_applied": False,
        "contract_mutation_applied": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }


__all__ = [
    "SUFFICIENCY_SEMANTIC_CONSUMPTION_OWNER",
    "SUFFICIENCY_SEMANTIC_CONSUMPTION_REASON",
    "SUFFICIENCY_SEMANTIC_CONSUMPTION_SCHEMA_VERSION",
    "SUFFICIENCY_SEMANTIC_CONSUMPTION_STAGE",
    "SUFFICIENCY_SEMANTIC_CONSUMPTION_TRACE_KEY",
    "SufficiencySemanticConsumptionError",
    "build_sufficiency_semantic_consumption_projection",
    "build_sufficiency_semantic_consumption_state",
]
