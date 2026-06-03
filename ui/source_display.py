"""Pure source-card and evidence-display helpers for Streamlit pages."""

from __future__ import annotations

from typing import Any


def _safe_display_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        return " ".join(str(value).split())
    except Exception:
        return ""


def _short_preview(passage: dict[str, Any], *, max_chars: int = 220) -> str:
    raw = (
        passage.get("text")
        or passage.get("snippet")
        or passage.get("raw_content")
        or ""
    )
    text = _safe_display_value(raw)
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def _truncate_display_value(value: Any, *, max_chars: int) -> str:
    text = _safe_display_value(value)
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def _evidence_sort_key(indexed_passage: tuple[int, Any]) -> tuple[int, float, int]:
    index, passage = indexed_passage
    if not isinstance(passage, dict):
        return (1, 0.0, index)
    source_id = passage.get("source_id")
    if isinstance(source_id, (int, float)):
        return (0, float(source_id), index)
    return (1, 0.0, index)


def _source_chip_groups(top_passages: Any) -> list[dict[str, Any]]:
    if not isinstance(top_passages, list):
        return []

    groups_by_source: dict[Any, dict[str, Any]] = {}
    for index, passage in sorted(enumerate(top_passages), key=_evidence_sort_key):
        if not isinstance(passage, dict):
            continue

        raw_source_id = _safe_display_value(passage.get("source_id"))
        source_id = raw_source_id or "?"
        title = _safe_display_value(passage.get("title"))
        domain = _safe_display_value(passage.get("domain"))
        url = _safe_display_value(passage.get("url"))
        preview = _short_preview(passage, max_chars=320)
        grouping_key = raw_source_id or url or index

        group = groups_by_source.get(grouping_key)
        if group is None:
            groups_by_source[grouping_key] = {
                "source_id": source_id,
                "title": title or "Untitled",
                "domain": domain,
                "url": url,
                "preview": preview,
                "chunk_count": 1,
            }
            continue

        group["chunk_count"] += 1
        if group["title"] == "Untitled" and title:
            group["title"] = title
        if not group["domain"] and domain:
            group["domain"] = domain
        if not group["url"] and url:
            group["url"] = url
        if not group["preview"] and preview:
            group["preview"] = preview

    groups = list(groups_by_source.values())
    for group in groups:
        label_text = group.get("domain") or group.get("title") or "Untitled"
        group["label"] = _truncate_display_value(
            f"[{group['source_id']}] {label_text}",
            max_chars=42,
        )
    return groups


def _evidence_provenance_rows(top_passages: Any) -> list[dict[str, str]]:
    if not isinstance(top_passages, list):
        return []

    rows: list[dict[str, str]] = []
    for _index, passage in sorted(enumerate(top_passages), key=_evidence_sort_key):
        if not isinstance(passage, dict):
            continue
        rows.append(
            {
                "Source": _safe_display_value(passage.get("source_id")),
                "Title": _safe_display_value(passage.get("title")),
                "Domain": _safe_display_value(passage.get("domain")),
                "URL": _safe_display_value(passage.get("url")),
                "Preview": _short_preview(passage),
            }
        )
    return rows


def _render_source_chip_details(st: Any, group: dict[str, Any]) -> None:
    st.markdown(f"**{group.get('title') or 'Untitled'}**")
    st.caption(f"Source: {group.get('source_id') or '?'}")
    st.caption(f"Domain: {group.get('domain') or 'N/A'}")
    st.caption(f"URL: {group.get('url') or 'N/A'}")
    if group.get("chunk_count", 0) > 1:
        st.caption(f"Chunks: {group['chunk_count']}")
    preview = group.get("preview") or ""
    if preview:
        st.write(preview)


def _render_source_chip_strip(st: Any, top_passages: Any) -> None:
    groups = _source_chip_groups(top_passages)
    if not groups:
        return

    st.caption("Sources")
    for row_start in range(0, len(groups), 4):
        row_groups = groups[row_start : row_start + 4]
        columns = st.columns(len(row_groups))
        for column, group in zip(columns, row_groups):
            with column:
                if hasattr(st, "popover"):
                    with st.popover(group["label"]):
                        _render_source_chip_details(st, group)
                else:
                    with st.expander(group["label"], expanded=False):
                        _render_source_chip_details(st, group)
