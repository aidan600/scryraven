from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.context_measurement import (
    ContextMeasurementCollector,
    estimate_context_tokens,
    repeated_value_count,
    stable_context_hash,
)
from core.corpus_state import CorpusState
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from tests.test_balanced_anchor_resolution_shadow import _run_anchor_pipeline
from tests.test_pre_analyst_gate import (
    _execution_event_from_log,
    _run_post_economist_harness,
)


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            out.append(str(key))
            out.extend(_flatten_strings(item))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_flatten_strings(item))
        return out
    if isinstance(value, str):
        return [value]
    return []


def _context_text(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True)


def test_context_measurement_helper_is_deterministic_and_hash_only() -> None:
    raw = "Sensitive prompt evidence text"

    assert estimate_context_tokens(None) == 0
    assert estimate_context_tokens("") == 0
    assert estimate_context_tokens("abcd") == 1
    assert estimate_context_tokens("abcde") == 2
    assert estimate_context_tokens(raw) == estimate_context_tokens(raw)

    digest = stable_context_hash(raw)
    assert digest == stable_context_hash(raw)
    assert re.fullmatch(r"[0-9a-f]{16}", digest)
    assert raw not in digest

    assert repeated_value_count(["1", "2", "2", "3"], ["2", "4"]) == 1


def test_context_measurement_collector_counts_repeated_sources_and_hashes() -> None:
    collector = ContextMeasurementCollector()
    collector.add_stage(
        "analyst",
        prompt="first prompt",
        evidence_texts=["alpha evidence", "beta evidence"],
        source_ids=["1", "2"],
    )
    collector.add_stage(
        "author",
        prompt="second prompt",
        evidence_texts=["beta evidence", "gamma evidence"],
        source_ids=["2", "3"],
    )

    payload = collector.payload()
    assert payload["available"] is True
    assert payload["stage_count"] == 2
    assert payload["stages"]["author"]["repeated_source_id_count"] == 1
    assert payload["stages"]["author"]["repeated_evidence_hash_count"] == 1
    assert payload["aggregate"]["repeated_source_id_count_total"] == 1
    assert payload["aggregate"]["repeated_evidence_hash_count_total"] == 1
    assert payload["aggregate"]["raw_prompt_logged"] is False
    assert payload["aggregate"]["raw_evidence_logged"] is False
    assert "alpha evidence" not in _context_text(payload)
    assert "beta evidence" not in _context_text(payload)


