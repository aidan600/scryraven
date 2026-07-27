"""Evaluation-only semantic expectations for AnalystOS model origination.

Harness label: SEAM-DIAGNOSTIC
Ordinary product path guarded or fed:
``core.pipeline_orchestrator.run_pipeline`` through the reusable
``searchos_analystos_offline_scenarios`` corpus.
Runtime consumer: the separately licensed model-origination evaluator.
Why direct product work is not done here: this phase is offline/no-live and may
prepare, but not perform, the first real-model acceptance run.
Integration deadline: the next separately licensed bounded live-model
origination evaluation.
Exit condition: use the harness for that evaluation, then convert it to a
durable regression guard or retire it.
Why this is not a shadow product path: scenario meaning, fictional evidence,
recovery material, and downstream ordinary-path semantics remain owned by the
merged fixture and ordinary pipeline.
Forbidden interpretation: these expectations do not prove real-model quality.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from tests.fixtures.searchos_analystos_offline_scenarios import (
    BOUNDED_LIMIT,
    CASE_1,
    CASE_2,
    CASE_3,
    CASE_4,
    CASE_5,
    CASE_6,
    CASE_7,
    PASS,
    SCENARIO_BY_ID,
)

ROLE_SEARCH_PLANNER = "search_planner"
ROLE_COMPONENT_ANALYST = "component_analyst"
ROLE_CROSS_COMPONENT_ANALYST = "cross_component_analyst"

MODEL_ROLES = frozenset(
    {
        ROLE_SEARCH_PLANNER,
        ROLE_COMPONENT_ANALYST,
        ROLE_CROSS_COMPONENT_ANALYST,
    }
)
ANALYST_ROLES = frozenset(
    {
        ROLE_COMPONENT_ANALYST,
        ROLE_CROSS_COMPONENT_ANALYST,
    }
)

DEFAULT_COMBINED_SCENARIO_IDS = (CASE_3, CASE_4, CASE_6, CASE_7)


@dataclass(frozen=True, slots=True)
class CrossCallExpectation:
    """One expected Cross-Component Analyst semantic-origination call."""

    purpose: str
    classification: str
    target_concept: str
    dependency_concepts: tuple[str, ...]
    relationship_aliases: tuple[str, ...] = ()
    semantic_inference_depth: int = 0
    support_kind: str = "direct"
    conditional_skip_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioEvaluationExpectation:
    """Scoring and call-planning metadata layered over the merged corpus."""

    scenario_id: str
    expected_status: str
    expected_terminal_posture: str
    component_call_concepts: tuple[str, ...]
    cross_calls: tuple[CrossCallExpectation, ...]
    concept_aliases: Mapping[str, tuple[str, ...]]
    expected_search_generations: int
    rejected_search_generation: int | None = None
    distractor_concepts: tuple[str, ...] = ()
    honest_nonclosure: bool = False


def _aliases(scenario_id: str, overrides: Mapping[str, tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
    """Derive aliases from the canonical fixture without copying its corpus."""

    scenario = SCENARIO_BY_ID[scenario_id]
    result: dict[str, tuple[str, ...]] = {}
    for item in (*scenario.direct_facts, *scenario.targets):
        concept = item.component_id
        generated = (
            concept,
            concept.replace("_", " "),
            item.label,
            item.question,
        )
        result[concept] = tuple(dict.fromkeys((*generated, *overrides.get(concept, ()))))
    for generation in scenario.recovery_generations:
        for item in generation:
            concept = item.semantic_key
            generated = (
                concept,
                concept.replace("_", " "),
                item.label,
                item.question,
            )
            existing = result.get(concept, ())
            result[concept] = tuple(dict.fromkeys((*existing, *generated, *overrides.get(concept, ()))))
    return result


def _searched(
    target: str,
    dependencies: tuple[str, ...],
    *,
    purpose: str,
    skip: str | None = None,
) -> CrossCallExpectation:
    return CrossCallExpectation(
        purpose=purpose,
        classification="searched_premise",
        target_concept=target,
        dependency_concepts=dependencies,
        conditional_skip_reason=skip,
    )


def _inferred(
    target: str,
    dependencies: tuple[str, ...],
    relationships: tuple[str, ...],
    *,
    depth: int,
    purpose: str,
    skip: str | None = None,
) -> CrossCallExpectation:
    return CrossCallExpectation(
        purpose=purpose,
        classification="inferred_conclusion",
        target_concept=target,
        dependency_concepts=dependencies,
        relationship_aliases=relationships,
        semantic_inference_depth=depth,
        support_kind="inferred",
        conditional_skip_reason=skip,
    )


SCENARIO_EXPECTATIONS = {
    CASE_1: ScenarioEvaluationExpectation(
        scenario_id=CASE_1,
        expected_status=PASS,
        expected_terminal_posture="direct_closure",
        component_call_concepts=("harbor_filing_route",),
        cross_calls=(),
        concept_aliases=_aliases(
            CASE_1,
            {"harbor_filing_route": ("harbor route", "direct filing route")},
        ),
        expected_search_generations=0,
    ),
    CASE_2: ScenarioEvaluationExpectation(
        scenario_id=CASE_2,
        expected_status=PASS,
        expected_terminal_posture="inferred_closure_after_one_searched_premise",
        component_call_concepts=("current_eligibility", "signed_dispatch_condition"),
        cross_calls=(
            _searched(
                "harbor_route_target",
                ("current_eligibility",),
                purpose="originate the missing searchable signed-dispatch premise",
            ),
            _inferred(
                "harbor_route_target",
                ("current_eligibility", "signed_dispatch_condition"),
                ("northstar filing rule", "eligibility signed dispatch route"),
                depth=1,
                purpose="originate the Harbor route relationship after recovery",
                skip="skip when searched-premise recovery fails closed",
            ),
        ),
        concept_aliases=_aliases(
            CASE_2,
            {
                "current_eligibility": ("harbor eligibility",),
                "signed_dispatch_condition": ("signed dispatch", "dispatch condition"),
                "harbor_route_target": ("harbor route", "filing route"),
            },
        ),
        expected_search_generations=1,
    ),
    CASE_3: ScenarioEvaluationExpectation(
        scenario_id=CASE_3,
        expected_status=PASS,
        expected_terminal_posture="depth_two_inferred_closure",
        component_call_concepts=(
            "active_certificate",
            "registry_designation",
            "regional_filing_flag",
        ),
        cross_calls=(
            _inferred(
                "compliance_class",
                ("active_certificate", "registry_designation"),
                ("certificate registry classification", "certificate and registry class"),
                depth=1,
                purpose="originate the depth-one compliance-class intermediate",
            ),
            _inferred(
                "meridian_route_target",
                ("compliance_class", "regional_filing_flag"),
                ("classification regional route", "class and regional flag route"),
                depth=2,
                purpose="originate the depth-two Meridian route",
                skip="skip when the depth-one intermediate fails closed",
            ),
        ),
        concept_aliases=_aliases(
            CASE_3,
            {
                "active_certificate": ("certificate active",),
                "registry_designation": ("registry class designation",),
                "regional_filing_flag": ("regional flag",),
                "compliance_class": ("northstar class",),
                "meridian_route_target": ("meridian route",),
            },
        ),
        expected_search_generations=0,
    ),
    CASE_4: ScenarioEvaluationExpectation(
        scenario_id=CASE_4,
        expected_status=PASS,
        expected_terminal_posture="nested_recovery_then_depth_two_closure",
        component_call_concepts=(
            "active_certificate",
            "regional_filing_flag",
            "registry_designation",
        ),
        cross_calls=(
            _searched(
                "nested_compliance_class",
                ("active_certificate",),
                purpose="originate the missing searchable registry premise",
            ),
            _inferred(
                "nested_compliance_class",
                ("active_certificate", "registry_designation"),
                ("certificate registry classification", "certificate and registry class"),
                depth=1,
                purpose="reconcile fresh authority into the nested class",
                skip="skip when registry recovery fails closed",
            ),
            _inferred(
                "nested_route_target",
                ("nested_compliance_class", "regional_filing_flag"),
                ("classification regional route", "class and regional flag route"),
                depth=2,
                purpose="reconcile the newly derivable nested route",
                skip="skip when the nested class remains unresolved",
            ),
        ),
        concept_aliases=_aliases(
            CASE_4,
            {
                "active_certificate": ("nested active certificate",),
                "registry_designation": ("recovered registry",),
                "regional_filing_flag": ("nested regional flag",),
                "nested_compliance_class": ("nested class",),
                "nested_route_target": ("nested route",),
            },
        ),
        expected_search_generations=1,
    ),
    CASE_5: ScenarioEvaluationExpectation(
        scenario_id=CASE_5,
        expected_status=BOUNDED_LIMIT,
        expected_terminal_posture="bounded_limit_before_second_generation",
        component_call_concepts=("solace_regional_flag", "solace_certificate"),
        cross_calls=(
            _searched(
                "solace_route_target",
                ("solace_regional_flag",),
                purpose="originate the first late searchable certificate premise",
            ),
            _searched(
                "solace_route_target",
                ("solace_regional_flag", "solace_certificate"),
                purpose="record the second late searchable registry premise for policy rejection",
                skip="skip when the first searched generation fails closed",
            ),
        ),
        concept_aliases=_aliases(
            CASE_5,
            {
                "solace_regional_flag": ("solace flag",),
                "solace_certificate": ("solace active certificate",),
                "solace_registry_designation": ("solace registry",),
                "solace_route_target": ("solace route",),
            },
        ),
        expected_search_generations=1,
        rejected_search_generation=2,
    ),
    CASE_6: ScenarioEvaluationExpectation(
        scenario_id=CASE_6,
        expected_status=PASS,
        expected_terminal_posture="distractor_resistant_depth_two_closure",
        component_call_concepts=(
            "fuel_use_basis",
            "nonfuel_expense_record",
            "period_correct_fuel_price",
        ),
        cross_calls=(
            _searched(
                "fuel_expense_parent",
                ("fuel_use_basis",),
                purpose="originate the missing period-correct searchable fuel-price premise",
            ),
            _inferred(
                "fuel_expense_parent",
                ("fuel_use_basis", "period_correct_fuel_price"),
                ("price fuel use to fuel expense", "fuel price and use expense"),
                depth=1,
                purpose="reconcile the period-correct fuel-expense intermediate",
                skip="skip when correct-basis recovery fails closed",
            ),
            _inferred(
                "aircraft_cost_target",
                ("fuel_expense_parent", "nonfuel_expense_record"),
                ("fuel and nonfuel to operating cost", "fuel and non-fuel operating cost"),
                depth=2,
                purpose="reconcile the root operating-cost target",
                skip="skip when the fuel-expense intermediate remains unresolved",
            ),
        ),
        concept_aliases=_aliases(
            CASE_6,
            {
                "fuel_use_basis": ("fuel use",),
                "nonfuel_expense_record": ("non-fuel expense", "nonfuel expense"),
                "period_correct_fuel_price": (
                    "2024 pacifica fuel price",
                    "period correct fuel price",
                    "price per gallon",
                ),
                "fuel_expense_parent": ("fuel expense",),
                "aircraft_cost_target": ("operating cost", "aircraft cost"),
            },
        ),
        expected_search_generations=1,
        distractor_concepts=("2025 atlantic", "price per litre"),
    ),
    CASE_7: ScenarioEvaluationExpectation(
        scenario_id=CASE_7,
        expected_status=PASS,
        expected_terminal_posture="honest_nonclosure",
        component_call_concepts=("active_certificate", "regional_filing_flag"),
        cross_calls=(
            _searched(
                "nonclosure_compliance_class",
                ("active_certificate",),
                purpose="originate the required searchable registry premise",
            ),
        ),
        concept_aliases=_aliases(
            CASE_7,
            {
                "active_certificate": ("certificate active",),
                "regional_filing_flag": ("regional flag",),
                "unavailable_registry_designation": ("missing registry",),
                "nonclosure_compliance_class": ("conditional class",),
                "nonclosure_route_target": ("conditional route",),
            },
        ),
        expected_search_generations=1,
        honest_nonclosure=True,
    ),
}


def expectation_for(scenario_id: str) -> ScenarioEvaluationExpectation:
    """Return one exact evaluation expectation or fail closed."""

    try:
        return SCENARIO_EXPECTATIONS[scenario_id]
    except KeyError as exc:
        raise ValueError(f"unknown AnalystOS evaluation scenario: {scenario_id}") from exc


__all__ = [
    "ANALYST_ROLES",
    "DEFAULT_COMBINED_SCENARIO_IDS",
    "MODEL_ROLES",
    "ROLE_COMPONENT_ANALYST",
    "ROLE_CROSS_COMPONENT_ANALYST",
    "ROLE_SEARCH_PLANNER",
    "SCENARIO_EXPECTATIONS",
    "CrossCallExpectation",
    "ScenarioEvaluationExpectation",
    "expectation_for",
]
