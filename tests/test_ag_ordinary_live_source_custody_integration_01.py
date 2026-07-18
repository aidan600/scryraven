"""Selected-candidate nontrigger proof.

Test class: phase_focus / offline_product_path_proof / PRODUCT-PATH-REGRESSION.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.acquisition_adapters import AcquisitionTransports
from core.cap_enforcement import RunCapPolicy
from core.ordinary_live_authority_consolidation_runtime import (
    ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY,
)
from core.ordinary_live_main_runkernel_coverage_runtime import (
    ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY,
)
from core.ordinary_live_semantic_coverage_runtime import (
    ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY,
)
from core.ordinary_live_source_custody_runtime import (
    ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY,
    execute_ordinary_live_source_custody,
)
from core.run_kernel import ActionType, RunKernel
from tests.helpers.offline_ordinary_pipeline import (
    OfflineOrdinaryPipelineHarness,
    run_offline_ordinary_pipeline,
    scrub_offline_runtime,
)

QUERY = "What is the official current permit threshold for the example program?"
CANDIDATE_URL = "https://official.example.gov/program/threshold"


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch, available_search_providers=("tavily",))


class _Harness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=QUERY,
            core_topic="Example Program current permit threshold",
            primary_entity="Example Program",
            researcher_queries=("Example Program threshold diagnostics",),
            raw_author_response="The offline fixture does not activate exact-URL READ.",
            logger_name="test_ag_ordinary_live_source_custody_integration_01",
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": 1,
                "title": "Provider-returned diagnostic fixture",
                "url": "https://retrieval.example.test/provider-result",
                "text": "Provider-returned discovery material remains snippet-only.",
                "score": 0.99,
                "credibility": 3,
                "source_tier": "secondary",
                "source_class": "ordinary_retrieval_diagnostic",
                "currentness_signal": "unknown",
                "readable_status": "readable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": False,
                "_provider": "offline_fake_search",
            }
        ]


def _candidate_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example Program Permit Threshold",
            "url": CANDIDATE_URL,
            "domain": "official.example.gov",
            "snippet": "Provider-returned candidate material only.",
            "published_or_observed_date": "2026-06-30",
        }
    ]


class FakeSourceFetchRead:
    """Legacy-shaped test fixture translated to a typed transport by the helper."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        candidate: dict[str, Any],
        source_url: str,
        source_candidate_ref: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "candidate": dict(candidate),
                "source_url": source_url,
                "source_candidate_ref": dict(source_candidate_ref),
            }
        )
        text = "Offline readable exact-URL fixture material. " * 8
        return {
            "attempted_url": source_url,
            "resolved_url": source_url,
            "final_url": source_url,
            "canonical_url": source_url,
            "http_status": 200,
            "content_type": "text/html; charset=utf-8",
            "content_title": candidate["title"],
            "sanitized_text": text,
            "markdown": text,
        }


def _run_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    candidate_enabled: bool,
    source_enabled: bool,
    candidate_results: Any = None,
    fetcher: Any = None,
    acquisition_transports: AcquisitionTransports | None = None,
    provider_availability: dict[str, object] | None = None,
    cap_policy: RunCapPolicy | None = None,
    semantic_enabled: bool = False,
    consolidation_enabled: bool = False,
    main_coverage_enabled: bool = False,
) -> tuple[dict[str, Any], _Harness, Any]:
    harness = _Harness(tmp_path)
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-30",
        session_id="selected-candidate-compat-helper",
        run_id="selected-candidate-compat-helper",
        capture_stages=(),
        cap_policy=cap_policy,
        enable_ordinary_live_candidate_handoff=candidate_enabled,
        ordinary_live_candidate_handoff_results=candidate_results,
        enable_ordinary_live_source_custody=source_enabled,
        ordinary_live_source_fetch_read=fetcher,
        ordinary_live_source_acquisition_transports=acquisition_transports,
        provider_availability=(
            provider_availability
            if provider_availability is not None
            else {"linkup": True, "tavily": True}
        ),
        enable_ordinary_live_semantic_coverage=semantic_enabled,
        enable_ordinary_live_authority_consolidation=consolidation_enabled,
        enable_ordinary_live_main_runkernel_coverage=main_coverage_enabled,
    )
    return captured, harness, outcome


def _cap_policy() -> RunCapPolicy:
    return RunCapPolicy(
        max_search_dispatches=20,
        max_fetch_read_operations=0,
        max_author_model_calls=20,
        max_smart_search_judgment_model_calls=20,
        max_retries=0,
    )


