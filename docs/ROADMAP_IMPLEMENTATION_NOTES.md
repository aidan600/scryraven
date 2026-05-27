# Roadmap vs implementation (snapshot)

Status: Historical/superseded implementation snapshot. This document is
repo-local context only and must not be treated as current authorization for
behavior changes.

Cross-reference: [RETRIEVAL_AND_FAILURE_UX_ROADMAP.md](RETRIEVAL_AND_FAILURE_UX_ROADMAP.md).

## Implemented in codebase

- **P0 — Query typing, utilization, retries:** Router emits `query_type` / entity signals; [`core/retrieval_quality.py`](../core/retrieval_quality.py) implements utilization scoring and disambiguation retries; orchestrator logs metrics to `output/execution_log.jsonl`.
- **P0 — Recency merge:** [`should_merge_recency_queries`](core/retrieval_quality.py) drives extra query shaping where configured.
- **P2-7 — Thin failure prose:** [`DEFAULT_SYSTEM["author_corpus_weak"]`](core/prompts.py) plus `corpus_weak` routing in [`core/pipeline_orchestrator.py`](../core/pipeline_orchestrator.py).
- **P3 — JSONL quality lines:** Execution events include utilization, `waste_flags`, traces; [`scripts/aggregate_run_quality.py`](../scripts/aggregate_run_quality.py) aggregates offline.

## Added / tightened for this plan

- **P1-6 — Recency disclosure:** [`core/source_recency.py`](../core/source_recency.py) infers a coarse year span from passage titles/snippets and injects a short **TEMPORAL CALIBRATION** block into the author prompt. When recency-sensitive phrasing + stale inferred years, logs `stale_corpus_for_news_query` in `waste_flags`.
- **P2-8 — Verbosity gate (Balanced/Deep):** If utilization is below [`VERBOSITY_GATE_UTILIZATION_THRESHOLD`](../core/retrieval_quality.py) (0.5) and mode complexity is medium/high, the author tier is forced to **THIN** (Fast-style brevity) even when `corpus_weak` is false — see `_relevance_low` in the orchestrator.

## Still optional / product-level

- Collaboration, cloud sync, multi-user accounts (not planned in roadmap v1).
- In-app dashboard for run quality (roadmap suggests offline scripts first).
- Exact publish dates per URL (search snippets rarely expose structured dates; heuristics use visible years only).
