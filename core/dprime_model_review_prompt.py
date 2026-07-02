"""Prompt/input boundary for D-prime assessment-only model review.

The prompt is built only for an explicitly licensed D-prime assessment review
lane: the fake/test callable path or the product-owned one-shot adapter
contract. Callers may retain prompt metadata, but must not retain the raw prompt
text or raw model response. This module imports no provider client and performs
no model, search, retrieval, fetch/read, citation, Author, or RunKernel work.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping

DPRIME_MODEL_REVIEW_PROMPT_SCHEMA_VERSION = (
    "dprime_model_review_prompt_assessment_slice_01_v2"
)

MODEL_FILLABLE_ASSESSMENT_FIELDS = [
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
]

RUNTIME_FILLED_FORBIDDEN_MODEL_OUTPUT_FIELDS = [
    "record_kind",
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
]

AUTHORITY_OBJECT_FORBIDDEN_MODEL_OUTPUT_FIELDS = [
    "assessment_created",
    "validated_support_proposal_created",
    "run_kernel_support_admission_request_created",
    "semantic_observation_created",
    "component_coverage_created",
    "citation_eligibility_claimed",
    "source_obligation_satisfaction_claimed",
    "answer_text_created",
    "product_correctness_claimed",
    "analysis_gap_search_proposal",
]

CLOSED_SURFACE_FLAGS_REQUIRED_FALSE_KEYS = [
    "model_review_licensed",
    "assessment_created",
    "validated_support_proposal_created",
    "run_kernel_support_admission_request_created",
    "semantic_observation_created",
    "component_coverage_bound",
    "citation_eligibility_claimed",
    "source_obligation_satisfaction_claimed",
    "answer_text_created",
    "product_correctness_claimed",
]

DPRIME_MODEL_REVIEW_SYSTEM_PROMPT = (
    "You are a D-prime evidence-relative assessment reviewer. Return only strict "
    "JSON with exactly the model-fillable assessment fields. Do not include "
    "runtime-filled fields, create a proposal, admit support, request search, "
    "cite sources, answer the user, or write prose."
)

DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA: dict[str, Any] = {
    "record_kind": "EvidenceRelativeSupportAssessment",
    "model_output_contract": (
        "Return one JSON object whose top-level keys are exactly "
        "model_fillable_allowed_fields. Runtime-filled fields and "
        "authority/object-created fields are forbidden in model output."
    ),
    "model_fillable_allowed_fields": MODEL_FILLABLE_ASSESSMENT_FIELDS,
    "required_fields": MODEL_FILLABLE_ASSESSMENT_FIELDS,
    "runtime_filled_fields": RUNTIME_FILLED_FORBIDDEN_MODEL_OUTPUT_FIELDS,
    "forbidden_runtime_filled_fields": (
        RUNTIME_FILLED_FORBIDDEN_MODEL_OUTPUT_FIELDS
    ),
    "forbidden_authority_object_created_fields": (
        AUTHORITY_OBJECT_FORBIDDEN_MODEL_OUTPUT_FIELDS
    ),
    "forbidden_top_level_fields": (
        RUNTIME_FILLED_FORBIDDEN_MODEL_OUTPUT_FIELDS
        + AUTHORITY_OBJECT_FORBIDDEN_MODEL_OUTPUT_FIELDS
    ),
    "closed_surface_flags_required_false_keys": (
        CLOSED_SURFACE_FLAGS_REQUIRED_FALSE_KEYS
    ),
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
        "- You may produce only EvidenceRelativeSupportAssessment JSON with the",
        "  exact model-fillable top-level keys in output_schema.",
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
        "Model-fillable output contract:",
        "- The top-level JSON keys must be exactly",
        "  output_schema.model_fillable_allowed_fields.",
        "- Do not include output_schema.runtime_filled_fields; runtime will fill",
        "  those fields after deterministic checks.",
        "- Do not include output_schema.forbidden_authority_object_created_fields",
        "  as top-level keys.",
        "- closed_surface_flags is allowed only as a nested assessment field whose",
        "  required false keys stay false.",
        "- Do not add extra keys, aliases, explanatory wrappers, object-created",
        "  flags, authority-upgrade flags, raw/private fields, or downstream",
        "  product claims.",
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
    "AUTHORITY_OBJECT_FORBIDDEN_MODEL_OUTPUT_FIELDS",
    "CLOSED_SURFACE_FLAGS_REQUIRED_FALSE_KEYS",
    "MODEL_FILLABLE_ASSESSMENT_FIELDS",
    "RUNTIME_FILLED_FORBIDDEN_MODEL_OUTPUT_FIELDS",
    "build_dprime_model_review_prompt",
    "prompt_metadata",
]
