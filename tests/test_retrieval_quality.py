from core.retrieval_quality import _extract_retry_year


def test_extract_retry_year_long_date() -> None:
    assert _extract_retry_year("May 06, 2026") == "2026"


def test_extract_retry_year_iso_date() -> None:
    assert _extract_retry_year("2026-05-06") == "2026"


def test_extract_retry_year_none() -> None:
    assert _extract_retry_year(None) == ""


def test_extract_retry_year_empty_string() -> None:
    assert _extract_retry_year("") == ""


def test_extract_retry_year_missing_year() -> None:
    assert _extract_retry_year("next Tuesday in spring") == ""
