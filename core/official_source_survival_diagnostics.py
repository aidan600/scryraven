"""Pure AG-48B source acquisition/survival diagnostics.

This module consumes sanitized booleans and counts from tests or future review
packets. It does not inspect traces, call providers, alter prompts, import
runtime source-class behavior, or participate in orchestration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

SCHEMA_VERSION = "official_source_survival_ag48b_v1"

OBLIGATION_NOT_DETECTED = "obligation_not_detected"
NO_CANDIDATE_QUERY = "no_candidate_query"
NO_OFFICIAL_CANDIDATES_RETURNED = "no_official_candidates_returned"
OFFICIAL_CANDIDATE_REJECTED_OR_UNREADABLE = (
    "official_candidate_rejected_or_unreadable"
)
OFFICIAL_CANDIDATE_MISCLASSIFIED = "official_candidate_misclassified"
ACCEPTED_SOURCE_DROPPED_BEFORE_FINAL_EVIDENCE = (
    "accepted_source_dropped_before_final_evidence"
)
FINAL_EVIDENCE_SOURCE_NOT_CITED = "final_evidence_source_not_cited"
CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED = (
    "citation_survived_but_value_extraction_failed"
)
ANSWER_CORRECTLY_CAVEATED_MISSING_SOURCE = (
    "answer_correctly_caveated_missing_source"
)
NOT_A_SOURCE_ACQUISITION_FAILURE = "not_a_source_acquisition_failure"

SOURCE_OBLIGATION_DETECTION_STAGE = "source_obligation_detection"
CANDIDATE_QUERY_GENERATION_STAGE = "candidate_query_generation"
CANDIDATE_ACQUISITION_STAGE = "candidate_acquisition"
CANDIDATE_ACCEPTANCE_STAGE = "candidate_acceptance"
FINAL_EVIDENCE_SURVIVAL_STAGE = "final_evidence_survival"
FINAL_CITATION_SURVIVAL_STAGE = "final_citation_survival"
CITED_VALUE_EXTRACTION_STAGE = "cited_value_extraction"
SOURCE_SURVIVED_STAGE = "source_survived"

NO_ACTION_LANE = "no_action"
SOURCE_ACQUISITION_SURVIVAL_LANE = "source_acquisition_survival_lane"
SOURCE_CLASS_CANONICAL_CLASSIFICATION_LANE = (
    "source_class_canonical_classification_lane"
)
SOURCE_FIT_CITATION_SURVIVAL_LANE = "source_fit_citation_survival_lane"
NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE = (
    "numeric_extraction_source_bound_value_lane"
)

CAVEAT_PRESENT = "caveat_present"
CAVEAT_ABSENT = "caveat_absent"
CAVEAT_NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class OfficialSourceSurvivalDiagnostic:
    """Sanitized AG-48B source survival inputs."""

    question_type: str
    source_obligation_required: bool
    required_source_obligation: str = ""
    obligation_detected: bool = True
    candidate_query_count: int = 0
    candidate_official_or_canonical_count: int = 0
    accepted_official_or_canonical_count: int = 0
    final_evidence_official_or_canonical_count: int = 0
    final_citation_official_or_canonical_count: int = 0
    candidate_misclassified: bool = False
    caveat_present: bool = False
    numeric_value_mismatch: bool = False
    metadata: Mapping[str, Any] | None = None

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> "OfficialSourceSurvivalDiagnostic":
        """Build diagnostic input from a sanitized mapping."""
        return cls(
            question_type=str(payload.get("question_type") or "unspecified"),
            source_obligation_required=bool(
                payload.get("source_obligation_required")
            ),
            required_source_obligation=str(
                payload.get("required_source_obligation") or ""
            ),
            obligation_detected=bool(payload.get("obligation_detected", True)),
            candidate_query_count=_non_negative_int(
                payload.get("candidate_query_count")
            ),
            candidate_official_or_canonical_count=_non_negative_int(
                payload.get("candidate_official_or_canonical_count")
            ),
            accepted_official_or_canonical_count=_non_negative_int(
                payload.get("accepted_official_or_canonical_count")
            ),
            final_evidence_official_or_canonical_count=_non_negative_int(
                payload.get("final_evidence_official_or_canonical_count")
            ),
            final_citation_official_or_canonical_count=_non_negative_int(
                payload.get("final_citation_official_or_canonical_count")
            ),
            candidate_misclassified=bool(payload.get("candidate_misclassified")),
            caveat_present=bool(payload.get("caveat_present")),
            numeric_value_mismatch=bool(payload.get("numeric_value_mismatch")),
            metadata=(
                dict(payload.get("metadata"))
                if isinstance(payload.get("metadata"), Mapping)
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfficialSourceSurvivalClassification:
    """Diagnostic output. ``behavior_changed`` must remain false."""

    schema_version: str
    bottleneck_class: str
    source_survival_stage: str
    recommended_next_lane: str
    caveat_status: str
    rationale: tuple[str, ...] = field(default_factory=tuple)
    behavior_changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_official_source_survival(
    diagnostic: OfficialSourceSurvivalDiagnostic | Mapping[str, Any],
) -> OfficialSourceSurvivalClassification:
    """Classify the earliest material official/canonical source disappearance."""
    facts = (
        OfficialSourceSurvivalDiagnostic.from_mapping(diagnostic)
        if isinstance(diagnostic, Mapping)
        else diagnostic
    )

    if not facts.source_obligation_required:
        return _result(
            NOT_A_SOURCE_ACQUISITION_FAILURE,
            SOURCE_SURVIVED_STAGE,
            NO_ACTION_LANE,
            _caveat_status(facts),
            "official/current/canonical source obligation was not required",
            f"question_type={facts.question_type}",
        )

    if not facts.obligation_detected:
        return _result(
            OBLIGATION_NOT_DETECTED,
            SOURCE_OBLIGATION_DETECTION_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            _caveat_status(facts),
            "required source obligation was not detected",
        )

    if facts.candidate_query_count <= 0:
        return _result(
            NO_CANDIDATE_QUERY,
            CANDIDATE_QUERY_GENERATION_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            _caveat_status(facts),
            "source obligation was detected but no candidate query was available",
        )

    if facts.candidate_official_or_canonical_count <= 0:
        if facts.caveat_present and not facts.numeric_value_mismatch:
            return _result(
                ANSWER_CORRECTLY_CAVEATED_MISSING_SOURCE,
                CANDIDATE_ACQUISITION_STAGE,
                SOURCE_ACQUISITION_SURVIVAL_LANE,
                _caveat_status(facts),
                "no official/current/canonical candidates returned and answer caveated missing evidence",
            )
        return _result(
            NO_OFFICIAL_CANDIDATES_RETURNED,
            CANDIDATE_ACQUISITION_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            _caveat_status(facts),
            "candidate queries returned no official/current/canonical candidates",
        )

    if facts.accepted_official_or_canonical_count <= 0:
        if facts.candidate_misclassified:
            return _result(
                OFFICIAL_CANDIDATE_MISCLASSIFIED,
                CANDIDATE_ACCEPTANCE_STAGE,
                SOURCE_CLASS_CANONICAL_CLASSIFICATION_LANE,
                _caveat_status(facts),
                "official/current/canonical candidate was returned but misclassified",
            )
        return _result(
            OFFICIAL_CANDIDATE_REJECTED_OR_UNREADABLE,
            CANDIDATE_ACCEPTANCE_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            _caveat_status(facts),
            "official/current/canonical candidate was rejected or unreadable",
        )

    if facts.final_evidence_official_or_canonical_count <= 0:
        return _result(
            ACCEPTED_SOURCE_DROPPED_BEFORE_FINAL_EVIDENCE,
            FINAL_EVIDENCE_SURVIVAL_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            _caveat_status(facts),
            "accepted official/current/canonical source did not reach final evidence",
        )

    if facts.final_citation_official_or_canonical_count <= 0:
        return _result(
            FINAL_EVIDENCE_SOURCE_NOT_CITED,
            FINAL_CITATION_SURVIVAL_STAGE,
            SOURCE_FIT_CITATION_SURVIVAL_LANE,
            _caveat_status(facts),
            "final evidence included the source but final answer did not cite it",
        )

    if facts.numeric_value_mismatch:
        return _result(
            CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED,
            CITED_VALUE_EXTRACTION_STAGE,
            NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE,
            _caveat_status(facts),
            "source citation survived but numeric/status extraction or binding failed",
        )

    return _result(
        NOT_A_SOURCE_ACQUISITION_FAILURE,
        SOURCE_SURVIVED_STAGE,
        NO_ACTION_LANE,
        _caveat_status(facts),
        "required source survived through final citation",
    )


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _caveat_status(facts: OfficialSourceSurvivalDiagnostic) -> str:
    if not facts.source_obligation_required:
        return CAVEAT_NOT_APPLICABLE
    return CAVEAT_PRESENT if facts.caveat_present else CAVEAT_ABSENT


def _result(
    bottleneck_class: str,
    source_survival_stage: str,
    recommended_next_lane: str,
    caveat_status: str,
    *rationale: str,
) -> OfficialSourceSurvivalClassification:
    return OfficialSourceSurvivalClassification(
        schema_version=SCHEMA_VERSION,
        bottleneck_class=bottleneck_class,
        source_survival_stage=source_survival_stage,
        recommended_next_lane=recommended_next_lane,
        caveat_status=caveat_status,
        rationale=tuple(rationale),
        behavior_changed=False,
    )


__all__ = [
    "ACCEPTED_SOURCE_DROPPED_BEFORE_FINAL_EVIDENCE",
    "ANSWER_CORRECTLY_CAVEATED_MISSING_SOURCE",
    "CANDIDATE_ACCEPTANCE_STAGE",
    "CANDIDATE_ACQUISITION_STAGE",
    "CANDIDATE_QUERY_GENERATION_STAGE",
    "CAVEAT_ABSENT",
    "CAVEAT_NOT_APPLICABLE",
    "CAVEAT_PRESENT",
    "CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED",
    "CITED_VALUE_EXTRACTION_STAGE",
    "FINAL_CITATION_SURVIVAL_STAGE",
    "FINAL_EVIDENCE_SOURCE_NOT_CITED",
    "FINAL_EVIDENCE_SURVIVAL_STAGE",
    "NO_ACTION_LANE",
    "NO_CANDIDATE_QUERY",
    "NO_OFFICIAL_CANDIDATES_RETURNED",
    "NOT_A_SOURCE_ACQUISITION_FAILURE",
    "NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE",
    "OBLIGATION_NOT_DETECTED",
    "OFFICIAL_CANDIDATE_MISCLASSIFIED",
    "OFFICIAL_CANDIDATE_REJECTED_OR_UNREADABLE",
    "OfficialSourceSurvivalClassification",
    "OfficialSourceSurvivalDiagnostic",
    "SCHEMA_VERSION",
    "SOURCE_ACQUISITION_SURVIVAL_LANE",
    "SOURCE_CLASS_CANONICAL_CLASSIFICATION_LANE",
    "SOURCE_FIT_CITATION_SURVIVAL_LANE",
    "SOURCE_OBLIGATION_DETECTION_STAGE",
    "SOURCE_SURVIVED_STAGE",
    "classify_official_source_survival",
]
