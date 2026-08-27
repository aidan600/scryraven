from __future__ import annotations

from copy import deepcopy
from typing import Any


def snapshot_o2_closed_surfaces(kernel: Any) -> dict[str, Any]:
    return {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
        "followup_final_answer_packet_readiness_state": deepcopy(
            kernel.state.followup_final_answer_packet_readiness_state
        ),
        "followup_final_answer_packet_readiness_projection": deepcopy(
            kernel.state.followup_final_answer_packet_readiness_projection
        ),
        "followup_final_answer_packet_state": deepcopy(
            kernel.state.followup_final_answer_packet_state
        ),
        "followup_author_gate_state": deepcopy(kernel.state.followup_author_gate_state),
        "followup_author_observation_state": deepcopy(
            kernel.state.followup_author_observation_state
        ),
    }


def assert_o2_closed_surfaces_unchanged(
    kernel: Any,
    before: dict[str, Any],
) -> None:
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.author_observation == before["author_observation"]
    assert kernel.state.final_answer_outcome == before["final_answer_outcome"]
    assert kernel.state.followup_final_answer_packet_readiness_state == before[
        "followup_final_answer_packet_readiness_state"
    ]
    assert kernel.state.followup_final_answer_packet_readiness_projection == before[
        "followup_final_answer_packet_readiness_projection"
    ]
    assert kernel.state.followup_final_answer_packet_state == before[
        "followup_final_answer_packet_state"
    ]
    assert kernel.state.followup_author_gate_state == before["followup_author_gate_state"]
    assert kernel.state.followup_author_observation_state == before[
        "followup_author_observation_state"
    ]


def snapshot_o2_boundary_state(kernel: Any) -> dict[str, Any]:
    return {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "followup_blocked_final_answer_packet_shell_state": deepcopy(
            kernel.state.followup_blocked_final_answer_packet_shell_state
        ),
        "followup_blocked_final_answer_packet_shell_projection": deepcopy(
            kernel.state.followup_blocked_final_answer_packet_shell_projection
        ),
        "followup_blocked_final_answer_packet_shell_history": deepcopy(
            kernel.state.followup_blocked_final_answer_packet_shell_history
        ),
        "followup_final_answer_packet_state": deepcopy(
            kernel.state.followup_final_answer_packet_state
        ),
        "followup_final_answer_packet_projection": deepcopy(
            kernel.state.followup_final_answer_packet_projection
        ),
        "followup_final_answer_packet_history": deepcopy(
            kernel.state.followup_final_answer_packet_history
        ),
        "projections": deepcopy(kernel.state.projections),
        "action_statuses": deepcopy(kernel.state.action_statuses),
        "stage_statuses": deepcopy(kernel.state.stage_statuses),
        "reduced_action_ids": deepcopy(kernel.state.reduced_action_ids),
        "observations": deepcopy(kernel.state.observations),
        "next_observation_sequence": kernel.state.next_observation_sequence,
    }


def assert_o2_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert kernel.state.final_answer_packet == snapshot["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.final_answer_authority_projection == snapshot[
        "final_answer_authority_projection"
    ]
    assert kernel.state.followup_blocked_final_answer_packet_shell_state == snapshot[
        "followup_blocked_final_answer_packet_shell_state"
    ]
    assert kernel.state.followup_blocked_final_answer_packet_shell_projection == snapshot[
        "followup_blocked_final_answer_packet_shell_projection"
    ]
    assert kernel.state.followup_blocked_final_answer_packet_shell_history == snapshot[
        "followup_blocked_final_answer_packet_shell_history"
    ]
    assert kernel.state.followup_final_answer_packet_state == snapshot[
        "followup_final_answer_packet_state"
    ]
    assert kernel.state.followup_final_answer_packet_projection == snapshot[
        "followup_final_answer_packet_projection"
    ]
    assert kernel.state.followup_final_answer_packet_history == snapshot[
        "followup_final_answer_packet_history"
    ]
    assert kernel.state.projections == snapshot["projections"]
    assert kernel.state.action_statuses == snapshot["action_statuses"]
    assert kernel.state.stage_statuses == snapshot["stage_statuses"]
    assert kernel.state.reduced_action_ids == snapshot["reduced_action_ids"]
    assert kernel.state.observations == snapshot["observations"]
    assert kernel.state.next_observation_sequence == snapshot[
        "next_observation_sequence"
    ]


