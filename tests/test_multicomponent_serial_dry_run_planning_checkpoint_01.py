"""SEAM-DIAGNOSTIC: multi-component serial dry-run checkpoint V0.

Harness label: SEAM-DIAGNOSTIC

Ordinary product path guarded or fed:
future multi-component readiness/FAP path over serially representable,
RunKernel-admitted graph/synthesis refs.

Runtime consumer:
future Sufficiency/FAP phases after explicit licensing.

Why ordinary product-path work cannot be done directly:
this checkpoint verifies serial composition of no-execution graph/synthesis/
admission refs before scheduling, runtime execution, FAP, Author, and rendering
are licensed.

Integration deadline:
the next product-facing answer checkpoint should consume admitted graph/synthesis
refs or name the blocker that prevents doing so.

Exit condition:
keep until serial checkpoint artifacts are superseded by a current
product-consumed multi-component path.

Why this is not a shadow product path:
the checkpoint does not execute graph work, dispatch retrieval, package FAP,
render Author prose, display sources, render citations, or answer.

Forbidden interpretation:
passing tests is not multi-component answering, graph scheduling, runtime
parallelism, retrieval quality, source display, citation rendering, FAP, Author,
source-obligation satisfaction, product correctness, or friend-level MVP.
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
    VALIDATION_STATUS_CHALLENGED,
    VALIDATION_STATUS_FOLLOWUP_NEEDED,
    VALIDATION_STATUS_SUPPORTED,
    VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS,
    VALIDATION_STATUS_UNSUPPORTED,
    dprime_synthesis_validation_v0_from_workbench,
)
from core.multicomponent_serial_dry_run_checkpoint import (
    SERIAL_CHECKPOINT_CLOSED_DOWNSTREAM_FLAGS,
    SERIAL_DRY_RUN_STATUS_BLOCKED,
    SERIAL_DRY_RUN_STATUS_CHALLENGED,
    SERIAL_DRY_RUN_STATUS_RECOVERY_AUTHORIZED,
    SERIAL_DRY_RUN_STATUS_REPRESENTED,
    SERIAL_DRY_RUN_STATUS_REPRESENTED_WITH_CAVEATS,
    MulticomponentSerialDryRunCheckpointError,
    multicomponent_serial_dry_run_checkpoint_v0_from_artifacts,
    multicomponent_serial_dry_run_checkpoint_v0_ref,
    validate_multicomponent_serial_dry_run_checkpoint_v0,
)
from core.runkernel_component_graph_admission import (
    ADMISSION_STATUS_ADMITTED,
    ADMISSION_STATUS_ADMITTED_WITH_CAVEATS,
    ADMISSION_STATUS_BLOCKED,
    ADMISSION_STATUS_CHALLENGED,
    ADMISSION_STATUS_RECOVERY_AUTHORIZED,
    runkernel_component_graph_admission_v0_from_refs,
)

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_RUNTIME = ROOT / "core" / "multicomponent_serial_dry_run_checkpoint.py"


def test_happy_path_builds_reviewable_serial_checkpoint_packet() -> None:
    graph, workbench, validation, admission = _admitted_chain()

    checkpoint = _checkpoint(graph, workbench, validation, admission)

    assert validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint) == checkpoint
    assert checkpoint["schema_version"] == "multicomponent_serial_dry_run_checkpoint_v0"
    assert checkpoint["phase"] == "MULTICOMPONENT-SERIAL-DRY-RUN-PLANNING-CHECKPOINT-01"
    assert checkpoint["serial_dry_run_status"] == SERIAL_DRY_RUN_STATUS_REPRESENTED
    assert checkpoint["runkernel_graph_admission_ref"]["admission_status"] == (
        ADMISSION_STATUS_ADMITTED
    )
    assert checkpoint["admitted_synthesis_refs"][0]["admission_status"] == (
        ADMISSION_STATUS_ADMITTED
    )
    assert checkpoint["parent_run_id"] == graph["parent_run_id"]
    assert checkpoint["user_query_ref"]["query_id"] == "query:n400-fee-and-eligibility"
    assert checkpoint["review_packet_refs"]
    assert checkpoint["serial_trace_refs"]
    assert checkpoint["serial_checkpoint_executed_graph"] is False
    assert checkpoint["serial_checkpoint_scheduled_graph"] is False
    assert checkpoint["serial_checkpoint_dispatched_search"] is False
    assert checkpoint["serial_checkpoint_performed_cross_component_analysis"] is False
    assert checkpoint["serial_checkpoint_performed_dprime_validation"] is False
    assert checkpoint["serial_checkpoint_performed_runkernel_admission"] is False
    assert checkpoint["serial_checkpoint_created_fap"] is False
    assert checkpoint["serial_checkpoint_created_author_output"] is False
    assert checkpoint["serial_checkpoint_rendered_citations"] is False
    assert checkpoint["serial_checkpoint_claimed_product_correctness"] is False
    assert checkpoint["serial_checkpoint_claimed_friend_mvp"] is False


def test_compact_checkpoint_ref_stays_review_only() -> None:
    checkpoint = _checkpoint(*_admitted_chain())

    ref = multicomponent_serial_dry_run_checkpoint_v0_ref(checkpoint)

    assert ref["checkpoint_id"] == checkpoint["checkpoint_id"]
    assert ref["checkpoint_digest"] == checkpoint["checkpoint_digest"]
    assert ref["review_artifact_only"] is True
    assert ref["graph_executed"] is False
    assert ref["graph_scheduled"] is False
    assert ref["fap_created"] is False
    assert ref["author_output_created"] is False
    assert ref["product_correctness_claimed"] is False


def test_preserves_component_node_refs() -> None:
    graph, workbench, validation, admission = _admitted_chain()

    checkpoint = _checkpoint(graph, workbench, validation, admission)

    assert checkpoint["component_node_refs"] == graph["component_node_refs"]
    assert checkpoint["cross_component_analyst_ref"]["component_node_refs"] == (
        graph["component_node_refs"]
    )


def test_preserves_dependency_edge_refs() -> None:
    graph, workbench, validation, admission = _admitted_chain()

    checkpoint = _checkpoint(graph, workbench, validation, admission)

    edge = checkpoint["dependency_edge_refs"][0]
    assert edge["edge_id"] == "edge:eligibility-before-fee"
    assert edge["edge_digest"] == graph["dependency_edges"][0]["edge_digest"]
    assert checkpoint["cross_component_analyst_ref"]["dependency_edge_refs"][0][
        "edge_id"
    ] == edge["edge_id"]


def test_preserves_parent_graph_workbench_dprime_and_runkernel_identity() -> None:
    graph, workbench, validation, admission = _admitted_chain()

    checkpoint = _checkpoint(graph, workbench, validation, admission)

    assert checkpoint["parent_graph_ref"]["graph_id"] == graph["graph_id"]
    assert checkpoint["parent_graph_ref"]["graph_digest"] == graph["graph_digest"]
    assert checkpoint["cross_component_analyst_ref"][
        "cross_component_analyst_id"
    ] == workbench["cross_component_analyst_id"]
    assert checkpoint["cross_component_analyst_ref"][
        "cross_component_analyst_digest"
    ] == workbench["cross_component_analyst_digest"]
    assert checkpoint["dprime_synthesis_validation_ref"][
        "dprime_synthesis_validation_id"
    ] == validation["dprime_synthesis_validation_id"]
    assert checkpoint["dprime_synthesis_validation_ref"][
        "dprime_synthesis_validation_digest"
    ] == validation["dprime_synthesis_validation_digest"]
    assert checkpoint["runkernel_graph_admission_ref"][
        "runkernel_graph_admission_id"
    ] == admission["runkernel_graph_admission_id"]
    assert checkpoint["runkernel_graph_admission_ref"][
        "runkernel_graph_admission_digest"
    ] == admission["runkernel_graph_admission_digest"]


def test_preserves_synthesis_proposal_and_claim_identity() -> None:
    workbench = _workbench()
    validation = _validation(workbench)
    admission = _admission(_graph_from_workbench(workbench), workbench, validation)

    checkpoint = _checkpoint(_graph_from_workbench(workbench), workbench, validation, admission)

    proposal_id, proposal_digest = _synthesis_identity(workbench)
    admitted = checkpoint["admitted_synthesis_refs"][0]
    assert admitted["synthesis_proposal_id"] == proposal_id
    assert admitted["synthesis_proposal_digest"] == proposal_digest
    assert admitted["synthesis_claim_ref"] == _claim_ref()

    tampered = deepcopy(checkpoint)
    tampered["admitted_synthesis_refs"][0]["synthesis_claim_ref"][
        "claim_digest"
    ] = "claim-digest:changed"
    tampered["checkpoint_digest"] = None
    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(tampered)


def test_preserves_required_caveats_and_nonclaims() -> None:
    caveat = _caveat_ref()
    nonclaim = _nonclaim_ref()
    workbench = _workbench(required_caveat_refs=[caveat], nonclaim_refs=[nonclaim])
    validation = _validation(
        workbench,
        validation_status=VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS,
        caveat_preservation_refs=[_caveat_preservation_ref(workbench, caveat)],
    )
    admission = _admission(_graph_from_workbench(workbench), workbench, validation)

    checkpoint = _checkpoint(_graph_from_workbench(workbench), workbench, validation, admission)

    assert checkpoint["serial_dry_run_status"] == (
        SERIAL_DRY_RUN_STATUS_REPRESENTED_WITH_CAVEATS
    )
    assert checkpoint["required_caveat_refs"] == [caveat]
    assert checkpoint["preserved_nonclaim_refs"] == [nonclaim]
    assert checkpoint["admitted_synthesis_refs"][0]["required_caveat_refs"] == [caveat]
    assert checkpoint["admitted_synthesis_refs"][0]["preserved_nonclaim_refs"] == [
        nonclaim
    ]


def test_blocked_checkpoint_preserves_blockers_without_admitted_synthesis() -> None:
    graph = _graph()
    workbench = _workbench(parent_graph_ref=graph)
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_UNSUPPORTED,
    )
    admission = _admission(
        graph,
        workbench,
        validation,
        admission_status=ADMISSION_STATUS_BLOCKED,
        blocker_refs=[_blocker_ref()],
    )

    checkpoint = _checkpoint(graph, workbench, validation, admission)

    assert checkpoint["serial_dry_run_status"] == SERIAL_DRY_RUN_STATUS_BLOCKED
    assert checkpoint["runkernel_graph_admission_ref"]["admission_status"] == (
        ADMISSION_STATUS_BLOCKED
    )
    assert checkpoint["admitted_synthesis_refs"] == []
    assert checkpoint["blocked_synthesis_refs"]
    assert checkpoint["blocked_synthesis_refs"][0]["admission_status"] == (
        ADMISSION_STATUS_BLOCKED
    )
    assert checkpoint["blocker_refs"] == [_blocker_ref()]


def test_accepts_challenged_state_without_admitted_synthesis() -> None:
    graph = _graph()
    workbench = _workbench(parent_graph_ref=graph)
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_CHALLENGED,
        challenge_refs=True,
    )
    admission = _admission(graph, workbench, validation)

    checkpoint = _checkpoint(graph, workbench, validation, admission)

    assert checkpoint["serial_dry_run_status"] == SERIAL_DRY_RUN_STATUS_CHALLENGED
    assert checkpoint["admitted_synthesis_refs"] == []
    assert checkpoint["challenge_refs"]
    assert checkpoint["challenge_refs"][0]["challenge_status"] == (
        ADMISSION_STATUS_CHALLENGED
    )


def test_accepts_bounded_recovery_authorized_state_without_dispatching() -> None:
    checkpoint = _recovery_authorized_checkpoint()

    assert checkpoint["serial_dry_run_status"] == (
        SERIAL_DRY_RUN_STATUS_RECOVERY_AUTHORIZED
    )
    assert checkpoint["runkernel_graph_admission_ref"]["admission_status"] == (
        ADMISSION_STATUS_RECOVERY_AUTHORIZED
    )
    recovery = checkpoint["recovery_authorization_refs"][0]
    assert recovery["runkernel_owned_output_ref"] is True
    assert recovery["created_by_runkernel_component_graph_admission_v0"] is True
    assert recovery["no_dispatch"] is True
    assert recovery["not_executed"] is True
    assert recovery["search_dispatched"] is False
    assert recovery["retrieval_dispatched"] is False


def test_rejects_mismatched_parent_run_id_across_refs() -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["cross_component_analyst_ref"]["parent_run_id"] = "run:other"
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_rejects_mismatched_graph_digest_across_refs() -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["dprime_synthesis_validation_ref"]["parent_graph_ref"][
        "graph_digest"
    ] = "graph-digest:other"
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("component_node_refs", []),
        ("parent_graph_ref", {}),
        ("cross_component_analyst_ref", {}),
        ("dprime_synthesis_validation_ref", {}),
        ("runkernel_graph_admission_ref", {}),
    ],
)
def test_rejects_missing_or_malformed_required_refs(
    field_name: str,
    replacement: Any,
) -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint[field_name] = replacement
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_rejects_malformed_component_node_ref_schema() -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["component_node_refs"][0]["schema_version"] = "not_component_node"
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_rejects_represented_status_when_runkernel_admission_is_blocked() -> None:
    graph = _graph()
    workbench = _workbench(parent_graph_ref=graph)
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_UNSUPPORTED,
    )
    admission = _admission(
        graph,
        workbench,
        validation,
        admission_status=ADMISSION_STATUS_BLOCKED,
        blocker_refs=[_blocker_ref()],
    )

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        _checkpoint(
            graph,
            workbench,
            validation,
            admission,
            serial_dry_run_status=SERIAL_DRY_RUN_STATUS_REPRESENTED,
        )


def test_rejects_represented_unless_runkernel_admission_status_is_admitted() -> None:
    graph, workbench, validation, admission = _admitted_chain()

    checkpoint = _checkpoint(graph, workbench, validation, admission)
    checkpoint["runkernel_graph_admission_ref"]["admission_status"] = (
        ADMISSION_STATUS_ADMITTED_WITH_CAVEATS
    )
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_rejects_represented_with_caveats_unless_admitted_with_caveats() -> None:
    graph, workbench, validation, admission = _admitted_chain()

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        _checkpoint(
            graph,
            workbench,
            validation,
            admission,
            serial_dry_run_status=SERIAL_DRY_RUN_STATUS_REPRESENTED_WITH_CAVEATS,
        )


@pytest.mark.parametrize(
    "serial_status",
    [
        SERIAL_DRY_RUN_STATUS_BLOCKED,
        SERIAL_DRY_RUN_STATUS_CHALLENGED,
        SERIAL_DRY_RUN_STATUS_RECOVERY_AUTHORIZED,
    ],
)
def test_rejects_non_represented_checkpoint_with_admitted_synthesis_state(
    serial_status: str,
) -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["serial_dry_run_status"] = serial_status
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


@pytest.mark.parametrize(
    "flag",
    [
        "scheduled_graph",
        "executed_graph",
        "created_runtime_parallelism",
        "created_budget_lease",
    ],
)
def test_rejects_serial_trace_refs_that_claim_scheduling_execution_or_budget(
    flag: str,
) -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["serial_trace_refs"][0][flag] = True
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_rejects_serial_trace_ref_with_admission_status() -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["serial_trace_refs"][0]["admission_status"] = ADMISSION_STATUS_ADMITTED
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("provider_called", "true"),
        ("model_called", 1),
    ],
)
def test_rejects_serial_trace_reverse_call_aliases(
    flag: str,
    value: Any,
) -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["serial_trace_refs"][0][flag] = value
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


@pytest.mark.parametrize(
    "flag",
    [
        "created_fap",
        "created_author_output",
        "created_source_display",
        "rendered_citations",
        "claimed_source_obligation_satisfaction",
        "claimed_product_correctness",
        "claimed_friend_mvp",
    ],
)
def test_rejects_review_packet_refs_that_claim_downstream_output(flag: str) -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["review_packet_refs"][0][flag] = True
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_rejects_review_packet_ref_with_admission_status() -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["review_packet_refs"][0]["admission_status"] = (
        ADMISSION_STATUS_ADMITTED
    )
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("provider_called", "yes"),
        ("model_called", 1),
        ("fetch_read_called", "false"),
        ("retrieval_called", "true"),
    ],
)
def test_rejects_review_packet_reverse_call_aliases(
    flag: str,
    value: Any,
) -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["review_packet_refs"][0][flag] = value
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_rejects_blocker_ref_with_admission_status() -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    blocker_ref = _blocker_ref()
    blocker_ref["admission_status"] = ADMISSION_STATUS_ADMITTED
    checkpoint["blocker_refs"] = [blocker_ref]
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_rejects_typed_review_ref_with_reverse_call_alias() -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    blocker_ref = _blocker_ref()
    blocker_ref["retrieval_called"] = "false"
    checkpoint["blocker_refs"] = [blocker_ref]
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


@pytest.mark.parametrize(
    "flag",
    [
        "serial_checkpoint_dispatched_search",
        "serial_checkpoint_called_provider",
        "serial_checkpoint_called_model",
        "serial_checkpoint_called_fetch_read",
        "serial_checkpoint_called_retrieval",
    ],
)
def test_rejects_provider_model_search_fetch_read_retrieval_call_flags(
    flag: str,
) -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint[flag] = True
    checkpoint["closed_downstream_flags"][flag] = True
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_rejects_raw_private_material_anywhere() -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    checkpoint["review_packet_refs"][0]["nested"] = {"raw_source_text": "private"}
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


@pytest.mark.parametrize("value", ["false", "true", 1, 0, None, "no"])
def test_rejects_closed_downstream_flags_that_are_not_boolean_false(value: Any) -> None:
    checkpoint = _checkpoint(*_admitted_chain())
    flag = "serial_checkpoint_executed_graph"
    checkpoint[flag] = value
    checkpoint["closed_downstream_flags"][flag] = value
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


@pytest.mark.parametrize("flag", SERIAL_CHECKPOINT_CLOSED_DOWNSTREAM_FLAGS)
def test_all_required_closed_downstream_flags_are_present_and_false(flag: str) -> None:
    checkpoint = _checkpoint(*_admitted_chain())

    assert checkpoint["closed_downstream_flags"][flag] is False
    assert checkpoint[flag] is False


def test_rejects_bounded_recovery_authorization_that_dispatches_retrieval() -> None:
    graph = _graph()
    workbench = _workbench(parent_graph_ref=graph)
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_FOLLOWUP_NEEDED,
        followup_need_refs=True,
    )
    admission_id = "runkernel-component-graph-admission:test-recovery"
    recovery_ref = _recovery_authorization_ref(workbench, validation, admission_id)
    recovery_ref["retrieval_dispatched"] = True

    with pytest.raises(Exception):  # admission validator fails first, as desired.
        _admission(
            graph,
            workbench,
            validation,
            runkernel_graph_admission_id=admission_id,
            admission_status=ADMISSION_STATUS_RECOVERY_AUTHORIZED,
            recovery_authorization_refs=[recovery_ref],
        )


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("model_called", "yes"),
        ("fetch_read_called", 1),
        ("retrieval_called", "false"),
    ],
)
def test_rejects_recovery_authorization_reverse_call_aliases(
    flag: str,
    value: Any,
) -> None:
    checkpoint = _recovery_authorized_checkpoint()
    checkpoint["recovery_authorization_refs"][0][flag] = value
    checkpoint["checkpoint_digest"] = None

    with pytest.raises(MulticomponentSerialDryRunCheckpointError):
        validate_multicomponent_serial_dry_run_checkpoint_v0(checkpoint)


def test_runtime_imports_do_not_open_live_or_product_surfaces() -> None:
    imported, called = _imports_and_calls(CHECKPOINT_RUNTIME)

    forbidden_imports = {
        "httpx",
        "openai",
        "requests",
        "search_providers",
        "pipeline_orchestrator",
        "final_answer_packet_hardening_runtime",
        "author_prose_finalization_runtime",
        "sufficiency_readiness_runtime",
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


def _checkpoint(
    graph: Mapping[str, Any],
    workbench: Mapping[str, Any],
    validation: Mapping[str, Any],
    admission: Mapping[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    return multicomponent_serial_dry_run_checkpoint_v0_from_artifacts(
        parent_graph_artifact=graph,
        cross_component_analyst_artifact=workbench,
        dprime_synthesis_validation_artifact=validation,
        runkernel_graph_admission_artifact=admission,
        **overrides,
    )


def _admitted_chain() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    graph = _graph()
    workbench = _workbench(parent_graph_ref=graph)
    validation = _validation(workbench)
    admission = _admission(graph, workbench, validation)
    return graph, workbench, validation, admission


def _recovery_authorized_checkpoint() -> dict[str, Any]:
    graph = _graph()
    workbench = _workbench(parent_graph_ref=graph)
    validation = _validation_for_status(
        workbench,
        validation_status=VALIDATION_STATUS_FOLLOWUP_NEEDED,
        followup_need_refs=True,
    )
    admission_id = "runkernel-component-graph-admission:test-recovery"
    recovery_ref = _recovery_authorization_ref(workbench, validation, admission_id)
    admission = _admission(
        graph,
        workbench,
        validation,
        runkernel_graph_admission_id=admission_id,
        admission_status=ADMISSION_STATUS_RECOVERY_AUTHORIZED,
        recovery_authorization_refs=[recovery_ref],
    )
    return _checkpoint(graph, workbench, validation, admission)


def _admission(
    graph: Mapping[str, Any],
    workbench: Mapping[str, Any],
    validation: Mapping[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    return runkernel_component_graph_admission_v0_from_refs(
        parent_graph_ref=graph,
        cross_component_analyst_ref=workbench,
        dprime_synthesis_validation_ref=validation,
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
    challenge_refs: bool = False,
    followup_need_refs: bool = False,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if challenge_refs:
        kwargs["challenge_refs"] = [_challenge_ref(workbench)]
    if followup_need_refs:
        kwargs["followup_need_refs"] = [_followup_need_ref(workbench)]
        kwargs["runkernel_consideration_refs"] = [_runkernel_consideration_ref(workbench)]
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
        parent_run_id="run:serial-checkpoint-test",
        parent_run_ref={
            "run_id": "run:serial-checkpoint-test",
            "run_digest": "run-digest:serial-checkpoint-test",
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
        "parent_run_id": "run:serial-checkpoint-test",
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
