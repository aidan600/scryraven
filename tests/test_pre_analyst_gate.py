from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

import pytest

from core.corpus_state import CorpusState
from core.cost_accounting import CostAccumulator
from core.pipeline import detect_nutrition_lookup_telemetry
from core.pipeline_orchestrator import (
    _author_quant_source_telemetry_defaults,
    _economist_pre_analyst_skip_candidate_telemetry,
    _economist_skip_eligibility_shadow_telemetry,
    _economist_skip_shadow_alignment,
    _format_analyst_quant_packet_section,
    _format_nutrition_partial_evidence_author_note,
    _nutrition_macro_per_unit_lookup,
    _post_economist_analyst_gate,
    _pre_analyst_retrieval_gate,
    _query_expects_official_evidence,
    _scan_author_quant_source_telemetry,
    run_pipeline,
)
from core.post_author_output_projection import _final_answer_source_citation_telemetry
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig, RunDeps


def _gate(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query": "What changed in Acme Widget?",
        "report_type": "general_research",
        "query_type": "product",
        "corpus_state": CorpusState.HEALTHY.value,
        "corpus_weak": False,
        "failure_card_show": False,
        "utilization_rate_val": 0.9,
        "utilization_threshold": 0.25,
        "source_tier_counts": {"official": 3, "trusted_community": 1},
        "source_domain_counts": {"acme.com": 4},
        "top_source_domains": [{"domain": "acme.com", "count": 4}],
        "on_domain_source_count": 4,
        "official_evidence_found": True,
        "community_signal_found": True,
    }
    base.update(overrides)
    return _pre_analyst_retrieval_gate(**base)


def test_off_topic_corpus_skips_analyst() -> None:
    out = _gate(corpus_state=CorpusState.OFF_TOPIC.value, corpus_weak=True)
    assert out["analyst_skipped"] is True
    assert out["analyst_skip_reason"] == "corpus_off_topic"
    assert out["post_retrieval_fast_path_used"] is True


def test_failure_card_show_skips_analyst() -> None:
    out = _gate(failure_card_show=True)
    assert out["analyst_skipped"] is True
    assert out["analyst_skip_reason"] == "failure_card_shown"


def test_domain_specific_current_events_generic_news_only_skips_analyst() -> None:
    out = _gate(
        query="What happened with the Acme Cloud outage today?",
        query_type="current_events",
        utilization_rate_val=0.3,
        source_tier_counts={"unknown": 10},
        source_domain_counts={"apnews.com": 8, "abcnews.go.com": 2},
        top_source_domains=[{"domain": "apnews.com", "count": 8}],
        on_domain_source_count=0,
        official_evidence_found=False,
        community_signal_found=False,
    )
    assert out["analyst_skipped"] is True
    assert out["analyst_skip_reason"] in {
        "low_utilization_unknown_sources",
        "unsupported_off_domain_retrieval",
    }
    assert "generic_news_dominated" in out["pre_analyst_gate_signals"]
    assert "mostly_unknown_sources" in out["pre_analyst_gate_signals"]


def test_official_patch_note_query_missing_official_and_unknown_sources_skips_analyst() -> None:
    out = _gate(
        query="Expected numeric changes in Acme Widget patch notes",
        utilization_rate_val=0.28,
        source_tier_counts={"unknown": 12},
        source_domain_counts={"example-news.net": 9, "updates.example.org": 3},
        top_source_domains=[{"domain": "example-news.net", "count": 9}],
        on_domain_source_count=0,
        official_evidence_found=False,
        community_signal_found=False,
    )
    assert out["analyst_skipped"] is True
    assert out["analyst_skip_reason"] == "missing_expected_official_evidence"
    assert "missing_expected_official_evidence" in out["pre_analyst_gate_signals"]


def test_top_two_primary_system_does_not_imply_official_evidence_expectation() -> None:
    out = _gate(
        query="How does California's top-two primary system affect the governor race?",
        query_type="current_events",
        utilization_rate_val=0.28,
        source_tier_counts={"unknown": 8},
        source_domain_counts={"cbsnews.com": 4, "apnews.com": 4},
        top_source_domains=[{"domain": "cbsnews.com", "count": 4}],
        on_domain_source_count=0,
        official_evidence_found=False,
        community_signal_found=False,
    )

    assert "missing_expected_official_evidence" not in out["pre_analyst_gate_signals"]
    assert out["analyst_skip_reason"] != "missing_expected_official_evidence"


@pytest.mark.parametrize(
    "query",
    [
        "What changed in the primary election calendar?",
        "What is the enrollment trend for the primary school?",
        "What are primary care wait times this year?",
        "What primary color is used in the new logo?",
        "What is the primary reason customers switched providers?",
    ],
)
def test_bare_primary_does_not_imply_official_evidence_expectation(query: str) -> None:
    assert (
        _query_expects_official_evidence(
            query,
            report_type="general_research",
            query_type="current_events",
        )
        is False
    )


@pytest.mark.parametrize(
    "query",
    [
        "Find primary sources for the Acme pricing change.",
        "Compare primary documents about the Acme policy update.",
        "Use official or primary sources for the Acme incident timeline.",
        "Find company filings for Acme's reported margin change.",
        "Summarize Acme's reported company materials on the new margin target.",
        "What are the current eligibility requirements for the program?",
        "What are the official rules for program participation?",
    ],
)
def test_primary_source_phrases_and_official_materials_expect_official_evidence(
    query: str,
) -> None:
    assert (
        _query_expects_official_evidence(
            query,
            report_type="general_research",
            query_type="product",
        )
        is True
    )


def test_healthy_evidence_rich_corpus_does_not_skip_analyst() -> None:
    out = _gate(
        query="Summarize Acme Widget official pricing policy",
        utilization_rate_val=0.95,
        source_tier_counts={"official": 6, "trusted_community": 2},
        source_domain_counts={"acme.com": 6, "github.com": 2},
        top_source_domains=[{"domain": "acme.com", "count": 6}],
        on_domain_source_count=6,
        official_evidence_found=True,
        community_signal_found=True,
    )
    assert out["analyst_skipped"] is False
    assert out["analyst_skip_reason"] is None
    assert out["post_retrieval_fast_path_used"] is False


def test_mixed_official_and_secondary_source_diagnostics_do_not_skip_analyst() -> None:
    out = _gate(
        query="Summarize Acme Widget official pricing policy",
        utilization_rate_val=0.92,
        source_tier_counts={"official": 1, "secondary": 3, "unknown": 2},
        source_domain_counts={
            "acme.example": 1,
            "trade-press.example": 3,
            "analysis.example": 2,
        },
        top_source_domains=[{"domain": "trade-press.example", "count": 3}],
        on_domain_source_count=1,
        official_evidence_found=True,
        community_signal_found=False,
    )

    assert out["analyst_skipped"] is False
    assert out["analyst_skip_reason"] is None
    assert out["post_retrieval_fast_path_used"] is False


