"""Completed answers and exact citation custody, without semantic state."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256

from markdown_it import MarkdownIt
from markdown_it.token import Token

from scryraven.documents import SessionDocument, document_text_view
from scryraven.errors import RunError
from scryraven.presentation import Citation, CitationUse
from scryraven.sources import Evidence, SupportRegion, exact_view, locate_unique_passage


@dataclass(frozen=True)
class CompletedAnswer:
    """Public result of a fresh source-first answer pass; notes are not Evidence."""

    answer: str
    posture: str
    stop_reason: str
    evidence: tuple[Evidence, ...]
    trace: tuple[dict, ...]
    selected_evidence: tuple[Evidence, ...]
    citations: tuple[Citation, ...]
    citation_uses: tuple[CitationUse, ...]
    image_ids: tuple[str, ...] = ()


def _passage_proposals(rows: object) -> dict[tuple[str, int], str | None]:
    proposals: dict[tuple[str, int], str | None] = {}
    for row in rows if isinstance(rows, list) else ():
        if not isinstance(row, dict):
            continue
        ref, occurrence, text = row.get("ref"), row.get("occurrence"), row.get("text")
        if (not isinstance(ref, str) or type(occurrence) is not int or occurrence < 1
                or not isinstance(text, str) or not 1 <= len(text) <= 1200 or not text.strip()):
            continue
        key = (ref, occurrence)
        if proposals.setdefault(key, text) != text:
            proposals[key] = None
    return proposals


def _saved_passage(material: Evidence | None, text: str | None) -> tuple[SupportRegion, ...]:
    if material is None or text is None:
        return ()
    try:
        start, end = locate_unique_passage(material.content, text)
        material_hash = sha256(material.content.encode("utf-8")).hexdigest()
        passage_hash = sha256(material.content[start:end].encode("utf-8")).hexdigest()
    except ValueError:
        return ()
    return (SupportRegion(material.id, start, end, material_hash, passage_hash),)


def _line_starts(text: str) -> list[int]:
    return [0, *(line.end() for line in re.finditer(r"\r\n?|\n", text)), len(text)]


def _has_closing_fence(block: Token) -> bool:
    # MarkdownIt includes the closer in the token's line range, but leaves it
    # out of the code content. An implicitly ended fence adds only its opener.
    assert block.map is not None
    start, end = block.map
    code_lines = block.content.count("\n") + int(bool(block.content) and not block.content.endswith("\n"))
    return end - start == code_lines + 2


def _separate_fence_citations(draft: str, token: re.Pattern[str], markdown: MarkdownIt) -> str:
    """Move citation-only suffixes outside closing fences."""
    suffix = re.compile(
        rf" {{0,3}}(?P<fence>`{{3,}}|~{{3,}})[ \t]*"
        rf"(?P<cites>{token.pattern}(?:[ \t]*{token.pattern})*)[ \t]*"
    )
    while True:
        starts = _line_starts(draft)
        normalized = draft
        for block in markdown.parse(draft):
            if block.type != "fence" or not block.map or _has_closing_fence(block):
                continue
            start, end = block.map
            for line in range(start + 1, end):
                raw = draft[starts[line]:starts[line + 1]]
                content = raw.rstrip("\r\n")
                match = suffix.fullmatch(content)
                if match is None or not match["fence"].startswith(block.markup):
                    continue
                eol = raw[len(content):]
                preceding = draft[starts[line] - 2:starts[line]]
                separator = eol or ("\r\n" if preceding == "\r\n" else preceding[-1])
                tail = draft[starts[line + 1]:]
                after = eol
                if tail and not re.match(r"[ \t]*(?:\r\n?|\n)", tail):
                    after += separator
                indent = content[:match.start("fence")]
                proposed = (draft[:starts[line] + match.end("fence")] + separator * 2
                            + indent + match["cites"] + after + tail)
                if any(candidate.type == "fence" and candidate.map == [start, line + 1]
                       and _has_closing_fence(candidate) for candidate in markdown.parse(proposed)):
                    normalized = proposed
                    break
            if normalized != draft:
                break
        if normalized == draft:
            return draft
        draft = normalized


def resolve_citations(
    draft: str, selected: list[Evidence] | tuple[Evidence, ...],
    acquisitions: list[Evidence] | tuple[Evidence, ...], trace: list[dict], *,
    documents: tuple[SessionDocument, ...] = (),
    require_citation: bool = True,
    descriptions: object = None,
    passages: object = None,
) -> tuple[str, tuple[Citation, ...], tuple[CitationUse, ...]]:
    """Resolve only aliases for actual supplied material, grouping by source.

    Exact material IDs and a selected group's canonical source ID are accepted.
    A source alias grants access only to the supplied packet, never to unseen
    retained versions or the unsupplied remainder of a full parent.
    """
    acquired = {item.id: item for item in acquisitions}
    stored_documents = {item.document_id: item for item in documents}
    aliases: dict[str, str] = {}
    materials: dict[str, list[Evidence]] = {}
    for item in selected:
        try:
            if item.source_kind == "user_document":
                original = document_text_view(stored_documents[item.document_id], item.start_char, item.end_char)
                if original != item or item.source_id != item.document_id:
                    raise ValueError("invalid_document_view")
            else:
                original = (exact_view(acquired[item.parent_id], item.start_char, item.end_char)
                            if item.acquisition == "targeted_view" else acquired[item.id])
                source = acquired[item.source_id]
                if original != item or source.id != source.source_id or source.url != item.url:
                    raise ValueError("invalid_web_view")
        except (KeyError, TypeError, ValueError):
            raise RunError("citations", "invalid_selected_material", trace) from None
        if item.id in aliases:
            raise RunError("citations", "duplicate_selected_material", trace)
        aliases[item.id] = item.source_id
        group = materials.setdefault(item.source_id, [])
        group.append(item)
    for source_id in materials:
        aliases[source_id] = source_id

    used: list[str] = []
    uses: list[CitationUse] = []
    selected_by_id = {item.id: item for item in selected}
    proposals = _passage_proposals(passages)
    occurrences: Counter[str] = Counter()
    offset = 0
    alias = r"(?:E|D)[0-9]+(?:@[0-9]+:[0-9]+)?"
    alias_list = rf"\s*{alias}(?:\s*,\s*{alias})*\s*"
    token = re.compile(rf"\[(?:\[{alias_list}\](?:\s*,\s*\[{alias_list}\])*|{alias_list})\]")

    def reject(code: str, pattern: str, match: re.Match | None = None) -> None:
        trace.append({
            "stage": "citations", "action": "rejected", "code": code,
            "pattern": pattern, "offset": match.start() if match else None,
            "evidence_ids": re.findall(alias, match.group())[:8] if match else [],
            "selected_evidence_ids": [item.id for item in selected],
        })
        raise RunError("citations", code, trace)

    link = re.search(r"https?://|\]\(|!\[|<a\b|(?m:^[ \t]{0,3}\[[^\]\n]+\]:)", draft, re.IGNORECASE)
    if link:
        reject("unresolved_answer_link", "answer_link_or_image", link)
    literal_regions = []
    outside_start = 0
    if "```" in draft or "~~~" in draft:
        markdown = MarkdownIt("commonmark", {"html": False}).enable("table")
        draft = _separate_fence_citations(draft, token, markdown)
        line_starts = _line_starts(draft)
        for block in markdown.parse(draft):
            if block.type == "fence" and block.map:
                start, end = (line_starts[line] for line in block.map)
                if literal := token.search(draft, start, end):
                    reject("malformed_citation_reference", "literal_citation", literal)
                literal_regions.append((outside_start, start))
                outside_start = end
    literal_regions.append((outside_start, len(draft)))
    literal_syntax = re.compile(r"(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)|(?m:^(?: {4}|\t).+$)")
    for start, end in literal_regions:
        for literal in literal_syntax.finditer(draft, start, end):
            if token.search(literal.group()):
                reject("malformed_citation_reference", "literal_citation", literal)

    def replace(match: re.Match) -> str:
        nonlocal offset
        prefix = draft[:match.start()]
        if prefix.endswith("[") or draft[match.end():].startswith("]"):
            reject("malformed_citation_reference", "unbalanced_brackets", match)
        if (len(prefix) - len(prefix.rstrip("\\"))) % 2:
            reject("malformed_citation_reference", "escaped_citation", match)
        references: list[str] = []
        source_refs: dict[str, list[tuple[str, int]]] = {}
        for ref in re.findall(alias, match.group()):
            if ref not in aliases:
                reject("invalid_citation_reference", "unknown_or_unselected_alias", match)
            occurrences[ref] += 1
            source_refs.setdefault(aliases[ref], []).append((ref, occurrences[ref]))
        for source_id, keys in source_refs.items():
            if source_id not in used:
                used.append(source_id)
            number = used.index(source_id) + 1
            marker = f"[{number}]"
            start = match.start() + offset + sum(len(part) + 1 for part in references)
            support = ()
            if len(keys) == 1:
                key, = keys
                support = _saved_passage(selected_by_id.get(key[0]), proposals.get(key))
            uses.append(CitationUse(number, start, start + len(marker), support))
            references.append(marker)
        rendered = " ".join(references)
        offset += len(rendered) - len(match.group())
        return rendered

    prose = token.sub(lambda match: " " * len(match.group()), draft)
    malformed = re.search(
        r"\[\s*[EDed](?=\d|\s|\]|,|$)[0-9]*|(?<!\w)[EDed][0-9]*(?:@[^\s\]]*)?\s*\]", prose,
    )
    if malformed:
        reject("malformed_citation_reference", "incomplete_alias", malformed)
    answer = token.sub(replace, draft)
    if not answer.strip():
        raise RunError("answer", "empty_answer", trace)
    if require_citation and not used:
        reject("missing_citation", "no_alias")
    # Generated descriptions cannot establish membership. Match only through
    # already-validated aliases to sources actually cited in the final prose.
    previews: dict[str, str] = {}
    for row in descriptions if isinstance(descriptions, list) else ():
        if not isinstance(row, dict):
            continue
        ref, text = row.get("source_ref"), row.get("description")
        if not isinstance(ref, str) or not isinstance(text, str) or not 1 <= len(text) <= 1200:
            continue
        source_id = aliases.get(ref)
        text = " ".join(text.split())
        if source_id in used and text:
            previews.setdefault(source_id, text)
    citations = []
    for number, source_id in enumerate(used, 1):
        group = tuple(materials[source_id])
        if group[0].source_kind == "user_document":
            document = stored_documents[source_id]
            citations.append(Citation(
                number, source_id, document.filename, "", group, "user_document", document.document_id,
                document.filename, min(item.page_start for item in group), max(item.page_end for item in group),
                description=previews.get(source_id),
            ))
        else:
            citations.append(Citation(number, source_id, acquired[source_id].title, acquired[source_id].url, group,
                                      description=previews.get(source_id)))
    citations = tuple(citations)
    trace.append({"stage": "citations", "action": "resolved", "source_ids": used,
                  "material_ids": [item.id for citation in citations for item in citation.materials]})
    return answer, citations, tuple(uses)
