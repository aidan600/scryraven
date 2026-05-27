import ast
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse


def load_app_functions(*function_names: str) -> Dict[str, Any]:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(app_path))

    selected_nodes: List[ast.FunctionDef] = []
    wanted = set(function_names)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            node.decorator_list = []
            selected_nodes.append(node)

    mini_module = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(mini_module)

    namespace: Dict[str, Any] = {
        "json": json,
        "re": re,
        "urlparse": urlparse,
        "Path": Path,
        "logger": logging.getLogger("tests"),
        "List": List,
        "Dict": Dict,
        "Any": Any,
    }
    exec(compile(mini_module, str(app_path), "exec"), namespace)
    return {name: namespace[name] for name in function_names}


def test_parse_domain_list_trims_and_normalizes() -> None:
    funcs = load_app_functions("parse_domain_list")
    parse_domain_list = funcs["parse_domain_list"]

    assert parse_domain_list(" NIH.gov, Nature.com ,,  ") == ["nih.gov", "nature.com"]


def test_clean_json_response_extracts_json_object() -> None:
    from core.text_utils import clean_json_response

    raw = "Result:\n```json\n{\"ok\": true}\n```\n"
    assert clean_json_response(raw) == "{\"ok\": true}"


def test_normalize_domain_strips_www_prefix() -> None:
    from core.retrieval import normalize_domain

    assert normalize_domain("https://www.example.com/path?a=1") == "example.com"


def test_chunk_text_splits_large_input_into_multiple_chunks() -> None:
    from core.retrieval import chunk_text

    text = "Sentence one. Sentence two. " * 200
    chunks = chunk_text(text, chunk_size=300)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 350 for chunk in chunks)


def test_filter_top_evidence_limits_chunks_per_domain() -> None:
    from core.retrieval import filter_top_evidence

    passages = [
        {"domain": "a.com", "score": 0.9},
        {"domain": "a.com", "score": 0.8},
        {"domain": "a.com", "score": 0.7},
        {"domain": "b.com", "score": 0.6},
    ]
    filtered = filter_top_evidence(passages, max_chunks=3, max_per_domain=2)

    assert len(filtered) == 3
    assert sum(1 for p in filtered if p["domain"] == "a.com") == 2


def test_ensure_passage_source_ids_groups_urls_and_fills_missing() -> None:
    from core.retrieval import ensure_passage_source_ids

    passages = [
        {"url": "https://a.example/x", "text": "one"},
        {"url": "https://b.example/y", "text": "two"},
        {"url": "https://a.example/x", "text": "three"},
        {"text": "no url"},
    ]
    ensure_passage_source_ids(passages)
    assert passages[0]["source_id"] == passages[2]["source_id"] == 1
    assert passages[1]["source_id"] == 2
    assert passages[3]["source_id"] == 3


def test_passage_mentions_entity_full_phrase_contiguous_not_token_or() -> None:
    from core.retrieval_quality import passage_mentions_entity, passage_mentions_entity_full_phrase

    p_ok = {
        "title": "Commentary",
        "text": "Scott Galloway on paternity leave.",
    }
    p_wrong = {
        "title": "Dilbert",
        "text": "Scott Adams and others discussed the strip.",
    }
    ent = "Scott Galloway"
    assert passage_mentions_entity_full_phrase(p_ok, ent) is True
    assert passage_mentions_entity_full_phrase(p_wrong, ent) is False
    # Looser util heuristic can still see "Scott" match on the wrong passage.
    assert passage_mentions_entity(p_wrong, ent) is True


def test_passage_mentions_entity_full_phrase_single_token_word_boundary() -> None:
    from core.retrieval_quality import passage_mentions_entity_full_phrase

    p = {"title": "X", "text": "Tesla stock moved."}
    assert passage_mentions_entity_full_phrase(p, "Tesla") is True
    assert passage_mentions_entity_full_phrase(p, "esla") is False


