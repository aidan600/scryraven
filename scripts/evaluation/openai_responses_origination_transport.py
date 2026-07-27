"""Evaluation-only direct OpenAI Responses transport for AnalystOS origination.

This adapter is deliberately narrower than the product-owned model routes.  It
supports one provider, one model snapshot, one reasoning posture, and one
physical Responses API attempt per invocation.  Authentication is delegated to
the OpenAI SDK's process authentication; this module never reads a credential.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable

from core.cost_accounting import extract_usage_tokens
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationConfigurationError,
    EvaluationTransportError,
    EvaluationTransportResponse,
    LiveAuthorization,
)

TRANSPORT_FACTORY_SPEC = (
    "scripts.evaluation.openai_responses_origination_transport:"
    "create_openai_responses_transport"
)
SUPPORTED_PROVIDER = "openai"
SUPPORTED_MODEL = "gpt-5.4-2026-03-05"
REASONING_EFFORT = "medium"
REQUEST_TIMEOUT_SECONDS = 600.0
SDK_MAX_RETRIES = 0

INPUT_PRICE_USD_PER_MILLION = Decimal("2.50")
OUTPUT_PRICE_USD_PER_MILLION = Decimal("15.00")
TOKENS_PER_MILLION = Decimal("1000000")

TIMEOUT_ERROR_MESSAGE = (
    "OpenAI Responses request timed out; billing is unknown and explicit "
    "maintainer reauthorization is required."
)
TRANSPORT_ERROR_MESSAGE = "OpenAI Responses request failed closed."
USAGE_ERROR_MESSAGE = "OpenAI Responses request omitted exact usage accounting."
OUTPUT_ERROR_MESSAGE = "OpenAI Responses request returned no output text."

OpenAIConstructor = Callable[..., Any]


def conservative_cost_decimal(
    input_tokens: int | Decimal,
    output_tokens: int | Decimal,
) -> Decimal:
    """Return conservative uncached cost at the phase-fixed token prices."""

    return (
        Decimal(input_tokens) * INPUT_PRICE_USD_PER_MILLION / TOKENS_PER_MILLION
        + Decimal(output_tokens) * OUTPUT_PRICE_USD_PER_MILLION / TOKENS_PER_MILLION
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
    _maximum_input_tokens: int
    _maximum_output_tokens: int
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
        if provider != SUPPORTED_PROVIDER or model != SUPPORTED_MODEL:
            raise EvaluationTransportError(
                "OpenAI Responses transport rejected a route outside its exact authorization."
            )
        if (
            maximum_input_tokens != self._maximum_input_tokens
            or maximum_output_tokens != self._maximum_output_tokens
        ):
            raise EvaluationTransportError(
                "OpenAI Responses transport rejected token caps outside its exact authorization."
            )

        response: Any = None
        try:
            response = self._responses_create(
                model=model,
                instructions=system_prompt,
                input=prompt,
                reasoning={"effort": REASONING_EFFORT},
                max_output_tokens=maximum_output_tokens,
                store=False,
            )
        except self._timeout_error_type:
            raise EvaluationTransportError(TIMEOUT_ERROR_MESSAGE) from None
        except Exception:
            raise EvaluationTransportError(TRANSPORT_ERROR_MESSAGE) from None

        try:
            output = getattr(response, "output_text", None)
            if not isinstance(output, str) or not output:
                raise EvaluationTransportError(OUTPUT_ERROR_MESSAGE)
            input_tokens, output_tokens = extract_usage_tokens(response)
            if (
                input_tokens is None
                or output_tokens is None
                or input_tokens < 0
                or output_tokens < 0
            ):
                raise EvaluationTransportError(USAGE_ERROR_MESSAGE)
            observed_cost = conservative_cost_decimal(
                input_tokens,
                output_tokens,
            )
            return EvaluationTransportResponse(
                output=output,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=float(observed_cost),
                canonical_provider_used=SUPPORTED_PROVIDER,
                canonical_model_used=SUPPORTED_MODEL,
                provider_request_attempt_count=1,
                raw_material_retained=False,
                credentials_accessed=True,
            )
        finally:
            response = None


def create_openai_responses_transport(
    authorization: LiveAuthorization,
) -> _OpenAIResponsesTransport:
    """Construct the exact phase-specific direct Responses transport."""

    if authorization.provider != SUPPORTED_PROVIDER:
        raise EvaluationConfigurationError(
            "direct origination transport supports only provider openai"
        )
    if authorization.model != SUPPORTED_MODEL:
        raise EvaluationConfigurationError(
            f"direct origination transport supports only model {SUPPORTED_MODEL}"
        )
    if authorization.retry_cap != SDK_MAX_RETRIES:
        raise EvaluationConfigurationError(
            "direct origination transport requires retry cap 0"
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

    openai_constructor, timeout_error_type = _load_openai_sdk()
    try:
        client = openai_constructor(
            max_retries=SDK_MAX_RETRIES,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception:
        raise EvaluationTransportError(
            "OpenAI Responses client construction failed closed."
        ) from None
    return _OpenAIResponsesTransport(
        _responses_create=client.responses.create,
        _timeout_error_type=timeout_error_type,
        _maximum_input_tokens=authorization.maximum_input_tokens,
        _maximum_output_tokens=authorization.maximum_output_tokens,
    )


setattr(
    create_openai_responses_transport,
    "transport_factory_spec",
    TRANSPORT_FACTORY_SPEC,
)


__all__ = [
    "INPUT_PRICE_USD_PER_MILLION",
    "OUTPUT_PRICE_USD_PER_MILLION",
    "REASONING_EFFORT",
    "REQUEST_TIMEOUT_SECONDS",
    "SDK_MAX_RETRIES",
    "SUPPORTED_MODEL",
    "SUPPORTED_PROVIDER",
    "TIMEOUT_ERROR_MESSAGE",
    "TRANSPORT_FACTORY_SPEC",
    "conservative_cost_decimal",
    "create_openai_responses_transport",
]
