from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from core.targeted_retrieval_controller import (
    TARGETED_RETRIEVAL_STAGE,
    TARGETED_RETRIEVAL_TRACE_FIELDS,
    TargetedRetrievalControllerDecision,
    build_targeted_retrieval_controller_input,
    build_targeted_retrieval_lifecycle,
    decide_targeted_retrieval,
    targeted_retrieval_lifecycle_defaults,
)

_ROOT = Path(__file__).resolve().parents[1]
_CONTROLLER_PATH = _ROOT / "core" / "targeted_retrieval_controller.py"


def _input(**overrides: Any) -> Any:
    values: dict[str, Any] = {
        "material_contract_gap_remaining": True,
        "material_contract_gap": "current corroboration missing",
        "approved_ordinary_next_queries": (
            "Acme current official update",
            "Acme current official update",
            "Acme independent corroboration",
        ),
        "query_provenance": "evaluator_next_queries",
        "query_generation_complete": True,
        "prior_queries": ("Acme overview",),
        "next_queries_redundant": False,
        "redundancy_status": "non_redundant",
        "redundancy_overlap": 0.2,
        "iteration": 1,
        "max_iterations": 3,
        "targeted_budget_remaining": 1,
        "metadata": {
            "safe": ("first", "second"),
            "raw_trace": "redacted",
        },
    }
    values.update(overrides)
    return build_targeted_retrieval_controller_input(**values)


@pytest.mark.parametrize(
    "provenance",
    [
        "evaluator_next_queries",
        "scout_directed_queries",
        "expander_component_queries",
    ],
)
def test_targeted_retrieval_approves_non_redundant_ordinary_queries(
    provenance: str,
) -> None:
    snapshot = _input(query_provenance=provenance)

    decision = decide_targeted_retrieval(snapshot)
    lifecycle = build_targeted_retrieval_lifecycle(snapshot)
    trace = lifecycle.to_trace_fields()

    assert decision.decision is (
        TargetedRetrievalControllerDecision.APPROVE_TARGETED_RETRIEVAL_CANDIDATE
    )
    assert decision.reason == "targeted_retrieval_candidate_available"
    assert decision.blockers == ()
    assert decision.ordinary_next_queries == (
        "Acme current official update",
        "Acme independent corroboration",
    )
    assert decision.query_provenance == provenance
    assert decision.stage == TARGETED_RETRIEVAL_STAGE
    assert trace["targeted_retrieval_candidate_eligible"] is True
    assert trace["targeted_retrieval_candidate_used"] is False
    assert trace["targeted_retrieval_candidate_stage"] == TARGETED_RETRIEVAL_STAGE
    assert set(trace) == set(TARGETED_RETRIEVAL_TRACE_FIELDS)


def test_targeted_retrieval_blocks_when_query_generation_is_required() -> None:
    decision = decide_targeted_retrieval(
        _input(
            query_generation_complete=False,
            approved_ordinary_next_queries=("Acme generated later",),
        )
    )

    assert decision.decision is TargetedRetrievalControllerDecision.BLOCKED_WITH_REASON
    assert decision.reason == "query_generation_required"
    assert "query_generation_required" in decision.blockers


def test_targeted_retrieval_blocks_provider_swap_and_depth_escalation() -> None:
    provider = decide_targeted_retrieval(
        _input(provider_policy_reusable=False, provider_swap_required=True)
    )
    depth = decide_targeted_retrieval(
        _input(
            search_depth_reusable=False,
            search_depth_escalation_required=True,
        )
    )

    assert provider.reason == "blocked_by_provider_policy_change_required"
    assert "blocked_by_provider_policy_change_required" in provider.blockers
    assert depth.reason == "blocked_by_search_depth_policy_change_required"
    assert "blocked_by_search_depth_policy_change_required" in depth.blockers


