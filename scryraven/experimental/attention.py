"""Reversible attention over retained Evidence. Local mechanics only, no judgments."""

from __future__ import annotations

import re
from dataclasses import asdict

from core.exa_transport import DiscoveryCandidate
from scryraven.experimental.contracts import CatalogWindow, ExperimentalLimits, Inspect
from scryraven.research import _public_url
from scryraven.sources import Evidence, SourceIndex, exact_view


class AttentionError(ValueError):
    """Fixed mechanical failure code, with no source or model text."""


class Attention:
    def __init__(self, retained: tuple[Evidence, ...], limits: ExperimentalLimits) -> None:
        self.limits = limits
        self.acquisitions = list(retained)
        self.materials = {item.id: item for item in retained}
        self.source_ids: dict[str, str] = {}
        for index, item in enumerate(retained, 1):
            if (item.id != f"E{index}" or item.acquisition == "targeted_view"
                    or not item.content.strip() or not _public_url(item.url)
                    or item.source_id != self.source_ids.setdefault(item.url, item.id)):
                raise AttentionError("invalid_retained_corpus")
        self.active: dict[str, Evidence] = {}
        self.exposed: set[str] = set()
        self.navigation: dict[str, dict] = {}
        self.indexes: dict[str, SourceIndex] = {}
        self.window = CatalogWindow(offset=0, query="")

    def retain(self, url: str, title: str, content: str, acquisition: str) -> Evidence:
        if (not _public_url(url) or not content.strip()
                or acquisition not in {"provider_highlights", "fetched_source"}):
            raise AttentionError("unusable_acquisition")
        existing = next((item for item in self.acquisitions if
                         (item.url, item.content, item.acquisition) == (url, content, acquisition)), None)
        if existing is not None:
            return existing
        ref = f"E{len(self.acquisitions) + 1}"
        item = Evidence(ref, url, title, content, acquisition, self.source_ids.setdefault(url, ref))
        self.acquisitions.append(item)
        self.materials[item.id] = item
        return item

    def discover(self, leads: list[DiscoveryCandidate]) -> dict:
        retained, activated, candidates = [], [], []
        for lead in leads:
            if not _public_url(lead.url):
                continue
            ref = next((ref for ref, row in self.navigation.items() if row["url"] == lead.url), None)
            if ref is None:
                ref = f"D{len(self.navigation) + 1}"
                self.navigation[ref] = {"id": ref, "url": lead.url, "title": lead.title,
                                        "acquisition": "navigation"}
            candidates.append(ref)
            if (lead.context_kind == "provider_highlights" and not lead.context_omitted_characters
                    and lead.context.strip()):
                item = self.retain(lead.url, lead.title, lead.context, "provider_highlights")
                retained.append(item.id)
                if self.activate([item]):
                    activated.append(item.id)
        return {"kind": "discover", "candidate_refs": list(dict.fromkeys(candidates)),
                "retained_material_refs": list(dict.fromkeys(retained)),
                "activated_material_refs": list(dict.fromkeys(activated))}

    def resolve(self, ref: str) -> Evidence:
        if ref in self.materials:
            return self.materials[ref]
        match = re.fullmatch(r"(E[0-9]+)@([0-9]+):([0-9]+)", ref)
        if match and match[1] in self.materials:
            try:
                view = exact_view(self.materials[match[1]], int(match[2]), int(match[3]))
            except ValueError:
                raise AttentionError("invalid_exact_range") from None
            if view.id == ref:
                self.materials[ref] = view
                return view
        raise AttentionError("unknown_material_reference")

    def source(self, ref: str) -> tuple[str, str]:
        if ref in self.navigation:
            row = self.navigation[ref]
            return row["url"], row["title"]
        item = self.resolve(ref)
        return item.url, item.title

    def full_parent(self, url: str) -> Evidence | None:
        return next((item for item in self.acquisitions
                     if item.url == url and item.acquisition == "fetched_source"), None)

    def shelve(self, refs: list[str]) -> None:
        # Direct addressing is independent of the visible catalog window/lexical ranking.
        for ref in refs:
            self.resolve(ref)
        for ref in refs:
            self.active.pop(ref, None)

    def activate(self, items: list[Evidence]) -> bool:
        proposed = {**self.active, **{item.id: item for item in items}}
        if sum(len(item.content) for item in proposed.values()) > self.limits.active_evidence_target_chars:
            return False
        self.active = proposed
        return True

    def inspect(self, action: Inspect) -> dict:
        items = [self.resolve(ref) for ref in action.activate_material_refs]
        for span in action.exact_ranges:
            try:
                view = exact_view(self.resolve(span.parent_ref), span.start_char, span.end_char)
            except ValueError:
                raise AttentionError("invalid_exact_range") from None
            self.materials[view.id] = view
            items.append(view)
        result = {"kind": "inspect", "activation": "applied" if self.activate(items) else "attention_target_exceeded",
                  "requested_material_refs": [item.id for item in items]}
        if action.locate is not None:
            locator = action.locate
            item = self.resolve(locator.material_ref)
            parent = self.resolve(item.parent_id) if item.parent_id else item
            if parent.acquisition != "fetched_source":
                raise AttentionError("region_inspection_requires_full_parent")
            if parent.id not in self.indexes:
                self.indexes[parent.id] = SourceIndex(parent)
            index = self.indexes[parent.id]
            ranked = index.rank(locator.query, locator.start_char)
            # Ranges are navigation, never independent evidence or semantic proof locations.
            result["located_regions"] = [{"parent_ref": parent.id, "start_char": index.regions[i][0],
                                           "end_char": index.regions[i][1]}
                                          for i in ranked[:self.limits.region_page_size]]
            result["matching_region_count"] = len(ranked)
        if action.catalog_window is not None:
            self.window = action.catalog_window
        return result

    def catalog(self) -> dict:
        rows = []
        for item in self.materials.values():
            row = asdict(item)
            del row["content"]
            rows.append({**row, "characters": len(item.content), "exposed": item.id in self.exposed,
                         "active": item.id in self.active})
        rows.extend({**row, "source_id": self.source_ids.get(row["url"])} for row in self.navigation.values())
        query = self.window.query.casefold()
        matching = [row for row in rows if not query or query in " ".join(
            str(row.get(key, "")) for key in ("id", "source_id", "title", "url")).casefold()]
        offset = self.window.offset
        return {"navigation_only": True, "known_count": len(rows), "matching_count": len(matching),
                "offset": offset, "next_offset": offset + self.limits.catalog_page_size
                if offset + self.limits.catalog_page_size < len(matching) else None,
                "items": matching[offset:offset + self.limits.catalog_page_size]}
