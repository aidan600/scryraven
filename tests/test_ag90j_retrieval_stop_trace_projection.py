from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from core import retrieval_stop_trace_projection as projection
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    RetrievalStopDecision,
)


def test_active_stop_decision_trace_exact_dict() -> None:
    telemetry = projection.build_retrieval_stop_active_stop_no_queries_telemetry(
        stage="evaluator_no_queries",
        evaluator_sufficient=False,
        iteration=1,
        max_iterations=3,
        prior_queries=["Acme Widget rollout evidence"],
        next_queries=[],
        query_source="evaluator",
        shadow_telemetry={
            "retrieval_stop_shadow_available": True,
            "retrieval_stop_shadow_decision": "stop_no_queries",
        },
    )

    assert telemetry == {
        "retrieval_stop_active_available": True,
        "retrieval_stop_active_action_name": "stop_insufficient_with_caveat",
        "retrieval_stop_active_authority": "active",
        "retrieval_stop_active_decision": "stop_no_queries",
        "retrieval_stop_active_reason": "no_new_queries",
        "retrieval_stop_active_terminal_branch_reason": "no_new_queries",
        "retrieval_stop_active_blockers": ["no_new_queries"],
        "retrieval_stop_active_next_query_count": 0,
        "retrieval_stop_active_approved_query_count": 0,
        "retrieval_stop_active_stage": "evaluator_no_queries",
        "retrieval_stop_active_mode": "active_stop_no_queries",
        "retrieval_stop_active_final_answer_posture": "answer with caveats",
        "retrieval_stop_active_ag28_candidate": (
            "ag28:stop_insufficient_with_caveat:terminal_no_query_or_budget_exhausted"
        ),
        "retrieval_stop_active_shadow_alignment": "aligned",
        "retrieval_stop_active_fallback_reason": None,
    }


def test_continue_decision_trace_projection_exact_dict() -> None:
    decision = RetrievalStopDecision(
        decision=RetrievalStopControllerDecision.CONTINUE_RETRIEVAL,
        reason="candidate_queries_available",
        next_queries=("Acme Widget migration timeline",),
        query_source="evaluator",
    )

    trace = projection.build_retrieval_stop_trace_projection(
        decision=decision,
        stage="evaluator",
        evaluator_sufficient=False,
        iteration=1,
        max_iterations=3,
        prior_queries=["Acme Widget rollout evidence"],
        next_queries=["Acme Widget migration timeline"],
        query_source="evaluator",
    )

    assert trace == {
        "retrieval_stop_shadow_telemetry": {
            "retrieval_stop_shadow_available": True,
            "retrieval_stop_shadow_decision": "continue_retrieval",
            "retrieval_stop_shadow_reason": "candidate_queries_available",
            "retrieval_stop_shadow_blockers": [],
            "retrieval_stop_shadow_next_query_count": 1,
            "retrieval_stop_shadow_alignment": "aligned",
            "retrieval_stop_shadow_stage": "evaluator",
            "retrieval_stop_shadow_mode": "shadow_only",
        },
        "ordinary_continuation_candidate_trace": {
            "considered": True,
            "eligible": True,
            "reason": "ordinary_continuation_candidate_available",
            "blockers": [],
            "ordinary_next_queries": ["Acme Widget migration timeline"],
            "query_provenance": "evaluator_next_queries",
            "prior_queries": ["Acme Widget rollout evidence"],
            "prior_query_count": 1,
            "conflict_resolving_queries": [],
            "source_path": "evaluator_next_queries",
            "current_iteration": 1,
            "max_iterations": 3,
            "can_be_future_retrieve_targeted_candidate": True,
            "currently_spine_authorized": False,
            "used": False,
        },
    }


def test_stop_due_to_no_queries_and_exhausted_budget_exact_dicts() -> None:
    no_queries = projection.build_retrieval_stop_shadow_telemetry(
        actual_decision="stop_no_queries",
        stage="evaluator_no_queries",
        evaluator_sufficient=False,
        iteration=1,
        max_iterations=3,
        prior_queries=["Acme Widget rollout evidence"],
        next_queries=[],
        query_source="evaluator",
    )
    budget = projection.build_retrieval_stop_active_stop_budget_exhausted_telemetry(
        stage="iteration_budget_exhausted",
        evaluator_sufficient=False,
        iteration=2,
        max_iterations=2,
        prior_queries=["Acme Widget rollout evidence"],
        next_queries=["Acme Widget official follow up"],
        query_source="budget",
        shadow_telemetry={
            "retrieval_stop_shadow_available": True,
            "retrieval_stop_shadow_decision": "stop_budget_exhausted",
        },
    )

    assert no_queries == {
        "retrieval_stop_shadow_available": True,
        "retrieval_stop_shadow_decision": "stop_no_queries",
        "retrieval_stop_shadow_reason": "no_new_queries",
        "retrieval_stop_shadow_blockers": ["no_new_queries"],
        "retrieval_stop_shadow_next_query_count": 0,
        "retrieval_stop_shadow_alignment": "aligned",
        "retrieval_stop_shadow_stage": "evaluator_no_queries",
        "retrieval_stop_shadow_mode": "shadow_only",
    }
    assert budget == {
        "retrieval_stop_active_available": True,
        "retrieval_stop_active_action_name": "stop_insufficient_with_caveat",
        "retrieval_stop_active_authority": "active",
        "retrieval_stop_active_decision": "stop_budget_exhausted",
        "retrieval_stop_active_reason": "iteration_budget_exhausted",
        "retrieval_stop_active_terminal_branch_reason": "iteration_budget_exhausted",
        "retrieval_stop_active_blockers": ["iteration_budget_exhausted"],
        "retrieval_stop_active_next_query_count": 1,
        "retrieval_stop_active_approved_query_count": 0,
        "retrieval_stop_active_stage": "iteration_budget_exhausted",
        "retrieval_stop_active_mode": "active_stop_budget_exhausted",
        "retrieval_stop_active_final_answer_posture": "answer with caveats",
        "retrieval_stop_active_ag28_candidate": (
            "ag28:stop_insufficient_with_caveat:terminal_no_query_or_budget_exhausted"
        ),
        "retrieval_stop_active_shadow_alignment": "aligned",
        "retrieval_stop_active_fallback_reason": None,
    }


