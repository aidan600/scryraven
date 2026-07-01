"""PRODUCT-PATH-REGRESSION: ordinary CLI semantic coverage status.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.__main__ -> proplex.live_semantic_coverage_status
Why ordinary product-path work cannot be done directly: not applicable; this
test guards the direct ordinary status path with fixture-sized retained artifacts
so private local output is not required.
Integration deadline: current phase.
Exit condition: keep while the default-off status flag exists.
Why this is not a shadow product path: it invokes the product status builder and
CLI dispatch, not a standalone script.
Forbidden interpretation: this is not source-obligation satisfaction, citation
eligibility/rendering, Sufficiency, FAP, Author behavior, answer text,
answerability, or product correctness.
"""

from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import core.dprime_support_proposal_schema as dprime
import proplex.live_semantic_coverage_status as semantic_status
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
)
from core.search_result_candidate_packet import (
    SearchResultCandidatePacket,
    SearchResultCandidateRecord,
)
from proplex.live_semantic_coverage_status import (
    LIVE_SEMANTIC_COVERAGE_STATUS_FLAG,
    build_live_semantic_coverage_status,
)
from tests.test_ag_limited_live_search_candidate_01 import _generic_provider_output
from tests.test_ag_search_result_candidate_packet_01 import _packet_from_state

QUERY = "What is the current adult U.S. passport book renewal fee?"

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_MODULE = ROOT / "proplex" / "live_semantic_coverage_status.py"
PASSPORT_COMPONENT_ID = "component:adult-us-passport-book-renewal-fee"
PASSPORT_OBLIGATION_ID = "obligation:official-current-passport-fee-source"
PASSPORT_URL = "https://travel.state.gov/en/passports/apply/help/fees.html"
PASSPORT_TEXT = (
    "The U.S. Department of State passport fees page lists the adult passport "
    "book renewal by mail fee as $130."
)
UNRELATED_SAME_LANE_TEXT = (
    "This bounded sanitized retained page excerpt describes routine passport "
    "photo requirements and appointment scheduling. It does not state an adult "
    "passport book renewal fee."
)


