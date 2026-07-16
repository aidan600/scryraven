from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, replace
from pathlib import Path
from typing import Any

import pytest

import core.component_gap_recovery_coordinator as recovery_coordinator
import core.component_gap_recovery_runtime as recovery_runtime
import core.final_evidence_bundle_builder as final_material_builder
import core.pipeline_orchestrator as orchestrator
from core.component_gap_recovery_runtime import (
    COMPONENT_GAP_RECOVERY_TRACE_KEY,
    ComponentGapRecoveryPolicy,
    execute_authorized_component_gap_recovery,
)
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from core.query_plan import QUERY_PLAN_TRACE_KEY
from core.run_config import RunDeps, compose_component_gap_recovery_deps
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    OfflineOrdinaryPipelineHarness,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)

RAW_AUTHOR_RESPONSE = (
    "AG_BAL_01_FINAL_REPORT\n\n"
    "The appeal-deadline component has recovered official support."
)
RECOVERED_FACT = (
    "The Example Filing Program appeal deadline is calculated as 30 calendar "
    "days after the notice date."
)
RECOVERED_SOURCE_URL = "https://official.example/deadline"
POISONED_AUTHORITY_FIELDS = {
    "citation_eligible": True,
    "citation_eligibility_posture": "adapter_claimed_citation_eligible",
    "disposition": "accepted",
    "eligible_for_stronger_obligation": True,
    "final_authority": "adapter_claimed_final_authority",
    "final_evidence_eligible": True,
    "final_evidence_selected": True,
    "source_obligation_posture": "adapter_claimed_satisfied",
    "source_obligation_satisfied": True,
    "status": "accepted",
}
PRE_RECOVERY_FINAL_PACKET_STOP_REASON = (
    "pre_recovery_final_answer_packet_already_present"
)


class _AdapterSpy:
    def __init__(self, passages: list[dict[str, Any]] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.passages = list(passages or [])

    def __call__(
        self,
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "queries": list(queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "provider_role": kwargs.get("provider_role"),
            }
        )
        return [dict(item) for item in self.passages]


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


def _balanced_policy() -> ComponentGapRecoveryPolicy:
    return ComponentGapRecoveryPolicy(
        policy_label="balanced_single_cycle_offline",
        requested_mode="Balanced",
        allowed_requested_modes=("Balanced",),
        max_cycles=1,
        offline_only=True,
        existing_candidate_query_only=True,
        model_generated_query_text_allowed=False,
        provider_live_calls_allowed=False,
        accepted_amendments_allowed=False,
        deep_reconciliation_allowed=False,
    )


class _BalancedRecoveryHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=(
                "What is the current official filing fee and how is the "
                "appeal deadline calculated?"
            ),
            core_topic="official filing fee and appeal deadline",
            primary_entity="Example Filing Program",
            researcher_queries=(
                "current official filing fee",
                "appeal deadline legal rule",
            ),
            raw_author_response=RAW_AUTHOR_RESPONSE,
            analyst_response="Analysis is limited to official recovered evidence.",
            logger_name="test_ag_bal_01_component_gap_recovery",
        )

    def deps(self) -> RunDeps:
        return compose_component_gap_recovery_deps(
            super().deps(),
            enabled=True,
            offline_recovery_adapter=self.process_search_queries,
        )

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if "ruthless fact-checker and logic auditor" in system_prompt:
            self._record_model_call(system_prompt, kwargs)
            return '{"verdict": "clean", "flags": []}'
        return super().ask_model(prompt, system_prompt, **kwargs)

    def build_search_passages(self) -> list[dict[str, Any]]:
        if len(self.search_calls) == 1:
            return [
                {
                    "source_id": 1,
                    "title": "Example Filing Program current official filing fee",
                    "url": "https://official.example/fee",
                    "text": (
                        "The Example Filing Program current official filing "
                        "fee is $120 for 2026."
                    ),
                    "score": 0.99,
                    "credibility": 4,
                    "source_tier": "official",
                    "source_class": "official_current_rules",
                    "_provider": "offline_fake_search",
                }
            ]
        return [
            {
                "source_id": 2,
                "title": "Example Filing Program appeal deadline legal rule",
                "url": "https://official.example/deadline",
                "text": (
                    "The Example Filing Program appeal deadline is calculated "
                    "as 30 calendar days after the notice date."
                ),
                "score": 0.98,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "legal_or_regulatory_text",
                "currentness_signal": "current",
                "_provider": "offline_fake_search",
                "provider_name": "offline-fixture",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
            }
        ]


class _AdapterAbsentHarness(_BalancedRecoveryHarness):
    def deps(self) -> RunDeps:
        return OfflineOrdinaryPipelineHarness.deps(self)


