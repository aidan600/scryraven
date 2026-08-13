"""SearchJudgment mechanical request-envelope authorship repair.

Test path: tests/test_searchos_judgment_mechanical_envelope_01.py
Proof class: PRODUCT-supporting adversarial boundary proof.
Validation bucket: phase_focus.
Surface guarded: SearchJudgment model-facing proposal vs runtime-bound
request identity, plus stale candidate/READ/semantic/navigation refs.
Runtime/product path guarded: validate_searchos_judgment_model_output.
Expected cost: milliseconds per node.
Promotion posture: remain phase_focus until the next SearchJudgment envelope
change.
Why not fast_pr: detailed adversarial envelope coverage, not a cheap sentinel.
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
    validate_searchos_judgment_model_output,
)
from core.searchos_navigation_runtime import project_navigation_window
from tests.test_searchos_bounded_navigation_foundation_01 import (
    _admit,
    _record_empty_candidate_window,
)
from tests.test_searchos_iterative_judgment_cutover_01 import (
    _digest,
    _new_judgment_action_output,
    _orientation_judgment_request,
    _post_read_judgment_request,
    _ref,
)


def test_runtime_binds_request_identity_and_rejects_model_authored_ids() -> None:
    request = _orientation_judgment_request()
    output = _new_judgment_action_output(request, action="REQUIRE_CLARIFICATION")
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output=output,
    )

    assert "judgment_request_id" not in output
    assert "judgment_request_digest" not in output
    assert "slot_id" not in output
    assert decision["judgment_request_ref"] == {
        "judgment_request_id": request["judgment_request_id"],
        "judgment_request_digest": request["judgment_request_digest"],
    }
    assert decision["slot_ref"] == request["slot_ref"]
    assert decision["deterministic_fallback_used"] is False

    matching = {
        **output,
        "judgment_request_id": request["judgment_request_id"],
        "judgment_request_digest": request["judgment_request_digest"],
        "slot_id": request["slot_ref"]["slot_id"],
    }
    with pytest.raises(SearchOSRuntimeError, match="must not author request identity"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output=matching,
        )


@pytest.mark.parametrize(
    "field",
    ("judgment_request_id", "judgment_request_digest", "slot_id"),
)
def test_model_authored_mechanical_identity_is_rejected_even_when_stale(
    field: str,
) -> None:
    request = _orientation_judgment_request()
    output = _new_judgment_action_output(request, action="REQUIRE_CLARIFICATION")
    output[field] = "stale-or-foreign"
    with pytest.raises(SearchOSRuntimeError, match="must not author request identity"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output=output,
        )


def test_old_candidate_ref_cannot_cross_requests() -> None:
    first = _orientation_judgment_request()
    second = _orientation_judgment_request()
    stale_option = deepcopy(first["candidate_use_options"][0]["candidate_use_option_ref"])
    stale_option["normalized_url"] = "https://example.com/stale-cross-request"
    with pytest.raises(SearchOSRuntimeError, match="stale or altered|outside current candidate window"):
        validate_searchos_judgment_model_output(
            request=second,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "REQUEST_READ_PAGE",
                "candidate_use_option_ref": stale_option,
                "reason": "old candidate must not cross requests",
            },
        )


def test_old_read_custody_ref_cannot_cross_requests() -> None:
    request, custody, _ = _post_read_judgment_request()
    stale_custody = {
        **custody,
        "searchos_read_custody_material_digest": _digest("other-request"),
    }
    with pytest.raises(SearchOSRuntimeError, match="stale or altered"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                "read_custody_refs": [stale_custody],
                "reason": "old READ custody must not cross requests",
            },
        )


def test_old_semantic_slot_ref_cannot_cross_requests() -> None:
    request = _orientation_judgment_request()
    stale_slot = deepcopy(request["clarification_eligible_semantic_slot_refs"][0])
    stale_slot["slot_id"] = "semantic:foreign-request"
    with pytest.raises(SearchOSRuntimeError, match="incompatible payload"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "REQUIRE_CLARIFICATION",
                "semantic_slot_ref": stale_slot,
                "reason": "old semantic slot must not cross requests",
            },
        )


def test_unauthorized_action_and_job_class_are_rejected() -> None:
    request = _orientation_judgment_request()
    with pytest.raises(SearchOSRuntimeError, match="not currently authorized"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                "read_custody_refs": [_ref("searchos_read_custody_material", "none")],
                "reason": "unauthorized semantic handoff",
            },
        )
    followup = {
        "schema_version": "searchos_judgment_decision_v1",
        "action": "PROPOSE_FOLLOWUP_QUERY",
        "followup_query": "Alpha unauthorized job class follow-up",
        "discovery_job_class": "deep_discovery",
        "reason": "unauthorized job class must fail closed",
    }
    if "PROPOSE_FOLLOWUP_QUERY" not in set(request["legal_actions"] or ()):
        with pytest.raises(SearchOSRuntimeError, match="not currently authorized"):
            validate_searchos_judgment_model_output(
                request=request,
                model_output=followup,
            )
        return
    with pytest.raises(SearchOSRuntimeError, match="follow-up nomination payload is invalid"):
        validate_searchos_judgment_model_output(
            request=request,
            model_output=followup,
        )


def test_old_navigation_ref_cannot_cross_requests() -> None:
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
    stale_navigation = deepcopy(navigation_window[0]["navigation_candidate_ref"])
    stale_navigation["navigation_option_id"] = "navigation-option:foreign-request"
    with pytest.raises(
        SearchOSRuntimeError,
        match="stale or altered|outside current navigation window",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_navigation_judgment_decision_v1",
                "action": SearchOSJudgmentAction.REQUEST_NAVIGATE_BREADCRUMB.value,
                "navigation_candidate_ref": stale_navigation,
                "reason": "old navigation ref must not cross requests",
                "read_custody_assessments": [
                    {
                        "reviewed_custody_ref": custody,
                        "material_disposition": "read_insufficient",
                        "reason_code": "needed_detail_absent",
                    }
                ],
            },
        )
