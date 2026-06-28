from __future__ import annotations

import ast
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.live_search_validation_invocation_runtime import (
    LiveSearchValidationCaps,
    build_live_search_validation_request_packet,
    build_output_packet,
)
from core.search_result_candidate_packet import (
    SEARCH_RESULT_CANDIDATE_PACKET_OWNER,
    SEARCH_RESULT_CANDIDATE_PACKET_POSTURE,
    SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION,
    SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION,
    SearchResultCandidatePacketError,
    build_search_result_candidate_packet_from_live_search_validation_output,
    build_search_result_candidate_packet_from_live_validation_state,
    reduce_live_search_validation_candidates_to_packet,
    search_result_candidate_packet_ref_from_packet,
    validate_search_result_candidate_packet,
)
from tests.test_ag_live_xaxis_validation_01a import (
    _authorize_validation,
    _fake_results,
    _ready_kernel,
    _reduce_validation,
    _selected_task_ids,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "search_result_candidate_packet.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
    ROOT / "docs" / "codex" / "AG_LIVE_PLAN_01_BOUNDED_LIVE_VALIDATION_PLAN.md",
)

FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "fetched_content_included": False,
    "fetch_read_executed": False,
    "fetch_read_retrieval_executed": False,
    "read_executed": False,
    "evidence_ledger_admitted": False,
    "evidence_created": False,
    "citation_eligible": False,
    "citation_created": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
}

TRUE_POSTURE_FLAGS = {
    "closed_surface": True,
    "non_evidence": True,
    "not_fetched": True,
    "not_read": True,
    "not_citation": True,
    "not_citation_eligible": True,
    "not_sufficient": True,
    "not_source_obligation_satisfaction": True,
}


def _packet_from_state(*, candidate_count: int = 2) -> tuple[Any, dict[str, Any]]:
    kernel = _ready_kernel()
    _reduce_validation(kernel, results=_fake_results(kernel, count=candidate_count))
    packet = build_search_result_candidate_packet_from_live_validation_state(
        kernel.state.live_search_validation_state
    )
    return kernel, packet


def _live_run_01_output_packet() -> dict[str, Any]:
    kernel = _ready_kernel()
    selected = _selected_task_ids(kernel)
    action = _authorize_validation(kernel, selected=selected)
    _reduce_validation(
        kernel,
        action=action,
        results=_fake_results(kernel, count=2),
    )
    request_packet = build_live_search_validation_request_packet(
        current_answer_contract=kernel.state.current_answer_contract,
        search_executor_handoff_state=kernel.state.search_executor_handoff_state,
        selected_search_task_ids=selected,
        provider_authorized="serper",
        output_packet_path="output/ag_search_result_candidate_packet_01.json",
        root=ROOT,
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        caps=LiveSearchValidationCaps(),
    )
    return build_output_packet(
        request_packet=request_packet,
        validation_state=kernel.state.live_search_validation_state,
        budget_exhausted=False,
        decision_made_by_run="search_result_candidates_reduced",
    )


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


def test_search_result_candidate_packet_builds_durable_non_evidence_records() -> None:
    kernel, packet = _packet_from_state()

    assert packet["owner"] == SEARCH_RESULT_CANDIDATE_PACKET_OWNER
    assert packet["schema_version"] == SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION
    assert packet["packet_posture"] == SEARCH_RESULT_CANDIDATE_PACKET_POSTURE
    assert packet["run_id"] == kernel.state.run_id
    assert packet["request_id"] == kernel.state.request_id
    assert packet["current_answer_contract_digest"] == (
        kernel.state.current_answer_contract["accepted_contract_digest"]
    )
    assert packet["search_executor_handoff_digest"] == (
        kernel.state.search_executor_handoff_state["handoff_digest"]
    )
    assert packet["parent_live_search_validation_ref"]["validation_id"] == (
        kernel.state.live_search_validation_state["validation_id"]
    )
    assert packet["parent_live_search_validation_ref"]["validation_digest"] == (
        kernel.state.live_search_validation_state["validation_digest"]
    )
    assert packet["selected_search_task_ids"] == _selected_task_ids(kernel)
    assert packet["candidate_count"] == 2

    source_candidate = kernel.state.live_search_validation_state[
        "search_result_candidates"
    ][0]
    record = packet["candidate_records"][0]
    assert record["schema_version"] == SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION
    assert record["candidate_id"] == source_candidate["candidate_id"]
    assert record["candidate_digest"] == source_candidate["candidate_digest"]
    assert record["search_task_id"] == source_candidate["search_task_id"]
    assert record["query_intent_id"] == source_candidate["query_intent_id"]
    assert record["component_id"] == source_candidate["component_id"]
    assert record["source_obligation_candidate_ids"] == (
        source_candidate["source_obligation_candidate_ids"]
    )
    assert record["title"] == source_candidate["title"]
    assert record["url"] == source_candidate["url"]
    assert record["domain"] == source_candidate["domain"]
    assert record["snippet"] == source_candidate["snippet"]
    assert record["published_or_observed_date"] == (
        source_candidate["published_or_observed_date"]
    )
    for key, expected in FALSE_FLAGS.items():
        assert packet[key] is expected
        assert record[key] is expected
    for key, expected in TRUE_POSTURE_FLAGS.items():
        assert packet[key] is expected
        assert record[key] is expected

    compact_ref = search_result_candidate_packet_ref_from_packet(packet)
    assert compact_ref["packet_id"] == packet["packet_id"]
    assert compact_ref["packet_digest"] == packet["packet_digest"]
    assert compact_ref["candidate_count"] == 2


