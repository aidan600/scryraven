"""Validate sparse SearchPlanner meaning and compile current rich compatibility.

The ordinary model authors only semantic differences.  This module owns the one
compact prompt-visible contract, validates it fail closed, and deterministically
constructs the rich state still required by Phase-1 downstream consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from core.semantic_contract_foundation import (
    ComponentPurpose,
    Materiality,
    RequirementPosture,
    SemanticSlotStatus,
    SourceObligationKind,
    SourceObligationStrictness,
    inference_depth_ceiling_for_mode,
)

SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA_VERSION = "search_planner_sparse_semantic_proposal_v3"
SEARCH_PLANNER_SEMANTIC_PROPOSAL_CONTRACT_FORMAT = "search_planner_sparse_semantic_proposal_v3"

SEARCH_PLANNER_SEMANTIC_PROPOSAL_REQUIRED_TOP_LEVEL_FIELDS = ("disposition",)
SEARCH_PLANNER_SEMANTIC_PROPOSAL_DIRECT_SIMPLE_OPTIONAL_FIELDS = (
    "source",
    "freshness",
    "caveat",
)
SEARCH_PLANNER_SEMANTIC_PROPOSAL_COMPONENTS_BRANCH_REQUIRED_FIELDS = (
    "disposition",
    "components",
)
SEARCH_PLANNER_SEMANTIC_PROPOSAL_COMPONENTS_BRANCH_FORBIDDEN_TOP_LEVEL_FIELDS = (
    "source",
    "freshness",
    "caveat",
)
# Not a single optional set. direct_simple may omit source/freshness/caveat;
# components requires components and forbids those three top-level fields.
SEARCH_PLANNER_SEMANTIC_PROPOSAL_OPTIONAL_TOP_LEVEL_FIELDS = (
    SEARCH_PLANNER_SEMANTIC_PROPOSAL_DIRECT_SIMPLE_OPTIONAL_FIELDS
)

_DISPOSITIONS = frozenset({"direct_simple", "components"})
_COMPONENT_PURPOSES = frozenset(item.value for item in ComponentPurpose)
_REQUIREMENT_POSTURES = frozenset(item.value for item in RequirementPosture)
_UNCERTAINTY_KINDS = frozenset({"entity", "variant", "time_period", "source_basis", "unknown_or_other"})
_UNCERTAINTY_STATUSES = frozenset(item.value for item in SemanticSlotStatus)
_MATERIALITY_VALUES = frozenset(item.value for item in Materiality)
_SOURCE_KINDS = frozenset(
    item.value for item in SourceObligationKind if item is not SourceObligationKind.NO_SPECIAL_OBLIGATION
)
_SOURCE_STRICTNESSES = frozenset(item.value for item in SourceObligationStrictness)
_SUPPORT_VALUES = frozenset({"direct", "inferred", "direct_or_inferred"})

_MAX_COMPONENTS = 5
_MAX_UNCERTAINTIES_PER_COMPONENT = 5
_MAX_NEED_CHARS = 300
_MAX_LOCAL_KEY_CHARS = 80
_MAX_FRESHNESS_CHARS = 220
_MAX_CAVEAT_CHARS = 260
_MAX_POLICY_CHARS = 300
_MAX_UNCERTAINTY_VALUE_CHARS = 220

_FORBIDDEN_MECHANICAL_IDENTITY_KEYS = frozenset(
    {
        "slot_id",
        "component_id",
        "component_revision",
        "candidate_id",
        "requirement_id",
        "strategy_id",
        "hypothesis_id",
        "relationship_id",
        "digest",
        "request_digest",
        "prompt_hash",
        "artifact_digest",
        "stable_ref",
        "lineage_id",
        "dimension_id",
        "unresolved_dimension_ids",
        "query_kind",
        "required_for_truthful_targeting",
        "recon_requirement",
        "semantic_slot_ids",
        "source_obligation_candidate_ids",
        "component_candidate_ids",
        "dependency_component_ids",
        "target_component_id",
        "premise_component_ids",
        "run_id",
        "request_id",
    }
)

_FORBIDDEN_RICH_KEYS = frozenset(
    {
        "answer_components",
        "semantic_slots",
        "source_obligation_candidates",
        "component_search_requirements",
        "contract_amendment_candidates",
        "relationship_hypotheses",
        "question_meaning_summary",
        "requested_output",
        "material_ambiguity_posture",
        "mandatory_caveats",
        "normalization_obligations",
        "unsupported_or_deferred_outputs",
        "search",
        "recon",
        "primary_query",
        "secondary_query",
    }
)

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "accepted_amendment",
        "accepted_contract",
        "answer",
        "author_input",
        "canonical_coverage",
        "citation",
        "citations",
        "component_coverage_record",
        "contract_amendment_record",
        "current_answer_contract",
        "evidence",
        "evidence_ledger_admission",
        "final_answer",
        "final_answer_packet",
        "initial_answer_contract",
        "search_judgment_decision",
        "semantic_observation",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_FORBIDDEN_PROVIDER_KEYS = frozenset(
    {
        "provider",
        "provider_hint",
        "provider_name",
        "provider_order",
        "provider_depth",
        "provider_variant",
        "provider_fallback",
        "model",
        "model_name",
        "model_selector",
        "routing",
    }
)

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "token",
    }
)

# Exhaustive validator-owned catalog. Not serialized into ordinary model prompts.
SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA: dict[str, Any] = {
    "format": SEARCH_PLANNER_SEMANTIC_PROPOSAL_CONTRACT_FORMAT,
    "json_type": "object",
    "required_top_level": ["disposition"],
    "disposition": {
        "json_type": "string",
        "required": True,
        "enum": sorted(_DISPOSITIONS),
        "empty_vs_omitted": "required nonempty",
    },
    "branches": {
        "direct_simple": {
            "when": "disposition == direct_simple",
            "allowed_fields": ["disposition", "source", "freshness", "caveat"],
            "required_fields": ["disposition"],
            "optional_fields": ["source", "freshness", "caveat"],
            "forbidden_fields": ["components"],
            "unknown_fields": "fail closed",
            "empty_optional_rule": "omit empty strings; do not emit empty values",
            "cross_field": (
                "never a fallback; authoritative query must fit 300 characters; "
                "no dependency, inference, material uncertainty, calculation, "
                "or nonstandard normalization"
            ),
        },
        "components": {
            "when": "disposition == components",
            "allowed_fields": ["disposition", "components"],
            "required_fields": ["disposition", "components"],
            "optional_fields": [],
            "forbidden_fields": ["source", "freshness", "caveat"],
            "unknown_fields": "fail closed",
            "empty_optional_rule": ("components must be a nonempty array; omit empty nested optionals"),
            "cross_field": "requires at least one required user_facing_answer_target",
        },
    },
    "source": {
        "json_type": "object",
        "required": False,
        "allowed_fields": ["kind", "strictness"],
        "presence": {
            "direct_simple": "optional top-level",
            "components_top_level": "forbidden",
            "component": "optional; forbidden when support is inferred",
        },
        "kind": {
            "json_type": "string",
            "required": True,
            "enum": sorted(_SOURCE_KINDS),
        },
        "strictness": {
            "json_type": "string",
            "required": False,
            "enum": sorted(_SOURCE_STRICTNESSES),
            "empty_vs_omitted": "omit instead of empty",
        },
        "empty_vs_omitted": "omit the object instead of empty",
    },
    "freshness": {
        "json_type": "string",
        "required": False,
        "max_chars": _MAX_FRESHNESS_CHARS,
        "empty_vs_omitted": "omit instead of empty",
        "presence": {
            "direct_simple": "optional top-level",
            "components_top_level": "forbidden",
            "component": "optional; forbidden when support is inferred",
        },
    },
    "caveat": {
        "json_type": "string",
        "required": False,
        "max_chars": _MAX_CAVEAT_CHARS,
        "empty_vs_omitted": "omit instead of empty",
        "presence": {
            "direct_simple": "optional top-level",
            "components_top_level": "forbidden",
            "component": "optional",
        },
    },
    "components": {
        "json_type": "array",
        "required_when": "disposition == components",
        "forbidden_when": "disposition == direct_simple",
        "min_items": 1,
        "max_items": _MAX_COMPONENTS,
        "empty_vs_omitted": "must be nonempty when present; omit instead of empty",
        "item": "component",
    },
    "component": {
        "json_type": "object",
        "required": ["need"],
        "optional": [
            "key",
            "purpose",
            "posture",
            "support",
            "depends_on",
            "source",
            "freshness",
            "uncertainties",
            "caveat",
            "prohibited_upgrade",
            "normalization",
            "calculation",
        ],
        "unknown_fields": "fail closed",
        "need": {
            "json_type": "string",
            "required": True,
            "max_chars": _MAX_NEED_CHARS,
            "empty_vs_omitted": "required nonempty",
        },
        "key": {
            "json_type": "string",
            "required": False,
            "max_chars": _MAX_LOCAL_KEY_CHARS,
            "empty_vs_omitted": "omit instead of empty",
        },
        "purpose": {
            "json_type": "string",
            "required": False,
            "enum": sorted(_COMPONENT_PURPOSES),
            "omitted_means": "user_facing_answer_target",
            "empty_vs_omitted": "omit instead of empty",
        },
        "posture": {
            "json_type": "string",
            "required": False,
            "enum": sorted(_REQUIREMENT_POSTURES),
            "omitted_means": "required",
            "empty_vs_omitted": "omit instead of empty",
        },
        "support": {
            "json_type": "string",
            "required": False,
            "enum": sorted(_SUPPORT_VALUES),
            "omitted_means": "direct",
            "empty_vs_omitted": "omit instead of empty",
        },
        "depends_on": {
            "json_type": "array",
            "item_json_type": "string",
            "required": False,
            "max_items": _MAX_COMPONENTS,
            "item_max_chars": _MAX_LOCAL_KEY_CHARS,
            "empty_vs_omitted": "omit instead of empty",
            "cross_field": (
                "required when support is inferred or direct_or_inferred; "
                "forbidden when support is direct or omitted; keys must resolve "
                "to other component keys; no self-dependency"
            ),
        },
        "uncertainties": {
            "json_type": "array",
            "required": False,
            "max_items": _MAX_UNCERTAINTIES_PER_COMPONENT,
            "empty_vs_omitted": "omit instead of empty",
            "item": "uncertainty",
        },
        "prohibited_upgrade": {
            "json_type": "string",
            "required": False,
            "max_chars": _MAX_CAVEAT_CHARS,
            "empty_vs_omitted": "omit instead of empty",
        },
        "normalization": {
            "json_type": "string",
            "required": False,
            "max_chars": _MAX_POLICY_CHARS,
            "empty_vs_omitted": "omit instead of empty",
        },
        "calculation": {
            "json_type": "string",
            "required": False,
            "max_chars": _MAX_POLICY_CHARS,
            "empty_vs_omitted": "omit instead of empty",
        },
    },
    "uncertainty": {
        "json_type": "object",
        "required": ["kind", "status"],
        "optional": [
            "candidates",
            "selected",
            "user_confirmation_required",
            "materiality",
        ],
        "unknown_fields": "fail closed",
        "kind": {
            "json_type": "string",
            "required": True,
            "enum": sorted(_UNCERTAINTY_KINDS),
        },
        "status": {
            "json_type": "string",
            "required": True,
            "enum": sorted(_UNCERTAINTY_STATUSES),
        },
        "candidates": {
            "json_type": "array",
            "item_json_type": "string",
            "required": False,
            "max_items": 8,
            "item_max_chars": _MAX_UNCERTAINTY_VALUE_CHARS,
            "empty_vs_omitted": "omit instead of empty",
        },
        "selected": {
            "json_type": "string",
            "required": False,
            "max_chars": _MAX_UNCERTAINTY_VALUE_CHARS,
            "empty_vs_omitted": "omit instead of empty",
            "cross_field": (
                "forbidden when status is unresolved or ambiguous; when "
                "candidates are present it must match one declared candidate"
            ),
        },
        "user_confirmation_required": {
            "json_type": "boolean",
            "required": False,
            "cross_field": (
                "true only when status is unresolved or ambiguous and "
                "materiality is material (omitted materiality means material)"
            ),
        },
        "materiality": {
            "json_type": "string",
            "required": False,
            "enum": sorted(_MATERIALITY_VALUES),
            "omitted_means": "material",
            "empty_vs_omitted": "omit instead of empty",
        },
    },
    "purpose": sorted(_COMPONENT_PURPOSES),
    "posture": sorted(_REQUIREMENT_POSTURES),
    "support": sorted(_SUPPORT_VALUES),
    "limits": {
        "components": _MAX_COMPONENTS,
        "uncertainties": _MAX_UNCERTAINTIES_PER_COMPONENT,
        "need_chars": _MAX_NEED_CHARS,
        "local_key_chars": _MAX_LOCAL_KEY_CHARS,
        "freshness_chars": _MAX_FRESHNESS_CHARS,
        "caveat_chars": _MAX_CAVEAT_CHARS,
        "policy_chars": _MAX_POLICY_CHARS,
        "uncertainty_value_chars": _MAX_UNCERTAINTY_VALUE_CHARS,
        "uncertainty_candidates": 8,
    },
    "reject": "unknown/rich/mechanical/provider/authority/runtime fields",
}


def build_search_planner_model_visible_schema() -> dict[str, Any]:
    """Compact model-facing projection of the accepted sparse language."""

    exhaustive = SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA
    component = exhaustive["component"]
    uncertainty = exhaustive["uncertainty"]
    return {
        "format": exhaustive["format"],
        "disposition": list(exhaustive["disposition"]["enum"]),
        "direct_simple": list(exhaustive["branches"]["direct_simple"]["allowed_fields"]),
        "components": list(exhaustive["branches"]["components"]["allowed_fields"]),
        "component": {
            "required": list(component["required"]),
            "optional": list(component["optional"]),
        },
        "source": {
            "kind": list(exhaustive["source"]["kind"]["enum"]),
            "strictness": list(exhaustive["source"]["strictness"]["enum"]),
        },
        "uncertainty": {
            "required": list(uncertainty["required"]),
            "optional": list(uncertainty["optional"]),
            "kind": list(uncertainty["kind"]["enum"]),
            "status": list(uncertainty["status"]["enum"]),
            "materiality": list(uncertainty["materiality"]["enum"]),
        },
        "purpose": list(exhaustive["purpose"]),
        "posture": list(exhaustive["posture"]),
        "support": list(exhaustive["support"]),
        "limits": {
            "components": [
                exhaustive["components"]["min_items"],
                exhaustive["components"]["max_items"],
            ],
            "uncertainties": exhaustive["limits"]["uncertainties"],
            "need_chars": exhaustive["limits"]["need_chars"],
        },
        "reject": exhaustive["reject"],
    }


SEARCH_PLANNER_MODEL_VISIBLE_SCHEMA = build_search_planner_model_visible_schema()


class SearchPlannerSemanticProposalSubtype(str, Enum):
    """Closed privacy-safe M02 families under INVALID_SEMANTIC_PROPOSAL."""

    FORBIDDEN_SURFACE = "forbidden_surface"
    BRANCH_FIELD_SET = "branch_field_set"
    OMISSION_CONTRACT = "omission_contract"
    TYPE_ENUM_OR_BOUND = "type_enum_or_bound"
    CROSS_FIELD_CONDITION = "cross_field_condition"


class SearchPlannerBranchFieldSetDetail(str, Enum):
    """Closed privacy-safe detail for branch-field-set rejections."""

    DIRECT_SIMPLE_WITH_COMPONENTS = "direct_simple_with_components"
    DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL = "direct_simple_disallowed_top_level"
    COMPONENTS_DISALLOWED_TOP_LEVEL = "components_disallowed_top_level"
    COMPONENTS_REQUIRED_NONEMPTY = "components_required_nonempty"
    COMPONENT_UNKNOWN_FIELD_FORBIDDEN = "component_unknown_field_forbidden"
    SOURCE_UNKNOWN_FIELD_FORBIDDEN = "source_unknown_field_forbidden"
    UNCERTAINTY_UNKNOWN_FIELD_FORBIDDEN = "uncertainty_unknown_field_forbidden"


class SearchPlannerSemanticValidationRuleId(str, Enum):
    """Closed code-owned identities for sparse semantic validation rules."""

    PROPOSAL_JSON_OBJECT_REQUIRED = "proposal_json_object_required"
    DISPOSITION_ENUM = "disposition_enum"
    DIRECT_SIMPLE_QUERY_COMPATIBILITY_BOUND = "direct_simple_query_compatibility_bound"
    DIRECT_SIMPLE_WITH_COMPONENTS = "direct_simple_with_components"
    DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL = "direct_simple_disallowed_top_level"
    DIRECT_SIMPLE_FRESHNESS_JSON_TYPE = "direct_simple_freshness_json_type"
    DIRECT_SIMPLE_FRESHNESS_OMIT_EMPTY = "direct_simple_freshness_omit_empty"
    DIRECT_SIMPLE_FRESHNESS_MAX_BOUND = "direct_simple_freshness_max_bound"
    DIRECT_SIMPLE_CAVEAT_JSON_TYPE = "direct_simple_caveat_json_type"
    DIRECT_SIMPLE_CAVEAT_OMIT_EMPTY = "direct_simple_caveat_omit_empty"
    DIRECT_SIMPLE_CAVEAT_MAX_BOUND = "direct_simple_caveat_max_bound"
    COMPONENTS_DISALLOWED_TOP_LEVEL = "components_disallowed_top_level"
    COMPONENTS_REQUIRED_NONEMPTY = "components_required_nonempty"
    COMPONENT_ARRAY_MAX_ITEMS = "component_array_max_items"
    DUPLICATE_COMPONENT_LOCAL_KEY = "duplicate_component_local_key"
    DEPENDENCY_LOCAL_KEY_RESOLUTION = "dependency_local_key_resolution"
    DEPENDENCY_SELF_REFERENCE_FORBIDDEN = "dependency_self_reference_forbidden"
    COMPONENTS_REQUIRED_USER_FACING_TARGET = "components_required_user_facing_target"
    COMPONENT_OBJECT_REQUIRED = "component_object_required"
    COMPONENT_UNKNOWN_FIELD_FORBIDDEN = "component_unknown_field_forbidden"
    COMPONENT_NEED_JSON_TYPE = "component_need_json_type"
    COMPONENT_NEED_NONEMPTY = "component_need_nonempty"
    COMPONENT_NEED_MAX_BOUND = "component_need_max_bound"
    COMPONENT_PURPOSE_ENUM = "component_purpose_enum"
    COMPONENT_PURPOSE_OMIT_EMPTY = "component_purpose_omit_empty"
    COMPONENT_POSTURE_ENUM = "component_posture_enum"
    COMPONENT_POSTURE_OMIT_EMPTY = "component_posture_omit_empty"
    COMPONENT_SUPPORT_ENUM = "component_support_enum"
    COMPONENT_SUPPORT_OMIT_EMPTY = "component_support_omit_empty"
    COMPONENT_KEY_JSON_TYPE = "component_key_json_type"
    COMPONENT_KEY_OMIT_EMPTY = "component_key_omit_empty"
    COMPONENT_KEY_MAX_BOUND = "component_key_max_bound"
    COMPONENT_DEPENDS_ON_ARRAY_REQUIRED = "component_depends_on_array_required"
    COMPONENT_DEPENDS_ON_OMIT_EMPTY = "component_depends_on_omit_empty"
    COMPONENT_DEPENDS_ON_MAX_ITEMS = "component_depends_on_max_items"
    COMPONENT_DEPENDS_ON_ITEM_JSON_TYPE = "component_depends_on_item_json_type"
    COMPONENT_DEPENDS_ON_ITEM_TEXT_BOUND = "component_depends_on_item_text_bound"
    COMPONENT_DEPENDS_ON_UNIQUE_VALUES = "component_depends_on_unique_values"
    DIRECT_SUPPORT_FORBIDS_DEPENDS_ON = "direct_support_forbids_depends_on"
    INFERRED_SUPPORT_REQUIRES_DEPENDS_ON = "inferred_support_requires_depends_on"
    INFERRED_SUPPORT_FORBIDS_SOURCE = "inferred_support_forbids_source"
    INFERRED_SUPPORT_FORBIDS_FRESHNESS = "inferred_support_forbids_freshness"
    SOURCE_OBJECT_REQUIRED = "source_object_required"
    SOURCE_UNKNOWN_FIELD_FORBIDDEN = "source_unknown_field_forbidden"
    SOURCE_KIND_ENUM = "source_kind_enum"
    SOURCE_STRICTNESS_ENUM = "source_strictness_enum"
    SOURCE_STRICTNESS_OMIT_EMPTY = "source_strictness_omit_empty"
    COMPONENT_FRESHNESS_JSON_TYPE = "component_freshness_json_type"
    COMPONENT_FRESHNESS_OMIT_EMPTY = "component_freshness_omit_empty"
    COMPONENT_FRESHNESS_MAX_BOUND = "component_freshness_max_bound"
    COMPONENT_UNCERTAINTIES_ARRAY_REQUIRED = "component_uncertainties_array_required"
    COMPONENT_UNCERTAINTIES_OMIT_EMPTY = "component_uncertainties_omit_empty"
    COMPONENT_UNCERTAINTIES_MAX_ITEMS = "component_uncertainties_max_items"
    UNCERTAINTY_OBJECT_REQUIRED = "uncertainty_object_required"
    UNCERTAINTY_UNKNOWN_FIELD_FORBIDDEN = "uncertainty_unknown_field_forbidden"
    UNCERTAINTY_STATUS_ENUM = "uncertainty_status_enum"
    UNCERTAINTY_KIND_ENUM = "uncertainty_kind_enum"
    UNCERTAINTY_CANDIDATES_ARRAY_REQUIRED = "uncertainty_candidates_array_required"
    UNCERTAINTY_CANDIDATES_OMIT_EMPTY = "uncertainty_candidates_omit_empty"
    UNCERTAINTY_CANDIDATES_MAX_ITEMS = "uncertainty_candidates_max_items"
    UNCERTAINTY_CANDIDATES_ITEM_JSON_TYPE = "uncertainty_candidates_item_json_type"
    UNCERTAINTY_CANDIDATES_ITEM_TEXT_BOUND = "uncertainty_candidates_item_text_bound"
    UNCERTAINTY_CANDIDATES_UNIQUE_VALUES = "uncertainty_candidates_unique_values"
    UNCERTAINTY_SELECTED_JSON_TYPE = "uncertainty_selected_json_type"
    UNCERTAINTY_SELECTED_OMIT_EMPTY = "uncertainty_selected_omit_empty"
    UNCERTAINTY_SELECTED_MAX_BOUND = "uncertainty_selected_max_bound"
    UNCERTAINTY_USER_CONFIRMATION_REQUIRED_JSON_TYPE = "uncertainty_user_confirmation_required_json_type"
    UNCERTAINTY_MATERIALITY_ENUM = "uncertainty_materiality_enum"
    UNCERTAINTY_MATERIALITY_OMIT_EMPTY = "uncertainty_materiality_omit_empty"
    UNRESOLVED_AMBIGUOUS_FORBIDS_SELECTED = "unresolved_ambiguous_forbids_selected"
    SELECTED_MUST_BE_DECLARED_CANDIDATE = "selected_must_be_declared_candidate"
    CONFIRMATION_REQUIRES_MATERIAL_UNRESOLVED = "confirmation_requires_material_unresolved"
    COMPONENT_CAVEAT_JSON_TYPE = "component_caveat_json_type"
    COMPONENT_CAVEAT_OMIT_EMPTY = "component_caveat_omit_empty"
    COMPONENT_CAVEAT_MAX_BOUND = "component_caveat_max_bound"
    COMPONENT_PROHIBITED_UPGRADE_JSON_TYPE = "component_prohibited_upgrade_json_type"
    COMPONENT_PROHIBITED_UPGRADE_OMIT_EMPTY = "component_prohibited_upgrade_omit_empty"
    COMPONENT_PROHIBITED_UPGRADE_MAX_BOUND = "component_prohibited_upgrade_max_bound"
    COMPONENT_NORMALIZATION_JSON_TYPE = "component_normalization_json_type"
    COMPONENT_NORMALIZATION_OMIT_EMPTY = "component_normalization_omit_empty"
    COMPONENT_NORMALIZATION_MAX_BOUND = "component_normalization_max_bound"
    COMPONENT_CALCULATION_JSON_TYPE = "component_calculation_json_type"
    COMPONENT_CALCULATION_OMIT_EMPTY = "component_calculation_omit_empty"
    COMPONENT_CALCULATION_MAX_BOUND = "component_calculation_max_bound"
    SOURCE_BOUND_NUMERIC_REQUIRES_CALCULATION = (
        "source_bound_numeric_requires_calculation"
    )
    QUALIFIED_MULTICOMPONENT_STRUCTURE_BINDING = (
        "qualified_multicomponent_structure_binding"
    )
    AUTHORITATIVE_USER_QUERY_JSON_TYPE = "authoritative_user_query_json_type"
    AUTHORITATIVE_USER_QUERY_NONEMPTY = "authoritative_user_query_nonempty"
    AUTHORITATIVE_USER_QUERY_MAX_BOUND = "authoritative_user_query_max_bound"
    SENSITIVE_FIELD_FORBIDDEN = "sensitive_field_forbidden"
    MECHANICAL_IDENTITY_FIELD_FORBIDDEN = "mechanical_identity_field_forbidden"
    RICH_ADMINISTRATIVE_FIELD_FORBIDDEN = "rich_administrative_field_forbidden"
    CLOSED_AUTHORITY_FIELD_FORBIDDEN = "closed_authority_field_forbidden"
    PROVIDER_ROUTING_FIELD_FORBIDDEN = "provider_routing_field_forbidden"


@dataclass(frozen=True, slots=True)
class SearchPlannerSemanticValidationRule:
    """One exact subtype/detail registration for a closed validator rule."""

    semantic_proposal_subtype: SearchPlannerSemanticProposalSubtype
    branch_field_set_detail: SearchPlannerBranchFieldSetDetail | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.semantic_proposal_subtype,
            SearchPlannerSemanticProposalSubtype,
        ):
            raise TypeError("semantic proposal subtype must be a closed enum")
        if self.branch_field_set_detail is not None and not isinstance(
            self.branch_field_set_detail,
            SearchPlannerBranchFieldSetDetail,
        ):
            raise TypeError("branch field-set detail must be a closed enum")
        if (self.semantic_proposal_subtype is SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET) != (
            self.branch_field_set_detail is not None
        ):
            raise ValueError("branch field-set detail must be present exactly for branch-field rules")


def _build_semantic_validation_rule_registry() -> Mapping[
    SearchPlannerSemanticValidationRuleId,
    SearchPlannerSemanticValidationRule,
]:
    """Return the complete static rule-to-projection vocabulary."""

    type_enum_or_bound = SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND
    cross_field = SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION
    omission = SearchPlannerSemanticProposalSubtype.OMISSION_CONTRACT
    forbidden_surface = SearchPlannerSemanticProposalSubtype.FORBIDDEN_SURFACE
    type_enum_or_bound_rule_ids = frozenset(
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
    omission_rule_ids = frozenset(
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
    cross_field_rule_ids = frozenset(
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
            SearchPlannerSemanticValidationRuleId.SOURCE_BOUND_NUMERIC_REQUIRES_CALCULATION,
            SearchPlannerSemanticValidationRuleId.QUALIFIED_MULTICOMPONENT_STRUCTURE_BINDING,
            SearchPlannerSemanticValidationRuleId.UNRESOLVED_AMBIGUOUS_FORBIDS_SELECTED,
            SearchPlannerSemanticValidationRuleId.SELECTED_MUST_BE_DECLARED_CANDIDATE,
            SearchPlannerSemanticValidationRuleId.CONFIRMATION_REQUIRES_MATERIAL_UNRESOLVED,
        }
    )
    forbidden_surface_rule_ids = frozenset(
        {
            SearchPlannerSemanticValidationRuleId.SENSITIVE_FIELD_FORBIDDEN,
            SearchPlannerSemanticValidationRuleId.MECHANICAL_IDENTITY_FIELD_FORBIDDEN,
            SearchPlannerSemanticValidationRuleId.RICH_ADMINISTRATIVE_FIELD_FORBIDDEN,
            SearchPlannerSemanticValidationRuleId.CLOSED_AUTHORITY_FIELD_FORBIDDEN,
            SearchPlannerSemanticValidationRuleId.PROVIDER_ROUTING_FIELD_FORBIDDEN,
        }
    )
    branch_field_set_details = {
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
    groups = (
        type_enum_or_bound_rule_ids,
        omission_rule_ids,
        cross_field_rule_ids,
        forbidden_surface_rule_ids,
        frozenset(branch_field_set_details),
    )
    all_grouped_rule_ids = set().union(*groups)
    if sum(len(group) for group in groups) != len(all_grouped_rule_ids):
        raise ValueError("semantic validation rule registry groups must not overlap")
    if all_grouped_rule_ids != set(SearchPlannerSemanticValidationRuleId):
        raise ValueError("semantic validation rule registry must classify every rule exactly once")

    entries: dict[SearchPlannerSemanticValidationRuleId, SearchPlannerSemanticValidationRule] = {}
    entries.update(
        {rule_id: SearchPlannerSemanticValidationRule(type_enum_or_bound) for rule_id in type_enum_or_bound_rule_ids}
    )
    entries.update({rule_id: SearchPlannerSemanticValidationRule(omission) for rule_id in omission_rule_ids})
    entries.update({rule_id: SearchPlannerSemanticValidationRule(cross_field) for rule_id in cross_field_rule_ids})
    entries.update(
        {rule_id: SearchPlannerSemanticValidationRule(forbidden_surface) for rule_id in forbidden_surface_rule_ids}
    )
    entries.update(
        {
            rule_id: SearchPlannerSemanticValidationRule(
                SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET,
                detail,
            )
            for rule_id, detail in branch_field_set_details.items()
        }
    )
    if set(entries) != set(SearchPlannerSemanticValidationRuleId):
        raise ValueError("semantic validation rule registry must contain every rule exactly once")
    if len(SearchPlannerSemanticValidationRuleId.__members__) != len(SearchPlannerSemanticValidationRuleId):
        raise ValueError("semantic validation rule identifiers must not define aliases")
    for rule_id in SearchPlannerSemanticValidationRuleId:
        if rule_id.value != rule_id.name.casefold() or not rule_id.value.replace("_", "").isalnum():
            raise ValueError("semantic validation rule identifiers must be lowercase snake case")
    return MappingProxyType(entries)


SEARCH_PLANNER_SEMANTIC_VALIDATION_RULE_REGISTRY = _build_semantic_validation_rule_registry()


class SearchPlannerSemanticProposalError(ValueError):
    """Fail-closed sparse semantic proposal validation or compilation error."""

    def __init__(
        self,
        message: str,
        *,
        semantic_validation_rule_id: SearchPlannerSemanticValidationRuleId,
    ) -> None:
        if not isinstance(
            semantic_validation_rule_id,
            SearchPlannerSemanticValidationRuleId,
        ):
            raise TypeError("semantic_validation_rule_id must be a closed enum")
        registration = SEARCH_PLANNER_SEMANTIC_VALIDATION_RULE_REGISTRY.get(semantic_validation_rule_id)
        if registration is None:
            raise ValueError("semantic_validation_rule_id is not registered")
        super().__init__(message)
        self.semantic_validation_rule_id = semantic_validation_rule_id
        self.subtype = registration.semantic_proposal_subtype
        self.branch_field_set_detail = registration.branch_field_set_detail


def is_semantic_planner_proposal(payload: Mapping[str, Any]) -> bool:
    """Return whether a payload declares the sparse discriminator."""

    return isinstance(payload, Mapping) and "disposition" in payload


def count_model_authored_mechanical_identity_keys(
    payload: Mapping[str, Any],
) -> int:
    """Count forbidden mechanical identity key names in a proposal."""

    return len(_collect_keys(payload) & _FORBIDDEN_MECHANICAL_IDENTITY_KEYS)


def validate_semantic_planner_proposal(
    model_output: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and normalize the sparse, discriminated ordinary language."""

    if not isinstance(model_output, Mapping):
        raise SearchPlannerSemanticProposalError(
            "sparse planner proposal must be a JSON object",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.PROPOSAL_JSON_OBJECT_REQUIRED,
        )
    _reject_unsafe_payload(model_output)
    disposition = _required_enum(
        model_output,
        "disposition",
        allowed=_DISPOSITIONS,
        context="proposal",
        rule_id=SearchPlannerSemanticValidationRuleId.DISPOSITION_ENUM,
    )
    if disposition == "direct_simple":
        return _validate_direct_simple(model_output)
    return _validate_components_branch(model_output)


