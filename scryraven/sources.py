"""Immutable acquired material and run-local exact packet mechanics. No I/O or judgment."""

from __future__ import annotations

import math
import re
from bisect import bisect_right
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Literal

# Provisional, observable economics choices; none decides evidentiary sufficiency.
TARGETED_SOURCE_CHARACTERS = 32_000
REGION_TARGET = 3_200
REGION_MAX = 4_800
PACKET_CHARACTERS = 32_000
EXPANSION_CHARACTERS = 48_000


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    url: str
    title: str
    content: str
    acquisition: Literal["provider_highlights", "fetched_source", "targeted_view"] = "fetched_source"
    source_id: str = ""
    parent_id: str | None = None
    start_char: int | None = None
    end_char: int | None = None

    def __post_init__(self) -> None:
        if not self.source_id:
            object.__setattr__(self, "source_id", self.id)
        if self.acquisition == "targeted_view":
            if (not self.parent_id or self.start_char is None or self.end_char is None
                    or not 0 <= self.start_char < self.end_char
                    or self.end_char - self.start_char != len(self.content)):
                raise ValueError("invalid_source_range")
        elif any(value is not None for value in (self.parent_id, self.start_char, self.end_char)):
            raise ValueError("non_view_has_source_offsets")

    def material(self) -> dict:
        return asdict(self)


def exact_view(parent: Evidence, start: int, end: int) -> Evidence:
    if parent.acquisition != "fetched_source" or not 0 <= start < end <= len(parent.content):
        raise ValueError("invalid_source_range")
    return Evidence(
        f"{parent.id}@{start}:{end}", parent.url, parent.title, parent.content[start:end],
        "targeted_view", parent.source_id, parent.id, start, end,
    )


_STOP = frozenset("""a an and are as at be been but by can did do does for from had has
have how i if in into is it its may of on or our that the their there these they this
those to use uses using was were what when where which who why will with would
according about show shows evidence question source material need""".split())


def _terms(text: str) -> list[str]:
    text = re.sub(r"(?<=\d),(?=\d)", "", text.casefold())
    return [term for term in re.findall(r"\w+", text) if term not in _STOP and (len(term) > 1 or term.isdigit())]


