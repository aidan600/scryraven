"""Passive ControllerState mirror for already-computed run metadata.

This helper records basic run metadata into RunController.state. It does not
derive metadata, choose routing, call providers, retrieve, or persist telemetry.
"""

from __future__ import annotations

from copy import deepcopy

from core.run_controller import RunController


def record_run_metadata_snapshot(
    controller: RunController,
    *,
    session_id: str | None,
    run_id: str | None,
    query: str | None,
    mode: str | None,
    current_date: str | None,
    core_topic: str | None,
    intent: str | None,
    complexity: str | None,
) -> RunController:
    """Mirror already-computed run metadata into passive ControllerState."""
    controller.state.session_id = deepcopy(session_id)
    controller.state.run_id = deepcopy(run_id)
    controller.state.query = deepcopy(query)
    controller.state.mode = deepcopy(mode)
    controller.state.current_date = deepcopy(current_date)
    controller.state.core_topic = deepcopy(core_topic)
    controller.state.intent = deepcopy(intent)
    controller.state.complexity = deepcopy(complexity)
    return controller


__all__ = ["record_run_metadata_snapshot"]
