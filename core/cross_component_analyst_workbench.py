"""Cross-Component Analyst Workbench V0 proposal contract.

The Workbench artifact is a proposal-only ref contract over an existing
ComponentWorkGraph V0 manifest. It does not validate synthesis, mutate the
parent graph or AnswerContract, dispatch retrieval, create D-prime validation,
create RunKernel admission, open FAP/Author/source display, render citations, or
claim product correctness.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_work_graph import (
    COMPONENT_WORK_GRAPH_V0_PHASE,
    COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
    GRAPH_CLOSED_DOWNSTREAM_FLAGS,
    GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
    GRAPH_STATUS_ADMITTED,
    GRAPH_STATUS_CLOSED,
    GRAPH_STATUS_RUNKERNEL_ADMISSION_REQUIRED,
    GRAPH_STATUS_SYNTHESIS_VALIDATED,
    GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED,
    validate_component_work_graph_v0,
)
from core.component_work_node import COMPONENT_WORK_NODE_V0_SCHEMA_VERSION

CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION = (
    "cross_component_analyst_workbench_v0"
)
CROSS_COMPONENT_ANALYST_WORKBENCH_V0_PHASE = (
    "CROSS-COMPONENT-SYNTHESIS-PROPOSAL-V0-01"
)
CROSS_COMPONENT_ANALYST_WORKBENCH_V0_RUNTIME_CONSUMER = (
    "future synthesis D-prime validation and RunKernel graph/synthesis admission phases"
)

ANALYSIS_STATUS_DRAFT = "draft"
ANALYSIS_STATUS_PROPOSED = "proposed"
ANALYSIS_STATUS_BLOCKED_MISSING_COMPONENT = "blocked_missing_component"
ANALYSIS_STATUS_BLOCKED_DEPENDENCY = "blocked_dependency"
ANALYSIS_STATUS_BLOCKED_CONTRADICTION = "blocked_contradiction"
ANALYSIS_STATUS_SYNTHESIS_PROPOSED = "synthesis_proposed"
ANALYSIS_STATUS_RECOVERY_PROPOSED = "recovery_proposed"
ANALYSIS_STATUS_NO_SYNTHESIS_PROPOSED = "no_synthesis_proposed"

ALLOWED_ANALYSIS_STATUSES = frozenset(
    {
        ANALYSIS_STATUS_DRAFT,
        ANALYSIS_STATUS_PROPOSED,
        ANALYSIS_STATUS_BLOCKED_MISSING_COMPONENT,
        ANALYSIS_STATUS_BLOCKED_DEPENDENCY,
        ANALYSIS_STATUS_BLOCKED_CONTRADICTION,
        ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
        ANALYSIS_STATUS_RECOVERY_PROPOSED,
        ANALYSIS_STATUS_NO_SYNTHESIS_PROPOSED,
    }
)

CROSS_COMPONENT_ANALYST_CLOSED_DOWNSTREAM_FLAGS = {
    "cross_component_analyst_validated_synthesis": False,
    "cross_component_analyst_admitted_support": False,
    "cross_component_analyst_mutated_answer_contract": False,
    "cross_component_analyst_mutated_parent_graph": False,
    "cross_component_analyst_dispatched_search": False,
    "cross_component_analyst_called_provider": False,
    "cross_component_analyst_called_model": False,
    "cross_component_analyst_called_fetch_read": False,
    "cross_component_analyst_called_retrieval": False,
    "cross_component_analyst_created_dprime_validation": False,
    "cross_component_analyst_created_runkernel_admission": False,
    "cross_component_analyst_created_sufficiency_readiness": False,
    "cross_component_analyst_created_fap": False,
    "cross_component_analyst_created_author_output": False,
    "cross_component_analyst_created_source_display": False,
    "cross_component_analyst_rendered_citations": False,
    "cross_component_analyst_claimed_product_correctness": False,
}

CROSS_COMPONENT_ANALYST_RAW_PRIVATE_RETENTION_FALSE_FLAGS = {
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

CROSS_COMPONENT_ANALYST_NONCLAIMS = (
    "Cross-Component Analyst Workbench V0 is proposal-only.",
    "Cross-Component Analyst Workbench V0 does not validate synthesis.",
    "Cross-Component Analyst Workbench V0 does not admit support or mutate AnswerContract state.",
    "Cross-Component Analyst Workbench V0 does not mutate or upgrade the parent ComponentWorkGraph.",
    "Cross-Component Analyst Workbench V0 does not dispatch search, provider, model, fetch/read, or retrieval work.",
    "Cross-Component Analyst Workbench V0 does not create FAP, Author output, source display, rendered citations, or product correctness.",
)

_REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "phase",
    "cross_component_analyst_id",
    "cross_component_analyst_digest",
    "parent_run_id",
    "parent_graph_ref",
    "component_node_refs",
    "component_node_count",
    "dependency_edge_refs",
    "input_graph_status",
    "analysis_status",
    "consistency_matrix_ref",
    "constraint_relation_refs",
    "stale_or_overbroad_component_refs",
    "contradiction_refs",
    "unresolved_dependency_refs",
    "missing_component_proposal_refs",
    "cross_component_recovery_request_refs",
    "synthesis_proposal_refs",
    "component_refs_supporting_synthesis",
    "evidence_refs_to_revisit",
    "source_refs_to_revisit",
    "required_caveat_refs",
    "nonclaim_refs",
    "dprime_synthesis_dossier_refs",
    "closed_downstream_flags",
    "raw_private_retention_flags",
    "nonclaims",
)

_GRAPH_FUTURE_REF_FIELDS = frozenset(
    {
        "cross_component_analyst_refs",
        "synthesis_proposal_refs",
        "dprime_synthesis_validation_refs",
        "runkernel_synthesis_admission_refs",
    }
)

_FORBIDDEN_PARENT_GRAPH_STATUSES = frozenset(
    {
        GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED,
        GRAPH_STATUS_SYNTHESIS_VALIDATED,
        GRAPH_STATUS_RUNKERNEL_ADMISSION_REQUIRED,
        GRAPH_STATUS_ADMITTED,
        GRAPH_STATUS_CLOSED,
    }
)

_FORBIDDEN_NORMALIZED_KEYS = frozenset(
    {
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
)

_SUMMARY_ONLY_KEYS = frozenset(
    {
        "answer_text",
        "author_answer",
        "author_prose",
        "collapsed_component_summary",
        "combined_answer",
        "combined_answer_summary",
        "component_node_summaries",
        "component_node_summary",
        "component_refs_collapsed",
        "component_summaries",
        "component_summary",
        "cross_component_summary",
        "final_answer",
        "single_combined_answer",
        "single_undifferentiated_component_summary",
        "untraceable_component_summary",
    }
)

_ALLOWED_FALSE_KEYS = frozenset(
    {
        *CROSS_COMPONENT_ANALYST_CLOSED_DOWNSTREAM_FLAGS,
        *CROSS_COMPONENT_ANALYST_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
        *GRAPH_CLOSED_DOWNSTREAM_FLAGS,
        *GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
        "admitted",
        "admitted_support",
        "author_ready",
        "citation_eligible",
        "correct",
        "created_by_component_work_graph",
        "dprime_synthesis_validation_created",
        "dprime_validated",
        "evidence_admitted",
        "fap_ready",
        "graph_future_refs_populated_by_workbench",
        "not_created_by_graph",
        "product_correctness_claimed",
        "proposal_only",
        "runkernel_admitted",
        "runkernel_authorized",
        "source_obligation_satisfied",
        "sufficiency_ready",
        "synthesis_validated",
        "validated",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *CROSS_COMPONENT_ANALYST_CLOSED_DOWNSTREAM_FLAGS,
        *GRAPH_CLOSED_DOWNSTREAM_FLAGS,
        "admitted",
        "admitted_by_runkernel",
        "admitted_support",
        "answer_contract_mutated",
        "answer_created",
        "author_output_created",
        "author_ready",
        "authorized",
        "budget_lease_created",
        "called_provider",
        "called_model",
        "citation_eligible",
        "citation_rendered",
        "component_refs_collapsed",
        "correct",
        "created_author_output",
        "created_fap",
        "created_source_display",
        "direct_retrieval_dispatch",
        "dprime_synthesis_validated",
        "dprime_synthesis_validation_created",
        "dprime_validated",
        "evidence_admitted",
        "fap_created",
        "fap_ready",
        "fetch_read_called",
        "graph_future_refs_populated_by_workbench",
        "model_called",
        "mutated_answer_contract",
        "mutated_parent_graph",
        "parent_graph_mutated",
        "product_correctness_claimed",
        "provider_called",
        "retrieval_called",
        "retrieval_dispatched",
        "runkernel_admission_created",
        "runkernel_admitted",
        "runkernel_authorized",
        "search_authorized",
        "search_dispatched",
        "source_display_created",
        "source_obligation_satisfied",
        "sufficiency_ready",
        "support_admitted",
        "validated_synthesis",
        "synthesis_validated",
        "validated",
    }
)

_STATUS_KEYS = frozenset(
    {
        "admission_status",
        "analysis_status",
        "dprime_validation_status",
        "readiness_status",
        "runkernel_admission_status",
        "status",
        "support_status",
        "validation_status",
    }
)

_DANGEROUS_STATUS_VALUES = frozenset(
    {
        "admitted",
        "author_ready",
        "citation_eligible",
        "correct",
        "dprime_validated",
        "fap_ready",
        "passed",
        "product_correct",
        "ready_for_author",
        "ready_for_fap",
        "runkernel_admitted",
        "source_obligation_satisfied",
        "sufficiency_ready",
        "support_admitted",
        "synthesis_validated",
        "validated",
    }
)

_DPRIME_SYNTHESIS_VALIDATION_OUTPUT_KEYS = frozenset(
    {
        "dprime_synthesis_validation_id",
        "dprime_synthesis_validation_digest",
        "dprime_synthesis_validation_ref",
        "dprime_synthesis_validation_refs",
        "synthesis_validation_id",
        "synthesis_validation_digest",
    }
)


class CrossComponentAnalystWorkbenchError(ValueError):
    """Raised when a Workbench artifact crosses proposal-only boundaries."""


def cross_component_analyst_workbench_v0_from_graph(
    *,
    parent_graph_ref: Mapping[str, Any],
    cross_component_analyst_id: str | None = None,
    analysis_status: str = ANALYSIS_STATUS_PROPOSED,
    consistency_matrix_ref: Mapping[str, Any] | None = None,
    constraint_relation_refs: Sequence[Mapping[str, Any]] | None = None,
    stale_or_overbroad_component_refs: Sequence[Mapping[str, Any]] | None = None,
    contradiction_refs: Sequence[Mapping[str, Any]] | None = None,
    unresolved_dependency_refs: Sequence[Mapping[str, Any]] | None = None,
    missing_component_proposal_refs: Sequence[Mapping[str, Any]] | None = None,
    cross_component_recovery_request_refs: Sequence[Mapping[str, Any]] | None = None,
    synthesis_proposal_refs: Sequence[Mapping[str, Any]] | None = None,
    component_refs_supporting_synthesis: Sequence[Mapping[str, Any]] | None = None,
    evidence_refs_to_revisit: Sequence[Mapping[str, Any]] | None = None,
    source_refs_to_revisit: Sequence[Mapping[str, Any]] | None = None,
    required_caveat_refs: Sequence[Mapping[str, Any]] | None = None,
    nonclaim_refs: Sequence[Mapping[str, Any]] | None = None,
    dprime_synthesis_dossier_refs: Sequence[Mapping[str, Any]] | None = None,
    nonclaims: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Build a separate proposal artifact from an existing graph manifest.

    The builder consumes only typed graph/node refs and caller-supplied proposal
    refs. It does not inspect raw evidence, call runtime/model/search/provider
    surfaces, validate synthesis, admit support, or mutate the parent graph.
    """

    graph = validate_component_work_graph_v0(parent_graph_ref)
    _validate_parent_graph_input(graph)
    nodes = [dict(item) for item in graph["component_node_refs"]]
    edges = [dict(item) for item in graph.get("dependency_edges", [])]
    seed_payload = {
        "phase": CROSS_COMPONENT_ANALYST_WORKBENCH_V0_PHASE,
        "parent_graph_digest": graph.get("graph_digest"),
        "analysis_status": analysis_status,
        "consistency_matrix_ref": consistency_matrix_ref or {},
        "constraint_relation_refs": list(constraint_relation_refs or []),
        "stale_or_overbroad_component_refs": list(
            stale_or_overbroad_component_refs or []
        ),
        "contradiction_refs": list(contradiction_refs or []),
        "unresolved_dependency_refs": list(unresolved_dependency_refs or []),
        "missing_component_proposal_refs": list(
            missing_component_proposal_refs or []
        ),
        "cross_component_recovery_request_refs": list(
            cross_component_recovery_request_refs or []
        ),
        "synthesis_proposal_refs": list(synthesis_proposal_refs or []),
        "dprime_synthesis_dossier_refs": list(dprime_synthesis_dossier_refs or []),
    }
    seed_digest = _digest_json(seed_payload)
    artifact = {
        "schema_version": CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION,
        "phase": CROSS_COMPONENT_ANALYST_WORKBENCH_V0_PHASE,
        "runtime_consumer": CROSS_COMPONENT_ANALYST_WORKBENCH_V0_RUNTIME_CONSUMER,
        "cross_component_analyst_id": (
            _clean_text(cross_component_analyst_id, limit=260)
            or f"cross-component-analyst-workbench:v0:{seed_digest[:20]}"
        ),
        "cross_component_analyst_digest": None,
        "parent_run_id": graph["parent_run_id"],
        "parent_graph_ref": _compact_parent_graph_ref(graph),
        "component_node_refs": nodes,
        "component_node_count": len(nodes),
        "dependency_edge_refs": edges,
        "input_graph_status": graph["graph_status"],
        "analysis_status": _required_analysis_status(analysis_status),
        "consistency_matrix_ref": dict(consistency_matrix_ref or {}),
        "constraint_relation_refs": list(constraint_relation_refs or []),
        "stale_or_overbroad_component_refs": list(
            stale_or_overbroad_component_refs or []
        ),
        "contradiction_refs": list(contradiction_refs or []),
        "unresolved_dependency_refs": list(unresolved_dependency_refs or []),
        "missing_component_proposal_refs": list(
            missing_component_proposal_refs or []
        ),
        "cross_component_recovery_request_refs": list(
            cross_component_recovery_request_refs or []
        ),
        "synthesis_proposal_refs": list(synthesis_proposal_refs or []),
        "component_refs_supporting_synthesis": list(
            component_refs_supporting_synthesis or []
        ),
        "evidence_refs_to_revisit": list(evidence_refs_to_revisit or []),
        "source_refs_to_revisit": list(source_refs_to_revisit or []),
        "required_caveat_refs": list(required_caveat_refs or []),
        "nonclaim_refs": list(nonclaim_refs or []),
        "dprime_synthesis_dossier_refs": list(dprime_synthesis_dossier_refs or []),
        "closed_downstream_flags": dict(
            CROSS_COMPONENT_ANALYST_CLOSED_DOWNSTREAM_FLAGS
        ),
        "raw_private_retention_flags": dict(
            CROSS_COMPONENT_ANALYST_RAW_PRIVATE_RETENTION_FALSE_FLAGS
        ),
        "nonclaims": _nonclaims(nonclaims),
        "parent_graph_mutated": False,
        "graph_future_refs_populated_by_workbench": False,
        **CROSS_COMPONENT_ANALYST_CLOSED_DOWNSTREAM_FLAGS,
    }
    return validate_cross_component_analyst_workbench_v0(artifact)


