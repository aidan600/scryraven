"""Bounded orchestration adapter for one Scrutineer-originated recovery.

The adapter consumes RunKernel recovery authority and reuses the existing
AnswerContract amendment, SearchPlanner, SearchExecutorHandoff, offline search
execution, candidate/fetch-read, and EvidenceLedger owners.  It does not own
semantic support, component admission, graph authority, or finalization.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.contract_amendment_record import (
    REQUIRED_TO_FULFILL_EXISTING_ACCEPTED_USER_OBLIGATION,
    AffectedComponentRef,
    AmendmentOperation,
    AmendmentOperationKind,
    AmendmentTriggerRefs,
    ContractAmendmentRecord,
    MaterialityPosture,
    ModePermissionPosture,
    MonotonicityPosture,
    ProposalDisposition,
    StaleCoverageCandidatePosture,
    UserConfirmationPosture,
    WeakeningPosture,
)
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
    fetch_read_content_packet_ref_from_packet,
    validate_fetch_read_content_packet,
)
from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
    build_live_search_validation_observation_payload,
)
from core.ordinary_semantic_producer_runtime import BindableFinalPassage
from core.run_kernel import (
    MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE,
    MULTICOMPONENT_RECOVERY_OUTCOME_STAGE,
    Observation,
    ObservationType,
    RunStageStatus,
)
from core.search_executor_handoff_runtime import (
    SearchExecutorHandoffInput,
    execute_search_executor_handoff_action,
    handoff_ref_from_handoff_state,
    planner_ref_from_search_planner_state,
)
from core.search_executor_handoff_runtime import (
    contract_ref_from_contract as handoff_contract_ref_from_contract,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    execute_search_planner_action,
)
from core.search_planner_runtime import (
    contract_ref_from_contract as planner_contract_ref_from_contract,
)
from core.search_result_candidate_packet import (
    build_search_result_candidate_packet_from_live_validation_state,
    search_result_candidate_packet_ref_from_packet,
    validate_search_result_candidate_packet,
)
from core.semantic_contract_foundation import (
    AnswerComponentContract,
    Materiality,
    RequirementPosture,
    SupportKind,
)

MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE = "multicomponent_dynamic_recovery"
MULTICOMPONENT_DYNAMIC_RECOVERY_OWNER = (
    "OrdinaryMulticomponent.DynamicRecoveryAdapter"
)
RECOVERY_STATUS_ACQUIRED = "acquired"
RECOVERY_STATUS_BLOCKED = "blocked"
RECOVERY_DISPOSITION_ACQUIRED = "acquired"
RECOVERY_DISPOSITION_BLOCKED_REQUIRES_CONFIRMATION = (
    "blocked_requires_user_confirmation"
)
RECOVERY_DISPOSITION_BLOCKED_NO_CANDIDATES = "blocked_no_candidates"
RECOVERY_DISPOSITION_BLOCKED_NO_READABLE_EVIDENCE = (
    "blocked_no_readable_evidence"
)
RECOVERY_DISPOSITION_BLOCKED_COMPONENT_ADMISSION = (
    "blocked_component_admission"
)
RECOVERY_DISPOSITION_BLOCKED_RESYNTHESIS = "blocked_resynthesis"
_MAX_RECOVERY_RESULTS = 5


class MulticomponentDynamicRecoveryError(ValueError):
    """Raised when the bounded adapter would cross an authority boundary."""


@dataclass(frozen=True, slots=True)
class RecoveryAmendmentResult:
    component_ref: Mapping[str, Any]
    amendment_record: Mapping[str, Any]
    amendment_admission: Mapping[str, Any]
    amendment_application: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RecoveryAcquisitionResult:
    status: str
    bindable: BindableFinalPassage | None
    projection: Mapping[str, Any]
    blocker: str | None = None
    observed_provider_identities: tuple[str, ...] = ()

    @property
    def acquired(self) -> bool:
        return self.status == RECOVERY_STATUS_ACQUIRED and self.bindable is not None


@dataclass(frozen=True, slots=True)
class _RecoveryPlannerAdapter:
    component_ref: Mapping[str, Any]
    source_obligation_id: str
    search_requirement_id: str
    recovery_authorization_ref: Mapping[str, Any]

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        component = dict(self.component_ref)
        component["semantic_slot_ids"] = ["slot:recovered-component-source-basis"]
        return {
            "question_meaning_summary": (
                "Prepare one targeted ordinary search handoff for the exact "
                "RunKernel-authorized missing component."
            ),
            "requested_output": (
                "Sanitized candidate and bounded fetch/read material only; no answer text."
            ),
            "semantic_slots": [
                {
                    "slot_id": "slot:recovered-component-source-basis",
                    "slot_kind": "source_basis",
                    "status": "explicit",
                    "selected_value": "RunKernel-authorized recovered component source",
                    "materiality": "material",
                }
            ],
            "answer_components": [component],
            "source_obligation_candidates": [
                {
                    "candidate_id": self.source_obligation_id,
                    "obligation_kind": "bounded_current_source_support",
                    "component_candidate_ids": [component["component_id"]],
                    "strictness": "required",
                }
            ],
            "component_search_requirements": [
                {
                    "component_id": component["component_id"],
                    "requirement_id": self.search_requirement_id,
                    "requirement_summary": component["user_facing_question"],
                    "source_obligation_candidate_ids": [
                        self.source_obligation_id
                    ],
                    "preferred_source_kinds": ["official", "primary", "canonical"],
                    "recency_requirement": "current source required",
                    "metadata": {
                        "recovery_authorization_ref": dict(
                            self.recovery_authorization_ref
                        ),
                        "bounded_multicomponent_recovery": True,
                    },
                }
            ],
            "material_ambiguity_posture": "clear",
            "mandatory_caveats": list(component.get("mandatory_caveats") or ()),
            "prohibited_upgrades": list(
                component.get("prohibited_upgrades") or ()
            ),
            "normalization_obligations": [
                "Treat the recovered component question as search direction only."
            ],
            "unsupported_outputs": [
                "Search planning does not create semantic support or admission."
            ],
            "planner_model_metadata": {
                "provider": "deterministic_multicomponent_recovery_adapter",
                "model_adapter_enabled": False,
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "provider_payload_retained": False,
                "prompt_hash": _safe_mapping(
                    planner_input.get("user_query_ref")
                ).get("digest"),
                "front_half_source": MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE,
            },
        }


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any, *, limit: int = 1000) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _identity_token(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _trace_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(payload),
        "trace_only": True,
        "canonical_state": False,
        "final_answer_authority": False,
    }


def reduce_recovery_outcome(
    *,
    run_kernel: Any,
    disposition: str,
    observed_provider_identities: Sequence[str] = (),
    blocker_reason: str | None = None,
) -> dict[str, Any]:
    """Reduce one authority-bearing terminal recovery outcome through RunKernel."""

    action = run_kernel.authorize_multicomponent_recovery_outcome(
        disposition=disposition,
        observed_provider_identities=observed_provider_identities,
        blocker_reason=blocker_reason,
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    return dict(run_kernel.state.projections[MULTICOMPONENT_RECOVERY_OUTCOME_STAGE])


def _observed_provider_identities(
    results: Sequence[Mapping[str, Any]],
    diagnostics: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    providers: list[str] = []
    for value in (
        *[item.get("_provider") for item in results],
        *[item.get("provider") for item in diagnostics],
    ):
        provider = str(value or "").strip().casefold()
        if provider and provider not in providers:
            providers.append(provider)
    return tuple(providers)


def _active_contract(run_kernel: Any) -> dict[str, Any]:
    contract = _safe_mapping(
        run_kernel.state.current_answer_contract
        or run_kernel.state.initial_answer_contract
    )
    if not contract:
        raise MulticomponentDynamicRecoveryError(
            "dynamic recovery requires an accepted AnswerContract"
        )
    return contract


def _recovery_authorization(run_kernel: Any) -> dict[str, Any]:
    authorization = _safe_mapping(
        run_kernel.state.projections.get(
            MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE
        )
    )
    if (
        authorization.get("owner")
        != "RunKernel.MulticomponentRecoveryAuthorization"
        or authorization.get("canonical_state") is not True
        or authorization.get("run_id") != run_kernel.state.run_id
        or authorization.get("request_id") != run_kernel.state.request_id
    ):
        raise MulticomponentDynamicRecoveryError(
            "dynamic recovery requires canonical RunKernel authorization"
        )
    return authorization


def _recovery_authority_inputs(authorization: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "automatic_amendment_authority_class": (
            REQUIRED_TO_FULFILL_EXISTING_ACCEPTED_USER_OBLIGATION
        ),
        "recovery_authorization_id": authorization["authorization_id"],
        "recovery_authorization_digest": authorization["authorization_digest"],
        "recovery_proposal_id": authorization["proposal_id"],
        "recovery_proposal_digest": authorization["proposal_digest"],
        "user_confirmation_posture": (
            REQUIRED_TO_FULFILL_EXISTING_ACCEPTED_USER_OBLIGATION
        ),
    }


def build_recovered_component_amendment(
    *,
    run_kernel: Any,
) -> tuple[AnswerComponentContract, ContractAmendmentRecord]:
    """Build the one passive add-component record from canonical recovery state."""

    authorization = _recovery_authorization(run_kernel)
    parent = _active_contract(run_kernel)
    proposal = _safe_mapping(authorization.get("proposal"))
    proposal_digest = str(authorization["proposal_digest"])
    component_id = f"component:recovered:{proposal_digest[:16]}"
    source_obligation_id = f"source_obligation:recovered:{proposal_digest[:16]}"
    component = AnswerComponentContract(
        component_id=component_id,
        component_revision="1",
        user_facing_label=str(proposal["component_label"]),
        user_facing_question=str(proposal["component_question"]),
        requirement_posture=RequirementPosture.REQUIRED,
        acceptance_criteria=(
            str(proposal["necessity_reason"]),
            "bind any support to bounded EvidenceLedger custody",
        ),
        source_obligation_candidate_ids=(source_obligation_id,),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        mandatory_caveats=tuple(proposal.get("caveats") or ()),
        prohibited_upgrades=(
            "Do not broaden the accepted topic or requested deliverable.",
            "Do not treat search candidates as semantic support.",
        ),
        materiality=Materiality.MATERIAL,
        metadata={
            "recovery_proposal_id": authorization["proposal_id"],
            "recovery_target_kind": authorization["target_kind"],
            "recovery_target_key": authorization["target_key"],
        },
    )
    component_payload = component.to_dict()
    operation = AmendmentOperation(
        operation_id=f"operation:add-recovered-component:{proposal_digest[:16]}",
        operation_kind=AmendmentOperationKind.ADD_COMPONENT,
        operation_payload={"component": component_payload},
        notes=(
            "Add one subordinate component required by the accepted synthesis directive.",
        ),
        metadata={
            "recovery_authorization_id": authorization["authorization_id"],
            "automatic_amendment_authority_class": (
                REQUIRED_TO_FULFILL_EXISTING_ACCEPTED_USER_OBLIGATION
            ),
        },
    )
    affected = AffectedComponentRef(
        component_id=component.component_id,
        component_revision=component.component_revision,
        component_digest=str(component.component_digest),
        relationship="new_required_subordinate_component",
    )
    version = str(parent["accepted_contract_version"])
    record = ContractAmendmentRecord(
        amendment_record_id=f"amendment:recovery:{proposal_digest[:20]}",
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        request_digest=str(
            parent.get("parent_question_meaning_record_digest")
            or _digest({"request_id": run_kernel.state.request_id})
        ),
        parent_contract_version=version,
        parent_contract_digest=str(parent["accepted_contract_digest"]),
        parent_question_meaning_record_id=parent.get(
            "parent_question_meaning_record_id"
        ),
        parent_question_meaning_record_digest=parent.get(
            "parent_question_meaning_record_digest"
        ),
        accepted_contract_ref=f"contract:{version}:accepted",
        trigger_refs=AmendmentTriggerRefs(
            gap_refs=(str(authorization["proposal_id"]),),
            metadata={
                "recovery_authorization_id": authorization["authorization_id"],
                "recovery_authorization_digest": authorization[
                    "authorization_digest"
                ],
                "scrutineer_artifact_digest": authorization[
                    "scrutineer_artifact_digest"
                ],
                "graph_digest": authorization["graph_digest"],
            },
        ),
        operations=(operation,),
        affected_component_refs=(affected,),
        materiality=MaterialityPosture.MATERIAL,
        user_confirmation_posture=(
            UserConfirmationPosture.REQUIRED_TO_FULFILL_EXISTING_ACCEPTED_USER_OBLIGATION
        ),
        monotonicity=MonotonicityPosture.STRENGTHENS,
        weakening_posture=WeakeningPosture.NONE,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE,
        stale_coverage_candidate_posture=(
            StaleCoverageCandidatePosture.CANDIDATE_STALE
        ),
        required_caveats=tuple(proposal.get("caveats") or ()),
        prohibited_upgrades=(
            "No unrelated material amendment is authorized.",
            "No accepted obligation or user constraint may be weakened.",
        ),
        metadata={
            "automatic_amendment_authority_class": (
                REQUIRED_TO_FULFILL_EXISTING_ACCEPTED_USER_OBLIGATION
            ),
            "recovery_proposal_id": authorization["proposal_id"],
        },
    ).require_valid()
    return component, record


def apply_recovered_component_amendment(
    *,
    run_kernel: Any,
) -> RecoveryAmendmentResult:
    """Admit and apply the passive record through the existing RunKernel owners."""

    if run_kernel.state.contract_amendment_application_history:
        raise MulticomponentDynamicRecoveryError(
            "dynamic recovery permits exactly one AnswerContract amendment"
        )
    authorization = _recovery_authorization(run_kernel)
    component, record = build_recovered_component_amendment(
        run_kernel=run_kernel
    )
    authority_inputs = _recovery_authority_inputs(authorization)
    admission_action = run_kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        parent_contract_digest=record.parent_contract_digest,
        parent_contract_version=record.parent_contract_version,
        inputs=authority_inputs,
    )
    run_kernel.reduce(
        Observation.from_action(
            admission_action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={"contract_amendment_record": record.to_dict()},
        )
    )
    admission = dict(run_kernel.state.contract_amendment_admission_projection)
    application_action = run_kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=str(admission["admission_digest"]),
        inputs=authority_inputs,
    )
    run_kernel.reduce(
        Observation.from_action(
            application_action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    current = _active_contract(run_kernel)
    component_ref = next(
        dict(item)
        for item in current.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping)
        and item.get("component_id") == component.component_id
    )
    return RecoveryAmendmentResult(
        component_ref=component_ref,
        amendment_record=record.to_dict(),
        amendment_admission=admission,
        amendment_application=dict(
            run_kernel.state.contract_amendment_application_projection
        ),
    )


def _source_refs_from_contract(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for component in contract.get("accepted_answer_component_refs") or ():
        if not isinstance(component, Mapping):
            continue
        component_id = component.get("component_id")
        for candidate_id in component.get("source_obligation_candidate_ids") or ():
            refs.append(
                {
                    "candidate_id": candidate_id,
                    "obligation_kind": "bounded_current_source_support",
                    "component_candidate_ids": [component_id],
                    "strictness": "required",
                }
            )
    return refs


def _reduce_recovery_planner(
    *,
    run_kernel: Any,
    component_ref: Mapping[str, Any],
    authorization: Mapping[str, Any],
) -> str:
    source_ids = list(component_ref.get("source_obligation_candidate_ids") or ())
    if len(source_ids) != 1:
        raise MulticomponentDynamicRecoveryError(
            "recovered component requires one source obligation"
        )
    source_id = str(source_ids[0])
    requirement_id = f"search-requirement:recovery:{authorization['proposal_digest'][:16]}"
    planner_input = SearchPlannerInput(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        user_query_text=str(component_ref["user_facing_question"]),
        requested_mode="balanced",
        safe_context={
            "phase": "AG-MULTICOMPONENT-DYNAMIC-GRAPH-RECOVERY-01",
            "runtime_parallelism": False,
            "recovery_round": 1,
        },
        route_context_ref={"route_ref": MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE},
        run_context_ref={"run_kernel_consumer": MULTICOMPONENT_DYNAMIC_RECOVERY_OWNER},
        parent_initial_contract_ref=planner_contract_ref_from_contract(
            run_kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=planner_contract_ref_from_contract(
            run_kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )
    action = run_kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
        inputs={
            "multicomponent_recovery_authorization_id": authorization[
                "authorization_id"
            ],
        },
    )
    result = execute_search_planner_action(
        action=action,
        planner_input=planner_input,
        adapter=_RecoveryPlannerAdapter(
            component_ref=component_ref,
            source_obligation_id=source_id,
            search_requirement_id=requirement_id,
            recovery_authorization_ref={
                "authorization_id": authorization["authorization_id"],
                "authorization_digest": authorization["authorization_digest"],
            },
        ),
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
            status=RunStageStatus.COMPLETED,
            payload=result.observation_payload,
        )
    )
    return requirement_id


def _reduce_recovery_handoff(*, run_kernel: Any) -> None:
    current = _active_contract(run_kernel)
    planner_state = run_kernel.state.search_planner_proposal_state
    handoff_input = SearchExecutorHandoffInput(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        parent_current_contract_ref=handoff_contract_ref_from_contract(
            current,
            source="current_answer_contract",
        ),
        parent_initial_contract_ref=handoff_contract_ref_from_contract(
            run_kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        contract_parent_kind="current_answer_contract",
        parent_search_planner_proposal_ref=planner_ref_from_search_planner_state(
            planner_state
        ),
        answer_component_refs=current.get("accepted_answer_component_refs", []),
        source_obligation_candidate_refs=_source_refs_from_contract(current),
        component_search_requirements=planner_state.get(
            "component_search_requirements", []
        ),
        required_caveats=current.get("mandatory_caveats", []),
        prohibited_upgrades=current.get("prohibited_upgrades", []),
        query_budget={"max_search_tasks": 1, "max_results_per_task": 5},
        allowed_verticals=["search"],
        provider_preference_hint=None,
    )
    action = run_kernel.authorize_search_executor_handoff()
    result = execute_search_executor_handoff_action(
        action=action,
        handoff_input=handoff_input,
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_EXECUTOR_HANDOFF_CREATED,
            status=RunStageStatus.COMPLETED,
            payload=result.observation_payload,
        )
    )


def _selected_task(run_kernel: Any) -> dict[str, Any]:
    state = _safe_mapping(run_kernel.state.search_executor_handoff_state)
    tasks = [
        dict(item)
        for item in state.get("search_task_records") or ()
        if isinstance(item, Mapping)
    ]
    if len(tasks) != 1:
        raise MulticomponentDynamicRecoveryError(
            "recovery SearchExecutorHandoff must select exactly one task"
        )
    return tasks[0]


def _fetch_materials(
    results: Sequence[Mapping[str, Any]],
    candidate_packet: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    candidates = [
        dict(item)
        for item in candidate_packet.get("candidate_records") or ()
        if isinstance(item, Mapping)
    ]
    if len(results) != len(candidates):
        raise MulticomponentDynamicRecoveryError(
            "recovery candidate/fetch material count mismatch"
        )
    materials: list[dict[str, Any]] = []
    for result, candidate in zip(results, candidates, strict=True):
        bounded_text = _clean_text(result.get("text"), limit=20_000)
        materials.append(
            {
                "candidate_id": candidate.get("candidate_id"),
                "candidate_digest": candidate.get("candidate_digest"),
                "fetch_read_status": (
                    "readable"
                    if bounded_text
                    and str(result.get("readable_status") or "readable").casefold()
                    in {"readable", "available", "ok"}
                    else "unreadable"
                ),
                "attempted_url": candidate.get("url"),
                "resolved_url": candidate.get("url"),
                "final_url": candidate.get("url"),
                "canonical_url": candidate.get("url"),
                "resolved_domain": candidate.get("domain"),
                "content_type": "text/html",
                "http_status": 200 if bounded_text else None,
                "retrieved_or_observed_at": (
                    "offline-ordinary-dispatcher-observation"
                ),
                "content_title": candidate.get("title"),
                "bounded_text": bounded_text,
                "bounded_text_sanitized": True,
                "bounded_text_bounded": True,
                "failure_reason": None if bounded_text else "no readable bounded text",
            }
        )
    return tuple(materials)


def _validated_recovery_obligation_lineage(
    *,
    run_kernel: Any,
    component_ref: Mapping[str, Any],
    source_obligation_id: str,
    search_requirement_id: str,
    authorization: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify the exact obligation identity before any EvidenceLedger link."""

    current = _active_contract(run_kernel)
    current_components = [
        dict(item)
        for item in current.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping)
        and item.get("component_id") == component_ref.get("component_id")
    ]
    if len(current_components) != 1:
        raise MulticomponentDynamicRecoveryError(
            "recovered obligation requires one current component binding"
        )
    current_component = current_components[0]
    for key in ("component_id", "component_revision", "component_digest"):
        if current_component.get(key) != component_ref.get(key):
            raise MulticomponentDynamicRecoveryError(
                "recovered obligation component binding became stale"
            )
    source_ids = [
        str(item)
        for item in current_component.get("source_obligation_candidate_ids") or ()
        if str(item or "").strip()
    ]
    if source_ids != [source_obligation_id]:
        raise MulticomponentDynamicRecoveryError(
            "recovered obligation source identity became stale"
        )
    if (
        authorization.get("authorization_id")
        != _recovery_authorization(run_kernel).get("authorization_id")
        or authorization.get("authorization_digest")
        != _recovery_authorization(run_kernel).get("authorization_digest")
        or authorization.get("search_authorized") is not True
    ):
        raise MulticomponentDynamicRecoveryError(
            "recovered obligation authorization binding became stale"
        )

    planner = _safe_mapping(run_kernel.state.search_planner_proposal_state)
    planner_requirements = [
        dict(item)
        for item in planner.get("component_search_requirements") or ()
        if isinstance(item, Mapping)
        and item.get("component_id") == current_component["component_id"]
        and item.get("requirement_id") == search_requirement_id
        and list(item.get("source_obligation_candidate_ids") or ())
        == [source_obligation_id]
    ]
    if (
        planner.get("run_id") != run_kernel.state.run_id
        or planner.get("request_id") != run_kernel.state.request_id
        or len(planner_requirements) != 1
    ):
        raise MulticomponentDynamicRecoveryError(
            "recovered obligation planner lineage is not exact"
        )
    planner_authorization = _safe_mapping(
        _safe_mapping(planner_requirements[0].get("metadata")).get(
            "recovery_authorization_ref"
        )
    )
    if (
        planner_authorization.get("authorization_id")
        != authorization.get("authorization_id")
        or planner_authorization.get("authorization_digest")
        != authorization.get("authorization_digest")
    ):
        raise MulticomponentDynamicRecoveryError(
            "recovered obligation planner authorization lineage is not exact"
        )

    handoff = _safe_mapping(run_kernel.state.search_executor_handoff_state)
    tasks = [
        dict(item)
        for item in handoff.get("search_task_records") or ()
        if isinstance(item, Mapping)
        and item.get("component_id") == current_component["component_id"]
        and list(item.get("source_obligation_candidate_ids") or ())
        == [source_obligation_id]
    ]
    parent = _safe_mapping(handoff.get("parent_current_contract_ref"))
    if (
        handoff.get("run_id") != run_kernel.state.run_id
        or handoff.get("request_id") != run_kernel.state.request_id
        or parent.get("contract_version")
        != current.get("accepted_contract_version")
        or parent.get("contract_digest")
        != current.get("accepted_contract_digest")
        or len(tasks) != 1
    ):
        raise MulticomponentDynamicRecoveryError(
            "recovered obligation handoff lineage is not exact"
        )
    return {
        "component_id": current_component["component_id"],
        "source_obligation_id": source_obligation_id,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "answer_contract_version": current["accepted_contract_version"],
        "answer_contract_digest": current["accepted_contract_digest"],
        "recovery_authorization_id": authorization["authorization_id"],
        "recovery_authorization_digest": authorization["authorization_digest"],
    }


