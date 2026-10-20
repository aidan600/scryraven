"""Bounded Answer attention over the current session's immutable acquisitions.

This is an adapter to AcquisitionLibrary, not a second retrieval system. Only
local Read/Find are dispatched; navigation never creates citation membership.
"""
from __future__ import annotations

import json
from hashlib import sha256
from time import monotonic

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core.exa_transport import DISCOVERY_CONTEXT_SAFETY_LIMIT
from scryraven.acquisition import AcquisitionError, AcquisitionLibrary

MAX_OPERATIONS = 12
CATALOG_PAGE = 24
PACKET_CHARACTERS = 32_000


class _Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Browse(_Arguments):
    offset: int = Field(ge=0)


class Find(_Arguments):
    query: str = Field(min_length=1, max_length=1000)
    scope: list[str] = Field(max_length=12)


class Read(_Arguments):
    target: str = Field(min_length=1, max_length=2048)
    focus: str = Field(max_length=1000)
    start_char: int | None = Field(ge=0)
    end_char: int | None = Field(ge=0)


ARGUMENTS = {"library_browse": Browse, "library_find": Find, "library_read": Read}
_DESCRIPTIONS = {
    "library_browse": "Browse a page of acquired session material metadata. Navigation only, not citable text. Use next_offset for more.",
    "library_find": "Find exact text in retained session material, including sources absent from initial Evidence. Lexical search; use scope=[] for all material or source/material/document IDs. Returns citable original text, never web search.",
    "library_read": "Read retained original material by material/source/document ID. Use focus for a bounded exact view of a large body, or paired start_char/end_char offsets. Null offsets use normal local reading. Only acquired text is available; highlights do not grant the full page. Never fetches externally.",
}
LIBRARY_TOOLS = [
    {"type": "function", "name": name, "description": _DESCRIPTIONS[name],
     "parameters": shape.model_json_schema(), "strict": True}
    for name, shape in ARGUMENTS.items()
]


def material_receipt(item):
    data = item.content.encode("utf-8")
    return {"id": item.id, "source_id": item.source_id, "parent_id": item.parent_id,
            "start_char": item.start_char, "end_char": item.end_char,
            "acquisition": item.acquisition, "characters": len(item.content),
            "utf8_bytes": len(data), "sha256": sha256(data).hexdigest()}


class AnswerLibrary:
    def __init__(self, library: AcquisitionLibrary, refs: list[str], *,
                 attention_characters: int = 128_000, emit=None, clock=monotonic):
        self.library, self.refs = library, refs
        self.remaining = attention_characters - sum(len(library.materials[r].content) for r in refs)
        self.operations = 0
        self.emit, self.clock = emit, clock

    def catalog(self, offset=0):
        # Stable acquisition order, not Research's attention order or selections.
        rows = [{"id": item.id, "source_id": item.source_id, "title": item.title[:320],
                 "acquisition": item.acquisition, "characters": len(item.content)}
                for item in self.library.acquisitions]
        rows.extend({"id": doc.document_id, "source_id": doc.document_id,
                     "title": doc.filename[:320], "acquisition": "user_document",
                     "characters": doc.text_character_count, "pages": doc.page_count,
                     "textless_page_count": doc.textless_page_count, "visual_analysis": False}
                    for doc in self.library.documents)
        return {"navigation_only": True, "total": len(rows),
                "entries": rows[offset:offset + CATALOG_PAGE],
                "next_offset": offset + CATALOG_PAGE if offset + CATALOG_PAGE < len(rows) else None,
                "operations_remaining": max(0, MAX_OPERATIONS - self.operations),
                "text_characters_remaining": max(0, self.remaining)}

    @staticmethod
    def _no_external():
        raise AcquisitionError("local_material_unavailable")

    def __call__(self, name, raw_arguments):
        started = self.clock()
        self.operations += 1
        args = None
        result = {"error": "invalid_tool_arguments"}
        if self.operations > MAX_OPERATIONS:
            result = {"error": "library_operation_limit"}
        else:
            try:
                if name not in ARGUMENTS or len(raw_arguments) > 12_000:
                    raise ValueError()
                args = ARGUMENTS[name].model_validate_json(raw_arguments).model_dump()
                if name == "library_find" and any(len(ref) > 2048 for ref in args["scope"]):
                    raise ValueError()
                result = self._execute(name, args)
            except (ValidationError, ValueError, TypeError):
                result = {"error": "invalid_tool_arguments"}
        evidence = result.get("evidence", [])
        if self.emit is not None:
            self.emit("answer_library_used", contract="answer", operation=name,
                      sequence=self.operations, code=result.get("error"), external=False,
                      duration_seconds=round(max(0, self.clock() - started), 6),
                      exposed=[material_receipt(self.library.materials[row["id"]]) for row in evidence],
                      returned_utf8_bytes=len(json.dumps(result, ensure_ascii=False).encode("utf-8")),
                      text_characters_remaining=max(0, self.remaining))
            self.emit("answer_library_result", source_body=True, contract="answer",
                      operation=name, sequence=self.operations, arguments=args, result=result)
        return result

    def _execute(self, name, args):
        if name == "library_browse":
            return self.catalog(args["offset"])
        if self.remaining <= 0:
            return {"error": "library_attention_limit"}
        request = {"kind": "find" if name == "library_find" else "read", **args, "mode": "local"}
        if name == "library_read" and args["start_char"] is not None and args["end_char"] is not None:
            if args["end_char"] - args["start_char"] > PACKET_CHARACTERS:
                return {"error": "range_exceeds_local_packet", "max_characters": PACKET_CHARACTERS}
        outcome = self.library.execute(request, before_external=self._no_external, clock=self.clock)
        if outcome["status"] == "error":
            return {"error": outcome["code"]}
        chosen, used = [], 0
        for ref in outcome["material_ids"]:
            item = self.library.materials[ref]
            # Highlights have no full-page coordinates. Keep an admitted large
            # excerpt whole instead of inventing a source-contiguous view or
            # making legitimate acquired text permanently unreadable.
            if (not chosen and item.acquisition == "provider_highlights"
                    and PACKET_CHARACTERS < len(item.content) <= min(DISCOVERY_CONTEXT_SAFETY_LIMIT, self.remaining)):
                chosen.append(item)
                used = len(item.content)
                break
            if used + len(item.content) <= min(PACKET_CHARACTERS, self.remaining):
                chosen.append(item)
                used += len(item.content)
        self.remaining -= used  # Repeated returned text consumes attention too.
        self.refs.extend(item.id for item in chosen if item.id not in self.refs)
        return {"evidence": [item.material() for item in chosen],
                "omitted_material_ids": [r for r in outcome["material_ids"] if r not in {i.id for i in chosen}],
                "matching_region_count": outcome.get("matching_region_count"),
                "omitted_match_count": outcome.get("omitted_match_count"),
                "text_characters_returned": used,
                "text_characters_remaining": self.remaining,
                "operations_remaining": MAX_OPERATIONS - self.operations}
