"""Generated thread-report artifacts for Projects (AG-86A).

This module is intentionally narrow: it builds a bounded packet from already
available thread/project context, calls an injected model function only for the
thread-report task, and saves generated Markdown reports as Project artifacts.
It does not import or call providers, search, retrieval, prompts for ordinary
answers, caches, databases, connectors, or the pipeline/orchestrator.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from core.project_sources import (
    LOCAL_PRIVATE_BOUNDARY_MARKER,
    Project,
    ProjectSource,
    default_storage_root,
    list_project_sources,
    load_project,
)

THREAD_REPORT_SCHEMA_VERSION = "ag86a-thread-report-v1"
THREAD_REPORT_GENERATOR = "scryraven-ag86a-thread-report-generator"
THREAD_REPORT_TYPE = "thread_report"
GENERATED_ARTIFACT_LABEL = "generated-project-artifact"
NOT_PRIMARY_EVIDENCE_LABEL = "not-primary-evidence"
AVAILABLE_CONTEXT_LABEL = "based-on-available-thread-project-context"
MISSING_PROVENANCE_LABEL = "some-provenance-may-be-unavailable"
NO_RETRIEVAL_INTEGRATION_LABEL = "no-retrieval-integration-or-project-source-injection"
REPORTS_DIRECTORY = "reports"
REPORT_BODY_DIRECTORY = "bodies"
_INPUT_TEXT_LIMIT = 12_000
_BODY_TEXT_LIMIT = 80_000
_PREVIEW_LIMIT = 700

Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]
ThreadReportModel = Callable[..., str]

THREAD_REPORT_SYSTEM_PROMPT = """You generate ScryRaven thread reports only.
Do not answer as the normal chat Author. Do not perform search, retrieval, public
validation, provider selection, source ranking, or citation re-ordering. Use only
the supplied JSON packet. Preserve boundaries between thread material, thread
attachments, Project Sources, document-local anchors, and web evidence.

The report is a generated Project artifact and not primary evidence. It may
summarize, organize, and synthesize the supplied context, but it must not present
model synthesis as source truth. If provenance is missing or unavailable, say so.
"""

THREAD_REPORT_USER_TEMPLATE = """Create a structured Markdown thread report from this JSON packet.

Required sections:
1. Generated report boundary
2. Executive summary
3. Key decisions / findings
4. Evidence and provenance references
5. Unresolved gaps
6. Risks / open questions
7. Next actions, only if supported by the supplied context

Rules:
- Start by labeling this as a generated Project artifact and not primary evidence.
- Cite/reference the packet's provenance IDs, source IDs, ProjectSource IDs,
  document-anchor references, attachment references, and web URLs where present.
- Keep document-local claims local to the document/thread unless public evidence
  in the packet supports broader truth.
- Distinguish thread material, Project Sources, thread attachments, document
  anchors, and web evidence.
- Preserve unresolved gaps and missing/unavailable provenance labels.
- Do not invent sources, URLs, anchors, attachments, Project Sources, or citations.
- Do not claim this report is a Project Source or primary evidence.

