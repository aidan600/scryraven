from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import proplex.__main__ as compatibility_cli  # noqa: E402
from core.searchos_iterative_judgment_runtime import (  # noqa: E402
    SEARCHOS_OWNER,
    SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
    SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION,
)
from core.searchos_slice_a_product_runtime import (  # noqa: E402
    SEARCHOS_SLICE_A_TRACE_KEY,
    build_bounded_searchos_n1_causal_projection,
)
from core.validation_profiles import (  # noqa: E402
    AG_LIVE_MULTI_COMPONENT,
    MULTI_COMPONENT_DOCS_DOMAINS,
    get_validation_profile,
)

RUNNER_PATH = ROOT / "scripts" / "ag_live_bound_01_bounded_product_runner.py"
SUPPORT_PATH = ROOT / "scripts" / "ag_live_bound_01_support.py"
DEFAULT_OUTPUT = ROOT / "output" / "ag_live_bound_01_packet.json"

PRIMARY_QUERY = (
    "According to the official Python 3 documentation, what are the default "
    "values for rel_tol and abs_tol in math.isclose()?"
)
VALID_ARGS = [
    "--query",
    PRIMARY_QUERY,
    "--mode",
    "Balanced",
    "--include-domains",
    "docs.python.org",
    "--output",
    "output/ag_live_bound_01_packet.json",
]


def _ensure_scripts_package() -> None:
    if "scripts" not in sys.modules:
        scripts_pkg = ModuleType("scripts")
        scripts_pkg.__path__ = [str(ROOT / "scripts")]  # type: ignore[attr-defined]
        sys.modules["scripts"] = scripts_pkg


def _load_module(path: Path, module_name: str) -> ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]
    _ensure_scripts_package()
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_runner() -> ModuleType:
    return _load_module(
        RUNNER_PATH,
        "scripts.ag_live_bound_01_bounded_product_runner",
    )


def _load_support() -> ModuleType:
    return _load_module(SUPPORT_PATH, "scripts.ag_live_bound_01_support")


def _gitignored_output_path(name: str) -> str:
    return f"output/{name}"


