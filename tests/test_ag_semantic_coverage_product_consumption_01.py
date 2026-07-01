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
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from proplex.live_semantic_coverage_status import (
    LIVE_SEMANTIC_COVERAGE_STATUS_FLAG,
    build_live_semantic_coverage_status,
)
from tests.test_ag_live_acquisition_readability_product_consumption_01 import (
    QUERY,
    _retained_repo,
)

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_MODULE = ROOT / "proplex" / "live_semantic_coverage_status.py"


def test_product_status_consumes_readiness_and_reports_semantic_coverage_blocker(
    tmp_path: Path,
) -> None:
    repo_root, candidate = _retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
    )

    assert result.decision == "BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING"
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
    assert "SemanticObservation admission status: BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING" in result.output
    assert "SemanticObservation id/ref/digest: unavailable" in result.output
    assert "ComponentCoverage status: BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING" in result.output
    assert "ComponentCoverage id/ref/digest: unavailable" in result.output
    assert f"component id/ref: {candidate['component_id']}" in result.output
    assert "source obligation id/ref:" in result.output
    assert "semantic support cannot be inferred from URL/domain/snippet/custody/lineage" in result.output
    assert "coverage cannot bind to custody/lineage alone" in result.output
    assert "ad hoc semantic matcher/heuristic avoided: true" in result.output
    assert "raw/private retention: false" in result.output
    assert "citation eligibility/rendering" in result.output
    assert "source-obligation satisfaction" in result.output
    assert "SufficiencyReadiness" in result.output
    assert "FinalAnswerPacket" in result.output
    assert "Author/AuthorProse" in result.output
    assert "decision: BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING" in result.output

    semantic = result.payload["semantic_observation_admission_ref"]
    assert semantic["status"] == "BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING"
    coverage = result.payload["component_coverage_ref"]
    assert coverage["status"] == "BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING"
    assert coverage["component_id"] == candidate["component_id"]
    admission = result.payload["source_evidence_admission_ref"]
    assert admission["candidate_content_custody_is_semantic_support"] is False
    assert result.payload["ad_hoc_semantic_matcher_avoided"] is True
    assert "bounded_text" not in result.output
    assert "official current Example Program permit threshold is 500" not in result.output
    assert "source-obligation satisfaction claimed: true" not in result.output
    assert "citation eligibility claimed: true" not in result.output
    assert "answer prose:" not in result.output


def test_cli_flag_is_default_off_and_skips_live_key_validation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _import_cli_with_dotenv_disabled(monkeypatch)
    calls: list[str] = []

    def fake_status(**_kwargs: Any) -> Any:
        calls.append("status")
        return SimpleNamespace(return_code=0, output="decision: BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING")

    def fail_key_validation(**_kwargs: Any) -> list[str]:
        raise AssertionError("status path must not validate live provider keys")

    def fail_pipeline(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("status path must not run the pipeline")

    monkeypatch.setattr(cli, "build_live_semantic_coverage_status", fake_status)
    monkeypatch.setattr(cli, "missing_required_api_keys", fail_key_validation)
    monkeypatch.setattr(cli, "run_pipeline", fail_pipeline)

    assert cli.main([QUERY, LIVE_SEMANTIC_COVERAGE_STATUS_FLAG]) == 0

    assert calls == ["status"]
    assert "decision: BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING" in capsys.readouterr().out


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
