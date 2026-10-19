"""Shared bounded SSE framing; completion authority belongs to the caller."""
from __future__ import annotations

import json
from itertools import chain

from .http import PlanError, failure


def _event_object(pairs):
    item = dict(pairs)
    if len(item) != len(pairs):
        raise ValueError("duplicate event key")
    return item


def _invalid_json_number(value):
    raise ValueError("non-JSON number")


def events(response, deadline, *, chunks=None):
    """Bounded Responses SSE framing, including BOM, CR/LF and multiline data.

    Byte-sized reads allow the total deadline/cancellation to be checked even on
    a slow trickling response, rather than only after a large buffer fills.
    """
    line, data, event_name = bytearray(), [], None
    total = event_size = 0
    first_line, skip_lf = True, False
    for chunk in response.iter_content(chunk_size=1) if chunks is None else chunks:
        deadline.left()
        total += len(chunk)
        if total > 32_000_000:
            raise PlanError("malformed_model_response", reason="stream_size_limit")
        for byte in chunk:
            if skip_lf and byte == 10:
                skip_lf = False
                continue
            skip_lf = byte == 13
            if byte not in {10, 13}:
                line.append(byte)
                if len(line) > 2_000_000:
                    raise PlanError("malformed_model_response", reason="event_size_limit")
                continue
            try:
                value = line.decode("utf-8")
            except UnicodeError:
                raise PlanError("malformed_model_response", reason="invalid_stream_encoding") from None
            event_size += len(line) + 1
            if event_size > 2_000_000:
                raise PlanError("malformed_model_response", reason="event_size_limit")
            line.clear()
            if first_line:
                value = value.removeprefix("\ufeff")
                first_line = False
            if not value:
                if data:
                    try:
                        item = json.loads("\n".join(data), object_pairs_hook=_event_object,
                                          parse_constant=_invalid_json_number)
                    except (ValueError, RecursionError):
                        raise PlanError("malformed_model_response", reason="invalid_stream_json") from None
                    kind = item.get("type") if isinstance(item, dict) else None
                    if not isinstance(kind, str) or not (kind.startswith("response.") or kind == "error") or (
                        event_name and kind != event_name
                    ):
                        raise PlanError("malformed_model_response", reason="invalid_stream_event")
                    yield item
                elif event_name:
                    raise PlanError("malformed_model_response", reason="invalid_stream_event")
                data, event_name, event_size = [], None, 0
            elif value.startswith("data:"):
                data.append(value[5:].removeprefix(" "))
            elif value == "data":
                data.append("")
            elif value.startswith("event:"):
                if event_name is not None:
                    raise PlanError("malformed_model_response", reason="invalid_stream_event")
                event_name = value[6:].removeprefix(" ")
            elif value.startswith(":") or value.partition(":")[0] in {"id", "retry"}:
                continue
            else:
                raise PlanError("malformed_model_response", reason="invalid_stream_field")
    raise PlanError("malformed_model_response", reason="stream_ended_without_completion")


def _nonstream_diagnostics(response, deadline, *, chunks=None):
    """Inspect at most 16 KiB in memory; return only fixed categories/codes."""
    content = bytearray()
    truncated = False
    for chunk in response.iter_content(chunk_size=4096) if chunks is None else chunks:
        deadline.left()
        remaining = 16_384 - len(content)
        content.extend(chunk[:remaining])
        if len(chunk) > remaining:
            truncated = True
            break
    prefix = content.lstrip().removeprefix(b"\xef\xbb\xbf").lower()
    category = "empty_body" if not prefix else (
        "sse_like_body" if prefix.startswith((b":", b"data:", b"event:", b"id:", b"retry:")) else
        "html_like_body" if prefix.startswith((b"<!doctype html", b"<html")) else
        "json_like_body" if prefix.startswith((b"{", b"[")) else "non_json_body"
    )
    if truncated:
        return {"response_category": category, "diagnostic_body_truncated": True}
    try:
        body = json.loads(content)
    except (ValueError, RecursionError):
        return {"response_category": "non_json_body" if category == "json_like_body" else category}
    # Reuse the existing allowlist; never copy error messages or response text.
    projection = failure(response.status_code, body).diagnostic
    return {
        **{key: projection[key] for key in ("provider_code", "param", "body_shape") if key in projection},
        "response_category": "json_" + projection["body_shape"],
    }


def _headerless_chunks(response, deadline, facts):
    """Sniff only framing; replay every byte to the ordinary event parser.

    A plausible prefix grants no completion authority. Non-SSE diagnostics have
    their own bound, independent of the event and total stream limits.
    """
    chunks = response.iter_content(chunk_size=1)
    prefix = bytearray()
    fields = (b":", b"data:", b"event:", b"id:", b"retry:")
    for chunk in chunks:
        deadline.left()
        prefix.extend(chunk)
        probe = bytes(prefix)
        if b"\xef\xbb\xbf".startswith(probe):
            continue
        probe = probe.removeprefix(b"\xef\xbb\xbf").lstrip(b"\r\n")
        if any(probe.startswith(field) for field in fields) or len(prefix) >= 16_384 and not probe:
            facts["response_category"] = "sse_like_body"
            return chain((bytes(prefix),), chunks)
        if not any(field.startswith(probe) for field in fields):
            break
    facts.update(_nonstream_diagnostics(response, deadline, chunks=chain((bytes(prefix),), chunks)))
    raise PlanError("malformed_model_response", reason="expected_event_stream")
