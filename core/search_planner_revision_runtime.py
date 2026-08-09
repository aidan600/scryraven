"""RunKernel-authorized SearchPlannerRevision runtime.

SearchPlannerRevision consumes a stored Scout DisambiguationReport as
non-evidence direction, produces sanitized planner-revision state, and emits
passive amendment candidates. It does not mutate contracts, admit amendments,
apply amendments, execute search/fetch/read/retrieval, create EvidenceLedger
custody, create citations, decide sufficiency, create FinalAnswerPacket, or
create Author input.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Callable, Mapping, Protocol, Sequence

from core.cap_enforcement import RunCapExceeded
from core.contract_amendment_record import (
    CONTRACT_AMENDMENT_RECORD_SCHEMA_VERSION,
    AffectedComponentRef,
    AmendmentLineage,
    AmendmentOperation,
    AmendmentOperationKind,
    AmendmentTriggerRefs,
    ContractAmendmentRecord,
    MaterialityPosture,
    ModePermissionPosture,
    MonotonicityPosture,
    ProposalDisposition,
    UserConfirmationPosture,
    WeakeningPosture,
)

SEARCH_PLANNER_REVISION_SCHEMA_VERSION = (
    "search_planner_revision_runtime_ag_search_planner_revision_01_v2"
)
SEARCH_PLANNER_REVISION_PROPOSAL_SCHEMA_VERSION = (
    "search_planner_revision_proposal_ag_search_planner_revision_01_v2"
)
SEARCH_PLANNER_REVISION_OBSERVATION_SCHEMA_VERSION = (
    "search_planner_revision_observation_ag_search_planner_revision_01_v2"
)
SEARCH_PLANNER_REVISION_STAGE = "search_planner_revision"
SEARCH_PLANNER_REVISION_REASON = (
    "search_planner_revision_from_scout_disambiguation_report"
)
SEARCH_PLANNER_REVISION_TRACE_KEY = "search_planner_revision"
SEARCH_PLANNER_REVISION_OWNER = "RunKernel.SearchPlannerRevision"
SCOUT_DIRECTIONAL_CONTEXT_SCHEMA_VERSION = "search_planner_revision_scout_directional_context_v1"
SCOUT_DIRECTIONAL_CONTEXT_MAX_HINTS = 25

_EXPECTED_ACTION_TYPE = "search_planner_revise"
_EXPECTED_OBSERVATION_TYPE = "search_planner_revised"

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
    "scout_hints_are_evidence": False,
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
        "current_answer_contract_created",
        "evidence_ledger_admitted",
        "fetch_executed",
        "live_search_called",
        "model_called",
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
    "parent_scout_disambiguation_report_id",
    "parent_scout_disambiguation_report_digest",
    "component_id",
    "consumed_ambiguity_dimension_ids",
    "consumed_scout_hint_ids",
    "parent_initial_contract_version",
    "parent_initial_contract_digest",
    "revision_schema_version",
    "reason",
)

_ALLOWED_OPERATION_KINDS = frozenset({"add_caveat", "strengthen_source_obligation"})
_FORBIDDEN_OPERATION_KINDS = frozenset(
    {
        "mark_requirement_satisfied",
        "mark_source_obligation_satisfied",
        "resolve_slot",
    }
)


class SearchPlannerRevisionRuntimeError(ValueError):
    """Raised when revision execution, binding validation, or reduction fails."""


class SearchPlannerRevisionAdapter(Protocol):
    """Injected revision adapter boundary."""

    def produce(self, revision_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return a sanitized planner-revision proposal mapping."""


@dataclass(frozen=True, slots=True)
class SearchPlannerRevisionInput:
    run_id: str
    request_id: str
    parent_search_planner_proposal_ref: Mapping[str, Any]
    parent_scout_disambiguation_report_ref: Mapping[str, Any]
    parent_initial_contract_ref: Mapping[str, Any]
    parent_current_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    component_id: str = ""
    consumed_ambiguity_dimension_ids: Sequence[str] = field(default_factory=tuple)
    consumed_scout_hint_ids: Sequence[str] = field(default_factory=tuple)
    scout_directional_context: Mapping[str, Any] = field(default_factory=dict)
    safe_revision_context: Mapping[str, Any] = field(default_factory=dict)
    closed_surface_flags: Mapping[str, Any] = field(default_factory=dict)

    def to_adapter_payload(self) -> dict[str, Any]:
        run_id = _required_token(self.run_id, "planner revision input requires run_id")
        request_id = _required_token(
            self.request_id,
            "planner revision input requires request_id",
        )
        component_id = _required_token(
            self.component_id,
            "planner revision input requires component_id",
        )
        parent_planner_ref = _planner_ref_or_raise(
            self.parent_search_planner_proposal_ref
        )
        parent_scout_ref = _scout_ref_or_raise(
            self.parent_scout_disambiguation_report_ref
        )
        dimension_ids = _text_list(self.consumed_ambiguity_dimension_ids)
        hint_ids = _text_list(self.consumed_scout_hint_ids)
        if not dimension_ids:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision input requires consumed ambiguity dimensions"
            )
        directional_context = _normalize_scout_directional_context(
            self.scout_directional_context,
            parent_scout_ref=parent_scout_ref,
            component_id=component_id,
            consumed_dimension_ids=dimension_ids,
            consumed_hint_ids=hint_ids,
        )
        if hint_ids and not directional_context:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision input requires lineage-bound Scout direction"
            )
        closed_flags = {**_REQUIRED_FALSE_FLAGS, **_safe_mapping(self.closed_surface_flags)}
        if any(bool(value) for value in closed_flags.values()):
            raise SearchPlannerRevisionRuntimeError(
                "planner revision input cannot open closed runtime surfaces"
            )
        _reject_forbidden_surface_claims(
            self.safe_revision_context,
            context="planner revision input",
        )
        return {
            "schema_version": SEARCH_PLANNER_REVISION_SCHEMA_VERSION,
            "run_id": run_id,
            "request_id": request_id,
            "parent_search_planner_proposal_ref": parent_planner_ref,
            "parent_scout_disambiguation_report_ref": parent_scout_ref,
            "parent_initial_contract_ref": _contract_ref_or_empty(
                self.parent_initial_contract_ref
            ),
            "parent_current_contract_ref": _contract_ref_or_empty(
                self.parent_current_contract_ref
            ),
            "component_id": component_id,
            "consumed_ambiguity_dimension_ids": dimension_ids,
            "consumed_scout_hint_ids": hint_ids,
            "scout_directional_context": directional_context,
            "safe_revision_context": _json_safe(self.safe_revision_context),
            "closed_surface_flags": {
                key: bool(value) for key, value in closed_flags.items()
            },
        }


@dataclass(frozen=True, slots=True)
class SearchPlannerRevisionExecutionResult:
    adapter_input: Mapping[str, Any]
    observation_payload: Mapping[str, Any]


def execute_search_planner_revision_action(
    *,
    action: Any,
    revision_input: SearchPlannerRevisionInput,
    adapter: SearchPlannerRevisionAdapter
    | Callable[[Mapping[str, Any]], Mapping[str, Any]]
    | None = None,
) -> SearchPlannerRevisionExecutionResult:
    """Call an explicitly injected revision adapter and return observation."""

    if adapter is None:
        raise SearchPlannerRevisionRuntimeError(
            "search planner revision requires an explicitly injected adapter"
        )
    _validate_action_like(action=action, revision_input=revision_input)
    adapter_input = revision_input.to_adapter_payload()
    adapter_result = _call_adapter(adapter, adapter_input)
    observation_payload = build_search_planner_revision_observation_payload(
        adapter_result=adapter_result,
        revision_input=adapter_input,
        authorized_action_id=_clean_token(getattr(action, "action_id", None)),
    )
    return SearchPlannerRevisionExecutionResult(
        adapter_input=adapter_input,
        observation_payload=observation_payload,
    )


