"""Generic single-relation D-prime Analyst intake.

This module describes one single D-prime Analyst relation. It is intake and
lineage only, not support authority. It does not create SemanticObservation,
ComponentCoverage, source-obligation authority, citation authority,
SufficiencyReadiness, FinalAnswerPacket, Author output, search, follow-up
authorization, live calls, or product correctness.

The intake must be consumed by existing product and RunKernel authority surfaces
to matter.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

DPRIME_ANALYST_RELATION_INTAKE_SCHEMA_VERSION = (
    "dprime_analyst_relation_intake_runtime_v1"
)
DPRIME_ANALYST_RELATION_INTAKE_SURFACE = (
    "core.dprime_analyst_relation_intake_runtime"
)
DPRIME_ANALYST_RELATION_KIND = "evidence_support_for_answer_component"
DPRIME_ANALYST_RELATION_INTAKE_STATUS_CONSUMED = "consumed"

_CLOSED_SURFACE_FALSE_FLAGS = {
    "support_claimed": False,
    "answer_created": False,
    "semantic_observation_created": False,
    "component_coverage_bound": False,
    "source_obligation_authority_claimed": False,
    "source_obligation_satisfaction_claimed": False,
    "citation_authority_claimed": False,
    "citation_eligibility_claimed": False,
    "sufficiency_readiness_created": False,
    "final_answer_packet_created": False,
    "author_output_created": False,
    "search_authorized": False,
    "live_calls_run": False,
    "product_correctness_claimed": False,
}


class DPrimeAnalystRelationIntakeError(ValueError):
    """Raised when a single-relation D-prime intake cannot be represented."""


@dataclass(frozen=True, slots=True)
class DPrimeAnalystRelationIntake:
    """Lineage-only D-prime Analyst relation intake."""

    relation_id: str
    relation_digest: str
    question_ref: Mapping[str, Any]
    answer_component_ref: Mapping[str, Any]
    source_obligation_ref: Mapping[str, Any]
    evidence_source_ref: Mapping[str, Any]
    readiness_ref: Mapping[str, Any]
    relation_kind: str = DPRIME_ANALYST_RELATION_KIND
    single_lane_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DPRIME_ANALYST_RELATION_INTAKE_SCHEMA_VERSION,
            "record_kind": "DPrimeAnalystRelationIntake",
            "runtime_surface": DPRIME_ANALYST_RELATION_INTAKE_SURFACE,
            "status": DPRIME_ANALYST_RELATION_INTAKE_STATUS_CONSUMED,
            "relation_id": self.relation_id,
            "relation_digest": self.relation_digest,
            "relation_kind": self.relation_kind,
            "single_lane_only": self.single_lane_only,
            "question_ref": dict(self.question_ref),
            "answer_component_ref": dict(self.answer_component_ref),
            "source_obligation_ref": dict(self.source_obligation_ref),
            "evidence_source_ref": dict(self.evidence_source_ref),
            "readiness_ref": dict(self.readiness_ref),
            "lineage_flags": {
                "retained_refs_are_lineage_only": True,
                "intake_is_support_authority": False,
                "intake_is_answer_authority": False,
                "intake_is_source_obligation_authority": False,
                "intake_is_citation_authority": False,
                "downstream_product_consumption_required": True,
            },
            "closed_surface_flags": dict(_CLOSED_SURFACE_FALSE_FLAGS),
        }

    def status_ref(self) -> dict[str, Any]:
        source_ref = _safe_mapping(self.source_obligation_ref)
        component_ref = _safe_mapping(self.answer_component_ref)
        question_ref = _safe_mapping(self.question_ref)
        evidence_ref = _safe_mapping(self.evidence_source_ref)
        return _without_empty(
            {
                "status": DPRIME_ANALYST_RELATION_INTAKE_STATUS_CONSUMED,
                "runtime_surface": DPRIME_ANALYST_RELATION_INTAKE_SURFACE,
                "relation_intake_id": self.relation_id,
                "relation_intake_digest": self.relation_digest,
                "relation_kind": self.relation_kind,
                "single_lane_only": True,
                "question_digest": question_ref.get("question_digest"),
                "component_id": component_ref.get("component_id"),
                "component_label": component_ref.get("component_label"),
                "component_revision": component_ref.get("component_revision"),
                "component_digest": component_ref.get("component_digest"),
                "source_obligation_candidate_ids": list(
                    _text_tuple(source_ref.get("source_obligation_candidate_ids"))
                ),
                "evidence_candidate_id": evidence_ref.get("candidate_id"),
                "evidence_reference_id": evidence_ref.get("reference_id"),
                "source_title": evidence_ref.get("source_title"),
                "source_domain": evidence_ref.get("source_domain"),
                "source_url": evidence_ref.get("source_url"),
                "lineage_only": True,
                "support_claimed": False,
                "answer_created": False,
                "source_obligation_authority_claimed": False,
                "citation_authority_claimed": False,
                "product_correctness_claimed": False,
                "live_calls_run": False,
            }
        )


def build_dprime_analyst_relation_intake(
    *,
    query: str,
    fetch_read_content_packet: Mapping[str, Any],
    source_evidence_admission_ref: Mapping[str, Any],
    citation_source_obligation_readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
) -> DPrimeAnalystRelationIntake:
    """Build one lineage-only relation from retained product-path refs."""

    packet = _safe_mapping(fetch_read_content_packet)
    admission = _safe_mapping(source_evidence_admission_ref)
    readiness = _safe_mapping(citation_source_obligation_readiness_ref)
    component = _safe_mapping(component_ref)
    source_obligation = _safe_mapping(source_obligation_ref)
    reference = _matching_readable_reference(
        packet,
        expected_candidate_id=_clean_text(admission.get("candidate_id"), limit=320),
        expected_reference_id=_clean_text(admission.get("reference_id"), limit=320),
    )
    if not reference:
        raise DPrimeAnalystRelationIntakeError(
            "generic D-prime relation intake requires a matching readable reference"
        )

    component_id = _required_text(
        component.get("component_id") or reference.get("component_id"),
        "generic D-prime relation intake requires component_id",
    )
    if reference.get("component_id") != component_id:
        raise DPrimeAnalystRelationIntakeError(
            "generic D-prime relation component does not match retained reference"
        )
    source_ids = _text_tuple(source_obligation.get("source_obligation_candidate_ids"))
    reference_source_ids = _text_tuple(reference.get("source_obligation_candidate_ids"))
    if not source_ids:
        raise DPrimeAnalystRelationIntakeError(
            "generic D-prime relation intake requires source-obligation ids"
        )
    if source_ids != reference_source_ids:
        raise DPrimeAnalystRelationIntakeError(
            "generic D-prime relation source-obligation ids do not match retained reference"
        )
    if component.get("component_coverage_bound") is not False:
        raise DPrimeAnalystRelationIntakeError(
            "generic D-prime relation intake requires unbound component coverage"
        )
    if source_obligation.get("satisfaction_claimed") is not False:
        raise DPrimeAnalystRelationIntakeError(
            "generic D-prime relation intake requires unsatisfied source-obligation posture"
        )

    question_ref = _question_ref(query)
    component_lineage_ref = _component_lineage_ref(
        component=component,
        component_id=component_id,
        source_ids=source_ids,
    )
    source_obligation_lineage_ref = _source_obligation_lineage_ref(
        source_obligation,
        source_ids=source_ids,
    )
    evidence_source_ref = _evidence_source_ref(packet=packet, reference=reference)
    readiness_lineage_ref = _readiness_ref(readiness)
    base = {
        "schema_version": DPRIME_ANALYST_RELATION_INTAKE_SCHEMA_VERSION,
        "runtime_surface": DPRIME_ANALYST_RELATION_INTAKE_SURFACE,
        "relation_kind": DPRIME_ANALYST_RELATION_KIND,
        "single_lane_only": True,
        "question_ref": question_ref,
        "answer_component_ref": component_lineage_ref,
        "source_obligation_ref": source_obligation_lineage_ref,
        "evidence_source_ref": evidence_source_ref,
        "readiness_ref": readiness_lineage_ref,
        "lineage_only": True,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FALSE_FLAGS),
    }
    digest = _digest_json(base)
    relation_id = (
        "dprime-analyst-relation-intake:"
        f"{component_id}:{evidence_source_ref['reference_digest'][:16]}:{digest[:16]}"
    )
    return DPrimeAnalystRelationIntake(
        relation_id=relation_id,
        relation_digest=digest,
        question_ref=question_ref,
        answer_component_ref=component_lineage_ref,
        source_obligation_ref=source_obligation_lineage_ref,
        evidence_source_ref=evidence_source_ref,
        readiness_ref=readiness_lineage_ref,
    )


def component_ref_from_relation_intake(
    intake: DPrimeAnalystRelationIntake | Mapping[str, Any],
) -> dict[str, Any]:
    """Return the component lineage ref consumed by existing D-prime surfaces."""

    component = _intake_component_ref(intake)
    return _without_empty(
        {
            "component_id": component.get("component_id"),
            "component_label": component.get("component_label"),
            "component_revision": component.get("component_revision"),
            "component_digest": component.get("component_digest"),
            "component_contract_digest": component.get("component_digest"),
            "current_answer_contract_digest": component.get(
                "current_answer_contract_digest"
            ),
            "component_coverage_bound": False,
            "source_obligation_candidate_ids": list(
                _text_tuple(component.get("source_obligation_candidate_ids"))
            ),
            "relation_intake_id": _intake_ref_value(intake, "relation_id"),
            "relation_intake_digest": _intake_ref_value(intake, "relation_digest"),
            "lineage_only": True,
        }
    )


def source_obligation_ref_from_relation_intake(
    intake: DPrimeAnalystRelationIntake | Mapping[str, Any],
) -> dict[str, Any]:
    """Return the source-obligation lineage ref consumed by D-prime surfaces."""

    source = _intake_source_obligation_ref(intake)
    return _without_empty(
        {
            "source_obligation_candidate_ids": list(
                _text_tuple(source.get("source_obligation_candidate_ids"))
            ),
            "source_obligation_labels": list(
                _text_tuple(source.get("source_obligation_labels"))
            ),
            "satisfaction_claimed": False,
            "relation_intake_id": _intake_ref_value(intake, "relation_id"),
            "relation_intake_digest": _intake_ref_value(intake, "relation_digest"),
            "lineage_only": True,
        }
    )


def relation_intake_ref(
    intake: DPrimeAnalystRelationIntake | Mapping[str, Any],
) -> dict[str, Any]:
    """Return the CLI-safe relation intake proof ref."""

    if isinstance(intake, DPrimeAnalystRelationIntake):
        return intake.status_ref()
    safe = _safe_mapping(intake)
    component = _safe_mapping(safe.get("answer_component_ref"))
    source = _safe_mapping(safe.get("source_obligation_ref"))
    question = _safe_mapping(safe.get("question_ref"))
    evidence = _safe_mapping(safe.get("evidence_source_ref"))
    return _without_empty(
        {
            "status": safe.get("status")
            or DPRIME_ANALYST_RELATION_INTAKE_STATUS_CONSUMED,
            "runtime_surface": safe.get("runtime_surface")
            or DPRIME_ANALYST_RELATION_INTAKE_SURFACE,
            "relation_intake_id": safe.get("relation_id")
            or safe.get("relation_intake_id"),
            "relation_intake_digest": safe.get("relation_digest")
            or safe.get("relation_intake_digest"),
            "relation_kind": safe.get("relation_kind"),
            "single_lane_only": safe.get("single_lane_only") is True,
            "question_digest": question.get("question_digest"),
            "component_id": component.get("component_id"),
            "component_label": component.get("component_label"),
            "component_revision": component.get("component_revision"),
            "component_digest": component.get("component_digest"),
            "source_obligation_candidate_ids": list(
                _text_tuple(source.get("source_obligation_candidate_ids"))
            ),
            "evidence_candidate_id": evidence.get("candidate_id"),
            "evidence_reference_id": evidence.get("reference_id"),
            "source_title": evidence.get("source_title"),
            "source_domain": evidence.get("source_domain"),
            "source_url": evidence.get("source_url"),
            "lineage_only": True,
            "support_claimed": False,
            "answer_created": False,
            "source_obligation_authority_claimed": False,
            "citation_authority_claimed": False,
            "product_correctness_claimed": False,
            "live_calls_run": False,
        }
    )


def _question_ref(query: str) -> dict[str, Any]:
    question_text = _required_text(query, "generic D-prime relation intake requires query")
    return {
        "question_text": question_text,
        "question_digest": _digest_json({"question_text": question_text}),
        "lineage_only": True,
    }


def _component_lineage_ref(
    *,
    component: Mapping[str, Any],
    component_id: str,
    source_ids: Sequence[str],
) -> dict[str, Any]:
    contract_digest = _clean_text(component.get("current_answer_contract_digest"), limit=128)
    component_digest = (
        _clean_text(component.get("component_digest"), limit=128)
        or _clean_text(component.get("component_contract_digest"), limit=128)
        or _digest_json(
            {
                "component_id": component_id,
                "current_answer_contract_digest": contract_digest,
                "source_obligation_candidate_ids": list(source_ids),
            }
        )
    )
    return _without_empty(
        {
            "component_id": component_id,
            "component_label": (
                _clean_text(component.get("component_label"), limit=260)
                or _clean_text(component.get("user_facing_label"), limit=260)
                or _label_from_component_id(component_id)
            ),
            "component_revision": (
                _clean_text(component.get("component_revision"), limit=160)
                or "dprime-generic-single-relation-1"
            ),
            "component_digest": component_digest,
            "current_answer_contract_digest": contract_digest,
            "source_obligation_candidate_ids": list(source_ids),
            "component_coverage_bound": False,
            "lineage_only": True,
        }
    )


def _source_obligation_lineage_ref(
    source_obligation: Mapping[str, Any],
    *,
    source_ids: Sequence[str],
) -> dict[str, Any]:
    return _without_empty(
        {
            "source_obligation_candidate_ids": list(source_ids),
            "source_obligation_labels": list(
                _text_tuple(source_obligation.get("source_obligation_labels"))
            ),
            "satisfaction_claimed": False,
            "lineage_only": True,
        }
    )


def _evidence_source_ref(
    *,
    packet: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    source_url = (
        reference.get("resolved_url")
        or reference.get("final_url")
        or reference.get("canonical_url")
        or reference.get("candidate_url")
    )
    return _without_empty(
        {
            "fetch_read_content_packet_id": packet.get("packet_id"),
            "fetch_read_content_packet_digest": packet.get("packet_digest"),
            "candidate_id": reference.get("candidate_id"),
            "candidate_digest": reference.get("candidate_digest"),
            "reference_id": reference.get("reference_id"),
            "reference_digest": reference.get("reference_digest"),
            "source_title": reference.get("content_title")
            or reference.get("candidate_title"),
            "source_domain": reference.get("resolved_domain")
            or reference.get("candidate_domain"),
            "source_url": source_url,
            "bounded_content_digest": reference.get("excerpt_digest"),
            "bounded_character_count": reference.get("bounded_character_count"),
            "fetch_read_status": reference.get("fetch_read_status"),
            "lineage_only": True,
            "bounded_content_not_retained_in_status": True,
        }
    )


def _readiness_ref(readiness: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "posture": readiness.get("posture"),
            "next_blocked_surface": readiness.get("next_blocked_surface"),
            "lineage_only": True,
        }
    )


def _matching_readable_reference(
    packet: Mapping[str, Any],
    *,
    expected_candidate_id: str | None,
    expected_reference_id: str | None,
) -> dict[str, Any]:
    if not expected_candidate_id or not expected_reference_id:
        return {}
    for item in _safe_sequence(packet.get("reference_records")):
        reference = _safe_mapping(item)
        if reference.get("fetch_read_status") != "readable":
            continue
        if reference.get("candidate_id") != expected_candidate_id:
            continue
        if reference.get("reference_id") != expected_reference_id:
            continue
        return reference
    return {}


def _intake_component_ref(
    intake: DPrimeAnalystRelationIntake | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(intake, DPrimeAnalystRelationIntake):
        return dict(intake.answer_component_ref)
    return _safe_mapping(_safe_mapping(intake).get("answer_component_ref"))


def _intake_source_obligation_ref(
    intake: DPrimeAnalystRelationIntake | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(intake, DPrimeAnalystRelationIntake):
        return dict(intake.source_obligation_ref)
    return _safe_mapping(_safe_mapping(intake).get("source_obligation_ref"))


def _intake_ref_value(
    intake: DPrimeAnalystRelationIntake | Mapping[str, Any],
    key: str,
) -> Any:
    if isinstance(intake, DPrimeAnalystRelationIntake):
        return getattr(intake, key)
    return _safe_mapping(intake).get(key)


def _label_from_component_id(component_id: str) -> str:
    normalized = component_id.removeprefix("component:")
    normalized = normalized.replace("-", " ").replace("_", " ").strip()
    return normalized or component_id


def _required_text(value: Any, message: str, *, limit: int = 500) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        raise DPrimeAnalystRelationIntakeError(message)
    return text


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


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


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    return value


__all__ = [
    "DPRIME_ANALYST_RELATION_INTAKE_SCHEMA_VERSION",
    "DPRIME_ANALYST_RELATION_INTAKE_STATUS_CONSUMED",
    "DPRIME_ANALYST_RELATION_INTAKE_SURFACE",
    "DPRIME_ANALYST_RELATION_KIND",
    "DPrimeAnalystRelationIntake",
    "DPrimeAnalystRelationIntakeError",
    "build_dprime_analyst_relation_intake",
    "component_ref_from_relation_intake",
    "relation_intake_ref",
    "source_obligation_ref_from_relation_intake",
]
