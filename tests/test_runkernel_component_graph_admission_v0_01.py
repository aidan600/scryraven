"""SEAM-DIAGNOSTIC: RunKernel graph/synthesis admission V0 contract.

Harness label: SEAM-DIAGNOSTIC
Ordinary product path guarded or fed: future multi-component readiness/FAP
admission path over RunKernel-admitted graph/synthesis refs.
Runtime consumer: future MULTICOMPONENT-SERIAL-DRY-RUN-PLANNING-CHECKPOINT-01
and later Sufficiency/FAP phases.
Why ordinary product-path work cannot be done directly: this is the RunKernel
admission boundary before scheduling, runtime execution, SufficiencyReadiness
expansion, FAP, Author, and product rendering are licensed.
Integration deadline: MULTICOMPONENT-SERIAL-DRY-RUN-PLANNING-CHECKPOINT-01
should consume this admission contract.
Exit condition: keep until graph/synthesis admission artifacts are superseded by
a current product-consumed multi-component path.
Why this is not a shadow product path: RunKernel admission does not execute
graph work, dispatch retrieval, package FAP, render Author prose, or answer.
Forbidden interpretation: passing tests is not multi-component answering, graph
scheduling, runtime parallelism, retrieval quality, FAP, Author, source display,
citation rendering, or product correctness.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from core.component_work_graph import component_work_graph_v0_from_component_nodes
from core.cross_component_analyst_workbench import (
    ANALYSIS_STATUS_SYNTHESIS_PROPOSED,
    cross_component_analyst_workbench_v0_from_graph,
)
from core.dprime_synthesis_validation import (
    VALIDATION_STATUS_BLOCKED_CONTRADICTION,
    VALIDATION_STATUS_BLOCKED_MISSING_COMPONENT,
    VALIDATION_STATUS_BLOCKED_MISSING_DEPENDENCY,
    VALIDATION_STATUS_CHALLENGED,
    VALIDATION_STATUS_FOLLOWUP_NEEDED,
    VALIDATION_STATUS_SUPPORTED,
    VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS,
    VALIDATION_STATUS_UNSUPPORTED,
    dprime_synthesis_validation_v0_from_workbench,
)
from core.runkernel_component_graph_admission import (
    ADMISSION_STATUS_ADMITTED,
    ADMISSION_STATUS_ADMITTED_WITH_CAVEATS,
    ADMISSION_STATUS_BLOCKED,
    ADMISSION_STATUS_CHALLENGED,
    ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED,
    ADMISSION_STATUS_RECOVERY_AUTHORIZED,
    RunKernelComponentGraphAdmissionError,
    runkernel_component_graph_admission_v0_from_refs,
    validate_runkernel_component_graph_admission_v0,
)

ROOT = Path(__file__).resolve().parents[1]
ADMISSION_RUNTIME = ROOT / "core" / "runkernel_component_graph_admission.py"


def test_happy_path_admits_supported_typed_graph_workbench_and_dprime_refs() -> None:
    workbench = _workbench()
    validation = _validation(workbench)

    admission = _admission(workbench, validation)

    assert validate_runkernel_component_graph_admission_v0(admission) == admission
    assert admission["schema_version"] == "runkernel_component_graph_admission_v0"
    assert admission["phase"] == "RUNKERNEL-COMPONENT-GRAPH-ADMISSION-V0-01"
    assert admission["admission_status"] == ADMISSION_STATUS_ADMITTED
    assert admission["input_validation_status"] == VALIDATION_STATUS_SUPPORTED
    assert len(admission["admitted_synthesis_refs"]) == 1
    admitted = admission["admitted_synthesis_refs"][0]
    assert admitted["synthesis_proposal_id"] == _synthesis_identity(workbench)[0]
    assert admitted["synthesis_proposal_digest"] == _synthesis_identity(workbench)[1]
    assert admitted["synthesis_claim_ref"] == _claim_ref()
    assert admission["runkernel_graph_admission_executed_graph"] is False
    assert admission["runkernel_graph_admission_dispatched_search"] is False
    assert admission["runkernel_graph_admission_created_fap"] is False
    assert admission["runkernel_graph_admission_created_author_output"] is False
    assert admission["runkernel_graph_admission_claimed_product_correctness"] is False


def test_rejects_malformed_or_tampered_inbound_compact_refs() -> None:
    admission = _admission(_workbench())

    malformed_graph = deepcopy(admission)
    malformed_graph["parent_graph_ref"] = {}
    malformed_graph["runkernel_graph_admission_digest"] = None
    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(malformed_graph)

    tampered_validation = deepcopy(admission)
    tampered_validation["dprime_synthesis_validation_ref"][
        "dprime_synthesis_validation_digest"
    ] = "tampered:digest"
    tampered_validation["runkernel_graph_admission_digest"] = None
    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(tampered_validation)


def test_preserves_parent_graph_workbench_and_dprime_validation_refs() -> None:
    graph = _graph()
    workbench = _workbench(parent_graph_ref=graph)
    validation = _validation(workbench)

    admission = _admission(workbench, validation)

    assert admission["parent_graph_ref"]["graph_id"] == graph["graph_id"]
    assert admission["parent_graph_ref"]["graph_digest"] == graph["graph_digest"]
    assert admission["cross_component_analyst_ref"][
        "cross_component_analyst_id"
    ] == workbench["cross_component_analyst_id"]
    assert admission["cross_component_analyst_ref"][
        "cross_component_analyst_digest"
    ] == workbench["cross_component_analyst_digest"]
    assert admission["dprime_synthesis_validation_ref"][
        "dprime_synthesis_validation_id"
    ] == validation["dprime_synthesis_validation_id"]
    assert admission["dprime_synthesis_validation_ref"][
        "dprime_synthesis_validation_digest"
    ] == validation["dprime_synthesis_validation_digest"]


def test_preserves_synthesis_proposal_and_claim_identity() -> None:
    workbench = _workbench()
    validation = _validation(workbench)

    admission = _admission(workbench, validation)

    proposal = admission["dprime_synthesis_validation_ref"]["synthesis_proposal_refs"][0]
    assert proposal["synthesis_proposal_id"] == _synthesis_identity(workbench)[0]
    assert proposal["synthesis_proposal_digest"] == _synthesis_identity(workbench)[1]
    assert proposal["synthesis_claim_ref"] == _claim_ref()

    tampered = deepcopy(admission)
    tampered["admitted_synthesis_refs"][0]["synthesis_claim_ref"][
        "claim_digest"
    ] = "tampered:claim"
    tampered["runkernel_graph_admission_digest"] = None
    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(tampered)


def test_preserves_required_caveat_refs() -> None:
    caveat = _caveat_ref()
    workbench = _workbench(required_caveat_refs=[caveat])
    validation = _validation(
        workbench,
        validation_status=VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS,
        caveat_preservation_refs=[_caveat_preservation_ref(workbench, caveat)],
    )

    admission = _admission(workbench, validation)

    assert admission["admission_status"] == ADMISSION_STATUS_ADMITTED_WITH_CAVEATS
    assert admission["required_caveat_refs"] == [caveat]
    assert admission["admitted_synthesis_refs"][0]["required_caveat_refs"] == [caveat]

    tampered = deepcopy(admission)
    tampered["admitted_synthesis_refs"][0]["required_caveat_refs"] = []
    tampered["runkernel_graph_admission_digest"] = None
    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(tampered)


def test_preserves_nonclaim_refs() -> None:
    nonclaim = _nonclaim_ref()
    workbench = _workbench(nonclaim_refs=[nonclaim])
    validation = _validation(workbench)

    admission = _admission(workbench, validation)

    assert admission["preserved_nonclaim_refs"] == [nonclaim]
    assert admission["admitted_synthesis_refs"][0]["preserved_nonclaim_refs"] == [
        nonclaim
    ]

    tampered = deepcopy(admission)
    tampered["admitted_synthesis_refs"][0]["preserved_nonclaim_refs"] = []
    tampered["runkernel_graph_admission_digest"] = None
    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(tampered)


@pytest.mark.parametrize(
    "validation_status, validation_kwargs",
    [
        (VALIDATION_STATUS_UNSUPPORTED, {}),
        (VALIDATION_STATUS_CHALLENGED, {"challenge_refs": "challenge"}),
        (VALIDATION_STATUS_FOLLOWUP_NEEDED, {"followup_need_refs": "followup"}),
        (
            VALIDATION_STATUS_BLOCKED_MISSING_DEPENDENCY,
            {"missing_dependency_refs": "missing_dependency"},
        ),
        (
            VALIDATION_STATUS_BLOCKED_CONTRADICTION,
            {"contradiction_refs_under_validation": "contradiction"},
        ),
        (
            VALIDATION_STATUS_BLOCKED_MISSING_COMPONENT,
            {"missing_component_refs_under_validation": "missing_component"},
        ),
    ],
)
def test_rejects_admission_when_dprime_validation_status_is_not_support_like(
    validation_status: str,
    validation_kwargs: Mapping[str, str],
) -> None:
    workbench = _workbench()
    validation = _validation_for_status(
        workbench,
        validation_status=validation_status,
        **validation_kwargs,
    )

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        _admission(
            workbench,
            validation,
            admission_status=ADMISSION_STATUS_ADMITTED,
        )


def test_accepts_blocked_synthesis_refs_without_admitting_support() -> None:
    workbench = _workbench()
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_UNSUPPORTED,
    )

    admission = _admission(
        workbench,
        validation,
        admission_status=ADMISSION_STATUS_BLOCKED,
        blocker_refs=[_blocker_ref()],
    )

    assert admission["admission_status"] == ADMISSION_STATUS_BLOCKED
    assert admission["admitted_synthesis_refs"] == []
    assert admission["blocked_synthesis_refs"]


def test_accepts_challenge_refs_without_admitting_support() -> None:
    workbench = _workbench()
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_CHALLENGED,
        challenge_refs="challenge",
    )

    admission = _admission(workbench, validation)

    assert admission["admission_status"] == ADMISSION_STATUS_CHALLENGED
    assert admission["challenge_refs"]
    assert admission["admitted_synthesis_refs"] == []


def test_accepts_bounded_recovery_authorization_refs_without_dispatching() -> None:
    workbench = _workbench()
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_FOLLOWUP_NEEDED,
        followup_need_refs="followup",
    )

    admission_id = "runkernel-component-graph-admission:test-recovery"
    recovery = _recovery_authorization_ref(workbench, validation, admission_id)
    admission = _admission(
        workbench,
        validation,
        runkernel_graph_admission_id=admission_id,
        recovery_authorization_refs=[recovery],
    )

    assert admission["admission_status"] == ADMISSION_STATUS_RECOVERY_AUTHORIZED
    assert admission["recovery_authorization_refs"][0]["no_dispatch"] is True
    assert admission["recovery_authorization_refs"][0]["not_executed"] is True
    assert admission["runkernel_graph_admission_dispatched_search"] is False
    assert admission["runkernel_graph_admission_called_retrieval"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        {"search_dispatched": True},
        {"retrieval_dispatched": True},
        {"component_refs_involved": []},
        {"synthesis_proposal_id": None},
        {"synthesis_proposal_digest": None},
        {"max_attempts": None},
        {"allowed_future_recovery_surface": None},
        {"expires_or_requires_new_admission": None},
    ],
)
def test_rejects_unbounded_or_dispatching_recovery_authorization_refs(
    mutation: Mapping[str, Any],
) -> None:
    workbench = _workbench()
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_FOLLOWUP_NEEDED,
        followup_need_refs="followup",
    )
    admission_id = "runkernel-component-graph-admission:test-recovery"
    recovery = _recovery_authorization_ref(workbench, validation, admission_id)
    for key, value in mutation.items():
        if value is None:
            recovery.pop(key, None)
        else:
            recovery[key] = value

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        _admission(
            workbench,
            validation,
            admission_status=ADMISSION_STATUS_RECOVERY_AUTHORIZED,
            runkernel_graph_admission_id=admission_id,
            recovery_authorization_refs=[recovery],
        )


def test_accepts_contract_amendment_candidate_refs_without_mutation_claims() -> None:
    workbench = _workbench()
    validation = _validation(workbench)

    admission = _admission(
        workbench,
        validation,
        admission_status=ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED,
        contract_amendment_candidate_refs=[_contract_amendment_candidate_ref()],
    )

    assert admission["admission_status"] == ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED
    assert admission["contract_amendment_candidate_refs"][0][
        "answer_contract_mutated"
    ] is False
    assert admission["answer_contract_mutated"] is False
    assert admission["current_answer_contract_mutated"] is False


def test_rejects_contract_amendment_refs_that_mutate_answer_contract() -> None:
    workbench = _workbench()
    validation = _validation(workbench)
    candidate = _contract_amendment_candidate_ref()
    candidate["answer_contract_mutated"] = True

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        _admission(
            workbench,
            validation,
            admission_status=ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED,
            contract_amendment_candidate_refs=[candidate],
        )


def test_rejects_tampered_admission_decision_ref_dispatch_claim() -> None:
    admission = _admission(_workbench())
    admission["admission_decision_refs"][0]["search_dispatched"] = True
    admission["runkernel_graph_admission_digest"] = None

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(admission)


@pytest.mark.parametrize("flag", ["called_provider", "retrieval_dispatched"])
def test_rejects_tampered_admitted_synthesis_ref_provider_or_retrieval_claim(
    flag: str,
) -> None:
    admission = _admission(_workbench())
    admission["admitted_synthesis_refs"][0][flag] = True
    admission["runkernel_graph_admission_digest"] = None

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(admission)


@pytest.mark.parametrize(
    "field_name",
    ["accepted_graph_state_refs", "accepted_synthesis_state_refs"],
)
def test_rejects_tampered_accepted_state_ref_contract_mutation_claim(
    field_name: str,
) -> None:
    admission = _admission(_workbench())
    admission[field_name][0]["answer_contract_mutated"] = True
    admission["runkernel_graph_admission_digest"] = None

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(admission)


@pytest.mark.parametrize(
    "flag",
    [
        "created_fap",
        "created_author_output",
        "created_source_display",
        "rendered_citations",
        "product_correctness_claimed",
    ],
)
def test_rejects_tampered_runkernel_output_ref_downstream_claims(flag: str) -> None:
    admission = _admission(_workbench())
    admission["admission_decision_refs"][0][flag] = True
    admission["runkernel_graph_admission_digest"] = None

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(admission)


@pytest.mark.parametrize(
    "field_name, value",
    [
        ("status", "executed"),
        ("authorization_status", "authorized"),
    ],
)
def test_rejects_tampered_runkernel_output_ref_unapproved_status_values(
    field_name: str,
    value: str,
) -> None:
    admission = _admission(_workbench())
    admission["admission_decision_refs"][0][field_name] = value
    admission["runkernel_graph_admission_digest"] = None

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(admission)


@pytest.mark.parametrize(
    "flag",
    [
        "runkernel_graph_admission_executed_graph",
        "runkernel_graph_admission_scheduled_graph",
        "runkernel_graph_admission_created_runtime_parallelism",
        "runkernel_graph_admission_created_budget_lease",
    ],
)
def test_rejects_graph_execution_scheduling_parallelism_and_budget_flags(
    flag: str,
) -> None:
    admission = _admission(_workbench())
    admission[flag] = True
    admission["closed_downstream_flags"][flag] = True
    admission["runkernel_graph_admission_digest"] = None

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(admission)


@pytest.mark.parametrize(
    "flag",
    [
        "runkernel_graph_admission_dispatched_search",
        "runkernel_graph_admission_called_provider",
        "runkernel_graph_admission_called_model",
        "runkernel_graph_admission_called_fetch_read",
        "runkernel_graph_admission_called_retrieval",
    ],
)
def test_rejects_provider_model_search_fetch_read_retrieval_call_flags(
    flag: str,
) -> None:
    admission = _admission(_workbench())
    admission[flag] = True
    admission["closed_downstream_flags"][flag] = True
    admission["runkernel_graph_admission_digest"] = None

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(admission)


@pytest.mark.parametrize(
    "flag",
    [
        "runkernel_graph_admission_performed_cross_component_analysis",
        "runkernel_graph_admission_performed_dprime_validation",
        "runkernel_graph_admission_created_sufficiency_readiness",
        "runkernel_graph_admission_created_fap",
        "runkernel_graph_admission_created_author_output",
        "runkernel_graph_admission_created_source_display",
        "runkernel_graph_admission_rendered_citations",
        "runkernel_graph_admission_claimed_product_correctness",
    ],
)
def test_rejects_downstream_sufficiency_fap_author_source_display_flags(
    flag: str,
) -> None:
    admission = _admission(_workbench())
    admission[flag] = True
    admission["closed_downstream_flags"][flag] = True
    admission["runkernel_graph_admission_digest"] = None

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(admission)


def test_rejects_raw_private_material_anywhere() -> None:
    admission = _admission(_workbench())
    admission["admission_decision_refs"][0]["raw_source_text"] = "private text"
    admission["runkernel_graph_admission_digest"] = None

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        validate_runkernel_component_graph_admission_v0(admission)


def test_rejects_status_laundering_values_in_nested_non_runkernel_refs() -> None:
    workbench = _workbench()
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_UNSUPPORTED,
    )

    with pytest.raises(RunKernelComponentGraphAdmissionError):
        _admission(
            workbench,
            validation,
            admission_status=ADMISSION_STATUS_BLOCKED,
            blocker_refs=[{**_blocker_ref(), "status": "admitted"}],
        )


def test_rejects_admission_when_blocker_refs_remain_unresolved() -> None:
    with pytest.raises(RunKernelComponentGraphAdmissionError):
        _admission(
            _workbench(),
            admission_status=ADMISSION_STATUS_ADMITTED,
            blocker_refs=[_blocker_ref()],
        )


def test_runtime_imports_do_not_open_live_or_product_surfaces() -> None:
    imported, called = _imports_and_calls(ADMISSION_RUNTIME)

    forbidden_imports = {
        "requests",
        "httpx",
        "openai",
        "search_providers",
        "final_answer_packet_hardening_runtime",
        "author_prose_finalization_runtime",
        "sufficiency_readiness_runtime",
        "runkernel_followup_search_reentry_ordinary_search_runtime",
    }
    forbidden_calls = {
        "run_pipeline",
        "fetch",
        "retrieve",
        "search",
        "authorize_live_search_validation",
        "build_final_answer_packet",
        "build_author_prose",
    }
    assert not (imported & forbidden_imports)
    assert not (called & forbidden_calls)


def _admission(
    workbench: Mapping[str, Any],
    validation: Mapping[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    validation_artifact = validation or _validation(workbench)
    return runkernel_component_graph_admission_v0_from_refs(
        parent_graph_ref=_graph_from_workbench(workbench),
        cross_component_analyst_ref=workbench,
        dprime_synthesis_validation_ref=validation_artifact,
        **overrides,
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


def _validation_for_status(
    workbench: Mapping[str, Any],
    *,
    validation_status: str,
    challenge_refs: str | None = None,
    followup_need_refs: str | None = None,
    missing_dependency_refs: str | None = None,
    contradiction_refs_under_validation: str | None = None,
    missing_component_refs_under_validation: str | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if challenge_refs:
        kwargs["challenge_refs"] = [_challenge_ref(workbench)]
    if followup_need_refs:
        kwargs["followup_need_refs"] = [_followup_need_ref(workbench)]
        kwargs["runkernel_consideration_refs"] = [_runkernel_consideration_ref(workbench)]
    if missing_dependency_refs:
        kwargs["missing_dependency_refs"] = [_missing_dependency_ref(workbench)]
    if contradiction_refs_under_validation:
        kwargs["contradiction_refs_under_validation"] = [_contradiction_ref()]
    if missing_component_refs_under_validation:
        kwargs["missing_component_refs_under_validation"] = [_missing_component_ref()]
    return dprime_synthesis_validation_v0_from_workbench(
        workbench_artifact=workbench,
        validation_status=validation_status,
        **kwargs,
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


def _graph_from_workbench(workbench: Mapping[str, Any]) -> dict[str, Any]:
    parent_graph_ref = workbench["parent_graph_ref"]
    graph = _graph()
    assert graph["graph_id"] == parent_graph_ref["graph_id"]
    assert graph["graph_digest"] == parent_graph_ref["graph_digest"]
    return graph


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
        parent_run_id="run:runkernel-graph-admission-test",
        parent_run_ref={
            "run_id": "run:runkernel-graph-admission-test",
            "run_digest": "run-digest:runkernel-graph-admission-test",
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
        "parent_run_id": "run:runkernel-graph-admission-test",
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
        synthesis_claim_ref=_claim_ref(),
        support_posture="candidate_support_only",
        **extra,
    )


def _claim_ref() -> dict[str, str]:
    return {
        "claim_id": "claim:fee-applies-if-eligible",
        "claim_digest": "claim-digest:fee-applies-if-eligible",
    }


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


def _missing_dependency_ref(workbench: Mapping[str, Any]) -> dict[str, Any]:
    proposal_id, proposal_digest = _synthesis_identity(workbench)
    return {
        "schema_version": "dprime_synthesis_missing_dependency_ref_v0",
        "missing_dependency_id": "missing-dependency:eligibility-currentness",
        "missing_dependency_digest": "digest:missing-dependency:eligibility-currentness",
        "synthesis_proposal_id": proposal_id,
        "synthesis_proposal_digest": proposal_digest,
        "retrieval_authorized": False,
        "search_dispatched": False,
    }


def _recovery_authorization_ref(
    workbench: Mapping[str, Any],
    validation: Mapping[str, Any],
    admission_id: str,
) -> dict[str, Any]:
    proposal_id, proposal_digest = _synthesis_identity(workbench)
    return {
        "schema_version": "runkernel_graph_admission_recovery_authorization_ref_v0",
        "runkernel_graph_admission_id": admission_id,
        "recovery_authorization_id": "recovery-auth:fee-eligibility",
        "recovery_authorization_digest": "digest:recovery-auth:fee-eligibility",
        "runkernel_owned_output_ref": True,
        "created_by_runkernel_component_graph_admission_v0": True,
        "dprime_synthesis_validation_id": validation["dprime_synthesis_validation_id"],
        "dprime_synthesis_validation_digest": validation[
            "dprime_synthesis_validation_digest"
        ],
        "synthesis_proposal_id": proposal_id,
        "synthesis_proposal_digest": proposal_digest,
        "component_refs_involved": [_fee_ref(), _elig_ref()],
        "reason": "D-prime requested bounded follow-up before synthesis admission.",
        "max_attempts": 1,
        "allowed_future_recovery_surface": "future RunKernel ordinary recovery re-entry only",
        "no_dispatch": True,
        "not_executed": True,
        "expires_or_requires_new_admission": "expires-after-next-admission-decision",
        "search_dispatched": False,
        "retrieval_dispatched": False,
        "called_provider": False,
        "called_model": False,
        "called_fetch_read": False,
        "called_retrieval": False,
        "answer_contract_mutated": False,
    }


def _contract_amendment_candidate_ref() -> dict[str, Any]:
    return {
        "schema_version": "runkernel_graph_admission_contract_amendment_candidate_ref_v0",
        "contract_amendment_candidate_id": "contract-candidate:graph-state",
        "contract_amendment_candidate_digest": "digest:contract-candidate:graph-state",
        "status": "candidate",
        "candidate_only": True,
        "answer_contract_mutated": False,
        "current_answer_contract_mutated": False,
        "live_current_answer_contract_mutated": False,
        "applied_to_current_answer_contract": False,
        "contract_amendment_applied": False,
    }


def _caveat_ref() -> dict[str, Any]:
    return _proposal(
        "required_caveat",
        "caveat:eligibility-limited",
        component_refs=[_fee_ref(), _elig_ref()],
    )


def _nonclaim_ref() -> dict[str, Any]:
    return _proposal(
        "nonclaim",
        "nonclaim:not-final-fee-advice",
        component_refs=[_fee_ref(), _elig_ref()],
    )


def _contradiction_ref() -> dict[str, Any]:
    return _proposal(
        "contradiction",
        "contradiction:fee-currentness",
        component_refs=[_fee_ref(), _elig_ref()],
    )


def _missing_component_ref() -> dict[str, Any]:
    return _proposal(
        "missing_component_proposal",
        "missing-component:effective-date",
        component_refs=[_fee_ref()],
        missing_component_id="missing-component:effective-date",
    )


def _blocker_ref() -> dict[str, Any]:
    return {
        "schema_version": "runkernel_graph_admission_blocker_ref_v0",
        "blocker_id": "blocker:unresolved-synthesis",
        "blocker_digest": "digest:blocker:unresolved-synthesis",
        "status": "unresolved",
    }


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
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[-1])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    return imported, called