def test_balanced_pipeline_context_measurement_is_nested_hash_only(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    evidence_rows = [
        {
            "title": f"Quarter source {idx}",
            "url": f"https://ir.example/q{idx}",
            "text": (
                f"Tesla quarter {idx} automotive gross margin was {margin}."
                if idx <= 2
                else f"Quarter {idx} automotive gross margin was {margin}."
            ),
            "source_tier": "official",
            "credibility": 3,
        }
        for idx, margin in enumerate(("18.5%", "18.9%", "19.3%", "20.1%"), 1)
    ]
    (tmp_path / "policy.json").write_text(
        json.dumps(
            {
                "thresholds": {
                    "utilization_threshold": 0.0,
                    "synth_skip_utilization_threshold": 1.0,
                }
            }
        ),
        encoding="utf-8",
    )
    outcome, harness = _run_post_economist_harness(
        tmp_path,
        monkeypatch,
        report_type="quantitative_comparison",
        economist_output="",
        healthy=True,
        forced_corpus_state=CorpusState.HEALTHY.value,
        evidence_rows=evidence_rows,
        preflight_allows=True,
    )
    row = _execution_event_from_log(tmp_path / "execution.jsonl")

    measurement = outcome.execution_trace["context_measurement"]
    assert row["execution_trace"]["context_measurement"] == measurement
    assert "context_measurement" not in row
    assert measurement["available"] is True
    assert measurement["stage_count"] == len(measurement["stages"])

    expected_stages = {
        "router",
        "researcher",
        "evaluator",
        "economist_preflight",
        "analyst",
        "synth_evaluator",
        "author",
    }
    assert expected_stages <= set(measurement["stages"])
    for stage_name in expected_stages:
        stage = measurement["stages"][stage_name]
        assert stage["prompt_token_estimate"] > 0, stage_name
        assert re.fullmatch(r"[0-9a-f]{16}", stage["prompt_hash"]), stage_name
    assert measurement["stages"]["economist_preflight"]["evidence_token_estimate"] > 0
    assert measurement["stages"]["analyst"]["evidence_token_estimate"] > 0
    assert measurement["stages"]["author"]["evidence_token_estimate"] > 0
    assert measurement["stages"]["author"]["repeated_source_id_count"] > 0
    assert measurement["aggregate"]["prompt_token_estimate_total"] > 0
    assert measurement["aggregate"]["evidence_token_estimate_total"] > 0
    assert measurement["aggregate"]["repeated_source_id_count_total"] > 0
    assert measurement["aggregate"]["raw_prompt_logged"] is False
    assert measurement["aggregate"]["raw_evidence_logged"] is False

    measurement_text = _context_text(measurement)
    forbidden_fragments = [
        "Today is 2026-05-06",
        "Tesla automotive gross margin",
        "Quarter 1 automotive gross margin",
        "quantitative_packet",
        "ECONOMIST FRAMEWORK",
        "economist_v1",
        "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in measurement_text
    for text_value in _flatten_strings(measurement):
        assert "prompt" not in text_value.lower() or text_value in {
            "prompt_token_estimate",
            "prompt_hash",
            "prompt_token_estimate_total",
            "raw_prompt_logged",
        }

    assert harness.economist_calls == 1
    assert harness.analyst_calls == 1
    assert harness.author_prompts
    assert outcome.execution_trace["analyst_skipped"] is False
    assert outcome.execution_trace["weak_corpus_recovery_used"] is False


def test_context_measurement_preserves_balanced_provider_search_and_call_contracts(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_anchor_pipeline(tmp_path)
    trace = outcome.execution_trace

    assert "context_measurement" in trace
    assert trace["context_measurement"]["available"] is True
    assert len(harness.search_calls) == 1
    assert harness.search_calls[0]["search_depth"] == "basic"
    assert harness.search_calls[0]["complexity"] == "medium"
    assert harness.search_calls[0]["queries"] == trace["queries_per_iteration"]["1"]
    assert "tavily" in harness.search_calls[0]["search_providers"]
    assert harness.analyst_calls == 1
    assert harness.economist_calls == 0
    assert harness.author_prompts
    assert trace["analyst_skipped"] is False
    assert trace["weak_corpus_recovery_used"] is False


def test_context_measurement_is_diagnostic_only_for_fast_and_deep(
    tmp_path: Path,
) -> None:
    fast_outcome, fast_harness = _run_anchor_pipeline(tmp_path / "fast", mode="Fast")
    deep_outcome, deep_harness = _run_anchor_pipeline(tmp_path / "deep", mode="Deep")

    fast_trace = fast_outcome.execution_trace
    deep_trace = deep_outcome.execution_trace
    assert fast_trace["context_measurement"]["available"] is True
    assert deep_trace["context_measurement"]["available"] is True
    assert len(fast_harness.search_calls) == 1
    assert fast_harness.search_calls[0]["search_depth"] == "basic"
    assert fast_harness.analyst_calls == 0
    assert fast_harness.economist_calls == 0
    assert fast_trace["mode"] == "Fast"
    assert fast_trace["complexity"] == "low"

    assert len(deep_harness.search_calls) == 1
    assert deep_harness.search_calls[0]["search_depth"] == "advanced"
    assert deep_harness.analyst_calls == 1
    assert deep_harness.economist_calls == 0
    assert deep_trace["mode"] == "Deep"
    assert deep_trace["complexity"] == "high"


def test_context_measurement_sqlite_mapping_and_top_level_jsonl_stay_compact(
    tmp_path: Path,
) -> None:
    _outcome, _harness = _run_anchor_pipeline(tmp_path)
    row = _execution_event_from_log(tmp_path / "execution.jsonl")

    assert "context_measurement" in row["execution_trace"]
    assert "context_measurement" not in row
    forbidden_top_level = {
        "prompt",
        "raw_prompt",
        "system_prompt",
        "user_prompt",
        "evidence_block",
        "raw_evidence",
    }
    assert not (forbidden_top_level & set(row))

    sqlite_row = execution_jsonl_to_run_row(row)
    assert sqlite_row is not None
    assert set(sqlite_row) == set(RUN_COLUMNS)
    assert "execution_trace" not in sqlite_row
    assert "context_measurement" not in sqlite_row
