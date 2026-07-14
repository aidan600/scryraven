"""Sanitized AG-LIVE validation observability projection.

This module consolidates already-existing validation/runtime telemetry into one
packet-facing projection. It does not call providers, select routes, fetch
pages, rank evidence, alter citation eligibility, or change Author behavior.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlparse, urlunparse

from core.provider_diagnostics import summarize_provider_diagnostics
from core.retrieval_loop_contract import RETRIEVAL_LOOP_TRACE_KEY
from core.validation_profiles import get_validation_profile

VALIDATION_OBSERVABILITY_SCHEMA_VERSION = "validation_observability_v1"
SUBJECT_BUDGET_SUMMARY_SCHEMA_VERSION = "subject_budget_summary_v1"

_UNKNOWN = "unknown"
_SNIPPET_ONLY = "snippet_only"
_FULL_PAGE_FETCHED = "full_page_fetched"
_NOT_AVAILABLE = "not_available"
_SUBJECT_SCOPE_INITIAL = "initial_independent_subjects_only"
_FOLLOWUP_POLICY = "internal_followups_governed_by_existing_mode_and_resource_caps"
_MAX_SANITIZED_SUBJECTS = 20
_SENSITIVE_VALUE_MARKERS = (
    "api_key",
    "bearer ",
    "provider_payload",
    "raw_prompt",
    "raw_request",
    "raw_response",
    "secret",
    "sk-",
    "token",
)
_SATISFIED_STATUSES = {
    "fulfilled",
    "not_required_or_satisfied",
    "requirement_satisfied",
    "satisfied",
    "source_obligation_satisfied",
}
_UNSATISFIED_MARKERS = (
    "partial",
    "unfulfilled",
    "unsatisfied",
    "unmet",
)
_HTTP_URL_RE = re.compile(r"https?://[^\s<>\]\)]+", re.IGNORECASE)


def build_validation_observability(
    *,
    validation_profile: Any | None = None,
    preflight_context: Any | None = None,
    run_config: Any | None = None,
    outcome: Any | None = None,
    cap_policy: Any | None = None,
) -> dict[str, Any]:
    """Build the single sanitized AG-LIVE observability packet field."""

    trace = _mapping(getattr(outcome, "execution_trace", None))
    top_passages = _mapping_list(getattr(outcome, "top_passages", None))
    seen_urls = _string_list(getattr(outcome, "seen_urls", None))
    final_answer_text = str(getattr(outcome, "report", "") or "")
    final_answer_urls = extract_cited_urls_from_text(final_answer_text)
    cited_source_ids, cited_source_id_source = _cited_source_id_resolution(trace)
    cited_urls = _cited_urls(outcome, trace, cited_source_ids)
    used_final_answer_urls = False
    if not cited_urls and final_answer_urls:
        cited_urls = final_answer_urls
        used_final_answer_urls = True
    cited_url_resolution_source = _cited_url_resolution_source(
        cited_source_ids,
        cited_urls,
        cited_source_id_source,
        used_final_answer_urls=used_final_answer_urls,
    )
    profile_name = _profile_name(validation_profile, preflight_context)
    caps_observed = _caps_observed(cap_policy, trace)

    return {
        "schema_version": VALIDATION_OBSERVABILITY_SCHEMA_VERSION,
        "projection_mode": "sanitized_existing_telemetry_consolidation",
        "validation_profile_name": profile_name,
        "model_invocation_summary": _model_invocation_summary(run_config, trace),
        "search_provider_summary": _search_provider_summary(trace),
        "retrieval_dispatch_summary": _retrieval_dispatch_summary(
            trace,
            caps_observed=caps_observed,
        ),
        "source_material_summary": _source_material_summary(
            top_passages=top_passages,
            seen_urls=seen_urls,
            cited_source_ids=cited_source_ids,
            cited_urls=cited_urls,
            cited_url_resolution_source=cited_url_resolution_source,
        ),
        "source_custody_summary": _source_custody_summary(
            profile_name=profile_name,
            trace=trace,
            top_passages=top_passages,
            cited_source_ids=cited_source_ids,
            cited_urls=cited_urls,
            fetch_read_operations=_optional_int(
                caps_observed.get("fetch_read_operations")
            ),
            final_answer_text=final_answer_text,
        ),
        "subject_budget_summary": build_subject_budget_summary(
            validation_profile=validation_profile,
            preflight_context=preflight_context,
            trace=trace,
        ),
        "cap_and_retention_summary": _cap_and_retention_summary(
            validation_profile=validation_profile,
            preflight_context=preflight_context,
            caps_observed=caps_observed,
        ),
        "raw_private_material_serialized": False,
    }


def build_subject_budget_summary(
    *,
    validation_profile: Any | None = None,
    preflight_context: Any | None = None,
    trace: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize passive initial subject/component budget state."""

    trace_map = _mapping(trace)
    policy = _subject_budget_policy(validation_profile)
    subjects, selection_source, detection_diagnosis = _detected_subjects(trace_map)
    enabled = bool(policy.get("subject_budget_enabled", False))
    max_subjects = _optional_int(policy.get("max_initial_selected_subjects"))
    if not enabled:
        selected: list[dict[str, Any]] = []
        omitted: list[dict[str, Any]] = []
    elif max_subjects is None:
        selected = list(subjects)
        omitted = []
    else:
        selected = list(subjects[:max_subjects])
        omitted = list(subjects[max_subjects:])

    mapped_ids, mapping_available = _query_mapped_subject_ids(trace_map)
    evidenced_ids, evidence_available, same_source_observed = (
        _component_evidenced_subject_ids(trace_map)
    )
    selected_ids = {_subject_identity(item) for item in selected}
    query_mapped_subject_count = (
        len(selected_ids & mapped_ids) if mapping_available else None
    )
    independently_evidenced_subject_count = (
        len(selected_ids & evidenced_ids) if evidence_available else None
    )
    subjects_without_evidence = (
        [
            _subject_payload(
                item,
                mapped_ids=mapped_ids,
                mapping_available=mapping_available,
                evidenced_ids=evidenced_ids,
                evidence_available=evidence_available,
            )
            for item in selected
            if _subject_identity(item) not in evidenced_ids
        ]
        if evidence_available
        else []
    )
    diagnosis = _subject_budget_diagnosis(
        enabled=enabled,
        subjects=subjects,
        detection_diagnosis=detection_diagnosis,
        mapping_available=mapping_available,
        evidence_available=evidence_available,
    )

    return {
        "schema_version": SUBJECT_BUDGET_SUMMARY_SCHEMA_VERSION,
        "subject_budget_enabled": enabled,
        "max_initial_selected_subjects": max_subjects if enabled else None,
        "subject_budget_scope": (
            _safe_text(policy.get("subject_budget_scope"))
            or _SUBJECT_SCOPE_INITIAL
        ),
        "applies_to_internal_followups": bool(
            policy.get("applies_to_internal_followups", False)
        ),
        "detected_subject_count": len(subjects),
        "selected_subject_count": len(selected),
        "omitted_subject_count": len(omitted),
        "selected_subjects": [
            _subject_payload(
                item,
                mapped_ids=mapped_ids,
                mapping_available=mapping_available,
                evidenced_ids=evidenced_ids,
                evidence_available=evidence_available,
            )
            for item in selected
        ],
        "omitted_subjects": [
            _subject_payload(
                item,
                mapped_ids=mapped_ids,
                mapping_available=mapping_available,
                evidenced_ids=evidenced_ids,
                evidence_available=evidence_available,
            )
            for item in omitted
        ],
        "subject_selection_source": selection_source,
        "subject_cap_exceeded": bool(enabled and max_subjects is not None)
        and len(subjects) > max_subjects,
        "query_mapped_subject_count": query_mapped_subject_count,
        "independently_evidenced_subject_count": (
            independently_evidenced_subject_count
        ),
        "subjects_without_evidence": subjects_without_evidence,
        "same_source_evidence_allowed": (
            policy.get("same_source_evidence_allowed") if enabled else None
        ),
        "same_source_evidence_observed": same_source_observed,
        "followup_budget_policy": _followup_budget_policy(
            policy=policy,
            trace=trace_map,
        ),
        "validation_profile_name": _profile_name(
            validation_profile,
            preflight_context,
        ),
        "diagnosis": diagnosis,
    }


