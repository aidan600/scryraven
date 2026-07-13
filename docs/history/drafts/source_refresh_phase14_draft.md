Status: historical
Authority: none
Default-read: no
Historical-scope: Phase 14 source-refresh review draft; provenance only.

# Source Refresh Phase 14 Draft

Status: Historical/draft Phase 14 review package. This document is a dated
repo-local review artifact, not an active canonical Project Source.

Review-lane draft for human approval before any Project Source update. This file
is repo-local, docs-only, and does not change runtime behavior.

## 1. Current Checkpoint

- Date: 2026-05-13
- Baseline SHA: `4850686` (`diag: add provider overlap yield telemetry`)
- Branch/status assumption: `main` is clean and pushed at the baseline SHA.
- Scope: draft source-refresh package only; no Project Source edits, code edits,
  test edits, commits, pushes, Streamlit runs, provider calls, model calls, live
  ProPlex queries, search API calls, or competitor calls.

## 2. Proposed Active Project Source Stack

Proposed active Project Source stack for review:

- Operating/safety contracts.
- Refreshed architecture/test baseline v2.
- History/constraints source.
- Roadmap/context hygiene v7.
- Collaboration/workflow v3.
- Optional compact provider diagnostics appendix/source candidate.

The active root Project Source files numbered 02, 04, and 05 are not present in
this repo checkout. This draft treats their replacement/refresh content as a
human-review package, not as an applied Project Source update.

## 3. Proposed Replacement For Stale 02 Baseline

Recommended replacement shape for the stale architecture/test baseline:

- Current architecture summary: ProPlex keeps retrieval, provider diagnostics,
  source filtering, Analyst, Economist, Author, telemetry, SQLite summary,
  replay, summarizer, and weak-corpus behavior under existing contracts.
- Tests/CI status: recent completed work added diagnostics and eval-harness
  contract coverage through the baseline SHA. This draft does not assert a fresh
  CI run beyond the clean-check commands listed below.
- Telemetry inventory: JSONL remains the rich trace; SQLite remains compact
  summary telemetry. Current diagnostic additions include provider role/cost
  fields, follow-up route/parity aggregates, and provider overlap/yield fields.
- Eval harness process/pipeline status contract: process status and pipeline
  status must be interpreted separately. Legacy `-1` means `process_status`
  unknown; `run_completed` with `error=null` means `pipeline_status` completed;
  stderr or NativeCommandError-looking output alone is not failure.
- Current non-policy boundaries: diagnostics expose review signals only. They do
  not authorize routing, retrieval, provider, prompt, source-filtering, Analyst,
  Economist, Author, SQLite, replay, summarizer, weak-corpus, or pricing policy
  changes.

## 4. Proposed V7 Roadmap Checkpoint

Phase 13 observability arc is complete through the baseline SHA:

- Shadow follow-up route telemetry was added.
- Follow-up route and parity aggregates were summarized.
- Eval harness exit-code status contract coverage was added.
- Provider role/cost telemetry was added.
- Provider overlap/yield telemetry was added.

Two approved live telemetry validation runs passed structurally:

- `oil and equity markets past week`, Fast, `--news`.
- `CRISPR off-target mitigation methods 2025 2026`, Balanced, `--academic`.

These live smoke runs should be described only as structural telemetry validation.
They are not answer-quality benchmarks, golden answers, or regression baselines.

Remaining priorities:

- Six-query diagnostics validation plan, later.
- Query-efficiency policy audit, later and no-edit first.
- CB-002 quantitative semantics audit, no-edit first.
- Quantitative Analyst-cost audit, no-edit first.
- Durable live-run helper/wrapper cleanup, no-edit first.

What not to do yet:

- Do not change routing, retrieval, provider selection, prompts, source filtering,
  Analyst behavior, Economist behavior, Author behavior, SQLite persistence,
  replay, summarizer, or weak-corpus behavior.
- Do not treat live smoke answers as benchmarks or golden answers.
- Do not convert provider pricing or TCO assumptions into production policy.

## 5. Compact Provider Diagnostics Source Candidate

Provider roles today:

- Tavily remains the current ordinary/default retrieval provider path.
- Exa remains a semantic/general/academic specialist path where existing routing
  already uses it.
- Linkup/deeper paths remain bounded to existing behavior and should not be
  promoted by this draft.

Provider diagnostics now implemented:

- Provider role/cost telemetry records provider role, attempts, success/failure
  shape, and cost fields needed for review.
- Follow-up provider/depth route and parity aggregate summaries exist for
  diagnostics.
- Provider overlap/yield telemetry records overlap/yield counts that help
  reviewers reason about marginal source value.

Cost/policy boundaries:

- Provider prices remain disabled/null or zeroed for production behavior.
- `docs/retrieval/provider_role_cost_audit_phase13b.md` remains repo-local
  because it contains dated pricing and TCO assumptions.
- The full provider audit should stay repo-only unless separately refreshed and
  approved.
- This compact candidate does not recommend provider swaps, routing policy,
  pricing policy, procurement policy, or provider escalation policy.

## 6. Eval Harness Source Note

Recommended source note:

- Legacy exit code `-1` means `process_status` unknown.
- A lifecycle event with `run_completed` and `error=null` means
  `pipeline_status` completed.
- stderr text, including NativeCommandError-looking output, is not by itself a
  failure signal.
- Reviewers should read process status and pipeline status as separate axes.

## 7. Historical/Superseded Docs Note

- `docs/history/roadmaps/RETRIEVAL_AND_FAILURE_UX_ROADMAP.md` should be treated as historical and
  repo-only unless explicitly refreshed.
- `docs/history/roadmaps/ROADMAP_IMPLEMENTATION_NOTES.md` should be treated as stale unless
  updated in a later docs-only pass.
- Older retrieval roadmap docs should not be used as active Project Source
  guidance without human review.

## 8. Remaining Priority List

- Six-query diagnostics validation plan, later.
- Query-efficiency policy audit, later and no-edit first.
- CB-002 quantitative semantics audit, no-edit first.
- Quantitative Analyst-cost audit, no-edit first.
- Durable live-run helper/wrapper cleanup, no-edit first.

These are planning/audit priorities only. They do not authorize behavior changes.

## 9. Explicit Non-Changes

This draft makes no changes to:

- Routing.
- Retrieval.
- Providers.
- Prompts.
- Project Sources.
- Source filtering.
- Analyst.
- Economist.
- Author.
- SQLite.
- Replay.
- Summarizer.
- Weak-corpus behavior.
- Live-run answer-quality benchmarks.
- Provider pricing or production cost policy.

No live smoke result should be marked as a benchmark, golden answer, or answer
quality baseline. No provider pricing should be treated as production policy.