class _WeakRecoveryHarness(_BalancedRecoveryHarness):
    def build_search_passages(self) -> list[dict[str, Any]]:
        if len(self.search_calls) == 1:
            return super().build_search_passages()
        return [
            {
                "source_id": 3,
                "title": "Secondary discussion of appeal deadlines",
                "url": "https://secondary.example/deadline",
                "text": "A secondary discussion mentions possible deadline timing.",
                "score": 0.75,
                "credibility": 2,
                "source_tier": "secondary",
                "source_class": "secondary_analysis",
                "currentness_signal": "unknown",
                "eligible_for_stronger_obligation": False,
                "_provider": "offline_fake_search",
            }
        ]


def _poisoned_authority_passage(passage: dict[str, Any]) -> dict[str, Any]:
    return {**passage, **POISONED_AUTHORITY_FIELDS}


class _PoisonedAuthorityRecoveryHarness(_BalancedRecoveryHarness):
    def build_search_passages(self) -> list[dict[str, Any]]:
        passages = super().build_search_passages()
        if len(self.search_calls) == 1:
            return passages
        return [_poisoned_authority_passage(dict(item)) for item in passages]


class _PoisonedWeakRecoveryHarness(_WeakRecoveryHarness):
    def build_search_passages(self) -> list[dict[str, Any]]:
        passages = super().build_search_passages()
        if len(self.search_calls) == 1:
            return passages
        return [_poisoned_authority_passage(dict(item)) for item in passages]


def _candidate_records_for_url(
    projection: dict[str, Any],
    url: str,
) -> list[dict[str, Any]]:
    return [
        dict(record)
        for record in projection.get("candidate_records") or ()
        if isinstance(record, dict) and record.get("url") == url
    ]


def _assert_recovered_candidate_authority_neutral(
    records: list[dict[str, Any]],
) -> None:
    assert records
    for record in records:
        assert record.get("final_evidence_eligible") is not True
        assert record.get("eligible_for_stronger_obligation") is not True
        assert record.get("citation_eligible") is not True
        assert record.get("final_evidence_selected") is not True
        assert record.get("source_obligation_satisfied") is not True
        assert record.get("fact_disposition") != "accepted"
        assert record.get("proposal_disposition") != "accepted"
        assert record.get("disposition") != "accepted"


def _assert_adapter_authority_markers_absent(text: str) -> None:
    assert "adapter_claimed_citation_eligible" not in text
    assert "adapter_claimed_final_authority" not in text
    assert "adapter_claimed_satisfied" not in text


