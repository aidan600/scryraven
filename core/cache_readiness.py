"""Observer-only cache/cost readiness helpers for AG-82B.

This module builds redacted cache-candidate observations for later ScryRaven
phases. It deliberately contains no cache lookup, memoization, provider/search
calls, retrieval integration, prompt construction, model selection, or runtime
reuse decisions. Candidate records are local/private readiness telemetry only.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Literal, Mapping, Sequence
from uuid import uuid4

from core.document_review import DocumentReviewContext
from core.project_sources import ProjectSource, SourceRevision
from core.thread_reports import ReportInputPacket, ThreadReportArtifact

CACHE_READINESS_SCHEMA_VERSION = "ag82b-cache-readiness-v1"
CACHE_READINESS_GENERATOR = "scryraven-ag82b-cache-readiness-observer"
DEFAULT_CACHE_READINESS_OUTPUT_ROOT = Path("output/cache_readiness")
REDACTION_MARKER = "redacted-no-raw-private-text-prompts-provider-payloads-or-report-body"
AG82B_REUSE_DISABLED_REASON = "reuse-disabled-ag82b"
NO_RUNTIME_REUSE_POSTURE = "observer-only-no-runtime-cache-reuse"

PrivacyScope = Literal[
    "session-private-document",
    "project-local-private",
    "project-source-local-private",
    "thread-report-local-private",
    "future-project-source-index-local-private",
    "unknown-private",
]
CostLatencyClass = Literal[
    "low-cost-low-latency",
    "medium-cost-medium-latency",
    "high-cost-high-latency",
    "unknown-cost-latency",
]
CandidateSurface = Literal[
    "document-parse",
    "document-chunk",
    "project-source-manifest",
    "thread-report-generation",
    "saved-report-artifact-storage",
    "future-project-source-indexing-retrieval",
]
ReuseBlockedReason = Literal[
    "reuse-disabled-ag82b",
    "private-scope-not-licensed-for-reuse",
    "missing-stable-key",
    "freshness-or-validation-required",
    "raw-private-text-not-cacheable",
]
InvalidationReason = Literal[
    "document-hash-changed",
    "parser-version-changed",
    "source-revision-changed",
    "privacy-scope-changed",
    "report-packet-or-provenance-digest-changed",
]

_RAW_FIELD_NAMES = frozenset(
    {
        "text",
        "raw_text",
        "normalized_text",
        "content",
        "body",
        "report_body",
        "prompt",
        "full_prompt",
        "provider_payload",
        "payload",
        "trace",
        "full_trace",
        "secret",
        "api_key",
        "token",
    }
)


@dataclass(frozen=True)
class CacheCandidateKey:
    """Stable candidate identity fields for future bounded reuse consideration."""

    surface: CandidateSurface
    schema_version: str
    privacy_scope: PrivacyScope
    fields: tuple[tuple[str, str], ...]
    key_digest: str
    safe_for_future_consideration: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "surface": self.surface,
            "schema_version": self.schema_version,
            "privacy_scope": self.privacy_scope,
            "fields": dict(self.fields),
            "key_digest": self.key_digest,
            "safe_for_future_consideration": self.safe_for_future_consideration,
        }


@dataclass(frozen=True)
class CacheabilityInputs:
    """Redacted inputs that explain which versions/hashes matter."""

    document_hash: str | None = None
    input_format: str | None = None
    parser_name: str | None = None
    parser_version: str | None = None
    parser_confidence: float | None = None
    source_record_id: str | None = None
    source_revision_id: str | None = None
    project_source_id: str | None = None
    project_id: str | None = None
    report_id: str | None = None
    report_type: str | None = None
    report_generator: str | None = None
    model_identity: str | None = None
    packet_schema_version: str | None = None
    packet_digest: str | None = None
    provenance_digest: str | None = None
    privacy_scope: PrivacyScope = "unknown-private"

    def to_dict(self) -> dict[str, object]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class CacheReadinessRecord:
    """Compact redacted AG-82B observation; never a cache entry or decision input."""

    record_id: str
    observed_at: str
    candidate_key: CacheCandidateKey
    cacheability_inputs: CacheabilityInputs
    invalidation_reasons: tuple[InvalidationReason, ...]
    blocked_reuse_reasons: tuple[ReuseBlockedReason, ...]
    cost_latency_class: CostLatencyClass
    would_save: str
    safe_for_future_consideration: bool
    notes: tuple[str, ...] = ()
    schema_version: str = CACHE_READINESS_SCHEMA_VERSION
    generator: str = CACHE_READINESS_GENERATOR
    redaction_marker: str = REDACTION_MARKER
    runtime_reuse_posture: str = NO_RUNTIME_REUSE_POSTURE

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "generator": self.generator,
            "record_id": self.record_id,
            "observed_at": self.observed_at,
            "candidate_key": self.candidate_key.to_dict(),
            "cacheability_inputs": self.cacheability_inputs.to_dict(),
            "invalidation_reasons": list(self.invalidation_reasons),
            "blocked_reuse_reasons": list(self.blocked_reuse_reasons),
            "cost_latency_class": self.cost_latency_class,
            "would_save": self.would_save,
            "safe_for_future_consideration": self.safe_for_future_consideration,
            "notes": list(self.notes),
            "redaction_marker": self.redaction_marker,
            "runtime_reuse_posture": self.runtime_reuse_posture,
        }


@dataclass(frozen=True)
class _SourceLike:
    source_record_id: str
    source_revision_id: str
    document_hash: str
    parser_metadata: Mapping[str, object]
    privacy_class: str = "local-private"
    project_source_id: str | None = None
    project_id: str | None = None
    schema_version: str | None = None


def build_document_parse_cache_candidate(
    context: DocumentReviewContext,
    *,
    privacy_scope: PrivacyScope = "session-private-document",
) -> CacheCandidateKey:
    """Build a parse candidate key from redacted document/parser metadata only."""

    metadata = context.metadata
    return _candidate_key(
        "document-parse",
        privacy_scope,
        {
            "document_hash": metadata.document_hash,
            "input_format": metadata.input_format,
            "parser_name": metadata.parser_name,
            "parser_version": metadata.parser_version,
            "parser_confidence": _format_confidence(metadata.parser_confidence),
            "document_review_version": metadata.version,
            "privacy_scope": privacy_scope,
            "schema_version": CACHE_READINESS_SCHEMA_VERSION,
        },
    )


def build_document_chunk_cache_candidate(
    context: DocumentReviewContext,
    *,
    privacy_scope: PrivacyScope = "session-private-document",
) -> CacheCandidateKey:
    """Build a chunk/anchor candidate key without storing chunk or anchor text."""

    metadata = context.metadata
    chunk_ids_digest = _digest_json([chunk.chunk_id for chunk in context.chunks])
    anchor_ids_digest = _digest_json([anchor.anchor_id for anchor in context.anchors])
    return _candidate_key(
        "document-chunk",
        privacy_scope,
        {
            "document_hash": metadata.document_hash,
            "input_format": metadata.input_format,
            "parser_name": metadata.parser_name,
            "parser_version": metadata.parser_version,
            "parser_confidence": _format_confidence(metadata.parser_confidence),
            "document_review_version": metadata.version,
            "anchor_count": str(len(context.anchors)),
            "chunk_count": str(len(context.chunks)),
            "anchor_ids_digest": anchor_ids_digest,
            "chunk_ids_digest": chunk_ids_digest,
            "privacy_scope": privacy_scope,
            "schema_version": CACHE_READINESS_SCHEMA_VERSION,
        },
    )


def build_project_source_cache_candidate(
    source: ProjectSource | SourceRevision,
    *,
    privacy_scope: PrivacyScope = "project-source-local-private",
) -> CacheCandidateKey:
    """Build a ProjectSource/SourceRevision candidate key from manifest metadata."""

    source_like = _source_like(source)
    parser_metadata = source_like.parser_metadata
    return _candidate_key(
        "project-source-manifest",
        privacy_scope,
        {
            "source_record_id": source_like.source_record_id,
            "source_revision_id": source_like.source_revision_id,
            "project_source_id": source_like.project_source_id or "",
            "project_id": source_like.project_id or "",
            "document_hash": source_like.document_hash,
            "parser_name": _string(parser_metadata.get("parser_name")),
            "parser_version": _string(parser_metadata.get("parser_version")),
            "parser_confidence": _format_confidence(parser_metadata.get("parser_confidence")),
            "privacy_class": source_like.privacy_class,
            "privacy_scope": privacy_scope,
            "manifest_schema_version": source_like.schema_version or "",
            "schema_version": CACHE_READINESS_SCHEMA_VERSION,
        },
    )


def build_thread_report_cache_candidate(
    packet: ReportInputPacket,
    *,
    artifact: ThreadReportArtifact | None = None,
    report_generator: str | None = None,
    model_identity: str = "model-identity-placeholder-ag82b-no-selection-change",
    privacy_scope: PrivacyScope = "thread-report-local-private",
) -> CacheCandidateKey:
    """Build a report-generation candidate key from packet/provenance digests."""

    generator = report_generator or (artifact.generator if artifact else "thread-report-generator-placeholder")
    project_id = _string(packet.project.get("project_id"))
    report_type = artifact.report_type if artifact else packet.report_type
    return _candidate_key(
        "thread-report-generation",
        privacy_scope,
        {
            "project_id": project_id,
            "report_id": artifact.report_id if artifact else "",
            "report_type": report_type,
            "model_identity": model_identity,
            "report_generator": generator,
            "packet_schema_version": packet.schema_version,
            "packet_digest": build_report_packet_digest(packet),
            "provenance_digest": build_report_provenance_digest(packet),
            "privacy_scope": privacy_scope,
            "schema_version": CACHE_READINESS_SCHEMA_VERSION,
        },
    )


def build_saved_report_artifact_cache_candidate(
    artifact: ThreadReportArtifact,
    *,
    packet: ReportInputPacket | None = None,
    privacy_scope: PrivacyScope = "thread-report-local-private",
) -> CacheCandidateKey:
    """Build an observation candidate for saved report artifact storage only."""

    fields = {
        "project_id": artifact.project_id,
        "report_id": artifact.report_id,
        "report_type": artifact.report_type,
        "report_generator": artifact.generator,
        "artifact_schema_version": artifact.schema_version,
        "body_path_digest": _digest_json(artifact.body_path),
        "provenance_digest": _digest_json([asdict(ref) for ref in artifact.source_provenance_references]),
        "privacy_scope": privacy_scope,
        "schema_version": CACHE_READINESS_SCHEMA_VERSION,
    }
    if packet is not None:
        fields["packet_digest"] = build_report_packet_digest(packet)
    return _candidate_key("saved-report-artifact-storage", privacy_scope, fields)


def build_future_project_source_index_cache_candidate(
    source: ProjectSource | SourceRevision,
    *,
    indexer_version: str = "future-indexer-unimplemented-ag82b",
    retrieval_profile: str = "future-project-source-retrieval-unimplemented-ag82b",
    privacy_scope: PrivacyScope = "future-project-source-index-local-private",
) -> CacheCandidateKey:
    """Build an observation-only candidate for future ProjectSource indexing/retrieval."""

    source_like = _source_like(source)
    parser_metadata = source_like.parser_metadata
    return _candidate_key(
        "future-project-source-indexing-retrieval",
        privacy_scope,
        {
            "source_record_id": source_like.source_record_id,
            "source_revision_id": source_like.source_revision_id,
            "project_source_id": source_like.project_source_id or "",
            "project_id": source_like.project_id or "",
            "document_hash": source_like.document_hash,
            "parser_name": _string(parser_metadata.get("parser_name")),
            "parser_version": _string(parser_metadata.get("parser_version")),
            "indexer_version": indexer_version,
            "retrieval_profile": retrieval_profile,
            "privacy_class": source_like.privacy_class,
            "privacy_scope": privacy_scope,
            "schema_version": CACHE_READINESS_SCHEMA_VERSION,
        },
    )


def build_cacheability_inputs_from_candidate(candidate: CacheCandidateKey) -> CacheabilityInputs:
    """Project redacted candidate fields into a compact cacheability-input record."""

    fields = dict(candidate.fields)
    return CacheabilityInputs(
        document_hash=_empty_to_none(fields.get("document_hash")),
        input_format=_empty_to_none(fields.get("input_format")),
        parser_name=_empty_to_none(fields.get("parser_name")),
        parser_version=_empty_to_none(fields.get("parser_version")),
        parser_confidence=_parse_float(fields.get("parser_confidence")),
        source_record_id=_empty_to_none(fields.get("source_record_id")),
        source_revision_id=_empty_to_none(fields.get("source_revision_id")),
        project_source_id=_empty_to_none(fields.get("project_source_id")),
        project_id=_empty_to_none(fields.get("project_id")),
        report_id=_empty_to_none(fields.get("report_id")),
        report_type=_empty_to_none(fields.get("report_type")),
        report_generator=_empty_to_none(fields.get("report_generator")),
        model_identity=_empty_to_none(fields.get("model_identity")),
        packet_schema_version=_empty_to_none(fields.get("packet_schema_version")),
        packet_digest=_empty_to_none(fields.get("packet_digest")),
        provenance_digest=_empty_to_none(fields.get("provenance_digest")),
        privacy_scope=candidate.privacy_scope,
    )


def build_cache_readiness_record(
    candidate: CacheCandidateKey,
    *,
    invalidation_reasons: Sequence[InvalidationReason] | None = None,
    blocked_reuse_reasons: Sequence[ReuseBlockedReason] | None = None,
    cost_latency_class: CostLatencyClass = "unknown-cost-latency",
    would_save: str = "future bounded reuse may save repeated local work if licensed later",
    notes: Sequence[str] = (),
    observed_at: datetime | str | None = None,
    record_id: str | None = None,
) -> CacheReadinessRecord:
    """Create a redacted observer-only readiness record from a candidate key."""

    blocked = tuple(dict.fromkeys(blocked_reuse_reasons or default_blocked_reuse_reasons(candidate.privacy_scope)))
    invalidations = tuple(dict.fromkeys(invalidation_reasons or default_invalidation_reasons(candidate.surface)))
    safe = candidate.safe_for_future_consideration and "missing-stable-key" not in blocked
    timestamp = observed_at if isinstance(observed_at, str) else (observed_at or datetime.now(timezone.utc)).isoformat()
    return CacheReadinessRecord(
        record_id=record_id or f"cr_{uuid4().hex}",
        observed_at=timestamp,
        candidate_key=candidate,
        cacheability_inputs=build_cacheability_inputs_from_candidate(candidate),
        invalidation_reasons=invalidations,
        blocked_reuse_reasons=blocked,
        cost_latency_class=cost_latency_class,
        would_save=would_save,
        safe_for_future_consideration=safe,
        notes=tuple(_bounded_note(note) for note in notes),
    )


def classify_invalidation_reasons(
    *,
    document_hash_changed: bool = False,
    parser_version_changed: bool = False,
    source_revision_changed: bool = False,
    privacy_scope_changed: bool = False,
    report_packet_or_provenance_digest_changed: bool = False,
) -> tuple[InvalidationReason, ...]:
    """Classify invalidation flags into stable AG-82B labels."""

    reasons: list[InvalidationReason] = []
    if document_hash_changed:
        reasons.append("document-hash-changed")
    if parser_version_changed:
        reasons.append("parser-version-changed")
    if source_revision_changed:
        reasons.append("source-revision-changed")
    if privacy_scope_changed:
        reasons.append("privacy-scope-changed")
    if report_packet_or_provenance_digest_changed:
        reasons.append("report-packet-or-provenance-digest-changed")
    return tuple(reasons)


def classify_blocked_reuse_reasons(
    *,
    reuse_disabled_ag82b: bool = True,
    private_scope_not_licensed_for_reuse: bool = False,
    missing_stable_key: bool = False,
    freshness_or_validation_required: bool = False,
    raw_private_text_not_cacheable: bool = False,
) -> tuple[ReuseBlockedReason, ...]:
    """Classify why a candidate must not be reused in AG-82B."""

    reasons: list[ReuseBlockedReason] = []
    if reuse_disabled_ag82b:
        reasons.append("reuse-disabled-ag82b")
    if private_scope_not_licensed_for_reuse:
        reasons.append("private-scope-not-licensed-for-reuse")
    if missing_stable_key:
        reasons.append("missing-stable-key")
    if freshness_or_validation_required:
        reasons.append("freshness-or-validation-required")
    if raw_private_text_not_cacheable:
        reasons.append("raw-private-text-not-cacheable")
    return tuple(reasons)


def default_blocked_reuse_reasons(privacy_scope: PrivacyScope) -> tuple[ReuseBlockedReason, ...]:
    """Return conservative observer-only block reasons for local/private scopes."""

    reasons: list[ReuseBlockedReason] = ["reuse-disabled-ag82b"]
    if "private" in privacy_scope:
        reasons.append("private-scope-not-licensed-for-reuse")
    return tuple(reasons)


def default_invalidation_reasons(surface: CandidateSurface) -> tuple[InvalidationReason, ...]:
    """Return likely invalidation inputs for a candidate surface."""

    common: list[InvalidationReason] = ["privacy-scope-changed"]
    if surface in {"document-parse", "document-chunk"}:
        return ("document-hash-changed", "parser-version-changed", *common)
    if surface in {"project-source-manifest", "future-project-source-indexing-retrieval"}:
        return ("document-hash-changed", "parser-version-changed", "source-revision-changed", *common)
    if surface in {"thread-report-generation", "saved-report-artifact-storage"}:
        return ("source-revision-changed", "report-packet-or-provenance-digest-changed", *common)
    return tuple(common)


def build_report_packet_digest(packet: ReportInputPacket) -> str:
    """Hash a report packet for identity without persisting packet text."""

    return _digest_json(_redacted_dataclass(packet))


def build_report_provenance_digest(packet: ReportInputPacket) -> str:
    """Hash report provenance IDs/metadata without persisting report or prompt text."""

    return _digest_json([_redacted_dataclass(ref) for ref in packet.provenance_references])


def write_cache_readiness_record(
    record: CacheReadinessRecord,
    *,
    output_root: str | Path | None = None,
) -> Path:
    """Write one redacted local readiness record to an ignored output directory."""

    root = Path(output_root) if output_root is not None else DEFAULT_CACHE_READINESS_OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    payload = record.to_dict()
    _assert_redacted_payload(payload)
    path = root / f"{_safe_filename(record.record_id)}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_cache_readiness_record(path: str | Path) -> dict[str, object]:
    """Read a local readiness record as JSON-safe data for tests/review tools."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Cache readiness record must be a JSON object.")
    return payload


