"""Exhaustive offline census for SearchPlanner semantic-validation rule IDs.

Mode: REPAIR.
Test class: phase_focus / offline_validator_census.
No test in this file makes provider, search, READ, or retrieval calls.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Callable

import pytest

import core.search_planner_semantic_compiler as compiler
from core.run_config import RunConfig
from core.search_planner_model_adapter import (
    SearchPlannerModelAdapterError,
    accept_planner_model_output,
)
from core.search_planner_semantic_compiler import (
    SEARCH_PLANNER_SEMANTIC_VALIDATION_RULE_REGISTRY,
    SearchPlannerBranchFieldSetDetail,
    SearchPlannerSemanticProposalError,
    SearchPlannerSemanticProposalSubtype,
    SearchPlannerSemanticValidationRuleId,
    compile_semantic_planner_proposal,
    validate_semantic_planner_proposal,
)
from proplex import __main__ as compatibility_cli
from scripts.evaluation.search_planner_product_boundary_observer import (
    CanonicalProductSearchPlannerBoundaryObserver,
)

_COMPILER_PATH = Path(compiler.__file__).resolve()


_EXPECTED_RULE_PROJECTIONS: dict[
    SearchPlannerSemanticValidationRuleId,
    tuple[
        SearchPlannerSemanticProposalSubtype,
        SearchPlannerBranchFieldSetDetail | None,
    ],
] = {
    SearchPlannerSemanticValidationRuleId.PROPOSAL_JSON_OBJECT_REQUIRED: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_QUERY_COMPATIBILITY_BOUND: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_WITH_COMPONENTS: (
        SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET,
        SearchPlannerBranchFieldSetDetail.DIRECT_SIMPLE_WITH_COMPONENTS,
    ),
    SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL: (
        SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET,
        SearchPlannerBranchFieldSetDetail.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL,
    ),
    SearchPlannerSemanticValidationRuleId.COMPONENTS_DISALLOWED_TOP_LEVEL: (
        SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET,
        SearchPlannerBranchFieldSetDetail.COMPONENTS_DISALLOWED_TOP_LEVEL,
    ),
    SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_NONEMPTY: (
        SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET,
        SearchPlannerBranchFieldSetDetail.COMPONENTS_REQUIRED_NONEMPTY,
    ),
    SearchPlannerSemanticValidationRuleId.COMPONENT_ARRAY_MAX_ITEMS: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.DUPLICATE_COMPONENT_LOCAL_KEY: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.DEPENDENCY_LOCAL_KEY_RESOLUTION: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.DEPENDENCY_SELF_REFERENCE_FORBIDDEN: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_USER_FACING_TARGET: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.COMPONENT_OBJECT_REQUIRED: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.NESTED_DISALLOWED_FIELD: (
        SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET,
        SearchPlannerBranchFieldSetDetail.NESTED_DISALLOWED_FIELD,
    ),
    SearchPlannerSemanticValidationRuleId.DIRECT_SUPPORT_FORBIDS_DEPENDS_ON: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_REQUIRES_DEPENDS_ON: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_SOURCE: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_FRESHNESS: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.SOURCE_OBJECT_REQUIRED: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.UNCERTAINTIES_ARRAY_REQUIRED: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.UNCERTAINTIES_OMIT_EMPTY: (
        SearchPlannerSemanticProposalSubtype.OMISSION_CONTRACT,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.UNCERTAINTIES_MAX_ITEMS: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.UNCERTAINTY_OBJECT_REQUIRED: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.UNRESOLVED_AMBIGUOUS_FORBIDS_SELECTED: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.SELECTED_MUST_BE_DECLARED_CANDIDATE: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.CONFIRMATION_REQUIRES_MATERIAL_UNRESOLVED: (
        SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.REQUIRED_TEXT_JSON_STRING: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.REQUIRED_TEXT_NONEMPTY: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.REQUIRED_TEXT_MAX_BOUND: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.OPTIONAL_TEXT_JSON_STRING: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.OPTIONAL_TEXT_OMIT_EMPTY: (
        SearchPlannerSemanticProposalSubtype.OMISSION_CONTRACT,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.OPTIONAL_TEXT_MAX_BOUND: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.REQUIRED_ENUM_MEMBER: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.OPTIONAL_ENUM_MEMBER: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.OPTIONAL_BOOLEAN_JSON_TYPE: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.TEXT_LIST_ARRAY_REQUIRED: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.TEXT_LIST_OMIT_EMPTY: (
        SearchPlannerSemanticProposalSubtype.OMISSION_CONTRACT,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.TEXT_LIST_MAX_ITEMS: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.TEXT_LIST_ITEM_JSON_STRING: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.TEXT_LIST_ITEM_TEXT_BOUND: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.TEXT_LIST_UNIQUE_VALUES: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.EXTERNAL_TEXT_JSON_STRING: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.EXTERNAL_TEXT_NONEMPTY: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.EXTERNAL_TEXT_MAX_BOUND: (
        SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.SENSITIVE_FIELD_FORBIDDEN: (
        SearchPlannerSemanticProposalSubtype.FORBIDDEN_SURFACE,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.MECHANICAL_IDENTITY_FIELD_FORBIDDEN: (
        SearchPlannerSemanticProposalSubtype.FORBIDDEN_SURFACE,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.RICH_ADMINISTRATIVE_FIELD_FORBIDDEN: (
        SearchPlannerSemanticProposalSubtype.FORBIDDEN_SURFACE,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.CLOSED_AUTHORITY_FIELD_FORBIDDEN: (
        SearchPlannerSemanticProposalSubtype.FORBIDDEN_SURFACE,
        None,
    ),
    SearchPlannerSemanticValidationRuleId.PROVIDER_ROUTING_FIELD_FORBIDDEN: (
        SearchPlannerSemanticProposalSubtype.FORBIDDEN_SURFACE,
        None,
    ),
}


def _component(**overrides: Any) -> dict[str, Any]:
    return {"need": "bounded fixture need", **overrides}


def _components(*components: Any, **top_level: Any) -> dict[str, Any]:
    return {
        "disposition": "components",
        "components": list(components),
        **top_level,
    }


def _direct(**overrides: Any) -> dict[str, Any]:
    return {"disposition": "direct_simple", **overrides}


def _uncertainty(**overrides: Any) -> dict[str, Any]:
    return {
        "kind": "unknown_or_other",
        "status": "explicit",
        **overrides,
    }


def _compile_direct(value: Any) -> None:
    compile_semantic_planner_proposal(
        _direct(),
        user_query_text=value,
        requested_mode="Balanced",
    )


RuleCase = tuple[SearchPlannerSemanticValidationRuleId, Callable[[], None]]


def _census_cases() -> tuple[RuleCase, ...]:
    return (
        (
            SearchPlannerSemanticValidationRuleId.PROPOSAL_JSON_OBJECT_REQUIRED,
            lambda: validate_semantic_planner_proposal([]),  # type: ignore[arg-type]
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_QUERY_COMPATIBILITY_BOUND,
            lambda: _compile_direct("x" * 301),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_WITH_COMPONENTS,
            lambda: validate_semantic_planner_proposal(_direct(components=[])),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL,
            lambda: validate_semantic_planner_proposal(_direct(unexpected="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENTS_DISALLOWED_TOP_LEVEL,
            lambda: validate_semantic_planner_proposal(_components(_component(), unexpected="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_NONEMPTY,
            lambda: validate_semantic_planner_proposal({"disposition": "components"}),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_ARRAY_MAX_ITEMS,
            lambda: validate_semantic_planner_proposal(_components(*(_component() for _ in range(6)))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DUPLICATE_COMPONENT_LOCAL_KEY,
            lambda: validate_semantic_planner_proposal(_components(_component(key="a"), _component(key="a"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DEPENDENCY_LOCAL_KEY_RESOLUTION,
            lambda: validate_semantic_planner_proposal(
                _components(
                    _component(key="a"),
                    _component(support="inferred", depends_on=["missing"]),
                )
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DEPENDENCY_SELF_REFERENCE_FORBIDDEN,
            lambda: validate_semantic_planner_proposal(
                _components(
                    _component(
                        key="a",
                        support="inferred",
                        depends_on=["a"],
                    )
                )
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_USER_FACING_TARGET,
            lambda: validate_semantic_planner_proposal(_components(_component(purpose="supporting_premise"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_OBJECT_REQUIRED,
            lambda: validate_semantic_planner_proposal(_components(object())),
        ),
        (
            SearchPlannerSemanticValidationRuleId.NESTED_DISALLOWED_FIELD,
            lambda: validate_semantic_planner_proposal(_components(_component(unexpected="x"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SUPPORT_FORBIDS_DEPENDS_ON,
            lambda: validate_semantic_planner_proposal(_components(_component(depends_on=["a"]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_REQUIRES_DEPENDS_ON,
            lambda: validate_semantic_planner_proposal(_components(_component(support="inferred"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_SOURCE,
            lambda: validate_semantic_planner_proposal(
                _components(
                    _component(key="a"),
                    _component(
                        support="inferred",
                        depends_on=["a"],
                        source={"kind": "official_current"},
                    ),
                )
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_FRESHNESS,
            lambda: validate_semantic_planner_proposal(
                _components(
                    _component(key="a"),
                    _component(
                        support="inferred",
                        depends_on=["a"],
                        freshness="current",
                    ),
                )
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SOURCE_OBJECT_REQUIRED,
            lambda: validate_semantic_planner_proposal(_direct(source=1)),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTIES_ARRAY_REQUIRED,
            lambda: validate_semantic_planner_proposal(_components(_component(uncertainties="x"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTIES_OMIT_EMPTY,
            lambda: validate_semantic_planner_proposal(_components(_component(uncertainties=[]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTIES_MAX_ITEMS,
            lambda: validate_semantic_planner_proposal(
                _components(_component(uncertainties=[_uncertainty() for _ in range(6)]))
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_OBJECT_REQUIRED,
            lambda: validate_semantic_planner_proposal(_components(_component(uncertainties=[object()]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNRESOLVED_AMBIGUOUS_FORBIDS_SELECTED,
            lambda: validate_semantic_planner_proposal(
                _components(_component(uncertainties=[_uncertainty(status="ambiguous", selected="x")]))
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SELECTED_MUST_BE_DECLARED_CANDIDATE,
            lambda: validate_semantic_planner_proposal(
                _components(_component(uncertainties=[_uncertainty(candidates=["a"], selected="b")]))
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.CONFIRMATION_REQUIRES_MATERIAL_UNRESOLVED,
            lambda: validate_semantic_planner_proposal(
                _components(_component(uncertainties=[_uncertainty(user_confirmation_required=True)]))
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.REQUIRED_TEXT_JSON_STRING,
            lambda: validate_semantic_planner_proposal(_components(_component(need=1))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.REQUIRED_TEXT_NONEMPTY,
            lambda: validate_semantic_planner_proposal({"disposition": " "}),
        ),
        (
            SearchPlannerSemanticValidationRuleId.REQUIRED_TEXT_MAX_BOUND,
            lambda: validate_semantic_planner_proposal({"disposition": "x" * 81}),
        ),
        (
            SearchPlannerSemanticValidationRuleId.OPTIONAL_TEXT_JSON_STRING,
            lambda: validate_semantic_planner_proposal(_direct(caveat=1)),
        ),
        (
            SearchPlannerSemanticValidationRuleId.OPTIONAL_TEXT_OMIT_EMPTY,
            lambda: validate_semantic_planner_proposal(_direct(caveat=" ")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.OPTIONAL_TEXT_MAX_BOUND,
            lambda: validate_semantic_planner_proposal(_direct(caveat="x" * 261)),
        ),
        (
            SearchPlannerSemanticValidationRuleId.REQUIRED_ENUM_MEMBER,
            lambda: validate_semantic_planner_proposal({"disposition": "invalid"}),
        ),
        (
            SearchPlannerSemanticValidationRuleId.OPTIONAL_ENUM_MEMBER,
            lambda: validate_semantic_planner_proposal(_components(_component(purpose="invalid"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.OPTIONAL_BOOLEAN_JSON_TYPE,
            lambda: validate_semantic_planner_proposal(
                _components(_component(uncertainties=[_uncertainty(user_confirmation_required="yes")]))
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.TEXT_LIST_ARRAY_REQUIRED,
            lambda: validate_semantic_planner_proposal(_components(_component(depends_on="a"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.TEXT_LIST_OMIT_EMPTY,
            lambda: validate_semantic_planner_proposal(_components(_component(depends_on=[]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.TEXT_LIST_MAX_ITEMS,
            lambda: validate_semantic_planner_proposal(_components(_component(depends_on=["a"] * 6))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.TEXT_LIST_ITEM_JSON_STRING,
            lambda: validate_semantic_planner_proposal(_components(_component(depends_on=[1]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.TEXT_LIST_ITEM_TEXT_BOUND,
            lambda: validate_semantic_planner_proposal(_components(_component(depends_on=["x" * 81]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.TEXT_LIST_UNIQUE_VALUES,
            lambda: validate_semantic_planner_proposal(_components(_component(depends_on=["a", "a"]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.EXTERNAL_TEXT_JSON_STRING,
            lambda: _compile_direct(1),
        ),
        (
            SearchPlannerSemanticValidationRuleId.EXTERNAL_TEXT_NONEMPTY,
            lambda: _compile_direct(" "),
        ),
        (
            SearchPlannerSemanticValidationRuleId.EXTERNAL_TEXT_MAX_BOUND,
            lambda: _compile_direct("x" * 12_001),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SENSITIVE_FIELD_FORBIDDEN,
            lambda: validate_semantic_planner_proposal(_direct(raw_fixture="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.MECHANICAL_IDENTITY_FIELD_FORBIDDEN,
            lambda: validate_semantic_planner_proposal(_direct(run_id="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.RICH_ADMINISTRATIVE_FIELD_FORBIDDEN,
            lambda: validate_semantic_planner_proposal(_direct(answer_components=[])),
        ),
        (
            SearchPlannerSemanticValidationRuleId.CLOSED_AUTHORITY_FIELD_FORBIDDEN,
            lambda: validate_semantic_planner_proposal(_direct(accepted_contract="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.PROVIDER_ROUTING_FIELD_FORBIDDEN,
            lambda: validate_semantic_planner_proposal(_direct(provider="x")),
        ),
    )


def _raise_rule(
    expected_rule_id: SearchPlannerSemanticValidationRuleId,
    invoke: Callable[[], None],
) -> SearchPlannerSemanticProposalError:
    with pytest.raises(SearchPlannerSemanticProposalError) as caught:
        invoke()
    error = caught.value
    assert error.semantic_validation_rule_id is expected_rule_id
    expected_subtype, expected_detail = _EXPECTED_RULE_PROJECTIONS[expected_rule_id]
    assert error.subtype is expected_subtype
    assert error.branch_field_set_detail is expected_detail
    return error


def test_rule_registry_is_closed_exact_and_has_no_aliases() -> None:
    registry = SEARCH_PLANNER_SEMANTIC_VALIDATION_RULE_REGISTRY

    assert len(SearchPlannerSemanticValidationRuleId.__members__) == len(SearchPlannerSemanticValidationRuleId)
    assert set(registry) == set(SearchPlannerSemanticValidationRuleId)
    assert set(_EXPECTED_RULE_PROJECTIONS) == set(SearchPlannerSemanticValidationRuleId)
    assert {
        rule_id: (
            registration.semantic_proposal_subtype,
            registration.branch_field_set_detail,
        )
        for rule_id, registration in registry.items()
    } == _EXPECTED_RULE_PROJECTIONS
    for rule_id, registration in registry.items():
        assert rule_id.value == rule_id.name.casefold()
        assert registration.semantic_proposal_subtype in (SearchPlannerSemanticProposalSubtype)
        assert (registration.branch_field_set_detail is not None) == (
            registration.semantic_proposal_subtype is SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET
        )


def test_rule_projection_is_registry_owned_not_exception_message_text() -> None:
    rule_id = SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL
    first = SearchPlannerSemanticProposalError(
        "first message includes arbitrary rejected-value sentinel",
        semantic_validation_rule_id=rule_id,
    )
    second = SearchPlannerSemanticProposalError(
        "second unrelated message contains another sentinel",
        semantic_validation_rule_id=rule_id,
    )

    assert first.subtype is second.subtype is SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET
    assert (
        first.branch_field_set_detail
        is second.branch_field_set_detail
        is SearchPlannerBranchFieldSetDetail.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL
    )


def test_every_registered_rule_exercises_one_current_validator_rejection_path() -> None:
    cases = _census_cases()
    assert len(cases) == len(SearchPlannerSemanticValidationRuleId)
    assert {rule_id for rule_id, _ in cases} == set(SearchPlannerSemanticValidationRuleId)

    observed = {_raise_rule(rule_id, invoke).semantic_validation_rule_id for rule_id, invoke in cases}
    assert observed == set(SearchPlannerSemanticValidationRuleId)


def test_typed_rule_survives_the_existing_failure_carrier_chain() -> None:
    private_field = "private-field-sentinel"
    private_value = "private-value-sentinel"
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        accept_planner_model_output(
            _direct(**{private_field: private_value}),
            user_query_text="bounded offline query",
            requested_mode="Balanced",
        )

    failure = caught.value
    assert failure.semantic_validation_rule_id is (
        SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL
    )
    terminal = compatibility_cli._bounded_terminal_payload(
        entrypoint="scryraven",
        exc=failure,
        config=RunConfig(query="bounded offline query"),
    )
    observation = CanonicalProductSearchPlannerBoundaryObserver(lambda *_args, **_kwargs: "").finalize(
        run_kernel=None, failure=failure
    )

    assert (
        terminal["terminal"]["search_planner_failure"]["semantic_validation_rule_id"]
        == failure.semantic_validation_rule_id.value
    )
    assert observation.semantic_validation_rule_id == (failure.semantic_validation_rule_id.value)
    retained = json.dumps(
        {"terminal": terminal, "observation": observation.to_packet()},
        sort_keys=True,
    )
    assert private_field not in retained
    assert private_value not in retained


def test_every_compiler_rejection_constructor_has_exact_typed_rule_identity() -> None:
    tree = ast.parse(_COMPILER_PATH.read_text(encoding="utf-8"))
    constructors = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SearchPlannerSemanticProposalError"
    ]
    assert constructors
    for constructor in constructors:
        names = {keyword.arg for keyword in constructor.keywords}
        assert "semantic_validation_rule_id" in names
        assert "subtype" not in names
        assert "branch_field_set_detail" not in names
    assert "classify_semantic_proposal_subtype" not in _COMPILER_PATH.read_text(encoding="utf-8")
