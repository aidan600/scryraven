"""Prompt and schema boundary for the AG-SEARCH-PLANNER-MODEL-01 adapter.

The prompt builder is pure: callers may retain only the metadata returned by
``prompt_metadata`` and must not store the prompt text.
"""

from __future__ import annotations

import json
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Mapping

from core.search_planner_runtime import SEARCH_PLANNER_MAX_ANSWER_COMPONENTS
from core.search_work_plan import SourceObligationKind, SourceObligationStrictness
from core.semantic_contract_foundation import (
    ComponentPurpose,
    Materiality,
    PartialAnswerPolicy,
    RequirementPosture,
    SemanticSlotKind,
    SemanticSlotStatus,
    SupportKind,
)

SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION = "search_planner_model_prompt_ag_search_planner_model_01_v4"

SEARCH_PLANNER_MODEL_STRICT_JSON_OUTPUT_CONTRACT = (
    "Return exactly one JSON object.",
    "Return JSON only; emit no prose before or after the object.",
    "Do not wrap the object in Markdown or code fences.",
    (
        "Within every JSON object, including nested objects and objects inside arrays, "
        "use each member name at most once. Never emit duplicate keys."
    ),
    "Never emit NaN, Infinity, or -Infinity.",
    "Use only standard finite JSON values.",
)
_STRICT_JSON_OUTPUT_CONTRACT_TEXT = "\n".join(
    f"- {requirement}"
    for requirement in SEARCH_PLANNER_MODEL_STRICT_JSON_OUTPUT_CONTRACT
)

SEARCH_PLANNER_MODEL_SYSTEM_PROMPT = (
    "You are SearchPlanner and own semantic interpretation of the supplied human "
    "utterance and bounded planning context. You are not Author, Scout, SearchExecutor, "
    "a citation formatter, or an evidence ledger. Follow the strict JSON output contract:\n"
    f"{_STRICT_JSON_OUTPUT_CONTRACT_TEXT}"
)

SEARCH_PLANNER_MODEL_REQUIRED_TOP_LEVEL_FIELDS = (
    "question_meaning_summary",
    "requested_output",
    "semantic_slots",
    "answer_components",
    "source_obligation_candidates",
    "component_search_requirements",
    "material_ambiguity_posture",
    "mandatory_caveats",
    "prohibited_upgrades",
    "normalization_obligations",
    "assumptions",
    "unsupported_or_deferred_outputs",
)
SEARCH_PLANNER_MODEL_OPTIONAL_TOP_LEVEL_FIELDS = (
    "contract_amendment_candidates",
    "relationship_hypotheses",
)

SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_KINDS = frozenset(
    item.value for item in SemanticSlotKind
)
SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_STATUSES = frozenset(
    item.value for item in SemanticSlotStatus
)
SEARCH_PLANNER_MODEL_MATERIALITY_VALUES = frozenset(
    item.value for item in Materiality
)
SEARCH_PLANNER_MODEL_REQUIREMENT_POSTURES = frozenset(
    item.value for item in RequirementPosture
)
SEARCH_PLANNER_MODEL_COMPONENT_PURPOSES = frozenset(
    item.value for item in ComponentPurpose
)
SEARCH_PLANNER_MODEL_SUPPORT_KINDS = frozenset(
    item.value
    for item in SupportKind
    if item in {SupportKind.DIRECT, SupportKind.INFERRED}
)
SEARCH_PLANNER_MODEL_PARTIAL_ANSWER_POLICIES = frozenset(
    item.value for item in PartialAnswerPolicy
)
SEARCH_PLANNER_MODEL_QUERY_CANDIDATE_KINDS = frozenset({"primary", "secondary"})
SEARCH_PLANNER_MODEL_QUERY_ROLES = frozenset(
    {
        "initial",
        "official_bias",
        "canonical_bias",
        "recency",
        "disambiguation",
        "recon_rewrite",
    }
)
SEARCH_PLANNER_MODEL_RECON_POSTURES = frozenset(
    {"not_needed", "optional", "required"}
)
SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_KINDS = frozenset(
    item.value for item in SourceObligationKind
)
SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_STRICTNESSES = frozenset(
    item.value for item in SourceObligationStrictness
)
SEARCH_PLANNER_MODEL_ALLOWED_SUPPORT_KIND_COMBINATIONS = (
    ("direct",),
    ("inferred",),
    ("direct", "inferred"),
)

