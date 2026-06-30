from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import pytest

import core.pipeline_orchestrator as orchestrator
from core.live_ordinary_candidate_handoff_runtime import (
    ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY,
)
from core.ordinary_live_semantic_coverage_runtime import (
    ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY,
    execute_ordinary_live_semantic_coverage,
)
from core.ordinary_live_source_custody_runtime import (
    ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY,
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
RUNTIME = CORE / "ordinary_live_semantic_coverage_runtime.py"
DOC = (
    ROOT
    / "docs"
    / "architecture"
    / "AG_ORDINARY_LIVE_SEMANTIC_COVERAGE_INTEGRATION_01.md"
)
QUERY = "What is the official current permit threshold for the example program?"
RESEARCH_QUERY = "Example program current permit threshold diagnostics"
CANDIDATE_URL = "https://official.example.gov/program/threshold"
DIAGNOSTIC_RETRIEVAL_URL = "https://retrieval.example.test/not-authority"
RAW_AUTHOR_RESPONSE = (
    "AG_ORDINARY_LIVE_SEMANTIC_COVERAGE_INTEGRATION_AUTHOR_REPORT: The "
    "example program threshold remains bound to the offline fixture source "
    f"[[31]]({DIAGNOSTIC_RETRIEVAL_URL})."
)
ANCHORS = (
    ("official",),
    ("current",),
    ("permit",),
    ("threshold",),
    ("500",),
)
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


class _SemanticCoverageHarness(OfflineOrdinaryPipelineHarness):
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
            logger_name="test_ag_ordinary_live_semantic_coverage_integration_01",
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": 31,
                "title": "Retrieval Diagnostic Fixture",
                "url": DIAGNOSTIC_RETRIEVAL_URL,
                "text": (
                    "This retrieval passage is ordinary pipeline evidence, "
                    "not semantic support authority for the new seam."
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
    candidate_enabled: bool,
    source_enabled: bool,
    semantic_enabled: bool,
    candidate_results: Sequence[dict[str, Any]] | Mapping[str, Any] | None = None,
    fetcher: Any | None = None,
) -> tuple[dict[str, Any], _SemanticCoverageHarness, Any]:
    harness = _SemanticCoverageHarness(tmp_path)
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-30",
        session_id="ag-ordinary-live-semantic-coverage-session",
        run_id="ag-ordinary-live-semantic-coverage-run",
        capture_stages=(HANDOFF_PACKET,),
        enable_ordinary_live_candidate_handoff=candidate_enabled,
        ordinary_live_candidate_handoff_results=candidate_results,
        enable_ordinary_live_source_custody=source_enabled,
        ordinary_live_source_fetch_read=fetcher,
        ordinary_live_source_custody_anchor_groups=ANCHORS,
        enable_ordinary_live_semantic_coverage=semantic_enabled,
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
        candidate_enabled=False,
        source_enabled=False,
        semantic_enabled=False,
        fetcher=fetcher,
    )

    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY not in outcome.execution_trace
    assert ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY not in outcome.execution_trace
    assert ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY not in outcome.execution_trace
    assert fetcher.calls == []
    assert harness.forbidden_live_calls == []


def test_candidate_and_source_enabled_semantic_disabled_preserves_363_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()

    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=False,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    source_projection = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    assert source_projection["status"] == "source_custody_reduced"
    assert source_projection["ran"] is True
    assert ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY not in outcome.execution_trace
    assert len(fetcher.calls) == 1


