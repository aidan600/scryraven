"""AG-50C allowed-artifact export for recovery execution visibility.

This module formats already-sanitized runtime facts for reports and local
output-quality packets. It does not retrieve, route providers, choose depth,
rank/filter sources, classify returned sources, read logs/DB/cache files, alter
prompts, or affect final-answer behavior.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from core.authority_candidate_passport import (
    AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY,
)
from core.official_canonical_recovery_execution_admission import (
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY,
)
from core.official_source_obligation_candidate_visibility import (
    OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY,
)
from core.official_source_survival_projection import (
    OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY,
)

OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY = (
    "official_canonical_recovery_visibility_export"
)
OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_SCHEMA_VERSION = (
    "official_canonical_recovery_visibility_ag50c_v1"
)
OFFICIAL_CANONICAL_RECOVERY_DIAGNOSTICS_TITLE = (
    "Official / Canonical Source Recovery Diagnostics"
)

UNKNOWN = "unknown"
NOT_OBSERVABLE = "not_observable"

_MAX_QUERY_PREVIEWS = 3
_MAX_LIST_ITEMS = 8
_MAX_QUERY_CHARS = 140
_MAX_TEXT_CHARS = 120
_OFFICIAL_OR_CANONICAL_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)
_OFFICIAL_OR_CANONICAL_TIERS = frozenset({"official", "primary", "canonical"})
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "cache",
    "credential",
    "db",
    "env",
    "full_trace",
    "key",
    "log",
    "output_packet",
    "password",
    "prompt",
    "provider_payload",
    "raw_",
    "secret",
    "token",
)
_PROTECTED_MARKERS = (
    "raw prompt",
    "raw_provider",
    "provider_payload",
    "secret",
    "token",
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(
        r"(?i)\b(api[_ -]?key|secret|token|password)\b\s*[:=]\s*[^,\s;]+"
    ),
)


def build_official_canonical_recovery_visibility_export(
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build the compact AG-50C visibility export from whitelisted fields."""
    trace = runtime_trace if isinstance(runtime_trace, Mapping) else {}
    admission = _admission_payload(trace)
    candidate = _candidate_payload(trace)
    survival = _survival_payload(trace)
    lifecycle_candidate_fit = _authority_lifecycle_candidate_fit(trace)
    authority_candidate_passport = _authority_candidate_passport_payload(trace)

    admission_considered = _bool_or_unknown(admission.get("admission_considered"))
    admission_eligible = _bool_or_unknown(admission.get("admission_eligible"))
    admission_used = _bool_or_unknown(admission.get("admission_used"))
    source_class_eligible = _bool_or_unknown(
        trace.get("active_source_class_recovery_eligible")
    )
    source_class_used = _bool_or_unknown(
        trace.get("active_source_class_recovery_used")
    )
    execution_attempted = _bool_or_unknown(
        trace.get("active_source_class_recovery_execution_attempted")
    )
    if execution_attempted == UNKNOWN and source_class_used != UNKNOWN:
        execution_attempted = source_class_used

    recovered_result_count = _first_known_int(
        trace.get("active_source_class_recovery_result_count"),
        _nested(
            trace,
            ("source_class_recovery_validation_l1", "active_result_count"),
        ),
        _nested(
            trace,
            (
                "source_class_recovery_validation_l1",
                "provider_attempt_totals",
                "result_count",
            ),
        ),
    )
    accepted_url_count = _first_known_int(
        trace.get("recovered_accepted_url_count"),
        _nested(
            trace,
            ("source_class_recovery_validation_l1", "accepted_url_count"),
        ),
        _nested(
            trace,
            (
                "source_class_recovery_validation_l1",
                "provider_attempt_totals",
                "accepted_url_count",
            ),
        ),
    )
    recovered_class_counts = _safe_count_map(
        trace.get("recovered_source_class_counts"),
        allowed=_OFFICIAL_OR_CANONICAL_CLASSES,
    )
    recovered_tier_counts = _safe_count_map(
        trace.get("recovered_source_tier_counts"),
        allowed=_OFFICIAL_OR_CANONICAL_TIERS,
    )
    zero_candidate_blocker = _optional_text(
        trace.get("zero_candidate_blocker")
    )
    zero_candidate_blocker_kind = _optional_text(
        trace.get("zero_candidate_blocker_kind")
    )
    candidate_acquisition_provider_result_count = _first_known_int(
        trace.get("candidate_acquisition_provider_result_count")
    )
    candidate_acquisition_provider_accepted_url_count = _first_known_int(
        trace.get("candidate_acquisition_provider_accepted_url_count")
    )
    candidate_acquisition_provider_new_source_count = _first_known_int(
        trace.get("candidate_acquisition_provider_new_source_count")
    )
    candidate_acquisition_result_status = _optional_text(
        trace.get("candidate_acquisition_result_status")
    )
    candidate_visibility_export_status = _optional_text(
        trace.get("candidate_visibility_export_status")
    )
    candidate_visibility_blocker_kind = _optional_text(
        trace.get("candidate_visibility_blocker_kind")
    )

    candidate_official_or_canonical_count = _candidate_count(
        trace,
        candidate,
        recovered_class_counts,
        source_class_used=source_class_used,
    )
    candidate_official_or_canonical_count_basis = _candidate_count_basis(trace)
    accepted_or_readable_count = _accepted_or_readable_count(
        trace,
        candidate,
        source_class_used=source_class_used,
    )
    returned_or_evaluated_count = _returned_or_evaluated_candidate_count(
        trace,
        lifecycle_candidate_fit,
        candidate_official_or_canonical_count,
    )
    rejected_candidate_count = _rejected_candidate_count(
        trace,
        lifecycle_candidate_fit,
    )
    accepted_readable_authority_evidence_count = (
        _accepted_readable_authority_evidence_count(
            trace,
            lifecycle_candidate_fit,
            accepted_or_readable_count,
        )
    )
    final_selected_authority_evidence_count = (
        _final_selected_authority_evidence_count(trace, lifecycle_candidate_fit)
    )
    final_evidence_count = _first_known_int(
        trace.get("source_survival_final_evidence_official_or_canonical_count"),
        survival.get("final_evidence_official_or_canonical_count"),
    )
    final_citation_count = _first_known_int(
        trace.get("source_survival_final_citation_official_or_canonical_count"),
        survival.get("final_citation_official_or_canonical_count"),
    )

    recovery_query_previews = _recovery_query_previews(trace, admission)
    recovery_query_count = _first_known_int(
        admission.get("recovery_query_count"),
        len(recovery_query_previews) if recovery_query_previews else UNKNOWN,
    )

    export = {
        "schema_version": OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_SCHEMA_VERSION,
        "diagnostic_only": True,
        "sanitized": True,
        "official_canonical_recovery_visibility_status": _visibility_status(
            admission_considered=admission_considered,
            source_class_eligible=source_class_eligible,
            source_class_used=source_class_used,
            recovered_result_count=recovered_result_count,
        ),
        "admission_considered": admission_considered,
        "admission_eligible": admission_eligible,
        "admission_used": admission_used,
        "admission_skip_reason": _optional_text_field(
            admission,
            "admission_skip_reason",
        ),
        "admission_blockers": _safe_list(admission.get("admission_blockers")),
        "source_class_recovery_eligible": source_class_eligible,
        "source_class_recovery_used": source_class_used,
        "source_class_recovery_execution_attempted": execution_attempted,
        "source_class_recovery_skip_reason": _optional_text_field(
            trace,
            "active_source_class_recovery_skip_reason",
        ),
        "source_class_recovery_provider_role": _optional_text(
            trace.get("active_source_class_recovery_provider_role")
        ),
        "recovery_query_count": recovery_query_count,
        "recovery_query_previews": recovery_query_previews,
        "recovered_result_count": recovered_result_count,
        "accepted_url_count": accepted_url_count,
        "recovered_candidate_domain_preview": _safe_list(
            trace.get("recovered_candidate_domain_preview")
        ),
        "recovered_source_class_counts": recovered_class_counts,
        "recovered_source_tier_counts": recovered_tier_counts,
        "candidate_official_or_canonical_count": (
            candidate_official_or_canonical_count
        ),
        "candidate_official_or_canonical_count_basis": (
            candidate_official_or_canonical_count_basis
        ),
        "returned_or_evaluated_official_or_canonical_count": (
            returned_or_evaluated_count
        ),
        "rejected_official_or_canonical_candidate_count": (
            rejected_candidate_count
        ),
        "accepted_or_readable_official_or_canonical_count": (
            accepted_or_readable_count
        ),
        "accepted_readable_authority_evidence_count": (
            accepted_readable_authority_evidence_count
        ),
        "final_selected_authority_evidence_count": (
            final_selected_authority_evidence_count
        ),
        "final_evidence_official_or_canonical_count": final_evidence_count,
        "final_citation_official_or_canonical_count": final_citation_count,
        "candidate_return_visibility_status": _count_visibility_status(
            recovered_result_count
        ),
        "candidate_return_status": _candidate_return_status(
            execution_attempted=execution_attempted,
            recovered_result_count=recovered_result_count,
            precomputed_status=trace.get("candidate_return_status")
            or lifecycle_candidate_fit.get("candidate_return_status"),
        ),
        "zero_candidate_blocker": zero_candidate_blocker,
        "zero_candidate_blocker_kind": zero_candidate_blocker_kind,
        "candidate_acquisition_considered": _bool_or_unknown(
            trace.get("candidate_acquisition_considered")
        ),
        "candidate_acquisition_eligible": _bool_or_unknown(
            trace.get("candidate_acquisition_eligible")
        ),
        "candidate_acquisition_used": _bool_or_unknown(
            trace.get("candidate_acquisition_used")
        ),
        "candidate_acquisition_skip_reason": _optional_text_field(
            trace,
            "candidate_acquisition_skip_reason",
        ),
        "candidate_acquisition_blockers": _safe_list(
            trace.get("candidate_acquisition_blockers")
        ),
        "acquisition_provider_role": _optional_text(
            trace.get("acquisition_provider_role")
        ),
        "acquisition_query_count": _first_known_int(
            trace.get("acquisition_query_count")
        ),
        "acquisition_query_previews": _safe_list(
            trace.get("acquisition_query_previews"),
            limit=_MAX_QUERY_PREVIEWS,
            text_limit=_MAX_QUERY_CHARS,
        ),
        "acquisition_attempted": _bool_or_unknown(
            trace.get("acquisition_attempted")
        ),
        "candidate_acquisition_provider_result_count": (
            candidate_acquisition_provider_result_count
        ),
        "candidate_acquisition_provider_accepted_url_count": (
            candidate_acquisition_provider_accepted_url_count
        ),
        "candidate_acquisition_provider_new_source_count": (
            candidate_acquisition_provider_new_source_count
        ),
        "candidate_acquisition_result_status": candidate_acquisition_result_status,
        "candidate_visibility_export_status": candidate_visibility_export_status,
        "candidate_visibility_blocker_kind": candidate_visibility_blocker_kind,
        "official_canonical_candidate_visible": _bool_or_unknown(
            trace.get("official_canonical_candidate_visible")
        ),
        "authority_candidate_passport_available": bool(
            authority_candidate_passport
        ),
        "authority_candidate_passport_schema_version": (
            _optional_text(authority_candidate_passport.get("schema_version"))
            if authority_candidate_passport
            else NOT_OBSERVABLE
        ),
        "authority_candidate_passport_count": (
            _first_known_int(authority_candidate_passport.get("passport_count"))
            if authority_candidate_passport
            else UNKNOWN
        ),
        "authority_candidate_passport_integrity_status": (
            _optional_text(
                authority_candidate_passport.get("passport_integrity_status")
            )
            if authority_candidate_passport
            else NOT_OBSERVABLE
        ),
        "authority_candidate_passport_final_dispositions": (
            _passport_field_values(
                authority_candidate_passport,
                "final_disposition",
            )
            if authority_candidate_passport
            else NOT_OBSERVABLE
        ),
        "authority_candidate_passport_first_missing_stages": (
            _passport_field_values(
                authority_candidate_passport,
                "first_missing_stage",
            )
            if authority_candidate_passport
            else NOT_OBSERVABLE
        ),
        "authority_candidate_passport_projection": (
            authority_candidate_passport or NOT_OBSERVABLE
        ),
        "recovered_candidate_source_fit_status": _optional_text(
            trace.get("recovered_visibility_source_fit_status")
            or _legacy_lifecycle_fit_state(lifecycle_candidate_fit)
        ),
        "recovered_candidate_source_fit_count": _first_known_int(
            trace.get("recovered_visibility_source_fit_candidate_count"),
            _lifecycle_candidate_count(lifecycle_candidate_fit),
        ),
        "recovered_candidate_selected_readable_count": _first_known_int(
            trace.get("recovered_visibility_source_fit_selected_count"),
            _lifecycle_selected_count(lifecycle_candidate_fit),
        ),
        "recovered_candidate_rejection_reasons": _safe_list(
            trace.get("recovered_visibility_source_fit_rejection_reasons")
            or _lifecycle_rejection_reasons(lifecycle_candidate_fit)
        ),
        "citation_eligibility_state": _citation_eligibility_state(trace),
        "accepted_readable_visibility_status": _count_visibility_status(
            accepted_or_readable_count
        ),
        "final_evidence_survival_status": _count_visibility_status(
            final_evidence_count
        ),
        "final_citation_survival_status": _count_visibility_status(
            final_citation_count
        ),
        "likely_next_failure_layer": classify_likely_next_failure_layer(
            admission_used=admission_used,
            source_class_recovery_used=execution_attempted,
            recovered_result_count=recovered_result_count,
            candidate_official_or_canonical_count=(
                candidate_official_or_canonical_count
            ),
            accepted_or_readable_official_or_canonical_count=(
                accepted_or_readable_count
            ),
            final_evidence_official_or_canonical_count=final_evidence_count,
            final_citation_official_or_canonical_count=final_citation_count,
            candidate_visibility_export_status=candidate_visibility_export_status,
            zero_candidate_blocker_kind=zero_candidate_blocker_kind,
        ),
        "next_failure_layer": classify_ag50d_next_failure_layer(
            admission_used=admission_used,
            execution_attempted=execution_attempted,
            recovered_result_count=recovered_result_count,
            candidate_official_or_canonical_count=(
                candidate_official_or_canonical_count
            ),
            accepted_or_readable_official_or_canonical_count=(
                accepted_or_readable_count
            ),
            final_citation_official_or_canonical_count=final_citation_count,
            candidate_visibility_export_status=candidate_visibility_export_status,
            zero_candidate_blocker_kind=zero_candidate_blocker_kind,
        ),
        "unknown_fields": [],
        "behavior_changed": False,
    }
    export["unknown_fields"] = _unknown_fields(export)
    return export


