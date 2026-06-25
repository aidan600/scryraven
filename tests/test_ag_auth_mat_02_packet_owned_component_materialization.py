from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from core.final_answer_packet import (
    FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION,
    FINAL_ANSWER_PACKET_SEMANTIC_PACKET_EVIDENCE_BINDING_SCHEMA_VERSION,
    CitationEligibilityRecord,
    CitationEligibilityStatus,
    EvidenceAuthorityStatus,
    FinalAnswerPacket,
    FinalAnswerReadinessStatus,
    FinalEvidenceRecord,
    semantic_packet_evidence_binding_digest,
)
from core.semantic_observation_foundation import (
    ContentKind,
    SanitizedContentReference,
)

COMPONENT_ID = "component:answer-bearing-rule"
COMPONENT_DIGEST = "c" * 64
CONTRACT_VERSION = "accepted-v1"
CONTRACT_DIGEST = "a" * 64
COVERAGE_ID = "coverage:answer-bearing-rule"
COVERAGE_DIGEST = "b" * 64
ORIGIN_EVIDENCE_ID = "evidence:official-rule"
PACKET_EVIDENCE_ID = "packet-e1"
CONTENT_REF_ID = f"content:{COMPONENT_ID}:{ORIGIN_EVIDENCE_ID}"
BOUNDED_TEXT = "Official rule says the covered value is 42 units."


def _content_digest(text: str = BOUNDED_TEXT) -> str:
    return SanitizedContentReference(
        content_ref_id=CONTENT_REF_ID,
        evidence_ref_id=ORIGIN_EVIDENCE_ID,
        admitted_evidence_ref=ORIGIN_EVIDENCE_ID,
        answer_component_id=COMPONENT_ID,
        component_contract_digest=COMPONENT_DIGEST,
        content_kind=ContentKind.BOUNDED_EXCERPT,
        bounded_text=text,
    ).content_digest


def _binding() -> dict[str, Any]:
    row = {
        "schema_version": (
            FINAL_ANSWER_PACKET_SEMANTIC_PACKET_EVIDENCE_BINDING_SCHEMA_VERSION
        ),
        "origin_evidence_ref_id": ORIGIN_EVIDENCE_ID,
        "origin_evidence_ref_kind": "evidence_ledger_candidate",
        "packet_evidence_id": PACKET_EVIDENCE_ID,
        "content_ref_id": CONTENT_REF_ID,
        "content_digest": _content_digest(),
        "coverage_record_id": COVERAGE_ID,
        "coverage_record_digest": COVERAGE_DIGEST,
        "component_id": COMPONENT_ID,
        "component_digest": COMPONENT_DIGEST,
    }
    row["binding_digest"] = semantic_packet_evidence_binding_digest(row)
    return row


def _material_ref(**overrides: Any) -> dict[str, Any]:
    row = {
        "content_ref_id": CONTENT_REF_ID,
        "content_digest": _content_digest(),
        "evidence_ref_id": ORIGIN_EVIDENCE_ID,
        "admitted_evidence_ref": ORIGIN_EVIDENCE_ID,
        "origin_evidence_ref_id": ORIGIN_EVIDENCE_ID,
        "origin_evidence_ref_kind": "evidence_ledger_candidate",
        "packet_evidence_id": PACKET_EVIDENCE_ID,
        "answer_component_id": COMPONENT_ID,
        "component_id": COMPONENT_ID,
        "component_digest": COMPONENT_DIGEST,
        "component_contract_digest": COMPONENT_DIGEST,
        "accepted_contract_version": CONTRACT_VERSION,
        "accepted_contract_digest": CONTRACT_DIGEST,
        "coverage_record_id": COVERAGE_ID,
        "coverage_record_digest": COVERAGE_DIGEST,
        "content_kind": "bounded_excerpt",
        "bounded_text": BOUNDED_TEXT,
        "source_id": 1,
        "citation_eligibility_posture": "packet_evidence_pending",
        "sanitized": True,
        "bounded": True,
        "raw_content_retained": False,
        "raw_provider_payload_retained": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "private_logs_retained": False,
        "db_cache_rows_retained": False,
        "full_trace_retained": False,
        "secrets_returned": False,
        "raw_content_included": False,
        "raw_prompt_included": False,
        "provider_payload_included": False,
        "final_text_included": False,
        "trace_only": True,
        "accepted_authority": False,
    }
    row.update(overrides)
    return row