SEARCH_PLANNER_MODEL_TEXT_LIMITS: Mapping[str, int] = MappingProxyType(
    {
        "default_text": 160,
        "question_meaning_summary": 420,
        "requested_output": 300,
        "material_ambiguity_posture": 120,
        "top_level_text_list_item": 260,
        "semantic_slot_candidate_value": 220,
        "semantic_slot_selected_value": 220,
        "semantic_slot_normalization_note": 260,
        "answer_component_user_facing_label": 180,
        "answer_component_user_facing_question": 400,
        "answer_component_acceptance_criterion": 320,
        "answer_component_normalization_policy": 300,
        "answer_component_calculation_policy": 300,
        "answer_component_mandatory_caveat": 260,
        "answer_component_prohibited_upgrade": 260,
        "relationship_hypothesis_summary": 360,
        "component_search_requirement_summary": 320,
        "component_search_requirement_recency": 220,
        "query_strategy_candidate_query": 300,
        "query_strategy_distinct_need_justification": 300,
        "recon_candidate_query": 300,
        "contract_amendment_candidate_summary": 260,
    }
)

_REQUIRED_NARRATIVE_TEXT_NORMALIZATION = (
    "Whitespace is normalized before validation: leading and trailing whitespace is "
    "removed, internal whitespace runs are collapsed to one space, and the normalized "
    "text must contain at least one non-whitespace character. max_length applies to the "
    "normalized text."
)


def _text_contract(
    limit_key: str,
    *,
    required: bool,
    enum_values: frozenset[str] | None = None,
    nonempty: bool = True,
    adapter_normalization: str | None = None,
) -> dict[str, Any]:
    contract: dict[str, Any] = {
        "json_type": "string",
        "required": required,
        "nonempty": nonempty,
        "max_length": SEARCH_PLANNER_MODEL_TEXT_LIMITS[limit_key],
    }
    if enum_values is not None:
        contract["exact_values"] = sorted(enum_values)
    if adapter_normalization is not None:
        contract["adapter_normalization"] = adapter_normalization
    return contract


def _text_array_contract(
    limit_key: str,
    *,
    required: bool,
    minimum_items: int,
    enum_values: frozenset[str] | None = None,
) -> dict[str, Any]:
    return {
        "json_type": "array",
        "required": required,
        "minimum_nonempty_items": minimum_items,
        "items": _text_contract(
            limit_key,
            required=True,
            enum_values=enum_values,
            nonempty=False,
        ),
    }


def _object_contract(
    *,
    required: bool,
    required_fields: tuple[str, ...],
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "json_type": "object",
        "required": required,
        "required_fields": list(required_fields),
        "fields": dict(fields),
    }