def build_official_canonical_recovery_visibility_trace(
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build a trace-envelope version of the allowed-artifact export."""
    return {
        "schema_version": OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_SCHEMA_VERSION,
        "trace_mode": "allowed_artifact_visibility_export",
        "OfficialCanonicalRecoveryVisibility": (
            build_official_canonical_recovery_visibility_export(runtime_trace)
        ),
    }


def classify_likely_next_failure_layer(
    *,
    admission_used: Any,
    source_class_recovery_used: Any,
    recovered_result_count: Any,
    candidate_official_or_canonical_count: Any,
    accepted_or_readable_official_or_canonical_count: Any,
    final_evidence_official_or_canonical_count: Any,
    final_citation_official_or_canonical_count: Any,
    candidate_visibility_export_status: Any = UNKNOWN,
    zero_candidate_blocker_kind: Any = UNKNOWN,
) -> str:
    """Classify the next visible layer without inferring upstream facts."""
    if admission_used is False:
        return "admission_not_used"
    if admission_used != True:  # noqa: E712 - preserve unknown sentinel handling.
        return NOT_OBSERVABLE
    if source_class_recovery_used is False:
        return "execution_not_attempted"
    if source_class_recovery_used != True:  # noqa: E712
        return NOT_OBSERVABLE

    if recovered_result_count == UNKNOWN:
        return "candidate_return_not_visible"
    if _is_zero(recovered_result_count):
        if candidate_visibility_export_status == "candidate_visibility_not_exported":
            return "candidate_visibility_not_exported"
        if candidate_visibility_export_status == "acquisition_result_not_observable":
            return "acquisition_result_not_observable"
        if zero_candidate_blocker_kind == "provider_returned_zero_results":
            return "provider_returned_zero_results"
        return "recovery_executed_no_candidate_visibility"
    if not _positive_int(recovered_result_count):
        return NOT_OBSERVABLE

    if candidate_official_or_canonical_count == UNKNOWN:
        return NOT_OBSERVABLE
    if _is_zero(candidate_official_or_canonical_count):
        return "candidate_returned_no_official_canonical_visible"

    if accepted_or_readable_official_or_canonical_count == UNKNOWN:
        return "official_canonical_candidate_visible_not_accepted"
    if _is_zero(accepted_or_readable_official_or_canonical_count):
        return "official_canonical_candidate_visible_not_accepted"

    if final_evidence_official_or_canonical_count == UNKNOWN:
        return NOT_OBSERVABLE
    if _is_zero(final_evidence_official_or_canonical_count):
        return "accepted_source_not_in_final_evidence"

    if final_citation_official_or_canonical_count == UNKNOWN:
        return NOT_OBSERVABLE
    if _is_zero(final_citation_official_or_canonical_count):
        return "final_evidence_source_not_cited"
    if _positive_int(final_citation_official_or_canonical_count):
        return "source_survived_to_citation"
    return NOT_OBSERVABLE


def classify_ag50d_next_failure_layer(
    *,
    admission_used: Any,
    execution_attempted: Any,
    recovered_result_count: Any,
    candidate_official_or_canonical_count: Any,
    accepted_or_readable_official_or_canonical_count: Any,
    final_citation_official_or_canonical_count: Any,
    candidate_visibility_export_status: Any = UNKNOWN,
    zero_candidate_blocker_kind: Any = UNKNOWN,
) -> str:
    """Classify the AG-50D allowed-artifact dispatch/result layer."""
    if admission_used is False:
        return "admission_not_used"
    if admission_used != True:  # noqa: E712 - preserve unknown sentinel handling.
        return "telemetry_gap"
    if execution_attempted is False:
        return "execution_not_attempted"
    if execution_attempted != True:  # noqa: E712
        return "telemetry_gap"
    if recovered_result_count == UNKNOWN:
        return "execution_attempted_candidate_return_unknown"
    if _is_zero(recovered_result_count):
        if candidate_visibility_export_status == "candidate_visibility_not_exported":
            return "execution_attempted_candidate_visibility_not_exported"
        if candidate_visibility_export_status == "acquisition_result_not_observable":
            return "execution_attempted_acquisition_result_not_observable"
        return "execution_attempted_zero_candidates"
    if not _positive_int(recovered_result_count):
        return "telemetry_gap"
    if candidate_official_or_canonical_count == UNKNOWN:
        return "execution_attempted_candidate_return_unknown"
    if _is_zero(candidate_official_or_canonical_count):
        return "canonical_candidate_returned_not_accepted"
    if accepted_or_readable_official_or_canonical_count == UNKNOWN:
        return "canonical_candidate_returned_not_accepted"
    if _is_zero(accepted_or_readable_official_or_canonical_count):
        return "canonical_candidate_returned_not_accepted"
    if final_citation_official_or_canonical_count == UNKNOWN:
        return "telemetry_gap"
    if _is_zero(final_citation_official_or_canonical_count):
        return "canonical_candidate_accepted_not_cited"
    if _positive_int(final_citation_official_or_canonical_count):
        return "canonical_source_cited"
    return "telemetry_gap"


def format_official_canonical_recovery_diagnostics_markdown(
    runtime_trace_or_export: Mapping[str, Any] | None,
) -> str:
    """Render the AG-50C export as a compact Markdown report section."""
    if _looks_like_export(runtime_trace_or_export):
        export = dict(runtime_trace_or_export or {})
    else:
        export = build_official_canonical_recovery_visibility_export(
            runtime_trace_or_export
        )
    lines = [f"## {OFFICIAL_CANONICAL_RECOVERY_DIAGNOSTICS_TITLE}"]
    for key in (
        "official_canonical_recovery_visibility_status",
        "admission_considered",
        "admission_eligible",
        "admission_used",
        "admission_skip_reason",
        "admission_blockers",
        "source_class_recovery_eligible",
        "source_class_recovery_used",
        "source_class_recovery_execution_attempted",
        "source_class_recovery_skip_reason",
        "source_class_recovery_provider_role",
        "recovery_query_count",
        "recovery_query_previews",
        "recovered_result_count",
        "accepted_url_count",
        "recovered_candidate_domain_preview",
        "recovered_source_class_counts",
        "recovered_source_tier_counts",
        "candidate_official_or_canonical_count",
        "candidate_official_or_canonical_count_basis",
        "returned_or_evaluated_official_or_canonical_count",
        "rejected_official_or_canonical_candidate_count",
        "accepted_or_readable_official_or_canonical_count",
        "accepted_readable_authority_evidence_count",
        "final_selected_authority_evidence_count",
        "final_evidence_official_or_canonical_count",
        "final_citation_official_or_canonical_count",
        "candidate_return_visibility_status",
        "candidate_return_status",
        "zero_candidate_blocker",
        "zero_candidate_blocker_kind",
        "candidate_acquisition_considered",
        "candidate_acquisition_eligible",
        "candidate_acquisition_used",
        "candidate_acquisition_skip_reason",
        "candidate_acquisition_blockers",
        "acquisition_provider_role",
        "acquisition_query_count",
        "acquisition_query_previews",
        "acquisition_attempted",
        "candidate_acquisition_provider_result_count",
        "candidate_acquisition_provider_accepted_url_count",
        "candidate_acquisition_provider_new_source_count",
        "candidate_acquisition_result_status",
        "candidate_visibility_export_status",
        "candidate_visibility_blocker_kind",
        "official_canonical_candidate_visible",
        "authority_candidate_passport_available",
        "authority_candidate_passport_schema_version",
        "authority_candidate_passport_count",
        "authority_candidate_passport_integrity_status",
        "authority_candidate_passport_final_dispositions",
        "authority_candidate_passport_first_missing_stages",
        "recovered_candidate_source_fit_status",
        "recovered_candidate_source_fit_count",
        "recovered_candidate_selected_readable_count",
        "recovered_candidate_rejection_reasons",
        "citation_eligibility_state",
        "accepted_readable_visibility_status",
        "final_evidence_survival_status",
        "final_citation_survival_status",
        "likely_next_failure_layer",
        "next_failure_layer",
        "unknown_fields",
        "behavior_changed",
    ):
        lines.append(f"- `{key}`: {_format_value(export.get(key, UNKNOWN))}")
    return "\n".join(lines)


def append_official_canonical_recovery_diagnostics_section(
    report: str,
    runtime_trace: Mapping[str, Any] | None,
) -> str:
    """Append the allowed diagnostics section to a report string."""
    base = str(report or "").rstrip()
    section = format_official_canonical_recovery_diagnostics_markdown(runtime_trace)
    return f"{base}\n\n{section}\n" if base else f"{section}\n"


def _admission_payload(trace: Mapping[str, Any]) -> dict[str, Any]:
    packet = trace.get(OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY)
    if isinstance(packet, Mapping):
        payload = packet.get("OfficialCanonicalRecoveryExecutionAdmission")
        if isinstance(payload, Mapping):
            return _safe_mapping(payload)
    return {}


def _candidate_payload(trace: Mapping[str, Any]) -> dict[str, Any]:
    packet = trace.get(OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY)
    if isinstance(packet, Mapping):
        payload = packet.get("OfficialSourceCandidateVisibility")
        if isinstance(payload, Mapping):
            return _safe_mapping(payload)
    return {}


def _survival_payload(trace: Mapping[str, Any]) -> dict[str, Any]:
    packet = trace.get(OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY)
    if isinstance(packet, Mapping):
        payload = packet.get("OfficialSourceSurvivalProjection")
        if isinstance(payload, Mapping):
            return _safe_mapping(payload)
    return {}


def _authority_candidate_passport_payload(trace: Mapping[str, Any]) -> dict[str, Any]:
    packet = trace.get(AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY)
    if isinstance(packet, Mapping):
        payload = packet.get("AuthorityCandidatePassportProjection")
        if isinstance(payload, Mapping):
            return _safe_mapping(payload)
    return {}


def _visibility_status(
    *,
    admission_considered: Any,
    source_class_eligible: Any,
    source_class_used: Any,
    recovered_result_count: Any,
) -> str:
    if any(
        value != UNKNOWN
        for value in (
            admission_considered,
            source_class_eligible,
            source_class_used,
            recovered_result_count,
        )
    ):
        return "visible"
    return NOT_OBSERVABLE


def _candidate_count(
    trace: Mapping[str, Any],
    candidate: Mapping[str, Any],
    recovered_class_counts: Mapping[str, int] | str,
    *,
    source_class_used: Any,
) -> int | str:
    source_fit_count = (
        _first_known_int(trace.get("recovered_visibility_source_fit_candidate_count"))
        if _source_fit_evaluated(trace)
        else UNKNOWN
    )
    direct = _first_known_int(
        source_fit_count,
        trace.get("candidate_official_or_canonical_count"),
        trace.get("candidate_official_source_count"),
        candidate.get("candidate_official_source_count"),
    )
    if direct != UNKNOWN:
        return direct
    if isinstance(recovered_class_counts, Mapping) and source_class_used is True:
        return sum(int(value or 0) for value in recovered_class_counts.values())
    return UNKNOWN


def _accepted_or_readable_count(
    trace: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    source_class_used: Any,
) -> int | str:
    selected_count = (
        _first_known_int(
            trace.get("recovered_visibility_source_fit_selected_count"),
            trace.get("recovered_visibility_reserved_count"),
        )
        if _source_fit_evaluated(trace)
        else UNKNOWN
    )
    direct = _first_known_int(
        selected_count,
        trace.get("accepted_or_readable_official_or_canonical_count"),
        trace.get("accepted_or_readable_official_source_count"),
        candidate.get("accepted_or_readable_official_source_count"),
    )
    if direct != UNKNOWN:
        return direct
    if source_class_used is True:
        return _first_known_int(trace.get("recovered_official_or_primary_count"))
    return UNKNOWN


def _candidate_count_basis(trace: Mapping[str, Any]) -> str:
    status = _optional_text(trace.get("recovered_visibility_source_fit_status"))
    if status in {"matched_selected", "matched_not_selected"}:
        return "authority_lifecycle_candidate_fit"
    if status in {"no_matching_source_fit", "rejected_with_reason"}:
        return "authority_lifecycle_rejected_candidate_fit"
    if _optional_text(trace.get("candidate_official_or_canonical_count")) != UNKNOWN:
        return "legacy_direct_candidate_count"
    if isinstance(trace.get("recovered_source_class_counts"), Mapping) or isinstance(
        trace.get("recovered_source_tier_counts"),
        Mapping,
    ):
        return "recovered_class_or_tier_counts"
    return UNKNOWN


def _returned_or_evaluated_candidate_count(
    trace: Mapping[str, Any],
    candidate_fit: Mapping[str, Any],
    candidate_official_or_canonical_count: Any,
) -> int | str:
    direct = _first_known_int(
        trace.get("recovered_visibility_returned_or_evaluated_candidate_count"),
        trace.get("authority_lifecycle_returned_or_evaluated_candidate_count"),
        candidate_fit.get("returned_or_evaluated_candidate_count"),
    )
    if direct != UNKNOWN:
        return direct
    lifecycle_count = _lifecycle_candidate_count(candidate_fit)
    if lifecycle_count != UNKNOWN:
        return lifecycle_count
    if candidate_official_or_canonical_count != UNKNOWN:
        return candidate_official_or_canonical_count
    return UNKNOWN


def _rejected_candidate_count(
    trace: Mapping[str, Any],
    candidate_fit: Mapping[str, Any],
) -> int | str:
    direct = _first_known_int(
        trace.get("recovered_visibility_rejected_candidate_count"),
        trace.get("authority_lifecycle_rejected_candidate_count"),
        candidate_fit.get("rejected_candidate_count"),
    )
    if direct != UNKNOWN:
        return direct
    structured = candidate_fit.get("structured_rejections")
    if isinstance(structured, list):
        return len(structured)
    reasons = _safe_list(
        trace.get("recovered_visibility_source_fit_rejection_reasons")
        or candidate_fit.get("rejection_reasons")
    )
    if isinstance(reasons, list):
        return len(reasons)
    return UNKNOWN


def _accepted_readable_authority_evidence_count(
    trace: Mapping[str, Any],
    candidate_fit: Mapping[str, Any],
    accepted_or_readable_count: Any,
) -> int | str:
    direct = _first_known_int(
        trace.get("recovered_visibility_accepted_readable_authority_evidence_count"),
        trace.get("authority_lifecycle_accepted_readable_authority_evidence_count"),
        candidate_fit.get("accepted_readable_authority_evidence_count"),
    )
    if direct != UNKNOWN:
        return direct
    lifecycle_selected = _lifecycle_selected_count(candidate_fit)
    if lifecycle_selected != UNKNOWN:
        return lifecycle_selected
    return accepted_or_readable_count


def _final_selected_authority_evidence_count(
    trace: Mapping[str, Any],
    candidate_fit: Mapping[str, Any],
) -> int | str:
    direct = _first_known_int(
        trace.get("recovered_visibility_final_selected_authority_evidence_count"),
        trace.get("authority_lifecycle_final_selected_authority_evidence_count"),
        candidate_fit.get("final_selected_authority_evidence_count"),
    )
    if direct != UNKNOWN:
        return direct
    if _citation_eligibility_state(trace) == "eligible":
        return _lifecycle_selected_count(candidate_fit)
    return UNKNOWN


def _citation_eligibility_state(trace: Mapping[str, Any]) -> str:
    authority = trace.get("authority_lifecycle")
    if isinstance(authority, Mapping):
        return _optional_text(authority.get("citation_eligibility_state"))
    return _optional_text(trace.get("citation_eligibility_state"))


def _source_fit_evaluated(trace: Mapping[str, Any]) -> bool:
    return _optional_text(trace.get("recovered_visibility_source_fit_status")) not in {
        UNKNOWN,
        "not_evaluated",
    }


def _authority_lifecycle_candidate_fit(trace: Mapping[str, Any]) -> dict[str, Any]:
    authority = trace.get("authority_lifecycle")
    if not isinstance(authority, Mapping):
        return {}
    candidate_fit = authority.get("candidate_fit")
    return _safe_mapping(candidate_fit) if isinstance(candidate_fit, Mapping) else {}


def _legacy_lifecycle_fit_state(candidate_fit: Mapping[str, Any]) -> str:
    state = _optional_text(candidate_fit.get("fit_state"))
    if state == "rejected_with_reason":
        return "no_matching_source_fit"
    return state


def _lifecycle_candidate_count(candidate_fit: Mapping[str, Any]) -> int | str:
    state = _optional_text(candidate_fit.get("fit_state"))
    if state == "not_evaluated":
        return UNKNOWN
    selected = _lifecycle_selected_count(candidate_fit)
    rejection_count = len(_lifecycle_rejection_reasons(candidate_fit))
    if isinstance(selected, int) and selected > 0:
        return selected
    if rejection_count > 0:
        return rejection_count
    if _optional_text(candidate_fit.get("candidate_return_status")) == (
        "candidates_returned"
    ):
        return 1
    return UNKNOWN


def _lifecycle_selected_count(candidate_fit: Mapping[str, Any]) -> int | str:
    selected_records = candidate_fit.get("selected_authority_evidence")
    if isinstance(selected_records, list):
        return len(selected_records)
    selected_ids = candidate_fit.get("selected_evidence_ids")
    if isinstance(selected_ids, list):
        return len(selected_ids)
    return UNKNOWN


def _lifecycle_rejection_reasons(candidate_fit: Mapping[str, Any]) -> list[str]:
    structured = candidate_fit.get("structured_rejections")
    reasons: list[str] = []
    if isinstance(structured, list):
        for rejection in structured:
            if isinstance(rejection, Mapping):
                reason = _clean_text(
                    rejection.get("rejection_reason"),
                    limit=_MAX_TEXT_CHARS,
                )
                if reason:
                    reasons.append(reason)
    if reasons:
        return _dedupe(reasons)
    legacy = candidate_fit.get("rejection_reasons")
    safe = _safe_list(legacy)
    return safe if isinstance(safe, list) else []


def _passport_field_values(
    authority_candidate_passport: Mapping[str, Any],
    field_name: str,
) -> list[str] | str:
    passports = authority_candidate_passport.get("passports")
    if not isinstance(passports, list):
        return UNKNOWN
    values: list[str] = []
    for passport in passports:
        if not isinstance(passport, Mapping):
            continue
        value = _optional_text(passport.get(field_name))
        if value != UNKNOWN:
            values.append(value)
    return _dedupe(values)


def _recovery_query_previews(
    trace: Mapping[str, Any],
    admission: Mapping[str, Any],
) -> list[str]:
    return _dedupe(
        [
            *_list_or_empty(
                _safe_list(
                    admission.get("recovery_query_previews"),
                    limit=_MAX_QUERY_PREVIEWS,
                    text_limit=_MAX_QUERY_CHARS,
                )
            ),
            *_list_or_empty(
                _safe_list(
                    trace.get("active_source_class_recovery_queries"),
                    limit=_MAX_QUERY_PREVIEWS,
                    text_limit=_MAX_QUERY_CHARS,
                )
            ),
            *_list_or_empty(
                _safe_list(
                    trace.get("source_class_recovery_queries"),
                    limit=_MAX_QUERY_PREVIEWS,
                    text_limit=_MAX_QUERY_CHARS,
                )
            ),
        ],
        limit=_MAX_QUERY_PREVIEWS,
    )


def _count_visibility_status(value: Any) -> str:
    if value == UNKNOWN:
        return NOT_OBSERVABLE
    if _positive_int(value):
        return "visible"
    if _is_zero(value):
        return "not_visible"
    return NOT_OBSERVABLE


def _candidate_return_status(
    *,
    execution_attempted: Any,
    recovered_result_count: Any,
    precomputed_status: Any = UNKNOWN,
) -> str:
    status = _optional_text(precomputed_status)
    if status != UNKNOWN:
        return status
    if execution_attempted is False:
        return "not_attempted"
    if execution_attempted != True:  # noqa: E712
        return UNKNOWN
    if recovered_result_count == UNKNOWN:
        return UNKNOWN
    if _is_zero(recovered_result_count):
        return "zero_candidates"
    if _positive_int(recovered_result_count):
        return "candidates_returned"
    return UNKNOWN


def _unknown_fields(export: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for key, value in export.items():
        if key in {
            "schema_version",
            "diagnostic_only",
            "sanitized",
            "behavior_changed",
            "unknown_fields",
        }:
            continue
        if isinstance(value, str) and value in {UNKNOWN, NOT_OBSERVABLE}:
            out.append(key)
    return out


def _looks_like_export(value: Mapping[str, Any] | None) -> bool:
    return isinstance(value, Mapping) and value.get("schema_version") == (
        OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_SCHEMA_VERSION
    )


def _nested(source: Mapping[str, Any], keys: Iterable[str]) -> Any:
    current: Any = source
    for key in keys:
        if not isinstance(current, Mapping):
            return UNKNOWN
        current = current.get(key, UNKNOWN)
    return current


def _bool_or_unknown(value: Any) -> bool | str:
    if isinstance(value, bool):
        return value
    return UNKNOWN


def _first_known_int(*values: Any) -> int | str:
    for value in values:
        parsed = _optional_int(value)
        if parsed != UNKNOWN:
            return parsed
    return UNKNOWN


def _optional_int(value: Any) -> int | str:
    if value is None or isinstance(value, bool) or value == UNKNOWN:
        return UNKNOWN
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return UNKNOWN


def _is_zero(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == 0


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, item in value.items():
        if _is_sensitive_key(key):
            continue
        out[str(key)] = _safe_value(item)
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=240)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:_MAX_LIST_ITEMS]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:_MAX_LIST_ITEMS]]
    return _clean_text(value, limit=240)


def _safe_list(
    value: Any,
    *,
    limit: int = _MAX_LIST_ITEMS,
    text_limit: int = _MAX_TEXT_CHARS,
) -> list[str] | str:
    if value == UNKNOWN:
        return UNKNOWN
    if value is None:
        return UNKNOWN
    if not isinstance(value, (list, tuple, set)):
        return UNKNOWN
    out: list[str] = []
    for item in value:
        clean = _clean_text(item, limit=text_limit)
        if clean:
            out.append(clean)
        if len(out) >= limit:
            break
    return _dedupe(out, limit=limit)


def _dedupe(values: Iterable[str], *, limit: int = _MAX_LIST_ITEMS) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = _clean_text(value, limit=_MAX_QUERY_CHARS)
        key = str(clean or "").casefold()
        if clean and key not in seen:
            out.append(clean)
            seen.add(key)
        if len(out) >= limit:
            break
    return out


def _safe_count_map(
    value: Any,
    *,
    allowed: frozenset[str],
) -> dict[str, int] | str:
    if value is None:
        return UNKNOWN
    if not isinstance(value, Mapping):
        return UNKNOWN
    out: dict[str, int] = {}
    for raw_key, raw_count in value.items():
        if _is_sensitive_key(raw_key):
            continue
        key = _clean_token(raw_key)
        if key and key in allowed:
            parsed = _optional_int(raw_count)
            if parsed != UNKNOWN:
                out[key] = parsed
    return dict(sorted(out.items()))


def _optional_text(value: Any) -> str:
    if value is None:
        return UNKNOWN
    text = _clean_text(value, limit=_MAX_TEXT_CHARS)
    return text or UNKNOWN


def _optional_text_field(source: Mapping[str, Any], key: str) -> str:
    if key in source and source.get(key) is None:
        return "none"
    return _optional_text(source.get(key))


def _list_or_empty(value: list[str] | str) -> list[str]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    for pattern in _SECRET_VALUE_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text[:limit]


def _clean_token(value: Any) -> str:
    return _clean_text(value, limit=80).casefold().replace("-", "_").replace(" ", "_")


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or any(
        marker in normalized for marker in _SENSITIVE_KEY_MARKERS
    )


def _format_value(value: Any) -> str:
    if value is None:
        return UNKNOWN
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        if not value:
            return "{}"
        return ", ".join(f"{key}={value[key]}" for key in sorted(value))
    if isinstance(value, list):
        if not value:
            return "[]"
        return "; ".join(str(item) for item in value)
    return _clean_text(value, limit=_MAX_TEXT_CHARS) or UNKNOWN


__all__ = [
    "NOT_OBSERVABLE",
    "OFFICIAL_CANONICAL_RECOVERY_DIAGNOSTICS_TITLE",
    "OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_SCHEMA_VERSION",
    "OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY",
    "UNKNOWN",
    "append_official_canonical_recovery_diagnostics_section",
    "build_official_canonical_recovery_visibility_export",
    "build_official_canonical_recovery_visibility_trace",
    "classify_ag50d_next_failure_layer",
    "classify_likely_next_failure_layer",
    "format_official_canonical_recovery_diagnostics_markdown",
]
