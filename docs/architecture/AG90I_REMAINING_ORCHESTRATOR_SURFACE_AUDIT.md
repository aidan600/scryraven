# AG-90I — Remaining Orchestrator Surface Audit / Stop-Go Map

## Scope and constraints

This is a static architecture audit of the remaining
`core/pipeline_orchestrator.py` surface after AG-90A through AG-90H. It is
intentionally docs-first and does not implement any extraction, runtime rewrite,
provider/model/search behavior change, or live validation.

## Static inventory

- Current `core/pipeline_orchestrator.py` line count: **5,590** lines.
- Public entry point: `run_pipeline(...)` remains a compatibility shell at lines
  **1941-2008**.
- Monolithic runtime body: `_run_pipeline_inner(...)` remains at lines
  **2011-5590**.
- Direct model callsites remaining in this file: **9** static `ask_model(...)`
  callsites at lines **2221, 2241, 2374, 2434, 2540, 4041, 4133, 4795, 5188**.
- Direct embedding callsites remaining in this file: **1** static
  `embed_texts(...)` callsite at line **2670**.
- Direct final persistence side-effect callsite remaining in this file: **1**
  static `execute_persistence_side_effects(...)` callsite at line **5566**.
- Direct final session payload callsite remaining in this file: **1** static
  `build_session_payload(...)` callsite at line **5389**.
- Direct final evidence bundle callsite remaining in this file: **1** static
  `build_final_evidence_bundle(...)` callsite at line **4734**.
- Direct Author prompt assembly callsite remaining in this file: **1** static
  `build_author_prompt_from_scope(...)` callsite at line **5126**.
- Direct final Author runtime assembly callsite remaining in this file: **1**
  static `assemble_final_answer_author_runtime_from_scope(...)` callsite at
  line **5142**.
- Static repo search used only local file content. No live provider, model,
  search, or validation calls were run.

## Classification legend

- **Must remain for now**: compatibility shell, side-effect execution,
  persistence/DB/session writes, live model/provider callsites requiring an
  explicit phase license, or protected product behavior.
- **Safe burn-down candidate**: deterministic projection glue, trace attachment
  grouping, compatibility alias packaging, or already-computed runtime fact
  serialization.
- **Authority-collapse candidate**: remaining places where the orchestrator
  decides query behavior, provider/depth behavior, source satisfaction,
  evidence selection, citation eligibility, final posture, or Author
  instructions.
- **Product behavior phase candidate**: provider/search/depth,
  retrieval ranking/filtering, final evidence selection, citation formatting,
  Author prose/style, or official/current acquisition quality.
- **Deletion/demotion candidate**: duplicate trace-only wrappers, stale
  compatibility mirrors, or static guards freezing old scaffolding.

## Major remaining blocks by line range

