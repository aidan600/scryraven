"""SearchOS model-output rejection and bounded retry semantics.

Proof class: PRODUCT-supporting structural proof. Validation bucket:
phase_focus. The fixtures use the ordinary offline product harness and never
invoke a live provider or model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.searchos_iterative_judgment_runtime import (
    SearchOSJudgmentAction,
    SearchOSSlotPosture,
    is_searchos_recoverable_judgment_output_failure_reason,
)
from core.searchos_slice_a_product_runtime import SEARCHOS_JUDGMENT_SYSTEM_PROMPT
from tests.helpers.offline_ordinary_pipeline import (
    PostRetirementOrdinaryPipelineHarness,
    run_post_retirement_ordinary_pipeline,
)


def _searchos_model_prompt(system_prompt: str) -> bool:
    return system_prompt.startswith(SEARCHOS_JUDGMENT_SYSTEM_PROMPT)


def _install_one_invalid_read_then_valid(
    monkeypatch: pytest.MonkeyPatch,
    *,
    target_component_id: str | None = None,
) -> list[dict[str, Any]]:
    original = PostRetirementOrdinaryPipelineHarness.ask_model
    records: list[dict[str, Any]] = []
    invalidated = False

    def ask_model(
        harness: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        nonlocal invalidated
        if not _searchos_model_prompt(system_prompt):
            return original(harness, prompt, system_prompt, **kwargs)
        payload = json.loads(prompt)
        authorized = dict(payload.get("authorized_request") or {})
        result = original(harness, prompt, system_prompt, **kwargs)
        decision = json.loads(result)
        slot_ref = dict(authorized.get("slot_ref") or {})
        component_id = slot_ref.get("component_id")
        record = {
            "slot_id": slot_ref.get("slot_id"),
            "component_id": component_id,
            "action": decision.get("action"),
            "authorized_option_ids": [
                dict(item.get("candidate_use_option_ref") or {}).get(
                    "candidate_use_option_id"
                )
                for item in authorized.get("candidate_use_options") or ()
            ],
            "emitted_option_id": decision.get("candidate_use_option_id"),
        }
        records.append(record)
        if (
            not invalidated
            and decision.get("action") == SearchOSJudgmentAction.REQUEST_READ_PAGE.value
            and (
                target_component_id is None
                or component_id == target_component_id
            )
        ):
            invalidated = True
            decision["candidate_use_option_id"] = "searchos-option:unauthorized"
            record["emitted_option_id"] = decision["candidate_use_option_id"]
            return json.dumps(decision)
        return result

    monkeypatch.setattr(PostRetirementOrdinaryPipelineHarness, "ask_model", ask_model)
    return records


def _judgment_model_calls(harness: PostRetirementOrdinaryPipelineHarness) -> int:
    return sum(_searchos_model_prompt(prompt) for prompt in harness.model_system_prompts)


def _slot_by_component(
    harness: PostRetirementOrdinaryPipelineHarness,
) -> dict[str, dict[str, Any]]:
    state = harness.run_kernel.state.searchos_state
    return {
        str(dict(slot.get("component_ref") or {}).get("component_id")): slot
        for slot in state["slots_by_id"].values()
    }


def test_read_window_output_rejection_reuses_only_existing_judgment_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = _install_one_invalid_read_then_valid(monkeypatch)
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
    )

    read_records = [
        record
        for record in records
        if record["action"] == SearchOSJudgmentAction.REQUEST_READ_PAGE.value
    ]
    assert len(read_records) >= 2
    assert read_records[0]["authorized_option_ids"]
    assert read_records[1]["authorized_option_ids"] == read_records[0][
        "authorized_option_ids"
    ]
    assert read_records[0]["emitted_option_id"] == "searchos-option:unauthorized"
    assert read_records[0]["emitted_option_id"] not in read_records[0][
        "authorized_option_ids"
    ]
    assert read_records[1]["emitted_option_id"] in read_records[1][
        "authorized_option_ids"
    ]

    state = harness.run_kernel.state.searchos_state
    slot = next(iter(state["slots_by_id"].values()))
    assert slot["posture"] == SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value
    assert slot["judgment_call_count"] == len(records)
    assert state["budget"]["charged_logical_judgment_calls"] == len(records)
    assert state["budget"]["failed_logical_judgment_calls"] == 1
    assert slot["read_nomination_count"] == 1
    assert len(slot["custody_refs"]) == 1
    assert len(slot["semantic_handoff_refs"]) == 1
    assert len(harness.read_transport_calls) == 1
    assert any(
        item.get("event") == "judgment_output_rejected"
        for item in slot["action_history"]
    )
    assert not any(
        item.get("event") == "stale_or_invalid"
        for item in slot["action_history"]
    )
    assert "searchos-option:unauthorized" not in json.dumps(
        {"state": state, "searchos": outcome.execution_trace["searchos_slice_a"]},
        sort_keys=True,
    )


def test_repeated_invalid_read_output_stops_at_installed_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        read_assessment_decision="INVALID_NOMINATION",
    )

    state = harness.run_kernel.state.searchos_state
    slot = next(iter(state["slots_by_id"].values()))
    assert _judgment_model_calls(harness) == 3
    assert slot["judgment_call_count"] == 3
    assert state["budget"]["charged_logical_judgment_calls"] == 3
    assert state["budget"]["failed_logical_judgment_calls"] == 3
    assert state["budget"]["judgment_call_ceiling"] == 3
    assert slot["posture"] == SearchOSSlotPosture.BUDGET_EXHAUSTED.value
    assert len(harness.read_transport_calls) == 0
    assert sum(
        item.get("event") == "judgment_output_rejected"
        for item in slot["action_history"]
    ) == 3
    assert not any(
        item.get("event") == "stale_or_invalid"
        for item in slot["action_history"]
    )
    assert "not-an-eligible-option" not in json.dumps(
        {"state": state, "searchos": outcome.execution_trace["searchos_slice_a"]},
        sort_keys=True,
    )


def test_rejected_component_two_output_preserves_component_one_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = _install_one_invalid_read_then_valid(
        monkeypatch,
        target_component_id="component-2",
    )
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="Compare Alpha and Beta current official operating rates.",
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        query_type="comparison",
        router_entities=("Alpha", "Beta"),
        researcher_queries=[
            "Alpha current official operating rate",
            "Beta current official operating rate",
        ],
    )

    slots = _slot_by_component(harness)
    assert set(slots) >= {"component-1", "component-2"}
    component_one = slots["component-1"]
    component_two = slots["component-2"]
    assert component_one["posture"] == SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value
    assert len(component_one["custody_refs"]) == 1
    assert len(component_one["semantic_handoff_refs"]) == 1
    assert not any(
        item.get("event") == "stale_or_invalid"
        for item in component_one["action_history"]
    )
    assert all(
        item.get("stale") is False for item in component_one["custody_refs"]
    )
    assert component_one["component_ref"]["component_id"] == "component-1"

    component_two_reads = [
        record
        for record in records
        if record["component_id"] == "component-2"
        and record["action"] == SearchOSJudgmentAction.REQUEST_READ_PAGE.value
    ]
    assert len(component_two_reads) >= 2
    assert component_two_reads[0]["emitted_option_id"] == "searchos-option:unauthorized"
    assert component_two_reads[1]["emitted_option_id"] in component_two_reads[1][
        "authorized_option_ids"
    ]
    assert component_two["posture"] == SearchOSSlotPosture.SEMANTICALLY_HANDED_OFF.value
    assert len(component_two["custody_refs"]) == 1
    assert len(component_two["semantic_handoff_refs"]) == 1
    assert harness.run_kernel.state.searchos_state["budget"][
        "failed_logical_judgment_calls"
    ] == 1


def test_recoverable_reason_is_closed_and_does_not_include_canonical_staleness() -> None:
    assert is_searchos_recoverable_judgment_output_failure_reason(
        "model_output_invalid:read_nomination_is_outside_current_candidate_window"
    )
    assert is_searchos_recoverable_judgment_output_failure_reason(
        "model_output_invalid:post-read_action_requires_exact_read_insufficient_assessments"
    )
    assert not is_searchos_recoverable_judgment_output_failure_reason(
        "model_output_invalid:candidate_packet_stale"
    )
    assert not is_searchos_recoverable_judgment_output_failure_reason(
        "model_output_invalid:transient_candidate_direction_binds_a_stale_lineage_snapshot"
    )
    assert not is_searchos_recoverable_judgment_output_failure_reason(
        "model_output_malformed"
    )
