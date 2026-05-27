from __future__ import annotations

from core.followup import (
    MemorySearchResult,
    SynthesisResult,
    WebRetrievalResult,
    build_followup_diagnostics,
    build_source_card_parity_diagnostics,
    run_memory_search_and_evaluator,
)


def _memory(**overrides):
    values = {
        "sources": {},
        "next_source_id": 1,
        "conversation_history": "",
        "query_embedding": [],
        "existing_evidence_block": "",
        "needs_search": False,
        "followup_queries": [],
        "evaluator_parse_status": "parsed",
    }
    values.update(overrides)
    return MemorySearchResult(**values)


def _web(**overrides):
    values = {
        "sources": {},
        "next_source_id": 1,
        "new_passages": [],
        "new_evidence_block": "",
        "seen_urls": [],
        "collected_images": [],
        "search_ran": False,
        "error": None,
    }
    values.update(overrides)
    return WebRetrievalResult(**values)


def _synthesis(**overrides):
    values = {
        "answer": "ok",
        "prompt_used": "",
        "sources": {},
        "sources_text": "",
        "error": None,
    }
    values.update(overrides)
    return SynthesisResult(**values)


def _diagnostics(*, memory=None, web=None, synthesis=None, source_cards=None, prompt=None, answer_text=None):
    return build_followup_diagnostics(
        memory_result=memory or _memory(),
        web_result=web or _web(),
        synthesis_result=synthesis or _synthesis(),
        source_cards=[] if source_cards is None else source_cards,
        prompt=prompt,
        answer_text=answer_text,
    )


def test_followup_diagnostics_saved_context_sufficient() -> None:
    diagnostics = _diagnostics(
        memory=_memory(needs_search=False, followup_queries=[]),
        web=_web(search_ran=False),
    )

    assert diagnostics["needs_search"] is False
    assert diagnostics["search_ran"] is False
    assert diagnostics["query_count"] == 0
    assert diagnostics["followup_query_count"] == 0
    assert diagnostics["search_skip_reason"] == "existing_context_sufficient"
    assert diagnostics["followup_route_observed"] == "saved_context"
    assert diagnostics["followup_route_shadow"] == "saved_context"
    assert diagnostics["followup_route_reason"] == "observed_current_behavior"
    assert diagnostics["saved_context_sufficient"] is True
    assert diagnostics["freshness_cue_detected"] is False
    assert diagnostics["freshness_cue_type"] == "none"
    assert diagnostics["would_require_fresh_retrieval"] is False


def test_followup_diagnostics_fresh_retrieval() -> None:
    diagnostics = _diagnostics(
        memory=_memory(needs_search=True, followup_queries=["fresh synthetic support"]),
        web=_web(search_ran=True, new_passages=[{"url": "https://example.com/a"}]),
    )

    assert diagnostics["needs_search"] is True
    assert diagnostics["search_ran"] is True
    assert diagnostics["query_count"] == 1
    assert diagnostics["new_passage_count"] > 0
    assert diagnostics["queries_preview"] == ["fresh synthetic support"]
    assert diagnostics["search_skip_reason"] is None
    assert diagnostics["followup_route_observed"] == "fresh_retrieval"
    assert diagnostics["followup_route_shadow"] == "fresh_retrieval"


def test_followup_diagnostics_empty_retrieval_no_results() -> None:
    diagnostics = _diagnostics(
        memory=_memory(needs_search=True, followup_queries=["empty synthetic retrieval"]),
        web=_web(search_ran=True, new_passages=[]),
    )

    assert diagnostics["needs_search"] is True
    assert diagnostics["search_ran"] is True
    assert diagnostics["new_passage_count"] == 0
    assert diagnostics["no_results"] is True
    assert diagnostics["followup_route_observed"] == "no_results_fallback"
    assert diagnostics["followup_route_shadow"] == "weak_no_answer"


