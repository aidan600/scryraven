"""Bridge AG-96F1 provider-job handoffs into EvidenceLedger observations.

The bridge is evidence-custody only. It consumes already-computed QueryPlan,
SearchWork, provider-job handoff, and retrieval/search records, then emits a
sanitized EvidenceLedger observation payload. It never calls providers, search,
retrieval, fetch, prompts, models, citations, or final-answer surfaces.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse, urlunparse

PROVIDER_JOB_EVIDENCE_LEDGER_BRIDGE_SCHEMA_VERSION = (
    "provider_job_evidence_ledger_bridge_ag96g1_v1"
)
PROVIDER_JOB_EVIDENCE_LEDGER_BRIDGE_TRACE_KEY = (
    "provider_job_evidence_ledger_bridge_projection"
)

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_text",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "snippet",
        "snippets",
        "text",
        "token",
    }
)
_STRONG_REQUIREMENT_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "sourced_numeric_values",
    }
)
_STRONG_SOURCE_TIERS = frozenset({"official", "primary", "canonical"})
_WEAK_SOURCE_CLASSES = frozenset(
    {
        "secondary",
        "secondary_analysis",
        "reputable_secondary",
        "social_signal",
        "social_or_forum",
        "community",
        "context",
    }
)
_WEAK_SOURCE_TIERS = frozenset(
    {
        "secondary",
        "trusted_community",
        "social_or_forum",
        "context",
        "analysis",
    }
)
_CURRENTNESS_KINDS = frozenset(
    {"official_current", "legal_current_primary", "date_bound_currentness"}
)
_SOURCE_BOUND_NUMERIC_KINDS = frozenset({"source_bound_numeric", "source_bound"})


@dataclass(frozen=True, slots=True)
class ProviderJobEvidenceLedgerBridgeResult:
    observation_payload: Mapping[str, Any]
    projection: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_payload": dict(self.observation_payload),
            "projection": dict(self.projection),
        }


def build_provider_job_evidence_ledger_observation(
    *,
    observation_id: str,
    provider_job_execution_handoff: Mapping[str, Any] | None,
    query_plan_trace: Mapping[str, Any] | None = None,
    current_authorized_queries: Sequence[str] | None = None,
    retrieval_records: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
    search_work_projection: Mapping[str, Any] | None = None,
) -> ProviderJobEvidenceLedgerBridgeResult:
    """Return a sanitized EvidenceLedger observation plus bridge projection."""

    handoff = _mapping(provider_job_execution_handoff)
    records = _sequence_of_mappings(handoff.get("provider_job_execution_records"))
    if not handoff:
        return _no_op_result("provider_job_execution_handoff_absent")
    if not records:
        return _no_op_result(
            _clean_token(handoff.get("fallback_reason"))
            or "provider_job_execution_records_absent"
        )

    query_plan = _extract_query_plan(query_plan_trace)
    search_work = _mapping(search_work_projection)
    obligations = _source_obligations_by_ref(search_work)
    requirements = _requirements_from_execution_records(records, obligations)
    candidates = _candidate_records_from_runtime(retrieval_records)
    aggregate_counts = _aggregate_counts_for_requirements(
        retrieval_records,
        requirements,
    )
    links, linked_requirement_ids = _requirement_links(
        records=records,
        candidates=candidates,
        requirements=requirements,
        query_plan=query_plan,
        current_authorized_queries=current_authorized_queries or (),
    )
    gaps = _custody_gaps(
        requirements=requirements,
        candidates=candidates,
        links=links,
        linked_requirement_ids=linked_requirement_ids,
        aggregate_counts=aggregate_counts,
    )

    observation = _json_safe(
        {
            "schema_version": PROVIDER_JOB_EVIDENCE_LEDGER_BRIDGE_SCHEMA_VERSION,
            "observation_id": observation_id,
            "observation_source": "provider_job_evidence_ledger_bridge",
            "owner": "ProviderJobEvidenceLedgerBridge",
            "requirements": requirements,
            "candidates": candidates,
            "requirement_links": links,
            "custody_gaps": gaps,
            "aggregate_counts": aggregate_counts,
            "provider_job_evidence_ledger_bridge_projection": _projection(
                ran=True,
                observation_created=True,
                requirements=requirements,
                candidates=candidates,
                links=links,
                gaps=gaps,
                aggregate_counts=aggregate_counts,
                fallback_reason=None,
            ),
        }
    )
    observation.setdefault("requirements", [])
    observation.setdefault("candidates", [])
    observation.setdefault("requirement_links", [])
    observation.setdefault("custody_gaps", [])
    observation.setdefault("aggregate_counts", {})
    projection = dict(observation["provider_job_evidence_ledger_bridge_projection"])
    return ProviderJobEvidenceLedgerBridgeResult(
        observation_payload=observation,
        projection=projection,
    )


def _no_op_result(fallback_reason: str) -> ProviderJobEvidenceLedgerBridgeResult:
    projection = _projection(
        ran=False,
        observation_created=False,
        requirements=(),
        candidates=(),
        links=(),
        gaps=(),
        aggregate_counts={},
        fallback_reason=fallback_reason,
    )
    return ProviderJobEvidenceLedgerBridgeResult(
        observation_payload={},
        projection=projection,
    )


def _projection(
    *,
    ran: bool,
    observation_created: bool,
    requirements: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    links: Sequence[Mapping[str, Any]],
    gaps: Sequence[Mapping[str, Any]],
    aggregate_counts: Mapping[str, int],
    fallback_reason: str | None,
) -> dict[str, Any]:
    official_status = _official_current_status(
        requirements=requirements,
        links=links,
        aggregate_counts=aggregate_counts,
    )
    return _json_safe(
        {
            "schema_version": PROVIDER_JOB_EVIDENCE_LEDGER_BRIDGE_SCHEMA_VERSION,
            "trace_key": PROVIDER_JOB_EVIDENCE_LEDGER_BRIDGE_TRACE_KEY,
            "owner": "ProviderJobEvidenceLedgerBridge",
            "provider_job_evidence_ledger_bridge_ran": bool(ran),
            "evidence_ledger_observation_created": bool(observation_created),
            "candidate_count": len(candidates),
            "requirement_count": len(requirements),
            "requirement_link_count": len(links),
            "custody_gap_count": len(gaps),
            "official_current_custody_status": official_status,
            "source_obligation_satisfaction_claimed_by_bridge": False,
            "final_answer_behavior_changed": False,
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "fallback_reason": fallback_reason,
        }
    )


def _requirements_from_execution_records(
    records: Sequence[Mapping[str, Any]],
    obligations: Mapping[tuple[str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        component_id = _clean_token(record.get("component_id")) or "component_unknown"
        provider_job_id = _clean_token(record.get("provider_job_id")) or "provider_job_unknown"
        for obligation_id in _text_sequence(record.get("source_obligation_ids")):
            obligation = _mapping(obligations.get((component_id, obligation_id)))
            kind = _clean_token(obligation.get("kind")) or _kind_from_provider_job(
                record.get("provider_job_kind")
            )
            required_class = (
                _clean_token(
                    obligation.get("required_source_class")
                    or obligation.get("source_class")
                )
                or _required_source_class(kind)
            )
            requirement_id = _requirement_id(component_id, obligation_id, provider_job_id)
            if requirement_id in seen:
                continue
            seen.add(requirement_id)
            out.append(
                {
                    "requirement_id": requirement_id,
                    "requirement_kind": _requirement_kind(kind, required_class),
                    "required_source_class": required_class,
                    "required_currentness": _required_currentness(kind, obligation),
                    "origin_ref": (
                        "provider_job_execution:"
                        f"{_clean_token(record.get('execution_id')) or provider_job_id}"
                    ),
                    "component_id": component_id,
                    "source_obligation_id": obligation_id,
                    "provider_job_id": provider_job_id,
                    "query_plan_item_ids": _text_sequence(
                        record.get("query_plan_item_ids")
                    ),
                    "authorized_queries": _clean_queries(
                        record.get("authorized_queries")
                    ),
                    "aggregate_counts_insufficient": _strong_requirement_class(
                        required_class
                    ),
                }
            )
    return out


def _candidate_records_from_runtime(
    retrieval_records: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, source in enumerate(_runtime_record_items(retrieval_records), start=1):
        candidate = _candidate_record(source, index=index)
        candidate_id = candidate.get("candidate_id")
        if not candidate_id or candidate_id in seen:
            continue
        seen.add(str(candidate_id))
        out.append(candidate)
    return out


def _candidate_record(source: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    url = _clean_text(source.get("url") or source.get("source_url"), limit=500)
    domain = _clean_text(
        source.get("domain") or source.get("normalized_domain"),
        limit=160,
    ) or _domain_from_url(url)
    source_class = _clean_token(source.get("source_class"))
    source_tier = _clean_token(source.get("source_tier"))
    lower_tier = source_class in _WEAK_SOURCE_CLASSES or source_tier in _WEAK_SOURCE_TIERS
    return _json_safe(
        {
            "candidate_id": _candidate_id(source, index=index),
            "url": url,
            "title": source.get("title"),
            "domain": domain,
            "provider_name": source.get("provider_name") or source.get("provider"),
            "retrieval_pass_id": (
                source.get("retrieval_pass_id")
                or source.get("retrieval_stage")
                or source.get("pass_id")
                or source.get("dispatch_ref")
            ),
            "query_ref": (
                source.get("query_ref")
                or source.get("query_preview")
                or source.get("query")
                or source.get("authorized_query")
                or source.get("search_query")
            ),
            "source_tier": source_tier,
            "source_class": source_class,
            "currentness_signal": (
                source.get("currentness_signal") or source.get("currentness")
            ),
            "readable_status": (
                source.get("readable_status")
                or source.get("readability_status")
                or source.get("readable")
            ),
            "fetchable_status": (
                source.get("fetchable_status") or source.get("fetch_status")
            ),
            "disposition": (
                source.get("disposition")
                or source.get("fit_disposition")
                or source.get("status")
                or "observed"
            ),
            "record_kind": "fact",
            "eligible_for_stronger_obligation": source.get(
                "eligible_for_stronger_obligation"
            ),
            "contextual_only": bool(source.get("contextual_only")) or lower_tier,
            "lower_tier": lower_tier,
            "final_evidence_eligible": source.get("final_evidence_eligible", False),
            "provider_job_id": source.get("provider_job_id"),
            "provider_job_execution_id": source.get("provider_job_execution_id"),
        }
    )


def _requirement_links(
    *,
    records: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    requirements: Sequence[Mapping[str, Any]],
    query_plan: Mapping[str, Any],
    current_authorized_queries: Sequence[str],
) -> tuple[list[dict[str, Any]], set[str]]:
    requirements_by_obligation: dict[tuple[str, str, str], dict[str, Any]] = {}
    for requirement in requirements:
        requirements_by_obligation[
            (
                str(requirement.get("component_id")),
                str(requirement.get("source_obligation_id")),
                str(requirement.get("provider_job_id")),
            )
        ] = dict(requirement)
    query_plan_items = _query_plan_items_by_provider_job(query_plan)
    current_query_set = {
        _clean_query(query).casefold() for query in current_authorized_queries or ()
    }
    links: list[dict[str, Any]] = []
    linked_requirement_ids: set[str] = set()
    for record in records:
        provider_job_id = _clean_token(record.get("provider_job_id"))
        execution_id = _clean_token(record.get("execution_id"))
        authorized_queries = {
            query.casefold() for query in _clean_queries(record.get("authorized_queries"))
        }
        if current_query_set:
            authorized_queries &= current_query_set
        dispatch_refs = set(_text_sequence(record.get("dispatch_refs")))
        item_refs = query_plan_items.get(provider_job_id, {})
        for obligation_id in _text_sequence(record.get("source_obligation_ids")):
            requirement = requirements_by_obligation.get(
                (
                    _clean_token(record.get("component_id")),
                    obligation_id,
                    provider_job_id,
                )
            )
            if not requirement:
                continue
            for candidate in candidates:
                reason = _candidate_relation_reason(
                    candidate=candidate,
                    provider_job_id=provider_job_id,
                    execution_id=execution_id,
                    authorized_queries=authorized_queries,
                    dispatch_refs=dispatch_refs,
                    query_plan_item_refs=item_refs,
                )
                if not reason:
                    continue
                if not _candidate_source_fit(candidate, requirement):
                    continue
                links.append(
                    {
                        "requirement_id": requirement["requirement_id"],
                        "candidate_id": candidate["candidate_id"],
                        "link_reason": reason,
                        "link_status": candidate.get("disposition") or "observed",
                    }
                )
                linked_requirement_ids.add(str(requirement["requirement_id"]))
    return _dedupe_links(links), linked_requirement_ids


def _custody_gaps(
    *,
    requirements: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    links: Sequence[Mapping[str, Any]],
    linked_requirement_ids: set[str],
    aggregate_counts: Mapping[str, int],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    candidate_count = len(candidates)
    linked_candidate_ids = {str(link.get("candidate_id")) for link in links}
    for requirement in requirements:
        req_id = str(requirement.get("requirement_id"))
        if req_id in aggregate_counts:
            gaps.append(
                {
                    "gap_type": "legacy_aggregate_only_path",
                    "requirement_id": req_id,
                    "reason": "aggregate_count_observed_without_candidate_identity",
                    "source_ref": "provider_job_evidence_ledger_bridge",
                }
            )
        if req_id in linked_requirement_ids:
            continue
        gaps.append(
            {
                "gap_type": "missing_candidate_identity"
                if candidate_count == 0
                else "missing_source_class_fit",
                "requirement_id": req_id,
                "reason": "no_candidate_linked_to_provider_job_source_obligation",
                "source_ref": "provider_job_evidence_ledger_bridge",
            }
        )
    for candidate in candidates:
        if str(candidate.get("candidate_id")) not in linked_candidate_ids:
            gaps.append(
                {
                    "gap_type": "missing_source_class_fit",
                    "candidate_id": candidate.get("candidate_id"),
                    "reason": "candidate_not_trace_safely_linked_to_source_obligation",
                    "source_ref": "provider_job_evidence_ledger_bridge",
                }
            )
    return _dedupe_gaps(gaps)


def _aggregate_counts_for_requirements(
    retrieval_records: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
    requirements: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    source = _mapping(retrieval_records)
    aggregate = _mapping(source.get("aggregate_counts"))
    tier_counts = _mapping(source.get("source_tier_counts"))
    out: dict[str, int] = {}
    for requirement in requirements:
        req_id = str(requirement.get("requirement_id"))
        required_class = _clean_token(requirement.get("required_source_class"))
        count = _positive_int(aggregate.get(req_id))
        if count == 0 and required_class in {"official_current_rules", "legal_or_regulatory_text"}:
            count = _positive_int(tier_counts.get("official"))
        if count == 0 and required_class == "primary_source_documents":
            count = _positive_int(tier_counts.get("canonical") or tier_counts.get("primary"))
        if count > 0:
            out[req_id] = count
    return out


def _source_obligations_by_ref(
    search_work_projection: Mapping[str, Any],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    source = _extract_query_plan_shadow(search_work_projection) or search_work_projection
    out: dict[tuple[str, str], Mapping[str, Any]] = {}
    for component_id, items in _mapping(source.get("source_obligations_by_component")).items():
        component_token = _clean_token(component_id)
        for item in _sequence_of_mappings(items):
            obligation_id = _clean_token(
                item.get("obligation_id") or item.get("candidate_id")
            )
            if obligation_id:
                out[(component_token, obligation_id)] = dict(item)
    plan = _extract_plan_like(search_work_projection)
    for component in _sequence_of_mappings(plan.get("components")):
        component_id = _clean_token(component.get("component_id"))
        for item in _sequence_of_mappings(component.get("source_obligations")):
            obligation_id = _clean_token(
                item.get("obligation_id") or item.get("candidate_id")
            )
            if obligation_id:
                out[(component_id, obligation_id)] = dict(item)
    return out


def _extract_query_plan_shadow(source: Mapping[str, Any]) -> dict[str, Any]:
    source = _mapping(source)
    if source.get("trace_key") == "query_plan_work_shadow_projection":
        return source
    nested = _mapping(source.get("query_plan_work_shadow_projection"))
    if nested:
        return nested
    projections = _mapping(source.get("projections"))
    return _mapping(projections.get("query_plan_work_shadow_projection"))


def _extract_plan_like(source: Mapping[str, Any]) -> dict[str, Any]:
    source = _mapping(source)
    if _sequence_of_mappings(source.get("components")):
        return source
    return _mapping(source.get("search_work_plan"))


def _extract_query_plan(query_plan_trace: Mapping[str, Any] | None) -> dict[str, Any]:
    source = _mapping(query_plan_trace)
    if "items" in source:
        return source
    return _mapping(source.get("query_plan"))


def _query_plan_items_by_provider_job(
    query_plan: Mapping[str, Any],
) -> dict[str, dict[str, set[str]]]:
    out: dict[str, dict[str, set[str]]] = {}
    for item in _sequence_of_mappings(query_plan.get("items")):
        metadata = _mapping(item.get("metadata"))
        for provider_job_id in _text_sequence(metadata.get("provider_job_candidate_ids")):
            entry = out.setdefault(
                provider_job_id,
                {"queries": set(), "item_ids": set()},
            )
            if query := _clean_query(item.get("authorized_query")):
                entry["queries"].add(query.casefold())
            if item_id := _clean_token(item.get("item_id")):
                entry["item_ids"].add(item_id)
    return out


def _candidate_relation_reason(
    *,
    candidate: Mapping[str, Any],
    provider_job_id: str,
    execution_id: str,
    authorized_queries: set[str],
    dispatch_refs: set[str],
    query_plan_item_refs: Mapping[str, set[str]],
) -> str | None:
    candidate_provider_job = _clean_token(candidate.get("provider_job_id"))
    if candidate_provider_job and candidate_provider_job == provider_job_id:
        return "same_provider_job_execution_record"
    candidate_execution = _clean_token(candidate.get("provider_job_execution_id"))
    if candidate_execution and candidate_execution == execution_id:
        return "same_provider_job_execution_record"
    retrieval_pass_id = _clean_token(candidate.get("retrieval_pass_id"))
    if retrieval_pass_id and retrieval_pass_id in dispatch_refs:
        return "same_retrieval_dispatch_ref"
    query_ref = _clean_query(candidate.get("query_ref")).casefold()
    if query_ref and query_ref in authorized_queries:
        return "same_authorized_query"
    if query_ref and query_ref in query_plan_item_refs.get("queries", set()):
        return "same_query_plan_item_metadata"
    return None


def _candidate_source_fit(
    candidate: Mapping[str, Any],
    requirement: Mapping[str, Any],
) -> bool:
    required_class = _clean_token(requirement.get("required_source_class"))
    if not _strong_requirement_class(required_class):
        return True
    if bool(candidate.get("contextual_only")) or bool(candidate.get("lower_tier")):
        return False
    source_class = _clean_token(candidate.get("source_class"))
    source_tier = _clean_token(candidate.get("source_tier"))
    domain = _clean_text(candidate.get("domain"), limit=160) or ""
    if required_class == "official_current_rules":
        return (
            source_class == "official_current_rules"
            or source_tier in _STRONG_SOURCE_TIERS
            or domain.endswith(".gov")
        )
    if required_class == "legal_or_regulatory_text":
        return source_class in {
            "legal_or_regulatory_text",
            "current_primary_or_official",
            "official_current_rules",
        } or source_tier in {"official", "primary"}
    if required_class == "current_primary_or_official":
        return source_class in {
            "current_primary_or_official",
            "official_current_rules",
            "legal_or_regulatory_text",
            "primary_source_documents",
        } or source_tier in {"official", "primary"}
    if required_class == "primary_source_documents":
        return source_class == "primary_source_documents" or source_tier in {
            "official",
            "primary",
            "canonical",
        }
    if required_class == "sourced_numeric_values":
        return source_class == "sourced_numeric_values" or source_tier in {
            "official",
            "primary",
            "canonical",
        }
    return source_class == required_class


def _runtime_record_items(
    value: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        direct_items = []
        for key in (
            "candidates",
            "candidate_records",
            "passages",
            "all_passages",
            "results",
            "records",
            "search_results",
            "retrieval_records",
        ):
            direct_items.extend(_sequence_of_mappings(value.get(key)))
        if direct_items:
            return tuple(direct_items)
        return ()
    return _sequence_of_mappings(value)


def _required_source_class(kind: str) -> str:
    if kind == "official_current":
        return "official_current_rules"
    if kind == "legal_current_primary":
        return "legal_or_regulatory_text"
    if kind == "canonical_documentation":
        return "primary_source_documents"
    if kind in _SOURCE_BOUND_NUMERIC_KINDS:
        return "sourced_numeric_values"
    return "not_observable"


def _requirement_kind(kind: str, required_class: str) -> str:
    if kind == "official_current" or required_class == "official_current_rules":
        return "official_current"
    if kind == "legal_current_primary" or required_class in {
        "legal_or_regulatory_text",
        "current_primary_or_official",
    }:
        return "legal"
    if kind == "canonical_documentation" or required_class == "primary_source_documents":
        return "canonical"
    if kind in _SOURCE_BOUND_NUMERIC_KINDS or required_class == "sourced_numeric_values":
        return "source_bound"
    return kind or "general"


def _required_currentness(kind: str, obligation: Mapping[str, Any]) -> str | None:
    explicit = _clean_token(
        obligation.get("required_currentness")
        or obligation.get("currentness_requirement")
    )
    if explicit:
        return explicit
    if kind in _CURRENTNESS_KINDS:
        return "current"
    return None


def _kind_from_provider_job(provider_job_kind: Any) -> str:
    kind = _clean_token(provider_job_kind)
    if kind == "official_candidate_acquisition":
        return "official_current"
    if kind == "canonical_extraction":
        return "canonical_documentation"
    if kind == "conflict_currentness_check":
        return "legal_current_primary"
    if kind == "fetch_read_extract":
        return "source_bound_numeric"
    return "general"


def _requirement_id(component_id: str, obligation_id: str, provider_job_id: str) -> str:
    return f"provider_job_requirement:{component_id}:{obligation_id}:{provider_job_id}"


def _candidate_id(record: Mapping[str, Any], *, index: int) -> str:
    explicit = _clean_token(record.get("candidate_id"))
    if explicit:
        return explicit
    if source_id := _clean_token(record.get("source_id")):
        return f"provider_job_candidate:source:{source_id}"
    identity = _normalize_identity(
        record.get("url")
        or record.get("source_url")
        or record.get("normalized_source_identity")
        or record.get("source_identity")
        or record.get("title")
    )
    if identity:
        return f"provider_job_candidate:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"
    return f"provider_job_candidate:runtime:{index}"


def _official_current_status(
    *,
    requirements: Sequence[Mapping[str, Any]],
    links: Sequence[Mapping[str, Any]],
    aggregate_counts: Mapping[str, int],
) -> str:
    official_requirements = {
        str(item.get("requirement_id"))
        for item in requirements
        if _clean_token(item.get("required_source_class"))
        in {
            "official_current_rules",
            "legal_or_regulatory_text",
            "current_primary_or_official",
            "primary_source_documents",
        }
    }
    if not official_requirements:
        return "not_available"
    linked = {
        str(link.get("requirement_id"))
        for link in links
        if str(link.get("requirement_id")) in official_requirements
    }
    if linked:
        return "candidate_linked_pending_evidence_ledger_evaluation"
    if any(req in aggregate_counts for req in official_requirements):
        return "aggregate_only_insufficient"
    return "missing_candidate_identity"


def _strong_requirement_class(required_class: str | None) -> bool:
    return _clean_token(required_class) in _STRONG_REQUIREMENT_CLASSES


def _behavior_boundary_flags() -> dict[str, Any]:
    return {
        "query_text_generated": False,
        "provider_search_behavior_changed": False,
        "retrieval_behavior_changed": False,
        "prompt_behavior_changed": False,
        "citation_behavior_changed": False,
        "final_answer_behavior_changed": False,
        "sufficiency_judgment_behavior_changed": False,
        "source_obligation_satisfaction_claimed_by_bridge": False,
        "provider_selected": False,
        "search_executed_by_bridge": False,
        "retrieval_executed_by_bridge": False,
        "quant_extraction_executed": False,
        "calculation_executed": False,
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


def _clean_queries(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(_dedupe_strings(_clean_query(item) for item in value))


def _dedupe_strings(values: Sequence[str] | Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return tuple(out)


def _dedupe_links(links: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for link in links:
        key = (str(link.get("requirement_id")), str(link.get("candidate_id")))
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(link))
    return out


def _dedupe_gaps(gaps: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for gap in gaps:
        key = (
            str(gap.get("gap_type")),
            str(gap.get("requirement_id")),
            str(gap.get("candidate_id")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(gap))
    return out


def _positive_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _normalize_identity(value: Any) -> str:
    text = _clean_text(value, limit=500) or ""
    if not text:
        return ""
    parsed = urlparse(text)
    if not parsed.netloc:
        return text.casefold()
    return urlunparse(
        (
            parsed.scheme.casefold() or "https",
            parsed.netloc.casefold(),
            parsed.path.rstrip("/"),
            "",
            parsed.query,
            "",
        )
    )


def _domain_from_url(value: Any) -> str | None:
    parsed = urlparse(str(value or "").strip())
    return parsed.netloc.casefold() or None


def _clean_query(value: Any) -> str:
    return " ".join(str(value or "").strip().split())[:300]


def _clean_text(value: Any, *, limit: int = 260) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        return ""
    return text.casefold().replace("-", "_").replace(" ", "_")[:limit]


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
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
            safe = _json_safe(item, depth=depth + 1)
            if safe not in (None, "", [], {}):
                out[key_text] = safe
        return out
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:120]]
    return _clean_text(value, limit=300)


__all__ = [
    "PROVIDER_JOB_EVIDENCE_LEDGER_BRIDGE_SCHEMA_VERSION",
    "PROVIDER_JOB_EVIDENCE_LEDGER_BRIDGE_TRACE_KEY",
    "ProviderJobEvidenceLedgerBridgeResult",
    "build_provider_job_evidence_ledger_observation",
]
