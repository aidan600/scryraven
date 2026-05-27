from __future__ import annotations

from pathlib import Path
from typing import Any

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from core.quantitative_consistency import (
    apply_quantitative_consistency_guard,
    build_two_item_normalized_consistency_diagnostic,
    is_two_item_calorie_gram_comparison_candidate,
)
from core.run_config import RunConfig
from tests.test_source_class_recovery_trace import (
    _execution_event_from_log,
    _TraceHarness,
)

QUERY = (
    "A protein bar has 220 calories / 60g and another has "
    "170 calories / 45g. Which is more calorie-dense?"
)
WRONG_ANSWER = (
    "The 220 calorie / 60g bar is more calorie-dense. "
    "The normalized values are 3.67 and 3.78 calories per gram."
)
CORRECT_ANSWER = (
    "The 170 calorie / 45g bar is more calorie-dense. "
    "It is about 3.78 calories per gram versus about 3.67."
)
INTERNAL_MARKERS = (
    "quantitative_packet",
    "source_bound_values",
    "calculation_results",
    "economist_v1",
    "ECONOMIST FRAMEWORK",
    "provider_diagnostics",
)


def _guard(query: str, answer: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    diagnostic = build_two_item_normalized_consistency_diagnostic(
        query=query,
        final_answer=answer,
    )
    output, telemetry = apply_quantitative_consistency_guard(
        query=query,
        final_answer=answer,
        diagnostic=diagnostic,
    )
    return output, telemetry, diagnostic


def test_ag18_stream_buffer_candidate_predicate_is_narrow() -> None:
    assert is_two_item_calorie_gram_comparison_candidate(QUERY) is True
    assert (
        is_two_item_calorie_gram_comparison_candidate(
            "Compare 220 calories / 60g, 170 calories / 45g, "
            "and 90 calories / 20g for calorie density."
        )
        is False
    )
    assert (
        is_two_item_calorie_gram_comparison_candidate(
            "A plan costs 10 dollars / 2 users and another costs 15 dollars / 5 users."
        )
        is False
    )


def test_ag18_wrong_two_item_calorie_density_prose_is_replaced() -> None:
    output, telemetry, diagnostic = _guard(QUERY, WRONG_ANSWER)

    assert diagnostic["quantitative_consistency_status"] == "contradiction_detected"
    assert diagnostic["quantitative_consistency_computed_winner"] == "item_b"
    assert diagnostic["quantitative_consistency_stated_winner"] == "item_a"
    assert output != WRONG_ANSWER
    assert "170 calories / 45 g item is more calorie-dense" in output
    assert "220 calories / 60 g = 3.667 cal/g = 366.7 cal/100g" in output
    assert "170 calories / 45 g = 3.778 cal/g = 377.8 cal/100g" in output
    assert "0.111 cal/g" in output
    assert "11.1 cal/100g" in output
    assert "figures you provided" in output
    assert telemetry["quantitative_consistency_guard_applied"] is True
    assert (
        telemetry["quantitative_consistency_guard_reason"]
        == "deterministic_normalized_winner_replacement"
    )
    assert telemetry["quantitative_consistency_guard_output_mode"] == (
        "deterministic_corrected_answer"
    )
    assert telemetry["quantitative_consistency_guard_final_answer_replaced"] is True


def test_ag18_corrected_answer_exposes_no_raw_quantitative_internals() -> None:
    output, telemetry, _diagnostic = _guard(QUERY, WRONG_ANSWER)

    assert telemetry["quantitative_consistency_guard_applied"] is True
    for marker in INTERNAL_MARKERS:
        assert marker not in output


def test_ag18_correct_two_item_calorie_density_prose_is_unchanged() -> None:
    output, telemetry, diagnostic = _guard(QUERY, CORRECT_ANSWER)

    assert diagnostic["quantitative_consistency_status"] == "consistent"
    assert output == CORRECT_ANSWER
    assert telemetry["quantitative_consistency_guard_applied"] is False
    assert telemetry["quantitative_consistency_guard_reason"] == "status_not_contradiction"
    assert telemetry["quantitative_consistency_guard_output_mode"] == "unchanged"
    assert telemetry["quantitative_consistency_guard_final_answer_replaced"] is False


def test_ag18_no_stated_winner_is_unchanged() -> None:
    answer = "The normalized values are 3.67 and 3.78 calories per gram."
    output, telemetry, diagnostic = _guard(QUERY, answer)

    assert diagnostic["quantitative_consistency_status"] == "not_applicable"
    assert diagnostic["quantitative_consistency_reason"] == "no_stated_winner_detected"
    assert output == answer
    assert telemetry["quantitative_consistency_guard_applied"] is False


def test_ag18_tied_normalized_values_are_unchanged() -> None:
    query = "A snack has 100 calories / 50g and another has 200 calories / 100g."
    answer = "The 100 calorie / 50g snack is denser."
    output, telemetry, diagnostic = _guard(query, answer)

    assert diagnostic["quantitative_consistency_status"] == "not_applicable"
    assert diagnostic["quantitative_consistency_reason"] == "normalized_values_tie"
    assert output == answer
    assert telemetry["quantitative_consistency_guard_applied"] is False


def test_ag18_non_calorie_query_is_unchanged() -> None:
    query = "A plan costs 10 dollars / 2 users and another costs 15 dollars / 5 users."
    answer = "The 10 dollar / 2 user plan is more expensive per user."
    output, telemetry, diagnostic = _guard(query, answer)

    assert diagnostic["quantitative_consistency_status"] == "not_applicable"
    assert output == answer
    assert telemetry["quantitative_consistency_guard_applied"] is False


def test_ag18_three_item_comparison_is_unchanged() -> None:
    query = (
        "Compare 220 calories / 60g, 170 calories / 45g, "
        "and 90 calories / 20g for calorie density."
    )
    answer = "The 220 calorie / 60g item is more calorie-dense."
    output, telemetry, diagnostic = _guard(query, answer)

    assert diagnostic["quantitative_consistency_status"] == "not_applicable"
    assert output == answer
    assert telemetry["quantitative_consistency_guard_applied"] is False


class _QuantitativeAuthorHarness(_TraceHarness):
    def __init__(self, tmp_path: Path, *, author_answer: str) -> None:
        super().__init__(
            tmp_path,
            query=QUERY,
            core_topic="protein bar calorie density comparison",
            primary_entity="protein bar",
            researcher_query="protein bar calorie density",
            router_report_type="quantitative_comparison",
            router_query_type="comparison",
            source_tiers=["secondary", "secondary"],
            domains=["nutrition.example"],
        )
        self.author_answer = author_answer

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if kwargs.get("stream"):
            self.author_calls += 1
            self.author_prompts.append(prompt)
            return self.author_answer
        return super().ask_model(prompt, system_prompt, **kwargs)


class _StreamingAuthorHarness(_TraceHarness):
    def __init__(
        self,
        tmp_path: Path,
        *,
        query: str,
        author_chunks: list[str],
        core_topic: str,
        primary_entity: str,
        router_report_type: str,
        router_query_type: str,
    ) -> None:
        super().__init__(
            tmp_path,
            query=query,
            core_topic=core_topic,
            primary_entity=primary_entity,
            researcher_query=core_topic,
            router_report_type=router_report_type,
            router_query_type=router_query_type,
            source_tiers=["secondary", "secondary"],
            domains=["nutrition.example"],
        )
        self.author_chunks = list(author_chunks)

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> Any:
        if kwargs.get("stream"):
            self.author_calls += 1
            self.author_prompts.append(prompt)
            return iter(self.author_chunks)
        return super().ask_model(prompt, system_prompt, **kwargs)


def _run_streaming_case(
    tmp_path: Path,
    *,
    query: str,
    author_chunks: list[str],
    core_topic: str = "protein bar calorie density comparison",
    primary_entity: str = "protein bar",
    router_report_type: str = "quantitative_comparison",
    router_query_type: str = "comparison",
) -> tuple[Any, _StreamingAuthorHarness, dict[str, Any], list[str]]:
    displayed_chunks: list[str] = []
    harness = _StreamingAuthorHarness(
        tmp_path,
        query=query,
        author_chunks=author_chunks,
        core_topic=core_topic,
        primary_entity=primary_entity,
        router_report_type=router_report_type,
        router_query_type=router_query_type,
    )

    def display(chunks: Any) -> None:
        displayed_chunks.extend(list(chunks))

    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode="Balanced",
            current_date="2026-05-22",
            use_reasoning=False,
            author_stream_display=display,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")
    return outcome, harness, log_entry, displayed_chunks


def test_ag18_pipeline_replaces_contradictory_author_report_before_return_and_log(
    tmp_path: Path,
) -> None:
    harness = _QuantitativeAuthorHarness(tmp_path, author_answer=WRONG_ANSWER)

    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode="Balanced",
            current_date="2026-05-22",
            use_reasoning=False,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")

    assert harness.author_calls == 1
    assert outcome.report != WRONG_ANSWER
    assert outcome.new_session["report"] == outcome.report
    assert "170 calories / 45 g item is more calorie-dense" in outcome.report
    assert "377.8 cal/100g" in outcome.report
    assert log_entry["execution_trace"]["quantitative_consistency_status"] == (
        "contradiction_detected"
    )
    assert (
        log_entry["execution_trace"]["quantitative_consistency_guard_applied"] is True
    )
    assert log_entry["execution_trace"][
        "quantitative_consistency_guard_final_answer_replaced"
    ] is True
    assert "170 calories / 45 g item is more calorie-dense" in log_entry[
        "execution_trace"
    ]["final_output_preview"]
    for marker in INTERNAL_MARKERS:
        assert marker not in outcome.report
    assert harness.author_prompts
    assert "quantitative_packet" not in harness.author_prompts[-1]


def test_ag18_streamed_quantitative_candidate_buffers_raw_chunks_and_returns_guarded_report(
    tmp_path: Path,
) -> None:
    outcome, harness, log_entry, displayed_chunks = _run_streaming_case(
        tmp_path,
        query=QUERY,
        author_chunks=[
            "The 220 calorie / 60g bar is more calorie-dense. ",
            "The normalized values are 3.67 and 3.78 calories per gram.",
        ],
    )

    assert harness.author_calls == 1
    assert displayed_chunks == []
    assert outcome.author_streamed is False
    assert outcome.report != WRONG_ANSWER
    assert outcome.new_session["report"] == outcome.report
    assert "170 calories / 45 g item is more calorie-dense" in outcome.report
    assert "377.8 cal/100g" in outcome.report
    assert log_entry["execution_trace"]["quantitative_consistency_guard_applied"] is True
    assert "170 calories / 45 g item is more calorie-dense" in log_entry[
        "execution_trace"
    ]["final_output_preview"]


def test_ag18_streamed_correct_quantitative_candidate_buffers_and_remains_unchanged(
    tmp_path: Path,
) -> None:
    outcome, _harness, log_entry, displayed_chunks = _run_streaming_case(
        tmp_path,
        query=QUERY,
        author_chunks=[
            "The 170 calorie / 45g bar is more calorie-dense. ",
            "It is about 3.78 calories per gram versus about 3.67.",
        ],
    )

    assert displayed_chunks == []
    assert outcome.author_streamed is False
    assert outcome.report == CORRECT_ANSWER
    assert outcome.new_session["report"] == CORRECT_ANSWER
    assert log_entry["execution_trace"]["quantitative_consistency_status"] == "consistent"
    assert (
        log_entry["execution_trace"]["quantitative_consistency_guard_applied"] is False
    )


def test_ag18_non_quantitative_streaming_behavior_is_unchanged(
    tmp_path: Path,
) -> None:
    chunks = ["Plain ", "streamed ", "answer."]
    outcome, harness, log_entry, displayed_chunks = _run_streaming_case(
        tmp_path,
        query="What is the care program?",
        author_chunks=chunks,
        core_topic="care program overview",
        primary_entity="Care Program",
        router_report_type="general_research",
        router_query_type="other",
    )

    assert harness.author_calls == 1
    assert displayed_chunks == chunks
    assert outcome.author_streamed is True
    assert outcome.report == "Plain streamed answer."
    assert outcome.new_session["report"] == "Plain streamed answer."
    assert (
        log_entry["execution_trace"]["quantitative_consistency_guard_applied"] is False
    )
