import json
from dataclasses import replace
from pathlib import Path

import pytest

from core.final_answer_packet import (
    CitationEligibilityRecord,
    CitationEligibilityStatus,
    CitationRequirementStatus,
    ClaimPosture,
    EvidenceAuthorityStatus,
    FinalAnswerPacket,
    FinalAnswerReadinessStatus,
    FinalEvidenceRecord,
    SourceObligationStatus,
)
from core.final_answer_packet_runtime import (
    _blocked_author_payload_ref,
    build_safe_blocked_fap_summary,
)
from core.final_answer_runtime_adapter import (
    build_final_answer_packet,
    build_packet_derived_citation_source_handoff_state,
    derive_author_input_payload,
    final_answer_packet_compatibility_refs,
    final_answer_packet_trace_fragment,
)
from core.official_current_source_custody import OfficialCurrentSourceCustodyState
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    SufficiencyPosture,
)

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_DIGEST = "b" * 64


def _passage(**overrides):
    data = {
        "source_id": 1,
        "url": "https://irs.gov/pub/notice",
        "title": "IRS notice",
        "text": "Official text about a current rule.",
        "source_tier": "official",
        "source_class": "official_current_rules",
    }
    data.update(overrides)
    return data


def test_ag89d_packet_status_vocabulary_and_required_reasons() -> None:
    assert EvidenceAuthorityStatus.EVIDENCE_ALLOWED.value == "evidence_allowed"
    assert EvidenceAuthorityStatus.EVIDENCE_EXCLUDED.value == "evidence_excluded"
    assert CitationEligibilityStatus.CITATION_ELIGIBLE.value == "citation_eligible"
    assert CitationEligibilityStatus.CITATION_INELIGIBLE.value == "citation_ineligible"
    assert CitationRequirementStatus.CITATION_REQUIRED.value == "citation_required"
    assert SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED.value == "official_current_unsatisfied"
    assert ClaimPosture.WEAK_CORPUS_AUTHORIZED.value == "weak_corpus_authorized"

    with pytest.raises(ValueError):
        FinalEvidenceRecord(evidence_id="e1", status="evidence_excluded")
    with pytest.raises(ValueError):
        CitationEligibilityRecord(
            citation_id="c1",
            evidence_id="e1",
            status="citation_ineligible",
        )


def test_ag89d_json_safe_serialization_and_redaction() -> None:
    packet = build_final_answer_packet(
        run_id="r1",
        final_evidence=[_passage(text="raw provider_payload secret should redact")],
        query_lineage_refs={"raw_provider_payload": {"secret": "abc"}},
    )
    payload = packet.to_dict()
    encoded = json.dumps(payload, sort_keys=True)
    assert "raw provider_payload secret" not in encoded
    assert "[redacted]" in encoded or "[redacted protected material]" in encoded
    assert payload["evidence_allowed"][0]["text_hash"]
    assert "text" not in payload["evidence_allowed"][0]


def test_ag89d_official_current_unsatisfied_becomes_missing_obligation_not_citation_satisfaction() -> None:
    custody = OfficialCurrentSourceCustodyState.for_required_source_classes(
        ["official_current_rules"]
    )
    packet = build_final_answer_packet(
        run_id="r2",
        final_evidence=[_passage(source_id=7, source_class="secondary_analysis")],
        source_obligation_projection=custody.to_dict(),
        evidence_sufficient=True,
    )
    assert packet.citation_eligible[0].source_id == 7
    assert packet.source_obligations[0].status is SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED
    assert packet.official_current_custody_summary["unsatisfied_source_classes"] == [
        "official_current_rules"
    ]
    assert "official_current_unsatisfied:official_current_rules" in packet.mandatory_caveats
    assert ClaimPosture.INSUFFICIENT_EVIDENCE in packet.claim_postures


def test_ag89d_citation_eligible_evidence_is_derived_from_packet_records() -> None:
    packet = build_final_answer_packet(run_id="r3", final_evidence=[_passage(source_id=4)])
    assert [record.source_id for record in packet.citation_eligible] == [4]
    trace = final_answer_packet_trace_fragment(packet)["final_answer_packet"]
    assert trace["citation_eligible"][0]["evidence_id"] == packet.evidence_allowed[0].evidence_id


def test_ag89d_citation_ineligible_and_excluded_evidence_carry_reasons() -> None:
    packet = build_final_answer_packet(
        run_id="r4",
        final_evidence=[_passage(source_id=None), _passage(source_id=2, url="")],
    )
    reasons = {record.reason for record in packet.citation_ineligible}
    assert reasons == {"source_id_missing", "source_url_missing"}
    excluded = FinalEvidenceRecord(
        evidence_id="excluded-1",
        status=EvidenceAuthorityStatus.EVIDENCE_EXCLUDED,
        reason="not_selected_for_final_answer",
    )
    assert excluded.to_dict()["reason"] == "not_selected_for_final_answer"


