from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.ordinary_semantic_producer_runtime import (
    OrdinarySemanticProducerHandoffStatus,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    OfflineOrdinaryPipelineHarness,
    run_offline_ordinary_pipeline,
    scrub_offline_runtime,
)

DIRECT_SPEC_QUERY = (
    "What does the Acme Widget API spec say about supported payload size?"
)
DIRECT_SPEC_RESEARCH_QUERY = "Acme Widget API spec supported payload size"
RAW_DIRECT_AUTHOR_RESPONSE = (
    "AG_SEM_PROD_02_AUTHOR_FINAL_REPORT: The Acme Widget API spec states that "
    "supported payload size is 64 KiB, and the answer stays bound to the packet "
    "source identity [[11]](https://docs.acme.test/widget-api/spec)."
)
RAW_INSUFFICIENT_AUTHOR_RESPONSE = (
    "AG_SEM_PROD_02_INSUFFICIENT_AUTHOR_FINAL_REPORT: Available evidence is "
    "insufficient for semantic coverage, so this legacy-path answer is caveated "
    "and does not claim semantic coverage."
)
MATERIALIZATION_TRACE_REF_KEY = "semantic_author_materialization_trace_ref"


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _DirectSpecHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path, *, insufficient: bool = False) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=DIRECT_SPEC_QUERY,
            core_topic="Acme Widget API specification payload size",
            primary_entity="Acme Widget API",
            researcher_queries=(DIRECT_SPEC_RESEARCH_QUERY,),
            raw_author_response=(
                RAW_INSUFFICIENT_AUTHOR_RESPONSE
                if insufficient
                else RAW_DIRECT_AUTHOR_RESPONSE
            ),
            analyst_response=(
                "Analysis is limited to the retrieved Acme Widget API specification."
            ),
            logger_name="test_ag_sem_prod_02_broader_ordinary_semantic_production",
        )
        self.insufficient = insufficient

    def build_search_passages(self) -> list[dict[str, Any]]:
        if self.insufficient:
            return [
                {
                    "source_id": 21,
                    "title": "Acme Widget forum payload discussion",
                    "url": "https://forum.acme.test/widget-api/payload",
                    "text": (
                        "A community discussion guesses that Acme Widget API "
                        "payloads may be large, but no specification text is readable."
                    ),
                    "score": 0.92,
                    "credibility": 2,
                    "source_tier": "secondary",
                    "source_class": "secondary_analysis",
                    "currentness_signal": "stale",
                    "readable_status": "unreadable",
                    "disposition": "observed",
                    "eligible_for_stronger_obligation": False,
                    "lower_tier": True,
                    "query_ref": DIRECT_SPEC_RESEARCH_QUERY,
                    "_provider": "offline_fake_search",
                }
            ]
        return [
            {
                "source_id": 11,
                "title": "Acme Widget API specification",
                "url": "https://docs.acme.test/widget-api/spec",
                "text": (
                    "Acme Widget API specification says supported payload size "
                    "is 64 KiB for direct requests."
                ),
                "score": 0.99,
                "credibility": 4,
                "source_tier": "canonical",
                "source_class": "primary_source_documents",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
                "query_ref": DIRECT_SPEC_RESEARCH_QUERY,
                "_provider": "offline_fake_search",
            },
            {
                "source_id": 12,
                "title": "Acme Widget API release support note",
                "url": "https://docs.acme.test/widget-api/release-support",
                "text": (
                    "Acme Widget API release support note confirms that the "
                    "payload-size behavior remains supported."
                ),
                "score": 0.95,
                "credibility": 4,
                "source_tier": "canonical",
                "source_class": "primary_source_documents",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
                "query_ref": DIRECT_SPEC_RESEARCH_QUERY,
                "_provider": "offline_fake_search",
            },
        ]