SEARCH_PLANNER_MODEL_OUTPUT_SCHEMA: dict[str, Any] = {
    "contract_format": "static_model_visible_output_contract_v1",
    "strict_json_output_contract": list(
        SEARCH_PLANNER_MODEL_STRICT_JSON_OUTPUT_CONTRACT
    ),
    "top_level": _object_contract(
        required=True,
        required_fields=SEARCH_PLANNER_MODEL_REQUIRED_TOP_LEVEL_FIELDS,
        fields={
            "question_meaning_summary": _text_contract(
                "question_meaning_summary",
                required=True,
                adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
            ),
            "requested_output": _text_contract(
                "requested_output",
                required=True,
                adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
            ),
            "semantic_slots": {
                "json_type": "array",
                "required": True,
                "minimum_items": 1,
                "item_contract": "semantic_slot",
            },
            "answer_components": {
                "json_type": "array",
                "required": True,
                "minimum_items": 1,
                "maximum_items": SEARCH_PLANNER_MAX_ANSWER_COMPONENTS,
                "item_contract": "answer_component",
            },
            "source_obligation_candidates": {
                "json_type": "array",
                "required": True,
                "minimum_items": 1,
                "item_contract": "source_obligation_candidate",
            },
            "component_search_requirements": {
                "json_type": "array",
                "required": True,
                "minimum_items": 1,
                "item_contract": "component_search_requirement",
            },
            "material_ambiguity_posture": _text_contract(
                "material_ambiguity_posture",
                required=True,
                adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
            ),
            "mandatory_caveats": _text_array_contract(
                "top_level_text_list_item",
                required=True,
                minimum_items=0,
            ),
            "prohibited_upgrades": _text_array_contract(
                "top_level_text_list_item",
                required=True,
                minimum_items=0,
            ),
            "normalization_obligations": _text_array_contract(
                "top_level_text_list_item",
                required=True,
                minimum_items=0,
            ),
            "assumptions": _text_array_contract(
                "top_level_text_list_item",
                required=True,
                minimum_items=0,
            ),
            "unsupported_or_deferred_outputs": _text_array_contract(
                "top_level_text_list_item",
                required=True,
                minimum_items=0,
            ),
            "contract_amendment_candidates": {
                "json_type": "array",
                "required": False,
                "minimum_items": 0,
                "item_contract": "contract_amendment_candidate",
            },
            "relationship_hypotheses": {
                "json_type": "array",
                "required": False,
                "minimum_items": 0,
                "maximum_items": SEARCH_PLANNER_MAX_ANSWER_COMPONENTS,
                "item_contract": "relationship_hypothesis",
            },
        },
    ),
    "semantic_slot": _object_contract(
        required=True,
        required_fields=("slot_id", "slot_kind", "status", "materiality"),
        fields={
            "slot_id": _text_contract("default_text", required=True),
            "slot_kind": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_KINDS,
            ),
            "status": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_STATUSES,
            ),
            "candidate_values": _text_array_contract(
                "semantic_slot_candidate_value",
                required=False,
                minimum_items=0,
            ),
            "selected_value": _text_contract(
                "semantic_slot_selected_value",
                required=False,
                nonempty=False,
                adapter_normalization="empty text is omitted",
            ),
            "materiality": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_MATERIALITY_VALUES,
            ),
            "user_confirmation_required": {
                "json_type": "boolean",
                "required": False,
                "default": False,
                "adapter_normalization": "adapter applies boolean truthiness; emit a JSON boolean",
            },
            "normalization_notes": _text_array_contract(
                "semantic_slot_normalization_note",
                required=False,
                minimum_items=0,
            ),
            "metadata": {
                "json_type": "object",
                "required": False,
                "adapter_normalization": "safe metadata only",
            },
        },
        ),
    "semantic_slot_cross_field_conditions": [
        {
            "if": {
                "materiality": "material",
                "status": {"one_of": ["ambiguous", "unresolved"]},
            },
            "then": {"user_confirmation_required": True},
        }
    ],
    "answer_component": _object_contract(
        required=True,
        required_fields=(
            "component_id",
            "component_revision",
            "component_purpose",
            "user_facing_label",
            "user_facing_question",
            "requirement_posture",
            "acceptance_criteria",
            "semantic_slot_ids",
            "allowed_support_kinds",
            "max_inference_depth",
            "materiality",
        ),
        fields={
            "component_id": _text_contract("default_text", required=True),
            "component_revision": _text_contract("default_text", required=True),
            "component_purpose": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_COMPONENT_PURPOSES,
            ),
            "user_facing_label": _text_contract(
                "answer_component_user_facing_label",
                required=True,
                adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
            ),
            "user_facing_question": _text_contract(
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
            "semantic_slot_ids": _text_array_contract(
                "default_text",
                required=True,
                minimum_items=1,
            ),
            "source_obligation_candidate_ids": _text_array_contract(
                "default_text",
                required=False,
                minimum_items=0,
            ),
            "allowed_support_kinds": _text_array_contract(
                "default_text",
                required=True,
                minimum_items=1,
                enum_values=SEARCH_PLANNER_MODEL_SUPPORT_KINDS,
            ),
            "max_inference_depth": {
                "json_type": "integer",
                "required": True,
                "minimum": 0,
                "adapter_normalization": "adapter accepts integer-coercible values; emit a JSON integer",
            },
            "normalization_policy": _text_contract(
                "answer_component_normalization_policy",
                required=False,
                nonempty=False,
                adapter_normalization="empty text is omitted",
            ),
            "calculation_policy": _text_contract(
                "answer_component_calculation_policy",
                required=False,
                nonempty=False,
                adapter_normalization="empty text is omitted",
            ),
            "dependency_component_ids": _text_array_contract(
                "default_text",
                required=False,
                minimum_items=0,
            ),
            "partial_answer_policy": _text_contract(
                "default_text",
                required=False,
                enum_values=SEARCH_PLANNER_MODEL_PARTIAL_ANSWER_POLICIES,
                nonempty=False,
                adapter_normalization="empty text is omitted",
            ),
            "mandatory_caveats": _text_array_contract(
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
            "metadata": {
                "json_type": "object",
                "required": False,
                "adapter_normalization": "safe metadata only",
            },
        },
    ),
    "answer_component_cross_field_conditions": [
        {
            "if": {"allowed_support_kinds": ["direct"]},
            "then": {
                "max_inference_depth": {"equals": 0},
                "source_obligation_candidate_ids": {"exact_item_count": 1},
            },
        },
        {
            "if": {"allowed_support_kinds": ["inferred"]},
            "then": {
                "max_inference_depth": {"minimum": 1},
                "dependency_component_ids": {"minimum_nonempty_items": 1},
                "source_obligation_candidate_ids": {"exact_item_count": 0},
            },
        },
        {
            "if": {"allowed_support_kinds": ["direct", "inferred"]},
            "then": {
                "max_inference_depth": {"minimum": 1},
                "dependency_component_ids": {"minimum_nonempty_items": 1},
                "source_obligation_candidate_ids": {"exact_item_count": 1},
            },
        },
        {
            "allowed_support_kinds": {
                "exact_ordered_combinations": [
                    list(item)
                    for item in SEARCH_PLANNER_MODEL_ALLOWED_SUPPORT_KIND_COMBINATIONS
                ]
            }
        },
        {
            "answer_components": {
                "at_least_one_item_where": {"requirement_posture": "required"}
            }
        },
    ],
    "source_obligation_candidate": _object_contract(
        required=True,
        required_fields=(
            "candidate_id",
            "obligation_kind",
            "component_candidate_ids",
        ),
        fields={
            "candidate_id": _text_contract("default_text", required=True),
            "obligation_kind": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_KINDS,
            ),
            "component_candidate_ids": _text_array_contract(
                "default_text",
                required=True,
                minimum_items=1,
            ),
            "strictness": _text_contract(
                "default_text",
                required=False,
                enum_values=SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_STRICTNESSES,
                nonempty=False,
                adapter_normalization="empty text is omitted",
            ),
            "metadata": {
                "json_type": "object",
                "required": False,
                "adapter_normalization": "safe metadata only",
            },
        },
    ),
    "component_search_requirement": _object_contract(
        required=True,
        required_fields=(
            "component_id",
            "requirement_id",
            "requirement_summary",
            "source_obligation_candidate_ids",
            "metadata",
        ),
        fields={
            "component_id": _text_contract("default_text", required=True),
            "requirement_id": _text_contract("default_text", required=True),
            "requirement_summary": _text_contract(
                "component_search_requirement_summary",
                required=True,
                adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
            ),
            "source_obligation_candidate_ids": _text_array_contract(
                "default_text",
                required=True,
                minimum_items=1,
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
                adapter_normalization="empty text is omitted",
            ),
            "metadata": {
                "json_type": "object",
                "required": True,
                "required_fields": ["query_strategy_candidates"],
                "fields": {
                    "query_strategy_candidates": {
                        "json_type": "array",
                        "required": True,
                        "minimum_items": 1,
                        "item_contract": "query_strategy_candidate",
                    }
                },
            },
        },
    ),
    "component_search_requirement_cross_field_conditions": [
        {
            "for_each_component_where": {
                "allowed_support_kinds": ["inferred"]
            },
            "then": {
                "owned_component_search_requirements": {"exact_item_count": 0}
            },
        },
        {
            "for_each_component_where": {
                "requirement_posture": "required",
                "allowed_support_kinds_contains": "direct",
            },
            "then": {
                "owned_query_strategy_candidates": {
                    "candidate_kind": "primary",
                    "exact_item_count": 1,
                }
            },
        },
    ],
    "query_strategy_candidate": _object_contract(
        required=True,
        required_fields=(
            "strategy_id",
            "component_id",
            "candidate_kind",
            "candidate_query_text",
            "requested_role",
            "source_obligation_candidate_ids",
            "distinct_need_justification",
            "recon_requirement",
        ),
        fields={
            "strategy_id": _text_contract("default_text", required=True),
            "component_id": _text_contract("default_text", required=True),
            "candidate_kind": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_QUERY_CANDIDATE_KINDS,
            ),
            "candidate_query_text": _text_contract(
                "query_strategy_candidate_query",
                required=True,
            ),
            "requested_role": _text_contract(
                "default_text",
                required=True,
                enum_values=SEARCH_PLANNER_MODEL_QUERY_ROLES,
            ),
            "source_obligation_candidate_ids": _text_array_contract(
                "default_text",
                required=True,
                minimum_items=1,
            ),
            "distinct_need_justification": _text_contract(
                "query_strategy_distinct_need_justification",
                required=True,
            ),
            "recon_requirement": {
                "json_type": "object",
                "required": True,
                "required_fields": [
                    "posture",
                    "unresolved_dimension_ids",
                    "candidate_queries",
                ],
                "fields": {
                    "posture": _text_contract(
                        "default_text",
                        required=True,
                        enum_values=SEARCH_PLANNER_MODEL_RECON_POSTURES,
                    ),
                    "unresolved_dimension_ids": _text_array_contract(
                        "default_text",
                        required=True,
                        minimum_items=0,
                    ),
                    "candidate_queries": {
                        "json_type": "array",
                        "required": True,
                        "minimum_items": 0,
                        "item_contract": "recon_candidate_query",
                    },
                },
            },
        },
    ),
    "query_strategy_candidate_cross_field_conditions": [
        {
            "component_id": {
                "must_equal": "parent component_search_requirement.component_id"
            }
        },
        {
            "source_obligation_candidate_ids": {
                "each_item_must_reference": "source_obligation_candidate.candidate_id"
            }
        },
    ],
    "recon_candidate_query": _object_contract(
        required=True,
        required_fields=("dimension_id", "candidate_query_text", "query_kind"),
        fields={
            "dimension_id": _text_contract("default_text", required=True),
            "candidate_query_text": _text_contract(
                "recon_candidate_query",
                required=True,
            ),
            "query_kind": _text_contract("default_text", required=True),
        },
    ),
    "relationship_hypothesis": _object_contract(
        required=True,
        required_fields=(
            "hypothesis_id",
            "target_component_id",
            "premise_component_ids",
            "relationship_summary",
        ),
        fields={
            "hypothesis_id": _text_contract("default_text", required=True),
            "target_component_id": _text_contract("default_text", required=True),
            "premise_component_ids": _text_array_contract(
                "default_text",
                required=True,
                minimum_items=1,
            ),
            "relationship_summary": _text_contract(
                "relationship_hypothesis_summary",
                required=True,
                adapter_normalization=_REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
            ),
        },
    ),
    "contract_amendment_candidate": _object_contract(
        required=True,
        required_fields=(),
        fields={
            "candidate_id": _text_contract(
                "default_text",
                required=False,
                nonempty=False,
                adapter_normalization="empty text is omitted",
            ),
            "operation_kind": _text_contract(
                "default_text",
                required=False,
                nonempty=False,
                adapter_normalization="empty text is omitted",
            ),
            "summary": _text_contract(
                "contract_amendment_candidate_summary",
                required=False,
                nonempty=False,
                adapter_normalization="empty text is omitted",
            ),
            "metadata": {
                "json_type": "object",
                "required": False,
                "adapter_normalization": "safe metadata only",
            },
        },
    ),
}


