"""Phase 5A product-path regressions for hosted component parallel dispatch.

Test classification:
- proof class: offline_product_path_proof
- validation bucket: phase_focus
- harness label: PRODUCT-PATH-REGRESSION
- runtime path: ordinary qualifying ``run_pipeline`` multi-component execution
- promotion posture: remain phase-focused; these are detailed concurrency custody tests
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from threading import Barrier, Event, Lock, get_ident
from threading import enumerate as enumerate_threads
from typing import Any

import pytest

import core.multicomponent_graph_scheduling as scheduling
import core.ordinary_multicomponent_synthesis_runtime as ordinary_runtime
import core.pipeline_orchestrator as orchestrator
from core.component_work_graph_v1 import COMPONENT_WORK_GRAPH_V1_STAGE
from core.cost_accounting import CostAccumulator
from core.multicomponent_component_admission import (
    MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
)
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
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    execute_prepared_multicomponent_transport,
    failed_unstarted_multicomponent_worker_result,
    prepare_multicomponent_transport_call,
    reduce_multicomponent_worker_result,
    safe_packet_digest,
)
from core.protocols import NullStatusWriter
from core.run_kernel import ActionType, RunKernel, RunKernelTransitionError, RunStageStatus
from core.strict_one_shot_model_transport import (
    PROVIDER_OPENAI,
    StrictOneShotModelTransportResult,
    normalize_canonical_model_provider,
    wrap_text_callable_as_strict_one_shot_transport,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_SEMANTIC,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)
from tests.test_multicomponent_graph_scheduling_leases_01 import (
    _scheduler,
    _scheduler_kernel,
)
from tests.test_multicomponent_ordinary_end_to_end_synthesis_01 import (
    NORTHSTAR_REPORT,
    NorthstarHarness,
)


def _redact_identity_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _redact_identity_fields(item)
            for key, item in value.items()
            if key not in {"run_id", "request_id", "action_id", "session_id"}
        }
    if isinstance(value, list):
        return [_redact_identity_fields(item) for item in value]
    return value


class SynchronizedHostedNorthstarHarness(NorthstarHarness):
    def __init__(
        self,
        tmp_path: Path,
        *,
        synchronize: bool,
        completion_order: str | None = None,
        fail_first_analyst: str | None = None,
    ) -> None:
        super().__init__(tmp_path)
        self.synchronize = synchronize
        self.completion_order = completion_order
        self.fail_first_analyst = fail_first_analyst
        self._call_lock = Lock()
        self._barriers = {
            ROLE_COMPONENT_ANALYST: Barrier(2),
            ROLE_COMPONENT_DPRIME: Barrier(2),
        }
        self.role_call_counts = {
            ROLE_COMPONENT_ANALYST: 0,
            ROLE_COMPONENT_DPRIME: 0,
        }
        self.role_active_counts = {
            ROLE_COMPONENT_ANALYST: 0,
            ROLE_COMPONENT_DPRIME: 0,
        }
        self.role_maximum_in_flight = {
            ROLE_COMPONENT_ANALYST: 0,
            ROLE_COMPONENT_DPRIME: 0,
        }
        self.role_thread_ids: dict[str, set[int]] = {
            ROLE_COMPONENT_ANALYST: set(),
            ROLE_COMPONENT_DPRIME: set(),
        }
        self._completion_events: dict[tuple[str, int], Event] = {}
        self.physical_completion_order: dict[str, list[int]] = {
            ROLE_COMPONENT_ANALYST: [],
            ROLE_COMPONENT_DPRIME: [],
        }

    @staticmethod
    def _role_for_system_prompt(system_prompt: str) -> str | None:
        return next(
            (
                candidate
                for candidate in (ROLE_COMPONENT_ANALYST, ROLE_COMPONENT_DPRIME)
                if system_prompt == ROLE_SYSTEM_PROMPTS[candidate]
            ),
            None,
        )

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        return super().ask_model(prompt, system_prompt, **kwargs)

    def strict_one_shot_smart_model_transport(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> Any:
        from core.cost_accounting import estimate_tokens
        from core.strict_one_shot_model_transport import (
            BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED,
            BLOCKED_STRICT_ONE_SHOT_PROVIDER_UNSUPPORTED,
            PROVIDER_UNSUPPORTED,
        )

        provider = normalize_canonical_model_provider(kwargs.get("provider") or "OpenAI")
        model = str(kwargs.get("model") or "gpt-5.4")
        if provider == PROVIDER_UNSUPPORTED:
            return StrictOneShotModelTransportResult(
                return_code=2,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_PROVIDER_UNSUPPORTED,
                detail="Configured SmartModel provider is not supported by the strict one-shot transport.",
                canonical_provider=PROVIDER_UNSUPPORTED,
                configured_model=model,
                provider_request_attempt_count=0,
                provider_request_succeeded=False,
                provider_request_failed=False,
            )
        try:
            text = self._strict_role_text(prompt, system_prompt, **kwargs)
        except Exception as exc:  # noqa: BLE001 - bounded fake transport failure.
            return StrictOneShotModelTransportResult(
                return_code=2,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED,
                detail=f"Injected strict one-shot failure: {type(exc).__name__}.",
                canonical_provider=provider,
                configured_model=model,
                provider_request_attempt_count=1,
                provider_request_succeeded=False,
                provider_request_failed=True,
            )
        return StrictOneShotModelTransportResult(
            return_code=0,
            output_text=text,
            canonical_provider=provider,
            configured_model=model,
            provider_request_attempt_count=1,
            provider_request_succeeded=True,
            provider_request_failed=False,
            provider_response_received=True,
            input_tokens=estimate_tokens(prompt) + estimate_tokens(system_prompt),
            output_tokens=estimate_tokens(text),
            usage_observed=False,
            usage_estimated=True,
        )

    def _strict_role_text(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        role = self._role_for_system_prompt(system_prompt)
        if role is None:
            return NorthstarHarness.ask_model(self, prompt, system_prompt, **kwargs)
        with self._call_lock:
            call_index = self.role_call_counts[role]
            self.role_call_counts[role] += 1
            self.role_active_counts[role] += 1
            self.role_maximum_in_flight[role] = max(
                self.role_maximum_in_flight[role],
                self.role_active_counts[role],
            )
            self.role_thread_ids[role].add(get_ident())
        try:
            if self.synchronize and call_index < 4:
                self._barriers[role].wait(timeout=5)
            pair_index = call_index // 2
            event = self._completion_events.setdefault((role, pair_index), Event())
            wait_for_sibling = (
                self.completion_order == "second_first" and call_index % 2 == 0
            ) or (
                self.completion_order == "first_first" and call_index % 2 == 1
            )
            if self.synchronize and call_index < 4 and wait_for_sibling:
                if not event.wait(timeout=5):
                    raise AssertionError("forced completion ordering timed out")
            if role == ROLE_COMPONENT_ANALYST and call_index == 0:
                if self.fail_first_analyst == "transport":
                    raise RuntimeError("bounded injected transport failure")
                if self.fail_first_analyst == "malformed":
                    result = "not-json"
                else:
                    result = NorthstarHarness.ask_model(self, prompt, system_prompt, **kwargs)
            else:
                result = NorthstarHarness.ask_model(self, prompt, system_prompt, **kwargs)
            with self._call_lock:
                self.physical_completion_order[role].append(call_index)
            if self.synchronize and call_index < 4 and not wait_for_sibling:
                event.set()
            return result
        finally:
            with self._call_lock:
                self.role_active_counts[role] -= 1


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
        ("unsupported-provider", "unsupported", BACKEND_CONSERVATIVE_UNKNOWN, 1),
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
    two_active = deepcopy(scheduler)
    two_active.pop("scheduler_digest")
    two_active["lease_history"] = [
        {
            "status": "granted_reserved",
            "work": {"role": ROLE_COMPONENT_ANALYST},
        },
        {
            "status": "granted_reserved",
            "work": {"role": ROLE_COMPONENT_ANALYST},
        },
    ]
    two_active["compatibility_envelope"]["remaining_units"] -= 2
    with pytest.raises(MulticomponentGraphSchedulingError):
        scheduling._refresh_scheduler(two_active)


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
    retained_scheduler_text = json.dumps(scheduler, sort_keys=True)
    assert "A bounded fixture fact" not in retained_scheduler_text
    assert NORTHSTAR_REPORT not in retained_scheduler_text
    for flag in (
        "raw_prompt_retained",
        "raw_model_response_retained",
        "raw_provider_payload_retained",
        "private_descriptor_retained",
        "prepared_transport_retained",
        "worker_result_retained",
        "private_log_retained",
        "full_trace_retained",
    ):
        assert scheduler[flag] is False


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


def _run_hosted_product(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    synchronize: bool,
    completion_order: str | None = None,
    fail_first_analyst: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
) -> tuple[Any, RunKernel, SynchronizedHostedNorthstarHarness, dict[str, Any]]:
    scrub_offline_runtime(monkeypatch)
    harness = SynchronizedHostedNorthstarHarness(
        tmp_path,
        synchronize=synchronize,
        completion_order=completion_order,
        fail_first_analyst=fail_first_analyst,
    )
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_SEMANTIC,),
    )
    config = offline_balanced_run_config(
        query=harness.query,
        current_date="2026-07-12",
        session_id=session_id or f"phase5a-{provider}-session",
        run_id=run_id or f"phase5a-{provider}-run",
    )
    config.smart_provider = provider
    outcome = orchestrator.run_pipeline(
        config,
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    return outcome, captured["semantic_run_kernel"], harness, captured


def test_openai_ordinary_product_overlaps_analyst_and_dprime_at_width_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_thread_id = get_ident()
    admission_thread_ids: list[int] = []
    authorize_thread_ids: list[int] = []
    reduce_thread_ids: list[int] = []
    original_admission = ordinary_runtime.execute_multicomponent_component_admission
    original_authorize = RunKernel.authorize
    original_reduce = RunKernel.reduce

    def record_admission_thread(**kwargs):
        admission_thread_ids.append(get_ident())
        return original_admission(**kwargs)

    def record_authorize_thread(self: RunKernel, **kwargs):
        authorize_thread_ids.append(get_ident())
        return original_authorize(self, **kwargs)

    def record_reduce_thread(self: RunKernel, observation):
        reduce_thread_ids.append(get_ident())
        return original_reduce(self, observation)

    monkeypatch.setattr(
        ordinary_runtime,
        "execute_multicomponent_component_admission",
        record_admission_thread,
    )
    monkeypatch.setattr(RunKernel, "authorize", record_authorize_thread)
    monkeypatch.setattr(RunKernel, "reduce", record_reduce_thread)
    outcome, kernel, harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=True,
    )
    scheduler = _scheduler(kernel)
    counters = scheduler["accounting_counters"]

    assert outcome.report == NORTHSTAR_REPORT
    assert scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION
    assert scheduler["backend_class"] == BACKEND_HOSTED_API
    assert scheduler["effective_width"] == 2
    assert {
        call["provider"]
        for call in harness.model_calls
        if call["system_prompt"] in ROLE_SYSTEM_PROMPTS.values()
    } == {"OpenAI"}
    assert harness.role_maximum_in_flight[ROLE_COMPONENT_ANALYST] == 2
    assert harness.role_call_counts[ROLE_COMPONENT_ANALYST] == 5
    assert harness.role_maximum_in_flight[ROLE_COMPONENT_DPRIME] == 2
    assert counters["maximum_observed_in_flight_transports"] == 2
    assert counters["physical_overlap_observed"] is True
    component_batch_roles = [
        batch["ordered_work_refs"][0]["role"]
        for batch in scheduler["batch_history"]
        if batch["ordered_work_refs"][0]["target_kind"] == "component"
    ]
    assert component_batch_roles[:6] == [
        ROLE_COMPONENT_ANALYST,
        ROLE_COMPONENT_DPRIME,
        ROLE_COMPONENT_ANALYST,
        ROLE_COMPONENT_DPRIME,
        ROLE_COMPONENT_ANALYST,
        ROLE_COMPONENT_DPRIME,
    ]
    analyst_batch_sizes = [
        len(batch["ordered_work_refs"])
        for batch in scheduler["batch_history"]
        if batch["parallel_class"] == "parallel_initial_component_analyst"
    ]
    dprime_batch_sizes = [
        len(batch["ordered_work_refs"])
        for batch in scheduler["batch_history"]
        if batch["parallel_class"] == "parallel_initial_component_dprime"
    ]
    assert analyst_batch_sizes == [2, 2, 1]
    assert dprime_batch_sizes == [2, 2, 1]
    assert all(
        len({item["role"] for item in batch["ordered_work_refs"]}) == 1
        for batch in scheduler["batch_history"]
    )
    assert counters["dispatch_committed_unit_count"] == counters[
        "transport_submission_count"
    ]
    assert counters["transport_submission_count"] == counters[
        "transport_started_count"
    ]
    assert counters["transport_started_count"] == counters[
        "transport_completed_count"
    ]
    assert counters["transport_completed_count"] == counters[
        "successful_artifact_count"
    ]
    assert all(
        thread_id != main_thread_id
        for thread_id in (
            harness.role_thread_ids[ROLE_COMPONENT_ANALYST]
            | harness.role_thread_ids[ROLE_COMPONENT_DPRIME]
        )
    )
    assert admission_thread_ids
    assert set(admission_thread_ids) == {main_thread_id}
    assert set(authorize_thread_ids) == {main_thread_id}
    assert set(reduce_thread_ids) == {main_thread_id}
    assert not any(
        thread.name.startswith("scryraven-component-wave")
        for thread in enumerate_threads()
    )


@pytest.mark.parametrize(
    ("provider", "backend"),
    [
        ("Local (LM Studio)", BACKEND_LOCAL_OPENAI_COMPATIBLE),
    ],
)
def test_local_ordinary_product_uses_v2_serial_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    backend: str,
) -> None:
    outcome, kernel, harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider=provider,
        synchronize=False,
    )
    scheduler = _scheduler(kernel)

    assert outcome.report == NORTHSTAR_REPORT
    assert scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION
    assert scheduler["backend_class"] == backend
    assert scheduler["effective_width"] == 1
    assert scheduler["maximum_active_physical_leases"] == 1
    assert scheduler["accounting_counters"][
        "maximum_observed_in_flight_transports"
    ] == 1
    assert harness.role_maximum_in_flight[ROLE_COMPONENT_ANALYST] == 1
    assert harness.role_maximum_in_flight[ROLE_COMPONENT_DPRIME] == 1
    assert scheduler["local_parallelism_enabled"] is False


def test_unsupported_ordinary_product_uses_width_1_safe_blocked_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, kernel, harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="unsupported-provider",
        synchronize=False,
    )
    scheduler = _scheduler(kernel)
    counters = scheduler["accounting_counters"]

    assert outcome.report != NORTHSTAR_REPORT
    assert "ScryRaven could not complete" in outcome.report or outcome.report
    assert scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION
    assert scheduler["configured_provider_class"] == "unsupported"
    assert scheduler["backend_class"] == BACKEND_CONSERVATIVE_UNKNOWN
    assert scheduler["effective_width"] == 1
    assert scheduler["maximum_active_physical_leases"] == 1
    assert int(counters.get("provider_request_attempt_count") or 0) == 0
    assert int(counters.get("failed_transport_count") or 0) >= 1
    assert harness.role_maximum_in_flight[ROLE_COMPONENT_ANALYST] <= 1
    assert scheduler["local_parallelism_enabled"] is False


def test_out_of_order_physical_completion_keeps_canonical_state_equivalent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second_first_dir = tmp_path / "second-first"
    first_first_dir = tmp_path / "first-first"
    second_first_dir.mkdir()
    first_first_dir.mkdir()
    with monkeypatch.context() as second_first_patch:
        first_outcome, first_kernel, first_harness, _captured = _run_hosted_product(
            tmp_path=second_first_dir,
            monkeypatch=second_first_patch,
            provider="OpenAI",
            synchronize=True,
            completion_order="second_first",
        )
    with monkeypatch.context() as first_first_patch:
        second_outcome, second_kernel, second_harness, _captured = _run_hosted_product(
            tmp_path=first_first_dir,
            monkeypatch=first_first_patch,
            provider="OpenAI",
            synchronize=True,
            completion_order="first_first",
        )

    assert first_harness.physical_completion_order[ROLE_COMPONENT_ANALYST][:2] == [
        1,
        0,
    ]
    assert second_harness.physical_completion_order[ROLE_COMPONENT_ANALYST][:2] == [
        0,
        1,
    ]
    assert first_harness.physical_completion_order[ROLE_COMPONENT_DPRIME][:2] == [
        1,
        0,
    ]
    assert second_harness.physical_completion_order[ROLE_COMPONENT_DPRIME][:2] == [
        0,
        1,
    ]
    assert first_outcome.report == second_outcome.report == NORTHSTAR_REPORT
    assert first_kernel.state.projections[COMPONENT_WORK_GRAPH_V1_STAGE] == (
        second_kernel.state.projections[COMPONENT_WORK_GRAPH_V1_STAGE]
    )
    assert first_kernel.state.projections[MULTICOMPONENT_COMPONENT_ADMISSION_STAGE] == (
        second_kernel.state.projections[MULTICOMPONENT_COMPONENT_ADMISSION_STAGE]
    )
    assert _scheduler(first_kernel)["accounting_counters"] == _scheduler(second_kernel)[
        "accounting_counters"
    ]


def _assert_failed_batch_drained(kernel: RunKernel) -> dict[str, Any]:
    scheduler = _scheduler(kernel)
    assert scheduler["status"] == "blocked_required_work_failed"
    assert scheduler["active_physical_lease_count"] == 0
    assert all(
        action.action_id in kernel.state.reduced_action_ids
        for action in kernel.state.issued_actions.values()
        if action.action_type
        in {
            ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_COMPONENT_DPRIME_EXECUTE,
        }
    )
    return scheduler


def test_executor_construction_failure_spends_and_drains_without_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_executor(**_kwargs):
        raise RuntimeError("bounded injected executor failure")

    monkeypatch.setattr(ordinary_runtime, "ThreadPoolExecutor", fail_executor)
    outcome, kernel, _harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=False,
    )
    scheduler = _assert_failed_batch_drained(kernel)
    counters = scheduler["accounting_counters"]

    assert outcome.report != NORTHSTAR_REPORT
    assert counters["dispatch_committed_unit_count"] == 2
    assert counters["transport_submission_count"] == 0
    assert counters["transport_started_count"] == 0
    assert counters["failed_submission_count"] == 2
    assert counters["successful_artifact_count"] == 0


def test_second_submission_failure_drains_submitted_sibling_and_starts_no_new_wave(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_executor = ordinary_runtime.ThreadPoolExecutor

    class FailSecondSubmitExecutor:
        def __init__(self, **kwargs: Any) -> None:
            self.inner = real_executor(**kwargs)
            self.submission_count = 0

        def submit(self, *args: Any, **kwargs: Any):
            self.submission_count += 1
            if self.submission_count == 2:
                raise RuntimeError("bounded injected submission failure")
            return self.inner.submit(*args, **kwargs)

        def shutdown(self, **kwargs: Any) -> None:
            self.inner.shutdown(**kwargs)

    monkeypatch.setattr(
        ordinary_runtime,
        "ThreadPoolExecutor",
        FailSecondSubmitExecutor,
    )
    _outcome, kernel, _harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=False,
    )
    scheduler = _assert_failed_batch_drained(kernel)
    counters = scheduler["accounting_counters"]

    assert counters["dispatch_committed_unit_count"] == 2
    assert counters["transport_submission_count"] == 1
    assert counters["transport_started_count"] == 1
    assert counters["transport_completed_count"] == 1
    assert counters["successful_artifact_count"] == 1
    assert counters["failed_submission_count"] == 1
    assert counters["batch_count"] == 1


@pytest.mark.parametrize("failure_mode", ["transport", "malformed"])
def test_required_worker_failure_drains_sibling_before_terminalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    _outcome, kernel, harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=True,
        fail_first_analyst=failure_mode,
    )
    scheduler = _assert_failed_batch_drained(kernel)
    counters = scheduler["accounting_counters"]

    assert harness.role_maximum_in_flight[ROLE_COMPONENT_ANALYST] == 2
    assert harness.role_call_counts[ROLE_COMPONENT_ANALYST] == 2
    assert counters["dispatch_committed_unit_count"] == 2
    assert counters["transport_submission_count"] == 2
    assert counters["transport_started_count"] == 2
    assert counters["transport_completed_count"] == 2
    assert counters["successful_artifact_count"] == 1
    assert counters["failed_transport_count"] == 1
    assert counters["batch_count"] == 1
    assert scheduler["batch_history"][-1]["terminal_settlement_summary"][
        "all_leases_terminal"
    ] is True


def test_postdispatch_authority_change_rejects_late_batch_results_as_stale() -> None:
    kernel, packets_by_component = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    scheduler = _scheduler(kernel)
    leases_by_id = {
        item["lease_id"]: item for item in scheduler["lease_history"]
    }
    leases = [
        leases_by_id[item["lease_id"]] for item in batch["ordered_lease_refs"]
    ]
    packets = [
        packets_by_component[lease["work"]["component_id"]] for lease in leases
    ]
    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=batch["batch_id"],
        packet_digests=[safe_packet_digest(packet) for packet in packets],
    )
    prepared = [
        prepare_multicomponent_transport_call(
            action=action,
            input_packet=packet,
            strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
                lambda *_args, **_kwargs: (
                    '{"claim_text":"Late bounded claim","support_status":"supported"}'
                ),
                canonical_provider="OpenAI",
                model="gpt-5.4",
            ),
            clean_json_response=lambda value: value,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
        )
        for action, packet in zip(actions, packets, strict=True)
    ]
    results = [execute_prepared_multicomponent_transport(item) for item in prepared]
    changed = dict(kernel.state.initial_answer_contract)
    changed["accepted_contract_digest"] = "changed-after-batch-dispatch"
    kernel.state.initial_answer_contract = changed

    artifacts = [
        reduce_multicomponent_worker_result(
            run_kernel=kernel,
            action=action,
            result=result,
            observed_batch_max_in_flight=2,
        )
        for action, result in zip(actions, results, strict=True)
    ]
    scheduler = _assert_failed_batch_drained(kernel)

    assert artifacts == [None, None]
    assert scheduler["compatibility_envelope"]["spent_units"] == 2
    assert scheduler["accounting_counters"]["stale_result_count"] == 2
    assert scheduler["accounting_counters"]["successful_artifact_count"] == 0


def _cost_snapshot_subset(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_calls": int(snapshot.get("total_calls") or 0),
        "calls_by_phase": dict(snapshot.get("calls_by_phase") or {}),
        "cost_by_model": dict(snapshot.get("cost_by_model") or {}),
        "total_input_tokens": int(snapshot.get("total_input_tokens") or 0),
        "total_output_tokens": int(snapshot.get("total_output_tokens") or 0),
    }


def test_ordinary_hosted_run_records_phase5a_costs_in_run_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from threading import get_ident

    main_thread = get_ident()
    record_threads: list[int] = []
    original_record = CostAccumulator.record_model_call

    def _spy(self: CostAccumulator, **kwargs: Any) -> None:
        record_threads.append(get_ident())
        return original_record(self, **kwargs)

    monkeypatch.setattr(CostAccumulator, "record_model_call", _spy)
    outcome, kernel, _harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=False,
    )
    scheduler = _scheduler(kernel)
    phase5a_calls = int(scheduler["accounting_counters"]["provider_request_attempt_count"])
    snapshot = outcome.cost_snapshot
    assert phase5a_calls > 0
    assert int(snapshot["calls_by_phase"].get("model") or 0) >= phase5a_calls
    assert "offline-fake-smart-model" in snapshot["cost_by_model"]
    assert int(snapshot["total_input_tokens"]) > 0
    assert int(snapshot["total_output_tokens"]) > 0
    assert all(thread_id == main_thread for thread_id in record_threads)
    privacy_blob = json.dumps(
        {
            "snapshot": snapshot,
            "scheduler": _redact_identity_fields(scheduler),
        },
        sort_keys=True,
        default=str,
    )
    for marker in ("sk-", "OPENAI_API_KEY", "Bearer "):
        assert marker not in privacy_blob
    assert '"raw_prompt_retained": true' not in privacy_blob.casefold()
    assert '"raw_model_response_retained": true' not in privacy_blob.casefold()
    assert '"raw_provider_payload_retained": true' not in privacy_blob.casefold()
    assert '"credential_values_retained": true' not in privacy_blob.casefold()


def test_width_one_and_width_two_produce_equivalent_aggregate_cost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared_session = "phase5a-width-eq-session"
    shared_run = "phase5a-width-eq-run"
    width_two, kernel_two, _h2, _c2 = _run_hosted_product(
        tmp_path=tmp_path / "w2",
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=True,
        session_id=shared_session,
        run_id=shared_run,
    )
    width_one, kernel_one, _h1, _c1 = _run_hosted_product(
        tmp_path=tmp_path / "w1",
        monkeypatch=monkeypatch,
        provider="lm_studio",
        synchronize=False,
        session_id=shared_session,
        run_id=shared_run,
    )
    assert int(_scheduler(kernel_two)["effective_width"]) == 2
    assert int(_scheduler(kernel_one)["effective_width"]) == 1
    assert int(
        _scheduler(kernel_two)["accounting_counters"]["provider_request_attempt_count"]
    ) == int(
        _scheduler(kernel_one)["accounting_counters"]["provider_request_attempt_count"]
    )
    left = _cost_snapshot_subset(width_two.cost_snapshot)
    right = _cost_snapshot_subset(width_one.cost_snapshot)
    assert left["calls_by_phase"].get("model") == right["calls_by_phase"].get("model")
    assert left["cost_by_model"].get("offline-fake-smart-model") == right[
        "cost_by_model"
    ].get("offline-fake-smart-model")
    assert left["total_input_tokens"] == right["total_input_tokens"]
    assert left["total_output_tokens"] == right["total_output_tokens"]


def test_reversed_completion_order_preserves_cost_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, _k1, _h1, _c1 = _run_hosted_product(
        tmp_path=tmp_path / "first",
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=True,
        completion_order="first_first",
    )
    second, _k2, _h2, _c2 = _run_hosted_product(
        tmp_path=tmp_path / "second",
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=True,
        completion_order="second_first",
    )
    assert _cost_snapshot_subset(first.cost_snapshot) == _cost_snapshot_subset(
        second.cost_snapshot
    )


def test_malformed_response_bearing_result_records_one_cost_call() -> None:
    from core.cost_accounting import estimate_tokens
    from core.ordinary_multicomponent_synthesis_runtime import (
        _record_phase5a_model_costs_on_main_thread,
    )

    kernel, packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    leases = [
        item
        for item in _scheduler(kernel)["lease_history"]
        if item.get("batch_id") == batch.get("batch_id")
    ]
    digests = [
        safe_packet_digest(packets[str(lease["work"]["component_id"])])
        for lease in leases
    ]
    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=digests,
    )
    transport = wrap_text_callable_as_strict_one_shot_transport(
        lambda *_a, **_k: "not-json",
        canonical_provider="OpenAI",
        model="gpt-5.4",
    )
    prepared = [
        prepare_multicomponent_transport_call(
            action=action,
            input_packet=packets[str(lease["work"]["component_id"])],
            strict_one_shot_transport=transport,
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
        )
        for action, lease in zip(actions, leases, strict=True)
    ]
    results = [execute_prepared_multicomponent_transport(item) for item in prepared]
    assert all(result.provider_response_received for result in results)
    assert all(result.normalized_semantic_output is None for result in results)
    accumulator = CostAccumulator()
    drive_context = {
        "runtime_scope": {"accumulator": accumulator, "smart_model": "gpt-5.4"},
        "cost_recorded_child_action_ids": set(),
    }
    _record_phase5a_model_costs_on_main_thread(
        drive_context=drive_context,
        actions=actions,
        results=results,
        configured_model="gpt-5.4",
    )
    # Idempotent: second pass must not double-count.
    _record_phase5a_model_costs_on_main_thread(
        drive_context=drive_context,
        actions=actions,
        results=results,
        configured_model="gpt-5.4",
    )
    snapshot = accumulator.snapshot()
    assert snapshot["calls_by_phase"]["model"] == len(actions)
    assert snapshot["total_calls"] == len(actions)
    assert snapshot["total_input_tokens"] > 0
    assert snapshot["total_output_tokens"] == len(actions) * estimate_tokens("not-json")


def test_empty_and_artifact_failure_still_record_response_bearing_cost() -> None:
    from core.ordinary_multicomponent_synthesis_runtime import (
        _record_phase5a_model_costs_on_main_thread,
    )
    from core.strict_one_shot_model_transport import (
        BLOCKED_STRICT_ONE_SHOT_OUTPUT_EMPTY,
    )

    kernel, packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    leases = [
        item
        for item in _scheduler(kernel)["lease_history"]
        if item.get("batch_id") == batch.get("batch_id")
    ]
    digests = [
        safe_packet_digest(packets[str(lease["work"]["component_id"])])
        for lease in leases
    ]
    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=digests,
    )
    empty_result = StrictOneShotModelTransportResult(
        return_code=2,
        failure_kind=BLOCKED_STRICT_ONE_SHOT_OUTPUT_EMPTY,
        detail="empty",
        canonical_provider=PROVIDER_OPENAI,
        configured_model="gpt-5.4",
        provider_request_attempt_count=1,
        provider_request_failed=True,
        provider_response_received=True,
        input_tokens=12,
        output_tokens=0,
        usage_observed=False,
        usage_estimated=True,
    )

    def _empty_transport(*_a: Any, **_k: Any) -> StrictOneShotModelTransportResult:
        return empty_result

    prepared = prepare_multicomponent_transport_call(
        action=actions[0],
        input_packet=packets[str(leases[0]["work"]["component_id"])],
        strict_one_shot_transport=_empty_transport,
        clean_json_response=None,
        provider="OpenAI",
        model="gpt-5.4",
        use_reasoning=False,
    )
    result = execute_prepared_multicomponent_transport(prepared)
    assert result.provider_response_received is True
    assert result.normalized_semantic_output is None
    accumulator = CostAccumulator()
    drive_context = {
        "runtime_scope": {"accumulator": accumulator, "smart_model": "gpt-5.4"},
        "cost_recorded_child_action_ids": set(),
    }
    _record_phase5a_model_costs_on_main_thread(
        drive_context=drive_context,
        actions=[actions[0]],
        results=[result],
        configured_model="gpt-5.4",
    )
    assert accumulator.snapshot()["calls_by_phase"]["model"] == 1
    assert accumulator.snapshot()["total_input_tokens"] == 12


def test_executor_submission_and_no_response_failures_add_zero_model_cost() -> None:
    from core.ordinary_multicomponent_synthesis_runtime import (
        _record_phase5a_model_costs_on_main_thread,
    )

    kernel, packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    leases = [
        item
        for item in _scheduler(kernel)["lease_history"]
        if item.get("batch_id") == batch.get("batch_id")
    ]
    digests = [
        safe_packet_digest(packets[str(lease["work"]["component_id"])])
        for lease in leases
    ]
    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=digests,
    )
    transport = wrap_text_callable_as_strict_one_shot_transport(
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
        canonical_provider="OpenAI",
        model="gpt-5.4",
    )
    prepared_calls = [
        prepare_multicomponent_transport_call(
            action=action,
            input_packet=packets[str(lease["work"]["component_id"])],
            strict_one_shot_transport=transport,
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
        )
        for action, lease in zip(actions, leases, strict=True)
    ]
    unstarted = [
        failed_unstarted_multicomponent_worker_result(
            prepared,
            failure_kind="executor_initialization_failure",
        )
        for prepared in prepared_calls
    ]
    attempted = [
        execute_prepared_multicomponent_transport(prepared)
        for prepared in prepared_calls
    ]
    assert all(item.provider_request_attempt_count == 0 for item in unstarted)
    assert all(item.provider_response_received is False for item in unstarted)
    assert all(item.provider_request_attempt_count == 1 for item in attempted)
    assert all(item.provider_response_received is False for item in attempted)
    accumulator = CostAccumulator()
    drive_context = {
        "runtime_scope": {"accumulator": accumulator, "smart_model": "gpt-5.4"},
        "cost_recorded_child_action_ids": set(),
    }
    _record_phase5a_model_costs_on_main_thread(
        drive_context=drive_context,
        actions=actions,
        results=unstarted,
        configured_model="gpt-5.4",
    )
    assert accumulator.snapshot()["total_calls"] == 0
    drive_context["cost_recorded_child_action_ids"] = set()
    _record_phase5a_model_costs_on_main_thread(
        drive_context=drive_context,
        actions=actions,
        results=attempted,
        configured_model="gpt-5.4",
    )
    assert accumulator.snapshot()["total_calls"] == 0


def test_workers_never_receive_cost_accumulator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_in_worker: list[bool] = []
    original = ordinary_runtime.execute_prepared_multicomponent_transport

    def _wrapped(prepared):
        transport = prepared.strict_one_shot_transport
        owns_accumulator = any(
            "cost_accumulator" in name or name == "accumulator"
            for name in dir(transport)
        )
        seen_in_worker.append(owns_accumulator)
        assert not hasattr(prepared, "cost_accumulator")
        assert "accumulator" not in repr(prepared).casefold()
        return original(prepared)

    monkeypatch.setattr(
        ordinary_runtime,
        "execute_prepared_multicomponent_transport",
        _wrapped,
    )
    monkeypatch.setattr(
        "core.ordinary_multicomponent_synthesis_runtime.execute_prepared_multicomponent_transport",
        _wrapped,
    )
    outcome, _kernel, _harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=True,
    )
    assert "Northstar" in outcome.report
    assert seen_in_worker
    assert all(flag is False for flag in seen_in_worker)
