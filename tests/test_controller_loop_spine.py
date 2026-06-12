from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    ControllerLoopActionCandidate,
    ControllerLoopDispatchAuthorization,
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
    checkpoint_action_name_from_trace,
)

_ROOT = Path(__file__).resolve().parents[1]
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_SOURCE_CLASS_RECOVERY_RUNNER_PATH = (
    _ROOT / "core" / "source_class_recovery_runner.py"
)
_RETRIEVE_TARGETED = "retrieve_targeted"


def _checkpoint(action_name: str, *, available: bool = True) -> dict[str, Any]:
    if not available:
        return {"available": False, "decision": None, "recommended_action_name": None}
    return {
        "available": True,
        "decision": {
            "action_name": action_name,
            "shadow_mode": True,
            "runtime_behavior_changed": False,
        },
        "recommended_action_name": action_name,
        "shadow_mode": True,
        "runtime_behavior_changed": False,
    }


def _source_lifecycle(
    *,
    eligible: bool = True,
    reason: str = "blocked",
    official_canonical_admitted: bool = False,
) -> dict[str, Any]:
    payload = {
        "active_source_class_recovery_eligible": eligible,
        "active_source_class_recovery_blockers": [] if eligible else [reason],
        "active_source_class_recovery_official_canonical_admitted": (
            official_canonical_admitted
        ),
    }
    if official_canonical_admitted:
        payload["active_source_class_recovery_action_envelope"] = {
            "action_type": "recover_missing_source_class",
            "required_source_class": ["official_current_rules"],
            "allowed_action": True,
        }
    return payload


def _weak_lifecycle(*, approved: bool = True, reason: str = "weak_blocked") -> dict[str, Any]:
    return {
        "approved": approved,
        "reason": "weak_corpus_first_pass" if approved else reason,
        "blockers": [] if approved else [reason],
    }


def _conflict_lifecycle(
    *, approved: bool = True, reason: str = "conflict_blocked"
) -> dict[str, Any]:
    return {
        "approved": approved,
        "reason": "conflict_requires_resolution" if approved else reason,
        "blockers": [] if approved else [reason],
        "active_conflict_resolution_considered": True,
    }


def _targeted_lifecycle(
    *,
    eligible: bool = True,
    reason: str = "blocked_by_currentness_gap",
    queries: tuple[str, ...] = ("Acme Widget migration timeline",),
    resolving_queries: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "targeted_retrieval_candidate_considered": True,
        "targeted_retrieval_candidate_eligible": eligible,
        "targeted_retrieval_candidate_used": False,
        "targeted_retrieval_candidate_reason": (
            "targeted_retrieval_candidate_available" if eligible else reason
        ),
        "targeted_retrieval_candidate_skip_reason": (
            None if eligible else reason
        ),
        "targeted_retrieval_candidate_blockers": [] if eligible else [reason],
        "targeted_retrieval_candidate_queries": list(queries),
        "targeted_retrieval_candidate_conflict_resolving_queries": list(
            resolving_queries
        ),
    }


def _run(action_name: str, **overrides: Any) -> dict[str, Any]:
    result = build_controller_loop_spine_result(
        checkpoint_trace=_checkpoint(action_name),
        source_class_lifecycle_trace=overrides.get(
            "source", _source_lifecycle()
        ),
        weak_corpus_lifecycle_trace=overrides.get("weak", _weak_lifecycle()),
        conflict_resolution_lifecycle_trace=overrides.get(
            "conflict", _conflict_lifecycle()
        ),
        targeted_retrieval_lifecycle_trace=overrides.get(
            "targeted", _targeted_lifecycle()
        ),
    )
    return result.trace_packet


def test_checkpoint_action_name_extraction_prefers_decision() -> None:
    assert (
        checkpoint_action_name_from_trace(
            {
                "available": True,
                "decision": {"action_name": RECOVER_WEAK_CORPUS},
                "recommended_action_name": RECOVER_MISSING_SOURCE_CLASS,
            }
        )
        == RECOVER_WEAK_CORPUS
    )