def summarize_cache_readiness_record(record: CacheReadinessRecord | Mapping[str, object]) -> dict[str, object]:
    """Return a compact review summary without any raw content fields."""

    payload = record.to_dict() if isinstance(record, CacheReadinessRecord) else dict(record)
    candidate = payload.get("candidate_key", {})
    if not isinstance(candidate, Mapping):
        candidate = {}
    return {
        "schema_version": payload.get("schema_version"),
        "generator": payload.get("generator"),
        "surface": candidate.get("surface"),
        "privacy_scope": candidate.get("privacy_scope"),
        "key_digest": candidate.get("key_digest"),
        "blocked_reuse_reasons": list(payload.get("blocked_reuse_reasons", [])),
        "invalidation_reasons": list(payload.get("invalidation_reasons", [])),
        "cost_latency_class": payload.get("cost_latency_class"),
        "runtime_reuse_posture": payload.get("runtime_reuse_posture"),
        "redaction_marker": payload.get("redaction_marker"),
    }


def _candidate_key(
    surface: CandidateSurface,
    privacy_scope: PrivacyScope,
    fields: Mapping[str, object],
) -> CacheCandidateKey:
    clean_fields = tuple(sorted((str(key), _string(value)) for key, value in fields.items()))
    missing_stable = any(key for key, value in clean_fields if key in _required_fields(surface) and not value)
    digest = _digest_json({"surface": surface, "privacy_scope": privacy_scope, "fields": clean_fields})
    return CacheCandidateKey(
        surface=surface,
        schema_version=CACHE_READINESS_SCHEMA_VERSION,
        privacy_scope=privacy_scope,
        fields=clean_fields,
        key_digest=digest,
        safe_for_future_consideration=not missing_stable,
    )


