"""Summarize Economist shadow telemetry from execution JSONL logs.

This script is intentionally read-only: it parses execution log rows and prints
aggregate counts without importing or running the ProPlex pipeline.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "output" / "execution_log.jsonl"
TOP_LIMIT = 10
DEFAULT_MAX_DETAILS = 25
COMMIT_METADATA_FIELDS = (
    "commit_sha",
    "git_sha",
    "git_commit",
    "git_commit_sha",
    "code_version",
    "app_version",
    "build_sha",
    "revision",
)

BOOLEAN_COUNT_FIELDS = (
    "economist_pre_analyst_skip_candidate_shadow",
    "economist_skip_eligible_shadow",
    "high_stakes_quant_detected",
)
SAFETY_ANOMALY_FIELDS = (
    "author_received_raw_quant_packet",
    "author_received_economist_framework",
    "author_received_analyst_packet_marker",
    "analyst_skipped_after_economist",
    "economist_output_used_as_analysis",
    "economist_code_execution_requested",
)
AUTHOR_MARKER_LEAK_FIELDS = (
    "author_received_raw_quant_packet",
    "author_received_economist_framework",
    "author_received_analyst_packet_marker",
)
LIVE_BEHAVIOR_ANOMALY_FIELDS = (
    "analyst_skipped_after_economist",
    "economist_output_used_as_analysis",
)
BLOCKER_FIELDS = (
    "quant_retrieval_sufficiency_blockers",
    "economist_pre_analyst_skip_candidate_blockers",
    "economist_skip_eligibility_blockers",
)
PRE_ANALYST_RETRIEVAL_AUDIT_FIELDS = (
    "analyst_skipped",
    "analyst_skip_reason",
    "corpus_state",
    "utilization_rate",
    "source_tier_counts",
    "source_domain_counts",
    "top_source_domains",
    "official_evidence_found",
    "community_signal_found",
    "on_domain_source_count",
    "off_domain_source_count",
    "answer_class",
    "response_displayable",
    "evidence_sufficient",
)
POST_ECONOMIST_SEPARATE_FIELDS = (
    "analyst_skipped_after_economist",
    "economist_output_used_as_analysis",
)
NOTABLE_TRUE_FIELDS = (
    "economist_pre_analyst_skip_candidate_shadow",
    "economist_skip_eligible_shadow",
    "high_stakes_quant_detected",
    *SAFETY_ANOMALY_FIELDS,
)
OFFICIAL_LIKE_CDN_DOMAINS = frozenset(
    {
        "d18rn0p25nwr6d.cloudfront.net",
    }
)
POLLUTION_DOMAIN_BUCKETS = (
    ("academic_preprint", ("arxiv.org", "biorxiv.org", "medrxiv.org", "ssrn.com")),
    ("biomedical_index", ("ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov")),
    ("academic_publisher", ("nature.com", "plos.org", "science.org")),
)


def _label(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else "missing"
    return str(value)


def _bool_label(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "missing"


def _one_line(value: Any) -> str:
    if value is None:
        return "missing"
    text = str(value).strip()
    return " ".join(text.split()) if text else "missing"


def _truncate(value: Any, limit: int) -> str:
    text = _one_line(value)
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return f"{text[: limit - 3]}..."


def _blocker_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if not isinstance(value, (list, tuple, set)):
        return ["<non_list_blockers_field>"]

    blockers: list[str] = []
    for item in value:
        if item is None:
            continue
        if isinstance(item, str):
            if item:
                blockers.append(item)
        elif isinstance(item, (bool, int, float)):
            blockers.append(str(item))
        else:
            blockers.append("<non_scalar_blocker>")
    return blockers


def _blocker_union(row: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    seen: set[str] = set()
    for field in BLOCKER_FIELDS:
        for blocker in _blocker_values(row.get(field)):
            if blocker not in seen:
                blockers.append(blocker)
                seen.add(blocker)
    return blockers


def _row_value(row: dict[str, Any], field: str) -> Any:
    if field in row:
        return row.get(field)
    trace = row.get("execution_trace")
    if isinstance(trace, dict):
        return trace.get(field)
    return None


def _audit_row_value(row: dict[str, Any], field: str) -> Any:
    trace = row.get("execution_trace")
    if isinstance(trace, dict) and field in trace:
        return trace.get(field)
    return row.get(field)


def _scalar_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, (list, tuple, set)):
        return []

    out: list[str] = []
    for item in value:
        if item is None:
            continue
        if isinstance(item, (str, bool, int, float)):
            text = str(item).strip()
            if text:
                out.append(text)
    return out


def _domain_count_items(value: Any) -> list[tuple[str, int]]:
    if not isinstance(value, dict):
        return []

    out: list[tuple[str, int]] = []
    for raw_domain, raw_count in value.items():
        domain = str(raw_domain or "").strip().lower()
        if not domain:
            continue
        try:
            count = int(raw_count or 0)
        except (TypeError, ValueError):
            continue
        if count > 0:
            out.append((domain, count))
    return out


def _top_source_domain_items(row: dict[str, Any]) -> list[tuple[str, int]]:
    top_domains = _audit_row_value(row, "top_source_domains")
    if isinstance(top_domains, list):
        out: list[tuple[str, int]] = []
        for item in top_domains:
            if not isinstance(item, dict):
                continue
            domain = str(item.get("domain") or "").strip().lower()
            if not domain:
                continue
            try:
                count = int(item.get("count") or 0)
            except (TypeError, ValueError):
                continue
            if count > 0:
                out.append((domain, count))
        if out:
            return out[:TOP_LIMIT]

    return Counter(dict(_domain_count_items(_audit_row_value(row, "source_domain_counts")))).most_common(
        TOP_LIMIT
    )


def _source_tier_count_items(value: Any) -> list[tuple[str, int]]:
    if not isinstance(value, dict):
        return []

    out: list[tuple[str, int]] = []
    for raw_tier, raw_count in value.items():
        tier = str(raw_tier or "").strip().lower()
        if not tier:
            continue
        try:
            count = int(raw_count or 0)
        except (TypeError, ValueError):
            continue
        if count > 0:
            out.append((tier, count))
    return sorted(out)


def _source_tier_mix(value: Any) -> str:
    if not isinstance(value, dict):
        return "missing"
    items = _source_tier_count_items(value)
    if not items:
        return "empty"
    return "|".join(f"{tier}={count}" for tier, count in items)


def _utilization_band(value: Any) -> str:
    if value is None:
        return "missing"
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return "invalid"
    if rate < 0:
        return "below_0"
    if rate <= 0.35:
        return "low_<=0.35"
    if rate <= 0.70:
        return "medium_0.36_0.70"
    if rate <= 1.00:
        return "high_0.71_1.00"
    return "above_1.00"


def _count_label(value: Any) -> str:
    if value is None:
        return "missing"
    try:
        count = int(value)
    except (TypeError, ValueError):
        return "invalid"
    return str(count)


def _skip_reason_label(value: Any) -> str:
    if value is None:
        return "missing"
    if not isinstance(value, str):
        return "unknown"
    text = value.strip()
    return text if text else "missing"


def _host_suffix_matches(host: str, suffix: str) -> bool:
    normalized_host = host.lower().strip(".")
    normalized_suffix = suffix.lower().strip(".")
    return normalized_host == normalized_suffix or normalized_host.endswith(
        "." + normalized_suffix
    )


def _official_like_domain_bucket(domain: str) -> str | None:
    if _host_suffix_matches(domain, "sec.gov"):
        return "sec.gov"
    if _host_suffix_matches(domain, "annualreports.com"):
        return "annualreports.com"
    if _host_suffix_matches(domain, "q4cdn.com"):
        return "q4cdn.com"
    if domain in OFFICIAL_LIKE_CDN_DOMAINS:
        return "sec_filing_cdn"

    labels = [part for part in domain.split(".") if part]
    if labels:
        if labels[0] in {"investor", "investors"}:
            return "investor_subdomain"
        if labels[0] == "ir":
            return "ir_subdomain"
        if labels[0] == "newsroom":
            return "newsroom_subdomain"
    return None


def _pollution_domain_bucket(domain: str) -> str | None:
    for bucket, suffixes in POLLUTION_DOMAIN_BUCKETS:
        if any(_host_suffix_matches(domain, suffix) for suffix in suffixes):
            return bucket
    return None


def _is_quantitative_comparison_row(row: dict[str, Any]) -> bool:
    return (
        _label(_row_value(row, "report_type")) == "quantitative_comparison"
        or _label(_row_value(row, "query_type")) == "quantitative_comparison"
    )


def _is_notable_run(row: dict[str, Any]) -> bool:
    if row.get("quant_retrieval_sufficiency_valid") is False:
        return True
    return any(row.get(field) is True for field in NOTABLE_TRUE_FIELDS)


def _author_source(row: dict[str, Any]) -> Any:
    if "author_source" in row:
        return row.get("author_source")
    return row.get("author_quant_content_source")


def _unique(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _is_clean_positive_evidence(row: dict[str, Any]) -> bool:
    """Positive shadow evidence for review, not for live behavior changes."""

    if row.get("economist_pre_analyst_skip_candidate_shadow") is not True:
        return False
    if row.get("economist_skip_eligible_shadow") is not True:
        return False
    alignment = _label(row.get("economist_skip_shadow_alignment"))
    if alignment != "candidate_and_posthoc_eligible":
        return False
    if row.get("quant_retrieval_sufficiency_valid") is not True:
        return False
    if row.get("high_stakes_quant_detected") is not False:
        return False
    if any(row.get(field) is not False for field in SAFETY_ANOMALY_FIELDS):
        return False
    if _author_source(row) != "analyst_reviewed":
        return False
    if _blocker_union(row):
        return False
    return True


def _readiness_row_blockers(row: dict[str, Any]) -> list[str]:
    """Return diagnostic-only blockers for future human review."""

    blockers: list[str] = []
    pre_candidate = row.get("economist_pre_analyst_skip_candidate_shadow") is True
    posthoc_eligible = row.get("economist_skip_eligible_shadow") is True
    shadow_eligible = pre_candidate or posthoc_eligible
    alignment = _label(row.get("economist_skip_shadow_alignment"))

    if alignment in {"candidate_only", "posthoc_only"}:
        blockers.append(f"alignment_mismatch:{alignment}")
    elif shadow_eligible and alignment != "candidate_and_posthoc_eligible":
        blockers.append(f"alignment_missing_or_unexpected:{alignment}")

    for field in LIVE_BEHAVIOR_ANOMALY_FIELDS:
        if row.get(field) is True:
            blockers.append(f"live_behavior:{field}")

    for field in AUTHOR_MARKER_LEAK_FIELDS:
        if row.get(field) is True:
            blockers.append(f"author_marker_leak:{field}")

    if shadow_eligible:
        high_stakes = row.get("high_stakes_quant_detected")
        if high_stakes is True:
            blockers.append("unsafe_shadow_eligible:high_stakes")
        elif high_stakes is not False:
            blockers.append("unsafe_shadow_eligible:high_stakes_not_cleared")

        code_requested = row.get("economist_code_execution_requested")
        if code_requested is True:
            blockers.append("unsafe_shadow_eligible:code_execution_requested")
        elif code_requested is not False:
            blockers.append("unsafe_shadow_eligible:code_request_not_cleared")

        if row.get("quant_retrieval_sufficiency_valid") is not True:
            blockers.append("unsafe_shadow_eligible:retrieval_not_valid")

    if posthoc_eligible:
        if _author_source(row) != "analyst_reviewed":
            blockers.append("unsafe_shadow_eligible:author_not_analyst_reviewed")
        if row.get("analyst_quant_packet_reviewed_by_model") is not True:
            blockers.append("unsafe_shadow_eligible:packet_not_reviewed_by_analyst")

    if (
        row.get("high_stakes_quant_detected") is True
        and row.get("high_stakes_quant_future_direct_use_allowed") is not False
    ):
        blockers.append("high_stakes_guardrail:not_future_blocked")

    return _unique(blockers)


def _blocked_negative_controls(row: dict[str, Any]) -> list[str]:
    pre_candidate = row.get("economist_pre_analyst_skip_candidate_shadow") is True
    posthoc_eligible = row.get("economist_skip_eligible_shadow") is True
    if pre_candidate or posthoc_eligible:
        return []

    controls: list[str] = []
    if (
        row.get("high_stakes_quant_detected") is True
        and row.get("high_stakes_quant_future_direct_use_allowed") is False
    ):
        controls.append("high_stakes_guardrail_blocked")
    if row.get("economist_code_execution_requested") is True:
        controls.append("code_request_blocked")
    if row.get("quant_retrieval_sufficiency_valid") is False:
        controls.append("retrieval_sufficiency_blocked")
    return controls


def _update_readiness_summary(summary: dict[str, Any], row: dict[str, Any]) -> None:
    readiness = summary["readiness"]
    readiness["evaluated_execution_events"] += 1

    if _is_clean_positive_evidence(row):
        readiness["clean_positive_evidence_count"] += 1

    row_blockers = _readiness_row_blockers(row)
    if row_blockers:
        readiness["rows_with_readiness_blockers"] += 1
        readiness["promotion_blocker_counts"].update(row_blockers)

    for field in AUTHOR_MARKER_LEAK_FIELDS:
        if row.get(field) is True:
            readiness["marker_leak_counts"][field] += 1

    for field in LIVE_BEHAVIOR_ANOMALY_FIELDS:
        if row.get(field) is True:
            readiness["live_behavior_anomaly_counts"][field] += 1

    for blocker in row_blockers:
        if blocker.startswith("unsafe_shadow_eligible:"):
            readiness["unsafe_shadow_eligible_counts"][blocker] += 1
        if blocker.startswith("alignment_mismatch:"):
            readiness["alignment_mismatch_counts"][blocker] += 1

    readiness["negative_control_blocked_counts"].update(
        _blocked_negative_controls(row)
    )


def _finalize_readiness_summary(summary: dict[str, Any]) -> None:
    readiness = summary["readiness"]
    if readiness["evaluated_execution_events"] == 0:
        readiness["promotion_blocker_counts"]["no_execution_events"] += 1
    if readiness["clean_positive_evidence_count"] == 0:
        readiness["promotion_blocker_counts"]["no_clean_positive_evidence"] += 1
    readiness["readiness_for_review"] = (
        sum(readiness["promotion_blocker_counts"].values()) == 0
    )


def _update_official_target_evidence_diagnostics(
    summary: dict[str, Any], row: dict[str, Any]
) -> None:
    diagnostics = summary["official_target_evidence_diagnostics"]

    final_not_in_packet = _scalar_list(
        _row_value(row, "final_answer_source_ids_not_in_packet")
    )
    packet_not_in_final = _scalar_list(
        _row_value(row, "packet_source_ids_not_in_final_answer")
    )
    diverged = _row_value(row, "final_answer_packet_source_ids_diverged") is True
    if diverged or final_not_in_packet or packet_not_in_final:
        diagnostics["rows_with_final_packet_source_divergence"] += 1
    if final_not_in_packet:
        diagnostics["rows_with_final_sources_not_in_packet"] += 1
        diagnostics["top_final_answer_source_ids_not_in_packet"].update(
            final_not_in_packet
        )
    if packet_not_in_final:
        diagnostics["rows_with_packet_sources_not_in_final"] += 1
        diagnostics["top_packet_source_ids_not_in_final_answer"].update(
            packet_not_in_final
        )

    evidence_seen = set(_scalar_list(_row_value(row, "economist_evidence_source_ids_seen")))
    evidence_used = set(_scalar_list(_row_value(row, "economist_evidence_source_ids_used")))
    if evidence_seen - evidence_used:
        diagnostics["rows_with_economist_window_seen_but_not_used"] += 1

    domain_counts = _domain_count_items(_row_value(row, "source_domain_counts"))
    official_like_domains: Counter[str] = Counter()
    polluted_domains: Counter[str] = Counter()
    for domain, count in domain_counts:
        official_bucket = _official_like_domain_bucket(domain)
        if official_bucket:
            official_like_domains[official_bucket] += count

        pollution_bucket = _pollution_domain_bucket(domain)
        if pollution_bucket:
            polluted_domains[pollution_bucket] += count

    if (
        _row_value(row, "official_evidence_found") is False
        and official_like_domains
    ):
        diagnostics[
            "rows_with_official_evidence_found_false_but_official_like_domains_present"
        ] += 1
        diagnostics[
            "top_official_like_domains_present_when_official_evidence_found_false"
        ].update(official_like_domains)

    if _is_quantitative_comparison_row(row) and polluted_domains:
        diagnostics[
            "rows_with_academic_or_biomedical_domain_pollution_on_quantitative_comparison"
        ] += 1
        diagnostics["top_polluted_domains_for_quantitative_comparison"].update(
            polluted_domains
        )

    validation_errors = _scalar_list(
        _row_value(row, "quantitative_packet_validation_errors")
    )
    if (
        "target_metric_evidence_missing" in validation_errors
        and _row_value(row, "quant_retrieval_sufficiency_valid") is True
    ):
        diagnostics[
            "rows_where_target_metric_evidence_missing_but_retrieval_sufficiency_valid"
        ] += 1

    if (
        _scalar_list(_row_value(row, "target_metric_bound_value_refs"))
        and _row_value(row, "target_metric_evidence_found") is False
    ):
        diagnostics[
            "rows_where_target_bound_refs_present_but_target_metric_evidence_found_false"
        ] += 1


def _new_pre_analyst_skip_reason_detail() -> dict[str, Any]:
    return {
        "count": 0,
        "corpus_state_counts": Counter(),
        "utilization_band_counts": Counter(),
        "source_tier_mix_counts": Counter(),
        "source_tier_counts": Counter(),
        "top_source_domains": Counter(),
        "official_evidence_found_counts": Counter({"true": 0, "false": 0, "missing": 0}),
        "community_signal_found_counts": Counter({"true": 0, "false": 0, "missing": 0}),
        "on_domain_source_count_counts": Counter(),
        "off_domain_source_count_counts": Counter(),
        "answer_class_counts": Counter(),
        "response_displayable_counts": Counter({"true": 0, "false": 0, "missing": 0}),
        "evidence_sufficient_counts": Counter({"true": 0, "false": 0, "missing": 0}),
    }


def _pre_analyst_skip_reason_detail(
    audit: dict[str, Any], reason: str
) -> dict[str, Any]:
    details = audit["skip_reason_details"]
    if reason not in details:
        details[reason] = _new_pre_analyst_skip_reason_detail()
    return details[reason]


def _update_pre_analyst_retrieval_gate_audit(
    summary: dict[str, Any], row: dict[str, Any]
) -> None:
    audit = summary["pre_analyst_retrieval_gate_audit"]
    audit["denominator_execution_events"] += 1

    for field in PRE_ANALYST_RETRIEVAL_AUDIT_FIELDS:
        if _audit_row_value(row, field) is None:
            audit["missing_field_counts"][field] += 1

    skipped_label = _bool_label(_audit_row_value(row, "analyst_skipped"))
    audit["analyst_skipped_counts"][skipped_label] += 1

    for field in POST_ECONOMIST_SEPARATE_FIELDS:
        label = _bool_label(_audit_row_value(row, field))
        audit["post_economist_separate_counts"][f"{field}:{label}"] += 1

    after_economist_reason = _skip_reason_label(
        _audit_row_value(row, "analyst_after_economist_skip_reason")
    )
    if after_economist_reason != "missing":
        audit["analyst_after_economist_skip_reason_counts"][
            after_economist_reason
        ] += 1

    if skipped_label != "true":
        return

    audit["active_pre_analyst_skip_count"] += 1
    reason = _skip_reason_label(_audit_row_value(row, "analyst_skip_reason"))
    audit["analyst_skip_reason_counts"][reason] += 1
    detail = _pre_analyst_skip_reason_detail(audit, reason)
    detail["count"] += 1
    detail["corpus_state_counts"][_label(_audit_row_value(row, "corpus_state"))] += 1
    detail["utilization_band_counts"][
        _utilization_band(_audit_row_value(row, "utilization_rate"))
    ] += 1

    source_tier_counts = _audit_row_value(row, "source_tier_counts")
    detail["source_tier_mix_counts"][_source_tier_mix(source_tier_counts)] += 1
    detail["source_tier_counts"].update(dict(_source_tier_count_items(source_tier_counts)))
    detail["top_source_domains"].update(dict(_top_source_domain_items(row)))
    detail["official_evidence_found_counts"][
        _bool_label(_audit_row_value(row, "official_evidence_found"))
    ] += 1
    detail["community_signal_found_counts"][
        _bool_label(_audit_row_value(row, "community_signal_found"))
    ] += 1
    detail["on_domain_source_count_counts"][
        _count_label(_audit_row_value(row, "on_domain_source_count"))
    ] += 1
    detail["off_domain_source_count_counts"][
        _count_label(_audit_row_value(row, "off_domain_source_count"))
    ] += 1
    detail["answer_class_counts"][_label(_audit_row_value(row, "answer_class"))] += 1
    detail["response_displayable_counts"][
        _bool_label(_audit_row_value(row, "response_displayable"))
    ] += 1
    detail["evidence_sufficient_counts"][
        _bool_label(_audit_row_value(row, "evidence_sufficient"))
    ] += 1


def _notable_run_detail(row: dict[str, Any]) -> dict[str, str]:
    detail = {
        "run_id": _label(row.get("run_id")),
        "timestamp_utc": _label(row.get("timestamp_utc")),
        "query": _truncate(row.get("query"), 140),
        "mode": _label(row.get("mode")),
        "report_type": _label(row.get("report_type")),
        "complexity": _label(row.get("complexity")),
        "pre_candidate": _bool_label(
            row.get("economist_pre_analyst_skip_candidate_shadow")
        ),
        "posthoc_eligible": _bool_label(row.get("economist_skip_eligible_shadow")),
        "alignment": _label(row.get("economist_skip_shadow_alignment")),
        "retrieval_valid": _bool_label(row.get("quant_retrieval_sufficiency_valid")),
        "high_stakes": _bool_label(row.get("high_stakes_quant_detected")),
        "author_source": _label(_author_source(row)),
        "pre_candidate_gate_reason": _label(
            row.get("economist_pre_analyst_skip_candidate_gate_reason")
        ),
        "skip_eligibility_gate_reason": _label(
            row.get("economist_skip_eligibility_gate_reason")
        ),
        "retrieval_gate_reason": _label(
            row.get("quant_retrieval_sufficiency_gate_reason")
        ),
        "blockers": ", ".join(_blocker_union(row)) or "none",
    }
    if row.get("final_output_preview"):
        detail["final_output_preview"] = _truncate(row.get("final_output_preview"), 180)
    return detail


def _parse_timestamp_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text == "missing":
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _newest_first_sort_key(run: dict[str, str]) -> tuple[int, datetime]:
    parsed = _parse_timestamp_utc(run.get("timestamp_utc"))
    if parsed is None:
        return (0, datetime.min.replace(tzinfo=timezone.utc))
    return (1, parsed)


def _format_timestamp_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _update_execution_timestamp_window(
    summary: dict[str, Any], row: dict[str, Any]
) -> None:
    parsed = _parse_timestamp_utc(_row_value(row, "timestamp_utc"))
    if parsed is None:
        return

    oldest = _parse_timestamp_utc(summary.get("oldest_execution_timestamp"))
    if oldest is None or parsed < oldest:
        summary["oldest_execution_timestamp"] = _format_timestamp_utc(parsed)

    newest = _parse_timestamp_utc(summary.get("newest_execution_timestamp"))
    if newest is None or parsed > newest:
        summary["newest_execution_timestamp"] = _format_timestamp_utc(parsed)


def _commit_metadata_fields(row: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for field in COMMIT_METADATA_FIELDS:
        if _label(_row_value(row, field)) != "missing":
            fields.append(field)
    return fields


def summarize_log(path: str | Path) -> dict[str, Any]:
    """Return compact Economist telemetry counts for execution rows in ``path``."""

    jsonl_path = Path(path)
    summary: dict[str, Any] = {
        "path": jsonl_path,
        "total_lines_read": 0,
        "total_execution_events": 0,
        "oldest_execution_timestamp": None,
        "newest_execution_timestamp": None,
        "execution_rows_with_commit_metadata": 0,
        "commit_metadata_fields_seen": Counter(),
        "malformed_rows": 0,
        "non_execution_rows": 0,
        "report_type_counts": Counter(),
        "mode_counts": Counter(),
        "complexity_counts": Counter(),
        "boolean_counts": {
            field: Counter({"true": 0, "false": 0, "missing": 0})
            for field in BOOLEAN_COUNT_FIELDS
        },
        "economist_skip_shadow_alignment_counts": Counter(),
        "quant_retrieval_sufficiency_valid_counts": Counter({"true": 0, "false": 0, "missing": 0}),
        "blocker_counts": {field: Counter() for field in BLOCKER_FIELDS},
        "safety_anomaly_counts": Counter({field: 0 for field in SAFETY_ANOMALY_FIELDS}),
        "readiness": {
            "diagnostic_only": True,
            "readiness_for_review": False,
            "evaluated_execution_events": 0,
            "clean_positive_evidence_count": 0,
            "rows_with_readiness_blockers": 0,
            "promotion_blocker_counts": Counter(),
            "negative_control_blocked_counts": Counter(),
            "marker_leak_counts": Counter({field: 0 for field in AUTHOR_MARKER_LEAK_FIELDS}),
            "live_behavior_anomaly_counts": Counter(
                {field: 0 for field in LIVE_BEHAVIOR_ANOMALY_FIELDS}
            ),
            "unsafe_shadow_eligible_counts": Counter(),
            "alignment_mismatch_counts": Counter(),
        },
        "official_target_evidence_diagnostics": {
            "diagnostic_only": True,
            "rows_with_final_packet_source_divergence": 0,
            "rows_with_final_sources_not_in_packet": 0,
            "rows_with_packet_sources_not_in_final": 0,
            "rows_with_economist_window_seen_but_not_used": 0,
            "top_final_answer_source_ids_not_in_packet": Counter(),
            "top_packet_source_ids_not_in_final_answer": Counter(),
            "rows_with_official_evidence_found_false_but_official_like_domains_present": 0,
            "top_official_like_domains_present_when_official_evidence_found_false": Counter(),
            "rows_with_academic_or_biomedical_domain_pollution_on_quantitative_comparison": 0,
            "top_polluted_domains_for_quantitative_comparison": Counter(),
            "rows_where_target_metric_evidence_missing_but_retrieval_sufficiency_valid": 0,
            "rows_where_target_bound_refs_present_but_target_metric_evidence_found_false": 0,
        },
        "pre_analyst_retrieval_gate_audit": {
            "diagnostic_only": True,
            "source_of_truth": "execution_jsonl_full_trace",
            "sqlite_compact_summary_complete": False,
            "denominator_execution_events": 0,
            "active_pre_analyst_skip_count": 0,
            "analyst_skipped_counts": Counter({"true": 0, "false": 0, "missing": 0}),
            "analyst_skip_reason_counts": Counter(),
            "missing_field_counts": Counter(),
            "post_economist_separate_counts": Counter(),
            "analyst_after_economist_skip_reason_counts": Counter(),
            "skip_reason_details": {},
        },
        "notable_runs": [],
    }

    with jsonl_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            summary["total_lines_read"] += 1
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                summary["malformed_rows"] += 1
                continue

            if not isinstance(row, dict) or row.get("event") != "execution":
                summary["non_execution_rows"] += 1
                continue

            summary["total_execution_events"] += 1
            _update_execution_timestamp_window(summary, row)
            commit_fields = _commit_metadata_fields(row)
            if commit_fields:
                summary["execution_rows_with_commit_metadata"] += 1
                summary["commit_metadata_fields_seen"].update(commit_fields)

            summary["report_type_counts"][_label(row.get("report_type"))] += 1
            summary["mode_counts"][_label(row.get("mode"))] += 1
            summary["complexity_counts"][_label(row.get("complexity"))] += 1

            for field in BOOLEAN_COUNT_FIELDS:
                summary["boolean_counts"][field][_bool_label(row.get(field))] += 1

            alignment = _label(row.get("economist_skip_shadow_alignment"))
            summary["economist_skip_shadow_alignment_counts"][alignment] += 1

            sufficiency = _bool_label(row.get("quant_retrieval_sufficiency_valid"))
            summary["quant_retrieval_sufficiency_valid_counts"][sufficiency] += 1

            for field in BLOCKER_FIELDS:
                summary["blocker_counts"][field].update(_blocker_values(row.get(field)))

            for field in SAFETY_ANOMALY_FIELDS:
                if row.get(field) is True:
                    summary["safety_anomaly_counts"][field] += 1

            _update_readiness_summary(summary, row)
            _update_official_target_evidence_diagnostics(summary, row)
            _update_pre_analyst_retrieval_gate_audit(summary, row)

            if _is_notable_run(row):
                summary["notable_runs"].append(_notable_run_detail(row))

    _finalize_readiness_summary(summary)
    return summary


def _format_counter(counter: Counter[str], *, limit: int | None = None) -> list[str]:
    items = counter.most_common(limit)
    if not items:
        return ["  (none)"]
    return [f"  {key}: {count}" for key, count in items]


def _format_notable_runs(
    summary: dict[str, Any], *, max_details: int, newest_first: bool = False
) -> list[str]:
    notable_runs = summary.get("notable_runs", [])
    lines = ["", "notable runs:"]
    if not notable_runs:
        lines.append("  (none)")
        return lines

    if newest_first:
        notable_runs = sorted(
            notable_runs,
            key=_newest_first_sort_key,
            reverse=True,
        )
    shown_runs = notable_runs[:max_details]
    for index, run in enumerate(shown_runs, start=1):
        lines.append(f"- notable_run: {index}")
        for field, value in run.items():
            lines.append(f"  {field}: {value}")

    remaining = len(notable_runs) - len(shown_runs)
    if remaining > 0:
        lines.append(f"... {remaining} more notable runs not shown")
    return lines


def _format_nonzero_counter(
    counter: Counter[str], *, limit: int | None = None
) -> list[str]:
    nonzero = Counter({key: count for key, count in counter.items() if count})
    return _format_counter(nonzero, limit=limit)


def _format_fixed_counter(counter: Counter[str], fields: tuple[str, ...]) -> list[str]:
    return [f"  {field}: {counter[field]}" for field in fields]


def _format_readiness_summary(summary: dict[str, Any]) -> list[str]:
    readiness = summary.get("readiness", {})
    lines = [
        "",
        "readiness diagnostics:",
        f"  diagnostic_only: {str(bool(readiness.get('diagnostic_only'))).lower()}",
        f"  readiness_for_review: {str(bool(readiness.get('readiness_for_review'))).lower()}",
        f"  evaluated_execution_events: {readiness.get('evaluated_execution_events', 0)}",
        f"  clean_positive_evidence_count: {readiness.get('clean_positive_evidence_count', 0)}",
        f"  rows_with_readiness_blockers: {readiness.get('rows_with_readiness_blockers', 0)}",
        "readiness blockers:",
        *_format_nonzero_counter(readiness.get("promotion_blocker_counts", Counter())),
        "unsafe shadow eligible counts:",
        *_format_nonzero_counter(readiness.get("unsafe_shadow_eligible_counts", Counter())),
        "alignment mismatch counts:",
        *_format_nonzero_counter(readiness.get("alignment_mismatch_counts", Counter())),
        "marker leak counts:",
        *_format_fixed_counter(
            readiness.get("marker_leak_counts", Counter()),
            AUTHOR_MARKER_LEAK_FIELDS,
        ),
        "live behavior anomaly counts:",
        *_format_fixed_counter(
            readiness.get("live_behavior_anomaly_counts", Counter()),
            LIVE_BEHAVIOR_ANOMALY_FIELDS,
        ),
        "blocked negative-control counts:",
        *_format_nonzero_counter(
            readiness.get("negative_control_blocked_counts", Counter())
        ),
    ]
    return lines


def _format_log_metadata_summary(summary: dict[str, Any]) -> list[str]:
    commit_fields_seen = summary.get("commit_metadata_fields_seen", Counter())
    commit_field_lines = _format_nonzero_counter(commit_fields_seen)
    lines = [
        "",
        "log metadata:",
        "  historical_log_only: true",
        "  recomputed_with_current_code: false",
        "  diagnostic_note: historical log only; parsed rows are not recomputed with current code.",
        "  replay_warning: this script cannot replay historical rows; it only summarizes stored telemetry.",
        "  oldest_execution_timestamp: "
        f"{_label(summary.get('oldest_execution_timestamp'))}",
        "  newest_execution_timestamp: "
        f"{_label(summary.get('newest_execution_timestamp'))}",
        "  execution_rows_with_commit_metadata: "
        f"{summary.get('execution_rows_with_commit_metadata', 0)}",
        "  commit_metadata_fields_seen:",
        *commit_field_lines,
    ]
    if not commit_fields_seen:
        lines.append(
            "  commit_metadata_warning: missing commit SHA/code version metadata; "
            "use timestamps and run_id only."
        )
    return lines


def _format_official_target_evidence_diagnostics(
    summary: dict[str, Any]
) -> list[str]:
    diagnostics = summary.get("official_target_evidence_diagnostics", {})
    lines = [
        "",
        "official_target_evidence_diagnostics:",
        f"  diagnostic_only: {str(bool(diagnostics.get('diagnostic_only'))).lower()}",
        "  rows_with_final_packet_source_divergence: "
        f"{diagnostics.get('rows_with_final_packet_source_divergence', 0)}",
        "  rows_with_final_sources_not_in_packet: "
        f"{diagnostics.get('rows_with_final_sources_not_in_packet', 0)}",
        "  rows_with_packet_sources_not_in_final: "
        f"{diagnostics.get('rows_with_packet_sources_not_in_final', 0)}",
        "  rows_with_economist_window_seen_but_not_used: "
        f"{diagnostics.get('rows_with_economist_window_seen_but_not_used', 0)}",
        "  rows_with_official_evidence_found_false_but_official_like_domains_present: "
        f"{diagnostics.get('rows_with_official_evidence_found_false_but_official_like_domains_present', 0)}",
        "  rows_with_academic_or_biomedical_domain_pollution_on_quantitative_comparison: "
        f"{diagnostics.get('rows_with_academic_or_biomedical_domain_pollution_on_quantitative_comparison', 0)}",
        "  rows_where_target_metric_evidence_missing_but_retrieval_sufficiency_valid: "
        f"{diagnostics.get('rows_where_target_metric_evidence_missing_but_retrieval_sufficiency_valid', 0)}",
        "  rows_where_target_bound_refs_present_but_target_metric_evidence_found_false: "
        f"{diagnostics.get('rows_where_target_bound_refs_present_but_target_metric_evidence_found_false', 0)}",
        "top final_answer_source_ids_not_in_packet:",
        *_format_nonzero_counter(
            diagnostics.get("top_final_answer_source_ids_not_in_packet", Counter()),
            limit=TOP_LIMIT,
        ),
        "top packet_source_ids_not_in_final_answer:",
        *_format_nonzero_counter(
            diagnostics.get("top_packet_source_ids_not_in_final_answer", Counter()),
            limit=TOP_LIMIT,
        ),
        "top official-like domains present when official_evidence_found=false:",
        *_format_nonzero_counter(
            diagnostics.get(
                "top_official_like_domains_present_when_official_evidence_found_false",
                Counter(),
            ),
            limit=TOP_LIMIT,
        ),
        "top polluted domains for quantitative comparison rows:",
        *_format_nonzero_counter(
            diagnostics.get("top_polluted_domains_for_quantitative_comparison", Counter()),
            limit=TOP_LIMIT,
        ),
    ]
    return lines


def _format_pre_analyst_detail(
    reason: str, detail: dict[str, Any], *, limit: int = TOP_LIMIT
) -> list[str]:
    lines = [
        f"- analyst_skip_reason: {reason}",
        f"  count: {detail.get('count', 0)}",
        "  corpus_state_counts:",
        *_format_counter(detail.get("corpus_state_counts", Counter()), limit=limit),
        "  utilization_band_counts:",
        *_format_counter(detail.get("utilization_band_counts", Counter()), limit=limit),
        "  source_tier_mix_counts:",
        *_format_counter(detail.get("source_tier_mix_counts", Counter()), limit=limit),
        "  aggregate_source_tier_counts:",
        *_format_counter(detail.get("source_tier_counts", Counter()), limit=limit),
        "  top_source_domains:",
        *_format_counter(detail.get("top_source_domains", Counter()), limit=limit),
        "  official_evidence_found_counts:",
    ]
    for key in ("true", "false", "missing"):
        lines.append(f"    {key}: {detail['official_evidence_found_counts'][key]}")
    lines.append("  community_signal_found_counts:")
    for key in ("true", "false", "missing"):
        lines.append(f"    {key}: {detail['community_signal_found_counts'][key]}")
    lines.extend(
        [
            "  on_domain_source_count_counts:",
            *_format_counter(
                detail.get("on_domain_source_count_counts", Counter()), limit=limit
            ),
            "  off_domain_source_count_counts:",
            *_format_counter(
                detail.get("off_domain_source_count_counts", Counter()), limit=limit
            ),
            "  answer_class_counts:",
            *_format_counter(detail.get("answer_class_counts", Counter()), limit=limit),
            "  response_displayable_counts:",
        ]
    )
    for key in ("true", "false", "missing"):
        lines.append(f"    {key}: {detail['response_displayable_counts'][key]}")
    lines.append("  evidence_sufficient_counts:")
    for key in ("true", "false", "missing"):
        lines.append(f"    {key}: {detail['evidence_sufficient_counts'][key]}")
    return lines


def _format_pre_analyst_retrieval_gate_audit(summary: dict[str, Any]) -> list[str]:
    audit = summary.get("pre_analyst_retrieval_gate_audit", {})
    lines = [
        "",
        "pre_analyst_retrieval_gate_audit:",
        f"  diagnostic_only: {str(bool(audit.get('diagnostic_only'))).lower()}",
        f"  source_of_truth: {_label(audit.get('source_of_truth'))}",
        "  sqlite_compact_summary_complete: "
        f"{str(bool(audit.get('sqlite_compact_summary_complete'))).lower()}",
        "  denominator_execution_events: "
        f"{audit.get('denominator_execution_events', 0)}",
        "  active_pre_analyst_skip_count: "
        f"{audit.get('active_pre_analyst_skip_count', 0)}",
        "analyst_skipped counts:",
    ]
    skipped_counts = audit.get("analyst_skipped_counts", Counter())
    for key in ("true", "false", "missing"):
        lines.append(f"  {key}: {skipped_counts[key]}")

    lines.extend(
        [
            "analyst_skip_reason counts:",
            *_format_counter(audit.get("analyst_skip_reason_counts", Counter())),
            "post-Economist fields kept separate:",
            *_format_counter(audit.get("post_economist_separate_counts", Counter())),
            "analyst_after_economist_skip_reason counts:",
            *_format_counter(
                audit.get("analyst_after_economist_skip_reason_counts", Counter())
            ),
            "missing pre-Analyst audit fields:",
            *_format_counter(audit.get("missing_field_counts", Counter())),
            "active pre-Analyst skip details:",
        ]
    )

    details = audit.get("skip_reason_details", {})
    if not details:
        lines.append("  (none)")
        return lines

    for reason, detail in sorted(details.items()):
        lines.extend(_format_pre_analyst_detail(reason, detail))
    return lines


def format_summary(
    summary: dict[str, Any],
    *,
    include_details: bool = False,
    max_details: int = DEFAULT_MAX_DETAILS,
    newest_first: bool = False,
) -> str:
    """Format ``summarize_log`` output for stdout."""

    lines = [
        "Economist Telemetry Summary",
        f"log: {summary['path']}",
        f"total_lines_read: {summary['total_lines_read']}",
        f"execution_events: {summary['total_execution_events']}",
        f"malformed_rows: {summary['malformed_rows']}",
        f"non_execution_rows: {summary['non_execution_rows']}",
        "",
        "report_type counts:",
        *_format_counter(summary["report_type_counts"]),
        "",
        "mode counts:",
        *_format_counter(summary["mode_counts"]),
        "",
        "complexity counts:",
        *_format_counter(summary["complexity_counts"]),
        "",
        "shadow boolean counts:",
    ]

    boolean_counts = summary["boolean_counts"]
    for field in BOOLEAN_COUNT_FIELDS:
        lines.append(f"{field} counts:")
        for key in ("true", "false", "missing"):
            lines.append(f"  {key}: {boolean_counts[field][key]}")

    lines.extend(
        [
            "",
            "economist_skip_shadow_alignment counts:",
            *_format_counter(summary["economist_skip_shadow_alignment_counts"]),
            "",
            "quant_retrieval_sufficiency_valid counts:",
        ]
    )
    sufficiency_counts = summary["quant_retrieval_sufficiency_valid_counts"]
    for key in ("true", "false", "missing"):
        if key in sufficiency_counts:
            lines.append(f"  {key}: {sufficiency_counts[key]}")

    for field in BLOCKER_FIELDS:
        lines.extend(
            [
                "",
                f"top {field}:",
                *_format_counter(summary["blocker_counts"][field], limit=TOP_LIMIT),
            ]
        )

    lines.extend(["", "safety anomaly counts:"])
    anomaly_counts = summary["safety_anomaly_counts"]
    for field in SAFETY_ANOMALY_FIELDS:
        lines.append(f"  {field}: {anomaly_counts[field]}")

    lines.extend(_format_log_metadata_summary(summary))
    lines.extend(_format_readiness_summary(summary))
    lines.extend(_format_official_target_evidence_diagnostics(summary))
    lines.extend(_format_pre_analyst_retrieval_gate_audit(summary))

    if include_details:
        lines.extend(
            _format_notable_runs(
                summary,
                max_details=max(0, max_details),
                newest_first=newest_first,
            )
        )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "jsonl_path",
        nargs="?",
        default=str(DEFAULT_LOG),
        help=f"Path to execution JSONL log. Defaults to {DEFAULT_LOG}.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Append run-level details for notable execution rows.",
    )
    parser.add_argument(
        "--max-details",
        type=int,
        default=DEFAULT_MAX_DETAILS,
        help=f"Maximum notable runs to print with --details. Defaults to {DEFAULT_MAX_DETAILS}.",
    )
    parser.add_argument(
        "--newest-first",
        action="store_true",
        help="Sort notable run details by timestamp_utc descending before limiting.",
    )
    args = parser.parse_args(argv)
    path = Path(args.jsonl_path)
    if not path.exists():
        print(f"No log at {path}")
        return 1

    print(
        format_summary(
            summarize_log(path),
            include_details=args.details,
            max_details=args.max_details,
            newest_first=args.newest_first,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