def test_spine_input_dataclasses_normalize_json_safe_control_facts() -> None:
    action = ControllerLoopActionCandidate.from_trace(
        {
            "available": True,
            "decision": {"action_name": RECOVER_MISSING_SOURCE_CLASS},
            "recommended_action_name": RECOVER_WEAK_CORPUS,
            "tuple_value": ("one", "two"),
        }
    )
    spine_input = ControllerLoopSpineInput.from_traces(
        checkpoint_trace=action.checkpoint_trace,
        source_class_lifecycle_trace=_source_lifecycle(),
        weak_corpus_lifecycle_trace=_weak_lifecycle(),
        conflict_resolution_lifecycle_trace=_conflict_lifecycle(),
        targeted_retrieval_lifecycle_trace={
            **_targeted_lifecycle(),
            "tuple_value": ("targeted", "facts"),
        },
    )

    payload = spine_input.to_dict()

    assert action.available is True
    assert action.action_name == RECOVER_MISSING_SOURCE_CLASS
    assert payload["checkpoint_action"]["action_name"] == (
        RECOVER_MISSING_SOURCE_CLASS
    )
    assert payload["checkpoint_action"]["checkpoint_trace"]["tuple_value"] == [
        "one",
        "two",
    ]
    assert payload["source_class_lifecycle_trace"][
        "active_source_class_recovery_eligible"
    ] is True
    assert payload["targeted_retrieval_lifecycle_trace"]["tuple_value"] == [
        "targeted",
        "facts",
    ]


def test_spine_result_exposes_explicit_dispatch_authorization() -> None:
    result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=_checkpoint(RECOVER_WEAK_CORPUS),
            source_class_lifecycle_trace=_source_lifecycle(),
            weak_corpus_lifecycle_trace=_weak_lifecycle(),
            conflict_resolution_lifecycle_trace=_conflict_lifecycle(),
        )
    )

    authorization = result.dispatch_authorization

    assert isinstance(authorization, ControllerLoopDispatchAuthorization)
    assert authorization.authorized_action_name == RECOVER_WEAK_CORPUS
    assert authorization.weak_corpus_executor_dispatched is True
    assert result.authorized_dispatch == RECOVER_WEAK_CORPUS
    assert result.to_dict()["dispatch_authorization"][
        "authorized_action_name"
    ] == RECOVER_WEAK_CORPUS


@pytest.mark.parametrize(
    ("action_name", "executed"),
    [
        (RECOVER_MISSING_SOURCE_CLASS, RECOVER_MISSING_SOURCE_CLASS),
        (RECOVER_WEAK_CORPUS, RECOVER_WEAK_CORPUS),
        (RESOLVE_CONFLICT, RESOLVE_CONFLICT),
    ],
)
def test_exactly_one_checkpoint_decision_and_at_most_one_promoted_action(
    action_name: str,
    executed: str,
) -> None:
    packet = _run(action_name)

    assert packet["checkpoint_decision_count"] == 1
    assert packet["checkpoint_action_name"] == action_name
    assert packet["promoted_action_name"] == executed
    assert packet["executed_action_name"] == executed
    dispatched = [
        packet["source_class_executor_dispatched"],
        packet["weak_corpus_executor_dispatched"],
        packet["conflict_resolution_executor_dispatched"],
    ]
    assert dispatched.count(True) == 1


@pytest.mark.parametrize(
    ("action_name", "posture"),
    [
        (STOP_SUFFICIENT, "sufficient"),
        (STOP_INSUFFICIENT_WITH_CAVEAT, "insufficient_with_caveat"),
    ],
)
def test_terminal_stop_blocks_bounded_executors(
    action_name: str,
    posture: str,
) -> None:
    packet = _run(action_name)

    assert packet["terminal_stop_approved"] is True
    assert packet["final_answer_posture"] == posture
    assert packet["promoted_action_name"] == action_name
    assert packet["executed_action_name"] is None
    assert packet["source_class_executor_dispatched"] is False
    assert packet["weak_corpus_executor_dispatched"] is False
    assert packet["conflict_resolution_executor_dispatched"] is False
    assert packet["blocked_or_skipped_actions"][RECOVER_MISSING_SOURCE_CLASS] == (
        "blocked_by_terminal_stop"
    )
    assert packet["blocked_or_skipped_actions"][RECOVER_WEAK_CORPUS] == (
        "blocked_by_terminal_stop"
    )
    assert packet["blocked_or_skipped_actions"][RESOLVE_CONFLICT] == (
        "blocked_by_terminal_stop"
    )
    assert packet["blocked_or_skipped_actions"][_RETRIEVE_TARGETED] == (
        "blocked_by_terminal_stop"
    )
    assert packet["targeted_retrieval_gate_reason"] == "blocked_by_terminal_stop"
    assert packet["targeted_retrieval_executor_dispatched"] is False
    assert packet["targeted_retrieval_dispatch_authorized"] is False


