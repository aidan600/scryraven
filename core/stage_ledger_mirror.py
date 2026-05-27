"""Passive StageLedger mirror for already-computed query/provider facts.

This helper records query lists, pass providers, and provider diagnostics into
RunController.ledger snapshots. It does not call retrieval, providers, prompts,
routing, persistence, or trace assembly.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from core.run_controller import RunController


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _copy_sequence(value: Iterable[Any] | None) -> list[Any]:
    if value is None:
        return []
    return deepcopy(list(value))


def _iter_mapping_items(
    value: Mapping[Any, Iterable[Any]] | None,
) -> list[tuple[Any, list[Any]]]:
    if value is None:
        return []
    return [(key, _copy_sequence(items)) for key, items in value.items()]


def _provider_name(value: Any) -> str:
    clean = str(value or "").strip()
    return clean or "unknown"


def _record_query_list(
    controller: RunController,
    *,
    stage: str,
    source: str,
    iteration: Any,
    queries: list[Any],
) -> None:
    for query_index, query in enumerate(queries):
        controller.ledger.record_query(
            stage=stage,
            query=str(query),
            iteration=iteration,
            metadata={
                "source": source,
                "query_index": query_index,
            },
        )


def _record_pass_provider_facts(
    controller: RunController,
    *,
    providers_by_iteration: Iterable[Iterable[Any]] | None,
) -> None:
    for iteration_index, providers in enumerate(
        _copy_sequence(providers_by_iteration),
        start=1,
    ):
        provider_list = _copy_sequence(providers)
        for provider_index, provider in enumerate(provider_list):
            controller.ledger.record_provider_fact(
                stage="providers_by_iteration",
                provider=_provider_name(provider),
                metadata={
                    "source": "providers_by_iteration",
                    "iteration": iteration_index,
                    "provider_index": provider_index,
                    "providers": provider_list,
                },
            )


def _record_retrieval_pass_facts(
    controller: RunController,
    *,
    retrieval_pass_records: Iterable[Mapping[str, Any]] | None,
) -> None:
    for pass_index, record in enumerate(_copy_sequence(retrieval_pass_records)):
        if not isinstance(record, Mapping):
            continue
        snapshot = _copy_mapping(record)
        stage = str(snapshot.get("stage") or "retrieval_pass")
        provider_role = snapshot.get("provider_role")
        providers = _copy_sequence(snapshot.get("providers"))
        for provider_index, provider in enumerate(providers):
            controller.ledger.record_provider_fact(
                stage=stage,
                provider=_provider_name(provider),
                provider_role=None if provider_role is None else str(provider_role),
                metadata={
                    "source": "retrieval_pass_records",
                    "pass_index": pass_index,
                    "iteration": deepcopy(snapshot.get("iteration")),
                    "provider_index": provider_index,
                    "search_depth": deepcopy(snapshot.get("search_depth")),
                    "results_per_query": deepcopy(
                        snapshot.get("results_per_query")
                    ),
                    "queries": _copy_sequence(snapshot.get("queries")),
                    "providers": providers,
                },
            )


def _record_provider_diagnostics(
    controller: RunController,
    *,
    provider_diagnostics: Iterable[Mapping[str, Any]] | None,
) -> None:
    for diagnostic_index, diagnostic in enumerate(
        _copy_sequence(provider_diagnostics)
    ):
        if not isinstance(diagnostic, Mapping):
            continue
        snapshot = _copy_mapping(diagnostic)
        provider_role = snapshot.get("provider_role")
        success = snapshot.get("success")
        controller.ledger.record_provider_fact(
            stage="provider_diagnostic",
            provider=_provider_name(snapshot.get("provider")),
            provider_role=None if provider_role is None else str(provider_role),
            success=success if isinstance(success, bool) else None,
            metadata={
                "source": "provider_diagnostics",
                "diagnostic_index": diagnostic_index,
                "diagnostic": snapshot,
            },
        )


def record_stage_ledger_query_provider_facts(
    controller: RunController,
    *,
    queries_by_iteration: Mapping[Any, Iterable[Any]] | None,
    disambiguation_queries_by_iteration: Mapping[Any, Iterable[Any]] | None,
    providers_by_iteration: Iterable[Iterable[Any]] | None,
    provider_diagnostics: Iterable[Mapping[str, Any]] | None,
    retrieval_pass_records: Iterable[Mapping[str, Any]] | None = None,
) -> RunController:
    """Mirror query/provider facts into the passive StageLedger."""
    for iteration, queries in _iter_mapping_items(queries_by_iteration):
        _record_query_list(
            controller,
            stage="queries_by_iteration",
            source="queries_by_iteration",
            iteration=iteration,
            queries=queries,
        )

    for iteration, queries in _iter_mapping_items(
        disambiguation_queries_by_iteration
    ):
        _record_query_list(
            controller,
            stage="disambiguation_queries_by_iteration",
            source="disambiguation_queries_by_iteration",
            iteration=iteration,
            queries=queries,
        )

    _record_pass_provider_facts(
        controller,
        providers_by_iteration=providers_by_iteration,
    )
    _record_retrieval_pass_facts(
        controller,
        retrieval_pass_records=retrieval_pass_records,
    )
    _record_provider_diagnostics(
        controller,
        provider_diagnostics=provider_diagnostics,
    )
    return controller


__all__ = ["record_stage_ledger_query_provider_facts"]
