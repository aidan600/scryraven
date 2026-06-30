from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

import core.pipeline_orchestrator as orchestrator
from core.live_ordinary_candidate_handoff_runtime import (
    ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY,
    execute_ordinary_live_candidate_handoff,
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
RUNTIME = CORE / "live_ordinary_candidate_handoff_runtime.py"
QUERY = "What is the official current permit threshold for the example program?"
RESEARCH_QUERY = "Example program official current permit threshold"
RAW_AUTHOR_RESPONSE = (
    "AG_ORDINARY_LIVE_CANDIDATE_HANDOFF_REPAIR_AUTHOR_REPORT: The example "
    "program threshold remains bound to the offline fixture source [[31]]"
    "(https://official.example.gov/program/threshold)."
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _CandidateRepairHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=QUERY,
            core_topic="Example Program current permit threshold",
            primary_entity="Example Program",
            researcher_queries=(RESEARCH_QUERY,),
            raw_author_response=RAW_AUTHOR_RESPONSE,
            analyst_response=(
                "Analysis is limited to the retrieved official Example Program "
                "threshold source."
            ),
            logger_name="test_ag_ordinary_live_candidate_handoff_repair_01",
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": 31,
                "title": "Example Program Permit Threshold",
                "url": "https://official.example.gov/program/threshold",
                "text": (
                    "The official current Example Program permit threshold is "
                    "500 units for the active program year."
                ),
                "score": 0.99,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "primary_source_documents",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
                "query_ref": RESEARCH_QUERY,
                "_provider": "offline_fake_search",
            }
        ]


def _candidate_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example Program Permit Threshold",
            "url": "https://official.example.gov/program/threshold",
            "domain": "official.example.gov",
            "snippet": "Official current permit threshold for the Example Program.",
            "published_or_observed_date": "2026-06-30",
        }
    ]


def _run_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool,
    candidate_results: Sequence[dict[str, Any]] | Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], _CandidateRepairHarness, Any]:
    harness = _CandidateRepairHarness(tmp_path)
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-30",
        session_id=(
            "ag-ordinary-live-candidate-enabled-session"
            if enabled
            else "ag-ordinary-live-candidate-disabled-session"
        ),
        run_id=(
            "ag-ordinary-live-candidate-enabled-run"
            if enabled
            else "ag-ordinary-live-candidate-disabled-run"
        ),
        capture_stages=(HANDOFF_PACKET,),
        enable_ordinary_live_candidate_handoff=enabled,
        ordinary_live_candidate_handoff_results=candidate_results,
    )
    return captured, harness, outcome


def test_default_disabled_run_pipeline_behavior_has_no_candidate_handoff_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        enabled=False,
    )

    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY not in outcome.execution_trace
    assert harness.search_calls
    state = captured["run_kernel"].state
    assert state.search_executor_handoff_state == {}
    assert state.live_search_validation_state == {}


def test_enabled_run_pipeline_consumes_candidate_handoff_before_retrieval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization_calls: list[dict[str, Any]] = []
    candidate_kernels: list[RunKernel] = []
    original_authorize = RunKernel.authorize_live_search_validation
    original_handoff = orchestrator.execute_ordinary_live_candidate_handoff

    def spy_authorize(self: RunKernel, *args: Any, **kwargs: Any) -> Any:
        authorization_calls.append(dict(kwargs))
        return original_authorize(self, *args, **kwargs)

    def spy_handoff(**kwargs: Any) -> Any:
        candidate_kernels.append(kwargs["run_kernel"])
        return original_handoff(**kwargs)

    monkeypatch.setattr(
        RunKernel,
        "authorize_live_search_validation",
        spy_authorize,
    )
    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_live_candidate_handoff",
        spy_handoff,
    )
    captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        enabled=True,
        candidate_results=_candidate_results(),
    )

    assert harness.search_calls
    assert authorization_calls
    projection = outcome.execution_trace[ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY]
    assert projection["enabled"] is True
    assert projection["ran"] is True
    assert projection["failed_closed"] is False
    assert projection["status"] == "search_result_candidate_packet_built"
    assert projection["runtime_consumer"] == "core.pipeline_orchestrator.run_pipeline"
    assert projection["current_path_timing"] == (
        "before ordinary retrieval/provider result dispatch"
    )
    assert candidate_kernels
    state = candidate_kernels[0].state
    assert state.current_answer_contract
    assert state.search_executor_handoff_state
    assert state.live_search_validation_state
    assert captured["run_kernel"].state.search_executor_handoff_state == {}
    assert captured["run_kernel"].state.live_search_validation_state == {}
    assert projection["candidate_handoff_state_owner"] == (
        "ordinary_live_candidate_handoff_run_kernel"
    )
    assert projection["parent_run_kernel_run_id"] == captured["run_kernel"].state.run_id
    assert projection["candidate_handoff_run_kernel_run_id"] == state.run_id
    assert projection["main_answer_kernel_semantic_state_preserved_before_retrieval"] is True
    assert projection["current_answer_contract_digest"] == (
        state.current_answer_contract["accepted_contract_digest"]
    )
    assert projection["search_executor_handoff_digest"] == (
        state.search_executor_handoff_state["handoff_digest"]
    )
    assert projection["live_search_validation_ref"]["validation_digest"] == (
        state.live_search_validation_state["validation_digest"]
    )
    assert projection["search_result_candidate_packet_ref"]["packet_digest"] == (
        projection["search_result_candidate_packet_digest"]
    )
    assert projection["search_result_candidate_packet_candidate_count"] == 1
    assert authorization_calls[0]["selected_search_task_ids"] == (
        projection["selected_search_task_ids"]
    )


