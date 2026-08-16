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
    _model_read_custody_assessment,
    _new_judgment_action_output,
    _orientation_judgment_request,
    _post_read_judgment_request,
    _post_read_two_custody_judgment_request,
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


def _whole_custody_variant(
    custody: dict[str, object],
    *,
    variant: str,
) -> dict[str, object]:
    if variant == "partial":
        return {
            "read_custody_material_id": custody["read_custody_material_id"],
            "read_custody_material_digest": custody[
                "read_custody_material_digest"
            ],
        }
    altered = deepcopy(custody)
    if variant == "augmented":
        altered["unrecognized_custody_payload"] = "must-fail"
        return altered
    if variant == "nested_altered":
        slot_ref = dict(altered["slot_ref"])
        slot_ref["slot_id"] = "slot:altered"
        altered["slot_ref"] = slot_ref
        return altered
    raise AssertionError(f"unknown custody variant: {variant}")


def test_whole_current_custody_objects_are_valid_for_handoff_and_assessment(
) -> None:
    request, custody, _ = _post_read_judgment_request()

    handoff = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
            "read_custody_refs": [deepcopy(custody)],
            "reason": "current custody supports semantic evaluation",
        },
    )
    assert handoff["action"] == (
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
    )
    assert handoff["read_custody_refs"] == [custody]

    unresolved = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "action": "HANDOFF_UNRESOLVED",
            "reason": "current custody does not resolve the active need",
            "read_custody_assessments": [
                _model_read_custody_assessment(custody)
            ],
        },
    )
    assert unresolved["action"] == "HANDOFF_UNRESOLVED"
    assert unresolved["read_custody_assessments"][0][
        "reviewed_custody_ref"
    ] == custody
    assert unresolved["read_custody_assessments"][0][
        "material_disposition"
    ] == "read_insufficient"


@pytest.mark.parametrize(
    "variant",
    ("partial", "augmented", "nested_altered"),
)
def test_handoff_rejects_non_whole_current_custody_objects(variant: str) -> None:
    request, custody, _ = _post_read_judgment_request()

    with pytest.raises(
        SearchOSRuntimeError,
        match="semantic handoff nominated stale or altered READ custody",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                "read_custody_refs": [
                    _whole_custody_variant(custody, variant=variant)
                ],
                "reason": "non-whole custody must fail closed",
            },
        )


@pytest.mark.parametrize(
    "variant",
    ("partial", "augmented", "nested_altered"),
)
def test_assessment_rejects_obsolete_whole_object_copy(
    variant: str,
) -> None:
    request, custody, _ = _post_read_judgment_request()

    with pytest.raises(
        SearchOSRuntimeError,
        match="READ custody assessment shape is invalid",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_UNRESOLVED",
                "reason": "obsolete whole-object assessment must fail closed",
                "read_custody_assessments": [
                    {
                        "reviewed_custody_ref": _whole_custody_variant(
                            custody,
                            variant=variant,
                        ),
                        "material_disposition": "read_insufficient",
                        "reason_code": "needed_detail_absent",
                    }
                ],
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
                    _model_read_custody_assessment(custody)
                ],
            },
        )


def test_extra_assessment_field_reproduces_custody_assessment_shape_invalid() -> None:
    request, custody, _ = _post_read_judgment_request()
    with pytest.raises(
        SearchOSRuntimeError,
        match="READ custody assessment shape is invalid",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_UNRESOLVED",
                "reason": "synthetic extra assessment field",
                "read_custody_assessments": [
                    {
                        **_model_read_custody_assessment(custody),
                        "extra_mechanical_field": "must-fail",
                    }
                ],
            },
        )


def test_id_and_reason_assessment_binds_current_custody_without_model_copy() -> None:
    request, custody, _ = _post_read_judgment_request()
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "action": "HANDOFF_UNRESOLVED",
            "reason": "current material is semantically insufficient",
            "read_custody_assessments": [
                _model_read_custody_assessment(
                    custody,
                    reason_code="needed_detail_absent",
                )
            ],
        },
    )
    bound = decision["read_custody_assessments"][0]
    assert bound["reviewed_custody_ref"] == custody
    assert bound["material_disposition"] == "read_insufficient"
    assert bound["reason_code"] == "needed_detail_absent"


def test_multi_custody_assessments_bind_reason_codes_by_material_id() -> None:
    request, first, second = _post_read_two_custody_judgment_request()
    decision = validate_searchos_judgment_model_output(
        request=request,
        model_output={
            "schema_version": "searchos_judgment_decision_v1",
            "action": "HANDOFF_UNRESOLVED",
            "reason": "neither current material satisfies the active need",
            "read_custody_assessments": [
                _model_read_custody_assessment(
                    second,
                    reason_code="second_material_off_point",
                ),
                _model_read_custody_assessment(
                    first,
                    reason_code="first_material_lacks_detail",
                ),
            ],
        },
    )
    bound = decision["read_custody_assessments"]
    assert bound[0]["reviewed_custody_ref"] == second
    assert bound[0]["reason_code"] == "second_material_off_point"
    assert bound[1]["reviewed_custody_ref"] == first
    assert bound[1]["reason_code"] == "first_material_lacks_detail"
    assert {item["reviewed_custody_ref"]["read_custody_material_id"] for item in bound} == {
        first["read_custody_material_id"],
        second["read_custody_material_id"],
    }


def test_omitting_one_of_two_current_assessments_fails_closed() -> None:
    request, first, _second = _post_read_two_custody_judgment_request()
    with pytest.raises(
        SearchOSRuntimeError,
        match="requires exact read_insufficient assessments",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_UNRESOLVED",
                "reason": "one inconvenient current material was omitted",
                "read_custody_assessments": [
                    _model_read_custody_assessment(first)
                ],
            },
        )


def test_empty_material_id_is_shape_invalid() -> None:
    request, _custody, _ = _post_read_judgment_request()
    with pytest.raises(
        SearchOSRuntimeError,
        match="READ custody assessment shape is invalid",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "HANDOFF_UNRESOLVED",
                "reason": "empty correspondence identity must fail closed",
                "read_custody_assessments": [
                    {
                        "read_custody_material_id": "   ",
                        "reason_code": "needed_detail_absent",
                    }
                ],
            },
        )


def test_pre_read_decision_cannot_invent_assessments() -> None:
    request = _orientation_judgment_request()
    with pytest.raises(
        SearchOSRuntimeError,
        match="stale or altered",
    ):
        validate_searchos_judgment_model_output(
            request=request,
            model_output={
                "schema_version": "searchos_judgment_decision_v1",
                "action": "REQUIRE_CLARIFICATION",
                "semantic_slot_ref": dict(
                    request["clarification_eligible_semantic_slot_refs"][0]
                ),
                "reason": "no current custody exists to assess",
                "read_custody_assessments": [
                    {
                        "read_custody_material_id": "searchos-read-custody:none",
                        "reason_code": "invented_assessment",
                    }
                ],
            },
        )
