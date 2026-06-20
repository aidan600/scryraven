from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pytest

import scripts.ag96i3af6a_brokered_author_lane_smoke as af6a
from tests.ag96_static_guards import imported_modules

ROOT = Path(__file__).resolve().parents[1]
ANSWER_TEXT = "AF6A mocked broker-live Author-lane answer."


class MockBrokerLiveAdapter:
    def __init__(self, answer_text: str = ANSWER_TEXT) -> None:
        self.answer_text = answer_text
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        request_text: str,
        *,
        request_digest: str,
        request_length: int,
        request_metadata: Mapping[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "saw_request_text": bool(request_text),
                "request_digest": request_digest,
                "request_length": request_length,
                "request_metadata": dict(request_metadata),
            }
        )
        return {
            "final_answer_text": self.answer_text,
            "raw_model_response": "not retained",
            "provider_payload": {"not": "retained"},
        }


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"job_id": "wrong-job"}, "unknown AF6A job id"),
        ({"broker_live_mode": False}, "broker live mode"),
        ({"confirm_live_provider_call": False}, "confirmation"),
        ({"adapter": None}, "adapter factory"),
    ],
)
def test_af6a_absent_broker_live_guard_fails_closed(
    overrides: dict[str, Any],
    match: str,
) -> None:
    params = {
        "job_id": af6a.JOB_ID,
        "broker_live_mode": True,
        "confirm_live_provider_call": True,
        "adapter": MockBrokerLiveAdapter(),
    }
    params.update(overrides)
    with pytest.raises(af6a.AF6AFailClosed, match=match):
        af6a.run_af6a_smoke(**params)


def test_af6a_mocked_broker_live_path_calls_adapter_exactly_once() -> None:
    adapter = MockBrokerLiveAdapter()
    result = af6a.run_af6a_smoke(
        job_id=af6a.JOB_ID,
        broker_live_mode=True,
        confirm_live_provider_call=True,
        adapter=adapter,
    )
    packet = result.packet

    assert len(adapter.calls) == 1
    assert adapter.calls[0]["saw_request_text"] is True
    assert adapter.calls[0]["request_metadata"]["job_id"] == af6a.JOB_ID
    assert packet["mode"] == "broker_live"
    assert packet["budget"]["max_model_calls"] == 1
    assert packet["budget"]["model_calls_used"] == 1
    assert packet["final_answer_text"] == ANSWER_TEXT
    _assert_sanitized_shape(packet, expected_model_calls=1)


def test_af6a_fake_mode_has_sanitized_output_without_model_call_budget() -> None:
    result = af6a.run_af6a_smoke(
        job_id="fake-mode-job",
        broker_live_mode=False,
        confirm_live_provider_call=False,
        adapter=None,
        fake_mode=True,
        fake_answer="AF6A fake mode answer.",
    )
    packet = result.packet

    assert packet["mode"] == "fake"
    assert packet["budget"]["max_model_calls"] == 0
    assert packet["budget"]["model_calls_used"] == 0
    assert packet["final_answer_text"] == "AF6A fake mode answer."
    _assert_sanitized_shape(packet, expected_model_calls=0)


def test_af6a_rejects_output_outside_ignored_output_json() -> None:
    with pytest.raises(af6a.AF6AFailClosed, match="outside output"):
        af6a._output_path("docs/ag96i3af6a_packet.json")
    with pytest.raises(af6a.AF6AFailClosed, match="JSON"):
        af6a._output_path("output/ag96i3af6a_packet.txt")


def test_af6a_static_guards_no_search_fetch_retrieval_citation_or_pipeline() -> None:
    script_path = ROOT / "scripts" / "ag96i3af6a_brokered_author_lane_smoke.py"
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.llm",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "dotenv",
        "subprocess",
    }
    assert imported_modules(script_path).isdisjoint(forbidden_imports)
    source = script_path.read_text(encoding="utf-8")
    for token in (
        "pipeline_orchestrator",
        "ask_model(",
        "execute_author_action(",
        "search_web",
        "retrieve(",
        "retrieval_executed = True",
        "fetch(",
        "render_citation",
        "format_citation",
    ):
        assert token not in source


def _assert_sanitized_shape(
    packet: dict[str, Any],
    *,
    expected_model_calls: int,
) -> None:
    assert packet["schema_version"] == af6a.SCHEMA_VERSION
    assert packet["record_type"] == "ag96i3af6a_brokered_author_lane_smoke_packet"
    assert packet["chain"] == ["AF4B2", "AF4C", "AF4D", "AF5A", "AF5B"]
    assert packet["budget"]["model_calls_used"] == expected_model_calls
    assert packet["budget"]["max_provider_search_calls"] == 0
    assert packet["budget"]["max_fetch_read_attempts"] == 0
    assert packet["budget"]["max_retrieval_calls"] == 0
    assert packet["budget"]["retries_allowed"] is False
    assert packet["final_answer_outcome_id"]
    assert packet["final_answer_outcome_digest"]
    assert packet["packet_id"]
    assert packet["source_ref_count"] > 0
    assert packet["citation_ref_count"] > 0
    assert packet["caveat_ref_count"] > 0
    assert packet["closed_surface_flags"]["raw_prompt_retained"] is False
    assert packet["closed_surface_flags"]["raw_provider_payload_retained"] is False
    assert packet["closed_surface_flags"]["raw_model_response_retained"] is False
    assert packet["closed_surface_flags"]["search_fetch_retrieval_executed"] is False
    _assert_no_forbidden_packet_fields(packet)


def _assert_no_forbidden_packet_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in af6a.FORBIDDEN_PACKET_KEYS
            _assert_no_forbidden_packet_fields(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_no_forbidden_packet_fields(child)