def test_community_signal_allowed_query_does_not_treat_community_as_weak() -> None:
    out = _gate(
        query="What are users discussing in forums about Acme Widget reliability?",
        utilization_rate_val=0.88,
        source_tier_counts={"trusted_community": 2, "social_or_forum": 2, "unknown": 1},
        source_domain_counts={
            "github.com": 2,
            "reddit.com": 2,
            "independent.example": 1,
        },
        top_source_domains=[{"domain": "github.com", "count": 2}],
        on_domain_source_count=0,
        official_evidence_found=False,
        community_signal_found=True,
    )

    assert out["analyst_skipped"] is False
    assert out["analyst_skip_reason"] is None
    assert "missing_expected_community_signal" not in out["pre_analyst_gate_signals"]
    assert "no_domain_relevant_source" in out["pre_analyst_gate_signals"]


def test_corpus_weak_gate_precedence_unchanged_by_source_diagnostics() -> None:
    out = _gate(
        corpus_weak=True,
        utilization_rate_val=0.95,
        source_tier_counts={"official": 3, "trusted_community": 2},
        source_domain_counts={"acme.example": 3, "github.com": 2},
        top_source_domains=[{"domain": "acme.example", "count": 3}],
        on_domain_source_count=3,
        official_evidence_found=True,
        community_signal_found=True,
    )

    assert out["analyst_skipped"] is True
    assert out["analyst_skip_reason"] == "corpus_weak"
    assert out["post_retrieval_fast_path_used"] is True


def test_final_answer_source_telemetry_exposes_packet_citation_divergence() -> None:
    telemetry = _final_answer_source_citation_telemetry(
        "Walmart revenue was higher [[9]](https://example.test/walmart).",
        {
            "quantitative_packet": {
                "source_ids_used": ["1", "8", "14"],
            }
        },
    )

    assert telemetry["final_answer_source_ids_used"] == ["9"]
    assert telemetry["final_answer_source_ids_not_in_packet"] == ["9"]
    assert telemetry["packet_source_ids_not_in_final_answer"] == ["1", "14", "8"]
    assert telemetry["final_answer_packet_source_ids_diverged"] is True
    assert telemetry["final_answer_source_telemetry_shadow_mode"] is True


class _PipelineHarness:
    def __init__(
        self,
        tmp_path: Path,
        *,
        healthy: bool,
        query: str = "Find official pricing policy changes for Acme Widget",
        router_report_type: str = "general_research",
        router_query_type: str = "product",
        core_topic: str = "Acme Widget official pricing policy",
        primary_entity: str = "Acme Widget",
        researcher_query: str = "Acme Widget pricing policy",
        evidence_texts: list[str] | None = None,
    ) -> None:
        self.tmp_path = tmp_path
        self.healthy = healthy
        self.query = query
        self.router_report_type = router_report_type
        self.router_query_type = router_query_type
        self.core_topic = core_topic
        self.primary_entity = primary_entity
        self.researcher_query = researcher_query
        self.evidence_texts = evidence_texts
        self.analyst_calls = 0
        self.author_prompts: list[str] = []

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt == DEFAULT_SYSTEM["router"]:
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
            return self.primary_entity
        if system_prompt == DEFAULT_SYSTEM["researcher"]:
            return json.dumps({"queries": [self.researcher_query]})
        if system_prompt.startswith("You are a search query expander"):
            return json.dumps({"component_queries": [], "reasoning": "enough"})
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return json.dumps({"is_sufficient": True, "new_queries": []})
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            self.analyst_calls += 1
            return f"Analysis: {self.primary_entity} is supported by official sources."
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if kwargs.get("stream"):
            self.author_prompts.append(prompt)
            if self.healthy:
                return (
                    f"{self.primary_entity} is supported by the official source. "
                    f"[Official {self.primary_entity} source](https://example.com/source)"
                )
            return (
                "There is no reliable evidence in the retrieved material for the requested "
                f"{self.primary_entity} claim. The retrieved pages were off-topic."
            )
        return "ok"

    def embed_texts(self, texts: list[str], **_kwargs: Any) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    def process_search_queries(self, queries: list[str], *_args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is None and len(_args) >= 8:
            seen_urls = _args[7]
        out: list[dict[str, Any]] = []
        for idx in range(4):
            if self.healthy:
                url = f"https://example.com/source/{idx}"
                title = f"{self.primary_entity} official source {idx}"
                text = (
                    self.evidence_texts[idx % len(self.evidence_texts)]
                    if self.evidence_texts
                    else f"{self.primary_entity} calories protein fat carbs per 100g evidence excerpt {idx}."
                )
                tier = "official"
            else:
                url = f"https://apnews.com/article/unrelated-{idx}"
                title = f"Unrelated general news {idx}"
                text = f"Unrelated Gadget general news excerpt {idx}."
                tier = "unknown"
            if seen_urls is not None:
                seen_urls.add(url)
            out.append(
                {
                    "title": title,
                    "url": url,
                    "text": text,
                    "score": 1.0 - (idx * 0.01),
                    "credibility": 3 if self.healthy else 1,
                    "source_tier": tier,
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
            QUANT_REPORT_TYPES={"quantitative_comparison", "benchmark"},
            logger=logging.getLogger("test_pre_analyst_gate"),
            execution_log_path=self.tmp_path / "execution.jsonl",
            feedback_log_path=self.tmp_path / "feedback.jsonl",
            kb_triggers_path=self.tmp_path / "kb.jsonl",
            policy_state_path=self.tmp_path / "policy.json",
            policy_journal_path=self.tmp_path / "policy_journal.jsonl",
            provider_availability={"tavily": True},
        )


def _run_pipeline_harness(
    tmp_path: Path,
    *,
    healthy: bool,
    mode: str = "Balanced",
    **harness_kwargs: Any,
):
    harness = _PipelineHarness(tmp_path, healthy=healthy, **harness_kwargs)
    outcome = run_pipeline(
        RunConfig(
            query=harness.query,
            mode=mode,
            current_date="2026-05-06",
            use_reasoning=False,
            forced_corpus_state=None if healthy else CorpusState.OFF_TOPIC.value,
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


def test_execution_log_includes_commit_sha_when_available(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(
        "core.pipeline_orchestrator.current_code_version_metadata",
        lambda: {"commit_sha": "abc123"},
    )

    outcome, _harness = _run_pipeline_harness(tmp_path, healthy=True)

    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")
    assert log_entry["commit_sha"] == "abc123"
    assert "commit_sha" not in outcome.execution_trace
    assert "commit_sha" not in log_entry["execution_trace"]


def test_execution_log_omits_commit_sha_when_unavailable(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(
        "core.pipeline_orchestrator.current_code_version_metadata",
        lambda: {},
    )

    outcome, _harness = _run_pipeline_harness(tmp_path, healthy=True)

    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")
    assert "commit_sha" not in log_entry
    assert "git_sha" not in log_entry
    assert "commit_sha" not in outcome.execution_trace
    assert "commit_sha" not in log_entry["execution_trace"]


def test_nutrition_macro_per_unit_lookup_positive_cases() -> None:
    assert _nutrition_macro_per_unit_lookup("silver round herring macros per 100g") is True
    assert _nutrition_macro_per_unit_lookup("salmon protein and calories per 100 g") is True


def test_nutrition_lookup_telemetry_detects_named_metrics_per_100g() -> None:
    telemetry = detect_nutrition_lookup_telemetry("salmon protein and calories per 100g")

    assert telemetry["nutrition_lookup_detected"] is True
    assert telemetry["nutrition_lookup_reason"] == "nutrition_metric_per_100g"
    assert telemetry["nutrition_lookup_unit"] == "per_100g"
    assert telemetry["nutrition_lookup_shadow_mode"] is True
    assert set(telemetry["nutrition_lookup_metrics_requested"]) >= {
        "protein",
        "calories",
    }


def test_nutrition_lookup_telemetry_expands_macros_per_100g() -> None:
    telemetry = detect_nutrition_lookup_telemetry("silver round herring macros per 100g")

    assert telemetry["nutrition_lookup_detected"] is True
    assert telemetry["nutrition_lookup_unit"] == "per_100g"
    assert set(telemetry["nutrition_lookup_metrics_requested"]) >= {
        "calories",
        "protein",
        "fat",
        "carbohydrates",
    }


def test_nutrition_macro_per_unit_lookup_negative_controls() -> None:
    assert _nutrition_macro_per_unit_lookup("silver round herring habitat and fishing season") is False
    assert _nutrition_macro_per_unit_lookup("herring recipe serving size") is False
    assert _nutrition_macro_per_unit_lookup("apple vs microsoft gross margin per 100 shares") is False
    assert _nutrition_macro_per_unit_lookup("calories in a restaurant menu item") is False


def test_nutrition_lookup_telemetry_negative_controls() -> None:
    for query in (
        "silver round herring habitat and fishing season",
        "herring recipe serving size",
        "apple vs microsoft gross margin per 100 shares",
    ):
        telemetry = detect_nutrition_lookup_telemetry(query)
        assert telemetry["nutrition_lookup_detected"] is False
        assert telemetry["nutrition_lookup_metrics_requested"] == []
        assert telemetry["nutrition_lookup_unit"] is None


def test_nutrition_partial_evidence_author_note_marks_missing_macro_fields() -> None:
    note = _format_nutrition_partial_evidence_author_note(
        nutrition_lookup_telemetry={
            "nutrition_lookup_detected": True,
            "nutrition_lookup_reason": "nutrition_metric_per_100g",
            "nutrition_lookup_metrics_requested": [
                "calories",
                "protein",
                "fat",
                "carbohydrates",
            ],
            "nutrition_lookup_unit": "per_100g",
            "nutrition_lookup_shadow_mode": True,
        },
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_sufficiency_valid": False,
            "quant_retrieval_sufficiency_blockers": [
                "nutrition_metrics_missing",
                "nutrition_partial_macro_coverage",
            ],
        },
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Silver round herring calories",
                "url": "https://nutrition.example/herring",
                "text": (
                    "Silver round herring has 93 calories per 100g. "
                    "No protein, fat, or carbohydrate panel is reported."
                ),
            }
        ],
    )

    assert "I found partial nutrition evidence, not a complete macro panel." in note
    assert "Calories" in note
    assert "93 calories per 100g" in note
    assert "Protein" in note
    assert "Fat" in note
    assert "Carbohydrates" in note
    assert note.count("Not found in retrieved evidence") == 3
    assert "20 g protein" not in note
    assert "5 g fat" not in note
    assert "1 g carbohydrates" not in note


def test_nutrition_partial_evidence_author_note_labels_proxy_evidence() -> None:
    note = _format_nutrition_partial_evidence_author_note(
        nutrition_lookup_telemetry={
            "nutrition_lookup_detected": True,
            "nutrition_lookup_reason": "nutrition_metric_per_100g",
            "nutrition_lookup_metrics_requested": [
                "calories",
                "protein",
                "fat",
                "carbohydrates",
            ],
            "nutrition_lookup_unit": "per_100g",
            "nutrition_lookup_shadow_mode": True,
        },
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_sufficiency_valid": False,
            "quant_retrieval_sufficiency_blockers": ["nutrition_partial_macro_coverage"],
        },
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Proxy/indirect nutrition source",
                "url": "https://nutrition.example/proxy",
                "text": "Proxy/indirect source reports 93 kcal per 100g for a nearest alternative.",
            }
        ],
    )

    assert "Calories | Found proxy/indirect | 93 kcal per 100g" in note


