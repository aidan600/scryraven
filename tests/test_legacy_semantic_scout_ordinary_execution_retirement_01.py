"""Offline product-path guards for semantic Scout and provider-synthesis retirement.

Harness label: PRODUCT-PATH-REGRESSION.
Ordinary product path guarded: supported ``run_pipeline()`` composition.
Runtime consumer: ``core.pipeline_orchestrator.run_pipeline``.
Why this is not a shadow product path: every behavioral proof invokes the real
ordinary pipeline with injected deterministic model/search/provider fakes.
Exit condition: retain while the ordinary product continues to use this pipeline.
Forbidden interpretation: offline proof does not establish live provider quality.

Test classification: phase_focus; not a fast_pr candidate because the detailed
retirement assertions overlap the durable semantic/search validation lanes.
"""

from __future__ import annotations

import ast
from dataclasses import MISSING, fields
from pathlib import Path
from typing import Any

import pytest

from core.run_config import RunDeps
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "core" / "pipeline_orchestrator.py"
CLI = ROOT / "proplex" / "__main__.py"
ORDINARY_LIVE_DRY_RUN = ROOT / "proplex" / "ordinary_live_entrypoint_dry_run.py"
BOUNDED_PRODUCT_RUNNER = ROOT / "scripts" / "ag_live_bound_01_bounded_product_runner.py"
ORDINARY_COMPOSITION_ROOTS = (
    CLI,
    ORDINARY_LIVE_DRY_RUN,
    BOUNDED_PRODUCT_RUNNER,
)
PROMPTS = ROOT / "core" / "prompts.py"
SCOUT_COMPATIBILITY = ROOT / "core" / "scout.py"
QUERY_PLAN_ADAPTER = ROOT / "core" / "query_plan_runtime_adapter.py"
SCHEDULER = ROOT / "core" / "retrieval_scheduler.py"
PIPELINE_HELPERS = ROOT / "core" / "pipeline.py"
SEARCH_PROVIDERS = ROOT / "core" / "search_providers.py"
GENERIC_ACQUISITION = ROOT / "core" / "generic_product_provider_acquisition.py"
LEGACY_REVIEW = ROOT / "core" / "legacy_review_runtime_stage.py"

