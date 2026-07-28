from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from scripts import ag_limited_live_search_candidate_01 as prior
from scripts import ag_live_source_survival_fetch_read_custody_01 as harness

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ag_live_source_survival_fetch_read_custody_01.py"
DOC = (
    ROOT
    / "docs"
    / "architecture"
    / "AG_LIVE_SOURCE_SURVIVAL_FETCH_READ_CUSTODY_01.md"
)


class FakeFetcher:
    def __init__(self, result: harness.FetchReadResult) -> None:
        self.result = result
        self.calls: list[str] = []

    def __call__(self, url: str) -> harness.FetchReadResult:
        self.calls.append(url)
        return self.result


def _output_dir(name: str) -> Path:
    return ROOT / "output" / "ag_live_source_survival_fetch_read_custody_01" / name


def _prior_dir(name: str) -> Path:
    return ROOT / "output" / "ag_limited_live_search_candidate_01" / (
        f"source-survival-{name}"
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def _generic_provider_output(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "2",
        "proof_kind": "scryraven_search_query_proof_v2",
        "provider": "serper",
        "operation": "search.query",
        "status": "ok",
        "result_count": len(results),
        "results": results,
        "physical_attempt_count": 1,
        "provider_elapsed_milliseconds_total": 5,
        "caller_authorized_cost_ceiling_usd": "0.05",
        "raw_provider_payload_retained": False,
        "raw_request_material_retained": False,
        "raw_response_material_retained": False,
        "raw_search_response_retained": False,
    }


def _official_result(rank: int = 1) -> dict[str, Any]:
    return {
        "title": "Passport Fees - Travel.gov - State Department",
        "url": "https://travel.state.gov/en/passports/apply/help/fees.html",
        "domain": "travel.state.gov",
        "snippet": "Official passport book renewal fee information.",
        "published_or_observed_date": "Mar 19, 2026",
        "result_rank": rank,
        "provider_call_index": 1,
    }


def _secondary_result(rank: int = 1) -> dict[str, Any]:
    return {
        "title": "Passport renewal fees guide",
        "url": "https://example.com/passport-renewal-fees",
        "domain": "example.com",
        "snippet": "Unofficial fee summary.",
        "result_rank": rank,
        "provider_call_index": 1,
    }


def _prior_outputs(
    name: str,
    *,
    results: list[dict[str, Any]] | None = None,
) -> tuple[Path, Path]:
    out = _prior_dir(name)
    provider_results = _write_json(
        out / "sanitized_provider_results.json",
        _generic_provider_output(results or [_official_result()]),
    )
    prior.reduce_results(
        query=prior.DEFAULT_QUERY,
        provider_results_path=provider_results,
        output_dir=out,
    )
    return out / "search_result_candidate_packet.json", out / "validation_packet.json"


def _fake_fetch_result(*, text: str | None = None) -> harness.FetchReadResult:
    sanitized = text or (
        "Passport Fees Travel.gov State Department Adult passport book renewal "
        "fee information in bounded sanitized readable content."
    )
    return harness.FetchReadResult(
        attempted_url="https://travel.state.gov/en/passports/apply/help/fees.html",
        final_url="https://travel.state.gov/en/passports/apply/help/fees.html",
        final_domain="travel.state.gov",
        status_code=200,
        status_class="2xx",
        content_type="text/html",
        fetched_byte_count=42_000,
        sanitized_text=sanitized,
        content_title="Passport Fees - Travel.gov - State Department",
        redirect_count=0,
        retrieved_or_observed_at="2026-06-29T00:00:00+00:00",
    )


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


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


def test_prepare_request_consumes_prior_packets_without_fetching() -> None:
    candidate_path, validation_path = _prior_outputs("prepare")

    packet = harness.prepare_request(
        candidate_packet_path=candidate_path,
        validation_packet_path=validation_path,
        output_dir=_output_dir("prepare"),
    )

    assert packet["packet_kind"] == "source_survival_request_packet"
    assert packet["selected_source_survived"] == (
        "validation_not_run_operator_blocked"
    )
    assert packet["fetch_read_calls_attempted"] == 0
    assert packet["fetch_read_calls_completed"] == 0
    assert packet["selected_candidate"]["rank"] == 1
    assert packet["selected_candidate"]["domain"] == "travel.state.gov"
    assert packet["selected_candidate"]["url"] == (
        "https://travel.state.gov/en/passports/apply/help/fees.html"
    )
    assert packet["request_generation_fetch_read_free"] is True
    assert (_output_dir("prepare") / "request_packet.json").exists()
    assert (_output_dir("prepare") / "request_packet.md").exists()


def test_selected_candidate_must_be_rank_one_travel_state_gov() -> None:
    candidate_path, validation_path = _prior_outputs(
        "mismatch-rank-one",
        results=[_secondary_result(1), _official_result(2)],
    )

    with pytest.raises(
        harness.SourceSurvivalError,
        match="prior_candidate_packet_missing_or_mismatched",
    ):
        harness.prepare_request(
            candidate_packet_path=candidate_path,
            validation_packet_path=validation_path,
            output_dir=_output_dir("mismatch-rank-one"),
        )


def test_missing_or_mismatched_prior_output_fails_closed() -> None:
    candidate_path, validation_path = _prior_outputs("mismatch-validation")
    tampered = _read_json(validation_path)
    tampered["sanitized_provider_result_summaries"][0]["url"] = (
        "https://travel.state.gov/en/other.html"
    )
    tampered_path = _write_json(
        validation_path.parent / "tampered_validation_packet.json",
        tampered,
    )

    with pytest.raises(harness.SourceSurvivalError) as exc_info:
        harness.prepare_request(
            candidate_packet_path=candidate_path,
            validation_packet_path=tampered_path,
            output_dir=_output_dir("mismatch-validation"),
        )
    assert exc_info.value.code == "prior_candidate_packet_missing_or_mismatched"


def test_fetch_read_custody_requires_confirm_fetch_read() -> None:
    candidate_path, validation_path = _prior_outputs("confirm-required")
    fetcher = FakeFetcher(_fake_fetch_result())

    with pytest.raises(harness.SourceSurvivalError) as exc_info:
        harness.fetch_read_custody(
            candidate_packet_path=candidate_path,
            validation_packet_path=validation_path,
            output_dir=_output_dir("confirm-required"),
            confirm_fetch_read=False,
            fetcher=fetcher,
        )

    assert exc_info.value.code == "confirm_fetch_read_required"
    assert fetcher.calls == []


def test_fetch_read_uses_exactly_one_selected_url_and_no_provider_imports() -> None:
    candidate_path, validation_path = _prior_outputs("one-fetch")
    fetcher = FakeFetcher(_fake_fetch_result())

    packet = harness.fetch_read_custody(
        candidate_packet_path=candidate_path,
        validation_packet_path=validation_path,
        output_dir=_output_dir("one-fetch"),
        confirm_fetch_read=True,
        fetcher=fetcher,
    )

    assert fetcher.calls == [
        "https://travel.state.gov/en/passports/apply/help/fees.html"
    ]
    assert packet["fetch_read_calls_attempted"] == 1
    assert packet["fetch_read_calls_completed"] == 1
    assert packet["live_budget"]["provider_search_calls"] == 0
    assert packet["live_budget"]["broker_calls"] == 0
    assert packet["live_budget"]["model_calls"] == 0
    forbidden_imports = {
        "scripts.run_provider_proxy_broker_once",
        "scripts.request_provider_proxy_broker",
        "core.search_providers",
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "subprocess",
    }
    assert _imports(SCRIPT).isdisjoint(forbidden_imports)


def test_sanitized_fixture_reduces_through_fetch_read_packet_and_ledger() -> None:
    candidate_path, validation_path = _prior_outputs("survival-pass")

    packet = harness.fetch_read_custody(
        candidate_packet_path=candidate_path,
        validation_packet_path=validation_path,
        output_dir=_output_dir("survival-pass"),
        confirm_fetch_read=True,
        fetcher=FakeFetcher(_fake_fetch_result()),
    )

    out = _output_dir("survival-pass")
    assert packet["selected_source_survived"] == "source_survival_pass"
    assert packet["final_domain"] == "travel.state.gov"
    assert packet["http_status_class"] == "2xx"
    assert packet["fetch_read_content_packet_ref"]["packet_id"]
    assert packet["sanitized_content_reference_ref"]["reference_id"]
    assert packet["evidence_ledger_candidate_content_custody_count"] == 1
    assert (out / "source_survival_packet.json").exists()
    assert (out / "source_survival_packet.md").exists()
    assert (out / "fetch_read_content_packet.json").exists()
    assert (out / "sanitized_content_reference.json").exists()
    assert (out / "evidence_ledger_projection.json").exists()


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "raw_html",
        "headers",
        "cookies",
        "unbounded_text",
        "citations",
        "fap_material",
        "author_material",
        "semantic_support",
        "source_obligation_satisfaction",
        "component_satisfaction",
    ],
)
def test_source_survival_packet_rejects_raw_unbounded_and_closed_authority_fields(
    forbidden_key: str,
) -> None:
    candidate_path, validation_path = _prior_outputs(f"forbidden-{forbidden_key}")
    packet = harness.prepare_request(
        candidate_packet_path=candidate_path,
        validation_packet_path=validation_path,
        output_dir=_output_dir(f"forbidden-{forbidden_key}"),
    )
    spoofed = deepcopy(packet)
    spoofed[forbidden_key] = "forbidden"

    with pytest.raises(harness.SourceSurvivalError):
        harness.validate_source_survival_packet(spoofed)