def build_search_planner_revision_observation_payload(
    *,
    adapter_result: Mapping[str, Any],
    revision_input: Mapping[str, Any],
    authorized_action_id: str | None = None,
) -> dict[str, Any]:
    revision_input_ref = _safe_mapping(revision_input)
    result = _required_mapping(adapter_result, "planner revision adapter result")
    _reject_forbidden_surface_claims(
        result,
        context="planner revision adapter result",
    )
    _validate_required_adapter_fields(result)
    input_dimension_ids = _text_list(
        revision_input_ref.get("consumed_ambiguity_dimension_ids")
    )
    input_hint_ids = _text_list(revision_input_ref.get("consumed_scout_hint_ids"))
    consumed_dimensions = _text_list(result.get("consumed_ambiguity_dimension_ids"))
    consumed_hints = _text_list(result.get("consumed_scout_hint_ids"))
    if consumed_dimensions != input_dimension_ids:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision consumed dimensions do not match input"
        )
    if consumed_hints != input_hint_ids:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision consumed Scout hint ids do not match input"
        )
    closed_flags = {
        **_REQUIRED_FALSE_FLAGS,
        **_safe_mapping(result.get("closed_surface_flags")),
    }
    if any(bool(value) for value in closed_flags.values()):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision output cannot open closed runtime surfaces"
        )

    revision_base = {
        "schema_version": SEARCH_PLANNER_REVISION_PROPOSAL_SCHEMA_VERSION,
        "trace_key": SEARCH_PLANNER_REVISION_TRACE_KEY,
        "owner": SEARCH_PLANNER_REVISION_OWNER,
        "run_id": revision_input_ref.get("run_id"),
        "request_id": revision_input_ref.get("request_id"),
        "authorized_action_id": authorized_action_id,
        "parent_search_planner_proposal_ref": _safe_mapping(
            revision_input_ref.get("parent_search_planner_proposal_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            revision_input_ref.get("parent_scout_disambiguation_report_ref")
        ),
        "parent_initial_contract_ref": _contract_ref_or_empty(
            revision_input_ref.get("parent_initial_contract_ref")
        ),
        "parent_current_contract_ref": _contract_ref_or_empty(
            revision_input_ref.get("parent_current_contract_ref")
        ),
        "component_id": revision_input_ref.get("component_id"),
        "consumed_ambiguity_dimension_ids": consumed_dimensions,
        "consumed_scout_hint_ids": consumed_hints,
        "revised_question_meaning_summary": _clean_text(
            result.get("revised_question_meaning_summary"),
            limit=500,
        ),
        "revised_question_meaning_record": _safe_mapping(
            result.get("revised_question_meaning_record")
        ),
        "semantic_slot_updates": _safe_list(
            result.get("semantic_slot_updates") or result.get("revised_semantic_slots")
        ),
        "answer_component_updates": _safe_list(
            result.get("answer_component_updates")
            or result.get("revised_answer_components")
        ),
        "component_search_requirement_updates": _safe_list(
            result.get("component_search_requirement_updates")
            or result.get("revised_component_search_requirements")
        ),
        "revised_source_obligation_candidates": _safe_list(
            result.get("revised_source_obligation_candidates")
        ),
        "source_obligation_focus_updates": _safe_list(
            result.get("source_obligation_focus_updates")
        ),
        "mandatory_caveats": _text_list(result.get("mandatory_caveats"), limit=360),
        "prohibited_upgrades": _text_list(
            result.get("prohibited_upgrades"),
            limit=260,
        ),
        "normalization_obligations": _text_list(
            result.get("normalization_obligations"),
            limit=260,
        ),
        "assumptions": _text_list(result.get("assumptions"), limit=260),
        "unresolved_ambiguities": _safe_list(result.get("unresolved_ambiguities")),
        "planner_revision_notes": _text_list(
            result.get("planner_revision_notes"),
            limit=300,
        ),
        "confidence_posture": _clean_token(result.get("confidence_posture"))
        or "directional",
        "revision_posture": _clean_token(result.get("revision_posture"))
        or "proposal_only",
        "planner_revision_metadata": _planner_revision_metadata(result),
        "closed_surface_flags": dict(_REQUIRED_FALSE_FLAGS),
        "retention_flags": {
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
        },
        **_REQUIRED_FALSE_FLAGS,
    }
    revision_id = (
        "search-planner-revision:"
        f"{_clean_token(revision_input_ref.get('request_id'))}:"
        f"{_clean_token(revision_input_ref.get('component_id'))}:"
        f"{_digest_json(_dedupe_payload(revision_base))[:16]}"
    )
    candidates = _normalize_amendment_candidates(
        result.get("amendment_candidates"),
        revision_id=revision_id,
        revision_input=revision_input_ref,
    )
    revision_without_digest = {
        **revision_base,
        "revision_id": revision_id,
        "amendment_candidates": candidates,
        "amendment_candidate_refs": [
            {
                "candidate_id": candidate.get("candidate_id"),
                "operation_kind": candidate.get("operation_kind"),
                "amendment_record_id": _safe_mapping(
                    candidate.get("contract_amendment_record")
                ).get("amendment_record_id"),
                "amendment_record_digest": _safe_mapping(
                    candidate.get("contract_amendment_record")
                ).get("record_digest"),
                "passive": True,
                "proposal_only": True,
            }
            for candidate in candidates
        ],
    }
    revision_digest = _digest_json(_revision_digest_payload(revision_without_digest))
    planner_revision = {
        **revision_without_digest,
        "revision_digest": revision_digest,
    }
    return {
        "schema_version": SEARCH_PLANNER_REVISION_OBSERVATION_SCHEMA_VERSION,
        "revision_input": revision_input_ref,
        "planner_revision": planner_revision,
    }


def build_search_planner_revision_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    current_search_planner_proposal_state: Mapping[str, Any] | None = None,
    current_scout_disambiguation_report_state: Mapping[str, Any] | None = None,
    current_parent_initial_contract: Mapping[str, Any] | None = None,
    current_parent_current_contract: Mapping[str, Any] | None = None,
    existing_revision_history: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Validate one planner revision observation for RunKernel state."""

    clean_action_id = _required_token(
        action_id,
        "planner revision reduction requires action_id",
        limit=200,
    )
    clean_run_id = _required_token(run_id, "planner revision reduction requires run_id")
    clean_request_id = _required_token(
        request_id,
        "planner revision reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    raw_payload = _required_mapping(
        observation_payload,
        "planner revision observation payload",
    )
    payload_shell = {
        key: raw_payload[key]
        for key in raw_payload
        if key != "planner_revision"
    }
    payload = _safe_mapping(payload_shell)
    revision_input = _safe_mapping(payload.get("revision_input"))
    revision = _safe_planner_revision_payload(raw_payload.get("planner_revision"))
    if payload.get("schema_version") != SEARCH_PLANNER_REVISION_OBSERVATION_SCHEMA_VERSION:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision observation schema version does not match"
        )
    if not revision_input or not revision:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision observation requires revision_input and planner_revision"
        )
    _reject_forbidden_surface_claims(
        raw_payload,
        context="planner revision observation",
    )
    _validate_action_inputs(inputs)

    if revision_input.get("run_id") != clean_run_id or revision.get("run_id") != clean_run_id:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision run_id does not match the run"
        )
    if (
        revision_input.get("request_id") != clean_request_id
        or revision.get("request_id") != clean_request_id
    ):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision request_id does not match the request"
        )
    if revision.get("authorized_action_id") != clean_action_id:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision action_id binding does not match authorization"
        )
    if revision_input.get("schema_version") != SEARCH_PLANNER_REVISION_SCHEMA_VERSION:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision input schema version does not match"
        )
    if revision.get("schema_version") != SEARCH_PLANNER_REVISION_PROPOSAL_SCHEMA_VERSION:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision proposal schema version does not match"
        )
    if revision.get("owner") != SEARCH_PLANNER_REVISION_OWNER:
        raise SearchPlannerRevisionRuntimeError("planner revision owner does not match")

    declared_digest = _clean_token(revision.get("revision_digest"), limit=128)
    if not declared_digest:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision requires revision_digest"
        )
    recomputed_digest = _digest_json(_revision_digest_payload(revision))
    if declared_digest != recomputed_digest:
        raise SearchPlannerRevisionRuntimeError(
            "stale planner revision: revision digest does not match payload content"
        )

    parent_planner_ref = _planner_ref_or_raise(
        revision.get("parent_search_planner_proposal_ref")
    )
    input_parent_planner_ref = _planner_ref_or_raise(
        revision_input.get("parent_search_planner_proposal_ref")
    )
    if parent_planner_ref != input_parent_planner_ref:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision parent planner ref does not match input"
        )
    current_parent_ref = planner_ref_from_search_planner_state(
        current_search_planner_proposal_state
    )
    if parent_planner_ref != current_parent_ref:
        raise SearchPlannerRevisionRuntimeError(
            "stale parent planner digest: planner revision does not match current planner proposal"
        )
    _validate_action_parent_planner_bindings(
        action_inputs=inputs,
        parent_planner_ref=parent_planner_ref,
    )

    parent_scout_ref = _scout_ref_or_raise(
        revision.get("parent_scout_disambiguation_report_ref")
    )
    input_parent_scout_ref = _scout_ref_or_raise(
        revision_input.get("parent_scout_disambiguation_report_ref")
    )
    if parent_scout_ref != input_parent_scout_ref:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision parent Scout ref does not match input"
        )
    current_scout_ref = scout_ref_from_scout_report_state(
        current_scout_disambiguation_report_state
    )
    if parent_scout_ref != current_scout_ref:
        raise SearchPlannerRevisionRuntimeError(
            "stale Scout report digest: planner revision does not match current Scout report"
        )
    _validate_action_parent_scout_bindings(
        action_inputs=inputs,
        parent_scout_ref=parent_scout_ref,
    )
    if _safe_mapping(parent_scout_ref.get("parent_search_planner_proposal_ref")) != parent_planner_ref:
        raise SearchPlannerRevisionRuntimeError(
            "Scout report is not bound to the current parent planner/QMR"
        )

    component_id = _clean_token(revision.get("component_id"))
    if not component_id or component_id != _clean_token(revision_input.get("component_id")):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision component_id does not match input"
        )
    if component_id != parent_scout_ref.get("component_id"):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision component_id does not match Scout report"
        )
    qmr = _safe_mapping(
        _safe_mapping(current_search_planner_proposal_state).get(
            "question_meaning_record"
        )
    )
    component = _component_from_qmr(qmr, component_id=component_id)
    if not component:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision component_id is not present in parent QMR"
        )
    _validate_parent_contract_bindings(
        action_inputs=inputs,
        revision_input=revision_input,
        revision=revision,
        current_parent_initial_contract=current_parent_initial_contract,
        current_parent_current_contract=current_parent_current_contract,
    )

    scout_report = _safe_mapping(current_scout_disambiguation_report_state)
    consumed_dimensions = _text_list(revision.get("consumed_ambiguity_dimension_ids"))
    consumed_hints = _text_list(revision.get("consumed_scout_hint_ids"))
    _validate_consumed_scout_refs(
        consumed_dimension_ids=consumed_dimensions,
        consumed_hint_ids=consumed_hints,
        scout_report=scout_report,
        action_inputs=inputs,
    )
    _validate_scout_directional_context(
        revision_input.get("scout_directional_context"),
        parent_scout_ref=parent_scout_ref,
        component_id=component_id,
        consumed_dimension_ids=consumed_dimensions,
        consumed_hint_ids=consumed_hints,
        scout_report=scout_report,
    )
    _validate_closed_revision_flags(revision)
    amendment_candidates = _safe_amendment_candidates(
        revision.get("amendment_candidates")
    )
    _validate_revision_amendment_candidates(
        amendment_candidates,
        revision_id=str(revision.get("revision_id") or ""),
        parent_planner_ref=parent_planner_ref,
        parent_scout_ref=parent_scout_ref,
        consumed_dimension_ids=consumed_dimensions,
        consumed_hint_ids=consumed_hints,
    )
    requirement_updates = _safe_list(
        revision.get("component_search_requirement_updates")
    )
    revision_effect_class = (
        "contractual_pending_admission"
        if amendment_candidates
        else "query_direction_only_non_contractual"
        if requirement_updates
        else "no_planning_effect"
    )

    dedupe_key = _dedupe_key(revision)
    for item in existing_revision_history:
        if _safe_mapping(item).get("dedupe_key") == dedupe_key:
            raise SearchPlannerRevisionRuntimeError(
                "duplicate search planner revision for the same Scout/planner context"
            )

    state = {
        "schema_version": SEARCH_PLANNER_REVISION_PROPOSAL_SCHEMA_VERSION,
        "trace_key": SEARCH_PLANNER_REVISION_TRACE_KEY,
        "owner": SEARCH_PLANNER_REVISION_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "revision_id": revision.get("revision_id"),
        "revision_digest": declared_digest,
        "dedupe_key": dedupe_key,
        "parent_search_planner_proposal_ref": parent_planner_ref,
        "parent_scout_disambiguation_report_ref": parent_scout_ref,
        "parent_initial_contract_ref": _contract_ref_or_empty(
            revision.get("parent_initial_contract_ref")
        ),
        "parent_current_contract_ref": _contract_ref_or_empty(
            revision.get("parent_current_contract_ref")
        ),
        "component_id": component_id,
        "consumed_ambiguity_dimension_ids": consumed_dimensions,
        "consumed_scout_hint_ids": consumed_hints,
        "revised_question_meaning_summary": revision.get(
            "revised_question_meaning_summary"
        ),
        "revised_question_meaning_record": _safe_mapping(
            revision.get("revised_question_meaning_record")
        ),
        "semantic_slot_updates": _safe_list(revision.get("semantic_slot_updates")),
        "answer_component_updates": _safe_list(
            revision.get("answer_component_updates")
        ),
        "component_search_requirement_updates": requirement_updates,
        "revised_source_obligation_candidates": _safe_list(
            revision.get("revised_source_obligation_candidates")
        ),
        "source_obligation_focus_updates": _safe_list(
            revision.get("source_obligation_focus_updates")
        ),
        "mandatory_caveats": _text_list(revision.get("mandatory_caveats"), limit=360),
        "prohibited_upgrades": _text_list(
            revision.get("prohibited_upgrades"),
            limit=260,
        ),
        "normalization_obligations": _text_list(
            revision.get("normalization_obligations"),
            limit=260,
        ),
        "assumptions": _text_list(revision.get("assumptions"), limit=260),
        "unresolved_ambiguities": _safe_list(revision.get("unresolved_ambiguities")),
        "amendment_candidates": amendment_candidates,
        "amendment_candidate_refs": _safe_list(
            revision.get("amendment_candidate_refs")
        ),
        "planner_revision_metadata": _safe_mapping(
            revision.get("planner_revision_metadata")
        ),
        "closed_surface_flags": dict(_REQUIRED_FALSE_FLAGS),
        "retention_flags": _safe_mapping(revision.get("retention_flags")),
        "search_planner_revision_runtime_activated": True,
        "planner_revision_reduced": True,
        "revision_proposes_only": True,
        **_REQUIRED_FALSE_FLAGS,
        "revision_effect_class": revision_effect_class,
        "contractual_effect_admitted_and_applied": False,
        "contractual_revision_blocks_planning": bool(amendment_candidates),
        "query_direction_authorized_for_planning": bool(
            requirement_updates and not amendment_candidates
        ),
        "answer_contract_mutated": False,
    }
    state_shell = {
        key: value for key, value in state.items() if key != "amendment_candidates"
    }
    safe_state = _safe_mapping(state_shell)
    safe_state["amendment_candidates"] = amendment_candidates
    return safe_state


def build_search_planner_revision_projection(
    *,
    revision_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project planner revision state without raw/private data."""

    state = _safe_mapping(
        {
            key: value
            for key, value in revision_state.items()
            if key != "amendment_candidates"
        }
        if isinstance(revision_state, Mapping)
        else revision_state
    )
    amendment_candidates = _safe_amendment_candidates(
        revision_state.get("amendment_candidates")
        if isinstance(revision_state, Mapping)
        else None
    )
    requirement_updates = _safe_list(
        state.get("component_search_requirement_updates")
    )
    revision_effect_class = str(
        state.get("revision_effect_class")
        or (
            "contractual_pending_admission"
            if amendment_candidates
            else "query_direction_only_non_contractual"
            if requirement_updates
            else "no_planning_effect"
        )
    )
    return {
        "owner": SEARCH_PLANNER_REVISION_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": SEARCH_PLANNER_REVISION_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "revision_id": state.get("revision_id"),
        "revision_digest": state.get("revision_digest"),
        "dedupe_key": state.get("dedupe_key"),
        "parent_search_planner_proposal_ref": _safe_mapping(
            state.get("parent_search_planner_proposal_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            state.get("parent_scout_disambiguation_report_ref")
        ),
        "parent_initial_contract_ref": _safe_mapping(
            state.get("parent_initial_contract_ref")
        ),
        "parent_current_contract_ref": _safe_mapping(
            state.get("parent_current_contract_ref")
        ),
        "component_id": state.get("component_id"),
        "consumed_ambiguity_dimension_ids": _text_list(
            state.get("consumed_ambiguity_dimension_ids")
        ),
        "consumed_scout_hint_ids": _text_list(state.get("consumed_scout_hint_ids")),
        "revised_question_meaning_summary": state.get(
            "revised_question_meaning_summary"
        ),
        "semantic_slot_updates": _safe_list(state.get("semantic_slot_updates")),
        "answer_component_updates": _safe_list(state.get("answer_component_updates")),
        "component_search_requirement_updates": requirement_updates,
        "revised_source_obligation_candidates": _safe_list(
            state.get("revised_source_obligation_candidates")
        ),
        "source_obligation_focus_updates": _safe_list(
            state.get("source_obligation_focus_updates")
        ),
        "mandatory_caveats": _text_list(state.get("mandatory_caveats"), limit=360),
        "prohibited_upgrades": _text_list(
            state.get("prohibited_upgrades"),
            limit=260,
        ),
        "normalization_obligations": _text_list(
            state.get("normalization_obligations"),
            limit=260,
        ),
        "assumptions": _text_list(state.get("assumptions"), limit=260),
        "unresolved_ambiguities": _safe_list(state.get("unresolved_ambiguities")),
        "amendment_candidates": amendment_candidates,
        "amendment_candidate_refs": _safe_list(state.get("amendment_candidate_refs")),
        "planner_revision_metadata": _safe_mapping(
            state.get("planner_revision_metadata")
        ),
        "closed_surface_flags": dict(_REQUIRED_FALSE_FLAGS),
        "retention_flags": _safe_mapping(state.get("retention_flags")),
        "search_planner_revision_runtime_activated": True,
        "planner_revision_reduced": True,
        "revision_proposes_only": True,
        **_REQUIRED_FALSE_FLAGS,
        "revision_effect_class": revision_effect_class,
        "contractual_effect_admitted_and_applied": False,
        "contractual_revision_blocks_planning": bool(amendment_candidates),
        "query_direction_authorized_for_planning": bool(
            requirement_updates and not amendment_candidates
        ),
        "answer_contract_mutated": False,
    }


def revision_ref_from_revision_state(
    revision_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = _safe_mapping(revision_state)
    revision_id = _clean_token(state.get("revision_id"))
    revision_digest = _clean_token(state.get("revision_digest"), limit=128)
    if not revision_id or not revision_digest:
        return {}
    return {
        "revision_id": revision_id,
        "revision_digest": revision_digest,
        "schema_version": _clean_token(state.get("schema_version")),
        "component_id": _clean_token(state.get("component_id")),
        "parent_search_planner_proposal_ref": _safe_mapping(
            state.get("parent_search_planner_proposal_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            state.get("parent_scout_disambiguation_report_ref")
        ),
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


def build_scout_directional_context(
    *,
    scout_report: Mapping[str, Any],
    parent_scout_disambiguation_report_ref: Mapping[str, Any],
    component_id: str,
    consumed_ambiguity_dimension_ids: Sequence[str],
    consumed_scout_hint_ids: Sequence[str],
) -> dict[str, Any]:
    """Build bounded non-evidence direction tied to one stored Scout report."""

    return _build_scout_directional_context(
        scout_report=_safe_mapping(scout_report),
        parent_scout_ref=_scout_ref_or_raise(parent_scout_disambiguation_report_ref),
        component_id=_required_token(component_id, "planner revision requires component_id"),
        consumed_dimension_ids=_text_list(consumed_ambiguity_dimension_ids),
        consumed_hint_ids=_text_list(consumed_scout_hint_ids),
        require_context=True,
    )
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


def _normalize_amendment_candidates(
    value: Any,
    *,
    revision_id: str,
    revision_input: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, item in enumerate(_safe_list(value), start=1):
        mapping = _required_mapping(item, "amendment candidate")
        operation_kind = _normalize_operation_kind(
            mapping.get("operation_kind") or "add_caveat"
        )
        if operation_kind in _FORBIDDEN_OPERATION_KINDS:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision cannot emit forbidden amendment operation: "
                + operation_kind
            )
        if operation_kind not in _ALLOWED_OPERATION_KINDS:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision emitted unsupported amendment operation: "
                + operation_kind
            )
        record = _build_amendment_record(
            candidate=mapping,
            candidate_index=index,
            operation_kind=operation_kind,
            revision_id=revision_id,
            revision_input=revision_input,
        )
        record_payload = record.to_dict()
        lineage = _search_planner_revision_lineage(
            revision_id=revision_id,
            revision_input=revision_input,
        )
        candidate_payload = {
            "candidate_id": mapping.get("candidate_id")
            or record_payload.get("amendment_record_id"),
            "operation_kind": operation_kind,
            "planner_revision_id": revision_id,
            "parent_search_planner_proposal_ref": _safe_mapping(
                revision_input.get("parent_search_planner_proposal_ref")
            ),
            "parent_scout_disambiguation_report_ref": _safe_mapping(
                revision_input.get("parent_scout_disambiguation_report_ref")
            ),
            "consumed_ambiguity_dimension_ids": _text_list(
                revision_input.get("consumed_ambiguity_dimension_ids")
            ),
            "consumed_scout_hint_ids": _text_list(
                revision_input.get("consumed_scout_hint_ids")
            ),
            "contract_amendment_record": record_payload,
            "search_planner_revision_lineage": lineage,
            "passive": True,
            "proposal_only": True,
            "admission_required": True,
            **_REQUIRED_FALSE_FLAGS,
        }
        candidate_shell = {
            key: value
            for key, value in candidate_payload.items()
            if key != "contract_amendment_record"
        }
        safe_candidate = _safe_mapping(candidate_shell)
        safe_candidate["contract_amendment_record"] = record_payload
        candidates.append(safe_candidate)
    return candidates


def _build_amendment_record(
    *,
    candidate: Mapping[str, Any],
    candidate_index: int,
    operation_kind: str,
    revision_id: str,
    revision_input: Mapping[str, Any],
) -> ContractAmendmentRecord:
    parent_contract_ref = _contract_ref_or_empty(
        revision_input.get("parent_initial_contract_ref")
    )
    parent_version = _required_token(
        parent_contract_ref.get("contract_version"),
        "planner revision amendment requires parent initial contract version",
    )
    parent_digest = _required_token(
        parent_contract_ref.get("contract_digest"),
        "planner revision amendment requires parent initial contract digest",
        limit=128,
    )
    parent_planner_ref = _planner_ref_or_raise(
        revision_input.get("parent_search_planner_proposal_ref")
    )
    component_id = _required_token(
        candidate.get("component_id") or revision_input.get("component_id"),
        "planner revision amendment requires component_id",
    )
    caveats = _text_list(
        candidate.get("required_caveats")
        or candidate.get("mandatory_caveats")
        or candidate.get("caveats")
        or candidate.get("caveat"),
        limit=360,
    )
    if operation_kind == "add_caveat" and not caveats:
        raise SearchPlannerRevisionRuntimeError(
            "add_caveat amendment candidate requires a caveat"
        )
    operation_payload = {
        "normalized_operation_kind": operation_kind,
        "component_id": component_id,
        "target_component_ids": [component_id],
        "caveats": caveats,
        "required_caveats": caveats,
        "source": SEARCH_PLANNER_REVISION_OWNER,
        "search_planner_revision_lineage": _search_planner_revision_lineage(
            revision_id=revision_id,
            revision_input=revision_input,
        ),
        **_REQUIRED_FALSE_FLAGS,
    }
    operation = AmendmentOperation(
        operation_id=_clean_token(candidate.get("operation_id"))
        or f"operation:search-planner-revision:{candidate_index}",
        operation_kind=AmendmentOperationKind.ADD_CAVEAT
        if operation_kind == "add_caveat"
        else AmendmentOperationKind.STRENGTHEN_SOURCE_OBLIGATION,
        operation_payload=operation_payload,
        notes=tuple(_text_list(candidate.get("notes"), limit=360)),
        metadata={
            "search_planner_revision_lineage": _search_planner_revision_lineage(
                revision_id=revision_id,
                revision_input=revision_input,
            ),
            **_REQUIRED_FALSE_FLAGS,
        },
    )
    lineage = _search_planner_revision_lineage(
        revision_id=revision_id,
        revision_input=revision_input,
    )
    component_ref = _component_ref_from_revision_context(
        component_id=component_id,
        revision_input=revision_input,
    )
    affected_refs = (
        (
            AffectedComponentRef(
                component_id=component_ref["component_id"],
                component_revision=component_ref["component_revision"],
                component_digest=component_ref["component_digest"],
                relationship="caveat_target_component",
            ),
        )
        if component_ref
        else ()
    )
    amendment_id = (
        _clean_token(candidate.get("amendment_record_id"))
        or _clean_token(candidate.get("candidate_id"))
        or (
            "contract-amendment:search-planner-revision:"
            f"{_clean_token(revision_input.get('request_id'))}:"
            f"{component_id}:{candidate_index}"
        )
    )
    return ContractAmendmentRecord(
        amendment_record_id=amendment_id,
        run_id=str(revision_input.get("run_id") or ""),
        request_id=str(revision_input.get("request_id") or ""),
        request_digest=_request_digest_from_revision_context(revision_input),
        parent_contract_version=parent_version,
        parent_contract_digest=parent_digest,
        parent_question_meaning_record_id=parent_planner_ref.get(
            "question_meaning_record_id"
        ),
        parent_question_meaning_record_digest=parent_planner_ref.get(
            "question_meaning_record_digest"
        ),
        accepted_contract_ref=f"contract:{parent_version}:accepted",
        trigger_refs=AmendmentTriggerRefs(
            currentness_refs=(
                str(
                    _safe_mapping(
                        revision_input.get("parent_scout_disambiguation_report_ref")
                    ).get("report_id")
                    or "scout_disambiguation_report"
                ),
            ),
            metadata={
                "search_planner_revision_lineage": lineage,
                "scout_hints_are_evidence": False,
                "citation_eligible": False,
                "source_obligation_satisfied": False,
            },
        ),
        affected_component_refs=affected_refs,
        operations=(operation,),
        materiality=MaterialityPosture.NON_MATERIAL,
        user_confirmation_posture=UserConfirmationPosture.NOT_REQUIRED,
        monotonicity=MonotonicityPosture.STRENGTHENS,
        weakening_posture=WeakeningPosture.NONE,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE,
        required_caveats=tuple(caveats),
        lineage=AmendmentLineage(
            created_by=SEARCH_PLANNER_REVISION_OWNER,
            created_from=(
                "search_planner_revision",
                "scout_disambiguation_report",
                "search_planner_proposal",
            ),
            parent_record_digest=str(
                _safe_mapping(
                    revision_input.get("parent_scout_disambiguation_report_ref")
                ).get("report_digest")
                or ""
            ),
        ),
        metadata={
            "search_planner_revision_lineage": lineage,
            "proposal_only": True,
            **_REQUIRED_FALSE_FLAGS,
        },
        schema_version=CONTRACT_AMENDMENT_RECORD_SCHEMA_VERSION,
    ).require_valid()


def _component_ref_from_revision_context(
    *,
    component_id: str,
    revision_input: Mapping[str, Any],
) -> dict[str, Any]:
    context = _safe_mapping(revision_input.get("safe_revision_context"))
    for key in ("parent_question_meaning_record", "question_meaning_record"):
        qmr = _safe_mapping(context.get(key))
        for item in _safe_list(qmr.get("answer_components")):
            mapping = _safe_mapping(item)
            if mapping.get("component_id") != component_id:
                continue
            component_revision = _clean_token(mapping.get("component_revision"))
            component_digest = _clean_token(mapping.get("component_digest"), limit=128)
            if component_revision and component_digest:
                return {
                    "component_id": component_id,
                    "component_revision": component_revision,
                    "component_digest": component_digest,
                }
    component_ref = _safe_mapping(context.get("answer_component_ref"))
    if component_ref.get("component_id") == component_id:
        component_revision = _clean_token(component_ref.get("component_revision"))
        component_digest = _clean_token(component_ref.get("component_digest"), limit=128)
        if component_revision and component_digest:
            return {
                "component_id": component_id,
                "component_revision": component_revision,
                "component_digest": component_digest,
            }
    return {}


def _request_digest_from_revision_context(revision_input: Mapping[str, Any]) -> str:
    context = _safe_mapping(revision_input.get("safe_revision_context"))
    for key in ("parent_question_meaning_record", "question_meaning_record"):
        qmr = _safe_mapping(context.get(key))
        digest = _clean_token(qmr.get("request_digest"), limit=128)
        if digest:
            return digest
    user_query_ref = _safe_mapping(context.get("user_query_ref"))
    digest = _clean_token(user_query_ref.get("digest"), limit=128)
    if digest:
        return digest
    raise SearchPlannerRevisionRuntimeError(
        "planner revision amendment requires parent request digest"
    )


def _search_planner_revision_lineage(
    *,
    revision_id: str,
    revision_input: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "origin": "search_planner_revision",
        "planner_revision_id": revision_id,
        "planner_revision_digest_status": "not_filled_until_revision_reduction",
        "parent_search_planner_proposal_ref": _safe_mapping(
            revision_input.get("parent_search_planner_proposal_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            revision_input.get("parent_scout_disambiguation_report_ref")
        ),
        "component_id": revision_input.get("component_id"),
        "consumed_ambiguity_dimension_ids": _text_list(
            revision_input.get("consumed_ambiguity_dimension_ids")
        ),
        "consumed_scout_hint_ids": _text_list(
            revision_input.get("consumed_scout_hint_ids")
        ),
        "scout_hints_are_evidence": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "evidence_admitted": False,
        "contract_mutation_applied": False,
    }


def _validate_required_adapter_fields(result: Mapping[str, Any]) -> None:
    required = (
        "revised_question_meaning_summary",
        "mandatory_caveats",
        "prohibited_upgrades",
        "normalization_obligations",
        "assumptions",
        "unresolved_ambiguities",
        "consumed_ambiguity_dimension_ids",
        "consumed_scout_hint_ids",
        "amendment_candidates",
    )
    missing = [field for field in required if field not in result]
    if missing:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision adapter result missing required fields: "
            + ", ".join(missing)
        )


def _validate_revision_amendment_candidates(
    candidates: Sequence[Any],
    *,
    revision_id: str,
    parent_planner_ref: Mapping[str, Any],
    parent_scout_ref: Mapping[str, Any],
    consumed_dimension_ids: Sequence[str],
    consumed_hint_ids: Sequence[str],
) -> None:
    for item in candidates:
        candidate = _required_mapping(item, "planner revision amendment candidate")
        if candidate.get("passive") is not True or candidate.get("proposal_only") is not True:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision amendment candidate must remain passive/proposal-only"
            )
        for key, expected in _REQUIRED_FALSE_FLAGS.items():
            if candidate.get(key) is not expected:
                raise SearchPlannerRevisionRuntimeError(
                    f"planner revision amendment candidate must keep {key} false"
                )
        if candidate.get("planner_revision_id") != revision_id:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision amendment candidate revision lineage does not match"
            )
        if _safe_mapping(candidate.get("parent_search_planner_proposal_ref")) != _safe_mapping(parent_planner_ref):
            raise SearchPlannerRevisionRuntimeError(
                "planner revision amendment candidate parent planner lineage does not match"
            )
        if _safe_mapping(candidate.get("parent_scout_disambiguation_report_ref")) != _safe_mapping(parent_scout_ref):
            raise SearchPlannerRevisionRuntimeError(
                "planner revision amendment candidate Scout lineage does not match"
            )
        if _text_list(candidate.get("consumed_ambiguity_dimension_ids")) != list(consumed_dimension_ids):
            raise SearchPlannerRevisionRuntimeError(
                "planner revision amendment candidate consumed dimensions do not match"
            )
        if _text_list(candidate.get("consumed_scout_hint_ids")) != list(consumed_hint_ids):
            raise SearchPlannerRevisionRuntimeError(
                "planner revision amendment candidate consumed Scout hints do not match"
            )
        record = _safe_mapping(candidate.get("contract_amendment_record"))
        if record.get("passive") is not True or record.get("canonical_state") is True:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision amendment record must remain passive"
            )
        operations = _safe_list(record.get("operations"))
        if not operations:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision amendment record requires operations"
            )
        for operation in operations:
            mapping = _safe_mapping(operation)
            operation_kind = _normalize_operation_kind(
                mapping.get("operation_kind")
                or _safe_mapping(mapping.get("operation_payload")).get(
                    "normalized_operation_kind"
                )
            )
            normalized_payload_kind = _normalize_operation_kind(
                _safe_mapping(mapping.get("operation_payload")).get(
                    "normalized_operation_kind"
                )
            )
            if operation_kind in _FORBIDDEN_OPERATION_KINDS or normalized_payload_kind in _FORBIDDEN_OPERATION_KINDS:
                raise SearchPlannerRevisionRuntimeError(
                    "planner revision amendment cannot resolve slots or satisfy requirements"
                )
            if operation_kind not in _ALLOWED_OPERATION_KINDS:
                raise SearchPlannerRevisionRuntimeError(
                    "planner revision amendment operation is unsupported"
                )


