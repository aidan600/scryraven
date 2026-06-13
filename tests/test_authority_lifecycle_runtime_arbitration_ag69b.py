from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.authoritative_source_action import (
    AuthoritativeSourceActionFacts,
    build_authoritative_source_obligation_state_and_action,
)
from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    build_controller_loop_spine_result,
)
from core.run_controller import RunController

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"
_ACTION_PATH = _ROOT / "core" / "authoritative_source_action.py"

_QUERY = (
    "What is the current Social Security taxable maximum wage base for 2026, "
    "and what official source supports it? Keep the answer concise."
)
_RECOVERY_QUERIES = (
    "SSA 2026 Social Security taxable maximum wage base official source",
    "official current Social Security contribution benefit base 2026",
)


def _recommendation(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": ["official_current_rules"],
        "source_class_recovery_queries": list(_RECOVERY_QUERIES),
        "source_class_recovery_query_count": len(_RECOVERY_QUERIES),
        "source_class_recovery_reason": "source_class_recovery:ssa_gap",
        "source_class_recovery_trigger_fields": [
            "runtime_source_class_expectation"
        ],
    }
    payload.update(overrides)
    return payload


def _observability() -> dict[str, Any]:
    return {
        "source_class_satisfaction_status": {
            "official_current_rules": "expected_but_only_secondary"
        },
        "source_class_strong_satisfaction_counts": {
            "official_current_rules": 0
        },
        "source_class_gap_candidates": ["official_current_rules"],
    }


def _facts(
    *,
    terminal_stop_approved: bool = False,
    corpus_weak: bool = False,
    weak_corpus_recovery_used: bool = False,
    recommendation: dict[str, Any] | None = None,
) -> AuthoritativeSourceActionFacts:
    return AuthoritativeSourceActionFacts(
        query=_QUERY,
        intent="general",
        report_type="answer",
        query_type="official_current_status",
        core_topic="SSA 2026 Social Security taxable maximum wage base",
        primary_entity="SSA",
        recommendation=recommendation or _recommendation(),
        source_class_observability=_observability(),
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"payroll.example": 2},
            "top_source_domains": [{"domain": "payroll.example", "count": 2}],
            "unique_source_domain_count": 1,
            "on_domain_source_count": 0,
            "off_domain_source_count": 1,
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        corpus_state="OFF_TOPIC" if corpus_weak else "HEALTHY",
        corpus_weak=corpus_weak,
        weak_corpus_recovery_considered=weak_corpus_recovery_used,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=(
            "weak_corpus_recovery_used" if weak_corpus_recovery_used else None
        ),
        current_search_depth="basic",
        iteration_budget_available=False,
        terminal_stop_approved=terminal_stop_approved,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )


def _handoff(facts: AuthoritativeSourceActionFacts) -> Any:
    return build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=facts,
    )


def _terminal_checkpoint() -> dict[str, Any]:
    return {
        "available": True,
        "decision": {"action_name": STOP_INSUFFICIENT_WITH_CAVEAT},
        "recommended_action_name": STOP_INSUFFICIENT_WITH_CAVEAT,
    }


def _weak_checkpoint() -> dict[str, Any]:
    return {
        "available": True,
        "decision": {"action_name": RECOVER_WEAK_CORPUS},
        "recommended_action_name": RECOVER_WEAK_CORPUS,
    }


def _weak_lifecycle() -> dict[str, Any]:
    return {
        "approved": True,
        "reason": "weak_corpus_first_pass",
        "blockers": [],
    }


def _spine(
    lifecycle: dict[str, Any],
    *,
    checkpoint_trace: dict[str, Any],
    weak_lifecycle: dict[str, Any] | None = None,
) -> Any:
    return build_controller_loop_spine_result(
        checkpoint_trace=checkpoint_trace,
        source_class_lifecycle_trace=lifecycle,
        weak_corpus_lifecycle_trace=weak_lifecycle,
    )


def _requirement_bound_blocker(requirement_id: str) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "kind": "terminal_stop_approved",
        "reason": "controller_bound_terminal_stop",
        "owner": "controller",
        "hard": True,
    }


def test_ag69b_terminal_stop_blocks_required_recovery_admission() -> None:
    handoff = _handoff(_facts(terminal_stop_approved=True))
    lifecycle = handoff.active_source_class_recovery_lifecycle
    admission = handoff.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]
    spine = _spine(lifecycle, checkpoint_trace=_terminal_checkpoint())

    assert admission["admission_used"] is False
    assert admission["admission_blockers"] == ["terminal_stop_approved"]
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is True
    assert lifecycle["authority_lifecycle_terminal_stop_may_preempt"] is False
    assert spine.terminal_stop_approved is True
    assert spine.trace_packet["blocked_or_skipped_actions"][
        RECOVER_MISSING_SOURCE_CLASS
    ] == "blocked_by_terminal_stop"


