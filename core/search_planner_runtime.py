"""RunKernel-authorized SearchPlanner proposal runtime for AG-SEARCH-PLANNER-RUNTIME-01.

The SearchPlanner is a model-call-ready semantic planner boundary. This module
builds bounded adapter input, calls only an explicitly injected adapter, and
turns the adapter's sanitized result into a passive ``QuestionMeaningRecord``
proposal plus subordinate component-search requirements.

It does not import RunKernel, call providers, execute search/fetch/read or
retrieval, create SemanticObservation/ComponentCoverage, admit or apply
amendments, decide Sufficiency, create FinalAnswerPacket/Author input, or
change citation behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Callable, Mapping, Protocol, Sequence

from core.semantic_contract_foundation import (
    AnswerComponentContract,
    Materiality,
    MaterialityPolicy,
    PartialAnswerPolicy,
    QuestionMeaningRecord,
    RequirementPosture,
    ResolverKind,
    SearchWorkPlanRef,
    SemanticSlot,
    SemanticSlotKind,
    SemanticSlotStatus,
    SourceObligationCandidateRef,
    SupportKind,
)

SEARCH_PLANNER_SCHEMA_VERSION = "search_planner_runtime_ag_search_planner_runtime_01_v1"
SEARCH_PLANNER_PROPOSAL_SCHEMA_VERSION = "search_planner_proposal_ag_search_planner_runtime_01_v1"
SEARCH_PLANNER_OBSERVATION_SCHEMA_VERSION = "search_planner_observation_ag_search_planner_runtime_01_v1"
SEARCH_PLANNER_PRODUCTION_STAGE = "search_planner_production"
SEARCH_PLANNER_PRODUCTION_REASON = "search_planner_production_from_authorized_runtime_boundary"
SEARCH_PLANNER_TRACE_KEY = "search_planner_proposal"
SEARCH_PLANNER_PROPOSAL_OWNER = "RunKernel.SearchPlannerProposal"
SEARCH_PLANNER_QMR_RESOLVER_VERSION = "ag-search-planner-runtime-01"
SEARCH_PLANNER_INPUT_PREVIEW_CHARS = 500
SEARCH_PLANNER_FULL_QUERY_TEXT_CHARS = 12000
_ADAPTER_ONLY_USER_QUERY_TEXT_KEY = "user_query_text_for_planning"

_EXPECTED_ACTION_TYPE = "search_planner_produce"
_EXPECTED_OBSERVATION_TYPE = "search_planner_produced"

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
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
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

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "accepted_amendment",
        "accepted_contract",
        "author_input",
        "canonical_coverage",
        "component_coverage_record",
        "contract_amendment_record",
        "current_answer_contract",
        "evidence_ledger_admission",
        "final_answer",
        "final_answer_packet",
        "initial_answer_contract",
        "search_judgment_decision",
        "semantic_observation",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        "accepted_authority",
        "amendment_admitted",
        "amendment_applied",
        "author_behavior_changed",
        "author_executor_invoked",
        "author_input_created",
        "citation_behavior_changed",
        "citation_eligible",
        "citation_rendered",
        "component_satisfied",
        "constructs_search_work_plan",
        "contract_mutation_applied",
        "current_answer_contract_mutated",
        "evidence_admitted",
        "fetch_read_retrieval_behavior_changed",
        "final_answer_packet_created",
        "initial_answer_contract_mutated",
        "live_model_called",
        "live_validation_run",
        "model_called",
        "partial_answer_readiness_changed",
        "provider_called",
        "provider_search_behavior_changed",
        "query_plan_activated",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_trace_retained",
        "runtime_behavior_changed",
        "scout_runtime_activated",
        "search_executed",
        "search_executor_runtime_activated",
        "search_judgment_decided",
        "search_work_plan_activated",
        "source_obligation_satisfied",
        "sufficiency_decided",
    }
)

_REQUIRED_ACTION_INPUT_KEYS = (
    "run_id",
    "request_id",
    "user_query_digest",
    "planner_schema_version",
    "parent_initial_contract_digest",
    "parent_initial_contract_version",
    "parent_current_contract_digest",
    "parent_current_contract_version",
)

_CLOSED_SURFACE_FLAGS = {
    "live_model_called": False,
    "provider_called": False,
    "provider_search_behavior_changed": False,
    "search_executed": False,
    "fetch_read_retrieval_behavior_changed": False,
    "scout_runtime_activated": False,
    "search_executor_runtime_activated": False,
    "contract_mutation_applied": False,
    "initial_answer_contract_mutated": False,
    "current_answer_contract_mutated": False,
    "amendment_admitted": False,
    "amendment_applied": False,
    "semantic_observation_admitted": False,
    "component_coverage_reduced": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "author_behavior_changed": False,
    "citation_behavior_changed": False,
    "partial_answer_readiness_changed": False,
    "raw_prompt_retained": False,
    "raw_provider_payload_retained": False,
    "raw_trace_retained": False,
    "private_artifact_retained": False,
    "live_validation_run": False,
}


class SearchPlannerRuntimeError(ValueError):
    """Raised when planner execution, binding validation, or reduction fails."""


class SearchPlannerAdapter(Protocol):
    """Injected model/planner adapter boundary.

    Production/default code must supply this explicitly. Tests may inject a
    deterministic adapter with the same shape.
    """

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return a sanitized planner proposal mapping."""


