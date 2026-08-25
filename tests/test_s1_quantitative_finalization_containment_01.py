from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

import pytest

import core.author_execution_runtime as author_execution_runtime
import core.quantitative_consistency as quantitative_consistency
from core.author_execution_runtime import execute_author_action
from core.final_answer_packet import FinalAnswerAuthorInputPayload
from core.multicomponent_role_runtime import safe_packet_digest
from core.quantitative_finalization_authority import (
    QuantitativeFinalizationAuthorityError,
    build_quantitative_author_instruction_block,
    build_quantitative_fap_authority_preflight,
    build_quantitative_finalization_authority_bundle,
    build_quantitative_finalization_authority_manifest,
    evaluate_author_output_quantitative_authority,
    specialist_quantitative_authority_ref_from_handoff,
    validate_author_output_quantitative_authority,
)
from core.run_kernel import (
    AUTHOR_EXECUTION_STAGE,
    ActionType,
    AuthorizedAction,
    ObservationType,
)


def _source_bundle(*claims: str) -> dict[str, Any]:
    entries = tuple(
        {
            "entry_kind": "direct_component",
            "component_id": f"component-{index}",
            "claim_id": f"claim-{index}",
            "claim_digest": f"claim-digest-{index}",
            "claim_text": claim,
            "admission_status": "admitted",
            "current": True,
            "stale": False,
            "component_analyst_case_ref": {
                "artifact_id": f"component-analyst-{index}",
                "artifact_digest": f"component-analyst-digest-{index}",
            },
            "semantic_observation_ref": {
                "observation_id": f"observation-{index}",
                "observation_digest": f"observation-digest-{index}",
            },
            "component_coverage_ref": {
                "coverage_record_id": f"coverage-{index}",
                "coverage_record_digest": f"coverage-digest-{index}",
            },
            "evidence_refs": [
                {
                    "content_ref_id": f"content-{index}",
                    "content_digest": f"content-digest-{index}",
                    "evidence_ref_id": f"evidence-{index}",
                }
            ],
        }
        for index, claim in enumerate(claims, start=1)
    )
    return build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "packet-direct", "readiness_status": "author_ready"},
        semantic_author_materialization=_source_materialization(*claims),
        direct_component_entries=entries,
    )


def _source_materialization(*claims: str) -> dict[str, Any]:
    material_refs = [
        {
            "component_id": f"component-{index}",
            "content_ref_id": f"content-{index}",
            "content_digest": f"content-digest-{index}",
            "coverage_record_id": f"coverage-{index}",
            "coverage_record_digest": f"coverage-digest-{index}",
            "evidence_ref_id": f"evidence-{index}",
            "packet_evidence_id": f"packet-evidence-{index}",
            "source_id": index,
            "bounded_text": claim,
        }
        for index, claim in enumerate(claims, start=1)
    ]
    return {
        "available": True,
        "bounded_material_complete": True,
        "bounded_material_refs": material_refs,
    }


def _fap_materialization(*claims: str) -> dict[str, Any]:
    return {
        "available": True,
        "bounded_material_complete": True,
        "bounded_material_refs": [
            {
                "component_id": "component-a",
                "content_ref_id": f"content-{index}",
                "content_digest": f"content-digest-{index}",
                "coverage_record_id": "coverage-a",
                "coverage_record_digest": "coverage-digest-a",
                "evidence_ref_id": f"evidence-{index}",
                "packet_evidence_id": f"packet-evidence-{index}",
                "source_id": index,
                "bounded_text": claim,
            }
            for index, claim in enumerate(claims, start=1)
        ],
    }


def _fap_direct_entry(claim_text: str, **overrides: Any) -> dict[str, Any]:
    entry = {
        "entry_kind": "direct_component",
        "component_id": "component-a",
        "claim_id": "claim-a",
        "claim_digest": "claim-digest-a",
        "claim_text": claim_text,
        "admission_status": "admitted",
        "current": True,
        "stale": False,
        "component_analyst_case_ref": {
            "artifact_id": "component-analyst-a",
            "artifact_digest": "component-analyst-digest-a",
        },
        "semantic_observation_ref": {
            "observation_id": "observation-a",
            "observation_digest": "observation-digest-a",
        },
        "component_coverage_ref": {
            "coverage_record_id": "coverage-a",
            "coverage_record_digest": "coverage-digest-a",
        },
        "evidence_refs": [
            {"content_ref_id": "content-1", "content_digest": "content-digest-1"}
        ],
    }
    entry.update(overrides)
    return entry


def _accept(text: str, bundle: Mapping[str, Any]) -> dict[str, Any]:
    return validate_author_output_quantitative_authority(
        text,
        manifest=dict(bundle["manifest"]),
    )


def _reject(text: str, bundle: Mapping[str, Any]) -> dict[str, Any]:
    with pytest.raises(QuantitativeFinalizationAuthorityError) as exc_info:
        _accept(text, bundle)
    diagnostic = exc_info.value.diagnostic
    assert diagnostic["status"] == "rejected"
    assert diagnostic["answer_rewritten"] is False
    assert diagnostic["answer_fragment_deleted"] is False
    assert diagnostic["author_retry_requested"] is False
    assert diagnostic["final_text_included"] is False
    return diagnostic