def snapshot_p1_boundary_state(kernel: Any) -> dict[str, Any]:
    return {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "followup_final_evidence_selection_state": deepcopy(
            kernel.state.followup_final_evidence_selection_state
        ),
        "followup_final_evidence_selection_projection": deepcopy(
            kernel.state.followup_final_evidence_selection_projection
        ),
        "followup_final_evidence_selection_history": deepcopy(
            kernel.state.followup_final_evidence_selection_history
        ),
        "followup_final_answer_packet_state": deepcopy(
            kernel.state.followup_final_answer_packet_state
        ),
        "followup_blocked_final_answer_packet_shell_state": deepcopy(
            kernel.state.followup_blocked_final_answer_packet_shell_state
        ),
        "projections": deepcopy(kernel.state.projections),
        "action_statuses": deepcopy(kernel.state.action_statuses),
        "stage_statuses": deepcopy(kernel.state.stage_statuses),
        "reduced_action_ids": deepcopy(kernel.state.reduced_action_ids),
        "observations": deepcopy(kernel.state.observations),
        "next_observation_sequence": kernel.state.next_observation_sequence,
    }


def assert_p1_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert kernel.state.final_answer_packet == snapshot["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == snapshot[
        "final_answer_authority_projection"
    ]
    assert kernel.state.followup_final_evidence_selection_state == snapshot[
        "followup_final_evidence_selection_state"
    ]
    assert kernel.state.followup_final_evidence_selection_projection == snapshot[
        "followup_final_evidence_selection_projection"
    ]
    assert kernel.state.followup_final_evidence_selection_history == snapshot[
        "followup_final_evidence_selection_history"
    ]
    assert kernel.state.followup_final_answer_packet_state == snapshot[
        "followup_final_answer_packet_state"
    ]
    assert kernel.state.followup_blocked_final_answer_packet_shell_state == snapshot[
        "followup_blocked_final_answer_packet_shell_state"
    ]
    assert kernel.state.projections == snapshot["projections"]
    assert kernel.state.action_statuses == snapshot["action_statuses"]
    assert kernel.state.stage_statuses == snapshot["stage_statuses"]
    assert kernel.state.reduced_action_ids == snapshot["reduced_action_ids"]
    assert kernel.state.observations == snapshot["observations"]
    assert kernel.state.next_observation_sequence == snapshot[
        "next_observation_sequence"
    ]


def snapshot_q1_boundary_state(kernel: Any) -> dict[str, Any]:
    return {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "followup_citation_eligibility_state": deepcopy(
            kernel.state.followup_citation_eligibility_state
        ),
        "followup_citation_eligibility_projection": deepcopy(
            kernel.state.followup_citation_eligibility_projection
        ),
        "followup_citation_eligibility_history": deepcopy(
            kernel.state.followup_citation_eligibility_history
        ),
        "followup_final_evidence_selection_state": deepcopy(
            kernel.state.followup_final_evidence_selection_state
        ),
        "followup_final_answer_packet_state": deepcopy(
            kernel.state.followup_final_answer_packet_state
        ),
        "followup_blocked_final_answer_packet_shell_state": deepcopy(
            kernel.state.followup_blocked_final_answer_packet_shell_state
        ),
        "projections": deepcopy(kernel.state.projections),
        "action_statuses": deepcopy(kernel.state.action_statuses),
        "stage_statuses": deepcopy(kernel.state.stage_statuses),
        "reduced_action_ids": deepcopy(kernel.state.reduced_action_ids),
        "observations": deepcopy(kernel.state.observations),
        "next_observation_sequence": kernel.state.next_observation_sequence,
    }


