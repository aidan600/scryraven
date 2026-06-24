from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.final_answer_packet import SourceObligationStatus
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    OfflineOrdinaryPipelineHarness,
    run_offline_ordinary_pipeline,
    scrub_offline_runtime,
)

CHAIN_CLASSIFICATIONS = {
    "RunAuthorityContract": "canonical_and_consumed",
    "EvidenceLedger": "canonical_and_consumed",
    "SearchJudgment": "canonical_and_consumed",
    "SufficiencyJudgment": "canonical_and_consumed",
    "FinalAnswerPacket": "canonical_and_consumed",
    "ordinary Author execution": "canonical_and_consumed",
    "final RunOutcome/report/post-author state": "canonical_and_consumed",
}
AF_COMPONENT_LANE_RELATIONSHIP = "partially_shared_and_bridgeable"
POST_AUTHOR_CITATION_SURVIVAL_CLASSIFICATION = "trace_or_projection_only"

RAW_AUTHOR_RESPONSE = (
    "AG_CHECK_01_AUTHOR_FINAL_REPORT: Example Program remains governed by the "
    "retrieved official rule. The official evidence says the rule is current, "
    "and this answer cites only packet-provided source identity "
    "[[1]](https://official.example/rule). The answer stays narrow, avoids new "
    "evidence, and leaves any unresolved source obligations caveated."
)
MANIFEST_TRACE_REF_KEY = "semantic_evidence_authority_manifest_trace_ref"
ENVELOPE_TRACE_REF_KEY = "semantic_content_coverage_ref_envelope_trace_ref"
ENVELOPE_KEY = "semantic_content_coverage_ref_envelope"


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _OfflineOrdinaryHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query="What is the current official rule for Example Program?",
            core_topic="Example Program current official rule",
            primary_entity="Example Program",
            raw_author_response=RAW_AUTHOR_RESPONSE,
            analyst_response=(
                "Analysis is limited to the retrieved official Example Program rule."
            ),
            logger_name="test_ag_check_01_offline_ordinary_authority_path",
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": 1,
                "title": "Example Program official rule",
                "url": "https://official.example/rule",
                "text": (
                    "Example Program official current rule says the program "
                    "uses the current eligibility rule and remains in effect."
                ),
                "score": 0.99,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "_provider": "offline_fake_search",
            },
            {
                "source_id": 2,
                "title": "Example Program implementation memo",
                "url": "https://official.example/memo",
                "text": (
                    "Official implementation memo confirms the current rule "
                    "and gives supporting context for Example Program."
                ),
                "score": 0.97,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "_provider": "offline_fake_search",
            },
        ]


