"""Dogfood-only conformance checks for Author prose finalization.

The helper is deterministic and offline. It checks that prose stayed inside the
hardened FAP posture without becoming a second production authority.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from core.author_prose_finalization_runtime import (
    AUTHOR_PROSE_OWNER,
    FAP_TO_AUTHOR_PROSE_STATUS,
)
from core.author_prose_policy import (
    AuthorProsePolicy,
    author_prose_policy_digest,
    author_prose_policy_ref,
    normalize_author_prose_policy,
)

AUTHOR_PROSE_CONFORMANCE_SCHEMA_VERSION = (
    "author_prose_conformance_review_author_prose_only_finalization_01_v1"
)
AUTHOR_PROSE_CONFORMANCE_OWNER = "Dogfood.AuthorProseConformanceReview"

_CLOSED_FLAG_KEYS = {
    "author_prose_is_product_correctness",
    "citation_eligible",
    "citations_rendered",
    "source_obligation_satisfied",
    "product_correctness_claimed",
    "model_called",
    "provider_called",
    "live_provider_called",
    "search_executed",
    "retrieval_executed",
    "fetch_read_executed",
    "old_author_runtime_called",
    "pipeline_orchestrator_called",
    "followup_authorized_by_author_prose",
    "remediation_completed_claimed",
}


class AuthorProseConformanceReviewError(ValueError):
    """Raised when conformance review inputs are unusable."""


def review_author_prose_conformance(
    *,
    fap_projection: Mapping[str, Any],
    author_prose_projection: Mapping[str, Any],
    policy: AuthorProsePolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Review Author prose projection against hardened FAP projection."""

    fap = _safe_mapping(fap_projection)
    prose = _safe_mapping(author_prose_projection)
    normalized_policy = normalize_author_prose_policy(
        policy or prose.get("policy_ref"),
        mode=prose.get("mode") or fap.get("mode") or "Balanced",
    )
    issue_codes: list[str] = []
    if not fap or fap.get("owner") != "RunKernel.FinalAnswerPacket":
        issue_codes.append("missing_or_invalid_fap_projection")
    if not prose or prose.get("owner") != AUTHOR_PROSE_OWNER:
        issue_codes.append("missing_or_invalid_author_prose_projection")

    fap_status = _normalized_token(fap.get("fap_status"))
    expected_prose_status = FAP_TO_AUTHOR_PROSE_STATUS.get(fap_status)
    if not expected_prose_status:
        issue_codes.append("unsupported_fap_status")
    elif prose.get("author_prose_status") != expected_prose_status:
        issue_codes.append("fap_to_prose_status_mismatch")
    if prose.get("fap_status") != fap_status:
        issue_codes.append("fap_status_not_preserved")

    _check_partial_implication(
        fap_status=fap_status,
        prose=prose,
        issue_codes=issue_codes,
    )
    _check_component_treatments(
        fap=fap,
        prose=prose,
        issue_codes=issue_codes,
    )
    _check_required_caveats(
        fap=fap,
        prose=prose,
        issue_codes=issue_codes,
    )
    _check_contested_followup_posture(
        fap_status=fap_status,
        prose=prose,
        issue_codes=issue_codes,
    )
    _check_closed_downstream_flags(prose, issue_codes)
    _check_prohibited_claim_lists(fap, prose, issue_codes)

    issue_codes = _dedupe_text(issue_codes)
    if not issue_codes:
        review_status = "conformance_passed"
    elif any(code.startswith("missing_or_invalid") for code in issue_codes):
        review_status = "blocked_for_review"
    else:
        review_status = "laundering_suspected"
    record = {
        "schema_version": AUTHOR_PROSE_CONFORMANCE_SCHEMA_VERSION,
        "record_kind": "author_prose_conformance_review",
        "owner": AUTHOR_PROSE_CONFORMANCE_OWNER,
        "dogfood_only": True,
        "production_blocking": False,
        "review_status": review_status,
        "issue_codes": issue_codes,
        "issue_count": len(issue_codes),
        "fap_status": fap.get("fap_status"),
        "author_prose_status": prose.get("author_prose_status"),
        "fap_ref": _fap_ref(fap),
        "author_prose_ref": _author_prose_ref(prose),
        "policy_ref": author_prose_policy_ref(normalized_policy),
        "policy_digest": author_prose_policy_digest(normalized_policy),
        "model_called": False,
        "provider_called": False,
        "live_provider_called": False,
        "search_executed": False,
        "retrieval_executed": False,
        "fetch_read_executed": False,
        "old_author_runtime_called": False,
        "pipeline_orchestrator_called": False,
        "citation_eligible": False,
        "citations_rendered": False,
        "source_obligation_satisfied": False,
        "product_correctness_claimed": False,
    }
    record["review_digest"] = _digest_json(
        {key: value for key, value in record.items() if key != "review_digest"}
    )
    return record


