"""D-prime single-lane answer-path bridge.

This runtime consumes the completed D-prime evidence-support bundle and then
consumes SufficiencyReadiness, hardened FinalAnswerPacket, and Author/answer
surfaces only through product/RunKernel authority. It is consumed by ordinary
product status in the same phase. It does not run live/model/provider/search/
fetch/read/retrieval calls, does not claim product correctness, and does not
generalize D-prime analyst intake beyond the current single D-prime lane.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from core.author_prose_finalization_runtime import (
    AuthorProseFinalizationRuntimeError,
    reduce_author_prose_finalization,
)
from core.final_answer_packet_hardening_runtime import (
    FinalAnswerPacketHardeningRuntimeError,
    reduce_hardened_final_answer_packet,
)
from core.run_kernel import (
    DPRIME_CITATION_SOURCE_DISPLAY_STAGE,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.sufficiency_readiness_runtime import (
    SufficiencyReadinessRuntimeError,
    reduce_sufficiency_readiness,
)

DPRIME_SINGLE_LANE_ANSWER_PATH_SCHEMA_VERSION = (
    "dprime_single_lane_answer_path_runtime_v1"
)
DPRIME_SINGLE_LANE_ANSWER_PATH_SURFACE = (
    "core.dprime_single_lane_answer_path_runtime"
)
DPRIME_SINGLE_LANE_ANSWER_PATH_OWNER = "RunKernel.DPrimeSingleLaneAnswerPath"
DPRIME_CITATION_SOURCE_DISPLAY_OWNER = "RunKernel.DPrimeCitationSourceDisplay"

BLOCKED_DPRIME_ANSWER_PATH_SUPPORT_BUNDLE_INCOMPLETE = (
    "BLOCKED_DPRIME_ANSWER_PATH_SUPPORT_BUNDLE_INCOMPLETE"
)
BLOCKED_DPRIME_SUFFICIENCY_READINESS_AUTHORITY_MISSING = (
    "BLOCKED_DPRIME_SUFFICIENCY_READINESS_AUTHORITY_MISSING"
)
BLOCKED_DPRIME_FAP_AUTHORITY_MISSING = "BLOCKED_DPRIME_FAP_AUTHORITY_MISSING"
BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING = (
    "BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING"
)
BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING = (
    "BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING"
)

PASS_DECISION = "PASS"
_ANSWER_STATUSES = {
    "full_answer_prose_created",
    "partial_answer_prose_created",
}
_FALSE_FLAGS = (
    "product_correctness_claimed",
    "author_answer_is_product_correctness",
    "model_called",
    "provider_called",
    "live_provider_called",
    "search_executed",
    "fetch_read_executed",
    "retrieval_executed",
    "raw_prompt_retained",
    "raw_model_response_retained",
    "raw_provider_payload_retained",
    "raw_source_text_retained",
    "bounded_source_text_retained",
    "db_rows_retained",
    "cache_rows_retained",
    "private_logs_retained",
)
_RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "bounded_text",
        "cache_row",
        "cookie",
        "db_row",
        "env",
        "full_prompt",
        "full_text",
        "full_trace",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_page_text",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "raw_source_text",
        "secret",
        "secrets",
        "source_text",
        "token",
        "unbounded_text",
    }
)


class DPrimeSingleLaneAnswerPathError(ValueError):
    """Raised when the D-prime answer path stops at a named surface."""

    def __init__(self, blocker: str, detail: str, next_surface: str) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail
        self.next_surface = next_surface


@dataclass(frozen=True, slots=True)
class DPrimeSingleLaneAnswerPathResult:
    """Product-visible outcome for the single D-prime answer lane."""

    readiness_projection: Mapping[str, Any]
    final_answer_packet_projection: Mapping[str, Any]
    author_answer_projection: Mapping[str, Any]
    citation_source_display_projection: Mapping[str, Any]
    decision: str = PASS_DECISION

    def to_status_overlay(self) -> dict[str, Any]:
        readiness = _safe_mapping(self.readiness_projection)
        fap = _safe_mapping(self.final_answer_packet_projection)
        author = _safe_mapping(self.author_answer_projection)
        display = _safe_mapping(self.citation_source_display_projection)
        return {
            "dprime_single_lane_answer_path_status": "consumed",
            "single_lane_only": True,
            "support_bundle_consumed_by_answer_path": True,
            "sufficiency_readiness_status": readiness.get("final_readiness_status"),
            "sufficiency_readiness_ref": {
                "readiness_id": readiness.get("readiness_id"),
                "readiness_digest": readiness.get("readiness_digest"),
                "final_readiness_status": readiness.get("final_readiness_status"),
            },
            "final_answer_packet_status": fap.get("fap_status"),
            "final_answer_packet_ref": _fap_ref(fap),
            "author_answer_status": author.get("author_prose_status"),
            "author_answer_ref": _author_ref(author),
            "answer_text": author.get("answer_text"),
            "citation_source_display_status": display.get("status"),
            "citation_source_display_ref": _display_ref(display),
            "citation_source_display": display,
            "citation_source_display_created": True,
            "citation_source_display_count": len(
                display.get("citation_source_entries") or []
            ),
            "source_obligation_authority_consumed": True,
            "citation_source_handoff_authority_consumed": True,
            "fap_consumed_dprime_source_refs": True,
            "author_answer_consumed_fap": True,
            "product_correctness_claimed": False,
            "model_called": False,
            "provider_called": False,
            "live_provider_called": False,
            "search_executed": False,
            "fetch_read_executed": False,
            "retrieval_executed": False,
            "decision": self.decision,
        }


def build_dprime_single_lane_answer_path(
    *,
    support_bundle: Any,
    run_kernel: RunKernel,
    mode: str = "Balanced",
    author_policy: Mapping[str, Any] | None = None,
) -> DPrimeSingleLaneAnswerPathResult:
    """Consume D-prime support through readiness, FAP, Author, and source display."""

    _require_completed_support_bundle(
        support_bundle=support_bundle,
        run_kernel=run_kernel,
    )
    try:
        readiness_result = reduce_sufficiency_readiness(
            run_kernel=run_kernel,
            mode=mode,
        )
    except (SufficiencyReadinessRuntimeError, RunKernelTransitionError) as exc:
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_SUFFICIENCY_READINESS_AUTHORITY_MISSING,
            str(exc),
            "SufficiencyReadiness",
        ) from exc

    readiness_projection = dict(readiness_result.readiness_projection)
    if not readiness_projection.get("final_readiness_status"):
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_SUFFICIENCY_READINESS_AUTHORITY_MISSING,
            "SufficiencyReadiness did not produce a final readiness status",
            "SufficiencyReadiness",
        )

    try:
        fap_result = reduce_hardened_final_answer_packet(run_kernel=run_kernel)
    except (FinalAnswerPacketHardeningRuntimeError, RunKernelTransitionError) as exc:
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_FAP_AUTHORITY_MISSING,
            str(exc),
            "FinalAnswerPacket",
        ) from exc
    fap_projection = dict(fap_result.final_answer_authority_projection)
    _require_fap_consumed_dprime_source_refs(
        fap_projection=fap_projection,
        handoff_projection=run_kernel.state.dprime_citation_source_handoff_projection,
    )

    try:
        author_result = reduce_author_prose_finalization(
            run_kernel=run_kernel,
            policy=author_policy,
        )
    except (AuthorProseFinalizationRuntimeError, RunKernelTransitionError) as exc:
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING,
            str(exc),
            "Author/answer output",
        ) from exc
    author_projection = dict(author_result.author_prose_projection)
    _require_author_answer(
        author_projection=author_projection,
        fap_projection=fap_projection,
    )

    display_state = _build_citation_source_display_state(
        run_kernel=run_kernel,
        fap_projection=fap_projection,
        author_projection=author_projection,
    )
    try:
        action = run_kernel.authorize_dprime_citation_source_display(
            display_id=str(display_state["display_id"]),
            display_digest=str(display_state["display_digest"]),
            citation_source_handoff_id=str(
                display_state["citation_source_handoff_id"]
            ),
            citation_source_handoff_digest=str(
                display_state["citation_source_handoff_digest"]
            ),
            author_prose_id=str(display_state["author_prose_id"]),
            author_prose_digest=str(display_state["author_prose_digest"]),
            final_answer_packet_digest=str(
                display_state["final_answer_packet_digest"]
            ),
            inputs={
                "runtime_surface": DPRIME_SINGLE_LANE_ANSWER_PATH_SURFACE,
                "single_lane_only": True,
            },
        )
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.DPRIME_CITATION_SOURCE_DISPLAY_CREATED,
                status=RunStageStatus.COMPLETED,
                payload={"dprime_citation_source_display": display_state},
            )
        )
    except RunKernelTransitionError as exc:
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING,
            str(exc),
            "citation/source display",
        ) from exc

    return DPrimeSingleLaneAnswerPathResult(
        readiness_projection=dict(run_kernel.state.sufficiency_readiness_projection),
        final_answer_packet_projection=dict(
            run_kernel.state.final_answer_authority_projection
        ),
        author_answer_projection=dict(run_kernel.state.author_prose_projection),
        citation_source_display_projection=dict(
            run_kernel.state.projections.get(DPRIME_CITATION_SOURCE_DISPLAY_STAGE, {})
        ),
    )


def _require_completed_support_bundle(
    *,
    support_bundle: Any,
    run_kernel: RunKernel,
) -> None:
    coverage = _safe_mapping(getattr(support_bundle, "component_coverage_projection", {}))
    source = _safe_mapping(getattr(support_bundle, "source_obligation_authority_ref", {}))
    handoff = _safe_mapping(getattr(support_bundle, "citation_eligibility_authority_ref", {}))
    if not coverage or coverage.get("coverage_state") != "supported_with_caveats":
        _blocked_support("completed D-prime ComponentCoverage is unavailable")
    if source.get("authority_consumed") is not True:
        _blocked_support("D-prime source-obligation authority was not consumed")
    if handoff.get("citation_source_handoff_consumed") is not True:
        _blocked_support("D-prime citation-source handoff authority was not consumed")
    kernel_coverage = _safe_mapping(run_kernel.state.component_coverage_projection)
    if coverage.get("coverage_record_digest") != kernel_coverage.get(
        "coverage_record_digest"
    ):
        _blocked_support("support-bundle coverage does not match RunKernel coverage")
    kernel_source = _safe_mapping(
        run_kernel.state.dprime_source_obligation_authority_projection
    )
    if source.get("source_obligation_authority_digest") != kernel_source.get(
        "source_obligation_authority_digest"
    ):
        _blocked_support("support-bundle source authority does not match RunKernel")
    kernel_handoff = _safe_mapping(run_kernel.state.dprime_citation_source_handoff_projection)
    if handoff.get("citation_source_handoff_digest") != kernel_handoff.get(
        "citation_source_handoff_digest"
    ):
        _blocked_support("support-bundle citation handoff does not match RunKernel")


def _blocked_support(detail: str) -> None:
    raise DPrimeSingleLaneAnswerPathError(
        BLOCKED_DPRIME_ANSWER_PATH_SUPPORT_BUNDLE_INCOMPLETE,
        detail,
        "D-prime evidence-support bundle",
    )


def _require_fap_consumed_dprime_source_refs(
    *,
    fap_projection: Mapping[str, Any],
    handoff_projection: Mapping[str, Any],
) -> None:
    fap = _safe_mapping(fap_projection)
    handoff = _safe_mapping(handoff_projection)
    if fap.get("packet_created") is not True:
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_FAP_AUTHORITY_MISSING,
            "FinalAnswerPacket did not create a packet for the D-prime lane",
            "FinalAnswerPacket",
        )
    source_refs = [_safe_mapping(item) for item in fap.get("source_support_refs") or []]
    content_ids = {
        item.get("content_ref_id")
        for item in source_refs
        if _clean_text(item.get("content_ref_id"))
    }
    evidence_ids = {
        item.get("evidence_ref_id")
        for item in source_refs
        if _clean_text(item.get("evidence_ref_id"))
    }
    handoff_records = [
        _safe_mapping(item) for item in handoff.get("citation_source_records") or []
    ]
    for record in handoff_records:
        if (
            record.get("content_ref_id") not in content_ids
            and record.get("evidence_id") not in evidence_ids
        ):
            raise DPrimeSingleLaneAnswerPathError(
                BLOCKED_DPRIME_FAP_AUTHORITY_MISSING,
                "FinalAnswerPacket source refs do not match D-prime citation-source handoff",
                "FinalAnswerPacket",
            )


def _require_author_answer(
    *,
    author_projection: Mapping[str, Any],
    fap_projection: Mapping[str, Any],
) -> None:
    author = _safe_mapping(author_projection)
    fap = _safe_mapping(fap_projection)
    if author.get("fap_status") != fap.get("fap_status"):
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING,
            "Author/answer output does not bind the current FinalAnswerPacket status",
            "Author/answer output",
        )
    if author.get("author_prose_status") not in _ANSWER_STATUSES:
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING,
            "Author/answer output produced a non-answer posture",
            "Author/answer output",
        )
    if not _clean_text(author.get("answer_text"), limit=4_000):
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING,
            "Author/answer output did not create answer text",
            "Author/answer output",
        )
    _reject_raw_or_private(author, context="author answer projection")


def _build_citation_source_display_state(
    *,
    run_kernel: RunKernel,
    fap_projection: Mapping[str, Any],
    author_projection: Mapping[str, Any],
) -> dict[str, Any]:
    handoff = _safe_mapping(run_kernel.state.dprime_citation_source_handoff_projection)
    source_authority = _safe_mapping(
        run_kernel.state.dprime_source_obligation_authority_projection
    )
    fap = _safe_mapping(fap_projection)
    author = _safe_mapping(author_projection)
    records = [_safe_mapping(item) for item in handoff.get("citation_source_records") or []]
    entries = [
        _source_display_entry(record, index)
        for index, record in enumerate(records, start=1)
    ]
    if not entries:
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING,
            "D-prime citation-source handoff has no source records to display",
            "citation/source display",
        )
    packet_digest = _required_token(
        fap.get("packet_digest") or fap.get("no_packet_digest"),
        "FinalAnswerPacket digest is missing",
    )
    author_id = _required_token(author.get("author_prose_id"), "author answer id is missing")
    author_digest = _required_token(
        author.get("author_prose_digest"),
        "author answer digest is missing",
    )
    handoff_id = _required_token(
        handoff.get("citation_source_handoff_id"),
        "citation-source handoff id is missing",
    )
    handoff_digest = _required_token(
        handoff.get("citation_source_handoff_digest"),
        "citation-source handoff digest is missing",
    )
    display_id = f"dprime-source-display:{handoff_digest[:16]}:{author_digest[:16]}"
    answer_text_digest = _digest_json(
        {"answer_text": _clean_text(author.get("answer_text"), limit=4_000)}
    )
    state = {
        "schema_version": DPRIME_SINGLE_LANE_ANSWER_PATH_SCHEMA_VERSION,
        "owner": DPRIME_CITATION_SOURCE_DISPLAY_OWNER,
        "runtime_surface": DPRIME_SINGLE_LANE_ANSWER_PATH_SURFACE,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "display_id": display_id,
        "status": "created",
        "citation_source_display_created": True,
        "citations_rendered": True,
        "citation_rendering_surface": "dprime_source_display",
        "single_lane_only": True,
        "citation_source_handoff_id": handoff_id,
        "citation_source_handoff_digest": handoff_digest,
        "source_obligation_authority_id": source_authority.get(
            "source_obligation_authority_id"
        ),
        "source_obligation_authority_digest": source_authority.get(
            "source_obligation_authority_digest"
        ),
        "source_obligation_authority_consumed": True,
        "citation_source_handoff_consumed": True,
        "final_answer_packet_consumed": True,
        "final_answer_packet_status": fap.get("fap_status"),
        "final_answer_packet_digest": packet_digest,
        "author_answer_consumed": True,
        "author_prose_id": author_id,
        "author_prose_digest": author_digest,
        "author_answer_status": author.get("author_prose_status"),
        "answer_text_digest": answer_text_digest,
        "citation_source_entries": entries,
        "rendered_source_count": len(entries),
        "rendering_note": (
            "Source display is derived from consumed D-prime citation-source "
            "handoff authority; it is not a product-correctness claim."
        ),
        "product_correctness_claimed": False,
        "author_answer_is_product_correctness": False,
        "model_called": False,
        "provider_called": False,
        "live_provider_called": False,
        "search_executed": False,
        "fetch_read_executed": False,
        "retrieval_executed": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "raw_source_text_retained": False,
        "bounded_source_text_retained": False,
        "db_rows_retained": False,
        "cache_rows_retained": False,
        "private_logs_retained": False,
    }
    _reject_raw_or_private(state, context="D-prime source display")
    for flag in _FALSE_FLAGS:
        if state.get(flag) is not False:
            raise DPrimeSingleLaneAnswerPathError(
                BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING,
                f"D-prime source display must keep {flag}=False",
                "citation/source display",
            )
    state["display_digest"] = _digest_json(_display_digest_payload(state))
    return state


def _source_display_entry(record: Mapping[str, Any], index: int) -> dict[str, Any]:
    mapped = _safe_mapping(record)
    label = f"D{index}"
    title = _clean_text(mapped.get("title"), limit=180)
    domain = _clean_text(mapped.get("domain"), limit=160)
    url = _clean_text(mapped.get("url"), limit=500)
    source_id = _required_token(mapped.get("source_id"), "source display lacks source id")
    display_name = title or domain or source_id
    if url:
        display_text = f"[{label}] {display_name} - {url}"
    elif domain:
        display_text = f"[{label}] {display_name} - {domain}"
    else:
        display_text = f"[{label}] {display_name}"
    return _without_empty(
        {
            "label": label,
            "display_text": display_text,
            "source_id": source_id,
            "source_obligation_id": mapped.get("source_obligation_id"),
            "evidence_id": mapped.get("evidence_id"),
            "content_ref_id": mapped.get("content_ref_id"),
            "title": title,
            "domain": domain,
            "url": url,
            "source_digest": mapped.get("source_digest"),
            "derived_from_citation_source_handoff": True,
            "citation_rendered": True,
            "product_correctness_claimed": False,
        }
    )


def _fap_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    mapped = _safe_mapping(value)
    return _without_empty(
        {
            "packet_id": mapped.get("packet_id"),
            "packet_digest": mapped.get("packet_digest")
            or mapped.get("no_packet_digest"),
            "fap_status": mapped.get("fap_status"),
            "packet_created": mapped.get("packet_created"),
        }
    )


def _author_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    mapped = _safe_mapping(value)
    return _without_empty(
        {
            "author_prose_id": mapped.get("author_prose_id"),
            "author_prose_digest": mapped.get("author_prose_digest"),
            "author_prose_status": mapped.get("author_prose_status"),
            "fap_status": mapped.get("fap_status"),
        }
    )


def _display_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    mapped = _safe_mapping(value)
    return _without_empty(
        {
            "display_id": mapped.get("display_id"),
            "display_digest": mapped.get("display_digest"),
            "status": mapped.get("status"),
            "rendered_source_count": mapped.get("rendered_source_count"),
        }
    )


def _display_digest_payload(state: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in state.items() if key != "display_digest"}


def _reject_raw_or_private(value: Any, *, context: str) -> None:
    if _contains_raw_or_private_key(value):
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING,
            f"{context} contains raw/private material",
            "citation/source display",
        )


def _contains_raw_or_private_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _RAW_OR_PRIVATE_KEYS:
                if normalized.startswith("raw_") and item is False:
                    continue
                return True
            if _contains_raw_or_private_key(item):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return any(_contains_raw_or_private_key(item) for item in value)
    return False


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {}, ())
    }


def _required_token(value: Any, message: str, *, limit: int = 260) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        raise DPrimeSingleLaneAnswerPathError(
            BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING,
            message,
            "citation/source display",
        )
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


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
    "BLOCKED_DPRIME_ANSWER_PATH_SUPPORT_BUNDLE_INCOMPLETE",
    "BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING",
    "BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING",
    "BLOCKED_DPRIME_FAP_AUTHORITY_MISSING",
    "BLOCKED_DPRIME_SUFFICIENCY_READINESS_AUTHORITY_MISSING",
    "DPRIME_CITATION_SOURCE_DISPLAY_OWNER",
    "DPRIME_SINGLE_LANE_ANSWER_PATH_OWNER",
    "DPRIME_SINGLE_LANE_ANSWER_PATH_SCHEMA_VERSION",
    "DPRIME_SINGLE_LANE_ANSWER_PATH_SURFACE",
    "DPrimeSingleLaneAnswerPathError",
    "DPrimeSingleLaneAnswerPathResult",
    "build_dprime_single_lane_answer_path",
]