def test_downstream_surfaces_remain_closed_false() -> None:
    candidate_path, validation_path = _prior_outputs("closed-surfaces")

    packet = harness.fetch_read_custody(
        candidate_packet_path=candidate_path,
        validation_packet_path=validation_path,
        output_dir=_output_dir("closed-surfaces"),
        confirm_fetch_read=True,
        fetcher=FakeFetcher(_fake_fetch_result()),
    )

    assert packet["semantic_observation_admissions"] == 0
    assert packet["component_coverage_reductions"] == 0
    assert packet["citation_eligibility_decisions"] == 0
    assert packet["source_obligation_satisfaction_decisions"] == 0
    assert packet["sufficiency_fap_author_authorprose_from_live_evidence"] == 0
    summary = packet["evidence_ledger_candidate_content_custody_projection_summary"]
    for key in (
        "candidate_content_custody_is_semantic_support",
        "citation_eligible",
        "source_obligation_satisfied",
        "component_coverage_created",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "bounded_content_payload_retained",
    ):
        assert summary[key] is False


def test_source_survival_verdicts_are_distinct_from_support_and_readiness() -> None:
    assert "source_survival_pass" in harness.SOURCE_SURVIVAL_RESULTS
    assert "validation_not_run_operator_blocked" in harness.SOURCE_SURVIVAL_RESULTS
    assert "semantic_support" not in harness.SOURCE_SURVIVAL_RESULTS
    assert "readiness" not in harness.SOURCE_SURVIVAL_RESULTS


