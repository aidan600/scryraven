"""Exhaustive offline census for SearchPlanner semantic-validation rule IDs.

Mode: REPAIR.
Test class: phase_focus / offline_validator_census.
No test in this file makes provider, search, READ, or retrieval calls.
"""

from __future__ import annotations

import ast
import json
import re
from copy import deepcopy
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
_EXPECTED_RULE_COUNT = 92

_EXPECTED_TYPE_ENUM_OR_BOUND_RULE_IDS = frozenset(
    {
        SearchPlannerSemanticValidationRuleId.PROPOSAL_JSON_OBJECT_REQUIRED,
        SearchPlannerSemanticValidationRuleId.DISPOSITION_ENUM,
        SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_FRESHNESS_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_FRESHNESS_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_CAVEAT_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_CAVEAT_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.COMPONENT_ARRAY_MAX_ITEMS,
        SearchPlannerSemanticValidationRuleId.COMPONENT_OBJECT_REQUIRED,
        SearchPlannerSemanticValidationRuleId.COMPONENT_NEED_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.COMPONENT_NEED_NONEMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_NEED_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.COMPONENT_PURPOSE_ENUM,
        SearchPlannerSemanticValidationRuleId.COMPONENT_POSTURE_ENUM,
        SearchPlannerSemanticValidationRuleId.COMPONENT_SUPPORT_ENUM,
        SearchPlannerSemanticValidationRuleId.COMPONENT_KEY_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.COMPONENT_KEY_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_ARRAY_REQUIRED,
        SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_MAX_ITEMS,
        SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_ITEM_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_ITEM_TEXT_BOUND,
        SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_UNIQUE_VALUES,
        SearchPlannerSemanticValidationRuleId.SOURCE_OBJECT_REQUIRED,
        SearchPlannerSemanticValidationRuleId.SOURCE_KIND_ENUM,
        SearchPlannerSemanticValidationRuleId.SOURCE_STRICTNESS_ENUM,
        SearchPlannerSemanticValidationRuleId.COMPONENT_FRESHNESS_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.COMPONENT_FRESHNESS_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.COMPONENT_UNCERTAINTIES_ARRAY_REQUIRED,
        SearchPlannerSemanticValidationRuleId.COMPONENT_UNCERTAINTIES_MAX_ITEMS,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_OBJECT_REQUIRED,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_STATUS_ENUM,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_KIND_ENUM,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_ARRAY_REQUIRED,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_MAX_ITEMS,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_ITEM_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_ITEM_TEXT_BOUND,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_UNIQUE_VALUES,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_SELECTED_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_SELECTED_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_USER_CONFIRMATION_REQUIRED_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_MATERIALITY_ENUM,
        SearchPlannerSemanticValidationRuleId.COMPONENT_CAVEAT_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.COMPONENT_CAVEAT_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.COMPONENT_PROHIBITED_UPGRADE_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.COMPONENT_PROHIBITED_UPGRADE_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.COMPONENT_NORMALIZATION_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.COMPONENT_NORMALIZATION_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.COMPONENT_CALCULATION_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.COMPONENT_CALCULATION_MAX_BOUND,
        SearchPlannerSemanticValidationRuleId.AUTHORITATIVE_USER_QUERY_JSON_TYPE,
        SearchPlannerSemanticValidationRuleId.AUTHORITATIVE_USER_QUERY_NONEMPTY,
        SearchPlannerSemanticValidationRuleId.AUTHORITATIVE_USER_QUERY_MAX_BOUND,
    }
)

_EXPECTED_OMISSION_RULE_IDS = frozenset(
    {
        SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_FRESHNESS_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_CAVEAT_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_PURPOSE_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_POSTURE_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_SUPPORT_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_KEY_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.SOURCE_STRICTNESS_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_FRESHNESS_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_UNCERTAINTIES_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_SELECTED_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.UNCERTAINTY_MATERIALITY_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_CAVEAT_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_PROHIBITED_UPGRADE_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_NORMALIZATION_OMIT_EMPTY,
        SearchPlannerSemanticValidationRuleId.COMPONENT_CALCULATION_OMIT_EMPTY,
    }
)

