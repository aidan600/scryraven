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

DOCUMENT_REVIEW_VERSION = "ag83d-v1"
DOCUMENT_LOCAL_EVIDENCE_LABEL = "document-local-evidence"
DOCUMENT_LOCAL_ONLY_LABEL = "document-local-only"
DOCUMENT_SOURCE_SCOPE = "private-session-document"
FOLLOWUP_RETRIEVAL_MODE = "deterministic-retained-chunk-retrieval"
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
    r"increase|decrease|growth|decline|saves|costs|owner|action|recommend|"
    r"required|requirement|optional|not required|improved|efficacy|is|are)\b",
    re.IGNORECASE,
)
_INFERENCE_CUE_RE = re.compile(r"\b(?:because|therefore|implies|suggests|indicates|likely|may|could)\b", re.IGNORECASE)
_SUPPORT_CUE_RE = re.compile(
    r"\b(?:according to|cites|citation|source|appendix|exhibit|table|figure|data|survey|report|study)\b",
    re.IGNORECASE,
)
_OFFICIAL_CURRENT_CUE_RE = re.compile(
    r"\b(?:current|currently|latest|today|now|official|policy|price|pricing|status|release|announcement)\b",
    re.IGNORECASE,
)
_LEGAL_CUE_RE = re.compile(
    r"\b(?:legal|law|statute|regulation|regulatory|compliance|court|jurisdiction|contract|tax|effective date)\b",
    re.IGNORECASE,
)
_FINANCIAL_CUE_RE = re.compile(
    r"\b(?:price|pricing|revenue|cost|costs|budget|market|rate|rates|fee|fees|forecast|estimate|saves|savings)\b",
    re.IGNORECASE,
)
_MEDICAL_SCIENTIFIC_CUE_RE = re.compile(
    r"\b(?:medical|clinical|health|safety|efficacy|treatment|trial|patient|scientific|causes|study)\b",
    re.IGNORECASE,
)
_ACADEMIC_CUE_RE = re.compile(
    r"\b(?:paper|literature|citation|doi|arxiv|benchmark|methodology|peer-reviewed|study)\b",
    re.IGNORECASE,
)
_TECHNICAL_CURRENT_CUE_RE = re.compile(
    r"\b(?:api|sdk|package|library|browser|model|compatibility|version|changelog|release notes|endpoint)\b",
    re.IGNORECASE,
)
_CORPUS_CUE_RE = re.compile(
    r"\b(?:our files|internal records|customer records|private corpus|personal corpus|uploaded documents|document library)\b",
    re.IGNORECASE,
)
_ACTION_CUE_RE = re.compile(
    r"\b(?:must|shall|required|requires|should|recommend|action item|owner|task|prepare|request|submit)\b",
    re.IGNORECASE,
)
_DEADLINE_CUE_RE = re.compile(
    r"\b(?:by|before|after|due|deadline|effective date|renewal)\s+(?:[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2}|Q[1-4]\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})\b",
    re.IGNORECASE,
)
_RISK_CUE_RE = re.compile(
    r"\b(?:risk|red flag|concern|may increase|could increase|exposure|gap|blocked|failure)\b", re.IGNORECASE
)
_OPINION_CUE_RE = re.compile(r"\b(?:should|recommend|recommendation|best|prefer|opinion|consider)\b", re.IGNORECASE)
_NEGATED_MODAL_RE = re.compile(r"\b(?:will not|must not|shall not|not required|optional)\b", re.IGNORECASE)
_POSITIVE_MODAL_RE = re.compile(r"\b(?:will|must|shall|required)\b", re.IGNORECASE)