def test_source_class_dispatch_only_when_checkpoint_selects_it_and_lifecycle_is_eligible() -> None:
    approved = _run(RECOVER_MISSING_SOURCE_CLASS)
    blocked = _run(
        RECOVER_MISSING_SOURCE_CLASS,
        source=_source_lifecycle(eligible=False, reason="blocked_by_iteration_budget"),
    )

    assert approved["executed_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert approved["executor_dispatched"] is True
    assert blocked["executed_action_name"] is None
    assert blocked["gate_reason"] == "blocked_by_lifecycle"
    assert blocked["blocked_or_skipped_actions"][RECOVER_MISSING_SOURCE_CLASS] == (
        "blocked_by_lifecycle"
    )


def test_official_canonical_admission_dispatches_when_no_checkpoint_action_competes() -> None:
    result = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": None,
            "recommended_action_name": None,
        },
        source_class_lifecycle_trace=_source_lifecycle(
            official_canonical_admitted=True
        ),
    )
    packet = result.trace_packet

    assert packet["checkpoint_decision_count"] == 0
    assert packet["official_canonical_admitted"] is True
    assert packet["official_canonical_dispatch_fallback"] is True
    assert packet["source_class_executor_dispatched"] is True
    assert packet["executed_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert result.dispatch_authorization.authorized_action_name == (
        RECOVER_MISSING_SOURCE_CLASS
    )


def test_official_canonical_admission_requires_valid_controller_envelope_for_fallback() -> None:
    lifecycle = _source_lifecycle(official_canonical_admitted=True)
    lifecycle["active_source_class_recovery_action_envelope"] = {
        "action_type": "recover_missing_source_class",
        "required_source_class": [],
        "allowed_action": True,
    }

    packet = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": None,
            "recommended_action_name": None,
        },
        source_class_lifecycle_trace=lifecycle,
    ).trace_packet

    assert packet["official_canonical_admitted"] is True
    assert packet["controller_action_envelope_approved"] is False
    assert packet["source_class_executor_dispatched"] is False
    assert packet["executed_action_name"] is None


def test_official_canonical_admission_dispatches_on_licensed_checkpoint_exception() -> None:
    packet = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": False,
            "reason": "checkpoint_exception",
            "official_canonical_checkpoint_exception_fallback_allowed": True,
            "decision": None,
            "recommended_action_name": None,
        },
        source_class_lifecycle_trace=_source_lifecycle(
            official_canonical_admitted=True
        ),
    ).trace_packet

    assert packet["official_canonical_admitted"] is True
    assert packet["official_canonical_dispatch_fallback"] is True
    assert packet["source_class_executor_dispatched"] is True
    assert packet["gate_reason"] == "approved_by_official_canonical_admission"
    assert packet["executed_action_name"] == RECOVER_MISSING_SOURCE_CLASS


def test_checkpoint_exception_without_fallback_control_fact_fails_closed() -> None:
    packet = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": False,
            "reason": "checkpoint_exception",
            "decision": None,
            "recommended_action_name": None,
        },
        source_class_lifecycle_trace=_source_lifecycle(
            official_canonical_admitted=True
        ),
    ).trace_packet

    assert packet["official_canonical_admitted"] is True
    assert packet["official_canonical_dispatch_fallback"] is False
    assert packet["source_class_executor_dispatched"] is False
    assert packet["gate_reason"] == "checkpoint_unavailable"
    assert packet["executed_action_name"] is None


