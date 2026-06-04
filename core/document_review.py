"""Deterministic document-local review helpers for pasted text and Markdown.

AG-83B deliberately keeps this module pure and local-only: it parses user-provided
text into a retained in-memory context, derives simple document-local findings,
supports deterministic follow-up retrieval, and renders a Markdown export. It does
not call providers, search, retrieval, persistence, caches, prompts, or the main
pipeline/orchestrator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from typing import Iterable, Literal

DOCUMENT_REVIEW_VERSION = "ag83b-v1"
DOCUMENT_LOCAL_EVIDENCE_LABEL = "document-local-evidence"
PRIVACY_MARKER = "session-local-private-document"
BOUNDARY_NOTICE = (
    "Based only on the provided document. No public web validation, provider/model "
    "call, search call, persistent corpus, or document library storage is performed."
)
PRIVACY_WARNING = (
    "Private/session-local: pasted document text is retained only in the current "
    "in-memory document-review session state by the UI. Do not treat document claims "
    "as public-truth validation."
)

_SECTION_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+?)\s*$")
_TABLE_RE = re.compile(r"^\s*\|.+\|\s*$")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_WORD_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")
_NUMERIC_RE = re.compile(r"(?:\$|€|£)?\b\d[\d,]*(?:\.\d+)?\b|\b\d+(?:\.\d+)?%")
_EXTERNAL_CUE_RE = re.compile(
    r"\b(?:current|currently|latest|today|now|recent|market|price|legal|law|"
    r"regulation|compliance|deadline|effective date|tax|medical|clinical|official|"
    r"public|published|validated|according to|reported by)\b",
    re.IGNORECASE,
)
_CLAIM_CUE_RE = re.compile(
    r"\b(?:will|would|must|should|shall|can|could|because|therefore|conclude|"
    r"shows|proves|indicates|requires|expects|forecast|target|deadline|risk|"
    r"increase|decrease|growth|decline|saves|costs)\b",
    re.IGNORECASE,
)
_INFERENCE_CUE_RE = re.compile(r"\b(?:because|therefore|implies|suggests|indicates|likely)\b", re.IGNORECASE)
_SUPPORT_CUE_RE = re.compile(r"\b(?:according to|cites|citation|source|appendix|exhibit|table|figure|data)\b", re.IGNORECASE)

BlockKind = Literal["paragraph", "list", "table"]
FindingLabel = Literal[
    "document-supported",
    "document-supported-inference",
    "unsupported-by-document",
    "external-validation-required",
    "source-bound-numeric",
]


@dataclass(frozen=True)
class DocumentMetadata:
    """User-visible document metadata retained with the session-local context."""

    title: str
    input_format: Literal["pasted_text", "markdown"]
    document_id: str
    document_hash: str
    version: str = DOCUMENT_REVIEW_VERSION
    created_at: str = ""
    privacy_marker: str = PRIVACY_MARKER


@dataclass(frozen=True)
class DocumentSection:
    """A deterministic Markdown/text section."""

    section_id: str
    heading: str
    level: int
    start_line: int
    anchor: str


@dataclass(frozen=True)
class DocumentAnchor:
    """Paragraph/excerpt anchor for document-local citations."""

    anchor_id: str
    section_id: str
    section_heading: str
    kind: BlockKind
    start_line: int
    end_line: int
    text: str
    extraction_confidence: float


@dataclass(frozen=True)
class DocumentChunk:
    """Controller/model-usable document-local evidence packet shape."""

    document_id: str
    chunk_id: str
    section_id: str
    section_heading: str
    anchor_ids: tuple[str, ...]
    text: str
    preview: str
    extraction_confidence: float
    evidence_label: str = DOCUMENT_LOCAL_EVIDENCE_LABEL


@dataclass(frozen=True)
class ReviewFinding:
    """Deterministic claim/review finding tied to document anchors."""

    finding_id: str
    text: str
    labels: tuple[FindingLabel, ...]
    anchor_ids: tuple[str, ...]
    extraction_confidence: float
    note: str


@dataclass(frozen=True)
class FollowupHit:
    """Deterministic follow-up retrieval result."""

    chunk_id: str
    section_heading: str
    anchor_ids: tuple[str, ...]
    snippet: str
    score: float
    labels: tuple[str, ...] = (DOCUMENT_LOCAL_EVIDENCE_LABEL, "document-local-only")


@dataclass(frozen=True)
class DocumentReviewArtifact:
    """Exportable deterministic document-local review."""

    boundary_notice: str
    summary: str
    findings: tuple[ReviewFinding, ...]
    followup_hint: str
    markdown: str


@dataclass(frozen=True)
class DocumentReviewContext:
    """Retained session-local document review state.

    The normalized text is intentionally retained here for same-session follow-up,
    but the module never persists it or treats it as a personal corpus/library.
    """

    metadata: DocumentMetadata
    normalized_text: str
    sections: tuple[DocumentSection, ...]
    anchors: tuple[DocumentAnchor, ...]
    chunks: tuple[DocumentChunk, ...]
    findings: tuple[ReviewFinding, ...]
    export_markdown: str
    boundary_notice: str = BOUNDARY_NOTICE
    privacy_warning: str = PRIVACY_WARNING

    def snapshot(self) -> "DocumentReviewContext":
        """Return a structurally independent immutable snapshot for session state."""

        return replace(
            self,
            metadata=replace(self.metadata),
            sections=tuple(replace(item) for item in self.sections),
            anchors=tuple(replace(item) for item in self.anchors),
            chunks=tuple(replace(item) for item in self.chunks),
            findings=tuple(replace(item) for item in self.findings),
        )


def build_document_review_context(
    raw_text: str,
    *,
    title: str | None = None,
    input_format: Literal["pasted_text", "markdown"] | None = None,
    created_at: datetime | None = None,
) -> DocumentReviewContext:
    """Build a complete deterministic document-review context from pasted text/Markdown."""

    normalized = normalize_document_text(raw_text)
    if not normalized:
        raise ValueError("Document review requires non-empty pasted text or Markdown.")
    detected_format = input_format or ("markdown" if _looks_like_markdown(normalized) else "pasted_text")
    digest = sha256(normalized.encode("utf-8")).hexdigest()
    document_id = f"doc-{digest[:16]}"
    timestamp = (created_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    metadata = DocumentMetadata(
        title=_clean_title(title) or _derive_title(normalized),
        input_format=detected_format,
        document_id=document_id,
        document_hash=digest,
        created_at=timestamp,
    )
    sections, anchors = parse_document_blocks(normalized)
    chunks = build_document_chunks(metadata.document_id, anchors)
    findings = extract_review_findings(anchors)
    artifact = build_review_artifact(metadata, chunks, findings)
    return DocumentReviewContext(
        metadata=metadata,
        normalized_text=normalized,
        sections=sections,
        anchors=anchors,
        chunks=chunks,
        findings=findings,
        export_markdown=artifact.markdown,
    )


def normalize_document_text(raw_text: str) -> str:
    """Normalize pasted text deterministically without semantic rewriting."""

    text = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    normalized_lines: list[str] = []
    blank_seen = False
    for line in lines:
        if line.strip():
            normalized_lines.append(line)
            blank_seen = False
        elif not blank_seen:
            normalized_lines.append("")
            blank_seen = True
    return "\n".join(normalized_lines)


def parse_document_blocks(normalized_text: str) -> tuple[tuple[DocumentSection, ...], tuple[DocumentAnchor, ...]]:
    """Parse headings, paragraphs, lists, and simple Markdown tables into stable anchors."""

    lines = normalized_text.split("\n")
    sections: list[DocumentSection] = [
        DocumentSection("s01", "Document", 0, 1, "s01")
    ]
    current_section = sections[0]
    anchors: list[DocumentAnchor] = []
    block_lines: list[tuple[int, str]] = []
    block_kind: BlockKind | None = None

    def flush() -> None:
        nonlocal block_lines, block_kind
        if not block_lines:
            return
        text = _normalize_block_text(block_lines, block_kind or "paragraph")
        if text:
            para_num = 1 + sum(1 for anchor in anchors if anchor.section_id == current_section.section_id)
            anchor_id = f"{current_section.anchor}-p{para_num:03d}"
            confidence = _confidence_for_kind(block_kind or "paragraph")
            anchors.append(
                DocumentAnchor(
                    anchor_id=anchor_id,
                    section_id=current_section.section_id,
                    section_heading=current_section.heading,
                    kind=block_kind or "paragraph",
                    start_line=block_lines[0][0],
                    end_line=block_lines[-1][0],
                    text=text,
                    extraction_confidence=confidence,
                )
            )
        block_lines = []
        block_kind = None

    for idx, line in enumerate(lines, start=1):
        heading_match = _SECTION_HEADING_RE.match(line)
        if heading_match:
            flush()
            section_id = f"s{len(sections) + 1:02d}"
            heading = heading_match.group(2).strip().rstrip("# ").strip() or f"Section {len(sections) + 1}"
            current_section = DocumentSection(
                section_id=section_id,
                heading=heading,
                level=len(heading_match.group(1)),
                start_line=idx,
                anchor=section_id,
            )
            sections.append(current_section)
            continue
        if not line.strip():
            flush()
            continue
        kind = _classify_block_line(line)
        if block_kind and kind != block_kind:
            flush()
        block_kind = kind
        block_lines.append((idx, line))
    flush()

    return tuple(sections), tuple(anchors)


def build_document_chunks(
    document_id: str,
    anchors: Iterable[DocumentAnchor],
    *,
    max_chars: int = 900,
) -> tuple[DocumentChunk, ...]:
    """Build deterministic document-local evidence chunks from anchors."""

    chunks: list[DocumentChunk] = []
    pending: list[DocumentAnchor] = []
    pending_len = 0
    pending_section: str | None = None

    def flush() -> None:
        nonlocal pending, pending_len, pending_section
        if not pending:
            return
        text = "\n\n".join(anchor.text for anchor in pending)
        first = pending[0]
        chunks.append(
            DocumentChunk(
                document_id=document_id,
                chunk_id=f"{document_id}-c{len(chunks) + 1:03d}",
                section_id=first.section_id,
                section_heading=first.section_heading,
                anchor_ids=tuple(anchor.anchor_id for anchor in pending),
                text=text,
                preview=_preview(text),
                extraction_confidence=round(
                    sum(anchor.extraction_confidence for anchor in pending) / len(pending), 3
                ),
            )
        )
        pending = []
        pending_len = 0
        pending_section = None

    for anchor in anchors:
        anchor_len = len(anchor.text)
        if pending and (anchor.section_id != pending_section or pending_len + anchor_len > max_chars):
            flush()
        pending.append(anchor)
        pending_len += anchor_len
        pending_section = anchor.section_id
    flush()
    return tuple(chunks)


def extract_review_findings(anchors: Iterable[DocumentAnchor], *, limit: int = 12) -> tuple[ReviewFinding, ...]:
    """Extract modest deterministic claim candidates and labels."""

    findings: list[ReviewFinding] = []
    seen: set[str] = set()
    for anchor in anchors:
        for sentence in _candidate_sentences(anchor.text):
            if len(findings) >= limit:
                return tuple(findings)
            key = sentence.casefold()
            if key in seen or not _looks_like_claim(sentence):
                continue
            seen.add(key)
            labels = _labels_for_claim(sentence)
            findings.append(
                ReviewFinding(
                    finding_id=f"f{len(findings) + 1:03d}",
                    text=sentence,
                    labels=labels,
                    anchor_ids=(anchor.anchor_id,),
                    extraction_confidence=0.72 if anchor.kind == "paragraph" else 0.66,
                    note=_note_for_labels(labels),
                )
            )
    return tuple(findings)


def retrieve_document_followup(
    context: DocumentReviewContext,
    query: str,
    *,
    limit: int = 5,
) -> tuple[FollowupHit, ...]:
    """Return deterministic document-local chunks relevant to a follow-up query."""

    query_terms = _keywords(query)
    if not query_terms:
        return tuple()
    hits: list[FollowupHit] = []
    for chunk in context.chunks:
        text_terms = _keywords(f"{chunk.section_heading} {chunk.text}")
        overlap = query_terms & text_terms
        if not overlap:
            continue
        section_bonus = len(query_terms & _keywords(chunk.section_heading)) * 0.5
        score = len(overlap) + section_bonus + min(len(chunk.anchor_ids), 3) * 0.05
        hits.append(
            FollowupHit(
                chunk_id=chunk.chunk_id,
                section_heading=chunk.section_heading,
                anchor_ids=chunk.anchor_ids,
                snippet=chunk.preview,
                score=round(score, 3),
            )
        )
    hits.sort(key=lambda item: (-item.score, item.chunk_id))
    return tuple(hits[:limit])


def build_review_artifact(
    metadata: DocumentMetadata,
    chunks: Iterable[DocumentChunk],
    findings: Iterable[ReviewFinding],
) -> DocumentReviewArtifact:
    """Build the exportable deterministic review artifact."""

    chunk_list = tuple(chunks)
    finding_list = tuple(findings)
    summary = _summary_from_chunks(chunk_list)
    followup_hint = (
        "Follow-up in AG-83B is deterministic retrieval: ask for a heading, keyword, "
        "or concept to retrieve retained document-local chunks and anchors."
    )
    markdown = export_review_markdown(metadata, summary, finding_list, followup_hint)
    return DocumentReviewArtifact(
        boundary_notice=BOUNDARY_NOTICE,
        summary=summary,
        findings=finding_list,
        followup_hint=followup_hint,
        markdown=markdown,
    )


def export_review_markdown(
    metadata: DocumentMetadata,
    summary: str,
    findings: Iterable[ReviewFinding],
    followup_hint: str,
) -> str:
    """Render a Markdown document-review export preserving labels and anchors."""

    lines = [
        f"# Document Review: {metadata.title}",
        "",
        f"- Document ID: `{metadata.document_id}`",
        f"- Document hash: `{metadata.document_hash}`",
        f"- Version: `{metadata.version}`",
        f"- Input format: `{metadata.input_format}`",
        f"- Privacy marker: `{metadata.privacy_marker}`",
        "",
        "## Boundary",
        BOUNDARY_NOTICE,
        "",
        "## Privacy warning",
        PRIVACY_WARNING,
        "",
        "## Document-local summary",
        summary,
        "",
        "## Claim candidates and review labels",
    ]
    finding_list = tuple(findings)
    if not finding_list:
        lines.append("No deterministic claim candidates were detected in this short document.")
    for finding in finding_list:
        labels = ", ".join(finding.labels)
        anchors = ", ".join(finding.anchor_ids)
        lines.extend(
            [
                f"- **{finding.finding_id}** [{labels}] anchors: `{anchors}`",
                f"  - Claim candidate: {finding.text}",
                f"  - Note: {finding.note}",
            ]
        )
    lines.extend(["", "## Follow-up", followup_hint, ""])
    return "\n".join(lines)


def _classify_block_line(line: str) -> BlockKind:
    if _TABLE_RE.match(line):
        return "table"
    if _LIST_RE.match(line):
        return "list"
    return "paragraph"


def _normalize_block_text(block_lines: list[tuple[int, str]], kind: BlockKind) -> str:
    raw_lines = [line.strip() for _, line in block_lines]
    if kind == "list":
        return "\n".join(raw_lines)
    if kind == "table":
        return "\n".join(raw_lines)
    return " ".join(line for line in raw_lines if line)


def _confidence_for_kind(kind: BlockKind) -> float:
    if kind == "table":
        return 0.62
    if kind == "list":
        return 0.74
    return 0.82


def _candidate_sentences(text: str) -> list[str]:
    pieces: list[str] = []
    for line in text.split("\n"):
        clean = _LIST_RE.sub(r"\1", line).strip()
        pieces.extend(_SENTENCE_RE.split(clean))
    return [piece.strip(" -•\t") for piece in pieces if len(piece.strip()) >= 32]


def _looks_like_claim(sentence: str) -> bool:
    return bool(_CLAIM_CUE_RE.search(sentence) or _NUMERIC_RE.search(sentence))


def _labels_for_claim(sentence: str) -> tuple[FindingLabel, ...]:
    labels: list[FindingLabel] = []
    if _NUMERIC_RE.search(sentence):
        labels.append("source-bound-numeric")
    if _EXTERNAL_CUE_RE.search(sentence):
        labels.append("external-validation-required")
    if _INFERENCE_CUE_RE.search(sentence):
        labels.append("document-supported-inference")
    if not _SUPPORT_CUE_RE.search(sentence) and ("external-validation-required" in labels or "source-bound-numeric" in labels):
        labels.append("unsupported-by-document")
    if not labels:
        labels.append("document-supported")
    return tuple(dict.fromkeys(labels))


def _note_for_labels(labels: tuple[FindingLabel, ...]) -> str:
    if "external-validation-required" in labels:
        return "Document-local extraction only; outside-world/current/legal/numeric truth was not validated."
    if "unsupported-by-document" in labels:
        return "The document states this candidate, but AG-83B found no explicit local support cue nearby."
    if "document-supported-inference" in labels:
        return "Inference cue detected; preserve the document-local inference boundary."
    if "source-bound-numeric" in labels:
        return "Numeric statement should remain tied to its document anchor."
    return "Direct deterministic claim candidate from the provided document."


def _summary_from_chunks(chunks: tuple[DocumentChunk, ...]) -> str:
    if not chunks:
        return "No document-local chunks were generated."
    preview = " ".join(chunk.preview for chunk in chunks[:3])
    if len(preview) > 700:
        preview = preview[:697].rstrip() + "..."
    return f"Document-local summary from retained chunks: {preview}"


def _preview(text: str, *, limit: int = 280) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 3].rstrip() + "..."


def _derive_title(normalized_text: str) -> str:
    first_line = next((line.strip("# ") for line in normalized_text.split("\n") if line.strip()), "Document")
    return _clean_title(first_line)[:80] or "Document"


def _clean_title(title: str | None) -> str:
    return " ".join(str(title or "").strip().split())


def _looks_like_markdown(normalized_text: str) -> bool:
    return any(_SECTION_HEADING_RE.match(line) or _TABLE_RE.match(line) for line in normalized_text.split("\n")) or "```" in normalized_text


def _keywords(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "from", "that", "this", "into", "only", "about", "what", "where", "when", "does"}
    return {token.casefold() for token in _WORD_RE.findall(text or "") if len(token) > 2 and token.casefold() not in stop}
