"""Focused owner proofs for PR #521 Case 5 artifact and action closure."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from core.analyst_query_resolution_proposal import (
    ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY,
    selected_proposals_for_role_artifact,
)
from core.multicomponent_graph_scheduling import LEASE_FAILED
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    MulticomponentRoleRuntimeError,
    execute_multicomponent_role_call,
    safe_packet_digest,
    validate_multicomponent_role_artifact,
)
from core.ordinary_multicomponent_synthesis_runtime import (
    record_analyst_query_resolution_candidates,
)
from core.run_kernel import (
    ActionType,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from tests.fixtures.searchos_analystos_offline_scenarios import (
    CASE_5,
    SCENARIO_BY_ID,
    run_offline_integration_scenario,
)
from tests.test_multicomponent_graph_scheduling_leases_01 import (
    _role_kwargs,
    _scheduler,
    _scheduler_kernel,
)


def _component_analyst_artifact(action) -> dict:
    core = {
        "schema_version": "multicomponent_semantic_role_artifact_v1",
        "role": ROLE_COMPONENT_ANALYST,
        "artifact_id": f"{ROLE_COMPONENT_ANALYST}:{action.action_id}",
        "run_id": action.run_id,
        "request_id": "artifact-custody-request",
        "input_packet_digest": action.inputs["input_packet_digest"],
        "logical_evaluation_key": action.inputs["logical_evaluation_key"],
        "logical_evaluations": 1,
        "physical_calls": 1,
        "authorized_action_ref": {
            "action_id": action.action_id,
            "stage": action.stage,
            "sequence": action.sequence,
            "observation_type": action.expected_observation_type.value,
        },
        "semantic_output": {
            "case_posture": "supported",
            "support_status": "supported",
            "claim_text": "Bounded fixture claim.",
            "evidence_analysis": "The bounded fixture evidence supports the claim.",
            "self_audit": "The case does not extend beyond its fixture evidence.",
            "caveats": [],
            "nonclaims": [],
            "contradictions": [],
            "blockers": [],
        },
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
    }
    return {**core, "artifact_digest": safe_packet_digest(core)}


def test_semantic_role_observation_defensively_preserves_nested_output() -> None:
    kernel = RunKernel.start(
        run_id="nested-role-observation-run",
        request_id="nested-role-observation-request",
    )
    action = kernel.authorize(
        stage="nested-role-observation",
        action_type=ActionType.MULTICOMPONENT_CROSS_ANALYST_EXECUTE,
        reason="prove_nested_role_artifact_custody",
        inputs={},
        expected_observation_type=(ObservationType.MULTICOMPONENT_CROSS_ANALYST_COMPLETED),
    )
    source = {
        "semantic_role_artifact": {
            "semantic_output": {
                "query_resolution_proposals": [
                    {
                        "current_dependency_component_refs": [
                            {},
                            {
                                "metadata": {
                                    "source_obligation_specification": {
                                        "candidate_id": "candidate:stable",
                                        "obligation_kind": "supporting_fact",
                                        "strictness": "required",
                                    }
                                }
                            },
                        ]
                    }
                ]
            }
        }
    }
    observation = Observation.from_action(
        action,
        observation_type=action.expected_observation_type,
        status=RunStageStatus.COMPLETED,
        payload=source,
    )
    nested = observation.payload["semantic_role_artifact"]["semantic_output"]["query_resolution_proposals"][0][
        "current_dependency_component_refs"
    ][1]["metadata"]["source_obligation_specification"]
    assert nested == {
        "candidate_id": "candidate:stable",
        "obligation_kind": "supporting_fact",
        "strictness": "required",
    }
    source["semantic_role_artifact"]["semantic_output"]["query_resolution_proposals"][0][
        "current_dependency_component_refs"
    ][1]["metadata"]["source_obligation_specification"]["candidate_id"] = "candidate:mutated"
    assert nested["candidate_id"] == "candidate:stable"


def test_invalid_role_artifact_reduction_is_atomic_and_blocks_n_plus_one() -> None:
    kernel = RunKernel.start(
        run_id="artifact-custody-run",
        request_id="artifact-custody-request",
    )
    action = kernel.authorize_multicomponent_role_call(
        role=ROLE_COMPONENT_ANALYST,
        input_packet_digest="1" * 64,
        logical_evaluation_key="artifact-custody",
    )
    artifact = _component_analyst_artifact(action)
    validate_multicomponent_role_artifact(
        artifact,
        expected_role=ROLE_COMPONENT_ANALYST,
    )
    artifact["semantic_output"]["claim_text"] = "Digest drift."
    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="semantic role artifact digest mismatch",
    ):
        kernel.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"semantic_role_artifact": artifact},
            )
        )
    assert action.action_id not in kernel.state.reduced_action_ids
    assert kernel.state.next_observation_sequence == action.sequence

    later = kernel.authorize(
        stage="later-sequence",
        action_type=ActionType.ROUTE_REQUEST,
        reason="prove_n_plus_one_is_blocked",
        inputs={},
        expected_observation_type=ObservationType.ROUTE_RESULT,
    )
    with pytest.raises(
        RunKernelTransitionError,
        match="observation reduced out of order",
    ):
        kernel.reduce(
            Observation.from_action(
                later,
                observation_type=later.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
    assert later.action_id not in kernel.state.reduced_action_ids


def test_failed_role_observation_reduction_closes_current_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    original_reduce = kernel.reduce
    forced = False

    def fail_completed_role_observation_once(observation):
        nonlocal forced
        if (
            not forced
            and observation.status is RunStageStatus.COMPLETED
            and observation.observation_type is ObservationType.MULTICOMPONENT_COMPONENT_ANALYST_COMPLETED
        ):
            forced = True
            raise MulticomponentRoleRuntimeError("forced semantic role observation reduction failure")
        return original_reduce(observation)

    monkeypatch.setattr(
        kernel,
        "reduce",
        fail_completed_role_observation_once,
    )
    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="forced semantic role observation reduction failure",
    ):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=work["role"],
            input_packet=packets[str(work["component_id"])],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id=lease["lease_id"],
            **_role_kwargs(
                ask_model=lambda *_args, **_kwargs: json.dumps(
                    {
                        "case_posture": "supported",
                        "claim_text": "A bounded claim.",
                        "evidence_analysis": "The bounded evidence directly supports the claim.",
                        "self_audit": "The claim stays within the bounded evidence.",
                    }
                )
            ),
        )

    role_action = next(
        item
        for item in kernel.state.issued_actions.values()
        if item.action_type is ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE
    )
    observations = [item for item in kernel.state.observations if item.action_id == role_action.action_id]
    assert role_action.action_id in kernel.state.reduced_action_ids
    assert len(observations) == 1
    assert observations[0].status is RunStageStatus.FAILED
    assert kernel.state.next_observation_sequence == role_action.sequence + 1
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_FAILED


def test_case5_proposal_recording_and_replay_do_not_mutate_role_artifact(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution = run_offline_integration_scenario(
        SCENARIO_BY_ID[CASE_5],
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    artifacts = [
        dict(item.payload["semantic_role_artifact"])
        for item in execution.kernel.state.observations
        if isinstance(item.payload.get("semantic_role_artifact"), dict)
        and item.payload["semantic_role_artifact"].get("role") == ROLE_CROSS_COMPONENT_ANALYST
        and item.payload["semantic_role_artifact"].get("semantic_output", {}).get("query_resolution_proposals")
    ]
    artifact = max(
        artifacts,
        key=lambda item: item["authorized_action_ref"]["sequence"],
    )
    before = deepcopy(artifact)
    first_replay = validate_multicomponent_role_artifact(
        artifact,
        expected_role=ROLE_CROSS_COMPONENT_ANALYST,
    )
    second_replay = validate_multicomponent_role_artifact(
        first_replay,
        expected_role=ROLE_CROSS_COMPONENT_ANALYST,
    )
    assert first_replay == second_replay == before

    registry = deepcopy(execution.kernel.state.projections[ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY])
    selected = selected_proposals_for_role_artifact(
        registry=registry,
        role_artifact=artifact,
        classification="searched_premise",
    )
    registry_before = deepcopy(registry)
    selected[0]["variant_payload"]["local_mutation_probe"] = True
    assert registry == registry_before

    record_analyst_query_resolution_candidates(
        run_kernel=execution.kernel,
        artifact=artifact,
    )
    assert artifact == before
