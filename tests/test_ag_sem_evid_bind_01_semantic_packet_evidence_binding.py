from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.final_answer_packet import (
    FINAL_ANSWER_PACKET_SEMANTIC_PACKET_EVIDENCE_BINDING_SCHEMA_VERSION,
    FinalAnswerPacket,
    _safe_json,
    semantic_packet_evidence_binding_digest,
)
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    SufficiencyPosture,
)
from core.sufficiency_semantic_state_consumption_runtime import (
    SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
)

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "core" / "final_answer_packet.py"
ADAPTER = ROOT / "core" / "final_answer_runtime_adapter.py"
AUTHOR_RUNTIME = ROOT / "core" / "author_execution_runtime.py"
PROMPT_ASSEMBLY = ROOT / "core" / "runtime_prompt_assembly.py"

SEMANTIC_SCHEMA = "sufficiency_semantic_state_consumption_ag_sem_09_v1"
SEMANTIC_DIGEST = "a" * 64
ACCEPTED_CONTRACT_DIGEST = "b" * 64
COMPONENT_ID = "component:current-rule"
COMPONENT_DIGEST = "c" * 64
COVERAGE_RECORD_ID = "coverage:current-rule"
COVERAGE_RECORD_DIGEST = "d" * 64
OBSERVATION_ID = "observation:current-rule"
OBSERVATION_DIGEST = "e" * 64
CONTENT_REF_ID = "content:candidate:official-rule"
CONTENT_DIGEST = "f" * 64
ORIGIN_ID = "candidate:official-rule"
MISMATCH_ORIGIN_ID = "candidate:other-rule"