def _run_blocked_offline_path(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    harness: OfflineOrdinaryPipelineHarness | None = None,
) -> tuple[OfflineOrdinaryPipelineHarness, dict[str, Any]]:
    active_harness = harness or _BalancedRecoveryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET,),
    )
    config = offline_balanced_run_config(
        query=active_harness.query,
        current_date="2026-06-24",
        session_id=f"ag-bal-01-{mode.casefold()}-session",
        run_id=f"ag-bal-01-{mode.casefold()}-run",
    )
    config.mode = mode
    outcome = orchestrator.run_pipeline(
        config,
        active_harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    terminal = (outcome.execution_trace or {}).get("blocked_fap_terminal") or {}
    assert terminal.get("blocked_fap") is True
    assert terminal.get("author_called") is False
    assert active_harness.author_prompts == []
    assert active_harness.author_kwargs == []
    captured["blocked_outcome"] = outcome
    return active_harness, captured


def _run_balanced_adapter_absent_path(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[OfflineOrdinaryPipelineHarness, dict[str, Any]]:
    return _run_blocked_offline_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        mode="Balanced",
        harness=_AdapterAbsentHarness(tmp_path),
    )


def _remove_final_answer_packet_guard_state(captured: dict[str, Any]) -> None:
    state = captured["run_kernel"].state
    assert state.final_answer_packet
    state.final_answer_packet = {}
    state.final_answer_authority_projection = {}
    state.projections.pop("final_answer_packet", None)
    if hasattr(state, "final_answer_packet_projection"):
        state.final_answer_packet_projection = {}


def _direct_recovery_kwargs(
    captured: dict[str, Any],
    *,
    query_plan_trace: dict[str, Any] | None = None,
    search_judgment_projection: dict[str, Any] | None = None,
    offline_recovery_adapter: Any = None,
) -> dict[str, Any]:
    run_kernel = captured["run_kernel"]
    runtime_scope = captured["packet_runtime_scope"]
    return {
        "run_kernel": run_kernel,
        "policy": _balanced_policy(),
        "query_plan_trace": query_plan_trace
        or runtime_scope["query_authority"].to_trace_fragment(),
        "search_judgment_projection": search_judgment_projection
        or run_kernel.state.search_judgment_projection,
        "evidence_ledger_projection": runtime_scope["evidence_ledger_projection"],
        "search_work_projection": None,
        "offline_recovery_adapter": offline_recovery_adapter,
        "runtime_context": {
            "query": runtime_scope["query"],
            "intent": runtime_scope["intent"],
            "complexity": runtime_scope["complexity"],
            "search_depth": runtime_scope["search_depth"],
            "results_per_query": runtime_scope["results_per_query"],
        },
        "seen_urls": set(),
    }


def test_ag_bal_01_recovers_one_authorized_component_gap_and_regenerates_author(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _BalancedRecoveryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-bal-01-session",
            run_id="ag-bal-01-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert harness.forbidden_live_calls == []
    assert len(harness.search_calls) == 2
    assert harness.search_calls[0]["queries"] == [
        "current official filing fee",
        "appeal deadline legal rule",
    ]
    assert harness.search_calls[1]["queries"] == ["appeal deadline legal rule"]
    assert harness.search_calls[1]["provider_role"] == (
        "component_gap_recovery_offline"
    )
    assert harness.search_calls[1]["search_providers"] == []

    state = captured["run_kernel"].state
    assert len(state.component_gap_recovery_history) == 1
    recovery_projection = state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]
    assert recovery_projection["projection_derived_from_canonical_state"] is True
    assert recovery_projection["canonical_budget_owner"] == (
        "RunKernel.RunState.component_gap_recovery_history"
    )
    latest_recovery = recovery_projection["latest"]
    assert latest_recovery["owner"] == "ComponentGapRecoveryRuntime"
    assert latest_recovery["mode_neutral_primitive"] is True
    assert "Balanced" not in latest_recovery["owner"]
    assert latest_recovery["status"] == "recovered"
    assert latest_recovery["policy"]["policy_label"] == (
        "balanced_single_cycle_offline"
    )
    assert latest_recovery["policy"]["requested_mode"] == "Balanced"
    assert latest_recovery["policy"]["max_cycles"] == 1
    assert latest_recovery["policy"]["offline_only"] is True
    assert latest_recovery["policy"]["existing_candidate_query_only"] is True
    assert latest_recovery["policy"]["provider_live_calls_allowed"] is False
    assert latest_recovery["policy"]["model_generated_query_text_allowed"] is False
    assert latest_recovery["policy"]["accepted_amendments_allowed"] is False
    assert latest_recovery["policy"]["deep_reconciliation_allowed"] is False
    assert latest_recovery["canonical_budget_owner"] == (
        "RunKernel.RunState.component_gap_recovery_history"
    )

    accepted_component_ids = {
        ref["component_id"]
        for ref in state.initial_answer_contract["accepted_answer_component_refs"]
    }
    covered_component_ids = {
        item["answer_component_id"] for item in state.component_coverage_history
    }
    assert covered_component_ids == accepted_component_ids

    assert len(captured["sufficiency_handoffs"]) == 2
    assert captured["sufficiency_projections"][0]["semantic_consumption"][
        "missing_component_count"
    ] == 1
    assert captured["sufficiency_projections"][1]["semantic_consumption"][
        "missing_component_count"
    ] == 0
    sufficiency_projection = state.sufficiency_judgment_projection
    semantic_consumption = sufficiency_projection["semantic_consumption"]
    assert semantic_consumption["required_component_count"] == 2
    assert semantic_consumption["covered_component_count"] == 2
    assert semantic_consumption["missing_component_count"] == 0
    assert captured["packet_runtime_scope"]["sufficiency_judgment_projection"] == (
        captured["sufficiency_projections"][1]
    )

    query_authority = captured["packet_runtime_scope"]["query_authority"]
    query_plan_trace = query_authority.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    consumption = query_plan_trace["search_work_consumption"]
    assert consumption["version_bound_component_gap_authority_consumed"] is True
    assert consumption["version_bound_component_gap_authorized_query"] == (
        "appeal deadline legal rule"
    )
    metadata = consumption["query_metadata"]["appeal deadline legal rule"]
    assert metadata["version_bound_component_gap_authorized"] is True
    assert not metadata.get("query_text_generated")
    assert not metadata.get("new_executable_query_text_generated")
    assert consumption["behavior_boundary_flags"][
        "new_executable_query_text_generated"
    ] is False
    assert consumption["behavior_boundary_flags"][
        "component_gap_authority_changed_retrieval_queries"
    ] is False

    assert captured["packet_handoff_called"] is True
    assert captured["author_handoff_called"] is True
    assert captured["author_runtime_scope"]["final_answer_packet"] == (
        captured["packet_handoff"].packet
    )
    packet = state.final_answer_packet
    packet_text = repr(packet)
    assert RECOVERED_SOURCE_URL in packet_text
    assert "source_id': 2" in packet_text or '"source_id": 2' in packet_text
    author_payload_text = repr(captured["packet_handoff"].author_payload)
    assert RECOVERED_FACT in author_payload_text
    assert RECOVERED_SOURCE_URL in author_payload_text
    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert len(harness.author_prompts) == 1
    author_prompt = harness.author_prompts[0]
    assert RECOVERED_FACT in author_prompt
    assert RECOVERED_SOURCE_URL in author_prompt
    assert "CONTROLLED SEMANTIC CONTEXT" in author_prompt
    assert "2 required components are supported" in author_prompt


def test_ag_bal_01_fails_closed_without_offline_recovery_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _AdapterAbsentHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET,),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-bal-01-no-adapter-session",
            run_id="ag-bal-01-no-adapter-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    assert outcome.execution_trace["blocked_fap_terminal"]["blocked_fap"] is True
    assert outcome.execution_trace["blocked_fap_terminal"]["author_called"] is False

    assert harness.forbidden_live_calls == []
    assert harness.author_prompts == []
    assert len(harness.search_calls) == 1
    state = captured["run_kernel"].state
    assert len(state.component_gap_recovery_history) == 1
    latest_recovery = state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]["latest"]
    assert latest_recovery["status"] == "blocked"
    assert latest_recovery["stop_reason"] == "offline_recovery_adapter_absent"
    assert latest_recovery["policy"]["offline_only"] is True
    assert latest_recovery["policy"]["provider_live_calls_allowed"] is False


