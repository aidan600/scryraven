"""RunKernel-authorized SearchExecutor handoff runtime.

This module turns accepted contract and planner/revision direction into a
bounded offline search work packet. It does not call providers, execute search,
fetch/read/retrieval, admit EvidenceLedger custody, create citations, decide
sufficiency, create FinalAnswerPacket state, or create Author input.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION = (
    "search_executor_handoff_runtime_ag_search_executor_handoff_01_v1"
)
SEARCH_EXECUTOR_HANDOFF_OBSERVATION_SCHEMA_VERSION = (
    "search_executor_handoff_observation_ag_search_executor_handoff_01_v1"
)
SEARCH_EXECUTOR_HANDOFF_STAGE = "search_executor_handoff"
SEARCH_EXECUTOR_HANDOFF_REASON = (
    "search_executor_handoff_from_authorized_run_kernel_state"
)
SEARCH_EXECUTOR_HANDOFF_TRACE_KEY = "search_executor_handoff"
SEARCH_EXECUTOR_HANDOFF_OWNER = "RunKernel.SearchExecutorHandoff"

CONTRACT_PARENT_CURRENT = "current_answer_contract"
CONTRACT_PARENT_INITIAL_FALLBACK = "initial_answer_contract_fallback"
EXECUTION_MODE = "offline_handoff_only"
TASK_EXECUTION_STATUS = "not_executed"

_EXPECTED_ACTION_TYPE = "search_executor_handoff"
_EXPECTED_OBSERVATION_TYPE = "search_executor_handoff_created"

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
        "serper_api_key",
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
        "raw_model_response_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)

_REQUIRED_FALSE_FLAGS = {
    "provider_calls_executed": False,
    "live_search_executed": False,
    "fetch_read_retrieval_executed": False,
    "retrieval_executed": False,
    "search_provider_called": False,
    "evidence_admitted": False,
    "evidence_ledger_custody_created": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "live_validation_run": False,
    "search_executor_runtime_activated": False,
    "search_work_plan_activated": False,
    "contract_mutation_applied": False,
    "current_answer_contract_mutated": False,
    "initial_answer_contract_mutated": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
}

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "accepted_amendment",
        "accepted_contract",
        "admitted_sources",
        "answer",
        "author_input",
        "canonical_coverage",
        "citation",
        "citation_sources",
        "citations",
        "component_coverage_record",
        "current_answer_contract",
        "evidence",
        "evidence_ledger",
        "evidence_ledger_admission",
        "evidence_sources",
        "final_answer",
        "final_answer_packet",
        "final_sources",
        "initial_answer_contract",
        "raw_provider_payload",
        "raw_search_response",
        "search_judgment_decision",
        "semantic_observation",
        "source_results",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_REQUIRED_FALSE_FLAGS,
        "accepted_authority",
        "author_behavior_changed",
        "author_executor_invoked",
        "citation_behavior_changed",
        "citation_created",
        "citation_rendered",
        "component_satisfied",
        "evidence_ledger_admitted",
        "fetch_executed",
        "live_model_called",
        "live_provider_call_executed",
        "live_provider_calls_executed",
        "live_search_called",
        "model_called",
        "provider_called",
        "provider_execution_licensed",
        "provider_payload_retained",
        "provider_search_behavior_changed",
        "provider_selected",
        "query_plan_activated",
        "read_executed",
        "retrieval_behavior_changed",
        "runtime_behavior_changed",
        "search_executed",
        "source_obligation_support_created",
    }
)

_REQUIRED_ACTION_INPUT_KEYS = (
    "run_id",
    "request_id",
    "contract_parent_kind",
    "parent_initial_contract_version",
    "parent_initial_contract_digest",
    "parent_current_contract_version",
    "parent_current_contract_digest",
    "parent_search_planner_proposal_id",
    "parent_search_planner_proposal_digest",
    "parent_question_meaning_record_id",
    "parent_question_meaning_record_digest",
    "handoff_schema_version",
    "reason",
)


class SearchExecutorHandoffRuntimeError(ValueError):
    """Raised when handoff construction or RunKernel reduction fails."""


@dataclass(frozen=True, slots=True)
class SearchExecutorHandoffInput:
    run_id: str
    request_id: str
    parent_current_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    parent_initial_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    contract_parent_kind: str = CONTRACT_PARENT_CURRENT
    parent_search_planner_proposal_ref: Mapping[str, Any] = field(
        default_factory=dict
    )
    parent_search_planner_revision_ref: Mapping[str, Any] = field(
        default_factory=dict
    )
    parent_scout_disambiguation_report_ref: Mapping[str, Any] = field(
        default_factory=dict
    )
    answer_component_refs: Sequence[Mapping[str, Any]] = field(
        default_factory=tuple
    )
    source_obligation_candidate_refs: Sequence[Mapping[str, Any]] = field(
        default_factory=tuple
    )
    component_search_requirements: Sequence[Mapping[str, Any]] = field(
        default_factory=tuple
    )
    revision_search_requirement_updates: Sequence[Mapping[str, Any]] = field(
        default_factory=tuple
    )
    source_obligation_focus_updates: Sequence[Mapping[str, Any]] = field(
        default_factory=tuple
    )
    scout_direction_hint_refs: Sequence[Mapping[str, Any] | str] = field(
        default_factory=tuple
    )
    non_evidence_direction_refs: Sequence[Mapping[str, Any] | str] = field(
        default_factory=tuple
    )
    required_caveats: Sequence[str] = field(default_factory=tuple)
    prohibited_upgrades: Sequence[str] = field(default_factory=tuple)
    query_budget: Mapping[str, Any] = field(default_factory=dict)
    allowed_verticals: Sequence[str] = field(default_factory=lambda: ("search",))
    provider_preference_hint: str | None = None
    no_fetch_read_policy_active: bool = True
    not_live: bool = True
    closed_surface_flags: Mapping[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        run_id = _required_token(self.run_id, "handoff input requires run_id")
        request_id = _required_token(
            self.request_id,
            "handoff input requires request_id",
        )
        parent_kind = _clean_token(self.contract_parent_kind)
        if parent_kind not in {CONTRACT_PARENT_CURRENT, CONTRACT_PARENT_INITIAL_FALLBACK}:
            raise SearchExecutorHandoffRuntimeError(
                "handoff input requires an explicit contract parent kind"
            )
        parent_initial_ref = _contract_ref_or_empty(self.parent_initial_contract_ref)
        if not parent_initial_ref:
            raise SearchExecutorHandoffRuntimeError(
                "handoff input requires parent initial contract ref"
            )
        parent_current_ref = _contract_ref_or_empty(self.parent_current_contract_ref)
        if parent_kind == CONTRACT_PARENT_CURRENT and not parent_current_ref:
            raise SearchExecutorHandoffRuntimeError(
                "current contract parent requires parent_current_contract_ref"
            )
        if parent_kind == CONTRACT_PARENT_INITIAL_FALLBACK and parent_current_ref:
            raise SearchExecutorHandoffRuntimeError(
                "initial fallback parent requires empty parent_current_contract_ref"
            )
        if self.not_live is not True or self.no_fetch_read_policy_active is not True:
            raise SearchExecutorHandoffRuntimeError(
                "handoff input must keep not_live and no_fetch_read_policy_active true"
            )
        parent_planner_ref = _planner_ref_or_raise(
            self.parent_search_planner_proposal_ref
        )
        parent_revision_ref = _revision_ref_or_empty(
            self.parent_search_planner_revision_ref
        )
        parent_scout_ref = _scout_ref_or_empty(
            self.parent_scout_disambiguation_report_ref
        )
        answer_component_refs = _normalize_component_refs(
            self.answer_component_refs
        )
        if not answer_component_refs:
            raise SearchExecutorHandoffRuntimeError(
                "handoff input requires answer component refs"
            )
        source_refs = _normalize_source_obligation_refs(
            self.source_obligation_candidate_refs
        )
        requirements = _normalize_requirements(self.component_search_requirements)
        revision_updates = _normalize_requirements(
            self.revision_search_requirement_updates
        )
        focus_updates = _safe_list(self.source_obligation_focus_updates)
        scout_direction_refs = _normalize_direction_refs(
            self.scout_direction_hint_refs,
            default_prefix="scout-direction",
        )
        non_evidence_refs = _normalize_direction_refs(
            self.non_evidence_direction_refs,
            default_prefix="non-evidence-direction",
        )
        closed_flags = {**_REQUIRED_FALSE_FLAGS, **_safe_mapping(self.closed_surface_flags)}
        if any(bool(value) for value in closed_flags.values()):
            raise SearchExecutorHandoffRuntimeError(
                "handoff input cannot open closed runtime surfaces"
            )
        payload = {
            "schema_version": SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION,
            "run_id": run_id,
            "request_id": request_id,
            "contract_parent_kind": parent_kind,
            "parent_current_contract_ref": parent_current_ref,
            "parent_initial_contract_ref": parent_initial_ref,
            "initial_answer_contract_fallback_explicit": (
                parent_kind == CONTRACT_PARENT_INITIAL_FALLBACK
            ),
            "parent_search_planner_proposal_ref": parent_planner_ref,
            "parent_search_planner_revision_ref": parent_revision_ref,
            "parent_scout_disambiguation_report_ref": parent_scout_ref,
            "answer_component_refs": answer_component_refs,
            "source_obligation_candidate_refs": source_refs,
            "component_search_requirements": requirements,
            "revision_search_requirement_updates": revision_updates,
            "source_obligation_focus_updates": focus_updates,
            "scout_direction_hint_refs": scout_direction_refs,
            "non_evidence_direction_refs": non_evidence_refs,
            "required_caveats": _text_list(self.required_caveats, limit=360),
            "prohibited_upgrades": _text_list(
                self.prohibited_upgrades,
                limit=260,
            ),
            "query_budget": _normalize_query_budget(self.query_budget),
            "allowed_verticals": _allowed_verticals(self.allowed_verticals),
            "provider_preference_hint": _clean_token(
                self.provider_preference_hint,
                limit=120,
            ),
            "no_fetch_read_policy_active": True,
            "not_live": True,
            "closed_surface_flags": {
                key: bool(value) for key, value in closed_flags.items()
            },
        }
        _reject_forbidden_surface_claims(payload, context="handoff input")
        return _json_safe(payload)


@dataclass(frozen=True, slots=True)
class SearchExecutorHandoffExecutionResult:
    handoff_input: Mapping[str, Any]
    observation_payload: Mapping[str, Any]


def execute_search_executor_handoff_action(
    *,
    action: Any,
    handoff_input: SearchExecutorHandoffInput,
) -> SearchExecutorHandoffExecutionResult:
    """Build a handoff observation for an authorized action without live work."""

    _validate_action_like(action=action, handoff_input=handoff_input)
    payload = handoff_input.to_payload()
    observation_payload = build_search_executor_handoff_observation_payload(
        handoff_input=payload,
        authorized_action_id=_clean_token(getattr(action, "action_id", None)),
    )
    return SearchExecutorHandoffExecutionResult(
        handoff_input=payload,
        observation_payload=observation_payload,
    )


def build_search_executor_handoff_observation_payload(
    *,
    handoff_input: SearchExecutorHandoffInput | Mapping[str, Any],
    authorized_action_id: str | None = None,
) -> dict[str, Any]:
    """Construct the sanitized SearchExecutor handoff observation payload."""

    if isinstance(handoff_input, SearchExecutorHandoffInput):
        input_payload = handoff_input.to_payload()
    else:
        _reject_forbidden_surface_claims(handoff_input, context="handoff input")
        input_payload = _safe_mapping(handoff_input)
    if input_payload.get("schema_version") != SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION:
        raise SearchExecutorHandoffRuntimeError(
            "handoff input schema version does not match"
        )

    query_intents, search_tasks = _build_intent_and_task_records(input_payload)
    handoff_base = {
        "schema_version": SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION,
        "trace_key": SEARCH_EXECUTOR_HANDOFF_TRACE_KEY,
        "owner": SEARCH_EXECUTOR_HANDOFF_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": input_payload.get("run_id"),
        "request_id": input_payload.get("request_id"),
        "authorized_action_id": authorized_action_id,
        "contract_parent_kind": input_payload.get("contract_parent_kind"),
        "parent_current_contract_ref": _safe_mapping(
            input_payload.get("parent_current_contract_ref")
        ),
        "parent_initial_contract_ref": _safe_mapping(
            input_payload.get("parent_initial_contract_ref")
        ),
        "initial_answer_contract_fallback_explicit": (
            input_payload.get("contract_parent_kind")
            == CONTRACT_PARENT_INITIAL_FALLBACK
        ),
        "parent_search_planner_proposal_ref": _safe_mapping(
            input_payload.get("parent_search_planner_proposal_ref")
        ),
        "parent_search_planner_revision_ref": _safe_mapping(
            input_payload.get("parent_search_planner_revision_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            input_payload.get("parent_scout_disambiguation_report_ref")
        ),
        "answer_component_refs": _safe_list(
            input_payload.get("answer_component_refs")
        ),
        "source_obligation_candidate_refs": _safe_list(
            input_payload.get("source_obligation_candidate_refs")
        ),
        "component_search_requirements": _safe_list(
            input_payload.get("component_search_requirements")
        ),
        "revision_search_requirement_updates": _safe_list(
            input_payload.get("revision_search_requirement_updates")
        ),
        "source_obligation_focus_updates": _safe_list(
            input_payload.get("source_obligation_focus_updates")
        ),
        "scout_direction_hint_refs": _safe_list(
            input_payload.get("scout_direction_hint_refs")
        ),
        "non_evidence_direction_refs": _safe_list(
            input_payload.get("non_evidence_direction_refs")
        ),
        "query_intent_records": query_intents,
        "search_task_records": search_tasks,
        "required_caveats": _text_list(input_payload.get("required_caveats")),
        "prohibited_upgrades": _text_list(input_payload.get("prohibited_upgrades")),
        "query_budget": _safe_mapping(input_payload.get("query_budget")),
        "allowed_verticals": _text_list(input_payload.get("allowed_verticals")),
        "provider_preference_hint": _clean_token(
            input_payload.get("provider_preference_hint"),
            limit=120,
        ),
        "execution_mode": EXECUTION_MODE,
        "not_live": True,
        "no_fetch_read_policy_active": True,
        "search_executor_handoff_created": True,
        "search_work_packet_constructed": True,
        "retention_flags": _retention_flags(),
        "closed_surface_flags": dict(_REQUIRED_FALSE_FLAGS),
        **_REQUIRED_FALSE_FLAGS,
    }
    dedupe_key = _dedupe_key(handoff_base)
    handoff_id = (
        "search-executor-handoff:"
        f"{_clean_token(input_payload.get('request_id'))}:"
        f"{dedupe_key[:16]}"
    )
    handoff_without_digest = {
        **handoff_base,
        "handoff_id": handoff_id,
        "dedupe_key": dedupe_key,
    }
    handoff_digest = _digest_json(_handoff_digest_payload(handoff_without_digest))
    handoff = {**handoff_without_digest, "handoff_digest": handoff_digest}
    return {
        "schema_version": SEARCH_EXECUTOR_HANDOFF_OBSERVATION_SCHEMA_VERSION,
        "handoff_input": input_payload,
        "search_executor_handoff": handoff,
    }


def build_search_executor_handoff_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    current_search_planner_proposal_state: Mapping[str, Any] | None = None,
    current_search_planner_revision_state: Mapping[str, Any] | None = None,
    current_scout_disambiguation_report_state: Mapping[str, Any] | None = None,
    current_parent_initial_contract: Mapping[str, Any] | None = None,
    current_parent_current_contract: Mapping[str, Any] | None = None,
    existing_handoff_history: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Validate one handoff observation and build canonical RunKernel state."""

    clean_action_id = _required_token(
        action_id,
        "SearchExecutor handoff reduction requires action_id",
        limit=200,
    )
    clean_run_id = _required_token(
        run_id,
        "SearchExecutor handoff reduction requires run_id",
    )
    clean_request_id = _required_token(
        request_id,
        "SearchExecutor handoff reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    raw_payload = _required_mapping(
        observation_payload,
        "SearchExecutor handoff observation payload",
    )
    _reject_forbidden_surface_claims(
        raw_payload,
        context="SearchExecutor handoff observation",
    )
    payload = _safe_mapping(raw_payload)
    handoff_input = _safe_mapping(payload.get("handoff_input"))
    handoff = _safe_mapping(payload.get("search_executor_handoff"))
    if payload.get("schema_version") != SEARCH_EXECUTOR_HANDOFF_OBSERVATION_SCHEMA_VERSION:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff observation schema version does not match"
        )
    if not handoff_input or not handoff:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff observation requires input and handoff state"
        )
    if handoff_input.get("schema_version") != SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff input schema version does not match"
        )
    if handoff.get("schema_version") != SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff schema version does not match"
        )
    if handoff.get("owner") != SEARCH_EXECUTOR_HANDOFF_OWNER:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff owner does not match"
        )
    if handoff.get("authorized_action_id") != clean_action_id:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff action_id binding does not match"
        )
    if handoff.get("run_id") != clean_run_id or handoff_input.get("run_id") != clean_run_id:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff run_id does not match the run"
        )
    if (
        handoff.get("request_id") != clean_request_id
        or handoff_input.get("request_id") != clean_request_id
    ):
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff request_id does not match the request"
        )

    _validate_action_inputs(inputs)
    if inputs.get("run_id") != clean_run_id or inputs.get("request_id") != clean_request_id:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff action run/request binding does not match"
        )

    declared_digest = _clean_token(handoff.get("handoff_digest"), limit=128)
    if not declared_digest:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff requires handoff_digest"
        )
    recomputed_digest = _digest_json(_handoff_digest_payload(handoff))
    if declared_digest != recomputed_digest:
        raise SearchExecutorHandoffRuntimeError(
            "stale SearchExecutor handoff: handoff digest does not match payload content"
        )
    if handoff.get("dedupe_key") != _dedupe_key(handoff):
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff dedupe key does not match payload content"
        )

    active_contract = _validate_parent_contract_bindings(
        action_inputs=inputs,
        handoff_input=handoff_input,
        handoff=handoff,
        current_parent_initial_contract=current_parent_initial_contract,
        current_parent_current_contract=current_parent_current_contract,
    )
    planner_ref = _validate_planner_bindings(
        action_inputs=inputs,
        handoff_input=handoff_input,
        handoff=handoff,
        current_search_planner_proposal_state=current_search_planner_proposal_state,
    )
    revision_ref = _validate_revision_bindings(
        action_inputs=inputs,
        handoff_input=handoff_input,
        handoff=handoff,
        current_search_planner_revision_state=current_search_planner_revision_state,
        parent_planner_ref=planner_ref,
    )
    _validate_scout_bindings(
        action_inputs=inputs,
        handoff_input=handoff_input,
        handoff=handoff,
        current_scout_disambiguation_report_state=(
            current_scout_disambiguation_report_state
        ),
        parent_planner_ref=planner_ref,
        parent_revision_ref=revision_ref,
    )
    _validate_component_and_work_bindings(
        action_inputs=inputs,
        handoff=handoff,
        active_contract=active_contract,
        planner_state=current_search_planner_proposal_state,
        revision_state=current_search_planner_revision_state,
        scout_state=current_scout_disambiguation_report_state,
    )
    _validate_handoff_records(handoff)
    _validate_closed_handoff_flags(handoff)

    dedupe_key = _clean_token(handoff.get("dedupe_key"), limit=128)
    for item in existing_handoff_history:
        if _safe_mapping(item).get("dedupe_key") == dedupe_key:
            raise SearchExecutorHandoffRuntimeError(
                "duplicate SearchExecutor handoff for the same contract/planner context"
            )

    state = {
        "schema_version": SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION,
        "trace_key": SEARCH_EXECUTOR_HANDOFF_TRACE_KEY,
        "owner": SEARCH_EXECUTOR_HANDOFF_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "handoff_id": handoff.get("handoff_id"),
        "handoff_digest": declared_digest,
        "dedupe_key": dedupe_key,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "contract_parent_kind": handoff.get("contract_parent_kind"),
        "parent_current_contract_ref": _safe_mapping(
            handoff.get("parent_current_contract_ref")
        ),
        "parent_initial_contract_ref": _safe_mapping(
            handoff.get("parent_initial_contract_ref")
        ),
        "initial_answer_contract_fallback_explicit": handoff.get(
            "initial_answer_contract_fallback_explicit"
        )
        is True,
        "parent_search_planner_proposal_ref": _safe_mapping(
            handoff.get("parent_search_planner_proposal_ref")
        ),
        "parent_search_planner_revision_ref": _safe_mapping(
            handoff.get("parent_search_planner_revision_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            handoff.get("parent_scout_disambiguation_report_ref")
        ),
        "answer_component_refs": _safe_list(handoff.get("answer_component_refs")),
        "source_obligation_candidate_refs": _safe_list(
            handoff.get("source_obligation_candidate_refs")
        ),
        "component_search_requirements": _safe_list(
            handoff.get("component_search_requirements")
        ),
        "revision_search_requirement_updates": _safe_list(
            handoff.get("revision_search_requirement_updates")
        ),
        "source_obligation_focus_updates": _safe_list(
            handoff.get("source_obligation_focus_updates")
        ),
        "scout_direction_hint_refs": _safe_list(
            handoff.get("scout_direction_hint_refs")
        ),
        "non_evidence_direction_refs": _safe_list(
            handoff.get("non_evidence_direction_refs")
        ),
        "query_intent_records": _safe_list(handoff.get("query_intent_records")),
        "search_task_records": _safe_list(handoff.get("search_task_records")),
        "required_caveats": _text_list(handoff.get("required_caveats"), limit=360),
        "prohibited_upgrades": _text_list(
            handoff.get("prohibited_upgrades"),
            limit=260,
        ),
        "query_budget": _safe_mapping(handoff.get("query_budget")),
        "allowed_verticals": _text_list(handoff.get("allowed_verticals")),
        "provider_preference_hint": _clean_token(
            handoff.get("provider_preference_hint"),
            limit=120,
        ),
        "execution_mode": EXECUTION_MODE,
        "not_live": True,
        "no_fetch_read_policy_active": True,
        "search_executor_handoff_created": True,
        "search_work_packet_constructed": True,
        "retention_flags": _retention_flags(),
        "closed_surface_flags": dict(_REQUIRED_FALSE_FLAGS),
        **_REQUIRED_FALSE_FLAGS,
    }
    return _json_safe(state)


def build_search_executor_handoff_projection(
    *,
    handoff_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project sanitized handoff state for trace/history consumers."""

    state = _safe_mapping(handoff_state)
    return {
        "owner": SEARCH_EXECUTOR_HANDOFF_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": SEARCH_EXECUTOR_HANDOFF_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "handoff_id": state.get("handoff_id"),
        "handoff_digest": state.get("handoff_digest"),
        "dedupe_key": state.get("dedupe_key"),
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "contract_parent_kind": state.get("contract_parent_kind"),
        "parent_current_contract_ref": _safe_mapping(
            state.get("parent_current_contract_ref")
        ),
        "parent_initial_contract_ref": _safe_mapping(
            state.get("parent_initial_contract_ref")
        ),
        "initial_answer_contract_fallback_explicit": state.get(
            "initial_answer_contract_fallback_explicit"
        )
        is True,
        "parent_search_planner_proposal_ref": _safe_mapping(
            state.get("parent_search_planner_proposal_ref")
        ),
        "parent_search_planner_revision_ref": _safe_mapping(
            state.get("parent_search_planner_revision_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            state.get("parent_scout_disambiguation_report_ref")
        ),
        "answer_component_refs": _safe_list(state.get("answer_component_refs")),
        "source_obligation_candidate_refs": _safe_list(
            state.get("source_obligation_candidate_refs")
        ),
        "component_search_requirements": _safe_list(
            state.get("component_search_requirements")
        ),
        "revision_search_requirement_updates": _safe_list(
            state.get("revision_search_requirement_updates")
        ),
        "source_obligation_focus_updates": _safe_list(
            state.get("source_obligation_focus_updates")
        ),
        "scout_direction_hint_refs": _safe_list(
            state.get("scout_direction_hint_refs")
        ),
        "non_evidence_direction_refs": _safe_list(
            state.get("non_evidence_direction_refs")
        ),
        "query_intent_records": _safe_list(state.get("query_intent_records")),
        "search_task_records": _safe_list(state.get("search_task_records")),
        "query_intent_record_count": len(
            _safe_list(state.get("query_intent_records"))
        ),
        "search_task_record_count": len(_safe_list(state.get("search_task_records"))),
        "required_caveats": _text_list(state.get("required_caveats"), limit=360),
        "prohibited_upgrades": _text_list(
            state.get("prohibited_upgrades"),
            limit=260,
        ),
        "query_budget": _safe_mapping(state.get("query_budget")),
        "allowed_verticals": _text_list(state.get("allowed_verticals")),
        "provider_preference_hint": state.get("provider_preference_hint"),
        "execution_mode": EXECUTION_MODE,
        "not_live": True,
        "no_fetch_read_policy_active": True,
        "search_executor_handoff_created": True,
        "search_work_packet_constructed": True,
        "retention_flags": _retention_flags(),
        "closed_surface_flags": dict(_REQUIRED_FALSE_FLAGS),
        **_REQUIRED_FALSE_FLAGS,
    }


def handoff_ref_from_handoff_state(
    handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = _safe_mapping(handoff_state)
    handoff_id = _clean_token(state.get("handoff_id"))
    handoff_digest = _clean_token(state.get("handoff_digest"), limit=128)
    if not handoff_id or not handoff_digest:
        return {}
    return {
        "handoff_id": handoff_id,
        "handoff_digest": handoff_digest,
        "schema_version": _clean_token(state.get("schema_version")),
        "dedupe_key": _clean_token(state.get("dedupe_key"), limit=128),
        "contract_parent_kind": _clean_token(state.get("contract_parent_kind")),
        "parent_current_contract_ref": _safe_mapping(
            state.get("parent_current_contract_ref")
        ),
        "parent_initial_contract_ref": _safe_mapping(
            state.get("parent_initial_contract_ref")
        ),
        "parent_search_planner_proposal_ref": _safe_mapping(
            state.get("parent_search_planner_proposal_ref")
        ),
        "parent_search_planner_revision_ref": _safe_mapping(
            state.get("parent_search_planner_revision_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            state.get("parent_scout_disambiguation_report_ref")
        ),
    }


def contract_ref_from_contract(
    contract: Mapping[str, Any] | None,
    *,
    source: str,
) -> dict[str, Any]:
    return _contract_ref_or_empty(
        {
            **_safe_mapping(contract),
            "source": source,
        }
    )


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
    qmr_id = _clean_token(qmr_ref.get("record_id") or qmr.get("record_id"))
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


def revision_ref_from_revision_state(
    revision_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = _safe_mapping(revision_state)
    if not state:
        return {}
    revision_id = _clean_token(state.get("revision_id"))
    revision_digest = _clean_token(state.get("revision_digest"), limit=128)
    if not revision_id or not revision_digest:
        return {}
    return {
        "revision_id": revision_id,
        "revision_digest": revision_digest,
        "schema_version": _clean_token(state.get("schema_version")),
        "component_id": _clean_token(state.get("component_id")),
        "parent_search_planner_proposal_ref": _planner_ref_or_empty(
            state.get("parent_search_planner_proposal_ref")
        ),
        "parent_scout_disambiguation_report_ref": _scout_ref_or_empty(
            state.get("parent_scout_disambiguation_report_ref")
        ),
    }


def scout_ref_from_scout_report_state(
    scout_report_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = _safe_mapping(scout_report_state)
    if not state:
        return {}
    report_id = _clean_token(state.get("report_id"))
    report_digest = _clean_token(state.get("report_digest"), limit=128)
    component_id = _clean_token(state.get("component_id"))
    parent_planner_ref = _planner_ref_or_empty(
        state.get("parent_search_planner_proposal_ref")
    )
    if not report_id or not report_digest or not component_id or not parent_planner_ref:
        return {}
    return {
        "report_id": report_id,
        "report_digest": report_digest,
        "component_id": component_id,
        "parent_search_planner_proposal_ref": parent_planner_ref,
    }


def _build_intent_and_task_records(
    handoff_input: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    components = _safe_list(handoff_input.get("answer_component_refs"))
    requirements = _merge_requirements(
        handoff_input.get("component_search_requirements"),
        handoff_input.get("revision_search_requirement_updates"),
    )
    query_budget = _safe_mapping(handoff_input.get("query_budget"))
    max_tasks = _bounded_int(
        query_budget.get("max_search_tasks"),
        minimum=1,
        maximum=25,
        default=5,
    )
    max_results = _bounded_int(
        query_budget.get("max_results_per_task"),
        minimum=1,
        maximum=25,
        default=10,
    )
    provider_hint = _clean_token(
        handoff_input.get("provider_preference_hint"),
        limit=120,
    )
    allowed_verticals = _allowed_verticals(handoff_input.get("allowed_verticals"))
    required_caveats = _text_list(handoff_input.get("required_caveats"), limit=360)
    prohibited_upgrades = _text_list(
        handoff_input.get("prohibited_upgrades"),
        limit=260,
    )
    direction_refs = _safe_list(handoff_input.get("non_evidence_direction_refs"))
    direction_ids = [
        _clean_token(ref.get("direction_ref_id") or ref.get("hint_id"))
        for ref in direction_refs
        if isinstance(ref, Mapping)
    ]
    contract_source = (
        CONTRACT_PARENT_CURRENT
        if handoff_input.get("contract_parent_kind") == CONTRACT_PARENT_CURRENT
        else "initial_answer_contract"
    )
    intents: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    requirement_items = requirements or _requirements_from_components(components)
    for index, requirement in enumerate(requirement_items, start=1):
        if len(tasks) >= max_tasks:
            break
        component_id = _clean_token(requirement.get("component_id"))
        if not component_id:
            continue
        component = _component_by_id(components, component_id=component_id)
        if not component:
            continue
        requirement_id = _clean_token(
            requirement.get("requirement_id")
            or requirement.get("search_requirement_id")
            or f"searchreq:{component_id}:{index}",
            limit=180,
        )
        source_ids = _source_ids_for_requirement(requirement, component)
        intent_id = f"search-intent:{component_id}:{index}"
        derived_from = [contract_source, "search_planner_proposal"]
        if _safe_list(handoff_input.get("revision_search_requirement_updates")):
            derived_from.append("search_planner_revision")
        if direction_ids:
            derived_from.append("scout_direction")
        summary = _clean_text(
            requirement.get("requirement_summary")
            or requirement.get("summary")
            or requirement.get("query_goal")
            or component.get("user_facing_label")
            or component.get("component_id"),
            limit=420,
        )
        intent = {
            "query_intent_id": intent_id,
            "component_id": component_id,
            "source_obligation_candidate_ids": source_ids,
            "source_obligation_candidate_refs": source_ids,
            "search_requirement_id": requirement_id,
            "intent_summary": summary,
            "derived_from": derived_from,
            "non_evidence_direction_ref_ids": [
                item for item in direction_ids if item
            ],
            "required_caveats": required_caveats,
            "prohibited_upgrades": prohibited_upgrades,
            "provider_preference_hint": provider_hint,
            "allowed_verticals": allowed_verticals,
            "not_live": True,
            "no_fetch_read_policy_active": True,
            "evidence_admitted": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
        }
        task = {
            "search_task_id": f"search-task:{component_id}:{index}",
            "query_intent_id": intent_id,
            "component_id": component_id,
            "search_requirement_id": requirement_id,
            "safe_query_text": _safe_query_text(
                component=component,
                requirement=requirement,
            ),
            "query_summary": summary,
            "source_obligation_candidate_ids": source_ids,
            "source_obligation_candidate_refs": source_ids,
            "preferred_source_kinds": _text_list(
                requirement.get("preferred_source_kinds"),
                limit=160,
            ),
            "recency_requirement": _clean_text(
                requirement.get("recency_requirement"),
                limit=220,
            ),
            "provider_preference_hint": provider_hint,
            "allowed_verticals": allowed_verticals,
            "max_results": max_results,
            "execution_status": TASK_EXECUTION_STATUS,
            "not_live": True,
            "no_fetch_read_policy_active": True,
            "provider_calls_executed": False,
            "live_search_executed": False,
            "fetch_read_retrieval_executed": False,
            "evidence_admitted": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
        }
        intents.append(_without_empty(intent))
        tasks.append(_without_empty(task))
    if not intents or not tasks:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff requires at least one query intent and task"
        )
    return intents, tasks


def _validate_action_like(
    *,
    action: Any,
    handoff_input: SearchExecutorHandoffInput,
) -> None:
    action_type = _enum_or_text(getattr(action, "action_type", None))
    expected_observation_type = _enum_or_text(
        getattr(action, "expected_observation_type", None)
    )
    if getattr(action, "stage", None) != SEARCH_EXECUTOR_HANDOFF_STAGE:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff action stage does not match"
        )
    if action_type != _EXPECTED_ACTION_TYPE:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff action type does not match"
        )
    if expected_observation_type != _EXPECTED_OBSERVATION_TYPE:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff expected observation type does not match"
        )
    inputs = _safe_mapping(getattr(action, "inputs", None))
    payload = handoff_input.to_payload()
    expected = {
        "run_id": payload.get("run_id"),
        "request_id": payload.get("request_id"),
        "contract_parent_kind": payload.get("contract_parent_kind"),
        "handoff_schema_version": SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if inputs.get(key) != value:
            raise SearchExecutorHandoffRuntimeError(
                f"SearchExecutor handoff action binding does not match input: {key}"
            )


def _validate_action_inputs(inputs: Mapping[str, Any]) -> None:
    missing = [key for key in _REQUIRED_ACTION_INPUT_KEYS if key not in inputs]
    if missing:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff action missing required bindings: "
            + ", ".join(missing)
        )
    for key in (
        "run_id",
        "request_id",
        "contract_parent_kind",
        "parent_initial_contract_version",
        "parent_initial_contract_digest",
        "parent_search_planner_proposal_id",
        "parent_search_planner_proposal_digest",
        "parent_question_meaning_record_id",
        "parent_question_meaning_record_digest",
        "handoff_schema_version",
        "reason",
    ):
        if not _clean_token(inputs.get(key), limit=180):
            raise SearchExecutorHandoffRuntimeError(
                f"SearchExecutor handoff action requires {key} binding"
            )
    if inputs.get("handoff_schema_version") != SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff action binds the wrong schema version"
        )


def _validate_parent_contract_bindings(
    *,
    action_inputs: Mapping[str, Any],
    handoff_input: Mapping[str, Any],
    handoff: Mapping[str, Any],
    current_parent_initial_contract: Mapping[str, Any] | None,
    current_parent_current_contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    expected_initial = contract_ref_from_contract(
        current_parent_initial_contract,
        source="initial_answer_contract",
    )
    expected_current = contract_ref_from_contract(
        current_parent_current_contract,
        source="current_answer_contract",
    )
    if not expected_initial:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff requires an accepted initial answer contract"
        )
    parent_kind = _clean_token(handoff.get("contract_parent_kind"))
    if parent_kind != _clean_token(handoff_input.get("contract_parent_kind")):
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff parent kind does not match input"
        )
    if parent_kind != _clean_token(action_inputs.get("contract_parent_kind")):
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff parent kind does not match authorization"
        )
    _validate_one_parent_binding(
        label="parent_initial_contract",
        action_version=action_inputs.get("parent_initial_contract_version"),
        action_digest=action_inputs.get("parent_initial_contract_digest"),
        input_ref=_safe_mapping(handoff_input.get("parent_initial_contract_ref")),
        handoff_ref=_safe_mapping(handoff.get("parent_initial_contract_ref")),
        expected_ref=expected_initial,
    )
    if expected_current:
        if parent_kind != CONTRACT_PARENT_CURRENT:
            raise SearchExecutorHandoffRuntimeError(
                "current_answer_contract must be the handoff parent when present"
            )
        _validate_one_parent_binding(
            label="parent_current_contract",
            action_version=action_inputs.get("parent_current_contract_version"),
            action_digest=action_inputs.get("parent_current_contract_digest"),
            input_ref=_safe_mapping(handoff_input.get("parent_current_contract_ref")),
            handoff_ref=_safe_mapping(handoff.get("parent_current_contract_ref")),
            expected_ref=expected_current,
        )
        return _safe_mapping(current_parent_current_contract)
    if parent_kind != CONTRACT_PARENT_INITIAL_FALLBACK:
        raise SearchExecutorHandoffRuntimeError(
            "initial_answer_contract_fallback must be explicit when no current contract exists"
        )
    if handoff.get("initial_answer_contract_fallback_explicit") is not True:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff must record initial fallback explicitly"
        )
    _validate_empty_parent_binding(
        label="parent_current_contract",
        action_version=action_inputs.get("parent_current_contract_version"),
        action_digest=action_inputs.get("parent_current_contract_digest"),
        input_ref=_safe_mapping(handoff_input.get("parent_current_contract_ref")),
        handoff_ref=_safe_mapping(handoff.get("parent_current_contract_ref")),
    )
    return _safe_mapping(current_parent_initial_contract)


def _validate_one_parent_binding(
    *,
    label: str,
    action_version: Any,
    action_digest: Any,
    input_ref: Mapping[str, Any],
    handoff_ref: Mapping[str, Any],
    expected_ref: Mapping[str, Any],
) -> None:
    expected_version = _clean_token(expected_ref.get("contract_version"))
    expected_digest = _clean_token(expected_ref.get("contract_digest"), limit=128)
    action_version_text = _clean_token(action_version)
    action_digest_text = _clean_token(action_digest, limit=128)
    input_version = _clean_token(input_ref.get("contract_version"))
    input_digest = _clean_token(input_ref.get("contract_digest"), limit=128)
    handoff_version = _clean_token(handoff_ref.get("contract_version"))
    handoff_digest = _clean_token(handoff_ref.get("contract_digest"), limit=128)
    if (
        action_version_text != expected_version
        or action_digest_text != expected_digest
        or input_version != expected_version
        or input_digest != expected_digest
        or handoff_version != expected_version
        or handoff_digest != expected_digest
    ):
        raise SearchExecutorHandoffRuntimeError(
            f"stale parent digest: {label} binding is not current"
        )


def _validate_empty_parent_binding(
    *,
    label: str,
    action_version: Any,
    action_digest: Any,
    input_ref: Mapping[str, Any],
    handoff_ref: Mapping[str, Any],
) -> None:
    if (
        _clean_token(action_version)
        or _clean_token(action_digest, limit=128)
        or _clean_token(input_ref.get("contract_version"))
        or _clean_token(input_ref.get("contract_digest"), limit=128)
        or _clean_token(handoff_ref.get("contract_version"))
        or _clean_token(handoff_ref.get("contract_digest"), limit=128)
    ):
        raise SearchExecutorHandoffRuntimeError(
            f"stale parent digest: {label} was bound but no current parent exists"
        )


def _validate_planner_bindings(
    *,
    action_inputs: Mapping[str, Any],
    handoff_input: Mapping[str, Any],
    handoff: Mapping[str, Any],
    current_search_planner_proposal_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    parent_planner_ref = _planner_ref_or_raise(
        handoff.get("parent_search_planner_proposal_ref")
    )
    input_planner_ref = _planner_ref_or_raise(
        handoff_input.get("parent_search_planner_proposal_ref")
    )
    current_planner_ref = planner_ref_from_search_planner_state(
        current_search_planner_proposal_state
    )
    if not current_planner_ref:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff requires a current SearchPlanner proposal"
        )
    if parent_planner_ref != input_planner_ref:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff parent planner ref does not match input"
        )
    if parent_planner_ref != current_planner_ref:
        raise SearchExecutorHandoffRuntimeError(
            "stale parent planner digest: handoff does not match current planner proposal"
        )
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
            raise SearchExecutorHandoffRuntimeError(
                "stale parent planner digest: action binding is not current"
            )
    return parent_planner_ref


def _validate_revision_bindings(
    *,
    action_inputs: Mapping[str, Any],
    handoff_input: Mapping[str, Any],
    handoff: Mapping[str, Any],
    current_search_planner_revision_state: Mapping[str, Any] | None,
    parent_planner_ref: Mapping[str, Any],
) -> dict[str, Any]:
    current_revision_ref = revision_ref_from_revision_state(
        current_search_planner_revision_state
    )
    handoff_revision_ref = _revision_ref_or_empty(
        handoff.get("parent_search_planner_revision_ref")
    )
    input_revision_ref = _revision_ref_or_empty(
        handoff_input.get("parent_search_planner_revision_ref")
    )
    direction_consumed = _direction_consumed(handoff)
    if current_revision_ref:
        if not handoff_revision_ref or not input_revision_ref:
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff must bind current SearchPlannerRevision"
            )
        if handoff_revision_ref != input_revision_ref:
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff parent revision ref does not match input"
            )
        if handoff_revision_ref != current_revision_ref:
            raise SearchExecutorHandoffRuntimeError(
                "stale planner revision digest: handoff does not match current revision"
            )
        if (
            _safe_mapping(current_revision_ref.get("parent_search_planner_proposal_ref"))
            != parent_planner_ref
        ):
            raise SearchExecutorHandoffRuntimeError(
                "SearchPlannerRevision is not bound to the current planner/QMR"
            )
        expected = {
            "parent_search_planner_revision_id": current_revision_ref.get(
                "revision_id"
            ),
            "parent_search_planner_revision_digest": current_revision_ref.get(
                "revision_digest"
            ),
        }
        for key, value in expected.items():
            if action_inputs.get(key) != value:
                raise SearchExecutorHandoffRuntimeError(
                    "stale planner revision digest: action binding is not current"
                )
        return current_revision_ref
    if direction_consumed:
        raise SearchExecutorHandoffRuntimeError(
            "Scout direction requires current SearchPlannerRevision"
        )
    if (
        handoff_revision_ref
        or input_revision_ref
        or _clean_token(action_inputs.get("parent_search_planner_revision_id"))
        or _clean_token(
            action_inputs.get("parent_search_planner_revision_digest"),
            limit=128,
        )
    ):
        raise SearchExecutorHandoffRuntimeError(
            "stale planner revision digest: no current revision exists"
        )
    return {}


def _validate_scout_bindings(
    *,
    action_inputs: Mapping[str, Any],
    handoff_input: Mapping[str, Any],
    handoff: Mapping[str, Any],
    current_scout_disambiguation_report_state: Mapping[str, Any] | None,
    parent_planner_ref: Mapping[str, Any],
    parent_revision_ref: Mapping[str, Any],
) -> dict[str, Any]:
    current_scout_ref = scout_ref_from_scout_report_state(
        current_scout_disambiguation_report_state
    )
    handoff_scout_ref = _scout_ref_or_empty(
        handoff.get("parent_scout_disambiguation_report_ref")
    )
    input_scout_ref = _scout_ref_or_empty(
        handoff_input.get("parent_scout_disambiguation_report_ref")
    )
    direction_consumed = _direction_consumed(handoff)
    if direction_consumed:
        if not current_scout_ref:
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff consumes Scout direction without Scout report"
            )
        if not handoff_scout_ref or not input_scout_ref:
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff must bind Scout report when consuming direction"
            )
        if handoff_scout_ref != input_scout_ref:
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff parent Scout ref does not match input"
            )
        if handoff_scout_ref != current_scout_ref:
            raise SearchExecutorHandoffRuntimeError(
                "stale Scout report digest: handoff does not match current Scout report"
            )
        if _safe_mapping(current_scout_ref.get("parent_search_planner_proposal_ref")) != parent_planner_ref:
            raise SearchExecutorHandoffRuntimeError(
                "Scout report is not bound to the current parent planner/QMR"
            )
        if parent_revision_ref and _safe_mapping(
            parent_revision_ref.get("parent_scout_disambiguation_report_ref")
        ) != current_scout_ref:
            raise SearchExecutorHandoffRuntimeError(
                "SearchPlannerRevision is not bound to the current Scout report"
            )
        expected = {
            "parent_scout_disambiguation_report_id": current_scout_ref.get(
                "report_id"
            ),
            "parent_scout_disambiguation_report_digest": current_scout_ref.get(
                "report_digest"
            ),
        }
        for key, value in expected.items():
            if action_inputs.get(key) != value:
                raise SearchExecutorHandoffRuntimeError(
                    "stale Scout report digest: action binding is not current"
                )
        return current_scout_ref
    if handoff_scout_ref or input_scout_ref:
        if not current_scout_ref or handoff_scout_ref != current_scout_ref:
            raise SearchExecutorHandoffRuntimeError(
                "stale Scout report digest: no matching current Scout report exists"
            )
    return current_scout_ref


def _validate_component_and_work_bindings(
    *,
    action_inputs: Mapping[str, Any],
    handoff: Mapping[str, Any],
    active_contract: Mapping[str, Any],
    planner_state: Mapping[str, Any] | None,
    revision_state: Mapping[str, Any] | None,
    scout_state: Mapping[str, Any] | None,
) -> None:
    answer_component_refs = _safe_list(handoff.get("answer_component_refs"))
    component_ids = _ordered_unique(
        ref.get("component_id") for ref in answer_component_refs if isinstance(ref, Mapping)
    )
    if not component_ids:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff requires component refs"
        )
    contract_component_ids = _component_ids_from_contract(active_contract)
    missing_components = [
        component_id
        for component_id in component_ids
        if component_id not in contract_component_ids
    ]
    if missing_components:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff component ids are not present in parent contract: "
            + ", ".join(missing_components)
        )
    if _ordered_unique(action_inputs.get("component_ids")) != component_ids:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff component id bindings do not match authorization"
        )

    known_source_ids = _known_source_obligation_ids(
        active_contract=active_contract,
        planner_state=planner_state,
        revision_state=revision_state,
    )
    included_source_ids = _source_ids_from_handoff(handoff)
    if included_source_ids and not set(included_source_ids).issubset(known_source_ids):
        missing = sorted(set(included_source_ids) - known_source_ids)
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff source obligation refs are not represented: "
            + ", ".join(missing)
        )
    if _ordered_unique(action_inputs.get("source_obligation_candidate_ids")) != included_source_ids:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff source-obligation bindings do not match authorization"
        )

    known_requirement_ids = _known_search_requirement_ids(
        planner_state=planner_state,
        revision_state=revision_state,
    )
    included_requirement_ids = _search_requirement_ids_from_handoff(handoff)
    if included_requirement_ids and not set(included_requirement_ids).issubset(
        known_requirement_ids
    ):
        missing = sorted(set(included_requirement_ids) - known_requirement_ids)
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff search requirement ids are not represented: "
            + ", ".join(missing)
        )
    if _ordered_unique(action_inputs.get("search_requirement_ids")) != included_requirement_ids:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff search-requirement bindings do not match authorization"
        )

    known_hint_ids = _scout_hint_ids_from_report(_safe_mapping(scout_state))
    included_hint_ids = _hint_ids_from_handoff(handoff)
    if included_hint_ids and not set(included_hint_ids).issubset(known_hint_ids):
        missing = sorted(set(included_hint_ids) - known_hint_ids)
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff consumes unknown Scout hints: "
            + ", ".join(missing)
        )
    if _ordered_unique(action_inputs.get("scout_direction_hint_ids")) != included_hint_ids:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff Scout hint bindings do not match authorization"
        )


def _validate_handoff_records(handoff: Mapping[str, Any]) -> None:
    intents = _safe_list(handoff.get("query_intent_records"))
    tasks = _safe_list(handoff.get("search_task_records"))
    if not intents or not tasks:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff requires query intent and task records"
        )
    intent_ids = {
        _clean_token(item.get("query_intent_id"))
        for item in intents
        if isinstance(item, Mapping)
    }
    for intent in intents:
        if not isinstance(intent, Mapping):
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff query intent record must be a mapping"
            )
        for key in (
            "query_intent_id",
            "component_id",
            "intent_summary",
            "search_requirement_id",
        ):
            if not _clean_token(intent.get(key), limit=300):
                raise SearchExecutorHandoffRuntimeError(
                    f"SearchExecutor handoff query intent requires {key}"
                )
        if intent.get("not_live") is not True:
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff query intent must be not_live"
            )
        if intent.get("no_fetch_read_policy_active") is not True:
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff query intent must keep no-fetch/read policy"
            )
        for key in (
            "evidence_admitted",
            "citation_eligible",
            "source_obligation_satisfied",
        ):
            if intent.get(key) is not False:
                raise SearchExecutorHandoffRuntimeError(
                    f"SearchExecutor handoff query intent must keep {key}=False"
                )
    for task in tasks:
        if not isinstance(task, Mapping):
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff task record must be a mapping"
            )
        for key in (
            "search_task_id",
            "query_intent_id",
            "component_id",
            "search_requirement_id",
        ):
            if not _clean_token(task.get(key), limit=300):
                raise SearchExecutorHandoffRuntimeError(
                    f"SearchExecutor handoff task requires {key}"
                )
        if task.get("query_intent_id") not in intent_ids:
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff task references unknown query intent"
            )
        if task.get("execution_status") != TASK_EXECUTION_STATUS:
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff task must be not_executed"
            )
        for key, expected in {
            "not_live": True,
            "no_fetch_read_policy_active": True,
            "provider_calls_executed": False,
            "live_search_executed": False,
            "fetch_read_retrieval_executed": False,
            "evidence_admitted": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
        }.items():
            if task.get(key) is not expected:
                raise SearchExecutorHandoffRuntimeError(
                    f"SearchExecutor handoff task requires {key}={expected}"
                )
    for ref in _safe_list(handoff.get("non_evidence_direction_refs")):
        if not isinstance(ref, Mapping):
            raise SearchExecutorHandoffRuntimeError(
                "SearchExecutor handoff direction ref must be a mapping"
            )
        if ref.get("role") != "search_direction_only":
            raise SearchExecutorHandoffRuntimeError(
                "Scout direction refs must remain search_direction_only"
            )
        for key in (
            "evidence_admitted",
            "citation_eligible",
            "source_obligation_satisfied",
            "fetch_read_retrieval_executed",
        ):
            if ref.get(key) is not False:
                raise SearchExecutorHandoffRuntimeError(
                    "Scout direction refs must keep evidence/citation/source flags false"
                )


def _validate_closed_handoff_flags(handoff: Mapping[str, Any]) -> None:
    for key, expected in _REQUIRED_FALSE_FLAGS.items():
        value = handoff.get(key, False if key in _SAFE_FALSE_RETENTION_KEYS else None)
        if value is not expected:
            raise SearchExecutorHandoffRuntimeError(
                f"SearchExecutor handoff must keep {key} false"
            )
    flags = _safe_mapping(handoff.get("closed_surface_flags"))
    for key, expected in _REQUIRED_FALSE_FLAGS.items():
        value = flags.get(key, False if key in _SAFE_FALSE_RETENTION_KEYS else None)
        if value is not expected:
            raise SearchExecutorHandoffRuntimeError(
                f"SearchExecutor handoff closed-surface flag {key} must be false"
            )
    retention = _safe_mapping(handoff.get("retention_flags"))
    for key, expected in _retention_flags().items():
        if retention.get(key) is not expected:
            raise SearchExecutorHandoffRuntimeError(
                f"SearchExecutor handoff retention flag {key} must be false"
            )
    for key, expected in {
        "not_live": True,
        "no_fetch_read_policy_active": True,
        "search_executor_handoff_created": True,
        "search_work_packet_constructed": True,
    }.items():
        if handoff.get(key) is not expected:
            raise SearchExecutorHandoffRuntimeError(
                f"SearchExecutor handoff requires {key}={expected}"
            )
    if handoff.get("execution_mode") != EXECUTION_MODE:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff must remain offline_handoff_only"
        )


def _direction_consumed(handoff: Mapping[str, Any]) -> bool:
    return bool(
        _safe_list(handoff.get("scout_direction_hint_refs"))
        or _safe_list(handoff.get("non_evidence_direction_refs"))
    )


def _normalize_component_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_list(value):
        mapping = _safe_mapping(item)
        component_id = _clean_token(mapping.get("component_id"))
        if not component_id:
            continue
        refs.append(
            _without_empty(
                {
                    "component_id": component_id,
                    "component_revision": _clean_token(
                        mapping.get("component_revision")
                    ),
                    "component_digest": _clean_token(
                        mapping.get("component_digest"),
                        limit=128,
                    ),
                    "user_facing_label": _clean_text(
                        mapping.get("user_facing_label"),
                        limit=180,
                    ),
                    "requirement_posture": _clean_token(
                        mapping.get("requirement_posture")
                    ),
                    "materiality": _clean_token(mapping.get("materiality")),
                    "source_obligation_candidate_ids": _text_list(
                        mapping.get("source_obligation_candidate_ids")
                    ),
                    "source_obligation_candidate_refs": _text_list(
                        mapping.get("source_obligation_candidate_refs")
                    ),
                    "mandatory_caveats": _text_list(
                        mapping.get("mandatory_caveats"),
                        limit=260,
                    ),
                    "prohibited_upgrades": _text_list(
                        mapping.get("prohibited_upgrades"),
                        limit=260,
                    ),
                }
            )
        )
    return refs


def _normalize_source_obligation_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_list(value):
        mapping = _safe_mapping(item)
        candidate_id = _clean_token(
            mapping.get("candidate_id") or mapping.get("source_obligation_id")
        )
        if not candidate_id:
            continue
        refs.append(
            _without_empty(
                {
                    "candidate_id": candidate_id,
                    "obligation_kind": _clean_token(
                        mapping.get("obligation_kind")
                    )
                    or "source_support",
                    "component_candidate_ids": _text_list(
                        mapping.get("component_candidate_ids")
                        or mapping.get("component_ids")
                    ),
                    "strictness": _clean_token(mapping.get("strictness")),
                    "evidence_admitted": False,
                    "citation_eligible": False,
                    "source_obligation_satisfied": False,
                }
            )
        )
    return refs


def _normalize_requirements(value: Any) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for item in _safe_list(value):
        mapping = _safe_mapping(item)
        component_id = _clean_token(mapping.get("component_id"))
        requirement_id = _clean_token(
            mapping.get("requirement_id") or mapping.get("search_requirement_id")
        )
        if not component_id or not requirement_id:
            continue
        requirements.append(
            _without_empty(
                {
                    "component_id": component_id,
                    "requirement_id": requirement_id,
                    "requirement_summary": _clean_text(
                        mapping.get("requirement_summary")
                        or mapping.get("summary")
                        or mapping.get("query_goal"),
                        limit=420,
                    ),
                    "source_obligation_candidate_ids": _text_list(
                        mapping.get("source_obligation_candidate_ids")
                    ),
                    "preferred_source_kinds": _text_list(
                        mapping.get("preferred_source_kinds")
                    ),
                    "recency_requirement": _clean_text(
                        mapping.get("recency_requirement"),
                        limit=220,
                    ),
                    "must_not_execute": True,
                    "subordinate_to_answer_contract": True,
                    "search_executed": False,
                    "fetch_read_retrieval_executed": False,
                    "evidence_admitted": False,
                    "citation_eligible": False,
                    "source_obligation_satisfied": False,
                }
            )
        )
    return requirements


def _normalize_direction_refs(
    value: Any,
    *,
    default_prefix: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for index, item in enumerate(_safe_list(value), start=1):
        if isinstance(item, Mapping):
            mapping = _safe_mapping(item)
        else:
            mapping = {"hint_id": item}
        hint_id = _clean_token(mapping.get("hint_id"))
        direction_ref_id = _clean_token(
            mapping.get("direction_ref_id") or hint_id or f"{default_prefix}:{index}"
        )
        refs.append(
            _without_empty(
                {
                    "direction_ref_id": direction_ref_id,
                    "source_report_id": _clean_token(mapping.get("source_report_id")),
                    "hint_id": hint_id,
                    "hint_kind": _clean_token(mapping.get("hint_kind")),
                    "title": _clean_text(mapping.get("title"), limit=240),
                    "domain": _clean_text(mapping.get("domain"), limit=240),
                    "link": _clean_text(mapping.get("link"), limit=600),
                    "role": "search_direction_only",
                    "evidence_admitted": False,
                    "citation_eligible": False,
                    "source_obligation_satisfied": False,
                    "fetch_read_retrieval_executed": False,
                }
            )
        )
    return refs


def _normalize_query_budget(value: Any) -> dict[str, Any]:
    mapping = _safe_mapping(value)
    max_tasks = _bounded_int(
        mapping.get("max_search_tasks"),
        minimum=1,
        maximum=25,
        default=5,
    )
    max_results = _bounded_int(
        mapping.get("max_results_per_task"),
        minimum=1,
        maximum=25,
        default=10,
    )
    return {
        "max_search_tasks": max_tasks,
        "max_results_per_task": max_results,
        "max_total_results": max_tasks * max_results,
        "provider_calls_authorized": 0,
        "fetches_authorized": 0,
        "reads_authorized": 0,
        "live_validation_run": False,
        "not_live": True,
        "no_fetch_read_policy_active": True,
    }


def _allowed_verticals(value: Any) -> list[str]:
    verticals = _text_list(value)
    return verticals or ["search"]


def _merge_requirements(*values: Any) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        for item in _safe_list(value):
            mapping = _safe_mapping(item)
            component_id = _clean_token(mapping.get("component_id"))
            requirement_id = _clean_token(
                mapping.get("requirement_id")
                or mapping.get("search_requirement_id")
            )
            if not component_id or not requirement_id:
                continue
            key = (component_id, requirement_id)
            if key in seen:
                continue
            seen.add(key)
            merged.append(mapping)
    return merged


def _requirements_from_components(
    components: Sequence[Any],
) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for index, item in enumerate(components, start=1):
        component = _safe_mapping(item)
        component_id = _clean_token(component.get("component_id"))
        if not component_id:
            continue
        requirements.append(
            {
                "component_id": component_id,
                "requirement_id": f"searchreq:{component_id}:{index}",
                "requirement_summary": _clean_text(
                    component.get("user_facing_label") or component_id,
                    limit=300,
                ),
                "source_obligation_candidate_ids": _text_list(
                    component.get("source_obligation_candidate_ids")
                ),
            }
        )
    return requirements


def _safe_query_text(
    *,
    component: Mapping[str, Any],
    requirement: Mapping[str, Any],
) -> str:
    summary = _clean_text(
        requirement.get("requirement_summary")
        or requirement.get("summary")
        or component.get("user_facing_label")
        or component.get("component_id"),
        limit=260,
    )
    return f"Search task direction: {summary}" if summary else "Search task direction"


def _component_by_id(
    components: Sequence[Any],
    *,
    component_id: str,
) -> dict[str, Any]:
    for item in components:
        mapping = _safe_mapping(item)
        if mapping.get("component_id") == component_id:
            return mapping
    return {}


def _source_ids_for_requirement(
    requirement: Mapping[str, Any],
    component: Mapping[str, Any],
) -> list[str]:
    return _ordered_unique(
        [
            *_text_list(requirement.get("source_obligation_candidate_ids")),
            *_text_list(component.get("source_obligation_candidate_ids")),
            *_text_list(component.get("source_obligation_candidate_refs")),
        ]
    )


def _component_ids_from_contract(contract: Mapping[str, Any]) -> set[str]:
    ids: set[str] = set()
    for item in _safe_list(contract.get("accepted_answer_component_refs")):
        mapping = _safe_mapping(item)
        component_id = _clean_token(mapping.get("component_id"))
        if component_id:
            ids.add(component_id)
    return ids


def _known_source_obligation_ids(
    *,
    active_contract: Mapping[str, Any],
    planner_state: Mapping[str, Any] | None,
    revision_state: Mapping[str, Any] | None,
) -> set[str]:
    ids: set[str] = set()
    for item in _safe_list(active_contract.get("accepted_answer_component_refs")):
        mapping = _safe_mapping(item)
        ids.update(_text_list(mapping.get("source_obligation_candidate_ids")))
        ids.update(_text_list(mapping.get("source_obligation_candidate_refs")))
    planner = _safe_mapping(planner_state)
    qmr = _safe_mapping(planner.get("question_meaning_record"))
    for item in _safe_list(qmr.get("answer_components")):
        mapping = _safe_mapping(item)
        ids.update(_text_list(mapping.get("source_obligation_candidate_ids")))
        ids.update(_text_list(mapping.get("source_obligation_candidate_refs")))
    for item in _safe_list(qmr.get("source_obligation_candidate_refs")):
        mapping = _safe_mapping(item)
        candidate_id = _clean_token(mapping.get("candidate_id"))
        if candidate_id:
            ids.add(candidate_id)
    for item in _safe_list(planner.get("component_search_requirements")):
        ids.update(_text_list(_safe_mapping(item).get("source_obligation_candidate_ids")))
    revision = _safe_mapping(revision_state)
    for key in (
        "component_search_requirement_updates",
        "source_obligation_focus_updates",
        "revised_source_obligation_candidates",
    ):
        for item in _safe_list(revision.get(key)):
            mapping = _safe_mapping(item)
            ids.update(_text_list(mapping.get("source_obligation_candidate_ids")))
            candidate_id = _clean_token(
                mapping.get("candidate_id") or mapping.get("source_obligation_id")
            )
            if candidate_id:
                ids.add(candidate_id)
    return ids


def _known_search_requirement_ids(
    *,
    planner_state: Mapping[str, Any] | None,
    revision_state: Mapping[str, Any] | None,
) -> set[str]:
    ids: set[str] = set()
    for source in (
        _safe_mapping(planner_state).get("component_search_requirements"),
        _safe_mapping(revision_state).get("component_search_requirement_updates"),
    ):
        for item in _safe_list(source):
            mapping = _safe_mapping(item)
            requirement_id = _clean_token(
                mapping.get("requirement_id")
                or mapping.get("search_requirement_id")
            )
            if requirement_id:
                ids.add(requirement_id)
    return ids


def _source_ids_from_handoff(handoff: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in _safe_list(handoff.get("source_obligation_candidate_refs")):
        mapping = _safe_mapping(item)
        ids.append(mapping.get("candidate_id"))
    for key in ("query_intent_records", "search_task_records"):
        for item in _safe_list(handoff.get(key)):
            mapping = _safe_mapping(item)
            ids.extend(_text_list(mapping.get("source_obligation_candidate_ids")))
            ids.extend(_text_list(mapping.get("source_obligation_candidate_refs")))
    return _ordered_unique(ids)


def _search_requirement_ids_from_handoff(handoff: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("query_intent_records", "search_task_records"):
        for item in _safe_list(handoff.get(key)):
            mapping = _safe_mapping(item)
            ids.append(mapping.get("search_requirement_id"))
    return _ordered_unique(ids)


def _hint_ids_from_handoff(handoff: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("scout_direction_hint_refs", "non_evidence_direction_refs"):
        for item in _safe_list(handoff.get(key)):
            mapping = _safe_mapping(item)
            ids.append(mapping.get("hint_id"))
    return _ordered_unique(ids)


def _scout_hint_ids_from_report(report: Mapping[str, Any]) -> set[str]:
    hint_ids: set[str] = set()
    for key in (
        "scout_result_hints",
        "likely_official_target_hints",
        "currentness_hints",
    ):
        for item in _safe_list(report.get(key)):
            mapping = _safe_mapping(item)
            hint_id = _clean_token(mapping.get("hint_id"), limit=180)
            if hint_id:
                hint_ids.add(hint_id)
    for item in _safe_list(report.get("candidate_interpretations")):
        mapping = _safe_mapping(item)
        for hint_id in _text_list(mapping.get("supporting_hint_ids")):
            hint_ids.add(hint_id)
    return hint_ids


def _dedupe_key(handoff: Mapping[str, Any]) -> str:
    return _digest_json(
        {
            "contract_parent_kind": handoff.get("contract_parent_kind"),
            "parent_current_contract_ref": _safe_mapping(
                handoff.get("parent_current_contract_ref")
            ),
            "parent_initial_contract_ref": _safe_mapping(
                handoff.get("parent_initial_contract_ref")
            ),
            "parent_search_planner_proposal_ref": _safe_mapping(
                handoff.get("parent_search_planner_proposal_ref")
            ),
            "parent_search_planner_revision_ref": _safe_mapping(
                handoff.get("parent_search_planner_revision_ref")
            ),
            "parent_scout_disambiguation_report_ref": _safe_mapping(
                handoff.get("parent_scout_disambiguation_report_ref")
            ),
            "component_ids": [
                item.get("component_id")
                for item in _safe_list(handoff.get("answer_component_refs"))
                if isinstance(item, Mapping)
            ],
            "source_obligation_candidate_ids": _source_ids_from_handoff(handoff),
            "search_requirement_ids": _search_requirement_ids_from_handoff(handoff),
            "scout_direction_hint_ids": _hint_ids_from_handoff(handoff),
            "action_type": _EXPECTED_ACTION_TYPE,
        }
    )


def _handoff_digest_payload(handoff: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(handoff)
    payload.pop("handoff_digest", None)
    return payload


def _planner_ref_or_raise(value: Any) -> dict[str, Any]:
    ref = _planner_ref_or_empty(value)
    if not ref:
        raise SearchExecutorHandoffRuntimeError(
            "SearchExecutor handoff requires parent planner proposal and QMR refs"
        )
    return ref


def _planner_ref_or_empty(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    proposal_id = _clean_token(ref.get("proposal_id"))
    proposal_digest = _clean_token(ref.get("proposal_digest"), limit=128)
    qmr_id = _clean_token(ref.get("question_meaning_record_id"))
    qmr_digest = _clean_token(ref.get("question_meaning_record_digest"), limit=128)
    if not proposal_id or not proposal_digest or not qmr_id or not qmr_digest:
        return {}
    return {
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
        "question_meaning_record_id": qmr_id,
        "question_meaning_record_digest": qmr_digest,
    }


def _revision_ref_or_empty(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    revision_id = _clean_token(ref.get("revision_id"))
    revision_digest = _clean_token(ref.get("revision_digest"), limit=128)
    if not revision_id or not revision_digest:
        return {}
    return {
        "revision_id": revision_id,
        "revision_digest": revision_digest,
        "schema_version": _clean_token(ref.get("schema_version")),
        "component_id": _clean_token(ref.get("component_id")),
        "parent_search_planner_proposal_ref": _planner_ref_or_empty(
            ref.get("parent_search_planner_proposal_ref")
        ),
        "parent_scout_disambiguation_report_ref": _scout_ref_or_empty(
            ref.get("parent_scout_disambiguation_report_ref")
        ),
    }


def _scout_ref_or_empty(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    report_id = _clean_token(ref.get("report_id"))
    report_digest = _clean_token(ref.get("report_digest"), limit=128)
    component_id = _clean_token(ref.get("component_id"))
    parent_planner_ref = _planner_ref_or_empty(
        ref.get("parent_search_planner_proposal_ref")
    )
    if not report_id or not report_digest or not component_id or not parent_planner_ref:
        return {}
    return {
        "report_id": report_id,
        "report_digest": report_digest,
        "component_id": component_id,
        "parent_search_planner_proposal_ref": parent_planner_ref,
    }


def _contract_ref_or_empty(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    version = _clean_token(
        ref.get("accepted_contract_version")
        or ref.get("current_contract_version")
        or ref.get("contract_version")
    )
    digest = _clean_token(
        ref.get("accepted_contract_digest")
        or ref.get("current_contract_digest")
        or ref.get("contract_digest"),
        limit=128,
    )
    if not version or not digest:
        return {}
    return {
        "source": _clean_token(ref.get("source")) or "answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _retention_flags() -> dict[str, bool]:
    return {
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "private_artifact_retained": False,
        "full_trace_retained": False,
        "output_packet_retained": False,
    }


def _reject_forbidden_surface_claims(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    sensitive = sorted(key for key in keys if _is_sensitive_key(key))
    if sensitive:
        raise SearchExecutorHandoffRuntimeError(
            f"{context} contains raw/private fields: " + ", ".join(sensitive)
        )
    forbidden = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if forbidden:
        raise SearchExecutorHandoffRuntimeError(
            f"{context} includes closed authority fields: " + ", ".join(forbidden)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SearchExecutorHandoffRuntimeError(
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
            clean_key = _clean_key_token(key, limit=120)
            if not clean_key:
                continue
            if _is_sensitive_key(clean_key):
                if value[key] is False and clean_key in _SAFE_FALSE_RETENTION_KEYS:
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
        raise SearchExecutorHandoffRuntimeError(f"{label} must be a mapping")
    return value


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise SearchExecutorHandoffRuntimeError(message)
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    return _clean_token(value, limit=limit)


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


def _clean_key_token(value: Any, *, limit: int = 120) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


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


def _ordered_unique(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, bytes):
        items = []
    else:
        try:
            items = list(value)
        except TypeError:
            items = []
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_token(item, limit=180)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _enum_or_text(value: Any) -> str | None:
    if isinstance(value, Enum):
        return str(value.value)
    return _clean_token(value)


def _bounded_int(
    value: Any,
    *,
    minimum: int,
    maximum: int,
    default: int,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "SEARCH_EXECUTOR_HANDOFF_OBSERVATION_SCHEMA_VERSION",
    "SEARCH_EXECUTOR_HANDOFF_OWNER",
    "SEARCH_EXECUTOR_HANDOFF_REASON",
    "SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION",
    "SEARCH_EXECUTOR_HANDOFF_STAGE",
    "SEARCH_EXECUTOR_HANDOFF_TRACE_KEY",
    "SearchExecutorHandoffExecutionResult",
    "SearchExecutorHandoffInput",
    "SearchExecutorHandoffRuntimeError",
    "build_search_executor_handoff_observation_payload",
    "build_search_executor_handoff_projection",
    "build_search_executor_handoff_state",
    "contract_ref_from_contract",
    "execute_search_executor_handoff_action",
    "handoff_ref_from_handoff_state",
    "planner_ref_from_search_planner_state",
    "revision_ref_from_revision_state",
    "scout_ref_from_scout_report_state",
]