JSON packet:
{packet_json}
"""


@dataclass(frozen=True)
class ProvenanceReference:
    """A compact reference to source material visible to the app."""

    reference_id: str
    reference_type: str
    title: str | None = None
    source_id: str | None = None
    url: str | None = None
    domain: str | None = None
    project_source_id: str | None = None
    source_record_id: str | None = None
    source_revision_id: str | None = None
    anchor_ref: str | None = None
    posture_label: str = "available-reference"
    preview: str | None = None


@dataclass(frozen=True)
class ReportInputPacket:
    """Bounded packet supplied to the injected thread-report model seam."""

    schema_version: str
    report_type: str
    project: dict[str, object]
    thread: dict[str, object]
    messages: tuple[dict[str, object], ...]
    final_report: dict[str, object]
    provenance_references: tuple[ProvenanceReference, ...]
    evidence_posture_labels: tuple[str, ...]
    unresolved_gaps: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class ThreadReportArtifact:
    """Saved generated Project artifact manifest.

    The Markdown body is stored separately. The manifest deliberately labels the
    report as generated synthesis and not primary evidence.
    """

    report_id: str
    project_id: str
    title: str
    report_type: str
    generated_at: str
    source_provenance_references: tuple[ProvenanceReference, ...]
    evidence_posture_labels: tuple[str, ...]
    unresolved_gaps: tuple[str, ...]
    body_path: str
    generated_artifact: bool
    not_primary_evidence: str
    schema_version: str = THREAD_REPORT_SCHEMA_VERSION
    generator: str = THREAD_REPORT_GENERATOR
    local_private_boundary: str = LOCAL_PRIVATE_BOUNDARY_MARKER
    retrieval_integration: str = NO_RETRIEVAL_INTEGRATION_LABEL


@dataclass(frozen=True)
class ThreadReportSaveResult:
    """Return packet for generated report creation and persistence."""

    artifact: ThreadReportArtifact
    body: str
    prompt: str
    artifact_manifest_path: Path
    body_path: Path


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def default_id_factory(prefix: str) -> str:
    """Return a stable-format locally unique ID."""

    return f"{prefix}_{uuid4().hex}"


def thread_report_boundary_caption() -> str:
    """Return a user-facing boundary caption for generated reports."""

    return " ".join(
        (
            "Generated Project artifact; not primary evidence.",
            "Based on available thread/project context; some provenance may be unavailable.",
            "Saved reports are not Project Sources.",
            "No retrieval integration or Project Source injection into ordinary answers.",
        )
    )


def build_report_input_packet(
    session: dict[str, Any],
    project: Project | str,
    *,
    storage_root: str | Path | None = None,
    extra_thread_references: tuple[dict[str, object], ...] | list[dict[str, object]] = (),
) -> ReportInputPacket:
    """Build a bounded report packet from app-visible session/project data."""

    root = _prepare_storage_root(storage_root, create=False)
    loaded_project = load_project(project, storage_root=root) if isinstance(project, str) else project
    missing: list[str] = []
    messages = _messages_from_session(session, missing)
    final_report = _final_report_from_session(session, missing)
    provenance = _provenance_from_session(session, missing)
    project_sources = list_project_sources(loaded_project, storage_root=root)
    provenance.extend(_provenance_from_project_sources(project_sources))
    provenance.extend(_provenance_from_extra_refs(extra_thread_references))
    if not provenance:
        missing.append("source/provenance references unavailable")

    unresolved = _unresolved_gaps(session, missing)
    labels = (
        GENERATED_ARTIFACT_LABEL,
        NOT_PRIMARY_EVIDENCE_LABEL,
        AVAILABLE_CONTEXT_LABEL,
        MISSING_PROVENANCE_LABEL if missing else "all-visible-provenance-packaged",
        NO_RETRIEVAL_INTEGRATION_LABEL,
    )
    return ReportInputPacket(
        schema_version=THREAD_REPORT_SCHEMA_VERSION,
        report_type=THREAD_REPORT_TYPE,
        project={
            "project_id": loaded_project.project_id,
            "name": loaded_project.name,
            "privacy_class": loaded_project.privacy_class,
            "project_source_count": len(loaded_project.project_source_ids),
        },
        thread={
            "session_id": _clean(session.get("id")),
            "run_id": _clean(session.get("run_id")),
            "title": _clean(session.get("title")),
            "query": _clean(session.get("query")),
            "timestamp": _clean(session.get("timestamp")),
        },
        messages=tuple(messages),
        final_report=final_report,
        provenance_references=tuple(provenance),
        evidence_posture_labels=labels,
        unresolved_gaps=tuple(unresolved),
        missing=tuple(dict.fromkeys(missing)),
    )


def build_thread_report_prompt(packet: ReportInputPacket) -> str:
    """Build the narrow user prompt for thread-report generation only."""

    return THREAD_REPORT_USER_TEMPLATE.format(packet_json=json.dumps(_packet_payload(packet), indent=2, sort_keys=True))


def generate_thread_report_body(packet: ReportInputPacket, model_fn: ThreadReportModel) -> tuple[str, str]:
    """Generate Markdown using an injected model function for thread reports only."""

    prompt = build_thread_report_prompt(packet)
    body = model_fn(prompt, system_prompt=THREAD_REPORT_SYSTEM_PROMPT)
    if not isinstance(body, str):
        raise TypeError("Thread report model seam must return a Markdown string.")
    clean_body = body.strip()
    if not clean_body:
        raise ValueError("Thread report model seam returned an empty report.")
    return (_bounded(clean_body, _BODY_TEXT_LIMIT), prompt)


def generate_and_save_thread_report(
    session: dict[str, Any],
    project: Project | str,
    model_fn: ThreadReportModel,
    *,
    storage_root: str | Path | None = None,
    title: str | None = None,
    clock: Clock = utc_now,
    id_factory: IdFactory = default_id_factory,
    extra_thread_references: tuple[dict[str, object], ...] | list[dict[str, object]] = (),
) -> ThreadReportSaveResult:
    """Build packet, call the injected report model, and save a Project artifact."""

    root = _prepare_storage_root(storage_root)
    loaded_project = load_project(project, storage_root=root) if isinstance(project, str) else project
    packet = build_report_input_packet(
        session,
        loaded_project,
        storage_root=root,
        extra_thread_references=extra_thread_references,
    )
    body, prompt = generate_thread_report_body(packet, model_fn)
    return save_thread_report_artifact(
        loaded_project,
        body,
        packet,
        storage_root=root,
        title=title,
        clock=clock,
        id_factory=id_factory,
        prompt=prompt,
    )


def save_thread_report_artifact(
    project: Project | str,
    body: str,
    packet: ReportInputPacket,
    *,
    storage_root: str | Path | None = None,
    title: str | None = None,
    clock: Clock = utc_now,
    id_factory: IdFactory = default_id_factory,
    prompt: str = "",
) -> ThreadReportSaveResult:
    """Persist a generated report manifest and Markdown body under reports/."""

    root = _prepare_storage_root(storage_root)
    loaded_project = load_project(project, storage_root=root) if isinstance(project, str) else project
    report_id = id_factory("rpt")
    timestamp = clock().astimezone(timezone.utc).isoformat()
    clean_title = (
        title or f"Thread report — {packet.thread.get('title') or packet.thread.get('query') or report_id}"
    ).strip()
    if not clean_title:
        clean_title = f"Thread report — {report_id}"
    body_relative = f"{REPORTS_DIRECTORY}/{REPORT_BODY_DIRECTORY}/{_safe_id(report_id)}.md"
    body_path = root / body_relative
    artifact = ThreadReportArtifact(
        report_id=report_id,
        project_id=loaded_project.project_id,
        title=clean_title,
        report_type=THREAD_REPORT_TYPE,
        generated_at=timestamp,
        source_provenance_references=packet.provenance_references,
        evidence_posture_labels=packet.evidence_posture_labels,
        unresolved_gaps=packet.unresolved_gaps,
        body_path=body_relative,
        generated_artifact=True,
        not_primary_evidence=NOT_PRIMARY_EVIDENCE_LABEL,
    )
    manifest_path = _report_manifest_path(root, report_id)
    _write_text(body_path, _ensure_boundary_preamble(body))
    _write_json(manifest_path, _artifact_payload(artifact))
    return ThreadReportSaveResult(
        artifact=artifact,
        body=body_path.read_text(encoding="utf-8"),
        prompt=prompt,
        artifact_manifest_path=manifest_path,
        body_path=body_path,
    )


def load_thread_report(report_id: str, *, storage_root: str | Path | None = None) -> ThreadReportArtifact:
    """Load one thread-report artifact manifest by ID."""

    root = _prepare_storage_root(storage_root, create=False)
    return _artifact_from_payload(_read_json(_report_manifest_path(root, report_id)))


def load_thread_report_body(artifact: ThreadReportArtifact, *, storage_root: str | Path | None = None) -> str:
    """Load the Markdown body for a saved report artifact."""

    root = _prepare_storage_root(storage_root, create=False)
    return (root / artifact.body_path).read_text(encoding="utf-8")


def list_thread_reports(
    project: Project | str, *, storage_root: str | Path | None = None
) -> tuple[ThreadReportArtifact, ...]:
    """List generated thread reports saved for one Project."""

    root = _prepare_storage_root(storage_root, create=False)
    project_id = project if isinstance(project, str) else project.project_id
    reports_dir = root / REPORTS_DIRECTORY
    if not reports_dir.exists():
        return ()
    reports = []
    for path in reports_dir.glob("*.json"):
        artifact = _artifact_from_payload(_read_json(path))
        if artifact.project_id == project_id:
            reports.append(artifact)
    return tuple(sorted(reports, key=lambda item: item.generated_at))


def format_thread_report_row(artifact: ThreadReportArtifact) -> dict[str, object]:
    """Format a saved report artifact for UI/tests."""

    return {
        "Title": artifact.title,
        "Report ID": artifact.report_id,
        "Type": artifact.report_type,
        "Generated": artifact.generated_at,
        "Generated artifact": artifact.generated_artifact,
        "Not primary evidence": artifact.not_primary_evidence,
        "Provenance refs": len(artifact.source_provenance_references),
        "Unresolved gaps": len(artifact.unresolved_gaps),
        "Retrieval integration": artifact.retrieval_integration,
    }


def _messages_from_session(session: dict[str, Any], missing: list[str]) -> list[dict[str, object]]:
    raw_messages = session.get("chat_messages")
    messages: list[dict[str, object]] = []
    if isinstance(raw_messages, list):
        for index, message in enumerate(raw_messages[:40]):
            if not isinstance(message, dict):
                continue
            role = _clean(message.get("role")) or "unknown"
            content = _bounded(_clean(message.get("content")), _INPUT_TEXT_LIMIT // 4)
            if content:
                messages.append({"message_id": f"chat_{index + 1}", "role": role, "content": content})
    if not messages:
        query = _clean(session.get("query"))
        if query:
            messages.append({"message_id": "thread_query", "role": "user", "content": _bounded(query, 2000)})
        else:
            missing.append("thread user messages unavailable")
    return messages


def _final_report_from_session(session: dict[str, Any], missing: list[str]) -> dict[str, object]:
    report = _clean(session.get("report"))
    if not report:
        missing.append("assistant final report unavailable")
        return {"available": False, "text": ""}
    return {"available": True, "text": _bounded(report, _INPUT_TEXT_LIMIT)}


def _provenance_from_session(session: dict[str, Any], missing: list[str]) -> list[ProvenanceReference]:
    passages = session.get("top_passages")
    if not isinstance(passages, list) or not passages:
        missing.append("thread retrieved evidence unavailable")
        return []
    refs: list[ProvenanceReference] = []
    for index, passage in enumerate(passages[:80]):
        if not isinstance(passage, dict):
            continue
        source_id = _clean(passage.get("source_id"))
        refs.append(
            ProvenanceReference(
                reference_id=f"thread_evidence_{source_id or index + 1}",
                reference_type="thread_web_evidence",
                title=_clean(passage.get("title")) or None,
                source_id=source_id or None,
                url=_clean(passage.get("url")) or None,
                domain=_clean(passage.get("domain")) or None,
                posture_label="thread-visible-web-evidence-reference",
                preview=_bounded(
                    _clean(passage.get("text") or passage.get("snippet") or passage.get("raw_content")), _PREVIEW_LIMIT
                )
                or None,
            )
        )
    return refs


def _provenance_from_project_sources(project_sources: tuple[ProjectSource, ...]) -> list[ProvenanceReference]:
    refs: list[ProvenanceReference] = []
    for source in project_sources:
        refs.append(
            ProvenanceReference(
                reference_id=f"project_source_{source.project_source_id}",
                reference_type="project_source_reference",
                title=source.title,
                project_source_id=source.project_source_id,
                source_record_id=source.source_record_id,
                source_revision_id=source.source_revision_id,
                anchor_ref=source.anchor_manifest_ref,
                posture_label=f"{source.evidence_role}; {source.validation_posture}; not-report-primary-evidence",
                preview=str(source.source_obligation_summary)[:_PREVIEW_LIMIT]
                if source.source_obligation_summary
                else None,
            )
        )
    return refs


def _provenance_from_extra_refs(
    extra_refs: tuple[dict[str, object], ...] | list[dict[str, object]],
) -> list[ProvenanceReference]:
    refs: list[ProvenanceReference] = []
    for index, ref in enumerate(extra_refs[:40]):
        if not isinstance(ref, dict):
            continue
        refs.append(
            ProvenanceReference(
                reference_id=_clean(ref.get("reference_id")) or f"thread_attachment_{index + 1}",
                reference_type=_clean(ref.get("reference_type")) or "thread_attachment_reference",
                title=_clean(ref.get("title")) or None,
                url=_clean(ref.get("url")) or None,
                anchor_ref=_clean(ref.get("anchor_ref")) or None,
                posture_label=_clean(ref.get("posture_label")) or "thread-visible-attachment-reference",
                preview=_bounded(_clean(ref.get("preview")), _PREVIEW_LIMIT) or None,
            )
        )
    return refs


def _unresolved_gaps(session: dict[str, Any], missing: list[str]) -> list[str]:
    gaps: list[str] = []
    failure_card = session.get("failure_card")
    if isinstance(failure_card, dict):
        for field in ("reason", "message", "summary"):
            value = _clean(failure_card.get(field))
            if value:
                gaps.append(_bounded(value, 700))
    gaps.extend(missing)
    if not gaps:
        gaps.append("No explicit unresolved gaps were available beyond model-visible context limits.")
    return list(dict.fromkeys(gaps))


def _packet_payload(packet: ReportInputPacket) -> dict[str, object]:
    payload = asdict(packet)
    payload["provenance_references"] = [asdict(ref) for ref in packet.provenance_references]
    payload["messages"] = list(packet.messages)
    payload["evidence_posture_labels"] = list(packet.evidence_posture_labels)
    payload["unresolved_gaps"] = list(packet.unresolved_gaps)
    payload["missing"] = list(packet.missing)
    return payload


def _artifact_payload(artifact: ThreadReportArtifact) -> dict[str, object]:
    payload = asdict(artifact)
    payload["source_provenance_references"] = [asdict(ref) for ref in artifact.source_provenance_references]
    payload["evidence_posture_labels"] = list(artifact.evidence_posture_labels)
    payload["unresolved_gaps"] = list(artifact.unresolved_gaps)
    return payload


def _artifact_from_payload(payload: dict[str, object]) -> ThreadReportArtifact:
    refs = tuple(
        _provenance_from_payload(item)
        for item in payload.get("source_provenance_references", [])
        if isinstance(item, dict)
    )
    return ThreadReportArtifact(
        report_id=str(payload["report_id"]),
        project_id=str(payload["project_id"]),
        title=str(payload["title"]),
        report_type=str(payload.get("report_type", THREAD_REPORT_TYPE)),
        generated_at=str(payload["generated_at"]),
        source_provenance_references=refs,
        evidence_posture_labels=tuple(str(item) for item in payload.get("evidence_posture_labels", [])),
        unresolved_gaps=tuple(str(item) for item in payload.get("unresolved_gaps", [])),
        body_path=str(payload["body_path"]),
        generated_artifact=bool(payload.get("generated_artifact", True)),
        not_primary_evidence=str(payload.get("not_primary_evidence", NOT_PRIMARY_EVIDENCE_LABEL)),
        schema_version=str(payload.get("schema_version", THREAD_REPORT_SCHEMA_VERSION)),
        generator=str(payload.get("generator", THREAD_REPORT_GENERATOR)),
        local_private_boundary=str(payload.get("local_private_boundary", LOCAL_PRIVATE_BOUNDARY_MARKER)),
        retrieval_integration=str(payload.get("retrieval_integration", NO_RETRIEVAL_INTEGRATION_LABEL)),
    )


def _provenance_from_payload(payload: dict[str, object]) -> ProvenanceReference:
    return ProvenanceReference(
        reference_id=str(payload["reference_id"]),
        reference_type=str(payload["reference_type"]),
        title=payload.get("title") if isinstance(payload.get("title"), str) else None,
        source_id=payload.get("source_id") if isinstance(payload.get("source_id"), str) else None,
        url=payload.get("url") if isinstance(payload.get("url"), str) else None,
        domain=payload.get("domain") if isinstance(payload.get("domain"), str) else None,
        project_source_id=payload.get("project_source_id")
        if isinstance(payload.get("project_source_id"), str)
        else None,
        source_record_id=payload.get("source_record_id") if isinstance(payload.get("source_record_id"), str) else None,
        source_revision_id=payload.get("source_revision_id")
        if isinstance(payload.get("source_revision_id"), str)
        else None,
        anchor_ref=payload.get("anchor_ref") if isinstance(payload.get("anchor_ref"), str) else None,
        posture_label=str(payload.get("posture_label", "available-reference")),
        preview=payload.get("preview") if isinstance(payload.get("preview"), str) else None,
    )


def _ensure_boundary_preamble(body: str) -> str:
    preamble = (
        "<!-- generated-project-artifact; not-primary-evidence; "
        "based-on-available-thread-project-context; no-retrieval-integration-or-project-source-injection -->\n\n"
    )
    if body.startswith("<!-- generated-project-artifact"):
        return body
    return preamble + body.strip() + "\n"


def _prepare_storage_root(storage_root: str | Path | None, *, create: bool = True) -> Path:
    root = Path(storage_root) if storage_root is not None else default_storage_root()
    if create:
        (root / REPORTS_DIRECTORY / REPORT_BODY_DIRECTORY).mkdir(parents=True, exist_ok=True)
    return root


def _report_manifest_path(root: Path, report_id: str) -> Path:
    return root / REPORTS_DIRECTORY / f"{_safe_id(report_id)}.json"


def _safe_id(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
        raise ValueError(f"Unsafe report identifier: {identifier!r}")
    return identifier


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest is not a JSON object: {path}")
    return payload


def _write_text(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _bounded(text: str, limit: int) -> str:
    clean = _clean(text)
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"
