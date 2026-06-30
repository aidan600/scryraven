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
from core.ordinary_live_authority_consolidation_runtime import (
    ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY,
    execute_ordinary_live_authority_consolidation,
)
from core.ordinary_live_semantic_coverage_runtime import (
    ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY,
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
RUNTIME = CORE / "ordinary_live_authority_consolidation_runtime.py"
DOC = (
    ROOT
    / "docs"
    / "architecture"
    / "AG_ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_AND_READINESS_PRECONDITION_01.md"
)

QUERY = "What is the official current permit threshold for the example program?"
RESEARCH_QUERY = "Example program current permit threshold diagnostics"
CANDIDATE_URL = "https://official.example.gov/program/threshold"
DIAGNOSTIC_RETRIEVAL_URL = "https://retrieval.example.test/not-authority"
RAW_AUTHOR_RESPONSE = (
    "AG_ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_AUTHOR_REPORT: The answer remains "
    "limited to the ordinary offline fixture."
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


class _AuthorityConsolidationHarness(OfflineOrdinaryPipelineHarness):
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
                "test_ag_ordinary_live_authority_consolidation_and_"
                "readiness_precondition_01"
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
                    "authority for ordinary-live consolidation."
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
            "The official current Example Program permit threshold is 500 units "
            "for the active program year."
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
    consolidation_enabled: bool,
    candidate_results: Sequence[dict[str, Any]] | Mapping[str, Any] | None = None,
    fetcher: Any | None = None,
) -> tuple[dict[str, Any], _AuthorityConsolidationHarness, Any]:
    harness = _AuthorityConsolidationHarness(tmp_path)
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-30",
        session_id="ag-ordinary-live-authority-consolidation-session",
        run_id="ag-ordinary-live-authority-consolidation-run",
        capture_stages=(HANDOFF_PACKET,),
        enable_ordinary_live_candidate_handoff=candidate_enabled,
        ordinary_live_candidate_handoff_results=candidate_results,
        enable_ordinary_live_source_custody=source_enabled,
        ordinary_live_source_fetch_read=fetcher,
        ordinary_live_source_custody_anchor_groups=ANCHORS,
        enable_ordinary_live_semantic_coverage=semantic_enabled,
        enable_ordinary_live_authority_consolidation=consolidation_enabled,
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
        consolidation_enabled=False,
        fetcher=fetcher,
    )

    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY not in outcome.execution_trace
    assert ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY not in outcome.execution_trace
    assert ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY not in outcome.execution_trace
    assert (
        ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY
        not in outcome.execution_trace
    )
    assert fetcher.calls == []
    assert harness.forbidden_live_calls == []


def test_semantic_enabled_consolidation_disabled_preserves_364_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=True,
        consolidation_enabled=False,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    semantic = outcome.execution_trace[ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY]
    assert semantic["status"] == "semantic_observation_and_component_coverage_reduced"
    assert semantic["readiness_build_precondition_met"] is False
    assert semantic["readiness_blocker_if_any"] == (
        "coverage_not_bound_to_main_answer_readiness_component"
    )
    assert (
        ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY
        not in outcome.execution_trace
    )


def test_run_pipeline_calls_consolidation_with_in_memory_semantic_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper_inputs: list[dict[str, Any]] = []
    original = orchestrator.execute_ordinary_live_authority_consolidation

    def spy_consolidation(**kwargs: Any) -> Any:
        helper_inputs.append(dict(kwargs))
        return original(**kwargs)

    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_live_authority_consolidation",
        spy_consolidation,
    )

    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=True,
        consolidation_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    projection = outcome.execution_trace[
        ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY
    ]
    assert helper_inputs
    assert not isinstance(helper_inputs[0]["semantic_coverage_result"], Mapping)
    assert helper_inputs[0]["semantic_coverage_result"].component_coverage_projection
    assert helper_inputs[0]["child_run_kernel"].state.component_coverage_history
    assert projection["runtime_consumer"] == "core.pipeline_orchestrator.run_pipeline"
    assert projection["source_semantic_coverage_result_object_consumed"] is True
    assert projection["projection_consumed_as_authority"] is False
    assert projection["child_kernel_consumed_in_memory"] is True
    assert projection["projection_to_runkernel_rehydration"] is False
    assert projection["direct_runkernel_mutation"] is False
    assert projection["failed_closed"] is True
    assert projection["authority_consolidation_status"] == (
        "blocked_missing_main_answer_component_binding"
    )
    assert projection["readiness_precondition_status"] == "not_met"
    assert projection["readiness_blocker_if_any"] == (
        "main_answer_component_binding_missing"
    )
    assert projection["legacy_readiness_blocker"] == (
        "coverage_not_bound_to_main_answer_readiness_component"
    )
    assert projection["component_equivalence_posture"] == (
        "unknown_requires_architecture_decision"
    )
    assert projection["binding_basis"] == "main_answer_component_absent"
    assert projection["safe_binding_created"] is False
    assert projection["child_coverage_ref"]["coverage_record_id"]
    assert projection["child_component_ref"]["component_id"] == (
        "component:ordinary-live-candidate-handoff-primary"
    )
    assert projection["main_answer_component_candidate_count"] == 0
    assert projection["precondition_binding_record_authoritative"] is False
    assert projection["named_future_consumer"] == "none_currently"
    assert projection["named_future_consumer_exists"] is False
    assert projection["future_sufficiency_readiness_may_consume"] is False
    assert projection["future_final_answer_packet_may_consume"] is False
    assert projection["future_author_may_consume"] is False
    assert harness.forbidden_live_calls == []


