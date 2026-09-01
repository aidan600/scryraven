"""Experimental thin direct Component Analyst-to-Cross composition.

This branch-only corridor composes existing semantic-role and RunKernel
authorities.  It deliberately creates no scheduler, lease, batch, Graph V1,
synthesis relation, D-prime, Scrutineer, Sufficiency, FAP, or Author state.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from typing import Any

from core.component_analyst_evidence_set import (
    ComponentAnalystEvidenceSetError,
    component_analyst_evidence_member_code_evidence,
    validate_component_analyst_evidence_sets,
)
from core.component_work_graph_v1 import MAX_SYNTHESIS_DEPTH
from core.multicomponent_component_admission import (
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


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any, *, limit: int = 400) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    return text[:limit] if text else None


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
    for component in component_refs:
        component_id = str(component["component_id"])
        admission = by_id[component_id]
        if (
            admission.get("owner")
            != "RunKernel.MulticomponentComponentAdmission"
            or admission.get("canonical_state") is not True
            or admission.get("run_id") != run_kernel.state.run_id
            or admission.get("request_id") != run_kernel.state.request_id
            or admission.get("accepted_contract_version")
            != contract.get("accepted_contract_version")
            or admission.get("accepted_contract_digest")
            != contract.get("accepted_contract_digest")
            or admission.get("component_revision")
            != component.get("component_revision")
            or admission.get("component_digest") != component.get("component_digest")
            or admission.get("admission_status")
            not in {"admitted", "admitted_with_caveats"}
            or admission.get("current") is not True
            or admission.get("stale") is True
            or not _safe_mapping(admission.get("component_analyst_case_ref"))
            or not _safe_mapping(admission.get("admitted_claim_ref"))
            or not _safe_mapping(admission.get("semantic_observation_ref"))
            or not _safe_mapping(admission.get("component_coverage_ref"))
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


def build_direct_cross_input_packet(
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
    visited: set[str] = set()

    def visit(key: str, depth: int) -> None:
        if key in visiting:
            raise OrdinaryDirectSemanticCorridorError(
                "direct Cross proposal dependencies contain a cycle"
            )
        if depth > MAX_SYNTHESIS_DEPTH:
            raise OrdinaryDirectSemanticCorridorError(
                "direct Cross proposal dependency depth exceeds the installed bound"
            )
        if key in visited:
            return
        visiting.add(key)
        for parent in dependencies.get(key, ()):
            visit(parent, depth + 1)
        visiting.remove(key)
        visited.add(key)

    for proposal_key in proposal_keys:
        visit(proposal_key, 0)


def validate_direct_cross_result_binding(
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
    """Execute the Phase-1 direct corridor without installing another owner."""

    _require_direct_boundary(run_kernel)
    contract, component_refs = _active_contract(run_kernel)
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
    if len(component_refs) == 1:
        return tuple(current_admissions), None

    cross_input = build_direct_cross_input_packet(
        run_kernel=run_kernel,
        component_analyst_input_packets=packets,
        component_analyst_evidence_sets=evidence_sets,
        requested_synthesis_directive=requested_synthesis_directive,
        requested_mode=requested_mode,
    )
    cross_artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=cross_input,
        logical_evaluation_key=DIRECT_CROSS_LOGICAL_EVALUATION_KEY,
        **role_kwargs,
    )
    bound_cross = validate_direct_cross_result_binding(
        run_kernel=run_kernel,
        cross_input_packet=cross_input,
        cross_artifact=cross_artifact,
    )
    return tuple(current_admissions), bound_cross


__all__ = [
    "DIRECT_CROSS_LOGICAL_EVALUATION_KEY",
    "OrdinaryDirectSemanticCorridorError",
    "build_direct_cross_input_packet",
    "execute_ordinary_direct_semantic_corridor",
    "validate_direct_cross_result_binding",
]
