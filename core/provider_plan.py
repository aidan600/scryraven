"""Run-local records for completed provider-capability routing decisions.

ProviderPlan remains a mechanical authority boundary: ``core.routing`` derives
and selects, while this module records and projects the completed decision for
scheduler and dispatch consumers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

from core.routing import (
    PROVIDER_NAMES,
    DiscoverQualifier,
    ProviderAvailability,
    ProviderRouteDecision,
    derive_provider_capability_request,
    route_provider_capability,
)
from core.routing import (
    merge_search_provider_overrides as routing_merge_search_provider_overrides,
)
from core.routing import select_providers as routing_select_providers


@dataclass(frozen=True)
class ProviderAvailabilitySnapshot:
    """Boolean-only availability snapshot with a retained three-key projection."""

    tavily: bool = False
    linkup: bool = False
    exa: bool = False
    serper: bool = False
    brave: bool = False

    @classmethod
    def from_mapping(cls, values: Mapping[str, object] | None) -> "ProviderAvailabilitySnapshot":
        availability = ProviderAvailability.from_mapping(values)
        return cls(**availability.to_mapping())

    def to_available_keys(self) -> dict[str, bool]:
        """Return the retained three-provider compatibility projection."""

        return {"tavily": self.tavily, "linkup": self.linkup, "exa": self.exa}

    def to_capability_available_keys(self) -> dict[str, bool]:
        return {provider: bool(getattr(self, provider)) for provider in PROVIDER_NAMES}

    def to_trace(self) -> dict[str, bool]:
        """Return the retained compatibility trace projection."""

        return self.to_available_keys()


@dataclass(frozen=True)
class ProviderPlanRecord:
    """One completed provider-capability decision for a runtime role."""

    role: str
    providers: tuple[str, ...]
    route_decision: ProviderRouteDecision
    search_depth: str | None = None
    provider_override: tuple[str, ...] | None = None
    availability: ProviderAvailabilitySnapshot = field(default_factory=ProviderAvailabilitySnapshot)
    selection_inputs: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.providers) > 1:
            raise ValueError("ProviderPlanRecord permits at most one active provider")
        if self.providers != self.route_decision.providers():
            raise ValueError("ProviderPlanRecord provider projection must match route decision")

    def providers_list(self) -> list[str]:
        return list(self.providers)

    @property
    def provider_variant(self) -> str | None:
        return self.route_decision.variant

    def to_trace(self) -> dict[str, object]:
        trace: dict[str, object] = {
            "role": self.role,
            "providers": list(self.providers),
            "available_keys": self.availability.to_trace(),
            "provider_availability": self.availability.to_capability_available_keys(),
            "selection_inputs": dict(self.selection_inputs),
            "route_decision": self.route_decision.to_trace(),
        }
        if self.search_depth is not None:
            trace["search_depth"] = self.search_depth
        if self.provider_override is not None:
            trace["provider_override"] = list(self.provider_override)
        return trace


@dataclass
class ProviderPlan:
    """Run-local holder for completed provider-capability route decisions."""

    availability: ProviderAvailabilitySnapshot
    selector_available_keys: Mapping[str, bool] | None = None
    records: list[ProviderPlanRecord] = field(default_factory=list)

    @classmethod
    def from_available_keys(cls, available_keys: Mapping[str, object]) -> "ProviderPlan":
        normalized = {
            provider: bool(available_keys.get(provider)) for provider in PROVIDER_NAMES if provider in available_keys
        }
        return cls(
            availability=ProviderAvailabilitySnapshot.from_mapping(available_keys),
            selector_available_keys=normalized,
        )

    def available_keys(self) -> dict[str, bool]:
        return self.availability.to_available_keys()

    def capability_available_keys(self) -> dict[str, bool]:
        return self.availability.to_capability_available_keys()

    def _selector_available_keys(self) -> dict[str, bool]:
        return dict(self.selector_available_keys or self.capability_available_keys())

    def _route(
        self,
        *,
        query_type: str | None,
        intent: str,
        complexity: str,
        report_type: str | None,
        is_academic: bool,
        suppress_tavily: bool,
        include_domains: Sequence[str],
        exclude_domains: Sequence[str],
        override: Sequence[str] | None,
        override_is_user: bool,
        premium_search_escalation: bool,
        discover_qualifier: DiscoverQualifier | str | None = None,
        scrutineer_deep_authorized: bool = False,
        select_provider_list: Callable[..., list[str]] = routing_select_providers,
    ) -> ProviderRouteDecision:
        request = derive_provider_capability_request(
            query_type=query_type,
            intent=intent,
            is_academic=is_academic,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            discover_qualifier=discover_qualifier,
        )
        preferences = list(override) if override is not None else None
        override_posture = "user_ordered_preferences" if override_is_user else "internal_ordered_preferences"
        if select_provider_list is not routing_select_providers:
            preferences = select_provider_list(
                query_type,
                intent,
                complexity,
                self._selector_available_keys(),
                report_type=report_type,
                is_academic=is_academic,
                suppress_tavily=suppress_tavily,
                override=preferences,
            )
            override_posture = "compatibility_selector_preferences"
        return route_provider_capability(
            request,
            self.capability_available_keys(),
            override=preferences,
            override_posture=(override_posture if preferences is not None else "none"),
            suppress_tavily=suppress_tavily,
            scrutineer_deep_authorized=scrutineer_deep_authorized,
        )

    def _append_record(
        self,
        *,
        role: str,
        decision: ProviderRouteDecision,
        search_depth: str | None,
        provider_override: Sequence[str] | None,
        selection_inputs: Mapping[str, object],
    ) -> ProviderPlanRecord:
        record = ProviderPlanRecord(
            role=role,
            providers=decision.providers(),
            route_decision=decision,
            search_depth=search_depth,
            provider_override=(tuple(provider_override) if provider_override is not None else None),
            availability=self.availability,
            selection_inputs=selection_inputs,
        )
        self.records.append(record)
        return record

    def record_main_retrieval(
        self,
        *,
        query_type: str,
        intent: str,
        complexity: str,
        report_type: str,
        is_academic: bool,
        suppress_tavily: bool,
        base_search_depth: str | None,
        iteration: int,
        primary_override: Sequence[str] | None,
        scout_override: Sequence[str] | None,
        choose_search_depth: Callable[[str, str | None, int], str],
        include_domains: Sequence[str] = (),
        exclude_domains: Sequence[str] = (),
        merge_provider_overrides: Callable[..., list[str] | None] = routing_merge_search_provider_overrides,
        select_provider_list: Callable[..., list[str]] = routing_select_providers,
    ) -> ProviderPlanRecord:
        available_keys = self._selector_available_keys()
        search_depth = choose_search_depth(complexity, base_search_depth, iteration)
        merged_override = merge_provider_overrides(
            list(primary_override) if primary_override else None,
            list(scout_override) if scout_override else None,
            available_keys,
            complexity=complexity,
        )
        decision = self._route(
            query_type=query_type,
            intent=intent,
            complexity=complexity,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            override=merged_override,
            override_is_user=bool(primary_override),
            premium_search_escalation=False,
            select_provider_list=select_provider_list,
        )
        return self._append_record(
            role="main_retrieval",
            decision=decision,
            search_depth=search_depth,
            provider_override=merged_override,
            selection_inputs={
                "query_type": query_type,
                "intent": intent,
                "complexity": complexity,
                "report_type": report_type,
                "is_academic": is_academic,
                "suppress_tavily": suppress_tavily,
                "base_search_depth": base_search_depth,
                "iteration": iteration,
                "primary_override": list(primary_override) if primary_override else None,
                "scout_override": list(scout_override) if scout_override else None,
                "include_domains": list(include_domains),
                "exclude_domains": list(exclude_domains),
            },
        )

    def record_continuation(
        self,
        *,
        role: str,
        query_type: str,
        intent: str,
        complexity: str,
        report_type: str,
        is_academic: bool,
        suppress_tavily: bool,
        override: Sequence[str] | None,
        override_is_user: bool,
        premium_search_escalation: bool = False,
        include_domains: Sequence[str] = (),
        exclude_domains: Sequence[str] = (),
        select_provider_list: Callable[..., list[str]] = routing_select_providers,
    ) -> ProviderPlanRecord:
        decision = self._route(
            query_type=query_type,
            intent=intent,
            complexity=complexity,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            override=override,
            override_is_user=override_is_user,
            premium_search_escalation=premium_search_escalation,
            select_provider_list=select_provider_list,
        )
        return self._append_record(
            role=role,
            decision=decision,
            search_depth=None,
            provider_override=override,
            selection_inputs={
                "query_type": query_type,
                "intent": intent,
                "complexity": complexity,
                "report_type": report_type,
                "is_academic": is_academic,
                "suppress_tavily": suppress_tavily,
                "override": list(override) if override is not None else None,
                "override_is_user": override_is_user,
                "premium_search_escalation": premium_search_escalation,
                "include_domains": list(include_domains),
                "exclude_domains": list(exclude_domains),
            },
        )

    def record_supplemental_retrieval(
        self,
        *,
        query_type: str | None,
        intent: str,
        complexity: str,
        report_type: str | None,
        is_academic: bool,
        suppress_tavily: bool,
        base_search_depth: str,
        choose_search_depth: Callable[[str, str], str],
        include_domains: Sequence[str] = (),
        exclude_domains: Sequence[str] = (),
        select_provider_list: Callable[..., Sequence[str]] = routing_select_providers,
    ) -> ProviderPlanRecord:
        search_depth = choose_search_depth(complexity, base_search_depth)
        decision = self._route(
            query_type=query_type,
            intent=intent,
            complexity=complexity,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            override=None,
            override_is_user=False,
            premium_search_escalation=False,
            select_provider_list=select_provider_list,
        )
        return self._append_record(
            role="supplemental_search",
            decision=decision,
            search_depth=search_depth,
            provider_override=None,
            selection_inputs={
                "query_type": query_type,
                "intent": intent,
                "complexity": complexity,
                "report_type": report_type,
                "is_academic": is_academic,
                "suppress_tavily": suppress_tavily,
                "base_search_depth": base_search_depth,
                "override": None,
                "include_domains": list(include_domains),
                "exclude_domains": list(exclude_domains),
            },
        )

    def record_scrutineer_remediation(
        self,
        *,
        query_type: str | None,
        intent: str,
        complexity: str,
        report_type: str | None,
        is_academic: bool,
        suppress_tavily: bool,
        search_depth: str,
        include_domains: Sequence[str] = (),
        exclude_domains: Sequence[str] = (),
        select_provider_list: Callable[..., Sequence[str]] = routing_select_providers,
    ) -> ProviderPlanRecord:
        decision = self._route(
            query_type=query_type,
            intent=intent,
            complexity=complexity,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            override=None,
            override_is_user=False,
            premium_search_escalation=False,
            scrutineer_deep_authorized=True,
            select_provider_list=select_provider_list,
        )
        return self._append_record(
            role="scrutineer_remediation",
            decision=decision,
            search_depth=search_depth,
            provider_override=None,
            selection_inputs={
                "query_type": query_type,
                "intent": intent,
                "complexity": complexity,
                "report_type": report_type,
                "is_academic": is_academic,
                "suppress_tavily": suppress_tavily,
                "search_depth": search_depth,
                "override": None,
                "include_domains": list(include_domains),
                "exclude_domains": list(exclude_domains),
                "scrutineer_deep_authorized": True,
            },
        )

    def to_trace(self) -> dict[str, object]:
        return {
            "available_keys": self.availability.to_trace(),
            "provider_availability": self.capability_available_keys(),
            "records": [record.to_trace() for record in self.records],
        }
