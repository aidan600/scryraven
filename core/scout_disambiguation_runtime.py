"""RunKernel-authorized Scout disambiguation runtime.

Scout is a narrow reconnaissance worker. It accepts an explicitly injected
adapter, normalizes Serper-shaped result metadata into direction hints, and
returns a DisambiguationReport for RunKernel reduction.

This module does not import RunKernel, legacy Scout, search providers, fetch/read
or retrieval code, SearchExecutor, citations, Author, or provider clients.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import urlparse

from core.initial_query_allocation_policy import (
    DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
)

SCOUT_DISAMBIGUATION_SCHEMA_VERSION = (
    "scout_disambiguation_runtime_ag_scout_disambiguation_runtime_01_v1"
)
SCOUT_DISAMBIGUATION_REPORT_SCHEMA_VERSION = (
    "scout_disambiguation_report_ag_scout_disambiguation_runtime_01_v1"
)
SCOUT_DISAMBIGUATION_OBSERVATION_SCHEMA_VERSION = (
    "scout_disambiguation_observation_ag_scout_disambiguation_runtime_01_v1"
)
SCOUT_DISAMBIGUATION_STAGE = "scout_disambiguation"
SCOUT_DISAMBIGUATION_REASON = (
    "scout_disambiguation_from_authorized_runtime_boundary"
)
SCOUT_DISAMBIGUATION_TRACE_KEY = "scout_disambiguation_report"
SCOUT_DISAMBIGUATION_REPORT_OWNER = "RunKernel.ScoutDisambiguationReport"

# The Scout runtime's bounded shape follows the single SearchOS allocation
# policy owner.  These remain per-component safety limits, never a global run
# total, and can be calibrated without changing the Scout schema.
SCOUT_MAX_QUERIES_PER_COMPONENT = (
    DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY.recon_candidate_ceiling_per_affected_component
)
SCOUT_MAX_DIMENSIONS_PER_COMPONENT = SCOUT_MAX_QUERIES_PER_COMPONENT

_EXPECTED_ACTION_TYPE = "scout_disambiguate"
_EXPECTED_OBSERVATION_TYPE = "scout_disambiguation_reported"

_ALLOWED_DIMENSION_KINDS = frozenset(
    {
        "entity_identity",
        "jurisdiction",
        "time_version_currentness",
        "rename_alias",
        "official_target_direction",
        "unknown_or_other",
    }
)

_ALLOWED_DIMENSION_STATUSES = frozenset(
    {"proposed", "open", "resolved", "unresolved"}
)

_ALLOWED_QUERY_KINDS = frozenset(
    {
        "all_time",
        "recent_current",
        "official_domain_probe",
        "alias_probe",
        "jurisdiction_probe",
        "unknown_or_other",
    }
)

_ALLOWED_QUERY_STATUSES = frozenset(
    {"executed_by_fake_adapter", "skipped_budget", "deferred", "blocked"}
)

_ALLOWED_HINT_KINDS = frozenset(
    {
        "organic",
        "knowledge_graph",
        "people_also_ask",
        "related_search",
        "news",
        "unknown_or_other",
    }
)

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "cache_row",
        "db",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "serper_payload",
        "token",
        "unbounded_text",
    }
)

_PRIVATE_VALUE_MARKERS = frozenset(
    {
        "api_key",
        "private_sentinel",
        "provider_payload",
        "raw_private",
        "raw_prompt",
        "raw_provider",
        "secret",
    }
)

_SAFE_FALSE_RETENTION_KEYS = frozenset(
    {
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "raw_prompt_retained",
        "raw_model_response_retained",
    }
)

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "admitted_sources",
        "author_input",
        "canonical_coverage",
        "citation",
        "citation_sources",
        "citations",
        "component_coverage_record",
        "current_answer_contract",
        "evidence",
        "evidence_ledger_admission",
        "evidence_sources",
        "final_answer",
        "final_answer_packet",
        "final_sources",
        "initial_answer_contract",
        "search_executor",
        "search_judgment_decision",
        "search_work_plan",
        "semantic_observation",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_REQUIRED_FALSE_FLAGS = {
    "evidence_admitted": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "fetch_read_retrieval_behavior_changed": False,
    "search_executor_runtime_activated": False,
    "search_work_plan_constructed": False,
    "contract_mutation_applied": False,
    "initial_answer_contract_mutated": False,
    "current_answer_contract_mutated": False,
    "amendment_admitted": False,
    "amendment_applied": False,
    "semantic_observation_admitted": False,
    "component_coverage_reduced": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "live_validation_run": False,
    "live_provider_calls_executed": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
}

_HINT_FALSE_FLAGS = {
    "evidence_admitted": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "fetch_read_retrieval_behavior_changed": False,
}

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_REQUIRED_FALSE_FLAGS,
        "accepted_authority",
        "author_behavior_changed",
        "author_executor_invoked",
        "citation_behavior_changed",
        "citation_rendered",
        "component_satisfied",
        "constructs_search_work_plan",
        "evidence_ledger_admitted",
        "fetch_executed",
        "live_search_called",
        "model_called",
        "planner_revision_applied",
        "provider_called",
        "provider_payload_retained",
        "provider_search_behavior_changed",
        "query_plan_activated",
        "read_executed",
        "retrieval_executed",
        "runtime_behavior_changed",
        "search_executed",
        "search_provider_called",
        "search_work_plan_activated",
    }
)

_REQUIRED_ACTION_INPUT_KEYS = (
    "run_id",
    "request_id",
    "parent_search_planner_proposal_id",
    "parent_search_planner_proposal_digest",
    "parent_question_meaning_record_id",
    "parent_question_meaning_record_digest",
    "component_id",
    "ambiguity_dimension_ids",
    "max_queries_per_component",
    "max_dimensions_per_component",
    "scout_schema_version",
)


class ScoutDisambiguationRuntimeError(ValueError):
    """Raised when Scout execution, binding validation, or reduction fails."""


class ScoutDisambiguationAdapter(Protocol):
    """Injected Scout adapter boundary."""

    def produce(self, scout_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return sanitized Serper-shaped Scout result hints."""


@dataclass(frozen=True, slots=True)
class ScoutDisambiguationInput:
    run_id: str
    request_id: str
    parent_search_planner_proposal_ref: Mapping[str, Any]
    parent_initial_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    parent_current_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    component_id: str = ""
    answer_component_ref: Mapping[str, Any] = field(default_factory=dict)
    ambiguity_dimensions: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    query_budget: Mapping[str, Any] = field(default_factory=dict)
    candidate_queries: Sequence[Mapping[str, Any] | str] = field(default_factory=tuple)
    safe_context: Mapping[str, Any] = field(default_factory=dict)
    closed_surface_flags: Mapping[str, Any] = field(default_factory=dict)

    def to_adapter_payload(self) -> dict[str, Any]:
        run_id = _required_token(self.run_id, "Scout input requires run_id")
        request_id = _required_token(
            self.request_id,
            "Scout input requires request_id",
        )
        component_id = _required_token(
            self.component_id,
            "Scout input requires component_id",
        )
        parent_planner_ref = _planner_ref_or_raise(
            self.parent_search_planner_proposal_ref
        )
        dimensions = _normalize_dimensions(
            self.ambiguity_dimensions,
            component_id=component_id,
        )
        candidate_queries = _normalize_candidate_queries(
            self.candidate_queries,
            dimensions=dimensions,
            default_status="deferred",
        )
        budget = _normalize_query_budget(
            self.query_budget,
            candidate_queries=candidate_queries,
            executed_query_count=0,
        )
        closed_flags = {**_REQUIRED_FALSE_FLAGS, **_safe_mapping(self.closed_surface_flags)}
        if any(bool(value) for value in closed_flags.values()):
            raise ScoutDisambiguationRuntimeError(
                "Scout input cannot open closed runtime surfaces"
            )
        _reject_forbidden_surface_claims(self.safe_context, context="Scout input")
        return {
            "schema_version": SCOUT_DISAMBIGUATION_SCHEMA_VERSION,
            "run_id": run_id,
            "request_id": request_id,
            "parent_search_planner_proposal_ref": parent_planner_ref,
            "parent_initial_contract_ref": _contract_ref_or_empty(
                self.parent_initial_contract_ref
            ),
            "parent_current_contract_ref": _contract_ref_or_empty(
                self.parent_current_contract_ref
            ),
            "component_id": component_id,
            "answer_component_ref": _json_safe(self.answer_component_ref),
            "ambiguity_dimensions": dimensions,
            "query_budget": budget,
            "candidate_queries": candidate_queries,
            "safe_context": _json_safe(self.safe_context),
            "closed_surface_flags": {key: bool(value) for key, value in closed_flags.items()},
        }


