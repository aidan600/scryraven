"""Trace-safe provider-job execution records for SearchWork handoff.

AG-96F1 turns SearchWork provider-job hints into accountability records only.
The helper binds hints to QueryPlan-admitted query metadata when present, then
hands ordinary query strings back to the existing retrieval loop. It never calls
providers, search, retrieval, fetch, prompts, models, citations, or final-answer
surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

PROVIDER_JOB_EXECUTION_SCHEMA_VERSION = "search_work_provider_job_execution_ag96f1_v1"
PROVIDER_JOB_EXECUTION_TRACE_KEY = "search_work_provider_job_execution_handoff"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output",
        "output_artifact",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_trace",
        "secret",
        "secrets",
        "token",
    }
)
_ADMITTED_STATUSES = frozenset({"finalized", "ordered", "admitted"})
_REJECTED_STATUSES = frozenset(
    {
        "rejected_over_budget",
        "rejected_blocked",
        "rejected_duplicate",
        "rejected_empty",
    }
)
_NUMERIC_PROVIDER_KINDS = frozenset({"fetch_read_extract"})


@dataclass(frozen=True, slots=True)
class ProviderJobHint:
    component_id: str
    provider_job_id: str
    provider_job_kind: str
    source_obligation_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QueryPlanProviderJobBinding:
    item_id: str
    authorized_query: str
    status: str
    component_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderJobExecutionRecord:
    execution_id: str
    component_id: str
    provider_job_id: str
    provider_job_kind: str
    source_obligation_ids: tuple[str, ...] = ()
    query_plan_item_ids: tuple[str, ...] = ()
    authorized_queries: tuple[str, ...] = ()
    execution_status: str = "unmatched"
    execution_owner: str = "existing_retrieval_loop"
    provider_selected: bool = False
    search_executed_by_helper: bool = False
    retrieval_executed_by_helper: bool = False
    source_obligations_satisfied: bool = False
    evidence_refs: tuple[str, ...] = ()
    handoff_to_existing_retrieval_loop: bool = False
    existing_retrieval_loop_remains_dispatch_owner: bool = True
    dispatch_refs: tuple[str, ...] = ()
    deferred_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        source_bound_numeric = self.provider_job_kind in _NUMERIC_PROVIDER_KINDS
        payload = {
            "execution_id": self.execution_id,
            "component_id": self.component_id,
            "provider_job_id": self.provider_job_id,
            "provider_job_kind": self.provider_job_kind,
            "source_obligation_ids": list(self.source_obligation_ids),
            "query_plan_item_ids": list(self.query_plan_item_ids),
            "authorized_queries": list(self.authorized_queries),
            "execution_status": self.execution_status,
            "execution_owner": self.execution_owner,
            "provider_selected": self.provider_selected,
            "search_executed_by_helper": self.search_executed_by_helper,
            "retrieval_executed_by_helper": self.retrieval_executed_by_helper,
            "source_obligations_satisfied": self.source_obligations_satisfied,
            "source_obligation_satisfaction_owner": "EvidenceLedger",
            "official_current_custody_satisfied": False,
            "quant_extraction_executed": False,
            "calculation_executed": False,
            "source_bound_numeric_evidence_phase_deferred": source_bound_numeric,
            "evidence_refs": list(self.evidence_refs),
            "handoff_to_existing_retrieval_loop": (
                self.handoff_to_existing_retrieval_loop
            ),
            "existing_retrieval_loop_remains_dispatch_owner": (
                self.existing_retrieval_loop_remains_dispatch_owner
            ),
            "dispatch_refs": list(self.dispatch_refs),
            "deferred_reason": self.deferred_reason,
        }
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True, slots=True)
class ProviderJobExecutionHandoff:
    records: tuple[ProviderJobExecutionRecord, ...] = ()
    component_ids_considered: tuple[str, ...] = ()
    unmatched_provider_job_ids: tuple[str, ...] = ()
    deferred_provider_job_ids: tuple[str, ...] = ()
    admitted_provider_job_ids: tuple[str, ...] = ()
    admitted_authorized_queries: tuple[str, ...] = ()
    deferred_unfilled_component_ids: tuple[str, ...] = ()
    fallback_reason: str | None = None
    behavior_boundary_flags: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        records = [record.to_dict() for record in self.records]
        component_summary = _component_coverage_summary(records)
        payload = {
            "schema_version": PROVIDER_JOB_EXECUTION_SCHEMA_VERSION,
            "trace_key": PROVIDER_JOB_EXECUTION_TRACE_KEY,
            "owner": "SearchWorkProviderJobExecutionHelper",
            "provider_job_execution_record_count": len(records),
            "provider_job_execution_records": records,
            "component_coverage_summary": component_summary,
            "unmatched_provider_jobs": list(self.unmatched_provider_job_ids),
            "deferred_provider_jobs": list(self.deferred_provider_job_ids),
            "admitted_query_handoff_summary": {
                "execution_owner": "existing_retrieval_loop",
                "existing_retrieval_loop_remains_dispatch_owner": True,
                "authorized_queries": list(self.admitted_authorized_queries),
                "provider_job_ids": list(self.admitted_provider_job_ids),
            },
            "deferred_unfilled_work": {
                "component_ids": list(self.deferred_unfilled_component_ids),
                "provider_job_ids": list(self.deferred_provider_job_ids),
            },
            "behavior_boundary_flags": dict(self.behavior_boundary_flags),
            "fallback_reason": self.fallback_reason,
        }
        return _json_safe(
            {key: value for key, value in payload.items() if value is not None}
        )


def build_provider_job_execution_handoff(
    *,
    search_work_projection: Mapping[str, Any] | None,
    query_plan_trace: Mapping[str, Any] | None,
    current_queries: Sequence[str],
    retrieval_dispatch_trace: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build execution records without changing provider/search/retrieval behavior."""

    flags = _behavior_boundary_flags()
    projection = _mapping(search_work_projection)
    query_plan = _extract_query_plan(query_plan_trace)
    if not projection:
        return ProviderJobExecutionHandoff(
            behavior_boundary_flags=flags,
            fallback_reason="search_work_projection_absent",
        ).to_dict()
    if not query_plan:
        return ProviderJobExecutionHandoff(
            behavior_boundary_flags=flags,
            fallback_reason="query_plan_trace_absent",
        ).to_dict()

    hints, component_ids = _provider_job_hints(projection)
    if not hints:
        return ProviderJobExecutionHandoff(
            component_ids_considered=component_ids,
            behavior_boundary_flags=flags,
            fallback_reason="provider_job_hints_absent",
        ).to_dict()

    current_query_set = {_clean_query(query).casefold() for query in current_queries}
    unfilled_components = _unfilled_component_ids(query_plan)
    dispatch_refs_by_query = _dispatch_refs_by_query(retrieval_dispatch_trace)
    records: list[ProviderJobExecutionRecord] = []
    for index, hint in enumerate(hints, start=1):
        bindings = _bindings_for_provider_job(query_plan, hint.provider_job_id)
        admitted = tuple(
            binding
            for binding in bindings
            if binding.status in _ADMITTED_STATUSES
            and binding.authorized_query.casefold() in current_query_set
        )
        rejected = tuple(
            binding for binding in bindings if binding.status in _REJECTED_STATUSES
        )
        status = "unmatched"
        reason: str | None = "query_plan_metadata_missing"
        selected_bindings: tuple[QueryPlanProviderJobBinding, ...] = ()
        if admitted:
            status = "admitted"
            reason = None
            selected_bindings = admitted
        elif rejected:
            status = "deferred"
            reason = "query_plan_item_rejected"
            selected_bindings = rejected
        elif hint.component_id in unfilled_components:
            status = "deferred"
            reason = "search_work_component_unfilled"
        if hint.provider_job_kind in _NUMERIC_PROVIDER_KINDS and status != "admitted":
            reason = reason or "source_bound_numeric_deferred_to_future_quant_phase"
        records.append(
            ProviderJobExecutionRecord(
                execution_id=f"provider-job-execution:{index}",
                component_id=hint.component_id,
                provider_job_id=hint.provider_job_id,
                provider_job_kind=hint.provider_job_kind,
                source_obligation_ids=hint.source_obligation_ids,
                query_plan_item_ids=tuple(binding.item_id for binding in selected_bindings),
                authorized_queries=tuple(
                    _dedupe_strings(binding.authorized_query for binding in selected_bindings)
                ),
                execution_status=status,
                provider_selected=False,
                handoff_to_existing_retrieval_loop=status == "admitted",
                dispatch_refs=tuple(
                    ref
                    for binding in selected_bindings
                    for ref in dispatch_refs_by_query.get(
                        binding.authorized_query.casefold(),
                        (),
                    )
                ),
                deferred_reason=reason,
            )
        )

    admitted_ids = tuple(
        record.provider_job_id
        for record in records
        if record.execution_status == "admitted"
    )
    deferred_ids = tuple(
        record.provider_job_id
        for record in records
        if record.execution_status == "deferred"
    )
    unmatched_ids = tuple(
        record.provider_job_id
        for record in records
        if record.execution_status == "unmatched"
    )
    admitted_queries = tuple(
        _dedupe_strings(
            query
            for record in records
            if record.execution_status == "admitted"
            for query in record.authorized_queries
        )
    )
    return ProviderJobExecutionHandoff(
        records=tuple(records),
        component_ids_considered=component_ids,
        unmatched_provider_job_ids=unmatched_ids,
        deferred_provider_job_ids=deferred_ids,
        admitted_provider_job_ids=admitted_ids,
        admitted_authorized_queries=admitted_queries,
        deferred_unfilled_component_ids=unfilled_components,
        behavior_boundary_flags=flags,
    ).to_dict()