def test_ag_bal_01_fails_closed_when_recovered_evidence_cannot_cover_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _WeakRecoveryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET,),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-bal-01-weak-evidence-session",
            run_id="ag-bal-01-weak-evidence-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    assert outcome.execution_trace["blocked_fap_terminal"]["blocked_fap"] is True
    assert outcome.execution_trace["blocked_fap_terminal"]["author_called"] is False

    assert harness.forbidden_live_calls == []
    assert harness.author_prompts == []
    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["queries"] == ["appeal deadline legal rule"]
    state = captured["run_kernel"].state
    latest_recovery = state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]["latest"]
    assert latest_recovery["status"] == "attempted_no_coverage"
    assert latest_recovery["stop_reason"] == (
        "recovered_evidence_not_semantically_covering_gap"
    )
    semantic_consumption = state.sufficiency_judgment_projection[
        "semantic_consumption"
    ]
    assert semantic_consumption["required_component_count"] == 2
    assert semantic_consumption["covered_component_count"] == 1
    assert semantic_consumption["missing_component_count"] == 1
    candidate_records = state.evidence_ledger.to_projection().to_dict()[
        "candidate_records"
    ]
    recovered_candidates = [
        record
        for record in candidate_records
        if record.get("url") == "https://secondary.example/deadline"
    ]
    assert recovered_candidates
    assert all(
        record.get("final_evidence_eligible") is not True
        for record in recovered_candidates
    )


def test_ag_bal_harden_01_poisoned_adapter_authority_is_neutral_before_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pre_rebuild: dict[str, Any] = {}
    original_rebuild = orchestrator.build_final_material_runtime_handoff_from_scope

    def capture_pre_rebuild_scope(scope: Any, *args: Any, **kwargs: Any) -> Any:
        if kwargs.get("final_evidence_handoff") is None:
            pre_rebuild["evidence_ledger_projection"] = deepcopy(
                scope["run_kernel"].state.evidence_ledger.to_projection().to_dict()
            )
            pre_rebuild["all_passages"] = deepcopy(scope["all_passages"])
        return original_rebuild(scope, *args, **kwargs)

    monkeypatch.setattr(
        orchestrator,
        "build_final_material_runtime_handoff_from_scope",
        capture_pre_rebuild_scope,
    )
    harness = _PoisonedAuthorityRecoveryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET, HANDOFF_AUTHOR, HANDOFF_SUFFICIENCY),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-bal-harden-01-poison-success-session",
            run_id="ag-bal-harden-01-poison-success-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    pre_rebuild_candidates = _candidate_records_for_url(
        pre_rebuild["evidence_ledger_projection"],
        RECOVERED_SOURCE_URL,
    )
    assert pre_rebuild_candidates
    for record in pre_rebuild_candidates:
        assert record.get("final_evidence_eligible") is not True
        assert record.get("citation_eligible") is not True
        assert record.get("final_evidence_selected") is not True
        assert record.get("fact_disposition") == "accepted"
        assert record.get("eligible_for_stronger_obligation") is True
        assert record.get("disposition_reason") == (
            "component_gap_recovery_semantic_binding_validated"
        )
    recovered_passages = [
        item
        for item in pre_rebuild["all_passages"]
        if item.get("url") == RECOVERED_SOURCE_URL
    ]
    assert recovered_passages
    for passage in recovered_passages:
        assert passage["final_evidence_eligible"] == "unknown"
        assert passage["component_gap_recovery_semantic_coverage_committed"] is True
        for key in POISONED_AUTHORITY_FIELDS:
            if key != "final_evidence_eligible":
                assert key not in passage

    final_candidates = _candidate_records_for_url(
        captured["run_kernel"].state.evidence_ledger.to_projection().to_dict(),
        RECOVERED_SOURCE_URL,
    )
    assert any(
        record.get("final_evidence_eligible") is True
        and record.get("eligible_for_stronger_obligation") is True
        and record.get("fact_disposition") == "accepted"
        for record in final_candidates
    )
    assert RECOVERED_FACT in repr(captured["packet_handoff"].author_payload)
    assert RECOVERED_SOURCE_URL in repr(captured["packet_handoff"].author_payload)
    assert RECOVERED_FACT in harness.author_prompts[0]
    assert RECOVERED_SOURCE_URL in harness.author_prompts[0]
    assert outcome.report == RAW_AUTHOR_RESPONSE
    combined_material = "\n".join(
        (
            repr(captured["packet_handoff"].author_payload),
            harness.author_prompts[0],
            outcome.report,
        )
    )
    _assert_adapter_authority_markers_absent(combined_material)


