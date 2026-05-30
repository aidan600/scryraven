# AG-76C-KB-C — KB Review Persistence Context Construction Extraction / Reduction

Date: 2026-05-30

## Scope

AG-76C-KB-C is a parity-preserving KB review persistence-context extraction for
ScryRaven. It reduces the final persistence tail of `core/pipeline_orchestrator.py`
without changing KB behavior, model/provider/search behavior, prompt behavior,
Author/final-answer/citation behavior, DB schema, JSONL/session/SQLite payload
shape, or `RunOutcome` shape.

## Old Orchestrator Block Extracted / Reduced

Before KB-C, the orchestrator constructed the full `KbReviewPersistenceContext(...)`
inline at the tail of `run_pipeline`, immediately before calling
`execute_persistence_side_effects(...)`. That inline field list packaged KB
execution-record inputs, KB trigger inputs, review-agent call dependencies, and
provider/model/base-url/API-key values.

After KB-C, the orchestrator delegates that packaging to
`build_kb_review_persistence_context(...)` and passes only the already-computed
runtime facts mapping plus the two non-local callables that were already used by
the old context handoff.

## New Helper / Module Owner

`core.kb_review_persistence_context` now owns passive KB context and record
construction:

- `KbReviewPersistenceContext`
- `build_kb_review_persistence_context(...)`
- `build_kb_execution_record(...)`
- `build_kb_trigger_entry(...)`
- `flatten_providers_used(...)`

The helper is passive. It performs no persistence writes, no provider calls, no
model calls, no search calls, no prompt construction, no review-agent invocation,
and no decisions about whether KB review should run.

## Exact Behavior Preserved

KB-C preserves:

- exact KB execution-record payload keys and values;
- query, entity, canonical subject, and final-output preview truncation;
- list/dict copy behavior already present in the old payload construction;
- query/provider iteration fields;
- answer flags, corpus flags, recon flags, Scout flags, weak-corpus recovery
  facts, Scrutineer counts, cost, latency, and output preview;
- exact KB trigger-entry payload fields;
- `should_auto_review(...)` evaluation in `core.persistence_side_effects`;
- `kb_review_agent(...)` guard behavior;
- `kb_review_agent(...)` positional argument order;
- provider/model/base-url/API-key values passed to `kb_review_agent(...)`;
- non-fatal warning/error behavior for feedback/review/append/agent/policy/DB
  failures;
- write order: execution JSONL append -> completed log -> policy journal append
  -> KB append/trigger -> SQLite write;
- `execution_log_entry["kb_instrumentation"]` mutation before SQLite conversion;
- `build_run_outcome(...)` handoff of `kb_instrumentation` and `kb_warning`.

## Execution Record Parity Summary

`build_kb_execution_record(...)` contains the old execution-record field mapping.
The parity test uses synthetic long queries/entities/reports, list fields,
provider iteration facts, query iteration facts, answer flags, cost, latency, and
previews, then asserts exact dictionary equality against the legacy field shape.

## Trigger Entry Parity Summary

`build_kb_trigger_entry(...)` contains the old trigger-entry field mapping. The
parity test freezes `timestamp_utc`, supplies synthetic `ReviewFlags`, and asserts
exact dictionary equality including score, fired flag, retrieval yield,
provider flattening, timing copy, and all review-flag fields.

## Agent-Call Guard / Argument Parity Summary

The KB review-agent remains called only from `core.persistence_side_effects` after
`should_auto_review(...)` is evaluated. Tests prove:

- `should_auto_review=False` produces no `kb_review_agent(...)` call;
- `should_auto_review=True` produces exactly one call;
- the call uses the preserved positional tuple:
  `ask_model`, `clean_json_response`, `trigger_entry`, `execution_record`,
  `report`, `fast_provider`, `fast_model`, `local_url`, `or_api_key`.

## Ordering Parity Summary

`execute_persistence_side_effects(...)` still owns side effects and preserves the
old order:

1. execution JSONL append;
2. completed-log append;
3. policy journal append;
4. KB trigger append/review;
5. SQLite write.

A call-recorder test asserts this order exactly.

## SQLite / RunOutcome Handoff Parity Summary

The side-effect helper still mutates `execution_log_entry` with
`kb_instrumentation` before `build_sqlite_row_payload(...)` is called. The
orchestrator still passes the resulting `kb_instrumentation` and `kb_warning` to
`build_run_outcome(...)` without changing `RunOutcome` fields.

## Tests Added / Updated

- Added `tests/test_ag76c_kb_c_persistence_context.py` for KB-C delegation,
  execution-record parity, trigger-entry parity, review-agent guard/argument
  parity, KB warning truncation, non-fatal agent error parity, ordering/SQLite
  handoff parity, protected-import closure, and schema-drift guard.
- Updated `tests/test_ag76c_pe_persistence_side_effects.py` so the static PE
  guard expects the orchestrator to delegate context construction.
- Updated `tests/test_ag76c_bd_orchestrator_burndown.py` to mark KB-C complete
  and select AG-77A as the next recommended phase.

## Protected Surfaces Kept Closed

KB-C did not change provider/search/routing behavior, query strategy,
retrieval/ranking/filtering, prompt behavior, model-call behavior, LLM caching,
Author/final-answer/citation behavior, classifier/currentness semantics,
candidate-fit semantics, Controller/AnswerContract decisions, follow-up behavior,
Scrutineer/Economist behavior, weak-corpus/off-topic/failure-card behavior, DB
schema, `RUN_COLUMNS`, JSONL/session/SQLite/RunOutcome shape, package/CLI/env
compatibility names, or IRS/source-specific behavior.

## LLM Workflow Caching Note

LLM workflow caching remains future design-only under AG-76C-LC. KB-C implements
no cache, no cache lookup, no cache write, no model-call wrapper, and no runtime
caching behavior.

## Recommended Next Phase

Recommended next phase: **AG-77A — Source Conflict Representation Model**.

Rationale: after KB-C, no clearly smaller mechanical post-KB-C AG-76C seam is
selected. AG-76C-LC must remain design-only unless separately licensed.
