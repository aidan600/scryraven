from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from core.author_execution_runtime import execute_author_action
from core.final_answer_packet import (
    FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_MATERIALIZATION_TRACE_SCHEMA_VERSION,
    FINAL_ANSWER_SEMANTIC_AUTHOR_MATERIALIZATION_SCHEMA_VERSION,
    FinalAnswerPacket,
    _safe_json,
)
from core.final_answer_packet_runtime import execute_final_answer_packet_prepare_action
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    SufficiencyPosture,
)
from core.run_kernel import RunKernel
from core.semantic_observation_foundation import SanitizedContentReference
from core.sufficiency_semantic_state_consumption_runtime import (
    SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
)

ROOT = Path(__file__).resolve().parents[1]
AUTHOR_RUNTIME = ROOT / "core" / "author_execution_runtime.py"
PACKET = ROOT / "core" / "final_answer_packet.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
PROMPT_ASSEMBLY = ROOT / "core" / "runtime_prompt_assembly.py"

SEMANTIC_DIGEST = "a" * 64
ACCEPTED_CONTRACT_DIGEST = "b" * 64
COMPONENT_ID = "component:current-rule"
COMPONENT_DIGEST = "c" * 64
COVERAGE_RECORD_ID = "coverage:current-rule"
COVERAGE_RECORD_DIGEST = "d" * 64
OBSERVATION_ID = "observation:current-rule"
OBSERVATION_DIGEST = "e" * 64
CONTENT_REF_ID = "content:candidate:official-rule"
ORIGIN_ID = "candidate:official-rule"
SOURCE_ID = 101


