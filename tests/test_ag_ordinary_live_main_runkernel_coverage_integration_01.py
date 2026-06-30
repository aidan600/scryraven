from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import pytest

import core.ordinary_live_main_runkernel_coverage_runtime as main_runtime
from core.ordinary_live_authority_consolidation_runtime import (
    ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY,
)
from core.ordinary_live_main_runkernel_coverage_runtime import (
    ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY,
    execute_ordinary_live_main_runkernel_coverage,
)
from core.ordinary_live_semantic_coverage_runtime import (
    ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY,
)
from core.run_kernel import RunKernel
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_PACKET,
    OfflineOrdinaryPipelineHarness,
    run_offline_ordinary_pipeline,
    scrub_offline_runtime,
)

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
PIPELINE = CORE / "pipeline_orchestrator.py"
RUNTIME = CORE / "ordinary_live_main_runkernel_coverage_runtime.py"
DOC = (
    ROOT
    / "docs"
    / "architecture"
    / "AG_ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_INTEGRATION_01.md"
)

QUERY = "What is the official current permit threshold for the example program?"
RESEARCH_QUERY = "Example program current permit threshold diagnostics"
CANDIDATE_URL = "https://official.example.gov/program/threshold"
DIAGNOSTIC_RETRIEVAL_URL = "https://retrieval.example.test/not-authority"
RAW_AUTHOR_RESPONSE = (
    "AG_ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_AUTHOR_REPORT: The answer "
    "remains limited to the ordinary offline fixture."
)
ANCHORS = (
    ("official",),
    ("current",),
    ("permit",),
    ("threshold",),
    ("500",),
)
MAIN_COMPONENT_ID = "component:ordinary-live-main-answer-primary"
FORBIDDEN_TRACE_KEYS = {
    "bounded_text",
    "raw_html",
    "raw_page_text",
    "unbounded_text",
    "answer_text",
    "citations",
    "final_answer_packet",
    "author_material",
    "prompt",
    "model_response",
    "provider_payload",
    "secret",
}


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _MainRunKernelCoverageHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=QUERY,
            core_topic="Example Program current permit threshold",
            primary_entity="Example Program",
            researcher_queries=(RESEARCH_QUERY,),
            raw_author_response=RAW_AUTHOR_RESPONSE,
            analyst_response=(
                "Analysis is limited to the retrieved diagnostic fixture source."
            ),
            logger_name=(
                "test_ag_ordinary_live_main_runkernel_coverage_integration_01"
            ),
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": 31,
                "title": "Retrieval Diagnostic Fixture",
                "url": DIAGNOSTIC_RETRIEVAL_URL,
                "text": (
                    "This retrieval passage is ordinary pipeline evidence, not "
                    "authority for ordinary-live main RunKernel coverage."
                ),
                "score": 0.99,
                "credibility": 4,
                "source_tier": "secondary",
                "source_class": "ordinary_retrieval_diagnostic",
                "currentness_signal": "unknown",
                "readable_status": "readable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": False,
                "query_ref": RESEARCH_QUERY,
                "_provider": "offline_fake_search",
            }
        ]


class FakeSourceFetchRead:
    def __init__(
        self,
        *,
        text: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self.text = text or (
            "The official current Example Program permit threshold is 500 "
            "units for the active program year."
        )
        self.extra = dict(extra or {})

    def __call__(
        self,
        *,
        candidate: Mapping[str, Any],
        source_url: str,
        source_candidate_ref: Mapping[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "candidate": dict(candidate),
                "source_url": source_url,
                "source_candidate_ref": dict(source_candidate_ref),
            }
        )
        return {
            "fetch_read_status": "readable",
            "attempted_url": source_url,
            "resolved_url": source_url,
            "final_url": source_url,
            "canonical_url": source_url,
            "resolved_domain": candidate["domain"],
            "http_status": 200,
            "content_type": "text/html; charset=utf-8",
            "retrieved_or_observed_at": "2026-06-30T12:00:00Z",
            "content_title": candidate["title"],
            "content_length": len(self.text),
            "sanitized_text": self.text,
            **self.extra,
        }


def _candidate_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example Program Permit Threshold",
            "url": CANDIDATE_URL,
            "domain": "official.example.gov",
            "snippet": "Official current permit threshold for the Example Program.",
            "published_or_observed_date": "2026-06-30",
        }
    ]


