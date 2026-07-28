from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from core import retained_live_artifact_preflight as retained_preflight
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


def _current_run_output_dir(name: str) -> Path:
    return ROOT / "output" / "ag_live_ordinary_search_candidate_01b" / name


def _provider_results_path(name: str) -> Path:
    return _output_dir(name) / "sanitized_provider_results.json"


def _current_run_provider_results_path(name: str) -> Path:
    return _current_run_output_dir(name) / "sanitized_provider_results.json"


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def _generic_provider_output(results: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_results = [
        {
            **result,
            "provider": "serper",
            "operation": "search.query",
        }
        for result in results
    ]
    return {
        "schema_version": "2",
        "proof_kind": "scryraven_search_query_proof_v2",
        "provider": "serper",
        "operation": "search.query",
        "status": "ok",
        "result_count": len(normalized_results),
        "results": normalized_results,
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
    assert (out / "search_candidate_packet.json").exists()
    assert packet["sanitized_provider_result_count"] == 5
    assert packet["provider_calls_attempted"] == 1
    assert packet["provider_calls_completed"] == 1
    assert packet["broker_invoked"] is True
    assert packet["live_provider_called"] is True
    assert packet["search_result_candidate_packet_status"] == "built_and_validated"
    assert packet["likely_acquisition_result"] == "candidate_acquisition_pass"
    assert packet["at_least_one_result_appears_official_current_government_source"] is True
    candidate_packet = _read_json(out / "search_result_candidate_packet.json")
    current_run_candidate_packet = _read_json(out / "search_candidate_packet.json")
    assert current_run_candidate_packet == candidate_packet
    assert candidate_packet["candidate_count"] == 5
    assert candidate_packet["candidate_records"][0]["domain"] == "travel.state.gov"


def test_reduce_results_accepts_current_run_output_dir_under_repo_output() -> None:
    out = _current_run_output_dir("reduce-pass")
    provider_results = _write_json(
        _current_run_provider_results_path("reduce-pass"),
        _generic_provider_output([_official_result()]),
    )

    packet = harness.reduce_results(
        query="current passport renewal fees official government site",
        provider_results_path=provider_results,
        output_dir=out,
    )

    assert (out / "validation_packet.json").exists()
    assert (out / "search_candidate_packet.json").exists()
    assert (out / "search_result_candidate_packet.json").exists()
    assert packet["search_candidate_packet_path"].endswith("search_candidate_packet.json")
    assert packet["search_result_candidate_packet_path"].endswith(
        "search_result_candidate_packet.json"
    )
    assert packet["search_result_candidate_packet_status"] == "built_and_validated"
    assert packet["provider_calls_attempted"] == 1
    assert packet["provider_calls_completed"] == 1
    assert packet["validation_reducer_provider_free"] is True


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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "old"),
        ("proof_kind", "legacy"),
        ("status", "failed"),
        ("physical_attempt_count", 0),
        ("caller_authorized_cost_ceiling_usd", "0.06"),
    ],
)
def test_reducer_rejects_nonexact_search_proof_attestation(
    field: str,
    value: object,
) -> None:
    payload = _generic_provider_output([_official_result()])
    payload[field] = value
    with pytest.raises(
        harness.LimitedLiveSearchCandidateError,
        match="proof attestation",
    ):
        harness._decode_sanitized_provider_results(payload)


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


def test_output_paths_must_stay_under_repo_local_output_dir(tmp_path: Path) -> None:
    out = ROOT / "output" / "other_phase"
    packet = harness.prepare_request(
        query=harness.DEFAULT_QUERY,
        output_dir=out,
    )

    assert (out / "request_packet.json").exists()
    assert packet["expected_output_paths"]["request_packet"].replace("\\", "/").startswith(
        "output/other_phase"
    )

    with pytest.raises(
        harness.LimitedLiveSearchCandidateError,
        match="repo-local output",
    ):
        harness.prepare_request(
            query=harness.DEFAULT_QUERY,
            output_dir=tmp_path / "outside-output",
        )

    with pytest.raises(
        harness.LimitedLiveSearchCandidateError,
        match="repo-local output",
    ):
        harness.load_sanitized_provider_results(tmp_path / "other.json")


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


