"""SearchOS READ transport failures preserve current slot authority.

Proof class: REPAIR regression guard. Validation bucket: phase_focus.
The tests use the ordinary offline product harness with deterministic
synthetic SearchJudgment and READ transport behavior; no live provider or
model call is permitted.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import core.pipeline as pipeline
from core.acquisition_adapters import AcquisitionTransports
from core.searchos_iterative_judgment_runtime import (
    SearchOSJudgmentAction,
    SearchOSRuntimeError,
    SearchOSSlotPosture,
    is_searchos_read_transport_failure_reason,
    mark_searchos_slot_stale_or_invalid,
    record_searchos_read_transport_failure,
)
from core.searchos_slice_a_product_runtime import SEARCHOS_JUDGMENT_SYSTEM_PROMPT
from tests.helpers.offline_ordinary_pipeline import (
    PostRetirementOrdinaryPipelineHarness,
    run_post_retirement_ordinary_pipeline,
)
from tests.test_searchos_post_read_closed_cause_projection_01 import (
    _awaiting_read_state,
)


def _install_two_candidate_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    def response(
        *_args: Any,
        **_kwargs: Any,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        rows = [
            {
                "title": f"Alpha official current operating rule {index}",
                "url": f"https://alpha.example/official-rule-{index}",
                "domain": "alpha.example",
                "credibility": 10 - index,
                "snippet": "Alpha official current operating rule material.",
                "raw_content": (
                    "Alpha official current operating rule material. " * 20
                ),
            }
            for index in (1, 2)
        ]
        return rows, []

    monkeypatch.setattr(pipeline, "search_web_results", response)
    monkeypatch.setattr(pipeline, "search_linkup_results", response)
    monkeypatch.setattr(pipeline, "search_exa_results", response)


def _is_searchos_judgment(system_prompt: str) -> bool:
    return system_prompt.startswith(SEARCHOS_JUDGMENT_SYSTEM_PROMPT)


def _searchos_slots(harness: PostRetirementOrdinaryPipelineHarness) -> list[dict[str, Any]]:
    assert harness.run_kernel is not None
    state = harness.run_kernel.state.searchos_state
    return [state["slots_by_id"][slot_id] for slot_id in state["active_slot_ids"]]


def _install_one_transport_failure_then_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> list[dict[str, Any]]:
    original = PostRetirementOrdinaryPipelineHarness.ask_model
    request_counts_by_slot: dict[str, int] = {}
    records: list[dict[str, Any]] = []

    def ask_model(
        harness: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if not _is_searchos_judgment(system_prompt):
            return original(harness, prompt, system_prompt, **kwargs)
        payload = json.loads(prompt)
        authorized = dict(payload.get("authorized_request") or {})
        result = original(harness, prompt, system_prompt, **kwargs)
        decision = json.loads(result)
        slot_ref = dict(authorized.get("slot_ref") or {})
        slot_id = str(slot_ref.get("slot_id") or "")
        record = {
            "slot_id": slot_id,
            "component_id": slot_ref.get("component_id"),
            "action": decision.get("action"),
            "authorized_option_ids": [
                dict(item.get("candidate_use_option_ref") or {}).get(
                    "candidate_use_option_id"
                )
                for item in authorized.get("candidate_use_options") or ()
            ],
            "emitted_option_id": decision.get("candidate_use_option_id"),
            "candidate_state_ref": deepcopy(
                authorized.get("candidate_state_ref")
            ),
            "candidate_window_ref": deepcopy(
                authorized.get("candidate_window_ref")
            ),
            "custody_count": len(authorized.get("read_custody_refs") or ()),
        }
        if (
            decision.get("action") == SearchOSJudgmentAction.REQUEST_READ_PAGE.value
            and not record["custody_count"]
        ):
            request_count = request_counts_by_slot.get(slot_id, 0) + 1
            request_counts_by_slot[slot_id] = request_count
            if request_count >= 2:
                options = list(authorized.get("candidate_use_options") or ())
                assert len(options) >= 2
                selected_option = dict(options[-1])
                selected_ref = dict(
                    selected_option.get("candidate_use_option_ref") or {}
                )
                decision["candidate_use_option_id"] = selected_ref[
                    "candidate_use_option_id"
                ]
                result = json.dumps(decision)
                record["emitted_option_id"] = decision["candidate_use_option_id"]
        records.append(record)
        return result

    monkeypatch.setattr(
        PostRetirementOrdinaryPipelineHarness,
        "ask_model",
        ask_model,
    )
    return records


def _read_transport_result(payload: dict[str, Any], url: str) -> dict[str, Any]:
    del payload
    return {
        "results": [
            {
                "url": url,
                "attempted_url": url,
                "title": "Offline exact READ source",
                "raw_content": (
                    "Offline exact current official operating-rate material for "
                    + url
                ),
            }
        ],
        "failed_results": [],
    }


def test_one_transport_failure_reuses_existing_judgment_and_read_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_two_candidate_discovery(monkeypatch)
    records = _install_one_transport_failure_then_valid(monkeypatch)
    transport_calls: list[str] = []

    def fail_once_then_succeed(payload: dict[str, Any]) -> dict[str, Any]:
        requested = payload.get("urls")
        url = str(requested[0]) if isinstance(requested, list) else str(requested or "")
        transport_calls.append(url)
        if len(transport_calls) == 1:
            raise RuntimeError("offline physical READ transport failure")
        return _read_transport_result(payload, url)

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="Compare Alpha and Beta current official operating rates.",
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        query_type="comparison",
        router_entities=("Alpha", "Beta"),
        researcher_queries=(
            "Alpha current official operating rate",
            "Beta current official operating rate",
        ),
        deps_overrides={
            "process_search_queries": pipeline.process_search_queries,
            "searchos_read_acquisition_transports": AcquisitionTransports(
                tavily_extract=fail_once_then_succeed
            ),
        },
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    assert harness.run_kernel is not None
    state = harness.run_kernel.state.searchos_state
    slots = _searchos_slots(harness)
    failed_slots = [
        slot
        for slot in slots
        if sum(
            item.get("event") == "read_transport_failure"
            for item in slot["action_history"]
        )
    ]
    assert len(failed_slots) == 1
    failed_slot = failed_slots[0]
    failed_slot_id = failed_slot["slot_id"]
    read_records = [
        record
        for record in records
        if record["slot_id"] == failed_slot_id
        and record["action"] == SearchOSJudgmentAction.REQUEST_READ_PAGE.value
        and record["custody_count"] == 0
    ]
    assert len(read_records) == 2
    assert read_records[0]["emitted_option_id"] in read_records[0]["authorized_option_ids"]
    assert read_records[1]["emitted_option_id"] in read_records[1]["authorized_option_ids"]
    assert read_records[0]["emitted_option_id"] != read_records[1]["emitted_option_id"]
    assert read_records[0]["candidate_state_ref"] == read_records[1]["candidate_state_ref"]
    assert read_records[0]["candidate_window_ref"] == read_records[1]["candidate_window_ref"]

    transport_events = [
        index
        for index, item in enumerate(failed_slot["action_history"])
        if item.get("event") == "read_transport_failure"
    ]
    custody_events = [
        index
        for index, item in enumerate(failed_slot["action_history"])
        if item.get("event") == "read_custody_admitted"
    ]
    assert len(transport_events) == 1
    assert len(custody_events) == 1
    assert transport_events[0] < custody_events[0]
    assert failed_slot["read_nomination_count"] == 2
    assert len(failed_slot["custody_refs"]) == 1
    assert len(failed_slot["semantic_handoff_refs"]) == 1
    assert failed_slot["posture"] == SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value

    peer_slots = [slot for slot in slots if slot["slot_id"] != failed_slot_id]
    assert peer_slots
    assert all(
        slot["posture"] == SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value
        and len(slot["custody_refs"]) == 1
        and len(slot["semantic_handoff_refs"]) == 1
        and not any(
            item.get("event") == "stale_or_invalid"
            for item in slot["action_history"]
        )
        for slot in peer_slots
    )
    assert all(
        not any(
            item.get("event") == "stale_or_invalid"
            for item in slot["action_history"]
        )
        for slot in slots
    )

    projection = outcome.execution_trace["searchos_slice_a"]
    assert len(transport_calls) == 3
    assert len(set(transport_calls)) >= 2
    assert projection["provider_calls_attempted"] == len(transport_calls)
    assert projection["provider_calls_completed"] == len(transport_calls) - 1
    assert state["budget"]["charged_logical_judgment_calls"] == len(records)
    assert state["budget"]["failed_logical_judgment_calls"] == 0
    assert failed_slot["judgment_call_count"] >= 2
    assert failed_slot["read_nomination_count"] <= state["policy_snapshot"][
        "read_nominations_per_slot"
    ]


def test_repeated_transport_failures_terminate_at_installed_budgets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_two_candidate_discovery(monkeypatch)
    original = PostRetirementOrdinaryPipelineHarness.ask_model
    transport_calls: list[str] = []
    request_counts_by_slot: dict[str, int] = {}

    def bounded_model(
        harness: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if not _is_searchos_judgment(system_prompt):
            return original(harness, prompt, system_prompt, **kwargs)
        payload = json.loads(prompt)
        authorized = dict(payload.get("authorized_request") or {})
        if SearchOSJudgmentAction.REQUEST_READ_PAGE.value not in set(
            authorized.get("legal_actions") or ()
        ):
            prior = harness.read_assessment_decision
            harness.read_assessment_decision = "NO_READ"
            try:
                return original(harness, prompt, system_prompt, **kwargs)
            finally:
                harness.read_assessment_decision = prior
        result = original(harness, prompt, system_prompt, **kwargs)
        decision = json.loads(result)
        if decision.get("action") == SearchOSJudgmentAction.REQUEST_READ_PAGE.value:
            slot_id = str(
                dict(authorized.get("slot_ref") or {}).get("slot_id") or ""
            )
            request_count = request_counts_by_slot.get(slot_id, 0) + 1
            request_counts_by_slot[slot_id] = request_count
            options = list(authorized.get("candidate_use_options") or ())
            assert options
            selected_option = dict(options[min(request_count - 1, len(options) - 1)])
            selected_ref = dict(
                selected_option.get("candidate_use_option_ref") or {}
            )
            decision["candidate_use_option_id"] = selected_ref[
                "candidate_use_option_id"
            ]
            result = json.dumps(decision)
        return result

    def always_fail(payload: dict[str, Any]) -> dict[str, Any]:
        requested = payload.get("urls")
        url = str(requested[0]) if isinstance(requested, list) else str(requested or "")
        transport_calls.append(url)
        raise RuntimeError("offline repeated physical READ transport failure")

    monkeypatch.setattr(
        PostRetirementOrdinaryPipelineHarness,
        "ask_model",
        bounded_model,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        deps_overrides={
            "process_search_queries": pipeline.process_search_queries,
            "searchos_read_acquisition_transports": AcquisitionTransports(
                tavily_extract=always_fail
            ),
        },
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    assert harness.run_kernel is not None
    state = harness.run_kernel.state.searchos_state
    slot = next(iter(state["slots_by_id"].values()))
    policy = state["policy_snapshot"]
    transport_failure_count = sum(
        item.get("event") == "read_transport_failure"
        for item in slot["action_history"]
    )
    assert slot["read_nomination_count"] == policy["read_nominations_per_slot"]
    assert transport_failure_count == slot["read_nomination_count"]
    assert len(transport_calls) == slot["read_nomination_count"]
    assert slot["posture"] in {
        SearchOSSlotPosture.UNRESOLVED_HANDOFF.value,
        SearchOSSlotPosture.BUDGET_EXHAUSTED.value,
    }
    assert not any(
        item.get("event") == "stale_or_invalid"
        for item in slot["action_history"]
    )
    assert state["budget"]["charged_logical_judgment_calls"] == slot[
        "judgment_call_count"
    ]
    assert state["budget"]["failed_logical_judgment_calls"] == 0
    assert outcome.execution_trace["searchos_slice_a"]["provider_calls_attempted"] == len(
        transport_calls
    )
    assert outcome.execution_trace["searchos_slice_a"]["provider_calls_completed"] == 0


def test_transport_transition_preserves_current_state_and_rejects_true_staleness() -> None:
    state = _awaiting_read_state()
    before_slot = deepcopy(state["slots_by_id"]["slot-1"])

    assert is_searchos_read_transport_failure_reason(
        "read_transport_failure:selected_provider_transport_failed"
    )
    assert not is_searchos_read_transport_failure_reason("candidate_packet_stale")
    restored = record_searchos_read_transport_failure(
        state,
        slot_id="slot-1",
        reason="read_transport_failure:selected_provider_transport_failed",
    )
    after_slot = restored["slots_by_id"]["slot-1"]
    assert after_slot["posture"] == SearchOSSlotPosture.ACTIVE_UNJUDGED.value
    assert after_slot["current_candidate_state_ref"] == before_slot[
        "current_candidate_state_ref"
    ]
    assert after_slot["current_window_ref"] == before_slot["current_window_ref"]
    assert after_slot["read_nomination_count"] == before_slot["read_nomination_count"]
    assert after_slot["custody_refs"] == []
    assert after_slot["action_history"][-1]["event"] == "read_transport_failure"

    for reason in ("candidate_packet_stale", "read_nomination_already_disposed"):
        stale = mark_searchos_slot_stale_or_invalid(
            state,
            slot_id="slot-1",
            reason=reason,
        )
        with pytest.raises(
            SearchOSRuntimeError,
            match="does not follow REQUEST_READ_PAGE",
        ):
            record_searchos_read_transport_failure(
                stale,
                slot_id="slot-1",
                reason="read_transport_failure:selected_provider_transport_failed",
            )