def test_checkpoint_exception_without_official_canonical_admission_fails_closed() -> None:
    packet = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": False,
            "reason": "checkpoint_exception",
            "official_canonical_checkpoint_exception_fallback_allowed": True,
            "decision": None,
            "recommended_action_name": None,
        },
        source_class_lifecycle_trace=_source_lifecycle(
            official_canonical_admitted=False
        ),
    ).trace_packet

    assert packet["official_canonical_admitted"] is False
    assert packet["official_canonical_dispatch_fallback"] is False
    assert packet["source_class_executor_dispatched"] is False
    assert packet["gate_reason"] == "checkpoint_unavailable"
    assert packet["executed_action_name"] is None


def test_official_canonical_admission_dispatches_when_checkpoint_actionless() -> None:
    packet = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": False,
            "reason": "checkpoint_unavailable",
            "decision": None,
            "recommended_action_name": None,
        },
        source_class_lifecycle_trace=_source_lifecycle(
            official_canonical_admitted=True
        ),
    ).trace_packet

    assert packet["official_canonical_admitted"] is True
    assert packet["official_canonical_dispatch_fallback"] is True
    assert packet["source_class_executor_dispatched"] is True
    assert packet["gate_reason"] == "approved_by_official_canonical_admission"
    assert packet["executed_action_name"] == RECOVER_MISSING_SOURCE_CLASS


@pytest.mark.parametrize(
    "action_name",
    [
        RECOVER_WEAK_CORPUS,
        RESOLVE_CONFLICT,
        _RETRIEVE_TARGETED,
        STOP_INSUFFICIENT_WITH_CAVEAT,
    ],
)
def test_official_canonical_admission_does_not_substitute_for_checkpoint_action(
    action_name: str,
) -> None:
    packet = _run(
        action_name,
        source=_source_lifecycle(official_canonical_admitted=True),
    )

    assert packet["official_canonical_admitted"] is True
    assert packet["official_canonical_dispatch_fallback"] is False
    assert packet["source_class_executor_dispatched"] is False


def test_weak_corpus_dispatch_only_when_checkpoint_selects_it_and_lifecycle_is_eligible() -> None:
    approved = _run(RECOVER_WEAK_CORPUS)
    blocked = _run(
        RECOVER_WEAK_CORPUS,
        weak=_weak_lifecycle(approved=False, reason="max_iterations_1"),
    )

    assert approved["executed_action_name"] == RECOVER_WEAK_CORPUS
    assert approved["weak_corpus_executor_dispatched"] is True
    assert blocked["executed_action_name"] is None
    assert blocked["gate_reason"] == "max_iterations_1"
    assert blocked["blocked_or_skipped_actions"][RECOVER_WEAK_CORPUS] == (
        "max_iterations_1"
    )


def test_conflict_dispatch_only_when_checkpoint_selects_it_and_lifecycle_is_eligible() -> None:
    approved = _run(RESOLVE_CONFLICT)
    blocked = _run(
        RESOLVE_CONFLICT,
        conflict=_conflict_lifecycle(
            approved=False,
            reason="no_resolving_queries",
        ),
    )

    assert approved["executed_action_name"] == RESOLVE_CONFLICT
    assert approved["conflict_resolution_executor_dispatched"] is True
    assert blocked["executed_action_name"] is None
    assert blocked["gate_reason"] == "no_resolving_queries"
    assert blocked["blocked_or_skipped_actions"][RESOLVE_CONFLICT] == (
        "no_resolving_queries"
    )


def test_source_class_weak_corpus_and_conflict_dispatch_are_mutually_exclusive() -> None:
    packets = [
        _run(RECOVER_MISSING_SOURCE_CLASS),
        _run(RECOVER_WEAK_CORPUS),
        _run(RESOLVE_CONFLICT),
    ]

    for packet in packets:
        dispatched_names = [
            action
            for action, used in (
                (
                    RECOVER_MISSING_SOURCE_CLASS,
                    packet["source_class_executor_dispatched"],
                ),
                (RECOVER_WEAK_CORPUS, packet["weak_corpus_executor_dispatched"]),
                (RESOLVE_CONFLICT, packet["conflict_resolution_executor_dispatched"]),
            )
            if used
        ]
        assert dispatched_names == [packet["executed_action_name"]]


