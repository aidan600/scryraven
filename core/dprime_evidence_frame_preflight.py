"""Deterministic D-prime evidence-frame preflight.

This module verifies retained evidence-frame eligibility only. It consumes
already-retained, sanitized fetch/read and readiness refs, emits only refs and
digests, and does not create semantic support, model review, assessment,
proposal validation, RunKernel admission, SemanticObservation, ComponentCoverage,
citation eligibility, answer text, or product-correctness claims.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.dprime_support_proposal_schema import EvidenceFramePreflight
from core.fetch_read_content_reference import (
    FetchReadContentReferenceError,
    fetch_read_content_packet_ref_from_packet,
    validate_fetch_read_content_packet,
)

DPRIME_PREFLIGHT_PHASE = "DPRIME-PREFLIGHT-01"

_PACKET_REFERENCE_FALSE_FLAGS = frozenset(
    {
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "raw_page_content_retained",
        "raw_page_text_retained",
        "raw_headers_retained",
        "raw_prompt_retained",
        "evidence_ledger_admitted",
        "citation_created",
        "citation_eligible",
        "source_obligation_satisfied",
        "semantic_observation_created",
        "analyst_report_created",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "partial_answer_ready",
        "product_correctness_claimed",
    }
)
_ADMISSION_FALSE_FLAGS = frozenset(
    {
        "candidate_content_custody_is_semantic_support",
        "citation_eligible",
        "source_obligation_satisfied",
        "source_obligation_candidate_ids_satisfy_requirements",
        "component_coverage_created",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "partial_answer_ready",
        "product_correctness_claimed",
    }
)
_RAW_PRIVATE_FALSE_FLAGS = frozenset(
    {
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "raw_page_content_retained",
        "raw_page_text_retained",
        "raw_headers_retained",
        "raw_prompt_retained",
        "headers_retained",
        "page_content_retained",
        "page_html_retained",
        "page_text_retained",
        "private_material_retained",
        "prompt_retained",
        "provider_payload_retained",
        "search_response_retained",
        "unbounded_page_material_retained",
    }
)


def build_evidence_frame_preflight(
    *,
    fetch_read_content_packet: Mapping[str, Any] | None,
    source_evidence_admission_ref: Mapping[str, Any],
    citation_source_obligation_readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    relation_intake_ref: Mapping[str, Any] | None = None,
) -> EvidenceFramePreflight:
    """Return deterministic D-prime preflight status for one retained lane."""

    packet = _safe_mapping(fetch_read_content_packet)
    if not packet:
        return _failed("fetch/read packet is missing")

    admission = _safe_mapping(source_evidence_admission_ref)
    readiness = _safe_mapping(citation_source_obligation_readiness_ref)
    component = _safe_mapping(component_ref)
    source_obligation = _safe_mapping(source_obligation_ref)
    relation_intake = _safe_mapping(relation_intake_ref)

    reference = _matching_readable_reference(
        packet,
        expected_candidate_id=_clean_text(admission.get("candidate_id"), limit=320),
        expected_reference_id=_clean_text(admission.get("reference_id"), limit=320),
    )
    if not reference:
        return _failed("matching readable content reference is missing")

    structural_blocker = _first_structural_blocker(
        packet=packet,
        reference=reference,
        admission=admission,
        readiness=readiness,
        component=component,
        source_obligation=source_obligation,
        relation_intake=relation_intake,
    )
    if structural_blocker:
        return _failed(structural_blocker)

    try:
        validated_packet = validate_fetch_read_content_packet(packet)
    except FetchReadContentReferenceError as exc:
        return _failed(f"fetch/read packet validation failed: {exc}")

    validated_reference = _matching_readable_reference(
        validated_packet,
        expected_candidate_id=_clean_text(admission.get("candidate_id"), limit=320),
        expected_reference_id=_clean_text(admission.get("reference_id"), limit=320),
    )
    if not validated_reference:
        return _failed("validated fetch/read packet lost the retained reference")

    frame_ref_base = _without_empty(
        {
            "frame_kind": "dprime_evidence_frame_preflight",
            "phase": DPRIME_PREFLIGHT_PHASE,
            "fetch_read_packet_ref": fetch_read_content_packet_ref_from_packet(
                validated_packet
            ),
            "source_evidence_custody_ref": _source_evidence_custody_ref(
                admission
            ),
            "readiness_posture_ref": _readiness_posture_ref(readiness),
            "content_reference_ref": _content_reference_ref(validated_reference),
            "component_binding_ref": _component_binding_ref(component),
            "source_obligation_lane_ref": _source_obligation_lane_ref(
                source_obligation
            ),
            "relation_intake_ref": _relation_intake_status_ref(relation_intake),
            "selector_ref": _selector_ref(validated_reference),
            "model_browse_allowed": False,
            "downstream_surfaces_closed": True,
            "identity_fields_are_not_support": True,
            "frame_eligibility_only": True,
        }
    )
    frame_digest = _digest_json(frame_ref_base)
    frame_ref = {
        **frame_ref_base,
        "frame_id": (
            "dprime-evidence-frame-preflight:"
            f"{_clean_text(validated_reference.get('reference_id'), limit=120)}:"
            f"{frame_digest[:16]}"
        ),
        "frame_digest": frame_digest,
    }
    return EvidenceFramePreflight(
        frame_ref=frame_ref,
        preflight_status="passed",
        metadata={
            "phase": DPRIME_PREFLIGHT_PHASE,
            "ordinary_runtime_consumer": "proplex.live_semantic_coverage_status",
            "preflight_authority": "deterministic frame eligibility only",
            "model_browse_allowed": False,
        },
    )


def _first_structural_blocker(
    *,
    packet: Mapping[str, Any],
    reference: Mapping[str, Any],
    admission: Mapping[str, Any],
    readiness: Mapping[str, Any],
    component: Mapping[str, Any],
    source_obligation: Mapping[str, Any],
    relation_intake: Mapping[str, Any],
) -> str | None:
    for context, value, flags in (
        ("fetch/read packet", packet, _PACKET_REFERENCE_FALSE_FLAGS),
        ("sanitized content reference", reference, _PACKET_REFERENCE_FALSE_FLAGS),
        ("source/evidence custody ref", admission, _ADMISSION_FALSE_FLAGS),
    ):
        blocker = _required_false_flag_blocker(context, value, flags)
        if blocker:
            return blocker
        blocker = _nested_false_flag_blocker(context, value, _RAW_PRIVATE_FALSE_FLAGS)
        if blocker:
            return blocker

    boundary_blocker = _nested_false_flag_blocker(
        "source/evidence custody behavior flags",
        _safe_mapping(admission.get("behavior_boundary_flags")),
        _ADMISSION_FALSE_FLAGS,
    )
    if boundary_blocker:
        return boundary_blocker

    if admission.get("status") != "custody_created":
        return "EvidenceLedger/source-evidence custody ref is missing"
    if packet.get("packet_id") != admission.get("fetch_read_content_packet_id"):
        return "fetch/read packet id does not match custody/admission ref"
    if packet.get("packet_digest") != admission.get("fetch_read_content_packet_digest"):
        return "fetch/read packet digest does not match custody/admission ref"
    for key in ("candidate_id", "reference_id", "reference_digest"):
        if _clean_text(reference.get(key), limit=320) != _clean_text(
            admission.get(key),
            limit=320,
        ):
            return f"content reference {key} does not match custody/admission ref"

    if not _clean_text(reference.get("component_id"), limit=260):
        return "retained content component is missing"
    if component.get("component_id") != reference.get("component_id"):
        return "component ref does not match retained content component"
    if component.get("component_coverage_bound") is not False:
        return "closed downstream surface flag not false: component_coverage_bound"

    reference_source_ids = _text_tuple(
        reference.get("source_obligation_candidate_ids"),
        limit=260,
    )
    readiness_source_ids = _text_tuple(
        source_obligation.get("source_obligation_candidate_ids"),
        limit=260,
    )
    if not reference_source_ids:
        return "retained content source-obligation lane is missing"
    if readiness_source_ids != reference_source_ids:
        return "source-obligation ref does not match retained content lane"
    if source_obligation.get("satisfaction_claimed") is not False:
        return "closed downstream surface flag not false: satisfaction_claimed"
    relation_blocker = _relation_intake_blocker(
        relation_intake=relation_intake,
        component=component,
        source_obligation=source_obligation,
        reference=reference,
    )
    if relation_blocker:
        return relation_blocker

    if readiness.get("posture") != "not_yet_semantically_supported":
        return "source-obligation readiness posture is not pre-support"

    contract_digest = _clean_text(
        reference.get("current_answer_contract_digest"),
        limit=128,
    )
    if not contract_digest:
        return "current answer contract digest/ref is missing"
    if packet.get("current_answer_contract_digest") != contract_digest:
        return "current answer contract digest/ref mismatches fetch/read packet"
    if component.get("current_answer_contract_digest") != contract_digest:
        return "current answer contract digest/ref mismatches component ref"
    contract_ref = _safe_mapping(reference.get("current_answer_contract_ref"))
    if contract_ref.get("contract_digest") != contract_digest:
        return "current answer contract digest/ref mismatches content reference"

    bounded_blocker = _bounded_content_blocker(reference)
    if bounded_blocker:
        return bounded_blocker
    return _selector_blocker(reference)


def _bounded_content_blocker(reference: Mapping[str, Any]) -> str | None:
    if reference.get("bounded_text_sanitized") is not True:
        return "bounded sanitized content is missing"
    if reference.get("bounded_text_bounded") is not True:
        return "bounded sanitized content is not bounded"
    if not _clean_raw_text(reference.get("bounded_text")):
        return "bounded sanitized content is missing"
    bounded_count = _optional_int(reference.get("bounded_character_count"))
    if not bounded_count:
        return "bounded sanitized content count is missing"
    if not _clean_text(reference.get("excerpt_digest"), limit=128):
        return "bounded content digest is missing"
    return None


def _selector_blocker(reference: Mapping[str, Any]) -> str | None:
    bounded_count = _optional_int(reference.get("bounded_character_count"))
    bounded_digest = _clean_text(reference.get("excerpt_digest"), limit=128)
    selection = _safe_mapping(reference.get("bounded_text_selection"))
    if not selection:
        if bounded_count and bounded_digest:
            return None
        return "selector/span surrogate is missing bounded digest/count"
    if selection.get("bounded_text_digest") != bounded_digest:
        return "selector/span digest does not match retained bounded content"
    if _optional_int(selection.get("bounded_text_char_count")) != bounded_count:
        return "selector/span count does not match retained bounded content"
    start = _optional_int(selection.get("selected_window_start_offset"))
    end = _optional_int(selection.get("selected_window_end_offset"))
    if start is None or end is None or start < 0 or end < start:
        return "selector/span is missing, unbounded, or outside the retained content"
    if end - start != bounded_count:
        return "selector/span is not bounded to the retained content count"
    for key in (
        "anti_anchor_laundering_passed",
        "not_semantic_support",
        "not_citation_eligible",
        "not_source_obligation_satisfied",
    ):
        if selection.get(key) is not True:
            return f"selector/span closed-surface flag is not true: {key}"
    return None


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


def _source_evidence_custody_ref(admission: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "status": admission.get("status"),
            "owner": admission.get("owner"),
            "schema_version": admission.get("schema_version"),
            "custody_ref_digest": admission.get("ref_digest"),
            "ledger_observation_id": admission.get("observation_id"),
            "fetch_read_packet_id": admission.get("fetch_read_content_packet_id"),
            "fetch_read_packet_digest": admission.get(
                "fetch_read_content_packet_digest"
            ),
            "candidate_id": admission.get("candidate_id"),
            "reference_id": admission.get("reference_id"),
            "reference_digest": admission.get("reference_digest"),
            "custody_record_count": admission.get("custody_record_count"),
            "readable_record_count": admission.get("readable_record_count"),
        }
    )


def _readiness_posture_ref(readiness: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "posture": readiness.get("posture"),
            "next_blocked_surface": readiness.get("next_blocked_surface"),
        }
    )


def _content_reference_ref(reference: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "reference_id": reference.get("reference_id"),
            "reference_digest": reference.get("reference_digest"),
            "candidate_id": reference.get("candidate_id"),
            "candidate_digest": reference.get("candidate_digest"),
            "candidate_record_digest": reference.get(
                "search_result_candidate_record_digest"
            ),
            "bounded_content_digest": reference.get("excerpt_digest"),
            "bounded_character_count": reference.get("bounded_character_count"),
            "fetch_read_status": reference.get("fetch_read_status"),
        }
    )


def _component_binding_ref(component: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "component_id": component.get("component_id"),
            "current_contract_digest": component.get(
                "current_answer_contract_digest"
            ),
            "lineage_only": True,
        }
    )


def _source_obligation_lane_ref(source_obligation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_obligation_candidate_ids": _text_tuple(
            source_obligation.get("source_obligation_candidate_ids"),
            limit=260,
        ),
        "lineage_only": True,
    }


def _relation_intake_blocker(
    *,
    relation_intake: Mapping[str, Any],
    component: Mapping[str, Any],
    source_obligation: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> str | None:
    if not relation_intake:
        return None
    if relation_intake.get("single_lane_only") is not True:
        return "generic D-prime relation intake is not single-lane"
    component_id = _clean_text(relation_intake.get("component_id"), limit=260)
    if component_id and component_id != component.get("component_id"):
        return "generic D-prime relation intake component mismatch"
    if component_id and component_id != reference.get("component_id"):
        return "generic D-prime relation intake retained reference mismatch"
    relation_source_ids = _text_tuple(
        relation_intake.get("source_obligation_candidate_ids"),
        limit=260,
    )
    source_ids = _text_tuple(
        source_obligation.get("source_obligation_candidate_ids"),
        limit=260,
    )
    if relation_source_ids and relation_source_ids != source_ids:
        return "generic D-prime relation intake source-obligation mismatch"
    for key in (
        "support_claimed",
        "answer_created",
        "source_obligation_authority_claimed",
        "citation_authority_claimed",
        "product_correctness_claimed",
        "live_calls_run",
    ):
        if relation_intake.get(key) is not False:
            return f"generic D-prime relation intake opened closed surface: {key}"
    return None


def _relation_intake_status_ref(relation_intake: Mapping[str, Any]) -> dict[str, Any]:
    if not relation_intake:
        return {}
    return _without_empty(
        {
            "relation_intake_id": relation_intake.get("relation_intake_id")
            or relation_intake.get("relation_id"),
            "relation_intake_digest": relation_intake.get("relation_intake_digest")
            or relation_intake.get("relation_digest"),
            "relation_kind": relation_intake.get("relation_kind"),
            "single_lane_only": relation_intake.get("single_lane_only") is True,
            "component_id": relation_intake.get("component_id"),
            "source_obligation_candidate_ids": list(
                _text_tuple(
                    relation_intake.get("source_obligation_candidate_ids"),
                    limit=260,
                )
            ),
            "lineage_only": True,
        }
    )


def _selector_ref(reference: Mapping[str, Any]) -> dict[str, Any]:
    bounded_count = _optional_int(reference.get("bounded_character_count")) or 0
    bounded_digest = _clean_text(reference.get("excerpt_digest"), limit=128)
    selection = _safe_mapping(reference.get("bounded_text_selection"))
    if selection:
        return _without_empty(
            {
                "selector_kind": "bounded_selection_metadata",
                "bounded_content_digest": bounded_digest,
                "bounded_character_count": bounded_count,
                "selected_window_start_offset": selection.get(
                    "selected_window_start_offset"
                ),
                "selected_window_end_offset": selection.get(
                    "selected_window_end_offset"
                ),
                "local_context_posture": selection.get("local_context_posture"),
                "selector_not_semantic_support": True,
            }
        )
    return _without_empty(
        {
            "selector_kind": "bounded_digest_count_surrogate",
            "bounded_content_digest": bounded_digest,
            "bounded_character_count": bounded_count,
            "surrogate_source": "SanitizedContentReference digest/count metadata",
            "surrogate_reason": (
                "retained packet exposes bounded content digest/count but no "
                "richer selector object"
            ),
            "selector_not_semantic_support": True,
        }
    )


def _required_false_flag_blocker(
    context: str,
    value: Mapping[str, Any],
    flags: frozenset[str],
) -> str | None:
    for key in sorted(flags):
        if value.get(key) is not False:
            category = (
                "raw/private retained flag"
                if key in _RAW_PRIVATE_FALSE_FLAGS
                else "closed downstream surface flag"
            )
            return f"{category} not false in {context}: {key}"
    return None


def _nested_false_flag_blocker(
    context: str,
    value: Any,
    flags: frozenset[str],
) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in flags and item is not False:
                category = (
                    "raw/private retained flag"
                    if normalized in _RAW_PRIVATE_FALSE_FLAGS
                    else "closed downstream surface flag"
                )
                return f"{category} true in {context}: {normalized}"
            blocker = _nested_false_flag_blocker(context, item, flags)
            if blocker:
                return blocker
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            blocker = _nested_false_flag_blocker(context, item, flags)
            if blocker:
                return blocker
    return None


def _failed(reason: str) -> EvidenceFramePreflight:
    clean = _clean_text(reason, limit=260) or "D-prime preflight failed"
    return EvidenceFramePreflight(
        frame_ref={
            "frame_kind": "dprime_evidence_frame_preflight",
            "phase": DPRIME_PREFLIGHT_PHASE,
            "failed_check": clean,
            "frame_eligibility_only": True,
            "model_browse_allowed": False,
        },
        preflight_status="failed",
        blockers=(clean,),
        metadata={
            "phase": DPRIME_PREFLIGHT_PHASE,
            "ordinary_runtime_consumer": "proplex.live_semantic_coverage_status",
            "preflight_authority": "deterministic frame eligibility only",
            "model_browse_allowed": False,
        },
    )


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


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _clean_raw_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "DPRIME_PREFLIGHT_PHASE",
    "build_evidence_frame_preflight",
]