@dataclass(frozen=True, slots=True)
class ScoutDisambiguationExecutionResult:
    adapter_input: Mapping[str, Any]
    observation_payload: Mapping[str, Any]


def execute_scout_disambiguation_action(
    *,
    action: Any,
    scout_input: ScoutDisambiguationInput,
    adapter: ScoutDisambiguationAdapter
    | Callable[[Mapping[str, Any]], Mapping[str, Any]]
    | None = None,
) -> ScoutDisambiguationExecutionResult:
    """Call an explicitly injected Scout adapter and return observation payload."""

    if adapter is None:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation requires an explicitly injected adapter"
        )
    _validate_action_like(action=action, scout_input=scout_input)
    adapter_input = scout_input.to_adapter_payload()
    adapter_result = _call_adapter(adapter, adapter_input)
    observation_payload = build_scout_disambiguation_report_payload(
        adapter_result=adapter_result,
        scout_input=adapter_input,
        authorized_action_id=_clean_token(getattr(action, "action_id", None)),
    )
    return ScoutDisambiguationExecutionResult(
        adapter_input=adapter_input,
        observation_payload=observation_payload,
    )


def build_scout_disambiguation_report_payload(
    *,
    adapter_result: Mapping[str, Any],
    scout_input: Mapping[str, Any],
    authorized_action_id: str | None = None,
) -> dict[str, Any]:
    scout_input_ref = _scout_input_ref_for_observation(scout_input)
    result = _required_mapping(adapter_result, "Scout adapter result")
    _reject_forbidden_surface_claims(result, context="Scout adapter result")

    dimensions = _normalize_dimensions(
        scout_input_ref.get("ambiguity_dimensions"),
        component_id=str(scout_input_ref.get("component_id") or ""),
    )
    scout_queries = _normalize_report_queries(
        result.get("scout_queries")
        or result.get("queries")
        or scout_input_ref.get("candidate_queries"),
        dimensions=dimensions,
    )
    executed_query_count = _executed_query_count(scout_queries)
    query_budget = _normalize_query_budget(
        result.get("query_budget") or scout_input_ref.get("query_budget"),
        candidate_queries=scout_queries,
        executed_query_count=executed_query_count,
    )
    query_lookup = {
        str(query.get("query_id")): query
        for query in scout_queries
        if query.get("query_id")
    }
    scout_result_hints = _normalize_serper_hints(
        result,
        query_lookup=query_lookup,
    )
    likely_official_target_hints = _normalize_hint_collection(
        result.get("likely_official_target_hints")
        or result.get("candidate_target_hints"),
        allowed_keys={
            "hint_id",
            "query_id",
            "related_dimension_ids",
            "title",
            "link",
            "domain",
            "source",
            "official_target_hint",
            "interpretation_hint",
            "confidence_posture",
        },
        default_prefix="official-target-hint",
    )
    currentness_hints = _normalize_hint_collection(
        result.get("currentness_hints"),
        allowed_keys={
            "hint_id",
            "query_id",
            "related_dimension_ids",
            "title",
            "date",
            "source",
            "domain",
            "currentness_hint",
            "interpretation_hint",
            "confidence_posture",
        },
        default_prefix="currentness-hint",
    )
    candidate_interpretations = _normalize_interpretations(
        result.get("candidate_interpretations")
    )
    unresolved_ambiguities = _normalize_unresolved_ambiguities(
        result.get("unresolved_ambiguities"),
        dimensions=dimensions,
    )
    recommendations = _normalize_recommended_planner_revision_inputs(
        result.get("recommended_planner_revision_inputs")
    )
    non_executed = [
        query
        for query in scout_queries
        if query.get("execution_status") != "executed_by_fake_adapter"
    ]

    report_base = {
        "schema_version": SCOUT_DISAMBIGUATION_REPORT_SCHEMA_VERSION,
        "trace_key": SCOUT_DISAMBIGUATION_TRACE_KEY,
        "owner": SCOUT_DISAMBIGUATION_REPORT_OWNER,
        "run_id": scout_input_ref.get("run_id"),
        "request_id": scout_input_ref.get("request_id"),
        "authorized_action_id": authorized_action_id,
        "parent_search_planner_proposal_ref": _safe_mapping(
            scout_input_ref.get("parent_search_planner_proposal_ref")
        ),
        "parent_initial_contract_ref": _contract_ref_or_empty(
            scout_input_ref.get("parent_initial_contract_ref")
        ),
        "parent_current_contract_ref": _contract_ref_or_empty(
            scout_input_ref.get("parent_current_contract_ref")
        ),
        "component_id": scout_input_ref.get("component_id"),
        "answer_component_ref": _safe_mapping(
            scout_input_ref.get("answer_component_ref")
        ),
        "ambiguity_dimensions": dimensions,
        "query_budget": query_budget,
        "executed_query_count": executed_query_count,
        "scout_queries": scout_queries,
        "non_executed_candidate_queries": non_executed,
        "scout_result_hints": scout_result_hints,
        "likely_official_target_hints": likely_official_target_hints,
        "currentness_hints": currentness_hints,
        "candidate_interpretations": candidate_interpretations,
        "unresolved_ambiguities": unresolved_ambiguities,
        "recommended_planner_revision_inputs": recommendations,
        "confidence_posture": _clean_token(
            result.get("confidence_posture"),
            limit=120,
        )
        or "scout_hint_only",
        "disambiguation_posture": _clean_token(
            result.get("disambiguation_posture"),
            limit=120,
        )
        or "report_only",
        "closed_surface_flags": dict(_REQUIRED_FALSE_FLAGS),
        "retention_flags": {
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
        },
        "planner_revision_applied": False,
        **_REQUIRED_FALSE_FLAGS,
    }
    report_id = (
        "scout-disambiguation-report:"
        f"{_clean_token(scout_input_ref.get('request_id'))}:"
        f"{_clean_token(scout_input_ref.get('component_id'))}:"
        f"{_digest_json(_dedupe_payload(report_base))[:16]}"
    )
    report_without_digest = {**report_base, "report_id": report_id}
    report_digest = _digest_json(_report_digest_payload(report_without_digest))
    report = {**report_without_digest, "report_digest": report_digest}
    return {
        "schema_version": SCOUT_DISAMBIGUATION_OBSERVATION_SCHEMA_VERSION,
        "scout_input": scout_input_ref,
        "disambiguation_report": report,
    }


