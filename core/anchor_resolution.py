"""Diagnostics-only Balanced Anchor Resolution v1 helpers.

This module is intentionally pure string/metadata logic. It does not call
models, search providers, retrieval, ranking, or prompt-building code.
"""

from __future__ import annotations

import re
from typing import Any

NEXT_ACTIONS = frozenset(
    {
        "proceed_single_frame",
        "preserve_multiple_frames",
        "retrieve_to_anchor",
        "ask_clarification",
    }
)

CONFIDENCE_BUCKETS = frozenset({"low", "medium", "high"})

_CAP_SHORT = 160
_CAP_QUERY = 240
_MAX_LIST_ITEMS = 5


def _compact_text(value: Any, *, limit: int = _CAP_SHORT) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return text[:limit]


def _compact_list(values: list[Any] | tuple[Any, ...] | None, *, limit: int = _CAP_SHORT) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = _compact_text(value, limit=limit)
        key = item.casefold()
        if item and key not in seen:
            out.append(item)
            seen.add(key)
        if len(out) >= _MAX_LIST_ITEMS:
            break
    return out


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _temporal_frame(text: str) -> str:
    if _has_any(text, (r"\b(?:today|now|latest|current|currently|recent|new|changed|update)\b",)):
        return "recent"
    if _has_any(text, (r"\b(?:last|past|previous|rolling)\s+(?:reporting\s+)?(?:period|quarter|year|month|window)\b",)):
        return "rolling"
    if _has_any(text, (r"\b(?:19|20)\d{2}\b",)):
        return "point-in-time"
    if _has_any(text, (r"\b(?:specified|given|stated)\s+(?:region|period|window|time\s+window)\b",)):
        return "user-bounded"
    return "evergreen"


def _freshness_requirement(text: str, temporal_frame: str, source_class: str) -> str:
    if _has_any(text, (r"\b(?:current|latest|today|now)\b",)) and source_class == "official":
        return "official-current"
    if temporal_frame == "recent":
        return "high"
    if temporal_frame in {"rolling", "point-in-time", "user-bounded"}:
        return "medium"
    return "none"


def _source_class_expectation(text: str, report_type: str, query_type: str) -> str:
    combined = f"{text} {report_type} {query_type}".casefold()
    if _has_any(
        combined,
        (
            r"\b(?:official|regulatory|compliance|requirement|eligibility|filing|rule|policy|notice)\b",
            r"\b(?:sec|irs|fda|cms|epa|court|statute)\b",
        ),
    ):
        return "official"
    if _has_any(combined, (r"\b(?:current|latest|market|price|pricing|news|event)\b",)):
        return "market/current"
    if _has_any(combined, (r"\b(?:peer-reviewed|clinical|trial|study|paper|academic)\b",)):
        return "peer-reviewed"
    if _has_any(combined, (r"\b(?:internal|private|memo|non-public|nonpublic)\b",)):
        return "primary"
    return "mixed"


def _claim_or_metric_type(text: str, report_type: str, query_type: str) -> str:
    combined = f"{text} {report_type} {query_type}".casefold()
    if _has_any(combined, (r"\b(?:cause|caused|causal|drove|because|impact|effect)\b",)):
        return "causal claim"
    if _has_any(combined, (r"\b(?:forecast|predict|projection|estimate)\b",)):
        return "forecast"
    if _has_any(
        combined,
        (
            r"\b(?:metric|rate|ratio|margin|retention|cost|price|rank|exact|denominator|per)\b",
            r"\b(?:quantitative_comparison|benchmark|cost_analysis|unit_economics)\b",
        ),
    ):
        return "metric"
    if _has_any(combined, (r"\b(?:compare|comparison|versus|vs\.?)\b",)):
        return "comparison"
    if _has_any(combined, (r"\b(?:rule|requirement|eligibility|how_to)\b",)):
        return "rule"
    return "factual lookup"


def _ambiguity_types(
    *,
    text: str,
    query_type: str,
    entities: list[str],
    router_entity_retry_used: bool,
) -> list[str]:
    ambiguity: list[str] = []

    def add(value: str) -> None:
        if value not in ambiguity:
            ambiguity.append(value)

    if router_entity_retry_used:
        add("referent")
    if _has_any(
        text,
        (
            r"\b(?:after it|when it|before it)\b",
            r"\b(?:this|that)\s+(?:service|product|company|rule|policy)\b",
            r"\b(?:the service|the product|the company)\b",
        ),
    ):
        add("referent")
    if not entities and query_type in {"other", "concept"} and _has_any(text, (r"\b(?:it|that)\b",)):
        add("referent")

    if _has_any(
        text,
        (
            r"\b(?:domain|product class|margin requirement|wrong-domain|off-domain)\b",
            r"\b(?:same terms|specified domain|intended domain)\b",
        ),
    ):
        add("domain")

    if _has_any(
        text,
        (
            r"\b(?:retention|margin|rate|metric|denominator|unit|time basis|reporting period|rank)\b",
        ),
    ) and not _has_any(text, (r"\b(?:stated denominator|specified denominator|using the stated)\b",)):
        add("metric")

    if _has_any(text, (r"\b(?:last|current|latest|recent|reporting period|time window)\b",)):
        add("temporal")

    if _has_any(text, (r"\b(?:region|scope|only for|specified region|specified .* window)\b",)):
        if not _has_any(text, (r"\b(?:specified|stated|given)\b",)):
            add("scope")

    if _has_any(text, (r"\b(?:internal|private|non-public|nonpublic|memo|not public|inaccessible)\b",)):
        add("evidence-access")

    if _has_any(text, (r"\b(?:cause|caused|causal|mechanism|drove|because|effect)\b",)):
        add("causal-mechanism")

    return ambiguity[:_MAX_LIST_ITEMS]


