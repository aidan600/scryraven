"""PRODUCT-PATH-REGRESSION: ComponentWorkGraph V0 no-execution contract.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: future cross-component phase routing over
current ComponentWorkNode refs.
Runtime consumer: future Cross-Component Analyst Workbench /
ComponentWorkGraph phases.
Why ordinary product-path work cannot be done directly: this is a no-execution
contract phase before graph execution and synthesis runtime are licensed.
Integration deadline: CROSS-COMPONENT-SYNTHESIS-PROPOSAL-V0-01 should consume
this contract.
Exit condition: keep until graph contract is superseded by a current
product-consumed graph path.
Why this is not a shadow product path: the graph does not execute, schedule,
retrieve, validate synthesis, admit support, package FAP, render Author prose,
or answer.
Forbidden interpretation: passing tests is not multi-component answering,
scheduling, runtime parallelism, retrieval quality, synthesis validation,
RunKernel admission, FAP, Author, source display, citation rendering, or
product correctness.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from core.component_work_graph import (
    GRAPH_STATUS_SYNTHESIS_VALIDATED,
    GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED,
    ComponentWorkGraphError,
    component_work_graph_v0_from_component_nodes,
    validate_component_work_graph_v0,
)


def test_graph_v0_accepts_two_component_nodes_and_dependency_edge() -> None:
    graph = _graph()

    assert validate_component_work_graph_v0(graph) == graph
    assert graph["schema_version"] == "component_work_graph_v0"
    assert graph["graph_status"] == "proposed"
    assert graph["component_node_count"] == 2
    assert [ref["component_id"] for ref in graph["component_node_refs"]] == [
        "component:fee",
        "component:eligibility",
    ]
    assert len(graph["dependency_edges"]) == 1
    assert graph["graph_executed_nodes"] is False
    assert graph["graph_scheduled_runtime_work"] is False
    assert graph["graph_dispatched_search"] is False
    assert graph["graph_validated_synthesis"] is False
    assert graph["graph_created_runkernel_admission"] is False
    assert graph["graph_created_fap"] is False
    assert graph["graph_created_author_output"] is False
    assert graph["graph_rendered_citations"] is False
    assert graph["graph_claimed_product_correctness"] is False


def test_graph_counts_component_nodes_not_same_component_multi_source_counts() -> None:
    node = _node_ref(
        "component:fee",
        "node:fee",
        relation_count=3,
        source_count=3,
    )

    graph = _graph(component_node_refs=[node], dependency_edges=[])

    assert graph["component_node_count"] == 1
    assert graph["component_node_refs"][0]["multi_source_shape_ref"][
        "relation_count"
    ] == 3
    assert graph["component_node_refs"][0]["multi_source_shape_ref"][
        "source_count"
    ] == 3

    tampered = deepcopy(graph)
    tampered["component_node_count"] = 3
    with pytest.raises(ComponentWorkGraphError):
        validate_component_work_graph_v0(tampered)


def test_graph_preserves_dependency_edge_refs() -> None:
    graph = _graph()
    edge = graph["dependency_edges"][0]

    assert edge["edge_id"] == "edge:eligibility-before-fee"
    assert edge["edge_digest"]
    assert edge["from_component_node_ref"] == _edge_node_ref(
        "node:eligibility",
        "component:eligibility",
    )
    assert edge["to_component_node_ref"] == _edge_node_ref(
        "node:fee",
        "component:fee",
    )
    assert edge["blocking"] is True
    assert edge["admitted_by_runkernel_ref"]["status"] == "not_admitted"
    assert graph["blocking_dependency_refs"][0]["edge_id"] == edge["edge_id"]


def test_graph_carries_recovery_and_missing_component_refs_only() -> None:
    recovery_ref = {
        "schema_version": "cross_component_recovery_request_ref_v0",
        "recovery_request_id": "recovery:official-source-needed",
        "status": "proposed_elsewhere",
        "created_by_component_work_graph": False,
        "graph_dispatched_search": False,
    }
    missing_ref = {
        "schema_version": "missing_component_proposal_ref_v0",
        "missing_component_proposal_id": "missing-component:effective-date",
        "status": "proposed_elsewhere",
        "created_by_component_work_graph": False,
    }

    graph = _graph(
        recovery_request_refs=[recovery_ref],
        missing_component_proposal_refs=[missing_ref],
    )

    assert graph["recovery_request_refs"] == [recovery_ref]
    assert graph["missing_component_proposal_refs"] == [missing_ref]
    assert graph["graph_dispatched_search"] is False
    assert graph["graph_called_retrieval"] is False


def test_builder_does_not_create_future_analysis_or_admission_refs() -> None:
    graph = _graph()

    assert graph["cross_component_analyst_refs"] == []
    assert graph["synthesis_proposal_refs"] == []
    assert graph["dprime_synthesis_validation_refs"] == []
    assert graph["runkernel_synthesis_admission_refs"] == []


def test_external_future_refs_are_labeled_as_not_created_by_graph() -> None:
    graph = _graph(
        cross_component_analyst_refs=[
            _future_ref("cross_component_analyst_ref_v0", "cca:1")
        ],
        synthesis_proposal_refs=[_future_ref("synthesis_proposal_ref_v0", "syn:1")],
        dprime_synthesis_validation_refs=[
            _future_ref("dprime_synthesis_validation_ref_v0", "dprime-syn:1")
        ],
        runkernel_synthesis_admission_refs=[
            _future_ref("runkernel_synthesis_admission_ref_v0", "rk-admit:1")
        ],
    )

    for key in (
        "cross_component_analyst_refs",
        "synthesis_proposal_refs",
        "dprime_synthesis_validation_refs",
        "runkernel_synthesis_admission_refs",
    ):
        ref = graph[key][0]
        assert ref["externally_supplied"] is True
        assert ref["not_created_by_graph"] is True
        assert ref["created_by_component_work_graph"] is False


def test_builder_requires_external_synthesis_refs_for_validation_required_status() -> None:
    with pytest.raises(ComponentWorkGraphError):
        _graph(graph_status=GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED)

    graph = _graph(
        graph_status=GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED,
        synthesis_proposal_refs=[_future_ref("synthesis_proposal_ref_v0", "syn:1")],
    )

    assert graph["graph_status"] == GRAPH_STATUS_SYNTHESIS_VALIDATION_REQUIRED
    assert graph["synthesis_proposal_refs"][0]["externally_supplied"] is True


def test_validator_accepts_future_status_only_with_external_typed_refs() -> None:
    graph = _graph()
    graph["graph_status"] = GRAPH_STATUS_SYNTHESIS_VALIDATED
    graph["graph_digest"] = None
    with pytest.raises(ComponentWorkGraphError):
        validate_component_work_graph_v0(graph)

    graph["dprime_synthesis_validation_refs"] = [
        {
            **_future_ref("dprime_synthesis_validation_ref_v0", "dprime-syn:1"),
            "externally_supplied": True,
            "not_created_by_graph": True,
            "created_by_component_work_graph": False,
        }
    ]
    validated = validate_component_work_graph_v0(graph)

    assert validated["graph_status"] == GRAPH_STATUS_SYNTHESIS_VALIDATED
    assert validated["dprime_synthesis_validation_refs"][0][
        "created_by_component_work_graph"
    ] is False


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("raw_source_text", "full source text"),
        ("raw_provider_payload", {"answer": "payload"}),
        ("headers", {"Authorization": "Bearer private"}),
        ("prompt", "raw prompt"),
        ("local_output_packet", {"path": "output/private.json"}),
    ],
)
def test_graph_rejects_raw_private_material_anywhere(key: str, value: Any) -> None:
    node = _node_ref("component:fee", "node:fee")
    node[key] = value

    with pytest.raises(ComponentWorkGraphError):
        _graph(component_node_refs=[node], dependency_edges=[])


@pytest.mark.parametrize(
    "flag",
    [
        "graph_executed_nodes",
        "graph_scheduled_runtime_work",
        "runtime_parallelism_executed",
    ],
)
def test_graph_rejects_execution_scheduler_and_parallelism_flags(flag: str) -> None:
    graph = _graph()
    graph["closed_downstream_flags"][flag] = True

    with pytest.raises(ComponentWorkGraphError):
        validate_component_work_graph_v0(graph)


def test_graph_rejects_budget_lease_creation() -> None:
    graph = _graph()
    graph["budget_lease_created"] = True

    with pytest.raises(ComponentWorkGraphError):
        validate_component_work_graph_v0(graph)


@pytest.mark.parametrize(
    "flag",
    [
        "graph_dispatched_search",
        "graph_called_provider",
        "graph_called_model",
        "graph_called_fetch_read",
        "graph_called_retrieval",
    ],
)
def test_graph_rejects_direct_dispatch_flags(flag: str) -> None:
    graph = _graph()
    graph[flag] = True

    with pytest.raises(ComponentWorkGraphError):
        validate_component_work_graph_v0(graph)


def test_graph_rejects_synthesis_validation_created_by_graph() -> None:
    graph = _graph(
        dprime_synthesis_validation_refs=[
            _future_ref("dprime_synthesis_validation_ref_v0", "dprime-syn:1")
        ]
    )
    graph["dprime_synthesis_validation_refs"][0][
        "created_by_component_work_graph"
    ] = True
    graph["graph_digest"] = None

    with pytest.raises(ComponentWorkGraphError):
        validate_component_work_graph_v0(graph)


def test_graph_rejects_runkernel_admission_created_by_graph() -> None:
    graph = _graph()
    graph["graph_created_runkernel_admission"] = True

    with pytest.raises(ComponentWorkGraphError):
        validate_component_work_graph_v0(graph)


@pytest.mark.parametrize(
    "flag",
    [
        "graph_created_fap",
        "graph_created_author_output",
        "graph_created_source_display",
        "graph_rendered_citations",
        "graph_claimed_product_correctness",
        "source_obligation_satisfaction_claimed",
        "citation_eligibility_created",
    ],
)
def test_graph_rejects_downstream_rendering_and_correctness_claims(flag: str) -> None:
    graph = _graph()
    graph[flag] = True

    with pytest.raises(ComponentWorkGraphError):
        validate_component_work_graph_v0(graph)


def test_graph_rejects_untraceable_component_summaries() -> None:
    with pytest.raises(ComponentWorkGraphError):
        _graph(
            component_node_refs=[
                {
                    "component_summary": "fee and eligibility were summarized together",
                    "component_node_ref_collapsed_to_summary": True,
                }
            ],
            dependency_edges=[],
        )


def test_dependency_edge_rejects_unknown_component_node() -> None:
    with pytest.raises(ComponentWorkGraphError):
        _graph(
            dependency_edges=[
                _edge(
                    from_node_id="node:unknown",
                    from_component_id="component:unknown",
                )
            ]
        )


def test_dependency_edge_requires_typed_component_node_refs() -> None:
    edge = _edge()
    edge["from_component_node_ref"].pop("schema_version")

    with pytest.raises(ComponentWorkGraphError):
        _graph(dependency_edges=[edge])


def test_graph_rejects_multiple_graph_ids() -> None:
    graph = _graph()
    graph["graph_ids"] = [graph["graph_id"], "component-work-graph:v0:other"]

    with pytest.raises(ComponentWorkGraphError):
        validate_component_work_graph_v0(graph)


def _graph(**overrides: Any) -> dict[str, Any]:
    nodes = overrides.pop(
        "component_node_refs",
        [
            _node_ref("component:fee", "node:fee"),
            _node_ref("component:eligibility", "node:eligibility"),
        ],
    )
    edges = overrides.pop("dependency_edges", [_edge()])
    return component_work_graph_v0_from_component_nodes(
        parent_run_id="run:component-work-graph-test",
        parent_run_ref={
            "run_id": "run:component-work-graph-test",
            "run_digest": "run-digest:component-work-graph-test",
        },
        user_query_ref={
            "query_id": "query:n400-fee-and-eligibility",
            "query_digest": "query-digest:n400-fee-and-eligibility",
        },
        supported_query_class="mvp-current-source-of-record-single-fact-v1",
        answer_contract_ref={
            "answer_contract_id": "contract:n400",
            "answer_contract_digest": "contract-digest:n400",
        },
        component_node_refs=nodes,
        dependency_edges=edges,
        **overrides,
    )


def _node_ref(
    component_id: str,
    node_id: str,
    *,
    relation_count: int = 1,
    source_count: int = 1,
) -> dict[str, Any]:
    return {
        "schema_version": "component_work_node_v0",
        "node_kind": "component_work_node_v0_output",
        "node_id": node_id,
        "parent_run_id": "run:component-work-graph-test",
        "component_id": component_id,
        "component_ids": [component_id],
        "source_obligation_id": f"source-obligation:{component_id}",
        "source_obligation_lane_ids": [f"source-obligation:{component_id}"],
        "node_status": "consumed",
        "output_ref_digest": f"node-output-digest:{node_id}",
        "multi_source_shape_ref": {
            "status": "preserved" if relation_count > 1 else "not_present",
            "relation_count": relation_count,
            "source_count": source_count,
            "relation_ref_count": relation_count,
            "source_ref_count": source_count,
            "candidate_ref_count": max(source_count, 1),
            "best_source_collapse_created": False,
            "single_undifferentiated_source_output_created": False,
            "multi_component_claimed": False,
        },
        "closed_downstream_flags": {
            "component_work_node_created_source_display": False,
            "component_work_node_created_fap": False,
            "component_work_node_created_author": False,
            "component_work_node_rendered_citations": False,
            "component_work_node_claimed_product_correctness": False,
        },
        "raw_private_retention_flags": {
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
            "raw_source_content_retained": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "private_logs_retained": False,
            "db_cache_rows_retained": False,
            "full_trace_retained": False,
        },
    }


def _edge(
    *,
    from_node_id: str = "node:eligibility",
    from_component_id: str = "component:eligibility",
    to_node_id: str = "node:fee",
    to_component_id: str = "component:fee",
) -> dict[str, Any]:
    return {
        "edge_id": "edge:eligibility-before-fee",
        "from_component_node_ref": _edge_node_ref(from_node_id, from_component_id),
        "to_component_node_ref": _edge_node_ref(to_node_id, to_component_id),
        "dependency_kind": "eligibility_constrains_fee_answer",
        "blocking": True,
        "required_upstream_status": "consumed",
        "constraint_summary_ref": {
            "constraint_summary_id": "constraint:eligibility-before-fee",
            "constraint_summary_digest": "constraint-digest:eligibility-before-fee",
        },
        "rationale_ref": {
            "rationale_id": "rationale:eligibility-before-fee",
            "rationale_digest": "rationale-digest:eligibility-before-fee",
        },
        "created_by": "external_dependency_fixture",
        "admitted_by_runkernel_ref": {"status": "not_admitted"},
    }


def _edge_node_ref(node_id: str, component_id: str) -> dict[str, str]:
    return {
        "schema_version": "component_work_node_v0",
        "node_id": node_id,
        "component_id": component_id,
    }


def _future_ref(schema_version: str, ref_id: str) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "ref_id": ref_id,
        "ref_digest": f"digest:{ref_id}",
        "status": "externally_produced",
    }
