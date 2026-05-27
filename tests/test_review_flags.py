import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.review_flags import (
    ReviewFlags,
    compute_review_flags,
    jaccard_query_overlap,
    review_score,
    should_auto_review,
)


def test_score_zero_for_clean_run() -> None:
    f = ReviewFlags()
    assert review_score(f) == 0.0
    assert should_auto_review(f) is False


def test_hard_flag_override() -> None:
    f = ReviewFlags(
        synth_insufficient=True,
        low_user_rating=True,
    )
    assert should_auto_review(f) is True
    f2 = ReviewFlags(
        synth_insufficient=True,
        low_user_rating=True,
        query_redundancy=True,
    )
    # score alone might be high, but two hard flags already force True
    assert should_auto_review(f2) is True


def test_jaccard_identical_queries() -> None:
    a = ["foo bar baz"]
    b = ["foo bar baz"]
    assert jaccard_query_overlap(a, b) == 1.0


def test_jaccard_disjoint_queries() -> None:
    a = ["alpha beta"]
    b = ["gamma delta"]
    assert jaccard_query_overlap(a, b) == 0.0


def test_query_redundancy_flag() -> None:
    ex = {
        "queries_iter1": ["oil markets weekly", "sp500 weekly return"],
        "queries_iter2": ["oil markets weekly", "sp500 weekly return"],
        "total_chunks_embedded": 30,
        "complexity": "medium",
        "intent": "general",
        "pass_providers": [["tavily", "linkup"]],
        "scout_fired": False,
        "synth_was_insufficient": False,
        "supplemental_ran": False,
        "delta_urls_supplemental": 0,
        "scrutineer_high_flags": 0,
    }
    fb: dict = {}
    f = compute_review_flags(ex, fb)
    assert f.query_redundancy is True
