"""Offline diagnostics for current follow-up route quality behavior.

These cases document today's route signals only. They are not golden-answer scoring
and should not be treated as production routing policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from core.followup import FollowUpDeps, FollowUpRunResult, run_followup

FU_PARAMS = {
    "max_queries": 3,
    "search_depth": "advanced",
    "max_results": 3,
    "top_passage_count": 2,
}

DEFAULT_MEMORY_PASSAGE = {
    "url": "https://memory.example/saved-context",
    "title": "Saved Synthetic Evidence",
    "text": "Saved synthetic evidence says the original conclusion came from archived context.",
}

WEAK_MEMORY_PASSAGE = {
    "url": "https://memory.example/weak-context",
    "title": "Weak Saved Evidence",
    "text": "Thin saved excerpt with weak support and no corroborating synthetic source.",
}

FRESH_PASSAGE = {
    "url": "https://fresh.example/route-evidence",
    "title": "Fresh Route Evidence",
    "text": "Fresh synthetic evidence retrieved for the follow-up route.",
    "score": 0.93,
}

CONTRADICTION_PASSAGE = {
    "url": "https://fresh.example/contradiction",
    "title": "Contradictory Synthetic Evidence",
    "text": "Synthetic source that challenges the saved conclusion.",
    "score": 0.91,
}

PEER_REVIEWED_PASSAGE = {
    "url": "https://journal.example/peer-review",
    "title": "Peer Reviewed Synthetic Evidence",
    "text": "Synthetic journal-style evidence used to document source-constraint routing.",
    "score": 0.89,
}


@dataclass(frozen=True, kw_only=True)
class _RouteCase:
    case_id: str
    query: str
    evaluator_output: str
    expected_needs_search: bool
    expected_followup_queries: tuple[str, ...]
    expected_search_ran: bool
    expected_search_calls: int
    expected_new_passage_count: int
    search_passages: tuple[dict[str, Any], ...] = ()
    top_passages: tuple[dict[str, Any], ...] = (DEFAULT_MEMORY_PASSAGE,)
    similarity_scores: tuple[float, ...] = (0.9,)
    include_domains: tuple[str, ...] = ()
    exclude_domains: tuple[str, ...] = ()
    prompt_contains: tuple[str, ...] = ()
    prompt_absent: tuple[str, ...] = ()
    progress_contains: tuple[str, ...] = ()
    warning_contains: tuple[str, ...] = ()


class _WarningLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)


class _SyntheticFollowupHarness:
    def __init__(
        self,
        *,
        evaluator_output: str,
        search_passages: tuple[dict[str, Any], ...] = (),
        search_error: Exception | None = None,
        similarity_scores: tuple[float, ...] = (0.9,),
    ) -> None:
        self.evaluator_output = evaluator_output
        self.search_passages = [dict(passage) for passage in search_passages]
        self.search_error = search_error
        self.similarity_scores = list(similarity_scores)
        self.embedding_calls: list[dict[str, Any]] = []
        self.evaluator_calls: list[dict[str, Any]] = []
        self.search_calls: list[dict[str, Any]] = []
        self.synthesis_prompts: list[str] = []
        self.logger = _WarningLogger()

    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        self.embedding_calls.append({"texts": list(texts), "kwargs": dict(kwargs)})
        return [[float(index + 1), 0.0] for index, _text in enumerate(texts)]

    def compute_similarities(self, _query_embedding: list[float], existing_embeddings: list[list[float]]) -> list[float]:
        scores = list(self.similarity_scores)
        if not scores:
            scores = [0.0]
        if len(scores) < len(existing_embeddings):
            scores.extend([scores[-1]] * (len(existing_embeddings) - len(scores)))
        return scores[: len(existing_embeddings)]

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        self.evaluator_calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "require_json": kwargs.get("require_json"),
                "provider": kwargs.get("provider"),
                "model": kwargs.get("model"),
            }
        )
        return self.evaluator_output

    def search_fn(
        self,
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        max_results: int,
        include_domains: list[str],
        exclude_domains: list[str],
        query_embedding: list[float],
        seen_urls: set[str],
        collected_images: set[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self.search_calls.append(
            {
                "queries": list(queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_domains": list(include_domains),
                "exclude_domains": list(exclude_domains),
                "query_embedding": list(query_embedding),
                "seen_urls": sorted(seen_urls),
                "collected_images": sorted(collected_images),
                "kwargs": dict(kwargs),
            }
        )
        if self.search_error is not None:
            raise self.search_error
        return [dict(passage) for passage in self.search_passages]

    def synthesis_model_fn(self, prompt: str) -> str:
        self.synthesis_prompts.append(prompt)
        return "synthetic follow-up answer"


def _session(top_passages: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return {
        "report": "Synthetic saved report with a compact conclusion and citation context.",
        "top_passages": [dict(passage) for passage in top_passages],
        "chat_messages": [
            {"role": "user", "content": "Original synthetic question."},
            {"role": "assistant", "content": "Synthetic saved report answer."},
            {"role": "user", "content": "Synthetic follow-up placeholder."},
        ],
        "seen_urls": ["https://memory.example/saved-context"],
        "collected_images": [],
    }


def _run_case(
    case: _RouteCase,
    *,
    execution_log_path: Path | None = None,
    search_error: Exception | None = None,
) -> tuple[FollowUpRunResult, _SyntheticFollowupHarness, list[str]]:
    harness = _SyntheticFollowupHarness(
        evaluator_output=case.evaluator_output,
        search_passages=case.search_passages,
        search_error=search_error,
        similarity_scores=case.similarity_scores,
    )
    deps = FollowUpDeps(
        embed_texts=harness.embed_texts,
        compute_similarities=harness.compute_similarities,
        search_fn=harness.search_fn,
        ask_model=harness.ask_model,
        clean_json_response=lambda value: value,
        synthesis_model_fn=harness.synthesis_model_fn,
        execution_log_path=execution_log_path,
        logger=harness.logger,
    )
    progress: list[str] = []

    result = run_followup(
        query=case.query,
        session=_session(case.top_passages),
        deps=deps,
        current_date="2026-05-12",
        follow_complexity="medium",
        fu_params=FU_PARAMS,
        intent="general",
        include_domains=list(case.include_domains),
        exclude_domains=list(case.exclude_domains),
        embed_provider="SyntheticEmbeddings",
        embed_model="synthetic-embedding-model",
        fast_provider="SyntheticEvaluator",
        fast_model="synthetic-evaluator-model",
        local_url="",
        api_key="",
        use_reasoning=False,
        chat_evaluator_prompt="Return only synthetic JSON.",
        is_plausible_domain=lambda _url: True,
        run_id="route-matrix-run",
        session_id="route-matrix-session",
        on_progress=progress.append,
    )

    return result, harness, progress


ROUTE_CASES = (
    _RouteCase(
        case_id="saved_context_sufficient_documents_current_no_search",
        query="Summarize the saved finding in one sentence.",
        evaluator_output='{"can_answer": true}',
        expected_needs_search=False,
        expected_followup_queries=(),
        expected_search_ran=False,
        expected_search_calls=0,
        expected_new_passage_count=0,
        prompt_contains=("Raw Source Excerpts for Precision", "Saved Synthetic Evidence", "AVAILABLE SOURCES"),
        prompt_absent=("Newly Gathered Evidence for Follow-up",),
        progress_contains=("Existing context sufficient; skipping web search.",),
    ),
    _RouteCase(
        case_id="fresh_retrieval_required_documents_current_search_route",
        query="Find the latest synthetic support for that point.",
        evaluator_output='{"can_answer": false, "search_queries": ["fresh synthetic support"]}',
        search_passages=(FRESH_PASSAGE,),
        expected_needs_search=True,
        expected_followup_queries=("fresh synthetic support",),
        expected_search_ran=True,
        expected_search_calls=1,
        expected_new_passage_count=1,
        prompt_contains=("Newly Gathered Evidence for Follow-up", "[New Source 2] Fresh Route Evidence"),
        progress_contains=("Searching the web", "Integrated 1 new evidence passages."),
    ),
    _RouteCase(
        case_id="malformed_evaluator_output_documents_current_saved_context_default",
        query="Should this malformed evaluator response trigger search?",
        evaluator_output="not-json-from-synthetic-evaluator",
        expected_needs_search=False,
        expected_followup_queries=(),
        expected_search_ran=False,
        expected_search_calls=0,
        expected_new_passage_count=0,
        prompt_absent=("Newly Gathered Evidence for Follow-up",),
        progress_contains=("Existing context sufficient; skipping web search.",),
        warning_contains=("Evaluator JSON parse failed",),
    ),
    _RouteCase(
        case_id="empty_retrieval_documents_current_synthesis_without_new_evidence",
        query="Search for more synthetic evidence, even if none is readable.",
        evaluator_output='{"can_answer": false, "search_queries": ["empty synthetic retrieval"]}',
        expected_needs_search=True,
        expected_followup_queries=("empty synthetic retrieval",),
        expected_search_ran=True,
        expected_search_calls=1,
        expected_new_passage_count=0,
        prompt_absent=("Newly Gathered Evidence for Follow-up",),
        progress_contains=("No new readable text found.",),
    ),
    _RouteCase(
        case_id="source_constraint_documents_current_pass_through_without_new_policy",
        query="Narrow to peer-reviewed only.",
        evaluator_output='{"can_answer": false, "search_queries": ["peer reviewed synthetic evidence"]}',
        search_passages=(PEER_REVIEWED_PASSAGE,),
        expected_needs_search=True,
        expected_followup_queries=("peer reviewed synthetic evidence",),
        expected_search_ran=True,
        expected_search_calls=1,
        expected_new_passage_count=1,
        prompt_contains=("Peer Reviewed Synthetic Evidence",),
    ),
    _RouteCase(
        case_id="contradiction_followup_documents_current_retrieval_route",
        query="What sources contradict that conclusion?",
        evaluator_output='{"can_answer": false, "search_queries": ["synthetic contradiction evidence"]}',
        search_passages=(CONTRADICTION_PASSAGE,),
        expected_needs_search=True,
        expected_followup_queries=("synthetic contradiction evidence",),
        expected_search_ran=True,
        expected_search_calls=1,
        expected_new_passage_count=1,
        prompt_contains=("Contradictory Synthetic Evidence",),
    ),
    _RouteCase(
        case_id="ambiguous_followup_documents_current_no_clarification_route",
        query="What about the other one?",
        evaluator_output='{"can_answer": true}',
        expected_needs_search=False,
        expected_followup_queries=(),
        expected_search_ran=False,
        expected_search_calls=0,
        expected_new_passage_count=0,
        prompt_absent=("Newly Gathered Evidence for Follow-up",),
    ),
    _RouteCase(
        case_id="weak_saved_evidence_documents_current_evaluator_controls_route",
        query="Can the saved evidence support that claim?",
        evaluator_output='{"can_answer": true}',
        top_passages=(WEAK_MEMORY_PASSAGE,),
        similarity_scores=(0.01,),
        expected_needs_search=False,
        expected_followup_queries=(),
        expected_search_ran=False,
        expected_search_calls=0,
        expected_new_passage_count=0,
        prompt_contains=("Weak Saved Evidence", "Thin saved excerpt with weak support"),
        prompt_absent=("Newly Gathered Evidence for Follow-up",),
    ),
)


@pytest.mark.parametrize("case", ROUTE_CASES, ids=lambda case: case.case_id)
def test_followup_route_quality_matrix_documents_current_behavior(case: _RouteCase) -> None:
    result, harness, progress = _run_case(case)

    # Current evaluator state is exposed as needs_search/followup_queries, not as a retained can_answer field.
    assert result.memory_result.needs_search is case.expected_needs_search
    assert tuple(result.memory_result.followup_queries) == case.expected_followup_queries
    assert result.web_result.search_ran is case.expected_search_ran
    assert len(harness.search_calls) == case.expected_search_calls
    assert len(result.web_result.new_passages) == case.expected_new_passage_count
    assert len(harness.evaluator_calls) == 1
    assert harness.evaluator_calls[0]["require_json"] is True
    assert result.synthesis_result.answer == "synthetic follow-up answer"
    assert harness.synthesis_prompts == [result.synthesis_result.prompt_used]
    assert f"USER FOLLOW-UP: {case.query}" in result.synthesis_result.prompt_used

    if harness.search_calls:
        search_call = harness.search_calls[0]
        assert tuple(search_call["queries"]) == case.expected_followup_queries
        assert tuple(search_call["include_domains"]) == case.include_domains
        assert tuple(search_call["exclude_domains"]) == case.exclude_domains

    for expected_text in case.prompt_contains:
        assert expected_text in result.synthesis_result.prompt_used
    for absent_text in case.prompt_absent:
        assert absent_text not in result.synthesis_result.prompt_used
    for expected_progress in case.progress_contains:
        assert any(expected_progress in message for message in progress)
    for expected_warning in case.warning_contains:
        assert any(expected_warning in message for message in harness.logger.warnings)


def test_followup_route_quality_matrix_documents_current_retrieval_error_path(tmp_path: Path) -> None:
    case = _RouteCase(
        case_id="retrieval_error_documents_current_logged_fallback_path",
        query="Search, but the synthetic retriever fails.",
        evaluator_output='{"can_answer": false, "search_queries": ["synthetic retrieval error"]}',
        expected_needs_search=True,
        expected_followup_queries=("synthetic retrieval error",),
        expected_search_ran=True,
        expected_search_calls=1,
        expected_new_passage_count=0,
        prompt_absent=("Newly Gathered Evidence for Follow-up",),
        progress_contains=("Follow-up web retrieval failed; continuing with existing context.",),
    )
    log_path = tmp_path / "execution_log.jsonl"

    result, harness, progress = _run_case(
        case,
        execution_log_path=log_path,
        search_error=RuntimeError("synthetic retrieval outage"),
    )

    assert result.memory_result.needs_search is True
    assert tuple(result.memory_result.followup_queries) == ("synthetic retrieval error",)
    assert result.web_result.search_ran is True
    assert result.web_result.error == "synthetic retrieval outage"
    assert result.web_result.new_passages == []
    assert len(harness.search_calls) == 1
    assert result.synthesis_result.answer == "synthetic follow-up answer"
    assert "Newly Gathered Evidence for Follow-up" not in result.synthesis_result.prompt_used
    assert any("Follow-up web retrieval failed" in message for message in progress)
    assert any("Follow-up web retrieval failed" in message for message in harness.logger.warnings)

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(events) == 1
    assert events[0]["event"] == "provider_error"
    assert events[0]["provider"] == "followup_web_retrieval"
    assert events[0]["phase"] == "chat_followup"
    assert events[0]["run_id"] == "route-matrix-run"
    assert events[0]["session_id"] == "route-matrix-session"
    assert events[0]["query_preview"] == "['synthetic retrieval error']"


def test_followup_route_quality_matrix_keeps_existing_budget_and_provider_behavior() -> None:
    case = _RouteCase(
        case_id="budget_provider_guard",
        query="Find the latest synthetic support for that point.",
        evaluator_output='{"can_answer": false, "search_queries": ["fresh synthetic support", "extra support"]}',
        search_passages=(FRESH_PASSAGE,),
        expected_needs_search=True,
        expected_followup_queries=("fresh synthetic support", "extra support"),
        expected_search_ran=True,
        expected_search_calls=1,
        expected_new_passage_count=1,
    )

    result, harness, _progress = _run_case(case)

    assert tuple(result.memory_result.followup_queries) == ("fresh synthetic support", "extra support")
    assert len(harness.evaluator_calls) == 1
    assert harness.evaluator_calls[0]["provider"] == "SyntheticEvaluator"
    assert harness.evaluator_calls[0]["model"] == "synthetic-evaluator-model"
    assert len(harness.search_calls) == 1
    search_call = harness.search_calls[0]
    assert search_call["queries"] == ["fresh synthetic support", "extra support"]
    assert search_call["search_depth"] == FU_PARAMS["search_depth"]
    assert search_call["max_results"] == FU_PARAMS["max_results"]
    assert search_call["complexity"] == "medium"