def test_jaccard_similarity_query_lists() -> None:
    from core.retrieval_quality import jaccard_similarity

    a = ["scott galloway controversy 2026"]
    b = ["scott galloway backlash 2026"]
    assert 0.0 < jaccard_similarity(a, b) < 1.0
    assert jaccard_similarity([], ["a"]) == 0.0


def test_extract_recon_context_empty() -> None:
    from core.retrieval_quality import extract_recon_context

    assert extract_recon_context([]) == {"recon_titles": "", "recon_snippets": ""}


def test_utilization_entity_anchor_compacts_long_event_phrase() -> None:
    from core.retrieval_quality import utilization_entity_anchor

    e = "Sabastian Sawe's first competitive sub-2-hour marathon at the 2026 London Marathon"
    a = utilization_entity_anchor(e, "event")
    assert a
    assert "Sabastian" in a and "Sawe" in a


def test_followup_mode_inherits_parent_session_fields() -> None:
    from core.followup import complexity_for_ui_mode, resolve_followup_mode

    assert resolve_followup_mode({"last_report_mode": "Balanced"}) == "Balanced"
    assert complexity_for_ui_mode("Balanced") == "medium"
    assert resolve_followup_mode({"pipeline_config": {"mode": "Fast", "complexity": "high"}}) == "Fast"
    assert resolve_followup_mode({"pipeline_config": {"complexity": "medium"}}) == "Balanced"


def test_followup_source_map_and_prompt_helpers() -> None:
    from core.followup import (
        add_passages_to_source_map,
        build_followup_prompt,
        build_image_context,
        build_new_evidence_block,
        build_source_map,
        build_sources_text,
    )

    passages = [
        {"url": "https://example.com/a", "title": "A"},
        {"url": "https://example.com/a", "title": "A duplicate"},
        {"url": "https://example.com/b", "title": "B"},
    ]
    sources, next_id = build_source_map(passages)
    assert next_id == 3
    assert sources["https://example.com/a"]["id"] == 1
    assert sources["https://example.com/b"]["id"] == 2

    sources_text = build_sources_text(sources, lambda url: "example.com" in url)
    assert "[1] A - https://example.com/a" in sources_text
    assert "[2] B - https://example.com/b" in sources_text
    next_id = add_passages_to_source_map(sources, next_id, [{"url": "https://example.com/c", "title": "C"}])
    assert next_id == 4
    evidence = build_new_evidence_block(
        [{"url": "https://example.com/c", "title": "C", "text": "new source text"}],
        sources,
    )
    assert "[New Source 3] C" in evidence
    assert "new source text" in evidence
    assert "AVAILABLE IMAGES" in build_image_context(["https://example.com/image.jpg"])

    prompt = build_followup_prompt(
        current_date="Monday Apr 27, 2026",
        report="Original report",
        existing_evidence_block="Existing evidence",
        new_evidence_block="New evidence",
        sources_text=sources_text,
        conversation_history="USER: prior",
        prompt="Compare costs",
        complexity="medium",
    )
    assert "FOLLOW-UP FORMAT" in prompt
    assert "Do not produce markdown tables wider than 4 columns" in prompt
    assert "TIER: BALANCED" in prompt
    assert "USER FOLLOW-UP: Compare costs" in prompt


