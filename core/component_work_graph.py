"""ComponentWorkGraph V0 no-execution contract over ComponentWorkNode refs.

The graph is an inert validated manifest. It carries compact typed refs,
dependency refs, future externally supplied synthesis/admission refs, false
closed-surface flags, and nonclaims. It does not execute, schedule, dispatch
retrieval, validate synthesis, admit support, create FAP/Author/source display,
render citations, or claim product correctness.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_work_node import COMPONENT_WORK_NODE_V0_SCHEMA_VERSION

COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION = "component_work_graph_v0"
COMPONENT_WORK_GRAPH_V0_PHASE = "COMPONENTWORKGRAPH-V0-NOEXEC-CONTRACT-01"
COMPONENT_WORK_GRAPH_V0_RUNTIME_CONSUMER = (
    "future Cross-Component Analyst Workbench / ComponentWorkGraph phases"
)

GRAPH_STATUS_DRAFT = "draft"
GRAPH_STATUS_PROPOSED = "proposed"
GRAPH_STATUS_BLOCKED_MISSING_COMPONENT = "blocked_missing_component"
GRAPH_STATUS_BLOCKED_DEPENDENCY = "blocked_dependency"
GRAPH_STATUS_READY_FOR_CROSS_COMPONENT_ANALYSIS = (
    "ready_for_cross_component_analysis"
)
GRAPH_STATUS_CROSS_COMPONENT_ANALYSIS_PROPOSED = (
    "cross_component_analysis_proposed"
)
GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED = "synthesis_validation_required"
GRAPH_STATUS_SYNTHESIS_VALIDATED = "synthesis_validated"
GRAPH_STATUS_RUNKERNEL_ADMISSION_REQUIRED = "runkernel_admission_required"
GRAPH_STATUS_ADMITTED = "admitted"
GRAPH_STATUS_BLOCKED = "blocked"
GRAPH_STATUS_CLOSED = "closed"

ALLOWED_GRAPH_STATUSES = frozenset(
    {
        GRAPH_STATUS_DRAFT,
        GRAPH_STATUS_PROPOSED,
        GRAPH_STATUS_BLOCKED_MISSING_COMPONENT,
        GRAPH_STATUS_BLOCKED_DEPENDENCY,
        GRAPH_STATUS_READY_FOR_CROSS_COMPONENT_ANALYSIS,
        GRAPH_STATUS_CROSS_COMPONENT_ANALYSIS_PROPOSED,
        GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED,
        GRAPH_STATUS_SYNTHESIS_VALIDATED,
        GRAPH_STATUS_RUNKERNEL_ADMISSION_REQUIRED,
        GRAPH_STATUS_ADMITTED,
        GRAPH_STATUS_BLOCKED,
        GRAPH_STATUS_CLOSED,
    }
)

BUILDER_GRAPH_STATUSES = frozenset(
    {
        GRAPH_STATUS_DRAFT,
        GRAPH_STATUS_PROPOSED,
        GRAPH_STATUS_BLOCKED_MISSING_COMPONENT,
        GRAPH_STATUS_BLOCKED_DEPENDENCY,
        GRAPH_STATUS_READY_FOR_CROSS_COMPONENT_ANALYSIS,
    }
)

GRAPH_CLOSED_DOWNSTREAM_FLAGS = {
    "graph_executed_nodes": False,
    "graph_scheduled_runtime_work": False,
    "runtime_parallelism_executed": False,
    "budget_lease_created": False,
    "graph_dispatched_search": False,
    "graph_called_provider": False,
    "graph_called_model": False,
    "graph_called_fetch_read": False,
    "graph_called_retrieval": False,
    "graph_admitted_evidence": False,
    "graph_validated_synthesis": False,
    "graph_created_runkernel_admission": False,
    "graph_created_sufficiency_readiness": False,
    "graph_created_fap": False,
    "graph_created_author_output": False,
    "graph_created_source_display": False,
    "graph_rendered_citations": False,
    "graph_claimed_product_correctness": False,
}

GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_source_text_retained": False,
    "raw_text_retained": False,
    "raw_page_text_retained": False,
    "raw_page_content_retained": False,
    "source_text_retained": False,
    "bounded_text_retained": False,
    "full_text_retained": False,
    "html_retained": False,
    "raw_html_retained": False,
    "raw_prompt_retained": False,
    "full_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
    "local_output_packet_retained": False,
    "secrets_retained": False,
}

GRAPH_NONCLAIMS = (
    "ComponentWorkGraph V0 is a no-execution ref manifest.",
    "ComponentWorkGraph V0 does not schedule runtime work or execute graph nodes.",
    "ComponentWorkGraph V0 does not dispatch search, provider, model, fetch/read, or retrieval work.",
    "ComponentWorkGraph V0 does not create Cross-Component Analyst, synthesis D-prime, or RunKernel admission refs.",
    "ComponentWorkGraph V0 does not create FAP, Author output, source display, rendered citations, or product correctness.",
)

_FORBIDDEN_NORMALIZED_KEYS = {
    "api_key",
    "authorization",
    "bounded_text",
    "cache_row",
    "cookie",
    "cookies",
    "db_row",
    "env",
    "full_prompt",
    "full_text",
    "full_trace",
    "headers",
    "html",
    "local_output_packet",
    "model_response",
    "page_content",
    "page_text",
    "password",
    "private_log",
    "prompt",
    "raw_html",
    "raw_model_response",
    "raw_page_content",
    "raw_page_text",
    "raw_prompt",
    "raw_provider_payload",
    "raw_search_response",
    "raw_source_text",
    "raw_text",
    "secret",
    "secrets",
    "source_text",
    "token",
}

_ALLOWED_FALSE_KEYS = frozenset(
    {
        *GRAPH_CLOSED_DOWNSTREAM_FLAGS,
        *GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
        "raw_source_content_retained",
        "raw_prompt_retained",
        "raw_model_response_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "private_logs_retained",
        "db_cache_rows_retained",
        "full_trace_retained",
        "provider_payload_retained",
        "citation_eligible",
        "citation_eligibility_created",
        "citation_rendered",
        "created_by_component_work_graph",
        "evidence_admitted",
        "final_answer_packet_created",
        "source_display_created",
        "source_obligation_satisfied",
        "source_obligation_satisfaction_claimed",
        "support_admitted",
        "support_claimed",
        "product_correctness_claimed",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *GRAPH_CLOSED_DOWNSTREAM_FLAGS,
        "admitted_support",
        "answer_created",
        "author_created",
        "author_output_created",
        "budget_lease_created",
        "citation_eligible",
        "citation_eligibility_created",
        "citation_rendered",
        "component_coverage_bound",
        "component_refs_collapsed",
        "cross_component_analyst_runtime_created",
        "direct_retrieval_dispatch",
        "evidence_admitted",
        "fap_created",
        "final_answer_packet_created",
        "graph_created_citation_eligibility",
        "graph_created_source_obligation_satisfaction",
        "graph_executed",
        "graph_ran_nodes",
        "graph_scheduled",
        "graph_synthesized_answer",
        "model_called",
        "parallel_runtime_executed",
        "product_correctness_claimed",
        "provider_called",
        "retrieval_dispatched",
        "runkernel_admission_created",
        "search_dispatched",
        "source_display_created",
        "source_obligation_satisfied",
        "source_obligation_satisfaction_claimed",
        "support_admitted",
        "support_claimed",
        "synthesis_validated_by_graph",
    }
)

_SUMMARY_ONLY_KEYS = frozenset(
    {
        "collapsed_component_summary",
        "component_node_summary",
        "component_node_summaries",
        "component_refs_collapsed",
        "component_summaries",
        "component_summary",
        "raw_component_summary",
        "untraceable_component_summary",
    }
)

class ComponentWorkGraphError(ValueError):
    """Raised when ComponentWorkGraph V0 would cross the no-execution boundary."""


def component_work_graph_v0_from_component_nodes(
    *,
    parent_run_id: str,
    parent_run_ref: Mapping[str, Any],
    user_query_ref: Mapping[str, Any],
    supported_query_class: str,
    answer_contract_ref: Mapping[str, Any],
    component_node_refs: Sequence[Mapping[str, Any]],
    graph_id: str | None = None,
    graph_status: str = GRAPH_STATUS_PROPOSED,
    dependency_edges: Sequence[Mapping[str, Any]] | None = None,
    blocking_dependency_refs: Sequence[Mapping[str, Any]] | None = None,
    nonblocking_dependency_refs: Sequence[Mapping[str, Any]] | None = None,
    cross_component_analyst_refs: Sequence[Mapping[str, Any]] | None = None,
    synthesis_proposal_refs: Sequence[Mapping[str, Any]] | None = None,
    dprime_synthesis_validation_refs: Sequence[Mapping[str, Any]] | None = None,
    runkernel_synthesis_admission_refs: Sequence[Mapping[str, Any]] | None = None,
    recovery_request_refs: Sequence[Mapping[str, Any]] | None = None,
    missing_component_proposal_refs: Sequence[Mapping[str, Any]] | None = None,
    contract_amendment_candidate_refs: Sequence[Mapping[str, Any]] | None = None,
    nonclaims: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Build a validated inert graph manifest from typed ComponentWorkNode refs."""

    status = _required_status(graph_status)
    supplied_synthesis_refs = _external_refs(
        synthesis_proposal_refs,
        field_name="synthesis_proposal_refs",
    )
    if status == GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED:
        if not supplied_synthesis_refs:
            raise ComponentWorkGraphError(
                "builder cannot require synthesis validation without external synthesis proposal refs"
            )
    elif status not in BUILDER_GRAPH_STATUSES:
        raise ComponentWorkGraphError(
            "builder cannot create future graph authority status"
        )

    nodes = _validate_component_node_refs(component_node_refs)
    node_index = _component_node_index(nodes)
    edges = _validate_dependency_edges(dependency_edges or [], node_index=node_index)
    graph_id_value = (
        _clean_text(graph_id, limit=260)
        or _default_graph_id(
            parent_run_id=parent_run_id,
            component_node_refs=nodes,
            dependency_edges=edges,
        )
    )
    blocking_refs = _safe_refs(blocking_dependency_refs)
    nonblocking_refs = _safe_refs(nonblocking_dependency_refs)
    if not blocking_refs and not nonblocking_refs:
        for edge in edges:
            edge_ref = _dependency_edge_ref(edge)
            if edge.get("blocking") is True:
                blocking_refs.append(edge_ref)
            else:
                nonblocking_refs.append(edge_ref)

    graph = {
        "schema_version": COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
        "phase": COMPONENT_WORK_GRAPH_V0_PHASE,
        "runtime_consumer": COMPONENT_WORK_GRAPH_V0_RUNTIME_CONSUMER,
        "graph_id": graph_id_value,
        "graph_digest": None,
        "parent_run_id": _required_text(parent_run_id, "parent_run_id"),
        "parent_run_ref": _require_mapping_ref(parent_run_ref, "parent_run_ref"),
        "user_query_ref": _require_mapping_ref(user_query_ref, "user_query_ref"),
        "supported_query_class": _required_text(
            supported_query_class,
            "supported_query_class",
        ),
        "answer_contract_ref": _require_mapping_ref(
            answer_contract_ref,
            "answer_contract_ref",
        ),
        "graph_status": status,
        "component_node_refs": nodes,
        "component_node_count": _component_node_count(nodes),
        "dependency_edges": edges,
        "blocking_dependency_refs": blocking_refs,
        "nonblocking_dependency_refs": nonblocking_refs,
        "cross_component_analyst_refs": _external_refs(
            cross_component_analyst_refs,
            field_name="cross_component_analyst_refs",
        ),
        "synthesis_proposal_refs": supplied_synthesis_refs,
        "dprime_synthesis_validation_refs": _external_refs(
            dprime_synthesis_validation_refs,
            field_name="dprime_synthesis_validation_refs",
        ),
        "runkernel_synthesis_admission_refs": _external_refs(
            runkernel_synthesis_admission_refs,
            field_name="runkernel_synthesis_admission_refs",
        ),
        "recovery_request_refs": _safe_refs(recovery_request_refs),
        "missing_component_proposal_refs": _safe_refs(
            missing_component_proposal_refs
        ),
        "contract_amendment_candidate_refs": _safe_refs(
            contract_amendment_candidate_refs
        ),
        "closed_downstream_flags": dict(GRAPH_CLOSED_DOWNSTREAM_FLAGS),
        "raw_private_retention_flags": dict(GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS),
        "nonclaims": _nonclaims(nonclaims),
        **GRAPH_CLOSED_DOWNSTREAM_FLAGS,
    }
    graph["graph_digest"] = _digest_json(_without_digest(graph))
    return validate_component_work_graph_v0(graph)