_EXPECTED_CROSS_FIELD_RULE_IDS = frozenset(
    {
        SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_QUERY_COMPATIBILITY_BOUND,
        SearchPlannerSemanticValidationRuleId.DUPLICATE_COMPONENT_LOCAL_KEY,
        SearchPlannerSemanticValidationRuleId.DEPENDENCY_LOCAL_KEY_RESOLUTION,
        SearchPlannerSemanticValidationRuleId.DEPENDENCY_SELF_REFERENCE_FORBIDDEN,
        SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_USER_FACING_TARGET,
        SearchPlannerSemanticValidationRuleId.DIRECT_SUPPORT_FORBIDS_DEPENDS_ON,
        SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_REQUIRES_DEPENDS_ON,
        SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_SOURCE,
        SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_FRESHNESS,
        SearchPlannerSemanticValidationRuleId.UNRESOLVED_AMBIGUOUS_FORBIDS_SELECTED,
        SearchPlannerSemanticValidationRuleId.SELECTED_MUST_BE_DECLARED_CANDIDATE,
        SearchPlannerSemanticValidationRuleId.CONFIRMATION_REQUIRES_MATERIAL_UNRESOLVED,
    }
)

_EXPECTED_FORBIDDEN_SURFACE_RULE_IDS = frozenset(
    {
        SearchPlannerSemanticValidationRuleId.SENSITIVE_FIELD_FORBIDDEN,
        SearchPlannerSemanticValidationRuleId.MECHANICAL_IDENTITY_FIELD_FORBIDDEN,
        SearchPlannerSemanticValidationRuleId.RICH_ADMINISTRATIVE_FIELD_FORBIDDEN,
        SearchPlannerSemanticValidationRuleId.CLOSED_AUTHORITY_FIELD_FORBIDDEN,
        SearchPlannerSemanticValidationRuleId.PROVIDER_ROUTING_FIELD_FORBIDDEN,
    }
)

_EXPECTED_BRANCH_FIELD_SET_DETAILS = {
    SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_WITH_COMPONENTS: (
        SearchPlannerBranchFieldSetDetail.DIRECT_SIMPLE_WITH_COMPONENTS
    ),
    SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL: (
        SearchPlannerBranchFieldSetDetail.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL
    ),
    SearchPlannerSemanticValidationRuleId.COMPONENTS_DISALLOWED_TOP_LEVEL: (
        SearchPlannerBranchFieldSetDetail.COMPONENTS_DISALLOWED_TOP_LEVEL
    ),
    SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_NONEMPTY: (
        SearchPlannerBranchFieldSetDetail.COMPONENTS_REQUIRED_NONEMPTY
    ),
    SearchPlannerSemanticValidationRuleId.COMPONENT_UNKNOWN_FIELD_FORBIDDEN: (
        SearchPlannerBranchFieldSetDetail.COMPONENT_UNKNOWN_FIELD_FORBIDDEN
    ),
    SearchPlannerSemanticValidationRuleId.SOURCE_UNKNOWN_FIELD_FORBIDDEN: (
        SearchPlannerBranchFieldSetDetail.SOURCE_UNKNOWN_FIELD_FORBIDDEN
    ),
    SearchPlannerSemanticValidationRuleId.UNCERTAINTY_UNKNOWN_FIELD_FORBIDDEN: (
        SearchPlannerBranchFieldSetDetail.UNCERTAINTY_UNKNOWN_FIELD_FORBIDDEN
    ),
}