def test_ag_bal_harden_01_poisoned_adapter_authority_cannot_promote_failed_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _PoisonedWeakRecoveryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET,),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-bal-harden-01-poison-weak-session",
            run_id="ag-bal-harden-01-poison-weak-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    assert outcome.execution_trace["blocked_fap_terminal"]["blocked_fap"] is True
    assert outcome.execution_trace["blocked_fap_terminal"]["author_called"] is False

    state = captured["run_kernel"].state
    latest_recovery = state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]["latest"]
    assert latest_recovery["status"] == "attempted_no_coverage"
    candidate_projection = state.evidence_ledger.to_projection().to_dict()
    weak_candidates = _candidate_records_for_url(
        candidate_projection,
        "https://secondary.example/deadline",
    )
    _assert_recovered_candidate_authority_neutral(weak_candidates)
    packet_text = repr(state.final_answer_packet)
    assert "https://secondary.example/deadline" not in packet_text
    assert harness.author_prompts == []
    _assert_adapter_authority_markers_absent(packet_text)


def test_ag_bal_01_recovery_preflight_blocks_invalid_coverage_without_orphan_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_builder = recovery_runtime.build_component_coverage_proposal

    def stale_coverage_proposal(*args: Any, **kwargs: Any) -> Any:
        coverage = original_builder(*args, **kwargs)
        if coverage is None:
            return None
        return replace(coverage, component_digest="stale-component-digest")

    monkeypatch.setattr(
        recovery_runtime,
        "build_component_coverage_proposal",
        stale_coverage_proposal,
    )
    harness = _BalancedRecoveryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET,),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-bal-01-invalid-coverage-session",
            run_id="ag-bal-01-invalid-coverage-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    assert outcome.execution_trace["blocked_fap_terminal"]["blocked_fap"] is True
    assert outcome.execution_trace["blocked_fap_terminal"]["author_called"] is False

    state = captured["run_kernel"].state
    latest_recovery = state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]["latest"]
    assert latest_recovery["status"] == "attempted_no_coverage"
    assert latest_recovery["stop_reason"] == (
        "recovered_evidence_not_semantically_covering_gap"
    )
    assert "component:component-2" not in {
        item["answer_component_id"]
        for item in state.semantic_observation_admission_history
    }
    assert "component:component-2" not in {
        item["answer_component_id"] for item in state.component_coverage_history
    }
    semantic_consumption = state.sufficiency_judgment_projection[
        "semantic_consumption"
    ]
    assert semantic_consumption["covered_component_count"] == 1
    assert semantic_consumption["missing_component_count"] == 1
    assert harness.author_prompts == []
    candidate_records = state.evidence_ledger.to_projection().to_dict()[
        "candidate_records"
    ]
    assert any(record.get("url") == RECOVERED_SOURCE_URL for record in candidate_records)
    assert RECOVERED_SOURCE_URL not in repr(state.final_answer_packet)


@pytest.mark.parametrize("mode", ("Fast", "Deep"))
def test_ag_bal_01_ineligible_modes_do_not_invoke_or_record_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    coordinator_policies: list[ComponentGapRecoveryPolicy] = []
    original_coordinator = orchestrator.execute_component_gap_recovery

    def shared_coordinator(*args: Any, **kwargs: Any) -> Any:
        coordinator_policies.append(kwargs["policy"])
        return original_coordinator(*args, **kwargs)

    monkeypatch.setattr(
        orchestrator,
        "execute_component_gap_recovery",
        shared_coordinator,
    )
    harness, captured = _run_blocked_offline_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        mode=mode,
    )

    assert harness.forbidden_live_calls == []
    assert harness.author_prompts == []
    assert len(harness.search_calls) == 1
    state = captured["run_kernel"].state
    assert len(coordinator_policies) == 1
    assert coordinator_policies[0].requested_mode == mode
    assert coordinator_policies[0].recovery_eligible is False
    assert state.component_gap_recovery_history == []
    assert COMPONENT_GAP_RECOVERY_TRACE_KEY not in state.projections


