from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
)
from proplex.live_acquisition_readability_status import (
    LIVE_ACQUISITION_READABILITY_STATUS_FLAG,
    build_live_acquisition_readability_status,
)
from tests.test_ag_limited_live_search_candidate_01 import _generic_provider_output
from tests.test_ag_search_result_candidate_packet_01 import _packet_from_state

QUERY = "What is the current adult U.S. passport book renewal fee?"
ROOT = Path(__file__).resolve().parents[1]


def test_product_status_consumes_retained_search_and_fetch_read_artifacts(
    tmp_path: Path,
) -> None:
    repo_root, candidate = _retained_repo(tmp_path)

    result = build_live_acquisition_readability_status(
        query=QUERY,
        repo_root=repo_root,
    )

    assert result.decision == "PASS"
    assert result.return_code == 0
    assert "mode: BUILD" in result.output
    assert "usable-answer verdict target: YES" in result.output
    assert "answerability/correctness: not claimed" in result.output
    assert "retained search candidate status: preflight_passed" in result.output
    assert "selected candidate rank: 1" in result.output
    assert "selected candidate domain: official.example.gov" in result.output
    assert f"selected candidate URL: {candidate['url']}" in result.output
    assert "candidate lineage status: preserved" in result.output
    assert "fetch/read handoff status: retained_packet_verified" in result.output
    assert "readability status: readable" in result.output
    assert "sanitized content reference present: true" in result.output
    assert "raw/private retention: false" in result.output
    assert "decision: PASS" in result.output
    legacy_non_build_verdict = "NO" + "-BUT-JUSTIFIED"
    assert legacy_non_build_verdict not in result.output
    assert "bounded_text" not in result.output
    assert "official current Example Program permit threshold is 500" not in result.output


def test_product_status_blocks_fetch_read_lineage_mismatch(tmp_path: Path) -> None:
    repo_root, _candidate = _retained_repo(tmp_path)
    fetch_packet_path = (
        repo_root
        / "output"
        / "ag_live_source_survival_fetch_read_01"
        / "fetch_read_content_packet.json"
    )
    fetch_packet = _read_json(fetch_packet_path)
    fetch_packet["search_result_candidate_packet_digest"] = "0" * 64
    _write_json(fetch_packet_path, fetch_packet)

    result = build_live_acquisition_readability_status(
        query=QUERY,
        repo_root=repo_root,
    )

    assert result.decision == "BLOCKED_FETCH_READ_ARTIFACT_LINEAGE"
    assert "usable-answer verdict target: YES" in result.output
    assert "answerability/correctness: not claimed" in result.output


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

    monkeypatch.setattr(cli, "build_live_acquisition_readability_status", fake_status)
    monkeypatch.setattr(cli, "missing_required_api_keys", fail_key_validation)
    monkeypatch.setattr(cli, "run_pipeline", fail_pipeline)

    assert cli.main([QUERY, LIVE_ACQUISITION_READABILITY_STATUS_FLAG]) == 0

    assert calls == ["status"]
    assert "decision: PASS" in capsys.readouterr().out


def _retained_repo(tmp_path: Path) -> tuple[Path, Mapping[str, Any]]:
    repo_root = tmp_path / "repo"
    search_dir = repo_root / "output" / "ag_live_ordinary_search_candidate_01b"
    fetch_dir = repo_root / "output" / "ag_live_source_survival_fetch_read_01"
    _kernel, candidate_packet = _packet_from_state(candidate_count=1)
    candidate = candidate_packet["candidate_records"][0]
    provider_result = {
        "title": candidate["title"],
        "url": candidate["url"],
        "domain": candidate["domain"],
        "snippet": candidate.get("snippet", "Official source candidate."),
        "published_or_observed_date": candidate.get("published_or_observed_date"),
        "result_rank": candidate["result_rank"],
        "provider_call_index": candidate["provider_call_index"],
    }
    fetch_packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        [_readable_material(candidate_packet)],
    )
    search_dir.mkdir(parents=True, exist_ok=True)
    fetch_dir.mkdir(parents=True, exist_ok=True)
    _write_json(search_dir / "sanitized_provider_results.json", _generic_provider_output([provider_result]))
    _write_json(search_dir / "search_candidate_packet.json", candidate_packet)
    _write_json(search_dir / "search_result_candidate_packet.json", candidate_packet)
    _write_json(fetch_dir / "fetch_read_content_packet.json", fetch_packet)
    _write_json(fetch_dir / "live_source_survival_summary.json", _summary(fetch_packet))
    return repo_root, candidate


def _readable_material(packet: Mapping[str, Any]) -> dict[str, Any]:
    candidate = packet["candidate_records"][0]
    text = "The official current Example Program permit threshold is 500 units."
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
        "content_title": "Official Example Program Permit Threshold",
        "bounded_text": text,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_text_char_count": len(text),
        "raw_page_content_retained": False,
        "raw_headers_retained": False,
    }


def _summary(fetch_packet: Mapping[str, Any]) -> dict[str, Any]:
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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def _import_cli_with_dotenv_disabled(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    return importlib.import_module("proplex.__main__")
