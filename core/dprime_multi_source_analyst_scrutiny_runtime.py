"""D-prime multi-source Analyst posture and narrow Scrutineer gate.

This runtime consumes multiple generic single-relation D-prime intakes for one
answer component and one lane only. It aggregates support/conflict/caveat
posture across sources and runs a narrow deterministic Scrutineer challenge gate
that product status must consume before the answer path can proceed.

It does not invoke Economist or Specialist routing, does not run live/model/
provider/search/fetch/read/retrieval calls, does not claim product correctness,
and does not replace the existing support bundle, answer path, or follow-up
loop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SCHEMA_VERSION = (
    "dprime_multi_source_analyst_scrutiny_runtime_v1"
)
DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SURFACE = (
    "core.dprime_multi_source_analyst_scrutiny_runtime"
)
DPRIME_MULTI_SOURCE_OWNER = "RunKernel.DPrimeMultiSourceAnalystScrutiny"
DPRIME_MULTI_SOURCE_SCRUTINEER_OWNER = (
    "RunKernel.DPrimeMultiSourceScrutineerChallengeGate"
)

BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING = (
    "BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING"
)
BLOCKED_DPRIME_MULTI_SOURCE_SUPPORT_POSTURE_MISSING = (
    "BLOCKED_DPRIME_MULTI_SOURCE_SUPPORT_POSTURE_MISSING"
)
BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_GATE_MISSING = (
    "BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_GATE_MISSING"
)
BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_CHALLENGE = (
    "BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_CHALLENGE"
)
BLOCKED_DPRIME_MULTI_SOURCE_CONFLICT_UNRESOLVED = (
    "BLOCKED_DPRIME_MULTI_SOURCE_CONFLICT_UNRESOLVED"
)
BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED = (
    "BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED"
)

SCRUTINEER_STATUS_PASSED = "passed"
SCRUTINEER_STATUS_CHALLENGED = "challenged"
SCRUTINEER_STATUS_BLOCKED = "blocked"

CHALLENGE_NONE = "none"
CHALLENGE_CONTRADICTION = "contradiction"
CHALLENGE_MISSING_QUALIFIER = "missing_qualifier"
CHALLENGE_CURRENTNESS_CONFLICT = "currentness_conflict"
CHALLENGE_SOURCE_LAUNDERING_RISK = "source_laundering_risk"
CHALLENGE_UNSUPPORTED_OVERCLAIM = "unsupported_overclaim"

_SUPPORT_BEARING_RELATIONS = frozenset({"directly_supports", "partially_supports"})
_CONTRADICTION_RELATIONS = frozenset({"contradicts"})
_CAVEAT_RELATIONS = frozenset({"partially_supports", "missing_qualifier"})
_CURRENTNESS_OK = frozenset({"", "current", "current_passed", "passed"})
_CONTRADICTION_ABSENT = frozenset({"", "absent", "none", "not_contradicted"})


class DPrimeMultiSourceAnalystScrutinyError(ValueError):
    """Raised when multi-source D-prime posture cannot be consumed safely."""

    def __init__(self, blocker: str, detail: str) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DPrimeMultiSourceRelationSet:
    """Product-visible relation-set ref for one D-prime answer component."""

    relation_set_id: str
    relation_set_digest: str
    answer_component_id: str
    source_obligation_candidate_ids: Sequence[str]
    relation_intake_refs: Sequence[Mapping[str, Any]]
    assessment_refs: Sequence[Mapping[str, Any]]
    evidence_source_refs: Sequence[Mapping[str, Any]]
    source_count: int
    relation_count: int

    def to_status_ref(self) -> dict[str, Any]:
        return {
            "schema_version": DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SCHEMA_VERSION,
            "owner": DPRIME_MULTI_SOURCE_OWNER,
            "runtime_surface": DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SURFACE,
            "status": "consumed",
            "relation_set_id": self.relation_set_id,
            "relation_set_digest": self.relation_set_digest,
            "relation_count": self.relation_count,
            "source_count": self.source_count,
            "answer_component_id": self.answer_component_id,
            "source_obligation_candidate_ids": list(
                self.source_obligation_candidate_ids
            ),
            "relation_intake_refs": [dict(item) for item in self.relation_intake_refs],
            "assessment_refs": [dict(item) for item in self.assessment_refs],
            "evidence_source_refs": [dict(item) for item in self.evidence_source_refs],
            "single_lane_only": True,
            "multi_component": False,
            "relation_set_is_support_authority": False,
            "product_correctness_claimed": False,
            "live_calls_run": False,
        }


@dataclass(frozen=True, slots=True)
class DPrimeMultiSourceSupportPosture:
    """Aggregate support/conflict/caveat posture for a relation set."""

    support_posture_id: str
    support_posture_digest: str
    relation_set_ref: Mapping[str, Any]
    support_bearing_relation_refs: Sequence[Mapping[str, Any]]
    contradiction_relation_refs: Sequence[Mapping[str, Any]]
    caveat_relation_refs: Sequence[Mapping[str, Any]]
    currentness_posture: str
    conflict_posture: str
    source_count: int
    source_display_candidate_refs: Sequence[Mapping[str, Any]]
    answer_path_allowed: bool
    blocker: str | None
    blocker_detail: str | None
    challenge_kind: str

    def to_status_ref(self) -> dict[str, Any]:
        return _without_empty(
            {
                "schema_version": DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SCHEMA_VERSION,
                "owner": DPRIME_MULTI_SOURCE_OWNER,
                "runtime_surface": DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SURFACE,
                "status": "consumed",
                "support_posture_id": self.support_posture_id,
                "support_posture_digest": self.support_posture_digest,
                "relation_set_ref": dict(self.relation_set_ref),
                "support_bearing_relation_refs": [
                    dict(item) for item in self.support_bearing_relation_refs
                ],
                "contradiction_relation_refs": [
                    dict(item) for item in self.contradiction_relation_refs
                ],
                "caveat_relation_refs": [
                    dict(item) for item in self.caveat_relation_refs
                ],
                "currentness_posture": self.currentness_posture,
                "conflict_posture": self.conflict_posture,
                "source_count": self.source_count,
                "source_display_candidate_refs": [
                    dict(item) for item in self.source_display_candidate_refs
                ],
                "answer_path_allowed": self.answer_path_allowed,
                "blocker": self.blocker,
                "blocker_detail": self.blocker_detail,
                "challenge_kind": self.challenge_kind,
                "multi_source_posture_is_answer_authority": False,
                "product_correctness_claimed": False,
                "live_calls_run": False,
            }
        )


@dataclass(frozen=True, slots=True)
class DPrimeScrutineerChallengeRef:
    """Narrow product-consumed Scrutineer gate over multi-source posture."""

    scrutineer_gate_id: str
    scrutineer_gate_digest: str
    status: str
    challenge_kind: str
    consumed_multi_source_posture_digest: str
    answer_path_allowed: bool
    blocker: str | None
    blocker_detail: str | None

    def to_status_ref(self) -> dict[str, Any]:
        return _without_empty(
            {
                "schema_version": DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SCHEMA_VERSION,
                "owner": DPRIME_MULTI_SOURCE_SCRUTINEER_OWNER,
                "runtime_surface": DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SURFACE,
                "status": self.status,
                "scrutineer_gate_id": self.scrutineer_gate_id,
                "scrutineer_gate_digest": self.scrutineer_gate_digest,
                "challenge_kind": self.challenge_kind,
                "consumed_multi_source_posture_digest": (
                    self.consumed_multi_source_posture_digest
                ),
                "answer_path_allowed": self.answer_path_allowed,
                "blocker": self.blocker,
                "blocker_detail": self.blocker_detail,
                "scrutineer_gate_consumed_by_product_status": True,
                "scrutineer_is_product_correctness": False,
                "product_correctness_claimed": False,
                "live_calls_run": False,
            }
        )


def build_dprime_multi_source_relation_set(
    *,
    relation_intake_refs: Sequence[Mapping[str, Any]],
    assessment_material_refs: Sequence[Mapping[str, Any]],
) -> DPrimeMultiSourceRelationSet:
    """Build one product-visible relation set for a single component lane."""

    relations = [_safe_mapping(item) for item in relation_intake_refs]
    assessments = [_safe_mapping(item) for item in assessment_material_refs]
    relations = [item for item in relations if item]
    assessments = [item for item in assessments if item]
    if len(relations) < 2:
        raise DPrimeMultiSourceAnalystScrutinyError(
            BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING,
            "multi-source D-prime requires at least two relation intakes",
        )
    if len(assessments) != len(relations):
        raise DPrimeMultiSourceAnalystScrutinyError(
            BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING,
            "multi-source D-prime requires one assessment material ref per relation",
        )

    component_ids = {_required_token(item.get("component_id")) for item in relations}
    if len(component_ids) != 1:
        raise DPrimeMultiSourceAnalystScrutinyError(
            BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING,
            "multi-source D-prime is single answer-component only",
        )
    component_id = next(iter(component_ids))
    source_id_sets = {
        tuple(_text_tuple(item.get("source_obligation_candidate_ids")))
        for item in relations
    }
    if len(source_id_sets) != 1 or not next(iter(source_id_sets)):
        raise DPrimeMultiSourceAnalystScrutinyError(
            BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING,
            "multi-source D-prime requires one shared source-obligation lane",
        )
    source_ids = next(iter(source_id_sets))
    if any(item.get("single_lane_only") is not True for item in relations):
        raise DPrimeMultiSourceAnalystScrutinyError(
            BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING,
            "multi-source D-prime requires single-lane relation intakes",
        )

    evidence_refs = _dedupe_refs(
        [_evidence_ref_from_relation(item) for item in relations],
        key_fields=("evidence_reference_id", "evidence_candidate_id", "source_url"),
    )
    source_count = len(
        {
            ref.get("source_url")
            or ref.get("evidence_reference_id")
            or ref.get("evidence_candidate_id")
            for ref in evidence_refs
            if ref
        }
    )
    digest_payload = {
        "schema_version": DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SCHEMA_VERSION,
        "answer_component_id": component_id,
        "source_obligation_candidate_ids": list(source_ids),
        "relation_refs": [
            _relation_digest_ref(item) for item in relations
        ],
        "assessment_refs": [
            _assessment_digest_ref(item) for item in assessments
        ],
        "evidence_refs": evidence_refs,
        "single_lane_only": True,
        "multi_component": False,
    }
    digest = _digest_json(digest_payload)
    return DPrimeMultiSourceRelationSet(
        relation_set_id=f"dprime-multi-source-relation-set:{component_id}:{digest[:16]}",
        relation_set_digest=digest,
        answer_component_id=component_id,
        source_obligation_candidate_ids=source_ids,
        relation_intake_refs=tuple(relations),
        assessment_refs=tuple(_assessment_digest_ref(item) for item in assessments),
        evidence_source_refs=tuple(evidence_refs),
        source_count=source_count,
        relation_count=len(relations),
    )


def build_dprime_multi_source_support_posture(
    *,
    relation_set: DPrimeMultiSourceRelationSet,
    assessment_material_refs: Sequence[Mapping[str, Any]],
) -> DPrimeMultiSourceSupportPosture:
    """Aggregate support, conflict, currentness, and caveat posture."""

    relation_ref = relation_set.to_status_ref()
    assessments = [_safe_mapping(item) for item in assessment_material_refs]
    if len(assessments) != relation_set.relation_count:
        raise DPrimeMultiSourceAnalystScrutinyError(
            BLOCKED_DPRIME_MULTI_SOURCE_SUPPORT_POSTURE_MISSING,
            "multi-source support posture requires aligned assessments",
        )

    support_refs: list[dict[str, Any]] = []
    contradiction_refs: list[dict[str, Any]] = []
    caveat_refs: list[dict[str, Any]] = []
    currentness_problem_refs: list[dict[str, Any]] = []
    for index, (relation, assessment) in enumerate(
        zip(relation_set.relation_intake_refs, assessments, strict=True),
        start=1,
    ):
        ref = _posture_relation_ref(index, relation, assessment)
        support_relation = _clean_token(assessment.get("support_relation")) or ""
        currentness = _clean_token(
            _safe_mapping(assessment.get("currentness_check")).get("status")
        ) or ""
        contradiction = _clean_token(
            _safe_mapping(assessment.get("contradiction_check")).get("status")
        ) or ""
        missing = _text_tuple(assessment.get("missing_qualifiers"))
        if support_relation in _SUPPORT_BEARING_RELATIONS:
            support_refs.append(ref)
        if (
            support_relation in _CONTRADICTION_RELATIONS
            or contradiction not in _CONTRADICTION_ABSENT
        ):
            contradiction_refs.append(ref)
        if support_relation in _CAVEAT_RELATIONS or missing:
            caveat_refs.append(
                {
                    **ref,
                    "missing_qualifiers": list(missing),
                }
            )
        if currentness not in _CURRENTNESS_OK:
            currentness_problem_refs.append(
                {
                    **ref,
                    "currentness_status": currentness,
                }
            )

    source_laundering = relation_set.source_count < 2
    unsupported_overclaim = len(support_refs) < 2
    challenge_kind = CHALLENGE_NONE
    blocker = None
    blocker_detail = None
    if contradiction_refs:
        challenge_kind = CHALLENGE_CONTRADICTION
        blocker = BLOCKED_DPRIME_MULTI_SOURCE_CONFLICT_UNRESOLVED
        blocker_detail = "multi-source posture has contradiction-bearing relation"
    elif currentness_problem_refs:
        challenge_kind = CHALLENGE_CURRENTNESS_CONFLICT
        blocker = BLOCKED_DPRIME_MULTI_SOURCE_CONFLICT_UNRESOLVED
        blocker_detail = "multi-source posture has material currentness conflict"
    elif any(_safe_mapping(item).get("missing_qualifiers") for item in caveat_refs):
        challenge_kind = CHALLENGE_MISSING_QUALIFIER
        blocker = BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_CHALLENGE
        blocker_detail = "multi-source posture has a material missing qualifier"
    elif source_laundering:
        challenge_kind = CHALLENGE_SOURCE_LAUNDERING_RISK
        blocker = BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_CHALLENGE
        blocker_detail = "multi-source posture does not prove at least two sources"
    elif unsupported_overclaim:
        challenge_kind = CHALLENGE_UNSUPPORTED_OVERCLAIM
        blocker = BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_CHALLENGE
        blocker_detail = "multi-source posture lacks two support-bearing relations"

    answer_path_allowed = blocker is None
    currentness_posture = "current"
    if currentness_problem_refs:
        currentness_posture = "conflicting"
    conflict_posture = "present" if contradiction_refs else "none"
    digest_payload = {
        "relation_set_digest": relation_set.relation_set_digest,
        "support_refs": support_refs,
        "contradiction_refs": contradiction_refs,
        "caveat_refs": caveat_refs,
        "currentness_posture": currentness_posture,
        "conflict_posture": conflict_posture,
        "source_count": relation_set.source_count,
        "answer_path_allowed": answer_path_allowed,
        "challenge_kind": challenge_kind,
    }
    digest = _digest_json(digest_payload)
    return DPrimeMultiSourceSupportPosture(
        support_posture_id=(
            "dprime-multi-source-support-posture:"
            f"{relation_set.answer_component_id}:{digest[:16]}"
        ),
        support_posture_digest=digest,
        relation_set_ref=relation_ref,
        support_bearing_relation_refs=tuple(support_refs),
        contradiction_relation_refs=tuple(contradiction_refs),
        caveat_relation_refs=tuple(caveat_refs),
        currentness_posture=currentness_posture,
        conflict_posture=conflict_posture,
        source_count=relation_set.source_count,
        source_display_candidate_refs=tuple(relation_set.evidence_source_refs),
        answer_path_allowed=answer_path_allowed,
        blocker=blocker,
        blocker_detail=blocker_detail,
        challenge_kind=challenge_kind,
    )


def build_dprime_scrutineer_challenge_gate(
    *,
    support_posture: DPrimeMultiSourceSupportPosture,
    scrutineer_enabled: bool = True,
) -> DPrimeScrutineerChallengeRef:
    """Consume multi-source posture through a deterministic Scrutineer gate."""

    if not scrutineer_enabled:
        return _scrutineer_gate(
            status=SCRUTINEER_STATUS_BLOCKED,
            challenge_kind="scrutineer_gate_missing",
            support_posture=support_posture,
            answer_path_allowed=False,
            blocker=BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_GATE_MISSING,
            blocker_detail="multi-source answer path requires Scrutineer gate",
        )
    if support_posture.answer_path_allowed:
        return _scrutineer_gate(
            status=SCRUTINEER_STATUS_PASSED,
            challenge_kind=CHALLENGE_NONE,
            support_posture=support_posture,
            answer_path_allowed=True,
            blocker=None,
            blocker_detail=None,
        )
    return _scrutineer_gate(
        status=SCRUTINEER_STATUS_CHALLENGED,
        challenge_kind=support_posture.challenge_kind,
        support_posture=support_posture,
        answer_path_allowed=False,
        blocker=support_posture.blocker
        or BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_CHALLENGE,
        blocker_detail=support_posture.blocker_detail
        or "Scrutineer challenged the multi-source posture",
    )


def _scrutineer_gate(
    *,
    status: str,
    challenge_kind: str,
    support_posture: DPrimeMultiSourceSupportPosture,
    answer_path_allowed: bool,
    blocker: str | None,
    blocker_detail: str | None,
) -> DPrimeScrutineerChallengeRef:
    payload = {
        "schema_version": DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SCHEMA_VERSION,
        "owner": DPRIME_MULTI_SOURCE_SCRUTINEER_OWNER,
        "runtime_surface": DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SURFACE,
        "status": status,
        "challenge_kind": challenge_kind,
        "support_posture_digest": support_posture.support_posture_digest,
        "answer_path_allowed": answer_path_allowed,
        "blocker": blocker,
        "blocker_detail": blocker_detail,
        "product_correctness_claimed": False,
        "live_calls_run": False,
    }
    digest = _digest_json(payload)
    return DPrimeScrutineerChallengeRef(
        scrutineer_gate_id=f"dprime-scrutineer-gate:{digest[:16]}",
        scrutineer_gate_digest=digest,
        status=status,
        challenge_kind=challenge_kind,
        consumed_multi_source_posture_digest=(
            support_posture.support_posture_digest
        ),
        answer_path_allowed=answer_path_allowed,
        blocker=blocker,
        blocker_detail=blocker_detail,
    )


def _posture_relation_ref(
    index: int,
    relation: Mapping[str, Any],
    assessment: Mapping[str, Any],
) -> dict[str, Any]:
    return _without_empty(
        {
            "ordinal": index,
            "relation_intake_id": relation.get("relation_intake_id"),
            "relation_intake_digest": relation.get("relation_intake_digest"),
            "assessment_id": assessment.get("assessment_id"),
            "assessment_digest": assessment.get("assessment_digest"),
            "support_relation": assessment.get("support_relation"),
            "evidence_candidate_id": relation.get("evidence_candidate_id"),
            "evidence_reference_id": relation.get("evidence_reference_id"),
            "source_domain": relation.get("source_domain"),
            "source_url": relation.get("source_url"),
            "source_title": relation.get("source_title"),
        }
    )


def _evidence_ref_from_relation(relation: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "evidence_candidate_id": relation.get("evidence_candidate_id"),
            "evidence_reference_id": relation.get("evidence_reference_id"),
            "source_title": relation.get("source_title"),
            "source_domain": relation.get("source_domain"),
            "source_url": relation.get("source_url"),
        }
    )


def _relation_digest_ref(relation: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "relation_intake_id": relation.get("relation_intake_id"),
            "relation_intake_digest": relation.get("relation_intake_digest"),
            "component_id": relation.get("component_id"),
            "source_obligation_candidate_ids": _text_tuple(
                relation.get("source_obligation_candidate_ids")
            ),
            "evidence_candidate_id": relation.get("evidence_candidate_id"),
            "evidence_reference_id": relation.get("evidence_reference_id"),
        }
    )


def _assessment_digest_ref(assessment: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "assessment_id": assessment.get("assessment_id"),
            "assessment_digest": assessment.get("assessment_digest"),
            "support_relation": assessment.get("support_relation"),
            "currentness_check": _safe_mapping(assessment.get("currentness_check")),
            "contradiction_check": _safe_mapping(assessment.get("contradiction_check")),
            "missing_qualifiers": list(
                _text_tuple(assessment.get("missing_qualifiers"))
            ),
        }
    )


def _dedupe_refs(
    refs: Sequence[Mapping[str, Any]],
    *,
    key_fields: Sequence[str] = ("relation_intake_digest", "assessment_digest"),
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for ref in refs:
        mapped = _safe_mapping(ref)
        if not mapped:
            continue
        key = tuple(mapped.get(field) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        out.append(mapped)
    return out


def _required_token(value: Any, *, limit: int = 260) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        raise DPrimeMultiSourceAnalystScrutinyError(
            BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING,
            "multi-source D-prime relation set is missing required lineage",
        )
    return text


def _safe_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return (text,) if text else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    text = _clean_text(value, limit=limit)
    return text.casefold().replace("-", "_").replace(" ", "_") if text else None


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {}, ())
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_json_safe(item) for item in value]
    return value


__all__ = [
    "BLOCKED_DPRIME_MULTI_SOURCE_CONFLICT_UNRESOLVED",
    "BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED",
    "BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING",
    "BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_CHALLENGE",
    "BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_GATE_MISSING",
    "BLOCKED_DPRIME_MULTI_SOURCE_SUPPORT_POSTURE_MISSING",
    "DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SCHEMA_VERSION",
    "DPRIME_MULTI_SOURCE_ANALYST_SCRUTINY_SURFACE",
    "DPrimeMultiSourceAnalystScrutinyError",
    "DPrimeMultiSourceRelationSet",
    "DPrimeMultiSourceSupportPosture",
    "DPrimeScrutineerChallengeRef",
    "SCRUTINEER_STATUS_BLOCKED",
    "SCRUTINEER_STATUS_CHALLENGED",
    "SCRUTINEER_STATUS_PASSED",
    "build_dprime_multi_source_relation_set",
    "build_dprime_multi_source_support_posture",
    "build_dprime_scrutineer_challenge_gate",
]
