from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.fetch_read_content_reference import (
    FETCH_READ_CONTENT_PACKET_OWNER,
    FETCH_READ_CONTENT_PACKET_POSTURE,
    FETCH_READ_CONTENT_PACKET_SCHEMA_VERSION,
    SANITIZED_CONTENT_REFERENCE_SCHEMA_VERSION,
    FetchReadContentReferenceError,
    build_fetch_read_content_packet_from_candidate_packet,
    fetch_read_content_packet_ref_from_packet,
    reduce_candidate_packet_and_sanitized_reads_to_fetch_read_packet,
    validate_fetch_read_content_packet,
)
from core.search_result_candidate_packet import SearchResultCandidatePacketError
from tests.test_ag_search_result_candidate_packet_01 import _packet_from_state

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "fetch_read_content_reference.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
)

FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_page_content_retained": False,
    "raw_page_text_retained": False,
    "raw_headers_retained": False,
    "raw_prompt_retained": False,
    "evidence_ledger_admitted": False,
    "citation_created": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "semantic_observation_created": False,
    "analyst_report_created": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
}

TRUE_POSTURE_FLAGS = {
    "closed_surface": True,
    "non_evidence": True,
    "not_evidence_ledger_custody": True,
    "not_semantic_support": True,
    "not_citation_eligible": True,
    "not_source_obligation_satisfaction": True,
    "not_sufficient": True,
    "not_final_answer_material": True,
    "not_author_input": True,
}


