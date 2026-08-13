"""Ordinary-product SearchOS Slice A judgment and acquisition composition."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from core import searchos_navigation_runtime as navigation_runtime
from core.acquisition_adapters import AcquisitionTransports
from core.cap_enforcement import RunCapExceeded
from core.discovery_source_result import normalize_discovery_result_url
from core.fetch_read_content_reference import (
    fetch_read_content_packet_ref_from_packet,
    validate_fetch_read_content_packet,
)
from core.query_plan_runtime_adapter import QueryPlanRuntimeAdapter
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_judgment_read_assessment_runtime import (
    SelectedCandidateMaterialNeedBindingV1,
    derive_selected_candidate_material_need_bindings,
    execute_searchos_candidate_read_to_custody,
)
from core.search_result_candidate_packet import (
    search_result_candidate_packet_ref_from_packet,
)
from core.searchos_iterative_judgment_runtime import (
    MAX_FOLLOWUP_QUERY_CHARS,
    MAX_UNRESOLVED_REASON_CHARS,
    SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION,
    SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION,
    SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION,
    SearchOSJudgmentAction,
    SearchOSRuntimeError,
    SearchOSSlotPosture,
    build_candidate_use_options_v1,
    build_candidate_use_window_v1,
    build_searchos_effective_semantic_slot_view,
    build_searchos_iteration_candidate_set_v1,
    build_searchos_policy_snapshot,
    build_searchos_read_custody_material_ref,
    build_searchos_revision_1_candidate_state_v1,
    candidate_use_option_ref,
    searchos_revision_1_candidate_state_ref,
    validate_searchos_append_only_lineage,
    validate_searchos_judgment_model_output,
)
from core.source_classifier import classify_source

SEARCHOS_SLICE_A_TRACE_KEY = "searchos_slice_a"
SEARCHOS_JUDGMENT_MODEL_INPUT_SCHEMA_VERSION = (
    "searchos_judgment_model_input_v1"
)
SEARCHOS_JUDGMENT_DECISION_CONTRACT_SCHEMA_VERSION = (
    "searchos_judgment_decision_contract_v1"
)
SEARCHOS_ZERO_RESULT_INITIAL_DISCOVER_WAVE_SCHEMA_VERSION = (
    "searchos_zero_result_initial_discover_wave_v1"
)
SEARCHOS_JUDGMENT_SYSTEM_PROMPT = """You are the neutral SearchOS SearchJudgment.
The input is one searchos_judgment_model_input_v1 JSON object.
authorized_request is the sole legal-action and exact-ref authority. Inspect
authorized_request.legal_actions, authorized_request.candidate_use_options,
and authorized_request.read_custody_refs. active_need explains the component
question, source obligation, and authorized search work that the action must
advance. candidate_directional_contexts are
DISCOVER-only hints: they may guide a READ or follow-up decision but cannot
support an answer. read_custody_materials contain the bounded readable content
that must be judged against active_need; only this material may be handed to
semantic evaluation. Do not treat custody-ref presence alone as readiness.
decision_contract is the normative output contract.

Return exactly one JSON object matching searchos_judgment_decision_v1. Always
include schema_version, judgment_request_id, judgment_request_digest, slot_id,
action, and a nonempty bounded reason; copy judgment_request_id,
judgment_request_digest, and slot_id exactly from authorized_request. Choose
exactly one action from
authorized_request.legal_actions:
- REQUEST_READ_PAGE copies one exact candidate_use_option_ref from the request.
- PROPOSE_FOLLOWUP_QUERY authors new bounded followup_query text from
  active_need and inspected material and selects exactly one provider-neutral
  discovery_job_class from authorized_request.allowed_followup_job_classes;
  this is the only action allowed to author a query, and QueryPlan independently
  validates the exact text, job class, and component/semantic lineage.
- PROPOSE_INTERPRETATION_BINDING supplies exactly interpretation_binding with
  one exact semantic_slot_ref from the authorized eligible list, one declared
  resolved_value, exact current candidate/READ basis refs, and
  disclose_assumption. It does not admit the binding, evidence, support,
  satisfaction, or a contract mutation.
- REQUIRE_CLARIFICATION supplies one exact semantic_slot_ref from the
  authorized clarification-eligible list (plus exact required
  READ-insufficient assessments when custody exists). It does not author prose.
- HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION copies a nonempty selection
  of exact current read_custody_refs.
- HANDOFF_UNRESOLVED supplies only the shared fields and its reason.

After READ custody exists, REQUEST_READ_PAGE, PROPOSE_FOLLOWUP_QUERY,
REQUIRE_CLARIFICATION, and HANDOFF_UNRESOLVED must include exactly one
read_insufficient assessment for every current READ custody ref, copied
exactly, with the contract's exact assessment fields and disposition. Semantic
handoff and interpretation-binding proposal must not include those assessments.
Forbidden fields must be absent, and no unsupported fields are allowed. Never
invent or alter a URL, authority ref, candidate ref, custody ref, component
ref, source-obligation ref, provider choice, request identity, disposition,
deterministic fallback, or unsupported field.
"""
_NAVIGATION_JUDGMENT_SYSTEM_PROMPT = """You are the neutral SearchOS SearchJudgment.
The input is one searchos_judgment_model_input_v1 JSON object containing an
authorized searchos_navigation_judgment_request_v1. authorized_request is the
sole legal-action and exact-ref authority. Inspect
authorized_request.legal_actions, authorized_request.candidate_use_options,
authorized_request.read_custody_refs, and authorized_request.navigation_options.
active_need explains the component question, source obligation, and authorized
search work that the action must advance. candidate_directional_contexts are
DISCOVER-only hints: they may guide a READ, navigation, or follow-up decision
but cannot support an answer. read_custody_materials contain the bounded
readable content that must be judged against active_need; only this material
may be handed to semantic evaluation. Do not treat custody-ref presence alone
as readiness. decision_contract is the normative output contract.

Return exactly one JSON object matching
searchos_navigation_judgment_decision_v1. Always include schema_version,
judgment_request_id, judgment_request_digest, slot_id, action, and a nonempty
bounded reason; copy judgment_request_id, judgment_request_digest, and slot_id
exactly from authorized_request. Choose exactly one action from
authorized_request.legal_actions:
- REQUEST_READ_PAGE copies one exact candidate_use_option_ref from the request.
- PROPOSE_FOLLOWUP_QUERY authors new bounded followup_query text from
  active_need and inspected material and selects exactly one provider-neutral
  discovery_job_class from authorized_request.allowed_followup_job_classes;
  this is the only action allowed to author a query, and QueryPlan independently
  validates the exact text, job class, and component/semantic lineage.
- PROPOSE_INTERPRETATION_BINDING supplies exactly interpretation_binding with
  one exact semantic_slot_ref from the authorized eligible list, one declared
  resolved_value, exact current candidate/READ basis refs, and
  disclose_assumption. It does not admit the binding, evidence, support,
  satisfaction, or a contract mutation.
- REQUIRE_CLARIFICATION supplies one exact semantic_slot_ref from the
  authorized clarification-eligible list (plus exact required
  READ-insufficient assessments when custody exists). It does not author prose.
- HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION copies a nonempty selection
  of exact current read_custody_refs.
- HANDOFF_UNRESOLVED supplies the shared fields and its reason, plus only the
  required exact read-custody assessments when current custody exists.
- REQUEST_NAVIGATE_BREADCRUMB copies exactly one current, URL-free
  navigation_candidate_ref from authorized_request.navigation_options and no
  other navigation field.

After READ custody exists, REQUEST_READ_PAGE, PROPOSE_FOLLOWUP_QUERY,
REQUIRE_CLARIFICATION, HANDOFF_UNRESOLVED, and REQUEST_NAVIGATE_BREADCRUMB must
include exactly one read_insufficient assessment for every current READ custody
ref, copied exactly, with the contract's exact assessment fields and
disposition. Semantic handoff and interpretation-binding proposal must not
include those assessments. Forbidden fields must be absent, and no unsupported
fields are allowed. Never invent or alter a URL,
destination binding, authority ref, candidate ref, navigation ref, custody ref,
component ref, source-obligation ref, provider choice, route, request identity,
disposition, deterministic fallback, or unsupported field. Exact navigation
destination URLs are intentionally absent from the input.
"""
TERMINAL_CANDIDATE_OPTION_DISPOSITIONS = frozenset(
    {"custodied", "read_insufficient", "invalid", "declined"}
)


def build_searchos_judgment_decision_contract_v1(*, navigation_enabled: bool = False) -> dict[str, Any]:
    """Build the transient machine-readable mirror of the strict validator."""

    shared_required_fields = [
        "schema_version",
        "judgment_request_id",
        "judgment_request_digest",
        "slot_id",
        "action",
        "reason",
    ]
    conditionally_assessed = "required_exact_if_current_custody_else_absent"
    actions = {
        SearchOSJudgmentAction.REQUEST_READ_PAGE.value: {
            "required_fields": [
                *shared_required_fields,
                "candidate_use_option_ref",
            ],
            "forbidden_fields": [
                "read_custody_refs",
                "followup_query",
                "discovery_job_class",
                "interpretation_binding",
                "semantic_slot_ref",
            ],
            "candidate_use_option_ref_rule": (
                "copy exactly one candidate_use_option_ref from "
                "authorized_request.candidate_use_options"
            ),
            "post_read_assessment_rule": (
                "each existing READ material was inspected and does not satisfy "
                "the active need, so another candidate READ is justified"
            ),
            "read_custody_assessments_mode": conditionally_assessed,
        },
        SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY.value: {
            "required_fields": [
                *shared_required_fields,
                "followup_query",
                "discovery_job_class",
            ],
            "forbidden_fields": [
                "candidate_use_option_ref",
                "read_custody_refs",
                "interpretation_binding",
                "semantic_slot_ref",
            ],
            "followup_query_rule": (
                "SearchJudgment authors one exact bounded follow-up query from "
                "the accepted active need and the inspected material; QueryPlan "
                "independently validates and authorizes the exact text"
            ),
            "discovery_job_class_rule": (
                "copy exactly one provider-neutral class from "
                "authorized_request.allowed_followup_job_classes"
            ),
            "authorship_forbidden": [
                "urls",
                "authority_refs",
                "component_refs",
                "source_obligation_refs",
                "candidate_refs",
                "provider_choices",
            ],
            "read_custody_assessments_mode": conditionally_assessed,
        },
        SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION.value: {
            "required_fields": [*shared_required_fields, "read_custody_refs"],
            "forbidden_fields": [
                "candidate_use_option_ref",
                "followup_query",
                "read_custody_assessments",
                "discovery_job_class",
                "interpretation_binding",
                "semantic_slot_ref",
            ],
            "read_custody_refs_rule": (
                "copy a nonempty selection of exact refs from "
                "authorized_request.read_custody_refs"
            ),
            "semantic_handoff_rule": (
                "material selected for semantic handoff is not simultaneously "
                "labeled insufficient"
            ),
            "read_custody_assessments_mode": "forbidden",
        },
        SearchOSJudgmentAction.HANDOFF_UNRESOLVED.value: {
            "required_fields": list(shared_required_fields),
            "forbidden_fields": [
                "candidate_use_option_ref",
                "read_custody_refs",
                "followup_query",
                "discovery_job_class",
                "interpretation_binding",
                "semantic_slot_ref",
            ],
            "unresolved_rule": (
                "bounded explanation of an open need; this action is not success "
                "and is not final whole-run stopping"
            ),
            "read_custody_assessments_mode": conditionally_assessed,
        },
        SearchOSJudgmentAction.PROPOSE_INTERPRETATION_BINDING.value: {
            "required_fields": [
                *shared_required_fields,
                "interpretation_binding",
            ],
            "forbidden_fields": [
                "candidate_use_option_ref",
                "read_custody_refs",
                "followup_query",
                "discovery_job_class",
                "read_custody_assessments",
                "semantic_slot_ref",
            ],
            "interpretation_binding_exact_fields": [
                "semantic_slot_ref",
                "resolved_value",
                "basis_candidate_refs",
                "basis_read_custody_refs",
                "disclose_assumption",
            ],
            "semantic_slot_ref_rule": (
                "copy authorized_request.interpretation_binding_contract."
                "eligible_semantic_slot_refs member exactly"
            ),
            "resolved_value_rule": (
                "select exactly one already-declared candidate value"
            ),
            "basis_ref_rule": (
                "copy exact current candidate or READ custody refs; at least "
                "one basis ref is required"
            ),
            "authority_created": [],
            "read_custody_assessments_mode": "forbidden",
        },
        SearchOSJudgmentAction.REQUIRE_CLARIFICATION.value: {
            "required_fields": [
                *shared_required_fields,
                "semantic_slot_ref",
            ],
            "forbidden_fields": [
                "candidate_use_option_ref",
                "read_custody_refs",
                "followup_query",
                "discovery_job_class",
                "interpretation_binding",
            ],
            "clarification_rule": (
                "copy one exact member of authorized_request."
                "clarification_eligible_semantic_slot_refs; do not select "
                "or invent an interpretation"
            ),
            "read_custody_assessments_mode": conditionally_assessed,
        },
    }
    if navigation_enabled:
        for contract in actions.values():
            contract["forbidden_fields"].append("navigation_candidate_ref")
        actions[SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value] = {
            "required_fields": [*shared_required_fields, "navigation_candidate_ref"],
            "forbidden_fields": [
                "candidate_use_option_ref",
                "read_custody_refs",
                "followup_query",
                "discovery_job_class",
                "interpretation_binding",
                "semantic_slot_ref",
            ],
            "navigation_candidate_ref_rule": (
                "copy exactly one navigation_candidate_ref from "
                "authorized_request.navigation_options"
            ),
            "authorship_forbidden": ["urls", "destination_bindings", "providers", "routes", "alternate_refs"],
            "read_custody_assessments_mode": conditionally_assessed,
        }
    core = {
        "contract_name": "SearchOSJudgmentDecisionContractV1",
        "schema_version": SEARCHOS_JUDGMENT_DECISION_CONTRACT_SCHEMA_VERSION,
        "decision_schema_version": SEARCHOS_NAVIGATION_JUDGMENT_DECISION_SCHEMA_VERSION
        if navigation_enabled
        else SEARCHOS_JUDGMENT_DECISION_SCHEMA_VERSION,
        "shared_required_fields": shared_required_fields,
        "copy_exactly_from_authorized_request": {
            "judgment_request_id": "judgment_request_id",
            "judgment_request_digest": "judgment_request_digest",
            "slot_id": "slot_ref.slot_id",
        },
        "allowed_output_fields": [
            *shared_required_fields,
            "candidate_use_option_ref",
            *(["navigation_candidate_ref"] if navigation_enabled else []),
            "read_custody_refs",
            "followup_query",
            "discovery_job_class",
            "interpretation_binding",
            "semantic_slot_ref",
            "read_custody_assessments",
        ],
        "unsupported_fields_forbidden": True,
        "input_field_roles": {
            "authorized_request": (
                "sole request identity and legal-action authority; its option "
                "and custody refs are exact-copy sources"
                + ("; navigation_options are URL-free exact-copy sources" if navigation_enabled else "")
            ),
            "active_need": (
                "accepted component question, source-obligation standard, and "
                "all semantic obligations plus authorized search work that "
                "this decision must advance"
            ),
            "candidate_directional_contexts": (
                "DISCOVER-only non-support-bearing hints for READ or follow-up"
            ),
            "read_custody_materials": (
                "bounded readable content corresponding exactly to current "
                "custody refs and inspected for usefulness or insufficiency "
                "against active_need"
            ),
        },
        "post_read_assessment_contract": {
            "required_when": (
                "authorized_request.read_custody_refs is nonempty and action "
                "is neither HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION "
                "nor PROPOSE_INTERPRETATION_BINDING"
            ),
            "absent_when_no_current_custody": True,
            "one_per_current_custody_ref": True,
            "required_fields": [
                "reviewed_custody_ref",
                "material_disposition",
                "reason_code",
            ],
            "reviewed_custody_ref_rule": (
                "copy each authorized_request.read_custody_refs item exactly"
            ),
            "material_disposition": "read_insufficient",
            "reason_code_rule": (
                "nonempty machine-readable lower-case token of at most 80 "
                "characters using letters, digits, underscore, period, colon, "
                "or hyphen"
            ),
            "meaning": (
                "The model has inspected every existing READ material and "
                "determined that it does not satisfy the active need, so the "
                "selected non-handoff action is justified."
            ),
        },
        "bounds": {
            "followup_query_max_characters": MAX_FOLLOWUP_QUERY_CHARS,
            "reason_max_characters": MAX_UNRESOLVED_REASON_CHARS,
        },
        "actions": actions,
        "durable_retention_allowed": False,
    }
    return {**core, "decision_contract_digest": _digest(core)}


@dataclass(frozen=True, slots=True)
class SearchOSSliceAProductResult:
    revision_1: Mapping[str, Any]
    iteration_candidate_sets: tuple[Mapping[str, Any], ...]
    semantic_handoffs: tuple[Mapping[str, Any], ...]
    searchos_semantic_material: tuple[Mapping[str, Any], ...]
    projection: Mapping[str, Any]
    provider_calls_attempted: int = 0
    provider_calls_completed: int = 0
    initial_query_plan_items: tuple[Mapping[str, Any], ...] = ()
    initial_identity_refs: tuple[Mapping[str, Any], ...] = ()
    identity_deltas_by_digest: Mapping[
        str, tuple[Mapping[str, Any], ...]
    ] | None = None
    candidate_packets: tuple[Mapping[str, Any], ...] = ()
    reusable_read_custody_by_url: Mapping[str, Mapping[str, Any]] | None = field(
        default=None,
        repr=False,
        compare=False,
    )


FollowupDiscover = Callable[[str, int, Mapping[str, Any]], Mapping[str, Any]]


def build_searchos_zero_result_initial_discover_wave_v1(
    *,
    run_id: str,
    request_id: str,
    query_plan_ref: Mapping[str, Any],
    query_plan_item_refs: Sequence[Mapping[str, Any]],
    provider_plan_ref: Mapping[str, Any],
    provider_plan_record_refs: Sequence[Mapping[str, Any]],
    provider_route_refs: Sequence[Mapping[str, Any]],
    retrieval_action_refs: Sequence[Mapping[str, Any]],
    source_result_identity_set_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Record an exact first orientation wave that returned no identities."""

    item_refs = [deepcopy(dict(item)) for item in query_plan_item_refs]
    if not item_refs or any(
        item.get("discovery_job_class") != "orientation"
        for item in item_refs
    ):
        raise SearchOSRuntimeError(
            "zero-result initial wave requires only orientation QueryPlan items"
        )
    record_refs = [deepcopy(dict(item)) for item in provider_plan_record_refs]
    route_refs = [deepcopy(dict(item)) for item in provider_route_refs]
    if not record_refs or len(record_refs) != len(route_refs):
        raise SearchOSRuntimeError(
            "zero-result initial wave requires exact provider record/route lineage"
        )
    action_refs = [deepcopy(dict(item)) for item in retrieval_action_refs]
    if not action_refs:
        raise SearchOSRuntimeError(
            "zero-result initial wave requires completed retrieval action lineage"
        )
    core = {
        "schema_version": (
            SEARCHOS_ZERO_RESULT_INITIAL_DISCOVER_WAVE_SCHEMA_VERSION
        ),
        "owner": "RunKernel.SearchOSIterativeJudgment",
        "run_id": str(run_id),
        "request_id": str(request_id),
        "query_plan_ref": deepcopy(dict(query_plan_ref)),
        "query_plan_item_refs": item_refs,
        "provider_plan_ref": deepcopy(dict(provider_plan_ref)),
        "provider_plan_record_refs": record_refs,
        "provider_route_refs": route_refs,
        "retrieval_action_refs": action_refs,
        "source_result_identity_set_ref": deepcopy(
            dict(source_result_identity_set_ref)
        ),
        "selected_candidate_refs": [],
        "zero_useful_result": True,
        "orientation_refinement_authority_created": True,
        "orientation_refinement_limit": 1,
        "read_authority_created": False,
        "evidence_admitted": False,
        "support_admitted": False,
        "source_obligation_satisfied": False,
        "canonical_state": True,
    }
    digest = _digest(core)
    return validate_searchos_zero_result_initial_discover_wave_v1({
        **core,
        "zero_result_discover_wave_id": (
            f"searchos-zero-result-wave:{digest[:24]}"
        ),
        "zero_result_discover_wave_digest": digest,
        "replay_identity": f"searchos-zero-result-wave:{digest}",
    }, run_id=run_id, request_id=request_id)