def compile_semantic_planner_proposal(
    semantic_proposal: Mapping[str, Any],
    *,
    user_query_text: str,
    requested_mode: str,
    qualified_multicomponent_structure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile accepted sparse meaning into the current rich compatibility state."""

    proposal = validate_semantic_planner_proposal(semantic_proposal)
    query = _normalized_external_text(
        user_query_text,
        context="authoritative user query",
        limit=12000,
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.AUTHORITATIVE_USER_QUERY_JSON_TYPE,
        nonempty_rule_id=SearchPlannerSemanticValidationRuleId.AUTHORITATIVE_USER_QUERY_NONEMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.AUTHORITATIVE_USER_QUERY_MAX_BOUND,
    )
    qualified_slots = _qualified_multicomponent_structure_slots(
        qualified_multicomponent_structure
    )
    if proposal["disposition"] == "direct_simple":
        if qualified_slots:
            _raise_qualified_multicomponent_structure_binding()
        if len(query) > _MAX_NEED_CHARS:
            raise SearchPlannerSemanticProposalError(
                "direct_simple requires the authoritative query to fit the current "
                "300-character compatibility query bound",
                semantic_validation_rule_id=(
                    SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_QUERY_COMPATIBILITY_BOUND
                ),
            )
        components_in = [
            {
                "need": query,
                "purpose": "user_facing_answer_target",
                "posture": "required",
                "support": "direct",
                "source": proposal.get("source"),
                "freshness": proposal.get("freshness"),
                "caveat": proposal.get("caveat"),
                "uncertainties": [],
            }
        ]
    else:
        components_in = list(proposal["components"])

    if qualified_slots:
        _validate_qualified_multicomponent_components(
            components=components_in,
            slots=qualified_slots,
        )

    key_to_component_id = {
        component["key"]: (
            qualified_slots[index - 1]["component_id"]
            if qualified_slots
            else f"component:{index:02d}"
        )
        for index, component in enumerate(components_in, start=1)
        if component.get("key")
    }
    mode_depth = inference_depth_ceiling_for_mode(requested_mode)
    semantic_slots: list[dict[str, Any]] = []
    answer_components: list[dict[str, Any]] = []
    source_obligations: list[dict[str, Any]] = []
    search_requirements: list[dict[str, Any]] = []
    aggregate_caveats: list[str] = []
    aggregate_prohibited: list[str] = []
    aggregate_normalization: list[str] = []
    factual_uncertainty = False
    confirmation_required = False
    obligation_ordinal = 0

    for index, component in enumerate(components_in, start=1):
        component_id = (
            qualified_slots[index - 1]["component_id"]
            if qualified_slots
            else f"component:{index:02d}"
        )
        uncertainties = list(component.get("uncertainties") or ())
        slot_ids: list[str] = []
        if uncertainties:
            for uncertainty_index, uncertainty in enumerate(uncertainties, start=1):
                slot_id = f"slot:{index:02d}:{uncertainty_index:02d}"
                slot_ids.append(slot_id)
                status = uncertainty["status"]
                materiality = uncertainty.get("materiality") or "material"
                user_confirmation = bool(uncertainty.get("user_confirmation_required", False))
                factual_uncertainty = factual_uncertainty or (status in {"ambiguous", "unresolved"})
                confirmation_required = confirmation_required or user_confirmation
                slot: dict[str, Any] = {
                    "slot_id": slot_id,
                    "slot_kind": uncertainty["kind"],
                    "status": status,
                    "materiality": materiality,
                    "user_confirmation_required": user_confirmation,
                }
                if uncertainty.get("candidates"):
                    slot["candidate_values"] = list(uncertainty["candidates"])
                if uncertainty.get("selected"):
                    slot["selected_value"] = uncertainty["selected"]
                semantic_slots.append(slot)
        else:
            slot_id = f"slot:{index:02d}:subject"
            slot_ids.append(slot_id)
            semantic_slots.append(
                {
                    "slot_id": slot_id,
                    "slot_kind": "unknown_or_other",
                    "status": "explicit",
                    "materiality": _component_materiality(component),
                    "user_confirmation_required": False,
                }
            )

        support = component.get("support") or "direct"
        support_kinds = {
            "direct": ["direct"],
            "inferred": ["inferred"],
            "direct_or_inferred": ["direct", "inferred"],
        }[support]
        dependency_ids = [key_to_component_id[local_key] for local_key in component.get("depends_on") or ()]
        owns_direct = "direct" in support_kinds
        owns_inferred = "inferred" in support_kinds
        obligation_ids: list[str] = []
        if owns_direct:
            obligation_ordinal += 1
            obligation_id = f"obligation:{obligation_ordinal:02d}"
            obligation_ids.append(obligation_id)
            source = component.get("source") or {}
            obligation: dict[str, Any] = {
                "candidate_id": obligation_id,
                "obligation_kind": source.get("kind") or "no_special_obligation",
                "component_candidate_ids": [component_id],
            }
            if source.get("strictness"):
                obligation["strictness"] = source["strictness"]
            source_obligations.append(obligation)

        posture = component.get("posture") or "required"
        purpose = component.get("purpose") or "user_facing_answer_target"
        acceptance_criterion = (
            "Direct support for the accepted component need."
            if support == "direct"
            else "Support the accepted inference from its declared dependencies."
            if support == "inferred"
            else "Direct support or an accepted inference from declared dependencies."
        )
        rich_component: dict[str, Any] = {
            "component_id": component_id,
            "component_revision": "1",
            "component_purpose": purpose,
            "user_facing_label": (
                f"Supporting premise {index}" if purpose == "supporting_premise" else f"Answer component {index}"
            ),
            "user_facing_question": component["need"],
            "requirement_posture": posture,
            "acceptance_criteria": [acceptance_criterion],
            "semantic_slot_ids": slot_ids,
            "source_obligation_candidate_ids": obligation_ids,
            "allowed_support_kinds": support_kinds,
            "max_inference_depth": mode_depth if owns_inferred else 0,
            "materiality": _component_materiality(component),
            "partial_answer_policy": ("allow_if_optional_only" if posture == "optional" else "qualify_visible_gap"),
        }
        if dependency_ids:
            rich_component["dependency_component_ids"] = dependency_ids
        if component.get("caveat"):
            rich_component["mandatory_caveats"] = [component["caveat"]]
            aggregate_caveats.append(component["caveat"])
        if component.get("prohibited_upgrade"):
            rich_component["prohibited_upgrades"] = [component["prohibited_upgrade"]]
            aggregate_prohibited.append(component["prohibited_upgrade"])
        if component.get("normalization"):
            rich_component["normalization_policy"] = component["normalization"]
            aggregate_normalization.append(component["normalization"])
        if component.get("calculation"):
            rich_component["calculation_policy"] = component["calculation"]
        answer_components.append(rich_component)

        if owns_direct:
            strategy = {
                "strategy_id": f"strategy:{index:02d}:primary",
                "component_id": component_id,
                "candidate_kind": "primary",
                "candidate_query_text": component["need"],
                "requested_role": "initial",
                "source_obligation_candidate_ids": obligation_ids,
                "distinct_need_justification": ("Initial candidate copied from the accepted semantic need."),
            }
            requirement: dict[str, Any] = {
                "component_id": component_id,
                "requirement_id": f"searchreq:{index:02d}",
                "requirement_summary": ("Find direct support for the accepted component need."),
                "source_obligation_candidate_ids": obligation_ids,
                "metadata": {"query_strategy_candidates": [strategy]},
            }
            if component.get("freshness"):
                requirement["recency_requirement"] = component["freshness"]
            search_requirements.append(requirement)

    first_target = next(
        component
        for component in components_in
        if (component.get("purpose") or "user_facing_answer_target") == "user_facing_answer_target"
    )
    material_ambiguity = (
        "user_confirmation_required"
        if confirmation_required
        else "factual_uncertainty_declared"
        if factual_uncertainty
        else "clear"
    )
    return {
        "question_meaning_summary": query[:420],
        "requested_output": first_target["need"],
        "semantic_slots": semantic_slots,
        "answer_components": answer_components,
        "source_obligation_candidates": source_obligations,
        "component_search_requirements": search_requirements,
        "material_ambiguity_posture": material_ambiguity,
        "mandatory_caveats": aggregate_caveats,
        "prohibited_upgrades": aggregate_prohibited,
        "normalization_obligations": aggregate_normalization,
        "assumptions": [],
        "unsupported_or_deferred_outputs": [],
    }


def _qualified_multicomponent_structure_slots(
    structure: Mapping[str, Any] | None,
) -> tuple[dict[str, str], ...]:
    """Validate code-owned component bindings supplied beside sparse meaning."""

    if structure is None:
        return ()
    if not isinstance(structure, Mapping):
        _raise_qualified_multicomponent_structure_binding()
    raw_slots = structure.get("component_slots")
    expected_count = structure.get("component_count")
    directive = _qualified_structure_text(
        structure.get("requested_synthesis_directive"),
        limit=360,
    )
    if (
        not directive
        or not isinstance(raw_slots, list)
        or not isinstance(expected_count, int)
        or expected_count != len(raw_slots)
        or not (2 <= expected_count <= _MAX_COMPONENTS)
        or structure.get("component_order_is_binding") is not True
        or structure.get("directive_is_not_an_answer_component") is not True
        or structure.get("additional_required_answer_targets_forbidden") is not True
    ):
        _raise_qualified_multicomponent_structure_binding()
    slots: list[dict[str, str]] = []
    for position, item in enumerate(raw_slots, start=1):
        if not isinstance(item, Mapping) or item.get("position") != position:
            _raise_qualified_multicomponent_structure_binding()
        component_id = _qualified_structure_text(item.get("component_id"), limit=160)
        question = _qualified_structure_text(
            item.get("user_facing_question"),
            limit=_MAX_NEED_CHARS,
        )
        if not component_id or not question:
            _raise_qualified_multicomponent_structure_binding()
        slots.append(
            {
                "component_id": component_id,
                "user_facing_question": question,
            }
        )
    if len({slot["component_id"] for slot in slots}) != len(slots):
        _raise_qualified_multicomponent_structure_binding()
    return tuple(slots)


def _qualified_structure_text(value: Any, *, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    if not text or len(text) > limit:
        return None
    return text


def _validate_qualified_multicomponent_components(
    *,
    components: Sequence[Mapping[str, Any]],
    slots: Sequence[Mapping[str, str]],
) -> None:
    """Reject model cardinality, ordering, target, or directive drift."""

    if len(components) != len(slots):
        _raise_qualified_multicomponent_structure_binding()
    for component, slot in zip(components, slots):
        if (
            component.get("need") != slot.get("user_facing_question")
            or component.get("purpose") not in {None, "user_facing_answer_target"}
            or component.get("posture") not in {None, "required"}
        ):
            _raise_qualified_multicomponent_structure_binding()


def _raise_qualified_multicomponent_structure_binding() -> None:
    raise SearchPlannerSemanticProposalError(
        "qualified multi-component structure binding failed closed",
        semantic_validation_rule_id=(
            SearchPlannerSemanticValidationRuleId.QUALIFIED_MULTICOMPONENT_STRUCTURE_BINDING
        ),
    )


def _validate_direct_simple(model_output: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"disposition", "source", "freshness", "caveat"}
    _reject_unknown_fields(
        model_output,
        allowed=allowed,
        context="direct_simple",
        semantic_validation_rule_id=(
            SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_WITH_COMPONENTS
            if "components" in model_output
            else SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL
        ),
    )
    result: dict[str, Any] = {"disposition": "direct_simple"}
    source = _optional_source(model_output.get("source"), context="direct_simple.source")
    if source:
        result["source"] = source
    freshness = _optional_text(
        model_output,
        "freshness",
        limit=_MAX_FRESHNESS_CHARS,
        context="direct_simple",
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_FRESHNESS_JSON_TYPE,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_FRESHNESS_OMIT_EMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_FRESHNESS_MAX_BOUND,
    )
    if freshness:
        result["freshness"] = freshness
    caveat = _optional_text(
        model_output,
        "caveat",
        limit=_MAX_CAVEAT_CHARS,
        context="direct_simple",
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_CAVEAT_JSON_TYPE,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_CAVEAT_OMIT_EMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.DIRECT_SIMPLE_CAVEAT_MAX_BOUND,
    )
    if caveat:
        result["caveat"] = caveat
    return result


def _validate_components_branch(model_output: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"disposition", "components"}
    _reject_unknown_fields(
        model_output,
        allowed=allowed,
        context="components branch",
        semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.COMPONENTS_DISALLOWED_TOP_LEVEL),
    )
    raw_components = model_output.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise SearchPlannerSemanticProposalError(
            "components disposition requires a nonempty components array",
            semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_NONEMPTY),
        )
    if len(raw_components) > _MAX_COMPONENTS:
        raise SearchPlannerSemanticProposalError(
            "components disposition exceeds the five-component ceiling",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_ARRAY_MAX_ITEMS,
        )
    components = [_validate_component(item, index=index) for index, item in enumerate(raw_components)]
    keyed: dict[str, int] = {}
    for index, component in enumerate(components):
        local_key = component.get("key")
        if not local_key:
            continue
        if local_key in keyed:
            raise SearchPlannerSemanticProposalError(
                f"duplicate proposal-local component key: {local_key}",
                semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.DUPLICATE_COMPONENT_LOCAL_KEY,
            )
        keyed[local_key] = index
    for index, component in enumerate(components):
        for local_key in component.get("depends_on") or ():
            if local_key not in keyed:
                raise SearchPlannerSemanticProposalError(
                    f"components[{index}].depends_on has unresolved local key",
                    semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.DEPENDENCY_LOCAL_KEY_RESOLUTION,
                )
            if local_key == component.get("key"):
                raise SearchPlannerSemanticProposalError(
                    f"components[{index}] must not depend on itself",
                    semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.DEPENDENCY_SELF_REFERENCE_FORBIDDEN,
                )
    if not any(
        (component.get("purpose") or "user_facing_answer_target") == "user_facing_answer_target"
        and (component.get("posture") or "required") == "required"
        for component in components
    ):
        raise SearchPlannerSemanticProposalError(
            "components disposition requires a required user-facing target",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENTS_REQUIRED_USER_FACING_TARGET,
        )
    return {"disposition": "components", "components": components}


def _validate_component(item: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] must be an object",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_OBJECT_REQUIRED,
        )
    allowed = {
        "key",
        "need",
        "purpose",
        "posture",
        "support",
        "depends_on",
        "source",
        "freshness",
        "uncertainties",
        "caveat",
        "prohibited_upgrade",
        "normalization",
        "calculation",
    }
    _reject_unknown_fields(
        item,
        allowed=allowed,
        context=f"components[{index}]",
        semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.COMPONENT_UNKNOWN_FIELD_FORBIDDEN),
    )
    need = _required_text(
        item,
        "need",
        limit=_MAX_NEED_CHARS,
        context=f"components[{index}]",
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_NEED_JSON_TYPE,
        nonempty_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_NEED_NONEMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_NEED_MAX_BOUND,
    )
    result: dict[str, Any] = {"need": need}
    purpose = _optional_enum(
        item,
        "purpose",
        allowed=_COMPONENT_PURPOSES,
        context=f"components[{index}]",
        enum_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_PURPOSE_ENUM,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_PURPOSE_OMIT_EMPTY,
    )
    if purpose:
        result["purpose"] = purpose
    posture = _optional_enum(
        item,
        "posture",
        allowed=_REQUIREMENT_POSTURES,
        context=f"components[{index}]",
        enum_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_POSTURE_ENUM,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_POSTURE_OMIT_EMPTY,
    )
    if posture:
        result["posture"] = posture
    support_value = _optional_enum(
        item,
        "support",
        allowed=_SUPPORT_VALUES,
        context=f"components[{index}]",
        enum_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_SUPPORT_ENUM,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_SUPPORT_OMIT_EMPTY,
    )
    if support_value:
        result["support"] = support_value
    local_key = _optional_text(
        item,
        "key",
        limit=_MAX_LOCAL_KEY_CHARS,
        context=f"components[{index}]",
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_KEY_JSON_TYPE,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_KEY_OMIT_EMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_KEY_MAX_BOUND,
    )
    if local_key:
        result["key"] = local_key
    dependencies = _optional_text_list(
        item,
        "depends_on",
        item_limit=_MAX_LOCAL_KEY_CHARS,
        maximum_items=_MAX_COMPONENTS,
        context=f"components[{index}]",
        array_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_ARRAY_REQUIRED,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_OMIT_EMPTY,
        max_items_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_MAX_ITEMS,
        item_json_type_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_ITEM_JSON_TYPE,
        item_text_bound_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_ITEM_TEXT_BOUND,
        uniqueness_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_DEPENDS_ON_UNIQUE_VALUES,
    )
    support = result.get("support") or "direct"
    if support == "direct" and dependencies:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] direct support must not declare depends_on",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.DIRECT_SUPPORT_FORBIDS_DEPENDS_ON,
        )
    if support in {"inferred", "direct_or_inferred"} and not dependencies:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] inferred support requires depends_on",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_REQUIRES_DEPENDS_ON,
        )
    if dependencies:
        result["depends_on"] = dependencies
    source = _optional_source(item.get("source"), context=f"components[{index}].source")
    if support == "inferred" and source:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] inferred-only support must not declare source",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_SOURCE,
        )
    if source:
        result["source"] = source
    freshness = _optional_text(
        item,
        "freshness",
        limit=_MAX_FRESHNESS_CHARS,
        context=f"components[{index}]",
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_FRESHNESS_JSON_TYPE,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_FRESHNESS_OMIT_EMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_FRESHNESS_MAX_BOUND,
    )
    if support == "inferred" and freshness:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] inferred-only support must not declare freshness",
            semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.INFERRED_SUPPORT_FORBIDS_FRESHNESS),
        )
    if freshness:
        result["freshness"] = freshness
    uncertainties = _optional_uncertainties(
        item.get("uncertainties"),
        context=f"components[{index}].uncertainties",
    )
    if uncertainties:
        result["uncertainties"] = uncertainties
    caveat = _optional_text(
        item,
        "caveat",
        limit=_MAX_CAVEAT_CHARS,
        context=f"components[{index}]",
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_CAVEAT_JSON_TYPE,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_CAVEAT_OMIT_EMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_CAVEAT_MAX_BOUND,
    )
    if caveat:
        result["caveat"] = caveat
    prohibited_upgrade = _optional_text(
        item,
        "prohibited_upgrade",
        limit=_MAX_CAVEAT_CHARS,
        context=f"components[{index}]",
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_PROHIBITED_UPGRADE_JSON_TYPE,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_PROHIBITED_UPGRADE_OMIT_EMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_PROHIBITED_UPGRADE_MAX_BOUND,
    )
    if prohibited_upgrade:
        result["prohibited_upgrade"] = prohibited_upgrade
    normalization = _optional_text(
        item,
        "normalization",
        limit=_MAX_POLICY_CHARS,
        context=f"components[{index}]",
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_NORMALIZATION_JSON_TYPE,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_NORMALIZATION_OMIT_EMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_NORMALIZATION_MAX_BOUND,
    )
    if normalization:
        result["normalization"] = normalization
    calculation = _optional_text(
        item,
        "calculation",
        limit=_MAX_POLICY_CHARS,
        context=f"components[{index}]",
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_CALCULATION_JSON_TYPE,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_CALCULATION_OMIT_EMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.COMPONENT_CALCULATION_MAX_BOUND,
    )
    if calculation:
        result["calculation"] = calculation
    if source and source.get("kind") == "source_bound_numeric" and not calculation:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] source_bound_numeric requires an explicit calculation posture",
            semantic_validation_rule_id=(
                SearchPlannerSemanticValidationRuleId.SOURCE_BOUND_NUMERIC_REQUIRES_CALCULATION
            ),
        )
    return result


def _optional_source(value: Any, *, context: str) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise SearchPlannerSemanticProposalError(
            f"{context} must be an object",
            semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.SOURCE_OBJECT_REQUIRED),
        )
    _reject_unknown_fields(
        value,
        allowed={"kind", "strictness"},
        context=context,
        semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.SOURCE_UNKNOWN_FIELD_FORBIDDEN),
    )
    kind = _required_enum(
        value,
        "kind",
        allowed=_SOURCE_KINDS,
        context=context,
        rule_id=SearchPlannerSemanticValidationRuleId.SOURCE_KIND_ENUM,
    )
    result = {"kind": kind}
    strictness = _optional_enum(
        value,
        "strictness",
        allowed=_SOURCE_STRICTNESSES,
        context=context,
        enum_rule_id=SearchPlannerSemanticValidationRuleId.SOURCE_STRICTNESS_ENUM,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.SOURCE_STRICTNESS_OMIT_EMPTY,
    )
    if strictness:
        result["strictness"] = strictness
    return result


def _optional_uncertainties(value: Any, *, context: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SearchPlannerSemanticProposalError(
            f"{context} must be an array",
            semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.COMPONENT_UNCERTAINTIES_ARRAY_REQUIRED),
        )
    if not value:
        raise SearchPlannerSemanticProposalError(
            f"{context} must be omitted instead of empty",
            semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.COMPONENT_UNCERTAINTIES_OMIT_EMPTY),
        )
    if len(value) > _MAX_UNCERTAINTIES_PER_COMPONENT:
        raise SearchPlannerSemanticProposalError(
            f"{context} exceeds the five-item ceiling",
            semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.COMPONENT_UNCERTAINTIES_MAX_ITEMS),
        )
    return [_validate_uncertainty(item, context=f"{context}[{index}]") for index, item in enumerate(value)]


def _validate_uncertainty(item: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise SearchPlannerSemanticProposalError(
            f"{context} must be an object",
            semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.UNCERTAINTY_OBJECT_REQUIRED),
        )
    _reject_unknown_fields(
        item,
        allowed={
            "kind",
            "status",
            "candidates",
            "selected",
            "user_confirmation_required",
            "materiality",
        },
        context=context,
        semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.UNCERTAINTY_UNKNOWN_FIELD_FORBIDDEN),
    )
    status = _required_enum(
        item,
        "status",
        allowed=_UNCERTAINTY_STATUSES,
        context=context,
        rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_STATUS_ENUM,
    )
    result: dict[str, Any] = {
        "kind": _required_enum(
            item,
            "kind",
            allowed=_UNCERTAINTY_KINDS,
            context=context,
            rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_KIND_ENUM,
        ),
        "status": status,
    }
    candidates = _optional_text_list(
        item,
        "candidates",
        item_limit=_MAX_UNCERTAINTY_VALUE_CHARS,
        maximum_items=8,
        context=context,
        array_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_ARRAY_REQUIRED,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_OMIT_EMPTY,
        max_items_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_MAX_ITEMS,
        item_json_type_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_ITEM_JSON_TYPE,
        item_text_bound_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_ITEM_TEXT_BOUND,
        uniqueness_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_CANDIDATES_UNIQUE_VALUES,
    )
    if candidates:
        result["candidates"] = candidates
    selected = _optional_text(
        item,
        "selected",
        limit=_MAX_UNCERTAINTY_VALUE_CHARS,
        context=context,
        json_type_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_SELECTED_JSON_TYPE,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_SELECTED_OMIT_EMPTY,
        max_bound_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_SELECTED_MAX_BOUND,
    )
    if selected and status in {"ambiguous", "unresolved"}:
        raise SearchPlannerSemanticProposalError(
            f"{context} unresolved/ambiguous status must not claim selected",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.UNRESOLVED_AMBIGUOUS_FORBIDS_SELECTED,
        )
    if selected and candidates and selected not in candidates:
        raise SearchPlannerSemanticProposalError(
            f"{context} selected must match one declared candidate",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.SELECTED_MUST_BE_DECLARED_CANDIDATE,
        )
    if selected:
        result["selected"] = selected
    confirmation = _optional_bool(
        item,
        "user_confirmation_required",
        context=context,
        json_type_rule_id=(SearchPlannerSemanticValidationRuleId.UNCERTAINTY_USER_CONFIRMATION_REQUIRED_JSON_TYPE),
    )
    materiality = _optional_enum(
        item,
        "materiality",
        allowed=_MATERIALITY_VALUES,
        context=context,
        enum_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_MATERIALITY_ENUM,
        empty_omission_rule_id=SearchPlannerSemanticValidationRuleId.UNCERTAINTY_MATERIALITY_OMIT_EMPTY,
    )
    effective_materiality = materiality or "material"
    if confirmation is True and (status not in {"ambiguous", "unresolved"} or effective_materiality != "material"):
        raise SearchPlannerSemanticProposalError(
            f"{context} confirmation requires material unresolved/ambiguous status",
            semantic_validation_rule_id=(
                SearchPlannerSemanticValidationRuleId.CONFIRMATION_REQUIRES_MATERIAL_UNRESOLVED
            ),
        )
    if confirmation is not None:
        result["user_confirmation_required"] = confirmation
    if materiality:
        result["materiality"] = materiality
    return result


def _component_materiality(component: Mapping[str, Any]) -> str:
    if any(
        uncertainty.get("materiality", "material") == "material" for uncertainty in component.get("uncertainties") or ()
    ):
        return "material"
    return "non_material" if component.get("posture") == "optional" else "material"


def _required_text(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int,
    context: str,
    json_type_rule_id: SearchPlannerSemanticValidationRuleId,
    nonempty_rule_id: SearchPlannerSemanticValidationRuleId,
    max_bound_rule_id: SearchPlannerSemanticValidationRuleId,
) -> str:
    if key not in mapping or not isinstance(mapping[key], str):
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} must be a JSON string",
            semantic_validation_rule_id=json_type_rule_id,
        )
    value = _normalize_whitespace(mapping[key])
    if not value:
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} must be nonempty",
            semantic_validation_rule_id=nonempty_rule_id,
        )
    if len(value) > limit:
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} exceeds {limit} characters",
            semantic_validation_rule_id=max_bound_rule_id,
        )
    return value


def _optional_text(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int,
    context: str,
    json_type_rule_id: SearchPlannerSemanticValidationRuleId,
    empty_omission_rule_id: SearchPlannerSemanticValidationRuleId,
    max_bound_rule_id: SearchPlannerSemanticValidationRuleId,
) -> str | None:
    if key not in mapping:
        return None
    if not isinstance(mapping[key], str):
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} must be a JSON string when present",
            semantic_validation_rule_id=json_type_rule_id,
        )
    value = _normalize_whitespace(mapping[key])
    if not value:
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} must be omitted instead of empty",
            semantic_validation_rule_id=empty_omission_rule_id,
        )
    if len(value) > limit:
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} exceeds {limit} characters",
            semantic_validation_rule_id=max_bound_rule_id,
        )
    return value


def _required_enum(
    mapping: Mapping[str, Any],
    key: str,
    *,
    allowed: frozenset[str],
    context: str,
    rule_id: SearchPlannerSemanticValidationRuleId,
) -> str:
    value = _required_text(
        mapping,
        key,
        limit=80,
        context=context,
        json_type_rule_id=rule_id,
        nonempty_rule_id=rule_id,
        max_bound_rule_id=rule_id,
    )
    if value not in allowed:
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} is not an allowed value",
            semantic_validation_rule_id=rule_id,
        )
    return value


def _optional_enum(
    mapping: Mapping[str, Any],
    key: str,
    *,
    allowed: frozenset[str],
    context: str,
    enum_rule_id: SearchPlannerSemanticValidationRuleId,
    empty_omission_rule_id: SearchPlannerSemanticValidationRuleId,
) -> str | None:
    value = _optional_text(
        mapping,
        key,
        limit=80,
        context=context,
        json_type_rule_id=enum_rule_id,
        empty_omission_rule_id=empty_omission_rule_id,
        max_bound_rule_id=enum_rule_id,
    )
    if value is not None and value not in allowed:
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} is not an allowed value",
            semantic_validation_rule_id=enum_rule_id,
        )
    return value


def _optional_bool(
    mapping: Mapping[str, Any],
    key: str,
    *,
    context: str,
    json_type_rule_id: SearchPlannerSemanticValidationRuleId,
) -> bool | None:
    if key not in mapping:
        return None
    value = mapping[key]
    if not isinstance(value, bool):
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} must be a JSON boolean",
            semantic_validation_rule_id=json_type_rule_id,
        )
    return value


def _optional_text_list(
    mapping: Mapping[str, Any],
    key: str,
    *,
    item_limit: int,
    maximum_items: int,
    context: str,
    array_rule_id: SearchPlannerSemanticValidationRuleId,
    empty_omission_rule_id: SearchPlannerSemanticValidationRuleId,
    max_items_rule_id: SearchPlannerSemanticValidationRuleId,
    item_json_type_rule_id: SearchPlannerSemanticValidationRuleId,
    item_text_bound_rule_id: SearchPlannerSemanticValidationRuleId,
    uniqueness_rule_id: SearchPlannerSemanticValidationRuleId,
) -> list[str]:
    if key not in mapping:
        return []
    raw = mapping[key]
    if not isinstance(raw, list):
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} must be an array",
            semantic_validation_rule_id=array_rule_id,
        )
    if not raw:
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} must be omitted instead of empty",
            semantic_validation_rule_id=empty_omission_rule_id,
        )
    if len(raw) > maximum_items:
        raise SearchPlannerSemanticProposalError(
            f"{context}.{key} exceeds the item ceiling",
            semantic_validation_rule_id=max_items_rule_id,
        )
    values: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str):
            raise SearchPlannerSemanticProposalError(
                f"{context}.{key}[{index}] must be a JSON string",
                semantic_validation_rule_id=item_json_type_rule_id,
            )
        value = _normalize_whitespace(item)
        if not value or len(value) > item_limit:
            raise SearchPlannerSemanticProposalError(
                f"{context}.{key}[{index}] is empty or over the text bound",
                semantic_validation_rule_id=item_text_bound_rule_id,
            )
        if value in values:
            raise SearchPlannerSemanticProposalError(
                f"{context}.{key} contains a duplicate value",
                semantic_validation_rule_id=uniqueness_rule_id,
            )
        values.append(value)
    return values


def _normalized_external_text(
    value: Any,
    *,
    context: str,
    limit: int,
    json_type_rule_id: SearchPlannerSemanticValidationRuleId,
    nonempty_rule_id: SearchPlannerSemanticValidationRuleId,
    max_bound_rule_id: SearchPlannerSemanticValidationRuleId,
) -> str:
    if not isinstance(value, str):
        raise SearchPlannerSemanticProposalError(
            f"{context} must be a string",
            semantic_validation_rule_id=json_type_rule_id,
        )
    normalized = _normalize_whitespace(value)
    if not normalized:
        raise SearchPlannerSemanticProposalError(
            f"{context} must be nonempty",
            semantic_validation_rule_id=nonempty_rule_id,
        )
    if len(normalized) > limit:
        raise SearchPlannerSemanticProposalError(
            f"{context} exceeds {limit} characters",
            semantic_validation_rule_id=max_bound_rule_id,
        )
    return normalized


def _reject_unknown_fields(
    mapping: Mapping[str, Any],
    *,
    allowed: set[str],
    context: str,
    semantic_validation_rule_id: SearchPlannerSemanticValidationRuleId,
) -> None:
    unknown = sorted(str(key) for key in mapping if key not in allowed)
    if unknown:
        raise SearchPlannerSemanticProposalError(
            f"{context} has unknown fields: " + ", ".join(unknown),
            semantic_validation_rule_id=semantic_validation_rule_id,
        )


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_collect_keys(nested))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for nested in value:
            keys.update(_collect_keys(nested))
        return keys
    return set()


def _reject_unsafe_payload(payload: Mapping[str, Any]) -> None:
    keys = _collect_keys(payload)
    normalized = {key.strip().casefold() for key in keys}
    sensitive = sorted(key for key in normalized if key.startswith("raw_") or key in _SENSITIVE_KEYS)
    if sensitive:
        raise SearchPlannerSemanticProposalError(
            "sparse planner proposal contains unsafe/raw/private fields",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.SENSITIVE_FIELD_FORBIDDEN,
        )
    mechanical = sorted(keys & _FORBIDDEN_MECHANICAL_IDENTITY_KEYS)
    if mechanical:
        raise SearchPlannerSemanticProposalError(
            "sparse planner proposal must not author mechanical identity fields",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.MECHANICAL_IDENTITY_FIELD_FORBIDDEN,
        )
    rich = sorted(keys & _FORBIDDEN_RICH_KEYS)
    if rich:
        raise SearchPlannerSemanticProposalError(
            "sparse planner proposal must not author rich administrative fields",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.RICH_ADMINISTRATIVE_FIELD_FORBIDDEN,
        )
    authority = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if authority:
        raise SearchPlannerSemanticProposalError(
            "sparse planner proposal must not claim closed authority",
            semantic_validation_rule_id=SearchPlannerSemanticValidationRuleId.CLOSED_AUTHORITY_FIELD_FORBIDDEN,
        )
    provider = sorted(keys & _FORBIDDEN_PROVIDER_KEYS)
    if provider:
        raise SearchPlannerSemanticProposalError(
            "sparse planner proposal must not select provider/model/routing authority",
            semantic_validation_rule_id=(SearchPlannerSemanticValidationRuleId.PROVIDER_ROUTING_FIELD_FORBIDDEN),
        )


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


__all__ = [
    "SEARCH_PLANNER_MODEL_VISIBLE_SCHEMA",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_COMPONENTS_BRANCH_FORBIDDEN_TOP_LEVEL_FIELDS",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_COMPONENTS_BRANCH_REQUIRED_FIELDS",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_CONTRACT_FORMAT",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_DIRECT_SIMPLE_OPTIONAL_FIELDS",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_OPTIONAL_TOP_LEVEL_FIELDS",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_REQUIRED_TOP_LEVEL_FIELDS",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA_VERSION",
    "SEARCH_PLANNER_SEMANTIC_VALIDATION_RULE_REGISTRY",
    "SearchPlannerBranchFieldSetDetail",
    "SearchPlannerSemanticProposalError",
    "SearchPlannerSemanticProposalSubtype",
    "SearchPlannerSemanticValidationRule",
    "SearchPlannerSemanticValidationRuleId",
    "build_search_planner_model_visible_schema",
    "compile_semantic_planner_proposal",
    "count_model_authored_mechanical_identity_keys",
    "is_semantic_planner_proposal",
    "validate_semantic_planner_proposal",
]
