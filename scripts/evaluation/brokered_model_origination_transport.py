"""Provider-neutral brokered transport for AnalystOS model origination."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Mapping

from scripts import request_provider_proxy_broker as broker_client
from scripts.evaluation.model_cost_policy import (
    ModelCostPolicy,
    resolve_model_cost_policy,
    route_priced_cost_decimal,
)
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationConfigurationError,
    EvaluationTransportError,
    EvaluationTransportResponse,
    LiveAuthorization,
)
from scripts.provider_execution_contract import (
    FALSE_RETENTION_FLAGS,
    MODEL_GENERATE_OPERATION,
    ProviderExecutionContractError,
    build_model_request,
    digest_text,
    validate_provider_execution_response,
)

TRANSPORT_FACTORY_SPEC = (
    "scripts.evaluation.brokered_model_origination_transport:"
    "create_brokered_model_origination_transport"
)

BrokerRequest = Callable[
    [str, str, Mapping[str, Any]],
    Mapping[str, Any],
]


@dataclass(frozen=True, slots=True)
class _BrokeredModelOriginationTransport:
    _broker_url: str
    _session_token: str = field(repr=False, compare=False)
    _request: BrokerRequest = field(repr=False, compare=False)
    _authorization: LiveAuthorization
    _cost_policy: ModelCostPolicy
    credentials_accessed: bool = field(default=False, init=False)

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
        if role not in self._authorization.allowed_model_roles:
            prompt = ""
            system_prompt = ""
            raise EvaluationTransportError(
                "brokered transport rejected a role outside exact authorization"
            )
        if (
            provider != self._authorization.provider
            or model != self._authorization.model
        ):
            prompt = ""
            system_prompt = ""
            raise EvaluationTransportError(
                "brokered transport rejected a route outside exact authorization"
            )
        if (
            maximum_input_tokens != self._authorization.maximum_input_tokens
            or maximum_output_tokens != self._authorization.maximum_output_tokens
        ):
            prompt = ""
            system_prompt = ""
            raise EvaluationTransportError(
                "brokered transport rejected token caps outside exact authorization"
            )
        request_payload = build_model_request(
            provider=provider,
            model=model,
            system_instructions=system_prompt,
            input_prompt=prompt,
            reasoning_effort=self._authorization.reasoning_effort,
            max_output_tokens=maximum_output_tokens,
            timeout_seconds=self._authorization.timeout_seconds,
            retry_cap=self._authorization.retry_cap,
        )
        response: Mapping[str, Any] | None = None
        output_text: str | None = None
        try:
            response = validate_provider_execution_response(
                self._request(
                    self._broker_url,
                    self._session_token,
                    request_payload,
                ),
                request_payload=request_payload,
            )
            if any(response.get(flag) is not False for flag in FALSE_RETENTION_FLAGS):
                raise EvaluationTransportError(
                    "brokered transport response retention posture is invalid"
                )
            if (
                response.get("provider") != provider
                or response.get("operation") != MODEL_GENERATE_OPERATION
                or response.get("model") != model
                or response.get("reasoning_effort")
                != self._authorization.reasoning_effort
                or response.get("physical_attempt_count") != 1
            ):
                raise EvaluationTransportError(
                    "brokered transport response attestation is invalid"
                )
            usage = response.get("usage")
            if not isinstance(usage, Mapping):
                raise EvaluationTransportError(
                    "brokered transport response omitted usage posture"
                )
            usage_observed = usage.get("usage_observed") is True
            input_tokens = usage.get("input_tokens")
            cached_input_tokens = usage.get("cached_input_tokens")
            uncached_input_tokens = usage.get("uncached_input_tokens")
            output_tokens = usage.get("output_tokens")
            reasoning_tokens = usage.get("reasoning_tokens")
            non_reasoning_output_tokens = usage.get(
                "non_reasoning_output_tokens"
            )
            total_tokens = usage.get("total_tokens")
            cost: Decimal | None = None
            if usage_observed:
                if (
                    input_tokens > maximum_input_tokens
                    or output_tokens > maximum_output_tokens
                ):
                    raise EvaluationTransportError(
                        "brokered transport response exceeded authorized token caps"
                    )
                cost = route_priced_cost_decimal(
                    uncached_input_tokens,
                    cached_input_tokens,
                    output_tokens,
                    policy=self._cost_policy,
                )
                if cost > Decimal(str(self._authorization.cost_ceiling)):
                    raise EvaluationTransportError(
                        "brokered transport response exceeded authorized cost ceiling"
                    )
            output_text_value = response.get("output_text")
            if not isinstance(output_text_value, str):
                raise EvaluationTransportError(
                    "brokered transport response omitted output posture"
                )
            output_text = output_text_value
            output_token_utilization = (
                format(
                    Decimal(output_tokens) / Decimal(maximum_output_tokens),
                    "f",
                )
                if usage_observed
                else None
            )
            reasoning_token_share = (
                format(Decimal(reasoning_tokens) / Decimal(output_tokens), "f")
                if usage_observed and output_tokens
                else None
            )
            result = EvaluationTransportResponse(
                output=output_text,
                reasoning_effort=self._authorization.reasoning_effort,
                generation_status=response["generation_status"],
                generation_incomplete_reason=response.get(
                    "generation_incomplete_reason"
                ),
                max_output_tokens_reached=response[
                    "max_output_tokens_reached"
                ],
                output_text_present=response["output_text_present"],
                output_text_character_count=len(output_text),
                output_text_digest=digest_text(output_text),
                usage_observed=usage_observed,
                input_tokens=input_tokens,
                cached_input_tokens=cached_input_tokens,
                uncached_input_tokens=uncached_input_tokens,
                output_tokens=output_tokens,
                reasoning_tokens=reasoning_tokens,
                non_reasoning_output_tokens=non_reasoning_output_tokens,
                total_tokens=total_tokens,
                caller_calculated_route_priced_cost_usd=(
                    format(cost, "f") if cost is not None else None
                ),
                cost_posture="exact" if cost is not None else "unknown",
                output_token_utilization=output_token_utilization,
                reasoning_token_share=reasoning_token_share,
                provider_elapsed_milliseconds_total=response[
                    "provider_elapsed_milliseconds_total"
                ],
                canonical_provider_used=provider,
                canonical_model_used=model,
                provider_request_attempt_count=1,
                raw_material_retained=False,
                credentials_accessed=True,
            )
            response = None
            output_text = None
            prompt = ""
            system_prompt = ""
            return result
        except EvaluationTransportError:
            raise
        except ProviderExecutionContractError as exc:
            raise EvaluationTransportError(
                "brokered model origination transport failed closed: "
                f"{exc.failure_class}"
            ) from None
        except broker_client.ProviderExecutionClientError as exc:
            raise EvaluationTransportError(
                "brokered model origination transport failed closed: "
                f"{exc.failure_class}"
            ) from None
        finally:
            response = None
            output_text = None
            prompt = ""
            system_prompt = ""


def _request_broker(
    broker_url: str,
    token: str,
    request_payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    return broker_client.request_provider_execution(
        broker_url=broker_url,
        token=token,
        request_payload=request_payload,
    )


def _create_brokered_model_origination_transport(
    authorization: LiveAuthorization,
    *,
    broker_url: str,
    session_token: str,
    request_function: BrokerRequest,
) -> _BrokeredModelOriginationTransport:
    if authorization.retry_cap != 0:
        raise EvaluationConfigurationError(
            "brokered origination transport requires exact retry cap 0"
        )
    if (
        authorization.timeout_seconds <= 0
        or authorization.timeout_seconds > 600
    ):
        raise EvaluationConfigurationError(
            "brokered origination transport requires a bounded timeout"
        )
    if (
        authorization.maximum_input_tokens <= 0
        or authorization.maximum_output_tokens <= 0
    ):
        raise EvaluationConfigurationError(
            "brokered origination transport requires positive token caps"
        )
    if authorization.raw_retention_posture != "sanitized_only":
        raise EvaluationConfigurationError(
            "brokered origination transport requires sanitized_only retention"
        )
    if not authorization.reasoning_effort:
        raise EvaluationConfigurationError(
            "brokered origination transport requires exact reasoning effort"
        )
    if not broker_client._is_loopback_broker_url(broker_url):
        raise EvaluationConfigurationError(
            "brokered origination transport requires the loopback broker"
        )
    if not session_token:
        raise EvaluationConfigurationError(
            "brokered origination transport requires a temporary broker session"
        )
    try:
        cost_policy = resolve_model_cost_policy(
            authorization.provider,
            authorization.model,
        )
    except ValueError as exc:
        raise EvaluationConfigurationError(
            "no caller-owned cost policy exists for the exact authorized route"
        ) from exc
    return _BrokeredModelOriginationTransport(
        _broker_url=broker_url,
        _session_token=session_token,
        _request=request_function,
        _authorization=authorization,
        _cost_policy=cost_policy,
    )


def create_brokered_model_origination_transport(
    authorization: LiveAuthorization,
) -> _BrokeredModelOriginationTransport:
    """Construct the active provider-neutral AnalystOS broker transport."""

    return _create_brokered_model_origination_transport(
        authorization,
        broker_url=broker_client.DEFAULT_BROKER_URL,
        session_token=os.environ.get(broker_client.TOKEN_ENV_VAR, ""),
        request_function=_request_broker,
    )


setattr(
    create_brokered_model_origination_transport,
    "transport_factory_spec",
    TRANSPORT_FACTORY_SPEC,
)


__all__ = [
    "TRANSPORT_FACTORY_SPEC",
    "create_brokered_model_origination_transport",
]