def _answerability_forecast(text: str, ambiguity_types: list[str]) -> str:
    if "evidence-access" in ambiguity_types or _has_any(
        text,
        (
            r"\b(?:internal|private|non-public|nonpublic)\b",
            r"\bexact\s+(?:target\s+)?metric\b.*\bprivate\b",
        ),
    ):
        return "likely non-public"
    if _has_any(text, (r"\b(?:proxy-only|proxy only|proxy metric|target metric unavailable)\b",)):
        return "proxy-only risk"
    if ambiguity_types:
        return "answerable with constraints"
    return "likely answerable"


def _next_action(
    *,
    text: str,
    ambiguity_types: list[str],
    freshness_requirement: str,
    answerability_forecast: str,
    source_class_expectation: str,
) -> str:
    if answerability_forecast in {"likely non-public", "proxy-only risk"}:
        return "retrieve_to_anchor"
    if any(kind in ambiguity_types for kind in ("referent", "domain", "metric", "causal-mechanism", "scope")):
        return "preserve_multiple_frames"
    if freshness_requirement in {"high", "official-current"}:
        return "retrieve_to_anchor"
    if source_class_expectation == "official" and _has_any(text, (r"\b(?:current|latest|requirement|rule)\b",)):
        return "retrieve_to_anchor"
    return "proceed_single_frame"


def _decomposition_hints(
    *,
    next_action: str,
    temporal_frame: str,
    source_class_expectation: str,
    answerability_forecast: str,
) -> list[str]:
    hints: list[str] = []
    if next_action == "preserve_multiple_frames":
        hints.append("preserve-frame")
    if temporal_frame != "evergreen":
        hints.append("include-date")
    if source_class_expectation == "official":
        hints.append("include-official-source")
    if answerability_forecast == "proxy-only risk":
        hints.append("avoid-proxy-only")
    return hints[:_MAX_LIST_ITEMS]


def _off_domain_traps(text: str, ambiguity_types: list[str]) -> list[str]:
    traps: list[str] = []
    if "domain" in ambiguity_types:
        traps.append("nearby wrong-domain interpretation")
    if _has_any(text, (r"\bmargin requirement\b",)):
        traps.append("financial margin vs product-domain margin")
    if _has_any(text, (r"\bproduct class\b",)):
        traps.append("generic product class vs intended domain")
    return _compact_list(traps)


def format_anchor_context_for_researcher(telemetry: dict[str, Any] | None) -> str:
    """Render allowlisted anchor fields for Balanced query decomposition."""
    if not telemetry or not telemetry.get("anchor_packet_present"):
        return ""
    packet = telemetry.get("anchor_packet")
    if not isinstance(packet, dict):
        return ""

    ambiguity = _compact_list(packet.get("ambiguity_types"))
    hints = _compact_list(packet.get("decomposition_hints"))
    traps = _compact_list(packet.get("off_domain_traps"))
    temporal = _compact_text(packet.get("temporal_frame"), limit=40)
    freshness = _compact_text(packet.get("freshness_requirement"), limit=40)
    source_class = _compact_text(packet.get("source_class_expectation"), limit=60)
    claim_type = _compact_text(packet.get("claim_or_metric_type"), limit=60)
    selected_frame = _compact_text(packet.get("selected_frame_id"), limit=60)
    frame = f"selected {selected_frame}" if selected_frame else "preserve multiple frames"

    is_noop = (
        frame == "selected primary"
        and not ambiguity
        and temporal in {"", "evergreen"}
        and freshness in {"", "none"}
        and source_class in {"", "mixed"}
        and claim_type in {"", "factual lookup"}
        and not hints
        and not traps
    )
    if is_noop:
        return ""

    lines = [
        "ANCHOR CONTEXT FOR QUERY DECOMPOSITION:",
        f"- Frame: {frame}",
    ]
    if ambiguity:
        lines.append(f"- Ambiguity: {', '.join(ambiguity)}")
    if temporal or freshness:
        lines.append(f"- Time/Freshness: {temporal or 'unspecified'} / {freshness or 'unspecified'}")
    if source_class:
        lines.append(f"- Expected source class: {source_class}")
    if claim_type:
        lines.append(f"- Claim/metric type: {claim_type}")
    if hints:
        lines.append(f"- Decomposition hints: {', '.join(hints)}")
    if traps:
        lines.append(f"- Off-domain traps: {', '.join(traps)}")
    lines.append(
        "Use this only to preserve the intended frame while generating search queries. "
        "Do not answer the user. Do not add searches beyond the existing query budget."
    )
    return "\n".join(lines)