def test_search_result_candidate_packet_ids_and_digests_are_stable() -> None:
    _, packet = _packet_from_state()

    rebuilt = validate_search_result_candidate_packet(deepcopy(packet))
    reduced = reduce_live_search_validation_candidates_to_packet(
        _live_run_01_output_packet()
    )
    assert rebuilt["packet_id"] == packet["packet_id"]
    assert rebuilt["packet_digest"] == packet["packet_digest"]
    assert rebuilt["candidate_records"][0]["record_digest"] == (
        packet["candidate_records"][0]["record_digest"]
    )
    assert validate_search_result_candidate_packet(reduced) == reduced


def test_search_result_candidate_packet_rejects_raw_private_material() -> None:
    kernel = _ready_kernel()
    _reduce_validation(kernel)
    state = deepcopy(kernel.state.live_search_validation_state)

    state["search_result_candidates"][0]["headers"] = {
        "authorization": "Bearer private"
    }
    with pytest.raises(SearchResultCandidatePacketError, match="raw/private"):
        build_search_result_candidate_packet_from_live_validation_state(state)

    state = deepcopy(kernel.state.live_search_validation_state)
    state["raw_provider_payload"] = {"private": True}
    with pytest.raises(SearchResultCandidatePacketError, match="raw/private"):
        build_search_result_candidate_packet_from_live_validation_state(state)


def test_search_result_candidate_packet_rejects_evidence_citation_sufficiency_claims() -> None:
    kernel = _ready_kernel()
    _reduce_validation(kernel)

    state = deepcopy(kernel.state.live_search_validation_state)
    state["search_result_candidates"][0]["evidence_ledger_admitted"] = True
    with pytest.raises(SearchResultCandidatePacketError, match="closed runtime"):
        build_search_result_candidate_packet_from_live_validation_state(state)

    state = deepcopy(kernel.state.live_search_validation_state)
    state["search_result_candidates"][0]["citations"] = [
        "https://official.example.gov/permit"
    ]
    with pytest.raises(SearchResultCandidatePacketError, match="closed authority"):
        build_search_result_candidate_packet_from_live_validation_state(state)

    state = deepcopy(kernel.state.live_search_validation_state)
    state["source_obligation_satisfied"] = True
    with pytest.raises(SearchResultCandidatePacketError, match="closed runtime"):
        build_search_result_candidate_packet_from_live_validation_state(state)


def test_search_result_candidate_packet_rejects_tampered_candidate_digest() -> None:
    kernel = _ready_kernel()
    _reduce_validation(kernel)
    state = deepcopy(kernel.state.live_search_validation_state)
    state["search_result_candidates"][0]["candidate_digest"] = "0" * 64

    with pytest.raises(SearchResultCandidatePacketError, match="candidate digest"):
        build_search_result_candidate_packet_from_live_validation_state(state)


def test_search_result_candidate_packet_consumes_live_run_01_output_shape() -> None:
    output = _live_run_01_output_packet()

    packet = build_search_result_candidate_packet_from_live_search_validation_output(
        output
    )

    assert packet["run_id"] == output["run_id"]
    assert packet["request_id"] == output["request_id"]
    assert packet["current_answer_contract_ref"] == output[
        "current_answer_contract_ref"
    ]
    assert packet["search_executor_handoff_ref"] == output[
        "search_executor_handoff_ref"
    ]
    assert packet["selected_search_task_ids"] == output["selected_search_task_ids"]
    assert packet["provider_authorized"] == output["provider_authorized"]
    assert packet["provider_used"] == output["provider_used"]
    assert packet["candidate_count"] == output["candidate_count"] == 2
    assert packet["parent_live_search_validation_ref"]["validation_id"] == (
        output["search_result_candidates"][0]["validation_id"]
    )
    for record, candidate in zip(
        packet["candidate_records"],
        output["search_result_candidates"],
        strict=True,
    ):
        assert record["candidate_id"] == candidate["candidate_id"]
        assert record["candidate_digest"] == candidate["candidate_digest"]
        assert record["not_fetched"] is True
        assert record["not_citation"] is True
        assert record["not_sufficient"] is True


def test_search_result_candidate_packet_static_closed_surface_guard() -> None:
    forbidden_imports = {
        "core.run_kernel",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.evidence_ledger_admission_runtime",
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
        "API key",
        "requests.",
        "httpx.",
        "openai.",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "fetch_linkup_precision_block",
        "execute_author_action(",
        "build_citation",
        "EvidenceLedger(",
    ):
        assert token not in source, token

    diff = subprocess.run(
        ["git", "diff", "--numstat", "--", str(PIPELINE.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert diff.stdout.strip() == ""


def test_search_result_candidate_packet_contains_no_forbidden_material() -> None:
    _, packet = _packet_from_state()

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
        "content_fetched_from_url",
        "evidence",
        "citations",
        "final_answer_packet",
        "author_input",
    }
    assert _all_keys(packet).isdisjoint(forbidden_keys)


def test_docs_record_candidate_packet_non_evidence_handoff_posture() -> None:
    required = (
        "SearchResultCandidatePacket",
        "durable non-evidence candidate handoff",
        "before fetch/read",
        "not evidence",
        "not citation-eligible",
        "does not satisfy source obligations",
    )
    for path in DOCS:
        text = " ".join(_text(path).replace("`", "").split())
        for needle in required:
            assert needle in text, (path, needle)