def _check_partial_implication(
    *,
    fap_status: str,
    prose: Mapping[str, Any],
    issue_codes: list[str],
) -> None:
    if fap_status != "full_answer_packet_ready" and prose.get(
        "full_answer_implication_allowed"
    ) is True:
        issue_codes.append("full_answer_implied_from_non_full_fap")
    if (
        fap_status == "partial_answer_packet_ready"
        and prose.get("author_prose_status") == "full_answer_prose_created"
    ):
        issue_codes.append("partial_fap_upgraded_to_full_prose")


def _check_component_treatments(
    *,
    fap: Mapping[str, Any],
    prose: Mapping[str, Any],
    issue_codes: list[str],
) -> None:
    fap_entries = {
        entry.get("component_id"): entry
        for entry in _safe_list(fap.get("component_packet_entries"))
        if _safe_mapping(entry).get("component_id")
    }
    prose_entries = {
        entry.get("component_id"): entry
        for entry in _safe_list(prose.get("component_prose_entries"))
        if _safe_mapping(entry).get("component_id")
    }
    for component_id, fap_entry in fap_entries.items():
        prose_entry = _safe_mapping(prose_entries.get(component_id))
        if fap_entry.get("must_not_answer") is True and (
            prose_entry.get("supported_in_prose") is True
            or prose_entry.get("prose_treatment") == "supported_component"
        ):
            issue_codes.append("must_not_answer_component_presented_as_supported")
        if fap_entry.get("supported_claim_allowed") is not True and prose_entry.get(
            "supported_in_prose"
        ) is True:
            issue_codes.append("unsupported_component_answered")


def _check_required_caveats(
    *,
    fap: Mapping[str, Any],
    prose: Mapping[str, Any],
    issue_codes: list[str],
) -> None:
    required = set(_text_list(fap.get("mandatory_caveats"), limit=800))
    observed = set(_text_list(prose.get("mandatory_caveats"), limit=800))
    missing = sorted(required - observed)
    if missing:
        issue_codes.append("required_caveats_omitted")


def _check_contested_followup_posture(
    *,
    fap_status: str,
    prose: Mapping[str, Any],
    issue_codes: list[str],
) -> None:
    if fap_status == "contested_answer_packet":
        if prose.get("contested_posture_preserved") is not True:
            issue_codes.append("contested_posture_not_preserved")
        if prose.get("supported_claims_created") is True:
            issue_codes.append("contested_claim_smoothed_into_supported_fact")
    if fap_status == "followup_required_packet":
        if prose.get("followup_authorized_by_author_prose") is True:
            issue_codes.append("followup_required_prose_authorized_followup")
        if prose.get("remediation_completed_claimed") is True:
            issue_codes.append("followup_required_prose_claimed_remediation_complete")


def _check_closed_downstream_flags(
    prose: Mapping[str, Any],
    issue_codes: list[str],
) -> None:
    for key in sorted(_CLOSED_FLAG_KEYS):
        if prose.get(key) is True:
            issue_codes.append(f"closed_flag_opened:{key}")
    flags = _safe_mapping(prose.get("closed_surface_flags"))
    for key, value in flags.items():
        if value is True:
            issue_codes.append(f"closed_surface_flags_opened:{key}")


def _check_prohibited_claim_lists(
    fap: Mapping[str, Any],
    prose: Mapping[str, Any],
    issue_codes: list[str],
) -> None:
    fap_claims = set(_text_list(fap.get("author_prohibited_claims"), limit=800))
    prose_claims = set(_text_list(prose.get("prohibited_claims"), limit=800))
    if fap_claims and not fap_claims.issubset(prose_claims):
        issue_codes.append("prohibited_claims_not_preserved")
    fap_upgrades = set(_text_list(fap.get("prohibited_upgrades"), limit=800))
    prose_upgrades = set(_text_list(prose.get("prohibited_upgrades"), limit=800))
    if fap_upgrades and not fap_upgrades.issubset(prose_upgrades):
        issue_codes.append("prohibited_upgrades_not_preserved")


def _fap_ref(fap: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "fap_status": fap.get("fap_status"),
            "packet_created": fap.get("packet_created"),
            "packet_id": fap.get("packet_id"),
            "packet_digest": fap.get("packet_digest"),
            "no_packet_record_digest": fap.get("no_packet_record_digest"),
            "final_answer_authority_projection_digest": _digest_json(fap),
        }
    )


def _author_prose_ref(prose: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "author_prose_id": prose.get("author_prose_id"),
            "author_prose_digest": prose.get("author_prose_digest"),
            "author_prose_status": prose.get("author_prose_status"),
            "fap_status": prose.get("fap_status"),
            "policy_digest": prose.get("policy_digest"),
        }
    )


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return []
    return [_safe_mapping(item) for item in value if _safe_mapping(item)]


def _text_list(value: Any, *, limit: int = 260) -> list[str]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return [text] if text else []
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _dedupe_text(values: Sequence[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_text(item, limit=260)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalized_token(value: Any) -> str:
    text = _clean_text(value, limit=180) or ""
    return text.casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "AUTHOR_PROSE_CONFORMANCE_OWNER",
    "AUTHOR_PROSE_CONFORMANCE_SCHEMA_VERSION",
    "AuthorProseConformanceReviewError",
    "review_author_prose_conformance",
]
