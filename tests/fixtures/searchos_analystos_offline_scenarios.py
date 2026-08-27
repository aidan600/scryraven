"""Reusable deterministic corpus for the SearchOS/AnalystOS offline gate.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded: ``core.pipeline_orchestrator.run_pipeline``.
The fake responses stop at installed model/transport boundaries. Canonical
proposal binding, amendment, recovery, graph, Sufficiency, FAP, and Author
state are produced only by the ordinary product path.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import core.pipeline_orchestrator as orchestrator
from core.analyst_query_resolution_proposal import (
    _digest as _proposal_ref_digest,
)
from core.analyst_query_resolution_proposal import (
    _safe as _proposal_safe,
)
from core.cost_accounting import CostAccumulator
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_ANALYST_RESUME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT,
    safe_packet_digest,
)
from core.protocols import NullStatusWriter
from core.searchos_slice_a_product_runtime import SEARCHOS_JUDGMENT_SYSTEM_PROMPT
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

CASE_1 = "case_01_direct_control"
CASE_2 = "case_02_one_searched_premise"
CASE_3 = "case_03_pure_depth_two"
CASE_4 = "case_04_nested_serial_recovery"
CASE_5 = "case_05_late_sibling_requirements"
CASE_6 = "case_06_root_query_retention"
CASE_7 = "case_07_honest_nonclosure"

PASS = "PASS"
BOUNDED_LIMIT = "BOUNDED LIMIT"

DIRECT_RESULT = "The current Northstar bulletin directly assigns the Harbor filing route."
SEARCHED_RESULT = "The eligibility and signed-dispatch premises establish the Harbor filing route."
CLASS_RESULT = "The active certificate and registry designation establish the Northstar compliance class."
DEPTH_TWO_RESULT = "The Northstar compliance class and regional flag establish the Meridian filing route."
NESTED_CLASS_RESULT = "The active certificate and recovered registry designation establish the nested compliance class."
NESTED_RESULT = "The nested compliance class and regional flag establish the nested Meridian filing route."
FUEL_RESULT = "The period-correct Pacifica fuel price and fuel-use basis establish fuel expense per passenger-mile."
AIRCRAFT_RESULT = (
    "The fuel-expense intermediate and non-fuel expense record establish the aircraft operating-cost posture."
)


@dataclass(frozen=True)
class DirectFact:
    component_id: str
    label: str
    question: str
    query: str
    text: str


@dataclass(frozen=True)
class Target:
    component_id: str
    purpose: str
    label: str
    question: str
    max_depth: int
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class RecoveryFact:
    semantic_key: str
    label: str
    question: str
    query: str
    text: str
    url_slug: str
    correct_basis: bool = True


@dataclass(frozen=True)
class OfflineScenario:
    scenario_id: str
    mode: str
    root_query: str
    meaning: str
    direct_facts: tuple[DirectFact, ...]
    targets: tuple[Target, ...]
    recovery_generations: tuple[tuple[RecoveryFact, ...], ...]
    author_response: str
    expected_status: str = PASS
    unavailable_recovery: bool = False


def _d(
    component_id: str,
    label: str,
    question: str,
    query: str,
    text: str,
) -> DirectFact:
    return DirectFact(component_id, label, question, query, text)


def _t(
    component_id: str,
    purpose: str,
    label: str,
    question: str,
    max_depth: int,
    *dependencies: str,
) -> Target:
    return Target(
        component_id,
        purpose,
        label,
        question,
        max_depth,
        tuple(dependencies),
    )


def _r(
    semantic_key: str,
    label: str,
    question: str,
    query: str,
    text: str,
    *,
    url_slug: str | None = None,
    correct_basis: bool = True,
) -> RecoveryFact:
    return RecoveryFact(
        semantic_key,
        label,
        question,
        query,
        text,
        url_slug or semantic_key.replace("_", "-"),
        correct_basis,
    )


SCENARIOS = (
    OfflineScenario(
        CASE_1,
        "Balanced",
        "Under fictional Northstar Bulletin 26, which filing route is directly assigned to Harbor Cooperative?",
        "Identify Harbor Cooperative's directly stated current filing route.",
        (
            _d(
                "harbor_filing_route",
                "Harbor filing-route assignment",
                "Which filing route does Bulletin 26 directly assign to Harbor Cooperative?",
                "Northstar Bulletin 26 Harbor filing route",
                DIRECT_RESULT,
            ),
        ),
        (),
        (),
        DIRECT_RESULT,
    ),
    OfflineScenario(
        CASE_2,
        "Balanced",
        "For Harbor Cooperative, determine the Northstar filing route that follows from current eligibility and the required signed dispatch condition.",
        "Determine the Harbor route from eligibility and an independently recovered signed-dispatch premise.",
        (
            _d(
                "current_eligibility",
                "Harbor current eligibility",
                "What is Harbor Cooperative's current Northstar eligibility posture?",
                "Harbor Northstar current eligibility",
                "The fictional bulletin directly records Harbor as eligible.",
            ),
        ),
        (
            _t(
                "harbor_route_target",
                "user_facing_answer_target",
                "Harbor governed filing route",
                "Which filing route follows for Harbor Cooperative?",
                1,
                "current_eligibility",
            ),
        ),
        (
            (
                _r(
                    "signed_dispatch_condition",
                    "Signed Harbor dispatch condition",
                    "Which signed dispatch condition applies to Harbor Cooperative?",
                    "Harbor exact signed dispatch condition",
                    "The fictional signed record directly establishes Harbor's required dispatch condition.",
                ),
            ),
        ),
        SEARCHED_RESULT,
    ),
    OfflineScenario(
        CASE_3,
        "Deep",
        "Using the fictional Northstar certificate, registry, and regional records, determine Meridian Works' filing route.",
        "Reconstruct a compliance class from certificate and registry facts, then combine it with the regional flag.",
        (
            _d(
                "active_certificate",
                "Active Northstar certificate",
                "Is Meridian Works' Northstar certificate active?",
                "Meridian active Northstar certificate",
                "The fictional certificate directly records an active status.",
            ),
            _d(
                "registry_designation",
                "Meridian registry designation",
                "What designation does the registry assign to Meridian Works?",
                "Meridian Northstar registry designation",
                "The fictional registry directly assigns the required designation.",
            ),
            _d(
                "regional_filing_flag",
                "Meridian regional filing flag",
                "What regional filing flag applies to Meridian Works?",
                "Meridian regional filing flag",
                "The fictional regional record directly establishes the filing flag.",
            ),
        ),
        (
            _t(
                "compliance_class",
                "supporting_premise",
                "Northstar compliance class",
                "Which compliance class follows from the certificate and registry designation?",
                1,
                "active_certificate",
                "registry_designation",
            ),
            _t(
                "meridian_route_target",
                "user_facing_answer_target",
                "Meridian governed filing route",
                "Which filing route follows from the compliance class and regional flag?",
                2,
                "compliance_class",
                "regional_filing_flag",
            ),
        ),
        (),
        DEPTH_TWO_RESULT,
    ),
    OfflineScenario(
        CASE_4,
        "Deep",
        "For Meridian Works, recover any missing registry premise and determine the nested Northstar filing route from current certificate and regional records.",
        "Recover the registry designation, reconstruct the compliance class, and determine the root route.",
        (
            _d(
                "active_certificate",
                "Active nested certificate",
                "Is Meridian Works' nested Northstar certificate active?",
                "Meridian nested active certificate",
                "The fictional nested certificate directly records an active status.",
            ),
            _d(
                "regional_filing_flag",
                "Nested regional filing flag",
                "What nested regional filing flag applies to Meridian Works?",
                "Meridian nested regional filing flag",
                "The fictional nested regional record directly establishes the flag.",
            ),
        ),
        (
            _t(
                "nested_compliance_class",
                "supporting_premise",
                "Nested Northstar compliance class",
                "Which nested class follows from the certificate and registry designation?",
                1,
                "active_certificate",
            ),
            _t(
                "nested_route_target",
                "user_facing_answer_target",
                "Nested Meridian filing route",
                "Which route follows from the nested class and regional flag?",
                2,
                "nested_compliance_class",
                "regional_filing_flag",
            ),
        ),
        (
            (
                _r(
                    "registry_designation",
                    "Recovered Meridian registry designation",
                    "Which current registry designation is assigned to Meridian Works?",
                    "Meridian exact nested registry designation",
                    "The fictional signed registry directly establishes the missing designation.",
                ),
            ),
        ),
        NESTED_RESULT,
    ),
    OfflineScenario(
        CASE_5,
        "Balanced",
        "Determine Solace Freight's Northstar route when the represented record initially contains only its regional flag and requested final route.",
        "Assess two late-discovered sibling premises without branching recovery.",
        (
            _d(
                "solace_regional_flag",
                "Solace regional flag",
                "What regional flag applies to Solace Freight?",
                "Solace Northstar regional flag",
                "The fictional regional record directly establishes Solace's flag.",
            ),
        ),
        (
            _t(
                "solace_route_target",
                "user_facing_answer_target",
                "Solace governed route",
                "Which Northstar route follows for Solace Freight?",
                1,
                "solace_regional_flag",
            ),
        ),
        (
            (
                _r(
                    "solace_certificate",
                    "Solace active certificate",
                    "Is Solace Freight's current Northstar certificate active?",
                    "Solace exact current certificate",
                    "The fictional certificate directly records Solace as active.",
                ),
            ),
            (
                _r(
                    "solace_registry_designation",
                    "Solace registry designation",
                    "Which registry designation applies to Solace Freight?",
                    "Solace exact registry designation",
                    "The fictional registry directly records Solace's designation.",
                ),
            ),
        ),
        "This response must remain blocked by the bounded sibling limit.",
        BOUNDED_LIMIT,
    ),
    OfflineScenario(
        CASE_6,
        "Deep",
        "Estimate the fictional Pacifica Air 2024 operating-cost posture per passenger-mile using Pacifica-region fuel expense and non-fuel expense records.",
        "Use the 2024 Pacifica per-gallon price to establish fuel expense, then combine it with non-fuel expense for the root target.",
        (
            _d(
                "fuel_use_basis",
                "Pacifica fuel-use basis",
                "What 2024 Pacifica Air fuel-use basis applies per passenger-mile?",
                "Pacifica Air 2024 fuel use per passenger-mile",
                "The fictional 2024 Pacifica record directly establishes the fuel-use basis per passenger-mile.",
            ),
            _d(
                "nonfuel_expense_record",
                "Pacifica non-fuel expense record",
                "What 2024 Pacifica non-fuel expense posture applies per passenger-mile?",
                "Pacifica Air 2024 non-fuel expense per passenger-mile",
                "The fictional 2024 Pacifica record directly establishes non-fuel expense per passenger-mile.",
            ),
        ),
        (
            _t(
                "fuel_expense_parent",
                "supporting_premise",
                "Fuel expense per passenger-mile",
                "What fuel expense follows from the 2024 Pacifica fuel-use and price bases?",
                1,
                "fuel_use_basis",
            ),
            _t(
                "aircraft_cost_target",
                "user_facing_answer_target",
                "Aircraft operating-cost posture per passenger-mile",
                "What operating-cost posture follows for Pacifica Air in 2024?",
                2,
                "fuel_expense_parent",
                "nonfuel_expense_record",
            ),
        ),
        (
            (
                _r(
                    "period_correct_fuel_price",
                    "Attractive 2025 Atlantic fuel-price basis",
                    "What is the 2024 Pacifica-region fuel price per gallon?",
                    "Pacifica Air 2024 Pacifica fuel price per gallon",
                    "An attractive fictional fact gives a 2025 Atlantic price per litre, not the required basis.",
                    url_slug="wrong-basis-fuel-price",
                    correct_basis=False,
                ),
                _r(
                    "period_correct_fuel_price",
                    "Correct 2024 Pacifica per-gallon fuel price",
                    "What is the 2024 Pacifica-region fuel price per gallon?",
                    "Pacifica Air 2024 Pacifica fuel price per gallon",
                    "The fictional 2024 Pacifica record directly states the region-matched price per gallon.",
                    url_slug="correct-basis-fuel-price",
                ),
            ),
        ),
        AIRCRAFT_RESULT,
    ),
    OfflineScenario(
        CASE_7,
        "Deep",
        "Determine Meridian Works' Northstar route only if the missing registry premise and both required relationships can be warranted.",
        "Do not construct the compliance class or final route unless the missing registry premise is directly recovered.",
        (
            _d(
                "active_certificate",
                "Nonclosure active certificate",
                "Is Meridian Works' certificate active?",
                "Meridian nonclosure active certificate",
                "The fictional certificate directly records an active status.",
            ),
            _d(
                "regional_filing_flag",
                "Nonclosure regional flag",
                "What regional flag applies to Meridian Works?",
                "Meridian nonclosure regional flag",
                "The fictional regional record directly establishes the filing flag.",
            ),
        ),
        (
            _t(
                "nonclosure_compliance_class",
                "supporting_premise",
                "Unwarranted compliance class",
                "Which class follows if the missing registry premise exists?",
                1,
                "active_certificate",
            ),
            _t(
                "nonclosure_route_target",
                "user_facing_answer_target",
                "Conditional Meridian route",
                "Which route follows only if the complete class is warranted?",
                2,
                "nonclosure_compliance_class",
                "regional_filing_flag",
            ),
        ),
        (
            (
                _r(
                    "unavailable_registry_designation",
                    "Unavailable Meridian registry designation",
                    "Which current registry designation applies to Meridian Works?",
                    "Meridian unavailable registry designation",
                    "No fixture material is available for this required premise.",
                ),
            ),
        ),
        "The certificate and regional flag are directly supported, but no compliance class or filing route is warranted.",
        PASS,
        True,
    ),
)
SCENARIO_BY_ID = {item.scenario_id: item for item in SCENARIOS}


def _component(
    component_id: str,
    purpose: str,
    label: str,
    question: str,
    support: Sequence[str],
    depth: int,
    dependencies: Sequence[str] = (),
    obligations: Sequence[str] = (),
) -> dict[str, Any]:
    result = {
        "component_id": component_id,
        "component_revision": "1",
        "component_purpose": purpose,
        "user_facing_label": label,
        "user_facing_question": question,
        "requirement_posture": "required",
        "acceptance_criteria": ["Preserve the exact fictional year, geography, unit, relationship, and source basis."],
        "semantic_slot_ids": ["slot:northstar"],
        "source_obligation_candidate_ids": list(obligations),
        "allowed_support_kinds": list(support),
        "max_inference_depth": depth,
        "materiality": "material",
        "partial_answer_policy": "qualify_visible_gap",
    }
    if dependencies:
        result["dependency_component_ids"] = list(dependencies)
    return result


def planner_payload(scenario: OfflineScenario) -> dict[str, Any]:
    components, obligations, requirements = [], [], []
    for fact in scenario.direct_facts:
        obligation_id = f"obligation:{fact.component_id}"
        components.append(
            _component(
                fact.component_id,
                "user_facing_answer_target" if not scenario.targets else "supporting_premise",
                fact.label,
                fact.question,
                ("direct",),
                0,
                obligations=(obligation_id,),
            )
        )
        strategy = {
            "strategy_id": f"strategy:{fact.component_id}:primary:1",
            "component_id": fact.component_id,
            "candidate_kind": "primary",
            "candidate_query_text": fact.query,
            "requested_role": "initial",
            "source_obligation_candidate_ids": [obligation_id],
            "domain_constraints": {"include": [], "exclude": []},
            "distinct_need_justification": f"Directly establish {fact.label}.",
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
        obligations.append(
            {
                "candidate_id": obligation_id,
                "obligation_kind": "supporting_fact",
                "component_candidate_ids": [fact.component_id],
                "strictness": "required",
                "metadata": {"provider_name_neutral": True},
            }
        )
        requirements.append(
            {
                "component_id": fact.component_id,
                "requirement_id": f"search-requirement:{fact.component_id}:initial",
                "requirement_summary": f"Find direct support for {fact.label}.",
                "source_obligation_candidate_ids": [obligation_id],
                "preferred_source_kinds": ["supporting_fact"],
                "metadata": {
                    "query_strategy_candidates": [strategy],
                    "provider_name_neutral": True,
                },
            }
        )
    components.extend(
        _component(
            item.component_id,
            item.purpose,
            item.label,
            item.question,
            ("inferred",),
            item.max_depth,
            item.dependencies,
        )
        for item in scenario.targets
    )
    return {
        "question_meaning_summary": scenario.meaning,
        "requested_output": "Return the requested root answer or an honest typed nonclosure.",
        "explicit_factual_component_list": True,
        # The installed synthesis directive is the bounded exact root context
        # carried into every Cross-Component Analyst packet.
        "requested_synthesis_directive": scenario.root_query,
        "semantic_slots": [
            {
                "slot_id": "slot:northstar",
                "slot_kind": "entity",
                "status": "explicit",
                "candidate_values": ["Northstar"],
                "selected_value": "Northstar",
                "materiality": "material",
                "user_confirmation_required": False,
            }
        ],
        "answer_components": components,
        "source_obligation_candidates": obligations,
        "component_search_requirements": requirements,
        "relationship_hypotheses": [],
        "material_ambiguity_posture": "none_detected",
        "mandatory_caveats": [],
        "prohibited_upgrades": [
            "Do not treat a planning hypothesis as admitted inference.",
            "Do not substitute a source stating the root conclusion for missing premises.",
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


class ScenarioPlanner:
    def __init__(self, scenario: OfflineScenario) -> None:
        self.scenario = scenario

    def produce(self, _planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return deepcopy(planner_payload(self.scenario))


def _component_by_id(payload: Mapping[str, Any], component_id: str) -> dict[str, Any]:
    for item in payload.get("accepted_component_refs") or ():
        if dict(item).get("component_id") == component_id:
            return dict(item)
    raise AssertionError(f"missing accepted component {component_id}")


def _node_ref(node: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "node_kind": node.get("node_kind"),
        "node_id": node.get("node_id"),
        "node_revision": node.get("node_revision"),
        "node_digest": node.get("node_digest"),
        "component_id": node.get("component_id"),
        "synthesis_key": node.get("synthesis_key"),
        "status": node.get("status") or node.get("admission_status"),
        "current": node.get("current") is True,
        "stale": node.get("stale") is True,
    }


def _available_nodes(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = [
        *list(payload.get("component_nodes") or ()),
        *list(payload.get("licensed_current_component_refs") or ()),
        *list(payload.get("current_synthesis_nodes") or ()),
        *list(payload.get("preserved_boundary_synthesis_catalog") or ()),
    ]
    recovered = dict(payload.get("current_recovered_component_ref") or {})
    if recovered:
        values.append(recovered)
    return [dict(item) for item in values]


def _nodes(payload: Mapping[str, Any], identifiers: Sequence[str]) -> list[dict[str, Any]]:
    wanted = set(identifiers)
    found = {
        str(item.get("component_id") or item.get("synthesis_key")): _node_ref(item)
        for item in _available_nodes(payload)
        if str(item.get("component_id") or item.get("synthesis_key")) in wanted
    }
    if set(found) != wanted:
        raise AssertionError(f"missing current nodes wanted={sorted(wanted)} found={sorted(found)}")
    return sorted(found.values(), key=safe_packet_digest)


def _synthesis(
    key: str,
    claim: str,
    relationship: str,
    *,
    components: Sequence[str] = (),
    syntheses: Sequence[str] = (),
    selective: bool = False,
) -> dict[str, Any]:
    result = {
        "synthesis_key": key,
        "claim_text": claim,
        "relationship_type": relationship,
        "component_inputs": list(components),
        "caveats": [],
        "nonclaims": [],
        "blockers": [],
    }
    if selective:
        result["affected_synthesis_inputs"] = list(syntheses)
        result["preserved_synthesis_inputs"] = []
    else:
        result["synthesis_inputs"] = list(syntheses)
    return result


def _searched(
    payload: Mapping[str, Any],
    *,
    target_id: str,
    dependencies: Sequence[str],
    fact: RecoveryFact,
    depth: int,
) -> dict[str, Any]:
    target = _component_by_id(payload, target_id)
    return {
        "classification": "searched_premise",
        "local_proposal_key": f"recover_{fact.semantic_key}_generation_{depth}",
        "local_target_key": target_id,
        "normalized_premise_identity": f"{fact.semantic_key.replace('_', ' ')} generation {depth}",
        "answer_target_refs": [target],
        "parent_component_refs": [target],
        "current_dependency_component_refs": sorted(
            [_component_by_id(payload, item) for item in dependencies],
            # The model boundary must emit exact component refs in the
            # proposal schema's canonical digest order.
            key=lambda item: _proposal_ref_digest(_proposal_safe(item)),
        ),
        "premise_semantics": fact.label,
        "user_facing_label": fact.label,
        "user_facing_question": fact.question,
        "acceptance_criteria": [
            "Use the exact fictional record matching the required year, geography, unit, and relationship."
        ],
        "requirement_posture": "required",
        "materiality": "material",
        "partial_answer_policy": "qualify_visible_gap",
        "mandatory_caveats": ["The premise remains direct-source bounded."],
        "source_obligation_specification": {
            "candidate_id": f"obligation:{fact.semantic_key}",
            "obligation_kind": "supporting_fact",
            "strictness": "required",
        },
        "necessity_rationale": f"{target['user_facing_label']} requires {fact.label}.",
        "why_current_premises_insufficient": f"The current graph lacks direct support for {fact.label}.",
        "searchability_material_need_posture": "material_and_searchable",
        "recovery_generation": {
            "parent_ref": str(dict(payload.get("graph_ref") or {}).get("graph_digest") or "initial-searchos-state"),
            "depth": depth,
        },
        "assumptions": [],
        "caveats": [],
        "prohibited_upgrades": ["Do not infer the searched premise from query direction or the requested conclusion."],
    }


def _inferred(
    payload: Mapping[str, Any],
    *,
    target_id: str,
    premises: Sequence[str],
    claim: str,
    relationship: str,
    depth: int,
) -> dict[str, Any]:
    return {
        "classification": "inferred_conclusion",
        "local_proposal_key": f"infer_{target_id}_depth_{depth}",
        "local_target_key": target_id,
        "answer_target_ref": _component_by_id(payload, target_id),
        "current_admitted_premise_node_refs": _nodes(payload, premises),
        "relationship_type": relationship,
        "proposed_conclusion": claim,
        "support_kind": "inferred",
        "proposed_semantic_inference_depth": depth,
        "current_graph_ref": dict(payload.get("graph_ref") or {}),
        "existing_specialist_handoff_refs": [],
        "assumptions": [],
        "caveats": ["The conclusion is admitted inference, not direct source text."],
        "prohibited_upgrades": ["Do not state that a premise source directly asserts this conclusion."],
    }


class SearchOSAnalystOSHarness(OfflineOrdinaryPipelineHarness):
    """Fake only existing planner, role-model, discovery, and READ transports."""

    def __init__(self, tmp_path: Path, scenario: OfflineScenario) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=scenario.root_query,
            core_topic=scenario.meaning,
            primary_entity="Northstar",
            researcher_queries=tuple(item.query for item in scenario.direct_facts),
            raw_author_response=scenario.author_response,
            read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
            logger_name=f"test.searchos_analystos.{scenario.scenario_id}",
        )
        self.scenario = scenario
        self.cross_contexts: list[dict[str, Any]] = []
        self.component_contexts: list[dict[str, Any]] = []
        self.dprime_contexts: list[dict[str, Any]] = []
        self.graph_reproof_failures: list[str] = []
        self.unexpected_calls: list[str] = []
        self.correct_recovery_urls = {
            f"https://northstar.example/{item.url_slug}"
            for generation in scenario.recovery_generations
            for item in generation
            if item.correct_basis
        }
        self.distractor_urls = {
            f"https://northstar.example/{item.url_slug}"
            for generation in scenario.recovery_generations
            for item in generation
            if not item.correct_basis
        }

    def deps(self):
        return replace(super().deps(), search_planner_adapter=ScenarioPlanner(self.scenario))

    @staticmethod
    def _passage(
        source_id: int,
        title: str,
        url: str,
        text: str,
        query_ref: str,
    ) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "title": title,
            "url": url,
            "text": text,
            "score": 1.0,
            "credibility": 4,
            "source_tier": "official",
            "source_class": "supporting_fact",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
            "query_ref": query_ref,
            "_provider": "offline_fake_search",
        }

    def build_search_passages(self) -> list[dict[str, Any]]:
        if len(self.search_calls) == 1:
            return [
                self._passage(
                    100 + index,
                    item.label,
                    f"https://northstar.example/{item.component_id.replace('_', '-')}",
                    item.text,
                    item.query,
                )
                for index, item in enumerate(self.scenario.direct_facts, start=1)
            ]
        generation = len(self.search_calls) - 2
        if self.scenario.unavailable_recovery or generation >= len(self.scenario.recovery_generations):
            return []
        return [
            self._passage(
                200 + (generation * 10) + index,
                item.label,
                f"https://northstar.example/{item.url_slug}",
                item.text,
                item.query,
            )
            for index, item in enumerate(
                self.scenario.recovery_generations[generation],
                start=1,
            )
        ]

    def _depth_two_response(
        self,
        payload: Mapping[str, Any],
        call_index: int,
    ) -> dict[str, Any]:
        if call_index == 1:
            return {
                "synthesis_proposals": [
                    _synthesis(
                        "compliance_class",
                        CLASS_RESULT,
                        "certificate_registry_classification",
                        components=("active_certificate", "registry_designation"),
                    ),
                    _synthesis(
                        "meridian_route_target",
                        DEPTH_TWO_RESULT,
                        "classification_regional_route",
                        components=("regional_filing_flag",),
                        syntheses=("compliance_class",),
                    ),
                ],
                "query_resolution_proposals": [
                    _inferred(
                        payload,
                        target_id="compliance_class",
                        premises=("active_certificate", "registry_designation"),
                        claim=CLASS_RESULT,
                        relationship="certificate_registry_classification",
                        depth=1,
                    )
                ],
            }
        return {
            "synthesis_proposals": [
                _synthesis(
                    "meridian_route_target",
                    DEPTH_TWO_RESULT,
                    "classification_regional_route",
                    components=("regional_filing_flag",),
                    syntheses=("compliance_class",),
                )
            ],
            "query_resolution_proposals": [
                _inferred(
                    payload,
                    target_id="meridian_route_target",
                    premises=("compliance_class", "regional_filing_flag"),
                    claim=DEPTH_TWO_RESULT,
                    relationship="classification_regional_route",
                    depth=2,
                )
            ],
        }

    def _nested_response(
        self,
        payload: Mapping[str, Any],
        *,
        call_index: int,
        selective: bool,
    ) -> dict[str, Any]:
        if self.scenario.scenario_id == CASE_6:
            parent_id, root_id = "fuel_expense_parent", "aircraft_cost_target"
            direct_a, direct_d = "fuel_use_basis", "nonfuel_expense_record"
            parent_claim, root_claim = FUEL_RESULT, AIRCRAFT_RESULT
            parent_rel = "price_fuel_use_to_fuel_expense"
            root_rel = "fuel_and_nonfuel_to_operating_cost"
            recovery = self.scenario.recovery_generations[0][-1]
        elif self.scenario.scenario_id == CASE_4:
            parent_id, root_id = "nested_compliance_class", "nested_route_target"
            direct_a, direct_d = "active_certificate", "regional_filing_flag"
            parent_claim, root_claim = NESTED_CLASS_RESULT, NESTED_RESULT
            parent_rel = "certificate_registry_classification"
            root_rel = "classification_regional_route"
            recovery = self.scenario.recovery_generations[0][0]
        else:
            parent_id, root_id = (
                "nonclosure_compliance_class",
                "nonclosure_route_target",
            )
            direct_a, direct_d = "active_certificate", "regional_filing_flag"
            parent_claim = "The unavailable registry premise would be required for a compliance class."
            root_claim = "The unavailable class prevents a warranted route."
            parent_rel = "certificate_registry_classification"
            root_rel = "classification_regional_route"
            recovery = self.scenario.recovery_generations[0][0]
        if call_index == 1:
            return {
                "synthesis_proposals": [
                    _synthesis(
                        parent_id,
                        f"{self.scenario.targets[0].label} remains unresolved pending direct recovery.",
                        f"{parent_rel}_pending_premise",
                        components=(direct_a,),
                    ),
                    _synthesis(
                        root_id,
                        f"{self.scenario.targets[-1].label} remains unresolved pending its parent.",
                        f"{root_rel}_pending_parent",
                        components=(direct_d,),
                        syntheses=(parent_id,),
                    ),
                ],
                "query_resolution_proposals": [
                    _searched(
                        payload,
                        target_id=parent_id,
                        dependencies=(direct_a,),
                        fact=recovery,
                        depth=1,
                    )
                ],
            }
        if selective:
            recovered_id = str(dict(payload["current_recovered_component_ref"])["component_id"])
            return {
                "synthesis_proposals": [
                    _synthesis(
                        parent_id,
                        parent_claim,
                        parent_rel,
                        components=(direct_a, recovered_id),
                        selective=True,
                    ),
                    _synthesis(
                        root_id,
                        root_claim,
                        root_rel,
                        components=(direct_d,),
                        syntheses=(parent_id,),
                        selective=True,
                    ),
                ],
                "query_resolution_proposals": [
                    _inferred(
                        payload,
                        target_id=parent_id,
                        premises=(direct_a, recovered_id),
                        claim=parent_claim,
                        relationship=parent_rel,
                        depth=1,
                    )
                ],
            }
        return {
            "synthesis_proposals": [
                _synthesis(
                    root_id,
                    root_claim,
                    root_rel,
                    components=(direct_d,),
                    syntheses=(parent_id,),
                )
            ],
            "query_resolution_proposals": [
                _inferred(
                    payload,
                    target_id=root_id,
                    premises=(parent_id, direct_d),
                    claim=root_claim,
                    relationship=root_rel,
                    depth=2,
                )
            ],
        }

    def _cross_response(
        self,
        payload: Mapping[str, Any],
        *,
        call_index: int,
        selective: bool,
    ) -> dict[str, Any]:
        case = self.scenario.scenario_id
        if case == CASE_2:
            if not selective:
                return {
                    "synthesis_proposals": [
                        _synthesis(
                            "harbor_route_target",
                            "The Harbor route awaits its signed dispatch condition.",
                            "northstar_filing_rule_pending_premise",
                            components=("current_eligibility",),
                        )
                    ],
                    "query_resolution_proposals": [
                        _searched(
                            payload,
                            target_id="harbor_route_target",
                            dependencies=("current_eligibility",),
                            fact=self.scenario.recovery_generations[0][0],
                            depth=1,
                        )
                    ],
                }
            recovered_id = str(dict(payload["current_recovered_component_ref"])["component_id"])
            return {
                "synthesis_proposals": [
                    _synthesis(
                        "harbor_route_target",
                        SEARCHED_RESULT,
                        "northstar_filing_rule",
                        components=("current_eligibility", recovered_id),
                        selective=True,
                    )
                ],
                "query_resolution_proposals": [
                    _inferred(
                        payload,
                        target_id="harbor_route_target",
                        premises=("current_eligibility", recovered_id),
                        claim=SEARCHED_RESULT,
                        relationship="northstar_filing_rule",
                        depth=1,
                    )
                ],
            }
        if case == CASE_3:
            return self._depth_two_response(payload, call_index)
        if case in {CASE_4, CASE_6, CASE_7}:
            return self._nested_response(
                payload,
                call_index=call_index,
                selective=selective,
            )
        if case == CASE_5:
            if call_index == 1:
                return {
                    "synthesis_proposals": [
                        _synthesis(
                            "solace_route_target",
                            "The Solace route remains unresolved pending late certificate and registry premises.",
                            "late_dependency_chain_pending",
                            components=("solace_regional_flag",),
                        )
                    ],
                    "query_resolution_proposals": [
                        _searched(
                            payload,
                            target_id="solace_route_target",
                            dependencies=("solace_regional_flag",),
                            fact=self.scenario.recovery_generations[0][0],
                            depth=1,
                        )
                    ],
                }
            recovered_id = str(dict(payload["current_recovered_component_ref"])["component_id"])
            return {
                "synthesis_proposals": [
                    _synthesis(
                        "solace_route_target",
                        "The Solace route remains unresolved because a sibling registry premise is still missing.",
                        "late_dependency_chain_pending_sibling",
                        components=("solace_regional_flag", recovered_id),
                        selective=True,
                    )
                ],
                "query_resolution_proposals": [
                    _searched(
                        payload,
                        target_id="solace_route_target",
                        dependencies=("solace_regional_flag", recovered_id),
                        fact=self.scenario.recovery_generations[1][0],
                        depth=2,
                    )
                ],
            }
        raise AssertionError(f"unexpected Cross call for {case}")

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        role_prompt = (
            system_prompt in ROLE_SYSTEM_PROMPTS.values()
            or system_prompt == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT
        )
        if role_prompt:
            payload = json.loads(prompt)
            self._record_model_call(system_prompt, kwargs)
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
                component = dict(payload.get("component_ref") or {})
                self.component_contexts.append(
                    {
                        "component_ref": {
                            key: component.get(key)
                            for key in (
                                "component_id",
                                "component_revision",
                                "component_digest",
                                "component_purpose",
                                "user_facing_label",
                                "user_facing_question",
                                "dependency_component_ids",
                                "acceptance_criteria",
                            )
                        },
                        "accepted_contract_ref": dict(payload.get("accepted_contract_ref") or {}),
                        "evidence_ref_id": dict(payload.get("component_evidence") or {}).get("evidence_ref_id"),
                    }
                )
                return json.dumps(
                    {
                        "claim_text": f"Direct fictional source support is current for {component.get('user_facing_label')}.",
                        "case_posture": "supported",
                        "evidence_analysis": (
                            "The exact current fictional source establishes "
                            "only the stated direct component premise."
                        ),
                        "self_audit": (
                            "The case does not extend beyond the exact "
                            "bounded source material."
                        ),
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST_RESUME]:
                prior = dict(payload.get("prior_component_case") or {})
                semantic = dict(prior)
                return json.dumps(
                    {
                        "claim_text": semantic.get("claim_text") or "Offline resumed finding.",
                        "case_posture": "supported",
                        "evidence_analysis": (
                            "The exact bounded Specialist handoff and current "
                            "component evidence support only the resumed finding."
                        ),
                        "self_audit": (
                            "The resumed case does not treat execution alone as "
                            "support or extend beyond the bounded inputs."
                        ),
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt in {
                ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST],
                SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT,
            }:
                selective = system_prompt == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT
                accepted = list(payload.get("accepted_component_refs") or ())
                self.cross_contexts.append(
                    {
                        "selective": selective,
                        "accepted_contract_ref": dict(
                            payload.get("accepted_contract_ref") or payload.get("current_contract_ref") or {}
                        ),
                        "graph_ref": dict(payload.get("graph_ref") or {}),
                        "requested_synthesis_directive": payload.get("requested_synthesis_directive"),
                        "component_ids": sorted(
                            str(item.get("component_id"))
                            for item in _available_nodes(payload)
                            if item.get("component_id")
                        ),
                        "synthesis_keys": sorted(
                            str(item.get("synthesis_key"))
                            for item in _available_nodes(payload)
                            if item.get("synthesis_key")
                        ),
                        "accepted_component_context": [
                            {
                                key: dict(item).get(key)
                                for key in (
                                    "component_id",
                                    "component_purpose",
                                    "user_facing_label",
                                    "user_facing_question",
                                    "dependency_component_ids",
                                    "acceptance_criteria",
                                )
                            }
                            for item in accepted
                        ],
                    }
                )
                response = self._cross_response(
                    payload,
                    call_index=len(self.cross_contexts),
                    selective=selective,
                )
                return json.dumps(response)
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SYNTHESIS_DPRIME]:
                nominated = dict(payload.get("nominated_synthesis") or {})
                self.dprime_contexts.append(
                    {
                        "graph_ref": dict(payload.get("graph_ref") or {}),
                        "synthesis_key": nominated.get("synthesis_key"),
                        "relationship_type": nominated.get("relationship_type"),
                        "input_refs": [
                            {
                                key: dict(item).get(key)
                                for key in (
                                    "node_kind",
                                    "component_id",
                                    "synthesis_key",
                                    "status",
                                    "admission_status",
                                    "semantic_inference_depth",
                                )
                            }
                            for item in payload.get("current_admitted_inputs") or ()
                        ],
                    }
                )
                return json.dumps(
                    {
                        "validation_status": "supported",
                        "reasons": ["The exact current premises support the bounded nominated relationship."],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER]:
                return json.dumps(
                    {
                        "challenge_status": "passed",
                        "reasons": ["The fictional case preserves exact current lineage and bounded depth."],
                        "challenged_synthesis_keys": [],
                        "caveats": [],
                        "nonclaims": [],
                    }
                )
        if system_prompt.startswith(SEARCHOS_JUDGMENT_SYSTEM_PROMPT):
            result = super().ask_model(prompt, system_prompt, **kwargs)
            decision = json.loads(result)
            if decision.get("action") == "PROPOSE_FOLLOWUP_QUERY":
                cycle_ids = {
                    str(item.get("recovery_cycle_id"))
                    for item in self.read_assessment_calls
                    if item.get("recovery_cycle_id")
                }
                generation = max(0, len(cycle_ids) - 1)
                if generation < len(self.scenario.recovery_generations):
                    decision["followup_query"] = self.scenario.recovery_generations[generation][-1].query
                return json.dumps(decision)
            return result
        return super().ask_model(prompt, system_prompt, **kwargs)


@dataclass
class ScenarioExecution:
    scenario: OfflineScenario
    harness: SearchOSAnalystOSHarness
    captured: dict[str, Any]
    outcome: Any
    observation_packet: dict[str, Any] = field(default_factory=dict)

    @property
    def kernel(self) -> Any:
        return self.captured["run_kernel"]


def _ref(value: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    item = dict(value or {})
    return {key: item.get(key) for key in keys if item.get(key) is not None}


def _trace(execution: ScenarioExecution) -> dict[str, Any]:
    state = execution.kernel.state
    role_artifacts = [
        dict(value)
        for key, value in state.projections.items()
        if str(key).startswith("multicomponent_role:") and isinstance(value, Mapping) and value.get("artifact_id")
    ]
    graph = deepcopy(dict(state.projections.get("multicomponent_component_work_graph_v1") or {}))
    registry = deepcopy(dict(state.projections.get("analyst_query_resolution_proposal") or {}))
    sufficiency = deepcopy(dict(state.sufficiency_judgment_projection or {}))
    initial = deepcopy(dict(state.initial_answer_contract or {}))
    current = deepcopy(dict(state.current_answer_contract or initial))
    searchos = deepcopy(dict(state.searchos_state or {}))
    packet_handoff = execution.captured.get("packet_handoff")
    fap = getattr(packet_handoff, "packet", None)
    graph_nodes = [
        {
            "synthesis_key": item.get("synthesis_key"),
            "status": item.get("status"),
            "support_kind": item.get("support_kind"),
            "semantic_inference_depth": item.get("semantic_inference_depth"),
            "answer_target_component_id": item.get("answer_target_component_id"),
            "input_node_refs": [
                _ref(
                    dict(ref),
                    "node_kind",
                    "component_id",
                    "synthesis_key",
                    "node_id",
                    "node_digest",
                )
                for ref in item.get("input_node_refs") or ()
            ],
            "dprime_ref": _ref(
                dict(item.get("dprime_validation_ref") or {}),
                "artifact_id",
                "artifact_digest",
                "role",
            ),
            "relationship_admission_ref": _ref(
                dict(item.get("inferred_relationship_admission_ref") or {}),
                "relationship_admission_id",
                "relationship_admission_digest",
                "answer_target_component_id",
                "semantic_inference_depth",
                "support_kind",
            ),
        }
        for item in graph.get("synthesis_nodes") or ()
    ]
    consumption = dict(sufficiency.get("multicomponent_graph_consumption") or {})
    status = (
        BOUNDED_LIMIT
        if execution.scenario.scenario_id == CASE_5 and not sufficiency.get("final_answer_allowed")
        else PASS
    )
    query_plan = dict(execution.outcome.execution_trace.get("query_plan") or {})
    return {
        "scenario_id": execution.scenario.scenario_id,
        "mode": execution.scenario.mode,
        "root_query": execution.scenario.root_query,
        "question_meaning_record": {
            "ref": _ref(
                initial,
                "parent_question_meaning_record_id",
                "parent_question_meaning_record_digest",
            ),
            "semantic_projection": {
                key: dict(initial.get("question_meaning_metadata") or {}).get(key)
                for key in (
                    "question_meaning_summary",
                    "requested_output",
                    "requested_synthesis_directive",
                )
            },
        },
        "initial_answer_contract_ref": _ref(
            initial,
            "accepted_contract_version",
            "accepted_contract_digest",
        ),
        "answer_contract_history": {
            "initial_ref": _ref(
                initial,
                "accepted_contract_version",
                "accepted_contract_digest",
            ),
            "current_ref": _ref(
                current,
                "accepted_contract_version",
                "accepted_contract_digest",
            ),
            "admission_refs": [
                _ref(dict(item), "amendment_record_id", "admission_digest")
                for item in state.contract_amendment_admission_history
            ],
            "application_refs": [
                _ref(dict(item), "amendment_record_id", "application_digest")
                for item in state.contract_amendment_application_history
            ],
        },
        "components": [
            {
                key: dict(item).get(key)
                for key in (
                    "component_id",
                    "component_purpose",
                    "user_facing_label",
                    "user_facing_question",
                    "allowed_support_kinds",
                    "max_inference_depth",
                    "dependency_component_ids",
                    "acceptance_criteria",
                    "source_obligation_candidate_ids",
                )
            }
            for item in current.get("accepted_answer_component_refs") or ()
        ],
        "search_work_and_query_plan": {
            "search_work_plan_ref": _ref(
                dict(state.projections.get("search_work_plan") or {}),
                "search_work_plan_id",
                "search_work_plan_digest",
            ),
            "query_plan_ref": _ref(
                query_plan,
                "plan_id",
                "plan_digest",
                "revision",
            ),
            "targets": [
                {
                    key: dict(item).get(key)
                    for key in (
                        "query_plan_item_id",
                        "component_id",
                        "authorized_query",
                        "query_plan_role",
                    )
                }
                for item in query_plan.get("items") or ()
            ],
        },
        "component_analyst": {
            "input_context": deepcopy(execution.harness.component_contexts),
            "output_refs": [
                _ref(
                    dict(item),
                    "artifact_id",
                    "artifact_digest",
                    "role",
                    "logical_evaluation_key",
                )
                for item in role_artifacts
                if dict(item).get("role") == ROLE_COMPONENT_ANALYST
            ],
        },
        "cross_component_analyst": {
            "input_context": deepcopy(execution.harness.cross_contexts),
            "output_refs": [
                _ref(
                    dict(item),
                    "artifact_id",
                    "artifact_digest",
                    "role",
                    "logical_evaluation_key",
                )
                for item in role_artifacts
                if dict(item).get("role") == ROLE_CROSS_COMPONENT_ANALYST
            ],
        },
        "proposal_registry": {
            "registry_ref": _ref(
                registry,
                "registry_id",
                "registry_digest",
                "schema_version",
            ),
            "arbitration": deepcopy(registry.get("arbitration") or []),
            "proposals": [
                _ref(
                    dict(item),
                    "proposal_id",
                    "proposal_digest",
                    "stable_replay_key",
                    "classification",
                )
                for item in registry.get("proposals") or ()
            ],
            "lifecycle": deepcopy(registry.get("proposal_lifecycle") or {}),
        },
        "contract_amendment": {
            "record_refs": [
                _ref(
                    dict(item),
                    "amendment_record_id",
                    "amendment_record_digest",
                )
                for item in state.contract_amendment_admission_history
            ],
            "admission_refs": [
                _ref(dict(item), "amendment_record_id", "admission_digest")
                for item in state.contract_amendment_admission_history
            ],
            "application_refs": [
                _ref(dict(item), "amendment_record_id", "application_digest")
                for item in state.contract_amendment_application_history
            ],
        },
        "searchos": {
            "lease_ref": _ref(
                dict(searchos.get("recovery_lease") or {}),
                "recovery_lease_id",
                "recovery_lease_digest",
                "status",
            ),
            "cycle_admissions": [
                _ref(
                    dict(item),
                    "cycle_id",
                    "generation_depth",
                    "recovery_classification",
                    "status",
                )
                for item in searchos.get("recovery_cycle_admission_history") or ()
            ],
            "cycle_terminals": [
                {
                    **_ref(
                        dict(item),
                        "cycle_id",
                        "terminal_status",
                        "terminal_interpretation",
                    ),
                    "expenditure": deepcopy(dict(item).get("expenditure") or {}),
                }
                for item in searchos.get("recovery_cycle_terminal_history") or ()
            ],
            "terminal_aggregate_ref": _ref(
                dict(searchos.get("recovery_terminal_aggregate") or {}),
                "aggregate_id",
                "aggregate_digest",
                "posture",
                "settled_interpretation",
            ),
        },
        "direct_support": {
            "semantic_observation_refs": [
                _ref(
                    dict(item),
                    "semantic_observation_id",
                    "semantic_observation_digest",
                    "answer_component_id",
                    "support_status",
                    "inference_depth",
                )
                for item in state.semantic_observation_admission_history
            ],
            "component_coverage_refs": [
                _ref(
                    dict(item),
                    "coverage_id",
                    "coverage_digest",
                    "answer_component_id",
                    "coverage_state",
                )
                for item in state.component_coverage_history
            ],
        },
        "graph_v1": {
            "ref": _ref(
                graph,
                "graph_id",
                "graph_revision",
                "graph_digest",
                "graph_status",
            ),
            "revisions": int(graph.get("graph_revision") or 0),
            "synthesis_proposals": graph_nodes,
            "synthesis_dprime_refs": [item["dprime_ref"] for item in graph_nodes if item["dprime_ref"]],
            "runkernel_relationship_admission_refs": [
                item["relationship_admission_ref"] for item in graph_nodes if item["relationship_admission_ref"]
            ],
        },
        "whole_case_analyst_rerun": {
            "call_count": len(execution.harness.cross_contexts),
            "rerun_count": max(0, len(execution.harness.cross_contexts) - 1),
            "triggering_graph_refs": [deepcopy(item["graph_ref"]) for item in execution.harness.cross_contexts[1:]],
        },
        "sufficiency": {
            "decision": sufficiency.get("decision"),
            "rationale": list(sufficiency.get("decision_rationale") or ()),
            "final_answer_posture": sufficiency.get("final_answer_posture"),
            "final_answer_allowed": sufficiency.get("final_answer_allowed"),
            "answer_target_fulfillments": deepcopy(consumption.get("answer_target_fulfillments") or []),
            "supporting_premise_readiness": deepcopy(consumption.get("supporting_premise_readiness") or []),
        },
        "final_answer_packet": {
            "posture": getattr(fap, "final_answer_posture", None),
            "direct_entries": [dict(item) for item in getattr(fap, "direct_component_entries", ())],
            "admitted_synthesis_entries": [dict(item) for item in getattr(fap, "admitted_synthesis_entries", ())],
            "limitations": list(getattr(fap, "limitations", ()) or ()),
        },
        "author": {
            "called": bool(execution.harness.author_prompts),
            "call_count": len(execution.harness.author_prompts),
            "constraints": {
                "packet_only": True,
                "no_evidence_strengthening": True,
                "no_direct_upgrade_of_inference": True,
            },
            "final_posture": (
                "rendered_from_packet" if execution.harness.author_prompts else "safe_non_author_terminal"
            ),
        },
        "unexpected_calls_or_mutations": {
            "forbidden_live_calls": list(execution.harness.forbidden_live_calls),
            "unexpected_model_calls": list(execution.harness.unexpected_calls),
            "legacy_recovery_projection_present": any(
                token in str(key)
                for key in state.projections
                for token in (
                    "_begin_scheduler_dynamic_recovery",
                    "_attempt_dynamic_recovery",
                )
            ),
        },
        "status": status,
    }


def run_offline_integration_scenario(
    scenario: OfflineScenario,
    *,
    tmp_path: Path,
    monkeypatch: Any,
) -> ScenarioExecution:
    """Enter the maintained offline harness and ordinary pipeline exactly once."""

    scrub_offline_runtime(monkeypatch)
    harness = SearchOSAnalystOSHarness(tmp_path, scenario)
    original_graph_reproof = orchestrator.execute_searchos_recovery_graph_reproof_from_scope

    def capture_graph_reproof(**kwargs: Any) -> dict[str, Any]:
        try:
            return original_graph_reproof(**kwargs)
        except Exception as exc:
            graph = dict(
                kwargs["run_kernel"].state.projections.get(
                    "multicomponent_component_work_graph_v1",
                    {},
                )
            )
            statuses = [
                (
                    str(item.get("synthesis_key") or ""),
                    str(item.get("status") or ""),
                )
                for item in graph.get("synthesis_nodes", ())
            ]
            harness.graph_reproof_failures.append(
                f"{type(exc).__name__}:{' '.join(str(exc).split())[:240]}:nodes={statuses!r}"
            )
            raise

    monkeypatch.setattr(
        orchestrator,
        "execute_searchos_recovery_graph_reproof_from_scope",
        capture_graph_reproof,
    )
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
            query=scenario.root_query,
            current_date="2026-07-26",
            session_id=f"integration-{scenario.scenario_id}",
            run_id=f"integration-{scenario.scenario_id}",
        ),
        mode=scenario.mode,
    )
    outcome = orchestrator.run_pipeline(
        config,
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    execution = ScenarioExecution(scenario, harness, captured, outcome)
    execution.observation_packet = _trace(execution)
    return execution


__all__ = [
    "AIRCRAFT_RESULT",
    "BOUNDED_LIMIT",
    "CASE_1",
    "CASE_2",
    "CASE_3",
    "CASE_4",
    "CASE_5",
    "CASE_6",
    "CASE_7",
    "CLASS_RESULT",
    "DEPTH_TWO_RESULT",
    "DIRECT_RESULT",
    "FUEL_RESULT",
    "NESTED_CLASS_RESULT",
    "NESTED_RESULT",
    "OfflineScenario",
    "PASS",
    "SCENARIOS",
    "SCENARIO_BY_ID",
    "SEARCHED_RESULT",
    "ScenarioExecution",
    "run_offline_integration_scenario",
]
