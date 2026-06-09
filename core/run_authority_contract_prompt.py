"""RunAuthority smart contract-synthesis prompt for AG-92A."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from core.run_authority_contract import stable_hash

RUN_AUTHORITY_CONTRACT_PROMPT_SCHEMA_VERSION = "run_authority_contract_prompt_ag92a_v1"

RUN_AUTHORITY_CONTRACT_SYSTEM_PROMPT = (
    "You are a careful research director. You are not an Author, not a search "
    "helper, not a citation formatter, and not a vibes machine. Write only a "
    "compact JSON RunAuthority contract that preserves source hierarchy law."
)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def build_run_authority_contract_prompt(
    *,
    query: str,
    mode: str | None,
    current_date: str | None,
    route_facts: Mapping[str, Any],
    deterministic_contract_projection: Mapping[str, Any],
    selected_template_ids: Sequence[str],
) -> str:
    """Build the smart-model prompt. Callers store only hash/length metadata."""

    facts = {
        "query": str(query or "")[:1200],
        "mode": mode,
        "current_date": current_date,
        "route_facts": dict(route_facts or {}),
        "selected_template_ids": list(selected_template_ids),
    }
    schema = {
        "contract_id": "string",
        "synthesis_mode": "smart_model_adapted",
        "selected_template_ids": ["string"],
        "user_query_ref": "reuse deterministic user_query_ref",
        "selected_depth": "Fast|Balanced|Deep or configured mode",
        "route_facts_used": "compact object",
        "question_type": "compact taxonomy label",
        "claim_type": "compact taxonomy label",
        "source_requirements": [
            {
                "requirement_id": "stable string",
                "requirement_kind": (
                    "official_current|legal_primary|canonical_docs|academic|"
                    "reputable_secondary|user_document|source_bound_numeric|general"
                ),
                "strictness": "required|preferred|contextual",
                "required_source_class": "string",
                "required_source_tier": "string or null",
                "required_currentness": "string or null",
                "satisfaction_rule": "concise rule",
                "allowed_lower_tier_use": "concise rule",
                "cannot_satisfy_with": ["string"],
                "rationale": "concise rationale, not chain-of-thought",
            }
        ],
        "inference_policy": "compact object",
        "conflict_policy": "compact object",
        "numeric_policy": "compact object",
        "recovery_policy": "compact object",
        "final_posture_policy": "compact object",
        "downstream_hints": "compact object",
    }
    return "\n".join(
        [
            "RUNAUTHORITY CONTRACT SYNTHESIS",
            f"Prompt schema: {RUN_AUTHORITY_CONTRACT_PROMPT_SCHEMA_VERSION}",
            "",
            "Task:",
            "- Choose or adapt source, inference, conflict, numeric, recovery, and final-posture obligations.",
            "- Preserve deterministic source hierarchy. You may add stricter obligations, but do not weaken required ones.",
            "- Distinguish required, preferred, and contextual evidence.",
            "- Treat helper/controller assessments as advisory unless canonical state admits them.",
            "- Preserve unsupported unknowns.",
            "- Forbid citation laundering and inference laundering.",
            "- Do not downgrade official/current/legal/canonical/source-bound obligations because search may be hard.",
            "- Output strict JSON matching the requested schema.",
            "- Include concise rationale fields only. Do not include chain-of-thought.",
            "- Keep the contract compact.",
            "",
            "Non-negotiable invariants:",
            "- Official/current/source-bound obligations cannot become secondary-only.",
            "- Legal/current-primary obligations cannot be satisfied by secondary explainers alone.",
            "- Current canonical technical behavior requires official/project/canonical docs when applicable.",
            "- Social/forum/community evidence cannot satisfy factual/legal/medical/financial/source-bound/current obligations.",
            "- Unsupported source-bound numeric values remain unknown.",
            "- Inferred conclusions cannot be marked directly sourced unless a source directly states them.",
            "- Lower-tier evidence is context/leads only unless no stronger obligation applies.",
            "",
            "Run facts JSON:",
            _json(facts),
            "",
            "Deterministic baseline contract JSON:",
            _json(deterministic_contract_projection),
            "",
            "Required output schema JSON:",
            _json(schema),
        ]
    )


def prompt_metadata(prompt: str) -> dict[str, Any]:
    return {
        "prompt_hash": stable_hash(prompt),
        "prompt_length": len(prompt),
        "raw_prompt_retained": False,
    }


__all__ = [
    "RUN_AUTHORITY_CONTRACT_PROMPT_SCHEMA_VERSION",
    "RUN_AUTHORITY_CONTRACT_SYSTEM_PROMPT",
    "build_run_authority_contract_prompt",
    "prompt_metadata",
]
