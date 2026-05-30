# AG-76C-OP Outcome / Persistence Packaging Extraction

Date: 2026-05-30

## Scope

AG-76C-OP extracted mechanical outcome and persistence packaging from
`core/pipeline_orchestrator.py` into `core.outcome_persistence_packaging`.
This is an orchestrator-strangling extraction only: JSONL, SQLite, session,
RunOutcome, and final-output metadata shapes are intended to remain unchanged.

The phase did not change provider/search behavior, model calls, query strategy,
source classification, candidate fit, Controller decisions, AnswerContract
behavior, prompt behavior, Author behavior, citation selection/formatting,
final-answer prose, live validation, DB schema, or UI compatibility names.

## Extracted Seam

`core.outcome_persistence_packaging` now owns packaging for already-computed run
facts:

- `build_pipeline_config(...)` packages the legacy `pipeline_config` dict shared
  by the session payload and `RunOutcome`.
- `build_final_output_metadata(...)` packages `latency_seconds`,
  `output_word_count`, `final_output_preview`, and `cost`.
- `build_session_payload(...)` packages the legacy session blob saved by callers.
- `build_execution_log_entry(...)` packages the JSONL execution event and its
  compatibility aliases from already-computed trace and telemetry facts.
- `build_sqlite_row_payload(...)` maps the JSONL execution event through the
  existing `core.db.execution_jsonl_to_run_row(...)` row conversion without
  changing `RUN_COLUMNS`.
- `build_run_outcome(...)` packages the `RunOutcome` dataclass return value.

`core/pipeline_orchestrator.py` now delegates the existing write calls and handoffs
to `core.persistence_side_effects` before returning the packaged `RunOutcome`.

## Helper Contract

The helper is packaging-only. It may receive already-computed run facts, trace,
report text, citations/source telemetry, costs, warnings, session data, and
compatibility fields, then assemble dictionaries, SQLite rows, and RunOutcome
objects.

The helper must not choose providers, call models, run search, alter retrieval
depth, classify sources, evaluate candidate fit, decide Controller or
AnswerContract posture, select citations, edit final answer prose, invoke Author,
perform live validation, or inspect secrets/local private artifacts.

## Parity Evidence

`tests/test_ag76c_op_outcome_persistence_packaging.py` covers:

- session payload key order and shared `pipeline_config` shape;
- execution JSONL field shape, final-output preview/word-count packaging, and
  legacy trace-derived aliases;
- SQLite row conversion preserves `RUN_COLUMNS` coverage;
- `RunOutcome` exposes the dataclass field set unchanged;
- static helper import guard against provider/search/prompt/routing/Author/final
  evidence/protected behavior modules;
- static orchestrator guard that the packaging seam delegates to the helper and
  that AG-76C-RT runtime trace/export attachment remains delegated to
  `core.runtime_trace_export_attachment`.

## Protected Surfaces Kept Closed

AG-76C-OP did not change:

- DB schema or `RUN_COLUMNS`;
- JSONL schema other than moving assembly into the helper;
- session payload schema other than moving assembly into the helper;
- `RunOutcome` fields;
- final answer prose, citation formatting, citation selection, or Author logic;
- Controller, AnswerContract, follow-up, Scrutineer, Economist, classifier,
  candidate-fit, provider/search/query/routing/depth behavior;
- live validation or provider/model/search calls.

## What Remains In `core/pipeline_orchestrator.py`

The orchestrator still builds the large runtime trace from local run facts, but
persistence side-effect execution now delegates to `core.persistence_side_effects`.
Runtime trace/export/checkpoint compatibility remains owned by
`core.runtime_trace_export_attachment`.

## Next Deletion Target

The next safe deletion target is to reduce the large passive KB persistence
context handoff after a dedicated phase proves KB execution-record and trigger
entry parity. Protected behavior surfaces should remain closed.