def _required_fields(surface: CandidateSurface) -> frozenset[str]:
    required = {
        "document-parse": {"document_hash", "input_format", "parser_name", "parser_version", "privacy_scope"},
        "document-chunk": {"document_hash", "input_format", "parser_name", "parser_version"},
        "project-source-manifest": {"source_record_id", "source_revision_id", "document_hash", "parser_version"},
        "thread-report-generation": {
            "project_id",
            "report_type",
            "report_generator",
            "packet_schema_version",
            "packet_digest",
            "provenance_digest",
        },
        "saved-report-artifact-storage": {"project_id", "report_id", "report_type", "artifact_schema_version"},
        "future-project-source-indexing-retrieval": {
            "source_record_id",
            "source_revision_id",
            "document_hash",
            "indexer_version",
        },
    }
    return frozenset(required.get(surface, set()))


def _source_like(source: ProjectSource | SourceRevision) -> _SourceLike:
    if isinstance(source, ProjectSource):
        document_hash = _string(source.source_identity.get("document_hash"))
        return _SourceLike(
            source_record_id=source.source_record_id,
            source_revision_id=source.source_revision_id,
            document_hash=document_hash,
            parser_metadata=source.parser_metadata,
            privacy_class=source.privacy_class,
            project_source_id=source.project_source_id,
            project_id=source.project_id,
            schema_version=source.schema_version,
        )
    return _SourceLike(
        source_record_id=source.source_record_id,
        source_revision_id=source.source_revision_id,
        document_hash=source.document_hash,
        parser_metadata=source.parser_metadata,
        privacy_class=source.privacy_class,
        schema_version=source.schema_version,
    )


