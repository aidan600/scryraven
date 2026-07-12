"""Phase 5A product-path regressions for hosted component parallel dispatch.

Test classification:
- proof class: offline_product_path_proof
- validation bucket: phase_focus
- harness label: PRODUCT-PATH-REGRESSION
- runtime path: ordinary qualifying ``run_pipeline`` multi-component execution
- promotion posture: remain phase-focused; these are detailed concurrency custody tests
"""

from __future__ import annotations

from copy import deepcopy

import pytest

import core.multicomponent_graph_scheduling as scheduling
from core.multicomponent_graph_scheduling import (
    BACKEND_CONSERVATIVE_UNKNOWN,
    BACKEND_HOSTED_API,
    BACKEND_LOCAL_OPENAI_COMPATIBLE,
    MULTICOMPONENT_SCHEDULER_SCHEMA_VERSION,
    MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION,
    MulticomponentGraphSchedulingError,
    cancel_batch,
    derive_ready_batch_work,
    initialize_scheduler_state,
    initialize_scheduler_v2_state,
    validate_scheduler_state,
)
from core.run_kernel import ActionType, RunKernel, RunKernelTransitionError, RunStageStatus
from tests.test_multicomponent_graph_scheduling_leases_01 import (
    _scheduler,
    _scheduler_kernel,
)


@pytest.mark.parametrize(
    ("provider", "configured", "backend", "width"),
    [
        ("OpenAI", "OpenAI", BACKEND_HOSTED_API, 2),
        ("open_router", "OpenRouter", BACKEND_HOSTED_API, 2),
        (
            "lm_studio",
            "Local (LM Studio)",
            BACKEND_LOCAL_OPENAI_COMPATIBLE,
            1,
        ),
        ("unsupported-provider", "unsupported-provider", BACKEND_CONSERVATIVE_UNKNOWN, 1),
    ],
)
def test_scheduler_v2_profile_is_derived_only_from_canonical_provider_identity(
    provider: str,
    configured: str,
    backend: str,
    width: int,
) -> None:
    scheduler = initialize_scheduler_v2_state(
        run_id="run-profile",
        request_id="request-profile",
        configured_provider=provider,
    )

    assert scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION
    assert scheduler["configured_provider_class"] == configured
    assert scheduler["backend_class"] == backend
    assert scheduler["effective_width"] == width
    assert scheduler["hard_cap"] == width
    assert scheduler["maximum_active_physical_leases"] == width
    assert scheduler["runtime_parallelism"] is (width == 2)
    assert scheduler["serial_scheduling"] is (width == 1)


def test_retained_scheduler_v1_rejects_every_parallel_or_batch_extension() -> None:
    scheduler = initialize_scheduler_state(
        run_id="run-v1",
        request_id="request-v1",
    )
    assert scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_SCHEMA_VERSION
    validate_scheduler_state(scheduler)

    mutations = (
        ("runtime_parallelism", True),
        ("maximum_active_physical_leases", 2),
        ("effective_width", 2),
        ("batch_history", []),
    )
    for key, value in mutations:
        forged = deepcopy(scheduler)
        forged[key] = value
        with pytest.raises(MulticomponentGraphSchedulingError):
            validate_scheduler_state(forged)


def test_v2_batch_grant_reserves_exact_contiguous_analyst_prefix() -> None:
    kernel, _packets = _scheduler_kernel()
    before = deepcopy(_scheduler(kernel)["compatibility_envelope"])

    batch = kernel.grant_next_multicomponent_work_batch()
    after = _scheduler(kernel)

    assert batch["parallel_class"] == "parallel_initial_component_analyst"
    assert [item["component_id"] for item in batch["ordered_work_refs"]] == [
        "component:0",
        "component:1",
    ]
    assert len(batch["ordered_lease_refs"]) == 2
    assert after["active_physical_lease_count"] == 2
    assert after["compatibility_envelope"]["remaining_units"] == (
        before["remaining_units"] - 2
    )
    assert after["compatibility_envelope"]["reserved_units"] == 2


