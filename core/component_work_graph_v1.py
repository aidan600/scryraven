"""Ordinary canonical ComponentWorkGraph V1 with first-class synthesis nodes."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_work_node import (
    validate_component_work_node_v1,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    SUPPORTED_QUERY_CLASS,
    role_artifact_ref,
    validate_multicomponent_role_artifact,
)

COMPONENT_WORK_GRAPH_V1_SCHEMA_VERSION = "component_work_graph_v1"
COMPONENT_WORK_GRAPH_V1_STAGE = "multicomponent_component_work_graph_v1"
COMPONENT_WORK_GRAPH_V1_OWNER = "RunKernel.ComponentWorkGraphV1"

MAX_COMPONENT_NODES = 5
MIN_COMPONENT_NODES = 2
MAX_SYNTHESIS_NODES = 4
MAX_SYNTHESIS_DEPTH = 2

GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED = "synthesis_validation_required"
GRAPH_STATUS_READY = "ready"
GRAPH_STATUS_READY_WITH_CAVEATS = "ready_with_caveats"
GRAPH_STATUS_PARTIAL = "partial_independent_direct_output"
GRAPH_STATUS_MISSING_DEPENDENCY = "missing_component_or_dependency"
GRAPH_STATUS_MISSING_SCRUTINY = "missing_required_scrutiny"
GRAPH_STATUS_CHALLENGED = "challenged_synthesis"
GRAPH_STATUS_BLOCKED = "blocked_synthesis"
GRAPH_STATUS_CHALLENGED_COMPONENT = "challenged_component"
GRAPH_STATUS_CHALLENGED_EDGE = "challenged_edge"
GRAPH_STATUS_CHALLENGED_SUBGRAPH = "challenged_subgraph"
GRAPH_STATUS_CHALLENGED_GRAPH = "challenged_graph"
GRAPH_STATUS_BLOCKED_GRAPH = "blocked_graph"
GRAPH_STATUS_STALE = "stale_synthesis"
GRAPH_STATUS_RECOVERY_UNAVAILABLE = "recovery_proposed_unavailable"
GRAPH_STATUS_UNSUPPORTED = "unsupported_graph_posture"

_READY_STATUSES = frozenset({GRAPH_STATUS_READY, GRAPH_STATUS_READY_WITH_CAVEATS})
_SUPPORT_VALIDATIONS = frozenset({"supported", "supported_with_caveats"})
_LOGICAL_ACCOUNTING_KEYS = (
    "component_analyst_evaluations",
    "component_dprime_evaluations",
    "cross_component_analyst_evaluations",
    "synthesis_dprime_evaluations",
    "scrutineer_evaluations",
)
_PHYSICAL_ACCOUNTING_KEYS = (
    "component_analyst_calls",
    "component_dprime_calls",
    "cross_component_analyst_calls",
    "synthesis_dprime_calls",
    "scrutineer_calls",
)
_ROLE_LOGICAL_ACCOUNTING_KEY = {
    ROLE_COMPONENT_ANALYST: "component_analyst_evaluations",
    ROLE_COMPONENT_DPRIME: "component_dprime_evaluations",
    ROLE_CROSS_COMPONENT_ANALYST: "cross_component_analyst_evaluations",
    ROLE_SYNTHESIS_DPRIME: "synthesis_dprime_evaluations",
    ROLE_SCRUTINEER: "scrutineer_evaluations",
}
_ROLE_PHYSICAL_ACCOUNTING_KEY = {
    ROLE_COMPONENT_ANALYST: "component_analyst_calls",
    ROLE_COMPONENT_DPRIME: "component_dprime_calls",
    ROLE_CROSS_COMPONENT_ANALYST: "cross_component_analyst_calls",
    ROLE_SYNTHESIS_DPRIME: "synthesis_dprime_calls",
    ROLE_SCRUTINEER: "scrutineer_calls",
}


class ComponentWorkGraphV1Error(ValueError):
    """Raised when V1 graph state or authority binding is invalid."""


def _clean_text(value: Any, *, limit: int = 1000) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return list(value)
    return []


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 10:
        return "[truncated]"
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item, depth=depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:100]]
    return str(value)


def _digest(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _without_graph_digest(graph: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(graph)
    payload.pop("graph_digest", None)
    return payload


def _node_ref(node: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "node_kind": node.get("node_kind"),
        "node_id": node.get("node_id"),
        "node_revision": node.get("node_revision"),
        "node_digest": node.get("node_digest"),
        "component_id": node.get("component_id"),
        "synthesis_key": node.get("synthesis_key"),
        "status": node.get("status") or node.get("admission_status"),
        "current": node.get("current") is True,
        "stale": node.get("stale") is True,
    }


def _input_ref_from_node(node: Mapping[str, Any]) -> dict[str, Any]:
    ref = _node_ref(node)
    if ref.get("node_kind") == "component":
        ref["admission_status"] = node.get("admission_status")
    else:
        ref["admission_status"] = node.get("status")
        ref["synthesis_claim_ref"] = _safe_mapping(node.get("synthesis_claim_ref"))
    return ref


def _bounded_blocker_projection(blockers: Sequence[Any]) -> list[Any]:
    projected: list[Any] = []
    for item in blockers or ():
        if isinstance(item, Mapping):
            projected.append(
                {
                    key: item.get(key)
                    for key in (
                        "blocker_id",
                        "blocker_kind",
                        "reason",
                        "blocker_reason",
                        "status",
                    )
                    if item.get(key) is not None
                }
            )
        elif isinstance(item, str):
            cleaned = _clean_text(item, limit=240)
            if cleaned:
                projected.append(cleaned)
    return projected


def _bounded_semantic_role_input_from_node(node: Mapping[str, Any]) -> dict[str, Any]:
    """Authority-bound identity plus bounded admitted semantic meaning for roles."""

    projection = _input_ref_from_node(node)
    projection["required_caveats"] = list(node.get("required_caveats") or ())
    projection["preserved_nonclaims"] = list(node.get("preserved_nonclaims") or ())
    projection["blocker_refs"] = _bounded_blocker_projection(
        list(node.get("blocker_refs") or ())
    )
    if node.get("node_kind") == "component":
        claim = _safe_mapping(node.get("admitted_claim_ref"))
        projection["claim_text"] = claim.get("claim_text")
        projection["claim_id"] = claim.get("claim_id")
        projection["claim_digest"] = claim.get("claim_digest")
        projection["admitted_claim_ref"] = {
            key: claim.get(key)
            for key in ("claim_id", "claim_text", "claim_digest")
            if claim.get(key) is not None
        }
    else:
        claim = _safe_mapping(node.get("synthesis_claim_ref"))
        projection["claim_text"] = node.get("claim_text")
        projection["claim_id"] = claim.get("claim_id")
        projection["claim_digest"] = claim.get("claim_digest")
        projection["synthesis_claim_ref"] = {
            key: claim.get(key)
            for key in ("claim_id", "claim_digest", "claim_text")
            if claim.get(key) is not None
        }
        if "claim_text" not in projection["synthesis_claim_ref"] and node.get(
            "claim_text"
        ):
            projection["synthesis_claim_ref"]["claim_text"] = node.get("claim_text")
    return projection


def cross_component_input_packet(
    *,
    component_nodes: Sequence[Mapping[str, Any]],
    accepted_contract_ref: Mapping[str, Any],
    requested_synthesis_directive: str,
) -> dict[str, Any]:
    return {
        "supported_query_class": SUPPORTED_QUERY_CLASS,
        "accepted_contract_ref": _safe_mapping(accepted_contract_ref),
        "requested_synthesis_directive": _clean_text(
            requested_synthesis_directive, limit=360
        ),
        "dependency_posture": "unknown_until_cross_component_analysis",
        "component_nodes": [
            {
                **_input_ref_from_node(node),
                "component_label": node.get("component_label"),
                "component_question": node.get("component_question"),
                "direct_claim_ref": _safe_mapping(
                    node.get("admitted_claim_ref")
                ),
                "required_caveats": list(node.get("required_caveats") or ()),
                "preserved_nonclaims": list(
                    node.get("preserved_nonclaims") or ()
                ),
                "blocker_refs": list(node.get("blocker_refs") or ()),
            }
            for node in component_nodes
        ],
    }


def synthesis_dprime_input_packet(
    graph: Mapping[str, Any],
    *,
    synthesis_key: str,
) -> dict[str, Any]:
    validated = validate_component_work_graph_v1(graph)
    node = _synthesis_node(validated, synthesis_key)
    input_nodes = _input_nodes(validated, node)
    for upstream in input_nodes:
        if upstream.get("node_kind") == "component":
            if upstream.get("admission_status") not in {
                "admitted",
                "admitted_with_caveats",
            }:
                raise ComponentWorkGraphV1Error(
                    "synthesis D-prime requires admitted component inputs"
                )
        elif upstream.get("status") != "admitted":
            raise ComponentWorkGraphV1Error(
                "synthesis D-prime requires upstream synthesis admission"
            )
        if upstream.get("current") is not True or upstream.get("stale") is True:
            raise ComponentWorkGraphV1Error(
                "synthesis D-prime input is stale or not current"
            )
    return {
        "supported_query_class": SUPPORTED_QUERY_CLASS,
        "graph_ref": {
            "graph_id": validated["graph_id"],
            "graph_revision": validated["graph_revision"],
            "graph_digest": validated["graph_digest"],
            "run_id": validated["run_id"],
            "request_id": validated["request_id"],
        },
        "nominated_synthesis": {
            "synthesis_key": node["synthesis_key"],
            "claim_text": node["claim_text"],
            "relationship_type": node["relationship_type"],
            "proposal_ref": dict(node["proposal_ref"]),
            "required_caveats": list(node.get("required_caveats") or ()),
            "preserved_nonclaims": list(
                node.get("preserved_nonclaims") or ()
            ),
        },
        "current_admitted_inputs": [
            _bounded_semantic_role_input_from_node(item) for item in input_nodes
        ],
    }


def scrutineer_input_packet(graph: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_component_work_graph_v1(graph)
    return {
        "supported_query_class": SUPPORTED_QUERY_CLASS,
        "graph_ref": {
            "graph_id": validated["graph_id"],
            "graph_revision": validated["graph_revision"],
            "graph_digest": validated["graph_digest"],
            "run_id": validated["run_id"],
            "request_id": validated["request_id"],
        },
        "trigger_reasons": list(validated.get("scrutineer_trigger_reasons") or ()),
        "component_refs": [
            _bounded_semantic_role_input_from_node(item)
            for item in validated["component_nodes"]
        ],
        "synthesis_refs": [
            {
                **_bounded_semantic_role_input_from_node(item),
                "input_node_refs": list(item.get("input_node_refs") or ()),
                "dprime_validation_ref": _safe_mapping(
                    item.get("dprime_validation_ref")
                ),
            }
            for item in validated["synthesis_nodes"]
        ],
        "challenge_target_catalog": _scrutineer_challenge_target_catalog(validated),
    }


def _scrutineer_challenge_target_catalog(
    graph: Mapping[str, Any],
) -> list[dict[str, Any]]:
    nodes = [*graph["component_nodes"], *graph["synthesis_nodes"]]
    node_by_id = {item["node_id"]: item for item in nodes}
    catalog: list[dict[str, Any]] = []
    for index, node in enumerate(graph["component_nodes"], start=1):
        catalog.append(
            {
                "target_kind": "component",
                "target_key": f"component_{index:02d}",
                "label": f"Component: {node.get('component_label') or node.get('component_id')}",
                "canonical_target_ref": _node_ref(node),
                "semantic_material": {
                    "component_label": node.get("component_label"),
                    "component_question": node.get("component_question"),
                    "admitted_claim_ref": _safe_mapping(node.get("admitted_claim_ref")),
                    "required_caveats": list(node.get("required_caveats") or ()),
                    "preserved_nonclaims": list(node.get("preserved_nonclaims") or ()),
                    "admission_status": node.get("admission_status"),
                    "direct_output_eligible": node.get("direct_output_eligible") is True,
                },
            }
        )
    for index, node in enumerate(graph["synthesis_nodes"], start=1):
        catalog.append(
            {
                "target_kind": "synthesis",
                "target_key": f"synthesis_{index:02d}",
                "label": f"Synthesis: {node.get('synthesis_key')}",
                "canonical_target_ref": _node_ref(node),
                "semantic_material": {
                    "synthesis_key": node.get("synthesis_key"),
                    "claim_text": node.get("claim_text"),
                    "relationship_type": node.get("relationship_type"),
                    "required_caveats": list(node.get("required_caveats") or ()),
                    "preserved_nonclaims": list(node.get("preserved_nonclaims") or ()),
                    "blocker_refs": _bounded_blocker_projection(
                        list(node.get("blocker_refs") or ())
                    ),
                    "validation_admission_current_posture": {
                        "status": node.get("status"),
                        "current": node.get("current") is True,
                        "stale": node.get("stale") is True,
                        "dprime_validated": bool(node.get("dprime_validation_ref")),
                        "runkernel_admitted": bool(node.get("runkernel_admission_ref")),
                    },
                },
            }
        )
    for index, edge in enumerate(graph["edges"], start=1):
        upstream = node_by_id[edge["from_node_id"]]
        downstream = node_by_id[edge["to_node_id"]]
        catalog.append(
            {
                "target_kind": "edge",
                "target_key": f"edge_{index:02d}",
                "label": (
                    f"Semantic dependency: {upstream.get('component_label') or upstream.get('synthesis_key')} "
                    f"-> {downstream.get('synthesis_key')}"
                ),
                "canonical_target_ref": {
                    "edge_id": edge.get("edge_id"),
                    "edge_digest": edge.get("edge_digest"),
                    "from_node_ref": _node_ref(upstream),
                    "to_node_ref": _node_ref(downstream),
                },
                "semantic_material": {
                    "edge_kind": edge.get("edge_kind"),
                    "dependency_posture": edge.get("dependency_posture"),
                    "upstream_meaning": _bounded_semantic_role_input_from_node(upstream),
                    "downstream_meaning": _bounded_semantic_role_input_from_node(downstream),
                },
            }
        )
    downstream_by_id: dict[str, list[str]] = {}
    for edge in graph["edges"]:
        downstream_by_id.setdefault(edge["from_node_id"], []).append(edge["to_node_id"])
    for index, root in enumerate(graph["synthesis_nodes"], start=1):
        member_ids = {root["node_id"]}
        pending = [root["node_id"]]
        while pending:
            upstream_id = pending.pop(0)
            for downstream_id in downstream_by_id.get(upstream_id, ()):
                if downstream_id not in member_ids:
                    member_ids.add(downstream_id)
                    pending.append(downstream_id)
        member_nodes = [node_by_id[item] for item in member_ids]
        member_nodes.sort(key=lambda item: (item.get("synthesis_depth", 0), item["node_id"]))
        member_edges = [
            edge
            for edge in graph["edges"]
            if edge["from_node_id"] in member_ids and edge["to_node_id"] in member_ids
        ]
        member_edge_refs = [
            {"edge_id": edge["edge_id"], "edge_digest": edge["edge_digest"]}
            for edge in member_edges
        ]
        binding = {
            "root_synthesis_ref": _node_ref(root),
            "member_node_refs": [_node_ref(item) for item in member_nodes],
            "member_edge_refs": member_edge_refs,
        }
        catalog.append(
            {
                "target_kind": "subgraph",
                "target_key": f"subgraph_{index:02d}",
                "label": f"Synthesis branch rooted at {root.get('synthesis_key')}",
                "canonical_target_ref": {
                    **binding,
                    "subgraph_digest": _digest(binding),
                },
                "semantic_material": {
                    "branch_meaning": root.get("claim_text"),
                    "member_synthesis_keys": [
                        item.get("synthesis_key") for item in member_nodes
                    ],
                },
            }
        )
    catalog.append(
        {
            "target_kind": "graph",
            "target_key": "whole_graph",
            "label": "Whole current ComponentWorkGraph V1 case",
            "canonical_target_ref": {
                "graph_id": graph["graph_id"],
                "graph_revision": graph["graph_revision"],
                "graph_digest": graph["graph_digest"],
                "run_id": graph["run_id"],
                "request_id": graph["request_id"],
            },
            "semantic_material": {
                "graph_status": graph.get("graph_status"),
                "dependency_posture": graph.get("dependency_posture"),
                "scrutineer_status": graph.get("scrutineer_status"),
            },
        }
    )
    return catalog


def component_work_graph_v1_from_cross_component_artifact(
    *,
    run_id: str,
    request_id: str,
    accepted_contract_ref: Mapping[str, Any],
    requested_synthesis_directive: str,
    component_nodes: Sequence[Mapping[str, Any]],
    cross_component_artifact: Mapping[str, Any],
    additional_scrutineer_trigger_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    components = [validate_component_work_node_v1(item) for item in component_nodes]
    if not MIN_COMPONENT_NODES <= len(components) <= MAX_COMPONENT_NODES:
        raise ComponentWorkGraphV1Error("Graph V1 component width outside Phase 1 bounds")
    if any(item.get("run_id") != run_id or item.get("request_id") != request_id for item in components):
        raise ComponentWorkGraphV1Error("Graph V1 component node cross-run binding")
    if len({item["component_id"] for item in components}) != len(components):
        raise ComponentWorkGraphV1Error("Graph V1 duplicate component node")

    cross = validate_multicomponent_role_artifact(
        cross_component_artifact,
        expected_role=ROLE_CROSS_COMPONENT_ANALYST,
    )
    if cross.get("run_id") != run_id or cross.get("request_id") != request_id:
        raise ComponentWorkGraphV1Error("Cross-Component Analyst cross-run artifact")
    expected_cross_input = cross_component_input_packet(
        component_nodes=components,
        accepted_contract_ref=accepted_contract_ref,
        requested_synthesis_directive=requested_synthesis_directive,
    )
    if cross["input_packet_digest"] != _digest(expected_cross_input):
        raise ComponentWorkGraphV1Error(
            "Cross-Component Analyst input binding mismatch"
        )

    proposals = list(cross["semantic_output"]["synthesis_proposals"])
    if len(proposals) > MAX_SYNTHESIS_NODES:
        raise ComponentWorkGraphV1Error("Graph V1 synthesis width exceeded")
    component_by_id = {item["component_id"]: item for item in components}
    proposal_by_key = {item["synthesis_key"]: item for item in proposals}
    for proposal in proposals:
        for component_id in proposal["component_inputs"]:
            if component_id not in component_by_id:
                raise ComponentWorkGraphV1Error(
                    f"unknown synthesis component dependency: {component_id}"
                )
            if component_by_id[component_id].get("direct_output_eligible") is not True:
                raise ComponentWorkGraphV1Error(
                    "synthesis proposal depends on an unadmitted component: "
                    f"{component_id}"
                )
        for synthesis_key in proposal["synthesis_inputs"]:
            if synthesis_key not in proposal_by_key:
                raise ComponentWorkGraphV1Error(
                    f"unknown synthesis dependency: {synthesis_key}"
                )
            if synthesis_key == proposal["synthesis_key"]:
                raise ComponentWorkGraphV1Error("synthesis node cannot depend on itself")
    order, depths = _topological_synthesis_order(proposals)
    if max(depths.values(), default=0) > MAX_SYNTHESIS_DEPTH:
        raise ComponentWorkGraphV1Error("Graph V1 maximum synthesis depth exceeded")

    graph_seed = _digest(
        {
            "run_id": run_id,
            "request_id": request_id,
            "components": [item["node_digest"] for item in components],
            "cross": cross["artifact_digest"],
        }
    )
    synthesis_nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for key in order:
        proposal = proposal_by_key[key]
        input_refs: list[dict[str, Any]] = []
        for component_id in proposal["component_inputs"]:
            input_refs.append(_node_ref(component_by_id[component_id]))
        for upstream_key in proposal["synthesis_inputs"]:
            upstream = next(
                item for item in synthesis_nodes if item["synthesis_key"] == upstream_key
            )
            input_refs.append(_node_ref(upstream))
        proposal_core = {
            "synthesis_key": key,
            "claim_text": proposal["claim_text"],
            "relationship_type": proposal["relationship_type"],
            "input_node_refs": input_refs,
            "required_caveats": list(proposal.get("caveats") or ()),
            "preserved_nonclaims": list(proposal.get("nonclaims") or ()),
            "blockers": list(proposal.get("blockers") or ()),
            "cross_component_analyst_ref": role_artifact_ref(cross),
        }
        proposal_digest = _digest(proposal_core)
        node = {
            "schema_version": "synthesis_work_node_v1",
            "node_kind": "synthesis",
            "node_id": f"synthesis-work-node:v1:{graph_seed[:12]}:{key}",
            "node_revision": "1",
            "node_digest": None,
            "run_id": run_id,
            "request_id": request_id,
            "synthesis_key": key,
            "synthesis_depth": depths[key],
            "claim_text": proposal["claim_text"],
            "relationship_type": proposal["relationship_type"],
            "input_node_refs": input_refs,
            "proposal_ref": {
                "proposal_id": f"synthesis-proposal:{graph_seed[:12]}:{key}",
                "proposal_digest": proposal_digest,
                "cross_component_analyst_ref": role_artifact_ref(cross),
            },
            "synthesis_claim_ref": {
                "claim_id": f"synthesis-claim:{graph_seed[:12]}:{key}",
                "claim_digest": _digest(proposal["claim_text"]),
            },
            "required_caveats": list(proposal.get("caveats") or ()),
            "preserved_nonclaims": list(proposal.get("nonclaims") or ()),
            "blocker_refs": [
                {"reason": item} for item in proposal.get("blockers") or ()
            ],
            "status": "proposed",
            "current": True,
            "stale": False,
            "dprime_validation_ref": {},
            "scrutineer_ref": {},
            "runkernel_admission_ref": {},
        }
        node["node_digest"] = _digest(
            {item_key: item_value for item_key, item_value in node.items() if item_key != "node_digest"}
        )
        synthesis_nodes.append(node)
        for input_ref in input_refs:
            edge_core = {
                "from_node_id": input_ref["node_id"],
                "from_node_revision": input_ref["node_revision"],
                "from_node_digest": input_ref["node_digest"],
                "to_node_id": node["node_id"],
                "edge_kind": "semantic_dependency",
                "dependency_posture": "proposed",
            }
            edges.append(
                {
                    **edge_core,
                    "edge_id": f"edge:v1:{_digest(edge_core)[:20]}",
                    "edge_digest": _digest(edge_core),
                }
            )

    synthesis_depends_on_synthesis = any(
        ref.get("node_kind") == "synthesis"
        for node in synthesis_nodes
        for ref in node["input_node_refs"]
    )
    trigger_reasons = list(
        dict.fromkeys(
            [
                *(
                    ["synthesis_depends_on_synthesis"]
                    if synthesis_depends_on_synthesis
                    else []
                ),
                *(
                    ["material_synthesis_caveat"]
                    if any(item.get("caveats") for item in proposals)
                    else []
                ),
                *(
                    ["unresolved_synthesis_dependency_or_blocker"]
                    if any(item.get("blockers") for item in proposals)
                    else []
                ),
                *(
                    ["cross_component_contradiction"]
                    if any(
                        item.get("relationship_type")
                        in {"contradiction", "contradicts", "conflict"}
                        for item in proposals
                    )
                    else []
                ),
                *[
                    reason
                    for reason in (
                        _clean_text(item, limit=120)
                        for item in additional_scrutineer_trigger_reasons
                    )
                    if reason
                ],
            ]
        )
    )
    graph = {
        "schema_version": COMPONENT_WORK_GRAPH_V1_SCHEMA_VERSION,
        "supported_query_class": SUPPORTED_QUERY_CLASS,
        "owner": "pending_runkernel_admission",
        "canonical_state": False,
        "graph_id": f"component-work-graph:v1:{graph_seed[:20]}",
        "graph_revision": 1,
        "graph_digest": None,
        "previous_graph_digest": None,
        "run_id": run_id,
        "request_id": request_id,
        "accepted_contract_ref": _safe_mapping(accepted_contract_ref),
        "requested_synthesis_directive": _clean_text(
            requested_synthesis_directive, limit=360
        ),
        "dependency_posture": "explicitly_assessed",
        "component_nodes": components,
        "synthesis_nodes": synthesis_nodes,
        "edges": edges,
        "direct_output_component_ids": [
            item["component_id"]
            for item in components
            if item.get("direct_output_eligible") is True
        ],
        "synthesis_topological_order": order,
        "maximum_synthesis_depth": max(depths.values(), default=0),
        "scrutineer_required": bool(trigger_reasons),
        "scrutineer_trigger_reasons": trigger_reasons,
        "scrutineer_status": "required" if trigger_reasons else "not_required",
        "scrutineer_ref": {},
        "challenge_refs": [],
        "graph_challenge_posture": "none",
        "graph_output_suppressed": False,
        "graph_status": GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED,
        "logical_accounting": {},
        "physical_call_accounting": {},
        "automatic_recovery_rounds": 0,
        "graph_amendment_rounds": 0,
        "runtime_parallelism": False,
        "scheduler_created": False,
        "budget_lease_created": False,
    }
    graph["graph_digest"] = _digest(_without_graph_digest(graph))
    return validate_component_work_graph_v1(graph)


def graph_with_recovered_component(
    graph: Mapping[str, Any],
    *,
    recovered_component_node: Mapping[str, Any],
    current_contract_ref: Mapping[str, Any],
    recovery_authorization_ref: Mapping[str, Any],
    amendment_application_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Advance one graph identity and invalidate all pre-recovery synthesis."""

    current = validate_component_work_graph_v1(graph)
    node = validate_component_work_node_v1(recovered_component_node)
    if node.get("run_id") != current.get("run_id") or node.get(
        "request_id"
    ) != current.get("request_id"):
        raise ComponentWorkGraphV1Error("recovered component node is cross-run")
    if any(
        item.get("component_id") == node.get("component_id")
        for item in current["component_nodes"]
    ):
        raise ComponentWorkGraphV1Error("recovered component node is duplicate")
    if len(current["component_nodes"]) >= MAX_COMPONENT_NODES:
        raise ComponentWorkGraphV1Error("recovered component exceeds graph cap")
    contract_ref = _safe_mapping(current_contract_ref)
    prior_contract_ref = _safe_mapping(current.get("accepted_contract_ref"))
    if (
        not contract_ref.get("accepted_contract_version")
        or not contract_ref.get("accepted_contract_digest")
        or contract_ref.get("accepted_contract_digest")
        == prior_contract_ref.get("accepted_contract_digest")
    ):
        raise ComponentWorkGraphV1Error(
            "graph amendment requires a new current AnswerContract binding"
        )
    recovery_ref = _safe_mapping(recovery_authorization_ref)
    amendment_ref = _safe_mapping(amendment_application_ref)
    if (
        recovery_ref.get("canonical_state") is not True
        or recovery_ref.get("recovery_round") != 1
        or recovery_ref.get("graph_digest") != current.get("graph_digest")
        or not amendment_ref.get("application_digest")
    ):
        raise ComponentWorkGraphV1Error(
            "graph amendment requires exact recovery and amendment authority"
        )

    stale_nodes: list[dict[str, Any]] = []
    for prior in current["synthesis_nodes"]:
        stale = deepcopy(prior)
        stale["status"] = "stale"
        stale["current"] = False
        stale["stale"] = True
        stale["stale_reason"] = "AnswerContract and component graph amended"
        _clear_synthesis_validation_and_admission(stale)
        _refresh_node_digest(stale)
        stale_nodes.append(stale)
    stale_edges = []
    for prior in current["edges"]:
        stale = deepcopy(prior)
        stale["current"] = False
        stale["stale"] = True
        stale["stale_reason"] = "pre-recovery synthesis authority invalidated"
        stale_edges.append(stale)
    stale_challenges = []
    for prior in current.get("challenge_refs") or ():
        stale = deepcopy(prior)
        stale["current"] = False
        stale["stale"] = True
        stale_challenges.append(stale)

    current["component_nodes"].append(node)
    current["accepted_contract_ref"] = contract_ref
    current["stale_synthesis_history"] = [
        *list(current.get("stale_synthesis_history") or ()),
        *stale_nodes,
    ]
    current["stale_edge_history"] = [
        *list(current.get("stale_edge_history") or ()),
        *stale_edges,
    ]
    current["stale_challenge_history"] = [
        *list(current.get("stale_challenge_history") or ()),
        *stale_challenges,
    ]
    prior_scrutineer_ref = _safe_mapping(current.get("scrutineer_ref"))
    if prior_scrutineer_ref:
        current["stale_scrutineer_history"] = [
            *list(current.get("stale_scrutineer_history") or ()),
            {
                **prior_scrutineer_ref,
                "current": False,
                "stale": True,
            },
        ]
    current["synthesis_nodes"] = []
    current["edges"] = []
    current["synthesis_topological_order"] = []
    current["maximum_synthesis_depth"] = 0
    current["dependency_posture"] = "requires_fresh_resynthesis"
    current["scrutineer_required"] = True
    current["scrutineer_status"] = "required_after_recovery"
    current["scrutineer_ref"] = {}
    current["challenge_refs"] = []
    current["graph_challenge_posture"] = "none"
    current["graph_output_suppressed"] = True
    current["graph_status"] = GRAPH_STATUS_STALE
    current["direct_output_component_ids"] = [
        item["component_id"]
        for item in current["component_nodes"]
        if item.get("direct_output_eligible") is True
    ]
    current["automatic_recovery_rounds"] = 1
    current["graph_amendment_rounds"] = 1
    current["component_research_reentry_rounds"] = 1
    current["whole_graph_resynthesis_rounds"] = 0
    current["recovery_authorization_ref"] = recovery_ref
    current["contract_amendment_application_ref"] = amendment_ref
    current["pre_recovery_synthesis_authority_invalidated"] = True
    return _next_revision(current)


