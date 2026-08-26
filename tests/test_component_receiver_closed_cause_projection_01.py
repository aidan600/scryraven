"""Focused offline proof for closed SearchOS component-receiver causes."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

import core.multicomponent_graph_scheduling as scheduling
import core.ordinary_multicomponent_synthesis_runtime as multicomponent_runtime
from core.multicomponent_graph_scheduling import (
    COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
    MULTICOMPONENT_SCHEDULER_STAGE,
    component_identity_digest,
    component_receiver_cause_from_current_scheduler_failure,
    component_receiver_exact_evidence_or_custody_cause,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    execute_multicomponent_role_call,
)
from core.ordinary_multicomponent_synthesis_runtime import (
    OrdinaryMulticomponentRuntimeError,
    _selected_lane_evidence_or_custody_failure_cause,
)
from core.searchos_slice_a_product_runtime import (
    build_bounded_searchos_n1_causal_projection,
)
from tests.test_multicomponent_graph_scheduling_leases_01 import (
    _role_kwargs,
    _scheduler_kernel,
)


def _receiver_trace(
    *,
    cause: dict[str, str] | None = None,
    receiver_failed: bool = True,
    posture: str = "semantically_handed_off",
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "slot_postures": {"slot-1": posture},
        "semantic_outcomes_by_slot": {
            "slot-1": {
                "semantic_handoff_ref": {},
                "component_analyst_case_ref": {},
                "semantic_admission_outcome_ref": {},
                "semantic_admission_status": "not_admitted",
                "searchos_handoff_material_consumed": False,
            }
        },
        "readiness_projection": {
            "required_slot_count": 1,
            "optional_slot_count": 0,
            "all_required_slots_slice_a_ready": False,
            "slot_records": [
                {
                    "slot_ref": {
                        "slot_id": "slot-1",
                        "slot_digest": "slot-digest-1",
                        "component_id": "component-a",
                        "source_obligation_id": "obligation-a",
                    },
                    "requirement_posture": "required",
                    "support_kind": "official_current",
                    "latest_judgment_posture": posture,
                    "latest_judgment_reason": "none",
                    "judgment_call_count": 1,
                    "action_history": [],
                    "custody_refs": [],
                    "semantic_handoff_ref": {},
                    "slice_a_ready": False,
                }
            ],
        },
    }
    if receiver_failed:
        trace["component_receiver_failure"] = "OrdinaryMulticomponentRuntimeError"
    if cause is not None:
        trace["component_receiver_cause"] = dict(cause)
    return trace


def _n2_receiver_trace(*, cause: dict[str, str]) -> dict[str, Any]:
    trace = _receiver_trace(cause=cause)
    trace["slot_postures"]["slot-2"] = "semantically_handed_off"
    trace["semantic_outcomes_by_slot"]["slot-2"] = {
        "semantic_handoff_ref": {},
        "component_analyst_case_ref": {},
        "semantic_admission_outcome_ref": {},
        "semantic_admission_status": "not_admitted",
        "searchos_handoff_material_consumed": False,
    }
    trace["readiness_projection"]["required_slot_count"] = 2
    trace["readiness_projection"]["slot_records"].append(
        {
            "slot_ref": {
                "slot_id": "slot-2",
                "slot_digest": "slot-digest-2",
                "component_id": "component-b",
                "source_obligation_id": "obligation-b",
            },
            "requirement_posture": "required",
            "support_kind": "official_current",
            "latest_judgment_posture": "semantically_handed_off",
            "latest_judgment_reason": "none",
            "judgment_call_count": 1,
            "action_history": [],
            "custody_refs": [],
            "semantic_handoff_ref": {},
            "slice_a_ready": False,
        }
    )
    return trace


@pytest.mark.parametrize(
    ("failure_code", "component_id"),
    [
        ("no_bindable_passage", "component-missing"),
        ("source_obligation_custody_not_current", "component-noncurrent"),
    ],
)
def test_selected_lane_single_component_evidence_causes_are_exact(
    failure_code: str,
    component_id: str,
) -> None:
    cause = _selected_lane_evidence_or_custody_failure_cause(
        {component_id: failure_code}
    )

    assert cause == {
        "schema_version": COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
        "cause_status": "exact",
        "cause_transition": "evidence_selection_or_custody",
        "component_identity_digest": component_identity_digest(component_id),
        "failure_code": failure_code,
    }
    assert component_id not in json.dumps(cause, sort_keys=True)


def test_selected_lane_multiple_missing_components_do_not_guess_an_origin() -> None:
    cause = _selected_lane_evidence_or_custody_failure_cause(
        {
            "component-a": "no_bindable_passage",
            "component-b": "source_obligation_custody_not_current",
        }
    )

    assert cause == {
        "schema_version": COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
        "cause_status": "other_safe",
        "cause_transition": "evidence_selection_or_custody",
        "failure_code": "other_safe",
    }


def _failed_two_component_scheduler() -> tuple[dict[str, Any], str, str, str, str]:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = dict(lease["work"])
    failed_component_id = str(work["component_id"])
    other_component_id = next(
        component_id
        for component_id in packets
        if component_id != failed_component_id
    )

    def transport_failure(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("private scheduler transport failure")

    with pytest.raises(Exception):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=str(work["role"]),
            input_packet=packets[failed_component_id],
            logical_evaluation_key=str(work["logical_evaluation_key"]),
            lease_id=str(lease["lease_id"]),
            **_role_kwargs(ask_model=transport_failure),
        )
    scheduler = dict(kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE])
    assert scheduler["status"] == "blocked_required_work_failed"
    return (
        scheduler,
        kernel.state.run_id,
        kernel.state.request_id,
        failed_component_id,
        other_component_id,
    )


def test_scheduler_component_failure_correlates_the_exact_component_in_n2() -> None:
    (
        scheduler,
        run_id,
        request_id,
        failed_component_id,
        other_component_id,
    ) = _failed_two_component_scheduler()
    cause = component_receiver_cause_from_current_scheduler_failure(
        state=scheduler,
        expected_run_id=run_id,
        expected_request_id=request_id,
    )

    assert cause == {
        "schema_version": COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
        "cause_status": "scheduler_correlated",
        "cause_transition": "component_analyst_work",
        "component_identity_digest": component_identity_digest(failed_component_id),
        "failure_code": "model_transport_failure",
        "role": ROLE_COMPONENT_ANALYST,
        "failure_kind": "model_transport_failure",
        "settlement_posture": "failed_spent",
    }
    assert cause["component_identity_digest"] != component_identity_digest(
        other_component_id
    )
    assert failed_component_id not in json.dumps(cause, sort_keys=True)


def test_receiver_wrapper_threads_the_scheduler_cause_without_exception_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, packets = _scheduler_kernel()
    failed_component: dict[str, str] = {}

    def transport_failure(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("private scheduler transport failure")

    def block_selected_lane(*_args: Any, **_kwargs: Any) -> None:
        lease = kernel.grant_next_multicomponent_work_lease()
        work = dict(lease["work"])
        failed_component["id"] = str(work["component_id"])
        with pytest.raises(Exception):
            execute_multicomponent_role_call(
                run_kernel=kernel,
                role=str(work["role"]),
                input_packet=packets[str(work["component_id"])],
                logical_evaluation_key=str(work["logical_evaluation_key"]),
                lease_id=str(lease["lease_id"]),
                **_role_kwargs(ask_model=transport_failure),
            )
        raise multicomponent_runtime._ScheduledSemanticWorkBlocked("private text")

    monkeypatch.setattr(
        multicomponent_runtime,
        "_selected_multicomponent_contract",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        multicomponent_runtime,
        "_execute_selected_lane",
        block_selected_lane,
    )

    with pytest.raises(OrdinaryMulticomponentRuntimeError) as raised:
        multicomponent_runtime.execute_ordinary_semantic_or_multicomponent_handoff_from_scope(
            kernel,
            {"query": "offline fixture"},
            allow_searchos_component_receiver=True,
        )

    assert raised.value.component_receiver_cause == {
        "schema_version": COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
        "cause_status": "scheduler_correlated",
        "cause_transition": "component_analyst_work",
        "component_identity_digest": component_identity_digest(failed_component["id"]),
        "failure_code": "model_transport_failure",
        "role": ROLE_COMPONENT_ANALYST,
        "failure_kind": "model_transport_failure",
        "settlement_posture": "failed_spent",
    }
    assert "private text" not in json.dumps(
        raised.value.component_receiver_cause,
        sort_keys=True,
    )


def test_nonunique_scheduler_correlation_collapses_to_other_safe() -> None:
    (
        scheduler,
        run_id,
        request_id,
        _failed_component_id,
        _other_component_id,
    ) = _failed_two_component_scheduler()
    ambiguous = deepcopy(scheduler)
    duplicate = deepcopy(ambiguous["lease_history"][-1])
    duplicate["lease_id"] = str(duplicate["lease_id"]) + "-duplicate"
    ambiguous["lease_history"].append(duplicate)

    assert scheduling._scheduled_component_analyst_failure_correlation(
        ambiguous,
        run_id=run_id,
        request_id=request_id,
    ) is None

    cause = component_receiver_cause_from_current_scheduler_failure(
        state=ambiguous,
        expected_run_id=run_id,
        expected_request_id=request_id,
    )

    assert cause == {
        "schema_version": COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
        "cause_status": "other_safe",
        "cause_transition": "component_analyst_work",
        "failure_code": "other_safe",
    }


def test_unknown_error_is_other_safe_and_private_text_never_reaches_projection() -> None:
    private_text = "private exception prose: raw-component-id=component-secret"
    error = OrdinaryMulticomponentRuntimeError(private_text)
    trace = _receiver_trace(cause=error.component_receiver_cause)

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=trace
    )

    assert projection is not None
    assert projection["component_receiver_cause"] == {
        "schema_version": COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
        "cause_status": "other_safe",
        "cause_transition": "other_safe",
        "failure_code": "other_safe",
    }
    assert private_text not in json.dumps(projection, sort_keys=True)
    assert "component-secret" not in json.dumps(projection, sort_keys=True)


def test_later_unresolved_handoff_cannot_overwrite_an_earlier_exact_cause() -> None:
    cause = component_receiver_exact_evidence_or_custody_cause(
        component_id="component-earlier",
        failure_code="no_bindable_passage",
    )
    trace = _receiver_trace(cause=cause, posture="unresolved_handoff")

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=trace
    )

    assert projection is not None
    assert projection["slots"][0]["final_posture"] == "unresolved_handoff"
    assert projection["component_receiver_cause"] == cause


def test_n2_bounded_projection_keeps_the_receiver_cause() -> None:
    cause = component_receiver_exact_evidence_or_custody_cause(
        component_id="component-b",
        failure_code="source_obligation_custody_not_current",
    )

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_n2_receiver_trace(cause=cause)
    )

    assert projection is not None
    assert projection["required_slot_count"] == 2
    assert projection["component_receiver_cause"] == cause


def test_success_path_has_no_component_receiver_cause() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_receiver_trace(
            cause=component_receiver_exact_evidence_or_custody_cause(
                component_id="ignored-on-success",
                failure_code="no_bindable_passage",
            ),
            receiver_failed=False,
        )
    )

    assert projection is not None
    assert "component_receiver_cause" not in projection


def test_cause_only_supplements_the_bounded_diagnostic_projection() -> None:
    baseline = _receiver_trace()
    with_cause = _receiver_trace(
        cause=component_receiver_exact_evidence_or_custody_cause(
            component_id="component-diagnostic-only",
            failure_code="no_bindable_passage",
        )
    )

    baseline_projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=baseline
    )
    caused_projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=with_cause
    )

    assert baseline_projection is not None
    assert caused_projection is not None
    baseline_cause = baseline_projection.pop("component_receiver_cause")
    cause = caused_projection.pop("component_receiver_cause")
    assert baseline_cause["cause_status"] == "other_safe"
    assert cause["cause_status"] == "exact"
    assert caused_projection == baseline_projection


def test_cause_projection_is_pure_and_rejects_private_or_foreign_fields() -> None:
    private_tokens = {
        "query": "private query text",
        "url": "https://private.invalid/source",
        "component_id": "raw-component-id",
        "exception": "private exception prose",
    }
    trace = _receiver_trace(
        cause={
            "schema_version": COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
            "cause_status": "exact",
            "cause_transition": "evidence_selection_or_custody",
            "component_identity_digest": "raw-component-id",
            "failure_code": "no_bindable_passage",
            **private_tokens,
        }
    )
    original = deepcopy(trace)

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=trace
    )

    assert trace == original
    assert projection is not None
    assert projection["component_receiver_cause"]["cause_status"] == "other_safe"
    rendered = json.dumps(projection, sort_keys=True)
    assert all(token not in rendered for token in private_tokens.values())


@pytest.mark.parametrize(
    "malformed_field",
    [
        {"failure_code": ["no_bindable_passage"]},
        {"role": {"component_analyst"}},
        {"failure_kind": ["model_transport_failure"]},
        {"settlement_posture": {"failed_spent"}},
        {"cause_transition": ["component_analyst_work"]},
    ],
)
def test_malformed_closed_cause_fields_collapse_without_raising(
    malformed_field: dict[str, Any],
) -> None:
    cause = {
        "schema_version": COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
        "cause_status": "scheduler_correlated",
        "cause_transition": "component_analyst_work",
        "component_identity_digest": component_identity_digest("component-private"),
        "failure_code": "model_transport_failure",
        "role": ROLE_COMPONENT_ANALYST,
        "failure_kind": "model_transport_failure",
        "settlement_posture": "failed_spent",
    }
    cause.update(malformed_field)

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_receiver_trace(cause=cause)
    )

    assert projection is not None
    assert projection["component_receiver_cause"] == {
        "schema_version": COMPONENT_RECEIVER_CAUSE_SCHEMA_VERSION,
        "cause_status": "other_safe",
        "cause_transition": "other_safe",
        "failure_code": "other_safe",
    }