def test_product_status_blocks_without_current_path_support_signal(
    tmp_path: Path,
) -> None:
    repo_root, candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
    )

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert result.return_code == 2
    assert "mode: BUILD" in result.output
    assert "ordinary entrypoint: python -m proplex" in result.output
    assert f"status flag: {LIVE_SEMANTIC_COVERAGE_STATUS_FLAG}" in result.output
    assert "usable-answer verdict target: YES" in result.output
    assert "answerability/correctness: not claimed" in result.output
    assert "retained-artifact preflight status: PASS" in result.output
    assert "retained search candidate status: preflight_passed" in result.output
    assert "fetch/read handoff status: retained_packet_verified" in result.output
    assert "source/evidence custody/admission status: custody_created" in result.output
    assert (
        "citation/source-obligation readiness posture before semantic support: "
        "not_yet_semantically_supported"
    ) in result.output
    assert "EvidenceRelativeAnalysisPacket / AnalystReport" in result.output
    assert "D-prime schema status: available" in result.output
    assert "D-prime preflight status: passed" in result.output
    assert "D-prime model review status: not licensed" in result.output
    assert "D-prime assessment status: not reached" in result.output
    assert "D-prime proposal validation status: not reached" in result.output
    assert "RunKernel support admission status: not reached" in result.output
    assert "Analyst support proposal status: not reached" in result.output
    assert "Analyst support proposal ref/digest: unavailable" in result.output
    assert "SemanticObservation admission status: unavailable" in result.output
    assert "SemanticObservation id/ref/digest: unavailable" in result.output
    assert "ComponentCoverage status: unavailable" in result.output
    assert "ComponentCoverage id/ref/digest: unavailable" in result.output
    assert f"component id/ref: {candidate['component_id']}" in result.output
    assert "coverage not bound" in result.output
    assert "source obligation id/ref:" in result.output
    assert (
        "semantic support source: unavailable; D-prime model review not licensed"
        in result.output
    )
    assert "semantic support/custody distinction preserved: true" in result.output
    assert "ad hoc semantic matcher/heuristic avoided: true" in result.output
    assert "raw/private retention: false" in result.output
    assert "citation eligibility/rendering" in result.output
    assert "source-obligation satisfaction" in result.output
    assert "SufficiencyReadiness" in result.output
    assert "final answer packet" in result.output
    assert "Author/AuthorProse" in result.output
    assert (
        f"decision: {dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED}"
        in result.output
    )

    support = result.payload["analyst_support_proposal_ref"]
    assert support["status"] == "not reached"
    assert support["proposal_ref"] == "unavailable"
    semantic = result.payload["semantic_observation_admission_ref"]
    assert semantic["status"] == "unavailable"
    assert semantic["observation_ref"] == "unavailable"
    coverage = result.payload["component_coverage_ref"]
    assert coverage["status"] == "unavailable"
    assert coverage["coverage_ref"] == "unavailable"
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["schema_status"] == "available"
    assert dprime_status["preflight_status"] == "passed"
    assert dprime_status["model_review_status"] == "not licensed"
    assert dprime_status["objects_created"]["evidence_frame_preflight"] is True
    assert dprime_status["objects_created"]["validated_support_proposal"] is False
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    admission = result.payload["source_evidence_admission_ref"]
    assert admission["candidate_content_custody_is_semantic_support"] is False
    assert result.payload["ad_hoc_semantic_matcher_avoided"] is True
    assert "bounded_text" not in result.output
    assert PASSPORT_TEXT not in result.output
    assert "source-obligation satisfaction claimed: true" not in result.output
    assert "citation eligibility claimed: true" not in result.output
    assert "answer prose:" not in result.output


_DPRIME_MODEL_REVIEW_DETAIL = "D-prime model review is not licensed in this phase"


def test_same_lane_unrelated_bounded_text_does_not_create_semantic_support(
    tmp_path: Path,
) -> None:
    repo_root, candidate = _passport_retained_repo(
        tmp_path,
        bounded_text=UNRELATED_SAME_LANE_TEXT,
    )
    fetch_packet = json.loads(
        (
            repo_root
            / "output"
            / "ag_live_source_survival_fetch_read_01"
            / "fetch_read_content_packet.json"
        ).read_text(encoding="utf-8")
    )
    reference = fetch_packet["reference_records"][0]
    assert reference["fetch_read_status"] == "readable"
    assert reference["bounded_text_sanitized"] is True
    assert reference["bounded_text_bounded"] is True
    assert reference["bounded_character_count"] == len(UNRELATED_SAME_LANE_TEXT)
    assert reference["excerpt_digest"]
    assert reference["candidate_id"] == candidate["candidate_id"]
    assert reference["component_id"] == PASSPORT_COMPONENT_ID
    assert reference["source_obligation_candidate_ids"] == [PASSPORT_OBLIGATION_ID]

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
    )

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert result.return_code == 2
    assert _DPRIME_MODEL_REVIEW_DETAIL in result.output
    support = result.payload["analyst_support_proposal_ref"]
    assert support["status"] == "not reached"
    assert support["proposal_ref"] == "unavailable"
    semantic = result.payload["semantic_observation_admission_ref"]
    assert semantic["status"] == "unavailable"
    assert semantic["observation_ref"] == "unavailable"
    coverage = result.payload["component_coverage_ref"]
    assert coverage["status"] == "unavailable"
    assert coverage["coverage_ref"] == "unavailable"
    assert "ComponentCoverage id/ref/digest: unavailable" in result.output
    assert "SemanticObservation id/ref/digest: unavailable" in result.output
    assert "Analyst support proposal ref/digest: unavailable" in result.output
    assert "bounded_text" not in result.output
    assert UNRELATED_SAME_LANE_TEXT not in result.output


