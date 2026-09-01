"""Experimental thin ordinary semantic and terminal corridors.

Phase 1 composes Component Analyst, canonical RunKernel component admission,
and Cross without installing scheduler or Graph authority.  Phase 2 carries
those exact transient results through the existing Sufficiency, FinalAnswerPacket,
and Author owners.  Neither path creates scheduler, lease, batch, Graph V1,
D-prime, or Scrutineer state.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from core.component_analyst_evidence_set import (
    ComponentAnalystEvidenceSetError,
    component_analyst_evidence_member_code_evidence,
    validate_component_analyst_evidence_sets,
)
from core.component_work_graph_v1 import MAX_SYNTHESIS_DEPTH
from core.multicomponent_component_admission import (
    MULTICOMPONENT_COMPONENT_ADMISSION_OWNER,
    MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
    component_analyst_input_packet,
    execute_multicomponent_component_admission,
)
from core.multicomponent_graph_scheduling import (
    canonical_multicomponent_contract_ref,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    MulticomponentRoleRuntimeError,
    execute_multicomponent_role_call,
    role_artifact_ref,
    safe_packet_digest,
    validate_multicomponent_role_artifact,
)
from core.ordinary_multicomponent_synthesis_runtime import (
    build_component_analyst_admission_semantic_material,
    component_analyst_evidence_set_is_searchos_read_custody,
)
from core.quantitative_specialist_product_activation import (
    QUANTITATIVE_SYNTHESIS_TARGET_KEY_RULE,
    build_quantitative_specialist_proposal_contract,
    build_synthesis_quantitative_source_catalog,
)
from core.semantic_contract_foundation import inference_depth_ceiling_for_mode

DIRECT_CROSS_LOGICAL_EVALUATION_KEY = "thin-ordinary-direct-cross"
_SCHEDULER_STAGE = "multicomponent_graph_scheduler"
_GRAPH_V1_STAGE = "multicomponent_component_work_graph_v1"


class OrdinaryDirectSemanticCorridorError(ValueError):
    """Raised when the experimental direct corridor loses exact mechanics."""


@dataclass(frozen=True, slots=True)
class OrdinaryDirectSemanticCorridorResult:
    """Transient exact Phase-1 result; never a canonical runtime authority."""

    component_admission_refs: tuple[Mapping[str, Any], ...]
    cross_artifact: Mapping[str, Any] | None
    cross_input_packet: Mapping[str, Any] | None
    component_analyst_input_packets: Mapping[str, Mapping[str, Any]]
    component_evidence_sets: Mapping[str, Mapping[str, Any]]
    query: str
    requested_synthesis_directive: str


@dataclass(frozen=True, slots=True)
class OrdinaryDirectTerminalCorridorResult:
    """Existing-owner handoffs returned by the transient Phase-2 coordinator."""

    direct_result: OrdinaryDirectSemanticCorridorResult
    direct_semantic_consumption: Mapping[str, Any]
    selected_evidence_passages: tuple[Mapping[str, Any], ...]
    sufficiency_handoff: Any
    final_answer_packet_handoff: Any
    author_handoff: Any | None


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any, *, limit: int = 400) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    return text[:limit] if text else None


def _exact_requested_synthesis_directive(
    contract: Mapping[str, Any],
    supplied: str,
    *,
    component_count: int,
) -> str:
    """Bind the transient directive to accepted question-meaning authority."""

    canonical = _clean_text(
        _safe_mapping(contract.get("question_meaning_metadata")).get(
            "requested_synthesis_directive"
        ),
        limit=360,
    )
    requested = _clean_text(supplied, limit=360)
    if canonical:
        if requested != canonical:
            raise OrdinaryDirectSemanticCorridorError(
                "direct corridor synthesis directive is not current contract authority"
            )
        return canonical
    if component_count >= 2 or requested:
        raise OrdinaryDirectSemanticCorridorError(
            "direct corridor requires an exact contract-authored synthesis directive"
        )
    return ""


def _active_contract(run_kernel: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contract = _safe_mapping(
        run_kernel.state.current_answer_contract
        or run_kernel.state.initial_answer_contract
    )
    if (
        not contract
        or contract.get("canonical_state") is not True
        or contract.get("run_id") != run_kernel.state.run_id
        or contract.get("request_id") != run_kernel.state.request_id
        or not contract.get("accepted_contract_version")
        or not contract.get("accepted_contract_digest")
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct corridor requires the exact active accepted contract"
        )
    component_refs = [
        deepcopy(dict(item))
        for item in contract.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping)
    ]
    component_ids = [str(item.get("component_id") or "") for item in component_refs]
    declared_count = contract.get("accepted_answer_component_count")
    if (
        not 1 <= len(component_refs) <= 5
        or any(not component_id for component_id in component_ids)
        or len(component_ids) != len(set(component_ids))
        or (declared_count is not None and declared_count != len(component_refs))
        or any(
            not item.get("component_revision")
            or not item.get("component_digest")
            or "direct" not in list(item.get("allowed_support_kinds") or ("direct",))
            for item in component_refs
        )
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct corridor accepted component binding is malformed"
        )
    return deepcopy(contract), component_refs


def _require_direct_boundary(run_kernel: Any) -> None:
    if (
        run_kernel.state.projections.get(_SCHEDULER_STAGE)
        or run_kernel.state.projections.get(_GRAPH_V1_STAGE)
        or _safe_mapping(run_kernel.state.multicomponent_scheduler_context)
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct corridor cannot consume scheduler or Graph authority"
        )
    forbidden_roles = {"synthesis_dprime", "scrutineer"}
    if any(
        str(action.inputs.get("role") or "") in forbidden_roles
        for action in run_kernel.state.issued_actions.values()
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct corridor cannot follow D-prime or Scrutineer work"
        )


def _validated_evidence_sets(
    run_kernel: Any,
    *,
    component_refs: Sequence[Mapping[str, Any]],
    component_evidence_sets: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    try:
        evidence_sets = validate_component_analyst_evidence_sets(
            component_evidence_sets
        )
    except ComponentAnalystEvidenceSetError as exc:
        raise OrdinaryDirectSemanticCorridorError(str(exc)) from exc
    component_ids = [str(item.get("component_id") or "") for item in component_refs]
    if set(evidence_sets) != set(component_ids):
        raise OrdinaryDirectSemanticCorridorError(
            "direct corridor requires one exact evidence set per accepted component"
        )
    ledger_candidate_ids = {
        str(_safe_mapping(item).get("candidate_id") or "")
        for item in run_kernel.state.evidence_ledger.to_projection().to_dict().get(
            "candidate_records", ()
        )
        if _safe_mapping(item).get("candidate_id")
    }
    for component_id in component_ids:
        member_component_bindings = [
            str(
                _safe_mapping(
                    _safe_mapping(
                        _safe_mapping(member).get("code_binding")
                    ).get("material_identity")
                ).get("searchos_slot_identity", {})
                .get("component_id")
                or ""
            )
            for member in evidence_sets[component_id]["members"]
        ]
        if any(member_component_bindings) and (
            any(not item for item in member_component_bindings)
            or set(member_component_bindings) != {component_id}
        ):
            raise OrdinaryDirectSemanticCorridorError(
                "direct corridor evidence member has a cross-component binding"
            )
        evidence_ref_ids = {
            str(
                component_analyst_evidence_member_code_evidence(member).get(
                    "evidence_ref_id"
                )
                or ""
            )
            for member in evidence_sets[component_id]["members"]
        }
        if (
            not evidence_ref_ids
            or "" in evidence_ref_ids
            or not evidence_ref_ids.issubset(ledger_candidate_ids)
        ):
            raise OrdinaryDirectSemanticCorridorError(
                "direct corridor evidence member is not current ledger authority"
            )
    return evidence_sets


def _current_component_admissions(
    run_kernel: Any,
    *,
    contract: Mapping[str, Any],
    component_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    projection = _safe_mapping(
        run_kernel.state.projections.get(MULTICOMPONENT_COMPONENT_ADMISSION_STAGE)
    )
    refs = [
        deepcopy(dict(item))
        for item in projection.get("component_admission_refs") or ()
        if isinstance(item, Mapping)
    ]
    projection_core = {
        key: deepcopy(value)
        for key, value in projection.items()
        if key != "projection_digest"
    }
    expected_projection_fields = {
        "schema_version",
        "owner",
        "canonical_state",
        "trace_only",
        "storage_only",
        "run_id",
        "request_id",
        "accepted_contract_version",
        "accepted_contract_digest",
        "component_admission_refs",
        "component_count",
        "admitted_component_count",
        "blocked_component_count",
        "logical_component_analyst_evaluations",
        "physical_component_analyst_calls",
        "latest_action_id",
        "projection_digest",
    }
    if (
        set(projection) != expected_projection_fields
        or projection.get("schema_version")
        != "multicomponent_component_admission_projection_v1"
        or projection.get("owner") != MULTICOMPONENT_COMPONENT_ADMISSION_OWNER
        or projection.get("trace_only") is not False
        or projection.get("storage_only") is not False
        or projection.get("projection_digest")
        != safe_packet_digest(projection_core)
        or projection.get("component_count") != len(refs)
        or projection.get("admitted_component_count")
        != sum(
            item.get("admission_status")
            in {"admitted", "admitted_with_caveats"}
            for item in refs
        )
        or projection.get("blocked_component_count")
        != sum(
            item.get("admission_status")
            not in {"admitted", "admitted_with_caveats"}
            for item in refs
        )
        or projection.get("logical_component_analyst_evaluations")
        != sum(
            int(item.get("logical_component_analyst_evaluations") or 0)
            for item in refs
        )
        or projection.get("physical_component_analyst_calls")
        != sum(
            int(item.get("physical_component_analyst_calls") or 0)
            for item in refs
        )
        or not refs
        or projection.get("latest_action_id") != refs[-1].get("action_id")
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct corridor component admission projection lost canonical integrity"
        )
    component_ids = [str(item.get("component_id") or "") for item in component_refs]
    by_id = {str(item.get("component_id") or ""): item for item in refs}
    if (
        projection.get("canonical_state") is not True
        or projection.get("run_id") != run_kernel.state.run_id
        or projection.get("request_id") != run_kernel.state.request_id
        or projection.get("accepted_contract_version")
        != contract.get("accepted_contract_version")
        or projection.get("accepted_contract_digest")
        != contract.get("accepted_contract_digest")
        or len(refs) != len(component_refs)
        or set(by_id) != set(component_ids)
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct corridor component admissions are not the exact current set"
        )
    ordered: list[dict[str, Any]] = []
    canonical_terminal_statuses = {
        "admitted",
        "admitted_with_caveats",
        "unsupported",
        "blocked",
    }
    support_bearing_statuses = {"admitted", "admitted_with_caveats"}
    support_ref_fields = (
        "admitted_claim_ref",
        "semantic_observation_ref",
        "component_coverage_ref",
    )
    for component in component_refs:
        component_id = str(component["component_id"])
        admission = by_id[component_id]
        admission_status = admission.get("admission_status")
        case_ref = admission.get("component_analyst_case_ref")
        completed_case = _safe_mapping(
            run_kernel.state.projections.get(
                f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{component_id}"
            )
        )
        try:
            expected_case_ref = role_artifact_ref(completed_case)
        except MulticomponentRoleRuntimeError:
            expected_case_ref = {}
        support_refs_are_mappings = all(
            field in admission and isinstance(admission.get(field), Mapping)
            for field in support_ref_fields
        )
        support_refs = tuple(
            _safe_mapping(admission.get(field)) for field in support_ref_fields
        )
        if (
            admission.get("schema_version")
            != "multicomponent_component_admission_ref_v1"
            or admission.get("owner") != MULTICOMPONENT_COMPONENT_ADMISSION_OWNER
            or admission.get("canonical_state") is not True
            or admission.get("run_id") != run_kernel.state.run_id
            or admission.get("request_id") != run_kernel.state.request_id
            or admission.get("accepted_contract_version")
            != contract.get("accepted_contract_version")
            or admission.get("accepted_contract_digest")
            != contract.get("accepted_contract_digest")
            or admission.get("component_id") != component_id
            or admission.get("logical_evaluation_key") != component_id
            or admission.get("component_revision")
            != component.get("component_revision")
            or admission.get("component_digest") != component.get("component_digest")
            or admission_status not in canonical_terminal_statuses
            or admission.get("current") is not True
            or admission.get("stale") is not False
            or not isinstance(case_ref, Mapping)
            or not case_ref
            or dict(case_ref) != expected_case_ref
            or not support_refs_are_mappings
            or (
                admission_status in support_bearing_statuses
                and not all(support_refs)
            )
            or (
                admission_status not in support_bearing_statuses
                and any(support_refs)
            )
        ):
            raise OrdinaryDirectSemanticCorridorError(
                f"direct corridor component admission is stale or incomplete: {component_id}"
            )
        ordered.append(admission)
    return ordered


def _admitted_component_view(
    component: Mapping[str, Any],
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    claim = _safe_mapping(admission.get("admitted_claim_ref"))
    return {
        "component_id": component.get("component_id"),
        "component_revision": component.get("component_revision"),
        "component_digest": component.get("component_digest"),
        "component_label": component.get("user_facing_label"),
        "component_question": component.get("user_facing_question"),
        "admission_status": admission.get("admission_status"),
        "current": admission.get("current") is True,
        "stale": admission.get("stale") is True,
        "component_admission_action_ref": {
            "action_id": admission.get("action_id"),
            "owner": admission.get("owner"),
        },
        "component_analyst_case_ref": deepcopy(
            _safe_mapping(admission.get("component_analyst_case_ref"))
        ),
        "claim_text": claim.get("claim_text"),
        "claim_id": claim.get("claim_id"),
        "claim_digest": claim.get("claim_digest"),
        "direct_claim_ref": deepcopy(claim),
        "admitted_claim_ref": deepcopy(claim),
        "semantic_observation_ref": deepcopy(
            _safe_mapping(admission.get("semantic_observation_ref"))
        ),
        "component_coverage_ref": deepcopy(
            _safe_mapping(admission.get("component_coverage_ref"))
        ),
        "evidence_refs": [
            deepcopy(dict(item))
            for item in admission.get("evidence_refs") or ()
            if isinstance(item, Mapping)
        ],
        "required_caveats": list(admission.get("required_caveats") or ()),
        "preserved_nonclaims": list(admission.get("preserved_nonclaims") or ()),
        "blocker_refs": [
            deepcopy(dict(item)) if isinstance(item, Mapping) else item
            for item in admission.get("blocker_refs") or ()
        ],
        "direct_output_eligible": True,
    }


def _build_direct_cross_input_packet(
    *,
    run_kernel: Any,
    component_analyst_input_packets: Mapping[str, Mapping[str, Any]],
    component_analyst_evidence_sets: Mapping[str, Mapping[str, Any]],
    requested_synthesis_directive: str,
    requested_mode: str,
) -> dict[str, Any]:
    """Build the one transient Cross packet from fresh canonical admissions."""

    _require_direct_boundary(run_kernel)
    contract, component_refs = _active_contract(run_kernel)
    admissions = _current_component_admissions(
        run_kernel,
        contract=contract,
        component_refs=component_refs,
    )
    if any(
        admission.get("admission_status")
        not in {"admitted", "admitted_with_caveats"}
        for admission in admissions
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct Cross requires support-bearing canonical component admissions"
        )
    component_ids = [str(item["component_id"]) for item in component_refs]
    packets = {
        str(key): deepcopy(dict(value))
        for key, value in component_analyst_input_packets.items()
        if isinstance(value, Mapping)
    }
    evidence_sets = _validated_evidence_sets(
        run_kernel,
        component_refs=component_refs,
        component_evidence_sets=component_analyst_evidence_sets,
    )
    if set(packets) != set(component_ids):
        raise OrdinaryDirectSemanticCorridorError(
            "direct Cross requires every exact Component Analyst input packet"
        )
    for component, component_id in zip(component_refs, component_ids, strict=True):
        expected = component_analyst_input_packet(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            accepted_contract=contract,
            component_ref=component,
            component_evidence_set=evidence_sets[component_id],
        )
        if packets[component_id] != expected:
            raise OrdinaryDirectSemanticCorridorError(
                "direct Cross Component Analyst input is not exact current input"
            )
    directive = _clean_text(requested_synthesis_directive, limit=360)
    mode = _clean_text(requested_mode, limit=40) or "Balanced"
    if len(component_refs) < 2 or not directive:
        raise OrdinaryDirectSemanticCorridorError(
            "direct Cross requires at least two admitted components and one directive"
        )
    component_views = [
        _admitted_component_view(component, admission)
        for component, admission in zip(component_refs, admissions, strict=True)
    ]
    packet = {
        "supported_query_class": (
            "ordinary-bounded-multicomponent-factual-synthesis-v1"
        ),
        "accepted_contract_ref": canonical_multicomponent_contract_ref(contract),
        "accepted_component_refs": deepcopy(component_refs),
        "semantic_inference_profile": {
            "requested_mode": mode,
            "profile_ceiling": inference_depth_ceiling_for_mode(mode),
            "graph_hard_ceiling": MAX_SYNTHESIS_DEPTH,
        },
        "requested_synthesis_directive": directive,
        "dependency_posture": "unknown_until_cross_component_analysis",
        # One transient compatibility projection for the installed Cross input
        # field. These are admitted-component views, never Graph V1 nodes.
        "component_nodes": component_views,
    }
    packet["quantitative_source_catalog"] = (
        build_synthesis_quantitative_source_catalog(
            component_nodes=component_views,
            component_analyst_input_packets=packets,
            component_analyst_evidence_sets=evidence_sets,
        )
    )
    packet["quantitative_specialist_proposal_contract"] = (
        build_quantitative_specialist_proposal_contract(
            target_kind="synthesis",
            target_key_or_rule=QUANTITATIVE_SYNTHESIS_TARGET_KEY_RULE,
            allowed_source_local_keys=tuple(
                f"component_{index:02d}"
                for index, _component in enumerate(component_refs, start=1)
            ),
        )
    )
    return packet


def _validate_cross_proposal_mechanics(
    semantic_output: Mapping[str, Any],
    *,
    component_ids: Sequence[str],
) -> None:
    proposals = [
        _safe_mapping(item)
        for item in semantic_output.get("synthesis_proposals") or ()
    ]
    proposal_keys = [str(item.get("synthesis_key") or "") for item in proposals]
    known_components = set(component_ids)
    known_proposals = set(proposal_keys)
    dependencies: dict[str, list[str]] = {}
    for proposal in proposals:
        key = str(proposal.get("synthesis_key") or "")
        component_inputs = [
            str(item) for item in proposal.get("component_inputs") or ()
        ]
        synthesis_inputs = [
            str(item) for item in proposal.get("synthesis_inputs") or ()
        ]
        if (
            any(item not in known_components for item in component_inputs)
            or len(component_inputs) != len(set(component_inputs))
        ):
            raise OrdinaryDirectSemanticCorridorError(
                "direct Cross proposal has an unknown or duplicate component binding"
            )
        if (
            any(item not in known_proposals or item == key for item in synthesis_inputs)
            or len(synthesis_inputs) != len(set(synthesis_inputs))
        ):
            raise OrdinaryDirectSemanticCorridorError(
                "direct Cross proposal has an unknown, duplicate, or self dependency"
            )
        dependencies[key] = synthesis_inputs

    visiting: set[str] = set()
    depths: dict[str, int] = {}

    def semantic_depth(key: str) -> int:
        if key in visiting:
            raise OrdinaryDirectSemanticCorridorError(
                "direct Cross proposal dependencies contain a cycle"
            )
        if key in depths:
            return depths[key]
        visiting.add(key)
        depth = 1 + max(
            (semantic_depth(parent) for parent in dependencies.get(key, ())),
            default=0,
        )
        visiting.remove(key)
        if depth > MAX_SYNTHESIS_DEPTH:
            raise OrdinaryDirectSemanticCorridorError(
                "direct Cross proposal dependency depth exceeds the installed bound"
            )
        depths[key] = depth
        return depth

    for proposal_key in proposal_keys:
        semantic_depth(proposal_key)


def _validate_direct_cross_result_binding(
    *,
    run_kernel: Any,
    cross_input_packet: Mapping[str, Any],
    cross_artifact: Mapping[str, Any],
    logical_evaluation_key: str = DIRECT_CROSS_LOGICAL_EVALUATION_KEY,
) -> dict[str, Any]:
    """Reprove one Cross artifact against the still-current admitted inputs."""

    _require_direct_boundary(run_kernel)
    contract, component_refs = _active_contract(run_kernel)
    admissions = _current_component_admissions(
        run_kernel,
        contract=contract,
        component_refs=component_refs,
    )
    if any(
        admission.get("admission_status")
        not in {"admitted", "admitted_with_caveats"}
        for admission in admissions
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct Cross requires support-bearing canonical component admissions"
        )
    packet = deepcopy(dict(cross_input_packet))
    expected_views = [
        _admitted_component_view(component, admission)
        for component, admission in zip(component_refs, admissions, strict=True)
    ]
    if (
        packet.get("accepted_contract_ref")
        != canonical_multicomponent_contract_ref(contract)
        or packet.get("accepted_component_refs") != component_refs
        or packet.get("component_nodes") != expected_views
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct Cross input is stale against current admitted components"
        )
    artifact = validate_multicomponent_role_artifact(
        cross_artifact,
        expected_role=ROLE_CROSS_COMPONENT_ANALYST,
    )
    if (
        artifact.get("run_id") != run_kernel.state.run_id
        or artifact.get("request_id") != run_kernel.state.request_id
        or artifact.get("logical_evaluation_key") != logical_evaluation_key
        or artifact.get("input_packet_digest") != safe_packet_digest(packet)
        or artifact.get("accepted_contract_ref")
        != packet.get("accepted_contract_ref")
        or _safe_mapping(artifact.get("graph_ref"))
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct Cross artifact exact-input binding mismatch"
        )
    completed = _safe_mapping(
        run_kernel.state.projections.get(
            f"multicomponent_role:{ROLE_CROSS_COMPONENT_ANALYST}:"
            f"{logical_evaluation_key}"
        )
    )
    if not completed or role_artifact_ref(completed) != role_artifact_ref(artifact):
        raise OrdinaryDirectSemanticCorridorError(
            "direct Cross requires the exact completed RunKernel artifact"
        )
    action_ref = _safe_mapping(artifact.get("authorized_action_ref"))
    action = run_kernel.state.issued_actions.get(str(action_ref.get("action_id") or ""))
    if (
        action is None
        or action.run_id != run_kernel.state.run_id
        or action.inputs.get("role") != ROLE_CROSS_COMPONENT_ANALYST
        or action.inputs.get("input_packet_digest") != safe_packet_digest(packet)
        or action.inputs.get("logical_evaluation_key") != logical_evaluation_key
        or action.action_id not in run_kernel.state.reduced_action_ids
    ):
        raise OrdinaryDirectSemanticCorridorError(
            "direct Cross RunKernel action binding mismatch"
        )
    component_ids = [str(item["component_id"]) for item in component_refs]
    _validate_cross_proposal_mechanics(
        artifact["semantic_output"],
        component_ids=component_ids,
    )
    return artifact


def execute_ordinary_direct_semantic_corridor_with_context(
    *,
    run_kernel: Any,
    component_evidence_sets: Mapping[str, Mapping[str, Any]],
    query: str,
    requested_synthesis_directive: str,
    requested_mode: str,
    strict_one_shot_transport: Callable[..., Any],
    clean_json_response: Callable[[str], str] | None,
    provider: str,
    model: str,
    use_reasoning: bool,
    effort: str = "medium",
) -> OrdinaryDirectSemanticCorridorResult:
    """Execute Phase 1 and retain only the transient exact inputs Phase 2 needs."""

    _require_direct_boundary(run_kernel)
    contract, component_refs = _active_contract(run_kernel)
    exact_directive = _exact_requested_synthesis_directive(
        contract,
        requested_synthesis_directive,
        component_count=len(component_refs),
    )
    evidence_sets = _validated_evidence_sets(
        run_kernel,
        component_refs=component_refs,
        component_evidence_sets=component_evidence_sets,
    )
    packets: dict[str, dict[str, Any]] = {}
    returned_admissions: list[dict[str, Any]] = []
    role_kwargs = {
        "strict_one_shot_transport": strict_one_shot_transport,
        "clean_json_response": clean_json_response,
        "provider": provider,
        "model": model,
        "use_reasoning": use_reasoning,
        "effort": effort,
    }
    for component_ref in component_refs:
        component_id = str(component_ref["component_id"])
        evidence_set = evidence_sets[component_id]
        packet = component_analyst_input_packet(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            accepted_contract=contract,
            component_ref=component_ref,
            component_evidence_set=evidence_set,
        )
        packets[component_id] = packet
        analyst_artifact = execute_multicomponent_role_call(
            run_kernel=run_kernel,
            role=ROLE_COMPONENT_ANALYST,
            input_packet=packet,
            logical_evaluation_key=component_id,
            **role_kwargs,
        )
        observation, content_refs, coverage = (
            build_component_analyst_admission_semantic_material(
                run_kernel=run_kernel,
                component_ref=component_ref,
                component_evidence_set=evidence_set,
                analyst_artifact=analyst_artifact,
                query=query,
            )
        )
        returned_admissions.append(
            execute_multicomponent_component_admission(
                run_kernel=run_kernel,
                component_id=component_id,
                analyst_artifact=analyst_artifact,
                analyst_input_packet=packet,
                component_evidence_set=evidence_set,
                semantic_observation=observation,
                sanitized_content_references=content_refs,
                component_coverage_record=coverage,
                logical_evaluation_key=component_id,
                allow_searchos_semantic_requirement_historical_gap_exception=(
                    component_analyst_evidence_set_is_searchos_read_custody(
                        evidence_set
                    )
                ),
            )
        )
        _require_direct_boundary(run_kernel)

    current_admissions = _current_component_admissions(
        run_kernel,
        contract=contract,
        component_refs=component_refs,
    )
    if returned_admissions != current_admissions:
        raise OrdinaryDirectSemanticCorridorError(
            "direct corridor admission return lost current RunKernel binding"
        )
    if any(
        admission.get("admission_status")
        not in {"admitted", "admitted_with_caveats"}
        for admission in current_admissions
    ):
        return OrdinaryDirectSemanticCorridorResult(
            component_admission_refs=tuple(deepcopy(current_admissions)),
            cross_artifact=None,
            cross_input_packet=None,
            component_analyst_input_packets=deepcopy(packets),
            component_evidence_sets=deepcopy(evidence_sets),
            query=str(query),
            requested_synthesis_directive=exact_directive,
        )
    if len(component_refs) == 1:
        return OrdinaryDirectSemanticCorridorResult(
            component_admission_refs=tuple(deepcopy(current_admissions)),
            cross_artifact=None,
            cross_input_packet=None,
            component_analyst_input_packets=deepcopy(packets),
            component_evidence_sets=deepcopy(evidence_sets),
            query=str(query),
            requested_synthesis_directive=exact_directive,
        )

    cross_input = _build_direct_cross_input_packet(
        run_kernel=run_kernel,
        component_analyst_input_packets=packets,
        component_analyst_evidence_sets=evidence_sets,
        requested_synthesis_directive=exact_directive,
        requested_mode=requested_mode,
    )
    cross_artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=cross_input,
        logical_evaluation_key=DIRECT_CROSS_LOGICAL_EVALUATION_KEY,
        **role_kwargs,
    )
    bound_cross = _validate_direct_cross_result_binding(
        run_kernel=run_kernel,
        cross_input_packet=cross_input,
        cross_artifact=cross_artifact,
    )
    return OrdinaryDirectSemanticCorridorResult(
        component_admission_refs=tuple(deepcopy(current_admissions)),
        cross_artifact=deepcopy(bound_cross),
        cross_input_packet=deepcopy(cross_input),
        component_analyst_input_packets=deepcopy(packets),
        component_evidence_sets=deepcopy(evidence_sets),
        query=str(query),
        requested_synthesis_directive=exact_directive,
    )


def _reprove_direct_semantic_result(
    *,
    run_kernel: Any,
    direct_result: OrdinaryDirectSemanticCorridorResult,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Any] | None,
]:
    """Rebind the transient Phase-1 result to current RunKernel state."""

    _require_direct_boundary(run_kernel)
    contract, component_refs = _active_contract(run_kernel)
    admissions = _current_component_admissions(
        run_kernel,
        contract=contract,
        component_refs=component_refs,
    )
    supplied_admissions = [
        deepcopy(dict(item)) for item in direct_result.component_admission_refs
    ]
    if supplied_admissions != admissions:
        raise OrdinaryDirectSemanticCorridorError(
            "terminal corridor component admissions are not exact current refs"
        )
    directive = _exact_requested_synthesis_directive(
        contract,
        direct_result.requested_synthesis_directive,
        component_count=len(component_refs),
    )
    evidence_sets = _validated_evidence_sets(
        run_kernel,
        component_refs=component_refs,
        component_evidence_sets=direct_result.component_evidence_sets,
    )
    packets = {
        str(key): deepcopy(dict(value))
        for key, value in direct_result.component_analyst_input_packets.items()
        if isinstance(value, Mapping)
    }
    component_ids = [str(item["component_id"]) for item in component_refs]
    admissions_by_id = {
        str(item.get("component_id") or ""): item for item in admissions
    }
    if set(packets) != set(component_ids):
        raise OrdinaryDirectSemanticCorridorError(
            "terminal corridor requires every exact Component Analyst input"
        )
    for component in component_refs:
        component_id = str(component["component_id"])
        expected_packet = component_analyst_input_packet(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            accepted_contract=contract,
            component_ref=component,
            component_evidence_set=evidence_sets[component_id],
        )
        current_case_ref = _safe_mapping(
            admissions_by_id[component_id].get("component_analyst_case_ref")
        )
        if (
            packets[component_id] != expected_packet
            or current_case_ref.get("input_packet_digest")
            != safe_packet_digest(expected_packet)
        ):
            raise OrdinaryDirectSemanticCorridorError(
                "terminal corridor Component Analyst input is not exact current input"
            )

    all_supporting = all(
        item.get("admission_status") in {"admitted", "admitted_with_caveats"}
        for item in admissions
    )
    cross_artifact: dict[str, Any] | None = None
    if len(component_refs) >= 2 and all_supporting:
        if not isinstance(direct_result.cross_input_packet, Mapping) or not isinstance(
            direct_result.cross_artifact,
            Mapping,
        ):
            raise OrdinaryDirectSemanticCorridorError(
                "terminal corridor requires the exact completed Cross result"
            )
        cross_artifact = _validate_direct_cross_result_binding(
            run_kernel=run_kernel,
            cross_input_packet=direct_result.cross_input_packet,
            cross_artifact=direct_result.cross_artifact,
        )
        if (
            _clean_text(
                _safe_mapping(direct_result.cross_input_packet).get(
                    "requested_synthesis_directive"
                ),
                limit=360,
            )
            != directive
        ):
            raise OrdinaryDirectSemanticCorridorError(
                "terminal corridor Cross directive is not current contract authority"
            )
    elif direct_result.cross_artifact is not None or direct_result.cross_input_packet is not None:
        raise OrdinaryDirectSemanticCorridorError(
            "terminal corridor received Cross state without lawful supporting inputs"
        )
    return contract, component_refs, admissions, evidence_sets, cross_artifact


def _selected_direct_evidence_passages(
    *,
    admissions: Sequence[Mapping[str, Any]],
    evidence_sets: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Select only exact Analyst-used passages for FAP/citation mechanics."""

    selected: list[dict[str, Any]] = []
    seen_evidence_ids: set[str] = set()
    for admission in admissions:
        component_id = str(admission.get("component_id") or "")
        evidence_set = _safe_mapping(evidence_sets.get(component_id))
        members = [
            deepcopy(dict(item))
            for item in evidence_set.get("members") or ()
            if isinstance(item, Mapping)
        ]
        by_evidence_id = {
            str(
                component_analyst_evidence_member_code_evidence(member).get(
                    "evidence_ref_id"
                )
                or ""
            ): member
            for member in members
        }
        for evidence_ref in admission.get("evidence_refs") or ():
            ref = _safe_mapping(evidence_ref)
            evidence_id = str(ref.get("evidence_ref_id") or "")
            member = by_evidence_id.get(evidence_id)
            if not evidence_id or member is None:
                raise OrdinaryDirectSemanticCorridorError(
                    "terminal corridor evidence selection lost Analyst binding"
                )
            if evidence_id in seen_evidence_ids:
                continue
            passage = _safe_mapping(member.get("passage"))
            if not passage or str(passage.get("candidate_id") or evidence_id) != evidence_id:
                raise OrdinaryDirectSemanticCorridorError(
                    "terminal corridor selected passage identity is malformed"
                )
            seen_evidence_ids.add(evidence_id)
            selected.append(deepcopy(passage))
    return tuple(selected)