def test_missing_semantic_coverage_result_fails_closed_with_named_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=False,
        consolidation_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    projection = outcome.execution_trace[
        ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY
    ]
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == (
        "ordinary_live_semantic_coverage_result_missing"
    )
    assert projection["source_semantic_coverage_result_object_consumed"] is False
    assert projection["projection_consumed_as_authority"] is False
    assert projection["future_readiness_fap_author_eligibility"] is False


def test_projection_mapping_instead_of_result_object_fails_closed() -> None:
    result = execute_ordinary_live_authority_consolidation(
        main_run_kernel=RunKernel.start(run_id="main-run", request_id="main-request"),
        child_run_kernel=RunKernel.start(run_id="child-run", request_id="child-request"),
        semantic_coverage_result={"component_coverage_ref": {"coverage_record_id": "x"}},
    )

    projection = result.projection
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == (
        "ordinary_live_semantic_coverage_result_object_missing"
    )
    assert projection["projection_consumed_as_authority"] is False


def test_missing_child_kernel_or_child_coverage_fails_without_rehydration() -> None:
    semantic_result = SimpleNamespace(
        projection={"status": "semantic_observation_and_component_coverage_reduced"},
        component_coverage_projection={
            "coverage_record_id": "coverage-record",
            "coverage_record_digest": "coverage-digest",
            "coverage_reduction_digest": "reduction-digest",
            "answer_component_id": "component:child",
            "component_revision": "1",
            "component_digest": "component-digest",
        },
    )

    missing_child = execute_ordinary_live_authority_consolidation(
        main_run_kernel=RunKernel.start(run_id="main-run", request_id="main-request"),
        child_run_kernel=None,
        semantic_coverage_result=semantic_result,
    ).projection
    assert missing_child["first_failed_seam"] == (
        "ordinary_candidate_handoff_run_kernel_missing"
    )
    assert missing_child["projection_to_runkernel_rehydration"] is False
    assert missing_child["direct_runkernel_mutation"] is False

    missing_coverage = execute_ordinary_live_authority_consolidation(
        main_run_kernel=RunKernel.start(run_id="main-run", request_id="main-request"),
        child_run_kernel=RunKernel.start(
            run_id="child-run",
            request_id="child-request",
        ),
        semantic_coverage_result=semantic_result,
    ).projection
    assert missing_coverage["first_failed_seam"] == "child_component_coverage_missing"
    assert missing_coverage["projection_to_runkernel_rehydration"] is False
    assert missing_coverage["direct_runkernel_mutation"] is False


def test_diagnostic_fields_are_rejected_as_authority() -> None:
    mapping_result = execute_ordinary_live_authority_consolidation(
        main_run_kernel=RunKernel.start(run_id="main-run", request_id="main-request"),
        child_run_kernel=RunKernel.start(run_id="child-run", request_id="child-request"),
        semantic_coverage_result={"provider_diagnostics": {"result_count": 1}},
    ).projection
    assert mapping_result["first_failed_seam"] == (
        "diagnostic_consolidation_authority_rejected"
    )
    assert mapping_result["retrieval_diagnostics_used_as_authority"] is False

    object_result = execute_ordinary_live_authority_consolidation(
        main_run_kernel=RunKernel.start(run_id="main-run", request_id="main-request"),
        child_run_kernel=RunKernel.start(run_id="child-run", request_id="child-request"),
        semantic_coverage_result=SimpleNamespace(
            projection={"retrieval_diagnostics": {"count": 1}},
            component_coverage_projection={},
        ),
    ).projection
    assert object_result["first_failed_seam"] == (
        "diagnostic_consolidation_authority_rejected"
    )
    assert object_result["diagnostic_provider_fields_used_as_authority"] is False


def test_trace_projection_is_safe_and_closed_surfaces_remain_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=True,
        consolidation_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=FakeSourceFetchRead(),
    )

    projection = outcome.execution_trace[
        ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY
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
        "citation_rendered",
        "sufficiency_readiness_reduced",
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


def test_pipeline_orchestrator_contains_only_minimal_consolidation_callsite() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    semantic_call = source.index(
        "ordinary_live_semantic_coverage = execute_ordinary_live_semantic_coverage("
    )
    consolidation_call = source.index(
        "execute_ordinary_live_authority_consolidation("
    )
    retrieval_state = source.index("all_passages: list[dict[str, Any]] = []")

    assert semantic_call < consolidation_call < retrieval_state
    for forbidden in (
        "main_answer_component_equivalence_not_established",
        "child_to_parent_component_coverage_transfer_reducer_missing",
        "ComponentCoverageRecord",
        "build_sufficiency_readiness",
    ):
        assert forbidden not in source


def test_docs_record_repair_posture_blocker_and_next_checkpoint() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "Mode: REPAIR",
        "ordinary_live_authority_consolidation",
        "main_answer_component_binding_missing",
        "unknown_requires_architecture_decision",
        "precondition/binding record is not authoritative",
        "core.pipeline_orchestrator.py` remains a narrow shell",
        "provider/search calls: 0",
        "Closed Surfaces",
        "Explicit Non-Proofs",
        "AG-ORDINARY-LIVE-MAIN-COMPONENT-BINDING-AUTHORITY-DECISION-01",
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