def test_product_status_blocks_before_retained_support_consumer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    def fail_consumer(**_kwargs: Any) -> Any:
        raise AssertionError("D-prime preflight blocker must run before old consumer")

    monkeypatch.setattr(
        semantic_status,
        "build_retained_custody_semantic_coverage",
        fail_consumer,
    )

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
    )

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert result.return_code == 2
    assert "D-prime preflight status: passed" in result.output
    assert "D-prime model review status: not licensed" in result.output
    assert "Analyst support proposal status: not reached" in result.output
    assert (
        f"decision: {dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED}"
        in result.output
    )
    assert f"blocker detail: {_DPRIME_MODEL_REVIEW_DETAIL}" in result.output
    assert "next blocked surface:" in result.output
    assert PASSPORT_TEXT not in result.output


def test_cli_flag_is_default_off_and_skips_live_key_validation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _import_cli_with_dotenv_disabled(monkeypatch)
    calls: list[str] = []

    def fake_status(**_kwargs: Any) -> Any:
        calls.append("status")
        return SimpleNamespace(return_code=0, output="decision: PASS")

    def fail_key_validation(**_kwargs: Any) -> list[str]:
        raise AssertionError("status path must not validate live provider keys")

    def fail_pipeline(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("status path must not run the pipeline")

    monkeypatch.setattr(cli, "build_live_semantic_coverage_status", fake_status)
    monkeypatch.setattr(cli, "missing_required_api_keys", fail_key_validation)
    monkeypatch.setattr(cli, "run_pipeline", fail_pipeline)

    assert cli.main([QUERY, LIVE_SEMANTIC_COVERAGE_STATUS_FLAG]) == 0

    assert calls == ["status"]
    assert "decision: PASS" in capsys.readouterr().out


def test_product_status_module_avoids_live_calls_scripts_and_ad_hoc_semantics() -> None:
    imported, called = _imports_and_calls(PRODUCT_MODULE)
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.semantic_observation_admission_bridge",
        "core.semantic_observation_admission_runtime",
        "core.component_coverage_reduction_runtime",
        "core.component_coverage_record",
        "openai",
        "requests",
        "httpx",
        "dotenv",
        "subprocess",
    }
    forbidden_calls = {
        "run_pipeline",
        "call_broker",
        "invoke_broker",
        "search_web",
        "retrieve",
        "dispatch_retrieval",
        "fetch_url",
        "fetch_page",
        "read_url",
        "ask_model",
        "re",
        "search",
        "match",
        "findall",
    }
    assert imported.isdisjoint(forbidden_imports)
    assert not any(name == "scripts" or name.startswith("scripts.") for name in imported)
    assert called.isdisjoint(forbidden_calls)


