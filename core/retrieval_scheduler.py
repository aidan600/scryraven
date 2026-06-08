"""Active retrieval scheduling authority for already-authorized retrieval work.

The scheduler consumes QueryPlan/ProviderPlan/controller outputs that already
exist and turns them into runtime actions. It does not generate queries, choose
providers, choose search depth, execute search, rank evidence, or inspect
prompt/model behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


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
