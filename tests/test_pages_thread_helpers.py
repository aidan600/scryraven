from __future__ import annotations

from copy import deepcopy

from ui.source_display import (
    _evidence_provenance_rows,
    _render_source_chip_details,
    _source_chip_groups,
)


class _FakeSt:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def caption(self, value: str) -> None:
        self.calls.append(("caption", value))

    def markdown(self, value: str) -> None:
        self.calls.append(("markdown", value))

    def write(self, value: str) -> None:
        self.calls.append(("write", value))


def test_source_chip_groups_sort_distinct_sources_by_source_id() -> None:
    passages = [
        {
            "source_id": 3,
            "title": "Third source",
            "domain": "third.example",
            "credibility": 2,
            "url": "https://third.example/report",
            "text": "Third source preview.",
        },
        {
            "source_id": 1,
            "title": "First source",
            "domain": "first.example",
            "credibility": 3,
            "url": "https://first.example/report",
            "text": "First source preview.",
        },
        {
            "source_id": 2,
            "title": "Second source",
            "domain": "second.example",
            "credibility": 1,
            "url": "https://second.example/report",
            "text": "Second source preview.",
        },
    ]

    groups = _source_chip_groups(passages)

    assert [g["source_id"] for g in groups] == ["1", "2", "3"]
    assert [g["chunk_count"] for g in groups] == [1, 1, 1]
    assert [g["label"] for g in groups] == [
        "[1] first.example",
        "[2] second.example",
        "[3] third.example",
    ]


def test_source_chip_groups_group_duplicates_without_changing_provenance_rows() -> None:
    passages = [
        {
            "source_id": 2,
            "title": "First chunk title",
            "domain": "example.com",
            "credibility": 2,
            "url": "https://example.com/report",
            "text": "First chunk text.",
        },
        {
            "source_id": 2,
            "title": "Second chunk title",
            "domain": "example.com",
            "credibility": 2,
            "url": "https://example.com/report",
            "text": "Second chunk text.",
        },
    ]

    groups = _source_chip_groups(passages)
    rows = _evidence_provenance_rows(passages)

    assert len(groups) == 1
    assert groups[0]["source_id"] == "2"
    assert groups[0]["chunk_count"] == 2
    assert groups[0]["label"] == "[2] example.com"
    assert len(rows) == 2
    assert [r["Title"] for r in rows] == ["First chunk title", "Second chunk title"]


def test_source_chip_groups_do_not_merge_missing_source_ids_with_different_urls() -> None:
    passages = [
        {
            "title": "First missing source id",
            "domain": "first.example",
            "url": "https://first.example/report",
            "text": "First preview.",
        },
        {
            "title": "Second missing source id",
            "domain": "second.example",
            "url": "https://second.example/report",
            "text": "Second preview.",
        },
    ]

    groups = _source_chip_groups(passages)

    assert len(groups) == 2
    assert [g["source_id"] for g in groups] == ["?", "?"]
    assert [g["chunk_count"] for g in groups] == [1, 1]
    assert [g["label"] for g in groups] == [
        "[?] first.example",
        "[?] second.example",
    ]


def test_thread_public_surfaces_omit_zero_missing_and_none_credibility() -> None:
    passages = [
        {
            "source_id": 1,
            "title": "Zero score",
            "domain": "zero.example",
            "credibility": 0,
            "url": "https://zero.example/report",
            "text": "Zero score preview.",
        },
        {
            "source_id": 2,
            "title": "None score",
            "domain": "none.example",
            "credibility": None,
            "url": "https://none.example/report",
            "text": "None score preview.",
        },
        {
            "source_id": 3,
            "title": "Missing score",
            "domain": "missing.example",
            "url": "https://missing.example/report",
            "text": "Missing score preview.",
        },
    ]

    groups = _source_chip_groups(passages)
    rows = _evidence_provenance_rows(passages)

    assert all("credibility" not in group for group in groups)
    assert all("Credibility" not in row for row in rows)

    st = _FakeSt()
    for group in groups:
        _render_source_chip_details(st, group)

    captions = [value for kind, value in st.calls if kind == "caption"]
    assert "Credibility: 0" not in captions
    assert not any(value.startswith("Credibility:") for value in captions)


