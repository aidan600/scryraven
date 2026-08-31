"""Canonical exact Component Analyst evidence-set mechanics.

The set is code-owned.  Its model projection contains only bounded evidence
content and packet-local aliases; canonical custody identity remains inside the
same set for mechanical verification and admission binding.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from core.multicomponent_role_runtime import safe_packet_digest

COMPONENT_ANALYST_EVIDENCE_SET_SCHEMA_VERSION = (
    "component_analyst_evidence_set_v1"
)
COMPONENT_ANALYST_EVIDENCE_ALIAS_PREFIX = "component_evidence_"


class ComponentAnalystEvidenceSetError(ValueError):
    """Raised when the exact code-owned component evidence set is invalid."""


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any, *, limit: int = 1_000) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _structured_evidence_fact(
    *,
    candidate: Mapping[str, Any],
    passage: Mapping[str, Any],
    candidate_keys: Sequence[str],
    passage_keys: Sequence[str],
    limit: int = 160,
) -> str | None:
    for owner, keys in ((candidate, candidate_keys), (passage, passage_keys)):
        for key in keys:
            value = _clean_text(owner.get(key), limit=limit)
            if value and value.casefold() != "unknown":
                return value
    return None


def _exact_conflict_facts(
    *, candidate: Mapping[str, Any], passage: Mapping[str, Any]
) -> tuple[str | None, bool | None]:
    for owner in (candidate, passage):
        conflict = _clean_text(owner.get("conflict_posture"), limit=80)
        if conflict and conflict.casefold() != "unknown":
            return conflict, conflict.casefold() == "present"
        contradictory = owner.get("contradictory")
        if isinstance(contradictory, bool):
            return ("present" if contradictory else "none"), contradictory
        disposition = _clean_text(
            owner.get("fact_disposition") or owner.get("disposition"),
            limit=80,
        )
        if disposition and disposition.casefold() in {"contradicted", "contested"}:
            return "present", True
    return None, None


def _exact_currency_fact(
    *, candidate: Mapping[str, Any], passage: Mapping[str, Any]
) -> str | None:
    for owner in (candidate, passage):
        value = owner.get("canonical_currency_unit")
        if isinstance(value, str):
            token = value.strip()
            if len(token) == 3 and token.isascii() and token.isalpha():
                return token.upper()
    return None


def _candidate_custody_ref(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: candidate.get(key)
        for key in (
            "candidate_id",
            "source_class",
            "source_tier",
            "fact_disposition",
            "readable_status",
            "currentness_signal",
            "conflict_posture",
            "contradictory",
            "canonical_currency_unit",
        )
        if candidate.get(key) is not None
    }


def _code_material_identity(
    *, passage: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    """Keep the internal identity facts required for exact reconstruction."""

    # A SearchOS slot is a live state record.  Its full serialized shape can
    # legitimately acquire reducer bookkeeping after the handoff without
    # changing the handed-off material.  Bind the immutable handoff facts
    # instead; current-slot equality itself is checked against RunKernel state
    # at the receiver/admission boundary.
    slot_ref = _safe_mapping(passage.get("searchos_slot_ref"))
    lineage = _safe_mapping(passage.get("searchos_qualification_lineage"))
    lineage_slot_ref = _safe_mapping(lineage.get("slot_ref"))
    canonical_slot_ref = slot_ref or lineage_slot_ref
    handoff_ref = _safe_mapping(passage.get("searchos_semantic_handoff_ref"))
    lineage_handoff_ref = _safe_mapping(lineage.get("semantic_handoff_ref"))
    canonical_handoff_ref = handoff_ref or lineage_handoff_ref
    custody_ref = _safe_mapping(lineage.get("read_custody_ref"))

    return {
        "candidate_identity": {
            key: deepcopy(candidate.get(key))
            for key in (
                "candidate_id",
                "candidate_digest",
                "candidate_record_digest",
            )
            if candidate.get(key) is not None
        },
        "material_identity": {
            "candidate_id": passage.get("candidate_id"),
            "material_authority": passage.get("material_authority"),
            "provider": passage.get("_provider"),
            "searchos_slot_identity": {
                key: deepcopy(canonical_slot_ref.get(key))
                for key in (
                    "slot_id",
                    "component_id",
                    "source_obligation_id",
                    "recovery_cycle_id",
                )
                if canonical_slot_ref.get(key) is not None
            },
            "searchos_semantic_handoff_ref": {
                key: deepcopy(canonical_handoff_ref.get(key))
                for key in (
                    "semantic_handoff_id",
                    "semantic_handoff_digest",
                )
                if canonical_handoff_ref.get(key) is not None
            },
            "searchos_read_custody_ref": {
                key: deepcopy(custody_ref.get(key))
                for key in (
                    "read_custody_material_id",
                    "read_custody_material_digest",
                    "bounded_text_digest",
                )
                if custody_ref.get(key) is not None
            },
            "searchos_canonical_candidate_id": lineage.get(
                "canonical_candidate_id"
            ),
        },
    }


def _member_alias(index: int) -> str:
    return f"{COMPONENT_ANALYST_EVIDENCE_ALIAS_PREFIX}{index:02d}"


def _member_model_evidence(
    *, passage: Mapping[str, Any], candidate: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    bounded_text = _clean_text(passage.get("text"), limit=6_000)
    if not bounded_text:
        raise ComponentAnalystEvidenceSetError(
            "component evidence member lacks bounded text"
        )
    supplied_digest = _clean_text(passage.get("bounded_text_digest"), limit=128)
    bounded_text_digest = safe_packet_digest({"bounded_text": bounded_text})
    if supplied_digest and supplied_digest != bounded_text_digest:
        raise ComponentAnalystEvidenceSetError(
            "component evidence member bounded-text digest mismatch"
        )
    source_class = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("source_class",),
        passage_keys=("source_class",),
    )
    source_tier = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("source_tier",),
        passage_keys=("source_tier",),
    )
    currentness = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("currentness_signal", "currentness"),
        passage_keys=("currentness_signal", "currentness"),
    )
    fact_disposition = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("fact_disposition", "disposition"),
        passage_keys=("fact_disposition", "disposition"),
        limit=80,
    )
    readability = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("readable_status", "readability_status"),
        passage_keys=("readable_status", "readability_status"),
        limit=80,
    )
    conflict, contradictory = _exact_conflict_facts(
        candidate=candidate,
        passage=passage,
    )
    model_evidence: dict[str, Any] = {
        "evidence_status": "available",
        "source_title": _clean_text(passage.get("title"), limit=240),
        "source_url": _clean_text(passage.get("url"), limit=500),
        "bounded_text": bounded_text,
        "currentness": currentness,
        "source_class": source_class,
        "source_tier": source_tier,
        "fact_disposition": fact_disposition,
        "readability_posture": readability,
        "conflict_posture": conflict,
        "canonical_currency_unit": _exact_currency_fact(
            candidate=candidate,
            passage=passage,
        ),
    }
    if contradictory is not None:
        model_evidence["contradictory"] = contradictory
    return model_evidence, {
        "bounded_text_digest": bounded_text_digest,
        "candidate_custody_ref": _candidate_custody_ref(candidate),
    }


def build_component_analyst_evidence_set(
    members: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build one ordered exact set from code-owned evidence members.

    Each source member must provide the existing code-owned `evidence_ref_id`,
    `passage`, and `candidate_record` values.  The returned representation is
    the only canonical evidence-set object; the model packet is a derived safe
    projection of it.
    """

    if isinstance(members, str | bytes) or not isinstance(members, Sequence):
        raise ComponentAnalystEvidenceSetError(
            "component evidence set members must be an ordered sequence"
        )
    if not members:
        raise ComponentAnalystEvidenceSetError(
            "component evidence set requires one or more members"
        )
    built: list[dict[str, Any]] = []
    evidence_ids: set[str] = set()
    custody_ids: set[str] = set()
    for index, raw_member in enumerate(members, start=1):
        raw = _safe_mapping(raw_member)
        evidence_ref_id = _clean_text(raw.get("evidence_ref_id"), limit=320)
        passage = _safe_mapping(raw.get("passage"))
        candidate = _safe_mapping(raw.get("candidate_record"))
        candidate_id = _clean_text(candidate.get("candidate_id"), limit=320)
        if (
            not evidence_ref_id
            or not passage
            or not candidate
            or candidate_id != evidence_ref_id
        ):
            raise ComponentAnalystEvidenceSetError(
                "component evidence member canonical identity is incomplete"
            )
        if evidence_ref_id in evidence_ids:
            raise ComponentAnalystEvidenceSetError(
                "component evidence set repeats canonical evidence identity"
            )
        model_evidence, mechanical = _member_model_evidence(
            passage=passage,
            candidate=candidate,
        )
        lineage = _safe_mapping(passage.get("searchos_qualification_lineage"))
        custody = _safe_mapping(lineage.get("read_custody_ref"))
        custody_id = _clean_text(custody.get("read_custody_material_id"), limit=320)
        if custody_id:
            if custody_id in custody_ids:
                raise ComponentAnalystEvidenceSetError(
                    "component evidence set repeats custody material identity"
                )
            custody_ids.add(custody_id)
        evidence_ids.add(evidence_ref_id)
        built.append(
            {
                "local_evidence_alias": _member_alias(index),
                "code_binding": {
                    "evidence_ref_id": evidence_ref_id,
                    **mechanical,
                    **_code_material_identity(
                        passage=passage,
                        candidate=candidate,
                    ),
                },
                "model_evidence": model_evidence,
                "passage": deepcopy(passage),
                "candidate_record": deepcopy(candidate),
            }
        )
    core = {
        "schema_version": COMPONENT_ANALYST_EVIDENCE_SET_SCHEMA_VERSION,
        "members": built,
    }
    identity_core = {
        "schema_version": COMPONENT_ANALYST_EVIDENCE_SET_SCHEMA_VERSION,
        "members": [
            {
                "local_evidence_alias": item["local_evidence_alias"],
                "code_binding": item["code_binding"],
                "model_evidence": item["model_evidence"],
            }
            for item in built
        ],
    }
    return {
        **core,
        "evidence_set_digest": safe_packet_digest(identity_core),
    }