def assert_q1_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert kernel.state.final_answer_packet == snapshot["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == snapshot[
        "final_answer_authority_projection"
    ]
    assert kernel.state.followup_citation_eligibility_state == snapshot[
        "followup_citation_eligibility_state"
    ]
    assert kernel.state.followup_citation_eligibility_projection == snapshot[
        "followup_citation_eligibility_projection"
    ]
    assert kernel.state.followup_citation_eligibility_history == snapshot[
        "followup_citation_eligibility_history"
    ]
    assert kernel.state.followup_final_evidence_selection_state == snapshot[
        "followup_final_evidence_selection_state"
    ]
    assert kernel.state.followup_final_answer_packet_state == snapshot[
        "followup_final_answer_packet_state"
    ]
    assert kernel.state.followup_blocked_final_answer_packet_shell_state == snapshot[
        "followup_blocked_final_answer_packet_shell_state"
    ]
    assert kernel.state.projections == snapshot["projections"]
    assert kernel.state.action_statuses == snapshot["action_statuses"]
    assert kernel.state.stage_statuses == snapshot["stage_statuses"]
    assert kernel.state.reduced_action_ids == snapshot["reduced_action_ids"]
    assert kernel.state.observations == snapshot["observations"]
    assert kernel.state.next_observation_sequence == snapshot[
        "next_observation_sequence"
    ]


def snapshot_r1_boundary_state(kernel: Any) -> dict[str, Any]:
    return {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "followup_citation_source_handoff_state": deepcopy(
            kernel.state.followup_citation_source_handoff_state
        ),
        "followup_citation_source_handoff_projection": deepcopy(
            kernel.state.followup_citation_source_handoff_projection
        ),
        "followup_citation_source_handoff_history": deepcopy(
            kernel.state.followup_citation_source_handoff_history
        ),
        "followup_citation_eligibility_state": deepcopy(
            kernel.state.followup_citation_eligibility_state
        ),
        "followup_citation_eligibility_projection": deepcopy(
            kernel.state.followup_citation_eligibility_projection
        ),
        "followup_citation_eligibility_history": deepcopy(
            kernel.state.followup_citation_eligibility_history
        ),
        "projections": deepcopy(kernel.state.projections),
        "action_statuses": deepcopy(kernel.state.action_statuses),
        "stage_statuses": deepcopy(kernel.state.stage_statuses),
        "reduced_action_ids": deepcopy(kernel.state.reduced_action_ids),
        "observations": deepcopy(kernel.state.observations),
        "next_observation_sequence": kernel.state.next_observation_sequence,
    }


def assert_r1_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert kernel.state.final_answer_packet == snapshot["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == snapshot[
        "final_answer_authority_projection"
    ]
    assert kernel.state.followup_citation_source_handoff_state == snapshot[
        "followup_citation_source_handoff_state"
    ]
    assert kernel.state.followup_citation_source_handoff_projection == snapshot[
        "followup_citation_source_handoff_projection"
    ]
    assert kernel.state.followup_citation_source_handoff_history == snapshot[
        "followup_citation_source_handoff_history"
    ]
    assert kernel.state.followup_citation_eligibility_state == snapshot[
        "followup_citation_eligibility_state"
    ]
    assert kernel.state.followup_citation_eligibility_projection == snapshot[
        "followup_citation_eligibility_projection"
    ]
    assert kernel.state.followup_citation_eligibility_history == snapshot[
        "followup_citation_eligibility_history"
    ]
    assert kernel.state.projections == snapshot["projections"]
    assert kernel.state.action_statuses == snapshot["action_statuses"]
    assert kernel.state.stage_statuses == snapshot["stage_statuses"]
    assert kernel.state.reduced_action_ids == snapshot["reduced_action_ids"]
    assert kernel.state.observations == snapshot["observations"]
    assert kernel.state.next_observation_sequence == snapshot[
        "next_observation_sequence"
    ]