def validate_component_work_graph_v0(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a ComponentWorkGraph V0 no-execution manifest."""

    graph = _safe_mapping(value)
    _reject_multiple_graph_ids(graph)
    _reject_summary_only_component_payload(graph)
    _reject_forbidden_material(graph, context="ComponentWorkGraph V0")
    if graph.get("schema_version") != COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION:
        raise ComponentWorkGraphError("ComponentWorkGraph schema mismatch")
    if graph.get("phase") != COMPONENT_WORK_GRAPH_V0_PHASE:
        raise ComponentWorkGraphError("ComponentWorkGraph phase mismatch")
    graph_id = _required_text(graph.get("graph_id"), "graph_id")
    parent_run_id = _required_text(graph.get("parent_run_id"), "parent_run_id")
    status = _required_status(graph.get("graph_status"))
    parent_run_ref = _require_mapping_ref(graph.get("parent_run_ref"), "parent_run_ref")
    user_query_ref = _require_mapping_ref(graph.get("user_query_ref"), "user_query_ref")
    supported_query_class = _required_text(
        graph.get("supported_query_class"),
        "supported_query_class",
    )
    answer_contract_ref = _require_mapping_ref(
        graph.get("answer_contract_ref"),
        "answer_contract_ref",
    )
    nodes = _validate_component_node_refs(graph.get("component_node_refs"))
    node_index = _component_node_index(nodes)
    declared_count = _bounded_int(graph.get("component_node_count"), default=-1)
    actual_count = _component_node_count(nodes)
    if declared_count != actual_count:
        raise ComponentWorkGraphError(
            "ComponentWorkGraph component count must come from component node refs"
        )
    edges = _validate_dependency_edges(
        graph.get("dependency_edges") or [],
        node_index=node_index,
    )
    blocking_refs = _safe_refs(graph.get("blocking_dependency_refs"))
    nonblocking_refs = _safe_refs(graph.get("nonblocking_dependency_refs"))
    cross_component_analyst_refs = _validate_external_refs(
        graph.get("cross_component_analyst_refs"),
        field_name="cross_component_analyst_refs",
    )
    synthesis_proposal_refs = _validate_external_refs(
        graph.get("synthesis_proposal_refs"),
        field_name="synthesis_proposal_refs",
    )
    dprime_synthesis_validation_refs = _validate_external_refs(
        graph.get("dprime_synthesis_validation_refs"),
        field_name="dprime_synthesis_validation_refs",
    )
    runkernel_synthesis_admission_refs = _validate_external_refs(
        graph.get("runkernel_synthesis_admission_refs"),
        field_name="runkernel_synthesis_admission_refs",
    )
    _validate_status_refs(
        status,
        cross_component_analyst_refs=cross_component_analyst_refs,
        synthesis_proposal_refs=synthesis_proposal_refs,
        dprime_synthesis_validation_refs=dprime_synthesis_validation_refs,
        runkernel_synthesis_admission_refs=runkernel_synthesis_admission_refs,
    )
    closed_flags = _validate_closed_downstream_flags(graph)
    raw_flags = _validate_raw_private_flags(graph)
    normalized = {
        **_json_safe(graph),
        "graph_id": graph_id,
        "parent_run_id": parent_run_id,
        "parent_run_ref": parent_run_ref,
        "user_query_ref": user_query_ref,
        "supported_query_class": supported_query_class,
        "answer_contract_ref": answer_contract_ref,
        "graph_status": status,
        "component_node_refs": nodes,
        "component_node_count": actual_count,
        "dependency_edges": edges,
        "blocking_dependency_refs": blocking_refs,
        "nonblocking_dependency_refs": nonblocking_refs,
        "cross_component_analyst_refs": cross_component_analyst_refs,
        "synthesis_proposal_refs": synthesis_proposal_refs,
        "dprime_synthesis_validation_refs": dprime_synthesis_validation_refs,
        "runkernel_synthesis_admission_refs": runkernel_synthesis_admission_refs,
        "recovery_request_refs": _safe_refs(graph.get("recovery_request_refs")),
        "missing_component_proposal_refs": _safe_refs(
            graph.get("missing_component_proposal_refs")
        ),
        "contract_amendment_candidate_refs": _safe_refs(
            graph.get("contract_amendment_candidate_refs")
        ),
        "closed_downstream_flags": closed_flags,
        "raw_private_retention_flags": raw_flags,
        "nonclaims": _nonclaims(graph.get("nonclaims")),
        **closed_flags,
    }
    declared = _clean_text(graph.get("graph_digest"), limit=128)
    digest = _digest_json(_without_digest(normalized))
    if declared and declared != digest:
        raise ComponentWorkGraphError("ComponentWorkGraph digest mismatch")
    normalized["graph_digest"] = digest
    _reject_forbidden_material(normalized, context="ComponentWorkGraph V0")
    return normalized


def _validate_component_node_refs(value: Any) -> list[dict[str, Any]]:
    refs = _safe_sequence(value)
    if not refs:
        raise ComponentWorkGraphError("ComponentWorkGraph requires component_node_refs")
    nodes: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()
    for item in refs:
        ref = _compact_component_node_ref(item)
        node_id = ref["node_id"]
        if node_id in seen_node_ids:
            raise ComponentWorkGraphError("ComponentWorkGraph duplicate node id")
        seen_node_ids.add(node_id)
        nodes.append(ref)
    return nodes


def _compact_component_node_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if not ref:
        raise ComponentWorkGraphError("ComponentWorkGraph component node ref malformed")
    _reject_summary_only_component_payload(ref)
    _reject_forbidden_material(ref, context="ComponentWorkGraph component node ref")
    combined_digest = _clean_text(
        ref.get("component_work_node_v0_digest"),
        limit=128,
    )
    output_ref = _safe_mapping(ref.get("component_work_node_v0_output_ref"))
    node = output_ref or ref
    if node.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
        raise ComponentWorkGraphError(
            "ComponentWorkGraph requires typed ComponentWorkNode refs"
        )
    node_id = _required_text(node.get("node_id"), "component node_id")
    component_id = _required_text(node.get("component_id"), "component_id")
    component_ids = _text_tuple(node.get("component_ids"), limit=320)
    if len(component_ids) != 1 or component_ids[0] != component_id:
        raise ComponentWorkGraphError(
            "ComponentWorkGraph component node refs must remain one component each"
        )
    source_lane_ids = _text_tuple(node.get("source_obligation_lane_ids"), limit=320)
    if len(source_lane_ids) != 1:
        raise ComponentWorkGraphError(
            "ComponentWorkGraph component node ref must carry exactly one "
            "source-obligation lane ref"
        )
    source_obligation_id = _clean_text(node.get("source_obligation_id"), limit=320)
    if source_obligation_id and source_obligation_id != source_lane_ids[0]:
        raise ComponentWorkGraphError(
            "ComponentWorkGraph component node source_obligation_id must match "
            "its single source-obligation lane ref"
        )
    compact = _without_empty(
        {
            "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
            "node_kind": node.get("node_kind") or "component_work_node_v0_ref",
            "node_id": node_id,
            "component_id": component_id,
            "component_ids": [component_id],
            "source_obligation_lane_ids": list(source_lane_ids),
            "source_obligation_id": source_obligation_id,
            "node_status": node.get("node_status")
            or ref.get("component_work_node_v0_status"),
            "component_work_node_v0_digest": combined_digest,
            "input_ref_digest": node.get("input_ref_digest"),
            "output_ref_digest": node.get("output_ref_digest"),
            "multi_source_shape_ref": _compact_multi_source_shape_ref(
                _safe_mapping(node.get("multi_source_shape_ref"))
            ),
            "closed_downstream_flags": _safe_mapping(
                node.get("closed_downstream_flags")
            ),
            "raw_private_retention_flags": _safe_mapping(
                node.get("raw_private_retention_flags")
            ),
            "graph_ref_only": True,
            "component_node_ref_collapsed_to_summary": False,
        }
    )
    _reject_forbidden_material(compact, context="ComponentWorkGraph component node ref")
    return _json_safe(compact)


def _compact_multi_source_shape_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    if not value:
        return {}
    ref = _without_empty(
        {
            "status": value.get("status"),
            "relation_count": _bounded_int(value.get("relation_count")),
            "source_count": _bounded_int(value.get("source_count")),
            "relation_ref_count": _bounded_int(value.get("relation_ref_count")),
            "source_ref_count": _bounded_int(value.get("source_ref_count")),
            "candidate_ref_count": _bounded_int(value.get("candidate_ref_count")),
            "currentness_posture": value.get("currentness_posture"),
            "conflict_posture": value.get("conflict_posture"),
            "challenge_kind": value.get("challenge_kind"),
            "best_source_collapse_created": value.get(
                "best_source_collapse_created"
            )
            is True,
            "single_undifferentiated_source_output_created": value.get(
                "single_undifferentiated_source_output_created"
            )
            is True,
            "multi_component_claimed": value.get("multi_component_claimed") is True,
        }
    )
    for key in (
        "best_source_collapse_created",
        "single_undifferentiated_source_output_created",
        "multi_component_claimed",
    ):
        if ref.get(key) is True:
            raise ComponentWorkGraphError(
                "ComponentWorkGraph cannot consume collapsed or multi-component-laundered node refs"
            )
        ref[key] = False
    return ref


def _component_node_index(
    nodes: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for node in nodes:
        safe = _safe_mapping(node)
        index[str(safe.get("node_id"))] = dict(safe)
    return index


def _component_node_count(nodes: Sequence[Mapping[str, Any]]) -> int:
    component_ids = {
        _required_text(_safe_mapping(node).get("component_id"), "component_id")
        for node in nodes
    }
    return len(component_ids)


def _validate_dependency_edges(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    seen_edge_ids: set[str] = set()
    for item in _safe_sequence(value):
        edge = _normalize_dependency_edge(item, node_index=node_index)
        edge_id = edge["edge_id"]
        if edge_id in seen_edge_ids:
            raise ComponentWorkGraphError("ComponentWorkGraph duplicate edge id")
        seen_edge_ids.add(edge_id)
        edges.append(edge)
    return edges


def _normalize_dependency_edge(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    edge = _safe_mapping(value)
    if not edge:
        raise ComponentWorkGraphError("ComponentWorkGraph dependency edge malformed")
    _reject_forbidden_material(edge, context="ComponentWorkGraph dependency edge")
    from_ref = _dependency_component_ref(
        edge.get("from_component_node_ref"),
        node_index=node_index,
        field_name="from_component_node_ref",
    )
    to_ref = _dependency_component_ref(
        edge.get("to_component_node_ref"),
        node_index=node_index,
        field_name="to_component_node_ref",
    )
    if from_ref["node_id"] == to_ref["node_id"]:
        raise ComponentWorkGraphError("ComponentWorkGraph edge cannot self-depend")
    edge_id = _clean_text(edge.get("edge_id"), limit=260)
    base = {
        "schema_version": COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
        "edge_id": edge_id or _default_edge_id(from_ref=from_ref, to_ref=to_ref, edge=edge),
        "from_component_node_ref": from_ref,
        "to_component_node_ref": to_ref,
        "dependency_kind": _required_text(
            edge.get("dependency_kind"),
            "dependency_kind",
        ),
        "blocking": edge.get("blocking") is True,
        "required_upstream_status": _required_text(
            edge.get("required_upstream_status"),
            "required_upstream_status",
        ),
        "constraint_summary_ref": _require_mapping_ref(
            edge.get("constraint_summary_ref"),
            "constraint_summary_ref",
        ),
        "rationale_ref": _require_mapping_ref(edge.get("rationale_ref"), "rationale_ref"),
        "created_by": _required_text(edge.get("created_by"), "created_by"),
        "admitted_by_runkernel_ref": _runkernel_edge_admission_ref(
            edge.get("admitted_by_runkernel_ref")
        ),
    }
    digest = _digest_json(base)
    declared = _clean_text(edge.get("edge_digest"), limit=128)
    if declared and declared != digest:
        raise ComponentWorkGraphError("ComponentWorkGraph dependency edge digest mismatch")
    return {**base, "edge_digest": digest}


def _dependency_component_ref(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]],
    field_name: str,
) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if not ref:
        raise ComponentWorkGraphError(
            f"ComponentWorkGraph dependency edge missing {field_name}"
        )
    _reject_forbidden_material(ref, context=f"ComponentWorkGraph {field_name}")
    if ref.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
        raise ComponentWorkGraphError(
            "ComponentWorkGraph dependency edges require typed component-node refs"
        )
    node_id = _required_text(ref.get("node_id"), f"{field_name}.node_id")
    component_id = _required_text(ref.get("component_id"), f"{field_name}.component_id")
    known = _safe_mapping(node_index.get(node_id))
    if not known or known.get("component_id") != component_id:
        raise ComponentWorkGraphError(
            "ComponentWorkGraph dependency edge references unknown component node"
        )
    return {
        "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
        "node_id": node_id,
        "component_id": component_id,
    }


def _runkernel_edge_admission_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if not ref:
        return {
            "status": "not_admitted",
            "admitted": False,
            "externally_supplied": False,
            "created_by_component_work_graph": False,
        }
    _reject_forbidden_material(ref, context="ComponentWorkGraph edge admission ref")
    status = _normalize_key(ref.get("status"))
    if status in {"", "not_admitted", "absent"}:
        return {
            **_json_safe(ref),
            "status": "not_admitted",
            "admitted": False,
            "created_by_component_work_graph": False,
        }
    return _external_future_ref(ref, field_name="admitted_by_runkernel_ref")


def _dependency_edge_ref(edge: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(edge)
    return _without_empty(
        {
            "schema_version": COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
            "edge_id": safe.get("edge_id"),
            "edge_digest": safe.get("edge_digest"),
            "from_component_node_ref": safe.get("from_component_node_ref"),
            "to_component_node_ref": safe.get("to_component_node_ref"),
            "dependency_kind": safe.get("dependency_kind"),
            "blocking": safe.get("blocking") is True,
        }
    )


def _external_refs(value: Any, *, field_name: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        refs.append(
            _external_future_ref(
                {
                    **ref,
                    "externally_supplied": True,
                    "not_created_by_graph": True,
                    "created_by_component_work_graph": False,
                },
                field_name=field_name,
            )
        )
    return refs


def _validate_external_refs(value: Any, *, field_name: str) -> list[dict[str, Any]]:
    return [
        _external_future_ref(item, field_name=field_name)
        for item in _safe_sequence(value)
        if _safe_mapping(item)
    ]


def _external_future_ref(value: Any, *, field_name: str) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if not ref:
        raise ComponentWorkGraphError(f"ComponentWorkGraph {field_name} malformed")
    _reject_forbidden_material(ref, context=f"ComponentWorkGraph {field_name}")
    if ref.get("externally_supplied") is not True:
        raise ComponentWorkGraphError(
            f"ComponentWorkGraph {field_name} must be externally supplied"
        )
    if ref.get("created_by_component_work_graph") is not False:
        raise ComponentWorkGraphError(
            f"ComponentWorkGraph {field_name} cannot be created by graph"
        )
    if ref.get("not_created_by_graph") is not True:
        raise ComponentWorkGraphError(
            f"ComponentWorkGraph {field_name} must be labeled not created by graph"
        )
    if not _typed_external_ref(ref):
        raise ComponentWorkGraphError(
            f"ComponentWorkGraph {field_name} requires typed refs"
        )
    return _json_safe(ref)


def _typed_external_ref(ref: Mapping[str, Any]) -> bool:
    has_type = any(
        _clean_text(ref.get(key), limit=260)
        for key in ("schema_version", "ref_kind", "kind", "status")
    )
    has_identity = any(
        _clean_text(value, limit=320)
        for key, value in ref.items()
        if _normalize_key(key).endswith(("_id", "_digest", "_ref"))
        and key not in {"not_created_by_graph"}
    )
    return bool(has_type and has_identity)


def _validate_status_refs(
    status: str,
    *,
    cross_component_analyst_refs: Sequence[Mapping[str, Any]],
    synthesis_proposal_refs: Sequence[Mapping[str, Any]],
    dprime_synthesis_validation_refs: Sequence[Mapping[str, Any]],
    runkernel_synthesis_admission_refs: Sequence[Mapping[str, Any]],
) -> None:
    if (
        status == GRAPH_STATUS_CROSS_COMPONENT_ANALYSIS_PROPOSED
        and not cross_component_analyst_refs
    ):
        raise ComponentWorkGraphError(
            "cross-component analysis status requires external Workbench refs"
        )
    if status == GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED and not synthesis_proposal_refs:
        raise ComponentWorkGraphError(
            "synthesis validation required status requires external synthesis proposal refs"
        )
    if status == GRAPH_STATUS_SYNTHESIS_VALIDATED and not dprime_synthesis_validation_refs:
        raise ComponentWorkGraphError(
            "synthesis validated status requires external D-prime synthesis refs"
        )
    if (
        status == GRAPH_STATUS_RUNKERNEL_ADMISSION_REQUIRED
        and not dprime_synthesis_validation_refs
    ):
        raise ComponentWorkGraphError(
            "RunKernel admission required status requires external synthesis validation refs"
        )
    if status in {GRAPH_STATUS_ADMITTED, GRAPH_STATUS_CLOSED} and not (
        runkernel_synthesis_admission_refs
    ):
        raise ComponentWorkGraphError(
            "admitted or closed graph status requires external RunKernel admission refs"
        )


def _validate_closed_downstream_flags(graph: Mapping[str, Any]) -> dict[str, bool]:
    closed = _safe_mapping(graph.get("closed_downstream_flags"))
    if not closed:
        raise ComponentWorkGraphError("ComponentWorkGraph missing closed_downstream_flags")
    normalized: dict[str, bool] = {}
    for key in GRAPH_CLOSED_DOWNSTREAM_FLAGS:
        if closed.get(key) is not False:
            raise ComponentWorkGraphError(
                f"ComponentWorkGraph closed downstream flag must remain false: {key}"
            )
        if key in graph and graph.get(key) is not False:
            raise ComponentWorkGraphError(
                f"ComponentWorkGraph top-level downstream flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_raw_private_flags(graph: Mapping[str, Any]) -> dict[str, bool]:
    flags = _safe_mapping(graph.get("raw_private_retention_flags"))
    if not flags:
        raise ComponentWorkGraphError(
            "ComponentWorkGraph missing raw_private_retention_flags"
        )
    normalized: dict[str, bool] = {}
    for key in GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS:
        if flags.get(key) is not False:
            raise ComponentWorkGraphError(
                f"ComponentWorkGraph raw/private flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    summary_keys = sorted(_collect_keys(value) & _SUMMARY_ONLY_KEYS)
    if summary_keys:
        raise ComponentWorkGraphError(
            f"{context} collapses component refs into summary-only keys: "
            + ", ".join(summary_keys)
        )
    forbidden = sorted(_collect_keys(value) & _FORBIDDEN_NORMALIZED_KEYS)
    if forbidden:
        raise ComponentWorkGraphError(
            f"{context} includes forbidden raw/private material: "
            + ", ".join(forbidden)
        )
    invalid_false_flags = sorted(_invalid_false_flags(value))
    if invalid_false_flags:
        raise ComponentWorkGraphError(
            f"{context} raw/private or closed flags must be explicitly false: "
            + ", ".join(invalid_false_flags)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise ComponentWorkGraphError(
            f"{context} attempts forbidden no-execution authority upgrade: "
            + ", ".join(dangerous)
        )


def _reject_summary_only_component_payload(value: Mapping[str, Any]) -> None:
    keys = _collect_keys(value)
    summary = sorted(keys & _SUMMARY_ONLY_KEYS)
    if summary:
        raise ComponentWorkGraphError(
            "ComponentWorkGraph requires typed traceable component refs, not summaries: "
            + ", ".join(summary)
        )


def _reject_multiple_graph_ids(graph: Mapping[str, Any]) -> None:
    if "graph_ids" in {_normalize_key(key) for key in graph}:
        raise ComponentWorkGraphError("ComponentWorkGraph cannot carry graph_ids")
    if isinstance(graph.get("graph_id"), Sequence) and not isinstance(
        graph.get("graph_id"),
        str | bytes,
    ):
        raise ComponentWorkGraphError("ComponentWorkGraph graph_id must be singular")


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(normalized)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _invalid_false_flags(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _ALLOWED_FALSE_KEYS and item is not False:
                found.add(normalized)
            if (
                (
                    normalized.endswith("_retained")
                    or normalized.endswith("_called")
                    or normalized.endswith("_dispatched")
                    or normalized.endswith("_executed")
                )
                and item is not False
                and normalized not in {"externally_supplied"}
            ):
                found.add(normalized)
            found.update(_invalid_false_flags(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_invalid_false_flags(item))
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


def _safe_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        _reject_forbidden_material(ref, context="ComponentWorkGraph nested ref")
        refs.append(_json_safe(ref))
    return refs


def _require_mapping_ref(value: Any, key: str) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if not ref:
        raise ComponentWorkGraphError(f"ComponentWorkGraph requires {key}")
    _reject_forbidden_material(ref, context=f"ComponentWorkGraph {key}")
    return _json_safe(ref)


def _required_status(value: Any) -> str:
    status = _clean_text(value, limit=120)
    if status not in ALLOWED_GRAPH_STATUSES:
        raise ComponentWorkGraphError("ComponentWorkGraph graph status invalid")
    return status


def _required_text(value: Any, key: str) -> str:
    text = _clean_text(value, limit=900)
    if not text:
        raise ComponentWorkGraphError(f"ComponentWorkGraph requires {key}")
    return text


def _nonclaims(value: Any) -> list[str]:
    claims = list(_text_tuple(value if value is not None else GRAPH_NONCLAIMS, limit=500))
    if not claims:
        raise ComponentWorkGraphError("ComponentWorkGraph requires nonclaims")
    return claims


def _default_graph_id(
    *,
    parent_run_id: str,
    component_node_refs: Sequence[Mapping[str, Any]],
    dependency_edges: Sequence[Mapping[str, Any]],
) -> str:
    digest = _digest_json(
        {
            "phase": COMPONENT_WORK_GRAPH_V0_PHASE,
            "parent_run_id": parent_run_id,
            "component_node_refs": [
                {
                    "node_id": item.get("node_id"),
                    "component_id": item.get("component_id"),
                    "component_work_node_v0_digest": item.get(
                        "component_work_node_v0_digest"
                    ),
                    "output_ref_digest": item.get("output_ref_digest"),
                }
                for item in component_node_refs
            ],
            "dependency_edges": [
                {
                    "edge_id": item.get("edge_id"),
                    "edge_digest": item.get("edge_digest"),
                }
                for item in dependency_edges
            ],
        }
    )
    return f"component-work-graph:v0:{digest[:20]}"


def _default_edge_id(
    *,
    from_ref: Mapping[str, Any],
    to_ref: Mapping[str, Any],
    edge: Mapping[str, Any],
) -> str:
    digest = _digest_json(
        {
            "from": from_ref,
            "to": to_ref,
            "dependency_kind": edge.get("dependency_kind"),
            "required_upstream_status": edge.get("required_upstream_status"),
        }
    )
    return f"component-work-graph-edge:v0:{digest[:20]}"


def _safe_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _text_tuple(value: Any, *, limit: int) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return (text,) if text else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {}, ())
    }


def _without_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "graph_digest"}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ALLOWED_GRAPH_STATUSES",
    "BUILDER_GRAPH_STATUSES",
    "COMPONENT_WORK_GRAPH_V0_PHASE",
    "COMPONENT_WORK_GRAPH_V0_RUNTIME_CONSUMER",
    "COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION",
    "GRAPH_CLOSED_DOWNSTREAM_FLAGS",
    "GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS",
    "GRAPH_STATUS_ADMITTED",
    "GRAPH_STATUS_BLOCKED",
    "GRAPH_STATUS_BLOCKED_DEPENDENCY",
    "GRAPH_STATUS_BLOCKED_MISSING_COMPONENT",
    "GRAPH_STATUS_CLOSED",
    "GRAPH_STATUS_CROSS_COMPONENT_ANALYSIS_PROPOSED",
    "GRAPH_STATUS_DRAFT",
    "GRAPH_STATUS_PROPOSED",
    "GRAPH_STATUS_READY_FOR_CROSS_COMPONENT_ANALYSIS",
    "GRAPH_STATUS_RUNKERNEL_ADMISSION_REQUIRED",
    "GRAPH_STATUS_SYNTHESIS_VALIDATED",
    "GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED",
    "ComponentWorkGraphError",
    "component_work_graph_v0_from_component_nodes",
    "validate_component_work_graph_v0",
]