def validate_searchos_zero_result_initial_discover_wave_v1(
    wave: Mapping[str, Any],
    *,
    run_id: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    safe = deepcopy(dict(wave)) if isinstance(wave, Mapping) else {}
    identity_fields = {
        "zero_result_discover_wave_id",
        "zero_result_discover_wave_digest",
        "replay_identity",
    }
    exact_fields = {
        "schema_version",
        "owner",
        "run_id",
        "request_id",
        "query_plan_ref",
        "query_plan_item_refs",
        "provider_plan_ref",
        "provider_plan_record_refs",
        "provider_route_refs",
        "retrieval_action_refs",
        "source_result_identity_set_ref",
        "selected_candidate_refs",
        "zero_useful_result",
        "orientation_refinement_authority_created",
        "orientation_refinement_limit",
        "read_authority_created",
        "evidence_admitted",
        "support_admitted",
        "source_obligation_satisfied",
        "canonical_state",
        *identity_fields,
    }
    if set(safe) != exact_fields:
        raise SearchOSRuntimeError(
            "zero-result initial discover wave fields are not exact"
        )
    if safe.get("schema_version") != (
        SEARCHOS_ZERO_RESULT_INITIAL_DISCOVER_WAVE_SCHEMA_VERSION
    ) or safe.get("owner") != "RunKernel.SearchOSIterativeJudgment":
        raise SearchOSRuntimeError(
            "zero-result initial discover wave schema or owner is invalid"
        )
    if run_id is not None and safe.get("run_id") != str(run_id):
        raise SearchOSRuntimeError("zero-result initial wave run scope mismatch")
    if request_id is not None and safe.get("request_id") != str(request_id):
        raise SearchOSRuntimeError(
            "zero-result initial wave request scope mismatch"
        )
    item_refs = list(safe.get("query_plan_item_refs") or ())
    record_refs = list(safe.get("provider_plan_record_refs") or ())
    route_refs = list(safe.get("provider_route_refs") or ())
    action_refs = list(safe.get("retrieval_action_refs") or ())
    if not isinstance(safe.get("query_plan_ref"), Mapping) or not item_refs:
        raise SearchOSRuntimeError(
            "zero-result initial wave lacks QueryPlan lineage"
        )
    if any(
        not isinstance(item, Mapping)
        or item.get("discovery_job_class") != "orientation"
        for item in item_refs
    ):
        raise SearchOSRuntimeError(
            "zero-result initial wave requires only orientation QueryPlan items"
        )
    if (
        not isinstance(safe.get("provider_plan_ref"), Mapping)
        or not record_refs
        or len(record_refs) != len(route_refs)
        or not action_refs
        or any(
            not isinstance(item, Mapping)
            for item in [*record_refs, *route_refs, *action_refs]
        )
    ):
        raise SearchOSRuntimeError(
            "zero-result initial wave lacks exact route/action lineage"
        )
    identity_set_ref = safe.get("source_result_identity_set_ref")
    if (
        not isinstance(identity_set_ref, Mapping)
        or identity_set_ref.get("source_result_identity_count") != 0
        or safe.get("selected_candidate_refs") != []
    ):
        raise SearchOSRuntimeError(
            "zero-result initial wave cannot retain selected identities"
        )
    for authority_field, expected in {
        "zero_useful_result": True,
        "orientation_refinement_authority_created": True,
        "orientation_refinement_limit": 1,
        "read_authority_created": False,
        "evidence_admitted": False,
        "support_admitted": False,
        "source_obligation_satisfied": False,
        "canonical_state": True,
    }.items():
        if safe.get(authority_field) != expected:
            raise SearchOSRuntimeError(
                "zero-result initial wave field "
                f"{authority_field} is invalid"
            )
    core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key not in identity_fields
    }
    digest = _digest(core)
    if (
        safe.get("zero_result_discover_wave_digest") != digest
        or safe.get("zero_result_discover_wave_id")
        != f"searchos-zero-result-wave:{digest[:24]}"
        or safe.get("replay_identity")
        != f"searchos-zero-result-wave:{digest}"
    ):
        raise SearchOSRuntimeError(
            "zero-result initial discover wave identity is invalid"
        )
    return safe


def initialize_searchos_clarification_only(
    *,
    run_kernel: RunKernel,
    query_authority: QueryPlanRuntimeAdapter,
    profile_name: str,
) -> SearchOSSliceAProductResult:
    """Install a no-dispatch SearchOS result for explicit user-choice slots."""

    if run_kernel.state.searchos_state:
        raise SearchOSRuntimeError(
            "clarification-only SearchOS state is already initialized"
        )
    active_slots = _active_slots(
        run_kernel,
        query_authority,
        allow_no_dispatch_planning_snapshot=True,
    )
    if not active_slots or any(
        item.get("clarification_only") is not True
        for item in active_slots
    ):
        raise SearchOSRuntimeError(
            "clarification-only initialization requires only explicit confirmation slots"
        )
    policy = build_searchos_policy_snapshot(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        profile_name=_profile_name(profile_name),
        navigation_runtime_open=True,
        existing_gap_recovery_runtime_open=True,
    )
    initialize = run_kernel.authorize_searchos_initialization(
        answer_contract_ref=_active_answer_contract_ref(run_kernel),
        policy_snapshot=policy,
        active_slots=active_slots,
        initial_candidate_state_ref=None,
    )
    run_kernel.reduce(
        Observation.from_action(
            initialize,
            observation_type=ObservationType.SEARCHOS_INITIALIZED,
            status=RunStageStatus.COMPLETED,
            payload={"searchos_state": initialize.inputs["searchos_state"]},
        )
    )
    state = run_kernel.state.searchos_state
    semantic_obligations = dict(
        state.get("semantic_obligations_by_id") or {}
    )
    projection = {
        "schema_version": "searchos_slice_a_product_runtime_v1",
        "owner": "RunKernel.SearchOSIterativeJudgment",
        "revision_1_ref": {},
        "iteration_candidate_set_refs": [],
        "append_only_lineage_proof_ref": {},
        "semantic_handoff_refs": [],
        "semantic_material_refs": [],
        "slot_postures": {
            slot_id: state["slots_by_id"][slot_id]["posture"]
            for slot_id in state["active_slot_ids"]
        },
        "slot_discovery_job_classes": {
            slot_id: None for slot_id in state["active_slot_ids"]
        },
        "semantic_obligation_binding_postures": {
            semantic_obligation_id: dict(obligation).get(
                "binding_posture"
            )
            for semantic_obligation_id, obligation in (
                semantic_obligations.items()
            )
        },
        "semantic_obligation_clarification_postures": {
            semantic_obligation_id: deepcopy(
                dict(obligation).get("clarification_posture") or {}
            )
            for semantic_obligation_id, obligation in (
                semantic_obligations.items()
            )
        },
        "clarification_required": True,
        "clarification_only_no_dispatch": True,
        "interpretation_binding_refs": [],
        "directional_candidate_context_support_eligible": False,
        "read_custody_is_only_support_proposal_eligible_material": True,
        "provider_calls_attempted": 0,
        "provider_calls_completed": 0,
        "searchos_recovery_executed": False,
    }
    return SearchOSSliceAProductResult(
        revision_1={},
        iteration_candidate_sets=(),
        semantic_handoffs=(),
        searchos_semantic_material=(),
        projection=projection,
        provider_calls_attempted=0,
        provider_calls_completed=0,
        initial_query_plan_items=tuple(
            item.to_dict() for item in query_authority.plan.items
        ),
        initial_identity_refs=(),
        identity_deltas_by_digest={},
        candidate_packets=(),
        reusable_read_custody_by_url={},
    )


def execute_searchos_slice_a_iterative_judgment(
    *,
    run_kernel: RunKernel,
    candidate_packet: Mapping[str, Any],
    query_authority: QueryPlanRuntimeAdapter,
    discovery_result_store: Any,
    profile_name: str,
    ask_model: Callable[..., Any] | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    available_providers: Mapping[str, object],
    acquisition_transports: AcquisitionTransports | None,
    execute_followup_discover: FollowupDiscover | None,
    before_transport: Callable[[], Any] | None = None,
    measure_context_stage: Callable[..., Any] | None = None,
    effort: str = "medium",
) -> SearchOSSliceAProductResult:
    locator_store = navigation_runtime.EphemeralNavigationLocatorStore(
        run_id=run_kernel.state.run_id, request_id=run_kernel.state.request_id
    )
    try:
        return _execute_searchos_slice_a_iterative_judgment(**locals())
    finally:
        locator_store.discard_all()


def execute_searchos_zero_result_orientation(
    *,
    run_kernel: RunKernel,
    zero_result_initial_wave: Mapping[str, Any],
    query_authority: QueryPlanRuntimeAdapter,
    discovery_result_store: Any,
    profile_name: str,
    ask_model: Callable[..., Any] | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    available_providers: Mapping[str, object],
    acquisition_transports: AcquisitionTransports | None,
    execute_followup_discover: FollowupDiscover | None,
    before_transport: Callable[[], Any] | None = None,
    measure_context_stage: Callable[..., Any] | None = None,
    effort: str = "medium",
) -> SearchOSSliceAProductResult:
    """Run the same SearchOS worklist after a zero-result orientation wave."""

    locator_store = navigation_runtime.EphemeralNavigationLocatorStore(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
    )
    try:
        return _execute_searchos_slice_a_iterative_judgment(
            locator_store=locator_store,
            run_kernel=run_kernel,
            candidate_packet={},
            zero_result_initial_wave=zero_result_initial_wave,
            query_authority=query_authority,
            discovery_result_store=discovery_result_store,
            profile_name=profile_name,
            ask_model=ask_model,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            use_reasoning=use_reasoning,
            available_providers=available_providers,
            acquisition_transports=acquisition_transports,
            execute_followup_discover=execute_followup_discover,
            before_transport=before_transport,
            measure_context_stage=measure_context_stage,
            effort=effort,
        )
    finally:
        locator_store.discard_all()


def execute_searchos_recovery_cycle(
    *,
    prior_result: SearchOSSliceAProductResult,
    recovery_cycle_ref: Mapping[str, Any],
    run_kernel: RunKernel,
    candidate_packet: Mapping[str, Any],
    query_authority: QueryPlanRuntimeAdapter,
    discovery_result_store: Any,
    profile_name: str,
    ask_model: Callable[..., Any] | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    available_providers: Mapping[str, object],
    acquisition_transports: AcquisitionTransports | None,
    execute_followup_discover: FollowupDiscover | None,
    before_transport: Callable[[], Any] | None = None,
    measure_context_stage: Callable[..., Any] | None = None,
    effort: str = "medium",
) -> SearchOSSliceAProductResult:
    """Consume an already-admitted SearchOS recovery lease through the same loop."""

    locator_store = navigation_runtime.EphemeralNavigationLocatorStore(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
    )
    try:
        return _execute_searchos_slice_a_iterative_judgment(
            locator_store=locator_store,
            prior_result=prior_result,
            recovery_cycle_ref=recovery_cycle_ref,
            run_kernel=run_kernel,
            candidate_packet=candidate_packet,
            query_authority=query_authority,
            discovery_result_store=discovery_result_store,
            profile_name=profile_name,
            ask_model=ask_model,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            use_reasoning=use_reasoning,
            effort=effort,
            available_providers=available_providers,
            acquisition_transports=acquisition_transports,
            execute_followup_discover=execute_followup_discover,
            before_transport=before_transport,
            measure_context_stage=measure_context_stage,
        )
    finally:
        locator_store.discard_all()


