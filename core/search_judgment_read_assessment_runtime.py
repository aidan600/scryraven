"""Subordinate SearchJudgment READ assessment and ordinary custody composition.

This module owns the narrow post-DISCOVER material-need judgment installed by
SEARCHOS-READ-SOURCE-AND-CUSTODY-01.  Bindings and committed RunKernel state are
reference-only.  DISCOVER material is assembled transiently for one strict
model call and is never retained here.  A successful READ ends at candidate
content custody; it creates no evidence, support, satisfaction, continuation,
citation, sufficiency, answer, or author authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from core.acquisition_adapters import AcquisitionTransports
from core.acquisition_contracts import AcquisitionArtifact
from core.acquisition_control import (
    AcquisitionNeedProposalV1,
    stable_json_digest,
)
from core.authorized_acquisition_runtime import (
    execute_acquisition_custody_authorization_action,
    execute_acquisition_work_order_to_terminal,
)
from core.discovery_source_result import (
    DiscoveryResultMaterialStore,
    normalize_discovery_result_url,
)
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
    fetch_read_content_packet_ref_from_packet,
    select_bounded_answer_bearing_text,
    validate_fetch_read_content_packet,
)
from core.query_plan import QueryPlan
from core.run_kernel import (
    SEARCH_JUDGMENT_READ_ASSESSMENT_STAGE,
    SEARCH_JUDGMENT_READ_BINDING_STAGE,
    SEARCH_JUDGMENT_READ_CUSTODY_STAGE,
    SEARCH_JUDGMENT_READ_PROPOSAL_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
    validate_authorized_action,
)
from core.search_planner_runtime import contract_ref_from_contract
from core.search_result_candidate_packet import (
    ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_REVISION,
    SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER,
    search_result_candidate_packet_ref_from_packet,
    validate_ordinary_search_result_candidate_packet,
)

SEARCH_JUDGMENT_READ_POLICY_SCHEMA_VERSION = (
    "search_judgment_read_assessment_policy_v1"
)
SELECTED_CANDIDATE_MATERIAL_NEED_BINDING_SCHEMA_VERSION = (
    "selected_candidate_material_need_binding_v1"
)
SEARCH_JUDGMENT_READ_BINDING_SET_SCHEMA_VERSION = (
    "search_judgment_read_binding_set_v1"
)
SEARCH_JUDGMENT_READ_ASSESSMENT_SCHEMA_VERSION = (
    "search_judgment_read_assessment_v1"
)
SEARCH_JUDGMENT_READ_STATE_SCHEMA_VERSION = (
    "runkernel_search_judgment_read_state_v1"
)
SEARCH_JUDGMENT_READ_CUSTODY_EVENT_SCHEMA_VERSION = (
    "search_judgment_read_custody_event_v1"
)
SEARCH_JUDGMENT_READ_PROPOSAL_EVENT_SCHEMA_VERSION = (
    "search_judgment_read_proposal_event_v1"
)
SEARCH_JUDGMENT_READ_TRACE_KEY = "search_judgment_read_assessment"
SEARCH_JUDGMENT_READ_COST_PHASE = "search_judgment_read_assessment"
SEARCH_JUDGMENT_READ_PRODUCER_SURFACE = (
    "core.search_judgment_read_assessment_runtime"
)
SEARCH_JUDGMENT_READ_SLOT_BUDGET_EXCEEDED = (
    "search_judgment_read_assessment_slot_budget_exceeded"
)

SEARCH_JUDGMENT_READ_SYSTEM_PROMPT = """You are the subordinate SearchJudgment READ assessor.
Decide only whether the active source-obligation slot needs one full-page READ
of one listed binding. Candidate rank orders input but never implies need.
Return exactly one JSON object and no prose:
{\"schema_version\":\"search_judgment_read_assessment_decision_v1\",\"decision\":\"NO_READ\",\"reason_code\":\"bounded_token\"}
or
{\"schema_version\":\"search_judgment_read_assessment_decision_v1\",\"decision\":\"REQUEST_READ_PAGE\",\"nominated_binding_id\":\"exact listed id\",\"reason_code\":\"bounded_token\"}
Do not decide evidence, support, satisfaction, continuation, recovery, stopping,
citations, sufficiency, answer content, or provider selection."""

_MODEL_DECISION_SCHEMA_VERSION = "search_judgment_read_assessment_decision_v1"
_DECISIONS = frozenset({"NO_READ", "REQUEST_READ_PAGE"})
class SearchJudgmentReadAssessmentError(ValueError):
    """Fail-closed binding, assessment, proposal, or custody error."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True, slots=True)
class SearchJudgmentReadAssessmentPolicyV1:
    """Versioned bounds for the one-slot assessment checkpoint."""

    maximum_bindings_shown: int = 12
    maximum_bounded_material_characters_per_binding: int = 1_200
    maximum_logical_read_assessments_per_checkpoint_run: int = 8
    maximum_nominated_reads_per_active_slot: int = 1
    schema_version: str = SEARCH_JUDGMENT_READ_POLICY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "maximum_bindings_shown": self.maximum_bindings_shown,
            "maximum_bounded_material_characters_per_binding": (
                self.maximum_bounded_material_characters_per_binding
            ),
            "maximum_logical_read_assessments_per_checkpoint_run": (
                self.maximum_logical_read_assessments_per_checkpoint_run
            ),
            "maximum_nominated_reads_per_active_slot": (
                self.maximum_nominated_reads_per_active_slot
            ),
            "call_unit": "one_active_component_source_obligation_slot",
            "candidate_rank_is_activation_or_nomination_authority": False,
        }

    def ref(self) -> dict[str, Any]:
        payload = self.to_dict()
        return {
            "schema_version": self.schema_version,
            "policy_digest": stable_json_digest(payload),
            "maximum_bindings_shown": self.maximum_bindings_shown,
            "maximum_bounded_material_characters_per_binding": (
                self.maximum_bounded_material_characters_per_binding
            ),
            "maximum_logical_read_assessments_per_checkpoint_run": (
                self.maximum_logical_read_assessments_per_checkpoint_run
            ),
            "maximum_nominated_reads_per_active_slot": (
                self.maximum_nominated_reads_per_active_slot
            ),
        }


SEARCH_JUDGMENT_READ_ASSESSMENT_POLICY = SearchJudgmentReadAssessmentPolicyV1()


@dataclass(frozen=True, slots=True)
class SelectedCandidateMaterialNeedBindingV1:
    binding_id: str
    binding_digest: str
    run_id: str
    request_id: str
    answer_contract_ref: Mapping[str, Any]
    component_ref: Mapping[str, Any]
    source_obligation_ref: Mapping[str, Any]
    search_work_plan_ref: Mapping[str, Any]
    search_requirement_ref: Mapping[str, Any]
    query_plan_ref: Mapping[str, Any]
    query_plan_item_ref: Mapping[str, Any]
    contributing_source_result_ref: Mapping[str, Any]
    source_material_ref: Mapping[str, Any]
    candidate_packet_ref: Mapping[str, Any]
    candidate_ref: Mapping[str, Any]
    normalized_url: str
    selected_candidate_rank: int
    provider_call_ordinal: int
    provider_result_rank: int
    material_class: str
    source_obligation_kind: str
    source_obligation_strictness: str
    schema_version: str = SELECTED_CANDIDATE_MATERIAL_NEED_BINDING_SCHEMA_VERSION

    @classmethod
    def create(cls, **values: Any) -> "SelectedCandidateMaterialNeedBindingV1":
        core = {
            "schema_version": SELECTED_CANDIDATE_MATERIAL_NEED_BINDING_SCHEMA_VERSION,
            **{key: _json_clone(value) for key, value in values.items()},
            "binding_posture": "eligible_for_semantic_read_assessment_only",
            "read_need_decided": False,
            "evidence_created": False,
            "semantic_support_created": False,
            "source_obligation_satisfied": False,
        }
        digest = stable_json_digest(core)
        source_id = str(
            _mapping(core.get("contributing_source_result_ref")).get(
                "source_result_id"
            )
            or "source"
        )
        component_id = str(
            _mapping(core.get("component_ref")).get("component_id") or "component"
        )
        obligation_id = str(
            _mapping(core.get("source_obligation_ref")).get(
                "source_obligation_id"
            )
            or "obligation"
        )
        payload = {
            **core,
            "binding_id": (
                "selected-candidate-material-need-binding:"
                f"{component_id}:{obligation_id}:{source_id}:{digest[:16]}"
            ),
            "binding_digest": digest,
        }
        return cls.from_dict(payload)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "SelectedCandidateMaterialNeedBindingV1":
        raw = _mapping(value)
        allowed = {
            "schema_version",
            "binding_id",
            "binding_digest",
            "run_id",
            "request_id",
            "answer_contract_ref",
            "component_ref",
            "source_obligation_ref",
            "search_work_plan_ref",
            "search_requirement_ref",
            "query_plan_ref",
            "query_plan_item_ref",
            "contributing_source_result_ref",
            "source_material_ref",
            "candidate_packet_ref",
            "candidate_ref",
            "normalized_url",
            "selected_candidate_rank",
            "provider_call_ordinal",
            "provider_result_rank",
            "material_class",
            "source_obligation_kind",
            "source_obligation_strictness",
            "binding_posture",
            "read_need_decided",
            "evidence_created",
            "semantic_support_created",
            "source_obligation_satisfied",
        }
        if set(raw).difference(allowed):
            raise SearchJudgmentReadAssessmentError("binding_unknown_fields")
        if raw.get("schema_version") != (
            SELECTED_CANDIDATE_MATERIAL_NEED_BINDING_SCHEMA_VERSION
        ):
            raise SearchJudgmentReadAssessmentError("binding_schema_invalid")
        if raw.get("binding_posture") != (
            "eligible_for_semantic_read_assessment_only"
        ):
            raise SearchJudgmentReadAssessmentError("binding_posture_invalid")
        for key in (
            "read_need_decided",
            "evidence_created",
            "semantic_support_created",
            "source_obligation_satisfied",
        ):
            if raw.get(key) is not False:
                raise SearchJudgmentReadAssessmentError("binding_authority_open")
        core = {
            key: _json_clone(raw.get(key))
            for key in allowed
            if key not in {"binding_id", "binding_digest"}
        }
        digest = stable_json_digest(core)
        if raw.get("binding_digest") != digest:
            raise SearchJudgmentReadAssessmentError("binding_digest_mismatch")
        required_maps = (
            "answer_contract_ref",
            "component_ref",
            "source_obligation_ref",
            "search_work_plan_ref",
            "search_requirement_ref",
            "query_plan_ref",
            "query_plan_item_ref",
            "contributing_source_result_ref",
            "source_material_ref",
            "candidate_packet_ref",
            "candidate_ref",
        )
        if any(not _mapping(raw.get(key)) for key in required_maps):
            raise SearchJudgmentReadAssessmentError("binding_ref_missing")
        url = normalize_discovery_result_url(str(raw.get("normalized_url") or ""))
        source_id = str(
            _mapping(raw.get("contributing_source_result_ref")).get(
                "source_result_id"
            )
            or "source"
        )
        component_id = str(_mapping(raw.get("component_ref")).get("component_id"))
        obligation_component_ids = {
            str(value)
            for value in _sequence(
                _mapping(raw.get("source_obligation_ref")).get("component_ids")
            )
            if str(value)
        }
        if component_id not in obligation_component_ids:
            raise SearchJudgmentReadAssessmentError(
                "binding_component_not_in_source_obligation"
            )
        obligation_id = str(
            _mapping(raw.get("source_obligation_ref")).get(
                "source_obligation_id"
            )
        )
        expected_id = (
            "selected-candidate-material-need-binding:"
            f"{component_id}:{obligation_id}:{source_id}:{digest[:16]}"
        )
        if raw.get("binding_id") != expected_id:
            raise SearchJudgmentReadAssessmentError("binding_id_mismatch")
        return cls(
            binding_id=expected_id,
            binding_digest=digest,
            run_id=_required_text(raw.get("run_id"), "binding_run_id_missing"),
            request_id=_required_text(
                raw.get("request_id"), "binding_request_id_missing"
            ),
            answer_contract_ref=_mapping(raw.get("answer_contract_ref")),
            component_ref=_mapping(raw.get("component_ref")),
            source_obligation_ref=_mapping(raw.get("source_obligation_ref")),
            search_work_plan_ref=_mapping(raw.get("search_work_plan_ref")),
            search_requirement_ref=_mapping(raw.get("search_requirement_ref")),
            query_plan_ref=_mapping(raw.get("query_plan_ref")),
            query_plan_item_ref=_mapping(raw.get("query_plan_item_ref")),
            contributing_source_result_ref=_mapping(
                raw.get("contributing_source_result_ref")
            ),
            source_material_ref=_mapping(raw.get("source_material_ref")),
            candidate_packet_ref=_mapping(raw.get("candidate_packet_ref")),
            candidate_ref=_mapping(raw.get("candidate_ref")),
            normalized_url=url,
            selected_candidate_rank=_positive_int(
                raw.get("selected_candidate_rank"), "binding_rank_invalid"
            ),
            provider_call_ordinal=_positive_int(
                raw.get("provider_call_ordinal"), "binding_call_ordinal_invalid"
            ),
            provider_result_rank=_positive_int(
                raw.get("provider_result_rank"), "binding_result_rank_invalid"
            ),
            material_class=_required_text(
                raw.get("material_class"), "binding_material_class_missing"
            ),
            source_obligation_kind=_required_text(
                raw.get("source_obligation_kind"), "binding_obligation_kind_missing"
            ),
            source_obligation_strictness=_required_text(
                raw.get("source_obligation_strictness"),
                "binding_obligation_strictness_missing",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "binding_id": self.binding_id,
            "binding_digest": self.binding_digest,
            "run_id": self.run_id,
            "request_id": self.request_id,
            "answer_contract_ref": _json_clone(self.answer_contract_ref),
            "component_ref": _json_clone(self.component_ref),
            "source_obligation_ref": _json_clone(self.source_obligation_ref),
            "search_work_plan_ref": _json_clone(self.search_work_plan_ref),
            "search_requirement_ref": _json_clone(self.search_requirement_ref),
            "query_plan_ref": _json_clone(self.query_plan_ref),
            "query_plan_item_ref": _json_clone(self.query_plan_item_ref),
            "contributing_source_result_ref": _json_clone(
                self.contributing_source_result_ref
            ),
            "source_material_ref": _json_clone(self.source_material_ref),
            "candidate_packet_ref": _json_clone(self.candidate_packet_ref),
            "candidate_ref": _json_clone(self.candidate_ref),
            "normalized_url": self.normalized_url,
            "selected_candidate_rank": self.selected_candidate_rank,
            "provider_call_ordinal": self.provider_call_ordinal,
            "provider_result_rank": self.provider_result_rank,
            "material_class": self.material_class,
            "source_obligation_kind": self.source_obligation_kind,
            "source_obligation_strictness": self.source_obligation_strictness,
            "binding_posture": "eligible_for_semantic_read_assessment_only",
            "read_need_decided": False,
            "evidence_created": False,
            "semantic_support_created": False,
            "source_obligation_satisfied": False,
        }

    def ref(self) -> dict[str, str]:
        return {
            "binding_id": self.binding_id,
            "binding_digest": self.binding_digest,
        }

    def slot_id(self) -> str:
        return _slot_id(self.component_ref, self.source_obligation_ref)


@dataclass(frozen=True, slots=True)
class SearchJudgmentReadRuntimeResult:
    projection: Mapping[str, Any]
    fetch_read_content_packets: tuple[Mapping[str, Any], ...] = ()
    provider_calls_attempted: int = 0
    provider_calls_completed: int = 0


def derive_selected_candidate_material_need_bindings(
    *,
    run_kernel: RunKernel,
    candidate_packet: Mapping[str, Any],
    query_plan: QueryPlan,
    discovery_result_store: DiscoveryResultMaterialStore,
    policy: SearchJudgmentReadAssessmentPolicyV1 = (
        SEARCH_JUDGMENT_READ_ASSESSMENT_POLICY
    ),
) -> dict[str, Any]:
    """Derive exact current text-free bindings from canonical owners."""

    packet = validate_ordinary_search_result_candidate_packet(candidate_packet)
    if packet.get("packet_revision") != (
        ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_REVISION
    ):
        raise SearchJudgmentReadAssessmentError("candidate_packet_revision_stale")
    if packet.get("origin_kind") != (
        SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER
    ):
        raise SearchJudgmentReadAssessmentError("candidate_packet_origin_invalid")
    if packet.get("run_id") != run_kernel.state.run_id:
        raise SearchJudgmentReadAssessmentError("candidate_packet_run_stale")
    if packet.get("request_id") != run_kernel.state.request_id:
        raise SearchJudgmentReadAssessmentError("candidate_packet_request_stale")

    active_contract, active_contract_ref = _active_contract(run_kernel)
    if _mapping(packet.get("answer_contract_ref")) != active_contract_ref:
        raise SearchJudgmentReadAssessmentError("candidate_packet_contract_stale")
    handoff_packet_ref = _mapping(
        run_kernel.state.projections.get("ordinary_discovery_candidate_handoff", {})
    ).get("search_result_candidate_packet_ref")
    packet_ref = search_result_candidate_packet_ref_from_packet(packet)
    if _mapping(handoff_packet_ref) != packet_ref:
        raise SearchJudgmentReadAssessmentError("candidate_packet_handoff_stale")
    packet_handoff_ref = _mapping(packet.get("search_executor_handoff_ref"))
    if query_plan.to_ref() != _mapping(packet_handoff_ref.get("query_plan_ref")):
        raise SearchJudgmentReadAssessmentError("candidate_packet_query_plan_stale")
    if discovery_result_store.identity_set_ref() != _mapping(
        packet.get("source_result_identity_set_ref")
    ):
        raise SearchJudgmentReadAssessmentError("candidate_packet_contributors_stale")

    search_work_plan = _mapping(run_kernel.state.search_work_plan)
    if not search_work_plan:
        raise SearchJudgmentReadAssessmentError("search_work_plan_missing")
    accepted_ref = _mapping(
        _mapping(search_work_plan.get("metadata")).get("accepted_contract_ref")
    )
    if not _search_work_plan_contract_ref_matches(
        accepted_ref,
        active_contract_ref=active_contract_ref,
    ):
        raise SearchJudgmentReadAssessmentError("search_work_plan_contract_stale")
    search_work_plan_ref = _search_work_plan_ref(search_work_plan)
    try:
        authority_snapshot = run_kernel.acquisition_authority_snapshot()
    except RunKernelTransitionError as exc:
        raise SearchJudgmentReadAssessmentError(str(exc)) from exc
    canonical_obligations = _mapping(
        authority_snapshot.get("source_obligations_by_id")
    )

    contract_components = {
        str(_mapping(item).get("component_id")): _mapping(item)
        for item in _sequence(active_contract.get("accepted_answer_component_refs"))
        if _mapping(item).get("component_id")
    }
    work_components = {
        str(_mapping(item).get("component_id")): _mapping(item)
        for item in _sequence(search_work_plan.get("components"))
        if _mapping(item).get("component_id")
    }
    current_items = {
        str(item.to_ref(query_plan.plan_id).get("query_plan_item_id")): item
        for item in query_plan.items
        if item.authorized_query
    }
    current_item_refs = {
        str(ref.get("query_plan_item_id")): _compact_query_plan_item_ref(ref)
        for ref in query_plan.authorized_discovery_item_refs()
    }

    bindings: list[SelectedCandidateMaterialNeedBindingV1] = []
    seen_binding_cores: set[tuple[str, str, str, str]] = set()
    candidates = sorted(
        (_mapping(item) for item in _sequence(packet.get("candidate_records"))),
        key=lambda item: int(item.get("selected_candidate_rank") or 10**9),
    )
    for candidate in candidates:
        candidate_url = normalize_discovery_result_url(
            str(candidate.get("normalized_url") or "")
        )
        candidate_ref = _ordinary_candidate_ref(packet_ref, candidate)
        matching_identities = [
            identity
            for identity in discovery_result_store.identities()
            if identity.normalized_url == candidate_url
        ]
        if not matching_identities:
            raise SearchJudgmentReadAssessmentError("candidate_contributor_missing")
        contributor_facts = discovery_result_store.contributors_for_url(candidate_url)
        if int(contributor_facts.get("contributor_count") or 0) != len(
            matching_identities
        ):
            raise SearchJudgmentReadAssessmentError("candidate_contributor_count_stale")
        retained_contributor_refs = [
            _mapping(value)
            for value in _sequence(
                contributor_facts.get("contributing_source_result_refs")
            )
        ]
        if [
            _mapping(value)
            for value in _sequence(
                candidate.get("contributing_source_result_refs")
            )
        ] != retained_contributor_refs:
            raise SearchJudgmentReadAssessmentError("candidate_contributor_refs_stale")
        overflow_count = int(
            contributor_facts.get("contributor_overflow_count") or 0
        )
        if (
            int(candidate.get("contributor_ref_count") or 0)
            != len(retained_contributor_refs)
            or int(candidate.get("contributor_overflow_count") or 0)
            != overflow_count
            or (
                overflow_count > 0
                and candidate.get("contributor_overflow_digest")
                != contributor_facts.get("full_contributor_digest")
            )
        ):
            raise SearchJudgmentReadAssessmentError(
                "candidate_contributor_overflow_stale"
            )
        for identity in matching_identities:
            item_ref = _compact_query_plan_item_ref(identity.query_plan_item_ref)
            item_id = str(item_ref.get("query_plan_item_id") or "")
            if current_item_refs.get(item_id) != item_ref:
                raise SearchJudgmentReadAssessmentError("contributor_query_item_stale")
            item = current_items.get(item_id)
            if item is None:
                raise SearchJudgmentReadAssessmentError("contributor_query_item_missing")
            metadata = _mapping(item.metadata)
            searchos_slot_ref = _mapping(metadata.get("searchos_slot_ref"))
            searchos_slot: Mapping[str, Any] = {}
            if searchos_slot_ref:
                searchos_state = _mapping(run_kernel.state.searchos_state)
                searchos_slot = _mapping(
                    _mapping(searchos_state.get("slots_by_id")).get(
                        str(searchos_slot_ref.get("slot_id") or "")
                    )
                )
                if (
                    not searchos_slot
                    or _mapping(searchos_slot.get("slot_ref"))
                    != searchos_slot_ref
                ):
                    raise SearchJudgmentReadAssessmentError(
                        "searchos_contributor_slot_stale"
                    )
                component_ref = _mapping(searchos_slot.get("component_ref"))
                slot_obligation_ref = _mapping(
                    searchos_slot.get("source_obligation_ref")
                )
                obligation_ids = [
                    str(slot_obligation_ref.get("source_obligation_id") or "")
                ]
                requirement_ref: Mapping[str, Any] = {}
            else:
                component_ref = _mapping(metadata.get("accepted_component_ref"))
                requirement_ref = _mapping(metadata.get("search_requirement_ref"))
                obligation_ids = [
                    str(value)
                    for value in _sequence(
                        metadata.get("source_obligation_candidate_ids")
                    )
                    if str(value)
                ]
            if not component_ref or not requirement_ref or not obligation_ids:
                # A current discovery contributor can be intentionally
                # disambiguation-only.  It is current but has no eligible
                # material-need lineage, so it creates no binding or model call.
                if not searchos_slot_ref:
                    continue
                if not component_ref or not obligation_ids[0]:
                    raise SearchJudgmentReadAssessmentError(
                        "searchos_contributor_slot_incomplete"
                    )
            component_id = str(component_ref.get("component_id") or "")
            contract_component = contract_components.get(component_id)
            work_component = work_components.get(component_id)
            if not component_id or contract_component is None or work_component is None:
                raise SearchJudgmentReadAssessmentError("binding_component_stale")
            expected_component_ref = _component_ref(contract_component)
            if _component_ref(component_ref) != expected_component_ref:
                raise SearchJudgmentReadAssessmentError("binding_component_ref_stale")
            work_component_ref = _component_ref(
                _mapping(_mapping(work_component.get("metadata")).get(
                    "accepted_component_ref"
                ))
            )
            if work_component_ref != expected_component_ref:
                raise SearchJudgmentReadAssessmentError(
                    "search_work_plan_component_stale"
                )
            current_requirements = [
                _mapping(value)
                for value in _sequence(
                    _mapping(work_component.get("metadata")).get(
                        "search_requirement_refs"
                    )
                )
            ]
            if searchos_slot_ref:
                matching_requirements = [
                    value
                    for value in current_requirements
                    if str(value.get("component_id") or "") == component_id
                    and obligation_ids[0]
                    in {
                        str(obligation_id)
                        for obligation_id in _sequence(
                            value.get("source_obligation_candidate_ids")
                        )
                        if str(obligation_id)
                    }
                ]
            else:
                matching_requirements = [
                    value
                    for value in current_requirements
                    if _search_requirement_refs_match(
                        requirement_ref,
                        value,
                        component_id=component_id,
                    )
                ]
            if len(matching_requirements) != 1:
                raise SearchJudgmentReadAssessmentError(
                    "binding_search_requirement_stale"
                )
            requirement_ref = matching_requirements[0]
            contract_obligation_ids = set(
                str(value)
                for value in _sequence(
                    contract_component.get("source_obligation_candidate_ids")
                    or contract_component.get("source_obligation_candidate_refs")
                )
                if str(value)
            )
            requirement_obligation_ids = set(
                str(value)
                for value in _sequence(
                    requirement_ref.get("source_obligation_candidate_ids")
                )
                if str(value)
            )
            work_obligations = {
                str(_mapping(value).get("obligation_id")): _mapping(value)
                for value in _sequence(work_component.get("source_obligations"))
                if _mapping(value).get("obligation_id")
            }
            for obligation_id in obligation_ids:
                obligation = work_obligations.get(obligation_id)
                if (
                    obligation is None
                    or obligation_id not in contract_obligation_ids
                    or obligation_id not in requirement_obligation_ids
                ):
                    raise SearchJudgmentReadAssessmentError(
                        "binding_source_obligation_stale"
                    )
                key = (
                    component_id,
                    obligation_id,
                    identity.source_result_id,
                    str(candidate.get("candidate_id") or ""),
                )
                if key in seen_binding_cores:
                    continue
                seen_binding_cores.add(key)
                obligation_ref = _mapping(
                    canonical_obligations.get(obligation_id)
                )
                if searchos_slot_ref and obligation_ref != _mapping(
                    searchos_slot.get("source_obligation_ref")
                ):
                    raise SearchJudgmentReadAssessmentError(
                        "searchos_contributor_obligation_stale"
                    )
                if (
                    not obligation_ref
                    or component_id
                    not in {
                        str(value)
                        for value in _sequence(obligation_ref.get("component_ids"))
                    }
                ):
                    raise SearchJudgmentReadAssessmentError(
                        "binding_source_obligation_snapshot_stale"
                    )
                binding = SelectedCandidateMaterialNeedBindingV1.create(
                    run_id=run_kernel.state.run_id,
                    request_id=run_kernel.state.request_id,
                    answer_contract_ref=active_contract_ref,
                    component_ref=expected_component_ref,
                    source_obligation_ref=obligation_ref,
                    search_work_plan_ref=search_work_plan_ref,
                    search_requirement_ref=requirement_ref,
                    query_plan_ref=query_plan.to_ref(),
                    query_plan_item_ref=item_ref,
                    contributing_source_result_ref=identity.ref(),
                    source_material_ref=dict(identity.material_ref),
                    candidate_packet_ref=packet_ref,
                    candidate_ref=candidate_ref,
                    normalized_url=candidate_url,
                    selected_candidate_rank=int(
                        candidate.get("selected_candidate_rank")
                    ),
                    provider_call_ordinal=identity.provider_call_ordinal,
                    provider_result_rank=identity.result_rank,
                    material_class=identity.material_class,
                    source_obligation_kind=str(obligation.get("kind") or ""),
                    source_obligation_strictness=str(
                        obligation.get("strictness") or ""
                    ),
                )
                bindings.append(binding)

    bindings.sort(
        key=lambda item: (
            item.selected_candidate_rank,
            item.provider_call_ordinal,
            item.provider_result_rank,
            item.binding_id,
        )
    )
    slot_order: list[str] = []
    bindings_by_slot: dict[str, list[str]] = {}
    for binding in bindings:
        slot_id = binding.slot_id()
        if slot_id not in bindings_by_slot:
            slot_order.append(slot_id)
            bindings_by_slot[slot_id] = []
        bindings_by_slot[slot_id].append(binding.binding_id)
    if len(slot_order) > (
        policy.maximum_logical_read_assessments_per_checkpoint_run
    ):
        raise SearchJudgmentReadAssessmentError(
            SEARCH_JUDGMENT_READ_SLOT_BUDGET_EXCEEDED
        )
    admitted_slots = list(slot_order)
    state_core = {
        "schema_version": SEARCH_JUDGMENT_READ_BINDING_SET_SCHEMA_VERSION,
        "owner": "RunKernel.SearchJudgment",
        "canonical_state": True,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "answer_contract_ref": active_contract_ref,
        "candidate_packet_ref": packet_ref,
        "query_plan_ref": query_plan.to_ref(),
        "search_work_plan_ref": search_work_plan_ref,
        "source_result_identity_set_ref": (
            discovery_result_store.identity_set_ref()
        ),
        "policy_ref": policy.ref(),
        "bindings": [item.to_dict() for item in bindings],
        "binding_count": len(bindings),
        "slot_order": slot_order,
        "bindings_by_slot": bindings_by_slot,
        "policy_admitted_slot_ids": admitted_slots,
        "policy_deferred_slot_ids": [],
        "read_triggered": False,
        "read_need_decided": False,
        "candidate_rank_triggered_read": False,
        "provider_selected": False,
        "acquisition_created": False,
        "semantic_support_created": False,
        "source_obligation_satisfied": False,
    }
    return {
        **state_core,
        "binding_set_digest": stable_json_digest(state_core),
    }


def execute_search_judgment_read_binding_action(
    action: AuthorizedAction,
) -> Observation:
    validate_authorized_action(
        action,
        action_type=ActionType.SEARCH_JUDGMENT_READ_BINDINGS_DERIVE,
        stage=SEARCH_JUDGMENT_READ_BINDING_STAGE,
        expected_observation_type=(
            ObservationType.SEARCH_JUDGMENT_READ_BINDINGS_DERIVED
        ),
    )
    return Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_JUDGMENT_READ_BINDINGS_DERIVED,
        status=RunStageStatus.COMPLETED,
        payload={"binding_state": _mapping(action.inputs.get("binding_state"))},
    )


def validate_search_judgment_read_binding_reduction(
    *,
    action_inputs: Mapping[str, Any],
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    initial_answer_contract: Mapping[str, Any],
    current_answer_contract: Mapping[str, Any],
    search_work_plan: Mapping[str, Any],
    search_executor_handoff_projection: Mapping[str, Any],
) -> dict[str, Any]:
    expected = _mapping(action_inputs.get("binding_state"))
    observed = _mapping(observation_payload.get("binding_state"))
    if not expected or observed != expected:
        raise SearchJudgmentReadAssessmentError("binding_observation_mismatch")
    if expected.get("run_id") != run_id or expected.get("request_id") != request_id:
        raise SearchJudgmentReadAssessmentError("binding_run_identity_stale")
    active_ref = _active_contract_ref_from_values(
        initial_answer_contract=initial_answer_contract,
        current_answer_contract=current_answer_contract,
    )
    if _mapping(expected.get("answer_contract_ref")) != active_ref:
        raise SearchJudgmentReadAssessmentError("binding_contract_became_stale")
    work_ref = _search_work_plan_ref(_mapping(search_work_plan))
    if _mapping(expected.get("search_work_plan_ref")) != work_ref:
        raise SearchJudgmentReadAssessmentError("binding_work_plan_became_stale")
    packet_ref = _mapping(
        search_executor_handoff_projection.get("search_result_candidate_packet_ref")
    )
    if _mapping(expected.get("candidate_packet_ref")) != packet_ref:
        raise SearchJudgmentReadAssessmentError("binding_packet_became_stale")
    bindings = [
        SelectedCandidateMaterialNeedBindingV1.from_dict(item)
        for item in _sequence(expected.get("bindings"))
    ]
    if expected.get("binding_count") != len(bindings):
        raise SearchJudgmentReadAssessmentError("binding_count_mismatch")
    slot_order = list(_sequence(expected.get("slot_order")))
    admitted_slots = list(
        _sequence(expected.get("policy_admitted_slot_ids"))
    )
    deferred_slots = list(
        _sequence(expected.get("policy_deferred_slot_ids"))
    )
    if (
        admitted_slots != slot_order
        or deferred_slots
        or len(slot_order)
        > SEARCH_JUDGMENT_READ_ASSESSMENT_POLICY.maximum_logical_read_assessments_per_checkpoint_run
    ):
        raise SearchJudgmentReadAssessmentError(
            SEARCH_JUDGMENT_READ_SLOT_BUDGET_EXCEEDED
        )
    core = {key: _json_clone(value) for key, value in expected.items() if key != "binding_set_digest"}
    if expected.get("binding_set_digest") != stable_json_digest(core):
        raise SearchJudgmentReadAssessmentError("binding_set_digest_mismatch")
    return {
        "schema_version": SEARCH_JUDGMENT_READ_STATE_SCHEMA_VERSION,
        "owner": "RunKernel.SearchJudgment",
        "canonical_state": True,
        "run_id": run_id,
        "request_id": request_id,
        "binding_state": expected,
        "assessment_records_by_slot": {},
        "logical_assessment_count": 0,
        "acquisition_need_proposal_refs": [],
        "proposal_events": [],
        "custody_by_normalized_url": {},
        "custody_events": [],
        "deterministic_read_decision_used": False,
        "deterministic_fallback_used": False,
        "semantic_support_created": False,
        "source_obligation_satisfied": False,
    }


def execute_search_judgment_read_assessment_action(
    action: AuthorizedAction,
    *,
    binding_state: Mapping[str, Any],
    search_work_plan: Mapping[str, Any],
    discovery_result_store: DiscoveryResultMaterialStore,
    ask_model: Callable[..., Any] | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    effort: str = "high",
    use_reasoning: bool = True,
    measure_context_stage: Callable[..., Any] | None = None,
) -> Observation:
    """Make exactly one logical strict model call for one admitted slot."""

    validate_authorized_action(
        action,
        action_type=ActionType.SEARCH_JUDGMENT_READ_ASSESS,
        stage=SEARCH_JUDGMENT_READ_ASSESSMENT_STAGE,
        expected_observation_type=(
            ObservationType.SEARCH_JUDGMENT_READ_ASSESSED
        ),
    )
    slot_id = _required_text(action.inputs.get("slot_id"), "assessment_slot_missing")
    binding_ids = [str(value) for value in _sequence(action.inputs.get("binding_ids"))]
    bindings_by_id = {
        item.binding_id: item
        for item in (
            SelectedCandidateMaterialNeedBindingV1.from_dict(value)
            for value in _sequence(binding_state.get("bindings"))
        )
    }
    policy = SEARCH_JUDGMENT_READ_ASSESSMENT_POLICY
    shown_ids = binding_ids[: policy.maximum_bindings_shown]
    shown_bindings = [bindings_by_id.get(binding_id) for binding_id in shown_ids]
    if not shown_bindings or any(item is None for item in shown_bindings):
        raise SearchJudgmentReadAssessmentError("assessment_binding_set_stale")
    if any(item.slot_id() != slot_id for item in shown_bindings if item is not None):
        raise SearchJudgmentReadAssessmentError("assessment_slot_binding_mismatch")
    prompt = _assessment_prompt(
        slot_id=slot_id,
        bindings=[item for item in shown_bindings if item is not None],
        search_work_plan=search_work_plan,
        discovery_result_store=discovery_result_store,
        policy=policy,
    )
    prompt_digest = sha256(prompt.encode("utf-8")).hexdigest()
    if measure_context_stage is not None:
        measure_context_stage(
            SEARCH_JUDGMENT_READ_COST_PHASE,
            prompt=prompt,
            system_prompt=SEARCH_JUDGMENT_READ_SYSTEM_PROMPT,
        )
    record_core: dict[str, Any] = {
        "schema_version": SEARCH_JUDGMENT_READ_ASSESSMENT_SCHEMA_VERSION,
        "owner": "RunKernel.SearchJudgment",
        "slot_id": slot_id,
        "binding_set_digest": binding_state.get("binding_set_digest"),
        "eligible_binding_refs": [
            bindings_by_id[binding_id].ref() for binding_id in binding_ids
        ],
        "shown_binding_refs": [
            item.ref() for item in shown_bindings if item is not None
        ],
        "logical_model_call_count": 1,
        "model_attempted": True,
        "provider": _optional_text(provider),
        "model": _optional_text(model),
        "effort": effort,
        "use_reasoning": bool(use_reasoning),
        "cost_phase": SEARCH_JUDGMENT_READ_COST_PHASE,
        "prompt_digest": prompt_digest,
        "prompt_length": len(prompt),
        "raw_prompt_retained": False,
        "raw_response_retained": False,
        "deterministic_decision_used": False,
        "deterministic_fallback_used": False,
        "provider_selection_made": False,
        "semantic_support_created": False,
        "source_obligation_satisfied": False,
    }
    try:
        if (
            ask_model is None
            or not _optional_text(provider)
            or not _optional_text(model)
        ):
            raise SearchJudgmentReadAssessmentError(
                "model_transport_unavailable"
            )
        raw = ask_model(
            prompt,
            SEARCH_JUDGMENT_READ_SYSTEM_PROMPT,
            provider=provider,
            model=model,
            effort=effort,
            base_url=base_url,
            api_key=api_key,
            require_json=True,
            use_reasoning=use_reasoning,
        )
        parsed = _parse_strict_assessment_output(raw)
        decision = str(parsed["decision"])
        nominated_id = _optional_text(parsed.get("nominated_binding_id"))
        if decision == "REQUEST_READ_PAGE" and nominated_id not in shown_ids:
            raise SearchJudgmentReadAssessmentError(
                "invalid_binding_nomination"
            )
        if decision == "NO_READ" and nominated_id is not None:
            raise SearchJudgmentReadAssessmentError(
                "invalid_no_read_nomination"
            )
        record_core.update(
            {
                "outcome_status": "completed",
                "decision": decision,
                "reason_code": parsed["reason_code"],
                "nominated_binding_ref": (
                    bindings_by_id[nominated_id].ref()
                    if nominated_id is not None
                    else {}
                ),
                "assessment_failure_code": None,
            }
        )
    except SearchJudgmentReadAssessmentError as exc:
        record_core.update(
            {
                "outcome_status": "failed_closed",
                "decision": None,
                "reason_code": None,
                "nominated_binding_ref": {},
                "assessment_failure_code": exc.code,
            }
        )
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        record_core.update(
            {
                "outcome_status": "failed_closed",
                "decision": None,
                "reason_code": None,
                "nominated_binding_ref": {},
                "assessment_failure_code": "model_output_malformed",
            }
        )
    except Exception as exc:  # transport/provider implementations are external
        record_core.update(
            {
                "outcome_status": "failed_closed",
                "decision": None,
                "reason_code": None,
                "nominated_binding_ref": {},
                "assessment_failure_code": (
                    "model_transport_failed:" + type(exc).__name__
                ),
            }
        )
    record_core = _without_none(record_core)
    record = {
        **record_core,
        "assessment_digest": stable_json_digest(record_core),
    }
    record["assessment_id"] = (
        f"search-judgment-read-assessment:{slot_id}:"
        f"{record['assessment_digest'][:16]}"
    )
    return Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_JUDGMENT_READ_ASSESSED,
        status=RunStageStatus.COMPLETED,
        payload={"assessment_record": record},
    )


