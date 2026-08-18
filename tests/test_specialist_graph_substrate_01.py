"""PRODUCT-PATH-REGRESSION: generic Specialist work in ordinary run_pipeline.

Proof class: offline_product_path_proof.
Validation bucket: phase_focus.
Surface guarded: generic proposal, registry, policy, Scheduler V3, work/result,
D-prime consumption, and exact Scrutineer leaf remediation contracts.
Runtime consumer: core.ordinary_multicomponent_synthesis_runtime.
Expected cost: about 12 seconds offline.
Promotion posture: remain phase_focus until a smaller broad sentinel is named.
Why not fast_pr: the detailed origin and rejection matrix is phase-specific.
The injected capabilities are deterministic test fixtures; they are not
production features and do not prove live model, provider, retrieval, or answer
quality.
"""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import core.multicomponent_graph_scheduling as scheduling
import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.multicomponent_graph_scheduling import (
    LEASE_BLOCKED,
    LEASE_CANCELLED,
    LEASE_COMPLETED,
    LEASE_CONTESTED,
    LEASE_FAILED,
    LEASE_STALE,
    MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SCHEMA_VERSION,
    MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SET_SCHEMA_VERSION,
    MULTICOMPONENT_SCHEDULER_STAGE,
    MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION,
    MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION,
    WORK_KIND_SPECIALIST_CAPABILITY,
    cancel_batch,
    dispatch_batch,
    grant_next_batch,
    initialize_scheduler_v3_state,
    settle_specialist_lease,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_ANALYST_RESUME,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    role_artifact_ref,
)
from core.protocols import NullStatusWriter
from core.run_kernel import RunKernel, RunKernelTransitionError
from core.specialist_graph_runtime import (
    AVAILABILITY_BLOCKED,
    AVAILABILITY_BUDGET,
    AVAILABILITY_CAPABILITY,
    AVAILABILITY_CONTESTED,
    AVAILABILITY_FAILED,
    AVAILABILITY_POLICY,
    AVAILABILITY_RESULT,
    AVAILABILITY_TARGET,
    EXECUTION_BLOCKED,
    EXECUTION_CONTESTED,
    EXECUTION_FAILED,
    PROPOSAL_ACCEPTED,
    PROPOSAL_DENIED_POLICY,
    PROPOSAL_REJECTED,
    PROPOSAL_UNSUPPORTED_TARGET,
    SPECIALIST_NEED_SCHEMA_VERSION,
    SPECIALIST_WORK_PLANE_STAGE,
    SpecialistCapabilityRegistry,
    SpecialistCapabilitySpec,
    SpecialistExecutionPolicy,
    SpecialistGraphRuntimeError,
    bind_specialist_need_proposal,
    closed_specialist_execution_policy,
    closed_specialist_registry,
    normalize_specialist_need_proposal,
    specialist_digest,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)
from tests.test_multicomponent_ordinary_end_to_end_synthesis_01 import (
    NORTHSTAR_REPORT,
    NorthstarHarness,
)

INPUT_SCHEMA = "generic.specialist.input.v1"
OUTPUT_SCHEMA = "generic.specialist.output.v1"
REQUIREMENT = "generic_bounded_transform"


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class SpecialistNorthstarHarness(NorthstarHarness):
    proposal_origin = "component"
    capability_hint = "test.specialist.alpha"
    capability_requirement = REQUIREMENT
    posture = "optional"
    synthesis_target_kind = "synthesis"
    synthesis_target_key = "S"
    scrutineer_target_kind = "synthesis"
    scrutineer_target_key = "S"
    scrutineer_challenge_target_key = "synthesis_02"
    component_proposal_all = False
    component_target_override: str | None = None

    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.specialist_dprime_inputs: list[dict[str, Any]] = []
        self.specialist_analyst_resume_inputs: list[dict[str, Any]] = []
        self.all_dprime_inputs: list[dict[str, Any]] = []
        self.scrutineer_calls = 0

    @staticmethod
    def _proposal(*, target_kind: str, target_key: str, hint: str, posture: str, requirement: str) -> dict[str, Any]:
        return {
            "schema_version": SPECIALIST_NEED_SCHEMA_VERSION,
            "local_need_id": "need-one",
            "capability_requirement": requirement,
            "candidate_capability_hint": hint,
            "bounded_question": "Apply the bounded generic transformation.",
            "target": {"target_kind": target_kind, "target_key": target_key},
            "posture": posture,
            "input_schema_ref": INPUT_SCHEMA,
            "expected_output_schema_ref": OUTPUT_SCHEMA,
            "input_artifact_refs": [],
            "assumptions": ["Fixture-only deterministic capability."],
            "caveats": [],
            "nonclaims": ["No product Specialist is activated."],
            "advisory_budget_posture": "one unit",
            "recursion_depth": 0,
            "specialist_parent_ref": None,
        }

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt not in ROLE_SYSTEM_PROMPTS.values():
            return super().ask_model(prompt, system_prompt, **kwargs)
        payload = json.loads(prompt)
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST_RESUME]:
            self.specialist_analyst_resume_inputs.append(deepcopy(payload))
        if system_prompt in {
            ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_DPRIME],
            ROLE_SYSTEM_PROMPTS[ROLE_SYNTHESIS_DPRIME],
        }:
            self.all_dprime_inputs.append(deepcopy(payload))
            if payload.get("specialist_need_handoff"):
                self.specialist_dprime_inputs.append(deepcopy(payload))
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER]:
            self.scrutineer_calls += 1
            if self.proposal_origin == "scrutineer" and self.scrutineer_calls == 1:
                return json.dumps(
                    {
                        "challenge_status": "challenged",
                        "reasons": ["The exact leaf needs bounded remediation."],
                        "challenge_targets": [
                            {
                                "target_kind": self.scrutineer_target_kind,
                                "target_key": self.scrutineer_challenge_target_key,
                            }
                        ],
                        "caveats": [],
                        "nonclaims": [],
                        "specialist_need_proposal": self._proposal(
                            target_kind=self.scrutineer_target_kind,
                            target_key=self.scrutineer_target_key,
                            hint=self.capability_hint,
                            posture=self.posture,
                            requirement=self.capability_requirement,
                        ),
                    }
                )
        raw = super().ask_model(prompt, system_prompt, **kwargs)
        output = json.loads(raw)
        if (
            self.proposal_origin == "component"
            and system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]
            and (
                self.component_proposal_all
                or "base rebate"
                in str(
                    payload.get("component_ref", {}).get("user_facing_question")
                    or ""
                ).casefold()
            )
        ):
            output["specialist_need_proposal"] = self._proposal(
                target_kind="component",
                target_key=(
                    self.component_target_override
                    or str(payload["component_ref"]["component_id"])
                ),
                hint=self.capability_hint,
                posture=self.posture,
                requirement=self.capability_requirement,
            )
        if (
            self.proposal_origin == "synthesis"
            and system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
        ):
            output["specialist_need_proposal"] = self._proposal(
                target_kind=self.synthesis_target_kind,
                target_key=self.synthesis_target_key,
                hint=self.capability_hint,
                posture=self.posture,
                requirement=self.capability_requirement,
            )
        return json.dumps(output)


