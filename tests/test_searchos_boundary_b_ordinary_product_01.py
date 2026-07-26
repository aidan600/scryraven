"""PRODUCT_PROOF: Boundary B through the ordinary offline backend."""

from __future__ import annotations

import json
from copy import deepcopy
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
from core.searchos_slice_a_product_runtime import (
    SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
)
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
            "distinct_need_justification": ("Directly establish the accepted current premise."),
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
                "Answer target E from current premise D and any independently admitted necessary premise."
            ),
            "requested_output": "Determine the governed Alder filing route.",
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": ("Determine target_E from its exact admitted premises."),
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
                    "user_facing_question": ("What is the current Alder eligibility fact?"),
                    "requirement_posture": "required",
                    "acceptance_criteria": ["Use one exact direct source for premise D."],
                    "semantic_slot_ids": ["slot:alder"],
                    "source_obligation_candidate_ids": ["obligation:premise_D"],
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
                    "user_facing_question": ("Which Alder filing route follows?"),
                    "requirement_posture": "required",
                    "acceptance_criteria": ["Use only an admitted relationship over current premises."],
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
                    "requirement_summary": ("Find direct support for premise D."),
                    "source_obligation_candidate_ids": ["obligation:premise_D"],
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
            "prohibited_upgrades": ["Do not treat a planning hypothesis as admitted inference."],
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
            raw_author_response=("The admitted premises establish " + UNIQUE_RECOVERED_RESULT + "."),
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
                    "text": ("An Alder applicant has the accepted current eligibility status described by premise D."),
                    "score": 1.0,
                    "credibility": 4,
                    "source_tier": "official",
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
                "source_tier": "official",
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
            or system_prompt == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT
        ):
            payload = json.loads(prompt)
            self.role_packets.append({"system_prompt": system_prompt, "payload": payload})
            self._record_model_call(system_prompt, kwargs)
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
                question = str(payload.get("component_ref", {}).get("user_facing_question") or "")
                claim = (
                    "Direct premise C is established by its dedicated source."
                    if "searched premise" in question.casefold() or "direct evidence establishes" in question.casefold()
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
                        "reasons": ["The exact dedicated material supports the premise."],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
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
                                "relationship_type": ("conditional_filing_route_pending_premise"),
                                "component_inputs": ["premise_D"],
                                "synthesis_inputs": [],
                                "caveats": ["The missing filing condition remains unresolved."],
                                "nonclaims": ["The final filing route is not established before recovery."],
                                "blockers": [],
                            }
                        ],
                        "query_resolution_proposals": [
                            {
                                "classification": "searched_premise",
                                "local_proposal_key": "recover_premise_C",
                                "local_target_key": "target_E",
                                "normalized_premise_identity": ("alder missing filing condition premise c"),
                                "answer_target_refs": [target],
                                "parent_component_refs": [target],
                                "current_dependency_component_refs": [premise_d],
                                "premise_semantics": ("Alder missing filing condition premise C"),
                                "user_facing_label": ("Alder signed-condition premise C"),
                                "user_facing_question": ("Which signed Alder filing condition establishes premise C?"),
                                "acceptance_criteria": ["Use the exact signed Alder filing-condition record."],
                                "requirement_posture": "required",
                                "materiality": "material",
                                "partial_answer_policy": ("qualify_visible_gap"),
                                "mandatory_caveats": ["Premise C is limited to the signed condition."],
                                "source_obligation_specification": {
                                    "candidate_id": ("obligation:searched_premise_c"),
                                    "obligation_kind": "supporting_fact",
                                    "strictness": "required",
                                },
                                "necessity_rationale": (
                                    "The accepted filing-route target cannot be fulfilled without premise C."
                                ),
                                "why_current_premises_insufficient": (
                                    "Premise D identifies eligibility but does not establish the filing condition."
                                ),
                                "searchability_material_need_posture": ("material_and_searchable"),
                                "recovery_generation": {
                                    "parent_ref": "initial-searchos-state",
                                    "depth": 1,
                                },
                                "assumptions": [],
                                "caveats": ["Premise C remains direct-source bounded."],
                                "prohibited_upgrades": ["Do not infer premise C from the search direction."],
                            }
                        ],
                    }
                )
            if system_prompt == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT:
                recovered = dict(payload["current_recovered_component_ref"])
                target = self._component_by_id(payload, "target_E")
                premise_refs = sorted(
                    [
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
                        if node.get("component_id") in {"premise_D", recovered["component_id"]}
                    ],
                    key=safe_packet_digest,
                )
                return json.dumps(
                    {
                        "synthesis_proposals": [
                            {
                                "synthesis_key": "target_E",
                                "claim_text": UNIQUE_RECOVERED_RESULT,
                                "relationship_type": ("conditional_filing_route"),
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
                                "current_admitted_premise_node_refs": (premise_refs),
                                "relationship_type": ("conditional_filing_route"),
                                "proposed_conclusion": (UNIQUE_RECOVERED_RESULT),
                                "support_kind": "inferred",
                                "proposed_semantic_inference_depth": 1,
                                "current_graph_ref": payload["graph_ref"],
                                "existing_specialist_handoff_refs": [],
                                "assumptions": [],
                                "caveats": ["The result is an admitted inference."],
                                "prohibited_upgrades": ["Do not say either premise source directly states E."],
                            }
                        ],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SYNTHESIS_DPRIME]:
                return json.dumps(
                    {
                        "validation_status": "supported",
                        "reasons": ["The exact current inputs support the bounded proposal."],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER]:
                return json.dumps(
                    {
                        "challenge_status": "passed",
                        "reasons": ["The bounded case preserves exact premise lineage."],
                        "challenge_targets": [],
                        "caveats": [],
                        "nonclaims": [],
                    }
                )
        return super().ask_model(prompt, system_prompt, **kwargs)


SERIAL_E_RESULT = "BOUNDARY_B_DEEP_SERIAL_E_RESULT_41C8"
SERIAL_F_RESULT = "BOUNDARY_B_DEEP_SERIAL_F_RESULT_92B6"


class _DeepSerialBoundaryBPlanner(_BoundaryBPlanner):
    def produce(
        self,
        planner_input: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        payload = deepcopy(dict(super().produce(planner_input)))
        payload["answer_components"].append(
            {
                "component_id": "target_F",
                "component_revision": "1",
                "component_purpose": "user_facing_answer_target",
                "user_facing_label": "Governed reporting route F",
                "user_facing_question": ("Which Alder reporting route follows?"),
                "requirement_posture": "required",
                "acceptance_criteria": ["Use only an admitted relationship over current premises."],
                "semantic_slot_ids": ["slot:alder"],
                "source_obligation_candidate_ids": [],
                "allowed_support_kinds": ["inferred"],
                "max_inference_depth": 2,
                "dependency_component_ids": ["premise_D"],
                "materiality": "material",
                "partial_answer_policy": "qualify_visible_gap",
            }
        )
        payload["relationship_hypotheses"].append(
            {
                "local_hypothesis_key": "target_F",
                "relationship_type": "conditional_reporting_route",
                "component_inputs": ["premise_D"],
                "proposal_only": True,
            }
        )
        payload["question_meaning_summary"] = (
            "Answer targets E and F through two serial, directly sourced premise generations."
        )
        payload["requested_synthesis_directive"] = "Determine target_E and target_F from their exact admitted premises."
        return payload


class DeepSerialBoundaryBOrdinaryHarness(BoundaryBOrdinaryHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.query = (
            "For the fictional Alder Deep rule, determine filing route E "
            "and reporting route F through any necessary serial premises."
        )
        self.raw_author_response = f"{SERIAL_E_RESULT}. {SERIAL_F_RESULT}."
        self.selective_cross_calls = 0
        self.followup_queries: list[tuple[str, str]] = []

    def deps(self):
        return replace(
            super().deps(),
            search_planner_adapter=_DeepSerialBoundaryBPlanner(),
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        if len(self.search_calls) <= 1:
            return super().build_search_passages()
        if len(self.search_calls) == 2:
            return [
                {
                    "source_id": 822,
                    "title": "Alder direct searched premise C",
                    "url": "https://alder.example/deep-premise-c",
                    "text": ("The Alder rule directly establishes searched premise C."),
                    "score": 1.0,
                    "credibility": 4,
                    "source_tier": "official",
                    "source_class": "supporting_fact",
                    "currentness_signal": "current",
                    "readable_status": "readable",
                    "disposition": "accepted",
                    "query_ref": "Alder missing filing condition premise C",
                    "_provider": "offline_fake_search",
                }
            ]
        return [
            {
                "source_id": 823,
                "title": "Alder direct searched grandchild premise B",
                "url": "https://alder.example/deep-premise-b",
                "text": ("The Alder rule directly establishes searched grandchild premise B."),
                "score": 1.0,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "supporting_fact",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "query_ref": "Alder missing reporting condition premise B",
                "_provider": "offline_fake_search",
            }
        ]

    @staticmethod
    def _searched_candidate(
        *,
        target: Mapping[str, Any],
        dependency_refs: list[dict[str, Any]],
        premise_key: str,
        depth: int,
        parent_ref: str,
    ) -> dict[str, Any]:
        label = "Alder grandchild reporting premise B" if premise_key == "B" else "Alder signed-condition premise C"
        question = (
            "Which signed Alder reporting condition establishes grandchild premise B?"
            if premise_key == "B"
            else "Which signed Alder filing condition establishes premise C?"
        )
        return {
            "classification": "searched_premise",
            "local_proposal_key": (f"recover_premise_{premise_key}_generation_{depth}"),
            "local_target_key": str(target["component_id"]),
            "normalized_premise_identity": (f"alder searched premise {premise_key.casefold()} generation {depth}"),
            "answer_target_refs": [dict(target)],
            "parent_component_refs": [dict(target)],
            "current_dependency_component_refs": sorted(
                dependency_refs,
                key=safe_packet_digest,
            ),
            "premise_semantics": (f"Alder directly sourced premise {premise_key} at generation {depth}"),
            "user_facing_label": label,
            "user_facing_question": question,
            "acceptance_criteria": [f"Use the exact signed Alder premise {premise_key} record."],
            "requirement_posture": "required",
            "materiality": "material",
            "partial_answer_policy": "qualify_visible_gap",
            "mandatory_caveats": [f"Premise {premise_key} remains direct-source bounded."],
            "source_obligation_specification": {
                "candidate_id": (f"obligation:searched_premise_{premise_key.casefold()}"),
                "obligation_kind": "supporting_fact",
                "strictness": "required",
            },
            "necessity_rationale": (f"The accepted target requires direct premise {premise_key}."),
            "why_current_premises_insufficient": (
                f"The current graph does not directly establish premise {premise_key}."
            ),
            "searchability_material_need_posture": ("material_and_searchable"),
            "recovery_generation": {
                "parent_ref": parent_ref,
                "depth": depth,
            },
            "assumptions": [],
            "caveats": [],
            "prohibited_upgrades": [f"Do not infer premise {premise_key} from the search direction."],
        }

    @staticmethod
    def _inferred_candidate(
        *,
        payload: Mapping[str, Any],
        target: Mapping[str, Any],
        recovered: Mapping[str, Any],
        result: str,
        local_key: str,
    ) -> dict[str, Any]:
        premise_refs = sorted(
            [
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
                    *payload.get(
                        "licensed_current_component_refs",
                        [],
                    ),
                    recovered,
                ]
                if node.get("component_id") in {"premise_D", recovered.get("component_id")}
            ],
            key=safe_packet_digest,
        )
        return {
            "classification": "inferred_conclusion",
            "local_proposal_key": local_key,
            "local_target_key": str(target["component_id"]),
            "answer_target_ref": dict(target),
            "current_admitted_premise_node_refs": premise_refs,
            "relationship_type": "bounded_serial_rule",
            "proposed_conclusion": result,
            "support_kind": "inferred",
            "proposed_semantic_inference_depth": 1,
            "current_graph_ref": dict(payload["graph_ref"]),
            "existing_specialist_handoff_refs": [],
            "assumptions": [],
            "caveats": ["The result is admitted inference."],
            "prohibited_upgrades": ["Do not state that either source directly asserts the target."],
        }

    def ask_model(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if system_prompt.startswith(SEARCHOS_JUDGMENT_SYSTEM_PROMPT):
            payload = json.loads(prompt)
            authorized = dict(payload.get("authorized_request") or payload)
            cycle_id = str(dict(authorized.get("slot_ref") or {}).get("recovery_cycle_id") or "")
            prior_for_cycle = [item for item in self.read_assessment_calls if item.get("recovery_cycle_id") == cycle_id]
            if cycle_id and not prior_for_cycle:
                prior_cycle_ids = {
                    str(item.get("recovery_cycle_id") or "")
                    for item in self.read_assessment_calls
                    if item.get("recovery_cycle_id")
                }
                cycle_number = len(prior_cycle_ids) + 1
                retained = [item for item in self.read_assessment_calls if not item.get("recovery_cycle_id")]
                retained_count = len(retained)
                prior = self.read_assessment_calls
                self.read_assessment_calls = retained
                try:
                    result = super().ask_model(
                        prompt,
                        system_prompt,
                        **kwargs,
                    )
                    newly_recorded = self.read_assessment_calls[retained_count:]
                finally:
                    self.read_assessment_calls = prior
                self.read_assessment_calls.extend(newly_recorded)
                decision = json.loads(result)
                if decision.get("action") == "PROPOSE_FOLLOWUP_QUERY":
                    decision["followup_query"] = {
                        1: "ZXQ41C8 signed filing predicate record",
                        2: "QVB92B6 reporting trigger document",
                    }[cycle_number]
                    self.followup_queries.append((cycle_id, decision["followup_query"]))
                return json.dumps(decision)
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            payload = json.loads(prompt)
            self.role_packets.append({"system_prompt": system_prompt, "payload": payload})
            self._record_model_call(system_prompt, kwargs)
            target_e = self._component_by_id(payload, "target_E")
            premise_d = self._component_by_id(payload, "premise_D")
            return json.dumps(
                {
                    "synthesis_proposals": [
                        {
                            "synthesis_key": "target_E",
                            "claim_text": ("Target E awaits direct searched premise C."),
                            "relationship_type": "bounded_serial_rule",
                            "component_inputs": ["premise_D"],
                            "synthesis_inputs": [],
                            "caveats": [],
                            "nonclaims": [],
                            "blockers": [],
                        },
                        {
                            "synthesis_key": "target_F",
                            "claim_text": ("Target F awaits a later direct premise."),
                            "relationship_type": "bounded_serial_rule",
                            "component_inputs": ["premise_D"],
                            "synthesis_inputs": [],
                            "caveats": [],
                            "nonclaims": [],
                            "blockers": [],
                        },
                    ],
                    "query_resolution_proposals": [
                        self._searched_candidate(
                            target=target_e,
                            dependency_refs=[premise_d],
                            premise_key="C",
                            depth=1,
                            parent_ref="initial-searchos-state",
                        )
                    ],
                }
            )
        if system_prompt == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT:
            payload = json.loads(prompt)
            self.role_packets.append({"system_prompt": system_prompt, "payload": payload})
            self._record_model_call(system_prompt, kwargs)
            self.selective_cross_calls += 1
            recovered = dict(payload["current_recovered_component_ref"])
            premise_d = self._component_by_id(payload, "premise_D")
            graph_ref = dict(payload["graph_ref"])
            if self.selective_cross_calls == 1:
                target = self._component_by_id(payload, "target_E")
                next_target = self._component_by_id(
                    payload,
                    "target_F",
                )
                return json.dumps(
                    {
                        "synthesis_proposals": [
                            {
                                "synthesis_key": "target_E",
                                "claim_text": SERIAL_E_RESULT,
                                "relationship_type": ("bounded_serial_rule"),
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
                            self._inferred_candidate(
                                payload=payload,
                                target=target,
                                recovered=recovered,
                                result=SERIAL_E_RESULT,
                                local_key="infer_serial_target_E",
                            ),
                            self._searched_candidate(
                                target=next_target,
                                dependency_refs=[premise_d],
                                premise_key="B",
                                depth=2,
                                parent_ref=str(graph_ref["graph_digest"]),
                            ),
                        ],
                    }
                )
            target = self._component_by_id(payload, "target_F")
            generation_three_target = self._component_by_id(
                payload,
                "target_E",
            )
            return json.dumps(
                {
                    "synthesis_proposals": [
                        {
                            "synthesis_key": "target_F",
                            "claim_text": SERIAL_F_RESULT,
                            "relationship_type": "bounded_serial_rule",
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
                        self._inferred_candidate(
                            payload=payload,
                            target=target,
                            recovered=recovered,
                            result=SERIAL_F_RESULT,
                            local_key="infer_serial_target_F",
                        ),
                        self._searched_candidate(
                            target=generation_three_target,
                            dependency_refs=[premise_d],
                            premise_key="G",
                            depth=3,
                            parent_ref=str(graph_ref["graph_digest"]),
                        ),
                    ],
                }
            )
        return super().ask_model(prompt, system_prompt, **kwargs)


class _FastInferencePlanner:
    def produce(self, _planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        components = []
        obligations = []
        requirements = []
        strategies = []
        for component_id in ("premise_a", "premise_b"):
            obligation_id = f"obligation:{component_id}"
            query_text = f"Alder direct {component_id}"
            components.append(
                {
                    "component_id": component_id,
                    "component_revision": "1",
                    "component_purpose": "supporting_premise",
                    "user_facing_label": f"Direct {component_id}",
                    "user_facing_question": (f"What directly establishes {component_id}?"),
                    "requirement_posture": "required",
                    "acceptance_criteria": ["Use one exact current direct source."],
                    "semantic_slot_ids": ["slot:alder-fast"],
                    "source_obligation_candidate_ids": [obligation_id],
                    "allowed_support_kinds": ["direct"],
                    "max_inference_depth": 0,
                    "materiality": "material",
                    "partial_answer_policy": "qualify_visible_gap",
                }
            )
            obligations.append(
                {
                    "candidate_id": obligation_id,
                    "obligation_kind": "supporting_fact",
                    "component_candidate_ids": [component_id],
                    "strictness": "required",
                    "metadata": {"provider_name_neutral": True},
                }
            )
            strategy = {
                "strategy_id": f"strategy:{component_id}:primary:1",
                "component_id": component_id,
                "candidate_kind": "primary",
                "candidate_query_text": query_text,
                "requested_role": "initial",
                "source_obligation_candidate_ids": [obligation_id],
                "domain_constraints": {"include": [], "exclude": []},
                "distinct_need_justification": (f"Directly establish {component_id}."),
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
            strategies.append(strategy)
            requirements.append(
                {
                    "component_id": component_id,
                    "requirement_id": (f"search-requirement:{component_id}:initial"),
                    "requirement_summary": (f"Find direct support for {component_id}."),
                    "source_obligation_candidate_ids": [obligation_id],
                    "preferred_source_kinds": ["supporting_fact"],
                    "metadata": {
                        "query_strategy_candidates": [strategy],
                        "provider_name_neutral": True,
                    },
                }
            )
        components.append(
            {
                "component_id": "target_E",
                "component_revision": "1",
                "component_purpose": "user_facing_answer_target",
                "user_facing_label": "Fast inferred target E",
                "user_facing_question": ("What follows jointly from premises A and B?"),
                "requirement_posture": "required",
                "acceptance_criteria": ["Use only the admitted bounded relationship."],
                "semantic_slot_ids": ["slot:alder-fast"],
                "source_obligation_candidate_ids": [],
                "allowed_support_kinds": ["inferred"],
                "max_inference_depth": 1,
                "dependency_component_ids": [
                    "premise_a",
                    "premise_b",
                ],
                "materiality": "material",
                "partial_answer_policy": "qualify_visible_gap",
            }
        )
        return {
            "question_meaning_summary": ("Infer target E from direct premises A and B."),
            "requested_output": "Return the governed Fast target E.",
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": ("Infer target_E from exact admitted premises A and B."),
            "semantic_slots": [
                {
                    "slot_id": "slot:alder-fast",
                    "slot_kind": "entity",
                    "status": "explicit",
                    "candidate_values": ["Alder"],
                    "selected_value": "Alder",
                    "materiality": "material",
                    "user_confirmation_required": False,
                }
            ],
            "answer_components": components,
            "source_obligation_candidates": obligations,
            "component_search_requirements": requirements,
            "relationship_hypotheses": [
                {
                    "local_hypothesis_key": "target_E",
                    "relationship_type": "bounded_conjunction",
                    "component_inputs": ["premise_a", "premise_b"],
                    "proposal_only": True,
                }
            ],
            "material_ambiguity_posture": "none_detected",
            "mandatory_caveats": [],
            "prohibited_upgrades": ["Do not treat the planning hypothesis as admitted inference."],
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


FAST_INFERRED_RESULT = "BOUNDARY_B_FAST_INFERRED_E_RESULT_2A91"


class FastInferenceOrdinaryHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=("For the fictional Alder Fast rule, what target E follows jointly from direct premises A and B?"),
            core_topic="Alder Fast rule",
            primary_entity="Alder",
            researcher_queries=(
                "Alder direct premise_a",
                "Alder direct premise_b",
            ),
            raw_author_response=FAST_INFERRED_RESULT,
            logger_name="test_boundary_b_fast_inference",
        )

    def deps(self):
        return replace(
            super().deps(),
            search_planner_adapter=_FastInferencePlanner(),
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": 811,
                "title": "Alder direct premise A",
                "url": "https://alder.example/fast-premise-a",
                "text": "The Alder rule directly establishes premise A.",
                "score": 1.0,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "supporting_fact",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "query_ref": "Alder direct premise_a",
                "_provider": "offline_fake_search",
            },
            {
                "source_id": 812,
                "title": "Alder direct premise B",
                "url": "https://alder.example/fast-premise-b",
                "text": "The Alder rule directly establishes premise B.",
                "score": 1.0,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "supporting_fact",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "query_ref": "Alder direct premise_b",
                "_provider": "offline_fake_search",
            },
        ]

    def ask_model(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if system_prompt in ROLE_SYSTEM_PROMPTS.values():
            payload = json.loads(prompt)
            self._record_model_call(system_prompt, kwargs)
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
                component_id = str(payload["component_ref"]["component_id"])
                return json.dumps(
                    {
                        "claim_text": (f"Direct {component_id} is established."),
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
                        "reasons": ["Exact direct support is current."],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
                target = BoundaryBOrdinaryHarness._component_by_id(
                    payload,
                    "target_E",
                )
                premise_refs = sorted(
                    [
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
                        for node in payload["component_nodes"]
                        if node.get("component_id") in {"premise_a", "premise_b"}
                    ],
                    key=safe_packet_digest,
                )
                return json.dumps(
                    {
                        "synthesis_proposals": [
                            {
                                "synthesis_key": "target_E",
                                "claim_text": FAST_INFERRED_RESULT,
                                "relationship_type": "bounded_conjunction",
                                "component_inputs": [
                                    "premise_a",
                                    "premise_b",
                                ],
                                "synthesis_inputs": [],
                                "caveats": [],
                                "nonclaims": [],
                                "blockers": [],
                            }
                        ],
                        "query_resolution_proposals": [
                            {
                                "classification": "inferred_conclusion",
                                "local_proposal_key": "infer_fast_target_E",
                                "local_target_key": "target_E",
                                "answer_target_ref": target,
                                "current_admitted_premise_node_refs": (premise_refs),
                                "relationship_type": ("bounded_conjunction"),
                                "proposed_conclusion": (FAST_INFERRED_RESULT),
                                "support_kind": "inferred",
                                "proposed_semantic_inference_depth": 1,
                                "current_graph_ref": {},
                                "existing_specialist_handoff_refs": [],
                                "assumptions": [],
                                "caveats": ["The result is admitted inference."],
                                "prohibited_upgrades": ["Do not state that either source directly asserts target E."],
                            }
                        ],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SYNTHESIS_DPRIME]:
                return json.dumps(
                    {
                        "validation_status": "supported",
                        "reasons": ["The exact premises support the bounded inference."],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER]:
                return json.dumps(
                    {
                        "challenge_status": "passed",
                        "reasons": ["The depth-one inference preserves exact lineage."],
                        "challenge_targets": [],
                        "caveats": [],
                        "nonclaims": [],
                    }
                )
        return super().ask_model(prompt, system_prompt, **kwargs)


def test_deep_serial_generations_run_through_one_ordinary_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_legacy(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("retired legacy derived-recovery path was invoked")

    monkeypatch.setattr(runtime, "_execute_fresh_resynthesis", no_legacy)
    harness = DeepSerialBoundaryBOrdinaryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    config = replace(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-25",
            session_id="boundary-b-deep-serial-request",
            run_id="boundary-b-deep-serial-run",
            smart_search_judgment_model=True,
        ),
        mode="Deep",
    )
    outcome = orchestrator.run_pipeline(
        config,
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    kernel = captured["run_kernel"]
    admissions = deepcopy(kernel.state.searchos_state["recovery_cycle_admission_history"])
    terminals = deepcopy(kernel.state.searchos_state["recovery_cycle_terminal_history"])
    amendment_admissions = deepcopy(kernel.state.contract_amendment_admission_history)
    amendment_applications = deepcopy(kernel.state.contract_amendment_application_history)
    graph = deepcopy(kernel.state.projections["multicomponent_component_work_graph_v1"])
    registry = deepcopy(kernel.state.projections["analyst_query_resolution_proposal"])
    searched = sorted(
        [item for item in registry["proposals"] if item["classification"] == "searched_premise"],
        key=lambda item: int(item["variant_payload"]["recovery_generation"]["depth"]),
    )
    lifecycle = registry["proposal_lifecycle"]

    assert [item["generation_depth"] for item in admissions] == [1, 2], (
        [
            (
                item["terminal_status"],
                item.get("terminal_interpretation"),
                item.get("terminal_reason"),
            )
            for item in terminals
        ],
        [
            (
                item["variant_payload"]["recovery_generation"]["depth"],
                lifecycle[item["proposal_id"]]["status"],
                lifecycle[item["proposal_id"]].get("reason"),
            )
            for item in searched
        ],
        harness.selective_cross_calls,
        len(harness.search_calls),
        harness.followup_queries,
    )
    assert len(terminals) == 2
    assert all(item["terminal_status"] == "recovered" for item in terminals), (
        [
            (
                item["terminal_status"],
                item.get("terminal_interpretation"),
                item.get("terminal_reason"),
            )
            for item in terminals
        ],
        kernel.state.projections.get("searchos_slice_a", {}).get("existing_gap_recovery"),
        [item.get("query") for item in harness.search_calls],
    )
    lease_refs = {
        (
            item["whole_run_lease_ref"]["recovery_lease_id"],
            item["whole_run_lease_ref"]["recovery_lease_digest"],
        )
        for item in admissions
    }
    assert len(lease_refs) == 1
    assert len(kernel.state.searchos_state["recovery_lease_history"]) == 1
    assert len(amendment_admissions) == len(amendment_applications) == 2
    assert len(searched) == 3
    assert lifecycle[searched[0]["proposal_id"]]["status"] == "consumed"
    assert lifecycle[searched[1]["proposal_id"]]["status"] == "consumed"
    assert lifecycle[searched[2]["proposal_id"]]["status"] == "rejected"
    assert [
        item["status"]
        for item in registry["proposal_lifecycle_history"]
        if item["proposal_id"] == searched[1]["proposal_id"]
    ] == ["pending", "consumed", "consumed"]
    assert "generation 3" in str(lifecycle[searched[2]["proposal_id"]]["reason"])
    assert lifecycle[searched[0]["proposal_id"]]["downstream_refs"]["graph_reproof_ref"]["graph_digest"]
    assert (
        lifecycle[searched[1]["proposal_id"]]["downstream_refs"]["graph_reproof_ref"]["graph_digest"]
        == graph["graph_digest"]
    )

    searched_component_nodes = [
        item for item in graph["component_nodes"] if str(item["component_id"]).startswith("component:searched-premise:")
    ]
    assert len(searched_component_nodes) == 2
    assert all(item["component_coverage_ref"]["coverage_state"] == "satisfied" for item in searched_component_nodes)
    assert graph["selective_recomputation_rounds"] == 1
    assert len(kernel.state.projections["multicomponent_selective_recomputation_closure_history"]["closures"]) == 2
    assert graph["graph_status"] == "ready"
    fulfillments = {
        item["component_id"]: item
        for item in captured["sufficiency_projection"]["multicomponent_graph_consumption"]["answer_target_fulfillments"]
    }
    assert fulfillments["target_E"]["fulfillment_status"] == ("fulfilled_inferred")
    assert fulfillments["target_F"]["fulfillment_status"] == ("fulfilled_inferred")
    aggregate = kernel.state.searchos_state["recovery_terminal_aggregate"]
    assert aggregate["posture"] == "settled"
    assert aggregate["settled_interpretation"] == "recovery_completed"
    assert aggregate["admission_count"] == aggregate["terminal_count"] == 2
    assert len(harness.search_calls) == 3
    assert harness.selective_cross_calls == 2
    assert len(harness.author_prompts) == 1
    assert captured["author_handoff_called"] is True
    assert SERIAL_E_RESULT in outcome.report
    assert SERIAL_F_RESULT in outcome.report
    assert not any(
        "_begin_scheduler_dynamic_recovery" in str(item) or "_attempt_dynamic_recovery" in str(item)
        for item in kernel.state.projections
    )

    mutation_counts_before_replay = {
        "issued_actions": len(kernel.state.issued_actions),
        "observations": len(kernel.state.observations),
        "amendment_admissions": len(kernel.state.contract_amendment_admission_history),
        "amendment_applications": len(kernel.state.contract_amendment_application_history),
        "recovery_admissions": len(kernel.state.searchos_state["recovery_cycle_admission_history"]),
        "recovery_terminals": len(kernel.state.searchos_state["recovery_cycle_terminal_history"]),
        "graph_digest": graph["graph_digest"],
        "author_calls": len(harness.author_prompts),
        "search_calls": len(harness.search_calls),
    }
    first_downstream = deepcopy(lifecycle[searched[0]["proposal_id"]]["downstream_refs"])
    replay = runtime.authorize_searched_premise_recovery_from_analyst_proposals(
        run_kernel=kernel,
        requested_mode="Deep",
        proposal_ref={
            key: searched[0][key]
            for key in (
                "proposal_id",
                "proposal_digest",
                "stable_replay_key",
            )
        },
    )
    assert replay["status"] == "exact_replay"
    assert replay["work_authorized"] is False
    assert replay["downstream_refs"] == first_downstream
    assert kernel.state.contract_amendment_admission_history == (amendment_admissions)
    assert kernel.state.contract_amendment_application_history == (amendment_applications)
    assert kernel.state.searchos_state["recovery_cycle_admission_history"] == admissions
    assert kernel.state.searchos_state["recovery_cycle_terminal_history"] == terminals
    assert {
        "issued_actions": len(kernel.state.issued_actions),
        "observations": len(kernel.state.observations),
        "amendment_admissions": len(kernel.state.contract_amendment_admission_history),
        "amendment_applications": len(kernel.state.contract_amendment_application_history),
        "recovery_admissions": len(kernel.state.searchos_state["recovery_cycle_admission_history"]),
        "recovery_terminals": len(kernel.state.searchos_state["recovery_cycle_terminal_history"]),
        "graph_digest": kernel.state.projections["multicomponent_component_work_graph_v1"]["graph_digest"],
        "author_calls": len(harness.author_prompts),
        "search_calls": len(harness.search_calls),
    } == mutation_counts_before_replay


def test_fast_depth_one_inference_reaches_one_author_without_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_legacy(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("retired derived-recovery path was invoked")

    monkeypatch.setattr(runtime, "_execute_fresh_resynthesis", no_legacy)
    harness = FastInferenceOrdinaryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    config = replace(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-25",
            session_id="boundary-b-fast-request",
            run_id="boundary-b-fast-run",
        ),
        mode="Fast",
    )
    outcome = orchestrator.run_pipeline(
        config,
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    kernel = captured["run_kernel"]
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    target = next(
        item
        for item in captured["sufficiency_projection"]["multicomponent_graph_consumption"]["answer_target_fulfillments"]
        if item["component_id"] == "target_E"
    )
    assert target["fulfillment_status"] == "fulfilled_inferred"
    assert target["selected_support_kind"] == "inferred"
    inferred = target["inferred_fulfillment_ref"]
    assert inferred["semantic_inference_depth"] == 1
    assert {item["component_id"] for item in inferred["premise_node_refs"]} == {"premise_a", "premise_b"}
    assert not kernel.state.contract_amendment_admission_history
    assert not kernel.state.contract_amendment_application_history
    assert kernel.state.searchos_state.get("recovery_cycle_admission_history") in (None, [])
    assert kernel.state.searchos_state.get("recovery_cycle_terminal_history") in (None, [])
    assert not kernel.state.searchos_state.get("recovery_lease")
    assert graph["semantic_inference_profile"]["profile_ceiling"] == 1
    assert captured["sufficiency_projection"]["final_answer_posture"] == ("sufficient_with_admitted_inference")
    packet = captured["packet_handoff"].packet
    assert not any(dict(item).get("component_id") == "target_E" for item in packet.direct_component_entries)
    assert any(
        dict(item).get("answer_target_component_id") == "target_E" and dict(item).get("support_kind") == "inferred"
        for item in packet.admitted_synthesis_entries
    )
    assert len(harness.author_prompts) == 1
    assert captured["author_handoff_called"] is True
    assert FAST_INFERRED_RESULT in outcome.report


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
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    lease = kernel.state.searchos_state["recovery_lease"]
    admissions = kernel.state.searchos_state["recovery_cycle_admission_history"]
    terminals = kernel.state.searchos_state["recovery_cycle_terminal_history"]
    target = next(
        item
        for item in captured["sufficiency_projection"]["multicomponent_graph_consumption"]["answer_target_fulfillments"]
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
    assert admissions[0]["whole_run_lease_ref"]["recovery_lease_id"] == lease["recovery_lease_id"]
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
    recovered_candidates = [item for item in graph["component_nodes"] if item["component_id"] != "premise_D"]
    assert recovered_candidates, (
        terminals,
        graph,
        outcome.failure_card,
    )
    recovered = recovered_candidates[0]
    assert recovered["semantic_inference_depth"] == 0
    assert recovered["component_coverage_ref"]["coverage_state"] == ("satisfied")
    recovered_contract_component = next(
        item
        for item in kernel.state.current_answer_contract["accepted_answer_component_refs"]
        if item["component_id"] == recovered["component_id"]
    )
    assert recovered_contract_component["user_facing_label"] == ("Alder signed-condition premise C")
    assert recovered_contract_component["user_facing_question"] == (
        "Which signed Alder filing condition establishes premise C?"
    )
    assert recovered_contract_component["acceptance_criteria"] == [
        "Use the exact signed Alder filing-condition record."
    ]
    assert recovered_contract_component["mandatory_caveats"] == ["Premise C is limited to the signed condition."]
    assert recovered["accepted_component_ref"] == (recovered_contract_component)
    initial_target = next(
        item
        for item in kernel.state.initial_answer_contract["accepted_answer_component_refs"]
        if item["component_id"] == "target_E"
    )
    amended_target = next(
        item
        for item in kernel.state.current_answer_contract["accepted_answer_component_refs"]
        if item["component_id"] == "target_E"
    )
    assert amended_target["allowed_support_kinds"] == (initial_target["allowed_support_kinds"])
    assert amended_target["max_inference_depth"] == (initial_target["max_inference_depth"])
    assert target["selected_support_kind"] == "inferred"
    assert target["fulfillment_status"] == "fulfilled_inferred"
    inferred_fulfillment = target["inferred_fulfillment_ref"]
    assert inferred_fulfillment["semantic_inference_depth"] == 1
    assert {item["component_id"] for item in inferred_fulfillment["premise_node_refs"]} == {
        "premise_D",
        recovered["component_id"],
    }
    assert graph["selective_recomputation_rounds"] == 1
    assert graph["graph_status"] == "ready"
    registry = kernel.state.projections["analyst_query_resolution_proposal"]
    searched_proposal = next(item for item in registry["proposals"] if item["classification"] == "searched_premise")
    lifecycle = registry["proposal_lifecycle"][searched_proposal["proposal_id"]]
    assert lifecycle["status"] == "consumed"
    assert lifecycle["downstream_refs"]["graph_reproof_ref"]["graph_digest"] == graph["graph_digest"]
    assert kernel.state.searchos_state["recovery_terminal_aggregate"]["posture"] == "settled"
    assert kernel.state.searchos_state["recovery_terminal_aggregate"]["settled_interpretation"] == "recovery_completed"
    assert captured["sufficiency_projection"]["decision"] == ("ready_with_admitted_inference")
    assert captured["sufficiency_projection"]["final_answer_posture"] == ("sufficient_with_admitted_inference")
    packet = captured["packet_handoff"].packet
    inferred_entries = [
        dict(item) for item in packet.admitted_synthesis_entries if dict(item).get("support_kind") == "inferred"
    ]
    assert inferred_entries
    assert inferred_entries[0]["answer_target_component_id"] == "target_E"
    assert not any(dict(item).get("component_id") == "target_E" for item in packet.direct_component_entries)
    assert UNIQUE_RECOVERED_RESULT in captured["packet_handoff"].author_payload.prompt
    assert UNIQUE_RECOVERED_RESULT in outcome.report
    assert len(harness.author_prompts) == 1
    assert captured["author_handoff_called"] is True
    assert not any(
        "_begin_scheduler_dynamic_recovery" in str(item) or "_attempt_dynamic_recovery" in str(item)
        for item in kernel.state.projections
    )

    admission = deepcopy(kernel.state.contract_amendment_admission_history[0])
    application = deepcopy(kernel.state.contract_amendment_application_history[0])
    mutation_counts_before = {
        "issued_actions": len(kernel.state.issued_actions),
        "observations": len(kernel.state.observations),
        "amendment_admissions": len(kernel.state.contract_amendment_admission_history),
        "amendment_applications": len(kernel.state.contract_amendment_application_history),
        "recovery_admissions": len(admissions),
        "recovery_terminals": len(terminals),
        "author_calls": len(harness.author_prompts),
    }
    graph_before_replay = deepcopy(graph)
    searchos_before_replay = deepcopy(kernel.state.searchos_state)

    replay = runtime.authorize_searched_premise_recovery_from_analyst_proposals(
        run_kernel=kernel,
        requested_mode="Balanced",
    )
    admission_replay = kernel.authorize_contract_amendment_admission(
        amendment_record_id=str(admission["amendment_record_id"]),
        amendment_record_digest=str(admission["amendment_record_digest"]),
        parent_contract_digest=str(admission["parent_contract_digest"]),
        parent_contract_version=str(admission["parent_contract_version"]),
    )
    application_replay = kernel.authorize_contract_amendment_application(
        amendment_record_id=str(application["amendment_record_id"]),
        amendment_record_digest=str(application["amendment_record_digest"]),
        admission_digest=str(application["admission_digest"]),
        parent_contract_digest=str(application["parent_contract_digest"]),
        parent_contract_version=str(application["parent_contract_version"]),
    )

    assert replay["status"] == "exact_replay"
    assert replay["work_authorized"] is False
    assert replay["contract_amendment_record"]["schema_version"] == ("contract_amendment_record_v2")
    assert replay["contract_amendment_admission"] == admission
    assert replay["contract_amendment_application"] == application
    assert (
        replay["new_contract_ref"]["accepted_contract_digest"]
        == (kernel.state.current_answer_contract["accepted_contract_digest"])
    )
    assert replay["graph_transition_ref"]["authorization_digest"]
    assert replay["graph_transition_ref"]["closure_ref"]["closure_digest"]
    replay_without_proposal = {key: value for key, value in replay.items() if key != "proposal"}
    assert admission_replay == replay_without_proposal
    assert application_replay == replay_without_proposal
    assert {
        "issued_actions": len(kernel.state.issued_actions),
        "observations": len(kernel.state.observations),
        "amendment_admissions": len(kernel.state.contract_amendment_admission_history),
        "amendment_applications": len(kernel.state.contract_amendment_application_history),
        "recovery_admissions": len(kernel.state.searchos_state["recovery_cycle_admission_history"]),
        "recovery_terminals": len(kernel.state.searchos_state["recovery_cycle_terminal_history"]),
        "author_calls": len(harness.author_prompts),
    } == mutation_counts_before
    assert kernel.state.projections["multicomponent_component_work_graph_v1"] == graph_before_replay
    assert kernel.state.searchos_state == searchos_before_replay
