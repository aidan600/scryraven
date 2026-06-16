from __future__ import annotations

from pathlib import Path

import pytest

from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.run_kernel import (
    EVIDENCE_LEDGER_STAGE,
    FINAL_ANSWER_PACKET_STAGE,
    FOLLOWUP_AUTHOR_GATE_STAGE,
    FOLLOWUP_AUTHORIZATION_STAGE,
    FOLLOWUP_EVIDENCE_INTAKE_STAGE,
    FOLLOWUP_EXECUTION_STAGE,
    FOLLOWUP_FINAL_ANSWER_PACKET_STAGE,
    FOLLOWUP_SUFFICIENCY_RECHECK_STAGE,
    RUN_KERNEL_TRACE_KEY,
    SUFFICIENCY_JUDGMENT_STAGE,
    RunKernelTransitionError,
)
from tests.helpers.followup_fixture_spine import (
    AUTHOR_CITATION_PRODUCT_FALSE_FLAGS,
    NO_LIVE_FALSE_FLAGS,
    assert_projection_from_state,
    boundary_flag_sets,
    run_followup_fixture_spine,
)

ROOT = Path(__file__).resolve().parents[1]


def test_balanced_followup_fixture_spine_consumes_author_gate_without_opening_closed_surfaces() -> None:
    spine = run_followup_fixture_spine(run_id="ag96i2g-fixture")
    kernel = spine.kernel

    assert [observation.stage for observation in kernel.state.observations] == [
        FOLLOWUP_AUTHORIZATION_STAGE,
        FOLLOWUP_EXECUTION_STAGE,
        FOLLOWUP_EVIDENCE_INTAKE_STAGE,
        FOLLOWUP_SUFFICIENCY_RECHECK_STAGE,
        FOLLOWUP_FINAL_ANSWER_PACKET_STAGE,
        FOLLOWUP_AUTHOR_GATE_STAGE,
    ]

    assert_projection_from_state(
        kernel.state.followup_authorization_projection,
        kernel.state.followup_authorization_state,
        ("consumption_id", "checkpoint_id", "run_id", "status"),
    )
    assert_projection_from_state(
        kernel.state.followup_execution_projection,
        kernel.state.followup_execution_state,
        ("execution_id", "observation_id", "sealed_candidate_id", "result_status"),
    )
    assert_projection_from_state(
        kernel.state.followup_evidence_intake_projection,
        kernel.state.followup_evidence_intake_state,
        (
            "intake_id",
            "observation_id",
            "sealed_candidate_id",
            "source_obligation_satisfied",
        ),
    )
    assert_projection_from_state(
        kernel.state.followup_sufficiency_recheck_projection,
        kernel.state.followup_sufficiency_recheck_state,
        ("recheck_id", "observation_id", "fixture_sufficiency_posture"),
    )
    assert_projection_from_state(
        kernel.state.followup_final_answer_packet_projection,
        kernel.state.followup_final_answer_packet_state,
        ("packet_preparation_id", "observation_id", "packet_id"),
    )
    assert_projection_from_state(
        kernel.state.followup_author_gate_projection,
        kernel.state.followup_author_gate_state,
        ("author_gate_id", "observation_id", "packet_id"),
    )

    assert kernel.state.followup_authorization_history == [
        kernel.state.followup_authorization_projection
    ]
    assert kernel.state.followup_execution_history == [
        kernel.state.followup_execution_projection
    ]
    assert kernel.state.followup_evidence_intake_history == [
        kernel.state.followup_evidence_intake_projection
    ]
    assert kernel.state.followup_sufficiency_recheck_history == [
        kernel.state.followup_sufficiency_recheck_projection
    ]
    assert kernel.state.followup_final_answer_packet_history == [
        kernel.state.followup_final_answer_packet_projection
    ]
    assert kernel.state.followup_author_gate_history == [
        kernel.state.followup_author_gate_projection
    ]

    ledger_projection = kernel.state.evidence_ledger.to_projection().to_dict()
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE] == ledger_projection
    assert kernel.state.projections[SUFFICIENCY_JUDGMENT_STAGE] == (
        kernel.state.sufficiency_judgment_projection
    )
    assert kernel.state.projections[FINAL_ANSWER_PACKET_STAGE] == (
        kernel.state.final_answer_authority_projection
    )
    assert ledger_projection["owner"] == "RunKernel.EvidenceLedger"
    assert ledger_projection["canonical_state"] is True
    assert ledger_projection["candidate_count"] == 1
    assert kernel.state.final_answer_authority_projection["packet_id"] == (
        kernel.state.final_answer_packet["packet_id"]
    )

    gate_state = kernel.state.followup_author_gate_state
    assert gate_state["packet_authority_consumed"] is True
    assert gate_state["final_answer_packet_digest"] == followup_projection_digest(
        kernel.state.final_answer_packet
    )
    assert gate_state["final_answer_authority_projection_digest"] == (
        followup_projection_digest(kernel.state.final_answer_authority_projection)
    )
    assert spine.gate_result.record.to_dict()["packet_authority_consumed"] is True

    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    with pytest.raises(RunKernelTransitionError, match="author input payload"):
        kernel.authorize_author_execution()

    for flags in boundary_flag_sets(kernel):
        for flag in NO_LIVE_FALSE_FLAGS:
            if flag in flags:
                assert flags[flag] is False
        for flag in AUTHOR_CITATION_PRODUCT_FALSE_FLAGS:
            if flag in flags:
                assert flags[flag] is False
        if "live_validation_not_run" in flags:
            assert flags["live_validation_not_run"] is True

    assert kernel.state.followup_final_answer_packet_projection[
        "canonical_final_answer_packet_ref"
    ] == {
        "owner": "RunKernel.FinalAnswerPacket",
        "canonical_state": True,
        "packet_id": kernel.state.final_answer_packet["packet_id"],
        "projection_stage": FINAL_ANSWER_PACKET_STAGE,
    }
    assert kernel.state.followup_author_gate_projection[
        "canonical_final_answer_packet_ref"
    ] == {
        "owner": "RunKernel.FinalAnswerPacket",
        "canonical_state": True,
        "packet_id": kernel.state.final_answer_packet["packet_id"],
        "projection_stage": FINAL_ANSWER_PACKET_STAGE,
    }

    trace = kernel.to_trace_fragment()[RUN_KERNEL_TRACE_KEY]
    assert trace["followup_author_gate_state"]["author_gate_id"] == (
        kernel.state.followup_author_gate_state["author_gate_id"]
    )
    assert trace["followup_author_gate_state"]["packet_authority_consumed"] is True
    assert trace["followup_author_gate_projection"] == (
        kernel.state.followup_author_gate_projection
    )


def test_extracted_followup_helpers_do_not_own_runkernel_state_commits() -> None:
    helper_source = (
        ROOT / "core" / "followup_runkernel_reducers.py"
    ).read_text(encoding="utf-8")
    run_kernel_source = (ROOT / "core" / "run_kernel.py").read_text(
        encoding="utf-8"
    )

    assert "RunKernel.start" not in helper_source
    assert ".state." not in helper_source
    assert "self.state.followup_author_gate_state = gate_state" in run_kernel_source
    assert (
        "self.state.followup_author_gate_projection = ("
        in run_kernel_source
    )
    assert "build_followup_author_gate_projection(" in run_kernel_source
