"""Prompt boundary for the AG-SEARCH-PLANNER-REVISION-01 adapter.

The prompt builder is pure. Callers may retain only metadata from
``prompt_metadata``; raw prompt text must not be persisted.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping

SEARCH_PLANNER_REVISION_MODEL_PROMPT_SCHEMA_VERSION = (
    "search_planner_revision_model_prompt_ag_search_planner_revision_01_v2"
)

SEARCH_PLANNER_REVISION_MODEL_SYSTEM_PROMPT = (
    "You are SearchPlannerRevision. You are not Author, Scout, SearchExecutor, "
    "a citation formatter, or an evidence ledger. Return only strict JSON "
    "planner-revision proposal data."
)

SEARCH_PLANNER_REVISION_MODEL_OUTPUT_SCHEMA: dict[str, Any] = {
    "required_top_level_fields": [
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
    ],
    "optional_top_level_fields": [
        "revised_source_obligation_candidates",
        "source_obligation_focus_updates",
        "planner_revision_notes",
        "confidence_posture",
        "revision_posture",
    ],
    "allowed_amendment_operation_kinds": [
        "add_caveat",
        "strengthen_source_obligation",
    ],
    "forbidden_operation_kinds": [
        "resolve_slot",
        "mark_requirement_satisfied",
        "mark_source_obligation_satisfied",
    ],
}


def build_search_planner_revision_model_prompt(
    revision_input: Mapping[str, Any],
) -> str:
    """Build a strict JSON revision prompt from sanitized adapter input."""

    prompt_payload = {
        "schema_version": SEARCH_PLANNER_REVISION_MODEL_PROMPT_SCHEMA_VERSION,
        "revision_input": {
            "run_id": revision_input.get("run_id"),
            "request_id": revision_input.get("request_id"),
            "parent_search_planner_proposal_ref": revision_input.get(
                "parent_search_planner_proposal_ref"
            ),
            "parent_scout_disambiguation_report_ref": revision_input.get(
                "parent_scout_disambiguation_report_ref"
            ),
            "parent_initial_contract_ref": revision_input.get(
                "parent_initial_contract_ref"
            ),
            "parent_current_contract_ref": revision_input.get(
                "parent_current_contract_ref"
            ),
            "component_id": revision_input.get("component_id"),
            "consumed_ambiguity_dimension_ids": revision_input.get(
                "consumed_ambiguity_dimension_ids"
            ),
            "consumed_scout_hint_ids": revision_input.get("consumed_scout_hint_ids"),
            "scout_directional_context": revision_input.get("scout_directional_context"),
            "safe_revision_context": revision_input.get("safe_revision_context"),
            "closed_surface_flags": revision_input.get("closed_surface_flags"),
        },
        "output_schema": SEARCH_PLANNER_REVISION_MODEL_OUTPUT_SCHEMA,
    }
    instructions = [
        "SEARCHPLANNERREVISION MODEL TASK",
        f"Prompt schema: {SEARCH_PLANNER_REVISION_MODEL_PROMPT_SCHEMA_VERSION}",
        "",
        "Role and authority:",
        "- You are SearchPlannerRevision, not Author.",
        "- Consume the Scout DisambiguationReport only as disambiguation direction.",
        "- Scout hints are not evidence.",
        "- Scout hints are not citations.",
        "- Scout hints do not satisfy source obligations.",
        "- You may propose; RunKernel governs.",
        "- Contract changes must go through ContractAmendmentRecord admission/application.",
        "- Do not answer the user.",
        "- Do not cite sources.",
        "- Do not claim evidence was found.",
        "- Do not mark requirements satisfied.",
        "- Do not resolve material slots unless user-confirmed or explicitly non-material.",
        "- For this phase, prefer caveats or source-focus adjustments.",
        "- Do not invoke Scout.",
        "- Do not invoke SearchExecutor.",
        "- Do not execute search.",
        "- Do not fetch, read, or retrieve.",
        "- Do not create EvidenceLedger custody.",
        "- Do not create FinalAnswerPacket or Author input.",
        "",
        "Revision rules:",
        "- Produce revision proposal data and passive amendment candidates only.",
        "- The preferred proof amendment is add_caveat.",
        "- strengthen_source_obligation is allowed only as a source-focus proposal.",
        "- Do not emit resolve_slot.",
        "- Do not emit mark_requirement_satisfied.",
        "- Every amendment candidate must keep scout_hints_are_evidence, citation_eligible, source_obligation_satisfied, evidence_admitted, and contract_mutation_applied false.",
        "- Use concise rationale fields only; do not include chain-of-thought.",
        "- Return strict JSON only. Do not wrap it in Markdown fences.",
        "",
        "Sanitized revision input JSON:",
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
    "SEARCH_PLANNER_REVISION_MODEL_OUTPUT_SCHEMA",
    "SEARCH_PLANNER_REVISION_MODEL_PROMPT_SCHEMA_VERSION",
    "SEARCH_PLANNER_REVISION_MODEL_SYSTEM_PROMPT",
    "build_search_planner_revision_model_prompt",
    "prompt_metadata",
]