def test_followup_memory_search_and_evaluator_uses_injected_dependencies() -> None:
    from core.followup import run_memory_search_and_evaluator

    session = {
        "report": "Original report",
        "chat_messages": [{"role": "user", "content": "Compare costs"}],
        "top_passages": [
            {"url": "https://example.com/md80", "title": "MD80", "text": "MD-80 cost data"},
            {"url": "https://example.com/777", "title": "777", "text": "777 cost data"},
        ],
    }

    def fake_embed_texts(texts, **_kwargs):
        if len(texts) == 1:
            return [[1.0, 0.0]]
        return [[0.0, 1.0], [1.0, 0.0]]

    def fake_compute_similarities(_query_embedding, _existing_embeddings):
        return [0.1, 0.9]

    prompts_seen = []

    def fake_ask_model(prompt, *_args, **_kwargs):
        prompts_seen.append(prompt)
        return '{"can_answer": false, "search_queries": ["777 CASM", "MD80 CASM", "extra"]}'

    result = run_memory_search_and_evaluator(
        prompt="Compare aircraft CASM",
        session=session,
        current_date="Monday Apr 27, 2026",
        fu_params={"max_queries": 2},
        fast_provider="OpenAI",
        fast_model="mini",
        local_url="http://localhost:1234/v1",
        api_key="",
        use_reasoning=False,
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        embed_texts=fake_embed_texts,
        compute_similarities=fake_compute_similarities,
        ask_model=fake_ask_model,
        clean_json_response=lambda x: x,
        chat_evaluator_prompt="evaluate",
    )

    assert result.query_embedding == [1.0, 0.0]
    assert result.needs_search is True
    assert result.followup_queries == ["777 CASM", "MD80 CASM"]
    assert "[Memory Source 2] 777" in result.existing_evidence_block
    assert "User's Follow-up Question: Compare aircraft CASM" in prompts_seen[0]


def test_web_retrieval_skipped_when_needs_search_false() -> None:
    from core.followup import MemorySearchResult, run_web_retrieval

    calls = []
    memory = MemorySearchResult(
        sources={"https://example.com/a": {"title": "A", "id": 1}},
        next_source_id=2,
        conversation_history="",
        query_embedding=[1.0],
        existing_evidence_block="",
        needs_search=False,
        followup_queries=["should not run"],
    )

    def search_fn(*_args, **_kwargs):
        calls.append("called")
        return []

    result = run_web_retrieval(
        memory_result=memory,
        session={"seen_urls": ["https://old.example"]},
        intent="general",
        complexity="medium",
        fu_params={"search_depth": "advanced", "max_results": 3, "top_passage_count": 2},
        include_domains=[],
        exclude_domains=[],
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        search_fn=search_fn,
    )

    assert calls == []
    assert result.search_ran is False
    assert result.new_passages == []
    assert result.sources == memory.sources


def test_web_retrieval_extends_source_map_and_reports_progress() -> None:
    from core.followup import MemorySearchResult, run_web_retrieval

    progress = []
    memory = MemorySearchResult(
        sources={"https://example.com/a": {"title": "A", "id": 1}},
        next_source_id=2,
        conversation_history="",
        query_embedding=[1.0],
        existing_evidence_block="",
        needs_search=True,
        followup_queries=["777 CASM"],
    )

    def search_fn(*args, **_kwargs):
        assert args[0] == ["777 CASM"]
        return [
            {"url": "https://example.com/b", "title": "B", "text": "new evidence", "score": 0.9},
            {"url": "https://example.com/c", "title": "C", "text": "lower evidence", "score": 0.1},
        ]

    result = run_web_retrieval(
        memory_result=memory,
        session={},
        intent="general",
        complexity="medium",
        fu_params={"search_depth": "advanced", "max_results": 3, "top_passage_count": 1},
        include_domains=[],
        exclude_domains=[],
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        search_fn=search_fn,
        on_progress=progress.append,
    )

    assert result.search_ran is True
    assert result.next_source_id == 3
    assert result.sources["https://example.com/b"]["id"] == 2
    assert len(result.new_passages) == 1
    assert "[New Source 2] B" in result.new_evidence_block
    assert any("Searching the web" in msg for msg in progress)
    assert any("Integrated 1 new evidence passages" in msg for msg in progress)


