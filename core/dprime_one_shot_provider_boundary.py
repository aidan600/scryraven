"""D-prime one-shot provider boundary contract.

This module validates declared provider-boundary facts for a future D-prime
model-review call. It performs no provider import, provider/model selection,
model call, retry, fallback, prompt retention, response retention, payload
retention, search, retrieval, fetch/read, RunKernel admission, citation,
Author, or answer work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE = (
    "DPRIME-ONE-SHOT-PROVIDER-BOUNDARY-01"
)
DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_SCHEMA_VERSION = (
    "dprime_one_shot_provider_boundary_v1"
)
DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_ID = (
    "dprime-one-shot-provider-boundary:default-disabled:v1"
)

PROVIDER_BOUNDARY_STATUS_APPROVED = "approved"
PROVIDER_BOUNDARY_STATUS_NOT_APPROVED = "not approved"
PROVIDER_BOUNDARY_STATUS_REJECTED = "rejected"

PROVIDER_MODEL_SELECTION_UNRESOLVED = "unresolved"
PROVIDER_MODEL_SELECTION_APPROVAL_REF_PRESENT = "approval_ref_present"

RETRY_POLICY_FORBIDDEN = "forbidden"
FALLBACK_POLICY_FORBIDDEN = "forbidden"
TIMEOUT_POLICY_FAIL_CLOSED = "fail_closed"

_APPROVAL_REF_SELECTION_STATUSES = frozenset(
    {
        PROVIDER_MODEL_SELECTION_APPROVAL_REF_PRESENT,
        "approved_by_ref",
        "future_approval_ref_present",
    }
)
_BROAD_HELPER_CANDIDATES = frozenset(
    {
        "ask_model",
        "core.llm.ask_model",
        "llm.ask_model",
        "proplex.__main__.ask_model",
    }
)
_CLOSED_SURFACE_FALSE_FLAGS = frozenset(
    {
        "retry_loop_created",
        "fallback_enabled",
        "provider_switching_enabled",
        "multi_call_review_enabled",
        "raw_prompt_retained",
        "raw_model_response_retained",
        "provider_payload_retained",
        "real_model_called",
        "model_review_callable_invoked",
        "validated_support_proposal_created",
        "run_kernel_support_admission_request_created",
        "semantic_observation_created",
        "component_coverage_bound",
        "citation_eligibility_claimed",
        "source_obligation_satisfaction_claimed",
        "answer_text_created",
        "product_correctness_claimed",
        "analysis_gap_search_proposal_created",
    }
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
_AUTHORITY_KEYS = frozenset(
    {
        "analysis_gap_search_proposal",
        "answer",
        "answer_prose",
        "answer_text",
        "author_input",
        "author_prose",
        "citation",
        "citation_eligible",
        "component_coverage",
        "component_coverage_bound",
        "evidence_relative_analysis_packet",
        "final_answer_packet",
        "product_correctness",
        "run_kernel_admission",
        "run_kernel_decision",
        "semantic_observation",
        "source_obligation_satisfaction",
        "sufficiency_readiness",
        "validated_support_proposal",
    }
)
_DANGEROUS_TRUE_KEYS = _AUTHORITY_KEYS | _CLOSED_SURFACE_FALSE_FLAGS | frozenset(
    {
        "fallback_allowed",
        "fallback_policy_enabled",
        "model_success_claimed",
        "provider_switching",
        "retry_allowed",
        "retry_enabled",
    }
)


class DPrimeOneShotProviderBoundaryError(ValueError):
    """Raised when D-prime provider-boundary material cannot be coerced."""


@dataclass(frozen=True, slots=True)
class DPrimeOneShotProviderBoundary:
    """Declared boundary facts for a future one-shot D-prime provider call."""

    boundary_id: str = DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_ID
    phase: str = DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE
    enabled: bool = False
    default_disabled: bool = True
    test_only: bool = False
    provider_model_selection_status: str = PROVIDER_MODEL_SELECTION_UNRESOLVED
    provider_model_approval_ref: str | None = None
    max_provider_attempts: int = 0
    retry_policy: str = RETRY_POLICY_FORBIDDEN
    fallback_policy: str = FALLBACK_POLICY_FORBIDDEN
    timeout_policy: str = TIMEOUT_POLICY_FAIL_CLOSED
    raw_prompt_retention: bool = False
    raw_model_response_retention: bool = False
    provider_payload_retention: bool = False
    real_call_authorized: bool = False
    call_count: int = 0
    provider_model_selection_detail_present: bool = False
    provider_switching_allowed: bool = False
    candidate_helper: str | None = None
    one_shot_adapter_proven: bool = False
    closed_surface_flags: Mapping[str, bool] = field(
        default_factory=lambda: default_closed_surface_flags()
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> DPrimeOneShotProviderBoundary:
        safe = _required_mapping(value, "DPrimeOneShotProviderBoundary")
        enabled = safe.get("enabled") is True
        return cls(
            boundary_id=(
                _clean_text(safe.get("boundary_id"), limit=260)
                or DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_ID
            ),
            phase=(
                _clean_text(safe.get("phase"), limit=160)
                or DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE
            ),
            enabled=enabled,
            default_disabled=safe.get("default_disabled", not enabled) is True,
            test_only=safe.get("test_only") is True,
            provider_model_selection_status=(
                _clean_text(safe.get("provider_model_selection_status"), limit=120)
                or PROVIDER_MODEL_SELECTION_UNRESOLVED
            ),
            provider_model_approval_ref=_clean_text(
                safe.get("provider_model_approval_ref"),
                limit=320,
            ),
            max_provider_attempts=_bounded_int(
                safe.get("max_provider_attempts"),
                default=0,
            ),
            retry_policy=(
                _clean_text(safe.get("retry_policy"), limit=80)
                or RETRY_POLICY_FORBIDDEN
            ),
            fallback_policy=(
                _clean_text(safe.get("fallback_policy"), limit=80)
                or FALLBACK_POLICY_FORBIDDEN
            ),
            timeout_policy=(
                _clean_text(safe.get("timeout_policy"), limit=80)
                or TIMEOUT_POLICY_FAIL_CLOSED
            ),
            raw_prompt_retention=_flag(
                safe,
                "raw_prompt_retention",
                "raw_prompt_retained",
            ),
            raw_model_response_retention=_flag(
                safe,
                "raw_model_response_retention",
                "raw_model_response_retained",
            ),
            provider_payload_retention=_flag(
                safe,
                "provider_payload_retention",
                "provider_payload_retained",
                "raw_provider_payload_retained",
            ),
            real_call_authorized=safe.get("real_call_authorized") is True,
            call_count=_bounded_int(safe.get("call_count"), default=0),
            provider_model_selection_detail_present=any(
                _clean_text(safe.get(key), limit=260)
                for key in (
                    "provider",
                    "provider_id",
                    "provider_name",
                    "model",
                    "model_id",
                    "model_name",
                )
            ),
            provider_switching_allowed=_flag(
                safe,
                "provider_switching_allowed",
                "provider_switching",
                "provider_switching_enabled",
            ),
            candidate_helper=_clean_text(
                safe.get("candidate_helper")
                or safe.get("helper")
                or safe.get("callable_ref"),
                limit=260,
            ),
            one_shot_adapter_proven=safe.get("one_shot_adapter_proven") is True,
            closed_surface_flags=_closed_surface_flags_from_mapping(
                safe.get("closed_surface_flags")
            ),
        )

    def to_ref(self) -> dict[str, Any]:
        return {
            "schema_version": DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_SCHEMA_VERSION,
            "boundary_id": self.boundary_id,
            "phase": self.phase,
            "enabled": self.enabled,
            "default_disabled": self.default_disabled,
            "test_only": self.test_only,
            "provider_model_selection_status": self.provider_model_selection_status,
            "provider_model_approval_ref": self.provider_model_approval_ref,
            "max_provider_attempts": self.max_provider_attempts,
            "retry_policy": self.retry_policy,
            "fallback_policy": self.fallback_policy,
            "timeout_policy": self.timeout_policy,
            "raw_prompt_retention": self.raw_prompt_retention,
            "raw_model_response_retention": self.raw_model_response_retention,
            "provider_payload_retention": self.provider_payload_retention,
            "real_call_authorized": self.real_call_authorized,
            "call_count": self.call_count,
            "provider_model_selection_detail_present": (
                self.provider_model_selection_detail_present
            ),
            "provider_switching_allowed": self.provider_switching_allowed,
            "candidate_helper": self.candidate_helper,
            "one_shot_adapter_proven": self.one_shot_adapter_proven,
            "closed_surface_flags": dict(self.closed_surface_flags),
        }


@dataclass(frozen=True, slots=True)
class DPrimeOneShotProviderBoundaryValidation:
    """Validation/status projection for product and tests."""

    status: str
    boundary_ref: Mapping[str, Any]
    blockers: Sequence[str] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)

    @property
    def approved(self) -> bool:
        return self.status == PROVIDER_BOUNDARY_STATUS_APPROVED

    def to_status_ref(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "boundary_ref": dict(self.boundary_ref),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "provider_boundary_approved_is_not_semantic_support": True,
            "real_provider_call_performed": False,
            "real_model_call_performed": False,
        }


def build_default_dprime_one_shot_provider_boundary() -> DPrimeOneShotProviderBoundary:
    """Return the default-disabled, zero-call, not-approved boundary."""

    return DPrimeOneShotProviderBoundary()


def default_closed_surface_flags() -> dict[str, bool]:
    """Return required false flags for the D-prime provider boundary."""

    return {key: False for key in sorted(_CLOSED_SURFACE_FALSE_FLAGS)}


def validate_dprime_one_shot_provider_boundary(
    boundary: Mapping[str, Any] | DPrimeOneShotProviderBoundary | None = None,
) -> DPrimeOneShotProviderBoundaryValidation:
    """Validate whether a future real-call boundary is one-shot safe."""

    boundary_obj = _coerce_boundary(boundary)
    blockers = _safety_blockers(boundary_obj)
    if blockers:
        return DPrimeOneShotProviderBoundaryValidation(
            status=PROVIDER_BOUNDARY_STATUS_REJECTED,
            boundary_ref=boundary_obj.to_ref(),
            blockers=tuple(blockers),
        )

    approval_blockers = _approval_blockers(boundary_obj)
    if approval_blockers:
        return DPrimeOneShotProviderBoundaryValidation(
            status=PROVIDER_BOUNDARY_STATUS_NOT_APPROVED,
            boundary_ref=boundary_obj.to_ref(),
            blockers=tuple(approval_blockers),
        )

    return DPrimeOneShotProviderBoundaryValidation(
        status=PROVIDER_BOUNDARY_STATUS_APPROVED,
        boundary_ref=boundary_obj.to_ref(),
    )


def _safety_blockers(boundary: DPrimeOneShotProviderBoundary) -> list[str]:
    blockers: list[str] = []
    ref = boundary.to_ref()
    raw_private = sorted(_collect_keys(ref) & _RAW_PRIVATE_KEYS)
    if raw_private:
        blockers.append(
            "D-prime provider boundary includes raw/private fields: "
            + ", ".join(raw_private)
        )
    dangerous = sorted(_dangerous_true_claims(ref))
    if dangerous:
        blockers.append(
            "D-prime provider boundary attempts forbidden true flags: "
            + ", ".join(dangerous)
        )
    if not boundary.boundary_id:
        blockers.append("D-prime provider boundary_id is required")
    if boundary.phase != DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE:
        blockers.append("D-prime provider boundary phase is unsupported")
    if boundary.retry_policy != RETRY_POLICY_FORBIDDEN:
        blockers.append("D-prime provider boundary retries are forbidden")
    if boundary.fallback_policy != FALLBACK_POLICY_FORBIDDEN:
        blockers.append("D-prime provider boundary fallback is forbidden")
    if boundary.timeout_policy != TIMEOUT_POLICY_FAIL_CLOSED:
        blockers.append("D-prime provider boundary timeout policy must fail closed")
    if boundary.raw_prompt_retention:
        blockers.append("D-prime provider boundary cannot retain raw prompts")
    if boundary.raw_model_response_retention:
        blockers.append("D-prime provider boundary cannot retain raw model responses")
    if boundary.provider_payload_retention:
        blockers.append("D-prime provider boundary cannot retain provider payloads")
    if boundary.provider_switching_allowed:
        blockers.append("D-prime provider boundary cannot allow provider switching")
    if boundary.provider_model_selection_detail_present:
        blockers.append(
            "D-prime provider boundary cannot select provider/model in this phase"
        )
    if boundary.max_provider_attempts > 1:
        blockers.append("D-prime provider boundary cannot allow multiple attempts")
    if boundary.call_count > boundary.max_provider_attempts:
        blockers.append("D-prime provider boundary call count exceeds attempt cap")
    helper = _normalize_token(boundary.candidate_helper)
    if helper in _BROAD_HELPER_CANDIDATES and not boundary.one_shot_adapter_proven:
        blockers.append(
            "broad model helper candidate is unsafe without a proven one-shot adapter"
        )
    closed_flags = _closed_surface_flags_from_mapping(boundary.closed_surface_flags)
    for key in sorted(_CLOSED_SURFACE_FALSE_FLAGS):
        if closed_flags.get(key) is not False:
            blockers.append(f"closed_surface_flags must keep {key} false")
    return blockers


def _approval_blockers(boundary: DPrimeOneShotProviderBoundary) -> list[str]:
    blockers: list[str] = []
    if boundary.enabled is not True:
        blockers.append("D-prime provider boundary is default-disabled")
    if boundary.default_disabled is not False:
        blockers.append("D-prime provider boundary has not been explicitly enabled")
    if boundary.real_call_authorized is not True:
        blockers.append("D-prime real provider call is not authorized")
    if boundary.max_provider_attempts != 1:
        blockers.append("D-prime approved boundary requires max_provider_attempts == 1")
    if boundary.call_count != 0:
        blockers.append("D-prime approved boundary must be pre-run with call_count 0")
    if (
        boundary.provider_model_selection_status
        not in _APPROVAL_REF_SELECTION_STATUSES
    ):
        blockers.append(
            "D-prime approved boundary requires provider/model approval ref status"
        )
    if not boundary.provider_model_approval_ref:
        blockers.append(
            "D-prime approved boundary requires explicit provider/model approval ref"
        )
    return blockers


def _coerce_boundary(
    value: Mapping[str, Any] | DPrimeOneShotProviderBoundary | None,
) -> DPrimeOneShotProviderBoundary:
    if isinstance(value, DPrimeOneShotProviderBoundary):
        return value
    if value is None:
        return build_default_dprime_one_shot_provider_boundary()
    if isinstance(value, Mapping):
        return DPrimeOneShotProviderBoundary.from_mapping(value)
    raise DPrimeOneShotProviderBoundaryError(
        "D-prime provider boundary must be a mapping"
    )


def _closed_surface_flags_from_mapping(value: Any) -> dict[str, bool]:
    if not isinstance(value, Mapping):
        return default_closed_surface_flags()
    flags = default_closed_surface_flags()
    for key, item in value.items():
        normalized = _normalize_key(key)
        if normalized in _CLOSED_SURFACE_FALSE_FLAGS:
            flags[normalized] = item is True
    return flags


def _required_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DPrimeOneShotProviderBoundaryError(f"{label} must be a mapping")
    return dict(value)


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(normalized)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _flag(value: Mapping[str, Any], *keys: str) -> bool:
    return any(value.get(key) is True for key in keys)


def _bounded_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _normalize_token(value: Any) -> str:
    return str(value or "").strip().casefold()


__all__ = [
    "DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_ID",
    "DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE",
    "DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_SCHEMA_VERSION",
    "DPrimeOneShotProviderBoundary",
    "DPrimeOneShotProviderBoundaryError",
    "DPrimeOneShotProviderBoundaryValidation",
    "FALLBACK_POLICY_FORBIDDEN",
    "PROVIDER_BOUNDARY_STATUS_APPROVED",
    "PROVIDER_BOUNDARY_STATUS_NOT_APPROVED",
    "PROVIDER_BOUNDARY_STATUS_REJECTED",
    "PROVIDER_MODEL_SELECTION_APPROVAL_REF_PRESENT",
    "PROVIDER_MODEL_SELECTION_UNRESOLVED",
    "RETRY_POLICY_FORBIDDEN",
    "TIMEOUT_POLICY_FAIL_CLOSED",
    "build_default_dprime_one_shot_provider_boundary",
    "default_closed_surface_flags",
    "validate_dprime_one_shot_provider_boundary",
]
