from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
            source_custody_policy=None,
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
    assert packet["caps_requested"]["max_search_dispatches"] == 2
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
    assert captured_config["config"].cap_policy.max_search_dispatches == 2
    assert captured_config["config"].cap_policy.max_fetch_read_operations == 3
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


def test_source_custody_profile_builds_run_config_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    support = _load_support()
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
    context = support.build_preflight_context(
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

    config = runner._build_live_run_config(
        context,
        cap_policy=context.caps.to_run_cap_policy(),
    )

    assert config.source_custody_policy is not None
    assert config.source_custody_policy.require_official_full_fetch_read is True
    assert config.source_custody_policy.preferred_domains == ("docs.python.org",)
    assert config.source_custody_policy.required_source_class == (
        "primary_source_documents"
    )


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
        result = runner.main([*VALID_ARGS, "--output", output, "--confirm-live-product-run"])

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
    assert "raw_prompt" not in observed
    assert packet["sanitized_projection_summaries"]["blocked_fap_summary"] == observed
    assert packet["failure_summary"]["blocked_fap"] is True
    assert packet["failure_summary"]["blocked_fap_readiness_status"] == "blocked"
    assert packet["validation_observability"]["subject_budget_summary"][
        "subject_budget_enabled"
    ] is False
    rendered = json.dumps(packet, sort_keys=True)
    assert "must not serialize" not in rendered
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
    assert packet["caps_requested"]["max_retries"] == 0

    bad_caps_result = runner.main(
        [
            *VALID_ARGS,
            "--output",
            _gitignored_output_path("ag_live_bound_01_bad_caps.json"),
            "--max-search-dispatches",
            "3",
        ]
    )
    captured = capsys.readouterr()
    assert bad_caps_result == 2
    assert "caps must match" in captured.err


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
