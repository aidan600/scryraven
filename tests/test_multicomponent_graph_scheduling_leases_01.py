"""PRODUCT-PATH-REGRESSION: RunKernel serial graph scheduling and leases.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded: run_pipeline -> selected ordinary multi-component
runtime -> Sufficiency -> FinalAnswerPacket -> Author or safe blocked RunOutcome.
Runtime consumer: core.ordinary_multicomponent_synthesis_runtime.
Exit condition: retain while the qualifying product path is scheduler-governed.
Forbidden interpretation: offline fixtures do not prove live model quality,
arbitrary-query support, permanent mode budgets, or physical parallelism.
"""

from __future__ import annotations

import inspect
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import core.multicomponent_graph_scheduling as scheduling
import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.evidence_ledger import EvidenceCandidate
from core.multicomponent_component_admission import component_analyst_input_packet
from core.multicomponent_graph_scheduling import (
    LEASE_CANCELLED,
    LEASE_COMPLETED,
    LEASE_DENIED_EXHAUSTED,
    LEASE_EXECUTION_STARTED,
    LEASE_FAILED,
    LEASE_GRANTED,
    LEASE_STALE,
    MULTICOMPONENT_ROLE_CALL_LIMITS,
    MULTICOMPONENT_SCHEDULER_STAGE,
    MulticomponentGraphSchedulingError,
    derive_multicomponent_compatibility_envelope,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    SELECTIVE_CROSS_COMPONENT_SCHEMA,
    execute_multicomponent_role_call,
    safe_packet_digest,
)
from core.protocols import NullStatusWriter
from core.run_kernel import (
    ActionType,
    Observation,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
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
from tests.test_multicomponent_dynamic_graph_recovery_01 import (
    DynamicNorthstarHarness,
    _forbid_direct_semantic_producer,
)
from tests.test_multicomponent_ordinary_end_to_end_synthesis_01 import (
    NORTHSTAR_REPORT,
    NorthstarHarness,
)


def _run_product(tmp_path: Path, *, dynamic: bool = False, total: int | None = None):
    monkeypatch = pytest.MonkeyPatch()
    scrub_offline_runtime(monkeypatch)
    _forbid_direct_semantic_producer(monkeypatch)
    if total is not None:
        monkeypatch.setattr(
            scheduling,
            "derive_multicomponent_compatibility_envelope",
            lambda: total,
        )
    harness = DynamicNorthstarHarness(tmp_path) if dynamic else NorthstarHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    try:
        outcome = orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-07-11",
                session_id=f"scheduler-{'dynamic' if dynamic else 'ordinary'}-{total}",
                run_id=f"scheduler-{'dynamic' if dynamic else 'ordinary'}-{total}",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )
        return outcome, captured["semantic_run_kernel"], captured, harness
    finally:
        monkeypatch.undo()


@pytest.fixture(scope="module")
def ordinary_product(tmp_path_factory: pytest.TempPathFactory):
    return _run_product(tmp_path_factory.mktemp("scheduler-ordinary"))


@pytest.fixture(scope="module")
def dynamic_product(tmp_path_factory: pytest.TempPathFactory):
    return _run_product(tmp_path_factory.mktemp("scheduler-dynamic"), dynamic=True)


def _contract(kernel: RunKernel, *, component_count: int = 2) -> dict[str, Any]:
    components = [
        {
            "component_id": f"component:{index}",
            "component_revision": 1,
            "component_digest": f"component-digest:{index}",
            "user_facing_label": f"Fact {index}",
            "user_facing_question": f"What is fact {index}?",
            "mandatory_caveats": [],
            "prohibited_upgrades": [],
        }
        for index in range(component_count)
    ]
    return {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": kernel.state.run_id,
        "request_id": kernel.state.request_id,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": f"contract-digest:{component_count}",
        "parent_question_meaning_record_id": "qmr:scheduler-test",
        "parent_question_meaning_record_digest": "qmr-digest:scheduler-test",
        "accepted_answer_component_count": component_count,
        "accepted_answer_component_refs": components,
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Explain how these facts relate.",
        },
    }


