"""Centralized search-provider selection (Phase A4)."""

from __future__ import annotations

from typing import Optional

QUERY_TYPE_ENUM = frozenset(
    {
        "news",
        "current_events",
        "event",
        "person",
        "product",
        "place",
        "comparison",
        "quantitative_comparison",
        "concept",
        "how_to",
        "other",
    }
)


def is_quantitative_query(query_type: str | None, report_type: str | None) -> bool:
    """True when retrieval/corpus logic should treat the run as comparison or benchmark-heavy."""
    qt = (query_type or "other").strip().lower()
    rt = (report_type or "").strip().lower()
    return qt in {"comparison", "quantitative_comparison"} or rt in {
        "quantitative_comparison",
        "comparative_analysis",
        "benchmark",
        "cost_analysis",
        "unit_economics",
    }


def should_allow_linkup_provider(
    complexity: str | None,
    *,
    explicit_provider_override: bool = False,
    premium_search_escalation: bool = False,
) -> bool:
    """Return True when Linkup is justified despite its premium cost profile."""
    if explicit_provider_override or premium_search_escalation:
        return True
    return (complexity or "").strip().lower() == "high"


def merge_search_provider_overrides(
    primary: list[str] | None,
    secondary: list[str] | None,
    available_keys: dict[str, bool],
    *,
    complexity: str | None = None,
    secondary_premium_escalation: bool = False,
) -> list[str] | None:
    """Merge scout/expander overrides with user retry overrides; preserve order, dedupe."""
    if not primary and not secondary:
        return None
    seen: set[str] = set()
    out: list[str] = []
    for source, providers in (("primary", primary or []), ("secondary", secondary or [])):
        for p in providers:
            key = str(p).strip().lower()
            if not key or key in seen or not available_keys.get(key):
                continue
            if (
                key == "linkup"
                and complexity is not None
                and not should_allow_linkup_provider(
                    complexity,
                    explicit_provider_override=source == "primary",
                    premium_search_escalation=source == "secondary" and secondary_premium_escalation,
                )
            ):
                continue
            seen.add(key)
            out.append(key)
    return out or None


def _filter_available_override_providers(
    override: list[str],
    available_keys: dict[str, bool],
    complexity: str,
    *,
    override_is_user: bool,
    premium_search_escalation: bool,
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for p in override:
        key = str(p).strip().lower()
        if not key or key in seen or not available_keys.get(key):
            continue
        if key == "linkup" and not should_allow_linkup_provider(
            complexity,
            explicit_provider_override=override_is_user,
            premium_search_escalation=premium_search_escalation,
        ):
            continue
        seen.add(key)
        out.append(key)
    return out


def select_providers(
    query_type: str,
    intent: str,
    complexity: str,
    available_keys: dict[str, bool],
    report_type: str = "general_research",
    is_academic: bool = False,
    suppress_tavily: bool = False,
    override: Optional[list[str]] = None,
    override_is_user: bool = True,
    premium_search_escalation: bool = False,
) -> list[str]:
    """
    Returns ordered provider list.
    Override (from UI or scout) bypasses matrix logic and keeps only providers
    that are available.
    Comparison / quantitative paths drop Exa in favor of Tavily/Linkup.
    """

    def ensure_non_empty(result: list[str]) -> list[str]:
        return result if result else ["tavily"]

    if override is not None:
        return ensure_non_empty(
            _filter_available_override_providers(
                override,
                available_keys,
                complexity,
                override_is_user=override_is_user,
                premium_search_escalation=premium_search_escalation,
            )
        )

    qt = (query_type or "other").strip().lower()
    is_quant = is_quantitative_query(query_type, report_type)
    linkup_allowed = should_allow_linkup_provider(
        complexity,
        premium_search_escalation=premium_search_escalation,
    )

    if intent == "news" or qt in {"news", "current_events", "event"}:
        result = ["tavily"]
        if available_keys.get("linkup") and linkup_allowed:
            result.append("linkup")
        return ensure_non_empty(result)

    if is_quant:
        result = []
        if (not suppress_tavily) and available_keys.get("tavily"):
            result.append("tavily")
        if available_keys.get("linkup") and linkup_allowed:
            result.append("linkup")
        return ensure_non_empty(result or (["tavily"] if available_keys.get("tavily") else []))

    if is_academic:
        if available_keys.get("exa"):
            return ["exa"]
        return ensure_non_empty(["tavily"])

    result = []
    if (not suppress_tavily) and available_keys.get("tavily"):
        result.append("tavily")
    if available_keys.get("linkup") and linkup_allowed:
        result.append("linkup")
    if available_keys.get("exa"):
        result.append("exa")
    return ensure_non_empty(result)
