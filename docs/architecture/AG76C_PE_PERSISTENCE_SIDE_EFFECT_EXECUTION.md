# AG-76C-PE Persistence Side-Effect Execution Handoff

Date: 2026-05-30

## Scope

AG-76C-PE extracted mechanical persistence side-effect execution from
`core/pipeline_orchestrator.py` into `core.persistence_side_effects` while
leaving payload packaging in `core.outcome_persistence_packaging`.

This was an orchestrator-strangling extraction only. JSONL execution-log shape,
policy journal shape, KB trigger shape, SQLite row/session shape, `RunOutcome`
shape, write ordering, and non-fatal error behavior are intended to remain
unchanged.

## Extracted Seam

`core.persistence_side_effects.execute_persistence_side_effects(...)` now owns the
already-authorized persistence writes that previously lived at the final
orchestrator tail:

1. append the already-built execution JSONL payload;
2. call `log_run_completed(...)`;
3. append the policy journal entry inside the same non-fatal warning guard;
4. append KB trigger logging and optional existing KB review callable behavior
   inside the same non-fatal warning guard;
5. mutate the already-built execution entry with `kb_instrumentation` when the KB
   side effect succeeds, as before;
6. under the existing DB-enabled gate, build the SQLite row through
   `core.outcome_persistence_packaging.build_sqlite_row_payload(...)`, ensure the
   telemetry schema, connect, `insert_run`, `upsert_session`, commit, and close;
7. log SQLite failures as non-fatal errors.

`KbReviewPersistenceContext` is a passive handoff object for KB trigger inputs.
`PersistenceSideEffectResult` returns passive result values needed by the
orchestrator tail (`execution_log_entry`, `kb_instrumentation`, `kb_warning`, and
`sqlite_row_written`).

## Helper Contract

The helper is side-effect-only. It may receive already-computed execution log
entries, policy payload inputs, KB trigger inputs, trace timing, report text,
telemetry paths, DB flags, and callables needed to preserve the existing KB
review path. It may execute the same persistence writes in the same order.

The helper must not choose providers, run search, alter retrieval depth,
classify sources, evaluate candidate fit, decide Controller or AnswerContract
posture, select citations, edit final-answer prose, invoke Author behavior,
introduce model calls, perform live validation, or inspect secrets/local private
artifacts. The existing KB review callable is passed in and invoked only under
the same guard conditions as the pre-extraction orchestrator block.

## Parity Evidence

`tests/test_ag76c_pe_persistence_side_effects.py` covers:

- execution JSONL append receives the already-built payload;
- `log_run_completed(...)` remains ordered immediately after execution JSONL
  append;
- policy journal append remains after completion logging and before KB trigger
  logging;
- policy journal failures remain non-fatal warnings;
- KB trigger failures remain non-fatal warnings;
- DB-disabled runs skip SQLite writes;
- DB-enabled writes call schema ensure, connect, insert, upsert, commit, and
  close in order;
- SQLite failures remain non-fatal errors;
- `kb_instrumentation` still mutates the execution entry after KB logging for
  downstream SQLite/RunOutcome handoff;
- static import guards keep protected provider/search/prompt/routing/Author/final
  answer modules out of the new helper;
- static orchestrator guards prove the moved append/log/SQLite/error-handling
  block is no longer inlined in `core/pipeline_orchestrator.py`;
- static packaging guards prove `core.outcome_persistence_packaging` remains
  packaging-only and did not absorb side-effect execution.

## What Remains In `core/pipeline_orchestrator.py`

The orchestrator still assembles run facts, delegates session/execution/SQLite
row/RunOutcome packaging to `core.outcome_persistence_packaging`, delegates
runtime trace/export/checkpoint attachment to `core.runtime_trace_export_attachment`,
constructs the passive `KbReviewPersistenceContext`, calls
`execute_persistence_side_effects(...)`, and passes the returned
`kb_instrumentation` / `kb_warning` into `build_run_outcome(...)`.

## Protected Surfaces Kept Closed

AG-76C-PE did not change:

- DB schema or `RUN_COLUMNS`;
- JSONL, policy journal, KB trigger, session, SQLite row, or `RunOutcome` field
  shapes;
- final answer prose, citation formatting, citation selection, or Author logic;
- Controller, AnswerContract, follow-up, Scrutineer, Economist, classifier,
  candidate-fit, provider/search/query/routing/depth behavior;
- live validation or provider/model/search calls.

## Next Deletion Target

The next deletion target is the passive `KbReviewPersistenceContext` construction
at the orchestrator tail. A future phase can reduce that large handoff only if it
can prove the KB execution-record payload and trigger-entry payload stay
unchanged without opening Controller, provider/search, prompt, Author, citation,
or final-answer behavior.