def execute_ordinary_direct_terminal_corridor_from_result(
    *,
    run_kernel: Any,
    direct_result: OrdinaryDirectSemanticCorridorResult,
    runtime_scope: Mapping[str, Any],
    default_system: Mapping[str, str],
    author_ask_model: Callable[..., Any],
    author_system_prompt_registry: Mapping[str, str],
    base_url: str | None = None,
    api_key: str | None = None,
    stream_display: Callable[[Any], Any] | None = None,
) -> OrdinaryDirectTerminalCorridorResult:
    """Carry an exact Phase-1 result through existing terminal product owners."""

    from core.author_execution_runtime import execute_author_handoff_from_scope
    from core.direct_semantic_sufficiency_consumption_runtime import (
        DirectSemanticSufficiencyConsumptionError,
        build_direct_semantic_sufficiency_consumption,
    )
    from core.final_answer_packet_runtime import (
        prepare_final_answer_packet_author_handoff_from_scope,
    )
    from core.run_authority_sufficiency_runtime import (
        execute_sufficiency_judgment_handoff_from_scope,
    )

    contract, _component_refs, admissions, evidence_sets, cross_artifact = (
        _reprove_direct_semantic_result(
            run_kernel=run_kernel,
            direct_result=direct_result,
        )
    )
    if runtime_scope.get("scrutineer_flags"):
        raise OrdinaryDirectSemanticCorridorError(
            "terminal corridor does not execute routine Scrutineer policy"
        )
    supplied_query = str(runtime_scope.get("query") or "")
    if supplied_query and supplied_query != direct_result.query:
        raise OrdinaryDirectSemanticCorridorError(
            "terminal corridor query does not match the Phase-1 execution"
        )
    try:
        direct_consumption = build_direct_semantic_sufficiency_consumption(
            accepted_contract=contract,
            component_admission_refs=admissions,
            cross_component_artifact=cross_artifact,
            requested_synthesis_directive=(
                direct_result.requested_synthesis_directive
            ),
        )
    except DirectSemanticSufficiencyConsumptionError as exc:
        raise OrdinaryDirectSemanticCorridorError(str(exc)) from exc

    selected_passages = _selected_direct_evidence_passages(
        admissions=admissions,
        evidence_sets=evidence_sets,
    )
    exact_scope = dict(runtime_scope)
    exact_scope.update(
        {
            "run_id": run_kernel.state.run_id,
            "query": direct_result.query,
            "evidence_ledger_projection": (
                run_kernel.state.evidence_ledger.to_projection().to_dict()
            ),
            "run_contract_projection": deepcopy(
                _safe_mapping(run_kernel.state.run_contract_projection)
            ),
            "answer_contract_projection": deepcopy(contract),
            "accepted_answer_contract_projection": deepcopy(contract),
            "direct_semantic_consumption": deepcopy(direct_consumption),
            "final_top_evidence": [deepcopy(item) for item in selected_passages],
            "author_evidence": [deepcopy(item) for item in selected_passages],
            "ordered_sources": [
                str(item.get("source_id") or item.get("url") or "")
                for item in selected_passages
                if item.get("source_id") or item.get("url")
            ],
            "unique_source_urls": {
                str(item["url"]): item.get("source_id")
                for item in selected_passages
                if item.get("url")
            },
            "scrutineer_flags": [],
            "synth_was_insufficient": False,
        }
    )
    if not exact_scope["run_contract_projection"]:
        raise OrdinaryDirectSemanticCorridorError(
            "terminal corridor requires the existing RunContract authority"
        )

    sufficiency_handoff = execute_sufficiency_judgment_handoff_from_scope(
        run_kernel,
        exact_scope,
        smart_model_enabled=False,
    )
    _require_direct_boundary(run_kernel)
    exact_scope["sufficiency_judgment_projection"] = deepcopy(
        sufficiency_handoff.projection
    )
    final_answer_packet_handoff = (
        prepare_final_answer_packet_author_handoff_from_scope(
            run_kernel,
            exact_scope,
            default_system=default_system,
        )
    )
    _require_direct_boundary(run_kernel)
    author_handoff = None
    if not final_answer_packet_handoff.author_input_blocked:
        if final_answer_packet_handoff.author_payload is None:
            raise OrdinaryDirectSemanticCorridorError(
                "terminal corridor FAP did not produce Author input"
            )
        exact_scope["final_answer_packet_action"] = (
            final_answer_packet_handoff.action
        )
        exact_scope["final_answer_author_payload"] = (
            final_answer_packet_handoff.author_payload
        )
        author_handoff = execute_author_handoff_from_scope(
            run_kernel,
            exact_scope,
            ask_model=author_ask_model,
            system_prompt_registry=author_system_prompt_registry,
            base_url=base_url,
            api_key=api_key,
            stream_display=stream_display,
        )
        _require_direct_boundary(run_kernel)
    return OrdinaryDirectTerminalCorridorResult(
        direct_result=direct_result,
        direct_semantic_consumption=deepcopy(direct_consumption),
        selected_evidence_passages=tuple(
            deepcopy(item) for item in selected_passages
        ),
        sufficiency_handoff=sufficiency_handoff,
        final_answer_packet_handoff=final_answer_packet_handoff,
        author_handoff=author_handoff,
    )