def _readable_material(
    packet: Mapping[str, Any],
    *,
    index: int = 0,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = packet["candidate_records"][index]
    bounded_text = "Bounded sanitized excerpt about the permit threshold."
    material = {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "run_id": packet["run_id"],
        "request_id": packet["request_id"],
        "current_answer_contract_digest": packet["current_answer_contract_digest"],
        "search_executor_handoff_digest": packet["search_executor_handoff_digest"],
        "search_result_candidate_packet_id": packet["packet_id"],
        "search_result_candidate_packet_digest": packet["packet_digest"],
        "fetch_read_status": "readable",
        "attempted_url": candidate["url"],
        "resolved_url": candidate["url"],
        "resolved_domain": candidate["domain"],
        "content_type": "text/html",
        "http_status": 200,
        "retrieved_or_observed_at": "2026-06-28T00:00:00Z",
        "published_or_observed_date": "2026-01-01",
        "content_title": "Official Example Permit Threshold",
        "bounded_text": bounded_text,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_text_char_count": len(bounded_text),
        "raw_page_content_retained": False,
        "raw_headers_retained": False,
    }
    if extra:
        material.update(extra)
    return material


def _failed_material(
    packet: Mapping[str, Any],
    *,
    index: int = 0,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = packet["candidate_records"][index]
    material = {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "fetch_read_status": "failed",
        "attempted_url": candidate["url"],
        "resolved_domain": candidate["domain"],
        "read_error_code": "timeout",
        "failure_reason": "timeout",
        "raw_page_content_retained": False,
        "raw_headers_retained": False,
    }
    if extra:
        material.update(extra)
    return material


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(_text(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()


def test_fetch_read_content_packet_builds_bounded_non_evidence_references() -> None:
    _, candidate_packet = _packet_from_state()

    packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        [_readable_material(candidate_packet)],
    )

    candidate = candidate_packet["candidate_records"][0]
    reference = packet["reference_records"][0]
    assert packet["owner"] == FETCH_READ_CONTENT_PACKET_OWNER
    assert packet["schema_version"] == FETCH_READ_CONTENT_PACKET_SCHEMA_VERSION
    assert packet["packet_posture"] == FETCH_READ_CONTENT_PACKET_POSTURE
    assert packet["run_id"] == candidate_packet["run_id"]
    assert packet["request_id"] == candidate_packet["request_id"]
    assert packet["current_answer_contract_digest"] == (
        candidate_packet["current_answer_contract_digest"]
    )
    assert packet["search_executor_handoff_digest"] == (
        candidate_packet["search_executor_handoff_digest"]
    )
    assert packet["search_result_candidate_packet_ref"]["packet_id"] == (
        candidate_packet["packet_id"]
    )
    assert packet["search_result_candidate_packet_digest"] == (
        candidate_packet["packet_digest"]
    )
    assert packet["selected_candidate_ids"] == [candidate["candidate_id"]]
    assert packet["reference_count"] == 1

    assert reference["schema_version"] == SANITIZED_CONTENT_REFERENCE_SCHEMA_VERSION
    assert reference["candidate_id"] == candidate["candidate_id"]
    assert reference["candidate_digest"] == candidate["candidate_digest"]
    assert reference["search_task_id"] == candidate["search_task_id"]
    assert reference["query_intent_id"] == candidate["query_intent_id"]
    assert reference["component_id"] == candidate["component_id"]
    assert reference["source_obligation_candidate_ids"] == (
        candidate["source_obligation_candidate_ids"]
    )
    assert reference["candidate_title"] == candidate["title"]
    assert reference["candidate_url"] == candidate["url"]
    assert reference["candidate_domain"] == candidate["domain"]
    assert reference["fetch_read_status"] == "readable"
    assert reference["bounded_text"] == (
        "Bounded sanitized excerpt about the permit threshold."
    )
    assert reference["bounded_character_count"] == len(reference["bounded_text"])
    assert reference["excerpt_digest"]

    for key, expected in FALSE_FLAGS.items():
        assert packet[key] is expected
        assert reference[key] is expected
    for key, expected in TRUE_POSTURE_FLAGS.items():
        assert packet[key] is expected
        assert reference[key] is expected

    compact_ref = fetch_read_content_packet_ref_from_packet(packet)
    assert compact_ref["packet_id"] == packet["packet_id"]
    assert compact_ref["packet_digest"] == packet["packet_digest"]
    assert compact_ref["reference_count"] == 1


def test_fetch_read_content_packet_ids_and_digests_are_stable() -> None:
    _, candidate_packet = _packet_from_state()
    materials = [_readable_material(candidate_packet)]

    packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        materials,
    )
    rebuilt = validate_fetch_read_content_packet(deepcopy(packet))
    reduced = reduce_candidate_packet_and_sanitized_reads_to_fetch_read_packet(
        candidate_packet,
        materials,
    )

    assert rebuilt["packet_id"] == packet["packet_id"]
    assert rebuilt["packet_digest"] == packet["packet_digest"]
    assert rebuilt["reference_records"][0]["reference_digest"] == (
        packet["reference_records"][0]["reference_digest"]
    )
    assert reduced["packet_id"] == packet["packet_id"]
    assert reduced["packet_digest"] == packet["packet_digest"]


def test_fetch_read_content_packet_rejects_absent_duplicate_and_stale_candidates() -> None:
    _, candidate_packet = _packet_from_state(candidate_count=2)

    absent = _readable_material(candidate_packet)
    absent["candidate_id"] = "search-result-candidate:missing"
    with pytest.raises(FetchReadContentReferenceError, match="not bound"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [absent],
        )

    stale = _readable_material(candidate_packet)
    stale["candidate_digest"] = "0" * 64
    with pytest.raises(FetchReadContentReferenceError, match="candidate_digest"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [stale],
        )

    duplicate = [
        _readable_material(candidate_packet),
        _readable_material(candidate_packet),
    ]
    with pytest.raises(FetchReadContentReferenceError, match="unique"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            duplicate,
        )


def test_fetch_read_content_packet_rejects_lineage_and_url_domain_mismatch() -> None:
    _, candidate_packet = _packet_from_state()

    wrong_lineage = _readable_material(
        candidate_packet,
        extra={"search_executor_handoff_digest": "0" * 64},
    )
    with pytest.raises(FetchReadContentReferenceError, match="handoff_digest"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [wrong_lineage],
        )

    wrong_url = _readable_material(
        candidate_packet,
        extra={"attempted_url": "https://official.example.gov/other-path"},
    )
    with pytest.raises(FetchReadContentReferenceError, match="attempted_url"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [wrong_url],
        )

    wrong_domain = _readable_material(
        candidate_packet,
        extra={"resolved_domain": "other.example.gov"},
    )
    with pytest.raises(FetchReadContentReferenceError, match="resolved_domain"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [wrong_domain],
        )


def test_fetch_read_content_packet_rejects_tampered_candidate_packet() -> None:
    _, candidate_packet = _packet_from_state()
    tampered = deepcopy(candidate_packet)
    tampered["candidate_records"][0]["title"] = "Tampered title"

    with pytest.raises(SearchResultCandidatePacketError, match="digest"):
        build_fetch_read_content_packet_from_candidate_packet(
            tampered,
            [_readable_material(candidate_packet)],
        )


def test_fetch_read_content_packet_rejects_raw_private_and_authority_material() -> None:
    _, candidate_packet = _packet_from_state()

    raw = _readable_material(
        candidate_packet,
        extra={"headers": {"authorization": "Bearer private"}},
    )
    with pytest.raises(FetchReadContentReferenceError, match="raw/private"):
        build_fetch_read_content_packet_from_candidate_packet(candidate_packet, [raw])

    raw_page = _readable_material(
        candidate_packet,
        extra={"raw_page_content": "<html>raw</html>"},
    )
    with pytest.raises(FetchReadContentReferenceError, match="raw/private"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [raw_page],
        )

    authority = _readable_material(
        candidate_packet,
        extra={"citations": ["https://official.example.gov/permit/threshold-1"]},
    )
    with pytest.raises(FetchReadContentReferenceError, match="closed authority"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [authority],
        )

    dangerous = _readable_material(
        candidate_packet,
        extra={"citation_eligible": True},
    )
    with pytest.raises(FetchReadContentReferenceError, match="closed runtime"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [dangerous],
        )


def test_fetch_read_content_packet_rejects_unbounded_content() -> None:
    _, candidate_packet = _packet_from_state()

    unbounded_key = _readable_material(
        candidate_packet,
        extra={"unbounded_text": "raw body text"},
    )
    with pytest.raises(FetchReadContentReferenceError, match="raw/private"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [unbounded_key],
        )

    missing_markers = _readable_material(candidate_packet)
    missing_markers.pop("bounded_text_sanitized")
    missing_markers.pop("bounded_text_bounded")
    missing_markers.pop("bounded_text_char_count")
    with pytest.raises(FetchReadContentReferenceError, match="sanitized and bounded"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [missing_markers],
        )

    too_long = _readable_material(
        candidate_packet,
        extra={
            "bounded_text": "x" * 2001,
            "bounded_text_char_count": 2001,
        },
    )
    with pytest.raises(FetchReadContentReferenceError, match="exceeds"):
        build_fetch_read_content_packet_from_candidate_packet(
            candidate_packet,
            [too_long],
        )


def test_fetch_read_content_packet_preserves_failed_read_posture() -> None:
    _, candidate_packet = _packet_from_state()

    packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        [_failed_material(candidate_packet)],
    )

    reference = packet["reference_records"][0]
    assert reference["fetch_read_status"] == "failed"
    assert reference["read_error_code"] == "timeout"
    assert reference["failure_reason"] == "timeout"
    assert "bounded_text" not in reference
    assert reference["non_evidence"] is True
    assert reference["not_citation_eligible"] is True
    assert reference["evidence_ledger_admitted"] is False
    assert reference["citation_created"] is False
    assert reference["source_obligation_satisfied"] is False


def test_fetch_read_content_packet_contains_no_forbidden_material() -> None:
    _, candidate_packet = _packet_from_state()
    packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        [_readable_material(candidate_packet)],
    )

    forbidden_keys = {
        "raw_provider_payload",
        "raw_search_response",
        "api_key",
        "auth_headers",
        "headers",
        "private_logs",
        "raw_prompt",
        "model_response",
        "full_trace",
        "db_row",
        "raw_page_content",
        "raw_headers",
        "unbounded_text",
        "evidence",
        "citations",
        "final_answer_packet",
        "author_input",
    }
    assert _all_keys(packet).isdisjoint(forbidden_keys)