def snapshot_t1_boundary_state(kernel: Any) -> dict[str, Any]:
    return {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "followup_citation_rendering_state": deepcopy(
            kernel.state.followup_citation_rendering_state
        ),
        "followup_citation_rendering_projection": deepcopy(
            kernel.state.followup_citation_rendering_projection
        ),
        "followup_citation_rendering_history": deepcopy(
            kernel.state.followup_citation_rendering_history
        ),
        "followup_citation_source_handoff_state": deepcopy(
            kernel.state.followup_citation_source_handoff_state
        ),
        "followup_citation_source_handoff_projection": deepcopy(
            kernel.state.followup_citation_source_handoff_projection
        ),
        "followup_citation_source_handoff_history": deepcopy(
            kernel.state.followup_citation_source_handoff_history
        ),
        "followup_citation_eligibility_state": deepcopy(
            kernel.state.followup_citation_eligibility_state
        ),
        "followup_citation_eligibility_projection": deepcopy(
            kernel.state.followup_citation_eligibility_projection
        ),
        "followup_citation_eligibility_history": deepcopy(
            kernel.state.followup_citation_eligibility_history
        ),
        "projections": deepcopy(kernel.state.projections),
        "action_statuses": deepcopy(kernel.state.action_statuses),
        "stage_statuses": deepcopy(kernel.state.stage_statuses),
        "reduced_action_ids": deepcopy(kernel.state.reduced_action_ids),
        "observations": deepcopy(kernel.state.observations),
        "next_observation_sequence": kernel.state.next_observation_sequence,
    }


def assert_t1_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert kernel.state.final_answer_packet == snapshot["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == snapshot[
        "final_answer_authority_projection"
    ]
    assert kernel.state.followup_citation_rendering_state == snapshot[
        "followup_citation_rendering_state"
    ]
    assert kernel.state.followup_citation_rendering_projection == snapshot[
        "followup_citation_rendering_projection"
    ]
    assert kernel.state.followup_citation_rendering_history == snapshot[
        "followup_citation_rendering_history"
    ]
    assert kernel.state.followup_citation_source_handoff_state == snapshot[
        "followup_citation_source_handoff_state"
    ]
    assert kernel.state.followup_citation_source_handoff_projection == snapshot[
        "followup_citation_source_handoff_projection"
    ]
    assert kernel.state.followup_citation_source_handoff_history == snapshot[
        "followup_citation_source_handoff_history"
    ]
    assert kernel.state.followup_citation_eligibility_state == snapshot[
        "followup_citation_eligibility_state"
    ]
    assert kernel.state.followup_citation_eligibility_projection == snapshot[
        "followup_citation_eligibility_projection"
    ]
    assert kernel.state.followup_citation_eligibility_history == snapshot[
        "followup_citation_eligibility_history"
    ]
    assert kernel.state.projections == snapshot["projections"]
    assert kernel.state.action_statuses == snapshot["action_statuses"]
    assert kernel.state.stage_statuses == snapshot["stage_statuses"]
    assert kernel.state.reduced_action_ids == snapshot["reduced_action_ids"]
    assert kernel.state.observations == snapshot["observations"]
    assert kernel.state.next_observation_sequence == snapshot[
        "next_observation_sequence"
    ]


def snapshot_u1_boundary_state(kernel: Any) -> dict[str, Any]:
    return {
        "trace_projection": deepcopy(kernel.state.to_trace_projection().to_dict()),
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "followup_author_input_authority_state": deepcopy(
            kernel.state.followup_author_input_authority_state
        ),
        "followup_author_input_authority_projection": deepcopy(
            kernel.state.followup_author_input_authority_projection
        ),
        "followup_author_input_authority_history": deepcopy(
            kernel.state.followup_author_input_authority_history
        ),
        "followup_citation_rendering_state": deepcopy(
            kernel.state.followup_citation_rendering_state
        ),
        "followup_citation_rendering_projection": deepcopy(
            kernel.state.followup_citation_rendering_projection
        ),
        "followup_citation_rendering_history": deepcopy(
            kernel.state.followup_citation_rendering_history
        ),
        "followup_author_gate_state": deepcopy(kernel.state.followup_author_gate_state),
        "followup_author_observation_state": deepcopy(
            kernel.state.followup_author_observation_state
        ),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
        "projections": deepcopy(kernel.state.projections),
        "action_statuses": deepcopy(kernel.state.action_statuses),
        "stage_statuses": deepcopy(kernel.state.stage_statuses),
        "reduced_action_ids": deepcopy(kernel.state.reduced_action_ids),
        "observations": deepcopy(kernel.state.observations),
        "next_observation_sequence": kernel.state.next_observation_sequence,
    }