def execute_ordinary_direct_terminal_corridor(
    *,
    run_kernel: Any,
    component_evidence_sets: Mapping[str, Mapping[str, Any]],
    query: str,
    requested_synthesis_directive: str,
    requested_mode: str,
    strict_one_shot_transport: Callable[..., Any],
    clean_json_response: Callable[[str], str] | None,
    provider: str,
    model: str,
    use_reasoning: bool,
    runtime_scope: Mapping[str, Any],
    default_system: Mapping[str, str],
    author_ask_model: Callable[..., Any],
    author_system_prompt_registry: Mapping[str, str],
    effort: str = "medium",
    base_url: str | None = None,
    api_key: str | None = None,
    stream_display: Callable[[Any], Any] | None = None,
) -> OrdinaryDirectTerminalCorridorResult:
    """Execute the branch-only Phase-1 + Phase-2 ordinary corridor."""

    direct_result = execute_ordinary_direct_semantic_corridor_with_context(
        run_kernel=run_kernel,
        component_evidence_sets=component_evidence_sets,
        query=query,
        requested_synthesis_directive=requested_synthesis_directive,
        requested_mode=requested_mode,
        strict_one_shot_transport=strict_one_shot_transport,
        clean_json_response=clean_json_response,
        provider=provider,
        model=model,
        use_reasoning=use_reasoning,
        effort=effort,
    )
    return execute_ordinary_direct_terminal_corridor_from_result(
        run_kernel=run_kernel,
        direct_result=direct_result,
        runtime_scope=runtime_scope,
        default_system=default_system,
        author_ask_model=author_ask_model,
        author_system_prompt_registry=author_system_prompt_registry,
        base_url=base_url,
        api_key=api_key,
        stream_display=stream_display,
    )


