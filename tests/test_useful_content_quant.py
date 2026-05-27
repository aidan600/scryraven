"""Quant/comparison-aware useful_content rules (Phase B1 M1.1)."""

from core.review_flags import compute_review_flags, should_auto_review
from core.useful_content import evaluate_useful_content


def test_quant_long_refusal_without_numbers_false() -> None:
    text = (
        "I couldn't find solid, current apples-to-apples data for MD-80 vs Boeing 777 cost per passenger mile. "
        "The material discusses unrelated topics such as cabin ventilation and generic fleet commentary without "
        "airline-specific operating economics. Try narrowing with carrier filings or DOT Form Forty-One context. "
        + ("More precise carrier-level disclosures would be needed for a defensible comparison. " * 14)
    )
    ok, reason = evaluate_useful_content(
        text,
        query_type="quantitative_comparison",
        report_type="quantitative_comparison",
    )
    assert ok is False
    assert reason == "quant_query_missing_numeric_signal"


def test_quant_with_numeric_signal_true() -> None:
    text = (
        "### Comparison\n\n"
        "On a modeled basis, **USD 0.1018** per passenger-mile (MD-80 proxy) vs **USD 0.0981** (777-family proxy) "
        "at 85% load and 2,000 statute miles, with explicit uncertainty bands.\n\n"
        + ("Sources discuss stage length and fuel as primary drivers; cite operating cost literature. " * 8)
    )
    ok, reason = evaluate_useful_content(
        text,
        query_type="comparison",
        report_type="general_research",
    )
    assert ok is True
    assert "word_count" in reason


def test_non_quant_preserves_long_refusal_behavior() -> None:
    text = (
        "I couldn't find solid, current apples-to-apples data for MD-80 vs Boeing 777. "
        "The material discusses unrelated topics. "
        + ("Try narrowing your query with carrier names or DOT filings. " * 12)
    )
    ok, reason = evaluate_useful_content(text)
    assert ok is False
    assert "refusal" in reason


def test_quant_year_only_does_not_count_as_numeric_signal() -> None:
    text = (
        "As of May 2026, I cannot verify aircraft-specific cost per passenger mile from the supplied evidence; "
        "the retrieval set appears off-topic for airline unit economics."
        + (" The discussion stays qualitative without carrier-level numeric disclosures. " * 10)
    )
    ok, reason = evaluate_useful_content(
        text,
        query_type="quantitative_comparison",
        report_type="cost_analysis",
    )
    assert ok is False
    assert reason == "quant_query_missing_numeric_signal"


def test_quant_missing_exact_metric_non_answer_without_method_is_low_utility() -> None:
    text = (
        "I could not find an exact cost per passenger mile comparison for the requested aircraft "
        "in the retrieved material. The available snippets mostly discuss generic aircraft specifications, "
        "fleet history, and cabin layout. Without direct source coverage, I would treat any comparison as "
        "unsupported. A better answer would need direct airline operating economics evidence for each aircraft. "
        + ("The current evidence does not establish the requested metric for either aircraft. " * 10)
    )

    assert "](http" not in text
    assert "|" not in text
    assert "/" not in text
    assert "assumption" not in text.lower()
    assert "formula" not in text.lower()
    assert "search" not in text.lower()

    ok, reason = evaluate_useful_content(
        text,
        query_type="quantitative_comparison",
        report_type="quantitative_comparison",
    )
    assert ok is False
    assert reason == "quant_query_missing_numeric_signal"


def test_quant_missing_numeric_signal_is_review_worthy_after_large_retrieval() -> None:
    query = "cost per passenger mile of an MD-80 vs 777-300ER"
    text = (
        "I could not find an exact cost per passenger mile comparison for the requested aircraft. "
        + ("The retrieved corpus does not provide direct metric evidence. " * 8)
    )
    ok, _reason = evaluate_useful_content(
        text,
        query_type="quantitative_comparison",
        report_type="quantitative_comparison",
    )
    flags = compute_review_flags(
        {
            "corpus_state": "HEALTHY",
            "query_preview": query,
            "total_chunks_embedded": 60,
            "final_output_preview": text,
            "useful_content": ok,
        },
        {},
    )

    assert ok is False
    assert flags.synth_declined_with_evidence is True
    assert should_auto_review(flags) is True