def validate_search_judgment_read_assessment_reduction(
    *,
    action_inputs: Mapping[str, Any],
    observation_payload: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> dict[str, Any]:
    state = _json_clone(current_state)
    if state.get("schema_version") != SEARCH_JUDGMENT_READ_STATE_SCHEMA_VERSION:
        raise SearchJudgmentReadAssessmentError("read_state_missing")
    record = _mapping(observation_payload.get("assessment_record"))
    slot_id = _required_text(action_inputs.get("slot_id"), "assessment_slot_missing")
    if record.get("slot_id") != slot_id:
        raise SearchJudgmentReadAssessmentError("assessment_slot_mismatch")
    if record.get("logical_model_call_count") != 1 or record.get("model_attempted") is not True:
        raise SearchJudgmentReadAssessmentError("assessment_call_count_invalid")
    if record.get("deterministic_decision_used") is not False or record.get(
        "deterministic_fallback_used"
    ) is not False:
        raise SearchJudgmentReadAssessmentError("assessment_deterministic_path_open")
    core = {
        key: _json_clone(value)
        for key, value in record.items()
        if key not in {"assessment_id", "assessment_digest"}
    }
    digest = stable_json_digest(core)
    if record.get("assessment_digest") != digest or record.get("assessment_id") != (
        f"search-judgment-read-assessment:{slot_id}:{digest[:16]}"
    ):
        raise SearchJudgmentReadAssessmentError("assessment_identity_mismatch")
    binding_state = _mapping(state.get("binding_state"))
    if record.get("binding_set_digest") != binding_state.get("binding_set_digest"):
        raise SearchJudgmentReadAssessmentError("assessment_binding_set_stale")
    admitted = set(_sequence(binding_state.get("policy_admitted_slot_ids")))
    if slot_id not in admitted:
        raise SearchJudgmentReadAssessmentError("assessment_slot_not_admitted")
    records = _mapping(state.get("assessment_records_by_slot"))
    if slot_id in records:
        raise SearchJudgmentReadAssessmentError("assessment_slot_already_reduced")
    expected_ids = list(
        _sequence(_mapping(binding_state.get("bindings_by_slot")).get(slot_id))
    )
    if list(_sequence(action_inputs.get("binding_ids"))) != expected_ids:
        raise SearchJudgmentReadAssessmentError("assessment_bindings_stale")
    records[slot_id] = record
    state["assessment_records_by_slot"] = records
    state["logical_assessment_count"] = int(
        state.get("logical_assessment_count") or 0
    ) + 1
    if state["logical_assessment_count"] > (
        SEARCH_JUDGMENT_READ_ASSESSMENT_POLICY.maximum_logical_read_assessments_per_checkpoint_run
    ):
        raise SearchJudgmentReadAssessmentError("assessment_policy_budget_exceeded")
    return state


def build_binding_backed_acquisition_need_proposal(
    *,
    run_kernel: RunKernel,
    binding: SelectedCandidateMaterialNeedBindingV1,
) -> AcquisitionNeedProposalV1:
    snapshot = run_kernel.acquisition_authority_snapshot()
    component_id = str(binding.component_ref.get("component_id") or "")
    obligation_id = str(
        binding.source_obligation_ref.get("source_obligation_id") or ""
    )
    component_ref = _mapping(
        _mapping(snapshot.get("components_by_id")).get(component_id)
    )
    obligation_ref = _mapping(
        _mapping(snapshot.get("source_obligations_by_id")).get(obligation_id)
    )
    if snapshot.get("answer_contract_ref") != binding.answer_contract_ref:
        raise SearchJudgmentReadAssessmentError("proposal_contract_stale")
    if component_ref != binding.component_ref:
        raise SearchJudgmentReadAssessmentError("proposal_component_stale")
    if obligation_ref != binding.source_obligation_ref:
        raise SearchJudgmentReadAssessmentError("proposal_obligation_stale")
    proposal = AcquisitionNeedProposalV1.create(
        run_id=binding.run_id,
        request_id=binding.request_id,
        producer_surface=SEARCH_JUDGMENT_READ_PRODUCER_SURFACE,
        answer_contract_ref=binding.answer_contract_ref,
        component_ref=binding.component_ref,
        source_obligation_ref=binding.source_obligation_ref,
        requested_material_shape="ordinary_single_page",
        candidate_ref=binding.candidate_ref,
        available_urls=(binding.normalized_url,),
        requested_bounds={"max_retained_characters": 20_000},
        proposal_reason_code="search_judgment_read_assessment_request_read_page",
    )
    validate_binding_backed_acquisition_need_proposal(
        proposal=proposal,
        binding=binding,
        authority_snapshot=snapshot,
    )
    return proposal


def validate_binding_backed_acquisition_need_proposal(
    *,
    proposal: AcquisitionNeedProposalV1,
    binding: SelectedCandidateMaterialNeedBindingV1,
    authority_snapshot: Mapping[str, Any],
) -> AcquisitionNeedProposalV1:
    if proposal.producer_surface != SEARCH_JUDGMENT_READ_PRODUCER_SURFACE:
        raise SearchJudgmentReadAssessmentError("proposal_producer_invalid")
    if proposal.proposal_reason_code != (
        "search_judgment_read_assessment_request_read_page"
    ):
        raise SearchJudgmentReadAssessmentError("proposal_reason_invalid")
    if proposal.requested_material_shape != "ordinary_single_page":
        raise SearchJudgmentReadAssessmentError("proposal_material_shape_invalid")
    exact = {
        "answer_contract_ref": binding.answer_contract_ref,
        "component_ref": binding.component_ref,
        "source_obligation_ref": binding.source_obligation_ref,
        "candidate_ref": binding.candidate_ref,
    }
    for field, expected in exact.items():
        if getattr(proposal, field) != expected:
            raise SearchJudgmentReadAssessmentError(f"proposal_{field}_mismatch")
    if proposal.available_urls != (binding.normalized_url,):
        raise SearchJudgmentReadAssessmentError("proposal_url_mismatch")
    if _mapping(authority_snapshot.get("answer_contract_ref")) != (
        binding.answer_contract_ref
    ):
        raise SearchJudgmentReadAssessmentError("proposal_snapshot_stale")
    return proposal


def execute_search_judgment_read_source_and_custody(
    *,
    run_kernel: RunKernel,
    candidate_packet: Mapping[str, Any],
    query_plan: QueryPlan,
    discovery_result_store: DiscoveryResultMaterialStore,
    ask_model: Callable[..., Any] | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    available_providers: Mapping[str, object],
    acquisition_transports: AcquisitionTransports | None,
    before_transport: Callable[[], Any] | None = None,
    measure_context_stage: Callable[..., Any] | None = None,
) -> SearchJudgmentReadRuntimeResult:
    """Run the mandatory main-RunKernel checkpoint and end at custody."""

    packets: list[Mapping[str, Any]] = []
    attempted = 0
    completed = 0
    try:
        binding_action = run_kernel.authorize_search_judgment_read_bindings(
            candidate_packet=candidate_packet,
            query_plan=query_plan,
            discovery_result_store=discovery_result_store,
        )
        run_kernel.reduce(execute_search_judgment_read_binding_action(binding_action))
    except SearchJudgmentReadAssessmentError as exc:
        if exc.code == SEARCH_JUDGMENT_READ_SLOT_BUDGET_EXCEEDED:
            raise
        return SearchJudgmentReadRuntimeResult(
            projection=_closed_runtime_projection(
                status="binding_derivation_failed_closed",
                failure_code=exc.code,
                run_kernel=run_kernel,
            )
        )
    except Exception as exc:
        return SearchJudgmentReadRuntimeResult(
            projection=_closed_runtime_projection(
                status="binding_derivation_failed_closed",
                failure_code=getattr(exc, "code", type(exc).__name__),
                run_kernel=run_kernel,
            )
        )

    binding_state = _mapping(
        _mapping(run_kernel.state.search_judgment_read_state).get("binding_state")
    )
    bindings_by_id = {
        item.binding_id: item
        for item in (
            SelectedCandidateMaterialNeedBindingV1.from_dict(value)
            for value in _sequence(binding_state.get("bindings"))
        )
    }
    for slot_id in _sequence(binding_state.get("policy_admitted_slot_ids")):
        binding_ids = list(
            _sequence(_mapping(binding_state.get("bindings_by_slot")).get(slot_id))
        )
        assessment_action = run_kernel.authorize_search_judgment_read_assessment(
            slot_id=str(slot_id),
            binding_ids=binding_ids,
        )
        assessment_observation = execute_search_judgment_read_assessment_action(
            assessment_action,
            binding_state=binding_state,
            search_work_plan=run_kernel.state.search_work_plan,
            discovery_result_store=discovery_result_store,
            ask_model=ask_model,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            effort="high",
            use_reasoning=use_reasoning,
            measure_context_stage=measure_context_stage,
        )
        run_kernel.reduce(assessment_observation)
        assessment = _mapping(
            _mapping(
                run_kernel.state.search_judgment_read_state.get(
                    "assessment_records_by_slot"
                )
            ).get(slot_id)
        )
        if assessment.get("decision") != "REQUEST_READ_PAGE":
            continue
        nomination_ref = _mapping(assessment.get("nominated_binding_ref"))
        binding = bindings_by_id.get(str(nomination_ref.get("binding_id") or ""))
        if binding is None or binding.ref() != nomination_ref:
            continue
        try:
            proposal = build_binding_backed_acquisition_need_proposal(
                run_kernel=run_kernel,
                binding=binding,
            )
            proposal_event = _proposal_event(
                binding=binding,
                assessment=assessment,
                proposal=proposal,
            )
            proposal_action = (
                run_kernel.authorize_search_judgment_read_proposal_event(
                    event=proposal_event
                )
            )
            run_kernel.reduce(_proposal_event_observation(proposal_action))
            existing = run_kernel.current_search_judgment_read_custody(
                binding.normalized_url
            )
            if existing:
                event = _custody_event(
                    binding=binding,
                    assessment=assessment,
                    proposal=proposal,
                    reused=True,
                    custody_record=existing,
                )
                action = run_kernel.authorize_search_judgment_read_custody_event(
                    event=event
                )
                run_kernel.reduce(_custody_event_observation(action))
                continue
            custody = _execute_one_acquisition_to_custody(
                run_kernel=run_kernel,
                candidate_packet=candidate_packet,
                binding=binding,
                assessment=assessment,
                proposal=proposal,
                available_providers=available_providers,
                acquisition_transports=acquisition_transports,
                before_transport=before_transport,
            )
            attempted += int(custody.get("provider_calls_attempted") or 0)
            completed += int(custody.get("provider_calls_completed") or 0)
            if custody.get("fetch_read_content_packet"):
                packets.append(_mapping(custody["fetch_read_content_packet"]))
        except SearchJudgmentReadAssessmentError:
            # Acquisition owners retain their typed terminal/block state.  This
            # subordinate branch never invents a semantic substitute.
            if (
                run_kernel.state.next_action_sequence
                != run_kernel.state.next_observation_sequence
            ):
                raise
            continue
    return SearchJudgmentReadRuntimeResult(
        projection=_closed_runtime_projection(
            status="checkpoint_completed",
            failure_code=None,
            run_kernel=run_kernel,
        ),
        fetch_read_content_packets=tuple(packets),
        provider_calls_attempted=attempted,
        provider_calls_completed=completed,
    )


def validate_search_judgment_read_proposal_reduction(
    *,
    action_inputs: Mapping[str, Any],
    observation_payload: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> dict[str, Any]:
    state = _json_clone(current_state)
    event = _mapping(observation_payload.get("proposal_event"))
    if event != _mapping(action_inputs.get("proposal_event")):
        raise SearchJudgmentReadAssessmentError("proposal_event_mismatch")
    if event.get("schema_version") != SEARCH_JUDGMENT_READ_PROPOSAL_EVENT_SCHEMA_VERSION:
        raise SearchJudgmentReadAssessmentError("proposal_event_schema_invalid")
    core = {
        key: _json_clone(value)
        for key, value in event.items()
        if key not in {"event_id", "event_digest"}
    }
    digest = stable_json_digest(core)
    if event.get("event_digest") != digest or event.get("event_id") != (
        f"search-judgment-read-proposal:{digest[:20]}"
    ):
        raise SearchJudgmentReadAssessmentError("proposal_event_identity_invalid")
    binding_ref = _mapping(event.get("binding_ref"))
    binding_state = _mapping(state.get("binding_state"))
    binding = next(
        (
            SelectedCandidateMaterialNeedBindingV1.from_dict(value)
            for value in _sequence(binding_state.get("bindings"))
            if _mapping(value).get("binding_id") == binding_ref.get("binding_id")
        ),
        None,
    )
    if binding is None or binding.ref() != binding_ref:
        raise SearchJudgmentReadAssessmentError("proposal_binding_stale")
    assessment = _mapping(
        _mapping(state.get("assessment_records_by_slot")).get(binding.slot_id())
    )
    if (
        assessment.get("decision") != "REQUEST_READ_PAGE"
        or _mapping(assessment.get("nominated_binding_ref")) != binding.ref()
        or _mapping(event.get("assessment_ref")) != _assessment_ref(assessment)
    ):
        raise SearchJudgmentReadAssessmentError("proposal_assessment_stale")
    proposal_ref = _mapping(event.get("acquisition_need_proposal_ref"))
    if not proposal_ref:
        raise SearchJudgmentReadAssessmentError("proposal_ref_missing")
    prior_events = list(_sequence(state.get("proposal_events")))
    if any(
        _mapping(value).get("assessment_ref") == event.get("assessment_ref")
        for value in prior_events
    ):
        raise SearchJudgmentReadAssessmentError("proposal_assessment_duplicate")
    prior_events.append(event)
    state["proposal_events"] = prior_events
    proposal_refs = list(_sequence(state.get("acquisition_need_proposal_refs")))
    proposal_refs.append(proposal_ref)
    state["acquisition_need_proposal_refs"] = proposal_refs
    return state


def validate_search_judgment_read_custody_reduction(
    *,
    action_inputs: Mapping[str, Any],
    observation_payload: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> dict[str, Any]:
    state = _json_clone(current_state)
    event = _mapping(observation_payload.get("custody_event"))
    if event != _mapping(action_inputs.get("custody_event")):
        raise SearchJudgmentReadAssessmentError("custody_event_mismatch")
    if event.get("schema_version") != SEARCH_JUDGMENT_READ_CUSTODY_EVENT_SCHEMA_VERSION:
        raise SearchJudgmentReadAssessmentError("custody_event_schema_invalid")
    core = {
        key: _json_clone(value)
        for key, value in event.items()
        if key not in {"event_id", "event_digest"}
    }
    digest = stable_json_digest(core)
    if event.get("event_digest") != digest or event.get("event_id") != (
        f"search-judgment-read-custody:{digest[:20]}"
    ):
        raise SearchJudgmentReadAssessmentError("custody_event_identity_invalid")
    binding_ref = _mapping(event.get("binding_ref"))
    binding_state = _mapping(state.get("binding_state"))
    binding = next(
        (
            SelectedCandidateMaterialNeedBindingV1.from_dict(value)
            for value in _sequence(binding_state.get("bindings"))
            if _mapping(value).get("binding_id") == binding_ref.get("binding_id")
        ),
        None,
    )
    if binding is None or binding.ref() != binding_ref:
        raise SearchJudgmentReadAssessmentError("custody_binding_stale")
    assessments = _mapping(state.get("assessment_records_by_slot"))
    assessment = _mapping(assessments.get(binding.slot_id()))
    if (
        assessment.get("decision") != "REQUEST_READ_PAGE"
        or _mapping(assessment.get("nominated_binding_ref")) != binding.ref()
        or _mapping(event.get("assessment_ref")) != _assessment_ref(assessment)
    ):
        raise SearchJudgmentReadAssessmentError("custody_assessment_stale")
    normalized_url = normalize_discovery_result_url(
        str(event.get("normalized_url") or "")
    )
    if normalized_url != binding.normalized_url:
        raise SearchJudgmentReadAssessmentError("custody_url_mismatch")
    registry = _mapping(state.get("custody_by_normalized_url"))
    custody_record = _mapping(event.get("custody_record"))
    if event.get("reused") is True:
        if not registry.get(normalized_url) or _mapping(
            registry.get(normalized_url)
        ) != custody_record:
            raise SearchJudgmentReadAssessmentError("custody_reuse_stale")
    elif event.get("reused") is False:
        if registry.get(normalized_url):
            raise SearchJudgmentReadAssessmentError("duplicate_custody_registration")
        required_refs = (
            "fetch_read_content_packet_ref",
            "evidence_ledger_custody_ref",
            "terminal_receipt_ref",
            "custody_authorization_ref",
        )
        if any(not _mapping(custody_record.get(key)) for key in required_refs):
            raise SearchJudgmentReadAssessmentError("custody_record_incomplete")
        registry[normalized_url] = custody_record
    else:
        raise SearchJudgmentReadAssessmentError("custody_reuse_posture_invalid")
    proposal_ref = _mapping(event.get("acquisition_need_proposal_ref"))
    if proposal_ref not in [
        _mapping(value)
        for value in _sequence(state.get("acquisition_need_proposal_refs"))
    ]:
        raise SearchJudgmentReadAssessmentError("custody_proposal_not_recorded")
    state["custody_by_normalized_url"] = registry
    events = list(_sequence(state.get("custody_events")))
    events.append(event)
    state["custody_events"] = events
    return state


def build_full_search_judgment_containment_projection(
    *,
    evidence_ledger_projection: Mapping[str, Any],
    search_judgment_read_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Exclude only this phase's custody at the existing full-judgment seam."""

    projection = _json_clone(evidence_ledger_projection)
    state = _mapping(search_judgment_read_state)
    registry = _mapping(state.get("custody_by_normalized_url"))
    candidate_ids = {
        str(_mapping(record).get("candidate_id") or "")
        for record in registry.values()
        if isinstance(record, Mapping)
    }
    candidate_ids.update(
        str(_mapping(record).get("evidence_ledger_candidate_id") or "")
        for record in registry.values()
        if isinstance(record, Mapping)
    )
    candidate_ids.discard("")
    packet_ids = {
        str(
            _mapping(_mapping(record).get("fetch_read_content_packet_ref")).get(
                "packet_id"
            )
            or ""
        )
        for record in registry.values()
        if isinstance(record, Mapping)
    }
    observation_ids = {
        str(
            _mapping(_mapping(record).get("evidence_ledger_observation_ref")).get(
                "observation_id"
            )
            or ""
        )
        for record in registry.values()
        if isinstance(record, Mapping)
    }
    candidates = [
        _mapping(item)
        for item in _sequence(projection.get("candidate_records"))
        if str(_mapping(item).get("candidate_id") or "") not in candidate_ids
    ]
    projection["candidate_records"] = candidates
    projection["candidate_count"] = len(candidates)
    if "custody_gaps" in projection:
        projection["custody_gaps"] = [
            _mapping(item)
            for item in _sequence(projection.get("custody_gaps"))
            if str(_mapping(item).get("candidate_id") or "")
            not in candidate_ids
            and str(_mapping(item).get("observation_id") or "")
            not in observation_ids
        ]
    custody = _mapping(projection.get("fetch_read_candidate_custody"))
    records = [
        _mapping(item)
        for item in _sequence(custody.get("fetch_read_candidate_custody_records"))
        if str(_mapping(item).get("candidate_id") or "") not in candidate_ids
        and str(_mapping(item).get("fetch_read_content_packet_id") or "")
        not in packet_ids
    ]
    if custody:
        custody["fetch_read_candidate_custody_records"] = records
        custody["candidate_content_custody_visible"] = bool(records)
        custody["custody_record_count"] = len(records)
        custody["readable_record_count"] = sum(
            1 for item in records if item.get("fetch_read_status") == "readable"
        )
        custody["unreadable_record_count"] = sum(
            1 for item in records if item.get("fetch_read_status") != "readable"
        )
        custody_gaps = [
            _mapping(item)
            for item in _sequence(custody.get("custody_gaps"))
            if str(_mapping(item).get("candidate_id") or "") not in candidate_ids
        ]
        custody["custody_gaps"] = custody_gaps
        custody["custody_gap_count"] = len(custody_gaps)
        projection["fetch_read_candidate_custody"] = custody
    observation_refs = [
        _mapping(item)
        for item in _sequence(projection.get("observation_refs"))
        if not (
            _mapping(item).get("source")
            == "fetch_read_content_packet_candidate_custody"
            and str(_mapping(item).get("observation_id") or "")
            in observation_ids
        )
    ]
    projection["observation_refs"] = observation_refs
    return projection


def _execute_one_acquisition_to_custody(
    *,
    run_kernel: RunKernel,
    candidate_packet: Mapping[str, Any],
    binding: SelectedCandidateMaterialNeedBindingV1,
    assessment: Mapping[str, Any],
    proposal: AcquisitionNeedProposalV1,
    available_providers: Mapping[str, object],
    acquisition_transports: AcquisitionTransports | None,
    before_transport: Callable[[], Any] | None,
    register_legacy_event: bool = True,
) -> dict[str, Any]:
    acquisition = execute_acquisition_work_order_to_terminal(
        run_kernel=run_kernel,
        proposal=proposal,
        available_providers=available_providers,
        transports=acquisition_transports,
        before_transport=before_transport,
    )
    execution = acquisition.get("execution_result")
    if execution is None:
        raise SearchJudgmentReadAssessmentError(
            str(acquisition.get("failure_code") or "acquisition_route_blocked")
        )
    if not execution.succeeded or len(execution.artifacts) != 1:
        raise SearchJudgmentReadAssessmentError(
            execution.failure_code or execution.block_code or "read_dispatch_failed"
        )
    custody_action = run_kernel.authorize_acquisition_custody_consumption(
        terminal_receipt_ref=acquisition["terminal_receipt"].ref(),
        custody_consumer=SEARCH_JUDGMENT_READ_PRODUCER_SURFACE,
    )
    custody_result = execute_acquisition_custody_authorization_action(
        custody_action,
        work_order=acquisition["work_order"],
        route_observation=acquisition["route_observation"],
        terminal_receipt=acquisition["terminal_receipt"],
        custody_consumer=SEARCH_JUDGMENT_READ_PRODUCER_SURFACE,
        acquisition_control_state=run_kernel.state.acquisition_control_state,
    )
    run_kernel.reduce(custody_result.observation)
    run_kernel.require_current_acquisition_custody_authorization(
        custody_result.custody_authorization.ref()
    )
    artifact = execution.artifacts[0]
    material = _sanitized_material_from_artifact(
        artifact=artifact,
        binding=binding,
    )
    packet = validate_fetch_read_content_packet(
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [material],
            selected_candidate_ids=[str(binding.candidate_ref["candidate_id"])],
        )
    )
    component_id = str(binding.component_ref.get("component_id") or "")
    source_obligation_id = str(
        binding.source_obligation_ref.get("source_obligation_id") or ""
    )
    component_identity = component_id.replace("-", "_")
    exact_requirement_ids = [
        str(item["requirement_id"])
        for item in run_kernel.state.evidence_ledger.to_projection().to_dict().get(
            "source_requirements"
        )
        or ()
        if isinstance(item, Mapping)
        and str(item.get("component_id") or "").replace("-", "_")
        == component_identity
        and item.get("source_obligation_id") == source_obligation_id
        and item.get("requirement_id")
    ]
    recovery_cycle_ref = _mapping(
        run_kernel.state.searchos_state.get(
            "active_existing_gap_recovery_cycle_ref"
        )
    )
    recovery_slot_ref = _mapping(
        recovery_cycle_ref.get("recovery_slot_ref")
    )
    if (
        recovery_cycle_ref
        and str(recovery_slot_ref.get("component_id") or "").replace(
            "-", "_"
        )
        == component_identity
        and recovery_slot_ref.get("source_obligation_id")
        == source_obligation_id
    ):
        semantic_requirement_id = (
            "searchos_semantic_requirement:"
            + source_obligation_id.split(":", 1)[-1]
            + ":"
            + stable_json_digest(
                {
                    "slot_id": recovery_slot_ref.get("slot_id"),
                    "component_id": component_id,
                    "source_obligation_id": source_obligation_id,
                }
            )[:24]
        )
        exact_requirement_ids = list(
            dict.fromkeys(
                [*exact_requirement_ids, semantic_requirement_id]
            )
        )
    ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=run_kernel,
        fetch_read_content_packet=packet,
        observation_id=(
            f"{binding.run_id}:evidence-ledger:searchos-read-custody:"
            f"{packet['packet_digest'][:16]}"
        ),
        linked_requirement_ids=exact_requirement_ids,
    )
    custody_record = _canonical_custody_record(
        binding=binding,
        packet=packet,
        ledger_projection=ledger_projection,
        terminal_receipt_ref=acquisition["terminal_receipt"].ref(),
        custody_authorization_ref=custody_result.custody_authorization.ref(),
    )
    if register_legacy_event:
        event = _custody_event(
            binding=binding,
            assessment=assessment,
            proposal=proposal,
            reused=False,
            custody_record=custody_record,
        )
        event_action = run_kernel.authorize_search_judgment_read_custody_event(event=event)
        run_kernel.reduce(_custody_event_observation(event_action))
    return {
        "fetch_read_content_packet": packet,
        "custody_record": custody_record,
        "navigation_source_markdown": artifact.retained_text,
        "provider_calls_attempted": execution.provider_calls_attempted,
        "provider_calls_completed": execution.provider_calls_completed,
    }


def execute_searchos_candidate_read_to_custody(
    *,
    run_kernel: RunKernel,
    candidate_packet: Mapping[str, Any],
    binding: SelectedCandidateMaterialNeedBindingV1,
    available_providers: Mapping[str, object],
    acquisition_transports: AcquisitionTransports | None,
    before_transport: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Execute one neutral SearchOS READ through existing acquisition owners.

    SearchJudgment has already selected the exact admitted candidate binding.
    This subordinate transport composition performs no model judgment and does
    not write the retired standalone READ-assessment registry.
    """

    proposal = build_binding_backed_acquisition_need_proposal(
        run_kernel=run_kernel,
        binding=binding,
    )
    return _execute_one_acquisition_to_custody(
        run_kernel=run_kernel,
        candidate_packet=candidate_packet,
        binding=binding,
        assessment={},
        proposal=proposal,
        available_providers=available_providers,
        acquisition_transports=acquisition_transports,
        before_transport=before_transport,
        register_legacy_event=False,
    )


def _sanitized_material_from_artifact(
    *, artifact: AcquisitionArtifact, binding: SelectedCandidateMaterialNeedBindingV1
) -> dict[str, Any]:
    selection = select_bounded_answer_bearing_text(artifact.retained_text or "")
    return _without_none(
        {
            "candidate_id": binding.candidate_ref.get("candidate_id"),
            "candidate_digest": binding.candidate_ref.get("candidate_digest"),
            "fetch_read_status": "readable",
            "attempted_url": artifact.attempted_url,
            "provider_reported_url": artifact.provider_reported_url,
            "resolved_url": artifact.resolved_url,
            "final_url": artifact.final_url,
            "canonical_url": artifact.canonical_url,
            "http_status": artifact.http_status,
            "content_type": artifact.content_type,
            "retrieved_or_observed_at": artifact.observed_at,
            "content_title": artifact.title,
            "content_length": artifact.retained_character_count,
            "bounded_text": selection.bounded_text,
            "bounded_text_sanitized": True,
            "bounded_text_bounded": True,
            "bounded_character_count": selection.bounded_text_char_count,
            "excerpt_digest": selection.bounded_text_digest,
            "bounded_text_selection": selection.to_metadata(),
            "raw_provider_payload_retained": False,
            "raw_page_content_retained": False,
            "raw_page_text_retained": False,
            "semantic_support_created": False,
            "source_obligation_satisfied": False,
        }
    )


def _assessment_prompt(
    *,
    slot_id: str,
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
    search_work_plan: Mapping[str, Any],
    discovery_result_store: DiscoveryResultMaterialStore,
    policy: SearchJudgmentReadAssessmentPolicyV1,
) -> str:
    first = bindings[0]
    component_id = str(first.component_ref.get("component_id") or "")
    component = next(
        (
            _mapping(value)
            for value in _sequence(search_work_plan.get("components"))
            if _mapping(value).get("component_id") == component_id
        ),
        {},
    )
    obligation_id = str(
        first.source_obligation_ref.get("source_obligation_id") or ""
    )
    obligation = next(
        (
            _mapping(value)
            for value in _sequence(component.get("source_obligations"))
            if _mapping(value).get("obligation_id") == obligation_id
        ),
        {},
    )
    material_rows: list[dict[str, Any]] = []
    for binding in bindings:
        material = discovery_result_store.material_for_ref(
            binding.source_material_ref
        )
        if material is None:
            raise SearchJudgmentReadAssessmentError("assessment_material_stale")
        text = str(material.material_text or "")[
            : policy.maximum_bounded_material_characters_per_binding
        ]
        material_rows.append(
            {
                "binding_id": binding.binding_id,
                "selected_candidate_rank": binding.selected_candidate_rank,
                "url": binding.normalized_url,
                "material_class": binding.material_class,
                "title": material.title[:220],
                "snippet": material.snippet[:500],
                "bounded_discover_material": text,
                "bounded_material_char_count": len(text),
            }
        )
    payload = {
        "assessment_unit": {
            "slot_id": slot_id,
            "component_id": component_id,
            "component_question": str(
                component.get("user_facing_subquestion") or ""
            )[:500],
            "source_obligation_id": obligation_id,
            "source_obligation_kind": obligation.get("kind"),
            "source_obligation_strictness": obligation.get("strictness"),
            "currentness_requirement": obligation.get("currentness_requirement"),
            "satisfaction_rule": obligation.get("satisfaction_rule"),
        },
        "eligible_bindings": material_rows,
        "policy": policy.to_dict(),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _parse_strict_assessment_output(raw: Any) -> dict[str, Any]:
    text = raw if isinstance(raw, str) else json.dumps(raw)
    # Do not use the legacy JSON-extraction helper here: it would repair prose
    # or fenced output into a decision despite this branch's exact-object contract.
    parsed = json.loads(text)
    if not isinstance(parsed, Mapping):
        raise SearchJudgmentReadAssessmentError("model_output_not_object")
    decision = str(parsed.get("decision") or "")
    allowed = {"schema_version", "decision", "reason_code"}
    if decision == "REQUEST_READ_PAGE":
        allowed.add("nominated_binding_id")
    if set(parsed) != allowed:
        raise SearchJudgmentReadAssessmentError("model_output_fields_invalid")
    if parsed.get("schema_version") != _MODEL_DECISION_SCHEMA_VERSION:
        raise SearchJudgmentReadAssessmentError("model_output_schema_invalid")
    if decision not in _DECISIONS:
        raise SearchJudgmentReadAssessmentError("model_output_decision_invalid")
    reason = _required_text(parsed.get("reason_code"), "model_reason_code_missing")
    if len(reason) > 120 or not all(
        character.isalnum() or character in "_-" for character in reason
    ):
        raise SearchJudgmentReadAssessmentError("model_reason_code_invalid")
    if decision == "REQUEST_READ_PAGE":
        _required_text(
            parsed.get("nominated_binding_id"), "model_nomination_missing"
        )
    return dict(parsed)


def _active_contract(
    run_kernel: RunKernel,
) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _mapping(
        run_kernel.state.current_answer_contract
        or run_kernel.state.initial_answer_contract
    )
    source = (
        "current_answer_contract"
        if run_kernel.state.current_answer_contract
        else "initial_answer_contract"
    )
    ref = contract_ref_from_contract(contract, source=source)
    if not contract or not ref:
        raise SearchJudgmentReadAssessmentError("active_answer_contract_missing")
    return contract, ref


def _active_contract_ref_from_values(
    *,
    initial_answer_contract: Mapping[str, Any],
    current_answer_contract: Mapping[str, Any],
) -> dict[str, Any]:
    contract = _mapping(current_answer_contract or initial_answer_contract)
    source = (
        "current_answer_contract"
        if current_answer_contract
        else "initial_answer_contract"
    )
    return contract_ref_from_contract(contract, source=source)


def _component_ref(component: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "component_id": _required_text(
            component.get("component_id"), "component_id_missing"
        ),
        "component_revision": _required_text(
            component.get("component_revision"), "component_revision_missing"
        ),
        "component_digest": _required_text(
            component.get("component_digest"), "component_digest_missing"
        ),
    }


def _search_work_plan_ref(plan: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _mapping(plan.get("metadata"))
    plan_id = _required_text(
        metadata.get("search_work_plan_id") or metadata.get("construction_id"),
        "search_work_plan_id_missing",
    )
    return {
        "search_work_plan_id": plan_id,
        "search_work_plan_digest": stable_json_digest(plan),
        "schema_version": plan.get("schema_version"),
    }


def _search_work_plan_contract_ref_matches(
    value: Mapping[str, Any],
    *,
    active_contract_ref: Mapping[str, Any],
) -> bool:
    ref = _mapping(value)
    return (
        str(ref.get("contract_version") or "")
        == str(active_contract_ref.get("contract_version") or "")
        and ref.get("contract_digest") == active_contract_ref.get("contract_digest")
        and ref.get("parent_kind") == active_contract_ref.get("source")
    )


def _search_requirement_refs_match(
    query_ref: Mapping[str, Any],
    work_ref: Mapping[str, Any],
    *,
    component_id: str,
) -> bool:
    query = _mapping(query_ref)
    work = _mapping(work_ref)
    query_id = str(
        query.get("requirement_id") or query.get("search_requirement_id") or ""
    )
    work_id = str(
        work.get("requirement_id") or work.get("search_requirement_id") or ""
    )
    if not query_id or query_id != work_id:
        return False
    if str(query.get("component_id") or "") != component_id:
        return False
    if str(work.get("component_id") or "") != component_id:
        return False
    query_sources = {
        str(value)
        for value in _sequence(query.get("source_obligation_candidate_ids"))
        if str(value)
    }
    work_sources = {
        str(value)
        for value in _sequence(work.get("source_obligation_candidate_ids"))
        if str(value)
    }
    if query_sources and query_sources != work_sources:
        return False
    query_digest = query.get("requirement_digest")
    work_digest = work.get("requirement_digest")
    return not (query_digest and work_digest and query_digest != work_digest)


def _ordinary_candidate_ref(
    packet_ref: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "packet_id": _required_text(packet_ref.get("packet_id"), "packet_id_missing"),
        "packet_digest": _required_text(
            packet_ref.get("packet_digest"), "packet_digest_missing"
        ),
        "candidate_id": _required_text(
            candidate.get("candidate_id"), "candidate_id_missing"
        ),
        "candidate_digest": _required_text(
            candidate.get("candidate_digest"), "candidate_digest_missing"
        ),
        "record_digest": _required_text(
            candidate.get("record_digest"), "candidate_record_digest_missing"
        ),
        "url": normalize_discovery_result_url(
            str(candidate.get("normalized_url") or "")
        ),
    }


def _slot_id(
    component_ref: Mapping[str, Any], source_obligation_ref: Mapping[str, Any]
) -> str:
    return (
        "search-judgment-read-slot:"
        f"{component_ref.get('component_id')}:"
        f"{source_obligation_ref.get('source_obligation_id')}"
    )


def _compact_query_plan_item_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    ref = _mapping(value)
    return {
        "query_plan_item_id": ref.get("query_plan_item_id"),
        "query_plan_item_digest": ref.get("query_plan_item_digest"),
        "query_digest": ref.get("query_digest"),
    }


def _assessment_ref(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "assessment_id": record.get("assessment_id"),
        "assessment_digest": record.get("assessment_digest"),
        "slot_id": record.get("slot_id"),
        "decision": record.get("decision"),
    }


def _proposal_event(
    *,
    binding: SelectedCandidateMaterialNeedBindingV1,
    assessment: Mapping[str, Any],
    proposal: AcquisitionNeedProposalV1,
) -> dict[str, Any]:
    core = {
        "schema_version": SEARCH_JUDGMENT_READ_PROPOSAL_EVENT_SCHEMA_VERSION,
        "binding_ref": binding.ref(),
        "assessment_ref": _assessment_ref(assessment),
        "acquisition_need_proposal_ref": proposal.ref(),
        "semantic_support_created": False,
        "source_obligation_satisfied": False,
    }
    digest = stable_json_digest(core)
    return {
        **core,
        "event_id": f"search-judgment-read-proposal:{digest[:20]}",
        "event_digest": digest,
    }


def _proposal_event_observation(action: AuthorizedAction) -> Observation:
    validate_authorized_action(
        action,
        action_type=ActionType.SEARCH_JUDGMENT_READ_PROPOSAL_RECORD,
        stage=SEARCH_JUDGMENT_READ_PROPOSAL_STAGE,
        expected_observation_type=(
            ObservationType.SEARCH_JUDGMENT_READ_PROPOSAL_RECORDED
        ),
    )
    return Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_JUDGMENT_READ_PROPOSAL_RECORDED,
        status=RunStageStatus.COMPLETED,
        payload={"proposal_event": _mapping(action.inputs.get("proposal_event"))},
    )


def _custody_event(
    *,
    binding: SelectedCandidateMaterialNeedBindingV1,
    assessment: Mapping[str, Any],
    proposal: AcquisitionNeedProposalV1,
    reused: bool,
    custody_record: Mapping[str, Any],
) -> dict[str, Any]:
    core = {
        "schema_version": SEARCH_JUDGMENT_READ_CUSTODY_EVENT_SCHEMA_VERSION,
        "binding_ref": binding.ref(),
        "assessment_ref": _assessment_ref(assessment),
        "acquisition_need_proposal_ref": proposal.ref(),
        "normalized_url": binding.normalized_url,
        "reused": reused,
        "provider_transport_attempted": not reused,
        "custody_record": _json_clone(custody_record),
        "semantic_support_created": False,
        "source_obligation_satisfied": False,
    }
    digest = stable_json_digest(core)
    return {
        **core,
        "event_id": f"search-judgment-read-custody:{digest[:20]}",
        "event_digest": digest,
    }


def _custody_event_observation(action: AuthorizedAction) -> Observation:
    validate_authorized_action(
        action,
        action_type=ActionType.SEARCH_JUDGMENT_READ_CUSTODY_RECORD,
        stage=SEARCH_JUDGMENT_READ_CUSTODY_STAGE,
        expected_observation_type=(
            ObservationType.SEARCH_JUDGMENT_READ_CUSTODY_RECORDED
        ),
    )
    return Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_JUDGMENT_READ_CUSTODY_RECORDED,
        status=RunStageStatus.COMPLETED,
        payload={"custody_event": _mapping(action.inputs.get("custody_event"))},
    )


def _canonical_custody_record(
    *,
    binding: SelectedCandidateMaterialNeedBindingV1,
    packet: Mapping[str, Any],
    ledger_projection: Mapping[str, Any],
    terminal_receipt_ref: Mapping[str, Any],
    custody_authorization_ref: Mapping[str, Any],
) -> dict[str, Any]:
    custody = _mapping(ledger_projection.get("fetch_read_candidate_custody"))
    record = next(
        (
            _mapping(value)
            for value in _sequence(
                custody.get("fetch_read_candidate_custody_records")
            )
            if _mapping(value).get("candidate_id")
            == binding.candidate_ref.get("candidate_id")
        ),
        {},
    )
    if not record:
        raise SearchJudgmentReadAssessmentError("ledger_custody_record_missing")
    ledger_candidate_id = (
        str(binding.candidate_ref.get("candidate_id") or "")
        .casefold()
        .replace("-", "_")
        .replace(" ", "_")[:160]
    )
    if not any(
        str(_mapping(value).get("candidate_id") or "") == ledger_candidate_id
        for value in _sequence(ledger_projection.get("candidate_records"))
    ):
        raise SearchJudgmentReadAssessmentError(
            "ledger_candidate_record_missing"
        )
    return {
        "normalized_url": binding.normalized_url,
        "candidate_id": binding.candidate_ref.get("candidate_id"),
        "evidence_ledger_candidate_id": ledger_candidate_id,
        "candidate_digest": binding.candidate_ref.get("candidate_digest"),
        "answer_contract_ref": binding.answer_contract_ref,
        "fetch_read_content_packet_ref": (
            fetch_read_content_packet_ref_from_packet(packet)
        ),
        "evidence_ledger_custody_ref": {
            "owner": ledger_projection.get("owner"),
            "schema_version": ledger_projection.get("schema_version"),
            "reference_id": record.get("reference_id"),
            "reference_digest": record.get("reference_digest"),
        },
        "evidence_ledger_observation_ref": {
            "observation_id": (
                f"{binding.run_id}:evidence-ledger:searchos-read-custody:"
                f"{packet['packet_digest'][:16]}"
            ),
            "source": "fetch_read_content_packet_candidate_custody",
        },
        "terminal_receipt_ref": _json_clone(terminal_receipt_ref),
        "custody_authorization_ref": _json_clone(custody_authorization_ref),
        "bounded_content_present": record.get("bounded_content_present") is True,
        "semantic_support_created": False,
        "source_obligation_satisfied": False,
    }


def _closed_runtime_projection(
    *, status: str, failure_code: str | None, run_kernel: RunKernel
) -> dict[str, Any]:
    state = _mapping(run_kernel.state.search_judgment_read_state)
    binding_state = _mapping(state.get("binding_state"))
    assessments = list(
        _mapping(state.get("assessment_records_by_slot")).values()
    )
    events = list(_sequence(state.get("custody_events")))
    proposal_ids = {
        str(_mapping(value).get("proposal_id") or "")
        for value in _sequence(state.get("acquisition_need_proposal_refs"))
    }
    acquisition_state = _mapping(run_kernel.state.acquisition_control_state)
    decision_ids = {
        str(_mapping(value).get("decision_id") or "")
        for value in _mapping(
            acquisition_state.get("capability_decisions_by_id")
        ).values()
        if str(
            _mapping(_mapping(value).get("proposal_ref")).get("proposal_id")
            or ""
        )
        in proposal_ids
    }
    work_order_ids = {
        str(_mapping(value).get("work_order_id") or "")
        for value in _mapping(acquisition_state.get("work_orders_by_id")).values()
        if str(
            _mapping(
                _mapping(value).get("accepted_capability_observation_ref")
            ).get("decision_id")
            or ""
        )
        in decision_ids
    }
    execution_observations = [
        _mapping(value)
        for value in _mapping(
            acquisition_state.get("execution_observations_by_id")
        ).values()
        if str(
            _mapping(_mapping(value).get("work_order_ref")).get("work_order_id")
            or ""
        )
        in work_order_ids
    ]
    route_observations = [
        _mapping(value)
        for value in _mapping(acquisition_state.get("routes_by_id")).values()
        if str(
            _mapping(_mapping(value).get("work_order_ref")).get("work_order_id")
            or ""
        )
        in work_order_ids
    ]
    acquisition_failure_codes = [
        str(value.get("failure_or_block_code"))
        for value in execution_observations
        if value.get("terminal_status") != "completed"
        and value.get("failure_or_block_code")
    ] + [
        str(value.get("block_code"))
        for value in route_observations
        if value.get("terminal_status") == "blocked" and value.get("block_code")
    ]
    return _without_none(
        {
            "trace_key": SEARCH_JUDGMENT_READ_TRACE_KEY,
            "owner": "RunKernel.SearchJudgment",
            "canonical_state": True,
            "status": status,
            "failure_code": failure_code,
            "binding_set_ref": {
                "binding_set_digest": binding_state.get("binding_set_digest"),
                "binding_count": binding_state.get("binding_count", 0),
            },
            "eligible_binding_count": binding_state.get("binding_count", 0),
            "eligible_slot_count": len(
                _sequence(binding_state.get("slot_order"))
            ),
            "policy_admitted_slot_count": len(
                _sequence(binding_state.get("policy_admitted_slot_ids"))
            ),
            "logical_assessment_count": state.get("logical_assessment_count", 0),
            "assessment_failure_count": sum(
                1 for item in assessments if _mapping(item).get("outcome_status") == "failed_closed"
            ),
            "no_read_count": sum(
                1 for item in assessments if _mapping(item).get("decision") == "NO_READ"
            ),
            "request_read_page_count": sum(
                1
                for item in assessments
                if _mapping(item).get("decision") == "REQUEST_READ_PAGE"
            ),
            "acquisition_need_proposal_count": len(
                _sequence(state.get("acquisition_need_proposal_refs"))
            ),
            "canonical_custody_count": len(
                _mapping(state.get("custody_by_normalized_url"))
            ),
            "provider_calls_attempted": sum(
                int(item.get("provider_calls_attempted") or 0)
                for item in execution_observations
            ),
            "provider_calls_completed": sum(
                int(item.get("provider_calls_completed") or 0)
                for item in execution_observations
            ),
            "acquisition_failure_count": len(acquisition_failure_codes),
            "acquisition_failure_codes": acquisition_failure_codes,
            "same_url_custody_reuse_count": sum(
                1 for item in events if _mapping(item).get("reused") is True
            ),
            "legacy_full_search_judgment_flag_consulted": False,
            "ordinary_live_flag_consulted": False,
            "child_run_kernel_used": False,
            "deterministic_read_decision_used": False,
            "deterministic_fallback_used": False,
            "provider_failure_fallback_attempted": any(
                item.get("provider_failure_fallback_attempted") is True
                for item in execution_observations
            ),
            "semantic_support_created": False,
            "source_obligation_satisfied": False,
            "query_plan_continuation_created": False,
            "citation_created": False,
            "sufficiency_decided": False,
            "final_answer_packet_created": False,
            "author_input_created": False,
            "raw_prompt_retained": False,
            "raw_response_retained": False,
            "raw_provider_payload_retained": False,
        }
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str))


def _required_text(value: Any, code: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SearchJudgmentReadAssessmentError(code)
    return text


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _positive_int(value: Any, code: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise SearchJudgmentReadAssessmentError(code) from exc
    if number <= 0:
        raise SearchJudgmentReadAssessmentError(code)
    return number


def _without_none(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


__all__ = [
    "SEARCH_JUDGMENT_READ_ASSESSMENT_POLICY",
    "SEARCH_JUDGMENT_READ_COST_PHASE",
    "SEARCH_JUDGMENT_READ_STATE_SCHEMA_VERSION",
    "SEARCH_JUDGMENT_READ_SLOT_BUDGET_EXCEEDED",
    "SEARCH_JUDGMENT_READ_TRACE_KEY",
    "SearchJudgmentReadAssessmentError",
    "SearchJudgmentReadAssessmentPolicyV1",
    "SearchJudgmentReadRuntimeResult",
    "SelectedCandidateMaterialNeedBindingV1",
    "build_binding_backed_acquisition_need_proposal",
    "build_full_search_judgment_containment_projection",
    "derive_selected_candidate_material_need_bindings",
    "execute_search_judgment_read_assessment_action",
    "execute_search_judgment_read_binding_action",
    "execute_search_judgment_read_source_and_custody",
    "execute_searchos_candidate_read_to_custody",
    "validate_binding_backed_acquisition_need_proposal",
    "validate_search_judgment_read_assessment_reduction",
    "validate_search_judgment_read_binding_reduction",
    "validate_search_judgment_read_custody_reduction",
    "validate_search_judgment_read_proposal_reduction",
]
