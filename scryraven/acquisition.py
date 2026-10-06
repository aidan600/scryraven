"""Mechanical Search/Read/Find executor over immutable actual material.

Acquisition, local location and exposure are observable facts. None of them is an
assessment of truth, applicability or sufficiency. There is no model call here.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable
from html import unescape
from urllib.parse import quote, urljoin, urlsplit

from core.exa_transport import DiscoveryCandidate, ExaTransportError, search_exa
from core.linkup_transport import LINKUP_FAILURE_CODES, LINKUP_FETCH_STRATEGY, LinkupTransportError, fetch_linkup
from core.serper_transport import SerperTransportError, search_serper
from core.transport import FetchedMaterial
from scryraven.documents import (
    DOCUMENT_ID,
    DOCUMENT_VIEW_ID,
    SessionDocument,
    document_views,
    index_parent,
    page_slices,
)
from scryraven.sources import TARGETED_SOURCE_CHARACTERS, Evidence, SourceIndex, exact_view, rank_corpus_regions

FIND_RESULT_LIMIT = 8
SEARCH_NOVELTY_COUNTS = (
    "returned_candidate_count", "new_candidate_count", "known_candidate_count",
    "returned_material_count", "new_material_count", "new_candidate_material_count",
    "refreshed_known_candidate_material_count", "exact_reused_material_count",
)


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


def generic_search_failure(exc: BaseException) -> str:
    """Map a generic Exa failure to a fixed code. The exception text stays here."""
    if isinstance(exc, ExaTransportError) and str(exc) == "exa_configuration_missing":
        return "exa_configuration_missing"
    return "search_failed"


class AcquisitionLibrary:
    def __init__(
        self, retained_acquisitions: Iterable[Evidence] = (), *,
        documents: Iterable[SessionDocument] = (),
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
        self._documents: dict[str, SessionDocument] = {}
        self._index_parents: dict[str, Evidence] = {}
        for document in documents:
            if (not isinstance(document, SessionDocument) or document.document_id in self._documents
                    or not DOCUMENT_ID.fullmatch(document.document_id)):
                raise AcquisitionError("invalid_retained_documents")
            self._documents[document.document_id] = document
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

    @property
    def documents(self) -> tuple[SessionDocument, ...]:
        return tuple(self._documents.values())

    def catalog(self) -> dict:
        rows = []
        for item in self.materials.values():
            row = item.material()
            del row["content"]
            rows.append({**row, "characters": len(item.content), "exposed": item.id in self.exposed})
        return {
            "materials": rows,
            "candidates": [{**row, "material_ids": [item.id for item in self.acquisitions
                                                       if item.url == row["url"]]}
                           for row in self.candidates.values()],
            "documents": [{
                "id": document.document_id, "filename": document.filename,
                "media_type": document.media_type, "pages": document.page_count,
                "characters": document.text_character_count, "source_kind": "user_document",
                "visual_analysis": False, "textless_page_count": document.textless_page_count,
            } for document in self._documents.values()],
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
            boundaries = ()
            if item.source_kind == "user_document" and item.document_id in self._documents:
                boundaries = self._documents[item.document_id].interior_boundaries
            self._indexes[item.id] = SourceIndex(item, boundaries)
        return self._indexes[item.id]

    def _index_parent(self, document: SessionDocument) -> Evidence:
        if document.document_id not in self._index_parents:
            self._index_parents[document.document_id] = index_parent(document)
        return self._index_parents[document.document_id]

    def _parent_evidence(self, parent_id: str) -> Evidence:
        if parent_id in self._index_parents:
            return self._index_parents[parent_id]
        if parent_id in self._documents:
            return self._index_parent(self._documents[parent_id])
        return self.materials[parent_id]

    def _document_counts(self) -> dict:
        return {
            "document_count": len(self._documents),
            "document_page_count": sum(document.page_count for document in self._documents.values()),
            "document_character_count": sum(document.text_character_count for document in self._documents.values()),
        }

    def _normalize_views(self, items: list[Evidence]) -> list[Evidence]:
        """Replace locator spans with exact single-page document views."""
        normalized = []
        for item in items:
            if item.source_kind == "user_document" and item.acquisition == "targeted_view":
                normalized.extend(document_views(self._documents[item.document_id], item.start_char, item.end_char))
            else:
                normalized.append(item)
        return normalized

    def _remember(self, items: list[Evidence]) -> list[Evidence]:
        items = self._normalize_views(items)
        self.materials.update((item.id, item) for item in items)
        return items

    def _views(self, item: Evidence, focus: str, start: int | None, end: int | None) -> tuple[list[Evidence], dict]:
        parent = self.materials[item.parent_id] if item.parent_id else item
        lexical_match_found = None
        if start is not None or end is not None:
            if (isinstance(start, bool) or isinstance(end, bool)
                    or not isinstance(start, int) or not isinstance(end, int)):
                raise AcquisitionError("invalid_exact_range")
            if parent.acquisition != "fetched_source" or not 0 <= start < end <= len(parent.content):
                raise AcquisitionError("invalid_exact_range")
            # Preserve the complete requested range in source order, with each
            # item small enough for the caller to deliver through bounded attention.
            items = [exact_view(parent, left, min(left + TARGETED_SOURCE_CHARACTERS, end))
                     for left in range(start, end, TARGETED_SOURCE_CHARACTERS)]
            selection_mode = "exact_range"
        elif item.acquisition == "targeted_view":
            items = [item]
            selection_mode = "targeted_view"
        else:
            if parent.acquisition == "fetched_source" and len(parent.content) > TARGETED_SOURCE_CHARACTERS:
                items, metrics = self._index(parent).packet([focus])
                selection_mode = "focused_packet" if focus else "dispersed_packet"
                if focus:
                    lexical_match_found = metrics["candidate_regions_considered"] > 0
            else:
                items = [parent]
                selection_mode = "provider_highlights" if parent.acquisition == "provider_highlights" else "full_parent"
        self.materials.update((item.id, item) for item in items)
        receipt = {"selection_mode": selection_mode,
                   "returned_characters": sum(len(view.content) for view in items),
                   "ranges": [{"id": view.id, "start_char": view.start_char, "end_char": view.end_char}
                              for view in items if view.acquisition == "targeted_view"]}
        if parent.acquisition == "fetched_source":
            if items == [parent]:
                receipt["ranges"] = [{"id": parent.id, "start_char": 0, "end_char": len(parent.content)}]
            ranges = sorted((row["start_char"], row["end_char"]) for row in receipt["ranges"])
            cursor = 0
            for left, right in ranges:
                if left != cursor:
                    break
                cursor = right
            receipt.update(parent_id=parent.id, parent_characters=len(parent.content),
                           full_body_in_packet=cursor == len(parent.content))
        if lexical_match_found is not None:
            receipt["lexical_match_found"] = lexical_match_found
        return items, receipt

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
            document = self._documents.get(parent_ref)
            for start, end, position in sorted(spans):
                crosses_page = False
                if document is not None and merged:
                    crosses_page = len(page_slices(document, merged[-1][0], max(end, merged[-1][1]))) > 1
                if merged and start <= merged[-1][1] and not crosses_page:
                    old_start, old_end, old_position = merged[-1]
                    merged[-1] = (old_start, max(end, old_end), min(position, old_position))
                else:
                    merged.append((start, end, position))
            parent = self._parent_evidence(parent_ref)
            for start, end, position in merged:
                for left in range(start, end, TARGETED_SOURCE_CHARACTERS):
                    ordered.append((position, left - start,
                                    exact_view(parent, left, min(left + TARGETED_SOURCE_CHARACTERS, end))))
        # Preserve the first selected hit's priority for each merged region. Only
        # contiguous source characters are joined, never different parent versions.
        return self._normalize_views([item for _, _, item in sorted(ordered, key=lambda row: (row[0], row[1]))])

    def _target(self, ref: str) -> tuple[str, str, Evidence | None]:
        if ref in self.materials:
            item = self.materials[ref]
            return item.url, item.title, item
        if "@" in ref and re.match(r"^E[1-9]\d*[@]", ref):
            match = re.fullmatch(r"(E[1-9]\d*)@((?:0|[1-9]\d*)):((?:0|[1-9]\d*))", ref)
            if match is None:
                raise AcquisitionError("invalid_exact_range")
            parent = self.materials.get(match.group(1))
            if parent is None:
                raise AcquisitionError("unknown_target")
            try:
                start, end = int(match.group(2)), int(match.group(3))
            except ValueError:
                raise AcquisitionError("invalid_exact_range") from None
            # Ordinary targeted views are bounded; larger requests use the
            # explicit parent range path, which splits them for delivery.
            if (parent.acquisition != "fetched_source" or not 0 <= start < end <= len(parent.content)
                    or end - start > TARGETED_SOURCE_CHARACTERS):
                raise AcquisitionError("invalid_exact_range")
            item = exact_view(parent, start, end)
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

    def execute(
        self, request: dict, *, before_external: Callable[[], None],
        observe_operation: Callable[[dict], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> dict:
        started_at = clock()
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
        ended_at = clock()
        return self._finish_execution(result, before, started_at, ended_at, observe_operation)

    def plan_generic_search(self, request: dict) -> dict | None:
        """Validate one ordinary generic Search without external I/O or library mutation."""
        try:
            normalized = self._request(request)
        except AcquisitionError:
            return None
        if normalized["kind"] != "search":
            return None
        return normalized

    def admit_transported_search(
        self, normalized: dict, outcome: dict, *,
        observe_operation: Callable[[dict], None] | None = None,
    ) -> dict:
        """Admit one finished generic Search. Callers must do this serially, in request order.

        ``outcome`` carries only the transport clock and either leads or a fixed
        error code. This method allocates candidates, materials and Evidence IDs.
        """
        before = len(self.acquisitions)
        result = {"kind": "search", "status": "ok", "material_ids": [], "new_acquisition_ids": [],
                  "candidate_refs": [], "external": True, "local": False, "request": normalized}
        try:
            code = outcome.get("code")
            leads = outcome.get("leads")
            if code:
                raise AcquisitionError(str(code))
            if not isinstance(leads, list):
                raise AcquisitionError("invalid_search_response")
            self._admit_search_leads(normalized, result, leads)
        except AcquisitionError as exc:
            result.update(status="error", code=str(exc))
        return self._finish_execution(
            result, before, outcome["started_at"], outcome["ended_at"], observe_operation,
        )

    def _finish_execution(
        self, result: dict, before: int, started_at: float, ended_at: float,
        observe_operation: Callable[[dict], None] | None,
    ) -> dict:
        result["new_acquisition_ids"] = [item.id for item in self.acquisitions[before:]]
        result["material_ids"] = list(dict.fromkeys(result["material_ids"]))
        duration = max(0.0, ended_at - started_at)
        if "failed_external_read" in result:
            result["failed_external_read"]["duration_seconds"] = round(duration, 6)
        if observe_operation is not None:
            kind = result["kind"]
            provider = ({"search": "exa", "search_lexical": "serper", "read": "linkup"}.get(kind)
                        if result["external"] else "local")
            event = {
                "kind": kind,
                "mode": result.get("request", {}).get("mode") if kind == "read" else None,
                "provider": provider,
                "external": result["external"],
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_seconds": duration,
                "status": result["status"],
                "code": result.get("code"),
                "returned_material_count": len(result["material_ids"]),
                "new_acquisition_count": len(result["new_acquisition_ids"]),
                "returned_material_characters": sum(len(self.materials[ref].content)
                                                     for ref in result["material_ids"]),
                "reused_retained_material": (not result["external"] and bool(result["material_ids"])
                                             and not result["new_acquisition_ids"]),
            }
            if "search_novelty_receipt" in result:
                event["search_novelty_receipt"] = dict(result["search_novelty_receipt"])
            if "document_navigation" in result:
                event["document_navigation"] = {
                    key: value for key, value in result["document_navigation"].items()
                    if type(value) is int and value >= 0
                }
            # A diagnostics observer is never allowed to change the result or Evidence.
            try:
                observe_operation(event)
            except Exception:
                pass
        return result

    def _search(self, request: dict, result: dict, before_external: Callable[[], None]) -> None:
        before_external()
        result.update(external=True, local=False)
        lexical = request["kind"] == "search_lexical"
        try:
            leads = (self.lexical_search if lexical else self.search)(request["query"])
        except Exception as exc:
            if lexical and isinstance(exc, SerperTransportError) and str(exc) == "serper_configuration_missing":
                raise AcquisitionError("serper_configuration_missing") from None
            if lexical:
                raise AcquisitionError("search_failed") from None
            raise AcquisitionError(generic_search_failure(exc)) from None
        if not isinstance(leads, list):
            raise AcquisitionError("invalid_search_response")
        self._admit_search_leads(request, result, leads)

    def _admit_search_leads(self, request: dict, result: dict, leads: list) -> None:
        """Apply provider leads to library state. Novelty is measured at this moment."""
        known_urls = set(self._candidate_ids)
        prior_material_ids = set(self.materials)
        lexical = request["kind"] == "search_lexical"
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
        returned_urls = {self.candidates[ref]["url"] for ref in result["candidate_refs"]}
        returned_ids = set(result["material_ids"])
        new_ids = returned_ids - prior_material_ids
        new_candidate_materials = sum(self.materials[ref].url not in known_urls for ref in new_ids)
        result["search_novelty_receipt"] = {
            "provider": "serper" if lexical else "exa", "kind": request["kind"],
            "returned_candidate_count": len(returned_urls),
            "new_candidate_count": len(returned_urls - known_urls),
            "known_candidate_count": len(returned_urls & known_urls),
            "returned_material_count": len(returned_ids), "new_material_count": len(new_ids),
            "new_candidate_material_count": new_candidate_materials,
            "refreshed_known_candidate_material_count": len(new_ids) - new_candidate_materials,
            "exact_reused_material_count": len(returned_ids & prior_material_ids),
        }

    def _document_request(self, ref: str) -> tuple[SessionDocument, int | None, int | None] | None:
        """Resolve a D id. None means the ref is not a document id."""
        if ref in self._documents:
            return self._documents[ref], None, None
        match = DOCUMENT_VIEW_ID.fullmatch(ref)
        if match:
            document = self._documents.get(match.group(1))
            if document is None:
                raise AcquisitionError("unknown_target")
            return document, int(match.group(2)), int(match.group(3))
        head = ref.split("@", 1)[0]
        if DOCUMENT_ID.fullmatch(head):
            raise AcquisitionError("invalid_exact_range" if "@" in ref else "unknown_target")
        return None

    def _read_document(self, document: SessionDocument, request: dict, explicit: tuple[int | None, int | None],
                       result: dict) -> None:
        """Local exact views only. Document reads never call a provider or spend external attempts."""
        text = document.extracted_text
        start = request["start_char"] if request["start_char"] is not None else explicit[0]
        end = request["end_char"] if request["end_char"] is not None else explicit[1]
        metrics: dict = {}
        if start is not None or end is not None:
            if (isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int)
                    or not isinstance(end, int) or not 0 <= start < end <= len(text)):
                raise AcquisitionError("invalid_exact_range")
            if explicit[0] is not None and (request["start_char"], request["end_char"]) == (None, None):
                if end - start > TARGETED_SOURCE_CHARACTERS:
                    raise AcquisitionError("invalid_exact_range")
            spans = [(start, end)]
            selection_mode = "exact_range"
        elif len(text) > TARGETED_SOURCE_CHARACTERS:
            views, metrics = self._index(self._index_parent(document)).packet([request["focus"]] if request["focus"] else [])
            spans = [(view.start_char, view.end_char) for view in views]
            selection_mode = "focused_packet" if request["focus"] else "dispersed_packet"
        else:
            spans = [(0, len(text))]
            selection_mode = "full_parent"
        items: list[Evidence] = []
        for span_start, span_end in spans:
            items.extend(document_views(document, span_start, span_end))
        items = list(dict.fromkeys(items))
        self.materials.update((item.id, item) for item in items)
        ranges = [{"id": item.id, "start_char": item.start_char, "end_char": item.end_char} for item in items]
        covered = sorted((item.start_char, item.end_char) for item in items)
        cursor = 0
        for left, right in covered:
            if left > cursor:
                break
            cursor = max(cursor, right)
        receipt = {
            "selection_mode": selection_mode,
            "returned_characters": sum(len(item.content) for item in items),
            "ranges": ranges, "parent_id": document.document_id, "parent_characters": len(text),
            "full_body_in_packet": cursor == len(text) and bool(items),
        }
        if request["focus"] and selection_mode != "exact_range":
            receipt["lexical_match_found"] = metrics.get("candidate_regions_considered", 0) > 0
        result["material_ids"] = [item.id for item in items]
        result["candidate_refs"] = []
        result["read_receipt"] = receipt
        result["document_navigation"] = {
            **self._document_counts(),
            "local_read_packet_characters": receipt["returned_characters"],
            "candidate_regions_considered": metrics.get("candidate_regions_considered", 0),
            "exact_returned_region_count": len(items),
        }

    def _read(self, request: dict, result: dict, before_external: Callable[[], None]) -> None:
        document_request = self._document_request(request["target"])
        if document_request is not None:
            self._read_document(document_request[0], request, (document_request[1], document_request[2]), result)
            return
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
            except Exception as exc:
                code = (str(exc) if isinstance(exc, LinkupTransportError)
                        and str(exc) in LINKUP_FAILURE_CODES else "read_failed")
            else:
                code = None
                if (not isinstance(fetched, FetchedMaterial) or fetched.requested_url != url
                        or not isinstance(fetched.readable_text, str) or not fetched.readable_text.strip()):
                    code = "unusable_fetch_material"
            if code is not None:
                result["failed_external_read"] = {
                    "candidate_ref": self._candidate_ids[url], "provider": "linkup",
                    "strategy": LINKUP_FETCH_STRATEGY, "requested_mode": mode, "code": code,
                }
                raise AcquisitionError(code) from None
            item = self._retain(url, title, fetched.readable_text, "fetched_source")
        items, receipt = self._views(item, request["focus"], request["start_char"], request["end_char"])
        result["material_ids"] = [item.id for item in items]
        result["candidate_refs"] = [self._candidate_ids[url]]
        result["read_receipt"] = receipt

    def _find(self, request: dict, result: dict) -> None:
        document_indexes = [self._index(self._index_parent(document)) for document in self._documents.values()]
        if not request["scope"]:
            hits, count = rank_corpus_regions(
                [self._index(item) for item in self.acquisitions] + document_indexes, request["query"],
            )
            chosen = []
            seen_material_ids = set()
            for index, region in hits:
                item = index.source
                if item.acquisition == "fetched_source":
                    # Include adjacent exact context, as scoped Find does.
                    start = index.regions[max(0, region - 1)][0]
                    end = index.regions[min(len(index.regions) - 1, region + 1)][1]
                    material = exact_view(item, start, end)
                else:
                    # A highlight acquisition is one retained text item even if
                    # several of its regions match the query.
                    material = item
                if material.id in seen_material_ids:
                    continue
                seen_material_ids.add(material.id)
                chosen.append(material)
                if len(chosen) == FIND_RESULT_LIMIT:
                    break
            merged = self._coalesce_views(chosen)
            self.materials.update((item.id, item) for item in merged)
            # A selected view can contain several adjacent matching regions, and
            # one selected highlight exposes all of its regions. Count only
            # matching regions whose text was actually left out.
            omitted = 0
            for index, region in hits:
                start, end = index.regions[region]
                if not any(material.id == index.source.id or
                           (material.parent_id == index.source.id
                            and material.start_char <= start and end <= material.end_char)
                           for material in merged):
                    omitted += 1
            result.update(material_ids=[item.id for item in merged], matching_region_count=count,
                          omitted_match_count=omitted,
                          matched_source_count=len({index.source.source_id for index, _ in hits}))
            if document_indexes:
                document_hits = sum(index.source.source_kind == "user_document" for index, _ in hits)
                result["document_navigation"] = {
                    **self._document_counts(),
                    "candidate_regions_considered": sum(len(index.regions) for index in document_indexes),
                    "matching_region_count": document_hits,
                    "exact_returned_region_count": sum(item.source_kind == "user_document" for item in merged),
                }
            return
        scoped = []
        scoped_documents = []
        for ref in request["scope"]:
            document_request = self._document_request(ref)
            if document_request is not None:
                document, start, end = document_request
                parent = self._index_parent(document)
                if start is None:
                    scoped.append(parent)
                else:
                    views = document_views(document, start, end)
                    if len(views) != 1:
                        raise AcquisitionError("invalid_exact_range")
                    scoped.append(views[0])
                scoped_documents.append(document)
                continue
            url, _, item = self._target(ref)
            scoped.extend([item] if item else [source for source in self.acquisitions if source.url == url])
        scoped = list({item.id: item for item in scoped}.values())
        matches = []
        matched_sources = set()
        for item in scoped:
            index = self._index(item)
            ranked = index.rank(request["query"])
            if ranked:
                matched_sources.add(item.source_id)
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
                      omitted_match_count=max(0, count - len(chosen)),
                      matched_source_count=len(matched_sources))
        if scoped_documents:
            result["document_navigation"] = {
                **self._document_counts(),
                "candidate_regions_considered": sum(
                    len(self._index(item).regions) for item in scoped if item.source_kind == "user_document"
                ),
                "matching_region_count": sum(
                    len(self._index(item).rank(request["query"]))
                    for item in scoped if item.source_kind == "user_document"
                ),
                "exact_returned_region_count": sum(item.source_kind == "user_document" for item in merged),
            }