def _run_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    main_enabled: bool,
    candidate_enabled: bool = False,
    source_enabled: bool = False,
    semantic_enabled: bool = False,
    consolidation_enabled: bool = False,
    candidate_results: Sequence[dict[str, Any]] | Mapping[str, Any] | None = None,
    fetcher: Any | None = None,
) -> tuple[dict[str, Any], _MainRunKernelCoverageHarness, Any]:
    harness = _MainRunKernelCoverageHarness(tmp_path)
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-30",
        session_id="ag-ordinary-live-main-runkernel-coverage-session",
        run_id="ag-ordinary-live-main-runkernel-coverage-run",
        capture_stages=(HANDOFF_PACKET,),
        enable_ordinary_live_candidate_handoff=candidate_enabled,
        ordinary_live_candidate_handoff_results=candidate_results,
        enable_ordinary_live_source_custody=source_enabled,
        ordinary_live_source_fetch_read=fetcher,
        ordinary_live_source_custody_anchor_groups=ANCHORS,
        enable_ordinary_live_semantic_coverage=semantic_enabled,
        enable_ordinary_live_authority_consolidation=consolidation_enabled,
        enable_ordinary_live_main_runkernel_coverage=main_enabled,
    )
    return captured, harness, outcome


def test_default_disabled_run_pipeline_behavior_remains_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()

    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        main_enabled=False,
        fetcher=fetcher,
    )

    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert (
        ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY
        not in outcome.execution_trace
    )
    assert fetcher.calls == []
    assert harness.forbidden_live_calls == []


def test_existing_child_consolidation_behavior_is_unchanged_when_new_flag_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        main_enabled=False,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=True,
        consolidation_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    consolidation = outcome.execution_trace[
        ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY
    ]
    assert (
        ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY
        not in outcome.execution_trace
    )
    assert consolidation["failed_closed"] is True
    assert consolidation["readiness_blocker_if_any"] == (
        "main_answer_component_binding_missing"
    )
    assert consolidation["component_equivalence_posture"] == (
        "unknown_requires_architecture_decision"
    )


def test_run_pipeline_reduces_main_semantic_observation_and_component_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()

    captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        main_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    projection = outcome.execution_trace[
        ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY
    ]
    run_kernel = captured["run_kernel"]
    assert projection["ran"] is True, json.dumps(projection, indent=2, sort_keys=True)
    assert projection["failed_closed"] is False
    assert projection["runtime_consumer"] == "core.pipeline_orchestrator.run_pipeline"
    assert projection["main_run_kernel_consumed"] is True
    assert projection["source_custody_authority_owner"] == "main_run_kernel"
    assert projection["semantic_observation_authority_owner"] == "main_run_kernel"
    assert projection["component_coverage_authority_owner"] == "main_run_kernel"
    assert run_kernel.state.initial_answer_contract
    assert run_kernel.state.semantic_observation_admission_history
    assert run_kernel.state.component_coverage_history
    assert projection["main_semantic_observation_admitted_count"] == len(
        run_kernel.state.semantic_observation_admission_history
    )
    assert projection["main_component_coverage_reduced_count"] == len(
        run_kernel.state.component_coverage_history
    )
    assert len(fetcher.calls) == 1
    assert harness.forbidden_live_calls == []


def test_component_coverage_exactly_matches_main_accepted_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        main_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    run_kernel = captured["run_kernel"]
    projection = outcome.execution_trace[
        ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY
    ]
    accepted = next(
        ref
        for ref in run_kernel.state.initial_answer_contract[
            "accepted_answer_component_refs"
        ]
        if ref["component_id"] == MAIN_COMPONENT_ID
    )
    coverage = run_kernel.state.component_coverage_projection
    assert coverage["answer_component_id"] == accepted["component_id"]
    assert coverage["component_revision"] == accepted["component_revision"]
    assert coverage["component_digest"] == accepted["component_digest"]
    assert projection["main_accepted_answer_component_ref"]["component_id"] == (
        MAIN_COMPONENT_ID
    )
    assert (
        projection["exact_component_id_revision_digest_match_with_main_contract"]
        is True
    )
    assert projection["legacy_365_blocker_resolved"] is True
    assert projection["structural_readiness_input_compatibility"] is True
    assert projection["readiness_input_compatibility_status"] == (
        "main_component_coverage_available"
    )
    assert projection["main_answer_component_binding_missing"] is False


def test_new_path_is_not_child_only_or_projection_rehydration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        main_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    projection = outcome.execution_trace[
        ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY
    ]
    assert ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY not in outcome.execution_trace
    assert projection["child_kernel_used"] is False
    assert projection["child_acquisition_only"] is False
    assert projection["projection_to_runkernel_rehydration"] is False
    assert projection["direct_runkernel_mutation"] is False
    assert "child-only ComponentCoverage" in (
        projection["forbidden_substitute_outputs_ruled_out"]
    )


