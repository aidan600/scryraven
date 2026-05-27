from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import (
    STOP_INSUFFICIENT_WITH_CAVEAT,
    ControllerActionAuthority,
)
from core.cost_accounting import CostAccumulator
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    RetrievalStopDecision,
)
from core.run_config import RunConfig, RunDeps
from tests.test_weak_corpus_recovery import _run as _run_weak_corpus_case

SHADOW_FIELDS = {
    "retrieval_stop_shadow_available",
    "retrieval_stop_shadow_decision",
    "retrieval_stop_shadow_reason",
    "retrieval_stop_shadow_blockers",
    "retrieval_stop_shadow_next_query_count",
    "retrieval_stop_shadow_alignment",
    "retrieval_stop_shadow_stage",
    "retrieval_stop_shadow_mode",
}

ACTIVE_FIELDS = {
    "retrieval_stop_active_available",
    "retrieval_stop_active_action_name",
    "retrieval_stop_active_authority",
    "retrieval_stop_active_decision",
    "retrieval_stop_active_reason",
    "retrieval_stop_active_terminal_branch_reason",
    "retrieval_stop_active_blockers",
    "retrieval_stop_active_next_query_count",
    "retrieval_stop_active_approved_query_count",
    "retrieval_stop_active_stage",
    "retrieval_stop_active_mode",
    "retrieval_stop_active_final_answer_posture",
    "retrieval_stop_active_ag28_candidate",
    "retrieval_stop_active_shadow_alignment",
    "retrieval_stop_active_fallback_reason",
}

LEAK_MARKERS = (
    "retrieval_stop_shadow",
    "retrieval_stop_active",
    "retrieval_stop_controller",
    "proceed_to_synthesis",
    "continue_retrieval",
    "stop_no_queries",
    "stop_redundant_queries",
    "stop_budget_exhausted",
    "stop_after_recovery",
    "active_stop_no_queries",
    "active_stop_budget_exhausted",
    "no_new_queries",
    "iteration_budget_exhausted",
    "unexpected_controller_decision",
    "controller_diagnostics",
    "planned_vs_observed",
    "quantitative_packet",
    "economist_v1",
    "ECONOMIST FRAMEWORK",
    "Author internals",
)


def _long_report() -> str:
    return (
        "Acme Widget rollout evidence supports a concise answer about the requested "
        "product context. The retrieved snippets are synthetic but on topic, citing "
        "release timing, adoption notes, and customer-facing rollout details. This "
        "offline report remains deliberately plain so tests can compare output without "
        "live search or model calls. It avoids diagnostic labels and focuses only on "
        "the answer content that a user should see."
    )


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "BRAVE_API_KEY",
        "TAVILY_API_KEY",
        "LINKUP_API_KEY",
        "EXA_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