def _subject_budget_policy(validation_profile: Any | None) -> dict[str, Any]:
    policy = getattr(validation_profile, "subject_budget", None)
    if hasattr(policy, "as_requested_dict"):
        return dict(policy.as_requested_dict())
    return {
        "subject_budget_enabled": False,
        "max_initial_selected_subjects": None,
        "subject_budget_scope": _SUBJECT_SCOPE_INITIAL,
        "applies_to_internal_followups": False,
        "same_source_evidence_allowed": None,
        "subject_selection_source": _NOT_AVAILABLE,
        "followup_budget_policy": _FOLLOWUP_POLICY,
        "policy_status": "not_configured",
    }


def _detected_subjects(
    trace: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str, str | None]:
    query_plan_shadow = _query_plan_work_shadow_projection(trace)
    if query_plan_shadow:
        subjects = _subjects_from_components(
            _mapping_list(query_plan_shadow.get("components")),
            source="query_plan_work_shadow_projection",
        )
        if subjects:
            return subjects, "query_plan_work_shadow_projection_component_order", None
    search_work_plan = _search_work_plan_projection(trace)
    if search_work_plan:
        subjects = _subjects_from_components(
            _mapping_list(search_work_plan.get("components")),
            source="search_work_plan_component_order",
        )
        if subjects:
            return subjects, "search_work_plan_component_order", None
    query_shape = _mapping(trace.get("query_shape_assessment"))
    subjects = _subjects_from_components(
        _mapping_list(query_shape.get("component_candidates")),
        source="query_shape_assessment_component_order",
    )
    if subjects:
        return subjects, "query_shape_assessment_component_order", None
    query_plan_consumption = _query_plan_search_work_consumption(trace)
    subjects = _subjects_from_component_ids_considered(
        query_plan_consumption,
        source="query_plan_search_work_consumption_component_ids_considered",
    )
    if subjects:
        return (
            subjects,
            "query_plan_search_work_consumption_component_ids_considered",
            None,
        )
    for consumption in _standalone_search_work_consumption_sources(trace):
        subjects = _subjects_from_component_ids_considered(
            consumption,
            source="search_work_consumption_component_ids_considered",
        )
        if subjects:
            return subjects, "search_work_consumption_component_ids_considered", None
    return [], _NOT_AVAILABLE, "detected_subjects_not_available"


def _query_plan_work_shadow_projection(trace: Mapping[str, Any]) -> dict[str, Any]:
    direct = _mapping(trace.get("query_plan_work_shadow_projection"))
    if direct:
        return direct
    lane = _mapping(trace.get("search_work_shadow_lane_projection"))
    nested = _mapping(lane.get("query_plan_work_shadow_projection"))
    if nested:
        return nested
    projections = _mapping(trace.get("projections"))
    return _mapping(projections.get("query_plan_work_shadow_projection"))


