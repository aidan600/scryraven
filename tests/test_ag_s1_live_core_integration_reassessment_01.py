"""Offline sentinels for AG-S1-LIVE-CORE-INTEGRATION-REASSESSMENT-01.

Mode: PROOF.  Test class: phase_focus.
Proof class: offline_product_path_projection_proof.
Surface guarded: bounded-lane selection and final quantitative authority.
High-custody surface: FinalAnswerPacket/Author authority (diagnostic only).
Runtime path guarded: current deterministic owners consumed by run_pipeline.
Expected cost: sub-second, pure Python, no provider/search/model/fetch work.
Promotion posture: remain phase-local; do not add to a permanent bucket.
Retirement condition: retain independent route/prompt diagnostics until their
own licensed repairs; quantitative finalization containment is now passing.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from core.final_answer_runtime_adapter import (
    build_final_answer_packet,
    derive_author_input_payload,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    _normalize_semantic_output,
)
from core.quantitative_finalization_authority import (
    QuantitativeFinalizationAuthorityError,
    build_quantitative_finalization_authority_manifest,
    validate_author_output_quantitative_authority,
)
from core.quantitative_specialist_product_activation import (
    QUANTITATIVE_CAPABILITY_ID,
    QUANTITATIVE_CAPABILITY_REQUIREMENT,
    QUANTITATIVE_INPUT_SCHEMA_REF,
    QUANTITATIVE_OUTPUT_SCHEMA_REF,
    build_quantitative_product_specialist_policy,
    build_quantitative_product_specialist_registry,
)
from core.search_work_query_shape_runtime import (
    DeterministicSearchWorkRuntimeInput,
    build_deterministic_search_work_runtime_records,
)
from core.specialist_graph_runtime import bind_specialist_need_proposal

FIXED_QUERIES = {
    "A": """Using only NASA's official Earth and Mars facts pages, answer two separate components:

1. Report Earth's stated length of day and number of moons.
2. Report Mars's stated length of day and number of moons.

Then compare those stated facts qualitatively. Do not calculate totals, differences, ratios, averages, percentages, or converted values.""",
    "B": """Using NASA's official Earth facts page, answer two separately supported components:

1. Calculate the absolute difference between Earth's stated equatorial and polar diameters, using the exact source-visible kilometer literals.
2. Report Earth's stated length of day.

Do not round or convert units.""",
    "C": """Using NASA's official Earth facts page and Mars facts page as separate answer components:

1. Report Earth's stated equatorial diameter in kilometers.
2. Report Mars's stated equatorial diameter in kilometers.

Then calculate the absolute difference between those admitted component values, using the exact source-visible literals. Do not round or convert units.""",
    "D": """Using NASA's official Earth facts page and Mars facts page as separate answer components:

1. Report Earth's stated equatorial diameter in kilometers.
2. Report Mars's stated equatorial diameter in kilometers.

