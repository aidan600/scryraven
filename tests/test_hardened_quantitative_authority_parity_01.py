"""PRODUCT-PATH-REGRESSION: hardened quantitative authority parity.

Proof class: offline_product_path_proof.
Validation bucket: phase_focus.
Surface guarded: SufficiencyReadiness -> hardened FinalAnswerPacket ->
AuthorProseFinalization quantitative authority and fail-closed containment.
High-custody surface: source-bound numeric authority and complete installed S1
lineage; no acquisition, D-prime, retry, provider, or model behavior is opened.
Runtime/product path guarded: production RunKernel reducers and deterministic
AuthorProse finalization, using bounded offline fixtures.
Expected cost: focused offline execution under one minute.
Promotion posture: remain phase_focus; the detailed custody matrix is not an
ordinary fast_pr tax.
Demotion/retirement condition: replace only if the hardened route is retired or
an equivalent smaller production-path sentinel owns every guarded invariant.
Why not fast_pr: this is an exhaustive high-custody parity and laundering matrix.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

import pytest

from core.author_prose_finalization_runtime import reduce_author_prose_finalization
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.evidence_relative_analysis_packet import (
    build_evidence_relative_analysis_packet,
)
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
)
from core.final_answer_packet_hardening_runtime import (
    reduce_hardened_final_answer_packet,
)
from core.quantitative_finalization_authority import (
    QuantitativeFinalizationAuthorityError,
)
from core.quantitative_specialist_product_activation import (
    build_quantitative_product_specialist_policy,
    build_quantitative_product_specialist_registry,
)
from core.specialist_graph_runtime import (
    append_bound_proposal,
    append_specialist_result,
    bind_specialist_need_proposal,
    bind_specialist_work_authority,
    build_specialist_work_node,
    execute_specialist_capability,
    handoff_for_target,
    initialize_specialist_work_plane,
    mark_validator_consumption,
    specialist_digest,
)
from core.sufficiency_readiness_runtime import reduce_sufficiency_readiness
from tests.test_ag_analysis_gap_followup_search_01 import (
    _contract_ref_from_projection,
)
from tests.test_ag_analyst_evidence_relative_report_01 import (
    _records_by_status,
    _support_proposal,
)
from tests.test_ag_component_coverage_reliability_proof_01 import (
    _reduce_coverage,
)
from tests.test_ag_fetch_read_content_reference_01 import _readable_material
from tests.test_ag_search_result_candidate_packet_01 import _packet_from_state
from tests.test_ag_semantic_observation_admission_bridge_01 import (
    _bridge,
    _bridge_coverage_record,
)
from tests.test_quantitative_specialist_product_activation_01 import (
    _component_transient,
    _product_proposal,
    _rekey_specialist_handoff,
)

PRIVATE_SOURCE_SENTINEL = "PRIVATE_HARDENED_SOURCE_SENTINEL"
PRIVATE_SPECIALIST_SENTINEL = "PRIVATE_HARDENED_SPECIALIST_SENTINEL"


def _numeric_chain(*, bounded_source_text: str, safe_claim: str) -> dict[str, Any]:
    kernel, candidate_packet = _packet_from_state(candidate_count=1)
    material = _readable_material(
        candidate_packet,
        extra={
            "bounded_text": bounded_source_text,
            "bounded_text_char_count": len(bounded_source_text),
        },
    )
    fetch_packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        (material,),
    )
    ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=kernel,
        fetch_read_content_packet=fetch_packet,
    )
    record = _records_by_status(ledger_projection, "readable")[0]
    proposal = _support_proposal(record)
    proposal["proposal_summary"] = safe_claim
    contract_ref = _contract_ref_from_projection(ledger_projection)
    analysis_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=ledger_projection,
        analyst_proposal_records=(proposal,),
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref["contract_digest"],
    )
    chain: dict[str, Any] = {
        "kernel": kernel,
        "fetch_read_packet": fetch_packet,
        "ledger_projection": ledger_projection,
        "analysis_packet": analysis_packet,
    }
    admission = _bridge(chain)
    coverage_record = _bridge_coverage_record(chain, admission)
    coverage_projection = _reduce_coverage(kernel, coverage_record)
    return {
        **chain,
        "semantic_admission": admission,
        "coverage_projection": coverage_projection,
    }


def _source_authority_material(
    chain: Mapping[str, Any],
    *,
    source_proposition: str,
) -> dict[str, Any]:
    admission = chain["semantic_admission"]
    content_ref = admission.sanitized_content_reference.to_dict()
    coverage = dict(chain["coverage_projection"])
    observation = dict(coverage["accepted_observation_refs"][0])
    component = chain["kernel"].state.current_answer_contract[
        "accepted_answer_component_refs"
    ][0]
    metadata = dict(content_ref.get("metadata") or {})
    return {
        "source_proposition": source_proposition,
        "sanitized_content_reference": content_ref,
        "component_id": component["component_id"],
        "component_revision": component["component_revision"],
        "component_digest": component["component_digest"],
        "semantic_observation_id": observation["observation_id"],
        "semantic_observation_digest": observation["observation_digest"],
        "coverage_record_id": coverage["coverage_record_id"],
        "coverage_record_digest": coverage["coverage_record_digest"],
        "packet_evidence_id": metadata.get("fetch_read_content_packet_id"),
    }


def _reduce_hardened_route(
    chain: Mapping[str, Any],
    *,
    source_materials: Sequence[Mapping[str, Any]] = (),
    specialist_inputs: Sequence[Mapping[str, Any]] = (),
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    kernel = chain["kernel"]
    readiness = reduce_sufficiency_readiness(
        run_kernel=kernel,
        quantitative_source_authority_materials=source_materials,
        specialist_quantitative_authority_inputs=specialist_inputs,
    ).readiness_projection
    fap = reduce_hardened_final_answer_packet(
        run_kernel=kernel,
    ).final_answer_authority_projection
    author = reduce_author_prose_finalization(
        run_kernel=kernel,
    ).author_prose_projection
    return dict(readiness), dict(fap), dict(author)


def _assert_author_fails_closed(chain: Mapping[str, Any]) -> None:
    kernel = chain["kernel"]
    with pytest.raises(
        QuantitativeFinalizationAuthorityError,
        match="unsupported quantitative proposition",
    ) as exc_info:
        reduce_author_prose_finalization(run_kernel=kernel)
    diagnostic = exc_info.value.diagnostic
    assert diagnostic["status"] == "rejected"
    assert diagnostic["answer_rewritten"] is False
    assert diagnostic["answer_fragment_deleted"] is False
    assert diagnostic["author_retry_requested"] is False
    assert diagnostic["final_text_included"] is False
    assert kernel.state.author_prose_state == {}
    assert kernel.state.author_prose_projection == {}
    assert kernel.state.author_prose_history == []
    assert (
        sum(
            action.action_type.value == "author_prose_finalize"
            for action in kernel.state.issued_actions.values()
        )
        == 1
    )


@pytest.mark.parametrize(
    ("label", "source_claim", "safe_claim"),
    (
        ("integer", "The span is 17 km.", "The span is 17 km."),
        ("decimal", "The measured mass is 3.50 kg.", "The measured mass is 3.50 kg."),
        (
            "percentage",
            "The supported share is 25 percent.",
            "The supported share is 25 percent.",
        ),
        ("date", "The date is 2026-07-14.", "The date is 2026-07-14."),
        ("comma", "The diameter is 1,000 km.", "The diameter is 1000 km."),
    ),
)
def test_hardened_direct_source_numeric_propositions_reach_author_prose(
    label: str,
    source_claim: str,
    safe_claim: str,
) -> None:
    chain = _numeric_chain(
        bounded_source_text=f"{PRIVATE_SOURCE_SENTINEL}. {source_claim}",
        safe_claim=safe_claim,
    )
    source_material = _source_authority_material(
        chain,
        source_proposition=source_claim,
    )

    readiness, fap, author = _reduce_hardened_route(
        chain,
        source_materials=(source_material,),
    )

    component_id = next(iter(readiness["component_readiness_map"]))
    readiness_entry = readiness["component_readiness_map"][component_id]
    fap_entry = fap["component_packet_entries"][0]
    source_refs = readiness_entry["quantitative_source_authority_refs"]
    rows = fap["quantitative_finalization_authority_manifest"][
        "authorized_numeric_claims"
    ]
    assert source_refs
    assert fap_entry["quantitative_source_authority_refs"] == source_refs
    assert rows
    assert {row["authority_kind"] for row in rows} == {"direct_source_numeric"}
    assert safe_claim in author["answer_text"]
    assert author["quantitative_finalization_validation"]["status"] == "accepted"
    assert author["supported_safe_claims_created"] is True
    if label == "comma":
        assert any(row["normalized_numeric_value_text"] == "1000" for row in rows)
    if label == "integer":
        ref = source_refs[0]
        assert ref["component_id"] == component_id
        assert ref["component_digest"]
        assert ref["source_proposition_fingerprint"]
        assert ref["complete_literal_signature_digest"]
        assert ref["semantic_observation_ref"]["observation_id"]
        assert ref["content_reference_ref"]["content_ref_id"]
        assert ref["content_reference_ref"]["content_digest"]
        assert ref["component_coverage_ref"]["coverage_record_id"]
        assert ref["component_coverage_ref"]["coverage_record_digest"]
        assert ref["evidence_or_packet_evidence_ref"]["evidence_ref_id"]
        assert ref["current"] is True
        assert ref["stale"] is False
        assert ref["source_safe_claim_relationship"] == "exact_claim_fingerprint"
    retained = json.dumps(
        {
            "readiness": readiness,
            "fap": fap,
            "author": author,
            "issued_actions": [
                action.to_dict()
                for action in chain["kernel"].state.issued_actions.values()
            ],
        },
        sort_keys=True,
    )
    assert PRIVATE_SOURCE_SENTINEL not in retained
    assert "bounded_text" not in retained
    assert '"source_proposition":' not in retained


@pytest.mark.parametrize(
    ("source_text", "safe_claim", "source_propositions"),
    (
        (
            "Object A is 100 km. Object B is 60 km.",
            "The difference is 40 km.",
            ("Object A is 100 km.", "Object B is 60 km."),
        ),
        (
            "Object A is 100 km.",
            "Object A is 62.1 miles.",
            ("Object A is 100 km.",),
        ),
        (
            "Object A is 100 km.",
            "The difference is 100 km.",
            ("Object A is 100 km.",),
        ),
    ),
)
def test_hardened_dprime_only_arithmetic_conversion_and_same_value_laundering_fail(
    source_text: str,
    safe_claim: str,
    source_propositions: tuple[str, ...],
) -> None:
    chain = _numeric_chain(
        bounded_source_text=source_text,
        safe_claim=safe_claim,
    )
    materials = tuple(
        _source_authority_material(chain, source_proposition=item)
        for item in source_propositions
    )
    readiness = reduce_sufficiency_readiness(
        run_kernel=chain["kernel"],
        quantitative_source_authority_materials=materials,
    ).readiness_projection
    fap = reduce_hardened_final_answer_packet(
        run_kernel=chain["kernel"]
    ).final_answer_authority_projection

    component_id = next(iter(readiness["component_readiness_map"]))
    assert (
        readiness["component_readiness_map"][component_id].get(
            "quantitative_source_authority_refs", []
        )
        == []
    )
    assert (
        fap["quantitative_finalization_authority_manifest"]["authorized_numeric_claims"]
        == []
    )
    _assert_author_fails_closed(chain)


@pytest.mark.parametrize(
    "broken_binding",
    (
        "missing_content",
        "stale_content",
        "stale_coverage",
        "component_mismatch",
        "observation_mismatch",
    ),
)
def test_hardened_broken_source_custody_grants_no_numeric_authority(
    broken_binding: str,
) -> None:
    claim = "Object A is 100 km."
    chain = _numeric_chain(bounded_source_text=claim, safe_claim=claim)
    material = _source_authority_material(chain, source_proposition=claim)
    if broken_binding == "missing_content":
        material["sanitized_content_reference"]["content_ref_id"] = "content:missing"
    elif broken_binding == "stale_content":
        material["sanitized_content_reference"]["content_digest"] = "stale-content"
    elif broken_binding == "stale_coverage":
        material["coverage_record_digest"] = "stale-coverage"
    elif broken_binding == "component_mismatch":
        material["component_id"] = "component:other"
    elif broken_binding == "observation_mismatch":
        material["semantic_observation_digest"] = "stale-observation"

    readiness = reduce_sufficiency_readiness(
        run_kernel=chain["kernel"],
        quantitative_source_authority_materials=(material,),
    ).readiness_projection
    fap = reduce_hardened_final_answer_packet(
        run_kernel=chain["kernel"]
    ).final_answer_authority_projection

    component_id = next(iter(readiness["component_readiness_map"]))
    assert (
        readiness["component_readiness_map"][component_id].get(
            "quantitative_source_authority_refs", []
        )
        == []
    )
    assert (
        fap["quantitative_finalization_authority_manifest"]["authorized_numeric_claims"]
        == []
    )
    _assert_author_fails_closed(chain)


def _real_component_specialist_handoff(
    *,
    target_key: str = "component:quantitative",
    target_digest: str = "component-digest-quantitative",
    consumed: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    transient = _component_transient(
        evidence_text=(
            f"{PRIVATE_SPECIALIST_SENTINEL}. Reported values were 10 USD and 20 USD."
        )
    )
    transient["canonical_target_ref"] = {
        "target_kind": "component",
        "target_key": target_key,
        "target_revision": "1",
        "target_digest": target_digest,
    }
    registry = build_quantitative_product_specialist_registry()
    policy = build_quantitative_product_specialist_policy()
    proposal = bind_specialist_need_proposal(
        run_id="hardened-specialist-run",
        request_id="hardened-specialist-request",
        origin_role="component_analyst",
        origin_action_ref={"action_id": "component-analyst-action"},
        origin_artifact_ref={"artifact_id": "component-analyst-artifact"},
        proposal=_product_proposal(
            target_kind="component",
            target_key=target_key,
            capability_request=transient["capability_request"],
        ),
        canonical_target_ref=transient["canonical_target_ref"],
        accepted_contract_ref={"contract_id": "contract:hardened-specialist"},
        graph_ref=None,
        registry=registry,
        policy=policy,
    )
    work = build_specialist_work_node(
        proposal=proposal,
        bounded_input_digest=specialist_digest(transient),
        bounded_input_lineage_refs=({"lineage_id": "hardened-specialist-lineage"},),
        bounded_input_reconstruction_ref={
            "reconstruction_id": "hardened-specialist-reconstruction"
        },
    )
    authorization_ref = {"action_id": "specialist-execution-action"}
    lease_ref = {"lease_id": "specialist-lease"}
    work = bind_specialist_work_authority(
        work,
        authorization_action_ref=authorization_ref,
        grant_action_ref={"action_id": "specialist-grant-action"},
        dispatch_action_ref={"action_id": "specialist-dispatch-action"},
        lease_ref=lease_ref,
        specialist_budget_ref={"budget_id": "specialist-budget"},
    )
    result = execute_specialist_capability(
        registry=registry,
        work_node=work,
        transient_bounded_input=transient,
        authorization_action_ref=authorization_ref,
        lease_ref=lease_ref,
    )
    plane = initialize_specialist_work_plane(registry=registry, policy=policy)
    plane = append_bound_proposal(plane, proposal)
    plane = append_specialist_result(plane, work_node=work, result=result)
    handoff = handoff_for_target(
        plane,
        target_kind="component",
        target_key=target_key,
    )
    if consumed:
        dprime_ref = {
            "artifact_id": "component-dprime:hardened-specialist",
            "artifact_digest": "component-dprime-digest:hardened-specialist",
        }
        plane = mark_validator_consumption(
            plane,
            handoff_id=handoff["handoff_id"],
            route="component_dprime",
            validation_status="supported",
            dprime_artifact_ref=dprime_ref,
        )
        handoff = handoff_for_target(
            plane,
            target_kind="component",
            target_key=target_key,
            include_consumed=True,
        )
    return handoff, result


def _align_chain_to_component_specialist(
    chain: Mapping[str, Any],
    *,
    safe_claim: str,
) -> None:
    kernel = chain["kernel"]
    component_id = "component:quantitative"
    component_digest = "component-digest-quantitative"
    component_revision = "1"
    for contract in (
        kernel.state.current_answer_contract,
        kernel.state.initial_answer_contract,
    ):
        if not contract:
            continue
        component = contract["accepted_answer_component_refs"][0]
        component["component_id"] = component_id
        component["component_revision"] = component_revision
        component["component_digest"] = component_digest
    for admission in (
        kernel.state.semantic_observation_admission_projection,
        *kernel.state.semantic_observation_admission_history,
    ):
        admission["answer_component_id"] = component_id
        admission["component_revision"] = component_revision
        admission["component_digest"] = component_digest
        admission["claim_or_value"] = safe_claim
    for coverage in (
        kernel.state.component_coverage_projection,
        *kernel.state.component_coverage_history,
    ):
        coverage["answer_component_id"] = component_id
        coverage["component_revision"] = component_revision
        coverage["component_digest"] = component_digest
        for observation in coverage.get("accepted_observation_refs", []):
            observation["answer_component_id"] = component_id
            observation["component_revision"] = component_revision
            observation["component_contract_digest"] = component_digest
            observation["claim_or_value"] = safe_claim
        for content_ref in coverage.get("content_reference_bindings", []):
            content_ref["answer_component_id"] = component_id
            content_ref["component_revision"] = component_revision
            content_ref["component_contract_digest"] = component_digest


def test_real_component_s1_authority_survives_readiness_hardened_fap_and_author() -> (
    None
):
    claim = "The combined reported value is 30 USD."
    handoff, result = _real_component_specialist_handoff()
    chain = _numeric_chain(
        bounded_source_text="The source reports two input amounts.",
        safe_claim=claim,
    )
    _align_chain_to_component_specialist(chain, safe_claim=claim)

    readiness, fap, author = _reduce_hardened_route(
        chain,
        specialist_inputs=(
            {
                "specialist_need_handoff": handoff,
                "applicable_dprime_ref": handoff["validator_dprime_artifact_ref"],
            },
        ),
    )

    component = readiness["component_readiness_map"]["component:quantitative"]
    readiness_ref = component["specialist_quantitative_authority_ref"]
    fap_ref = fap["component_packet_entries"][0][
        "specialist_quantitative_authority_ref"
    ]
    rows = fap["quantitative_finalization_authority_manifest"][
        "authorized_numeric_claims"
    ]
    row = next(
        item for item in rows if item["authority_kind"] == "specialist_derived_numeric"
    )
    assert result["capability_id"] == "specialist.source_bound_calculation"
    assert result["execution_posture"] == "completed"
    assert readiness_ref == fap_ref
    assert readiness_ref["normalized_numeric_value_text"] == "30"
    assert readiness_ref["canonical_unit"] == "USD"
    assert readiness_ref["precision_posture"] == "exact_as_reported"
    assert (
        readiness_ref["claim_material_digest"]
        == sha256(claim.encode("utf-8")).hexdigest()
    )
    assert readiness_ref["applicable_dprime_consumption_ref"]["route"] == (
        "component_dprime"
    )
    assert readiness_ref["current"] is True
    assert readiness_ref["stale"] is False
    assert row["normalized_numeric_value_text"] == "30"
    assert row["canonical_unit"] == "USD"
    assert row["applicable_dprime_consumption_ref"]["route"] == ("component_dprime")
    assert author["quantitative_finalization_validation"]["status"] == "accepted"
    assert claim in author["answer_text"]
    assert "admitted_synthesis_entries" not in fap
    assert "synthesis_specialist_quantitative_authority_ref" not in fap
    retained = json.dumps(
        {
            "readiness": readiness,
            "fap": fap,
            "author": author,
            "actions": [
                action.to_dict()
                for action in chain["kernel"].state.issued_actions.values()
            ],
        },
        sort_keys=True,
    )
    assert PRIVATE_SPECIALIST_SENTINEL not in retained
    assert "quantitative_source_catalog" not in retained
    assert "capability_request" not in retained


@pytest.mark.parametrize(
    "broken_specialist",
    (
        "missing",
        "malformed",
        "unconsumed",
        "wrong_target",
        "unit_conflict",
    ),
)
def test_broken_component_specialist_lineage_grants_no_hardened_authority(
    broken_specialist: str,
) -> None:
    claim = "The combined reported value is 30 USD."
    inputs: tuple[dict[str, Any], ...] = ()
    if broken_specialist == "wrong_target":
        handoff, _result = _real_component_specialist_handoff(
            target_key="component:other",
            target_digest="component-digest-other",
        )
    else:
        handoff, _result = _real_component_specialist_handoff(
            consumed=broken_specialist != "unconsumed",
        )
    if broken_specialist == "malformed":
        handoff["handoff_digest"] = "malformed"
    elif broken_specialist == "unit_conflict":
        handoff["result"]["bounded_result"]["unit"] = "km"
        handoff = _rekey_specialist_handoff(handoff)
    if broken_specialist != "missing":
        inputs = (
            {
                "specialist_need_handoff": handoff,
                "applicable_dprime_ref": handoff.get(
                    "validator_dprime_artifact_ref",
                    {"artifact_id": "unconsumed-component-dprime"},
                ),
            },
        )
    chain = _numeric_chain(
        bounded_source_text="The source reports two input amounts.",
        safe_claim=claim,
    )
    _align_chain_to_component_specialist(chain, safe_claim=claim)
    readiness = reduce_sufficiency_readiness(
        run_kernel=chain["kernel"],
        specialist_quantitative_authority_inputs=inputs,
    ).readiness_projection
    fap = reduce_hardened_final_answer_packet(
        run_kernel=chain["kernel"]
    ).final_answer_authority_projection

    component = readiness["component_readiness_map"]["component:quantitative"]
    assert component.get("specialist_quantitative_authority_ref", {}) == {}
    assert (
        fap["component_packet_entries"][0].get(
            "specialist_quantitative_authority_ref", {}
        )
        == {}
    )
    assert (
        fap["quantitative_finalization_authority_manifest"]["authorized_numeric_claims"]
        == []
    )
    _assert_author_fails_closed(chain)