def _stable_safe_digest(value: Any) -> str:
    return sha256(
        json.dumps(
            _safe_json(value),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _passage(**overrides: Any) -> dict[str, Any]:
    passage = {
        "source_id": 101,
        "url": "https://example.gov/current-rule",
        "title": "Current rule",
        "text": "Official current rule excerpt.",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
    }
    passage.update(overrides)
    return passage


def _ledger_projection(*, candidate_id: str = ORIGIN_ID, url: str | None = None) -> dict[str, Any]:
    return {
        "owner": "RunKernel.EvidenceLedger",
        "schema_version": "evidence_ledger_ag91j_v1",
        "candidate_records": [
            {
                "candidate_id": candidate_id,
                "url": url or "https://example.gov/current-rule",
                "normalized_source_identity": (
                    url or "https://example.gov/current-rule"
                ),
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


def _semantic_source_binding(**overrides: Any) -> dict[str, Any]:
    binding = {
        "origin_evidence_ref_id": ORIGIN_ID,
        "origin_evidence_ref_kind": "evidence_ledger_candidate",
        "content_ref_id": CONTENT_REF_ID,
        "content_digest": CONTENT_DIGEST,
        "coverage_record_id": COVERAGE_RECORD_ID,
        "coverage_record_digest": COVERAGE_RECORD_DIGEST,
        "component_id": COMPONENT_ID,
        "component_digest": COMPONENT_DIGEST,
    }
    binding.update(overrides)
    return binding


def _semantic_ref_projection(**overrides: Any) -> dict[str, Any]:
    projection = {
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
        "content_ref_digests": [CONTENT_DIGEST],
        "evidence_ids": [ORIGIN_ID],
        "semantic_source_ref_bindings": [_semantic_source_binding()],
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
    projection.update(overrides)
    return projection


def _sufficiency_projection(
    semantic_ref_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    semantic_consumption: dict[str, Any] = {
        "schema_version": SEMANTIC_SCHEMA,
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
        judgment_id="ag-sem-evid-bind-01:judgment",
        decision=RunSufficiencyDecision.READY_DIRECT,
        final_answer_posture=SufficiencyPosture.DIRECT_ANSWER,
        final_answer_allowed=True,
        semantic_consumption=semantic_consumption,
    ).to_projection()


def _packet(
    *,
    semantic_ref_projection: Mapping[str, Any] | None = None,
    ledger_projection: Mapping[str, Any] | None = None,
    final_evidence: list[dict[str, Any]] | None = None,
) -> FinalAnswerPacket:
    return build_final_answer_packet(
        run_id="ag-sem-evid-bind-01",
        final_evidence=final_evidence or [_passage()],
        author_evidence=final_evidence or [_passage()],
        source_obligation_projection=(
            _ledger_projection() if ledger_projection is None else ledger_projection
        ),
        sufficiency_judgment_projection=(
            _sufficiency_projection(
                _semantic_ref_projection()
                if semantic_ref_projection is None
                else semantic_ref_projection
            )
            if semantic_ref_projection is not False
            else None
        ),
    )


def test_origin_stamping_uses_matched_evidence_ledger_candidate_record() -> None:
    packet = _packet(semantic_ref_projection=False)

    record = packet.evidence_allowed[0]

    assert record.origin_evidence_ref_id == ORIGIN_ID
    assert record.origin_evidence_ref_kind == "evidence_ledger_candidate"
    assert record.to_dict()["origin_evidence_ref_id"] == ORIGIN_ID
    assert packet.semantic_packet_evidence_bindings == ()


def test_no_guess_fallback_without_matching_candidate_record() -> None:
    packet = _packet(
        semantic_ref_projection=False,
        ledger_projection=_ledger_projection(url="https://example.gov/different"),
    )

    assert packet.evidence_allowed[0].origin_evidence_ref_id is None
    assert packet.semantic_packet_evidence_bindings == ()

    with pytest.raises(ValueError, match="unresolved origin evidence refs"):
        _packet(ledger_projection=_ledger_projection(url="https://example.gov/different"))


def test_semantic_packet_evidence_binding_joins_semantic_refs_to_allowed_packet_evidence() -> None:
    packet = _packet()

    assert len(packet.semantic_packet_evidence_bindings) == 1
    row = dict(packet.semantic_packet_evidence_bindings[0])
    allowed_id = packet.evidence_allowed[0].evidence_id

    assert row["schema_version"] == (
        FINAL_ANSWER_PACKET_SEMANTIC_PACKET_EVIDENCE_BINDING_SCHEMA_VERSION
    )
    assert row["origin_evidence_ref_id"] == ORIGIN_ID
    assert row["origin_evidence_ref_kind"] == "evidence_ledger_candidate"
    assert row["packet_evidence_id"] == allowed_id
    assert row["content_ref_id"] == CONTENT_REF_ID
    assert row["content_digest"] == CONTENT_DIGEST
    assert row["coverage_record_id"] == COVERAGE_RECORD_ID
    assert row["coverage_record_digest"] == COVERAGE_RECORD_DIGEST
    assert row["component_id"] == COMPONENT_ID
    assert row["component_digest"] == COMPONENT_DIGEST
    assert row["binding_digest"] == semantic_packet_evidence_binding_digest(row)

    manifest = packet.semantic_evidence_authority_manifest
    assert manifest["semantic_packet_evidence_binding_available"] is True
    assert manifest["semantic_packet_evidence_binding_count"] == 1
    assert manifest["semantic_packet_evidence_binding_digest"] == _stable_safe_digest(
        packet.semantic_packet_evidence_bindings
    )
    assert "semantic_packet_evidence_bindings" not in manifest

    payload = packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )
    assert "CONTROLLED SEMANTIC CONTEXT" in payload.prompt
    trace_ref = payload.to_trace_ref()["semantic_content_coverage_ref_envelope_trace_ref"]
    assert trace_ref["semantic_packet_evidence_binding_count"] == 1
    assert trace_ref["semantic_packet_evidence_binding_digest"] == manifest[
        "semantic_packet_evidence_binding_digest"
    ]
    assert "semantic_packet_evidence_bindings" not in trace_ref
    assert "semantic_packet_evidence_bindings" not in payload.prompt


def test_semantic_packet_evidence_binding_fails_closed_on_mismatch() -> None:
    mismatch_projection = _semantic_ref_projection(
        evidence_ids=[MISMATCH_ORIGIN_ID],
        semantic_source_ref_bindings=[
            _semantic_source_binding(origin_evidence_ref_id=MISMATCH_ORIGIN_ID)
        ],
    )

    with pytest.raises(ValueError, match="unresolved origin evidence refs"):
        _packet(semantic_ref_projection=mismatch_projection)


def test_semantic_packet_evidence_binding_digest_tamper_fails_validation() -> None:
    packet = _packet()
    tampered = dict(packet.semantic_packet_evidence_bindings[0])
    tampered["content_digest"] = "9" * 64

    with pytest.raises(ValueError, match="binding_digest does not match"):
        replace(packet, semantic_packet_evidence_bindings=(tampered,))


def test_legacy_non_semantic_packet_does_not_claim_authoritative_empty_binding() -> None:
    packet = _packet(semantic_ref_projection=False, ledger_projection={})

    assert packet.evidence_allowed[0].origin_evidence_ref_id is None
    assert packet.semantic_packet_evidence_bindings == ()
    assert "semantic_packet_evidence_bindings" not in packet.to_dict()
    assert packet.semantic_evidence_authority_manifest == {}

    payload = packet.to_author_input_payload(
        prompt="unchanged author prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )
    assert "semantic_packet_evidence_bindings" not in payload.prompt
    assert "semantic_content_coverage_ref_envelope_trace_ref" not in payload.to_trace_ref()


def test_semantic_packet_evidence_binding_raw_leakage_scan() -> None:
    packet = _packet()
    payload = packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )
    serializations = json.dumps(
        [
            packet.evidence_allowed[0].to_dict(),
            packet.semantic_packet_evidence_bindings,
            packet.semantic_evidence_authority_manifest,
            payload.semantic_content_coverage_ref_envelope,
            payload.to_trace_ref().get("semantic_content_coverage_ref_envelope_trace_ref"),
        ],
        sort_keys=True,
    )

    for forbidden in (
        "SENTINEL_RAW_SOURCE_TEXT",
        "SENTINEL_BOUNDED_TEXT",
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
        "SENTINEL_CACHE_ROW",
        "SENTINEL_FULL_TRACE",
        "SENTINEL_SECRET_TOKEN",
    ):
        assert forbidden not in serializations
    assert "Official current rule excerpt" not in serializations


def test_static_guards_keep_binding_out_of_closed_surfaces() -> None:
    packet_source = PACKET.read_text(encoding="utf-8")
    adapter_source = ADAPTER.read_text(encoding="utf-8")
    author_source = AUTHOR_RUNTIME.read_text(encoding="utf-8")
    prompt_source = PROMPT_ASSEMBLY.read_text(encoding="utf-8")

    assert "semantic_observation_admission_history" not in packet_source
    assert "component_coverage_history" not in packet_source
    assert "semantic_observation_admission_history" not in adapter_source
    assert "component_coverage_history" not in adapter_source
    assert "semantic_packet_evidence_bindings" not in author_source
    assert "semantic_packet_evidence_bindings" not in prompt_source

    for path in (ROOT / "core").glob("*retrieval*.py"):
        assert "semantic_packet_evidence_bindings" not in path.read_text(
            encoding="utf-8"
        )
    for path in (ROOT / "core").glob("*search*.py"):
        assert "semantic_packet_evidence_bindings" not in path.read_text(
            encoding="utf-8"
        )
