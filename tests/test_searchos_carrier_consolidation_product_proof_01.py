"""Phase-3 ordinary product proof: AnswerContract -> QueryPlan without carriers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from core.run_kernel import ActionType
from core.search_planner_model_adapter import accept_planner_model_output
from tests.fixtures.search_planner_sparse_semantic_corpus import valid_case
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    install_handoff_capture,
    offline_balanced_run_config,
    run_post_retirement_ordinary_pipeline,
)
from tests.test_searchos_boundary_b_ordinary_product_01 import (
    BoundaryBOrdinaryHarness,
)
from tests.test_searchos_existing_gap_recovery_and_stop_foundation_01 import (
    _initial_incomplete_canonical_rows,
    _install_initially_unsupported_component,
    _recovered_canonical_rows,
)

_RETIRED_ACTION_VALUES = {
    "scout_disambiguate",
    "search_planner_revise",
    "search_work_plan_construct",
    "query_production",
}


class _SparseProposalAdapter:
    def __init__(self, proposal: Mapping[str, Any]) -> None:
        self.proposal = deepcopy(dict(proposal))

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return accept_planner_model_output(
            deepcopy(self.proposal),
            user_query_text=str(planner_input["user_query_text_for_planning"]),
            requested_mode=str(planner_input["requested_mode"]),
        )


def _product_deps(proposal: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "search_planner_adapter": _SparseProposalAdapter(proposal),
        "provider_availability": {"tavily": True, "serper": True},
    }


def _evidence_row(name: str, *, suffix: str) -> dict[str, Any]:
    return {
        "title": f"{name} bounded offline source",
        "url": f"https://alpha.example/{suffix}",
        "text": f"Bounded directional material about {name}.",
        "source_tier": "official",
        "source_class": "primary_source_documents",
        "currentness_signal": "current",
        "readable_status": "readable",
        "disposition": "accepted",
    }


def _ordered_query_plan_items(outcome: Any) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in outcome.execution_trace["query_plan"]["items"]
        if item["status"] == "ordered"
    ]


def _assert_ordinary_carriers_retired(harness: Any, outcome: Any) -> None:
    kernel = harness.run_kernel
    assert kernel is not None
    issued = {
        action.action_type.value
        for action in kernel.state.issued_actions.values()
    }
    assert issued.isdisjoint(_RETIRED_ACTION_VALUES)
    assert ActionType.QUERY_PLAN_ADMISSION.value in issued
    projections = kernel.state.projections
    assert "query_production" not in projections
    assert "search_work_plan_construction" not in projections
    for item in _ordered_query_plan_items(outcome):
        assert item.get("search_work_plan_ref") in (None, {}, [])
        assert "discovery_job_class" in item
        assert item["discovery_job_class"] in {
            "orientation",
            "standard_discovery",
            "deep_discovery",
        }
        assert item.get("provider_name") in (None, "")
    accepted = kernel.state.initial_answer_contract
    assert accepted["canonical_state"] is True
    assert accepted["accepted_answer_component_count"] >= 1
    ledger = kernel.state.evidence_ledger
    assert ledger is not None
    trace = str(outcome.execution_trace)
    assert "query_candidates_produced" not in trace
    assert "search_work_plan_constructed" not in trace
    assert "scout_disambiguate" not in issued
    assert kernel.state.scout_disambiguation_report_history == []
    assert kernel.state.search_planner_revision_history == []


def test_a_clear_direct_python_isclose_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("official_source_direct_simple")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="Python math.isclose defaults",
        primary_entity="Python",
        evidence_rows=[_evidence_row("Python", suffix="phase3-a")],
        deps_overrides=_product_deps(case["proposal"]),
    )
    _assert_ordinary_carriers_retired(harness, outcome)
    assert {item["discovery_job_class"] for item in _ordered_query_plan_items(outcome)} == {
        "standard_discovery"
    }
    assert len(harness.search_calls) == 1


def test_b_factual_uncertainty_galloway(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("factual_identity_uncertainty")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="recent Galloway controversy",
        primary_entity="Galloway",
        evidence_rows=[_evidence_row("Scott Galloway", suffix="phase3-b-orientation")],
        followup_evidence_rows=[
            _evidence_row("Scott Galloway", suffix="phase3-b-standard")
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(case["proposal"]),
    )
    _assert_ordinary_carriers_retired(harness, outcome)
    assert [
        item["discovery_job_class"]
        for item in _ordered_query_plan_items(outcome)
    ] == ["orientation", "standard_discovery"]
    accepted_slot = harness.run_kernel.state.initial_answer_contract[
        "accepted_semantic_slot_refs"
    ][0]
    assert accepted_slot["status"] == "unresolved"
    assert accepted_slot.get("selected_value") is None


def test_c_true_user_ambiguity_mercury(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("true_user_intent_ambiguity")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="Mercury",
        primary_entity="Mercury",
        evidence_rows=[_evidence_row("Mercury", suffix="phase3-c")],
        deps_overrides=_product_deps(case["proposal"]),
    )
    _assert_ordinary_carriers_retired(harness, outcome)
    assert _ordered_query_plan_items(outcome) == []
    assert harness.search_calls == []
    slot = harness.run_kernel.state.initial_answer_contract[
        "accepted_semantic_slot_refs"
    ][0]
    assert slot["user_confirmation_required"] is True


def test_d_one_component_two_factual_uncertainties(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {
                "need": "Report the current policy for the intended Acme product version",
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "unresolved",
                        "candidates": ["Acme Legacy", "Acme Current"],
                    },
                    {
                        "kind": "variant",
                        "status": "unresolved",
                        "candidates": ["v2", "v3"],
                    },
                ],
            }
        ],
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="What is the current policy for the intended Acme version?",
        core_topic="Acme current product policy and version",
        primary_entity="Acme",
        evidence_rows=[_evidence_row("Acme Current v3", suffix="phase3-d")],
        followup_evidence_rows=[
            _evidence_row("Acme Current v3", suffix="phase3-d-standard")
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(proposal),
    )
    _assert_ordinary_carriers_retired(harness, outcome)
    accepted_slots = harness.run_kernel.state.initial_answer_contract[
        "accepted_semantic_slot_refs"
    ]
    assert len(accepted_slots) == 2


def test_e_one_component_factual_and_clarification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {
                "need": "Report the intended Acme policy",
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "unresolved",
                        "candidates": ["Acme Legacy", "Acme Current"],
                    },
                    {
                        "kind": "variant",
                        "status": "ambiguous",
                        "candidates": ["consumer policy", "enterprise policy"],
                        "user_confirmation_required": True,
                    },
                ],
            }
        ],
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="Report the intended Acme policy.",
        core_topic="intended Acme policy",
        primary_entity="Acme",
        evidence_rows=[_evidence_row("Acme Current", suffix="phase3-e")],
        followup_evidence_rows=[
            _evidence_row("Acme Current", suffix="phase3-e-standard")
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(proposal),
    )
    _assert_ordinary_carriers_retired(harness, outcome)
    accepted_slots = harness.run_kernel.state.initial_answer_contract[
        "accepted_semantic_slot_refs"
    ]
    assert len(accepted_slots) == 2
    assert any(item["user_confirmation_required"] is True for item in accepted_slots)
    assert any(item["user_confirmation_required"] is False for item in accepted_slots)


def test_f_mixed_multi_component_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {"key": "stable", "need": "Report Alpha's current operating rule"},
            {
                "key": "identity",
                "need": "Identify the relevant Galloway controversy",
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "unresolved",
                        "candidates": ["Scott Galloway", "George Galloway"],
                    }
                ],
            },
            {
                "key": "ambiguous",
                "need": "Explain the intended Mercury subject",
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "ambiguous",
                        "candidates": ["planet", "element", "automobile brand"],
                        "user_confirmation_required": True,
                    }
                ],
            },
        ],
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=(
            "Report Alpha's rule, identify the relevant Galloway controversy, "
            "and explain Mercury."
        ),
        core_topic="Alpha rule, Galloway controversy, and Mercury",
        primary_entity="Alpha",
        evidence_rows=[_evidence_row("Alpha", suffix="phase3-f")],
        followup_evidence_rows=[
            _evidence_row("Scott Galloway", suffix="phase3-f-orientation")
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(proposal),
    )
    _assert_ordinary_carriers_retired(harness, outcome)
    initial = [
        item
        for item in _ordered_query_plan_items(outcome)
        if item["iteration"] == 1
    ]
    assert [item["discovery_job_class"] for item in initial] == [
        "standard_discovery",
        "orientation",
    ]
    assert harness.run_kernel.state.initial_answer_contract[
        "accepted_answer_component_count"
    ] == 3


def test_g_zero_result_orientation_bounded_refinement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("factual_identity_uncertainty")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="recent Galloway controversy",
        primary_entity="Galloway",
        evidence_rows=[],
        followup_evidence_rows=[],
        read_assessment_decision="ZERO_ORIENTATION_REFINE",
        deps_overrides=_product_deps(case["proposal"]),
    )
    _assert_ordinary_carriers_retired(harness, outcome)
    assert [item["discovery_job_class"] for item in _ordered_query_plan_items(outcome)] == [
        "orientation",
        "orientation",
    ]
    assert len(harness.search_calls) == 2


def test_h_typed_deep_discovery_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("minimal_direct_simple")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="capital of France",
        primary_entity="France",
        evidence_rows=[_evidence_row("France", suffix="phase3-h")],
        read_assessment_decision="STANDARD_TO_DEEP_BLOCK",
        deps_overrides=_product_deps(case["proposal"]),
    )
    _assert_ordinary_carriers_retired(harness, outcome)
    assert [
        item["discovery_job_class"]
        for item in _ordered_query_plan_items(outcome)
    ] == ["standard_discovery", "deep_discovery"]
    records = outcome.execution_trace["provider_plan"]["records"]
    assert records[-1]["route_decision"]["fidelity"] == "blocked"
    assert records[-1]["route_decision"]["block_reason"] == (
        "general_deep_authorization_required"
    )


def test_i_existing_component_searchos_gap_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=False,
        recovered_claim="Alpha's current canonical API response name is Raven.",
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="What do Alpha's current API docs say about the Raven endpoint?",
        core_topic="Alpha current API documentation",
        primary_entity="Alpha",
        researcher_queries=["Alpha current API documentation"],
        evidence_rows=_initial_incomplete_canonical_rows(),
        followup_evidence_rows=_recovered_canonical_rows(),
        read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
        read_content_by_url={
            "https://docs.alpha.example/api": (
                "Alpha's canonical API documentation lists the endpoint, "
                "but omits its current response name."
            ),
            "https://docs.alpha.example/api/raven": (
                "Alpha's current canonical API response name is Raven."
            ),
            "https://example.test/alpha-api-overview": (
                "A secondary overview confirms that Alpha publishes an API, "
                "without stating the current canonical response name."
            ),
        },
        raw_author_response=(
            "Alpha's current canonical API response name is Raven. "
            "[[1]](https://docs.alpha.example/api/raven)"
        ),
    )
    _assert_ordinary_carriers_retired(harness, outcome)
    terminal = harness.run_kernel.state.projections["searchos_recovery_cycle_terminal"]
    assert terminal["terminal_status"] == "recovered"


def test_j_boundary_b_searched_premise_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = BoundaryBOrdinaryHarness(tmp_path)
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
            current_date="2026-07-25",
            session_id="phase3-boundary-b-request",
            run_id="phase3-boundary-b-run",
            smart_search_judgment_model=True,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    kernel = captured["run_kernel"]
    harness.run_kernel = kernel
    _assert_ordinary_carriers_retired(harness, outcome)
    admissions = kernel.state.searchos_state["recovery_cycle_admission_history"]
    assert admissions[0]["recovery_classification"] == "searched_premise"
    terminals = kernel.state.searchos_state["recovery_cycle_terminal_history"]
    assert terminals[0]["terminal_status"] == "recovered"