def _projection(material_refs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema_version": (
            FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION
        ),
        "available": True,
        "source_authority": "RunAuthoritySufficiency.semantic_ref_projection",
        "source_schema_version": "sufficiency_semantic_ref_projection_ag_sem_proj_01_v1",
        "source_projection_digest": "d" * 64,
        "semantic_state_facts_digest": "e" * 64,
        "accepted_contract_version": CONTRACT_VERSION,
        "accepted_contract_digest": CONTRACT_DIGEST,
        "component_refs": [
            {"component_id": COMPONENT_ID, "component_digest": COMPONENT_DIGEST}
        ],
        "coverage_record_refs": [
            {
                "coverage_record_id": COVERAGE_ID,
                "coverage_record_digest": COVERAGE_DIGEST,
                "answer_component_id": COMPONENT_ID,
            }
        ],
        "semantic_observation_refs": [
            {"observation_id": "observation:rule", "observation_digest": "f" * 64}
        ],
        "sanitized_content_ref_ids": [CONTENT_REF_ID],
        "content_ref_digests": [_content_digest()],
        "semantic_ref_evidence_ids": [ORIGIN_EVIDENCE_ID],
        "semantic_source_ref_bindings": [
            {
                "origin_evidence_ref_id": ORIGIN_EVIDENCE_ID,
                "origin_evidence_ref_kind": "evidence_ledger_candidate",
                "content_ref_id": CONTENT_REF_ID,
                "content_digest": _content_digest(),
                "coverage_record_id": COVERAGE_ID,
                "coverage_record_digest": COVERAGE_DIGEST,
                "component_id": COMPONENT_ID,
                "component_digest": COMPONENT_DIGEST,
            }
        ],
        "author_materialization_content_refs": (
            [_material_ref()] if material_refs is None else material_refs
        ),
        "content_refs_available": True,
        "coverage_refs_available": True,
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }


def _packet(
    *,
    material_refs: list[dict[str, Any]] | None = None,
    citation_status: CitationEligibilityStatus = CitationEligibilityStatus.CITATION_ELIGIBLE,
    readiness_status: FinalAnswerReadinessStatus = FinalAnswerReadinessStatus.AUTHOR_READY,
) -> FinalAnswerPacket:
    return FinalAnswerPacket(
        packet_id="packet-ag-auth-mat-02",
        evidence_records=(
            FinalEvidenceRecord(
                evidence_id=PACKET_EVIDENCE_ID,
                status=EvidenceAuthorityStatus.EVIDENCE_ALLOWED,
                position=1,
                source_id=1,
                url="https://official.example/rule",
                title="Official rule",
                source_tier="official",
                source_class="official_current_rules",
                origin_evidence_ref_id=ORIGIN_EVIDENCE_ID,
                origin_evidence_ref_kind="evidence_ledger_candidate",
            ),
        ),
        citation_records=(
            CitationEligibilityRecord(
                citation_id=f"{PACKET_EVIDENCE_ID}:citation",
                evidence_id=PACKET_EVIDENCE_ID,
                status=citation_status,
                source_id=1,
                reason=(
                    "source_id_missing"
                    if citation_status is CitationEligibilityStatus.CITATION_INELIGIBLE
                    else None
                ),
            ),
        ),
        mandatory_caveats=("Preserve the official-rule caveat.",),
        prohibited_upgrades=("Do not replace packet evidence with an estimate.",),
        readiness_status=readiness_status,
        semantic_content_coverage_ref_projection=_projection(material_refs),
        semantic_packet_evidence_bindings=(_binding(),),
    )


def _payload(packet: FinalAnswerPacket):
    return packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )


