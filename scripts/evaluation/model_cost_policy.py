"""Caller-owned exact model pricing used by evaluation and smoke proofs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

SUPPORTED_PROVIDER = "openai"
GPT54_MODEL_ID = "gpt-5.4-2026-03-05"
TOKENS_PER_MILLION = Decimal("1000000")


@dataclass(frozen=True, slots=True)
class ModelCostPolicy:
    provider: str
    model: str
    reasoning_effort: str
    input_price_usd_per_million: Decimal
    output_price_usd_per_million: Decimal


MODEL_COST_POLICIES: Mapping[tuple[str, str], ModelCostPolicy] = MappingProxyType(
    {
        (SUPPORTED_PROVIDER, GPT54_MODEL_ID): ModelCostPolicy(
            provider=SUPPORTED_PROVIDER,
            model=GPT54_MODEL_ID,
            reasoning_effort="medium",
            input_price_usd_per_million=Decimal("2.50"),
            output_price_usd_per_million=Decimal("15.00"),
        )
    }
)


def resolve_model_cost_policy(provider: str, model: str) -> ModelCostPolicy:
    policy = MODEL_COST_POLICIES.get((provider, model))
    if policy is None:
        raise ValueError("no caller-owned cost policy exists for the exact route")
    if (
        policy.provider != provider
        or policy.model != model
        or not policy.reasoning_effort
        or policy.input_price_usd_per_million < 0
        or policy.output_price_usd_per_million < 0
    ):
        raise ValueError("caller-owned model cost policy is invalid")
    return policy


def conservative_cost_decimal(
    input_tokens: int | Decimal,
    output_tokens: int | Decimal,
    *,
    policy: ModelCostPolicy,
) -> Decimal:
    return (
        Decimal(input_tokens)
        * policy.input_price_usd_per_million
        / TOKENS_PER_MILLION
        + Decimal(output_tokens)
        * policy.output_price_usd_per_million
        / TOKENS_PER_MILLION
    )


__all__ = [
    "GPT54_MODEL_ID",
    "MODEL_COST_POLICIES",
    "ModelCostPolicy",
    "SUPPORTED_PROVIDER",
    "conservative_cost_decimal",
    "resolve_model_cost_policy",
]