def test_shadow_telemetry_only_defaults_and_alignment_projection() -> None:
    defaults = projection.retrieval_stop_shadow_defaults()
    mismatch = projection.build_retrieval_stop_alignment_projection(
        active_decision="stop_budget_exhausted",
        shadow_telemetry={
            "retrieval_stop_shadow_available": True,
            "retrieval_stop_shadow_decision": "continue_retrieval",
        },
    )

    assert defaults == {
        "retrieval_stop_shadow_available": False,
        "retrieval_stop_shadow_decision": None,
        "retrieval_stop_shadow_reason": None,
        "retrieval_stop_shadow_blockers": [],
        "retrieval_stop_shadow_next_query_count": 0,
        "retrieval_stop_shadow_alignment": None,
        "retrieval_stop_shadow_stage": None,
        "retrieval_stop_shadow_mode": "shadow_only",
    }
    assert mismatch == "mismatch"
    assert projection.build_retrieval_stop_alignment_projection(
        active_decision="stop_no_queries",
        shadow_telemetry={"retrieval_stop_shadow_available": False},
    ) == "shadow_unavailable"


def test_ordinary_continuation_trace_projection_exact_dict() -> None:
    evidence_state = SimpleNamespace(
        next_queries=("fallback query",),
        prior_queries=("fallback prior",),
        resolving_queries=("fallback resolving",),
    )

    trace = projection.build_ordinary_continuation_trace_projection(
        existing_candidate_trace={
            "source_path": "evaluator_next_queries",
            "ordinary_next_queries": ["Acme Widget support matrix"],
            "prior_queries": ["Acme Widget rollout evidence"],
            "blockers": ["not_evaluated"],
            "current_iteration": 1,
            "max_iterations": 3,
        },
        evidence_state=evidence_state,
        compact_runtime_strings_fn=_compact_runtime_strings,
        conflict_resolving_queries=["Acme Widget conflict check"],
    )

    assert trace == {
        "considered": True,
        "eligible": True,
        "reason": "ordinary_continuation_candidate_available",
        "blockers": [],
        "ordinary_next_queries": ["Acme Widget support matrix"],
        "query_provenance": "evaluator_next_queries",
        "prior_queries": ["Acme Widget rollout evidence"],
        "prior_query_count": 1,
        "conflict_resolving_queries": ["Acme Widget conflict check"],
        "source_path": "evaluator_next_queries",
        "current_iteration": 1,
        "max_iterations": 3,
        "can_be_future_retrieve_targeted_candidate": True,
        "currently_spine_authorized": False,
        "used": False,
    }


def test_projection_helper_static_seam_guard() -> None:
    helper_path = Path("core/retrieval_stop_trace_projection.py")
    source = helper_path.read_text()
    tree = ast.parse(source)
    imported_modules = {
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    } | {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    forbidden_import_fragments = (
        "provider",
        "search_providers",
        "prompts",
        "citation",
        "final_evidence",
        "persistence",
        "db",
        "cache",
        "runtime_prompt",
    )
    forbidden_calls = {
        "ask_model",
        "process_search_queries",
        "select_providers",
        "embed_texts",
        "build_final_evidence_bundle",
        "attach_author_evidence",
        "execute_persistence_side_effects",
        "record_final_evidence_snapshot",
        "build_author_prompt_from_scope",
        "globals",
        "locals",
    }

    assert not any(
        fragment in module
        for module in imported_modules
        for fragment in forbidden_import_fragments
    )
    assert "{**globals(), **locals()}" not in source
    assert "globals()" not in source
    assert "locals()" not in source
    assert not {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } & forbidden_calls


def _compact_runtime_strings(
    values: Any, *, max_items: int = 8, max_len: int = 180
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    iterable = values if isinstance(values, (list, tuple, set, frozenset)) else []
    for item in iterable:
        text = " ".join(str(item or "").strip().split())[:max_len]
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
        if len(out) >= max_items:
            break
    return out
