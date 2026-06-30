from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_DEFAULT_RESULTS_PER_TASK_CAP,
    LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP,
)
from core.run_kernel import RunKernelTransitionError
from scripts import ag_limited_live_search_candidate_01 as harness

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ag_limited_live_search_candidate_01.py"
DOC = ROOT / "docs" / "architecture" / "AG_LIMITED_LIVE_SEARCH_CANDIDATE_01.md"

FALSE_PACKET_FLAGS = {
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


def _output_dir(name: str) -> Path:
    return ROOT / "output" / "ag_limited_live_search_candidate_01" / name


def _provider_results_path(name: str) -> Path:
    return _output_dir(name) / "sanitized_provider_results.json"


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def _generic_provider_output(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "request_kind": "generic_provider_proxy_request",
        "provider": "serper",
        "operation": "search",
        "result_count": len(results),
        "results": results,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _official_result(rank: int = 1) -> dict[str, Any]:
    return {
        "title": "Passport Fees",
        "url": "https://travel.state.gov/content/travel/en/passports/how-apply/fees.html",
        "domain": "travel.state.gov",
        "snippet": "Official passport book renewal fee information.",
        "published_or_observed_date": "2026-06-01",
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


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_prepare_request_includes_exact_query_mode_caps_redaction_and_paths() -> None:
    out = _output_dir("prepare")

    packet = harness.prepare_request(
        query=harness.DEFAULT_QUERY,
        output_dir=out,
    )

    assert (out / "request_packet.json").exists()
    assert (out / "request_packet.md").exists()
    assert _read_json(out / "request_packet.json") == packet
    assert packet["mode"] == "PROOF"
    assert packet["usable_answer_verdict_target"] == "NO-BUT-JUSTIFIED"
    assert packet["validation_search_query"] == harness.DEFAULT_QUERY
    assert packet["original_user_style_query"] == harness.USER_FACING_QUESTION
    assert packet["live_budget"]["max_provider_search_calls_total"] == 1
    assert packet["live_budget"]["max_results"] == 5
    assert packet["live_budget"]["budget_scope"] == (
        "phase-local licensed budget; not a global default"
    )
    assert packet["live_budget"]["ordinary_default_results_per_task_cap"] == 2
    assert packet["live_budget"]["explicit_results_per_task_ceiling"] == 5
    assert packet["live_budget"]["model_calls"] == 0
    assert packet["raw_provider_payload_retained"] is False
    assert packet["raw_search_response_retained"] is False
    assert packet["provider_calls_attempted"] == 0
    assert packet["broker_invoked"] is False
    assert packet["live_provider_called"] is False
    assert packet["request_generation_provider_free"] is True
    assert packet["expected_output_paths"]["request_packet"].startswith(
        "output\\ag_limited_live_search_candidate_01"
    ) or packet["expected_output_paths"]["request_packet"].startswith(
        "output/ag_limited_live_search_candidate_01"
    )


def test_global_default_results_per_task_cap_remains_two() -> None:
    assert LIVE_SEARCH_VALIDATION_DEFAULT_RESULTS_PER_TASK_CAP == 2
    assert LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP == 5
    front_half = harness.build_front_half(
        query=harness.DEFAULT_QUERY,
        output_dir=_output_dir("global-default"),
    )

    action = front_half.kernel.authorize_live_search_validation(
        selected_search_task_ids=front_half.selected_search_task_ids,
        provider_authorized="serper",
    )

    assert action.inputs["results_per_task_cap"] == 2


def test_prepare_request_and_reduce_results_do_not_import_provider_transport() -> None:
    forbidden_imports = {
        "scripts.run_provider_proxy_broker_once",
        "scripts.request_provider_proxy_broker",
        "core.search_providers",
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "urllib.request",
        "subprocess",
    }
    assert _imports(SCRIPT).isdisjoint(forbidden_imports)


def test_reduce_results_builds_candidate_packet_from_five_sanitized_records() -> None:
    out = _output_dir("reduce-pass")
    results = [_official_result(rank=1), *[_secondary_result(rank=i) for i in range(2, 6)]]
    provider_results = _write_json(
        _provider_results_path("reduce-pass"),
        _generic_provider_output(results),
    )

    packet = harness.reduce_results(
        query=harness.DEFAULT_QUERY,
        provider_results_path=provider_results,
        output_dir=out,
    )

    assert (out / "validation_packet.json").exists()
    assert (out / "validation_packet.md").exists()
    assert (out / "search_result_candidate_packet.json").exists()
    assert packet["sanitized_provider_result_count"] == 5
    assert packet["provider_calls_attempted"] == 1
    assert packet["provider_calls_completed"] == 1
    assert packet["broker_invoked"] is True
    assert packet["live_provider_called"] is True
    assert packet["search_result_candidate_packet_status"] == "built_and_validated"
    assert packet["likely_acquisition_result"] == "candidate_acquisition_pass"
    assert packet["at_least_one_result_appears_official_current_government_source"] is True
    candidate_packet = _read_json(out / "search_result_candidate_packet.json")
    assert candidate_packet["candidate_count"] == 5
    assert candidate_packet["candidate_records"][0]["domain"] == "travel.state.gov"


def test_cap_above_explicit_licensed_ceiling_fails_closed() -> None:
    front_half = harness.build_front_half(
        query=harness.DEFAULT_QUERY,
        output_dir=_output_dir("above-ceiling-action"),
    )

    with pytest.raises(RunKernelTransitionError, match="explicit cap"):
        front_half.kernel.authorize_live_search_validation(
            selected_search_task_ids=front_half.selected_search_task_ids,
            provider_authorized="serper",
            results_per_task_cap=6,
        )

    too_many_results = [_official_result(rank=index) for index in range(1, 7)]
    provider_results = _write_json(
        _provider_results_path("above-ceiling-results"),
        _generic_provider_output(too_many_results),
    )
    with pytest.raises(harness.LimitedLiveSearchCandidateError, match="max results cap 5"):
        harness.reduce_results(
            query=harness.DEFAULT_QUERY,
            provider_results_path=provider_results,
            output_dir=_output_dir("above-ceiling-results"),
        )


def test_reducer_accepts_allowed_alias_fields_only() -> None:
    out = _output_dir("aliases")
    result = {
        "title": "Passport Fees",
        "link": "https://travel.state.gov/content/travel/en/passports/how-apply/fees.html",
        "snippet": "Official passport book renewal fee information.",
        "date": "2026-06-01",
        "rank": 1,
        "call_index": 1,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    provider_results = _write_json(
        _provider_results_path("aliases"),
        _generic_provider_output([result]),
    )

    packet = harness.reduce_results(
        query=harness.DEFAULT_QUERY,
        provider_results_path=provider_results,
        output_dir=out,
    )

    summary = packet["sanitized_provider_result_summaries"][0]
    assert summary["url"].startswith("https://travel.state.gov/")
    assert summary["rank"] == 1
    assert summary["published_or_observed_date"] == "2026-06-01"


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "api_key",
        "auth_headers",
        "raw_provider_payload",
        "raw_search_response",
        "raw_content",
        "full_trace",
        "db_row",
        "evidence",
        "citation_records",
        "fap",
        "author_material",
        "content",
    ],
)
def test_reducer_rejects_forbidden_raw_private_or_authority_fields(
    forbidden_key: str,
) -> None:
    result = _official_result()
    result[forbidden_key] = "private"
    provider_results = _write_json(
        _provider_results_path(f"forbidden-{forbidden_key}"),
        _generic_provider_output([result]),
    )

    with pytest.raises(harness.LimitedLiveSearchCandidateError):
        harness.reduce_results(
            query=harness.DEFAULT_QUERY,
            provider_results_path=provider_results,
            output_dir=_output_dir(f"forbidden-{forbidden_key}"),
        )


def test_reducer_rejects_raw_retention_flags_true() -> None:
    envelope = _generic_provider_output([_official_result()])
    envelope["raw_provider_payload_retained"] = True
    provider_results = _write_json(
        _provider_results_path("raw-retention-envelope"),
        envelope,
    )

    with pytest.raises(harness.LimitedLiveSearchCandidateError, match="retained"):
        harness.reduce_results(
            query=harness.DEFAULT_QUERY,
            provider_results_path=provider_results,
            output_dir=_output_dir("raw-retention-envelope"),
        )

    result = _official_result()
    result["raw_search_response_retained"] = True
    provider_results = _write_json(
        _provider_results_path("raw-retention-result"),
        _generic_provider_output([result]),
    )

    with pytest.raises(harness.LimitedLiveSearchCandidateError, match="retained"):
        harness.reduce_results(
            query=harness.DEFAULT_QUERY,
            provider_results_path=provider_results,
            output_dir=_output_dir("raw-retention-result"),
        )


def test_downstream_surfaces_remain_explicitly_closed_false() -> None:
    out = _output_dir("closed-flags")
    provider_results = _write_json(
        _provider_results_path("closed-flags"),
        _generic_provider_output([_official_result()]),
    )

    harness.reduce_results(
        query=harness.DEFAULT_QUERY,
        provider_results_path=provider_results,
        output_dir=out,
    )

    candidate_packet = _read_json(out / "search_result_candidate_packet.json")
    record = candidate_packet["candidate_records"][0]
    for key, expected in FALSE_PACKET_FLAGS.items():
        assert candidate_packet[key] is expected
        assert record[key] is expected


def test_output_paths_must_stay_under_phase_output_dir() -> None:
    with pytest.raises(harness.LimitedLiveSearchCandidateError, match="output-dir"):
        harness.prepare_request(
            query=harness.DEFAULT_QUERY,
            output_dir=ROOT / "output" / "other_phase",
        )

    with pytest.raises(harness.LimitedLiveSearchCandidateError, match="paths"):
        harness.load_sanitized_provider_results(ROOT / "output" / "other.json")


def test_no_old_author_fap_pipeline_paths_are_imported_or_called() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "core.final_answer_packet_hardening_runtime",
        "core.author_prose_finalization_runtime",
        "core.sufficiency_readiness_runtime",
        "core.evidence_ledger_runtime",
        "core.fetch_read_content_reference",
    }
    assert _imports(SCRIPT).isdisjoint(forbidden_imports)
    source = SCRIPT.read_text(encoding="utf-8")
    for token in (
        "execute_author_action(",
        "reduce_hardened_final_answer_packet(",
        "reduce_author_prose_finalization(",
        "run_pipeline(",
        "pipeline_orchestrator",
    ):
        assert token not in source


def test_docs_and_packets_make_proof_mode_and_no_but_justified_explicit() -> None:
    out = _output_dir("posture")
    packet = harness.prepare_request(query=harness.DEFAULT_QUERY, output_dir=out)
    doc = DOC.read_text(encoding="utf-8")

    assert "Mode: PROOF" in doc
    assert "NO-BUT-JUSTIFIED" in doc
    assert "candidate acquisition only, not source survival" in doc
    assert packet["mode"] == "PROOF"
    assert packet["usable_answer_verdict_target"] == "NO-BUT-JUSTIFIED"
    assert packet["product_facing_progress_type"] == (
        "live-search-only validation with explicit live license"
    )


def test_live_provider_calls_are_not_run_in_pytest_or_ci() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "request.urlopen" not in source
    assert "subprocess." not in source
    assert "SERPER_API_KEY" not in source
    packet = harness.prepare_request(
        query=harness.DEFAULT_QUERY,
        output_dir=_output_dir("no-live"),
    )
    assert packet["request_generation_provider_free"] is True
    assert packet["live_provider_called"] is False


def test_operator_blocked_is_distinct_from_validation_inconclusive() -> None:
    packet = harness.prepare_request(
        query=harness.DEFAULT_QUERY,
        output_dir=_output_dir("blocked-distinct"),
    )

    assert packet["likely_acquisition_result"] == "validation_not_run_operator_blocked"
    assert "validation_inconclusive" in harness.LIKELY_ACQUISITION_RESULTS
    assert packet["likely_acquisition_result"] != "validation_inconclusive"
    assert packet["operator_blocked_status_is_distinct_from_inconclusive"] is True


def test_no_official_current_source_is_localized_as_acquisition_failure() -> None:
    out = _output_dir("no-official")
    provider_results = _write_json(
        _provider_results_path("no-official"),
        _generic_provider_output([_secondary_result()]),
    )

    packet = harness.reduce_results(
        query=harness.DEFAULT_QUERY,
        provider_results_path=provider_results,
        output_dir=out,
    )

    assert packet["search_result_candidate_packet_status"] == "built_and_validated"
    assert packet["likely_acquisition_result"] == "candidate_acquisition_fail"
    assert packet["likely_failure_layer_if_not_pass"] == (
        "official_current_source_acquisition"
    )