def test_thread_public_surfaces_omit_nonzero_credibility() -> None:
    passages = [
        {
            "source_id": 1,
            "title": "Positive score",
            "domain": "positive.example",
            "credibility": 3,
            "url": "https://positive.example/report",
            "text": "Positive score preview.",
        },
        {
            "source_id": 2,
            "title": "Negative score",
            "domain": "negative.example",
            "credibility": -1,
            "url": "https://negative.example/report",
            "text": "Negative score preview.",
        },
    ]

    groups = _source_chip_groups(passages)
    rows = _evidence_provenance_rows(passages)

    assert all("credibility" not in group for group in groups)
    assert all("Credibility" not in row for row in rows)

    st = _FakeSt()
    for group in groups:
        _render_source_chip_details(st, group)

    captions = [value for kind, value in st.calls if kind == "caption"]
    assert "Credibility: 3" not in captions
    assert "Credibility: -1" not in captions
    assert not any(value.startswith("Credibility:") for value in captions)


def test_source_chip_groups_handle_empty_and_malformed_inputs() -> None:
    malformed = [
        "not a passage",
        {
            "title": ["Nested", "title"],
            "text": "x" * 400,
        },
    ]

    assert _source_chip_groups([]) == []
    assert _source_chip_groups(None) == []

    groups = _source_chip_groups(malformed)

    assert len(groups) == 1
    assert groups[0]["source_id"] == "?"
    assert groups[0]["title"] == "['Nested', 'title']"
    assert groups[0]["domain"] == ""
    assert "credibility" not in groups[0]
    assert groups[0]["url"] == ""
    assert groups[0]["chunk_count"] == 1
    assert groups[0]["label"].startswith("[?] ['Nested',")
    assert len(groups[0]["preview"]) <= 320
    assert groups[0]["preview"].endswith("...")


def test_source_chip_groups_do_not_mutate_input() -> None:
    passages = [
        {
            "source_id": 1,
            "title": "First source",
            "domain": "source.example",
            "credibility": 3,
            "url": "https://source.example/article",
            "text": "First source preview text.",
        },
        {
            "title": "No source id",
            "text": "Fallback preview text.",
        },
    ]
    before = deepcopy(passages)

    _source_chip_groups(passages)

    assert passages == before


def test_evidence_provenance_rows_preserve_duplicate_url_chunks() -> None:
    passages = [
        {
            "source_id": 2,
            "title": "Second chunk title",
            "domain": "example.com",
            "credibility": 2,
            "url": "https://example.com/report",
            "text": "Second chunk text with enough detail for a preview.",
        },
        {
            "source_id": 1,
            "title": "First source",
            "domain": "source.example",
            "credibility": 3,
            "url": "https://source.example/article",
            "text": "First source preview text.",
        },
        {
            "source_id": 2,
            "title": "Same URL, useful second chunk",
            "domain": "example.com",
            "credibility": 2,
            "url": "https://example.com/report",
            "text": "Distinct passage text from the same source URL.",
        },
    ]
    before = deepcopy(passages)

    rows = _evidence_provenance_rows(passages)

    assert len(rows) == 3
    assert [r["Source"] for r in rows] == ["1", "2", "2"]
    assert rows[0] == {
        "Source": "1",
        "Title": "First source",
        "Domain": "source.example",
        "URL": "https://source.example/article",
        "Preview": "First source preview text.",
    }
    assert rows[1]["Title"] == "Second chunk title"
    assert rows[2]["Title"] == "Same URL, useful second chunk"
    assert rows[1]["URL"] == rows[2]["URL"] == "https://example.com/report"
    assert passages == before


def test_evidence_provenance_rows_handle_empty_and_malformed_inputs() -> None:
    malformed = [
        "not a passage",
        {
            "title": ["Nested", "title"],
            "text": "x" * 260,
        },
    ]
    before = deepcopy(malformed)

    assert _evidence_provenance_rows([]) == []
    assert _evidence_provenance_rows(None) == []

    rows = _evidence_provenance_rows(malformed)

    assert len(rows) == 1
    assert rows[0]["Source"] == ""
    assert rows[0]["Title"] == "['Nested', 'title']"
    assert rows[0]["Domain"] == ""
    assert "Credibility" not in rows[0]
    assert rows[0]["URL"] == ""
    assert len(rows[0]["Preview"]) <= 220
    assert rows[0]["Preview"].endswith("...")
    assert malformed == before
