from ui.pages_sidebar import SIDEBAR_TITLE_LIMIT, _compact_sidebar_title


def test_compact_sidebar_title_collapses_whitespace() -> None:
    assert _compact_sidebar_title("  Aircraft\n\ncost   comparison  ") == "Aircraft cost comparison"


def test_compact_sidebar_title_truncates_long_titles() -> None:
    title = "x" * (SIDEBAR_TITLE_LIMIT + 20)
    compact = _compact_sidebar_title(title)

    assert len(compact) == SIDEBAR_TITLE_LIMIT
    assert compact.endswith("...")