def _spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Prefer paragraph, then sentence, then word boundaries; preserve every char."""
    spans = []
    while end - start > REGION_MAX:
        low, target, high = start + REGION_TARGET // 2, start + REGION_TARGET, start + REGION_MAX
        candidates = [m.end() for m in re.finditer(r"\n[ \t]*\n", text[start:high])]
        candidates = [start + offset for offset in candidates if start + offset >= low]
        if not candidates:
            candidates = [start + m.end() for m in re.finditer(r"[.!?][\"')\]]?\s+", text[start:high])
                          if start + m.end() >= low]
        if not candidates:
            candidates = [start + m.end() for m in re.finditer(r"\s+", text[start:high])
                          if start + m.end() >= low]
        cut = min(candidates, key=lambda position: abs(position - target)) if candidates else target
        spans.append((start, cut))
        start = cut
    if start < end:
        spans.append((start, end))
    return spans


class SourceIndex:
    """A disposable structure/lexical locator, with the immutable parent intact."""

    def __init__(self, source: Evidence) -> None:
        self.source = source
        text = source.content
        # Only explicit line structure. Flattened PDFs do not acquire invented headings/pages.
        self.headings = [(m.start(), m.end()) for m in re.finditer(
            r"(?m)^(?:#{1,6}[ \t]+[^\n]+|[1-9]\d{0,2}(?:\.\d+)+\.?[ \t]+[^\W\d_][^\n]{0,159}"
            r"|[^|\n]{1,80}[ \t]+\|[ \t]+[^|\n]{1,160})$", text,
        )]
        boundaries = sorted({0, len(text), *(start for start, _ in self.headings)})
        self.section_starts = boundaries[:-1]
        self.sections = list(zip(boundaries, boundaries[1:]))
        self.regions = [span for start, end in zip(boundaries, boundaries[1:]) for span in _spans(text, start, end)]
        tokens = [_terms(text[start:end]) for start, end in self.regions]
        self.counts = [Counter(terms) for terms in tokens]
        self.pairs = [set(zip(terms, terms[1:])) for terms in tokens]
        self.frequency = Counter(term for counts in self.counts for term in counts)
        self.pair_frequency = Counter(pair for pairs in self.pairs for pair in pairs)
        self.lengths = [sum(counts.values()) for counts in self.counts]
        self.average_length = sum(self.lengths) / max(1, len(self.lengths))


    def rank(self, query: str, start_char: int = 0) -> list[int]:
        tokens = _terms(query)
        terms, pairs = set(tokens), set(zip(tokens, tokens[1:]))
        scores = []
        for index, counts in enumerate(self.counts):
            if self.regions[index][1] <= start_char:
                continue
            score = 0.0
            length = self.lengths[index] / max(1, self.average_length)
            for term in terms:
                frequency = counts[term]
                if frequency:
                    idf = math.log(1 + (len(self.regions) - self.frequency[term] + 0.5) / (self.frequency[term] + 0.5))
                    score += idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length))
            # Adjacent lexical terms and coverage reduce isolated rare-word distractors.
            # These are inspection priorities only; Research still selects relevance.
            for pair in pairs.intersection(self.pairs[index]):
                score += 2 * math.log(1 + (len(self.regions) - self.pair_frequency[pair] + 0.5)
                                      / (self.pair_frequency[pair] + 0.5))
            score *= sum(bool(counts[term]) for term in terms) / max(1, len(terms))
            if score:
                scores.append((score, index))
        return [index for _, index in sorted(scores, key=lambda item: (-item[0], item[1]))]

    def anchor_regions(self, excerpt: str) -> tuple[list[int], dict]:
        """Locate whitespace-exact wording, without treating joins as source spans."""
        if not excerpt.strip():
            return [], {"anchor_mode": "unavailable", "anchor_regions": 0}
        tokens = list(re.finditer(r"\S+", self.source.content))
        normalized = " ".join(token.group() for token in tokens)
        normalized_starts = []
        offset = 0
        for token in tokens:
            normalized_starts.append(offset)
            offset += len(token.group()) + 1
        words = excerpt.split()
        whole = " ".join(words)
        hit = normalized.find(whole)
        starts = [start for start, _ in self.regions]
        locations = []
        if hit >= 0:
            locations.append(hit)
            mode = "whole_whitespace_exact"
        else:
            mode = "partial_whitespace_exact"
            # Ignore TOC dots and URL/formatting runs. This is location, never support.
            for index in range(0, max(0, len(words) - 7), 4):
                phrase = " ".join(words[index:index + 8])
                if len(set(_terms(phrase))) < 4:
                    continue
                found = normalized.find(phrase)
                if (found >= 0 and (found == 0 or normalized[found - 1] == " ")
                        and (found + len(phrase) == len(normalized) or normalized[found + len(phrase)] == " ")):
                    locations.append(found)
        regions = list(dict.fromkeys(
            bisect_right(starts, tokens[bisect_right(normalized_starts, location) - 1].start()) - 1
            for location in locations
        ))
        return regions, {"anchor_mode": mode if regions else "not_located", "anchor_regions": len(regions)}

    def packet(
        self, queries: list[str], excerpt: str = "", previous: list[Evidence] | None = None,
    ) -> tuple[list[Evidence], dict]:
        """One generous packet, interleaving needs and matchable excerpt regions."""
        expanding = previous is not None
        budget = EXPANSION_CHARACTERS if expanding else PACKET_CHARACTERS
        anchors, anchor_metrics = self.anchor_regions(excerpt)
        rankings = [self.rank(query) for query in queries if query.strip()]
        considered = len(set(region for ranking in rankings for region in ranking))
        # Lexical hypotheses get independent turns; an anchor cannot dominate the packet.
        if anchors:
            rankings.append(anchors)
        radius = 2 if expanding else 1
        if previous:
            starts = [start for start, _ in self.regions]
            neighbors = []
            for view in previous:
                neighbors.extend([
                    max(0, bisect_right(starts, view.start_char) - 1),
                    min(len(starts) - 1, bisect_right(starts, view.end_char - 1) - 1),
                ])
            rankings.append(list(dict.fromkeys(neighbors)))
        spans: list[tuple[int, int]] = []

        def add(start: int, end: int) -> bool:
            combined = sorted([*spans, (start, end)])
            merged: list[tuple[int, int]] = []
            for left, right in combined:
                if merged and left <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], right))
                else:
                    merged.append((left, right))
            if sum(right - left for left, right in merged) > budget:
                return False
            spans[:] = merged
            return True

        # Actual front matter can establish identity/scope; title metadata cannot.
        add(*self.regions[0])
        for position in range(max((len(ranking) for ranking in rankings), default=0)):
            for ranking in rankings:
                if position >= len(ranking):
                    continue
                index = ranking[position]
                start = self.regions[max(0, index - radius)][0]
                end = self.regions[min(len(self.regions) - 1, index + radius)][1]
                if self.headings:
                    section_start, section_end = self.sections[bisect_right(self.section_starts, self.regions[index][0]) - 1]
                    if section_end - section_start <= budget // 2:
                        # Keep a reasonably sized printed section coherent, including
                        # its definitions/captions, instead of clipping to a lexical hit.
                        start, end = min(start, section_start), max(end, section_end)
                add(start, end)
        if not considered and not anchors:
            # Observable lexical miss: inspect dispersed exact context, never invent relevance.
            for index in (len(self.regions) // 2, len(self.regions) - 1):
                add(self.regions[max(0, index - radius)][0], self.regions[min(len(self.regions) - 1, index + radius)][1])
        if expanding and len(self.source.content) <= budget:
            spans = [(0, len(self.source.content))]
        views = [exact_view(self.source, start, end) for start, end in spans]
        return views, {
            **anchor_metrics, "candidate_regions_considered": considered,
            "packet_characters": sum(len(view.content) for view in views),
            "packet_budget_characters": budget, "region_count": len(self.regions),
            "full_body_in_packet": spans == [(0, len(self.source.content))],
            "regions": [{"id": view.id, "start_char": view.start_char, "end_char": view.end_char} for view in views],
        }


class SourcePackets:
    """Run-local retained acquisitions and exact exposed material, with one expansion."""

    def __init__(self) -> None:
        self.materials: dict[str, Evidence] = {}
        self.indexes: dict[str, SourceIndex] = {}
        self.expanded: set[str] = set()
        self.pending: list[Evidence] = []
        self.selection_refs: list[str] = []

    def acquire(self, source: Evidence, queries: list[str], excerpt: str, trace: list[dict]) -> None:
        targeted = source.acquisition == "fetched_source" and len(source.content) > TARGETED_SOURCE_CHARACTERS
        metrics = {}
        if targeted:
            index = SourceIndex(source)
            self.indexes[source.id] = index
            exposed, metrics = index.packet(queries, excerpt)
        else:
            exposed = [source]
        self._retain(exposed)
        trace.append({
            "stage": "research", "action": "source_material_prepared", "evidence_id": source.id,
            "source_id": source.source_id, "acquisition": source.acquisition,
            "source_characters": len(source.content), "targeted": targeted,
            "activation_threshold_characters": TARGETED_SOURCE_CHARACTERS, **metrics,
        })

    def _retain(self, items: list[Evidence]) -> None:
        for item in items:
            if item.id not in self.materials:
                self.materials[item.id] = item
                self.pending.append(item)

    def expand(self, parent_id: str, context_needed: str, trace: list[dict]) -> bool:
        if parent_id not in self.indexes or parent_id in self.expanded or not context_needed.strip():
            trace.append({"stage": "research", "action": "expansion_rejected", "parent_id": parent_id,
                          "code": "expansion_unavailable"})
            return False
        self.expanded.add(parent_id)
        previous = [item for item in self.materials.values() if item.parent_id == parent_id]
        views, metrics = self.indexes[parent_id].packet([context_needed], previous=previous)
        before = len(self.materials)
        self._retain(views)
        trace.append({"stage": "research", "action": "source_expanded", "parent_id": parent_id,
                      "context_needed": context_needed[:600], "expansions_remaining": 0, **metrics})
        return len(self.materials) > before

    def catalog(self) -> list[dict]:
        return [{"id": item.id, "url": item.url, "title": item.title, "source_id": item.source_id,
                 "acquisition": item.acquisition, "parent_id": item.parent_id,
                 "start_char": item.start_char, "end_char": item.end_char} for item in self.materials.values()]