def _retained_fixture(
    tmp_path: Path,
    name: str,
    *,
    provider_payload: Mapping[str, Any] | None = None,
) -> tuple[Path, Path]:
    source_dir = _output_dir(f"retained-preflight-{name}")
    provider_results = _write_json(
        source_dir / "sanitized_provider_results.json",
        provider_payload or _generic_provider_output([_official_result()]),
    )
    harness.reduce_results(
        query=harness.DEFAULT_QUERY,
        provider_results_path=provider_results,
        output_dir=source_dir,
    )

    repo = tmp_path / f"repo-{name}"
    retained = repo / "output" / harness.RETAINED_ARTIFACT_OUTPUT_DIR_NAME
    _write_json(
        retained / "sanitized_provider_results.json",
        provider_payload or _generic_provider_output([_official_result()]),
    )
    candidate = _read_json(source_dir / "search_result_candidate_packet.json")
    _write_json(retained / "search_candidate_packet.json", candidate)
    _write_json(retained / "search_result_candidate_packet.json", candidate)
    return repo, retained


def test_retained_artifact_preflight_passes_on_sanitized_repo_output_fixture(
    tmp_path: Path,
) -> None:
    repo, retained = _retained_fixture(tmp_path, "pass")

    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )

    assert result["decision"] == "PASS"
    assert result["artifact_dir"]["repo_relative_path"].replace("\\", "/") == (
        "output/ag_live_ordinary_search_candidate_01b"
    )
    assert result["artifact_dir"]["under_repo_output"] is True
    assert result["provider_result_count"] == 1
    assert result["candidate_count"] == 1
    assert result["raw_retention_flags"] == {
        "provider_results_raw_provider_payload_retained": False,
        "provider_results_raw_search_response_retained": False,
        "candidate_packet_raw_provider_payload_retained": False,
        "candidate_packet_raw_search_response_retained": False,
    }
    assert all(result["candidate_lineage_status"].values())
    assert result["closed_surfaces_not_invoked"] == {
        "provider_calls": 0,
        "broker_calls": 0,
        "fetch_read_calls": 0,
        "retrieval_calls": 0,
        "model_calls": 0,
        "evidence_ledger_admissions": 0,
        "citation_operations": 0,
        "sufficiency_fap_author_operations": 0,
    }


def test_ag_script_preflight_command_remains_operator_wrapper(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, retained = _retained_fixture(tmp_path, "script-compat")

    assert harness.preflight_retained_live_artifacts is (
        retained_preflight.preflight_retained_live_artifacts
    )
    result = harness.main(
        [
            "preflight-retained-artifacts",
            "--repo-root",
            str(repo),
            "--artifact-dir",
            str(retained),
        ]
    )

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["decision"] == "PASS"


def test_retained_artifact_preflight_missing_files_are_named_blocker(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "missing-repo"
    retained = repo / "output" / harness.RETAINED_ARTIFACT_OUTPUT_DIR_NAME

    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )

    assert result["decision"] == "BLOCKED_LOCAL_ARTIFACT_MISSING"
    assert result["missing_artifacts"] == list(
        retained_preflight.RETAINED_ARTIFACT_REQUIRED_NAMES
    )

    repo, retained = _retained_fixture(tmp_path, "missing-file")
    (retained / "search_candidate_packet.json").unlink()
    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )

    assert result["decision"] == "BLOCKED_LOCAL_ARTIFACT_MISSING"
    assert result["missing_artifacts"] == ["search_candidate_packet.json"]


def test_retained_artifact_preflight_unreadable_or_invalid_json_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, retained = _retained_fixture(tmp_path, "unreadable")

    def unreadable(path: Path) -> bool:
        return path.name != "sanitized_provider_results.json"

    monkeypatch.setattr(retained_preflight, "_read_permission", unreadable)
    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )

    assert result["decision"] == "BLOCKED_LOCAL_ARTIFACT_UNREADABLE"
    assert result["unreadable_artifacts"] == ["sanitized_provider_results.json"]

    repo, retained = _retained_fixture(tmp_path, "invalid-json")
    (retained / "sanitized_provider_results.json").write_text(
        "{not json",
        encoding="utf-8",
    )
    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )

    assert result["decision"] == "BLOCKED_LOCAL_ARTIFACT_UNREADABLE"
    assert result["unreadable_artifacts"] == ["sanitized_provider_results.json"]


