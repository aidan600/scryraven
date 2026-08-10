"""Provider-neutral ordinary Scout adapter for bounded disambiguation.

This adapter is deliberately small: it turns an already-authorized Scout
candidate into one ``DISCOVER/lightweight_disambiguation`` route decision and
one bounded provider search per admitted candidate.  It retains neither raw
provider responses nor evidence authority; its output is the sanitized,
direction-only shape consumed by ``scout_disambiguation_runtime``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from core.cap_enforcement import RunCapPolicy
from core.routing import (
    AcquisitionCapability,
    DiscoverQualifier,
    ProviderCapabilityRequest,
    ProviderRouteDecision,
    route_provider_capability,
)
from core.search_providers import search_scout_results

ORDINARY_SCOUT_DISAMBIGUATION_ADAPTER_SCHEMA_VERSION = (
    "ordinary_scout_disambiguation_adapter_searchos_required_scout_ordinary_composition_01_v1"
)
ORDINARY_SCOUT_MAX_RESULTS_PER_QUERY = 5

ScoutSearchCallable = Callable[..., Sequence[Mapping[str, Any]]]
ScoutRouteCallable = Callable[..., ProviderRouteDecision]


@dataclass(frozen=True, slots=True)
class OrdinaryScoutDisambiguationAdapter:
    """Execute authorized Scout candidates through the provider-neutral route."""

    available_providers: Mapping[str, object]
    cap_policy: RunCapPolicy | None = None
    cost_accumulator: Any | None = None
    scout_search: ScoutSearchCallable = search_scout_results
    route: ScoutRouteCallable = route_provider_capability
    max_results_per_query: int = ORDINARY_SCOUT_MAX_RESULTS_PER_QUERY
    cost_phase: str = "scout_disambiguation"

    def produce(self, scout_input: Mapping[str, Any]) -> Mapping[str, Any]:
        candidates = _authorized_candidates(scout_input)
        if not candidates:
            return {
                "scout_queries": [],
                "scout_execution_posture": "skipped_budget",
                "route_available": None,
            }

        request = ProviderCapabilityRequest(
            capability=AcquisitionCapability.DISCOVER,
            qualifier=DiscoverQualifier.LIGHTWEIGHT_DISAMBIGUATION,
            derivation_reason="authorized_scout_disambiguation",
        )
        decision = self.route(request, dict(self.available_providers))
        route_projection = _route_projection(decision)
        if decision.blocked or not decision.selected_provider:
            return {
                "scout_queries": [
                    _completed_query(candidate, status="blocked", provider=None)
                    for candidate in candidates
                ],
                "scout_execution_posture": "blocked",
                "route_available": False,
                "scout_route": route_projection,
            }

        provider = str(decision.selected_provider)
        max_results = _bounded_max_results(self.max_results_per_query)
        completed_queries: list[dict[str, Any]] = []
        organic_results: list[dict[str, Any]] = []
        for candidate in candidates:
            logical_call_id = _logical_call_id(self.cap_policy)
            provider_results = self.scout_search(
                provider=provider,
                query=str(candidate["safe_query_text"]),
                max_results=max_results,
                cost_accumulator=self.cost_accumulator,
                cost_phase=self.cost_phase,
                cap_policy=self.cap_policy,
                logical_call_id=logical_call_id,
                strict_failure=True,
            )
            completed_queries.append(
                _completed_query(candidate, status="executed", provider=provider)
            )
            organic_results.extend(
                _sanitize_provider_result(
                    item,
                    query_id=str(candidate["query_id"]),
                    related_dimension_ids=candidate["related_dimension_ids"],
                    position=index,
                )
                for index, item in enumerate(list(provider_results or ())[:max_results], start=1)
                if isinstance(item, Mapping)
            )

        return {
            "scout_queries": completed_queries,
            "organic_results": organic_results,
            "scout_execution_posture": "executed",
            "route_available": True,
            "scout_route": route_projection,
            "confidence_posture": "directional",
            "disambiguation_posture": "ordinary_provider_neutral",
        }


def build_ordinary_scout_disambiguation_adapter(
    *,
    available_providers: Mapping[str, object],
    cap_policy: RunCapPolicy | None,
    cost_accumulator: Any | None,
) -> OrdinaryScoutDisambiguationAdapter:
    """Build the ordinary bounded Scout adapter from run-local dependencies."""

    return OrdinaryScoutDisambiguationAdapter(
        available_providers=dict(available_providers),
        cap_policy=cap_policy,
        cost_accumulator=cost_accumulator,
    )


def _authorized_candidates(scout_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    budget = _mapping(scout_input.get("query_budget"))
    authorized = _non_negative_int(budget.get("authorized_query_count"))
    candidates: list[dict[str, Any]] = []
    for raw in _sequence(scout_input.get("candidate_queries"))[:authorized]:
        candidate = _mapping(raw)
        query_id = _text(candidate.get("query_id"), limit=160)
        query_text = _text(candidate.get("safe_query_text"), limit=360)
        dimension_ids = _text_list(candidate.get("related_dimension_ids"), limit=160)
        if not query_id or not query_text or not dimension_ids:
            raise ValueError("authorized Scout candidate is missing bounded identity")
        candidates.append(
            {
                "query_id": query_id,
                "safe_query_text": query_text,
                "query_kind": _text(candidate.get("query_kind"), limit=120)
                or "unknown_or_other",
                "priority": _positive_int(candidate.get("priority"), fallback=len(candidates) + 1),
                "related_dimension_ids": dimension_ids,
                "search_vertical": _text(candidate.get("search_vertical"), limit=80)
                or "search",
                "locale": _text(candidate.get("locale"), limit=80),
                "country": _text(candidate.get("country"), limit=80),
                "language": _text(candidate.get("language"), limit=80),
            }
        )
    return candidates


def _completed_query(
    candidate: Mapping[str, Any],
    *,
    status: str,
    provider: str | None,
) -> dict[str, Any]:
    return {
        "query_id": candidate["query_id"],
        "safe_query_text": candidate["safe_query_text"],
        "query_kind": candidate["query_kind"],
        "priority": candidate["priority"],
        "related_dimension_ids": list(candidate["related_dimension_ids"]),
        "execution_status": status,
        "search_vertical": candidate["search_vertical"],
        "provider_hint": provider or "provider_route_unavailable",
        "locale": candidate.get("locale"),
        "country": candidate.get("country"),
        "language": candidate.get("language"),
        "not_live": status != "executed",
        "provider_payload_retained": False,
        "fetch_read_retrieval_behavior_changed": False,
        "source_obligation_satisfied": False,
    }


def _sanitize_provider_result(
    item: Mapping[str, Any],
    *,
    query_id: str,
    related_dimension_ids: Sequence[str],
    position: int,
) -> dict[str, Any]:
    """Copy only the bounded directional fields accepted by Scout runtime."""

    return {
        "query_id": query_id,
        "related_dimension_ids": list(related_dimension_ids),
        "title": _text(item.get("title"), limit=320),
        "link": _text(item.get("url") or item.get("link"), limit=600),
        "snippet": _text(item.get("snippet"), limit=700),
        "domain": _text(item.get("domain"), limit=240),
        "position": _positive_int(item.get("position"), fallback=position),
        "date": _text(item.get("date"), limit=120),
        "confidence_posture": "directional",
    }


def _route_projection(decision: ProviderRouteDecision) -> dict[str, Any]:
    return {
        "adapter_schema_version": ORDINARY_SCOUT_DISAMBIGUATION_ADAPTER_SCHEMA_VERSION,
        "capability": decision.capability.value,
        "qualifier": decision.qualifier.value if decision.qualifier is not None else None,
        "selected_provider": decision.selected_provider,
        "operation": decision.operation,
        "variant": decision.variant,
        "fidelity": decision.fidelity.value,
        "availability_posture": decision.availability_posture,
        "adapter_posture": decision.adapter_posture,
        "route_available": not decision.blocked and bool(decision.selected_provider),
        "returned_material_class": decision.returned_material_class,
        "authority_posture": decision.authority_posture,
    }


def _logical_call_id(cap_policy: RunCapPolicy | None) -> str | None:
    if cap_policy is None or not cap_policy.bounded:
        return None
    return cap_policy.new_logical_call_id("scout_disambiguation")


def _bounded_max_results(value: int) -> int:
    try:
        return max(1, min(int(value), ORDINARY_SCOUT_MAX_RESULTS_PER_QUERY))
    except (TypeError, ValueError):
        return ORDINARY_SCOUT_MAX_RESULTS_PER_QUERY


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _text(value: Any, *, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _text_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    for item in value:
        text = _text(item, limit=limit)
        if text and text not in out:
            out.append(text)
    return out


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _positive_int(value: Any, *, fallback: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return fallback


__all__ = [
    "ORDINARY_SCOUT_DISAMBIGUATION_ADAPTER_SCHEMA_VERSION",
    "ORDINARY_SCOUT_MAX_RESULTS_PER_QUERY",
    "OrdinaryScoutDisambiguationAdapter",
    "build_ordinary_scout_disambiguation_adapter",
]
