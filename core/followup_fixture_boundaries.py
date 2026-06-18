"""Shared fixture-only follow-up boundary helpers.

The AG-96I2 fixture spine intentionally keeps stage records explicit. These
helpers only centralize repeated closed-surface flags and redaction/provenance
posture so each stage can declare its own opened fixture seam without copying
the same no-live lists.
"""

from __future__ import annotations

from typing import Any

FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS = (
    "provider_execution_licensed",
    "live_provider_call_executed",
    "provider_job_scheduled",
    "provider_job_dispatched",
    "search_executed",
    "retrieval_executed",
    "fetch_executed",
    "model_called",
    "query_generation_changed",
    "retrieval_ranking_filtering_changed",
    "pipeline_orchestrator_domain_logic_changed",
)

FOLLOWUP_NO_LIVE_FALSE_FLAGS = FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS[1:]

FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS = (
    "search_judgment_rerun",
)

FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS = (
    "author_executor_invoked",
    "author_prompt_changed",
    "author_prose_behavior_changed",
    "citation_rendering_changed",
    "citation_formatter_invoked",
    "citation_behavior_changed",
    "product_answer_behavior_changed",
    "final_answer_behavior_changed",
)

FOLLOWUP_FINAL_ANSWER_PACKET_MUTATION_FALSE_FLAGS = (
    "canonical_final_answer_packet_mutated",
    "final_answer_packet_updated",
    "final_answer_packet_rebuilt",
)

FOLLOWUP_ROLE_HANDOFF_RUNTIME_FALSE_FLAGS = (
    "author_payload_created",
    "analyst_activation_allowed",
    "analyst_handoff_created",
    "economist_activation_allowed",
    "economist_handoff_created",
    "economist_code_execution_allowed",
    "answer_ready",
    "prompt_behavior_changed",
)

FOLLOWUP_COMMON_REDACTION_FALSE_FLAGS = (
    "provider_payloads_retained",
    "prompts_retained",
    "model_responses_retained",
    "unsanitized_text_retained",
    "private_records_or_complete_traces_retained",
)


def followup_closed_flags(
    *flag_names: str,
    overrides: dict[str, bool] | None = None,
) -> dict[str, bool]:
    flags = {name: False for name in flag_names}
    if overrides:
        flags.update(overrides)
    return flags


def followup_live_surface_flags(
    *,
    overrides: dict[str, bool] | None = None,
) -> dict[str, bool]:
    return followup_closed_flags(
        *FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS,
        overrides=overrides,
    )


def followup_closed_surface_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        **followup_closed_flags(*FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS),
        **followup_closed_flags(*FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS),
        **followup_closed_flags(*FOLLOWUP_ROLE_HANDOFF_RUNTIME_FALSE_FLAGS),
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "live_validation_not_run": True,
        "not_role_consumption_payload": True,
    }


def blocked_packet_shell_boundary_flags() -> dict[str, bool]:
    return {
        **followup_closed_surface_boundary_flags(),
        "sufficiency_judgment_rechecked": True,
        "packet_preparation_readiness_consumed": True,
        **{
            name: True
            for name in FOLLOWUP_FINAL_ANSWER_PACKET_MUTATION_FALSE_FLAGS
        },
        "blocked_final_answer_packet_shell_activated": True,
        "final_evidence_selected": False,
        "citation_eligible": False,
        "citations_rendered": False,
        "final_evidence_selection_deferred": True,
        "citation_eligibility_deferred": True,
    }


def final_evidence_selection_boundary_flags() -> dict[str, bool]:
    return {
        **followup_closed_surface_boundary_flags(),
        "sufficiency_judgment_rechecked": True,
        "packet_preparation_readiness_consumed": True,
        "blocked_final_answer_packet_shell_consumed": True,
        **{
            name: True
            for name in FOLLOWUP_FINAL_ANSWER_PACKET_MUTATION_FALSE_FLAGS
        },
        "final_evidence_selected": True,
        "citation_eligible": False,
        "citations_rendered": False,
        "final_evidence_selection_deferred": False,
        "citation_eligibility_deferred": True,
    }


