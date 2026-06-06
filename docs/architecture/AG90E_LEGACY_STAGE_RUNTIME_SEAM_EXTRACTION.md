# AG-90E Legacy Stage Runtime Seam Extraction

Status: behavior-preserving extraction; no live validation; no provider/model/search calls during development/testing

Branch: `ag-90e-legacy-stage-runtime-seam-extraction`

Base: merged AG-90D-R1 / PR #93 (`556c03f`, `Merge pull request #93 from aidan600/codex/reduce-retrieval-dispatch-helper-bloat`)

## Purpose

AG-90E continues the orchestrator burn-down after the AG-90D-R1 retrieval-dispatch helper diet.  The phase moves the legacy synthesis-evaluator / supplemental-search / Scrutineer remediation runtime stage out of `core/pipeline_orchestrator.py` while preserving exact prompt text, model-call arguments, provider/search selection, retrieval-dispatch shape, evidence rebuild behavior, Analyst rerun behavior, telemetry updates, citation behavior, and final-answer behavior.

The helper executes an already-authorized legacy stage.  It does not decide whether the stage should run outside the exact moved gate, does not introduce a stage engine, and does not own provider routing, query generation policy, search depth policy, evidence ranking/filtering, citation formatting, Author posture, or a new authority framework.

## Candidate blocks inspected

| Candidate | Approx. removable orchestrator lines inspected | Risk | Decision |
| --- | ---: | --- | --- |
| Scrutineer / remediation runtime stage | ~205 | High custody: Scrutineer model call, remediation-query model call, remediation retrieval, evidence rebuild, Analyst rerun | Extracted as part of one adjacent legacy review runtime stage with call-shape tests |
| Synthesis evaluator / supplemental-search runtime stage | ~140 | High custody: evaluator model call, supplemental query finalization, supplemental retrieval, evidence rebuild, Analyst rerun, Author hedge note | Extracted as part of the same adjacent legacy review runtime stage with call-shape tests |
| Linkup + Economist preflight quantitative component | ~120-170 | Higher risk: Linkup provider boundary and Economist skip/author-note behavior are sensitive | Not selected |
| Retrieval-loop telemetry reducer | ~60-100 | Lower risk but too small for AG-90E target | Not selected |

## Selected stage

Selected extraction: the adjacent legacy review runtime stage covering:

- synthesis completeness eligibility and strong-retrieval skip telemetry;
- synthesis-evaluator prompt assembly via the existing AG-90C prompt helper;
- synthesis-evaluator JSON model call and parse/deficiency handling;
- QueryPlan supplemental finalization;
- supplemental provider selection as the same injected `select_providers(...)` call shape;
- supplemental retrieval dispatch via the AG-90D `execute_supplemental_search_from_scope(...)` helper;
- supplemental evidence rebuild and Analyst rerun;
- Scrutineer prompt assembly via the existing AG-90C prompt helper;
- Scrutineer JSON model call and high-flag threshold handling;
- remediation-query prompt/model call;
- novelty filtering and QueryPlan remediation finalization;
- remediation retrieval dispatch via the AG-90D `execute_scrutineer_remediation_from_scope(...)` helper;
- remediation evidence rebuild and Analyst rerun.

## Before / after line counts

- Before: `core/pipeline_orchestrator.py` had **6,920** lines on the AG-90D-R1 baseline.
- After: `core/pipeline_orchestrator.py` has **6,565** lines.
- Net orchestrator delta: **-355 lines**.

This meets the AG-90E minimum target of at least `-350` net orchestrator lines.

## Production-code and total deltas

Production code:

- `core/pipeline_orchestrator.py`: 10 additions / 365 deletions, **-355 net lines**.
- `core/legacy_review_runtime_stage.py`: new bounded helper, **+498 lines**.
- Production-code net delta: **+143 lines**.

Helper-growth discipline:

- Removed orchestrator production lines: **365**.
- New helper production lines: **498**.
- Helper over removed lines: **+133**, within the phase's `~150` helper-growth budget.

Total repo delta after tests and this architecture note:

- Production code net: **+143**.
- Test code net before this note: `tests/test_ag90e_legacy_review_runtime_stage.py` adds 401 lines; static-guard updates add 18 net lines.
- Documentation net: this file.