def _registry(
    calls: list[dict[str, Any]], *, capability_ids: tuple[str, ...] = ("test.specialist.alpha", "test.specialist.beta")
) -> SpecialistCapabilityRegistry:
    def adapter(inputs: dict[str, Any]) -> dict[str, Any]:
        calls.append(
            {
                "thread_id": threading.get_ident(),
                "inputs": deepcopy(inputs),
            }
        )
        assert "run_kernel" not in inputs
        assert "provider" not in inputs
        assert "model" not in inputs
        assert "search" not in inputs
        assert "retrieval" not in inputs
        return {
            "bounded_result": {"fixture_transform": "complete"},
            "assumptions": ["Deterministic fixture."],
            "caveats": [],
            "blockers": [],
            "confidence_posture": "deterministic",
            "execution_posture": "completed",
        }

    return SpecialistCapabilityRegistry(
        tuple(
            SpecialistCapabilitySpec(
                capability_id=capability_id,
                version="1.0.0",
                capability_requirement=REQUIREMENT,
                supported_target_kinds=("component", "synthesis"),
                input_schema_ref=INPUT_SCHEMA,
                output_schema_ref=OUTPUT_SCHEMA,
                adapter=adapter,
            )
            for capability_id in capability_ids
        )
    )


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    harness: SpecialistNorthstarHarness,
    registry: SpecialistCapabilityRegistry | None,
    policy: SpecialistExecutionPolicy | None,
) -> tuple[Any, Any, dict[str, Any]]:
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    deps = harness.deps()
    deps.specialist_capability_registry = registry
    deps.specialist_execution_policy = policy
    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-13",
            session_id=f"specialist-session:{harness.proposal_origin}",
            run_id=f"specialist-run:{harness.proposal_origin}",
        ),
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )
    return outcome, captured["semantic_run_kernel"], captured


def _run_through_analyst_consumer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    forgery: str | None = None,
) -> tuple[Any, RunKernel, Any]:
    original_consume = RunKernel.consume_specialist_handoff_by_analyst_case

    def consume_then_stop(
        self: RunKernel,
        *,
        handoff_id: str,
        analyst_case_artifact_ref: dict[str, Any],
    ) -> dict[str, Any]:
        artifact_ref = deepcopy(analyst_case_artifact_ref)
        if forgery == "digest":
            artifact_ref["artifact_digest"] = "0" * 64
        elif forgery == "wrong_role":
            handoff = next(
                dict(item)
                for item in self.state.projections[SPECIALIST_WORK_PLANE_STAGE][
                    "need_handoffs"
                ]
                if dict(item).get("handoff_id") == handoff_id
            )
            target_key = str(
                dict(handoff["canonical_target_ref"]).get("target_key") or ""
            )
            artifact_ref = role_artifact_ref(
                self.state.projections[
                    f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{target_key}"
                ]
            )
        result = original_consume(
            self,
            handoff_id=handoff_id,
            analyst_case_artifact_ref=artifact_ref,
        )
        if forgery is None:
            raise RuntimeError("expected exact Analyst-resume consumption capture")
        return result

    monkeypatch.setattr(
        RunKernel,
        "consume_specialist_handoff_by_analyst_case",
        consume_then_stop,
    )
    harness = SpecialistNorthstarHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    deps = harness.deps()
    deps.specialist_capability_registry = _registry([])
    deps.specialist_execution_policy = SpecialistExecutionPolicy(
        enabled_capability_ids=("test.specialist.alpha",),
        specialist_work_item_limit=1,
    )
    expected_error = RuntimeError if forgery is None else RunKernelTransitionError
    with pytest.raises(expected_error):
        orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-07-13",
                session_id="specialist-consumer-session",
                run_id="specialist-consumer-run",
            ),
            deps,
            NullStatusWriter(),
            CostAccumulator(),
        )
    kernel = captured["semantic_run_kernel"]
    handoff = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE][
        "need_handoffs"
    ][0]
    assert handoff["validator_consumption"] == (
        "consumed_by_component_analyst"
        if forgery is None
        else "pending_validator_consumption"
    )
    outcome = SimpleNamespace(report="")
    return outcome, kernel, original_consume


def test_no_need_ordinary_run_preserves_scheduler_v2_and_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = NorthstarHarness(tmp_path)
    captured = install_handoff_capture(monkeypatch, capture_stages=(HANDOFF_SEMANTIC,))
    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-13",
            session_id="specialist-no-need-session",
            run_id="specialist-no-need-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    kernel = captured["semantic_run_kernel"]
    assert outcome.report == NORTHSTAR_REPORT
    assert kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE][
        "schema_version"
    ] == MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION
    assert SPECIALIST_WORK_PLANE_STAGE not in kernel.state.projections


def test_enabled_specialist_lane_without_proposal_omits_handoff_from_exact_packets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = SpecialistNorthstarHarness(tmp_path)
    harness.proposal_origin = "none"
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry([]),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert outcome.report == NORTHSTAR_REPORT
    assert plane["proposal_count"] == plane["need_handoff_count"] == 0
    assert harness.all_dprime_inputs
    assert all(
        "specialist_need_handoff" not in packet
        and "specialist_result_inputs" not in packet
        for packet in harness.all_dprime_inputs
    )


