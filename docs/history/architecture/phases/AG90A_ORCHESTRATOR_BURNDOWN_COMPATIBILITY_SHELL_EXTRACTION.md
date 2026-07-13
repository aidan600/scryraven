Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG90A_ORCHESTRATOR_BURNDOWN_COMPATIBILITY_SHELL_EXTRACTION).

# AG-90A Orchestrator Burn-Down / Compatibility Shell Extraction

Status: implementation complete; behavior-preserving; no live validation; no provider/model/search calls.

Branch: `ag-90a-orchestrator-burndown-compatibility-shell-extraction`
Base: `main`

## Purpose

AG-90A deliberately reduces `core/pipeline_orchestrator.py` by extracting legacy
compatibility-shell assembly that had remained after AG-89B/C/D/E introduced
Official/Current custody, QueryPlan authority, FinalAnswerPacket authority, and
packet-derived compatibility projections.

The phase goal is not to create a new authority framework. The goal is to keep the
orchestrator as runtime plumbing while moving projection/export assembly into a
bounded helper that serializes already-computed facts.

## Extraction candidates inspected

| Candidate | Estimated removable orchestrator lines | Risk | Decision |
| --- | ---: | --- | --- |
| Final answer / Author / citation packet seam around `build_final_answer_packet`, Author payload derivation, citation-source handoff, and Economist handoff trace refs | ~90-150 | Medium: callsite is close to Author prompt/citation handoff wiring, and closed surfaces forbid Author prose, citation formatting, and FinalAnswerPacket semantics changes | Not selected for this pass beyond preserving existing AG-89D/E wiring |
| Handoff trace attachment cluster (`trace_fields.update(...)` calls for packet/citation/economist fragments) | ~10-30 | Low but too small for AG-90A minimum; extraction alone would create wrapper churn | Not selected alone |
| QueryPlan compatibility plumbing (`queries_by_iteration`, `queries_per_iteration`, stage ledger provider facts) | ~20-50 | Medium: QueryPlan behavior and query text are closed; top-level compatibility keys still have diagnostics consumers | Not selected |
| Post-run session/output/telemetry assembly (`execution_trace` dict and JSONL entry callsite) | ~250-300 | Low-to-medium: projection-only, after retrieval/Author/citation decisions are already complete; no provider/search/prompt behavior involved | Selected |
| Obsolete compatibility mirrors from Official/Current custody or FinalAnswerPacket | Unknown without a deeper consumer audit | Medium-high: bridge/source-obligation telemetry still has repo-visible diagnostics consumers | Deferred |

## Selected extraction

AG-90A extracts the final post-run trace and execution-log compatibility assembly
from `core/pipeline_orchestrator.py` into `core/session_output_projection.py`.
The orchestrator now calls:

- `build_execution_trace_projection(locals())`
- `build_execution_log_entry_projection(...)`

Both helpers are projection-only. They receive runtime facts that are already
computed by the pipeline, preserve legacy key names and payload values, and return
compatibility payloads for existing session/output/export consumers.

## Before/after line counts

- `core/pipeline_orchestrator.py` before AG-90A: **7,727** lines.
- `core/pipeline_orchestrator.py` after AG-90A: **7,434** lines.
- Net orchestrator delta: **-293** lines.

## Surfaces moved out of the orchestrator

Moved to `core/session_output_projection.py`:

- legacy `execution_trace` dict assembly;
- packet/citation/economist/supplemental/scrutineer trace-fragment stitching inside the final execution trace;
- source-tier/source-domain compatibility projection keys;
- source-survival official/canonical count helper;
- JSONL `build_execution_log_entry(...)` argument plumbing;
- source-class recovery validation trace-key wiring for the execution log entry.

The orchestrator still computes runtime facts and invokes persistence side effects,
but it no longer hosts the final compatibility export dictionary.

## Helper/adapter responsibilities

`core/session_output_projection.py` is a bounded projection helper. It may:

- serialize already-computed run facts into the existing execution-trace shape;
- preserve QueryPlan-derived compatibility keys such as `queries_per_iteration`;
- preserve packet-derived trace fragments from `FinalAnswerPacket`;
- preserve legacy JSONL execution-log packaging by delegating to
  `build_execution_log_entry(...)`.

It must not:

- select providers or search depth;
- generate or mutate queries;
- run retrieval, search, model, or provider calls;
- choose evidence, citations, answer posture, or Author instructions;
- alter prompts, final prose, citation formatting, or source ranking.

## Behavior-preservation proof

The extraction is behavior-preserving because the moved code is pure assembly over
already-computed values. The new helper copies the same keys, coercions, list/dict
materialization, trace-fragment merges, and source-survival max-count semantics from
the old orchestrator block.

Focused AG-90A tests assert that:

- QueryPlan compatibility keys still appear in the execution trace;
- FinalAnswerPacket trace fragments still appear in the execution trace;
- source-survival official/canonical count semantics match the legacy max-count
  behavior;
- the execution JSONL entry keeps the legacy event, query, execution-trace, source
  recovery validation, and code-version metadata shapes.

Existing AG-89B/C/D tests were also run to confirm custody, QueryPlan, and
FinalAnswerPacket behavior remained intact.

## Protected surfaces kept closed

AG-90A did not change:

- provider routing, provider selection, provider depth, or provider swap behavior;
- query generation text or QueryPlan-authorized query text;
- Official/Current custody semantics;
- FinalAnswerPacket authority semantics;
- retrieval ranking/filtering;
- evidence selection quality;
- citation formatting;
- Author prompt text or final answer prose;
- Analyst/Economist/Scrutineer behavior;
- cache reuse or ProjectSource retrieval.

No live validation and no provider/model/search calls were run.

## Static guard updates

Several older static diff guards encoded phase-specific "orchestrator unchanged"
expectations. AG-90A explicitly licenses bounded behavior-preserving extraction from
`core/pipeline_orchestrator.py`, so those guards were updated to allow diffs that
contain `session_output_projection` while still rejecting unrelated provider/search,
prompt, Author, citation, or policy rewrites.

## Remaining high-value extraction candidates

1. Extract the final-answer / Author / citation packet runtime seam once downstream
   consumers can read a smaller packet-derived handoff directly.
2. Audit and demote `queries_per_iteration` consumers to QueryPlan-native trace keys,
   then delete the top-level compatibility mirror.
3. Audit official/current source-obligation bridge telemetry consumers and fold
   remaining bridge satisfaction summaries behind custody projections.
4. Extract Scrutineer remediation and supplemental-search trace-fragment preparation
   only if doing so removes policy-neutral assembly without changing remediation,
   citation, or final evidence behavior.
5. Replace any remaining trace-only wrappers with direct projections from canonical
   authority states where consumer audits prove the mirror is obsolete.

## Recommended next phase

AG-90B should perform a consumer audit for QueryPlan and official/current
source-obligation compatibility mirrors. The preferred next deletion is a measured
collapse of top-level query/source-obligation trace mirrors after tests and runtime
exports are updated to consume canonical `query_plan` and custody projections.
