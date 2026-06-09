"""Prompt builder for optional RunAuthority search judgment adaptation."""

from __future__ import annotations

import json
from typing import Any, Mapping

from core.run_authority_search_judgment import (
    RUN_AUTHORITY_SEARCH_JUDGMENT_SCHEMA_VERSION,
    RunSearchJudgmentInput,
    safe_json,
    stable_hash,
)

RUN_AUTHORITY_SEARCH_JUDGMENT_SYSTEM_PROMPT = """You are a careful research director deciding the next retrieval action against a committed contract and evidence ledger.

You are not an Author, not a search executor, not a citation formatter, and not a provider router with unlimited freedom. Judge only the next retrieval action. Treat helper assessments as advisory unless the RunAuthority contract and EvidenceLedger support promoting them.

Preserve source hierarchy. Lower-tier evidence may be a useful lead, but it does not satisfy official/current, legal/current-primary, canonical-document, source-bound numeric, or user-document requirements. Stale or off-topic evidence does not satisfy current or source-fit requirements. Reject redundant continuation queries unless they target a new active gap or source class.

Output strict JSON matching the schema. Include concise rationale fields only, not chain-of-thought. Do not include raw retrieved content, raw prompts, raw provider payloads, logs, database rows, caches, secrets, full traces, or output packets.
"""


def build_run_authority_search_judgment_prompt(
    judgment_input: RunSearchJudgmentInput,
) -> str:
    """Build a strict JSON prompt from sanitized input facts."""

    payload = safe_json(judgment_input.to_model_payload())
    schema: dict[str, Any] = {
        "schema_version": RUN_AUTHORITY_SEARCH_JUDGMENT_SCHEMA_VERSION,
        "required_object_fields": [
            "decision",
            "classifications",
            "satisfaction",
            "gaps",
            "redundancy",
            "continuation",
            "target_source_classes",
            "recommended_queries",
            "helper_assessments",
            "insufficient_posture",
            "rationale",
        ],
        "decision_values": [
            "stop_satisfied",
            "continue_targeted_search",
            "recover_missing_official_current",
            "recover_missing_legal_primary",
            "recover_missing_canonical",
            "recover_missing_source_bound_numeric",
            "escalate_existing_provider_or_depth",
            "block_redundant_query",
            "stop_insufficient",
            "defer_to_existing_legacy_compatibility",
        ],
        "classification_values": [
            "contract_satisfied",
            "active_required_gap",
            "lower_tier_lead_only",
            "stale_or_off_topic_only",
            "useful_lead_needs_targeted_recovery",
            "redundant_query_blocked",
            "new_source_class_target_allowed",
            "budget_exhausted",
            "insufficient_but_answerable_with_caveats",
            "helper_assessment_rejected",
            "helper_assessment_promoted",
        ],
    }
    return (
        "Decide the next retrieval action for this run.\n\n"
        "Return only JSON. Use the schema below.\n\n"
        f"Schema:\n{json.dumps(schema, sort_keys=True)}\n\n"
        f"Sanitized input:\n{json.dumps(payload, sort_keys=True)}"
    )


def prompt_metadata(prompt: str) -> dict[str, int | str]:
    return {
        "prompt_hash": stable_hash({"prompt": prompt}),
        "prompt_length": len(prompt),
    }


def compact_prompt_ref(prompt: str, *, system_prompt: str | None = None) -> Mapping[str, Any]:
    return {
        "prompt_hash": prompt_metadata(prompt)["prompt_hash"],
        "prompt_length": prompt_metadata(prompt)["prompt_length"],
        "system_prompt_hash": stable_hash({"system_prompt": system_prompt or ""}),
        "prompt_text_retained": False,
        "system_prompt_text_retained": False,
    }


__all__ = [
    "RUN_AUTHORITY_SEARCH_JUDGMENT_SYSTEM_PROMPT",
    "build_run_authority_search_judgment_prompt",
    "compact_prompt_ref",
    "prompt_metadata",
]