def test_v2_batch_cancellation_returns_every_reservation_atomically() -> None:
    kernel, _packets = _scheduler_kernel()
    initial_remaining = _scheduler(kernel)["compatibility_envelope"]["remaining_units"]
    batch = kernel.grant_next_multicomponent_work_batch()

    kernel.cancel_multicomponent_work_batch(batch_id=batch["batch_id"])
    scheduler = _scheduler(kernel)
    cancelled = scheduler["batch_history"][-1]

    assert cancelled["status"] == "cancelled_predispatch_returned"
    assert cancelled["terminal_settlement_summary"] == {
        "settlement": "cancelled_predispatch_returned",
        "lease_count": 2,
        "all_reservations_returned": True,
    }
    assert scheduler["active_physical_lease_count"] == 0
    assert scheduler["compatibility_envelope"]["remaining_units"] == initial_remaining
    assert scheduler["compatibility_envelope"]["reserved_units"] == 0
    assert scheduler["compatibility_envelope"]["returned_units"] == 2


def test_v2_partial_budget_grants_only_the_prefix_that_fits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        scheduling,
        "derive_multicomponent_compatibility_envelope",
        lambda: 1,
    )
    kernel, _packets = _scheduler_kernel()

    batch = kernel.grant_next_multicomponent_work_batch()
    scheduler = _scheduler(kernel)

    assert len(batch["ordered_work_refs"]) == 1
    assert len(batch["ordered_lease_refs"]) == 1
    assert scheduler["compatibility_envelope"]["remaining_units"] == 0
    assert scheduler["compatibility_envelope"]["reserved_units"] == 1
    assert scheduler["status"] == "active"


def test_v2_batch_derivation_never_skips_incompatible_intervening_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, _packets = _scheduler_kernel()
    ready = kernel.derive_current_multicomponent_ready_work()
    intervening = deepcopy(ready[1])
    intervening.update(
        {
            "role": "cross_component_analyst",
            "parallel_class": "serial_only",
            "work_id": "intervening-work",
            "work_digest": "intervening-work-digest",
            "logical_evaluation_key": "intervening",
            "component_id": "intervening-component",
            "input_packet_digest": "intervening-packet-digest",
        }
    )
    monkeypatch.setattr(
        scheduling,
        "derive_ready_work",
        lambda *_args, **_kwargs: [ready[0], intervening, ready[1]],
    )

    selected = derive_ready_batch_work(kernel.state)

    assert [item["work_id"] for item in selected] == [ready[0]["work_id"]]


def test_v2_batch_cancellation_cannot_partially_refund() -> None:
    kernel, _packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    scheduler = deepcopy(_scheduler(kernel))
    scheduler["lease_history"][0]["status"] = "execution_started_spent"
    kernel.state.projections[scheduling.MULTICOMPONENT_SCHEDULER_STAGE] = (
        scheduling._refresh_scheduler(scheduler)
    )
    before = deepcopy(_scheduler(kernel))

    with pytest.raises(MulticomponentGraphSchedulingError):
        cancel_batch(
            state=kernel.state,
            batch_id=batch["batch_id"],
            action_ref={"action_id": "must-not-commit"},
            reason="forced-partial-cancellation",
        )

    assert _scheduler(kernel) == before