## Helper responsibilities

`core/legacy_review_runtime_stage.py` provides:

- `LegacyReviewRuntimeDeps` — injected model, prompt-measurement, evidence rebuild, provider-selection, retrieval-dispatch, and timing callables.
- `LegacyReviewRuntimeRequest` — explicit caller-owned state for the moved legacy stage.
- `LegacyReviewRuntimeOutcome` — updated caller-owned fields that the orchestrator reassigns in the old local-variable shape.
- `execute_legacy_review_runtime_stage(...)` — direct bounded stage entrypoint tested with fakes.
- `execute_legacy_review_runtime_stage_from_scope(...)` — strict-whitelist compatibility wrapper for the orchestrator's current runtime locals/globals seam.

The helper consumes existing providers, models, API-key/base-URL values, search depth, QueryPlan adapter, telemetry collector, and retrieval helper callables.  It does not import provider routing modules, search provider integrations, broad orchestrator modules, `DEFAULT_SYSTEM` mutation surfaces, or live model clients.

## Exact prompt/model/search parity proof

Focused AG-90E tests in `tests/test_ag90e_legacy_review_runtime_stage.py` verify:

- exact synthesis-evaluator prompt string from `build_synthesis_evaluator_prompt(...)`;
- exact synthesis-evaluator system prompt and `ask_model(...)` argument shape: provider, model, effort, base URL, API key, `require_json`, and `use_reasoning`;
- exact supplemental provider-selection argument shape and supplemental retrieval-dispatch argument shape;
- exact supplemental Analyst rerun model-call shape;
- exact Scrutineer prompt string/system prompt and model-call shape, including `require_json=True` and `use_reasoning=False`;
- high-flag threshold behavior that passes flags directly to Author without remediation dispatch;
- exact remediation-query prompt string/system prompt and remediation model-call shape;
- duplicate remediation-query rejection telemetry without retrieval dispatch;
- remediation retrieval-dispatch argument shape, dispatch posture/provider-role/depth telemetry, evidence rebuild, and Analyst resynthesis shape;
- helper static guards: orchestrator line-count burn-down, no provider-routing/search-provider imports, no `process_search_queries(...)`, no `core.prompts` import, and the orchestrator uses the bounded helper seam.

Existing AG-76D/AG-90C/AG-90D static guards were updated to recognize that the stage-local collector calls and remediation-query fact construction now live in the bounded helper, while the trace handoff assembly remains in the orchestrator.

## Protected surfaces kept closed

AG-90E did not change:

- prompt text;
- provider routing or provider selection policy;
- provider depth/search-depth policy;
- QueryPlan-authorized query text/order;
- supplemental/remediation retrieval helper call shapes;
- retrieval ranking/filtering;
- final evidence selection semantics;
- citation formatting;
- Author prose/style/posture;
- official/current custody semantics;
- `FinalAnswerPacket` authority semantics;
- cache reuse;
- ProjectSource retrieval;
- model/provider/search integrations.

No live provider/model/search validation was run.

## Remaining high-value extraction candidates

1. **Primary Analyst gate + first Analyst runtime call** — adjacent to the extracted stage and still high-value, but it contains pre-Analyst gate/economist handoff interactions that should be extracted under a dedicated Analyst-gate parity phase.
2. **Linkup + Economist quantitative component** — meaningful line-count opportunity, but sensitive because it spans provider preflight, quantitative schema telemetry, and Author note behavior.
3. **Source-class recovery and weak-corpus recovery telemetry reducers** — likely safer, but smaller and should be coordinated with source-custody consumers.
4. **Author prompt and final packet residual wiring** — further reduction possible only with strict prompt/final-answer invariance tests.

## Recommended next phase

Run an AG-90F Analyst Gate / First Analyst Runtime Seam phase that extracts the pre-Analyst gate, post-Economist gate, and first Analyst call into a bounded helper with exact prompt/model-call parity tests.  Keep provider/search/query/citation/Author behavior closed and avoid reintroducing broad retrieval-dispatch scope wrappers removed by AG-90D-R1.