def _provider_job_hints(
    projection: Mapping[str, Any],
) -> tuple[tuple[ProviderJobHint, ...], tuple[str, ...]]:
    source = _mapping(projection)
    query_plan_shadow = _extract_query_plan_shadow(source)
    if query_plan_shadow:
        return _hints_from_query_plan_shadow(query_plan_shadow)
    plan = _extract_plan_like_projection(source)
    if plan:
        return _hints_from_plan(plan)
    return (), ()


def _extract_query_plan_shadow(source: Mapping[str, Any]) -> dict[str, Any]:
    if source.get("trace_key") == "query_plan_work_shadow_projection":
        return _mapping(source)
    nested = _mapping(source.get("query_plan_work_shadow_projection"))
    if nested:
        return nested
    projections = _mapping(source.get("projections"))
    return _mapping(projections.get("query_plan_work_shadow_projection"))


def _extract_plan_like_projection(source: Mapping[str, Any]) -> dict[str, Any]:
    if _sequence_of_mappings(source.get("components")):
        return _mapping(source)
    plan = _mapping(source.get("search_work_plan"))
    if _sequence_of_mappings(plan.get("components")):
        return plan
    return {}


def _hints_from_query_plan_shadow(
    projection: Mapping[str, Any],
) -> tuple[tuple[ProviderJobHint, ...], tuple[str, ...]]:
    components = _sequence_of_mappings(projection.get("components"))
    obligations_by_component = _mapping(projection.get("source_obligations_by_component"))
    jobs_by_component = _mapping(projection.get("provider_jobs_by_component"))
    hints: list[ProviderJobHint] = []
    component_ids: list[str] = []
    for rank, component in enumerate(components, start=1):
        component_id = _clean_token(component.get("component_id")) or f"component-{rank}"
        component_ids.append(component_id)
        obligation_ids = tuple(
            value
            for obligation in _sequence_of_mappings(obligations_by_component.get(component_id))
            if (value := _clean_token(obligation.get("obligation_id")))
        )
        for job in _sequence_of_mappings(jobs_by_component.get(component_id)):
            job_id = _clean_token(job.get("work_id"))
            if not job_id:
                continue
            source_ids = tuple(
                _dedupe_strings(_text_sequence(job.get("source_obligation_ids")) or obligation_ids)
            )
            hints.append(
                ProviderJobHint(
                    component_id=component_id,
                    provider_job_id=job_id,
                    provider_job_kind=_clean_token(job.get("work_kind")) or "unknown",
                    source_obligation_ids=source_ids,
                )
            )
    return tuple(hints), tuple(_dedupe_strings(component_ids))


