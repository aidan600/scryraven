"""Mechanical Search/Read/Find executor over immutable actual material.

Acquisition, local location and exposure are observable facts. None of them is an
assessment of truth, applicability or sufficiency. There is no model call here.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import asdict
from html import unescape
from urllib.parse import quote, urljoin, urlsplit

from core.exa_transport import DiscoveryCandidate, search_exa
from core.linkup_transport import fetch_linkup
from core.serper_transport import search_serper
from core.transport import FetchedMaterial
from scryraven.sources import TARGETED_SOURCE_CHARACTERS, Evidence, SourceIndex, exact_view

FIND_RESULT_LIMIT = 8


def _public_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme in {"http", "https"} and bool(parsed.hostname)
            and not parsed.username and not parsed.password
            and not any(char.isspace() or ord(char) < 32 for char in url)
        )
    except ValueError:
        return False


def _link_url(value: str, base: str) -> str:
    # Fetch markdown may contain unescaped spaces in link targets.
    value = re.sub(r"\\([_.*~])", r"\1", value.strip().strip("<>"))
    return quote(urljoin(base, unescape(value)), safe=":/?#@!$&'*+,;=%~-._")


def _visible_links(text: str, base: str) -> set[str]:
    """Recognize explicit links without truncating balanced URL parentheses."""
    targets = []
    masked = list(text)
    for match in re.finditer(r"\]\(", text):
        start, position, depth, quoted = match.end(), match.end(), 1, ""
        while position < len(text):
            char = text[position]
            if char == "\\":
                position += 2
                continue
            if quoted:
                if char == quoted:
                    quoted = ""
            elif char in "\"'" and position > start and text[position - 1].isspace():
                quoted = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    destination = re.sub(r"\s+[\"'][^\"']*[\"']$", "", text[start:position])
                    targets.append(destination)
                    masked[match.start():position + 1] = " " * (position + 1 - match.start())
                    break
            elif char in "\r\n":
                break
            position += 1
    targets.extend(re.findall(r"href=[\"']([^\"']+)[\"']", text, flags=re.IGNORECASE))
    for target in re.findall(r"https?://[^\s<>\"']+", "".join(masked)):
        target = target.rstrip(".,;!?")
        for opening, closing in (("(", ")"), ("[", "]")):
            while target.endswith(closing) and target.count(closing) > target.count(opening):
                target = target[:-1]
        targets.append(target)
    links = set()
    for target in targets:
        try:
            url = _link_url(re.sub(r"\\([()])", r"\1", target), base)
        except ValueError:
            continue
        if _public_url(url):
            links.add(url)
    return links


class AcquisitionError(ValueError):
    """A fixed mechanical code; never contains provider, source or model text."""


class AcquisitionLibrary:
    def __init__(
        self, retained_acquisitions: Iterable[Evidence] = (), *,
        search: Callable[..., list[DiscoveryCandidate]] = search_exa,
        lexical_search: Callable[..., list[DiscoveryCandidate]] = search_serper,
        fetch: Callable[..., FetchedMaterial] = fetch_linkup,
    ) -> None:
        self.search, self.lexical_search, self.fetch = search, lexical_search, fetch
        self.acquisitions = list(retained_acquisitions)
        self.materials: dict[str, Evidence] = {}
        self.exposed: set[str] = set()
        self.candidates: dict[str, dict] = {}
        self._source_ids: dict[str, str] = {}
        self._candidate_ids: dict[str, str] = {}
        self._indexes: dict[str, SourceIndex] = {}
        for index, item in enumerate(self.acquisitions, 1):
            if (not isinstance(item, Evidence) or item.id != f"E{index}"
                    or item.acquisition not in {"fetched_source", "provider_highlights"}
                    or not item.content.strip() or not _public_url(item.url)
                    or item.source_id != self._source_ids.setdefault(item.url, item.id)):
                raise AcquisitionError("invalid_retained_acquisitions")
            self.materials[item.id] = item
            self._candidate(item.url, item.title)

    def _candidate(self, url: str, title: str = "", context: str = "") -> str:
        if not _public_url(url):
            raise AcquisitionError("invalid_public_url")
        if url not in self._candidate_ids:
            ref = f"C{len(self.candidates) + 1}"
            self._candidate_ids[url] = ref
            self.candidates[ref] = {"id": ref, "url": url, "title": title}
        ref = self._candidate_ids[url]
        if title and not self.candidates[ref]["title"]:
            self.candidates[ref]["title"] = title
        if context and "context" not in self.candidates[ref]:
            self.candidates[ref]["context"] = context
        return ref

    def allow_question_urls(self, question: str) -> None:
        """Explicit links supplied by the user are available navigation targets."""
        for url in sorted(_visible_links(question, "")):
            self._candidate(url)

    def expose(self, refs: Iterable[str]) -> None:
        """Record exactly supplied items; only their visible links become targets."""
        refs = list(dict.fromkeys(refs))
        if any(ref not in self.materials for ref in refs):
            raise AcquisitionError("unknown_exposure_reference")
        for ref in refs:
            item = self.materials[ref]
            self.exposed.add(ref)
            for url in sorted(_visible_links(item.content, item.url)):
                self._candidate(url)

    def catalog(self) -> dict:
        rows = []
        for item in self.materials.values():
            row = asdict(item)
            del row["content"]
            rows.append({**row, "characters": len(item.content), "exposed": item.id in self.exposed})
        return {
            "materials": rows,
            "candidates": [{**row, "material_ids": [item.id for item in self.acquisitions
                                                       if item.url == row["url"]]}
                           for row in self.candidates.values()],
        }

    def _retain(self, url: str, title: str, content: str, acquisition: str) -> Evidence:
        if not _public_url(url) or not isinstance(content, str) or not content.strip():
            raise AcquisitionError("unusable_acquisition")
        existing = next((item for item in self.acquisitions
                         if (item.url, item.content, item.acquisition) == (url, content, acquisition)), None)
        if existing is not None:
            return existing
        ref = f"E{len(self.acquisitions) + 1}"
        item = Evidence(ref, url, title, content, acquisition, self._source_ids.setdefault(url, ref))
        self.acquisitions.append(item)
        self.materials[ref] = item
        self._candidate(url, title)
        return item

    def _index(self, item: Evidence) -> SourceIndex:
        if item.id not in self._indexes:
            self._indexes[item.id] = SourceIndex(item)
        return self._indexes[item.id]

    def _views(self, item: Evidence, focus: str, start: int | None, end: int | None) -> list[Evidence]:
        if start is not None or end is not None:
            if (isinstance(start, bool) or isinstance(end, bool)
                    or not isinstance(start, int) or not isinstance(end, int)):
                raise AcquisitionError("invalid_exact_range")
            parent = self.materials[item.parent_id] if item.parent_id else item
            if parent.acquisition != "fetched_source" or not 0 <= start < end <= len(parent.content):
                raise AcquisitionError("invalid_exact_range")
            # Preserve the complete requested range in source order, with each
            # item small enough for the caller to deliver through bounded attention.
            items = [exact_view(parent, left, min(left + TARGETED_SOURCE_CHARACTERS, end))
                     for left in range(start, end, TARGETED_SOURCE_CHARACTERS)]
        elif item.acquisition == "targeted_view":
            items = [item]
        else:
            parent = self.materials[item.parent_id] if item.parent_id else item
            if parent.acquisition == "fetched_source" and len(parent.content) > TARGETED_SOURCE_CHARACTERS:
                items, _ = self._index(parent).packet([focus])
            else:
                items = [parent]
        self.materials.update((item.id, item) for item in items)
        return items

    def _coalesce_views(self, items: list[Evidence]) -> list[Evidence]:
        """Remove repeated characters within selected views, without changing selection."""
        by_parent: dict[str, list[tuple[int, int, int]]] = {}
        ordered = []
        for position, item in enumerate(items):
            if item.acquisition == "targeted_view":
                by_parent.setdefault(item.parent_id, []).append((item.start_char, item.end_char, position))
            else:
                ordered.append((position, 0, item))
        for parent_ref, spans in by_parent.items():
            merged = []
            for start, end, position in sorted(spans):
                if merged and start <= merged[-1][1]:
                    old_start, old_end, old_position = merged[-1]
                    merged[-1] = (old_start, max(end, old_end), min(position, old_position))
                else:
                    merged.append((start, end, position))
            parent = self.materials[parent_ref]
            for start, end, position in merged:
                for left in range(start, end, TARGETED_SOURCE_CHARACTERS):
                    ordered.append((position, left - start,
                                    exact_view(parent, left, min(left + TARGETED_SOURCE_CHARACTERS, end))))
        # Preserve the first selected hit's priority for each merged region. Only
        # contiguous source characters are joined, never different parent versions.
        return [item for _, _, item in sorted(ordered, key=lambda row: (row[0], row[1]))]

    def _target(self, ref: str) -> tuple[str, str, Evidence | None]:
        if ref in self.materials:
            item = self.materials[ref]
            return item.url, item.title, item
        if ref in self.candidates:
            row = self.candidates[ref]
            return row["url"], row["title"], None
        if _public_url(ref):
            # Normalize only syntactic escaped links, never publication identity.
            normalized = _link_url(ref, ref)
            ref = ref if ref in self._candidate_ids else normalized
            if ref in self._candidate_ids:
                row = self.candidates[self._candidate_ids[ref]]
                return ref, row["title"], None
            raise AcquisitionError("unobserved_url")
        raise AcquisitionError("unknown_target")

    @staticmethod
    def _request(request: dict) -> dict:
        """Validate the small executor contract without retaining arbitrary keys."""
        if not isinstance(request, dict):
            raise AcquisitionError("invalid_request")
        kind = request.get("kind")
        if not isinstance(kind, str) or kind not in {"search", "search_lexical", "read", "find"}:
            raise AcquisitionError("invalid_request_kind")
        result = {"kind": kind}
        for key in ("query", "target", "focus"):
            value = request.get(key, "")
            if not isinstance(value, str):
                raise AcquisitionError("invalid_request_field")
            result[key] = value.strip()
        result["mode"] = request.get("mode", "auto")
        if not isinstance(result["mode"], str) or result["mode"] not in {"auto", "local", "full", "refresh"}:
            raise AcquisitionError("invalid_read_mode")
        scope = request.get("scope", [])
        if not isinstance(scope, list) or any(not isinstance(ref, str) for ref in scope):
            raise AcquisitionError("invalid_find_scope")
        result["scope"] = list(dict.fromkeys(scope))
        for key in ("start_char", "end_char"):
            value = request.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                raise AcquisitionError("invalid_exact_range")
            result[key] = value
        start, end = result["start_char"], result["end_char"]
        if (start is not None or end is not None) and (start is None or end is None or not 0 <= start < end):
            raise AcquisitionError("invalid_exact_range")
        if kind in {"search", "search_lexical", "find"} and not result["query"]:
            raise AcquisitionError("empty_query")
        if kind == "read" and not result["target"]:
            raise AcquisitionError("empty_target")
        return result

    def execute(self, request: dict, *, before_external: Callable[[], None]) -> dict:
        before = len(self.acquisitions)
        kind = request.get("kind") if isinstance(request, dict) else None
        result = {"kind": kind if isinstance(kind, str) and kind in {"search", "search_lexical", "read", "find"} else None,
                  "status": "ok", "material_ids": [], "new_acquisition_ids": [],
                  "candidate_refs": [], "external": False, "local": True}
        try:
            normalized = self._request(request)
            result["request"] = normalized
            if normalized["kind"] in {"search", "search_lexical"}:
                self._search(normalized, result, before_external)
            elif normalized["kind"] == "read":
                self._read(normalized, result, before_external)
            else:
                self._find(normalized, result)
        except AcquisitionError as exc:
            result.update(status="error", code=str(exc))
        result["new_acquisition_ids"] = [item.id for item in self.acquisitions[before:]]
        result["material_ids"] = list(dict.fromkeys(result["material_ids"]))
        return result

    def _search(self, request: dict, result: dict, before_external: Callable[[], None]) -> None:
        before_external()
        result.update(external=True, local=False)
        try:
            lexical = request["kind"] == "search_lexical"
            leads = (self.lexical_search if lexical else self.search)(request["query"])
        except Exception:
            raise AcquisitionError("search_failed") from None
        if not isinstance(leads, list):
            raise AcquisitionError("invalid_search_response")
        for lead in leads:
            if not isinstance(lead, DiscoveryCandidate) or not _public_url(lead.url):
                continue
            navigation = lead.context.strip()[:650] if lexical and isinstance(lead.context, str) else ""
            result["candidate_refs"].append(self._candidate(lead.url, lead.title, navigation))
            if (not lexical and lead.context_kind == "provider_highlights" and not lead.context_omitted_characters
                    and isinstance(lead.context, str) and lead.context.strip()):
                item = self._retain(lead.url, lead.title, lead.context, "provider_highlights")
                result["material_ids"].append(item.id)
        result["candidate_refs"] = list(dict.fromkeys(result["candidate_refs"]))

    def _read(self, request: dict, result: dict, before_external: Callable[[], None]) -> None:
        url, title, exact_item = self._target(request["target"])
        mode = request["mode"]
        full = next((item for item in reversed(self.acquisitions)
                     if item.url == url and item.acquisition == "fetched_source"), None)
        if mode == "local":
            item = exact_item or full or next((item for item in reversed(self.acquisitions) if item.url == url), None)
            if item is None:
                raise AcquisitionError("local_material_unavailable")
        elif mode == "auto" and exact_item is not None:
            item = exact_item
        elif mode in {"auto", "full"} and full is not None:
            item = full
        else:
            before_external()
            result.update(external=True, local=False)
            try:
                fetched = self.fetch(url)
            except Exception:
                raise AcquisitionError("read_failed") from None
            if (not isinstance(fetched, FetchedMaterial) or fetched.requested_url != url
                    or not isinstance(fetched.readable_text, str) or not fetched.readable_text.strip()):
                raise AcquisitionError("unusable_fetch_material")
            item = self._retain(url, title, fetched.readable_text, "fetched_source")
        items = self._views(item, request["focus"], request["start_char"], request["end_char"])
        result["material_ids"] = [item.id for item in items]
        result["candidate_refs"] = [self._candidate_ids[url]]

    def _find(self, request: dict, result: dict) -> None:
        scoped = []
        if request["scope"]:
            for ref in request["scope"]:
                url, _, item = self._target(ref)
                scoped.extend([item] if item else [source for source in self.acquisitions if source.url == url])
        else:
            scoped = list(self.acquisitions)
        scoped = list({item.id: item for item in scoped}.values())
        matches = []
        for item in scoped:
            index = self._index(item)
            ranked = index.rank(request["query"])
            if item.acquisition != "fetched_source":
                if ranked:
                    matches.append([item])
                continue
            # Include adjacent exact context. Finding does not label the match as support.
            views = []
            for region in ranked:
                start = index.regions[max(0, region - 1)][0]
                end = index.regions[min(len(index.regions) - 1, region + 1)][1]
                views.append(exact_view(item, start, end))
            if views:
                matches.append(list({view.id: view for view in views}.values()))
        count = sum(len(items) for items in matches)
        chosen = []
        for position in range(max((len(items) for items in matches), default=0)):
            for items in matches:
                if position < len(items) and len(chosen) < FIND_RESULT_LIMIT:
                    chosen.append(items[position])
        merged = self._coalesce_views(chosen)
        self.materials.update((item.id, item) for item in merged)
        result.update(material_ids=[item.id for item in merged], matching_region_count=count,
                      omitted_match_count=max(0, count - len(chosen)))
