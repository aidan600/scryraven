"""Strict accounted FastModel planning route.

This module owns the live FastModel provider boundary for model-assisted
single-relation planning. It avoids the broad product LLM helper because that
path can retry or fall back; each route invocation makes at most one chat
completion request to the configured FastModel provider and returns only safe
accounting diagnostics plus transient output text for the reducer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from core.model_assisted_single_relation_planning import (
    MODEL_ASSISTED_PLANNING_MODEL_TASK,
    MODEL_ASSISTED_PLANNING_PRODUCT_MODEL_ROLE,
)

STRICT_ACCOUNTED_FASTMODEL_ROUTE_SCHEMA_VERSION = (
    "strict_accounted_fastmodel_planning_route_01_v1"
)
STRICT_ACCOUNTED_FASTMODEL_ROUTE_PHASE = (
    "STRICT-ACCOUNTED-FASTMODEL-PLANNING-ROUTE-01"
)
PRODUCT_ROUTE_KIND_STRICT_FASTMODEL = "strict_accounted_fast_model_route"
PRODUCT_ROUTE_SETTINGS_SURFACE = (
    "core.run_config.RunConfig.fast_provider/fast_model/local_url; "
    "CLI --fast-provider/--fast-model/--local-url; "
    "SCRYRAVEN_FAST_PROVIDER/PROPLEX_FAST_PROVIDER; "
    "SCRYRAVEN_FAST_MODEL/PROPLEX_FAST_MODEL; "
    "SCRYRAVEN_LOCAL_URL/PROPLEX_LOCAL_URL"
)
PRODUCT_CONFIG_INITIALIZATION_BOUNDARY = (
    "core.product_model_route_config.initialize_product_model_route_config"
)

PROVIDER_OPENAI = "OpenAI"
PROVIDER_OPENROUTER = "OpenRouter"
PROVIDER_LOCAL = "Local (LM Studio)"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
LOCAL_STUDIO_KEY_PLACEHOLDER = "lm-studio"

BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_UNSUPPORTED = (
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_UNSUPPORTED"
)
BLOCKED_STRICT_ACCOUNTED_FASTMODEL_MODEL_UNCONFIGURED = (
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_MODEL_UNCONFIGURED"
)
BLOCKED_STRICT_ACCOUNTED_FASTMODEL_CREDENTIAL_UNAVAILABLE = (
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_CREDENTIAL_UNAVAILABLE"
)
BLOCKED_STRICT_ACCOUNTED_FASTMODEL_LOCAL_URL_UNAVAILABLE = (
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_LOCAL_URL_UNAVAILABLE"
)
BLOCKED_STRICT_ACCOUNTED_FASTMODEL_UNSAFE_REQUEST = (
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_UNSAFE_REQUEST"
)
BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_CALL_FAILED = (
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_CALL_FAILED"
)
BLOCKED_STRICT_ACCOUNTED_FASTMODEL_MODEL_UNAVAILABLE = (
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_MODEL_UNAVAILABLE"
)
BLOCKED_STRICT_ACCOUNTED_FASTMODEL_OUTPUT_EMPTY = (
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_OUTPUT_EMPTY"
)

RETRY_POLICY_FORBIDDEN = "forbidden"
FALLBACK_POLICY_FORBIDDEN = "forbidden"
TIMEOUT_POLICY_FAIL_CLOSED = "fail_closed"

CredentialLookup = Callable[[str], str | None]
OpenAICompatibleClientFactory = Callable[..., Any]

_FORBIDDEN_RUNTIME_KWARGS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "fallback",
        "fallback_policy",
        "provider_payload",
        "raw_model_response",
        "raw_prompt",
        "retry",
        "retry_policy",
        "token",
    }
)


@dataclass(frozen=True, slots=True)
class StrictAccountedModelRouteResult:
    """Safe route result; ``output_text`` is transient reducer input only."""

    return_code: int
    output_text: str = field(default="", repr=False, compare=False)
    blocker: str | None = None
    detail: str | None = None
    model_calls_attempted: int = 0
    model_calls_completed: int = 0
    configured_provider: str = ""
    configured_model: str = ""
    provider_used: str = ""
    model_used: str = ""
    configured_local_url_present: bool = False
    configured_local_url_posture: str = "not_configured"
    credential_present: bool = False
    strict_one_shot: bool = True
    retry_policy: str = RETRY_POLICY_FORBIDDEN
    fallback_policy: str = FALLBACK_POLICY_FORBIDDEN
    timeout_policy: str = TIMEOUT_POLICY_FAIL_CLOSED
    provider_switching_allowed: bool = False
    raw_prompt_retained: bool = False
    raw_model_response_retained: bool = False
    raw_provider_payload_retained: bool = False
    provider_payload_retained: bool = False
    credential_values_retained: bool = False

    def to_safe_diagnostic(self) -> dict[str, Any]:
        return {
            "return_code": self.return_code,
            "blocker": self.blocker,
            "detail": self.detail,
            "model_calls_attempted": self.model_calls_attempted,
            "model_calls_completed": self.model_calls_completed,
            "configured_provider": self.configured_provider,
            "configured_model": self.configured_model,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "configured_local_url_present": self.configured_local_url_present,
            "configured_local_url_posture": self.configured_local_url_posture,
            "credential_present": self.credential_present,
            "strict_one_shot": self.strict_one_shot,
            "retry_policy": self.retry_policy,
            "fallback_policy": self.fallback_policy,
            "timeout_policy": self.timeout_policy,
            "provider_switching_allowed": self.provider_switching_allowed,
            "raw_prompt_retained": self.raw_prompt_retained,
            "raw_model_response_retained": self.raw_model_response_retained,
            "raw_provider_payload_retained": self.raw_provider_payload_retained,
            "provider_payload_retained": self.provider_payload_retained,
            "credential_values_retained": self.credential_values_retained,
        }


@dataclass(slots=True)
class StrictAccountedFastModelRoute:
    """Callable FastModel route with one provider request per invocation."""

    fast_provider: str
    fast_model: str
    local_url: str | None = field(default=None, repr=False)
    credential_lookup: CredentialLookup = field(
        default=os.getenv,
        repr=False,
        compare=False,
    )
    client_factory: OpenAICompatibleClientFactory = field(
        default=lambda **kwargs: _build_openai_compatible_client(**kwargs),
        repr=False,
        compare=False,
    )
    timeout_seconds: float = 60.0

    def __call__(self, prompt: str, system_prompt: str, **kwargs: Any) -> StrictAccountedModelRouteResult:
        provider = normalize_fast_model_provider(self.fast_provider)
        model = _clean_route_value(self.fast_model)
        base = self._base_result(provider=provider, model=model)
        unsafe = self._unsafe_request_reason(
            prompt=prompt,
            system_prompt=system_prompt,
            kwargs=kwargs,
            provider=provider,
            model=model,
        )
        if unsafe:
            return self._failed_result(
                base,
                blocker=BLOCKED_STRICT_ACCOUNTED_FASTMODEL_UNSAFE_REQUEST,
                detail=unsafe,
            )
        if provider not in {PROVIDER_OPENAI, PROVIDER_OPENROUTER, PROVIDER_LOCAL}:
            return self._failed_result(
                base,
                blocker=BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_UNSUPPORTED,
                detail="Configured FastModel provider is not supported by the strict route.",
            )
        if not model:
            return self._failed_result(
                base,
                blocker=BLOCKED_STRICT_ACCOUNTED_FASTMODEL_MODEL_UNCONFIGURED,
                detail="Configured FastModel name is empty.",
            )

        client_result = self._client_for_provider(provider=provider, base=base)
        if isinstance(client_result, StrictAccountedModelRouteResult):
            return client_result
        client, credential_present = client_result
        create_kwargs = self._chat_create_kwargs(
            prompt=prompt,
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            kwargs=kwargs,
        )
        try:
            response = client.chat.completions.create(**create_kwargs)
        except Exception as exc:  # noqa: BLE001 - fail closed with safe blocker only.
            return self._failed_result(
                base,
                blocker=_provider_error_blocker(exc),
                detail=(
                    "Strict FastModel provider request failed closed: "
                    f"{type(exc).__name__}."
                ),
                attempted=1,
                completed=0,
                credential_present=credential_present,
            )
        output_text = _response_text(response)
        if not output_text:
            return self._failed_result(
                base,
                blocker=BLOCKED_STRICT_ACCOUNTED_FASTMODEL_OUTPUT_EMPTY,
                detail="Strict FastModel provider request returned no text.",
                attempted=1,
                completed=1,
                credential_present=credential_present,
            )
        return StrictAccountedModelRouteResult(
            **{
                **base,
                "return_code": 0,
                "output_text": output_text,
                "model_calls_attempted": 1,
                "model_calls_completed": 1,
                "credential_present": credential_present,
            }
        )

    def to_ref(self) -> dict[str, Any]:
        provider = normalize_fast_model_provider(self.fast_provider)
        model = _clean_route_value(self.fast_model)
        local_url = _clean_route_value(self.local_url)
        return {
            "schema_version": STRICT_ACCOUNTED_FASTMODEL_ROUTE_SCHEMA_VERSION,
            "phase": STRICT_ACCOUNTED_FASTMODEL_ROUTE_PHASE,
            "model_task": MODEL_ASSISTED_PLANNING_MODEL_TASK,
            "product_model_role": MODEL_ASSISTED_PLANNING_PRODUCT_MODEL_ROLE,
            "product_route_kind": PRODUCT_ROUTE_KIND_STRICT_FASTMODEL,
            "product_route_settings_surface": PRODUCT_ROUTE_SETTINGS_SURFACE,
            "product_config_initialization_boundary": (
                PRODUCT_CONFIG_INITIALIZATION_BOUNDARY
            ),
            "configured_fast_provider": provider,
            "configured_fast_model": model,
            "configured_local_url_present": bool(local_url),
            "configured_local_url_posture": _local_url_posture(local_url),
            "execution_policy": "strict_accounted_one_provider_request",
            "max_model_calls": 1,
            "max_provider_attempts": 1,
            "retry_policy": RETRY_POLICY_FORBIDDEN,
            "fallback_policy": FALLBACK_POLICY_FORBIDDEN,
            "timeout_policy": TIMEOUT_POLICY_FAIL_CLOSED,
            "provider_switching_allowed": False,
            "strict_one_shot": True,
            "call_count": 0,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
            "provider_payload_retained": False,
            "raw_search_response_retained": False,
            "credential_values_retained": False,
        }

    def _base_result(self, *, provider: str, model: str) -> dict[str, Any]:
        local_url = _clean_route_value(self.local_url)
        return {
            "configured_provider": provider,
            "configured_model": model,
            "provider_used": provider if provider in {
                PROVIDER_OPENAI,
                PROVIDER_OPENROUTER,
                PROVIDER_LOCAL,
            } else "",
            "model_used": model,
            "configured_local_url_present": bool(local_url),
            "configured_local_url_posture": _local_url_posture(local_url),
            "strict_one_shot": True,
            "retry_policy": RETRY_POLICY_FORBIDDEN,
            "fallback_policy": FALLBACK_POLICY_FORBIDDEN,
            "timeout_policy": TIMEOUT_POLICY_FAIL_CLOSED,
            "provider_switching_allowed": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
            "provider_payload_retained": False,
            "credential_values_retained": False,
        }

    def _unsafe_request_reason(
        self,
        *,
        prompt: str,
        system_prompt: str,
        kwargs: Mapping[str, Any],
        provider: str,
        model: str,
    ) -> str | None:
        if not prompt or not system_prompt:
            return "Strict FastModel route requires transient prompt and system text."
        forbidden = sorted(_FORBIDDEN_RUNTIME_KWARGS & {_normalize_key(k) for k in kwargs})
        if forbidden:
            return "Strict FastModel route rejected unsafe runtime arguments."
        requested_provider = kwargs.get("provider")
        if requested_provider and normalize_fast_model_provider(requested_provider) != provider:
            return "Strict FastModel route rejected provider switching."
        requested_model = _clean_route_value(kwargs.get("model"))
        if requested_model and requested_model != model:
            return "Strict FastModel route rejected model switching."
        return None

    def _client_for_provider(
        self,
        *,
        provider: str,
        base: Mapping[str, Any],
    ) -> tuple[Any, bool] | StrictAccountedModelRouteResult:
        try:
            if provider == PROVIDER_OPENAI:
                key = self.credential_lookup("OPENAI_API_KEY")
                if not key:
                    return self._failed_result(
                        base,
                        blocker=BLOCKED_STRICT_ACCOUNTED_FASTMODEL_CREDENTIAL_UNAVAILABLE,
                        detail="Configured OpenAI FastModel credential is unavailable.",
                    )
                return (
                    self.client_factory(
                        api_key=key,
                        max_retries=0,
                        timeout=self.timeout_seconds,
                    ),
                    True,
                )
            if provider == PROVIDER_OPENROUTER:
                key = self.credential_lookup("OPENROUTER_API_KEY")
                if not key:
                    return self._failed_result(
                        base,
                        blocker=BLOCKED_STRICT_ACCOUNTED_FASTMODEL_CREDENTIAL_UNAVAILABLE,
                        detail="Configured OpenRouter FastModel credential is unavailable.",
                    )
                return (
                    self.client_factory(
                        api_key=key,
                        base_url=OPENROUTER_BASE_URL,
                        max_retries=0,
                        timeout=self.timeout_seconds,
                    ),
                    True,
                )
            local_url = _clean_route_value(self.local_url)
            if not local_url:
                return self._failed_result(
                    base,
                    blocker=BLOCKED_STRICT_ACCOUNTED_FASTMODEL_LOCAL_URL_UNAVAILABLE,
                    detail="Configured local FastModel URL is unavailable.",
                )
            return (
                self.client_factory(
                    api_key=LOCAL_STUDIO_KEY_PLACEHOLDER,
                    base_url=local_url,
                    max_retries=0,
                    timeout=self.timeout_seconds,
                ),
                True,
            )
        except Exception as exc:  # noqa: BLE001 - fail closed without provider detail.
            return self._failed_result(
                base,
                blocker=BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_CALL_FAILED,
                detail=(
                    "Strict FastModel client construction failed closed: "
                    f"{type(exc).__name__}."
                ),
            )

    def _chat_create_kwargs(
        self,
        *,
        prompt: str,
        system_prompt: str,
        provider: str,
        model: str,
        kwargs: Mapping[str, Any],
    ) -> dict[str, Any]:
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        if kwargs.get("require_json") is True:
            create_kwargs["response_format"] = {"type": "json_object"}
        max_tokens = _positive_int(kwargs.get("max_tokens"))
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens
        effort = _normalize_key(kwargs.get("effort"))
        if (
            provider == PROVIDER_OPENAI
            and kwargs.get("use_reasoning") is True
            and effort in {"low", "medium", "high"}
            and _is_reasoning_model(model)
        ):
            create_kwargs["reasoning_effort"] = effort
        if provider == PROVIDER_OPENROUTER:
            create_kwargs["extra_headers"] = {
                "HTTP-Referer": "https://localhost",
                "X-Title": "ScryRaven",
            }
        return create_kwargs

    def _failed_result(
        self,
        base: Mapping[str, Any],
        *,
        blocker: str,
        detail: str,
        attempted: int = 0,
        completed: int = 0,
        credential_present: bool = False,
    ) -> StrictAccountedModelRouteResult:
        return StrictAccountedModelRouteResult(
            **{
                **dict(base),
                "return_code": 2,
                "blocker": blocker,
                "detail": detail,
                "model_calls_attempted": attempted,
                "model_calls_completed": completed,
                "credential_present": credential_present,
            }
        )


def build_strict_accounted_fast_model_planning_route(
    *,
    fast_provider: str,
    fast_model: str,
    local_url: str | None = None,
    credential_lookup: CredentialLookup | None = None,
    client_factory: OpenAICompatibleClientFactory | None = None,
    timeout_seconds: float = 60.0,
) -> StrictAccountedFastModelRoute:
    """Build the product-owned strict FastModel planning route."""

    return StrictAccountedFastModelRoute(
        fast_provider=fast_provider,
        fast_model=fast_model,
        local_url=local_url,
        credential_lookup=credential_lookup or os.getenv,
        client_factory=client_factory or _build_openai_compatible_client,
        timeout_seconds=timeout_seconds,
    )


def normalize_fast_model_provider(value: Any) -> str:
    text = _clean_route_value(value)
    key = _normalize_key(text)
    if key == "openai":
        return PROVIDER_OPENAI
    if key in {"openrouter", "open_router"}:
        return PROVIDER_OPENROUTER
    if key in {"local", "lm_studio", "local_lm_studio", "local_(lm_studio)"}:
        return PROVIDER_LOCAL
    return text


def _build_openai_compatible_client(**kwargs: Any) -> Any:
    from openai import OpenAI

    return OpenAI(**kwargs)


def _provider_error_blocker(exc: Exception) -> str:
    if _looks_like_model_unavailable(exc):
        return BLOCKED_STRICT_ACCOUNTED_FASTMODEL_MODEL_UNAVAILABLE
    return BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_CALL_FAILED


def _looks_like_model_unavailable(exc: Exception) -> bool:
    code = _normalize_key(getattr(exc, "code", ""))
    status_code = getattr(exc, "status_code", None)
    if code in {"model_not_found", "model_not_available", "invalid_model"}:
        return True
    if status_code in {400, 404}:
        text = str(exc).casefold()
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
    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))
    return "\n".join(parts).strip()


def _local_url_posture(local_url: str | None) -> str:
    if not local_url:
        return "not_configured"
    parsed = urlparse(local_url)
    host = (parsed.hostname or "").casefold()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".localhost"):
        return "local_configured_not_retained"
    if parsed.scheme in {"http", "https"} and host:
        return "remote_configured_not_retained"
    return "configured_unvalidated_not_retained"


def _is_reasoning_model(model: str) -> bool:
    return _normalize_key(model) in {
        "gpt_5.4",
        "gpt_5.4_mini",
        "o1",
        "o1_mini",
        "o1_preview",
        "o3_mini",
    }


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _clean_route_value(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


__all__ = [
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_CREDENTIAL_UNAVAILABLE",
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_LOCAL_URL_UNAVAILABLE",
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_MODEL_UNAVAILABLE",
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_MODEL_UNCONFIGURED",
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_OUTPUT_EMPTY",
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_CALL_FAILED",
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_UNSUPPORTED",
    "BLOCKED_STRICT_ACCOUNTED_FASTMODEL_UNSAFE_REQUEST",
    "FALLBACK_POLICY_FORBIDDEN",
    "OPENROUTER_BASE_URL",
    "PRODUCT_ROUTE_KIND_STRICT_FASTMODEL",
    "PROVIDER_LOCAL",
    "PROVIDER_OPENAI",
    "PROVIDER_OPENROUTER",
    "RETRY_POLICY_FORBIDDEN",
    "STRICT_ACCOUNTED_FASTMODEL_ROUTE_PHASE",
    "STRICT_ACCOUNTED_FASTMODEL_ROUTE_SCHEMA_VERSION",
    "StrictAccountedFastModelRoute",
    "StrictAccountedModelRouteResult",
    "TIMEOUT_POLICY_FAIL_CLOSED",
    "build_strict_accounted_fast_model_planning_route",
    "normalize_fast_model_provider",
]