class _ShadowHarness:
    def __init__(
        self,
        tmp_path: Path,
        *,
        query: str = "Summarize Acme Widget rollout evidence",
        core_topic: str = "Acme Widget rollout evidence",
        primary_entity: str = "Acme Widget",
        researcher_query: str = "Acme Widget rollout evidence",
        evaluator_responses: list[dict[str, Any]] | None = None,
    ) -> None:
        self.tmp_path = tmp_path
        self.query = query
        self.core_topic = core_topic
        self.primary_entity = primary_entity
        self.researcher_query = researcher_query
        self.evaluator_responses = list(
            evaluator_responses
            if evaluator_responses is not None
            else [{"is_sufficient": True, "new_queries": []}]
        )
        self.search_calls: list[dict[str, Any]] = []
        self.model_stage_calls: list[str] = []
        self.author_prompts: list[str] = []
        self.analyst_calls = 0

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        stage = self._stage_for(system_prompt, kwargs)
        self.model_stage_calls.append(stage)
        if system_prompt == DEFAULT_SYSTEM["router"]:
            return json.dumps(
                {
                    "intent": "general",
                    "report_type": "general_research",
                    "image_mode": "none",
                    "core_topic": self.core_topic,
                    "is_academic": False,
                    "query_type": "product",
                    "entities": [self.primary_entity],
                    "primary_entity": self.primary_entity,
                }
            )
        if system_prompt == "You are a concise title generator.":
            return f"{self.primary_entity} Research"
        if system_prompt == DEFAULT_SYSTEM["researcher"]:
            return json.dumps({"queries": [self.researcher_query]})
        if "research gap detector" in system_prompt:
            return json.dumps({"component_queries": [], "reasoning": "enough"})
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            if len(self.evaluator_responses) > 1:
                response = self.evaluator_responses.pop(0)
            else:
                response = self.evaluator_responses[0]
            return json.dumps(response)
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            self.analyst_calls += 1
            return "Analysis remains focused on Acme Widget rollout evidence."
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if kwargs.get("stream"):
            self.author_prompts.append(prompt)
            return _long_report()
        return _long_report()

    def _stage_for(self, system_prompt: str, kwargs: dict[str, Any]) -> str:
        if kwargs.get("stream"):
            return "author"
        if system_prompt == DEFAULT_SYSTEM["router"]:
            return "router"
        if system_prompt == "You are a concise title generator.":
            return "title"
        if system_prompt == DEFAULT_SYSTEM["researcher"]:
            return "researcher"
        if "research gap detector" in system_prompt:
            return "expander"
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return "evaluator"
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            return "analyst"
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return "synth_evaluator"
        return "other"

    def embed_texts(self, texts: list[str], **_kwargs: Any) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    def process_search_queries(
        self,
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self.search_calls.append(
            {
                "queries": list(queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "search_providers": list(kwargs.get("search_providers") or []),
                "provider_role": kwargs.get("provider_role"),
                "linkup_depth_override": kwargs.get("linkup_depth_override"),
            }
        )
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is None and len(_args) >= 4:
            seen_urls = _args[3]

        call_no = len(self.search_calls)
        out: list[dict[str, Any]] = []
        for idx in range(3):
            url = f"https://example.com/acme-widget/{call_no}/{idx}"
            if seen_urls is not None:
                seen_urls.add(url)
            out.append(
                {
                    "title": f"{self.primary_entity} source {call_no}-{idx}",
                    "url": url,
                    "text": (
                        f"{self.primary_entity} rollout evidence for "
                        f"{self.core_topic} with adoption detail {idx}."
                    ),
                    "score": 1.0 - (idx * 0.01),
                    "credibility": 3,
                    "source_tier": "secondary",
                    "_provider": "tavily",
                }
            )
        return out

    def deps(self) -> RunDeps:
        return RunDeps(
            ask_model=self.ask_model,
            embed_texts=self.embed_texts,
            compute_similarities=lambda *_args, **_kwargs: [1.0],
            process_search_queries=self.process_search_queries,
            filter_top_evidence=lambda passages, *_args, **_kwargs: list(passages),
            is_plausible_domain=lambda _url: True,
            anchor_query_to_topic=lambda q, _topic: q,
            fetch_linkup_precision_block=lambda *_args, **_kwargs: "",
            run_economist_step=lambda *_args, **_kwargs: "",
            run_scout=lambda *_args, **_kwargs: {},
            should_skip_quant_scout=lambda *_args, **_kwargs: False,
            clean_json_response=lambda value: value,
            DEFAULT_SYSTEM=DEFAULT_SYSTEM,
            NEWS_PREFERRED_DOMAINS=[],
            ACADEMIC_DOMAINS=[],
            QUANT_REPORT_TYPES=set(),
            logger=logging.getLogger("test_retrieval_stop_shadow"),
            execution_log_path=self.tmp_path / "execution.jsonl",
            feedback_log_path=self.tmp_path / "feedback.jsonl",
            kb_triggers_path=self.tmp_path / "kb.jsonl",
            policy_state_path=self.tmp_path / "policy.json",
            policy_journal_path=self.tmp_path / "policy_journal.jsonl",
        )


def _execution_event_from_log(path: Path) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") == "execution":
            return row
    raise AssertionError("execution event not found")


def _run_case(
    tmp_path: Path,
    *,
    mode: str = "Balanced",
    **harness_kwargs: Any,
) -> tuple[Any, _ShadowHarness, dict[str, Any]]:
    harness = _ShadowHarness(tmp_path, **harness_kwargs)
    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode=mode,
            current_date="2026-05-20",
            use_reasoning=False,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    return outcome, harness, _execution_event_from_log(tmp_path / "execution.jsonl")


def _assert_shadow(
    trace: dict[str, Any],
    *,
    decision: str,
    stage: str,
    next_query_count: int | None = None,
) -> None:
    assert trace["retrieval_stop_shadow_available"] is True
    assert trace["retrieval_stop_shadow_decision"] == decision
    assert trace["retrieval_stop_shadow_stage"] == stage
    assert trace["retrieval_stop_shadow_mode"] == "shadow_only"
    assert trace["retrieval_stop_shadow_alignment"] == "aligned"
    assert isinstance(trace["retrieval_stop_shadow_reason"], str)
    assert isinstance(trace["retrieval_stop_shadow_blockers"], list)
    if next_query_count is not None:
        assert trace["retrieval_stop_shadow_next_query_count"] == next_query_count


def _assert_active_defaults(trace: dict[str, Any]) -> None:
    assert trace["retrieval_stop_active_available"] is False
    assert trace["retrieval_stop_active_action_name"] is None
    assert trace["retrieval_stop_active_authority"] is None
    assert trace["retrieval_stop_active_decision"] is None
    assert trace["retrieval_stop_active_reason"] is None
    assert trace["retrieval_stop_active_terminal_branch_reason"] is None
    assert trace["retrieval_stop_active_blockers"] == []
    assert trace["retrieval_stop_active_next_query_count"] == 0
    assert trace["retrieval_stop_active_approved_query_count"] == 0
    assert trace["retrieval_stop_active_stage"] is None
    assert trace["retrieval_stop_active_mode"] == "active_stop_no_queries"
    assert trace["retrieval_stop_active_final_answer_posture"] is None
    assert trace["retrieval_stop_active_ag28_candidate"] is None
    assert trace["retrieval_stop_active_shadow_alignment"] is None
    assert trace["retrieval_stop_active_fallback_reason"] is None


def _assert_active_stop_no_queries(trace: dict[str, Any]) -> None:
    assert trace["retrieval_stop_active_available"] is True
    assert trace["retrieval_stop_active_action_name"] == (
        STOP_INSUFFICIENT_WITH_CAVEAT
    )
    assert trace["retrieval_stop_active_authority"] == (
        ControllerActionAuthority.ACTIVE.value
    )
    assert trace["retrieval_stop_active_decision"] == "stop_no_queries"
    assert trace["retrieval_stop_active_reason"] == "no_new_queries"
    assert trace["retrieval_stop_active_terminal_branch_reason"] == "no_new_queries"
    assert "no_new_queries" in trace["retrieval_stop_active_blockers"]
    assert trace["retrieval_stop_active_next_query_count"] == 0
    assert trace["retrieval_stop_active_approved_query_count"] == 0
    assert trace["retrieval_stop_active_stage"] == "evaluator_no_queries"
    assert trace["retrieval_stop_active_mode"] == "active_stop_no_queries"
    assert trace["retrieval_stop_active_final_answer_posture"] == (
        "answer with caveats"
    )
    assert trace["retrieval_stop_active_ag28_candidate"] == (
        "ag28:stop_insufficient_with_caveat:terminal_no_query_or_budget_exhausted"
    )
    assert trace["retrieval_stop_active_shadow_alignment"] == "aligned"
    assert trace["retrieval_stop_active_fallback_reason"] is None


def _assert_active_stop_budget_exhausted(trace: dict[str, Any]) -> None:
    assert trace["retrieval_stop_active_available"] is True
    assert trace["retrieval_stop_active_action_name"] == (
        STOP_INSUFFICIENT_WITH_CAVEAT
    )
    assert trace["retrieval_stop_active_authority"] == (
        ControllerActionAuthority.ACTIVE.value
    )
    assert trace["retrieval_stop_active_decision"] == "stop_budget_exhausted"
    assert trace["retrieval_stop_active_reason"] == "iteration_budget_exhausted"
    assert trace["retrieval_stop_active_terminal_branch_reason"] == (
        "iteration_budget_exhausted"
    )
    assert "iteration_budget_exhausted" in trace["retrieval_stop_active_blockers"]
    assert trace["retrieval_stop_active_next_query_count"] == 0
    assert trace["retrieval_stop_active_approved_query_count"] == 0
    assert trace["retrieval_stop_active_stage"] == "iteration_budget_exhausted"
    assert trace["retrieval_stop_active_mode"] == "active_stop_budget_exhausted"
    assert trace["retrieval_stop_active_final_answer_posture"] == (
        "answer with caveats"
    )
    assert trace["retrieval_stop_active_ag28_candidate"] == (
        "ag28:stop_insufficient_with_caveat:terminal_no_query_or_budget_exhausted"
    )
    assert trace["retrieval_stop_active_shadow_alignment"] == "aligned"
    assert trace["retrieval_stop_active_fallback_reason"] is None


def test_shadow_records_proceed_to_synthesis_when_evaluator_sufficient(
    tmp_path: Path,
) -> None:
    outcome, harness, log_entry = _run_case(
        tmp_path,
        evaluator_responses=[{"is_sufficient": True, "new_queries": []}],
    )

    _assert_shadow(
        outcome.execution_trace,
        decision="proceed_to_synthesis",
        stage="evaluator",
        next_query_count=0,
    )
    assert log_entry["execution_trace"]["retrieval_stop_shadow_decision"] == (
        "proceed_to_synthesis"
    )
    _assert_active_defaults(outcome.execution_trace)
    assert len(harness.search_calls) == 1
    assert outcome.execution_trace["queries_per_iteration"] == {
        "1": harness.search_calls[0]["queries"]
    }


def test_shadow_records_continue_retrieval_for_nonredundant_evaluator_queries(
    tmp_path: Path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        evaluator_responses=[
            {
                "is_sufficient": False,
                "new_queries": [
                    "Acme Widget migration timeline",
                    "Acme Widget support matrix",
                ],
            }
        ],
    )

    _assert_shadow(
        outcome.execution_trace,
        decision="continue_retrieval",
        stage="evaluator",
        next_query_count=2,
    )
    assert len(harness.search_calls) == 2
    assert outcome.execution_trace["queries_per_iteration"]["2"] == (
        harness.search_calls[1]["queries"]
    )
    assert outcome.execution_trace["iterations_run"] == 2
    _assert_active_defaults(outcome.execution_trace)


def test_active_stop_no_queries_records_terminal_controller_handoff(
    tmp_path: Path,
) -> None:
    outcome, harness, log_entry = _run_case(
        tmp_path,
        evaluator_responses=[{"is_sufficient": False, "new_queries": []}],
    )

    _assert_shadow(
        outcome.execution_trace,
        decision="stop_no_queries",
        stage="evaluator_no_queries",
        next_query_count=0,
    )
    assert "no_new_queries" in outcome.execution_trace[
        "retrieval_stop_shadow_blockers"
    ]
    _assert_active_stop_no_queries(outcome.execution_trace)
    _assert_active_stop_no_queries(log_entry["execution_trace"])
    assert len(harness.search_calls) == 1
    assert outcome.execution_trace["iterations_run"] == 1
    sqlite_row = execution_jsonl_to_run_row(log_entry)
    assert sqlite_row is not None
    assert all(field not in log_entry for field in ACTIVE_FIELDS)
    assert all(field not in sqlite_row for field in ACTIVE_FIELDS)
    for text in [outcome.report, *harness.author_prompts]:
        for marker in LEAK_MARKERS:
            assert marker not in text


def test_shadow_records_stop_redundant_queries_for_redundant_terminal_case(
    tmp_path: Path,
) -> None:
    redundant_query = "Acme Widget rollout evidence"
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        researcher_query=redundant_query,
        evaluator_responses=[
            {"is_sufficient": False, "new_queries": [redundant_query]}
        ],
    )

    _assert_shadow(
        outcome.execution_trace,
        decision="stop_redundant_queries",
        stage="evaluator_redundant_queries",
        next_query_count=1,
    )
    assert "redundant_queries" in outcome.execution_trace[
        "retrieval_stop_shadow_blockers"
    ]
    assert outcome.execution_trace["query_redundancy_skipped"] is True
    assert len(harness.search_calls) == 1
    _assert_active_defaults(outcome.execution_trace)


def test_active_stop_budget_exhausted_records_terminal_controller_handoff(
    tmp_path: Path,
) -> None:
    outcome, harness, log_entry = _run_case(tmp_path, mode="Fast")

    _assert_shadow(
        outcome.execution_trace,
        decision="stop_budget_exhausted",
        stage="iteration_budget_exhausted",
        next_query_count=0,
    )
    assert "evaluator" not in harness.model_stage_calls
    assert len(harness.search_calls) == 1
    assert outcome.execution_trace["iterations_run"] == 1
    _assert_active_stop_budget_exhausted(outcome.execution_trace)
    _assert_active_stop_budget_exhausted(log_entry["execution_trace"])
    sqlite_row = execution_jsonl_to_run_row(log_entry)
    assert sqlite_row is not None
    assert all(field not in log_entry for field in ACTIVE_FIELDS)
    assert all(field not in sqlite_row for field in ACTIVE_FIELDS)
    for text in [outcome.report, *harness.author_prompts]:
        for marker in LEAK_MARKERS:
            assert marker not in text


def test_active_budget_exhausted_records_no_approved_queries_with_pending_facts() -> None:
    telemetry = orchestrator._build_retrieval_stop_active_stop_budget_exhausted_telemetry(
        stage="iteration_budget_exhausted",
        evaluator_sufficient=False,
        iteration=2,
        max_iterations=2,
        prior_queries=["Acme Widget rollout evidence"],
        next_queries=["Acme Widget official follow up"],
        query_source="evaluator",
        shadow_telemetry={
            "retrieval_stop_shadow_available": True,
            "retrieval_stop_shadow_decision": "stop_budget_exhausted",
        },
    )

    assert telemetry["retrieval_stop_active_available"] is True
    assert telemetry["retrieval_stop_active_action_name"] == (
        STOP_INSUFFICIENT_WITH_CAVEAT
    )
    assert telemetry["retrieval_stop_active_authority"] == "active"
    assert telemetry["retrieval_stop_active_decision"] == "stop_budget_exhausted"
    assert telemetry["retrieval_stop_active_next_query_count"] == 1
    assert telemetry["retrieval_stop_active_approved_query_count"] == 0
    assert telemetry["retrieval_stop_active_final_answer_posture"] == (
        "answer with caveats"
    )
    assert telemetry["retrieval_stop_active_shadow_alignment"] == "aligned"


def test_ag30_active_budget_exhausted_pending_query_facts_do_not_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_builder = (
        orchestrator._build_retrieval_stop_active_stop_budget_exhausted_telemetry
    )

    def _inject_pending_query_facts(**kwargs: Any) -> dict[str, Any]:
        kwargs["next_queries"] = ["Acme Widget official follow up"]
        kwargs["query_source"] = "evaluator"
        return original_builder(**kwargs)

    monkeypatch.setattr(
        orchestrator,
        "_build_retrieval_stop_active_stop_budget_exhausted_telemetry",
        _inject_pending_query_facts,
    )

    outcome, harness, log_entry = _run_case(tmp_path, mode="Fast")

    assert len(harness.search_calls) == 1
    assert outcome.execution_trace["iterations_run"] == 1
    assert outcome.execution_trace["queries_per_iteration"] == {
        "1": harness.search_calls[0]["queries"]
    }
    assert "2" not in outcome.execution_trace["queries_per_iteration"]
    assert outcome.execution_trace["retrieval_stop_active_decision"] == (
        "stop_budget_exhausted"
    )
    assert outcome.execution_trace["retrieval_stop_active_next_query_count"] == 1
    assert outcome.execution_trace["retrieval_stop_active_approved_query_count"] == 0
    assert log_entry["execution_trace"]["retrieval_stop_active_next_query_count"] == 1
    assert log_entry["execution_trace"][
        "retrieval_stop_active_approved_query_count"
    ] == 0


def test_shadow_records_stop_after_weak_corpus_recovery(tmp_path: Path) -> None:
    outcome, harness = _run_weak_corpus_case(tmp_path)

    _assert_shadow(
        outcome.execution_trace,
        decision="stop_after_recovery",
        stage="weak_corpus_recovery_completed",
        next_query_count=0,
    )
    assert outcome.execution_trace["weak_corpus_recovery_used"] is True
    assert harness.search_calls[-1] == outcome.execution_trace[
        "weak_corpus_recovery_queries"
    ]
    _assert_active_defaults(outcome.execution_trace)


def test_active_stop_no_queries_parity_with_legacy_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluator_responses = [{"is_sufficient": False, "new_queries": []}]
    active_outcome, active_harness, active_log = _run_case(
        tmp_path / "active",
        evaluator_responses=list(evaluator_responses),
    )

    monkeypatch.setattr(
        orchestrator,
        "_build_retrieval_stop_active_stop_no_queries_telemetry",
        lambda **_kwargs: orchestrator._retrieval_stop_active_defaults(),
    )
    baseline_outcome, baseline_harness, baseline_log = _run_case(
        tmp_path / "baseline",
        evaluator_responses=list(evaluator_responses),
    )

    assert active_harness.search_calls == baseline_harness.search_calls
    assert active_harness.model_stage_calls == baseline_harness.model_stage_calls
    assert active_harness.author_prompts == baseline_harness.author_prompts
    assert active_outcome.report == baseline_outcome.report
    for field in (
        "queries_per_iteration",
        "pass_providers",
        "iterations_run",
        "weak_corpus_recovery_used",
        "scout_fired",
        "supplemental_ran",
        "analyst_skipped",
        "economist_ran",
    ):
        assert active_outcome.execution_trace[field] == baseline_outcome.execution_trace[
            field
        ]
    for field in SHADOW_FIELDS:
        assert active_outcome.execution_trace[field] == baseline_outcome.execution_trace[
            field
        ]
        assert active_log["execution_trace"][field] == baseline_log["execution_trace"][
            field
        ]
    _assert_active_stop_no_queries(active_outcome.execution_trace)
    _assert_active_defaults(baseline_outcome.execution_trace)


def test_active_stop_budget_exhausted_parity_with_legacy_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_outcome, active_harness, active_log = _run_case(
        tmp_path / "active",
        mode="Fast",
    )

    monkeypatch.setattr(
        orchestrator,
        "_build_retrieval_stop_active_stop_budget_exhausted_telemetry",
        lambda **_kwargs: orchestrator._retrieval_stop_active_defaults(),
    )
    baseline_outcome, baseline_harness, baseline_log = _run_case(
        tmp_path / "baseline",
        mode="Fast",
    )

    assert active_harness.search_calls == baseline_harness.search_calls
    assert active_harness.model_stage_calls == baseline_harness.model_stage_calls
    assert active_harness.author_prompts == baseline_harness.author_prompts
    assert active_harness.analyst_calls == baseline_harness.analyst_calls
    assert active_outcome.report == baseline_outcome.report
    for field in (
        "queries_per_iteration",
        "pass_providers",
        "iterations_run",
        "weak_corpus_recovery_considered",
        "weak_corpus_recovery_used",
        "weak_corpus_recovery_skip_reason",
        "weak_corpus_recovery_queries",
        "weak_corpus_recovery_decision",
        "weak_corpus_recovery_reason",
        "weak_corpus_recovery_blockers",
        "analyst_skipped",
        "analyst_skip_reason",
        "analyst_skipped_after_economist",
        "analyst_after_economist_skip_reason",
        "economist_ran",
        "economist_output_used_as_analysis",
        "post_retrieval_fast_path_used",
    ):
        assert active_outcome.execution_trace[field] == baseline_outcome.execution_trace[
            field
        ]
    for field in SHADOW_FIELDS:
        assert active_outcome.execution_trace[field] == baseline_outcome.execution_trace[
            field
        ]
        assert active_log["execution_trace"][field] == baseline_log["execution_trace"][
            field
        ]
    _assert_active_stop_budget_exhausted(active_outcome.execution_trace)
    _assert_active_defaults(baseline_outcome.execution_trace)


def test_active_stop_no_queries_falls_back_on_unexpected_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unexpected_decision(_snapshot: Any) -> RetrievalStopDecision:
        return RetrievalStopDecision(
            decision=RetrievalStopControllerDecision.CONTINUE_RETRIEVAL,
            reason="candidate_queries_available",
            next_queries=("Acme Widget migration timeline",),
            query_source="evaluator",
        )

    monkeypatch.setattr(
        orchestrator,
        "_decide_retrieval_stop_for_active",
        _unexpected_decision,
    )
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        evaluator_responses=[{"is_sufficient": False, "new_queries": []}],
    )

    _assert_shadow(
        outcome.execution_trace,
        decision="stop_no_queries",
        stage="evaluator_no_queries",
        next_query_count=0,
    )
    assert len(harness.search_calls) == 1
    assert outcome.execution_trace["iterations_run"] == 1
    assert outcome.execution_trace["retrieval_stop_active_available"] is False
    assert outcome.execution_trace["retrieval_stop_active_decision"] == (
        "continue_retrieval"
    )
    assert outcome.execution_trace["retrieval_stop_active_fallback_reason"] == (
        "unexpected_controller_decision"
    )


