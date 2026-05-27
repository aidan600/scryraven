# Roadmap: Retrieval, Disambiguation, and Failure UX

Status: Historical/superseded roadmap. This document is repo-local context only
and must not be treated as current authorization for behavior changes.

This document generalizes a diagnosis pattern (weak search → wrong entities in the corpus → honest or verbose “non-answers”) into an implementation sequence. It is **not** tailored to a single user query; the same mechanisms apply to any **person / place / product** name collision, thin evidence, or “controversy / latest / news” phrasing that demands recency and entity precision.

**Sequencing rule:** ship **P0** first, run **20–30** diverse real queries, read logs, then decide how much of P1–P2 to build. P1–P2 are contingent on P0 being in place.

---

## P0 — Search layer (highest leverage)

### 1. Query type classification (pre-search)

**Goal:** One cheap structured step before the first search: `person | place | product | concept | news | how_to | other` (exact enum TBD).

**Why:** Person-like queries need disambiguation and often recency; purely conceptual queries need different query expansion. Today a single generic search path overfits to “one size fits all.”

**Where to hook (ProPlex):** Extend the existing **router** output in `core/prompts.py` (or a tiny follow-up call) to emit `query_type` and optional `primary_entity` string. Thread through `ui/pages.py` into the first `process_search_queries` / researcher query generation.

**Acceptance:** For held-out person queries, generated search strings include at least one disambiguating token (role, org, domain) when `query_type=person`.

---

### 2. Entity disambiguation for person (and high-collision) queries

**Goal:** When `query_type` is `person` (or router flags ambiguity), automatically append or alternate queries such as `"[name]" (professor|NYU|…)` or use a second-stage query if top results disagree on entity.

**Heuristic (concrete):** If the top *N* URLs/titles do not coherently refer to the same real-world referent (e.g. name collision in titles), **reformulate and re-search** once before synthesis.

**Where to hook:** After first retrieval pass, before or inside the loop in `ui/pages.py` (or a small `core/retrieval_quality.py` helper), inspect **candidate titles/domains**; on failure, push **refined queries** into `current_queries` or a dedicated retry slot.

**Acceptance:** Name-collision class failures (unrelated “same substring” articles) drop measurably in the waste log (see P3).

---

### 3. Recency-parallel search for time-sensitive phrasing

**Goal:** If the query contains signals like *controversy, latest, news, today, 2025, 2026* or `intent=news`, fire a **second** search pass scoped to a **recent window** (e.g. last 7–30 days) in parallel with or after the base query. Merge and rank with recency.

**Why:** A single undated web query often returns durable SEO pages, obituaries, or geography — not the story the user meant.

**Where to hook:** `core/search_providers.py` / `core/retrieval.py` (date windows already exist for news in places); `ui/pages.py` where `current_queries` are built for `intent == "news"` or from `query_type`.

**Acceptance:** Median “age of newest cited source” decreases for `news` / “controversy”-style eval queries.

---

### 4. Utilization / relevance retry (one automatic pass)

**Goal:** After retrieval, compute a simple **utilization** signal, e.g. `sources_with_entity_mention / sources_fetched` or `chunks_passing_relevance / chunks_fetched` (exact metric to define in code). If below a threshold (start with **0.25**), **reformulate the query once** and re-fetch **before** the author runs.

**User-facing rule:** The user should not be asked to “allow a fresh search” for a fix the system can do automatically. Retries are internal; copy should not blame the “evidence pipeline” in user-facing text (see P2).

**Where to hook:** Between `process_search_queries` and analyst/author in `ui/pages.py`, or a `core/pipeline.py` helper.

**Acceptance:** “Zero useful entity” runs trigger exactly one extra search attempt when not cost-prohibitive.

---

## P1 — Source validation (lightweight)

### 5. Primary-entity presence check (pre-synthesis)

**Goal:** Before spending tokens on a long report, require a minimum **name/entity match rate** in the retrieved set (e.g. ≥2 independent sources that clearly discuss the intended entity). If not met → **same retry path as P0-4**, not a long report about off-topic material.

**Why:** Stops the failure mode where Balanced/Deep **sound** authoritative by narrating *wrong* articles in depth.