def _redacted_dataclass(value: object) -> object:
    if is_dataclass(value):
        return _redacted_mapping(asdict(value))
    if isinstance(value, Mapping):
        return _redacted_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_redacted_dataclass(item) for item in value]
    return value


def _redacted_mapping(value: Mapping[str, object]) -> dict[str, object]:
    redacted: dict[str, object] = {}
    for key, item in value.items():
        key_string = str(key)
        if key_string in _RAW_FIELD_NAMES:
            redacted[f"{key_string}_digest"] = _digest_json(item)
            redacted[f"{key_string}_redacted"] = True
        elif isinstance(item, Mapping) or is_dataclass(item):
            redacted[key_string] = _redacted_dataclass(item)
        elif isinstance(item, (list, tuple)):
            redacted[key_string] = [_redacted_dataclass(entry) for entry in item]
        else:
            redacted[key_string] = item
    return redacted


def _assert_redacted_payload(payload: Mapping[str, object]) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    forbidden_names = [f'"{name}"' for name in _RAW_FIELD_NAMES]
    leaked_names = [name for name in forbidden_names if name in serialized]
    if leaked_names:
        raise ValueError(f"Cache readiness payload contains forbidden raw field names: {', '.join(leaked_names)}")


def _digest_json(value: object) -> str:
    return sha256(json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _format_confidence(value: object) -> str:
    parsed = _parse_float(value)
    return "" if parsed is None else f"{parsed:.4f}"


def _parse_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (dict, list, tuple, set, frozenset)):
        return _digest_json(value)
    return str(value)


def _empty_to_none(value: str | None) -> str | None:
    return value if value else None


def _bounded_note(note: str) -> str:
    clean = " ".join(str(note).split())
    return clean[:240]


def _safe_filename(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)
    return safe[:120] or f"cr_{uuid4().hex}"