def assert_u1_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert kernel.state.to_trace_projection().to_dict() == snapshot["trace_projection"]
    assert kernel.state.final_answer_packet == snapshot["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == snapshot[
        "final_answer_authority_projection"
    ]
    assert kernel.state.followup_author_input_authority_state == snapshot[
        "followup_author_input_authority_state"
    ]
    assert kernel.state.followup_author_input_authority_projection == snapshot[
        "followup_author_input_authority_projection"
    ]
    assert kernel.state.followup_author_input_authority_history == snapshot[
        "followup_author_input_authority_history"
    ]
    assert kernel.state.followup_citation_rendering_state == snapshot[
        "followup_citation_rendering_state"
    ]
    assert kernel.state.followup_citation_rendering_projection == snapshot[
        "followup_citation_rendering_projection"
    ]
    assert kernel.state.followup_citation_rendering_history == snapshot[
        "followup_citation_rendering_history"
    ]
    assert kernel.state.followup_author_gate_state == snapshot[
        "followup_author_gate_state"
    ]
    assert kernel.state.followup_author_observation_state == snapshot[
        "followup_author_observation_state"
    ]
    assert kernel.state.author_observation == snapshot["author_observation"]
    assert kernel.state.final_answer_outcome == snapshot["final_answer_outcome"]
    assert kernel.state.projections == snapshot["projections"]
    assert kernel.state.action_statuses == snapshot["action_statuses"]
    assert kernel.state.stage_statuses == snapshot["stage_statuses"]
    assert kernel.state.reduced_action_ids == snapshot["reduced_action_ids"]
    assert kernel.state.observations == snapshot["observations"]
    assert kernel.state.next_observation_sequence == snapshot[
        "next_observation_sequence"
    ]


def snapshot_v1_boundary_state(kernel: Any) -> dict[str, Any]:
    snapshot = snapshot_u1_boundary_state(kernel)
    snapshot["followup_author_gate_projection"] = deepcopy(
        kernel.state.followup_author_gate_projection
    )
    snapshot["followup_author_gate_history"] = deepcopy(
        kernel.state.followup_author_gate_history
    )
    return snapshot


def assert_v1_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert_u1_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.followup_author_gate_projection == snapshot[
        "followup_author_gate_projection"
    ]
    assert kernel.state.followup_author_gate_history == snapshot[
        "followup_author_gate_history"
    ]


def snapshot_w_boundary_state(kernel: Any) -> dict[str, Any]:
    snapshot = snapshot_v1_boundary_state(kernel)
    snapshot["followup_author_execution_readiness_state"] = deepcopy(
        kernel.state.followup_author_execution_readiness_state
    )
    snapshot["followup_author_execution_readiness_projection"] = deepcopy(
        kernel.state.followup_author_execution_readiness_projection
    )
    snapshot["followup_author_execution_readiness_history"] = deepcopy(
        kernel.state.followup_author_execution_readiness_history
    )
    return snapshot


def assert_w_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert_v1_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.followup_author_execution_readiness_state == snapshot[
        "followup_author_execution_readiness_state"
    ]
    assert kernel.state.followup_author_execution_readiness_projection == snapshot[
        "followup_author_execution_readiness_projection"
    ]
    assert kernel.state.followup_author_execution_readiness_history == snapshot[
        "followup_author_execution_readiness_history"
    ]


def snapshot_x_boundary_state(kernel: Any) -> dict[str, Any]:
    snapshot = snapshot_w_boundary_state(kernel)
    snapshot["followup_author_input_materialization_state"] = deepcopy(
        kernel.state.followup_author_input_materialization_state
    )
    snapshot["followup_author_input_materialization_projection"] = deepcopy(
        kernel.state.followup_author_input_materialization_projection
    )
    snapshot["followup_author_input_materialization_history"] = deepcopy(
        kernel.state.followup_author_input_materialization_history
    )
    return snapshot


