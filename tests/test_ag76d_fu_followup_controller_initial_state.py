from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from core.followup import MemorySearchResult, build_followup_diagnostics, run_followup
from core.followup_initial_state_contract import (
    FOLLOWUP_INITIAL_STATE_TRACE_KEY,
    FollowUpInitialControllerState,
    build_followup_initial_controller_state,
    execute_followup_initial_state_handoff,
)
from tests.test_ag61a_followup_source_obligation_refresh import (
    CONCEPT_PASSAGE,
    FRESH_OFFICIAL_PASSAGE,
    FU_PARAMS,
    OFFICIAL_RULE_PASSAGE,
    SECONDARY_RULE_PASSAGE,
    _Harness,
    _session,
)

_ROOT = Path(__file__).resolve().parents[1]


def _run(query: str, passages: tuple[dict, ...], *, evaluator_output: str = '{"can_answer": true}'):
    harness = _Harness(evaluator_output=evaluator_output, search_passages=(FRESH_OFFICIAL_PASSAGE,))
    from core.followup import FollowUpDeps
    from core.prompts import DEFAULT_SYSTEM

    deps = FollowUpDeps(
        embed_texts=harness.embed_texts,
        compute_similarities=harness.compute_similarities,
        search_fn=harness.search_fn,
        ask_model=harness.ask_model,
        clean_json_response=lambda value: value,
        synthesis_model_fn=harness.synthesis_model_fn,
    )
    result = run_followup(
        query=query,
        session=_session(passages),
        deps=deps,
        current_date="2026-06-01",
        follow_complexity="medium",
        fu_params=FU_PARAMS,
        intent="general",
        include_domains=[],
        exclude_domains=[],
        embed_provider="SyntheticEmbeddings",
        embed_model="synthetic-embedding-model",
        fast_provider="SyntheticEvaluator",
        fast_model="synthetic-evaluator-model",
        local_url="",
        api_key="",
        use_reasoning=False,
        chat_evaluator_prompt=DEFAULT_SYSTEM["chat_evaluator"],
        is_plausible_domain=lambda _url: True,
    )
    return result, harness


def test_contract_exposes_controller_owned_prior_refs_and_upstream_contract_refs() -> None:
    state = build_followup_initial_controller_state(
        query="Summarize that in one sentence.",
        session={
            "report": "Prior saved report.",
            "top_passages": [CONCEPT_PASSAGE],
            "session_id": "session-1",
            "last_run_id": "run-1",
            "answer_contract_ref": {"schema_version": "answer-contract-test", "status": "partial"},
            "controller_ledger_ref": {"route": "balanced", "ledger_id": "ledger-1"},
            "controller_posture": {"posture": "partial_answer"},
        },
    )
    trace = state.to_trace()

    assert isinstance(state, FollowUpInitialControllerState)
    assert trace["schema_version"] == "AG76D-FU.v1"
    assert trace["controller_owned"] is True
    assert trace["prior_report"]["available"] is True
    assert trace["prior_report"]["session_id"] == "session-1"
    assert trace["prior_evidence"]["prior_evidence_count"] == 1
    assert trace["prior_evidence"]["prior_ledger_ref"]["ledger_id"] == "ledger-1"
    assert trace["prior_answer_contract"]["prior_answer_contract_available"] is True
    assert trace["prior_answer_contract"]["prior_posture_available"] is True
    assert trace["saved_context_reuse"]["saved_context_reuse_decision"] == "reuse_as_sufficient_context"
    assert trace["closed_surface_non_changes"] == {
        "provider_search_query_behavior_changed": False,
        "author_final_answer_citation_behavior_changed": False,
        "economist_behavior_changed": False,
        "scrutineer_behavior_changed": False,
        "db_session_schema_changed": False,
        "cache_behavior_changed": False,
        "live_behavior_changed": False,
    }


def test_simple_followup_reuses_saved_context_without_new_stronger_obligation() -> None:
    result, harness = _run("Summarize the saved finding in one sentence.", (CONCEPT_PASSAGE,))
    trace = result.memory_result.followup_initial_state_trace

    assert result.memory_result.needs_search is False
    assert harness.search_calls == []
    assert result.memory_result.saved_context_reuse_decision == "reuse_as_sufficient_context"
    assert trace["new_stronger_obligation"]["new_stronger_obligation_detected"] is False
    assert trace["saved_context_reuse"]["saved_context_reuse_decision"] == "reuse_as_sufficient_context"


