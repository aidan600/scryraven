"""RunKernel-authorized FinalAnswerPacket preparation runtime for AG-91K."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.final_answer_packet import FinalAnswerAuthorInputPayload, FinalAnswerPacket
from core.final_answer_runtime_assembly import (
    FinalAnswerAuthorRuntimeAssembly,
    assemble_final_answer_author_runtime,
)
from core.run_kernel import (
    FINAL_ANSWER_PACKET_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)
from core.runtime_prompt_assembly import select_author_system_prompt

SAFE_BLOCKED_FAP_SUMMARY_SCHEMA_VERSION = "blocked_final_answer_packet_safe_summary_v1"
COMPONENT_BLOCKED_SUMMARY_SCHEMA_VERSION = "blocked_fap_component_summary_v1"
QUANTITATIVE_FAP_AUTHORITY_SAFE_SUMMARY_SCHEMA_VERSION = (
    "blocked_fap_quantitative_authority_safe_summary_v1"
)

_SAFE_QUANTITATIVE_PREFLIGHT_STATUSES = frozenset({"ready", "blocked"})
_SAFE_QUANTITATIVE_CLAIM_KINDS = frozenset(
    {"direct_component", "admitted_synthesis", "hardened_component"}
)
_SAFE_QUANTITATIVE_PREFLIGHT_REASON_CODES = frozenset(
    {
        "unadmitted_numeric_claim",
        "missing_admitted_component_authority",
        "stale_or_foreign_quantitative_authority",
        "stale_or_foreign_lineage",
        "missing_component_analyst_authority",
        "missing_semantic_observation_authority",
        "missing_component_coverage_authority",
        "missing_content_evidence_lineage",
        "missing_synthesis_validator_authority",
        "missing_required_specialist_binding",
        "incomplete_specialist_authority",
        "missing_direct_source_binding",
        "unsupported_claim_literal_surface",
        "claim_literal_absent_from_bound_material",
        "literal_signature_mismatch",
    }
)


def _safe_text(value: Any, *, limit: int = 240) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:limit]


def _safe_text_list(value: Any, *, limit: int = 240) -> list[str]:
    if isinstance(value, str):
        values: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        values = ()
    result: list[str] = []
    for item in values:
        clean = _safe_text(item, limit=limit)
        if clean and clean not in result:
            result.append(clean)
    return result


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_mapping_sequence_from_any(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _safe_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized >= 0 else None


def _safe_quantitative_fap_authority_preflight(value: Any) -> dict[str, Any]:
    """Project only enumerated FAP quantitative preflight facts.

    The blocked-Author path must not surface selected claim text, source text,
    provider output, or prompt material.  The preflight already emits a
    structural diagnostic; this helper keeps the PRODUCT failure packet to its
    closed safe vocabulary so a blocked run remains mechanically diagnosable.
    """

    raw = _safe_mapping(value)
    status = _safe_text(raw.get("status"), limit=40)
    if status not in _SAFE_QUANTITATIVE_PREFLIGHT_STATUSES:
        return {}

    summary: dict[str, Any] = {
        "schema_version": QUANTITATIVE_FAP_AUTHORITY_SAFE_SUMMARY_SCHEMA_VERSION,
        "status": status,
    }
    for key in (
        "author_invocation_allowed",
        "post_author_semantic_validation_required",
    ):
        if isinstance(raw.get(key), bool):
            summary[key] = raw[key]
    for key in (
        "required_numeric_claim_count",
        "authorized_numeric_claim_count",
        "blocked_numeric_claim_count",
    ):
        count = _safe_nonnegative_int(raw.get(key))
        if count is not None:
            summary[key] = count

    reason_codes = [
        code
        for code in _safe_text_list(raw.get("reason_codes"), limit=120)
        if code in _SAFE_QUANTITATIVE_PREFLIGHT_REASON_CODES
    ]
    if reason_codes:
        summary["reason_codes"] = list(dict.fromkeys(reason_codes))

    reason_refs: list[dict[str, Any]] = []
    for raw_ref in _safe_mapping_sequence_from_any(raw.get("reason_refs")):
        reason_code = _safe_text(raw_ref.get("reason_code"), limit=120)
        if reason_code not in _SAFE_QUANTITATIVE_PREFLIGHT_REASON_CODES:
            continue
        ref: dict[str, Any] = {"reason_code": reason_code}
        claim_kind = _safe_text(raw_ref.get("claim_kind"), limit=120)
        if claim_kind in _SAFE_QUANTITATIVE_CLAIM_KINDS:
            ref["claim_kind"] = claim_kind
        literal_count = _safe_nonnegative_int(raw_ref.get("literal_count"))
        if literal_count is not None:
            ref["literal_count"] = literal_count
        if isinstance(raw_ref.get("specialist_declared"), bool):
            ref["specialist_declared"] = raw_ref["specialist_declared"]
        if ref not in reason_refs:
            reason_refs.append(ref)
    if reason_refs:
        summary["reason_refs"] = reason_refs
    return summary


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _count_from_sources(
    *,
    key: str,
    sequence_key: str,
    projection: Mapping[str, Any],
    payload_ref: Mapping[str, Any],
    authority_payload: Mapping[str, Any],
) -> int:
    for source in (projection, payload_ref, authority_payload):
        value = _optional_int(source.get(key))
        if value is not None:
            return value
    sequence = payload_ref.get(sequence_key)
    if isinstance(sequence, Sequence) and not isinstance(sequence, (str, bytes)):
        return len(sequence)
    return 0


def _safe_component_digest(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _safe_semantic_component_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_mapping_sequence_from_any(value):
        component_id = _safe_text(
            item.get("component_id") or item.get("answer_component_id"),
            limit=160,
        )
        component_digest = _safe_text(item.get("component_digest"), limit=128)
        if not component_id and not component_digest:
            continue
        ref: dict[str, Any] = {}
        if component_id:
            ref["component_id"] = component_id
        if component_digest:
            ref["component_digest"] = component_digest
        safe_label = None
        if item.get("sanitized") is True or item.get("safe_label") is not None:
            safe_label = _safe_text(
                item.get("safe_label") or item.get("sanitized_label"),
                limit=120,
            )
        if safe_label:
            ref["safe_label"] = safe_label
        if ref not in refs:
            refs.append(ref)
    return refs


def _component_entry(
    *,
    packet_id: str | None,
    status: str,
    index: int,
    component_ref: Mapping[str, Any] | None = None,
    blocker_reason_codes: Sequence[str] = (),
    expected_answerable: bool | None = True,
    answered_or_answerable_from_evidence: bool = False,
    satisfied_source_obligation_count: int = 0,
    missing_source_obligation_count: int = 0,
    partial_source_obligation_count: int = 0,
    citation_binding_available: bool = False,
    evidence_binding_available: bool = False,
) -> dict[str, Any]:
    ref = dict(component_ref or {})
    component_id = _safe_text(
        ref.get("component_id") or ref.get("answer_component_id"),
        limit=160,
    )
    component_digest = _safe_text(ref.get("component_digest"), limit=128)
    if not component_id:
        component_id = (
            "component:"
            + _safe_component_digest(
                {
                    "packet_id": packet_id,
                    "status": status,
                    "index": index,
                    "schema": COMPONENT_BLOCKED_SUMMARY_SCHEMA_VERSION,
                }
            )[:16]
        )
    entry = {
        "component_id": component_id,
        "status": status,
        "expected_answerable": expected_answerable,
        "answered_or_answerable_from_evidence": bool(
            answered_or_answerable_from_evidence
        ),
        "blocker_reason_codes": _safe_text_list(blocker_reason_codes, limit=160),
        "satisfied_source_obligation_count": max(
            0,
            int(satisfied_source_obligation_count or 0),
        ),
        "missing_source_obligation_count": max(
            0,
            int(missing_source_obligation_count or 0),
        ),
        "partial_source_obligation_count": max(
            0,
            int(partial_source_obligation_count or 0),
        ),
        "citation_binding_available": bool(citation_binding_available),
        "evidence_binding_available": bool(evidence_binding_available),
    }
    if component_digest:
        entry["component_digest"] = component_digest
    safe_label = _safe_text(
        ref.get("safe_label") or ref.get("sanitized_label"),
        limit=120,
    )
    if safe_label:
        entry["safe_label"] = safe_label
    return _without_empty(entry)


def _semantic_ref_from_blocked_sources(
    *,
    projection: Mapping[str, Any],
    payload_ref: Mapping[str, Any],
    authority_payload: Mapping[str, Any],
) -> dict[str, Any]:
    for source in (payload_ref, projection, authority_payload):
        semantic_ref = _safe_mapping(source.get("semantic_authority_ref"))
        if semantic_ref:
            return semantic_ref
    return {}


def _component_refs_from_blocked_sources(
    *,
    projection: Mapping[str, Any],
    payload_ref: Mapping[str, Any],
    authority_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    for source in (payload_ref, projection, authority_payload):
        refs = _safe_semantic_component_refs(source.get("semantic_component_refs"))
        if refs:
            return refs
    return []


def _component_readiness_from_blocked_sources(
    *,
    projection: Mapping[str, Any],
    payload_ref: Mapping[str, Any],
    authority_payload: Mapping[str, Any],
) -> dict[str, Any]:
    for source in (payload_ref, projection, authority_payload):
        readiness = _safe_mapping(source.get("component_readiness"))
        if readiness:
            return readiness
    author_refs = _safe_mapping(projection.get("author_input_refs"))
    return _safe_mapping(author_refs.get("component_readiness"))


def _component_binding_ref(binding: Mapping[str, Any]) -> dict[str, Any]:
    ref: dict[str, Any] = {}
    for field_name in (
        "evidence_bound",
        "citation_bound",
        "source_obligation_bound",
        "answer_value_bound",
        "full_component_success",
        "partial_user_answer_candidate",
        "source_obligation_satisfied_from_ledger",
    ):
        if field_name in binding:
            ref[field_name] = binding.get(field_name) is True
    for field_name in (
        "evidence_binding_status",
        "citation_binding_status",
        "source_obligation_binding_status",
        "answer_value_binding_status",
    ):
        value = _safe_text(binding.get(field_name), limit=120)
        if value:
            ref[field_name] = value
    return ref


def _blocked_component_summary_from_readiness(
    *,
    component_readiness: Mapping[str, Any],
    packet_id: str | None,
) -> dict[str, Any]:
    readiness_components = _safe_mapping_sequence_from_any(
        component_readiness.get("components")
    )
    if not readiness_components:
        return {}
    components: list[dict[str, Any]] = []
    for index, component in enumerate(readiness_components, start=1):
        binding = _safe_mapping(component.get("binding_status"))
        status = (
            _safe_text(
                component.get("status")
                or component.get("component_readiness_status"),
                limit=120,
            )
            or "missing_component"
        )
        entry = _component_entry(
            packet_id=packet_id,
            status=status,
            index=index,
            component_ref={
                "component_id": component.get("component_id"),
                "safe_label": component.get("safe_label") or component.get("label"),
            },
            blocker_reason_codes=_safe_text_list(
                component.get("blocker_reasons"),
                limit=160,
            ),
            expected_answerable=True,
            answered_or_answerable_from_evidence=(
                status == "satisfied_component"
                and binding.get("full_component_success") is True
            ),
            satisfied_source_obligation_count=(
                1 if binding.get("source_obligation_bound") is True else 0
            ),
            missing_source_obligation_count=(
                0 if binding.get("source_obligation_bound") is True else 1
            ),
            partial_source_obligation_count=(
                1 if status == "partial_component" else 0
            ),
            citation_binding_available=binding.get("citation_bound") is True,
            evidence_binding_available=binding.get("evidence_bound") is True,
        )
        binding_ref = _component_binding_ref(binding)
        if binding_ref:
            entry["binding_status_ref"] = binding_ref
        for target_key, source_key in (
            ("component_candidate_link_refs", "component_candidate_link_refs"),
            ("component_custody_gap_refs", "component_custody_gap_refs"),
            (
                "component_source_obligation_refs",
                "component_source_obligation_refs",
            ),
        ):
            refs = _safe_mapping_sequence_from_any(component.get(source_key))
            if refs:
                entry[target_key] = refs
        components.append(entry)

    expected_count = _optional_int(component_readiness.get("component_count"))
    if expected_count is None:
        expected_count = len(components)
    satisfied_count = sum(1 for item in components if item["status"] == "satisfied_component")
    partial_count = sum(1 for item in components if item["status"] == "partial_component")
    missing_count = sum(1 for item in components if item["status"] == "missing_component")
    blocked_count = sum(1 for item in components if item["status"] == "blocked_component")
    unready_count = partial_count + missing_count + blocked_count
    candidate_observed_count = sum(
        1 for item in components if item.get("component_candidate_link_refs")
    )
    summary = {
        "schema_version": COMPONENT_BLOCKED_SUMMARY_SCHEMA_VERSION,
        "component_summary_available": True,
        "source": "RunKernel.RunAuthoritySufficiencyJudgment.component_readiness",
        "readiness_owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "final_packet_owner": "RunKernel.FinalAnswerPacket",
        "expected_component_count": expected_count,
        "expected_answerable_component_count": expected_count,
        "supported_component_count": satisfied_count,
        "candidate_observed_component_count": candidate_observed_count,
        "citation_bound_component_count": sum(
            1
            for item in components
            if _safe_mapping(item.get("binding_status_ref")).get("citation_bound")
            is True
        ),
        "evidence_bound_component_count": sum(
            1
            for item in components
            if _safe_mapping(item.get("binding_status_ref")).get("evidence_bound")
            is True
        ),
        "source_obligation_satisfied_component_count": sum(
            1
            for item in components
            if _safe_mapping(item.get("binding_status_ref")).get(
                "source_obligation_bound"
            )
            is True
        ),
        "satisfied_component_count": satisfied_count,
        "partial_component_count": partial_count,
        "missing_component_count": missing_count,
        "blocked_component_count": blocked_count,
        "expected_answerable_missing_component_count": unready_count,
        "unsupported_component_count": 0,
        "unclear_component_count": 0,
        "entangled_component_count": 0,
        "source_bound_numeric_unknown_component_count": 0,
        "full_component_success": bool(
            expected_count and satisfied_count >= expected_count and unready_count == 0
        ),
        "partial_user_answer_candidate": False,
        "user_facing_partial_answer_enabled": False,
        "component_partial_readiness_observed": bool(partial_count),
        "hard_block_candidate": bool(unready_count),
        "components": components,
    }
    return _without_empty(summary)


def _blocked_component_summary(
    *,
    projection: Mapping[str, Any],
    payload_ref: Mapping[str, Any],
    authority_payload: Mapping[str, Any],
) -> dict[str, Any]:
    packet_id = _safe_text(
        payload_ref.get("packet_id")
        or projection.get("packet_id")
        or authority_payload.get("packet_id"),
        limit=160,
    )
    component_readiness = _component_readiness_from_blocked_sources(
        projection=projection,
        payload_ref=payload_ref,
        authority_payload=authority_payload,
    )
    readiness_summary = _blocked_component_summary_from_readiness(
        component_readiness=component_readiness,
        packet_id=packet_id,
    )
    if readiness_summary:
        return readiness_summary

    semantic_ref = _semantic_ref_from_blocked_sources(
        projection=projection,
        payload_ref=payload_ref,
        authority_payload=authority_payload,
    )
    blocker_codes = _safe_text_list(semantic_ref.get("blocker_codes"), limit=160)
    readiness_reasons = _safe_text_list(
        payload_ref.get("readiness_reasons")
        or projection.get("readiness_reasons")
        or authority_payload.get("readiness_reasons"),
        limit=160,
    )
    semantic_blockers = set(blocker_codes) | set(readiness_reasons)
    source_bound_unknown_count = _count_from_sources(
        key="source_bound_numeric_unknown_count",
        sequence_key="source_bound_numeric_unknowns",
        projection=projection,
        payload_ref=payload_ref,
        authority_payload=authority_payload,
    )
    has_semantic_component_signal = bool(
        semantic_ref.get("available")
        or semantic_ref.get("sufficiency_semantic_consumed")
        or semantic_ref.get("required_component_count")
        or semantic_ref.get("covered_component_count")
        or "missing_required_component_coverage" in semantic_blockers
        or "semantic_direct_answer_blocked" in semantic_blockers
        or "missing_required_component_coverage" in blocker_codes
    )
    if not has_semantic_component_signal and source_bound_unknown_count <= 0:
        return {}

    expected_count = _optional_int(semantic_ref.get("required_component_count"))
    supported_count = _optional_int(semantic_ref.get("covered_component_count")) or 0
    missing_count = _optional_int(semantic_ref.get("missing_component_count"))
    if missing_count is None and expected_count is not None:
        missing_count = max(0, expected_count - supported_count)
    missing_count = max(0, int(missing_count or 0))
    expected_component_count = max(
        0,
        int(expected_count if expected_count is not None else supported_count + missing_count),
    )
    expected_answerable_count = expected_component_count or None
    expected_answerable_missing_count = missing_count + source_bound_unknown_count
    citation_bound_component_count = 0
    evidence_bound_component_count = 0
    source_obligation_satisfied_component_count = min(
        supported_count,
        _count_from_sources(
            key="satisfied_source_obligation_count",
            sequence_key="satisfied_source_obligations",
            projection=projection,
            payload_ref=payload_ref,
            authority_payload=authority_payload,
        ),
    )
    semantic_partial_coverage_observed = bool(
        supported_count > 0 and expected_answerable_missing_count > 0
    )
    supported_components_safely_answerable = bool(
        supported_count > 0
        and citation_bound_component_count >= supported_count
        and evidence_bound_component_count >= supported_count
        and source_obligation_satisfied_component_count >= supported_count
    )
    partial_candidate = None
    if expected_component_count:
        partial_candidate = bool(
            semantic_partial_coverage_observed
            and supported_components_safely_answerable
        )
    hard_block_candidate = (
        supported_count == 0
        or expected_answerable_missing_count > 0
        or bool(semantic_ref.get("direct_answer_blocked"))
        or bool(semantic_ref.get("finalization_blocked"))
    )
    full_component_success = bool(
        expected_component_count
        and supported_count >= expected_component_count
        and expected_answerable_missing_count == 0
        and source_bound_unknown_count == 0
    )

    component_refs = _component_refs_from_blocked_sources(
        projection=projection,
        payload_ref=payload_ref,
        authority_payload=authority_payload,
    )
    components: list[dict[str, Any]] = []
    supported_refs = component_refs[:supported_count]
    for index in range(supported_count):
        ref = supported_refs[index] if index < len(supported_refs) else None
        components.append(
            _component_entry(
                packet_id=packet_id,
                status="supported",
                index=index + 1,
                component_ref=ref,
                expected_answerable=True,
                answered_or_answerable_from_evidence=False,
            )
        )
    missing_blockers = blocker_codes or ["missing_required_component_coverage"]
    for index in range(missing_count):
        components.append(
            _component_entry(
                packet_id=packet_id,
                status="missing",
                index=index + 1,
                blocker_reason_codes=missing_blockers,
                expected_answerable=True,
                answered_or_answerable_from_evidence=False,
                missing_source_obligation_count=1,
            )
        )
    for index in range(source_bound_unknown_count):
        components.append(
            _component_entry(
                packet_id=packet_id,
                status="source_bound_numeric_unknown",
                index=index + 1,
                blocker_reason_codes=["source_bound_numeric_unknown"],
                expected_answerable=True,
                answered_or_answerable_from_evidence=False,
                missing_source_obligation_count=1,
            )
        )

    summary = {
        "schema_version": COMPONENT_BLOCKED_SUMMARY_SCHEMA_VERSION,
        "component_summary_available": True,
        "expected_component_count": expected_component_count,
        "expected_answerable_component_count": expected_answerable_count,
        "supported_component_count": supported_count,
        "citation_bound_component_count": citation_bound_component_count,
        "evidence_bound_component_count": evidence_bound_component_count,
        "source_obligation_satisfied_component_count": (
            source_obligation_satisfied_component_count
        ),
        "missing_component_count": missing_count,
        "expected_answerable_missing_component_count": expected_answerable_missing_count,
        "unsupported_component_count": 0,
        "unclear_component_count": 0,
        "entangled_component_count": 0,
        "source_bound_numeric_unknown_component_count": source_bound_unknown_count,
        "full_component_success": full_component_success,
        "partial_user_answer_candidate": partial_candidate,
        "semantic_partial_coverage_observed": semantic_partial_coverage_observed,
        "hard_block_candidate": hard_block_candidate,
        "components": components,
    }
    return _without_empty(summary)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


BLOCKED_FAP_TERMINAL_TRACE_KEY = "blocked_fap_terminal"
BLOCKED_FAP_TERMINAL_SCHEMA_VERSION = "blocked_fap_terminal_outcome_v1"
BLOCKED_FAP_TERMINAL_EXPORTED_POSTURE = "blocked"


def build_blocked_fap_terminal_report(
    blocked_fap_summary: Mapping[str, Any] | None,
) -> str:
    """Return a deterministic sanitized non-Author terminal message.

    Uses only safe blocked-FAP summary fields. Never includes prompts, provider
    payloads, raw evidence, private logs, full traces, or unsupported answers.
    """

    summary = _safe_mapping(blocked_fap_summary)
    lines = [
        "ScryRaven could not produce a supported answer.",
        "FinalAnswerPacket readiness is blocked, so Author was not invoked.",
    ]
    posture = _safe_text(summary.get("final_answer_posture"), limit=120)
    if posture:
        lines.append(f"Evidence posture: {posture}.")
    reasons = _safe_text_list(summary.get("readiness_reasons"), limit=160)
    if reasons:
        lines.append("Readiness reasons: " + "; ".join(reasons[:12]) + ".")
    missing = summary.get("missing_source_obligation_count")
    satisfied = summary.get("satisfied_source_obligation_count")
    if isinstance(missing, int) or isinstance(satisfied, int):
        lines.append(
            "Source obligations: "
            f"missing={int(missing or 0)}, satisfied={int(satisfied or 0)}."
        )
    unknown = summary.get("source_bound_numeric_unknown_count")
    if isinstance(unknown, int) and unknown > 0:
        lines.append(f"Source-bound numeric unknowns: {unknown}.")
    component_summary = _safe_mapping(summary.get("component_blocked_summary"))
    if component_summary.get("component_summary_available") is True:
        expected = int(component_summary.get("expected_component_count") or 0)
        missing_components = int(component_summary.get("missing_component_count") or 0)
        supported = int(component_summary.get("supported_component_count") or 0)
        lines.append(
            "Component readiness: "
            f"expected={expected}, supported={supported}, missing={missing_components}."
        )
        blocker_codes: list[str] = []
        for component in component_summary.get("components") or ():
            if not isinstance(component, Mapping):
                continue
            blocker_codes.extend(
                _safe_text_list(component.get("blocker_reason_codes"), limit=120)
            )
        unique_blockers = list(dict.fromkeys(blocker_codes))
        if unique_blockers:
            lines.append(
                "Component blockers: " + "; ".join(unique_blockers[:12]) + "."
            )
    lines.append("No Author payload was derived and no Author model call was made.")
    return "\n".join(lines)


def build_blocked_fap_terminal_trace_fragment(
    blocked_fap_summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return execution-trace fragment for a blocked FAP terminal outcome.

    Exported terminal posture is always blocked/insufficient when FAP is blocked.
    Sufficiency lineage such as partial_answer_authorized is preserved only as
    diagnostic lineage and must not become the final RunOutcome posture.
    """

    summary = _safe_mapping(blocked_fap_summary)
    sufficiency_lineage = _safe_text(summary.get("sufficiency_decision"), limit=120)
    partial_candidate_not_fap_safe = (
        sufficiency_lineage == "partial_answer_authorized"
    )
    return {
        BLOCKED_FAP_TERMINAL_TRACE_KEY: {
            "schema_version": BLOCKED_FAP_TERMINAL_SCHEMA_VERSION,
            "blocked_fap": True,
            "author_input_blocked": True,
            "author_called": False,
            "author_payload_derived": False,
            "exported_terminal_posture": BLOCKED_FAP_TERMINAL_EXPORTED_POSTURE,
            "answer_class": "no_evidence_found",
            "response_displayable": False,
            "evidence_sufficient": False,
            "sufficiency_decision_lineage": sufficiency_lineage or None,
            "partial_candidate_not_fap_safe": partial_candidate_not_fap_safe,
            "blocked_fap_summary": dict(summary),
        }
    }