def test_default_disabled_composition_has_no_source_custody_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _Harness(tmp_path)
    _captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-30",
        session_id="selected-candidate-default-disabled",
        run_id="selected-candidate-default-disabled",
        capture_stages=(),
    )

    assert ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY not in outcome.execution_trace
    assert harness.forbidden_live_calls == []


def test_selected_candidate_without_material_need_is_a_complete_nontrigger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def trap_transport(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(dict(payload))
        raise AssertionError("selected candidate alone must not reach transport")

    transports = AcquisitionTransports(
        linkup_fetch=trap_transport,
        tavily_extract=trap_transport,
    )
    cap_policy = _cap_policy()
    source_results: list[Any] = []
    child_kernels: list[RunKernel] = []
    original = orchestrator.execute_ordinary_live_source_custody

    def capture_source(**kwargs: Any) -> Any:
        child_kernels.append(kwargs["run_kernel"])
        result = original(**kwargs)
        source_results.append(result)
        return result

    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_live_source_custody",
        capture_source,
    )
    harness = _Harness(tmp_path)
    _captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-30",
        session_id="selected-candidate-nontrigger",
        run_id="selected-candidate-nontrigger",
        capture_stages=(),
        cap_policy=cap_policy,
        enable_ordinary_live_candidate_handoff=True,
        ordinary_live_candidate_handoff_results=_candidate_results(),
        enable_ordinary_live_source_custody=True,
        ordinary_live_source_acquisition_transports=transports,
        provider_availability={"linkup": True, "tavily": True},
        enable_ordinary_live_semantic_coverage=True,
        enable_ordinary_live_authority_consolidation=True,
        enable_ordinary_live_main_runkernel_coverage=True,
    )

    projection = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    assert projection["status"] == "not_needed"
    assert projection["evaluated"] is True
    assert projection["ran"] is False
    assert projection["failed_closed"] is False
    assert projection["candidate_packet_present"] is True
    assert projection["candidate_selection_creates_material_need"] is False
    assert projection["acquisition_need_proposal_created"] is False
    assert projection["acquisition_work_order_created"] is False
    assert projection["acquisition_route_created"] is False
    assert projection["exact_url_cap_charged"] is False
    assert projection["exact_url_transport_attempted"] is False
    assert projection["fetch_read_attempted_count"] == 0
    assert projection["fetch_read_completed_count"] == 0
    assert projection["evidence_ledger_custody_count"] == 0
    assert calls == []
    assert cap_policy.fetch_read_operations == 0
    assert harness.forbidden_live_calls == []
    assert len(source_results) == len(child_kernels) == 1
    assert source_results[0].fetch_read_content_packet is None
    assert source_results[0].sanitized_content_reference is None
    assert source_results[0].evidence_ledger_projection is None
    child = child_kernels[0]
    assert child.state.acquisition_control_state == {}
    acquisition_actions = {
        ActionType.ACQUISITION_CAPABILITY_DECIDE,
        ActionType.ACQUISITION_WORK_ORDER_ADMIT,
        ActionType.ACQUISITION_ROUTE,
        ActionType.ACQUISITION_EXECUTE,
        ActionType.ACQUISITION_TERMINAL_REDUCE,
        ActionType.ACQUISITION_CUSTODY_CONSUME,
    }
    assert all(
        action.action_type not in acquisition_actions
        for action in child.state.issued_actions.values()
    )
    assert ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY not in outcome.execution_trace
    assert (
        ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY
        not in outcome.execution_trace
    )
    assert (
        ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY
        not in outcome.execution_trace
    )


def test_missing_or_diagnostic_packet_is_not_inspected_without_material_need() -> None:
    calls: list[dict[str, Any]] = []

    result = execute_ordinary_live_source_custody(
        run_kernel=None,
        parent_run_id="parent-run",
        parent_request_id="parent-request",
        candidate_packet={"raw_provider_payload": "must not be inspected"},
        acquisition_transports=AcquisitionTransports(
            linkup_fetch=lambda payload: calls.append(payload) or {}
        ),
        available_providers={"linkup": True},
        cap_policy=_cap_policy(),
    )

    assert result.projection["status"] == "not_needed"
    assert result.projection["failed_closed"] is False
    assert result.projection["candidate_packet_present"] is True
    assert result.projection["exact_url_transport_attempted"] is False
    assert calls == []
