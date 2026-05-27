"""Phase A3: refusal-with-evidence KB flag behavior."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.review_flags import (
    REFUSAL_PATTERNS,
    ReviewFlags,
    compute_review_flags,
    review_score,
    should_auto_review,
)


def _minimal_execution(**kwargs: object) -> dict:
    base = {
        "queries_iter1": [],
        "queries_iter2": [],
        "complexity": "high",
        "intent": "general",
        "pass_providers": [["tavily"]],
        "scout_fired": False,
        "synth_was_insufficient": False,
        "supplemental_ran": False,
        "delta_urls_supplemental": 0,
        "scrutineer_high_flags": 0,
    }
    base.update(kwargs)
    return base


def test_refusal_patterns_exact_spec_strings() -> None:
    expected = [
        r"couldn'?t find (solid|reliable|on-point|specific)",
        r"I cannot verify",
        r"unable to (verify|locate|find|confirm)",
        r"no reliable, sourced basis",
        r"the (provided|available|supplied) (evidence|sources|material) (do(es)? not|cannot|fail)",
        r"I (don't|do not) have (enough|sufficient) (information|evidence|sources)",
        r"there is no (reliable|verified|sourced) (basis|information)",
        r"the source set (does not|fails to)",
    ]
    assert REFUSAL_PATTERNS == expected


def test_synth_declined_not_fired_when_off_topic_refusal_expected() -> None:
    ex = _minimal_execution(
        total_chunks_embedded=221,
        corpus_state="OFF_TOPIC",
        useful_content=True,
        final_output_preview=(
            "I couldn't find solid on-point sources for MD-80 vs 777-300 CASM in one table. "
            "The retrieved pages discuss unrelated fleet news."
        ),
    )
    f = compute_review_flags(ex, {})
    assert f.synth_declined_with_evidence is False


def test_synth_declined_fires_estimate_from_priors_but_refused() -> None:
    ex = _minimal_execution(
        total_chunks_embedded=236,
        corpus_state="ESTIMATE_FROM_PRIORS",
        useful_content=True,
        final_output_preview=(
            "I couldn't find solid, current apples-to-apples data for MD-80 vs Boeing 777 cost per passenger mile."
        ),
    )
    f = compute_review_flags(ex, {})
    assert f.synth_declined_with_evidence is True


def test_synth_declined_not_fired_when_chunk_count_low() -> None:
    ex = _minimal_execution(
        total_chunks_embedded=12,
        corpus_state="OFF_TOPIC",
        useful_content=True,
        final_output_preview="I couldn't find solid sources so I cannot answer.",
    )
    f = compute_review_flags(ex, {})
    assert f.synth_declined_with_evidence is False


def test_synth_declined_fires_when_useful_content_false_despite_no_regex() -> None:
    ex = _minimal_execution(
        total_chunks_embedded=80,
        corpus_state="HEALTHY",
        useful_content=False,
        final_output_preview="Short. " * 5,
    )
    f = compute_review_flags(ex, {})
    assert f.synth_declined_with_evidence is True


def test_should_auto_review_true_solo_synth_declined() -> None:
    f = ReviewFlags(synth_declined_with_evidence=True)
    assert review_score(f) == 0.55
    assert should_auto_review(f) is True


def test_healthy_long_answer_not_flagged() -> None:
    ex = _minimal_execution(
        total_chunks_embedded=120,
        corpus_state="HEALTHY",
        useful_content=True,
        final_output_preview=(
            "### Comparison\n\n"
            "Per ASM, narrowbody legacy types often clustered around **10–14¢** in comparable-era disclosures [[1]](https://example.com/a). "
            "Widebody twin-aisle economics differ by mission profile; treat stage length as the primary driver."
        ),
    )
    f = compute_review_flags(ex, {})
    assert f.synth_declined_with_evidence is False
