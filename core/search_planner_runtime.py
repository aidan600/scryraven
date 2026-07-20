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

from core.initial_query_allocation_policy import InitialQueryAllocationPolicy
from core.search_work_query_shape_runtime import (
    DeterministicSearchWorkRuntimeInput,
    build_deterministic_search_work_runtime_records,
)
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
SEARCH_PLANNER_MAX_ANSWER_COMPONENTS = 5
SEARCH_PLANNER_SAFE_CONTEXT_MAX_DEPTH = 12
SEARCH_PLANNER_SAFE_CONTEXT_MAX_COLLECTION_ITEMS = 64
SEARCH_PLANNER_SAFE_CONTEXT_TEXT_CHARS = 900
_ADAPTER_ONLY_USER_QUERY_TEXT_KEY = "user_query_text_for_planning"

_ALLOWED_INITIAL_QUERY_ROLES = frozenset(
    {
        "initial",
        "official_bias",
        "canonical_bias",
        "recency",
        "disambiguation",
        "recon_rewrite",
    }
)
_ALLOWED_RECON_POSTURES = frozenset({"not_needed", "optional", "required"})

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

_SAFE_FALSE_RETENTION_KEYS = frozenset(
    {
        "raw_model_response_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
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

    Product composition supplies the selected fast-model adapter. Tests and
    bounded diagnostics may explicitly inject another adapter with this shape.
    """

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return a sanitized planner proposal mapping."""


@dataclass(frozen=True, slots=True)
class DeterministicSearchPlannerAdapter:
    """Explicit validation-only/offline SearchPlanner fixture.

    The adapter reuses the repository's deterministic query-shape assessment
    and emits the same passive proposal shape as an injected model adapter.  It
    never calls a model, provider, search, fetch/read, or environment surface.
    It must be directly injected and is never the ordinary default or a failure
    fallback; its query-shape interpretation is not product semantic authority.
    """

    adapter_version: str = "searchos_deterministic_search_planner_v1"

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        safe_context = _safe_mapping(planner_input.get("safe_context"))
        route_facts = _safe_mapping(safe_context.get("route_facts"))
        run_contract = _safe_mapping(safe_context.get("run_contract_projection"))
        contract_id = _clean_token(run_contract.get("contract_id"))
        query_text = _clean_text(
            planner_input.get(_ADAPTER_ONLY_USER_QUERY_TEXT_KEY),
            limit=SEARCH_PLANNER_FULL_QUERY_TEXT_CHARS,
        )
        if not contract_id or not route_facts or not query_text:
            raise SearchPlannerRuntimeError(
                "deterministic SearchPlanner requires explicit route, run-contract, and query composition"
            )

        records = build_deterministic_search_work_runtime_records(
            DeterministicSearchWorkRuntimeInput(
                contract_id=contract_id,
                run_contract_projection=run_contract,
                route_facts=route_facts,
                requested_mode=_clean_token(planner_input.get("requested_mode")),
                selected_depth=_clean_token(run_contract.get("selected_depth")),
                safe_query_preview=query_text,
                current_date_ref=_clean_text(safe_context.get("current_date")),
                metadata={
                    "owner": self.adapter_version,
                    "provider_free": True,
                },
            )
        )
        assessment = records.query_shape_assessment
        source_kind_by_id = {
            candidate.candidate_id: candidate.kind.value for candidate in assessment.source_obligation_candidates
        }
        localized_obligation_ids = _localized_component_obligation_ids(
            assessment=assessment,
            requested_mode=_clean_token(planner_input.get("requested_mode")),
            selected_depth=_clean_token(run_contract.get("selected_depth")),
            primary_entity=_clean_text(route_facts.get("primary_entity"), limit=220),
        )
        source_candidates = [
            {
                "candidate_id": candidate.candidate_id,
                "obligation_kind": candidate.kind.value,
                "component_candidate_ids": [
                    component.component_id
                    for component in assessment.component_candidates
                    if candidate.candidate_id in localized_obligation_ids.get(component.component_id, ())
                ],
                "strictness": candidate.strictness.value,
                "metadata": {
                    "required_source_class": candidate.required_source_class,
                    "currentness_requirement": candidate.currentness_requirement,
                    "provider_name_neutral": True,
                    "component_binding_posture": ("deterministic_component_local_reproof"),
                },
            }
            for candidate in assessment.source_obligation_candidates
        ]
        current_date = _clean_text(safe_context.get("current_date"), limit=40)
        include_domains = _text_list(
            safe_context.get("include_domains"),
            limit=180,
        )
        exclude_domains = _text_list(
            safe_context.get("exclude_domains"),
            limit=180,
        )

        components: list[dict[str, Any]] = []
        requirements: list[dict[str, Any]] = []
        for rank, candidate in enumerate(assessment.component_candidates, start=1):
            component_id = candidate.component_id
            obligation_ids = list(localized_obligation_ids.get(component_id, ()))
            subquestion = candidate.user_facing_subquestion
            strategy = _deterministic_primary_query_strategy(
                component_id=component_id,
                rank=rank,
                subquestion=subquestion,
                source_obligation_candidate_ids=obligation_ids,
                source_kinds=[source_kind_by_id[item] for item in obligation_ids if item in source_kind_by_id],
                current_date=current_date,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
            )
            requirement_id = f"search-requirement:{component_id}:initial"
            components.append(
                {
                    "component_id": component_id,
                    "component_revision": "1",
                    "user_facing_label": f"Required component {rank}",
                    "user_facing_question": subquestion,
                    "requirement_posture": "required",
                    "acceptance_criteria": ["Direct source support for the accepted component need."],
                    "semantic_slot_ids": ["slot:subject"],
                    "source_obligation_candidate_ids": obligation_ids,
                    "allowed_support_kinds": ["direct"],
                    "max_inference_depth": 0,
                    "materiality": "material",
                    "partial_answer_policy": "qualify_visible_gap",
                    "metadata": {
                        "deterministic_component_candidate_id": candidate.candidate_id,
                        "source_obligation_binding_posture": ("deterministic_component_local_reproof"),
                    },
                }
            )
            requirements.append(
                {
                    "component_id": component_id,
                    "requirement_id": requirement_id,
                    "requirement_summary": (
                        "Prepare a provider-neutral primary query for this accepted required component."
                    ),
                    "source_obligation_candidate_ids": obligation_ids,
                    "preferred_source_kinds": sorted(
                        {source_kind_by_id[item] for item in obligation_ids if item in source_kind_by_id}
                    ),
                    "recency_requirement": (
                        current_date
                        if any(
                            "current" in source_kind_by_id.get(item, "")
                            or "date_bound" in source_kind_by_id.get(item, "")
                            for item in obligation_ids
                        )
                        else None
                    ),
                    "metadata": {
                        "query_strategy_candidates": [strategy],
                        "allocation_posture": "one_primary_per_required_component",
                        "provider_name_neutral": True,
                    },
                }
            )

        subject = (
            _clean_text(
                route_facts.get("primary_entity") or route_facts.get("core_topic"),
                limit=220,
            )
            or query_text[:220]
        )
        return {
            "question_meaning_summary": (
                "Interpret the request as accepted, source-bound required "
                "components with provider-neutral initial query strategy."
            ),
            "requested_output": ("Answer every required component with bounded source support."),
            "semantic_slots": [
                {
                    "slot_id": "slot:subject",
                    "slot_kind": "entity",
                    "status": "explicit",
                    "candidate_values": [subject],
                    "selected_value": subject,
                    "materiality": "material",
                    "user_confirmation_required": False,
                    "metadata": {"provider_name_neutral": True},
                }
            ],
            "answer_components": components,
            "source_obligation_candidates": source_candidates,
            "component_search_requirements": requirements,
            "material_ambiguity_posture": "none_detected",
            "mandatory_caveats": [],
            "prohibited_upgrades": ["Do not treat query strategy or reconnaissance as evidence."],
            "normalization_obligations": [],
            "assumptions": [],
            "unsupported_or_deferred_outputs": [
                "Post-result secondary-query authorization belongs to later SearchJudgment."
            ],
            "contract_amendment_candidates": [],
            "planner_model_metadata": {
                "model_adapter_enabled": False,
                "provider": "none",
                "model": "deterministic",
                "effort": "deterministic",
                "use_reasoning": False,
                "require_json": False,
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "provider_payload_retained": False,
            },
        }


def _localized_component_obligation_ids(
    *,
    assessment: Any,
    requested_mode: str | None,
    selected_depth: str | None,
    primary_entity: str | None,
) -> dict[str, tuple[str, ...]]:
    """Bind only component-local source needs from the deterministic owner.

    The query-shape assessment can retain run-level source candidates that are
    not attributable to any one component.  Reusing its first-component
    fallback as an accepted component binding would make unrelated obligations
    look jointly satisfiable by one source.  Re-assessing each bounded
    subquestion without run-level source requirements preserves the source-kind
    semantics while keeping those unscoped candidates at QMR level.
    """

    candidates = tuple(assessment.source_obligation_candidates)
    localized: dict[str, tuple[str, ...]] = {}
    for component in assessment.component_candidates:
        local_records = build_deterministic_search_work_runtime_records(
            DeterministicSearchWorkRuntimeInput(
                contract_id=f"search-planner-local:{component.component_id}",
                run_contract_projection={"selected_depth": selected_depth},
                route_facts={
                    "core_topic": component.user_facing_subquestion,
                    "primary_entity": primary_entity,
                },
                requested_mode=requested_mode,
                selected_depth=selected_depth,
                safe_query_preview=component.user_facing_subquestion,
                metadata={
                    "owner": "search_planner_component_source_binding_reproof",
                    "provider_free": True,
                    "run_level_source_requirements_excluded": True,
                },
            )
        )
        local_kinds = {
            candidate.kind.value for candidate in local_records.query_shape_assessment.source_obligation_candidates
        }
        localized[component.component_id] = tuple(
            candidate.candidate_id
            for candidate in candidates
            if candidate.kind.value in local_kinds
            or (candidate.kind.value == "source_bound_numeric" and component.component_id in candidate.component_ids)
        )
    return localized


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
            "safe_context": _bounded_context_json_safe(self.safe_context),
            "route_context_ref": _bounded_context_json_safe(self.route_context_ref),
            "run_context_ref": _bounded_context_json_safe(self.run_context_ref),
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
        # The exact query is transient adapter input.  Use it only to rederive
        # the repository-owned deterministic query-shape qualification that
        # the accepted QMR must carry; it is never retained in the observation.
        planner_input=planner_input,
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
    planner_model_metadata = _planner_model_metadata(result)

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
        "planner_model_metadata": planner_model_metadata,
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
    # RunKernel's closed Observation envelope performs one final bounded JSON
    # projection before reduction.  Compute proposal identity from that exact
    # nested shape so depth/string bounding cannot invalidate an otherwise
    # truthful proposal between execution and canonical reduction.
    observation_payload = _observation_envelope_safe(
        {
            "schema_version": SEARCH_PLANNER_OBSERVATION_SCHEMA_VERSION,
            "planner_input": planner_input_ref,
            "planner_proposal": proposal_without_digest,
            "question_meaning_record": qmr_payload,
        }
    )
    bounded_proposal = _safe_mapping(observation_payload.get("planner_proposal"))
    proposal_digest = _digest_json(_proposal_digest_payload(bounded_proposal))
    observation_payload["planner_proposal"] = {
        **bounded_proposal,
        "proposal_digest": proposal_digest,
    }
    return _observation_envelope_safe(observation_payload)


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
        "planner_model_metadata": _safe_mapping(proposal.get("planner_model_metadata")),
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
        "planner_model_metadata": _safe_mapping(state.get("planner_model_metadata")),
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
    planner_model_metadata = _safe_mapping(
        adapter_result.get("planner_model_metadata")
    )
    query_shape_metadata = _deterministic_query_shape_metadata(
        planner_input=planner_input,
        components=components,
    )
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
        "contract_amendment_candidates_deferred": bool(_safe_list(adapter_result.get("contract_amendment_candidates"))),
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
        **query_shape_metadata,
        "semantic_planning_owner": (
            "selected fast-model SearchPlanner"
            if planner_model_metadata.get("model_adapter_enabled") is True
            else "explicitly injected SearchPlanner adapter"
        ),
        "model_proposed_component_count": len(components),
        # Existing downstream multi-component consumers use these compatibility
        # fields. They now reflect the accepted model proposal mechanically;
        # deterministic query-shape assessment no longer decides their values.
        "explicit_factual_component_list": len(components) > 1,
        "requested_synthesis_directive": (
            _clean_text(
                adapter_result.get("requested_output")
                or adapter_result.get("question_meaning_summary"),
                limit=360,
            )
            if len(components) > 1
            else None
        ),
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


def _deterministic_query_shape_metadata(
    *,
    planner_input: Mapping[str, Any],
    components: Sequence[AnswerComponentContract],
) -> dict[str, Any]:
    """Emit bounded compatibility telemetry without semantic authority."""

    safe_context = _safe_mapping(planner_input.get("safe_context"))
    route_facts = _safe_mapping(safe_context.get("route_facts"))
    run_contract = _safe_mapping(safe_context.get("run_contract_projection"))
    query_text = _clean_text(
        planner_input.get(_ADAPTER_ONLY_USER_QUERY_TEXT_KEY),
        limit=SEARCH_PLANNER_FULL_QUERY_TEXT_CHARS,
    )
    contract_id = _clean_token(run_contract.get("contract_id"))
    if not query_text or not contract_id or not route_facts:
        return {}

    try:
        records = build_deterministic_search_work_runtime_records(
            DeterministicSearchWorkRuntimeInput(
                contract_id=contract_id,
                run_contract_projection=run_contract,
                route_facts=route_facts,
                requested_mode=_clean_token(planner_input.get("requested_mode")),
                selected_depth=_clean_token(run_contract.get("selected_depth")),
                safe_query_preview=query_text,
                current_date_ref=_clean_text(safe_context.get("current_date")),
                metadata={
                    "owner": "search_planner_qmr_query_shape_compatibility_signal",
                    "provider_free": True,
                },
            )
        )
    except Exception as exc:  # noqa: BLE001 - telemetry cannot become authority.
        return {
            "deterministic_query_shape_signal_owner": (
                "core.search_work_query_shape_runtime"
            ),
            "deterministic_query_shape_role": "compatibility_observability_only",
            "deterministic_query_shape_signal_status": "unavailable",
            "deterministic_query_shape_failure_kind": type(exc).__name__,
        }
    assessment = records.query_shape_assessment
    assessment_metadata = _safe_mapping(assessment.metadata)
    assessment_component_ids = [candidate.component_id for candidate in assessment.component_candidates]
    proposal_component_ids = [component.component_id for component in components]
    explicitly_qualified = assessment_metadata.get("explicit_factual_component_list") is True
    return {
        "deterministic_query_shape_signal_owner": "core.search_work_query_shape_runtime",
        "deterministic_query_shape_role": "compatibility_observability_only",
        "deterministic_query_shape_assessed_from_transient_input": True,
        "deterministic_explicit_factual_component_list": explicitly_qualified,
        "deterministic_requested_synthesis_directive": _clean_text(
            assessment_metadata.get("requested_synthesis_directive"),
            limit=360,
        ),
        "structured_route_posture": _clean_token(assessment_metadata.get("structured_route_posture")),
        "structured_route_syntax_kind": _clean_token(assessment_metadata.get("structured_route_syntax_kind")),
        "newly_licensed_route_form": bool(assessment_metadata.get("newly_licensed_route_form")),
        "route_qualification_behavior_changed": bool(assessment_metadata.get("route_qualification_behavior_changed")),
        "query_plan_behavior_changed": bool(assessment_metadata.get("query_plan_behavior_changed")),
        "provider_search_behavior_changed": bool(assessment_metadata.get("provider_search_behavior_changed")),
        "deterministic_query_shape_component_ids": assessment_component_ids,
        "model_proposed_component_ids": proposal_component_ids,
        "deterministic_component_count_matches_model": (
            len(assessment_component_ids) == len(proposal_component_ids)
        ),
        "deterministic_component_ids_match_model": (
            assessment_component_ids == proposal_component_ids
        ),
    }


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
    if len(items) > SEARCH_PLANNER_MAX_ANSWER_COMPONENTS:
        raise SearchPlannerRuntimeError(
            "search planner proposal exceeds the five-component acceptance ceiling"
        )
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
                partial_answer_policy=mapping.get("partial_answer_policy") or PartialAnswerPolicy.QUALIFY_VISIBLE_GAP,
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
                            mapping.get("component_candidate_ids") or mapping.get("component_ids"),
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
        component_id = _clean_token(mapping.get("component_id"))
        requirement_id = _clean_token(mapping.get("requirement_id") or mapping.get("search_requirement_id"))
        metadata = _provider_neutral_requirement_metadata(
            mapping.get("metadata"),
            component_id=component_id,
            requirement_id=requirement_id,
        )
        requirements.append(
            _without_empty(
                {
                    "component_id": component_id,
                    "requirement_id": requirement_id,
                    "requirement_summary": _clean_text(
                        mapping.get("requirement_summary") or mapping.get("summary") or mapping.get("query_goal"),
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
                    "metadata": metadata,
                }
            )
        )
    return requirements


def initial_query_strategies_from_planner_state(
    *,
    planner_state: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    policy: InitialQueryAllocationPolicy,
) -> list[dict[str, Any]]:
    """Return validated planner candidates bound to accepted required components.

    This is deterministic validation, not admission.  QueryPlan remains the
    sole owner of executable identity, role, order, and dispatch eligibility.
    """

    state = _safe_mapping(planner_state)
    contract = _safe_mapping(accepted_contract)
    requirements = [
        _safe_mapping(item) for item in _safe_list(state.get("component_search_requirements")) if _safe_mapping(item)
    ]
    accepted_components = [
        _safe_mapping(item)
        for item in _safe_list(contract.get("accepted_answer_component_refs"))
        if _safe_mapping(item)
    ]
    if not state or not accepted_components:
        raise SearchPlannerRuntimeError("initial query strategy requires planner state and an accepted contract")

    planner_ref = {
        "proposal_id": state.get("proposal_id"),
        "proposal_digest": state.get("proposal_digest"),
        "question_meaning_record_id": _safe_mapping(state.get("question_meaning_record_ref")).get("record_id"),
        "question_meaning_record_digest": _safe_mapping(state.get("question_meaning_record_ref")).get("record_digest"),
    }
    required_components = [
        component
        for component in accepted_components
        if _clean_token(component.get("requirement_posture")) == "required"
    ]
    if not required_components:
        raise SearchPlannerRuntimeError("initial query strategy requires at least one accepted required component")

    strategies: list[dict[str, Any]] = []
    seen_strategy_ids: set[str] = set()
    for component in required_components:
        component_id = _clean_token(component.get("component_id"))
        if not component_id:
            raise SearchPlannerRuntimeError("accepted required component is missing component_id")
        accepted_source_ids = set(
            _text_list(
                component.get("source_obligation_candidate_ids") or component.get("source_obligation_candidate_refs"),
                limit=160,
            )
        )
        component_requirements = [
            requirement for requirement in requirements if _clean_token(requirement.get("component_id")) == component_id
        ]
        component_strategies: list[dict[str, Any]] = []
        for requirement in component_requirements:
            requirement_id = _clean_token(requirement.get("requirement_id"))
            requirement_source_ids = set(
                _text_list(
                    requirement.get("source_obligation_candidate_ids"),
                    limit=160,
                )
            )
            if not requirement_id:
                raise SearchPlannerRuntimeError(f"component {component_id} search requirement is missing identity")
            if not requirement_source_ids.issubset(accepted_source_ids):
                raise SearchPlannerRuntimeError(
                    f"component {component_id} search requirement references an unaccepted source obligation"
                )
            requirement_ref = {
                "requirement_id": requirement_id,
                "component_id": component_id,
                "source_obligation_candidate_ids": sorted(requirement_source_ids),
                "requirement_digest": _digest_json(
                    {
                        "requirement_id": requirement_id,
                        "component_id": component_id,
                        "source_obligation_candidate_ids": sorted(requirement_source_ids),
                        "requirement_summary": requirement.get("requirement_summary"),
                        "recency_requirement": requirement.get("recency_requirement"),
                    }
                ),
            }
            metadata = _safe_mapping(requirement.get("metadata"))
            for raw_strategy in _safe_list(metadata.get("query_strategy_candidates")):
                strategy = _safe_mapping(raw_strategy)
                strategy_id = _clean_token(strategy.get("strategy_id"))
                if not strategy_id:
                    raise SearchPlannerRuntimeError(f"component {component_id} query strategy requires strategy_id")
                if strategy_id in seen_strategy_ids:
                    raise SearchPlannerRuntimeError(f"duplicate initial query strategy id: {strategy_id}")
                seen_strategy_ids.add(strategy_id)
                strategy_component_id = _clean_token(strategy.get("component_id"))
                if strategy_component_id != component_id:
                    raise SearchPlannerRuntimeError(
                        f"initial query strategy component binding does not match accepted component {component_id}"
                    )
                strategy_source_ids = set(
                    _text_list(
                        strategy.get("source_obligation_candidate_ids"),
                        limit=160,
                    )
                )
                if not strategy_source_ids.issubset(accepted_source_ids):
                    raise SearchPlannerRuntimeError(
                        f"strategy {strategy_id} references an unaccepted source obligation"
                    )
                component_strategies.append(
                    {
                        **strategy,
                        "accepted_component_ref": {
                            "component_id": component_id,
                            "component_revision": component.get("component_revision"),
                            "component_digest": component.get("component_digest"),
                        },
                        "search_requirement_ref": requirement_ref,
                        "parent_search_planner_proposal_ref": planner_ref,
                        "allocation_policy_version": policy.policy_version,
                    }
                )
        primary_count = sum(1 for strategy in component_strategies if strategy.get("candidate_kind") == "primary")
        if (
            policy.required_component_floor_enabled
            and primary_count < policy.primary_query_target_per_required_component
        ):
            raise SearchPlannerRuntimeError(f"accepted required component {component_id} has no primary query strategy")
        strategies.extend(component_strategies)
    return strategies


def _provider_neutral_requirement_metadata(
    value: Any,
    *,
    component_id: str | None,
    requirement_id: str | None,
) -> dict[str, Any]:
    metadata = _safe_mapping(value)
    raw_strategies = _safe_list(metadata.get("query_strategy_candidates"))
    provider_identity_supplied = any(_contains_provider_selection_key(item) for item in raw_strategies)
    safe_metadata = {
        key: item
        for key, item in metadata.items()
        if key != "query_strategy_candidates"
        and _normalize_key(key)
        not in {
            "provider",
            "provider_hint",
            "provider_name",
            "provider_order",
            "provider_depth",
            "provider_variant",
            "provider_fallback",
        }
    }
    strategies = [
        _normalize_query_strategy_candidate(
            item,
            component_id=component_id,
            requirement_id=requirement_id,
        )
        for item in raw_strategies
    ]
    strategies = [item for item in strategies if item]
    if strategies:
        safe_metadata["query_strategy_candidates"] = strategies
    safe_metadata["provider_name_neutral"] = True
    safe_metadata["planner_provider_identity_ignored"] = provider_identity_supplied
    return _json_safe(safe_metadata)


def _normalize_query_strategy_candidate(
    value: Any,
    *,
    component_id: str | None,
    requirement_id: str | None,
) -> dict[str, Any]:
    candidate = _safe_mapping(value)
    if not candidate:
        return {}
    strategy_id = _clean_token(candidate.get("strategy_id") or candidate.get("candidate_id"))
    query_text = _clean_text(
        candidate.get("candidate_query_text") or candidate.get("query_text"),
        limit=300,
    )
    if not strategy_id or not query_text:
        raise SearchPlannerRuntimeError("query strategy candidate requires strategy_id and bounded query text")
    bound_component_id = _clean_token(candidate.get("component_id")) or component_id
    if not bound_component_id or (component_id and bound_component_id != component_id):
        raise SearchPlannerRuntimeError("query strategy candidate component binding is missing or stale")
    requested_role = _clean_token(candidate.get("requested_role")) or "initial"
    if requested_role not in _ALLOWED_INITIAL_QUERY_ROLES:
        raise SearchPlannerRuntimeError(f"unsupported initial query role requested: {requested_role}")
    candidate_kind = _clean_token(candidate.get("candidate_kind")) or "primary"
    if candidate_kind not in {"primary", "secondary"}:
        raise SearchPlannerRuntimeError("query strategy candidate_kind must be primary or secondary")
    recon = _normalize_recon_requirement(candidate.get("recon_requirement"))
    recon_candidates = [
        _safe_mapping(item) for item in _safe_list(recon.get("candidate_queries")) if _safe_mapping(item)
    ]
    return _without_empty(
        {
            "strategy_id": strategy_id,
            "component_id": bound_component_id,
            "requirement_id": _clean_token(candidate.get("requirement_id")) or requirement_id,
            "candidate_kind": candidate_kind,
            "candidate_query_text": query_text,
            "requested_role": requested_role,
            "source_obligation_candidate_ids": _text_list(
                candidate.get("source_obligation_candidate_ids"),
                limit=160,
            ),
            "entity_alias_posture": _clean_token(candidate.get("entity_alias_posture")),
            "currentness_posture": _clean_text(
                candidate.get("currentness_posture"),
                limit=180,
            ),
            "official_canonical_intent": _clean_token(candidate.get("official_canonical_intent")),
            "domain_constraints": _safe_domain_constraints(candidate.get("domain_constraints")),
            "document_family": _clean_text(
                candidate.get("document_family"),
                limit=160,
            ),
            "distinct_need_justification": _clean_text(
                candidate.get("distinct_need_justification") or candidate.get("nonredundancy_reason"),
                limit=300,
            ),
            "immediate_dispatch_requested": bool(candidate.get("immediate_dispatch_requested")),
            "immediate_dispatch_distinct_need": bool(candidate.get("immediate_dispatch_distinct_need")),
            # Candidate text is flattened one level so the existing bounded
            # RunKernel Observation sanitizer preserves it without changing
            # the SearchPlanner or QueryPlan schemas.
            "recon_posture": recon.get("posture"),
            "recon_unresolved_dimension_ids": recon.get("unresolved_dimension_ids"),
            "recon_required_for_truthful_targeting": bool(recon.get("required_for_truthful_targeting")),
            "recon_candidate_queries_by_dimension": {
                str(item["dimension_id"]): item["candidate_query_text"] for item in recon_candidates
            },
            "recon_query_kinds_by_dimension": {
                str(item["dimension_id"]): item["query_kind"] for item in recon_candidates
            },
            "provider_name_neutral": True,
            "planner_provider_identity_ignored": (_contains_provider_selection_key(candidate)),
        }
    )


def normalize_provider_neutral_query_strategy_candidate(
    value: Mapping[str, Any],
    *,
    component_id: str,
    requirement_id: str,
) -> dict[str, Any]:
    """Validate one planner/revision candidate through the shared contract."""

    normalized = _normalize_query_strategy_candidate(
        value,
        component_id=component_id,
        requirement_id=requirement_id,
    )
    if not normalized:
        raise SearchPlannerRuntimeError("query strategy candidate did not survive provider-neutral validation")
    return normalized


def _normalize_recon_requirement(value: Any) -> dict[str, Any]:
    recon = _safe_mapping(value)
    if not recon:
        return {"posture": "not_needed", "required_for_truthful_targeting": False}
    posture = _clean_token(recon.get("posture")) or "not_needed"
    if posture not in _ALLOWED_RECON_POSTURES:
        raise SearchPlannerRuntimeError(f"unsupported recon requirement posture: {posture}")
    dimension_ids = _text_list(
        recon.get("unresolved_dimension_ids") or recon.get("dimension_ids"),
        limit=160,
    )
    candidates: list[dict[str, Any]] = []
    seen_dimensions: set[str] = set()
    for raw in _safe_list(recon.get("candidate_queries")):
        item = _safe_mapping(raw)
        dimension_id = _clean_token(item.get("dimension_id"))
        query_text = _clean_text(
            item.get("candidate_query_text") or item.get("query_text"),
            limit=300,
        )
        if not dimension_id or not query_text:
            raise SearchPlannerRuntimeError("recon candidate requires dimension_id and bounded query text")
        if dimension_id in seen_dimensions:
            raise SearchPlannerRuntimeError("recon candidates must address distinct unresolved dimensions")
        seen_dimensions.add(dimension_id)
        candidates.append(
            {
                "dimension_id": dimension_id,
                "candidate_query_text": query_text,
                "query_kind": _clean_token(item.get("query_kind")) or "disambiguation_probe",
            }
        )
    if posture != "not_needed" and not dimension_ids:
        dimension_ids = [item["dimension_id"] for item in candidates]
    return {
        "posture": posture,
        "unresolved_dimension_ids": dimension_ids,
        "candidate_queries": candidates,
        "required_for_truthful_targeting": bool(recon.get("required_for_truthful_targeting")),
    }


def _safe_domain_constraints(value: Any) -> dict[str, list[str]]:
    constraints = _safe_mapping(value)
    return {
        "include": _text_list(
            constraints.get("include") or constraints.get("include_domains"),
            limit=180,
        ),
        "exclude": _text_list(
            constraints.get("exclude") or constraints.get("exclude_domains"),
            limit=180,
        ),
    }


def _contains_provider_selection_key(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    forbidden = {
        "provider",
        "provider_hint",
        "provider_name",
        "provider_order",
        "provider_depth",
        "provider_variant",
        "provider_fallback",
    }
    return any(_normalize_key(key) in forbidden for key in value)


def _deterministic_primary_query_strategy(
    *,
    component_id: str,
    rank: int,
    subquestion: str,
    source_obligation_candidate_ids: Sequence[str],
    source_kinds: Sequence[str],
    current_date: str | None,
    include_domains: Sequence[str],
    exclude_domains: Sequence[str],
) -> dict[str, Any]:
    kinds = set(source_kinds)
    role = "initial"
    suffixes: list[str] = []
    official_intent: str | None = None
    document_family: str | None = None
    if kinds & {"official_current", "legal_current_primary"}:
        role = "official_bias"
        suffixes.append("official")
        official_intent = "official_source"
        document_family = "official rule policy or release"
    elif "canonical_documentation" in kinds:
        role = "canonical_bias"
        suffixes.append("official documentation")
        official_intent = "canonical_source"
        document_family = "canonical documentation or release"
    if kinds & {"official_current", "date_bound_currentness"} and current_date:
        year = next(
            (token for token in current_date.replace("-", " ").split() if len(token) == 4 and token.isdigit()),
            None,
        )
        if year and year not in subquestion:
            suffixes.append(year)
    query_text = " ".join(item for item in [subquestion.rstrip(" ?."), *suffixes] if item)[:300]
    return {
        "strategy_id": f"strategy:{component_id}:primary:{rank}",
        "component_id": component_id,
        "candidate_kind": "primary",
        "candidate_query_text": query_text,
        "requested_role": role,
        "source_obligation_candidate_ids": list(source_obligation_candidate_ids),
        "currentness_posture": current_date if suffixes else None,
        "official_canonical_intent": official_intent,
        "domain_constraints": {
            "include": list(include_domains),
            "exclude": list(exclude_domains),
        },
        "document_family": document_family,
        "distinct_need_justification": ("Primary intentional query path for the accepted required component."),
        "immediate_dispatch_requested": True,
        "immediate_dispatch_distinct_need": True,
        "recon_requirement": {
            "posture": "not_needed",
            "unresolved_dimension_ids": [],
            "candidate_queries": [],
            "required_for_truthful_targeting": False,
        },
        "provider_name_neutral": True,
    }


def _planner_model_metadata(adapter_result: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _safe_mapping(adapter_result.get("planner_model_metadata"))
    allowed_keys = {
        "planner_model_adapter_schema_version",
        "planner_model_prompt_schema_version",
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
        raise SearchPlannerRuntimeError(
            "search planner proposal includes closed authority fields: " + ", ".join(forbidden)
        )
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
    # Query-strategy lineage adds several bounded identity layers beneath a
    # component requirement.  Keep the sanitizer idempotent across observation
    # creation and RunKernel reduction rather than replacing a legitimate deep
    # ref with a different truncation marker on the second pass.
    if depth > 16:
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
            clean_key = str(key or "").strip()[:120]
            if not clean_key:
                continue
            if _is_sensitive_key(clean_key):
                if clean_key in _SAFE_FALSE_RETENTION_KEYS and value[key] is False:
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
    return _clean_text(value, limit=300)


def _bounded_context_json_safe(value: Any, *, depth: int = 0) -> Any:
    """Bound planning-only context independently from proposal validation."""

    if depth > SEARCH_PLANNER_SAFE_CONTEXT_MAX_DEPTH:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=SEARCH_PLANNER_SAFE_CONTEXT_TEXT_CHARS)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        items = sorted(value.items(), key=lambda item: str(item[0]))[
            :SEARCH_PLANNER_SAFE_CONTEXT_MAX_COLLECTION_ITEMS
        ]
        for raw_key, item in items:
            clean_key = str(raw_key or "").strip()[:120]
            if not clean_key or _is_sensitive_key(clean_key):
                continue
            out[clean_key] = _bounded_context_json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [
            _bounded_context_json_safe(item, depth=depth + 1)
            for item in items[:SEARCH_PLANNER_SAFE_CONTEXT_MAX_COLLECTION_ITEMS]
        ]
    if hasattr(value, "to_dict"):
        return _bounded_context_json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=SEARCH_PLANNER_SAFE_CONTEXT_TEXT_CHARS)


def _observation_envelope_safe(value: Any, *, depth: int = 0) -> Any:
    """Project the exact bounded shape accepted by the closed RunKernel seam.

    SearchPlanner cannot import RunKernel.  This pure transport projection is
    intentionally narrower than planner-state sanitization and mirrors the
    existing Observation JSON envelope without changing that authority owner.
    """

    if depth > 8:
        return "[redacted]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _observation_clean_text(value, limit=800)
    if isinstance(value, Mapping):
        projected: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _observation_clean_text(key, limit=100)
            if not key_text:
                continue
            if key_text.casefold() in _SENSITIVE_KEYS:
                projected[key_text] = "[redacted]"
            else:
                projected[key_text] = _observation_envelope_safe(
                    item,
                    depth=depth + 1,
                )
        return projected
    if isinstance(value, list | tuple | set | frozenset):
        ordered = list(value)
        if isinstance(value, set | frozenset):
            ordered = sorted(ordered, key=str)
        return [_observation_envelope_safe(item, depth=depth + 1) for item in ordered[:80]]
    return _observation_clean_text(value, limit=300)


def _observation_clean_text(value: Any, *, limit: int) -> str | None:
    text = " ".join(str(value or "").split())
    return text[:limit] if text else None


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
    "DeterministicSearchPlannerAdapter",
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
    "initial_query_strategies_from_planner_state",
    "normalize_provider_neutral_query_strategy_candidate",
]