def _hints_from_plan(
    plan: Mapping[str, Any],
) -> tuple[tuple[ProviderJobHint, ...], tuple[str, ...]]:
    components = _sequence_of_mappings(plan.get("components"))
    provider_jobs = _sequence_of_mappings(plan.get("provider_jobs"))
    obligations_by_component: dict[str, tuple[str, ...]] = {}
    component_ids: list[str] = []
    for rank, component in enumerate(components, start=1):
        component_id = _clean_token(component.get("component_id")) or f"component-{rank}"
        component_ids.append(component_id)
        obligations_by_component[component_id] = tuple(
            value
            for obligation in _sequence_of_mappings(component.get("source_obligations"))
            if (
                value := _clean_token(
                    obligation.get("obligation_id")
                    or obligation.get("candidate_id")
                )
            )
        )
    hints: list[ProviderJobHint] = []
    for job in provider_jobs:
        job_id = _clean_token(
            job.get("provider_job_id") or job.get("work_id") or job.get("candidate_id")
        )
        if not job_id:
            continue
        for component_id in _text_sequence(job.get("component_ids")):
            obligation_ids = tuple(
                _dedupe_strings(
                    _text_sequence(job.get("source_obligation_ids"))
                    or obligations_by_component.get(component_id, ())
                )
            )
            hints.append(
                ProviderJobHint(
                    component_id=component_id,
                    provider_job_id=job_id,
                    provider_job_kind=_clean_token(
                        job.get("job_kind") or job.get("work_kind")
                    )
                    or "unknown",
                    source_obligation_ids=obligation_ids,
                )
            )
    return tuple(hints), tuple(_dedupe_strings(component_ids))


