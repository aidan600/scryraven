"""Product-owned bounded public CLI posture and immutable cap facts."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Iterable

from core.cap_enforcement import (
    ExternalCallFamily,
    RoutePricing,
    RunCapEnvelope,
    RunCapExceeded,
    RunCapPolicy,
    TokenUsage,
    conservative_text_token_upper_bound,
)

BOUNDED_PRODUCT_PROFILE_NAME = "public-cli-v1"
BOUNDED_PRODUCT_PRICING_VERSION = "cap-ceiling-2026-08-04-v1"
MODEL_OUTPUT_TOKEN_LIMIT = 16_384
MODEL_REASONING_TOKEN_LIMIT = 16_384
DEFAULT_EXTERNAL_TIMEOUT_SECONDS = 30.0
_DEADLINE_SECONDS = 240.0
_MAX_TOTAL_ATTEMPTS = 128
_MAX_ATTEMPTS_BY_FAMILY = MappingProxyType(
    {
        ExternalCallFamily.MODEL: 80,
        ExternalCallFamily.EMBEDDING: 24,
        ExternalCallFamily.SEARCH: 32,
        ExternalCallFamily.READ: 16,
    }
)
_MODEL_TOKEN_CAP = TokenUsage(
    input_tokens=4_000_000,
    cached_input_tokens=4_000_000,
    output_tokens=700_000,
    reasoning_tokens=700_000,
)
_EMBEDDING_TOKEN_CAP = TokenUsage(embedding_tokens=3_000_000)
_ZERO_TOKEN_CAP = TokenUsage()
_MAX_TOKENS = TokenUsage(
    input_tokens=_MODEL_TOKEN_CAP.input_tokens,
    cached_input_tokens=_MODEL_TOKEN_CAP.cached_input_tokens,
    output_tokens=_MODEL_TOKEN_CAP.output_tokens,
    reasoning_tokens=_MODEL_TOKEN_CAP.reasoning_tokens,
    embedding_tokens=_EMBEDDING_TOKEN_CAP.embedding_tokens,
)
_MAX_TOKENS_BY_FAMILY = MappingProxyType(
    {
        ExternalCallFamily.MODEL: _MODEL_TOKEN_CAP,
        ExternalCallFamily.EMBEDDING: _EMBEDDING_TOKEN_CAP,
        ExternalCallFamily.SEARCH: _ZERO_TOKEN_CAP,
        ExternalCallFamily.READ: _ZERO_TOKEN_CAP,
    }
)
_MAX_PER_ATTEMPT_USD = Decimal("20")
_MAX_RUN_USD = Decimal("120")
_MAX_RETRIES = 0
_MAX_FALLBACKS = 0
_SUPPRESS_PERSISTENCE = True


def _price(
    key: str,
    *,
    input_rate: str = "0",
    cached_input_rate: str = "0",
    output_rate: str = "0",
    reasoning_rate: str = "0",
    embedding_rate: str = "0",
    flat: str = "0",
) -> RoutePricing:
    return RoutePricing(
        pricing_key=key,
        input_per_million_usd=Decimal(input_rate),
        cached_input_per_million_usd=Decimal(cached_input_rate),
        output_per_million_usd=Decimal(output_rate),
        reasoning_per_million_usd=Decimal(reasoning_rate),
        embedding_per_million_usd=Decimal(embedding_rate),
        flat_attempt_usd=Decimal(flat),
    )


# These are intentionally conservative admission ceilings, not billing estimates.
# A bounded route is unavailable until an exact, immutable key is present here.
_ROUTE_PRICING = MappingProxyType(
    {
        (ExternalCallFamily.MODEL, "openai", "gpt-5.4-mini"): _price(
            "openai.gpt-5.4-mini",
            input_rate="5",
            cached_input_rate="5",
            output_rate="30",
            reasoning_rate="30",
        ),
        (ExternalCallFamily.MODEL, "openai", "gpt-5.4"): _price(
            "openai.gpt-5.4",
            input_rate="20",
            cached_input_rate="20",
            output_rate="120",
            reasoning_rate="120",
        ),
        (
            ExternalCallFamily.EMBEDDING,
            "openai",
            "text-embedding-3-small",
        ): _price(
            "openai.text-embedding-3-small",
            embedding_rate="1",
        ),
        (ExternalCallFamily.SEARCH, "tavily", "search"): _price(
            "tavily.search",
            flat="0.25",
        ),
        (ExternalCallFamily.SEARCH, "linkup", "search"): _price(
            "linkup.search",
            flat="0.25",
        ),
        (ExternalCallFamily.SEARCH, "exa", "search"): _price(
            "exa.search",
            flat="0.25",
        ),
        (ExternalCallFamily.SEARCH, "brave", "search"): _price(
            "brave.search",
            flat="0.25",
        ),
        (ExternalCallFamily.SEARCH, "serper", "search"): _price(
            "serper.search",
            flat="0.25",
        ),
        (ExternalCallFamily.READ, "linkup", "fetch"): _price(
            "linkup.fetch",
            flat="0.25",
        ),
        (ExternalCallFamily.READ, "tavily", "extract"): _price(
            "tavily.extract",
            flat="0.25",
        ),
        (ExternalCallFamily.READ, "tavily", "map"): _price(
            "tavily.map",
            flat="1.00",
        ),
        (ExternalCallFamily.READ, "tavily", "crawl"): _price(
            "tavily.crawl",
            flat="2.00",
        ),
        (ExternalCallFamily.READ, "linkup", "search"): _price(
            "linkup.search",
            flat="1.00",
        ),
    }
)


def _profile_digest() -> str:
    canonical = {
        "name": BOUNDED_PRODUCT_PROFILE_NAME,
        "pricing_version": BOUNDED_PRODUCT_PRICING_VERSION,
        "envelope": {
            "deadline_seconds": _DEADLINE_SECONDS,
            "max_total_attempts": _MAX_TOTAL_ATTEMPTS,
            "max_attempts_by_family": {family.value: _MAX_ATTEMPTS_BY_FAMILY[family] for family in ExternalCallFamily},
            "max_tokens": _MAX_TOKENS.as_dict(),
            "max_tokens_by_family": {
                family.value: _MAX_TOKENS_BY_FAMILY[family].as_dict() for family in ExternalCallFamily
            },
            "max_per_attempt_usd": str(_MAX_PER_ATTEMPT_USD),
            "max_run_usd": str(_MAX_RUN_USD),
            "max_retries": _MAX_RETRIES,
            "max_fallbacks": _MAX_FALLBACKS,
            "suppress_persistence": _SUPPRESS_PERSISTENCE,
        },
        "routes": sorted(
            (
                family.value,
                provider,
                route,
                pricing.pricing_key,
                str(pricing.input_per_million_usd),
                str(pricing.cached_input_per_million_usd),
                str(pricing.output_per_million_usd),
                str(pricing.reasoning_per_million_usd),
                str(pricing.embedding_per_million_usd),
                str(pricing.flat_attempt_usd),
            )
            for (family, provider, route), pricing in _ROUTE_PRICING.items()
        ),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:24]


BOUNDED_PRODUCT_PROFILE_DIGEST = _profile_digest()


def _new_policy() -> RunCapPolicy:
    envelope = RunCapEnvelope(
        profile_name=BOUNDED_PRODUCT_PROFILE_NAME,
        profile_digest=BOUNDED_PRODUCT_PROFILE_DIGEST,
        pricing_version=BOUNDED_PRODUCT_PRICING_VERSION,
        deadline_seconds=_DEADLINE_SECONDS,
        max_total_attempts=_MAX_TOTAL_ATTEMPTS,
        max_attempts_by_family=_MAX_ATTEMPTS_BY_FAMILY,
        max_tokens=_MAX_TOKENS,
        max_tokens_by_family=_MAX_TOKENS_BY_FAMILY,
        max_per_attempt_usd=_MAX_PER_ATTEMPT_USD,
        max_run_usd=_MAX_RUN_USD,
        max_retries=_MAX_RETRIES,
        max_fallbacks=_MAX_FALLBACKS,
        suppress_persistence=_SUPPRESS_PERSISTENCE,
    )
    return RunCapPolicy(
        max_search_dispatches=32,
        max_fetch_read_operations=16,
        max_author_model_calls=8,
        max_smart_search_judgment_model_calls=16,
        max_retries=_MAX_RETRIES,
        envelope=envelope,
    )


def build_bounded_product_policy(config: Any) -> RunCapPolicy:
    """Validate exact model routes and build a fresh run-scoped ledger."""

    validate_bounded_product_config(config)
    return _new_policy()


def bounded_product_configuration_snapshot() -> dict[str, Any]:
    """Return the immutable profile's sanitized zero-attempt configuration."""

    return _new_policy().physical_snapshot()