def build_search_planner_model_prompt(planner_input: Mapping[str, Any]) -> str:
    """Build a strict JSON planner prompt from sanitized adapter input."""

    query_text = str(planner_input.get("user_query_text_for_planning") or "")
    prompt_payload = {
        "schema_version": SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION,
        "planner_input": {
            "run_id": planner_input.get("run_id"),
            "request_id": planner_input.get("request_id"),
            "requested_mode": planner_input.get("requested_mode"),
            "user_query_text_for_planning": query_text,
            "user_query_ref": planner_input.get("user_query_ref"),
            "safe_context": planner_input.get("safe_context"),
            "route_context_ref": planner_input.get("route_context_ref"),
            "run_context_ref": planner_input.get("run_context_ref"),
            "parent_contract_refs": planner_input.get("parent_contract_refs"),
            "closed_surface_flags": planner_input.get("closed_surface_flags"),
        },
        "output_schema": SEARCH_PLANNER_MODEL_OUTPUT_SCHEMA,
    }
    instructions = [
        "SEARCHPLANNER MODEL TASK",
        f"Prompt schema: {SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION}",
        "",
        "Role and authority:",
        "- You are SearchPlanner, not Author.",
        "- Interpret the user query into a structured search and answer contract plan.",
        "- You may propose; RunKernel governs.",
        "- Existing reducers own accepted state.",
        "- Do not answer the user.",
        "- Do not cite sources.",
        "- Do not claim evidence was found.",
        "- Do not mark source obligations satisfied.",
        "- Do not execute search.",
        "- Do not request live fetch, read, or retrieval.",
        "- Do not invoke Scout.",
        "- Do not invoke SearchExecutor.",
        "- Do not create or mutate initial_answer_contract or current_answer_contract.",
        "- Do not create FinalAnswerPacket, Author input, citations, SemanticObservation, ComponentCoverage, or EvidenceLedger custody.",
        "",
        "Planning rules:",
        "- Every enum field must use an exact value listed in output_schema. Every required object or array must satisfy its declared type and cardinality. Omit an optional field rather than inventing an unsupported value.",
        "- The seven required narrative fields must contain meaningful non-whitespace text after whitespace normalization; never emit empty or whitespace-only values, and keep normalized text within each declared max_length.",
        "- You own the intended question, the distinction between request and context, and the warranted component structure.",
        "- Propose from one through five required answer components; five is a ceiling, never a target.",
        "- Use one component for one central intention even when the utterance is long, narrated, imprecise, or self-correcting.",
        "- Use multiple components only for genuinely distinct answer needs; do not turn background, examples, qualifications, or explanatory asides into components.",
        "- Treat safe-context and supplied-context references or summaries as planning context, not evidence and not automatic components.",
        "- Represent dependencies only through dependency_component_ids that name components in this same proposal; do not invent a new graph schema.",
        "- Classify every component as user_facing_answer_target or supporting_premise.",
        "- Keep component purpose orthogonal to direct versus inferred support.",
        "- Direct-only components require max_inference_depth 0 and exactly one component-owned source obligation.",
        "- Inferred-only components require dependencies, max_inference_depth of at least 1, and no source obligation or component-local search work.",
        "- Direct-or-inferred components require dependencies, max_inference_depth of at least 1, and exactly one direct-route source obligation.",
        "- Use only [direct], [inferred], or [direct, inferred] as allowed_support_kinds, in that order.",
        "- Fast and Balanced allow semantic inference depth 1; Deep allows depth 2.",
        "- Use only the source-obligation kinds and strictness values listed in the output schema.",
        "- Represent uncertainty as semantic slots, material ambiguity, assumptions, or deferred outputs.",
        "- You may identify that disambiguation is needed later without activating Scout.",
        "- You may propose component_search_requirements, but they are non-executing requirements only.",
        "- Do not create component_search_requirements for inferred-only components.",
        "- Put bounded provider-neutral initial query strategies under each requirement's metadata.query_strategy_candidates.",
        "- Give every required answer component one distinct primary candidate; do not rely on one broad query to cover unnamed components.",
        "- A secondary candidate requires a materially distinct accepted component or source-obligation need and an explicit distinct_need_justification.",
        "- Do not create a secondary merely because capacity may be available.",
        "- Use only initial, official_bias, canonical_bias, recency, disambiguation, or recon_rewrite as requested roles.",
        "- A query strategy may request domain/date/document-family constraints, but it must not select a provider, provider order, depth, variant, model, or fallback.",
        "- Recon needs must identify distinct unresolved dimensions and remain non-evidence direction material.",
        "- Do not encode Fast/Balanced/Deep query totals; allocation cardinality is owned by a separate versioned runtime policy.",
        "- contract_amendment_candidates, if present, are deferred/proposal-only.",
        "- relationship_hypotheses, if present, are bounded local noncanonical planning hypotheses only; they do not support an answer, create graph authority, or construct search work.",
        "- Use concise rationale fields only; do not include chain-of-thought.",
        "Strict JSON output contract:",
        *(
            f"- {requirement}"
            for requirement in SEARCH_PLANNER_MODEL_STRICT_JSON_OUTPUT_CONTRACT
        ),
        "",
        "Sanitized planner input JSON:",
        _json(prompt_payload),
    ]
    return "\n".join(instructions)