def _expected_rule_projections() -> dict[
    SearchPlannerSemanticValidationRuleId,
    tuple[SearchPlannerSemanticProposalSubtype, SearchPlannerBranchFieldSetDetail | None],
]:
    groups = (
        _EXPECTED_TYPE_ENUM_OR_BOUND_RULE_IDS,
        _EXPECTED_OMISSION_RULE_IDS,
        _EXPECTED_CROSS_FIELD_RULE_IDS,
        _EXPECTED_FORBIDDEN_SURFACE_RULE_IDS,
        frozenset(_EXPECTED_BRANCH_FIELD_SET_DETAILS),
    )
    grouped = set().union(*groups)
    assert sum(len(group) for group in groups) == len(grouped)
    assert grouped == set(SearchPlannerSemanticValidationRuleId)
    result = {
        rule_id: (SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND, None)
        for rule_id in _EXPECTED_TYPE_ENUM_OR_BOUND_RULE_IDS
    }
    result.update(
        {
            rule_id: (SearchPlannerSemanticProposalSubtype.OMISSION_CONTRACT, None)
            for rule_id in _EXPECTED_OMISSION_RULE_IDS
        }
    )
    result.update(
        {
            rule_id: (SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION, None)
            for rule_id in _EXPECTED_CROSS_FIELD_RULE_IDS
        }
    )
    result.update(
        {
            rule_id: (SearchPlannerSemanticProposalSubtype.FORBIDDEN_SURFACE, None)
            for rule_id in _EXPECTED_FORBIDDEN_SURFACE_RULE_IDS
        }
    )
    result.update(
        {
            rule_id: (SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET, detail)
            for rule_id, detail in _EXPECTED_BRANCH_FIELD_SET_DETAILS.items()
        }
    )
    return result


_EXPECTED_RULE_PROJECTIONS = _expected_rule_projections()
_LEGACY_HELPER_SHAPED_RULE_VALUES = frozenset(
    {
        "required_text_json_string",
        "required_text_nonempty",
        "required_text_max_bound",
        "optional_text_json_string",
        "optional_text_omit_empty",
        "optional_text_max_bound",
        "required_enum_member",
        "optional_enum_member",
        "optional_boolean_json_type",
        "text_list_array_required",
        "text_list_omit_empty",
        "text_list_max_items",
        "text_list_item_json_string",
        "text_list_item_text_bound",
        "text_list_unique_values",
        "external_text_json_string",
        "external_text_nonempty",
        "external_text_max_bound",
        "nested_disallowed_field",
    }
)


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


def _rejects(proposal: Any) -> Callable[[], None]:
    return lambda: validate_semantic_planner_proposal(deepcopy(proposal))


