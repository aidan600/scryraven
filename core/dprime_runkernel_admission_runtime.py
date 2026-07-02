"""RunKernel-owned D-prime support-proposal admission decisions.

This module is the narrow RunKernel-owned authority surface for D-prime
``RunKernelSupportProposalAdmissionRequest`` material. D-prime may prepare and
validate the request, but this runtime owns the admitted/rejected/challenged
decision projection. It does not create admitted semantic support,
SemanticObservation, ComponentCoverage, citations, source-obligation
satisfaction, SufficiencyReadiness, FinalAnswerPacket, Author output, answer
text, product correctness, live calls, model calls, provider calls, search,
fetch/read, or retrieval.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.dprime_support_proposal_schema import (
    DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY,
    DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
    RunKernelSupportProposalAdmissionRequest,
)

DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SCHEMA_VERSION = (
    "dprime_runkernel_admission_runtime_v1"
)
DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SURFACE = (
    "core.dprime_runkernel_admission_runtime"
)
DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED = "admitted"
DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED = "rejected"
DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED = "challenged"
DPRIME_RUN_KERNEL_ADMISSION_DECISION_STATUSES = frozenset(
    {
        DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
        DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED,
        DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED,
    }
)
BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED = (
    "BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED"
)
BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_REJECTED = (
    "BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_REJECTED"
)
BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_CHALLENGED = (
    "BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_CHALLENGED"
)

_RAW_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "bounded_text",
        "cache_row",
        "cookie",
        "cookies",
        "db_row",
        "env",
        "full_prompt",
        "full_text",
        "full_trace",
        "header",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_html",
        "raw_model_response",
        "raw_page",
        "raw_page_content",
        "raw_page_text",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "raw_text",
        "secret",
        "secrets",
        "token",
        "unbounded_text",
    }
)
_DOWNSTREAM_FORBIDDEN_KEYS = frozenset(
    {
        "answer",
        "answer_text",
        "author",
        "author_answer",
        "author_input",
        "author_prose",
        "citation",
        "citation_eligible",
        "citation_eligibility",
        "citation_rendered",
        "component_coverage",
        "component_coverage_ref",
        "component_coverage_status",
        "componentcoverage",
        "final_answer",
        "final_answer_packet",
        "product_correctness",
        "product_correctness_claimed",
        "run_kernel_admission_decision_ref",
        "run_kernel_admission_decision_status",
        "source_obligation_satisfaction",
        "source_obligation_satisfied",
        "sufficiency_readiness",
        "semantic_observation",
        "semantic_observation_ref",
        "semantic_observation_status",
        "semanticobservation",
    }
)
_SMUGGLED_DECISION_KEYS = frozenset(
    {
        "admit",
        "admitted",
        "challenge",
        "challenged",
        "reject",
        "rejected",
    }
)
_CLOSED_FALSE_KEYS = frozenset(
    {
        "component_coverage_created",
        "semantic_observation_created",
    }
)


class DPrimeRunKernelAdmissionRuntimeError(ValueError):
    """Raised when a D-prime request is unsafe for RunKernel decision."""


@dataclass(frozen=True, slots=True)
class RunKernelDPrimeAdmissionDecision:
    """RunKernel-owned D-prime decision; not admitted semantic support."""

    decision_status: str
    request_ref: Mapping[str, Any]
    rationale: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision_status not in DPRIME_RUN_KERNEL_ADMISSION_DECISION_STATUSES:
            raise DPrimeRunKernelAdmissionRuntimeError(
                f"unsupported RunKernel D-prime decision: {self.decision_status}"
            )
        _reject_unsafe_request_material(
            self.request_ref,
            context="RunKernelDPrimeAdmissionDecision.request_ref",
        )
        _reject_decision_metadata(self.metadata)

    @property
    def decision_id(self) -> str:
        request_digest = _request_digest(self.request_ref)
        return f"dprime-runkernel-admission-decision:{request_digest[:16]}"

    @property
    def decision_digest(self) -> str:
        return _digest_json(self._digest_payload())

    @property
    def blocker(self) -> str:
        if self.decision_status == DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED:
            return BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED
        if self.decision_status == DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED:
            return BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_REJECTED
        return BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_CHALLENGED

    @property
    def blocker_detail(self) -> str:
        if self.decision_status == DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED:
            return (
                "RunKernel admitted the D-prime proposal decision, but "
                "SemanticObservation materialization is not licensed"
            )
        if self.decision_status == DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED:
            return "RunKernel rejected the D-prime support proposal request"
        return "RunKernel challenged the D-prime support proposal request"

    @property
    def semantic_support_source(self) -> str:
        if self.decision_status == DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED:
            return (
                "unavailable; RunKernel admitted decision not materialized into "
                "SemanticObservation"
            )
        return "unavailable; RunKernel decision did not admit semantic support"

    def to_dict(self) -> dict[str, Any]:
        support_ref = _safe_mapping(self.request_ref.get("support_proposal_ref"))
        validation_ref = _safe_mapping(self.request_ref.get("validation_result_ref"))
        return {
            "schema_version": DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SCHEMA_VERSION,
            "record_kind": "RunKernelDPrimeAdmissionDecision",
            "owner": "RunKernel",
            "runtime_surface": DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SURFACE,
            "decision_status": self.decision_status,
            "run_kernel_decision": self.decision_status,
            "decision_id": self.decision_id,
            "decision_digest": self.decision_digest,
            "request_ref": _public_request_ref(self.request_ref),
            "support_proposal_ref": support_ref,
            "validation_result_ref": validation_ref,
            "rationale": _clean_text(self.rationale, limit=280),
            "admitted_support": False,
            "semantic_observation_created": False,
            "component_coverage_created": False,
            "citation_eligibility_claimed": False,
            "source_obligation_satisfaction_claimed": False,
            "sufficiency_readiness_created": False,
            "final_answer_packet_created": False,
            "author_answer_created": False,
            "product_correctness_claimed": False,
            "semantic_support_source": self.semantic_support_source,
            "decision": self.blocker,
            "blocker_detail": self.blocker_detail,
            "metadata": _safe_mapping(self.metadata),
        }

    def to_status_overlay(self) -> dict[str, Any]:
        ref = {
            "decision_id": self.decision_id,
            "decision_digest": self.decision_digest,
            "decision_status": self.decision_status,
            "owner": "RunKernel",
            "runtime_surface": DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SURFACE,
        }
        return {
            "run_kernel_decision": self.decision_status,
            "run_kernel_admission_decision_status": self.decision_status,
            "run_kernel_admission_decision_ref": ref,
            "run_kernel_admission_decision_owner": "RunKernel",
            "run_kernel_admission_decision_surface": (
                DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SURFACE
            ),
            "admitted_support": False,
            "semantic_observation_admission_status": "unavailable",
            "component_coverage_status": "unavailable",
            "semantic_support_source": self.semantic_support_source,
            "decision": self.blocker,
            "blocker_detail": self.blocker_detail,
        }

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema_version": DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SCHEMA_VERSION,
            "owner": "RunKernel",
            "runtime_surface": DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SURFACE,
            "decision_status": self.decision_status,
            "request_digest": _request_digest(self.request_ref),
            "support_proposal_ref": _safe_mapping(
                self.request_ref.get("support_proposal_ref")
            ),
            "validation_result_ref": _safe_mapping(
                self.request_ref.get("validation_result_ref")
            ),
        }


def build_run_kernel_dprime_admission_decision(
    request: Mapping[str, Any] | RunKernelSupportProposalAdmissionRequest,
    *,
    decision_status: str = DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
    rationale: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> RunKernelDPrimeAdmissionDecision:
    """Consume a valid D-prime request/ref and report a RunKernel decision."""

    request_ref = _coerce_request_ref(request)
    _require_request_lineage(request_ref)
    return RunKernelDPrimeAdmissionDecision(
        decision_status=decision_status,
        request_ref=request_ref,
        rationale=rationale,
        metadata=_safe_mapping(metadata),
    )


def _coerce_request_ref(
    request: Mapping[str, Any] | RunKernelSupportProposalAdmissionRequest,
) -> dict[str, Any]:
    if isinstance(request, RunKernelSupportProposalAdmissionRequest):
        request = request.to_dict()
    if not isinstance(request, Mapping):
        raise DPrimeRunKernelAdmissionRuntimeError(
            "RunKernel D-prime admission decision requires a request mapping"
        )
    _reject_unsafe_request_material(
        request,
        context="RunKernel D-prime admission request",
    )
    safe = dict(request)
    support_ref = _safe_mapping(safe.get("support_proposal_ref"))
    validation_ref = _safe_mapping(safe.get("validation_result_ref"))
    request_status = _clean_text(safe.get("request_status"), limit=120)
    record_kind = _clean_text(safe.get("record_kind"), limit=120)
    return _without_empty(
        {
            "record_kind": record_kind
            or "RunKernelSupportProposalAdmissionRequest",
            "request_status": request_status,
            "request_digest": _clean_text(safe.get("request_digest"), limit=128)
            or _digest_json(_json_safe(safe)),
            "support_proposal_ref": support_ref,
            "validation_result_ref": validation_ref,
        }
    )


def _require_request_lineage(request_ref: Mapping[str, Any]) -> None:
    if request_ref.get("record_kind") != "RunKernelSupportProposalAdmissionRequest":
        raise DPrimeRunKernelAdmissionRuntimeError(
            "RunKernel decision requires a D-prime admission request"
        )
    if request_ref.get("request_status") != DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY:
        raise DPrimeRunKernelAdmissionRuntimeError(
            "RunKernel decision requires a ready admission request"
        )
    if not _clean_text(request_ref.get("request_digest"), limit=128):
        raise DPrimeRunKernelAdmissionRuntimeError(
            "RunKernel decision requires request digest lineage"
        )
    support_ref = _safe_mapping(request_ref.get("support_proposal_ref"))
    validation_ref = _safe_mapping(request_ref.get("validation_result_ref"))
    if not _clean_text(support_ref.get("proposal_id"), limit=320):
        raise DPrimeRunKernelAdmissionRuntimeError(
            "RunKernel decision requires proposal id lineage"
        )
    if not _clean_text(support_ref.get("proposal_digest"), limit=128):
        raise DPrimeRunKernelAdmissionRuntimeError(
            "RunKernel decision requires proposal digest lineage"
        )
    if validation_ref.get("validation_status") != (
        DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    ):
        raise DPrimeRunKernelAdmissionRuntimeError(
            "RunKernel decision requires passed proposal validation status"
        )
    if validation_ref.get("support_proposal_validation_passed") is not True:
        raise DPrimeRunKernelAdmissionRuntimeError(
            "RunKernel decision requires passed validation flag"
        )
    if not _clean_text(validation_ref.get("validation_result_digest"), limit=128):
        raise DPrimeRunKernelAdmissionRuntimeError(
            "RunKernel decision requires validation result digest lineage"
        )


def _reject_unsafe_request_material(value: Any, *, context: str) -> None:
    for path, key, item in _walk_mapping_items(value):
        normalized = _normalize_key(key)
        if normalized in _RAW_PRIVATE_KEYS:
            raise DPrimeRunKernelAdmissionRuntimeError(
                f"{context} includes raw/private material: {'.'.join(path)}"
            )
        if normalized in _DOWNSTREAM_FORBIDDEN_KEYS:
            raise DPrimeRunKernelAdmissionRuntimeError(
                f"{context} includes downstream closed material: {'.'.join(path)}"
            )
        if normalized in _SMUGGLED_DECISION_KEYS:
            raise DPrimeRunKernelAdmissionRuntimeError(
                f"{context} smuggles RunKernel decision vocabulary: {'.'.join(path)}"
            )
        if normalized == "admitted_support" and item is not False:
            raise DPrimeRunKernelAdmissionRuntimeError(
                f"{context} attempts admitted_support true"
            )
        if normalized in _CLOSED_FALSE_KEYS and item is not False:
            raise DPrimeRunKernelAdmissionRuntimeError(
                f"{context} attempts downstream closed surface: {'.'.join(path)}"
            )
        if normalized == "run_kernel_decision" and _normalize_key(item) != "not_made":
            raise DPrimeRunKernelAdmissionRuntimeError(
                f"{context} attempts prebuilt RunKernel decision"
            )


def _reject_decision_metadata(value: Mapping[str, Any]) -> None:
    _reject_unsafe_request_material(
        value,
        context="RunKernelDPrimeAdmissionDecision.metadata",
    )


def _walk_mapping_items(value: Any, path: Sequence[str] = ()) -> list[tuple[tuple[str, ...], str, Any]]:
    items: list[tuple[tuple[str, ...], str, Any]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            item_path = (*path, key_text)
            items.append((item_path, key_text, item))
            items.extend(_walk_mapping_items(item, item_path))
    elif isinstance(value, list | tuple | set | frozenset):
        for index, item in enumerate(value):
            items.extend(_walk_mapping_items(item, (*path, str(index))))
    return items


def _public_request_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "record_kind": value.get("record_kind"),
            "request_status": value.get("request_status"),
            "request_digest": value.get("request_digest"),
            "support_proposal_ref": _safe_mapping(value.get("support_proposal_ref")),
            "validation_result_ref": _safe_mapping(
                value.get("validation_result_ref")
            ),
        }
    )


def _request_digest(value: Mapping[str, Any]) -> str:
    digest = _clean_text(value.get("request_digest"), limit=128)
    return digest or _digest_json(_public_request_ref(value))


def _safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    return value


__all__ = [
    "BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_CHALLENGED",
    "BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_REJECTED",
    "BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED",
    "DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED",
    "DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED",
    "DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED",
    "DPRIME_RUN_KERNEL_ADMISSION_DECISION_STATUSES",
    "DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SCHEMA_VERSION",
    "DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SURFACE",
    "DPrimeRunKernelAdmissionRuntimeError",
    "RunKernelDPrimeAdmissionDecision",
    "build_run_kernel_dprime_admission_decision",
]
