"""Shared model-visible contract policy for PlannerRevision output.

This module owns only the finite policy vocabulary that the model prompt and
the model-output adapter must share.  It grants no runtime authority and does
not sanitize, admit, or apply a PlannerRevision proposal.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

SEARCH_PLANNER_REVISION_MODEL_OUTPUT_CONTRACT_FORMAT = "static_model_visible_output_contract_v1"

SEARCH_PLANNER_REVISION_MODEL_STRICT_JSON_OUTPUT_CONTRACT = (
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

SEARCH_PLANNER_REVISION_REQUIRED_TOP_LEVEL_FIELDS = (
    "revised_question_meaning_summary",
    "semantic_slot_updates",
    "answer_component_updates",
    "component_search_requirement_updates",
    "mandatory_caveats",
    "prohibited_upgrades",
    "normalization_obligations",
    "assumptions",
    "unresolved_ambiguities",
    "consumed_ambiguity_dimension_ids",
    "consumed_scout_hint_ids",
    "amendment_candidates",
    "closed_surface_flags",
)

SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS = (
    "revised_source_obligation_candidates",
    "source_obligation_focus_updates",
    "planner_revision_notes",
    "confidence_posture",
    "revision_posture",
)

SEARCH_PLANNER_REVISION_MODEL_TEXT_LIMITS: Mapping[str, int] = MappingProxyType(
    {
        "revised_question_meaning_summary": 500,
        "mandatory_caveats": 360,
        "prohibited_upgrades": 260,
        "normalization_obligations": 260,
        "assumptions": 260,
        "identifier": 160,
        "planner_revision_notes": 300,
        "confidence_posture": 120,
        "revision_posture": 120,
        "amendment_candidate_caveat": 360,
        "amendment_candidate_summary": 300,
    }
)

SEARCH_PLANNER_REVISION_SENSITIVE_RAW_PRIVATE_MEMBER_NAMES = frozenset(
    {
        "api_key",
        "cache",
        "cache_row",
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
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "token",
        "unbounded_text",
    }
)

SEARCH_PLANNER_REVISION_FORBIDDEN_AUTHORITY_MEMBER_NAMES = frozenset(
    {
        "accepted_amendment",
        "accepted_contract",
        "answer",
        "author_input",
        "canonical_coverage",
        "citation",
        "citations",
        "component_coverage_record",
        "current_answer_contract",
        "evidence",
        "evidence_ledger_admission",
        "final_answer",
        "final_answer_packet",
        "initial_answer_contract",
        "search_executor",
        "search_judgment_decision",
        "semantic_observation",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

SEARCH_PLANNER_REVISION_DANGEROUS_TRUE_MEMBER_NAMES = frozenset(
    {
        "accepted_authority",
        "amendment_admitted",
        "amendment_applied",
        "author_behavior_changed",
        "author_executor_invoked",
        "author_input_created",
        "citation_behavior_changed",
        "citation_eligible",
        "citation_rendered",
        "component_satisfied",
        "constructs_search_work_plan",
        "contract_mutation_applied",
        "current_answer_contract_mutated",
        "evidence_admitted",
        "fetch_read_retrieval_behavior_changed",
        "final_answer_packet_created",
        "initial_answer_contract_mutated",
        "live_model_called",
        "live_provider_calls_executed",
        "live_validation_run",
        "model_called",
        "partial_answer_readiness_changed",
        "provider_called",
        "provider_search_behavior_changed",
        "query_plan_activated",
        "raw_model_response_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "raw_trace_retained",
        "runtime_behavior_changed",
        "scout_hints_are_evidence",
        "scout_runtime_activated",
        "search_executed",
        "search_executor_runtime_activated",
        "search_judgment_decided",
        "search_work_plan_activated",
        "search_work_plan_constructed",
        "source_obligation_satisfied",
        "sufficiency_decided",
    }
)

SEARCH_PLANNER_REVISION_ALLOWED_AMENDMENT_OPERATION_KINDS = frozenset({"add_caveat", "strengthen_source_obligation"})

SEARCH_PLANNER_REVISION_FORBIDDEN_AMENDMENT_OPERATION_KINDS = frozenset(
    {
        "mark_requirement_satisfied",
        "mark_source_obligation_satisfied",
        "resolve_slot",
    }
)

_SAFE_OBJECT_ARRAY_FIELDS = (
    "semantic_slot_updates",
    "answer_component_updates",
    "component_search_requirement_updates",
    "unresolved_ambiguities",
    "revised_source_obligation_candidates",
    "source_obligation_focus_updates",
)

_RUNTIME_DERIVED_AMENDMENT_FIELDS = (
    "proposal_only",
    "passive",
    "planner_revision_id",
    "parent_search_planner_proposal_ref",
    "parent_scout_disambiguation_report_ref",
    "contract_amendment_record",
    "amendment_admitted",
    "amendment_applied",
    "contract_mutation_applied",
)


def _text_contract(
    limit_key: str,
    *,
    required: bool,
    nonempty: bool = False,
) -> dict[str, Any]:
    contract: dict[str, Any] = {
        "json_type": "string",
        "required": required,
        "max_length": SEARCH_PLANNER_REVISION_MODEL_TEXT_LIMITS[limit_key],
    }
    if nonempty:
        contract["nonempty_after_normalization"] = True
        contract["adapter_normalization"] = (
            "leading and trailing whitespace is removed and internal whitespace runs are collapsed"
        )
    return contract


def _safe_object_array_contract(*, required: bool) -> dict[str, Any]:
    return {
        "json_type": "array",
        "required": required,
        "minimum_items": 0,
        "items": "safe JSON objects",
        "authority_posture": "proposal metadata only; no raw/private or closed-authority members",
    }


def _text_array_contract(
    limit_key: str,
    *,
    required: bool,
    minimum_nonempty_items: int = 0,
) -> dict[str, Any]:
    return {
        "json_type": "array",
        "required": required,
        "minimum_items": 0,
        "minimum_nonempty_items": minimum_nonempty_items,
        "items": {
            "json_type": "string",
            "max_length": SEARCH_PLANNER_REVISION_MODEL_TEXT_LIMITS[limit_key],
        },
    }


def build_search_planner_revision_model_visible_output_contract() -> dict[str, Any]:
    """Return the static contract shown to a PlannerRevision model."""

    top_level_fields: dict[str, Any] = {
        "revised_question_meaning_summary": _text_contract(
            "revised_question_meaning_summary",
            required=True,
            nonempty=True,
        ),
        **{field: _safe_object_array_contract(required=True) for field in _SAFE_OBJECT_ARRAY_FIELDS[:4]},
        "mandatory_caveats": _text_array_contract(
            "mandatory_caveats",
            required=True,
        ),
        "prohibited_upgrades": _text_array_contract(
            "prohibited_upgrades",
            required=True,
        ),
        "normalization_obligations": _text_array_contract(
            "normalization_obligations",
            required=True,
        ),
        "assumptions": _text_array_contract("assumptions", required=True),
        "consumed_ambiguity_dimension_ids": {
            **_text_array_contract(
                "identifier",
                required=True,
                minimum_nonempty_items=1,
            ),
            "copy_exact_input_ids": True,
            "preserve_input_order": True,
            "instruction": "Copy every supplied ambiguity dimension ID exactly; do not invent, omit, rename, or reorder IDs.",
        },
        "consumed_scout_hint_ids": {
            **_text_array_contract("identifier", required=True),
            "copy_exact_input_ids": True,
            "preserve_input_order": True,
            "instruction": "Copy every supplied Scout hint ID exactly; do not invent, omit, rename, or reorder IDs. Use [] when no hint IDs are supplied.",
        },
        "amendment_candidates": {
            "json_type": "array",
            "required": True,
            "minimum_items": 0,
            "item_contract": "amendment_candidate",
        },
        "closed_surface_flags": {
            "json_type": "object",
            "required": True,
            "preferred_output": {},
            "rule": "Prefer {}. If a permitted flag is emitted, its JSON value must be false; no flag may be true.",
        },
        **{field: _safe_object_array_contract(required=False) for field in _SAFE_OBJECT_ARRAY_FIELDS[4:]},
        "planner_revision_notes": _text_array_contract(
            "planner_revision_notes",
            required=False,
        ),
        "confidence_posture": _text_contract(
            "confidence_posture",
            required=False,
        ),
        "revision_posture": _text_contract(
            "revision_posture",
            required=False,
        ),
    }
    return {
        "contract_format": SEARCH_PLANNER_REVISION_MODEL_OUTPUT_CONTRACT_FORMAT,
        "strict_json_output_contract": list(SEARCH_PLANNER_REVISION_MODEL_STRICT_JSON_OUTPUT_CONTRACT),
        # Preserve the v2 prompt-schema keys for existing consumers while the
        # nested contracts below provide the complete model-visible shape.
        "required_top_level_fields": list(SEARCH_PLANNER_REVISION_REQUIRED_TOP_LEVEL_FIELDS),
        "optional_top_level_fields": list(SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS),
        "allowed_amendment_operation_kinds": sorted(
            SEARCH_PLANNER_REVISION_ALLOWED_AMENDMENT_OPERATION_KINDS
        ),
        "forbidden_operation_kinds": sorted(
            SEARCH_PLANNER_REVISION_FORBIDDEN_AMENDMENT_OPERATION_KINDS
        ),
        "top_level": {
            "json_type": "object",
            "required_fields": list(SEARCH_PLANNER_REVISION_REQUIRED_TOP_LEVEL_FIELDS),
            "optional_fields": list(SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS),
            "additional_top_level_fields": "Do not invent additional top-level fields to explain reasoning or authority posture.",
            "fields": top_level_fields,
        },
        "amendment_candidate": {
            "json_type": "object",
            "allowed_model_authored_fields": [
                "candidate_id",
                "operation_kind",
                "caveat",
                "required_caveats",
                "summary",
                "component_id",
                "metadata",
            ],
            "fields": {
                "candidate_id": _text_contract("identifier", required=False),
                "operation_kind": {
                    "json_type": "string",
                    "required": False,
                    "adapter_default": "add_caveat",
                    "allowed_values": sorted(SEARCH_PLANNER_REVISION_ALLOWED_AMENDMENT_OPERATION_KINDS),
                    "forbidden_values": sorted(SEARCH_PLANNER_REVISION_FORBIDDEN_AMENDMENT_OPERATION_KINDS),
                },
                "caveat": _text_contract(
                    "amendment_candidate_caveat",
                    required=False,
                ),
                "required_caveats": _text_array_contract(
                    "amendment_candidate_caveat",
                    required=False,
                ),
                "summary": _text_contract(
                    "amendment_candidate_summary",
                    required=False,
                ),
                "component_id": _text_contract("identifier", required=False),
                "metadata": {
                    "json_type": "object",
                    "required": False,
                    "authority_posture": "safe proposal metadata only",
                },
            },
            "operation_conditions": [
                {
                    "operation_kind": "add_caveat",
                    "downstream_requirement": "Provide a usable nonempty caveat; downstream runtime requires it for an add_caveat proposal.",
                },
                {
                    "operation_kind": "strengthen_source_obligation",
                    "authority_posture": "source-focus proposal only; never claim satisfaction.",
                },
            ],
            "runtime_derived_fields_not_model_authored": list(_RUNTIME_DERIVED_AMENDMENT_FIELDS),
        },
        "global_member_name_rules": {
            "scope": "These rules apply everywhere in model output, including nested safe-metadata objects and objects inside arrays.",
            "forbidden_authority_member_names": sorted(SEARCH_PLANNER_REVISION_FORBIDDEN_AUTHORITY_MEMBER_NAMES),
            "sensitive_raw_private_member_names": sorted(SEARCH_PLANNER_REVISION_SENSITIVE_RAW_PRIVATE_MEMBER_NAMES),
            "sensitive_raw_private_member_name_patterns": ["raw_*"],
            "sensitive_content_rule": (
                "Do not include raw or private provider, cache, database, prompt, trace, payload, credential, or secret content anywhere in values or member names."
            ),
            "dangerous_true_member_names": sorted(SEARCH_PLANNER_REVISION_DANGEROUS_TRUE_MEMBER_NAMES),
            "dangerous_true_rule": "If a listed posture member appears and is not otherwise forbidden, its value must be JSON false. Prefer omission.",
            "rule_precedence": "A sensitive/raw/private or forbidden-authority member is never allowed; the false-only rule does not make it allowed.",
        },
    }


__all__ = [
    "SEARCH_PLANNER_REVISION_ALLOWED_AMENDMENT_OPERATION_KINDS",
    "SEARCH_PLANNER_REVISION_DANGEROUS_TRUE_MEMBER_NAMES",
    "SEARCH_PLANNER_REVISION_FORBIDDEN_AMENDMENT_OPERATION_KINDS",
    "SEARCH_PLANNER_REVISION_FORBIDDEN_AUTHORITY_MEMBER_NAMES",
    "SEARCH_PLANNER_REVISION_MODEL_OUTPUT_CONTRACT_FORMAT",
    "SEARCH_PLANNER_REVISION_MODEL_STRICT_JSON_OUTPUT_CONTRACT",
    "SEARCH_PLANNER_REVISION_MODEL_TEXT_LIMITS",
    "SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS",
    "SEARCH_PLANNER_REVISION_REQUIRED_TOP_LEVEL_FIELDS",
    "SEARCH_PLANNER_REVISION_SENSITIVE_RAW_PRIVATE_MEMBER_NAMES",
    "build_search_planner_revision_model_visible_output_contract",
]
