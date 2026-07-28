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
    ordinary_input_price_usd_per_million: Decimal
    cached_input_price_usd_per_million: Decimal
    output_price_usd_per_million: Decimal


MODEL_COST_POLICIES: Mapping[tuple[str, str], ModelCostPolicy] = MappingProxyType(
    {
        (SUPPORTED_PROVIDER, GPT54_MODEL_ID): ModelCostPolicy(
            provider=SUPPORTED_PROVIDER,
            model=GPT54_MODEL_ID,
            ordinary_input_price_usd_per_million=Decimal("2.50"),
            cached_input_price_usd_per_million=Decimal("0.25"),
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
        or policy.ordinary_input_price_usd_per_million < 0
        or policy.cached_input_price_usd_per_million < 0
        or policy.output_price_usd_per_million < 0
    ):
        raise ValueError("caller-owned model cost policy is invalid")
    return policy


def route_priced_cost_decimal(
    uncached_input_tokens: int | Decimal,
    cached_input_tokens: int | Decimal,
    output_tokens: int | Decimal,
    *,
    policy: ModelCostPolicy,
) -> Decimal:
    return (
        (
            Decimal(uncached_input_tokens)
            * policy.ordinary_input_price_usd_per_million
            + Decimal(cached_input_tokens)
            * policy.cached_input_price_usd_per_million
            + Decimal(output_tokens)
            * policy.output_price_usd_per_million
        )
        / TOKENS_PER_MILLION
    )


__all__ = [
    "GPT54_MODEL_ID",
    "MODEL_COST_POLICIES",
    "ModelCostPolicy",
    "SUPPORTED_PROVIDER",
    "route_priced_cost_decimal",
    "resolve_model_cost_policy",
]