def test_nutrition_partial_evidence_author_note_non_nutrition_control() -> None:
    note = _format_nutrition_partial_evidence_author_note(
        nutrition_lookup_telemetry={
            "nutrition_lookup_detected": False,
            "nutrition_lookup_metrics_requested": [],
        },
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_sufficiency_valid": False,
        },
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Apple and Microsoft gross margin",
                "url": "https://example.com/margins",
                "text": "Apple gross margin and Microsoft gross margin are discussed.",
            }
        ],
    )

    assert note == ""


def test_nutrition_partial_evidence_author_prompt_includes_macro_table_instruction(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_pipeline_harness(
        tmp_path,
        healthy=True,
        query="silver round herring macros per 100g",
        router_report_type="general_research",
        router_query_type="product",
        core_topic="silver round herring macros per 100g",
        primary_entity="silver round herring",
        researcher_query="silver round herring calories per 100g",
        evidence_texts=[
            (
                "Silver round herring has 93 calories per 100g. "
                "No protein, fat, or carbohydrate panel is reported."
            )
        ],
    )

    trace = outcome.execution_trace
    assert trace["nutrition_lookup_detected"] is True
    assert trace["analyst_skipped_after_economist"] is False
    assert trace["economist_output_used_as_analysis"] is False
    assert harness.author_prompts
    prompt = harness.author_prompts[-1]
    assert "I found partial nutrition evidence, not a complete macro panel." in prompt
    assert "Calories" in prompt
    assert "Protein" in prompt
    assert "Fat" in prompt
    assert "Carbohydrates" in prompt
    assert prompt.count("Not found in retrieved evidence") == 3
    assert "93 calories per 100g" in prompt
    assert "quantitative_packet" not in prompt
    assert "QUANTITATIVE FRAMEWORK" not in prompt


def test_nutrition_macro_override_routes_to_quantitative_and_logs_telemetry(tmp_path: Path) -> None:
    outcome, harness = _run_pipeline_harness(
        tmp_path,
        healthy=True,
        mode="Balanced",
        query="silver round herring macros per 100g",
        router_report_type="general_research",
        router_query_type="product",
        core_topic="silver round herring macros per 100g",
        primary_entity="silver round herring",
        researcher_query="silver round herring macros per 100g",
    )
    trace = outcome.execution_trace

    assert harness.analyst_calls == 1
    assert trace["router_original_report_type"] == "general_research"
    assert trace["router_original_query_type"] == "product"
    assert trace["routing_override_applied"] is True
    assert trace["routing_override_reason"] == "nutrition_macro_per_100g_lookup"
    assert trace["report_type"] == "quantitative_comparison"
    assert trace["query_type"] == "product"
    assert trace["nutrition_lookup_detected"] is True
    assert trace["nutrition_lookup_unit"] == "per_100g"
    assert set(trace["nutrition_lookup_metrics_requested"]) >= {
        "calories",
        "protein",
        "fat",
        "carbohydrates",
    }
    assert trace["quant_retrieval_sufficiency_valid"] is False
    assert "comparison_subjects_unknown" not in trace["quant_retrieval_sufficiency_blockers"]
    assert "nutrition_value_source_binding_missing" in trace[
        "quant_retrieval_sufficiency_blockers"
    ]
    assert trace["analyst_skipped_after_economist"] is False
    assert trace["economist_output_used_as_analysis"] is False

    log_entry = next(
        json.loads(line)
        for line in (tmp_path / "execution.jsonl").read_text().splitlines()
        if json.loads(line).get("event") == "execution"
    )
    assert log_entry["router_original_report_type"] == "general_research"
    assert log_entry["router_original_query_type"] == "product"
    assert log_entry["routing_override_applied"] is True
    assert log_entry["routing_override_reason"] == "nutrition_macro_per_100g_lookup"
    assert log_entry["report_type"] == "quantitative_comparison"
    assert log_entry["query_type"] == "product"
    assert log_entry["nutrition_lookup_detected"] is True
    assert log_entry["nutrition_lookup_unit"] == "per_100g"
    assert log_entry["execution_trace"]["routing_override_applied"] is True
    assert log_entry["execution_trace"]["routing_override_reason"] == (
        "nutrition_macro_per_100g_lookup"
    )
    assert log_entry["execution_trace"]["nutrition_lookup_detected"] is True
    assert log_entry["execution_trace"]["nutrition_lookup_unit"] == "per_100g"
    assert "comparison_subjects_unknown" not in log_entry["execution_trace"][
        "quant_retrieval_sufficiency_blockers"
    ]
    assert log_entry["execution_trace"]["analyst_skipped_after_economist"] is False
    assert log_entry["execution_trace"]["economist_output_used_as_analysis"] is False


def test_nutrition_macro_override_applies_to_spaced_100g_query(tmp_path: Path) -> None:
    outcome, _harness = _run_pipeline_harness(
        tmp_path,
        healthy=True,
        mode="Balanced",
        query="salmon protein and calories per 100 g",
        router_report_type="general_research",
        router_query_type="product",
        core_topic="salmon protein and calories per 100 g",
        primary_entity="salmon",
        researcher_query="salmon protein calories per 100 g",
    )
    trace = outcome.execution_trace

    assert trace["routing_override_applied"] is True
    assert trace["routing_override_reason"] == "nutrition_macro_per_100g_lookup"
    assert trace["report_type"] == "quantitative_comparison"
    assert trace["query_type"] == "product"
    assert trace["nutrition_lookup_detected"] is True
    assert trace["nutrition_lookup_unit"] == "per_100g"
    assert set(trace["nutrition_lookup_metrics_requested"]) >= {"protein", "calories"}


def test_nutrition_macro_override_does_not_fire_for_habitat_query(tmp_path: Path) -> None:
    outcome, _harness = _run_pipeline_harness(
        tmp_path,
        healthy=True,
        mode="Balanced",
        query="silver round herring habitat and fishing season",
        router_report_type="general_research",
        router_query_type="product",
        core_topic="silver round herring habitat and fishing season",
        primary_entity="silver round herring",
        researcher_query="silver round herring habitat fishing season",
    )
    trace = outcome.execution_trace

    assert trace["router_original_report_type"] == "general_research"
    assert trace["router_original_query_type"] == "product"
    assert trace["routing_override_applied"] is False
    assert trace["routing_override_reason"] is None
    assert trace["report_type"] == "general_research"
    assert trace["query_type"] == "product"
    assert trace["nutrition_lookup_detected"] is False


def test_skipped_analyst_still_produces_displayable_author_output_and_telemetry(tmp_path: Path) -> None:
    outcome, harness = _run_pipeline_harness(tmp_path, healthy=False)
    trace = outcome.execution_trace

    assert harness.analyst_calls == 0
    assert outcome.report.strip()
    assert trace["response_displayable"] is True
    assert trace["analyst_skipped"] is True
    assert trace["analyst_skip_reason"] == "corpus_off_topic"
    assert trace["post_retrieval_fast_path_used"] is True
    assert isinstance(trace["pre_analyst_gate_signals"], list)
    assert trace["timing"]["analyst_seconds"] == 0.0

    log_entry = next(
        json.loads(line)
        for line in (tmp_path / "execution.jsonl").read_text().splitlines()
        if json.loads(line).get("event") == "execution"
    )
    assert log_entry["analyst_skipped"] is True
    assert log_entry["analyst_skip_reason"] == "corpus_off_topic"
    assert log_entry["post_retrieval_fast_path_used"] is True
    assert isinstance(log_entry["pre_analyst_gate_signals"], list)


def test_healthy_evidence_rich_pipeline_still_runs_analyst(tmp_path: Path) -> None:
    outcome, harness = _run_pipeline_harness(tmp_path, healthy=True)
    trace = outcome.execution_trace

    assert harness.analyst_calls == 1
    assert trace["analyst_skipped"] is False
    assert trace["analyst_skip_reason"] is None
    assert trace["post_retrieval_fast_path_used"] is False


ECONOMIST_BLOCK = (
    "## QUANTITATIVE FRAMEWORK (MODEL-DERIVED - not sourced from web evidence)\n"
    "**Normalization approach:** Compare the last four automotive gross margin percentages.\n\n"
    "**Computed results:**\n"
    "- trend: 18.5% -> 18.9% -> 19.3% -> 20.1%\n"
    "- direction: improving"
)


def _valid_revenue_packet_telemetry() -> dict[str, Any]:
    return {
        "economist_schema_version": "economist_v1",
        "economist_schema_valid": True,
        "economist_invalid_fields": [],
        "unsupported_values_count": 0,
        "economist_shadow_mode": True,
        "source_binding_valid": True,
        "source_bound_value_count": 2,
        "source_binding_invalid_fields": [],
        "source_binding_missing_source_id_count": 0,
        "source_binding_unknown_source_id_count": 0,
        "source_binding_malformed_count": 0,
        "source_ids_seen": ["1", "2", "3", "4"],
        "source_ids_used": ["1", "2"],
        "source_binding_shadow_mode": True,
        "calculation_requests_count": 1,
        "calculation_success_count": 1,
        "calculation_error_count": 0,
        "unsupported_calculation_names": [],
        "calculation_input_binding_valid": True,
        "calculation_input_binding_error_count": 0,
        "calculation_unresolved_input_refs": [],
        "calculation_results_count": 1,
        "calculation_results_shadow_mode": True,
        "calculation_results": [
            {
                "name": "percent_change",
                "result": 0.5,
                "input_refs": {"old": "old_revenue", "new": "new_revenue"},
            }
        ],
        "target_metric_detected": True,
        "target_metric_names": ["growth_change"],
        "target_metric_evidence_found": True,
        "target_metric_bound_value_refs": [],
        "target_metric_calculation_refs": ["percent_change"],
        "target_metric_missing": [],
        "target_metric_shadow_would_block": False,
        "target_metric_gate_reason": "target_metric_supported_by_calculation",
        "target_metric_shadow_mode": True,
        "high_stakes_quant_detected": False,
        "high_stakes_quant_domain": None,
        "high_stakes_quant_reasons": [],
        "high_stakes_quant_requires_analyst": False,
        "high_stakes_quant_shadow_mode": True,
        "high_stakes_quant_future_direct_use_allowed": True,
        "high_stakes_quant_gate_reason": "not_high_stakes_quantitative",
        "quantitative_packet_present": True,
        "quantitative_packet_valid": True,
        "quantitative_packet_validation_errors": [],
        "quantitative_packet_direct_use_eligible": True,
        "quantitative_packet_requires_analyst": False,
        "quantitative_packet_shadow_mode": True,
        "quantitative_packet_gate_reason": "valid_non_high_stakes_packet",
        "quantitative_packet": {
            "schema_version": "quantitative_packet_v1",
            "query": "What was revenue growth?",
            "economist_schema_version": "economist_v1",
            "source_ids_used": ["1", "2"],
            "source_bound_values": [
                {"name": "old_revenue", "value": "100", "unit": "USD", "source_id": "1"},
                {"name": "new_revenue", "value": "150", "unit": "USD", "source_id": "2"},
            ],
            "calculation_results": [
                {
                    "name": "percent_change",
                    "result": 0.5,
                    "input_refs": {"old": "old_revenue", "new": "new_revenue"},
                }
            ],
            "target_metric_names": ["growth_change"],
            "target_metric_bound_value_refs": [],
            "target_metric_calculation_refs": ["percent_change"],
            "unsupported_values_count": 0,
            "high_stakes_quant_detected": False,
            "high_stakes_quant_domain": None,
            "requires_analyst": False,
            "direct_use_eligible": True,
            "validation_errors": [],
        },
    }


def _valid_quant_retrieval_sufficiency_telemetry() -> dict[str, Any]:
    return {
        "quant_retrieval_target_detected": True,
        "quant_retrieval_sufficiency_valid": True,
        "quant_retrieval_sufficiency_blockers": [],
        "quant_retrieval_sufficiency_gate_reason": "sufficient_shadow_only",
        "quant_retrieval_sufficiency_shadow_mode": True,
    }


def _shadow_eligibility_base(**overrides: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "report_type": "quantitative_comparison",
        "complexity": "medium",
        "mode": "Balanced",
        "economist_safety_telemetry": copy.deepcopy(_valid_revenue_packet_telemetry()),
        "quant_retrieval_sufficiency_telemetry": (
            _valid_quant_retrieval_sufficiency_telemetry()
        ),
        "analyst_quant_packet_handoff_telemetry": {
            "analyst_quant_packet_reviewed_by_model": True,
            "analyst_model_called": True,
        },
        "author_quant_source_telemetry": {
            "author_quant_content_source": "analyst_reviewed",
            "author_received_raw_quant_packet": False,
            "author_received_economist_framework": False,
            "author_received_analyst_packet_marker": False,
        },
        "analyst_skipped_after_economist": False,
        "economist_output_used_as_analysis": False,
        "pre_analyst_gate_skipped": False,
    }
    args.update(overrides)
    return _economist_skip_eligibility_shadow_telemetry(**args)


def _pre_analyst_candidate_base(**overrides: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "report_type": "quantitative_comparison",
        "complexity": "medium",
        "mode": "Balanced",
        "economist_safety_telemetry": copy.deepcopy(_valid_revenue_packet_telemetry()),
        "quant_retrieval_sufficiency_telemetry": (
            _valid_quant_retrieval_sufficiency_telemetry()
        ),
    }
    args.update(overrides)
    return _economist_pre_analyst_skip_candidate_telemetry(**args)


def test_pre_analyst_candidate_positive_clean_quantitative_case() -> None:
    telemetry = _pre_analyst_candidate_base()

    assert telemetry["economist_pre_analyst_skip_candidate_shadow"] is True
    assert telemetry["economist_pre_analyst_skip_candidate_gate_reason"] == (
        "candidate_shadow_only"
    )
    assert telemetry["economist_pre_analyst_skip_candidate_blockers"] == []
    assert "bounded_quantitative_report" in telemetry[
        "economist_pre_analyst_skip_candidate_reasons"
    ]
    assert "retrieval_sufficiency_valid" in telemetry[
        "economist_pre_analyst_skip_candidate_reasons"
    ]


def test_pre_analyst_candidate_blocks_high_stakes_quant() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry.update(
        {
            "high_stakes_quant_detected": True,
            "quantitative_packet_direct_use_eligible": False,
            "quantitative_packet_requires_analyst": True,
        }
    )

    telemetry = _pre_analyst_candidate_base(
        economist_safety_telemetry=safety_telemetry
    )

    assert telemetry["economist_pre_analyst_skip_candidate_shadow"] is False
    assert "high_stakes_requires_analyst" in telemetry[
        "economist_pre_analyst_skip_candidate_blockers"
    ]
    assert telemetry["economist_pre_analyst_skip_candidate_gate_reason"] == (
        "blocked_by_high_stakes"
    )


def test_pre_analyst_candidate_blocks_invalid_packet() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry.update(
        {
            "quantitative_packet_valid": False,
            "quantitative_packet_direct_use_eligible": False,
            "quantitative_packet_requires_analyst": True,
        }
    )

    telemetry = _pre_analyst_candidate_base(
        economist_safety_telemetry=safety_telemetry
    )

    assert telemetry["economist_pre_analyst_skip_candidate_shadow"] is False
    assert "packet_invalid_or_missing" in telemetry[
        "economist_pre_analyst_skip_candidate_blockers"
    ]
    assert telemetry["economist_pre_analyst_skip_candidate_gate_reason"] == (
        "blocked_by_invalid_packet"
    )


def test_pre_analyst_candidate_blocks_retrieval_insufficiency() -> None:
    telemetry = _pre_analyst_candidate_base(
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_target_detected": True,
            "quant_retrieval_sufficiency_valid": False,
        }
    )

    assert telemetry["economist_pre_analyst_skip_candidate_shadow"] is False
    assert "retrieval_sufficiency_failed" in telemetry[
        "economist_pre_analyst_skip_candidate_blockers"
    ]
    assert telemetry["economist_pre_analyst_skip_candidate_gate_reason"] == (
        "blocked_by_retrieval_sufficiency"
    )