def test_missing_main_component_creation_fails_closed_with_named_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_candidate_handoff(**_kwargs: Any) -> Any:
        return SimpleNamespace(
            projection={
                "failed_closed": True,
                "first_failed_seam": "accepted_current_answer_contract_missing",
            },
            candidate_packet=None,
        )

    monkeypatch.setattr(
        main_runtime,
        "execute_ordinary_live_candidate_handoff",
        fake_candidate_handoff,
    )

    result = execute_ordinary_live_main_runkernel_coverage(
        main_run_kernel=RunKernel.start(run_id="main-run", request_id="main-request"),
        query=QUERY,
        requested_mode="Balanced",
        run_contract_projection={},
        candidate_results=_candidate_results(),
        fetch_read=FakeSourceFetchRead(),
    )

    projection = result.projection
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == (
        "accepted_current_answer_contract_missing"
    )
    assert projection["structural_readiness_input_compatibility"] is False
    assert projection["projection_to_runkernel_rehydration"] is False
    assert projection["direct_runkernel_mutation"] is False


def test_trace_projection_is_safe_and_keeps_closed_surfaces_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        main_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    projection = outcome.execution_trace[
        ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY
    ]
    assert _all_keys(projection).isdisjoint(FORBIDDEN_TRACE_KEYS)
    assert "bounded_text" not in json.dumps(projection, sort_keys=True)
    for key in (
        "provider_search_calls",
        "search_calls",
        "broker_calls",
        "fetch_read_calls",
        "model_calls",
        "retrieval_calls",
        "source_obligation_satisfaction_decisions",
        "citation_eligibility_decisions",
        "citation_rendering_decisions",
        "sufficiency_readiness_reductions",
        "final_answer_packet_creations",
        "author_authorprose_invocations",
        "answer_text_creations",
        "product_correctness_claims",
    ):
        assert projection[key] == 0
    for key in (
        "source_obligation_satisfied",
        "citation_eligible",
        "citation_created",
        "citation_rendered_or_eligible",
        "sufficiency_readiness_reduced",
        "fap_created",
        "author_invoked",
        "answer_text_created",
        "product_correctness_claimed",
    ):
        assert projection[key] is False
    assert harness.forbidden_live_calls == []


def test_product_code_does_not_import_scripts_ag_harnesses() -> None:
    for path in CORE.rglob("*.py"):
        imports = _imports(path)
        assert not any(name == "scripts" or name.startswith("scripts.") for name in imports)
    for path in (PIPELINE, RUNTIME):
        source = path.read_text(encoding="utf-8")
        assert "scripts/ag_" not in source
        assert "from scripts import ag_" not in source


def test_helper_does_not_mutate_runkernel_state_directly() -> None:
    tree = ast.parse(RUNTIME.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        for target in targets:
            assert not _is_state_attribute(target)


def test_pipeline_orchestrator_contains_only_minimal_main_coverage_callsite() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    consolidation_call = source.index(
        "execute_ordinary_live_authority_consolidation("
    )
    retrieval_state = source.index("all_passages: list[dict[str, Any]] = []")
    output_trace = source.index(
        "execution_trace = post_author_output_packaging.execution_trace"
    )
    main_call = source.rindex("execute_ordinary_live_main_runkernel_coverage(")
    trace_insert = source.index(
        "execution_trace[ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY]"
    )

    assert consolidation_call < retrieval_state < output_trace < main_call < trace_insert
    for forbidden in (
        "build_evidence_relative_analysis_packet",
        "admit_semantic_observations_from_analysis_support_findings",
        "ComponentCoverageRecord",
        "EvidenceLedgerSnapshotBinding",
    ):
        assert forbidden not in source


def test_docs_record_repair_scope_and_next_checkpoint() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "Mode: REPAIR",
        "ordinary_live_main_runkernel_coverage",
        "main RunKernel",
        "ComponentCoverage",
        "SemanticObservation admission",
        "legacy_365_blocker_resolved",
        "provider/search calls: 0",
        "Closed Surfaces",
        "Explicit Non-Proofs",
        "AG-ORDINARY-LIVE-ENTRYPOINT-VISIBILITY-01",
    )
    for needle in required:
        assert needle in text


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _is_state_attribute(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        value = node.value
        if isinstance(value, ast.Attribute) and value.attr == "state":
            return True
        return _is_state_attribute(value)
    if isinstance(node, ast.Subscript):
        return _is_state_attribute(node.value)
    if isinstance(node, ast.Tuple | ast.List):
        return any(_is_state_attribute(item) for item in node.elts)
    return False


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
