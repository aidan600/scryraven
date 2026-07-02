"""RunKernel-owned D-prime accepted/current contract authority.

This narrow product authority surface consumes retained D-prime source/fetch/read
lineage plus component/source-obligation lineage, creates an in-memory
``RunKernel`` authority carrier, and establishes accepted/current answer-contract
state through a RunKernel-owned reducer. Retained refs and digests are lineage
checks only; the materializer consumes the resulting RunKernel state.

It does not bind ComponentCoverage, create citations, satisfy source
obligations, decide SufficiencyReadiness, create FinalAnswerPacket state,
invoke Author, create answer text, claim product correctness, or run live/model/
provider/search/fetch/read/retrieval calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.fetch_read_content_reference import (
    FetchReadContentReferenceError,
    validate_fetch_read_content_packet,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)

DPRIME_ORDINARY_CONTRACT_AUTHORITY_SCHEMA_VERSION = (
    "dprime_ordinary_contract_authority_runtime_v1"
)
DPRIME_ORDINARY_CONTRACT_AUTHORITY_SURFACE = (
    "core.dprime_ordinary_contract_authority_runtime"
)
DPRIME_ORDINARY_CONTRACT_AUTHORITY_OWNER = (
    "RunKernel.DPrimeAnswerContractAuthority"
)

_SUPPORTED_COMPONENT_ID = "component:adult-us-passport-book-renewal-fee"
_SUPPORTED_SOURCE_OBLIGATION_ID = "obligation:official-current-passport-fee-source"


class DPrimeOrdinaryContractAuthorityError(ValueError):
    """Raised when the ordinary D-prime contract authority surface is unavailable."""


@dataclass(frozen=True, slots=True)
class DPrimeOrdinaryContractAuthorityResult:
    run_kernel: RunKernel
    authority_ref: Mapping[str, Any]


def build_dprime_ordinary_contract_authority(
    *,
    fetch_read_content_packet: Mapping[str, Any],
    source_evidence_admission_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
) -> DPrimeOrdinaryContractAuthorityResult:
    """Create the in-memory RunKernel authority consumed by D-prime materialization."""

    try:
        fetch_packet = validate_fetch_read_content_packet(fetch_read_content_packet)
    except FetchReadContentReferenceError as exc:
        raise DPrimeOrdinaryContractAuthorityError(str(exc)) from exc
    admission = _safe_mapping(source_evidence_admission_ref)
    component = _safe_mapping(component_ref)
    source_obligation = _safe_mapping(source_obligation_ref)
    reference = _matching_reference(
        fetch_packet=fetch_packet,
        admission=admission,
    )
    contract_ref = _safe_mapping(reference.get("current_answer_contract_ref"))
    contract_version = _required_text(
        contract_ref.get("contract_version"),
        "retained D-prime contract lineage lacks contract_version",
    )
    contract_digest = _required_text(
        contract_ref.get("contract_digest")
        or reference.get("current_answer_contract_digest"),
        "retained D-prime contract lineage lacks contract_digest",
        limit=128,
    )
    _require_lineage(
        fetch_packet=fetch_packet,
        reference=reference,
        admission=admission,
        component=component,
        source_obligation=source_obligation,
        contract_digest=contract_digest,
    )
    run_kernel = RunKernel.start(
        run_id=str(fetch_packet["run_id"]),
        request_id=str(fetch_packet["request_id"]),
        request={
            "authority_surface": DPRIME_ORDINARY_CONTRACT_AUTHORITY_SURFACE,
            "retained_refs_are_lineage_only": True,
        },
    )
    source_ids = _text_tuple(source_obligation.get("source_obligation_candidate_ids"))
    contract_payload = _contract_authority_payload(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        contract_version=contract_version,
        contract_digest=contract_digest,
        component=component,
        source_ids=source_ids,
        fetch_packet=fetch_packet,
        reference=reference,
    )
    action = run_kernel.authorize_dprime_current_answer_contract_authority(
        expected_contract_version=contract_version,
        expected_contract_digest=contract_digest,
        answer_component_id=_SUPPORTED_COMPONENT_ID,
        source_obligation_candidate_ids=source_ids,
        fetch_read_content_packet_id=str(fetch_packet["packet_id"]),
        fetch_read_content_packet_digest=str(fetch_packet["packet_digest"]),
        inputs={
            "authority_surface": DPRIME_ORDINARY_CONTRACT_AUTHORITY_SURFACE,
            "retained_refs_are_lineage_only": True,
        },
    )
    try:
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=(
                    ObservationType.DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORIZED
                ),
                status=RunStageStatus.COMPLETED,
                payload={"answer_contract_authority": contract_payload},
            )
        )
    except RunKernelTransitionError as exc:
        raise DPrimeOrdinaryContractAuthorityError(str(exc)) from exc
    return DPrimeOrdinaryContractAuthorityResult(
        run_kernel=run_kernel,
        authority_ref=_authority_ref(run_kernel),
    )


def _contract_authority_payload(
    *,
    run_id: str,
    request_id: str,
    contract_version: str,
    contract_digest: str,
    component: Mapping[str, Any],
    source_ids: Sequence[str],
    fetch_packet: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    component_digest = _required_text(
        component.get("component_digest")
        or component.get("component_contract_digest")
        or _digest_json(
            {
                "component_id": _SUPPORTED_COMPONENT_ID,
                "contract_digest": contract_digest,
                "source_obligation_candidate_ids": list(source_ids),
            }
        ),
        "D-prime component authority lacks component digest",
        limit=128,
    )
    qmr_digest = _digest_json(
        {
            "run_id": run_id,
            "request_id": request_id,
            "contract_digest": contract_digest,
            "component_id": _SUPPORTED_COMPONENT_ID,
            "reference_id": reference.get("reference_id"),
        }
    )
    return {
        "schema_version": DPRIME_ORDINARY_CONTRACT_AUTHORITY_SCHEMA_VERSION,
        "owner": DPRIME_ORDINARY_CONTRACT_AUTHORITY_OWNER,
        "trace_key": "dprime_answer_contract_authority",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": run_id,
        "request_id": request_id,
        "accepted_contract_version": contract_version,
        "accepted_contract_digest": contract_digest,
        "parent_question_meaning_record_id": (
            f"question-meaning-record:dprime-retained:{qmr_digest[:16]}"
        ),
        "parent_question_meaning_record_digest": qmr_digest,
        "parent_proposal_schema_version": (
            DPRIME_ORDINARY_CONTRACT_AUTHORITY_SCHEMA_VERSION
        ),
        "accepted_answer_component_refs": [
            {
                "component_id": _SUPPORTED_COMPONENT_ID,
                "component_revision": str(
                    component.get("component_revision") or "dprime-retained-1"
                ),
                "component_digest": component_digest,
                "requirement_posture": "required",
                "materiality": "material",
                "allowed_support_kinds": ["direct"],
                "source_obligation_candidate_ids": list(source_ids),
                "mandatory_caveats": [
                    "D-prime SemanticObservation does not bind ComponentCoverage.",
                ],
                "prohibited_upgrades": [
                    "Do not claim citation eligibility, source-obligation "
                    "satisfaction, SufficiencyReadiness, FAP, Author output, "
                    "answer text, or product correctness.",
                ],
            }
        ],
        "accepted_answer_component_count": 1,
        "accepted_semantic_slot_refs": [],
        "accepted_semantic_slot_count": 0,
        "material_ambiguity_count": 0,
        "material_ambiguity_preserved": True,
        "lineage": {
            "created_by": DPRIME_ORDINARY_CONTRACT_AUTHORITY_OWNER,
            "created_from": [
                "ordinary_dprime_product_status",
                "retained_source_fetch_read_lineage",
                "component_source_obligation_lineage",
            ],
            "fetch_read_content_packet_id": fetch_packet.get("packet_id"),
            "fetch_read_content_packet_digest": fetch_packet.get("packet_digest"),
            "reference_id": reference.get("reference_id"),
            "reference_digest": reference.get("reference_digest"),
            "retained_current_answer_contract_digest": contract_digest,
            "retained_refs_are_lineage_only": True,
            "retained_refs_are_authority": False,
        },
        "coverage_created": False,
        "semantic_observation_admitted": False,
        "source_obligation_satisfied": False,
        "citation_behavior_changed": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }


def _matching_reference(
    *,
    fetch_packet: Mapping[str, Any],
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    for item in fetch_packet.get("reference_records") or ():
        reference = _safe_mapping(item)
        if (
            reference.get("candidate_id") == admission.get("candidate_id")
            and reference.get("reference_id") == admission.get("reference_id")
            and reference.get("reference_digest") == admission.get("reference_digest")
        ):
            return reference
    raise DPrimeOrdinaryContractAuthorityError(
        "retained D-prime reference lineage does not match source/evidence custody"
    )


def _require_lineage(
    *,
    fetch_packet: Mapping[str, Any],
    reference: Mapping[str, Any],
    admission: Mapping[str, Any],
    component: Mapping[str, Any],
    source_obligation: Mapping[str, Any],
    contract_digest: str,
) -> None:
    if fetch_packet.get("packet_id") != admission.get("fetch_read_content_packet_id"):
        raise DPrimeOrdinaryContractAuthorityError(
            "fetch/read packet lineage does not match source/evidence custody"
        )
    if fetch_packet.get("packet_digest") != admission.get(
        "fetch_read_content_packet_digest"
    ):
        raise DPrimeOrdinaryContractAuthorityError(
            "fetch/read packet digest does not match source/evidence custody"
        )
    if component.get("component_id") != _SUPPORTED_COMPONENT_ID:
        raise DPrimeOrdinaryContractAuthorityError(
            "D-prime component lineage does not match retained packet"
        )
    if component.get("current_answer_contract_digest") != contract_digest:
        raise DPrimeOrdinaryContractAuthorityError(
            "component retained contract digest does not match source reference"
        )
    source_ids = set(_text_tuple(source_obligation.get("source_obligation_candidate_ids")))
    reference_ids = set(_text_tuple(reference.get("source_obligation_candidate_ids")))
    if _SUPPORTED_SOURCE_OBLIGATION_ID not in source_ids:
        raise DPrimeOrdinaryContractAuthorityError(
            "D-prime source-obligation lineage is unavailable"
        )
    if not source_ids.issubset(reference_ids):
        raise DPrimeOrdinaryContractAuthorityError(
            "source-obligation lineage does not match retained reference"
        )
    if source_obligation.get("satisfaction_claimed") is not False:
        raise DPrimeOrdinaryContractAuthorityError(
            "source-obligation satisfaction must remain closed"
        )


def _authority_ref(run_kernel: RunKernel) -> dict[str, Any]:
    projection = run_kernel.state.current_answer_contract_projection
    return {
        "status": "authorized",
        "owner": DPRIME_ORDINARY_CONTRACT_AUTHORITY_OWNER,
        "runtime_surface": DPRIME_ORDINARY_CONTRACT_AUTHORITY_SURFACE,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "accepted_contract_digest": (
            run_kernel.state.initial_answer_contract.get("accepted_contract_digest")
        ),
        "current_contract_digest": (
            projection.get("current_contract_digest")
            or projection.get("accepted_contract_digest")
        ),
        "retained_refs_are_lineage_only": True,
    }


def _required_text(value: Any, message: str, *, limit: int = 260) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        raise DPrimeOrdinaryContractAuthorityError(message)
    return text


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text_tuple(value: Any, *, limit: int = 200) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return (text,) if text else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _digest_json(value: Mapping[str, Any]) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = [
    "DPRIME_ORDINARY_CONTRACT_AUTHORITY_OWNER",
    "DPRIME_ORDINARY_CONTRACT_AUTHORITY_SCHEMA_VERSION",
    "DPRIME_ORDINARY_CONTRACT_AUTHORITY_SURFACE",
    "DPrimeOrdinaryContractAuthorityError",
    "DPrimeOrdinaryContractAuthorityResult",
    "build_dprime_ordinary_contract_authority",
]
