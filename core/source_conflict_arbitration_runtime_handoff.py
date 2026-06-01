"""Runtime/AnswerContract-visible handoff for AG-77B conflict arbitration.

This module exposes already-built AG-77A/AG-77B conflict posture as JSON-safe
Controller and AnswerContract runtime visibility. It does not retrieve, rank,
resolve, cite, prompt, persist, call providers, alter Author inputs, or change
final-answer behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from core.source_conflict_arbitration import (
    SOURCE_CONFLICT_ARBITRATION_TRACE_KEY,
    SourceConflictAnswerPosture,
    SourceConflictArbitrationDisposition,
    SourceConflictArbitrationState,
    arbitrate_source_conflicts,
)
from core.source_conflict_model import (
    SOURCE_CONFLICT_SCHEMA_VERSION,
    SourceConflictRepresentation,
)

SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_SCHEMA_VERSION = (
    "AG77C.conflict_arbitration_runtime_answercontract_handoff.v1"
)
SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_TRACE_KEY = (
    "source_conflict_arbitration"
)


@dataclass(frozen=True)
class SourceConflictArbitrationRuntimeState:
    """JSON-safe Controller/AnswerContract-visible AG-77C state."""

    controller_state: dict[str, Any]

    def to_controller_state(self) -> dict[str, Any]:
        return deepcopy(self.controller_state)

    def to_trace_fragment(self) -> dict[str, Any]:
        return {
            SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_TRACE_KEY: (
                self.to_controller_state()
            )
        }


@dataclass(frozen=True)
class SourceConflictArbitrationRuntimeHandoff:
    """Visibility-only handoff for Controller / AnswerContract runtime traces."""

    state: SourceConflictArbitrationRuntimeState

    def to_controller_state(self) -> dict[str, Any]:
        return self.state.to_controller_state()

    def execution_trace_fragment(self) -> dict[str, Any]:
        return self.state.to_trace_fragment()


def build_source_conflict_arbitration_runtime_handoff(
    *,
    representation: SourceConflictRepresentation | None = None,
    arbitration_state: SourceConflictArbitrationState | None = None,
) -> SourceConflictArbitrationRuntimeHandoff:
    """Build a visibility-only runtime handoff without changing behavior.

    If AG-77B arbitration state is absent but an AG-77A representation is
    supplied, AG-77B arbitration is computed from that immutable representation.
    If no representation is supplied, the handoff exposes an explicit
    no-conflict/no-answer-impact default instead of constructing conflicts.
    """

    if arbitration_state is None and representation is not None:
        arbitration_state = arbitrate_source_conflicts(representation)

    if arbitration_state is None:
        state = _no_conflict_controller_state()
    else:
        state = _controller_state_from_arbitration(
            arbitration_state=arbitration_state,
            representation=representation,
        )
    return SourceConflictArbitrationRuntimeHandoff(
        state=SourceConflictArbitrationRuntimeState(controller_state=state)
    )


def source_conflict_arbitration_runtime_trace_fragment(
    *,
    representation: SourceConflictRepresentation | None = None,
    arbitration_state: SourceConflictArbitrationState | None = None,
) -> dict[str, Any]:
    """Return the stable AG-77C trace fragment for runtime attachment."""

    return build_source_conflict_arbitration_runtime_handoff(
        representation=representation,
        arbitration_state=arbitration_state,
    ).execution_trace_fragment()


def _controller_state_from_arbitration(
    *,
    arbitration_state: SourceConflictArbitrationState,
    representation: SourceConflictRepresentation | None,
) -> dict[str, Any]:
    arbitration_controller_state = deepcopy(arbitration_state.to_controller_state())
    return {
        "schema_version": SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_SCHEMA_VERSION,
        "trace_key": SOURCE_CONFLICT_ARBITRATION_TRACE_KEY,
        "consumer": "Controller / AnswerContract runtime visibility",
        "author_exposed": False,
        "visibility_only": True,
        "source_conflict_representation_available": representation is not None,
        "input_representation_schema_version": arbitration_controller_state.get(
            "input_representation_schema_version",
            SOURCE_CONFLICT_SCHEMA_VERSION,
        ),
        "arbitration_schema_version": arbitration_controller_state.get(
            "schema_version"
        ),
        "arbitration": arbitration_controller_state,
        "top_level_disposition": _top_level_disposition(arbitration_controller_state),
        "top_level_answer_posture": arbitration_controller_state.get(
            "top_level_answer_posture",
            SourceConflictAnswerPosture.NO_ANSWER_IMPACT.value,
        ),
        "unresolved_blocking_count": int(
            arbitration_controller_state.get("unresolved_blocking_count", 0) or 0
        ),
        "unresolved_nonblocking_count": int(
            arbitration_controller_state.get("unresolved_nonblocking_count", 0) or 0
        ),
        "preserved_source_ids": _preserved_source_ids(arbitration_controller_state),
        "ledger_compatible": bool(
            arbitration_controller_state.get("ledger_compatible", True)
        ),
        "no_conflict_default": False,
        "no_answer_impact": arbitration_controller_state.get(
            "top_level_answer_posture"
        )
        == SourceConflictAnswerPosture.NO_ANSWER_IMPACT.value,
        "no_prose_change": True,
        "final_answer_behavior_changed": False,
        "runtime_behavior_changed": False,
        "author_behavior_changed": False,
        "author_exposure_changed": False,
        "citation_behavior_changed": False,
        "prompt_behavior_changed": False,
        "provider_search_query_behavior_changed": False,
        "retrieval_behavior_changed": False,
        "numeric_output_behavior_changed": False,
    }


def _no_conflict_controller_state() -> dict[str, Any]:
    return {
        "schema_version": SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_SCHEMA_VERSION,
        "trace_key": SOURCE_CONFLICT_ARBITRATION_TRACE_KEY,
        "consumer": "Controller / AnswerContract runtime visibility",
        "author_exposed": False,
        "visibility_only": True,
        "source_conflict_representation_available": False,
        "input_representation_schema_version": SOURCE_CONFLICT_SCHEMA_VERSION,
        "arbitration_schema_version": None,
        "arbitration": None,
        "top_level_disposition": SourceConflictArbitrationDisposition.NO_CONFLICT.value,
        "top_level_answer_posture": SourceConflictAnswerPosture.NO_ANSWER_IMPACT.value,
        "unresolved_blocking_count": 0,
        "unresolved_nonblocking_count": 0,
        "preserved_source_ids": [],
        "ledger_compatible": True,
        "no_conflict_default": True,
        "no_answer_impact": True,
        "no_prose_change": True,
        "final_answer_behavior_changed": False,
        "runtime_behavior_changed": False,
        "author_behavior_changed": False,
        "author_exposure_changed": False,
        "citation_behavior_changed": False,
        "prompt_behavior_changed": False,
        "provider_search_query_behavior_changed": False,
        "retrieval_behavior_changed": False,
        "numeric_output_behavior_changed": False,
    }


def _top_level_disposition(arbitration_controller_state: dict[str, Any]) -> str:
    groups = arbitration_controller_state.get("groups") or []
    dispositions = [str(group.get("group_disposition")) for group in groups]
    priority = (
        SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING.value,
        SourceConflictArbitrationDisposition.NEEDS_MORE_EVIDENCE.value,
        SourceConflictArbitrationDisposition.REPORT_BOTH_BY_SCOPE.value,
        SourceConflictArbitrationDisposition.REPORT_BOTH.value,
        SourceConflictArbitrationDisposition.PREFER_CLAIM_A.value,
        SourceConflictArbitrationDisposition.PREFER_CLAIM_B.value,
        SourceConflictArbitrationDisposition.UNRESOLVED_NONBLOCKING.value,
        SourceConflictArbitrationDisposition.BACKGROUND_ONLY.value,
        SourceConflictArbitrationDisposition.IGNORE_NON_MATERIAL_CONFLICT.value,
        SourceConflictArbitrationDisposition.NO_CONFLICT.value,
    )
    return next(
        (disposition for disposition in priority if disposition in dispositions),
        SourceConflictArbitrationDisposition.NO_CONFLICT.value,
    )


def _preserved_source_ids(arbitration_controller_state: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    preserved: list[str] = []
    for group in arbitration_controller_state.get("groups") or []:
        for source_id in group.get("involved_source_ids") or []:
            text = str(source_id or "").strip()
            if text and text not in seen:
                preserved.append(text)
                seen.add(text)
    return preserved


__all__ = [
    "SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_SCHEMA_VERSION",
    "SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_TRACE_KEY",
    "SourceConflictArbitrationRuntimeHandoff",
    "SourceConflictArbitrationRuntimeState",
    "build_source_conflict_arbitration_runtime_handoff",
    "source_conflict_arbitration_runtime_trace_fragment",
]