RETIREMENT_REASON = "legacy_semantic_scout_ordinary_execution_retired"
PROVIDER_ANSWER_MARKER = "PROVIDER_WRITTEN_LINKUP_ANSWER_MUST_NOT_ENTER_ANALYST"
QUERY = "Compare Alpha and Beta operating rates using current evidence."
RETIRED_RUNDEPS_NAMES = frozenset(
    {
        "fetch_linkup_precision_block",
        "run_scout",
        "should_skip_quant_scout",
    }
)


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def _rundeps_keywords(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    keywords: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (
            isinstance(node.func, ast.Name)
            and node.func.id == "RunDeps"
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == "RunDeps"
        ):
            continue
        keywords.update(keyword.arg for keyword in node.keywords if keyword.arg)
    return keywords


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    names = {
        alias.asname or alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    }
    names.update(
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    )
    return names


@pytest.mark.parametrize(
    "composition_root",
    ORDINARY_COMPOSITION_ROOTS,
    ids=("ordinary-cli", "ordinary-live-dry-run", "bounded-product-runner"),
)
def test_current_composition_root_does_not_import_or_inject_retired_dependencies(
    composition_root: Path,
) -> None:
    imported_retired_names = RETIRED_RUNDEPS_NAMES & _imported_names(composition_root)
    injected_retired_names = RETIRED_RUNDEPS_NAMES & _rundeps_keywords(composition_root)
    assert not imported_retired_names, (
        f"{composition_root} imports retired dependencies: {sorted(imported_retired_names)}"
    )
    assert not injected_retired_names, (
        f"{composition_root} injects retired RunDeps fields: {sorted(injected_retired_names)}"
    )


def test_ordinary_semantic_scout_spy_is_inert_and_downstream_still_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scout_calls: list[dict[str, Any]] = []

    def forbidden_scout(*args: Any, **kwargs: Any) -> dict[str, Any]:
        scout_calls.append({"args": args, "kwargs": dict(kwargs)})
        return {
            "directed_queries": [
                "Alpha scout-only operating rate",
                "Beta scout-only operating rate",
            ]
        }

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        report_type="quantitative_comparison",
        query_type="comparison",
        query=QUERY,
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        current_date="July 16, 2026",
        deps_overrides={
            "run_scout": forbidden_scout,
            "should_skip_quant_scout": lambda *_args, **_kwargs: False,
        },
    )

    trace = outcome.execution_trace
    assert scout_calls == []
    assert "FinalAnswerPacket readiness is blocked" in outcome.report
    assert harness.analyst_calls == 1
    assert harness.author_prompts == []
    assert harness.search_calls
    assert all(call["provider_role"] != "scout_continuation" for call in harness.search_calls)
    assert trace["scout_fired"] is False
    assert trace["scout_key"] is None
    assert trace["scout_queries"] == []
    assert trace["scout_skip_reason"] == RETIREMENT_REASON
    assert trace["timing"]["scout_llm_seconds"] == 0.0
    scout_gate = trace["scout_continuation_spine_gate_trace"]
    assert scout_gate["available"] is False
    assert scout_gate["reason"] == RETIREMENT_REASON
    assert scout_gate["authorized_queries"] == []

    query_plan_history = trace.get("query_plan_history") or []
    assert all("scout" not in str(item).casefold() for item in query_plan_history)
    assert "scout_directed_continuation" not in str(trace)
    assert "scout_continuation" not in str(trace.get("provider_plan", {}))


def test_ordinary_linkup_sourced_answer_spy_is_inert_and_analyst_gets_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sourced_answer_calls: list[dict[str, Any]] = []

    def forbidden_sourced_answer(*args: Any, **kwargs: Any) -> str:
        sourced_answer_calls.append({"args": args, "kwargs": dict(kwargs)})
        return f"\n\n{PROVIDER_ANSWER_MARKER}\n"

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Deep",
        report_type="quantitative_comparison",
        query_type="comparison",
        query=QUERY,
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        current_date="July 16, 2026",
        deps_overrides={"fetch_linkup_precision_block": forbidden_sourced_answer},
        environment_overrides={
            "LINKUP_API_KEY": "offline-availability-sentinel",  # pragma: allowlist secret
        },
    )

    assert sourced_answer_calls == []
    assert harness.analyst_calls == 1
    assert harness.analyst_prompts
    assert "<evidence_block>" in harness.analyst_prompts[-1]
    assert "Offline exact READ source" in harness.analyst_prompts[-1]
    assert PROVIDER_ANSWER_MARKER not in harness.analyst_prompts[-1]
    assert PROVIDER_ANSWER_MARKER not in "\n".join(harness.author_prompts)
    assert PROVIDER_ANSWER_MARKER not in outcome.report
    assert "sourcedAnswer" not in str(outcome.execution_trace)


@pytest.mark.parametrize("mode", ["Fast", "Balanced", "Deep"])
def test_all_modes_share_one_ordinary_pipeline_without_retired_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    retired_calls: list[str] = []

    def forbidden(name: str):
        def _called(*_args: Any, **_kwargs: Any) -> str:
            retired_calls.append(name)
            return PROVIDER_ANSWER_MARKER

        return _called

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode=mode,
        report_type="quantitative_comparison",
        query_type="comparison",
        query=QUERY,
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        current_date="July 16, 2026",
        deps_overrides={
            "run_scout": forbidden("run_scout"),
            "should_skip_quant_scout": lambda *_args, **_kwargs: False,
            "fetch_linkup_precision_block": forbidden("sourced_answer"),
        },
        environment_overrides={
            "LINKUP_API_KEY": "offline-availability-sentinel",  # pragma: allowlist secret
        },
    )

    assert retired_calls == []
    assert "FinalAnswerPacket readiness is blocked" in outcome.report
    assert harness.analyst_calls == (0 if mode == "Fast" else 1)
    assert harness.author_prompts == []