def test_ag69b_weak_corpus_cannot_own_path_while_recovery_allowed() -> None:
    handoff = _handoff(
        _facts(corpus_weak=True, weak_corpus_recovery_used=True)
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle
    spine = _spine(
        lifecycle,
        checkpoint_trace=_weak_checkpoint(),
        weak_lifecycle=_weak_lifecycle(),
    )

    assert handoff.official_canonical_recovery_execution_admitted is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is True
    assert lifecycle["authority_lifecycle_weak_corpus_may_own_path"] is False
    assert spine.weak_corpus_executor_dispatched is False
    assert spine.trace_packet["blocked_or_skipped_actions"][RECOVER_WEAK_CORPUS] == (
        "blocked_by_authority_lifecycle_required_recovery"
    )


def test_ag69b_required_recovery_permission_survives_weak_local_gate_only() -> None:
    terminal = _handoff(_facts(terminal_stop_approved=True))
    weak = _handoff(_facts(corpus_weak=True, weak_corpus_recovery_used=True))

    terminal_spine = _spine(
        terminal.active_source_class_recovery_lifecycle,
        checkpoint_trace=_terminal_checkpoint(),
    )
    weak_spine = _spine(
        weak.active_source_class_recovery_lifecycle,
        checkpoint_trace=_weak_checkpoint(),
        weak_lifecycle=_weak_lifecycle(),
    )

    assert terminal_spine.terminal_stop_approved is True
    assert weak_spine.trace_packet["blocked_or_skipped_actions"][
        RECOVER_WEAK_CORPUS
    ] == "blocked_by_authority_lifecycle_required_recovery"


def test_ag69b_controller_hard_blocker_projection_is_requirement_bound() -> None:
    wrong_requirement = _handoff(
        _facts(
            recommendation=_recommendation(
                authority_lifecycle_blockers=[
                    _requirement_bound_blocker("different-requirement")
                ]
            ),
        )
    )
    bound = _handoff(
        _facts(
            recommendation=_recommendation(
                authority_lifecycle_blockers=[
                    _requirement_bound_blocker(
                        "official_current_source:official_current_rules"
                    )
                ]
            ),
        )
    )

    assert wrong_requirement.official_canonical_recovery_execution_admitted is True
    assert wrong_requirement.action_decision.approved is True
    assert bound.official_canonical_recovery_execution_admitted is True
    assert any(
        blocker.get("requirement_id")
        == "official_current_source:official_current_rules"
        for blocker in bound.active_source_class_recovery_lifecycle[
            "authority_lifecycle"
        ].get("explicit_blockers", [])
    )


def test_ag69b_insufficient_partial_posture_is_explicit_when_recovery_not_executed() -> None:
    handoff = _handoff(
        _facts(
            terminal_stop_approved=True,
            recommendation=_recommendation(
                authority_lifecycle_final_posture="insufficient_partial"
            ),
        )
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle
    spine = _spine(lifecycle, checkpoint_trace=_terminal_checkpoint())

    assert handoff.official_canonical_recovery_execution_admitted is False
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is False
    assert lifecycle[
        "authority_lifecycle_insufficient_partial_posture_explicit"
    ] is True
    assert lifecycle["authority_lifecycle"]["final_posture"] == (
        "insufficient_partial"
    )
    assert spine.terminal_stop_approved is True


def test_ag69b_projection_fields_do_not_control_arbitration() -> None:
    handoff = _handoff(_facts(terminal_stop_approved=True))
    lifecycle = {
        **handoff.active_source_class_recovery_lifecycle,
        "authority_lifecycle": {
            **handoff.active_source_class_recovery_lifecycle["authority_lifecycle"],
            "final_posture": "blocked",
            "terminal_paths": ["controller_hard_blocker"],
        },
    }
    spine = _spine(lifecycle, checkpoint_trace=_terminal_checkpoint())

    assert lifecycle["authority_lifecycle_projection_used_as_control_input"] is False
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is True
    assert spine.terminal_stop_approved is True


def test_ag69b_no_broad_pipeline_domain_logic_added() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8").casefold()
    pipeline_tree = ast.parse(_PIPELINE_PATH.read_text(encoding="utf-8"))

    assert "authority_lifecycle_runtime_arbitration" not in pipeline_source
    assert "authority_lifecycle_required_recovery_allowed" not in pipeline_source
    assert "social security taxable maximum" not in pipeline_source
    assert "standard mileage rate" not in pipeline_source
    assert not {
        node.name
        for node in ast.walk(pipeline_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and "authority_lifecycle" in node.name
    }


def test_ag69b_controller_arbitration_imports_stay_off_protected_surfaces() -> None:
    for path in (_ACTION_PATH, _SPINE_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imported.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert imported.isdisjoint(
            {
                "core.pipeline_orchestrator",
                "core.prompts",
                "core.routing",
                "core.search_providers",
                "core.source_classifier",
                "openai",
                "requests",
            }
        )