BlockKind = Literal["paragraph", "list", "table"]
FindingLabel = Literal[
    "direct-document-statement",
    "document-supported",
    "document-supported-inference",
    "unsupported-by-document",
    "document-internal-possible-tension",
    "external-validation-required",
    "official-current-source-needed",
    "legal-current-official-source-needed",
    "financial-numeric-source-needed",
    "medical-scientific-validation-required",
    "academic-source-needed",
    "product-api-current-technical-source-needed",
    "corpus-validation-required",
    "source-bound-numeric",
    "opinion-recommendation",
    "action-item-obligation",
    "date-deadline-claim",
    "risk-red-flag",
]
ClaimType = Literal[
    "direct-document-statement",
    "document-supported-inference",
    "unsupported-by-document",
    "document-internal-possible-tension",
    "opinion-recommendation",
    "action-item-obligation",
    "date-deadline-claim",
    "risk-red-flag",
]
SourceObligation = Literal[
    "document-local-only",
    "external-validation-required",
    "official-current-source-needed",
    "legal-current-official-source-needed",
    "financial-numeric-source-needed",
    "medical-scientific-validation-required",
    "academic-source-needed",
    "product-api-current-technical-source-needed",
    "corpus-validation-required",
]
EvidenceRole = Literal["document-local", "document-inferred", "unsupported-by-document", "possible-tension"]
ValidationNeed = Literal[
    "none-document-local",
    "external-validation-if-user-needs-truth",
    "official-current-if-validated",
    "legal-current-official-if-validated",
    "financial-numeric-source-if-validated",
    "medical-scientific-validation-if-validated",
    "academic-source-if-validated",
    "product-api-current-technical-source-if-validated",
    "corpus-validation-if-validated",
]
RiskLevel = Literal["low", "medium"]


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
    """Paragraph/excerpt anchor for document-local citations.

    Line references are normalized pasted-text/Markdown lines only; they are not
    page, PDF, DOCX, OCR, or layout coordinates.
    """

    anchor_id: str
    section_id: str
    section_heading: str
    kind: BlockKind
    start_line: int
    end_line: int
    text: str
    extraction_confidence: float

    @property
    def line_reference(self) -> str:
        """Return an honest normalized-line reference, never page/layout precision."""

        if self.start_line == self.end_line:
            return f"line {self.start_line}"
        return f"lines {self.start_line}-{self.end_line}"


@dataclass(frozen=True)
class DocumentChunk:
    """Controller/model-usable document-local evidence packet shape.

    This is retained document context, not live web evidence and not public truth.
    Future Controller/model seams may consume it as private document-local context
    only while preserving the source_scope/evidence labels.
    """

    document_id: str
    document_hash: str
    chunk_id: str
    section_id: str
    section_heading: str
    anchor_ids: tuple[str, ...]
    text: str
    preview: str
    extraction_confidence: float
    evidence_label: str = DOCUMENT_LOCAL_EVIDENCE_LABEL
    locality_label: str = DOCUMENT_LOCAL_ONLY_LABEL
    source_scope: str = DOCUMENT_SOURCE_SCOPE
    retrieval_mode: str = FOLLOWUP_RETRIEVAL_MODE


@dataclass(frozen=True)
class ReviewFinding:
    """Deterministic claim/review finding tied to document anchors.

    The added AG-83D fields are local classifications only. They describe how the
    document appears to state a claim and what source class would be needed if a
    user later wanted truth validation; they do not validate outside-world truth.
    """

    finding_id: str
    text: str
    labels: tuple[FindingLabel, ...]
    anchor_ids: tuple[str, ...]
    extraction_confidence: float
    note: str
    claim_type: ClaimType = "direct-document-statement"
    source_obligation: SourceObligation = "document-local-only"
    evidence_role: EvidenceRole = "document-local"
    validation_need: ValidationNeed = "none-document-local"
    risk_level: RiskLevel = "low"


