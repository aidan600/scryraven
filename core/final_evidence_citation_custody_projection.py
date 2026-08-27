"""Normalized final evidence/citation custody projection for AG-93E.

This adapter consumes sanitized completed-run projections and exposes a compact
AG-93C-compatible view of final evidence and citation refs. It does not inspect
raw traces, call providers, recover sources, format citations, or change Author
prose.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

FINAL_EVIDENCE_CITATION_CUSTODY_PROJECTION_SCHEMA_VERSION = (
    "final_evidence_citation_custody_projection_ag93e_v1"
)

UNKNOWN = "unknown"

_MAX_LIST_ITEMS = 50
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "cache",
    "credential",
    "db",
    "env",
    "full_trace",
    "log",
    "output_packet",
    "password",
    "prompt",
    "provider_payload",
    "raw_",
    "secret",
    "token",
)


def build_ag93c_observed_snapshot_projection(
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    """Return an AG-93B/C observed snapshot with AG-93E custody projection.

    The returned payload preserves existing normalized fields when present and
    fills them from a sanitized ``run_kernel`` projection when they are absent.
    """

    payload = _safe_mapping(observed)
    kernel = _run_kernel_payload(payload)
    if kernel:
        payload.setdefault("contract", _first_mapping(kernel, "run_contract_projection", "run_contract"))
        payload.setdefault("ledger", _first_mapping(kernel, "evidence_ledger"))
        payload.setdefault(
            "sufficiency",
            _first_mapping(
                kernel,
                "sufficiency_judgment_projection",
                "sufficiency_judgment",
            ),
        )
        payload.setdefault("final_packet", _first_mapping(kernel, "final_answer_packet"))

    custody = build_final_evidence_citation_custody_projection(payload)
    if custody["status"] != "not_observed":
        payload.setdefault("final_evidence_citation_custody_projection", custody)

    final_answer = _mapping(payload.get("final_answer"))
    if final_answer and not final_answer.get("citations"):
        derived_citations = _derive_final_answer_citations(custody)
        if derived_citations:
            payload["final_answer"] = {**final_answer, "citations": derived_citations}
    return payload


def build_final_evidence_citation_custody_projection(
    observed: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Project final evidence/citation refs from canonical sanitized state."""

    payload = _safe_mapping(observed)
    kernel = _run_kernel_payload(payload)
    ledger = _first_mapping(payload, "ledger", "evidence_ledger", "evidence_ledger_projection")
    packet = _first_mapping(payload, "final_packet", "final_answer_packet", "final_answer_packet_projection")
    if kernel:
        ledger = ledger or _first_mapping(kernel, "evidence_ledger")
        packet = packet or _first_mapping(kernel, "final_answer_packet")

    controller_custody = _controller_custody_payload(payload)
    evidence_refs = _final_evidence_refs(packet, ledger)
    citation_refs = _final_citation_refs(packet)
    packet_projected = bool(packet and (evidence_refs or citation_refs))

    if packet_projected:
        status = "final_answer_packet_custody_projected"
    elif _legacy_gap_observed(controller_custody):
        status = "legacy_gap_observed"
    elif evidence_refs or citation_refs:
        status = "legacy_parallel_path_classified"
    else:
        status = "not_observed"

    legacy_status = _clean_text(controller_custody.get("status")) or UNKNOWN
    legacy_gap_types = _strings(controller_custody.get("legacy_gap_types"))
    return {
        "schema_version": FINAL_EVIDENCE_CITATION_CUSTODY_PROJECTION_SCHEMA_VERSION,
        "owner": "RunKernel.FinalAnswerPacket",
        "status": status,
        "custody_complete": status == "final_answer_packet_custody_projected",
        "projection_source": (
            "RunKernel.FinalAnswerPacket"
            if packet_projected
            else "ControllerEvidenceLedger"
            if controller_custody
            else "not_observed"
        ),
        "ag93c_normalized_snapshot_compatible": packet_projected,
        "final_answer_packet_ref": _packet_ref(packet),
        "evidence_ledger_ref": _ledger_ref(ledger),
        "final_evidence_refs": evidence_refs,
        "final_citation_refs": citation_refs,
        "legacy_controller_custody": {
            "owner": _clean_text(controller_custody.get("owner")) or UNKNOWN,
            "status": legacy_status,
            "custody_complete": bool(controller_custody.get("custody_complete")),
            "legacy_gap_types": legacy_gap_types,
            "old_path_classification": _clean_text(
                controller_custody.get("old_path_classification")
            )
            or UNKNOWN,
        },
        "legacy_parallel_path_classification": (
            "classified_legacy_not_complete"
            if _legacy_gap_observed(controller_custody)
            else "no_legacy_gap_observed"
        ),
        "legacy_gap_observed": _legacy_gap_observed(controller_custody),
        "behavior_changed": False,
        "runtime_behavior_changed": False,
    }


