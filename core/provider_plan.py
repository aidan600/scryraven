"""Run-local provider/depth plan facts for already-existing routing decisions.

ProviderPlan is an authority-boundary seed: it records and projects selected
provider/depth facts for a run while delegating routing and depth choices to the
existing selectors supplied by the orchestrator/runtime.  It does not execute
search, call models, inspect secrets, rank evidence, or invent provider policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

from core.routing import (
    merge_search_provider_overrides as routing_merge_search_provider_overrides,
)
from core.routing import select_providers as routing_select_providers


@dataclass(frozen=True)
class ProviderAvailabilitySnapshot:
    """Boolean availability snapshot for the existing search-provider keys."""

    tavily: bool = False
    linkup: bool = False
    exa: bool = False

    @classmethod
    def from_mapping(cls, values: Mapping[str, object] | None) -> "ProviderAvailabilitySnapshot":
        source = values or {}
        return cls(
            tavily=bool(source.get("tavily")),
            linkup=bool(source.get("linkup")),
            exa=bool(source.get("exa")),
        )

    def to_available_keys(self) -> dict[str, bool]:
        """Return the existing selector input shape, preserving key order."""

        return {"tavily": self.tavily, "linkup": self.linkup, "exa": self.exa}

    def to_trace(self) -> dict[str, bool]:
        """Return a JSON-safe projection of provider availability."""

        return self.to_available_keys()


@dataclass(frozen=True)
class ProviderPlanRecord:
    """One consumed provider/depth selection record for a runtime role."""

    role: str
    providers: tuple[str, ...]
    search_depth: str | None = None
    provider_override: tuple[str, ...] | None = None
    availability: ProviderAvailabilitySnapshot = field(
        default_factory=ProviderAvailabilitySnapshot
    )
    selection_inputs: Mapping[str, object] = field(default_factory=dict)

    def providers_list(self) -> list[str]:
        return list(self.providers)

    def to_trace(self) -> dict[str, object]:
        trace: dict[str, object] = {
            "role": self.role,
            "providers": list(self.providers),
            "available_keys": self.availability.to_trace(),
            "selection_inputs": dict(self.selection_inputs),
        }
        if self.search_depth is not None:
            trace["search_depth"] = self.search_depth
        if self.provider_override is not None:
            trace["provider_override"] = list(self.provider_override)
        return trace


@dataclass
class ProviderPlan:
    """Run-local holder for provider/depth facts selected by existing policy."""

    availability: ProviderAvailabilitySnapshot
    selector_available_keys: Mapping[str, object] | None = None
    records: list[ProviderPlanRecord] = field(default_factory=list)

    @classmethod
    def from_available_keys(cls, available_keys: Mapping[str, object]) -> "ProviderPlan":
        return cls(
            availability=ProviderAvailabilitySnapshot.from_mapping(available_keys),
            selector_available_keys=dict(available_keys),
        )

    def available_keys(self) -> dict[str, bool]:
        return self.availability.to_available_keys()

    def _selector_available_keys(self) -> dict[str, object]:
        return dict(self.selector_available_keys or self.available_keys())

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
        merge_provider_overrides: Callable[..., list[str] | None] = routing_merge_search_provider_overrides,
        select_provider_list: Callable[..., list[str]] = routing_select_providers,
    ) -> ProviderPlanRecord:
        """Record the main-loop provider/depth selection and return consumed facts.

        The call shape intentionally mirrors the previous orchestrator-local path:
        choose depth, merge user/scout overrides, then select providers.
        """

        available_keys = self._selector_available_keys()
        search_depth = choose_search_depth(complexity, base_search_depth, iteration)
        merged_override = merge_provider_overrides(
            list(primary_override) if primary_override else None,
            list(scout_override) if scout_override else None,
            available_keys,
            complexity=complexity,
        )
        providers = select_provider_list(
            query_type,
            intent,
            complexity,
            available_keys,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            override=merged_override,
        )
        record = ProviderPlanRecord(
            role="main_retrieval",
            providers=tuple(providers),
            search_depth=search_depth,
            provider_override=tuple(merged_override) if merged_override is not None else None,
            availability=self.availability,
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
            },
        )
        self.records.append(record)
        return record

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
        select_provider_list: Callable[..., list[str]] = routing_select_providers,
    ) -> ProviderPlanRecord:
        """Record a continuation provider-input selection and return consumed facts.

        This delegates to the existing provider selector with the same call shape
        as the orchestrator-local Scout/Expander continuation paths.  It records
        the provider inputs that will become the next pass's forced component
        providers; it does not merge main-loop overrides or choose depth.
        """

        available_keys = self._selector_available_keys()
        providers = select_provider_list(
            query_type,
            intent,
            complexity,
            available_keys,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            override=list(override) if override is not None else None,
            override_is_user=override_is_user,
            premium_search_escalation=premium_search_escalation,
        )
        record = ProviderPlanRecord(
            role=role,
            providers=tuple(providers),
            provider_override=tuple(override) if override is not None else None,
            availability=self.availability,
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
            },
        )
        self.records.append(record)
        return record

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
        select_provider_list: Callable[..., Sequence[str]] = routing_select_providers,
    ) -> ProviderPlanRecord:
        """Record supplemental-search provider/depth facts selected by existing policy."""

        available_keys = self._selector_available_keys()
        search_depth = choose_search_depth(complexity, base_search_depth)
        providers = select_provider_list(
            query_type,
            intent,
            complexity,
            available_keys,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            override=None,
        )
        record = ProviderPlanRecord(
            role="supplemental_search",
            providers=tuple(providers),
            search_depth=search_depth,
            availability=self.availability,
            selection_inputs={
                "query_type": query_type,
                "intent": intent,
                "complexity": complexity,
                "report_type": report_type,
                "is_academic": is_academic,
                "suppress_tavily": suppress_tavily,
                "base_search_depth": base_search_depth,
                "override": None,
            },
        )
        self.records.append(record)
        return record

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
        select_provider_list: Callable[..., Sequence[str]] = routing_select_providers,
    ) -> ProviderPlanRecord:
        """Record Scrutineer remediation provider/depth facts selected by existing policy."""

        available_keys = self._selector_available_keys()
        providers = select_provider_list(
            query_type,
            intent,
            complexity,
            available_keys,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            override=None,
        )
        record = ProviderPlanRecord(
            role="scrutineer_remediation",
            providers=tuple(providers),
            search_depth=search_depth,
            availability=self.availability,
            selection_inputs={
                "query_type": query_type,
                "intent": intent,
                "complexity": complexity,
                "report_type": report_type,
                "is_academic": is_academic,
                "suppress_tavily": suppress_tavily,
                "search_depth": search_depth,
                "override": None,
            },
        )
        self.records.append(record)
        return record

    def to_trace(self) -> dict[str, object]:
        """Return a JSON-safe trace/projection for diagnostics."""

        return {
            "available_keys": self.availability.to_trace(),
            "records": [record.to_trace() for record in self.records],
        }