**Where to hook:** After passages are collected, before “Final Synthesis”; filter or short-circuit to failure UX (P2) if check fails.

---

### 6. Recency & date-range disclosure (metadata line)

**Goal:** Add a one-line **source date span** to the report header or footer (e.g. “Sources in corpus: Mar 2024–Apr 2026”) when extractable. If the query implies currency and the newest source is **stale** (e.g. &gt;14 days for “latest/controversy”-style), add a **brief** caveat.

**Where to hook:** Author prompt or a small post-processor; optional field in `execution_log.jsonl` for analytics.

---

## P2 — Output behavior on failure

### 7. Failure response contract (short, no fake depth)

**Target behavior when retrieval is poor or off-entity:

- **≤3 short sentences** by default: (1) we didn’t get on-target sources, (2) one line on *what* was retrieved instead (optional), (3) we’re retrying or the user can narrow the ask.
- **No** long structured sections, **no** multi-header essay about **irrelevant** stories just because they were in the corpus.
- **No** internal jargon: avoid “the source set,” “the evidence pipeline,” “provided evidence as of …” in user-facing text; use plain language.

**Where to hook:** `DEFAULT_SYSTEM["author"]` (or a dedicated `author_failure` system string) + a flag from P0/P1 (`retrieval_confidence: low`).

---

### 8. Balanced / Deep verbosity gate

**Goal:** Long tables, many H3s, and “full report” structure only when a **relevance / utilization** score is above a threshold (e.g. **0.5**). Below that, **match Fast-style brevity** (same as P2-7) even if the mode is Balanced.

**Why:** Prevents “sophisticated-looking document about the wrong things” — worse UX than a short honest miss.

**Where to hook:** Author prompt tier in `ui/pages.py` (`tier_instructions` / complexity) conditioned on a `corpus_relevance_score` computed after retrieval.

---

## P3 — Instrumentation (minimal new surface area)

### 9. One JSONL “waste / quality” line per run

**Goal:** Append one line at end of run (beside existing `execution` event) with:

- `ts`, `query` (preview), `query_type`, `mode` (Fast/Balanced/Deep)
- `searches_fired`, `passes` or `iterations`
- `sources_fetched`, `sources_passing_entity_check` (or `chunks_cited` / similar)
- `utilization_rate` (defined consistently with P0-4)
- `retry_triggered` (bool)
- `waste_flags` (e.g. `entity_disambiguation_failure`, `low_utilization`, `stale_corpus_for_news_query`)
- `total_ms` (optional)

**Where to hook:** Next to existing `_append_jsonl(execution_log_path, …)` in `ui/pages.py` or a single `log_run_quality()` in `core/review_flags.py` / small `core/run_metrics.py`.

---

### 10. Weekly aggregation script (offline)

**Goal:** A **standalone** script (e.g. `scripts/aggregate_run_quality.py`) that reads the JSONL, prints:

- Bottom 20% of runs by `utilization_rate`
- Counts of `waste_flags`
- Avg searches per `query_type`

Run manually; no in-app dashboard required for v1.

---

## Explicitly out of scope (v1)

- A second “judge” LLM call on every run **before** fixing retrieval (adds cost/latency; defer).
- Automated third-party search API benchmarking in CI.
- Purely cosmetic formatting passes **without** P0 retrieval changes.

---

## Suggested order of implementation in this repo

1. **Router + `query_type`** → thread to query builder.
2. **Utilization + one automatic retry** (P0-4) + **waste log line** (P3-9) so every change is measurable.
3. **Entity presence check** (P1-5) + **failure author template** (P2-7).
4. **Recency parallel** (P0-3) for `news` + controversy-like tokens.
5. **Verbosity gate** for Balanced (P2-8).
6. **Recency disclosure** (P1-6) + **weekly script** (P3-10).

---

## Success criteria (not overfit to one example)

- **Retrieval:** ↑ fraction of runs where the primary named entity appears in ≥2 top-level sources.
- **User trust:** ↓ “confident long report on wrong subject” incidents (manual review of random sample).
- **Efficiency:** Automatic retries cap at **+1** search pass per run unless you raise the cap explicitly later.
- **Observability:** You can sort runs by `utilization_rate` and `waste_flags` without reading full reports.
