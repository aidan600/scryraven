"""PRODUCT-PATH-REGRESSION: direct-source numeric lineage binding.

Proof class: PRODUCT. Validation bucket: phase_focus. Surface: FAP quantitative
preflight consuming admitted claim lineage plus claim-literal accounting in
bound material. Closed: provider routing, SearchPlanner policy, Sufficiency
policy, Analyst schema, live calls.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import core.quantitative_finalization_authority as quantitative_evaluator
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
)
from core.search_planner_runtime import DeterministicSearchPlannerAdapter
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)
from tests.test_searchos_slice_a_product_cutover_01 import (
    _establish_official_current_qualification_truth,
)


def _install_fee_planner_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    original_produce = DeterministicSearchPlannerAdapter.produce

    def produce(self: Any, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        result = json.loads(json.dumps(original_produce(self, planner_input)))
        component = dict(result["answer_components"][0])
        component.update(
            {
                "semantic_slot_ids": ["slot:application_fee"],
                "source_obligation_candidate_ids": ["obligation:official_current"],
                "user_facing_question": "What is the published application fee?",
            }
        )
        result["semantic_slots"] = [
            {
                "slot_id": "slot:application_fee",
                "slot_kind": "parameter",
                "status": "explicit",
                "selected_value": "application_fee",
                "materiality": "material",
            },
        ]
        result["answer_components"] = [component]
        result["source_obligation_candidates"] = [
            {
                "candidate_id": "obligation:official_current",
                "obligation_kind": "official_current",
                "component_candidate_ids": [component["component_id"]],
                "strictness": "required",
            }
        ]
        requirement = dict(result["component_search_requirements"][0])
        requirement["source_obligation_candidate_ids"] = ["obligation:official_current"]
        requirement_metadata = dict(requirement.get("metadata") or {})
        strategies = [
            dict(item)
            for item in requirement_metadata.get("query_strategy_candidates") or ()
        ]
        for strategy in strategies:
            strategy["source_obligation_candidate_ids"] = ["obligation:official_current"]
        requirement_metadata["query_strategy_candidates"] = strategies
        requirement["metadata"] = requirement_metadata
        result["component_search_requirements"] = [requirement]
        return result

    monkeypatch.setattr(DeterministicSearchPlannerAdapter, "produce", produce)


def test_non_q1_ordinary_direct_source_numeric_fee_completes_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _establish_official_current_qualification_truth(monkeypatch)
    _install_fee_planner_contract(monkeypatch)
    original_validator = (
        quantitative_evaluator.validate_author_output_quantitative_authority
    )

    def fail_if_product_calls_retired_validator(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("post-Author quantitative evaluator must not be a PRODUCT gate")

    monkeypatch.setattr(
        quantitative_evaluator,
        "validate_author_output_quantitative_authority",
        fail_if_product_calls_retired_validator,
    )
    fee_sentence = (
        "The official Example Program fee schedule states the published "
        "application fee is $45."
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query=(
            "According to the official Example Program fee schedule, what is "
            "the published application fee?"
        ),
        core_topic="Example Program published application fee",
        primary_entity="Example Program",
        researcher_queries=["Example Program official published application fee"],
        analyst_response=(
            "The official fee schedule states the published application fee is $45."
        ),
        raw_author_response=(
            "The published application fee is $45. "
            "[[1]](https://official.example/fee-schedule)"
        ),
        inject_default_source_qualification=False,
        evidence_rows=[
            {
                "title": "Example Program fee schedule",
                "url": "https://official.example/fee-schedule",
                "text": fee_sentence,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
            }
        ],
        read_content_by_url={
            "https://official.example/fee-schedule": fee_sentence
        },
    )
    monkeypatch.setattr(
        quantitative_evaluator,
        "validate_author_output_quantitative_authority",
        original_validator,
    )

    packet = outcome.execution_trace["final_answer_packet"]
    admissions = harness.run_kernel.state.projections[
        "multicomponent_component_admission"
    ]
    graph = harness.run_kernel.state.projections[
        "multicomponent_component_work_graph_v1"
    ]
    manifest = packet["quantitative_finalization_authority_manifest"]
    assert outcome.terminal_status == "completed"
    assert "direct_source_numeric" not in {
        row["authority_kind"] for row in manifest["authorized_numeric_claims"]
    }
    assert admissions["physical_component_analyst_calls"] == 1
    assert graph["physical_call_accounting"]["component_analyst_calls"] == 1
    assert graph["physical_call_accounting"].get("specialist_calls", 0) == 0
    assert graph["physical_call_accounting"]["cross_component_analyst_calls"] == 0
    assert graph["physical_call_accounting"]["scrutineer_calls"] == 0
    assert graph["physical_call_accounting"]["synthesis_dprime_calls"] == 0
    assert harness.author_prompts and len(harness.author_prompts) == 1
    assert harness.run_kernel.state.author_observation[
        "post_author_quantitative_semantic_gate_active"
    ] is False
    assert packet["citation_eligible"]
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] in harness.model_system_prompts
    assert all(
        ROLE_SYSTEM_PROMPTS[role] not in harness.model_system_prompts
        for role in (
            ROLE_COMPONENT_DPRIME,
            ROLE_CROSS_COMPONENT_ANALYST,
            ROLE_SYNTHESIS_DPRIME,
        )
    )
    assert outcome.report != ""
    assert "45" in outcome.report