def build_scout_disambiguation_report_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    current_search_planner_proposal_state: Mapping[str, Any] | None = None,
    current_parent_initial_contract: Mapping[str, Any] | None = None,
    current_parent_current_contract: Mapping[str, Any] | None = None,
    existing_report_history: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Validate one Scout DisambiguationReport observation for RunKernel state."""

    clean_action_id = _required_token(
        action_id,
        "Scout report reduction requires action_id",
        limit=200,
    )
    clean_run_id = _required_token(run_id, "Scout report reduction requires run_id")
    clean_request_id = _required_token(
        request_id,
        "Scout report reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    payload = _safe_mapping(observation_payload)
    scout_input = _safe_mapping(payload.get("scout_input"))
    report = _safe_mapping(payload.get("disambiguation_report"))
    if payload.get("schema_version") != SCOUT_DISAMBIGUATION_OBSERVATION_SCHEMA_VERSION:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation observation schema version does not match"
        )
    if not scout_input or not report:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation observation requires scout_input and report"
        )
    _reject_forbidden_surface_claims(payload, context="Scout report observation")
    _validate_action_inputs(inputs)
    _validate_query_budget_against_action(
        action_inputs=inputs,
        query_budget=_safe_mapping(scout_input.get("query_budget")),
        context="Scout input",
    )
    _validate_query_budget_against_action(
        action_inputs=inputs,
        query_budget=_safe_mapping(report.get("query_budget")),
        context="Scout report",
    )

    if scout_input.get("run_id") != clean_run_id or report.get("run_id") != clean_run_id:
        raise ScoutDisambiguationRuntimeError(
            "Scout report run_id does not match the run"
        )
    if (
        scout_input.get("request_id") != clean_request_id
        or report.get("request_id") != clean_request_id
    ):
        raise ScoutDisambiguationRuntimeError(
            "Scout report request_id does not match the request"
        )
    if report.get("authorized_action_id") != clean_action_id:
        raise ScoutDisambiguationRuntimeError(
            "Scout report action_id binding does not match authorization"
        )
    if scout_input.get("schema_version") != SCOUT_DISAMBIGUATION_SCHEMA_VERSION:
        raise ScoutDisambiguationRuntimeError(
            "Scout input schema version does not match"
        )
    if report.get("schema_version") != SCOUT_DISAMBIGUATION_REPORT_SCHEMA_VERSION:
        raise ScoutDisambiguationRuntimeError(
            "Scout report schema version does not match"
        )
    if report.get("owner") != SCOUT_DISAMBIGUATION_REPORT_OWNER:
        raise ScoutDisambiguationRuntimeError("Scout report owner does not match")

    declared_digest = _clean_token(report.get("report_digest"), limit=128)
    if not declared_digest:
        raise ScoutDisambiguationRuntimeError("Scout report requires report_digest")
    recomputed_digest = _digest_json(_report_digest_payload(report))
    if declared_digest != recomputed_digest:
        raise ScoutDisambiguationRuntimeError(
            "stale Scout report: report digest does not match payload content"
        )

    parent_planner_ref = _planner_ref_or_raise(
        report.get("parent_search_planner_proposal_ref")
    )
    input_parent_planner_ref = _planner_ref_or_raise(
        scout_input.get("parent_search_planner_proposal_ref")
    )
    if parent_planner_ref != input_parent_planner_ref:
        raise ScoutDisambiguationRuntimeError(
            "Scout report parent planner ref does not match input"
        )
    current_parent_ref = planner_ref_from_search_planner_state(
        current_search_planner_proposal_state
    )
    if parent_planner_ref != current_parent_ref:
        raise ScoutDisambiguationRuntimeError(
            "stale parent planner digest: Scout report does not match current planner proposal"
        )
    _validate_action_parent_bindings(
        action_inputs=inputs,
        parent_planner_ref=parent_planner_ref,
    )
    _validate_parent_contract_bindings(
        action_inputs=inputs,
        scout_input=scout_input,
        report=report,
        current_parent_initial_contract=current_parent_initial_contract,
        current_parent_current_contract=current_parent_current_contract,
    )

    component_id = _clean_token(report.get("component_id"))
    if not component_id or component_id != _clean_token(scout_input.get("component_id")):
        raise ScoutDisambiguationRuntimeError(
            "Scout report component_id does not match input"
        )
    qmr = _safe_mapping(
        _safe_mapping(current_search_planner_proposal_state).get(
            "question_meaning_record"
        )
    )
    component = _component_from_qmr(qmr, component_id=component_id)
    if not component:
        raise ScoutDisambiguationRuntimeError(
            "Scout report component_id is not present in parent QMR"
        )

    dimensions = _safe_list(report.get("ambiguity_dimensions"))
    _validate_dimensions_against_component(
        dimensions=dimensions,
        action_inputs=inputs,
        component=component,
        qmr=qmr,
    )
    scout_queries = _safe_list(report.get("scout_queries"))
    _validate_queries(
        scout_queries,
        dimensions=dimensions,
        query_budget=_safe_mapping(report.get("query_budget")),
        action_inputs=inputs,
    )
    _validate_hints(
        report.get("scout_result_hints"),
        dimensions=dimensions,
        queries=scout_queries,
    )
    _validate_closed_report_flags(report)

    dedupe_key = _dedupe_key(report)
    for item in existing_report_history:
        if _safe_mapping(item).get("dedupe_key") == dedupe_key:
            raise ScoutDisambiguationRuntimeError(
                "duplicate Scout disambiguation report for the same planner/component context"
            )

    state = {
        "schema_version": SCOUT_DISAMBIGUATION_REPORT_SCHEMA_VERSION,
        "trace_key": SCOUT_DISAMBIGUATION_TRACE_KEY,
        "owner": SCOUT_DISAMBIGUATION_REPORT_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "report_id": report.get("report_id"),
        "report_digest": declared_digest,
        "dedupe_key": dedupe_key,
        "parent_search_planner_proposal_ref": parent_planner_ref,
        "parent_initial_contract_ref": _contract_ref_or_empty(
            report.get("parent_initial_contract_ref")
        ),
        "parent_current_contract_ref": _contract_ref_or_empty(
            report.get("parent_current_contract_ref")
        ),
        "component_id": component_id,
        "answer_component_ref": _safe_mapping(report.get("answer_component_ref")),
        "ambiguity_dimensions": dimensions,
        "query_budget": _safe_mapping(report.get("query_budget")),
        "executed_query_count": _non_negative_int(
            report.get("executed_query_count")
        ),
        "scout_queries": scout_queries,
        "non_executed_candidate_queries": _safe_list(
            report.get("non_executed_candidate_queries")
        ),
        "scout_result_hints": _safe_list(report.get("scout_result_hints")),
        "likely_official_target_hints": _safe_list(
            report.get("likely_official_target_hints")
        ),
        "currentness_hints": _safe_list(report.get("currentness_hints")),
        "candidate_interpretations": _safe_list(
            report.get("candidate_interpretations")
        ),
        "unresolved_ambiguities": _safe_list(report.get("unresolved_ambiguities")),
        "recommended_planner_revision_inputs": _safe_mapping(
            report.get("recommended_planner_revision_inputs")
        ),
        "confidence_posture": report.get("confidence_posture"),
        "disambiguation_posture": report.get("disambiguation_posture"),
        "closed_surface_flags": dict(_REQUIRED_FALSE_FLAGS),
        "retention_flags": _safe_mapping(report.get("retention_flags")),
        "scout_runtime_activated": True,
        "scout_report_reduced": True,
        "planner_revision_applied": False,
        **_REQUIRED_FALSE_FLAGS,
    }
    return _json_safe(state)


def build_scout_disambiguation_report_projection(
    *,
    report_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project Scout report state without raw/private data."""

    state = _safe_mapping(report_state)
    return {
        "owner": SCOUT_DISAMBIGUATION_REPORT_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": SCOUT_DISAMBIGUATION_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "report_id": state.get("report_id"),
        "report_digest": state.get("report_digest"),
        "dedupe_key": state.get("dedupe_key"),
        "parent_search_planner_proposal_ref": _safe_mapping(
            state.get("parent_search_planner_proposal_ref")
        ),
        "parent_initial_contract_ref": _safe_mapping(
            state.get("parent_initial_contract_ref")
        ),
        "parent_current_contract_ref": _safe_mapping(
            state.get("parent_current_contract_ref")
        ),
        "component_id": state.get("component_id"),
        "answer_component_ref": _safe_mapping(state.get("answer_component_ref")),
        "ambiguity_dimensions": _safe_list(state.get("ambiguity_dimensions")),
        "query_budget": _safe_mapping(state.get("query_budget")),
        "executed_query_count": _non_negative_int(
            state.get("executed_query_count")
        ),
        "scout_queries": _safe_list(state.get("scout_queries")),
        "non_executed_candidate_queries": _safe_list(
            state.get("non_executed_candidate_queries")
        ),
        "scout_result_hints": _safe_list(state.get("scout_result_hints")),
        "likely_official_target_hints": _safe_list(
            state.get("likely_official_target_hints")
        ),
        "currentness_hints": _safe_list(state.get("currentness_hints")),
        "candidate_interpretations": _safe_list(
            state.get("candidate_interpretations")
        ),
        "unresolved_ambiguities": _safe_list(state.get("unresolved_ambiguities")),
        "recommended_planner_revision_inputs": _safe_mapping(
            state.get("recommended_planner_revision_inputs")
        ),
        "confidence_posture": state.get("confidence_posture"),
        "disambiguation_posture": state.get("disambiguation_posture"),
        "closed_surface_flags": dict(_REQUIRED_FALSE_FLAGS),
        "retention_flags": _safe_mapping(state.get("retention_flags")),
        "scout_runtime_activated": True,
        "scout_report_reduced": True,
        "planner_revision_applied": False,
        **_REQUIRED_FALSE_FLAGS,
    }