def test_component_origin_runs_through_v3_registry_and_analyst_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    main_thread = threading.get_ident()
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    assert outcome.report == NORTHSTAR_REPORT
    assert scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION
    assert scheduler["specialist_compatibility_pool"] == {
        "schema_version": "specialist_budget_state_v1",
        "specialist_work_item_limit": 1,
        "specialist_total": 1,
        "specialist_remaining": 0,
        "specialist_reserved": 0,
        "specialist_spent": 1,
        "specialist_returned": 0,
    }
    assert len(calls) == 1 and calls[0]["thread_id"] == main_thread
    assert (
        plane["proposal_count"]
        == plane["work_node_count"]
        == plane["result_artifact_count"]
        == 1
    )
    assert (
        plane["proposal_disposition_count"] == plane["need_handoff_count"] == 1
    )
    assert (
        plane["proposal_dispositions"][0]["execution_availability_posture"]
        == AVAILABILITY_RESULT
    )
    assert (
        plane["proposal_dispositions"][0]["proposal_ref"]["proposal_digest"]
        == plane["proposals"][0]["proposal_digest"]
    )
    assert (
        plane["result_artifacts"][0]["validator_consumption"]
        == "consumed_by_component_analyst"
    )
    assert (
        harness.specialist_analyst_resume_inputs[0]["specialist_need_handoff"][
            "namespace"
        ]
        == "specialist_need_handoff"
    )
    assert scheduler["compatibility_envelope"]["total_units"] == 24
    assert not any(
        item["system_prompt"] == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_DPRIME]
        for item in harness.role_input_packets
    )
    assert any(
        item["system_prompt"] == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST_RESUME]
        for item in harness.role_input_packets
    )
    assert plane["provider_request_attempt_count"] == plane["model_call_count"] == 0
    assert plane["token_usage"] == plane["model_cost"] == 0
    assert plane["maximum_observed_in_flight"] == 1
    result = plane["result_artifacts"][0]
    assert (
        specialist_digest(calls[0]["inputs"])
        == plane["work_nodes"][0]["bounded_input_digest"]
        == result["bounded_input_digest"]
    )
    for authority in (
        "component_admission_authority",
        "synthesis_admission_authority",
        "semantic_observation_authority",
        "component_coverage_authority",
        "sufficiency_authority",
        "final_answer_packet_authority",
        "author_authority",
        "citation_authority",
        "source_obligation_authority",
    ):
        assert result[authority] is False
    retained = json.dumps(plane, sort_keys=True).casefold()
    for forbidden in (
        "raw_prompt",
        "raw_model_response",
        "raw_provider_payload",
        "database_row",
        "private_log",
        "full_trace",
    ):
        assert forbidden not in retained


def test_synthesis_origin_uses_second_capability_without_driver_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    harness.proposal_origin = "synthesis"
    harness.capability_hint = "test.specialist.alpha"
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.beta",),
            specialist_work_item_limit=1,
        ),
    )
    result = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE][
        "result_artifacts"
    ][0]
    assert outcome.report == NORTHSTAR_REPORT
    assert result["capability_id"] == "test.specialist.beta"
    assert result["validator_consumption"] == "consumed_by_synthesis_dprime"
    assert len(calls) == 1
    assert (
        harness.specialist_dprime_inputs[0]["nominated_synthesis"][
            "synthesis_key"
        ]
        == "S"
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert (
        specialist_digest(calls[0]["inputs"])
        == plane["work_nodes"][0]["bounded_input_digest"]
        == result["bounded_input_digest"]
    )


def test_transient_component_packet_sentinel_reaches_only_adapter_local_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    sentinel_url = "https://sentinel.invalid/specialist-transient-only"
    sentinel_evidence = "SENTINEL_EVIDENCE_" + ("x" * 6000)
    original = scheduling.reconstruct_specialist_bounded_input

    def with_sentinel(
        *, state: Any, proposal: dict[str, Any]
    ) -> dict[str, Any]:
        authority = original(state=state, proposal=proposal)
        packet = deepcopy(authority["transient_bounded_input"])
        packet["sentinel_source_url"] = sentinel_url
        packet["sentinel_evidence_text"] = sentinel_evidence
        authority["transient_bounded_input"] = packet
        authority["bounded_input_digest"] = specialist_digest(packet)
        return authority

    monkeypatch.setattr(
        scheduling, "reconstruct_specialist_bounded_input", with_sentinel
    )
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    assert outcome.report == NORTHSTAR_REPORT
    assert calls[0]["inputs"]["sentinel_source_url"] == sentinel_url
    assert calls[0]["inputs"]["sentinel_evidence_text"] == sentinel_evidence
    retained = json.dumps(
        {
            "projections": kernel.state.projections,
            "actions": [
                action.to_dict()
                for action in kernel.state.issued_actions.values()
            ],
        },
        sort_keys=True,
    )
    assert sentinel_url not in retained
    assert sentinel_evidence not in retained
    work = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]["work_nodes"][
        0
    ]
    assert "bounded_inputs" not in work
    assert set(key for key in work if key.startswith("bounded_input_")) == {
        "bounded_input_digest",
        "bounded_input_schema_ref",
        "bounded_input_lineage_refs",
        "bounded_input_reconstruction_ref",
    }


def test_changed_reconstruction_cancels_once_before_adapter_and_refunds_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    reconstruction_calls = 0

    def change_after_authorization(*, state: Any, work: dict[str, Any]) -> dict[str, Any]:
        nonlocal reconstruction_calls
        del state, work
        reconstruction_calls += 1
        raise scheduling.MulticomponentGraphSchedulingError(
            "authorized Specialist input changed before dispatch"
        )

    monkeypatch.setattr(
        scheduling,
        "reconstruct_specialist_input_for_work",
        change_after_authorization,
    )
    captured = install_handoff_capture(
        monkeypatch, capture_stages=(HANDOFF_SEMANTIC,)
    )
    deps = harness.deps()
    deps.specialist_capability_registry = _registry(calls)
    deps.specialist_execution_policy = SpecialistExecutionPolicy(
        enabled_capability_ids=("test.specialist.alpha",),
        specialist_work_item_limit=1,
    )
    try:
        orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-07-13",
                session_id="specialist-changed-packet-session",
                run_id="specialist-changed-packet-run",
            ),
            deps,
            NullStatusWriter(),
            CostAccumulator(),
        )
    except Exception:
        pass
    kernel = captured["semantic_run_kernel"]
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    pool = scheduler["specialist_compatibility_pool"]
    specialist_leases = [
        item
        for item in scheduler["lease_history"]
        if (item.get("work") or {}).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
    ]
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert reconstruction_calls == 1
    assert calls == []
    assert [item["status"] for item in specialist_leases] == [LEASE_CANCELLED]
    assert pool["specialist_remaining"] == pool["specialist_total"] == 1
    assert pool["specialist_reserved"] == pool["specialist_spent"] == 0
    assert pool["specialist_returned"] == 1
    assert plane["result_artifact_count"] == 0
    assert plane["proposal_dispositions"][0][
        "execution_availability_posture"
    ] == AVAILABILITY_FAILED
    assert plane["proposal_dispositions"][0]["terminal_nonexecution_reason"] == (
        "input_reconstruction_failed"
    )
    assert not any(
        action.action_type.value == "specialist_capability_execute"
        for action in kernel.state.issued_actions.values()
    )


