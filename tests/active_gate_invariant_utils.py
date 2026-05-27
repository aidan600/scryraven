from __future__ import annotations

from typing import Any

from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
)

_PROMOTED_ACTIVE_GATE_ACTIONS = {
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
}


def assert_active_gate_packet_invariants(
    packet: dict[str, Any],
    *,
    checkpoint_action_name: str,
    promoted_action_name: str | None,
    executed_action_name: str | None,
    gate_reason: str,
) -> None:
    assert packet["available"] is True
    assert packet["shadow_mode"] is False
    assert packet["runtime_behavior_changed"] is True
    assert packet["checkpoint_decision_count"] == 1

    decision = packet["decision"]
    assert isinstance(decision, dict)
    assert decision["action_name"] == checkpoint_action_name
    assert decision["shadow_mode"] is False
    assert decision["runtime_behavior_changed"] is True

    assert packet["recommended_action_name"] == checkpoint_action_name
    assert packet["checkpoint_action_name"] == checkpoint_action_name
    assert packet["promoted_action_name"] == promoted_action_name
    assert packet["executed_action_name"] == executed_action_name
    assert packet["gate_reason"] == gate_reason

    if promoted_action_name is not None:
        assert promoted_action_name in _PROMOTED_ACTIVE_GATE_ACTIONS
    if executed_action_name is not None:
        assert executed_action_name in {
            RECOVER_MISSING_SOURCE_CLASS,
            RECOVER_WEAK_CORPUS,
            RESOLVE_CONFLICT,
        }
        assert executed_action_name == promoted_action_name


def assert_blocked_or_skipped(
    packet: dict[str, Any],
    action_name: str,
    rationale: str,
) -> None:
    blocked_or_skipped_actions = packet["blocked_or_skipped_actions"]
    assert isinstance(blocked_or_skipped_actions, dict)
    assert blocked_or_skipped_actions[action_name] == rationale


def assert_passive_checkpoint_handoff_reference(
    handoff_reference: dict[str, Any],
    *,
    action_name: str,
) -> None:
    assert handoff_reference["action_name"] == action_name
    assert handoff_reference["shadow_mode"] is True
    assert handoff_reference["runtime_behavior_changed"] is False
    assert "promoted_action_name" not in handoff_reference
    assert "executed_action_name" not in handoff_reference
