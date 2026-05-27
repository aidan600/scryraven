from core.useful_content import evaluate_useful_content


def test_evaluate_useful_content_long_structured_true() -> None:
    line = (
        "### Findings\n\n"
        "Unit costs were **10-14 cents** per ASM with citations [[1]](https://example.com/x).\n"
    )
    text = line * 8
    ok, reason = evaluate_useful_content(text)
    assert ok is True
    assert "word_count" in reason


def test_evaluate_useful_content_thin_false() -> None:
    ok, reason = evaluate_useful_content("Sorry — not much here.")
    assert ok is False
    assert "thin" in reason or "low_substance" in reason


def test_evaluate_useful_content_refusal_medium_length_without_estimate_false() -> None:
    text = (
        "I couldn't find solid, current apples-to-apples data for MD-80 vs Boeing 777. "
        "The material discusses unrelated topics. "
        + ("Try narrowing your query with carrier names or DOT filings. " * 12)
    )
    ok, reason = evaluate_useful_content(text)
    assert ok is False
    assert "refusal" in reason


def test_evaluate_useful_content_refusal_with_model_derived_passes() -> None:
    filler = "Stage length and load factor dominate comparability; cabin density matters for seat-mile costs. " * 5
    text = (
        "I couldn't find sourced tables, but under declared assumptions the MODEL-DERIVED comparison "
        "suggests **12–18¢** vs **8–11¢** CASM proxies for narrowbody legacy vs twin-aisle on comparable routes.\n\n"
        + filler
    )
    ok, reason = evaluate_useful_content(text)
    assert ok is True