def test_pre_analyst_candidate_blocks_missing_retrieval_sufficiency() -> None:
    telemetry = _pre_analyst_candidate_base(
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_target_detected": False,
            "quant_retrieval_sufficiency_valid": False,
        }
    )

    assert telemetry["economist_pre_analyst_skip_candidate_shadow"] is False
    assert "retrieval_sufficiency_missing" in telemetry[
        "economist_pre_analyst_skip_candidate_blockers"
    ]
    assert telemetry["economist_pre_analyst_skip_candidate_gate_reason"] == (
        "blocked_by_retrieval_sufficiency"
    )


def test_pre_analyst_candidate_blocks_general_research() -> None:
    telemetry = _pre_analyst_candidate_base(report_type="general_research")

    assert telemetry["economist_pre_analyst_skip_candidate_shadow"] is False
    assert "non_bounded_quantitative_report" in telemetry[
        "economist_pre_analyst_skip_candidate_blockers"
    ]
    assert telemetry["economist_pre_analyst_skip_candidate_gate_reason"] == (
        "blocked_by_report_type"
    )


def test_pre_analyst_candidate_blocks_code_request() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry["economist_code_execution_requested"] = True

    telemetry = _pre_analyst_candidate_base(
        economist_safety_telemetry=safety_telemetry
    )

    assert telemetry["economist_pre_analyst_skip_candidate_shadow"] is False
    assert "economist_code_execution_requested" in telemetry[
        "economist_pre_analyst_skip_candidate_blockers"
    ]
    assert telemetry["economist_pre_analyst_skip_candidate_gate_reason"] == (
        "blocked_by_code_request"
    )