def test_targeted_retrieval_blocks_legal_source_repair_requirement() -> None:
    decision = decide_targeted_retrieval(
        _input(legal_source_repair_required=True)
    )

    assert decision.reason == "blocked_by_legal_source_repair_required"
    assert "blocked_by_legal_source_repair_required" in decision.blockers
    assert decision.approved is False


def test_targeted_retrieval_records_passive_currentness_source_fit_fields() -> None:
    snapshot = _input(
        currentness_gap_detected=True,
        official_current_source_gap=True,
        legal_or_regulatory_current_event_gap=True,
        reputable_news_or_primary_update_needed=True,
        final_answer_should_caveat_missing_current_source=True,
    )

    decision = decide_targeted_retrieval(snapshot)
    lifecycle = build_targeted_retrieval_lifecycle(snapshot)
    payload = lifecycle.to_dict()
    trace = lifecycle.to_trace_fields()

    assert decision.reason == "blocked_by_currentness_gap"
    assert "blocked_by_currentness_gap" in decision.blockers
    assert "blocked_by_official_current_source_gap" in decision.blockers
    assert "blocked_by_legal_or_regulatory_current_event_gap" in decision.blockers
    assert "blocked_by_reputable_news_or_primary_update_needed" in decision.blockers
    assert payload["snapshot"]["currentness_gap_detected"] is True
    assert payload["snapshot"]["official_current_source_gap"] is True
    assert payload["snapshot"]["legal_or_regulatory_current_event_gap"] is True
    assert payload["snapshot"]["reputable_news_or_primary_update_needed"] is True
    assert (
        payload["snapshot"]["final_answer_should_caveat_missing_current_source"]
        is True
    )
    assert trace["targeted_retrieval_candidate_currentness_gap_detected"] is True
    assert trace["targeted_retrieval_candidate_official_current_source_gap"] is True
    assert (
        trace[
            "targeted_retrieval_candidate_legal_or_regulatory_current_event_gap"
        ]
        is True
    )
    assert (
        trace[
            "targeted_retrieval_candidate_reputable_news_or_primary_update_needed"
        ]
        is True
    )
    assert (
        trace[
            "targeted_retrieval_candidate_final_answer_should_caveat_missing_current_source"
        ]
        is True
    )
    assert trace["targeted_retrieval_candidate_used"] is False
    assert set(trace) == set(TARGETED_RETRIEVAL_TRACE_FIELDS)


@pytest.mark.parametrize(
    ("flag", "blocker"),
    [
        ("source_class_recovery_owns_path", "blocked_by_source_class_recovery"),
        ("weak_corpus_recovery_owns_path", "blocked_by_weak_corpus_recovery"),
        ("conflict_resolution_owns_path", "blocked_by_conflict_resolution"),
    ],
)
def test_targeted_retrieval_blocks_recovery_and_conflict_ownership(
    flag: str,
    blocker: str,
) -> None:
    decision = decide_targeted_retrieval(_input(**{flag: True}))

    assert decision.reason == blocker
    assert blocker in decision.blockers
    assert decision.approved is False


@pytest.mark.parametrize(
    ("flag", "blocker"),
    [
        ("terminal_stop_owns_path", "blocked_by_terminal_stop"),
        ("social_signal_owns_path", "blocked_by_social_signal"),
        ("scrutineer_owns_path", "blocked_by_scrutineer"),
        ("clarification_owns_path", "blocked_by_clarification"),
    ],
)
def test_targeted_retrieval_blocks_other_higher_priority_ownership(
    flag: str,
    blocker: str,
) -> None:
    decision = decide_targeted_retrieval(_input(**{flag: True}))

    assert decision.reason == blocker
    assert blocker in decision.blockers
    assert decision.approved is False


