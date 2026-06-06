import json
from pathlib import Path

import pytest

from core.final_answer_packet import (
    CitationEligibilityRecord,
    CitationEligibilityStatus,
    CitationRequirementStatus,
    ClaimPosture,
    EvidenceAuthorityStatus,
    FinalEvidenceRecord,
    SourceObligationStatus,
)
from core.final_answer_runtime_adapter import (
    build_final_answer_packet,
    build_packet_derived_citation_source_handoff_state,
    derive_author_input_payload,
    final_answer_packet_trace_fragment,
)
from core.official_current_source_custody import OfficialCurrentSourceCustodyState

ROOT = Path(__file__).resolve().parents[1]


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
    assert "build_final_answer_packet(" in text
    assert "derive_author_input_payload(" in text
    assert "build_packet_derived_citation_source_handoff_state(" in text
    assert "author_prompt = final_author_payload.prompt" in text
    assert "source_obligation_projection=pre_author_source_obligation_projection" in text
    assert "process_search_queries(" in text
    assert "ask_model(\n        author_prompt, _author_system," in text
    assert "citation_source_handoff_state = build_packet_derived_citation_source_handoff_state" in text