def test_run_pipeline_consumes_in_memory_source_custody_and_reduces_semantic_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()
    helper_inputs: list[dict[str, Any]] = []
    original_semantic = orchestrator.execute_ordinary_live_semantic_coverage

    def spy_semantic(**kwargs: Any) -> Any:
        helper_inputs.append(dict(kwargs))
        return original_semantic(**kwargs)

    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_live_semantic_coverage",
        spy_semantic,
    )

    captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY]
    assert helper_inputs
    assert not isinstance(helper_inputs[0]["source_custody_result"], Mapping)
    assert helper_inputs[0]["source_custody_result"].fetch_read_content_packet
    assert helper_inputs[0]["source_custody_result"].sanitized_content_reference
    assert helper_inputs[0]["source_custody_result"].evidence_ledger_projection
    assert projection["runtime_consumer"] == "core.pipeline_orchestrator.run_pipeline"
    assert projection["ran"] is True, json.dumps(projection, indent=2, sort_keys=True)
    assert projection["failed_closed"] is False
    assert projection["status"] == "semantic_observation_and_component_coverage_reduced"
    assert projection["source_custody_result_object_consumed"] is True
    assert projection["source_custody_projection_only_consumed"] is False
    assert projection["source_came_from_ordinary_source_custody"] is True
    assert projection["retrieval_diagnostics_used_as_semantic_authority"] is False
    assert projection["evidence_relative_analysis_packet_attempted_count"] == 1
    assert projection["evidence_relative_analysis_packet_built_count"] == 1
    assert projection["semantic_observation_attempted_count"] == 1
    assert projection["semantic_observation_admitted_count"] == 1
    assert projection["component_coverage_attempted_count"] == 1
    assert projection["component_coverage_reduced_count"] == 1
    assert projection["evidence_relative_analysis_packet_ref"]["finding_count"] == 1
    assert projection["semantic_observation_ref"]["observation_id"]
    assert projection["component_coverage_ref"]["coverage_record_id"]
    child_kernel = helper_inputs[0]["run_kernel"]
    assert child_kernel.state.semantic_observation_admission_history
    assert child_kernel.state.component_coverage_history
    assert captured["run_kernel"].state.semantic_observation_admission_history == []
    assert captured["run_kernel"].state.component_coverage_history == []
    assert fetcher.calls[0]["source_url"] == CANDIDATE_URL
    assert harness.forbidden_live_calls == []


def test_component_identity_and_readiness_blocker_are_recorded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY]
    assert projection["coverage_component_id"] == (
        "component:ordinary-live-candidate-handoff-primary"
    )
    assert projection["coverage_component_digest"]
    assert projection["coverage_component_contract_kind"] == (
        "bounded_child_candidate_source_custody_component"
    )
    assert projection["coverage_is_final_answer_component_support"] is False
    assert projection["readiness_build_precondition_met"] is False
    assert projection["readiness_blocker_if_any"] == (
        "coverage_not_bound_to_main_answer_readiness_component"
    )


def test_child_kernel_boundary_records_semantic_and_coverage_debt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY]
    owned = " ".join(projection["child_kernel_state_owned"])
    not_owned = " ".join(projection["child_kernel_state_not_owned"])
    assert projection["child_kernel_used"] is True
    assert projection["child_kernel_owner"] == "ordinary_live_candidate_handoff_run_kernel"
    assert "SemanticObservation admission" in owned
    assert "ComponentCoverage reduction" in owned
    assert "FinalAnswerPacket" in not_owned
    assert "Author/AuthorProse" in not_owned
    assert projection["child_kernel_temporary_architecture_debt"] is True
    assert "AG-ORDINARY-LIVE-AUTHORITY-CONSOLIDATION" in (
        projection["child_kernel_future_consolidation_path"]
    )


def test_missing_source_custody_result_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()

    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=False,
        semantic_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY]
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == "ordinary_live_source_custody_result_missing"
    assert projection["semantic_observation_admitted_count"] == 0
    assert projection["component_coverage_reduced_count"] == 0
    assert fetcher.calls == []


def test_missing_in_memory_runkernel_fails_closed_without_projection_rehydration() -> None:
    result = execute_ordinary_live_semantic_coverage(
        run_kernel=None,
        parent_run_id="parent-run",
        parent_request_id="parent-request",
        source_custody_result=SimpleNamespace(
            projection={"status": "source_custody_reduced"},
            fetch_read_content_packet={"packet_id": "packet"},
            sanitized_content_reference={"reference_id": "reference"},
            evidence_ledger_projection={"fetch_read_candidate_custody": {}},
        ),
    )

    projection = result.projection
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == "ordinary_candidate_handoff_run_kernel_missing"
    assert projection["projection_to_runkernel_rehydration"] is False
    assert projection["direct_runkernel_mutation"] is False