def assert_x_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert_w_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.followup_author_input_materialization_state == snapshot[
        "followup_author_input_materialization_state"
    ]
    assert kernel.state.followup_author_input_materialization_projection == snapshot[
        "followup_author_input_materialization_projection"
    ]
    assert kernel.state.followup_author_input_materialization_history == snapshot[
        "followup_author_input_materialization_history"
    ]


def snapshot_y_boundary_state(kernel: Any) -> dict[str, Any]:
    snapshot = snapshot_x_boundary_state(kernel)
    snapshot["followup_author_execution_activation_state"] = deepcopy(
        kernel.state.followup_author_execution_activation_state
    )
    snapshot["followup_author_execution_activation_projection"] = deepcopy(
        kernel.state.followup_author_execution_activation_projection
    )
    snapshot["followup_author_execution_activation_history"] = deepcopy(
        kernel.state.followup_author_execution_activation_history
    )
    return snapshot


def assert_y_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert_x_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.followup_author_execution_activation_state == snapshot[
        "followup_author_execution_activation_state"
    ]
    assert kernel.state.followup_author_execution_activation_projection == snapshot[
        "followup_author_execution_activation_projection"
    ]
    assert kernel.state.followup_author_execution_activation_history == snapshot[
        "followup_author_execution_activation_history"
    ]


def snapshot_z_boundary_state(kernel: Any) -> dict[str, Any]:
    snapshot = snapshot_y_boundary_state(kernel)
    snapshot["followup_author_prompt_assembly_manifest_state"] = deepcopy(
        kernel.state.followup_author_prompt_assembly_manifest_state
    )
    snapshot["followup_author_prompt_assembly_manifest_projection"] = deepcopy(
        kernel.state.followup_author_prompt_assembly_manifest_projection
    )
    snapshot["followup_author_prompt_assembly_manifest_history"] = deepcopy(
        kernel.state.followup_author_prompt_assembly_manifest_history
    )
    return snapshot


def assert_z_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert_y_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.followup_author_prompt_assembly_manifest_state == snapshot[
        "followup_author_prompt_assembly_manifest_state"
    ]
    assert kernel.state.followup_author_prompt_assembly_manifest_projection == snapshot[
        "followup_author_prompt_assembly_manifest_projection"
    ]
    assert kernel.state.followup_author_prompt_assembly_manifest_history == snapshot[
        "followup_author_prompt_assembly_manifest_history"
    ]


def snapshot_ac_boundary_state(kernel: Any) -> dict[str, Any]:
    snapshot = snapshot_z_boundary_state(kernel)
    snapshot["followup_author_payload_authority_state"] = deepcopy(
        kernel.state.followup_author_payload_authority_state
    )
    snapshot["followup_author_payload_authority_projection"] = deepcopy(
        kernel.state.followup_author_payload_authority_projection
    )
    snapshot["followup_author_payload_authority_history"] = deepcopy(
        kernel.state.followup_author_payload_authority_history
    )
    return snapshot


def assert_ac_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert_z_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.followup_author_payload_authority_state == snapshot[
        "followup_author_payload_authority_state"
    ]
    assert kernel.state.followup_author_payload_authority_projection == snapshot[
        "followup_author_payload_authority_projection"
    ]
    assert kernel.state.followup_author_payload_authority_history == snapshot[
        "followup_author_payload_authority_history"
    ]


def snapshot_ad_boundary_state(kernel: Any) -> dict[str, Any]:
    snapshot = snapshot_ac_boundary_state(kernel)
    snapshot["followup_author_payload_construction_state"] = deepcopy(
        kernel.state.followup_author_payload_construction_state
    )
    snapshot["followup_author_payload_construction_projection"] = deepcopy(
        kernel.state.followup_author_payload_construction_projection
    )
    snapshot["followup_author_payload_construction_history"] = deepcopy(
        kernel.state.followup_author_payload_construction_history
    )
    return snapshot