def test_followup_diagnostics_retrieval_error_preview() -> None:
    diagnostics = _diagnostics(
        memory=_memory(needs_search=True, followup_queries=["synthetic retrieval error"]),
        web=_web(search_ran=True, error="network down while retrieving follow-up evidence"),
    )

    assert diagnostics["search_ran"] is True
    assert diagnostics["retrieval_error"] is True
    assert diagnostics["retrieval_error_preview"] == "network down while retrieving follow-up evidence"
    assert diagnostics["no_results"] is False
    assert diagnostics["followup_route_observed"] == "retrieval_error_fallback"
    assert diagnostics["followup_route_shadow"] == "retrieval_error_fallback"


def test_followup_diagnostics_missing_followup_queries_skip_reason() -> None:
    diagnostics = _diagnostics(
        memory=_memory(needs_search=True, followup_queries=[]),
        web=_web(search_ran=False),
    )

    assert diagnostics["search_skip_reason"] == "missing_followup_queries"


def test_followup_diagnostics_source_card_count_and_synthesis_error() -> None:
    source_cards = [
        {"source_id": "1", "title": "A", "url": "https://example.com/a"},
        {"source_id": "2", "title": "B", "url": "https://example.com/b"},
    ]
    diagnostics = _diagnostics(
        synthesis=_synthesis(error="model unavailable"),
        source_cards=source_cards,
    )

    assert diagnostics["source_card_count"] == 2
    assert diagnostics["synthesis_error"] is True
    assert diagnostics["cards_from_error_response"] is True


def test_followup_diagnostics_latest_current_shadow_requires_fresh_without_route_change() -> None:
    diagnostics = _diagnostics(
        prompt="Is the saved conclusion still current, and what is the latest update?",
        memory=_memory(needs_search=False, followup_queries=[]),
        web=_web(search_ran=False),
    )

    assert diagnostics["needs_search"] is False
    assert diagnostics["search_ran"] is False
    assert diagnostics["followup_route_observed"] == "saved_context"
    assert diagnostics["followup_route_shadow"] == "fresh_retrieval"
    assert diagnostics["freshness_cue_detected"] is True
    assert diagnostics["freshness_cue_type"] == "latest"
    assert diagnostics["would_require_fresh_retrieval"] is True


def test_followup_diagnostics_formatting_followup_has_no_retrieval_cues() -> None:
    diagnostics = _diagnostics(prompt="Turn that answer into three concise bullets.")

    assert diagnostics["freshness_cue_detected"] is False
    assert diagnostics["freshness_cue_type"] == "none"
    assert diagnostics["source_constraint_detected"] is False
    assert diagnostics["source_constraint_type"] == "none"
    assert diagnostics["contradiction_cue_detected"] is False
    assert diagnostics["ambiguity_cue_detected"] is False
    assert diagnostics["would_require_fresh_retrieval"] is False


def test_followup_diagnostics_clear_named_followup_has_no_ambiguity_cue() -> None:
    diagnostics = _diagnostics(prompt="What about Delta Air Lines on that same metric?")

    assert diagnostics["ambiguity_cue_detected"] is False


def test_source_card_parity_diagnostics_records_available_cited_and_card_ids() -> None:
    diagnostics = _diagnostics(
        synthesis=_synthesis(
            answer="Supported by [[1]](https://example.com/a) and [[3]](https://example.com/c).",
            sources={
                "https://example.com/a": {"id": 1, "title": "A"},
                "https://example.com/b": {"id": 2, "title": "B"},
                "https://example.com/c": {"id": 3, "title": "C"},
            },
        ),
        source_cards=[
            {"source_id": "1", "title": "A", "url": "https://example.com/a"},
            {"source_id": "2", "title": "B", "url": "https://example.com/b"},
        ],
    )

    assert diagnostics["source_card_parity_status"] == "cited_ids_without_cards"
    assert diagnostics["answer_citation_ids"] == ["1", "3"]
    assert diagnostics["source_card_ids"] == ["1", "2"]
    assert diagnostics["available_source_ids"] == ["1", "2", "3"]
    assert diagnostics["cited_ids_without_cards"] == ["3"]
    assert diagnostics["card_ids_not_cited"] == ["2"]


