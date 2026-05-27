"""Corpus quality state used by retrieval, logging, and KB review."""

from __future__ import annotations

from enum import Enum


class CorpusState(str, Enum):
    HEALTHY = "HEALTHY"
    OFF_TOPIC = "OFF_TOPIC"
    EMPTY_ENTITY = "EMPTY_ENTITY"
    ESTIMATE_FROM_PRIORS = "ESTIMATE_FROM_PRIORS"


WEAK_CORPUS_STATES = {
    CorpusState.OFF_TOPIC.value,
    CorpusState.ESTIMATE_FROM_PRIORS.value,
}


def classify_corpus_state(
    *,
    empty_entity: bool,
    utilization_rate: float | None,
    utilization_threshold: float,
    estimate_from_priors: bool = False,
) -> CorpusState:
    if estimate_from_priors:
        return CorpusState.ESTIMATE_FROM_PRIORS
    if empty_entity:
        return CorpusState.EMPTY_ENTITY
    if utilization_rate is not None and utilization_rate < utilization_threshold:
        return CorpusState.OFF_TOPIC
    return CorpusState.HEALTHY


def is_weak_corpus_state(state: CorpusState | str | None) -> bool:
    value = state.value if isinstance(state, CorpusState) else str(state or "")
    return value in WEAK_CORPUS_STATES