def _derive_final_answer_citations(custody: Mapping[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for ref in _mapping_list(custody.get("final_citation_refs")):
        source_id = ref.get("source_id")
        if source_id in (None, ""):
            continue
        citations.append(
            {
                "source_ids": [source_id],
                "citation_id": ref.get("citation_id"),
                "evidence_id": ref.get("evidence_id"),
                "custody_source": ref.get("custody_source"),
            }
        )
    return citations


def _final_evidence_refs(
    packet: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidates = _ledger_candidate_index(ledger)
    refs: list[dict[str, Any]] = []
    for record in _mapping_list(packet.get("evidence_allowed")):
        source_id = record.get("source_id")
        url = _clean_text(record.get("url"))
        candidate_id = _matched_candidate_id(record, candidates)
        refs.append(
            _compact(
                {
                    "evidence_id": _clean_text(record.get("evidence_id")),
                    "source_id": source_id,
                    "url": url,
                    "title": _clean_text(record.get("title")),
                    "source_class": _clean_text(record.get("source_class")),
                    "source_tier": _clean_text(record.get("source_tier")),
                    "ledger_candidate_id": candidate_id,
                    "custody_source": "RunKernel.FinalAnswerPacket.evidence_allowed",
                    "ledger_candidate_matched": bool(candidate_id),
                }
            )
        )
    return refs


def _final_citation_refs(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for record in _mapping_list(packet.get("citation_eligible")):
        refs.append(
            _compact(
                {
                    "citation_id": _clean_text(record.get("citation_id")),
                    "evidence_id": _clean_text(record.get("evidence_id")),
                    "source_id": record.get("source_id"),
                    "requirement": _clean_text(record.get("requirement")),
                    "custody_source": "RunKernel.FinalAnswerPacket.citation_eligible",
                }
            )
        )
    return refs


def _ledger_candidate_index(ledger: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for candidate in _mapping_list(ledger.get("candidate_records")):
        candidate_id = _clean_text(candidate.get("candidate_id"))
        if not candidate_id:
            continue
        for key in (
            candidate_id,
            _clean_text(candidate.get("source_id")),
            _clean_text(candidate.get("url")),
            _clean_text(candidate.get("normalized_source_identity")),
        ):
            if key:
                out[key] = candidate_id
    for ref in _mapping_list(ledger.get("final_evidence_refs")):
        candidate_id = _clean_text(ref.get("candidate_id"))
        if not candidate_id:
            continue
        for key in (
            candidate_id,
            _clean_text(ref.get("source_id")),
            _clean_text(ref.get("url")),
        ):
            if key:
                out.setdefault(key, candidate_id)
    return out


def _matched_candidate_id(
    record: Mapping[str, Any],
    candidates: Mapping[str, str],
) -> str | None:
    for key in (
        _clean_text(record.get("source_id")),
        _clean_text(record.get("url")),
        _clean_text(record.get("evidence_id")),
    ):
        if key and key in candidates:
            return candidates[key]
    return None


def _packet_ref(packet: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "packet_id": _clean_text(packet.get("packet_id")),
            "readiness_status": _clean_text(packet.get("readiness_status")),
            "evidence_allowed_count": len(_mapping_list(packet.get("evidence_allowed"))),
            "citation_eligible_count": len(_mapping_list(packet.get("citation_eligible"))),
            "trace_mode": _clean_text(packet.get("trace_mode")),
        }
    )


def _ledger_ref(ledger: Mapping[str, Any]) -> dict[str, Any]:
    compatibility = _mapping(ledger.get("compatibility"))
    return _compact(
        {
            "owner": _clean_text(ledger.get("owner")),
            "candidate_count": ledger.get("candidate_count"),
            "requirement_count": ledger.get("requirement_count"),
            "final_evidence_ref_count": len(_mapping_list(ledger.get("final_evidence_refs"))),
            "final_evidence_compatibility_gap_count": compatibility.get(
                "final_evidence_compatibility_gap_count"
            ),
        }
    )


def _controller_custody_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    for key in ("controller_evidence_ledger", "controller_evidence_ledger_projection"):
        ledger = _mapping(payload.get(key))
        nested = _mapping(ledger.get("ControllerEvidenceLedger"))
        if nested:
            ledger = nested
        custody = _mapping(ledger.get("final_evidence_citation_custody"))
        if custody:
            return custody
    trace = _mapping(payload.get("official_canonical_recovery_visibility_export"))
    status = trace.get("final_evidence_citation_custody_status")
    if status:
        return {
            "owner": trace.get("final_evidence_citation_custody_owner"),
            "status": status,
            "custody_complete": trace.get("final_evidence_citation_custody_complete"),
            "legacy_gap_types": trace.get("ledger_legacy_gap_types"),
        }
    return {}


def _legacy_gap_observed(custody: Mapping[str, Any]) -> bool:
    status = _clean_text(custody.get("status"))
    gaps = _strings(custody.get("legacy_gap_types"))
    return status == "legacy_gap_observed" or bool(gaps)


def _run_kernel_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    kernel = _mapping(payload.get("run_kernel"))
    if kernel:
        return kernel
    return {}


def _first_mapping(payload: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = _mapping(payload.get(key))
        if value:
            return value
    return {}


def _mapping(value: Any) -> dict[str, Any]:
    return _safe_mapping(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        return [_safe_mapping(value)]
    if not isinstance(value, (list, tuple)):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(_safe_mapping(item))
        if len(out) >= _MAX_LIST_ITEMS:
            break
    return out


def _strings(value: Any) -> list[str]:
    raw = value if isinstance(value, (list, tuple, set, frozenset)) else [value]
    out: list[str] = []
    for item in raw:
        text = _clean_text(item)
        if text and text not in out:
            out.append(text)
    return out


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key or "")
        if _is_sensitive_key(key_text):
            continue
        safe = _safe_value(item)
        if safe is not None:
            out[key_text] = safe
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in list(value)[:_MAX_LIST_ITEMS]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:_MAX_LIST_ITEMS]]
    return _clean_text(value)


def _clean_text(value: Any, *, limit: int = 240) -> str:
    if value is None:
        return ""
    text = " ".join(str(value or "").strip().split())
    return text[:limit] if text else ""


def _is_sensitive_key(key: Any) -> bool:
    text = str(key or "").casefold()
    return any(marker in text for marker in _SENSITIVE_KEY_MARKERS)


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


__all__ = [
    "FINAL_EVIDENCE_CITATION_CUSTODY_PROJECTION_SCHEMA_VERSION",
    "build_ag93c_observed_snapshot_projection",
    "build_final_evidence_citation_custody_projection",
]