@dataclass(frozen=True, slots=True)
class SearchPlannerInput:
    run_id: str
    request_id: str
    user_query_text: str
    requested_mode: str = "balanced"
    planner_schema_version: str = SEARCH_PLANNER_SCHEMA_VERSION
    safe_context: Mapping[str, Any] = field(default_factory=dict)
    route_context_ref: Mapping[str, Any] = field(default_factory=dict)
    run_context_ref: Mapping[str, Any] = field(default_factory=dict)
    parent_initial_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    parent_current_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    closed_surface_flags: Mapping[str, Any] = field(default_factory=dict)

    @property
    def user_query_preview(self) -> str:
        return _clean_text(self.user_query_text, limit=SEARCH_PLANNER_INPUT_PREVIEW_CHARS) or ""

    @property
    def normalized_user_query_text(self) -> str:
        return _normalize_user_query_text(
            self.user_query_text,
            limit=SEARCH_PLANNER_FULL_QUERY_TEXT_CHARS,
        )

    @property
    def user_query_digest(self) -> str:
        payload = {
            "run_id": _clean_token(self.run_id),
            "request_id": _clean_token(self.request_id),
            "normalized_user_query_text": self.normalized_user_query_text,
        }
        return _digest_json(payload)

    def to_adapter_payload(self) -> dict[str, Any]:
        run_id = _clean_token(self.run_id)
        request_id = _clean_token(self.request_id)
        if not run_id or not request_id:
            raise SearchPlannerRuntimeError("search planner input requires run_id and request_id")
        query_digest = self.user_query_digest
        closed_flags = {**_CLOSED_SURFACE_FLAGS, **_safe_mapping(self.closed_surface_flags)}
        closed_flags = {key: bool(value) for key, value in closed_flags.items()}
        if any(value for value in closed_flags.values()):
            raise SearchPlannerRuntimeError("search planner input cannot open closed runtime surfaces")
        return {
            "schema_version": self.planner_schema_version,
            "run_id": run_id,
            "request_id": request_id,
            "requested_mode": _clean_token(self.requested_mode) or "balanced",
            _ADAPTER_ONLY_USER_QUERY_TEXT_KEY: self.normalized_user_query_text,
            "user_query_text_for_planning_char_limit": SEARCH_PLANNER_FULL_QUERY_TEXT_CHARS,
            "user_query_ref": {
                "preview": self.user_query_preview,
                "digest": query_digest,
                "preview_char_limit": SEARCH_PLANNER_INPUT_PREVIEW_CHARS,
                "full_user_query_text_retained": False,
                "raw_user_query_retained": False,
                "user_query_text_for_planning_retained": False,
            },
            "safe_context": _json_safe(self.safe_context),
            "route_context_ref": _json_safe(self.route_context_ref),
            "run_context_ref": _json_safe(self.run_context_ref),
            "parent_contract_refs": {
                "initial": _contract_ref_or_empty(self.parent_initial_contract_ref),
                "current": _contract_ref_or_empty(self.parent_current_contract_ref),
            },
            "closed_surface_flags": closed_flags,
        }


@dataclass(frozen=True, slots=True)
class SearchPlannerExecutionResult:
    adapter_input: Mapping[str, Any]
    observation_payload: Mapping[str, Any]


