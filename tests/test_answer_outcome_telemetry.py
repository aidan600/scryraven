"""Telemetry classification: displayable vs evidence-sufficient; KB weak-retrieval signal."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.answer_outcome import classify_answer_outcome
from core.corpus_state import CorpusState
from core.review_flags import compute_review_flags, review_score


def test_off_topic_safe_refusal_displayable_not_evidence_sufficient() -> None:
    report = (
        "I couldn't find solid on-point public sources for your question. "
        "The retrieved pages were off-topic relative to the main subject."
    )
    disp, ev_ok, ac = classify_answer_outcome(
        report,
        corpus_state=CorpusState.OFF_TOPIC.value,
        corpus_weak=True,
        useful_content=True,
        synth_was_insufficient=False,
        empty_entity=False,
    )
    assert disp is True
    assert ev_ok is False
    assert ac == "off_topic_retrieval"

    ex = {
        "corpus_state": CorpusState.OFF_TOPIC.value,
        "corpus_weak": True,
        "failure_card": {"show": True},
        "useful_content": True,
        "final_output_preview": report[:300],
        "total_chunks_embedded": 40,
        "complexity": "medium",
        "intent": "general",
        "pass_providers": [["tavily"]],
        "scout_fired": False,
        "synth_was_insufficient": False,
        "supplemental_ran": False,
        "delta_urls_supplemental": 0,
        "scrutineer_high_flags": 0,
    }
    flags = compute_review_flags(ex, {})
    assert flags.weak_retrieval_failure_card is True
    assert review_score(flags) >= 0.29


def test_healthy_long_unsourced_is_partial_not_evidence_sufficient() -> None:
    report = (
        "## Summary\n\n"
        "Acme Corp is a public company that operates in several markets. "
        "Industry observers have noted shifting competitive dynamics over the past several quarters. "
        "Management commentary in earnings calls has emphasized cost discipline and reinvestment. "
        "Analysts differ on near-term margin trajectory given macro uncertainty and input costs. "
        "This overview summarizes commonly discussed themes without tying claims to specific filings.\n\n"
        "## Next steps\n\n"
        "Consider reviewing primary disclosures for figures appropriate to your use case."
    )
    assert len(report.split()) >= 45
    disp, ev_ok, ac = classify_answer_outcome(
        report,
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        useful_content=True,
        synth_was_insufficient=False,
        empty_entity=False,
    )
    assert disp is True
    assert ev_ok is False
    assert ac == "partial_answer"


def test_strong_corpus_substantive_sourced_answer() -> None:
    report = (
        "## Summary\n\n"
        "Acme Corp reported revenue growth in Q3 per the filing.\n\n"
        "## Sources\n"
        "- [SEC filing](https://www.sec.gov/example)\n"
    )
    disp, ev_ok, ac = classify_answer_outcome(
        report,
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        useful_content=True,
        synth_was_insufficient=False,
        empty_entity=False,
    )
    assert disp is True
    assert ev_ok is True
    assert ac == "answered"


def test_healthy_sourced_no_reliable_evidence_is_not_evidence_sufficient() -> None:
    report = (
        "## Summary\n\n"
        "There is no reliable evidence in the retrieved material for the requested claim. "
        "The closest source is topic-adjacent background, but it does not establish the specific point.\n\n"
        "## Sources\n"
        "- [Background source](https://example.com/background)\n"
    )
    disp, ev_ok, ac = classify_answer_outcome(
        report,
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        useful_content=True,
        synth_was_insufficient=False,
        empty_entity=False,
    )
    assert disp is True
    assert ev_ok is False
    assert ac == "no_evidence_found"


def test_healthy_no_patch_notes_developer_quotes_or_stat_deltas_not_sufficient() -> None:
    report = (
        "## Finding\n\n"
        "The retrieved pages discuss the product, but no patch notes, developer quotes, or stat deltas "
        "support the requested numeric change forecast.\n\n"
        "## Sources\n"
        "- [Topic-adjacent source](https://example.com/topic)\n"
    )
    disp, ev_ok, ac = classify_answer_outcome(
        report,
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        useful_content=True,
        synth_was_insufficient=False,
        empty_entity=False,
    )
    assert disp is True
    assert ev_ok is False
    assert ac == "no_evidence_found"


def test_healthy_would_be_speculation_not_sufficient() -> None:
    report = (
        "## Bottom line\n\n"
        "The retrieved official page confirms the topic exists, but any numeric forecast would be "
        "model-derived speculation because the source does not provide the requested delta.\n\n"
        "## Sources\n"
        "- [Official page](https://example.com/official)\n"
    )
    disp, ev_ok, ac = classify_answer_outcome(
        report,
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        useful_content=True,
        synth_was_insufficient=False,
        empty_entity=False,
    )
    assert disp is True
    assert ev_ok is False
    assert ac == "no_evidence_found"


def test_empty_report_not_displayable() -> None:
    disp, ev_ok, ac = classify_answer_outcome(
        "   \n",
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        useful_content=False,
        synth_was_insufficient=False,
        empty_entity=False,
    )
    assert disp is False
    assert ev_ok is False
    assert ac == "no_evidence_found"