def _validate_action_inputs(inputs: Mapping[str, Any]) -> None:
    missing = [
        key
        for key in _REQUIRED_ACTION_INPUT_KEYS
        if key not in inputs or inputs.get(key) in (None, "")
    ]
    if missing:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision action missing required bindings: " + ", ".join(missing)
        )
    if inputs.get("revision_schema_version") != SEARCH_PLANNER_REVISION_SCHEMA_VERSION:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision action binds the wrong schema version"
        )


def _validate_action_parent_planner_bindings(
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
            raise SearchPlannerRevisionRuntimeError(
                "planner revision action parent planner binding is stale"
            )


def _validate_action_parent_scout_bindings(
    *,
    action_inputs: Mapping[str, Any],
    parent_scout_ref: Mapping[str, Any],
) -> None:
    expected = {
        "parent_scout_disambiguation_report_id": parent_scout_ref.get("report_id"),
        "parent_scout_disambiguation_report_digest": parent_scout_ref.get(
            "report_digest"
        ),
    }
    for key, value in expected.items():
        if action_inputs.get(key) != value:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision action Scout report binding is stale"
            )


def _normalize_scout_directional_context(
    value: Any,
    *,
    parent_scout_ref: Mapping[str, Any],
    component_id: str,
    consumed_dimension_ids: Sequence[str],
    consumed_hint_ids: Sequence[str],
) -> dict[str, Any]:
    context = _safe_mapping(value)
    if not context:
        return {}
    _reject_forbidden_surface_claims(
        context,
        context="planner revision Scout directional context",
    )
    if context.get("schema_version") != SCOUT_DIRECTIONAL_CONTEXT_SCHEMA_VERSION:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision Scout directional context has the wrong schema"
        )
    if _scout_ref_or_raise(context.get("parent_scout_disambiguation_report_ref")) != dict(parent_scout_ref):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision Scout directional context has stale parent lineage"
        )
    if _clean_token(context.get("component_id")) != component_id:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision Scout directional context has the wrong component"
        )
    if _text_list(context.get("consumed_ambiguity_dimension_ids")) != list(consumed_dimension_ids):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision Scout directional context has stale dimensions"
        )
    if _text_list(context.get("consumed_scout_hint_ids")) != list(consumed_hint_ids):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision Scout directional context has stale hint ids"
        )
    directional_hints = [
        _normalize_directional_hint(item, strict_keys=True)
        for item in _safe_list(context.get("directional_hints"))
    ]
    if len(directional_hints) != len(consumed_hint_ids) or len(directional_hints) > SCOUT_DIRECTIONAL_CONTEXT_MAX_HINTS:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision Scout directional context exceeds its bounded shape"
        )
    if [item["hint_id"] for item in directional_hints] != list(consumed_hint_ids):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision Scout directional context has stale hint material"
        )
    if context.get("non_evidence") is not True:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision Scout directional context must remain non-evidence"
        )
    for key in (
        "scout_hints_are_evidence",
        "evidence_admitted",
        "citation_eligible",
        "source_obligation_satisfied",
    ):
        if context.get(key) is not False:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision Scout directional context opens authority"
            )
    return {
        "schema_version": SCOUT_DIRECTIONAL_CONTEXT_SCHEMA_VERSION,
        "parent_scout_disambiguation_report_ref": dict(parent_scout_ref),
        "component_id": component_id,
        "consumed_ambiguity_dimension_ids": list(consumed_dimension_ids),
        "consumed_scout_hint_ids": list(consumed_hint_ids),
        "directional_hints": directional_hints,
        "non_evidence": True,
        "scout_hints_are_evidence": False,
        "evidence_admitted": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
    }

