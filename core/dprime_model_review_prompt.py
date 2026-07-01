"""Prompt/input boundary for D-prime assessment-only model review.

The prompt is built only for an explicitly injected test/fake review callable.
Callers may retain prompt metadata, but must not retain the raw prompt text or
raw model response. This module imports no provider client and performs no
model, search, retrieval, fetch/read, citation, Author, or RunKernel work.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping

DPRIME_MODEL_REVIEW_PROMPT_SCHEMA_VERSION = (
    "dprime_model_review_prompt_assessment_slice_01_v1"
)

DPRIME_MODEL_REVIEW_SYSTEM_PROMPT = (
    "You are a D-prime evidence-relative assessment reviewer. Return only strict "
    "JSON for EvidenceRelativeSupportAssessment. Do not answer the user, create "
    "a proposal, admit support, request search, cite sources, or write prose."
)

DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA: dict[str, Any] = {
    "record_kind": "EvidenceRelativeSupportAssessment",
    "required_fields": [
        "source_proposition",
        "answer_component_claim",
        "support_relation",
        "required_qualifiers",
        "observed_qualifiers",
        "missing_qualifiers",
        "scope_check",
        "currentness_check",
        "contradiction_check",
        "evidential_adequacy_notes",
        "non_support_reason_when_not_direct",
        "producer_abstained",
        "challenge_recommended",
        "closed_surface_flags",
    ],
    "runtime_filled_fields": [
        "assessment_id",
        "assessment_digest",
        "preflight_ref",
        "preflight_digest",
        "negative_control_profile_ref",
        "negative_control_profile_digest",
        "selector_ref",
        "component_ref",
        "source_obligation_ref",
        "model_review_ref",
        "prompt_license_ref",
    ],
    "support_relation_values": [
        "directly_supports",
        "partially_supports",
        "absent",
        "scope_mismatch",
        "currentness_mismatch",
        "contradicts",
        "missing_qualifier",
        "weak_or_overclaim_risk",
        "abstained",
    ],
    "forbidden_support_relation_values": [
        "yes",
        "supports",
        "support",
        "supported",
        "pass",
        "passed",
        "handled",
        "maybe_support",
        "weak_support",
        "ok",
    ],
}


def build_dprime_model_review_prompt(
    *,
    input_packet: Mapping[str, Any],
    transient_bounded_evidence_window: str,
) -> str:
    """Build the transient assessment prompt from sanitized packet material."""

    prompt_payload = {
        "schema_version": DPRIME_MODEL_REVIEW_PROMPT_SCHEMA_VERSION,
        "assessment_input_packet": dict(input_packet),
        "transient_sanitized_evidence_window": transient_bounded_evidence_window,
        "output_schema": DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA,
    }
    instructions = [
        "D-PRIME MODEL REVIEW ASSESSMENT TASK",
        f"Prompt schema: {DPRIME_MODEL_REVIEW_PROMPT_SCHEMA_VERSION}",
        "",
        "Authority boundary:",
        "- You may produce only EvidenceRelativeSupportAssessment JSON.",
        "- You are not RunKernel, Analyst proposal packaging, SemanticObservation,",
        "  ComponentCoverage, Sufficiency, FinalAnswerPacket, Author, or citation.",
        "- preflight pass is not semantic support.",
        "- negative-control profile availability is not semantic support.",
        "- assessment validator availability is not semantic support.",
        "- directly_supports is not RunKernel admission.",
        "",
        "Strict prohibitions:",
        "- Do not answer the user.",
        "- Do not create a ValidatedSupportProposal.",
        "- Do not request or authorize RunKernel admission.",
        "- Do not create SemanticObservation or ComponentCoverage.",
        "- Do not claim source-obligation satisfaction or citation eligibility.",
        "- Do not create SufficiencyReadiness, FinalAnswerPacket, Author input,",
        "  answer prose, product correctness, or analysis_gap_search_proposal.",
        "- Do not request browsing, search, retrieval, fetch/read, or follow-up.",
        "- Do not include chain-of-thought.",
        "- Return strict JSON only; no Markdown fences.",
        "",
        "Sanitized transient review input JSON:",
        _json(prompt_payload),
    ]
    return "\n".join(instructions)


def prompt_metadata(prompt: str) -> dict[str, Any]:
    """Return retainable metadata for a prompt whose raw text is discarded."""

    return {
        "prompt_schema_version": DPRIME_MODEL_REVIEW_PROMPT_SCHEMA_VERSION,
        "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_length": len(prompt),
        "raw_prompt_retained": False,
    }


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


__all__ = [
    "DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA",
    "DPRIME_MODEL_REVIEW_PROMPT_SCHEMA_VERSION",
    "DPRIME_MODEL_REVIEW_SYSTEM_PROMPT",
    "build_dprime_model_review_prompt",
    "prompt_metadata",
]