def build_safe_blocked_fap_summary(
    final_answer_authority_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return compact no-raw blocked-FAP details for failure observability."""

    projection = _safe_mapping(final_answer_authority_projection)
    payload_ref = _safe_mapping(projection.get("author_payload_ref"))
    if not payload_ref and projection.get("status") == "blocked":
        payload_ref = projection
        projection = {}
    if payload_ref.get("status") != "blocked":
        return {}
    authority_payload = _safe_mapping(payload_ref.get("authority_payload"))
    final_answer_allowed = authority_payload.get("final_answer_allowed")
    if not isinstance(final_answer_allowed, bool):
        final_answer_allowed = None
    summary = _without_empty(
        {
            "schema_version": SAFE_BLOCKED_FAP_SUMMARY_SCHEMA_VERSION,
            "blocked_fap": True,
            "packet_id": _safe_text(
                payload_ref.get("packet_id")
                or projection.get("packet_id")
                or authority_payload.get("packet_id"),
                limit=160,
            ),
            "status": "blocked",
            "readiness_status": _safe_text(
                payload_ref.get("readiness_status")
                or projection.get("readiness_status")
                or authority_payload.get("readiness_status"),
                limit=120,
            ),
            "readiness_reasons": _safe_text_list(
                payload_ref.get("readiness_reasons")
                or projection.get("readiness_reasons")
                or authority_payload.get("readiness_reasons"),
                limit=160,
            ),
            "author_input_deferred": bool(payload_ref.get("author_input_deferred")),
            "blocked_before_author_input": bool(
                payload_ref.get("blocked_before_author_input")
            ),
            "final_answer_allowed": final_answer_allowed,
            "final_answer_posture": _safe_text(
                payload_ref.get("final_answer_posture")
                or authority_payload.get("final_answer_posture"),
                limit=120,
            ),
            "sufficiency_decision": _safe_text(
                payload_ref.get("sufficiency_decision")
                or authority_payload.get("sufficiency_decision"),
                limit=120,
            ),
            "missing_source_obligation_count": _count_from_sources(
                key="missing_source_obligation_count",
                sequence_key="missing_source_obligations",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "partial_source_obligation_count": _count_from_sources(
                key="partial_source_obligation_count",
                sequence_key="partial_source_obligations",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "satisfied_source_obligation_count": _count_from_sources(
                key="satisfied_source_obligation_count",
                sequence_key="satisfied_source_obligations",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "source_bound_numeric_unknown_count": _count_from_sources(
                key="source_bound_numeric_unknown_count",
                sequence_key="source_bound_numeric_unknowns",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "mandatory_caveat_count": _count_from_sources(
                key="mandatory_caveat_count",
                sequence_key="mandatory_caveats",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "prohibited_upgrade_count": _count_from_sources(
                key="prohibited_upgrade_count",
                sequence_key="prohibited_upgrades",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "claim_postures": _safe_text_list(
                payload_ref.get("claim_postures")
                or authority_payload.get("claim_postures"),
                limit=160,
            ),
        }
    )
    component_summary = _blocked_component_summary(
        projection=projection,
        payload_ref=payload_ref,
        authority_payload=authority_payload,
    )
    if component_summary:
        summary["component_blocked_summary"] = component_summary
    quantitative_preflight = _safe_quantitative_fap_authority_preflight(
        payload_ref.get("quantitative_fap_authority_preflight")
        or authority_payload.get("quantitative_fap_authority_preflight")
    )
    if quantitative_preflight:
        summary["quantitative_fap_authority_preflight"] = quantitative_preflight
    return summary


@dataclass(frozen=True, slots=True)
class FinalAnswerPacketPreparationResult:
    """Packet, optional Author payload, and observation from the bounded executor."""

    packet: FinalAnswerPacket
    author_payload: FinalAnswerAuthorInputPayload | None
    author_payload_ref: Mapping[str, Any]
    author_prompt: str
    author_system_prompt_key: str
    author_effort: str
    author_system_prompt: str
    observation: Observation
    author_provider: str | None
    author_model: str | None
    author_input_blocked: bool = False
    blocked_reason: str | None = None


@dataclass(frozen=True, slots=True)
class FinalAnswerPacketAuthorHandoff:
    """RunKernel-reduced FinalAnswerPacket and optional Author payload handoff."""

    action: AuthorizedAction
    preparation: FinalAnswerPacketPreparationResult
    packet: FinalAnswerPacket
    author_payload: FinalAnswerAuthorInputPayload | None
    author_payload_ref: Mapping[str, Any]
    author_prompt: str
    author_system_prompt_key: str
    author_effort: str
    author_provider: str | None
    author_model: str | None
    author_system_prompt: str
    author_input_blocked: bool = False
    blocked_reason: str | None = None


def _author_effort(
    *,
    analyst_effort: str,
    corpus_weak: bool,
    estimate_from_priors_author: bool,
    relevance_low: bool,
) -> str:
    if (not corpus_weak or estimate_from_priors_author) and not relevance_low:
        return str(analyst_effort or "low")
    return "low"


def _author_provider_model(
    *,
    strategy: str,
    fast_provider: str | None,
    fast_model: str | None,
    smart_provider: str | None,
    smart_model: str | None,
) -> tuple[str | None, str | None]:
    if strategy in ("Fast", "Balanced"):
        return fast_provider, fast_model
    return smart_provider, smart_model


def _ledger_summary(projection: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(projection, Mapping):
        return {"evidence_ledger_consumed": False}
    return {
        "evidence_ledger_consumed": projection.get("owner")
        == "RunKernel.EvidenceLedger",
        "evidence_ledger_candidate_count": projection.get("candidate_count", 0),
        "evidence_ledger_requirement_count": projection.get("requirement_count", 0),
        "evidence_ledger_gap_count": len(projection.get("custody_gaps") or ()),
    }


def _safe_mapping_sequence(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return _safe_mapping_sequence_from_any(values)


def _blocked_author_payload_ref(packet: FinalAnswerPacket) -> dict[str, Any]:
    readiness_status = packet.readiness_status.value
    readiness_reasons = list(packet.readiness_reasons)
    missing_source_obligations = _safe_mapping_sequence(
        packet.missing_required_obligations
    )
    partial_source_obligations = _safe_mapping_sequence(packet.partial_obligations)
    satisfied_source_obligations = _safe_mapping_sequence(packet.satisfied_obligations)
    source_bound_numeric_unknowns = _safe_mapping_sequence(
        packet.source_bound_numeric_unknowns
    )
    source_bound_numeric_resolutions = _safe_mapping_sequence(
        packet.source_bound_numeric_resolutions
    )
    claim_postures = [
        item.value if hasattr(item, "value") else str(item)
        for item in packet.claim_postures
    ]
    component_readiness = _safe_mapping(
        packet.author_input_refs.get("component_readiness")
        if isinstance(packet.author_input_refs, Mapping)
        else {}
    )
    quantitative_preflight = _safe_quantitative_fap_authority_preflight(
        packet.author_input_refs.get("quantitative_fap_authority_preflight")
        if isinstance(packet.author_input_refs, Mapping)
        else {}
    )
    authority_payload = {
        "packet_id": packet.packet_id,
        "readiness_status": readiness_status,
        "readiness_reasons": readiness_reasons,
        "sufficiency_decision": packet.sufficiency_decision,
        "final_answer_posture": packet.final_answer_posture,
        "final_answer_allowed": bool(packet.final_answer_allowed),
        "required_obligations_satisfied": packet.required_obligations_satisfied,
        "claim_postures": claim_postures,
        "missing_source_obligation_count": len(missing_source_obligations),
        "partial_source_obligation_count": len(partial_source_obligations),
        "satisfied_source_obligation_count": len(satisfied_source_obligations),
        "source_bound_numeric_unknown_count": len(source_bound_numeric_unknowns),
        "mandatory_caveat_count": len(packet.mandatory_caveats),
        "prohibited_upgrade_count": len(packet.prohibited_upgrades),
        "author_input_deferred": True,
    }
    if component_readiness:
        authority_payload["component_readiness"] = component_readiness
    if quantitative_preflight:
        authority_payload["quantitative_fap_authority_preflight"] = (
            quantitative_preflight
        )
    semantic_component_refs = _safe_semantic_component_refs(
        packet.semantic_content_coverage_ref_projection.get("component_refs")
        if isinstance(packet.semantic_content_coverage_ref_projection, Mapping)
        else ()
    )
    if packet.semantic_authority_ref:
        authority_payload["semantic_authority_ref"] = _safe_mapping(
            packet.semantic_authority_ref
        )
    payload = {
        "packet_id": packet.packet_id,
        "status": "blocked",
        "prompt_text_included": False,
        "author_input_deferred": True,
        "blocked_before_author_input": True,
        "readiness_status": readiness_status,
        "readiness_reasons": readiness_reasons,
        "author_evidence_ids": [],
        "citation_source_ids": [],
        "citation_ineligible_refs": [],
        "missing_source_obligations": missing_source_obligations,
        "partial_source_obligations": partial_source_obligations,
        "satisfied_source_obligations": satisfied_source_obligations,
        "source_bound_numeric_unknowns": source_bound_numeric_unknowns,
        "source_bound_numeric_resolutions": source_bound_numeric_resolutions,
        "final_answer_posture": packet.final_answer_posture,
        "sufficiency_decision": packet.sufficiency_decision,
        "claim_postures": claim_postures,
        "mandatory_caveat_count": len(packet.mandatory_caveats),
        "prohibited_upgrade_count": len(packet.prohibited_upgrades),
        "authority_payload": authority_payload,
        "raw_prompt_included": False,
        "provider_payload_included": False,
        "raw_content_included": False,
        "final_text_included": False,
        "model_request_visible": False,
    }
    if component_readiness:
        payload["component_readiness"] = component_readiness
    if quantitative_preflight:
        payload["quantitative_fap_authority_preflight"] = quantitative_preflight
    if packet.semantic_authority_ref:
        payload["semantic_authority_ref"] = _safe_mapping(packet.semantic_authority_ref)
    if semantic_component_refs:
        payload["semantic_component_refs"] = semantic_component_refs
    return payload


def execute_final_answer_packet_prepare_action(
    action: AuthorizedAction,
    *,
    run_id: str,
    query: str,
    intent: str,
    report_type: str,
    query_type: str,
    core_topic: str,
    primary_entity: str,
    anchor_packet_telemetry: Mapping[str, Any] | None,
    final_top_evidence: Sequence[Mapping[str, Any]],
    author_evidence: Sequence[Mapping[str, Any]],
    ordered_sources: Sequence[str],
    unique_source_urls: Mapping[str, Any],
    query_lineage_refs: Mapping[str, Any],
    corpus_weak: bool,
    failure_card_payload: Mapping[str, Any],
    conflicts_present: bool,
    synth_was_insufficient: bool,
    author_notes: str,
    author_prompt: str,
    default_system: Mapping[str, str],
    analyst_effort: str,
    estimate_from_priors_author: bool,
    relevance_low: bool,
    strategy: str,
    fast_provider: str | None,
    fast_model: str | None,
    smart_provider: str | None,
    smart_model: str | None,
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    answer_contract_projection: Any | None = None,
    accepted_answer_contract_projection: Any | None = None,
    run_contract_projection: Mapping[str, Any] | None = None,
    sufficiency_judgment_projection: Mapping[str, Any] | None = None,
) -> FinalAnswerPacketPreparationResult:
    """Build a FinalAnswerPacket and packet-derived Author payload."""

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FINAL_ANSWER_PACKET_PREPARE,
        stage=FINAL_ANSWER_PACKET_STAGE,
        expected_observation_type=ObservationType.FINAL_ANSWER_PACKET_PREPARED,
    )
    if run_id != authorized.run_id:
        raise ValueError("packet preparation run_id must match AuthorizedAction")

    author_system_prompt, author_system_prompt_key = select_author_system_prompt(
        default_system=default_system,
        corpus_weak=corpus_weak,
        estimate_from_priors_author=estimate_from_priors_author,
    )
    author_effort = _author_effort(
        analyst_effort=analyst_effort,
        corpus_weak=corpus_weak,
        estimate_from_priors_author=estimate_from_priors_author,
        relevance_low=relevance_low,
    )
    author_provider, author_model = _author_provider_model(
        strategy=strategy,
        fast_provider=fast_provider,
        fast_model=fast_model,
        smart_provider=smart_provider,
        smart_model=smart_model,
    )

    assembly: FinalAnswerAuthorRuntimeAssembly = assemble_final_answer_author_runtime(
        run_id=run_id,
        query=query,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        anchor_packet_telemetry=anchor_packet_telemetry,
        final_top_evidence=final_top_evidence,
        author_evidence=author_evidence,
        ordered_sources=ordered_sources,
        unique_source_urls=unique_source_urls,
        query_lineage_refs=query_lineage_refs,
        corpus_weak=corpus_weak,
        failure_card_payload=failure_card_payload,
        conflicts_present=conflicts_present,
        synth_was_insufficient=synth_was_insufficient,
        author_notes=author_notes,
        author_prompt=author_prompt,
        author_system_prompt_key=author_system_prompt_key,
        author_effort=author_effort,
        author_provider=author_provider,
        author_model=author_model,
        answer_contract_projection=answer_contract_projection,
        accepted_answer_contract_projection=accepted_answer_contract_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        run_contract_projection=run_contract_projection,
        sufficiency_judgment_projection=sufficiency_judgment_projection,
    )
    packet_projection = assembly.packet.to_dict()
    if assembly.author_payload is None:
        payload_ref = _blocked_author_payload_ref(assembly.packet)
    else:
        payload_ref = assembly.author_payload.to_trace_ref()
    observation_payload = {
        "owner": "RunKernel.FinalAnswerPacket",
        "packet_projection": packet_projection,
        "author_payload_ref": payload_ref,
        "author_input_blocked": assembly.author_input_blocked,
        "blocked_reason": assembly.blocked_reason,
        "readiness_status": packet_projection.get("readiness_status"),
        "readiness_reasons": packet_projection.get("readiness_reasons", []),
        "citation_authority_available": "citation_eligible" in packet_projection
        and "citation_ineligible" in packet_projection,
        "missing_source_obligation_count": len(
            payload_ref.get("missing_source_obligations", []) or []
        ),
        "partial_source_obligation_count": len(
            payload_ref.get("partial_source_obligations", []) or []
        ),
        "satisfied_source_obligation_count": len(
            payload_ref.get("satisfied_source_obligations", []) or []
        ),
        "source_bound_numeric_unknown_count": len(
            payload_ref.get("source_bound_numeric_unknowns", []) or []
        ),
        "mandatory_caveat_count": payload_ref.get("mandatory_caveat_count", 0),
        "prohibited_upgrade_count": payload_ref.get("prohibited_upgrade_count", 0),
        "author_authority_payload_ref": payload_ref.get("authority_payload", {}),
        "sufficiency_judgment_consumed": bool(sufficiency_judgment_projection),
        "sufficiency_decision": (
            sufficiency_judgment_projection.get("decision")
            if isinstance(sufficiency_judgment_projection, Mapping)
            else None
        ),
        **_ledger_summary(evidence_ledger_projection),
    }
    return FinalAnswerPacketPreparationResult(
        packet=assembly.packet,
        author_payload=assembly.author_payload,
        author_payload_ref=payload_ref,
        author_prompt=assembly.author_prompt,
        author_system_prompt_key=assembly.author_system_prompt_key,
        author_effort=assembly.author_effort,
        author_system_prompt=author_system_prompt,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FINAL_ANSWER_PACKET_PREPARED,
            status=RunStageStatus.COMPLETED,
            payload=observation_payload,
        ),
        author_provider=author_provider,
        author_model=author_model,
        author_input_blocked=assembly.author_input_blocked,
        blocked_reason=assembly.blocked_reason,
    )


def execute_final_answer_packet_prepare_action_from_scope(
    action: AuthorizedAction,
    runtime_scope: Mapping[str, Any],
    *,
    default_system: Mapping[str, str],
    accepted_answer_contract_projection: Any | None = None,
) -> FinalAnswerPacketPreparationResult:
    """Whitelisted pipeline-scope adapter for packet preparation."""

    return execute_final_answer_packet_prepare_action(
        action,
        run_id=runtime_scope["run_id"],
        query=runtime_scope["query"],
        intent=runtime_scope["intent"],
        report_type=runtime_scope["report_type"],
        query_type=runtime_scope["query_type"],
        core_topic=runtime_scope["core_topic"],
        primary_entity=runtime_scope["primary_entity"],
        anchor_packet_telemetry=runtime_scope["anchor_packet_telemetry"],
        final_top_evidence=runtime_scope["final_top_evidence"],
        author_evidence=runtime_scope["author_evidence"],
        ordered_sources=runtime_scope["ordered_sources"],
        unique_source_urls=runtime_scope["unique_source_urls"],
        query_lineage_refs=runtime_scope["query_authority"].to_trace_fragment(),
        corpus_weak=runtime_scope["corpus_weak"],
        failure_card_payload={
            "show": runtime_scope["_pre_gate_failure_card_show"],
            "reason": runtime_scope["_pre_gate_failure_card_reason"],
        },
        conflicts_present=bool(runtime_scope["scrutineer_flags"]),
        synth_was_insufficient=runtime_scope["synth_was_insufficient"],
        author_notes=runtime_scope["author_notes"],
        author_prompt=runtime_scope["author_prompt"],
        default_system=default_system,
        analyst_effort=runtime_scope["analyst_effort"],
        estimate_from_priors_author=runtime_scope["_efp_author"],
        relevance_low=runtime_scope["_relevance_low"],
        strategy=runtime_scope["strategy"],
        fast_provider=runtime_scope["fast_provider"],
        fast_model=runtime_scope["fast_model"],
        smart_provider=runtime_scope["smart_provider"],
        smart_model=runtime_scope["smart_model"],
        evidence_ledger_projection=runtime_scope.get("evidence_ledger_projection"),
        answer_contract_projection=runtime_scope.get("answer_contract_projection"),
        accepted_answer_contract_projection=(
            accepted_answer_contract_projection
            if accepted_answer_contract_projection is not None
            else runtime_scope.get("accepted_answer_contract_projection")
        ),
        run_contract_projection=runtime_scope.get("run_contract_projection"),
        sufficiency_judgment_projection=runtime_scope.get(
            "sufficiency_judgment_projection"
        ),
    )


def prepare_final_answer_packet_author_handoff_from_scope(
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    *,
    default_system: Mapping[str, str],
) -> FinalAnswerPacketAuthorHandoff:
    """Authorize, execute, and reduce the FinalAnswerPacket Author handoff."""

    canonical_sufficiency_projection = dict(
        getattr(run_kernel.state, "sufficiency_judgment_projection", {}) or {}
    )
    direct_semantic_consumption = dict(
        canonical_sufficiency_projection.get("direct_semantic_consumption") or {}
    )
    action = run_kernel.authorize_final_answer_packet_prepare(
        inputs={
            "candidate_count": len(runtime_scope["final_top_evidence"]),
            "author_evidence_count": len(runtime_scope["author_evidence"]),
            "evidence_ledger_available": bool(
                runtime_scope.get("evidence_ledger_projection")
            ),
            "run_contract_available": bool(runtime_scope.get("run_contract_projection")),
            "run_contract_id": runtime_scope["run_contract_projection"].get(
                "contract_id"
            ),
            "sufficiency_judgment_available": bool(
                canonical_sufficiency_projection
            ),
            "sufficiency_decision": canonical_sufficiency_projection.get(
                "decision"
            ),
            "direct_semantic_consumption_digest": (
                direct_semantic_consumption.get("consumption_digest")
            ),
        }
    )
    accepted_answer_contract_projection = (
        getattr(run_kernel.state, "current_answer_contract", {})
        or getattr(run_kernel.state, "initial_answer_contract", {})
    )
    canonical_runtime_scope = dict(runtime_scope)
    canonical_runtime_scope["evidence_ledger_projection"] = (
        run_kernel.state.evidence_ledger.to_projection().to_dict()
    )
    canonical_runtime_scope["run_contract_projection"] = dict(
        run_kernel.state.run_contract_projection
    )
    canonical_runtime_scope["sufficiency_judgment_projection"] = (
        canonical_sufficiency_projection
    )
    preparation = execute_final_answer_packet_prepare_action_from_scope(
        action,
        canonical_runtime_scope,
        default_system=default_system,
        accepted_answer_contract_projection=accepted_answer_contract_projection,
    )
    run_kernel.reduce(preparation.observation)
    payload = preparation.author_payload
    if preparation.author_input_blocked:
        return FinalAnswerPacketAuthorHandoff(
            action=action,
            preparation=preparation,
            packet=preparation.packet,
            author_payload=None,
            author_payload_ref=preparation.author_payload_ref,
            author_prompt=preparation.author_prompt,
            author_system_prompt_key=preparation.author_system_prompt_key,
            author_effort=preparation.author_effort,
            author_provider=preparation.author_provider,
            author_model=preparation.author_model,
            author_system_prompt=preparation.author_system_prompt,
            author_input_blocked=True,
            blocked_reason=preparation.blocked_reason,
        )
    if payload is None:
        raise ValueError("FinalAnswerPacket preparation did not produce Author input")
    return FinalAnswerPacketAuthorHandoff(
        action=action,
        preparation=preparation,
        packet=preparation.packet,
        author_payload=payload,
        author_payload_ref=preparation.author_payload_ref,
        author_prompt=payload.prompt,
        author_system_prompt_key=payload.author_system_prompt_key,
        author_effort=payload.author_effort,
        author_provider=payload.author_provider,
        author_model=payload.author_model,
        author_system_prompt=preparation.author_system_prompt,
    )


__all__ = [
    "FinalAnswerPacketAuthorHandoff",
    "FinalAnswerPacketPreparationResult",
    "SAFE_BLOCKED_FAP_SUMMARY_SCHEMA_VERSION",
    "COMPONENT_BLOCKED_SUMMARY_SCHEMA_VERSION",
    "BLOCKED_FAP_TERMINAL_TRACE_KEY",
    "BLOCKED_FAP_TERMINAL_SCHEMA_VERSION",
    "BLOCKED_FAP_TERMINAL_EXPORTED_POSTURE",
    "build_blocked_fap_terminal_report",
    "build_blocked_fap_terminal_trace_fragment",
    "build_safe_blocked_fap_summary",
    "execute_final_answer_packet_prepare_action",
    "execute_final_answer_packet_prepare_action_from_scope",
    "prepare_final_answer_packet_author_handoff_from_scope",
]