def _extract_query_plan(value: Mapping[str, Any] | None) -> dict[str, Any]:
    source = _mapping(value)
    if "items" in source:
        return source
    return _mapping(source.get("query_plan"))


def _bindings_for_provider_job(
    query_plan: Mapping[str, Any],
    provider_job_id: str,
) -> tuple[QueryPlanProviderJobBinding, ...]:
    bindings: list[QueryPlanProviderJobBinding] = []
    for item in _sequence_of_mappings(query_plan.get("items")):
        metadata = _mapping(item.get("metadata"))
        provider_ids = set(_text_sequence(metadata.get("provider_job_candidate_ids")))
        if provider_job_id not in provider_ids:
            continue
        authorized_query = _clean_query(item.get("authorized_query"))
        if not authorized_query:
            continue
        item_id = _clean_token(item.get("item_id")) or "query-plan:item:unknown"
        status = _clean_token(item.get("status")) or "unknown"
        bindings.append(
            QueryPlanProviderJobBinding(
                item_id=item_id,
                authorized_query=authorized_query,
                status=status,
                component_id=_clean_token(metadata.get("search_work_component_id")),
            )
        )
    return tuple(bindings)


def _unfilled_component_ids(query_plan: Mapping[str, Any]) -> tuple[str, ...]:
    consumption = _mapping(query_plan.get("search_work_consumption"))
    return tuple(_text_sequence(consumption.get("unfilled_component_ids")))


