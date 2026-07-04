"""Product-owned retained live artifact preflight support.

The preflight is a read-only metadata gate for retained sanitized live-search
artifacts. It performs no live provider, broker, fetch/read, retrieval, model,
evidence, citation, Sufficiency, FAP, Author, or answer-prose work.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from core.search_result_candidate_packet import (
    SearchResultCandidatePacketError,
    validate_search_result_candidate_packet,
)

DEFAULT_PROVIDER = "serper"
EXTRACTION_PROVIDER = "tavily"
ALLOWED_PROVIDERS = frozenset({DEFAULT_PROVIDER, EXTRACTION_PROVIDER})
DEFAULT_OPERATION = "search"
MAX_RESULTS = 5
CURRENT_RUN_CANDIDATE_PACKET_NAME = "search_candidate_packet.json"
CANDIDATE_PACKET_NAME = "search_result_candidate_packet.json"

RETAINED_ARTIFACT_REPAIR_PHASE = "AG-LIVE-LOCAL-ARTIFACT-RETENTION-REPAIR-01"
RETAINED_ARTIFACT_OUTPUT_DIR_NAME = "ag_live_ordinary_search_candidate_01b"
RETAINED_ARTIFACT_REQUIRED_NAMES = (
    "sanitized_provider_results.json",
    CURRENT_RUN_CANDIDATE_PACKET_NAME,
    CANDIDATE_PACKET_NAME,
)
RETAINED_ARTIFACT_PREFLIGHT_PASS = "PASS"
RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_MISSING = "BLOCKED_LOCAL_ARTIFACT_MISSING"
RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_UNREADABLE = (
    "BLOCKED_LOCAL_ARTIFACT_UNREADABLE"
)
RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH = (
    "BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH"
)
RETAINED_ARTIFACT_BLOCKED_OUTPUT_BOUNDARY = "BLOCKED_OUTPUT_BOUNDARY"
RETAINED_ARTIFACT_BLOCKED_RAW_OR_PRIVATE_FIELD = "BLOCKED_RAW_OR_PRIVATE_FIELD"
RETAINED_ARTIFACT_BLOCKED_RETENTION_FLAG = "BLOCKED_RETENTION_FLAG"
RETAINED_ARTIFACT_BLOCKED_CANDIDATE_LINEAGE = "BLOCKED_CANDIDATE_LINEAGE"
RETAINED_ARTIFACT_PREFLIGHT_DECISIONS = frozenset(
    {
        RETAINED_ARTIFACT_PREFLIGHT_PASS,
        RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_MISSING,
        RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_UNREADABLE,
        RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH,
        RETAINED_ARTIFACT_BLOCKED_OUTPUT_BOUNDARY,
        RETAINED_ARTIFACT_BLOCKED_RAW_OR_PRIVATE_FIELD,
        RETAINED_ARTIFACT_BLOCKED_RETENTION_FLAG,
        RETAINED_ARTIFACT_BLOCKED_CANDIDATE_LINEAGE,
    }
)
ACTIVE_CHECKOUT_PATH_HINT = r"C:\Users\aidan\ScryRaven"
LOWERCASE_CHECKOUT_PATH_HINT = r"C:\Users\aidan\scryraven"

ALLOWED_PROVIDER_RESULT_KEYS = frozenset(
    {
        "title",
        "url",
        "link",
        "domain",
        "snippet",
        "date",
        "published_or_observed_date",
        "rank",
        "result_rank",
        "call_index",
        "provider_call_index",
        "provider_extracted_text_char_count",
        "provider_extracted_text_digest",
        "provider_extracted_content_type",
        "provider_extracted_at",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)
ALLOWED_PROVIDER_ENVELOPE_KEYS = frozenset(
    {
        "request_kind",
        "provider",
        "operation",
        "result_count",
        "results",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)
RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "auth_header",
        "auth_headers",
        "authorization",
        "authorization_header",
        "cache",
        "cache_row",
        "cookie",
        "db",
        "db_cache_row",
        "db_cache_rows",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
        "header",
        "headers",
        "html",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "page_content",
        "password",
        "private_log",
        "private_logs",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_html",
        "raw_model_response",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "serper_api_key",
        "serper_payload",
        "token",
        "unbounded_text",
    }
)
FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "admitted_source",
        "admitted_sources",
        "answer",
        "author",
        "author_input",
        "author_material",
        "citation",
        "citation_record",
        "citation_records",
        "citation_source",
        "citation_sources",
        "citations",
        "content",
        "content_fetched_from_url",
        "evidence",
        "evidence_ledger",
        "evidence_ledger_admission",
        "evidence_record",
        "evidence_records",
        "evidence_sources",
        "fap",
        "fap_material",
        "fetched_content",
        "final_answer",
        "final_answer_packet",
        "read_content",
        "retrieved_content",
        "semantic_observation",
        "source_obligation_claim",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)
PRIVATE_VALUE_MARKERS = frozenset(
    {
        "api_key",
        "authorization:",
        "bearer ",
        "private_sentinel",
        "provider_payload",
        "raw_private",
        "raw_prompt",
        "raw_provider",
        "secret",
    }
)


class RetainedLiveArtifactPreflightError(ValueError):
    """Raised when retained live artifact preflight must fail closed."""


def preflight_retained_live_artifacts(
    *,
    artifact_dir: str | Path | None = None,
    repo_root: str | Path | None = None,
    alternate_repo_roots: Sequence[str | Path] | None = None,
) -> dict[str, Any]:
    """Preflight retained sanitized live-search artifacts without printing contents.

    The check is intentionally repo-local and read-only. It may parse the three
    known sanitized JSON artifacts to report metadata, retention flags, and
    lineage status, but it never reads alternate-checkout artifact contents.
    """

    root = _resolve_path(repo_root or Path(__file__).resolve().parents[1])
    output_root = _resolve_path(root / "output")
    target = _resolve_relative_to_root(
        artifact_dir or Path("output") / RETAINED_ARTIFACT_OUTPUT_DIR_NAME,
        root,
    )
    alternate_reports = _alternate_artifact_reports(
        alternate_repo_roots or (),
        active_repo_root=root,
    )
    if not _path_under(target, output_root):
        matching_alternate = _matching_alternate_boundary_report(
            target,
            alternate_repo_roots or (),
            active_repo_root=root,
        )
        return _retained_preflight_result(
            RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH
            if matching_alternate
            else RETAINED_ARTIFACT_BLOCKED_OUTPUT_BOUNDARY,
            repo_root=root,
            artifact_dir=target,
            output_root=output_root,
            artifact_metadata=_required_artifact_metadata(target, root),
            alternate_artifact_locations=(
                [matching_alternate] if matching_alternate else alternate_reports
            ),
        )

    artifact_metadata = _required_artifact_metadata(target, root)
    missing = [
        name
        for name, metadata in artifact_metadata.items()
        if not metadata["exists"] or metadata["kind"] != "file"
    ]
    if missing:
        alternate_with_artifacts = [
            report
            for report in alternate_reports
            if report.get("all_required_artifacts_exist") is True
        ]
        return _retained_preflight_result(
            RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH
            if alternate_with_artifacts
            else RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_MISSING,
            repo_root=root,
            artifact_dir=target,
            output_root=output_root,
            artifact_metadata=artifact_metadata,
            alternate_artifact_locations=alternate_reports,
            missing_artifacts=missing,
        )

    unreadable = [
        name
        for name, metadata in artifact_metadata.items()
        if metadata.get("read_permission") is not True
    ]
    if unreadable:
        return _retained_preflight_result(
            RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_UNREADABLE,
            repo_root=root,
            artifact_dir=target,
            output_root=output_root,
            artifact_metadata=artifact_metadata,
            alternate_artifact_locations=alternate_reports,
            unreadable_artifacts=unreadable,
        )

    decoded: dict[str, Any] = {}
    for name in RETAINED_ARTIFACT_REQUIRED_NAMES:
        path = target / name
        decoded_value, parse_metadata = _read_json_metadata(path)
        artifact_metadata[name].update(parse_metadata)
        if parse_metadata["json_parse_success"] is not True:
            return _retained_preflight_result(
                RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_UNREADABLE,
                repo_root=root,
                artifact_dir=target,
                output_root=output_root,
                artifact_metadata=artifact_metadata,
                alternate_artifact_locations=alternate_reports,
                unreadable_artifacts=[name],
            )
        decoded[name] = decoded_value

    decoded_raw_retention_flags = _decoded_raw_retention_flags(decoded)
    try:
        sanitized_results, provider_envelope = _decode_sanitized_provider_results(
            decoded["sanitized_provider_results.json"]
        )
    except RetainedLiveArtifactPreflightError as exc:
        return _retained_preflight_result(
            _preflight_decision_from_error(exc),
            repo_root=root,
            artifact_dir=target,
            output_root=output_root,
            artifact_metadata=artifact_metadata,
            alternate_artifact_locations=alternate_reports,
            raw_retention_flags=decoded_raw_retention_flags,
        )

    try:
        search_candidate_packet = validate_search_result_candidate_packet(
            decoded[CURRENT_RUN_CANDIDATE_PACKET_NAME]
        )
        search_result_candidate_packet = validate_search_result_candidate_packet(
            decoded[CANDIDATE_PACKET_NAME]
        )
    except SearchResultCandidatePacketError as exc:
        return _retained_preflight_result(
            _preflight_decision_from_error(exc),
            repo_root=root,
            artifact_dir=target,
            output_root=output_root,
            artifact_metadata=artifact_metadata,
            alternate_artifact_locations=alternate_reports,
            raw_retention_flags=decoded_raw_retention_flags,
        )

    lineage_status = _retained_candidate_lineage_status(
        sanitized_results=sanitized_results,
        search_candidate_packet=search_candidate_packet,
        search_result_candidate_packet=search_result_candidate_packet,
    )
    if not all(lineage_status.values()):
        return _retained_preflight_result(
            RETAINED_ARTIFACT_BLOCKED_CANDIDATE_LINEAGE,
            repo_root=root,
            artifact_dir=target,
            output_root=output_root,
            artifact_metadata=artifact_metadata,
            alternate_artifact_locations=alternate_reports,
            provider_result_count=len(sanitized_results),
            candidate_count=_bounded_int(
                search_result_candidate_packet.get("candidate_count")
            ),
            raw_retention_flags=_retained_raw_flags(
                provider_envelope,
                search_result_candidate_packet,
            ),
            candidate_lineage_status=lineage_status,
        )

    return _retained_preflight_result(
        RETAINED_ARTIFACT_PREFLIGHT_PASS,
        repo_root=root,
        artifact_dir=target,
        output_root=output_root,
        artifact_metadata=artifact_metadata,
        alternate_artifact_locations=alternate_reports,
        provider_result_count=len(sanitized_results),
        candidate_count=_bounded_int(search_result_candidate_packet.get("candidate_count")),
        raw_retention_flags=_retained_raw_flags(
            provider_envelope,
            search_result_candidate_packet,
        ),
        candidate_lineage_status=lineage_status,
    )


def _decode_sanitized_provider_results(
    decoded: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    envelope: dict[str, Any]
    raw_results: Any
    if isinstance(decoded, list):
        envelope = {
            "provider": DEFAULT_PROVIDER,
            "operation": DEFAULT_OPERATION,
            "result_count": len(decoded),
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        }
        raw_results = decoded
    elif isinstance(decoded, Mapping):
        envelope = _validate_provider_results_envelope(decoded)
        raw_results = decoded.get("results")
    else:
        raise RetainedLiveArtifactPreflightError(
            "sanitized provider results must be a list or generic sanitized object"
        )

    if not isinstance(raw_results, list):
        raise RetainedLiveArtifactPreflightError(
            "sanitized provider results require a results list"
        )
    if len(raw_results) > MAX_RESULTS:
        raise RetainedLiveArtifactPreflightError(
            f"sanitized provider results exceed max results cap {MAX_RESULTS}"
        )
    if int(envelope.get("result_count", len(raw_results))) != len(raw_results):
        raise RetainedLiveArtifactPreflightError(
            "sanitized provider result_count does not match results length"
        )

    normalized = [
        _normalize_provider_result(record, default_rank=index)
        for index, record in enumerate(raw_results, start=1)
    ]
    return normalized, envelope


def _normalize_provider_result(
    result: Mapping[str, Any],
    *,
    default_rank: int,
) -> dict[str, Any]:
    raw = _safe_mapping(result)
    _reject_forbidden_material(raw, context="provider result")
    unknown = sorted(set(raw) - ALLOWED_PROVIDER_RESULT_KEYS)
    if unknown:
        raise RetainedLiveArtifactPreflightError(
            "provider result contains unsupported fields: " + ", ".join(unknown)
        )
    _validate_false_retention(raw, context="provider result")
    title = _required_token(raw.get("title"), "provider result requires title", 220)
    url = _required_url(raw.get("url") or raw.get("link"))
    domain = _clean_domain(raw.get("domain")) or _domain_from_url(url)
    if not domain:
        raise RetainedLiveArtifactPreflightError(
            "provider result requires domain or http(s) URL"
        )
    return _without_empty(
        {
            "title": title,
            "url": url,
            "domain": domain,
            "snippet": _clean_token(raw.get("snippet"), limit=500),
            "published_or_observed_date": _clean_token(
                raw.get("published_or_observed_date") or raw.get("date"),
                limit=80,
            ),
            "result_rank": _positive_int(
                raw.get("result_rank") or raw.get("rank") or default_rank,
                "provider result rank must be positive",
            ),
            "provider_call_index": _positive_int(
                raw.get("provider_call_index") or raw.get("call_index") or 1,
                "provider result call index must be positive",
            ),
        }
    )


def _validate_provider_results_envelope(decoded: Mapping[str, Any]) -> dict[str, Any]:
    raw = _safe_mapping(decoded)
    _reject_forbidden_material(raw, context="provider results envelope")
    unknown = sorted(set(raw) - ALLOWED_PROVIDER_ENVELOPE_KEYS)
    if unknown:
        raise RetainedLiveArtifactPreflightError(
            "provider results envelope contains unsupported fields: "
            + ", ".join(unknown)
        )
    _validate_false_retention(raw, context="provider results envelope")
    provider = _required_token(
        raw.get("provider") or DEFAULT_PROVIDER,
        "provider results envelope requires provider",
        80,
    )
    operation = _required_token(
        raw.get("operation") or DEFAULT_OPERATION,
        "provider results envelope requires operation",
        80,
    )
    if provider not in ALLOWED_PROVIDERS:
        raise RetainedLiveArtifactPreflightError(
            "provider results provider mismatch"
        )
    if operation != DEFAULT_OPERATION:
        raise RetainedLiveArtifactPreflightError(
            "provider results operation mismatch"
        )
    result_count = _bounded_int(raw.get("result_count"), default=0)
    return {
        "request_kind": raw.get("request_kind"),
        "provider": provider,
        "operation": operation,
        "result_count": result_count,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _retained_preflight_result(
    decision: str,
    *,
    repo_root: Path,
    artifact_dir: Path,
    output_root: Path,
    artifact_metadata: Mapping[str, Any],
    alternate_artifact_locations: Sequence[Mapping[str, Any]],
    missing_artifacts: Sequence[str] = (),
    unreadable_artifacts: Sequence[str] = (),
    provider_result_count: int | None = None,
    candidate_count: int | None = None,
    raw_retention_flags: Mapping[str, Any] | None = None,
    candidate_lineage_status: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if decision not in RETAINED_ARTIFACT_PREFLIGHT_DECISIONS:
        raise RetainedLiveArtifactPreflightError(
            "unknown retained artifact decision"
        )
    return _json_safe(
        _without_empty(
            {
                "phase": RETAINED_ARTIFACT_REPAIR_PHASE,
                "mode": "REPAIR",
                "usable_answer_verdict_target": "NO-BUT-JUSTIFIED",
                "decision": decision,
                "active_checkout_path_hint": ACTIVE_CHECKOUT_PATH_HINT,
                "lowercase_checkout_path_hint": LOWERCASE_CHECKOUT_PATH_HINT,
                "resolved_repo_root": str(repo_root),
                "repo_output_root": str(output_root),
                "artifact_dir": {
                    "repo_relative_path": _rel_from_root(artifact_dir, repo_root),
                    "resolved_path": str(artifact_dir),
                    "under_repo_output": _path_under(artifact_dir, output_root),
                },
                "required_artifact_names": list(RETAINED_ARTIFACT_REQUIRED_NAMES),
                "artifact_metadata": artifact_metadata,
                "alternate_artifact_locations": list(alternate_artifact_locations),
                "missing_artifacts": list(missing_artifacts),
                "unreadable_artifacts": list(unreadable_artifacts),
                "provider_result_count": provider_result_count,
                "candidate_count": candidate_count,
                "raw_retention_flags": raw_retention_flags,
                "allowed_sanitized_structures_only": (
                    decision == RETAINED_ARTIFACT_PREFLIGHT_PASS
                ),
                "candidate_lineage_status": candidate_lineage_status,
                "closed_surfaces_not_invoked": {
                    "provider_calls": 0,
                    "broker_calls": 0,
                    "fetch_read_calls": 0,
                    "retrieval_calls": 0,
                    "model_calls": 0,
                    "evidence_ledger_admissions": 0,
                    "citation_operations": 0,
                    "sufficiency_fap_author_operations": 0,
                },
            }
        )
    )


def _required_artifact_metadata(artifact_dir: Path, repo_root: Path) -> dict[str, Any]:
    return {
        name: _artifact_metadata(artifact_dir / name, repo_root)
        for name in RETAINED_ARTIFACT_REQUIRED_NAMES
    }


def _artifact_metadata(path: Path, repo_root: Path) -> dict[str, Any]:
    exists = path.exists()
    is_file = path.is_file()
    is_dir = path.is_dir()
    stat = path.stat() if exists else None
    return _without_empty(
        {
            "repo_relative_path": _rel_from_root(path, repo_root),
            "resolved_path": str(path),
            "exists": exists,
            "kind": "file" if is_file else "directory" if is_dir else "missing",
            "byte_size": stat.st_size if stat else None,
            "modified_time_unix": stat.st_mtime if stat else None,
            "read_permission": _read_permission(path) if is_file else False,
        }
    )


def _read_permission(path: Path) -> bool:
    try:
        with path.open("rb"):
            return True
    except OSError:
        return False


def _read_json_metadata(path: Path) -> tuple[Any, dict[str, Any]]:
    try:
        decoded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, {
            "json_parse_success": False,
            "json_top_level_type": None,
            "top_level_keys": [],
        }
    return decoded, {
        "json_parse_success": True,
        "json_top_level_type": type(decoded).__name__,
        "top_level_keys": sorted(str(key) for key in decoded)
        if isinstance(decoded, Mapping)
        else [],
    }


def _alternate_artifact_reports(
    alternate_repo_roots: Sequence[str | Path],
    *,
    active_repo_root: Path,
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for alternate_root in alternate_repo_roots:
        root = _resolve_path(alternate_root)
        if _same_path(root, active_repo_root):
            continue
        artifact_dir = root / "output" / RETAINED_ARTIFACT_OUTPUT_DIR_NAME
        metadata = _required_artifact_metadata(artifact_dir, root)
        reports.append(
            {
                "repo_root": str(root),
                "artifact_dir": {
                    "repo_relative_path": _rel_from_root(artifact_dir, root),
                    "resolved_path": str(artifact_dir),
                },
                "artifact_metadata": metadata,
                "all_required_artifacts_exist": all(
                    item.get("exists") is True and item.get("kind") == "file"
                    for item in metadata.values()
                ),
                "contents_read": False,
            }
        )
    return reports


def _matching_alternate_boundary_report(
    target: Path,
    alternate_repo_roots: Sequence[str | Path],
    *,
    active_repo_root: Path,
) -> dict[str, Any] | None:
    for alternate_root in alternate_repo_roots:
        root = _resolve_path(alternate_root)
        if _same_path(root, active_repo_root):
            continue
        alternate_output = _resolve_path(root / "output")
        if _path_under(target, alternate_output):
            metadata = _required_artifact_metadata(
                root / "output" / RETAINED_ARTIFACT_OUTPUT_DIR_NAME,
                root,
            )
            return {
                "repo_root": str(root),
                "artifact_dir": {
                    "repo_relative_path": _rel_from_root(target, root),
                    "resolved_path": str(target),
                },
                "artifact_metadata": metadata,
                "all_required_artifacts_exist": all(
                    item.get("exists") is True and item.get("kind") == "file"
                    for item in metadata.values()
                ),
                "contents_read": False,
            }
    return None


def _preflight_decision_from_error(exc: Exception) -> str:
    message = str(exc).casefold()
    if "must keep" in message or "retained" in message:
        return RETAINED_ARTIFACT_BLOCKED_RETENTION_FLAG
    if (
        "raw/private" in message
        or "private-looking" in message
        or "closed authority" in message
        or "closed runtime" in message
        or "unsupported fields" in message
    ):
        return RETAINED_ARTIFACT_BLOCKED_RAW_OR_PRIVATE_FIELD
    return RETAINED_ARTIFACT_BLOCKED_CANDIDATE_LINEAGE


def _retained_candidate_lineage_status(
    *,
    sanitized_results: Sequence[Mapping[str, Any]],
    search_candidate_packet: Mapping[str, Any],
    search_result_candidate_packet: Mapping[str, Any],
) -> dict[str, bool]:
    search_records = _safe_list(search_candidate_packet.get("candidate_records"))
    result_records = _safe_list(search_result_candidate_packet.get("candidate_records"))
    return {
        "search_candidate_packet_matches_search_result_packet": (
            _candidate_packet_lineage_signature(search_candidate_packet)
            == _candidate_packet_lineage_signature(search_result_candidate_packet)
        ),
        "provider_result_count_matches_candidate_count": (
            len(sanitized_results)
            == _bounded_int(search_result_candidate_packet.get("candidate_count"))
        ),
        "candidate_record_count_matches_packet_count": (
            len(result_records)
            == _bounded_int(search_result_candidate_packet.get("candidate_count"))
        ),
        "candidate_alias_record_count_matches_packet_count": (
            len(search_records)
            == _bounded_int(search_candidate_packet.get("candidate_count"))
        ),
        "provider_results_match_candidate_records_by_rank_url_domain": (
            _provider_results_match_candidate_records(
                sanitized_results=sanitized_results,
                candidate_records=result_records,
            )
        ),
    }


def _candidate_packet_lineage_signature(packet: Mapping[str, Any]) -> tuple[Any, ...]:
    records = _safe_list(packet.get("candidate_records"))
    return (
        packet.get("packet_id"),
        packet.get("packet_digest"),
        packet.get("candidate_count"),
        tuple(
            (
                record.get("candidate_id"),
                record.get("candidate_digest"),
                record.get("result_rank"),
                record.get("provider_call_index"),
                record.get("url"),
                record.get("domain"),
            )
            for record in records
            if isinstance(record, Mapping)
        ),
    )


def _provider_results_match_candidate_records(
    *,
    sanitized_results: Sequence[Mapping[str, Any]],
    candidate_records: Sequence[Any],
) -> bool:
    if len(sanitized_results) != len(candidate_records):
        return False
    for result, record_value in zip(sanitized_results, candidate_records, strict=True):
        record = _safe_mapping(record_value)
        if (
            result.get("url") != record.get("url")
            or result.get("domain") != record.get("domain")
            or _bounded_int(result.get("result_rank"))
            != _bounded_int(record.get("result_rank"))
            or _bounded_int(result.get("provider_call_index"))
            != _bounded_int(record.get("provider_call_index"))
        ):
            return False
    return True


def _retained_raw_flags(
    provider_envelope: Mapping[str, Any],
    candidate_packet: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "provider_results_raw_provider_payload_retained": provider_envelope.get(
            "raw_provider_payload_retained"
        ),
        "provider_results_raw_search_response_retained": provider_envelope.get(
            "raw_search_response_retained"
        ),
        "candidate_packet_raw_provider_payload_retained": candidate_packet.get(
            "raw_provider_payload_retained"
        ),
        "candidate_packet_raw_search_response_retained": candidate_packet.get(
            "raw_search_response_retained"
        ),
    }


def _decoded_raw_retention_flags(decoded: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "provider_results_raw_provider_payload_retained": _retention_flag_counts(
            decoded.get("sanitized_provider_results.json"),
            "raw_provider_payload_retained",
        ),
        "provider_results_raw_search_response_retained": _retention_flag_counts(
            decoded.get("sanitized_provider_results.json"),
            "raw_search_response_retained",
        ),
        "search_candidate_packet_raw_provider_payload_retained": _retention_flag_counts(
            decoded.get(CURRENT_RUN_CANDIDATE_PACKET_NAME),
            "raw_provider_payload_retained",
        ),
        "search_candidate_packet_raw_search_response_retained": _retention_flag_counts(
            decoded.get(CURRENT_RUN_CANDIDATE_PACKET_NAME),
            "raw_search_response_retained",
        ),
        "search_result_candidate_packet_raw_provider_payload_retained": (
            _retention_flag_counts(
                decoded.get(CANDIDATE_PACKET_NAME),
                "raw_provider_payload_retained",
            )
        ),
        "search_result_candidate_packet_raw_search_response_retained": (
            _retention_flag_counts(
                decoded.get(CANDIDATE_PACKET_NAME),
                "raw_search_response_retained",
            )
        ),
    }


def _retention_flag_counts(value: Any, key: str) -> dict[str, int]:
    counts = {"true": 0, "false": 0, "other": 0}
    for item in _retention_flag_values(value, key):
        if item is True:
            counts["true"] += 1
        elif item is False:
            counts["false"] += 1
        else:
            counts["other"] += 1
    return counts


def _retention_flag_values(value: Any, key: str) -> list[Any]:
    if isinstance(value, Mapping):
        found = [value[key]] if key in value else []
        for item in value.values():
            found.extend(_retention_flag_values(item, key))
        return found
    if isinstance(value, list | tuple | set | frozenset):
        found: list[Any] = []
        for item in value:
            found.extend(_retention_flag_values(item, key))
        return found
    return []


def _validate_false_retention(value: Mapping[str, Any], *, context: str) -> None:
    for key in ("raw_provider_payload_retained", "raw_search_response_retained"):
        if key in value and value.get(key) is not False:
            raise RetainedLiveArtifactPreflightError(
                f"{context} must keep {key} false"
            )


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(
        key
        for key in keys
        if key in RAW_OR_PRIVATE_KEYS
        or key in FORBIDDEN_AUTHORITY_KEYS
        or key.startswith("raw_")
    )
    for allowed_false_flag in (
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    ):
        if allowed_false_flag in forbidden:
            forbidden.remove(allowed_false_flag)
    if forbidden:
        raise RetainedLiveArtifactPreflightError(
            f"{context} contains forbidden raw/private or authority fields: "
            + ", ".join(forbidden)
        )
    markers = sorted(_private_value_markers(value))
    if markers:
        raise RetainedLiveArtifactPreflightError(
            f"{context} contains private-looking values: " + ", ".join(markers)
        )


def _private_value_markers(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for item in value.values():
            found.update(_private_value_markers(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_private_value_markers(item))
    elif isinstance(value, str):
        lowered = value.casefold()
        for marker in PRIVATE_VALUE_MARKERS:
            if marker in lowered:
                found.add(marker)
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _resolve_path(path: str | Path) -> Path:
    raw = Path(path)
    try:
        return raw.resolve()
    except OSError:
        return raw.absolute()


def _resolve_relative_to_root(path: str | Path, root: Path) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = root / raw
    return _resolve_path(raw)


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


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def _rel_from_root(path: str | Path, root: Path) -> str:
    raw = Path(path)
    try:
        return str(raw.resolve().relative_to(root))
    except (OSError, ValueError):
        return str(raw)


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _required_url(value: Any) -> str:
    url = _required_token(value, "provider result requires url", 700)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RetainedLiveArtifactPreflightError(
            "provider result requires http(s) url"
        )
    return url


def _required_token(value: Any, message: str, limit: int) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise RetainedLiveArtifactPreflightError(message)
    return text


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping | list | tuple | set | frozenset):
        raise RetainedLiveArtifactPreflightError(
            "provider result values must be scalar"
        )
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in PRIVATE_VALUE_MARKERS):
        raise RetainedLiveArtifactPreflightError(
            "provider result contains private-looking value"
        )
    return text[:limit]


def _clean_domain(value: Any) -> str | None:
    text = _clean_token(value, limit=260)
    if not text:
        return None
    parsed = urlparse(f"https://{text}" if "://" not in text else text)
    return (parsed.netloc or parsed.path).lower().strip("/")


def _domain_from_url(value: str) -> str | None:
    return urlparse(value).netloc.lower() or None


def _positive_int(value: Any, message: str) -> int:
    parsed = _bounded_int(value, default=0)
    if parsed <= 0:
        raise RetainedLiveArtifactPreflightError(message)
    return parsed


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed >= 0 else 0


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


__all__ = [
    "CANDIDATE_PACKET_NAME",
    "CURRENT_RUN_CANDIDATE_PACKET_NAME",
    "RETAINED_ARTIFACT_BLOCKED_CANDIDATE_LINEAGE",
    "RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_MISSING",
    "RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH",
    "RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_UNREADABLE",
    "RETAINED_ARTIFACT_BLOCKED_OUTPUT_BOUNDARY",
    "RETAINED_ARTIFACT_BLOCKED_RAW_OR_PRIVATE_FIELD",
    "RETAINED_ARTIFACT_BLOCKED_RETENTION_FLAG",
    "RETAINED_ARTIFACT_OUTPUT_DIR_NAME",
    "RETAINED_ARTIFACT_PREFLIGHT_DECISIONS",
    "RETAINED_ARTIFACT_PREFLIGHT_PASS",
    "RETAINED_ARTIFACT_REPAIR_PHASE",
    "RETAINED_ARTIFACT_REQUIRED_NAMES",
    "RetainedLiveArtifactPreflightError",
    "preflight_retained_live_artifacts",
]