Then convert both diameters to miles and calculate their difference in miles. Use only the source-visible kilometer literals.""",
}


def _route_facts(query_id: str) -> tuple[bool, str | None, int]:
    records = build_deterministic_search_work_runtime_records(
        DeterministicSearchWorkRuntimeInput(
            contract_id=f"reassessment:{query_id}",
            run_contract_projection={},
            route_facts={},
            requested_mode="Balanced",
            safe_query_preview=FIXED_QUERIES[query_id],
        )
    )
    assessment = records.query_shape_assessment
    metadata = dict(assessment.metadata)
    return (
        metadata.get("explicit_factual_component_list") is True,
        metadata.get("requested_synthesis_directive"),
        len(assessment.component_candidates),
    )


@pytest.mark.parametrize("query_id", tuple(FIXED_QUERIES))
@pytest.mark.xfail(
    strict=True,
    reason="reassessment reproduces numbered-imperative query-shape nonqualification",
)
def test_fixed_campaign_query_should_select_typed_multicomponent_lane(
    query_id: str,
) -> None:
    explicit, synthesis, component_count = _route_facts(query_id)
    assert explicit is True
    assert synthesis is not None
    assert 2 <= component_count <= 5


def _valid_component_proposal() -> dict:
    return {
        "local_need_id": "quantitative-need-one",
        "capability_requirement": QUANTITATIVE_CAPABILITY_REQUIREMENT,
        "candidate_capability_hint": QUANTITATIVE_CAPABILITY_ID,
        "bounded_question": "Calculate the nominated exact source literals.",
        "target": {"target_kind": "component", "target_key": "component_01"},
        "posture": "required",
        "input_schema_ref": QUANTITATIVE_INPUT_SCHEMA_REF,
        "expected_output_schema_ref": QUANTITATIVE_OUTPUT_SCHEMA_REF,
        "recursion_depth": 0,
        "specialist_parent_ref": None,
        "capability_request": {
            "request_kind": "source_bound_calculation",
            "calculation_kind": "difference",
            "operands": [
                {
                    "local_operand_key": "a",
                    "source_local_key": "component_evidence",
                    "source_numeric_literal": "100 km",
                    "operand_role": "minuend",
                },
                {
                    "local_operand_key": "b",
                    "source_local_key": "component_evidence",
                    "source_numeric_literal": "60 km",
                    "operand_role": "subtrahend",
                },
            ],
            "claim_binding": {
                "proposed_result_literal": "40 km",
                "literal_occurrence": None,
                "expected_result_unit": "km",
            },
        },
    }


def test_exact_top_level_proposal_survives_normalization_and_binding() -> None:
    output = {
        "claim_text": "The difference is 40 km.",
        "support_status": "supported",
        "caveats": [],
        "nonclaims": [],
        "blockers": [],
        "specialist_need_proposal": _valid_component_proposal(),
    }
    normalized = _normalize_semantic_output(ROLE_COMPONENT_ANALYST, output)
    bound = bind_specialist_need_proposal(
        run_id="offline-run",
        request_id="offline-request",
        origin_role=ROLE_COMPONENT_ANALYST,
        origin_action_ref={"action_id": "offline-action"},
        origin_artifact_ref={"artifact_id": "offline-artifact"},
        proposal=normalized["specialist_need_proposal"],
        canonical_target_ref={
            "target_kind": "component",
            "target_key": "component_01",
        },
        accepted_contract_ref={"accepted_contract_version": 1},
        graph_ref={},
        registry=build_quantitative_product_specialist_registry(),
        policy=build_quantitative_product_specialist_policy(),
    )
    assert bound["proposal_authority"] == "accepted"


def test_nested_cross_proposal_is_absent_from_normalized_role_artifact() -> None:
    proposal = deepcopy(_valid_component_proposal())
    proposal["target"] = {
        "target_kind": "synthesis",
        "target_key": "difference",
    }
    output = {
        "synthesis_proposals": [
            {
                "synthesis_key": "difference",
                "claim_text": "The difference is 40 km.",
                "relationship_type": "difference",
                "component_inputs": ["component_01", "component_02"],
                "synthesis_inputs": [],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
                "specialist_need_proposal": proposal,
            }
        ]
    }
    normalized = _normalize_semantic_output(ROLE_CROSS_COMPONENT_ANALYST, output)
    assert "specialist_need_proposal" not in normalized


@pytest.mark.xfail(
    strict=True,
    reason="FAP appends authority but currently preserves pre-FAP quantitative prompt text",
)
def test_insufficient_fap_should_not_preserve_unauthorized_conversion_prompt() -> None:
    prompt = (
        "Analysis: source facts are 100 km and 60 km; convert both to miles "
        "and state the mile difference."
    )
    packet = build_final_answer_packet(
        run_id="offline-fap",
        final_evidence=[],
        corpus_weak=True,
        failure_card_payload={"show": False},
        synth_was_insufficient=True,
    )
    _, payload = derive_author_input_payload(
        packet,
        prompt=prompt,
        author_system_prompt_key="author",
        author_effort="medium",
    )
    assert prompt not in payload.prompt


def test_finalization_validator_rejects_unsupported_generic_conversion() -> None:
    answer = "They are 62.1 and 37.3 miles; the difference is 24.8 miles."
    manifest = build_quantitative_finalization_authority_manifest(
        source_fap_ref={
            "packet_id": "reassessment-d02",
            "readiness_status": "author_ready",
        },
        semantic_author_materialization={
            "available": True,
            "bounded_material_complete": True,
            "bounded_material_refs": [
                {
                    "component_id": "earth",
                    "content_ref_id": "earth-diameter",
                    "content_digest": "earth-diameter-digest",
                    "evidence_ref_id": "earth-evidence",
                    "packet_evidence_id": "earth-packet-evidence",
                    "source_id": 1,
                    "bounded_text": "Earth's stated diameter is 100 km.",
                },
                {
                    "component_id": "mars",
                    "content_ref_id": "mars-diameter",
                    "content_digest": "mars-diameter-digest",
                    "evidence_ref_id": "mars-evidence",
                    "packet_evidence_id": "mars-packet-evidence",
                    "source_id": 2,
                    "bounded_text": "Mars's stated diameter is 60 km.",
                },
            ],
        },
    )
    with pytest.raises(QuantitativeFinalizationAuthorityError) as exc_info:
        validate_author_output_quantitative_authority(answer, manifest=manifest)
    assert exc_info.value.diagnostic["status"] == "rejected"
    assert exc_info.value.diagnostic["answer_rewritten"] is False
    assert exc_info.value.diagnostic["author_retry_requested"] is False