def _build_scout_directional_context(
    *,
    scout_report: Mapping[str, Any],
    parent_scout_ref: Mapping[str, Any],
    component_id: str,
    consumed_dimension_ids: Sequence[str],
    consumed_hint_ids: Sequence[str],
    require_context: bool,
) -> dict[str, Any]:
    report_ref = scout_ref_from_scout_report_state(scout_report)
    if report_ref != dict(parent_scout_ref):
        raise SearchPlannerRevisionRuntimeError(
            "Scout directional context is stale against its parent report"
        )
    if _clean_token(scout_report.get("component_id")) != component_id:
        raise SearchPlannerRevisionRuntimeError(
            "Scout directional context component does not match its report"
        )
    if not consumed_dimension_ids:
        raise SearchPlannerRevisionRuntimeError(
            "Scout directional context requires consumed ambiguity dimensions"
        )
    if require_context and not consumed_hint_ids:
        raise SearchPlannerRevisionRuntimeError(
            "Scout directional context requires consumed hints"
        )
    if len(consumed_hint_ids) > SCOUT_DIRECTIONAL_CONTEXT_MAX_HINTS:
        raise SearchPlannerRevisionRuntimeError(
            "Scout directional context exceeds its bounded hint limit"
        )
    dimension_ids = _scout_dimension_ids(scout_report)
    missing_dimensions = [item for item in consumed_dimension_ids if item not in dimension_ids]
    if missing_dimensions:
        raise SearchPlannerRevisionRuntimeError(
            "Scout directional context consumes unknown dimensions: "
            + ", ".join(missing_dimensions)
        )
    hints_by_id = _scout_hints_by_id(scout_report)
    missing_hints = [item for item in consumed_hint_ids if item not in hints_by_id]
    if missing_hints:
        raise SearchPlannerRevisionRuntimeError(
            "Scout directional context consumes unknown hints: "
            + ", ".join(missing_hints)
        )
    directional_hints = [
        _normalize_directional_hint(hints_by_id[hint_id], strict_keys=False)
        for hint_id in consumed_hint_ids
    ]
    return {
        "schema_version": SCOUT_DIRECTIONAL_CONTEXT_SCHEMA_VERSION,
        "parent_scout_disambiguation_report_ref": dict(parent_scout_ref),
        "component_id": component_id,
        "consumed_ambiguity_dimension_ids": list(consumed_dimension_ids),
        "consumed_scout_hint_ids": list(consumed_hint_ids),
        "directional_hints": directional_hints,
        "non_evidence": True,
        "scout_hints_are_evidence": False,
        "evidence_admitted": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
    }


