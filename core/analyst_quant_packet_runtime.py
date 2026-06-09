"""Bounded Analyst quantitative packet helpers.

This module contains mechanical runtime formatting helpers used by the
orchestrator and runtime prompt assembly. It owns no provider, query, retrieval,
or final-answer policy.
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.nutrition_lookup import detect_nutrition_lookup_telemetry

ANALYST_QUANT_PACKET_STRING_LIMIT = 200
ANALYST_QUANT_PACKET_SOURCE_VALUE_LIMIT = 12
ANALYST_QUANT_PACKET_CALCULATION_LIMIT = 8
ANALYST_QUANT_PACKET_REF_LIMIT = 12
MISSING_TARGET_METRIC_NOTE_LIMIT = 12


def _nutrition_macro_per_unit_lookup(query: str) -> bool:
    return bool(detect_nutrition_lookup_telemetry(query)["nutrition_lookup_detected"])


def _analyst_quant_packet_telemetry_defaults() -> dict[str, Any]:
    return {
        "analyst_quant_packet_present": False,
        "analyst_quant_packet_review_requested": False,
        "analyst_quant_packet_injected": False,
        "analyst_quant_packet_reviewed_by_model": False,
        "analyst_quant_packet_direct_use_eligible": False,
        "analyst_quant_packet_requires_analyst": True,
        "analyst_quant_packet_source": None,
        "analyst_quant_packet_gate_reason": "no_packet_for_analyst",
        "analyst_model_called": False,
    }


def _query_allows_proxy_or_qualitative_metric_framing(query: str) -> bool:
    text = str(query or "").replace("_", " ").replace("-", " ").casefold()
    return bool(
        re.search(
            r"\b("
            r"proxy|proxies|proxy only|proxy metric|indirect|directional|"
            r"qualitative|qualitatively"
            r")\b",
            text,
        )
    )


def _format_missing_target_metric_fallback_directive(
    *,
    query: str = "",
    report_type: str,
    quant_report_types: Any,
    economist_safety_telemetry: dict[str, Any],
    quant_retrieval_sufficiency_telemetry: dict[str, Any] | None = None,
    estimate_from_priors: bool = False,
) -> str:
    normalized_report_type = str(report_type or "").strip().lower()
    normalized_quant_types = {
        str(rt).strip().lower()
        for rt in (quant_report_types or [])
        if str(rt).strip()
    }
    bounded_quantitative_report = normalized_report_type in normalized_quant_types
    validation_errors = {
        str(error).strip()
        for error in (
            economist_safety_telemetry.get("quantitative_packet_validation_errors")
            or []
        )
        if str(error).strip()
    }
    missing_metrics = [
        str(metric).strip()[:ANALYST_QUANT_PACKET_STRING_LIMIT]
        for metric in (economist_safety_telemetry.get("target_metric_missing") or [])
        if str(metric).strip()
    ][:MISSING_TARGET_METRIC_NOTE_LIMIT]
    packet_missing_target = bool(
        bounded_quantitative_report
        and bool(economist_safety_telemetry.get("quantitative_packet_present"))
        and not bool(economist_safety_telemetry.get("quantitative_packet_valid"))
        and "target_metric_evidence_missing" in validation_errors
        and missing_metrics
    )

    retrieval_missing_metrics: list[str] = []
    if (
        bounded_quantitative_report
        and not estimate_from_priors
        and not bool(economist_safety_telemetry.get("quantitative_packet_valid"))
        and not _query_allows_proxy_or_qualitative_metric_framing(query)
        and isinstance(quant_retrieval_sufficiency_telemetry, dict)
        and bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_target_detected"
            )
        )
        and not bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_metric_coverage_valid"
            )
        )
        and bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_proxy_metric_detected"
            )
        )
    ):
        blockers = {
            str(blocker).strip()
            for blocker in (
                quant_retrieval_sufficiency_telemetry.get(
                    "quant_retrieval_sufficiency_blockers"
                )
                or []
            )
            if str(blocker).strip()
        }
        if "proxy_metric_only" in blockers and "missing_metric_coverage" in blockers:
            retrieval_missing_metrics = [
                str(metric).strip()[:ANALYST_QUANT_PACKET_STRING_LIMIT]
                for metric in (
                    quant_retrieval_sufficiency_telemetry.get(
                        "quant_retrieval_metrics"
                    )
                    or []
                )
                if str(metric).strip()
                and str(metric).strip() != "comparative_terms"
            ][:MISSING_TARGET_METRIC_NOTE_LIMIT]

    if retrieval_missing_metrics:
        for metric in retrieval_missing_metrics:
            if metric not in missing_metrics:
                missing_metrics.append(metric)
        missing_metrics = missing_metrics[:MISSING_TARGET_METRIC_NOTE_LIMIT]

    if not (packet_missing_target or retrieval_missing_metrics):
        return ""

    metric_list = ", ".join(missing_metrics)
    return (
        "\n\nNOTE FOR DOWNSTREAM SYNTHESIS - MISSING TARGET METRIC EVIDENCE:\n"
        "The requested quantitative target metric was not source-bound. "
        f"Missing metric evidence: {metric_list}. "
        "Available quantitative evidence may be adjacent or proxy-only; treat proxy "
        "evidence as proxy-only unless explicitly labeled that way. "
        "Do not present model-derived numeric estimates, ranges, or percent advantages "
        "for the missing metric. Answer qualitatively from available sourced evidence "
        "and explicitly state that direct evidence for the requested metric is missing.\n"
    )


def _economist_pre_analyst_skip_candidate_defaults() -> dict[str, Any]:
    return {
        "economist_pre_analyst_skip_candidate_shadow": False,
        "economist_pre_analyst_skip_candidate_reasons": [],
        "economist_pre_analyst_skip_candidate_blockers": [],
        "economist_pre_analyst_skip_candidate_gate_reason": "not_evaluated",
        "economist_pre_analyst_skip_candidate_shadow_mode": True,
    }


def _economist_pre_analyst_skip_candidate_telemetry(
    *,
    report_type: str,
    complexity: str,
    mode: str,
    economist_safety_telemetry: dict[str, Any],
    quant_retrieval_sufficiency_telemetry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Diagnostic-only pre-Analyst skip candidate telemetry.

    This reports whether a future policy might consider a clean Economist packet
    reviewable. It is not runtime control flow and must not skip Analyst.
    """
    telemetry = _economist_pre_analyst_skip_candidate_defaults()
    reasons: list[str] = []
    blockers: list[str] = []

    bounded_quantitative = str(report_type).lower() in {
        "quantitative_comparison",
        "benchmark",
    }
    if bounded_quantitative:
        reasons.append("bounded_quantitative_report")
    else:
        blockers.append("non_bounded_quantitative_report")

    if str(complexity).lower() == "medium":
        reasons.append("medium_complexity")
    else:
        blockers.append("non_medium_complexity")

    packet_valid = bool(economist_safety_telemetry.get("quantitative_packet_valid"))
    packet_direct_use = bool(
        economist_safety_telemetry.get("quantitative_packet_direct_use_eligible")
    )
    packet_requires_analyst = bool(
        economist_safety_telemetry.get("quantitative_packet_requires_analyst")
    )
    if packet_valid:
        reasons.append("packet_valid")
    else:
        blockers.append("packet_invalid_or_missing")
    if packet_direct_use:
        reasons.append("packet_direct_use_eligible")
    else:
        blockers.append("packet_not_direct_use_eligible")
    if packet_requires_analyst:
        blockers.append("packet_requires_analyst")
    else:
        reasons.append("packet_does_not_require_analyst")

    if bool(economist_safety_telemetry.get("high_stakes_quant_detected")):
        blockers.append("high_stakes_requires_analyst")
    else:
        reasons.append("non_high_stakes")

    if bool(economist_safety_telemetry.get("economist_code_execution_requested")):
        blockers.append("economist_code_execution_requested")
    else:
        reasons.append("no_economist_code_request")

    if bounded_quantitative:
        quant_retrieval_sufficiency_telemetry = (
            quant_retrieval_sufficiency_telemetry or {}
        )
        retrieval_target_detected = bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_target_detected"
            )
        )
        retrieval_sufficiency_valid = bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_sufficiency_valid"
            )
        )
        if retrieval_target_detected and retrieval_sufficiency_valid:
            reasons.append("retrieval_sufficiency_valid")
        elif not retrieval_target_detected:
            blockers.append("retrieval_sufficiency_missing")
        else:
            blockers.append("retrieval_sufficiency_failed")

    candidate = not blockers
    if candidate:
        gate_reason = "candidate_shadow_only"
    elif "high_stakes_requires_analyst" in blockers:
        gate_reason = "blocked_by_high_stakes"
    elif "packet_invalid_or_missing" in blockers:
        gate_reason = "blocked_by_invalid_packet"
    elif (
        "retrieval_sufficiency_failed" in blockers
        or "retrieval_sufficiency_missing" in blockers
    ):
        gate_reason = "blocked_by_retrieval_sufficiency"
    elif "non_bounded_quantitative_report" in blockers:
        gate_reason = "blocked_by_report_type"
    elif "non_medium_complexity" in blockers:
        gate_reason = "blocked_by_complexity"
    elif "economist_code_execution_requested" in blockers:
        gate_reason = "blocked_by_code_request"
    else:
        gate_reason = "blocked_by_multiple_reasons"

    telemetry.update(
        {
            "economist_pre_analyst_skip_candidate_shadow": candidate,
            "economist_pre_analyst_skip_candidate_reasons": reasons,
            "economist_pre_analyst_skip_candidate_blockers": blockers,
            "economist_pre_analyst_skip_candidate_gate_reason": gate_reason,
            "economist_pre_analyst_skip_candidate_shadow_mode": True,
        }
    )
    return telemetry


