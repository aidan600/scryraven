"""Completed answers and exact citation custody, without semantic state."""

from __future__ import annotations

import re
from dataclasses import dataclass

from scryraven.presentation import Citation, CitationUse
from scryraven.research import RunError
from scryraven.sources import Evidence, exact_view


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


def resolve_citations(
    draft: str, selected: list[Evidence] | tuple[Evidence, ...],
    acquisitions: list[Evidence] | tuple[Evidence, ...], trace: list[dict], *,
    require_citation: bool = True,
) -> tuple[str, tuple[Citation, ...], tuple[CitationUse, ...]]:
    """Resolve only aliases for actual supplied material, grouping by source.

    Exact material IDs and a selected group's canonical source ID are accepted.
    A source alias grants access only to the supplied packet, never to unseen
    retained versions or the unsupplied remainder of a full parent.
    """
    acquired = {item.id: item for item in acquisitions}
    aliases: dict[str, str] = {}
    materials: dict[str, list[Evidence]] = {}
    for item in selected:
        try:
            original = (exact_view(acquired[item.parent_id], item.start_char, item.end_char)
                        if item.acquisition == "targeted_view" else acquired[item.id])
            source = acquired[item.source_id]
        except (KeyError, TypeError, ValueError):
            raise RunError("citations", "invalid_selected_material", trace) from None
        if original != item or source.id != source.source_id or source.url != item.url:
            raise RunError("citations", "invalid_selected_material", trace)
        if item.id in aliases:
            raise RunError("citations", "duplicate_selected_material", trace)
        aliases[item.id] = item.source_id
        group = materials.setdefault(item.source_id, [])
        group.append(item)
    for source_id in materials:
        aliases[source_id] = source_id

    used: list[str] = []
    uses: list[CitationUse] = []
    offset = 0
    alias = r"E[0-9]+(?:@[0-9]+:[0-9]+)?"
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
    literal_syntax = (
        r"(?ms:^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?(?:^ {0,3}\1[ \t]*$|\Z))"
        r"|(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\2(?!`)|(?m:^(?: {4}|\t).+$)"
    )
    for literal in re.finditer(literal_syntax, draft):
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
        source_refs: list[str] = []
        for ref in re.findall(alias, match.group()):
            if ref not in aliases:
                reject("invalid_citation_reference", "unknown_or_unselected_alias", match)
            source_id = aliases[ref]
            if source_id in source_refs:
                continue
            source_refs.append(source_id)
            if source_id not in used:
                used.append(source_id)
            number = used.index(source_id) + 1
            marker = f"[{number}]"
            start = match.start() + offset + sum(len(part) + 1 for part in references)
            uses.append(CitationUse(number, start, start + len(marker)))
            references.append(marker)
        rendered = " ".join(references)
        offset += len(rendered) - len(match.group())
        return rendered

    prose = token.sub(lambda match: " " * len(match.group()), draft)
    malformed = re.search(r"\[\s*[Ee](?=\d|\s|\]|,|$)[0-9]*|(?<!\w)[Ee][0-9]*(?:@[^\s\]]*)?\s*\]", prose)
    if malformed:
        reject("malformed_citation_reference", "incomplete_alias", malformed)
    answer = token.sub(replace, draft)
    if not answer.strip():
        raise RunError("answer", "empty_answer", trace)
    if require_citation and not used:
        reject("missing_citation", "no_alias")
    citations = tuple(
        Citation(number, source_id, acquired[source_id].title, acquired[source_id].url,
                 tuple(materials[source_id]))
        for number, source_id in enumerate(used, 1)
    )
    trace.append({"stage": "citations", "action": "resolved", "source_ids": used,
                  "material_ids": [item.id for citation in citations for item in citation.materials]})
    return answer, citations, tuple(uses)