def test_skip_shadow_alignment_values() -> None:
    pre_candidate = {
        "economist_pre_analyst_skip_candidate_shadow": True,
    }
    pre_blocked = {
        "economist_pre_analyst_skip_candidate_shadow": False,
    }
    post_eligible = {"economist_skip_eligible_shadow": True}
    post_blocked = {"economist_skip_eligible_shadow": False}

    assert _economist_skip_shadow_alignment(
        pre_analyst_candidate_telemetry=pre_candidate,
        posthoc_skip_eligibility_telemetry=post_eligible,
    ) == "candidate_and_posthoc_eligible"
    assert _economist_skip_shadow_alignment(
        pre_analyst_candidate_telemetry=pre_candidate,
        posthoc_skip_eligibility_telemetry=post_blocked,
    ) == "candidate_only"
    assert _economist_skip_shadow_alignment(
        pre_analyst_candidate_telemetry=pre_blocked,
        posthoc_skip_eligibility_telemetry=post_eligible,
    ) == "posthoc_only"
    assert _economist_skip_shadow_alignment(
        pre_analyst_candidate_telemetry=pre_blocked,
        posthoc_skip_eligibility_telemetry=post_blocked,
    ) == "neither"
    assert _economist_skip_shadow_alignment(
        pre_analyst_candidate_telemetry=None,
        posthoc_skip_eligibility_telemetry=post_blocked,
    ) == "not_evaluated"


