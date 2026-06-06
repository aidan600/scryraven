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
    final_answer_packet_compatibility_refs,
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
    retrieval_helper_text = (ROOT / "core" / "retrieval_dispatch_runtime.py").read_text()
    assert "assemble_final_answer_author_runtime_from_scope(" in text
    assert "assemble_final_answer_citation_runtime_from_scope(" in text
    assert "process_search_queries(" in text or "process_search_queries(" in retrieval_helper_text
    assert "select_providers" not in retrieval_helper_text
    assert "ask_model" not in retrieval_helper_text
    assert "ask_model(\n        author_prompt, _author_system," in text
    assert "build_final_answer_packet(" in helper_text
    assert "derive_author_input_payload(" in helper_text
    assert "build_packet_derived_citation_source_handoff_state(" in helper_text
    assert "final_answer_packet_compatibility_refs(" in helper_text
    assert "source_obligation_projection = build_source_class_observability_telemetry" in helper_text
    assert "final_source_telemetry_inputs.final_evidence_snapshot_payload" in helper_text
    assert '"authority": "final_answer_packet"' not in text
