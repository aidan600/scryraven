"""Pure staging runtime for atomic semantic producer bundle commits."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from core.component_coverage_reduction_runtime import (
    ComponentCoverageReductionError,
    build_component_coverage_reduction_projection,
    build_component_coverage_reduction_state,
)
from core.initial_answer_contract_acceptance_runtime import (
    InitialAnswerContractAcceptanceError,
    build_initial_answer_contract_acceptance_projection,
    build_initial_answer_contract_acceptance_state,
)
from core.semantic_observation_admission_runtime import (
    SemanticObservationAdmissionError,
    build_semantic_observation_admission_projection,
    build_semantic_observation_admission_state,
)


class SemanticProducerBundleCommitStagingError(ValueError):
    """Raised when semantic producer bundle staging fails before mutation."""


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    return text[:limit]


def _payload_mapping(value: Any) -> dict[str, Any]:
    return deepcopy(dict(value)) if isinstance(value, Mapping) else {}


def _semantic_component_ref(
    accepted_contract: Mapping[str, Any],
    answer_component_id: Any,
) -> dict[str, Any]:
    component_id = _clean_text(answer_component_id, limit=160)
    for ref in accepted_contract.get("accepted_answer_component_refs") or ():
        if not isinstance(ref, Mapping):
            continue
        if _clean_text(ref.get("component_id"), limit=160) == component_id:
            return dict(ref)
    raise SemanticProducerBundleCommitStagingError(
        f"semantic producer bundle references unknown component {component_id!r}"
    )


def normalize_semantic_producer_bundle_payload(
    *,
    question_meaning_record: Mapping[str, Any],
    component_bundles: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "question_meaning_record": _payload_mapping(question_meaning_record),
        "component_bundles": [
            _payload_mapping(bundle)
            for bundle in component_bundles
            if isinstance(bundle, Mapping)
        ],
    }


def stage_semantic_producer_bundle_commit(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any],
    payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Stage all semantic bundle reducers without mutating RunState."""

    qmr_payload = _payload_mapping(payload.get("question_meaning_record"))
    component_payloads = [
        _payload_mapping(bundle)
        for bundle in payload.get("component_bundles") or ()
        if isinstance(bundle, Mapping)
    ]
    if not qmr_payload or not component_payloads:
        raise SemanticProducerBundleCommitStagingError(
            "semantic producer bundle commit requires question meaning record "
            "and component bundles"
        )
    expected_count = int(action_inputs.get("component_count") or 0)
    if expected_count != len(component_payloads):
        raise SemanticProducerBundleCommitStagingError(
            "semantic producer bundle component count binding does not match payload"
        )

    try:
        acceptance_state = build_initial_answer_contract_acceptance_state(
            action_id=action_id,
            action_inputs=action_inputs,
            question_meaning_record=qmr_payload,
            run_id=run_id,
            request_id=request_id,
        )
        acceptance_projection = build_initial_answer_contract_acceptance_projection(
            acceptance_state=acceptance_state
        )
    except InitialAnswerContractAcceptanceError as exc:
        raise SemanticProducerBundleCommitStagingError(str(exc)) from exc

    admission_states: list[dict[str, Any]] = []
    admission_projections: list[dict[str, Any]] = []
    coverage_states: list[dict[str, Any]] = []
    coverage_projections: list[dict[str, Any]] = []
    existing_observation_ids: list[str] = []
    existing_observation_digests: list[str] = []
    existing_coverage_record_ids: list[str] = []
    existing_coverage_record_digests: list[str] = []

    for index, component_payload in enumerate(component_payloads, start=1):
        semantic_observation = _payload_mapping(
            component_payload.get("semantic_observation")
        )
        content_references = [
            _payload_mapping(ref)
            for ref in component_payload.get("sanitized_content_references") or ()
            if isinstance(ref, Mapping)
        ]
        coverage_record = _payload_mapping(
            component_payload.get("component_coverage_record")
        )
        if not semantic_observation or not content_references:
            raise SemanticProducerBundleCommitStagingError(
                f"semantic producer bundle component {index} requires "
                "SemanticObservation and sanitized content references"
            )
        if not coverage_record:
            raise SemanticProducerBundleCommitStagingError(
                f"semantic producer bundle component {index} requires "
                "ComponentCoverageRecord"
            )

        component_ref = _semantic_component_ref(
            acceptance_state,
            semantic_observation.get("answer_component_id")
            or component_payload.get("answer_component_id"),
        )
        admission_inputs = {
            "semantic_observation_id": semantic_observation.get("observation_id"),
            "semantic_observation_digest": semantic_observation.get(
                "observation_digest"
            ),
            "accepted_contract_digest": acceptance_state["accepted_contract_digest"],
            "accepted_contract_version": acceptance_state[
                "accepted_contract_version"
            ],
            "answer_component_id": component_ref["component_id"],
            "component_revision": component_ref["component_revision"],
            "component_digest": component_ref["component_digest"],
            "request_id": request_id,
        }
        try:
            admission_state = build_semantic_observation_admission_state(
                action_id=action_id,
                action_inputs=admission_inputs,
                observation_payload={
                    "semantic_observation": semantic_observation,
                    "sanitized_content_references": content_references,
                },
                accepted_contract=acceptance_state,
                evidence_ledger_projection=evidence_ledger_projection,
                existing_observation_ids=existing_observation_ids,
                existing_observation_digests=existing_observation_digests,
                run_id=run_id,
                request_id=request_id,
            )
            admission_projection = build_semantic_observation_admission_projection(
                admission_state=admission_state
            )
        except SemanticObservationAdmissionError as exc:
            raise SemanticProducerBundleCommitStagingError(str(exc)) from exc
        admission_states.append(admission_state)
        admission_projections.append(admission_projection)
        existing_observation_ids.append(
            str(admission_projection.get("observation_id") or "")
        )
        existing_observation_digests.append(
            str(admission_projection.get("observation_digest") or "")
        )

        coverage_inputs = {
            "coverage_record_id": coverage_record.get("record_id"),
            "coverage_record_digest": coverage_record.get("record_digest"),
            "accepted_contract_digest": acceptance_state["accepted_contract_digest"],
            "accepted_contract_version": acceptance_state[
                "accepted_contract_version"
            ],
            "answer_component_id": component_ref["component_id"],
            "component_revision": component_ref["component_revision"],
            "component_digest": component_ref["component_digest"],
            "request_id": request_id,
        }
        try:
            coverage_state = build_component_coverage_reduction_state(
                action_id=action_id,
                action_inputs=coverage_inputs,
                coverage_payload={"component_coverage_record": coverage_record},
                accepted_contract=acceptance_state,
                admission_history=admission_projections,
                evidence_ledger_projection=evidence_ledger_projection,
                existing_coverage_record_ids=existing_coverage_record_ids,
                existing_coverage_record_digests=existing_coverage_record_digests,
                run_id=run_id,
                request_id=request_id,
            )
            coverage_projection = build_component_coverage_reduction_projection(
                coverage_state=coverage_state
            )
        except ComponentCoverageReductionError as exc:
            raise SemanticProducerBundleCommitStagingError(str(exc)) from exc
        coverage_states.append(coverage_state)
        coverage_projections.append(coverage_projection)
        existing_coverage_record_ids.append(
            str(coverage_projection.get("coverage_record_id") or "")
        )
        existing_coverage_record_digests.append(
            str(coverage_projection.get("coverage_record_digest") or "")
        )

    return {
        "acceptance_state": acceptance_state,
        "acceptance_projection": acceptance_projection,
        "admission_states": admission_states,
        "admission_projections": admission_projections,
        "coverage_states": coverage_states,
        "coverage_projections": coverage_projections,
    }


__all__ = [
    "SemanticProducerBundleCommitStagingError",
    "normalize_semantic_producer_bundle_payload",
    "stage_semantic_producer_bundle_commit",
]
