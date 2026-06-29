"""AG-SEM-FAP-01 FAP semantic content/coverage ref manifest enrichment."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.final_answer_packet import (
    FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION,
    _safe_json,
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
        judgment_id="ag-sem-fap-01:judgment",
        decision=RunSufficiencyDecision.READY_DIRECT,
        final_answer_posture=SufficiencyPosture.DIRECT_ANSWER,
        final_answer_allowed=True,
        semantic_consumption=semantic_consumption,
    ).to_projection()


def _packet(semantic_ref_projection: Mapping[str, Any] | None = None):
    return build_final_answer_packet(
        run_id="ag-sem-fap-01",
        final_evidence=[_passage()],
        author_evidence=[_passage()],
        source_obligation_projection=_evidence_ledger_projection(),
        sufficiency_judgment_projection=_sufficiency_projection(
            _semantic_ref_projection()
            if semantic_ref_projection is None
            else semantic_ref_projection
        ),
    )


def _expected_source_projection() -> dict[str, Any]:
    return _semantic_ref_projection()


def _expected_source_digest() -> str:
    return sha256(
        json.dumps(
            _expected_source_projection(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _stable_safe_digest(value: Any) -> str:
    return sha256(
        json.dumps(
            _safe_json(value),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _expected_serialized_projection_ref(
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    expected = {
        "schema_version": projection["schema_version"],
        "available": True,
        "source_authority": projection["source_authority"],
        "source_schema_version": projection["source_schema_version"],
        "source_projection_digest": projection["source_projection_digest"],
        "semantic_state_facts_digest": projection["semantic_state_facts_digest"],
        "accepted_contract_digest": projection["accepted_contract_digest"],
        "content_refs_available": True,
        "coverage_refs_available": True,
        "component_ref_count": len(projection["component_refs"]),
        "coverage_record_ref_count": len(projection["coverage_record_refs"]),
        "semantic_observation_ref_count": len(
            projection["semantic_observation_refs"]
        ),
        "sanitized_content_ref_count": len(projection["sanitized_content_ref_ids"]),
        "content_ref_digest_count": len(projection["content_ref_digests"]),
        "semantic_ref_evidence_id_count": len(
            projection["semantic_ref_evidence_ids"]
        ),
        "semantic_source_ref_binding_count": len(
            projection["semantic_source_ref_bindings"]
        ),
        "source_obligation_ref_count": len(projection["source_obligation_refs"]),
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }
    material_refs = projection.get("author_materialization_content_refs")
    if material_refs:
        expected["author_materialization_content_ref_count"] = len(material_refs)
        expected["author_materialization_content_ref_digest"] = _stable_safe_digest(
            material_refs
        )
    return expected


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(_walk_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_walk_keys(item))
        return keys
    return set()


def test_fap_projection_derives_refs_and_digests_from_sufficiency_only() -> None:
    packet = _packet()

    projection = packet.semantic_content_coverage_ref_projection

    assert projection
    assert projection["schema_version"] == (
        FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION
    )
    assert projection["available"] is True
    assert projection["source_authority"] == (
        "RunAuthoritySufficiency.semantic_ref_projection"
    )
    assert projection["source_schema_version"] == (
        SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION
    )
    assert projection["source_projection_digest"] == _expected_source_digest()
    assert projection["semantic_state_facts_digest"] == SEMANTIC_DIGEST
    assert projection["accepted_contract_digest"] == ACCEPTED_CONTRACT_DIGEST
    assert projection["component_refs"] == [COMPONENT_REF]
    assert projection["coverage_record_refs"] == [COVERAGE_REF]
    assert projection["semantic_observation_refs"] == [OBSERVATION_REF]
    assert projection["sanitized_content_ref_ids"] == [CONTENT_REF_ID]
    assert projection["content_ref_digests"] == [CONTENT_DIGEST]
    assert projection["semantic_ref_evidence_ids"] == [SEMANTIC_EVIDENCE_ID]
    assert projection["semantic_source_ref_bindings"] == [SEMANTIC_SOURCE_BINDING]
    assert projection["source_obligation_refs"] == [SOURCE_OBLIGATION_REF]
    assert projection["content_refs_available"] is True
    assert projection["coverage_refs_available"] is True
    assert projection["raw_content_included"] is False
    assert projection["bounded_text_included"] is False
    assert projection["prompt_visible"] is False
    assert projection["author_payload_visible"] is False
    assert projection["model_request_visible"] is False
    assert projection["final_text_included"] is False
    serialized_projection = _expected_serialized_projection_ref(projection)
    assert packet.to_dict()["semantic_content_coverage_ref_projection"] == (
        serialized_projection
    )
    assert packet.to_trace_fragment()["final_answer_packet"][
        "semantic_content_coverage_ref_projection"
    ] == serialized_projection
    for full_ref_key in (
        "component_refs",
        "coverage_record_refs",
        "semantic_observation_refs",
        "sanitized_content_ref_ids",
        "content_ref_digests",
        "semantic_ref_evidence_ids",
        "semantic_source_ref_bindings",
        "source_obligation_refs",
        "author_materialization_content_refs",
    ):
        assert full_ref_key not in serialized_projection


def test_fap_manifest_enriches_available_content_and_coverage_refs() -> None:
    packet = _packet()
    projection = packet.semantic_content_coverage_ref_projection

    manifest = packet.semantic_evidence_authority_manifest

    assert manifest["available"] is True
    assert manifest["content_refs_available"] is True
    assert manifest["coverage_refs_available"] is True
    assert "deferred_ref_fields" not in manifest
    assert manifest["semantic_content_coverage_ref_projection_schema_version"] == (
        projection["schema_version"]
    )
    assert manifest["source_projection_digest"] == projection[
        "source_projection_digest"
    ]
    assert manifest["component_ref_count"] == len(projection["component_refs"])
    assert manifest["coverage_record_ref_count"] == len(
        projection["coverage_record_refs"]
    )
    assert manifest["semantic_observation_ref_count"] == len(
        projection["semantic_observation_refs"]
    )
    assert manifest["sanitized_content_ref_count"] == len(
        projection["sanitized_content_ref_ids"]
    )
    assert manifest["content_ref_digest_count"] == len(
        projection["content_ref_digests"]
    )
    assert manifest["semantic_ref_evidence_id_count"] == len(
        projection["semantic_ref_evidence_ids"]
    )
    assert manifest["semantic_source_ref_binding_count"] == len(
        projection["semantic_source_ref_bindings"]
    )
    assert manifest["author_materialization_content_ref_count"] == len(
        projection["author_materialization_content_refs"]
    )
    assert manifest["author_materialization_content_ref_digest"] == _stable_safe_digest(
        projection["author_materialization_content_refs"]
    )
    assert manifest["source_obligation_ref_count"] == len(
        projection["source_obligation_refs"]
    )
    assert manifest["evidence_ids"] == [packet.evidence_allowed[0].evidence_id]
    assert manifest["semantic_packet_evidence_binding_available"] is True
    assert manifest["semantic_packet_evidence_binding_count"] == 1
    assert manifest["semantic_packet_evidence_binding_digest"]
    assert "semantic_packet_evidence_bindings" not in manifest
    assert manifest["citation_source_ids"] == [101]
    assert manifest["raw_content_included"] is False
    assert manifest["bounded_text_included"] is False
    assert manifest["prompt_visible"] is False
    assert manifest["author_payload_visible"] is False
    assert manifest["author_payload_ref_envelope_available"] is True
    assert manifest["model_request_visible"] is False
    assert manifest["final_text_included"] is False
    for full_ref_key in (
        "component_refs",
        "coverage_record_refs",
        "coverage_record_ids",
        "coverage_record_digests",
        "semantic_observation_refs",
        "sanitized_content_ref_ids",
        "content_ref_digests",
        "semantic_ref_evidence_ids",
        "semantic_source_ref_bindings",
        "source_obligation_refs",
        "author_materialization_content_refs",
    ):
        assert full_ref_key not in manifest


@pytest.mark.parametrize(
    "semantic_ref_projection",
    [
        None,
        _semantic_ref_projection(available=False),
        _semantic_ref_projection(content_refs_available=False),
        _semantic_ref_projection(coverage_refs_available=False),
        _semantic_ref_projection(schema_version="unexpected_schema"),
    ],
)
def test_unavailable_sufficiency_projection_preserves_deferred_manifest_behavior(
    semantic_ref_projection: Mapping[str, Any] | None,
) -> None:
    packet = build_final_answer_packet(
        run_id="ag-sem-fap-01-negative",
        final_evidence=[_passage()],
        author_evidence=[_passage()],
        sufficiency_judgment_projection=_sufficiency_projection(
            semantic_ref_projection
        ),
    )

    assert packet.semantic_content_coverage_ref_projection == {}
    manifest = packet.semantic_evidence_authority_manifest
    assert manifest["content_refs_available"] is False
    assert manifest["coverage_refs_available"] is False
    assert manifest["deferred_ref_fields"] == [
        "sanitized_content_ref_ids",
        "content_ref_digests",
        "coverage_record_ids",
        "coverage_record_digests",
    ]
    assert "sanitized_content_ref_ids" not in manifest
    assert "content_ref_digests" not in manifest
    assert "coverage_record_refs" not in manifest
    assert "semantic_observation_refs" not in manifest


def test_fap_projection_adds_controlled_context_without_changing_citation_surfaces() -> None:
    packet = _packet()
    packet_without_projection = replace(
        packet,
        semantic_content_coverage_ref_projection={},
    )

    payload = packet.to_author_input_payload(
        prompt="unchanged author prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )
    payload_without_projection = packet_without_projection.to_author_input_payload(
        prompt="unchanged author prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert payload.prompt != payload_without_projection.prompt
    assert "CONTROLLED SEMANTIC CONTEXT" in payload.prompt
    assert "CONTROLLED SEMANTIC CONTEXT" in payload.authority_block
    assert "CONTROLLED SEMANTIC CONTEXT" not in payload_without_projection.prompt
    assert payload.authority_payload == payload_without_projection.authority_payload
    assert payload.authority_block != payload_without_projection.authority_block
    assert payload.semantic_content_coverage_ref_envelope
    assert payload_without_projection.semantic_content_coverage_ref_envelope == {}
    assert packet.citation_records == packet_without_projection.citation_records
    assert packet.source_obligations == packet_without_projection.source_obligations
    assert packet.to_authority_payload(
        citation_source_ids=payload.citation_source_ids,
        citation_ineligible_refs=payload.citation_ineligible_refs,
        missing_source_obligations=payload.missing_source_obligations,
        partial_source_obligations=payload.partial_source_obligations,
        satisfied_source_obligations=payload.satisfied_source_obligations,
    ) == packet_without_projection.to_authority_payload(
        citation_source_ids=payload_without_projection.citation_source_ids,
        citation_ineligible_refs=payload_without_projection.citation_ineligible_refs,
        missing_source_obligations=(
            payload_without_projection.missing_source_obligations
        ),
        partial_source_obligations=(
            payload_without_projection.partial_source_obligations
        ),
        satisfied_source_obligations=(
            payload_without_projection.satisfied_source_obligations
        ),
    )


def test_author_manifest_trace_ref_exposes_only_digest_and_availability() -> None:
    packet = _packet()
    payload = packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )

    trace_ref = payload.to_trace_ref()[
        "semantic_evidence_authority_manifest_trace_ref"
    ]

    assert trace_ref["content_refs_available"] is True
    assert trace_ref["coverage_refs_available"] is True
    assert trace_ref["semantic_evidence_authority_manifest_digest"]
    for key in (
        "sanitized_content_ref_ids",
        "content_ref_digests",
        "coverage_record_refs",
        "coverage_record_digests",
        "semantic_observation_refs",
        "component_refs",
        "semantic_ref_evidence_ids",
        "source_obligation_refs",
    ):
        assert key not in trace_ref


def test_fap_projection_raw_leakage_scan() -> None:
    tainted_projection = _semantic_ref_projection(
        raw_content="SENTINEL_RAW_CONTENT",
        bounded_text="SENTINEL_BOUNDED_TEXT",
        raw_source_text="SENTINEL_RAW_SOURCE_TEXT",
        text_excerpts=["SENTINEL_TEXT_EXCERPT"],
        prompt_text="SENTINEL_PROMPT_TEXT",
        raw_prompt="SENTINEL_RAW_PROMPT",
        provider_payload={"private_marker": "SENTINEL_PROVIDER_PAYLOAD"},
        raw_provider_payload={"private_marker": "SENTINEL_RAW_PROVIDER_PAYLOAD"},
        model_response="SENTINEL_MODEL_RESPONSE",
        raw_model_response="SENTINEL_RAW_MODEL_RESPONSE",
        final_prose="SENTINEL_FINAL_PROSE",
        final_text="SENTINEL_FINAL_TEXT",
        db_row={"private_marker": "SENTINEL_DB_ROW"},
        cache={"private_marker": "SENTINEL_CACHE"},
        full_trace={"private_marker": "SENTINEL_FULL_TRACE"},
        logs=["SENTINEL_LOGS"],
    )
    packet = _packet(tainted_projection)
    payload = packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )
    scanned = (
        packet.semantic_content_coverage_ref_projection,
        packet.semantic_evidence_authority_manifest,
        payload.semantic_content_coverage_ref_envelope,
        payload.to_trace_ref(),
    )
    encoded = json.dumps(scanned, sort_keys=True)
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
    ):
        assert forbidden not in encoded

    forbidden_keys = {
        "raw_content",
        "bounded_text",
        "raw_source_text",
        "text_excerpts",
        "prompt_text",
        "raw_prompt",
        "provider_payload",
        "raw_provider_payload",
        "model_response",
        "raw_model_response",
        "final_prose",
        "final_text",
        "db_row",
        "cache",
        "secret",
        "token",
        "full_trace",
        "logs",
    }
    exported_scanned = (
        packet.to_dict()["semantic_content_coverage_ref_projection"],
        packet.semantic_evidence_authority_manifest,
        payload.semantic_content_coverage_ref_envelope,
        payload.to_trace_ref(),
    )
    for item in exported_scanned:
        assert _walk_keys(item).isdisjoint(forbidden_keys)
    assert "author_materialization_content_refs" not in _walk_keys(
        packet.to_dict()["semantic_content_coverage_ref_projection"]
    )
    assert "author_materialization_content_refs" not in _walk_keys(
        packet.semantic_evidence_authority_manifest
    )
    assert "author_materialization_content_refs" not in _walk_keys(
        payload.semantic_content_coverage_ref_envelope
    )
    assert "author_materialization_content_refs" not in _walk_keys(
        payload.to_trace_ref()
    )


def test_static_guards_keep_fap_projection_out_of_closed_surfaces() -> None:
    packet_source = PACKET.read_text(encoding="utf-8")
    adapter_source = ADAPTER.read_text(encoding="utf-8")
    prompt_assembly = PROMPT_ASSEMBLY.read_text(encoding="utf-8")

    assert "semantic_observation_admission_history" not in packet_source
    assert "component_coverage_history" not in packet_source
    assert "semantic_observation_admission_history" not in adapter_source
    assert "component_coverage_history" not in adapter_source
    assert "semantic_content_coverage_ref_projection" not in prompt_assembly
    assert "semantic_content_coverage_ref_envelope" not in prompt_assembly
    assert "semantic_ref_projection" not in prompt_assembly

    for path in (
        ROOT / "core" / "retrieval.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "search_providers.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "semantic_content_coverage_ref_projection" not in source
        assert "semantic_content_coverage_ref_envelope" not in source

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