def _validate_consumed_scout_refs(
    *,
    consumed_dimension_ids: Sequence[str],
    consumed_hint_ids: Sequence[str],
    scout_report: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> None:
    if _text_list(action_inputs.get("consumed_ambiguity_dimension_ids")) != list(
        consumed_dimension_ids
    ):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision action consumed dimensions do not match revision"
        )
    if _text_list(action_inputs.get("consumed_scout_hint_ids")) != list(
        consumed_hint_ids
    ):
        raise SearchPlannerRevisionRuntimeError(
            "planner revision action consumed Scout hints do not match revision"
        )
    dimension_ids = {
        str(item.get("dimension_id"))
        for item in _safe_list(scout_report.get("ambiguity_dimensions"))
        if isinstance(item, Mapping) and item.get("dimension_id")
    }
    missing_dimensions = [item for item in consumed_dimension_ids if item not in dimension_ids]
    if missing_dimensions:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision consumes unknown Scout dimensions: "
            + ", ".join(missing_dimensions)
        )
    hint_ids = _collect_scout_hint_ids(scout_report)
    missing_hints = [item for item in consumed_hint_ids if item not in hint_ids]
    if missing_hints:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision consumes unknown Scout hints: "
            + ", ".join(missing_hints)
        )


def _collect_scout_hint_ids(scout_report: Mapping[str, Any]) -> set[str]:
    hint_ids: set[str] = set()
    for key in (
        "scout_result_hints",
        "likely_official_target_hints",
        "currentness_hints",
    ):
        for item in _safe_list(scout_report.get(key)):
            if isinstance(item, Mapping):
                hint_id = _clean_token(item.get("hint_id"))
                if hint_id:
                    hint_ids.add(hint_id)
    for item in _safe_list(scout_report.get("candidate_interpretations")):
        if isinstance(item, Mapping):
            hint_ids.update(_text_list(item.get("supporting_hint_ids")))
    return hint_ids