def test_packet_owned_bounded_material_is_prompt_visible_and_trace_accounted() -> None:
    payload = _payload(_packet())
    trace_ref = payload.to_trace_ref()["semantic_author_materialization_trace_ref"]
    prompt = payload.prompt

    assert "Packet-owned bounded support 1" in prompt
    assert BOUNDED_TEXT in prompt
    assert "does not add citation authority" in prompt
    assert "Preserve the official-rule caveat." in prompt
    assert "Do not replace packet evidence with an estimate." in prompt
    assert trace_ref["bounded_text_included"] is True
    assert trace_ref["bounded_material_complete"] is True
    assert trace_ref["bounded_material_component_count"] == 1
    assert trace_ref["bounded_material_digest"]
    assert trace_ref["accepted_contract_digest"] == CONTRACT_DIGEST
    assert trace_ref["bounded_text_retained"] is False
    assert trace_ref["raw_content_included"] is False
    assert trace_ref["raw_prompt_retained"] is False
    assert trace_ref["provider_payload_retained"] is False
    assert "bounded_material_refs" not in trace_ref


@pytest.mark.parametrize(
    ("mutator", "reason"),
    (
        (
            lambda row: row.update(component_digest="wrong-component-digest"),
            "bounded_excerpt_component_digest_mismatch",
        ),
        (
            lambda row: row.update(accepted_contract_digest="wrong-contract-digest"),
            "bounded_excerpt_contract_digest_mismatch",
        ),
        (
            lambda row: row.update(packet_evidence_id="packet-e2"),
            "bounded_excerpt_packet_evidence_mismatch",
        ),
        (
            lambda row: row.update(content_digest="wrong-content-digest"),
            "bounded_excerpt_digest_mismatch",
        ),
    ),
)
def test_bounded_material_identity_mismatches_fail_closed(
    mutator: Any,
    reason: str,
) -> None:
    material = _material_ref()
    mutator(material)
    payload = _payload(_packet(material_refs=[material]))
    trace_ref = payload.to_trace_ref()["semantic_author_materialization_trace_ref"]

    assert BOUNDED_TEXT not in payload.prompt
    assert "Packet-owned bounded support" not in payload.prompt
    assert trace_ref["bounded_text_included"] is False
    assert trace_ref["bounded_material_complete"] is False
    assert trace_ref["unavailable_reason"] == reason


def test_material_not_bound_to_packet_evidence_is_not_prompt_visible() -> None:
    material = _material_ref(content_ref_id="content:unbound")
    payload = _payload(_packet(material_refs=[material]))
    trace_ref = payload.to_trace_ref()["semantic_author_materialization_trace_ref"]

    assert BOUNDED_TEXT not in payload.prompt
    assert trace_ref["bounded_text_included"] is False
    assert trace_ref["unavailable_reason"] == "bounded_excerpt_unbound_to_packet_evidence"


def test_citation_ineligible_packet_evidence_is_not_materialized() -> None:
    payload = _payload(
        _packet(citation_status=CitationEligibilityStatus.CITATION_INELIGIBLE)
    )
    trace_ref = payload.to_trace_ref()["semantic_author_materialization_trace_ref"]

    assert BOUNDED_TEXT not in payload.prompt
    assert trace_ref["bounded_text_included"] is False
    assert trace_ref["unavailable_reason"] == (
        "bounded_excerpt_evidence_not_citation_eligible"
    )


def test_missing_material_does_not_become_authoritative_empty_material() -> None:
    payload = _payload(_packet(material_refs=[]))
    trace_ref = payload.to_trace_ref()["semantic_author_materialization_trace_ref"]

    assert "CONTROLLED SEMANTIC CONTEXT" in payload.prompt
    assert BOUNDED_TEXT not in payload.prompt
    assert trace_ref["bounded_text_included"] is False
    assert trace_ref["bounded_material_component_count"] == 0
    assert trace_ref["bounded_material_complete"] is False
    assert trace_ref["unavailable_reason"] == "bounded_excerpt_not_packet_owned"


def test_blocked_packet_cannot_materialize_missing_component_to_author() -> None:
    packet = _packet(readiness_status=FinalAnswerReadinessStatus.BLOCKED)
    blocked = deepcopy(packet)

    with pytest.raises(ValueError, match="blocked FinalAnswerPacket"):
        _payload(blocked)