def test_required_reconstruction_failure_handoffs_once_then_blocks_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    harness.posture = "required"
    reconstruction_calls = 0

    def fail_reconstruction(*, state: Any, work: dict[str, Any]) -> dict[str, Any]:
        nonlocal reconstruction_calls
        del state, work
        reconstruction_calls += 1
        raise scheduling.MulticomponentGraphSchedulingError(
            "required Specialist input changed before dispatch"
        )

    monkeypatch.setattr(
        scheduling,
        "reconstruct_specialist_input_for_work",
        fail_reconstruction,
    )
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    pool = scheduler["specialist_compatibility_pool"]
    specialist_leases = [
        item
        for item in scheduler["lease_history"]
        if (item.get("work") or {}).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
    ]
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    disposition = plane["proposal_dispositions"][0]
    handoff = plane["need_handoffs"][0]
    blocked_transitions = [
        item
        for item in scheduler["transition_history"]
        if item.get("transition") == "blocked_required_specialist_work"
    ]

    assert outcome.report != NORTHSTAR_REPORT
    assert reconstruction_calls == 1
    assert calls == []
    assert [item["status"] for item in specialist_leases] == [LEASE_CANCELLED]
    assert pool["specialist_remaining"] == pool["specialist_total"] == 1
    assert pool["specialist_reserved"] == pool["specialist_spent"] == 0
    assert pool["specialist_returned"] == 1
    assert scheduler["status"] == "blocked_required_specialist_work"
    assert scheduler["terminal_posture"] == "blocked_required_specialist_work"
    assert len(blocked_transitions) == 1
    assert scheduler["failed_required_work_ref"]["nonexecution_reason"] == (
        "input_reconstruction_failed"
    )
    assert plane["result_artifact_count"] == 0
    assert plane["proposal_disposition_count"] == plane["need_handoff_count"] == 1
    assert disposition["execution_availability_posture"] == AVAILABILITY_FAILED
    assert disposition["terminal_nonexecution_reason"] == (
        "input_reconstruction_failed"
    )
    assert disposition["result_ref"] == {}
    assert disposition["validator_consumption"] == "pending_validator_consumption"
    assert handoff["availability_posture"] == AVAILABILITY_FAILED
    assert handoff["nonexecution_reason"] == "input_reconstruction_failed"
    assert handoff["result"] == {}
    assert handoff["validator_consumption"] == "pending_validator_consumption"
    assert not any(
        action.action_type.value == "specialist_capability_execute"
        for action in kernel.state.issued_actions.values()
    )


def test_runkernel_reproves_exact_analyst_resume_consumption_and_rejects_double_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _outcome, kernel, consume = _run_through_analyst_consumer(
        tmp_path, monkeypatch
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    handoff = plane["need_handoffs"][0]
    target_key = handoff["canonical_target_ref"]["target_key"]
    artifact = kernel.state.projections[
        f"multicomponent_role:{ROLE_COMPONENT_ANALYST_RESUME}:{target_key}"
    ]
    consumed = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert consumed["need_handoffs"][0]["validator_consumption"] == (
        "consumed_by_component_analyst"
    )
    consumption_action = next(
        action
        for action in reversed(tuple(kernel.state.issued_actions.values()))
        if action.action_type.value == "specialist_validator_consume"
    )
    assert "route" not in consumption_action.inputs
    assert consumption_action.inputs["validator_route"] == "component_analyst"
    assert consumption_action.inputs["validator_artifact_ref"] == role_artifact_ref(artifact)
    with pytest.raises(RunKernelTransitionError):
        consume(
            kernel,
            handoff_id=handoff["handoff_id"],
            analyst_case_artifact_ref=role_artifact_ref(artifact),
        )


@pytest.mark.parametrize("forgery", ["digest", "wrong_role"])
def test_runkernel_rejects_forged_or_wrong_role_analyst_handoff_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    _outcome, kernel, _consume = _run_through_analyst_consumer(
        tmp_path, monkeypatch, forgery=forgery
    )
    handoff = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE][
        "need_handoffs"
    ][0]
    assert handoff["validator_consumption"] == "pending_validator_consumption"


def test_cross_component_unknown_target_is_typed_rejected_and_optional(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    harness.proposal_origin = "synthesis"
    harness.synthesis_target_key = "missing-synthesis"
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert outcome.report == NORTHSTAR_REPORT
    assert plane["proposals"] == []
    assert plane["proposal_dispositions"] == []
    assert plane["need_handoffs"] == []
    assert plane["proposal_rejections"][0]["rejection_category"] == (
        "proposal_target_mismatch"
    )
    assert calls == []


def test_scrutineer_exact_leaf_remediation_revalidates_and_rescrutinizes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    harness.proposal_origin = "scrutineer"
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    result = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE][
        "result_artifacts"
    ][0]
    assert outcome.report == NORTHSTAR_REPORT
    assert harness.scrutineer_calls == 2
    assert result["validator_consumption"] == "consumed_by_synthesis_dprime"
    assert graph["scrutineer_status"] == "passed"
    assert graph["graph_status"] == "ready"
    assert any(
        item.get("specialist_result_ref", {}).get("result_id") == result["result_id"]
        for item in graph["synthesis_nodes"]
        if item["synthesis_key"] == "S"
    )