def _evaluate(text: str, bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Run the retained parser only as a non-authoritative test observation."""

    return evaluate_author_output_quantitative_authority(
        text,
        manifest=dict(bundle["manifest"]),
    )


@pytest.mark.parametrize(
    ("label", "entry", "materialization", "expected_reason"),
    (
        (
            "unsupported_arithmetic",
            _fap_direct_entry("The difference is 40 km."),
            _fap_materialization(
                "Object A has a length of 100 km.",
                "Object B has a length of 60 km.",
            ),
            "claim_literal_absent_from_bound_material",
        ),
        (
            "unauthorized_conversion",
            _fap_direct_entry("Object A has a length of 62.1 miles."),
            _fap_materialization("Object A has a length of 100 km."),
            "claim_literal_absent_from_bound_material",
        ),
        (
            "unbound_source_number",
            _fap_direct_entry("Object A has a length of 100 km."),
            {},
            "missing_content_evidence_lineage",
        ),
        (
            "unadmitted_numeric_proposition",
            _fap_direct_entry(
                "Object A has a length of 100 km.",
                admission_status="unsupported",
            ),
            _fap_materialization("Object A has a length of 100 km."),
            "missing_admitted_component_authority",
        ),
        (
            "stale_foreign_authority",
            _fap_direct_entry(
                "Object A has a length of 100 km.",
                stale=True,
            ),
            _fap_materialization("Object A has a length of 100 km."),
            "stale_or_foreign_lineage",
        ),
        (
            "missing_specialist_binding",
            _fap_direct_entry(
                "The derived amount is 40 km.",
                specialist_quantitative_authority_ref={"result_id": "missing"},
            ),
            _fap_materialization("Object A has a length of 100 km."),
            "incomplete_specialist_authority",
        ),
        (
            "wrong_content_lineage",
            _fap_direct_entry("Rebate is $1,200."),
            {
                "available": True,
                "bounded_material_complete": True,
                "bounded_material_refs": [
                    {
                        "component_id": "component-a",
                        "content_ref_id": "content-other",
                        "content_digest": "content-digest-other",
                        "coverage_record_id": "coverage-a",
                        "coverage_record_digest": "coverage-digest-a",
                        "evidence_ref_id": "evidence-other",
                        "packet_evidence_id": "packet-evidence-other",
                        "source_id": 99,
                        "bounded_text": "Rebate is $1,200.",
                    }
                ],
            },
            "missing_content_evidence_lineage",
        ),
    ),
)
def test_fap_structured_quantitative_preflight_blocks_incomplete_claims_before_author(
    label: str,
    entry: Mapping[str, Any],
    materialization: Mapping[str, Any],
    expected_reason: str,
) -> None:
    preflight = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": f"preflight-{label}"},
        direct_component_entries=(entry,),
        semantic_author_materialization=materialization,
    )

    diagnostic = preflight["diagnostic"]
    assert diagnostic["status"] == "blocked"
    assert diagnostic["author_invocation_allowed"] is False
    assert diagnostic["post_author_semantic_validation_required"] is False
    assert expected_reason in diagnostic["reason_codes"]
    assert diagnostic["final_text_included"] is False


def test_fap_structured_direct_source_numeric_authority_is_ready_before_author() -> None:
    claim = "Object A has a length of 100 km."
    preflight = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "preflight-direct-source"},
        direct_component_entries=(_fap_direct_entry(claim),),
        semantic_author_materialization=_fap_materialization(claim),
    )

    diagnostic = preflight["diagnostic"]
    claims = preflight["bundle"]["manifest"]["authorized_numeric_claims"]
    assert diagnostic["status"] == "ready", diagnostic["reason_codes"]
    assert diagnostic["author_invocation_allowed"] is True
    assert {claim["authority_kind"] for claim in claims} == {
        "direct_source_numeric"
    }


def test_fap_direct_source_numeric_survives_incidental_unsupported_surfaces() -> None:
    source = "Object A has a length of 100 km."
    claim = "The result is first. " + source
    preflight = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "preflight-incidental-unsupported"},
        direct_component_entries=(_fap_direct_entry(claim),),
        semantic_author_materialization=_fap_materialization(source),
    )

    diagnostic = preflight["diagnostic"]
    rows = preflight["bundle"]["manifest"]["authorized_numeric_claims"]
    assert diagnostic["status"] == "ready", diagnostic
    assert diagnostic["author_invocation_allowed"] is True
    assert "unsupported_claim_literal_surface" not in diagnostic["reason_codes"]
    assert {row["authority_kind"] for row in rows} == {"direct_source_numeric"}
    assert {row["normalized_numeric_value_text"] for row in rows} == {"100"}


def test_fap_direct_source_numeric_survives_incidental_name_integer() -> None:
    source = "Object A has a length of 100 km."
    claim = "Example Product 3 documentation states " + source
    preflight = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "preflight-incidental-name-integer"},
        direct_component_entries=(_fap_direct_entry(claim),),
        semantic_author_materialization=_fap_materialization(source),
    )

    diagnostic = preflight["diagnostic"]
    rows = preflight["bundle"]["manifest"]["authorized_numeric_claims"]
    assert diagnostic["status"] == "ready", diagnostic
    assert diagnostic["author_invocation_allowed"] is True
    assert "literal_signature_mismatch" not in diagnostic["reason_codes"]
    assert {row["authority_kind"] for row in rows} == {"direct_source_numeric"}
    assert {row["normalized_numeric_value_text"] for row in rows} == {"100"}
    assert {row["canonical_unit"] for row in rows} == {"km"}


def test_fap_preflight_ignores_claim_with_only_incidental_name_integers() -> None:
    claim = "Example Product 3 documentation is the cited handbook."
    preflight = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "preflight-only-incidental-name-integer"},
        direct_component_entries=(_fap_direct_entry(claim),),
        semantic_author_materialization=_fap_materialization(claim),
    )

    diagnostic = preflight["diagnostic"]
    assert diagnostic["status"] == "ready", diagnostic
    assert diagnostic["author_invocation_allowed"] is True
    assert diagnostic["required_numeric_claim_count"] == 0
    assert preflight["bundle"]["manifest"]["authorized_numeric_claims"] == []


def test_fap_direct_source_numeric_still_requires_plain_integer_claims() -> None:
    source = "The direct count is 17."
    preflight = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "preflight-plain-integer"},
        direct_component_entries=(_fap_direct_entry(source),),
        semantic_author_materialization=_fap_materialization(source),
    )

    diagnostic = preflight["diagnostic"]
    rows = preflight["bundle"]["manifest"]["authorized_numeric_claims"]
    assert diagnostic["status"] == "ready", diagnostic
    assert {row["normalized_numeric_value_text"] for row in rows} == {"17"}


def test_fap_preflight_blocks_when_every_numeric_surface_is_unsupported() -> None:
    claim = "The result is first."
    preflight = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "preflight-all-unsupported"},
        direct_component_entries=(_fap_direct_entry(claim),),
        semantic_author_materialization=_fap_materialization(claim),
    )

    diagnostic = preflight["diagnostic"]
    assert diagnostic["status"] == "blocked"
    assert diagnostic["author_invocation_allowed"] is False
    assert "unsupported_claim_literal_surface" in diagnostic["reason_codes"]
    assert diagnostic["final_text_included"] is False


def _specialist_ref(
    *, target_kind: str, value: str, unit: str, claim_text: str
) -> dict[str, Any]:
    target_key = "component-a" if target_kind == "component" else "synthesis-a"
    dprime_ref = {
        "artifact_id": f"{target_kind}-dprime-artifact",
        "artifact_digest": f"{target_kind}-dprime-digest",
    }
    return {
        "specialist_result_ref": {
            "result_id": f"result-{target_kind}",
            "result_digest": f"result-{target_kind}-digest",
            "canonical_target_ref": {
                "target_kind": target_kind,
                "target_key": target_key,
            },
            "capability_id": "specialist.source_bound_calculation",
            "capability_version": "1.0.0",
            "execution_posture": "completed",
        },
        "specialist_handoff_ref": {
            "handoff_id": f"handoff-{target_kind}",
            "handoff_digest": f"handoff-{target_kind}-digest",
            "canonical_target_ref": {
                "target_kind": target_kind,
                "target_key": target_key,
            },
        },
        "normalized_numeric_value_text": value,
        "canonical_unit": unit,
        "precision_posture": "exact_as_reported",
        "result_unit_contract_posture": "canonical_result_unit",
        "claim_alignment_posture": "exact_match",
        "claim_alignment_ref_digest": f"alignment-{target_kind}-digest",
        "claim_material_digest": sha256(claim_text.encode("utf-8")).hexdigest(),
        "applicable_dprime_ref": dprime_ref,
        "applicable_dprime_consumption_ref": {
            "route": f"{target_kind}_dprime",
            "handoff_id": f"handoff-{target_kind}",
            "handoff_digest": f"handoff-{target_kind}-digest",
            "dprime_artifact_ref": dprime_ref,
            "consumption_posture": "consumed_by_applicable_dprime",
        },
    }


def test_b_equivalent_author_arithmetic_is_rejected_but_operands_remain_eligible() -> None:
    bundle = _source_bundle(
        "Object A has a length of 600 km.",
        "Object B has a length of 400 km.",
    )

    assert _accept("Object A has a length of 600 km.", bundle)["status"] == "accepted"
    assert _accept("Object B has a length of 400 km.", bundle)["status"] == "accepted"
    diagnostic = _reject("The difference is 200 km.", bundle)

    assert diagnostic["reason_refs"][0]["reason_code"] == (
        "unauthorized_quantitative_proposition"
    )


def test_d02_equivalent_conversions_and_mile_difference_are_rejected() -> None:
    bundle = _source_bundle(
        "Object A has a length of 600 km.",
        "Object B has a length of 400 km.",
    )

    diagnostic = _reject(
        "Object A has a length of 372.8 miles. "
        "Object B has a length of 248.5 miles. The difference is 124.3 miles.",
        bundle,
    )

    assert diagnostic["rejection_count"] == 3
    assert diagnostic["candidate_quantitative_literal_count"] == 3


def test_claim_scope_blocks_subject_reuse_result_reuse_and_mixed_sentence() -> None:
    bundle = _source_bundle(
        "Object A has a length of 100 km.",
        "Object C has a length of 60 km.",
        "Object D has a length of 40 km.",
    )

    _reject("Object B has a length of 100 km.", bundle)
    _reject("The difference is 100 km.", bundle)
    _reject("Object C and Object D have a total length of 100 km.", bundle)
    _reject("Object A has a length of 100 km and the difference is 60 km.", bundle)


def test_same_literal_in_authorized_and_unauthorized_propositions_rejects_whole_output() -> None:
    bundle = _source_bundle("Object A has a length of 100 km.")

    diagnostic = _reject(
        "Object A has a length of 100 km. Object B has a length of 100 km.",
        bundle,
    )

    assert diagnostic["rejection_count"] == 1
    assert diagnostic["matched_claim_keys"]


def test_direct_numbers_and_narrow_comma_formatting_pass() -> None:
    bundle = _source_bundle(
        "The diameter is 1,000 km.",
        "The measured mass is 3.50 kg.",
        "The date is 2026-07-14.",
        "The schema version is 2.3.",
        "The service uses port 443.",
        "The supported share is 25 percent.",
        "Object A is 100 km and Object B is 100 km.",
    )

    assert _accept("The diameter is 1000 km.", bundle)["status"] == "accepted"
    assert _accept("The measured mass is 3.50 kg.", bundle)["status"] == "accepted"
    assert _accept("The date is 2026-07-14.", bundle)["status"] == "accepted"
    assert _accept("The schema version is 2.3.", bundle)["status"] == "accepted"
    assert _accept("The service uses port 443.", bundle)["status"] == "accepted"
    assert _accept("The supported share is 25 percent.", bundle)["status"] == "accepted"
    assert _accept("Object A is 100 km and Object B is 100 km.", bundle)[
        "status"
    ] == "accepted"


def test_wrong_unit_rounding_sign_scale_percent_scientific_and_rate_fail() -> None:
    bundle = _source_bundle("Object A has a length of 1000 km.")

    for candidate in (
        "Object A has a length of 1000 miles.",
        "Object A has a length of 1.0 thousand km.",
        "Object A has a length of approximately 1000 km.",
        "Object A has a length of -1000 km.",
        "Object A has a length of +1000 km.",
        "Object A has a length of 1000 percent.",
        "Object A has a length of 1000 basis points.",
        "Object A has a length of 1e3 km.",
        "Object A has a length of 1000 km/day.",
    ):
        _reject(candidate, bundle)


def test_textual_number_is_not_an_obvious_bypass() -> None:
    bundle = _source_bundle(
        "Object A has a length of 60 km.",
        "Object B has a length of 40 km.",
    )

    diagnostic = _reject("The difference is one hundred km.", bundle)

    assert diagnostic["candidate_quantitative_literal_count"] == 1


def test_urls_citations_and_alphanumeric_transport_ids_are_excluded() -> None:
    bundle = _source_bundle("Object A has a length of 100 km.")

    accepted = _accept(
        "Object A has a length of 100 km [1]. "
        "Sources: https://example.test/2026/v1.2/1000 and AF5B-ref-77.",
        bundle,
    )

    assert accepted["candidate_quantitative_literal_count"] == 1


def test_nonquantitative_answer_is_unchanged_and_empty_manifest_accepts_it() -> None:
    manifest = build_quantitative_finalization_authority_manifest(
        source_fap_ref={"packet_id": "nonquantitative"}
    )

    accepted = validate_author_output_quantitative_authority(
        "The available evidence supports the stated conclusion.",
        manifest=manifest,
    )

    assert accepted["status"] == "accepted"
    assert accepted["candidate_quantitative_literal_count"] == 0


def test_unsupported_claim_without_current_dprime_is_not_manifest_authority() -> None:
    bundle = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "unsupported-claim"},
        direct_component_entries=(
            {
                "entry_kind": "direct_component",
                "component_id": "component-1",
                "claim_id": "claim-a",
                "claim_digest": "claim-a-digest",
                "claim_text": "Object A has a length of 100 km.",
                "admission_status": "unsupported",
                "current": True,
                "stale": False,
            },
        ),
    )

    assert bundle["manifest"]["authorized_numeric_claims"] == []
    _reject("Object A has a length of 100 km.", bundle)


def test_admitted_component_arithmetic_and_same_value_reuse_do_not_launder_authority() -> None:
    source_materialization = _source_materialization(
        "Object A has a length of 100 km.",
        "Object B has a length of 60 km.",
    )
    common = {
        "entry_kind": "direct_component",
        "component_id": "component-1",
        "claim_id": "claim-derived",
        "claim_digest": "claim-derived-digest",
        "admission_status": "admitted",
        "current": True,
        "stale": False,
        "dprime_validation_ref": {"artifact_id": "component-dprime"},
        "component_analyst_case_ref": {
            "artifact_id": "component-analyst",
            "artifact_digest": "component-analyst-digest",
        },
        "semantic_observation_ref": {
            "observation_id": "observation-component-1",
            "observation_digest": "observation-digest-1",
        },
        "component_coverage_ref": {
            "coverage_record_id": "coverage-1",
            "coverage_record_digest": "coverage-digest-1",
        },
        "evidence_refs": [
            {
                "content_ref_id": "content-1",
                "content_digest": "content-digest-1",
            }
        ],
    }
    arithmetic = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "component-arithmetic"},
        semantic_author_materialization=source_materialization,
        direct_component_entries=(
            {**common, "claim_text": "The difference is 40 km."},
        ),
    )
    assert arithmetic["manifest"]["authorized_numeric_claims"] == []
    assert "The difference is 40 km." not in arithmetic["transient_renderings"].values()
    _reject("The difference is 40 km.", arithmetic)

    same_value = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "component-same-value"},
        semantic_author_materialization=source_materialization,
        direct_component_entries=(
            {**common, "claim_text": "The difference is 100 km."},
        ),
    )
    same_value_rows = same_value["manifest"]["authorized_numeric_claims"]
    assert len(same_value_rows) == 1
    assert same_value_rows[0]["authority_kind"] == "direct_source_numeric"
    assert same_value_rows[0]["normalized_numeric_value_text"] == "100"
    _accept("The difference is 100 km.", same_value)


def test_lineage_bound_component_paraphrase_remains_direct_source_authority() -> None:
    source_materialization = _source_materialization(
        "The Northstar Home-Energy Rebate base rebate is $1,200."
    )
    claim_text = "The Northstar base rebate is $1,200."
    bundle = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "component-source-paraphrase"},
        semantic_author_materialization=source_materialization,
        direct_component_entries=(
            {
                "entry_kind": "direct_component",
                "component_id": "component-1",
                "claim_id": "claim-component-1",
                "claim_digest": "claim-component-1-digest",
                "claim_text": claim_text,
                "admission_status": "admitted",
                "current": True,
                "stale": False,
                "dprime_validation_ref": {"artifact_id": "component-dprime"},
                "component_analyst_case_ref": {
                    "artifact_id": "component-analyst",
                    "artifact_digest": "component-analyst-digest",
                },
                "semantic_observation_ref": {
                    "observation_id": "observation-component-1",
                    "observation_digest": "observation-digest-1",
                },
                "component_coverage_ref": {
                    "coverage_record_id": "coverage-1",
                    "coverage_record_digest": "coverage-digest-1",
                },
                "evidence_refs": [
                    {
                        "content_ref_id": "content-1",
                        "content_digest": "content-digest-1",
                    }
                ],
            },
        ),
    )

    matching = [
        item
        for item in bundle["manifest"]["authorized_numeric_claims"]
        if item["authority_kind"] == "direct_source_numeric"
    ]
    assert len(matching) == 1
    assert matching[0]["applicable_validator_ref"] == {}
    assert matching[0]["claim_authority_posture"].endswith(
        "lineage_bound_literal_subset"
    )
    assert matching[0]["fap_material_ref"]["content_ref_id"] == "content-1"
    assert _accept(claim_text, bundle)["status"] == "accepted"


def test_same_lineage_subject_wording_is_not_a_fap_semantic_gate() -> None:
    claim = "Southstar rebate is $1,200."
    preflight = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "same-lineage-wording"},
        direct_component_entries=(_fap_direct_entry(claim),),
        semantic_author_materialization=_fap_materialization(
            "Northstar rebate is $1,200."
        ),
    )
    assert preflight["diagnostic"]["status"] == "ready"
    assert {
        item["authority_kind"]
        for item in preflight["bundle"]["manifest"]["authorized_numeric_claims"]
    } == {"direct_source_numeric"}


def test_cross_component_identical_text_does_not_share_direct_source_binding() -> None:
    claim = "The rebate is $1,200."
    shared_claim_digest = safe_packet_digest({"claim_text": claim})
    left = _fap_direct_entry(
        claim,
        component_id="component-a",
        claim_id="component-claim:component-a",
        claim_digest=shared_claim_digest,
        semantic_observation_ref={
            "observation_id": "observation-a",
            "observation_digest": "observation-digest-a",
        },
        evidence_refs=[
            {"content_ref_id": "content-1", "content_digest": "content-digest-1"}
        ],
        component_coverage_ref={
            "coverage_record_id": "coverage-a",
            "coverage_record_digest": "coverage-digest-a",
        },
    )
    right = _fap_direct_entry(
        claim,
        component_id="component-b",
        claim_id="component-claim:component-b",
        claim_digest=shared_claim_digest,
        semantic_observation_ref={
            "observation_id": "observation-b",
            "observation_digest": "observation-digest-b",
        },
        evidence_refs=[
            {"content_ref_id": "content-2", "content_digest": "content-digest-2"}
        ],
        component_coverage_ref={
            "coverage_record_id": "coverage-b",
            "coverage_record_digest": "coverage-digest-b",
        },
    )
    assert left["claim_digest"] == right["claim_digest"] == shared_claim_digest
    assert left["claim_id"] != right["claim_id"]
    materialization = {
        "available": True,
        "bounded_material_complete": True,
        "bounded_material_refs": [
            {
                "component_id": "component-a",
                "content_ref_id": "content-1",
                "content_digest": "content-digest-1",
                "coverage_record_id": "coverage-a",
                "coverage_record_digest": "coverage-digest-a",
                "evidence_ref_id": "evidence-1",
                "packet_evidence_id": "packet-evidence-1",
                "source_id": 1,
                "bounded_text": claim,
            },
            {
                "component_id": "component-b",
                "content_ref_id": "content-2",
                "content_digest": "content-digest-2",
                "coverage_record_id": "coverage-b",
                "coverage_record_digest": "coverage-digest-b",
                "evidence_ref_id": "evidence-2",
                "packet_evidence_id": "packet-evidence-2",
                "source_id": 2,
                "bounded_text": claim,
            },
        ],
    }
    ready = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "cross-component-ready"},
        direct_component_entries=(left, right),
        semantic_author_materialization=materialization,
    )
    assert ready["diagnostic"]["status"] == "ready"
    rows = [
        row
        for row in ready["bundle"]["manifest"]["authorized_numeric_claims"]
        if row["authority_kind"] == "direct_source_numeric"
    ]
    assert len(rows) == 2
    assert {row["current_claim_ref"]["claim_digest"] for row in rows} == {
        shared_claim_digest
    }
    assert {row["current_claim_ref"]["claim_id"] for row in rows} == {
        "component-claim:component-a",
        "component-claim:component-b",
    }
    assert len({row["local_claim_key"] for row in rows}) == 2
    assert all(
        str(row["local_claim_key"]).startswith("quant-claim-") for row in rows
    )
    by_component = {
        row["current_claim_ref"]["component_id"]: row
        for row in rows
    }
    assert set(by_component) == {"component-a", "component-b"}
    assert by_component["component-a"]["current_claim_ref"]["claim_id"] == (
        "component-claim:component-a"
    )
    assert by_component["component-a"]["fap_material_ref"]["content_ref_id"] == (
        "content-1"
    )
    assert by_component["component-b"]["current_claim_ref"]["claim_id"] == (
        "component-claim:component-b"
    )
    assert by_component["component-b"]["fap_material_ref"]["content_ref_id"] == (
        "content-2"
    )

    swapped = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "cross-component-swapped"},
        direct_component_entries=(left,),
        semantic_author_materialization={
            "available": True,
            "bounded_material_complete": True,
            "bounded_material_refs": [materialization["bounded_material_refs"][1]],
        },
    )
    assert swapped["diagnostic"]["status"] == "blocked"
    assert "missing_content_evidence_lineage" in swapped["diagnostic"]["reason_codes"]


def test_split_claim_literals_across_matched_materials_fail_closed() -> None:
    claim = "The rebate is $1,200 and the processing fee is $45."
    entry = _fap_direct_entry(
        claim,
        evidence_refs=[
            {"content_ref_id": "content-1", "content_digest": "content-digest-1"},
            {"content_ref_id": "content-2", "content_digest": "content-digest-2"},
        ],
    )
    split = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "split-literal-multi-material"},
        direct_component_entries=(entry,),
        semantic_author_materialization={
            "available": True,
            "bounded_material_complete": True,
            "bounded_material_refs": [
                {
                    "component_id": "component-a",
                    "content_ref_id": "content-1",
                    "content_digest": "content-digest-1",
                    "coverage_record_id": "coverage-a",
                    "coverage_record_digest": "coverage-digest-a",
                    "evidence_ref_id": "evidence-1",
                    "packet_evidence_id": "packet-evidence-1",
                    "source_id": 1,
                    "bounded_text": "The rebate is $1,200.",
                },
                {
                    "component_id": "component-a",
                    "content_ref_id": "content-2",
                    "content_digest": "content-digest-2",
                    "coverage_record_id": "coverage-a",
                    "coverage_record_digest": "coverage-digest-a",
                    "evidence_ref_id": "evidence-2",
                    "packet_evidence_id": "packet-evidence-2",
                    "source_id": 2,
                    "bounded_text": "The processing fee is $45.",
                },
            ],
        },
    )
    assert split["diagnostic"]["status"] == "blocked"
    assert split["bundle"]["manifest"]["authorized_numeric_claims"] == []
    assert {
        "literal_signature_mismatch",
        "claim_literal_absent_from_bound_material",
    } & set(split["diagnostic"]["reason_codes"])

    complete = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "single-material-complete-literals"},
        direct_component_entries=(
            _fap_direct_entry(
                claim,
                evidence_refs=[
                    {
                        "content_ref_id": "content-1",
                        "content_digest": "content-digest-1",
                    }
                ],
            ),
        ),
        semantic_author_materialization=_fap_materialization(claim),
    )
    assert complete["diagnostic"]["status"] == "ready"
    rows = [
        row
        for row in complete["bundle"]["manifest"]["authorized_numeric_claims"]
        if row["authority_kind"] == "direct_source_numeric"
    ]
    assert {row["normalized_numeric_value_text"] for row in rows} == {"1200", "45"}
    assert {row["fap_material_ref"]["content_ref_id"] for row in rows} == {"content-1"}
    assert all(
        row["fap_material_ref"]["content_digest"] == "content-digest-1" for row in rows
    )


def test_diagnostic_fingerprint_disagreement_does_not_block_lineage_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claim = "Object A has a length of 100 km."
    monkeypatch.setattr(
        "core.quantitative_finalization_authority.semantic_claim_fingerprint",
        lambda _text: "0" * 64,
    )
    preflight = build_quantitative_fap_authority_preflight(
        source_fap_ref={"packet_id": "fingerprint-diagnostic"},
        direct_component_entries=(_fap_direct_entry(claim),),
        semantic_author_materialization=_fap_materialization(claim),
    )
    assert preflight["diagnostic"]["status"] == "ready"
    rows = preflight["bundle"]["manifest"]["authorized_numeric_claims"]
    assert {row["authority_kind"] for row in rows} == {"direct_source_numeric"}
    assert {row["normalized_numeric_value_text"] for row in rows} == {"100"}


def test_admitted_synthesis_arithmetic_and_conversion_require_specialist_lineage() -> None:
    source_materialization = _source_materialization(
        "Object A has a length of 100 km.",
        "Object B has a length of 60 km.",
    )
    common = {
        "entry_kind": "admitted_synthesis",
        "synthesis_key": "derived-synthesis",
        "claim_id": "claim-synthesis-derived",
        "claim_digest": "claim-synthesis-derived-digest",
        "status": "admitted",
        "current": True,
        "stale": False,
        "input_node_refs": [{"node_id": "component-a"}, {"node_id": "component-b"}],
        "dprime_validation_ref": {"artifact_id": "synthesis-dprime"},
        "runkernel_admission_ref": {"action_id": "admit-synthesis"},
    }
    for packet_id, claim in (
        ("synthesis-arithmetic", "The difference is 40 km."),
        ("synthesis-conversion", "Object A has a length of 62.1 miles."),
    ):
        bundle = build_quantitative_finalization_authority_bundle(
            source_fap_ref={"packet_id": packet_id},
            semantic_author_materialization=source_materialization,
            admitted_synthesis_entries=({**common, "claim_text": claim},),
        )
        assert claim not in bundle["transient_renderings"].values()
        _reject(claim, bundle)
        assert bundle["manifest"]["authorized_numeric_claims"] == []


def test_hardened_component_claim_requires_same_source_explicit_proposition() -> None:
    source_materialization = _source_materialization(
        "Object A has a length of 100 km."
    )
    direct = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "hardened-direct"},
        semantic_author_materialization=source_materialization,
        component_packet_entries=(
            {
                "component_id": "component-1",
                "supported_safe_claim_allowed": True,
                "must_not_answer": False,
                "safe_answer_claim_text": "Object A has a length of 100 km.",
                "semantic_observation_ref": {
                    "observation_id": "observation-1",
                    "observation_digest": "observation-digest-1",
                },
                "component_coverage_ref": {
                    "coverage_record_id": "coverage-1",
                    "coverage_record_digest": "coverage-digest-1",
                },
                "evidence_refs": [
                    {
                        "content_ref_id": "content-1",
                        "content_digest": "content-digest-1",
                    }
                ],
                "fap_safe_claim_ref": {"claim_id": "hardened-claim-a"},
            },
        ),
    )
    assert _accept("Object A has a length of 100 km.", direct)["status"] == "accepted"
    assert {
        item["authority_kind"]
        for item in direct["manifest"]["authorized_numeric_claims"]
    } == {"direct_source_numeric"}

    converted = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "hardened-converted"},
        semantic_author_materialization=source_materialization,
        component_packet_entries=(
            {
                "component_id": "component-1",
                "supported_safe_claim_allowed": True,
                "must_not_answer": False,
                "safe_answer_claim_text": "Object A has a length of 62.1 miles.",
                "semantic_observation_ref": {
                    "observation_id": "observation-1",
                    "observation_digest": "observation-digest-1",
                },
                "component_coverage_ref": {
                    "coverage_record_id": "coverage-1",
                    "coverage_record_digest": "coverage-digest-1",
                },
                "evidence_refs": [
                    {
                        "content_ref_id": "content-1",
                        "content_digest": "content-digest-1",
                    }
                ],
                "fap_safe_claim_ref": {"claim_id": "hardened-claim-a"},
            },
        ),
    )
    assert "62.1" not in {
        item["normalized_numeric_value_text"]
        for item in converted["manifest"]["authorized_numeric_claims"]
    }
    _reject("Object A has a length of 62.1 miles.", converted)


def test_unvalidated_or_unconsumed_specialist_handoff_grants_no_authority() -> None:
    malformed = {
        "handoff_id": "forged-handoff",
        "handoff_digest": "forged-digest",
        "canonical_target_ref": {
            "target_kind": "component",
            "target_key": "component-a",
        },
        "result": {
            "result_ref": {
                "result_id": "forged-result",
                "result_digest": "forged-result-digest",
            },
            "execution_posture": "completed",
            "bounded_result": {
                "calculation_status": "computed",
                "numeric_value_text": "40",
                "result_unit": "km",
                "precision_posture": "exact_as_reported",
                "claim_alignment": {"posture": "exact_match"},
            },
        },
    }
    assert specialist_quantitative_authority_ref_from_handoff(
        malformed,
        applicable_dprime_ref={"artifact_id": "component-dprime"},
    ) == {}


def test_component_specialist_exact_result_and_dprime_consumption_pass() -> None:
    claim_text = "The supported derived amount is 1500 USD."
    specialist_ref = _specialist_ref(
        target_kind="component", value="1500", unit="USD", claim_text=claim_text
    )
    bundle = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "component-s1"},
        direct_component_entries=(
            {
                "entry_kind": "direct_component",
                "component_id": "component-a",
                "claim_id": "claim-component-a",
                "claim_digest": "claim-component-a-digest",
                "claim_text": claim_text,
                "admission_status": "admitted",
                "current": True,
                "stale": False,
                "dprime_validation_ref": {"artifact_id": "component-dprime"},
                "component_analyst_case_ref": {
                    "artifact_id": "component-analyst",
                    "artifact_digest": "component-analyst-digest",
                },
                "semantic_observation_ref": {"observation_id": "observation-a"},
                "component_coverage_ref": {"coverage_record_id": "coverage-a"},
                "specialist_quantitative_authority_ref": specialist_ref,
            },
        ),
    )

    assert {item["authority_kind"] for item in bundle["manifest"]["authorized_numeric_claims"]} == {
        "specialist_derived_numeric"
    }
    assert _accept(claim_text, bundle)["status"] == "accepted"

    unrelated = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "component-s1-unrelated"},
        direct_component_entries=(
            {
                "entry_kind": "direct_component",
                "component_id": "component-a",
                "claim_id": "claim-component-a-unrelated",
                "claim_digest": "claim-component-a-unrelated-digest",
                "claim_text": "The unrelated threshold is 1500 USD.",
                "admission_status": "admitted",
                "current": True,
                "stale": False,
                "dprime_validation_ref": {"artifact_id": "component-dprime"},
                "component_analyst_case_ref": {
                    "artifact_id": "component-analyst",
                    "artifact_digest": "component-analyst-digest",
                },
                "semantic_observation_ref": {"observation_id": "observation-a"},
                "component_coverage_ref": {"coverage_record_id": "coverage-a"},
                "specialist_quantitative_authority_ref": specialist_ref,
            },
        ),
    )
    assert unrelated["manifest"]["authorized_numeric_claims"] == []
    _reject("The unrelated threshold is 1500 USD.", unrelated)


def test_synthesis_specialist_two_hop_result_and_dprime_consumption_pass() -> None:
    claim_text = "The supported combined amount is 58800 USD."
    specialist_ref = _specialist_ref(
        target_kind="synthesis", value="58800", unit="USD", claim_text=claim_text
    )
    bundle = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "synthesis-s1"},
        admitted_synthesis_entries=(
            {
                "entry_kind": "admitted_synthesis",
                "synthesis_key": "synthesis-a",
                "claim_id": "claim-synthesis-a",
                "claim_digest": "claim-synthesis-a-digest",
                "claim_text": claim_text,
                "status": "admitted",
                "current": True,
                "stale": False,
                "input_node_refs": [
                    {"node_id": "component-a"},
                    {"node_id": "component-b"},
                ],
                "dprime_validation_ref": {"artifact_id": "synthesis-dprime"},
                "runkernel_admission_ref": {"action_id": "admit-synthesis"},
                "specialist_quantitative_authority_ref": specialist_ref,
            },
        ),
    )

    entry = bundle["manifest"]["authorized_numeric_claims"][0]
    assert entry["authority_kind"] == "specialist_derived_numeric"
    assert entry["applicable_validator_consumption_ref"]["route"] == (
        "synthesis_dprime"
    )
    assert _accept("The supported combined amount is 58800 USD.", bundle)[
        "status"
    ] == "accepted"


def test_author_instruction_is_authority_only_and_lists_exact_rendering() -> None:
    bundle = _source_bundle("Object A has a length of 100 km.")

    block = build_quantitative_author_instruction_block(
        bundle["manifest"],
        transient_renderings=bundle["transient_renderings"],
    )

    assert "Object A has a length of 100 km" in block
    for prohibited in ("calculate", "convert", "estimate", "interpolate", "round"):
        assert prohibited in block


def test_author_executor_does_not_make_parser_disagreement_a_product_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(**_kwargs: Any) -> dict[str, Any]:
        raise AssertionError(
            "ordinary Author must not invoke the quantitative consistency helper"
        )

    for module in (quantitative_consistency, author_execution_runtime):
        monkeypatch.setattr(
            module,
            "build_two_item_normalized_consistency_diagnostic",
            fail_if_called,
            raising=False,
        )
    payload = FinalAnswerAuthorInputPayload(
        packet_id="executor-packet",
        prompt="Draft the answer.\nFINAL ANSWER PACKET AUTHORITY",
        author_system_prompt_key="author",
        author_effort="low",
        quantitative_finalization_authority_manifest=(
            build_quantitative_finalization_authority_manifest(
                source_fap_ref={"packet_id": "executor-packet"}
            )
        ),
    )
    action = AuthorizedAction(
        action_id="author-action",
        run_id="author-run",
        stage=AUTHOR_EXECUTION_STAGE,
        action_type=ActionType.AUTHOR_EXECUTE,
        reason="test",
        inputs={
            "packet_id": "executor-packet",
            "author_system_prompt_key": "author",
            "author_effort": "low",
        },
        expected_observation_type=ObservationType.AUTHOR_OUTPUT_OBSERVED,
        sequence=1,
    )
    calls = 0
    displayed: list[str] = []

    def ask_model(*_args: Any, **_kwargs: Any) -> list[str]:
        nonlocal calls
        calls += 1
        return ["The unsupported difference is 200 km."]

    result = execute_author_action(
        action,
        author_payload=payload,
        ask_model=ask_model,
        system_prompt_registry={"author": "Render only supported claims."},
        base_url=None,
        api_key=None,
        query="Compare the objects.",
        stream_display=lambda chunks: displayed.extend(chunks),
    )

    assert calls == 1
    assert displayed == ["The unsupported difference is 200 km."]
    assert result.report == "The unsupported difference is 200 km."
    assert result.observation.payload["post_author_quantitative_semantic_gate_active"] is False
    assert "quantitative_finalization_validation" not in result.observation.payload
    assert result.quantitative_consistency_telemetry == {
        "quantitative_consistency_shadow_mode": False,
        "quantitative_consistency_check_attempted": False,
        "quantitative_consistency_status": "not_evaluated",
        "quantitative_consistency_reason": "validation_only_not_run_in_product",
        "quantitative_consistency_contradiction_flag": False,
        "quantitative_consistency_computed_winner": None,
        "quantitative_consistency_stated_winner": None,
        "quantitative_consistency_normalized_values": [],
    }
    assert result.quantitative_consistency_guard_telemetry == {
        "quantitative_consistency_guard_applied": False,
        "quantitative_consistency_guard_reason": (
            "validation_only_not_run_in_product"
        ),
        "quantitative_consistency_guard_output_mode": "unchanged",
        "quantitative_consistency_original_status": "not_evaluated",
        "quantitative_consistency_guard_final_answer_replaced": False,
        "guard_reason": "validation_only_not_run_in_product",
        "answer_rewritten": False,
    }
    assert result.observation.payload["quantitative_consistency_telemetry"] == dict(
        result.quantitative_consistency_telemetry
    )
    diagnostic = _evaluate(
        result.report,
        {"manifest": payload.quantitative_finalization_authority_manifest},
    )
    assert diagnostic["status"] == "rejected"
    assert result.report == "The unsupported difference is 200 km."


def test_af5b_compatibility_finalizer_keeps_parser_disagreement_non_authoritative() -> None:
    from tests.test_ag96i3af5b_author_response_finalization import (
        _consume_af5a_with_text,
        _execute_af5b,
        _kernel_through_af4d,
    )

    kernel = _kernel_through_af4d()
    _consume_af5a_with_text(kernel, "The unsupported difference is 200 km.")
    action = kernel.authorize_followup_author_response_finalization()
    result = _execute_af5b(kernel, action=action)
    kernel.reduce(result.observation)

    answer_before_evaluation = dict(kernel.state.final_answer_outcome)
    diagnostic = _evaluate(
        "The unsupported difference is 200 km.",
        {"manifest": build_quantitative_finalization_authority_manifest(
            source_fap_ref={"packet_id": "af5b-evaluator"}
        )},
    )
    assert diagnostic["status"] == "rejected"
    assert kernel.state.final_answer_outcome == answer_before_evaluation
    assert kernel.state.author_observation["final_answer_text"] == (
        "The unsupported difference is 200 km."
    )


def test_manifest_and_diagnostics_retain_no_private_or_full_text_material() -> None:
    private_sentinel = "PRIVATE-SENTINEL"
    bundle = build_quantitative_finalization_authority_bundle(
        source_fap_ref={
            "packet_id": "packet-private",
            "title": private_sentinel,
            "source_url": "https://private.invalid/material",
        },
        direct_component_entries=(
            {
                "entry_kind": "direct_component",
                "component_id": "component-private",
                "claim_id": "claim-private",
                "claim_digest": "claim-private-digest",
                "claim_text": (
                    f"{private_sentinel} Object A has a length of 100 km."
                ),
                "admission_status": "admitted",
                "current": True,
                "stale": False,
                "dprime_validation_ref": {
                    "artifact_id": "dprime-private",
                    "artifact_digest": "dprime-private-digest",
                    "title": private_sentinel,
                },
                "evidence_refs": [
                    {
                        "evidence_id": "evidence-private",
                        "title": private_sentinel,
                        "bounded_text": private_sentinel,
                    }
                ],
            },
        ),
    )
    diagnostic = _reject("Object B has a length of 100 km.", bundle)
    retained = {"manifest": bundle["manifest"], "diagnostic": diagnostic}
    serialized = repr(retained).casefold()

    assert "private-sentinel" not in serialized
    assert "object a has" not in serialized
    for forbidden in (
        "raw_prompt",
        "raw_model_response",
        "provider_payload",
        "bounded_text",
        "source_text",
        "full_trace",
        "private_log",
        "api_key",
    ):
        assert forbidden not in serialized


def test_manifest_digest_rejects_tampering() -> None:
    bundle = _source_bundle("Object A has a length of 100 km.")
    tampered = deepcopy(bundle["manifest"])
    tampered["authorized_numeric_claims"][0]["canonical_unit"] = "miles"

    with pytest.raises(QuantitativeFinalizationAuthorityError):
        validate_author_output_quantitative_authority(
            "Object A has a length of 100 miles.",
            manifest=tampered,
        )

    shape_tampered = deepcopy(bundle["manifest"])
    shape_tampered["authorized_numeric_claims"][0]["claim_text"] = (
        "Object A has a length of 100 km."
    )
    shape_core = {
        key: value
        for key, value in shape_tampered.items()
        if key != "manifest_digest"
    }
    shape_tampered["manifest_digest"] = sha256(
        json.dumps(shape_core, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    with pytest.raises(QuantitativeFinalizationAuthorityError):
        validate_author_output_quantitative_authority(
            "Object A has a length of 100 km.",
            manifest=shape_tampered,
        )
