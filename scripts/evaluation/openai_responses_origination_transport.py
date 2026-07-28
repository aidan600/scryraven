"""Deprecated direct OpenAI Responses fallback for AnalystOS origination.

No active preparation or operator path selects this adapter.  It remains
unlicensed by default as a last-resort private-shell compatibility fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Mapping

from scripts.evaluation.model_cost_policy import (
    GPT54_MODEL_ID,
    MODEL_COST_POLICIES,
    SUPPORTED_PROVIDER,
    ModelCostPolicy,
    route_priced_cost_decimal,
)
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationConfigurationError,
    EvaluationTransportError,
    EvaluationTransportResponse,
    LiveAuthorization,
)
from scripts.provider_execution_contract import digest_text

TRANSPORT_FACTORY_SPEC = (
    "scripts.evaluation.openai_responses_origination_transport:"
    "create_openai_responses_transport"
)
REQUEST_TIMEOUT_SECONDS = 600.0
SDK_MAX_RETRIES = 0

TIMEOUT_ERROR_MESSAGE = (
    "OpenAI Responses request timed out; billing is unknown and explicit "
    "maintainer reauthorization is required."
)
TRANSPORT_ERROR_MESSAGE = "OpenAI Responses request failed closed."
USAGE_ERROR_MESSAGE = "OpenAI Responses request omitted exact usage accounting."
OUTPUT_ERROR_MESSAGE = "OpenAI Responses request returned no output text."

OpenAIConstructor = Callable[..., Any]


OpenAIResponsesModelPolicy = ModelCostPolicy
OPENAI_MODEL_POLICIES: Mapping[str, OpenAIResponsesModelPolicy] = {
    GPT54_MODEL_ID: MODEL_COST_POLICIES[(SUPPORTED_PROVIDER, GPT54_MODEL_ID)]
}


def resolve_openai_model_policy(
    model: str,
    *,
    model_policies: Mapping[str, OpenAIResponsesModelPolicy] | None = None,
) -> OpenAIResponsesModelPolicy:
    """Resolve and validate one exact authorized OpenAI Responses policy."""

    policies = OPENAI_MODEL_POLICIES if model_policies is None else model_policies
    policy = policies.get(model)
    if policy is None:
        raise EvaluationConfigurationError(
            "no OpenAI Responses policy exists for the exact authorized model"
        )
    if (
        policy.provider != SUPPORTED_PROVIDER
        or policy.model != model
        or policy.ordinary_input_price_usd_per_million < 0
        or policy.cached_input_price_usd_per_million < 0
        or policy.output_price_usd_per_million < 0
    ):
        raise EvaluationConfigurationError(
            "OpenAI Responses model policy is invalid"
        )
    return policy


def conservative_cost_decimal(
    input_tokens: int | Decimal,
    output_tokens: int | Decimal,
    *,
    policy: OpenAIResponsesModelPolicy,
) -> Decimal:
    """Return conservative uncached cost at the resolved policy prices."""

    return route_priced_cost_decimal(
        input_tokens,
        0,
        output_tokens,
        policy=policy,
    )


def _load_openai_sdk() -> tuple[OpenAIConstructor, type[BaseException]]:
    """Load the SDK only after the evaluator has validated live authorization."""

    from openai import APITimeoutError, OpenAI

    return OpenAI, APITimeoutError


@dataclass(frozen=True, slots=True)
class _OpenAIResponsesTransport:
    """One licensed Responses client exposed through the evaluator protocol."""

    _responses_create: Callable[..., Any] = field(repr=False, compare=False)
    _timeout_error_type: type[BaseException] = field(repr=False, compare=False)
    policy: OpenAIResponsesModelPolicy
    _maximum_input_tokens: int
    _maximum_output_tokens: int
    _reasoning_effort: str
    credentials_accessed: bool = field(default=True, init=False)

    def __call__(
        self,
        *,
        role: str,
        prompt: str,
        system_prompt: str,
        provider: str,
        model: str,
        maximum_input_tokens: int,
        maximum_output_tokens: int,
    ) -> EvaluationTransportResponse:
        del role
        failure_message: str | None = None
        if provider != self.policy.provider or model != self.policy.model:
            failure_message = (
                "OpenAI Responses transport rejected a route outside its exact "
                "authorization."
            )
        elif (
            maximum_input_tokens != self._maximum_input_tokens
            or maximum_output_tokens != self._maximum_output_tokens
        ):
            failure_message = (
                "OpenAI Responses transport rejected token caps outside its "
                "exact authorization."
            )
        if failure_message is not None:
            prompt = ""
            system_prompt = ""
            raise EvaluationTransportError(failure_message)

        response: Any = None
        try:
            response = self._responses_create(
                model=model,
                instructions=system_prompt,
                input=prompt,
                reasoning={"effort": self._reasoning_effort},
                max_output_tokens=maximum_output_tokens,
                store=False,
            )
        except self._timeout_error_type:
            failure_message = TIMEOUT_ERROR_MESSAGE
        except Exception:
            failure_message = TRANSPORT_ERROR_MESSAGE
        if failure_message is not None:
            response = None
            prompt = ""
            system_prompt = ""
            raise EvaluationTransportError(failure_message)

        output: Any = None
        input_tokens: int | None = None
        output_tokens: int | None = None
        try:
            output = getattr(response, "output_text", None)
            if not isinstance(output, str) or not output:
                failure_message = OUTPUT_ERROR_MESSAGE
            else:
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "input_tokens", None)
                input_details = getattr(usage, "input_tokens_details", None)
                cached_input_tokens = getattr(
                    input_details,
                    "cached_tokens",
                    None,
                )
                output_tokens = getattr(usage, "output_tokens", None)
                output_details = getattr(
                    usage,
                    "output_tokens_details",
                    None,
                )
                reasoning_tokens = getattr(
                    output_details,
                    "reasoning_tokens",
                    None,
                )
                total_tokens = getattr(usage, "total_tokens", None)
                if (
                    any(
                        not isinstance(value, int) or value < 0
                        for value in (
                            input_tokens,
                            cached_input_tokens,
                            output_tokens,
                            reasoning_tokens,
                            total_tokens,
                        )
                    )
                    or cached_input_tokens > input_tokens
                    or reasoning_tokens > output_tokens
                    or total_tokens != input_tokens + output_tokens
                ):
                    failure_message = USAGE_ERROR_MESSAGE
        except Exception:
            failure_message = USAGE_ERROR_MESSAGE
        if failure_message is not None:
            response = None
            output = None
            input_tokens = None
            output_tokens = None
            prompt = ""
            system_prompt = ""
            raise EvaluationTransportError(failure_message)

        assert isinstance(output, str)
        assert input_tokens is not None
        assert output_tokens is not None
        uncached_input_tokens = input_tokens - cached_input_tokens
        non_reasoning_output_tokens = output_tokens - reasoning_tokens
        observed_cost = route_priced_cost_decimal(
            uncached_input_tokens,
            cached_input_tokens,
            output_tokens,
            policy=self.policy,
        )
        result = EvaluationTransportResponse(
            output=output,
            reasoning_effort=self._reasoning_effort,
            generation_status="completed",
            generation_incomplete_reason=None,
            max_output_tokens_reached=False,
            output_text_present=True,
            output_text_character_count=len(output),
            output_text_digest=digest_text(output),
            usage_observed=True,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            uncached_input_tokens=uncached_input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            non_reasoning_output_tokens=non_reasoning_output_tokens,
            total_tokens=total_tokens,
            caller_calculated_route_priced_cost_usd=format(
                observed_cost,
                "f",
            ),
            cost_posture="exact",
            output_token_utilization=format(
                Decimal(output_tokens)
                / Decimal(self._maximum_output_tokens),
                "f",
            ),
            reasoning_token_share=(
                format(Decimal(reasoning_tokens) / Decimal(output_tokens), "f")
                if output_tokens
                else None
            ),
            provider_elapsed_milliseconds_total=0,
            canonical_provider_used=self.policy.provider,
            canonical_model_used=self.policy.model,
            provider_request_attempt_count=1,
            raw_material_retained=False,
            credentials_accessed=True,
        )
        response = None
        return result


def _create_openai_responses_transport(
    authorization: LiveAuthorization,
    *,
    model_policies: Mapping[str, OpenAIResponsesModelPolicy],
) -> _OpenAIResponsesTransport:
    """Construct a direct Responses transport from one explicit policy map."""

    if authorization.provider != SUPPORTED_PROVIDER:
        raise EvaluationConfigurationError(
            "direct origination transport supports only provider openai"
        )
    policy = resolve_openai_model_policy(
        authorization.model,
        model_policies=model_policies,
    )
    if authorization.retry_cap != SDK_MAX_RETRIES:
        raise EvaluationConfigurationError(
            "direct origination transport requires retry cap 0"
        )
    if authorization.timeout_seconds != REQUEST_TIMEOUT_SECONDS:
        raise EvaluationConfigurationError(
            "direct origination transport requires its fixed timeout"
        )
    if (
        authorization.maximum_input_tokens <= 0
        or authorization.maximum_output_tokens <= 0
    ):
        raise EvaluationConfigurationError(
            "direct origination transport requires positive token caps"
        )
    if authorization.raw_retention_posture != "sanitized_only":
        raise EvaluationConfigurationError(
            "direct origination transport requires sanitized_only retention"
        )
    if not authorization.reasoning_effort:
        raise EvaluationConfigurationError(
            "direct origination transport requires exact reasoning effort"
        )

    openai_constructor, timeout_error_type = _load_openai_sdk()
    client: Any = None
    construction_failed = False
    try:
        client = openai_constructor(
            max_retries=SDK_MAX_RETRIES,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception:
        construction_failed = True
    if construction_failed:
        raise EvaluationTransportError(
            "OpenAI Responses client construction failed closed."
        )
    responses_create: Callable[..., Any] | None = None
    try:
        responses_create = client.responses.create
    except Exception:
        construction_failed = True
    if construction_failed or responses_create is None:
        client = None
        raise EvaluationTransportError(
            "OpenAI Responses client construction failed closed."
        )
    transport = _OpenAIResponsesTransport(
        _responses_create=responses_create,
        _timeout_error_type=timeout_error_type,
        policy=policy,
        _maximum_input_tokens=authorization.maximum_input_tokens,
        _maximum_output_tokens=authorization.maximum_output_tokens,
        _reasoning_effort=authorization.reasoning_effort,
    )
    client = None
    return transport


def create_openai_responses_transport(
    authorization: LiveAuthorization,
) -> _OpenAIResponsesTransport:
    """Construct the licensed direct Responses transport."""

    return _create_openai_responses_transport(
        authorization,
        model_policies=OPENAI_MODEL_POLICIES,
    )


setattr(
    create_openai_responses_transport,
    "transport_factory_spec",
    TRANSPORT_FACTORY_SPEC,
)


__all__ = [
    "GPT54_MODEL_ID",
    "OPENAI_MODEL_POLICIES",
    "OpenAIResponsesModelPolicy",
    "REQUEST_TIMEOUT_SECONDS",
    "SDK_MAX_RETRIES",
    "SUPPORTED_PROVIDER",
    "TIMEOUT_ERROR_MESSAGE",
    "TRANSPORT_FACTORY_SPEC",
    "conservative_cost_decimal",
    "create_openai_responses_transport",
    "resolve_openai_model_policy",
]