def test_web_retrieval_returns_empty_on_search_fn_failure(tmp_path: Path) -> None:
    from core.followup import MemorySearchResult, run_web_retrieval

    progress = []
    log_path = tmp_path / "execution_log.jsonl"
    memory = MemorySearchResult(
        sources={},
        next_source_id=1,
        conversation_history="",
        query_embedding=[1.0],
        existing_evidence_block="",
        needs_search=True,
        followup_queries=["bad query"],
    )

    def search_fn(*_args, **_kwargs):
        raise RuntimeError("network down")

    result = run_web_retrieval(
        memory_result=memory,
        session={},
        intent="general",
        complexity="medium",
        fu_params={"search_depth": "advanced", "max_results": 3, "top_passage_count": 2},
        include_domains=[],
        exclude_domains=[],
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        search_fn=search_fn,
        on_progress=progress.append,
        execution_log_path=log_path,
    )

    assert result.search_ran is True
    assert result.new_passages == []
    assert result.error == "network down"
    assert any("failed" in msg for msg in progress)

    err_line = json.loads(log_path.read_text(encoding="utf-8"))
    assert err_line["event"] == "provider_error"
    assert err_line["provider"] == "followup_web_retrieval"
    assert "network down" in err_line["error"]
    assert err_line["query_preview"] == "['bad query']"[:200]


def test_run_logging_writes_standard_lifecycle_events(tmp_path: Path) -> None:
    from core.run_logging import log_run_completed, log_run_failed, log_run_started

    log_path = tmp_path / "execution_log.jsonl"
    log_run_started(
        run_id="r1",
        session_id="s1",
        phase="chat_followup",
        query="Compare MD-83 vs 777-300ER CASM in 2019",
        mode="Balanced",
        parent_run_id="parent",
        path=log_path,
    )
    log_run_completed(
        run_id="r1",
        session_id="s1",
        phase="chat_followup",
        latency_seconds=1.25,
        mode="Balanced",
        parent_run_id="parent",
        timing={"synthesis_seconds": 1.25},
        path=log_path,
    )
    log_run_failed(
        run_id="r2",
        session_id="s1",
        phase="chat_followup",
        latency_seconds=0.5,
        error=RuntimeError("boom"),
        mode="Balanced",
        path=log_path,
    )

    lines = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [line["event"] for line in lines] == ["run_started", "run_completed", "run_failed"]
    assert lines[0]["query_preview"].startswith("Compare MD-83")
    assert lines[0]["mode"] == "Balanced"
    assert lines[1]["error"] is None
    assert lines[1]["timing"]["synthesis_seconds"] == 1.25
    assert lines[2]["error"] == "boom"
    assert all(line.get("timestamp_utc") for line in lines)


def test_code_version_metadata_is_absent_when_git_lookup_fails(monkeypatch) -> None:
    import subprocess

    from core.run_logging import COMMIT_SHA_ENV_VARS, current_code_version_metadata

    for env_var in COMMIT_SHA_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)

    def fail_git(*_args, **_kwargs):
        raise subprocess.SubprocessError("git unavailable")

    monkeypatch.setattr(subprocess, "run", fail_git)

    assert current_code_version_metadata() == {}


def test_run_logging_writes_retrieval_timeout(tmp_path: Path) -> None:
    from core.run_logging import log_retrieval_timeout

    log_path = tmp_path / "execution_log.jsonl"
    log_retrieval_timeout(provider="exa", query="slow query", timeout_seconds=30.0, path=log_path)

    line = json.loads(log_path.read_text(encoding="utf-8"))
    assert line["event"] == "retrieval_timeout"
    assert line["provider"] == "exa"
    assert line["query_preview"] == "slow query"
    assert line["timeout_seconds"] == 30.0


def test_run_logging_writes_provider_error(tmp_path: Path) -> None:
    from core.run_logging import log_provider_error

    log_path = tmp_path / "execution_log.jsonl"
    log_provider_error(
        provider="followup_synthesis",
        error="boom",
        query_preview="hello world",
        run_id="r1",
        session_id="s1",
        phase="chat_followup",
        path=log_path,
    )

    line = json.loads(log_path.read_text(encoding="utf-8"))
    assert line["event"] == "provider_error"
    assert line["provider"] == "followup_synthesis"
    assert line["error"] == "boom"
    assert line["query_preview"] == "hello world"
    assert line["run_id"] == "r1"
    assert line["session_id"] == "s1"
    assert line["phase"] == "chat_followup"


