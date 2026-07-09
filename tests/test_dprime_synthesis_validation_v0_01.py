"""SEAM-DIAGNOSTIC: synthesis D-prime validation V0 contract.

Harness label: SEAM-DIAGNOSTIC
Ordinary product path guarded or fed: future RunKernel graph/synthesis
admission over validated synthesis refs.
Runtime consumer: future RUNKERNEL-COMPONENT-GRAPH-ADMISSION-V0-01.
Why ordinary product-path work cannot be done directly: this is a synthesis
validation contract before RunKernel graph/synthesis admission and product
rendering are licensed.
Integration deadline: RUNKERNEL-COMPONENT-GRAPH-ADMISSION-V0-01 should consume
this validation contract.
Exit condition: keep until synthesis validation artifacts are superseded by a
current product-consumed cross-component path.
Why this is not a shadow product path: D-prime synthesis validation does not
admit support, mutate the contract, dispatch retrieval, package FAP, render
Author prose, or answer.
Forbidden interpretation: passing tests is not multi-component answering,
RunKernel admission, retrieval quality, FAP, Author, source display, citation
rendering, or product correctness.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from core.component_work_graph import component_work_graph_v0_from_component_nodes
from core.cross_component_analyst_workbench import (
    ANALYSIS_STATUS_BLOCKED_CONTRADICTION,
    ANALYSIS_STATUS_BLOCKED_DEPENDENCY,
    ANALYSIS_STATUS_BLOCKED_MISSING_COMPONENT,
    ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
    cross_component_analyst_workbench_v0_from_graph,
)
from core.dprime_synthesis_validation import (
    VALIDATION_STATUS_CHALLENGED,
    VALIDATION_STATUS_FOLLOWUP_NEEDED,
    VALIDATION_STATUS_SUPPORTED,
    VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS,
    DPrimeSynthesisValidationError,
    dprime_synthesis_validation_v0_from_workbench,
    dprime_synthesis_validation_v0_ref,
    validate_dprime_synthesis_validation_v0,
)

ROOT = Path(__file__).resolve().parents[1]
SYNTHESIS_RUNTIME = ROOT / "core" / "dprime_synthesis_validation.py"


def test_happy_path_accepts_two_component_synthesis_support_ref() -> None:
    workbench = _workbench()

    validation = _validation(workbench)

    assert validate_dprime_synthesis_validation_v0(validation) == validation
    assert validation["schema_version"] == "dprime_synthesis_validation_v0"
    assert validation["phase"] == "DPRIME-SYNTHESIS-VALIDATION-V0-01"
    assert validation["validation_status"] == VALIDATION_STATUS_SUPPORTED
    assert validation["input_workbench_status"] == ANALYSIS_STATUS_SYNTHESIS_PROPOSED
    assert len(validation["synthesis_proposal_refs"]) == 1
    assert len(validation["component_refs_under_validation"]) == 2
    assert validation["support_validation_refs"][0]["synthesis_proposal_id"] == (
        _synthesis_identity(workbench)[0]
    )
    assert validation["dprime_synthesis_admitted_support"] is False
    assert validation["dprime_synthesis_created_runkernel_admission"] is False
    assert validation["dprime_synthesis_authorized_retrieval"] is False
    assert validation["dprime_synthesis_created_fap"] is False
    assert validation["dprime_synthesis_created_author_output"] is False
    assert validation["dprime_synthesis_rendered_citations"] is False
    assert validation["dprime_synthesis_claimed_product_correctness"] is False


def test_compact_ref_is_built_from_validated_artifact() -> None:
    workbench = _workbench()
    validation = _validation(workbench)

    ref = dprime_synthesis_validation_v0_ref(validation)

    assert ref["schema_version"] == "dprime_synthesis_validation_v0"
    assert ref["phase"] == "DPRIME-SYNTHESIS-VALIDATION-V0-01"
    assert ref["dprime_synthesis_validation_id"] == (
        validation["dprime_synthesis_validation_id"]
    )
    assert ref["dprime_synthesis_validation_digest"] == (
        validation["dprime_synthesis_validation_digest"]
    )
    assert ref["parent_run_id"] == validation["parent_run_id"]
    assert ref["validation_status"] == validation["validation_status"]
    assert ref["synthesis_proposal_refs"] == [
        {
            "schema_version": "synthesis_proposal_ref_v0",
            "synthesis_proposal_id": _synthesis_identity(workbench)[0],
            "synthesis_proposal_digest": _synthesis_identity(workbench)[1],
            "proposal_only": True,
        }
    ]
    assert ref["support_validation_ref_count"] == 1
    assert ref["challenge_ref_count"] == 0
    assert ref["runkernel_admission_created"] is False
    assert ref["answer_contract_mutated"] is False
    assert ref["retrieval_authorized"] is False
    assert ref["product_correctness_claimed"] is False


def test_compact_ref_rejects_runkernel_admission_tampering() -> None:
    validation = _validation(_workbench())
    validation["runkernel_admitted"] = True

    with pytest.raises(DPrimeSynthesisValidationError):
        dprime_synthesis_validation_v0_ref(validation)


def test_compact_ref_rejects_raw_private_material() -> None:
    validation = _validation(_workbench())
    validation["support_validation_refs"][0]["raw_source_text"] = "private source text"

    with pytest.raises(DPrimeSynthesisValidationError):
        dprime_synthesis_validation_v0_ref(validation)


def test_preserves_parent_graph_and_workbench_refs_without_mutation() -> None:
    graph = _graph()
    workbench = _workbench(parent_graph_ref=graph)
    original_graph = deepcopy(graph)
    original_workbench = deepcopy(workbench)

    validation = _validation(workbench)

    assert graph == original_graph
    assert workbench == original_workbench
    assert validation["parent_graph_ref"]["graph_id"] == graph["graph_id"]
    assert validation["parent_graph_ref"]["graph_digest"] == graph["graph_digest"]
    assert validation["cross_component_analyst_ref"][
        "cross_component_analyst_id"
    ] == workbench["cross_component_analyst_id"]
    assert validation["cross_component_analyst_ref"][
        "cross_component_analyst_digest"
    ] == workbench["cross_component_analyst_digest"]
    assert validation["dprime_synthesis_mutated_parent_graph"] is False
    assert validation["dprime_synthesis_mutated_workbench_artifact"] is False
    assert validation["dprime_synthesis_mutated_answer_contract"] is False


def test_preserves_component_refs_under_validation() -> None:
    validation = _validation(_workbench())

    assert validation["component_refs_under_validation"] == [
        _fee_ref(),
        _elig_ref(),
    ]


def test_preserves_dependency_edge_refs_under_validation() -> None:
    validation = _validation(_workbench())
    edge = validation["dependency_edge_refs_under_validation"][0]

    assert edge["edge_id"] == "edge:eligibility-before-fee"
    assert edge["edge_digest"]
    assert edge["from_component_node_ref"] == _elig_ref()
    assert edge["to_component_node_ref"] == _fee_ref()


def test_accepts_challenge_refs_as_validation_outputs_not_analyst_proposals() -> None:
    workbench = _workbench()

    validation = dprime_synthesis_validation_v0_from_workbench(
        workbench_artifact=workbench,
        validation_status=VALIDATION_STATUS_CHALLENGED,
        challenge_refs=[_challenge_ref(workbench)],
    )

    assert validation["challenge_refs"][0]["challenge_kind"] == "overbreadth"
    assert validation["challenge_refs"][0][
        "dprime_synthesis_validation_output_only"
    ] is True
    assert validation["dprime_synthesis_became_cross_component_analyst"] is False


def test_accepts_caveat_preservation_refs() -> None:
    caveat = _caveat_ref()
    workbench = _workbench(required_caveat_refs=[caveat])

    validation = _validation(
        workbench,
        validation_status=VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS,
        caveat_preservation_refs=[_caveat_preservation_ref(workbench, caveat)],
    )

    assert validation["caveat_refs_under_validation"] == [caveat]
    assert validation["caveat_preservation_refs"][0]["required_caveat_id"] == (
        caveat["required_caveat_id"]
    )
    assert validation["dprime_synthesis_dropped_caveat"] is False


def test_accepts_followup_need_refs_only_as_runkernel_consideration_inputs() -> None:
    workbench = _workbench()

    validation = dprime_synthesis_validation_v0_from_workbench(
        workbench_artifact=workbench,
        validation_status=VALIDATION_STATUS_FOLLOWUP_NEEDED,
        followup_need_refs=[_followup_need_ref(workbench)],
        runkernel_consideration_refs=[_runkernel_consideration_ref(workbench)],
    )

    assert validation["followup_need_refs"][0]["retrieval_authorized"] is False
    assert validation["runkernel_consideration_refs"][0][
        "runkernel_admission_created"
    ] is False
    assert validation["dprime_synthesis_authorized_retrieval"] is False


def test_rejects_support_status_without_synthesis_proposal_refs() -> None:
    workbench = _workbench(
        analysis_status="proposed",
        synthesis_proposal_refs=[],
        component_refs_supporting_synthesis=[],
    )

    with pytest.raises(DPrimeSynthesisValidationError):
        dprime_synthesis_validation_v0_from_workbench(
            workbench_artifact=workbench,
            validation_status=VALIDATION_STATUS_SUPPORTED,
        )


def test_rejects_synthesis_proposal_with_fewer_than_two_components() -> None:
    artifact = _validation(_workbench())
    artifact["synthesis_proposal_refs"][0]["component_node_refs"] = [_fee_ref()]

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


def test_rejects_synthesis_proposal_with_wrong_node_for_known_component() -> None:
    artifact = _validation(_workbench())
    artifact["synthesis_proposal_refs"][0]["component_node_refs"][1] = {
        "schema_version": "component_work_node_v0",
        "node_id": "node:fee",
        "component_id": "component:eligibility",
    }

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


def test_rejects_support_ref_for_unknown_synthesis_proposal_id_digest() -> None:
    artifact = _validation(_workbench())
    artifact["support_validation_refs"][0]["synthesis_proposal_id"] = (
        "synthesis:unknown"
    )

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


def test_rejects_validation_artifact_that_introduces_new_synthesis_claim_ref() -> None:
    artifact = _validation(_workbench())
    artifact["synthesis_claim_ref"] = {
        "claim_id": "claim:new",
        "claim_digest": "claim-digest:new",
    }

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


@pytest.mark.parametrize(
    ("analysis_status", "workbench_field", "ref_kind"),
    [
        (
            ANALYSIS_STATUS_BLOCKED_CONTRADICTION,
            "contradiction_refs",
            "contradiction",
        ),
        (
            ANALYSIS_STATUS_BLOCKED_DEPENDENCY,
            "unresolved_dependency_refs",
            "unresolved_dependency",
        ),
        (
            ANALYSIS_STATUS_BLOCKED_MISSING_COMPONENT,
            "missing_component_proposal_refs",
            "missing_component",
        ),
    ],
)
def test_rejects_support_like_status_when_blockers_remain_present(
    analysis_status: str,
    workbench_field: str,
    ref_kind: str,
) -> None:
    ref = {
        "contradiction": _contradiction_ref,
        "unresolved_dependency": _unresolved_dependency_ref,
        "missing_component": _missing_component_ref,
    }[ref_kind]()
    workbench = _workbench(analysis_status=analysis_status, **{workbench_field: [ref]})

    with pytest.raises(DPrimeSynthesisValidationError):
        _validation(workbench)


def test_rejects_support_validation_when_required_caveat_refs_are_dropped() -> None:
    caveat = _caveat_ref()
    workbench = _workbench(required_caveat_refs=[caveat])
    artifact = _validation(
        workbench,
        validation_status=VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS,
        caveat_preservation_refs=[_caveat_preservation_ref(workbench, caveat)],
    )
    artifact["caveat_preservation_refs"] = []

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


def test_rejects_validation_artifact_that_chooses_different_synthesis_claim() -> None:
    artifact = _validation(_workbench())
    artifact["chosen_synthesis_claim_ref"] = {
        "claim_id": "claim:other",
        "claim_digest": "claim-digest:other",
    }

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


def test_rejects_validation_artifact_that_creates_new_synthesis_proposal_refs() -> None:
    artifact = _validation(_workbench())
    artifact["synthesis_proposal_refs"].append(
        {
            **_synthesis_ref(),
            "synthesis_proposal_id": "synthesis:new",
            "synthesis_proposal_digest": "digest:synthesis:new",
        }
    )

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


@pytest.mark.parametrize(
    "flag",
    [
        "dprime_synthesis_became_cross_component_analyst",
        "dprime_synthesis_chose_synthesis_claim",
        "dprime_synthesis_invented_claim",
    ],
)
def test_rejects_dprime_as_analyst_behavior_flags(flag: str) -> None:
    artifact = _validation(_workbench())
    artifact[flag] = True

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


def test_rejects_runkernel_admission_refs_or_admission_created_flags() -> None:
    artifact = _validation(_workbench())
    artifact["dprime_synthesis_created_runkernel_admission"] = True

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("status", "admitted"),
        ("authorization_status", "authorized"),
        ("runkernel_admission_status", "admitted"),
    ],
)
def test_rejects_runkernel_consideration_admission_or_authorization_status(
    key: str,
    value: str,
) -> None:
    artifact = _followup_validation(_workbench())
    artifact["runkernel_consideration_refs"][0][key] = value

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


@pytest.mark.parametrize(
    "flag",
    [
        "dprime_synthesis_mutated_answer_contract",
        "answer_contract_mutated",
    ],
)
def test_rejects_answer_contract_mutation_flags(flag: str) -> None:
    artifact = _validation(_workbench())
    artifact[flag] = True

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


@pytest.mark.parametrize(
    "flag",
    [
        "dprime_synthesis_authorized_retrieval",
        "dprime_synthesis_dispatched_search",
    ],
)
def test_rejects_retrieval_authorization_or_dispatch_flags(flag: str) -> None:
    artifact = _validation(_workbench())
    artifact[flag] = True

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


@pytest.mark.parametrize(
    "flag",
    [
        "dprime_synthesis_called_provider",
        "dprime_synthesis_called_model",
        "dprime_synthesis_called_fetch_read",
        "dprime_synthesis_called_retrieval",
    ],
)
def test_rejects_provider_model_fetch_read_retrieval_call_flags(flag: str) -> None:
    artifact = _validation(_workbench())
    artifact["closed_downstream_flags"][flag] = True

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


@pytest.mark.parametrize(
    "flag",
    [
        "dprime_synthesis_created_sufficiency_readiness",
        "dprime_synthesis_created_fap",
        "dprime_synthesis_created_author_output",
        "dprime_synthesis_created_source_display",
        "dprime_synthesis_rendered_citations",
        "dprime_synthesis_claimed_product_correctness",
    ],
)
def test_rejects_fap_author_source_display_citation_correctness_flags(
    flag: str,
) -> None:
    artifact = _validation(_workbench())
    artifact[flag] = True

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


def test_rejects_raw_private_material_anywhere() -> None:
    artifact = _validation(_workbench())
    artifact["challenge_refs"] = [
        {
            **_challenge_ref(_workbench()),
            "nested": {"raw_source_text": "private source text"},
        }
    ]

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


def test_rejects_authorization_approval_execution_status_values() -> None:
    artifact = _validation(_workbench())
    artifact["support_validation_refs"][0]["status"] = "approved"

    with pytest.raises(DPrimeSynthesisValidationError):
        validate_dprime_synthesis_validation_v0(artifact)


def test_runtime_imports_do_not_open_live_or_product_surfaces() -> None:
    imported, called = _imports_and_calls(SYNTHESIS_RUNTIME)

    assert imported.isdisjoint(
        {
            "core.pipeline_orchestrator",
            "core.search_providers",
            "openai",
            "requests",
            "httpx",
            "dotenv",
            "subprocess",
        }
    )
    assert called.isdisjoint(
        {
            "run_pipeline",
            "search_web",
            "retrieve",
            "dispatch_retrieval",
            "fetch_url",
            "fetch_page",
            "read_url",
            "ask_model",
        }
    )


def _validation(
    workbench: Mapping[str, Any],
    *,
    validation_status: str = VALIDATION_STATUS_SUPPORTED,
    caveat_preservation_refs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return dprime_synthesis_validation_v0_from_workbench(
        workbench_artifact=workbench,
        validation_status=validation_status,
        support_validation_refs=[_support_ref(workbench)],
        caveat_preservation_refs=list(caveat_preservation_refs or []),
    )


def _followup_validation(workbench: Mapping[str, Any]) -> dict[str, Any]:
    return dprime_synthesis_validation_v0_from_workbench(
        workbench_artifact=workbench,
        validation_status=VALIDATION_STATUS_FOLLOWUP_NEEDED,
        followup_need_refs=[_followup_need_ref(workbench)],
        runkernel_consideration_refs=[_runkernel_consideration_ref(workbench)],
    )


def _workbench(**overrides: Any) -> dict[str, Any]:
    graph = overrides.pop("parent_graph_ref", _graph())
    overrides.setdefault("analysis_status", ANALYSIS_STATUS_SYNTHESIS_PROPOSED)
    overrides.setdefault("synthesis_proposal_refs", [_synthesis_ref()])
    overrides.setdefault("component_refs_supporting_synthesis", [_fee_ref(), _elig_ref()])
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
        parent_run_id="run:dprime-synthesis-validation-test",
        parent_run_ref={
            "run_id": "run:dprime-synthesis-validation-test",
            "run_digest": "run-digest:dprime-synthesis-validation-test",
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


def _node_ref(component_id: str, node_id: str) -> dict[str, Any]:
    return {
        "schema_version": "component_work_node_v0",
        "node_kind": "component_work_node_v0_output",
        "node_id": node_id,
        "parent_run_id": "run:dprime-synthesis-validation-test",
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
        "from_component_node_ref": _elig_ref(),
        "to_component_node_ref": _fee_ref(),
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


def _synthesis_ref(**extra: Any) -> dict[str, Any]:
    return _proposal(
        "synthesis_proposal",
        "synthesis:fee-with-eligibility",
        component_refs=[_fee_ref(), _elig_ref()],
        dependency_refs=[_edge_ref()],
        synthesis_claim_ref={
            "claim_id": "claim:fee-applies-if-eligible",
            "claim_digest": "claim-digest:fee-applies-if-eligible",
        },
        support_posture="candidate_support_only",
        **extra,
    )


def _support_ref(workbench: Mapping[str, Any]) -> dict[str, Any]:
    proposal_id, proposal_digest = _synthesis_identity(workbench)
    return {
        "schema_version": "dprime_synthesis_support_validation_ref_v0",
        "support_validation_id": "support-validation:fee-eligibility",
        "support_validation_digest": "digest:support-validation:fee-eligibility",
        "validation_status": VALIDATION_STATUS_SUPPORTED,
        "synthesis_proposal_id": proposal_id,
        "synthesis_proposal_digest": proposal_digest,
        "evidence_admitted": False,
        "support_admitted": False,
        "runkernel_admission_created": False,
        "product_correctness_claimed": False,
    }


def _challenge_ref(workbench: Mapping[str, Any]) -> dict[str, Any]:
    proposal_id, proposal_digest = _synthesis_identity(workbench)
    return {
        "schema_version": "dprime_synthesis_challenge_ref_v0",
        "challenge_id": "challenge:overbreadth",
        "challenge_digest": "digest:challenge:overbreadth",
        "status": "challenged",
        "challenge_kind": "overbreadth",
        "synthesis_proposal_id": proposal_id,
        "synthesis_proposal_digest": proposal_digest,
        "support_admitted": False,
        "product_correctness_claimed": False,
    }


def _caveat_preservation_ref(
    workbench: Mapping[str, Any],
    caveat: Mapping[str, Any],
) -> dict[str, Any]:
    proposal_id, proposal_digest = _synthesis_identity(workbench)
    return {
        "schema_version": "dprime_synthesis_caveat_preservation_ref_v0",
        "caveat_preservation_id": caveat["required_caveat_id"],
        "caveat_preservation_digest": caveat["required_caveat_digest"],
        "required_caveat_id": caveat["required_caveat_id"],
        "required_caveat_digest": caveat["required_caveat_digest"],
        "status": "preserved",
        "synthesis_proposal_id": proposal_id,
        "synthesis_proposal_digest": proposal_digest,
        "dprime_synthesis_dropped_caveat": False,
    }


def _followup_need_ref(workbench: Mapping[str, Any]) -> dict[str, Any]:
    proposal_id, proposal_digest = _synthesis_identity(workbench)
    return {
        "schema_version": "dprime_synthesis_followup_need_ref_v0",
        "followup_need_id": "followup:effective-date-needed",
        "followup_need_digest": "digest:followup:effective-date-needed",
        "status": "followup_needed",
        "synthesis_proposal_id": proposal_id,
        "synthesis_proposal_digest": proposal_digest,
        "retrieval_authorized": False,
        "search_dispatched": False,
        "product_correctness_claimed": False,
    }


def _runkernel_consideration_ref(workbench: Mapping[str, Any]) -> dict[str, Any]:
    proposal_id, proposal_digest = _synthesis_identity(workbench)
    return {
        "schema_version": "runkernel_synthesis_consideration_ref_v0",
        "runkernel_consideration_id": "runkernel-consideration:fee-eligibility",
        "runkernel_consideration_digest": (
            "digest:runkernel-consideration:fee-eligibility"
        ),
        "status": "for_runkernel_consideration",
        "synthesis_proposal_id": proposal_id,
        "synthesis_proposal_digest": proposal_digest,
        "runkernel_admission_created": False,
        "authorization_status": "not_authorized",
        "answer_contract_mutated": False,
    }


def _caveat_ref() -> dict[str, Any]:
    return _proposal(
        "required_caveat",
        "caveat:eligibility-limited",
        component_refs=[_fee_ref(), _elig_ref()],
    )


def _contradiction_ref() -> dict[str, Any]:
    return _proposal(
        "contradiction",
        "contradiction:fee-currentness",
        component_refs=[_fee_ref(), _elig_ref()],
    )


def _unresolved_dependency_ref() -> dict[str, Any]:
    return _proposal(
        "unresolved_dependency",
        "dependency:eligibility-fee-unresolved",
        component_refs=[_fee_ref(), _elig_ref()],
        dependency_refs=[_edge_ref()],
    )


def _missing_component_ref() -> dict[str, Any]:
    return _proposal(
        "missing_component_proposal",
        "missing-component:effective-date",
        component_refs=[_fee_ref()],
        missing_component_id="missing-component:effective-date",
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


def _synthesis_identity(workbench: Mapping[str, Any]) -> tuple[str, str]:
    proposal = workbench["synthesis_proposal_refs"][0]
    return proposal["synthesis_proposal_id"], proposal["synthesis_proposal_digest"]


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


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    return imported, called