def _run_direct_spec_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    insufficient: bool = False,
) -> tuple[dict[str, Any], _DirectSpecHarness, Any]:
    harness = _DirectSpecHarness(tmp_path, insufficient=insufficient)
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-24",
        session_id=(
            "ag-sem-prod-02-insufficient-session"
            if insufficient
            else "ag-sem-prod-02-direct-session"
        ),
        run_id=(
            "ag-sem-prod-02-insufficient-run"
            if insufficient
            else "ag-sem-prod-02-direct-run"
        ),
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    return captured, harness, outcome


def _assert_offline_author_kwargs_unchanged(harness: _DirectSpecHarness) -> None:
    assert len(harness.author_kwargs) == 1
    assert harness.author_kwargs[0]["provider"] == "offline-fake-provider"
    assert harness.author_kwargs[0]["model"] == "offline-fake-fast-model"
    assert harness.author_kwargs[0]["base_url"] == "http://offline.invalid/v1"
    assert harness.author_kwargs[0]["api_key"] == ""
    assert harness.author_kwargs[0]["stream"] is True
    assert harness.author_kwargs[0]["use_reasoning"] is False
    assert harness.author_kwargs[0]["cost_phase"] == "model"


def _assert_no_private_material_leaks(
    *,
    packet_projection: dict[str, Any],
    author_payload_trace_ref: dict[str, Any],
    author_observation: dict[str, Any],
    kernel_trace_fragment: dict[str, Any],
    author_prompt: str,
    raw_author_response: str,
) -> None:
    serialized_surfaces = json.dumps(
        {
            "packet_projection": packet_projection,
            "author_payload_trace_ref": author_payload_trace_ref,
            "author_observation": author_observation,
            "kernel_trace_fragment": kernel_trace_fragment,
        },
        sort_keys=True,
    )
    for forbidden in (
        author_prompt,
        raw_author_response,
        "FINAL ANSWER PACKET AUTHORITY",
        "CONTROLLED SEMANTIC CONTEXT",
        "system prompt",
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
        "full semantic rows",
        '"secrets_returned": true',
        '"provider_payload_retained": true',
        '"raw_prompt_retained": true',
        '"raw_prompt_included": true',
        '"model_response_text_retained": true',
        '"db_cache_rows_retained": true',
    ):
        assert forbidden not in serialized_surfaces