def test_ag89d_blocked_payload_exposes_only_safe_quantitative_preflight() -> None:
    packet = build_final_answer_packet(
        run_id="r4-quantitative-preflight",
        final_evidence=[_passage(source_id=4)],
    ).with_quantitative_authority_block(
        {
            "schema_version": "quantitative_fap_authority_preflight_v1",
            "status": "blocked",
            "author_invocation_allowed": False,
            "post_author_semantic_validation_required": False,
            "required_numeric_claim_count": 2,
            "authorized_numeric_claim_count": 0,
            "blocked_numeric_claim_count": 1,
            "reason_codes": ["missing_direct_source_binding"],
            "reason_refs": [
                {
                    "claim_kind": "direct_component",
                    "claim_ref_digest": "a" * 64,
                    "literal_count": 2,
                    "reason_code": "missing_direct_source_binding",
                    "specialist_declared": False,
                    "raw_prompt": "must not escape into a blocked payload",
                }
            ],
            "provider_payload": "must not escape into a blocked payload",
        }
    )

    payload = _blocked_author_payload_ref(packet)
    observed = payload["quantitative_fap_authority_preflight"]
    assert observed == {
        "schema_version": "blocked_fap_quantitative_authority_safe_summary_v1",
        "status": "blocked",
        "author_invocation_allowed": False,
        "post_author_semantic_validation_required": False,
        "required_numeric_claim_count": 2,
        "authorized_numeric_claim_count": 0,
        "blocked_numeric_claim_count": 1,
        "reason_codes": ["missing_direct_source_binding"],
        "reason_refs": [
            {
                "reason_code": "missing_direct_source_binding",
                "claim_kind": "direct_component",
                "literal_count": 2,
                "specialist_declared": False,
            }
        ],
    }
    assert payload["authority_payload"]["quantitative_fap_authority_preflight"] == observed
    encoded = json.dumps(payload, sort_keys=True)
    assert "must not escape into a blocked payload" not in encoded
    assert "claim_ref_digest" not in encoded


def test_ag89d_blocked_summary_preserves_only_safe_quantitative_preflight() -> None:
    packet = build_final_answer_packet(
        run_id="r4-quantitative-preflight-summary",
        final_evidence=[_passage(source_id=4)],
    ).with_quantitative_authority_block(
        {
            "schema_version": "quantitative_fap_authority_preflight_v1",
            "status": "blocked",
            "author_invocation_allowed": False,
            "post_author_semantic_validation_required": False,
            "required_numeric_claim_count": 2,
            "authorized_numeric_claim_count": 0,
            "blocked_numeric_claim_count": 1,
            "reason_codes": ["missing_direct_source_binding"],
            "reason_refs": [
                {
                    "reason_code": "missing_direct_source_binding",
                    "claim_kind": "direct_component",
                    "literal_count": 2,
                    "specialist_declared": False,
                    "raw_prompt": "must not escape into the blocked summary",
                }
            ],
            "provider_payload": "must not escape into the blocked summary",
        }
    )

    payload = _blocked_author_payload_ref(packet)
    summary = build_safe_blocked_fap_summary(
        {
            "packet_id": packet.packet_id,
            "readiness_status": packet.readiness_status.value,
            "author_payload_ref": payload,
        }
    )

    assert summary["quantitative_fap_authority_preflight"] == payload[
        "quantitative_fap_authority_preflight"
    ]
    encoded = json.dumps(summary, sort_keys=True)
    assert "must not escape into the blocked summary" not in encoded
    assert "provider_payload" not in encoded


def test_ag89d_mandatory_caveats_and_prohibited_upgrades_are_packet_fields() -> None:
    packet = build_final_answer_packet(
        run_id="r5",
        final_evidence=[_passage()],
        corpus_weak=True,
        synth_was_insufficient=True,
        failure_card_payload={"show": True, "reason": "no_useful_content"},
        author_notes="Use only weak evidence.",
    )
    assert "weak_corpus_must_be_caveated" in packet.mandatory_caveats
    assert "synthesis_insufficient_must_be_caveated" in packet.mandatory_caveats
    assert "failure_card_authorized:no_useful_content" in packet.mandatory_caveats
    assert "do_not_upgrade_citation_ineligible_evidence" in packet.prohibited_upgrades