def _execution_event_from_log(path: Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return next(row for row in rows if row.get("event") == "execution")


def _classification_report(captured: dict[str, Any], outcome: Any) -> dict[str, Any]:
    kernel = captured["run_kernel"]
    state = kernel.state
    return {
        "chain_classifications": dict(CHAIN_CLASSIFICATIONS),
        "af_component_lane_relationship": AF_COMPONENT_LANE_RELATIONSHIP,
        "post_author_citation_survival_classification": (POST_AUTHOR_CITATION_SURVIVAL_CLASSIFICATION),
        "runtime_consumer_observed": {
            "FinalAnswerPacket": "AuthorExecutor",
            "ordinary Author execution": "RunKernel.AuthorObservation",
            "final RunOutcome/report/post-author state": "build_run_outcome_from_scope",
        },
        "authority_owners_observed": {
            "RunAuthorityContract": state.run_contract_projection.get("owner"),
            "EvidenceLedger": state.evidence_ledger.to_projection().to_dict().get("owner"),
            "SearchJudgment": state.search_judgment_projection.get("owner"),
            "SufficiencyJudgment": state.sufficiency_judgment_projection.get("owner"),
            "FinalAnswerPacket": state.final_answer_authority_projection.get("owner"),
            "ordinary Author execution": state.final_answer_outcome.get("owner"),
        },
        "ordinary_author_implementation": "core.author_execution_runtime.execute_author_action",
        "report_hash_observed": state.final_answer_outcome.get("report_hash"),
        "run_outcome_report_observed": bool(outcome.report),
    }


def test_ag_check_01_offline_run_pipeline_consumes_packet_constrained_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _OfflineOrdinaryHarness(tmp_path)
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-22",
        session_id="ag-check-01-session",
        run_id="ag-check-01-run",
        capture_stages=(HANDOFF_PACKET, HANDOFF_AUTHOR),
    )
    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")

    assert captured["packet_handoff_called"] is True
    assert captured["author_handoff_called"] is True
    assert harness.search_calls
    assert harness.forbidden_live_calls == []
    assert len(harness.author_prompts) == 1
    assert len(harness.author_kwargs) == 1
    assert harness.author_kwargs[0]["provider"] == "offline-fake-provider"
    assert harness.author_kwargs[0]["model"] == "offline-fake-fast-model"
    assert harness.author_kwargs[0]["base_url"] == "http://offline.invalid/v1"
    assert harness.author_kwargs[0]["api_key"] == ""
    assert harness.author_kwargs[0]["stream"] is True
    assert harness.author_kwargs[0]["use_reasoning"] is False
    assert harness.author_kwargs[0]["cost_phase"] == "model"

    kernel = captured["run_kernel"]
    state = kernel.state
    packet_handoff = captured["packet_handoff"]
    author_handoff = captured["author_handoff"]
    author_scope = captured["author_runtime_scope"]
    packet_scope = captured["packet_runtime_scope"]

    assert outcome.run_id == "ag-check-01-run"
    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert log_entry["execution_trace"]["final_output_preview"].startswith("AG_CHECK_01_AUTHOR_FINAL_REPORT")
    assert author_handoff.report == RAW_AUTHOR_RESPONSE
    assert state.final_answer_outcome["report_hash"]
    assert state.final_answer_outcome["final_text_included"] is False
    assert state.final_answer_outcome["packet_id"] == packet_handoff.packet.packet_id

    assert state.run_contract_projection["owner"] == "RunKernel.RunAuthorityContract"
    assert state.run_contract_projection["canonical_state"] is True
    assert state.run_contract_projection["trace_only"] is False
    assert state.run_contract_projection["storage_only"] is False
    assert state.run_contract_projection["contract_id"]

    ledger_projection = state.evidence_ledger.to_projection().to_dict()
    assert ledger_projection["owner"] == "RunKernel.EvidenceLedger"
    assert ledger_projection["candidate_count"] > 0
    assert packet_scope["evidence_ledger_projection"]["owner"] == "RunKernel.EvidenceLedger"

    assert state.search_judgment_projection["owner"] == "RunKernel.RunAuthoritySearchJudgment"
    assert state.search_judgment_projection["canonical_state"] is True
    assert state.search_judgment_projection["trace_only"] is False
    assert state.sufficiency_judgment_projection["owner"] == ("RunKernel.RunAuthoritySufficiencyJudgment")
    assert state.sufficiency_judgment_projection["canonical_state"] is True
    assert state.sufficiency_judgment_projection["trace_only"] is False
    assert state.sufficiency_judgment_projection["decision"]
    assert state.sufficiency_judgment_projection["decision"] == (state.final_answer_packet["sufficiency_decision"])

    semantic_ref = packet_handoff.packet.semantic_authority_ref
    assert semantic_ref.get("available") is True
    assert semantic_ref.get("semantic_state_facts_digest")
    assert semantic_ref.get("sufficiency_semantic_consumed") is True
    assert "consumed" not in semantic_ref
    assert state.final_answer_packet.get("semantic_authority_ref") == semantic_ref
    fap_ref_projection = packet_handoff.packet.semantic_content_coverage_ref_projection
    assert fap_ref_projection.get("available") is True
    assert fap_ref_projection.get("content_refs_available") is True
    assert fap_ref_projection.get("coverage_refs_available") is True
    assert fap_ref_projection.get("semantic_state_facts_digest") == (
        semantic_ref.get("semantic_state_facts_digest")
    )
    assert fap_ref_projection.get("sanitized_content_ref_ids")
    assert fap_ref_projection.get("content_ref_digests")
    assert fap_ref_projection.get("coverage_record_refs")
    assert fap_ref_projection.get("semantic_source_ref_bindings")
    assert state.final_answer_packet.get(
        "semantic_content_coverage_ref_projection"
    ) == fap_ref_projection
    manifest = packet_handoff.packet.semantic_evidence_authority_manifest
    assert manifest.get("available") is True
    assert manifest.get("semantic_state_facts_digest") == (
        semantic_ref.get("semantic_state_facts_digest")
    )
    assert manifest.get("evidence_ids") == [
        record.evidence_id for record in packet_handoff.packet.evidence_allowed
    ]
    assert manifest.get("citation_source_ids") == [
        record.source_id
        for record in packet_handoff.packet.citation_eligible
        if record.source_id is not None
    ]
    expected_status_summary = {item.value: 0 for item in SourceObligationStatus}
    for record in packet_handoff.packet.source_obligations:
        expected_status_summary[record.status.value] += 1
    assert manifest.get("source_obligation_status_summary") == expected_status_summary
    for key in (
        "required_component_count",
        "covered_component_count",
        "missing_component_count",
    ):
        if key in semantic_ref:
            assert manifest.get(key) == semantic_ref.get(key)
    assert manifest.get("content_refs_available") is True
    assert manifest.get("coverage_refs_available") is True
    assert "deferred_ref_fields" not in manifest
    assert manifest.get("sanitized_content_ref_ids")
    assert manifest.get("content_ref_digests")
    assert manifest.get("coverage_record_refs")
    assert manifest.get("semantic_observation_refs")
    assert manifest.get("component_refs")
    assert manifest.get("semantic_ref_evidence_ids")
    assert manifest.get("semantic_source_ref_bindings")
    assert manifest.get("source_obligation_refs")
    assert all(
        record.origin_evidence_ref_id and record.origin_evidence_ref_kind
        for record in packet_handoff.packet.evidence_allowed
    )
    bindings = tuple(
        dict(row) for row in packet_handoff.packet.semantic_packet_evidence_bindings
    )
    assert bindings
    allowed_packet_evidence_ids = {
        record.evidence_id for record in packet_handoff.packet.evidence_allowed
    }
    binding_origin_ids = {row["origin_evidence_ref_id"] for row in bindings}
    assert set(manifest.get("semantic_ref_evidence_ids")).issubset(
        binding_origin_ids
    )
    assert all(
        row["packet_evidence_id"] in allowed_packet_evidence_ids for row in bindings
    )
    assert manifest.get("semantic_packet_evidence_binding_available") is True
    assert manifest.get("semantic_packet_evidence_binding_count") == len(bindings)
    assert manifest.get("semantic_packet_evidence_binding_digest")
    assert manifest.get("raw_content_included") is False
    assert manifest.get("bounded_text_included") is False
    assert manifest.get("prompt_visible") is False
    assert manifest.get("author_payload_visible") is False
    assert manifest.get("author_payload_ref_envelope_available") is True
    assert manifest.get("model_request_visible") is False
    assert manifest.get("final_text_included") is False
    assert "coverage_record_ids" not in manifest
    assert "coverage_record_digests" not in manifest
    assert state.final_answer_packet.get("semantic_evidence_authority_manifest") == (
        manifest
    )
    semantic_trace_ref = packet_handoff.author_payload.to_trace_ref()[
        "semantic_authority_trace_ref"
    ]
    assert semantic_trace_ref.get("available") is True
    assert semantic_trace_ref.get("semantic_state_facts_digest") == (
        semantic_ref.get("semantic_state_facts_digest")
    )
    assert "semantic_authority_ref" not in packet_handoff.author_payload.to_trace_ref()
    assert "semantic_authority_ref" not in state.author_observation
    manifest_trace_ref = packet_handoff.author_payload.to_trace_ref()[
        MANIFEST_TRACE_REF_KEY
    ]
    assert manifest_trace_ref.get("available") is True
    assert manifest_trace_ref.get("content_refs_available") is True
    assert manifest_trace_ref.get("coverage_refs_available") is True
    assert manifest_trace_ref.get("semantic_state_facts_digest") == (
        manifest.get("semantic_state_facts_digest")
    )
    assert manifest_trace_ref.get("semantic_evidence_authority_manifest_digest")
    assert "evidence_ids" not in manifest_trace_ref
    assert "citation_source_ids" not in manifest_trace_ref
    assert "source_obligation_status_summary" not in manifest_trace_ref
    assert "sanitized_content_ref_ids" not in manifest_trace_ref
    assert "content_ref_digests" not in manifest_trace_ref
    assert "coverage_record_refs" not in manifest_trace_ref
    assert "semantic_observation_refs" not in manifest_trace_ref
    assert "component_refs" not in manifest_trace_ref
    assert "semantic_ref_evidence_ids" not in manifest_trace_ref
    assert "source_obligation_refs" not in manifest_trace_ref
    assert "semantic_packet_evidence_bindings" not in manifest_trace_ref
    assert manifest_trace_ref.get("semantic_packet_evidence_binding_available") is True
    assert manifest_trace_ref.get("semantic_packet_evidence_binding_count") == len(
        bindings
    )
    assert manifest_trace_ref.get("semantic_packet_evidence_binding_digest") == (
        manifest.get("semantic_packet_evidence_binding_digest")
    )
    envelope = packet_handoff.author_payload.semantic_content_coverage_ref_envelope
    assert envelope.get("available") is True
    assert envelope.get("semantic_state_facts_digest") == (
        fap_ref_projection.get("semantic_state_facts_digest")
    )
    assert envelope.get("sanitized_content_ref_ids")
    assert envelope.get("content_ref_digests")
    assert envelope.get("coverage_record_refs")
    assert envelope.get("semantic_packet_evidence_binding_available") is True
    assert envelope.get("semantic_packet_evidence_binding_count") == len(bindings)
    assert envelope.get("semantic_packet_evidence_binding_digest") == (
        manifest.get("semantic_packet_evidence_binding_digest")
    )
    assert "semantic_packet_evidence_bindings" not in envelope
    assert envelope.get("author_payload_visible") is True
    assert envelope.get("authority_payload_visible") is False
    assert envelope.get("authority_block_visible") is False
    assert envelope.get("prompt_visible") is False
    assert envelope.get("model_request_visible") is False
    envelope_trace_ref = packet_handoff.author_payload.to_trace_ref()[
        ENVELOPE_TRACE_REF_KEY
    ]
    assert envelope_trace_ref.get("available") is True
    assert envelope_trace_ref.get("envelope_digest")
    assert envelope_trace_ref.get("component_ref_count") > 0
    assert envelope_trace_ref.get("coverage_record_ref_count") > 0
    assert envelope_trace_ref.get("semantic_observation_ref_count") > 0
    assert envelope_trace_ref.get("sanitized_content_ref_count") > 0
    assert envelope_trace_ref.get("content_ref_digest_count") > 0
    assert envelope_trace_ref.get("semantic_ref_evidence_id_count") > 0
    assert envelope_trace_ref.get("source_obligation_ref_count") > 0
    assert envelope_trace_ref.get("semantic_packet_evidence_binding_available") is True
    assert envelope_trace_ref.get("semantic_packet_evidence_binding_count") == len(
        bindings
    )
    assert envelope_trace_ref.get("semantic_packet_evidence_binding_digest") == (
        manifest.get("semantic_packet_evidence_binding_digest")
    )
    for forbidden_ref_key in (
        "component_refs",
        "coverage_record_refs",
        "semantic_observation_refs",
        "sanitized_content_ref_ids",
        "content_ref_digests",
        "semantic_ref_evidence_ids",
        "source_obligation_refs",
        "semantic_packet_evidence_bindings",
    ):
        assert forbidden_ref_key not in envelope_trace_ref

    assert packet_handoff.packet.packet_id == state.final_answer_packet["packet_id"]
    assert packet_handoff.author_payload.packet_id == state.final_answer_packet["packet_id"]
    assert state.final_answer_authority_projection["owner"] == "RunKernel.FinalAnswerPacket"
    assert state.final_answer_authority_projection["canonical_state"] is True
    assert state.final_answer_authority_projection["trace_only"] is False
    assert state.final_answer_authority_projection["author_payload_ref"]["packet_id"] == (
        packet_handoff.packet.packet_id
    )
    assert state.final_answer_authority_projection["author_payload_ref"][
        "semantic_authority_trace_ref"
    ] == semantic_trace_ref
    assert state.final_answer_authority_projection["author_payload_ref"][
        MANIFEST_TRACE_REF_KEY
    ] == manifest_trace_ref
    assert state.final_answer_authority_projection["author_payload_ref"][
        ENVELOPE_TRACE_REF_KEY
    ] == envelope_trace_ref
    assert ENVELOPE_KEY not in state.final_answer_authority_projection[
        "author_payload_ref"
    ]
    assert state.final_answer_authority_projection["author_payload_ref"]["prompt_text_included"] is False
    assert "semantic_authority_trace_ref" not in state.author_observation
    assert MANIFEST_TRACE_REF_KEY not in state.author_observation
    assert ENVELOPE_TRACE_REF_KEY not in state.author_observation
    assert "semantic_packet_evidence_bindings" not in state.author_observation

    assert "FINAL ANSWER PACKET AUTHORITY" in harness.author_prompts[0]
    assert MANIFEST_TRACE_REF_KEY not in harness.author_prompts[0]
    assert ENVELOPE_TRACE_REF_KEY not in harness.author_prompts[0]
    assert ENVELOPE_KEY not in harness.author_prompts[0]
    assert "semantic_packet_evidence_bindings" not in harness.author_prompts[0]
    assert "semantic_packet_evidence_binding_digest" not in harness.author_prompts[0]
    assert author_scope["final_answer_packet_action"] is packet_handoff.action
    assert author_scope["final_answer_author_payload"] is packet_handoff.author_payload
    assert state.author_observation["owner"] == "RunKernel.AuthorExecutor"
    assert state.author_observation["packet_id"] == packet_handoff.packet.packet_id
    assert state.author_observation["authority_payload_ref"] == (packet_handoff.author_payload.authority_payload)
    assert state.author_observation["sufficiency_decision"] == (packet_handoff.author_payload.sufficiency_decision)
    assert state.author_observation["citation_source_ids"] == list(packet_handoff.author_payload.citation_source_ids)
    assert state.author_observation["prompt_text_included"] is False
    assert state.author_observation["final_text_included"] is False
    assert ENVELOPE_KEY not in state.author_observation
    assert "sanitized_content_ref_ids" not in state.author_observation
    assert "content_ref_digests" not in state.author_observation
    assert "coverage_record_refs" not in state.author_observation

    trace_packet = outcome.execution_trace["final_answer_packet"]
    assert trace_packet["packet_id"] == packet_handoff.packet.packet_id
    assert trace_packet["canonical_state"] is True
    assert trace_packet["trace_mode"] == "run_kernel_final_answer_packet_projection"
    assert outcome.execution_trace["final_answer_source_ids_used"] == ["1"]
    assert "final_authority_citation_survival" in outcome.execution_trace

    for attr in (
        "followup_author_evidence_content_bridge_state",
        "followup_author_invocation_construction_state",
        "followup_author_model_request_assembly_state",
        "followup_author_execution_from_af4d_state",
        "followup_author_response_finalization_state",
    ):
        assert getattr(state, attr) == {}

    canonical_trace = json.dumps(kernel.to_trace_fragment(), sort_keys=True)
    execution_trace = json.dumps(outcome.execution_trace, sort_keys=True)
    for forbidden in (
        harness.author_prompts[0],
        "FINAL ANSWER PACKET AUTHORITY",
        "provider_payload_text",
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
    ):
        assert forbidden not in canonical_trace
    assert state.initial_answer_contract
    assert state.semantic_observation_admission_history
    assert state.component_coverage_history
    component_ref = state.initial_answer_contract["accepted_answer_component_refs"][0]
    assert component_ref.get("source_obligation_candidate_ids")
    coverage = state.component_coverage_history[-1]
    assert coverage.get("source_obligation_status") == "satisfied"
    assert coverage.get("evidence_ledger_binding", {}).get("source_requirement_ids")
    assert "bounded_excerpt" in canonical_trace
    assert RAW_AUTHOR_RESPONSE not in canonical_trace
    assert harness.author_prompts[0] not in execution_trace
    for retained_flag in (
        '"prompt_text_retained": true',
        '"model_response_text_retained": true',
        '"provider_payload_retained": true',
        '"raw_provider_payloads_retained": true',
    ):
        assert retained_flag not in canonical_trace
        assert retained_flag not in execution_trace

    diagnostic = _classification_report(captured, outcome)
    assert diagnostic["chain_classifications"] == CHAIN_CLASSIFICATIONS
    assert diagnostic["af_component_lane_relationship"] == AF_COMPONENT_LANE_RELATIONSHIP
    assert diagnostic["post_author_citation_survival_classification"] == (POST_AUTHOR_CITATION_SURVIVAL_CLASSIFICATION)
    assert diagnostic["authority_owners_observed"] == {
        "RunAuthorityContract": "RunKernel.RunAuthorityContract",
        "EvidenceLedger": "RunKernel.EvidenceLedger",
        "SearchJudgment": "RunKernel.RunAuthoritySearchJudgment",
        "SufficiencyJudgment": "RunKernel.RunAuthoritySufficiencyJudgment",
        "FinalAnswerPacket": "RunKernel.FinalAnswerPacket",
        "ordinary Author execution": "RunKernel.AuthorObservation",
    }
