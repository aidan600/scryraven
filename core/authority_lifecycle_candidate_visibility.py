"""AuthorityLifecycle candidate-fit and recovered-evidence visibility.

This module is pure post-execution controller lifecycle logic. It consumes
already-returned recovered candidates and existing sanitized visibility facts;
it does not retrieve, route providers, rank/filter sources, build prompts,
cite sources, or alter final-answer behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse, urlunparse

from core.source_class_recovery import _evidence_source_class_strengths

AUTHORITY_LIFECYCLE_CANDIDATE_VISIBILITY_SCHEMA_VERSION = (
    "authority_lifecycle_candidate_visibility_ag69d_v1"
)

_OWNER = "controller/lifecycle"
_LOWER_TIER_REJECTION_REASONS = frozenset(
    {
        "already_visible_duplicate_lower_tier_context",
        "already_visible_not_authority_satisfying",
        "duplicate_visible_lower_tier_context_source",
        "duplicate_visible_not_authority_satisfying",
        "secondary_only",
        "source_class_mismatch",
        "not_strong_source_class",
        "context_allowed_but_not_authority_satisfying",
    }
)


def project_authority_lifecycle_candidate_fit_visibility(
    *,
    lifecycle_trace: Mapping[str, Any] | None,
    final_top_evidence: Iterable[Mapping[str, Any]],
    recovered_passages: Iterable[Mapping[str, Any]],
    visibility_decision: Mapping[str, Any],
) -> dict[str, Any]:
    """Record candidate fit/visibility on AuthorityLifecycle and project legacy fields."""

    if not isinstance(lifecycle_trace, dict):
        return {}
    authority = lifecycle_trace.get("authority_lifecycle")
    if not isinstance(authority, dict):
        return {}

    recovered = [
        dict(source) for source in recovered_passages or () if isinstance(source, Mapping)
    ]
    final = [
        dict(source) for source in final_top_evidence or () if isinstance(source, Mapping)
    ]
    decision = dict(visibility_decision or {})
    execution = _mapping(authority.get("execution_state"))
    execution_attempted = execution.get("state") == "attempted"
    if authority:
        recovered_result_count = _first_int(
            execution.get("recovered_result_count"),
            execution.get("result_count"),
        )
        accepted_url_count = _first_int(execution.get("accepted_url_count"))
    else:
        recovered_result_count = _first_int(
            lifecycle_trace.get("active_source_class_recovery_result_count"),
            lifecycle_trace.get("recovered_result_count"),
            execution.get("recovered_result_count"),
            execution.get("result_count"),
        )
        accepted_url_count = _first_int(
            lifecycle_trace.get("recovered_accepted_url_count"),
            lifecycle_trace.get("accepted_url_count"),
            execution.get("accepted_url_count"),
            decision.get("recovered_visibility_source_fit_selected_count"),
        )
    returned = bool(
        recovered
        or recovered_result_count > 0
        or accepted_url_count > 0
        or _positive_int(decision.get("recovered_visibility_source_fit_candidate_count"))
    )

    candidate_return_status = _candidate_return_status(
        execution_attempted=execution_attempted,
        returned=returned,
        recovered_result_count=recovered_result_count,
    )
    fit_state = _candidate_fit_state(
        decision=decision,
        returned=returned,
        accepted_url_count=accepted_url_count,
    )
    selected_records = _selected_records(
        authority=authority,
        decision=decision,
        final_top_evidence=final,
    )
    rejections = _structured_rejections(
        authority=authority,
        recovered_passages=recovered,
        decision=decision,
        fit_state=fit_state,
        returned=returned,
        accepted_url_count=accepted_url_count,
    )
    selected_ids = tuple(
        str(record.get("evidence_id") or "")
        for record in selected_records
        if record.get("evidence_id")
    )
    rejection_reasons = tuple(
        str(rejection.get("rejection_reason") or "")
        for rejection in rejections
        if rejection.get("rejection_reason")
    )

    authority["candidate_acquisition_state"] = _candidate_acquisition_state(
        lifecycle_trace=lifecycle_trace,
        execution_attempted=execution_attempted,
        returned=returned,
        recovered_result_count=recovered_result_count,
    )
    authority["candidate_return_status"] = candidate_return_status
    authority["candidate_fit"] = {
        **_mapping(authority.get("candidate_fit")),
        "candidate_return_status": candidate_return_status,
        "accepted_url_count": accepted_url_count,
        "fit_state": fit_state,
        "structured_rejections": rejections,
        "rejection_reasons": list(rejection_reasons),
        "selected_evidence_ids": list(selected_ids),
        "selected_authority_evidence": selected_records,
    }

    final_state, final_explanation = _final_evidence_state(
        authority=authority,
        decision=decision,
        returned=returned,
        selected_records=selected_records,
        rejection_reasons=rejection_reasons,
    )
    authority["final_evidence_state"] = final_state
    authority["final_evidence_explanation"] = final_explanation
    authority["citation_eligibility_state"] = (
        "eligible" if final_state == "visible" else "explained_ineligible"
        if final_state == "explained_absent"
        else "ineligible"
    )
    if selected_records:
        authority["satisfaction_state"] = "satisfied"
    elif returned and fit_state in {"rejected_with_reason", "no_matching_source_fit"}:
        authority["satisfaction_state"] = "partial"
    authority["final_posture"] = (
        "action_executed"
        if execution_attempted
        else authority.get("final_posture", "open")
    )
    authority["terminal_paths"] = (
        ["approved_action_executed"]
        if execution_attempted
        else list(authority.get("terminal_paths") or [])
    )

    projection = _legacy_projection(
        candidate_return_status=candidate_return_status,
        fit_state=fit_state,
        selected_records=selected_records,
        rejections=rejections,
        rejection_reasons=rejection_reasons,
        decision=decision,
        final_state=final_state,
        final_explanation=final_explanation,
    )
    lifecycle_trace.update(projection)
    lifecycle_trace["authority_lifecycle"] = authority
    return projection


def _candidate_return_status(
    *,
    execution_attempted: bool,
    returned: bool,
    recovered_result_count: int,
) -> str:
    if not execution_attempted:
        return "not_attempted"
    if returned:
        return "candidates_returned"
    if recovered_result_count == 0:
        return "no_candidates"
    return "candidate_return_unknown"


def _candidate_fit_state(
    *,
    decision: Mapping[str, Any],
    returned: bool,
    accepted_url_count: int,
) -> str:
    status = _text(decision.get("recovered_visibility_source_fit_status"))
    selected_count = _non_negative_int(
        decision.get("recovered_visibility_source_fit_selected_count")
    )
    candidate_count = _non_negative_int(
        decision.get("recovered_visibility_source_fit_candidate_count")
    )
    if status == "matched_selected" and selected_count > 0:
        return "matched_selected"
    if status == "matched_not_selected":
        return "matched_not_selected"
    if returned or accepted_url_count > 0 or candidate_count > 0:
        if status == "no_matching_source_fit":
            return "rejected_with_reason"
        if status in {"not_evaluated", "no_candidates", ""}:
            return "rejected_with_reason"
        return status
    if status == "no_candidates":
        return "no_matching_source_fit"
    return "not_evaluated"


def _selected_records(
    *,
    authority: Mapping[str, Any],
    decision: Mapping[str, Any],
    final_top_evidence: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    selected = {
        _identity_key(item)
        for item in decision.get("recovered_visibility_reserved_source_ids") or []
        if _identity_key(item)
    }
    if not selected:
        return []
    records: list[dict[str, Any]] = []
    for source in final_top_evidence:
        identity = _source_identity(source)
        if _identity_key(identity) not in selected and not (
            _identity_key(source.get("url")) in selected
        ):
            continue
        observed = _observed_source_class(source)
        evidence_id = identity or _text(source.get("url")) or _text(source.get("title"))
        records.append(
            {
                "requirement_id": _requirement_id(authority),
                "evidence_id": evidence_id,
                "url": _text(source.get("url")),
                "required_authority": _required_authority(authority),
                "observed_source_class": observed,
                "satisfies_authority": True,
            }
        )
    return records


def _structured_rejections(
    *,
    authority: Mapping[str, Any],
    recovered_passages: list[Mapping[str, Any]],
    decision: Mapping[str, Any],
    fit_state: str,
    returned: bool,
    accepted_url_count: int,
) -> list[dict[str, Any]]:
    if fit_state != "rejected_with_reason":
        return []
    reason = _rejection_reason(decision, returned=returned, accepted_url_count=accepted_url_count)
    candidates = recovered_passages or [
        {
            "source_id": "accepted-url-without-readable-candidate",
            "url": None,
        }
    ]
    rejections: list[dict[str, Any]] = []
    for source in candidates:
        identity = _source_identity(source) or "accepted-url-without-readable-candidate"
        observed = _observed_source_class(source)
        rejections.append(
            {
                "requirement_id": _requirement_id(authority),
                "candidate_id": identity,
                "url": _text(source.get("url")),
                "required_authority": _required_authority(authority),
                "observed_source_class": observed,
                "rejection_reason": reason,
                "rejection_owner": _OWNER,
                "lower_tier_context_allowed": reason in _LOWER_TIER_REJECTION_REASONS,
                "final_evidence_must_be_explained_absent": True,
            }
        )
    return rejections


def _final_evidence_state(
    *,
    authority: Mapping[str, Any],
    decision: Mapping[str, Any],
    returned: bool,
    selected_records: list[Mapping[str, Any]],
    rejection_reasons: tuple[str, ...],
) -> tuple[str, str | None]:
    if selected_records and decision.get("recovered_visibility_used") is True:
        return "visible", None
    if returned:
        reason = rejection_reasons[0] if rejection_reasons else _rejection_reason(
            decision,
            returned=returned,
            accepted_url_count=0,
        )
        return (
            "explained_absent",
            (
                f"requirement {_requirement_id(authority)}: recovered candidates "
                f"did not become final authority evidence because {reason}"
            ),
        )
    return "not_visible", None


def _legacy_projection(
    *,
    candidate_return_status: str,
    fit_state: str,
    selected_records: list[Mapping[str, Any]],
    rejections: list[Mapping[str, Any]],
    rejection_reasons: tuple[str, ...],
    decision: Mapping[str, Any],
    final_state: str,
    final_explanation: str | None,
) -> dict[str, Any]:
    legacy_fit_state = (
        "no_matching_source_fit" if fit_state == "rejected_with_reason" else fit_state
    )
    selected_count = len(selected_records)
    candidate_count = _non_negative_int(
        decision.get("recovered_visibility_source_fit_candidate_count")
    )
    if fit_state in {"matched_selected", "matched_not_selected"}:
        candidate_count = max(candidate_count, selected_count, 1)
    elif fit_state == "rejected_with_reason":
        candidate_count = max(candidate_count, 1)
    rejected_count = len(rejections)
    return {
        "authority_lifecycle_candidate_visibility_schema_version": (
            AUTHORITY_LIFECYCLE_CANDIDATE_VISIBILITY_SCHEMA_VERSION
        ),
        "authority_lifecycle_candidate_return_status": candidate_return_status,
        "authority_lifecycle_candidate_fit_state": fit_state,
        "authority_lifecycle_returned_or_evaluated_candidate_count": (
            candidate_count
        ),
        "authority_lifecycle_rejected_candidate_count": rejected_count,
        "authority_lifecycle_accepted_readable_authority_evidence_count": (
            selected_count
        ),
        "authority_lifecycle_final_selected_authority_evidence_count": (
            selected_count if final_state == "visible" else 0
        ),
        "authority_lifecycle_selected_authority_evidence": [
            dict(record) for record in selected_records
        ],
        "authority_lifecycle_candidate_rejections": [
            dict(rejection) for rejection in rejections
        ],
        "authority_lifecycle_final_evidence_state": final_state,
        "authority_lifecycle_final_evidence_explanation": final_explanation,
        "recovered_visibility_source_fit_status": legacy_fit_state,
        "recovered_visibility_source_fit_candidate_count": candidate_count,
        "recovered_visibility_source_fit_selected_count": selected_count,
        "recovered_visibility_returned_or_evaluated_candidate_count": (
            candidate_count
        ),
        "recovered_visibility_rejected_candidate_count": rejected_count,
        "recovered_visibility_accepted_readable_authority_evidence_count": (
            selected_count
        ),
        "recovered_visibility_final_selected_authority_evidence_count": (
            selected_count if final_state == "visible" else 0
        ),
        "recovered_visibility_source_fit_rejection_reasons": list(rejection_reasons),
    }


def _candidate_acquisition_state(
    *,
    lifecycle_trace: Mapping[str, Any],
    execution_attempted: bool,
    returned: bool,
    recovered_result_count: int,
) -> str:
    existing = _text(
        _mapping(lifecycle_trace.get("authority_lifecycle")).get(
            "candidate_acquisition_state"
        )
    )
    if existing == "provider_results_returned":
        return existing
    if lifecycle_trace.get("candidate_acquisition_result_status") == (
        "provider_results_returned"
    ):
        return "provider_results_returned"
    if returned:
        return "provider_results_returned"
    if execution_attempted and recovered_result_count == 0:
        return "no_results"
    if execution_attempted:
        return "attempted"
    return existing or "not_attempted"


def _rejection_reason(
    decision: Mapping[str, Any],
    *,
    returned: bool,
    accepted_url_count: int,
) -> str:
    for key in (
        "recovered_visibility_drop_reason",
        "recovered_visibility_reason",
    ):
        value = _text(decision.get(key))
        if value and value != "none":
            return value
    reasons = decision.get("recovered_visibility_source_fit_rejection_reasons")
    if isinstance(reasons, (list, tuple)) and reasons:
        value = _text(reasons[0])
        if value:
            return value
    if accepted_url_count > 0 and not returned:
        return "accepted_url_without_readable_candidate_data"
    return "returned_candidate_did_not_satisfy_required_authority"


def _observed_source_class(source: Mapping[str, Any]) -> str | None:
    signals = _evidence_source_class_strengths(source)
    for strength in ("strong", "weak", "secondary_only"):
        for source_class, class_signals in signals.items():
            if class_signals.get(strength):
                return source_class
    for key in ("source_class", "source_class_bucket", "source_tier"):
        value = _text(source.get(key))
        if value:
            return value.casefold().replace("-", "_").replace(" ", "_")
    return None


def _source_identity(source: Mapping[str, Any]) -> str:
    for key in ("source_id", "url", "title"):
        value = _text(source.get(key))
        if value:
            return value
    return ""


def _identity_key(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return text.casefold().rstrip("/")
    path = (parsed.path or "").rstrip("/")
    return urlunparse(("https", host, path, "", parsed.query, "")).casefold()


def _requirement_id(authority: Mapping[str, Any]) -> str:
    return _text(authority.get("requirement_id")) or "authority_requirement"


def _required_authority(authority: Mapping[str, Any]) -> str:
    return _text(authority.get("required_authority")) or "required_authority"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    return text or None


def _first_int(*values: Any) -> int:
    for value in values:
        parsed = _optional_int(value)
        if parsed is not None:
            return parsed
    return 0


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool) or value == "unknown":
        return None
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return None


def _non_negative_int(value: Any) -> int:
    parsed = _optional_int(value)
    return 0 if parsed is None else parsed


def _positive_int(value: Any) -> bool:
    parsed = _optional_int(value)
    return parsed is not None and parsed > 0


__all__ = [
    "AUTHORITY_LIFECYCLE_CANDIDATE_VISIBILITY_SCHEMA_VERSION",
    "project_authority_lifecycle_candidate_fit_visibility",
]