def validate_cross_component_analyst_workbench_v0(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and normalize a Cross-Component Analyst Workbench V0 artifact."""

    artifact = _safe_mapping(value)
    for key in _REQUIRED_TOP_LEVEL_FIELDS:
        if key not in artifact:
            raise CrossComponentAnalystWorkbenchError(
                f"Cross-Component Analyst Workbench requires {key}"
            )
    _reject_forbidden_material(
        artifact,
        context="Cross-Component Analyst Workbench V0",
    )
    _reject_dprime_synthesis_validation_output(artifact)
    if artifact.get("schema_version") != (
        CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION
    ):
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench schema mismatch"
        )
    if artifact.get("phase") != CROSS_COMPONENT_ANALYST_WORKBENCH_V0_PHASE:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench phase mismatch"
        )
    analyst_id = _required_text(
        artifact.get("cross_component_analyst_id"),
        "cross_component_analyst_id",
    )
    parent_graph_ref = _validate_parent_graph_ref(artifact.get("parent_graph_ref"))
    parent_run_id = _required_text(artifact.get("parent_run_id"), "parent_run_id")
    if parent_run_id != parent_graph_ref["parent_run_id"]:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench parent run mismatch"
        )
    input_graph_status = _required_text(
        artifact.get("input_graph_status"),
        "input_graph_status",
    )
    if input_graph_status != parent_graph_ref["graph_status"]:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench input graph status mismatch"
        )
    analysis_status = _required_analysis_status(artifact.get("analysis_status"))
    component_node_refs = _validate_component_node_refs(
        artifact.get("component_node_refs")
    )
    component_node_count = _bounded_int(
        artifact.get("component_node_count"),
        default=-1,
    )
    if component_node_count != len(component_node_refs):
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench component count must match node refs"
        )
    if component_node_count != parent_graph_ref["component_node_count"]:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench parent graph component count mismatch"
        )
    node_index = _component_node_index(component_node_refs)
    edge_refs = _validate_dependency_edge_refs(
        artifact.get("dependency_edge_refs"),
        node_index=node_index,
    )
    edge_index = _dependency_edge_index(edge_refs)
    consistency_matrix_ref = _proposal_ref_mapping(
        artifact.get("consistency_matrix_ref"),
        field_name="consistency_matrix_ref",
        node_index=node_index,
        edge_index=edge_index,
    )
    constraint_relation_refs = _proposal_ref_list(
        artifact.get("constraint_relation_refs"),
        field_name="constraint_relation_refs",
        node_index=node_index,
        edge_index=edge_index,
    )
    stale_or_overbroad_component_refs = _proposal_ref_list(
        artifact.get("stale_or_overbroad_component_refs"),
        field_name="stale_or_overbroad_component_refs",
        node_index=node_index,
        edge_index=edge_index,
    )
    contradiction_refs = _proposal_ref_list(
        artifact.get("contradiction_refs"),
        field_name="contradiction_refs",
        node_index=node_index,
        edge_index=edge_index,
    )
    unresolved_dependency_refs = _proposal_ref_list(
        artifact.get("unresolved_dependency_refs"),
        field_name="unresolved_dependency_refs",
        node_index=node_index,
        edge_index=edge_index,
    )
    missing_component_proposal_refs = _proposal_ref_list(
        artifact.get("missing_component_proposal_refs"),
        field_name="missing_component_proposal_refs",
        node_index=node_index,
        edge_index=edge_index,
        require_missing_component_id=True,
    )
    recovery_request_refs = _proposal_ref_list(
        artifact.get("cross_component_recovery_request_refs"),
        field_name="cross_component_recovery_request_refs",
        node_index=node_index,
        edge_index=edge_index,
        reject_recovery_authorization=True,
    )
    synthesis_proposal_refs = _synthesis_proposal_refs(
        artifact.get("synthesis_proposal_refs"),
        node_index=node_index,
        edge_index=edge_index,
    )
    component_refs_supporting_synthesis = _component_ref_list(
        artifact.get("component_refs_supporting_synthesis"),
        node_index=node_index,
        field_name="component_refs_supporting_synthesis",
    )
    if synthesis_proposal_refs and not component_refs_supporting_synthesis:
        component_refs_supporting_synthesis = _dedupe_component_refs(
            _component_refs_in_value(synthesis_proposal_refs)
        )
    _validate_synthesis_status(
        analysis_status,
        synthesis_proposal_refs=synthesis_proposal_refs,
        component_refs_supporting_synthesis=component_refs_supporting_synthesis,
        missing_component_proposal_refs=missing_component_proposal_refs,
        recovery_request_refs=recovery_request_refs,
        contradiction_refs=contradiction_refs,
        unresolved_dependency_refs=unresolved_dependency_refs,
    )
    evidence_refs_to_revisit = _proposal_ref_list(
        artifact.get("evidence_refs_to_revisit"),
        field_name="evidence_refs_to_revisit",
        node_index=node_index,
        edge_index=edge_index,
    )
    source_refs_to_revisit = _proposal_ref_list(
        artifact.get("source_refs_to_revisit"),
        field_name="source_refs_to_revisit",
        node_index=node_index,
        edge_index=edge_index,
    )
    required_caveat_refs = _proposal_ref_list(
        artifact.get("required_caveat_refs"),
        field_name="required_caveat_refs",
        node_index=node_index,
        edge_index=edge_index,
    )
    nonclaim_refs = _proposal_ref_list(
        artifact.get("nonclaim_refs"),
        field_name="nonclaim_refs",
        node_index=node_index,
        edge_index=edge_index,
    )
    dprime_synthesis_dossier_refs = _proposal_ref_list(
        artifact.get("dprime_synthesis_dossier_refs"),
        field_name="dprime_synthesis_dossier_refs",
        node_index=node_index,
        edge_index=edge_index,
        reject_dprime_validation_output=True,
    )
    closed_flags = _validate_closed_downstream_flags(artifact)
    raw_flags = _validate_raw_private_flags(artifact)
    normalized = {
        **_json_safe(artifact),
        "cross_component_analyst_id": analyst_id,
        "parent_run_id": parent_run_id,
        "parent_graph_ref": parent_graph_ref,
        "component_node_refs": component_node_refs,
        "component_node_count": component_node_count,
        "dependency_edge_refs": edge_refs,
        "input_graph_status": input_graph_status,
        "analysis_status": analysis_status,
        "consistency_matrix_ref": consistency_matrix_ref,
        "constraint_relation_refs": constraint_relation_refs,
        "stale_or_overbroad_component_refs": stale_or_overbroad_component_refs,
        "contradiction_refs": contradiction_refs,
        "unresolved_dependency_refs": unresolved_dependency_refs,
        "missing_component_proposal_refs": missing_component_proposal_refs,
        "cross_component_recovery_request_refs": recovery_request_refs,
        "synthesis_proposal_refs": synthesis_proposal_refs,
        "component_refs_supporting_synthesis": component_refs_supporting_synthesis,
        "evidence_refs_to_revisit": evidence_refs_to_revisit,
        "source_refs_to_revisit": source_refs_to_revisit,
        "required_caveat_refs": required_caveat_refs,
        "nonclaim_refs": nonclaim_refs,
        "dprime_synthesis_dossier_refs": dprime_synthesis_dossier_refs,
        "closed_downstream_flags": closed_flags,
        "raw_private_retention_flags": raw_flags,
        "nonclaims": _nonclaims(artifact.get("nonclaims")),
        "parent_graph_mutated": False,
        "graph_future_refs_populated_by_workbench": False,
        **closed_flags,
    }
    declared = _clean_text(
        artifact.get("cross_component_analyst_digest"),
        limit=128,
    )
    digest = _digest_json(_without_workbench_digest(normalized))
    if declared and declared != digest:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench digest mismatch"
        )
    normalized["cross_component_analyst_digest"] = digest
    _reject_forbidden_material(
        normalized,
        context="Cross-Component Analyst Workbench V0",
    )
    return normalized


def cross_component_analyst_workbench_v0_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the safe external ref for graph/future synthesis consumers."""

    artifact = validate_cross_component_analyst_workbench_v0(value)
    return {
        "schema_version": artifact["schema_version"],
        "phase": artifact["phase"],
        "cross_component_analyst_id": artifact["cross_component_analyst_id"],
        "cross_component_analyst_digest": artifact[
            "cross_component_analyst_digest"
        ],
        "parent_graph_ref": artifact["parent_graph_ref"],
        "analysis_status": artifact["analysis_status"],
        "proposal_only": True,
        "externally_supplied": True,
        "not_created_by_graph": True,
        "created_by_component_work_graph": False,
        "validated_synthesis": False,
        "runkernel_admitted": False,
        "product_correctness_claimed": False,
    }


def _validate_parent_graph_input(graph: Mapping[str, Any]) -> None:
    status = _clean_text(graph.get("graph_status"), limit=120)
    if status in _FORBIDDEN_PARENT_GRAPH_STATUSES:
        raise CrossComponentAnalystWorkbenchError(
            "parent ComponentWorkGraph status is downstream of proposal-only analysis"
        )
    for field_name in _GRAPH_FUTURE_REF_FIELDS:
        if _safe_sequence(graph.get(field_name)):
            raise CrossComponentAnalystWorkbenchError(
                "parent ComponentWorkGraph already carries future analysis or authority refs"
            )
    _reject_forbidden_material(
        graph,
        context="Cross-Component Analyst Workbench parent graph input",
    )


def _compact_parent_graph_ref(graph: Mapping[str, Any]) -> dict[str, Any]:
    ref = {
        "schema_version": COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
        "phase": COMPONENT_WORK_GRAPH_V0_PHASE,
        "graph_id": graph.get("graph_id"),
        "graph_digest": graph.get("graph_digest"),
        "parent_run_id": graph.get("parent_run_id"),
        "graph_status": graph.get("graph_status"),
        "component_node_count": _bounded_int(graph.get("component_node_count")),
        "dependency_edge_count": len(_safe_sequence(graph.get("dependency_edges"))),
        "closed_downstream_flags": dict(GRAPH_CLOSED_DOWNSTREAM_FLAGS),
        "raw_private_retention_flags": dict(GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS),
        "parent_graph_ref_only": True,
        "graph_future_refs_populated_by_workbench": False,
        **GRAPH_CLOSED_DOWNSTREAM_FLAGS,
    }
    return _validate_parent_graph_ref(ref)


def _validate_parent_graph_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if not ref:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench requires parent_graph_ref"
        )
    _reject_forbidden_material(ref, context="parent_graph_ref")
    if ref.get("schema_version") != COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION:
        raise CrossComponentAnalystWorkbenchError(
            "parent_graph_ref must be ComponentWorkGraph V0"
        )
    if ref.get("phase") != COMPONENT_WORK_GRAPH_V0_PHASE:
        raise CrossComponentAnalystWorkbenchError(
            "parent_graph_ref phase mismatch"
        )
    graph_id = _required_text(ref.get("graph_id"), "parent_graph_ref.graph_id")
    graph_digest = _required_text(
        ref.get("graph_digest"),
        "parent_graph_ref.graph_digest",
    )
    parent_run_id = _required_text(
        ref.get("parent_run_id"),
        "parent_graph_ref.parent_run_id",
    )
    graph_status = _required_text(
        ref.get("graph_status"),
        "parent_graph_ref.graph_status",
    )
    if graph_status in _FORBIDDEN_PARENT_GRAPH_STATUSES:
        raise CrossComponentAnalystWorkbenchError(
            "parent_graph_ref carries validation/admission graph status"
        )
    for field_name in _GRAPH_FUTURE_REF_FIELDS:
        if _safe_sequence(ref.get(field_name)):
            raise CrossComponentAnalystWorkbenchError(
                "parent_graph_ref must not populate graph future refs"
            )
    component_node_count = _bounded_int(
        ref.get("component_node_count"),
        default=-1,
    )
    if component_node_count < 1:
        raise CrossComponentAnalystWorkbenchError(
            "parent_graph_ref requires component_node_count"
        )
    closed_flags = _validate_graph_closed_flags(ref)
    raw_flags = _validate_graph_raw_flags(ref)
    return {
        **_json_safe(ref),
        "schema_version": COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
        "phase": COMPONENT_WORK_GRAPH_V0_PHASE,
        "graph_id": graph_id,
        "graph_digest": graph_digest,
        "parent_run_id": parent_run_id,
        "graph_status": graph_status,
        "component_node_count": component_node_count,
        "dependency_edge_count": _bounded_int(ref.get("dependency_edge_count")),
        "closed_downstream_flags": closed_flags,
        "raw_private_retention_flags": raw_flags,
        "parent_graph_ref_only": ref.get("parent_graph_ref_only") is True,
        "graph_future_refs_populated_by_workbench": False,
        **closed_flags,
    }


