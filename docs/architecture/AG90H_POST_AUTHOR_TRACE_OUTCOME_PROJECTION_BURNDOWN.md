# AG-90H Post-Author Trace / Outcome Projection Burn-Down

## Inspected block

The inspected production block was the deterministic post-Author tail in `core/pipeline_orchestrator.py` after the Author report text, final-answer citation telemetry, weak/failure gate outcome, and AG-90G post-Analyst handoff facts already existed.

## Selected extraction

`core/post_author_output_projection.py` now packages already-computed facts for:

- runtime answer-contract trace attachment inputs;
- weak/failure gate trace fragment projection;
- final-answer citation/runtime handoff projection glue;
- economist, synthesis-evaluator, and Scrutineer handoff trace fragments;
- execution-trace projection, runtime-trace export compatibility attachment, final output metadata, and execution-log entry projection;
- final `RunOutcome` input packaging.

## Size accounting

- `core/pipeline_orchestrator.py` before: 5903 lines.
- `core/pipeline_orchestrator.py` after: 5590 lines.
- Orchestrator reduction: -313 lines.
- Helper line count: 306 lines.
- Production-code delta: +327 / -334, net -7 lines.
- Total repo delta: +690 / -346, net +344 lines including focused AG-90H tests, static-guard test updates, and this architecture note.

## Helper responsibility

The helper has a bounded responsibility: serialize and package post-Author trace/output projections from already-computed runtime facts. It does not perform persistence side effects, provider/model/search calls, prompt construction, citation formatting, final evidence selection, or final answer prose changes.

## Exact projection/output parity proof

`tests/test_ag90h_post_author_output_projection.py` covers representative post-Author inputs and verifies:

- answer-contract, provider diagnostics, weak/failure gate, final-answer packet, citation, economist, synthesis-evaluator, and Scrutineer trace packaging shapes;
- output projection merges trace-packaging runtime fields before invoking execution-trace and execution-log projection helpers;
- static seams prohibit raw global/local scope merges, provider/search/model calls, citation formatting, final evidence selection, cache APIs, and persistence side effects in the helper.

Existing AG-90F/AG-90G tests and the full offline suite were also run.

## Protected surfaces kept closed

This extraction did not move or change:

- Author prompt construction;
- Author model calls;
- final answer prose mutation;
- citation formatting;
- final evidence selection;
- `FinalAnswerPacket` authority semantics;
- retrieval/provider/search/query behavior;
- DB/session writes or persistence side-effect execution.

## Remaining candidates

Remaining deterministic candidates are smaller: additional runtime trace callsite input adapters and legacy static-guard compatibility seams. Further extraction should avoid creating a generic projection framework or a helper larger than the orchestrator surface it removes.
