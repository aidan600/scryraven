"""Prompt and schema boundary for the AG-SEARCH-PLANNER-MODEL-01 adapter.

The prompt builder is pure: callers may retain only the metadata returned by
``prompt_metadata`` and must not store the prompt text.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping

from core.search_work_plan import SourceObligationKind, SourceObligationStrictness

SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION = "search_planner_model_prompt_ag_search_planner_model_01_v1"

SEARCH_PLANNER_MODEL_SYSTEM_PROMPT = (
    "You are SearchPlanner and own semantic interpretation of the supplied human "
    "utterance and bounded planning context. You are not Author, Scout, SearchExecutor, "
    "a citation formatter, or an evidence ledger. Return only strict JSON planner proposal data."
)

SEARCH_PLANNER_MODEL_OUTPUT_SCHEMA: dict[str, Any] = {
    "required_top_level_fields": [
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
    ],
    "optional_top_level_fields": [
        "contract_amendment_candidates",
        "planner_notes",
        "model_confidence_posture",
    ],
    "semantic_slot_required_fields": [
        "slot_id",
        "slot_kind",
        "status",
        "materiality",
    ],
    "answer_component_required_fields": [
        "component_id",
        "component_revision",
        "user_facing_label",
        "user_facing_question",
        "requirement_posture",
        "acceptance_criteria",
        "semantic_slot_ids",
        "source_obligation_candidate_ids",
        "allowed_support_kinds",
        "max_inference_depth",
        "materiality",
    ],
    "answer_component_count": {"minimum": 1, "maximum": 5},
    "source_obligation_candidate_required_fields": [
        "candidate_id",
        "obligation_kind",
        "component_candidate_ids",
    ],
    "source_obligation_kind_values": [item.value for item in SourceObligationKind],
    "source_obligation_strictness_values": [
        item.value for item in SourceObligationStrictness
    ],
    "component_search_requirement_required_fields": [
        "component_id",
        "requirement_id",
        "requirement_summary",
        "source_obligation_candidate_ids",
    ],
    "component_search_requirement_metadata": {
        "query_strategy_candidates": {
            "required_fields": [
                "strategy_id",
                "component_id",
                "candidate_kind",
                "candidate_query_text",
                "requested_role",
                "source_obligation_candidate_ids",
                "distinct_need_justification",
                "recon_requirement",
            ],
            "candidate_kind_values": ["primary", "secondary"],
            "requested_role_values": [
                "initial",
                "official_bias",
                "canonical_bias",
                "recency",
                "disambiguation",
                "recon_rewrite",
            ],
            "recon_posture_values": ["not_needed", "optional", "required"],
        }
    },
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
        "- You own the intended question, the distinction between request and context, and the warranted component structure.",
        "- Propose from one through five required answer components; five is a ceiling, never a target.",
        "- Use one component for one central intention even when the utterance is long, narrated, imprecise, or self-correcting.",
        "- Use multiple components only for genuinely distinct answer needs; do not turn background, examples, qualifications, or explanatory asides into components.",
        "- Treat safe-context and supplied-context references or summaries as planning context, not evidence and not automatic components.",
        "- Represent dependencies only through dependency_component_ids that name components in this same proposal; do not invent a new graph schema.",
        "- Required answer components must be explicit and source-bound.",
        "- Use only the source-obligation kinds and strictness values listed in the output schema.",
        "- Represent uncertainty as semantic slots, material ambiguity, assumptions, or deferred outputs.",
        "- You may identify that disambiguation is needed later without activating Scout.",
        "- You may propose component_search_requirements, but they are non-executing requirements only.",
        "- Put bounded provider-neutral initial query strategies under each requirement's metadata.query_strategy_candidates.",
        "- Give every required answer component one distinct primary candidate; do not rely on one broad query to cover unnamed components.",
        "- A secondary candidate requires a materially distinct accepted component or source-obligation need and an explicit distinct_need_justification.",
        "- Do not create a secondary merely because capacity may be available.",
        "- Use only initial, official_bias, canonical_bias, recency, disambiguation, or recon_rewrite as requested roles.",
        "- A query strategy may request domain/date/document-family constraints, but it must not select a provider, provider order, depth, variant, model, or fallback.",
        "- Recon needs must identify distinct unresolved dimensions and remain non-evidence direction material.",
        "- Do not encode Fast/Balanced/Deep query totals; allocation cardinality is owned by a separate versioned runtime policy.",
        "- contract_amendment_candidates, if present, are deferred/proposal-only.",
        "- Use concise rationale fields only; do not include chain-of-thought.",
        "- Return strict JSON only. Do not wrap it in Markdown fences.",
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
    "SEARCH_PLANNER_MODEL_OUTPUT_SCHEMA",
    "SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION",
    "SEARCH_PLANNER_MODEL_SYSTEM_PROMPT",
    "build_search_planner_model_prompt",
    "prompt_metadata",
]