def _validate_component_node_refs(value: Any) -> list[dict[str, Any]]:
    refs = _safe_sequence(value)
    if not refs:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench requires component_node_refs"
        )
    out: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_components: set[str] = set()
    for item in refs:
        ref = _validate_component_ref(item, node_index=None)
        node_id = ref["node_id"]
        component_id = ref["component_id"]
        if node_id in seen_nodes:
            raise CrossComponentAnalystWorkbenchError(
                "Cross-Component Analyst Workbench duplicate component node id"
            )
        if component_id in seen_components:
            raise CrossComponentAnalystWorkbenchError(
                "Cross-Component Analyst Workbench duplicate component id"
            )
        seen_nodes.add(node_id)
        seen_components.add(component_id)
        out.append(ref)
    return out


def _validate_component_ref(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if not ref:
        raise CrossComponentAnalystWorkbenchError("component node ref malformed")
    _reject_forbidden_material(ref, context="component node ref")
    if ref.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
        raise CrossComponentAnalystWorkbenchError(
            "component refs must be typed ComponentWorkNode V0 refs"
        )
    node_id = _required_text(ref.get("node_id"), "component node_id")
    component_id = _required_text(ref.get("component_id"), "component_id")
    component_ids = _text_tuple(ref.get("component_ids"), limit=320)
    if component_ids and (len(component_ids) != 1 or component_ids[0] != component_id):
        raise CrossComponentAnalystWorkbenchError(
            "component refs must preserve one component id"
        )
    if node_index is not None:
        known = _safe_mapping(node_index.get(node_id))
        if known and known.get("component_id") != component_id:
            raise CrossComponentAnalystWorkbenchError(
                "component ref uses a known node_id with the wrong component_id"
            )
        if not known:
            known_for_component = [
                dict(item)
                for item in node_index.values()
                if _safe_mapping(item).get("component_id") == component_id
            ]
            if known_for_component:
                raise CrossComponentAnalystWorkbenchError(
                    "component ref uses a known component_id with the wrong node_id"
                )
            raise CrossComponentAnalystWorkbenchError(
                "proposal ref references unknown component node"
            )
    normalized = {
        **_json_safe(ref),
        "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
        "node_id": node_id,
        "component_id": component_id,
        "component_ids": [component_id],
    }
    return normalized


def _validate_dependency_edge_refs(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _safe_sequence(value):
        edge = _validate_dependency_edge_ref(item, node_index=node_index)
        edge_id = edge["edge_id"]
        if edge_id in seen:
            raise CrossComponentAnalystWorkbenchError(
                "Cross-Component Analyst Workbench duplicate dependency edge id"
            )
        seen.add(edge_id)
        out.append(edge)
    return out


def _validate_dependency_edge_ref(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    edge = _safe_mapping(value)
    if not edge:
        raise CrossComponentAnalystWorkbenchError("dependency edge ref malformed")
    _reject_forbidden_material(edge, context="dependency edge ref")
    if edge.get("schema_version") != COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION:
        raise CrossComponentAnalystWorkbenchError(
            "dependency edge refs must be typed ComponentWorkGraph V0 refs"
        )
    edge_id = _required_text(edge.get("edge_id"), "edge_id")
    edge_digest = _clean_text(edge.get("edge_digest"), limit=128)
    from_ref = _validate_component_ref(
        edge.get("from_component_node_ref"),
        node_index=node_index,
    )
    to_ref = _validate_component_ref(
        edge.get("to_component_node_ref"),
        node_index=node_index,
    )
    if from_ref["node_id"] == to_ref["node_id"]:
        raise CrossComponentAnalystWorkbenchError(
            "dependency edge cannot self-depend"
        )
    return _without_empty(
        {
            **_json_safe(edge),
            "schema_version": COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
            "edge_id": edge_id,
            "edge_digest": edge_digest,
            "from_component_node_ref": _component_ref_identity(from_ref),
            "to_component_node_ref": _component_ref_identity(to_ref),
        }
    )


def _proposal_ref_mapping(
    value: Any,
    *,
    field_name: str,
    node_index: Mapping[str, Mapping[str, Any]],
    edge_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if not ref:
        return {}
    return _validate_proposal_ref(
        ref,
        field_name=field_name,
        node_index=node_index,
        edge_index=edge_index,
    )


def _proposal_ref_list(
    value: Any,
    *,
    field_name: str,
    node_index: Mapping[str, Mapping[str, Any]],
    edge_index: Mapping[str, Mapping[str, Any]],
    require_missing_component_id: bool = False,
    reject_recovery_authorization: bool = False,
    reject_dprime_validation_output: bool = False,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        refs.append(
            _validate_proposal_ref(
                ref,
                field_name=field_name,
                node_index=node_index,
                edge_index=edge_index,
                require_missing_component_id=require_missing_component_id,
                reject_recovery_authorization=reject_recovery_authorization,
                reject_dprime_validation_output=reject_dprime_validation_output,
            )
        )
    return refs


def _validate_proposal_ref(
    value: Mapping[str, Any],
    *,
    field_name: str,
    node_index: Mapping[str, Mapping[str, Any]],
    edge_index: Mapping[str, Mapping[str, Any]],
    require_missing_component_id: bool = False,
    reject_recovery_authorization: bool = False,
    reject_dprime_validation_output: bool = False,
) -> dict[str, Any]:
    ref = _safe_mapping(value)
    _reject_forbidden_material(ref, context=field_name)
    _reject_untyped_or_bare_component_refs(ref, context=field_name)
    if ref.get("proposal_only") is False:
        raise CrossComponentAnalystWorkbenchError(
            f"{field_name} must remain proposal-only"
        )
    if require_missing_component_id and not _clean_text(
        ref.get("missing_component_id"),
        limit=320,
    ):
        raise CrossComponentAnalystWorkbenchError(
            "missing-component proposal refs require missing_component_id"
        )
    if reject_recovery_authorization:
        _reject_recovery_authorization_claims(ref)
    if reject_dprime_validation_output:
        _reject_dprime_synthesis_validation_output(ref)
    component_refs = [
        _validate_component_ref(item, node_index=node_index)
        for item in _component_refs_in_value(ref)
    ]
    dependency_refs = [
        _validate_known_dependency_ref(item, edge_index=edge_index)
        for item in _dependency_refs_in_value(ref)
    ]
    if not component_refs and not dependency_refs:
        raise CrossComponentAnalystWorkbenchError(
            f"{field_name} must be traceable to component or dependency refs"
        )
    return {
        **_json_safe(ref),
        "proposal_only": True,
    }


def _synthesis_proposal_refs(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]],
    edge_index: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        normalized = _validate_proposal_ref(
            ref,
            field_name="synthesis_proposal_refs",
            node_index=node_index,
            edge_index=edge_index,
        )
        if not any(
            _clean_text(normalized.get(key), limit=320)
            for key in ("synthesis_proposal_id", "proposal_id", "ref_id")
        ):
            raise CrossComponentAnalystWorkbenchError(
                "synthesis proposal refs require a proposal id"
            )
        component_refs = [
            _validate_component_ref(item, node_index=node_index)
            for item in _component_refs_in_value(normalized)
        ]
        distinct = {
            (item["node_id"], item["component_id"])
            for item in component_refs
        }
        if len(distinct) < 2:
            raise CrossComponentAnalystWorkbenchError(
                "synthesis proposal refs require at least two distinct component node refs"
            )
        refs.append(normalized)
    return refs


def _component_ref_list(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]],
    field_name: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in _safe_sequence(value):
        ref = _validate_component_ref(item, node_index=node_index)
        key = (ref["node_id"], ref["component_id"])
        if key in seen:
            continue
        seen.add(key)
        refs.append(_component_ref_identity(ref))
    for ref in refs:
        _reject_forbidden_material(ref, context=field_name)
    return refs


def _validate_known_dependency_ref(
    value: Mapping[str, Any],
    *,
    edge_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    ref = _safe_mapping(value)
    edge_id = _required_text(ref.get("edge_id"), "dependency edge_id")
    known = _safe_mapping(edge_index.get(edge_id))
    if not known:
        raise CrossComponentAnalystWorkbenchError(
            "proposal ref references unknown dependency edge"
        )
    edge_digest = _clean_text(ref.get("edge_digest"), limit=128)
    if edge_digest and known.get("edge_digest") and edge_digest != known.get(
        "edge_digest"
    ):
        raise CrossComponentAnalystWorkbenchError(
            "proposal ref dependency edge digest mismatch"
        )
    return _without_empty(
        {
            "schema_version": COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
            "edge_id": edge_id,
            "edge_digest": edge_digest or known.get("edge_digest"),
        }
    )


def _validate_synthesis_status(
    analysis_status: str,
    *,
    synthesis_proposal_refs: Sequence[Mapping[str, Any]],
    component_refs_supporting_synthesis: Sequence[Mapping[str, Any]],
    missing_component_proposal_refs: Sequence[Mapping[str, Any]],
    recovery_request_refs: Sequence[Mapping[str, Any]],
    contradiction_refs: Sequence[Mapping[str, Any]],
    unresolved_dependency_refs: Sequence[Mapping[str, Any]],
) -> None:
    if synthesis_proposal_refs:
        distinct = {
            (ref.get("node_id"), ref.get("component_id"))
            for ref in component_refs_supporting_synthesis
        }
        if len(distinct) < 2:
            raise CrossComponentAnalystWorkbenchError(
                "synthesis proposals require top-level supporting component refs"
            )
    if analysis_status == ANALYSIS_STATUS_SYNTHESIS_PROPOSED and not (
        synthesis_proposal_refs
    ):
        raise CrossComponentAnalystWorkbenchError(
            "synthesis_proposed status requires synthesis proposal refs"
        )
    if analysis_status == ANALYSIS_STATUS_RECOVERY_PROPOSED and not (
        recovery_request_refs
    ):
        raise CrossComponentAnalystWorkbenchError(
            "recovery_proposed status requires recovery proposal refs"
        )
    if analysis_status == ANALYSIS_STATUS_BLOCKED_MISSING_COMPONENT and not (
        missing_component_proposal_refs
    ):
        raise CrossComponentAnalystWorkbenchError(
            "blocked_missing_component status requires missing-component refs"
        )
    if analysis_status == ANALYSIS_STATUS_BLOCKED_DEPENDENCY and not (
        unresolved_dependency_refs
    ):
        raise CrossComponentAnalystWorkbenchError(
            "blocked_dependency status requires unresolved dependency refs"
        )
    if analysis_status == ANALYSIS_STATUS_BLOCKED_CONTRADICTION and not (
        contradiction_refs
    ):
        raise CrossComponentAnalystWorkbenchError(
            "blocked_contradiction status requires contradiction refs"
        )
    if analysis_status == ANALYSIS_STATUS_NO_SYNTHESIS_PROPOSED and (
        synthesis_proposal_refs or component_refs_supporting_synthesis
    ):
        raise CrossComponentAnalystWorkbenchError(
            "no_synthesis_proposed status cannot carry synthesis refs"
        )


def _component_refs_in_value(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _walk_mappings(value):
        if (
            item.get("schema_version") == COMPONENT_WORK_NODE_V0_SCHEMA_VERSION
            and _clean_text(item.get("node_id"), limit=320)
            and _clean_text(item.get("component_id"), limit=320)
        ):
            refs.append(dict(item))
    return refs


def _dependency_refs_in_value(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _walk_mappings(value):
        if (
            item.get("schema_version") == COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION
            and _clean_text(item.get("edge_id"), limit=320)
        ):
            refs.append(dict(item))
    return refs


def _walk_mappings(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        out.append(dict(value))
        for item in value.values():
            out.extend(_walk_mappings(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            out.extend(_walk_mappings(item))
    return out


def _reject_untyped_or_bare_component_refs(value: Any, *, context: str) -> None:
    for item in _walk_mappings(value):
        has_node_id = _clean_text(item.get("node_id"), limit=320)
        has_component_id = _clean_text(item.get("component_id"), limit=320)
        if has_node_id and has_component_id and item.get(
            "schema_version"
        ) != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
            raise CrossComponentAnalystWorkbenchError(
                f"{context} component refs must be typed ComponentWorkNode refs"
            )
        if has_component_id and not has_node_id:
            raise CrossComponentAnalystWorkbenchError(
                f"{context} must reference component refs by node_id and component_id"
            )


def _reject_recovery_authorization_claims(value: Any) -> None:
    for item in _walk_mappings(value):
        for key, raw in item.items():
            normalized_key = _normalize_key(key)
            normalized_value = _normalize_key(raw)
            if normalized_key in {
                "authorization_status",
                "runkernel_authorization_status",
                "search_authorization_status",
            } and normalized_value in {"authorized", "admitted", "approved"}:
                raise CrossComponentAnalystWorkbenchError(
                    "recovery request refs must not claim RunKernel authorization"
                )


def _reject_dprime_synthesis_validation_output(value: Any) -> None:
    keys = _collect_keys(value)
    invalid = sorted(keys & _DPRIME_SYNTHESIS_VALIDATION_OUTPUT_KEYS)
    if invalid:
        raise CrossComponentAnalystWorkbenchError(
            "D-prime synthesis dossier refs must not be validation outputs: "
            + ", ".join(invalid)
        )
    for item in _walk_mappings(value):
        for key in ("schema_version", "ref_kind", "kind", "status"):
            text = _normalize_key(item.get(key))
            if text in {
                "dprime_synthesis_validation",
                "dprime_synthesis_validation_ref_v0",
                "synthesis_validation_output",
            }:
                raise CrossComponentAnalystWorkbenchError(
                    "D-prime synthesis dossier refs must be future validation inputs"
                )


def _validate_closed_downstream_flags(artifact: Mapping[str, Any]) -> dict[str, bool]:
    closed = _safe_mapping(artifact.get("closed_downstream_flags"))
    if not closed:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench missing closed downstream flags"
        )
    normalized: dict[str, bool] = {}
    for key in CROSS_COMPONENT_ANALYST_CLOSED_DOWNSTREAM_FLAGS:
        if closed.get(key) is not False:
            raise CrossComponentAnalystWorkbenchError(
                f"Cross-Component Analyst Workbench closed flag must remain false: {key}"
            )
        if artifact.get(key) is not False:
            raise CrossComponentAnalystWorkbenchError(
                f"Cross-Component Analyst Workbench top-level flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_raw_private_flags(artifact: Mapping[str, Any]) -> dict[str, bool]:
    flags = _safe_mapping(artifact.get("raw_private_retention_flags"))
    if not flags:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench missing raw/private flags"
        )
    normalized: dict[str, bool] = {}
    for key in CROSS_COMPONENT_ANALYST_RAW_PRIVATE_RETENTION_FALSE_FLAGS:
        if flags.get(key) is not False:
            raise CrossComponentAnalystWorkbenchError(
                f"Cross-Component Analyst Workbench raw/private flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_graph_closed_flags(ref: Mapping[str, Any]) -> dict[str, bool]:
    closed = _safe_mapping(ref.get("closed_downstream_flags"))
    if not closed:
        raise CrossComponentAnalystWorkbenchError(
            "parent_graph_ref missing closed downstream flags"
        )
    normalized: dict[str, bool] = {}
    for key in GRAPH_CLOSED_DOWNSTREAM_FLAGS:
        if closed.get(key) is not False or ref.get(key) is not False:
            raise CrossComponentAnalystWorkbenchError(
                f"parent_graph_ref downstream flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_graph_raw_flags(ref: Mapping[str, Any]) -> dict[str, bool]:
    flags = _safe_mapping(ref.get("raw_private_retention_flags"))
    if not flags:
        raise CrossComponentAnalystWorkbenchError(
            "parent_graph_ref missing raw/private flags"
        )
    normalized: dict[str, bool] = {}
    for key in GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS:
        if flags.get(key) is not False:
            raise CrossComponentAnalystWorkbenchError(
                f"parent_graph_ref raw/private flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    summary = sorted(keys & _SUMMARY_ONLY_KEYS)
    if summary:
        raise CrossComponentAnalystWorkbenchError(
            f"{context} collapses component refs into summary-only keys: "
            + ", ".join(summary)
        )
    forbidden = sorted(keys & _FORBIDDEN_NORMALIZED_KEYS)
    if forbidden:
        raise CrossComponentAnalystWorkbenchError(
            f"{context} includes forbidden raw/private material: "
            + ", ".join(forbidden)
        )
    invalid_false_flags = sorted(_invalid_false_flags(value))
    if invalid_false_flags:
        raise CrossComponentAnalystWorkbenchError(
            f"{context} raw/private or closed flags must be explicitly false: "
            + ", ".join(invalid_false_flags)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise CrossComponentAnalystWorkbenchError(
            f"{context} attempts forbidden authority upgrade: "
            + ", ".join(dangerous)
        )
    dangerous_statuses = sorted(_dangerous_status_claims(value))
    if dangerous_statuses:
        raise CrossComponentAnalystWorkbenchError(
            f"{context} carries forbidden status claims: "
            + ", ".join(dangerous_statuses)
        )


def _invalid_false_flags(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _ALLOWED_FALSE_KEYS and item not in (False, True):
                found.add(normalized)
            if normalized in _ALLOWED_FALSE_KEYS and item is True:
                continue
            if (
                (
                    normalized.endswith("_retained")
                    or normalized.endswith("_called")
                    or normalized.endswith("_dispatched")
                    or normalized.endswith("_executed")
                )
                and item is not False
            ):
                found.add(normalized)
            found.update(_invalid_false_flags(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            found.update(_invalid_false_flags(item))
    return found


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(normalized)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _dangerous_status_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            status_value = _normalize_key(item)
            if (
                normalized in _STATUS_KEYS
                and status_value in _DANGEROUS_STATUS_VALUES
            ):
                found.add(f"{normalized}={status_value}")
            found.update(_dangerous_status_claims(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            found.update(_dangerous_status_claims(item))
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _component_node_index(
    refs: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {str(ref["node_id"]): dict(ref) for ref in refs}


def _dependency_edge_index(
    refs: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {str(ref["edge_id"]): dict(ref) for ref in refs}


def _component_ref_identity(ref: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
        "node_id": ref["node_id"],
        "component_id": ref["component_id"],
    }


def _dedupe_component_refs(refs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        safe = _safe_mapping(ref)
        node_id = _clean_text(safe.get("node_id"), limit=320)
        component_id = _clean_text(safe.get("component_id"), limit=320)
        if not node_id or not component_id:
            continue
        key = (node_id, component_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
                "node_id": node_id,
                "component_id": component_id,
            }
        )
    return out


def _required_analysis_status(value: Any) -> str:
    status = _clean_text(value, limit=120)
    if status not in ALLOWED_ANALYSIS_STATUSES:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench analysis status invalid"
        )
    return status


def _required_text(value: Any, key: str) -> str:
    text = _clean_text(value, limit=900)
    if not text:
        raise CrossComponentAnalystWorkbenchError(
            f"Cross-Component Analyst Workbench requires {key}"
        )
    return text


def _nonclaims(value: Any) -> list[str]:
    claims = list(
        _text_tuple(
            value if value is not None else CROSS_COMPONENT_ANALYST_NONCLAIMS,
            limit=600,
        )
    )
    if not claims:
        raise CrossComponentAnalystWorkbenchError(
            "Cross-Component Analyst Workbench requires nonclaims"
        )
    return claims


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


def _without_workbench_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key != "cross_component_analyst_digest"
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ALLOWED_ANALYSIS_STATUSES",
    "ANALYSIS_STATUS_BLOCKED_CONTRADICTION",
    "ANALYSIS_STATUS_BLOCKED_DEPENDENCY",
    "ANALYSIS_STATUS_BLOCKED_MISSING_COMPONENT",
    "ANALYSIS_STATUS_DRAFT",
    "ANALYSIS_STATUS_NO_SYNTHESIS_PROPOSED",
    "ANALYSIS_STATUS_PROPOSED",
    "ANALYSIS_STATUS_RECOVERY_PROPOSED",
    "ANALYSIS_STATUS_SYNTHESIS_PROPOSED",
    "CROSS_COMPONENT_ANALYST_CLOSED_DOWNSTREAM_FLAGS",
    "CROSS_COMPONENT_ANALYST_RAW_PRIVATE_RETENTION_FALSE_FLAGS",
    "CROSS_COMPONENT_ANALYST_WORKBENCH_V0_PHASE",
    "CROSS_COMPONENT_ANALYST_WORKBENCH_V0_RUNTIME_CONSUMER",
    "CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION",
    "CrossComponentAnalystWorkbenchError",
    "cross_component_analyst_workbench_v0_from_graph",
    "cross_component_analyst_workbench_v0_ref",
    "validate_cross_component_analyst_workbench_v0",
]
