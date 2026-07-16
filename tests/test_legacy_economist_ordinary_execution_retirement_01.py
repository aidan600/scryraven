"""Offline product-path guards for legacy Economist ordinary retirement.

Test path: tests/test_legacy_economist_ordinary_execution_retirement_01.py
Proof class: offline_product_path_proof.
Validation bucket: phase_focus.
Surface guarded: ordinary orchestrator reachability, dependency composition,
Linkup separation, compatibility telemetry, and Author-facing input custody.
Runtime/product path guarded: public CLI composition and real run_pipeline().
Expected cost: two deterministic offline pipeline runs plus CLI help probes.
Promotion posture: remain phase_focus pending post-retirement topology census.
Why not fast_pr: detailed retirement proof overlaps broader durable lanes.
"""

from __future__ import annotations

import ast
import logging
import os
import subprocess
import sys
from dataclasses import MISSING, fields
from pathlib import Path
from typing import Any

import pytest

from core.prompts import DEFAULT_SYSTEM
from core.run_config import RunDeps
from proplex.ordinary_live_entrypoint_dry_run import OrdinaryLiveEntrypointDryRunDeps
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "core" / "pipeline_orchestrator.py"
CURRENT_COMPOSITION_ROOTS = (
    ROOT / "proplex" / "__main__.py",
    ROOT / "proplex" / "ordinary_live_entrypoint_dry_run.py",
    ROOT / "scripts" / "ag_live_bound_01_bounded_product_runner.py",
)
LEGACY_ECONOMIST_RETIREMENT_REASON = (
    "legacy_economist_ordinary_execution_retired"
)
LINKUP_CONTEXT_MARKER = "LINKUP_RETIREMENT_PARITY_CONTEXT"
QUERY = "Compare Alpha and Beta operating rates using current evidence."


def _call_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def _rundeps_calls(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id == "RunDeps"
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == "RunDeps"
        )
    ]


def test_static_ordinary_reachability_and_composition_are_closed() -> None:
    source = ORCHESTRATOR.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = _call_names(tree)

    assert "deps.run_economist_step" not in source
    assert "_run_economist_step" not in source
    assert "_economist_preflight_gate" not in source
    assert "_record_economist_preflight_result" not in source
    assert "build_economist_preflight_prompt" not in source
    assert "ThreadPoolExecutor" not in source
    assert "Building quantitative model" not in source
    assert "QUANTITATIVE FRAMEWORK NOT RUN" not in source
    assert "OPENAI_API_KEY" not in source
    assert "build_economist_preflight_prompt" not in calls

    need_assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(
            isinstance(target, ast.Name) and target.id == "need_economist"
            for target in (
                node.targets if isinstance(node, ast.Assign) else (node.target,)
            )
        )
    ]
    assert len(need_assignments) == 1
    assert isinstance(need_assignments[0].value, ast.Constant)
    assert need_assignments[0].value.value is False
    assert not any(
        isinstance(node, ast.If)
        and any(
            isinstance(child, ast.Name) and child.id == "need_economist"
            for child in ast.walk(node.test)
        )
        for node in ast.walk(tree)
    )

    for path in CURRENT_COMPOSITION_ROOTS:
        composition_source = path.read_text(encoding="utf-8")
        assert "run_economist_step" not in composition_source, path
        for call in _rundeps_calls(path):
            assert not call.args, path
            assert "run_economist_step" not in {
                keyword.arg for keyword in call.keywords
            }, path

    cli_tree = ast.parse((ROOT / "proplex" / "__main__.py").read_text(encoding="utf-8"))
    assert "compose_quantitative_specialist_product_deps" in _call_names(cli_tree)

    delegate_source = (ROOT / "scryraven" / "__main__.py").read_text(
        encoding="utf-8"
    )
    assert "from proplex.__main__ import main" in delegate_source
    assert "run_pipeline" not in delegate_source
    assert "RunDeps" not in delegate_source

    assert "run_economist_step" in (
        ROOT / "ui" / "pages_home.py"
    ).read_text(encoding="utf-8")
    assert "run_economist_step" in (
        ROOT / "tests" / "test_economist_safety.py"
    ).read_text(encoding="utf-8")


def test_rundeps_legacy_callable_is_optional_and_all_callers_are_keyword_only() -> None:
    legacy_field = next(
        field for field in fields(RunDeps) if field.name == "run_economist_step"
    )
    assert legacy_field.default is None
    assert legacy_field.default_factory is MISSING

    for path in ROOT.rglob("*.py"):
        if any(part in {".git", ".venv", "env", "output"} for part in path.parts):
            continue
        for call in _rundeps_calls(path):
            assert not call.args, path