def test_ag_bal_01_recovery_stops_when_final_answer_packet_already_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _harness, captured = _run_balanced_adapter_absent_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    assert captured["run_kernel"].state.final_answer_packet
    adapter = _AdapterSpy()

    result = execute_authorized_component_gap_recovery(
        **_direct_recovery_kwargs(captured, offline_recovery_adapter=adapter)
    )

    assert result.stop_reason == PRE_RECOVERY_FINAL_PACKET_STOP_REASON
    assert adapter.calls == []


def test_ag_bal_01_duplicate_recovery_invocation_blocks_before_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _harness, captured = _run_balanced_adapter_absent_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    first = captured["run_kernel"].state.projections[
        COMPONENT_GAP_RECOVERY_TRACE_KEY
    ]["latest"]
    assert first["stop_reason"] == "offline_recovery_adapter_absent"
    _remove_final_answer_packet_guard_state(captured)

    adapter = _AdapterSpy()
    second = execute_authorized_component_gap_recovery(
        **_direct_recovery_kwargs(captured, offline_recovery_adapter=adapter)
    )
    assert second.stop_reason == "duplicate_recovery_cycle"
    assert adapter.calls == []


def test_ag_bal_01_projection_deletion_does_not_reset_recovery_idempotency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _harness, captured = _run_balanced_adapter_absent_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    run_kernel = captured["run_kernel"]
    assert len(run_kernel.state.component_gap_recovery_history) == 1
    _remove_final_answer_packet_guard_state(captured)
    del run_kernel.state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]

    adapter = _AdapterSpy()
    second = execute_authorized_component_gap_recovery(
        **_direct_recovery_kwargs(captured, offline_recovery_adapter=adapter)
    )

    assert second.stop_reason == "duplicate_recovery_cycle"
    assert adapter.calls == []
    assert len(run_kernel.state.component_gap_recovery_history) == 2
    recovery_projection = run_kernel.state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]
    assert recovery_projection["history_count"] == 2
    assert recovery_projection["projection_derived_from_canonical_state"] is True


def test_ag_bal_01_multiple_component_gaps_block_before_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _harness, captured = _run_balanced_adapter_absent_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    _remove_final_answer_packet_guard_state(captured)
    captured["run_kernel"].state.component_coverage_history = []
    adapter = _AdapterSpy()

    result = execute_authorized_component_gap_recovery(
        **_direct_recovery_kwargs(captured, offline_recovery_adapter=adapter)
    )

    assert result.stop_reason == "multiple_component_gaps"
    assert adapter.calls == []


def test_ag_bal_01_zero_authorized_existing_gap_query_blocks_before_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _harness, captured = _run_balanced_adapter_absent_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    _remove_final_answer_packet_guard_state(captured)
    query_plan_trace = deepcopy(
        captured["packet_runtime_scope"]["query_authority"].to_trace_fragment()
    )
    metadata = query_plan_trace[QUERY_PLAN_TRACE_KEY]["search_work_consumption"][
        "query_metadata"
    ]["appeal deadline legal rule"]
    metadata["version_bound_component_gap_authorized"] = False
    metadata.pop("version_bound_component_gap_authority", None)
    adapter = _AdapterSpy()

    result = execute_authorized_component_gap_recovery(
        **_direct_recovery_kwargs(
            captured,
            query_plan_trace=query_plan_trace,
            offline_recovery_adapter=adapter,
        )
    )

    assert result.stop_reason == "authorized_component_gap_query_absent"
    assert adapter.calls == []


def test_ag_bal_01_multiple_authorized_existing_gap_queries_block_before_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _harness, captured = _run_balanced_adapter_absent_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    _remove_final_answer_packet_guard_state(captured)
    query_plan_trace = deepcopy(
        captured["packet_runtime_scope"]["query_authority"].to_trace_fragment()
    )
    query_plan = query_plan_trace[QUERY_PLAN_TRACE_KEY]
    metadata = query_plan["search_work_consumption"]["query_metadata"][
        "appeal deadline legal rule"
    ]
    duplicate_query = "appeal deadline legal rule duplicate"
    query_plan["search_work_consumption"]["query_metadata"][duplicate_query] = (
        deepcopy(metadata)
    )
    query_plan.setdefault("admitted_query_order", []).append(duplicate_query)
    query_plan.setdefault("authorized_queries_by_iteration", {}).setdefault(
        "1", []
    ).append(duplicate_query)
    adapter = _AdapterSpy()

    result = execute_authorized_component_gap_recovery(
        **_direct_recovery_kwargs(
            captured,
            query_plan_trace=query_plan_trace,
            offline_recovery_adapter=adapter,
        )
    )

    assert result.stop_reason == "multiple_authorized_component_gap_queries"
    assert adapter.calls == []