def test_new_stronger_obligation_is_detected_and_refreshes_saved_context() -> None:
    state = build_followup_initial_controller_state(
        query="What is the current official eligibility threshold?",
        session={"report": "Prior report", "top_passages": [SECONDARY_RULE_PASSAGE]},
    )
    handoff = execute_followup_initial_state_handoff(
        state=state,
        prompt="What is the current official eligibility threshold?",
        needs_search=False,
        followup_queries=[],
        max_queries=3,
    )
    trace = state.to_trace()

    assert handoff.needs_search is True
    assert handoff.required_source_classes == ("official_current_rules",)
    assert handoff.source_obligation_status == "saved_context_insufficient"
    assert handoff.saved_context_reuse_decision == "reuse_as_background_only"
    assert trace["new_stronger_obligation"]["new_stronger_obligation_detected"] is True
    assert trace["new_stronger_obligation"]["new_stronger_obligation_types"] == ["official_current"]
    assert trace["prompt_context"]["prompt_context_requires_refreshed_obligations"] is True


def test_saved_context_can_satisfy_stronger_obligation_when_required_source_class_present() -> None:
    result, harness = _run("What is the current official eligibility threshold?", (OFFICIAL_RULE_PASSAGE,))
    trace = result.memory_result.followup_initial_state_trace

    assert result.memory_result.needs_search is False
    assert harness.search_calls == []
    assert result.memory_result.source_obligation_status == "saved_context_sufficient"
    assert result.memory_result.saved_context_reuse_decision == "reuse_as_sufficient_context"
    assert trace["refreshed_source_obligations"]["refreshed_source_obligations"] is True
    assert trace["saved_context_reuse"]["saved_context_source_sufficient"] is True


def test_prompt_context_uses_controller_initial_state_and_trace_visibility() -> None:
    result, harness = _run("What is the current official eligibility threshold?", (SECONDARY_RULE_PASSAGE,))
    prompt = result.synthesis_result.prompt_used
    trace = result.memory_result.followup_initial_state_trace
    diagnostics = build_followup_diagnostics(
        memory_result=result.memory_result,
        web_result=result.web_result,
        synthesis_result=result.synthesis_result,
        source_cards=[],
        prompt="What is the current official eligibility threshold?",
    )

    assert harness.search_calls
    assert "Controller-owned follow-up initial state treats saved context as background only" in prompt
    assert "Saved-context decision: reuse_as_background_only" in prompt
    assert trace["prompt_context"]["prompt_context_hash"]
    assert trace["prompt_context"]["prompt_context_length"] == len(prompt)
    assert trace["trace_visibility"]["prior_context_reuse_visible"] is True
    assert diagnostics["saved_context_reuse_decision"] == "reuse_as_background_only"
    assert diagnostics[FOLLOWUP_INITIAL_STATE_TRACE_KEY]["new_stronger_obligation"][
        "new_stronger_obligation_detected"
    ] is True


def test_memory_result_shape_is_additive_and_closed_surfaces_are_not_claimed_changed() -> None:
    names = [field.name for field in fields(MemorySearchResult)]

    assert names[-2:] == ["saved_context_reuse_decision", "followup_initial_state_trace"]
    assert "source_obligation_note" in names
    state = build_followup_initial_controller_state(query="What changed?", session={})
    closed = state.to_trace()["closed_surface_non_changes"]
    assert all(value is False for value in closed.values())


def test_static_protected_import_guard_for_contract() -> None:
    source = (_ROOT / "core" / "followup_initial_state_contract.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden = {
        "core.pipeline_orchestrator",
        "core.pipeline",
        "core.providers",
        "core.search",
        "core.economist_handoff_contract",
        "core.citation_source_handoff_contract",
        "core.analyst_author_handoff_contract",
        "core.scrutineer",
        "sqlite3",
        "requests",
        "httpx",
        "openai",
    }
    assert forbidden.isdisjoint(imported_modules)
    assert "def build_followup_initial_controller_state" in source
    assert "def execute_followup_initial_state_handoff" in source


def test_orchestrator_session_authority_guard_keeps_sufficiency_out_of_orchestrator() -> None:
    orchestrator_source = (_ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")
    followup_source = (_ROOT / "core" / "followup.py").read_text(encoding="utf-8")

    assert "saved_context_satisfies_required_classes" not in orchestrator_source
    assert "source_obligation_status = (" not in orchestrator_source
    assert "build_followup_initial_controller_state" in followup_source
    assert "execute_followup_initial_state_handoff" in followup_source
    assert "Legacy-compatible wrapper around Controller-owned follow-up state" in followup_source