| # | Line range | Current responsibility | Classification | Remain/move judgment | Extraction risk | Expected orchestrator reduction if moved | Expected helper growth risk | Required parity tests | Recommended phase |
|---|---:|---|---|---|---|---:|---|---|---|
| 1 | 1-296 | Module contract, imports, constants, aliases, private compatibility exports, and `PipelineError`. | Must remain for now + deletion/demotion candidate for stale mirrors. | Keep imports/constants local unless a future cleanup proves an alias is stale. Demote only compatibility mirrors with consumer inventory. | Medium: import ordering and re-export compatibility tests are fragile. | 0-80 lines. | Low if deleting; medium if moved into a facade. | Static import/consumer search; import smoke test; compatibility import tests for any removed alias. | Pause unless a stale-compat cleanup phase is explicitly scoped. |
| 2 | 303-600 | Retrieval-stop defaults, active/shadow telemetry builders, active decision serialization, and alignment glue. | Safe burn-down candidate. | Move only as a deterministic projection package if it stays subordinate to `retrieval_stop_controller`. It should not re-own stop/continue authority. | Low/medium: many fields are trace-compatibility sensitive. | 180-250 lines. | Medium: helper could become a trace mirror unless field ownership is narrow. | Exact dict parity for active/shadow/stop-no-queries/budget-exhausted fixtures; static guard that no provider/search/model calls enter helper. | Best next safe burn-down candidate. |
| 3 | 602-1174 | Weak-corpus, conflict-resolution, targeted-retrieval, ordinary-continuation, and evidence-integration lifecycle fact projections from runtime/controller objects. | Safe burn-down candidate with authority-collapse watchpoints. | Most of this is already-computed runtime fact serialization and can move, but any logic that interprets source fit/currentness must remain subordinate to controller-owned decisions. | Medium: source-fit and lifecycle keys are high-value diagnostics. | 350-520 lines. | High: helper may grow into an omnibus lifecycle serializer. | Golden fixture parity for each lifecycle dict; controller-authority static guards; trace-key stability assertions. | Safe burn-down phase after block 2, or split into targeted/weak/conflict slices. |
| 4 | 1176-1424 | Authoritative-source checkpoint allowlist, year/time utilities, retrieval/search-depth selectors, and weak-corpus recovery seed-query construction. | Authority-collapse candidate + product behavior phase candidate. | Do not extract as a generic helper yet. Search-depth and recovery seed query behavior are product/authority surfaces and should move only under a phase licensed to alter or collapse that authority. | High: moving may accidentally freeze or duplicate query/depth policy. | 120-220 lines if moved. | Medium/high: helper could become a hidden policy engine. | Existing behavior fixtures for depth, supplemental depth, checkpoint allowlist, seed query ordering/deduplication; product acceptance for query quality. | Best authority-collapse/product candidate, but not a docs-only burn-down. |
| 5 | 1426-1934 | Nutrition constants, quantitative/fallback directives, final-answer source citation telemetry, Economist skip-candidate telemetry, Analyst quantitative packet serialization, and timing payloads. | Safe burn-down candidate + protected behavior for nutrition/fallback copy. | Deterministic serialization can move, but fallback directives and nutrition unit mappings are product-facing and should be touched only with exact copy/text parity. | Medium: Author-visible fallback text and telemetry keys are brittle. | 250-420 lines. | Medium: packet helper could accumulate product copy. | Exact string parity for fallback directives; telemetry dict parity; nutrition lookup fixtures; citation telemetry fixtures. | Safe burn-down if scoped to serialization only; product-copy changes deferred. |
| 6 | 1941-2008 | `run_pipeline(...)` public compatibility shell, policy loading, error logging/wrapping, and delegation into `_run_pipeline_inner(...)`. | Must remain for now. | Keep. This is the stable public entry point and compatibility shell. Shrinking it further is not useful until the inner runtime is substantially smaller. | High if changed: public API and failure behavior. | 0-30 lines. | Low if unchanged; high if facade layering is added. | Public API smoke tests; expected-failure logging/wrapping parity. | Stop/pause surface; do not extract yet. |
| 7 | 2011-2158 | `_run_pipeline_inner(...)` signature, config/dependency unpacking, cost-accounting wrappers, context measurement, model-call telemetry, and run metadata setup. | Must remain for now + side-effect integration. | Keep near the runtime because it binds injected deps, cost phases, and live call wrappers. Move only when a complete runtime context object exists. | High: call accounting, token measurement, and status side effects can regress silently. | 80-140 lines if a context object is introduced. | High: likely creates a large mutable context helper. | Cost phase parity, provider diagnostic parity, context measurement parity, status-message order tests. | Do not extract yet. |
| 8 | 2161-2670 | Pre-retrieval routing, router retry, nutrition override, strategy complexity/depth budgets, title generation, recon search/rewriter, query-plan finalization, recency merge, retrieval state initialization, and first embedding. | Authority-collapse/product phase candidate + protected behavior. | Do not move as burn-down. This block owns live model/search/embedding callsites and query/provider/depth behavior. It needs explicit provider/search/depth/query authority phase licensing. | Very high: alters query behavior, budgets, title/recon calls, or embedding cadence. | 400-650 lines if moved. | Very high: likely creates an orchestration clone. | Full offline parity for router/retry/recon/planner/recency; provider kwarg parity; query order/dedup parity; no-live-call static guards. | Best next authority-collapse/product phase if licensed. |
| 9 | 2682-3670 | Retrieval-loop local controller adapters, checkpoint timing, dispatch inputs, provider availability, source-class telemetry refresh, and retrieval batch dispatch/merge mechanics. | Authority-collapse candidate + side-effect integration + product behavior phase candidate. | Do not extract as a wrapper. Collapse only bounded authority leaks into existing controllers/dispatch helpers, preserving the orchestrator as executor of live retrieval side effects. | Very high: interleaves controller traces, search dispatch, provider diagnostics, source ranking, and corpus-state mutation. | 500-850 lines if moved wholesale, but only 100-250 lines should be safe in small slices. | Very high: wrapper extraction would recreate the monolith. | Retrieval dispatch parity, provider diagnostics parity, all_passages ordering, source-class telemetry parity, controller trace parity. | Explicit authority-collapse/product phase, not safe burn-down. |
| 10 | 3671-4308 | Main retrieval loop continuations: disambiguation, weak-corpus recovery, conflict-resolution recovery, Scout, Query Expander, Gap Evaluator, active retrieval-stop, supplemental query finalization, and loop termination. | Authority-collapse candidate + product behavior phase candidate. | Do not extract yet. This is where the orchestrator still coordinates query behavior and live model/search callsites. Future work should collapse remaining decisions into query/retrieval controllers rather than move the loop wholesale. | Very high: query text/order, iteration counts, stop/continue, and source satisfaction are product-critical. | 500-800 lines if moved wholesale; safer reduction is 100-200 lines from trace packaging only. | Very high if a loop helper owns too many locals. | Continuation query parity; Scout/Expander/Evaluator prompt kwarg parity; retrieval-stop active/shadow parity; weak/conflict recovery trace parity. | Product/authority phase after pre-retrieval authority is mapped. |
| 11 | 4309-4733 | Post-retrieval source-tier/domain/source-class telemetry refresh, controller lifecycle projections, conflict/source-class recovery bridges, corpus/failure-card facts, and final evidence bundle inputs. | Safe burn-down candidate with final-evidence authority boundary. | Projection glue can move if final evidence selection stays in `final_evidence_bundle_builder` and controller decisions stay authoritative. Avoid moving evidence ranking or recovered-evidence admission. | Medium/high: projection fields feed many traces and failure cards. | 250-450 lines. | High unless split into final trace packaging vs controller lifecycle facts. | Trace dict parity, failure-card payload parity, final evidence input identity checks, no ranking changes. | Safe burn-down candidate after retrieval-stop/lifecycle slices. |
| 12 | 4734-5020 | Final evidence bundle call, Linkup need gate, Economist preflight live call, Economist execution, quant sufficiency, and Economist skip-candidate telemetry. | Must remain for live callsites + product behavior phase candidate. | Keep until an explicit high-tier provider/Economist phase licenses changes. Deterministic post-call telemetry may be separated, but preflight/execution call shape should remain protected. | High: provider gating and Economist call semantics are product/runtime behavior. | 80-180 safe lines; 250+ only in product phase. | Medium/high. | Provider/model kwarg parity; Economist preflight string/JSON parity; quant telemetry parity; no-live-call static guards. | Do not extract live calls; possible later telemetry-only burn-down. |
| 13 | 5021-5090 | Analyst runtime seam invocation, legacy synthesis evaluator/Scrutineer helper invocation, and local assignment of downstream outputs. | Compatibility shell + side-effect integration. | Mostly already extracted by AG-90E/90F. Further work should avoid adding wrappers; only remove stale compatibility assignments when downstream consumers disappear. | Medium: assignment order and local names feed later scope adapters. | 40-100 lines. | Low/medium. | AG-90E/90F parity suites; static guard for local-name contract; no globals pass-through. | Pause unless stale assignments are proven removable. |
| 14 | 5091-5228 | Author evidence attachment, Author prompt assembly, Author system/effort selection, final Author runtime packet assembly, post-Analyst handoff packaging, Author context measurement, streaming final model call, quantitative consistency guard. | Must remain for live Author callsites + authority/product behavior. | Do not extract as burn-down. Author instructions, evidence attachment, effort/provider selection, and final model call are protected behavior. | Very high: Author prose/style/posture and final answer semantics. | 80-160 safe lines from deterministic telemetry only; 300+ only with product phase. | High. | Author prompt exact parity, final packet parity, provider kwarg parity, stream behavior parity, quantitative guard parity. | Explicit Author/final-answer product phase only. |
| 15 | 5229-5388 | Final answer source citation telemetry, timing payload, answer outcome/failure-card projections, final-source telemetry inputs, final evidence registry snapshot. | Safe burn-down candidate with citation/product boundary. | Deterministic projections can move, but citation eligibility/formatting and answer-outcome semantics must remain owned by their existing helpers. | Medium: final traces are externally inspected. | 120-240 lines. | Medium. | Exact final trace/session payload parity; citation telemetry fixture parity; outcome/failure-card parity. | Good safe burn-down after upstream projection cleanup. |
| 16 | 5389-5590 | Pipeline config/session payload, source-class recovery observability, run metadata/evidence mirror writes, post-Author trace/output packaging, persistence side-effect execution, and return outcome. | Must remain for persistence/DB/session side effects + safe burn-down for trace grouping. | Keep `execute_persistence_side_effects(...)` call and return assembly local. Some trace grouping may move only if writes, ordering, and `RunOutcome` identity stay unchanged. | High: persistence order and DB/session writes are protected. | 120-260 safe lines; keep side-effect callsite. | Medium/high. | Persistence write-order parity, session payload parity, RunOutcome parity, trace packaging parity. | Stop/pause for side effects; safe only for trace grouping. |