def _execute_searchos_slice_a_iterative_judgment(
    *,
    locator_store: navigation_runtime.EphemeralNavigationLocatorStore,
    run_kernel: RunKernel,
    candidate_packet: Mapping[str, Any],
    query_authority: QueryPlanRuntimeAdapter,
    discovery_result_store: Any,
    profile_name: str,
    ask_model: Callable[..., Any] | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    available_providers: Mapping[str, object],
    acquisition_transports: AcquisitionTransports | None,
    execute_followup_discover: FollowupDiscover | None,
    before_transport: Callable[[], Any] | None = None,
    measure_context_stage: Callable[..., Any] | None = None,
    prior_result: SearchOSSliceAProductResult | None = None,
    recovery_cycle_ref: Mapping[str, Any] | None = None,
    zero_result_initial_wave: Mapping[str, Any] | None = None,
    effort: str = "medium",
) -> SearchOSSliceAProductResult:
    """Run the canonical post-first-wave Slice A loop under RunKernel."""

    initial_packet = dict(candidate_packet)
    zero_result_wave = (
        validate_searchos_zero_result_initial_discover_wave_v1(
            zero_result_initial_wave or {},
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
        )
        if zero_result_initial_wave
        else {}
    )
    if bool(initial_packet) == bool(zero_result_wave):
        raise SearchOSRuntimeError(
            "SearchOS Slice A requires exactly one candidate packet or zero-result wave"
        )
    initial_packet_ref = (
        search_result_candidate_packet_ref_from_packet(initial_packet)
        if initial_packet
        else {}
    )
    initial_query_items = (
        [deepcopy(dict(item)) for item in prior_result.initial_query_plan_items]
        if prior_result is not None
        else [item.to_dict() for item in query_authority.plan.items]
    )
    initial_identities = (
        [deepcopy(dict(item)) for item in prior_result.initial_identity_refs]
        if prior_result is not None
        else [item.ref() for item in discovery_result_store.identities()]
    )
    prior_packets = (
        [
            deepcopy(dict(item))
            for item in prior_result.candidate_packets
        ]
        if prior_result is not None
        else []
    )
    if prior_result is None and initial_packet:
        initial_binding_state = derive_selected_candidate_material_need_bindings(
            run_kernel=run_kernel,
            candidate_packet=initial_packet,
            query_plan=query_authority.plan,
            discovery_result_store=discovery_result_store,
        )
        bindings = _bindings_from_state(initial_binding_state)
    else:
        # An admitted recovery cycle starts with an empty candidate window.
        # In particular, a searched-premise amendment changes the active
        # contract, so replaying the parent cycle's candidate packet would be
        # stale authority as well as non-novel recovery input.
        initial_binding_state = {
            "schema_version": "searchos_recovery_empty_binding_state_v1",
            "bindings": [],
        }
        bindings = []
    revision_1 = (
        deepcopy(dict(prior_result.revision_1))
        if prior_result is not None
        else build_searchos_revision_1_candidate_state_v1(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            candidate_packet_ref=initial_packet_ref,
            zero_result_discover_wave_ref=zero_result_wave,
            initial_query_plan_ref=query_authority.plan.to_ref(),
            initial_query_plan_items=initial_query_items,
            initial_identity_set_ref=discovery_result_store.identity_set_ref(),
            initial_identity_refs=initial_identities,
            selected_candidate_refs=_candidate_refs(initial_packet),
            bounded_candidate_material_refs=_material_refs(bindings),
            selection_facts={
                "selected_candidate_count": len(
                    initial_packet.get("candidate_records") or ()
                ),
                "first_admitted_discover_wave_count": 1,
                "zero_useful_result": not bool(initial_packet),
            },
            overflow_facts={
                "selection_overflow_count": int(
                    initial_packet.get("selection_overflow_count") or 0
                ),
                "contributor_overflow_count": sum(
                    int(item.get("contributor_overflow_count") or 0)
                    for item in initial_packet.get("candidate_records") or ()
                    if isinstance(item, Mapping)
                ),
            },
        )
    )
    revision_ref = searchos_revision_1_candidate_state_ref(revision_1)
    if prior_result is None:
        active_slots = _active_slots(
            run_kernel,
            query_authority,
            allow_no_dispatch_planning_snapshot=bool(zero_result_wave),
        )
        policy = build_searchos_policy_snapshot(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            profile_name=_profile_name(profile_name),
            navigation_runtime_open=True,
            existing_gap_recovery_runtime_open=True,
        )
        initialize = run_kernel.authorize_searchos_initialization(
            answer_contract_ref=(
                revision_1_answer_contract_ref(initial_packet)
                if initial_packet
                else _active_answer_contract_ref(run_kernel)
            ),
            policy_snapshot=policy,
            active_slots=active_slots,
            initial_candidate_state_ref=revision_ref,
        )
        run_kernel.reduce(
            Observation.from_action(
                initialize,
                observation_type=ObservationType.SEARCHOS_INITIALIZED,
                status=RunStageStatus.COMPLETED,
                payload={
                    "searchos_state": initialize.inputs["searchos_state"]
                },
            )
        )
    else:
        from core.searchos_existing_gap_recovery_runtime import (
            validate_active_searchos_generalized_recovery_cycle_ref,
        )

        if recovery_cycle_ref is None:
            raise SearchOSRuntimeError(
                "recovery execution requires its exact admitted cycle"
            )
        validate_active_searchos_generalized_recovery_cycle_ref(
            run_kernel.state.searchos_state,
            recovery_cycle_ref,
        )

    packets_by_id = {
        str(
            search_result_candidate_packet_ref_from_packet(packet)[
                "packet_id"
            ]
        ): packet
        for packet in [initial_packet, *prior_packets]
        if packet
    }
    candidate_packets = [
        packet for packet in [initial_packet, *prior_packets] if packet
    ]
    if prior_packets and prior_packets[0] == initial_packet:
        candidate_packets = prior_packets
    current_binding_state_ref = (
        deepcopy(
            run_kernel.state.searchos_state["current_candidate_state_ref"]
        )
        if prior_result is not None
        else revision_ref
    )
    binding_candidate_states = {
        binding.binding_id: current_binding_state_ref for binding in bindings
    }
    binding_iteration_refs: dict[str, Mapping[str, Any]] = (
        {
            binding.binding_id: current_binding_state_ref
            for binding in bindings
        }
        if prior_result is not None
        and current_binding_state_ref.get("iteration_candidate_set_id")
        else {}
    )
    iteration_sets: list[Mapping[str, Any]] = (
        [deepcopy(dict(item)) for item in prior_result.iteration_candidate_sets]
        if prior_result is not None
        else []
    )
    identity_deltas_by_digest: dict[str, Sequence[Mapping[str, Any]]] = {
        key: [deepcopy(dict(item)) for item in values]
        for key, values in (
            (prior_result.identity_deltas_by_digest or {}).items()
            if prior_result is not None
            else ()
        )
    }
    custody_by_url: dict[str, dict[str, Any]] = {
        str(url): deepcopy(dict(outcome))
        for url, outcome in (
            (prior_result.reusable_read_custody_by_url or {}).items()
            if prior_result is not None
            else ()
        )
    }
    packet_by_custody_id: dict[str, Mapping[str, Any]] = {}
    dispositions: dict[str, str] = {}
    semantic_handoffs: list[Mapping[str, Any]] = (
        [deepcopy(dict(item)) for item in prior_result.semantic_handoffs]
        if prior_result is not None
        else []
    )
    prior_handoff_count = len(semantic_handoffs)
    provider_calls = [0, 0]

    while True:
        state = run_kernel.state.searchos_state
        participating = [
            slot_id
            for slot_id in state["active_slot_ids"]
            if state["slots_by_id"][slot_id]["posture"] == SearchOSSlotPosture.ACTIVE_UNJUDGED.value
        ]
        if not participating:
            break
        try:
            reservation = run_kernel.reserve_searchos_judgment_round(
                slot_ids=participating
            )
        except ValueError:
            for slot_id in participating:
                _mark_budget_exhausted(run_kernel, slot_id)
            break

        for slot_id in participating:
            slot = run_kernel.state.searchos_state["slots_by_id"][slot_id]
            try:
                options, window, exhaustion_reason = _prepare_candidate_window(
                    slot=slot,
                    bindings=bindings,
                    binding_candidate_states=binding_candidate_states,
                    binding_iteration_refs=binding_iteration_refs,
                    discovery_result_store=discovery_result_store,
                    policy_snapshot=run_kernel.state.searchos_state["policy_snapshot"],
                    dispositions={
                        **dispositions,
                        **{
                            option_id: str(record.get("disposition") or "")
                            for option_id, record in dict(
                                slot.get("candidate_option_dispositions") or {}
                            ).items()
                            if isinstance(record, Mapping)
                        },
                    },
                )
            except Exception as exc:
                run_kernel.return_searchos_pre_call_reservation(
                    reservation_ref=reservation,
                    slot_id=slot_id,
                    reason="candidate_window_preparation_rejected",
                )
                run_kernel.mark_searchos_slot_stale_or_invalid(
                    slot_id=slot_id,
                    reason=f"candidate_window_preparation_failed:{type(exc).__name__}",
                )
                continue
            if exhaustion_reason:
                run_kernel.return_searchos_pre_call_reservation(
                    reservation_ref=reservation,
                    slot_id=slot_id,
                    reason=exhaustion_reason,
                )
                run_kernel.mark_searchos_slot_unresolved(
                    slot_id=slot_id,
                    reason=exhaustion_reason,
                )
                continue
            run_kernel.expose_searchos_candidate_window(window=window)
            current_slot = run_kernel.state.searchos_state["slots_by_id"][slot_id]
            navigation_window = navigation_runtime.project_navigation_window(
                run_kernel.state.searchos_state, slot_id=slot_id
            ) or None
            try:
                action = run_kernel.authorize_searchos_judgment(
                    reservation_ref=reservation,
                    slot_id=slot_id,
                    candidate_window=window,
                    read_custody_refs=current_slot["custody_refs"],
                    navigation_window=navigation_window,
                )
            except Exception as exc:
                run_kernel.return_searchos_pre_call_reservation(
                    reservation_ref=reservation,
                    slot_id=slot_id,
                    reason="judgment_authorization_rejected",
                )
                run_kernel.mark_searchos_slot_stale_or_invalid(
                    slot_id=slot_id,
                    reason=f"judgment_authorization_rejected:{type(exc).__name__}",
                )
                continue
            request = action.inputs["judgment_request"]
            try:
                model_input = _build_searchos_judgment_model_input(
                    run_kernel=run_kernel,
                    authorized_request=request,
                    slot_id=slot_id,
                    options=options,
                    window=window,
                    bindings=bindings,
                    binding_candidate_states=binding_candidate_states,
                    binding_iteration_refs=binding_iteration_refs,
                    discovery_result_store=discovery_result_store,
                    packet_by_custody_id=packet_by_custody_id,
                )
                raw = _invoke_judgment_model(
                    model_input=model_input,
                    ask_model=ask_model,
                    provider=provider,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    effort=effort,
                    use_reasoning=use_reasoning,
                    measure_context_stage=measure_context_stage,
                )
                parsed = _strict_json_object(raw)
                validate_searchos_judgment_model_output(
                    request=request,
                    model_output=parsed,
                )
            except RunCapExceeded:
                raise
            except Exception as exc:
                failure_reason = _failure_reason(exc)
                run_kernel.reduce(
                    Observation.from_action(
                        action,
                        observation_type=ObservationType.SEARCHOS_JUDGMENT_DECIDED,
                        status=RunStageStatus.FAILED,
                        payload={
                            "failure_reason": failure_reason,
                            "raw_model_response_retained": False,
                        },
                    )
                )
                if _invalid_or_stale_nomination(exc):
                    run_kernel.mark_searchos_slot_stale_or_invalid(
                        slot_id=slot_id,
                        reason=failure_reason,
                    )
                continue
            run_kernel.reduce(
                Observation.from_action(
                    action,
                    observation_type=ObservationType.SEARCHOS_JUDGMENT_DECIDED,
                    status=RunStageStatus.COMPLETED,
                    payload={"model_output": parsed},
                )
            )
            decision = deepcopy(run_kernel.state.projections["searchos_iterative_judgment"])
            for assessment in decision.get("read_custody_assessments") or ():
                custody_id = str(
                    dict(assessment.get("reviewed_custody_ref") or {}).get(
                        "read_custody_material_id"
                    )
                    or ""
                )
                assessed_custody = next(
                    (
                        dict(item)
                        for item in current_slot.get("custody_refs") or ()
                        if isinstance(item, Mapping)
                        and item.get("read_custody_material_id") == custody_id
                    ),
                    {},
                )
                assessed_option_id = str(
                    dict(assessed_custody.get("candidate_use_option_ref") or {}).get(
                        "candidate_use_option_id"
                    )
                    or ""
                )
                if assessed_option_id:
                    dispositions[assessed_option_id] = "read_insufficient"
            decision_action = SearchOSJudgmentAction(decision["action"])
            if decision_action is SearchOSJudgmentAction.REQUEST_READ_PAGE:
                if run_kernel.state.searchos_state["slots_by_id"][slot_id][
                    "posture"
                ] != SearchOSSlotPosture.AWAITING_READ.value:
                    continue
                option_ref = dict(decision["candidate_use_option_ref"])
                option_id = option_ref["candidate_use_option_id"]
                if (
                    dispositions.get(option_id)
                    in TERMINAL_CANDIDATE_OPTION_DISPOSITIONS
                ):
                    run_kernel.mark_searchos_slot_stale_or_invalid(
                        slot_id=slot_id,
                        reason="read_nomination_already_disposed",
                    )
                    continue
                binding = _binding_for_option(
                    bindings=bindings,
                    slot_id=slot_id,
                    binding_slot_id=_binding_source_slot_id(current_slot),
                    option_ref=option_ref,
                    options=options,
                )
                prior = custody_by_url.get(binding.normalized_url)
                navigation_source: Any = None
                if prior:
                    custody_outcome = prior
                    reused = True
                else:
                    packet_id = binding.candidate_packet_ref["packet_id"]
                    packet = packets_by_id.get(packet_id)
                    if not packet:
                        run_kernel.mark_searchos_slot_stale_or_invalid(
                            slot_id=slot_id,
                            reason="candidate_packet_stale",
                        )
                        continue
                    before_attempted, before_completed = (
                        _acquisition_provider_call_totals(run_kernel)
                    )
                    try:
                        custody_outcome = execute_searchos_candidate_read_to_custody(
                            run_kernel=run_kernel,
                            candidate_packet=packet,
                            binding=binding,
                            available_providers=available_providers,
                            acquisition_transports=acquisition_transports,
                            before_transport=before_transport,
                        )
                    except RunCapExceeded:
                        raise
                    except Exception as exc:
                        after_attempted, after_completed = (
                            _acquisition_provider_call_totals(run_kernel)
                        )
                        provider_calls[0] += max(0, after_attempted - before_attempted)
                        provider_calls[1] += max(0, after_completed - before_completed)
                        run_kernel.mark_searchos_slot_stale_or_invalid(
                            slot_id=slot_id,
                            reason=_read_failure_reason(exc),
                        )
                        continue
                    after_attempted, after_completed = (
                        _acquisition_provider_call_totals(run_kernel)
                    )
                    attempt_delta = max(0, after_attempted - before_attempted)
                    completion_delta = max(0, after_completed - before_completed)
                    if attempt_delta != int(
                        custody_outcome.get("provider_calls_attempted") or 0
                    ) or completion_delta != int(
                        custody_outcome.get("provider_calls_completed") or 0
                    ):
                        raise SearchOSRuntimeError(
                            "SearchOS READ provider-call accounting is stale"
                        )
                    provider_calls[0] += attempt_delta
                    provider_calls[1] += completion_delta
                    navigation_source = custody_outcome.pop(
                        "navigation_source_markdown",
                        None,
                    )
                    reused = False
                custody_ref = build_searchos_read_custody_material_ref(
                    slot_ref=run_kernel.state.searchos_state["slots_by_id"][slot_id]["slot_ref"],
                    candidate_use_option_ref=option_ref,
                    custody_record=custody_outcome["custody_record"],
                    same_normalized_url_reused=reused,
                )
                custody_action = run_kernel.authorize_searchos_read_custody_admission(custody_material_ref=custody_ref)
                run_kernel.reduce(
                    Observation.from_action(
                        custody_action,
                        observation_type=(ObservationType.SEARCHOS_READ_CUSTODY_ADMITTED),
                        status=RunStageStatus.COMPLETED,
                        payload={"custody_material_ref": custody_ref},
                    )
                )
                if not reused and isinstance(navigation_source, str):
                    run_kernel.state.searchos_state = navigation_runtime.admit_navigation_options_from_markdown(
                        run_kernel.state.searchos_state, slot_id=slot_id,
                        parent_read_custody_ref=custody_ref, parent_url=binding.normalized_url,
                        parent_depth=0, ancestor_physical_identity_digests=(),
                        markdown_text=navigation_source, locator_store=locator_store,
                    )[0]
                if not reused:
                    custody_by_url[binding.normalized_url] = custody_outcome
                dispositions[option_id] = "custodied"
                packet_by_custody_id[custody_ref["read_custody_material_id"]] = custody_outcome[
                    "fetch_read_content_packet"
                ]
            elif decision_action is SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB:
                navigation_result = _execute_product_navigation(
                    run_kernel=run_kernel,
                    decision=decision,
                    locator_store=locator_store,
                    available_providers=available_providers,
                    acquisition_transports=acquisition_transports,
                    before_transport=before_transport,
                    provider_calls=provider_calls,
                )
                if navigation_result.get("status") == "custodied":
                    custody_ref = dict(navigation_result["searchos_read_custody_ref"])
                    packet_by_custody_id[custody_ref["read_custody_material_id"]] = dict(
                        navigation_result["fetch_read_content_packet"]
                    )
            elif decision_action is SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY:
                if execute_followup_discover is None:
                    run_kernel.mark_searchos_slot_unresolved(
                        slot_id=slot_id,
                        reason="followup_discover_executor_unavailable",
                    )
                    continue
                iteration = len(iteration_sets) + 2
                try:
                    query_admission = query_authority.admit_searchos_followup_query(
                        judgment_decision=decision,
                        iteration=iteration,
                    )
                    query_plan_action = run_kernel.authorize_query_plan_admission(
                        inputs={
                            "authority": "SearchOSJudgment",
                            "judgment_decision_ref": _decision_ref(decision),
                            "iteration": iteration,
                        }
                    )
                    run_kernel.reduce(
                        Observation.from_action(
                            query_plan_action,
                            observation_type=ObservationType.QUERY_PLAN_ADMITTED,
                            status=RunStageStatus.COMPLETED,
                            payload=query_admission,
                        )
                    )
                except Exception as exc:
                    run_kernel.mark_searchos_slot_stale_or_invalid(
                        slot_id=slot_id,
                        reason=(
                            "followup_query_admission_rejected:"
                            f"{type(exc).__name__}:" + " ".join(str(exc).strip().split())[:120]
                        ),
                    )
                    continue
                before_identities = list(discovery_result_store.identities())
                parent_ref = deepcopy(
                    run_kernel.state.searchos_state["slots_by_id"][slot_id][
                        "current_candidate_state_ref"
                    ]
                )
                wave = dict(
                    execute_followup_discover(
                        decision["followup_query"],
                        iteration,
                        query_admission,
                    )
                )
                after_identities = list(discovery_result_store.identities())
                delta_identities = [item.ref() for item in after_identities[len(before_identities) :]]
                delta_ref = _identity_delta_ref(
                    run_id=run_kernel.state.run_id,
                    iteration=iteration,
                    identity_refs=delta_identities,
                )
                identity_deltas_by_digest[str(delta_ref["identity_set_delta_digest"])] = delta_identities
                wave_packet = dict(wave.get("candidate_packet") or {})
                if wave_packet:
                    wave_packet_ref = search_result_candidate_packet_ref_from_packet(wave_packet)
                    packets_by_id[wave_packet_ref["packet_id"]] = wave_packet
                    candidate_packets.append(wave_packet)
                    selected_refs = _candidate_refs(wave_packet)
                    wave_binding_state = derive_selected_candidate_material_need_bindings(
                        run_kernel=run_kernel,
                        candidate_packet=wave_packet,
                        query_plan=query_authority.plan,
                        discovery_result_store=discovery_result_store,
                    )
                    wave_bindings = _bindings_from_state(wave_binding_state)
                    material_refs = _material_refs(wave_bindings)
                else:
                    selected_refs = []
                    wave_bindings = []
                    material_refs = []
                candidate_set = build_searchos_iteration_candidate_set_v1(
                    run_id=run_kernel.state.run_id,
                    request_id=run_kernel.state.request_id,
                    iteration=iteration,
                    parent_candidate_state_ref=parent_ref,
                    slot_ref=run_kernel.state.searchos_state["slots_by_id"][slot_id]["slot_ref"],
                    query_plan_item_ref=query_admission["query_plan_item_ref"],
                    provider_plan_ref=dict(wave["provider_plan_ref"]),
                    route_refs=list(wave.get("route_refs") or ()),
                    retrieval_action_refs=list(wave.get("retrieval_action_refs") or ()),
                    ordered_provider_result_occurrence_refs=delta_identities,
                    identity_set_delta_ref=delta_ref,
                    selected_candidate_refs=selected_refs,
                    bounded_candidate_material_refs=material_refs,
                    selection_facts=dict(wave.get("selection_facts") or {}),
                    overflow_facts=dict(wave.get("overflow_facts") or {}),
                    zero_useful_result=not bool(selected_refs),
                )
                candidate_action = run_kernel.authorize_searchos_iteration_candidate_admission(
                    candidate_set=candidate_set
                )
                run_kernel.reduce(
                    Observation.from_action(
                        candidate_action,
                        observation_type=(ObservationType.SEARCHOS_ITERATION_CANDIDATES_ADMITTED),
                        status=RunStageStatus.COMPLETED,
                        payload={"candidate_set": candidate_set},
                    )
                )
                iteration_sets.append(candidate_set)
                iteration_ref = deepcopy(
                    run_kernel.state.searchos_state["slots_by_id"][slot_id][
                        "current_candidate_state_ref"
                    ]
                )
                bindings.extend(wave_bindings)
                for binding in wave_bindings:
                    binding_candidate_states[binding.binding_id] = iteration_ref
                for binding in wave_bindings:
                    binding_iteration_refs[binding.binding_id] = iteration_ref
                if wave.get("followup_failure_reason"):
                    run_kernel.mark_searchos_slot_stale_or_invalid(
                        slot_id=slot_id,
                        reason=(
                            "followup_discover_failed:"
                            + str(wave["followup_failure_reason"])
                        )[:240],
                    )
            elif (
                decision_action
                is SearchOSJudgmentAction.PROPOSE_INTERPRETATION_BINDING
            ):
                binding_action = (
                    run_kernel.authorize_searchos_interpretation_binding(
                        judgment_decision=decision
                    )
                )
                run_kernel.reduce(
                    Observation.from_action(
                        binding_action,
                        observation_type=(
                            ObservationType.SEARCHOS_INTERPRETATION_BINDING_ADMITTED
                        ),
                        status=RunStageStatus.COMPLETED,
                        payload={
                            "interpretation_binding": binding_action.inputs[
                                "interpretation_binding"
                            ]
                        },
                    )
                )
            elif (
                decision_action
                is SearchOSJudgmentAction.REQUIRE_CLARIFICATION
            ):
                # The reducer already installed the terminal, slot-local typed
                # clarification posture. No provider, query, or prose action is
                # licensed here.
                continue
            elif decision_action is (SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION):
                handoff_action = run_kernel.authorize_searchos_semantic_handoff(
                    slot_id=slot_id,
                    judgment_decision_ref=decision,
                    read_custody_material_refs=decision["read_custody_refs"],
                )
                run_kernel.reduce(
                    Observation.from_action(
                        handoff_action,
                        observation_type=(ObservationType.SEARCHOS_SEMANTIC_HANDOFF_ADMITTED),
                        status=RunStageStatus.COMPLETED,
                        payload={"semantic_handoff": handoff_action.inputs["semantic_handoff"]},
                    )
                )
                semantic_handoffs.append(deepcopy(handoff_action.inputs["semantic_handoff"]))

    new_semantic_material = _semantic_passages(
        semantic_handoffs=semantic_handoffs[prior_handoff_count:],
        packet_by_custody_id=packet_by_custody_id,
        discovery_result_store=discovery_result_store,
    )
    semantic_material = [
        *(
            [
                deepcopy(dict(item))
                for item in prior_result.searchos_semantic_material
            ]
            if prior_result is not None
            else []
        ),
        *new_semantic_material,
    ]
    append_only_proof = validate_searchos_append_only_lineage(
        revision_1=revision_1,
        initial_query_plan_items=initial_query_items,
        current_query_plan_items=[item.to_dict() for item in query_authority.plan.items],
        initial_identity_refs=initial_identities,
        iteration_candidate_sets=iteration_sets,
        identity_deltas_by_digest=identity_deltas_by_digest,
        current_identity_refs=[item.ref() for item in discovery_result_store.identities()],
    )
    final_state = run_kernel.state.searchos_state
    projection = {
        "schema_version": "searchos_slice_a_product_runtime_v1",
        "owner": "RunKernel.SearchOSIterativeJudgment",
        "revision_1_ref": revision_ref,
        "iteration_candidate_set_refs": deepcopy(final_state["iteration_candidate_set_refs"]),
        "append_only_lineage_proof_ref": {
            "lineage_proof_id": append_only_proof["lineage_proof_id"],
            "lineage_proof_digest": append_only_proof["lineage_proof_digest"],
        },
        "semantic_handoff_refs": deepcopy(final_state["semantic_handoff_refs"]),
        "semantic_material_refs": [
            {
                "source_id": item.get("source_id"),
                "url": item.get("url"),
                "bounded_character_count": len(str(item.get("text") or "")),
                "slot_ref": deepcopy(item.get("searchos_slot_ref")),
            }
            for item in semantic_material
        ],
        "slot_postures": {
            slot_id: final_state["slots_by_id"][slot_id]["posture"] for slot_id in final_state["active_slot_ids"]
        },
        "slot_discovery_job_classes": {
            slot_id: final_state["slots_by_id"][slot_id].get(
                "current_discovery_job_class"
            )
            for slot_id in final_state["active_slot_ids"]
        },
        "semantic_obligation_binding_postures": {
            semantic_obligation_id: dict(obligation).get(
                "binding_posture"
            )
            for semantic_obligation_id, obligation in dict(
                final_state.get("semantic_obligations_by_id") or {}
            ).items()
        },
        "semantic_obligation_clarification_postures": {
            semantic_obligation_id: deepcopy(
                dict(obligation).get("clarification_posture") or {}
            )
            for semantic_obligation_id, obligation in dict(
                final_state.get("semantic_obligations_by_id") or {}
            ).items()
        },
        "interpretation_binding_refs": [
            {
                "interpretation_binding_id": item.get(
                    "interpretation_binding_id"
                ),
                "interpretation_binding_digest": item.get(
                    "interpretation_binding_digest"
                ),
                "semantic_slot_id": dict(
                    item.get("semantic_slot_ref") or {}
                ).get("slot_id"),
            }
            for item in final_state.get("interpretation_binding_history")
            or ()
            if isinstance(item, Mapping)
        ],
        "slot_local_candidate_ancestry_proven": bool(
            append_only_proof.get("slot_local_candidate_ancestry_proven")
        ),
        "peer_slot_cursors_preserved": bool(
            append_only_proof.get("peer_slot_cursors_preserved")
        ),
        "directional_candidate_context_support_eligible": False,
        "read_custody_is_only_support_proposal_eligible_material": True,
        "all_passages_iteration_append_count": 0,
        "standalone_read_assessment_invoked": False,
        "evaluator_invoked_after_first_wave": False,
        "expander_invoked_after_first_wave": False,
        "disambiguation_invoked_after_first_wave": False,
        "weak_corpus_recovery_invoked_after_first_wave": False,
        "ag92b_full_search_judgment_invoked": False,
        "provider_calls_attempted": provider_calls[0],
        "provider_calls_completed": provider_calls[1],
        "recovery_cycle_admission_ref": deepcopy(
            dict(recovery_cycle_ref or {})
        ),
        "searchos_recovery_executed": prior_result is not None,
    }
    return SearchOSSliceAProductResult(
        revision_1=revision_1,
        iteration_candidate_sets=tuple(iteration_sets),
        semantic_handoffs=tuple(semantic_handoffs),
        searchos_semantic_material=tuple(semantic_material),
        projection=projection,
        provider_calls_attempted=provider_calls[0],
        provider_calls_completed=provider_calls[1],
        initial_query_plan_items=tuple(initial_query_items),
        initial_identity_refs=tuple(initial_identities),
        identity_deltas_by_digest={
            key: tuple(deepcopy(dict(item)) for item in values)
            for key, values in identity_deltas_by_digest.items()
        },
        candidate_packets=tuple(
            deepcopy(dict(item)) for item in candidate_packets
        ),
        reusable_read_custody_by_url={
            url: deepcopy(dict(outcome))
            for url, outcome in custody_by_url.items()
        },
    )


