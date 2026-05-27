"""Tests for inferred source time signals (``core/source_recency.py``)."""

from __future__ import annotations

from core.source_recency import (
    build_recency_author_notes,
    current_year_from_banner,
    infer_year_span,
)


def test_infer_year_span_empty() -> None:
    assert infer_year_span([]) == (None, None)


def test_infer_year_span_from_titles() -> None:
    passages = [
        {"title": "Breaking: vote scheduled for March 2025", "text": "Body text"},
        {"title": "Older recap from 2019", "text": ""},
    ]
    assert infer_year_span(passages) == (2019, 2025)


def test_current_year_from_banner() -> None:
    assert current_year_from_banner("May 04, 2026") == 2026


def test_build_recency_stale_for_latest_query() -> None:
    passages = [{"title": "News from 2024 only", "text": "x"}]
    notes, stale = build_recency_author_notes(
        passages,
        query="latest controversy today",
        intent="news",
        query_type="news",
        current_date="May 04, 2026",
    )
    assert stale is True
    assert "2024" in notes
    assert "TEMPORAL CALIBRATION" in notes


def test_build_recency_no_stale_when_recent_year_in_passages() -> None:
    passages = [{"title": "Update April 2026", "text": ""}]
    notes, stale = build_recency_author_notes(
        passages,
        query="latest news",
        intent="news",
        query_type="news",
        current_date="May 04, 2026",
    )
    assert stale is False
    assert "2026" in notes
