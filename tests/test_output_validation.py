"""Unit tests for core/output_validation.py."""

from __future__ import annotations

from core.output_validation import enforce_table_width, max_table_cols, stream_apply_table_width


def test_max_table_cols_detects_wide_row() -> None:
    md = "| A | B | C | D | E | F |\n| --- | --- | --- | --- | --- | --- |\n| a | b | c | d | e | f |\n"
    assert max_table_cols(md) == 6


def test_max_table_cols_ignores_separator() -> None:
    md = "| h1 | h2 |\n| --- | --- |\n| a | b |\n"
    assert max_table_cols(md) == 2


def test_max_table_cols_no_table() -> None:
    assert max_table_cols("Just prose\n\n## heading\n") == 0


def test_enforce_table_width_collapses_six_col_table() -> None:
    six = (
        "| Entity | A | B | C | D | E |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| Q1 | 1 | 2 | 3 | 4 | 5 |\n"
    )
    out = enforce_table_width(six, max_cols=4)
    assert max_table_cols(out) <= 4
    assert "split for readability" in out.lower() or "wide markdown" in out.lower()


def test_enforce_table_width_preserves_narrow_table() -> None:
    t = "| a | b | c |\n| --- | --- | --- |\n| 1 | 2 | 3 |\n"
    out = enforce_table_width(t, max_cols=4)
    assert max_table_cols(out) == max_table_cols(t) == 3


def test_enforce_table_width_preserves_inline_citations_in_collapsed_cells() -> None:
    """Wide-table collapse keeps cell text including pseudo-citations like [web:3]."""
    md = (
        "| Aircraft | Unit cost | Context | Stage length | Notes |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| MD-80 | 10–14 [web:3] | short-haul | 800 mi | DOT sample |\n"
    )
    out = enforce_table_width(md, max_cols=4)
    assert "10–14" in out
    assert "[web:3]" in out
    assert max_table_cols(out) <= 4


def test_stream_apply_table_width_yields_enforced_string() -> None:
    def gen():
        yield "| a | b | c | d | e |\n"
        yield "| - | - | - | - | - |\n"
        yield "| 1 | 2 | 3 | 4 | 5 |\n"

    out = list(stream_apply_table_width(gen(), max_cols=4))
    assert len(out) == 1
    assert max_table_cols(out[0]) <= 4