def test_static_ordinary_composition_prompt_queryplan_and_scheduler_are_closed() -> None:
    orchestrator_source = ORCHESTRATOR.read_text(encoding="utf-8")
    orchestrator_calls = _call_names(ORCHESTRATOR)
    assert "run_scout" not in orchestrator_source
    assert "SCOUT_REGISTRY" not in orchestrator_source
    assert "finalize_scout_continuation" not in orchestrator_source
    assert "_authorize_scout_continuation_before_scheduling" not in orchestrator_source
    assert "schedule_scout_continuation_from_pipeline_scope" not in orchestrator_source
    assert "fetch_linkup_precision_block" not in orchestrator_source
    assert "sourcedAnswer" not in orchestrator_source
    assert "run_scout" not in orchestrator_calls

    prompt_source = PROMPTS.read_text(encoding="utf-8")
    assert "SCOUT_PROMPTS" not in prompt_source
    assert "SCOUT_REPORT_TYPES" not in prompt_source
    assert "SCOUT_REGISTRY" not in prompt_source
    assert "quant_scout" not in prompt_source
    assert "jurisdiction_scout" not in prompt_source
    assert "comparator_scout" not in prompt_source

    scout_compatibility_source = SCOUT_COMPATIBILITY.read_text(encoding="utf-8")
    assert "get_scout_prompt" not in scout_compatibility_source
    assert "ask_model(" not in scout_compatibility_source
    assert "clean_json_response(" not in scout_compatibility_source

    query_plan_source = QUERY_PLAN_ADAPTER.read_text(encoding="utf-8")
    assert "finalize_scout_continuation" not in query_plan_source
    assert 'origin="scout_continuation"' not in query_plan_source
    assert 'phase="scout_directed_continuation"' not in query_plan_source

    scheduler_source = SCHEDULER.read_text(encoding="utf-8")
    assert "schedule_scout_continuation_from_pipeline_scope" not in scheduler_source
    assert 'stage="scout_directed_continuation"' not in scheduler_source
    assert 'provider_role="scout_continuation"' not in scheduler_source
    assert 'override=["exa", "linkup"]' not in scheduler_source


def test_retired_dependency_fields_are_optional_and_inert() -> None:
    for field_name in (
        "fetch_linkup_precision_block",
        "run_scout",
        "should_skip_quant_scout",
    ):
        legacy_field = next(field for field in fields(RunDeps) if field.name == field_name)
        assert legacy_field.default is None
        assert legacy_field.default_factory is MISSING


def test_retained_acquisition_and_continuation_boundaries_remain_present() -> None:
    provider_source = SEARCH_PROVIDERS.read_text(encoding="utf-8")
    assert "def search_scout_results(" in provider_source
    assert 'provider_name == "serper"' in provider_source
    assert 'provider_name == "brave"' in provider_source

    generic_source = GENERIC_ACQUISITION.read_text(encoding="utf-8")
    assert "without admitting sourcedAnswer text" in generic_source
    assert 'allow_provider_extracted_text=output_type == "searchResults"' in generic_source

    legacy_review_source = LEGACY_REVIEW.read_text(encoding="utf-8")
    assert 'scrutineer_remediation_linkup_depth_override = "deep"' in legacy_review_source
    assert "sourcedAnswer" not in legacy_review_source

    lower_level_source = PIPELINE_HELPERS.read_text(encoding="utf-8")
    assert "def fetch_linkup_precision_block(" in lower_level_source
    assert 'output_type="sourcedAnswer"' in lower_level_source
    assert "fetch_linkup_precision_block" not in ORCHESTRATOR.read_text(encoding="utf-8")