def validate_bounded_product_config(config: Any) -> None:
    """Fail closed before a run when its selected route lacks exact facts."""

    selected = (
        (ExternalCallFamily.MODEL, config.fast_provider, config.fast_model),
        (ExternalCallFamily.MODEL, config.smart_provider, config.smart_model),
        (
            ExternalCallFamily.EMBEDDING,
            config.embed_provider,
            config.embed_model,
        ),
    )
    for family, provider, route in selected:
        get_route_pricing(family, provider, route)


def get_route_pricing(
    family: ExternalCallFamily,
    provider: str,
    route: str,
) -> RoutePricing:
    """Return the immutable price fact for an exact physical route."""

    normalized_family = ExternalCallFamily(family)
    key = (
        normalized_family,
        str(provider).strip().lower(),
        str(route).strip().lower(),
    )
    try:
        return _ROUTE_PRICING[key]
    except KeyError as exc:
        raise RunCapExceeded(
            "unsupported_route_pricing",
            family=normalized_family,
        ) from exc


def model_usage_bound(prompt: str, system_prompt: str = "") -> TokenUsage:
    """Build a tokenizer-independent conservative per-attempt model bound."""

    input_bound = conservative_text_token_upper_bound(
        f"{system_prompt}\n{prompt}",
        structural_overhead=64,
    )
    return TokenUsage(
        input_tokens=input_bound,
        output_tokens=MODEL_OUTPUT_TOKEN_LIMIT,
        reasoning_tokens=MODEL_REASONING_TOKEN_LIMIT,
    )


def embedding_usage_bound(texts: Iterable[str]) -> TokenUsage:
    """Build a conservative aggregate embedding-token bound for one batch."""

    bound = sum(conservative_text_token_upper_bound(text, structural_overhead=8) for text in texts)
    return TokenUsage(embedding_tokens=bound)


__all__ = [
    "BOUNDED_PRODUCT_PRICING_VERSION",
    "BOUNDED_PRODUCT_PROFILE_DIGEST",
    "BOUNDED_PRODUCT_PROFILE_NAME",
    "DEFAULT_EXTERNAL_TIMEOUT_SECONDS",
    "MODEL_OUTPUT_TOKEN_LIMIT",
    "MODEL_REASONING_TOKEN_LIMIT",
    "bounded_product_configuration_snapshot",
    "build_bounded_product_policy",
    "embedding_usage_bound",
    "get_route_pricing",
    "model_usage_bound",
    "validate_bounded_product_config",
]
