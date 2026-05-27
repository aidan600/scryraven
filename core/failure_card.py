"""Failure-card copy and visibility rules (Phase A5) — no Streamlit imports."""

from __future__ import annotations

from core.corpus_state import CorpusState


def normalize_force_corpus_state(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip().upper()
    if s in {e.value for e in CorpusState}:
        return s
    return CorpusState.ESTIMATE_FROM_PRIORS.value


def failure_card_should_show(
    *,
    corpus_state: str,
    retrieval_retry_used: bool,
    empty_entity: bool,
    scrutineer_high_count: int,
    useful_content: bool,
) -> bool:
    return (
        corpus_state != CorpusState.HEALTHY.value
        or retrieval_retry_used
        or empty_entity
        or int(scrutineer_high_count or 0) > 0
        or useful_content is False
    )


def failure_card_reason(
    *,
    corpus_state: str,
    retrieval_retry_used: bool,
    empty_entity: bool,
    scrutineer_high_count: int,
    useful_content: bool,
    chunks_with_entity: int,
    total_chunks_embedded: int,
) -> str:
    if empty_entity:
        return (
            "Couldn't extract a primary entity from the query. "
            "Try naming the subject more directly."
        )
    if corpus_state == CorpusState.ESTIMATE_FROM_PRIORS.value:
        return (
            "Limited source coverage — answer below uses model knowledge with uncertainty bounds."
        )
    if corpus_state == CorpusState.OFF_TOPIC.value:
        return (
            f"Source coverage was off-topic ({chunks_with_entity}/"
            f"{total_chunks_embedded} chunks mentioned the topic)."
        )
    if retrieval_retry_used:
        return "Retrieval automatically retried with disambiguated queries."
    if int(scrutineer_high_count or 0) > 0:
        return (
            f"Audit raised {int(scrutineer_high_count)} high-severity flags; "
            "report includes hedging."
        )
    if useful_content is False:
        return (
            "Author output flagged as low-substance — try a different mode or refine the query."
        )
    return ""


def failure_card_show_force_keyword(
    *,
    corpus_state: str,
    first_pass_providers: list[str],
) -> bool:
    if corpus_state in {CorpusState.OFF_TOPIC.value, CorpusState.ESTIMATE_FROM_PRIORS.value}:
        return True
    if not first_pass_providers:
        return True
    return "tavily" not in first_pass_providers


def failure_card_show_estimate(*, corpus_state: str) -> bool:
    return corpus_state in {CorpusState.OFF_TOPIC.value, CorpusState.EMPTY_ENTITY.value}
