"""AG-73C bounded validation classifier for authority candidate passports.

This module reads the sanitized AG-73B passport export surface only. It does
not retrieve, route, classify, fit, preserve, cite, prompt, or alter runtime
answer behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

AG73C_VALIDATION_SCHEMA_VERSION = "authority_candidate_passport_validation_ag73c_v1"

INCONCLUSIVE_LIVE_BOUNDARY = (
    "inconclusive because candidate passports still do not cover the live boundary"
)
UNOBSERVABLE_PROVIDER_TO_REPRESENTED_CANDIDATE_BOUNDARY = (
    "provider-result to represented authority candidate; offline repo-visible "
    "evidence has aggregate result counts but no sanitized per-candidate live "
    "IRS passport"
)

_PROMOTED_LAYER = "promoted/citation-eligible authority evidence"
_NO_FAILURE = "no represented candidate failure"

_CLASSIFICATION_BY_STAGE = {
    "readability": "plausible official IRS candidate acquired but unreadable",
    "source_class_classification": "readable official-looking candidate misclassified",
    "source_class_or_tier": "readable official-looking candidate misclassified",
    "candidate_fit_currentness": (
        "classified official/current candidate rejected by fit/currentness"
    ),
    "controller_answer_contract": (
        "accepted/readable candidate lost before Controller/AnswerContract"
    ),
    "final_evidence_selection": (
        "Controller/AnswerContract saw it but failed to preserve/export it"
    ),
    "context_packet": "context packet failed to expose it",
    "analyst_author_citation_surface": "Analyst/Author/citation-surface failure",
}

_DECISION_USEFULNESS_BY_CLASSIFICATION = {
    "plausible official IRS candidate acquired but unreadable": (
        "a specific AG-73D/AG-74/AG-75 repair phase"
    ),
    "readable official-looking candidate misclassified": (
        "a specific AG-73D/AG-74/AG-75 repair phase"
    ),
    "classified official/current candidate rejected by fit/currentness": (
        "a specific AG-73D/AG-74/AG-75 repair phase"
    ),
    "accepted/readable candidate lost before Controller/AnswerContract": (
        "a specific AG-73D/AG-74/AG-75 repair phase"
    ),
    "Controller/AnswerContract saw it but failed to preserve/export it": (
        "a specific AG-73D/AG-74/AG-75 repair phase"
    ),
    "context packet failed to expose it": (
        "a specific AG-73D/AG-74/AG-75 repair phase"
    ),
    "Analyst/Author/citation-surface failure": (
        "a specific AG-73D/AG-74/AG-75 repair phase"
    ),
}


def classify_authority_candidate_passport_export(
    export: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify the first represented authority-candidate failure layer."""

    projection = _passport_projection(export)
    passports = projection.get("passports") if projection else None
    if not isinstance(passports, list) or not passports:
        return _result(
            classification=INCONCLUSIVE_LIVE_BOUNDARY,
            represented_candidate_layer="not observable",
            first_missing_stage=None,
            final_disposition=None,
            matched_candidate_id=None,
            unobservable_boundary=(
                UNOBSERVABLE_PROVIDER_TO_REPRESENTED_CANDIDATE_BOUNDARY
            ),
            decision_usefulness=(
                "narrow provider-result-to-represented-candidate visibility bridge"
            ),
        )

    promoted: dict[str, Any] | None = None
    for passport in passports:
        if not isinstance(passport, Mapping):
            continue
        classified = _classification_for_passport(passport)
        if classified["classification"] != _NO_FAILURE:
            return classified
        if promoted is None:
            promoted = classified

    if promoted is not None:
        return promoted

    return _result(
        classification=INCONCLUSIVE_LIVE_BOUNDARY,
        represented_candidate_layer="passport present but not classifiable",
        first_missing_stage=None,
        final_disposition=None,
        matched_candidate_id=None,
        unobservable_boundary="passport export contained no mapping-compatible record",
        decision_usefulness=(
            "narrow provider-result-to-represented-candidate visibility bridge"
        ),
    )


def _classification_for_passport(passport: Mapping[str, Any]) -> dict[str, Any]:
    final_disposition = _text(passport.get("final_disposition"))
    first_missing_stage = _text(passport.get("first_missing_stage"))
    candidate_id = _text(passport.get("candidate_id")) or None

    if final_disposition == "promoted_final_authority_evidence":
        return _result(
            classification=_NO_FAILURE,
            represented_candidate_layer=_PROMOTED_LAYER,
            first_missing_stage=None,
            final_disposition=final_disposition,
            matched_candidate_id=candidate_id,
            unobservable_boundary=None,
            decision_usefulness="no further offline validation needed",
        )

    classification = _CLASSIFICATION_BY_STAGE.get(first_missing_stage)
    if classification is None:
        classification = INCONCLUSIVE_LIVE_BOUNDARY
        unobservable_boundary = (
            "represented passport stage is outside the AG-73C decision map: "
            + (first_missing_stage or "missing")
        )
        decision_usefulness = (
            "narrow provider-result-to-represented-candidate visibility bridge"
        )
    else:
        unobservable_boundary = None
        decision_usefulness = _DECISION_USEFULNESS_BY_CLASSIFICATION[
            classification
        ]

    return _result(
        classification=classification,
        represented_candidate_layer=classification,
        first_missing_stage=first_missing_stage or None,
        final_disposition=final_disposition or None,
        matched_candidate_id=candidate_id,
        unobservable_boundary=unobservable_boundary,
        decision_usefulness=decision_usefulness,
    )


def _passport_projection(export: Mapping[str, Any]) -> Mapping[str, Any] | None:
    projection = export.get("authority_candidate_passport_projection")
    if isinstance(projection, Mapping):
        return projection
    return None


def _result(
    *,
    classification: str,
    represented_candidate_layer: str,
    first_missing_stage: str | None,
    final_disposition: str | None,
    matched_candidate_id: str | None,
    unobservable_boundary: str | None,
    decision_usefulness: str,
) -> dict[str, Any]:
    return {
        "schema_version": AG73C_VALIDATION_SCHEMA_VERSION,
        "diagnostic_only": True,
        "sanitized": True,
        "behavior_changed": False,
        "classification": classification,
        "represented_candidate_layer": represented_candidate_layer,
        "first_missing_stage": first_missing_stage,
        "final_disposition": final_disposition,
        "matched_candidate_id": matched_candidate_id,
        "unobservable_boundary": unobservable_boundary,
        "decision_usefulness": decision_usefulness,
    }


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


__all__ = [
    "AG73C_VALIDATION_SCHEMA_VERSION",
    "INCONCLUSIVE_LIVE_BOUNDARY",
    "UNOBSERVABLE_PROVIDER_TO_REPRESENTED_CANDIDATE_BOUNDARY",
    "classify_authority_candidate_passport_export",
]
