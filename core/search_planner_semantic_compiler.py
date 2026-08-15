"""Validate sparse SearchPlanner meaning and compile current rich compatibility.

The ordinary model authors only semantic differences.  This module owns the one
compact prompt-visible contract, validates it fail closed, and deterministically
constructs the rich state still required by Phase-1 downstream consumers.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

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
            "empty_optional_rule": (
                "components must be a nonempty array; omit empty nested optionals"
            ),
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
    NESTED_DISALLOWED_FIELD = "nested_disallowed_field"


class SearchPlannerSemanticProposalError(ValueError):
    """Fail-closed sparse semantic proposal validation or compilation error."""

    def __init__(
        self,
        message: str,
        *,
        subtype: SearchPlannerSemanticProposalSubtype | None = None,
        branch_field_set_detail: SearchPlannerBranchFieldSetDetail | None = None,
    ) -> None:
        resolved_subtype = subtype or classify_semantic_proposal_subtype(message)
        if branch_field_set_detail is not None and not isinstance(
            branch_field_set_detail,
            SearchPlannerBranchFieldSetDetail,
        ):
            raise TypeError("branch_field_set_detail must be a closed enum")
        if resolved_subtype is SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET:
            if branch_field_set_detail is None:
                raise ValueError(
                    "branch_field_set_detail is required for branch_field_set errors"
                )
        elif branch_field_set_detail is not None:
            raise ValueError(
                "branch_field_set_detail is reserved for branch_field_set errors"
            )
        super().__init__(message)
        self.subtype = resolved_subtype
        self.branch_field_set_detail = branch_field_set_detail


def classify_semantic_proposal_subtype(message: str) -> SearchPlannerSemanticProposalSubtype:
    """Map an owned validator message to one closed privacy-safe M02 family."""

    text = str(message)
    if any(
        token in text
        for token in (
            "unsafe/raw/private fields",
            "must not author mechanical identity fields",
            "must not author rich administrative fields",
            "must not claim closed authority",
            "must not select provider/model/routing authority",
        )
    ):
        return SearchPlannerSemanticProposalSubtype.FORBIDDEN_SURFACE
    if "must be omitted instead of empty" in text:
        return SearchPlannerSemanticProposalSubtype.OMISSION_CONTRACT
    if "has unknown fields" in text or text.startswith(
        "components disposition requires a nonempty components array"
    ):
        return SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET
    if any(
        token in text
        for token in (
            "requires a required user-facing target",
            "must not depend on itself",
            "has unresolved local key",
            "direct support must not declare depends_on",
            "inferred support requires depends_on",
            "inferred-only support must not declare source",
            "inferred-only support must not declare freshness",
            "unresolved/ambiguous status must not claim selected",
            "selected must match one declared candidate",
            "confirmation requires material unresolved/ambiguous status",
            "direct_simple requires the authoritative query to fit",
        )
    ):
        return SearchPlannerSemanticProposalSubtype.CROSS_FIELD_CONDITION
    return SearchPlannerSemanticProposalSubtype.TYPE_ENUM_OR_BOUND


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
        raise SearchPlannerSemanticProposalError("sparse planner proposal must be a JSON object")
    _reject_unsafe_payload(model_output)
    disposition = _required_enum(
        model_output,
        "disposition",
        allowed=_DISPOSITIONS,
        context="proposal",
    )
    if disposition == "direct_simple":
        return _validate_direct_simple(model_output)
    return _validate_components_branch(model_output)


def compile_semantic_planner_proposal(
    semantic_proposal: Mapping[str, Any],
    *,
    user_query_text: str,
    requested_mode: str,
) -> dict[str, Any]:
    """Compile accepted sparse meaning into the current rich compatibility state."""

    proposal = validate_semantic_planner_proposal(semantic_proposal)
    query = _normalized_external_text(
        user_query_text,
        context="authoritative user query",
        limit=12000,
    )
    if proposal["disposition"] == "direct_simple":
        if len(query) > _MAX_NEED_CHARS:
            raise SearchPlannerSemanticProposalError(
                "direct_simple requires the authoritative query to fit the current "
                "300-character compatibility query bound"
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

    key_to_component_id = {
        component["key"]: f"component:{index:02d}"
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
        component_id = f"component:{index:02d}"
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
                "distinct_need_justification": (
                    "Initial candidate copied from the accepted semantic need."
                ),
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


def _validate_direct_simple(model_output: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"disposition", "source", "freshness", "caveat"}
    _reject_unknown_fields(
        model_output,
        allowed=allowed,
        context="direct_simple",
        branch_field_set_detail=(
            SearchPlannerBranchFieldSetDetail.DIRECT_SIMPLE_WITH_COMPONENTS
            if "components" in model_output
            else SearchPlannerBranchFieldSetDetail.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL
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
    )
    if freshness:
        result["freshness"] = freshness
    caveat = _optional_text(
        model_output,
        "caveat",
        limit=_MAX_CAVEAT_CHARS,
        context="direct_simple",
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
        branch_field_set_detail=(
            SearchPlannerBranchFieldSetDetail.COMPONENTS_DISALLOWED_TOP_LEVEL
        ),
    )
    raw_components = model_output.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise SearchPlannerSemanticProposalError(
            "components disposition requires a nonempty components array",
            subtype=SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET,
            branch_field_set_detail=(
                SearchPlannerBranchFieldSetDetail.COMPONENTS_REQUIRED_NONEMPTY
            ),
        )
    if len(raw_components) > _MAX_COMPONENTS:
        raise SearchPlannerSemanticProposalError("components disposition exceeds the five-component ceiling")
    components = [_validate_component(item, index=index) for index, item in enumerate(raw_components)]
    keyed: dict[str, int] = {}
    for index, component in enumerate(components):
        local_key = component.get("key")
        if not local_key:
            continue
        if local_key in keyed:
            raise SearchPlannerSemanticProposalError(f"duplicate proposal-local component key: {local_key}")
        keyed[local_key] = index
    for index, component in enumerate(components):
        for local_key in component.get("depends_on") or ():
            if local_key not in keyed:
                raise SearchPlannerSemanticProposalError(f"components[{index}].depends_on has unresolved local key")
            if local_key == component.get("key"):
                raise SearchPlannerSemanticProposalError(f"components[{index}] must not depend on itself")
    if not any(
        (component.get("purpose") or "user_facing_answer_target") == "user_facing_answer_target"
        and (component.get("posture") or "required") == "required"
        for component in components
    ):
        raise SearchPlannerSemanticProposalError("components disposition requires a required user-facing target")
    return {"disposition": "components", "components": components}


def _validate_component(item: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise SearchPlannerSemanticProposalError(f"components[{index}] must be an object")
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
        branch_field_set_detail=(
            SearchPlannerBranchFieldSetDetail.NESTED_DISALLOWED_FIELD
        ),
    )
    need = _required_text(
        item,
        "need",
        limit=_MAX_NEED_CHARS,
        context=f"components[{index}]",
    )
    result: dict[str, Any] = {"need": need}
    for key, allowed_values in (
        ("purpose", _COMPONENT_PURPOSES),
        ("posture", _REQUIREMENT_POSTURES),
        ("support", _SUPPORT_VALUES),
    ):
        value = _optional_enum(
            item,
            key,
            allowed=allowed_values,
            context=f"components[{index}]",
        )
        if value:
            result[key] = value
    local_key = _optional_text(
        item,
        "key",
        limit=_MAX_LOCAL_KEY_CHARS,
        context=f"components[{index}]",
    )
    if local_key:
        result["key"] = local_key
    dependencies = _optional_text_list(
        item,
        "depends_on",
        item_limit=_MAX_LOCAL_KEY_CHARS,
        maximum_items=_MAX_COMPONENTS,
        context=f"components[{index}]",
    )
    support = result.get("support") or "direct"
    if support == "direct" and dependencies:
        raise SearchPlannerSemanticProposalError(f"components[{index}] direct support must not declare depends_on")
    if support in {"inferred", "direct_or_inferred"} and not dependencies:
        raise SearchPlannerSemanticProposalError(f"components[{index}] inferred support requires depends_on")
    if dependencies:
        result["depends_on"] = dependencies
    source = _optional_source(item.get("source"), context=f"components[{index}].source")
    if support == "inferred" and source:
        raise SearchPlannerSemanticProposalError(f"components[{index}] inferred-only support must not declare source")
    if source:
        result["source"] = source
    freshness = _optional_text(
        item,
        "freshness",
        limit=_MAX_FRESHNESS_CHARS,
        context=f"components[{index}]",
    )
    if support == "inferred" and freshness:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] inferred-only support must not declare freshness"
        )
    if freshness:
        result["freshness"] = freshness
    uncertainties = _optional_uncertainties(
        item.get("uncertainties"),
        context=f"components[{index}].uncertainties",
    )
    if uncertainties:
        result["uncertainties"] = uncertainties
    for key, limit in (
        ("caveat", _MAX_CAVEAT_CHARS),
        ("prohibited_upgrade", _MAX_CAVEAT_CHARS),
        ("normalization", _MAX_POLICY_CHARS),
        ("calculation", _MAX_POLICY_CHARS),
    ):
        value = _optional_text(
            item,
            key,
            limit=limit,
            context=f"components[{index}]",
        )
        if value:
            result[key] = value
    return result


def _optional_source(value: Any, *, context: str) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise SearchPlannerSemanticProposalError(f"{context} must be an object")
    _reject_unknown_fields(
        value,
        allowed={"kind", "strictness"},
        context=context,
        branch_field_set_detail=(
            SearchPlannerBranchFieldSetDetail.NESTED_DISALLOWED_FIELD
        ),
    )
    kind = _required_enum(value, "kind", allowed=_SOURCE_KINDS, context=context)
    result = {"kind": kind}
    strictness = _optional_enum(
        value,
        "strictness",
        allowed=_SOURCE_STRICTNESSES,
        context=context,
    )
    if strictness:
        result["strictness"] = strictness
    return result


def _optional_uncertainties(value: Any, *, context: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SearchPlannerSemanticProposalError(f"{context} must be an array")
    if not value:
        raise SearchPlannerSemanticProposalError(f"{context} must be omitted instead of empty")
    if len(value) > _MAX_UNCERTAINTIES_PER_COMPONENT:
        raise SearchPlannerSemanticProposalError(f"{context} exceeds the five-item ceiling")
    return [_validate_uncertainty(item, context=f"{context}[{index}]") for index, item in enumerate(value)]


def _validate_uncertainty(item: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise SearchPlannerSemanticProposalError(f"{context} must be an object")
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
        branch_field_set_detail=(
            SearchPlannerBranchFieldSetDetail.NESTED_DISALLOWED_FIELD
        ),
    )
    status = _required_enum(
        item,
        "status",
        allowed=_UNCERTAINTY_STATUSES,
        context=context,
    )
    result: dict[str, Any] = {
        "kind": _required_enum(
            item,
            "kind",
            allowed=_UNCERTAINTY_KINDS,
            context=context,
        ),
        "status": status,
    }
    candidates = _optional_text_list(
        item,
        "candidates",
        item_limit=_MAX_UNCERTAINTY_VALUE_CHARS,
        maximum_items=8,
        context=context,
    )
    if candidates:
        result["candidates"] = candidates
    selected = _optional_text(
        item,
        "selected",
        limit=_MAX_UNCERTAINTY_VALUE_CHARS,
        context=context,
    )
    if selected and status in {"ambiguous", "unresolved"}:
        raise SearchPlannerSemanticProposalError(f"{context} unresolved/ambiguous status must not claim selected")
    if selected and candidates and selected not in candidates:
        raise SearchPlannerSemanticProposalError(f"{context} selected must match one declared candidate")
    if selected:
        result["selected"] = selected
    confirmation = _optional_bool(item, "user_confirmation_required", context=context)
    materiality = _optional_enum(
        item,
        "materiality",
        allowed=_MATERIALITY_VALUES,
        context=context,
    )
    effective_materiality = materiality or "material"
    if confirmation is True and (status not in {"ambiguous", "unresolved"} or effective_materiality != "material"):
        raise SearchPlannerSemanticProposalError(
            f"{context} confirmation requires material unresolved/ambiguous status"
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
) -> str:
    if key not in mapping or not isinstance(mapping[key], str):
        raise SearchPlannerSemanticProposalError(f"{context}.{key} must be a JSON string")
    value = _normalize_whitespace(mapping[key])
    if not value:
        raise SearchPlannerSemanticProposalError(f"{context}.{key} must be nonempty")
    if len(value) > limit:
        raise SearchPlannerSemanticProposalError(f"{context}.{key} exceeds {limit} characters")
    return value


def _optional_text(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int,
    context: str,
) -> str | None:
    if key not in mapping:
        return None
    if not isinstance(mapping[key], str):
        raise SearchPlannerSemanticProposalError(f"{context}.{key} must be a JSON string when present")
    value = _normalize_whitespace(mapping[key])
    if not value:
        raise SearchPlannerSemanticProposalError(f"{context}.{key} must be omitted instead of empty")
    if len(value) > limit:
        raise SearchPlannerSemanticProposalError(f"{context}.{key} exceeds {limit} characters")
    return value


def _required_enum(
    mapping: Mapping[str, Any],
    key: str,
    *,
    allowed: frozenset[str],
    context: str,
) -> str:
    value = _required_text(mapping, key, limit=80, context=context)
    if value not in allowed:
        raise SearchPlannerSemanticProposalError(f"{context}.{key} is not an allowed value")
    return value


def _optional_enum(
    mapping: Mapping[str, Any],
    key: str,
    *,
    allowed: frozenset[str],
    context: str,
) -> str | None:
    value = _optional_text(mapping, key, limit=80, context=context)
    if value is not None and value not in allowed:
        raise SearchPlannerSemanticProposalError(f"{context}.{key} is not an allowed value")
    return value


def _optional_bool(
    mapping: Mapping[str, Any],
    key: str,
    *,
    context: str,
) -> bool | None:
    if key not in mapping:
        return None
    value = mapping[key]
    if not isinstance(value, bool):
        raise SearchPlannerSemanticProposalError(f"{context}.{key} must be a JSON boolean")
    return value


def _optional_text_list(
    mapping: Mapping[str, Any],
    key: str,
    *,
    item_limit: int,
    maximum_items: int,
    context: str,
) -> list[str]:
    if key not in mapping:
        return []
    raw = mapping[key]
    if not isinstance(raw, list):
        raise SearchPlannerSemanticProposalError(f"{context}.{key} must be an array")
    if not raw:
        raise SearchPlannerSemanticProposalError(f"{context}.{key} must be omitted instead of empty")
    if len(raw) > maximum_items:
        raise SearchPlannerSemanticProposalError(f"{context}.{key} exceeds the item ceiling")
    values: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str):
            raise SearchPlannerSemanticProposalError(f"{context}.{key}[{index}] must be a JSON string")
        value = _normalize_whitespace(item)
        if not value or len(value) > item_limit:
            raise SearchPlannerSemanticProposalError(f"{context}.{key}[{index}] is empty or over the text bound")
        if value in values:
            raise SearchPlannerSemanticProposalError(f"{context}.{key} contains a duplicate value")
        values.append(value)
    return values


def _normalized_external_text(value: Any, *, context: str, limit: int) -> str:
    if not isinstance(value, str):
        raise SearchPlannerSemanticProposalError(f"{context} must be a string")
    normalized = _normalize_whitespace(value)
    if not normalized:
        raise SearchPlannerSemanticProposalError(f"{context} must be nonempty")
    if len(normalized) > limit:
        raise SearchPlannerSemanticProposalError(f"{context} exceeds {limit} characters")
    return normalized


def _reject_unknown_fields(
    mapping: Mapping[str, Any],
    *,
    allowed: set[str],
    context: str,
    branch_field_set_detail: SearchPlannerBranchFieldSetDetail,
) -> None:
    unknown = sorted(str(key) for key in mapping if key not in allowed)
    if unknown:
        raise SearchPlannerSemanticProposalError(
            f"{context} has unknown fields: " + ", ".join(unknown),
            subtype=SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET,
            branch_field_set_detail=branch_field_set_detail,
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
        raise SearchPlannerSemanticProposalError("sparse planner proposal contains unsafe/raw/private fields")
    mechanical = sorted(keys & _FORBIDDEN_MECHANICAL_IDENTITY_KEYS)
    if mechanical:
        raise SearchPlannerSemanticProposalError("sparse planner proposal must not author mechanical identity fields")
    rich = sorted(keys & _FORBIDDEN_RICH_KEYS)
    if rich:
        raise SearchPlannerSemanticProposalError("sparse planner proposal must not author rich administrative fields")
    authority = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if authority:
        raise SearchPlannerSemanticProposalError("sparse planner proposal must not claim closed authority")
    provider = sorted(keys & _FORBIDDEN_PROVIDER_KEYS)
    if provider:
        raise SearchPlannerSemanticProposalError(
            "sparse planner proposal must not select provider/model/routing authority"
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
    "SearchPlannerBranchFieldSetDetail",
    "SearchPlannerSemanticProposalError",
    "SearchPlannerSemanticProposalSubtype",
    "build_search_planner_model_visible_schema",
    "classify_semantic_proposal_subtype",
    "compile_semantic_planner_proposal",
    "count_model_authored_mechanical_identity_keys",
    "is_semantic_planner_proposal",
    "validate_semantic_planner_proposal",
]