def test_direct_canonical_spec_fact_reaches_semantic_fap_and_author_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, harness, outcome = _run_direct_spec_pipeline(tmp_path, monkeypatch)

    assert captured["semantic_handoff_called"] is True
    assert captured["semantic_handoff_result"].status is (
        OrdinarySemanticProducerHandoffStatus.COMMITTED
    )
    assert captured["sufficiency_handoff_called"] is True
    assert captured["packet_handoff_called"] is True
    assert captured["author_handoff_called"] is True
    assert harness.search_calls
    assert harness.forbidden_live_calls == []
    _assert_offline_author_kwargs_unchanged(harness)

    kernel = captured["run_kernel"]
    state = kernel.state
    assert state.initial_answer_contract
    assert state.semantic_observation_admission_history
    assert state.component_coverage_history

    component_ref = state.initial_answer_contract["accepted_answer_component_refs"][0]
    assert component_ref["source_obligation_candidate_ids"] == [
        "obligation:canonical_documentation"
    ]

    admission = state.semantic_observation_admission_history[-1]
    assert admission["support_status"] == "supports"
    assert admission["directness"] == "direct"

    coverage = state.component_coverage_history[-1]
    assert coverage["coverage_state"] == "satisfied"
    assert coverage["source_obligation_status"] == "satisfied"
    assert coverage["evidence_custody_status"] == "custodied"
    assert coverage["evidence_ledger_binding"]["source_requirement_ids"]
    assert coverage["currentness_posture"] == "not_time_sensitive"

    ledger_projection = state.evidence_ledger.to_projection().to_dict()
    bound_requirements = {
        requirement["requirement_id"]: requirement
        for requirement in ledger_projection["source_requirements"]
    }
    assert any(
        requirement["required_source_class"] == "primary_source_documents"
        and requirement["status"] == "satisfied"
        for requirement in bound_requirements.values()
    )
    assert any(
        candidate["source_class"] == "primary_source_documents"
        and candidate["fact_disposition"] == "accepted"
        for candidate in ledger_projection["candidate_records"]
    )

    sufficiency_projection = captured["sufficiency_projection"]
    assert sufficiency_projection["decision"] == "ready_direct"
    semantic_consumption = sufficiency_projection["semantic_consumption"]
    semantic_ref_projection = semantic_consumption["semantic_ref_projection"]
    assert semantic_ref_projection["available"] is True
    assert semantic_ref_projection["content_refs_available"] is True
    assert semantic_ref_projection["coverage_refs_available"] is True

    packet_handoff = captured["packet_handoff"]
    packet = packet_handoff.packet
    fap_ref_projection = packet.semantic_content_coverage_ref_projection
    assert fap_ref_projection["available"] is True
    assert fap_ref_projection["semantic_source_ref_bindings"]
    bindings = tuple(dict(row) for row in packet.semantic_packet_evidence_bindings)
    assert bindings
    assert packet.semantic_evidence_authority_manifest[
        "semantic_packet_evidence_binding_available"
    ] is True

    author_payload_trace_ref = packet_handoff.author_payload.to_trace_ref()
    materialization_trace_ref = author_payload_trace_ref[MATERIALIZATION_TRACE_REF_KEY]
    assert materialization_trace_ref["available"] is True
    assert materialization_trace_ref["prompt_visible"] is True
    assert materialization_trace_ref["model_request_visible"] is True
    assert materialization_trace_ref["bounded_text_included"] is False
    assert materialization_trace_ref["unavailable_reason"] == (
        "bounded_excerpt_not_packet_owned"
    )

    assert "CONTROLLED SEMANTIC CONTEXT" in harness.author_prompts[0]
    assert "Bounded semantic excerpt from" not in harness.author_prompts[0]
    assert outcome.report == RAW_DIRECT_AUTHOR_RESPONSE
    _assert_no_private_material_leaks(
        packet_projection=state.final_answer_packet,
        author_payload_trace_ref=author_payload_trace_ref,
        author_observation=state.author_observation,
        kernel_trace_fragment=kernel.to_trace_fragment(),
        author_prompt=harness.author_prompts[0],
        raw_author_response=RAW_DIRECT_AUTHOR_RESPONSE,
    )


def test_insufficient_single_component_evidence_does_not_overclaim_semantic_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, harness, outcome = _run_direct_spec_pipeline(
        tmp_path,
        monkeypatch,
        insufficient=True,
    )

    assert captured["semantic_handoff_called"] is True
    assert captured["semantic_handoff_result"].status is (
        OrdinarySemanticProducerHandoffStatus.SKIPPED
    )
    assert not captured["run_kernel"].state.initial_answer_contract
    assert not captured["run_kernel"].state.semantic_observation_admission_history
    assert not captured["run_kernel"].state.component_coverage_history
    _assert_offline_author_kwargs_unchanged(harness)

    sufficiency_projection = captured["sufficiency_projection"]
    semantic_consumption = sufficiency_projection.get("semantic_consumption") or {}
    semantic_ref_projection = semantic_consumption.get("semantic_ref_projection") or {}
    assert semantic_ref_projection.get("available") is not True

    packet_handoff = captured["packet_handoff"]
    packet = packet_handoff.packet
    assert packet.semantic_content_coverage_ref_projection.get("available") is not True
    assert tuple(packet.semantic_packet_evidence_bindings) == ()
    assert "semantic_packet_evidence_binding_ref" not in packet.to_dict()

    author_payload_trace_ref = packet_handoff.author_payload.to_trace_ref()
    assert MATERIALIZATION_TRACE_REF_KEY not in author_payload_trace_ref
    assert "CONTROLLED SEMANTIC CONTEXT" not in harness.author_prompts[0]
    assert "semantic coverage" in outcome.report
    assert outcome.report == RAW_INSUFFICIENT_AUTHOR_RESPONSE
