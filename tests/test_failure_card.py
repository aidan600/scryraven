"""Tests for core/failure_card.py (Phase A5)."""

from __future__ import annotations

from core.corpus_state import CorpusState
from core.failure_card import (
    failure_card_reason,
    failure_card_should_show,
    failure_card_show_estimate,
    failure_card_show_force_keyword,
    normalize_force_corpus_state,
)


def test_normalize_force_invalid_falls_back_to_estimate() -> None:
    assert normalize_force_corpus_state("nope") == CorpusState.ESTIMATE_FROM_PRIORS.value
    assert normalize_force_corpus_state(CorpusState.HEALTHY.value) == CorpusState.HEALTHY.value


def test_should_show_trigger_sets() -> None:
    assert failure_card_should_show(
        corpus_state=CorpusState.HEALTHY.value,
        retrieval_retry_used=True,
        empty_entity=False,
        scrutineer_high_count=0,
        useful_content=True,
    )
    assert failure_card_should_show(
        corpus_state=CorpusState.OFF_TOPIC.value,
        retrieval_retry_used=False,
        empty_entity=False,
        scrutineer_high_count=0,
        useful_content=True,
    )
    assert not failure_card_should_show(
        corpus_state=CorpusState.HEALTHY.value,
        retrieval_retry_used=False,
        empty_entity=False,
        scrutineer_high_count=0,
        useful_content=True,
    )


def test_reason_priority_empty_entity_first() -> None:
    r = failure_card_reason(
        corpus_state=CorpusState.OFF_TOPIC.value,
        retrieval_retry_used=True,
        empty_entity=True,
        scrutineer_high_count=3,
        useful_content=False,
        chunks_with_entity=1,
        total_chunks_embedded=10,
    )
    assert "entity" in r.lower()


def test_show_force_keyword_when_no_tavily_in_first_pass() -> None:
    assert failure_card_show_force_keyword(
        corpus_state=CorpusState.HEALTHY.value,
        first_pass_providers=["exa", "linkup"],
    )


def test_show_estimate_for_empty_entity() -> None:
    assert failure_card_show_estimate(corpus_state=CorpusState.EMPTY_ENTITY.value)
    assert not failure_card_show_estimate(corpus_state=CorpusState.HEALTHY.value)