def test_quantitative_ordinary_run_never_calls_legacy_economist_or_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        report_type="quantitative_comparison",
        query_type="comparison",
        query=QUERY,
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        analyst_response="The retrieved evidence supports a bounded comparison.",
        raw_author_response=(
            "The evidence supports a bounded qualitative comparison. "
            "[[1]](https://alpha.example/report-1)"
        ),
        current_date="July 15, 2026",
        environment_overrides={
            "OPENAI_API_KEY": "isolated-test-sentinel",  # pragma: allowlist secret
        },
    )
    trace = outcome.execution_trace
    economist_handoff = trace["economist_handoff_contract"]

    assert harness.economist_calls == []
    assert outcome.report == harness.raw_author_response
    assert trace["economist_ran"] is False
    assert trace["timing"]["economist_seconds"] == 0.0
    assert trace["economist_preflight_allowed"] is None
    assert trace["economist_preflight_block_reason"] == (
        LEGACY_ECONOMIST_RETIREMENT_REASON
    )
    assert trace["economist_preflight_missing_entities"] == []
    assert trace["economist_skip_reason"] == LEGACY_ECONOMIST_RETIREMENT_REASON
    assert trace["economist_schema_version"] is None
    assert trace["quantitative_packet_present"] is False
    assert trace["quantitative_packet_valid"] is False
    assert trace["quantitative_packet"] is None
    assert economist_handoff["admission"]["economist_should_run"] is False
    assert economist_handoff["admission"]["economist_ran"] is False
    assert economist_handoff["preflight"]["evaluated"] is False
    assert economist_handoff["output"]["output_present"] is False

    systems = [str(call["system_prompt"]) for call in harness.model_calls]
    assert DEFAULT_SYSTEM["economist"] not in systems
    assert not any(system.startswith("You classify evidence only") for system in systems)
    assert harness.analyst_prompts
    assert harness.author_prompts
    for prompt in (*harness.analyst_prompts, *harness.author_prompts):
        assert "QUANTITATIVE FRAMEWORK" not in prompt
        assert "economist_v1" not in prompt
        assert "quantitative_packet" not in prompt
        assert LEGACY_ECONOMIST_RETIREMENT_REASON not in prompt
    assert "Analysis:" in harness.author_prompts[-1]
    assert "Precision Evidence" in harness.author_prompts[-1]


def test_linkup_keeps_existing_eligibility_arguments_and_analyst_integration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    linkup_calls: list[dict[str, Any]] = []

    def fake_linkup(*args: Any, **kwargs: Any) -> str:
        linkup_calls.append({"args": args, "kwargs": dict(kwargs)})
        return f"\n\n{LINKUP_CONTEXT_MARKER}\n"

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Deep",
        report_type="quantitative_comparison",
        query_type="comparison",
        query=QUERY,
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        analyst_response="The retrieved evidence and Linkup context agree.",
        raw_author_response=(
            "The evidence supports the comparison. "
            "[[1]](https://alpha.example/report-1)"
        ),
        current_date="July 15, 2026",
        deps_overrides={"fetch_linkup_precision_block": fake_linkup},
        environment_overrides={
            "LINKUP_API_KEY": "isolated-test-sentinel",  # pragma: allowlist secret
            "OPENAI_API_KEY": "isolated-test-sentinel",  # pragma: allowlist secret
        },
    )

    assert harness.economist_calls == []
    assert len(linkup_calls) == 1
    call = linkup_calls[0]
    assert call["args"] == (
        "Alpha and Beta operating rates",
        "general",
        "high",
        ["alpha.example"],
        ["blocked.example"],
    )
    assert set(call["kwargs"]) == {
        "provider_diagnostics",
        "cost_accumulator",
        "cost_phase",
    }
    assert isinstance(call["kwargs"]["provider_diagnostics"], list)
    assert call["kwargs"]["cost_phase"] == "retrieval"
    assert harness.analyst_prompts
    assert LINKUP_CONTEXT_MARKER in harness.analyst_prompts[-1]
    assert outcome.execution_trace["economist_ran"] is False
    assert outcome.execution_trace["timing"]["economist_seconds"] == 0.0
    assert outcome.execution_trace["quantitative_packet"] is None

    linkup_source = (ROOT / "core" / "pipeline.py").read_text(encoding="utf-8")
    linkup_body = linkup_source.split(
        "def fetch_linkup_precision_block(", maxsplit=1
    )[1].split("\ndef ", maxsplit=1)[0]
    assert 'depth="deep"' in linkup_body
    assert 'output_type="sourcedAnswer"' in linkup_body
    assert "max_results=8" in linkup_body


def test_current_composition_and_cli_help_work_without_economist_callable(
    tmp_path: Path,
) -> None:
    deps = OrdinaryLiveEntrypointDryRunDeps(
        output_dir=tmp_path,
        logger=logging.getLogger("test.economist.retirement.composition"),
    ).to_run_deps()
    assert deps.run_economist_step is None

    env = os.environ.copy()
    env["PYTHON_DOTENV_DISABLED"] = "1"
    for key in (
        "BRAVE_API_KEY",
        "TAVILY_API_KEY",
        "LINKUP_API_KEY",
        "EXA_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        env.pop(key, None)
    for module in ("scryraven", "proplex"):
        proc = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "ScryRaven" in proc.stdout
