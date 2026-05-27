"""Post-process model markdown for display constraints (table width, etc.)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from typing import Any


def max_table_cols(markdown: str) -> int:
    """Maximum pipe-column count across markdown table rows (excludes separator rows)."""
    sep = re.compile(r"^\s*\|[-:\s|]+\|\s*$")
    max_cols = 0
    for line in markdown.splitlines():
        if not line.strip().startswith("|"):
            continue
        if sep.match(line):
            continue
        # Non-separator data/header row
        max_cols = max(max_cols, line.count("|") - 1)
    return max_cols


def _separator_row(line: str) -> bool:
    return bool(re.match(r"^\s*\|[-:\s|]+\|\s*$", line))


def _parse_pipe_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _collapse_wide_table_block(lines: list[str], max_cols: int) -> list[str]:
    rows: list[list[str]] = []
    for line in lines:
        if _separator_row(line):
            continue
        cells = _parse_pipe_row(line)
        if cells:
            rows.append(cells)
    if not rows:
        return lines

    header = rows[0]
    body = rows[1:]
    banner = f"_*(Wide markdown table split for readability; at most {max_cols} columns per line.)*_"
    out: list[str] = ["", banner, ""]

    if not body:
        for i in range(0, len(header), max_cols):
            chunk = header[i : i + max_cols]
            out.append("- " + " · ".join(chunk))
        out.append("")
        return out

    for row in body:
        while len(row) < len(header):
            row.append("")
        for start in range(0, len(header), max_cols):
            stop = min(start + max_cols, len(header))
            parts: list[str] = []
            for j in range(start, stop):
                label = header[j] if j < len(header) else f"col{j + 1}"
                val = row[j] if j < len(row) else ""
                parts.append(f"**{label}**: {val}")
            out.append("- " + " · ".join(parts))
        out.append("")
    return out


def enforce_table_width(markdown: str, max_cols: int = 4) -> str:
    """
    Collapse markdown tables wider than max_cols into bullet lines (≤ max_cols labeled fields per bullet).
    Safety net when the model ignores CHAT_FOLLOWUP_FORMAT_RULES.
    """
    if max_cols < 1:
        return markdown

    lines = markdown.splitlines()
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|"):
            block_start = i
            while i < len(lines) and lines[i].strip().startswith("|"):
                i += 1
            block = lines[block_start:i]
            wide = 0
            for bl in block:
                if not _separator_row(bl) and bl.strip().startswith("|"):
                    wide = max(wide, bl.count("|") - 1)
            if wide > max_cols:
                result.extend(_collapse_wide_table_block(block, max_cols))
            else:
                result.extend(block)
        else:
            result.append(line)
            i += 1
    return "\n".join(result)


def stream_apply_table_width(stream: Iterable[Any], max_cols: int = 4) -> Iterator[str]:
    """
    Consume a token/chunk stream, then yield a single enforced markdown string
    (streaming trade-off: width fix needs full text for table parsing).
    """
    parts: list[str] = []
    for chunk in stream:
        if chunk:
            parts.append(chunk if isinstance(chunk, str) else str(chunk))
    full = "".join(parts)
    fixed = enforce_table_width(full, max_cols=max_cols)
    yield fixed