def planner_ref_from_search_planner_state(
    search_planner_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = _safe_mapping(search_planner_state)
    if not state:
        return {}
    qmr_ref = _safe_mapping(state.get("question_meaning_record_ref"))
    qmr = _safe_mapping(state.get("question_meaning_record"))
    proposal_id = _clean_token(state.get("proposal_id"))
    proposal_digest = _clean_token(state.get("proposal_digest"), limit=128)
    qmr_id = _clean_token(
        qmr_ref.get("record_id") or qmr.get("record_id"),
    )
    qmr_digest = _clean_token(
        qmr_ref.get("record_digest") or qmr.get("record_digest"),
        limit=128,
    )
    if not proposal_id or not proposal_digest or not qmr_id or not qmr_digest:
        return {}
    return {
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
        "question_meaning_record_id": qmr_id,
        "question_meaning_record_digest": qmr_digest,
    }


def contract_ref_from_contract(
    contract: Mapping[str, Any] | None,
    *,
    source: str,
) -> dict[str, Any]:
    mapping = _safe_mapping(contract)
    if not mapping:
        return {}
    version = _clean_token(
        mapping.get("accepted_contract_version")
        or mapping.get("current_contract_version")
        or mapping.get("contract_version")
    )
    digest = _clean_token(
        mapping.get("accepted_contract_digest")
        or mapping.get("current_contract_digest")
        or mapping.get("contract_digest"),
        limit=128,
    )
    if not version or not digest:
        return {}
    return {
        "source": _clean_token(source) or "answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _validate_action_like(
    *,
    action: Any,
    scout_input: ScoutDisambiguationInput,
) -> None:
    if action is None:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation requires an authorized action"
        )
    stage = getattr(action, "stage", None)
    action_type = _enum_or_text(getattr(action, "action_type", None))
    expected_observation_type = _enum_or_text(
        getattr(action, "expected_observation_type", None)
    )
    inputs = _safe_mapping(getattr(action, "inputs", None))
    if stage != SCOUT_DISAMBIGUATION_STAGE:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation action stage does not match"
        )
    if action_type != _EXPECTED_ACTION_TYPE:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation action type does not match"
        )
    if expected_observation_type != _EXPECTED_OBSERVATION_TYPE:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation expected observation type does not match"
        )
    if _clean_token(getattr(action, "run_id", None)) != _clean_token(
        scout_input.run_id
    ):
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation action run_id does not match input"
        )
    if _clean_token(inputs.get("request_id")) != _clean_token(scout_input.request_id):
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation action request_id does not match input"
        )
    input_payload = scout_input.to_adapter_payload()
    parent_ref = _safe_mapping(input_payload.get("parent_search_planner_proposal_ref"))
    if (
        inputs.get("parent_search_planner_proposal_id") != parent_ref.get("proposal_id")
        or inputs.get("parent_search_planner_proposal_digest")
        != parent_ref.get("proposal_digest")
        or inputs.get("parent_question_meaning_record_id")
        != parent_ref.get("question_meaning_record_id")
        or inputs.get("parent_question_meaning_record_digest")
        != parent_ref.get("question_meaning_record_digest")
    ):
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation action parent planner binding does not match input"
        )
    if _clean_token(inputs.get("component_id")) != _clean_token(
        input_payload.get("component_id")
    ):
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation action component_id does not match input"
        )
    _validate_query_budget_against_action(
        action_inputs=inputs,
        query_budget=_safe_mapping(input_payload.get("query_budget")),
        context="Scout input",
    )
    action_dimension_ids = _text_list(inputs.get("ambiguity_dimension_ids"))
    input_dimension_ids = [
        str(item.get("dimension_id"))
        for item in _safe_list(input_payload.get("ambiguity_dimensions"))
    ]
    if action_dimension_ids != input_dimension_ids:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation action ambiguity dimensions do not match input"
        )
    if inputs.get("scout_schema_version") != SCOUT_DISAMBIGUATION_SCHEMA_VERSION:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation action schema version does not match input"
        )


def _call_adapter(
    adapter: ScoutDisambiguationAdapter | Callable[[Mapping[str, Any]], Mapping[str, Any]],
    adapter_input: Mapping[str, Any],
) -> Mapping[str, Any]:
    if hasattr(adapter, "produce"):
        result = adapter.produce(adapter_input)  # type: ignore[union-attr]
    else:
        result = adapter(adapter_input)  # type: ignore[misc]
    if not isinstance(result, Mapping):
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation adapter must return a mapping"
        )
    return result


def _normalize_dimensions(
    value: Any,
    *,
    component_id: str,
) -> list[dict[str, Any]]:
    items = _safe_list(value)
    if not items:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation requires ambiguity dimensions"
        )
    if len(items) > SCOUT_MAX_DIMENSIONS_PER_COMPONENT:
        raise ScoutDisambiguationRuntimeError(
            "Scout disambiguation exceeds max 5 dimensions per component"
        )
    dimensions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        mapping = _required_mapping(item, "ambiguity dimension")
        dimension_id = _required_token(
            mapping.get("dimension_id"),
            "ambiguity dimension requires dimension_id",
        )
        if dimension_id in seen:
            raise ScoutDisambiguationRuntimeError(
                f"duplicate ambiguity dimension id: {dimension_id}"
            )
        seen.add(dimension_id)
        kind = _clean_token(mapping.get("dimension_kind")) or "unknown_or_other"
        if kind not in _ALLOWED_DIMENSION_KINDS:
            raise ScoutDisambiguationRuntimeError(
                f"unsupported ambiguity dimension kind: {kind}"
            )
        related_slots = _text_list(mapping.get("related_semantic_slot_ids"))
        if not related_slots:
            raise ScoutDisambiguationRuntimeError(
                f"ambiguity dimension {dimension_id} requires related semantic slots"
            )
        priority = _bounded_int(
            mapping.get("priority") if mapping.get("priority") is not None else index,
            minimum=1,
            maximum=100,
            label="ambiguity dimension priority",
        )
        status = _clean_token(mapping.get("status")) or "open"
        if status not in _ALLOWED_DIMENSION_STATUSES:
            raise ScoutDisambiguationRuntimeError(
                f"unsupported ambiguity dimension status: {status}"
            )
        summary = _required_token(
            mapping.get("summary"),
            f"ambiguity dimension {dimension_id} requires summary",
            limit=360,
        )
        dimensions.append(
            _without_empty(
                {
                    "dimension_id": dimension_id,
                    "dimension_kind": kind,
                    "summary": summary,
                    "related_semantic_slot_ids": related_slots,
                    "priority": priority,
                    "status": status,
                    "materiality": _clean_token(mapping.get("materiality"))
                    or "material",
                    "component_id": component_id,
                }
            )
        )
    return dimensions