def _scheduler_kernel() -> tuple[RunKernel, dict[str, dict[str, Any]]]:
    kernel = RunKernel.start(run_id="scheduler-unit-run", request_id="scheduler-unit-request")
    contract = _contract(kernel)
    kernel.state.initial_answer_contract = contract
    kernel.state.initial_answer_contract_projection = {"accepted": True}
    for component in contract["accepted_answer_component_refs"]:
        candidate_id = f"evidence:{component['component_id']}"
        kernel.state.evidence_ledger.candidates[candidate_id] = EvidenceCandidate(
            candidate_id=candidate_id,
            readable_status="readable",
        )
    packets = {
        str(component["component_id"]): component_analyst_input_packet(
            run_id=kernel.state.run_id,
            request_id=kernel.state.request_id,
            accepted_contract=contract,
            component_ref=component,
            evidence_input={
                "evidence_status": "available",
                "evidence_ref_id": f"evidence:{component['component_id']}",
                "bounded_text": "A bounded fixture fact.",
                "candidate_custody_ref": {
                    "candidate_id": f"evidence:{component['component_id']}"
                },
            },
        )
        for component in contract["accepted_answer_component_refs"]
    }
    kernel.initialize_multicomponent_graph_scheduler(
        component_analyst_input_packets=packets,
        requested_synthesis_directive="Explain how these facts relate.",
    )
    return kernel, packets


def _role_kwargs(*, ask_model):
    return {
        "ask_model": ask_model,
        "clean_json_response": lambda value: value,
        "provider": "offline",
        "model": "fixture",
        "base_url": "",
        "api_key": "",
        "use_reasoning": False,
    }


def _scheduler(kernel: RunKernel) -> dict[str, Any]:
    return kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]


def test_01_ordinary_serial_product_success(ordinary_product) -> None:
    outcome, kernel, captured, harness = ordinary_product
    scheduler = _scheduler(kernel)
    assert outcome.report == NORTHSTAR_REPORT
    assert captured["author_handoff_called"] is True
    assert scheduler["status"] == "completed"
    semantic_calls = [
        call for call in harness.model_calls if call.get("system_prompt") in ROLE_SYSTEM_PROMPTS.values()
    ]
    assert len(semantic_calls) == len(scheduler["lease_history"])
    assert all(lease["status"] == LEASE_COMPLETED for lease in scheduler["lease_history"])
    assert scheduler["active_physical_lease_count"] == 0


