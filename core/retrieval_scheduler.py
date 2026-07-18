"""Active retrieval scheduling authority for already-authorized retrieval work.

The scheduler consumes QueryPlan/ProviderPlan/controller outputs that already
exist and turns them into runtime actions. It does not generate queries, choose
providers, choose search depth, execute search, rank evidence, or inspect
prompt/model behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import Enum
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from core.run_kernel import (
    MAIN_RETRIEVAL_STAGE,
    ActionType,
    AuthorizedAction,
    ObservationType,
    validate_authorized_action,
)


class RetrievalScheduleReason(str, Enum):
    MAIN_PASS_SCHEDULED = "main_pass_scheduled"
    MAIN_PASS_BLOCKED = "main_pass_blocked"
    CONTINUATION_SCHEDULED = "continuation_scheduled"
    CONTINUATION_BLOCKED = "continuation_blocked"
    WEAK_CORPUS_RECOVERY_SCHEDULED = "weak_corpus_recovery_scheduled"
    WEAK_CORPUS_RECOVERY_BLOCKED = "weak_corpus_recovery_blocked"
    RECORDED_DISCOVERY_SCHEDULED = "recorded_discovery_scheduled"


@dataclass(frozen=True, slots=True)
class RetrievalScheduleInput:
    stage: str
    current_queries: Sequence[str]
    iteration: int | None = None
    provider_role: str = "main_retrieval"
    search_depth: str | None = None
    providers: Sequence[str] = ()
    provider_record: Any | None = None
    continuation_authorized: bool = True
    recovery_active: bool = False
    reason: RetrievalScheduleReason | str | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class RetrievalScheduledAction:
    stage: str
    current_queries: tuple[str, ...]
    iteration: int | None
    provider_role: str
    providers: tuple[str, ...]
    search_depth: str
    provider_operation: str | None
    provider_variant: str | None
    provider_output_type: str | None
    route_blocked: bool
    force_component_providers: tuple[str, ...]
    continue_retrieval: bool
    recovery_active: bool
    reason: RetrievalScheduleReason
    metadata: Mapping[str, Any]
    retrieval_action_ref: Mapping[str, Any] = field(default_factory=dict)
    query_plan_ref: Mapping[str, Any] = field(default_factory=dict)
    query_plan_item_refs: tuple[Mapping[str, Any], ...] = ()
    provider_plan_ref: Mapping[str, Any] = field(default_factory=dict)
    provider_plan_record_ref: Mapping[str, Any] = field(default_factory=dict)
    provider_route_ref: Mapping[str, Any] = field(default_factory=dict)
    provider_capability: str | None = None
    provider_qualifier: str | None = None

    def queries_list(self) -> list[str]:
        return list(self.current_queries)

    def providers_list(self) -> list[str]:
        return list(self.providers)

    def force_component_providers_list(self) -> list[str]:
        return list(self.force_component_providers)

    def to_trace(self) -> dict[str, Any]:
        trace = {
            "stage": self.stage,
            "current_queries": list(self.current_queries),
            "iteration": self.iteration,
            "provider_role": self.provider_role,
            "providers": list(self.providers),
            "search_depth": self.search_depth,
            "provider_operation": self.provider_operation,
            "provider_variant": self.provider_variant,
            "provider_output_type": self.provider_output_type,
            "route_blocked": self.route_blocked,
            "force_component_providers": list(self.force_component_providers),
            "continue_retrieval": self.continue_retrieval,
            "recovery_active": self.recovery_active,
            "reason": self.reason.value,
            "metadata": dict(self.metadata),
        }
        if self.retrieval_action_ref:
            trace["retrieval_action_ref"] = dict(self.retrieval_action_ref)
        if self.query_plan_ref:
            trace["query_plan_ref"] = dict(self.query_plan_ref)
        if self.query_plan_item_refs:
            trace["query_plan_item_refs"] = [
                dict(item_ref) for item_ref in self.query_plan_item_refs
            ]
        if self.provider_plan_ref:
            trace["provider_plan_ref"] = dict(self.provider_plan_ref)
        if self.provider_plan_record_ref:
            trace["provider_plan_record_ref"] = dict(
                self.provider_plan_record_ref
            )
        if self.provider_route_ref:
            trace["provider_route_ref"] = dict(self.provider_route_ref)
        if self.provider_capability is not None:
            trace["provider_capability"] = self.provider_capability
        if self.provider_qualifier is not None:
            trace["provider_qualifier"] = self.provider_qualifier
        return trace


def main_retrieval_action_values(
    action: RetrievalScheduledAction,
) -> tuple[list[str], str, list[str], list[str]]:
    """Return the legacy loop locals consumed after main-pass scheduling."""

    return (
        action.queries_list(),
        action.search_depth,
        action.providers_list(),
        action.force_component_providers_list(),
    )


def continuation_action_values(
    action: RetrievalScheduledAction,
) -> tuple[list[str], list[str]]:
    """Return legacy continuation locals without rescheduling in the orchestrator."""

    return action.queries_list(), action.force_component_providers_list()


def _require_scope(scope: Mapping[str, Any], names: Sequence[str]) -> dict[str, Any]:
    missing = [name for name in names if name not in scope]
    if missing:
        raise KeyError(f"retrieval scheduler scope missing keys: {missing}")
    return {name: scope[name] for name in names}


def _clean_queries(queries: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(query) for query in queries if str(query).strip())


def _providers_from_input(schedule_input: RetrievalScheduleInput) -> tuple[str, ...]:
    if schedule_input.provider_record is not None:
        return tuple(schedule_input.provider_record.providers_list())
    return tuple(str(provider) for provider in schedule_input.providers)


def _depth_from_input(schedule_input: RetrievalScheduleInput) -> str:
    depth = schedule_input.search_depth
    if schedule_input.provider_record is not None:
        depth = schedule_input.provider_record.search_depth or depth
    return str(depth or "basic")


def _route_fields(
    provider_record: Any | None,
) -> tuple[str | None, str | None, str | None, bool]:
    decision = getattr(provider_record, "route_decision", None)
    if decision is None:
        return None, None, None, False
    return (
        getattr(decision, "operation", None),
        getattr(decision, "variant", None),
        getattr(decision, "output_type", None),
        bool(getattr(decision, "blocked", False)),
    )


def _provider_record_metadata(provider_record: Any | None) -> dict[str, Any]:
    if provider_record is None:
        return {}
    trace = provider_record.to_trace() if hasattr(provider_record, "to_trace") else {}
    role = getattr(provider_record, "role", None)
    return {
        "provider_record_role": str(role) if role is not None else None,
        "provider_record": trace,
    }


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    enum_value = getattr(value, "value", value)
    text = str(enum_value).strip()
    return text or None


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def schedule_recorded_discovery_dispatch(
    *,
    stage: str,
    current_queries: Sequence[str],
    iteration: int | None,
    provider_role: str,
    search_depth: str,
    provider_record: Any,
    authority_source: str,
    authority_ref_digest: str,
) -> RetrievalScheduledAction:
    """Schedule an already-approved non-main DISCOVER dispatch.

    The caller supplies query, depth, and provider decisions from their
    existing owners.  This helper only records the mechanical action.
    """

    operation, variant, output_type, route_blocked = _route_fields(
        provider_record
    )
    queries = _clean_queries(current_queries)
    providers = tuple(getattr(provider_record, "providers", ()))
    if not queries:
        raise ValueError("recorded discovery dispatch requires queries")
    if not providers:
        raise ValueError("recorded discovery dispatch requires a provider route")
    route = getattr(provider_record, "route_decision", None)
    capability = _enum_value(getattr(route, "capability", None))
    qualifier = _enum_value(getattr(route, "qualifier", None))
    if capability != "DISCOVER":
        raise ValueError("recorded discovery requires DISCOVER capability")
    if qualifier == "lightweight_disambiguation" or "serper" in {
        provider.casefold() for provider in providers
    }:
        raise ValueError(
            "lightweight-disambiguation/Serper cannot enter ordinary discovery"
        )
    return RetrievalScheduledAction(
        stage=str(stage),
        current_queries=queries,
        iteration=iteration,
        provider_role=str(provider_role),
        providers=providers,
        search_depth=str(search_depth),
        provider_operation=operation,
        provider_variant=variant,
        provider_output_type=output_type,
        route_blocked=route_blocked,
        force_component_providers=(),
        continue_retrieval=not route_blocked,
        recovery_active=provider_role in {
            "source_class_recovery",
            "conflict_resolution",
        },
        reason=RetrievalScheduleReason.RECORDED_DISCOVERY_SCHEDULED,
        metadata={
            **_provider_record_metadata(provider_record),
            "authority_source": str(authority_source),
            "authority_ref_digest": str(authority_ref_digest),
        },
    )


def bind_recorded_discovery_lineage(
    scheduled_action: RetrievalScheduledAction,
    *,
    query_plan: Any,
    query_plan_item_refs: Sequence[Mapping[str, Any]],
    provider_plan: Any,
    provider_record: Any,
    authority_ref_digest: str,
) -> RetrievalScheduledAction:
    """Attach exact QueryPlan/ProviderPlan refs to one recorded action."""

    item_refs = tuple(dict(item) for item in query_plan_item_refs)
    queries = tuple(str(item.get("authorized_query") or "") for item in item_refs)
    if not item_refs or queries != scheduled_action.current_queries:
        raise ValueError(
            "recorded discovery queries do not match exact QueryPlan items"
        )
    if tuple(getattr(provider_record, "providers", ())) != (
        scheduled_action.providers
    ):
        raise ValueError(
            "recorded discovery providers do not match ProviderPlan record"
        )
    route = getattr(provider_record, "route_decision", None)
    capability = _enum_value(getattr(route, "capability", None))
    qualifier = _enum_value(getattr(route, "qualifier", None))
    if capability != "DISCOVER":
        raise ValueError("recorded discovery requires DISCOVER capability")
    if qualifier == "lightweight_disambiguation" or "serper" in {
        provider.casefold() for provider in scheduled_action.providers
    }:
        raise ValueError(
            "lightweight-disambiguation/Serper cannot enter ordinary discovery"
        )
    action_basis = {
        "stage": scheduled_action.stage,
        "queries": list(scheduled_action.current_queries),
        "iteration": scheduled_action.iteration,
        "provider_role": scheduled_action.provider_role,
        "providers": list(scheduled_action.providers),
        "search_depth": scheduled_action.search_depth,
        "provider_operation": scheduled_action.provider_operation,
        "provider_variant": scheduled_action.provider_variant,
        "provider_output_type": scheduled_action.provider_output_type,
        "provider_plan_record_ref": provider_record.to_ref(),
        "provider_route_ref": provider_record.route_ref(),
        "authority_ref_digest": authority_ref_digest,
    }
    scheduled_digest = _canonical_digest(action_basis)
    return replace(
        scheduled_action,
        retrieval_action_ref={
            "action_id": f"scheduled-discovery:{scheduled_digest[:32]}",
            "action_type": "scheduled_discovery_dispatch",
            "stage": scheduled_action.stage,
            # Scheduler-owned actions are not RunKernel-sequenced.  Zero is the
            # existing ref contract's explicit unsequenced value.
            "sequence": 0,
        },
        query_plan_ref=query_plan.to_ref(),
        query_plan_item_refs=item_refs,
        provider_plan_ref=provider_plan.to_ref(),
        provider_plan_record_ref=provider_record.to_ref(),
        provider_route_ref=provider_record.route_ref(),
        provider_capability=capability,
        provider_qualifier=qualifier,
    )


def _bind_main_retrieval_lineage(
    scheduled_action: RetrievalScheduledAction,
    *,
    kernel_action: AuthorizedAction,
    scope: Mapping[str, Any],
) -> RetrievalScheduledAction:
    """Bind ordinary main-pass authority refs without affecting legacy callers."""

    query_authority = scope.get("query_authority")
    if query_authority is None:
        # Compatibility for direct historical scheduler callers. The ordinary
        # product path always supplies QueryPlanRuntimeAdapter in its scope.
        return scheduled_action
    query_plan = getattr(query_authority, "plan", None)
    if query_plan is None or not hasattr(query_plan, "execution_item_refs"):
        raise ValueError("ordinary main retrieval requires QueryPlan execution refs")
    iteration = scheduled_action.iteration
    if iteration is None:
        raise ValueError("ordinary main retrieval requires an iteration")
    item_refs = tuple(query_plan.execution_item_refs(iteration))
    authorized_queries = tuple(
        str(item_ref.get("authorized_query") or "") for item_ref in item_refs
    )
    if not item_refs or authorized_queries != scheduled_action.current_queries:
        raise ValueError(
            "ordinary main retrieval queries must match exact QueryPlan execution items"
        )
    if not hasattr(query_plan, "to_ref"):
        raise ValueError("ordinary main retrieval requires a canonical QueryPlan ref")

    provider_plan = scope.get("provider_plan")
    records = tuple(getattr(provider_plan, "records", ()))
    if provider_plan is None or not records:
        raise ValueError("ordinary main retrieval requires a ProviderPlan record")
    provider_record = records[-1]
    if tuple(getattr(provider_record, "providers", ())) != scheduled_action.providers:
        raise ValueError("scheduled providers do not match latest ProviderPlan record")
    if not all(
        hasattr(owner, method)
        for owner, method in (
            (provider_plan, "to_ref"),
            (provider_record, "to_ref"),
            (provider_record, "route_ref"),
        )
    ):
        raise ValueError("ordinary main retrieval requires canonical provider refs")

    route_decision = getattr(provider_record, "route_decision", None)
    capability = _enum_value(getattr(route_decision, "capability", None))
    qualifier = _enum_value(getattr(route_decision, "qualifier", None))
    if capability != "DISCOVER":
        raise ValueError("ordinary main retrieval requires DISCOVER capability")

    return replace(
        scheduled_action,
        retrieval_action_ref={
            "action_id": kernel_action.action_id,
            "action_type": kernel_action.action_type.value,
            "stage": kernel_action.stage,
            "sequence": kernel_action.sequence,
        },
        query_plan_ref=query_plan.to_ref(),
        query_plan_item_refs=item_refs,
        provider_plan_ref=provider_plan.to_ref(),
        provider_plan_record_ref=provider_record.to_ref(),
        provider_route_ref=provider_record.route_ref(),
        provider_capability=capability,
        provider_qualifier=qualifier,
    )


def schedule_main_retrieval_action(
    schedule_input: RetrievalScheduleInput,
) -> RetrievalScheduledAction:
    """Schedule one main-loop retrieval pass from consumed QueryPlan/ProviderPlan facts."""

    providers = _providers_from_input(schedule_input)
    operation, variant, output_type, route_blocked = _route_fields(schedule_input.provider_record)
    return RetrievalScheduledAction(
        stage=schedule_input.stage,
        current_queries=_clean_queries(schedule_input.current_queries),
        iteration=schedule_input.iteration,
        provider_role=schedule_input.provider_role,
        providers=providers,
        search_depth=_depth_from_input(schedule_input),
        provider_operation=operation,
        provider_variant=variant,
        provider_output_type=output_type,
        route_blocked=route_blocked,
        force_component_providers=(),
        continue_retrieval=bool(schedule_input.current_queries) and bool(providers),
        recovery_active=bool(schedule_input.recovery_active),
        reason=(
            RetrievalScheduleReason.MAIN_PASS_BLOCKED if route_blocked else RetrievalScheduleReason.MAIN_PASS_SCHEDULED
        ),
        metadata={
            **_provider_record_metadata(schedule_input.provider_record),
            **dict(schedule_input.metadata or {}),
        },
    )


def schedule_main_retrieval_from_provider_record(
    *,
    current_queries: Sequence[str],
    iteration: int,
    provider_role: str,
    provider_record: Any,
    recovery_active: bool,
    force_component_providers: Sequence[str] | None = None,
) -> RetrievalScheduledAction:
    """Schedule a main-loop pass from QueryPlan queries and a ProviderPlan record."""

    return schedule_main_retrieval_action(
        RetrievalScheduleInput(
            stage="main_retrieval",
            current_queries=current_queries,
            iteration=iteration,
            provider_role=provider_role,
            provider_record=provider_record,
            recovery_active=recovery_active,
            metadata={
                "force_component_providers_consumed": list(force_component_providers or ()),
            },
        )
    )


def schedule_main_retrieval_with_provider_plan(
    *,
    provider_plan: Any,
    query_type: str,
    intent: str,
    complexity: str,
    report_type: str,
    is_academic: bool,
    suppress_tavily: bool,
    base_search_depth: str | None,
    iteration: int,
    primary_override: Sequence[str] | None,
    force_component_providers: Sequence[str],
    current_queries: Sequence[str],
    recovery_active: bool,
    choose_search_depth: Callable[[str, str | None, int], str],
    include_domains: Sequence[str] = (),
    exclude_domains: Sequence[str] = (),
    merge_provider_overrides: Callable[..., list[str] | None] | None = None,
    select_provider_list: Callable[..., list[str]] | None = None,
) -> RetrievalScheduledAction:
    """Record main-loop ProviderPlan facts and schedule the consumed action."""

    forced = list(force_component_providers)
    selector_kwargs: dict[str, Any] = {}
    if merge_provider_overrides is not None:
        selector_kwargs["merge_provider_overrides"] = merge_provider_overrides
    if select_provider_list is not None:
        selector_kwargs["select_provider_list"] = select_provider_list
    provider_record = provider_plan.record_main_retrieval(
        query_type=query_type,
        intent=intent,
        complexity=complexity,
        report_type=report_type,
        is_academic=is_academic,
        suppress_tavily=suppress_tavily,
        base_search_depth=base_search_depth,
        iteration=iteration,
        primary_override=primary_override,
        scout_override=forced if forced else None,
        choose_search_depth=choose_search_depth,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        **selector_kwargs,
    )
    return schedule_main_retrieval_from_provider_record(
        current_queries=current_queries,
        iteration=iteration,
        provider_role="weak_corpus_recovery" if recovery_active else "main_retrieval",
        provider_record=provider_record,
        recovery_active=recovery_active,
        force_component_providers=forced,
    )


def schedule_main_retrieval_from_pipeline_scope(
    scope: Mapping[str, Any],
    *,
    current_queries: Sequence[str],
    recovery_active: bool,
    choose_search_depth: Callable[[str, str | None, int], str],
) -> RetrievalScheduledAction:
    """Schedule main retrieval from a fixed pipeline-local compatibility scope."""

    values = _require_scope(
        scope,
        (
            "provider_plan",
            "query_type",
            "intent",
            "complexity",
            "report_type",
            "is_academic",
            "suppress_tavily",
            "search_depth",
            "iteration",
            "a5_provider_override",
            "force_component_providers",
            "include_domains",
            "exclude_domains",
            "merge_provider_overrides",
            "select_provider_list",
        ),
    )
    return schedule_main_retrieval_with_provider_plan(
        provider_plan=values["provider_plan"],
        query_type=values["query_type"],
        intent=values["intent"],
        complexity=values["complexity"],
        report_type=values["report_type"],
        is_academic=values["is_academic"],
        suppress_tavily=values["suppress_tavily"],
        base_search_depth=values["search_depth"],
        iteration=values["iteration"],
        primary_override=values["a5_provider_override"],
        force_component_providers=values["force_component_providers"],
        current_queries=current_queries,
        recovery_active=recovery_active,
        choose_search_depth=choose_search_depth,
        include_domains=values["include_domains"],
        exclude_domains=values["exclude_domains"],
        merge_provider_overrides=values["merge_provider_overrides"],
        select_provider_list=values["select_provider_list"],
    )


def schedule_main_retrieval_from_kernel_action(
    action: AuthorizedAction,
    scope: Mapping[str, Any],
    *,
    current_queries: Sequence[str],
    recovery_active: bool,
    choose_search_depth: Callable[[str, str | None, int], str],
) -> RetrievalScheduledAction:
    """Schedule main retrieval only after RunKernel authorizes the pass."""

    kernel_action = validate_authorized_action(
        action,
        action_type=ActionType.MAIN_RETRIEVAL_PASS,
        stage=MAIN_RETRIEVAL_STAGE,
        expected_observation_type=ObservationType.RETRIEVAL_PASS_RESULT,
    )
    scheduled_action = schedule_main_retrieval_from_pipeline_scope(
        scope,
        current_queries=current_queries,
        recovery_active=recovery_active,
        choose_search_depth=choose_search_depth,
    )
    return _bind_main_retrieval_lineage(
        scheduled_action,
        kernel_action=kernel_action,
        scope=scope,
    )


def schedule_continuation_action(
    schedule_input: RetrievalScheduleInput,
) -> RetrievalScheduledAction:
    """Schedule an ordinary retained-producer next-pass continuation."""

    providers = _providers_from_input(schedule_input)
    operation, variant, output_type, route_blocked = _route_fields(schedule_input.provider_record)
    authorized = bool(schedule_input.continuation_authorized)
    queries = _clean_queries(schedule_input.current_queries) if authorized else ()
    return RetrievalScheduledAction(
        stage=schedule_input.stage,
        current_queries=queries,
        iteration=schedule_input.iteration,
        provider_role=schedule_input.provider_role,
        providers=providers,
        search_depth=_depth_from_input(schedule_input),
        provider_operation=operation,
        provider_variant=variant,
        provider_output_type=output_type,
        route_blocked=route_blocked,
        force_component_providers=providers,
        continue_retrieval=authorized and bool(queries) and bool(providers),
        recovery_active=False,
        reason=(
            RetrievalScheduleReason.CONTINUATION_SCHEDULED
            if authorized and queries and providers
            else RetrievalScheduleReason.CONTINUATION_BLOCKED
        ),
        metadata={
            **_provider_record_metadata(schedule_input.provider_record),
            **dict(schedule_input.metadata or {}),
        },
    )


def schedule_provider_continuation_from_record(
    *,
    stage: str,
    current_queries: Sequence[str],
    iteration: int,
    provider_role: str,
    provider_record: Any,
    continuation_authorized: bool,
    query_source: str,
) -> RetrievalScheduledAction:
    """Schedule a continuation whose next pass forces ProviderPlan providers."""

    return schedule_continuation_action(
        RetrievalScheduleInput(
            stage=stage,
            current_queries=current_queries,
            iteration=iteration,
            provider_role=provider_role,
            provider_record=provider_record,
            continuation_authorized=continuation_authorized,
            metadata={"query_source": query_source},
        )
    )


def schedule_provider_continuation_with_plan(
    *,
    provider_plan: Any,
    stage: str,
    current_queries: Sequence[str],
    iteration: int,
    provider_role: str,
    query_source: str,
    continuation_authorized: bool,
    query_type: str,
    intent: str,
    complexity: str,
    report_type: str,
    is_academic: bool,
    suppress_tavily: bool,
    override: Sequence[str] | None,
    override_is_user: bool,
    include_domains: Sequence[str] = (),
    exclude_domains: Sequence[str] = (),
    select_provider_list: Callable[..., list[str]] | None = None,
) -> RetrievalScheduledAction:
    """Record continuation ProviderPlan facts and schedule the next pass."""

    selector_kwargs = {"select_provider_list": select_provider_list} if select_provider_list is not None else {}
    provider_record = provider_plan.record_continuation(
        role=provider_role,
        query_type=query_type,
        intent=intent,
        complexity=complexity,
        report_type=report_type,
        is_academic=is_academic,
        suppress_tavily=suppress_tavily,
        override=override,
        override_is_user=override_is_user,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        **selector_kwargs,
    )
    return schedule_provider_continuation_from_record(
        stage=stage,
        current_queries=current_queries,
        iteration=iteration,
        provider_role=provider_role,
        provider_record=provider_record,
        continuation_authorized=continuation_authorized,
        query_source=query_source,
    )


def schedule_expander_continuation_from_pipeline_scope(
    scope: Mapping[str, Any],
    *,
    current_queries: Sequence[str],
    iteration: int,
    continuation_authorized: bool,
) -> RetrievalScheduledAction:
    """Schedule Expander continuation from fixed provider-policy inputs."""

    values = _require_scope(
        scope,
        (
            "provider_plan",
            "query_type",
            "intent",
            "complexity",
            "report_type",
            "is_academic",
            "suppress_tavily",
            "include_domains",
            "exclude_domains",
            "select_provider_list",
        ),
    )
    return schedule_provider_continuation_with_plan(
        provider_plan=values["provider_plan"],
        stage="expander_component_queries",
        current_queries=current_queries,
        iteration=iteration,
        provider_role="expander_continuation",
        query_source="expander",
        continuation_authorized=continuation_authorized,
        query_type=values["query_type"],
        intent=values["intent"],
        complexity=values["complexity"],
        report_type=values["report_type"],
        is_academic=values["is_academic"],
        suppress_tavily=values["suppress_tavily"],
        override=None,
        override_is_user=True,
        include_domains=values["include_domains"],
        exclude_domains=values["exclude_domains"],
        select_provider_list=values["select_provider_list"],
    )


def schedule_evaluator_continuation(
    *,
    current_queries: Sequence[str],
    iteration: int,
    current_search_depth: str,
    continuation_authorized: bool,
) -> RetrievalScheduledAction:
    """Schedule evaluator continuation without introducing forced providers."""

    return schedule_continuation_action(
        RetrievalScheduleInput(
            stage="evaluator_next_queries",
            current_queries=current_queries,
            iteration=iteration,
            provider_role="evaluator_continuation",
            search_depth=current_search_depth,
            continuation_authorized=continuation_authorized,
            metadata={"query_source": "evaluator"},
        )
    )


def schedule_weak_corpus_recovery_action(
    schedule_input: RetrievalScheduleInput,
) -> RetrievalScheduledAction:
    """Schedule the bounded weak-corpus recovery pass after controller approval."""

    providers = _providers_from_input(schedule_input)
    authorized = bool(schedule_input.continuation_authorized)
    queries = _clean_queries(schedule_input.current_queries) if authorized else ()
    return RetrievalScheduledAction(
        stage=schedule_input.stage,
        current_queries=queries,
        iteration=schedule_input.iteration,
        provider_role=schedule_input.provider_role,
        providers=providers,
        search_depth=_depth_from_input(schedule_input),
        provider_operation=None,
        provider_variant=None,
        provider_output_type=None,
        route_blocked=False,
        force_component_providers=providers,
        continue_retrieval=authorized and bool(queries),
        recovery_active=authorized and bool(queries),
        reason=(
            RetrievalScheduleReason.WEAK_CORPUS_RECOVERY_SCHEDULED
            if authorized and queries
            else RetrievalScheduleReason.WEAK_CORPUS_RECOVERY_BLOCKED
        ),
        metadata={
            **_provider_record_metadata(schedule_input.provider_record),
            **dict(schedule_input.metadata or {}),
        },
    )


def schedule_weak_corpus_recovery_from_decision(
    *,
    recovery_queries: Sequence[str],
    iteration: int,
    current_search_depth: str,
    providers: Sequence[str],
    authorized_action_name: str,
    recover_action_name: str,
    controller_decision_reason: str | None,
) -> RetrievalScheduledAction:
    """Schedule the next weak-corpus pass from an approved controller decision."""

    return schedule_weak_corpus_recovery_action(
        RetrievalScheduleInput(
            stage="weak_corpus_recovery",
            current_queries=recovery_queries,
            iteration=iteration,
            provider_role="weak_corpus_recovery",
            search_depth=current_search_depth,
            providers=providers,
            continuation_authorized=authorized_action_name == recover_action_name,
            recovery_active=True,
            metadata={
                "authorized_action_name": authorized_action_name,
                "controller_decision_reason": controller_decision_reason,
            },
        )
    )


def schedule_weak_corpus_recovery_from_pipeline_scope(
    scope: Mapping[str, Any],
    *,
    recovery_queries: Sequence[str],
    iteration: int,
    authorized_action_name: str,
    recover_action_name: str,
    controller_decision_reason: str | None,
) -> RetrievalScheduledAction:
    """Schedule weak-corpus recovery from fixed retrieval-loop facts."""

    values = _require_scope(scope, ("current_search_depth", "loop_providers"))
    return schedule_weak_corpus_recovery_from_decision(
        recovery_queries=recovery_queries,
        iteration=iteration,
        current_search_depth=values["current_search_depth"],
        providers=values["loop_providers"],
        authorized_action_name=authorized_action_name,
        recover_action_name=recover_action_name,
        controller_decision_reason=controller_decision_reason,
    )