def citation_eligibility_boundary_flags() -> dict[str, bool]:
    return {
        **followup_closed_surface_boundary_flags(),
        "sufficiency_judgment_rechecked": True,
        "packet_preparation_readiness_consumed": True,
        "blocked_final_answer_packet_shell_consumed": True,
        "final_evidence_selection_consumed": True,
        **{
            name: True
            for name in FOLLOWUP_FINAL_ANSWER_PACKET_MUTATION_FALSE_FLAGS
        },
        "final_evidence_selected": True,
        "citation_eligibility_created": True,
        "citation_eligible": True,
        "citations_rendered": False,
        "citation_rendering_deferred": True,
        "final_evidence_selection_deferred": False,
        "citation_eligibility_deferred": False,
    }


def citation_source_handoff_boundary_flags() -> dict[str, bool]:
    return {
        **followup_closed_surface_boundary_flags(),
        "sufficiency_judgment_rechecked": True,
        "packet_preparation_readiness_consumed": True,
        "blocked_final_answer_packet_shell_consumed": True,
        "final_evidence_selection_consumed": True,
        "citation_eligibility_consumed": True,
        "packet_local_citation_eligibility_consumed": True,
        **{name: False for name in FOLLOWUP_FINAL_ANSWER_PACKET_MUTATION_FALSE_FLAGS},
        "final_evidence_selected": True,
        "citation_eligibility_created": True,
        "citation_source_handoff_created": True,
        "source_identity_records_created": True,
        "citation_eligible": True,
        "citations_rendered": False,
        "citation_rendering_deferred": True,
        "ordered_product_source_output_created": False,
    }


def followup_fixture_provenance(
    *,
    intake_bridge: str | None = None,
    recheck_bridge: str | None = None,
    packet_bridge: str | None = None,
    author_gate_bridge: str | None = None,
    author_executor_connected: bool | None = None,
) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "origin": "ag96i2b_followup_fixture_execution",
        "fixture_only": True,
        "live_provider_result": False,
        "provider_job_executor_connected": False,
    }
    for key, value in (
        ("intake_bridge", intake_bridge),
        ("recheck_bridge", recheck_bridge),
        ("packet_bridge", packet_bridge),
        ("author_gate_bridge", author_gate_bridge),
    ):
        if value is not None:
            provenance[key] = value
    if author_executor_connected is not None:
        provenance["author_executor_connected"] = author_executor_connected
    return provenance


def followup_common_redaction_posture(
    *,
    sanitized_fixture_summary_only: bool = True,
    packet_authority_refs_only: bool = False,
    final_text_retained: bool | None = None,
) -> dict[str, bool]:
    posture = {
        "json_safe": True,
        "sanitized_fixture_summary_only": sanitized_fixture_summary_only,
        **{name: False for name in FOLLOWUP_COMMON_REDACTION_FALSE_FLAGS},
    }
    if packet_authority_refs_only:
        posture.pop("sanitized_fixture_summary_only", None)
        posture["packet_authority_refs_only"] = True
    if final_text_retained is not None:
        posture["final_text_retained"] = final_text_retained
    return posture


__all__ = [
    "FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS",
    "FOLLOWUP_FINAL_ANSWER_PACKET_MUTATION_FALSE_FLAGS",
    "FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS",
    "FOLLOWUP_NO_LIVE_FALSE_FLAGS",
    "FOLLOWUP_ROLE_HANDOFF_RUNTIME_FALSE_FLAGS",
    "FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS",
    "blocked_packet_shell_boundary_flags",
    "citation_eligibility_boundary_flags",
    "citation_source_handoff_boundary_flags",
    "final_evidence_selection_boundary_flags",
    "followup_closed_flags",
    "followup_closed_surface_boundary_flags",
    "followup_common_redaction_posture",
    "followup_fixture_provenance",
    "followup_live_surface_flags",
]