def test_bounded_excerpt_is_review_debug_only_not_answer_or_citation_material() -> None:
    candidate_path, validation_path = _prior_outputs("bounded-excerpt")
    long_text = " ".join(["bounded sanitized passport fee content"] * 500)

    packet = harness.fetch_read_custody(
        candidate_packet_path=candidate_path,
        validation_packet_path=validation_path,
        output_dir=_output_dir("bounded-excerpt"),
        confirm_fetch_read=True,
        fetcher=FakeFetcher(_fake_fetch_result(text=long_text)),
    )

    assert len(packet["bounded_excerpt"]) <= (
        harness.FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS
    )
    posture = packet["bounded_excerpt_posture"]
    assert posture["review_debug_only"] is True
    assert posture["not_answer_material"] is True
    assert posture["not_citation_text"] is True
    assert posture["not_semantic_support"] is True


def test_no_live_fetch_runs_in_pytest_or_ci() -> None:
    candidate_path, validation_path = _prior_outputs("no-live-pytest")
    packet = harness.prepare_request(
        candidate_packet_path=candidate_path,
        validation_packet_path=validation_path,
        output_dir=_output_dir("no-live-pytest"),
    )

    assert packet["fetch_read_calls_attempted"] == 0
    assert packet["request_generation_fetch_read_free"] is True
    source = SCRIPT.read_text(encoding="utf-8")
    assert "confirm_fetch_read" in source
    assert "--confirm-fetch-read" in source


def test_output_contains_no_raw_private_fields_or_answer_material() -> None:
    candidate_path, validation_path = _prior_outputs("output-sanitized")
    packet = harness.fetch_read_custody(
        candidate_packet_path=candidate_path,
        validation_packet_path=validation_path,
        output_dir=_output_dir("output-sanitized"),
        confirm_fetch_read=True,
        fetcher=FakeFetcher(_fake_fetch_result()),
    )

    forbidden = {
        "raw_html",
        "raw_response_headers",
        "raw_cookies",
        "unbounded_text",
        "answer_text",
        "citations",
        "final_answer_packet",
        "author_material",
        "semantic_support",
        "source_obligation_satisfaction",
        "component_satisfaction",
    }
    assert _all_keys(packet).isdisjoint(forbidden)


def test_doc_records_proof_mode_caps_and_non_proofs() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "Mode: PROOF",
        "NO-BUT-JUSTIFIED",
        "rank-1 `travel.state.gov`",
        "one public URL fetch/read",
        "FetchReadContentPacket",
        "EvidenceLedger custody is lineage/custody only",
        "not semantic support",
        "mandatory next Build/product checkpoint",
    )
    for needle in required:
        assert needle in text