def test_child_two_private_materialization_failure_publishes_nothing_and_reuses_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, _packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    packet_digests = [
        item["input_packet_digest"] for item in batch["ordered_work_refs"]
    ]
    original = RunKernel._materialize_multicomponent_child_action
    calls = 0

    def fail_second(self: RunKernel, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RunKernelTransitionError("forced child two failure")
        return original(self, **kwargs)

    monkeypatch.setattr(
        RunKernel,
        "_materialize_multicomponent_child_action",
        fail_second,
    )

    with pytest.raises(RunKernelTransitionError, match="forced child two failure"):
        kernel.commit_multicomponent_batch_dispatch(
            batch_id=batch["batch_id"],
            packet_digests=packet_digests,
        )

    scheduler = _scheduler(kernel)
    assert scheduler["batch_history"][-1]["status"] == "cancelled_predispatch_returned"
    assert scheduler["compatibility_envelope"]["spent_units"] == 0
    assert scheduler["compatibility_envelope"]["reserved_units"] == 0
    assert not any(
        action.action_type
        in {
            ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_COMPONENT_DPRIME_EXECUTE,
        }
        for action in kernel.state.issued_actions.values()
    )

    monkeypatch.setattr(
        RunKernel,
        "_materialize_multicomponent_child_action",
        original,
    )
    later = kernel.grant_next_multicomponent_work_batch()
    assert [item["logical_evaluation_key"] for item in later["ordered_work_refs"]] == [
        item["logical_evaluation_key"] for item in batch["ordered_work_refs"]
    ]


def test_atomic_dispatch_publishes_all_children_only_with_commitment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, _packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    packet_digests = [
        item["input_packet_digest"] for item in batch["ordered_work_refs"]
    ]
    original_dispatch = scheduling.dispatch_batch
    checked_precommit = False

    def assert_no_children_before_commit(**kwargs):
        nonlocal checked_precommit
        checked_precommit = True
        assert not any(
            action.action_type
            is ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE
            for action in kernel.state.issued_actions.values()
        )
        return original_dispatch(**kwargs)

    monkeypatch.setattr(scheduling, "dispatch_batch", assert_no_children_before_commit)

    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=batch["batch_id"],
        packet_digests=packet_digests,
    )
    scheduler = _scheduler(kernel)

    assert checked_precommit is True
    assert len(actions) == 2
    assert [action.sequence for action in actions] == list(
        range(actions[0].sequence, actions[0].sequence + 2)
    )
    assert all(action.action_id in kernel.state.issued_actions for action in actions)
    assert kernel.state.next_observation_sequence == actions[0].sequence
    assert scheduler["batch_history"][-1]["status"] == "dispatch_committed"
    assert scheduler["compatibility_envelope"]["reserved_units"] == 0
    assert scheduler["compatibility_envelope"]["spent_units"] == 2
    assert scheduler["accounting_counters"]["dispatch_committed_unit_count"] == 2
    assert scheduler["private_descriptor_retained"] is False


def test_issued_dispatch_precommit_failure_closes_action_without_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, _packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    packet_digests = [
        item["input_packet_digest"] for item in batch["ordered_work_refs"]
    ]

    def fail_dispatch(**_kwargs):
        raise scheduling.MulticomponentGraphSchedulingError("forced reducer failure")

    monkeypatch.setattr(scheduling, "dispatch_batch", fail_dispatch)

    with pytest.raises(
        RunKernelTransitionError,
        match="batch dispatch failed before child publication",
    ):
        kernel.commit_multicomponent_batch_dispatch(
            batch_id=batch["batch_id"],
            packet_digests=packet_digests,
        )

    dispatch_actions = [
        action
        for action in kernel.state.issued_actions.values()
        if action.action_type is ActionType.MULTICOMPONENT_BATCH_DISPATCH
    ]
    assert len(dispatch_actions) == 1
    dispatch = dispatch_actions[0]
    assert kernel.state.action_statuses[dispatch.action_id] is RunStageStatus.FAILED
    assert dispatch.action_id in kernel.state.reduced_action_ids
    assert not any(
        action.action_type
        is ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE
        for action in kernel.state.issued_actions.values()
    )
    scheduler = _scheduler(kernel)
    assert scheduler["batch_history"][-1]["status"] == "cancelled_predispatch_returned"
    assert scheduler["compatibility_envelope"]["spent_units"] == 0
    assert scheduler["compatibility_envelope"]["reserved_units"] == 0
