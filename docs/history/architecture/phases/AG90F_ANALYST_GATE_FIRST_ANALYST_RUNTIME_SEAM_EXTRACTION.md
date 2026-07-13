Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG90F_ANALYST_GATE_FIRST_ANALYST_RUNTIME_SEAM_EXTRACTION).

# AG-90F — Analyst Gate / First Analyst Runtime Seam Extraction

## Inspected block

The inspected runtime was the Analyst-stage handoff in `core/pipeline_orchestrator.py` immediately after Analyst cached-prefix assembly and before the legacy synthesis-evaluator / Scrutineer runtime stage. The block owned:

- pre-Analyst source-tier/domain telemetry and retrieval gate evaluation;
- pre-gate failure-card payload calculation for downstream handoffs;
- post-Economist Analyst gate telemetry;
- Economist handoff execution before Analyst;
- Analyst gate descriptor and trace handoff projection;
- unsupported-retrieval Author directive fallback;
- low-complexity `DIRECT_TO_AUTHOR` fallback;
- weak-corpus estimate-from-priors Analyst call;
- normal first Analyst call;
- Analyst context measurement, model-call telemetry, and timing accumulation.

## Selected extraction

AG-90F extracts that coherent block into `core/analyst_runtime_stage.py`:

- `AnalystRuntimeDeps` carries injected runtime callables (`ask_model`, context measurement, Analyst model-call recording, evidence slicing, and gate callables).
- `AnalystRuntimeRequest` is a bounded value wrapper over the stage-local request mapping.
- `AnalystRuntimeOutcome` returns only the orchestrator locals needed by downstream handoffs.
- `execute_analyst_runtime_stage(...)` is the direct tested entrypoint.
- `execute_analyst_runtime_stage_from_scope(...)` is the orchestrator adapter; it whitelists local names and does not accept or pass `globals()`.

The orchestrator now builds the cached Analyst prefix, creates the Analyst model-call recorder, invokes the stage helper, and assigns the returned handoff/runtime values before continuing to the already-extracted AG-90E legacy review runtime stage.

## Line counts and deltas

- `core/pipeline_orchestrator.py` before: **6,580** lines.
- `core/pipeline_orchestrator.py` after: **6,235** lines.
- Orchestrator reduction: **-345** lines.
- `core/analyst_runtime_stage.py`: **380** lines.
- Production-code delta: `core/pipeline_orchestrator.py` **+51/-396** plus new helper **+380**, for a net **+35** production lines.
- Total repo delta before commit: production **+35** lines plus focused tests and this architecture note.

## Helper responsibilities

`core/analyst_runtime_stage.py` is intentionally bounded to executing already-determined stage plumbing:

- computes the legacy pre-Analyst failure-card inputs;
- executes the existing pre-Analyst retrieval gate;
- executes the existing post-Economist Analyst gate telemetry;
- builds and executes the Economist handoff before Analyst;
- builds the Analyst gate descriptor and trace projection;
- applies the unsupported-retrieval directive branch;
- applies the low-complexity direct-to-Author branch;
- executes the weak-corpus estimate-from-priors first Analyst model call;
- executes the normal first Analyst model call;
- preserves Analyst timing accumulation and context-measurement calls;
- preserves Analyst model-call telemetry mutation.

The helper does **not** own provider selection, retrieval, search-depth policy, query planning, query mutation, final evidence selection, citation formatting, Author prompt/prose, final-answer packet semantics, cache reuse, or ProjectSource retrieval.

## Exact Analyst prompt/model-call parity proof

Focused AG-90F tests directly exercise the helper with injected fakes and assert exact parity for representative paths:

1. Unsupported retrieval / Analyst skipped:
   - exact unsupported analysis string from `build_unsupported_retrieval_prompt_fragments(...)`;
   - exact Author note append;
   - preserved skip reason, fast-path flag, and no Analyst call.
2. Low complexity:
   - exact `DIRECT_TO_AUTHOR` analysis;
   - no Analyst model call, no context-measurement call, and no model-call telemetry record.
3. Estimate-from-priors Analyst:
   - exact `build_analyst_prompt(..., estimate_from_priors=True)` output;
   - exact `DEFAULT_SYSTEM["analyst_estimate_from_priors"]` system text;
   - exact `ask_model(...)` kwargs for `provider`, `model`, `effort`, `base_url`, `api_key`, and `use_reasoning`;
   - exact context-measurement stage name and stable-prefix wiring;
   - exact positive elapsed-time addition pattern.
4. Normal Analyst:
   - exact normal `build_analyst_prompt(...)` output;
   - exact `DEFAULT_SYSTEM["analyst"]` system text;
   - exact `ask_model(...)` kwargs;
   - exact context-measurement stage name and stable-prefix wiring;
   - exact positive elapsed-time addition pattern.
5. Economist handoff / post-Economist gate:
   - Economist handoff state values are copied through unchanged;
   - `economist_output_used_as_analysis` remains shadow/false;
   - post-Economist Analyst skip remains disabled.

## Protected surfaces kept closed

AG-90F did not change:

- prompt text;
- Analyst model-call shape;
- provider/model/effort/base-url/api-key/use-reasoning plumbing;
- provider selection or routing;
- search-depth policy;
- QueryPlan query text/order;
- retrieval ranking/filtering;
- final evidence selection;
- citation formatting;
- Author prose/style/posture;
- official/current custody behavior;
- `FinalAnswerPacket` semantics;
- cache reuse;
- ProjectSource retrieval.

No live validation, provider calls, model calls, or search calls were run.

## Static seam guards

The AG-90F static guard verifies:

- `core/pipeline_orchestrator.py` line count remains below the pre-phase 6,580-line baseline;
- no `{**globals(), **locals()}` pattern;
- no `globals()` use in the Analyst seam helper or orchestrator;
- helper imports no provider-routing or search-provider modules;
- helper does not call provider selection, supplemental search-depth selection, search dispatch, or citation formatting;
- orchestrator invokes the scope adapter with `locals()` only;
- tests use injected fakes for `ask_model(...)`.

## Remaining extraction candidates

Potential next seams remain downstream of AG-90F:

- diet the Analyst runtime helper further if later phases move shared gate telemetry primitives into narrower contracts;
- extract remaining final answer / Author handoff compatibility assignments that are already delegated to AG-90A/90B helpers but still have orchestration glue;
- continue shrinking telemetry packaging and execution-trace projection callsites without changing final answer behavior.

## Recommended next phase

Recommended next phase: extract a small, bounded post-Analyst handoff assignment seam that only packages already-computed Analyst/Economist gate outputs for downstream Author/citation handoffs. Keep Author prompt construction, evidence selection, citation formatting, and final-answer packet semantics closed.