def _search_work_plan_projection(trace: Mapping[str, Any]) -> dict[str, Any]:
    direct = _mapping(trace.get("search_work_plan"))
    if _mapping_list(direct.get("components")):
        return direct
    lane = _mapping(trace.get("search_work_shadow_lane_projection"))
    nested = _mapping(lane.get("search_work_plan"))
    if _mapping_list(nested.get("components")):
        return nested
    nested = _mapping(lane.get("search_work_plan_projection"))
    if _mapping_list(nested.get("components")):
        return nested
    projections = _mapping(trace.get("projections"))
    nested = _mapping(projections.get("search_work_plan"))
    if _mapping_list(nested.get("components")):
        return nested
    return {}


def _subjects_from_components(
    components: Sequence[Mapping[str, Any]],
    *,
    source: str,
) -> list[dict[str, Any]]:
    subjects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank, component in enumerate(components, start=1):
        subject_id = _first_text(
            component.get("component_id"),
            component.get("candidate_id"),
            component.get("group_id"),
            f"component-{rank}",
        )
        if not subject_id:
            continue
        identity = _normalize_subject_id(subject_id)
        if identity in seen:
            continue
        seen.add(identity)
        subjects.append(
            _without_none(
                {
                    "subject_id": subject_id,
                    "rank": rank,
                    "source": source,
                    "source_obligation_count": _optional_int(
                        component.get("source_obligation_count")
                    ),
                    "provider_job_count": _optional_int(
                        component.get("provider_job_count")
                    ),
                }
            )
        )
        if len(subjects) >= _MAX_SANITIZED_SUBJECTS:
            break
    return subjects


def _subjects_from_component_ids_considered(
    consumption: Mapping[str, Any],
    *,
    source: str,
) -> list[dict[str, Any]]:
    component_ids = consumption.get("component_ids_considered")
    if not isinstance(component_ids, Sequence) or isinstance(
        component_ids,
        (str, bytes),
    ):
        return []
    subjects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank, component_id in enumerate(component_ids, start=1):
        subject_id = _safe_text(component_id, limit=160)
        if not subject_id:
            continue
        identity = _normalize_subject_id(subject_id)
        if identity in seen:
            continue
        seen.add(identity)
        subjects.append(
            {
                "subject_id": subject_id,
                "rank": rank,
                "source": source,
            }
        )
        if len(subjects) >= _MAX_SANITIZED_SUBJECTS:
            break
    return subjects


def _subject_payload(
    subject: Mapping[str, Any],
    *,
    mapped_ids: set[str],
    mapping_available: bool,
    evidenced_ids: set[str],
    evidence_available: bool,
) -> dict[str, Any]:
    identity = _subject_identity(subject)
    payload = {
        "subject_id": _safe_text(subject.get("subject_id"), limit=160),
        "rank": _optional_int(subject.get("rank")),
        "source": _safe_text(subject.get("source"), limit=120),
        "query_mapped": identity in mapped_ids if mapping_available else None,
        "independently_evidenced": (
            identity in evidenced_ids if evidence_available else None
        ),
        "source_obligation_count": _optional_int(
            subject.get("source_obligation_count")
        ),
        "provider_job_count": _optional_int(subject.get("provider_job_count")),
    }
    return _without_none(payload)


def _subject_identity(subject: Mapping[str, Any]) -> str:
    return _normalize_subject_id(subject.get("subject_id"))


def _normalize_subject_id(value: Any) -> str:
    text = _safe_text(value, limit=160) or ""
    normalized = text.casefold().strip()
    if normalized.startswith("component:"):
        normalized = normalized.removeprefix("component:")
    return normalized


def _query_mapped_subject_ids(
    trace: Mapping[str, Any],
) -> tuple[set[str], bool]:
    ids: set[str] = set()
    consumption_available = False
    for consumption in _search_work_consumption_sources(trace):
        if "search_work_consumed_by_query_plan" in consumption:
            consumption_available = True
        for metadata in _mapping(consumption.get("query_metadata")).values():
            if not isinstance(metadata, Mapping):
                continue
            component_id = _safe_text(metadata.get("search_work_component_id"))
            if component_id:
                ids.add(_normalize_subject_id(component_id))
    query_plan = _mapping(trace.get("query_plan"))
    for item in _mapping_list(query_plan.get("items")):
        metadata = _mapping(item.get("metadata"))
        component_id = _safe_text(metadata.get("search_work_component_id"))
        if component_id:
            ids.add(_normalize_subject_id(component_id))
    available = bool(ids) or consumption_available
    return ids, available


def _query_plan_search_work_consumption(trace: Mapping[str, Any]) -> dict[str, Any]:
    query_plan = _mapping(trace.get("query_plan"))
    return _mapping(query_plan.get("search_work_consumption"))