def test_active_stop_no_queries_falls_back_on_controller_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_controller(_snapshot: Any) -> None:
        raise RuntimeError("synthetic active controller failure")

    monkeypatch.setattr(
        orchestrator,
        "_decide_retrieval_stop_for_active",
        _raise_controller,
    )
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        evaluator_responses=[{"is_sufficient": False, "new_queries": []}],
    )

    _assert_shadow(
        outcome.execution_trace,
        decision="stop_no_queries",
        stage="evaluator_no_queries",
        next_query_count=0,
    )
    assert len(harness.search_calls) == 1
    assert outcome.execution_trace["iterations_run"] == 1
    assert outcome.execution_trace["retrieval_stop_active_available"] is False
    assert outcome.execution_trace["retrieval_stop_active_reason"] == (
        "active_controller_unavailable"
    )
    assert outcome.execution_trace["retrieval_stop_active_fallback_reason"] == (
        "controller_exception"
    )


def test_active_stop_budget_exhausted_falls_back_on_unexpected_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unexpected_decision(_snapshot: Any) -> RetrievalStopDecision:
        return RetrievalStopDecision(
            decision=RetrievalStopControllerDecision.CONTINUE_RETRIEVAL,
            reason="candidate_queries_available",
            next_queries=("Acme Widget migration timeline",),
            query_source="budget",
        )

    monkeypatch.setattr(
        orchestrator,
        "_decide_retrieval_stop_for_active",
        _unexpected_decision,
    )
    outcome, harness, _log_entry = _run_case(tmp_path, mode="Fast")

    _assert_shadow(
        outcome.execution_trace,
        decision="stop_budget_exhausted",
        stage="iteration_budget_exhausted",
        next_query_count=0,
    )
    assert len(harness.search_calls) == 1
    assert outcome.execution_trace["iterations_run"] == 1
    assert outcome.execution_trace["retrieval_stop_active_available"] is False
    assert outcome.execution_trace["retrieval_stop_active_decision"] == (
        "continue_retrieval"
    )
    assert outcome.execution_trace["retrieval_stop_active_fallback_reason"] == (
        "unexpected_controller_decision"
    )


