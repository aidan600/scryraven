"""Calculator receipts stay forensic; ordinary diagnostics retain safe counts only."""

import json

from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.forensic_log import ForensicLog


def test_calculator_projection_counts_calls_without_expression_or_result():
    diagnostics = TurnDiagnostics(started_at=1.0, clock=lambda: 3.0)
    sensitive = {
        "stage": "research", "action": "calculator_result", "contract": "answer",
        "attempt": 2, "sequence": 1, "expression": "PRIVATE_EXPRESSION_12 + 4",
        "result": {"value": "PRIVATE_RESULT_16"},
    }
    diagnostics.observe(sensitive)
    diagnostics.observe({
        "stage": "research", "action": "calculator_used", "contract": "answer",
        "attempt": 2, "sequence": 1, "success": True, "duration_seconds": 0.25,
        "expression": sensitive["expression"], "result": sensitive["result"],
    })
    diagnostics.observe({
        "stage": "research", "action": "calculator_used", "contract": "answer",
        "attempt": 2, "sequence": 2, "success": False, "duration_seconds": 0.5,
        "error": "PRIVATE_ERROR_DETAIL",
    })
    diagnostics.observe({
        "stage": "research", "action": "calculator_used", "contract": "research",
        "success": False, "duration_seconds": 1.0,
    })
    diagnostics.observe({
        "stage": "research", "action": "calculator_used", "contract": "answer",
        "success": "PRIVATE_INVALID_STATUS", "duration_seconds": 1.0,
    })

    record = diagnostics.record(session_id="a" * 32, revision_before=0, revision_after=1)

    assert record["calculator"] == {"calls": 2, "failures": 1, "duration_seconds": 0.75}
    assert "PRIVATE_" not in json.dumps(record)
    assert "expression" not in json.dumps(record)
    assert "result" not in json.dumps(record)


def test_explicit_forensic_log_preserves_ordered_calculator_receipts(tmp_path):
    path = tmp_path / "observer.jsonl"
    log = ForensicLog(path)
    first = {
        "stage": "research", "action": "calculator_result", "contract": "answer",
        "attempt": 2, "sequence": 1, "expression": "PRIVATE_EXPRESSION_12 + 4",
        "result": {"value": "16"},
    }
    second = {
        "stage": "research", "action": "calculator_result", "contract": "answer",
        "attempt": 2, "sequence": 2, "expression": "16 / 0",
        "result": {"error": "division_by_zero"},
    }
    log.append(first, session_id="a" * 32, revision_before=0)
    log.append(second, session_id="a" * 32, revision_before=0)

    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [record["event_sequence"] for record in records] == [1, 2]
    assert [record["event"] for record in records] == [first, second]
    assert all(record["attempted_turn"] == 1 for record in records)