def _truncate_analyst_quant_packet_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) <= ANALYST_QUANT_PACKET_STRING_LIMIT:
        return value
    return value[: ANALYST_QUANT_PACKET_STRING_LIMIT - 3] + "..."


def _sanitize_analyst_quant_packet_value(value: Any) -> Any:
    if isinstance(value, str):
        return _truncate_analyst_quant_packet_string(value)
    if isinstance(value, dict):
        return {
            str(
                _truncate_analyst_quant_packet_string(k)
            ): _sanitize_analyst_quant_packet_value(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list):
        return [_sanitize_analyst_quant_packet_value(item) for item in value]
    return value


def _bounded_analyst_quant_packet_list(value: Any, limit: int) -> list[Any]:
    if not isinstance(value, list):
        return []
    return [_sanitize_analyst_quant_packet_value(item) for item in value[:limit]]


def _analyst_quant_packet_payload(
    telemetry: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    handoff = _analyst_quant_packet_telemetry_defaults()
    packet = telemetry.get("quantitative_packet")
    packet_present = bool(telemetry.get("quantitative_packet_present"))
    packet_valid = bool(telemetry.get("quantitative_packet_valid"))
    handoff["analyst_quant_packet_present"] = packet_present
    if packet_present:
        handoff["analyst_quant_packet_gate_reason"] = str(
            telemetry.get("quantitative_packet_gate_reason")
            or "packet_not_available_for_analyst"
        )[:ANALYST_QUANT_PACKET_STRING_LIMIT]

    if not (packet_present and packet_valid and isinstance(packet, dict)):
        return handoff, None

    direct_use_eligible = bool(
        telemetry.get(
            "quantitative_packet_direct_use_eligible",
            packet.get("direct_use_eligible", False),
        )
    )
    requires_analyst = bool(
        telemetry.get(
            "quantitative_packet_requires_analyst",
            packet.get("requires_analyst", True),
        )
    )
    handoff.update(
        {
            "analyst_quant_packet_review_requested": True,
            "analyst_quant_packet_injected": True,
            "analyst_quant_packet_direct_use_eligible": direct_use_eligible,
            "analyst_quant_packet_requires_analyst": requires_analyst,
            "analyst_quant_packet_source": "economist_quantitative_packet_v1",
        }
    )

    sanitized = {
        "schema_version": _truncate_analyst_quant_packet_string(
            packet.get("schema_version")
        ),
        "target_metric_names": _bounded_analyst_quant_packet_list(
            packet.get("target_metric_names", telemetry.get("target_metric_names")),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "source_bound_values": _bounded_analyst_quant_packet_list(
            packet.get("source_bound_values"),
            ANALYST_QUANT_PACKET_SOURCE_VALUE_LIMIT,
        ),
        "unsupported_values": _bounded_analyst_quant_packet_list(
            packet.get("unsupported_values"),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "calculation_results": _bounded_analyst_quant_packet_list(
            packet.get("calculation_results"),
            ANALYST_QUANT_PACKET_CALCULATION_LIMIT,
        ),
        "target_metric_bound_value_refs": _bounded_analyst_quant_packet_list(
            packet.get(
                "target_metric_bound_value_refs",
                telemetry.get("target_metric_bound_value_refs"),
            ),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "target_metric_calculation_refs": _bounded_analyst_quant_packet_list(
            packet.get(
                "target_metric_calculation_refs",
                telemetry.get("target_metric_calculation_refs"),
            ),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "high_stakes_quant_detected": bool(
            packet.get(
                "high_stakes_quant_detected",
                telemetry.get("high_stakes_quant_detected", False),
            )
        ),
        "high_stakes_quant_domain": _truncate_analyst_quant_packet_string(
            packet.get(
                "high_stakes_quant_domain",
                telemetry.get("high_stakes_quant_domain"),
            )
        ),
        "direct_use_eligible": direct_use_eligible,
        "requires_analyst": requires_analyst,
        "validation_errors": _bounded_analyst_quant_packet_list(
            packet.get(
                "validation_errors",
                telemetry.get("quantitative_packet_validation_errors"),
            ),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "gate_reason": str(
            telemetry.get("quantitative_packet_gate_reason")
            or packet.get("gate_reason")
            or "valid_packet_for_analyst_review"
        )[:ANALYST_QUANT_PACKET_STRING_LIMIT],
    }
    return handoff, sanitized


def _format_analyst_quant_packet_section(
    telemetry: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    handoff, packet = _analyst_quant_packet_payload(telemetry)
    if packet is None:
        return "", handoff
    serialized = json.dumps(
        packet, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    section = (
        "\n\nQUANTITATIVE PACKET FOR ANALYST REVIEW ONLY\n"
        "Instructions:\n"
        "- Treat this as structured evidence, not as a final conclusion.\n"
        "- Verify that the packet supports the user's requested metric.\n"
        "- Keep source_bound_values distinct from unsupported_values; unsupported_values are not sourced facts.\n"
        "- Check whether validation_errors is empty.\n"
        "- If direct_use_eligible is false, do not present it as a settled quantitative conclusion.\n"
        "- If high_stakes_quant_detected is true, apply extra caution and state limitations.\n"
        "- You may accept, reject, or qualify the packet.\n"
        "- Do not invent calculations or unstated values; do not cite unsupported_values as source-bound.\n"
        "Packet JSON:\n"
        f"{serialized}\n"
    )
    return section, handoff


__all__ = [
    "ANALYST_QUANT_PACKET_CALCULATION_LIMIT",
    "ANALYST_QUANT_PACKET_REF_LIMIT",
    "ANALYST_QUANT_PACKET_SOURCE_VALUE_LIMIT",
    "ANALYST_QUANT_PACKET_STRING_LIMIT",
    "MISSING_TARGET_METRIC_NOTE_LIMIT",
    "_analyst_quant_packet_payload",
    "_analyst_quant_packet_telemetry_defaults",
    "_economist_pre_analyst_skip_candidate_defaults",
    "_economist_pre_analyst_skip_candidate_telemetry",
    "_format_analyst_quant_packet_section",
    "_format_missing_target_metric_fallback_directive",
    "_nutrition_macro_per_unit_lookup",
    "_query_allows_proxy_or_qualitative_metric_framing",
]
