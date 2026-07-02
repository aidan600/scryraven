"""D-prime one-shot model-review adapter contract.

This module owns the product contract for a future single D-prime model-review
call. It validates safe adapter metadata and provides the single-attempt
``invoke_once`` path used by the product runner. It does not select a provider
or model, import provider clients, retry, fall back, retain raw prompts or
outputs, search, retrieve, fetch/read, create support proposals, request
RunKernel admission, admit SemanticObservation, bind ComponentCoverage, create
citations, write answer text, or claim product correctness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_PHASE = (
    "DPRIME-REAL-MODEL-REVIEW-ADAPTER-CONTRACT-01"
)
DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_SCHEMA_VERSION = (
    "dprime_one_shot_model_review_adapter_contract_01_v1"
)
DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_ID = (
    "dprime-one-shot-model-review-adapter:not-configured:v1"
)

ADAPTER_STATUS_CONFIGURED = "configured"
ADAPTER_STATUS_NOT_CONFIGURED = "not configured"
ADAPTER_STATUS_REJECTED = "rejected"

ADAPTER_KIND_REAL_ONE_SHOT = "real_one_shot"
RETRY_POLICY_FORBIDDEN = "forbidden"
FALLBACK_POLICY_FORBIDDEN = "forbidden"
TIMEOUT_POLICY_FAIL_CLOSED = "fail_closed"

OneShotModelReviewTransport = Callable[..., Any]

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
        "real_provider_called",
        "real_model_called",
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


class DPrimeOneShotModelReviewAdapterError(ValueError):
    """Raised when D-prime adapter material cannot be coerced."""


@dataclass(frozen=True, slots=True)
class DPrimeOneShotModelReviewAdapter:
    """Product-owned one-shot model-review adapter contract."""

    adapter_ref: str
    provider_model_approval_ref: str
    provider_boundary_ref: str
    transport: OneShotModelReviewTransport = field(repr=False, compare=False)
    phase: str = DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_PHASE
    adapter_kind: str = ADAPTER_KIND_REAL_ONE_SHOT
    one_shot_adapter_proven: bool = True
    max_provider_attempts: int = 1
    retry_policy: str = RETRY_POLICY_FORBIDDEN
    fallback_policy: str = FALLBACK_POLICY_FORBIDDEN
    provider_switching_allowed: bool = False
    timeout_policy: str = TIMEOUT_POLICY_FAIL_CLOSED
    call_count: int = 0
    raw_prompt_retained: bool = False
    raw_model_response_retained: bool = False
    provider_payload_retained: bool = False
    real_provider_call_performed: bool = False
    real_model_call_performed: bool = False
    provider_model_selection_detail_present: bool = False
    candidate_helper: str | None = None
    closed_surface_flags: Mapping[str, bool] = field(
        default_factory=lambda: default_closed_surface_flags()
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> DPrimeOneShotModelReviewAdapter:
        safe = _required_mapping(value, "DPrimeOneShotModelReviewAdapter")
        transport = safe.get("transport")
        if not callable(transport):
            raise DPrimeOneShotModelReviewAdapterError(
                "D-prime one-shot model-review adapter requires invoke_once transport"
            )
        return cls(
            adapter_ref=_clean_text(safe.get("adapter_ref"), limit=320) or "",
            provider_model_approval_ref=_clean_text(
                safe.get("provider_model_approval_ref"),
                limit=320,
            )
            or "",
            provider_boundary_ref=_clean_text(
                safe.get("provider_boundary_ref"),
                limit=320,
            )
            or "",
            transport=transport,
            phase=(
                _clean_text(safe.get("phase"), limit=160)
                or DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_PHASE
            ),
            adapter_kind=(
                _clean_text(safe.get("adapter_kind"), limit=80)
                or ADAPTER_KIND_REAL_ONE_SHOT
            ),
            one_shot_adapter_proven=safe.get("one_shot_adapter_proven") is True,
            max_provider_attempts=_bounded_int(
                safe.get("max_provider_attempts"),
                default=1,
            ),
            retry_policy=(
                _clean_text(safe.get("retry_policy"), limit=80)
                or RETRY_POLICY_FORBIDDEN
            ),
            fallback_policy=(
                _clean_text(safe.get("fallback_policy"), limit=80)
                or FALLBACK_POLICY_FORBIDDEN
            ),
            provider_switching_allowed=_flag(
                safe,
                "provider_switching_allowed",
                "provider_switching",
                "provider_switching_enabled",
            ),
            timeout_policy=(
                _clean_text(safe.get("timeout_policy"), limit=80)
                or TIMEOUT_POLICY_FAIL_CLOSED
            ),
            call_count=_bounded_int(safe.get("call_count"), default=0),
            raw_prompt_retained=_flag(
                safe,
                "raw_prompt_retained",
                "raw_prompt_retention",
            ),
            raw_model_response_retained=_flag(
                safe,
                "raw_model_response_retained",
                "raw_model_response_retention",
            ),
            provider_payload_retained=_flag(
                safe,
                "provider_payload_retained",
                "provider_payload_retention",
                "raw_provider_payload_retained",
            ),
            real_provider_call_performed=_flag(
                safe,
                "real_provider_call_performed",
                "real_provider_called",
            ),
            real_model_call_performed=_flag(
                safe,
                "real_model_call_performed",
                "real_model_called",
            ),
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
            candidate_helper=_clean_text(
                safe.get("candidate_helper")
                or safe.get("helper")
                or safe.get("callable_ref")
                or safe.get("transport_ref"),
                limit=260,
            ),
            closed_surface_flags=_closed_surface_flags_from_mapping(
                safe.get("closed_surface_flags")
            ),
        )

    def to_ref(self) -> dict[str, Any]:
        return {
            "schema_version": DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_SCHEMA_VERSION,
            "adapter_ref": self.adapter_ref,
            "phase": self.phase,
            "adapter_kind": self.adapter_kind,
            "one_shot_adapter_proven": self.one_shot_adapter_proven,
            "provider_model_approval_ref": self.provider_model_approval_ref,
            "provider_boundary_ref": self.provider_boundary_ref,
            "max_provider_attempts": self.max_provider_attempts,
            "retry_policy": self.retry_policy,
            "fallback_policy": self.fallback_policy,
            "provider_switching_allowed": self.provider_switching_allowed,
            "timeout_policy": self.timeout_policy,
            "call_count": self.call_count,
            "raw_prompt_retained": self.raw_prompt_retained,
            "raw_model_response_retained": self.raw_model_response_retained,
            "provider_payload_retained": self.provider_payload_retained,
            "real_provider_call_performed": self.real_provider_call_performed,
            "real_model_call_performed": self.real_model_call_performed,
            "provider_model_selection_detail_present": (
                self.provider_model_selection_detail_present
            ),
            "candidate_helper": self.candidate_helper,
            "closed_surface_flags": dict(self.closed_surface_flags),
        }

    def invoke_once(
        self,
        *,
        prompt: str,
        input_packet: Mapping[str, Any],
        system_prompt: str,
        license_ref: Mapping[str, Any],
        one_shot_provider_boundary_ref: Mapping[str, Any],
        one_shot_model_review_adapter_ref: Mapping[str, Any],
    ) -> DPrimeOneShotModelReviewAdapterInvocationResult:
        """Invoke the configured transport at most once and never retry."""

        return invoke_dprime_one_shot_model_review_adapter(
            self,
            prompt=prompt,
            input_packet=input_packet,
            system_prompt=system_prompt,
            license_ref=license_ref,
            one_shot_provider_boundary_ref=one_shot_provider_boundary_ref,
            one_shot_model_review_adapter_ref=one_shot_model_review_adapter_ref,
        )


@dataclass(frozen=True, slots=True)
class DPrimeOneShotModelReviewAdapterValidation:
    """Validation/status projection for product and tests."""

    status: str
    adapter_ref: Mapping[str, Any]
    blockers: Sequence[str] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)

    @property
    def configured(self) -> bool:
        return self.status == ADAPTER_STATUS_CONFIGURED

    def to_status_ref(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "adapter_ref": dict(self.adapter_ref),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "adapter_contract_valid_is_not_semantic_support": True,
            "real_provider_call_performed": False,
            "real_model_call_performed": False,
        }


@dataclass(frozen=True, slots=True)
class DPrimeOneShotModelReviewAdapterInvocationResult:
    """Transient invocation result; raw output must be parsed then discarded."""

    ok: bool
    call_count: int
    transient_model_review_output: Any | None = None
    timed_out: bool = False
    error_type: str | None = None


def build_default_dprime_one_shot_model_review_adapter_ref() -> dict[str, Any]:
    """Return the default not-configured adapter ref."""

    return {
        "schema_version": DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_SCHEMA_VERSION,
        "adapter_ref": DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_ID,
        "phase": DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_PHASE,
        "adapter_kind": ADAPTER_KIND_REAL_ONE_SHOT,
        "one_shot_adapter_proven": False,
        "provider_model_approval_ref": None,
        "provider_boundary_ref": None,
        "max_provider_attempts": 0,
        "retry_policy": RETRY_POLICY_FORBIDDEN,
        "fallback_policy": FALLBACK_POLICY_FORBIDDEN,
        "provider_switching_allowed": False,
        "timeout_policy": TIMEOUT_POLICY_FAIL_CLOSED,
        "call_count": 0,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "provider_payload_retained": False,
        "real_provider_call_performed": False,
        "real_model_call_performed": False,
        "provider_model_selection_detail_present": False,
        "candidate_helper": None,
        "closed_surface_flags": default_closed_surface_flags(),
    }


def default_closed_surface_flags() -> dict[str, bool]:
    """Return required false flags for the D-prime adapter contract."""

    return {key: False for key in sorted(_CLOSED_SURFACE_FALSE_FLAGS)}


def validate_dprime_one_shot_model_review_adapter(
    adapter: Mapping[str, Any] | DPrimeOneShotModelReviewAdapter | None = None,
) -> DPrimeOneShotModelReviewAdapterValidation:
    """Validate whether an adapter is configured for one-shot invocation."""

    if adapter is None:
        return DPrimeOneShotModelReviewAdapterValidation(
            status=ADAPTER_STATUS_NOT_CONFIGURED,
            adapter_ref=build_default_dprime_one_shot_model_review_adapter_ref(),
            blockers=(
                "D-prime one-shot model-review adapter is not configured",
            ),
        )
    try:
        adapter_obj = _coerce_adapter(adapter)
    except DPrimeOneShotModelReviewAdapterError as exc:
        return DPrimeOneShotModelReviewAdapterValidation(
            status=ADAPTER_STATUS_REJECTED,
            adapter_ref=build_default_dprime_one_shot_model_review_adapter_ref(),
            blockers=(str(exc),),
        )
    blockers = _safety_blockers(adapter_obj)
    if blockers:
        return DPrimeOneShotModelReviewAdapterValidation(
            status=ADAPTER_STATUS_REJECTED,
            adapter_ref=adapter_obj.to_ref(),
            blockers=tuple(blockers),
        )
    return DPrimeOneShotModelReviewAdapterValidation(
        status=ADAPTER_STATUS_CONFIGURED,
        adapter_ref=adapter_obj.to_ref(),
    )


def invoke_dprime_one_shot_model_review_adapter(
    adapter: Mapping[str, Any] | DPrimeOneShotModelReviewAdapter,
    *,
    prompt: str,
    input_packet: Mapping[str, Any],
    system_prompt: str,
    license_ref: Mapping[str, Any],
    one_shot_provider_boundary_ref: Mapping[str, Any],
    one_shot_model_review_adapter_ref: Mapping[str, Any],
) -> DPrimeOneShotModelReviewAdapterInvocationResult:
    """Invoke one configured adapter transport exactly once."""

    adapter_obj = _coerce_adapter(adapter)
    validation = validate_dprime_one_shot_model_review_adapter(adapter_obj)
    if not validation.configured:
        return DPrimeOneShotModelReviewAdapterInvocationResult(
            ok=False,
            call_count=0,
            error_type="DPrimeOneShotModelReviewAdapterInvalid",
        )
    call_count = _consume_adapter_call(0, limit=1)
    try:
        output = adapter_obj.transport(
            prompt,
            input_packet=dict(input_packet),
            system_prompt=system_prompt,
            license_ref=dict(license_ref),
            one_shot_provider_boundary_ref=dict(one_shot_provider_boundary_ref),
            one_shot_model_review_adapter_ref=dict(
                one_shot_model_review_adapter_ref
            ),
        )
    except TimeoutError:
        return DPrimeOneShotModelReviewAdapterInvocationResult(
            ok=False,
            call_count=call_count,
            timed_out=True,
            error_type="TimeoutError",
        )
    except Exception as exc:
        return DPrimeOneShotModelReviewAdapterInvocationResult(
            ok=False,
            call_count=call_count,
            error_type=_safe_adapter_error_type(exc),
        )
    return DPrimeOneShotModelReviewAdapterInvocationResult(
        ok=True,
        call_count=call_count,
        transient_model_review_output=output,
    )


def _coerce_adapter(
    value: Mapping[str, Any] | DPrimeOneShotModelReviewAdapter,
) -> DPrimeOneShotModelReviewAdapter:
    if isinstance(value, DPrimeOneShotModelReviewAdapter):
        return value
    if isinstance(value, Mapping):
        return DPrimeOneShotModelReviewAdapter.from_mapping(value)
    raise DPrimeOneShotModelReviewAdapterError(
        "D-prime one-shot model-review adapter must be a product-owned adapter"
    )


def _safety_blockers(adapter: DPrimeOneShotModelReviewAdapter) -> list[str]:
    blockers: list[str] = []
    ref = adapter.to_ref()
    raw_private = sorted(_collect_keys(ref) & _RAW_PRIVATE_KEYS)
    if raw_private:
        blockers.append(
            "D-prime model-review adapter includes raw/private fields: "
            + ", ".join(raw_private)
        )
    dangerous = sorted(_dangerous_true_claims(ref))
    if dangerous:
        blockers.append(
            "D-prime model-review adapter attempts forbidden true flags: "
            + ", ".join(dangerous)
        )
    if not adapter.adapter_ref:
        blockers.append("D-prime model-review adapter_ref is required")
    if adapter.phase != DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_PHASE:
        blockers.append("D-prime model-review adapter phase is unsupported")
    if _normalize_key(adapter.adapter_kind) != ADAPTER_KIND_REAL_ONE_SHOT:
        blockers.append("D-prime model-review adapter kind must be real_one_shot")
    if adapter.one_shot_adapter_proven is not True:
        blockers.append("D-prime model-review adapter must be proven one-shot")
    if not adapter.provider_model_approval_ref:
        blockers.append(
            "D-prime model-review adapter requires provider/model approval ref"
        )
    if not adapter.provider_boundary_ref:
        blockers.append("D-prime model-review adapter requires provider boundary ref")
    if adapter.max_provider_attempts != 1:
        blockers.append("D-prime model-review adapter requires max attempts == 1")
    if adapter.retry_policy != RETRY_POLICY_FORBIDDEN:
        blockers.append("D-prime model-review adapter retries are forbidden")
    if adapter.fallback_policy != FALLBACK_POLICY_FORBIDDEN:
        blockers.append("D-prime model-review adapter fallback is forbidden")
    if adapter.provider_switching_allowed:
        blockers.append("D-prime model-review adapter cannot allow provider switching")
    if adapter.timeout_policy != TIMEOUT_POLICY_FAIL_CLOSED:
        blockers.append("D-prime model-review adapter timeout policy must fail closed")
    if adapter.call_count != 0:
        blockers.append("D-prime model-review adapter must start with call_count 0")
    if adapter.raw_prompt_retained:
        blockers.append("D-prime model-review adapter cannot retain raw prompts")
    if adapter.raw_model_response_retained:
        blockers.append(
            "D-prime model-review adapter cannot retain raw model responses"
        )
    if adapter.provider_payload_retained:
        blockers.append("D-prime model-review adapter cannot retain provider payloads")
    if adapter.real_provider_call_performed:
        blockers.append(
            "D-prime model-review adapter cannot predeclare real provider calls"
        )
    if adapter.real_model_call_performed:
        blockers.append(
            "D-prime model-review adapter cannot predeclare real model calls"
        )
    if adapter.provider_model_selection_detail_present:
        blockers.append(
            "D-prime model-review adapter cannot select provider/model in this phase"
        )
    if not callable(adapter.transport):
        blockers.append("D-prime model-review adapter requires invoke_once transport")
    helper = _normalize_token(adapter.candidate_helper)
    if helper in _BROAD_HELPER_CANDIDATES:
        blockers.append(
            "broad model helper candidate is unsafe without a dedicated "
            "one-shot adapter"
        )
    closed_flags = _closed_surface_flags_from_mapping(adapter.closed_surface_flags)
    for key in sorted(_CLOSED_SURFACE_FALSE_FLAGS):
        if closed_flags.get(key) is not False:
            blockers.append(f"closed_surface_flags must keep {key} false")
    return blockers


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
        raise DPrimeOneShotModelReviewAdapterError(f"{label} must be a mapping")
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


def _consume_adapter_call(call_count: int, *, limit: int) -> int:
    if call_count >= limit:
        raise DPrimeOneShotModelReviewAdapterError(
            "D-prime model-review adapter one-call cap exceeded"
        )
    return call_count + 1


def _safe_adapter_error_type(exc: Exception) -> str:
    blocker = getattr(exc, "dprime_blocker", None) or getattr(exc, "blocker", None)
    text = _clean_text(blocker, limit=120)
    if text and text.startswith("BLOCKED_") and all(
        char.isupper() or char.isdigit() or char == "_" for char in text
    ):
        return text
    return type(exc).__name__


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
    "ADAPTER_KIND_REAL_ONE_SHOT",
    "ADAPTER_STATUS_CONFIGURED",
    "ADAPTER_STATUS_NOT_CONFIGURED",
    "ADAPTER_STATUS_REJECTED",
    "DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_ID",
    "DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_PHASE",
    "DPRIME_ONE_SHOT_MODEL_REVIEW_ADAPTER_SCHEMA_VERSION",
    "DPrimeOneShotModelReviewAdapter",
    "DPrimeOneShotModelReviewAdapterError",
    "DPrimeOneShotModelReviewAdapterInvocationResult",
    "DPrimeOneShotModelReviewAdapterValidation",
    "FALLBACK_POLICY_FORBIDDEN",
    "OneShotModelReviewTransport",
    "RETRY_POLICY_FORBIDDEN",
    "TIMEOUT_POLICY_FAIL_CLOSED",
    "build_default_dprime_one_shot_model_review_adapter_ref",
    "default_closed_surface_flags",
    "invoke_dprime_one_shot_model_review_adapter",
    "validate_dprime_one_shot_model_review_adapter",
]