def test_author_quant_source_telemetry_defaults() -> None:
    assert _author_quant_source_telemetry_defaults() == {
        "author_quant_content_source": "none",
        "author_received_raw_quant_packet": False,
        "author_received_economist_framework": False,
        "author_received_analyst_packet_marker": False,
        "author_quant_handoff_gate_reason": "no_quantitative_author_handoff_detected",
    }


def test_author_prompt_raw_packet_marker_scan_is_telemetry_only() -> None:
    telemetry = _scan_author_quant_source_telemetry(
        "Analysis includes quantitative_packet_v1 details for inspection only.",
        analyst_quant_packet_reviewed_by_model=False,
        analysis=None,
    )

    assert telemetry["author_received_raw_quant_packet"] is True
    assert telemetry["author_received_analyst_packet_marker"] is False
    assert telemetry["author_received_economist_framework"] is False
    assert telemetry["author_quant_content_source"] == "raw_quant_packet_detected"
    assert telemetry["author_quant_handoff_gate_reason"] == (
        "author_prompt_contains_raw_quant_packet"
    )


def test_author_prompt_analyst_packet_marker_scan_is_telemetry_only() -> None:
    telemetry = _scan_author_quant_source_telemetry(
        "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY\nPacket JSON: {}",
        analyst_quant_packet_reviewed_by_model=False,
        analysis=None,
    )

    assert telemetry["author_received_raw_quant_packet"] is False
    assert telemetry["author_received_analyst_packet_marker"] is True
    assert telemetry["author_received_economist_framework"] is False
    assert telemetry["author_quant_content_source"] == "analyst_packet_marker_detected"
    assert telemetry["author_quant_handoff_gate_reason"] == (
        "author_prompt_contains_analyst_packet_marker"
    )


def test_author_prompt_economist_framework_marker_scan_is_telemetry_only() -> None:
    telemetry = _scan_author_quant_source_telemetry(
        "QUANTITATIVE FRAMEWORK (CANONICAL)\n- computed value: 42",
        analyst_quant_packet_reviewed_by_model=False,
        analysis=None,
    )

    assert telemetry["author_received_raw_quant_packet"] is False
    assert telemetry["author_received_analyst_packet_marker"] is False
    assert telemetry["author_received_economist_framework"] is True
    assert telemetry["author_quant_content_source"] == "raw_economist_block_detected"
    assert telemetry["author_quant_handoff_gate_reason"] == (
        "author_prompt_contains_economist_framework"
    )


def test_author_prompt_static_framework_instruction_is_not_raw_economist_block() -> None:
    telemetry = _scan_author_quant_source_telemetry(
        (
            "NOTE FOR AUTHOR — QUANTITATIVE FRAMEWORK NOT RUN:\n"
            "Answer from available evidence; do not present a quantitative framework "
            "or MODEL-DERIVED tables."
        ),
        analyst_quant_packet_reviewed_by_model=False,
        analysis=None,
    )

    assert telemetry["author_received_raw_quant_packet"] is False
    assert telemetry["author_received_analyst_packet_marker"] is False
    assert telemetry["author_received_economist_framework"] is False
    assert telemetry["author_quant_content_source"] == "none"
    assert telemetry["author_quant_handoff_gate_reason"] == (
        "no_quantitative_author_handoff_detected"
    )


def test_author_prompt_framework_not_shown_instruction_is_not_raw_economist_block() -> None:
    telemetry = _scan_author_quant_source_telemetry(
        (
            "NOTE FOR AUTHOR — QUANTITATIVE FRAMEWORK NOT SHOWN "
            "(INSUFFICIENT RETRIEVED EVIDENCE):\n"
            "Do not display MODEL-DERIVED tables, comparison matrices, invented "
            "scaling exponents, or numeric results from the QUANTITATIVE FRAMEWORK block."
        ),
        analyst_quant_packet_reviewed_by_model=False,
        analysis=None,
    )

    assert telemetry["author_received_economist_framework"] is False
    assert telemetry["author_quant_content_source"] == "none"


def test_author_prompt_legacy_framework_block_still_detected() -> None:
    telemetry = _scan_author_quant_source_telemetry(
        (
            "LEGACY QUANTITATIVE FRAMEWORK (UNREVIEWED - not Author-ready evidence)\n"
            "NUMERIC RENDERING: Render numeric values from the framework as readable text.\n"
            "## QUANTITATIVE FRAMEWORK (MODEL-DERIVED - not sourced from web evidence)\n"
            "**Normalization approach:** Compare two reported values.\n"
            "**Computed results:**\n"
            "- computed value: 42"
        ),
        analyst_quant_packet_reviewed_by_model=False,
        analysis=None,
    )

    assert telemetry["author_received_economist_framework"] is True
    assert telemetry["author_quant_content_source"] == "raw_economist_block_detected"


def test_shadow_skip_eligibility_blocks_general_research_even_with_valid_packet() -> None:
    telemetry = _shadow_eligibility_base(report_type="general_research")

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "non_bounded_quantitative_report" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == "blocked_by_report_type"
    assert telemetry["economist_skip_eligibility_shadow_mode"] is True


def test_shadow_skip_eligibility_blocks_author_marker_leaks() -> None:
    telemetry = _shadow_eligibility_base(
        author_quant_source_telemetry={
            "author_quant_content_source": "raw_quant_packet_detected",
            "author_received_raw_quant_packet": True,
            "author_received_economist_framework": True,
            "author_received_analyst_packet_marker": False,
        },
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "author_raw_packet_marker_detected" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "author_framework_marker_detected" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_author_marker_leak"
    )


def test_shadow_skip_eligibility_blocks_economist_code_request() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry["economist_code_execution_requested"] = True

    telemetry = _shadow_eligibility_base(economist_safety_telemetry=safety_telemetry)

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "economist_code_execution_requested" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == "blocked_by_code_request"


