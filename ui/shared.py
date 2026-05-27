"""Shared UI helpers (no page routing; safe to import from multiple page modules)."""

from __future__ import annotations

from typing import Any

from core.run_logging import append_jsonl as _append_jsonl_core


def flatten_providers_used(providers_by_iteration: list | None) -> list[str]:
    """Unique search provider names in first-seen order across retrieval iterations."""
    seen: set[str] = set()
    out: list[str] = []
    for group in providers_by_iteration or []:
        for name in group or []:
            n = str(name).strip()
            if not n or n in seen:
                continue
            seen.add(n)
            out.append(n)
    return out


def pipeline_timing_payload(
    *,
    latency_seconds: float,
    pre_retrieval_seconds: float,
    recon_seconds: float,
    iter_timing_seconds: dict[int, float],
    scout_llm_seconds: float,
    expander_llm_seconds: float,
    gap_evaluator_llm_seconds: float,
    economist_seconds: float,
    analyst_seconds: float,
    synth_evaluator_seconds: float,
    scrutineer_seconds: float,
    author_seconds: float,
) -> dict[str, float]:
    """Timing rows for execution logs.

    Note: scout/expander/gap_evaluator LLM times overlap ``iter*_seconds`` (they run inside
    retrieval iterations). Do not sum all keys expecting ``latency_seconds``; use
    ``timing_accounted_seconds`` and ``unaccounted_wall_seconds``.
    """
    i1 = float(iter_timing_seconds.get(1, 0.0))
    i2 = float(iter_timing_seconds.get(2, 0.0))
    i3 = float(iter_timing_seconds.get(3, 0.0))
    retrieval_iters = i1 + i2 + i3
    post_llm = (
        float(economist_seconds)
        + float(analyst_seconds)
        + float(synth_evaluator_seconds)
        + float(scrutineer_seconds)
        + float(author_seconds)
    )
    accounted = (
        float(pre_retrieval_seconds)
        + float(recon_seconds)
        + retrieval_iters
        + post_llm
    )
    out = {
        "pre_retrieval_seconds": round(pre_retrieval_seconds, 2),
        "recon_seconds": round(float(recon_seconds), 2),
        "iter1_seconds": round(i1, 2),
        "iter2_seconds": round(i2, 2),
        "iter3_seconds": round(i3, 2),
        "scout_llm_seconds": round(scout_llm_seconds, 2),
        "expander_llm_seconds": round(expander_llm_seconds, 2),
        "gap_evaluator_llm_seconds": round(gap_evaluator_llm_seconds, 2),
        "economist_seconds": round(economist_seconds, 2),
        "analyst_seconds": round(analyst_seconds, 2),
        "synth_evaluator_seconds": round(synth_evaluator_seconds, 2),
        "scrutineer_seconds": round(scrutineer_seconds, 2),
        "author_seconds": round(author_seconds, 2),
        "synthesis_seconds": round(author_seconds, 2),
        "post_retrieval_llm_seconds": round(post_llm, 2),
        "timing_accounted_seconds": round(accounted, 2),
        "unaccounted_wall_seconds": round(max(0.0, float(latency_seconds) - accounted), 2),
    }
    return out


def append_jsonl_record(path: Any, payload: dict, *, logger: Any) -> None:
    _append_jsonl_core(path, payload, logger=logger)


def read_jsonl_records(path: Any, *, json_module: Any, logger: Any) -> list[dict]:
    records: list[dict] = []
    try:
        if not path.exists():
            return records
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json_module.loads(line))
                except Exception:
                    continue
    except Exception as e:
        logger.warning("Non-fatal log read failure (%s): %s", path.name, e)
    return records