def test_synthesis_calls_model_fn_with_assembled_prompt() -> None:
    from core.followup import MemorySearchResult, WebRetrievalResult, run_followup_synthesis

    captured: dict[str, str] = {}

    def model_fn(p: str) -> str:
        captured["prompt"] = p
        return "done"

    memory = MemorySearchResult(
        sources={},
        next_source_id=1,
        conversation_history="USER: earlier",
        query_embedding=[],
        existing_evidence_block="memory excerpt",
        needs_search=False,
        followup_queries=[],
    )
    web = WebRetrievalResult(
        sources={"https://a.example/x": {"title": "SrcTitle", "id": 1}},
        next_source_id=2,
        new_passages=[],
        new_evidence_block="fresh excerpt",
        seen_urls=[],
        collected_images=[],
    )

    run_followup_synthesis(
        query="Compare aircraft CASM",
        memory_result=memory,
        web_result=web,
        session={"report": "original report body"},
        current_date="2026-04-01",
        follow_complexity="medium",
        image_context="",
        is_plausible_domain=lambda _u: True,
        model_fn=model_fn,
    )

    p = captured["prompt"]
    assert "Compare aircraft CASM" in p
    assert "original report body" in p
    assert "memory excerpt" in p
    assert "fresh excerpt" in p
    assert "USER: earlier" in p
    assert "[1] SrcTitle - https://a.example/x" in p


def test_synthesis_returns_error_result_on_model_failure(tmp_path: Path) -> None:
    from core.followup import MemorySearchResult, WebRetrievalResult, run_followup_synthesis

    log_path = tmp_path / "exec.jsonl"

    def model_fn(_p: str) -> str:
        raise RuntimeError("model unavailable")

    memory = MemorySearchResult(
        sources={},
        next_source_id=1,
        conversation_history="",
        query_embedding=[],
        existing_evidence_block="",
        needs_search=False,
        followup_queries=[],
    )
    web = WebRetrievalResult(
        sources={},
        next_source_id=1,
        new_passages=[],
        new_evidence_block="",
        seen_urls=[],
        collected_images=[],
    )

    result = run_followup_synthesis(
        query="any question here",
        memory_result=memory,
        web_result=web,
        session={"report": ""},
        current_date="2026-04-01",
        follow_complexity="low",
        image_context="",
        is_plausible_domain=lambda _u: True,
        model_fn=model_fn,
        execution_log_path=log_path,
    )

    assert result.error == "model unavailable"
    assert "try again" in result.answer.lower()
    logged = json.loads(log_path.read_text(encoding="utf-8"))
    assert logged["event"] == "provider_error"
    assert logged["provider"] == "followup_synthesis"


def test_synthesis_sources_text_matches_web_result_sources() -> None:
    from core.followup import MemorySearchResult, WebRetrievalResult, build_sources_text, run_followup_synthesis

    sources_map = {"https://z.example/p": {"title": "Zed", "id": 1}}

    def model_fn(_p: str) -> str:
        return "ok"

    memory = MemorySearchResult(
        sources={},
        next_source_id=1,
        conversation_history="",
        query_embedding=[],
        existing_evidence_block="",
        needs_search=False,
        followup_queries=[],
    )
    web = WebRetrievalResult(
        sources=dict(sources_map),
        next_source_id=2,
        new_passages=[],
        new_evidence_block="",
        seen_urls=[],
        collected_images=[],
    )

    def plausible(url: str) -> bool:
        return "z.example" in url

    result = run_followup_synthesis(
        query="q",
        memory_result=memory,
        web_result=web,
        session={"report": ""},
        current_date="2026-04-01",
        follow_complexity="low",
        image_context="",
        is_plausible_domain=plausible,
        model_fn=model_fn,
    )

    expected = build_sources_text(web.sources, plausible)
    assert result.sources_text == expected