def test_fetch_read_content_packet_static_closed_surface_guard() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.evidence_ledger",
        "core.evidence_ledger_admission_runtime",
        "core.semantic_observation_foundation",
        "core.semantic_observation_admission_runtime",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "core.citations",
        "dotenv",
        "openai",
        "requests",
        "httpx",
    }
    assert _imports(RUNTIME_MODULE).isdisjoint(forbidden_imports)
    source = _text(RUNTIME_MODULE)
    for token in (
        "SERPER_API_KEY",
        "requests.",
        "httpx.",
        "openai.",
        "urlopen(",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "fetch_linkup_precision_block",
        "execute_author_action(",
        "build_citation",
        "EvidenceLedger(",
        "SemanticObservation(",
        "FinalAnswerPacket(",
    ):
        assert token not in source, token

    assert _text(PIPELINE)


def test_docs_record_fetch_read_content_reference_posture() -> None:
    required = (
        "FetchReadContentPacket",
        "SanitizedContentReference",
        "bounded readable-content handoff",
        "after SearchResultCandidatePacket",
        "before EvidenceLedger custody",
        "not evidence",
        "not citation-eligible",
        "does not satisfy source obligations",
    )
    for path in DOCS:
        text = " ".join(_text(path).replace("`", "").split())
        for needle in required:
            assert needle in text, (path, needle)
