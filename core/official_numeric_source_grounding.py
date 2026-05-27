"""Pure AG-48A diagnostic classification for official numeric grounding.

This module is offline-only. It consumes sanitized booleans supplied by tests or
review packets and returns a diagnostic label. It does not inspect traces, call
providers, alter prompts, or participate in runtime control flow.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from core.authoritative_source_obligations import (
    SOURCED_NUMERIC_VALUES,
    AuthoritativeSourceObligationState,
    AuthorityEvidenceFit,
    AuthorityRequirement,
    AuthorityStatus,
)

SCHEMA_VERSION = "official_numeric_source_grounding_ag48a_v1"

SOURCE_NEED_NOT_DETECTED = "source_need_not_detected"
OFFICIAL_SOURCE_NOT_REQUIRED = "official_current_source_not_required"
OFFICIAL_SOURCE_NOT_ACQUIRED = "official_current_source_not_acquired"
OFFICIAL_SOURCE_ACQUIRED_NOT_ACCEPTED = "official_current_source_acquired_not_accepted"
OFFICIAL_SOURCE_NOT_IN_FINAL_EVIDENCE = (
    "official_current_source_not_visible_in_final_evidence"
)
OFFICIAL_SOURCE_VISIBLE_NOT_CITED = "official_current_source_visible_not_cited"
WRONG_NUMBER_EXTRACTED = "correct_source_cited_wrong_number_extracted"
NUMERIC_VALUE_NOT_SOURCE_BOUND = "numeric_value_not_source_bound"
ECONOMIST_ELIGIBLE_NOT_INVOKED = "economist_eligible_not_invoked"
ECONOMIST_INVOKED_WEAK_EVIDENCE = "economist_invoked_with_weak_or_wrong_evidence"
ECONOMIST_CORRECT_DISTORTED_DOWNSTREAM = (
    "economist_correct_but_ignored_or_distorted_downstream"
)
FINAL_SYNTHESIS_DISTORTION = "correct_number_extracted_but_distorted_final"
ANSWER_CAVEATED_MISSING_EVIDENCE = "answer_correctly_caveated_missing_evidence"
NO_BOTTLENECK_DETECTED = "no_official_numeric_grounding_bottleneck_detected"

SOURCE_ACQUISITION_SURVIVAL_LANE = "source_acquisition_survival_lane"
CITATION_SOURCE_FIT_LANE = "source_fit_citation_survival_lane"
NUMERIC_EXTRACTION_LANE = "numeric_extraction_source_bound_value_lane"
ECONOMIST_INVOCATION_LANE = "economist_invocation_preflight_lane"
ECONOMIST_HANDOFF_LANE = "economist_handoff_use_lane"
AUTHOR_SYNTHESIS_LANE = "author_synthesis_value_preservation_lane"
NO_ACTION_LANE = "no_action_caveat_behavior_acceptable"


@dataclass(frozen=True)
class OfficialNumericGroundingDiagnostic:
    """Sanitized inputs for classifying an official/current numeric failure."""

    question_type: str
    official_source_required: bool
    source_need_detected: bool = True
    official_source_acquired: bool = False
    official_source_accepted: bool | None = None
    official_source_in_final_evidence: bool = False
    official_source_cited: bool = False
    numeric_values_extracted: bool = False
    numeric_values_source_bound: bool = False
    economist_eligible: bool = False
    economist_ran: bool = False
    economist_source_bound_values_present: bool = False
    final_answer_value_mismatch: bool = False
    caveat_present: bool = False

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> "OfficialNumericGroundingDiagnostic":
        """Build a diagnostic input from a sanitized mapping."""
        return cls(
            question_type=str(payload.get("question_type") or "unspecified"),
            official_source_required=bool(payload.get("official_source_required")),
            source_need_detected=bool(payload.get("source_need_detected", True)),
            official_source_acquired=bool(payload.get("official_source_acquired")),
            official_source_accepted=(
                None
                if "official_source_accepted" not in payload
                else bool(payload.get("official_source_accepted"))
            ),
            official_source_in_final_evidence=bool(
                payload.get("official_source_in_final_evidence")
            ),
            official_source_cited=bool(payload.get("official_source_cited")),
            numeric_values_extracted=bool(payload.get("numeric_values_extracted")),
            numeric_values_source_bound=bool(
                payload.get("numeric_values_source_bound")
            ),
            economist_eligible=bool(payload.get("economist_eligible")),
            economist_ran=bool(payload.get("economist_ran")),
            economist_source_bound_values_present=bool(
                payload.get("economist_source_bound_values_present")
            ),
            final_answer_value_mismatch=bool(
                payload.get("final_answer_value_mismatch")
            ),
            caveat_present=bool(payload.get("caveat_present")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfficialNumericGroundingClassification:
    """Diagnostic output. ``behavior_changed`` must remain false."""

    schema_version: str
    bottleneck_class: str
    next_recommended_lane: str
    confidence: str
    rationale: tuple[str, ...] = field(default_factory=tuple)
    behavior_changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_official_numeric_grounding(
    diagnostic: OfficialNumericGroundingDiagnostic | Mapping[str, Any],
) -> OfficialNumericGroundingClassification:
    """Classify the earliest material sanitized failure layer."""
    facts = (
        OfficialNumericGroundingDiagnostic.from_mapping(diagnostic)
        if isinstance(diagnostic, Mapping)
        else diagnostic
    )
    accepted = (
        facts.official_source_acquired
        if facts.official_source_accepted is None
        else facts.official_source_accepted
    )

    if not facts.official_source_required:
        return _result(
            OFFICIAL_SOURCE_NOT_REQUIRED,
            NO_ACTION_LANE,
            "high",
            "official/current source not required for this question type",
            f"question_type={facts.question_type}",
        )

    if not facts.source_need_detected:
        return _result(
            SOURCE_NEED_NOT_DETECTED,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            "high",
            "official/current source was required but the need was not detected",
        )

    if not facts.official_source_acquired:
        if facts.caveat_present and not facts.final_answer_value_mismatch:
            return _result(
                ANSWER_CAVEATED_MISSING_EVIDENCE,
                SOURCE_ACQUISITION_SURVIVAL_LANE,
                "medium",
                "required source was missing and the answer caveated/refused unsupported values",
                "final posture may be acceptable, but completeness is blocked upstream",
            )
        return _result(
            OFFICIAL_SOURCE_NOT_ACQUIRED,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            "high",
            "official/current source was required but not acquired",
        )

    if not accepted:
        return _result(
            OFFICIAL_SOURCE_ACQUIRED_NOT_ACCEPTED,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            "high",
            "official/current source was acquired but not accepted as relevant evidence",
        )

    if not facts.official_source_in_final_evidence:
        return _result(
            OFFICIAL_SOURCE_NOT_IN_FINAL_EVIDENCE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            "high",
            "official/current source was accepted but did not survive into final evidence",
        )

    if not facts.official_source_cited:
        return _result(
            OFFICIAL_SOURCE_VISIBLE_NOT_CITED,
            CITATION_SOURCE_FIT_LANE,
            "high",
            "official/current source was visible in final evidence but not cited",
        )

    if facts.economist_eligible and not facts.economist_ran:
        return _result(
            ECONOMIST_ELIGIBLE_NOT_INVOKED,
            ECONOMIST_INVOCATION_LANE,
            "medium",
            "numeric-sensitive question was Economist-eligible but Economist did not run",
        )

    if facts.economist_ran and not facts.economist_source_bound_values_present:
        return _result(
            ECONOMIST_INVOKED_WEAK_EVIDENCE,
            ECONOMIST_HANDOFF_LANE,
            "medium",
            "Economist ran but did not produce sanitized source-bound values",
        )

    if not facts.numeric_values_extracted:
        return _result(
            WRONG_NUMBER_EXTRACTED,
            NUMERIC_EXTRACTION_LANE,
            "high",
            "correct source was cited but required numeric/status values were not extracted",
        )

    source_bound_state = _source_bound_numeric_authority_state_from_diagnostic(facts)
    if (
        source_bound_state.satisfaction_for("source_bound_numeric")
        .status
        is not AuthorityStatus.FULFILLED
    ):
        return _result(
            NUMERIC_VALUE_NOT_SOURCE_BOUND,
            NUMERIC_EXTRACTION_LANE,
            "high",
            "numeric values were extracted without stable source binding",
        )

    if facts.final_answer_value_mismatch:
        if facts.economist_ran and facts.economist_source_bound_values_present:
            return _result(
                ECONOMIST_CORRECT_DISTORTED_DOWNSTREAM,
                AUTHOR_SYNTHESIS_LANE,
                "medium",
                "Economist had source-bound values but final answer did not preserve them",
            )
        return _result(
            FINAL_SYNTHESIS_DISTORTION,
            AUTHOR_SYNTHESIS_LANE,
            "high",
            "source-bound values were available but distorted in the final answer",
        )

    return _result(
        NO_BOTTLENECK_DETECTED,
        NO_ACTION_LANE,
        "medium",
        "sanitized diagnostic inputs did not identify a grounding bottleneck",
    )


def _source_bound_numeric_authority_state_from_diagnostic(
    diagnostic: OfficialNumericGroundingDiagnostic,
) -> AuthoritativeSourceObligationState:
    requirement = AuthorityRequirement.source_bound_numeric("source_bound_numeric")
    fits: tuple[AuthorityEvidenceFit, ...]
    if diagnostic.numeric_values_source_bound:
        fits = (
            AuthorityEvidenceFit.authoritative(
                requirement.requirement_id,
                "sanitized_numeric_source_binding",
                SOURCED_NUMERIC_VALUES,
            ),
        )
    elif diagnostic.numeric_values_extracted:
        fits = (
            AuthorityEvidenceFit.lower_tier_context(
                requirement.requirement_id,
                "numeric_value_without_source_binding",
                mismatch_reason="numeric_value_not_source_bound",
            ),
        )
    else:
        fits = ()
    return AuthoritativeSourceObligationState.evaluate([requirement], fits)


def _result(
    bottleneck_class: str,
    next_recommended_lane: str,
    confidence: str,
    *rationale: str,
) -> OfficialNumericGroundingClassification:
    return OfficialNumericGroundingClassification(
        schema_version=SCHEMA_VERSION,
        bottleneck_class=bottleneck_class,
        next_recommended_lane=next_recommended_lane,
        confidence=confidence,
        rationale=tuple(rationale),
        behavior_changed=False,
    )


__all__ = [
    "ANSWER_CAVEATED_MISSING_EVIDENCE",
    "AUTHOR_SYNTHESIS_LANE",
    "CITATION_SOURCE_FIT_LANE",
    "ECONOMIST_CORRECT_DISTORTED_DOWNSTREAM",
    "ECONOMIST_ELIGIBLE_NOT_INVOKED",
    "ECONOMIST_HANDOFF_LANE",
    "ECONOMIST_INVOCATION_LANE",
    "ECONOMIST_INVOKED_WEAK_EVIDENCE",
    "FINAL_SYNTHESIS_DISTORTION",
    "NO_ACTION_LANE",
    "NO_BOTTLENECK_DETECTED",
    "NUMERIC_EXTRACTION_LANE",
    "NUMERIC_VALUE_NOT_SOURCE_BOUND",
    "OFFICIAL_SOURCE_ACQUIRED_NOT_ACCEPTED",
    "OFFICIAL_SOURCE_NOT_ACQUIRED",
    "OFFICIAL_SOURCE_NOT_IN_FINAL_EVIDENCE",
    "OFFICIAL_SOURCE_NOT_REQUIRED",
    "OFFICIAL_SOURCE_VISIBLE_NOT_CITED",
    "OfficialNumericGroundingClassification",
    "OfficialNumericGroundingDiagnostic",
    "SCHEMA_VERSION",
    "SOURCE_ACQUISITION_SURVIVAL_LANE",
    "SOURCE_NEED_NOT_DETECTED",
    "WRONG_NUMBER_EXTRACTED",
    "classify_official_numeric_grounding",
]