def _promote_recovery_candidate_custody(
    *,
    run_kernel: Any,
    component_ref: Mapping[str, Any],
    source_obligation_id: str,
    search_requirement_id: str,
    authorization: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    candidate_packet: Mapping[str, Any],
) -> dict[str, Any]:
    exact_lineage = _validated_recovery_obligation_lineage(
        run_kernel=run_kernel,
        component_ref=component_ref,
        source_obligation_id=source_obligation_id,
        search_requirement_id=search_requirement_id,
        authorization=authorization,
    )
    candidate_records = [
        dict(item)
        for item in candidate_packet.get("candidate_records") or ()
        if isinstance(item, Mapping)
    ]
    promoted: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for result, candidate in zip(results, candidate_records, strict=True):
        readable = bool(_clean_text(result.get("text"), limit=20_000)) and str(
            result.get("readable_status") or "readable"
        ).casefold() in {"readable", "available", "ok"}
        linked_requirement_ids = list(
            dict.fromkeys([source_obligation_id, search_requirement_id])
        )
        promoted.append(
            {
                "candidate_id": candidate["candidate_id"],
                "url": candidate.get("url"),
                "domain": candidate.get("domain"),
                "title": candidate.get("title"),
                "record_kind": "fact",
                "disposition": "accepted" if readable else "unfetchable",
                "readable_status": "readable" if readable else "unreadable",
                "fetchable_status": "fetchable" if readable else "unfetchable",
                "currentness_signal": result.get("currentness_signal") or "current",
                "source_class": result.get("source_class"),
                "source_tier": result.get("source_tier"),
                "provider_name": result.get("_provider"),
                "provider_role": "multicomponent_recovery_diagnostic",
                "eligible_for_stronger_obligation": readable,
                "final_evidence_eligible": readable,
                "evidence_material_type": "answer_bearing_content",
                "requirement_id": source_obligation_id,
                "source_obligation_candidate_ids": linked_requirement_ids,
            }
        )
        links.extend(
            {
                "requirement_id": requirement_id,
                "candidate_id": candidate["candidate_id"],
                "link_reason": (
                    "RunKernel-authorized recovered component acquisition"
                ),
                "link_status": "accepted" if readable else "unfetchable",
            }
            for requirement_id in linked_requirement_ids
        )
    payload = {
        "observation_id": (
            f"{run_kernel.state.run_id}:evidence-ledger:multicomponent-recovery"
        ),
        "observation_source": "multicomponent_recovery_candidate_admission",
        "requirements": [
            {
                "requirement_id": source_obligation_id,
                "requirement_kind": "bounded_current_source_support",
                "origin_ref": "multicomponent_recovery_exact_source_obligation",
                **exact_lineage,
                "required_source_class": next(
                    (
                        item.get("source_class")
                        for item in results
                        if item.get("source_class")
                    ),
                    None,
                ),
                "required_evidence_material_type": "answer_bearing_content",
            },
            {
                "requirement_id": search_requirement_id,
                "requirement_kind": "recovery_search_requirement",
                "origin_ref": "multicomponent_recovery_exact_search_requirement",
                **exact_lineage,
                "required_evidence_material_type": "answer_bearing_content",
            },
        ],
        "candidates": promoted,
        "requirement_links": links,
    }
    action = run_kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": payload["observation_source"],
            "candidate_count": len(promoted),
            "requirement_count": 2,
        }
    )
    result = execute_evidence_ledger_reduction_action(action, payload=payload)
    run_kernel.reduce(result.observation)
    return run_kernel.state.evidence_ledger.to_projection().to_dict()