def _passport_retained_repo(
    tmp_path: Path,
    *,
    bounded_text: str = PASSPORT_TEXT,
) -> tuple[Path, dict[str, Any]]:
    repo_root = tmp_path / "repo"
    search_dir = repo_root / "output" / "ag_live_ordinary_search_candidate_01b"
    fetch_dir = repo_root / "output" / "ag_live_source_survival_fetch_read_01"
    _kernel, base_packet = _packet_from_state(candidate_count=1)
    base = base_packet["candidate_records"][0]
    candidate = SearchResultCandidateRecord(
        run_id=base_packet["run_id"],
        request_id=base_packet["request_id"],
        current_answer_contract_ref=base_packet["current_answer_contract_ref"],
        search_executor_handoff_ref=base_packet["search_executor_handoff_ref"],
        search_task_id=base["search_task_id"],
        provider_authorized=base["provider_authorized"],
        provider_used=base["provider_used"],
        provider_call_index=base["provider_call_index"],
        result_rank=1,
        title="Passport Fees",
        url=PASSPORT_URL,
        domain="travel.state.gov",
        candidate_id="search-result-candidate:adult-passport-fee",
        candidate_digest="candidate-digest-adult-passport-fee",
        validation_id=base.get("validation_id"),
        parent_live_search_validation_ref=base.get("parent_live_search_validation_ref"),
        query_intent_id=base.get("query_intent_id"),
        component_id=PASSPORT_COMPONENT_ID,
        source_obligation_candidate_ids=(PASSPORT_OBLIGATION_ID,),
        snippet="Official current passport fee information.",
        published_or_observed_date="2026-06-30",
    ).to_dict()
    candidate_packet = SearchResultCandidatePacket(
        run_id=base_packet["run_id"],
        request_id=base_packet["request_id"],
        current_answer_contract_ref=base_packet["current_answer_contract_ref"],
        search_executor_handoff_ref=base_packet["search_executor_handoff_ref"],
        candidate_records=[candidate],
        selected_search_task_ids=base_packet["selected_search_task_ids"],
        provider_authorized=base_packet["provider_authorized"],
        provider_used=base_packet["provider_used"],
        parent_live_search_validation_ref=base_packet.get(
            "parent_live_search_validation_ref",
            {},
        ),
    ).to_dict()
    fetch_packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        [_passport_readable_material(candidate_packet, bounded_text=bounded_text)],
    )
    provider_result = {
        "title": candidate["title"],
        "url": candidate["url"],
        "domain": candidate["domain"],
        "snippet": candidate["snippet"],
        "published_or_observed_date": candidate["published_or_observed_date"],
        "result_rank": candidate["result_rank"],
        "provider_call_index": candidate["provider_call_index"],
    }
    search_dir.mkdir(parents=True, exist_ok=True)
    fetch_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        search_dir / "sanitized_provider_results.json",
        _generic_provider_output([provider_result]),
    )
    _write_json(search_dir / "search_candidate_packet.json", candidate_packet)
    _write_json(search_dir / "search_result_candidate_packet.json", candidate_packet)
    _write_json(fetch_dir / "fetch_read_content_packet.json", fetch_packet)
    _write_json(fetch_dir / "live_source_survival_summary.json", _summary(fetch_packet))
    return repo_root, candidate


def _passport_readable_material(
    packet: dict[str, Any],
    *,
    bounded_text: str = PASSPORT_TEXT,
) -> dict[str, Any]:
    candidate = packet["candidate_records"][0]
    return {
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
        "retrieved_or_observed_at": "2026-06-30T00:00:00Z",
        "content_title": "Passport Fees",
        "bounded_text": bounded_text,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_text_char_count": len(bounded_text),
        "raw_page_content_retained": False,
        "raw_headers_retained": False,
    }


def _summary(fetch_packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": "PASS",
        "readable_content_handoff_created": True,
        "retention_flags": {
            "headers_retained": False,
            "page_content_retained": False,
            "page_html_retained": False,
            "page_text_retained": False,
            "private_material_retained": False,
            "prompt_retained": False,
            "provider_payload_retained": False,
            "search_response_retained": False,
            "unbounded_page_material_retained": False,
        },
        "closed_downstream_surfaces": {
            "answer_text": False,
            "author_or_authorprose": False,
            "citation_eligibility_or_rendering": False,
            "component_coverage": False,
            "evidence_ledger_admission": False,
            "final_answer_packet": False,
            "product_correctness_claim": False,
            "semantic_observation": False,
            "source_obligation_satisfaction": False,
            "sufficiency_readiness": False,
        },
        "fetch_read_content_packet_ref": {
            "packet_id": fetch_packet["packet_id"],
            "packet_digest": fetch_packet["packet_digest"],
            "reference_count": fetch_packet["reference_count"],
            "schema_version": fetch_packet["schema_version"],
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _import_cli_with_dotenv_disabled(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    return importlib.import_module("proplex.__main__")


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    return imported, called
