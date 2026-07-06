"""Strict D-prime execution for the product smart model route.

This module represents the existing product smart model route under a
D-prime-specific ``strict_one_shot`` execution policy. D-prime evidence-relative
assessment is Analyst-like work, so it consumes the product smart role settings:
``RunConfig.smart_provider`` / ``RunConfig.smart_model`` and their CLI/UI
equivalents. For this approved phase, that smart route must resolve to OpenAI
``gpt-5.4``. The transport avoids the broad product LLM helper because that
path can retry and fall back; instead it assumes the product config boundary
has initialized credential posture, then uses OpenAI SDK/environment lookup
with SDK retries disabled so the approved smart route can be consumed by
``DPrimeOneShotModelReviewAdapter`` without provider switching or raw retention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from core.dprime_one_shot_model_review_adapter import (
    DPrimeOneShotModelReviewAdapter,
)
from core.dprime_one_shot_model_review_adapter import (
    default_closed_surface_flags as default_adapter_closed_surface_flags,
)
from core.dprime_one_shot_provider_boundary import (
    DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE,
    PROVIDER_MODEL_SELECTION_APPROVAL_REF_PRESENT,
)
from core.dprime_one_shot_provider_boundary import (
    default_closed_surface_flags as default_provider_closed_surface_flags,
)
from core.dprime_support_proposal_schema import (
    BLOCKED_APPROVED_MODEL_UNAVAILABLE,
    BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE,
    BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE,
    BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT,
)

DPRIME_PRODUCT_SMART_TRANSPORT_PHASE = (
    "DPRIME-APPROVED-PROVIDER-ONE-SHOT-TRANSPORT-01"
)
DPRIME_PRODUCT_SMART_TRANSPORT_SCHEMA_VERSION = (
    "dprime_product_smart_one_shot_transport_v1"
)
DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF = (
    "human-approved:dprime-real-model-review-run-01:"
    "product-smart-model-route"
)
DPRIME_MODEL_TASK = "dprime_model_review_assessment"
PRODUCT_MODEL_ROLE_SMART = "smart"
PRODUCT_ROUTE_KIND_SMART_MODEL = "smart_model_route"
EXECUTION_POLICY_STRICT_ONE_SHOT = "strict_one_shot"
APPROVED_PROVIDER = "OpenAI"
APPROVED_MODEL = "gpt-5.4"
PRODUCT_ROUTE_SETTINGS_SURFACE = (
    "core.run_config.RunConfig.smart_provider/smart_model; "
    "CLI --smart-provider/--smart-model; "
    "Streamlit Smart Provider/Smart Model controls"
)
PRODUCT_CONFIG_INITIALIZATION_BOUNDARY = (
    "core.product_model_route_config.initialize_product_model_route_config"
)
DPRIME_PRODUCT_SMART_TRANSPORT_REF = (
    "product-smart-model-route:"
    "dprime-strict-one-shot:openai:gpt-5.4:v1"
)
DPRIME_PRODUCT_SMART_ADAPTER_REF = (
    "dprime-one-shot-model-review-adapter:"
    "product-smart:openai:gpt-5.4:v1"
)
PRIVATE_LOOKING_VALUE_REDACTION = "private_looking_value_not_retained"

OpenAIClientFactory = Callable[[], Any]

_FORBIDDEN_RUNTIME_KWARGS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "fallback",
        "fallback_policy",
        "model",
        "provider",
        "provider_payload",
        "raw_model_response",
        "raw_prompt",
        "retry",
        "retry_policy",
        "token",
    }
)


class DPrimeProductSmartOneShotError(RuntimeError):
    """Raised with a safe blocker code and no raw provider material."""

    def __init__(self, blocker: str) -> None:
        super().__init__(blocker)
        self.blocker = blocker
        self.dprime_blocker = blocker


def product_smart_model_route_ref(
    *,
    smart_provider: str = APPROVED_PROVIDER,
    smart_model: str = APPROVED_MODEL,
) -> dict[str, Any]:
    """Return the approved product smart-route metadata for this D-prime phase."""

    return {
        "schema_version": DPRIME_PRODUCT_SMART_TRANSPORT_SCHEMA_VERSION,
        "phase": DPRIME_PRODUCT_SMART_TRANSPORT_PHASE,
        "model_task": DPRIME_MODEL_TASK,
        "product_model_role": PRODUCT_MODEL_ROLE_SMART,
        "product_route_kind": PRODUCT_ROUTE_KIND_SMART_MODEL,
        "product_route_settings_surface": PRODUCT_ROUTE_SETTINGS_SURFACE,
        "configured_smart_provider": _safe_route_value(smart_provider),
        "configured_smart_model": _safe_route_value(smart_model),
        "default_provider": APPROVED_PROVIDER,
        "default_model": APPROVED_MODEL,
        "approved_provider": APPROVED_PROVIDER,
        "approved_model": APPROVED_MODEL,
        "provider_model_approval_ref": (
            DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF
        ),
        "product_config_initialization_boundary": (
            PRODUCT_CONFIG_INITIALIZATION_BOUNDARY
        ),
        "execution_policy": EXECUTION_POLICY_STRICT_ONE_SHOT,
        "credential_source": (
            "product model-route config initialization boundary, then OpenAI "
            "SDK/environment lookup"
        ),
        "max_provider_attempts": 1,
        "retry_policy": "forbidden",
        "fallback_policy": "forbidden",
        "provider_switching_allowed": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "provider_payload_retained": False,
        "search_calls": 0,
        "retrieval_calls": 0,
        "fetch_read_calls": 0,
    }


def build_openai_sdk_env_client(
    openai_client_cls: Callable[..., Any] | None = None,
) -> Any:
    """Build an OpenAI SDK client using only normal environment lookup."""

    if openai_client_cls is None:
        from openai import OpenAI as openai_client_cls

    return openai_client_cls(max_retries=0, timeout=60.0)


@dataclass(slots=True)
class DPrimeProductSmartOneShotTransport:
    """Callable product smart route transport with a one-call fuse."""

    openai_client_factory: OpenAIClientFactory = field(
        default=build_openai_sdk_env_client,
        repr=False,
        compare=False,
    )
    provider_model_approval_ref: str = (
        DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF
    )
    product_model_role: str = PRODUCT_MODEL_ROLE_SMART
    product_route_kind: str = PRODUCT_ROUTE_KIND_SMART_MODEL
    model_task: str = DPRIME_MODEL_TASK
    execution_policy: str = EXECUTION_POLICY_STRICT_ONE_SHOT
    smart_provider: str = APPROVED_PROVIDER
    smart_model: str = APPROVED_MODEL
    transport_ref: str = DPRIME_PRODUCT_SMART_TRANSPORT_REF
    _call_count: int = field(default=0, init=False, repr=False)

    def __call__(self, prompt: str, *, system_prompt: str, **kwargs: Any) -> str:
        """Perform exactly one OpenAI call for the approved product route."""

        self._validate_call(prompt=prompt, system_prompt=system_prompt, kwargs=kwargs)
        self._consume_call()
        try:
            client = self.openai_client_factory()
        except Exception as exc:
            raise _classify_client_construction_error(exc) from None
        try:
            response = client.chat.completions.create(
                model=self.smart_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                stream=False,
            )
        except Exception as exc:
            raise _classify_provider_error(exc) from None
        text = _response_text(response)
        if not text:
            raise DPrimeProductSmartOneShotError(
                BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE
            )
        return text

    def to_ref(self) -> dict[str, Any]:
        ref = product_smart_model_route_ref(
            smart_provider=self.smart_provider,
            smart_model=self.smart_model,
        )
        ref.update(
            {
                "model_task": self.model_task,
                "product_model_role": self.product_model_role,
                "product_route_kind": self.product_route_kind,
                "provider_model_approval_ref": self.provider_model_approval_ref,
                "execution_policy": self.execution_policy,
                "transport_ref": self.transport_ref,
            }
        )
        return ref

    def _consume_call(self) -> None:
        if self._call_count != 0:
            raise DPrimeProductSmartOneShotError(
                BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE
            )
        self._call_count += 1

    def _validate_call(
        self,
        *,
        prompt: str,
        system_prompt: str,
        kwargs: Mapping[str, Any],
    ) -> None:
        if not prompt or not system_prompt:
            raise DPrimeProductSmartOneShotError(
                BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE
            )
        forbidden = sorted(
            _FORBIDDEN_RUNTIME_KWARGS & {_normalize_key(k) for k in kwargs}
        )
        if forbidden:
            raise DPrimeProductSmartOneShotError(
                BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE
            )
        if not _approved_product_smart_route(
            smart_provider=self.smart_provider,
            smart_model=self.smart_model,
        ):
            raise DPrimeProductSmartOneShotError(
                BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT
            )
        expected_ref = {
            **product_smart_model_route_ref(
                smart_provider=APPROVED_PROVIDER,
                smart_model=APPROVED_MODEL,
            ),
            "transport_ref": DPRIME_PRODUCT_SMART_TRANSPORT_REF,
        }
        if self.to_ref() != expected_ref:
            raise DPrimeProductSmartOneShotError(
                BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT
            )


def build_dprime_product_smart_one_shot_transport(
    *,
    openai_client_factory: OpenAIClientFactory | None = None,
    smart_provider: str = APPROVED_PROVIDER,
    smart_model: str = APPROVED_MODEL,
) -> DPrimeProductSmartOneShotTransport:
    """Return the approved product smart route strict transport."""

    return DPrimeProductSmartOneShotTransport(
        openai_client_factory=openai_client_factory or build_openai_sdk_env_client,
        smart_provider=smart_provider,
        smart_model=smart_model,
    )


def build_dprime_product_smart_model_review_adapter(
    *,
    provider_boundary_ref: str,
    openai_client_factory: OpenAIClientFactory | None = None,
    smart_provider: str = APPROVED_PROVIDER,
    smart_model: str = APPROVED_MODEL,
) -> DPrimeOneShotModelReviewAdapter:
    """Wrap the approved product route in the D-prime adapter contract."""

    transport = build_dprime_product_smart_one_shot_transport(
        openai_client_factory=openai_client_factory,
        smart_provider=smart_provider,
        smart_model=smart_model,
    )
    return DPrimeOneShotModelReviewAdapter(
        adapter_ref=DPRIME_PRODUCT_SMART_ADAPTER_REF,
        provider_model_approval_ref=(
            DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF
        ),
        provider_boundary_ref=provider_boundary_ref,
        transport=transport,
        candidate_helper=(
            "core.dprime_product_smart_one_shot_transport."
            "DPrimeProductSmartOneShotTransport"
        ),
        closed_surface_flags=default_adapter_closed_surface_flags(),
    )


def build_dprime_product_smart_model_review_provider_boundary() -> dict[str, Any]:
    """Return the approved one-shot boundary for the product smart route."""

    return {
        "boundary_id": "dprime-one-shot-provider-boundary:product-smart-route:v1",
        "phase": DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE,
        "enabled": True,
        "default_disabled": False,
        "test_only": False,
        "provider_model_selection_status": (
            PROVIDER_MODEL_SELECTION_APPROVAL_REF_PRESENT
        ),
        "provider_model_approval_ref": DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF,
        "max_provider_attempts": 1,
        "retry_policy": "forbidden",
        "fallback_policy": "forbidden",
        "timeout_policy": "fail_closed",
        "raw_prompt_retention": False,
        "raw_model_response_retention": False,
        "provider_payload_retention": False,
        "real_call_authorized": True,
        "call_count": 0,
        "provider_switching_allowed": False,
        "one_shot_adapter_proven": True,
        "one_shot_adapter_ref": DPRIME_PRODUCT_SMART_ADAPTER_REF,
        "closed_surface_flags": default_provider_closed_surface_flags(),
    }


def build_dprime_product_smart_model_review_license() -> dict[str, Any]:
    """Return the one-call D-prime license for the product smart route."""

    return {
        "license_id": DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF,
        "enabled": True,
        "test_only": False,
        "callable_kind": "real_one_shot",
        "max_model_review_calls": 1,
        "retry_policy": "forbidden",
        "timeout_policy": "fail_closed",
        "one_shot_adapter_ref": DPRIME_PRODUCT_SMART_ADAPTER_REF,
    }


def _classify_client_construction_error(
    exc: Exception,
) -> DPrimeProductSmartOneShotError:
    if _looks_like_missing_credential(exc):
        return DPrimeProductSmartOneShotError(
            BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE
        )
    return DPrimeProductSmartOneShotError(
        BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE
    )


def _classify_provider_error(exc: Exception) -> DPrimeProductSmartOneShotError:
    if _looks_like_missing_credential(exc):
        return DPrimeProductSmartOneShotError(
            BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE
        )
    if _looks_like_model_unavailable(exc):
        return DPrimeProductSmartOneShotError(
            BLOCKED_APPROVED_MODEL_UNAVAILABLE
        )
    return DPrimeProductSmartOneShotError(
        BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE
    )


def _looks_like_missing_credential(exc: Exception) -> bool:
    text = _exception_text(exc)
    return "api_key" in text or "openai_api_key" in text


def _looks_like_model_unavailable(exc: Exception) -> bool:
    code = _normalize_key(getattr(exc, "code", ""))
    status_code = getattr(exc, "status_code", None)
    if code in {"model_not_found", "model_not_available", "invalid_model"}:
        return True
    if status_code in {400, 404}:
        text = _exception_text(exc)
        return "model" in text and any(
            marker in text
            for marker in (
                "does not exist",
                "invalid",
                "not available",
                "not found",
                "unsupported",
            )
        )
    return False


def _exception_text(exc: Exception) -> str:
    return str(exc).casefold()


def _response_text(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if content:
            return str(content)
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)
    return ""


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _clean_route_value(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _safe_route_value(value: Any) -> str:
    text = _clean_route_value(value)
    if not text:
        return ""
    return PRIVATE_LOOKING_VALUE_REDACTION if _private_value_markers(text) else text


def _private_value_markers(value: str) -> set[str]:
    lowered = value.casefold()
    markers = {
        "api_key",
        "authorization:",
        "bearer ",
        "private_sentinel",
        "provider_payload",
        "raw_prompt",
        "raw_provider",
        "secret",
        "sk-",
        "token",
    }
    return {marker for marker in markers if marker in lowered}


def _approved_product_smart_route(*, smart_provider: str, smart_model: str) -> bool:
    return (
        _normalize_key(smart_provider) == _normalize_key(APPROVED_PROVIDER)
        and _clean_route_value(smart_model) == APPROVED_MODEL
    )


__all__ = [
    "APPROVED_MODEL",
    "APPROVED_PROVIDER",
    "BLOCKED_APPROVED_MODEL_UNAVAILABLE",
    "BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE",
    "BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE",
    "BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT",
    "DPRIME_MODEL_TASK",
    "DPRIME_PRODUCT_SMART_ADAPTER_REF",
    "DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF",
    "DPRIME_PRODUCT_SMART_TRANSPORT_PHASE",
    "DPRIME_PRODUCT_SMART_TRANSPORT_REF",
    "DPrimeProductSmartOneShotError",
    "DPrimeProductSmartOneShotTransport",
    "EXECUTION_POLICY_STRICT_ONE_SHOT",
    "PRODUCT_MODEL_ROLE_SMART",
    "PRODUCT_CONFIG_INITIALIZATION_BOUNDARY",
    "PRODUCT_ROUTE_KIND_SMART_MODEL",
    "PRIVATE_LOOKING_VALUE_REDACTION",
    "build_dprime_product_smart_model_review_adapter",
    "build_dprime_product_smart_model_review_license",
    "build_dprime_product_smart_model_review_provider_boundary",
    "build_dprime_product_smart_one_shot_transport",
    "build_openai_sdk_env_client",
    "product_smart_model_route_ref",
]
