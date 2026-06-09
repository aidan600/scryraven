"""Active retrieval scheduling authority for already-authorized retrieval work.

The scheduler consumes QueryPlan/ProviderPlan/controller outputs that already
exist and turns them into runtime actions. It does not generate queries, choose
providers, choose search depth, execute search, rank evidence, or inspect
prompt/model behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Sequence


class RetrievalScheduleReason(str, Enum):
    MAIN_PASS_SCHEDULED = "main_pass_scheduled"
    CONTINUATION_SCHEDULED = "continuation_scheduled"
    CONTINUATION_BLOCKED = "continuation_blocked"
    WEAK_CORPUS_RECOVERY_SCHEDULED = "weak_corpus_recovery_scheduled"
    WEAK_CORPUS_RECOVERY_BLOCKED = "weak_corpus_recovery_blocked"


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
    force_component_providers: tuple[str, ...]
    continue_retrieval: bool
    recovery_active: bool
    reason: RetrievalScheduleReason
    metadata: Mapping[str, Any]

    def queries_list(self) -> list[str]:
        return list(self.current_queries)

    def providers_list(self) -> list[str]:
        return list(self.providers)

    def force_component_providers_list(self) -> list[str]:
        return list(self.force_component_providers)

    def to_trace(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "current_queries": list(self.current_queries),
            "iteration": self.iteration,
            "provider_role": self.provider_role,
            "providers": list(self.providers),
            "search_depth": self.search_depth,
            "force_component_providers": list(self.force_component_providers),
            "continue_retrieval": self.continue_retrieval,
            "recovery_active": self.recovery_active,
            "reason": self.reason.value,
            "metadata": dict(self.metadata),
        }


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


def _provider_record_metadata(provider_record: Any | None) -> dict[str, Any]:
    if provider_record is None:
        return {}
    trace = provider_record.to_trace() if hasattr(provider_record, "to_trace") else {}
    role = getattr(provider_record, "role", None)
    return {
        "provider_record_role": str(role) if role is not None else None,
        "provider_record": trace,
    }


def schedule_main_retrieval_action(
    schedule_input: RetrievalScheduleInput,
) -> RetrievalScheduledAction:
    """Schedule one main-loop retrieval pass from consumed QueryPlan/ProviderPlan facts."""

    providers = _providers_from_input(schedule_input)
    return RetrievalScheduledAction(
        stage=schedule_input.stage,
        current_queries=_clean_queries(schedule_input.current_queries),
        iteration=schedule_input.iteration,
        provider_role=schedule_input.provider_role,
        providers=providers,
        search_depth=_depth_from_input(schedule_input),
        force_component_providers=(),
        continue_retrieval=bool(schedule_input.current_queries),
        recovery_active=bool(schedule_input.recovery_active),
        reason=RetrievalScheduleReason.MAIN_PASS_SCHEDULED,
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
                "force_component_providers_consumed": list(
                    force_component_providers or ()
                ),
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
    )


def schedule_continuation_action(
    schedule_input: RetrievalScheduleInput,
) -> RetrievalScheduledAction:
    """Schedule ordinary Scout/Expander/Evaluator next-pass continuation."""

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
        force_component_providers=providers,
        continue_retrieval=authorized and bool(queries),
        recovery_active=False,
        reason=(
            RetrievalScheduleReason.CONTINUATION_SCHEDULED
            if authorized and queries
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
    select_provider_list: Callable[..., list[str]] | None = None,
) -> RetrievalScheduledAction:
    """Record continuation ProviderPlan facts and schedule the next pass."""

    selector_kwargs = (
        {"select_provider_list": select_provider_list}
        if select_provider_list is not None
        else {}
    )
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


def schedule_scout_continuation_from_pipeline_scope(
    scope: Mapping[str, Any],
    *,
    current_queries: Sequence[str],
    iteration: int,
    continuation_authorized: bool,
) -> RetrievalScheduledAction:
    """Schedule Scout continuation from fixed provider-policy inputs."""

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
        ),
    )
    return schedule_provider_continuation_with_plan(
        provider_plan=values["provider_plan"],
        stage="scout_directed_continuation",
        current_queries=current_queries,
        iteration=iteration,
        provider_role="scout_continuation",
        query_source="scout",
        continuation_authorized=continuation_authorized,
        query_type=values["query_type"],
        intent=values["intent"],
        complexity=values["complexity"],
        report_type=values["report_type"],
        is_academic=values["is_academic"],
        suppress_tavily=values["suppress_tavily"],
        override=["exa", "linkup"],
        override_is_user=False,
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
