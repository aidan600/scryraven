from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import scripts.ag96i3af6a_brokered_author_lane_smoke as af6a

JOB_LABEL = "ag96i3af6d-live-author-smoke"


def test_broker_live_without_adapter_path_fails_closed_and_writes_sanitized_json(
    tmp_path: Path, monkeypatch: Any
) -> None:
    packet, rc = _run(tmp_path, monkeypatch)
    assert rc == 2
    assert (
        packet["ok"],
        packet["status"],
        packet["author_model_call_mode"],
        packet["model_calls_used"],
        packet["live_model_call_performed"],
    ) == (False, "deferred", "broker_live_deferred", 0, False)
    assert packet["job_id"] == JOB_LABEL
    _assert_sanitized(packet)


def test_broker_live_with_external_adapter_completes_author_chain_and_writes_sanitized_json(
    tmp_path: Path, monkeypatch: Any
) -> None:
    adapter = tmp_path / "author_adapter.py"
    adapter.write_text(
        "import json, sys\njson.load(sys.stdin)\n"
        "json.dump({'candidate_text': 'External adapter bounded Author answer.'}, sys.stdout)\n",
        encoding="utf-8",
    )
    packet, rc = _run(tmp_path, monkeypatch, adapter=adapter)
    assert rc == 0
    assert packet["ok"] is True
    assert packet["status"] == "completed"
    assert packet["mode"] == "live_adapter"
    assert packet["job_id"] == JOB_LABEL
    assert packet["chain"] == ["AF4B2", "AF4C", "AF4D", "AF5A", "AF5B"]
    assert all(
        packet[field]
        for field in "final_answer_outcome_id final_answer_outcome_digest packet_id author_response_candidate_digest".split()
    )
    assert (
        packet["author_model_call_mode"],
        packet["author_model_call_status"],
        packet["author_model_call_source"],
        packet["model_calls_used"],
        packet["mock_model_adapter_calls_used"],
        packet["live_model_call_performed"],
        packet["live_adapter_mocked"],
        packet["fake_adapter_used"],
    ) == ("live_adapter", "completed_live_adapter", "external_live_model_adapter", 1, 0, True, False, False)
    _assert_sanitized(packet)


def _run(tmp_path: Path, monkeypatch: Any, *, adapter: Path | None = None) -> tuple[dict[str, Any], int]:
    monkeypatch.setattr(af6a, "ROOT", tmp_path)
    output = tmp_path / "output" / "packet.json"
    argv = [
        "--job-id",
        JOB_LABEL,
        "--broker-live-mode",
        "--confirm-live-provider-call",
        "--output",
        "output/packet.json",
    ]
    if adapter is not None:
        argv.extend(["--author-live-adapter-py", str(adapter)])
    rc = af6a.main(argv)
    return json.loads(output.read_text(encoding="utf-8")), rc


def _assert_sanitized(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in af6a.FORBIDDEN_PACKET_KEYS
            if key.endswith("_retained") or key == "secrets_returned":
                assert child is False
            _assert_sanitized(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_sanitized(child)