def test_diagnostic_shaped_fields_are_rejected_as_semantic_authority() -> None:
    result = execute_ordinary_live_semantic_coverage(
        run_kernel=RunKernel.start(run_id="diagnostic-run", request_id="diagnostic-request"),
        parent_run_id="parent-run",
        parent_request_id="parent-request",
        source_custody_result={"provider_diagnostics": {"result_count": 1}},
    )

    projection = result.projection
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == "diagnostic_semantic_authority_rejected"
    assert projection["retrieval_diagnostics_used_as_semantic_authority"] is False
    assert projection["semantic_observation_admitted_count"] == 0
    assert projection["component_coverage_reduced_count"] == 0


def test_semantic_coverage_trace_is_safe_and_keeps_closed_surfaces_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY]
    assert _all_keys(projection).isdisjoint(FORBIDDEN_TRACE_KEYS)
    assert "bounded_text" not in json.dumps(projection, sort_keys=True)
    assert projection["provider_search_calls"] == 0
    assert projection["search_calls"] == 0
    assert projection["broker_calls"] == 0
    assert projection["fetch_read_calls"] == 0
    assert projection["model_calls"] == 0
    assert projection["retrieval_calls"] == 0
    assert projection["source_obligation_satisfaction_decisions"] == 0
    assert projection["citation_eligibility_decisions"] == 0
    assert projection["citation_rendering_decisions"] == 0
    assert projection["sufficiency_readiness_reductions"] == 0
    assert projection["final_answer_packet_creations"] == 0
    assert projection["author_authorprose_invocations"] == 0
    assert projection["answer_text_creations"] == 0
    assert projection["product_correctness_claims"] == 0
    for key in (
        "source_obligation_satisfied",
        "citation_eligible",
        "citation_created",
        "citation_rendered",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
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


def test_pipeline_orchestrator_contains_only_minimal_semantic_callsite() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    candidate_call = source.index("execute_ordinary_live_candidate_handoff(")
    source_call = source.index(
        "ordinary_live_source_custody = execute_ordinary_live_source_custody("
    )
    semantic_call = source.index(
        "ordinary_live_semantic_coverage = execute_ordinary_live_semantic_coverage("
    )
    retrieval_state = source.index("all_passages: list[dict[str, Any]] = []")
    retrieval_dispatch = source.index("execute_main_retrieval_pass_from_scope(")

    assert candidate_call < source_call < semantic_call < retrieval_state
    assert semantic_call < retrieval_dispatch
    for forbidden in (
        "build_evidence_relative_analysis_packet",
        "admit_semantic_observations_from_analysis_support_findings",
        "ComponentCoverageRecord",
        "EvidenceLedgerSnapshotBinding",
    ):
        assert forbidden not in source
    assert "scripts/ag_" not in RUNTIME.read_text(encoding="utf-8")


def test_docs_record_repair_mode_boundary_child_debt_and_next_checkpoint() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "Mode: REPAIR",
        "EvidenceLedger custody + bounded sanitized source content",
        "enable_ordinary_live_semantic_coverage",
        "ordinary_live_semantic_coverage",
        "core.pipeline_orchestrator.py` remains a narrow compatibility shell",
        "SemanticObservation admission",
        "ComponentCoverage reduction",
        "coverage_is_final_answer_component_support = false",
        "coverage_not_bound_to_main_answer_readiness_component",
        "provider/search calls: 0",
        "Closed Surfaces",
        "Explicit Non-Proofs",
        "AG-ORDINARY-LIVE-AUTHORITY-CONSOLIDATION-AND-READINESS-PRECONDITION-01",
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