def test_run_followup_chains_memory_web_synthesis() -> None:
    from core.followup import FollowUpDeps, FollowUpRunResult, MemorySearchResult, WebRetrievalResult, run_followup

    phase: list[str] = []

    def embed_texts(texts: list, **_kwargs):
        return [[1.0, 0.0] for _ in texts]

    def compute_similarities(a, b):
        import numpy as np

        return np.array([1.0])

    def search_fn(*_a, **_k):
        return []

    def clean_json_response(s: str) -> str:
        return s

    calls: list[str] = []

    def ask_model(prompt: str, system_prompt: str, **_kwargs) -> str:
        calls.append("eval")
        return '{"can_answer": true}'

    def synthesis_fn(_p: str) -> str:
        calls.append("synthesis")
        return "final answer"

    session = {
        "report": "rep",
        "top_passages": [],
        "chat_messages": [{"role": "user", "content": "hi"}],
    }
    deps = FollowUpDeps(
        embed_texts=embed_texts,
        compute_similarities=compute_similarities,
        search_fn=search_fn,
        ask_model=ask_model,
        clean_json_response=clean_json_response,
        synthesis_model_fn=synthesis_fn,
    )
    out = run_followup(
        query="follow up q",
        session=session,
        deps=deps,
        current_date="2026-01-01",
        follow_complexity="low",
        fu_params={"max_queries": 3, "search_depth": "advanced", "max_results": 3, "top_passage_count": 2},
        intent="general",
        include_domains=[],
        exclude_domains=[],
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        fast_provider="OpenAI",
        fast_model="mini",
        local_url="",
        api_key="",
        use_reasoning=False,
        chat_evaluator_prompt="You return JSON.",
        is_plausible_domain=lambda _u: True,
        on_progress=lambda m: phase.append(m),
    )
    assert isinstance(out, FollowUpRunResult)
    assert isinstance(out.memory_result, MemorySearchResult)
    assert isinstance(out.web_result, WebRetrievalResult)
    assert out.synthesis_result.answer == "final answer"
    assert calls == ["eval", "synthesis"]
    assert phase[0] == "Searching existing memory..."


def test_synthesis_prompt_contains_format_rules() -> None:
    from core.followup import CHAT_FOLLOWUP_FORMAT_RULES, MemorySearchResult, WebRetrievalResult, run_followup_synthesis

    def model_fn(_p: str) -> str:
        return "x"

    memory = MemorySearchResult(
        sources={},
        next_source_id=1,
        conversation_history="",
        query_embedding=[],
        existing_evidence_block="",
        needs_search=False,
        followup_queries=[],
    )
    web = WebRetrievalResult(
        sources={},
        next_source_id=1,
        new_passages=[],
        new_evidence_block="",
        seen_urls=[],
        collected_images=[],
    )

    result = run_followup_synthesis(
        query="format rules regression",
        memory_result=memory,
        web_result=web,
        session={"report": ""},
        current_date="2026-04-01",
        follow_complexity="high",
        image_context="",
        is_plausible_domain=lambda _u: True,
        model_fn=model_fn,
    )

    assert CHAT_FOLLOWUP_FORMAT_RULES in result.prompt_used
    assert "TIER: DEEP" in result.prompt_used


def test_storage_round_trip_save_rename_delete(tmp_path: Path) -> None:
    from core.storage import configure_storage, delete_session, read_history, rename_session, save_session

    configure_storage(tmp_path, tmp_path / "history.json", logging.getLogger("tests"))

    session_data = {
        "id": "abc123",
        "title": "Initial",
        "query": "test",
        "report": "report text",
        "top_passages": [{"url": "https://example.com", "text": "sample"}],
    }

    save_session(session_data)
    history = read_history()
    assert len(history) == 1
    assert history[0]["id"] == "abc123"

    rename_session("abc123", "Renamed")
    assert read_history()[0]["title"] == "Renamed"

    delete_session("abc123")
    assert read_history() == []
    assert not (tmp_path / "abc123_passages.json").exists()