def _normalize_candidate_queries(
    value: Any,
    *,
    dimensions: Sequence[Mapping[str, Any]],
    default_status: str,
) -> list[dict[str, Any]]:
    items = _safe_list(value)
    out: list[dict[str, Any]] = []
    dimension_ids = [str(item["dimension_id"]) for item in dimensions]
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            mapping: Mapping[str, Any] = {
                "query_text": item,
                "related_dimension_ids": dimension_ids[:1],
            }
        else:
            mapping = _required_mapping(item, "Scout candidate query")
        query_id = _clean_token(mapping.get("query_id")) or f"scout-query:{index}"
        query_text = _clean_token(
            mapping.get("safe_query_text") or mapping.get("query_text"),
            limit=360,
        )
        if not query_text:
            raise ScoutDisambiguationRuntimeError(
                f"Scout query {query_id} requires safe query text"
            )
        related_ids = _text_list(mapping.get("related_dimension_ids"))
        if not related_ids:
            raise ScoutDisambiguationRuntimeError(
                f"Scout query {query_id} requires related dimension ids"
            )
        _require_related_dimensions(related_ids, dimension_ids, context="Scout query")
        query_kind = _clean_token(mapping.get("query_kind")) or "unknown_or_other"
        if query_kind not in _ALLOWED_QUERY_KINDS:
            raise ScoutDisambiguationRuntimeError(
                f"unsupported Scout query kind: {query_kind}"
            )
        status = _clean_token(mapping.get("execution_status")) or default_status
        if status not in _ALLOWED_QUERY_STATUSES:
            raise ScoutDisambiguationRuntimeError(
                f"unsupported Scout query execution status: {status}"
            )
        if mapping.get("not_live") is False:
            raise ScoutDisambiguationRuntimeError(
                f"Scout query {query_id} claims live execution"
            )
        if mapping.get("provider_payload_retained") is True:
            raise ScoutDisambiguationRuntimeError(
                f"Scout query {query_id} claims provider payload retention"
            )
        out.append(
            _without_empty(
                {
                    "query_id": query_id,
                    "safe_query_text": query_text,
                    "query_kind": query_kind,
                    "priority": _bounded_int(
                        mapping.get("priority") or index,
                        minimum=1,
                        maximum=100,
                        label="Scout query priority",
                    ),
                    "related_dimension_ids": related_ids,
                    "execution_status": status,
                    "search_vertical": _clean_token(
                        mapping.get("search_vertical")
                    )
                    or "search",
                    "provider_hint": _clean_token(mapping.get("provider_hint"))
                    or "serper",
                    "locale": _clean_token(mapping.get("locale")),
                    "country": _clean_token(mapping.get("country")),
                    "language": _clean_token(mapping.get("language")),
                    "not_live": True,
                    "provider_payload_retained": False,
                    "fetch_read_retrieval_behavior_changed": False,
                    "source_obligation_satisfied": False,
                }
            )
        )
    return out