def test_02_multiple_ready_items_are_serial_and_deterministic(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    scheduler = _scheduler(kernel)
    first_grant = next(
        item for item in scheduler["transition_history"] if item["transition"] == LEASE_GRANTED
    )
    assert first_grant["ready_work_count"] == 5
    works = [lease["work"] for lease in scheduler["lease_history"]]
    assert works[0]["role"] == ROLE_COMPONENT_ANALYST
    assert works[1]["role"] == ROLE_COMPONENT_DPRIME
    assert works[0]["component_id"] == works[1]["component_id"]
    assert scheduler["maximum_active_physical_leases"] == 1


def test_03_work_is_derived_only_after_exact_upstream_authority(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    leases = _scheduler(kernel)["lease_history"]
    analyst_position: dict[str, int] = {}
    for position, lease in enumerate(leases):
        work = lease["work"]
        if work["role"] == ROLE_COMPONENT_ANALYST:
            analyst_position[str(work["component_id"])] = position
        if work["role"] == ROLE_COMPONENT_DPRIME:
            assert analyst_position[str(work["component_id"])] < position
            assert any("analyst_artifact_digest" in ref for ref in work["prerequisite_refs"])
    assert "scheduler_graph" not in _scheduler(kernel)


def test_04_layered_synthesis_preserves_topological_readiness(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    synthesis = [
        lease["work"]
        for lease in _scheduler(kernel)["lease_history"]
        if lease["work"]["role"] == ROLE_SYNTHESIS_DPRIME
    ]
    assert [work["synthesis_key"] for work in synthesis] == ["E", "S"]
    assert any(ref.get("node_id") for ref in synthesis[1]["prerequisite_refs"])


def test_05_full_product_path_lease_coverage(dynamic_product) -> None:
    outcome, kernel, captured, _harness = dynamic_product
    assert outcome.report
    assert captured["author_handoff_called"] is True
    works = [lease["work"] for lease in _scheduler(kernel)["lease_history"]]
    assert {work["role"] for work in works} == set(MULTICOMPONENT_ROLE_CALL_LIMITS)
    assert any(work.get("recovery_authorization_ref") for work in works)
    assert any(work.get("selective_closure_ref") for work in works)
    assert any(work.get("output_schema_variant") == SELECTIVE_CROSS_COMPONENT_SCHEMA for work in works)
    assert any(
        work["role"] == ROLE_SCRUTINEER and work.get("selective_closure_ref")
        for work in works
    )


def test_06_compatibility_envelope_has_one_shared_cap_owner() -> None:
    kernel, packets = _scheduler_kernel()
    envelope = _scheduler(kernel)["compatibility_envelope"]
    assert envelope["role_limits"] == dict(MULTICOMPONENT_ROLE_CALL_LIMITS)
    assert envelope["total_units"] == sum(MULTICOMPONENT_ROLE_CALL_LIMITS.values())
    assert envelope["total_units"] == derive_multicomponent_compatibility_envelope()
    with pytest.raises(TypeError):
        kernel.initialize_multicomponent_graph_scheduler(
            component_analyst_input_packets=packets,
            requested_synthesis_directive="Explain how these facts relate.",
            total_units=1,  # type: ignore[call-arg]
        )


def test_07_dispatch_commitment_spends_immediately_before_transport() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    envelope = _scheduler(kernel)["compatibility_envelope"]
    assert lease["status"] == LEASE_GRANTED
    assert envelope["reserved_units"] == 1
    assert envelope["spent_units"] == 0
    work = lease["work"]
    kernel.prepare_multicomponent_role_dispatch(
        lease_id=lease["lease_id"],
        role=work["role"],
        input_packet_digest=safe_packet_digest(packets[str(work["component_id"])]),
        logical_evaluation_key=work["logical_evaluation_key"],
    )
    latest = _scheduler(kernel)["lease_history"][-1]
    assert latest["status"] == LEASE_EXECUTION_STARTED
    assert _scheduler(kernel)["compatibility_envelope"]["spent_units"] == 1


def test_08_atomic_role_admission_and_lease_completion() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    artifact = execute_multicomponent_role_call(
        run_kernel=kernel,
        role=work["role"],
        input_packet=packets[str(work["component_id"])],
        logical_evaluation_key=work["logical_evaluation_key"],
        lease_id=lease["lease_id"],
        **_role_kwargs(
            ask_model=lambda *_args, **_kwargs: json.dumps(
                {"claim_text": "A bounded claim.", "support_status": "supported"}
            )
        ),
    )
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_COMPLETED
    role_action = next(
        action
        for action in kernel.state.issued_actions.values()
        if action.action_type is ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE
    )
    assert kernel.state.projections[role_action.stage]["artifact_digest"] == artifact["artifact_digest"]
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(
            Observation.from_action(
                role_action,
                observation_type=role_action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"semantic_role_artifact": artifact},
            )
        )


def test_09_transport_failure_is_spent_and_admits_no_artifact() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    with pytest.raises(RuntimeError, match="transport failed"):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=work["role"],
            input_packet=packets[str(work["component_id"])],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id=lease["lease_id"],
            **_role_kwargs(ask_model=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("transport failed"))),
        )
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_FAILED
    assert _scheduler(kernel)["compatibility_envelope"]["spent_units"] == 1
    assert kernel.state.projections[
        f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{work['logical_evaluation_key']}"
    ]["semantic_artifact_admitted"] is False


def test_10_invalid_role_output_is_spent_without_retry() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    calls = {"count": 0}

    def invalid(*_args, **_kwargs):
        calls["count"] += 1
        return "not-json"

    with pytest.raises(Exception):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=work["role"],
            input_packet=packets[str(work["component_id"])],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id=lease["lease_id"],
            **_role_kwargs(ask_model=invalid),
        )
    assert calls["count"] == 1
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_FAILED


def test_11_predispatch_cancellation_returns_exactly_once() -> None:
    kernel, _packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    initial_remaining = _scheduler(kernel)["compatibility_envelope"]["remaining_units"]
    kernel.cancel_multicomponent_work_lease(lease_id=lease["lease_id"])
    envelope = _scheduler(kernel)["compatibility_envelope"]
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_CANCELLED
    assert envelope["remaining_units"] == initial_remaining + 1
    assert envelope["returned_units"] == 1
    with pytest.raises(MulticomponentGraphSchedulingError):
        kernel.cancel_multicomponent_work_lease(lease_id=lease["lease_id"])