def test_source_card_parity_diagnostics_does_not_mutate_or_suppress_cards() -> None:
    source_cards = [
        {"source_id": "1", "title": "A", "url": "https://example.com/a"},
        {"source_id": "2", "title": "B", "url": "https://example.com/b"},
    ]
    original_cards = [dict(card) for card in source_cards]

    diagnostics = build_source_card_parity_diagnostics(
        answer_text="Only [[1]](https://example.com/a) is cited.",
        source_cards=source_cards,
        available_sources={
            "https://example.com/a": {"id": 1},
            "https://example.com/b": {"id": 2},
        },
    )

    assert source_cards == original_cards
    assert diagnostics["source_card_ids"] == ["1", "2"]
    assert diagnostics["card_ids_not_cited"] == ["2"]


def test_malformed_evaluator_sets_parse_failed_and_keeps_no_search_fallback() -> None:
    def embed_texts(texts, **_kwargs):
        return [[1.0] for _ in texts]

    result = run_memory_search_and_evaluator(
        prompt="Can the saved report answer this?",
        session={"report": "report", "chat_messages": [{"role": "user", "content": "hi"}], "top_passages": []},
        current_date="2026-05-12",
        fu_params={"max_queries": 3},
        fast_provider="OpenAI",
        fast_model="mini",
        local_url="",
        api_key="",
        use_reasoning=False,
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        embed_texts=embed_texts,
        compute_similarities=lambda *_args, **_kwargs: [],
        ask_model=lambda *_args, **_kwargs: "{not valid json",
        clean_json_response=lambda value: value,
        chat_evaluator_prompt="evaluate",
    )

    assert result.evaluator_parse_status == "parse_failed"
    assert result.needs_search is False
    assert result.followup_queries == []

    diagnostics = _diagnostics(
        memory=result,
        web=_web(search_ran=False),
        prompt="Should this malformed evaluator response trigger search?",
    )

    assert diagnostics["evaluator_parse_status"] == "parse_failed"
    assert diagnostics["followup_route_observed"] == "parse_failure_fallback"
    assert diagnostics["followup_route_shadow"] == "parse_failure_fallback"
    assert diagnostics["followup_route_reason"] == "evaluator_parse_failed"
    assert diagnostics["saved_context_sufficient"] == "unknown"


def test_valid_evaluator_json_does_not_enter_parse_failure_diagnostics() -> None:
    def embed_texts(texts, **_kwargs):
        return [[1.0] for _ in texts]

    result = run_memory_search_and_evaluator(
        prompt="Find more support.",
        session={"report": "report", "chat_messages": [{"role": "user", "content": "hi"}], "top_passages": []},
        current_date="2026-05-12",
        fu_params={"max_queries": 3},
        fast_provider="OpenAI",
        fast_model="mini",
        local_url="",
        api_key="",
        use_reasoning=False,
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        embed_texts=embed_texts,
        compute_similarities=lambda *_args, **_kwargs: [],
        ask_model=lambda *_args, **_kwargs: '{"can_answer": false, "search_queries": ["more synthetic support"]}',
        clean_json_response=lambda value: value,
        chat_evaluator_prompt="evaluate",
    )

    diagnostics = _diagnostics(
        memory=result,
        web=_web(search_ran=True, new_passages=[{"url": "https://example.com/a"}]),
    )

    assert result.evaluator_parse_status == "parsed"
    assert result.needs_search is True
    assert result.followup_queries == ["more synthetic support"]
    assert diagnostics["evaluator_parse_status"] == "parsed"
    assert diagnostics["followup_route_observed"] != "parse_failure_fallback"