@pytest.mark.parametrize("target_kind", ["component", "edge", "subgraph", "graph", "whole_case"])
def test_scrutineer_nonleaf_targets_are_retained_and_typed_rejected(
    target_kind: str,
) -> None:
    calls: list[dict[str, Any]] = []
    proposal = SpecialistNorthstarHarness._proposal(
        target_kind=target_kind,
        target_key="target-one",
        hint="test.specialist.alpha",
        posture="optional",
        requirement=REQUIREMENT,
    )
    bound = bind_specialist_need_proposal(
        run_id="run-one",
        request_id="request-one",
        origin_role="scrutineer",
        origin_action_ref={"action_id": "action-one"},
        origin_artifact_ref={"artifact_id": "artifact-one"},
        proposal=proposal,
        canonical_target_ref={
            "target_kind": target_kind,
            "target_key": "target-one",
            "target_revision": 1,
        },
        accepted_contract_ref={"accepted_contract_digest": "contract-one"},
        graph_ref={"graph_digest": "graph-one"},
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
        scrutineer_leaf_target_authorized=False,
    )
    assert bound["proposal_authority"] == PROPOSAL_UNSUPPORTED_TARGET
    assert bound["rejection_reason"] == "not_authorized_s0_target_requires_graph_invalidation"
    assert calls == []


def test_registry_resolution_ignores_hint_and_rejects_unknown_or_incompatible() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(calls)
    policy = SpecialistExecutionPolicy(
        enabled_capability_ids=("test.specialist.beta",),
        specialist_work_item_limit=1,
    )
    proposal = SpecialistNorthstarHarness._proposal(
        target_kind="component",
        target_key="component-one",
        hint="test.specialist.alpha",
        posture="optional",
        requirement=REQUIREMENT,
    )
    common = {
        "run_id": "run-one",
        "request_id": "request-one",
        "origin_role": "component_analyst",
        "origin_action_ref": {"action_id": "action-one"},
        "origin_artifact_ref": {"artifact_id": "artifact-one"},
        "canonical_target_ref": {
            "target_kind": "component",
            "target_key": "component-one",
            "target_revision": 1,
        },
        "accepted_contract_ref": {"accepted_contract_digest": "contract-one"},
        "graph_ref": {},
        "registry": registry,
        "policy": policy,
    }
    accepted = bind_specialist_need_proposal(proposal=proposal, **common)
    assert accepted["proposal_authority"] == PROPOSAL_ACCEPTED
    assert accepted["capability_descriptor"]["capability_id"] == "test.specialist.beta"
    unknown = deepcopy(proposal)
    unknown["capability_requirement"] = "unknown_requirement"
    rejected = bind_specialist_need_proposal(proposal=unknown, **common)
    assert rejected["proposal_authority"] == PROPOSAL_REJECTED
    assert rejected["rejection_reason"] == "unknown_or_incompatible_specialist_capability"
    incompatible = deepcopy(proposal)
    incompatible["expected_output_schema_ref"] = "wrong.schema"
    assert bind_specialist_need_proposal(proposal=incompatible, **common)[
        "proposal_authority"
    ] == PROPOSAL_REJECTED


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_schema",
        "stale_schema",
        "non_string_schema",
        "unknown_field",
        "unknown_target_field",
        "top_level_target_aliases",
        "forbidden_nested_authority",
        "forbidden_raw_material",
        "missing_recursion_depth",
        "missing_specialist_parent_ref",
        "missing_posture",
    ),
)
def test_generic_proposal_candidate_is_not_softened_into_validity(
    mutation: str,
) -> None:
    proposal = SpecialistNorthstarHarness._proposal(
        target_kind="component",
        target_key="component-one",
        hint="test.specialist.alpha",
        posture="optional",
        requirement=REQUIREMENT,
    )
    if mutation == "missing_schema":
        proposal.pop("schema_version")
    elif mutation == "stale_schema":
        proposal["schema_version"] = "specialist_need_proposal_v0"
    elif mutation == "non_string_schema":
        proposal["schema_version"] = 1
    elif mutation == "unknown_field":
        proposal["unknown_proposal_field"] = "must not be discarded"
    elif mutation == "unknown_target_field":
        proposal["target"]["target_revision"] = "1"
    elif mutation == "top_level_target_aliases":
        proposal["target_kind"] = proposal["target"]["target_kind"]
        proposal["target_key"] = proposal["target"]["target_key"]
        proposal.pop("target")
    elif mutation == "forbidden_nested_authority":
        proposal["capability_request"] = {"graph_ref": {"graph_id": "forbidden"}}
    elif mutation == "forbidden_raw_material":
        proposal["raw_model_response"] = "must never be retained"
    elif mutation == "missing_recursion_depth":
        proposal.pop("recursion_depth")
    elif mutation == "missing_specialist_parent_ref":
        proposal.pop("specialist_parent_ref")
    elif mutation == "missing_posture":
        proposal.pop("posture")
    with pytest.raises(SpecialistGraphRuntimeError):
        normalize_specialist_need_proposal(proposal)


@pytest.mark.parametrize(
    "authority_key",
    (
        "action_id",
        "observation_id",
        "run_id",
        "request_id",
        "proposal_id",
        "validation_id",
        "challenge_id",
        "component_id",
        "edge_id",
        "graph_id",
        "node_id",
        "node_revision",
        "graph_revision",
        "revision",
        "canonical_state",
        "admission_status",
        "runkernel_action",
        "runkernel_observation",
        "final_answer_packet",
        "fap_authority",
        "author_authority",
        "proposal_digest",
        "Proposal-Digest",
        "runkernel_shadow",
    ),
)
def test_generic_proposal_rejects_authority_anywhere_in_input_refs(
    authority_key: str,
) -> None:
    proposal = SpecialistNorthstarHarness._proposal(
        target_kind="component",
        target_key="component-one",
        hint="test.specialist.alpha",
        posture="optional",
        requirement=REQUIREMENT,
    )
    proposal["input_artifact_refs"] = [
        {"nested": {"deeper": {authority_key: "model-authored"}}}
    ]

    with pytest.raises(SpecialistGraphRuntimeError):
        normalize_specialist_need_proposal(proposal)


def test_generic_proposal_rejects_input_ref_depth_instead_of_softening() -> None:
    nested: dict[str, Any] = {"local_artifact_key": "source_a"}
    for _ in range(14):
        nested = {"nested": nested}
    proposal = SpecialistNorthstarHarness._proposal(
        target_kind="component",
        target_key="component-one",
        hint="test.specialist.alpha",
        posture="optional",
        requirement=REQUIREMENT,
    )
    proposal["input_artifact_refs"] = [nested]

    with pytest.raises(SpecialistGraphRuntimeError):
        normalize_specialist_need_proposal(proposal)