def _execute_product_navigation(
    *,
    run_kernel: RunKernel,
    decision: Mapping[str, Any],
    locator_store: navigation_runtime.EphemeralNavigationLocatorStore,
    available_providers: Mapping[str, object],
    acquisition_transports: AcquisitionTransports | None,
    before_transport: Callable[[], Any] | None,
    provider_calls: list[int],
) -> dict[str, Any]:
    action = run_kernel.authorize_searchos_navigation_selection(
        judgment_decision_ref=_decision_ref(decision),
        navigation_candidate=dict(decision["navigation_candidate_ref"]),
    )
    observation = navigation_runtime.execute_navigation_selection(
        action=action,
        authorized_state_snapshot=deepcopy(run_kernel.state.searchos_state),
        locator_store=locator_store,
    )
    run_kernel.reduce(observation)
    if observation.payload.get("outcome") != "admitted_selection":
        return {"status": "selection_not_admitted", "provider_calls_attempted": 0,
                "provider_calls_completed": 0}
    option_id = dict(action.inputs["navigation_option_ref"])["navigation_option_id"]
    option = navigation_runtime.NavigationOption.from_dict(
        dict(run_kernel.state.searchos_state["navigation"]["options_by_id"])[option_id]
    )
    lineage = {
        "slot_ref": dict(action.inputs["slot_ref"]),
        "navigation_option_ref": option.ref(),
        "navigation_selection_ref": dict(option.active_selection_ref),
        "destination_binding_ref": dict(option.destination_binding_ref),
        "parent_read_custody_ref": dict(option.parent_read_custody_ref),
    }
    before = _acquisition_provider_call_totals(run_kernel)
    result: dict[str, Any] | None = None
    try:
        result = navigation_runtime.execute_searchos_navigation_read_to_custody(
            run_kernel=run_kernel,
            locator_store=locator_store,
            navigation_lineage=lineage,
            available_providers=available_providers,
            acquisition_transports=acquisition_transports,
            before_transport=before_transport,
        )
    finally:
        after = _acquisition_provider_call_totals(run_kernel)
        deltas = [max(0, after[index] - before[index]) for index in (0, 1)]
        provider_calls[0] += deltas[0]
        provider_calls[1] += deltas[1]
        returned = ([int(result.get(name) or 0) for name in
                     ("provider_calls_attempted", "provider_calls_completed")]
                    if result else None)
        if returned is not None and deltas != returned:
            raise SearchOSRuntimeError("SearchOS navigation provider-call accounting is stale")
    return result or {}


def revision_1_answer_contract_ref(
    candidate_packet: Mapping[str, Any],
) -> dict[str, Any]:
    ref = candidate_packet.get("answer_contract_ref")
    if not isinstance(ref, Mapping) or not ref:
        raise SearchOSRuntimeError("revision 1 lacks accepted AnswerContract ref")
    contract = dict(ref)
    digest = str(contract.get("contract_digest") or "")
    version = str(contract.get("contract_version") or "")
    if len(digest) != 64 or not version:
        raise SearchOSRuntimeError("revision 1 AnswerContract ref is incomplete")
    return {
        "answer_contract_id": f"accepted-answer-contract:{digest[:24]}",
        "answer_contract_digest": digest,
        "contract_version": version,
        "source": contract.get("source"),
    }


def _active_answer_contract_ref(run_kernel: RunKernel) -> dict[str, Any]:
    contract = dict(
        run_kernel.state.current_answer_contract
        or run_kernel.state.initial_answer_contract
        or {}
    )
    digest = str(contract.get("accepted_contract_digest") or "")
    version = str(contract.get("accepted_contract_version") or "")
    if len(digest) != 64 or not version:
        raise SearchOSRuntimeError(
            "SearchOS initialization lacks accepted AnswerContract identity"
        )
    return {
        "answer_contract_id": f"accepted-answer-contract:{digest[:24]}",
        "answer_contract_digest": digest,
        "contract_version": version,
        "source": (
            "current_answer_contract"
            if run_kernel.state.current_answer_contract
            else "initial_answer_contract"
        ),
    }


