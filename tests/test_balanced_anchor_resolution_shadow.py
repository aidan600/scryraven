from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from core.anchor_resolution import (
    build_shadow_anchor_packet,
    format_anchor_context_for_researcher,
)
from core.cost_accounting import CostAccumulator
from core.pipeline_orchestrator import run_pipeline
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig, RunDeps
from tests.test_balanced_anchor_resolution_contract import ANCHOR_FIXTURES, AnchorFixture


def _fixture(fixture_id: str) -> AnchorFixture:
    return next(fixture for fixture in ANCHOR_FIXTURES if fixture.id == fixture_id)


def _packet_for_fixture(fixture: AnchorFixture, *, mode: str = "Balanced") -> dict[str, Any]:
    return build_shadow_anchor_packet(
        mode=mode,
        query=fixture.positive_request_shape,
        current_date="2026-05-18",
        intent="general",
        report_type="general_research",
        router_original_report_type="general_research",
        query_type="other",
        router_original_query_type="other",
        core_topic=fixture.positive_request_shape,
        primary_entity="",
        entities=[],
        router_entity_retry_used=False,
    )


def _all_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            out.append(str(key))
            out.extend(_all_strings(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_all_strings(item))
        return out
    return [value] if isinstance(value, str) else []


RAW_ANCHOR_MARKERS = (
    "anchor_packet",
    "anchor_packet_v1",
    "schema_version",
    "metadata",
    "answerability_forecast",
    "clarification_question",
)

QUANT_ECONOMIST_MARKERS = (
    "quantitative_packet",
    "quantitative_packet_v1",
    "ECONOMIST FRAMEWORK",
    "economist_v1",
    "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
)

ANCHOR_CONTEXT_MARKER = "ANCHOR CONTEXT"


def _assert_no_raw_or_quant_leakage(text: str) -> None:
    for marker in RAW_ANCHOR_MARKERS + QUANT_ECONOMIST_MARKERS:
        assert marker not in text


def _assert_no_user_or_author_leakage(text: str) -> None:
    _assert_no_raw_or_quant_leakage(text)
    assert ANCHOR_CONTEXT_MARKER not in text


@pytest.mark.parametrize("fixture", ANCHOR_FIXTURES, ids=lambda item: item.id)
def test_shadow_anchor_helper_matches_fixture_next_action_contract(
    fixture: AnchorFixture,
) -> None:
    telemetry = _packet_for_fixture(fixture)

    assert telemetry["anchor_packet_shadow_mode"] is True
    assert telemetry["anchor_packet_present"] is True
    assert telemetry["anchor_packet_next_action"] == fixture.expected_next_action
    assert telemetry["anchor_packet"]["next_action"] == fixture.expected_next_action


def test_shadow_anchor_helper_balanced_ambiguous_fixture_is_compact_packet() -> None:
    telemetry = _packet_for_fixture(_fixture("ambiguous_referent"))

    assert telemetry["anchor_packet_next_action"] == "preserve_multiple_frames"
    assert "referent" in telemetry["anchor_packet_ambiguity_types"]
    assert telemetry["anchor_packet_confidence_bucket"] in {"low", "medium"}
    assert telemetry["anchor_packet"]["selected_frame_id"] == ""
    assert len(json.dumps(telemetry, sort_keys=True)) < 3000
    assert max(len(text) for text in _all_strings(telemetry)) <= 240


def test_shadow_anchor_helper_simple_evergreen_proceeds_single_frame() -> None:
    telemetry = _packet_for_fixture(_fixture("simple_evergreen_negative_control"))

    assert telemetry["anchor_packet_next_action"] == "proceed_single_frame"
    assert telemetry["anchor_packet_confidence_bucket"] == "high"
    assert telemetry["anchor_packet_ambiguity_types"] == []
    assert telemetry["anchor_packet"]["freshness_requirement"] == "none"


def test_shadow_anchor_helper_non_balanced_returns_non_present_default() -> None:
    for mode in ("Fast", "Deep"):
        telemetry = _packet_for_fixture(_fixture("ambiguous_referent"), mode=mode)

        assert telemetry["anchor_packet_shadow_mode"] is True
        assert telemetry["anchor_packet_present"] is False
        assert telemetry["anchor_packet"] is None


def test_researcher_anchor_context_formatter_uses_allowlisted_plain_text() -> None:
    telemetry = _packet_for_fixture(_fixture("wrong_domain_frame"))

    context = format_anchor_context_for_researcher(telemetry)

    assert context.startswith("ANCHOR CONTEXT FOR QUERY DECOMPOSITION:")
    assert "- Frame: preserve multiple frames" in context
    assert "- Ambiguity:" in context
    assert "- Off-domain traps:" in context
    assert "nearby wrong-domain interpretation" in context
    assert "Use this only to preserve the intended frame" in context
    _assert_no_raw_or_quant_leakage(context)
    assert "likely non-public" not in context


def test_researcher_anchor_context_formatter_omits_simple_evergreen_noop() -> None:
    telemetry = _packet_for_fixture(_fixture("simple_evergreen_negative_control"))

    assert format_anchor_context_for_researcher(telemetry) == ""


class _AnchorHarness:
    def __init__(
        self,
        tmp_path: Path,
        *,
        query: str,
        router_report_type: str = "general_research",
        router_query_type: str = "product",
        core_topic: str = "Acme Widget policy",
        primary_entity: str = "Acme Widget",
        researcher_query: str = "Acme Widget policy",
    ) -> None:
        self.tmp_path = tmp_path
        self.query = query
        self.router_report_type = router_report_type
        self.router_query_type = router_query_type
        self.core_topic = core_topic
        self.primary_entity = primary_entity
        self.researcher_query = researcher_query
        self.event_order: list[str] = []
        self.researcher_calls = 0
        self.researcher_prompts: list[str] = []
        self.search_calls: list[dict[str, Any]] = []
        self.analyst_calls = 0
        self.author_prompts: list[str] = []

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt == DEFAULT_SYSTEM["router"]:
            self.event_order.append("router")
            return json.dumps(
                {
                    "intent": "general",
                    "report_type": self.router_report_type,
                    "image_mode": "none",
                    "core_topic": self.core_topic,
                    "is_academic": False,
                    "query_type": self.router_query_type,
                    "entities": [self.primary_entity],
                    "primary_entity": self.primary_entity,
                }
            )
        if system_prompt == "You are a concise title generator.":
            self.event_order.append("title")
            return f"{self.primary_entity} Research"
        if system_prompt == DEFAULT_SYSTEM["researcher"]:
            self.event_order.append("researcher")
            self.researcher_calls += 1
            self.researcher_prompts.append(prompt)
            return json.dumps({"queries": [self.researcher_query]})
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            self.event_order.append("analyst")
            self.analyst_calls += 1
            return f"Analysis remains focused on {self.primary_entity}."
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return json.dumps({"is_sufficient": True, "new_queries": []})
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if "research gap detector" in system_prompt:
            return json.dumps({"component_queries": [], "reasoning": "enough"})
        if kwargs.get("stream"):
            self.event_order.append("author")
            self.author_prompts.append(prompt)
            return (
                f"{self.primary_entity} is supported by official synthetic evidence. "
                f"The answer remains scoped to {self.core_topic}, with no extra "
                "provider calls, no model-derived quantitative packet, and no raw "
                "upstream framework exposed to the user."
            )
        return "ok"

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
        self.event_order.append("search")
        self.search_calls.append(
            {
                "queries": list(queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "search_providers": list(kwargs.get("search_providers") or []),
            }
        )
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is None and len(_args) >= 4:
            seen_urls = _args[3]
        passages: list[dict[str, Any]] = []
        for idx in range(4):
            url = f"https://example.com/{idx}"
            if seen_urls is not None:
                seen_urls.add(url)
            passages.append(
                {
                    "title": f"{self.primary_entity} official source {idx}",
                    "url": url,
                    "text": (
                        f"{self.primary_entity} official evidence for "
                        f"{self.core_topic} excerpt {idx}."
                    ),
                    "score": 1.0 - (idx * 0.01),
                    "credibility": 3,
                    "source_tier": "official",
                    "_provider": "tavily",
                }
            )
        return passages

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
            clean_json_response=lambda value: value,
            DEFAULT_SYSTEM=DEFAULT_SYSTEM,
            NEWS_PREFERRED_DOMAINS=[],
            ACADEMIC_DOMAINS=[],
            QUANT_REPORT_TYPES={"quantitative_comparison", "benchmark"},
            logger=logging.getLogger("test_balanced_anchor_resolution_shadow"),
            execution_log_path=self.tmp_path / "execution.jsonl",
            feedback_log_path=self.tmp_path / "feedback.jsonl",
            kb_triggers_path=self.tmp_path / "kb.jsonl",
            policy_state_path=self.tmp_path / "policy.json",
            policy_journal_path=self.tmp_path / "policy_journal.jsonl",
            provider_availability={"tavily": True},
        )


def _run_anchor_pipeline(
    tmp_path: Path,
    *,
    mode: str = "Balanced",
    query: str = "summarize current official requirement for Acme Widget",
    router_report_type: str = "general_research",
    router_query_type: str = "product",
    core_topic: str = "Acme Widget official requirement",
    primary_entity: str = "Acme Widget",
    researcher_query: str = "Acme Widget official requirement",
) -> tuple[Any, _AnchorHarness]:
    harness = _AnchorHarness(
        tmp_path,
        query=query,
        router_report_type=router_report_type,
        router_query_type=router_query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        researcher_query=researcher_query,
    )
    outcome = run_pipeline(
        RunConfig(
            query=query,
            mode=mode,
            current_date="2026-05-18",
            use_reasoning=False,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    return outcome, harness


def _execution_event_from_log(path: Path) -> dict[str, Any]:
    return next(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if json.loads(line).get("event") == "execution"
    )


def test_pipeline_attaches_anchor_packet_and_compact_researcher_context(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_anchor_pipeline(
        tmp_path,
        query="compare the latest rule for the service after it changed ownership",
        router_query_type="other",
        core_topic="latest service ownership rule",
        primary_entity="service",
        researcher_query="service ownership rule changed ownership",
    )
    trace = outcome.execution_trace
    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")

    assert trace["anchor_packet_shadow_mode"] is True
    assert trace["anchor_packet_present"] is True
    assert trace["anchor_packet_next_action"] == "preserve_multiple_frames"
    assert "referent" in trace["anchor_packet_ambiguity_types"]
    assert log_entry["execution_trace"]["anchor_packet_present"] is True
    assert "anchor_packet" not in log_entry
    assert "anchor_packet_present" not in log_entry

    assert harness.researcher_calls == 1
    assert harness.analyst_calls == 1
    assert len(harness.search_calls) == 2
    assert harness.search_calls[0]["search_depth"] == "basic"
    assert harness.search_calls[0]["complexity"] == "medium"
    assert harness.search_calls[0]["queries"] == trace["queries_per_iteration"]["1"]
    assert harness.search_calls[1]["search_depth"] == "basic"
    assert harness.search_calls[1]["queries"] == [
        "official current source latest service ownership rule"
    ]
    assert trace["weak_corpus_recovery_used"] is False

    researcher_prompt = harness.researcher_prompts[-1]
    author_prompt = harness.author_prompts[-1]
    assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" in researcher_prompt
    assert "Frame: preserve multiple frames" in researcher_prompt
    assert "Ambiguity:" in researcher_prompt
    assert "referent" in researcher_prompt
    assert "preserve-frame" in researcher_prompt
    assert any("changed ownership" in q for q in trace["queries_per_iteration"]["1"])
    _assert_no_raw_or_quant_leakage(researcher_prompt)
    _assert_no_user_or_author_leakage(author_prompt)
    _assert_no_user_or_author_leakage(outcome.report)


def test_retrieve_to_anchor_is_recommendation_only_without_active_probe(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_anchor_pipeline(
        tmp_path,
        query="summarize the current official requirement for this compliance action",
        router_query_type="other",
        core_topic="current official compliance requirement",
        primary_entity="compliance action",
        researcher_query="compliance action official requirement",
    )
    trace = outcome.execution_trace

    assert trace["anchor_packet_next_action"] == "retrieve_to_anchor"
    researcher_prompt = harness.researcher_prompts[-1]
    assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" in researcher_prompt
    assert "Time/Freshness: recent / official-current" in researcher_prompt
    assert "Expected source class: official" in researcher_prompt
    assert "include-official-source" in researcher_prompt
    assert len(harness.search_calls) == 1
    assert harness.event_order.index("researcher") < harness.event_order.index("search")
    assert trace["retrieval_retry_used"] is False
    assert trace["weak_corpus_recovery_used"] is False
    assert harness.search_calls[0]["search_depth"] == "basic"
    assert harness.search_calls[0]["complexity"] == "medium"


def test_wrong_domain_anchor_context_keeps_query_in_intended_domain(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_anchor_pipeline(
        tmp_path,
        query="explain the current margin requirement for the product class",
        router_query_type="other",
        core_topic="intended domain product class margin requirement",
        primary_entity="product class",
        researcher_query="intended domain product class margin requirement",
    )
    prompt = harness.researcher_prompts[-1]
    query_text = " ".join(outcome.execution_trace["queries_per_iteration"]["1"]).lower()

    assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" in prompt
    assert "Off-domain traps:" in prompt
    assert "nearby wrong-domain interpretation" in prompt
    assert "financial margin vs product-domain margin" in prompt
    assert "intended domain" in query_text
    assert len(harness.search_calls) == 1
    assert harness.search_calls[0]["search_depth"] == "basic"
    assert harness.search_calls[0]["complexity"] == "medium"


def test_metric_ambiguity_anchor_context_does_not_change_provider_or_depth(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_anchor_pipeline(
        tmp_path,
        query="rank these two groups by retention for the last reporting period",
        router_query_type="other",
        core_topic="groups retention last reporting period",
        primary_entity="groups",
        researcher_query="groups retention denominator reporting period",
    )
    prompt = harness.researcher_prompts[-1]

    assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" in prompt
    assert "metric" in prompt
    assert "Time/Freshness:" in prompt
    assert "retention denominator" in " ".join(
        outcome.execution_trace["queries_per_iteration"]["1"]
    )
    assert len(harness.search_calls) == 1
    assert harness.search_calls[0]["search_depth"] == "basic"
    assert harness.search_calls[0]["complexity"] == "medium"


def test_anchor_context_does_not_change_provider_selection(
    tmp_path: Path,
) -> None:
    _, anchored_harness = _run_anchor_pipeline(
        tmp_path / "anchored",
        query="rank these two groups by retention for the last reporting period",
        router_query_type="other",
        core_topic="groups retention last reporting period",
        primary_entity="groups",
        researcher_query="groups retention denominator reporting period",
    )
    _, baseline_harness = _run_anchor_pipeline(
        tmp_path / "baseline",
        query="define the standard term used for this general process",
        router_query_type="other",
        core_topic="standard term general process",
        primary_entity="general process",
        researcher_query="standard term general process",
    )

    assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" in anchored_harness.researcher_prompts[-1]
    assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" not in baseline_harness.researcher_prompts[-1]
    assert len(anchored_harness.search_calls) == 1
    assert len(baseline_harness.search_calls) == 1
    assert anchored_harness.search_calls[0]["search_depth"] == "basic"
    assert anchored_harness.search_calls[0]["complexity"] == "medium"
    assert anchored_harness.search_calls[0]["search_providers"] == (
        baseline_harness.search_calls[0]["search_providers"]
    )


def test_simple_evergreen_negative_control_has_no_meaningful_anchor_context(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_anchor_pipeline(
        tmp_path,
        query="define the standard term used for this general process",
        router_query_type="other",
        core_topic="standard term general process",
        primary_entity="general process",
        researcher_query="standard term general process",
    )

    assert outcome.execution_trace["anchor_packet_next_action"] == "proceed_single_frame"
    assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" not in harness.researcher_prompts[-1]
    assert outcome.execution_trace["queries_per_iteration"]["1"] == [
        "standard term general process"
    ]
    assert len(harness.search_calls) == 1


def test_explicit_proxy_negative_control_does_not_suppress_proxy_framing(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_anchor_pipeline(
        tmp_path,
        query="give a proxy or qualitative framing for the private category",
        router_query_type="other",
        core_topic="private category proxy qualitative framing",
        primary_entity="private category",
        researcher_query="private category proxy qualitative framing",
    )
    query_text = " ".join(outcome.execution_trace["queries_per_iteration"]["1"]).lower()

    assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" in harness.researcher_prompts[-1]
    assert "proxy" in query_text
    assert "qualitative" in query_text
    assert outcome.execution_trace["analyst_skipped"] is False
    assert harness.analyst_calls == 1
    assert len(harness.search_calls) == 1


def test_bounded_comparison_anchor_context_preserves_constraints(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_anchor_pipeline(
        tmp_path,
        query="compare these options only for the specified region and time window",
        router_query_type="comparison",
        core_topic="options specified region time window comparison",
        primary_entity="options",
        researcher_query="options specified region time window comparison",
    )
    prompt = harness.researcher_prompts[-1]
    query_text = " ".join(outcome.execution_trace["queries_per_iteration"]["1"]).lower()

    assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" in prompt
    assert "Time/Freshness:" in prompt
    assert "region" in query_text
    assert "time window" in query_text
    assert "without any region" not in query_text
    assert len(harness.search_calls) == 1


def test_anchor_context_does_not_create_retrieval_retry_or_extra_probe(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_anchor_pipeline(
        tmp_path,
        query="summarize the current official requirement for this compliance action",
        router_query_type="other",
        core_topic="current official compliance requirement",
        primary_entity="compliance action",
        researcher_query="compliance action official requirement",
    )
    trace = outcome.execution_trace

    assert trace["anchor_packet_next_action"] == "retrieve_to_anchor"
    assert harness.event_order.index("researcher") < harness.event_order.index("search")
    assert harness.event_order.count("researcher") == 1
    assert harness.event_order.count("search") == 1
    assert len(harness.search_calls) == 1
    assert trace["retrieval_retry_used"] is False
    assert trace["weak_corpus_recovery_used"] is False


def test_fast_and_deep_pipeline_runs_do_not_attach_anchor_packet(
    tmp_path: Path,
) -> None:
    for mode in ("Fast", "Deep"):
        outcome, harness = _run_anchor_pipeline(tmp_path / mode, mode=mode)
        trace = outcome.execution_trace
        log_entry = _execution_event_from_log(tmp_path / mode / "execution.jsonl")

        assert "anchor_packet" not in trace
        assert "anchor_packet_present" not in trace
        assert "anchor_packet" not in log_entry["execution_trace"]
        assert "anchor_packet_present" not in log_entry["execution_trace"]
        assert harness.researcher_prompts
        assert "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:" not in harness.researcher_prompts[-1]
        _assert_no_user_or_author_leakage(harness.researcher_prompts[-1])
        assert harness.author_prompts
        _assert_no_user_or_author_leakage(harness.author_prompts[-1])
        _assert_no_user_or_author_leakage(outcome.report)
