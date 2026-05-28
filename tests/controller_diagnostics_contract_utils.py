from __future__ import annotations

from typing import Any

ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY = "controller_diagnostics"
ALLOWED_CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY = "controller_evidence_ledger"
ALLOWED_FUTURE_TRACE_KEY_DELTA = {
    ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY,
    ALLOWED_CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY,
}

_PAYLOAD_KEY_MARKERS = (
    "controller",
    "stage_ledger",
    "evidence_registry",
)


def disallowed_payload_keys(
    mapping: dict[str, Any],
    *,
    allow_controller_diagnostics_trace: bool = False,
) -> set[str]:
    disallowed: set[str] = set()
    for key in mapping:
        if allow_controller_diagnostics_trace and key in ALLOWED_FUTURE_TRACE_KEY_DELTA:
            continue
        if any(marker in key for marker in _PAYLOAD_KEY_MARKERS):
            disallowed.add(key)
    return disallowed


def assert_execution_trace_payload_contract(trace: dict[str, Any]) -> None:
    disallowed = disallowed_payload_keys(
        trace,
        allow_controller_diagnostics_trace=True,
    )
    assert disallowed == set()


def assert_no_top_level_controller_payload(mapping: dict[str, Any]) -> None:
    disallowed = disallowed_payload_keys(mapping)
    assert disallowed == set()


def assert_jsonl_event_controller_payload_contract(event: dict[str, Any]) -> None:
    top_level = {
        key: value
        for key, value in event.items()
        if key != "execution_trace"
    }
    assert_no_top_level_controller_payload(top_level)

    trace = event.get("execution_trace")
    if isinstance(trace, dict):
        assert_execution_trace_payload_contract(trace)


def assert_session_controller_payload_contract(session: dict[str, Any]) -> None:
    top_level = {
        key: value
        for key, value in session.items()
        if key != "execution_trace"
    }
    assert_no_top_level_controller_payload(top_level)

    trace = session.get("execution_trace")
    if isinstance(trace, dict):
        assert_execution_trace_payload_contract(trace)


def trace_key_delta(
    observed_trace: dict[str, Any],
    baseline_trace: dict[str, Any],
) -> set[str]:
    return set(observed_trace) ^ set(baseline_trace)


def assert_trace_key_delta_only_controller_diagnostics(
    observed_trace: dict[str, Any],
    baseline_trace: dict[str, Any],
) -> None:
    delta = trace_key_delta(observed_trace, baseline_trace)
    assert delta <= ALLOWED_FUTURE_TRACE_KEY_DELTA
