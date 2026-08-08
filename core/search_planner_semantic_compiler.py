"""Semantic SearchPlanner proposal validation and deterministic rich compilation.

Model authorship is limited to consumer-required semantic intent. This module
validates that small proposal, then compiles it into the existing rich Planner
representation that ``validate_and_sanitize_model_output`` already accepts.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.initial_query_allocation_policy import (
    DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
)
from core.search_planner_model_prompt import (
    SEARCH_PLANNER_MODEL_COMPONENT_PURPOSES,
    SEARCH_PLANNER_MODEL_MATERIALITY_VALUES,
    SEARCH_PLANNER_MODEL_PARTIAL_ANSWER_POLICIES,
    SEARCH_PLANNER_MODEL_QUERY_ROLES,
    SEARCH_PLANNER_MODEL_RECON_POSTURES,
    SEARCH_PLANNER_MODEL_REQUIREMENT_POSTURES,
    SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_KINDS,
    SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_STATUSES,
    SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_KINDS,
    SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_STRICTNESSES,
    SEARCH_PLANNER_MODEL_STRICT_JSON_OUTPUT_CONTRACT,
    SEARCH_PLANNER_MODEL_SUPPORT_KINDS,
    SEARCH_PLANNER_MODEL_TEXT_LIMITS,
)
from core.search_planner_model_prompt import (
    object_contract as _object_contract,
)
from core.search_planner_model_prompt import (
    text_array_contract as _text_array_contract,
)
from core.search_planner_model_prompt import (
    text_contract as _text_contract,
)
from core.search_planner_runtime import SEARCH_PLANNER_MAX_ANSWER_COMPONENTS

SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA_VERSION = (
    "search_planner_semantic_proposal_v1"
)
SEARCH_PLANNER_SEMANTIC_PROPOSAL_CONTRACT_FORMAT = (
    "search_planner_semantic_proposal_v1"
)

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
    }
)

# Reuse the installed Scout ambiguity-dimension vocabulary; do not invent a new ontology.
SEARCH_PLANNER_SEMANTIC_RECON_DIMENSION_KINDS = frozenset(
    {
        "entity_identity",
        "jurisdiction",
        "time_version_currentness",
        "rename_alias",
        "official_target_direction",
        "unknown_or_other",
    }
)

_RECON_DIMENSION_KIND_TO_QUERY_KIND = {
    "entity_identity": "all_time",
    "jurisdiction": "jurisdiction_probe",
    "time_version_currentness": "recent_current",
    "rename_alias": "alias_probe",
    "official_target_direction": "official_domain_probe",
    "unknown_or_other": "unknown_or_other",
}

_SEMANTIC_RECON_DIMENSION_CEILING = (
    DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY.recon_candidate_ceiling_per_affected_component
)

_FORBIDDEN_TOP_LEVEL_KEYS = frozenset(
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

_FORBIDDEN_QUERY_AUTHORITY_KEYS = frozenset(
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
    }
)

SEARCH_PLANNER_SEMANTIC_PROPOSAL_REQUIRED_TOP_LEVEL_FIELDS = (
    "interpretation",
    "components",
)
SEARCH_PLANNER_SEMANTIC_PROPOSAL_OPTIONAL_TOP_LEVEL_FIELDS = (
    "material_ambiguity",
    "caveats",
    "prohibited_upgrades",
    "assumptions",
    "normalization_notes",
    "deferred_outputs",
)

_REQUIRED_NARRATIVE_TEXT_NORMALIZATION = (
    "Whitespace is normalized before validation: leading and trailing whitespace is "
    "removed, internal whitespace runs are collapsed to one space, and the normalized "
    "text must contain at least one non-whitespace character. max_length applies to the "
    "normalized text."
)


def _query_object_contract() -> dict[str, Any]:
    return _object_contract(
        required=True,
        required_fields=("text", "role"),
        fields={
            "text": _text_contract(
                "query_strategy_candidate_query",
                required=True,
            ),
            "role": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_QUERY_ROLES,
            ),
            "justification": _text_contract(
                "query_strategy_distinct_need_justification",
                required=False,
                nonempty=False,
                adapter_normalization="empty text is omitted",
            ),
        },
    )


SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA: dict[str, Any] = {
    "contract_format": SEARCH_PLANNER_SEMANTIC_PROPOSAL_CONTRACT_FORMAT,
    "schema_version": SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA_VERSION,
    "strict_json_output_contract": list(
        SEARCH_PLANNER_MODEL_STRICT_JSON_OUTPUT_CONTRACT
    ),
    "top_level": _object_contract(
        required=True,
        required_fields=SEARCH_PLANNER_SEMANTIC_PROPOSAL_REQUIRED_TOP_LEVEL_FIELDS,
        fields={
            "interpretation": _text_contract(
                "question_meaning_summary",
                required=True,
                adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
            ),
            "components": {
                "json_type": "array",
                "required": True,
                "minimum_items": 1,
                "maximum_items": SEARCH_PLANNER_MAX_ANSWER_COMPONENTS,
                "item_contract": "semantic_component",
            },
            "material_ambiguity": _text_contract(
                "material_ambiguity_posture",
                required=False,
                nonempty=False,
                adapter_normalization="omit when not material; compiler defaults clear",
            ),
            "caveats": _text_array_contract(
                "top_level_text_list_item",
                required=False,
                minimum_items=0,
            ),
            "prohibited_upgrades": _text_array_contract(
                "top_level_text_list_item",
                required=False,
                minimum_items=0,
            ),
            "assumptions": _text_array_contract(
                "top_level_text_list_item",
                required=False,
                minimum_items=0,
            ),
            "normalization_notes": _text_array_contract(
                "top_level_text_list_item",
                required=False,
                minimum_items=0,
            ),
            "deferred_outputs": _text_array_contract(
                "top_level_text_list_item",
                required=False,
                minimum_items=0,
            ),
        },
    ),
    "semantic_component": _object_contract(
        required=True,
        required_fields=(
            "purpose",
            "label",
            "question",
            "requirement_posture",
            "acceptance_criteria",
            "support_kinds",
            "materiality",
            "slots",
        ),
        fields={
            "local_id": _text_contract("default_text", required=False, nonempty=False),
            "purpose": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_COMPONENT_PURPOSES,
            ),
            "label": _text_contract(
                "answer_component_user_facing_label",
                required=True,
                adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
            ),
            "question": _text_contract(
                "answer_component_user_facing_question",
                required=True,
                adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
            ),
            "requirement_posture": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_REQUIREMENT_POSTURES,
            ),
            "acceptance_criteria": _text_array_contract(
                "answer_component_acceptance_criterion",
                required=True,
                minimum_items=1,
            ),
            "support_kinds": _text_array_contract(
                "default_text",
                required=True,
                minimum_items=1,
                enum_values=SEARCH_PLANNER_MODEL_SUPPORT_KINDS,
            ),
            "max_inference_depth": {
                "json_type": "integer",
                "required": False,
                "minimum": 0,
                "adapter_normalization": (
                    "omit for direct-only (compiles to 0); required integer >=1 when "
                    "support_kinds includes inferred"
                ),
            },
            "depends_on": _text_array_contract(
                "default_text",
                required=False,
                minimum_items=0,
            ),
            "slots": {
                "json_type": "array",
                "required": True,
                "minimum_items": 1,
                "item_contract": "semantic_slot",
            },
            "source": {
                "json_type": "object",
                "required": False,
                "required_fields": ["kind"],
                "fields": {
                    "kind": _text_contract(
                        "default_text",
                        required=True,
                        enum_values=SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_KINDS,
                    ),
                    "strictness": _text_contract(
                        "default_text",
                        required=False,
                        enum_values=SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_STRICTNESSES,
                        nonempty=False,
                    ),
                },
            },
            "search": {
                "json_type": "object",
                "required": False,
                "required_fields": ["summary", "primary_query", "recon"],
                "fields": {
                    "summary": _text_contract(
                        "component_search_requirement_summary",
                        required=True,
                        adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
                    ),
                    "preferred_source_kinds": _text_array_contract(
                        "default_text",
                        required=False,
                        minimum_items=0,
                    ),
                    "recency_requirement": _text_contract(
                        "component_search_requirement_recency",
                        required=False,
                        nonempty=False,
                    ),
                    "primary_query": _query_object_contract(),
                    "secondary_query": {
                        "json_type": "object",
                        "required": False,
                        "required_fields": ("text", "role", "justification"),
                        "fields": {
                            "text": _text_contract(
                                "query_strategy_candidate_query",
                                required=True,
                            ),
                            "role": _text_contract(
                                "default_text",
                                required=True,
                                enum_values=SEARCH_PLANNER_MODEL_QUERY_ROLES,
                            ),
                            "justification": _text_contract(
                                "query_strategy_distinct_need_justification",
                                required=True,
                            ),
                        },
                    },
                    "recon": {
                        "json_type": "object",
                        "required": True,
                        "required_fields": ["posture", "dimensions"],
                        "fields": {
                            "posture": _text_contract(
                                "default_text",
                                required=True,
                                enum_values=SEARCH_PLANNER_MODEL_RECON_POSTURES,
                            ),
                            "dimensions": {
                                "json_type": "array",
                                "required": True,
                                "minimum_items": 0,
                                "maximum_items": _SEMANTIC_RECON_DIMENSION_CEILING,
                                "item_contract": "semantic_recon_dimension",
                            },
                        },
                    },
                },
            },
            "caveats": _text_array_contract(
                "answer_component_mandatory_caveat",
                required=False,
                minimum_items=0,
            ),
            "prohibited_upgrades": _text_array_contract(
                "answer_component_prohibited_upgrade",
                required=False,
                minimum_items=0,
            ),
            "materiality": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_MATERIALITY_VALUES,
            ),
            "partial_answer_policy": _text_contract(
                "default_text",
                required=False,
                enum_values=SEARCH_PLANNER_MODEL_PARTIAL_ANSWER_POLICIES,
                nonempty=False,
            ),
            "normalization_policy": _text_contract(
                "answer_component_normalization_policy",
                required=False,
                nonempty=False,
            ),
            "calculation_policy": _text_contract(
                "answer_component_calculation_policy",
                required=False,
                nonempty=False,
            ),
        },
    ),
    "semantic_recon_dimension": _object_contract(
        required=True,
        required_fields=("kind", "query"),
        fields={
            "kind": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_SEMANTIC_RECON_DIMENSION_KINDS,
            ),
            "query": _text_contract(
                "recon_candidate_query",
                required=True,
            ),
        },
    ),
    "semantic_slot": _object_contract(
        required=True,
        required_fields=("kind", "status", "materiality"),
        fields={
            "kind": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_KINDS,
            ),
            "status": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_STATUSES,
            ),
            "materiality": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_MATERIALITY_VALUES,
            ),
            "selected_value": _text_contract(
                "semantic_slot_selected_value",
                required=False,
                nonempty=False,
            ),
            "candidate_values": _text_array_contract(
                "semantic_slot_candidate_value",
                required=False,
                minimum_items=0,
            ),
            "user_confirmation_required": {
                "json_type": "boolean",
                "required": False,
                "default": False,
            },
            "normalization_notes": _text_array_contract(
                "semantic_slot_normalization_note",
                required=False,
                minimum_items=0,
            ),
        },
    ),
}


class SearchPlannerSemanticProposalError(ValueError):
    """Fail-closed semantic proposal validation or compilation error."""


def is_semantic_planner_proposal(payload: Mapping[str, Any]) -> bool:
    """Return True when payload uses the small semantic proposal shape."""

    if not isinstance(payload, Mapping):
        return False
    if "components" in payload and "answer_components" not in payload:
        return True
    contract = payload.get("contract_format")
    return contract == SEARCH_PLANNER_SEMANTIC_PROPOSAL_CONTRACT_FORMAT


def count_model_authored_mechanical_identity_keys(
    payload: Mapping[str, Any],
) -> int:
    """Count forbidden mechanical identity keys present anywhere in a proposal."""

    return len(_collect_keys(payload) & _FORBIDDEN_MECHANICAL_IDENTITY_KEYS)


def validate_semantic_planner_proposal(
    model_output: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and normalize the small semantic proposal (no rich IDs)."""

    if not isinstance(model_output, Mapping):
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal must be a JSON object"
        )
    _reject_unsafe_payload(model_output)
    forbidden_top = sorted(
        key for key in model_output.keys() if key in _FORBIDDEN_TOP_LEVEL_KEYS
    )
    if forbidden_top:
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal must not author rich administrative fields: "
            + ", ".join(forbidden_top)
        )
    mechanical = sorted(
        _collect_keys(model_output) & _FORBIDDEN_MECHANICAL_IDENTITY_KEYS
    )
    if mechanical:
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal must not author mechanical identity fields: "
            + ", ".join(mechanical)
        )
    unknown = sorted(
        key
        for key in model_output.keys()
        if key
        not in (
            *SEARCH_PLANNER_SEMANTIC_PROPOSAL_REQUIRED_TOP_LEVEL_FIELDS,
            *SEARCH_PLANNER_SEMANTIC_PROPOSAL_OPTIONAL_TOP_LEVEL_FIELDS,
            "contract_format",
            "schema_version",
        )
    )
    if unknown:
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal has unknown top-level fields: "
            + ", ".join(unknown)
        )
    missing = [
        field
        for field in SEARCH_PLANNER_SEMANTIC_PROPOSAL_REQUIRED_TOP_LEVEL_FIELDS
        if field not in model_output
    ]
    if missing:
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal missing required fields: " + ", ".join(missing)
        )

    interpretation = _required_text(
        model_output,
        "interpretation",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["question_meaning_summary"],
    )
    components_raw = model_output.get("components")
    if not isinstance(components_raw, list) or not components_raw:
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal requires a nonempty components array"
        )
    if len(components_raw) > SEARCH_PLANNER_MAX_ANSWER_COMPONENTS:
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal exceeds max answer components"
        )

    components: list[dict[str, Any]] = []
    local_ids: set[str] = set()
    for index, item in enumerate(components_raw):
        component = _validate_component(item, index=index)
        local_id = component.get("local_id")
        if local_id is not None:
            if local_id in local_ids:
                raise SearchPlannerSemanticProposalError(
                    f"duplicate component local_id: {local_id}"
                )
            local_ids.add(local_id)
        components.append(component)

    if not any(item["requirement_posture"] == "required" for item in components):
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal requires at least one required component"
        )

    for component in components:
        for dep in component.get("depends_on") or ():
            if dep not in local_ids:
                raise SearchPlannerSemanticProposalError(
                    f"component depends_on unresolved local_id: {dep}"
                )
            if dep == component.get("local_id"):
                raise SearchPlannerSemanticProposalError(
                    "component must not depend on itself"
                )

    return {
        "interpretation": interpretation,
        "components": components,
        "material_ambiguity": _optional_text(
            model_output,
            "material_ambiguity",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["material_ambiguity_posture"],
        ),
        "caveats": _optional_text_list(
            model_output,
            "caveats",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
        ),
        "prohibited_upgrades": _optional_text_list(
            model_output,
            "prohibited_upgrades",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
        ),
        "assumptions": _optional_text_list(
            model_output,
            "assumptions",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
        ),
        "normalization_notes": _optional_text_list(
            model_output,
            "normalization_notes",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
        ),
        "deferred_outputs": _optional_text_list(
            model_output,
            "deferred_outputs",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
        ),
    }