def test_ag89d_author_input_payload_is_derived_from_packet() -> None:
    packet = build_final_answer_packet(
        run_id="r6",
        final_evidence=[_passage(source_id=11)],
        author_evidence=[_passage(source_id=11)],
    )
    packet, payload = derive_author_input_payload(
        packet,
        prompt="unchanged author prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )
    assert payload.prompt.startswith("unchanged author prompt")
    assert "FINAL ANSWER PACKET AUTHORITY" in payload.prompt
    assert "Use only these citation-eligible Source IDs for citations: 11" in payload.prompt
    assert "do_not_upgrade_citation_ineligible_evidence" in payload.prompt
    assert payload.citation_source_ids == (11,)
    assert packet.author_input_refs["status"] == "author_input_ready"
    assert packet.author_input_refs["prompt_text_included"] is False
    assert packet.author_input_refs["authority_block_length"] > 0


def test_ag89d_unsatisfied_custody_reaches_author_facing_payload() -> None:
    custody = OfficialCurrentSourceCustodyState.for_required_source_classes(
        ["official_current_rules"]
    )
    packet = build_final_answer_packet(
        run_id="r6b",
        final_evidence=[_passage(source_id=21, source_class="secondary_analysis")],
        source_obligation_projection=custody.to_dict(),
    )
    packet, payload = derive_author_input_payload(
        packet,
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )
    assert payload.missing_source_obligations[0]["status"] == "official_current_unsatisfied"
    assert "official_current_unsatisfied" in payload.prompt
    assert "official_current_unsatisfied:official_current_rules" in payload.prompt


def test_ag89d_citation_ineligible_evidence_is_not_author_citable() -> None:
    packet = build_final_answer_packet(
        run_id="r6c",
        final_evidence=[_passage(source_id=31), _passage(source_id=None)],
    )
    _packet, payload = derive_author_input_payload(
        packet,
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )
    assert payload.citation_source_ids == (31,)
    assert payload.citation_ineligible_refs[0]["reason"] == "source_id_missing"
    assert "Do not cite citation-ineligible evidence" in payload.prompt
    assert "source_id_missing" in payload.prompt


def test_ag96g3_packet_consumes_sufficiency_final_packet_inputs_as_authority() -> None:
    sufficiency_projection = RunSufficiencyJudgment(
        judgment_id="ag96g3-contradictory-packet-inputs",
        decision=RunSufficiencyDecision.READY_DIRECT,
        final_answer_posture=SufficiencyPosture.DIRECT_ANSWER,
        final_answer_allowed=True,
        final_packet_inputs={
            "decision": "source_bound_numeric_unknown",
            "final_answer_posture": "partial_answer",
            "final_answer_allowed": True,
            "required_obligations_satisfied": False,
            "readiness_status": "insufficient_authorized",
            "readiness_reasons": ["source_bound_numeric_value_remains_unknown"],
            "claim_postures": ["insufficient_evidence"],
            "missing_required_obligations": [
                {
                    "requirement_id": "req-numeric",
                    "requirement_kind": "source_bound_numeric",
                    "required_source_class": "sourced_numeric_values",
                    "status": "missing",
                    "reason": "numeric_value_not_extracted",
                }
            ],
            "partial_obligations": [
                {
                    "requirement_id": "req-secondary-context",
                    "requirement_kind": "reputable_secondary",
                    "required_source_class": "reputable_secondary",
                    "status": "partial",
                }
            ],
            "satisfied_obligations": [
                {
                    "requirement_id": "req-official",
                    "requirement_kind": "official_current",
                    "required_source_class": "official_current_rules",
                    "status": "satisfied",
                    "satisfied_candidate_ids": ["candidate-official"],
                }
            ],
            "source_bound_numeric_unknowns": [
                {
                    "requirement_id": "req-numeric",
                    "reason": "numeric_value_not_extracted",
                }
            ],
            "mandatory_caveats": ["numeric_value_not_extracted_must_be_caveated"],
            "prohibited_upgrades": ["do_not_present_numeric_unknown_as_known"],
            "behavior_boundary_flags": {
                "provider_search_behavior_changed": False,
                "retrieval_behavior_changed": False,
                "prompt_behavior_changed": False,
                "citation_behavior_changed": False,
                "author_prose_behavior_changed": False,
            },
        },
    ).to_projection()
    packet = build_final_answer_packet(
        run_id="ag96g3-authority",
        final_evidence=[_passage(source_id=81)],
        sufficiency_judgment_projection=sufficiency_projection,
    )
    packet, payload = derive_author_input_payload(
        packet,
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert packet.readiness_status.value == "insufficient_authorized"
    assert packet.sufficiency_decision == "source_bound_numeric_unknown"
    assert packet.final_answer_posture == "partial_answer"
    assert packet.required_obligations_satisfied is False
    assert packet.missing_required_obligations[0]["requirement_id"] == "req-numeric"
    assert packet.partial_obligations[0]["requirement_id"] == "req-secondary-context"
    assert packet.satisfied_obligations[0]["requirement_id"] == "req-official"
    assert packet.source_bound_numeric_unknowns[0]["requirement_id"] == "req-numeric"
    assert packet.behavior_boundary_flags["citation_behavior_changed"] is False
    assert payload.authority_payload["readiness_status"] == "insufficient_authorized"
    assert payload.authority_payload["claim_postures"] == ["insufficient_evidence"]
    assert payload.authority_payload["source_bound_numeric_unknowns"]
    assert payload.authority_payload["partial_source_obligations"]
    assert payload.authority_payload["satisfied_source_obligations"]


def test_ag96g3_citation_ineligible_prompt_refs_are_stable_across_run_ids() -> None:
    sufficiency_projection = RunSufficiencyJudgment(
        judgment_id="ag96g3-stable-citation-ineligible",
        decision=RunSufficiencyDecision.PARTIAL_ANSWER_AUTHORIZED,
        final_answer_posture=SufficiencyPosture.PARTIAL_ANSWER,
        final_answer_allowed=True,
        final_packet_inputs={
            "decision": "partial_answer_authorized",
            "final_answer_posture": "partial_answer",
            "final_answer_allowed": True,
            "required_obligations_satisfied": False,
            "readiness_status": "insufficient_authorized",
            "readiness_reasons": ["required_obligations_missing"],
            "claim_postures": ["insufficient_evidence"],
            "missing_required_obligations": [
                {
                    "requirement_id": "req-official",
                    "requirement_kind": "official_current",
                    "required_source_class": "official_current_rules",
                    "status": "missing",
                    "reason": "required_evidence_ledger_gap",
                }
            ],
            "partial_obligations": [],
            "satisfied_obligations": [],
            "source_bound_numeric_unknowns": [],
            "mandatory_caveats": ["missing_source_custody_must_be_caveated"],
            "prohibited_upgrades": [
                "do_not_treat_missing_official_current_custody_as_satisfied"
            ],
            "behavior_boundary_flags": {
                "provider_search_behavior_changed": False,
                "retrieval_behavior_changed": False,
                "prompt_behavior_changed": False,
                "citation_behavior_changed": False,
                "author_prose_behavior_changed": False,
            },
        },
    ).to_projection()
    evidence = _passage(
        source_id=91,
        url="https://example.com/context",
        title="Context source",
        source_tier="secondary",
        source_class="reputable_secondary",
    )

    packet_a = build_final_answer_packet(
        run_id="stable-a",
        final_evidence=[evidence],
        sufficiency_judgment_projection=sufficiency_projection,
    )
    packet_b = build_final_answer_packet(
        run_id="stable-b",
        final_evidence=[evidence],
        sufficiency_judgment_projection=sufficiency_projection,
    )
    _packet_a, payload_a = derive_author_input_payload(
        packet_a,
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )
    _packet_b, payload_b = derive_author_input_payload(
        packet_b,
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )

    line_a = next(
        line
        for line in payload_a.authority_block.splitlines()
        if line.startswith("- Do not cite citation-ineligible evidence:")
    )
    line_b = next(
        line
        for line in payload_b.authority_block.splitlines()
        if line.startswith("- Do not cite citation-ineligible evidence:")
    )
    assert line_a == line_b
    assert "final-answer-packet-stable-a" not in line_a
    assert "final-answer-packet-stable-b" not in line_b
    assert "evidence_position=1" in line_a
    assert "source_id=91" in line_a
    assert "domain=example.com" in line_a
    assert "title=Context source" in line_a
    assert "reason=sufficiency_has_no_satisfied_source_obligation" in line_a
    assert payload_a.citation_ineligible_refs[0]["evidence_id"] != (
        payload_b.citation_ineligible_refs[0]["evidence_id"]
    )


def test_ag89d_legacy_citation_handoff_is_demoted_behind_packet() -> None:
    packet = build_final_answer_packet(
        run_id="r7",
        final_evidence=[_passage(source_id=12)],
        ordered_sources=["- [12] [IRS notice](https://irs.gov/pub/notice)"],
        unique_source_urls={"https://irs.gov/pub/notice": 12},
    ).with_citation_observations({"final_answer_source_ids_used": [12]})
    state = build_packet_derived_citation_source_handoff_state(packet, run_id="r7")
    trace = state.to_trace_fragment()["citation_source_handoff_contract"]
    assert trace["final_evidence_bundle_ref"]["authority"] == "final_answer_packet"
    assert trace["citation_eligibility"]["citation_eligible_source_ids"] == [12]
    assert trace["ordered_source_list"]["ordered_source_count"] == 1
    assert trace["citation_observations"]["final_answer_source_telemetry"]["final_answer_source_ids_used"] == [12]


def test_ag89e_legacy_final_evidence_refs_are_packet_derived() -> None:
    packet = build_final_answer_packet(
        run_id="r7b",
        final_evidence=[_passage(source_id=42)],
        author_evidence=[_passage(source_id=42)],
        ordered_sources=["- [42] [IRS notice](https://irs.gov/pub/notice)"],
        unique_source_urls={"https://irs.gov/pub/notice": 42},
    ).with_citation_observations({"final_answer_source_ids_used": [42]})

    refs = final_answer_packet_compatibility_refs(
        packet, final_evidence_snapshot_recorded=True
    )

    assert refs["final_evidence_ref"] == {
        "packet_id": packet.packet_id,
        "final_evidence_count": 1,
        "authority": "final_answer_packet",
        "author_evidence_count": 1,
        "ordered_source_count": 1,
        "unique_source_url_count": 1,
        "trace_mode": "final_answer_packet_compatibility_projection",
    }
    assert refs["ledger_ref"] == {
        "packet_id": packet.packet_id,
        "final_evidence_count": 1,
        "authority": "final_answer_packet",
        "final_evidence_snapshot_recorded": True,
    }
    assert refs["source_telemetry_ref"]["source_ids"] == [42]
    assert refs["source_telemetry_ref"]["ordered_sources"] == [
        "- [42] [IRS notice](https://irs.gov/pub/notice)"
    ]
    assert refs["source_telemetry_ref"]["final_answer_source_telemetry"] == {
        "final_answer_source_ids_used": [42]
    }
    assert refs["final_evidence_bundle_ref"] == {
        "packet_id": packet.packet_id,
        "final_evidence_count": 1,
        "authority": "final_answer_packet",
        "citation_eligible_count": 1,
    }


def test_ag89e_author_evidence_count_preserves_packet_recorded_zero() -> None:
    packet = build_final_answer_packet(
        run_id="r7d",
        final_evidence=[_passage(source_id=45)],
        author_evidence=[],
    )

    refs = final_answer_packet_compatibility_refs(packet)

    assert packet.author_input_refs["author_evidence_ids"] == [
        packet.evidence_allowed[0].evidence_id
    ]
    assert packet.author_input_refs["author_evidence_count"] == 0
    assert refs["final_evidence_ref"]["author_evidence_count"] == 0


def test_ag89e_packet_derived_citation_handoff_uses_packet_refs_by_default() -> None:
    packet = build_final_answer_packet(
        run_id="r7c",
        final_evidence=[_passage(source_id=44)],
        ordered_sources=["- [44] [IRS notice](https://irs.gov/pub/notice)"],
        unique_source_urls={"https://irs.gov/pub/notice": 44},
    ).with_citation_observations({"final_answer_source_ids_used": [44]})

    state = build_packet_derived_citation_source_handoff_state(packet, run_id="r7c")
    trace = state.to_trace_fragment()["citation_source_handoff_contract"]

    assert trace["final_evidence_bundle_ref"]["authority"] == "final_answer_packet"
    assert trace["final_evidence_bundle_ref"]["packet_id"] == packet.packet_id
    assert trace["ledger_ref"]["authority"] == "final_answer_packet"
    assert trace["source_telemetry_ref"]["authority"] == "final_answer_packet"
    assert trace["source_telemetry_ref"]["source_ids"] == [44]

def test_ag90b_author_runtime_assembly_scope_matches_bounded_builder() -> None:
    from core.final_answer_runtime_assembly import (
        assemble_final_answer_author_runtime,
        assemble_final_answer_author_runtime_from_scope,
    )

    class QueryAuthority:
        def to_trace_fragment(self):
            return {"query_plan": {"plan_id": "qp-ag90b"}}

    passage = _passage(source_id=61)
    direct = assemble_final_answer_author_runtime(
        run_id="ag90b-author",
        query="What is the current IRS notice?",
        intent="research",
        report_type="general",
        query_type="general",
        core_topic="IRS notice",
        primary_entity="IRS",
        anchor_packet_telemetry={},
        final_top_evidence=[passage],
        author_evidence=[passage],
        ordered_sources=["- [61] [IRS notice](https://irs.gov/pub/notice)"],
        unique_source_urls={"https://irs.gov/pub/notice": 61},
        query_lineage_refs={"query_plan": {"plan_id": "qp-ag90b"}},
        corpus_weak=False,
        failure_card_payload={"show": False, "reason": None},
        conflicts_present=False,
        synth_was_insufficient=False,
        author_notes="",
        author_prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )
    scoped = assemble_final_answer_author_runtime_from_scope(
        {
            "run_id": "ag90b-author",
            "query": "What is the current IRS notice?",
            "intent": "research",
            "report_type": "general",
            "query_type": "general",
            "core_topic": "IRS notice",
            "primary_entity": "IRS",
            "anchor_packet_telemetry": {},
            "final_top_evidence": [passage],
            "author_evidence": [passage],
            "ordered_sources": ["- [61] [IRS notice](https://irs.gov/pub/notice)"],
            "unique_source_urls": {"https://irs.gov/pub/notice": 61},
            "query_authority": QueryAuthority(),
            "corpus_weak": False,
            "_pre_gate_failure_card_show": False,
            "_pre_gate_failure_card_reason": None,
            "scrutineer_flags": [],
            "synth_was_insufficient": False,
            "author_notes": "",
            "author_prompt": "base prompt",
            "author_system_prompt_key": "author",
            "_author_effort": "low",
        }
    )

    assert scoped.packet.to_dict() == direct.packet.to_dict()
    assert scoped.author_payload.prompt == direct.author_payload.prompt
    assert scoped.author_system_prompt_key == "author"
    assert scoped.author_effort == "low"


def test_ag90b_citation_runtime_assembly_is_packet_derived_and_legacy_compatible() -> None:
    from types import SimpleNamespace

    from core.final_answer_runtime_assembly import assemble_final_answer_citation_runtime

    passage = _passage(source_id=71)
    packet = build_final_answer_packet(
        run_id="ag90b-citation",
        final_evidence=[passage],
        author_evidence=[passage],
        ordered_sources=["- [71] [IRS notice](https://irs.gov/pub/notice)"],
        unique_source_urls={"https://irs.gov/pub/notice": 71},
    )
    final_source_telemetry_inputs = SimpleNamespace(
        source_ids=[71],
        unique_source_url_count=1,
        ordered_sources=["- [71] [IRS notice](https://irs.gov/pub/notice)"],
        final_evidence_count=1,
        final_answer_source_telemetry={},
        final_evidence_snapshot_payload={"final_top_evidence": [passage]},
    )

    assembled = assemble_final_answer_citation_runtime(
        packet=packet,
        run_id="ag90b-citation",
        final_answer_source_telemetry={"final_answer_source_ids_used": [71]},
        final_source_telemetry_inputs=final_source_telemetry_inputs,
        answer_contract_ref={"answer_contract": {"available": True}},
        analyst_skipped=False,
        analyst_skip_reason=None,
        post_retrieval_fast_path_used=False,
        pre_analyst_gate_signals={"analyst_should_run": True},
        analyst_skipped_after_economist=False,
        analyst_after_economist_skip_reason=None,
        economist_output_used_as_analysis=False,
        analyst_evidence=[passage],
        analyst_context_prefix="ctx",
        linkup_block_included=False,
        quantitative_packet_injected=False,
        missing_target_metric_directive_emitted=False,
        corpus_weak=False,
        failure_card_payload={"show": False, "reason": None},
        author_notes="",
        author_evidence=[passage],
        selected_evidence=[passage],
        final_evidence=[passage],
        ordered_sources=["- [71] [IRS notice](https://irs.gov/pub/notice)"],
        unique_source_urls={"https://irs.gov/pub/notice": 71},
        author_evidence_block="[Source 71] IRS notice",
        author_prompt="base prompt",
        complexity="low",
        author_system_prompt_key="author",
        author_effort="low",
        includes_analysis=False,
        includes_recency_notes=False,
        includes_author_notes=False,
        image_context_active=False,
        pre_analyst_gate_ref={},
        weak_failure_gate_state=None,
        retrieval_loop_state={},
        router_query_preparation_state={},
    )

    citation_trace = assembled.citation_source_handoff_trace_fragment[
        "citation_source_handoff_contract"
    ]
    assert assembled.packet.author_input_refs["final_answer_source_telemetry"] == {
        "final_answer_source_ids_used": [71]
    }
    assert citation_trace["ledger_ref"]["authority"] == "final_answer_packet"
    assert citation_trace["ledger_ref"]["final_evidence_snapshot_recorded"] is True
    assert citation_trace["source_telemetry_ref"]["source_ids"] == [71]
    assert assembled.unique_source_urls == {"https://irs.gov/pub/notice": 71}
    assert assembled.packet_trace_fragment["final_answer_packet"] == assembled.packet.to_dict()


def test_ag89d_trace_projection_is_derived_from_packet() -> None:
    packet = build_final_answer_packet(
        run_id="r8",
        final_evidence=[_passage(source_id=14)],
        query_lineage_refs={"query_plan": {"plan_id": "qp-r8"}},
    )
    trace = final_answer_packet_trace_fragment(packet)
    assert list(trace) == ["final_answer_packet"]
    assert trace["final_answer_packet"] == packet.to_dict()
    assert trace["final_answer_packet"]["query_lineage_refs"]["query_plan"]["plan_id"] == "qp-r8"


def test_ag89d_static_orchestrator_wiring_does_not_change_protected_surfaces() -> None:
    text = (ROOT / "core" / "pipeline_orchestrator.py").read_text()
    helper_text = (ROOT / "core" / "final_answer_runtime_assembly.py").read_text()
    packet_runtime = (ROOT / "core" / "final_answer_packet_runtime.py").read_text()
    author_runtime = (ROOT / "core" / "author_execution_runtime.py").read_text()
    retrieval_helper_text = (ROOT / "core" / "retrieval_dispatch_runtime.py").read_text()
    assert "prepare_final_answer_packet_author_handoff_from_scope(" in text
    assert "assemble_final_answer_citation_runtime_from_scope(" in text
    assert "process_search_queries(" in text or "process_search_queries(" in retrieval_helper_text
    assert "select_providers" not in retrieval_helper_text
    assert "ask_model" not in retrieval_helper_text
    assert "run_kernel.authorize_final_answer_packet_prepare(" in packet_runtime
    assert "run_kernel.authorize_author_execution(" in author_runtime
    assert "execute_author_action(" in author_runtime
    assert "ask_model(\n        author_prompt, _author_system," not in text
    assert "build_final_answer_packet(" in helper_text
    assert "derive_author_input_payload(" in helper_text
    assert "build_packet_derived_citation_source_handoff_state(" in helper_text
    assert "final_answer_packet_compatibility_refs(" in helper_text
    assert "source_obligation_projection = evidence_ledger_projection" in helper_text
    assert "legacy_source_obligation_projection" not in helper_text
    assert "build_source_class_observability_telemetry" not in helper_text
    assert "final_source_telemetry_inputs.final_evidence_snapshot_payload" in helper_text
    assert '"authority": "final_answer_packet"' not in text


def test_ag_sem_12a_semantic_authority_ref_exact_non_delta_author_surfaces() -> None:
    sufficiency_projection = RunSufficiencyJudgment(
        judgment_id="ag-sem-12a-ag89d",
        decision=RunSufficiencyDecision.READY_DIRECT,
        final_answer_posture=SufficiencyPosture.DIRECT_ANSWER,
        final_answer_allowed=True,
        semantic_consumption={
            "schema_version": "sufficiency_semantic_state_consumption_ag_sem_09_v1",
            "semantic_state_facts_digest": SEMANTIC_DIGEST,
            "blocker_count": 0,
            "blocker_codes": [],
            "direct_answer_blocked": False,
            "finalization_blocked": False,
            "required_component_count": 1,
            "covered_component_count": 1,
        },
    ).to_projection()
    packet_with = build_final_answer_packet(
        run_id="ag-sem-12a-ag89d",
        final_evidence=[_passage(source_id=11)],
        author_evidence=[_passage(source_id=11)],
        sufficiency_judgment_projection=sufficiency_projection,
    )
    packet_without = replace(packet_with, semantic_authority_ref={})
    assert packet_with.semantic_authority_ref
    assert packet_without.semantic_authority_ref == {}

    from tests.test_ag_sem_12a_fap_semantic_authority_projection import _author_surfaces

    assert _author_surfaces(packet_with) == _author_surfaces(packet_without)


def _carried_synthesis_entry() -> dict:
    return {
        "entry_kind": "admitted_synthesis",
        "synthesis_key": "benefit_summary",
        "synthesis_depth": 1,
        "claim_text": (
            "The rebate and income threshold define the verified "
            "two-part Northstar benefit."
        ),
        "claim_id": "carried-claim:benefit_summary",
        "claim_digest": "carried-claim-digest",
        "relationship_type": "benefit_conjunction",
        "status": "admitted",
        "current": True,
        "stale": False,
        "input_node_refs": [],
        "dprime_validation_ref": {},
        "scrutineer_ref": {},
        "runkernel_admission_ref": {},
        "carried_semantic_lineage": {
            "prior_cross_component_analyst_ref": {
                "artifact_id": "prior-cross",
                "artifact_digest": "prior-cross-digest",
            },
            "prior_synthesis_claim_ref": {
                "claim_id": "prior-claim",
                "claim_digest": "prior-claim-digest",
            },
            "prior_synthesis_dprime_ref": {
                "artifact_id": "prior-dprime",
                "artifact_digest": "prior-dprime-digest",
            },
            "prior_synthesis_admission_ref": {
                "admission_id": "prior-admission",
                "admission_digest": "prior-admission-digest",
            },
        },
        "current_node_authority": {
            "runkernel_carry_forward_action_ref": {
                "operation": "selective_invalidation",
                "action_id": "carry-forward-action:test",
            }
        },
        "required_caveats": [],
        "preserved_nonclaims": [],
    }


@pytest.mark.parametrize("readiness", ["ready", "ready_with_caveats"])
def test_final_answer_packet_accepts_valid_carried_synthesis_when_graph_ready(
    readiness: str,
) -> None:
    packet = FinalAnswerPacket(
        packet_id="fap-carried-ready",
        admitted_synthesis_entries=(_carried_synthesis_entry(),),
        multicomponent_graph_readiness=readiness,
        multicomponent_limitations=("optional caveat text",),
    )

    assert len(packet.admitted_synthesis_entries) == 1
    assert packet.multicomponent_graph_readiness == readiness


def test_final_answer_packet_rejects_carried_synthesis_on_non_ready_graph_even_with_limitations() -> None:
    with pytest.raises(
        ValueError,
        match="cannot include synthesis from a non-ready graph",
    ):
        FinalAnswerPacket(
            packet_id="fap-carried-non-ready",
            admitted_synthesis_entries=(_carried_synthesis_entry(),),
            multicomponent_graph_readiness="stale",
            multicomponent_limitations=(
                "Only unaffected admitted synthesis remains available.",
            ),
        )


def _assemble_author_runtime(**overrides):
    from core.final_answer_runtime_assembly import assemble_final_answer_author_runtime

    passage = overrides.pop("passage", _passage())
    evidence = overrides.get("final_top_evidence") or [passage]
    first = evidence[0] if evidence else passage
    params = {
        "run_id": "fallback-retirement",
        "query": "Explain why plants need sunlight",
        "intent": "research",
        "report_type": "general",
        "query_type": "general",
        "core_topic": "plants",
        "primary_entity": "plants",
        "anchor_packet_telemetry": {},
        "final_top_evidence": evidence,
        "author_evidence": list(evidence),
        "ordered_sources": [
            f"- [{first.get('source_id')}] [{first.get('title')}]({first.get('url')})"
        ],
        "unique_source_urls": {first["url"]: first["source_id"]},
        "query_lineage_refs": {},
        "corpus_weak": False,
        "failure_card_payload": {"show": False, "reason": None},
        "conflicts_present": False,
        "synth_was_insufficient": False,
        "author_notes": "",
        "author_prompt": "base prompt",
        "author_system_prompt_key": "author",
        "author_effort": "low",
    }
    params.update(overrides)
    return assemble_final_answer_author_runtime(**params)


def _official_fee_contract_and_ledger():
    from core.evidence_ledger import (
        CandidateDisposition,
        EvidenceLedger,
        build_evidence_ledger_observation_from_run_contract,
    )
    from core.run_authority_contract_templates import build_deterministic_contract

    contract = build_deterministic_contract(
        query="What is the current official filing fee?",
        mode="Balanced",
    ).to_projection()
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        build_evidence_ledger_observation_from_run_contract(
            observation_id="fallback-retirement:ledger:contract",
            contract_projection=contract,
        ).to_dict()
    )
    ledger.reduce_observation(
        {
            "observation_id": "fallback-retirement:ledger:candidates",
            "observation_source": "fallback_retirement_fixture",
            "candidates": [
                {
                    "candidate_id": "C1",
                    "url": "https://example.test/C1",
                    "title": "C1",
                    "source_class": "official_current_rules",
                    "source_tier": "official",
                    "currentness_signal": "current",
                    "readable_status": "readable",
                    "fetchable_status": "fetchable",
                    "disposition": CandidateDisposition.ACCEPTED.value,
                    "eligible_for_stronger_obligation": True,
                }
            ],
            "requirement_links": [
                {
                    "requirement_id": requirement["requirement_id"],
                    "candidate_id": "C1",
                    "link_status": "fixture_link",
                }
                for requirement in contract["source_requirements"]
            ],
        }
    )
    return contract, ledger.to_projection().to_dict()


def _telemetry_for_official_fee(passage):
    from core.source_class_recovery import build_source_class_observability_telemetry

    return build_source_class_observability_telemetry(
        query="What is the current official filing fee?",
        intent="research",
        report_type="general",
        query_type="general",
        core_topic="filing fee",
        primary_entity="agency",
        anchor_packet=None,
        final_top_evidence=[passage],
    )


def test_telemetry_only_custody_cannot_satisfy_required_official_current() -> None:
    from core.run_authority_contract_templates import build_deterministic_contract

    passage = _passage(
        source_id=91,
        title="Official fee schedule",
        url="https://official.example/fee",
        text="The official current filing fee is $45.",
        source_tier="official",
        source_class="official_current_rules",
    )
    telemetry = _telemetry_for_official_fee(passage)
    custody = telemetry.get("official_current_source_custody") or {}
    telemetry_satisfied_classes = {
        item.get("source_class")
        for item in custody.get("requirements") or ()
        if item.get("status") == "requirement_satisfied"
        or item.get("satisfied_candidate_ids")
    }
    assert "official_current_rules" in telemetry_satisfied_classes

    contract = build_deterministic_contract(
        query="What is the current official filing fee?",
        mode="Balanced",
    ).to_projection()
    assembly = _assemble_author_runtime(
        run_id="telemetry-no-authority",
        query="What is the current official filing fee?",
        core_topic="filing fee",
        primary_entity="agency",
        passage=passage,
        run_contract_projection=contract,
    )
    packet = assembly.packet

    assert assembly.source_obligation_projection is None
    assert packet.official_current_custody_summary.get("available") is False
    assert not any(
        record.status is SourceObligationStatus.SATISFIED
        and record.source_class == "official_current_rules"
        for record in packet.source_obligations
    )
    assert any(
        record.source_class == "official_current_rules"
        and record.status is not SourceObligationStatus.SATISFIED
        for record in packet.source_obligations
    )
    assert packet.readiness_status is not FinalAnswerReadinessStatus.AUTHOR_READY


def test_evidence_ledger_canonical_custody_still_satisfies_source_obligation() -> None:
    from core.run_authority_sufficiency import RunSufficiencyJudgmentInput
    from core.run_authority_sufficiency_validation import (
        build_deterministic_sufficiency_judgment,
    )

    contract, ledger = _official_fee_contract_and_ledger()
    judgment = build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection=contract,
            evidence_ledger_projection=ledger,
            search_judgment_projection={"decision": "stop_satisfied"},
            answer_contract_projection={},
            source_obligation_projection=ledger,
            final_evidence_facts={
                "final_evidence_count": 1,
                "author_evidence_count": 1,
            },
            budget={"iteration": 1, "max_iterations": 3},
        )
    )
    assembly = _assemble_author_runtime(
        run_id="ledger-canonical-custody",
        query="What is the current official filing fee?",
        core_topic="filing fee",
        primary_entity="agency",
        passage=_passage(),
        evidence_ledger_projection=ledger,
        run_contract_projection=contract,
        sufficiency_judgment_projection=judgment.to_projection(),
    )
    packet = assembly.packet

    assert assembly.source_obligation_projection is ledger
    assert packet.official_current_custody_summary.get("custody_authority") == (
        "RunKernel.EvidenceLedger"
    )
    assert any(
        record.source_class == "official_current_rules"
        and record.status is SourceObligationStatus.SATISFIED
        for record in packet.source_obligations
    )
    assert packet.citation_eligible
    assert packet.readiness_status is FinalAnswerReadinessStatus.AUTHOR_READY