def execute_ordinary_direct_semantic_corridor(
    *,
    run_kernel: Any,
    component_evidence_sets: Mapping[str, Mapping[str, Any]],
    query: str,
    requested_synthesis_directive: str,
    requested_mode: str,
    strict_one_shot_transport: Callable[..., Any],
    clean_json_response: Callable[[str], str] | None,
    provider: str,
    model: str,
    use_reasoning: bool,
    effort: str = "medium",
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any] | None]:
    """Preserve the Phase-1 tuple API while retaining no additional authority."""

    result = execute_ordinary_direct_semantic_corridor_with_context(
        run_kernel=run_kernel,
        component_evidence_sets=component_evidence_sets,
        query=query,
        requested_synthesis_directive=requested_synthesis_directive,
        requested_mode=requested_mode,
        strict_one_shot_transport=strict_one_shot_transport,
        clean_json_response=clean_json_response,
        provider=provider,
        model=model,
        use_reasoning=use_reasoning,
        effort=effort,
    )
    return (
        tuple(deepcopy(dict(item)) for item in result.component_admission_refs),
        deepcopy(dict(result.cross_artifact)) if result.cross_artifact else None,
    )


__all__ = [
    "DIRECT_CROSS_LOGICAL_EVALUATION_KEY",
    "OrdinaryDirectSemanticCorridorResult",
    "OrdinaryDirectSemanticCorridorError",
    "OrdinaryDirectTerminalCorridorResult",
    "execute_ordinary_direct_semantic_corridor",
    "execute_ordinary_direct_semantic_corridor_with_context",
    "execute_ordinary_direct_terminal_corridor",
    "execute_ordinary_direct_terminal_corridor_from_result",
]