@pytest.mark.parametrize(
    ("stale_field", "expected_reason"),
    (
        (
            "accepted_contract_digest",
            "search_judgment_gap_accepted_contract_digest_mismatch",
        ),
        ("component_digest", "search_judgment_gap_component_digest_mismatch"),
    ),
)
def test_ag_bal_01_stale_search_judgment_gap_identity_blocks_before_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stale_field: str,
    expected_reason: str,
) -> None:
    _harness, captured = _run_balanced_adapter_absent_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    _remove_final_answer_packet_guard_state(captured)
    search_judgment_projection = deepcopy(
        captured["run_kernel"].state.search_judgment_projection
    )
    search_judgment_projection["gaps"][0][stale_field] = "stale-digest"
    adapter = _AdapterSpy()

    result = execute_authorized_component_gap_recovery(
        **_direct_recovery_kwargs(
            captured,
            search_judgment_projection=search_judgment_projection,
            offline_recovery_adapter=adapter,
        )
    )

    assert result.stop_reason == expected_reason
    assert adapter.calls == []


def test_ag_bal_01_generated_query_metadata_blocks_before_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _harness, captured = _run_balanced_adapter_absent_path(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    _remove_final_answer_packet_guard_state(captured)
    query_plan_trace = deepcopy(
        captured["packet_runtime_scope"]["query_authority"].to_trace_fragment()
    )
    metadata = query_plan_trace[QUERY_PLAN_TRACE_KEY]["search_work_consumption"][
        "query_metadata"
    ]["appeal deadline legal rule"]
    metadata["query_text_generated"] = True
    adapter = _AdapterSpy()

    result = execute_authorized_component_gap_recovery(
        **_direct_recovery_kwargs(
            captured,
            query_plan_trace=query_plan_trace,
            offline_recovery_adapter=adapter,
        )
    )

    assert result.stop_reason == "authorized_query_was_generated"
    assert adapter.calls == []


def test_initial_and_recovered_material_use_one_shared_typed_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []
    original_builder = orchestrator.build_final_material_runtime_handoff_from_scope

    def shared_builder(scope: Any, *args: Any, **kwargs: Any) -> Any:
        calls.append(kwargs.get("final_evidence_handoff") is not None)
        return original_builder(scope, *args, **kwargs)

    monkeypatch.setattr(
        orchestrator,
        "build_final_material_runtime_handoff_from_scope",
        shared_builder,
    )
    harness = _BalancedRecoveryHarness(tmp_path)

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-bal-01-shared-material-session",
            run_id="ag-bal-01-shared-material-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    assert calls == [True, False]
    assert outcome.report == RAW_AUTHOR_RESPONSE


def test_incomplete_post_recovery_shared_material_fails_closed_before_fap_or_author(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0
    original_builder = orchestrator.build_final_material_runtime_handoff_from_scope

    def incomplete_second_handoff(scope: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        handoff = original_builder(scope, *args, **kwargs)
        if call_count == 2:
            return replace(handoff, author_prompt="")
        return handoff

    monkeypatch.setattr(
        orchestrator,
        "build_final_material_runtime_handoff_from_scope",
        incomplete_second_handoff,
    )
    harness = _BalancedRecoveryHarness(tmp_path)

    with pytest.raises(
        orchestrator.PipelineError,
        match="shared final-material Author prompt is absent",
    ):
        orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-06-24",
                session_id="ag-bal-01-incomplete-material-session",
                run_id="ag-bal-01-incomplete-material-run",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )

    assert call_count == 2
    assert harness.author_prompts == []
    assert harness.author_kwargs == []


def test_cycle_budget_exhaustion_blocks_before_another_adapter_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _WeakRecoveryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET,),
    )
    orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-bal-01-exhausted-session",
            run_id="ag-bal-01-exhausted-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    _remove_final_answer_packet_guard_state(captured)
    adapter = _AdapterSpy()

    result = execute_authorized_component_gap_recovery(
        **_direct_recovery_kwargs(captured, offline_recovery_adapter=adapter)
    )

    assert result.stop_reason == "cycle_budget_exhausted"
    assert adapter.calls == []


def test_supported_cli_composition_leaves_recovery_adapter_absent() -> None:
    repo = Path(__file__).resolve().parents[1]
    cli_source = (repo / "proplex" / "__main__.py").read_text()
    adapter_field = RunDeps.__dataclass_fields__["component_gap_recovery_adapter"]

    assert adapter_field.default is None
    assert "compose_component_gap_recovery_deps" not in cli_source
    assert "component_gap_recovery_adapter=" not in cli_source


