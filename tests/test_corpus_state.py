"""Tier 1 tests for the Phase A corpus-state enum."""

from __future__ import annotations

from core.corpus_state import CorpusState, classify_corpus_state, is_weak_corpus_state


def test_corpus_state_exact_values_and_casing() -> None:
    assert [state.value for state in CorpusState] == [
        "HEALTHY",
        "OFF_TOPIC",
        "EMPTY_ENTITY",
        "ESTIMATE_FROM_PRIORS",
    ]


def test_classify_corpus_state_empty_entity_takes_precedence() -> None:
    state = classify_corpus_state(
        empty_entity=True,
        utilization_rate=0.0,
        utilization_threshold=0.25,
    )
    assert state is CorpusState.EMPTY_ENTITY


def test_classify_corpus_state_estimate_from_priors_takes_precedence() -> None:
    state = classify_corpus_state(
        empty_entity=True,
        utilization_rate=0.0,
        utilization_threshold=0.25,
        estimate_from_priors=True,
    )
    assert state is CorpusState.ESTIMATE_FROM_PRIORS


def test_classify_corpus_state_off_topic_after_low_utilization() -> None:
    state = classify_corpus_state(
        empty_entity=False,
        utilization_rate=0.10,
        utilization_threshold=0.25,
    )
    assert state is CorpusState.OFF_TOPIC
    assert is_weak_corpus_state(state) is True


def test_classify_corpus_state_low_util_with_estimate_flag_not_off_topic() -> None:
    state = classify_corpus_state(
        empty_entity=False,
        utilization_rate=0.10,
        utilization_threshold=0.25,
        estimate_from_priors=True,
    )
    assert state is CorpusState.ESTIMATE_FROM_PRIORS


def test_classify_corpus_state_returns_healthy_enum_when_entity_matches() -> None:
    state = classify_corpus_state(
        empty_entity=False,
        utilization_rate=0.50,
        utilization_threshold=0.25,
    )
    assert state is CorpusState.HEALTHY
    assert is_weak_corpus_state(state) is False


def test_empty_entity_is_not_treated_as_off_topic_weak_corpus() -> None:
    assert is_weak_corpus_state(CorpusState.EMPTY_ENTITY) is False