def test_12_postdispatch_staleness_rejects_result_and_keeps_spend() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]

    def stale_after_dispatch(*_args, **_kwargs):
        changed = dict(kernel.state.initial_answer_contract)
        changed["accepted_contract_digest"] = "changed-after-dispatch"
        kernel.state.initial_answer_contract = changed
        return json.dumps({"claim_text": "Late claim.", "support_status": "supported"})

    with pytest.raises(Exception, match="stale"):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=work["role"],
            input_packet=packets[str(work["component_id"])],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id=lease["lease_id"],
            **_role_kwargs(ask_model=stale_after_dispatch),
        )
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_STALE
    assert _scheduler(kernel)["compatibility_envelope"]["spent_units"] == 1


def test_13_wrong_and_caller_authored_bindings_are_rejected() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    wrongs = (
        {"role": ROLE_COMPONENT_DPRIME},
        {"logical_evaluation_key": "forged-key"},
        {"input_packet_digest": "forged-digest"},
        {"output_schema_variant": SELECTIVE_CROSS_COMPONENT_SCHEMA},
    )
    base = {
        "lease_id": lease["lease_id"],
        "role": work["role"],
        "input_packet_digest": safe_packet_digest(packets[str(work["component_id"])]),
        "logical_evaluation_key": work["logical_evaluation_key"],
        "output_schema_variant": None,
    }
    for replacement in wrongs:
        with pytest.raises(RunKernelTransitionError, match="scheduler-selected"):
            kernel.prepare_multicomponent_role_dispatch(**{**base, **replacement})
    with pytest.raises(RunKernelTransitionError, match="exact granted lease"):
        kernel.authorize_multicomponent_role_call(
            role=work["role"],
            input_packet_digest=work["input_packet_digest"],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id="caller-forged-lease",
            dispatch_action_id="caller-forged-dispatch",
        )


def test_14_selective_recovery_schedules_only_affected_branches(dynamic_product) -> None:
    _outcome, kernel, _captured, _harness = dynamic_product
    works = [lease["work"] for lease in _scheduler(kernel)["lease_history"]]
    selective = [work for work in works if work.get("selective_closure_ref")]
    assert {work.get("synthesis_key") for work in selective if work["role"] == ROLE_SYNTHESIS_DPRIME} == {
        "filing_route",
        "applicant_guidance",
    }
    benefit = [work for work in works if work.get("synthesis_key") == "benefit_summary"]
    assert len(benefit) == 1
    assert not benefit[0].get("selective_closure_ref")
    assert any(work["role"] == ROLE_SCRUTINEER for work in selective)


def test_15_early_exhaustion_returns_safe_blocked_runoutcome(tmp_path: Path) -> None:
    outcome, kernel, captured, harness = _run_product(tmp_path, total=0)
    scheduler = _scheduler(kernel)
    assert scheduler["status"] == "blocked_exhausted"
    assert scheduler["lease_history"][0]["status"] == LEASE_DENIED_EXHAUSTED
    assert not [
        call for call in harness.model_calls if call.get("system_prompt") in ROLE_SYSTEM_PROMPTS.values()
    ]
    assert captured["author_handoff_called"] is False
    assert outcome.failure_card["blocked_fap"] is True


def test_16_late_exhaustion_preserves_progress_and_blocks_author(tmp_path: Path) -> None:
    outcome, kernel, captured, harness = _run_product(tmp_path, total=11)
    scheduler = _scheduler(kernel)
    assert scheduler["status"] == "blocked_exhausted"
    assert scheduler["compatibility_envelope"]["spent_units"] == 11
    assert scheduler["lease_history"][-1]["work"]["role"] == ROLE_SYNTHESIS_DPRIME
    assert scheduler["lease_history"][-1]["status"] == LEASE_DENIED_EXHAUSTED
    semantic_calls = [
        call for call in harness.model_calls if call.get("system_prompt") in ROLE_SYSTEM_PROMPTS.values()
    ]
    assert len(semantic_calls) == 11
    assert captured["author_handoff_called"] is False
    assert outcome.failure_card["blocked_fap"] is True


def test_17_deterministic_transitions_consume_no_semantic_units(ordinary_product) -> None:
    _outcome, kernel, _captured, harness = ordinary_product
    scheduler = _scheduler(kernel)
    role_actions = [
        action
        for action in kernel.state.issued_actions.values()
        if action.action_type
        in {
            ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_COMPONENT_DPRIME_EXECUTE,
            ActionType.MULTICOMPONENT_CROSS_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_SYNTHESIS_DPRIME_EXECUTE,
            ActionType.MULTICOMPONENT_SCRUTINEER_EXECUTE,
        }
    ]
    assert scheduler["compatibility_envelope"]["spent_units"] == len(role_actions)
    semantic_calls = [
        call for call in harness.model_calls if call.get("system_prompt") in ROLE_SYSTEM_PROMPTS.values()
    ]
    assert len(role_actions) == len(semantic_calls)