def test_active_stop_budget_exhausted_falls_back_on_controller_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_controller(_snapshot: Any) -> None:
        raise RuntimeError("synthetic active controller failure")

    monkeypatch.setattr(
        orchestrator,
        "_decide_retrieval_stop_for_active",
        _raise_controller,
    )
    outcome, harness, _log_entry = _run_case(tmp_path, mode="Fast")

    _assert_shadow(
        outcome.execution_trace,
        decision="stop_budget_exhausted",
        stage="iteration_budget_exhausted",
        next_query_count=0,
    )
    assert len(harness.search_calls) == 1
    assert outcome.execution_trace["iterations_run"] == 1
    assert outcome.execution_trace["retrieval_stop_active_available"] is False
    assert outcome.execution_trace["retrieval_stop_active_reason"] == (
        "active_controller_unavailable"
    )
    assert outcome.execution_trace["retrieval_stop_active_fallback_reason"] == (
        "controller_exception"
    )


def test_shadow_wiring_preserves_runtime_behavior_and_storage_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluator_responses = [{"is_sufficient": True, "new_queries": []}]
    active_outcome, active_harness, active_log = _run_case(
        tmp_path / "active",
        evaluator_responses=list(evaluator_responses),
    )

    monkeypatch.setattr(
        orchestrator,
        "_build_retrieval_stop_shadow_telemetry",
        lambda **_kwargs: orchestrator._retrieval_stop_shadow_defaults(),
    )
    baseline_outcome, baseline_harness, baseline_log = _run_case(
        tmp_path / "baseline",
        evaluator_responses=list(evaluator_responses),
    )

    assert active_harness.search_calls == baseline_harness.search_calls
    assert active_harness.model_stage_calls == baseline_harness.model_stage_calls
    assert active_harness.author_prompts == baseline_harness.author_prompts
    assert active_outcome.report == baseline_outcome.report
    for field in (
        "queries_per_iteration",
        "pass_providers",
        "iterations_run",
        "weak_corpus_recovery_used",
        "scout_fired",
        "supplemental_ran",
        "analyst_skipped",
        "economist_ran",
    ):
        assert active_outcome.execution_trace[field] == baseline_outcome.execution_trace[
            field
        ]

    assert SHADOW_FIELDS <= set(active_outcome.execution_trace)
    assert ACTIVE_FIELDS <= set(active_outcome.execution_trace)
    assert SHADOW_FIELDS <= set(active_log["execution_trace"])
    assert ACTIVE_FIELDS <= set(active_log["execution_trace"])
    assert all(field not in active_log for field in SHADOW_FIELDS)
    assert all(field not in active_log for field in ACTIVE_FIELDS)

    sqlite_row = execution_jsonl_to_run_row(active_log)
    assert sqlite_row is not None
    assert set(sqlite_row) <= set(RUN_COLUMNS)
    assert "execution_trace" not in sqlite_row
    assert all(field not in sqlite_row for field in SHADOW_FIELDS)
    assert all(field not in sqlite_row for field in ACTIVE_FIELDS)

    for text in [active_outcome.report, *active_harness.author_prompts]:
        for marker in LEAK_MARKERS:
            assert marker not in text
