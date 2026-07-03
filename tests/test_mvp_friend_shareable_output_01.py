"""PRODUCT-PATH-REGRESSION: friend-shareable MVP output.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --mvp-demo
Runtime consumer: proplex.__main__ -> proplex.mvp_friend_shareable_output ->
proplex.live_semantic_coverage_status
Why ordinary product-path work cannot be done directly: the MVP demo is an
ordinary CLI path, but it uses deterministic retained artifacts and an injected
offline D-prime review because live/model/provider/search/fetch/read/retrieval
calls remain explicit-license only.
Integration deadline: current phase.
Exit condition: keep while the friend-shareable MVP demo flag exists.
Why this is not a shadow product path: it invokes the existing product status
builder and answer/source-display reducers instead of a standalone answer
formatter.
Forbidden interpretation: this is not live validation, product correctness,
source acquisition quality, multi-component support, full Scrutineer
remediation, Economist/Specialist routing, or old Author execution.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from core.product_model_route_config import (
    MVP_DEMO_FLAG,
    MVP_LIVE_DOGFOOD_RUN_FLAG,
    MVP_LIVE_DOGFOOD_STATUS_FLAG,
    PRODUCT_STATUS_DRY_RUN_FLAGS,
)
from proplex.mvp_friend_shareable_output import (
    BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED,
    BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING,
    DEFAULT_MVP_QUERY,
    MVP_DEMO_BOUNDED_TEXT,
    build_mvp_demo_output,
    build_mvp_live_dogfood_status_output,
)

ROOT = Path(__file__).resolve().parents[1]
QUERY = DEFAULT_MVP_QUERY
MVP_MODULE = ROOT / "proplex" / "mvp_friend_shareable_output.py"
CLI_MODULE = ROOT / "proplex" / "__main__.py"


def test_mvp_demo_reaches_product_answer_and_source_display(tmp_path: Path) -> None:
    result = build_mvp_demo_output(
        query=QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_demo_01",
        run_id="test-mvp-demo",
    )

    assert result.decision == "PASS", result.packet.get("blocker_detail")
    assert result.return_code == 0
    assert result.packet_path.exists()
    packet = json.loads(result.packet_path.read_text(encoding="utf-8"))

    assert packet["ordinary_entrypoint"] == "python -m proplex"
    assert packet["ordinary_product_path_consumed"] is True
    assert packet["runtime_consumer"] == (
        "proplex.live_semantic_coverage_status.build_live_semantic_coverage_status"
    )
    assert packet["answer_text_present"] is True
    assert "Adult U.S. passport book renewal by mail fee is $130" in (
        packet["answer_or_blocker_text"]
    )
    assert packet["source_display_entries"]
    assert packet["source_display_entries"][0]["domain"] == "travel.state.gov"
    assert packet["product_correctness_claimed"] is False
    assert packet["raw_provider_payload_retained"] is False
    assert packet["raw_search_response_retained"] is False
    assert packet["raw_prompt_retained"] is False
    assert packet["raw_model_response_retained"] is False
    assert packet["private_logs_retained"] is False
    assert packet["dprime_model_review_call_count"] == 1
    assert packet["evidence_ledger_admissions"] == 1
    assert packet["status_payload"]["dprime_answer_path_ref"]["status"] == "consumed"


def test_mvp_demo_human_output_is_compact_and_hygienic(tmp_path: Path) -> None:
    result = build_mvp_demo_output(
        query=QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_demo_01",
        run_id="test-mvp-human",
    )
    out = result.output

    assert "ScryRaven MVP demo" in out
    assert "Answer\n" in out
    assert "Sources\n" in out
    assert "Challenge State\n" in out
    assert "Product correctness claimed: false" in out
    assert "Raw/private retained: false" in out
    assert "Scrutineer: not invoked; single-source lane" in out
    assert "Follow-up: not requested" in out
    assert "Review packet:" in out
    assert len(out.splitlines()) <= 30
    for forbidden in (
        "bounded_text",
        MVP_DEMO_BOUNDED_TEXT,
        "raw prompt",
        "raw model response",
        "provider payload",
        "private log",
        "D-prime negative-control profile ref/digest",
    ):
        assert forbidden.casefold() not in out.casefold()


def test_mvp_demo_cli_runs_without_api_keys_and_uses_default_query() -> None:
    env = os.environ.copy()
    for key in (
        "BRAVE_API_KEY",
        "TAVILY_API_KEY",
        "LINKUP_API_KEY",
        "EXA_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        env.pop(key, None)

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proplex",
            MVP_DEMO_FLAG,
            "--mvp-output-dir",
            "output/test_mvp_friend_shareable_output_01",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Question: What is the current adult U.S. passport book renewal fee by mail?" in (
        proc.stdout
    )
    assert "ScryRaven MVP demo" in proc.stdout
    assert "Sources" in proc.stdout
    assert "OPENAI_API_KEY is required" not in proc.stderr


def test_mvp_demo_rejects_unsupported_query_with_named_blocker(
    tmp_path: Path,
) -> None:
    result = build_mvp_demo_output(
        query="What arbitrary question can this demo answer?",
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_demo_01",
        run_id="test-mvp-unsupported-query",
    )

    assert result.decision == BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED
    assert result.return_code == 2
    assert result.retained_artifact_root is None
    assert result.packet_path.exists()
    packet = json.loads(result.packet_path.read_text(encoding="utf-8"))

    assert packet["decision"] == BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED
    assert packet["status_decision"] == BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED
    assert packet["query"] == "unsupported MVP demo query (not retained)"
    assert packet["unsupported_query_retained"] is False
    assert packet["supported_demo_query"] == DEFAULT_MVP_QUERY
    assert packet["ordinary_product_path_consumed"] is False
    assert packet["provider_calls_attempted"] == 0
    assert packet["search_tasks_attempted"] == 0
    assert packet["fetch_read_attempts"] == 0
    assert packet["evidence_ledger_admissions"] == 0
    assert packet["dprime_model_review_call_count"] == 0
    assert packet["source_display_entries"] == []
    assert "fixed deterministic fixture" in packet["answer_or_blocker_text"]
    assert DEFAULT_MVP_QUERY in packet["answer_or_blocker_text"]
    assert (
        BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING
        in packet["answer_or_blocker_text"]
    )
    assert "fixed deterministic fixture" in result.output
    assert BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED in result.output
    assert "What arbitrary question" not in result.output
    assert not (result.packet_path.parent / "retained_status_repo").exists()


def test_mvp_demo_cli_rejects_unsupported_query() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "proplex",
            MVP_DEMO_FLAG,
            "--query",
            "What arbitrary question can this demo answer?",
            "--mvp-output-dir",
            "output/test_mvp_friend_shareable_output_01",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=45,
    )

    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED in proc.stdout
    assert "fixed deterministic fixture" in proc.stdout
    assert DEFAULT_MVP_QUERY in proc.stdout
    assert BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING in proc.stdout


def test_mvp_live_status_is_default_off_and_records_blocker(tmp_path: Path) -> None:
    result = build_mvp_live_dogfood_status_output(
        query=QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="test-live-blocker",
    )

    assert result.return_code == 2
    assert result.packet_path.exists()
    packet = json.loads(result.packet_path.read_text(encoding="utf-8"))
    assert packet["command_harness_used"] == (
        f"python -m proplex {MVP_LIVE_DOGFOOD_STATUS_FLAG}"
    )
    assert packet["provider_calls_attempted"] == 0
    assert packet["fetch_read_attempts"] == 0
    assert packet["dprime_model_review_call_count"] == 0
    assert packet["product_correctness_claimed"] is False
    assert "Blocked before answer:" in packet["answer_or_blocker_text"]
    assert "Raw/private retained: false" in result.output


def test_default_cli_does_not_run_mvp_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _import_cli_with_dotenv_disabled(monkeypatch)

    def fail_mvp(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("MVP path must be default-off")

    def fake_run_pipeline(*_args: Any, **_kwargs: Any) -> Any:
        return SimpleNamespace(
            report="default product report",
            execution_trace={},
            cost_snapshot={"total_calls": 0, "total_cost_usd": 0.0},
            latency_seconds=0.0,
        )

    monkeypatch.setattr(cli, "build_mvp_demo_output", fail_mvp)
    monkeypatch.setattr(cli, "build_mvp_live_dogfood_run_output", fail_mvp)
    monkeypatch.setattr(cli, "build_mvp_live_dogfood_status_output", fail_mvp)
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "missing_required_api_keys", lambda **_kwargs: [])
    monkeypatch.setattr(cli, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        cli,
        "append_official_canonical_recovery_diagnostics_section",
        lambda report, _trace: report,
    )

    assert cli.main(["ordinary query"]) == 0
    assert "default product report" in capsys.readouterr().out


def test_mvp_flags_are_no_secret_status_dry_run_flags() -> None:
    assert MVP_DEMO_FLAG in PRODUCT_STATUS_DRY_RUN_FLAGS
    assert MVP_LIVE_DOGFOOD_RUN_FLAG in PRODUCT_STATUS_DRY_RUN_FLAGS
    assert MVP_LIVE_DOGFOOD_STATUS_FLAG in PRODUCT_STATUS_DRY_RUN_FLAGS


def test_mvp_product_code_avoids_scripts_tests_and_live_clients() -> None:
    forbidden_imports = {
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "subprocess",
    }
    for path in (MVP_MODULE, CLI_MODULE):
        imported = _imports(path)
        assert not any(name == "tests" or name.startswith("tests.") for name in imported)
        assert "scripts" not in imported
    assert _imports(MVP_MODULE).isdisjoint(forbidden_imports)


def _import_cli_with_dotenv_disabled(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    return importlib.import_module("proplex.__main__")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