def validate_component_analyst_evidence_set(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate canonical membership, content integrity, and packet aliases."""

    safe = _safe_mapping(value)
    if set(safe) != {"schema_version", "members", "evidence_set_digest"}:
        raise ComponentAnalystEvidenceSetError(
            "component evidence set field shape is invalid"
        )
    if safe.get("schema_version") != COMPONENT_ANALYST_EVIDENCE_SET_SCHEMA_VERSION:
        raise ComponentAnalystEvidenceSetError(
            "component evidence set schema version is invalid"
        )
    raw_members = safe.get("members")
    if isinstance(raw_members, str | bytes) or not isinstance(raw_members, Sequence):
        raise ComponentAnalystEvidenceSetError(
            "component evidence set members are invalid"
        )
    rebuilt_sources: list[dict[str, Any]] = []
    for index, raw_member in enumerate(raw_members, start=1):
        member = _safe_mapping(raw_member)
        if set(member) != {
            "local_evidence_alias",
            "code_binding",
            "model_evidence",
            "passage",
            "candidate_record",
        }:
            raise ComponentAnalystEvidenceSetError(
                "component evidence set member field shape is invalid"
            )
        alias = _clean_text(member.get("local_evidence_alias"), limit=80)
        code_binding = _safe_mapping(member.get("code_binding"))
        passage = _safe_mapping(member.get("passage"))
        candidate = _safe_mapping(member.get("candidate_record"))
        model_evidence = _safe_mapping(member.get("model_evidence"))
        expected_alias = _member_alias(index)
        if alias != expected_alias or set(code_binding) != {
            "evidence_ref_id",
            "bounded_text_digest",
            "candidate_custody_ref",
            "candidate_identity",
            "material_identity",
        }:
            raise ComponentAnalystEvidenceSetError(
                "component evidence set member binding shape is invalid"
            )
        rebuilt_sources.append(
            {
                "evidence_ref_id": code_binding.get("evidence_ref_id"),
                "passage": passage,
                "candidate_record": candidate,
            }
        )
        expected_model, expected_mechanical = _member_model_evidence(
            passage=passage,
            candidate=candidate,
        )
        expected_identity = _code_material_identity(
            passage=passage,
            candidate=candidate,
        )
        if (
            model_evidence != expected_model
            or code_binding.get("bounded_text_digest")
            != expected_mechanical["bounded_text_digest"]
            or _safe_mapping(code_binding.get("candidate_custody_ref"))
            != expected_mechanical["candidate_custody_ref"]
            or _safe_mapping(code_binding.get("candidate_identity"))
            != expected_identity["candidate_identity"]
            or _safe_mapping(code_binding.get("material_identity"))
            != expected_identity["material_identity"]
        ):
            raise ComponentAnalystEvidenceSetError(
                "component evidence set member content or custody binding is altered"
            )
    rebuilt = build_component_analyst_evidence_set(rebuilt_sources)
    if safe != rebuilt:
        raise ComponentAnalystEvidenceSetError(
            "component evidence set canonical order or identity is altered"
        )
    return deepcopy(rebuilt)


def validate_component_analyst_evidence_sets(
    value: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Validate one exact canonical set per Component Analyst target."""

    if not isinstance(value, Mapping) or not value:
        raise ComponentAnalystEvidenceSetError(
            "component evidence sets require one exact set per component"
        )
    result: dict[str, dict[str, Any]] = {}
    for raw_component_id, raw_evidence_set in value.items():
        component_id = _clean_text(raw_component_id, limit=320)
        if not component_id or component_id in result:
            raise ComponentAnalystEvidenceSetError(
                "component evidence set target identity is invalid or collides"
            )
        if not isinstance(raw_evidence_set, Mapping):
            raise ComponentAnalystEvidenceSetError(
                "component evidence set is malformed"
            )
        result[component_id] = validate_component_analyst_evidence_set(
            raw_evidence_set
        )
    return deepcopy(result)


def component_analyst_evidence_set_model_projection(
    evidence_set: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the only model-visible projection of the canonical set."""

    safe = validate_component_analyst_evidence_set(evidence_set)
    return {
        "schema_version": COMPONENT_ANALYST_EVIDENCE_SET_SCHEMA_VERSION,
        "member_count": len(safe["members"]),
        "members": [
            {
                "local_evidence_alias": item["local_evidence_alias"],
                **deepcopy(_safe_mapping(item.get("model_evidence"))),
            }
            for item in safe["members"]
        ],
    }


def component_analyst_evidence_set_local_aliases(
    evidence_set: Mapping[str, Any],
) -> tuple[str, ...]:
    safe = validate_component_analyst_evidence_set(evidence_set)
    return tuple(str(item["local_evidence_alias"]) for item in safe["members"])


def component_analyst_evidence_set_members_for_aliases(
    evidence_set: Mapping[str, Any],
    aliases: Sequence[str],
) -> list[dict[str, Any]]:
    """Bind Analyst-selected local aliases to exact canonical members."""

    safe = validate_component_analyst_evidence_set(evidence_set)
    if isinstance(aliases, str | bytes) or not isinstance(aliases, Sequence):
        raise ComponentAnalystEvidenceSetError(
            "component support aliases must be an ordered sequence"
        )
    normalized = [_clean_text(item, limit=80) for item in aliases]
    if not normalized or any(not item for item in normalized):
        raise ComponentAnalystEvidenceSetError(
            "component support aliases are missing"
        )
    if len(normalized) != len(set(normalized)):
        raise ComponentAnalystEvidenceSetError(
            "component support aliases repeat one supplied member"
        )
    by_alias = {
        str(item["local_evidence_alias"]): item for item in safe["members"]
    }
    if any(alias not in by_alias for alias in normalized):
        raise ComponentAnalystEvidenceSetError(
            "component support aliases include an unknown supplied member"
        )
    canonical_selected_order = [
        alias for alias in by_alias if alias in set(normalized)
    ]
    if normalized != canonical_selected_order:
        raise ComponentAnalystEvidenceSetError(
            "component support aliases must preserve supplied canonical order"
        )
    return [deepcopy(by_alias[str(alias)]) for alias in normalized]


def component_analyst_evidence_member_code_evidence(
    member: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the code-only member shape needed by custody and Specialist code."""

    item = _safe_mapping(member)
    code_binding = _safe_mapping(item.get("code_binding"))
    model_evidence = _safe_mapping(item.get("model_evidence"))
    if not item or not code_binding or not model_evidence:
        raise ComponentAnalystEvidenceSetError(
            "component evidence member is malformed"
        )
    return {
        **deepcopy(model_evidence),
        "evidence_ref_id": code_binding.get("evidence_ref_id"),
        "bounded_text_digest": code_binding.get("bounded_text_digest"),
        "candidate_custody_ref": deepcopy(
            _safe_mapping(code_binding.get("candidate_custody_ref"))
        ),
    }


__all__ = [
    "COMPONENT_ANALYST_EVIDENCE_ALIAS_PREFIX",
    "COMPONENT_ANALYST_EVIDENCE_SET_SCHEMA_VERSION",
    "ComponentAnalystEvidenceSetError",
    "build_component_analyst_evidence_set",
    "component_analyst_evidence_member_code_evidence",
    "component_analyst_evidence_set_local_aliases",
    "component_analyst_evidence_set_members_for_aliases",
    "component_analyst_evidence_set_model_projection",
    "validate_component_analyst_evidence_set",
    "validate_component_analyst_evidence_sets",
]
