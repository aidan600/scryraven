"""Product-facing retained live acquisition/readability status.

This module backs a default-off ordinary CLI status path. It consumes retained
sanitized search-candidate and fetch/read artifacts, performs no live calls, and
prints only acquisition/readability status. It does not produce answer prose or
claim answerability/correctness.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.fetch_read_content_reference import (
    FetchReadContentReferenceError,
    validate_fetch_read_content_packet,
)
from core.retained_live_artifact_preflight import (
    RETAINED_ARTIFACT_PREFLIGHT_PASS,
    preflight_retained_live_artifacts,
)
from core.search_result_candidate_packet import (
    SearchResultCandidatePacketError,
    validate_search_result_candidate_packet,
)

PHASE = "AG-LIVE-ACQUISITION-READABILITY-PRODUCT-CONSUMPTION-01"
MODE = "BUILD"
USABLE_ANSWER_VERDICT_TARGET = "YES"
LIVE_ACQUISITION_READABILITY_STATUS_FLAG = (
    "--live-acquisition-readability-status-dry-run"
)

SEARCH_ARTIFACT_DIR = Path("output") / "ag_live_ordinary_search_candidate_01b"
FETCH_READ_ARTIFACT_DIR = Path("output") / "ag_live_source_survival_fetch_read_01"
SANITIZED_PROVIDER_RESULTS_NAME = "sanitized_provider_results.json"
SEARCH_CANDIDATE_PACKET_NAME = "search_candidate_packet.json"
SEARCH_RESULT_CANDIDATE_PACKET_NAME = "search_result_candidate_packet.json"
LIVE_SOURCE_SURVIVAL_SUMMARY_NAME = "live_source_survival_summary.json"
FETCH_READ_CONTENT_PACKET_NAME = "fetch_read_content_packet.json"

PASS_DECISION = "PASS"
BLOCKED_RETAINED_ARTIFACT_PREFLIGHT = "BLOCKED_RETAINED_ARTIFACT_PREFLIGHT"
BLOCKED_FETCH_READ_ARTIFACT_MISSING = "BLOCKED_FETCH_READ_ARTIFACT_MISSING"
BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE = "BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE"
BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE = "BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE"
BLOCKED_FETCH_READ_ARTIFACT_LINEAGE = "BLOCKED_FETCH_READ_ARTIFACT_LINEAGE"
BLOCKED_OUTPUT_HYGIENE = "BLOCKED_OUTPUT_HYGIENE"
BLOCKED_CLOSED_SURFACE_VIOLATION = "BLOCKED_CLOSED_SURFACE_VIOLATION"

NEXT_BLOCKED_SURFACE = "source/evidence admission product consumption"
CLOSED_DOWNSTREAM_SURFACES = (
    "EvidenceLedger admission",
    "SemanticObservation",
    "ComponentCoverage",
    "citation eligibility/rendering",
    "source-obligation satisfaction",
    "SufficiencyReadiness",
    "FinalAnswerPacket",
    "Author/AuthorProse",
    "answer text",
    "product correctness",
)
EXPLICIT_NON_CLAIM = (
    "This phase does not claim answerability, final-answer correctness, "
    "citation readiness, source-obligation satisfaction, Author behavior, or "
    "product correctness."
)

_RAW_PRIVATE_RETENTION_KEYS = frozenset(
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
_CLOSED_FALSE_KEYS = frozenset(
    {
        "evidence_ledger_admitted",
        "evidence_created",
        "citation_eligible",
        "citation_created",
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
        "final answer",
    }
)


@dataclass(frozen=True, slots=True)
class LiveAcquisitionReadabilityStatusResult:
    decision: str
    output: str
    payload: Mapping[str, Any]

    @property
    def return_code(self) -> int:
        return 0 if self.decision == PASS_DECISION else 2


class LiveAcquisitionReadabilityStatusError(ValueError):
    """Raised for unexpected status-consumer failures."""


def build_live_acquisition_readability_status(
    *,
    query: str,
    repo_root: str | Path,
) -> LiveAcquisitionReadabilityStatusResult:
    """Consume retained artifacts and return a CLI-safe status result."""

    root = _resolve_root(repo_root)
    search_dir = root / SEARCH_ARTIFACT_DIR
    fetch_dir = root / FETCH_READ_ARTIFACT_DIR

    preflight = preflight_retained_live_artifacts(
        artifact_dir=search_dir,
        repo_root=root,
    )
    preflight_decision = str(preflight.get("decision") or "")
    if preflight_decision != RETAINED_ARTIFACT_PREFLIGHT_PASS:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_RETAINED_ARTIFACT_PREFLIGHT,
            detail=f"retained search preflight decision: {preflight_decision}",
        )

    try:
        search_candidate_packet = validate_search_result_candidate_packet(
            _read_json(search_dir / SEARCH_CANDIDATE_PACKET_NAME)
        )
        search_result_candidate_packet = validate_search_result_candidate_packet(
            _read_json(search_dir / SEARCH_RESULT_CANDIDATE_PACKET_NAME)
        )
    except (OSError, json.JSONDecodeError, SearchResultCandidatePacketError) as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_RETAINED_ARTIFACT_PREFLIGHT,
            detail=f"retained search artifact validation failed: {exc}",
        )

    try:
        _require_under_repo_output(fetch_dir, root)
        fetch_summary = _read_json(fetch_dir / LIVE_SOURCE_SURVIVAL_SUMMARY_NAME)
        fetch_packet = validate_fetch_read_content_packet(
            _read_json(fetch_dir / FETCH_READ_CONTENT_PACKET_NAME)
        )
    except FileNotFoundError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_MISSING,
            detail=f"missing fetch/read artifact: {Path(exc.filename or '').name}",
        )
    except PermissionError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
            detail=f"unreadable fetch/read artifact: {Path(exc.filename or '').name}",
        )
    except json.JSONDecodeError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
            detail=f"fetch/read artifact is not JSON: {exc.msg}",
        )
    except FetchReadContentReferenceError as exc:
        blocker = (
            BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE
            if _looks_raw_private_error(str(exc))
            else BLOCKED_FETCH_READ_ARTIFACT_LINEAGE
        )
        return _blocked_result(query=query, blocker=blocker, detail=str(exc))
    except LiveAcquisitionReadabilityStatusError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_LINEAGE,
            detail=str(exc),
        )
    except OSError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
            detail=f"could not read fetch/read artifact: {exc}",
        )

    summary_status = _verify_fetch_read_summary(fetch_summary)
    if summary_status == BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE,
            detail="fetch/read summary retained raw/private material",
        )
    if summary_status == BLOCKED_CLOSED_SURFACE_VIOLATION:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_CLOSED_SURFACE_VIOLATION,
            detail="fetch/read summary opened a closed downstream surface",
        )

    try:
        selected_candidate, reference = _select_and_verify_lineage(
            search_candidate_packet=search_candidate_packet,
            search_result_candidate_packet=search_result_candidate_packet,
            fetch_packet=fetch_packet,
        )
    except LiveAcquisitionReadabilityStatusError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_LINEAGE,
            detail=str(exc),
        )

    payload = _pass_payload(
        query=query,
        preflight=preflight,
        selected_candidate=selected_candidate,
        reference=reference,
        fetch_packet=fetch_packet,
    )
    output = format_live_acquisition_readability_status(payload)
    if not output_hygiene_passes(output):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_OUTPUT_HYGIENE,
            detail="status output contained forbidden material",
        )
    return LiveAcquisitionReadabilityStatusResult(
        decision=PASS_DECISION,
        output=output,
        payload=payload,
    )


def format_live_acquisition_readability_status(payload: Mapping[str, Any]) -> str:
    """Format a concise CLI status without answer prose or readable text."""

    selected = _safe_mapping(payload.get("selected_candidate"))
    closed = payload.get("closed_downstream_surfaces") or CLOSED_DOWNSTREAM_SURFACES
    closed_text = ", ".join(str(item) for item in closed)
    return "\n".join(
        (
            "live acquisition/readability status",
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
            f"readability status: {payload.get('readability_status')}",
            (
                "sanitized content reference present: "
                f"{_bool_text(payload.get('sanitized_content_reference_present'))}"
            ),
            f"raw/private retention: {_bool_text(payload.get('raw_private_retention'))}",
            f"closed downstream surfaces: {closed_text}",
            f"next blocked surface: {payload.get('next_blocked_surface')}",
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


def _pass_payload(
    *,
    query: str,
    preflight: Mapping[str, Any],
    selected_candidate: Mapping[str, Any],
    reference: Mapping[str, Any],
    fetch_packet: Mapping[str, Any],
) -> dict[str, Any]:
    del fetch_packet
    return {
        "phase": PHASE,
        "mode": MODE,
        "ordinary_entrypoint": "python -m proplex",
        "user_style_query": _clean_query(query),
        "retained_search_candidate_status": "preflight_passed",
        "retained_search_candidate_count": _bounded_int(preflight.get("candidate_count")),
        "selected_candidate": {
            "rank": _bounded_int(selected_candidate.get("result_rank")),
            "domain": selected_candidate.get("domain"),
            "url": selected_candidate.get("url"),
        },
        "candidate_lineage_status": "preserved",
        "fetch_read_handoff_status": "retained_packet_verified",
        "readability_status": reference.get("fetch_read_status"),
        "sanitized_content_reference_present": True,
        "raw_private_retention": False,
        "closed_downstream_surfaces": CLOSED_DOWNSTREAM_SURFACES,
        "next_blocked_surface": NEXT_BLOCKED_SURFACE,
        "usable_answer_verdict_target": USABLE_ANSWER_VERDICT_TARGET,
        "answerability_correctness": "not claimed",
        "non_claim": EXPLICIT_NON_CLAIM,
        "decision": PASS_DECISION,
    }


def _blocked_result(
    *,
    query: str,
    blocker: str,
    detail: str,
) -> LiveAcquisitionReadabilityStatusResult:
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
            "live acquisition/readability status blocked",
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
    return LiveAcquisitionReadabilityStatusResult(
        decision=blocker,
        output=output,
        payload=payload,
    )


def _select_and_verify_lineage(
    *,
    search_candidate_packet: Mapping[str, Any],
    search_result_candidate_packet: Mapping[str, Any],
    fetch_packet: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if search_candidate_packet.get("packet_digest") != search_result_candidate_packet.get(
        "packet_digest"
    ):
        raise LiveAcquisitionReadabilityStatusError(
            "search candidate packet digest does not match search result packet"
        )
    if fetch_packet.get("search_result_candidate_packet_digest") != (
        search_result_candidate_packet.get("packet_digest")
    ):
        raise LiveAcquisitionReadabilityStatusError(
            "fetch/read packet does not point at retained search candidate packet"
        )
    references = _safe_list(fetch_packet.get("reference_records"))
    if len(references) != 1:
        raise LiveAcquisitionReadabilityStatusError(
            "fetch/read packet must contain one retained sanitized reference"
        )
    reference = _safe_mapping(references[0])
    if reference.get("fetch_read_status") != "readable":
        raise LiveAcquisitionReadabilityStatusError(
            "retained fetch/read reference is not readable"
        )
    if reference.get("bounded_text_sanitized") is not True:
        raise LiveAcquisitionReadabilityStatusError(
            "retained fetch/read reference is not marked sanitized"
        )
    if reference.get("bounded_text_bounded") is not True:
        raise LiveAcquisitionReadabilityStatusError(
            "retained fetch/read reference is not marked bounded"
        )
    candidates = {
        str(record.get("candidate_id")): _safe_mapping(record)
        for record in _safe_list(search_result_candidate_packet.get("candidate_records"))
        if isinstance(record, Mapping)
    }
    selected_candidate = candidates.get(str(reference.get("candidate_id")))
    if not selected_candidate:
        raise LiveAcquisitionReadabilityStatusError(
            "fetch/read selected candidate is absent from search candidate packet"
        )
    expected = {
        "candidate_digest": "candidate_digest",
        "url": "candidate_url",
        "domain": "candidate_domain",
        "result_rank": "result_rank",
    }
    for candidate_key, reference_key in expected.items():
        if selected_candidate.get(candidate_key) != reference.get(reference_key):
            raise LiveAcquisitionReadabilityStatusError(
                f"fetch/read reference {reference_key} does not match candidate"
            )
    return selected_candidate, reference


def _verify_fetch_read_summary(summary: Any) -> str | None:
    safe = _safe_mapping(summary)
    if not safe:
        return BLOCKED_FETCH_READ_ARTIFACT_LINEAGE
    retention_flags = _safe_mapping(safe.get("retention_flags"))
    if any(value is not False for value in retention_flags.values()):
        return BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE
    if any(_truthy_key_claim(safe, key) for key in _RAW_PRIVATE_RETENTION_KEYS):
        return BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE
    closed = _safe_mapping(safe.get("closed_downstream_surfaces"))
    if any(value is not False for value in closed.values()):
        return BLOCKED_CLOSED_SURFACE_VIOLATION
    if any(_truthy_key_claim(safe, key) for key in _CLOSED_FALSE_KEYS):
        return BLOCKED_CLOSED_SURFACE_VIOLATION
    if safe.get("decision") != PASS_DECISION:
        return BLOCKED_FETCH_READ_ARTIFACT_LINEAGE
    if safe.get("readable_content_handoff_created") is not True:
        return BLOCKED_FETCH_READ_ARTIFACT_LINEAGE
    return None


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require_under_repo_output(path: Path, root: Path) -> None:
    output_root = (root / "output").resolve()
    resolved = path.resolve()
    if not _path_under(resolved, output_root):
        raise LiveAcquisitionReadabilityStatusError(
            "fetch/read artifact path is outside repo-local output/"
        )


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


def _looks_raw_private_error(message: str) -> bool:
    lowered = message.casefold()
    return "raw/private" in lowered or "raw/private fields" in lowered


def _truthy_key_claim(value: Any, target_key: str) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized == target_key and item is not False:
                return True
            if _truthy_key_claim(item, target_key):
                return True
    elif isinstance(value, list | tuple | set | frozenset):
        return any(_truthy_key_claim(item, target_key) for item in value)
    return False


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _clean_query(query: str) -> str:
    return " ".join(str(query or "").strip().split())


def _bool_text(value: Any) -> str:
    return "true" if value is True else "false"


__all__ = [
    "LIVE_ACQUISITION_READABILITY_STATUS_FLAG",
    "LiveAcquisitionReadabilityStatusError",
    "LiveAcquisitionReadabilityStatusResult",
    "build_live_acquisition_readability_status",
    "format_live_acquisition_readability_status",
    "output_hygiene_passes",
]
