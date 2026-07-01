"""Product-facing citation/source-obligation readiness posture status.

This module backs a default-off ordinary CLI status path. It consumes retained
sanitized search-candidate, fetch/read, and source/evidence custody status, then
prints only the next citation/source-obligation readiness posture. It performs
no live calls and does not produce answer prose, citation eligibility, rendered
citations, source-obligation satisfaction, or correctness claims.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.search_result_candidate_packet import (
    SearchResultCandidatePacketError,
    validate_search_result_candidate_packet,
)
from proplex.live_source_evidence_admission_status import (
    PASS_DECISION,
    SEARCH_ARTIFACT_DIR,
    SEARCH_CANDIDATE_PACKET_NAME,
    SEARCH_RESULT_CANDIDATE_PACKET_NAME,
    build_live_source_evidence_admission_status,
)

PHASE = "AG-LIVE-CITATION-SOURCE-OBLIGATION-READINESS-PRODUCT-CONSUMPTION-01"
MODE = "BUILD"
USABLE_ANSWER_VERDICT_TARGET = "YES"
LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG = (
    "--live-citation-source-obligation-readiness-status-dry-run"
)

BLOCKED_ENTRYPOINT_MISSING = "BLOCKED_ENTRYPOINT_MISSING"
BLOCKED_RETAINED_ARTIFACT_PREFLIGHT = "BLOCKED_RETAINED_ARTIFACT_PREFLIGHT"
BLOCKED_FETCH_READ_ARTIFACT_MISSING = "BLOCKED_FETCH_READ_ARTIFACT_MISSING"
BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE = "BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE"
BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE = "BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE"
BLOCKED_FETCH_READ_ARTIFACT_LINEAGE = "BLOCKED_FETCH_READ_ARTIFACT_LINEAGE"
BLOCKED_SOURCE_EVIDENCE_STATUS = "BLOCKED_SOURCE_EVIDENCE_STATUS"
BLOCKED_CITATION_SOURCE_OBLIGATION_CONSUMER_MISSING = (
    "BLOCKED_CITATION_SOURCE_OBLIGATION_CONSUMER_MISSING"
)
BLOCKED_CITATION_SOURCE_OBLIGATION_READINESS = (
    "BLOCKED_CITATION_SOURCE_OBLIGATION_READINESS"
)
BLOCKED_CITATION_SOURCE_OBLIGATION_RAW_PRIVATE = (
    "BLOCKED_CITATION_SOURCE_OBLIGATION_RAW_PRIVATE"
)
BLOCKED_OUTPUT_HYGIENE = "BLOCKED_OUTPUT_HYGIENE"
BLOCKED_CLOSED_SURFACE_VIOLATION = "BLOCKED_CLOSED_SURFACE_VIOLATION"
BLOCKED_PRODUCT_IMPORT_BOUNDARY = "BLOCKED_PRODUCT_IMPORT_BOUNDARY"

READINESS_MACHINERY = (
    "proplex.live_source_evidence_admission_status custody status plus "
    "lineage-only citation/source-obligation readiness posture adapter"
)
NEXT_BLOCKED_SURFACE = (
    "semantic support/admission and component coverage product consumption"
)
CLOSED_DOWNSTREAM_SURFACES = (
    "SemanticObservation",
    "ComponentCoverage",
    "semantic support/admission",
    "component coverage/binding",
    "citation eligibility claim",
    "citation rendering",
    "source-obligation satisfaction",
    "SufficiencyReadiness",
    "FinalAnswerPacket",
    "Author/AuthorProse",
    "answer text",
    "product correctness",
)
EXPLICIT_NON_CLAIM = (
    "This phase does not prove semantic support, component coverage, citation "
    "eligibility, citation rendering, source-obligation satisfaction, "
    "SufficiencyReadiness, FinalAnswerPacket readiness, Author behavior, "
    "answer prose, answerability, or product correctness."
)

_SOURCE_STATUS_BLOCKER_MAP = {
    "BLOCKED_RETAINED_ARTIFACT_PREFLIGHT": BLOCKED_RETAINED_ARTIFACT_PREFLIGHT,
    "BLOCKED_FETCH_READ_ARTIFACT_MISSING": BLOCKED_FETCH_READ_ARTIFACT_MISSING,
    "BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE": BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
    "BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE": BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE,
    "BLOCKED_FETCH_READ_ARTIFACT_LINEAGE": BLOCKED_FETCH_READ_ARTIFACT_LINEAGE,
    "BLOCKED_SOURCE_EVIDENCE_CONSUMER_MISSING": BLOCKED_SOURCE_EVIDENCE_STATUS,
    "BLOCKED_SOURCE_EVIDENCE_ADMISSION": BLOCKED_SOURCE_EVIDENCE_STATUS,
    "BLOCKED_SOURCE_EVIDENCE_RAW_PRIVATE": (
        BLOCKED_CITATION_SOURCE_OBLIGATION_RAW_PRIVATE
    ),
    "BLOCKED_OUTPUT_HYGIENE": BLOCKED_OUTPUT_HYGIENE,
    "BLOCKED_CLOSED_SURFACE_VIOLATION": BLOCKED_CLOSED_SURFACE_VIOLATION,
}
_ADMISSION_FALSE_KEYS = frozenset(
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
_OUTPUT_FORBIDDEN_TOKENS = frozenset(
    {
        "bounded_text",
        "raw_html",
        "raw page",
        "raw_page_text",
        "raw_page_content",
        "headers:",
        "cookies",
        "provider_payload",
        "search response payload",
        "model_response",
        "prompt:",
        "answer prose:",
        "citation_ready",
        "citation ready",
    }
)


@dataclass(frozen=True, slots=True)
class LiveCitationSourceObligationReadinessStatusResult:
    decision: str
    output: str
    payload: Mapping[str, Any]

    @property
    def return_code(self) -> int:
        return 0 if self.decision == PASS_DECISION else 2


class LiveCitationSourceObligationReadinessStatusError(ValueError):
    """Raised for unexpected citation/source-obligation status failures."""


def build_live_citation_source_obligation_readiness_status(
    *,
    query: str,
    repo_root: str | Path,
) -> LiveCitationSourceObligationReadinessStatusResult:
    """Consume retained custody status and return a CLI-safe readiness posture."""

    root = _resolve_root(repo_root)
    source_status = build_live_source_evidence_admission_status(
        query=query,
        repo_root=root,
    )
    if source_status.decision != PASS_DECISION:
        return _blocked_from_source_status(
            query=query,
            source_decision=source_status.decision,
        )

    source_payload = _safe_mapping(source_status.payload)
    admission_ref = _safe_mapping(source_payload.get("source_evidence_admission_ref"))
    if source_payload.get("raw_private_retention") is not False:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_CITATION_SOURCE_OBLIGATION_RAW_PRIVATE,
            detail="source/evidence status did not preserve raw/private false posture",
        )
    if admission_ref.get("status") != "custody_created":
        return _blocked_result(
            query=query,
            blocker=BLOCKED_SOURCE_EVIDENCE_STATUS,
            detail="source/evidence custody status is not custody_created",
        )
    if _admission_opens_closed_surface(admission_ref):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_CLOSED_SURFACE_VIOLATION,
            detail="source/evidence custody status opened a closed downstream surface",
        )

    try:
        selected_candidate = _selected_candidate_from_retained_packet(
            root=root,
            admission_ref=admission_ref,
        )
    except (
        OSError,
        json.JSONDecodeError,
        SearchResultCandidatePacketError,
        LiveCitationSourceObligationReadinessStatusError,
    ) as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_LINEAGE,
            detail=f"retained candidate lineage could not be verified: {exc}",
        )

    component_ref = _component_ref(selected_candidate)
    source_obligation_ref = _source_obligation_ref(selected_candidate)
    readiness_ref = _readiness_ref(
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        admission_ref=admission_ref,
    )

    payload = _pass_payload(
        query=query,
        source_payload=source_payload,
        admission_ref=admission_ref,
        selected_candidate=selected_candidate,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        readiness_ref=readiness_ref,
    )
    output = format_live_citation_source_obligation_readiness_status(payload)
    if not output_hygiene_passes(output):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_OUTPUT_HYGIENE,
            detail="status output contained forbidden material",
        )
    return LiveCitationSourceObligationReadinessStatusResult(
        decision=PASS_DECISION,
        output=output,
        payload=payload,
    )


def format_live_citation_source_obligation_readiness_status(
    payload: Mapping[str, Any],
) -> str:
    """Format concise CLI readiness status without answer prose or readable text."""

    selected = _safe_mapping(payload.get("selected_candidate"))
    admission = _safe_mapping(payload.get("source_evidence_admission_ref"))
    readiness = _safe_mapping(payload.get("citation_source_obligation_readiness_ref"))
    closed = payload.get("closed_downstream_surfaces") or CLOSED_DOWNSTREAM_SURFACES
    closed_text = ", ".join(str(item) for item in closed)
    return "\n".join(
        (
            "live citation/source-obligation readiness status",
            f"phase: {PHASE}",
            f"mode: {MODE}",
            f"ordinary entrypoint: {payload.get('ordinary_entrypoint')}",
            f"user-style query: {payload.get('user_style_query')}",
            (
                "retained search candidate status: "
                f"{payload.get('retained_search_candidate_status')}"
            ),
            f"selected candidate rank: {selected.get('rank')}",
            f"selected candidate domain: {selected.get('domain')}",
            f"selected candidate URL: {selected.get('url')}",
            f"candidate lineage status: {payload.get('candidate_lineage_status')}",
            f"fetch/read handoff status: {payload.get('fetch_read_handoff_status')}",
            f"source/evidence custody/admission status: {admission.get('status')}",
            f"source/evidence custody/admission owner: {admission.get('owner')}",
            f"source/evidence custody records: {admission.get('custody_record_count')}",
            (
                "source/evidence readable custody records: "
                f"{admission.get('readable_record_count')}"
            ),
            (
                "citation/source-obligation readiness machinery: "
                f"{payload.get('readiness_machinery')}"
            ),
            (
                "citation/source-obligation readiness posture: "
                f"{readiness.get('posture')}"
            ),
            f"readiness reasons: {', '.join(readiness.get('reasons') or [])}",
            (
                "source obligation id/ref: "
                f"{_format_source_obligation_ref(payload.get('source_obligation_ref'))}"
            ),
            f"component id/ref: {_format_component_ref(payload.get('component_ref'))}",
            (
                "citation/source-obligation next blocked surface: "
                f"{readiness.get('next_blocked_surface')}"
            ),
            f"raw/private retention: {_bool_text(payload.get('raw_private_retention'))}",
            f"closed downstream surfaces: {closed_text}",
            f"usable-answer verdict target: {payload.get('usable_answer_verdict_target')}",
            "answerability/correctness: not claimed",
            (
                "current status path live calls: provider/search/broker/fetch/read/"
                "retrieval/model = 0"
            ),
            str(payload.get("non_claim")),
            f"decision: {payload.get('decision')}",
        )
    )


def output_hygiene_passes(output: str) -> bool:
    lowered = output.casefold()
    return not any(token in lowered for token in _OUTPUT_FORBIDDEN_TOKENS)


def _selected_candidate_from_retained_packet(
    *,
    root: Path,
    admission_ref: Mapping[str, Any],
) -> dict[str, Any]:
    search_dir = root / SEARCH_ARTIFACT_DIR
    search_candidate_packet = validate_search_result_candidate_packet(
        _read_json(search_dir / SEARCH_CANDIDATE_PACKET_NAME)
    )
    search_result_candidate_packet = validate_search_result_candidate_packet(
        _read_json(search_dir / SEARCH_RESULT_CANDIDATE_PACKET_NAME)
    )
    if search_candidate_packet.get("packet_digest") != search_result_candidate_packet.get(
        "packet_digest"
    ):
        raise LiveCitationSourceObligationReadinessStatusError(
            "search candidate packet digest does not match search result packet"
        )
    candidate_id = _clean_text(admission_ref.get("candidate_id"), limit=320)
    if not candidate_id:
        raise LiveCitationSourceObligationReadinessStatusError(
            "source/evidence custody ref is missing candidate_id"
        )
    candidates = [
        _safe_mapping(record)
        for record in _safe_list(search_result_candidate_packet.get("candidate_records"))
        if isinstance(record, Mapping)
    ]
    for candidate in candidates:
        if _clean_text(candidate.get("candidate_id"), limit=320) == candidate_id:
            return candidate
    raise LiveCitationSourceObligationReadinessStatusError(
        "source/evidence custody candidate_id is absent from retained packet"
    )


def _readiness_ref(
    *,
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
) -> dict[str, Any]:
    if not component_ref.get("component_id"):
        return {
            "posture": "missing_contract_component",
            "reasons": [
                "retained candidate has no product-consumable component id",
                "citation/source-obligation progression cannot bind to a component",
            ],
            "next_blocked_surface": "contract component lineage product consumption",
        }
    if not source_obligation_ref.get("source_obligation_candidate_ids"):
        return {
            "posture": "missing_source_obligation",
            "reasons": [
                "retained candidate has no source-obligation candidate id",
                "source-obligation progression cannot bind a requirement ref",
            ],
            "next_blocked_surface": "source-obligation lineage product consumption",
        }
    if admission_ref.get("candidate_content_custody_is_semantic_support") is False:
        return {
            "posture": "not_yet_semantically_supported",
            "reasons": [
                "source/evidence custody is visible",
                "custody is not semantic support",
                "SemanticObservation and ComponentCoverage remain closed",
                "citation eligibility and source-obligation satisfaction remain unclaimed",
            ],
            "next_blocked_surface": NEXT_BLOCKED_SURFACE,
        }
    return {
        "posture": "blocked",
        "reasons": ["source/evidence custody posture is not safely reducible"],
        "next_blocked_surface": "source/evidence custody posture repair",
    }


def _component_ref(candidate: Mapping[str, Any]) -> dict[str, Any]:
    component_id = _clean_text(candidate.get("component_id"), limit=260)
    if not component_id:
        return {}
    contract_ref = _safe_mapping(candidate.get("current_answer_contract_ref"))
    return _without_empty(
        {
            "component_id": component_id,
            "source": "SearchResultCandidatePacket.candidate_records",
            "current_answer_contract_digest": contract_ref.get("contract_digest")
            or candidate.get("current_answer_contract_digest"),
            "lineage_only": True,
            "component_coverage_bound": False,
        }
    )


def _source_obligation_ref(candidate: Mapping[str, Any]) -> dict[str, Any]:
    ids = _text_list(candidate.get("source_obligation_candidate_ids"))
    if not ids:
        return {}
    return {
        "source_obligation_candidate_ids": ids,
        "source": "SearchResultCandidatePacket.candidate_records",
        "lineage_only": True,
        "satisfaction_claimed": False,
    }


def _pass_payload(
    *,
    query: str,
    source_payload: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    selected_candidate: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
) -> dict[str, Any]:
    selected = _safe_mapping(source_payload.get("selected_candidate"))
    return {
        "phase": PHASE,
        "mode": MODE,
        "ordinary_entrypoint": "python -m proplex",
        "user_style_query": _clean_query(query),
        "retained_search_candidate_status": source_payload.get(
            "retained_search_candidate_status",
            "preflight_passed",
        ),
        "retained_search_candidate_count": _bounded_int(
            source_payload.get("retained_search_candidate_count")
        ),
        "selected_candidate": {
            "rank": selected.get("rank")
            or _bounded_int(selected_candidate.get("result_rank")),
            "domain": selected.get("domain") or selected_candidate.get("domain"),
            "url": selected.get("url") or selected_candidate.get("url"),
        },
        "candidate_lineage_status": source_payload.get(
            "candidate_lineage_status",
            "preserved",
        ),
        "fetch_read_handoff_status": source_payload.get("fetch_read_handoff_status"),
        "source_evidence_admission_ref": dict(admission_ref),
        "readiness_machinery": READINESS_MACHINERY,
        "citation_source_obligation_readiness_ref": dict(readiness_ref),
        "component_ref": dict(component_ref),
        "source_obligation_ref": dict(source_obligation_ref),
        "raw_private_retention": False,
        "closed_downstream_surfaces": CLOSED_DOWNSTREAM_SURFACES,
        "usable_answer_verdict_target": USABLE_ANSWER_VERDICT_TARGET,
        "answerability_correctness": "not claimed",
        "non_claim": EXPLICIT_NON_CLAIM,
        "decision": PASS_DECISION,
    }


def _blocked_from_source_status(
    *,
    query: str,
    source_decision: str,
) -> LiveCitationSourceObligationReadinessStatusResult:
    blocker = _SOURCE_STATUS_BLOCKER_MAP.get(
        source_decision,
        BLOCKED_SOURCE_EVIDENCE_STATUS,
    )
    return _blocked_result(
        query=query,
        blocker=blocker,
        detail=f"source/evidence status decision: {source_decision}",
    )


def _blocked_result(
    *,
    query: str,
    blocker: str,
    detail: str,
) -> LiveCitationSourceObligationReadinessStatusResult:
    payload = {
        "phase": PHASE,
        "mode": MODE,
        "ordinary_entrypoint": "python -m proplex",
        "user_style_query": _clean_query(query),
        "usable_answer_verdict_target": USABLE_ANSWER_VERDICT_TARGET,
        "answerability_correctness": "not claimed",
        "blocker_detail": detail,
        "decision": blocker,
    }
    output = "\n".join(
        (
            "live citation/source-obligation readiness status blocked",
            f"phase: {PHASE}",
            f"mode: {MODE}",
            "ordinary entrypoint: python -m proplex",
            f"user-style query: {payload['user_style_query']}",
            f"usable-answer verdict target: {USABLE_ANSWER_VERDICT_TARGET}",
            "answerability/correctness: not claimed",
            f"blocker: {blocker}",
            f"blocker detail: {detail}",
            f"next blocked surface: {NEXT_BLOCKED_SURFACE}",
            f"decision: {blocker}",
        )
    )
    return LiveCitationSourceObligationReadinessStatusResult(
        decision=blocker,
        output=output,
        payload=payload,
    )


def _admission_opens_closed_surface(admission_ref: Mapping[str, Any]) -> bool:
    for key in _ADMISSION_FALSE_KEYS:
        if admission_ref.get(key) is not False:
            return True
    flags = _safe_mapping(admission_ref.get("behavior_boundary_flags"))
    for key, value in flags.items():
        if key in _ADMISSION_FALSE_KEYS and value is not False:
            return True
    return False


def _format_component_ref(value: Any) -> str:
    ref = _safe_mapping(value)
    component_id = _clean_text(ref.get("component_id"), limit=260)
    if not component_id:
        return "unavailable"
    digest = _clean_text(ref.get("current_answer_contract_digest"), limit=128)
    suffix = f"; contract_digest={digest}" if digest else ""
    return f"{component_id} (lineage-only{suffix}; coverage not bound)"


def _format_source_obligation_ref(value: Any) -> str:
    ref = _safe_mapping(value)
    ids = _text_list(ref.get("source_obligation_candidate_ids"))
    if not ids:
        return "unavailable"
    return ", ".join(ids) + " (lineage-only; satisfaction not claimed)"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_root(path: str | Path) -> Path:
    return Path(path).resolve()


def _path_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        normalized_path = os.path.normcase(str(path))
        normalized_root = os.path.normcase(str(root))
        return normalized_path == normalized_root or normalized_path.startswith(
            normalized_root.rstrip("\\/") + os.sep
        )


def _clean_query(query: str) -> str:
    return " ".join(str(query or "").strip().split())


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _text_list(value: Any, *, limit: int = 160) -> list[str]:
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


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _bool_text(value: Any) -> str:
    return "true" if value is True else "false"


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


__all__ = [
    "LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG",
    "LiveCitationSourceObligationReadinessStatusError",
    "LiveCitationSourceObligationReadinessStatusResult",
    "build_live_citation_source_obligation_readiness_status",
    "format_live_citation_source_obligation_readiness_status",
    "output_hygiene_passes",
]