@pytest.mark.parametrize(
    "action_name",
    [
        "request_social_signal_check",
        "ask_user_clarification",
        "run_scrutineer_review",
    ],
)
def test_unpromoted_actions_do_not_dispatch_substitutes(action_name: str) -> None:
    packet = _run(action_name)

    assert packet["promoted_action_name"] is None
    assert packet["executed_action_name"] is None
    assert packet["gate_reason"] == "alternate_action_not_promoted"
    assert packet["source_class_executor_dispatched"] is False
    assert packet["weak_corpus_executor_dispatched"] is False
    assert packet["conflict_resolution_executor_dispatched"] is False


def test_checkpoint_selected_eligible_targeted_retrieval_is_explicitly_blocked() -> None:
    result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=_checkpoint(_RETRIEVE_TARGETED),
            source_class_lifecycle_trace=_source_lifecycle(),
            weak_corpus_lifecycle_trace=_weak_lifecycle(),
            conflict_resolution_lifecycle_trace=_conflict_lifecycle(),
            targeted_retrieval_lifecycle_trace=_targeted_lifecycle(),
        )
    )
    packet = result.trace_packet
    authorization = result.dispatch_authorization

    assert packet["promoted_action_name"] is None
    assert packet["executed_action_name"] is None
    assert authorization.authorized_action_name is None
    assert packet["blocked_or_skipped_actions"][_RETRIEVE_TARGETED] == (
        "blocked_by_runtime_dispatch_not_inverted"
    )
    assert packet["targeted_retrieval_gate_active"] is True
    assert packet["targeted_retrieval_gated_action"] == _RETRIEVE_TARGETED
    assert packet["targeted_retrieval_lifecycle_considered"] is True
    assert packet["targeted_retrieval_lifecycle_eligible"] is True
    assert packet["targeted_retrieval_lifecycle_blockers"] == []
    assert packet["targeted_retrieval_dispatch_authorized"] is False
    assert packet["targeted_retrieval_executor_dispatched"] is False
    assert packet["targeted_retrieval_gate_reason"] == (
        "blocked_by_runtime_dispatch_not_inverted"
    )
    assert packet["targeted_retrieval_runtime_dispatch_inverted"] is False
    assert result.targeted_retrieval_checkpoint_gate_trace[
        "targeted_retrieval_executor_dispatched"
    ] is False
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"executed_action_name": _RETRIEVE_TARGETED}
    ).authorized_action_name is None


def test_targeted_lifecycle_blocker_wins_over_runtime_dispatch_block() -> None:
    packet = _run(
        _RETRIEVE_TARGETED,
        targeted=_targeted_lifecycle(
            eligible=False,
            reason="blocked_by_currentness_gap",
        ),
    )

    assert packet["promoted_action_name"] is None
    assert packet["executed_action_name"] is None
    assert packet["blocked_or_skipped_actions"][_RETRIEVE_TARGETED] == (
        "blocked_by_currentness_gap"
    )
    assert packet["targeted_retrieval_lifecycle_eligible"] is False
    assert packet["targeted_retrieval_dispatch_authorized"] is False
    assert packet["targeted_retrieval_executor_dispatched"] is False