@pytest.mark.parametrize(
    "input_ref",
    (
        {"nested": {1: "coerced-key"}},
        {"nested": {"": "empty-key"}},
        {"nested": {f"key_{index}": "value" for index in range(65)}},
        {"nested": ["value"] * 65},
        {"nested": "x" * 1001},
        {f"field_{index}": "x" * 1000 for index in range(17)},
        {"nested": float("nan")},
        {"nested": b"binary"},
        {"nested": lambda: None},
        {"nested": object()},
    ),
)
def test_generic_proposal_rejects_nonexact_or_unbounded_input_refs(
    input_ref: dict[Any, Any],
) -> None:
    proposal = SpecialistNorthstarHarness._proposal(
        target_kind="component",
        target_key="component-one",
        hint="test.specialist.alpha",
        posture="optional",
        requirement=REQUIREMENT,
    )
    proposal["input_artifact_refs"] = [input_ref]

    with pytest.raises(SpecialistGraphRuntimeError):
        normalize_specialist_need_proposal(proposal)


def test_generic_proposal_preserves_safe_local_input_ref_exactly() -> None:
    proposal = SpecialistNorthstarHarness._proposal(
        target_kind="component",
        target_key="component-one",
        hint="test.specialist.alpha",
        posture="optional",
        requirement=REQUIREMENT,
    )
    safe_ref = {
        "local_artifact_key": "source_a",
        "artifact_kind": "bounded_local_input",
    }
    proposal["input_artifact_refs"] = [safe_ref]

    validated = normalize_specialist_need_proposal(proposal)

    assert validated == proposal
    assert validated["input_artifact_refs"] == [safe_ref]


def test_registry_and_policy_are_closed_by_default_and_calculator_is_absent() -> None:
    registry = closed_specialist_registry().projection()
    policy = closed_specialist_execution_policy().projection()
    assert registry["capability_count"] == 0
    assert policy["enabled_capability_ids"] == []
    assert policy["specialist_work_item_limit"] == 0
    assert policy["parallelism"] is policy["recursion"] is False
    assert "specialist_source_bound_calculation" not in json.dumps(registry)


def test_policy_denial_keeps_typed_required_optional_posture() -> None:
    proposal = SpecialistNorthstarHarness._proposal(
        target_kind="component",
        target_key="component-one",
        hint="test.specialist.alpha",
        posture="required",
        requirement=REQUIREMENT,
    )
    bound = bind_specialist_need_proposal(
        run_id="run-one",
        request_id="request-one",
        origin_role="component_analyst",
        origin_action_ref={"action_id": "action-one"},
        origin_artifact_ref={"artifact_id": "artifact-one"},
        proposal=proposal,
        canonical_target_ref={
            "target_kind": "component",
            "target_key": "component-one",
            "target_revision": 1,
        },
        accepted_contract_ref={"accepted_contract_digest": "contract-one"},
        graph_ref={},
        registry=closed_specialist_registry(),
        policy=closed_specialist_execution_policy(),
    )
    assert bound["proposal_authority"] == PROPOSAL_DENIED_POLICY
    assert bound["posture"] == "required"
    assert bound["rejection_reason"] == "specialist_execution_closed_by_policy"


@pytest.mark.parametrize(
    ("posture", "expected_answer", "expected_scheduler_status"),
    (
        ("optional", True, "completed"),
        ("required", False, "blocked_required_specialist_proposal"),
    ),
)
def test_required_versus_optional_policy_denial_in_ordinary_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    posture: str,
    expected_answer: bool,
    expected_scheduler_status: str,
) -> None:
    harness = SpecialistNorthstarHarness(tmp_path)
    harness.posture = posture
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=closed_specialist_registry(),
        policy=closed_specialist_execution_policy(),
    )
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    proposal = plane["proposals"][0]
    assert (outcome.report == NORTHSTAR_REPORT) is expected_answer
    assert scheduler["status"] == expected_scheduler_status
    assert proposal["proposal_authority"] == PROPOSAL_DENIED_POLICY
    assert proposal["posture"] == posture
    assert (
        plane["proposal_dispositions"][0]["execution_availability_posture"]
        == AVAILABILITY_POLICY
    )
    assert plane["need_handoffs"][0]["result"] == {}
    if posture == "optional":
        assert (
            harness.specialist_analyst_resume_inputs[0]["specialist_need_handoff"][
                "availability_posture"
            ]
            == AVAILABILITY_POLICY
        )
        assert plane["need_handoffs"][0]["validator_consumption"] == (
            "consumed_by_component_analyst"
        )
    else:
        assert plane["need_handoffs"][0]["validator_consumption"] == (
            "pending_validator_consumption"
        )


def test_one_unit_budget_exhaustion_blocks_second_required_specialist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    harness.component_proposal_all = True
    harness.posture = "required"
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    pool = scheduler["specialist_compatibility_pool"]
    specialist_leases = [
        item
        for item in scheduler["lease_history"]
        if (item.get("work") or {}).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
    ]
    assert outcome.report != NORTHSTAR_REPORT
    assert scheduler["status"] == "blocked_exhausted"
    assert pool["specialist_total"] == pool["specialist_spent"] == 1
    assert pool["specialist_remaining"] == pool["specialist_reserved"] == 0
    assert [item["status"] for item in specialist_leases] == [
        LEASE_COMPLETED,
        "denied_exhausted",
    ]
    assert len(calls) == 1
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert [
        item["execution_availability_posture"]
        for item in plane["proposal_dispositions"]
    ] == [
        AVAILABILITY_RESULT,
        AVAILABILITY_BUDGET,
    ]


def test_one_unit_budget_exhaustion_hands_optional_need_to_analyst_resume_without_second_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    harness.component_proposal_all = True
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    specialist_leases = [
        item
        for item in scheduler["lease_history"]
        if (item.get("work") or {}).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
    ]
    assert outcome.report == NORTHSTAR_REPORT
    assert len(calls) == len(specialist_leases) == 1
    assert plane["proposal_count"] == plane["proposal_disposition_count"] == 5
    availability = [
        item["execution_availability_posture"]
        for item in plane["proposal_dispositions"]
    ]
    assert availability.count(AVAILABILITY_RESULT) == 1
    assert availability.count(AVAILABILITY_BUDGET) == 4
    assert all(
        item["terminal_nonexecution_reason"] == "specialist_pool_exhausted"
        for item in plane["proposal_dispositions"]
        if item["execution_availability_posture"] == AVAILABILITY_BUDGET
    )
    assert [
        item["availability_posture"] for item in plane["need_handoffs"]
    ] == availability
    assert all(
        item["validator_consumption"] == "consumed_by_component_analyst"
        for item in plane["need_handoffs"]
    )
    assert any(
        packet["specialist_need_handoff"]["availability_posture"]
        == AVAILABILITY_BUDGET
        for packet in harness.specialist_analyst_resume_inputs
    )