@dataclass(frozen=True)
class FollowupHit:
    """Deterministic follow-up retrieval result."""

    chunk_id: str
    section_heading: str
    anchor_ids: tuple[str, ...]
    snippet: str
    score: float
    labels: tuple[str, ...] = (DOCUMENT_LOCAL_EVIDENCE_LABEL, DOCUMENT_LOCAL_ONLY_LABEL, DOCUMENT_SOURCE_SCOPE)
    retrieval_mode: str = FOLLOWUP_RETRIEVAL_MODE


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
    chunks = build_document_chunks(metadata.document_id, metadata.document_hash, anchors)
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
    sections: list[DocumentSection] = [DocumentSection("s01", "Document", 0, 1, "s01")]
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
    document_hash: str,
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
                document_hash=document_hash,
                chunk_id=f"{document_id}-c{len(chunks) + 1:03d}",
                section_id=first.section_id,
                section_heading=first.section_heading,
                anchor_ids=tuple(anchor.anchor_id for anchor in pending),
                text=text,
                preview=_preview(text),
                extraction_confidence=round(sum(anchor.extraction_confidence for anchor in pending) / len(pending), 3),
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

    anchor_list = tuple(anchors)
    findings: list[ReviewFinding] = []
    seen: set[str] = set()
    for anchor in anchor_list:
        for sentence in _candidate_sentences(anchor.text):
            if len(findings) >= limit:
                return tuple(findings)
            key = sentence.casefold()
            if key in seen or not _looks_like_claim(sentence):
                continue
            seen.add(key)
            finding = _finding_for_sentence(sentence, anchor, f"f{len(findings) + 1:03d}")
            findings.append(finding)
    for finding in _possible_tension_findings(anchor_list, findings, limit=limit):
        if len(findings) >= limit:
            break
        findings.append(finding)
    return tuple(findings)


def retrieve_document_followup(
    context: DocumentReviewContext,
    query: str,
    *,
    limit: int = 5,
) -> tuple[FollowupHit, ...]:
    """Return deterministic retained-chunk hits for a same-session follow-up query.

    The search surface is strictly ``context.chunks``. This helper does not answer
    natural-language questions, validate claims externally, or consult persisted
    document libraries/corpora.
    """

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
        "Follow-up is deterministic same-session retrieval: ask for retained headings "
        "or keyword tokens to retrieve document-local chunks, labels, and anchors. "
        "It is not model-mediated natural-language Q&A or public validation."
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
        f"- Evidence label: `{DOCUMENT_LOCAL_EVIDENCE_LABEL}`",
        f"- Source scope: `{DOCUMENT_SOURCE_SCOPE}`",
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
                f"  - Claim type: `{finding.claim_type}`",
                f"  - Source obligation: `{finding.source_obligation}`",
                f"  - Evidence role: `{finding.evidence_role}`",
                f"  - Validation need: `{finding.validation_need}`",
                f"  - Risk level: `{finding.risk_level}`",
                f"  - Note: {finding.note}",
            ]
        )
    lines.extend(
        [
            "",
            "## Follow-up boundary",
            followup_hint,
            "",
            "This export contains no PDF/page precision, no public validation, and no persistent document-library state.",
            "",
        ]
    )
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
    return [piece.strip(" -•\t") for piece in pieces if len(piece.strip()) >= 24]


def _looks_like_claim(sentence: str) -> bool:
    return bool(_CLAIM_CUE_RE.search(sentence) or _NUMERIC_RE.search(sentence) or _ACTION_CUE_RE.search(sentence))


def _finding_for_sentence(sentence: str, anchor: DocumentAnchor, finding_id: str) -> ReviewFinding:
    labels = _labels_for_claim(sentence)
    claim_type = _claim_type_for_labels(labels)
    source_obligation = _source_obligation_for_labels(labels)
    evidence_role = _evidence_role_for_labels(labels)
    validation_need = _validation_need_for_obligation(source_obligation)
    return ReviewFinding(
        finding_id=finding_id,
        text=sentence,
        labels=labels,
        anchor_ids=(anchor.anchor_id,),
        extraction_confidence=0.72 if anchor.kind == "paragraph" else 0.66,
        note=_note_for_finding(labels, source_obligation, evidence_role),
        claim_type=claim_type,
        source_obligation=source_obligation,
        evidence_role=evidence_role,
        validation_need=validation_need,
        risk_level="medium" if "risk-red-flag" in labels or source_obligation != "document-local-only" else "low",
    )


