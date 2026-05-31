"""Controller-owned Router / Query Preparation contract.

The helpers in this module are passive and deterministic. They normalize and
package already-computed router/query-preparation facts for controller-visible
state; they do not call providers, models, search, prompts, retrieval, Author,
citation, persistence, or final-answer behavior.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

from core.entity_extraction import normalize_entities_list

ROUTER_QUERY_PREPARATION_TRACE_KEY = "router_query_preparation_contract"
ROUTER_QUERY_PREPARATION_SCHEMA_VERSION = "ag76d_rq_v1"


def _clean_text(value: Any, *, max_len: int | None = None) -> str:
    text = str(value or "").strip()
    if max_len is not None:
        return text[:max_len]
    return text


def _lower_or_default(value: Any, default: str) -> str:
    text = str(value or default).lower().strip()
    return text or default


def _copy_string_list(value: Sequence[Any] | None, *, max_len: int = 300) -> tuple[str, ...]:
    out: list[str] = []
    for item in value or ():
        text = _clean_text(item, max_len=max_len)
        if text:
            out.append(text)
    return tuple(out)


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


@dataclass(frozen=True)
class RouterQueryPreparationState:
    """Passive Controller-owned snapshot of router/query-preparation posture."""

    intent: str
    report_type: str
    query_type: str
    image_mode: str
    core_topic: str
    is_academic: bool
    primary_entity: str
    entities: tuple[str, ...] = field(default_factory=tuple)
    router_original_report_type: str | None = None
    router_original_query_type: str | None = None
    entity_fallback_provenance: dict[str, Any] = field(default_factory=dict)
    router_retry_provenance: dict[str, Any] = field(default_factory=dict)
    router_source_obligation_hints: dict[str, Any] = field(default_factory=dict)
    official_current_posture_hints: dict[str, Any] = field(default_factory=dict)
    routing_override_provenance: dict[str, Any] = field(default_factory=dict)
    query_preparation_provenance: dict[str, Any] = field(default_factory=dict)
    retrieval_budget_seed_facts: dict[str, Any] = field(default_factory=dict)
    recency_query_merge_posture: dict[str, Any] = field(default_factory=dict)
    official_source_bias_posture: dict[str, Any] = field(default_factory=dict)
    query_text_order_facts: dict[str, Any] = field(default_factory=dict)
    answer_contract_relationship: dict[str, Any] = field(default_factory=dict)
    controller_visibility: dict[str, Any] = field(default_factory=dict)

    @property
    def entities_list(self) -> list[str]:
        return list(self.entities)

    @property
    def router_entity_retry_used(self) -> bool:
        return bool(self.router_retry_provenance.get("retry_attempted"))

    def to_trace_fragment(self) -> dict[str, Any]:
        """Return an additive trace packet without raw prompts or provider payloads."""
        return {
            ROUTER_QUERY_PREPARATION_TRACE_KEY: {
                "schema_version": ROUTER_QUERY_PREPARATION_SCHEMA_VERSION,
                "controller_owned": True,
                "intent": self.intent,
                "report_type": self.report_type,
                "query_type": self.query_type,
                "primary_entity": self.primary_entity,
                "entities": list(self.entities),
                "router_original_report_type": self.router_original_report_type,
                "router_original_query_type": self.router_original_query_type,
                "entity_fallback_provenance": deepcopy(self.entity_fallback_provenance),
                "router_retry_provenance": deepcopy(self.router_retry_provenance),
                "router_source_obligation_hints": deepcopy(
                    self.router_source_obligation_hints
                ),
                "official_current_posture_hints": deepcopy(
                    self.official_current_posture_hints
                ),
                "routing_override_provenance": deepcopy(
                    self.routing_override_provenance
                ),
                "query_preparation_provenance": deepcopy(
                    self.query_preparation_provenance
                ),
                "retrieval_budget_seed_facts": deepcopy(
                    self.retrieval_budget_seed_facts
                ),
                "recency_query_merge_posture": deepcopy(
                    self.recency_query_merge_posture
                ),
                "official_source_bias_posture": deepcopy(
                    self.official_source_bias_posture
                ),
                "query_text_order_facts": deepcopy(self.query_text_order_facts),
                "answer_contract_relationship": deepcopy(
                    self.answer_contract_relationship
                ),
                "controller_visibility": deepcopy(self.controller_visibility),
            }
        }

    def to_controller_state(self) -> dict[str, Any]:
        """Return the durable controller-state payload for route_fields."""
        return deepcopy(self.to_trace_fragment()[ROUTER_QUERY_PREPARATION_TRACE_KEY])


def _parse_router_payload(router_text: str | None, query: str) -> tuple[dict[str, Any], bool]:
    try:
        parsed = json.loads(router_text or "")
        if not isinstance(parsed, dict):
            raise TypeError("router_payload_not_mapping")
        intent = parsed.get("intent", "general").lower()
        report_type = parsed.get("report_type", "general_research").lower()
        image_mode = parsed.get("image_mode", "contextual").lower()
        core_topic = parsed.get("core_topic", query[:100])
        is_academic = parsed.get("is_academic", False)
        query_type = str(parsed.get("query_type") or "other").lower().strip() or "other"
        primary_entity = str(parsed.get("primary_entity") or "").strip()[:200]
        entities = normalize_entities_list(parsed.get("entities"))
        if entities:
            primary_entity = entities[0][:200]
        elif primary_entity:
            entities = [primary_entity]
        return (
            {
                "intent": intent,
                "report_type": report_type,
                "image_mode": image_mode,
                "core_topic": core_topic,
                "is_academic": is_academic,
                "query_type": query_type,
                "primary_entity": primary_entity,
                "entities": entities,
            },
            True,
        )
    except Exception:
        return (
            {
                "intent": "general",
                "report_type": "general_research",
                "image_mode": "contextual",
                "core_topic": query[:100],
                "is_academic": False,
                "query_type": "other",
                "primary_entity": "",
                "entities": [],
            },
            False,
        )


def build_router_query_preparation_state(
    *,
    query: str,
    router_text: str | None,
    fallback_entities: Sequence[str] | None = None,
    retry_router_text: str | None = None,
    retry_attempted: bool = False,
) -> RouterQueryPreparationState:
    """Normalize router JSON plus entity fallback/retry facts into Controller state."""
    initial, initial_parse_ok = _parse_router_payload(router_text, query)
    values = dict(initial)

    fallback_values = _copy_string_list(fallback_entities, max_len=200)
    fallback_used = False
    if not values["entities"] and fallback_values:
        values["entities"] = list(fallback_values)
        values["primary_entity"] = values["entities"][0][:200]
        fallback_used = True

    retry_parse_ok: bool | None = None
    retry_entities_used = False
    if retry_attempted and not values["entities"]:
        retry_values, retry_parse_ok = _parse_router_payload(retry_router_text, query)
        retry_entities = list(retry_values.get("entities") or [])
        retry_primary = _clean_text(retry_values.get("primary_entity"), max_len=200)
        if retry_entities:
            values["entities"] = retry_entities
            values["primary_entity"] = retry_entities[0][:200]
            retry_entities_used = True
        elif retry_primary:
            values["entities"] = [retry_primary]
            values["primary_entity"] = retry_primary
            retry_entities_used = True

    report_type = _lower_or_default(values.get("report_type"), "general_research")
    query_type = _lower_or_default(values.get("query_type"), "other")
    entities = tuple(normalize_entities_list(list(values.get("entities") or [])))
    primary_entity = _clean_text(values.get("primary_entity"), max_len=200)
    if entities:
        primary_entity = entities[0][:200]
    elif primary_entity:
        entities = (primary_entity,)

    return RouterQueryPreparationState(
        intent=_lower_or_default(values.get("intent"), "general"),
        report_type=report_type,
        query_type=query_type,
        image_mode=_lower_or_default(values.get("image_mode"), "contextual"),
        core_topic=values.get("core_topic", query[:100]),
        is_academic=bool(values.get("is_academic", False)),
        primary_entity=primary_entity,
        entities=entities,
        router_original_report_type=report_type,
        router_original_query_type=query_type,
        entity_fallback_provenance={
            "fallback_considered": True,
            "fallback_used": fallback_used,
            "fallback_entity_count": len(fallback_values),
            "source": "core.entity_extraction.fallback_entities_from_query",
        },
        router_retry_provenance={
            "initial_parse_ok": initial_parse_ok,
            "retry_attempted": bool(retry_attempted),
            "retry_parse_ok": retry_parse_ok,
            "retry_entities_used": retry_entities_used,
        },
        controller_visibility={
            "state_owner": "RouterQueryPreparationState",
            "normalized_router_fields_authoritative": True,
            "raw_router_payload_retained": False,
        },
    )


def with_router_query_runtime_posture(
    state: RouterQueryPreparationState,
    *,
    intent: str,
    report_type: str,
    query_type: str,
    primary_entity: str,
    entities: Sequence[str] | None,
    is_academic: bool,
    routing_override_applied: bool,
    routing_override_reason: str | None,
    focus_academic: bool,
    force_intent_news: bool,
    complexity: str,
    max_queries: int,
    results_per_query: int,
    search_depth: str,
    top_chunks: int,
    max_iterations: int,
    recency_merge_used: bool,
    recency_query: str | None,
    official_bias_requested: bool,
    official_bias_phrase: str | None,
    finalized_queries: Sequence[str] | None,
    current_queries: Sequence[str] | None,
    query_source: str,
    answer_contract_visible: bool = True,
    controller_ledger_visible: bool = True,
) -> RouterQueryPreparationState:
    """Attach already-computed runtime query-preparation posture to the state."""
    normalized_entities = tuple(normalize_entities_list(list(entities or [])))
    normalized_primary = _clean_text(primary_entity, max_len=200)
    if normalized_entities:
        normalized_primary = normalized_entities[0][:200]
    elif normalized_primary:
        normalized_entities = (normalized_primary,)

    return replace(
        state,
        intent=_lower_or_default(intent, "general"),
        report_type=_lower_or_default(report_type, "general_research"),
        query_type=_lower_or_default(query_type, "other"),
        is_academic=bool(is_academic),
        primary_entity=normalized_primary,
        entities=normalized_entities,
        router_source_obligation_hints={
            "source_obligation_inferred_later_from_source_class_recovery": True,
            "contract_does_not_change_obligation_bridge": True,
        },
        official_current_posture_hints={
            "official_current_posture_inferred_later_from_existing_source_class_helpers": True,
            "contract_does_not_classify_sources": True,
        },
        routing_override_provenance={
            "routing_override_applied": bool(routing_override_applied),
            "routing_override_reason": routing_override_reason,
            "focus_academic_applied": bool(focus_academic),
            "force_intent_news_applied": bool(force_intent_news),
            "provider_override_semantics_unchanged": True,
        },
        query_preparation_provenance={
            "query_source": query_source,
            "finalized_by_existing_retrieval_quality_helper": True,
            "contract_generated_queries": False,
            "contract_changed_query_order": False,
        },
        retrieval_budget_seed_facts={
            "complexity": complexity,
            "max_queries": int(max_queries),
            "results_per_query": int(results_per_query),
            "search_depth": search_depth,
            "top_chunks": int(top_chunks),
            "max_iterations": int(max_iterations),
        },
        recency_query_merge_posture={
            "recency_merge_used": bool(recency_merge_used),
            "recency_query": recency_query,
            "contract_changed_recency_merge": False,
        },
        official_source_bias_posture={
            "official_bias_requested": bool(official_bias_requested),
            "official_bias_phrase": official_bias_phrase,
            "contract_changed_official_bias": False,
        },
        query_text_order_facts={
            "finalized_queries": list(_copy_string_list(finalized_queries)),
            "current_queries": list(_copy_string_list(current_queries)),
            "finalized_query_count": len(tuple(finalized_queries or ())),
            "current_query_count": len(tuple(current_queries or ())),
        },
        answer_contract_relationship={
            "answer_contract_consumes_normalized_router_fields": bool(
                answer_contract_visible
            ),
            "controller_ledger_records_query_provider_facts": bool(
                controller_ledger_visible
            ),
        },
        controller_visibility={
            **_safe_mapping(state.controller_visibility),
            "runtime_posture_authoritative": True,
            "trace_visibility": "additive",
        },
    )


__all__ = [
    "ROUTER_QUERY_PREPARATION_SCHEMA_VERSION",
    "ROUTER_QUERY_PREPARATION_TRACE_KEY",
    "RouterQueryPreparationState",
    "build_router_query_preparation_state",
    "with_router_query_runtime_posture",
]