def test_shadow_skip_calibration_clean_quantitative_comparison_is_eligible() -> None:
    telemetry = _shadow_eligibility_base(report_type="quantitative_comparison")

    assert telemetry["economist_skip_eligible_shadow"] is True
    assert telemetry["economist_skip_eligibility_gate_reason"] == "eligible_shadow_only"
    assert telemetry["economist_skip_eligibility_blockers"] == []
    assert "bounded_quantitative_report" in telemetry[
        "economist_skip_eligibility_reasons"
    ]
    assert "valid_direct_use_packet" in telemetry["economist_skip_eligibility_reasons"]
    assert "analyst_reviewed_packet" in telemetry["economist_skip_eligibility_reasons"]
    assert "retrieval_sufficiency_valid" in telemetry[
        "economist_skip_eligibility_reasons"
    ]


def test_shadow_skip_calibration_benchmark_report_is_eligible_when_clean() -> None:
    telemetry = _shadow_eligibility_base(report_type="benchmark")

    assert telemetry["economist_skip_eligible_shadow"] is True
    assert telemetry["economist_skip_eligibility_gate_reason"] == "eligible_shadow_only"
    assert telemetry["economist_skip_eligibility_blockers"] == []
    assert "bounded_quantitative_report" in telemetry[
        "economist_skip_eligibility_reasons"
    ]


def test_shadow_skip_blocks_failed_retrieval_sufficiency() -> None:
    telemetry = _shadow_eligibility_base(
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_target_detected": True,
            "quant_retrieval_sufficiency_valid": False,
            "quant_retrieval_sufficiency_blockers": ["missing_metric_coverage"],
            "quant_retrieval_sufficiency_gate_reason": "blocked_by_missing_metric",
            "quant_retrieval_sufficiency_shadow_mode": True,
        }
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "retrieval_sufficiency_failed" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_retrieval_sufficiency"
    )


def test_shadow_skip_blocks_missing_retrieval_sufficiency_target() -> None:
    telemetry = _shadow_eligibility_base(
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_target_detected": False,
            "quant_retrieval_sufficiency_valid": False,
            "quant_retrieval_sufficiency_blockers": [],
            "quant_retrieval_sufficiency_gate_reason": "not_quantitative_target",
            "quant_retrieval_sufficiency_shadow_mode": True,
        }
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "retrieval_sufficiency_missing" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_retrieval_sufficiency"
    )


def test_shadow_skip_blocks_missing_retrieval_sufficiency_telemetry() -> None:
    telemetry = _shadow_eligibility_base(quant_retrieval_sufficiency_telemetry=None)

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "retrieval_sufficiency_missing" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_retrieval_sufficiency"
    )


def test_shadow_skip_general_research_keeps_report_type_priority_without_retrieval() -> None:
    telemetry = _shadow_eligibility_base(
        report_type="general_research",
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_target_detected": False,
            "quant_retrieval_sufficiency_valid": False,
        },
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "non_bounded_quantitative_report" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "retrieval_sufficiency_missing" not in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == "blocked_by_report_type"


def test_shadow_skip_calibration_high_stakes_packet_is_blocked() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry.update(
        {
            "high_stakes_quant_detected": True,
            "high_stakes_quant_domain": "medical",
            "high_stakes_quant_requires_analyst": True,
            "high_stakes_quant_future_direct_use_allowed": False,
            "high_stakes_quant_gate_reason": "medical_quantitative_requires_analyst",
            "quantitative_packet_direct_use_eligible": False,
            "quantitative_packet_requires_analyst": True,
            "quantitative_packet_gate_reason": "high_stakes_requires_analyst",
        }
    )

    telemetry = _shadow_eligibility_base(
        economist_safety_telemetry=safety_telemetry,
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_target_detected": True,
            "quant_retrieval_sufficiency_valid": False,
        },
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "high_stakes_requires_analyst" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "retrieval_sufficiency_failed" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == "blocked_by_high_stakes"


def test_shadow_skip_calibration_missing_target_packet_is_blocked() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry.update(
        {
            "target_metric_detected": False,
            "target_metric_missing": ["growth_change"],
            "target_metric_shadow_would_block": True,
            "target_metric_gate_reason": "target_metric_missing",
            "quantitative_packet_valid": False,
            "quantitative_packet_validation_errors": ["target_metric_evidence_missing"],
            "quantitative_packet_direct_use_eligible": False,
            "quantitative_packet_requires_analyst": True,
            "quantitative_packet_gate_reason": "packet_validation_failed",
        }
    )

    telemetry = _shadow_eligibility_base(
        economist_safety_telemetry=safety_telemetry,
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_target_detected": True,
            "quant_retrieval_sufficiency_valid": False,
        },
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "packet_invalid_or_missing" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "retrieval_sufficiency_failed" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_invalid_packet"
    )


def test_shadow_skip_calibration_valid_packet_not_direct_use_is_blocked() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry.update(
        {
            "quantitative_packet_valid": True,
            "quantitative_packet_direct_use_eligible": False,
            "quantitative_packet_requires_analyst": False,
            "quantitative_packet_gate_reason": "not_direct_use_eligible",
        }
    )

    telemetry = _shadow_eligibility_base(economist_safety_telemetry=safety_telemetry)

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "packet_not_direct_use_eligible" in telemetry[
        "economist_skip_eligibility_blockers"
    ]


def test_shadow_skip_calibration_packet_requires_analyst_is_blocked() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry.update(
        {
            "quantitative_packet_valid": True,
            "quantitative_packet_direct_use_eligible": True,
            "quantitative_packet_requires_analyst": True,
            "quantitative_packet_gate_reason": "requires_analyst",
        }
    )

    telemetry = _shadow_eligibility_base(economist_safety_telemetry=safety_telemetry)

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "packet_requires_analyst" in telemetry[
        "economist_skip_eligibility_blockers"
    ]


def test_shadow_skip_calibration_model_called_without_review_is_blocked() -> None:
    telemetry = _shadow_eligibility_base(
        analyst_quant_packet_handoff_telemetry={
            "analyst_quant_packet_reviewed_by_model": False,
            "analyst_model_called": True,
        },
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "packet_not_reviewed_by_analyst" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "analyst_model_not_called" not in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_missing_analyst_review"
    )


def test_shadow_skip_calibration_author_not_analyst_reviewed_is_blocked() -> None:
    telemetry = _shadow_eligibility_base(
        author_quant_source_telemetry={
            "author_quant_content_source": "none",
            "author_received_raw_quant_packet": False,
            "author_received_economist_framework": False,
            "author_received_analyst_packet_marker": False,
        },
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "author_not_analyst_reviewed" in telemetry[
        "economist_skip_eligibility_blockers"
    ]


def test_shadow_skip_calibration_author_raw_marker_leak_is_blocked() -> None:
    telemetry = _shadow_eligibility_base(
        author_quant_source_telemetry={
            "author_quant_content_source": "raw_quant_packet_detected",
            "author_received_raw_quant_packet": True,
            "author_received_economist_framework": False,
            "author_received_analyst_packet_marker": False,
        },
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "author_raw_packet_marker_detected" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_author_marker_leak"
    )


def test_shadow_skip_calibration_marker_leak_priority_beats_retrieval_failure() -> None:
    telemetry = _shadow_eligibility_base(
        author_quant_source_telemetry={
            "author_quant_content_source": "raw_economist_block_detected",
            "author_received_raw_quant_packet": False,
            "author_received_economist_framework": True,
            "author_received_analyst_packet_marker": False,
        },
        quant_retrieval_sufficiency_telemetry={
            "quant_retrieval_target_detected": True,
            "quant_retrieval_sufficiency_valid": False,
            "quant_retrieval_sufficiency_blockers": ["missing_metric_coverage"],
            "quant_retrieval_sufficiency_gate_reason": "blocked_by_missing_metric",
            "quant_retrieval_sufficiency_shadow_mode": True,
        },
    )

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "author_framework_marker_detected" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "retrieval_sufficiency_failed" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_author_marker_leak"
    )