def _stub_live_runner_without_env(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_load_live_environment", lambda: None)
    monkeypatch.setattr(runner, "_validate_live_model_keys", lambda: None)
    monkeypatch.setattr(runner, "_build_live_run_deps", lambda: SimpleNamespace())
    import core.quantitative_specialist_product_activation as product_activation

    monkeypatch.setattr(
        product_activation,
        "compose_quantitative_specialist_product_deps",
        lambda deps: deps,
    )
    monkeypatch.setattr(
        runner,
        "_live_runtime_helpers",
        lambda: (SimpleNamespace(), SimpleNamespace()),
    )

    def fake_run_config(context: Any, *, cap_policy: Any) -> Any:
        return SimpleNamespace(
            query=context.query,
            mode=context.mode,
            fast_provider="FixtureFastProvider",
            fast_model="fixture-fast-model",
            smart_provider="FixtureSmartProvider",
            smart_model="fixture-smart-model",
            embed_provider="FixtureEmbedProvider",
            embed_model="fixture-embed-model",
            cap_policy=cap_policy,
        )

    monkeypatch.setattr(runner, "_build_live_run_config", fake_run_config)


@pytest.fixture(autouse=True)
def _cleanup_output_packets() -> Any:
    yield
    for path in ROOT.glob("output/ag_live_bound_01*.json"):
        if path.exists():
            path.unlink()


def test_dry_run_writes_sanitized_packet(tmp_path: Path) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_dry_run_packet.json")

    result = runner.main([*VALID_ARGS, "--output", output])

    assert result == 0
    packet_path = ROOT / output
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["dry_run"] is True
    assert packet["confirm_live_product_run"] is False
    assert packet["planned_live_dispatch"] is False
    assert packet["validation_profile"]["name"] == "AG-LIVE-SMOKE"
    assert packet["validation_profile"]["live_status"] == (
        "succeeded_once_direct_human_private_shell"
    )
    assert packet["validation_profile"]["cap_policy_surface"] == "RunConfig.cap_policy"
    assert "run_pipeline_call_count == 1 on live success" in packet[
        "expected_packet_criteria"
    ]
    assert packet["packet_marker"] == "LOCAL/UNTRACKED — DO NOT COMMIT"
    assert packet["caps_requested"] == {
        "max_scryraven_runs": 1,
        "max_retries": 0,
    }
    assert packet["caps_observed"]["enforcement"] == "not_executed"
    assert packet["cap_enforcement_product_path"] == {
        "policy_surface": "RunConfig.cap_policy",
        "runtime_consumer": "run_pipeline",
        "script_owns_cap_authority": False,
        "product_policy_constructible": True,
    }


def test_dry_run_never_calls_run_pipeline(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_no_pipeline.json")

    with patch("core.pipeline_orchestrator.run_pipeline") as run_pipeline:
        result = runner.main([*VALID_ARGS, "--output", output])

    run_pipeline.assert_not_called()
    assert result == 0
    capsys.readouterr()


def test_confirm_live_with_missing_live_env_fails_before_run_pipeline(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_confirm_missing_env.json")

    monkeypatch.setattr(runner, "_load_live_environment", lambda: None)

    def fail_missing_env() -> None:
        support = _load_support()
        raise support.AgLiveBoundPreflightError("missing required live environment variable(s): OPENAI_API_KEY")

    monkeypatch.setattr(runner, "_validate_live_model_keys", fail_missing_env)

    with patch("core.pipeline_orchestrator.run_pipeline") as run_pipeline:
        result = runner.main(
            [
                *VALID_ARGS,
                "--output",
                output,
                "--confirm-live-product-run",
            ]
        )

    run_pipeline.assert_not_called()
    captured = capsys.readouterr()
    assert result == 2
    assert "missing required live environment variable" in captured.err

    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    assert packet["confirm_live_product_run"] is True
    assert packet["planned_live_dispatch"] is False
    assert packet["success_classification"] == "precheck_failure"
    assert packet["run_pipeline_call_count"] == 0
    assert packet["failure_summary"]["reason"] == (
        "missing required live environment variable(s): OPENAI_API_KEY"
    )


def test_run_pipeline_value_error_writes_sanitized_failure_observability(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_value_error.json")
    _stub_live_runner_without_env(runner, monkeypatch)

    def fail_run_pipeline(
        _config: Any,
        _deps: Any,
        _status: Any,
        _accumulator: Any,
    ) -> Any:
        raise ValueError("safe synthetic failure")

    with patch(
        "core.pipeline_orchestrator.run_pipeline",
        side_effect=fail_run_pipeline,
    ) as run_pipeline:
        result = runner.main(
            [*VALID_ARGS, "--output", output, "--confirm-live-product-run"]
        )

    assert result == 2
    assert run_pipeline.call_count == 1
    capsys.readouterr()

    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    assert packet["success_classification"] == "unexpected_failure"
    assert packet["planned_live_dispatch"] is True
    assert packet["run_pipeline_call_count"] == 1
    assert packet["failure_summary"]["reason"] == "ValueError"
    assert packet["failure_summary"]["safe_phase"] == "run_pipeline"
    assert packet["failure_summary"]["safe_error_type"] == "ValueError"
    assert packet["failure_summary"]["safe_error_code"] == (
        "run_pipeline_value_error"
    )
    assert packet["failure_summary"]["safe_error_message"] == (
        "safe synthetic failure"
    )

    observability = packet["failure_observability"]
    assert observability == {
        "schema_version": "ag_live_failure_observability_v1",
        "safe_phase": "run_pipeline",
        "safe_error_type": "ValueError",
        "safe_error_code": "run_pipeline_value_error",
        "safe_error_message": "safe synthetic failure",
        "safe_error_message_redacted": False,
        "raw_traceback_retained": False,
        "raw_exception_repr_retained": False,
        "raw_provider_payload_retained": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "private_logs_retained": False,
        "db_cache_rows_retained": False,
        "secrets_returned": False,
    }
    assert packet["no_retention"]["raw_provider_payloads_retained"] is False
    assert packet["no_retention"]["raw_prompts_retained"] is False
    assert packet["no_retention"]["full_raw_traces_retained"] is False
    assert packet["validation_observability"]["raw_private_material_serialized"] is False
    assert "subject_budget_summary" in packet["validation_observability"]
    rendered = json.dumps(packet, sort_keys=True)
    assert "Traceback" not in rendered
    assert '"raw_prompt":' not in rendered
    assert '"provider_payload":' not in rendered
    assert '"model_response":' not in rendered
    support = _load_support()
    support.reject_forbidden_packet(packet)


def test_run_pipeline_sensitive_value_error_message_is_redacted(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_sensitive_value_error.json")
    _stub_live_runner_without_env(runner, monkeypatch)
    sensitive_message = "OPENAI_API_KEY=sk-secret raw_prompt provider_payload"

    def fail_run_pipeline(
        _config: Any,
        _deps: Any,
        _status: Any,
        _accumulator: Any,
    ) -> Any:
        raise ValueError(sensitive_message)

    with patch(
        "core.pipeline_orchestrator.run_pipeline",
        side_effect=fail_run_pipeline,
    ):
        result = runner.main(
            [*VALID_ARGS, "--output", output, "--confirm-live-product-run"]
        )

    assert result == 2
    capsys.readouterr()

    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    observability = packet["failure_observability"]
    assert observability["safe_phase"] == "run_pipeline"
    assert observability["safe_error_type"] == "ValueError"
    assert observability["safe_error_code"] == "run_pipeline_value_error"
    assert observability["safe_error_message"] is None
    assert observability["safe_error_message_redacted"] is True
    assert packet["failure_summary"]["safe_error_message"] is None
    assert packet["failure_summary"]["safe_error_message_redacted"] is True
    rendered = json.dumps(packet, sort_keys=True)
    assert sensitive_message not in rendered
    assert "OPENAI_API_KEY=sk-secret" not in rendered
    assert "sk-secret" not in rendered


def test_confirm_live_constructs_cap_policy_and_calls_run_pipeline_once(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_confirm_success.json")
    captured_config: dict[str, Any] = {}
    attempted_execution_log = tmp_path / "ordinary_execution.jsonl"
    attempted_kb_log = tmp_path / "ordinary_kb.jsonl"

    monkeypatch.setattr(runner, "_load_live_environment", lambda: None)
    monkeypatch.setattr(runner, "_validate_live_model_keys", lambda: None)
    monkeypatch.setattr(
        runner,
        "_live_model_config",
        lambda: {
            "fast_provider": "FixtureFastProvider",
            "fast_model": "fixture-fast-model",
            "smart_provider": "FixtureSmartProvider",
            "smart_model": "fixture-smart-model",
            "embed_provider": "FixtureEmbedProvider",
            "embed_model": "fixture-embed-model",
            "local_url": "http://localhost:1234/v1",
        },
    )

    def fake_run_pipeline(config: Any, _deps: Any, _status: Any, _accumulator: Any) -> Any:
        import core.persistence_side_effects as persistence
        import core.pipeline_orchestrator as orchestrator

        captured_config["config"] = config
        assert config.cap_policy is not None
        assert orchestrator.DB_ENABLED is False
        config.cap_policy.mark_search_dispatch()
        orchestrator.log_run_started(
            run_id="would-log",
            session_id="would-log-session",
            phase="pipeline",
            query="would write if not suppressed",
            path=attempted_execution_log,
        )
        persistence.append_jsonl(attempted_kb_log, {"event": "would_log"})
        persistence_result = orchestrator.execute_persistence_side_effects(
            execution_log_path=attempted_execution_log,
            execution_log_entry={"event": "would_log_execution_trace"},
            run_id="would-log",
            session_id="would-log-session",
            latency_seconds=0.0,
            strategy="Balanced",
            execution_trace={"timing": {}},
            run_log=_NoopLogger(),
            policy_journal_path=tmp_path / "ordinary_policy.jsonl",
            policy_applied={},
            default_utilization_threshold=0.25,
            ts_utc="2026-06-25T00:00:00Z",
            query="would write if not suppressed",
            kb_context=None,
            db_enabled=True,
        )
        assert persistence_result.sqlite_row_written is False
        return SimpleNamespace(
            report="The defaults are rel_tol=1e-09 and abs_tol=0.0. [[1]](https://docs.python.org/3/library/math.html#math.isclose)",
            top_passages=[
                {
                    "source_id": 1,
                    "url": "https://docs.python.org/3/library/math.html#math.isclose",
                    "text": "not serialized",
                }
            ],
            seen_urls=["https://docs.python.org/3/library/math.html#math.isclose"],
            execution_trace={
                "final_answer_source_ids_used": ["1"],
                "evidence_sufficient": True,
                "synth_was_insufficient": False,
                "synth_sufficient_first_pass": True,
                "answer_class": "direct_answer",
                "response_displayable": True,
                "author_system_prompt_key": "default",
                "failure_card": {"show": False, "reason": None},
                "final_answer_packet": {
                    "canonical_state": True,
                    "trace_mode": "run_kernel_final_answer_packet_projection",
                    "readiness_status": "author_ready",
                    "author_payload_status": "author_input_ready",
                    "citation_eligible_source_ids": ["1"],
                    "sufficiency_decision": "sufficient",
                    "semantic_evidence_authority_manifest": {
                        "semantic_packet_evidence_binding_available": True,
                        "semantic_packet_evidence_binding_count": 1,
                        "content_refs_available": True,
                        "coverage_refs_available": True,
                    },
                    "semantic_content_coverage_ref": {
                        "component_ref_count": 1,
                        "coverage_record_ref_count": 1,
                        "semantic_observation_ref_count": 1,
                        "sanitized_content_ref_count": 1,
                    },
                },
            },
        )

    with patch("core.pipeline_orchestrator.run_pipeline", side_effect=fake_run_pipeline) as run_pipeline:
        result = runner.main([*VALID_ARGS, "--output", output, "--confirm-live-product-run"])

    assert result == 0
    assert run_pipeline.call_count == 1
    default_policy = _load_support().AgLiveBoundCaps().to_run_cap_policy()
    assert captured_config["config"].cap_policy.max_search_dispatches == (
        default_policy.max_search_dispatches
    )
    assert captured_config["config"].cap_policy.max_fetch_read_operations == (
        default_policy.max_fetch_read_operations
    )
    assert captured_config["config"].cap_policy.max_author_model_calls == (
        default_policy.max_author_model_calls
    )
    assert captured_config[
        "config"
    ].cap_policy.max_smart_search_judgment_model_calls == (
        default_policy.max_smart_search_judgment_model_calls
    )
    assert captured_config["config"].cap_policy.max_retries == 0
    assert attempted_execution_log.exists() is False
    assert attempted_kb_log.exists() is False
    captured = capsys.readouterr()
    assert "wrote sanitized AG-LIVE-BOUND live packet" in captured.out

    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    assert packet["phase_id"] == "AG-LIVE-EXEC-01"
    assert packet["validation_profile"]["name"] == "AG-LIVE-SMOKE"
    assert packet["success_classification"] == "success"
    assert packet["run_pipeline_call_count"] == 1
    assert packet["caps_observed"]["search_dispatches"] == 1
    assert packet["final_answer_text"].startswith("The defaults are")
    assert packet["cited_source_ids"] == ["1"]
    assert packet["cited_urls"] == [
        "https://docs.python.org/3/library/math.html#math.isclose"
    ]
    assert packet["sanitized_projection_summaries"]["component_binding"][
        "semantic_packet_evidence_binding_count"
    ] == 1
    observability = packet["validation_observability"]
    assert observability["model_invocation_summary"]["fast_provider"] == (
        "FixtureFastProvider"
    )
    assert observability["model_invocation_summary"]["fast_model"] == (
        "fixture-fast-model"
    )
    assert observability["model_invocation_summary"]["embed_model"] == (
        "fixture-embed-model"
    )
    assert observability["cap_and_retention_summary"]["caps_observed"][
        "search_dispatches"
    ] == 1
    assert observability["source_material_summary"]["cited_urls"] == [
        "https://docs.python.org/3/library/math.html#math.isclose"
    ]
    assert packet["retention_posture"] == {
        "ordinary_product_persistence": "suppressed_for_ag_live_bound_runner",
        "only_runner_artifact_written": True,
        "sanitized_packet_path": packet["output_path"],
        "ordinary_execution_jsonl_suppressed": True,
        "ordinary_kb_trigger_jsonl_suppressed": True,
        "ordinary_policy_journal_jsonl_suppressed": True,
        "sqlite_telemetry_suppressed": True,
        "ordinary_side_effect_paths_suppressed": [
            "output/ag_live_bound_01_execution_log.jsonl",
            "output/ag_live_bound_01_kb_triggers.jsonl",
            "output/ag_live_bound_01_policy_journal.jsonl",
            "proplex.db",
        ],
    }
    assert packet["no_retention"]["private_logs_retained"] is False
    assert packet["no_retention"]["db_cache_rows_retained_in_packet"] is False
    assert packet["no_retention"]["full_raw_traces_retained"] is False
    rendered_packet = json.dumps(packet, sort_keys=True)
    assert "not serialized" not in rendered_packet
    assert '"raw_prompt":' not in rendered_packet
    assert '"provider_payload":' not in rendered_packet
    assert '"model_response":' not in rendered_packet
    assert '"execution_trace":' not in rendered_packet


def test_source_custody_profile_is_not_executable() -> None:
    support = _load_support()
    with pytest.raises(
        support.AgLiveBoundPreflightError,
        match="not direct-runner ready",
    ):
        support.build_preflight_context(
            root=ROOT,
            profile_name="AG-LIVE-SOURCE-CUSTODY",
            query=PRIMARY_QUERY,
            mode="Balanced",
            include_domains=["docs.python.org"],
            output_path=ROOT / "output" / "ag_live_bound_01_source_custody.json",
            caps=support.AgLiveBoundCaps(),
            run_id="ag-live-source-custody-config-test",
            confirm_live_product_run=True,
            approved_backup_query=False,
        )

    product_path = support.source_custody_policy_product_path(
        "AG-LIVE-SOURCE-CUSTODY"
    )
    assert product_path["policy_enabled"] is False
    assert product_path["product_policy_constructible"] is False
    assert product_path["initial_discovery_transport_authority"] is False


def test_confirm_live_cap_overflow_writes_sanitized_failure_packet(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_confirm_cap_overflow.json")

    monkeypatch.setattr(runner, "_load_live_environment", lambda: None)
    monkeypatch.setattr(runner, "_validate_live_model_keys", lambda: None)

    def fake_run_pipeline(config: Any, _deps: Any, _status: Any, _accumulator: Any) -> Any:
        config.cap_policy.mark_search_dispatch()
        config.cap_policy.mark_search_dispatch()
        config.cap_policy.mark_search_dispatch()

    with patch("core.pipeline_orchestrator.run_pipeline", side_effect=fake_run_pipeline) as run_pipeline:
        result = runner.main(
            [
                *VALID_ARGS,
                "--output",
                output,
                "--max-search-dispatches",
                "2",
                "--confirm-live-product-run",
            ]
        )

    assert result == 2
    assert run_pipeline.call_count == 1
    capsys.readouterr()

    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    assert packet["success_classification"] == "cap_overflow"
    assert packet["run_pipeline_call_count"] == 1
    assert packet["caps_observed"]["search_dispatches"] == 2
    assert packet["failure_summary"]["reason"] == "search_dispatches cap exceeded"
    assert packet["failure_summary"]["classification"] == "cap_overflow"
    assert packet["failure_summary"]["safe_phase"] == "run_pipeline"
    assert packet["failure_summary"]["safe_error_type"] == "RunCapExceeded"
    assert packet["failure_observability"]["safe_error_code"] == (
        "run_pipeline_run_cap_exceeded"
    )


def test_confirm_live_pipeline_error_keeps_pipeline_failure_classification(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_pipeline_error.json")
    _stub_live_runner_without_env(runner, monkeypatch)
    pipeline_error_type = runner._pipeline_error_type()

    def fail_run_pipeline(
        _config: Any,
        _deps: Any,
        _status: Any,
        _accumulator: Any,
    ) -> Any:
        raise pipeline_error_type("safe pipeline failure")

    with patch(
        "core.pipeline_orchestrator.run_pipeline",
        side_effect=fail_run_pipeline,
    ) as run_pipeline:
        result = runner.main(
            [*VALID_ARGS, "--output", output, "--confirm-live-product-run"]
        )

    assert result == 2
    assert run_pipeline.call_count == 1
    capsys.readouterr()

    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    assert packet["success_classification"] == "pipeline_failure"
    assert packet["failure_summary"]["classification"] == "pipeline_failure"
    assert packet["failure_summary"]["reason"] == "safe pipeline failure"
    assert packet["failure_observability"]["safe_phase"] == "run_pipeline"
    assert packet["failure_observability"]["safe_error_type"] == "PipelineError"
    assert packet["failure_observability"]["safe_error_code"] == (
        "run_pipeline_pipeline_error"
    )
    assert "blocked_fap_summary" not in packet["failure_observability"]
    assert "blocked_fap_summary" not in packet["sanitized_projection_summaries"]


def test_confirm_live_blocked_fap_pipeline_error_serializes_safe_summary(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    support = _load_support()
    output = _gitignored_output_path("ag_live_bound_01_blocked_fap_error.json")
    _stub_live_runner_without_env(runner, monkeypatch)
    pipeline_error_type = runner._pipeline_error_type()
    blocked_summary = {
        "schema_version": "blocked_final_answer_packet_safe_summary_v1",
        "blocked_fap": True,
        "packet_id": "final-answer-packet-safe",
        "status": "blocked",
        "readiness_status": "blocked",
        "readiness_reasons": [
            "missing_required_component_coverage",
            "final_answer_not_allowed",
        ],
        "author_input_deferred": True,
        "blocked_before_author_input": True,
        "final_answer_allowed": False,
        "final_answer_posture": "insufficient_answer",
        "sufficiency_decision": "insufficient_evidence",
        "missing_source_obligation_count": 2,
        "partial_source_obligation_count": 1,
        "satisfied_source_obligation_count": 0,
        "source_bound_numeric_unknown_count": 0,
        "mandatory_caveat_count": 1,
        "prohibited_upgrade_count": 2,
        "claim_postures": ["insufficient_answer"],
        "component_blocked_summary": {
            "schema_version": "blocked_fap_component_summary_v1",
            "component_summary_available": True,
            "expected_component_count": 3,
            "expected_answerable_component_count": 3,
            "supported_component_count": 2,
            "citation_bound_component_count": 0,
            "evidence_bound_component_count": 0,
            "source_obligation_satisfied_component_count": 0,
            "missing_component_count": 1,
            "expected_answerable_missing_component_count": 1,
            "unsupported_component_count": 0,
            "unclear_component_count": 0,
            "entangled_component_count": 0,
            "source_bound_numeric_unknown_component_count": 0,
            "full_component_success": False,
            "partial_user_answer_candidate": False,
            "semantic_partial_coverage_observed": True,
            "hard_block_candidate": True,
            "components": [
                {
                    "component_id": "component:supported-one",
                    "safe_label": "supported-one",
                    "status": "supported",
                    "expected_answerable": True,
                    "answered_or_answerable_from_evidence": False,
                    "blocker_reason_codes": [],
                    "satisfied_source_obligation_count": 0,
                    "missing_source_obligation_count": 0,
                    "partial_source_obligation_count": 0,
                    "citation_binding_available": False,
                    "evidence_binding_available": False,
                    "raw_prompt": "nested must not serialize",
                },
                {
                    "component_id": "component:missing-one",
                    "status": "missing",
                    "expected_answerable": True,
                    "answered_or_answerable_from_evidence": False,
                    "blocker_reason_codes": ["missing_required_component_coverage"],
                    "satisfied_source_obligation_count": 0,
                    "missing_source_obligation_count": 1,
                    "partial_source_obligation_count": 0,
                    "citation_binding_available": False,
                    "evidence_binding_available": False,
                    "provider_payload": "nested must not serialize",
                },
            ],
            "model_response": "nested must not serialize",
        },
        "raw_prompt": "must not serialize",
    }

    def fail_run_pipeline(
        _config: Any,
        _deps: Any,
        _status: Any,
        _accumulator: Any,
    ) -> Any:
        raise pipeline_error_type(
            "blocked FinalAnswerPacket cannot proceed to Author handoff",
            blocked_fap_summary=blocked_summary,
        )

    with patch(
        "core.pipeline_orchestrator.run_pipeline",
        side_effect=fail_run_pipeline,
    ) as run_pipeline:
        result = runner.main(
            [*VALID_ARGS, "--output", output, "--confirm-live-product-run"]
        )

    assert result == 2
    assert run_pipeline.call_count == 1
    capsys.readouterr()

    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    assert packet["success_classification"] == "pipeline_failure"
    assert packet["failure_observability"]["safe_error_type"] == "PipelineError"
    assert packet["failure_observability"]["safe_error_code"] == (
        "run_pipeline_pipeline_error"
    )
    observed = packet["failure_observability"]["blocked_fap_summary"]
    assert observed["blocked_fap"] is True
    assert observed["readiness_status"] == "blocked"
    assert observed["author_input_deferred"] is True
    assert observed["blocked_before_author_input"] is True
    assert observed["missing_source_obligation_count"] == 2
    assert observed["partial_source_obligation_count"] == 1
    assert observed["mandatory_caveat_count"] == 1
    assert observed["prohibited_upgrade_count"] == 2
    component_summary = observed["component_blocked_summary"]
    assert component_summary["expected_component_count"] == 3
    assert component_summary["supported_component_count"] == 2
    assert component_summary["missing_component_count"] == 1
    assert component_summary["expected_answerable_missing_component_count"] == 1
    assert component_summary["full_component_success"] is False
    assert component_summary["partial_user_answer_candidate"] is False
    assert component_summary["semantic_partial_coverage_observed"] is True
    assert component_summary["hard_block_candidate"] is True
    assert "model_response" not in component_summary
    component_entries = component_summary["components"]
    assert {item["status"] for item in component_entries} == {"supported", "missing"}
    assert all(
        item["answered_or_answerable_from_evidence"] is False
        for item in component_entries
        if item["status"] == "supported"
    )
    assert all("raw_prompt" not in item for item in component_entries)
    assert all("provider_payload" not in item for item in component_entries)
    assert "raw_prompt" not in observed
    assert packet["sanitized_projection_summaries"]["blocked_fap_summary"] == observed
    assert packet["sanitized_projection_summaries"]["blocked_fap_summary"][
        "component_blocked_summary"
    ] == component_summary
    assert packet["failure_summary"]["blocked_fap"] is True
    assert packet["failure_summary"]["blocked_fap_readiness_status"] == "blocked"
    assert packet["validation_observability"]["subject_budget_summary"][
        "subject_budget_enabled"
    ] is False
    rendered = json.dumps(packet, sort_keys=True)
    assert "must not serialize" not in rendered
    assert "nested must not serialize" not in rendered
    assert "Traceback" not in rendered
    assert '"raw_prompt":' not in rendered
    assert '"provider_payload":' not in rendered
    support.reject_forbidden_packet(packet)


def test_multi_component_failure_without_outcome_keeps_subject_budget_fallback() -> None:
    support = _load_support()
    profile = get_validation_profile(AG_LIVE_MULTI_COMPONENT)
    context = support.build_preflight_context(
        root=ROOT,
        profile_name=AG_LIVE_MULTI_COMPONENT,
        query=profile.primary_query,
        mode="Balanced",
        include_domains=list(MULTI_COMPONENT_DOCS_DOMAINS),
        output_path=ROOT / "output" / "ag_live_bound_01_multi_failure.json",
        caps=support.AgLiveBoundCaps(),
        run_id="ag-live-multi-failure-test",
        confirm_live_product_run=True,
        approved_backup_query=False,
    )
    packet = support.build_live_failure_packet(
        context,
        cap_policy=context.caps.to_run_cap_policy(),
        classification="unexpected_failure",
        failure_reason="ValueError",
        run_pipeline_call_count=1,
        run_config=None,
        outcome=None,
        failure_observability=support.build_failure_observability(
            safe_phase="run_pipeline",
            exc=ValueError("safe synthetic failure"),
        ),
    )

    subject_budget = packet["validation_observability"]["subject_budget_summary"]
    assert packet["validation_profile"]["name"] == AG_LIVE_MULTI_COMPONENT
    assert subject_budget["subject_budget_enabled"] is True
    assert subject_budget["detected_subject_count"] == 0
    assert subject_budget["subject_selection_source"] == "not_available"
    assert "detected_subjects_not_available" in str(subject_budget["diagnosis"])
    support.reject_forbidden_packet(packet)


def test_multi_component_four_domain_allowlist_preflight_stays_bounded() -> None:
    support = _load_support()
    profile = get_validation_profile(AG_LIVE_MULTI_COMPONENT)

    context = support.build_preflight_context(
        root=ROOT,
        profile_name=AG_LIVE_MULTI_COMPONENT,
        query=profile.primary_query,
        mode="Balanced",
        include_domains=list(MULTI_COMPONENT_DOCS_DOMAINS),
        output_path=ROOT / "output" / "ag_live_bound_01_multi_preflight.json",
        caps=support.AgLiveBoundCaps(),
        run_id="ag-live-multi-preflight-test",
        confirm_live_product_run=True,
        approved_backup_query=False,
    )

    assert context.include_domains == list(MULTI_COMPONENT_DOCS_DOMAINS)
    with pytest.raises(support.AgLiveBoundPreflightError, match="mongodb.com"):
        support.build_preflight_context(
            root=ROOT,
            profile_name=AG_LIVE_MULTI_COMPONENT,
            query=profile.primary_query,
            mode="Balanced",
            include_domains=["postgresql.org", "dev.mysql.com", "redis.io"],
            output_path=ROOT / "output" / "ag_live_bound_01_multi_missing.json",
            caps=support.AgLiveBoundCaps(),
            run_id="ag-live-multi-preflight-missing-test",
            confirm_live_product_run=True,
            approved_backup_query=False,
        )


class _NoopLogger:
    def warning(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def test_unsafe_output_path_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()

    result = runner.main(
        [
            *VALID_ARGS,
            "--output",
            str(ROOT / "docs" / "ag_live_bound_01_packet.json"),
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "output path must be under ignored repo output/" in captured.err


def test_tracked_output_path_blocks(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()

    def fake_gitignored(_root: Path, _path: Path) -> bool:
        return False

    monkeypatch.setattr(
        "scripts.ag_live_bound_01_support.is_gitignored",
        fake_gitignored,
    )
    result = runner.main(
        [
            *VALID_ARGS,
            "--output",
            _gitignored_output_path("ag_live_bound_01_tracked.json"),
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "output path must be under ignored repo output/" in captured.err


def test_missing_domain_allowlist_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_missing_domain.json")

    result = runner.main(
        [
            "--query",
            PRIMARY_QUERY,
            "--mode",
            "Balanced",
            "--include-domains",
            "example.com",
            "--output",
            output,
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "docs.python.org" in captured.err


def test_non_exact_query_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_bad_query.json")

    result = runner.main(
        [
            "--query",
            "What is math.isclose?",
            "--mode",
            "Balanced",
            "--include-domains",
            "docs.python.org",
            "--output",
            output,
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "query must match" in captured.err


def test_backup_query_requires_flag(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_backup_without_flag.json")
    backup_query = (
        "According to the official Python 3 documentation, what are the default "
        "values for start and step in itertools.count()?"
    )

    result = runner.main(
        [
            "--query",
            backup_query,
            "--mode",
            "Balanced",
            "--include-domains",
            "docs.python.org",
            "--output",
            output,
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "query must match" in captured.err


def test_caps_serialized_and_validated(capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_caps_ok.json")

    result = runner.main([*VALID_ARGS, "--output", output])
    assert result == 0
    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    assert packet["caps_requested"] == {
        "max_scryraven_runs": 1,
        "max_retries": 0,
    }

    explicit_resource_cap_result = runner.main(
        [
            *VALID_ARGS,
            "--output",
            _gitignored_output_path("ag_live_bound_01_explicit_cap.json"),
            "--max-search-dispatches",
            "3",
        ]
    )
    capsys.readouterr()
    assert explicit_resource_cap_result == 0
    explicit_packet = json.loads(
        (
            ROOT / _gitignored_output_path("ag_live_bound_01_explicit_cap.json")
        ).read_text(encoding="utf-8")
    )
    assert explicit_packet["caps_requested"] == {
        "max_scryraven_runs": 1,
        "max_search_dispatches": 3,
        "max_retries": 0,
    }


def test_cap_overflow_fails_closed_with_fake_wrappers() -> None:
    support = _load_support()
    caps = support.AgLiveBoundCaps(max_search_dispatches=1)

    def fake_search(*_args: Any, **_kwargs: Any) -> list[Any]:
        return []

    wrapped = support.compose_capped_run_callables(
        process_search_queries=fake_search,
        fetch_linkup_precision_block=lambda *_a, **_k: None,
        ask_model=lambda *_a, **_k: None,
        caps=caps,
    )

    wrapped.process_search_queries("q")
    with pytest.raises(RuntimeError, match="search_dispatch budget exceeded"):
        wrapped.process_search_queries("q")


def test_author_and_smart_judgment_counters_with_fake_wrappers() -> None:
    support = _load_support()
    caps = support.AgLiveBoundCaps(
        max_author_model_calls=1,
        max_smart_search_judgment_model_calls=0,
    )

    wrapped = support.compose_capped_run_callables(
        process_search_queries=lambda *_a, **_k: [],
        fetch_linkup_precision_block=lambda *_a, **_k: None,
        ask_model=lambda *_a, **_k: "ok",
        caps=caps,
    )

    wrapped.ask_model("x", cost_phase="author")
    with pytest.raises(RuntimeError, match="smart_search_judgment_model_call budget exceeded"):
        wrapped.ask_model("x", cost_phase="search_judgment")


def test_fetch_read_cap_overflow_fails_closed_with_fake_wrappers() -> None:
    support = _load_support()
    caps = support.AgLiveBoundCaps(max_fetch_read_operations=0)
    fetch_attempted = False

    def fake_fetch(*_args: Any, **_kwargs: Any) -> str:
        nonlocal fetch_attempted
        fetch_attempted = True
        return "text"

    wrapped = support.compose_capped_run_callables(
        process_search_queries=lambda *_a, **_k: [],
        fetch_linkup_precision_block=fake_fetch,
        ask_model=lambda *_a, **_k: None,
        caps=caps,
    )

    with pytest.raises(RuntimeError, match="fetch_read_operation budget exceeded"):
        wrapped.fetch_linkup_precision_block("topic")
    assert fetch_attempted is False


def test_live_bound_caps_build_product_cap_policy() -> None:
    support = _load_support()
    policy = support.AgLiveBoundCaps().to_run_cap_policy()

    policy.mark_search_dispatch()
    observed = support.caps_observed_from_policy(policy)

    assert observed["scryraven_runs"] == 1
    assert observed["search_dispatches"] == 1
    assert observed["enforcement"] == "active"


def test_forbidden_packet_fields_absent() -> None:
    support = _load_support()
    context = support.build_preflight_context(
        root=ROOT,
        query=PRIMARY_QUERY,
        mode="Balanced",
        include_domains=["docs.python.org"],
        output_path=DEFAULT_OUTPUT,
        caps=support.AgLiveBoundCaps(),
        run_id="test-run",
        confirm_live_product_run=False,
        approved_backup_query=False,
    )
    packet = support.build_dry_run_packet(context)
    support.reject_forbidden_packet(packet)


def test_forbidden_packet_fields_rejected_recursively() -> None:
    support = _load_support()

    with pytest.raises(support.AgLiveBoundPacketError, match="raw_prompt"):
        support.reject_forbidden_packet(
            {"safe": [{"nested": {"raw_prompt": "must not serialize"}}]}
        )


def test_dry_run_module_has_no_top_level_live_imports() -> None:
    runner_source = RUNNER_PATH.read_text(encoding="utf-8")
    support_source = SUPPORT_PATH.read_text(encoding="utf-8")
    assert "request_live_validation_broker" not in runner_source
    support_tree = ast.parse(support_source)
    runner_tree = ast.parse(runner_source)
    runner_imported = {
        alias.name
        for node in runner_tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    runner_imported_from = {
        node.module
        for node in runner_tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported = {
        alias.name
        for node in ast.walk(support_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {
        node.module
        for node in ast.walk(support_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "dotenv" not in runner_imported
    assert "core.pipeline_orchestrator" not in runner_imported_from
    assert "run_pipeline" not in imported
    assert "dotenv" not in imported
    assert all("pipeline_orchestrator" not in (name or "") for name in imported_from)


def test_dry_run_no_dotenv_broker_env_access(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _load_runner()
    output = _gitignored_output_path("ag_live_bound_01_no_env.json")

    def fail_dotenv(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("dotenv must not be loaded in dry-run")

    def fail_broker(*_args: Any, **_kwargs: Any) -> int:
        raise AssertionError("broker client must not be invoked in dry-run")

    monkeypatch.setitem(sys.modules, "dotenv", type(sys)("dotenv"))
    sys.modules["dotenv"].load_dotenv = fail_dotenv  # type: ignore[attr-defined]
    broker_module = _load_module(
        ROOT / "scripts" / "request_live_validation_broker.py",
        "request_live_validation_broker_test_guard",
    )
    monkeypatch.setattr(broker_module, "main", fail_broker)

    result = runner.main([*VALID_ARGS, "--output", output])
    capsys.readouterr()
    assert result == 0


def test_is_allowed_output_path_requires_gitignore() -> None:
    support = _load_support()
    allowed = support.is_allowed_output_path(ROOT, ROOT / "output" / "probe.json")
    assert allowed == support.is_gitignored(ROOT, ROOT / "output" / "probe.json")
    assert support.is_allowed_output_path(ROOT, ROOT / "README.md") is False


def test_runner_ast_has_no_top_level_run_pipeline_import() -> None:
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
        for alias in node.names
    }
    assert "run_pipeline" not in imported_names
    assert "run_pipeline" not in imported_from
    assert "dotenv" not in imported_names
    assert all("pipeline_orchestrator" not in name for name in imported_from)


_N1_PRIVATE_CANARY = "AG_LIVE_N1_CAUSAL_PRIVATE_CANARY_MUST_NOT_SERIALIZE"
_N1_HANDOFF_DIGEST = "ab" * 32
_N1_TARGET_FACTS = (
    "semantic_handoff_present",
    "handoff_material_consumed",
    "component_analyst_case_present",
    "component_dprime_model_call_required",
    "component_dprime_model_call_executed",
    "semantic_admission_status",
    "component_coverage_satisfied",
    "canonical_slot_posture",
    "last_searchjudgment_action",
    "semantic_handoff_authorization_attempted",
    "semantic_handoff_sealed",
    "stale_or_invalid_transition_observed",
)


def _json_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _n1_handoff_ref() -> dict[str, str]:
    return {
        "semantic_handoff_id": f"searchos-semantic-handoff:{_N1_HANDOFF_DIGEST[:24]}",
        "semantic_handoff_digest": _N1_HANDOFF_DIGEST,
    }


def _n1_searchos_slice_a(
    *,
    run_id: str,
    request_id: str,
) -> dict[str, Any]:
    handoff = _n1_handoff_ref()
    slot_ref = {
        "slot_id": "slot-1",
        "slot_digest": "slot-digest-1",
        "component_id": "component-1",
        "source_obligation_id": "obligation-1",
    }
    analyst_case = {"role": "component_analyst"}
    slot_record = {
        "slot_ref": slot_ref,
        "requirement_posture": "required",
        "support_kind": "official_current",
        "latest_judgment_posture": "semantically_handed_off",
        "latest_judgment_reason": _N1_PRIVATE_CANARY,
        "judgment_call_count": 1,
        "action_history": [
            {
                "event": "judgment_decided",
                "action": _N1_PRIVATE_CANARY,
                "reason": _N1_PRIVATE_CANARY,
            },
            {
                "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
                "reason": _N1_PRIVATE_CANARY,
            },
        ],
        "custody_refs": [
            {
                "read_custody_material_id": "custody-1",
                "normalized_url": "https://fixture.invalid/private-canary",
                "read_content": _N1_PRIVATE_CANARY,
                "candidate_context": _N1_PRIVATE_CANARY,
            }
        ],
        "semantic_handoff_ref": handoff,
        "recorded_searchos_semantic_handoff_ref": {
            **handoff,
            "slot_ref": slot_ref,
            "schema_version": SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
        },
        "slice_a_ready": True,
        "component_analyst_case_ref": analyst_case,
    }
    readiness_core = {
        "schema_version": SEARCHOS_SLICE_A_READINESS_SCHEMA_VERSION,
        "owner": SEARCHOS_OWNER,
        "canonical_state": True,
        "run_id": run_id,
        "request_id": request_id,
        "required_slot_count": 1,
        "optional_slot_count": 0,
        "all_required_slots_slice_a_ready": True,
        "slot_records": [slot_record],
    }
    digest = _json_digest(readiness_core)
    readiness = {
        **readiness_core,
        "readiness_projection_digest": digest,
        "readiness_projection_id": f"searchos-readiness:{digest[:24]}",
        "replay_identity": f"searchos-readiness:{digest}",
    }
    return {
        "schema_version": "searchos_slice_a_product_runtime_v1",
        "owner": SEARCHOS_OWNER,
        "slot_postures": {"slot-1": "semantically_handed_off"},
        "semantic_outcomes_by_slot": {
            "slot-1": {
                "semantic_handoff_ref": handoff,
                "component_analyst_case_ref": analyst_case,
                "semantic_admission_outcome_ref": {
                    "component_analyst_case_ref": analyst_case,
                    "component_coverage_ref": {"coverage_state": "satisfied"},
                },
                "semantic_admission_status": "admitted",
                "searchos_handoff_material_consumed": True,
            }
        },
        "readiness_projection": readiness,
        "readiness_projection_ref": {
            "readiness_projection_id": readiness["readiness_projection_id"],
            "readiness_projection_digest": digest,
        },
        "semantic_handoff_authorization_attempted_slot_ids": ["slot-1"],
        "candidate_context": {"text": _N1_PRIVATE_CANARY},
        "private_raw": {
            "query": _N1_PRIVATE_CANARY,
            "prompt": _N1_PRIVATE_CANARY,
            "provider_payload": _N1_PRIVATE_CANARY,
            "model_response": _N1_PRIVATE_CANARY,
        },
    }


def _q1_like_blocked_outcome(
    *,
    run_id: str = "q1-like-run",
    session_id: str = "q1-like-session",
) -> SimpleNamespace:
    searchos = _n1_searchos_slice_a(run_id=run_id, request_id=session_id)
    return SimpleNamespace(
        run_id=run_id,
        session_id=session_id,
        terminal_status="blocked",
        report="Final answer blocked before Author.",
        top_passages=[
            {
                "source_id": 1,
                "url": "https://docs.python.org/3/library/math.html#math.isclose",
                "text": _N1_PRIVATE_CANARY,
            }
        ],
        seen_urls=["https://docs.python.org/3/library/math.html#math.isclose"],
        execution_trace={
            SEARCHOS_SLICE_A_TRACE_KEY: searchos,
            "final_answer_source_ids_used": [],
            "evidence_sufficient": False,
            "synth_was_insufficient": True,
            "synth_sufficient_first_pass": False,
            "answer_class": "blocked_final_answer",
            "response_displayable": False,
            "author_system_prompt_key": None,
            "failure_card": {"show": True, "reason": "blocked_final_answer_packet"},
            "blocked_fap_terminal": {
                "blocked_fap": True,
                "author_called": False,
                "exported_terminal_posture": "blocked",
            },
            "final_answer_packet": {
                "canonical_state": True,
                "trace_mode": "run_kernel_final_answer_packet_projection",
                "readiness_status": "blocked",
                "author_payload_status": "author_input_deferred",
                "citation_eligible_source_ids": [],
                "sufficiency_decision": "partial_answer_authorized",
                "semantic_evidence_authority_manifest": {
                    "semantic_packet_evidence_binding_available": False,
                    "semantic_packet_evidence_binding_count": 0,
                    "content_refs_available": False,
                    "coverage_refs_available": True,
                },
                "semantic_content_coverage_ref": {
                    "component_ref_count": 1,
                    "coverage_record_ref_count": 1,
                    "semantic_observation_ref_count": 0,
                    "sanitized_content_ref_count": 0,
                },
            },
        },
    )


def _direct_n1_projection(outcome: Any) -> dict[str, Any] | None:
    trace = dict(getattr(outcome, "execution_trace", {}) or {})
    return build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(trace.get(SEARCHOS_SLICE_A_TRACE_KEY) or {}),
        enabled=True,
        expected_run_id=str(getattr(outcome, "run_id", "") or ""),
        expected_request_id=str(getattr(outcome, "session_id", "") or ""),
    )


def _assert_target_facts(projection: Mapping[str, Any]) -> None:
    assert projection["projection_status"] == "available"
    assert projection["required_slot_count"] == 1
    assert len(projection["slots"]) == 1
    slot = dict(projection["slots"][0])
    for key in _N1_TARGET_FACTS:
        assert key in slot
    assert slot["semantic_handoff_present"] is True
    assert slot["handoff_material_consumed"] is True
    assert slot["component_analyst_case_present"] is True
    assert slot["component_dprime_model_call_required"] is False
    assert slot["component_dprime_model_call_executed"] is False
    assert slot["semantic_admission_status"] == "admitted"
    assert slot["component_coverage_satisfied"] is True
    assert slot["canonical_slot_posture"] == "semantically_handed_off"
    assert slot["last_searchjudgment_action"] == (
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
    )
    assert slot["semantic_handoff_authorization_attempted"] is True
    assert slot["semantic_handoff_sealed"] is True
    assert slot["stale_or_invalid_transition_observed"] is False
    assert "semantic_handoff_authorization_attempted_slot_ids" not in slot
    assert "action_history" not in slot
    assert "latest_judgment_reason" not in slot


def test_q1_like_blocked_fap_success_packet_reuses_canonical_n1_projection(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    support = _load_support()
    output = _gitignored_output_path("ag_live_bound_01_q1_like_blocked_fap.json")
    _stub_live_runner_without_env(runner, monkeypatch)
    outcome = _q1_like_blocked_outcome()
    expected = _direct_n1_projection(outcome)
    assert expected is not None

    def fake_run_pipeline(
        config: Any,
        _deps: Any,
        _status: Any,
        _accumulator: Any,
    ) -> Any:
        config.cap_policy.mark_search_dispatch()
        config.cap_policy.mark_search_dispatch()
        return outcome

    with patch(
        "core.pipeline_orchestrator.run_pipeline",
        side_effect=fake_run_pipeline,
    ) as run_pipeline:
        result = runner.main(
            [*VALID_ARGS, "--output", output, "--confirm-live-product-run"]
        )

    assert result == 0
    assert run_pipeline.call_count == 1
    capsys.readouterr()

    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    summaries = packet["sanitized_projection_summaries"]
    assert packet["success_classification"] == "success"
    assert packet["run_pipeline_call_count"] == 1
    assert summaries["searchos_n1_causal_projection"] == expected
    _assert_target_facts(summaries["searchos_n1_causal_projection"])
    cli_projection = compatibility_cli.build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(
            dict(getattr(outcome, "execution_trace", {}) or {}).get(
                SEARCHOS_SLICE_A_TRACE_KEY
            )
            or {}
        ),
        enabled=True,
        expected_run_id=str(outcome.run_id or ""),
        expected_request_id=str(outcome.session_id or ""),
    )
    assert cli_projection == expected
    assert support.build_bounded_searchos_n1_causal_projection is (
        build_bounded_searchos_n1_causal_projection
    )
    assert summaries["searchos_n1_causal_projection"].get("searchos_exit") == (
        "SEMANTIC_HANDOFF"
    )
    assert summaries["author_posture"]["failure_card_show"] is True
    assert summaries["author_posture"]["final_answer_readiness_status"] == "blocked"
    assert summaries["component_binding"]["semantic_packet_evidence_binding_count"] == 0
    assert summaries["component_coverage"]["component_ref_count"] == 1
    assert summaries["final_answer_packet"]["readiness_status"] == "blocked"
    assert summaries["sufficiency"]["sufficiency_decision"] == (
        "partial_answer_authorized"
    )
    assert packet["retention_posture"]["only_runner_artifact_written"] is True
    assert packet["no_retention"]["full_raw_traces_retained"] is False
    rendered = json.dumps(packet, sort_keys=True)
    assert _N1_PRIVATE_CANARY not in rendered
    assert "https://fixture.invalid/private-canary" not in rendered
    assert '"execution_trace":' not in rendered
    support.reject_forbidden_packet(packet)


def test_ag_live_n1_causal_projection_omitted_when_builder_returns_none() -> None:
    support = _load_support()
    context = support.build_preflight_context(
        root=ROOT,
        query=PRIMARY_QUERY,
        mode="Balanced",
        include_domains=["docs.python.org"],
        output_path=ROOT / "output" / "ag_live_bound_01_n1_omitted.json",
        caps=support.AgLiveBoundCaps(),
        run_id="ag-live-n1-omitted-test",
        confirm_live_product_run=True,
        approved_backup_query=False,
    )
    outcome = _q1_like_blocked_outcome()
    with patch.object(
        support,
        "build_bounded_searchos_n1_causal_projection",
        return_value=None,
    ):
        packet = support.build_live_success_packet(
            context,
            outcome=outcome,
            cap_policy=context.caps.to_run_cap_policy(),
        )
    assert "searchos_n1_causal_projection" not in packet["sanitized_projection_summaries"]
    support.reject_forbidden_packet(packet)


def test_ag_live_n1_causal_projection_identity_fail_closed() -> None:
    support = _load_support()
    context = support.build_preflight_context(
        root=ROOT,
        query=PRIMARY_QUERY,
        mode="Balanced",
        include_domains=["docs.python.org"],
        output_path=ROOT / "output" / "ag_live_bound_01_n1_identity.json",
        caps=support.AgLiveBoundCaps(),
        run_id="ag-live-packet-run-id",
        confirm_live_product_run=True,
        approved_backup_query=False,
    )
    matching = _q1_like_blocked_outcome(
        run_id="pipeline-run-id",
        session_id="pipeline-session-id",
    )
    mismatched = SimpleNamespace(
        run_id="stale-run-id",
        session_id="stale-session-id",
        terminal_status="blocked",
        report=matching.report,
        top_passages=matching.top_passages,
        seen_urls=matching.seen_urls,
        execution_trace=matching.execution_trace,
    )
    matching_direct = _direct_n1_projection(matching)
    mismatched_direct = _direct_n1_projection(mismatched)
    assert matching_direct is not None
    assert mismatched_direct is not None
    assert matching_direct.get("searchos_exit") == "SEMANTIC_HANDOFF"
    assert mismatched_direct.get("searchos_exit") != "SEMANTIC_HANDOFF"

    matching_packet = support.build_live_success_packet(
        context,
        outcome=matching,
        cap_policy=context.caps.to_run_cap_policy(),
    )
    mismatched_packet = support.build_live_success_packet(
        context,
        outcome=mismatched,
        cap_policy=context.caps.to_run_cap_policy(),
    )
    matching_observed = matching_packet["sanitized_projection_summaries"][
        "searchos_n1_causal_projection"
    ]
    mismatched_observed = mismatched_packet["sanitized_projection_summaries"][
        "searchos_n1_causal_projection"
    ]
    assert matching_observed == matching_direct
    assert mismatched_observed == mismatched_direct
    assert mismatched_observed != matching_direct
    assert mismatched_observed.get("searchos_exit") != "SEMANTIC_HANDOFF"
    support.reject_forbidden_packet(matching_packet)
    support.reject_forbidden_packet(mismatched_packet)
