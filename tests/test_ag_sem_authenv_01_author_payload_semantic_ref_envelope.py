"""AG-SEM-AUTHENV-01 Author payload semantic ref envelope bridge."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.final_answer_packet import (
    FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_SCHEMA_VERSION,
    FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_TRACE_SCHEMA_VERSION,
    FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION,
    CitationEligibilityRecord,
    CitationEligibilityStatus,
    CitationRequirementStatus,
    EvidenceAuthorityStatus,
    FinalAnswerPacket,
    FinalEvidenceRecord,
    _safe_json,
)
from core.final_answer_packet_runtime import execute_final_answer_packet_prepare_action
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    SufficiencyPosture,
)
from core.run_kernel import ActionType, RunKernel
from core.sufficiency_semantic_state_consumption_runtime import (
    SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
)

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "core" / "final_answer_packet.py"
ADAPTER = ROOT / "core" / "final_answer_runtime_adapter.py"
AUTHOR_RUNTIME = ROOT / "core" / "author_execution_runtime.py"
PROMPT_ASSEMBLY = ROOT / "core" / "runtime_prompt_assembly.py"
PACKET_RUNTIME = ROOT / "core" / "final_answer_packet_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"

TRACE_REF_KEY = "semantic_content_coverage_ref_envelope_trace_ref"
ENVELOPE_KEY = "semantic_content_coverage_ref_envelope"
SEMANTIC_DIGEST = "a" * 64
ACCEPTED_CONTRACT_DIGEST = "b" * 64
COMPONENT_REF = {
    "component_id": "component:current-rule",
    "component_digest": "c" * 64,
}
COVERAGE_REF = {
    "coverage_record_id": "coverage:current-rule",
    "coverage_record_digest": "d" * 64,
    "answer_component_id": "component:current-rule",
}
OBSERVATION_REF = {
    "observation_id": "observation:current-rule",
    "observation_digest": "e" * 64,
}
CONTENT_REF_ID = "content:current-rule"
CONTENT_DIGEST = "f" * 64
SEMANTIC_EVIDENCE_ID = "evidence:current-rule"
SOURCE_OBLIGATION_REF = "source-obligation:official-current"
SEMANTIC_SOURCE_BINDING = {
    "origin_evidence_ref_id": SEMANTIC_EVIDENCE_ID,
    "origin_evidence_ref_kind": "evidence_ledger_candidate",
    "content_ref_id": CONTENT_REF_ID,
    "content_digest": CONTENT_DIGEST,
    "coverage_record_id": COVERAGE_REF["coverage_record_id"],
    "coverage_record_digest": COVERAGE_REF["coverage_record_digest"],
    "component_id": COMPONENT_REF["component_id"],
    "component_digest": COMPONENT_REF["component_digest"],
}
FULL_ARRAY_KEYS = (
    "component_refs",
    "coverage_record_refs",
    "semantic_observation_refs",
    "sanitized_content_ref_ids",
    "content_ref_digests",
    "semantic_ref_evidence_ids",
    "source_obligation_refs",
    "author_materialization_content_refs",
)
FORBIDDEN_RAW_OR_FULL_MATERIALIZATION_KEYS = (
    "author_materialization_content_refs",
    "raw_content",
    "raw_text",
    "raw_source_text",
    "text_excerpts",
    "bounded_text",
    "prompt",
    "prompt_text",
    "raw_prompt",
    "system_prompt",
    "provider_payload",
    "raw_provider_payload",
    "model_payload",
    "model_request",
    "model_response",
    "raw_model_response",
    "db_row",
    "db_rows",
    "cache",
    "cache_row",
    "cache_rows",
    "full_trace",
    "log",
    "logs",
    "private_logs",
)


def _passage(**overrides: Any) -> dict[str, Any]:
    passage = {
        "source_id": 101,
        "url": "https://example.gov/current-rule",
        "title": "Current rule",
        "text": "Official current rule excerpt.",
        "source_tier": "official",
        "source_class": "official_current_rules",
    }
    passage.update(overrides)
    return passage


def _evidence_ledger_projection() -> dict[str, Any]:
    return {
        "owner": "RunKernel.EvidenceLedger",
        "schema_version": "evidence_ledger_ag91j_v1",
        "candidate_records": [
            {
                "candidate_id": SEMANTIC_EVIDENCE_ID,
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


def _semantic_ref_projection(**overrides: Any) -> dict[str, Any]:
    projection = {
        "schema_version": SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
        "available": True,
        "semantic_state_facts_digest": SEMANTIC_DIGEST,
        "accepted_contract_digest": ACCEPTED_CONTRACT_DIGEST,
        "component_refs": [COMPONENT_REF],
        "coverage_record_refs": [COVERAGE_REF],
        "semantic_observation_refs": [OBSERVATION_REF],
        "sanitized_content_ref_ids": [CONTENT_REF_ID],
        "content_ref_digests": [CONTENT_DIGEST],
        "evidence_ids": [SEMANTIC_EVIDENCE_ID],
        "semantic_source_ref_bindings": [SEMANTIC_SOURCE_BINDING],
        "source_obligation_refs": [SOURCE_OBLIGATION_REF],
        "content_refs_available": True,
        "coverage_refs_available": True,
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }
    projection.update(overrides)
    return projection


def _sufficiency_projection(
    semantic_ref_projection: Mapping[str, Any] | None = None,
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
        judgment_id="ag-sem-authenv-01:judgment",
        decision=RunSufficiencyDecision.READY_DIRECT,
        final_answer_posture=SufficiencyPosture.DIRECT_ANSWER,
        final_answer_allowed=True,
        semantic_consumption=semantic_consumption,
    ).to_projection()


def _packet(
    semantic_ref_projection: Mapping[str, Any] | None = None,
) -> FinalAnswerPacket:
    return build_final_answer_packet(
        run_id="ag-sem-authenv-01",
        final_evidence=[_passage()],
        author_evidence=[_passage()],
        source_obligation_projection=_evidence_ledger_projection(),
        sufficiency_judgment_projection=_sufficiency_projection(
            _semantic_ref_projection()
            if semantic_ref_projection is None
            else semantic_ref_projection
        ),
    )


def _manual_packet(
    projection: Mapping[str, Any] | None = None,
) -> FinalAnswerPacket:
    return FinalAnswerPacket(
        packet_id="ag-sem-authenv-01-manual",
        evidence_records=(
            FinalEvidenceRecord(
                evidence_id="ev-allowed",
                status=EvidenceAuthorityStatus.EVIDENCE_ALLOWED,
                source_id=101,
                url="https://example.gov/current-rule",
            ),
        ),
        citation_records=(
            CitationEligibilityRecord(
                citation_id="cit-1",
                evidence_id="ev-allowed",
                status=CitationEligibilityStatus.CITATION_ELIGIBLE,
                requirement=CitationRequirementStatus.CITATION_OPTIONAL,
                source_id=101,
            ),
        ),
        semantic_content_coverage_ref_projection=dict(projection or {}),
    )


def _payload(packet: FinalAnswerPacket):
    return packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )


def _expected_envelope(packet: FinalAnswerPacket) -> dict[str, Any]:
    projection = packet.semantic_content_coverage_ref_projection
    expected = {
        "schema_version": (
            FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_SCHEMA_VERSION
        ),
        "available": True,
        "source_packet_id": packet.packet_id,
        "source_packet_schema_version": packet.schema_version,
        "source_projection_schema_version": projection["schema_version"],
        "source_projection_digest": projection["source_projection_digest"],
        "envelope_source": "FinalAnswerPacket.semantic_content_coverage_ref_projection",
        "semantic_state_facts_digest": projection["semantic_state_facts_digest"],
        "accepted_contract_digest": projection["accepted_contract_digest"],
        "component_refs": [COMPONENT_REF],
        "coverage_record_refs": [COVERAGE_REF],
        "semantic_observation_refs": [OBSERVATION_REF],
        "sanitized_content_ref_ids": [CONTENT_REF_ID],
        "content_ref_digests": [CONTENT_DIGEST],
        "semantic_ref_evidence_ids": [SEMANTIC_EVIDENCE_ID],
        "source_obligation_refs": [SOURCE_OBLIGATION_REF],
        "content_refs_available": True,
        "coverage_refs_available": True,
        "semantic_packet_evidence_binding_available": True,
        "semantic_packet_evidence_binding_count": len(
            packet.semantic_packet_evidence_bindings
        ),
        "semantic_packet_evidence_binding_digest": _stable_safe_digest(
            packet.semantic_packet_evidence_bindings
        ),
        "author_payload_visible": True,
        "authority_payload_visible": False,
        "authority_block_visible": False,
        "prompt_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
        "raw_content_included": False,
        "bounded_text_included": False,
        "raw_prompt_included": False,
        "provider_payload_included": False,
    }
    material_refs = projection.get("author_materialization_content_refs")
    if material_refs:
        expected["author_materialization_content_ref_count"] = len(material_refs)
        expected["author_materialization_content_ref_digest"] = _stable_safe_digest(
            material_refs
        )
    return expected


def _stable_safe_digest(value: Any) -> str:
    return sha256(
        json.dumps(
            _safe_json(value),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_walk_keys(item))
        return keys
    if isinstance(value, (list, tuple)):
        keys: set[str] = set()
        for item in value:
            keys.update(_walk_keys(item))
        return keys
    return set()


def _assert_no_raw_or_full_materialization_content(surface: Mapping[str, Any]) -> None:
    surface_keys = _walk_keys(surface)
    for forbidden in FORBIDDEN_RAW_OR_FULL_MATERIALIZATION_KEYS:
        assert forbidden not in surface_keys


def _assert_trace_ref_sealed(trace_ref: Mapping[str, Any]) -> None:
    for key in FULL_ARRAY_KEYS:
        assert key not in trace_ref
    for forbidden in (
        "raw_source_text",
        "raw_text",
        "bounded_text",
        "text_excerpts",
        "prompt_text",
        "raw_prompt",
        "provider_payload",
        "raw_provider_payload",
        "model_payload",
        "model_response",
        "raw_model_response",
        "final_prose",
        "final_text",
        "db_row",
        "db_rows",
        "cache",
        "cache_rows",
        "full_trace",
        "private_logs",
        "logs",
    ):
        assert forbidden not in trace_ref


def test_author_payload_envelope_derives_from_fap_projection_only() -> None:
    packet = _packet()
    payload = _payload(packet)
    envelope = dict(payload.semantic_content_coverage_ref_envelope)
    projection = packet.semantic_content_coverage_ref_projection
    material_refs = projection["author_materialization_content_refs"]

    assert envelope == _expected_envelope(packet)
    assert envelope["schema_version"] == (
        FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_SCHEMA_VERSION
    )
    assert envelope["source_packet_id"] == packet.packet_id
    assert envelope["source_projection_schema_version"] == projection["schema_version"]
    assert envelope["source_projection_digest"] == projection[
        "source_projection_digest"
    ]
    assert envelope["semantic_state_facts_digest"] == projection[
        "semantic_state_facts_digest"
    ]
    assert envelope["component_refs"] == [COMPONENT_REF]
    assert envelope["coverage_record_refs"] == [COVERAGE_REF]
    assert envelope["semantic_observation_refs"] == [OBSERVATION_REF]
    assert envelope["sanitized_content_ref_ids"] == [CONTENT_REF_ID]
    assert envelope["content_ref_digests"] == [CONTENT_DIGEST]
    assert envelope["semantic_ref_evidence_ids"] == [SEMANTIC_EVIDENCE_ID]
    assert envelope["source_obligation_refs"] == [SOURCE_OBLIGATION_REF]
    assert envelope["semantic_packet_evidence_binding_available"] is True
    assert envelope["semantic_packet_evidence_binding_count"] == 1
    assert envelope["semantic_packet_evidence_binding_digest"] == _stable_safe_digest(
        packet.semantic_packet_evidence_bindings
    )
    assert "semantic_packet_evidence_bindings" not in envelope
    assert envelope["author_materialization_content_ref_count"] == len(material_refs)
    assert envelope["author_materialization_content_ref_digest"] == _stable_safe_digest(
        material_refs
    )
    assert "author_materialization_content_refs" not in envelope
    assert envelope["content_refs_available"] is True
    assert envelope["coverage_refs_available"] is True
    assert envelope["author_payload_visible"] is True
    assert envelope["authority_payload_visible"] is False
    assert envelope["authority_block_visible"] is False
    assert envelope["prompt_visible"] is False
    assert envelope["model_request_visible"] is False
    assert envelope["raw_content_included"] is False
    assert envelope["bounded_text_included"] is False
    _assert_no_raw_or_full_materialization_content(envelope)


@pytest.mark.parametrize(
    "projection",
    [
        {},
        {"available": False},
        {
            **_packet().semantic_content_coverage_ref_projection,
            "content_refs_available": False,
        },
        {
            **_packet().semantic_content_coverage_ref_projection,
            "coverage_refs_available": False,
        },
        {
            key: value
            for key, value in _packet().semantic_content_coverage_ref_projection.items()
            if key != "sanitized_content_ref_ids"
        },
        {
            key: value
            for key, value in _packet().semantic_content_coverage_ref_projection.items()
            if key != "content_ref_digests"
        },
        {
            key: value
            for key, value in _packet().semantic_content_coverage_ref_projection.items()
            if key != "coverage_record_refs"
        },
    ],
)
def test_author_payload_envelope_empty_when_projection_unavailable(
    projection: Mapping[str, Any],
) -> None:
    payload = _payload(_manual_packet(projection))

    assert payload.semantic_content_coverage_ref_envelope == {}
    assert TRACE_REF_KEY not in payload.to_trace_ref()


def test_author_payload_envelope_trace_ref_is_digest_and_counts_only() -> None:
    packet = _packet()
    payload = _payload(packet)
    envelope = dict(payload.semantic_content_coverage_ref_envelope)
    trace_ref = payload.to_trace_ref()[TRACE_REF_KEY]
    material_refs = packet.semantic_content_coverage_ref_projection[
        "author_materialization_content_refs"
    ]

    assert trace_ref["schema_version"] == (
        FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_TRACE_SCHEMA_VERSION
    )
    assert trace_ref["available"] is True
    assert trace_ref["source_projection_digest"] == envelope[
        "source_projection_digest"
    ]
    assert trace_ref["envelope_digest"] == _stable_safe_digest(envelope)
    assert trace_ref["semantic_state_facts_digest"] == SEMANTIC_DIGEST
    assert trace_ref["content_refs_available"] is True
    assert trace_ref["coverage_refs_available"] is True
    assert trace_ref["component_ref_count"] == 1
    assert trace_ref["coverage_record_ref_count"] == 1
    assert trace_ref["semantic_observation_ref_count"] == 1
    assert trace_ref["sanitized_content_ref_count"] == 1
    assert trace_ref["content_ref_digest_count"] == 1
    assert trace_ref["semantic_ref_evidence_id_count"] == 1
    assert trace_ref["source_obligation_ref_count"] == 1
    assert trace_ref["semantic_packet_evidence_binding_available"] is True
    assert trace_ref["semantic_packet_evidence_binding_count"] == 1
    assert trace_ref["semantic_packet_evidence_binding_digest"] == _stable_safe_digest(
        packet.semantic_packet_evidence_bindings
    )
    assert "semantic_packet_evidence_bindings" not in trace_ref
    assert trace_ref["author_materialization_content_ref_count"] == len(material_refs)
    assert trace_ref["author_materialization_content_ref_digest"] == _stable_safe_digest(
        material_refs
    )
    assert "author_materialization_content_refs" not in trace_ref
    assert trace_ref["author_payload_visible"] is True
    assert trace_ref["authority_payload_visible"] is False
    assert trace_ref["authority_block_visible"] is False
    assert trace_ref["prompt_visible"] is False
    assert trace_ref["model_request_visible"] is False
    assert trace_ref["final_text_included"] is False
    assert trace_ref["raw_content_included"] is False
    assert trace_ref["bounded_text_included"] is False
    assert trace_ref["raw_prompt_included"] is False
    assert trace_ref["provider_payload_included"] is False
    _assert_no_raw_or_full_materialization_content(trace_ref)
    _assert_trace_ref_sealed(trace_ref)


def test_author_payload_envelope_trace_ref_merges_into_packet_refs_only() -> None:
    packet = _packet()
    payload = _payload(packet)
    packet_with_payload = packet.with_author_input_payload(payload)

    assert TRACE_REF_KEY not in packet.author_input_refs
    assert packet_with_payload.author_input_refs[TRACE_REF_KEY] == (
        payload.to_trace_ref()[TRACE_REF_KEY]
    )
    assert ENVELOPE_KEY not in packet_with_payload.author_input_refs
    for key in FULL_ARRAY_KEYS:
        assert key not in packet_with_payload.author_input_refs[TRACE_REF_KEY]


def test_author_payload_envelope_propagates_through_packet_runtime_and_kernel() -> None:
    kernel = RunKernel.start(run_id="ag-sem-authenv-01-runtime", request_id="req")
    action = kernel.authorize_final_answer_packet_prepare(inputs={"candidate_count": 1})
    result = execute_final_answer_packet_prepare_action(
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
        unique_source_urls={"https://example.gov/current-rule": 101},
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
        evidence_ledger_projection=_evidence_ledger_projection(),
        sufficiency_judgment_projection=_sufficiency_projection(
            _semantic_ref_projection()
        ),
    )
    trace_ref = result.author_payload.to_trace_ref()[TRACE_REF_KEY]

    assert action.action_type is ActionType.FINAL_ANSWER_PACKET_PREPARE
    assert result.author_payload.semantic_content_coverage_ref_envelope
    assert result.observation.payload["author_payload_ref"][TRACE_REF_KEY] == (
        trace_ref
    )
    assert ENVELOPE_KEY not in result.observation.payload["author_payload_ref"]
    for key in FULL_ARRAY_KEYS:
        assert key not in result.observation.payload["author_payload_ref"][TRACE_REF_KEY]

    kernel.reduce(result.observation)

    assert kernel.state.final_answer_authority_projection["author_payload_ref"][
        TRACE_REF_KEY
    ] == trace_ref
    assert ENVELOPE_KEY not in kernel.state.final_answer_authority_projection[
        "author_payload_ref"
    ]
    assert TRACE_REF_KEY not in PACKET_RUNTIME.read_text(encoding="utf-8")
    assert TRACE_REF_KEY not in RUN_KERNEL.read_text(encoding="utf-8")


def test_author_payload_envelope_non_delta_surfaces_and_raw_leakage_scan() -> None:
    packet = _packet()
    packet_without_projection = replace(
        packet,
        semantic_content_coverage_ref_projection={},
    )
    payload = _payload(packet)
    payload_without_projection = _payload(packet_without_projection)

    assert payload.prompt != payload_without_projection.prompt
    assert "CONTROLLED SEMANTIC CONTEXT" in payload.prompt
    assert "CONTROLLED SEMANTIC CONTEXT" in payload.authority_block
    assert "CONTROLLED SEMANTIC CONTEXT" not in payload_without_projection.prompt
    assert payload.authority_payload == payload_without_projection.authority_payload
    assert payload.authority_block != payload_without_projection.authority_block
    assert payload.citation_source_ids == payload_without_projection.citation_source_ids
    assert packet.citation_records == packet_without_projection.citation_records
    assert packet.source_obligations == packet_without_projection.source_obligations
    assert ENVELOPE_KEY not in payload.prompt
    assert ENVELOPE_KEY not in payload.authority_payload
    assert ENVELOPE_KEY not in payload.authority_block
    assert packet.semantic_evidence_authority_manifest[
        "author_payload_visible"
    ] is False
    assert packet.semantic_evidence_authority_manifest[
        "author_payload_ref_envelope_available"
    ] is True

    tainted_projection = {
        **packet.semantic_content_coverage_ref_projection,
        "raw_content": "SENTINEL_RAW_CONTENT",
        "bounded_text": "SENTINEL_BOUNDED_TEXT",
        "raw_source_text": "SENTINEL_RAW_SOURCE_TEXT",
        "text_excerpts": ["SENTINEL_TEXT_EXCERPT"],
        "prompt_text": "SENTINEL_PROMPT_TEXT",
        "raw_prompt": "SENTINEL_RAW_PROMPT",
        "provider_payload": {"private_marker": "SENTINEL_PROVIDER_PAYLOAD"},
        "raw_provider_payload": {
            "private_marker": "SENTINEL_RAW_PROVIDER_PAYLOAD"
        },
        "model_response": "SENTINEL_MODEL_RESPONSE",
        "raw_model_response": "SENTINEL_RAW_MODEL_RESPONSE",
        "final_prose": "SENTINEL_FINAL_PROSE",
        "final_text": "SENTINEL_FINAL_TEXT",
        "db_row": {"private_marker": "SENTINEL_DB_ROW"},
        "cache": {"private_marker": "SENTINEL_CACHE"},
        "full_trace": {"private_marker": "SENTINEL_FULL_TRACE"},
        "logs": ["SENTINEL_LOGS"],
        "author_materialization_content_refs": [
            {
                "content_ref_id": CONTENT_REF_ID,
                "content_digest": CONTENT_DIGEST,
                "bounded_text": "SENTINEL_MATERIALIZATION_BOUNDED_TEXT",
                "raw_text": "SENTINEL_MATERIALIZATION_RAW_TEXT",
                "raw_prompt": "SENTINEL_MATERIALIZATION_RAW_PROMPT",
                "provider_payload": {
                    "private_marker": "SENTINEL_MATERIALIZATION_PROVIDER_PAYLOAD"
                },
                "model_response": "SENTINEL_MATERIALIZATION_MODEL_RESPONSE",
                "db_rows": ["SENTINEL_MATERIALIZATION_DB_ROWS"],
                "cache_rows": ["SENTINEL_MATERIALIZATION_CACHE_ROWS"],
                "full_trace": "SENTINEL_MATERIALIZATION_FULL_TRACE",
                "private_logs": ["SENTINEL_MATERIALIZATION_PRIVATE_LOGS"],
            }
        ],
    }
    tainted_payload = _payload(_manual_packet(tainted_projection))
    tainted_packet = _manual_packet(tainted_projection).with_author_input_payload(
        tainted_payload
    )
    _assert_no_raw_or_full_materialization_content(
        tainted_payload.semantic_content_coverage_ref_envelope
    )
    _assert_no_raw_or_full_materialization_content(
        tainted_payload.to_trace_ref()[TRACE_REF_KEY]
    )
    _assert_no_raw_or_full_materialization_content(
        tainted_packet.author_input_refs[TRACE_REF_KEY]
    )
    encoded = json.dumps(
        (
            tainted_payload.semantic_content_coverage_ref_envelope,
            tainted_payload.to_trace_ref(),
            tainted_packet.author_input_refs,
        ),
        sort_keys=True,
    )
    for forbidden in (
        "SENTINEL_RAW_CONTENT",
        "SENTINEL_BOUNDED_TEXT",
        "SENTINEL_RAW_SOURCE_TEXT",
        "SENTINEL_TEXT_EXCERPT",
        "SENTINEL_PROMPT_TEXT",
        "SENTINEL_RAW_PROMPT",
        "SENTINEL_PROVIDER_PAYLOAD",
        "SENTINEL_RAW_PROVIDER_PAYLOAD",
        "SENTINEL_MODEL_RESPONSE",
        "SENTINEL_RAW_MODEL_RESPONSE",
        "SENTINEL_FINAL_PROSE",
        "SENTINEL_FINAL_TEXT",
        "SENTINEL_DB_ROW",
        "SENTINEL_CACHE",
        "SENTINEL_FULL_TRACE",
        "SENTINEL_LOGS",
        "SENTINEL_MATERIALIZATION_BOUNDED_TEXT",
        "SENTINEL_MATERIALIZATION_RAW_TEXT",
        "SENTINEL_MATERIALIZATION_RAW_PROMPT",
        "SENTINEL_MATERIALIZATION_PROVIDER_PAYLOAD",
        "SENTINEL_MATERIALIZATION_MODEL_RESPONSE",
        "SENTINEL_MATERIALIZATION_DB_ROWS",
        "SENTINEL_MATERIALIZATION_CACHE_ROWS",
        "SENTINEL_MATERIALIZATION_FULL_TRACE",
        "SENTINEL_MATERIALIZATION_PRIVATE_LOGS",
    ):
        assert forbidden not in encoded


def test_static_guards_keep_envelope_out_of_closed_surfaces() -> None:
    packet_source = PACKET.read_text(encoding="utf-8")
    adapter_source = ADAPTER.read_text(encoding="utf-8")
    prompt_assembly = PROMPT_ASSEMBLY.read_text(encoding="utf-8")

    assert "semantic_observation_admission_history" not in packet_source
    assert "component_coverage_history" not in packet_source
    assert "semantic_observation_admission_history" not in adapter_source
    assert "component_coverage_history" not in adapter_source
    assert ENVELOPE_KEY not in prompt_assembly

    for path in (
        ROOT / "core" / "retrieval.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "search_providers.py",
    ):
        assert ENVELOPE_KEY not in path.read_text(encoding="utf-8")

    for path in (PACKET, ADAPTER):
        source = path.read_text(encoding="utf-8")
        for token in ("AF4B2", "AF4D", "AF5A", "AF5B", "followup_author"):
            assert token not in source
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        for module in imported:
            assert "followup_" not in module
            assert "offline_golden_harness" not in module


def test_projection_schema_available_for_control() -> None:
    assert _packet().semantic_content_coverage_ref_projection["schema_version"] == (
        FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION
    )
