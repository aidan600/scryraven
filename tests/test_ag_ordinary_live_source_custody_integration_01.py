from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

import core.pipeline_orchestrator as orchestrator
from core.fetch_read_content_reference import (
    validate_fetch_read_content_packet,
)
from core.live_ordinary_candidate_handoff_runtime import (
    ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY,
)
from core.ordinary_live_source_custody_runtime import (
    ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY,
    execute_ordinary_live_source_custody,
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
CANDIDATE_RUNTIME = CORE / "live_ordinary_candidate_handoff_runtime.py"
SOURCE_RUNTIME = CORE / "ordinary_live_source_custody_runtime.py"
QUERY = "What is the official current permit threshold for the example program?"
RESEARCH_QUERY = "Example program current permit threshold diagnostics"
CANDIDATE_URL = "https://official.example.gov/program/threshold"
DIAGNOSTIC_RETRIEVAL_URL = "https://retrieval.example.test/not-authority"
RAW_AUTHOR_RESPONSE = (
    "AG_ORDINARY_LIVE_SOURCE_CUSTODY_INTEGRATION_AUTHOR_REPORT: The example "
    "program threshold remains bound to the offline fixture source [[31]]"
    f"({DIAGNOSTIC_RETRIEVAL_URL})."
)
ANCHORS = (
    ("official",),
    ("current",),
    ("permit",),
    ("threshold",),
    ("500",),
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _SourceCustodyHarness(OfflineOrdinaryPipelineHarness):
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
            logger_name="test_ag_ordinary_live_source_custody_integration_01",
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": 31,
                "title": "Retrieval Diagnostic Fixture",
                "url": DIAGNOSTIC_RETRIEVAL_URL,
                "text": (
                    "This retrieval passage is ordinary pipeline evidence, "
                    "not source-custody authority for the new seam."
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
    candidate_results: Sequence[dict[str, Any]] | Mapping[str, Any] | None = None,
    fetcher: Any | None = None,
) -> tuple[dict[str, Any], _SourceCustodyHarness, Any]:
    harness = _SourceCustodyHarness(tmp_path)
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-30",
        session_id="ag-ordinary-live-source-custody-session",
        run_id="ag-ordinary-live-source-custody-run",
        capture_stages=(HANDOFF_PACKET,),
        enable_ordinary_live_candidate_handoff=candidate_enabled,
        ordinary_live_candidate_handoff_results=candidate_results,
        enable_ordinary_live_source_custody=source_enabled,
        ordinary_live_source_fetch_read=fetcher,
        ordinary_live_source_custody_anchor_groups=ANCHORS,
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
        fetcher=fetcher,
    )

    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY not in outcome.execution_trace
    assert ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY not in outcome.execution_trace
    assert fetcher.calls == []
    assert harness.forbidden_live_calls == []


def test_candidate_handoff_enabled_source_custody_disabled_preserves_362_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()

    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=False,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    candidate_projection = outcome.execution_trace[
        ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY
    ]
    assert candidate_projection["status"] == "search_result_candidate_packet_built"
    assert candidate_projection["ran"] is True
    assert ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY not in outcome.execution_trace
    assert fetcher.calls == []


def test_run_pipeline_consumes_candidate_packet_into_source_custody(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()
    source_results: list[Any] = []
    ledger_authorizations: list[dict[str, Any]] = []
    original_source = orchestrator.execute_ordinary_live_source_custody
    original_authorize = RunKernel.authorize_evidence_ledger_reduction

    def spy_source(**kwargs: Any) -> Any:
        result = original_source(**kwargs)
        source_results.append(result)
        return result

    def spy_authorize(self: RunKernel, *args: Any, **kwargs: Any) -> Any:
        ledger_authorizations.append(dict(kwargs))
        return original_authorize(self, *args, **kwargs)

    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_live_source_custody",
        spy_source,
    )
    monkeypatch.setattr(
        RunKernel,
        "authorize_evidence_ledger_reduction",
        spy_authorize,
    )

    captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    assert projection["runtime_consumer"] == "core.pipeline_orchestrator.run_pipeline"
    assert projection["ran"] is True, json.dumps(
        projection,
        indent=2,
        sort_keys=True,
    )
    assert projection["failed_closed"] is False
    assert projection["status"] == "source_custody_reduced"
    assert projection["source_selected_from_search_result_candidate_packet"] is True
    assert projection["retrieval_diagnostics_used_as_source_authority"] is False
    assert projection["source_candidate"]["url"] == CANDIDATE_URL
    assert projection["source_candidate"]["url"] != DIAGNOSTIC_RETRIEVAL_URL
    assert fetcher.calls[0]["source_url"] == CANDIDATE_URL
    assert len(fetcher.calls) == 1
    assert projection["fetch_read_attempted_count"] == 1
    assert projection["fetch_read_completed_count"] == 1
    assert projection["fetch_read_content_packet_ref"]["packet_id"]
    assert projection["sanitized_content_reference_ref"]["reference_id"]
    assert projection["evidence_ledger_custody_count"] == 1
    assert projection["evidence_ledger_custody_ref"]["custody_record_id"]
    assert ledger_authorizations
    assert source_results
    result = source_results[0]
    assert result.fetch_read_content_packet is not None
    assert validate_fetch_read_content_packet(result.fetch_read_content_packet)
    assert result.sanitized_content_reference is not None
    assert result.evidence_ledger_projection["owner"] == "RunKernel.EvidenceLedger"
    assert captured["run_kernel"].state.search_executor_handoff_state == {}
    assert captured["run_kernel"].state.live_search_validation_state == {}
    assert harness.forbidden_live_calls == []


def test_source_custody_projection_preserves_child_kernel_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()

    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    lineage = projection["child_kernel_parent_lineage"]
    assert projection["child_kernel_used"] is True
    assert projection["child_kernel_owner"] == "ordinary_live_candidate_handoff_run_kernel"
    assert projection["child_kernel_lifetime"] == (
        "in_memory_for_single_run_pipeline_invocation"
    )
    assert lineage["parent_run_id"] == "ag-ordinary-live-source-custody-run"
    assert lineage["child_run_id"].endswith(":ordinary-live-candidate-handoff")
    assert "EvidenceLedger candidate/content custody" in " ".join(
        projection["child_kernel_state_owned"]
    )
    assert "SemanticObservation" in projection["child_kernel_state_not_owned"]
    assert projection["child_kernel_temporary_architecture_debt"] is True
    assert "AG-ORDINARY-LIVE-SEMANTIC-COVERAGE-INTEGRATION-01" in (
        projection["child_kernel_future_consolidation_path"]
    )


def test_source_custody_closed_surfaces_and_zero_live_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()

    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    assert harness.forbidden_live_calls == []
    for key in (
        "provider_search_calls",
        "search_calls",
        "broker_calls",
        "model_calls",
        "retrieval_calls",
        "semantic_observation_admissions",
        "component_coverage_reductions",
        "citation_eligibility_decisions",
        "citation_rendering_decisions",
        "source_obligation_satisfaction_decisions",
        "sufficiency_readiness_reductions",
        "final_answer_packet_creations",
        "author_authorprose_invocations",
    ):
        assert projection[key] == 0
    for key in (
        "raw_html_retained",
        "raw_headers_retained",
        "raw_cookies_retained",
        "raw_page_text_retained",
        "raw_page_content_retained",
        "semantic_observation_created",
        "component_coverage_created",
        "citation_eligible",
        "source_obligation_satisfied",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "product_correctness_claimed",
    ):
        assert projection[key] is False
    summary = projection["evidence_ledger_custody_projection_summary"]
    assert summary["candidate_content_custody_is_semantic_support"] is False
    assert summary["bounded_content_payload_retained"] is False


def test_source_custody_fails_closed_without_candidate_handoff_packet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()

    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=False,
        source_enabled=True,
        fetcher=fetcher,
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == "search_result_candidate_packet_missing"
    assert projection["fetch_read_attempted_count"] == 0
    assert projection["evidence_ledger_custody_count"] == 0
    assert fetcher.calls == []


def test_diagnostic_shaped_fields_are_rejected_as_source_authority() -> None:
    fetcher = FakeSourceFetchRead()
    kernel = RunKernel.start(
        run_id="ag-ordinary-live-source-custody-diagnostic-run",
        request_id="ag-ordinary-live-source-custody-diagnostic-request",
        request={
            "parent_run_id": "parent-run",
            "parent_request_id": "parent-request",
        },
    )

    result = execute_ordinary_live_source_custody(
        run_kernel=kernel,
        parent_run_id="parent-run",
        parent_request_id="parent-request",
        candidate_packet={"provider_diagnostics": {"url": CANDIDATE_URL}},
        fetch_read=fetcher,
    )

    projection = result.projection
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == "diagnostic_source_authority_rejected"
    assert projection["retrieval_diagnostics_used_as_source_authority"] is False
    assert projection["fetch_read_attempted_count"] == 0
    assert fetcher.calls == []


def test_fake_fetch_read_raw_or_closed_fields_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead(extra={"raw_html": "<html>nope</html>"})

    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == "offline_fetch_read_result_invalid"
    assert projection["fetch_read_attempted_count"] == 1
    assert projection["fetch_read_completed_count"] == 1
    assert projection["fetch_read_content_packet_ref"] == {}
    assert projection["evidence_ledger_custody_count"] == 0


def test_product_code_does_not_import_scripts_ag_harnesses() -> None:
    for path in (PIPELINE, CANDIDATE_RUNTIME, SOURCE_RUNTIME):
        imports = _imports(path)
        assert not any(name == "scripts" or name.startswith("scripts.") for name in imports)
        source = path.read_text(encoding="utf-8")
        assert "scripts/ag_" not in source
        assert "from scripts import ag_" not in source


def test_pipeline_orchestrator_contains_only_minimal_source_custody_callsite() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    candidate_call = source.index("execute_ordinary_live_candidate_handoff(")
    source_call = source.index(
        "ordinary_live_source_custody = execute_ordinary_live_source_custody("
    )
    retrieval_state = source.index("all_passages: list[dict[str, Any]] = []")
    retrieval_dispatch = source.index("execute_main_retrieval_pass_from_scope(")

    assert candidate_call < source_call < retrieval_state < retrieval_dispatch
    assert "select_bounded_answer_bearing_text" not in source
    assert "build_fetch_read_content_packet_from_candidate_packet" not in source
    assert "reduce_fetch_read_content_packet_into_evidence_ledger" not in source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