## Top 10 remaining blocks by priority

1. **Retrieval-stop projection helpers (303-600)** — best safe burn-down: high
   line reduction with low authority risk if controller ownership is statically
   guarded.
2. **Lifecycle fact projections (602-1174)** — strong safe burn-down, but split
   by targeted/weak/conflict/evidence-integration to avoid a mega-helper.
3. **Quantitative packet/timing/final-source telemetry helpers (1450-1934,
   5229-5388)** — good deterministic serialization target; product-facing text
   must remain exact.
4. **Post-retrieval trace/failure-card projection (4309-4733)** — safe only if
   final evidence selection stays delegated and unchanged.
5. **Final persistence/post-author trace grouping (5389-5590)** — can reduce
   trace-copying, but the persistence side-effect callsite and write order must
   remain protected.
6. **Stale compatibility aliases/import mirrors (1-296, 5021-5090)** — deletion
   candidate only after static consumer inventory proves they are unused.
7. **Pre-retrieval query/provider/depth block (2161-2670)** — best authority or
   product phase target, not safe burn-down.
8. **Main retrieval loop (2682-4308)** — central authority/product surface; avoid
   wholesale wrapper extraction.
9. **Economist/Linkup/final evidence block (4734-5020)** — protected provider
   and product behavior; deterministic telemetry can be split later.