def test_targeted_retrieval_blocks_redundant_budget_wrong_phase_and_prior_attempt() -> None:
    redundant = decide_targeted_retrieval(
        _input(next_queries_redundant=True, redundancy_overlap=0.91)
    )
    exhausted = decide_targeted_retrieval(
        _input(iteration=3, max_iterations=3, targeted_budget_remaining=1)
    )
    wrong_phase = decide_targeted_retrieval(_input(lifecycle_phase="author"))
    attempted = decide_targeted_retrieval(_input(prior_attempted_for_gap=True))

    assert redundant.reason == "redundant_with_prior_queries"
    assert exhausted.reason == "blocked_by_iteration_budget"
    assert wrong_phase.reason == "blocked_by_wrong_phase"
    assert attempted.reason == "already_attempted_for_gap"


def test_targeted_retrieval_blocks_no_gap_no_queries_and_bad_provenance() -> None:
    no_gap = decide_targeted_retrieval(
        _input(material_contract_gap_remaining=False)
    )
    no_queries = decide_targeted_retrieval(
        _input(approved_ordinary_next_queries=())
    )
    bad_provenance = decide_targeted_retrieval(
        _input(query_provenance="conflict_resolution")
    )

    assert no_gap.decision is TargetedRetrievalControllerDecision.NO_ACTION
    assert no_gap.reason == "no_material_contract_gap"
    assert no_queries.reason == "no_approved_queries"
    assert bad_provenance.reason == "query_provenance_not_allowed"


def test_ordinary_next_queries_never_become_conflict_resolving_queries() -> None:
    snapshot = _input(
        approved_ordinary_next_queries=("Acme ordinary follow-up",),
        conflict_resolving_queries=(),
    )

    decision = decide_targeted_retrieval(snapshot)
    payload = decision.to_dict()
    trace = build_targeted_retrieval_lifecycle(snapshot).to_trace_fields()

    assert decision.approved is True
    assert payload["ordinary_next_queries"] == ["Acme ordinary follow-up"]
    assert payload["conflict_resolving_queries"] == []
    assert trace["targeted_retrieval_candidate_queries"] == [
        "Acme ordinary follow-up"
    ]
    assert trace["targeted_retrieval_candidate_conflict_resolving_queries"] == []


def test_targeted_retrieval_json_safety_and_metadata_sanitization() -> None:
    blocked_a = "_".join(("api", "key"))
    snapshot = _input(
        metadata={
            blocked_a: "secret-value",
            "provider_payload": {"body": "provider body"},
            "raw_prompt": "raw prompt body",
            "safe_key": "safe value",
            "nested": {
                "raw_trace": ["raw trace"],
                "safe_nested_key": {"second", "first"},
            },
        }
    )
    lifecycle = build_targeted_retrieval_lifecycle(snapshot)
    payload = lifecycle.to_dict()

    assert payload["snapshot"]["metadata"] == {
        "safe_key": "safe value",
        "nested": {"safe_nested_key": ["first", "second"]},
    }
    assert payload["candidate"]["metadata"] == payload["snapshot"]["metadata"]
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload


def test_targeted_retrieval_trace_defaults_are_passive() -> None:
    defaults = targeted_retrieval_lifecycle_defaults()

    assert defaults["targeted_retrieval_candidate_considered"] is False
    assert defaults["targeted_retrieval_candidate_eligible"] is False
    assert defaults["targeted_retrieval_candidate_used"] is False
    assert defaults["targeted_retrieval_candidate_reason"] == "not_evaluated"
    assert defaults["targeted_retrieval_candidate_queries"] == []
    assert defaults["targeted_retrieval_candidate_stage"] is None
    assert set(defaults) == set(TARGETED_RETRIEVAL_TRACE_FIELDS)


def test_targeted_retrieval_controller_static_import_guard() -> None:
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
        "core.researcher",
        "core.author",
        "core.output_validation",
        "core.run_controller",
    )
    forbidden_terms = (
        "ask_model",
        "process_search_queries",
        "select_providers",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "choose_retrieval_search_depth",
        "DEFAULT_SYSTEM",
        "ControllerLoop",
        "RetrievalAction",
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