def test_non_selected_eligible_targeted_retrieval_is_checkpoint_not_approved() -> None:
    packet = _run(RECOVER_MISSING_SOURCE_CLASS)

    assert packet["executed_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["targeted_retrieval_lifecycle_eligible"] is True
    assert packet["blocked_or_skipped_actions"][_RETRIEVE_TARGETED] == (
        "checkpoint_action_not_approved"
    )
    assert packet["targeted_retrieval_gate_reason"] == (
        "checkpoint_action_not_approved"
    )
    assert packet["targeted_retrieval_executor_dispatched"] is False


@pytest.mark.parametrize(
    ("action_name", "expected_executed"),
    [
        (RECOVER_MISSING_SOURCE_CLASS, RECOVER_MISSING_SOURCE_CLASS),
        (RECOVER_WEAK_CORPUS, RECOVER_WEAK_CORPUS),
        (RESOLVE_CONFLICT, RESOLVE_CONFLICT),
        ("request_social_signal_check", None),
        ("run_scrutineer_review", None),
        ("ask_user_clarification", None),
    ],
)
def test_targeted_retrieval_does_not_substitute_for_other_checkpoint_actions(
    action_name: str,
    expected_executed: str | None,
) -> None:
    packet = _run(action_name)
    authorization = ControllerLoopDispatchAuthorization.from_trace_packet(packet)

    assert packet["executed_action_name"] == expected_executed
    assert authorization.authorized_action_name != _RETRIEVE_TARGETED
    assert packet["targeted_retrieval_dispatch_authorized"] is False
    assert packet["targeted_retrieval_executor_dispatched"] is False
    assert packet["blocked_or_skipped_actions"][_RETRIEVE_TARGETED] == (
        "checkpoint_action_not_approved"
    )


def test_ordinary_next_queries_never_become_conflict_resolving_queries() -> None:
    targeted = _targeted_lifecycle(
        queries=("ordinary background follow-up",),
        resolving_queries=("Care Program official corrected date",),
    )
    result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=_checkpoint(RESOLVE_CONFLICT),
            source_class_lifecycle_trace=_source_lifecycle(),
            weak_corpus_lifecycle_trace=_weak_lifecycle(),
            targeted_retrieval_lifecycle_trace=targeted,
            conflict_resolution_lifecycle_trace={
                "approved": False,
                "reason": "no_resolving_queries",
                "blockers": ["no_resolving_queries"],
                "active_conflict_resolution_considered": True,
                "ordinary_next_queries": ["ordinary background follow-up"],
            },
        )
    )
    packet = result.trace_packet

    assert result.input_facts.targeted_retrieval_lifecycle_trace[
        "targeted_retrieval_candidate_queries"
    ] == ["ordinary background follow-up"]
    assert result.input_facts.targeted_retrieval_lifecycle_trace[
        "targeted_retrieval_candidate_conflict_resolving_queries"
    ] == ["Care Program official corrected date"]
    assert result.input_facts.conflict_resolution_lifecycle_trace[
        "ordinary_next_queries"
    ] == ["ordinary background follow-up"]
    assert packet["conflict_resolution_executor_dispatched"] is False
    assert packet["executed_action_name"] is None
    assert packet["blocked_or_skipped_actions"][RESOLVE_CONFLICT] == (
        "no_resolving_queries"
    )


def test_blocked_targeted_lifecycle_is_represented_when_not_selected() -> None:
    packet = _run(
        RECOVER_WEAK_CORPUS,
        conflict=_conflict_lifecycle(),
        targeted=_targeted_lifecycle(
            eligible=False,
            reason="query_generation_required",
            queries=(),
        ),
    )

    assert packet["executed_action_name"] == RECOVER_WEAK_CORPUS
    assert packet["blocked_or_skipped_actions"][_RETRIEVE_TARGETED] == (
        "query_generation_required"
    )
    assert packet["targeted_retrieval_gate_reason"] == "query_generation_required"


def test_controller_loop_spine_static_import_guard() -> None:
    tree = ast.parse(_SPINE_PATH.read_text(encoding="utf-8"))
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.db",
        "core.llm",
        "core.model",
        "core.persistence",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.providers",
        "core.retrieval",
        "core.routing",
        "core.search_providers",
        "core.storage",
    )

    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

    violations = [
        name
        for name in imported_names
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]

    assert violations == []


def test_pipeline_orchestrator_does_not_define_competing_active_gate_builders() -> None:
    tree = ast.parse(_ORCHESTRATOR_PATH.read_text(encoding="utf-8"))
    forbidden_builder_names = {
        "_build_source_class_checkpoint_gate_trace",
        "_build_weak_corpus_checkpoint_gate_trace",
        "_build_conflict_resolution_checkpoint_gate_trace",
        "_build_terminal_stop_checkpoint_gate_trace",
        "_build_active_checkpoint_invariant_trace",
    }

    defined_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert defined_names.isdisjoint(forbidden_builder_names)
    assert {
        name for name in defined_names if "checkpoint_gate" in name
    } == set()