def prompt_metadata(prompt: str) -> dict[str, Any]:
    return {
        "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_length": len(prompt),
        "raw_prompt_retained": False,
    }


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


__all__ = [
    "SEARCH_PLANNER_MODEL_ALLOWED_SUPPORT_KIND_COMBINATIONS",
    "SEARCH_PLANNER_MODEL_COMPONENT_PURPOSES",
    "SEARCH_PLANNER_MODEL_MATERIALITY_VALUES",
    "SEARCH_PLANNER_MODEL_OUTPUT_SCHEMA",
    "SEARCH_PLANNER_MODEL_OPTIONAL_TOP_LEVEL_FIELDS",
    "SEARCH_PLANNER_MODEL_PARTIAL_ANSWER_POLICIES",
    "SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION",
    "SEARCH_PLANNER_MODEL_QUERY_CANDIDATE_KINDS",
    "SEARCH_PLANNER_MODEL_QUERY_ROLES",
    "SEARCH_PLANNER_MODEL_RECON_POSTURES",
    "SEARCH_PLANNER_MODEL_REQUIRED_TOP_LEVEL_FIELDS",
    "SEARCH_PLANNER_MODEL_REQUIREMENT_POSTURES",
    "SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_KINDS",
    "SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_STATUSES",
    "SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_KINDS",
    "SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_STRICTNESSES",
    "SEARCH_PLANNER_MODEL_STRICT_JSON_OUTPUT_CONTRACT",
    "SEARCH_PLANNER_MODEL_SUPPORT_KINDS",
    "SEARCH_PLANNER_MODEL_SYSTEM_PROMPT",
    "SEARCH_PLANNER_MODEL_TEXT_LIMITS",
    "build_search_planner_model_prompt",
    "prompt_metadata",
]
