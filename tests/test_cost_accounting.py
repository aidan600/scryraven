from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.cost_accounting import CostAccumulator, estimate_tokens, extract_usage_tokens


class _Usage:
    prompt_tokens = 100
    completion_tokens = 25


class _Response:
    usage = _Usage()


def test_cost_accumulator_rolls_up_model_tokens_and_cost() -> None:
    acc = CostAccumulator()
    acc.record_model_call(
        phase="router",
        model="gpt-5.4-mini",
        input_tokens=1_000_000,
        output_tokens=500_000,
    )

    snap = acc.snapshot()
    assert snap["total_input_tokens"] == 1_000_000
    assert snap["total_output_tokens"] == 500_000
    assert snap["total_calls"] == 1
    assert snap["cost_by_phase"]["router"] == 1.25
    assert snap["cost_by_model"]["gpt-5.4-mini"] == 1.25
    assert snap["calls_by_phase"] == {"router": 1}
    assert snap["total_cost_usd"] == 1.25


def test_unknown_models_are_counted_without_invented_cost() -> None:
    acc = CostAccumulator()
    acc.record_model_call(
        phase="local",
        model="local-model",
        input_tokens=100,
        output_tokens=50,
    )

    snap = acc.snapshot()
    assert snap["total_calls"] == 1
    assert snap["calls_by_phase"] == {"local": 1}
    assert snap["total_input_tokens"] == 100
    assert snap["total_output_tokens"] == 50
    assert snap["total_cost_usd"] == 0.0


def test_extract_usage_tokens_supports_sdk_usage_objects() -> None:
    assert extract_usage_tokens(_Response()) == (100, 25)


def test_estimate_tokens_is_deterministic_for_batches() -> None:
    assert estimate_tokens(["abcd", "abcdefgh"]) == 3


def test_aggregate_run_quality_reads_old_and_new_cost_records(tmp_path: Path, capsys) -> None:
    from scripts import aggregate_run_quality

    log_path = tmp_path / "execution_log.jsonl"
    old_record = {"event": "execution", "query_type": "other", "timing": {}}
    new_record = {
        "event": "execution",
        "query_type": "product",
        "timing": {},
        "cost": {
            "total_cost_usd": 0.1234,
            "total_input_tokens": 1000,
            "total_output_tokens": 200,
            "total_calls": 4,
        },
    }
    log_path.write_text(
        "\n".join(json.dumps(x) for x in (old_record, new_record)),
        encoding="utf-8",
    )

    aggregate_run_quality.LOG = log_path
    aggregate_run_quality.KB_TRIGGERS = tmp_path / "missing_kb.jsonl"
    aggregate_run_quality.main()

    out = capsys.readouterr().out
    assert "Cost" in out
    assert "cost available on 1" in out
    assert "total_cost_usd" in out