def execute_recovery_acquisition(
    *,
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    component_ref: Mapping[str, Any],
) -> RecoveryAcquisitionResult:
    """Execute exactly one offline ordinary acquisition attempt."""

    authorization = _recovery_authorization(run_kernel)
    search_requirement_id = _reduce_recovery_planner(
        run_kernel=run_kernel,
        component_ref=component_ref,
        authorization=authorization,
    )
    _reduce_recovery_handoff(run_kernel=run_kernel)
    task = _selected_task(run_kernel)
    deps = runtime_scope.get("deps")
    execute_search = runtime_scope.get("process_search_queries") or getattr(
        deps,
        "process_search_queries",
        None,
    )
    if not callable(execute_search):
        raise MulticomponentDynamicRecoveryError(
            "ordinary offline search execution boundary is unavailable"
        )
    query_text = str(
        task.get("safe_query_text")
        or task.get("query_text")
        or task.get("query")
        or component_ref["user_facing_question"]
    )
    recovery_provider_diagnostics: list[dict[str, Any]] = []
    seen_urls = runtime_scope.get("seen_urls")
    if not isinstance(seen_urls, set):
        seen_urls = set()
    collected_images = runtime_scope.get("collected_images")
    if not isinstance(collected_images, set):
        collected_images = set()
    raw_results = execute_search(
        [query_text],
        str(runtime_scope.get("intent") or "general"),
        str(runtime_scope.get("complexity") or "medium"),
        str(runtime_scope.get("search_depth") or "basic"),
        _MAX_RECOVERY_RESULTS,
        list(runtime_scope.get("include_domains") or ()),
        list(runtime_scope.get("exclude_domains") or ()),
        runtime_scope.get("query_embedding"),
        seen_urls,
        collected_images,
        str(runtime_scope.get("embed_provider") or ""),
        str(runtime_scope.get("embed_model") or ""),
        runtime_scope.get("local_url"),
        runtime_scope.get("embed_texts") or getattr(deps, "embed_texts", None),
        getattr(deps, "compute_similarities", None),
        status_container=runtime_scope.get("status"),
        provider_diagnostics=recovery_provider_diagnostics,
        provider_role="multicomponent_recovery_diagnostic",
    )
    all_results = [
        dict(item)
        for item in raw_results or ()
        if isinstance(item, Mapping)
    ][:_MAX_RECOVERY_RESULTS]
    observed_providers = _observed_provider_identities(
        all_results,
        recovery_provider_diagnostics,
    )
    selected_provider = next(
        (
            str(item.get("_provider") or "").strip().casefold()
            for item in all_results
            if item.get("_provider")
        ),
        observed_providers[0] if observed_providers else None,
    )
    if not selected_provider:
        raise MulticomponentDynamicRecoveryError(
            "ordinary recovery dispatcher did not expose a provider identity"
        )
    results = [
        item
        for item in all_results
        if str(item.get("_provider") or "").strip().casefold()
        == selected_provider
    ]
    base_projection = _trace_projection({
        "schema_version": "multicomponent_dynamic_recovery_v1",
        "owner": MULTICOMPONENT_DYNAMIC_RECOVERY_OWNER,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "recovery_authorization_id": authorization["authorization_id"],
        "component_id": component_ref["component_id"],
        "ordinary_search_planner_ref": planner_ref_from_search_planner_state(
            run_kernel.state.search_planner_proposal_state
        ),
        "ordinary_search_executor_handoff_ref": handoff_ref_from_handoff_state(
            run_kernel.state.search_executor_handoff_state
        ),
        "selected_search_task_ids": [task["search_task_id"]],
        "ordinary_acquisition_attempt_count": 1,
        "runtime_parallelism": False,
        "direct_semantic_producer_used": False,
        "observed_provider_identities": list(observed_providers),
    })

    current = _active_contract(run_kernel)
    selected_task_id = str(task["search_task_id"])
    live_action = run_kernel.authorize_live_search_validation(
        selected_search_task_ids=[selected_task_id],
        provider_authorized=selected_provider,
        provider_call_cap=1,
        results_per_task_cap=max(1, len(results)),
        parent_current_contract_version=current["accepted_contract_version"],
        parent_current_contract_digest=current["accepted_contract_digest"],
        handoff_id=run_kernel.state.search_executor_handoff_state["handoff_id"],
        handoff_digest=run_kernel.state.search_executor_handoff_state[
            "handoff_digest"
        ],
    )
    live_payload = build_live_search_validation_observation_payload(
        action=live_action,
        current_answer_contract=current,
        search_executor_handoff_state=run_kernel.state.search_executor_handoff_state,
        provider_used=selected_provider,
        provider_results_by_task={selected_task_id: results},
        execution_mode=LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
        broker_invoked=False,
        live_provider_called=False,
    )
    run_kernel.reduce(
        Observation.from_action(
            live_action,
            observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
            status=RunStageStatus.COMPLETED,
            payload=live_payload,
        )
    )
    candidate_packet = validate_search_result_candidate_packet(
        build_search_result_candidate_packet_from_live_validation_state(
            run_kernel.state.live_search_validation_state
        )
    )
    if not results:
        projection = _trace_projection({
            **base_projection,
            "status": RECOVERY_STATUS_BLOCKED,
            "blocker": "no recovery search candidates were returned",
            "pending_recovery_disposition": (
                RECOVERY_DISPOSITION_BLOCKED_NO_CANDIDATES
            ),
            "candidate_count": 0,
            "search_result_candidate_packet_ref": (
                search_result_candidate_packet_ref_from_packet(candidate_packet)
            ),
        })
        run_kernel.state.projections[MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE] = projection
        return RecoveryAcquisitionResult(
            status=RECOVERY_STATUS_BLOCKED,
            bindable=None,
            projection=projection,
            blocker=str(projection["blocker"]),
            observed_provider_identities=observed_providers,
        )
    fetch_packet = validate_fetch_read_content_packet(
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            _fetch_materials(results, candidate_packet),
        )
    )
    reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=run_kernel,
        fetch_read_content_packet=fetch_packet,
        observation_id=(
            f"{run_kernel.state.run_id}:evidence-ledger:multicomponent-recovery-fetch"
        ),
    )
    source_ids = list(component_ref.get("source_obligation_candidate_ids") or ())
    ledger = _promote_recovery_candidate_custody(
        run_kernel=run_kernel,
        component_ref=component_ref,
        source_obligation_id=str(source_ids[0]),
        search_requirement_id=search_requirement_id,
        authorization=authorization,
        results=results,
        candidate_packet=candidate_packet,
    )
    candidate_by_id = {
        _identity_token(item["candidate_id"]): dict(item)
        for item in ledger.get("candidate_records") or ()
        if isinstance(item, Mapping) and item.get("candidate_id")
    }
    readable_ref = next(
        (
            dict(item)
            for item in fetch_packet.get("reference_records") or ()
            if isinstance(item, Mapping)
            and item.get("fetch_read_status") == "readable"
            and _identity_token(item.get("candidate_id")) in candidate_by_id
        ),
        None,
    )
    if readable_ref is None:
        projection = _trace_projection({
            **base_projection,
            "status": RECOVERY_STATUS_BLOCKED,
            "blocker": "no legitimate readable recovery evidence was admitted",
            "pending_recovery_disposition": (
                RECOVERY_DISPOSITION_BLOCKED_NO_READABLE_EVIDENCE
            ),
            "candidate_count": len(results),
            "search_result_candidate_packet_ref": (
                search_result_candidate_packet_ref_from_packet(candidate_packet)
            ),
            "fetch_read_content_packet_ref": (
                fetch_read_content_packet_ref_from_packet(fetch_packet)
            ),
        })
        run_kernel.state.projections[MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE] = projection
        return RecoveryAcquisitionResult(
            status=RECOVERY_STATUS_BLOCKED,
            bindable=None,
            projection=projection,
            blocker=str(projection["blocker"]),
            observed_provider_identities=observed_providers,
        )
    candidate_token = _identity_token(readable_ref["candidate_id"])
    candidate_id = str(candidate_by_id[candidate_token]["candidate_id"])
    result_index = next(
        index
        for index, candidate in enumerate(candidate_packet["candidate_records"])
        if _identity_token(candidate["candidate_id"]) == candidate_token
    )
    selected_result = results[result_index]
    bindable = BindableFinalPassage(
        passage={
            **selected_result,
            "text": selected_result.get("text"),
            "url": readable_ref.get("candidate_url") or selected_result.get("url"),
            "title": readable_ref.get("candidate_title") or selected_result.get("title"),
        },
        evidence_ref_id=candidate_id,
        candidate_record=candidate_by_id[candidate_token],
    )
    projection = _trace_projection({
        **base_projection,
        "status": RECOVERY_STATUS_ACQUIRED,
        "candidate_count": len(results),
        "selected_evidence_ref_id": candidate_id,
        "search_result_candidate_packet_ref": (
            search_result_candidate_packet_ref_from_packet(candidate_packet)
        ),
        "fetch_read_content_packet_ref": (
            fetch_read_content_packet_ref_from_packet(fetch_packet)
        ),
        "evidence_ledger_owner": ledger.get("owner"),
        "evidence_ledger_candidate_count": ledger.get("candidate_count"),
        "raw_provider_payload_retained": False,
    })
    run_kernel.state.projections[MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE] = projection
    return RecoveryAcquisitionResult(
        status=RECOVERY_STATUS_ACQUIRED,
        bindable=bindable,
        projection=projection,
        observed_provider_identities=observed_providers,
    )


__all__ = [
    "MULTICOMPONENT_DYNAMIC_RECOVERY_OWNER",
    "MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE",
    "RECOVERY_DISPOSITION_ACQUIRED",
    "RECOVERY_DISPOSITION_BLOCKED_COMPONENT_ADMISSION",
    "RECOVERY_DISPOSITION_BLOCKED_NO_CANDIDATES",
    "RECOVERY_DISPOSITION_BLOCKED_NO_READABLE_EVIDENCE",
    "RECOVERY_DISPOSITION_BLOCKED_REQUIRES_CONFIRMATION",
    "RECOVERY_DISPOSITION_BLOCKED_RESYNTHESIS",
    "RECOVERY_STATUS_ACQUIRED",
    "RECOVERY_STATUS_BLOCKED",
    "MulticomponentDynamicRecoveryError",
    "RecoveryAcquisitionResult",
    "RecoveryAmendmentResult",
    "apply_recovered_component_amendment",
    "build_recovered_component_amendment",
    "execute_recovery_acquisition",
    "reduce_recovery_outcome",
]
