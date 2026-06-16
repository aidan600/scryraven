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
    "FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS",
    "FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS",
    "followup_closed_flags",
    "followup_common_redaction_posture",
    "followup_fixture_provenance",
    "followup_live_surface_flags",
]
