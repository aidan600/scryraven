"""D-prime source-obligation and citation-source handoff authority.

This runtime consumes bound D-prime ComponentCoverage from ordinary product
status. It creates and consumes source-obligation authority only through a
product/RunKernel-owned surface. It creates and consumes citation eligibility or
citation-source handoff only through a product/RunKernel-owned surface. It is
consumed by ordinary product status in the same phase.

It does not create SufficiencyReadiness, FAP, Author output, answer text,
product correctness, live calls, provider/model calls, search, fetch/read, or
retrieval.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.dprime_semantic_observation_materialization_runtime import (
    DPrimeSemanticObservationMaterializationResult,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)

DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SCHEMA_VERSION = (
    "dprime_source_obligation_citation_authority_runtime_v1"
)
DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SURFACE = (
    "core.dprime_source_obligation_citation_authority_runtime"
)
DPRIME_SOURCE_OBLIGATION_AUTHORITY_OWNER = (
    "RunKernel.DPrimeSourceObligationAuthority"
)
DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_OWNER = (
    "RunKernel.DPrimeCitationSourceHandoffAuthority"
)

BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED = (
    "BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED"
)


class DPrimeSourceObligationCitationAuthorityError(ValueError):
    """Raised when D-prime source/citation authority cannot be consumed."""

    def __init__(self, blocker: str, detail: str) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DPrimeSourceObligationCitationAuthorityResult:
    source_obligation_authority_ref: Mapping[str, Any]
    citation_eligibility_authority_ref: Mapping[str, Any]
    decision: str = BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED
    blocker_detail: str = (
        "D-prime evidence-support bundle consumed source-obligation authority "
        "and citation-source handoff authority; SufficiencyReadiness is not "
        "licensed in this phase"
    )


def consume_dprime_source_obligation_and_citation_authority(
    *,
    semantic_materialization: DPrimeSemanticObservationMaterializationResult,
    run_kernel: RunKernel,
    component_coverage_projection: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    citation_source_obligation_readiness_ref: Mapping[str, Any],
) -> DPrimeSourceObligationCitationAuthorityResult:
    """Consume D-prime source obligation, then citation-source handoff authority."""

    coverage = _safe_mapping(component_coverage_projection)
    source_ref = _safe_mapping(source_obligation_ref)
    readiness_ref = _safe_mapping(citation_source_obligation_readiness_ref)
    content_ref = semantic_materialization.sanitized_content_reference.to_dict(
        include_validation=False
    )
    observation_ref = semantic_materialization.semantic_observation_ref
    source_ids = _text_tuple(source_ref.get("source_obligation_candidate_ids"))
    _require_bound_coverage(
        coverage=coverage,
        observation_ref=observation_ref,
        content_ref=content_ref,
        source_ids=source_ids,
    )

    source_state = _source_obligation_authority_state(
        run_kernel=run_kernel,
        coverage=coverage,
        observation_ref=observation_ref,
        content_ref=content_ref,
        source_ids=source_ids,
        source_ref=source_ref,
        readiness_ref=readiness_ref,
    )
    try:
        source_action = run_kernel.authorize_dprime_source_obligation_authority(
            source_obligation_authority_id=str(
                source_state["source_obligation_authority_id"]
            ),
            source_obligation_authority_digest=str(
                source_state["source_obligation_authority_digest"]
            ),
            coverage_record_id=str(coverage["coverage_record_id"]),
            coverage_record_digest=str(coverage["coverage_record_digest"]),
            coverage_reduction_digest=str(coverage["coverage_reduction_digest"]),
            answer_component_id=str(coverage["answer_component_id"]),
            source_obligation_candidate_ids=source_ids,
            semantic_observation_id=str(observation_ref["observation_id"]),
            semantic_observation_digest=str(observation_ref["observation_digest"]),
            content_ref_id=str(content_ref["content_ref_id"]),
            evidence_ref_id=str(content_ref["evidence_ref_id"]),
            inputs={
                "runtime_surface": DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SURFACE,
                "component_coverage_only_treated_as_pass": False,
                "retained_ids_alone_are_authority": False,
                "sufficiency_readiness_created": False,
                "final_answer_packet_created": False,
                "author_answer_created": False,
                "product_correctness_claimed": False,
            },
        )
        run_kernel.reduce(
            Observation.from_action(
                source_action,
                observation_type=(
                    ObservationType.DPRIME_SOURCE_OBLIGATION_AUTHORITY_CONSUMED
                ),
                status=RunStageStatus.COMPLETED,
                payload={"dprime_source_obligation_authority": source_state},
            )
        )
    except RunKernelTransitionError as exc:
        raise DPrimeSourceObligationCitationAuthorityError(
            "BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING",
            str(exc),
        ) from exc

    source_projection = dict(run_kernel.state.dprime_source_obligation_authority_projection)
    citation_state = _citation_source_handoff_authority_state(
        run_kernel=run_kernel,
        coverage=coverage,
        source_projection=source_projection,
        content_ref=content_ref,
        source_ids=source_ids,
    )
    try:
        citation_action = run_kernel.authorize_dprime_citation_source_handoff_authority(
            citation_source_handoff_id=str(
                citation_state["citation_source_handoff_id"]
            ),
            citation_source_handoff_digest=str(
                citation_state["citation_source_handoff_digest"]
            ),
            source_obligation_authority_id=str(
                source_projection["source_obligation_authority_id"]
            ),
            source_obligation_authority_digest=str(
                source_projection["source_obligation_authority_digest"]
            ),
            coverage_record_id=str(coverage["coverage_record_id"]),
            coverage_record_digest=str(coverage["coverage_record_digest"]),
            citation_eligible_source_ids=tuple(
                str(item["source_id"])
                for item in citation_state["citation_source_records"]
            ),
            inputs={
                "runtime_surface": DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SURFACE,
                "source_obligation_authority_consumed": True,
                "citation_rendering_created": False,
                "sufficiency_readiness_created": False,
                "final_answer_packet_created": False,
                "author_answer_created": False,
                "product_correctness_claimed": False,
            },
        )
        run_kernel.reduce(
            Observation.from_action(
                citation_action,
                observation_type=(
                    ObservationType.DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_CONSUMED
                ),
                status=RunStageStatus.COMPLETED,
                payload={"dprime_citation_source_handoff_authority": citation_state},
            )
        )
    except RunKernelTransitionError as exc:
        raise DPrimeSourceObligationCitationAuthorityError(
            "BLOCKED_DPRIME_CITATION_SOURCE_HANDOFF_MISSING",
            str(exc),
        ) from exc

    return DPrimeSourceObligationCitationAuthorityResult(
        source_obligation_authority_ref=dict(
            run_kernel.state.dprime_source_obligation_authority_projection
        ),
        citation_eligibility_authority_ref=dict(
            run_kernel.state.dprime_citation_source_handoff_projection
        ),
    )


def _require_bound_coverage(
    *,
    coverage: Mapping[str, Any],
    observation_ref: Mapping[str, Any],
    content_ref: Mapping[str, Any],
    source_ids: Sequence[str],
) -> None:
    if coverage.get("canonical_state") is not True:
        _blocked("ComponentCoverage projection is not canonical RunKernel state")
    if coverage.get("coverage_state") != "supported_with_caveats":
        _blocked("D-prime source authority requires supported_with_caveats coverage")
    if coverage.get("semantic_support_status") != "supported":
        _blocked("D-prime source authority requires supported semantic support")
    if not coverage.get("coverage_record_id") or not coverage.get(
        "coverage_record_digest"
    ):
        _blocked("ComponentCoverage ref/digest is missing")
    if not source_ids:
        _blocked("source-obligation authority requires retained source ids")
    observation_ids = {
        _safe_mapping(item).get("observation_id")
        for item in coverage.get("accepted_observation_refs") or ()
        if isinstance(item, Mapping)
    }
    if observation_ref.get("observation_id") not in observation_ids:
        _blocked("ComponentCoverage does not bind the admitted D-prime observation")
    content_ids = {
        _safe_mapping(item).get("content_ref_id")
        for item in coverage.get("content_reference_bindings") or ()
        if isinstance(item, Mapping)
    }
    if content_ref.get("content_ref_id") not in content_ids:
        _blocked("ComponentCoverage does not bind the D-prime content reference")


def _source_obligation_authority_state(
    *,
    run_kernel: RunKernel,
    coverage: Mapping[str, Any],
    observation_ref: Mapping[str, Any],
    content_ref: Mapping[str, Any],
    source_ids: Sequence[str],
    source_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
) -> dict[str, Any]:
    authority_id = (
        "dprime-source-obligation-authority:"
        f"{str(coverage['coverage_reduction_digest'])[:16]}"
    )
    digest_payload = {
        "authority_id": authority_id,
        "coverage_record_digest": coverage.get("coverage_record_digest"),
        "source_obligation_candidate_ids": list(source_ids),
        "semantic_observation_digest": observation_ref.get("observation_digest"),
        "content_ref_id": content_ref.get("content_ref_id"),
    }
    authority_digest = _digest_json(digest_payload)
    return {
        "schema_version": DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SCHEMA_VERSION,
        "owner": DPRIME_SOURCE_OBLIGATION_AUTHORITY_OWNER,
        "runtime_surface": DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SURFACE,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "source_obligation_authority_id": authority_id,
        "source_obligation_authority_digest": authority_digest,
        "source_obligation_authority_status": "consumed",
        "source_obligation_status": "satisfied",
        "status": "consumed",
        "authority_consumed": True,
        "satisfaction_claimed": True,
        "satisfaction_authority_backed_by": "RunKernel.DPrimeSourceObligationAuthority",
        "retained_ids_consumed_as_lineage": True,
        "retained_ids_alone_are_authority": False,
        "component_coverage_only_treated_as_pass": False,
        "source_obligation_candidate_ids": list(source_ids),
        "satisfied_source_obligation_ids": list(source_ids),
        "component_coverage_ref": {
            "coverage_record_id": coverage.get("coverage_record_id"),
            "coverage_record_digest": coverage.get("coverage_record_digest"),
            "coverage_reduction_digest": coverage.get("coverage_reduction_digest"),
            "coverage_state": coverage.get("coverage_state"),
            "semantic_support_status": coverage.get("semantic_support_status"),
        },
        "semantic_observation_ref": {
            "observation_id": observation_ref.get("observation_id"),
            "observation_digest": observation_ref.get("observation_digest"),
        },
        "content_ref": _source_safe_content_ref(content_ref),
        "lineage": {
            "created_by": DPRIME_SOURCE_OBLIGATION_AUTHORITY_OWNER,
            "created_from": [
                "ordinary_dprime_product_status",
                "admitted_dprime_semantic_observation",
                "bound_dprime_component_coverage",
                "lineage_only_source_obligation_ref",
            ],
            "readiness_posture_consumed": readiness_ref.get("posture"),
            "source_ref_lineage_only": bool(source_ref.get("lineage_only")),
        },
        "citation_eligibility_authority_consumed": False,
        "citation_rendering_created": False,
        "sufficiency_readiness_created": False,
        "final_answer_packet_created": False,
        "author_answer_created": False,
        "product_correctness_claimed": False,
        "live_validation_not_run": True,
    }


def _citation_source_handoff_authority_state(
    *,
    run_kernel: RunKernel,
    coverage: Mapping[str, Any],
    source_projection: Mapping[str, Any],
    content_ref: Mapping[str, Any],
    source_ids: Sequence[str],
) -> dict[str, Any]:
    handoff_id = (
        "dprime-citation-source-handoff:"
        f"{str(source_projection['source_obligation_authority_digest'])[:16]}"
    )
    source_record = _citation_source_record(
        content_ref=content_ref,
        source_obligation_id=source_ids[0],
    )
    digest_payload = {
        "handoff_id": handoff_id,
        "source_obligation_authority_digest": source_projection.get(
            "source_obligation_authority_digest"
        ),
        "coverage_record_digest": coverage.get("coverage_record_digest"),
        "citation_source_records": [source_record],
    }
    handoff_digest = _digest_json(digest_payload)
    return {
        "schema_version": DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SCHEMA_VERSION,
        "owner": DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_OWNER,
        "runtime_surface": DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SURFACE,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "citation_source_handoff_id": handoff_id,
        "citation_source_handoff_digest": handoff_digest,
        "citation_eligibility_authority_status": "consumed",
        "citation_source_handoff_status": "consumed",
        "status": "consumed",
        "authority_consumed": True,
        "citation_eligibility_authority_consumed": True,
        "citation_source_handoff_consumed": True,
        "source_obligation_authority_consumed": True,
        "source_obligation_authority_ref": {
            "source_obligation_authority_id": source_projection.get(
                "source_obligation_authority_id"
            ),
            "source_obligation_authority_digest": source_projection.get(
                "source_obligation_authority_digest"
            ),
            "source_obligation_status": source_projection.get(
                "source_obligation_status"
            ),
        },
        "component_coverage_ref": {
            "coverage_record_id": coverage.get("coverage_record_id"),
            "coverage_record_digest": coverage.get("coverage_record_digest"),
            "coverage_reduction_digest": coverage.get("coverage_reduction_digest"),
        },
        "citation_eligible_source_ids": [source_record["source_id"]],
        "citation_source_records": [source_record],
        "citation_rendering_created": False,
        "citations_rendered": False,
        "citation_formatter_invoked": False,
        "ordered_product_source_output_created": False,
        "sufficiency_readiness_created": False,
        "final_answer_packet_created": False,
        "author_answer_created": False,
        "author_input_created": False,
        "product_correctness_claimed": False,
        "live_validation_not_run": True,
        "reasons": [
            "citation-source handoff is backed by D-prime source-obligation authority",
            "source identity is safe handoff metadata, not rendered citation prose",
            "SufficiencyReadiness/FAP/Author remain closed",
        ],
    }


def _citation_source_record(
    *,
    content_ref: Mapping[str, Any],
    source_obligation_id: str,
) -> dict[str, Any]:
    source_domain = _clean_text(content_ref.get("source_domain"), limit=160)
    source_id = (
        _clean_text(content_ref.get("source_id"), limit=260)
        or (f"source:{source_domain}" if source_domain else None)
        or _clean_text(content_ref.get("evidence_ref_id"), limit=260)
    )
    if not source_id:
        _blocked("citation-source handoff requires source identity")
    return {
        "source_id": source_id,
        "evidence_id": content_ref.get("evidence_ref_id"),
        "content_ref_id": content_ref.get("content_ref_id"),
        "source_obligation_id": source_obligation_id,
        "url": content_ref.get("source_url"),
        "domain": content_ref.get("source_domain"),
        "title": content_ref.get("source_title"),
        "source_digest": content_ref.get("source_digest"),
        "citation_rendered_text": None,
        "citation_rendering_created": False,
        "author_prose_created": False,
    }


def _source_safe_content_ref(content_ref: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_ref_id": content_ref.get("content_ref_id"),
        "evidence_ref_id": content_ref.get("evidence_ref_id"),
        "source_id": content_ref.get("source_id"),
        "source_digest": content_ref.get("source_digest"),
        "source_url": content_ref.get("source_url"),
        "source_title": content_ref.get("source_title"),
        "source_domain": content_ref.get("source_domain"),
        "content_digest": content_ref.get("content_digest"),
        "readable_content_retained": False,
    }


def _blocked(detail: str) -> None:
    raise DPrimeSourceObligationCitationAuthorityError(
        "BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING",
        detail,
    )


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
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
    "BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED",
    "DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_OWNER",
    "DPRIME_SOURCE_OBLIGATION_AUTHORITY_OWNER",
    "DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SCHEMA_VERSION",
    "DPRIME_SOURCE_OBLIGATION_CITATION_AUTHORITY_SURFACE",
    "DPrimeSourceObligationCitationAuthorityError",
    "DPrimeSourceObligationCitationAuthorityResult",
    "consume_dprime_source_obligation_and_citation_authority",
]