def test_candidate_packet_is_built_from_live_validation_state_not_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        enabled=True,
        candidate_results=_candidate_results(),
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY]
    assert projection["live_search_validation_state_source"] == (
        "RunKernel.live_search_validation_state"
    )
    assert projection["candidate_authority_source"] == (
        "structured_offline_candidate_inputs"
    )
    assert projection["retrieval_diagnostics_used_as_candidate_authority"] is False
    assert projection["search_result_candidate_packet_status"] == (
        "built_from_live_search_validation_state"
    )


def test_enabled_without_candidate_inputs_fails_closed_without_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        enabled=True,
        candidate_results=None,
    )

    assert harness.search_calls
    projection = outcome.execution_trace[ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY]
    assert projection["enabled"] is True
    assert projection["ran"] is False
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == "structured_candidate_inputs_missing"
    assert projection["retrieval_diagnostics_used_as_candidate_authority"] is False
    assert projection["search_result_candidate_packet_status"] == "not_built"
    state = captured["run_kernel"].state
    assert state.search_executor_handoff_state == {}
    assert state.live_search_validation_state == {}


def test_retrieval_diagnostic_shaped_candidate_inputs_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        enabled=True,
        candidate_results=[
            {
                **_candidate_results()[0],
                "provider_diagnostics": {"result_count": 1},
            }
        ],
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY]
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == "structured_candidate_inputs_invalid"
    assert projection["retrieval_diagnostics_used_as_candidate_authority"] is False
    assert projection["search_result_candidate_packet_status"] == "not_built"

    _captured, _harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        enabled=True,
        candidate_results={
            "results": _candidate_results(),
            "provider_diagnostics": {"result_count": 1},
        },
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY]
    assert projection["failed_closed"] is True
    assert projection["first_failed_seam"] == "structured_candidate_inputs_invalid"
    assert projection["retrieval_diagnostics_used_as_candidate_authority"] is False


def test_closed_surfaces_and_zero_live_call_counts_are_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        enabled=True,
        candidate_results=_candidate_results(),
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY]
    assert harness.forbidden_live_calls == []
    for key in (
        "provider_search_calls",
        "broker_calls",
        "fetch_read_calls",
        "model_calls",
        "retrieval_calls",
    ):
        assert projection[key] == 0
    for key in (
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "fetch_read_executed",
        "evidence_ledger_admitted",
        "citation_eligible",
        "source_obligation_satisfied",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "partial_answer_ready",
        "product_correctness_claimed",
    ):
        assert projection[key] is False


def test_missing_current_contract_and_handoff_seams_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = RunKernel.start(
        run_id="ag-ordinary-live-candidate-missing-current-run",
        request_id="ag-ordinary-live-candidate-missing-current-request",
    )
    with monkeypatch.context() as patched:
        patched.setattr(
            "core.live_ordinary_candidate_handoff_runtime._apply_current_contract_candidate_caveat",
            lambda *_args, **_kwargs: None,
        )
        result = execute_ordinary_live_candidate_handoff(
            run_kernel=kernel,
            query=QUERY,
            requested_mode="Balanced",
            run_contract_projection={"contract_id": "contract:test"},
            route_projection={"route_id": "route:test"},
            core_topic="Example Program",
            candidate_results=_candidate_results(),
            provider_authorized="offline-fake-search",
        )

    assert result.projection["failed_closed"] is True
    assert result.projection["first_failed_seam"] == (
        "accepted_current_answer_contract_missing"
    )

    kernel = RunKernel.start(
        run_id="ag-ordinary-live-candidate-missing-handoff-run",
        request_id="ag-ordinary-live-candidate-missing-handoff-request",
    )
    with monkeypatch.context() as patched:
        patched.setattr(
            "core.live_ordinary_candidate_handoff_runtime._reduce_search_executor_handoff",
            lambda *_args, **_kwargs: None,
        )
        result = execute_ordinary_live_candidate_handoff(
            run_kernel=kernel,
            query=QUERY,
            requested_mode="Balanced",
            run_contract_projection={"contract_id": "contract:test"},
            route_projection={"route_id": "route:test"},
            core_topic="Example Program",
            candidate_results=_candidate_results(),
            provider_authorized="offline-fake-search",
        )

    assert result.projection["failed_closed"] is True
    assert result.projection["first_failed_seam"] == "search_executor_handoff_missing"


def test_product_code_does_not_import_scripts_ag_harnesses() -> None:
    for path in (PIPELINE, RUNTIME):
        imports = _imports(path)
        assert not any(name == "scripts" or name.startswith("scripts.") for name in imports)
        source = path.read_text(encoding="utf-8")
        assert "scripts/ag_" not in source
        assert "from scripts import ag_" not in source


def test_run_pipeline_callsite_is_before_ordinary_retrieval_dispatch() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    query_admission = source.index(
        "run_kernel.reduce(query_admission_result.observation)"
    )
    handoff_call = source.index("execute_ordinary_live_candidate_handoff(")
    retrieval_state = source.index("all_passages: list[dict[str, Any]] = []")
    retrieval_dispatch = source.index("execute_main_retrieval_pass_from_scope(")

    assert query_admission < handoff_call < retrieval_state < retrieval_dispatch


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
