"""PRODUCT_PROOF: Boundary B through the ordinary offline backend."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.ordinary_multicomponent_synthesis_runtime as runtime
import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT,
    safe_packet_digest,
)
from core.protocols import NullStatusWriter
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


UNIQUE_RECOVERED_RESULT = "BOUNDARY_B_RECOVERED_E_RESULT_7F3A"
BOUNDARY_B_QUERY = (
    "For the fictional Alder filing rule, determine the filing route that "
    "follows from the current eligibility fact and any necessary searchable "
    "premise."
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _BoundaryBPlanner:
    def produce(self, _planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        direct_strategy = {
            "strategy_id": "strategy:premise_D:primary:1",
            "component_id": "premise_D",
            "candidate_kind": "primary",
            "candidate_query_text": "Alder current eligibility fact",
            "requested_role": "initial",
            "source_obligation_candidate_ids": ["obligation:premise_D"],
            "domain_constraints": {"include": [], "exclude": []},
            "distinct_need_justification": (
                "Directly establish the accepted current premise."
            ),
            "immediate_dispatch_requested": True,
            "immediate_dispatch_distinct_need": True,
            "recon_requirement": {
                "posture": "not_needed",
                "unresolved_dimension_ids": [],
                "candidate_queries": [],
                "required_for_truthful_targeting": False,
            },
            "provider_name_neutral": True,
        }
        return {
            "question_meaning_summary": (
                "Answer target E from current premise D and any independently "
                "admitted necessary premise."
            ),
            "requested_output": "Determine the governed Alder filing route.",
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": (
                "Determine target_E from its exact admitted premises."
            ),
            "semantic_slots": [
                {
                    "slot_id": "slot:alder",
                    "slot_kind": "entity",
                    "status": "explicit",
                    "candidate_values": ["Alder"],
                    "selected_value": "Alder",
                    "materiality": "material",
                    "user_confirmation_required": False,
                }
            ],
            "answer_components": [
                {
                    "component_id": "premise_D",
                    "component_revision": "1",
                    "component_purpose": "supporting_premise",
                    "user_facing_label": "Current eligibility premise D",
                    "user_facing_question": (
                        "What is the current Alder eligibility fact?"
                    ),
                    "requirement_posture": "required",
                    "acceptance_criteria": [
                        "Use one exact direct source for premise D."
                    ],
                    "semantic_slot_ids": ["slot:alder"],
                    "source_obligation_candidate_ids": [
                        "obligation:premise_D"
                    ],
                    "allowed_support_kinds": ["direct"],
                    "max_inference_depth": 0,
                    "materiality": "material",
                    "partial_answer_policy": "qualify_visible_gap",
                },
                {
                    "component_id": "target_E",
                    "component_revision": "1",
                    "component_purpose": "user_facing_answer_target",
                    "user_facing_label": "Governed filing route E",
                    "user_facing_question": (
                        "Which Alder filing route follows?"
                    ),
                    "requirement_posture": "required",
                    "acceptance_criteria": [
                        "Use only an admitted relationship over current premises."
                    ],
                    "semantic_slot_ids": ["slot:alder"],
                    "source_obligation_candidate_ids": [],
                    "allowed_support_kinds": ["inferred"],
                    "max_inference_depth": 1,
                    "dependency_component_ids": ["premise_D"],
                    "materiality": "material",
                    "partial_answer_policy": "qualify_visible_gap",
                },
            ],
            "source_obligation_candidates": [
                {
                    "candidate_id": "obligation:premise_D",
                    "obligation_kind": "supporting_fact",
                    "component_candidate_ids": ["premise_D"],
                    "strictness": "required",
                    "metadata": {"provider_name_neutral": True},
                }
            ],
            "component_search_requirements": [
                {
                    "component_id": "premise_D",
                    "requirement_id": "search-requirement:premise_D:initial",
                    "requirement_summary": (
                        "Find direct support for premise D."
                    ),
                    "source_obligation_candidate_ids": [
                        "obligation:premise_D"
                    ],
                    "preferred_source_kinds": ["supporting_fact"],
                    "metadata": {
                        "query_strategy_candidates": [direct_strategy],
                        "provider_name_neutral": True,
                    },
                }
            ],
            "relationship_hypotheses": [
                {
                    "local_hypothesis_key": "target_E",
                    "relationship_type": "conditional_filing_route",
                    "component_inputs": ["premise_D"],
                    "proposal_only": True,
                }
            ],
            "material_ambiguity_posture": "none_detected",
            "mandatory_caveats": [],
            "prohibited_upgrades": [
                "Do not treat a planning hypothesis as admitted inference."
            ],
            "normalization_obligations": [],
            "assumptions": [],
            "unsupported_or_deferred_outputs": [],
            "contract_amendment_candidates": [],
            "planner_model_metadata": {
                "model_adapter_enabled": False,
                "provider": "none",
                "model": "offline-fixture",
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "provider_payload_retained": False,
            },
        }


class BoundaryBOrdinaryHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=BOUNDARY_B_QUERY,
            core_topic="Alder filing rule",
            primary_entity="Alder",
            researcher_queries=("Alder current eligibility fact",),
            raw_author_response=(
                "The admitted premises establish "
                + UNIQUE_RECOVERED_RESULT
                + "."
            ),
            read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
            logger_name="test_boundary_b_ordinary_product",
        )
        self.role_packets: list[dict[str, Any]] = []

    def deps(self):
        return replace(
            super().deps(),
            search_planner_adapter=_BoundaryBPlanner(),
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        if len(self.search_calls) <= 1:
            return [
                {
                    "source_id": 801,
                    "title": "Alder eligibility premise D",
                    "url": "https://alder.example/premise-d",
                    "text": (
                        "An Alder applicant has the accepted current "
                        "eligibility status described by premise D."
                    ),
                    "score": 1.0,
                    "credibility": 4,
                    "source_tier": "secondary",
                    "source_class": "supporting_fact",
                    "currentness_signal": "current",
                    "readable_status": "readable",
                    "disposition": "accepted",
                    "query_ref": "Alder current eligibility fact",
                    "_provider": "offline_fake_search",
                }
            ]
        return [
            {
                "source_id": 802,
                "title": "Alder direct searched premise C",
                "url": "https://alder.example/premise-c",
                "text": (
                    "The Alder rule directly establishes the missing filing "
                    "condition represented by searched premise C."
                ),
                "score": 1.0,
                "credibility": 4,
                "source_tier": "secondary",
                "source_class": "supporting_fact",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "query_ref": "Alder missing filing condition premise C",
                "_provider": "offline_fake_search",
            }
        ]

    @staticmethod
    def _component_by_id(payload: Mapping[str, Any], component_id: str) -> dict:
        for item in payload.get("accepted_component_refs") or ():
            if item.get("component_id") == component_id:
                return dict(item)
        raise AssertionError(f"missing accepted component {component_id}")

    def ask_model(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if (
            system_prompt in ROLE_SYSTEM_PROMPTS.values()
            or system_prompt
            == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT
        ):
            payload = json.loads(prompt)
            self.role_packets.append(
                {"system_prompt": system_prompt, "payload": payload}
            )
            self._record_model_call(system_prompt, kwargs)
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
                question = str(
                    payload.get("component_ref", {}).get(
                        "user_facing_question"
                    )
                    or ""
                )
                claim = (
                    "Direct premise C is established by its dedicated source."
                    if "searched premise" in question.casefold()
                    or "direct evidence establishes" in question.casefold()
                    else "Direct premise D is established by its dedicated source."
                )
                return json.dumps(
                    {
                        "claim_text": claim,
                        "support_status": "supported",
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_DPRIME]:
                return json.dumps(
                    {
                        "validation_status": "supported",
                        "reasons": [
                            "The exact dedicated material supports the premise."
                        ],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[
                ROLE_CROSS_COMPONENT_ANALYST
            ]:
                target = self._component_by_id(payload, "target_E")
                premise_d = self._component_by_id(payload, "premise_D")
                return json.dumps(
                    {
                        "synthesis_proposals": [
                            {
                                "synthesis_key": "target_E",
                                "claim_text": (
                                    "Premise D identifies the current case, but "
                                    "target E still requires searched premise C."
                                ),
                                "relationship_type": (
                                    "conditional_filing_route_pending_premise"
                                ),
                                "component_inputs": ["premise_D"],
                                "synthesis_inputs": [],
                                "caveats": [
                                    "The missing filing condition remains unresolved."
                                ],
                                "nonclaims": [
                                    "The final filing route is not established "
                                    "before recovery."
                                ],
                                "blockers": [],
                            }
                        ],
                        "query_resolution_proposals": [
                            {
                                "classification": "searched_premise",
                                "local_proposal_key": "recover_premise_C",
                                "local_target_key": "target_E",
                                "answer_target_refs": [target],
                                "parent_component_refs": [target],
                                "current_dependency_component_refs": [
                                    premise_d
                                ],
                                "premise_semantics": (
                                    "Alder missing filing condition premise C"
                                ),
                                "source_obligation_specification": {
                                    "candidate_id": (
                                        "obligation:searched-premise-C"
                                    ),
                                    "obligation_kind": "supporting_fact",
                                },
                                "necessity_rationale": (
                                    "The accepted filing-route target cannot be "
                                    "fulfilled without premise C."
                                ),
                                "why_current_premises_insufficient": (
                                    "Premise D identifies eligibility but does "
                                    "not establish the filing condition."
                                ),
                                "searchability_material_need_posture": (
                                    "material_and_searchable"
                                ),
                                "recovery_generation": {
                                    "parent_ref": "initial-searchos-state",
                                    "depth": 1,
                                },
                                "assumptions": [],
                                "caveats": [
                                    "Premise C remains direct-source bounded."
                                ],
                                "prohibited_upgrades": [
                                    "Do not infer premise C from the search direction."
                                ],
                            }
                        ],
                    }
                )
            if (
                system_prompt
                == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT
            ):
                recovered = dict(
                    payload["current_recovered_component_ref"]
                )
                target = self._component_by_id(payload, "target_E")
                premise_refs = sorted([
                    {
                        key: node.get(key)
                        for key in (
                            "node_kind",
                            "node_id",
                            "node_revision",
                            "node_digest",
                            "component_id",
                            "synthesis_key",
                            "status",
                            "current",
                            "stale",
                        )
                    }
                    for node in [
                        *payload.get("licensed_current_component_refs", []),
                        recovered,
                    ]
                    if node.get("component_id")
                    in {"premise_D", recovered["component_id"]}
                ], key=safe_packet_digest)
                return json.dumps(
                    {
                        "synthesis_proposals": [
                            {
                                "synthesis_key": "target_E",
                                "claim_text": UNIQUE_RECOVERED_RESULT,
                                "relationship_type": (
                                    "conditional_filing_route"
                                ),
                                "component_inputs": sorted(
                                    [
                                        "premise_D",
                                        recovered["component_id"],
                                    ]
                                ),
                                "affected_synthesis_inputs": [],
                                "preserved_synthesis_inputs": [],
                                "caveats": [],
                                "nonclaims": [],
                                "blockers": [],
                            }
                        ],
                        "query_resolution_proposals": [
                            {
                                "classification": "inferred_conclusion",
                                "local_proposal_key": "infer_target_E",
                                "local_target_key": "target_E",
                                "answer_target_ref": target,
                                "current_admitted_premise_node_refs": (
                                    premise_refs
                                ),
                                "relationship_type": (
                                    "conditional_filing_route"
                                ),
                                "proposed_conclusion": (
                                    UNIQUE_RECOVERED_RESULT
                                ),
                                "support_kind": "inferred",
                                "proposed_semantic_inference_depth": 1,
                                "current_graph_ref": payload["graph_ref"],
                                "existing_specialist_handoff_refs": [],
                                "assumptions": [],
                                "caveats": [
                                    "The result is an admitted inference."
                                ],
                                "prohibited_upgrades": [
                                    "Do not say either premise source directly states E."
                                ],
                            }
                        ],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SYNTHESIS_DPRIME]:
                return json.dumps(
                    {
                        "validation_status": "supported",
                        "reasons": [
                            "The exact current inputs support the bounded proposal."
                        ],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER]:
                return json.dumps(
                    {
                        "challenge_status": "passed",
                        "reasons": [
                            "The bounded case preserves exact premise lineage."
                        ],
                        "challenge_targets": [],
                        "caveats": [],
                        "nonclaims": [],
                    }
                )
        return super().ask_model(prompt, system_prompt, **kwargs)


def test_balanced_searched_premise_changes_ordinary_backend_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_legacy(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("retired legacy derived-recovery path was invoked")

    monkeypatch.setattr(runtime, "_execute_fresh_resynthesis", no_legacy)
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
            session_id="boundary-b-ordinary-request",
            run_id="boundary-b-ordinary-run",
            smart_search_judgment_model=True,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    kernel = captured["run_kernel"]
    assert "multicomponent_component_work_graph_v1" in kernel.state.projections
    graph = kernel.state.projections[
        "multicomponent_component_work_graph_v1"
    ]
    lease = kernel.state.searchos_state["recovery_lease"]
    admissions = kernel.state.searchos_state[
        "recovery_cycle_admission_history"
    ]
    terminals = kernel.state.searchos_state[
        "recovery_cycle_terminal_history"
    ]
    target = next(
        item
        for item in captured["sufficiency_projection"][
            "multicomponent_graph_consumption"
        ]["answer_target_fulfillments"]
        if item["component_id"] == "target_E"
    )

    assert len(kernel.state.contract_amendment_admission_history) == 1
    assert len(kernel.state.contract_amendment_application_history) == 1
    assert (
        kernel.state.current_answer_contract["accepted_contract_digest"]
        != kernel.state.initial_answer_contract["accepted_contract_digest"]
    )
    assert len(admissions) == len(terminals) == 1
    assert admissions[0]["generation_depth"] == 1
    assert admissions[0]["recovery_classification"] == "searched_premise"
    assert (
        admissions[0]["whole_run_lease_ref"]["recovery_lease_id"]
        == lease["recovery_lease_id"]
    )
    assert terminals[0]["cycle_id"] == admissions[0]["cycle_id"]
    assert terminals[0]["terminal_status"] == "recovered", (
        terminals[0].get("terminal_reason"),
        harness.search_calls,
        harness.read_assessment_calls,
    )
    assert kernel.state.searchos_state.get("active_recovery_cycle_ref") in (
        None,
        {},
    )
    recovered_candidates = [
        item
        for item in graph["component_nodes"]
        if item["component_id"] != "premise_D"
    ]
    assert recovered_candidates, (
        terminals,
        graph,
        outcome.failure_card,
    )
    recovered = recovered_candidates[0]
    assert recovered["semantic_inference_depth"] == 0
    assert recovered["component_coverage_ref"]["coverage_state"] == (
        "satisfied"
    )
    assert target["selected_support_kind"] == "inferred"
    assert target["fulfillment_status"] == "fulfilled_inferred"
    inferred_fulfillment = target["inferred_fulfillment_ref"]
    assert inferred_fulfillment["semantic_inference_depth"] == 1
    assert {
        item["component_id"]
        for item in inferred_fulfillment["premise_node_refs"]
    } == {"premise_D", recovered["component_id"]}
    assert graph["selective_recomputation_rounds"] == 1
    assert graph["graph_status"] == "ready"
    assert captured["sufficiency_projection"]["decision"] == (
        "ready_with_admitted_inference"
    )
    assert captured["sufficiency_projection"]["final_answer_posture"] == (
        "sufficient_with_admitted_inference"
    )
    packet = captured["packet_handoff"].packet
    inferred_entries = [
        dict(item)
        for item in packet.admitted_synthesis_entries
        if dict(item).get("support_kind") == "inferred"
    ]
    assert inferred_entries
    assert inferred_entries[0]["answer_target_component_id"] == "target_E"
    assert not any(
        dict(item).get("component_id") == "target_E"
        for item in packet.direct_component_entries
    )
    assert UNIQUE_RECOVERED_RESULT in captured[
        "packet_handoff"
    ].author_payload.prompt
    assert UNIQUE_RECOVERED_RESULT in outcome.report
    assert len(harness.author_prompts) == 1
    assert captured["author_handoff_called"] is True
    assert not any(
        "_begin_scheduler_dynamic_recovery" in str(item)
        or "_attempt_dynamic_recovery" in str(item)
        for item in kernel.state.projections
    )