def _dispatch_refs_by_query(
    retrieval_dispatch_trace: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    trace = _mapping(retrieval_dispatch_trace)
    refs: dict[str, list[str]] = {}
    for key in ("dispatch_records", "retrieval_pass_records", "records"):
        for index, item in enumerate(_sequence_of_mappings(trace.get(key)), start=1):
            query = _clean_query(
                item.get("authorized_query")
                or item.get("query")
                or item.get("search_query")
            )
            if not query:
                continue
            ref = _clean_token(
                item.get("dispatch_ref")
                or item.get("record_id")
                or item.get("pass_id")
                or f"{key}:{index}"
            )
            if ref:
                refs.setdefault(query.casefold(), []).append(ref)
    return {
        query: tuple(_dedupe_strings(values))
        for query, values in refs.items()
    }


def _component_coverage_summary(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_component: dict[str, dict[str, Any]] = {}
    for record in records:
        component_id = _clean_token(record.get("component_id")) or "component:unknown"
        summary = by_component.setdefault(
            component_id,
            {
                "component_id": component_id,
                "provider_job_ids": [],
                "admitted_provider_job_ids": [],
                "deferred_provider_job_ids": [],
                "unmatched_provider_job_ids": [],
                "authorized_queries": [],
            },
        )
        provider_job_id = _clean_token(record.get("provider_job_id"))
        status = _clean_token(record.get("execution_status")) or "unmatched"
        if provider_job_id:
            summary["provider_job_ids"].append(provider_job_id)
            if status == "admitted":
                summary["admitted_provider_job_ids"].append(provider_job_id)
            elif status == "deferred":
                summary["deferred_provider_job_ids"].append(provider_job_id)
            else:
                summary["unmatched_provider_job_ids"].append(provider_job_id)
        summary["authorized_queries"].extend(_text_sequence(record.get("authorized_queries")))
    return [
        {
            **summary,
            "provider_job_ids": list(_dedupe_strings(summary["provider_job_ids"])),
            "admitted_provider_job_ids": list(
                _dedupe_strings(summary["admitted_provider_job_ids"])
            ),
            "deferred_provider_job_ids": list(
                _dedupe_strings(summary["deferred_provider_job_ids"])
            ),
            "unmatched_provider_job_ids": list(
                _dedupe_strings(summary["unmatched_provider_job_ids"])
            ),
            "authorized_queries": list(_dedupe_strings(summary["authorized_queries"])),
        }
        for summary in by_component.values()
    ]


def _behavior_boundary_flags() -> dict[str, Any]:
    return {
        "query_text_generated": False,
        "provider_selected": False,
        "provider_job_execution_helper_selected_provider": False,
        "provider_search_behavior_changed": False,
        "retrieval_behavior_changed": False,
        "prompt_behavior_changed": False,
        "citation_behavior_changed": False,
        "final_answer_behavior_changed": False,
        "source_obligations_satisfied": False,
        "source_obligation_satisfaction_changed": False,
        "official_current_custody_satisfied": False,
        "evidence_refs_created": False,
        "search_executed_by_helper": False,
        "retrieval_executed_by_helper": False,
        "existing_retrieval_loop_remains_dispatch_owner": True,
        "query_plan_admission_order_changed": False,
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _text_sequence(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(text for item in value if (text := _clean_token(item)))


def _dedupe_strings(values: Sequence[str] | Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_token(value)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return tuple(out)


def _clean_query(value: Any) -> str:
    return " ".join(str(value or "").strip().split())[:300]


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_token(key, limit=100)
            if not key_text or _is_sensitive_key(key_text):
                continue
            out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:120]]
    return _clean_text(value, limit=300)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


__all__ = [
    "PROVIDER_JOB_EXECUTION_SCHEMA_VERSION",
    "PROVIDER_JOB_EXECUTION_TRACE_KEY",
    "build_provider_job_execution_handoff",
]