10. **Author/final-answer block (5091-5228)** — protected Author instructions,
    final model call, and answer semantics; do not extract without explicit
    Author product phase.

## Ranked next phase recommendation

### 1. Best next safe burn-down

**AG-90J candidate: Retrieval-stop and ordinary-continuation trace projection
packaging.** Move only lines **303-600** plus the local shadow-recording glue at
**2684-2774** if tests prove exact parity. This is deterministic projection over
controller outputs. The phase should explicitly forbid provider/search/model
imports, query mutation, stop/continue decision ownership, and final evidence
selection.

Expected result: **180-300 orchestrator lines removed**, modest helper growth,
and no runtime behavior changes.

### 2. Best next authority-collapse/product phase

**Pre-retrieval query/depth/provider authority map.** Audit and then collapse the
remaining orchestrator-owned query/depth behavior in lines **2161-2670**,
including router retry, recon-informed query replacement, recency merge, strategy
budgets, retrieval depth, and embedding kickoff. This should be an explicit
product/authority phase because it contains live model/search/embedding callsites
and user-visible retrieval behavior.

Expected result: not primarily line reduction. Success should be measured by
clear ownership of query/depth/provider decisions and parity of live-call shapes,
not by monolith shrinkage.

### 3. Stop/pause recommendation

Pause extraction if the next proposal targets only:

- `run_pipeline(...)` compatibility shell at **1941-2008**;
- `_run_pipeline_inner(...)` dependency/cost/context setup at **2011-2158**;
- Analyst/legacy review/post-Analyst assignment shells at **5021-5090**;
- final persistence/DB/session side-effect execution at **5389-5590**;
- Author final model-call execution at **5188**.

Those surfaces are mostly compatibility shell, live callsite, or side-effect
integration. Extracting them now would mostly create wrappers and helper growth
without reducing authority risk.

## Explicit do-not-extract-yet surfaces

Do not extract these surfaces without a phase brief that explicitly licenses the
corresponding runtime/product behavior:

- Live router/retry/recon/planner/Scout/Expander/Evaluator/Economist/Author
  `ask_model(...)` callsites.
- The `embed_texts(...)` callsite and retrieval embedding cadence.
- Provider availability, search-depth, strategy budget, and supplemental-depth
  behavior.
- Query text/order/deduplication/finalization, recency merge, disambiguation,
  weak-corpus recovery queries, and conflict-resolution queries.
- Retrieval ranking/filtering, passage merge order, domain caps, final evidence
  bundle construction, and recovered-evidence admission.
- Citation eligibility/formatting and final-answer packet semantics.
- Author system prompt selection, Author effort/provider/model selection, Author
  prompt/prose/style/posture, and streaming final call behavior.
- Persistence, DB/session writes, run metadata snapshots, evidence registry
  mirror writes, and write ordering.

## Required parity suites for future phases

Any future extraction or authority-collapse phase should include at least the
following static/offline tests before live validation is considered:

1. **Line-count guard** for `core/pipeline_orchestrator.py` with a phase-specific
   upper bound and no helper mega-growth escape hatch.
2. **No-live-call static guard** for docs-first/static phases: no invocation of
   provider/model/search functions in tests or scripts.
3. **No-authority-import guard** for projection helpers: no provider routing,
   search dispatch, citation formatting, evidence ranking, Author prompt, or
   query-authority imports unless the phase explicitly permits them.
4. **Exact dict/string parity** for every moved trace, telemetry, fallback copy,
   and session payload field.
5. **Call-shape parity** for any licensed live-call surface, including provider,
   model, effort, base URL, API key, streaming, JSON requirement, and reasoning
   flags.
6. **Ordering parity** for queries, passages, provider diagnostics, evidence
   slices, persistence writes, and execution trace attachments.

## Stop-go map

- **Go** for small deterministic projection burn-down where inputs are already
  computed and controller/product authority remains outside the new helper.
- **Go only with explicit product license** for provider/search/depth,
  retrieval-ranking, final-evidence, citation, Economist, and Author behavior.
- **Stop** for wrapper-only extraction around compatibility shells,
  dependency/cost setup, final side effects, or live model/search callsites.
- **Stop** for any helper that needs broad `locals()`/`globals()` access or would
  need to own both runtime execution and trace projection.

## Post-audit completion note — AG-90J and AG-90K

AG-90J and AG-90K have now completed the two safest deterministic projection
slices identified by this audit:

- AG-90J extracted retrieval-stop / ordinary-continuation trace projection into
  `core/retrieval_stop_trace_projection.py` and reduced
  `core/pipeline_orchestrator.py` from **5,590** to **5,252** lines.
- AG-90K extracted weak-corpus lifecycle fact projection,
  conflict-resolution lifecycle fact projection, and evidence-integration
  snapshot projection into `core/lifecycle_trace_projection.py` and reduced
  `core/pipeline_orchestrator.py` from **5,252** to **5,069** lines.

The remaining recommendations should now be read as post-AG-90K guidance:
continue only with tightly bounded deterministic projection slices, or switch to
a dedicated authority/product lane for pre-retrieval query/depth/provider,
official/current acquisition, cache, Project Source retrieval, or Evidence
Health work.