def test_no_special_obligation_ordinary_path_does_not_gain_official_current_requirement() -> None:
    assembly = _assemble_author_runtime(
        run_id="ordinary-no-special-obligation",
        query="Explain why plants need sunlight",
    )
    packet = assembly.packet

    assert assembly.source_obligation_projection is None
    assert not any(
        record.source_class in {"official_current_rules", "official_current"}
        for record in packet.source_obligations
    )
    assert packet.readiness_status is FinalAnswerReadinessStatus.AUTHOR_READY
    assert packet.citation_eligible


def test_source_class_observability_telemetry_remains_diagnostic_only() -> None:
    passage = _passage(
        source_id=92,
        title="Official fee schedule",
        url="https://official.example/fee-diagnostic",
        text="The official current filing fee is $45.",
        source_tier="official",
        source_class="official_current_rules",
    )
    telemetry = _telemetry_for_official_fee(passage)
    assert "official_current_source_custody" in telemetry
    custody = telemetry["official_current_source_custody"]
    assert custody.get("schema_version") == "official_current_source_custody_ag89b_v1"

    assembly = _assemble_author_runtime(
        run_id="telemetry-diagnostic-only",
        query="What is the current official filing fee?",
        core_topic="filing fee",
        primary_entity="agency",
        passage=passage,
    )
    packet = assembly.packet
    telemetry_requirement_ids = {
        item.get("requirement_id")
        for item in custody.get("requirements") or ()
        if item.get("requirement_id")
    }

    assert assembly.source_obligation_projection is None
    assert not any(
        record.custody_requirement_id in telemetry_requirement_ids
        for record in packet.source_obligations
    )
    assert not any(
        str(record.obligation_id).startswith("final-answer:official_current_source:")
        for record in packet.source_obligations
    )
