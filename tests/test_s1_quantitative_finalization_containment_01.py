from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

import pytest

from core.author_execution_runtime import execute_author_action
from core.final_answer_packet import FinalAnswerAuthorInputPayload
from core.quantitative_finalization_authority import (
    QuantitativeFinalizationAuthorityError,
    build_quantitative_author_instruction_block,
    build_quantitative_finalization_authority_bundle,
    build_quantitative_finalization_authority_manifest,
    semantic_claim_fingerprint,
    specialist_quantitative_authority_ref_from_handoff,
    validate_author_output_quantitative_authority,
)
from core.run_kernel import (
    AUTHOR_EXECUTION_STAGE,
    ActionType,
    AuthorizedAction,
    ObservationType,
    RunKernelTransitionError,
)


def _source_bundle(*claims: str) -> dict[str, Any]:
    return build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "packet-direct", "readiness_status": "author_ready"},
        semantic_author_materialization=_source_materialization(*claims),
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
                "component_id": "component-a",
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
    values = {
        item["normalized_numeric_value_text"]
        for item in arithmetic["manifest"]["authorized_numeric_claims"]
    }
    assert values == {"100", "60"}
    assert "The difference is 40 km." not in arithmetic["transient_renderings"].values()
    _reject("The difference is 40 km.", arithmetic)
    assert _accept("Object A has a length of 100 km.", arithmetic)["status"] == (
        "accepted"
    )

    same_value = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "component-same-value"},
        semantic_author_materialization=source_materialization,
        direct_component_entries=(
            {**common, "claim_text": "The difference is 100 km."},
        ),
    )
    _reject("The difference is 100 km.", same_value)


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
        if item["semantic_claim_fingerprint_or_existing_equivalent"]
        == semantic_claim_fingerprint(claim_text)
    ]
    assert len(matching) == 1
    assert matching[0]["authority_kind"] == "direct_source_numeric"
    assert matching[0]["applicable_dprime_ref"] == {}
    assert matching[0]["claim_authority_posture"].endswith(
        "component_source_lineage_equivalent"
    )
    assert _accept(claim_text, bundle)["status"] == "accepted"


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
        assert _accept("Object A has a length of 100 km.", bundle)["status"] == (
            "accepted"
        )


def test_hardened_component_claim_requires_same_source_explicit_proposition() -> None:
    source_materialization = _source_materialization(
        "Object A has a length of 100 km."
    )
    direct = build_quantitative_finalization_authority_bundle(
        source_fap_ref={"packet_id": "hardened-direct"},
        semantic_author_materialization=source_materialization,
        component_packet_entries=(
            {
                "component_id": "component-a",
                "supported_safe_claim_allowed": True,
                "must_not_answer": False,
                "safe_answer_claim_text": "Object A has a length of 100 km.",
                "semantic_observation_ref": {"observation_id": "observation-a"},
                "component_coverage_ref": {"coverage_record_id": "coverage-a"},
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
                "component_id": "component-a",
                "supported_safe_claim_allowed": True,
                "must_not_answer": False,
                "safe_answer_claim_text": "Object A has a length of 62.1 miles.",
                "semantic_observation_ref": {"observation_id": "observation-a"},
                "component_coverage_ref": {"coverage_record_id": "coverage-a"},
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
    assert entry["applicable_dprime_consumption_ref"]["route"] == (
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


def test_author_executor_rejects_atomically_and_never_retries() -> None:
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

    with pytest.raises(QuantitativeFinalizationAuthorityError):
        execute_author_action(
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
    assert displayed == []


def test_af5b_compatibility_finalizer_cannot_admit_rejected_numeric_prose() -> None:
    from tests.test_ag96i3af5b_author_response_finalization import (
        _consume_af5a_with_text,
        _kernel_through_af4d,
    )

    kernel = _kernel_through_af4d()
    _consume_af5a_with_text(kernel, "The unsupported difference is 200 km.")

    with pytest.raises(RunKernelTransitionError):
        kernel.authorize_followup_author_response_finalization()

    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.followup_author_response_finalization_state == {}


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