@pytest.mark.parametrize(
    ("denial", "expected_authority", "expected_availability"),
    (
        ("capability", PROPOSAL_REJECTED, AVAILABILITY_CAPABILITY),
        ("target", PROPOSAL_UNSUPPORTED_TARGET, AVAILABILITY_TARGET),
    ),
)
def test_optional_capability_and_target_denials_reach_component_analyst_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    denial: str,
    expected_authority: str,
    expected_availability: str,
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    if denial == "capability":
        harness.capability_requirement = "missing_fixture_requirement"
    else:
        harness.component_target_override = "unrelated-component"
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_registry(calls),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert outcome.report == NORTHSTAR_REPORT
    assert calls == []
    if denial == "target":
        assert plane["proposals"] == []
        assert plane["proposal_dispositions"] == []
        assert plane["need_handoffs"] == []
        assert plane["proposal_rejections"][0]["rejection_category"] == (
            "proposal_target_mismatch"
        )
        assert not harness.specialist_analyst_resume_inputs
        component_admission = next(
            item
            for item in kernel.state.projections[
                "multicomponent_component_admission"
            ]["component_admission_refs"]
            if item["component_id"] == "component-1"
        )
        assert component_admission["component_analyst_case_ref"]["role"] == ROLE_COMPONENT_ANALYST
        assert "dprime_validation_ref" not in component_admission
    else:
        assert plane["proposals"][0]["proposal_authority"] == expected_authority
        assert (
            plane["proposal_dispositions"][0]["execution_availability_posture"]
            == expected_availability
        )
        assert (
            harness.specialist_analyst_resume_inputs[0]["specialist_need_handoff"][
                "availability_posture"
            ]
            == expected_availability
        )


def _terminal_registry(
    calls: list[dict[str, Any]], *, posture: str
) -> SpecialistCapabilityRegistry:
    def adapter(inputs: dict[str, Any]) -> dict[str, Any]:
        calls.append({"inputs": deepcopy(inputs), "thread_id": threading.get_ident()})
        if posture == "raise":
            raise RuntimeError("fixture capability failure")
        return {
            "bounded_result": {},
            "execution_posture": posture,
            "blockers": [f"fixture {posture}"],
        }

    return SpecialistCapabilityRegistry(
        (
            SpecialistCapabilitySpec(
                capability_id="test.specialist.alpha",
                version="1",
                capability_requirement=REQUIREMENT,
                supported_target_kinds=("component", "synthesis"),
                input_schema_ref=INPUT_SCHEMA,
                output_schema_ref=OUTPUT_SCHEMA,
                adapter=adapter,
            ),
        )
    )


@pytest.mark.parametrize(
    ("posture", "expected_result", "expected_lease"),
    (
        ("raise", EXECUTION_FAILED, LEASE_FAILED),
        (EXECUTION_BLOCKED, EXECUTION_BLOCKED, LEASE_BLOCKED),
        (EXECUTION_CONTESTED, EXECUTION_CONTESTED, LEASE_CONTESTED),
    ),
)
def test_capability_failure_block_and_contested_remain_spent_and_validated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    posture: str,
    expected_result: str,
    expected_lease: str,
) -> None:
    calls: list[dict[str, Any]] = []
    harness = SpecialistNorthstarHarness(tmp_path)
    outcome, kernel, _captured = _run(
        tmp_path,
        monkeypatch,
        harness=harness,
        registry=_terminal_registry(calls, posture=posture),
        policy=SpecialistExecutionPolicy(
            enabled_capability_ids=("test.specialist.alpha",),
            specialist_work_item_limit=1,
        ),
    )
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    result = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE][
        "result_artifacts"
    ][0]
    lease = next(
        item
        for item in scheduler["lease_history"]
        if (item.get("work") or {}).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
    )
    assert outcome.report != NORTHSTAR_REPORT
    assert outcome.terminal_status == "blocked"
    assert outcome.execution_trace["blocked_fap_terminal"]["author_called"] is False
    assert harness.author_prompts == []
    assert result["execution_posture"] == expected_result
    assert result["validator_consumption"] == "rejected_by_validator"
    assert lease["status"] == expected_lease
    assert scheduler["specialist_compatibility_pool"]["specialist_spent"] == 1
    assert len(calls) == 1
    expected_availability = {
        EXECUTION_FAILED: AVAILABILITY_FAILED,
        EXECUTION_BLOCKED: AVAILABILITY_BLOCKED,
        EXECUTION_CONTESTED: AVAILABILITY_CONTESTED,
    }[expected_result]
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert (
        plane["proposal_dispositions"][0]["execution_availability_posture"]
        == expected_availability
    )
    assert (
        harness.specialist_analyst_resume_inputs[0]["specialist_need_handoff"][
            "availability_posture"
        ]
        == expected_availability
    )


def _specialist_scheduler_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[SimpleNamespace, dict[str, Any]]:
    scheduler = initialize_scheduler_v3_state(
        run_id="specialist-scheduler-run",
        request_id="specialist-scheduler-request",
        configured_provider="Local",
        specialist_work_item_limit=1,
        specialist_registry_digest="registry-digest",
        specialist_execution_policy_digest="policy-digest",
    )
    state = SimpleNamespace(
        run_id="specialist-scheduler-run",
        request_id="specialist-scheduler-request",
        projections={MULTICOMPONENT_SCHEDULER_STAGE: scheduler},
    )
    core = {
        "schema_version": "multicomponent_semantic_work_v1",
        "run_id": state.run_id,
        "request_id": state.request_id,
        "accepted_contract_ref": {"accepted_contract_digest": "contract"},
        "graph_ref": {"graph_digest": "graph"},
        "target_kind": "synthesis",
        "component_id": None,
        "synthesis_key": "S",
        "node_ref": {"target_kind": "synthesis", "target_key": "S"},
        "role": WORK_KIND_SPECIALIST_CAPABILITY,
        "logical_evaluation_key": "specialist-work:test",
        "input_packet_digest": "input-digest",
        "prerequisite_refs": [],
        "scheduler_revision": scheduler["scheduler_revision"],
        "output_schema_variant": OUTPUT_SCHEMA,
        "parallel_class": "serial_only",
        "work_kind": WORK_KIND_SPECIALIST_CAPABILITY,
        "resource_class": "deterministic_specialist",
        "executor_class": "registered_deterministic_capability",
        "capability_id": "test.specialist.alpha",
        "capability_version": "1",
        "capability_descriptor_digest": "descriptor-digest",
        "specialist_proposal_ref": {
            "proposal_id": "proposal-one",
            "posture": "required",
        },
    }
    work_digest = scheduling._digest(core)
    work = {
        **core,
        "work_id": f"multicomponent-work:{work_digest[:24]}",
        "work_digest": work_digest,
    }
    monkeypatch.setattr(
        scheduling,
        "derive_ready_work",
        lambda _state, allow_active_lease=False: [deepcopy(work)],
    )
    return state, work


