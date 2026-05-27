from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.conflict_resolution_controller import (
    CONFLICT_RESOLUTION_PROVIDER_ROLE,
    ConflictResolutionControllerDecision,
    build_conflict_resolution_controller_input,
    build_conflict_resolution_lifecycle,
    conflict_resolution_lifecycle_defaults,
    decide_conflict_resolution,
)

_ROOT = Path(__file__).resolve().parents[1]
_CONTROLLER_PATH = _ROOT / "core" / "conflict_resolution_controller.py"


def _input(**overrides: Any) -> Any:
    values: dict[str, Any] = {
        "conflicts_present": True,
        "conflict_notes": ("official date conflicts with media date",),
        "resolving_queries": (
            "Acme official launch date correction",
            "Acme official launch date correction",
            "Acme regulator launch date filing",
        ),
        "ordinary_next_queries": ("Acme launch date background",),
        "current_search_depth": "basic",
        "iteration_budget_available": True,
        "prior_attempt_count": 0,
        "metadata": {
            "raw_prompt": "must not be used by tests",
            "raw_trace": "must not be used by tests",
        },
    }
    values.update(overrides)
    return build_conflict_resolution_controller_input(**values)


def test_conflict_resolution_controller_approves_bounded_resolving_queries() -> None:
    snapshot = _input()

    decision = decide_conflict_resolution(snapshot)
    lifecycle = build_conflict_resolution_lifecycle(snapshot)
    trace = lifecycle.to_trace_fields()

    assert decision.decision is (
        ConflictResolutionControllerDecision.RUN_CONFLICT_RESOLUTION
    )
    assert decision.reason == "material_conflict_resolution_available"
    assert decision.blockers == ()
    assert decision.queries == (
        "Acme official launch date correction",
        "Acme regulator launch date filing",
    )
    assert decision.provider_role == CONFLICT_RESOLUTION_PROVIDER_ROLE
    assert decision.search_depth == "basic"
    assert decision.attempt_count == 1
    assert trace["active_conflict_resolution_considered"] is True
    assert trace["active_conflict_resolution_eligible"] is True
    assert trace["active_conflict_resolution_used"] is False
    assert trace["active_conflict_resolution_provider_role"] == (
        CONFLICT_RESOLUTION_PROVIDER_ROLE
    )
    assert trace["active_conflict_resolution_stage"] == "conflict_resolution"


def test_conflict_resolution_controller_returns_no_action_without_conflict() -> None:
    decision = decide_conflict_resolution(
        _input(conflicts_present=False, resolving_queries=())
    )

    assert decision.decision is ConflictResolutionControllerDecision.NO_ACTION
    assert decision.reason == "no_conflict"
    assert decision.provider_role is None
    assert decision.search_depth is None
    assert decision.attempt_count == 0


def test_ordinary_next_queries_do_not_become_resolving_queries() -> None:
    snapshot = _input(
        conflicts_present=True,
        resolving_queries=(),
        ordinary_next_queries=("Acme ordinary follow-up query",),
    )

    decision = decide_conflict_resolution(snapshot)

    assert snapshot.to_dict()["ordinary_next_query_count"] == 1
    assert snapshot.resolving_queries == ()
    assert decision.decision is (
        ConflictResolutionControllerDecision.BLOCKED_WITH_REASON
    )
    assert decision.reason == "no_resolving_queries"
    assert decision.queries == ()


def test_conflict_resolution_snapshot_metadata_omits_sensitive_keys() -> None:
    blocked_a = "_".join(("api", "key"))
    blocked_b = "sec" + "ret"
    snapshot = _input(
        metadata={
            blocked_a: "redacted",
            "provider_payload": {"body": "provider body"},
            "raw_provider_payload": {"body": "raw provider body"},
            "raw_prompt": "raw prompt body",
            "raw_trace": ["raw trace entry"],
            "safe_key": "safe value",
            blocked_b: "redacted",
            "token": "token-value",
            "nested": {
                "raw_prompt": "nested raw prompt body",
                "safe_nested_key": ("first", "second"),
                "token": "nested-token",
            },
        }
    )

    metadata = snapshot.to_dict()["metadata"]

    assert metadata == {
        "safe_key": "safe value",
        "nested": {"safe_nested_key": ["first", "second"]},
    }


def test_conflict_resolution_blocks_already_attempted_and_budget_unavailable() -> None:
    already = decide_conflict_resolution(_input(prior_attempt_count=1))
    exhausted = decide_conflict_resolution(_input(iteration_budget_available=False))

    assert already.decision is ConflictResolutionControllerDecision.BLOCKED_WITH_REASON
    assert already.reason == "already_attempted"
    assert "already_attempted" in already.blockers
    assert already.attempt_count == 1
    assert exhausted.decision is ConflictResolutionControllerDecision.BLOCKED_WITH_REASON
    assert exhausted.reason == "blocked_by_iteration_budget"
    assert "blocked_by_iteration_budget" in exhausted.blockers


def test_conflict_resolution_blocks_provider_or_depth_policy_change() -> None:
    provider = decide_conflict_resolution(
        _input(provider_policy_reusable=False, provider_swap_required=True)
    )
    depth = decide_conflict_resolution(
        _input(search_depth_reusable=False, search_depth_escalation_required=True)
    )

    assert provider.reason == "blocked_by_provider_policy_change_required"
    assert "blocked_by_provider_policy_change_required" in provider.blockers
    assert depth.reason == "blocked_by_search_depth_policy_change_required"
    assert "blocked_by_search_depth_policy_change_required" in depth.blockers


def test_conflict_resolution_blocks_wrong_author_and_post_analyst_phases() -> None:
    wrong = decide_conflict_resolution(_input(lifecycle_phase="scout"))
    author = decide_conflict_resolution(_input(lifecycle_phase="author"))
    post = decide_conflict_resolution(_input(lifecycle_phase="post_analyst"))

    assert wrong.reason == "blocked_by_wrong_phase"
    assert "blocked_by_wrong_phase" in wrong.blockers
    assert author.reason == "blocked_by_wrong_phase"
    assert "blocked_by_author_phase" in author.blockers
    assert post.reason == "blocked_by_wrong_phase"
    assert "blocked_by_post_analyst_phase" in post.blockers


def test_conflict_resolution_trace_defaults_are_passive_and_json_safe() -> None:
    defaults = conflict_resolution_lifecycle_defaults()

    assert defaults["active_conflict_resolution_considered"] is False
    assert defaults["active_conflict_resolution_eligible"] is False
    assert defaults["active_conflict_resolution_used"] is False
    assert defaults["active_conflict_resolution_reason"] == "not_evaluated"
    assert defaults["active_conflict_resolution_queries"] == []
    assert defaults["active_conflict_resolution_provider_role"] is None
    assert defaults["active_conflict_resolution_attempt_count"] == 0


def test_conflict_resolution_controller_static_import_guard() -> None:
    tree = ast.parse(_CONTROLLER_PATH.read_text(encoding="utf-8"))
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.llm",
        "core.prompts",
        "core.search_providers",
        "core.db",
        "core.storage",
        "core.run_logging",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.routing",
        "core.scout",
        "core.run_controller",
    )
    forbidden_terms = (
        "ask_model",
        "process_search_queries",
        "select_providers",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "os.environ",
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
    source = _CONTROLLER_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