def compile_semantic_planner_proposal(
    semantic_proposal: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a validated semantic proposal into the rich Planner representation."""

    proposal = (
        semantic_proposal
        if "interpretation" in semantic_proposal
        and isinstance(semantic_proposal.get("components"), list)
        and all(
            isinstance(item, Mapping) and "component_id" not in item
            for item in semantic_proposal.get("components") or ()
        )
        else validate_semantic_planner_proposal(semantic_proposal)
    )

    components_in = list(proposal["components"])
    local_to_component_id: dict[str, str] = {}
    for index, component in enumerate(components_in, start=1):
        component_id = f"component:{index:02d}"
        local_id = component.get("local_id")
        if local_id:
            local_to_component_id[str(local_id)] = component_id
        else:
            local_to_component_id[f"__ordinal_{index}"] = component_id

    semantic_slots: list[dict[str, Any]] = []
    slot_ids_by_component: dict[str, list[str]] = {}
    slot_ordinal = 0
    for index, component in enumerate(components_in, start=1):
        component_id = f"component:{index:02d}"
        owned_slot_ids: list[str] = []
        for slot in component.get("slots") or ():
            slot_ordinal += 1
            slot_id = f"slot:{slot_ordinal:02d}"
            owned_slot_ids.append(slot_id)
            slot_payload: dict[str, Any] = {
                "slot_id": slot_id,
                "slot_kind": slot["kind"],
                "status": slot["status"],
                "materiality": slot["materiality"],
            }
            if slot.get("selected_value"):
                slot_payload["selected_value"] = slot["selected_value"]
            if slot.get("candidate_values"):
                slot_payload["candidate_values"] = list(slot["candidate_values"])
            if "user_confirmation_required" in slot:
                slot_payload["user_confirmation_required"] = bool(
                    slot["user_confirmation_required"]
                )
            elif (
                slot["materiality"] == "material"
                and slot["status"] in {"ambiguous", "unresolved"}
            ):
                slot_payload["user_confirmation_required"] = True
            if slot.get("normalization_notes"):
                slot_payload["normalization_notes"] = list(slot["normalization_notes"])
            semantic_slots.append(slot_payload)
        slot_ids_by_component[component_id] = owned_slot_ids

    answer_components: list[dict[str, Any]] = []
    source_obligations: list[dict[str, Any]] = []
    component_search_requirements: list[dict[str, Any]] = []
    obligation_ordinal = 0

    for index, component in enumerate(components_in, start=1):
        component_id = f"component:{index:02d}"
        support_kinds = list(component["support_kinds"])
        owns_direct = "direct" in support_kinds
        owns_inferred = "inferred" in support_kinds
        max_depth = component.get("max_inference_depth")
        if support_kinds == ["direct"]:
            max_depth = 0 if max_depth is None else int(max_depth)
        elif max_depth is None:
            raise SearchPlannerSemanticProposalError(
                f"component {component_id} with inferred support requires max_inference_depth"
            )
        else:
            max_depth = int(max_depth)

        obligation_ids: list[str] = []
        if owns_direct:
            source = component.get("source")
            if not isinstance(source, Mapping):
                raise SearchPlannerSemanticProposalError(
                    f"component {component_id} with direct support requires source"
                )
            obligation_ordinal += 1
            obligation_id = f"obligation:{obligation_ordinal:02d}"
            obligation_ids.append(obligation_id)
            obligation: dict[str, Any] = {
                "candidate_id": obligation_id,
                "obligation_kind": source["kind"],
                "component_candidate_ids": [component_id],
            }
            if source.get("strictness"):
                obligation["strictness"] = source["strictness"]
            source_obligations.append(obligation)

        depends_on_local = list(component.get("depends_on") or ())
        dependency_ids = [local_to_component_id[dep] for dep in depends_on_local]
        if owns_inferred and not dependency_ids:
            raise SearchPlannerSemanticProposalError(
                f"component {component_id} with inferred support requires depends_on"
            )

        owned_slots = slot_ids_by_component[component_id]
        if not owned_slots:
            raise SearchPlannerSemanticProposalError(
                f"component {component_id} requires at least one nested semantic slot"
            )

        rich_component: dict[str, Any] = {
            "component_id": component_id,
            "component_revision": "1",
            "component_purpose": component["purpose"],
            "user_facing_label": component["label"],
            "user_facing_question": component["question"],
            "requirement_posture": component["requirement_posture"],
            "acceptance_criteria": list(component["acceptance_criteria"]),
            "semantic_slot_ids": list(owned_slots),
            "allowed_support_kinds": support_kinds,
            "max_inference_depth": int(max_depth),
            "materiality": component["materiality"],
        }
        if obligation_ids:
            rich_component["source_obligation_candidate_ids"] = obligation_ids
        elif owns_direct is False:
            rich_component["source_obligation_candidate_ids"] = []
        if dependency_ids:
            rich_component["dependency_component_ids"] = dependency_ids
        if component.get("caveats"):
            rich_component["mandatory_caveats"] = list(component["caveats"])
        if component.get("prohibited_upgrades"):
            rich_component["prohibited_upgrades"] = list(
                component["prohibited_upgrades"]
            )
        if component.get("partial_answer_policy"):
            rich_component["partial_answer_policy"] = component["partial_answer_policy"]
        if component.get("normalization_policy"):
            rich_component["normalization_policy"] = component["normalization_policy"]
        if component.get("calculation_policy"):
            rich_component["calculation_policy"] = component["calculation_policy"]
        answer_components.append(rich_component)

        if owns_direct:
            search = component.get("search")
            if not isinstance(search, Mapping):
                raise SearchPlannerSemanticProposalError(
                    f"component {component_id} with direct support requires search"
                )
            primary = search["primary_query"]
            recon_requirement = _compile_recon_requirement(
                search["recon"],
                component_index=index,
            )
            # Component-level recon is model-authored once. Attach the actionable
            # rich candidate payload to the primary strategy only so downstream
            # per-component aggregation does not see duplicated dimension IDs
            # when a secondary initial-query strategy also exists.
            strategies: list[dict[str, Any]] = [
                {
                    "strategy_id": f"strategy:{index:02d}:primary",
                    "component_id": component_id,
                    "candidate_kind": "primary",
                    "candidate_query_text": primary["text"],
                    "requested_role": primary["role"],
                    "source_obligation_candidate_ids": list(obligation_ids),
                    "distinct_need_justification": (
                        primary.get("justification")
                        or "Primary query for the accepted component."
                    ),
                    "recon_requirement": _copy_recon_requirement(recon_requirement),
                }
            ]
            secondary = search.get("secondary_query")
            if isinstance(secondary, Mapping):
                strategies.append(
                    {
                        "strategy_id": f"strategy:{index:02d}:secondary",
                        "component_id": component_id,
                        "candidate_kind": "secondary",
                        "candidate_query_text": secondary["text"],
                        "requested_role": secondary["role"],
                        "source_obligation_candidate_ids": list(obligation_ids),
                        "distinct_need_justification": secondary["justification"],
                        "recon_requirement": _empty_not_needed_recon_requirement(),
                    }
                )
            requirement: dict[str, Any] = {
                "component_id": component_id,
                "requirement_id": f"searchreq:{index:02d}",
                "requirement_summary": search["summary"],
                "source_obligation_candidate_ids": list(obligation_ids),
                "metadata": {"query_strategy_candidates": strategies},
            }
            if search.get("preferred_source_kinds"):
                requirement["preferred_source_kinds"] = list(
                    search["preferred_source_kinds"]
                )
            if search.get("recency_requirement"):
                requirement["recency_requirement"] = search["recency_requirement"]
            component_search_requirements.append(requirement)
        elif component.get("search") is not None:
            raise SearchPlannerSemanticProposalError(
                f"inferred-only component {component_id} must not author search"
            )

    interpretation = str(proposal["interpretation"])
    material_ambiguity = proposal.get("material_ambiguity") or "clear"
    return {
        "question_meaning_summary": interpretation,
        "requested_output": interpretation,
        "semantic_slots": semantic_slots,
        "answer_components": answer_components,
        "source_obligation_candidates": source_obligations,
        "component_search_requirements": component_search_requirements,
        "material_ambiguity_posture": material_ambiguity,
        "mandatory_caveats": list(proposal.get("caveats") or []),
        "prohibited_upgrades": list(proposal.get("prohibited_upgrades") or []),
        "normalization_obligations": list(proposal.get("normalization_notes") or []),
        "assumptions": list(proposal.get("assumptions") or []),
        "unsupported_or_deferred_outputs": list(proposal.get("deferred_outputs") or []),
    }


def _validate_component(item: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] must be an object"
        )
    mechanical = sorted(_collect_keys(item) & _FORBIDDEN_MECHANICAL_IDENTITY_KEYS)
    if mechanical:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] must not author mechanical identity fields: "
            + ", ".join(mechanical)
        )
    purpose = _required_text(
        item,
        "purpose",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
        allowed=SEARCH_PLANNER_MODEL_COMPONENT_PURPOSES,
    )
    label = _required_text(
        item,
        "label",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["answer_component_user_facing_label"],
    )
    question = _required_text(
        item,
        "question",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["answer_component_user_facing_question"],
    )
    requirement_posture = _required_text(
        item,
        "requirement_posture",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
        allowed=SEARCH_PLANNER_MODEL_REQUIREMENT_POSTURES,
    )
    acceptance_criteria = _required_text_list(
        item,
        "acceptance_criteria",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["answer_component_acceptance_criterion"],
        minimum_items=1,
    )
    support_kinds = _required_text_list(
        item,
        "support_kinds",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
        minimum_items=1,
        allowed=SEARCH_PLANNER_MODEL_SUPPORT_KINDS,
    )
    allowed_combos = (["direct"], ["inferred"], ["direct", "inferred"])
    if support_kinds not in allowed_combos:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] support_kinds must be direct, inferred, or both"
        )
    materiality = _required_text(
        item,
        "materiality",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
        allowed=SEARCH_PLANNER_MODEL_MATERIALITY_VALUES,
    )
    max_inference_depth = item.get("max_inference_depth")
    if max_inference_depth is not None:
        if isinstance(max_inference_depth, bool) or not isinstance(
            max_inference_depth, int
        ):
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] max_inference_depth must be an integer"
            )
        if max_inference_depth < 0:
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] max_inference_depth must be >= 0"
            )
    if support_kinds == ["direct"]:
        if max_inference_depth not in (None, 0):
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] direct-only max_inference_depth must be 0"
            )
        if "source" not in item or not isinstance(item.get("source"), Mapping):
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] direct support requires source"
            )
        if "search" not in item or not isinstance(item.get("search"), Mapping):
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] direct support requires search"
            )
    if "inferred" in support_kinds:
        if max_inference_depth is None:
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] inferred support requires max_inference_depth"
            )
        if max_inference_depth < 1:
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] inferred support requires max_inference_depth >= 1"
            )
        depends_on = item.get("depends_on")
        if not isinstance(depends_on, list) or not depends_on:
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] inferred support requires depends_on"
            )
        if support_kinds == ["inferred"] and item.get("source") is not None:
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] inferred-only must not author source"
            )
        if support_kinds == ["inferred"] and item.get("search") is not None:
            raise SearchPlannerSemanticProposalError(
                f"components[{index}] inferred-only must not author search"
            )

    local_id = _optional_text(
        item, "local_id", limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"]
    )
    slots_raw = item.get("slots")
    if slots_raw is None:
        slots_raw = []
    if not isinstance(slots_raw, list):
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] slots must be an array"
        )
    if not slots_raw:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}] requires at least one nested semantic slot"
        )
    slots = [
        _validate_slot(slot, index=index, slot_index=slot_index)
        for slot_index, slot in enumerate(slots_raw)
    ]

    source = None
    if isinstance(item.get("source"), Mapping):
        source = {
            "kind": _required_text(
                item["source"],
                "kind",
                limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
                allowed=SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_KINDS,
            ),
        }
        strictness = _optional_text(
            item["source"],
            "strictness",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
            allowed=SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_STRICTNESSES,
        )
        if strictness:
            source["strictness"] = strictness

    search = None
    if isinstance(item.get("search"), Mapping):
        search = _validate_search(item["search"], index=index)

    depends_on = _optional_text_list(
        item,
        "depends_on",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
    )
    result: dict[str, Any] = {
        "purpose": purpose,
        "label": label,
        "question": question,
        "requirement_posture": requirement_posture,
        "acceptance_criteria": acceptance_criteria,
        "support_kinds": support_kinds,
        "materiality": materiality,
        "slots": slots,
    }
    if local_id:
        result["local_id"] = local_id
    if max_inference_depth is not None:
        result["max_inference_depth"] = int(max_inference_depth)
    if depends_on:
        result["depends_on"] = depends_on
    if source is not None:
        result["source"] = source
    if search is not None:
        result["search"] = search
    caveats = _optional_text_list(
        item,
        "caveats",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["answer_component_mandatory_caveat"],
    )
    if caveats:
        result["caveats"] = caveats
    prohibited = _optional_text_list(
        item,
        "prohibited_upgrades",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["answer_component_prohibited_upgrade"],
    )
    if prohibited:
        result["prohibited_upgrades"] = prohibited
    partial = _optional_text(
        item,
        "partial_answer_policy",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
        allowed=SEARCH_PLANNER_MODEL_PARTIAL_ANSWER_POLICIES,
    )
    if partial:
        result["partial_answer_policy"] = partial
    normalization_policy = _optional_text(
        item,
        "normalization_policy",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["answer_component_normalization_policy"],
    )
    if normalization_policy:
        result["normalization_policy"] = normalization_policy
    calculation_policy = _optional_text(
        item,
        "calculation_policy",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["answer_component_calculation_policy"],
    )
    if calculation_policy:
        result["calculation_policy"] = calculation_policy
    return result


def _validate_slot(item: Any, *, index: int, slot_index: int) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].slots[{slot_index}] must be an object"
        )
    if "slot_id" in item:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].slots[{slot_index}] must not author slot_id"
        )
    result: dict[str, Any] = {
        "kind": _required_text(
            item,
            "kind",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
            allowed=SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_KINDS,
        ),
        "status": _required_text(
            item,
            "status",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
            allowed=SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_STATUSES,
        ),
        "materiality": _required_text(
            item,
            "materiality",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
            allowed=SEARCH_PLANNER_MODEL_MATERIALITY_VALUES,
        ),
    }
    selected = _optional_text(
        item,
        "selected_value",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["semantic_slot_selected_value"],
    )
    if selected:
        result["selected_value"] = selected
    candidates = _optional_text_list(
        item,
        "candidate_values",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["semantic_slot_candidate_value"],
    )
    if candidates:
        result["candidate_values"] = candidates
    if "user_confirmation_required" in item:
        result["user_confirmation_required"] = bool(item["user_confirmation_required"])
    notes = _optional_text_list(
        item,
        "normalization_notes",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["semantic_slot_normalization_note"],
    )
    if notes:
        result["normalization_notes"] = notes
    return result


def _validate_search(item: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    summary = _required_text(
        item,
        "summary",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["component_search_requirement_summary"],
    )
    primary_raw = item.get("primary_query")
    if not isinstance(primary_raw, Mapping):
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].search.primary_query is required"
        )
    primary = {
        "text": _required_text(
            primary_raw,
            "text",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["query_strategy_candidate_query"],
        ),
        "role": _required_text(
            primary_raw,
            "role",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
            allowed=SEARCH_PLANNER_MODEL_QUERY_ROLES,
        ),
    }
    justification = _optional_text(
        primary_raw,
        "justification",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
            "query_strategy_distinct_need_justification"
        ],
    )
    if justification:
        primary["justification"] = justification
    result: dict[str, Any] = {
        "summary": summary,
        "primary_query": primary,
        "recon": _validate_recon(item.get("recon"), index=index),
    }
    preferred = _optional_text_list(
        item,
        "preferred_source_kinds",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
    )
    if preferred:
        result["preferred_source_kinds"] = preferred
    recency = _optional_text(
        item,
        "recency_requirement",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["component_search_requirement_recency"],
    )
    if recency:
        result["recency_requirement"] = recency
    secondary_raw = item.get("secondary_query")
    if secondary_raw is not None:
        if not isinstance(secondary_raw, Mapping):
            raise SearchPlannerSemanticProposalError(
                f"components[{index}].search.secondary_query must be an object"
            )
        result["secondary_query"] = {
            "text": _required_text(
                secondary_raw,
                "text",
                limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["query_strategy_candidate_query"],
            ),
            "role": _required_text(
                secondary_raw,
                "role",
                limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
                allowed=SEARCH_PLANNER_MODEL_QUERY_ROLES,
            ),
            "justification": _required_text(
                secondary_raw,
                "justification",
                limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                    "query_strategy_distinct_need_justification"
                ],
            ),
        }
    forbidden = sorted(_collect_keys(item) & _FORBIDDEN_QUERY_AUTHORITY_KEYS)
    if forbidden:
        raise SearchPlannerSemanticProposalError(
            "search must not select provider/model authority: " + ", ".join(forbidden)
        )
    return result


def _validate_recon(item: Any, *, index: int) -> dict[str, Any]:
    if item is None:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].search.recon is required; "
            "omitted recon is not equivalent to not_needed"
        )
    if not isinstance(item, Mapping):
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].search.recon must be an object"
        )
    unknown = sorted(
        key for key in item.keys() if key not in {"posture", "dimensions"}
    )
    if unknown:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].search.recon has unknown fields: "
            + ", ".join(unknown)
        )
    posture = _required_text(
        item,
        "posture",
        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
        allowed=SEARCH_PLANNER_MODEL_RECON_POSTURES,
    )
    dimensions_raw = item.get("dimensions")
    if not isinstance(dimensions_raw, list):
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].search.recon.dimensions must be an array"
        )
    if len(dimensions_raw) > _SEMANTIC_RECON_DIMENSION_CEILING:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].search.recon.dimensions exceeds "
            f"per-affected-component ceiling {_SEMANTIC_RECON_DIMENSION_CEILING}"
        )
    if posture == "not_needed" and dimensions_raw:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].search.recon posture not_needed requires empty dimensions"
        )
    if posture in {"optional", "required"} and not dimensions_raw:
        raise SearchPlannerSemanticProposalError(
            f"components[{index}].search.recon posture {posture} requires at least "
            "one ambiguity dimension"
        )
    dimensions: list[dict[str, str]] = []
    seen_kinds: set[str] = set()
    for dim_index, raw_dimension in enumerate(dimensions_raw):
        if not isinstance(raw_dimension, Mapping):
            raise SearchPlannerSemanticProposalError(
                f"components[{index}].search.recon.dimensions[{dim_index}] must be an object"
            )
        unknown_dim = sorted(
            key for key in raw_dimension.keys() if key not in {"kind", "query"}
        )
        if unknown_dim:
            raise SearchPlannerSemanticProposalError(
                f"components[{index}].search.recon.dimensions[{dim_index}] has unknown "
                f"fields: " + ", ".join(unknown_dim)
            )
        kind = _required_text(
            raw_dimension,
            "kind",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
            allowed=SEARCH_PLANNER_SEMANTIC_RECON_DIMENSION_KINDS,
        )
        if kind in seen_kinds:
            raise SearchPlannerSemanticProposalError(
                f"components[{index}].search.recon.dimensions duplicates kind {kind}"
            )
        seen_kinds.add(kind)
        query = _required_text(
            raw_dimension,
            "query",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["recon_candidate_query"],
        )
        dimensions.append({"kind": kind, "query": query})
    return {"posture": posture, "dimensions": dimensions}


def _compile_recon_requirement(
    recon: Mapping[str, Any],
    *,
    component_index: int,
) -> dict[str, Any]:
    posture = str(recon["posture"])
    unresolved_dimension_ids: list[str] = []
    candidate_queries: list[dict[str, str]] = []
    for dim_index, dimension in enumerate(recon.get("dimensions") or (), start=1):
        kind = str(dimension["kind"])
        dimension_id = f"dimension:{component_index:02d}:{dim_index:02d}:{kind}"
        unresolved_dimension_ids.append(dimension_id)
        candidate_queries.append(
            {
                "dimension_id": dimension_id,
                "candidate_query_text": str(dimension["query"]),
                "query_kind": _RECON_DIMENSION_KIND_TO_QUERY_KIND[kind],
            }
        )
    return {
        "posture": posture,
        "unresolved_dimension_ids": unresolved_dimension_ids,
        "candidate_queries": candidate_queries,
        "required_for_truthful_targeting": posture == "required",
    }


def _copy_recon_requirement(recon_requirement: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "posture": str(recon_requirement["posture"]),
        "unresolved_dimension_ids": list(
            recon_requirement["unresolved_dimension_ids"]
        ),
        "candidate_queries": [
            {
                "dimension_id": str(item["dimension_id"]),
                "candidate_query_text": str(item["candidate_query_text"]),
                "query_kind": str(item["query_kind"]),
            }
            for item in recon_requirement["candidate_queries"]
        ],
        "required_for_truthful_targeting": bool(
            recon_requirement["required_for_truthful_targeting"]
        ),
    }


def _empty_not_needed_recon_requirement() -> dict[str, Any]:
    """Mechanical empty recon carrier for non-primary strategies of one component."""

    return {
        "posture": "not_needed",
        "unresolved_dimension_ids": [],
        "candidate_queries": [],
        "required_for_truthful_targeting": False,
    }


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _required_text(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int,
    allowed: frozenset[str] | None = None,
) -> str:
    if key not in mapping:
        raise SearchPlannerSemanticProposalError(f"missing required field: {key}")
    raw = mapping[key]
    if not isinstance(raw, str):
        raise SearchPlannerSemanticProposalError(f"{key} must be a string")
    text = _normalize_whitespace(raw)
    if not text:
        raise SearchPlannerSemanticProposalError(f"{key} must be nonempty")
    if len(text) > limit:
        raise SearchPlannerSemanticProposalError(f"{key} exceeds max length {limit}")
    if allowed is not None and text not in allowed:
        raise SearchPlannerSemanticProposalError(f"{key} value not allowed: {text}")
    return text


def _optional_text(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int,
    allowed: frozenset[str] | None = None,
) -> str | None:
    if key not in mapping or mapping[key] is None:
        return None
    raw = mapping[key]
    if not isinstance(raw, str):
        raise SearchPlannerSemanticProposalError(f"{key} must be a string")
    text = _normalize_whitespace(raw)
    if not text:
        return None
    if len(text) > limit:
        raise SearchPlannerSemanticProposalError(f"{key} exceeds max length {limit}")
    if allowed is not None and text not in allowed:
        raise SearchPlannerSemanticProposalError(f"{key} value not allowed: {text}")
    return text


def _required_text_list(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int,
    minimum_items: int,
    allowed: frozenset[str] | None = None,
) -> list[str]:
    if key not in mapping:
        raise SearchPlannerSemanticProposalError(f"missing required field: {key}")
    raw = mapping[key]
    if not isinstance(raw, list):
        raise SearchPlannerSemanticProposalError(f"{key} must be an array")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise SearchPlannerSemanticProposalError(f"{key} items must be strings")
        text = _normalize_whitespace(item)
        if not text:
            raise SearchPlannerSemanticProposalError(f"{key} items must be nonempty")
        if len(text) > limit:
            raise SearchPlannerSemanticProposalError(
                f"{key} item exceeds max length {limit}"
            )
        if allowed is not None and text not in allowed:
            raise SearchPlannerSemanticProposalError(
                f"{key} value not allowed: {text}"
            )
        values.append(text)
    if len(values) < minimum_items:
        raise SearchPlannerSemanticProposalError(
            f"{key} requires at least {minimum_items} items"
        )
    return values


def _optional_text_list(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int,
) -> list[str]:
    if key not in mapping or mapping[key] is None:
        return []
    raw = mapping[key]
    if not isinstance(raw, list):
        raise SearchPlannerSemanticProposalError(f"{key} must be an array")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise SearchPlannerSemanticProposalError(f"{key} items must be strings")
        text = _normalize_whitespace(item)
        if not text:
            continue
        if len(text) > limit:
            raise SearchPlannerSemanticProposalError(
                f"{key} item exceeds max length {limit}"
            )
        values.append(text)
    return values


def _collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(_collect_keys(nested))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            keys.update(_collect_keys(item))
    return keys


def _reject_unsafe_payload(payload: Mapping[str, Any]) -> None:
    keys = _collect_keys(payload)
    sensitive = sorted(keys & _SENSITIVE_KEYS)
    if sensitive:
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal contains private/raw material keys: "
            + ", ".join(sensitive)
        )
    authority = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if authority:
        raise SearchPlannerSemanticProposalError(
            "semantic planner proposal escalates closed authority: "
            + ", ".join(authority)
        )


__all__ = [
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_CONTRACT_FORMAT",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_OPTIONAL_TOP_LEVEL_FIELDS",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_REQUIRED_TOP_LEVEL_FIELDS",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA",
    "SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA_VERSION",
    "SEARCH_PLANNER_SEMANTIC_RECON_DIMENSION_KINDS",
    "SearchPlannerSemanticProposalError",
    "compile_semantic_planner_proposal",
    "count_model_authored_mechanical_identity_keys",
    "is_semantic_planner_proposal",
    "validate_semantic_planner_proposal",
]