def test_retained_artifact_preflight_rejects_paths_outside_repo_output(
    tmp_path: Path,
) -> None:
    repo, _retained = _retained_fixture(tmp_path, "outside-output")
    outside = repo / "not-output" / harness.RETAINED_ARTIFACT_OUTPUT_DIR_NAME

    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=outside,
        repo_root=repo,
    )

    assert result["decision"] == "BLOCKED_OUTPUT_BOUNDARY"
    assert result["artifact_dir"]["under_repo_output"] is False


def test_retained_artifact_preflight_rejects_raw_private_and_retention_flags(
    tmp_path: Path,
) -> None:
    repo, retained = _retained_fixture(tmp_path, "raw-private")
    payload = _generic_provider_output([_official_result()])
    payload["results"][0]["raw_provider_payload"] = "private"
    _write_json(retained / "sanitized_provider_results.json", payload)

    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )

    assert result["decision"] == "BLOCKED_RAW_OR_PRIVATE_FIELD"

    repo, retained = _retained_fixture(tmp_path, "raw-retention")
    payload = _generic_provider_output([_official_result()])
    payload["raw_search_response_retained"] = True
    _write_json(retained / "sanitized_provider_results.json", payload)

    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )

    assert result["decision"] == "BLOCKED_RETENTION_FLAG"


def test_retained_artifact_preflight_detects_path_mismatch_without_alt_content_read(
    tmp_path: Path,
) -> None:
    active_repo = tmp_path / "ScryRaven"
    alt_repo, _retained = _retained_fixture(tmp_path, "path-mismatch")

    result = retained_preflight.preflight_retained_live_artifacts(
        repo_root=active_repo,
        alternate_repo_roots=[alt_repo],
    )

    assert result["decision"] == "BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH"
    assert result["missing_artifacts"] == list(
        retained_preflight.RETAINED_ARTIFACT_REQUIRED_NAMES
    )
    assert result["alternate_artifact_locations"][0]["all_required_artifacts_exist"] is True
    assert result["alternate_artifact_locations"][0]["contents_read"] is False
    alt_metadata = result["alternate_artifact_locations"][0]["artifact_metadata"]
    assert "top_level_keys" not in alt_metadata["sanitized_provider_results.json"]


def test_retained_artifact_preflight_rejects_candidate_lineage_mismatch(
    tmp_path: Path,
) -> None:
    repo, retained = _retained_fixture(tmp_path, "lineage")
    packet = _read_json(retained / "search_candidate_packet.json")
    packet["candidate_records"] = []
    packet["candidate_count"] = 0
    _write_json(retained / "search_candidate_packet.json", packet)

    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )

    assert result["decision"] == "BLOCKED_CANDIDATE_LINEAGE"


def test_retained_artifact_preflight_summary_omits_full_artifact_contents(
    tmp_path: Path,
) -> None:
    repo, retained = _retained_fixture(tmp_path, "metadata-only")

    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )
    encoded = json.dumps(result, sort_keys=True)

    assert "Passport Fees" not in encoded
    assert "Official passport book renewal fee information" not in encoded
    assert "https://travel.state.gov/content/travel/en/passports/how-apply/fees.html" not in encoded
    assert result["artifact_metadata"]["sanitized_provider_results.json"][
        "top_level_keys"
    ] == [
        "caller_authorized_cost_ceiling_usd",
        "operation",
        "physical_attempt_count",
        "proof_kind",
        "provider",
        "provider_elapsed_milliseconds_total",
        "raw_provider_payload_retained",
        "raw_request_material_retained",
        "raw_response_material_retained",
        "raw_search_response_retained",
        "result_count",
        "results",
        "schema_version",
        "status",
    ]


def test_retained_artifact_preflight_callable_is_future_fetch_read_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, retained = _retained_fixture(tmp_path, "future-gate")
    closed_calls: list[str] = []

    def forbidden_front_half(*_args: Any, **_kwargs: Any) -> None:
        closed_calls.append("front_half")
        raise AssertionError("preflight must not build or reduce live validation")

    monkeypatch.setattr(harness, "build_front_half", forbidden_front_half)

    result = retained_preflight.preflight_retained_live_artifacts(
        artifact_dir=retained,
        repo_root=repo,
    )

    assert result["decision"] == "PASS"
    assert closed_calls == []
    assert result["closed_surfaces_not_invoked"]["fetch_read_calls"] == 0