def _stable_safe_digest(value: Any) -> str:
    return sha256(
        json.dumps(
            _safe_json(value),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _bounded_ref(text: str) -> SanitizedContentReference:
    return SanitizedContentReference(
        content_ref_id=CONTENT_REF_ID,
        evidence_ref_id=ORIGIN_ID,
        answer_component_id=COMPONENT_ID,
        content_kind="bounded_excerpt",
        bounded_text=text,
        source_id=str(SOURCE_ID),
        source_url="https://example.gov/current-rule",
        source_title="Current rule",
    )


def _passage(**overrides: Any) -> dict[str, Any]:
    passage = {
        "source_id": SOURCE_ID,
        "url": "https://example.gov/current-rule",
        "title": "Current rule",
        "text": "Official current rule excerpt.",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
    }
    passage.update(overrides)
    return passage


def _ledger_projection() -> dict[str, Any]:
    return {
        "owner": "RunKernel.EvidenceLedger",
        "schema_version": "evidence_ledger_ag91j_v1",
        "candidate_records": [
            {
                "candidate_id": ORIGIN_ID,
                "url": "https://example.gov/current-rule",
                "normalized_source_identity": "https://example.gov/current-rule",
                "title": "Current rule",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
                "readable_status": "readable",
                "fact_disposition": "accepted",
                "contextual_only": False,
                "lower_tier": False,
                "final_evidence_eligible": True,
            }
        ],
        "source_requirements": [],
        "requirement_links": [],
        "custody_gaps": [],
    }


def _semantic_source_binding(content_digest: str) -> dict[str, Any]:
    return {
        "origin_evidence_ref_id": ORIGIN_ID,
        "origin_evidence_ref_kind": "evidence_ledger_candidate",
        "content_ref_id": CONTENT_REF_ID,
        "content_digest": content_digest,
        "coverage_record_id": COVERAGE_RECORD_ID,
        "coverage_record_digest": COVERAGE_RECORD_DIGEST,
        "component_id": COMPONENT_ID,
        "component_digest": COMPONENT_DIGEST,
    }


def _semantic_ref_projection(content_digest: str | None = None) -> dict[str, Any]:
    content_digest = content_digest or ("f" * 64)
    return {
        "schema_version": SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
        "available": True,
        "semantic_state_facts_digest": SEMANTIC_DIGEST,
        "accepted_contract_digest": ACCEPTED_CONTRACT_DIGEST,
        "component_refs": [
            {"component_id": COMPONENT_ID, "component_digest": COMPONENT_DIGEST}
        ],
        "coverage_record_refs": [
            {
                "coverage_record_id": COVERAGE_RECORD_ID,
                "coverage_record_digest": COVERAGE_RECORD_DIGEST,
                "answer_component_id": COMPONENT_ID,
            }
        ],
        "semantic_observation_refs": [
            {"observation_id": OBSERVATION_ID, "observation_digest": OBSERVATION_DIGEST}
        ],
        "sanitized_content_ref_ids": [CONTENT_REF_ID],
        "content_ref_digests": [content_digest],
        "evidence_ids": [ORIGIN_ID],
        "semantic_source_ref_bindings": [_semantic_source_binding(content_digest)],
        "source_obligation_refs": ["source-obligation:official-current"],
        "content_refs_available": True,
        "coverage_refs_available": True,
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }


def _sufficiency_projection(
    semantic_ref_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    semantic_consumption: dict[str, Any] = {
        "schema_version": "sufficiency_semantic_state_consumption_ag_sem_09_v1",
        "semantic_state_facts_digest": SEMANTIC_DIGEST,
        "blocker_count": 0,
        "blocker_codes": [],
        "direct_answer_blocked": False,
        "finalization_blocked": False,
        "required_component_count": 1,
        "covered_component_count": 1,
    }
    if semantic_ref_projection is not None:
        semantic_consumption["semantic_ref_projection"] = dict(
            semantic_ref_projection
        )
    return RunSufficiencyJudgment(
        judgment_id="ag-auth-mat-01:judgment",
        decision=RunSufficiencyDecision.READY_DIRECT,
        final_answer_posture=SufficiencyPosture.DIRECT_ANSWER,
        final_answer_allowed=True,
        semantic_consumption=semantic_consumption,
    ).to_projection()


def _packet(content_digest: str | None = None) -> FinalAnswerPacket:
    return build_final_answer_packet(
        run_id="ag-auth-mat-01",
        final_evidence=[_passage()],
        author_evidence=[_passage()],
        source_obligation_projection=_ledger_projection(),
        sufficiency_judgment_projection=_sufficiency_projection(
            _semantic_ref_projection(content_digest)
        ),
    )


def _payload(packet: FinalAnswerPacket):
    return packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
        author_provider="fast-provider",
        author_model="fast-model",
    )


def _packet_with_materialization_ref(ref: SanitizedContentReference) -> FinalAnswerPacket:
    packet = _packet(ref.content_digest)
    return replace(
        packet,
        semantic_content_coverage_ref_projection={
            **dict(packet.semantic_content_coverage_ref_projection),
            "author_materialization_content_refs": [ref.to_dict()],
        },
    )


def _prepare_product_packet(kernel: RunKernel):
    action = kernel.authorize_final_answer_packet_prepare(inputs={"candidate_count": 1})
    return execute_final_answer_packet_prepare_action(
        action,
        run_id=kernel.state.run_id,
        query="What is the current official rule?",
        intent="research",
        report_type="general",
        query_type="general",
        core_topic="current official rule",
        primary_entity="Example Agency",
        anchor_packet_telemetry={},
        final_top_evidence=[_passage()],
        author_evidence=[_passage()],
        ordered_sources=["- [101] [Current rule](https://example.gov/current-rule)"],
        unique_source_urls={"https://example.gov/current-rule": SOURCE_ID},
        query_lineage_refs={},
        corpus_weak=False,
        failure_card_payload={"show": False, "reason": None},
        conflicts_present=False,
        synth_was_insufficient=False,
        author_notes="",
        author_prompt="BASE AUTHOR PROMPT",
        default_system={"author": "AUTHOR SYSTEM"},
        analyst_effort="medium",
        estimate_from_priors_author=False,
        relevance_low=False,
        strategy="Balanced",
        fast_provider="fast-provider",
        fast_model="fast-model",
        smart_provider="smart-provider",
        smart_model="smart-model",
        evidence_ledger_projection=_ledger_projection(),
        sufficiency_judgment_projection=_sufficiency_projection(
            _semantic_ref_projection()
        ),
    )


def _assert_materialization_trace_ref_sealed(trace_ref: Mapping[str, Any]) -> None:
    assert trace_ref["schema_version"] == (
        FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_MATERIALIZATION_TRACE_SCHEMA_VERSION
    )
    serialized = json.dumps(trace_ref, sort_keys=True)
    for forbidden in (
        "block_text",
        "Bounded semantic excerpt from",
        "Official current rule excerpt",
        "author_materialization_content_refs",
        "component_refs",
        "coverage_record_refs",
        "semantic_observation_refs",
        "sanitized_content_ref_ids",
        "content_ref_digests",
        "semantic_ref_evidence_ids",
        "semantic_packet_evidence_bindings",
        CONTENT_REF_ID,
        COVERAGE_RECORD_ID,
        OBSERVATION_ID,
    ):
        assert forbidden not in serialized


def test_summary_materialization_is_model_visible_and_trace_ref_sealed() -> None:
    packet = _packet()
    payload = _payload(packet)
    materialization = dict(payload.semantic_author_materialization)
    trace_ref = payload.to_trace_ref()["semantic_author_materialization_trace_ref"]
    block = materialization["block_text"]

    assert materialization["schema_version"] == (
        FINAL_ANSWER_SEMANTIC_AUTHOR_MATERIALIZATION_SCHEMA_VERSION
    )
    assert materialization["available"] is True
    assert materialization["component_count"] == 1
    assert materialization["excerpt_count"] == 0
    assert materialization["bounded_text_included"] is False
    assert materialization["unavailable_reason"] == "bounded_excerpt_not_packet_owned"
    assert materialization["semantic_packet_evidence_binding_count"] == 1
    assert materialization["semantic_packet_evidence_binding_digest"] == (
        _stable_safe_digest(packet.semantic_packet_evidence_bindings)
    )
    assert "CONTROLLED SEMANTIC CONTEXT" in payload.prompt
    assert "CONTROLLED SEMANTIC CONTEXT" in block
    assert "Bounded semantic excerpt from" not in block
    assert "Boundary: this block supports drafting only" in block
    for forbidden in (
        COMPONENT_ID,
        CONTENT_REF_ID,
        COVERAGE_RECORD_ID,
        OBSERVATION_ID,
        SEMANTIC_DIGEST,
        ACCEPTED_CONTRACT_DIGEST,
        "https://example.gov/current-rule",
        "Current rule",
        "citation_id",
        "semantic_packet_evidence_bindings",
    ):
        assert forbidden not in block

    assert trace_ref["available"] is True
    assert trace_ref["materialization_digest"] == materialization[
        "materialization_digest"
    ]
    assert trace_ref["semantic_materialization_block_hash"] == materialization[
        "semantic_materialization_block_hash"
    ]
    assert trace_ref["semantic_materialization_block_length"] == len(block)
    assert trace_ref["prompt_visible"] is True
    assert trace_ref["model_request_visible"] is True
    assert trace_ref["bounded_text_retained"] is False
    assert trace_ref["raw_content_included"] is False
    assert trace_ref["raw_prompt_retained"] is False
    assert trace_ref["provider_payload_retained"] is False
    assert trace_ref["final_text_included"] is False
    _assert_materialization_trace_ref_sealed(trace_ref)


def test_digest_verified_excerpt_is_capped_and_not_retained_in_refs() -> None:
    long_text = (
        "Official    current rule excerpt with   normalized whitespace. "
        + "supporting sentence " * 50
        + "TAIL_SENTINEL_AFTER_LIMIT"
    )
    content_ref = _bounded_ref(long_text)
    packet = _packet_with_materialization_ref(content_ref)
    payload = _payload(packet)
    trace_ref = payload.to_trace_ref()["semantic_author_materialization_trace_ref"]
    normalized_excerpt = " ".join(long_text.strip().split())[:600]

    assert "Bounded semantic excerpt from citation-eligible Source ID 101" in (
        payload.prompt
    )
    assert normalized_excerpt in payload.prompt
    assert "TAIL_SENTINEL_AFTER_LIMIT" not in payload.prompt
    assert trace_ref["excerpt_count"] == 1
    assert trace_ref["bounded_text_included"] is True
    assert trace_ref["bounded_text_retained"] is False
    assert packet.semantic_content_coverage_ref_projection[
        "author_materialization_content_refs"
    ]

    packet_with_payload = packet.with_author_input_payload(payload)
    sealed_serialization = json.dumps(
        [
            payload.to_trace_ref(),
            packet_with_payload.author_input_refs,
            packet.to_dict(),
        ],
        sort_keys=True,
    )
    assert normalized_excerpt not in sealed_serialization
    assert "TAIL_SENTINEL_AFTER_LIMIT" not in sealed_serialization
    assert "author_materialization_content_refs" not in sealed_serialization
    assert '"bounded_text":' not in sealed_serialization
    _assert_materialization_trace_ref_sealed(trace_ref)


def test_digest_mismatch_omits_unsafe_excerpt() -> None:
    good_ref = _bounded_ref("Digest-verified text that should not appear.")
    packet = _packet(good_ref.content_digest)
    bad_ref = {
        **good_ref.to_dict(),
        "bounded_text": "UNSAFE DIGEST MISMATCH EXCERPT",
    }
    tampered_packet = replace(
        packet,
        semantic_content_coverage_ref_projection={
            **dict(packet.semantic_content_coverage_ref_projection),
            "author_materialization_content_refs": [bad_ref],
        },
    )

    payload = _payload(tampered_packet)
    trace_ref = payload.to_trace_ref()["semantic_author_materialization_trace_ref"]

    assert "CONTROLLED SEMANTIC CONTEXT" in payload.prompt
    assert "UNSAFE DIGEST MISMATCH EXCERPT" not in payload.prompt
    assert "Bounded semantic excerpt from" not in payload.prompt
    assert trace_ref["bounded_text_included"] is False
    assert trace_ref["excerpt_count"] == 0
    assert trace_ref["unavailable_reason"] == "bounded_excerpt_digest_mismatch"


def test_legacy_non_semantic_packet_has_no_materialization_delta() -> None:
    packet = FinalAnswerPacket(packet_id="ag-auth-mat-01-legacy")
    payload = _payload(packet)

    assert "CONTROLLED SEMANTIC CONTEXT" not in payload.prompt
    assert payload.semantic_author_materialization == {}
    assert "semantic_author_materialization_trace_ref" not in payload.to_trace_ref()
    assert payload.prompt == "BASE AUTHOR PROMPT" + payload.authority_block


def test_author_execution_sends_materialization_only_through_prompt() -> None:
    kernel = RunKernel.start(run_id="ag-auth-mat-01-runtime", request_id="req")
    prepared = _prepare_product_packet(kernel)
    kernel.reduce(prepared.observation)
    action = kernel.authorize_author_execution(inputs={})
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_ask_model(*args: Any, **kwargs: Any):
        calls.append((args, kwargs))
        return iter(["RAW MODEL FINAL ANSWER"])

    result = execute_author_action(
        action,
        author_payload=prepared.author_payload,
        ask_model=fake_ask_model,
        system_prompt_registry={"author": "AUTHOR SYSTEM"},
        base_url="http://local",
        api_key=None,
        query="ordinary query",
    )
    kernel.reduce(result.observation)

    assert len(calls) == 1
    assert calls[0][0] == (prepared.author_payload.prompt, "AUTHOR SYSTEM")
    assert "CONTROLLED SEMANTIC CONTEXT" in calls[0][0][0]
    assert "Bounded semantic excerpt from" not in calls[0][0][0]
    assert calls[0][1] == {
        "provider": "fast-provider",
        "model": "fast-model",
        "effort": "medium",
        "base_url": "http://local",
        "api_key": None,
        "stream": True,
        "use_reasoning": False,
    }

    manifest = result.observation.payload["author_invocation_authority_manifest"]
    trace_ref = prepared.author_payload.to_trace_ref()[
        "semantic_author_materialization_trace_ref"
    ]
    assert manifest["semantic_materialization_available"] is True
    assert manifest["semantic_materialization_digest"] == trace_ref[
        "materialization_digest"
    ]
    assert manifest["semantic_materialization_block_hash"] == trace_ref[
        "semantic_materialization_block_hash"
    ]
    assert manifest["semantic_materialization_block_length"] == trace_ref[
        "semantic_materialization_block_length"
    ]
    assert manifest["semantic_materialization_component_count"] == 1
    assert manifest["semantic_materialization_excerpt_count"] == 0
    assert manifest["semantic_packet_evidence_binding_count"] == 1
    assert manifest["semantic_packet_evidence_binding_digest"] == trace_ref[
        "semantic_packet_evidence_binding_digest"
    ]
    assert manifest["prompt_visible"] is True
    assert manifest["model_request_visible"] is True
    assert manifest["bounded_text_included"] is False
    assert manifest["bounded_text_retained"] is False
    assert manifest["raw_content_included"] is False
    assert manifest["raw_prompt_included"] is False
    assert manifest["provider_payload_retained"] is False
    assert manifest["final_text_included"] is False

    serialized = json.dumps(
        [
            action.inputs,
            prepared.author_payload.to_trace_ref(),
            result.observation.payload,
            manifest,
            kernel.to_trace_fragment(),
        ],
        sort_keys=True,
    )
    for forbidden in (
        "BASE AUTHOR PROMPT",
        "AUTHOR SYSTEM",
        "RAW MODEL FINAL ANSWER",
        "CONTROLLED SEMANTIC CONTEXT",
        "Official current rule excerpt.",
        '"provider_payload":',
        '"raw_provider_payload":',
        '"raw_content":',
        "semantic_packet_evidence_bindings",
        "sanitized_content_ref_ids",
        "content_ref_digests",
        "coverage_record_refs",
        "semantic_observation_refs",
        "db_row",
        "cache",
        "full_trace",
        "logs",
        "secret",
        "token",
    ):
        assert forbidden not in serialized


def test_citation_and_source_obligation_records_are_non_delta() -> None:
    content_ref = _bounded_ref("Official current rule excerpt.")
    packet = _packet(content_ref.content_digest)
    packet_with_ref = replace(
        packet,
        semantic_content_coverage_ref_projection={
            **dict(packet.semantic_content_coverage_ref_projection),
            "author_materialization_content_refs": [content_ref.to_dict()],
        },
    )

    before_citations = tuple(record.to_dict() for record in packet.citation_records)
    before_obligations = tuple(record.to_dict() for record in packet.source_obligations)
    payload = _payload(packet_with_ref)

    assert tuple(record.to_dict() for record in packet_with_ref.citation_records) == (
        before_citations
    )
    assert tuple(record.to_dict() for record in packet_with_ref.source_obligations) == (
        before_obligations
    )
    assert payload.citation_source_ids == tuple(
        record.source_id
        for record in packet.citation_eligible
        if record.source_id is not None
    )
    assert packet_with_ref.citation_records == packet.citation_records
    assert packet_with_ref.source_obligations == packet.source_obligations


def test_static_guards_keep_materialization_out_of_closed_surfaces() -> None:
    packet_source = PACKET.read_text(encoding="utf-8")
    author_source = AUTHOR_RUNTIME.read_text(encoding="utf-8")
    prompt_source = PROMPT_ASSEMBLY.read_text(encoding="utf-8")
    pipeline_source = PIPELINE.read_text(encoding="utf-8")

    assert "semantic_author_materialization" in packet_source
    assert "author_payload.prompt" in author_source
    assert "semantic_author_materialization" not in prompt_source
    assert "semantic_author_materialization" not in pipeline_source
    assert "semantic_author_materialization" not in (
        ROOT / "core" / "retrieval.py"
    ).read_text(encoding="utf-8")
    assert "semantic_author_materialization" not in (
        ROOT / "core" / "retrieval_dispatch_runtime.py"
    ).read_text(encoding="utf-8")
    assert "semantic_author_materialization" not in (
        ROOT / "core" / "search_providers.py"
    ).read_text(encoding="utf-8")
    for token in ("AF4B2", "AF4D", "AF5A", "AF5B", "followup_author"):
        assert token not in packet_source