def test_mode_policy_resolution_uses_one_temporary_compatibility_envelope() -> None:
    balanced = recovery_coordinator.resolve_component_gap_recovery_mode_policy(
        "Balanced"
    )
    fast = recovery_coordinator.resolve_component_gap_recovery_mode_policy("Fast")
    deep = recovery_coordinator.resolve_component_gap_recovery_mode_policy("Deep")
    unsupported = recovery_coordinator.resolve_component_gap_recovery_mode_policy(
        "Unknown"
    )

    assert balanced.requested_mode == "Balanced"
    assert balanced.mode_supported is True
    assert balanced.recovery_eligible is True
    assert balanced.max_cycles == 1
    assert balanced.offline_only is True
    assert balanced.existing_candidate_query_only is True
    assert balanced.model_generated_query_text_allowed is False
    assert balanced.provider_live_calls_allowed is False
    assert balanced.accepted_amendments_allowed is False
    assert balanced.deep_reconciliation_allowed is False
    assert balanced.temporary_compatibility_values is True

    assert fast.requested_mode == "Fast"
    assert fast.mode_supported is True
    assert fast.recovery_eligible is False
    assert fast.max_cycles == 0
    assert fast.closure_reason == "recovery_closed_this_phase"
    assert fast.temporary_compatibility_values is True

    assert deep.requested_mode == "Deep"
    assert deep.mode_supported is True
    assert deep.recovery_eligible is False
    assert deep.max_cycles == 0
    assert deep.closure_reason == (
        "recovery_closed_pending_explicit_mode_policy_decision"
    )
    assert deep.temporary_compatibility_values is True

    assert unsupported.requested_mode == "Unknown"
    assert unsupported.mode_supported is False
    assert unsupported.recovery_eligible is False
    assert unsupported.max_cycles == 0
    assert unsupported.closure_reason == "unsupported_mode_recovery_closed"
    assert unsupported.temporary_compatibility_values is True


def test_unsupported_mode_envelope_fails_closed_in_shared_primitive() -> None:
    adapter = _AdapterSpy()
    result = execute_authorized_component_gap_recovery(
        run_kernel=object(),
        policy=recovery_coordinator.resolve_component_gap_recovery_mode_policy(
            "Unknown"
        ),
        query_plan_trace=None,
        search_judgment_projection=None,
        evidence_ledger_projection=None,
        search_work_projection=None,
        offline_recovery_adapter=adapter,
    )

    assert result.status.value == "blocked"
    assert result.stop_reason == "unsupported_mode_recovery_closed"
    assert result.budget_record["adapter_invoked"] is False
    assert adapter.calls == []


def test_recovery_handoff_contains_no_final_or_author_material() -> None:
    handoff_fields = {
        item.name
        for item in fields(recovery_coordinator.ComponentGapRecoveryPipelineHandoff)
    }

    assert handoff_fields == {
        "result",
        "recovered",
        "all_passages",
        "evidence_ledger_projection",
        "semantic_state_facts",
    }


def test_shared_final_material_owner_is_typed_and_not_recovery_specific() -> None:
    handoff_fields = {
        item.name for item in fields(final_material_builder.FinalMaterialRuntimeHandoff)
    }

    assert handoff_fields == {
        "final_evidence_handoff",
        "author_evidence",
        "author_evidence_block",
        "author_prompt",
        "author_notes",
    }
    assert callable(
        final_material_builder.build_final_material_runtime_handoff_from_scope
    )


def test_ag_bal_harden_01_structural_guards() -> None:
    repo = Path(__file__).resolve().parents[1]
    runtime = (repo / "core" / "component_gap_recovery_runtime.py").read_text()
    coordinator = (
        repo / "core" / "component_gap_recovery_coordinator.py"
    ).read_text()
    orchestrator_text = (repo / "core" / "pipeline_orchestrator.py").read_text()

    assert "state.projections.get(COMPONENT_GAP_RECOVERY_TRACE_KEY" not in runtime
    assert "_semantic_mutation_snapshot" not in runtime
    assert "_restore_semantic_mutation_snapshot" not in runtime
    assert "offline-fixture" not in runtime
    assert "offline-recovery-fixture" not in runtime
    assert 'setdefault("disposition", "accepted")' not in runtime
    assert "eligible_for_stronger_obligation\", True" not in runtime
    assert "ComponentGapRecoveryPolicy(" not in orchestrator_text
    assert "build_component_gap_recovery_evidence_patch" not in orchestrator_text
    assert "execute_authorized_component_gap_recovery(" not in orchestrator_text
    assert "execute_balanced_component_gap_recovery_from_scope" not in (
        orchestrator_text + coordinator
    )
    assert 'if strategy == "Balanced"' not in orchestrator_text
    assert "runtime_scope" not in coordinator
    assert "locals()" not in coordinator
    assert orchestrator_text.count(
        "build_final_material_runtime_handoff_from_scope("
    ) == 2
    for forbidden_field in (
        "final_top_evidence",
        "unique_source_urls",
        "ordered_sources",
        "evidence_block",
        "cached_prefix",
        "author_evidence",
        "author_evidence_block",
        "author_prompt",
        "author_notes",
        "final_answer_packet",
        "author_provider",
        "author_model",
        "author_effort",
    ):
        assert forbidden_field not in coordinator
    assert "Manifest" not in runtime + coordinator
    assert "Envelope" not in runtime + coordinator