def _scout_dimension_ids(scout_report: Mapping[str, Any]) -> set[str]:
    return {
        str(item.get("dimension_id"))
        for item in _safe_list(scout_report.get("ambiguity_dimensions"))
        if isinstance(item, Mapping) and item.get("dimension_id")
    }

def _scout_hints_by_id(scout_report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    hints: dict[str, Mapping[str, Any]] = {}
    for key in (
        "scout_result_hints",
        "likely_official_target_hints",
        "currentness_hints",
    ):
        for item in _safe_list(scout_report.get(key)):
            if not isinstance(item, Mapping):
                continue
            hint_id = _clean_token(item.get("hint_id"))
            if hint_id and hint_id not in hints:
                hints[hint_id] = item
    return hints

def _normalize_directional_hint(
    value: Any,
    *,
    strict_keys: bool,
) -> dict[str, Any]:
    hint = _safe_mapping(value)
    if not hint:
        raise SearchPlannerRevisionRuntimeError(
            "Scout directional context contains an invalid hint"
        )
    _reject_forbidden_surface_claims(
        hint,
        context="planner revision Scout directional hint",
    )
    allowed_keys = {
        "hint_id",
        "query_id",
        "related_dimension_ids",
        "title",
        "domain",
        "hint_kind",
        "official_target_hint",
        "currentness_hint",
        "interpretation_hint",
        "confidence_posture",
    }
    if strict_keys and set(hint) - allowed_keys:
        raise SearchPlannerRevisionRuntimeError(
            "Scout directional context contains fields outside its bounded shape"
        )
    hint_id = _required_token(
        hint.get("hint_id"),
        "Scout directional context hint requires hint_id",
    )
    return {
        "hint_id": hint_id,
        "query_id": _clean_token(hint.get("query_id")),
        "related_dimension_ids": _text_list(hint.get("related_dimension_ids")),
        "title": _clean_token(hint.get("title"), limit=320),
        "domain": _clean_token(hint.get("domain"), limit=240),
        "hint_kind": _clean_token(hint.get("hint_kind")) or "unknown_or_other",
        "official_target_hint": _clean_token(
            hint.get("official_target_hint"),
            limit=420,
        ),
        "currentness_hint": _clean_token(hint.get("currentness_hint"), limit=420),
        "interpretation_hint": _clean_token(
            hint.get("interpretation_hint"),
            limit=420,
        ),
        "confidence_posture": _clean_token(
            hint.get("confidence_posture"),
            limit=120,
        )
        or "hint_only",
    }

def _validate_scout_directional_context(
    value: Any,
    *,
    parent_scout_ref: Mapping[str, Any],
    component_id: str,
    consumed_dimension_ids: Sequence[str],
    consumed_hint_ids: Sequence[str],
    scout_report: Mapping[str, Any],
) -> None:
    context = _normalize_scout_directional_context(
        value,
        parent_scout_ref=parent_scout_ref,
        component_id=component_id,
        consumed_dimension_ids=consumed_dimension_ids,
        consumed_hint_ids=consumed_hint_ids,
    )
    if not context:
        if consumed_hint_ids:
            raise SearchPlannerRevisionRuntimeError(
                "planner revision requires lineage-bound Scout direction"
            )
        return
    expected = _build_scout_directional_context(
        scout_report=scout_report,
        parent_scout_ref=parent_scout_ref,
        component_id=component_id,
        consumed_dimension_ids=consumed_dimension_ids,
        consumed_hint_ids=consumed_hint_ids,
        require_context=True,
    )
    if context != expected:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision Scout directional context is stale or noncanonical"
        )