def _labels_for_claim(sentence: str) -> tuple[FindingLabel, ...]:
    labels: list[FindingLabel] = ["direct-document-statement"]
    support_detected = bool(_SUPPORT_CUE_RE.search(sentence))
    external_required = False
    if _NUMERIC_RE.search(sentence):
        labels.extend(["source-bound-numeric", "financial-numeric-source-needed"])
        external_required = True
    if _OFFICIAL_CURRENT_CUE_RE.search(sentence):
        labels.append("official-current-source-needed")
        external_required = True
    if _LEGAL_CUE_RE.search(sentence):
        labels.append("legal-current-official-source-needed")
        external_required = True
    if _FINANCIAL_CUE_RE.search(sentence):
        labels.append("financial-numeric-source-needed")
        external_required = True
    if _MEDICAL_SCIENTIFIC_CUE_RE.search(sentence):
        labels.append("medical-scientific-validation-required")
        external_required = True
    if _ACADEMIC_CUE_RE.search(sentence):
        labels.append("academic-source-needed")
        external_required = True
    if _TECHNICAL_CURRENT_CUE_RE.search(sentence):
        labels.append("product-api-current-technical-source-needed")
        external_required = True
    if _CORPUS_CUE_RE.search(sentence):
        labels.append("corpus-validation-required")
    if external_required:
        labels.append("external-validation-required")
    if _INFERENCE_CUE_RE.search(sentence):
        labels.append("document-supported-inference")
    if _OPINION_CUE_RE.search(sentence):
        labels.append("opinion-recommendation")
    if _ACTION_CUE_RE.search(sentence):
        labels.append("action-item-obligation")
    if _DEADLINE_CUE_RE.search(sentence):
        labels.append("date-deadline-claim")
    if _RISK_CUE_RE.search(sentence):
        labels.append("risk-red-flag")
    if not support_detected and external_required:
        labels.append("unsupported-by-document")
    if len(labels) == 1:
        labels.append("document-supported")
    return tuple(dict.fromkeys(labels))


def _claim_type_for_labels(labels: tuple[FindingLabel, ...]) -> ClaimType:
    ordered: tuple[ClaimType, ...] = (
        "document-internal-possible-tension",
        "risk-red-flag",
        "action-item-obligation",
        "date-deadline-claim",
        "opinion-recommendation",
        "unsupported-by-document",
        "document-supported-inference",
    )
    label_set = set(labels)
    for claim_type in ordered:
        if claim_type in label_set:
            return claim_type
    return "direct-document-statement"


def _source_obligation_for_labels(labels: tuple[FindingLabel, ...]) -> SourceObligation:
    priorities: tuple[SourceObligation, ...] = (
        "legal-current-official-source-needed",
        "medical-scientific-validation-required",
        "product-api-current-technical-source-needed",
        "official-current-source-needed",
        "academic-source-needed",
        "corpus-validation-required",
        "financial-numeric-source-needed",
        "external-validation-required",
    )
    label_set = set(labels)
    for obligation in priorities:
        if obligation in label_set:
            return obligation
    return "document-local-only"


def _evidence_role_for_labels(labels: tuple[FindingLabel, ...]) -> EvidenceRole:
    if "document-internal-possible-tension" in labels:
        return "possible-tension"
    if "unsupported-by-document" in labels:
        return "unsupported-by-document"
    if "document-supported-inference" in labels:
        return "document-inferred"
    return "document-local"


def _validation_need_for_obligation(source_obligation: SourceObligation) -> ValidationNeed:
    return {
        "document-local-only": "none-document-local",
        "external-validation-required": "external-validation-if-user-needs-truth",
        "official-current-source-needed": "official-current-if-validated",
        "legal-current-official-source-needed": "legal-current-official-if-validated",
        "financial-numeric-source-needed": "financial-numeric-source-if-validated",
        "medical-scientific-validation-required": "medical-scientific-validation-if-validated",
        "academic-source-needed": "academic-source-if-validated",
        "product-api-current-technical-source-needed": "product-api-current-technical-source-if-validated",
        "corpus-validation-required": "corpus-validation-if-validated",
    }[source_obligation]


def _note_for_finding(
    labels: tuple[FindingLabel, ...], source_obligation: SourceObligation, evidence_role: EvidenceRole
) -> str:
    if evidence_role == "possible-tension":
        return (
            "Possible document-internal tension detected deterministically; no winner or truth resolution was chosen."
        )
    if source_obligation != "document-local-only":
        support_phrase = (
            "The document contains a local support cue, but that cue was not externally checked."
            if "unsupported-by-document" not in labels
            else "No explicit local support cue was detected near this claim."
        )
        return f"Document-local extraction only; {source_obligation} would be needed if validating outside-world truth. {support_phrase}"
    if evidence_role == "document-inferred":
        return "Inference cue detected; preserve the document-local inference boundary."
    if "action-item-obligation" in labels:
        return "Document-local action or obligation cue detected; no task-management workflow was created."
    return "Direct deterministic claim candidate from the provided document."


