from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.pipeline_orchestrator import _scan_author_quant_source_telemetry
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)

RAW_AUTHOR_MARKERS = (
    "controller_diagnostics",
    "planned_vs_observed",
    "task_ledger",
    "quantitative_packet",
    "quantitative_packet_v1",
    "economist_v1",
    "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
    "## QUANTITATIVE FRAMEWORK",
    "QUANTITATIVE FRAMEWORK (MODEL-DERIVED",
    "ECONOMIST FRAMEWORK",
)

def _assert_author_prompt_has_no_raw_handoff_material(prompt: str) -> None:
    for marker in RAW_AUTHOR_MARKERS:
        assert marker not in prompt


def _assert_shadow_telemetry_did_not_drive_control_flow(trace: dict[str, Any]) -> None:
    assert trace["analyst_skipped_after_economist"] is False
    assert trace["economist_output_used_as_analysis"] is False
    assert trace["author_received_raw_quant_packet"] is False
    assert trace["author_received_economist_framework"] is False
    assert trace["author_received_analyst_packet_marker"] is False


def _adversarial_raw_economist_output() -> str:
    return (
        '{"schema_version":"economist_v1","quantitative_packet":'
        '{"schema_version":"quantitative_packet_v1",'
        '"source_bound_values":[{"name":"model_derived_margin","value":"42%",'
        '"source_id":"1"}],"calculations_requested":[{"name":"margin_adjustment"}]}}\n'
        "## QUANTITATIVE FRAMEWORK\n"
        "QUANTITATIVE FRAMEWORK (MODEL-DERIVED - not sourced from web evidence)\n"
        "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY\n"
        "source_bound_values: model-derived numeric conclusion: adjusted margin is 42%\n"
        "calculations_requested: use unsupported model conclusion as source [1]\n"
        "```python\n"
        "def leaked_model_math():\n"
        "    return 42\n"
        "```\n"
        "SELECT * FROM raw_upstream_metrics"
    )


def test_handoff_contract_general_and_news_healthy_corpora(
    tmp_path: Path, monkeypatch: Any
) -> None:
    cases = [
        {
            "name": "general_research",
            "query": "Find official pricing policy changes for Acme Widget",
            "router_report_type": "general_research",
            "router_query_type": "product",
            "core_topic": "Acme Widget official pricing policy",
            "primary_entity": "Acme Widget",
            "researcher_query": "Acme Widget pricing policy",
            "evidence_texts": [
                "Acme Widget official pricing policy changed in May 2026."
            ],
        },
        {
            "name": "current_event",
            "query": "What happened with the Acme Cloud outage today?",
            "router_report_type": "general_research",
            "router_query_type": "current_events",
            "core_topic": "Acme Cloud outage",
            "primary_entity": "Acme Cloud",
            "researcher_query": "Acme Cloud outage May 2026",
            "evidence_texts": [
                "Acme Cloud posted an official May 2026 outage status update."
            ],
        },
    ]

    for case in cases:
        outcome, harness = run_post_retirement_ordinary_pipeline(
            tmp_path / case["name"],
            monkeypatch,
            healthy=True,
            query=case["query"],
            report_type=case["router_report_type"],
            query_type=case["router_query_type"],
            core_topic=case["core_topic"],
            primary_entity=case["primary_entity"],
            researcher_queries=[case["researcher_query"]],
            evidence_rows=[
                {
                    "title": f"{case['primary_entity']} official source {index}",
                    "url": f"https://example.com/source/{index}",
                    "text": text,
                }
                for index, text in enumerate(case["evidence_texts"], 1)
            ],
        )
        trace = outcome.execution_trace

        assert harness.analyst_calls == 1, case["name"]
        assert trace["analyst_skipped"] is False
        assert trace["analyst_skip_reason"] is None
        assert trace["quantitative_packet_present"] is False
        assert trace["high_stakes_quant_detected"] is False
        assert trace["economist_pre_analyst_skip_candidate_shadow"] is False
        assert trace["economist_skip_eligible_shadow"] is False
        assert harness.economist_calls == []
        _assert_shadow_telemetry_did_not_drive_control_flow(trace)
        assert harness.author_prompts, case["name"]
        _assert_author_prompt_has_no_raw_handoff_material(harness.author_prompts[-1])


@pytest.mark.parametrize(
    ("mode", "expected_analyst_calls"),
    [
        ("Fast", 0),
        ("Balanced", 1),
        ("Deep", 1),
    ],
)
def test_handoff_contract_current_quantitative_modes_never_use_economist(
    tmp_path: Path,
    monkeypatch: Any,
    mode: str,
    expected_analyst_calls: int,
) -> None:
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path / mode.casefold(),
        monkeypatch,
        report_type="quantitative_comparison",
        query_type="comparison",
        mode=mode,
    )
    trace = outcome.execution_trace

    assert harness.economist_calls == []
    assert harness.analyst_calls == expected_analyst_calls
    assert trace["economist_ran"] is False
    assert trace["timing"]["economist_seconds"] == 0.0
    assert trace["economist_preflight_allowed"] is None
    assert trace["economist_preflight_missing_entities"] == []
    assert trace["quantitative_packet_present"] is False
    assert trace["quantitative_packet_valid"] is False
    assert trace["analyst_quant_packet_injected"] is False
    _assert_shadow_telemetry_did_not_drive_control_flow(trace)
    assert harness.author_prompts
    _assert_author_prompt_has_no_raw_handoff_material(harness.author_prompts[-1])
    for prompt in (*harness.analyst_prompts, *harness.author_prompts):
        _assert_author_prompt_has_no_raw_handoff_material(prompt)