def _dispatch_specialist_fixture(
    state: SimpleNamespace,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scheduler, batch = grant_next_batch(
        state=state,
        action_ref={"action_id": "grant-action"},
    )
    state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = scheduler
    lease_ref = batch["ordered_lease_refs"][0]
    lease = next(
        item
        for item in scheduler["lease_history"]
        if item["lease_id"] == lease_ref["lease_id"]
    )
    work = lease["work"]
    descriptor_core = {
        "schema_version": MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SCHEMA_VERSION,
        "batch_id": batch["batch_id"],
        "batch_digest": batch["batch_digest"],
        "batch_index": 0,
        "work_id": work["work_id"],
        "work_digest": work["work_digest"],
        "lease_id": lease["lease_id"],
        "lease_digest": lease["lease_digest"],
        "role": work["role"],
        "action_type": "specialist_capability_execute",
        "logical_evaluation_key": work["logical_evaluation_key"],
        "input_packet_digest": work["input_packet_digest"],
        "output_schema_variant": work["output_schema_variant"],
    }
    descriptor = {
        **descriptor_core,
        "descriptor_digest": scheduling._digest(descriptor_core),
    }
    descriptor_set_core = {
        "schema_version": MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SET_SCHEMA_VERSION,
        "batch_id": batch["batch_id"],
        "batch_digest": batch["batch_digest"],
        "ordered_descriptors": [descriptor],
    }
    action_ref = {
        "action_id": "specialist-action",
        "sequence": 1,
        "batch_index": 0,
        "role": work["role"],
        "logical_evaluation_key": work["logical_evaluation_key"],
        "input_packet_digest": work["input_packet_digest"],
        "lease_id": lease["lease_id"],
        "lease_digest": lease["lease_digest"],
        "work_id": work["work_id"],
        "work_digest": work["work_digest"],
    }
    scheduler = dispatch_batch(
        state=state,
        batch_id=batch["batch_id"],
        dispatch_action_ref={"action_id": "dispatch-action"},
        descriptor_set={
            **descriptor_set_core,
            "descriptor_set_digest": scheduling._digest(descriptor_set_core),
        },
        child_action_refs=(action_ref,),
    )
    state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = scheduler
    started = next(
        item
        for item in scheduler["lease_history"]
        if item["lease_id"] == lease["lease_id"]
    )
    inputs = {
        "batch_id": started["batch_id"],
        "batch_digest": started["batch_digest"],
        "batch_index": started["batch_index"],
        "lease_id": started["lease_id"],
        "lease_digest": started["lease_digest"],
        "work_id": work["work_id"],
        "work_digest": work["work_digest"],
        "logical_evaluation_key": work["logical_evaluation_key"],
        "input_packet_digest": work["input_packet_digest"],
        "capability_id": work["capability_id"],
        "capability_version": work["capability_version"],
    }
    return scheduler, started, inputs


def test_predispatch_cancellation_returns_specialist_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, _work = _specialist_scheduler_fixture(monkeypatch)
    scheduler, batch = grant_next_batch(
        state=state,
        action_ref={"action_id": "grant-action"},
    )
    state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = scheduler
    cancelled = cancel_batch(
        state=state,
        batch_id=batch["batch_id"],
        action_ref={"action_id": "cancel-action"},
        reason="fixture_predispatch_cancel",
    )
    pool = cancelled["specialist_compatibility_pool"]
    assert pool["specialist_remaining"] == pool["specialist_total"] == 1
    assert pool["specialist_reserved"] == pool["specialist_spent"] == 0
    assert pool["specialist_returned"] == 1
    assert cancelled["lease_history"][0]["status"] == LEASE_CANCELLED


def test_poststart_stale_rejection_is_spent_and_late_success_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, _work = _specialist_scheduler_fixture(monkeypatch)
    _scheduler, _started, inputs = _dispatch_specialist_fixture(state)
    monkeypatch.setattr(scheduling, "work_is_current", lambda *_args, **_kwargs: False)
    stale = settle_specialist_lease(
        state=state,
        action_inputs=inputs,
        settlement=LEASE_STALE,
    )
    state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = stale
    pool = stale["specialist_compatibility_pool"]
    assert pool["specialist_spent"] == pool["specialist_total"] == 1
    assert pool["specialist_remaining"] == pool["specialist_reserved"] == 0
    assert stale["lease_history"][0]["status"] == LEASE_STALE
    with pytest.raises(scheduling.MulticomponentGraphSchedulingError):
        settle_specialist_lease(
            state=state,
            action_inputs=inputs,
            settlement=LEASE_COMPLETED,
        )


def test_no_recursion_downstream_authority_or_private_material() -> None:
    proposal = SpecialistNorthstarHarness._proposal(
        target_kind="component",
        target_key="component-one",
        hint="test.specialist.alpha",
        posture="optional",
        requirement=REQUIREMENT,
    )
    recursive = deepcopy(proposal)
    recursive["recursion_depth"] = 1
    with pytest.raises(SpecialistGraphRuntimeError):
        normalize_specialist_need_proposal(recursive)
    with pytest.raises(SpecialistGraphRuntimeError):
        SpecialistCapabilitySpec(
            capability_id="test.specialist.recursive",
            version="1",
            capability_requirement=REQUIREMENT,
            supported_target_kinds=("component",),
            input_schema_ref=INPUT_SCHEMA,
            output_schema_ref=OUTPUT_SCHEMA,
            adapter=lambda inputs: inputs,
            recursion=True,
        )
    private = deepcopy(proposal)
    private["input_artifact_refs"] = [{"raw_prompt": "private"}]
    with pytest.raises(SpecialistGraphRuntimeError):
        normalize_specialist_need_proposal(private)
