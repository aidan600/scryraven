"""PRODUCT-PATH-REGRESSION: ordinary CLI citation/source-obligation readiness.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-citation-source-obligation-readiness-status-dry-run
Runtime consumer: proplex.__main__ -> proplex.live_citation_source_obligation_readiness_status
Why ordinary product-path work cannot be done directly: not applicable; this
test guards the direct ordinary status path with fixture-sized retained artifacts
so private local output is not required.
Integration deadline: current phase.
Exit condition: keep while the default-off status flag exists.
Why this is not a shadow product path: it invokes the product status builder and
CLI dispatch, not a standalone script.
Forbidden interpretation: this is not semantic support, ComponentCoverage,
citation eligibility, citation rendering, source-obligation satisfaction,
Sufficiency, FAP, Author behavior, answer text, answerability, or product
correctness.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from proplex.live_citation_source_obligation_readiness_status import (
    LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG,
    build_live_citation_source_obligation_readiness_status,
)
from tests.test_ag_live_acquisition_readability_product_consumption_01 import (
    QUERY,
    _retained_repo,
)

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_MODULE = ROOT / "proplex" / "live_citation_source_obligation_readiness_status.py"


def test_product_status_consumes_custody_into_readiness_posture(
    tmp_path: Path,
) -> None:
    repo_root, candidate = _retained_repo(tmp_path)

    result = build_live_citation_source_obligation_readiness_status(
        query=QUERY,
        repo_root=repo_root,
    )

    assert result.decision == "PASS"
    assert result.return_code == 0
    assert "mode: BUILD" in result.output
    assert "ordinary entrypoint: python -m proplex" in result.output
    assert "usable-answer verdict target: YES" in result.output
    assert "answerability/correctness: not claimed" in result.output
    assert "retained search candidate status: preflight_passed" in result.output
    assert "selected candidate rank: 1" in result.output
    assert "selected candidate domain: official.example.gov" in result.output
    assert f"selected candidate URL: {candidate['url']}" in result.output
    assert "fetch/read handoff status: retained_packet_verified" in result.output
    assert "source/evidence custody/admission status: custody_created" in result.output
    assert "citation/source-obligation readiness posture: not_yet_semantically_supported" in result.output
    assert "custody is not semantic support" in result.output
    assert "SemanticObservation and ComponentCoverage remain closed" in result.output
    assert "source obligation id/ref:" in result.output
    assert "lineage-only; satisfaction not claimed" in result.output
    assert f"component id/ref: {candidate['component_id']}" in result.output
    assert "coverage not bound" in result.output
    assert "raw/private retention: false" in result.output
    assert "citation eligibility claim" in result.output
    assert "citation rendering" in result.output
    assert "source-obligation satisfaction" in result.output
    assert "decision: PASS" in result.output

    readiness = result.payload["citation_source_obligation_readiness_ref"]
    assert readiness["posture"] == "not_yet_semantically_supported"
    assert (
        readiness["next_blocked_surface"]
        == "semantic support/admission and component coverage product consumption"
    )
    source_ref = result.payload["source_obligation_ref"]
    assert source_ref["source_obligation_candidate_ids"] == candidate[
        "source_obligation_candidate_ids"
    ]
    assert source_ref["lineage_only"] is True
    assert source_ref["satisfaction_claimed"] is False
    component_ref = result.payload["component_ref"]
    assert component_ref["component_id"] == candidate["component_id"]
    assert component_ref["lineage_only"] is True
    assert component_ref["component_coverage_bound"] is False
    admission_ref = result.payload["source_evidence_admission_ref"]
    assert admission_ref["candidate_content_custody_is_semantic_support"] is False
    assert admission_ref["citation_eligible"] is False
    assert admission_ref["source_obligation_satisfied"] is False
    assert admission_ref["component_coverage_created"] is False
    assert admission_ref["sufficiency_decided"] is False
    assert admission_ref["final_answer_packet_created"] is False
    assert admission_ref["author_input_created"] is False
    assert admission_ref["product_correctness_claimed"] is False
    assert "bounded_text" not in result.output
    assert "official current Example Program permit threshold is 500" not in result.output


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

    monkeypatch.setattr(
        cli,
        "build_live_citation_source_obligation_readiness_status",
        fake_status,
    )
    monkeypatch.setattr(cli, "missing_required_api_keys", fail_key_validation)
    monkeypatch.setattr(cli, "run_pipeline", fail_pipeline)

    assert (
        cli.main([QUERY, LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG])
        == 0
    )

    assert calls == ["status"]
    assert "decision: PASS" in capsys.readouterr().out


def test_product_status_module_does_not_directly_import_closed_downstream_surfaces() -> None:
    imported = _imports(PRODUCT_MODULE)
    forbidden_imports = {
        "core.semantic_observation_admission_bridge",
        "core.semantic_observation_admission_runtime",
        "core.component_coverage_record",
        "core.component_coverage_reduction_runtime",
        "core.sufficiency_readiness_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_hardening_runtime",
        "core.author_execution_runtime",
        "core.author_prose_finalization_runtime",
        "core.retrieval",
        "core.search_providers",
        "dotenv",
        "openai",
        "requests",
        "httpx",
    }
    assert imported.isdisjoint(forbidden_imports)


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