def _validate_parent_contract_bindings(
    *,
    action_inputs: Mapping[str, Any],
    revision_input: Mapping[str, Any],
    revision: Mapping[str, Any],
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
        input_ref=_safe_mapping(revision_input.get("parent_initial_contract_ref")),
        revision_ref=_safe_mapping(revision.get("parent_initial_contract_ref")),
        expected_ref=expected_initial,
    )
    _validate_one_contract_binding(
        label="parent_current_contract",
        action_version=action_inputs.get("parent_current_contract_version"),
        action_digest=action_inputs.get("parent_current_contract_digest"),
        input_ref=_safe_mapping(revision_input.get("parent_current_contract_ref")),
        revision_ref=_safe_mapping(revision.get("parent_current_contract_ref")),
        expected_ref=expected_current,
    )


def _validate_one_contract_binding(
    *,
    label: str,
    action_version: Any,
    action_digest: Any,
    input_ref: Mapping[str, Any],
    revision_ref: Mapping[str, Any],
    expected_ref: Mapping[str, Any],
) -> None:
    expected_version = _clean_token(expected_ref.get("contract_version"))
    expected_digest = _clean_token(expected_ref.get("contract_digest"), limit=128)
    action_version_text = _clean_token(action_version)
    action_digest_text = _clean_token(action_digest, limit=128)
    input_version = _clean_token(input_ref.get("contract_version"))
    input_digest = _clean_token(input_ref.get("contract_digest"), limit=128)
    revision_version = _clean_token(revision_ref.get("contract_version"))
    revision_digest = _clean_token(revision_ref.get("contract_digest"), limit=128)
    if expected_ref:
        if action_version_text != expected_version or action_digest_text != expected_digest:
            raise SearchPlannerRevisionRuntimeError(
                f"stale parent digest: {label} action binding is not current"
            )
        if input_version != expected_version or input_digest != expected_digest:
            raise SearchPlannerRevisionRuntimeError(
                f"stale parent digest: {label} input is not current"
            )
        if revision_version != expected_version or revision_digest != expected_digest:
            raise SearchPlannerRevisionRuntimeError(
                f"stale parent digest: {label} revision is not current"
            )
        return
    if (
        action_version_text
        or action_digest_text
        or input_version
        or input_digest
        or revision_version
        or revision_digest
    ):
        raise SearchPlannerRevisionRuntimeError(
            f"stale parent digest: {label} was bound but no current parent exists"
        )