def test_shadow_skip_calibration_non_medium_complexity_is_blocked() -> None:
    telemetry = _shadow_eligibility_base(complexity="high")

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "non_medium_complexity" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == "blocked_by_complexity"


def test_shadow_skip_calibration_pre_analyst_gate_skipped_is_blocked() -> None:
    telemetry = _shadow_eligibility_base(pre_analyst_gate_skipped=True)

    assert telemetry["economist_skip_eligible_shadow"] is False
    assert "pre_analyst_gate_skipped" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_pre_analyst_gate"
    )


def test_shadow_skip_calibration_high_stakes_priority_beats_other_blockers() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry.update(
        {
            "high_stakes_quant_detected": True,
            "quantitative_packet_valid": False,
            "quantitative_packet_direct_use_eligible": False,
            "quantitative_packet_requires_analyst": True,
        }
    )

    telemetry = _shadow_eligibility_base(
        report_type="general_research",
        complexity="high",
        economist_safety_telemetry=safety_telemetry,
    )

    assert "high_stakes_requires_analyst" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "packet_invalid_or_missing" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == "blocked_by_high_stakes"


def test_shadow_skip_calibration_invalid_packet_priority_beats_missing_review() -> None:
    safety_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    safety_telemetry.update(
        {
            "quantitative_packet_valid": False,
            "quantitative_packet_direct_use_eligible": False,
            "quantitative_packet_requires_analyst": True,
        }
    )

    telemetry = _shadow_eligibility_base(
        economist_safety_telemetry=safety_telemetry,
        analyst_quant_packet_handoff_telemetry={
            "analyst_quant_packet_reviewed_by_model": False,
            "analyst_model_called": True,
        },
    )

    assert "packet_invalid_or_missing" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "packet_not_reviewed_by_analyst" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_invalid_packet"
    )


def test_shadow_skip_calibration_missing_review_priority_beats_marker_leak() -> None:
    telemetry = _shadow_eligibility_base(
        analyst_quant_packet_handoff_telemetry={
            "analyst_quant_packet_reviewed_by_model": False,
            "analyst_model_called": True,
        },
        author_quant_source_telemetry={
            "author_quant_content_source": "raw_quant_packet_detected",
            "author_received_raw_quant_packet": True,
            "author_received_economist_framework": False,
            "author_received_analyst_packet_marker": False,
        },
    )

    assert "packet_not_reviewed_by_analyst" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "author_raw_packet_marker_detected" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_missing_analyst_review"
    )


def test_shadow_skip_calibration_marker_leak_priority_beats_report_type() -> None:
    telemetry = _shadow_eligibility_base(
        report_type="general_research",
        author_quant_source_telemetry={
            "author_quant_content_source": "raw_quant_packet_detected",
            "author_received_raw_quant_packet": True,
            "author_received_economist_framework": False,
            "author_received_analyst_packet_marker": False,
        },
    )

    assert "author_raw_packet_marker_detected" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert "non_bounded_quantitative_report" in telemetry[
        "economist_skip_eligibility_blockers"
    ]
    assert telemetry["economist_skip_eligibility_gate_reason"] == (
        "blocked_by_author_marker_leak"
    )


def test_quantitative_framework_prompt_language_is_not_direct_first_class_use() -> None:
    analyst_prompt = DEFAULT_SYSTEM["analyst"]
    assert "QUANTITATIVE FRAMEWORK block" in analyst_prompt
    assert "first-class evidence" not in analyst_prompt
    assert "treat it as unreviewed legacy material" in analyst_prompt
    assert "Analyst-authored synthesis" in analyst_prompt
    assert "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY" in analyst_prompt

    estimate_prompt = DEFAULT_SYSTEM["analyst_estimate_from_priors"]
    assert "QUANTITATIVE FRAMEWORK / economist JSON block" in estimate_prompt
    assert "treat it as unreviewed legacy material" in estimate_prompt
    assert "do not restate them as conclusions" in estimate_prompt

    author_estimate_prompt = DEFAULT_SYSTEM["author_estimate_from_priors"]
    assert "economist framework" in author_estimate_prompt
    assert "not Author-ready evidence" in author_estimate_prompt
    assert "using MODEL-DERIVED figures from the Analyst synthesis or economist framework" not in (
        author_estimate_prompt
    )


def test_thin_quant_prompt_marks_legacy_framework_unreviewed() -> None:
    thin_prompt = DEFAULT_SYSTEM["analyst_thin_quant"]
    assert "unreviewed computed framework from an economist agent" in thin_prompt
    assert "DO NOT treat the framework as Author-ready evidence" in thin_prompt
    assert "first-class" not in thin_prompt
    assert "unreviewed legacy material" in thin_prompt


def test_analyst_quantitative_packet_section_truncates_overlong_fields() -> None:
    long_value = "x" * 260
    packet_telemetry = copy.deepcopy(_valid_revenue_packet_telemetry())
    packet_telemetry["quantitative_packet"]["source_bound_values"] = [
        {
            "name": f"metric_{idx}_{long_value}",
            "value": f"value_{idx}_{long_value}",
            "unit": f"unit_{idx}_{long_value}",
            "source_id": f"source_{idx}_{long_value}",
        }
        for idx in range(15)
    ]
    packet_telemetry["quantitative_packet"]["calculation_results"] = [
        {"name": f"calc_{idx}", "result": idx, "input_refs": {"old": "a", "new": "b"}}
        for idx in range(10)
    ]

    section, handoff = _format_analyst_quant_packet_section(packet_telemetry)

    assert handoff["analyst_quant_packet_injected"] is True
    assert "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY" in section
    assert long_value not in section
    assert "metric_0_" in section
    assert "..." in section
    assert "source_11_" in section
    assert "source_12_" not in section
    assert "calc_7" in section
    assert "calc_8" not in section
    assert '"query"' not in section
    assert len(section) < 13000


def test_clinical_randomized_trial_comparative_effect_query_does_not_skip_analyst() -> None:
    out = _post_economist_analyst_gate(
        query=(
            "In randomized clinical trials, how does berberine compare with metformin "
            "for treatment effect on A1C?"
        ),
        report_type="quantitative_comparison",
        complexity="medium",
        economist_ran=True,
        economist_block=ECONOMIST_BLOCK,
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        failure_card_show=False,
        pre_analyst_gate_skipped=False,
    )

    assert out["analyst_skipped_after_economist"] is False
    assert (
        out["analyst_after_economist_skip_reason"]
        == "clinical_randomized_trial_comparative_effect_guardrail"
    )
    assert out["economist_output_used_as_analysis"] is False
