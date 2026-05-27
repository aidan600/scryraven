"""Chat follow-up cost accumulator threading and execution logging."""

from __future__ import annotations

import json
from pathlib import Path

from core.cost_accounting import CostAccumulator
from core.followup import FollowUpDeps, run_followup
from core.run_logging import log_chat_followup_completed


def test_run_followup_passes_cost_accumulator_to_embed_eval_and_search() -> None:
    ca = CostAccumulator()
    phases_seen: list[str] = []

    def embed_texts(texts: list, **kwargs):
        assert kwargs.get("cost_accumulator") is ca
        assert kwargs.get("cost_phase") == "embedding"
        phases_seen.append("embedding")
        ca.record_embedding_call(phase="embedding", model="text-embedding-3-small", input_tokens=32)
        return [[1.0, 0.0] for _ in texts]

    def compute_similarities(a, b):
        import numpy as np

        return np.array([1.0])

    def search_fn(*_args, **kwargs):
        assert kwargs.get("cost_accumulator") is ca
        assert kwargs.get("cost_phase") == "retrieval"
        phases_seen.append("retrieval")
        return []

    def clean_json_response(s: str) -> str:
        return s

    def ask_model(prompt: str, system_prompt: str, **kwargs):
        assert kwargs.get("cost_accumulator") is ca
        assert kwargs.get("cost_phase") == "model"
        phases_seen.append("model")
        ca.record_model_call(phase="model", model="gpt-5.4-mini", input_tokens=40, output_tokens=20)
        return '{"can_answer": false, "search_queries": ["probe query"]}'

    def synthesis_fn(_p: str) -> str:
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
        cost_accumulator=ca,
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
    )
    assert out.synthesis_result.answer == "final answer"
    assert "embedding" in phases_seen and "model" in phases_seen and "retrieval" in phases_seen
    snap = ca.snapshot()
    assert snap["total_cost_usd"] > 0


def test_log_chat_followup_completed_writes_event(tmp_path: Path) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    cost = {"total_cost_usd": 0.012345, "cost_by_phase": {"model": 0.01}, "total_calls": 2}
    log_chat_followup_completed(
        run_id="r1",
        session_id="s1",
        parent_run_id="p1",
        query_preview="hello world",
        mode="Balanced",
        latency_seconds=1.5,
        cost=cost,
        followup_diagnostics={"needs_search": False, "search_ran": False},
        path=log_path,
    )
    line = log_path.read_text(encoding="utf-8").strip().split("\n")[-1]
    payload = json.loads(line)
    assert payload["event"] == "chat_followup"
    assert payload["phase"] == "chat_followup"
    assert payload["run_id"] == "r1"
    assert payload["cost"] == cost
    assert payload["followup_diagnostics"] == {"needs_search": False, "search_ran": False}


def test_log_chat_followup_completed_lifts_provider_diagnostics(tmp_path: Path) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    provider_attempt = {
        "provider": "tavily",
        "provider_role": "chat_followup_search",
        "success": True,
        "logical_attempt_count": 1,
    }

    log_chat_followup_completed(
        run_id="r-provider",
        session_id="s1",
        parent_run_id="p1",
        query_preview="hello world",
        mode="Balanced",
        latency_seconds=1.5,
        followup_diagnostics={"provider_diagnostics": [provider_attempt]},
        path=log_path,
    )

    payload = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert payload["provider_diagnostics"] == [provider_attempt]
    assert payload["provider_successful_attempts_by_provider"] == {"tavily": 1}
    assert payload["provider_failed_attempts_by_provider"] == {}
    assert payload["provider_attempts_by_role"] == {"chat_followup_search": 1}
    assert payload["provider_shadow_cost_estimate_available"] is False
    assert payload["provider_estimated_cost_usd"] is None