def _uncertainty_rejects(**overrides: Any) -> Callable[[], None]:
    return _rejects(_components(_component(uncertainties=[_uncertainty(**overrides)])))


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
            _rejects([]),
        ),
        (SearchPlannerSemanticValidationRuleId.DISPOSITION_ENUM, _rejects({"disposition": "invalid"})),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_QUERY_COMPATIBILITY_BOUND,
            lambda: _compile_direct("x" * 301),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_WITH_COMPONENTS,
            _rejects(_direct(components=[])),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL,
            _rejects(_direct(unexpected="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_FRESHNESS_JSON_TYPE,
            _rejects(_direct(freshness=1)),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_FRESHNESS_OMIT_EMPTY,
            _rejects(_direct(freshness=" ")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_FRESHNESS_MAX_BOUND,
            _rejects(_direct(freshness="x" * 221)),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_CAVEAT_JSON_TYPE,
            _rejects(_direct(caveat=1)),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_CAVEAT_OMIT_EMPTY,
            _rejects(_direct(caveat=" ")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_CAVEAT_MAX_BOUND,
            _rejects(_direct(caveat="x" * 261)),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENTS_DISALLOWED_TOP_LEVEL,
            _rejects(_components(_component(), unexpected="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_NONEMPTY,
            _rejects({"disposition": "components"}),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_ARRAY_MAX_ITEMS,
            _rejects(_components(*(_component() for _ in range(6)))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DUPLICATE_COMPONENT_LOCAL_KEY,
            _rejects(_components(_component(key="a"), _component(key="a"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DEPENDENCY_LOCAL_KEY_RESOLUTION,
            _rejects(_components(_component(key="a"), _component(support="inferred", depends_on=["missing"]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DEPENDENCY_SELF_REFERENCE_FORBIDDEN,
            _rejects(_components(_component(key="a", support="inferred", depends_on=["a"]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_USER_FACING_TARGET,
            _rejects(_components(_component(purpose="supporting_premise"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_OBJECT_REQUIRED,
            _rejects(_components(object())),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_UNKNOWN_FIELD_FORBIDDEN,
            _rejects(_components(_component(unexpected="x"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_NEED_JSON_TYPE,
            _rejects(_components(_component(need=1))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_NEED_NONEMPTY,
            _rejects(_components(_component(need=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_NEED_MAX_BOUND,
            _rejects(_components(_component(need="x" * 301))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_PURPOSE_ENUM,
            _rejects(_components(_component(purpose="invalid"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_PURPOSE_OMIT_EMPTY,
            _rejects(_components(_component(purpose=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_POSTURE_ENUM,
            _rejects(_components(_component(posture="invalid"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_POSTURE_OMIT_EMPTY,
            _rejects(_components(_component(posture=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_SUPPORT_ENUM,
            _rejects(_components(_component(support="invalid"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_SUPPORT_OMIT_EMPTY,
            _rejects(_components(_component(support=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_KEY_JSON_TYPE,
            _rejects(_components(_component(key=1))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_KEY_OMIT_EMPTY,
            _rejects(_components(_component(key=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_KEY_MAX_BOUND,
            _rejects(_components(_component(key="x" * 81))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_ARRAY_REQUIRED,
            _rejects(_components(_component(depends_on="a"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_OMIT_EMPTY,
            _rejects(_components(_component(depends_on=[]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_MAX_ITEMS,
            _rejects(_components(_component(depends_on=["a"] * 6))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_ITEM_JSON_TYPE,
            _rejects(_components(_component(depends_on=[1]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_ITEM_TEXT_BOUND,
            _rejects(_components(_component(depends_on=["x" * 81]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_UNIQUE_VALUES,
            _rejects(_components(_component(depends_on=["a", "a"]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.DIRECT_SUPPORT_FORBIDS_DEPENDS_ON,
            _rejects(_components(_component(depends_on=["a"]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_REQUIRES_DEPENDS_ON,
            _rejects(_components(_component(support="inferred"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_SOURCE,
            _rejects(
                _components(
                    _component(key="a"),
                    _component(support="inferred", depends_on=["a"], source={"kind": "official_current"}),
                )
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_FRESHNESS,
            _rejects(
                _components(
                    _component(key="a"),
                    _component(support="inferred", depends_on=["a"], freshness="current"),
                )
            ),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SOURCE_OBJECT_REQUIRED,
            _rejects(_direct(source=1)),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SOURCE_UNKNOWN_FIELD_FORBIDDEN,
            _rejects(_direct(source={"unexpected": "x"})),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SOURCE_KIND_ENUM,
            _rejects(_direct(source={"kind": "invalid"})),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SOURCE_STRICTNESS_ENUM,
            _rejects(_direct(source={"kind": "official_current", "strictness": "invalid"})),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SOURCE_STRICTNESS_OMIT_EMPTY,
            _rejects(_direct(source={"kind": "official_current", "strictness": " "})),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_FRESHNESS_JSON_TYPE,
            _rejects(_components(_component(freshness=1))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_FRESHNESS_OMIT_EMPTY,
            _rejects(_components(_component(freshness=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_FRESHNESS_MAX_BOUND,
            _rejects(_components(_component(freshness="x" * 221))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_UNCERTAINTIES_ARRAY_REQUIRED,
            _rejects(_components(_component(uncertainties="x"))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_UNCERTAINTIES_OMIT_EMPTY,
            _rejects(_components(_component(uncertainties=[]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_UNCERTAINTIES_MAX_ITEMS,
            _rejects(_components(_component(uncertainties=[_uncertainty() for _ in range(6)]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_OBJECT_REQUIRED,
            _rejects(_components(_component(uncertainties=[object()]))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_UNKNOWN_FIELD_FORBIDDEN,
            _uncertainty_rejects(unexpected="x"),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_STATUS_ENUM,
            _uncertainty_rejects(status="invalid"),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_KIND_ENUM,
            _uncertainty_rejects(kind="invalid"),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_ARRAY_REQUIRED,
            _uncertainty_rejects(candidates="x"),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_OMIT_EMPTY,
            _uncertainty_rejects(candidates=[]),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_MAX_ITEMS,
            _uncertainty_rejects(candidates=["x"] * 9),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_ITEM_JSON_TYPE,
            _uncertainty_rejects(candidates=[1]),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_ITEM_TEXT_BOUND,
            _uncertainty_rejects(candidates=["x" * 221]),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_UNIQUE_VALUES,
            _uncertainty_rejects(candidates=["a", "a"]),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_SELECTED_JSON_TYPE,
            _uncertainty_rejects(selected=1),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_SELECTED_OMIT_EMPTY,
            _uncertainty_rejects(selected=" "),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_SELECTED_MAX_BOUND,
            _uncertainty_rejects(selected="x" * 221),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_USER_CONFIRMATION_REQUIRED_JSON_TYPE,
            _uncertainty_rejects(user_confirmation_required="yes"),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_MATERIALITY_ENUM,
            _uncertainty_rejects(materiality="invalid"),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNCERTAINTY_MATERIALITY_OMIT_EMPTY,
            _uncertainty_rejects(materiality=" "),
        ),
        (
            SearchPlannerSemanticValidationRuleId.UNRESOLVED_AMBIGUOUS_FORBIDS_SELECTED,
            _uncertainty_rejects(status="ambiguous", selected="x"),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SELECTED_MUST_BE_DECLARED_CANDIDATE,
            _uncertainty_rejects(candidates=["a"], selected="b"),
        ),
        (
            SearchPlannerSemanticValidationRuleId.CONFIRMATION_REQUIRES_MATERIAL_UNRESOLVED,
            _uncertainty_rejects(user_confirmation_required=True),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_CAVEAT_JSON_TYPE,
            _rejects(_components(_component(caveat=1))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_CAVEAT_OMIT_EMPTY,
            _rejects(_components(_component(caveat=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_CAVEAT_MAX_BOUND,
            _rejects(_components(_component(caveat="x" * 261))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_PROHIBITED_UPGRADE_JSON_TYPE,
            _rejects(_components(_component(prohibited_upgrade=1))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_PROHIBITED_UPGRADE_OMIT_EMPTY,
            _rejects(_components(_component(prohibited_upgrade=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_PROHIBITED_UPGRADE_MAX_BOUND,
            _rejects(_components(_component(prohibited_upgrade="x" * 261))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_NORMALIZATION_JSON_TYPE,
            _rejects(_components(_component(normalization=1))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_NORMALIZATION_OMIT_EMPTY,
            _rejects(_components(_component(normalization=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_NORMALIZATION_MAX_BOUND,
            _rejects(_components(_component(normalization="x" * 301))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_CALCULATION_JSON_TYPE,
            _rejects(_components(_component(calculation=1))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_CALCULATION_OMIT_EMPTY,
            _rejects(_components(_component(calculation=" "))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.COMPONENT_CALCULATION_MAX_BOUND,
            _rejects(_components(_component(calculation="x" * 301))),
        ),
        (
            SearchPlannerSemanticValidationRuleId.AUTHORITATIVE_USER_QUERY_JSON_TYPE,
            lambda: _compile_direct(1),
        ),
        (
            SearchPlannerSemanticValidationRuleId.AUTHORITATIVE_USER_QUERY_NONEMPTY,
            lambda: _compile_direct(" "),
        ),
        (
            SearchPlannerSemanticValidationRuleId.AUTHORITATIVE_USER_QUERY_MAX_BOUND,
            lambda: _compile_direct("x" * 12_001),
        ),
        (
            SearchPlannerSemanticValidationRuleId.SENSITIVE_FIELD_FORBIDDEN,
            _rejects(_direct(raw_fixture="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.MECHANICAL_IDENTITY_FIELD_FORBIDDEN,
            _rejects(_direct(run_id="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.RICH_ADMINISTRATIVE_FIELD_FORBIDDEN,
            _rejects(_direct(answer_components=[])),
        ),
        (
            SearchPlannerSemanticValidationRuleId.CLOSED_AUTHORITY_FIELD_FORBIDDEN,
            _rejects(_direct(accepted_contract="x")),
        ),
        (
            SearchPlannerSemanticValidationRuleId.PROVIDER_ROUTING_FIELD_FORBIDDEN,
            _rejects(_direct(provider="x")),
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

    assert len(SearchPlannerSemanticValidationRuleId) == _EXPECTED_RULE_COUNT
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
    assert set(_EXPECTED_BRANCH_FIELD_SET_DETAILS.values()) == set(SearchPlannerBranchFieldSetDetail)
    for rule_id, registration in registry.items():
        assert rule_id.value == rule_id.name.casefold()
        assert re.search(r"(?:^|_)\d+(?:_|$)", rule_id.value) is None
        assert registration.semantic_proposal_subtype in SearchPlannerSemanticProposalSubtype
        assert (registration.branch_field_set_detail is not None) == (
            registration.semantic_proposal_subtype is SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET
        )


def test_helper_shaped_ids_are_replaced_by_static_field_and_object_rules() -> None:
    values = {rule_id.value for rule_id in SearchPlannerSemanticValidationRuleId}

    assert not values & _LEGACY_HELPER_SHAPED_RULE_VALUES
    assert (
        len(
            {
                SearchPlannerSemanticValidationRuleId.COMPONENT_PURPOSE_ENUM,
                SearchPlannerSemanticValidationRuleId.COMPONENT_POSTURE_ENUM,
                SearchPlannerSemanticValidationRuleId.COMPONENT_SUPPORT_ENUM,
                SearchPlannerSemanticValidationRuleId.SOURCE_STRICTNESS_ENUM,
                SearchPlannerSemanticValidationRuleId.UNCERTAINTY_MATERIALITY_ENUM,
            }
        )
        == 5
    )
    assert (
        len(
            {
                SearchPlannerSemanticValidationRuleId.COMPONENT_UNKNOWN_FIELD_FORBIDDEN,
                SearchPlannerSemanticValidationRuleId.SOURCE_UNKNOWN_FIELD_FORBIDDEN,
                SearchPlannerSemanticValidationRuleId.UNCERTAINTY_UNKNOWN_FIELD_FORBIDDEN,
            }
        )
        == 3
    )


def test_rule_projection_is_registry_owned_not_exception_message_text() -> None:
    rule_id = SearchPlannerSemanticValidationRuleId.COMPONENT_PURPOSE_ENUM
    first = SearchPlannerSemanticProposalError(
        "first message includes arbitrary rejected-value sentinel",
        semantic_validation_rule_id=rule_id,
    )
    second = SearchPlannerSemanticProposalError(
        "second unrelated message contains another sentinel",
        semantic_validation_rule_id=rule_id,
    )

    assert first.subtype is second.subtype is SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND
    assert first.branch_field_set_detail is second.branch_field_set_detail is None


def test_every_registered_rule_exercises_one_current_validator_rejection_path() -> None:
    cases = _census_cases()
    assert len(cases) == len(SearchPlannerSemanticValidationRuleId)
    assert {rule_id for rule_id, _ in cases} == set(SearchPlannerSemanticValidationRuleId)

    observed = {_raise_rule(rule_id, invoke).semantic_validation_rule_id for rule_id, invoke in cases}
    assert observed == set(SearchPlannerSemanticValidationRuleId)


def test_known_valid_sparse_proposals_remain_accepted_unchanged() -> None:
    direct = _direct(source={"kind": "official_current"}, freshness="current", caveat="bounded")
    components = _components(
        _component(
            key="premise",
            purpose="supporting_premise",
            source={"kind": "official_current"},
            freshness="current",
            caveat="bounded",
            prohibited_upgrade="no upgrade",
            normalization="plain",
            calculation="none",
        ),
        _component(
            key="target",
            support="inferred",
            depends_on=["premise"],
            uncertainties=[
                _uncertainty(
                    status="explicit",
                    candidates=["one"],
                    selected="one",
                    materiality="material",
                )
            ],
        ),
    )
    for proposal in (direct, components):
        assert validate_semantic_planner_proposal(deepcopy(proposal)) == proposal
        compile_semantic_planner_proposal(
            deepcopy(proposal),
            user_query_text="bounded offline query",
            requested_mode="Balanced",
        )


def test_typed_rule_survives_the_existing_failure_carrier_chain_without_values() -> None:
    rejected_enum_value = "private-rejected-enum-sentinel"
    query_text = "private-query-sentinel"
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        accept_planner_model_output(
            _components(_component(purpose=rejected_enum_value)),
            user_query_text=query_text,
            requested_mode="Balanced",
        )

    failure = caught.value
    assert failure.semantic_validation_rule_id is SearchPlannerSemanticValidationRuleId.COMPONENT_PURPOSE_ENUM
    terminal = compatibility_cli._bounded_terminal_payload(
        entrypoint="scryraven",
        exc=failure,
        config=RunConfig(query=query_text),
    )
    observation = CanonicalProductSearchPlannerBoundaryObserver(lambda *_args, **_kwargs: "").finalize(
        run_kernel=None,
        failure=failure,
    )

    assert (
        terminal["terminal"]["search_planner_failure"]["semantic_validation_rule_id"]
        == failure.semantic_validation_rule_id.value
    )
    assert observation.semantic_validation_rule_id == failure.semantic_validation_rule_id.value
    retained = json.dumps(
        {"terminal": terminal, "observation": observation.to_packet()},
        sort_keys=True,
    )
    assert rejected_enum_value not in retained
    assert query_text not in retained
    assert "exception_text" not in retained
    assert '"provider_payload":' not in retained


_RULE_KEYWORDS_BY_HELPER = {
    "_required_text": {"json_type_rule_id", "nonempty_rule_id", "max_bound_rule_id"},
    "_optional_text": {"json_type_rule_id", "empty_omission_rule_id", "max_bound_rule_id"},
    "_required_enum": {"rule_id"},
    "_optional_enum": {"enum_rule_id", "empty_omission_rule_id"},
    "_optional_bool": {"json_type_rule_id"},
    "_optional_text_list": {
        "array_rule_id",
        "empty_omission_rule_id",
        "max_items_rule_id",
        "item_json_type_rule_id",
        "item_text_bound_rule_id",
        "uniqueness_rule_id",
    },
    "_normalized_external_text": {"json_type_rule_id", "nonempty_rule_id", "max_bound_rule_id"},
}
_GENERIC_HELPER_OWNERS = frozenset({"_required_enum", "_optional_enum"})


def _is_closed_rule_reference(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "SearchPlannerSemanticValidationRuleId"
    )


def test_static_callers_supply_closed_rule_ids_without_context_value_or_ordinal_derivation() -> None:
    source = _COMPILER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
        for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
            if not isinstance(call.func, ast.Name) or call.func.id not in _RULE_KEYWORDS_BY_HELPER:
                continue
            rule_keywords = _RULE_KEYWORDS_BY_HELPER[call.func.id]
            supplied = {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg is not None}
            assert rule_keywords <= set(supplied)
            if function.name not in _GENERIC_HELPER_OWNERS:
                assert all(_is_closed_rule_reference(supplied[key]) for key in rule_keywords)

    constructors = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SearchPlannerSemanticProposalError"
    ]
    assert constructors
    for constructor in constructors:
        keywords = {keyword.arg: keyword.value for keyword in constructor.keywords}
        assert "semantic_validation_rule_id" in keywords
        assert "subtype" not in keywords
        assert "branch_field_set_detail" not in keywords
        identifier_names = {
            node.id for node in ast.walk(keywords["semantic_validation_rule_id"]) if isinstance(node, ast.Name)
        }
        assert not identifier_names & {"context", "key", "index", "item", "value", "mapping", "model_output"}

    assert "classify_semantic_proposal_subtype" not in source
    assert "classify_semantic_validation_rule" not in source


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
