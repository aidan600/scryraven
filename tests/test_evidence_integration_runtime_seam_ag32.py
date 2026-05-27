from __future__ import annotations

from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS, STOP_SUFFICIENT
from core.controller_state_reducer import ControllerEvidenceBoundary
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
    EvidenceIntegrationDecision,
    EvidenceIntegrationExpectedValue,
)
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
)
from tests.test_source_class_recovery_trace import _run_case


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _care_case(tmp_path: Any) -> tuple[Any, Any, dict[str, Any]]:
    return _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )


def test_runtime_records_active_gate_and_historical_handoff_consumer(
    tmp_path: Any,
) -> None:
    outcome, _harness, log_entry = _care_case(tmp_path)
    trace = outcome.execution_trace
    packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]

    assert packet["available"] is True
    assert packet["shadow_mode"] is False
    assert packet["controller_gate_active"] is True
    assert packet["gated_action"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["checkpoint_action_name"] == packet["decision"]["action_name"]
    assert packet["lifecycle_eligible"] is True
    assert packet["executor_dispatched"] is True
    assert packet["runtime_behavior_changed"] is True
    assert packet["action_executed"] is False
    assert packet["recommended_action_name"] == packet["decision"]["action_name"]
    assert packet["decision"]["shadow_mode"] is False
    assert packet["decision"]["runtime_behavior_changed"] is True
    assert packet["decision"]["consumers"] == [
        "parity_assertion",
        "answer_contract_fulfillment_handoff",
    ]
    assert packet["snapshot"]["metadata"]["stage"] == (
        "post_retrieval_post_source_class_lifecycle_pre_source_class_execution"
    )
    assert packet["snapshot"]["metadata"]["provider_routing_boundary"] == (
        "orchestrator_owned"
    )

    handoff = trace["answer_contract_fulfillment_handoff"]
    checkpoint_handoff = handoff["evidence_integration_checkpoint"]
    assert checkpoint_handoff["schema_version"] == (
        "evidence_integration_checkpoint_handoff_ag32_v1"
    )
    assert checkpoint_handoff["consumer"] == "answer_contract_fulfillment_handoff"
    assert checkpoint_handoff["shadow_mode"] is True
    assert checkpoint_handoff["runtime_behavior_changed"] is False
    assert checkpoint_handoff["action_name"] == packet["decision"]["action_name"]

    assert log_entry["execution_trace"][EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY] == (
        packet
    )
    assert_execution_trace_payload_contract(trace)
    assert_execution_trace_payload_contract(log_entry["execution_trace"])


def test_checkpoint_decision_blocks_source_class_executor_when_not_recovery(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_checkpoint_decision(_snapshot: Any) -> EvidenceIntegrationDecision:
        return EvidenceIntegrationDecision(
            action_name=STOP_SUFFICIENT,
            reason="fake_shadow_stop_for_parity_test",
            contract_gap_addressed=None,
            expected_value=EvidenceIntegrationExpectedValue.HIGH,
            budget_rationale="fake shadow decision spends no runtime budget",
            blocked_or_skipped_action_rationale={},
            evidence_boundary=ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY,
        )

    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        fake_checkpoint_decision,
    )
    fake_outcome, fake_harness, _fake_log = _care_case(tmp_path / "fake")

    packet = fake_outcome.execution_trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]
    assert packet["decision"]["action_name"] == STOP_SUFFICIENT
    assert packet["checkpoint_action_name"] == STOP_SUFFICIENT
    assert packet["controller_gate_active"] is True
    assert packet["lifecycle_eligible"] is True
    assert packet["authority_lifecycle_required_recovery_allowed"] is True
    assert packet["executor_dispatched"] is True
    assert packet["promoted_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert fake_harness.search_calls[0]["provider_role"] == "main_retrieval"
    assert fake_harness.search_calls[-1]["provider_role"] == "source_class_recovery"


def test_runtime_snapshot_carries_blocked_source_class_lifecycle_state(
    tmp_path: Any,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        mode="Fast",
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )
    packet = outcome.execution_trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]
    source_class_state = packet["snapshot"]["source_class_state"]

    assert source_class_state["recovery_recommended"] is True
    assert source_class_state["recovery_eligible"] is False
    assert "blocked_by_iteration_budget" in source_class_state["blockers"]
    assert packet["decision"]["action_name"] != RECOVER_MISSING_SOURCE_CLASS
    assert packet["controller_gate_active"] is True
    assert packet["lifecycle_eligible"] is False
    assert packet["executor_dispatched"] is False
    assert packet["terminal_stop_approved"] is True
    assert packet["final_answer_posture"] == "insufficient_with_caveat"
    assert packet["gate_reason"] == "terminal_stop_insufficient_with_caveat"
    assert packet["decision"]["blocked_or_skipped_action_rationale"][
        RECOVER_MISSING_SOURCE_CLASS
    ] == "blocked:blocked_by_iteration_budget"
    assert [call["provider_role"] for call in harness.search_calls] == [
        "main_retrieval"
    ]
