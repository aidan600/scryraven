"""SearchJudgment compact model-selection plus exact-ref binding.

Test path: tests/test_searchos_judgment_compact_selection_binding_01.py
Proof class: PRODUCT-supporting adversarial boundary proof.
Validation bucket: phase_focus.
Surface guarded: SearchJudgment model-facing compact selection vs runtime-bound
exact current refs for READ, navigation, handoff, clarification, interpretation,
and post-READ assessments.
Runtime/product path guarded: validate_searchos_judgment_model_output and
reduce_searchos_judgment_decision.
Expected cost: milliseconds per node.
Promotion posture: remain phase_focus until the next SearchJudgment envelope
change.
Why not fast_pr: detailed compact-binding coverage, not a cheap sentinel.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from core.searchos_iterative_judgment_runtime import (
    SearchOSJudgmentAction,
    SearchOSRuntimeError,
    begin_searchos_judgment_round,
    build_searchos_navigation_judgment_request_v1,
    charge_searchos_judgment_call,
    reduce_searchos_judgment_decision,
    validate_searchos_judgment_model_output,
)
from core.searchos_navigation_runtime import project_navigation_window
from tests.test_searchos_bounded_navigation_foundation_01 import (
    _admit,
    _record_empty_candidate_window,
)
from tests.test_searchos_iterative_judgment_cutover_01 import (
    _compact_candidate_use_option_id,
    _compact_read_custody_material_ids,
    _model_read_custody_assessment,
    _new_judgment_action_output,
    _orientation_judgment_request,
    _post_read_judgment_request,
    _post_read_two_custody_judgment_request,
)


def test_compact_read_id_binds_exact_current_option_and_reducer_keeps_full_ref() -> None:
    request = _orientation_judgment_request()
    option_ref = dict(request["candidate_use_options"][0]["candidate_use_option_ref"])
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "action": "REQUEST_READ_PAGE",
            "candidate_use_option_id": option_ref["candidate_use_option_id"],
            "reason": "compact identity selects the current authorized option",
        },
    )
    assert decision["candidate_use_option_ref"] == option_ref
    assert decision["candidate_use_option_ref"]["lineage_snapshot_ref"] == (
        option_ref["lineage_snapshot_ref"]
    )
    assert "candidate_use_option_id" not in decision
    assert decision["deterministic_fallback_used"] is False


def test_foreign_and_empty_read_ids_fail_closed() -> None:
    request = _orientation_judgment_request()
    option_ref = dict(request["candidate_use_options"][0]["candidate_use_option_ref"])
    with pytest.raises(
        SearchOSRuntimeError,
        match="outside current candidate window",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "REQUEST_READ_PAGE",
                "candidate_use_option_id": "searchos-candidate-use:foreign",
                "reason": "foreign compact identity must fail",
            },
        )
    with pytest.raises(
        SearchOSRuntimeError,
        match="outside current candidate window",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "REQUEST_READ_PAGE",
                "candidate_use_option_id": "   ",
                "reason": "empty compact identity must fail",
            },
        )
    with pytest.raises(
        SearchOSRuntimeError,
        match="outside current candidate window",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "REQUEST_READ_PAGE",
                "reason": "omitted compact identity must fail",
            },
        )
    with pytest.raises(
        SearchOSRuntimeError,
        match="incompatible payload",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "REQUEST_READ_PAGE",
                "candidate_use_option_id": {
                    "candidate_use_option_id": option_ref["candidate_use_option_id"]
                },
                "reason": "mapping payload must fail closed",
            },
        )


def test_duplicate_authorized_read_ids_fail_closed() -> None:
    request = _orientation_judgment_request()
    first = dict(request["candidate_use_options"][0])
    colliding = deepcopy(first)
    colliding["candidate_use_option_ref"] = {
        **dict(first["candidate_use_option_ref"]),
        "normalized_url": "https://example.com/collapsed-collision",
    }
    request["candidate_use_options"] = [first, colliding]
    with pytest.raises(
        SearchOSRuntimeError,
        match="authorized compact identity is not unique",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "REQUEST_READ_PAGE",
                "candidate_use_option_id": _compact_candidate_use_option_id(first),
                "reason": "duplicate authorized identities must not collapse",
            },
        )


def test_obsolete_whole_read_object_is_unsupported() -> None:
    request = _orientation_judgment_request()
    with pytest.raises(SearchOSRuntimeError, match="unsupported fields"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "REQUEST_READ_PAGE",
                "candidate_use_option_ref": dict(
                    request["candidate_use_options"][0]["candidate_use_option_ref"]
                ),
                "reason": "obsolete whole-object copy must fail closed",
            },
        )


def test_compact_handoff_ids_bind_exact_current_custody_refs() -> None:
    request, first, second = _post_read_two_custody_judgment_request()
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
            "read_custody_material_ids": _compact_read_custody_material_ids(
                second,
                first,
            ),
            "reason": "compact custody identities bind exact current refs",
        },
    )
    assert decision["read_custody_refs"] == [second, first]
    assert decision["read_custody_assessments"] == []


def test_handoff_rejects_duplicate_foreign_and_omitted_custody_ids() -> None:
    request, first, _second = _post_read_two_custody_judgment_request()
    with pytest.raises(SearchOSRuntimeError, match="repeats READ custody"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                "read_custody_material_ids": [
                    first["read_custody_material_id"],
                    first["read_custody_material_id"],
                ],
                "reason": "duplicate compact custody selection is illegal",
            },
        )
    with pytest.raises(SearchOSRuntimeError, match="stale or altered"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                "read_custody_material_ids": ["searchos-read-custody:foreign"],
                "reason": "foreign compact custody selection is illegal",
            },
        )
    with pytest.raises(
        SearchOSRuntimeError,
        match="semantic handoff requires exact READ custody refs",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                "read_custody_material_ids": [],
                "reason": "omitted compact custody selection is illegal",
            },
        )


def test_duplicate_authorized_custody_ids_fail_closed() -> None:
    _state, request, first, _ = _post_read_judgment_request()
    colliding = deepcopy(first)
    colliding["normalized_url"] = "https://example.com/collapsed-custody"
    request["read_custody_refs"] = [first, colliding]
    with pytest.raises(
        SearchOSRuntimeError,
        match="authorized compact identity is not unique",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_UNRESOLVED",
                "reason": "duplicate authorized custody identities must not collapse",
                "read_custody_assessments": [
                    _model_read_custody_assessment(first)
                ],
            },
        )


def test_compact_clarification_slot_id_binds_exact_eligible_ref() -> None:
    request = _orientation_judgment_request()
    eligible = dict(request["clarification_eligible_semantic_slot_refs"][0])
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "action": "REQUIRE_CLARIFICATION",
            "semantic_slot_id": eligible["slot_id"],
            "reason": "compact slot identity binds the exact eligible ref",
        },
    )
    assert decision["semantic_slot_ref"] == eligible


def test_compact_interpretation_ids_bind_exact_slot_and_basis_refs() -> None:
    request = _orientation_judgment_request()
    output = _new_judgment_action_output(
        request,
        action="PROPOSE_INTERPRETATION_BINDING",
    )
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output=output,
    )
    contract = dict(request["interpretation_binding_contract"])
    assert decision["interpretation_binding"]["semantic_slot_ref"] == dict(
        contract["eligible_semantic_slot_refs"][0]
    )
    assert decision["interpretation_binding"]["basis_candidate_refs"] == [
        dict(contract["candidate_basis_refs"][0])
    ]
    assert decision["interpretation_binding"]["resolved_value"] == dict(
        contract["eligible_semantic_slot_refs"][0]
    )["candidate_values"][0]
    assert decision["interpretation_binding"]["disclose_assumption"] is True
    assert "semantic_slot_id" not in decision["interpretation_binding"]
    assert "basis_candidate_use_option_ids" not in decision["interpretation_binding"]
    assert "basis_read_custody_material_ids" not in decision["interpretation_binding"]
    duplicate = dict(output["interpretation_binding"])
    duplicate["basis_candidate_use_option_ids"] = [
        duplicate["basis_candidate_use_option_ids"][0],
        duplicate["basis_candidate_use_option_ids"][0],
    ]
    with pytest.raises(
        SearchOSRuntimeError,
        match="basis refs repeat identity",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={**output, "interpretation_binding": duplicate},
        )


def test_post_read_assessment_compact_id_still_binds_exact_custody() -> None:
    _state, request, custody, remaining = _post_read_judgment_request()
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "action": "REQUEST_READ_PAGE",
            "candidate_use_option_id": _compact_candidate_use_option_id(
                remaining
            ),
            "reason": "current READ material does not satisfy the active need",
            "read_custody_assessments": [
                _model_read_custody_assessment(
                    custody,
                    reason_code="needed_detail_absent",
                )
            ],
        },
    )
    assert decision["candidate_use_option_ref"] == remaining
    assert decision["read_custody_assessments"][0]["reviewed_custody_ref"] == custody
    assert decision["read_custody_assessments"][0]["material_disposition"] == (
        "read_insufficient"
    )


def test_compact_navigation_id_binds_exact_current_ref() -> None:
    state, _, _store = _admit("[child](/child)")
    state, candidate_window = _record_empty_candidate_window(state)
    state, reservation = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(
        state,
        reservation_ref=reservation,
        slot_id="slot-1",
    )
    navigation_window = project_navigation_window(state, slot_id="slot-1")
    custody = state["slots_by_id"]["slot-1"]["custody_refs"][0]
    request = build_searchos_navigation_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=candidate_window,
        navigation_window=navigation_window,
        read_custody_refs=[custody],
    )
    current_ref = navigation_window[0]["navigation_candidate_ref"]
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_navigation_judgment_decision_v1",
            "action": SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value,
            "navigation_candidate_id": current_ref["navigation_candidate_id"],
            "reason": "compact navigation identity binds the exact current ref",
            "read_custody_assessments": [
                _model_read_custody_assessment(custody)
            ],
        },
    )
    assert decision["navigation_candidate_ref"] == current_ref
    assert "navigation_candidate_id" not in decision
    reduced = reduce_searchos_judgment_decision(state, decision=decision)
    assert reduced["slots_by_id"]["slot-1"]["pending_navigation_candidate_ref"] == (
        current_ref
    )
    assert "navigation_candidate_id" not in reduced["slots_by_id"]["slot-1"]


def test_duplicate_authorized_navigation_ids_fail_closed() -> None:
    state, _, _store = _admit("[child](/child)")
    state, candidate_window = _record_empty_candidate_window(state)
    state, reservation = begin_searchos_judgment_round(state, slot_ids=["slot-1"])
    state, charge = charge_searchos_judgment_call(
        state,
        reservation_ref=reservation,
        slot_id="slot-1",
    )
    navigation_window = project_navigation_window(state, slot_id="slot-1")
    custody = state["slots_by_id"]["slot-1"]["custody_refs"][0]
    request = build_searchos_navigation_judgment_request_v1(
        state=state,
        slot_id="slot-1",
        charge_ref=charge,
        candidate_window=candidate_window,
        navigation_window=navigation_window,
        read_custody_refs=[custody],
    )
    first = dict(request["navigation_options"][0])
    colliding = deepcopy(first)
    colliding["navigation_candidate_ref"] = {
        **dict(first["navigation_candidate_ref"]),
        "navigation_candidate_digest": "f" * 64,
    }
    request["navigation_options"] = [first, colliding]
    with pytest.raises(
        SearchOSRuntimeError,
        match="authorized compact identity is not unique",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_navigation_judgment_decision_v1",
                "action": SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value,
                "navigation_candidate_id": first["navigation_candidate_ref"][
                    "navigation_candidate_id"
                ],
                "reason": "duplicate authorized navigation identities must not collapse",
                "read_custody_assessments": [
                    _model_read_custody_assessment(custody)
                ],
            },
        )