def build_shadow_anchor_packet(
    *,
    mode: str,
    query: str,
    current_date: str,
    intent: str,
    report_type: str,
    router_original_report_type: str,
    query_type: str,
    router_original_query_type: str,
    core_topic: str,
    primary_entity: str,
    entities: list[str],
    router_entity_retry_used: bool,
) -> dict[str, Any]:
    """Build a compact diagnostics-only shadow anchor packet.

    Non-Balanced callers receive a non-present default so orchestrators can
    avoid attaching any anchor fields outside Balanced mode.
    """
    if str(mode or "").strip() != "Balanced":
        return {
            "anchor_packet_shadow_mode": True,
            "anchor_packet_present": False,
            "anchor_packet_next_action": None,
            "anchor_packet_confidence_bucket": None,
            "anchor_packet_ambiguity_types": [],
            "anchor_packet": None,
        }

    query_s = _compact_text(query, limit=_CAP_QUERY)
    core_topic_s = _compact_text(core_topic)
    primary_entity_s = _compact_text(primary_entity)
    entities_s = _compact_list(entities)
    text = " ".join(
        part
        for part in (
            query_s,
            core_topic_s,
            primary_entity_s,
            " ".join(entities_s),
            _compact_text(intent),
            _compact_text(report_type),
            _compact_text(query_type),
        )
        if part
    ).casefold()

    temporal = _temporal_frame(text)
    source_class = _source_class_expectation(text, report_type, query_type)
    freshness = _freshness_requirement(text, temporal, source_class)
    claim_type = _claim_or_metric_type(text, report_type, query_type)
    ambiguity = _ambiguity_types(
        text=text,
        query_type=str(query_type or "").strip().lower(),
        entities=entities_s,
        router_entity_retry_used=router_entity_retry_used,
    )
    answerability = _answerability_forecast(text, ambiguity)
    action = _next_action(
        text=text,
        ambiguity_types=ambiguity,
        freshness_requirement=freshness,
        answerability_forecast=answerability,
        source_class_expectation=source_class,
    )
    confidence = "high"
    if action == "preserve_multiple_frames":
        confidence = "low" if len(ambiguity) > 1 else "medium"
    elif action == "retrieve_to_anchor":
        confidence = "medium"
    if answerability == "likely non-public":
        confidence = "low"

    frame_subject = primary_entity_s or core_topic_s or query_s
    candidate_frames = [
        {
            "frame_id": "primary",
            "rationale": _compact_text(
                f"{query_type or 'other'} / {report_type or 'general_research'} frame for {frame_subject}"
            ),
        }
    ]
    if action == "preserve_multiple_frames":
        candidate_frames.append(
            {
                "frame_id": "alternate",
                "rationale": _compact_text(
                    "Preserve nearby interpretation because ambiguity is visible in router/query metadata."
                ),
            }
        )

    packet = {
        "schema_version": "anchor_packet_v1",
        "candidate_frames": candidate_frames,
        "selected_frame_id": "" if action == "preserve_multiple_frames" else "primary",
        "ambiguity_types": ambiguity,
        "confidence_bucket": confidence,
        "temporal_frame": temporal,
        "freshness_requirement": freshness,
        "source_class_expectation": source_class,
        "claim_or_metric_type": claim_type,
        "answerability_forecast": answerability,
        "decomposition_hints": _decomposition_hints(
            next_action=action,
            temporal_frame=temporal,
            source_class_expectation=source_class,
            answerability_forecast=answerability,
        ),
        "off_domain_traps": _off_domain_traps(text, ambiguity),
        "next_action": action,
        "clarification_question": None,
        "metadata": {
            "current_date": _compact_text(current_date, limit=40),
            "intent": _compact_text(intent, limit=40),
            "report_type": _compact_text(report_type, limit=60),
            "router_original_report_type": _compact_text(router_original_report_type, limit=60),
            "query_type": _compact_text(query_type, limit=60),
            "router_original_query_type": _compact_text(router_original_query_type, limit=60),
            "primary_entity": primary_entity_s,
            "entities": entities_s,
            "router_entity_retry_used": bool(router_entity_retry_used),
        },
    }

    return {
        "anchor_packet_shadow_mode": True,
        "anchor_packet_present": True,
        "anchor_packet_next_action": action,
        "anchor_packet_confidence_bucket": confidence,
        "anchor_packet_ambiguity_types": ambiguity,
        "anchor_packet": packet,
    }