def component_work_graph_v1_resynthesis_from_cross_component_artifact(
    graph: Mapping[str, Any],
    *,
    accepted_contract_ref: Mapping[str, Any],
    cross_component_artifact: Mapping[str, Any],
    additional_scrutineer_trigger_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    """Install one complete fresh synthesis structure on an amended graph."""

    current = validate_component_work_graph_v1(graph)
    if (
        current.get("dependency_posture") != "requires_fresh_resynthesis"
        or current.get("synthesis_nodes")
        or int(current.get("whole_graph_resynthesis_rounds") or 0) != 0
        or int(current.get("automatic_recovery_rounds") or 0) != 1
    ):
        raise ComponentWorkGraphV1Error(
            "fresh whole-graph resynthesis requires one amended stale graph"
        )
    contract_ref = _safe_mapping(accepted_contract_ref)
    if contract_ref != _safe_mapping(current.get("accepted_contract_ref")):
        raise ComponentWorkGraphV1Error(
            "fresh resynthesis AnswerContract binding mismatch"
        )
    fresh = component_work_graph_v1_from_cross_component_artifact(
        run_id=str(current["run_id"]),
        request_id=str(current["request_id"]),
        accepted_contract_ref=contract_ref,
        requested_synthesis_directive=str(
            current["requested_synthesis_directive"]
        ),
        component_nodes=current["component_nodes"],
        cross_component_artifact=cross_component_artifact,
        additional_scrutineer_trigger_reasons=(
            *(
                ("deep_mode",)
                if "deep_mode"
                in set(current.get("scrutineer_trigger_reasons") or ())
                else ()
            ),
            *additional_scrutineer_trigger_reasons,
            "post_recovery_fresh_resynthesis",
        ),
    )
    fresh.update(
        {
            "owner": current.get("owner"),
            "canonical_state": current.get("canonical_state"),
            "graph_id": current["graph_id"],
            "graph_revision": int(current["graph_revision"]) + 1,
            "previous_graph_digest": current["graph_digest"],
            "stale_synthesis_history": list(
                current.get("stale_synthesis_history") or ()
            ),
            "stale_edge_history": list(current.get("stale_edge_history") or ()),
            "stale_challenge_history": list(
                current.get("stale_challenge_history") or ()
            ),
            "stale_scrutineer_history": list(
                current.get("stale_scrutineer_history") or ()
            ),
            "automatic_recovery_rounds": 1,
            "graph_amendment_rounds": 1,
            "component_research_reentry_rounds": 1,
            "whole_graph_resynthesis_rounds": 1,
            "recovery_authorization_ref": _safe_mapping(
                current.get("recovery_authorization_ref")
            ),
            "contract_amendment_application_ref": _safe_mapping(
                current.get("contract_amendment_application_ref")
            ),
            "pre_recovery_synthesis_authority_invalidated": True,
            "graph_output_suppressed": False,
        }
    )
    fresh["graph_digest"] = _digest(_without_graph_digest(fresh))
    return validate_component_work_graph_v1(fresh)


def graph_with_synthesis_validation(
    graph: Mapping[str, Any],
    *,
    synthesis_key: str,
    dprime_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    current = validate_component_work_graph_v1(graph)
    artifact = validate_multicomponent_role_artifact(
        dprime_artifact,
        expected_role=ROLE_SYNTHESIS_DPRIME,
    )
    expected_input = synthesis_dprime_input_packet(current, synthesis_key=synthesis_key)
    if artifact["input_packet_digest"] != _digest(expected_input):
        raise ComponentWorkGraphV1Error("synthesis D-prime input binding mismatch")
    node = _synthesis_node(current, synthesis_key)
    if node["status"] != "proposed":
        raise ComponentWorkGraphV1Error("synthesis D-prime validation is out of order")
    validation_status = artifact["semantic_output"]["validation_status"]
    node["dprime_validation_ref"] = role_artifact_ref(artifact)
    node["required_caveats"] = list(
        dict.fromkeys(
            [
                *node.get("required_caveats", ()),
                *artifact["semantic_output"].get("caveats", ()),
            ]
        )
    )
    node["preserved_nonclaims"] = list(
        dict.fromkeys(
            [
                *node.get("preserved_nonclaims", ()),
                *artifact["semantic_output"].get("nonclaims", ()),
            ]
        )
    )
    node["blocker_refs"] = list(node.get("blocker_refs") or ()) + [
        {"reason": item}
        for item in artifact["semantic_output"].get("blockers", ())
    ]
    if validation_status in _SUPPORT_VALIDATIONS:
        node["status"] = "validated"
    elif validation_status == "challenged":
        node["status"] = "challenged"
    else:
        node["status"] = "blocked"
    new_scrutineer_reasons = [
        *(
            ["synthesis_dprime_challenge"]
            if validation_status == "challenged"
            else []
        ),
        *(
            ["synthesis_dprime_ambiguity"]
            if validation_status == "ambiguous"
            else []
        ),
        *(
            ["synthesis_dprime_follow_up_need"]
            if artifact["semantic_output"].get("blockers")
            else []
        ),
        *(
            ["material_synthesis_dprime_caveat"]
            if artifact["semantic_output"].get("caveats")
            else []
        ),
    ]
    if new_scrutineer_reasons:
        current["scrutineer_required"] = True
        current["scrutineer_status"] = "required"
        current["scrutineer_trigger_reasons"] = list(
            dict.fromkeys(
                [
                    *current.get("scrutineer_trigger_reasons", ()),
                    *new_scrutineer_reasons,
                ]
            )
        )
    _refresh_node_digest(node)
    node["dprime_validated_node_revision"] = node["node_revision"]
    node["dprime_validated_node_digest"] = node["node_digest"]
    return _next_revision(current)


def _resolved_scrutineer_targets(
    graph: Mapping[str, Any],
    output: Mapping[str, Any],
) -> list[dict[str, Any]]:
    catalog = _scrutineer_challenge_target_catalog(graph)
    by_pair = {
        (item["target_kind"], item["target_key"]): item for item in catalog
    }
    kind_by_key: dict[str, set[str]] = {}
    for item in catalog:
        kind_by_key.setdefault(item["target_key"], set()).add(item["target_kind"])
    selections = list(output.get("challenge_targets") or ())
    legacy_keys = list(output.get("challenged_synthesis_keys") or ())
    if legacy_keys:
        synthesis_catalog = {
            item["semantic_material"].get("synthesis_key"): item
            for item in catalog
            if item["target_kind"] == "synthesis"
        }
        for synthesis_key in legacy_keys:
            target = synthesis_catalog.get(synthesis_key)
            if target is None:
                raise ComponentWorkGraphV1Error(
                    "Scrutineer referenced unknown legacy synthesis target"
                )
            selections.append(
                {
                    "target_kind": "synthesis",
                    "target_key": target["target_key"],
                }
            )
    if (
        output.get("challenge_status") == "passed_with_caveats"
        and not selections
        and (output.get("caveats") or output.get("nonclaims"))
    ):
        # Narrow compatibility for Phase 1 fixtures that predate typed targets:
        # material whole-case caveats revise every synthesis target, as before.
        selections.extend(
            {
                "target_kind": "synthesis",
                "target_key": item["target_key"],
            }
            for item in catalog
            if item["target_kind"] == "synthesis"
        )
    resolved: list[dict[str, Any]] = []
    for selection in selections:
        pair = (selection.get("target_kind"), selection.get("target_key"))
        target = by_pair.get(pair)
        if target is None:
            if pair[1] in kind_by_key:
                raise ComponentWorkGraphV1Error(
                    "Scrutineer target key used with the wrong target kind"
                )
            raise ComponentWorkGraphV1Error("Scrutineer referenced unknown target key")
        resolved.append(deepcopy(target))
    return resolved


def _invalidate_synthesis_closure(
    graph: dict[str, Any],
    *,
    initial_node_ids: set[str],
    initial_status: str,
) -> None:
    invalidated_ids = set(initial_node_ids)
    for node in graph["synthesis_nodes"]:
        if node["node_id"] in initial_node_ids:
            node["status"] = initial_status
            _clear_synthesis_validation_and_admission(node)
            _refresh_node_digest(node)
    changed = True
    while changed:
        changed = False
        for node in graph["synthesis_nodes"]:
            if node["node_id"] in invalidated_ids:
                continue
            if any(ref["node_id"] in invalidated_ids for ref in node["input_node_refs"]):
                node["status"] = "blocked_dependency"
                _clear_synthesis_validation_and_admission(node)
                _refresh_node_digest(node)
                invalidated_ids.add(node["node_id"])
                changed = True


def graph_with_scrutineer(
    graph: Mapping[str, Any],
    *,
    scrutineer_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    current = validate_component_work_graph_v1(graph)
    artifact = validate_multicomponent_role_artifact(
        scrutineer_artifact,
        expected_role=ROLE_SCRUTINEER,
    )
    expected_input = scrutineer_input_packet(current)
    if artifact["input_packet_digest"] != _digest(expected_input):
        raise ComponentWorkGraphV1Error("Scrutineer input binding mismatch")
    output = artifact["semantic_output"]
    resolved_targets = _resolved_scrutineer_targets(current, output)
    current["scrutineer_ref"] = role_artifact_ref(artifact)
    current["scrutineer_status"] = output["challenge_status"]
    output_caveats = list(output.get("caveats") or ())
    output_nonclaims = list(output.get("nonclaims") or ())
    challenge_status = output["challenge_status"]
    for target in resolved_targets:
        kind = target["target_kind"]
        ref = target["canonical_target_ref"]
        challenge_ref = {
            "target_kind": kind,
            "target_key": target["target_key"],
            "resolved_target": ref,
            "resolution_graph_id": current["graph_id"],
            "resolution_graph_revision": current["graph_revision"],
            "resolution_graph_digest": current["graph_digest"],
            "run_id": current["run_id"],
            "request_id": current["request_id"],
            "scrutineer_ref": role_artifact_ref(artifact),
            "challenge_status": challenge_status,
            "reasons": list(output.get("reasons") or ()),
            "caveats": output_caveats,
            "nonclaims": output_nonclaims,
        }
        if kind == "synthesis":
            challenge_ref["synthesis_key"] = ref["synthesis_key"]
        current["challenge_refs"].append(challenge_ref)
        initial_status = "blocked" if challenge_status == "blocked" else "challenged"
        if challenge_status == "passed_with_caveats":
            initial_status = "proposed"
        if kind == "component":
            component_id = ref.get("component_id")
            current["direct_output_component_ids"] = [
                item
                for item in current["direct_output_component_ids"]
                if item != component_id
            ]
            component_node_id = ref["node_id"]
            dependent_ids = {
                node["node_id"]
                for node in current["synthesis_nodes"]
                if any(
                    input_ref["node_id"] == component_node_id
                    for input_ref in node["input_node_refs"]
                )
            }
            _invalidate_synthesis_closure(
                current,
                initial_node_ids=dependent_ids,
                initial_status="blocked_dependency",
            )
        elif kind == "synthesis":
            node = next(
                item
                for item in current["synthesis_nodes"]
                if item["node_id"] == ref["node_id"]
            )
            node["required_caveats"] = list(
                dict.fromkeys([*node.get("required_caveats", ()), *output_caveats])
            )
            node["preserved_nonclaims"] = list(
                dict.fromkeys([*node.get("preserved_nonclaims", ()), *output_nonclaims])
            )
            node["scrutineer_ref"] = role_artifact_ref(artifact)
            _invalidate_synthesis_closure(
                current,
                initial_node_ids={node["node_id"]},
                initial_status=initial_status,
            )
        elif kind == "edge":
            _invalidate_synthesis_closure(
                current,
                initial_node_ids={ref["to_node_ref"]["node_id"]},
                initial_status=initial_status,
            )
        elif kind == "subgraph":
            _invalidate_synthesis_closure(
                current,
                initial_node_ids={
                    item["node_id"] for item in ref["member_node_refs"]
                },
                initial_status=initial_status,
            )
        elif kind == "graph":
            current["graph_challenge_posture"] = challenge_status
            current["graph_output_suppressed"] = True
            current["direct_output_component_ids"] = []
            _invalidate_synthesis_closure(
                current,
                initial_node_ids={
                    item["node_id"] for item in current["synthesis_nodes"]
                },
                initial_status=initial_status,
            )
    return _next_revision(current)


def graph_with_synthesis_admission(
    graph: Mapping[str, Any],
    *,
    synthesis_key: str,
    action_ref: Mapping[str, Any],
) -> dict[str, Any]:
    current = validate_component_work_graph_v1(graph)
    node = _synthesis_node(current, synthesis_key)
    if node["status"] != "validated":
        raise ComponentWorkGraphV1Error(
            "RunKernel can admit only a synthesis-D-prime validated node"
        )
    if (
        node.get("dprime_validated_node_revision") != node.get("node_revision")
        or node.get("dprime_validated_node_digest") != node.get("node_digest")
        or not _safe_mapping(node.get("dprime_validation_ref"))
    ):
        raise ComponentWorkGraphV1Error(
            "admitted synthesis must keep the exact D-prime-validated node revision"
        )
    node_is_upstream = any(
        ref.get("node_id") == node.get("node_id")
        for candidate in current["synthesis_nodes"]
        if candidate.get("synthesis_key") != synthesis_key
        for ref in candidate.get("input_node_refs") or ()
    )
    if not node_is_upstream and current.get("scrutineer_required") is True:
        if current.get("scrutineer_status") not in {"passed", "passed_with_caveats"}:
            raise ComponentWorkGraphV1Error(
                "required Scrutineer posture missing before terminal synthesis admission"
            )
    validated_revision = node["dprime_validated_node_revision"]
    validated_digest = node["dprime_validated_node_digest"]
    node["status"] = "admitted"
    node["runkernel_admission_ref"] = _safe_mapping(action_ref)
    _refresh_node_digest(node)
    # Preserve the exact validated revision/digest proof on the admitted node.
    node["dprime_validated_node_revision"] = validated_revision
    node["dprime_validated_node_digest"] = validated_digest
    return _next_revision(current)


def derive_multicomponent_role_call_accounting(
    projections: Mapping[str, Any],
    *,
    issued_actions: Mapping[str, Any] | None = None,
) -> tuple[dict[str, int], dict[str, int]]:
    """Derive logical/physical role-call counts from completed role history."""

    logical = {key: 0 for key in _LOGICAL_ACCOUNTING_KEYS}
    physical = {key: 0 for key in _PHYSICAL_ACCOUNTING_KEYS}
    seen_logical_keys: dict[str, set[str]] = {
        role: set() for role in _ROLE_LOGICAL_ACCOUNTING_KEY
    }
    for stage, payload in projections.items():
        if not isinstance(stage, str) or not stage.startswith("multicomponent_role:"):
            continue
        if not isinstance(payload, Mapping):
            continue
        artifact = validate_multicomponent_role_artifact(payload)
        role = str(artifact["role"])
        logical_key = str(artifact.get("logical_evaluation_key") or "")
        if not logical_key:
            raise ComponentWorkGraphV1Error(
                "role accounting requires exact logical evaluation keys"
            )
        if logical_key in seen_logical_keys[role]:
            raise ComponentWorkGraphV1Error(
                "role accounting saw duplicate logical evaluation keys"
            )
        seen_logical_keys[role].add(logical_key)
        logical[_ROLE_LOGICAL_ACCOUNTING_KEY[role]] += int(
            artifact.get("logical_evaluations") or 0
        )
        physical[_ROLE_PHYSICAL_ACCOUNTING_KEY[role]] += int(
            artifact.get("physical_calls") or 0
        )
    if issued_actions:
        action_counts = {key: 0 for key in _PHYSICAL_ACCOUNTING_KEYS}
        role_by_action_type = {
            "multicomponent_component_analyst_execute": "component_analyst_calls",
            "multicomponent_component_dprime_execute": "component_dprime_calls",
            "multicomponent_cross_analyst_execute": "cross_component_analyst_calls",
            "multicomponent_synthesis_dprime_execute": "synthesis_dprime_calls",
            "multicomponent_scrutineer_execute": "scrutineer_calls",
        }
        for action in issued_actions.values():
            action_type = getattr(action, "action_type", None)
            action_type_value = getattr(action_type, "value", action_type)
            physical_key = role_by_action_type.get(str(action_type_value or ""))
            if physical_key is None:
                continue
            action_counts[physical_key] += 1
        if any(action_counts.values()) and action_counts != physical:
            raise ComponentWorkGraphV1Error(
                "physical role-call accounting is inconsistent with action history"
            )
    return logical, physical


def graph_with_accounting(
    graph: Mapping[str, Any],
    *,
    logical_accounting: Mapping[str, Any],
    physical_call_accounting: Mapping[str, Any],
) -> dict[str, Any]:
    current = validate_component_work_graph_v1(graph)
    logical = _safe_mapping(logical_accounting)
    physical = _safe_mapping(physical_call_accounting)
    if set(logical) != set(_LOGICAL_ACCOUNTING_KEYS) or set(physical) != set(
        _PHYSICAL_ACCOUNTING_KEYS
    ):
        raise ComponentWorkGraphV1Error(
            "Graph V1 accounting must declare the exact role-call keys"
        )
    for key in _LOGICAL_ACCOUNTING_KEYS:
        if key not in logical or int(logical[key]) < 0:
            raise ComponentWorkGraphV1Error("Graph V1 logical accounting is invalid")
    for key in _PHYSICAL_ACCOUNTING_KEYS:
        if key not in physical or int(physical[key]) < 0:
            raise ComponentWorkGraphV1Error("Graph V1 physical accounting is invalid")
    current["logical_accounting"] = {
        key: int(logical[key]) for key in _LOGICAL_ACCOUNTING_KEYS
    }
    current["physical_call_accounting"] = {
        key: int(physical[key]) for key in _PHYSICAL_ACCOUNTING_KEYS
    }
    return _next_revision(current)


def expected_graph_after_transition(
    current_graph: Mapping[str, Any] | None,
    *,
    operation: str,
    action_ref: Mapping[str, Any],
    synthesis_key: str | None = None,
    role_artifact: Mapping[str, Any] | None = None,
    logical_accounting: Mapping[str, Any] | None = None,
    physical_call_accounting: Mapping[str, Any] | None = None,
    structure_graph: Mapping[str, Any] | None = None,
    transition_graph: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Rederive the unique next canonical graph for one Graph V1 operation."""

    if operation == "structure":
        if not isinstance(structure_graph, Mapping):
            raise ComponentWorkGraphV1Error(
                "structure transition requires the exact derived structure graph"
            )
        return runkernel_canonical_graph(structure_graph, action_ref=action_ref)
    if operation in {"graph_amendment", "resynthesis_structure"}:
        if not isinstance(transition_graph, Mapping):
            raise ComponentWorkGraphV1Error(
                f"{operation} transition requires the exact derived graph"
            )
        return runkernel_canonical_graph(transition_graph, action_ref=action_ref)
    current = validate_component_work_graph_v1(current_graph or {})
    if operation == "synthesis_validation":
        if not synthesis_key or role_artifact is None:
            raise ComponentWorkGraphV1Error(
                "synthesis validation requires the exact synthesis D-prime artifact"
            )
        candidate = graph_with_synthesis_validation(
            current,
            synthesis_key=synthesis_key,
            dprime_artifact=role_artifact,
        )
    elif operation == "scrutiny":
        if role_artifact is None:
            raise ComponentWorkGraphV1Error(
                "scrutiny transition requires the exact Scrutineer artifact"
            )
        candidate = graph_with_scrutineer(
            current,
            scrutineer_artifact=role_artifact,
        )
    elif operation == "synthesis_admission":
        if not synthesis_key:
            raise ComponentWorkGraphV1Error(
                "synthesis admission requires an exact synthesis key"
            )
        candidate = graph_with_synthesis_admission(
            current,
            synthesis_key=synthesis_key,
            action_ref=action_ref,
        )
    elif operation == "accounting":
        if logical_accounting is None or physical_call_accounting is None:
            raise ComponentWorkGraphV1Error(
                "accounting transition requires derived role-call counts"
            )
        candidate = graph_with_accounting(
            current,
            logical_accounting=logical_accounting,
            physical_call_accounting=physical_call_accounting,
        )
    elif operation == "finalize":
        candidate = finalize_component_work_graph_v1(current)
    else:
        raise ComponentWorkGraphV1Error(f"unknown Graph V1 operation: {operation}")
    return runkernel_canonical_graph(candidate, action_ref=action_ref)


def finalize_component_work_graph_v1(graph: Mapping[str, Any]) -> dict[str, Any]:
    current = validate_component_work_graph_v1(graph)
    synth_statuses = {item["status"] for item in current["synthesis_nodes"]}
    challenge_kinds = {
        item.get("target_kind") for item in current.get("challenge_refs") or ()
    }
    direct_count = len(current["direct_output_component_ids"])
    component_count = len(current["component_nodes"])
    if "graph" in challenge_kinds:
        status = (
            GRAPH_STATUS_BLOCKED_GRAPH
            if current.get("graph_challenge_posture") == "blocked"
            else GRAPH_STATUS_CHALLENGED_GRAPH
        )
    elif "component" in challenge_kinds:
        status = GRAPH_STATUS_CHALLENGED_COMPONENT
    elif "edge" in challenge_kinds:
        status = GRAPH_STATUS_CHALLENGED_EDGE
    elif "subgraph" in challenge_kinds:
        status = GRAPH_STATUS_CHALLENGED_SUBGRAPH
    elif any(item.get("stale") is True for item in current["synthesis_nodes"]):
        status = GRAPH_STATUS_STALE
    elif "challenged" in synth_statuses:
        status = GRAPH_STATUS_CHALLENGED
    elif "blocked_dependency" in synth_statuses:
        status = GRAPH_STATUS_MISSING_DEPENDENCY
    elif "blocked" in synth_statuses:
        status = GRAPH_STATUS_BLOCKED
    elif current.get("scrutineer_required") is True and current.get(
        "scrutineer_status"
    ) not in {"passed", "passed_with_caveats"}:
        status = GRAPH_STATUS_MISSING_SCRUTINY
    elif direct_count < component_count:
        status = GRAPH_STATUS_PARTIAL
    elif synth_statuses and synth_statuses == {"admitted"}:
        caveated = any(
            item.get("required_caveats") for item in current["synthesis_nodes"]
        )
        status = GRAPH_STATUS_READY_WITH_CAVEATS if caveated else GRAPH_STATUS_READY
    else:
        status = GRAPH_STATUS_UNSUPPORTED
    current["graph_status"] = status
    return _next_revision(current)


def runkernel_canonical_graph(
    graph: Mapping[str, Any],
    *,
    action_ref: Mapping[str, Any],
) -> dict[str, Any]:
    current = validate_component_work_graph_v1(graph)
    current["owner"] = COMPONENT_WORK_GRAPH_V1_OWNER
    current["canonical_state"] = True
    current["runkernel_graph_action_ref"] = _safe_mapping(action_ref)
    current["graph_digest"] = _digest(_without_graph_digest(current))
    return validate_component_work_graph_v1(current)


def reduce_component_work_graph_v1(
    *,
    run_kernel: Any,
    operation: str,
    graph_candidate: Mapping[str, Any],
    synthesis_key: str | None = None,
    role_evaluation_key: str | None = None,
) -> dict[str, Any]:
    """Bind a pure Graph V1 transition to one RunKernel action/reduction."""

    from core.run_kernel import Observation, RunStageStatus

    current = _safe_mapping(
        run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
    )
    action = run_kernel.authorize_multicomponent_graph_reduction(
        operation=operation,
        prior_graph_digest=current.get("graph_digest"),
        synthesis_key=synthesis_key,
        role_evaluation_key=role_evaluation_key,
    )
    canonical = runkernel_canonical_graph(
        graph_candidate,
        action_ref={
            "action_id": action.action_id,
            "action_type": action.action_type.value,
            "stage": action.stage,
            "sequence": action.sequence,
            "operation": operation,
            "synthesis_key": synthesis_key,
            "role_evaluation_key": role_evaluation_key,
        },
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={"component_work_graph_v1": canonical},
        )
    )
    return deepcopy(canonical)


def admit_synthesis_node_via_runkernel(
    *,
    run_kernel: Any,
    synthesis_key: str,
) -> dict[str, Any]:
    """Admit one validated synthesis with the exact RunKernel action ref."""

    from core.run_kernel import Observation, RunStageStatus

    current = validate_component_work_graph_v1(
        _safe_mapping(
            run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
        )
    )
    action = run_kernel.authorize_multicomponent_graph_reduction(
        operation="synthesis_admission",
        prior_graph_digest=current["graph_digest"],
        synthesis_key=synthesis_key,
    )
    candidate = graph_with_synthesis_admission(
        current,
        synthesis_key=synthesis_key,
        action_ref={
            "action_id": action.action_id,
            "action_type": action.action_type.value,
            "stage": action.stage,
            "sequence": action.sequence,
            "operation": "synthesis_admission",
            "synthesis_key": synthesis_key,
        },
    )
    canonical = runkernel_canonical_graph(
        candidate,
        action_ref={
            "action_id": action.action_id,
            "action_type": action.action_type.value,
            "stage": action.stage,
            "sequence": action.sequence,
            "operation": "synthesis_admission",
            "synthesis_key": synthesis_key,
        },
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={"component_work_graph_v1": canonical},
        )
    )
    return deepcopy(canonical)


def validate_component_work_graph_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    graph = _json_safe(value)
    if not isinstance(graph, dict):
        raise ComponentWorkGraphV1Error("Graph V1 must be a mapping")
    if graph.get("schema_version") != COMPONENT_WORK_GRAPH_V1_SCHEMA_VERSION:
        raise ComponentWorkGraphV1Error("Graph V1 schema mismatch")
    if graph.get("supported_query_class") != SUPPORTED_QUERY_CLASS:
        raise ComponentWorkGraphV1Error("Graph V1 supported query class mismatch")
    for key in ("graph_id", "graph_digest", "run_id", "request_id"):
        if not _clean_text(graph.get(key), limit=200):
            raise ComponentWorkGraphV1Error(f"Graph V1 requires {key}")
    components = [
        validate_component_work_node_v1(item) for item in graph.get("component_nodes") or ()
    ]
    if not MIN_COMPONENT_NODES <= len(components) <= MAX_COMPONENT_NODES:
        raise ComponentWorkGraphV1Error("Graph V1 component count invalid")
    synthesis_nodes = [
        _validate_synthesis_node(item, graph=graph)
        for item in graph.get("synthesis_nodes") or ()
    ]
    amended_awaiting_resynthesis = (
        not synthesis_nodes
        and graph.get("dependency_posture") == "requires_fresh_resynthesis"
        and graph.get("graph_status") == GRAPH_STATUS_STALE
        and int(graph.get("automatic_recovery_rounds") or 0) == 1
        and int(graph.get("graph_amendment_rounds") or 0) == 1
    )
    if not amended_awaiting_resynthesis and not (
        1 <= len(synthesis_nodes) <= MAX_SYNTHESIS_NODES
    ):
        raise ComponentWorkGraphV1Error("Graph V1 synthesis count invalid")
    all_nodes = [*components, *synthesis_nodes]
    if len({item["node_id"] for item in all_nodes}) != len(all_nodes):
        raise ComponentWorkGraphV1Error("Graph V1 duplicate node id")
    node_by_id = {item["node_id"]: item for item in all_nodes}
    edges = list(graph.get("edges") or ())
    edge_ids: set[str] = set()
    edge_pairs: set[tuple[str, str]] = set()
    for edge in edges:
        item = _safe_mapping(edge)
        if not item.get("edge_id") or not item.get("edge_digest"):
            raise ComponentWorkGraphV1Error("Graph V1 edge identity missing")
        if item["edge_id"] in edge_ids:
            raise ComponentWorkGraphV1Error("Graph V1 duplicate edge id")
        pair = (str(item.get("from_node_id")), str(item.get("to_node_id")))
        if pair in edge_pairs:
            raise ComponentWorkGraphV1Error("Graph V1 duplicate edge")
        if pair[0] not in node_by_id or pair[1] not in node_by_id:
            raise ComponentWorkGraphV1Error("Graph V1 edge references unknown node")
        if node_by_id[pair[1]].get("node_kind") != "synthesis":
            raise ComponentWorkGraphV1Error("Graph V1 edges must target synthesis nodes")
        expected_edge_digest = _digest(
            {
                key: value
                for key, value in item.items()
                if key not in {"edge_id", "edge_digest"}
            }
        )
        if item.get("edge_digest") != expected_edge_digest:
            raise ComponentWorkGraphV1Error("Graph V1 edge digest mismatch")
        edge_ids.add(item["edge_id"])
        edge_pairs.add(pair)
    for challenge in graph.get("challenge_refs") or ():
        item = _safe_mapping(challenge)
        if item.get("target_kind") not in {
            "component",
            "synthesis",
            "edge",
            "subgraph",
            "graph",
        }:
            raise ComponentWorkGraphV1Error("Graph V1 challenge target kind invalid")
        if not item.get("target_key") or not _safe_mapping(
            item.get("resolved_target")
        ):
            raise ComponentWorkGraphV1Error("Graph V1 resolved challenge target missing")
        if (
            item.get("resolution_graph_id") != graph.get("graph_id")
            or item.get("run_id") != graph.get("run_id")
            or item.get("request_id") != graph.get("request_id")
        ):
            raise ComponentWorkGraphV1Error("Graph V1 challenge cross-run binding")
        if int(item.get("resolution_graph_revision") or 0) >= int(
            graph.get("graph_revision") or 0
        ):
            raise ComponentWorkGraphV1Error("Graph V1 challenge revision binding invalid")
    if amended_awaiting_resynthesis:
        if edges:
            raise ComponentWorkGraphV1Error(
                "amended Graph V1 cannot retain current semantic edges"
            )
    elif not edges or graph.get("dependency_posture") != "explicitly_assessed":
        raise ComponentWorkGraphV1Error(
            "Graph V1 cannot treat empty or unknown dependency posture as independence"
        )
    if max((item["synthesis_depth"] for item in synthesis_nodes), default=0) > MAX_SYNTHESIS_DEPTH:
        raise ComponentWorkGraphV1Error("Graph V1 synthesis depth invalid")
    order = list(graph.get("synthesis_topological_order") or ())
    synthesis_by_id = {item["node_id"]: item for item in synthesis_nodes}
    synthesis_by_key = {item["synthesis_key"]: item for item in synthesis_nodes}
    if len(synthesis_by_key) != len(synthesis_nodes) or set(order) != set(
        synthesis_by_key
    ) or len(order) != len(synthesis_nodes):
        raise ComponentWorkGraphV1Error("Graph V1 topological order invalid")
    seen_synthesis: set[str] = set()
    computed_depths: dict[str, int] = {}
    for key in order:
        node = synthesis_by_key[key]
        upstream_keys: list[str] = []
        for ref in node.get("input_node_refs") or ():
            upstream = synthesis_by_id.get(ref.get("node_id"))
            if upstream:
                upstream_key = str(upstream["synthesis_key"])
                if upstream_key not in seen_synthesis:
                    raise ComponentWorkGraphV1Error(
                        "Graph V1 topological order contains a cycle or forward dependency"
                    )
                upstream_keys.append(upstream_key)
        computed_depth = 1 + max(
            (computed_depths[item] for item in upstream_keys),
            default=0,
        )
        if int(node.get("synthesis_depth") or 0) != computed_depth:
            raise ComponentWorkGraphV1Error("Graph V1 synthesis depth mismatch")
        computed_depths[key] = computed_depth
        seen_synthesis.add(key)
    if int(graph.get("maximum_synthesis_depth") or 0) != max(
        computed_depths.values(), default=0
    ):
        raise ComponentWorkGraphV1Error("Graph V1 maximum depth mismatch")
    expected_digest = _digest(_without_graph_digest(graph))
    if graph.get("graph_digest") != expected_digest:
        raise ComponentWorkGraphV1Error("Graph V1 digest mismatch")
    if graph.get("runtime_parallelism") is not False:
        raise ComponentWorkGraphV1Error("Graph V1 runtime parallelism is closed")
    if graph.get("scheduler_created") is not False or graph.get("budget_lease_created") is not False:
        raise ComponentWorkGraphV1Error("Graph V1 scheduler and leases are closed")
    if int(graph.get("automatic_recovery_rounds") or 0) not in {0, 1}:
        raise ComponentWorkGraphV1Error("Graph V1 recovery round count invalid")
    if int(graph.get("graph_amendment_rounds") or 0) not in {0, 1}:
        raise ComponentWorkGraphV1Error("Graph V1 amendment round count invalid")
    if int(graph.get("whole_graph_resynthesis_rounds") or 0) not in {0, 1}:
        raise ComponentWorkGraphV1Error("Graph V1 resynthesis round count invalid")
    graph["component_nodes"] = components
    graph["synthesis_nodes"] = synthesis_nodes
    return graph


def _validate_synthesis_node(
    value: Mapping[str, Any],
    *,
    graph: Mapping[str, Any],
) -> dict[str, Any]:
    node = _safe_mapping(value)
    if node.get("schema_version") != "synthesis_work_node_v1":
        raise ComponentWorkGraphV1Error("synthesis node schema mismatch")
    if node.get("node_kind") != "synthesis":
        raise ComponentWorkGraphV1Error("synthesis node kind mismatch")
    for key in (
        "node_id",
        "node_revision",
        "node_digest",
        "run_id",
        "request_id",
        "synthesis_key",
        "claim_text",
    ):
        if not _clean_text(node.get(key), limit=1200):
            raise ComponentWorkGraphV1Error(f"synthesis node requires {key}")
    if node.get("run_id") != graph.get("run_id") or node.get("request_id") != graph.get("request_id"):
        raise ComponentWorkGraphV1Error("synthesis node cross-run binding")
    if node.get("status") not in {
        "proposed",
        "validated",
        "admitted",
        "challenged",
        "blocked",
        "blocked_dependency",
        "stale",
    }:
        raise ComponentWorkGraphV1Error("synthesis node status invalid")
    if node.get("status") == "admitted" and not _safe_mapping(
        node.get("runkernel_admission_ref")
    ):
        raise ComponentWorkGraphV1Error("admitted synthesis lacks RunKernel ref")
    if node.get("status") in {"validated", "admitted"} and not _safe_mapping(
        node.get("dprime_validation_ref")
    ):
        raise ComponentWorkGraphV1Error("validated synthesis lacks D-prime ref")
    if node.get("status") in {"validated", "admitted"}:
        if (
            not node.get("dprime_validated_node_revision")
            or not node.get("dprime_validated_node_digest")
        ):
            raise ComponentWorkGraphV1Error(
                "validated synthesis lacks D-prime revision proof"
            )
    expected = _digest(_node_digest_payload(node))
    if node.get("node_digest") != expected:
        raise ComponentWorkGraphV1Error("synthesis node digest mismatch")
    return node


def _topological_synthesis_order(
    proposals: Sequence[Mapping[str, Any]],
) -> tuple[list[str], dict[str, int]]:
    pending = {str(item["synthesis_key"]): dict(item) for item in proposals}
    order: list[str] = []
    depths: dict[str, int] = {}
    while pending:
        progressed = False
        for key, proposal in list(pending.items()):
            upstream = list(proposal.get("synthesis_inputs") or ())
            if any(item not in depths for item in upstream):
                continue
            depths[key] = 1 + max((depths[item] for item in upstream), default=0)
            order.append(key)
            pending.pop(key)
            progressed = True
        if not progressed:
            raise ComponentWorkGraphV1Error("Graph V1 synthesis cycle detected")
    return order, depths


def _synthesis_node(graph: Mapping[str, Any], synthesis_key: str) -> dict[str, Any]:
    for node in graph.get("synthesis_nodes") or ():
        if isinstance(node, Mapping) and node.get("synthesis_key") == synthesis_key:
            return node  # type: ignore[return-value]
    raise ComponentWorkGraphV1Error(f"unknown synthesis node: {synthesis_key}")


def _input_nodes(
    graph: Mapping[str, Any],
    synthesis_node: Mapping[str, Any],
) -> list[dict[str, Any]]:
    node_by_id = {
        item["node_id"]: item
        for item in [*graph["component_nodes"], *graph["synthesis_nodes"]]
    }
    out: list[dict[str, Any]] = []
    for ref in synthesis_node.get("input_node_refs") or ():
        item = _safe_mapping(ref)
        node = node_by_id.get(item.get("node_id"))
        if node is None:
            raise ComponentWorkGraphV1Error("synthesis input ref is unknown")
        if (
            item.get("node_revision") != node.get("node_revision")
            or item.get("node_digest") != node.get("node_digest")
        ):
            raise ComponentWorkGraphV1Error("synthesis input ref is stale")
        out.append(node)
    return out


def _node_digest_payload(node: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in node.items()
        if key
        not in {
            "node_digest",
            "dprime_validated_node_revision",
            "dprime_validated_node_digest",
        }
    }


def _refresh_node_digest(node: dict[str, Any]) -> None:
    node["node_revision"] = str(int(node.get("node_revision") or 0) + 1)
    node["node_digest"] = _digest(_node_digest_payload(node))


def _refresh_dependent_refs(graph: dict[str, Any]) -> None:
    nodes = {
        item["node_id"]: item
        for item in [*graph["component_nodes"], *graph["synthesis_nodes"]]
    }
    for node in graph["synthesis_nodes"]:
        refreshed = []
        for ref in node["input_node_refs"]:
            upstream = nodes.get(ref["node_id"])
            refreshed.append(_node_ref(upstream) if upstream else ref)
        if refreshed != node["input_node_refs"]:
            node["input_node_refs"] = refreshed
            node["node_digest"] = _digest(_node_digest_payload(node))
    for edge in graph["edges"]:
        upstream = nodes.get(edge["from_node_id"])
        if upstream:
            edge["from_node_revision"] = upstream["node_revision"]
            edge["from_node_digest"] = upstream["node_digest"]
            edge["edge_digest"] = _digest(
                {
                    key: value
                    for key, value in edge.items()
                    if key not in {"edge_id", "edge_digest"}
                }
            )


def _next_revision(graph: dict[str, Any]) -> dict[str, Any]:
    previous = graph.get("graph_digest")
    graph["previous_graph_digest"] = previous
    graph["graph_revision"] = int(graph.get("graph_revision") or 0) + 1
    _refresh_dependent_refs(graph)
    graph["graph_digest"] = _digest(_without_graph_digest(graph))
    return validate_component_work_graph_v1(graph)


def _clear_synthesis_validation_and_admission(node: dict[str, Any]) -> None:
    node["dprime_validation_ref"] = {}
    node.pop("dprime_validated_node_revision", None)
    node.pop("dprime_validated_node_digest", None)
    node["runkernel_admission_ref"] = {}


def _invalidate_challenged_dependents(graph: dict[str, Any]) -> None:
    # Upstream nodes that lost readiness (challenge or material caveat/nonclaim
    # drift) invalidate every dependent synthesis transitively.
    invalidated_ids = {
        item["node_id"]
        for item in graph["synthesis_nodes"]
        if item["status"] in {"challenged", "proposed", "blocked", "blocked_dependency"}
    }
    changed = True
    while changed:
        changed = False
        for node in graph["synthesis_nodes"]:
            if node["status"] in {"challenged", "blocked_dependency"}:
                continue
            if any(ref["node_id"] in invalidated_ids for ref in node["input_node_refs"]):
                node["status"] = "blocked_dependency"
                _clear_synthesis_validation_and_admission(node)
                _refresh_node_digest(node)
                invalidated_ids.add(node["node_id"])
                changed = True


__all__ = [
    "COMPONENT_WORK_GRAPH_V1_OWNER",
    "COMPONENT_WORK_GRAPH_V1_SCHEMA_VERSION",
    "COMPONENT_WORK_GRAPH_V1_STAGE",
    "GRAPH_STATUS_BLOCKED",
    "GRAPH_STATUS_CHALLENGED",
    "GRAPH_STATUS_MISSING_DEPENDENCY",
    "GRAPH_STATUS_MISSING_SCRUTINY",
    "GRAPH_STATUS_PARTIAL",
    "GRAPH_STATUS_READY",
    "GRAPH_STATUS_READY_WITH_CAVEATS",
    "GRAPH_STATUS_RECOVERY_UNAVAILABLE",
    "GRAPH_STATUS_STALE",
    "GRAPH_STATUS_UNSUPPORTED",
    "MAX_COMPONENT_NODES",
    "MAX_SYNTHESIS_DEPTH",
    "MAX_SYNTHESIS_NODES",
    "ComponentWorkGraphV1Error",
    "admit_synthesis_node_via_runkernel",
    "component_work_graph_v1_from_cross_component_artifact",
    "component_work_graph_v1_resynthesis_from_cross_component_artifact",
    "cross_component_input_packet",
    "derive_multicomponent_role_call_accounting",
    "expected_graph_after_transition",
    "finalize_component_work_graph_v1",
    "graph_with_accounting",
    "graph_with_recovered_component",
    "graph_with_scrutineer",
    "graph_with_synthesis_admission",
    "graph_with_synthesis_validation",
    "runkernel_canonical_graph",
    "reduce_component_work_graph_v1",
    "scrutineer_input_packet",
    "synthesis_dprime_input_packet",
    "validate_component_work_graph_v1",
]