def _validate_closed_revision_flags(revision: Mapping[str, Any]) -> None:
    for key, expected in _REQUIRED_FALSE_FLAGS.items():
        value = revision.get(key, False if key in _SAFE_FALSE_RETENTION_KEYS else None)
        if value is not expected:
            raise SearchPlannerRevisionRuntimeError(
                f"planner revision must keep {key} false"
            )
    flags = _safe_mapping(revision.get("closed_surface_flags"))
    for key, expected in _REQUIRED_FALSE_FLAGS.items():
        value = flags.get(key, False if key in _SAFE_FALSE_RETENTION_KEYS else None)
        if value is not expected:
            raise SearchPlannerRevisionRuntimeError(
                f"planner revision closed-surface flag {key} must be false"
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


def _planner_revision_metadata(adapter_result: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _safe_mapping(adapter_result.get("planner_revision_model_metadata"))
    allowed_keys = {
        "planner_revision_model_adapter_schema_version",
        "planner_revision_model_prompt_schema_version",
        "prompt_hash",
        "prompt_length",
        "provider",
        "model",
        "effort",
        "use_reasoning",
        "require_json",
        "raw_prompt_retained",
        "raw_model_response_retained",
        "provider_payload_retained",
        "model_adapter_enabled",
    }
    return {key: metadata[key] for key in allowed_keys if key in metadata}


def _dedupe_key(revision: Mapping[str, Any]) -> str:
    return _digest_json(_dedupe_payload(revision))


def _dedupe_payload(revision: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "parent_search_planner_proposal_ref": _safe_mapping(
            revision.get("parent_search_planner_proposal_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            revision.get("parent_scout_disambiguation_report_ref")
        ),
        "parent_initial_contract_ref": _safe_mapping(
            revision.get("parent_initial_contract_ref")
        ),
        "parent_current_contract_ref": _safe_mapping(
            revision.get("parent_current_contract_ref")
        ),
        "component_id": revision.get("component_id"),
        "consumed_ambiguity_dimension_ids": _text_list(
            revision.get("consumed_ambiguity_dimension_ids")
        ),
        "consumed_scout_hint_ids": _text_list(revision.get("consumed_scout_hint_ids")),
        "action_type": _EXPECTED_ACTION_TYPE,
    }


def _revision_digest_payload(revision: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(revision)
    payload.pop("revision_digest", None)
    payload["amendment_candidates"] = [
        _revision_candidate_digest_payload(candidate)
        for candidate in _safe_list(payload.get("amendment_candidates"))
    ]
    return payload


def _revision_candidate_digest_payload(candidate: Any) -> dict[str, Any]:
    mapping = _safe_mapping(candidate)
    record = _safe_mapping(mapping.get("contract_amendment_record"))
    return {
        "candidate_id": mapping.get("candidate_id"),
        "operation_kind": mapping.get("operation_kind"),
        "planner_revision_id": mapping.get("planner_revision_id"),
        "parent_search_planner_proposal_ref": _safe_mapping(
            mapping.get("parent_search_planner_proposal_ref")
        ),
        "parent_scout_disambiguation_report_ref": _safe_mapping(
            mapping.get("parent_scout_disambiguation_report_ref")
        ),
        "consumed_ambiguity_dimension_ids": _text_list(
            mapping.get("consumed_ambiguity_dimension_ids")
        ),
        "consumed_scout_hint_ids": _text_list(mapping.get("consumed_scout_hint_ids")),
        "amendment_record_id": record.get("amendment_record_id"),
        "amendment_record_digest": record.get("record_digest"),
        "passive": mapping.get("passive"),
        "proposal_only": mapping.get("proposal_only"),
        "admission_required": mapping.get("admission_required"),
        "search_planner_revision_lineage": _safe_mapping(
            mapping.get("search_planner_revision_lineage")
        ),
        "closed_surface_flags": {
            key: mapping.get(key)
            for key in sorted(_REQUIRED_FALSE_FLAGS)
            if key in mapping
        },
    }


def _validate_action_like(
    *,
    action: Any,
    revision_input: SearchPlannerRevisionInput,
) -> None:
    action_type = _enum_or_text(getattr(action, "action_type", None))
    expected_observation_type = _enum_or_text(
        getattr(action, "expected_observation_type", None)
    )
    if action_type != _EXPECTED_ACTION_TYPE:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision action type does not match"
        )
    if expected_observation_type != _EXPECTED_OBSERVATION_TYPE:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision expected observation type does not match"
        )
    inputs = _safe_mapping(getattr(action, "inputs", {}))
    revision_payload = revision_input.to_adapter_payload()
    expected = {
        "run_id": revision_payload.get("run_id"),
        "request_id": revision_payload.get("request_id"),
        "parent_search_planner_proposal_id": _safe_mapping(
            revision_payload.get("parent_search_planner_proposal_ref")
        ).get("proposal_id"),
        "parent_search_planner_proposal_digest": _safe_mapping(
            revision_payload.get("parent_search_planner_proposal_ref")
        ).get("proposal_digest"),
        "parent_question_meaning_record_id": _safe_mapping(
            revision_payload.get("parent_search_planner_proposal_ref")
        ).get("question_meaning_record_id"),
        "parent_question_meaning_record_digest": _safe_mapping(
            revision_payload.get("parent_search_planner_proposal_ref")
        ).get("question_meaning_record_digest"),
        "parent_scout_disambiguation_report_id": _safe_mapping(
            revision_payload.get("parent_scout_disambiguation_report_ref")
        ).get("report_id"),
        "parent_scout_disambiguation_report_digest": _safe_mapping(
            revision_payload.get("parent_scout_disambiguation_report_ref")
        ).get("report_digest"),
        "component_id": revision_payload.get("component_id"),
        "consumed_ambiguity_dimension_ids": _text_list(
            revision_payload.get("consumed_ambiguity_dimension_ids")
        ),
        "consumed_scout_hint_ids": _text_list(
            revision_payload.get("consumed_scout_hint_ids")
        ),
        "revision_schema_version": SEARCH_PLANNER_REVISION_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if inputs.get(key) != value:
            raise SearchPlannerRevisionRuntimeError(
                f"planner revision action binding does not match input: {key}"
            )


def _call_adapter(
    adapter: SearchPlannerRevisionAdapter
    | Callable[[Mapping[str, Any]], Mapping[str, Any]],
    adapter_input: Mapping[str, Any],
) -> Mapping[str, Any]:
    try:
        if hasattr(adapter, "produce"):
            result = adapter.produce(adapter_input)  # type: ignore[union-attr]
        else:
            result = adapter(adapter_input)  # type: ignore[misc]
    except RunCapExceeded:
        raise
    except SearchPlannerRevisionRuntimeError:
        raise
    except Exception as exc:
        raise SearchPlannerRevisionRuntimeError(
            f"search planner revision adapter failed closed: {type(exc).__name__}"
        ) from exc
    if not isinstance(result, Mapping):
        raise SearchPlannerRevisionRuntimeError(
            "search planner revision adapter must return a mapping"
        )
    return result


def _planner_ref_or_raise(value: Any) -> dict[str, Any]:
    ref = _planner_ref_or_empty(value)
    if not ref:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision input requires parent planner proposal and QMR refs"
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


def _scout_ref_or_raise(value: Any) -> dict[str, Any]:
    ref = _scout_ref_or_empty(value)
    if not ref:
        raise SearchPlannerRevisionRuntimeError(
            "planner revision input requires parent Scout report ref"
        )
    return ref


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


def _reject_forbidden_surface_claims(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    sensitive = sorted(key for key in keys if _is_sensitive_key(key))
    if sensitive:
        raise SearchPlannerRevisionRuntimeError(
            f"{context} contains raw/private fields: " + ", ".join(sensitive)
        )
    forbidden = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if forbidden:
        raise SearchPlannerRevisionRuntimeError(
            f"{context} includes closed authority fields: " + ", ".join(forbidden)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SearchPlannerRevisionRuntimeError(
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


def _safe_amendment_candidates(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    candidates: list[dict[str, Any]] = []
    for item in value:
        if hasattr(item, "to_dict"):
            item = item.to_dict()
        if not isinstance(item, Mapping):
            continue
        record_payload = item.get("contract_amendment_record")
        shell = {
            key: item[key]
            for key in item
            if key != "contract_amendment_record"
        }
        candidate = _safe_mapping(shell)
        if hasattr(record_payload, "to_dict"):
            record_payload = record_payload.to_dict()
        if isinstance(record_payload, Mapping):
            candidate["contract_amendment_record"] = dict(record_payload)
        else:
            candidate["contract_amendment_record"] = _safe_mapping(record_payload)
        candidates.append(candidate)
    return candidates


def _safe_planner_revision_payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    shell = {
        key: value[key]
        for key in value
        if key != "amendment_candidates"
    }
    revision = _safe_mapping(shell)
    revision["amendment_candidates"] = _safe_amendment_candidates(
        value.get("amendment_candidates")
    )
    return revision


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
        raise SearchPlannerRevisionRuntimeError(f"{label} must be a mapping")
    return value


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise SearchPlannerRevisionRuntimeError(message)
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


def _normalize_operation_kind(value: Any) -> str:
    return _normalize_key(value)


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _enum_or_text(value: Any) -> str | None:
    if isinstance(value, Enum):
        return str(value.value)
    return _clean_token(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "SCOUT_DIRECTIONAL_CONTEXT_MAX_HINTS",
    "SCOUT_DIRECTIONAL_CONTEXT_SCHEMA_VERSION",
    "SEARCH_PLANNER_REVISION_OBSERVATION_SCHEMA_VERSION",
    "SEARCH_PLANNER_REVISION_OWNER",
    "SEARCH_PLANNER_REVISION_PROPOSAL_SCHEMA_VERSION",
    "SEARCH_PLANNER_REVISION_REASON",
    "SEARCH_PLANNER_REVISION_SCHEMA_VERSION",
    "SEARCH_PLANNER_REVISION_STAGE",
    "SEARCH_PLANNER_REVISION_TRACE_KEY",
    "SearchPlannerRevisionAdapter",
    "SearchPlannerRevisionExecutionResult",
    "SearchPlannerRevisionInput",
    "SearchPlannerRevisionRuntimeError",
    "build_scout_directional_context",
    "build_search_planner_revision_observation_payload",
    "build_search_planner_revision_projection",
    "build_search_planner_revision_state",
    "contract_ref_from_contract",
    "execute_search_planner_revision_action",
    "planner_ref_from_search_planner_state",
    "revision_ref_from_revision_state",
    "scout_ref_from_scout_report_state",
]
