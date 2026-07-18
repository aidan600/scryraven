from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.cost_accounting import CostAccumulator
from core.pipeline_orchestrator import run_pipeline
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig, RunDeps


def _long_report() -> str:
    return (
        "Acme Widget remains the requested subject, but the retrieved evidence is limited. "
        "The useful answer should stay anchored to Acme Widget pricing, official policy, "
        "and deployment details, while avoiding claims from unrelated pages. "
        "The available snippets indicate that the first pass did not line up well with "
        "the primary entity, so confidence should be modest and source-specific. "
        "For practical next steps, compare official pricing pages, release notes, support "
        "documentation, and current product announcements before treating third-party "
        "summaries as definitive. "
        "This synthetic report intentionally has enough ordinary words to pass the useful "
        "content heuristic in tests without relying on external search or live model calls. "
        "It also preserves the user's intent around pricing, deployment, and official "
        "documentation rather than drifting into a generic product overview."
    )


class _Harness:
    def __init__(
        self,
        tmp_path: Path,
        *,
        query: str = "Acme Widget pricing policy deployment official",
        core_topic: str = "Acme Widget pricing policy deployment",
        primary_entity: str = "Acme Widget",
        researcher_query: str = "pricing policy deployment",
        on_topic_first_pass: bool = False,
    ) -> None:
        self.tmp_path = tmp_path
        self.search_calls: list[list[str]] = []
        self.query = query
        self.core_topic = core_topic
        self.primary_entity = primary_entity
        self.researcher_query = researcher_query
        self.on_topic_first_pass = on_topic_first_pass
        self.author_prompts: list[str] = []
        self.search_call_details: list[dict[str, Any]] = []

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
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
        if system_prompt.startswith("You are a search query expander"):
            return json.dumps({"component_queries": [], "reasoning": "enough"})
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return json.dumps({"is_sufficient": True, "new_queries": []})
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            return "Analysis remains focused on Acme Widget pricing policy deployment."
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if kwargs.get("stream"):
            self.author_prompts.append(prompt)
            return _long_report()
        return _long_report()

    def embed_texts(self, texts: list[str], **_kwargs: Any) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    def process_search_queries(self, queries: list[str], *_args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        self.search_calls.append(list(queries))
        self.search_call_details.append(
            {
                "queries": list(queries),
                "intent": _args[0] if len(_args) > 0 else None,
                "complexity": _args[1] if len(_args) > 1 else None,
                "search_depth": _args[2] if len(_args) > 2 else None,
                "results_per_query": _args[3] if len(_args) > 3 else None,
                "search_providers": list(kwargs.get("search_providers") or []),
                "provider_role": kwargs.get("provider_role"),
                "linkup_depth_override": kwargs.get("linkup_depth_override"),
            }
        )
        call_no = len(self.search_calls)
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is None and len(_args) >= 8:
            seen_urls = _args[7]
        mentions_entity = self.on_topic_first_pass or call_no >= 3
        subject = self.primary_entity if mentions_entity else "Unrelated Gadget"
        out: list[dict[str, Any]] = []
        for idx in range(2):
            url = f"https://example.com/{call_no}/{idx}"
            if seen_urls is not None:
                seen_urls.add(url)
            out.append(
                {
                    "title": f"{subject} source {call_no}-{idx}",
                    "url": url,
                    "text": f"{subject} pricing policy deployment release notes evidence excerpt {idx}.",
                    "score": 1.0 - (idx * 0.01),
                    "credibility": 3,
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
            run_scout=lambda *_args, **_kwargs: {},
            should_skip_quant_scout=lambda *_args, **_kwargs: False,
            clean_json_response=lambda s: s,
            DEFAULT_SYSTEM=DEFAULT_SYSTEM,
            NEWS_PREFERRED_DOMAINS=[],
            ACADEMIC_DOMAINS=[],
            QUANT_REPORT_TYPES=set(),
            logger=logging.getLogger("test_weak_corpus_recovery"),
            execution_log_path=self.tmp_path / "execution.jsonl",
            feedback_log_path=self.tmp_path / "feedback.jsonl",
            kb_triggers_path=self.tmp_path / "kb.jsonl",
            policy_state_path=self.tmp_path / "policy.json",
            policy_journal_path=self.tmp_path / "policy_journal.jsonl",
            provider_availability={"tavily": True},
        )


def _run(
    tmp_path: Path,
    *,
    mode: str = "Balanced",
    query: str = "Acme Widget pricing policy deployment official",
    core_topic: str = "Acme Widget pricing policy deployment",
    primary_entity: str = "Acme Widget",
    researcher_query: str = "pricing policy deployment",
    on_topic_first_pass: bool = False,
):
    harness = _Harness(
        tmp_path,
        query=query,
        core_topic=core_topic,
        primary_entity=primary_entity,
        researcher_query=researcher_query,
        on_topic_first_pass=on_topic_first_pass,
    )
    outcome = run_pipeline(
        RunConfig(
            query=query,
            mode=mode,
            current_date="2026-05-06",
            use_reasoning=False,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    return outcome, harness


def test_weak_first_pass_runs_bounded_recovery_second_iteration(tmp_path: Path) -> None:
    outcome, harness = _run(tmp_path)

    trace = outcome.execution_trace
    assert trace["corpus_weak"] is True
    assert trace["weak_corpus_recovery_considered"] is True
    assert trace["weak_corpus_recovery_used"] is True
    assert trace["weak_corpus_recovery_skip_reason"] is None
    assert trace["weak_corpus_recovery_decision"] == "run_weak_corpus_recovery"
    assert trace["weak_corpus_recovery_reason"] == "weak_corpus_first_pass"
    assert trace["weak_corpus_recovery_blockers"] == []
    assert trace["iterations_run"] == 2
    assert "2" in trace["queries_per_iteration"]
    query_plan = trace["query_plan"]
    assert query_plan["authorized_queries_by_iteration"] == trace["queries_per_iteration"]
    assert harness.search_calls[0] == query_plan["authorized_queries_by_iteration"]["1"]
    assert harness.search_calls[-1] == query_plan["authorized_queries_by_iteration"]["2"]
    assert harness.search_calls[-1] == trace["weak_corpus_recovery_queries"]
    assert any(
        item["role"] == "recovery" and item["status"] == "ordered"
        for item in query_plan["items"]
    )
    assert harness.search_call_details[-1]["provider_role"] == "weak_corpus_recovery"


def test_weak_corpus_non_contract_candidate_preserves_required_recovery_path(
    tmp_path: Path,
) -> None:
    outcome, harness = _run(
        tmp_path,
        query="What are the current official rules and requirements for Acme Widget?",
        core_topic="Acme Widget current official rules requirements",
        primary_entity="Acme Widget",
        researcher_query="current official rules requirements",
    )

    trace = outcome.execution_trace
    assert trace["corpus_weak"] is True
    assert trace["weak_corpus_recovery_considered"] is True
    assert trace["weak_corpus_recovery_used"] is True
    assert trace["weak_corpus_recovery_decision"] == "run_weak_corpus_recovery"
    assert trace["source_class_recovery_recommended"] is True
    assert not str(trace["source_class_recovery_reason"] or "").startswith(
        "answer_contract_"
    )
    assert trace["source_class_underfire_shadow"] is True
    assert "official_current_rules" in trace["source_class_gap_candidates"]
    assert trace["active_source_class_recovery_considered"] is True
    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_skip_reason"] is None
    assert trace["active_source_class_recovery_blockers"] == []
    assert trace["authority_lifecycle_required_recovery_allowed"] is True
    assert trace["authority_lifecycle_weak_corpus_may_own_path"] is False
    packet = trace["source_class_recovery_candidate_v2"]
    assert packet["source_class_recovery_candidate_v2_shadow"] is True
    assert packet["source_class_recovery_candidate_v2_blocked_by_weak_corpus"] is True
    assert "weak_corpus_recovery_owns_path" in packet[
        "source_class_recovery_candidate_v2_blockers"
    ]
    assert trace["active_source_class_recovery_attempt_count"] == 1
    provider_roles = [call["provider_role"] for call in harness.search_call_details]
    assert "weak_corpus_recovery" in provider_roles
    assert "source_class_recovery" in provider_roles


def test_weak_first_pass_fast_mode_skips_recovery_with_reason(tmp_path: Path) -> None:
    outcome, _harness = _run(tmp_path, mode="Fast")

    trace = outcome.execution_trace
    assert trace["weak_corpus_recovery_considered"] is True
    assert trace["weak_corpus_recovery_used"] is False
    assert trace["weak_corpus_recovery_skip_reason"] == "max_iterations_1"
    assert trace["weak_corpus_recovery_decision"] == "blocked_with_reason"
    assert trace["weak_corpus_recovery_reason"] == "max_iterations_1"
    assert "max_iterations_1" in trace["weak_corpus_recovery_blockers"]
    assert trace["iterations_run"] == 1


def test_weak_recovery_runs_at_most_once(tmp_path: Path) -> None:
    outcome, harness = _run(tmp_path, mode="Deep")

    trace = outcome.execution_trace
    assert trace["weak_corpus_recovery_used"] is True
    assert trace["iterations_run"] == 2
    assert len(trace["weak_corpus_recovery_queries"]) <= 4
    assert len(harness.search_calls) == 3


def test_recovery_queries_are_finalized_anchored_and_specific(tmp_path: Path) -> None:
    outcome, _harness = _run(tmp_path)

    queries = outcome.execution_trace["weak_corpus_recovery_queries"]
    assert 2 <= len(queries) <= 4
    assert all("Acme Widget" in q for q in queries)
    assert any("pricing" in q and "policy" in q and "deployment" in q for q in queries)
    assert any("official" in q for q in queries)


def test_recovery_queries_do_not_repeat_iteration_one_or_raw_user_query(tmp_path: Path) -> None:
    query = "What are expected numeric changes to Acme Widget in the upcoming patch notes"
    outcome, _harness = _run(
        tmp_path,
        query=query,
        core_topic="Acme Widget expected numeric changes upcoming patch notes",
        primary_entity="Acme Widget",
        researcher_query="Acme Widget 2026 news",
    )

    trace = outcome.execution_trace
    iter1 = {q.casefold() for q in trace["queries_per_iteration"]["1"]}
    recovery = trace["weak_corpus_recovery_queries"]
    assert recovery
    assert all(q.casefold() not in iter1 for q in recovery)
    assert all(q.casefold() != query.casefold() for q in recovery)
    assert all("Acme Widget" in q for q in recovery)
    assert any("numeric" in q and "changes" in q and "patch" in q for q in recovery)
    assert any("official patch notes" in q for q in recovery)


def test_recovery_query_specificity_works_for_policy_pricing_domain(tmp_path: Path) -> None:
    query = "Find official pricing policy changes for Contoso Cloud enterprise seats"
    outcome, _harness = _run(
        tmp_path,
        query=query,
        core_topic="Contoso Cloud enterprise seat pricing policy changes",
        primary_entity="Contoso Cloud",
        researcher_query="enterprise seat pricing policy",
    )

    recovery = outcome.execution_trace["weak_corpus_recovery_queries"]
    assert recovery
    assert all("Contoso Cloud" in q for q in recovery)
    assert all(q.casefold() != query.casefold() for q in recovery)
    assert any("pricing" in q and "policy" in q and "enterprise" in q for q in recovery)
    assert any("official policy" in q or "official pricing" in q for q in recovery)


def test_mid_iteration_disambiguation_queries_visible_in_telemetry(tmp_path: Path) -> None:
    outcome, harness = _run(tmp_path)

    disambig = outcome.execution_trace["disambiguation_queries_by_iteration"]
    assert outcome.execution_trace["retrieval_retry_used"] is True
    assert "1" in disambig
    assert disambig["1"] == harness.search_calls[1]
    assert outcome.execution_trace["queries_per_iteration"]["1"] == harness.search_calls[0]


def test_healthy_corpus_behavior_unchanged_no_recovery(tmp_path: Path) -> None:
    outcome, harness = _run(tmp_path, on_topic_first_pass=True)

    trace = outcome.execution_trace
    assert trace["corpus_weak"] is False
    assert trace["weak_corpus_recovery_used"] is False
    assert trace["weak_corpus_recovery_skip_reason"] == "not_weak_corpus"
    assert trace["weak_corpus_recovery_decision"] == "no_action"
    assert trace["weak_corpus_recovery_reason"] == "not_weak_corpus"
    assert trace["weak_corpus_recovery_blockers"] == []
    assert trace["iterations_run"] == 1
    assert len(harness.search_calls) == 1
    assert all(
        detail["provider_role"] != "weak_corpus_recovery"
        for detail in harness.search_call_details
    )


def test_weak_corpus_controller_fields_do_not_reach_author_prompt(
    tmp_path: Path,
) -> None:
    outcome, harness = _run(tmp_path)

    trace = outcome.execution_trace
    assert trace["weak_corpus_recovery_decision"] == "run_weak_corpus_recovery"
    assert harness.author_prompts
    for marker in (
        "weak_corpus_recovery_decision",
        "weak_corpus_recovery_blockers",
        "controller_diagnostics",
        "planned_vs_observed",
        "quantitative_packet",
        "economist_v1",
        "ECONOMIST FRAMEWORK",
    ):
        assert marker not in harness.author_prompts[-1]
