"""SEAM-DIAGNOSTIC: Cross-Component Analyst Workbench V0 proposal contract.

Harness label: SEAM-DIAGNOSTIC
Ordinary product path guarded or fed: future cross-component phase routing over
ComponentWorkGraph and ComponentWorkNode refs.
Runtime consumer: future synthesis D-prime validation and RunKernel
graph/synthesis admission phases.
Why ordinary product-path work cannot be done directly: this is a proposal-only
contract phase before synthesis validation, RunKernel admission, and product
rendering are licensed.
Integration deadline: DPRIME-SYNTHESIS-VALIDATION-V0-01 should consume this
proposal contract.
Exit condition: keep until Cross-Component Analyst proposal artifacts are
superseded by a current product-consumed cross-component path.
Why this is not a shadow product path: the Workbench does not validate
synthesis, admit support, dispatch retrieval, package FAP, render Author prose,
or answer.
Forbidden interpretation: passing tests is not multi-component answering,
synthesis validation, RunKernel admission, retrieval quality, FAP, Author,
source display, citation rendering, or product correctness.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

import pytest

from core.component_work_graph import component_work_graph_v0_from_component_nodes
from core.cross_component_analyst_workbench import (
    ANALYSIS_STATUS_BLOCKED_DEPENDENCY,
    ANALYSIS_STATUS_BLOCKED_MISSING_COMPONENT,
    ANALYSIS_STATUS_RECOVERY_PROPOSED,
    ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
    CrossComponentAnalystWorkbenchError,
    cross_component_analyst_workbench_v0_from_graph,
    validate_cross_component_analyst_workbench_v0,
)


def test_workbench_v0_accepts_graph_with_two_nodes_and_dependency_edge() -> None:
    artifact = _workbench()

    assert validate_cross_component_analyst_workbench_v0(artifact) == artifact
    assert artifact["schema_version"] == "cross_component_analyst_workbench_v0"
    assert artifact["phase"] == "CROSS-COMPONENT-SYNTHESIS-PROPOSAL-V0-01"
    assert artifact["analysis_status"] == "proposed"
    assert artifact["component_node_count"] == 2
    assert len(artifact["component_node_refs"]) == 2
    assert len(artifact["dependency_edge_refs"]) == 1
    assert artifact["cross_component_analyst_validated_synthesis"] is False
    assert artifact["cross_component_analyst_admitted_support"] is False
    assert artifact["cross_component_analyst_mutated_answer_contract"] is False
    assert artifact["cross_component_analyst_mutated_parent_graph"] is False
    assert artifact["cross_component_analyst_dispatched_search"] is False
    assert artifact["cross_component_analyst_called_retrieval"] is False
    assert artifact["cross_component_analyst_created_fap"] is False
    assert artifact["cross_component_analyst_created_author_output"] is False
    assert artifact["cross_component_analyst_rendered_citations"] is False
    assert artifact["cross_component_analyst_claimed_product_correctness"] is False


def test_workbench_preserves_component_node_refs_and_dependency_edge_refs() -> None:
    graph = _graph()

    artifact = _workbench(parent_graph_ref=graph)

    assert artifact["component_node_refs"] == graph["component_node_refs"]
    assert artifact["dependency_edge_refs"] == graph["dependency_edges"]
    assert artifact["parent_graph_ref"]["graph_id"] == graph["graph_id"]
    assert artifact["parent_graph_ref"]["graph_digest"] == graph["graph_digest"]
    assert artifact["input_graph_status"] == graph["graph_status"]


def test_workbench_accepts_consistency_matrix_ref_as_proposal_only() -> None:
    artifact = _workbench(
        consistency_matrix_ref=_proposal(
            "consistency_matrix",
            "consistency:fee-eligibility",
            component_refs=[_component_ref("node:fee", "component:fee"), _elig_ref()],
        )
    )

    matrix = artifact["consistency_matrix_ref"]
    assert matrix["proposal_only"] is True
    assert matrix["consistency_matrix_id"] == "consistency:fee-eligibility"
    assert artifact["cross_component_analyst_validated_synthesis"] is False


def test_workbench_accepts_constraint_relation_ref_as_proposal_only() -> None:
    artifact = _workbench(
        constraint_relation_refs=[
            _proposal(
                "constraint_relation",
                "constraint:eligibility-before-fee",
                component_refs=[_fee_ref(), _elig_ref()],
                dependency_refs=[_edge_ref()],
            )
        ]
    )

    relation = artifact["constraint_relation_refs"][0]
    assert relation["proposal_only"] is True
    assert relation["dependency_edge_refs"][0]["edge_id"] == (
        "edge:eligibility-before-fee"
    )


def test_workbench_accepts_contradiction_and_unresolved_dependency_refs() -> None:
    artifact = _workbench(
        analysis_status=ANALYSIS_STATUS_BLOCKED_DEPENDENCY,
        contradiction_refs=[
            _proposal("contradiction", "contradiction:fee-currentness")
        ],
        unresolved_dependency_refs=[
            _proposal(
                "unresolved_dependency",
                "dependency:eligibility-fee-unresolved",
                component_refs=[_fee_ref(), _elig_ref()],
                dependency_refs=[_edge_ref()],
            )
        ],
    )

    assert artifact["contradiction_refs"][0]["proposal_only"] is True
    assert artifact["unresolved_dependency_refs"][0]["proposal_only"] is True


def test_missing_component_proposals_do_not_mutate_answer_contract() -> None:
    artifact = _workbench(
        analysis_status=ANALYSIS_STATUS_BLOCKED_MISSING_COMPONENT,
        missing_component_proposal_refs=[
            _missing_component_ref("missing-component:effective-date")
        ],
    )

    assert artifact["missing_component_proposal_refs"][0]["proposal_only"] is True
    assert artifact["cross_component_analyst_mutated_answer_contract"] is False

    bad = _missing_component_ref("missing-component:effective-date")
    bad["mutated_answer_contract"] = True
    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            analysis_status=ANALYSIS_STATUS_BLOCKED_MISSING_COMPONENT,
            missing_component_proposal_refs=[bad],
        )


def test_recovery_requests_do_not_dispatch_or_claim_authorization() -> None:
    artifact = _workbench(
        analysis_status=ANALYSIS_STATUS_RECOVERY_PROPOSED,
        cross_component_recovery_request_refs=[_recovery_ref()],
    )

    recovery = artifact["cross_component_recovery_request_refs"][0]
    assert recovery["proposal_only"] is True
    assert recovery["cross_component_analyst_dispatched_search"] is False
    assert artifact["cross_component_analyst_called_retrieval"] is False

    bad = _recovery_ref()
    bad["runkernel_authorization_status"] = "authorized"
    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            analysis_status=ANALYSIS_STATUS_RECOVERY_PROPOSED,
            cross_component_recovery_request_refs=[bad],
        )


def test_synthesis_proposals_require_two_distinct_known_component_refs() -> None:
    artifact = _workbench(
        analysis_status=ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
        synthesis_proposal_refs=[_synthesis_ref()],
    )

    synthesis = artifact["synthesis_proposal_refs"][0]
    assert synthesis["proposal_only"] is True
    assert len(artifact["component_refs_supporting_synthesis"]) == 2
    assert artifact["cross_component_analyst_validated_synthesis"] is False


def test_synthesis_proposal_rejects_single_component_ref() -> None:
    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            analysis_status=ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
            synthesis_proposal_refs=[_synthesis_ref(component_refs=[_fee_ref()])],
        )


def test_synthesis_proposal_rejects_wrong_node_for_known_component() -> None:
    wrong = {
        "schema_version": "component_work_node_v0",
        "node_id": "node:fee",
        "component_id": "component:eligibility",
    }

    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            analysis_status=ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
            synthesis_proposal_refs=[
                _synthesis_ref(component_refs=[_fee_ref(), wrong])
            ],
        )


def test_synthesis_proposal_rejects_validation_claims() -> None:
    bad = _synthesis_ref()
    bad["validated"] = True

    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            analysis_status=ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
            synthesis_proposal_refs=[bad],
        )


def test_synthesis_proposal_rejects_runkernel_admission_claims() -> None:
    bad = _synthesis_ref()
    bad["runkernel_admitted"] = True

    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            analysis_status=ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
            synthesis_proposal_refs=[bad],
        )


@pytest.mark.parametrize("flag", ["fap_ready", "author_ready", "sufficiency_ready"])
def test_synthesis_proposal_rejects_fap_author_readiness_claims(flag: str) -> None:
    bad = _synthesis_ref()
    bad[flag] = True

    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            analysis_status=ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
            synthesis_proposal_refs=[bad],
        )


def test_dprime_synthesis_dossier_candidate_is_future_input_only() -> None:
    artifact = _workbench(
        dprime_synthesis_dossier_refs=[
            _proposal(
                "dprime_synthesis_dossier_candidate",
                "dprime-dossier:fee-eligibility",
                component_refs=[_fee_ref(), _elig_ref()],
                status="candidate_for_future_validation",
                future_validation_input=True,
            )
        ]
    )

    dossier = artifact["dprime_synthesis_dossier_refs"][0]
    assert dossier["proposal_only"] is True
    assert dossier["future_validation_input"] is True
    assert artifact["cross_component_analyst_created_dprime_validation"] is False


def test_rejects_dprime_synthesis_validation_refs_or_created_flags() -> None:
    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            dprime_synthesis_dossier_refs=[
                {
                    "schema_version": "dprime_synthesis_validation_ref_v0",
                    "dprime_synthesis_validation_id": "dprime-syn:validation",
                    "status": "validated",
                    "component_node_refs": [_fee_ref(), _elig_ref()],
                }
            ]
        )

    artifact = _workbench()
    artifact["cross_component_analyst_created_dprime_validation"] = True
    with pytest.raises(CrossComponentAnalystWorkbenchError):
        validate_cross_component_analyst_workbench_v0(artifact)


def test_rejects_runkernel_admission_refs_or_created_flags() -> None:
    bad = _proposal(
        "required_caveat",
        "caveat:admitted-by-runkernel",
        component_refs=[_fee_ref()],
    )
    bad["runkernel_admission_status"] = "admitted"
    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(required_caveat_refs=[bad])

    artifact = _workbench()
    artifact["cross_component_analyst_created_runkernel_admission"] = True
    with pytest.raises(CrossComponentAnalystWorkbenchError):
        validate_cross_component_analyst_workbench_v0(artifact)


@pytest.mark.parametrize(
    "flag",
    [
        "cross_component_analyst_dispatched_search",
        "cross_component_analyst_called_provider",
        "cross_component_analyst_called_model",
        "cross_component_analyst_called_fetch_read",
        "cross_component_analyst_called_retrieval",
    ],
)
def test_rejects_direct_search_provider_model_fetch_read_retrieval_flags(
    flag: str,
) -> None:
    artifact = _workbench()
    artifact[flag] = True

    with pytest.raises(CrossComponentAnalystWorkbenchError):
        validate_cross_component_analyst_workbench_v0(artifact)


@pytest.mark.parametrize(
    "flag",
    [
        "cross_component_analyst_created_sufficiency_readiness",
        "cross_component_analyst_created_fap",
        "cross_component_analyst_created_author_output",
        "cross_component_analyst_created_source_display",
        "cross_component_analyst_rendered_citations",
        "cross_component_analyst_claimed_product_correctness",
    ],
)
def test_rejects_fap_author_source_display_citation_correctness_flags(
    flag: str,
) -> None:
    artifact = _workbench()
    artifact["closed_downstream_flags"][flag] = True

    with pytest.raises(CrossComponentAnalystWorkbenchError):
        validate_cross_component_analyst_workbench_v0(artifact)


def test_rejects_raw_private_material_anywhere() -> None:
    bad = _proposal("contradiction", "contradiction:raw")
    bad["nested"] = {"raw_source_text": "private source text"}

    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(contradiction_refs=[bad])


def test_rejects_untraceable_or_collapsed_combined_answer_summaries() -> None:
    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            required_caveat_refs=[
                {
                    "schema_version": "required_caveat_ref_v0",
                    "required_caveat_id": "caveat:untraceable",
                    "status": "proposed",
                    "proposal_only": True,
                    "combined_answer_summary": "fee plus eligibility final answer",
                }
            ]
        )

    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            required_caveat_refs=[
                {
                    "schema_version": "required_caveat_ref_v0",
                    "required_caveat_id": "caveat:no-trace",
                    "status": "proposed",
                    "proposal_only": True,
                    "required_caveat_digest": "digest:no-trace",
                }
            ]
        )


def test_rejects_proposal_refs_that_reference_unknown_component_nodes() -> None:
    unknown = {
        "schema_version": "component_work_node_v0",
        "node_id": "node:unknown",
        "component_id": "component:unknown",
    }

    with pytest.raises(CrossComponentAnalystWorkbenchError):
        _workbench(
            source_refs_to_revisit=[
                _proposal(
                    "source_revisit",
                    "source-revisit:unknown",
                    component_refs=[unknown],
                )
            ]
        )


def test_workbench_does_not_mutate_parent_graph_ref() -> None:
    graph = _graph()
    original = deepcopy(graph)

    artifact = _workbench(parent_graph_ref=graph)

    assert graph == original
    assert artifact["parent_graph_ref"]["graph_id"] == original["graph_id"]
    assert artifact["parent_graph_ref"]["graph_status"] == original["graph_status"]
    assert artifact["parent_graph_mutated"] is False


def test_workbench_does_not_populate_graph_future_refs() -> None:
    graph = _graph()

    artifact = _workbench(parent_graph_ref=graph, synthesis_proposal_refs=[])

    for field_name in (
        "cross_component_analyst_refs",
        "synthesis_proposal_refs",
        "dprime_synthesis_validation_refs",
        "runkernel_synthesis_admission_refs",
    ):
        assert field_name not in artifact["parent_graph_ref"]
        assert graph[field_name] == []
    assert artifact["graph_future_refs_populated_by_workbench"] is False


def _workbench(**overrides: Any) -> dict[str, Any]:
    graph = overrides.pop("parent_graph_ref", _graph())
    return cross_component_analyst_workbench_v0_from_graph(
        parent_graph_ref=graph,
        **overrides,
    )


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
        parent_run_id="run:cross-component-workbench-test",
        parent_run_ref={
            "run_id": "run:cross-component-workbench-test",
            "run_digest": "run-digest:cross-component-workbench-test",
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
) -> dict[str, Any]:
    return {
        "schema_version": "component_work_node_v0",
        "node_kind": "component_work_node_v0_output",
        "node_id": node_id,
        "parent_run_id": "run:cross-component-workbench-test",
        "component_id": component_id,
        "component_ids": [component_id],
        "source_obligation_id": f"source-obligation:{component_id}",
        "source_obligation_lane_ids": [f"source-obligation:{component_id}"],
        "node_status": "consumed",
        "output_ref_digest": f"node-output-digest:{node_id}",
        "multi_source_shape_ref": {
            "status": "not_present",
            "relation_count": 1,
            "source_count": 1,
            "relation_ref_count": 1,
            "source_ref_count": 1,
            "candidate_ref_count": 1,
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


def _edge() -> dict[str, Any]:
    return {
        "edge_id": "edge:eligibility-before-fee",
        "from_component_node_ref": _component_ref(
            "node:eligibility",
            "component:eligibility",
        ),
        "to_component_node_ref": _component_ref("node:fee", "component:fee"),
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


def _proposal(
    kind: str,
    ref_id: str,
    *,
    component_refs: Sequence[Mapping[str, Any]] | None = None,
    dependency_refs: Sequence[Mapping[str, Any]] | None = None,
    status: str = "proposed",
    **extra: Any,
) -> dict[str, Any]:
    refs = [_fee_ref()] if component_refs is None else list(component_refs)
    proposal = {
        "schema_version": f"{kind}_ref_v0",
        f"{kind}_id": ref_id,
        f"{kind}_digest": f"digest:{ref_id}",
        "status": status,
        "proposal_only": True,
        "component_node_refs": refs,
        "validated": False,
        "runkernel_admitted": False,
        "fap_ready": False,
        "author_ready": False,
        "product_correctness_claimed": False,
        **extra,
    }
    if dependency_refs is not None:
        proposal["dependency_edge_refs"] = list(dependency_refs)
    return proposal


def _synthesis_ref(
    *,
    component_refs: Sequence[Mapping[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    refs = [_fee_ref(), _elig_ref()] if component_refs is None else list(component_refs)
    return _proposal(
        "synthesis_proposal",
        "synthesis:fee-with-eligibility",
        component_refs=refs,
        synthesis_claim_ref={
            "claim_id": "claim:fee-applies-if-eligible",
            "claim_digest": "claim-digest:fee-applies-if-eligible",
        },
        support_posture="candidate_support_only",
        **extra,
    )


def _missing_component_ref(ref_id: str) -> dict[str, Any]:
    return _proposal(
        "missing_component_proposal",
        ref_id,
        component_refs=[_fee_ref()],
        missing_component_id=ref_id,
    )


def _recovery_ref() -> dict[str, Any]:
    return _proposal(
        "cross_component_recovery_request",
        "recovery:official-current-effective-date",
        component_refs=[_fee_ref(), _elig_ref()],
        runkernel_authorized=False,
        cross_component_analyst_dispatched_search=False,
        cross_component_analyst_called_retrieval=False,
    )


def _edge_ref() -> dict[str, Any]:
    edge = _graph()["dependency_edges"][0]
    return {
        "schema_version": edge["schema_version"],
        "edge_id": edge["edge_id"],
        "edge_digest": edge["edge_digest"],
        "from_component_node_ref": edge["from_component_node_ref"],
        "to_component_node_ref": edge["to_component_node_ref"],
    }


def _fee_ref() -> dict[str, str]:
    return _component_ref("node:fee", "component:fee")


def _elig_ref() -> dict[str, str]:
    return _component_ref("node:eligibility", "component:eligibility")


def _component_ref(node_id: str, component_id: str) -> dict[str, str]:
    return {
        "schema_version": "component_work_node_v0",
        "node_id": node_id,
        "component_id": component_id,
    }
