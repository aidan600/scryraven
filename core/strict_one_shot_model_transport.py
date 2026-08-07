"""Provider-neutral strict one-shot SmartModel transport.

Each invocation makes at most one underlying provider request with SDK retries
disabled and no endpoint, provider, or model fallback. Returns only safe
accounting facts plus transient output text for main-thread reduction.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Callable, ClassVar, Mapping

from core.cap_enforcement import (
    DEFAULT_MODEL_TIMEOUT_SECONDS,
    MODEL_OUTPUT_TOKEN_LIMIT,
    AttemptLifecycle,
    AttemptReservation,
    ExternalAttemptSpec,
    ExternalCallFamily,
    RunCapExceeded,
    RunCapPolicy,
    TokenUsage,
    model_usage_bound,
)
from core.cost_accounting import estimate_tokens, extract_usage_tokens
from core.strict_accounted_model_route import (
    ENDPOINT_KIND_CHAT_COMPLETIONS_COMPATIBLE,
    ENDPOINT_KIND_OPENAI_RESPONSES,
    FALLBACK_POLICY_FORBIDDEN,
    LOCAL_STUDIO_KEY_PLACEHOLDER,
    OPENROUTER_BASE_URL,
    PRIVATE_LOOKING_VALUE_REDACTION,
    PROVIDER_LOCAL,
    PROVIDER_OPENAI,
    PROVIDER_OPENROUTER,
    PROVIDER_UNSUPPORTED,
    RETRY_POLICY_FORBIDDEN,
    TIMEOUT_POLICY_FAIL_CLOSED,
    normalize_fast_model_provider,
)

# Repository-owned Phase 5A chat-completions sampling posture. Callers must not
# supply or override temperature; OpenAI Responses requests omit it entirely.
STRICT_ONE_SHOT_CHAT_TEMPERATURE = 0.3

SUPPORTED_STRICT_ONE_SHOT_PROVIDERS = frozenset({PROVIDER_OPENAI, PROVIDER_OPENROUTER, PROVIDER_LOCAL})

BLOCKED_STRICT_ONE_SHOT_PROVIDER_UNSUPPORTED = "BLOCKED_STRICT_ONE_SHOT_PROVIDER_UNSUPPORTED"
BLOCKED_STRICT_ONE_SHOT_MODEL_UNCONFIGURED = "BLOCKED_STRICT_ONE_SHOT_MODEL_UNCONFIGURED"
BLOCKED_STRICT_ONE_SHOT_CREDENTIAL_UNAVAILABLE = "BLOCKED_STRICT_ONE_SHOT_CREDENTIAL_UNAVAILABLE"
BLOCKED_STRICT_ONE_SHOT_LOCAL_URL_UNAVAILABLE = "BLOCKED_STRICT_ONE_SHOT_LOCAL_URL_UNAVAILABLE"
BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED = "BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED"
BLOCKED_STRICT_ONE_SHOT_OUTPUT_EMPTY = "BLOCKED_STRICT_ONE_SHOT_OUTPUT_EMPTY"
BLOCKED_STRICT_ONE_SHOT_UNSAFE_REQUEST = "BLOCKED_STRICT_ONE_SHOT_UNSAFE_REQUEST"

CredentialLookup = Callable[[str], str | None]
OpenAICompatibleClientFactory = Callable[..., Any]

_FORBIDDEN_RUNTIME_KWARGS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "base_url",
        "configured_endpoint_kind",
        "endpoint",
        "endpoint_kind",
        "endpoint_switching_allowed",
        "endpoint_used",
        "fallback",
        "fallback_policy",
        "local_url",
        "provider_payload",
        "raw_model_response",
        "raw_prompt",
        "retry",
        "retry_policy",
        "temperature",
        "token",
    }
)

_ZERO_USAGE_FACTS: dict[str, Any] = {
    "provider_response_received": False,
    "input_tokens": 0,
    "output_tokens": 0,
    "usage_observed": False,
    "usage_estimated": False,
}


@dataclass(frozen=True, slots=True)
class StrictOneShotModelTransportResult:
    """Bounded transport result; ``output_text`` is transient reducer input only."""

    return_code: int
    output_text: str = field(default="", repr=False, compare=False)
    failure_kind: str | None = None
    detail: str | None = None
    canonical_provider: str = PROVIDER_UNSUPPORTED
    configured_model: str = ""
    provider_request_attempt_count: int = 0
    provider_request_succeeded: bool = False
    provider_request_failed: bool = False
    provider_response_received: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    usage_observed: bool = False
    usage_estimated: bool = False
    configured_endpoint_kind: str = ""
    strict_one_shot: bool = True
    retry_policy: str = RETRY_POLICY_FORBIDDEN
    fallback_policy: str = FALLBACK_POLICY_FORBIDDEN
    timeout_policy: str = TIMEOUT_POLICY_FAIL_CLOSED
    provider_switching_allowed: bool = False
    endpoint_switching_allowed: bool = False
    raw_prompt_retained: bool = False
    raw_model_response_retained: bool = False
    raw_provider_payload_retained: bool = False
    credential_values_retained: bool = False


@dataclass(slots=True)
class StrictOneShotModelTransport:
    """Callable SmartModel transport with at most one provider request."""

    __scryraven_cap_aware__: ClassVar[bool] = True
    canonical_provider: str
    model: str
    local_url: str | None = field(default=None, repr=False, compare=False)
    openrouter_api_key: str | None = field(default=None, repr=False, compare=False)
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
    timeout_seconds: float = DEFAULT_MODEL_TIMEOUT_SECONDS
    cap_policy: RunCapPolicy | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __call__(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> StrictOneShotModelTransportResult:
        provider = normalize_canonical_model_provider(self.canonical_provider)
        model = _clean_route_value(self.model)
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
                failure_kind=BLOCKED_STRICT_ONE_SHOT_UNSAFE_REQUEST,
                detail=unsafe,
            )
        if provider not in SUPPORTED_STRICT_ONE_SHOT_PROVIDERS:
            return self._failed_result(
                base,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_PROVIDER_UNSUPPORTED,
                detail="Configured SmartModel provider is not supported by the strict one-shot transport.",
            )
        if not model:
            return self._failed_result(
                base,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_MODEL_UNCONFIGURED,
                detail="Configured SmartModel name is empty.",
            )

        request_kwargs = dict(kwargs)
        if self.cap_policy is not None and self.cap_policy.bounded:
            request_kwargs["max_tokens"] = min(
                _positive_int(request_kwargs.get("max_tokens")) or MODEL_OUTPUT_TOKEN_LIMIT,
                MODEL_OUTPUT_TOKEN_LIMIT,
            )
        reservation = self._reserve_attempt(
            provider=provider,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            logical_call_id=str(request_kwargs.get("logical_call_id") or ""),
        )
        client_result = self._client_for_provider(
            provider=provider,
            base=base,
            timeout_seconds=(reservation.timeout_seconds if reservation is not None else self.timeout_seconds),
        )
        if isinstance(client_result, StrictOneShotModelTransportResult):
            if reservation is not None:
                reservation.cancel_pre_dispatch("client_unavailable")
            return client_result
        client = client_result
        try:
            if reservation is not None:
                reservation.mark_dispatched()
            response = self._create_provider_response_once(
                client,
                prompt=prompt,
                system_prompt=system_prompt,
                provider=provider,
                model=model,
                kwargs=request_kwargs,
            )
        except RunCapExceeded:
            if reservation is not None and reservation.lifecycle is AttemptLifecycle.DISPATCHED:
                reservation.settle_conservative("dispatch_outcome_ambiguous")
            raise
        except Exception as exc:  # noqa: BLE001 - fail closed with safe facts only.
            if reservation is not None:
                reservation.settle_conservative("dispatch_outcome_ambiguous")
            return self._failed_result(
                base,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED,
                detail=(f"Strict one-shot provider request failed closed: {type(exc).__name__}."),
                attempted=1,
                provider_request_failed=True,
            )
        if reservation is not None:
            reservation.settle_observed(_ledger_usage_from_response(response))
        output_text = _response_text(response)
        usage_facts = _bounded_usage_facts_from_response(
            response,
            prompt=prompt,
            system_prompt=system_prompt,
            output_text=output_text,
        )
        if not output_text:
            return self._failed_result(
                base,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_OUTPUT_EMPTY,
                detail="Strict one-shot provider request returned no text.",
                attempted=1,
                provider_request_failed=True,
                usage_facts=usage_facts,
            )
        return StrictOneShotModelTransportResult(
            return_code=0,
            output_text=output_text,
            canonical_provider=provider,
            configured_model=model,
            provider_request_attempt_count=1,
            provider_request_succeeded=True,
            provider_request_failed=False,
            configured_endpoint_kind=_endpoint_kind_for_provider(provider),
            strict_one_shot=True,
            retry_policy=RETRY_POLICY_FORBIDDEN,
            fallback_policy=FALLBACK_POLICY_FORBIDDEN,
            timeout_policy=TIMEOUT_POLICY_FAIL_CLOSED,
            provider_switching_allowed=False,
            endpoint_switching_allowed=False,
            raw_prompt_retained=False,
            raw_model_response_retained=False,
            raw_provider_payload_retained=False,
            credential_values_retained=False,
            **usage_facts,
        )

    def _base_result(self, *, provider: str, model: str) -> dict[str, Any]:
        return {
            "canonical_provider": provider if provider in SUPPORTED_STRICT_ONE_SHOT_PROVIDERS else PROVIDER_UNSUPPORTED,
            "configured_model": _safe_route_value(model),
            "configured_endpoint_kind": _endpoint_kind_for_provider(provider),
            "strict_one_shot": True,
            "retry_policy": RETRY_POLICY_FORBIDDEN,
            "fallback_policy": FALLBACK_POLICY_FORBIDDEN,
            "timeout_policy": TIMEOUT_POLICY_FAIL_CLOSED,
            "provider_switching_allowed": False,
            "endpoint_switching_allowed": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
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
            return "Strict one-shot transport requires transient prompt and system text."
        forbidden = sorted(_FORBIDDEN_RUNTIME_KWARGS & {_normalize_key(k) for k in kwargs})
        if forbidden:
            return "Strict one-shot transport rejected unsafe runtime arguments."
        requested_provider = kwargs.get("provider")
        if requested_provider is not None and str(requested_provider).strip():
            requested = normalize_canonical_model_provider(requested_provider)
            if requested != provider:
                return "Strict one-shot transport rejected provider switching."
        requested_model = _clean_route_value(kwargs.get("model"))
        if requested_model and requested_model not in {
            model,
            PRIVATE_LOOKING_VALUE_REDACTION,
        }:
            return "Strict one-shot transport rejected model switching."
        return None

    def _client_for_provider(
        self,
        *,
        provider: str,
        base: Mapping[str, Any],
        timeout_seconds: float,
    ) -> Any | StrictOneShotModelTransportResult:
        try:
            if provider == PROVIDER_OPENAI:
                key = self.credential_lookup("OPENAI_API_KEY")
                if not key:
                    return self._failed_result(
                        base,
                        failure_kind=BLOCKED_STRICT_ONE_SHOT_CREDENTIAL_UNAVAILABLE,
                        detail="Configured OpenAI SmartModel credential is unavailable.",
                    )
                return self.client_factory(
                    api_key=key,
                    max_retries=0,
                    timeout=timeout_seconds,
                )
            if provider == PROVIDER_OPENROUTER:
                key = _clean_route_value(self.openrouter_api_key) or self.credential_lookup("OPENROUTER_API_KEY")
                if not key:
                    return self._failed_result(
                        base,
                        failure_kind=BLOCKED_STRICT_ONE_SHOT_CREDENTIAL_UNAVAILABLE,
                        detail="Configured OpenRouter SmartModel credential is unavailable.",
                    )
                return self.client_factory(
                    api_key=key,
                    base_url=OPENROUTER_BASE_URL,
                    max_retries=0,
                    timeout=timeout_seconds,
                )
            local_url = _clean_route_value(self.local_url)
            if not local_url:
                return self._failed_result(
                    base,
                    failure_kind=BLOCKED_STRICT_ONE_SHOT_LOCAL_URL_UNAVAILABLE,
                    detail="Configured local SmartModel URL is unavailable.",
                )
            return self.client_factory(
                api_key=LOCAL_STUDIO_KEY_PLACEHOLDER,
                base_url=local_url,
                max_retries=0,
                timeout=timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - fail closed without provider detail.
            return self._failed_result(
                base,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED,
                detail=(f"Strict one-shot client construction failed closed: {type(exc).__name__}."),
            )

    def _reserve_attempt(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        system_prompt: str,
        logical_call_id: str,
    ) -> AttemptReservation | None:
        if self.cap_policy is None or not self.cap_policy.bounded:
            return None
        self.cap_policy.note_product_stage("multicomponent_model")
        pricing = self.cap_policy.resolve_route_pricing(
            ExternalCallFamily.MODEL,
            provider,
            model,
        )
        identity_source = logical_call_id or self.cap_policy.new_logical_call_id("strict-model")
        identity_digest = sha256(identity_source.encode("utf-8")).hexdigest()[:20]
        return self.cap_policy.reserve_attempt(
            ExternalAttemptSpec(
                family=ExternalCallFamily.MODEL,
                provider=provider,
                route=model,
                operation=("responses" if provider == PROVIDER_OPENAI else "chat"),
                logical_call_id=f"strict-model:{identity_digest}",
                max_usage=model_usage_bound(prompt, system_prompt),
                pricing=pricing,
                requested_timeout_seconds=self.timeout_seconds,
            )
        )

    def _create_provider_response_once(
        self,
        client: Any,
        *,
        prompt: str,
        system_prompt: str,
        provider: str,
        model: str,
        kwargs: Mapping[str, Any],
    ) -> Any:
        if provider == PROVIDER_OPENAI:
            return client.responses.create(
                **self._responses_create_kwargs(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    kwargs=kwargs,
                )
            )
        return client.chat.completions.create(
            **self._chat_create_kwargs(
                prompt=prompt,
                system_prompt=system_prompt,
                provider=provider,
                model=model,
                kwargs=kwargs,
            )
        )

    def _responses_create_kwargs(
        self,
        *,
        prompt: str,
        system_prompt: str,
        model: str,
        kwargs: Mapping[str, Any],
    ) -> dict[str, Any]:
        create_kwargs: dict[str, Any] = {
            "model": model,
            "instructions": system_prompt,
            "input": prompt,
            "stream": False,
            "store": False,
        }
        if kwargs.get("require_json") is True:
            create_kwargs["text"] = {"format": {"type": "json_object"}}
        max_tokens = _positive_int(kwargs.get("max_tokens"))
        if max_tokens is not None:
            create_kwargs["max_output_tokens"] = max_tokens
        effort = _normalize_key(kwargs.get("effort"))
        if (
            kwargs.get("use_reasoning") is True
            and effort in {"none", "minimal", "low", "medium", "high", "xhigh"}
            and _is_reasoning_model(model)
        ):
            create_kwargs["reasoning"] = {"effort": effort}
        return create_kwargs

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
            "temperature": STRICT_ONE_SHOT_CHAT_TEMPERATURE,
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
        failure_kind: str,
        detail: str,
        attempted: int = 0,
        provider_request_failed: bool = False,
        usage_facts: Mapping[str, Any] | None = None,
    ) -> StrictOneShotModelTransportResult:
        bounded_usage = dict(_ZERO_USAGE_FACTS)
        if usage_facts is not None:
            bounded_usage.update(_validate_usage_facts(usage_facts))
        return StrictOneShotModelTransportResult(
            return_code=2,
            failure_kind=failure_kind,
            detail=detail,
            canonical_provider=str(base.get("canonical_provider") or PROVIDER_UNSUPPORTED),
            configured_model=str(base.get("configured_model") or ""),
            provider_request_attempt_count=attempted,
            provider_request_succeeded=False,
            provider_request_failed=provider_request_failed or attempted > 0,
            configured_endpoint_kind=str(base.get("configured_endpoint_kind") or ""),
            strict_one_shot=True,
            retry_policy=RETRY_POLICY_FORBIDDEN,
            fallback_policy=FALLBACK_POLICY_FORBIDDEN,
            timeout_policy=TIMEOUT_POLICY_FAIL_CLOSED,
            provider_switching_allowed=False,
            endpoint_switching_allowed=False,
            raw_prompt_retained=False,
            raw_model_response_retained=False,
            raw_provider_payload_retained=False,
            credential_values_retained=False,
            **bounded_usage,
        )


def normalize_canonical_model_provider(value: Any) -> str:
    """Return the repository-owned safe canonical SmartModel provider identity."""

    return normalize_fast_model_provider(value)


def is_supported_strict_one_shot_provider(value: Any) -> bool:
    return normalize_canonical_model_provider(value) in SUPPORTED_STRICT_ONE_SHOT_PROVIDERS


def build_strict_one_shot_smart_model_transport(
    *,
    smart_provider: Any,
    smart_model: str,
    local_url: str | None = None,
    openrouter_api_key: str | None = None,
    credential_lookup: CredentialLookup | None = None,
    client_factory: OpenAICompatibleClientFactory | None = None,
    timeout_seconds: float = DEFAULT_MODEL_TIMEOUT_SECONDS,
    cap_policy: RunCapPolicy | None = None,
) -> StrictOneShotModelTransport:
    """Build the product-owned strict one-shot SmartModel transport."""

    return StrictOneShotModelTransport(
        canonical_provider=normalize_canonical_model_provider(smart_provider),
        model=_clean_route_value(smart_model),
        local_url=local_url,
        openrouter_api_key=openrouter_api_key,
        credential_lookup=credential_lookup or os.getenv,
        client_factory=client_factory or _build_openai_compatible_client,
        timeout_seconds=timeout_seconds,
        cap_policy=cap_policy,
    )


def wrap_text_callable_as_strict_one_shot_transport(
    text_callable: Callable[..., str],
    *,
    canonical_provider: str,
    model: str,
) -> Callable[..., StrictOneShotModelTransportResult]:
    """Test/offline adapter: wrap a text-returning fake into a strict result."""

    provider = normalize_canonical_model_provider(canonical_provider)
    configured_model = _clean_route_value(model)

    def _transport(
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> StrictOneShotModelTransportResult:
        if provider not in SUPPORTED_STRICT_ONE_SHOT_PROVIDERS:
            return StrictOneShotModelTransportResult(
                return_code=2,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_PROVIDER_UNSUPPORTED,
                detail="Configured SmartModel provider is not supported by the strict one-shot transport.",
                canonical_provider=PROVIDER_UNSUPPORTED,
                configured_model=configured_model,
                provider_request_attempt_count=0,
                provider_request_succeeded=False,
                provider_request_failed=False,
            )
        try:
            output_text = text_callable(prompt, system_prompt, **kwargs)
        except Exception as exc:  # noqa: BLE001 - bounded failure facts only.
            return StrictOneShotModelTransportResult(
                return_code=2,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED,
                detail=f"Wrapped strict one-shot fake failed closed: {type(exc).__name__}.",
                canonical_provider=provider,
                configured_model=configured_model,
                provider_request_attempt_count=1,
                provider_request_succeeded=False,
                provider_request_failed=True,
                configured_endpoint_kind=_endpoint_kind_for_provider(provider),
            )
        text = str(output_text or "")
        usage_facts = _bounded_usage_facts_from_transient_texts(
            prompt=prompt,
            system_prompt=system_prompt,
            output_text=text,
        )
        if not text:
            return StrictOneShotModelTransportResult(
                return_code=2,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_OUTPUT_EMPTY,
                detail="Wrapped strict one-shot fake returned no text.",
                canonical_provider=provider,
                configured_model=configured_model,
                provider_request_attempt_count=1,
                provider_request_succeeded=False,
                provider_request_failed=True,
                configured_endpoint_kind=_endpoint_kind_for_provider(provider),
                **usage_facts,
            )
        return StrictOneShotModelTransportResult(
            return_code=0,
            output_text=text,
            canonical_provider=provider,
            configured_model=configured_model,
            provider_request_attempt_count=1,
            provider_request_succeeded=True,
            provider_request_failed=False,
            configured_endpoint_kind=_endpoint_kind_for_provider(provider),
            **usage_facts,
        )

    return _transport


def _build_openai_compatible_client(**kwargs: Any) -> Any:
    from openai import OpenAI

    return OpenAI(**kwargs)


def _endpoint_kind_for_provider(provider: str) -> str:
    if provider == PROVIDER_OPENAI:
        return ENDPOINT_KIND_OPENAI_RESPONSES
    if provider in {PROVIDER_OPENROUTER, PROVIDER_LOCAL}:
        return ENDPOINT_KIND_CHAT_COMPLETIONS_COMPATIBLE
    return ""


def _bounded_usage_facts_from_response(
    response: Any,
    *,
    prompt: str,
    system_prompt: str,
    output_text: str,
) -> dict[str, Any]:
    observed_input, observed_output = extract_usage_tokens(response)
    usage_observed = observed_input is not None or observed_output is not None
    usage_estimated = False
    if observed_input is None:
        input_tokens = estimate_tokens(prompt) + estimate_tokens(system_prompt)
        usage_estimated = True
    else:
        input_tokens = max(0, int(observed_input))
    if observed_output is None:
        output_tokens = estimate_tokens(output_text)
        usage_estimated = True
    else:
        output_tokens = max(0, int(observed_output))
    return _validate_usage_facts(
        {
            "provider_response_received": True,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "usage_observed": usage_observed,
            "usage_estimated": usage_estimated,
        }
    )


def _ledger_usage_from_response(response: Any) -> TokenUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    input_tokens = getattr(usage, "prompt_tokens", None)
    if input_tokens is None:
        input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "completion_tokens", None)
    if output_tokens is None:
        output_tokens = getattr(usage, "output_tokens", None)
    if input_tokens is None and output_tokens is None:
        return None
    input_details = getattr(usage, "prompt_tokens_details", None)
    if input_details is None:
        input_details = getattr(usage, "input_tokens_details", None)
    output_details = getattr(usage, "completion_tokens_details", None)
    if output_details is None:
        output_details = getattr(usage, "output_tokens_details", None)
    return TokenUsage(
        input_tokens=int(input_tokens or 0),
        cached_input_tokens=int(getattr(input_details, "cached_tokens", 0) or 0),
        output_tokens=int(output_tokens or 0),
        reasoning_tokens=int(getattr(output_details, "reasoning_tokens", 0) or 0),
    )


def _bounded_usage_facts_from_transient_texts(
    *,
    prompt: str,
    system_prompt: str,
    output_text: str,
) -> dict[str, Any]:
    return _validate_usage_facts(
        {
            "provider_response_received": True,
            "input_tokens": estimate_tokens(prompt) + estimate_tokens(system_prompt),
            "output_tokens": estimate_tokens(output_text),
            "usage_observed": False,
            "usage_estimated": True,
        }
    )


def _validate_usage_facts(values: Mapping[str, Any]) -> dict[str, Any]:
    provider_response_received = bool(values.get("provider_response_received"))
    if not provider_response_received:
        return dict(_ZERO_USAGE_FACTS)
    input_tokens = max(0, int(values.get("input_tokens") or 0))
    output_tokens = max(0, int(values.get("output_tokens") or 0))
    return {
        "provider_response_received": True,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "usage_observed": bool(values.get("usage_observed")),
        "usage_estimated": bool(values.get("usage_estimated")),
    }


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


def _safe_route_value(value: Any) -> str:
    text = _clean_route_value(value)
    if not text:
        return ""
    lowered = text.casefold()
    markers = (
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
    )
    if any(marker in lowered for marker in markers):
        return PRIVATE_LOOKING_VALUE_REDACTION
    return text


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


__all__ = [
    "BLOCKED_STRICT_ONE_SHOT_CREDENTIAL_UNAVAILABLE",
    "BLOCKED_STRICT_ONE_SHOT_LOCAL_URL_UNAVAILABLE",
    "BLOCKED_STRICT_ONE_SHOT_MODEL_UNCONFIGURED",
    "BLOCKED_STRICT_ONE_SHOT_OUTPUT_EMPTY",
    "BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED",
    "BLOCKED_STRICT_ONE_SHOT_PROVIDER_UNSUPPORTED",
    "BLOCKED_STRICT_ONE_SHOT_UNSAFE_REQUEST",
    "PROVIDER_LOCAL",
    "PROVIDER_OPENAI",
    "PROVIDER_OPENROUTER",
    "PROVIDER_UNSUPPORTED",
    "STRICT_ONE_SHOT_CHAT_TEMPERATURE",
    "SUPPORTED_STRICT_ONE_SHOT_PROVIDERS",
    "StrictOneShotModelTransport",
    "StrictOneShotModelTransportResult",
    "build_strict_one_shot_smart_model_transport",
    "is_supported_strict_one_shot_provider",
    "normalize_canonical_model_provider",
    "wrap_text_callable_as_strict_one_shot_transport",
]