def _active_slots(
    run_kernel: RunKernel,
    query_authority: QueryPlanRuntimeAdapter,
    *,
    allow_no_dispatch_planning_snapshot: bool = False,
) -> list[dict[str, Any]]:
    """Join the existing worklist to QueryPlan's exact job/semantic lineage."""

    snapshot = run_kernel.acquisition_authority_snapshot(
        allow_no_dispatch_planning_snapshot=(
            allow_no_dispatch_planning_snapshot
        )
    )
    components = dict(snapshot.get("components_by_id") or {})
    obligations = dict(snapshot.get("source_obligations_by_id") or {})
    accepted_contract = dict(
        run_kernel.state.current_answer_contract
        or run_kernel.state.initial_answer_contract
        or {}
    )
    work_components = list(
        accepted_contract.get("accepted_answer_component_refs") or ()
    )
    obligation_specs = {
        str(item.get("source_obligation_id") or item.get("candidate_id") or ""): dict(item)
        for item in accepted_contract.get("accepted_source_obligation_refs") or ()
        if isinstance(item, Mapping)
        and str(item.get("source_obligation_id") or item.get("candidate_id") or "")
    }
    initial_query_refs = query_authority.plan.execution_item_refs(1)
    query_refs_by_component: dict[str, list[dict[str, Any]]] = {}
    for query_ref in initial_query_refs:
        component_id = str(
            dict(query_ref.get("component_ref") or {}).get("component_id")
            or ""
        )
        if component_id:
            query_refs_by_component.setdefault(component_id, []).append(
                dict(query_ref)
            )
    planning_consumption = dict(
        query_authority.plan.search_work_consumption or {}
    )
    semantic_refs_by_component = {
        str(component_id): [
            dict(item)
            for item in raw_refs
            if isinstance(item, Mapping)
        ]
        for component_id, raw_refs in dict(
            planning_consumption.get("semantic_slot_refs_by_component")
            or {}
        ).items()
        if isinstance(raw_refs, Sequence)
        and not isinstance(raw_refs, (str, bytes))
    }
    clarification_by_component: dict[str, list[dict[str, Any]]] = {}
    for item in planning_consumption.get(
        "clarification_required_semantic_slots"
    ) or ():
        if not isinstance(item, Mapping):
            continue
        clarification = dict(item)
        component_id = str(
            dict(clarification.get("component_ref") or {}).get(
                "component_id"
            )
            or ""
        )
        if component_id:
            clarification_by_component.setdefault(component_id, []).append(
                clarification
            )
    slots: list[dict[str, Any]] = []
    for work_component in work_components:
        if not isinstance(work_component, Mapping):
            continue
        component_id = str(work_component.get("component_id") or "")
        component_ref = dict(components.get(component_id) or {})
        query_refs = query_refs_by_component.get(component_id, [])
        component_semantic_refs = semantic_refs_by_component.get(
            component_id,
            [],
        )
        clarifications = clarification_by_component.get(component_id, [])
        inferred_only = {
            str(item)
            for item in work_component.get("allowed_support_kinds") or ()
        } == {"inferred"}
        if inferred_only and not query_refs and not clarifications:
            continue
        if not component_semantic_refs or (
            not query_refs and not clarifications
        ):
            raise SearchOSRuntimeError(
                "component lacks complete plural semantic acquisition posture"
            )
        semantic_slot_ids = [
            str(item.get("slot_id") or "")
            for item in component_semantic_refs
        ]
        if (
            any(not item for item in semantic_slot_ids)
            or len(set(semantic_slot_ids)) != len(semantic_slot_ids)
        ):
            raise SearchOSRuntimeError(
                "component semantic obligations are missing or duplicated"
            )
        if query_refs:
            job_classes = {
                str(item.get("discovery_job_class") or "")
                for item in query_refs
            }
            semantic_ref_sets = {
                _digest(
                    [
                        dict(ref)
                        for ref in item.get("semantic_slot_refs") or ()
                        if isinstance(ref, Mapping)
                    ]
                )
                for item in query_refs
            }
            if (
                len(job_classes) != 1
                or "" in job_classes
                or len(semantic_ref_sets) != 1
            ):
                raise SearchOSRuntimeError(
                    "component QueryPlan discovery posture is ambiguous"
                )
            discovery_semantic_refs = [
                dict(item)
                for item in query_refs[0].get("semantic_slot_refs") or ()
                if isinstance(item, Mapping)
            ]
            discovery_job_class = next(iter(job_classes))
            posture_component_ref = dict(
                query_refs[0].get("component_ref") or {}
            )
        else:
            discovery_semantic_refs = []
            discovery_job_class = None
            posture_component_ref = dict(
                clarifications[0].get("component_ref") or {}
            )
        discovery_semantic_ids = {
            str(item.get("slot_id") or "")
            for item in discovery_semantic_refs
        }
        clarification_semantic_ids = {
            str(
                dict(item.get("semantic_slot_ref") or {}).get(
                    "slot_id"
                )
                or ""
            )
            for item in clarifications
        }
        if (
            "" in discovery_semantic_ids
            or "" in clarification_semantic_ids
            or not discovery_semantic_ids.issubset(
                set(semantic_slot_ids)
            )
            or not clarification_semantic_ids.issubset(
                set(semantic_slot_ids)
            )
            or discovery_semantic_ids & clarification_semantic_ids
        ):
            raise SearchOSRuntimeError(
                "component semantic acquisition posture crossed accepted slots"
            )
        clarification_by_semantic_id = {
            str(
                dict(item.get("semantic_slot_ref") or {}).get(
                    "slot_id"
                )
                or ""
            ): item
            for item in clarifications
        }
        semantic_obligations = [
            {
                "semantic_slot_ref": semantic_slot_ref,
                "discovery_job_class": (
                    discovery_job_class
                    if semantic_slot_ref["slot_id"]
                    in discovery_semantic_ids
                    else None
                ),
                "acquisition_driving": (
                    semantic_slot_ref["slot_id"]
                    in discovery_semantic_ids
                ),
                "clarification_required": (
                    semantic_slot_ref["slot_id"]
                    in clarification_semantic_ids
                ),
                "clarification_reason": dict(
                    clarification_by_semantic_id.get(
                        semantic_slot_ref["slot_id"],
                        {},
                    )
                ).get("reason"),
            }
            for semantic_slot_ref in component_semantic_refs
        ]
        identity_fields = (
            "component_id",
            "component_revision",
            "component_digest",
        )
        if {
            key: posture_component_ref.get(key) for key in identity_fields
        } != {key: component_ref.get(key) for key in identity_fields}:
            raise SearchOSRuntimeError(
                "QueryPlan component identity differs from acquisition authority"
            )
        requirement = work_component.get("requirement_posture")
        if requirement not in {"required", "optional"}:
            raise SearchOSRuntimeError(
                "accepted component required-versus-optional posture is ambiguous"
            )
        obligation_ids = [
            str(item)
            for item in work_component.get("source_obligation_candidate_ids") or ()
            if str(item)
        ]
        for obligation_id in obligation_ids:
            spec = dict(obligation_specs.get(obligation_id) or {})
            obligation_ref = dict(obligations.get(obligation_id) or {})
            strictness = str(
                spec.get("strictness") or "required"
            )
            if strictness not in {"required", "preferred", "contextual"}:
                raise SearchOSRuntimeError(
                    "source-obligation strictness is ambiguous"
                )
            slot_requirement = (
                "required"
                if requirement == "required" and strictness == "required"
                else "optional"
            )
            slots.append(
                {
                    "slot_id": (
                        "search-judgment-read-slot:"
                        f"{component_id}:{obligation_id}"
                    ),
                    "component_ref": component_ref,
                    "source_obligation_ref": obligation_ref,
                    "requirement_posture": slot_requirement,
                    "support_kind": str(
                        spec.get("kind") or spec.get("obligation_kind") or ""
                    ).strip(),
                    "semantic_obligations": semantic_obligations,
                    "query_plan_item_refs": query_refs,
                    "discovery_job_class": discovery_job_class,
                    "clarification_only": not bool(query_refs),
                }
            )
    if not slots:
        raise SearchOSRuntimeError("SearchOS Slice A has no active component slots")
    return slots


def _bindings_from_state(
    binding_state: Mapping[str, Any],
) -> list[SelectedCandidateMaterialNeedBindingV1]:
    return [
        SelectedCandidateMaterialNeedBindingV1.from_dict(item)
        for item in binding_state.get("bindings") or ()
        if isinstance(item, Mapping)
    ]


