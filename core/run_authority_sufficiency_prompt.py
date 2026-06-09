"""Prompt builder for optional RunAuthority final sufficiency adaptation."""

from __future__ import annotations

import json
from typing import Any, Mapping

from core.run_authority_sufficiency import (
    RUN_AUTHORITY_SUFFICIENCY_SCHEMA_VERSION,
    RunSufficiencyJudgmentInput,
    safe_json,
    stable_hash,
)

RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT = """You are a careful research director deciding whether the committed run contract is fulfilled enough for final answering.

You are not an Author, not a citation formatter, not a search executor, and not an unbounded vibes layer. Judge only final sufficiency against the active RunAuthority contract, EvidenceLedger custody facts, SearchJudgment recovery outcome, and compact compatibility facts.

Use EvidenceLedger custody, not aggregate counts or citation presence, for strong source obligations. Preserve source hierarchy: lower-tier, stale, off-topic, aggregate-only, helper-only, or context-only evidence cannot satisfy official/current, legal/current-primary, canonical-doc, source-bound numeric, or user-document requirements. Preserve conflicts, source-bound numeric unknowns, and indirect-inference labels.

Output strict JSON matching the schema. Include concise rationale fields only, not chain-of-thought. Do not include raw retrieved content, raw prompts, raw model output, raw provider payloads, logs, database rows, caches, secrets, full traces, local output packets, or private artifacts.
"""


def build_run_authority_sufficiency_prompt(
    judgment_input: RunSufficiencyJudgmentInput,
) -> str:
    """Build a strict JSON prompt from sanitized sufficiency input facts."""

    payload = safe_json(judgment_input.to_model_payload())
    schema: dict[str, Any] = {
        "schema_version": RUN_AUTHORITY_SUFFICIENCY_SCHEMA_VERSION,
        "required_object_fields": [
            "decision",
            "final_answer_posture",
            "contract_fulfilled",
            "required_obligations_satisfied",
            "missing_required_obligations",
            "partial_obligations",
            "satisfied_obligations",
            "unresolved_conflicts",
            "indirect_inference_claims",
            "source_bound_numeric_unknowns",
            "weak_or_thin_evidence",
            "failure_card_authorized",
            "final_answer_allowed",
            "mandatory_caveats",
            "prohibited_upgrades",
            "readiness_reasons",
            "final_packet_inputs",
            "rationale",
        ],
        "decision_values": [
            "ready_direct",
            "ready_with_caveats",
            "partial_answer_authorized",
            "insufficient_evidence",
            "block_finalization",
            "recovery_required_but_exhausted",
            "conflict_blocked",
            "inference_only_with_labeling",
            "source_bound_numeric_unknown",
            "defer_to_legacy_compatibility",
        ],
        "final_answer_posture_values": [
            "direct_answer",
            "answer_with_caveats",
            "partial_answer",
            "insufficient_answer",
            "failure_card",
            "blocked",
        ],
        "requirement_assessment_fields": [
            "requirement_id",
            "requirement_kind",
            "required_source_class",
            "required_source_tier",
            "required_currentness",
            "status",
            "reason",
        ],
    }
    return (
        "Decide final answer sufficiency for this run.\n\n"
        "Return only JSON. Use the schema below.\n\n"
        f"Schema:\n{json.dumps(schema, sort_keys=True)}\n\n"
        f"Sanitized input:\n{json.dumps(payload, sort_keys=True)}"
    )


def prompt_metadata(prompt: str) -> dict[str, int | str]:
    return {
        "prompt_hash": stable_hash({"prompt": prompt}),
        "prompt_length": len(prompt),
    }


def compact_prompt_ref(
    prompt: str,
    *,
    system_prompt: str | None = None,
) -> Mapping[str, Any]:
    return {
        "prompt_hash": prompt_metadata(prompt)["prompt_hash"],
        "prompt_length": prompt_metadata(prompt)["prompt_length"],
        "system_prompt_hash": stable_hash({"system_prompt": system_prompt or ""}),
        "prompt_text_retained": False,
        "system_prompt_text_retained": False,
    }


__all__ = [
    "RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT",
    "build_run_authority_sufficiency_prompt",
    "compact_prompt_ref",
    "prompt_metadata",
]