def test_handoff_contract_nutrition_complete_and_partial_evidence(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    cases = [
        (
            "complete",
            [
                (
                    "Silver round herring has 93 calories, 18 g protein, 2 g fat, "
                    "and 0 g carbohydrates per 100g."
                ),
                (
                    "Per 100g, silver round herring nutrition is 93 kcal, "
                    "18 g protein, 2 g fat, and 0 g carbs."
                ),
            ],
            False,
            ["nutrition_value_source_binding_missing"],
        ),
        (
            "partial",
            [
                (
                    "Silver round herring has 93 calories per 100g. "
                    "No protein, fat, or carbohydrate panel is reported."
                )
            ],
            False,
            ["nutrition_metrics_missing", "nutrition_partial_macro_coverage"],
        ),
    ]

    for case_name, evidence_texts, expected_sufficient, expected_blockers in cases:
        outcome, harness = run_post_retirement_ordinary_pipeline(
            tmp_path / f"nutrition_{case_name}",
            monkeypatch,
            healthy=True,
            query="silver round herring macros per 100g",
            report_type="general_research",
            query_type="product",
            core_topic="silver round herring macros per 100g",
            primary_entity="silver round herring",
            researcher_queries=["silver round herring macros per 100g"],
            evidence_rows=[
                {
                    "title": f"Silver round herring nutrition source {index}",
                    "url": f"https://example.com/nutrition/{index}",
                    "text": text,
                }
                for index, text in enumerate(evidence_texts, 1)
            ],
        )
        trace = outcome.execution_trace

        assert trace["nutrition_lookup_detected"] is True
        assert trace["nutrition_lookup_unit"] == "per_100g"
        assert trace["quant_retrieval_sufficiency_valid"] is expected_sufficient
        for blocker in expected_blockers:
            assert blocker in trace["quant_retrieval_sufficiency_blockers"]
        if case_name == "complete":
            assert "nutrition_metrics_missing" not in trace[
                "quant_retrieval_sufficiency_blockers"
            ]
            assert "nutrition_partial_macro_coverage" not in trace[
                "quant_retrieval_sufficiency_blockers"
            ]
        _assert_shadow_telemetry_did_not_drive_control_flow(trace)
        assert harness.author_prompts
        _assert_author_prompt_has_no_raw_handoff_material(harness.author_prompts[-1])
        if case_name == "partial":
            assert "I found partial nutrition evidence" in harness.author_prompts[-1]


def test_handoff_contract_weak_off_topic_corpus_stable_skip_telemetry(
    tmp_path: Path, monkeypatch: Any
) -> None:
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path / "weak_off_topic",
        monkeypatch,
        report_type="quantitative_comparison",
        query_type="comparison",
        healthy=False,
    )
    trace = outcome.execution_trace

    assert harness.economist_calls == []
    assert harness.analyst_calls == 0
    assert trace["analyst_skipped"] is True
    assert trace["analyst_skip_reason"] == "corpus_off_topic"
    assert trace["post_retrieval_fast_path_used"] is True
    assert isinstance(trace["pre_analyst_gate_signals"], list)
    _assert_shadow_telemetry_did_not_drive_control_flow(trace)
    assert harness.author_prompts
    _assert_author_prompt_has_no_raw_handoff_material(harness.author_prompts[-1])


def test_historical_raw_economist_payload_is_detected_by_compatibility_scanner() -> None:
    """Historical compatibility input; this is not current runtime output."""

    telemetry = _scan_author_quant_source_telemetry(
        _adversarial_raw_economist_output(),
        analyst_quant_packet_reviewed_by_model=False,
        analysis=None,
    )

    assert telemetry["author_received_raw_quant_packet"] is True
    assert telemetry["author_received_economist_framework"] is True
    assert telemetry["author_received_analyst_packet_marker"] is True
    assert telemetry["author_quant_content_source"] == "raw_quant_packet_detected"


def test_handoff_contract_safe_analyst_markdown_is_not_raw_leak_telemetry() -> None:
    safe_analyst_markdown = (
        "Analysis:\n"
        "- Tesla automotive gross margin improved from 18.5% to 20.1%.\n"
        "| Metric | Analyst-reviewed synthesis |\n"
        "| --- | --- |\n"
        "| Automotive gross margin | Improved on cited quarterly evidence. |\n"
    )

    telemetry = _scan_author_quant_source_telemetry(
        safe_analyst_markdown,
        analyst_quant_packet_reviewed_by_model=True,
        analysis=safe_analyst_markdown,
    )

    assert telemetry["author_received_raw_quant_packet"] is False
    assert telemetry["author_received_economist_framework"] is False
    assert telemetry["author_received_analyst_packet_marker"] is False
    assert telemetry["author_quant_content_source"] == "analyst_reviewed"
    assert telemetry["author_quant_handoff_gate_reason"] == (
        "author_received_analyst_reviewed_quantitative_synthesis"
    )