def _normalize_report_queries(
    value: Any,
    *,
    dimensions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    queries = _normalize_candidate_queries(
        value,
        dimensions=dimensions,
        default_status="executed_by_fake_adapter",
    )
    if not queries:
        raise ScoutDisambiguationRuntimeError("Scout report requires query records")
    return queries


def _normalize_query_budget(
    value: Any,
    *,
    candidate_queries: Sequence[Mapping[str, Any]],
    executed_query_count: int,
) -> dict[str, Any]:
    mapping = _safe_mapping(value)
    max_queries = _bounded_int(
        mapping.get("max_queries_per_component") or SCOUT_MAX_QUERIES_PER_COMPONENT,
        minimum=0,
        maximum=SCOUT_MAX_QUERIES_PER_COMPONENT,
        label="max_queries_per_component",
    )
    max_dimensions = _bounded_int(
        mapping.get("max_dimensions_per_component")
        or SCOUT_MAX_DIMENSIONS_PER_COMPONENT,
        minimum=0,
        maximum=SCOUT_MAX_DIMENSIONS_PER_COMPONENT,
        label="max_dimensions_per_component",
    )
    authorized = _bounded_int(
        mapping.get("authorized_query_count")
        if mapping.get("authorized_query_count") is not None
        else max_queries,
        minimum=0,
        maximum=SCOUT_MAX_QUERIES_PER_COMPONENT,
        label="authorized_query_count",
    )
    skipped = sum(
        1
        for query in candidate_queries
        if query.get("execution_status") in {"skipped_budget", "deferred", "blocked"}
    )
    remaining = max(0, authorized - int(executed_query_count or 0))
    return {
        "max_queries_per_component": max_queries,
        "max_dimensions_per_component": max_dimensions,
        "authorized_query_count": authorized,
        "executed_query_count": int(executed_query_count or 0),
        "skipped_query_count": skipped,
        "remaining_query_budget": remaining,
        "budget_exhausted": remaining == 0,
        "live_provider_calls_executed": False,
    }


def _normalize_serper_hints(
    result: Mapping[str, Any],
    *,
    query_lookup: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    raw_hints: list[tuple[str, Mapping[str, Any]]] = []
    for item in _safe_list(result.get("scout_result_hints")):
        mapping = _required_mapping(item, "Scout result hint")
        raw_hints.append((_clean_token(mapping.get("hint_kind")) or "unknown_or_other", mapping))
    for item in _safe_list(result.get("organic_results") or result.get("organic")):
        raw_hints.append(("organic", _required_mapping(item, "organic hint")))
    kg = result.get("knowledgeGraph") or result.get("knowledge_graph")
    if isinstance(kg, Mapping):
        raw_hints.append(("knowledge_graph", kg))
    for item in _safe_list(result.get("peopleAlsoAsk") or result.get("people_also_ask")):
        raw_hints.append(
            ("people_also_ask", _required_mapping(item, "people also ask hint"))
        )
    for item in _safe_list(result.get("relatedSearches") or result.get("related_searches")):
        raw_hints.append(
            ("related_search", _required_mapping(item, "related search hint"))
        )
    for item in _safe_list(result.get("news") or result.get("news_results")):
        raw_hints.append(("news", _required_mapping(item, "news hint")))

    out: list[dict[str, Any]] = []
    for index, (hint_kind, item) in enumerate(raw_hints, start=1):
        if hint_kind not in _ALLOWED_HINT_KINDS:
            hint_kind = "unknown_or_other"
        hint = _normalize_one_hint(
            item,
            hint_kind=hint_kind,
            index=index,
            query_lookup=query_lookup,
        )
        out.append(hint)
    return out


def _normalize_one_hint(
    item: Mapping[str, Any],
    *,
    hint_kind: str,
    index: int,
    query_lookup: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _reject_forbidden_surface_claims(item, context="Scout result hint")
    query_id = _clean_token(item.get("query_id"))
    if not query_id and len(query_lookup) == 1:
        query_id = next(iter(query_lookup))
    if not query_id:
        raise ScoutDisambiguationRuntimeError("Scout result hint requires query_id")
    related_ids = _text_list(item.get("related_dimension_ids"))
    if not related_ids:
        related_ids = _text_list(_safe_mapping(query_lookup.get(query_id)).get("related_dimension_ids"))
    if not related_ids:
        raise ScoutDisambiguationRuntimeError(
            "Scout result hint requires related dimension ids"
        )
    link = _clean_token(item.get("link") or item.get("website"), limit=600)
    domain = _clean_token(item.get("domain") or item.get("source"), limit=240)
    if not domain and link:
        domain = _domain_from_url(link)
    hint_id = _clean_token(item.get("hint_id")) or f"hint:{query_id}:{hint_kind}:{index}"
    return _without_empty(
        {
            "hint_id": hint_id,
            "hint_kind": hint_kind,
            "query_id": query_id,
            "related_dimension_ids": related_ids,
            "title": _clean_token(item.get("title"), limit=320),
            "type": _clean_token(item.get("type"), limit=160),
            "link": link,
            "snippet": _clean_token(item.get("snippet"), limit=700),
            "position": _optional_int(item.get("position")),
            "date": _clean_token(item.get("date"), limit=120),
            "source": _clean_token(item.get("source"), limit=240),
            "domain": domain,
            "attributes": _safe_shallow_mapping(item.get("attributes")),
            "sitelinks": _safe_sitelinks(item.get("sitelinks")),
            "description": _clean_token(item.get("description"), limit=700),
            "description_source": _clean_token(
                item.get("descriptionSource") or item.get("description_source"),
                limit=240,
            ),
            "description_link": _clean_token(
                item.get("descriptionLink") or item.get("description_link"),
                limit=600,
            ),
            "image_url": _clean_token(
                item.get("imageUrl") or item.get("image_url"),
                limit=600,
            ),
            "question": _clean_token(item.get("question"), limit=360),
            "related_query": _clean_token(
                item.get("related_query") or item.get("query"),
                limit=360,
            ),
            "interpretation_hint": _clean_token(
                item.get("interpretation_hint"),
                limit=420,
            ),
            "currentness_hint": _clean_token(item.get("currentness_hint"), limit=420),
            "official_target_hint": _clean_token(
                item.get("official_target_hint"),
                limit=420,
            ),
            "confidence_posture": _clean_token(
                item.get("confidence_posture"),
                limit=120,
            )
            or "hint_only",
            **_HINT_FALSE_FLAGS,
        }
    )


def _normalize_hint_collection(
    value: Any,
    *,
    allowed_keys: set[str],
    default_prefix: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, item in enumerate(_safe_list(value), start=1):
        mapping = _required_mapping(item, default_prefix)
        _reject_forbidden_surface_claims(mapping, context=default_prefix)
        clean = {
            key: _json_safe(mapping.get(key))
            for key in allowed_keys
            if mapping.get(key) not in (None, "", [], {})
        }
        clean["hint_id"] = _clean_token(clean.get("hint_id")) or f"{default_prefix}:{index}"
        clean.update(_HINT_FALSE_FLAGS)
        out.append(_without_empty(clean))
    return out


def _normalize_interpretations(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, item in enumerate(_safe_list(value), start=1):
        mapping = _required_mapping(item, "candidate interpretation")
        _reject_forbidden_surface_claims(mapping, context="candidate interpretation")
        out.append(
            _without_empty(
                {
                    "interpretation_id": _clean_token(
                        mapping.get("interpretation_id")
                    )
                    or f"interpretation:{index}",
                    "summary": _clean_token(mapping.get("summary"), limit=420),
                    "related_dimension_ids": _text_list(
                        mapping.get("related_dimension_ids")
                    ),
                    "supporting_hint_ids": _text_list(mapping.get("supporting_hint_ids")),
                    "confidence_posture": _clean_token(
                        mapping.get("confidence_posture"),
                        limit=120,
                    )
                    or "hint_only",
                    **_HINT_FALSE_FLAGS,
                }
            )
        )
    return out


def _normalize_unresolved_ambiguities(
    value: Any,
    *,
    dimensions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    dimension_ids = [str(item.get("dimension_id")) for item in dimensions]
    out: list[dict[str, Any]] = []
    for index, item in enumerate(_safe_list(value), start=1):
        mapping = _required_mapping(item, "unresolved ambiguity")
        related_ids = _text_list(mapping.get("related_dimension_ids"))
        if related_ids:
            _require_related_dimensions(
                related_ids,
                dimension_ids,
                context="unresolved ambiguity",
            )
        out.append(
            _without_empty(
                {
                    "unresolved_id": _clean_token(mapping.get("unresolved_id"))
                    or f"unresolved:{index}",
                    "summary": _clean_token(mapping.get("summary"), limit=420),
                    "related_dimension_ids": related_ids,
                    "status": _clean_token(mapping.get("status")) or "unresolved",
                }
            )
        )
    return out


def _normalize_recommended_planner_revision_inputs(value: Any) -> dict[str, Any]:
    mapping = _safe_mapping(value)
    if not mapping:
        return {
            "resolved_candidate_interpretations": [],
            "unresolved_ambiguity_dimensions": [],
            "suggested_slot_updates": [],
            "suggested_component_search_requirement_adjustments": [],
            "suggested_source_obligation_focus": [],
            "suggested_caveats": [],
            "candidate_official_target_hints": [],
            "planner_revision_applied": False,
            "contract_mutation_applied": False,
        }
    _reject_forbidden_surface_claims(
        mapping,
        context="recommended planner revision inputs",
    )
    return {
        "resolved_candidate_interpretations": _safe_list(
            mapping.get("resolved_candidate_interpretations")
        ),
        "unresolved_ambiguity_dimensions": _safe_list(
            mapping.get("unresolved_ambiguity_dimensions")
        ),
        "suggested_slot_updates": _safe_list(mapping.get("suggested_slot_updates")),
        "suggested_component_search_requirement_adjustments": _safe_list(
            mapping.get("suggested_component_search_requirement_adjustments")
        ),
        "suggested_source_obligation_focus": _safe_list(
            mapping.get("suggested_source_obligation_focus")
        ),
        "suggested_caveats": _text_list(mapping.get("suggested_caveats"), limit=260),
        "candidate_official_target_hints": _safe_list(
            mapping.get("candidate_official_target_hints")
        ),
        "planner_revision_applied": False,
        "contract_mutation_applied": False,
    }


def _validate_action_inputs(inputs: Mapping[str, Any]) -> None:
    missing = [key for key in _REQUIRED_ACTION_INPUT_KEYS if key not in inputs]
    if missing:
        raise ScoutDisambiguationRuntimeError(
            "Scout action missing required bindings: " + ", ".join(missing)
        )
    if inputs.get("scout_schema_version") != SCOUT_DISAMBIGUATION_SCHEMA_VERSION:
        raise ScoutDisambiguationRuntimeError(
            "Scout action binds the wrong schema version"
        )
    if _non_negative_int(inputs.get("max_queries_per_component")) > SCOUT_MAX_QUERIES_PER_COMPONENT:
        raise ScoutDisambiguationRuntimeError(
            "Scout action exceeds max queries per component"
        )
    if _non_negative_int(inputs.get("max_dimensions_per_component")) > SCOUT_MAX_DIMENSIONS_PER_COMPONENT:
        raise ScoutDisambiguationRuntimeError(
            "Scout action exceeds max dimensions per component"
        )


def _validate_query_budget_against_action(
    *,
    action_inputs: Mapping[str, Any],
    query_budget: Mapping[str, Any],
    context: str,
) -> None:
    action_max_queries = _non_negative_int(
        action_inputs.get("max_queries_per_component")
    )
    action_max_dimensions = _non_negative_int(
        action_inputs.get("max_dimensions_per_component")
    )
    if not query_budget:
        raise ScoutDisambiguationRuntimeError(f"{context} requires query budget")
    budget_max_queries = _non_negative_int(
        query_budget.get("max_queries_per_component")
    )
    authorized_queries = _non_negative_int(query_budget.get("authorized_query_count"))
    executed_queries = _non_negative_int(query_budget.get("executed_query_count"))
    budget_max_dimensions = _non_negative_int(
        query_budget.get("max_dimensions_per_component")
    )
    if budget_max_queries > action_max_queries:
        raise ScoutDisambiguationRuntimeError(
            f"{context} query budget exceeds authorized max_queries_per_component"
        )
    if authorized_queries > action_max_queries:
        raise ScoutDisambiguationRuntimeError(
            f"{context} query budget exceeds authorized_query_count"
        )
    if executed_queries > action_max_queries:
        raise ScoutDisambiguationRuntimeError(
            f"{context} executed query count exceeds authorized budget"
        )
    if budget_max_dimensions > action_max_dimensions:
        raise ScoutDisambiguationRuntimeError(
            f"{context} dimension budget exceeds authorized max_dimensions_per_component"
        )


def _validate_action_parent_bindings(
    *,
    action_inputs: Mapping[str, Any],
    parent_planner_ref: Mapping[str, Any],
) -> None:
    expected = {
        "parent_search_planner_proposal_id": parent_planner_ref.get("proposal_id"),
        "parent_search_planner_proposal_digest": parent_planner_ref.get(
            "proposal_digest"
        ),
        "parent_question_meaning_record_id": parent_planner_ref.get(
            "question_meaning_record_id"
        ),
        "parent_question_meaning_record_digest": parent_planner_ref.get(
            "question_meaning_record_digest"
        ),
    }
    for key, value in expected.items():
        if action_inputs.get(key) != value:
            raise ScoutDisambiguationRuntimeError(
                "Scout action parent planner binding is stale"
            )


def _validate_parent_contract_bindings(
    *,
    action_inputs: Mapping[str, Any],
    scout_input: Mapping[str, Any],
    report: Mapping[str, Any],
    current_parent_initial_contract: Mapping[str, Any] | None,
    current_parent_current_contract: Mapping[str, Any] | None,
) -> None:
    expected_initial = contract_ref_from_contract(
        current_parent_initial_contract,
        source="initial_answer_contract",
    )
    expected_current = contract_ref_from_contract(
        current_parent_current_contract,
        source="current_answer_contract",
    )
    _validate_one_contract_binding(
        label="parent_initial_contract",
        action_version=action_inputs.get("parent_initial_contract_version"),
        action_digest=action_inputs.get("parent_initial_contract_digest"),
        input_ref=_safe_mapping(scout_input.get("parent_initial_contract_ref")),
        report_ref=_safe_mapping(report.get("parent_initial_contract_ref")),
        expected_ref=expected_initial,
    )
    _validate_one_contract_binding(
        label="parent_current_contract",
        action_version=action_inputs.get("parent_current_contract_version"),
        action_digest=action_inputs.get("parent_current_contract_digest"),
        input_ref=_safe_mapping(scout_input.get("parent_current_contract_ref")),
        report_ref=_safe_mapping(report.get("parent_current_contract_ref")),
        expected_ref=expected_current,
    )


def _validate_one_contract_binding(
    *,
    label: str,
    action_version: Any,
    action_digest: Any,
    input_ref: Mapping[str, Any],
    report_ref: Mapping[str, Any],
    expected_ref: Mapping[str, Any],
) -> None:
    expected_version = _clean_token(expected_ref.get("contract_version"))
    expected_digest = _clean_token(expected_ref.get("contract_digest"), limit=128)
    action_version_text = _clean_token(action_version)
    action_digest_text = _clean_token(action_digest, limit=128)
    input_version = _clean_token(input_ref.get("contract_version"))
    input_digest = _clean_token(input_ref.get("contract_digest"), limit=128)
    report_version = _clean_token(report_ref.get("contract_version"))
    report_digest = _clean_token(report_ref.get("contract_digest"), limit=128)
    if expected_ref:
        if action_version_text != expected_version or action_digest_text != expected_digest:
            raise ScoutDisambiguationRuntimeError(
                f"stale parent digest: {label} action binding is not current"
            )
        if input_version != expected_version or input_digest != expected_digest:
            raise ScoutDisambiguationRuntimeError(
                f"stale parent digest: {label} input is not current"
            )
        if report_version != expected_version or report_digest != expected_digest:
            raise ScoutDisambiguationRuntimeError(
                f"stale parent digest: {label} report is not current"
            )
        return
    if (
        action_version_text
        or action_digest_text
        or input_version
        or input_digest
        or report_version
        or report_digest
    ):
        raise ScoutDisambiguationRuntimeError(
            f"stale parent digest: {label} was bound but no current parent exists"
        )


def _component_from_qmr(
    qmr: Mapping[str, Any],
    *,
    component_id: str,
) -> dict[str, Any]:
    for item in _safe_list(qmr.get("answer_components")):
        mapping = _safe_mapping(item)
        if mapping.get("component_id") == component_id:
            return mapping
    return {}


def _validate_dimensions_against_component(
    *,
    dimensions: Sequence[Any],
    action_inputs: Mapping[str, Any],
    component: Mapping[str, Any],
    qmr: Mapping[str, Any],
) -> None:
    action_max_dimensions = _non_negative_int(
        action_inputs.get("max_dimensions_per_component")
    )
    if len(dimensions) > action_max_dimensions:
        raise ScoutDisambiguationRuntimeError(
            "Scout report dimensions exceed authorized max_dimensions_per_component"
        )
    if len(dimensions) > SCOUT_MAX_DIMENSIONS_PER_COMPONENT:
        raise ScoutDisambiguationRuntimeError(
            "Scout report exceeds max 5 dimensions per component"
        )
    dimension_ids = []
    slot_ids = {
        str(slot.get("slot_id"))
        for slot in _safe_list(qmr.get("semantic_slots"))
        if isinstance(slot, Mapping) and slot.get("slot_id")
    }
    component_slot_ids = set(_text_list(component.get("semantic_slot_ids"))) or slot_ids
    for item in dimensions:
        mapping = _required_mapping(item, "Scout report dimension")
        dimension_id = _required_token(
            mapping.get("dimension_id"),
            "Scout report dimension requires id",
        )
        dimension_ids.append(dimension_id)
        if mapping.get("component_id") != component.get("component_id"):
            raise ScoutDisambiguationRuntimeError(
                "Scout report dimension is not scoped to the selected component"
            )
        related_slots = _text_list(mapping.get("related_semantic_slot_ids"))
        if not related_slots:
            raise ScoutDisambiguationRuntimeError(
                "Scout report dimension requires related semantic slots"
            )
        if not set(related_slots).issubset(component_slot_ids | slot_ids):
            raise ScoutDisambiguationRuntimeError(
                "Scout report dimension references semantic slots outside parent QMR"
            )
    if len(set(dimension_ids)) != len(dimension_ids):
        raise ScoutDisambiguationRuntimeError("duplicate Scout report dimension id")
    if _text_list(action_inputs.get("ambiguity_dimension_ids")) != dimension_ids:
        raise ScoutDisambiguationRuntimeError(
            "Scout report dimensions do not match authorized dimensions"
        )


def _validate_queries(
    queries: Sequence[Any],
    *,
    dimensions: Sequence[Mapping[str, Any]],
    query_budget: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> None:
    dimension_ids = [
        str(item.get("dimension_id"))
        for item in dimensions
        if isinstance(item, Mapping) and item.get("dimension_id")
    ]
    executed_count = 0
    query_ids: list[str] = []
    for item in queries:
        query = _required_mapping(item, "Scout query")
        query_id = _clean_token(query.get("query_id"))
        query_text = _clean_token(
            query.get("safe_query_text") or query.get("query_text"),
            limit=360,
        )
        related_ids = _text_list(query.get("related_dimension_ids"))
        if not query_id or not query_text or not related_ids:
            raise ScoutDisambiguationRuntimeError(
                "Scout query requires id, text, and related dimension ids"
            )
        query_ids.append(query_id)
        _require_related_dimensions(related_ids, dimension_ids, context="Scout query")
        if query.get("not_live") is not True:
            raise ScoutDisambiguationRuntimeError(
                "Scout query must be explicitly marked not_live"
            )
        if query.get("provider_payload_retained", False) is not False:
            raise ScoutDisambiguationRuntimeError(
                "Scout query must not retain provider payloads"
            )
        if query.get("fetch_read_retrieval_behavior_changed") is True:
            raise ScoutDisambiguationRuntimeError(
                "Scout query claims fetch/read/retrieval behavior"
            )
        if query.get("source_obligation_satisfied") is True:
            raise ScoutDisambiguationRuntimeError(
                "Scout query claims source-obligation satisfaction"
            )
        if query.get("execution_status") == "executed_by_fake_adapter":
            executed_count += 1
    if len(set(query_ids)) != len(query_ids):
        raise ScoutDisambiguationRuntimeError("duplicate Scout query id")
    if executed_count > SCOUT_MAX_QUERIES_PER_COMPONENT:
        raise ScoutDisambiguationRuntimeError(
            "Scout report exceeds max 5 executed queries per component"
        )
    if executed_count > _non_negative_int(action_inputs.get("max_queries_per_component")):
        raise ScoutDisambiguationRuntimeError(
            "Scout report executed more queries than the authorized budget"
        )
    if executed_count > _non_negative_int(query_budget.get("authorized_query_count")):
        raise ScoutDisambiguationRuntimeError(
            "Scout report executed more queries than authorized"
        )
    if query_budget.get("live_provider_calls_executed") is not False:
        raise ScoutDisambiguationRuntimeError(
            "Scout query budget must not claim live provider calls"
        )


def _validate_hints(
    hints: Any,
    *,
    dimensions: Sequence[Mapping[str, Any]],
    queries: Sequence[Mapping[str, Any]],
) -> None:
    dimension_ids = [
        str(item.get("dimension_id"))
        for item in dimensions
        if isinstance(item, Mapping) and item.get("dimension_id")
    ]
    query_ids = {
        str(item.get("query_id"))
        for item in queries
        if isinstance(item, Mapping) and item.get("query_id")
    }
    for item in _safe_list(hints):
        hint = _required_mapping(item, "Scout result hint")
        if hint.get("hint_kind") not in _ALLOWED_HINT_KINDS:
            raise ScoutDisambiguationRuntimeError("Scout hint kind is unsupported")
        if hint.get("query_id") not in query_ids:
            raise ScoutDisambiguationRuntimeError(
                "Scout hint references an unknown query"
            )
        related_ids = _text_list(hint.get("related_dimension_ids"))
        if not related_ids:
            raise ScoutDisambiguationRuntimeError(
                "Scout hint requires related dimension ids"
            )
        _require_related_dimensions(related_ids, dimension_ids, context="Scout hint")
        for key, expected in _HINT_FALSE_FLAGS.items():
            if hint.get(key) is not expected:
                raise ScoutDisambiguationRuntimeError(
                    "Scout hint must keep evidence/citation/source flags false"
                )


def _validate_closed_report_flags(report: Mapping[str, Any]) -> None:
    for key, expected in _REQUIRED_FALSE_FLAGS.items():
        value = report.get(
            key,
            False if key in _SAFE_FALSE_RETENTION_KEYS else None,
        )
        if value is not expected:
            raise ScoutDisambiguationRuntimeError(
                f"Scout report must keep {key} false"
            )
    flags = _safe_mapping(report.get("closed_surface_flags"))
    for key, expected in _REQUIRED_FALSE_FLAGS.items():
        value = flags.get(
            key,
            False if key in _SAFE_FALSE_RETENTION_KEYS else None,
        )
        if value is not expected:
            raise ScoutDisambiguationRuntimeError(
                f"Scout closed-surface flag {key} must be false"
            )
    if report.get("planner_revision_applied") is not False:
        raise ScoutDisambiguationRuntimeError(
            "Scout report must not apply planner revision"
        )


def _scout_input_ref_for_observation(scout_input: Mapping[str, Any]) -> dict[str, Any]:
    return _safe_mapping(scout_input)


def _planner_ref_or_raise(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    proposal_id = _clean_token(ref.get("proposal_id"))
    proposal_digest = _clean_token(ref.get("proposal_digest"), limit=128)
    qmr_id = _clean_token(ref.get("question_meaning_record_id"))
    qmr_digest = _clean_token(ref.get("question_meaning_record_digest"), limit=128)
    if not proposal_id or not proposal_digest or not qmr_id or not qmr_digest:
        raise ScoutDisambiguationRuntimeError(
            "Scout input requires parent planner proposal and QMR refs"
        )
    return {
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
        "question_meaning_record_id": qmr_id,
        "question_meaning_record_digest": qmr_digest,
    }


def _contract_ref_or_empty(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    version = _clean_token(ref.get("contract_version"))
    digest = _clean_token(ref.get("contract_digest"), limit=128)
    if not version or not digest:
        return {}
    return {
        "source": _clean_token(ref.get("source")) or "answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _dedupe_key(report: Mapping[str, Any]) -> str:
    return _digest_json(_dedupe_payload(report))


def _dedupe_payload(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "parent_search_planner_proposal_ref": _safe_mapping(
            report.get("parent_search_planner_proposal_ref")
        ),
        "parent_initial_contract_ref": _safe_mapping(
            report.get("parent_initial_contract_ref")
        ),
        "parent_current_contract_ref": _safe_mapping(
            report.get("parent_current_contract_ref")
        ),
        "component_id": report.get("component_id"),
        "ambiguity_dimension_ids": [
            item.get("dimension_id")
            for item in _safe_list(report.get("ambiguity_dimensions"))
            if isinstance(item, Mapping)
        ],
        "action_type": _EXPECTED_ACTION_TYPE,
    }


def _report_digest_payload(report: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(report)
    payload.pop("report_digest", None)
    return payload


def _reject_forbidden_surface_claims(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    sensitive = sorted(key for key in keys if _is_sensitive_key(key))
    if sensitive:
        raise ScoutDisambiguationRuntimeError(
            f"{context} contains raw/private fields: " + ", ".join(sensitive)
        )
    forbidden = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if forbidden:
        raise ScoutDisambiguationRuntimeError(
            f"{context} includes closed authority fields: " + ", ".join(forbidden)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise ScoutDisambiguationRuntimeError(
            f"{context} opens closed runtime surfaces: " + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _normalize_key(key)
            if token in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(token)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _is_sensitive_key(key: Any) -> bool:
    normalized = _normalize_key(key)
    if normalized in _SAFE_FALSE_RETENTION_KEYS:
        return False
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    safe = _json_safe(list(value))
    return list(safe) if isinstance(safe, list) else []


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 7:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_token(value, limit=900)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key:
                continue
            if _is_sensitive_key(clean_key):
                if value[key] is False and clean_key in _REQUIRED_FALSE_FLAGS:
                    out[clean_key] = False
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_token(value, limit=300)


def _required_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ScoutDisambiguationRuntimeError(f"{label} must be a mapping")
    return value


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise ScoutDisambiguationRuntimeError(message)
    return text


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PRIVATE_VALUE_MARKERS):
        return "[redacted]"
    return text[:limit]


def _text_list(value: Any, *, limit: int = 160) -> list[str]:
    if isinstance(value, str):
        text = _clean_token(value, limit=limit)
        return [text] if text else []
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_token(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _bounded_int(value: Any, *, minimum: int, maximum: int, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ScoutDisambiguationRuntimeError(f"{label} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise ScoutDisambiguationRuntimeError(
            f"{label} must be between {minimum} and {maximum}"
        )
    return parsed


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _executed_query_count(queries: Sequence[Mapping[str, Any]]) -> int:
    return sum(
        1
        for query in queries
        if query.get("execution_status") == "executed_by_fake_adapter"
    )


def _require_related_dimensions(
    related_ids: Sequence[str],
    dimension_ids: Sequence[str],
    *,
    context: str,
) -> None:
    missing = [item for item in related_ids if item not in dimension_ids]
    if missing:
        raise ScoutDisambiguationRuntimeError(
            f"{context} references unknown ambiguity dimensions: "
            + ", ".join(missing)
        )


def _safe_shallow_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        clean_key = _clean_token(key, limit=120)
        if not clean_key or _is_sensitive_key(clean_key):
            continue
        if isinstance(item, Mapping):
            raise ScoutDisambiguationRuntimeError(
                "Scout hint attributes must not contain provider-payload objects"
            )
        if isinstance(item, list | tuple):
            out[clean_key] = [_clean_token(child, limit=240) for child in item]
        else:
            out[clean_key] = _clean_token(item, limit=240)
    return _without_empty(out)


def _safe_sitelinks(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in _safe_list(value):
        mapping = _required_mapping(item, "Scout hint sitelink")
        out.append(
            _without_empty(
                {
                    "title": _clean_token(mapping.get("title"), limit=240),
                    "link": _clean_token(mapping.get("link"), limit=600),
                }
            )
        )
    return out


def _domain_from_url(value: str) -> str | None:
    parsed = urlparse(value)
    host = parsed.netloc or parsed.path.split("/", 1)[0]
    return _clean_token(host.removeprefix("www."), limit=240)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _enum_or_text(value: Any) -> str | None:
    if isinstance(value, Enum):
        return str(value.value)
    return _clean_token(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "SCOUT_DISAMBIGUATION_OBSERVATION_SCHEMA_VERSION",
    "SCOUT_DISAMBIGUATION_REASON",
    "SCOUT_DISAMBIGUATION_REPORT_OWNER",
    "SCOUT_DISAMBIGUATION_REPORT_SCHEMA_VERSION",
    "SCOUT_DISAMBIGUATION_SCHEMA_VERSION",
    "SCOUT_DISAMBIGUATION_STAGE",
    "SCOUT_DISAMBIGUATION_TRACE_KEY",
    "SCOUT_MAX_DIMENSIONS_PER_COMPONENT",
    "SCOUT_MAX_QUERIES_PER_COMPONENT",
    "ScoutDisambiguationAdapter",
    "ScoutDisambiguationExecutionResult",
    "ScoutDisambiguationInput",
    "ScoutDisambiguationRuntimeError",
    "build_scout_disambiguation_report_payload",
    "build_scout_disambiguation_report_projection",
    "build_scout_disambiguation_report_state",
    "contract_ref_from_contract",
    "execute_scout_disambiguation_action",
    "planner_ref_from_search_planner_state",
]