def assert_ad_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert_ac_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.followup_author_payload_construction_state == snapshot[
        "followup_author_payload_construction_state"
    ]
    assert kernel.state.followup_author_payload_construction_projection == snapshot[
        "followup_author_payload_construction_projection"
    ]
    assert kernel.state.followup_author_payload_construction_history == snapshot[
        "followup_author_payload_construction_history"
    ]


def snapshot_ae_boundary_state(kernel: Any) -> dict[str, Any]:
    snapshot = snapshot_ad_boundary_state(kernel)
    snapshot["followup_author_execution_from_ad_state"] = deepcopy(
        kernel.state.followup_author_execution_from_ad_state
    )
    snapshot["followup_author_execution_from_ad_projection"] = deepcopy(
        kernel.state.followup_author_execution_from_ad_projection
    )
    snapshot["followup_author_execution_from_ad_history"] = deepcopy(
        kernel.state.followup_author_execution_from_ad_history
    )
    snapshot["author_observation"] = deepcopy(kernel.state.author_observation)
    snapshot["final_answer_outcome"] = deepcopy(kernel.state.final_answer_outcome)
    return snapshot


def assert_ae_boundary_snapshot_unchanged(
    kernel: Any,
    snapshot: dict[str, Any],
) -> None:
    assert_ad_boundary_snapshot_unchanged(kernel, snapshot)
    assert kernel.state.followup_author_execution_from_ad_state == snapshot[
        "followup_author_execution_from_ad_state"
    ]
    assert kernel.state.followup_author_execution_from_ad_projection == snapshot[
        "followup_author_execution_from_ad_projection"
    ]
    assert kernel.state.followup_author_execution_from_ad_history == snapshot[
        "followup_author_execution_from_ad_history"
    ]
    assert kernel.state.author_observation == snapshot["author_observation"]
    assert kernel.state.final_answer_outcome == snapshot["final_answer_outcome"]


def assert_no_sensitive_payload(value: Any) -> None:
    markers = (
        "raw_page_text",
        "raw_prompt",
        "raw_provider_payload",
        "provider_payload",
        "private_log",
        "db_row",
        "secret",
        "full_trace",
        "cache",
    )

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                key_text = str(key).casefold()
                if any(marker in key_text for marker in markers):
                    assert child in (None, False, [], {}, (), "")
                    continue
                walk(child)
        elif isinstance(item, (list, tuple, set)):
            for child in item:
                walk(child)
        elif isinstance(item, str):
            text = item.casefold()
            assert not any(marker in text for marker in markers)

    walk(value)


__all__ = [
    "assert_no_sensitive_payload",
    "assert_o2_boundary_snapshot_unchanged",
    "assert_o2_closed_surfaces_unchanged",
    "assert_p1_boundary_snapshot_unchanged",
    "assert_q1_boundary_snapshot_unchanged",
    "assert_r1_boundary_snapshot_unchanged",
    "assert_t1_boundary_snapshot_unchanged",
    "assert_u1_boundary_snapshot_unchanged",
    "assert_v1_boundary_snapshot_unchanged",
    "assert_w_boundary_snapshot_unchanged",
    "assert_x_boundary_snapshot_unchanged",
    "assert_y_boundary_snapshot_unchanged",
    "assert_z_boundary_snapshot_unchanged",
    "assert_ac_boundary_snapshot_unchanged",
    "assert_ad_boundary_snapshot_unchanged",
    "assert_ae_boundary_snapshot_unchanged",
    "snapshot_o2_boundary_state",
    "snapshot_o2_closed_surfaces",
    "snapshot_p1_boundary_state",
    "snapshot_q1_boundary_state",
    "snapshot_r1_boundary_state",
    "snapshot_t1_boundary_state",
    "snapshot_u1_boundary_state",
    "snapshot_v1_boundary_state",
    "snapshot_w_boundary_state",
    "snapshot_x_boundary_state",
    "snapshot_y_boundary_state",
    "snapshot_z_boundary_state",
    "snapshot_ac_boundary_state",
    "snapshot_ad_boundary_state",
    "snapshot_ae_boundary_state",
]