def test_18_nonqualifying_path_creates_no_scheduler() -> None:
    import core.ordinary_multicomponent_synthesis_runtime as runtime

    kernel = RunKernel.start(run_id="nonqualifying-run", request_id="nonqualifying-request")
    kernel.state.initial_answer_contract = _contract(kernel, component_count=1)
    result = runtime.execute_ordinary_semantic_or_multicomponent_handoff_from_scope(
        kernel,
        {"query": "one component"},
        execute_selected_lane=False,
    )
    assert result.status is runtime.OrdinaryMulticomponentStatus.NOT_QUALIFIED
    assert MULTICOMPONENT_SCHEDULER_STAGE not in kernel.state.projections


def test_19_scheduler_trace_is_sanitized(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    rendered = json.dumps(_scheduler(kernel), sort_keys=True)
    for forbidden in (
        "SECRET_PROMPT",
        "provider_payload_value",
        "api_key_value",
        "private_log_value",
        "database_row_value",
        "cache_row_value",
    ):
        assert forbidden not in rendered
    assert "component_evidence" not in rendered
    assert "sanitized_excerpt" not in rendered


def test_20_no_parallelism_and_serial_trace(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    source = Path("core/multicomponent_graph_scheduling.py").read_text(encoding="utf-8")
    for forbidden in ("ThreadPoolExecutor", "multiprocessing", "asyncio", "create_task"):
        assert forbidden not in source
    scheduler = _scheduler(kernel)
    assert scheduler["runtime_parallelism"] is False
    assert scheduler["serial_scheduling"] is True
    assert scheduler["maximum_active_physical_leases"] == 1


def test_21_product_driver_dispatches_only_scheduler_selected_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import core.ordinary_multicomponent_synthesis_runtime as runtime

    original = runtime._execute_multicomponent_role_transport
    observed: list[tuple[str, str, str, str]] = []

    def exact_dispatch(**kwargs):
        kernel = kwargs["run_kernel"]
        lease = _scheduler(kernel)["lease_history"][-1]
        work = lease["work"]
        assert kwargs["lease_id"] == lease["lease_id"]
        assert kwargs["role"] == work["role"]
        assert kwargs["logical_evaluation_key"] == work["logical_evaluation_key"]
        assert safe_packet_digest(kwargs["input_packet"]) == work[
            "input_packet_digest"
        ]
        assert kwargs.get("output_schema_variant") == work.get(
            "output_schema_variant"
        )
        observed.append(
            (
                str(lease["lease_id"]),
                str(work["role"]),
                str(work["component_id"] or work["synthesis_key"] or "whole-case"),
                str(work["logical_evaluation_key"]),
            )
        )
        return original(**kwargs)

    monkeypatch.setattr(runtime, "_execute_multicomponent_role_transport", exact_dispatch)
    _outcome, kernel, _captured, _harness = _run_product(tmp_path)
    assert len(observed) == len(_scheduler(kernel)["lease_history"])


def test_22_scheduler_order_overrides_legacy_component_traversal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original = scheduling.derive_ready_work

    def reverse_scheduler_order(state, *, allow_active_lease=False):
        return list(
            reversed(
                original(state, allow_active_lease=allow_active_lease)
            )
        )

    monkeypatch.setattr(scheduling, "derive_ready_work", reverse_scheduler_order)
    _outcome, kernel, _captured, _harness = _run_product(tmp_path)
    legacy_order = [
        item["component_id"]
        for item in kernel.state.initial_answer_contract[
            "accepted_answer_component_refs"
        ]
    ]
    physical_order = [
        lease["work"]["component_id"]
        for lease in _scheduler(kernel)["lease_history"]
        if lease["work"]["role"] == ROLE_COMPONENT_ANALYST
    ]
    assert physical_order == list(reversed(legacy_order))
    assert physical_order != legacy_order


def test_23_selected_product_path_does_not_consume_legacy_semantic_loops(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import core.ordinary_multicomponent_synthesis_runtime as runtime

    def forbidden(*_args, **_kwargs):
        raise AssertionError("legacy semantic enumeration helper was invoked")

    for name in (
        "execute_multicomponent_role_call",
        "_execute_fresh_resynthesis",
        "_execute_selective_reconstruction",
        "_execute_selective_resynthesis",
        "_attempt_dynamic_recovery",
    ):
        monkeypatch.setattr(runtime, name, forbidden)
    outcome, kernel, _captured, _harness = _run_product(tmp_path, dynamic=True)
    assert outcome.report
    assert _scheduler(kernel)["status"] == "completed"
    selected_source = inspect.getsource(runtime._execute_selected_lane)
    assert "_drive_run_kernel_selected_semantic_work" in selected_source
    assert "execute_multicomponent_role_call(" not in selected_source


@pytest.mark.parametrize("dispatched", [False, True])
def test_24_completion_rejects_active_lease_without_mutation(
    dispatched: bool,
) -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    if dispatched:
        kernel.prepare_multicomponent_role_dispatch(
            lease_id=lease["lease_id"],
            role=work["role"],
            input_packet_digest=safe_packet_digest(
                packets[str(work["component_id"])]
            ),
            logical_evaluation_key=work["logical_evaluation_key"],
        )
    before = deepcopy(_scheduler(kernel))
    expected = LEASE_EXECUTION_STARTED if dispatched else LEASE_GRANTED
    with pytest.raises(
        MulticomponentGraphSchedulingError,
        match="cannot complete while a semantic lease is active",
    ):
        kernel.complete_multicomponent_graph_scheduler()
    assert _scheduler(kernel) == before
    assert _scheduler(kernel)["lease_history"][-1]["status"] == expected


def test_25_forged_terminal_scheduler_with_active_lease_is_rejected() -> None:
    kernel, _packets = _scheduler_kernel()
    kernel.grant_next_multicomponent_work_lease()
    forged = deepcopy(_scheduler(kernel))
    forged["status"] = "completed"
    forged.pop("scheduler_digest")
    forged = scheduling._refresh_scheduler(forged)
    with pytest.raises(
        MulticomponentGraphSchedulingError,
        match="terminal scheduler state cannot contain an active semantic lease",
    ):
        scheduling.validate_scheduler_state(forged)


def test_26_authorized_predispatch_authority_change_refunds_once() -> None:
    kernel, _packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    after_grant = deepcopy(_scheduler(kernel)["compatibility_envelope"])
    kernel.apply_multicomponent_scheduler_authority_change(
        transition="contract_authority_changed",
        authority_ref={"accepted_contract_digest": "next-contract-digest"},
    )
    scheduler = _scheduler(kernel)
    envelope = scheduler["compatibility_envelope"]
    assert scheduler["lease_history"][-1]["status"] == LEASE_CANCELLED
    assert envelope["remaining_units"] == after_grant["remaining_units"] + 1
    assert envelope["returned_units"] == after_grant["returned_units"] + 1
    kernel.apply_multicomponent_scheduler_authority_change(
        transition="target_authority_changed",
        authority_ref={"target_digest": "next-target-digest"},
    )
    assert _scheduler(kernel)["compatibility_envelope"]["returned_units"] == 1
    assert _scheduler(kernel)["lease_history"][-1]["lease_id"] == lease["lease_id"]


def test_27_authorized_postdispatch_change_rejects_late_observation() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    role_action = kernel.prepare_multicomponent_role_dispatch(
        lease_id=lease["lease_id"],
        role=work["role"],
        input_packet_digest=safe_packet_digest(
            packets[str(work["component_id"])]
        ),
        logical_evaluation_key=work["logical_evaluation_key"],
    )
    kernel.apply_multicomponent_scheduler_authority_change(
        transition="graph_authority_changed",
        authority_ref={"graph_digest": "next-graph-digest"},
    )
    scheduler = _scheduler(kernel)
    assert scheduler["lease_history"][-1]["status"] == LEASE_STALE
    assert scheduler["compatibility_envelope"]["spent_units"] == 1
    before_late_result = deepcopy(scheduler)
    with pytest.raises(
        MulticomponentGraphSchedulingError,
        match="exact active spent lease",
    ):
        kernel.reduce(
            Observation.from_action(
                role_action,
                observation_type=role_action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
    assert _scheduler(kernel) == before_late_result
    assert role_action.stage not in kernel.state.projections