def _possible_tension_findings(
    anchors: tuple[DocumentAnchor, ...], findings: list[ReviewFinding], *, limit: int
) -> tuple[ReviewFinding, ...]:
    candidates: list[tuple[str, str, str, tuple[str, ...]]] = []
    for anchor in anchors:
        for sentence in _candidate_sentences(anchor.text):
            numbers = tuple(_NUMERIC_RE.findall(sentence))
            topic = _tension_topic(sentence)
            if numbers and topic:
                candidates.append((topic, sentence, "|".join(numbers), (anchor.anchor_id,)))
    tensions: list[ReviewFinding] = []
    for idx, left in enumerate(candidates):
        for right in candidates[idx + 1 :]:
            if left[0] == right[0] and left[2] != right[2]:
                anchor_ids = tuple(dict.fromkeys(left[3] + right[3]))
                tensions.append(
                    _tension_finding(
                        finding_id=f"f{len(findings) + len(tensions) + 1:03d}",
                        text=f"Possible tension: {left[1]} / {right[1]}",
                        anchor_ids=anchor_ids,
                    )
                )
                return tuple(tensions[: max(0, limit - len(findings))])
    modal_sentences = [
        (sentence, anchor.anchor_id)
        for anchor in anchors
        for sentence in _candidate_sentences(anchor.text)
        if _POSITIVE_MODAL_RE.search(sentence) or _NEGATED_MODAL_RE.search(sentence)
    ]
    for idx, (left_sentence, left_anchor) in enumerate(modal_sentences):
        left_topic = _tension_topic(left_sentence)
        if not left_topic:
            continue
        for right_sentence, right_anchor in modal_sentences[idx + 1 :]:
            if left_topic != _tension_topic(right_sentence):
                continue
            if (_POSITIVE_MODAL_RE.search(left_sentence) and _NEGATED_MODAL_RE.search(right_sentence)) or (
                _NEGATED_MODAL_RE.search(left_sentence) and _POSITIVE_MODAL_RE.search(right_sentence)
            ):
                return (
                    _tension_finding(
                        finding_id=f"f{len(findings) + 1:03d}",
                        text=f"Possible tension: {left_sentence} / {right_sentence}",
                        anchor_ids=tuple(dict.fromkeys((left_anchor, right_anchor))),
                    ),
                )
    return tuple(tensions)


def _tension_finding(finding_id: str, text: str, anchor_ids: tuple[str, ...]) -> ReviewFinding:
    labels: tuple[FindingLabel, ...] = ("document-internal-possible-tension", "source-bound-numeric")
    return ReviewFinding(
        finding_id=finding_id,
        text=text,
        labels=labels,
        anchor_ids=anchor_ids,
        extraction_confidence=0.58,
        note=_note_for_finding(labels, "document-local-only", "possible-tension"),
        claim_type="document-internal-possible-tension",
        source_obligation="document-local-only",
        evidence_role="possible-tension",
        validation_need="none-document-local",
        risk_level="medium",
    )


def _tension_topic(sentence: str) -> str:
    tokens = [token.casefold() for token in _WORD_RE.findall(_NUMERIC_RE.sub("", sentence))]
    stop = {"the", "and", "for", "with", "from", "that", "this", "will", "must", "shall", "not", "required"}
    useful = [token for token in tokens if len(token) > 3 and token not in stop]
    return " ".join(useful[:3])


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
    return (
        any(_SECTION_HEADING_RE.match(line) or _TABLE_RE.match(line) for line in normalized_text.split("\n"))
        or "```" in normalized_text
    )


def _keywords(text: str) -> set[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "into",
        "only",
        "about",
        "what",
        "where",
        "when",
        "does",
    }
    return {
        token.casefold() for token in _WORD_RE.findall(text or "") if len(token) > 2 and token.casefold() not in stop
    }