def _candidate_refs(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    packet_ref = search_result_candidate_packet_ref_from_packet(packet)
    return [
        {
            "packet_id": packet_ref["packet_id"],
            "packet_digest": packet_ref["packet_digest"],
            "candidate_id": item.get("candidate_id"),
            "candidate_digest": item.get("candidate_digest"),
            "record_digest": item.get("record_digest"),
            "normalized_url": item.get("normalized_url"),
        }
        for item in packet.get("candidate_records") or ()
        if isinstance(item, Mapping)
    ]


def _material_refs(
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for binding in bindings:
        ref = dict(binding.source_material_ref)
        if ref not in refs:
            refs.append(ref)
    return refs


def _candidate_option_inputs(
    *,
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
    slot_ref: Mapping[str, Any],
    binding_candidate_states: Mapping[str, Mapping[str, Any]],
    binding_iteration_refs: Mapping[str, Mapping[str, Any]],
    discovery_result_store: Any,
    binding_slot_id: str | None = None,
) -> list[dict[str, Any]]:
    slot_id = slot_ref.get("slot_id")
    source_slot_id = binding_slot_id or slot_id
    rows: list[dict[str, Any]] = []
    for binding in bindings:
        if binding.slot_id() != source_slot_id:
            continue
        material = discovery_result_store.material_for_ref(binding.source_material_ref)
        if material is None:
            continue
        rows.append(
            {
                "slot_ref": dict(slot_ref),
                "normalized_url": binding.normalized_url,
                "candidate_state_ref": dict(binding_candidate_states[binding.binding_id]),
                "candidate_ref": dict(binding.candidate_ref),
                "query_plan_item_ref": dict(binding.query_plan_item_ref),
                "iteration_set_ref": dict(binding_iteration_refs.get(binding.binding_id) or {}),
                "provider_result_occurrence_ref": dict(binding.contributing_source_result_ref),
                "source_material_ref": dict(binding.source_material_ref),
                "title": str(material.title or "")[:220],
                "snippet": str(material.snippet or "")[:500],
            }
        )
    return rows


def _binding_source_slot_id(slot: Mapping[str, Any]) -> str:
    slot_ref = dict(slot.get("slot_ref") or {})
    if slot.get("prior_slot_absent") is True:
        return (
            "search-judgment-read-slot:"
            f"{slot_ref.get('component_id')}:"
            f"{slot_ref.get('source_obligation_id')}"
        )
    return str(
        dict(slot.get("prior_terminal_slot_ref") or {}).get("slot_id")
        or slot_ref.get("slot_id")
        or ""
    )


def _prepare_candidate_window(
    *,
    slot: Mapping[str, Any],
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
    binding_candidate_states: Mapping[str, Mapping[str, Any]],
    binding_iteration_refs: Mapping[str, Mapping[str, Any]],
    discovery_result_store: Any,
    policy_snapshot: Mapping[str, Any],
    dispositions: Mapping[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any], str | None]:
    option_inputs = _candidate_option_inputs(
        bindings=bindings,
        slot_ref=dict(slot["slot_ref"]),
        binding_candidate_states=binding_candidate_states,
        binding_iteration_refs=binding_iteration_refs,
        discovery_result_store=discovery_result_store,
        binding_slot_id=_binding_source_slot_id(slot),
    )
    options = build_candidate_use_options_v1(option_inputs)
    window_ordinal = max(1, int(slot.get("candidate_window_count") or 0))
    window_dispositions = {
        option_id: disposition
        for option_id, disposition in dispositions.items()
        if disposition in TERMINAL_CANDIDATE_OPTION_DISPOSITIONS
    }
    window = build_candidate_use_window_v1(
        slot_ref=dict(slot["slot_ref"]),
        ordered_options=options,
        window_ordinal=window_ordinal,
        policy_snapshot=policy_snapshot,
        option_dispositions=window_dispositions,
    )
    while (
        window["ordered_candidate_use_option_refs"]
        and all(
            dispositions.get(ref["candidate_use_option_id"])
            in TERMINAL_CANDIDATE_OPTION_DISPOSITIONS
            for ref in window["ordered_candidate_use_option_refs"]
        )
        and window["next_window_available"]
    ):
        window_ordinal += 1
        window = build_candidate_use_window_v1(
            slot_ref=dict(slot["slot_ref"]),
            ordered_options=options,
            window_ordinal=window_ordinal,
            policy_snapshot=policy_snapshot,
            option_dispositions=window_dispositions,
        )
    exhausted = bool(
        window["ordered_candidate_use_option_refs"]
        and all(
            dispositions.get(ref["candidate_use_option_id"])
            in TERMINAL_CANDIDATE_OPTION_DISPOSITIONS
            for ref in window["ordered_candidate_use_option_refs"]
        )
        and not window["next_window_available"]
    )
    reason = None
    if exhausted and not slot.get("custody_refs"):
        reason = (
            "candidate_window_budget_exhausted"
            if window["remaining_option_count"] > 0
            else "candidate_options_exhausted"
        )
    return options, window, reason


def _binding_for_option(
    *,
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
    slot_id: str,
    binding_slot_id: str | None = None,
    option_ref: Mapping[str, Any],
    options: Sequence[Mapping[str, Any]],
) -> SelectedCandidateMaterialNeedBindingV1:
    option = next(
        (item for item in options if item.get("candidate_use_option_id") == option_ref.get("candidate_use_option_id")),
        None,
    )
    if option is None or candidate_use_option_ref(option) != dict(option_ref):
        raise SearchOSRuntimeError("READ option is stale")
    candidate_ids = {
        str(item.get("candidate_id") or "") for item in option.get("candidate_refs") or () if isinstance(item, Mapping)
    }
    binding = next(
        (
            item
            for item in bindings
            if item.slot_id() == (binding_slot_id or slot_id)
            and item.normalized_url == option_ref.get("normalized_url")
            and item.candidate_ref.get("candidate_id") in candidate_ids
        ),
        None,
    )
    if binding is None:
        raise SearchOSRuntimeError("READ option has no current admitted binding")
    return binding


def _build_searchos_judgment_model_input(
    *,
    run_kernel: RunKernel,
    authorized_request: Mapping[str, Any],
    slot_id: str,
    options: Sequence[Mapping[str, Any]],
    window: Mapping[str, Any],
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
    binding_candidate_states: Mapping[str, Mapping[str, Any]],
    binding_iteration_refs: Mapping[str, Mapping[str, Any]],
    discovery_result_store: Any,
    packet_by_custody_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Compose transient need/content input around one authorized ref-only request."""

    request = deepcopy(dict(authorized_request))
    slot = dict(run_kernel.state.searchos_state["slots_by_id"][slot_id])
    active_need = _build_active_need_projection(
        run_kernel=run_kernel,
        slot=slot,
    )
    current_options = {
        str(item.get("candidate_use_option_id") or ""): dict(item)
        for item in options
        if isinstance(item, Mapping)
    }
    rows = _candidate_option_inputs(
        bindings=bindings,
        slot_ref=dict(slot["slot_ref"]),
        binding_candidate_states=binding_candidate_states,
        binding_iteration_refs=binding_iteration_refs,
        discovery_result_store=discovery_result_store,
        binding_slot_id=_binding_source_slot_id(slot),
    )
    directional_by_url: dict[str, dict[str, Any]] = {}
    for row in rows:
        url = str(row.get("normalized_url") or "")
        if url not in directional_by_url:
            directional_by_url[url] = {
                "title": _bounded_judgment_text(row.get("title"), 240),
                "snippet": _bounded_judgment_text(row.get("snippet"), 600),
            }
    directional_contexts: list[dict[str, Any]] = []
    for visible in window.get("model_visible_candidate_use_options") or ():
        visible_mapping = dict(visible) if isinstance(visible, Mapping) else {}
        option_ref = dict(visible_mapping.get("candidate_use_option_ref") or {})
        option_id = str(option_ref.get("candidate_use_option_id") or "")
        option = current_options.get(option_id)
        if option is None or candidate_use_option_ref(option) != option_ref:
            raise SearchOSRuntimeError(
                "transient candidate direction binds a stale lineage snapshot"
            )
        context = directional_by_url.get(str(option.get("normalized_url") or ""), {})
        directional_contexts.append(
            {
                "candidate_use_option_ref": option_ref,
                "normalized_url": option["normalized_url"],
                "title": context.get("title"),
                "snippet": context.get("snippet"),
                "material_authority": "directional_candidate_context",
                "support_proposal_eligible": False,
            }
        )
    read_materials = _build_read_custody_judgment_materials(
        searchos_state=run_kernel.state.searchos_state,
        slot=slot,
        current_options=current_options,
        packet_by_custody_id=packet_by_custody_id,
    )
    if [item["read_custody_ref"] for item in read_materials] != list(
        request.get("read_custody_refs") or ()
    ):
        raise SearchOSRuntimeError(
            "transient READ material does not match authorized custody order"
        )
    core = {
        "schema_version": SEARCHOS_JUDGMENT_MODEL_INPUT_SCHEMA_VERSION,
        "authorized_request": request,
        "active_need": active_need,
        "candidate_directional_contexts": directional_contexts,
        "read_custody_materials": read_materials,
        "decision_contract": build_searchos_judgment_decision_contract_v1(
            navigation_enabled=request.get("schema_version")
            == SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION
        ),
        "bounded_transient_input": True,
        "durable_retention_allowed": False,
    }
    return {**core, "model_input_digest": _digest(core)}


def _build_active_need_projection(
    *,
    run_kernel: RunKernel,
    slot: Mapping[str, Any],
) -> dict[str, Any]:
    slot_ref = dict(slot.get("slot_ref") or {})
    component_ref = dict(slot.get("component_ref") or {})
    obligation_ref = dict(slot.get("source_obligation_ref") or {})
    component_id = str(component_ref.get("component_id") or "")
    obligation_id = str(obligation_ref.get("source_obligation_id") or "")
    if (
        slot_ref.get("component_id") != component_id
        or slot_ref.get("source_obligation_id") != obligation_id
    ):
        raise SearchOSRuntimeError("active slot need lineage is internally stale")

    contract = dict(
        run_kernel.state.current_answer_contract
        or run_kernel.state.initial_answer_contract
        or {}
    )
    accepted = next(
        (
            dict(item)
            for item in contract.get("accepted_answer_component_refs") or ()
            if isinstance(item, Mapping)
            and item.get("component_id") == component_id
        ),
        {},
    )
    accepted_ref = {
        "component_id": accepted.get("component_id"),
        "component_revision": accepted.get("component_revision"),
        "component_digest": accepted.get("component_digest"),
    }
    if accepted_ref != {
        key: component_ref.get(key)
        for key in (
            "component_id",
            "component_revision",
            "component_digest",
        )
    }:
        raise SearchOSRuntimeError(
            "accepted component digest does not match active slot"
        )
    searchos_state = dict(run_kernel.state.searchos_state)
    obligations_by_id = dict(
        searchos_state.get("semantic_obligations_by_id") or {}
    )
    current_discovery_ids = {
        str(item)
        for item in slot.get(
            "current_discovery_semantic_obligation_ids"
        )
        or ()
    }
    semantic_obligation_projections: list[dict[str, Any]] = []
    for raw_semantic_obligation_id in (
        slot.get("semantic_obligation_ids") or ()
    ):
        semantic_obligation_id = str(
            raw_semantic_obligation_id or ""
        )
        semantic_obligation = dict(
            obligations_by_id.get(semantic_obligation_id) or {}
        )
        semantic_slot_ref = dict(
            semantic_obligation.get("semantic_slot_ref") or {}
        )
        if (
            not semantic_obligation_id
            or not semantic_obligation
            or not semantic_slot_ref
        ):
            raise SearchOSRuntimeError(
                "active slot has orphaned semantic-obligation lineage"
            )
        semantic_obligation_ref = {
            "semantic_obligation_id": semantic_obligation_id,
            "semantic_obligation_digest": (
                semantic_obligation.get(
                    "semantic_obligation_digest"
                )
            ),
            "component_id": component_id,
            "semantic_slot_id": semantic_slot_ref.get("slot_id"),
            "schema_version": semantic_obligation.get(
                "schema_version"
            ),
        }
        effective_slot_view = (
            {}
            if slot.get(
                "legacy_semantic_obligations_defaulted"
            )
            is True
            else build_searchos_effective_semantic_slot_view(
                state=searchos_state,
                semantic_slot_id=str(
                    semantic_slot_ref.get("slot_id") or ""
                ),
                component_id=component_id,
                accepted_contract=contract,
            )
        )
        semantic_obligation_projections.append(
            {
                "semantic_obligation_ref": (
                    semantic_obligation_ref
                ),
                "semantic_slot_ref": semantic_slot_ref,
                "effective_semantic_slot_view": (
                    effective_slot_view
                ),
                "acquisition_driving": bool(
                    semantic_obligation.get("acquisition_driving")
                ),
                "current_discovery_target": (
                    semantic_obligation_id in current_discovery_ids
                ),
                "binding_posture": semantic_obligation.get(
                    "binding_posture"
                ),
                "interpretation_binding_ref": dict(
                    semantic_obligation.get(
                        "interpretation_binding_ref"
                    )
                    or {}
                ),
                "clarification_posture": dict(
                    semantic_obligation.get(
                        "clarification_posture"
                    )
                    or {}
                ),
            }
        )
    semantic_slot_projection = {
        "semantic_obligations": semantic_obligation_projections,
        "current_discovery_semantic_obligation_refs": [
            deepcopy(item["semantic_obligation_ref"])
            for item in semantic_obligation_projections
            if item["current_discovery_target"]
        ],
        "current_discovery_job_class": slot.get(
            "current_discovery_job_class"
        ),
        "current_query_plan_item_refs": [
            dict(item)
            for item in slot.get("current_query_plan_item_refs")
            or ()
            if isinstance(item, Mapping)
        ],
    }
    active_recovery_ref = dict(
        searchos_state.get("active_recovery_cycle_ref") or {}
    )
    recovery_admission = next(
        (
            dict(item)
            for item in searchos_state.get(
                "recovery_cycle_admission_history"
            )
            or ()
            if isinstance(item, Mapping)
            and item.get("cycle_id")
            == active_recovery_ref.get("cycle_id")
            and item.get("cycle_admission_digest")
            == active_recovery_ref.get("cycle_admission_digest")
        ),
        {},
    )
    if (
        recovery_admission.get("recovery_classification")
        == "searched_premise"
        and slot_ref.get("recovery_cycle_id")
        == recovery_admission.get("cycle_id")
    ):
        if (
            dict(recovery_admission.get("component_ref") or {})
            != component_ref
            or dict(
                recovery_admission.get("source_obligation_ref") or {}
            )
            != obligation_ref
            or dict(recovery_admission.get("current_contract_ref") or {})
            != dict(searchos_state.get("answer_contract_ref") or {})
        ):
            raise SearchOSRuntimeError(
                "searched recovery active-need authority is stale"
            )
        component_metadata = dict(accepted.get("metadata") or {})
        source_specification = dict(
            component_metadata.get(
                "source_obligation_specification"
            )
            or {}
        )
        requirement = {
            "requirement_id": (
                "searchos-recovery-requirement:"
                + str(recovery_admission["cycle_id"])
            ),
            "component_id": component_id,
            "requirement_summary": _bounded_judgment_text(
                accepted.get("user_facing_question"),
                320,
            ),
            "source_obligation_candidate_ids": [obligation_id],
            "preferred_source_kinds": [
                str(
                    source_specification.get("obligation_kind")
                    or "supporting_fact"
                )
            ],
            "searchos_recovery_cycle_ref": active_recovery_ref,
        }
        return {
            "schema_version": "searchos_active_need_projection_v1",
            "component": {
                "component_ref": component_ref,
                "component_id": component_id,
                "user_facing_question": _bounded_judgment_text(
                    accepted.get("user_facing_question"),
                    500,
                ),
                "user_facing_label": _bounded_judgment_text(
                    accepted.get("user_facing_label"),
                    220,
                ),
                "acceptance_criteria": [
                    _bounded_judgment_text(item, 300)
                    for item in accepted.get("acceptance_criteria") or ()
                    if _bounded_judgment_text(item, 300)
                ],
            },
            "source_obligation": {
                "source_obligation_ref": obligation_ref,
                "obligation_id": obligation_id,
                "kind": str(
                    source_specification.get("obligation_kind")
                    or "supporting_fact"
                ),
                "strictness": str(
                    source_specification.get("strictness")
                    or "required"
                ),
                "currentness_requirement": _bounded_judgment_text(
                    source_specification.get("currentness_requirement"),
                    220,
                ),
                "satisfaction_rule": _bounded_judgment_text(
                    source_specification.get("satisfaction_rule")
                    or requirement["requirement_summary"],
                    320,
                ),
                "requirement_summary": requirement[
                    "requirement_summary"
                ],
                "search_constraint": _bounded_judgment_text(
                    source_specification.get("search_constraint"),
                    240,
                ),
            },
            "search_work": {
                "search_work_plan_ref": {
                    "search_work_plan_id": (
                        "searchos-recovery-work:"
                        + str(recovery_admission["cycle_id"])
                    ),
                    "search_work_plan_digest": str(
                        recovery_admission["cycle_admission_digest"]
                    ),
                    "authority_kind": (
                        "searchos_recovery_cycle_admission"
                    ),
                },
                "search_requirement_ref": requirement,
                "answer_contract_ref": dict(
                    searchos_state["answer_contract_ref"]
                ),
            },
            "slot": {
                "slot_ref": slot_ref,
                "requirement_posture": slot.get(
                    "requirement_posture"
                ),
                "recovery_cycle_ref": active_recovery_ref,
                **semantic_slot_projection,
            },
            "bounded_transient_projection": True,
            "retention_allowed": False,
        }

    zero_result_planning = bool(
        not run_kernel.state.search_executor_handoff_state
        and slot.get("current_candidate_zero_useful_result") is True
    )
    authority = run_kernel.acquisition_authority_snapshot(
        allow_no_dispatch_planning_snapshot=zero_result_planning
    )
    if dict(dict(authority.get("components_by_id") or {}).get(component_id) or {}) != component_ref:
        raise SearchOSRuntimeError("active component ref is stale")
    if dict(dict(authority.get("source_obligations_by_id") or {}).get(obligation_id) or {}) != obligation_ref:
        raise SearchOSRuntimeError("active source-obligation ref is stale")

    accepted = next(
        (
            dict(item)
            for item in contract.get("accepted_answer_component_refs") or ()
            if isinstance(item, Mapping) and item.get("component_id") == component_id
        ),
        {},
    )
    accepted_ref = {
        "component_id": accepted.get("component_id"),
        "component_revision": accepted.get("component_revision"),
        "component_digest": accepted.get("component_digest"),
    }
    if {
        key: accepted_ref.get(key)
        for key in ("component_id", "component_revision", "component_digest")
    } != {
        key: component_ref.get(key)
        for key in ("component_id", "component_revision", "component_digest")
    }:
        raise SearchOSRuntimeError("accepted component ref is stale")
    obligation_spec = next(
        (
            dict(item)
            for item in contract.get("accepted_source_obligation_refs") or ()
            if isinstance(item, Mapping)
            and str(
                item.get("source_obligation_id") or item.get("candidate_id") or ""
            )
            == obligation_id
        ),
        {},
    )
    if not obligation_spec:
        raise SearchOSRuntimeError("accepted source obligation is stale")
    planner_state = dict(run_kernel.state.search_planner_proposal_state or {})
    requirement_refs = [
        dict(item)
        for item in planner_state.get("component_search_requirements") or ()
        if isinstance(item, Mapping)
        and item.get("component_id") == component_id
        and obligation_id
        in set(item.get("source_obligation_candidate_ids") or ())
    ]
    if len(requirement_refs) != 1:
        requirement = {
            "requirement_id": f"searchreq:{component_id}:{obligation_id}",
            "component_id": component_id,
            "source_obligation_candidate_ids": [obligation_id],
            "requirement_summary": (
                accepted.get("user_facing_question")
                or "Find direct support for the accepted component need."
            ),
        }
    else:
        requirement = requirement_refs[0]
    contract_digest = str(contract.get("accepted_contract_digest") or "")
    contract_version = str(contract.get("accepted_contract_version") or "")
    answer_contract_ref = dict(run_kernel.state.searchos_state["answer_contract_ref"])
    if (
        answer_contract_ref.get("answer_contract_digest") != contract_digest
        or str(answer_contract_ref.get("contract_version") or "")
        != contract_version
    ):
        raise SearchOSRuntimeError("SearchOS AnswerContract ref is stale")
    requirement_summary = _bounded_judgment_text(
        requirement.get("requirement_summary"),
        320,
    )
    return {
        "schema_version": "searchos_active_need_projection_v1",
        "component": {
            "component_ref": component_ref,
            "component_id": component_id,
            "user_facing_question": _bounded_judgment_text(
                accepted.get("user_facing_question"),
                500,
            ),
            "user_facing_label": _bounded_judgment_text(
                accepted.get("user_facing_label"),
                220,
            ),
            "acceptance_criteria": [
                _bounded_judgment_text(item, 300)
                for item in accepted.get("acceptance_criteria") or ()
                if _bounded_judgment_text(item, 300)
            ],
        },
        "source_obligation": {
            "source_obligation_ref": obligation_ref,
            "obligation_id": obligation_id,
            "kind": obligation_spec.get("kind")
            or obligation_spec.get("obligation_kind"),
            "strictness": obligation_spec.get("strictness") or "required",
            "currentness_requirement": _bounded_judgment_text(
                obligation_spec.get("currentness_requirement")
                or requirement.get("recency_requirement"),
                220,
            ),
            "satisfaction_rule": _bounded_judgment_text(
                obligation_spec.get("satisfaction_rule") or requirement_summary,
                320,
            ),
            "requirement_summary": requirement_summary,
            "search_constraint": _bounded_judgment_text(
                obligation_spec.get("search_constraint"),
                240,
            ),
        },
        "search_work": {
            "search_requirement_ref": requirement,
            "answer_contract_ref": answer_contract_ref,
        },
        "slot": {
            "slot_ref": slot_ref,
            "requirement_posture": slot.get("requirement_posture"),
            **semantic_slot_projection,
        },
    }


def _build_read_custody_judgment_materials(
    *,
    searchos_state: Mapping[str, Any],
    slot: Mapping[str, Any],
    current_options: Mapping[str, Mapping[str, Any]],
    packet_by_custody_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    materials: list[dict[str, Any]] = []
    slot_ref = dict(slot.get("slot_ref") or {})
    for raw_custody in slot.get("custody_refs") or ():
        custody = dict(raw_custody) if isinstance(raw_custody, Mapping) else {}
        if dict(custody.get("slot_ref") or {}) != slot_ref:
            raise SearchOSRuntimeError("READ custody slot ref is stale")
        if custody.get("origin") == "searchos_navigation":
            custody_id = str(custody.get("read_custody_material_id") or "")
            materials.append(
                navigation_runtime._build_navigation_custody_judgment_material(
                    searchos_state,
                    custody,
                    packet_by_custody_id.get(custody_id) or {},
                )
            )
            continue
        historical_option_ref = dict(custody.get("candidate_use_option_ref") or {})
        option_id = str(historical_option_ref.get("candidate_use_option_id") or "")
        current_option = current_options.get(option_id)
        if current_option is None:
            raise SearchOSRuntimeError("READ custody stable option is no longer current")
        current_option_ref = candidate_use_option_ref(current_option)
        for key in (
            "candidate_use_option_id",
            "candidate_use_option_digest",
            "normalized_url",
            "slot_id",
        ):
            if historical_option_ref.get(key) != current_option_ref.get(key):
                raise SearchOSRuntimeError("READ custody stable option identity mismatch")
        custody_id = str(custody.get("read_custody_material_id") or "")
        packet = validate_fetch_read_content_packet(
            packet_by_custody_id.get(custody_id) or {}
        )
        packet_ref = fetch_read_content_packet_ref_from_packet(packet)
        if packet_ref != dict(custody.get("fetch_read_content_packet_ref") or {}):
            raise SearchOSRuntimeError("READ custody packet ref is stale")
        ledger_custody_ref = dict(
            custody.get("evidence_ledger_custody_ref") or {}
        )
        reference_id = str(ledger_custody_ref.get("reference_id") or "")
        references = [
            dict(item)
            for item in packet.get("reference_records") or ()
            if isinstance(item, Mapping) and item.get("reference_id") == reference_id
        ]
        if len(references) != 1:
            raise SearchOSRuntimeError("READ custody packet candidate binding is ambiguous")
        reference = references[0]
        url = normalize_discovery_result_url(
            reference.get("attempted_url") or reference.get("candidate_url")
        )
        if url != custody.get("normalized_url") or url != current_option.get(
            "normalized_url"
        ):
            raise SearchOSRuntimeError("READ custody URL lineage mismatch")
        bounded_text = str(reference.get("bounded_text") or "")
        bounded_count = int(reference.get("bounded_character_count") or 0)
        if not bounded_text or bounded_count != len(bounded_text):
            raise SearchOSRuntimeError("READ custody bounded text is unreadable")
        if reference.get("excerpt_digest") != _digest(
            {"bounded_text": bounded_text}
        ):
            raise SearchOSRuntimeError("READ custody bounded-text digest mismatch")
        materials.append(
            {
                "schema_version": "searchos_read_custody_judgment_material_v1",
                "slot_ref": slot_ref,
                "stable_candidate_use_option_ref": {
                    key: current_option_ref[key]
                    for key in (
                        "candidate_use_option_id",
                        "candidate_use_option_digest",
                        "normalized_url",
                        "slot_id",
                    )
                },
                "current_candidate_lineage_snapshot_ref": dict(
                    current_option_ref["lineage_snapshot_ref"]
                ),
                "read_custody_ref": custody,
                "fetch_read_content_packet_ref": packet_ref,
                "evidence_ledger_custody_ref": ledger_custody_ref,
                "normalized_url": url,
                "title": _bounded_judgment_text(
                    reference.get("content_title"),
                    300,
                ),
                "bounded_text": bounded_text,
                "bounded_text_digest": reference["excerpt_digest"],
                "bounded_character_count": bounded_count,
                "readability_posture": "readable",
                "completeness_posture": "unknown",
                "truncation_posture": "unknown",
                "same_normalized_url_reused": bool(
                    custody.get("same_normalized_url_reused")
                ),
            }
        )
    return materials


def _bounded_judgment_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text[:limit] or None


def _invoke_judgment_model(
    *,
    model_input: Mapping[str, Any],
    ask_model: Callable[..., Any] | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    measure_context_stage: Callable[..., Any] | None,
    effort: str = "medium",
) -> Any:
    if ask_model is None:
        raise SearchOSRuntimeError("model_unavailable")
    prompt = json.dumps(model_input, sort_keys=True, ensure_ascii=False)
    navigation_request = dict(model_input.get("authorized_request") or {}).get(
        "schema_version"
    ) == SEARCHOS_NAVIGATION_JUDGMENT_REQUEST_SCHEMA_VERSION
    system_prompt = (
        _NAVIGATION_JUDGMENT_SYSTEM_PROMPT
        if navigation_request
        else SEARCHOS_JUDGMENT_SYSTEM_PROMPT
    )
    if measure_context_stage is not None:
        material_count = sum(
            int(item.get("bounded_character_count") or 0)
            for item in model_input.get("read_custody_materials") or ()
            if isinstance(item, Mapping)
        )
        measure_context_stage(
            "searchos_iterative_judgment",
            prompt=json.dumps(
                {
                    "model_input_digest": model_input.get("model_input_digest"),
                    "bounded_character_count": material_count,
                },
                sort_keys=True,
            ),
            system_prompt=None,
            evidence_texts=[],
        )
    return ask_model(
        prompt,
        system_prompt,
        provider=provider,
        model=model,
        effort=effort,
        base_url=base_url,
        api_key=api_key,
        require_json=True,
        use_reasoning=use_reasoning,
    )


def _strict_json_object(raw: Any) -> dict[str, Any]:
    parsed = raw if isinstance(raw, Mapping) else json.loads(str(raw))
    if not isinstance(parsed, Mapping):
        raise SearchOSRuntimeError("model_output_not_object")
    return dict(parsed)


def _failure_reason(exc: Exception) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return "model_output_malformed"
    if isinstance(exc, SearchOSRuntimeError):
        detail = str(exc).strip().casefold().replace(" ", "_")
        return ("model_output_invalid:" + detail)[:240]
    return f"model_transport_failed:{type(exc).__name__}"


def _invalid_or_stale_nomination(exc: Exception) -> bool:
    if not isinstance(exc, SearchOSRuntimeError):
        return False
    detail = str(exc).casefold()
    return any(
        token in detail
        for token in (
            "nomination",
            "outside current candidate window",
            "stale or altered",
        )
    )


def _read_failure_reason(exc: Exception) -> str:
    raw_code = getattr(exc, "code", None)
    code = str(raw_code) if raw_code else type(exc).__name__
    if "transport" in code.casefold():
        posture = "read_transport_failure"
    elif any(
        token in code.casefold()
        for token in ("unreadable", "empty", "content", "material")
    ):
        posture = "read_unusable_or_invalid_material"
    else:
        posture = "read_authority_or_route_blocked"
    return f"{posture}:{code}"[:240]


def _profile_name(value: str) -> str:
    token = str(value or "").strip().casefold()
    return {"fast": "Fast", "balanced": "Balanced", "deep": "Deep"}.get(
        token,
        "Balanced",
    )


def _identity_delta_ref(*, run_id: str, iteration: int, identity_refs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    refs = [deepcopy(dict(item)) for item in identity_refs]
    refs_digest = _digest(refs)
    core = {
        "run_id": run_id,
        "iteration": iteration,
        "identity_count": len(refs),
        "identity_refs_digest": refs_digest,
    }
    digest = _digest(core)
    return {
        "identity_set_delta_id": f"searchos-identity-delta:{digest[:24]}",
        "identity_set_delta_digest": digest,
        **core,
    }


def _decision_ref(decision: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "judgment_decision_id": decision.get("judgment_decision_id"),
        "judgment_decision_digest": decision.get("judgment_decision_digest"),
    }


def _mark_budget_exhausted(run_kernel: RunKernel, slot_id: str) -> None:
    run_kernel.mark_searchos_slot_budget_exhausted(
        slot_id=slot_id,
        reason="judgment_call_budget_exhausted",
    )


def build_searchos_semantic_outcomes_by_slot(
    *,
    searchos_state: Mapping[str, Any],
    semantic_handoffs: Sequence[Mapping[str, Any]],
    searchos_semantic_material: Sequence[Mapping[str, Any]],
    component_admission_projection: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Bind each slot to the exact installed component semantic chain."""

    handoffs = {
        str(dict(item.get("slot_ref") or {}).get("slot_id") or ""): dict(item)
        for item in semantic_handoffs
        if isinstance(item, Mapping)
    }
    admissions_by_component: dict[str, list[dict[str, Any]]] = {}
    for item in (
        component_admission_projection.get("component_admission_refs") or ()
    ):
        if not isinstance(item, Mapping):
            continue
        admissions_by_component.setdefault(
            str(item.get("component_id") or ""),
            [],
        ).append(dict(item))
    material_source_ids_by_slot: dict[str, set[str]] = {}
    for item in searchos_semantic_material:
        if not isinstance(item, Mapping):
            continue
        slot_ref = dict(item.get("searchos_slot_ref") or item.get("slot_ref") or {})
        slot_id = str(slot_ref.get("slot_id") or "")
        source_id = str(item.get("searchos_evidence_ledger_candidate_id") or item.get("source_id") or "")
        if slot_id and source_id:
            material_source_ids_by_slot.setdefault(slot_id, set()).add(source_id)

    outcomes: dict[str, dict[str, Any]] = {}
    slots_by_id = dict(searchos_state.get("slots_by_id") or {})
    for slot_id in searchos_state.get("active_slot_ids") or ():
        slot = dict(slots_by_id.get(slot_id) or {})
        slot_ref = dict(slot.get("slot_ref") or {})
        component_id = str(
            slot_ref.get("component_id") or dict(slot_ref.get("component_ref") or {}).get("component_id") or ""
        )
        handoff = handoffs.get(str(slot_id), {})
        component_admissions = admissions_by_component.get(
            component_id, []
        )
        recovery_admission = next(
            (
                admission
                for admission in reversed(component_admissions)
                if _recovery_admission_matches_slot(
                    admission=admission,
                    slot=slot,
                )
            ),
            {},
        )
        if recovery_admission:
            admission = recovery_admission
            recovery_cycle_ref = dict(
                admission.get("searchos_recovery_cycle_ref") or {}
            )
            recovery_slot_ref = dict(
                slot.get("slot_ref") or {}
            )
            recovery_slot_id = str(
                recovery_slot_ref.get("slot_id")
                or ""
            )
            handoff = handoffs.get(recovery_slot_id, handoff)
            material_slot_id = recovery_slot_id
        else:
            admission = next(
                (
                    candidate
                    for candidate in reversed(component_admissions)
                    if _ordinary_admission_matches_slot(
                        admission=candidate,
                        slot=slot,
                    )
                ),
                {},
            )
            recovery_cycle_ref = {}
            recovery_slot_ref = {}
            material_slot_id = str(slot_id)
        evidence_ids = {
            str(item.get("evidence_ref_id") or "")
            for item in admission.get("evidence_refs") or ()
            if isinstance(item, Mapping)
        }
        consumed_evidence_ids = (
            material_source_ids_by_slot.get(material_slot_id, set())
            & evidence_ids
        )
        material_consumed = bool(consumed_evidence_ids)
        coverage_ref = dict(
            admission.get("component_coverage_ref") or {}
        )
        exact_coverage_chain = _coverage_ref_matches_slot(
            admission=admission,
            slot=slot,
        ) and _coverage_ref_matches_contract_and_candidates(
            coverage_ref=coverage_ref,
            answer_contract_ref=dict(
                searchos_state.get("answer_contract_ref") or {}
            ),
            consumed_candidate_ids=consumed_evidence_ids,
        )
        recovery_evidence_ref = next(
            (
                dict(item)
                for item in admission.get("evidence_refs") or ()
                if isinstance(item, Mapping)
                and str(item.get("evidence_ref_id") or "")
                in consumed_evidence_ids
            ),
            {},
        )
        admitted = bool(
            admission.get("admission_status")
            in {"admitted", "admitted_with_caveats"}
            and material_consumed
            and handoff
            and exact_coverage_chain
        )
        outcomes[str(slot_id)] = {
            "semantic_handoff_ref": (
                {
                    "semantic_handoff_id": handoff.get("semantic_handoff_id"),
                    "semantic_handoff_digest": handoff.get("semantic_handoff_digest"),
                }
                if handoff
                else {}
            ),
            "component_analyst_proposal_ref": (
                dict(admission.get("analyst_finding_ref") or {}) if material_consumed else {}
            ),
            "component_analyst_proposal_status": ("proposed" if material_consumed else "not_proposed"),
            "component_dprime_validation_ref": (
                dict(admission.get("dprime_validation_ref") or {}) if material_consumed else {}
            ),
            "component_dprime_validation_status": ("accepted" if admitted else "not_accepted"),
            "semantic_admission_outcome_ref": (
                {
                    "action_id": admission.get("action_id"),
                    "component_id": admission.get("component_id"),
                    "component_revision": admission.get("component_revision"),
                    "component_digest": admission.get("component_digest"),
                    "admission_status": admission.get("admission_status"),
                    "component_coverage_ref": deepcopy(coverage_ref),
                    "source_requirement_ids": list(
                        coverage_ref.get("source_requirement_ids") or ()
                    ),
                    "source_obligation_id": dict(
                        slot.get("slot_ref") or {}
                    ).get("source_obligation_id"),
                    "consumed_candidate_ids": sorted(
                        consumed_evidence_ids
                    ),
                }
                if admitted
                else {}
            ),
            "semantic_admission_status": "admitted" if admitted else "not_admitted",
            "material_authority": "read_custody_material",
            "searchos_handoff_material_consumed": material_consumed,
            "searchos_recovery_cycle_ref": (
                recovery_cycle_ref
                if recovery_admission and material_consumed
                else {}
            ),
            "searchos_recovery_evidence_ref": (
                recovery_evidence_ref
                if recovery_admission and material_consumed
                else {}
            ),
        }
    return outcomes


def _ordinary_admission_matches_slot(
    *,
    admission: Mapping[str, Any],
    slot: Mapping[str, Any],
) -> bool:
    component_ref = dict(slot.get("component_ref") or {})
    return bool(
        not dict(admission.get("searchos_recovery_cycle_ref") or {})
        and admission.get("component_id") == component_ref.get("component_id")
        and admission.get("component_revision")
        == component_ref.get("component_revision")
        and admission.get("component_digest")
        == component_ref.get("component_digest")
        and _coverage_ref_matches_slot(
            admission=admission,
            slot=slot,
        )
    )


def _unique_tokens(value: Any) -> list[str]:
    tokens = [
        str(item or "").strip()
        for item in value or ()
        if str(item or "").strip()
    ]
    return tokens if len(tokens) == len(set(tokens)) else []


def _coverage_ref_matches_slot(
    *,
    admission: Mapping[str, Any],
    slot: Mapping[str, Any],
) -> bool:
    slot_ref = dict(slot.get("slot_ref") or {})
    component_ref = dict(slot.get("component_ref") or {})
    coverage_ref = dict(
        admission.get("component_coverage_ref") or {}
    )
    target_obligation_id = str(
        slot_ref.get("source_obligation_id") or ""
    )
    source_obligation_ids = _unique_tokens(
        coverage_ref.get("source_obligation_ids")
    )
    source_requirement_ids = _unique_tokens(
        coverage_ref.get("source_requirement_ids")
    )
    owned_links = [
        dict(item)
        for item in coverage_ref.get(
            "owned_requirement_candidate_refs"
        )
        or ()
        if isinstance(item, Mapping)
    ]
    return bool(
        coverage_ref.get("coverage_state") == "satisfied"
        and coverage_ref.get("coverage_record_id")
        and coverage_ref.get("coverage_record_digest")
        and coverage_ref.get("answer_component_id")
        == component_ref.get("component_id")
        == slot_ref.get("component_id")
        and coverage_ref.get("component_revision")
        == component_ref.get("component_revision")
        and coverage_ref.get("component_digest")
        == component_ref.get("component_digest")
        and source_obligation_ids == [target_obligation_id]
        and source_requirement_ids
        and len(owned_links) == len(source_requirement_ids)
        and {
            str(item.get("requirement_id") or "")
            for item in owned_links
        }
        == set(source_requirement_ids)
        and all(
            item.get("source_obligation_id")
            == target_obligation_id
            and item.get("link_status") == "accepted"
            and item.get("candidate_id")
            in set(_unique_tokens(coverage_ref.get("candidate_ids")))
            for item in owned_links
        )
    )


def _coverage_ref_matches_contract_and_candidates(
    *,
    coverage_ref: Mapping[str, Any],
    answer_contract_ref: Mapping[str, Any],
    consumed_candidate_ids: set[str],
) -> bool:
    candidate_ids = set(_unique_tokens(coverage_ref.get("candidate_ids")))
    owned_candidate_ids = {
        str(item.get("candidate_id") or "")
        for item in coverage_ref.get(
            "owned_requirement_candidate_refs"
        )
        or ()
        if isinstance(item, Mapping)
    }
    return bool(
        coverage_ref.get("accepted_contract_version")
        == answer_contract_ref.get("contract_version")
        and coverage_ref.get("accepted_contract_digest")
        == answer_contract_ref.get("answer_contract_digest")
        and consumed_candidate_ids
        and consumed_candidate_ids <= candidate_ids
        and consumed_candidate_ids <= owned_candidate_ids
    )


def _recovery_admission_matches_slot(
    *,
    admission: Mapping[str, Any],
    slot: Mapping[str, Any],
) -> bool:
    slot_ref = dict(slot.get("slot_ref") or {})
    cycle_ref = dict(admission.get("searchos_recovery_cycle_ref") or {})
    slot_cycle = dict(slot.get("recovery_cycle_ref") or {})
    return bool(
        admission.get("admission_status")
        in {"admitted", "admitted_with_caveats"}
        and (
            admission.get("same_component_reassessment") is True
            or admission.get("derived_component_recovery") is True
        )
        and _coverage_ref_matches_slot(
            admission=admission,
            slot=slot,
        )
        and cycle_ref
        and cycle_ref.get("cycle_id")
        == slot_cycle.get("cycle_id")
        == slot_ref.get("recovery_cycle_id")
        and admission.get("component_id")
        == dict(slot.get("component_ref") or {}).get("component_id")
        and admission.get("component_revision")
        == dict(slot.get("component_ref") or {}).get(
            "component_revision"
        )
        and admission.get("component_digest")
        == dict(slot.get("component_ref") or {}).get("component_digest")
        and bool(admission.get("evidence_refs"))
    )


def build_searchos_required_needs_blocked_fap_projection(
    *,
    required_needs_block: Mapping[str, Any],
    readiness_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt the canonical SearchOS block to the installed safe FAP terminal."""

    unresolved = [
        dict(item) for item in required_needs_block.get("unresolved_required_slots") or () if isinstance(item, Mapping)
    ]
    reasons = [
        "SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED:"
        + str(dict(item.get("slot_ref") or {}).get("slot_id") or "unknown-slot")
        + ":"
        + str(item.get("reason") or "unresolved")
        for item in unresolved
    ]
    authority_payload = {
        "status": "blocked",
        "readiness_status": "required_needs_unresolved",
        "readiness_reasons": reasons,
        "author_input_deferred": True,
        "blocked_before_author_input": True,
        "final_answer_posture": "blocked_searchos_required_needs_unresolved",
        "missing_source_obligation_count": len(unresolved),
        "satisfied_source_obligation_count": int(readiness_projection.get("required_ready_count") or 0),
        "final_answer_allowed": False,
        "author_execution_allowed": False,
        "safe_blocked_non_author_terminal": True,
        "searchos_required_needs_block_ref": {
            "block_id": required_needs_block.get("block_id"),
            "block_digest": required_needs_block.get("block_digest"),
            "block_type": required_needs_block.get("block_type"),
        },
    }
    return {
        "schema_version": "searchos_slice_a_blocked_fap_adapter_v1",
        **authority_payload,
        "author_payload_ref": {
            "schema_version": "searchos_slice_a_blocked_author_payload_ref_v1",
            **authority_payload,
            "authority_payload": dict(authority_payload),
        },
    }


def _semantic_passages(
    *,
    semantic_handoffs: Sequence[Mapping[str, Any]],
    packet_by_custody_id: Mapping[str, Mapping[str, Any]],
    discovery_result_store: Any,
) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for handoff in semantic_handoffs:
        for custody in handoff.get("read_custody_material_refs") or ():
            if not isinstance(custody, Mapping):
                continue
            custody_id = str(custody.get("read_custody_material_id") or "")
            packet = packet_by_custody_id.get(custody_id) or {}
            navigation_origin = custody.get("origin") == "searchos_navigation"
            packet_ref: Mapping[str, Any] = {}
            if navigation_origin:
                packet_ref, navigation_reference = navigation_runtime._navigation_custody_packet_reference(custody, packet)
                references: Sequence[Mapping[str, Any]] = (navigation_reference,)
            else:
                packet_ref = fetch_read_content_packet_ref_from_packet(packet)
                references = packet.get("reference_records") or ()
            for reference in references:
                if not isinstance(reference, Mapping):
                    continue
                key = (
                    str(reference.get("reference_id") or ""),
                    str(handoff.get("semantic_handoff_id") or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                source_id = custody.get("evidence_ledger_candidate_id")
                url = (
                    reference.get("canonical_url")
                    or reference.get("final_url")
                    or reference.get("resolved_url")
                    or reference.get("provider_reported_url")
                    or reference.get("attempted_url")
                )
                if navigation_origin:
                    url = normalize_discovery_result_url(url)
                read_source_facts: dict[str, Any] = {}
                source_result_ref = discovery_result_store.ref_for_url(
                    str(url)
                )
                source_material = discovery_result_store.material_for_ref(
                    source_result_ref
                )
                if source_material is not None:
                    read_source_facts.update(
                        dict(source_material.source_facts)
                    )
                tier = classify_source(
                    str(url), str(reference.get("content_title") or "")
                )
                if (
                    tier != "unknown"
                    and not read_source_facts.get("source_tier")
                ):
                    read_source_facts["source_tier"] = tier
                qualification_lineage: dict[str, Any] = {
                    "navigation_origin": navigation_origin,
                    "canonical_candidate_id": source_id,
                    "navigation_content_reference": {
                        key: reference.get(key) for key in ("reference_id", "reference_digest")},
                    "fetch_read_content_packet": {
                        key: packet_ref.get(key) for key in ("packet_id", "packet_digest")},
                    "read_custody_ref": {
                        key: custody.get(key) for key in
                        ("read_custody_material_id", "read_custody_material_digest")},
                    "semantic_handoff_ref": {
                        key: handoff.get(key) for key in
                        ("semantic_handoff_id", "semantic_handoff_digest")},
                    "slot_ref": deepcopy(handoff.get("slot_ref")),
                    "source_facts": {
                        **read_source_facts,
                        "evidence_material_type": "searchos_read_custody",
                        "readable_status": "readable", "fetchable_status": "fetchable",
                    },
                }
                passages.append(
                    {
                        "candidate_id": source_id,
                        **read_source_facts,
                        "source_id": source_id,
                        "searchos_evidence_ledger_candidate_id": source_id,
                        "url": url,
                        "title": reference.get("content_title") or "Read source",
                        "text": reference.get("bounded_text") or "",
                        "score": 1.0,
                        "credibility": 3,
                        "_provider": "searchos_read_custody",
                        "material_authority": "read_custody_material",
                        "searchos_semantic_handoff_ref": {
                            "semantic_handoff_id": handoff.get("semantic_handoff_id"),
                            "semantic_handoff_digest": handoff.get("semantic_handoff_digest"),
                        },
                        "searchos_slot_ref": deepcopy(handoff.get("slot_ref")),
                        "searchos_qualification_lineage": qualification_lineage,
                        "support_admitted": False,
                    }
                )
    return passages


def _acquisition_provider_call_totals(run_kernel: RunKernel) -> tuple[int, int]:
    control = dict(run_kernel.state.acquisition_control_state or {})
    observations = list(
        dict(control.get("execution_observations_by_id") or {}).values()
    )
    return (
        sum(
            int(dict(item).get("provider_calls_attempted") or 0)
            for item in observations
            if isinstance(item, Mapping)
        ),
        sum(
            int(dict(item).get("provider_calls_completed") or 0)
            for item in observations
            if isinstance(item, Mapping)
        ),
    )


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


BOUNDED_SEARCHOS_N1_CAUSAL_PROJECTION_SCHEMA = (
    "bounded_searchos_n1_causal_projection_v1"
)

_SAFE_FAILURE_CLASS_PREFIXES: tuple[tuple[str, str], ...] = (
    ("model_transport_failed", "model_transport_failed"),
    ("model_output_malformed", "model_output_malformed"),
    ("model_output_invalid", "model_output_invalid"),
    ("read_transport_failure", "read_transport_failure"),
    ("read_unusable_or_invalid_material", "read_unusable_or_invalid_material"),
    ("read_authority_or_route_blocked", "read_authority_or_route_blocked"),
)

_SAFE_SUPPORT_KINDS = frozenset(
    {
        "official_current",
        "legal_current_primary",
        "canonical_documentation",
        "source_bound_numeric",
        "peer_reviewed",
        "reputable_secondary",
        "conflict_resolution",
        "date_bound_currentness",
        "user_document",
        "no_special_obligation",
        "not_available",
    }
)

_SAFE_SLOT_POSTURES = frozenset(
    {
        "active_unjudged",
        "awaiting_navigation_admission",
        "awaiting_navigation_execution",
        "awaiting_read",
        "awaiting_followup_discover",
        "ready_for_semantic_evaluation",
        "semantically_handed_off",
        "unresolved_handoff",
        "judgment_failed",
        "budget_exhausted",
        "stale_or_invalid",
    }
)

_SAFE_RECEIVER_FAILURE_CLASSES = frozenset(
    {
        "OrdinaryMulticomponentRuntimeError",
        "SearchOSExistingGapRecoveryError",
        "none",
        "other_safe",
    }
)

# Allowlisted exception-class tokens that can reach ordinary OpenAI SearchJudgment
# transport failures via `_failure_reason()` (`model_transport_failed:<type.__name__>`).
# Built-in TimeoutError/ConnectionError are omitted: the installed OpenAI client path
# surfaces APITimeoutError / APIConnectionError instead.
_SAFE_TRANSPORT_EXCEPTION_CLASSES = frozenset(
    {
        "APITimeoutError",
        "APIConnectionError",
        "RateLimitError",
        "BadRequestError",
        "AuthenticationError",
        "PermissionDeniedError",
        "NotFoundError",
        "ConflictError",
        "UnprocessableEntityError",
        "InternalServerError",
        "APIStatusError",
        "APIError",
        "OpenAIError",
    }
)
_TRANSPORT_FAILURE_PREFIX = "model_transport_failed:"
_MODEL_OUTPUT_INVALID_PREFIX = "model_output_invalid:"

# Closed allowlist: exact normalized `_failure_reason()` suffixes produced from
# fixed `validate_searchos_judgment_model_output` SearchOSRuntimeError messages.
# Unknown / private-looking / future suffixes collapse to other_safe.
_SAFE_MODEL_OUTPUT_INVALID_SUBTYPE_BY_SUFFIX: dict[str, str] = {
    "judgment_request_schema_version_mismatch": "schema_version_mismatch",
    "judgment_output_contains_unsupported_fields": "unsupported_fields",
    "judgment_output_schema_version_mismatch": "schema_version_mismatch",
    "judgment_nomination_is_stale": "request_identity_mismatch",
    "judgment_nomination_slot_is_stale": "slot_identity_mismatch",
    "judgment_action_is_not_in_the_neutral_vocabulary": "action_vocabulary_invalid",
    "judgment_action_is_not_currently_authorized": "action_not_authorized",
    "semantic_handoff_repeats_read_custody": "semantic_handoff_payload_invalid",
    "read_custody_assessment_shape_is_invalid": "custody_assessment_shape_invalid",
    "read_custody_assessment_is_stale_or_altered": "custody_assessment_ref_invalid",
    "read_custody_assessment_disposition_is_invalid": (
        "custody_assessment_disposition_invalid"
    ),
    "read_custody_assessment_repeats_material": "custody_assessment_duplicate",
    "read_nomination_is_outside_current_candidate_window": (
        "read_nomination_outside_window"
    ),
    "read_nomination_ref_is_stale_or_altered": "read_nomination_ref_invalid",
    "read_nomination_contains_incompatible_payload": "read_nomination_payload_invalid",
    "navigation_nomination_requires_navigation_request": "navigation_nomination_invalid",
    "navigation_nomination_is_outside_current_navigation_window": (
        "navigation_nomination_invalid"
    ),
    "navigation_nomination_ref_is_stale_or_altered": "navigation_nomination_invalid",
    "navigation_nomination_contains_incompatible_payload": "navigation_payload_invalid",
    "follow-up_nomination_payload_is_invalid": "followup_payload_invalid",
    "semantic_handoff_requires_exact_read_custody_refs": (
        "semantic_handoff_payload_invalid"
    ),
    "semantic_handoff_nominated_stale_or_altered_read_custody": (
        "semantic_handoff_ref_invalid"
    ),
    "unresolved_handoff_payload_is_invalid": "unresolved_payload_invalid",
    "post-read_action_requires_exact_read_insufficient_assessments": (
        "post_read_assessment_incomplete"
    ),
    "pre-read_action_cannot_assess_custody": "pre_read_assessment_forbidden",
    "navigation_judgment_action_fields_are_not_exact": "exact_action_fields_invalid",
}


def _opaque_identity_digest(token: Any) -> str:
    text = str(token or "").strip()
    if not text:
        return sha256(b"").hexdigest()
    return sha256(text.encode("utf-8")).hexdigest()


def _allowlisted_support_kind(value: Any) -> str:
    token = str(value or "").strip().casefold()
    if token in _SAFE_SUPPORT_KINDS:
        return token
    return "not_available"


def _allowlisted_slot_posture(value: Any) -> str:
    token = str(value or "").strip()
    if token in _SAFE_SLOT_POSTURES:
        return token
    return "stale_or_invalid"


def _project_safe_failure_class(*, posture: str, reason: Any) -> str:
    if posture in {
        "semantically_handed_off",
        "ready_for_semantic_evaluation",
        "active_unjudged",
        "awaiting_read",
        "awaiting_followup_discover",
        "awaiting_navigation_admission",
        "awaiting_navigation_execution",
    }:
        return "none"
    if posture == "budget_exhausted":
        return "budget_exhausted"
    if posture == "unresolved_handoff":
        return "unresolved_handoff"
    if posture == "stale_or_invalid":
        return "stale_or_invalid"
    text = str(reason or "").strip()
    if not text:
        return "other_safe" if posture == "judgment_failed" else "none"
    lowered = text.casefold()
    for prefix, safe_class in _SAFE_FAILURE_CLASS_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + ":") or lowered.startswith(prefix + "_"):
            return safe_class
    if "budget" in lowered and "exhaust" in lowered:
        return "budget_exhausted"
    if "unresolved" in lowered:
        return "unresolved_handoff"
    if "stale" in lowered or "invalid_nomination" in lowered:
        return "stale_or_invalid"
    return "other_safe"


def _extract_transport_exception_class_token(reason: str) -> str | None:
    """Return the first identifier after the transport prefix, else None."""

    if not reason.startswith(_TRANSPORT_FAILURE_PREFIX):
        return None
    remainder = reason[len(_TRANSPORT_FAILURE_PREFIX) :]
    if not remainder:
        return None
    token_chars: list[str] = []
    for index, char in enumerate(remainder):
        if index == 0:
            if not (char.isalpha() or char == "_"):
                return None
            token_chars.append(char)
            continue
        if char.isalnum() or char == "_":
            token_chars.append(char)
            continue
        break
    token = "".join(token_chars)
    return token or None


def _project_safe_transport_exception_class(*, posture: str, reason: Any) -> str:
    """Project an allowlisted transport exception class from canonical SearchOS reason."""

    if _project_safe_failure_class(posture=posture, reason=reason) != "model_transport_failed":
        return "none"
    text = str(reason or "").strip()
    token = _extract_transport_exception_class_token(text)
    if token is None:
        return "other_safe"
    if token in _SAFE_TRANSPORT_EXCEPTION_CLASSES:
        return token
    return "other_safe"


def _project_safe_model_output_invalid_subtype(*, posture: str, reason: Any) -> str:
    """Project a closed safe subtype for model_output_invalid SearchJudgment failures.

    Subtype projection is driven by the canonical ``model_output_invalid:`` reason
    prefix so a known validator cause remains visible when the slot lifecycle
    posture (and therefore ``safe_failure_class``) is ``stale_or_invalid``.
    """

    text = str(reason or "").strip().casefold()
    if text.startswith(_MODEL_OUTPUT_INVALID_PREFIX):
        suffix = text[len(_MODEL_OUTPUT_INVALID_PREFIX) :]
        if not suffix:
            return "other_safe"
        return _SAFE_MODEL_OUTPUT_INVALID_SUBTYPE_BY_SUFFIX.get(suffix, "other_safe")
    if _project_safe_failure_class(posture=posture, reason=reason) != "model_output_invalid":
        return "none"
    return "other_safe"


def _slot_read_custody_observed(record: Mapping[str, Any]) -> bool:
    custody_refs = record.get("custody_refs") or ()
    if isinstance(custody_refs, Sequence) and len(custody_refs) > 0:
        return True
    history = record.get("action_history") or ()
    if not isinstance(history, Sequence):
        return False
    return any(
        isinstance(item, Mapping) and item.get("event") == "read_custody_admitted"
        for item in history
    )


def _slot_judgment_counts(record: Mapping[str, Any]) -> tuple[int, int]:
    history = [
        item for item in (record.get("action_history") or ()) if isinstance(item, Mapping)
    ]
    failure_count = sum(1 for item in history if item.get("event") == "judgment_failed")
    decision_count = sum(
        1
        for item in history
        if item.get("judgment_decision_ref") or item.get("event") == "judgment_failed"
    )
    call_count = int(record.get("judgment_call_count") or 0)
    return max(call_count, decision_count), failure_count


def _project_required_slot_summary(
    *,
    record: Mapping[str, Any],
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    slot_ref = dict(record.get("slot_ref") or {})
    admission_ref = dict(outcome.get("semantic_admission_outcome_ref") or {})
    coverage_ref = dict(admission_ref.get("component_coverage_ref") or {})
    handoff_ref = dict(outcome.get("semantic_handoff_ref") or record.get("semantic_handoff_ref") or {})
    dprime_ref = dict(
        outcome.get("component_dprime_validation_ref")
        or record.get("component_dprime_validation_ref")
        or {}
    )
    final_posture = _allowlisted_slot_posture(record.get("latest_judgment_posture"))
    judgment_event_count, judgment_failure_count = _slot_judgment_counts(record)
    admission_status = str(outcome.get("semantic_admission_status") or "not_admitted")
    if admission_status not in {"admitted", "not_admitted", "admitted_with_caveats"}:
        admission_status = "not_admitted"
    analyst_status = str(outcome.get("component_analyst_proposal_status") or "not_proposed")
    if analyst_status not in {"proposed", "not_proposed"}:
        analyst_status = "not_proposed"
    coverage_satisfied = bool(
        admission_status in {"admitted", "admitted_with_caveats"}
        and (
            coverage_ref.get("coverage_state") == "satisfied"
            or record.get("slice_a_ready") is True
        )
    )
    reason = record.get("latest_judgment_reason")
    safe_failure_class = _project_safe_failure_class(
        posture=final_posture,
        reason=reason,
    )
    return {
        "slot_identity_digest": str(
            slot_ref.get("slot_digest") or _opaque_identity_digest(slot_ref.get("slot_id"))
        ),
        "component_identity_digest": _opaque_identity_digest(slot_ref.get("component_id")),
        "source_obligation_identity_digest": _opaque_identity_digest(
            slot_ref.get("source_obligation_id")
        ),
        "required": True,
        "support_kind": _allowlisted_support_kind(record.get("support_kind")),
        "final_posture": final_posture,
        "safe_failure_class": safe_failure_class,
        "safe_transport_exception_class": _project_safe_transport_exception_class(
            posture=final_posture,
            reason=reason,
        ),
        "safe_model_output_invalid_subtype": _project_safe_model_output_invalid_subtype(
            posture=final_posture,
            reason=reason,
        ),
        "judgment_event_count": judgment_event_count,
        "judgment_failure_count": judgment_failure_count,
        "read_custody_observed": _slot_read_custody_observed(record),
        "semantic_handoff_present": bool(handoff_ref),
        "handoff_material_consumed": bool(
            outcome.get("searchos_handoff_material_consumed") is True
        ),
        "component_analyst_proposal_status": analyst_status,
        "component_dprime_validation_present": bool(dprime_ref),
        "semantic_admission_status": (
            "admitted" if admission_status in {"admitted", "admitted_with_caveats"} else admission_status
        ),
        "component_coverage_satisfied": coverage_satisfied,
    }


def build_bounded_searchos_n1_causal_projection(
    *,
    searchos_slice_a_projection: Mapping[str, Any] | None,
    enabled: bool = True,
) -> dict[str, Any] | None:
    """Project allowlisted SearchOS N=1 causal facts for bounded product output."""

    if not enabled:
        return None
    if not isinstance(searchos_slice_a_projection, Mapping) or not searchos_slice_a_projection:
        return {
            "schema_version": BOUNDED_SEARCHOS_N1_CAUSAL_PROJECTION_SCHEMA,
            "projection_status": "not_applicable",
            "active_slot_count": 0,
            "required_slot_count": 0,
            "all_required_slots_ready": False,
            "component_receiver_selected": False,
            "component_receiver_failure_class": "none",
            "logical_call_correlation": "not_directly_available",
            "slots": [],
        }

    readiness = dict(searchos_slice_a_projection.get("readiness_projection") or {})
    outcomes = dict(searchos_slice_a_projection.get("semantic_outcomes_by_slot") or {})
    slot_records = [
        dict(item)
        for item in readiness.get("slot_records") or ()
        if isinstance(item, Mapping)
    ]
    if not readiness or not slot_records:
        return {
            "schema_version": BOUNDED_SEARCHOS_N1_CAUSAL_PROJECTION_SCHEMA,
            "projection_status": "insufficient",
            "active_slot_count": len(dict(searchos_slice_a_projection.get("slot_postures") or {})),
            "required_slot_count": int(readiness.get("required_slot_count") or 0),
            "all_required_slots_ready": False,
            "component_receiver_selected": False,
            "component_receiver_failure_class": "none",
            "logical_call_correlation": "not_directly_available",
            "slots": [],
        }

    required_records = [
        record
        for record in slot_records
        if str(record.get("requirement_posture") or "") == "required"
    ]
    slots: list[dict[str, Any]] = []
    for record in required_records:
        slot_id = str(dict(record.get("slot_ref") or {}).get("slot_id") or "")
        outcome = dict(outcomes.get(slot_id) or {})
        slots.append(_project_required_slot_summary(record=record, outcome=outcome))

    receiver_failure = searchos_slice_a_projection.get("component_receiver_failure")
    receiver_failure_class = "none"
    if receiver_failure is not None:
        token = str(receiver_failure).strip()
        receiver_failure_class = (
            token if token in _SAFE_RECEIVER_FAILURE_CLASSES else "other_safe"
        )
    receiver_selected = bool(
        receiver_failure is not None
        or any(
            item.get("component_analyst_proposal_status") == "proposed"
            or item.get("semantic_admission_status") == "admitted"
            or item.get("semantic_handoff_present") is True
            for item in slots
        )
        or any(
            str(record.get("latest_judgment_posture") or "")
            in {
                "semantically_handed_off",
                "ready_for_semantic_evaluation",
            }
            for record in required_records
        )
    )

    return {
        "schema_version": BOUNDED_SEARCHOS_N1_CAUSAL_PROJECTION_SCHEMA,
        "projection_status": "available",
        "active_slot_count": int(
            readiness.get("required_slot_count") or 0
        )
        + int(readiness.get("optional_slot_count") or 0),
        "required_slot_count": int(readiness.get("required_slot_count") or len(required_records)),
        "all_required_slots_ready": readiness.get("all_required_slots_slice_a_ready") is True,
        "component_receiver_selected": receiver_selected,
        "component_receiver_failure_class": receiver_failure_class,
        "logical_call_correlation": "not_directly_available",
        "slots": slots,
    }


__all__ = [
    "BOUNDED_SEARCHOS_N1_CAUSAL_PROJECTION_SCHEMA",
    "SEARCHOS_JUDGMENT_DECISION_CONTRACT_SCHEMA_VERSION",
    "SEARCHOS_JUDGMENT_SYSTEM_PROMPT",
    "SEARCHOS_SLICE_A_TRACE_KEY",
    "SEARCHOS_ZERO_RESULT_INITIAL_DISCOVER_WAVE_SCHEMA_VERSION",
    "SearchOSSliceAProductResult",
    "build_bounded_searchos_n1_causal_projection",
    "build_searchos_judgment_decision_contract_v1",
    "build_searchos_zero_result_initial_discover_wave_v1",
    "build_searchos_required_needs_blocked_fap_projection",
    "build_searchos_semantic_outcomes_by_slot",
    "execute_searchos_slice_a_iterative_judgment",
    "execute_searchos_zero_result_orientation",
    "initialize_searchos_clarification_only",
    "validate_searchos_zero_result_initial_discover_wave_v1",
]