def test_pipeline_orchestrator_does_not_recompute_spine_promotion_state() -> None:
    source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_trace_keys = {
        "promoted_action_name",
        "executed_action_name",
        "executor_dispatched",
        "executor_dispatch_blocked",
        "source_class_executor_dispatched",
        "weak_corpus_executor_dispatched",
        "conflict_resolution_executor_dispatched",
        "terminal_stop_approved",
    }
    string_literals = {
        node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
    }

    assert "ControllerLoopActionCandidate" not in source
    assert string_literals.isdisjoint(forbidden_trace_keys)


def test_pipeline_orchestrator_keeps_source_class_runner_dispatch_canonical() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    runner_source = _SOURCE_CLASS_RECOVERY_RUNNER_PATH.read_text(encoding="utf-8")
    orchestrator_tree = ast.parse(orchestrator_source)

    def parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
        parent_by_node: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parent_by_node[child] = parent
        return parent_by_node

    orchestrator_parent_by_node = parent_map(orchestrator_tree)

    assert "execute_source_class_recovery_action(" not in orchestrator_source
    assert orchestrator_source.count("run_source_class_recovery_dispatch(") == 1

    def call_name(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def nearest_enclosing_if(
        node: ast.AST,
        parent_by_node: dict[ast.AST, ast.AST],
    ) -> ast.If | None:
        parent = parent_by_node.get(node)
        while parent is not None:
            if isinstance(parent, ast.If):
                return parent
            parent = parent_by_node.get(parent)
        return None

    def is_authorized_dispatch_test(test: ast.AST, action_name: str) -> bool:
        for node in ast.walk(test):
            if not isinstance(node, ast.Compare):
                continue
            left_is_authorization = (
                isinstance(node.left, ast.Name)
                and node.left.id == "authorized_spine_action"
            ) or (
                isinstance(node.left, ast.Attribute)
                and node.left.attr == "authorized_spine_action"
            )
            comparator_is_action = any(
                isinstance(comparator, ast.Name)
                and comparator.id == action_name
                for comparator in node.comparators
            )
            if left_is_authorization and comparator_is_action:
                return True
        return False

    def guarded_calls_for(
        tree: ast.AST,
        parent_by_node: dict[ast.AST, ast.AST],
        required_guards: dict[str, str],
    ) -> dict[str, bool]:
        guarded_calls: dict[str, bool] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = call_name(node)
            if name not in required_guards:
                continue
            enclosing_if = nearest_enclosing_if(node, parent_by_node)
            guarded_calls[name] = bool(
                enclosing_if
                and is_authorized_dispatch_test(
                    enclosing_if.test,
                    required_guards[name],
                )
            )
        return guarded_calls

    assert guarded_calls_for(
        orchestrator_tree,
        orchestrator_parent_by_node,
        {"execute_conflict_resolution_from_scope": "RESOLVE_CONFLICT"},
    ) == {"execute_conflict_resolution_from_scope": True}
    assert (
        "_canonical_source_class_recovery_dispatch_authorized(context.lifecycle_trace)"
        in runner_source
    )
    assert "authorized_spine_action" not in runner_source
    assert "authority_lifecycle.recovery_action" in runner_source


def test_pipeline_orchestrator_does_not_authorize_retrieve_targeted_dispatch() -> None:
    tree = ast.parse(_ORCHESTRATOR_PATH.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        left_is_authorized_spine_action = (
            isinstance(node.left, ast.Name)
            and node.left.id == "authorized_spine_action"
        )
        compares_to_retrieve_targeted = any(
            isinstance(comparator, ast.Constant)
            and comparator.value == _RETRIEVE_TARGETED
            for comparator in node.comparators
        )
        assert not (
            left_is_authorized_spine_action and compares_to_retrieve_targeted
        )


def test_dispatch_authorization_allowlist_excludes_retrieve_targeted() -> None:
    packet = _run(_RETRIEVE_TARGETED)
    authorization = ControllerLoopDispatchAuthorization.from_trace_packet(packet)

    assert packet["executed_action_name"] is None
    assert authorization.authorized_action_name is None
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"executed_action_name": _RETRIEVE_TARGETED}
    ).authorized_action_name is None