def _standalone_search_work_consumption_sources(
    trace: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    sources: list[dict[str, Any]] = []
    direct = _mapping(trace.get("search_work_consumption"))
    if direct:
        sources.append(direct)
    projections = _mapping(trace.get("projections"))
    projected = _mapping(projections.get("search_work_consumption"))
    if projected:
        sources.append(projected)
    return tuple(sources)


def _search_work_consumption_sources(
    trace: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    sources: list[dict[str, Any]] = []
    query_plan_consumption = _query_plan_search_work_consumption(trace)
    if query_plan_consumption:
        sources.append(query_plan_consumption)
    sources.extend(_standalone_search_work_consumption_sources(trace))
    return tuple(sources)


def _component_evidenced_subject_ids(
    trace: Mapping[str, Any],
) -> tuple[set[str], bool, bool | None]:
    packet = _mapping(trace.get("final_answer_packet"))
    rows = _mapping_list(packet.get("semantic_packet_evidence_bindings"))
    if not rows:
        coverage = _semantic_content_coverage(packet, trace)
        manifest = _mapping(packet.get("semantic_evidence_authority_manifest"))
        binding_available = bool(
            manifest.get("semantic_packet_evidence_binding_available")
            or manifest.get("semantic_packet_evidence_binding_count")
        )
        if binding_available:
            rows = _mapping_list(coverage.get("semantic_source_ref_bindings"))
            if not rows:
                rows = _mapping_list(
                    coverage.get("author_materialization_content_refs")
                )
    if not rows:
        return set(), False, None

    ids: set[str] = set()
    source_keys_by_component: dict[str, set[str]] = {}
    for row in rows:
        component_id = _first_text(
            row.get("component_id"),
            row.get("answer_component_id"),
        )
        if not component_id:
            continue
        identity = _normalize_subject_id(component_id)
        ids.add(identity)
        source_key = _first_text(
            row.get("source_id"),
            row.get("source_url"),
            row.get("packet_evidence_id"),
            row.get("origin_evidence_ref_id"),
        )
        if source_key:
            source_keys_by_component.setdefault(identity, set()).add(source_key)
    if not ids:
        return set(), False, None
    same_source_observed = _same_source_observed(source_keys_by_component)
    return ids, True, same_source_observed


def _semantic_content_coverage(
    packet: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    for value in (
        packet.get("semantic_content_coverage_ref"),
        packet.get("semantic_content_coverage_ref_projection"),
        trace.get("semantic_content_coverage_ref"),
        trace.get("semantic_content_coverage_ref_projection"),
    ):
        coverage = _mapping(value)
        if coverage:
            return coverage
    return {}


def _same_source_observed(source_keys_by_component: Mapping[str, set[str]]) -> bool | None:
    source_to_components: dict[str, set[str]] = {}
    for component_id, source_keys in source_keys_by_component.items():
        for source_key in source_keys:
            source_to_components.setdefault(source_key, set()).add(component_id)
    if not source_to_components:
        return None
    return any(len(component_ids) > 1 for component_ids in source_to_components.values())


def _followup_budget_policy(
    *,
    policy: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    query_plan_shadow = _query_plan_work_shadow_projection(trace)
    followup = _mapping(query_plan_shadow.get("stop_and_follow_up_posture"))
    return {
        "policy": _safe_text(policy.get("followup_budget_policy"))
        or _FOLLOWUP_POLICY,
        "subject_budget_scope": _safe_text(policy.get("subject_budget_scope"))
        or _SUBJECT_SCOPE_INITIAL,
        "initial_subject_cap_applies_to_internal_followups": False,
        "internal_followups_governed_by": "existing_mode_resource_caps",
        "observation_status": (
            "internal_followups_exempt_but_not_independently_observed"
        ),
        "observed_follow_up_permission": _safe_text(
            followup.get("follow_up_permission")
        ),
    }


def _subject_budget_diagnosis(
    *,
    enabled: bool,
    subjects: Sequence[Mapping[str, Any]],
    detection_diagnosis: str | None,
    mapping_available: bool,
    evidence_available: bool,
) -> str | None:
    if not enabled:
        return "subject_budget_not_enabled_for_profile"
    notes: list[str] = []
    if detection_diagnosis:
        notes.append(detection_diagnosis)
    if subjects and not mapping_available:
        notes.append("query_component_mapping_not_available")
    if subjects and not evidence_available:
        notes.append("component_scoped_evidence_binding_not_available")
    return ";".join(notes) if notes else None


def _without_none(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _model_invocation_summary(
    run_config: Any | None,
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    packet = _mapping(trace.get("final_answer_packet"))
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))

    summary = {
        "fast_provider": _safe_text(getattr(run_config, "fast_provider", None)),
        "fast_model": _safe_text(getattr(run_config, "fast_model", None)),
        "smart_provider": _safe_text(getattr(run_config, "smart_provider", None)),
        "smart_model": _safe_text(getattr(run_config, "smart_model", None)),
        "embed_provider": _safe_text(getattr(run_config, "embed_provider", None)),
        "embed_model": _safe_text(getattr(run_config, "embed_model", None)),
        "author_provider": _first_text(
            trace.get("author_provider"),
            author_input_refs.get("author_provider"),
            author_payload_ref.get("author_provider"),
        ),
        "author_model": _first_text(
            trace.get("author_model"),
            author_input_refs.get("author_model"),
            author_payload_ref.get("author_model"),
        ),
        "author_system_prompt_key": _first_text(
            trace.get("author_system_prompt_key"),
            author_input_refs.get("author_system_prompt_key"),
            author_payload_ref.get("author_system_prompt_key"),
        ),
        "author_provider_model_source": "trace"
        if (
            trace.get("author_provider")
            or author_input_refs.get("author_provider")
            or author_payload_ref.get("author_provider")
        )
        else None,
    }
    if (
        summary["author_provider"] is None
        and summary["author_model"] is None
        and run_config is not None
    ):
        provider, model = _author_provider_model_from_config(run_config)
        summary["author_provider"] = provider
        summary["author_model"] = model
        summary["author_provider_model_source"] = "run_config_mode_inference"
    return summary


def _search_provider_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    attempts = _mapping_list(trace.get("provider_diagnostics"))
    summarized = summarize_provider_diagnostics(attempts) if attempts else {}
    selected_provider_list_by_iteration = _provider_lists_by_iteration(trace)
    providers_attempted = _unique_strings(
        [
            *(attempt.get("provider") for attempt in attempts),
            *(
                provider
                for providers in selected_provider_list_by_iteration
                for provider in providers
            ),
        ]
    )
    accepted_by_provider: Counter[str] = Counter()
    result_summary_count = _optional_int(trace.get("provider_result_summary_count"))
    computed_result_summary_count = 0
    for attempt in attempts:
        provider = _safe_text(attempt.get("provider")) or _UNKNOWN
        accepted = _optional_int(attempt.get("accepted_url_count")) or 0
        if accepted:
            accepted_by_provider[provider] += accepted
        computed_result_summary_count += (
            _optional_int(attempt.get("provider_result_summary_count")) or 0
        )
    if result_summary_count is None:
        result_summary_count = computed_result_summary_count

    return {
        "provider_diagnostics_available": bool(attempts),
        "providers_attempted_by_name": providers_attempted,
        "provider_successful_attempts_by_provider": _safe_count_mapping(
            trace.get("provider_successful_attempts_by_provider")
            or summarized.get("provider_successful_attempts_by_provider")
        ),
        "provider_failed_attempts_by_provider": _safe_count_mapping(
            trace.get("provider_failed_attempts_by_provider")
            or summarized.get("provider_failed_attempts_by_provider")
        ),
        "provider_attempts_by_role": _safe_count_mapping(
            trace.get("provider_attempts_by_role")
            or summarized.get("provider_attempts_by_role")
        ),
        "provider_accepted_url_count_by_provider": dict(
            sorted(accepted_by_provider.items())
        ),
        "providers_returned_accepted_urls": sorted(
            provider for provider, count in accepted_by_provider.items() if count > 0
        ),
        "provider_result_summary_count": result_summary_count,
        "selected_provider_list_by_iteration": selected_provider_list_by_iteration,
    }


def _retrieval_dispatch_summary(
    trace: Mapping[str, Any],
    *,
    caps_observed: Mapping[str, Any],
) -> dict[str, Any]:
    pass_records = _retrieval_pass_records(trace)
    loop_contract = _mapping(trace.get(RETRIEVAL_LOOP_TRACE_KEY))
    loop_records = _retrieval_loop_pass_records(loop_contract)
    selected = pass_records or loop_records
    return {
        "retrieval_pass_count": len(selected),
        "retrieval_pass_records_available": bool(pass_records),
        "retrieval_loop_contract_available": bool(loop_contract),
        "pass_records": selected,
        "search_dispatches_observed": _optional_int(
            caps_observed.get("search_dispatches")
        ),
        "fetch_read_operations_observed": _optional_int(
            caps_observed.get("fetch_read_operations")
        ),
    }


def _source_material_summary(
    *,
    top_passages: Sequence[Mapping[str, Any]],
    seen_urls: Sequence[str],
    cited_source_ids: Sequence[str],
    cited_urls: Sequence[str],
    cited_url_resolution_source: str,
) -> dict[str, Any]:
    cited_url_set = set(cited_urls)
    cited_url_by_key = {
        key: url
        for url in cited_urls
        if (key := _url_match_key(url))
    }
    cited_source_id_set = set(cited_source_ids)
    tiers_by_url: dict[str, str] = {}
    material_by_url: dict[str, str] = {}
    matched_cited_urls: set[str] = set()
    for passage in top_passages:
        url = _safe_text(passage.get("url"))
        matched_cited_url = _matched_cited_url(
            passage,
            cited_url_set=cited_url_set,
            cited_url_by_key=cited_url_by_key,
            cited_source_id_set=cited_source_id_set,
        )
        if not matched_cited_url:
            continue
        if not url:
            continue
        matched_cited_urls.add(matched_cited_url)
        tier = _safe_text(passage.get("source_tier"))
        if tier and matched_cited_url not in tiers_by_url:
            tiers_by_url[matched_cited_url] = tier
        material = _evidence_material_type(passage)
        material_by_url[matched_cited_url] = _stronger_material_type(
            material_by_url.get(matched_cited_url),
            material,
        )
    return {
        "cited_source_ids": list(cited_source_ids),
        "cited_urls": list(cited_urls),
        "cited_url_resolution_source": cited_url_resolution_source,
        "top_passage_count": len(top_passages),
        "seen_url_count": len(seen_urls),
        "cited_urls_seen_in_top_passages": bool(cited_urls)
        and len(matched_cited_urls) == len(set(cited_urls)),
        "cited_urls_seen_in_top_passages_count": len(matched_cited_urls),
        "source_tiers_by_cited_url": tiers_by_url,
        "evidence_material_type_by_cited_url": {
            url: material_by_url.get(url, _UNKNOWN) for url in cited_urls
        },
    }


def _source_custody_summary(
    *,
    profile_name: str | None,
    trace: Mapping[str, Any],
    top_passages: Sequence[Mapping[str, Any]],
    cited_source_ids: Sequence[str],
    cited_urls: Sequence[str],
    fetch_read_operations: int | None,
    final_answer_text: str,
) -> dict[str, Any]:
    packet = _mapping(trace.get("final_answer_packet"))
    expected = _source_custody_expected(profile_name)
    fetch_required = _source_custody_fetch_required(profile_name)
    official_satisfied = _official_source_custody_satisfied(trace, packet)
    source_obligation_status = _source_obligation_status(trace, packet)
    final_answer_mentions_custody_partial = _mentions_custody_partial(
        final_answer_text
    )
    has_official_doc_citations = _has_official_doc_citations(
        cited_urls,
        top_passages,
    )
    diagnosis = None
    explanation = None
    source_custody_satisfied = official_satisfied

    if (
        expected
        and fetch_required
        and fetch_read_operations == 0
        and has_official_doc_citations
    ):
        source_custody_satisfied = False
        diagnosis = "fetch_read_operations_zero_with_official_doc_citations"
        explanation = (
            "Cited official docs were present, but fetch/read operations were zero, "
            "so the packet does not prove official source custody."
        )
    elif source_custody_satisfied is None and _status_is_unsatisfied(
        source_obligation_status
    ):
        source_custody_satisfied = False
    elif source_custody_satisfied is None and final_answer_mentions_custody_partial:
        source_custody_satisfied = False
        diagnosis = "final_answer_declares_source_custody_partial"

    return {
        "source_custody_expected": expected,
        "fetch_read_required": fetch_required,
        "fetch_read_operations": fetch_read_operations,
        "official_source_custody_satisfied": official_satisfied,
        "source_custody_satisfied": source_custody_satisfied,
        "citation_eligible_source_ids": _citation_eligible_source_ids(
            trace,
            packet,
        ),
        "final_answer_source_ids_used": _string_list(
            trace.get("final_answer_source_ids_used")
        )
        or list(cited_source_ids),
        "source_obligation_status": source_obligation_status,
        "source_custody_diagnosis": diagnosis,
        "source_custody_explanation": explanation,
        "official_doc_citations_present": has_official_doc_citations,
        "final_answer_mentions_custody_partial": (
            final_answer_mentions_custody_partial
        ),
    }


def _cap_and_retention_summary(
    *,
    validation_profile: Any | None,
    preflight_context: Any | None,
    caps_observed: Mapping[str, Any],
) -> dict[str, Any]:
    profile = validation_profile
    return {
        "caps_requested": _caps_requested(profile, preflight_context),
        "caps_observed": dict(caps_observed),
        "retention_posture": _safe_text(getattr(profile, "retention_posture", None)),
        "no_retention": {
            "raw_provider_payloads_retained": False,
            "raw_prompts_retained": False,
            "raw_model_requests_retained": False,
            "raw_model_responses_retained": False,
            "private_logs_retained": False,
            "db_cache_rows_retained_in_packet": False,
            "full_raw_traces_retained": False,
        },
        "packet_schema": _safe_text(getattr(profile, "packet_schema", None)),
    }


def _caps_requested(
    validation_profile: Any | None,
    preflight_context: Any | None,
) -> dict[str, int]:
    caps = getattr(preflight_context, "caps", None)
    if hasattr(caps, "as_requested_dict"):
        return {
            str(key): int(value)
            for key, value in caps.as_requested_dict().items()
        }
    profile_caps = getattr(validation_profile, "cap_policy", None)
    if hasattr(profile_caps, "as_requested_dict"):
        return {
            str(key): int(value)
            for key, value in profile_caps.as_requested_dict().items()
        }
    return {}


def _caps_observed(
    cap_policy: Any | None,
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    if cap_policy is not None and hasattr(cap_policy, "observed_counts"):
        observed = cap_policy.observed_counts()
        return {
            "scryraven_runs": 1,
            "search_dispatches": _optional_int(observed.get("search_dispatches"))
            or 0,
            "fetch_read_operations": _optional_int(
                observed.get("fetch_read_operations")
            )
            or 0,
            "author_model_calls": _optional_int(observed.get("author_model_calls"))
            or 0,
            "smart_search_judgment_model_calls": _optional_int(
                observed.get("smart_search_judgment_model_calls")
            )
            or 0,
            "independent_manual_source_checks": 0,
            "retries": _optional_int(observed.get("retries")) or 0,
            "enforcement": _safe_text(observed.get("enforcement")) or "active",
            "facts": _string_list(getattr(cap_policy, "facts", None)),
        }
    cap_trace = _mapping(trace.get("cap_enforcement_trace")) or _mapping(
        trace.get("run_cap_enforcement")
    )
    if not cap_trace:
        return {}
    return {
        "scryraven_runs": 1,
        "search_dispatches": _optional_int(cap_trace.get("search_dispatches")) or 0,
        "fetch_read_operations": _optional_int(
            cap_trace.get("fetch_read_operations")
        )
        or 0,
        "author_model_calls": _optional_int(cap_trace.get("author_model_calls")) or 0,
        "smart_search_judgment_model_calls": _optional_int(
            cap_trace.get("smart_search_judgment_model_calls")
        )
        or 0,
        "independent_manual_source_checks": 0,
        "retries": _optional_int(cap_trace.get("retries")) or 0,
        "enforcement": _safe_text(cap_trace.get("enforcement")) or "active",
        "facts": _string_list(cap_trace.get("facts")),
    }


def _retrieval_pass_records(trace: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = _mapping_list(trace.get("retrieval_pass_records"))
    return [_retrieval_pass_record(record) for record in records]


def _retrieval_loop_pass_records(loop_contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not loop_contract:
        return []
    descriptor = _mapping(loop_contract.get("pass_descriptor"))
    pass_result_summaries = _mapping_list(loop_contract.get("pass_result_summaries"))
    query_count = _list_count(
        descriptor.get("current_queries") or loop_contract.get("current_queries")
    )
    providers = _string_list(
        descriptor.get("provider_list") or loop_contract.get("provider_list")
    )
    if not descriptor and not providers and not pass_result_summaries:
        return []
    return [
        {
            "stage": _safe_text(descriptor.get("stage")) or "main_retrieval",
            "iteration": _optional_int(
                descriptor.get("iteration") or loop_contract.get("iteration")
            ),
            "query_count": query_count,
            "providers": providers,
            "provider_role": _safe_text(
                descriptor.get("provider_role")
                or loop_contract.get("provider_role")
            )
            or "main_retrieval",
            "search_depth": _safe_text(
                descriptor.get("search_depth") or loop_contract.get("search_depth")
            ),
            "results_per_query": _optional_int(
                descriptor.get("results_per_query")
                or loop_contract.get("results_per_query")
            ),
            "pass_result_summary_count": len(pass_result_summaries),
        }
    ]


def _retrieval_pass_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": _safe_text(record.get("stage")) or "retrieval_pass",
        "iteration": _optional_int(record.get("iteration")),
        "query_count": _optional_int(record.get("query_count"))
        if record.get("query_count") is not None
        else _list_count(record.get("queries")),
        "providers": _string_list(record.get("providers")),
        "provider_role": _safe_text(record.get("provider_role")),
        "search_depth": _safe_text(record.get("search_depth")),
        "results_per_query": _optional_int(record.get("results_per_query")),
    }


def _provider_lists_by_iteration(trace: Mapping[str, Any]) -> list[list[str]]:
    values = trace.get("pass_providers") or trace.get("providers_by_iteration")
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        loop_contract = _mapping(trace.get(RETRIEVAL_LOOP_TRACE_KEY))
        providers = _string_list(loop_contract.get("provider_list"))
        return [providers] if providers else []
    if values and all(isinstance(item, str) for item in values):
        return [_string_list(values)]
    return [_string_list(item) for item in values if _string_list(item)]


def _cited_source_id_resolution(trace: Mapping[str, Any]) -> tuple[list[str], str]:
    ids = _string_list(trace.get("final_answer_source_ids_used"))
    if ids:
        return ids, "final_answer_source_ids_used"
    final_answer_source_telemetry = _mapping(trace.get("final_answer_source_telemetry"))
    ids = _string_list(
        final_answer_source_telemetry.get("final_answer_source_ids_used")
    )
    if ids:
        return ids, "final_answer_source_telemetry"
    packet = _mapping(trace.get("final_answer_packet"))
    ids = _citation_eligible_source_ids(trace, packet)
    if ids:
        return ids, "citation_eligible_source_ids"
    return [], "unavailable"


def _cited_url_resolution_source(
    cited_source_ids: Sequence[str],
    cited_urls: Sequence[str],
    cited_source_id_source: str,
    *,
    used_final_answer_urls: bool = False,
) -> str:
    if cited_urls and used_final_answer_urls:
        return "final_answer_markdown_urls"
    if not cited_source_ids:
        return "unavailable"
    if not cited_urls:
        return "source_ids_unresolved"
    return cited_source_id_source


def _cited_urls(
    outcome: Any | None,
    trace: Mapping[str, Any],
    cited_source_ids: Sequence[str],
) -> list[str]:
    cited_id_set = {str(item) for item in cited_source_ids}
    if not cited_id_set:
        return []
    urls: list[str] = []
    for passage in _mapping_list(getattr(outcome, "top_passages", None)):
        source_id = str(passage.get("source_id") or "").strip()
        if source_id and source_id not in cited_id_set:
            continue
        url = _safe_text(passage.get("url"))
        if url and url not in urls:
            urls.append(url)
    for url, source_id in _unique_source_url_items(trace):
        if source_id in cited_id_set and url not in urls:
            urls.append(url)
    return urls


def _unique_source_url_items(trace: Mapping[str, Any]) -> list[tuple[str, str]]:
    packet = _mapping(trace.get("final_answer_packet"))
    author_input_refs = _mapping(packet.get("author_input_refs"))
    unique_source_urls = _mapping(author_input_refs.get("unique_source_urls"))
    items: list[tuple[str, str]] = []
    for url, source_id in unique_source_urls.items():
        clean_url = _safe_text(url)
        clean_id = _safe_text(source_id)
        if clean_url and clean_id:
            items.append((clean_url, clean_id))
    return items


def _citation_eligible_source_ids(
    trace: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> list[str]:
    ids = _string_list(packet.get("citation_eligible_source_ids"))
    if ids:
        return ids
    eligibility = _mapping(packet.get("citation_eligibility"))
    ids = _string_list(eligibility.get("citation_eligible_source_ids"))
    if ids:
        return ids
    author_input_refs = _mapping(packet.get("author_input_refs"))
    ids = _string_list(author_input_refs.get("citation_source_ids"))
    if ids:
        return ids
    trace_eligibility = _mapping(trace.get("citation_eligibility"))
    return _string_list(trace_eligibility.get("citation_eligible_source_ids"))


def _official_source_custody_satisfied(
    trace: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> bool | None:
    candidates = (
        packet.get("official_current_custody_summary"),
        packet.get("official_current_source_custody"),
        trace.get("official_current_custody_summary"),
        trace.get("official_current_source_custody"),
    )
    for candidate in candidates:
        result = _custody_projection_satisfied(_mapping(candidate))
        if result is not None:
            return result
    status = _source_obligation_status(trace, packet)
    if status is None:
        return None
    if _status_is_satisfied(status):
        return True
    if _status_is_unsatisfied(status):
        return False
    return None


def _custody_projection_satisfied(projection: Mapping[str, Any]) -> bool | None:
    if not projection:
        return None
    requirements = _mapping_list(projection.get("requirements"))
    if requirements:
        statuses = [
            _safe_text(requirement.get("status"))
            for requirement in requirements
            if _safe_text(requirement.get("status"))
        ]
        if statuses:
            return all(status in _SATISFIED_STATUSES for status in statuses)
    records = _mapping_list(projection.get("records"))
    if records:
        terminal = [
            _safe_text(record.get("status"))
            for record in records
            if _safe_text(record.get("status")) in {
                "requirement_satisfied",
                "requirement_unsatisfied",
            }
        ]
        if terminal:
            return all(status == "requirement_satisfied" for status in terminal)
    direct = projection.get("source_custody_satisfied")
    if isinstance(direct, bool):
        return direct
    direct = projection.get("official_source_custody_satisfied")
    if isinstance(direct, bool):
        return direct
    return None


def _source_obligation_status(
    trace: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> str | None:
    direct = _safe_text(trace.get("source_obligation_status"))
    if direct:
        return direct
    obligations = _mapping_list(packet.get("source_obligations"))
    if not obligations:
        return None
    statuses = [
        _safe_text(obligation.get("status"))
        for obligation in obligations
        if _safe_text(obligation.get("status"))
    ]
    if not statuses:
        return None
    satisfied = [status for status in statuses if _status_is_satisfied(status)]
    unsatisfied = [status for status in statuses if _status_is_unsatisfied(status)]
    if unsatisfied and satisfied:
        return "partial"
    if unsatisfied:
        return "unsatisfied"
    if len(satisfied) == len(statuses):
        return "satisfied"
    return _UNKNOWN


def _source_custody_expected(profile_name: str | None) -> bool:
    return _source_custody_policy(profile_name) is not None


def _source_custody_fetch_required(profile_name: str | None) -> bool:
    policy = _source_custody_policy(profile_name)
    return bool(
        policy is not None
        and getattr(policy, "require_official_full_fetch_read", False)
    )


def _source_custody_policy(profile_name: str | None) -> Any | None:
    if not profile_name:
        return None
    try:
        return get_validation_profile(profile_name).source_custody_policy
    except KeyError:
        return None


def _has_official_doc_citations(
    cited_urls: Sequence[str],
    top_passages: Sequence[Mapping[str, Any]],
) -> bool:
    if any("docs.python.org" in url.casefold() for url in cited_urls):
        return True
    cited_set = set(cited_urls)
    return any(
        _safe_text(passage.get("url")) in cited_set
        and _safe_text(passage.get("source_tier")) == "official"
        for passage in top_passages
    )


def extract_cited_urls_from_text(text: Any) -> list[str]:
    """Extract sanitized HTTP(S) URLs visible in final answer text."""

    urls: list[str] = []
    for match in _HTTP_URL_RE.finditer(str(text or "")):
        url = _safe_url(match.group(0).rstrip(".,;:!?"))
        if url and url not in urls:
            urls.append(url)
    return urls


def _matched_cited_url(
    passage: Mapping[str, Any],
    *,
    cited_url_set: set[str],
    cited_url_by_key: Mapping[str, str],
    cited_source_id_set: set[str],
) -> str | None:
    url = _safe_url(passage.get("url"))
    if url:
        if url in cited_url_set:
            return url
        key = _url_match_key(url)
        if key and key in cited_url_by_key:
            return cited_url_by_key[key]
    source_id = str(passage.get("source_id") or "").strip()
    if source_id and source_id in cited_source_id_set:
        return url
    return None


def _url_match_key(value: Any) -> str:
    url = _safe_url(value)
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.netloc:
        return url.casefold()
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


def _mentions_custody_partial(answer_text: str) -> bool:
    normalized = answer_text.casefold()
    return "custody" in normalized and (
        "partial" in normalized or "unsatisfied" in normalized
    )


def _status_is_satisfied(status: str | None) -> bool:
    return _safe_text(status) in _SATISFIED_STATUSES


def _status_is_unsatisfied(status: str | None) -> bool:
    clean = _safe_text(status)
    return bool(clean and any(marker in clean for marker in _UNSATISFIED_MARKERS))


def _evidence_material_type(passage: Mapping[str, Any]) -> str:
    for key in (
        "evidence_material_type",
        "material_type",
        "source_material_type",
    ):
        value = _safe_text(passage.get(key))
        if value in {_SNIPPET_ONLY, _FULL_PAGE_FETCHED, _UNKNOWN}:
            return value
    if passage.get("full_page_fetched") is True:
        return _FULL_PAGE_FETCHED
    if passage.get("snippet_only") is True:
        return _SNIPPET_ONLY
    text = str(passage.get("text") or "")
    if text.startswith("[FULL_PAGE]"):
        return _FULL_PAGE_FETCHED
    if text.startswith("[SNIPPET]"):
        return _SNIPPET_ONLY
    return _UNKNOWN


def _stronger_material_type(current: str | None, incoming: str) -> str:
    order = {_UNKNOWN: 0, _SNIPPET_ONLY: 1, _FULL_PAGE_FETCHED: 2}
    if current is None:
        return incoming
    return incoming if order.get(incoming, 0) > order.get(current, 0) else current


def _author_provider_model_from_config(run_config: Any) -> tuple[str | None, str | None]:
    mode = str(getattr(run_config, "mode", "") or "")
    if mode in {"Fast", "Balanced"}:
        return (
            _safe_text(getattr(run_config, "fast_provider", None)),
            _safe_text(getattr(run_config, "fast_model", None)),
        )
    return (
        _safe_text(getattr(run_config, "smart_provider", None)),
        _safe_text(getattr(run_config, "smart_model", None)),
    )


def _profile_name(
    validation_profile: Any | None,
    preflight_context: Any | None,
) -> str | None:
    return _safe_text(
        getattr(validation_profile, "name", None)
        or getattr(preflight_context, "profile_name", None)
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        values = list(value)
    else:
        values = []
    return _unique_strings(values)


def _unique_strings(values: Sequence[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        clean = _safe_text(value)
        if clean and clean not in result:
            result.append(clean)
    return result


def _safe_count_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, int] = {}
    for key, item in value.items():
        clean_key = _safe_text(key)
        count = _optional_int(item)
        if clean_key and count is not None:
            result[clean_key] = count
    return dict(sorted(result.items()))


def _safe_text(value: Any, *, limit: int = 240) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _SENSITIVE_VALUE_MARKERS):
        return "[redacted]"
    return text[:limit]


def _safe_url(value: Any) -> str | None:
    text = _safe_text(value, limit=500)
    if not text or text == "[redacted]":
        return None
    parsed = urlparse(text)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        return None
    return text


def _first_text(*values: Any) -> str | None:
    for value in values:
        clean = _safe_text(value)
        if clean:
            return clean
    return None


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _list_count(value: Any) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return len(value)
    return 0


__all__ = [
    "SUBJECT_BUDGET_SUMMARY_SCHEMA_VERSION",
    "VALIDATION_OBSERVABILITY_SCHEMA_VERSION",
    "build_subject_budget_summary",
    "build_validation_observability",
    "extract_cited_urls_from_text",
]