def execute_search_planner_action(
    *,
    action: Any,
    planner_input: SearchPlannerInput,
    adapter: SearchPlannerAdapter | Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> SearchPlannerExecutionResult:
    """Call an explicitly injected planner adapter and return observation payload.

    ``core.run_kernel`` intentionally remains outside this module. The action is
    validated duck-typed by its public fields so this helper does not import
    RunKernel.
    """

    if adapter is None:
        raise SearchPlannerRuntimeError("search planner requires an explicitly injected adapter")
    _validate_action_like(action=action, planner_input=planner_input)
    adapter_input = planner_input.to_adapter_payload()
    adapter_result = _call_adapter(adapter, adapter_input)
    observation_payload = build_search_planner_observation_payload(
        adapter_result=adapter_result,
        planner_input=adapter_input,
    )
    return SearchPlannerExecutionResult(
        adapter_input=adapter_input,
        observation_payload=observation_payload,
    )


def build_search_planner_observation_payload(
    *,
    adapter_result: Mapping[str, Any],
    planner_input: Mapping[str, Any],
) -> dict[str, Any]:
    planner_input_ref = _planner_input_ref_for_observation(planner_input)
    result = _safe_mapping(adapter_result)
    if not result:
        raise SearchPlannerRuntimeError("search planner adapter returned no proposal")
    _reject_forbidden_surface_claims(result)

    qmr = _question_meaning_record_from_adapter_result(
        adapter_result=result,
        planner_input=planner_input_ref,
    )
    qmr_payload = qmr.to_dict()
    component_search_requirements = _component_search_requirements(result)
    amendment_candidates = _safe_list(result.get("contract_amendment_candidates"))
    deferred_outputs = _text_list(
        result.get("unsupported_outputs")
        or result.get("unsupported_or_deferred_outputs")
        or result.get("deferred_outputs"),
        limit=260,
    )
    if amendment_candidates:
        deferred_outputs.append("contract amendment candidates require a later authorized amendment admission path")

    proposal_base = {
        "schema_version": SEARCH_PLANNER_PROPOSAL_SCHEMA_VERSION,
        "trace_key": SEARCH_PLANNER_TRACE_KEY,
        "owner": SEARCH_PLANNER_PROPOSAL_OWNER,
        "run_id": planner_input_ref.get("run_id"),
        "request_id": planner_input_ref.get("request_id"),
        "planner_schema_version": planner_input_ref.get("schema_version"),
        "requested_mode": planner_input_ref.get("requested_mode"),
        "user_query_ref": _safe_mapping(planner_input_ref.get("user_query_ref")),
        "parent_contract_refs": _safe_mapping(planner_input_ref.get("parent_contract_refs")),
        "question_meaning_summary": _clean_text(
            result.get("question_meaning_summary") or result.get("intent"),
            limit=420,
        ),
        "material_ambiguity_posture": _clean_token(
            result.get("material_ambiguity_posture"),
            limit=120,
        )
        or "unknown",
        "mandatory_caveats": _text_list(result.get("mandatory_caveats"), limit=260),
        "prohibited_upgrades": _text_list(result.get("prohibited_upgrades"), limit=260),
        "normalization_obligations": _text_list(result.get("normalization_obligations"), limit=260),
        "assumptions": _text_list(result.get("assumptions"), limit=260),
        "unsupported_or_deferred_outputs": _dedupe_texts(deferred_outputs),
        "component_search_requirements": component_search_requirements,
        "question_meaning_record": qmr_payload,
        "question_meaning_record_ref": {
            "record_id": qmr_payload.get("record_id"),
            "record_digest": qmr_payload.get("record_digest"),
            "schema_version": qmr_payload.get("schema_version"),
            "answer_component_count": len(qmr_payload.get("answer_components") or []),
            "semantic_slot_count": len(qmr_payload.get("semantic_slots") or []),
        },
        "amendment_path": {
            "status": "deferred",
            "candidate_count": len(amendment_candidates),
            "contract_amendments_applied": False,
            "requires_later_authorized_admission": bool(amendment_candidates),
        },
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
        "adapter_result_sanitized": True,
    }
    proposal_id = (
        "search-planner-proposal:"
        f"{_clean_token(planner_input_ref.get('request_id'))}:"
        f"{qmr_payload.get('record_digest', '')[:16]}"
    )
    proposal_without_digest = {**proposal_base, "proposal_id": proposal_id}
    proposal_digest = _digest_json(_proposal_digest_payload(proposal_without_digest))
    planner_proposal = {
        **proposal_without_digest,
        "proposal_digest": proposal_digest,
    }
    return {
        "schema_version": SEARCH_PLANNER_OBSERVATION_SCHEMA_VERSION,
        "planner_input": planner_input_ref,
        "planner_proposal": planner_proposal,
        "question_meaning_record": qmr_payload,
    }


def build_search_planner_proposal_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    current_parent_initial_contract: Mapping[str, Any] | None = None,
    current_parent_current_contract: Mapping[str, Any] | None = None,
    existing_proposal_history: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Validate one planner proposal observation and build RunKernel state."""

    clean_action_id = _clean_token(action_id, limit=200)
    clean_run_id = _clean_token(run_id)
    clean_request_id = _clean_token(request_id)
    if not clean_action_id or not clean_run_id or not clean_request_id:
        raise SearchPlannerRuntimeError("search planner proposal reduction requires action_id, run_id, and request_id")

    inputs = _safe_mapping(action_inputs)
    payload = _safe_mapping(observation_payload)
    planner_input = _safe_mapping(payload.get("planner_input"))
    proposal = _safe_mapping(payload.get("planner_proposal"))
    qmr_payload = _safe_mapping(proposal.get("question_meaning_record") or payload.get("question_meaning_record"))
    if not planner_input or not proposal or not qmr_payload:
        raise SearchPlannerRuntimeError(
            "search planner proposal observation requires planner_input, planner_proposal, and question_meaning_record"
        )
    if payload.get("schema_version") != SEARCH_PLANNER_OBSERVATION_SCHEMA_VERSION:
        raise SearchPlannerRuntimeError("search planner observation schema version does not match")
    _reject_forbidden_surface_claims(payload)
    _validate_action_inputs(inputs)

    if planner_input.get("run_id") != clean_run_id or proposal.get("run_id") != clean_run_id:
        raise SearchPlannerRuntimeError("search planner proposal run_id does not match the run")
    if planner_input.get("request_id") != clean_request_id or proposal.get("request_id") != clean_request_id:
        raise SearchPlannerRuntimeError("search planner proposal request_id does not match the request")
    if qmr_payload.get("run_id") != clean_run_id or qmr_payload.get("request_id") != clean_request_id:
        raise SearchPlannerRuntimeError("question meaning record run/request binding does not match the run")

    query_ref = _safe_mapping(planner_input.get("user_query_ref"))
    bound_query_digest = _clean_token(inputs.get("user_query_digest"), limit=128)
    query_digest = _clean_token(query_ref.get("digest"), limit=128)
    if not bound_query_digest or not query_digest:
        raise SearchPlannerRuntimeError("search planner proposal requires a user query digest binding")
    if bound_query_digest != query_digest or qmr_payload.get("request_digest") != query_digest:
        raise SearchPlannerRuntimeError("stale query digest: planner proposal does not match authorization")

    bound_schema = _clean_token(inputs.get("planner_schema_version"))
    if bound_schema != SEARCH_PLANNER_SCHEMA_VERSION:
        raise SearchPlannerRuntimeError("search planner action binds the wrong planner schema version")
    if planner_input.get("schema_version") != bound_schema or proposal.get("planner_schema_version") != bound_schema:
        raise SearchPlannerRuntimeError("planner schema version binding does not match proposal")

    _validate_parent_contract_bindings(
        action_inputs=inputs,
        planner_input=planner_input,
        current_parent_initial_contract=current_parent_initial_contract,
        current_parent_current_contract=current_parent_current_contract,
    )

    declared_digest = _clean_token(proposal.get("proposal_digest"), limit=128)
    if not declared_digest:
        raise SearchPlannerRuntimeError("search planner proposal requires proposal_digest")
    recomputed = _digest_json(_proposal_digest_payload(proposal))
    if declared_digest != recomputed:
        raise SearchPlannerRuntimeError("stale planner proposal: proposal digest does not match payload content")

    _validate_question_meaning_payload(qmr_payload, query_digest=query_digest)

    parent_refs = _safe_mapping(planner_input.get("parent_contract_refs"))
    dedupe_key = _dedupe_key(
        proposal_digest=declared_digest,
        user_query_digest=query_digest,
        parent_contract_refs=parent_refs,
    )
    for item in existing_proposal_history:
        history_item = _safe_mapping(item)
        if history_item.get("dedupe_key") == dedupe_key:
            raise SearchPlannerRuntimeError(
                "duplicate search planner proposal for the same query and parent contract context"
            )

    state = {
        "schema_version": SEARCH_PLANNER_PROPOSAL_SCHEMA_VERSION,
        "trace_key": SEARCH_PLANNER_TRACE_KEY,
        "owner": SEARCH_PLANNER_PROPOSAL_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "proposal_id": proposal.get("proposal_id"),
        "proposal_digest": declared_digest,
        "dedupe_key": dedupe_key,
        "planner_schema_version": SEARCH_PLANNER_SCHEMA_VERSION,
        "user_query_ref": query_ref,
        "parent_contract_refs": parent_refs,
        "question_meaning_record": qmr_payload,
        "question_meaning_record_ref": _safe_mapping(proposal.get("question_meaning_record_ref")),
        "question_meaning_summary": proposal.get("question_meaning_summary"),
        "material_ambiguity_posture": proposal.get("material_ambiguity_posture"),
        "component_search_requirements": _safe_list(proposal.get("component_search_requirements")),
        "mandatory_caveats": _text_list(proposal.get("mandatory_caveats"), limit=260),
        "prohibited_upgrades": _text_list(proposal.get("prohibited_upgrades"), limit=260),
        "normalization_obligations": _text_list(proposal.get("normalization_obligations"), limit=260),
        "assumptions": _text_list(proposal.get("assumptions"), limit=260),
        "unsupported_or_deferred_outputs": _text_list(
            proposal.get("unsupported_or_deferred_outputs"),
            limit=260,
        ),
        "amendment_path": _safe_mapping(proposal.get("amendment_path")),
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
        "search_planner_runtime_activated": True,
        "question_meaning_proposed": True,
        "qmr_payload_compatible_with_initial_contract_acceptance": True,
        "component_search_requirements_subordinate": True,
        "component_search_requirements_executed": False,
        "contract_amendments_applied": False,
        "initial_answer_contract_mutated": False,
        "current_answer_contract_mutated": False,
        "search_work_plan_constructed": False,
        "search_executor_runtime_activated": False,
        "source_obligation_satisfied": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "live_validation_run": False,
    }
    return _json_safe(state)


def build_search_planner_proposal_projection(
    *,
    proposal_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project planner proposal state without raw/private data."""

    state = _safe_mapping(proposal_state)
    qmr = _safe_mapping(state.get("question_meaning_record"))
    return {
        "owner": SEARCH_PLANNER_PROPOSAL_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": SEARCH_PLANNER_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "proposal_id": state.get("proposal_id"),
        "proposal_digest": state.get("proposal_digest"),
        "dedupe_key": state.get("dedupe_key"),
        "planner_schema_version": state.get("planner_schema_version"),
        "user_query_ref": _safe_mapping(state.get("user_query_ref")),
        "parent_contract_refs": _safe_mapping(state.get("parent_contract_refs")),
        "question_meaning_record": qmr,
        "question_meaning_record_ref": _safe_mapping(state.get("question_meaning_record_ref")),
        "answer_component_count": len(qmr.get("answer_components") or []),
        "semantic_slot_count": len(qmr.get("semantic_slots") or []),
        "question_meaning_summary": state.get("question_meaning_summary"),
        "material_ambiguity_posture": state.get("material_ambiguity_posture"),
        "component_search_requirements": _safe_list(state.get("component_search_requirements")),
        "component_search_requirements_subordinate": True,
        "component_search_requirements_executed": False,
        "mandatory_caveats": _text_list(state.get("mandatory_caveats"), limit=260),
        "prohibited_upgrades": _text_list(state.get("prohibited_upgrades"), limit=260),
        "normalization_obligations": _text_list(state.get("normalization_obligations"), limit=260),
        "assumptions": _text_list(state.get("assumptions"), limit=260),
        "unsupported_or_deferred_outputs": _text_list(
            state.get("unsupported_or_deferred_outputs"),
            limit=260,
        ),
        "amendment_path": _safe_mapping(state.get("amendment_path")),
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
        "search_planner_runtime_activated": True,
        "question_meaning_proposed": True,
        "qmr_payload_compatible_with_initial_contract_acceptance": True,
        "contract_amendments_applied": False,
        "initial_answer_contract_mutated": False,
        "current_answer_contract_mutated": False,
        "search_work_plan_constructed": False,
        "search_executor_runtime_activated": False,
        "source_obligation_satisfied": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "live_validation_run": False,
    }


def contract_ref_from_contract(
    contract: Mapping[str, Any] | None,
    *,
    source: str,
) -> dict[str, Any]:
    """Return the version/digest binding used by planner authorization."""

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


def _planner_input_ref_for_observation(planner_input: Mapping[str, Any]) -> dict[str, Any]:
    planner_input_ref = _safe_mapping(planner_input)
    planner_input_ref.pop(_ADAPTER_ONLY_USER_QUERY_TEXT_KEY, None)
    planner_input_ref.pop("user_query_text_for_planning_char_limit", None)
    return planner_input_ref


def _validate_action_like(*, action: Any, planner_input: SearchPlannerInput) -> None:
    if action is None:
        raise SearchPlannerRuntimeError("search planner requires an authorized action")
    stage = getattr(action, "stage", None)
    action_type = _enum_or_text(getattr(action, "action_type", None))
    expected_observation_type = _enum_or_text(getattr(action, "expected_observation_type", None))
    inputs = _safe_mapping(getattr(action, "inputs", None))
    if stage != SEARCH_PLANNER_PRODUCTION_STAGE:
        raise SearchPlannerRuntimeError("search planner action stage does not match")
    if action_type != _EXPECTED_ACTION_TYPE:
        raise SearchPlannerRuntimeError("search planner action type does not match")
    if expected_observation_type != _EXPECTED_OBSERVATION_TYPE:
        raise SearchPlannerRuntimeError("search planner expected observation type does not match")
    if _clean_token(getattr(action, "run_id", None)) != _clean_token(planner_input.run_id):
        raise SearchPlannerRuntimeError("search planner action run_id does not match input")
    if _clean_token(inputs.get("request_id")) != _clean_token(planner_input.request_id):
        raise SearchPlannerRuntimeError("search planner action request_id does not match input")
    if _clean_token(inputs.get("user_query_digest"), limit=128) != planner_input.user_query_digest:
        raise SearchPlannerRuntimeError("search planner action user query digest does not match input")
    if _clean_token(inputs.get("planner_schema_version")) != planner_input.planner_schema_version:
        raise SearchPlannerRuntimeError("search planner action planner schema version does not match input")


def _call_adapter(
    adapter: SearchPlannerAdapter | Callable[[Mapping[str, Any]], Mapping[str, Any]],
    adapter_input: Mapping[str, Any],
) -> Mapping[str, Any]:
    if hasattr(adapter, "produce"):
        result = adapter.produce(adapter_input)  # type: ignore[union-attr]
    else:
        result = adapter(adapter_input)  # type: ignore[misc]
    if not isinstance(result, Mapping):
        raise SearchPlannerRuntimeError("search planner adapter must return a mapping")
    return result


def _question_meaning_record_from_adapter_result(
    *,
    adapter_result: Mapping[str, Any],
    planner_input: Mapping[str, Any],
) -> QuestionMeaningRecord:
    query_ref = _safe_mapping(planner_input.get("user_query_ref"))
    request_digest = _clean_token(query_ref.get("digest"), limit=128)
    if not request_digest:
        raise SearchPlannerRuntimeError("search planner input requires user_query_ref.digest")
    run_id = _clean_token(planner_input.get("run_id"))
    request_id = _clean_token(planner_input.get("request_id"))
    if not run_id or not request_id:
        raise SearchPlannerRuntimeError("search planner input requires run_id and request_id")

    slots = _semantic_slots(adapter_result.get("semantic_slots"))
    components = _answer_components(adapter_result.get("answer_components"))
    source_refs = _source_obligation_refs(
        adapter_result.get("source_obligation_candidates"),
        components=components,
    )
    component_search_requirements = _component_search_requirements(adapter_result)
    search_work_plan_ref = None
    if component_search_requirements:
        search_work_plan_ref = SearchWorkPlanRef(
            plan_id=f"search-planner-planning-only:{request_digest[:16]}",
            schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
            relationship=(
                "SearchPlanner component search requirements are subordinate planning refs; "
                "RunKernel has not constructed or executed a SearchWorkPlan."
            ),
            planning_only=True,
            semantic_owner=False,
            trace_only=True,
            metadata={"component_search_requirement_count": len(component_search_requirements)},
        )

    metadata = {
        "search_planner_schema_version": SEARCH_PLANNER_SCHEMA_VERSION,
        "planner_phase": "AG-SEARCH-PLANNER-RUNTIME-01",
        "material_ambiguity_posture": _clean_token(
            adapter_result.get("material_ambiguity_posture"),
            limit=120,
        )
        or "unknown",
        "mandatory_caveats": _text_list(adapter_result.get("mandatory_caveats"), limit=260),
        "prohibited_upgrades": _text_list(adapter_result.get("prohibited_upgrades"), limit=260),
        "normalization_obligations": _text_list(adapter_result.get("normalization_obligations"), limit=260),
        "assumptions": _text_list(adapter_result.get("assumptions"), limit=260),
        "unsupported_or_deferred_outputs": _text_list(
            adapter_result.get("unsupported_outputs")
            or adapter_result.get("unsupported_or_deferred_outputs")
            or adapter_result.get("deferred_outputs"),
            limit=260,
        ),
        "component_search_requirements_subordinate": True,
        "component_search_requirements_executed": False,
        "contract_amendment_candidates_deferred": bool(
            _safe_list(adapter_result.get("contract_amendment_candidates"))
        ),
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }

    record = QuestionMeaningRecord(
        record_id=f"qmr:search-planner:{request_id}:{request_digest[:16]}",
        run_id=run_id,
        request_id=request_id,
        request_digest=request_digest,
        requested_mode=_clean_token(planner_input.get("requested_mode")) or "balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version=SEARCH_PLANNER_QMR_RESOLVER_VERSION,
        intent=_clean_text(
            adapter_result.get("question_meaning_summary")
            or adapter_result.get("intent")
            or "SearchPlanner proposed question meaning.",
            limit=360,
        )
        or "SearchPlanner proposed question meaning.",
        requested_output=_clean_text(
            adapter_result.get("requested_output")
            or adapter_result.get("answer_output")
            or "Answer all required components with bounded source support.",
            limit=300,
        )
        or "Answer all required components with bounded source support.",
        semantic_slots=tuple(slots),
        answer_components=tuple(components),
        source_obligation_candidate_refs=tuple(source_refs),
        search_work_plan_ref=search_work_plan_ref,
        materiality_policy=MaterialityPolicy(auto_accepts_amendments=False),
        metadata=metadata,
        passive=True,
        canonical_state=False,
        runtime_behavior_changed=False,
    )
    return record.require_valid()


def _semantic_slots(value: Any) -> list[SemanticSlot]:
    items = _safe_list(value)
    if not items:
        raise SearchPlannerRuntimeError("search planner proposal requires at least one semantic slot")
    slots: list[SemanticSlot] = []
    for item in items:
        mapping = _safe_mapping(item)
        if not mapping:
            raise SearchPlannerRuntimeError("semantic slot proposal must be a mapping")
        slot_id = _clean_token(mapping.get("slot_id"))
        if not slot_id:
            raise SearchPlannerRuntimeError("semantic slot proposal requires slot_id")
        slots.append(
            SemanticSlot(
                slot_id=slot_id,
                slot_kind=mapping.get("slot_kind") or SemanticSlotKind.UNKNOWN_OR_OTHER,
                status=mapping.get("status") or SemanticSlotStatus.UNRESOLVED,
                candidate_values=tuple(_text_list(mapping.get("candidate_values"), limit=220)),
                selected_value=_clean_text(mapping.get("selected_value"), limit=220),
                materiality=mapping.get("materiality") or Materiality.UNKNOWN,
                user_confirmation_required=bool(mapping.get("user_confirmation_required", False)),
                normalization_notes=tuple(_text_list(mapping.get("normalization_notes"), limit=260)),
                metadata=_safe_mapping(mapping.get("metadata")),
            )
        )
    return slots


def _answer_components(value: Any) -> list[AnswerComponentContract]:
    items = _safe_list(value)
    if not items:
        raise SearchPlannerRuntimeError("search planner proposal requires at least one answer component")
    components: list[AnswerComponentContract] = []
    for item in items:
        mapping = _safe_mapping(item)
        if not mapping:
            raise SearchPlannerRuntimeError("answer component proposal must be a mapping")
        component_id = _clean_token(mapping.get("component_id"))
        label = _clean_text(mapping.get("user_facing_label"), limit=180)
        question = _clean_text(mapping.get("user_facing_question"), limit=400)
        if not component_id or not label or not question:
            raise SearchPlannerRuntimeError(
                "answer component proposal requires component_id, user_facing_label, and user_facing_question"
            )
        components.append(
            AnswerComponentContract(
                component_id=component_id,
                user_facing_label=label,
                user_facing_question=question,
                component_revision=_clean_token(mapping.get("component_revision")) or "1",
                requirement_posture=mapping.get("requirement_posture") or RequirementPosture.REQUIRED,
                acceptance_criteria=tuple(_text_list(mapping.get("acceptance_criteria"), limit=320)),
                semantic_slot_ids=tuple(_text_list(mapping.get("semantic_slot_ids"), limit=160)),
                source_obligation_candidate_ids=tuple(
                    _text_list(mapping.get("source_obligation_candidate_ids"), limit=160)
                ),
                source_obligation_candidate_refs=tuple(
                    _text_list(mapping.get("source_obligation_candidate_refs"), limit=160)
                ),
                allowed_support_kinds=tuple(mapping.get("allowed_support_kinds") or (SupportKind.DIRECT,)),
                max_inference_depth=int(mapping.get("max_inference_depth") or 0),
                normalization_policy=_clean_text(mapping.get("normalization_policy"), limit=300),
                calculation_policy=_clean_text(mapping.get("calculation_policy"), limit=300),
                dependency_component_ids=tuple(_text_list(mapping.get("dependency_component_ids"), limit=160)),
                partial_answer_policy=mapping.get("partial_answer_policy")
                or PartialAnswerPolicy.QUALIFY_VISIBLE_GAP,
                mandatory_caveats=tuple(_text_list(mapping.get("mandatory_caveats"), limit=260)),
                prohibited_upgrades=tuple(_text_list(mapping.get("prohibited_upgrades"), limit=260)),
                materiality=mapping.get("materiality") or Materiality.MATERIAL,
                metadata=_safe_mapping(mapping.get("metadata")),
            )
        )
    return components


def _source_obligation_refs(
    value: Any,
    *,
    components: Sequence[AnswerComponentContract],
) -> list[SourceObligationCandidateRef]:
    items = _safe_list(value)
    refs: list[SourceObligationCandidateRef] = []
    if items:
        for item in items:
            mapping = _safe_mapping(item)
            candidate_id = _clean_token(mapping.get("candidate_id"))
            if not candidate_id:
                raise SearchPlannerRuntimeError("source obligation candidate requires candidate_id")
            refs.append(
                SourceObligationCandidateRef(
                    candidate_id=candidate_id,
                    obligation_kind=_clean_token(mapping.get("obligation_kind")) or "source_support",
                    component_candidate_ids=tuple(
                        _text_list(
                            mapping.get("component_candidate_ids")
                            or mapping.get("component_ids"),
                            limit=160,
                        )
                    ),
                    strictness=_clean_token(mapping.get("strictness")),
                    trace_only=True,
                    metadata=_safe_mapping(mapping.get("metadata")),
                )
            )
        return refs

    seen: set[str] = set()
    for component in components:
        for candidate_id in component.source_obligation_candidate_ids:
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            refs.append(
                SourceObligationCandidateRef(
                    candidate_id=candidate_id,
                    obligation_kind="source_support",
                    component_candidate_ids=(component.component_id,),
                    strictness="required" if component.requirement_posture.value == "required" else None,
                    trace_only=True,
                )
            )
    return refs


def _component_search_requirements(adapter_result: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = (
        adapter_result.get("component_search_requirements")
        or adapter_result.get("component_search_plan")
        or adapter_result.get("search_requirements")
        or []
    )
    requirements: list[dict[str, Any]] = []
    for item in _safe_list(raw):
        mapping = _safe_mapping(item)
        if not mapping:
            continue
        requirements.append(
            _without_empty(
                {
                    "component_id": _clean_token(mapping.get("component_id")),
                    "requirement_id": _clean_token(
                        mapping.get("requirement_id") or mapping.get("search_requirement_id")
                    ),
                    "requirement_summary": _clean_text(
                        mapping.get("requirement_summary")
                        or mapping.get("summary")
                        or mapping.get("query_goal"),
                        limit=320,
                    ),
                    "source_obligation_candidate_ids": _text_list(
                        mapping.get("source_obligation_candidate_ids"),
                        limit=160,
                    ),
                    "preferred_source_kinds": _text_list(mapping.get("preferred_source_kinds"), limit=160),
                    "recency_requirement": _clean_text(mapping.get("recency_requirement"), limit=220),
                    "must_not_execute": True,
                    "subordinate_to_answer_contract": True,
                    "search_executed": False,
                    "fetch_read_retrieval_behavior_changed": False,
                    "source_obligation_satisfied": False,
                    "metadata": _safe_mapping(mapping.get("metadata")),
                }
            )
        )
    return requirements


def _validate_action_inputs(inputs: Mapping[str, Any]) -> None:
    missing = [key for key in _REQUIRED_ACTION_INPUT_KEYS if key not in inputs]
    if missing:
        raise SearchPlannerRuntimeError("search planner action missing required bindings: " + ", ".join(missing))
    for key in ("run_id", "request_id", "user_query_digest", "planner_schema_version"):
        if not _clean_token(inputs.get(key), limit=128):
            raise SearchPlannerRuntimeError(f"search planner action requires {key} binding")


def _validate_parent_contract_bindings(
    *,
    action_inputs: Mapping[str, Any],
    planner_input: Mapping[str, Any],
    current_parent_initial_contract: Mapping[str, Any] | None,
    current_parent_current_contract: Mapping[str, Any] | None,
) -> None:
    parent_refs = _safe_mapping(planner_input.get("parent_contract_refs"))
    expected_initial = contract_ref_from_contract(
        current_parent_initial_contract,
        source="initial_answer_contract",
    )
    expected_current = contract_ref_from_contract(
        current_parent_current_contract,
        source="current_answer_contract",
    )
    _validate_one_parent_binding(
        label="parent_initial_contract",
        action_version=action_inputs.get("parent_initial_contract_version"),
        action_digest=action_inputs.get("parent_initial_contract_digest"),
        planner_ref=_safe_mapping(parent_refs.get("initial")),
        expected_ref=expected_initial,
    )
    _validate_one_parent_binding(
        label="parent_current_contract",
        action_version=action_inputs.get("parent_current_contract_version"),
        action_digest=action_inputs.get("parent_current_contract_digest"),
        planner_ref=_safe_mapping(parent_refs.get("current")),
        expected_ref=expected_current,
    )


def _validate_one_parent_binding(
    *,
    label: str,
    action_version: Any,
    action_digest: Any,
    planner_ref: Mapping[str, Any],
    expected_ref: Mapping[str, Any],
) -> None:
    expected_version = _clean_token(expected_ref.get("contract_version"))
    expected_digest = _clean_token(expected_ref.get("contract_digest"), limit=128)
    action_version_text = _clean_token(action_version)
    action_digest_text = _clean_token(action_digest, limit=128)
    planner_version = _clean_token(planner_ref.get("contract_version"))
    planner_digest = _clean_token(planner_ref.get("contract_digest"), limit=128)

    if expected_ref:
        if action_version_text != expected_version or action_digest_text != expected_digest:
            raise SearchPlannerRuntimeError(f"stale parent digest: {label} action binding is not current")
        if planner_version != expected_version or planner_digest != expected_digest:
            raise SearchPlannerRuntimeError(f"stale parent digest: {label} planner input is not current")
        return
    if action_version_text or action_digest_text or planner_version or planner_digest:
        raise SearchPlannerRuntimeError(f"stale parent digest: {label} was bound but no current parent exists")


def _validate_question_meaning_payload(qmr_payload: Mapping[str, Any], *, query_digest: str) -> None:
    if qmr_payload.get("passive") is not True:
        raise SearchPlannerRuntimeError("search planner QMR must remain passive")
    if qmr_payload.get("canonical_state") is True:
        raise SearchPlannerRuntimeError("search planner QMR cannot be canonical state")
    if qmr_payload.get("runtime_behavior_changed") is True:
        raise SearchPlannerRuntimeError("search planner QMR must not change runtime behavior")
    if qmr_payload.get("provider_search_behavior_changed") is True:
        raise SearchPlannerRuntimeError("search planner QMR must not change provider search behavior")
    if qmr_payload.get("request_digest") != query_digest:
        raise SearchPlannerRuntimeError("search planner QMR request digest does not match query digest")
    validation = _safe_mapping(qmr_payload.get("validation"))
    if validation.get("ok") is False:
        errors = validation.get("errors") or []
        raise SearchPlannerRuntimeError("search planner QMR failed validation: " + ", ".join(map(str, errors)))
    if not qmr_payload.get("record_id") or not qmr_payload.get("record_digest"):
        raise SearchPlannerRuntimeError("search planner QMR requires record_id and record_digest")
    if not _safe_list(qmr_payload.get("answer_components")):
        raise SearchPlannerRuntimeError("search planner QMR requires answer components")


def _dedupe_key(
    *,
    proposal_digest: str,
    user_query_digest: str,
    parent_contract_refs: Mapping[str, Any],
) -> str:
    return _digest_json(
        {
            "proposal_digest": proposal_digest,
            "user_query_digest": user_query_digest,
            "parent_contract_refs": _safe_mapping(parent_contract_refs),
            "action_type": _EXPECTED_ACTION_TYPE,
        }
    )


def _proposal_digest_payload(proposal: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(proposal)
    payload.pop("proposal_digest", None)
    return payload


def _contract_ref_or_empty(value: Mapping[str, Any] | None) -> dict[str, Any]:
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


def _reject_forbidden_surface_claims(value: Any) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if forbidden:
        raise SearchPlannerRuntimeError("search planner proposal includes closed authority fields: " + ", ".join(forbidden))
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SearchPlannerRuntimeError("search planner proposal opens closed surfaces: " + ", ".join(dangerous))


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
    result = _json_safe(list(value))
    return list(result) if isinstance(result, list) else []


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 7:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=900)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key or _is_sensitive_key(clean_key):
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
    return _clean_text(value, limit=300)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PRIVATE_VALUE_MARKERS):
        return "[redacted]"
    return text[:limit]


def _normalize_user_query_text(
    value: Any,
    *,
    limit: int = SEARCH_PLANNER_FULL_QUERY_TEXT_CHARS,
) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).strip().split())
    if not text:
        return ""
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _is_sensitive_key(key: Any) -> bool:
    normalized = _normalize_key(key)
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _text_list(value: Any, *, limit: int = 160) -> list[str]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return [text] if text else []
    if not isinstance(value, Sequence) or isinstance(value, bytes):
        return []
    out: list[str] = []
    for item in value:
        text = _clean_text(item, limit=limit)
        if text:
            out.append(text)
    return out


def _dedupe_texts(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None and value != [] and value != {}}


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _enum_or_text(value: Any) -> str | None:
    if isinstance(value, Enum):
        return str(value.value)
    return _clean_token(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "SEARCH_PLANNER_OBSERVATION_SCHEMA_VERSION",
    "SEARCH_PLANNER_PRODUCTION_REASON",
    "SEARCH_PLANNER_PRODUCTION_STAGE",
    "SEARCH_PLANNER_FULL_QUERY_TEXT_CHARS",
    "SEARCH_PLANNER_INPUT_PREVIEW_CHARS",
    "SEARCH_PLANNER_PROPOSAL_OWNER",
    "SEARCH_PLANNER_PROPOSAL_SCHEMA_VERSION",
    "SEARCH_PLANNER_SCHEMA_VERSION",
    "SEARCH_PLANNER_TRACE_KEY",
    "SearchPlannerAdapter",
    "SearchPlannerExecutionResult",
    "SearchPlannerInput",
    "SearchPlannerRuntimeError",
    "build_search_planner_observation_payload",
    "build_search_planner_proposal_projection",
    "build_search_planner_proposal_state",
    "contract_ref_from_contract",
    "execute_search_planner_action",
]
