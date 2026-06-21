from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import scripts.ag96i3af6a_brokered_author_lane_smoke as af6a
from tests.ag96_static_guards import imported_modules

ROOT = Path(__file__).resolve().parents[1]
ANSWER_TEXT = "AF6A fake mode answer."


class MustNotCallAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *_args: Any, **_kwargs: Any) -> str:
        self.calls += 1
        raise AssertionError("tracked AF6A code must not call live adapters")


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"broker_live_mode": False}, "broker live mode"),
        ({"confirm_live_provider_call": False}, "confirmation"),
        ({}, "deferred"),
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
    }
    params.update(overrides)
    with pytest.raises(af6a.AF6AFailClosed, match=match):
        af6a.run_af6a_smoke(**params)


def test_af6a_broker_live_path_is_deferred_and_does_not_call_adapter() -> None:
    job_id = "caller-provided-af6a-label"
    adapter = MustNotCallAdapter()
    with pytest.raises(af6a.AF6AFailClosed, match="deferred") as exc_info:
        af6a.run_af6a_smoke(
            job_id=job_id,
            broker_live_mode=True,
            confirm_live_provider_call=True,
        )
    assert adapter.calls == 0
    packet = exc_info.value.packet
    assert packet is not None
    assert packet["job_id"] == job_id
    assert packet["status"] == "deferred"
    assert packet["deferred_reason"] == "broker_live_execution_not_enabled"
    assert packet["final_answer_created"] is False
    _assert_model_call_custody(
        packet,
        expected_mode="broker_live_deferred",
        expected_status="deferred",
        expected_source="broker_live_adapter_deferred",
        expected_max_model_calls=1,
        expected_fake_adapter_used=False,
        expected_broker_live_adapter_deferred=True,
        expected_broker_live_requested=True,
    )
    _assert_deferred_sanitized_shape(packet)


def test_af6a_fake_mode_has_sanitized_output_without_model_call_budget() -> None:
    result = af6a.run_af6a_smoke(
        job_id=af6a.JOB_ID,
        broker_live_mode=False,
        confirm_live_provider_call=False,
        fake_mode=True,
        fake_answer=ANSWER_TEXT,
    )
    packet = result.packet

    assert packet["mode"] == "fake"
    assert packet["budget"]["max_model_calls"] == 0
    assert packet["budget"]["model_calls_used"] == 0
    _assert_model_call_custody(
        packet,
        expected_mode="fake",
        expected_status="completed_fake",
        expected_source="injected_fake_model_adapter",
        expected_max_model_calls=0,
        expected_fake_adapter_used=True,
        expected_broker_live_adapter_deferred=False,
        expected_broker_live_requested=False,
    )
    assert packet["final_answer_text"] == ANSWER_TEXT
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
        "importlib",
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
        "importlib",
        "adapter_factory",
        "create_model_adapter",
        "request_live_validation_broker",
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
    assert packet["budget"]["live_model_call_performed"] is False
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
    assert packet["closed_surface_flags"]["raw_model_request_retained"] is False
    assert packet["closed_surface_flags"]["raw_provider_payload_retained"] is False
    assert packet["closed_surface_flags"]["raw_payload_retained"] is False
    assert packet["closed_surface_flags"]["raw_model_response_retained"] is False
    assert packet["closed_surface_flags"]["private_logs_retained"] is False
    assert packet["closed_surface_flags"]["db_cache_rows_retained"] is False
    assert packet["closed_surface_flags"]["full_trace_retained"] is False
    assert packet["closed_surface_flags"]["search_fetch_retrieval_executed"] is False
    _assert_no_forbidden_packet_fields(packet)


def _assert_deferred_sanitized_shape(packet: dict[str, Any]) -> None:
    assert packet["schema_version"] == af6a.SCHEMA_VERSION
    assert packet["record_type"] == "ag96i3af6a_brokered_author_lane_smoke_packet"
    assert packet["chain"] == []
    assert packet["budget"]["max_model_calls"] == 1
    assert packet["budget"]["model_calls_used"] == 0
    assert packet["budget"]["live_model_call_performed"] is False
    assert packet["budget"]["max_provider_search_calls"] == 0
    assert packet["budget"]["max_fetch_read_attempts"] == 0
    assert packet["budget"]["max_retrieval_calls"] == 0
    assert packet["budget"]["retries_allowed"] is False
    assert packet["closed_surface_flags"]["raw_prompt_retained"] is False
    assert packet["closed_surface_flags"]["raw_model_request_retained"] is False
    assert packet["closed_surface_flags"]["raw_provider_payload_retained"] is False
    assert packet["closed_surface_flags"]["raw_payload_retained"] is False
    assert packet["closed_surface_flags"]["raw_model_response_retained"] is False
    assert packet["closed_surface_flags"]["private_logs_retained"] is False
    assert packet["closed_surface_flags"]["db_cache_rows_retained"] is False
    assert packet["closed_surface_flags"]["full_trace_retained"] is False
    assert packet["closed_surface_flags"]["search_fetch_retrieval_executed"] is False
    _assert_no_forbidden_packet_fields(packet)


def _assert_model_call_custody(
    packet: dict[str, Any],
    *,
    expected_mode: str,
    expected_status: str,
    expected_source: str,
    expected_max_model_calls: int,
    expected_fake_adapter_used: bool,
    expected_broker_live_adapter_deferred: bool,
    expected_broker_live_requested: bool,
) -> None:
    assert packet["author_model_call_mode"] == expected_mode
    assert packet["author_model_call_status"] == expected_status
    assert packet["author_model_call_source"] == expected_source
    assert packet["max_model_calls"] == expected_max_model_calls
    assert packet["model_calls_used"] == 0
    assert packet["mock_model_adapter_calls_used"] == 0
    assert packet["live_model_call_performed"] is False
    assert packet["live_adapter_mocked"] is False
    assert packet["fake_adapter_used"] is expected_fake_adapter_used
    assert packet["broker_live_adapter_deferred"] is expected_broker_live_adapter_deferred
    assert packet["broker_live_requested"] is expected_broker_live_requested
    assert packet["broker_live_execution_enabled"] is False
    assert packet["prompt_raw_payload_retained"] is False
    assert packet["model_request_raw_payload_retained"] is False
    assert packet["provider_raw_payload_retained"] is False
    assert packet["payload_raw_retained"] is False
    assert packet["model_response_raw_payload_retained"] is False
    assert packet["private_logs_retained"] is False
    assert packet["db_cache_rows_retained"] is False
    assert packet["full_trace_retained"] is False


def _assert_no_forbidden_packet_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in af6a.FORBIDDEN_PACKET_KEYS
            _assert_no_forbidden_packet_fields(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_no_forbidden_packet_fields(child)
