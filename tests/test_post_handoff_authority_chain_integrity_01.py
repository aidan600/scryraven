"""POST-HANDOFF-AUTHORITY-CHAIN-INTEGRITY-01 focused regressions.

Test class: phase_focus / offline_product_path_proof.
No test in this file performs live, provider, or secrets-backed work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
import proplex.__main__ as compatibility_cli
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from tests.test_product_level_physical_attempt_cost_envelope_01 import (
    _bounded_isclose_runtime,
    _compiled_from_policy,
)


@pytest.mark.parametrize("entrypoint", ["proplex", "scryraven"])
def test_returned_blocked_fap_is_not_a_completed_bounded_answer(
    entrypoint: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the ordinary bounded N=1 path through its real blocked FAP."""

    harness, policy, config, deps = _bounded_isclose_runtime(
        tmp_path / entrypoint,
        monkeypatch,
        session_id=f"session-blocked-{entrypoint}",
        run_id=f"run-blocked-{entrypoint}",
    )
    compiled = _compiled_from_policy(policy)

    def fail_component_receiver(*_args: Any, **_kwargs: Any) -> None:
        raise orchestrator.OrdinaryMulticomponentRuntimeError(
            "forced component receiver validation failure"
        )

    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
        fail_component_receiver,
    )

    outcome = orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )

    assert outcome.report
    assert outcome.terminal_status == "blocked"
    assert outcome.execution_trace["blocked_fap_terminal"]["author_called"] is False
    assert harness.author_prompts == []
    assert harness.forbidden_live_calls == []
    assert policy.physical_snapshot()["furthest_product_stage"] == "run_outcome_blocked"
    assert policy.physical_snapshot()["product_failure_stage"] == (
        "searchos_component_receiver_failed"
    )

    payload = compatibility_cli._bounded_success_payload(
        entrypoint=entrypoint,
        config=config,
        outcome=outcome,
        compiled_authorization=compiled,
    )

    assert payload["status"] == "blocked"
    assert payload["terminal_status"] == "blocked"
    assert payload["furthest_product_stage"] == "run_outcome_blocked"
    assert payload["physical_envelope"]["product_failure_stage"] == (
        "searchos_component_receiver_failed"
    )
    assert payload["answer"] == ""
    assert payload["answer_present"] is False
    assert payload["citation_count"] == 0
    assert payload["citation_present"] is False
    assert payload["terminal_report"] == outcome.report
    terminal = dict(payload["terminal"])
    assert terminal["owner"] == "core.final_answer_packet_runtime"
    assert terminal["classification"] == "blocked"
    blocked_terminal = dict(terminal["blocked_fap_terminal"])
    assert blocked_terminal["exported_terminal_posture"] == "blocked"
    assert blocked_terminal["author_called"] is False

    projection = dict(payload["searchos_n1_causal_projection"])
    assert projection["projection_status"] == "available"
    assert projection["searchos_exit"] == "SEMANTIC_HANDOFF"
    assert projection["component_receiver_selected"] is True
    assert projection["slots"]
    assert any(slot["read_custody_observed"] is True for slot in projection["slots"])
    assert any(slot["semantic_handoff_present"] is True for slot in projection["slots"])
    assert all(
        slot["component_analyst_case_present"] is False
        for slot in projection["slots"]
    )
    assert all(
        slot["component_dprime_model_call_required"] is False
        and slot["component_dprime_model_call_executed"] is False
        for slot in projection["slots"]
    )
    assert all(
        slot["semantic_admission_status"] != "admitted"
        and slot["component_coverage_satisfied"] is False
        for slot in projection["slots"]
    )
