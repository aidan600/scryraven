# AG-76D-BD — Controller Authority Transfer Burn-Down / Adapter Debt Review

Date: 2026-06-01
Phase type: architecture review / design / burn-down ledger
Mode: Architecture Groove / Prove Mode
Status: Review complete; docs-only decision record

## Scope and Baseline Verification

This phase reviewed the repository after the AG-76D core authority-transfer
campaign. It did not implement runtime behavior, adapter cleanup, Scrutineer
changes, AG-77A, prompt changes, provider/model/search changes, DB/session
changes, or compatibility renames.

Baseline verification passed: `main` includes AG-76D-FU and the expected
contract/test/doc files:

- `core/followup_initial_state_contract.py`;
- `tests/test_ag76d_fu_followup_controller_initial_state.py`;
- `docs/architecture/AG76D_FU_FOLLOWUP_AS_CONTROLLER_INITIAL_STATE.md`;
- `core/economist_handoff_contract.py`;
- `core/citation_source_handoff_contract.py`;
- `core/analyst_author_handoff_contract.py`;
- `core/weak_failure_gate_contract.py`;
- `core/retrieval_loop_contract.py`;
- `core/router_query_preparation_contract.py`; and
- `core/retrieval_stop_controller.py`.

## Completed AG-76D Normal-Flow Chain

The AG-76D normal-flow authority-transfer chain is complete enough to pivot. The
main normal-flow seams that previously lived as orchestrator/local-helper
posture now have Controller-owned contracts, state, or decisions:

1. **Retrieval stop/continue** — `core.retrieval_stop_controller` owns the
   stop/continue decision values and controller input snapshot.
2. **Router/query-preparation posture** —
   `core.router_query_preparation_contract.RouterQueryPreparationState` owns
   normalized Router fields, fallback/retry provenance, routing override
   provenance, query-preparation posture, retrieval budget seeds, recency merge
   posture, official-source bias posture, query text/order visibility, and a
   controller-state payload.
3. **Retrieval-loop pass posture** — `core.retrieval_loop_contract` owns
   `RetrievalLoopState`, pass descriptors, execution envelopes, and pass-result
   summaries around already-authorized search execution.
4. **Weak/off-topic/failure-card gate posture** —
   `core.weak_failure_gate_contract.WeakFailureGateState` owns weak-corpus,
   useful-content, response-displayability, evidence-sufficiency, answer-class,
   failure-card, and Analyst gate posture.
5. **Analyst/Author handoff posture** —
   `core.analyst_author_handoff_contract.AnalystAuthorHandoffState` owns Analyst
   admission, Analyst evidence/context identity, unsupported/failure directives,
   Author evidence handoff, Author prompt input identity, and upstream
   Controller/AnswerContract refs.
6. **Citation/source-list handoff identity** —
   `core.citation_source_handoff_contract.CitationSourceHandoffState` owns final
   evidence identity, source IDs, ordered source lines, evidence blocks, citation
   observations, ledger refs, and AnswerContract/handoff refs.
7. **Economist handoff posture** —
   `core.economist_handoff_contract.EconomistHandoffState` owns Economist
   admission/run/block/unavailable posture, preflight, source-bound quantitative
   packet identity, unsupported/missing/model-derived value posture, output
   identity, Analyst/Author exposure, and safety refs.
8. **Follow-up initial state** —
   `core.followup_initial_state_contract.FollowUpInitialControllerState` owns
   prior report/session/evidence/ledger/AnswerContract refs, new follow-up
   intent, saved-context reuse posture, refreshed source obligations, stronger
   obligation detection, insufficiency/partiality carryover, and prompt/context
   inclusion metadata.

### Normal-Flow Completion Assessment

No major AG-76D normal-flow seam is missing from the intended chain. Remaining
normal-flow orchestrator code is still large, but most of it is now one of these
categories:

- mechanical executor code that calls existing providers/models/search helpers;
- adapter scaffolding that builds Controller-owned states from already-computed
  runtime facts;
- trace/projection/mirror code;
- compatibility packaging for existing `RunOutcome`, session, and trace shapes;
  or
- older recovery/source-conflict surfaces that predate AG-76D and should be
  handled by their own design phases, not reopened as AG-76D normal-flow gaps.

## Remaining Hidden-Authority Map

| Candidate seam | Location | Classification | Assessment |
| --- | --- | --- | --- |
| Scrutineer run gate, flag threshold, searchable category filter, remediation query generation, novelty filter, remediation provider/depth selection, re-synthesis trigger, and Author directive insertion | `core/pipeline_orchestrator.py` Scrutineer block | **Real hidden authority** | This is the largest remaining hidden authority. It is not represented by a Controller-owned Scrutineer/remediation handoff contract. It can cause extra retrieval, extra Analyst synthesis, and Author caveat/omit directives in Deep mode. |
| Synthesis evaluator completeness check and supplemental search path | `core/pipeline_orchestrator.py` synthesizer evaluator block | **Real hidden authority / older evaluator authority** | The path can decide that synthesis is insufficient, add Author notes, run supplemental searches, and re-analyze. It is outside AG-76D's completed main handoff chain, but it is an evaluator/supplemental lane rather than the next product-critical conflict-modeling gap. |
| Image inclusion filtering and image-context instructions | `core/pipeline_orchestrator.py` final Author prompt assembly | **Real hidden authority, closed for this phase** | It changes Author input shape for image modes. It was outside AG-76D's text/evidence authority chain and should not be altered without a dedicated image/Author phase. |
| Thin-body/tier instruction selection from weak corpus or low relevance | `core/pipeline_orchestrator.py` final Author prompt assembly | **Real hidden authority, partly covered upstream** | Upstream weak/failure and Analyst/Author handoff states now expose the facts, but final prompt text remains assembled locally. Changing it would be Author/final-answer behavior repair, not burn-down. |
| Source conflict state production | `core.conflict_state_producer` plus `_build_runtime_conflict_state_projection` in `core/pipeline_orchestrator.py` | **Architecture design / existing controller-side producer, unclear for AG-77A** | A bounded producer exists for explicit effective-date tension and feeds AnswerContract conflict fields. AG-77A should extend representation beyond this narrow producer rather than treating the orchestrator adapter as the owner. |
| Conflict resolution lifecycle/dispatch | `core.conflict_resolution_controller`, `core.conflict_resolution_executor`, lifecycle helpers | **Mostly core authority already transferred / parked specialized lane** | Conflict resolution decisions are modeled in dedicated controller/executor modules and guarded by tests. The remaining gap is source-conflict representation depth, not orchestrator-only hidden authority. |
| Source-class recovery and authoritative-source action adapters | `core.source_class_recovery*`, `core.authoritative_source_action_orchestrator_adapter`, orchestrator projections | **Mostly core authority already transferred plus adapter debt** | These paths use dedicated controllers/adapters and are not part of the AG-76D normal-flow handoff chain. Do not clean up in this phase. |
| Retrieval depth/provider selection calls around existing search execution | `choose_retrieval_search_depth`, `choose_supplemental_search_depth`, `select_providers`, `merge_search_provider_overrides` | **Acceptable mechanical executor for AG-76D scope / protected behavior** | The retrieval-loop contract records already-selected depth/provider facts. Changing ownership here would alter provider/search behavior and is closed. |
| Contract builder/executor calls for AG-76D seams | `build_*_state`, `execute_*_handoff`, `to_trace_fragment` calls in `core/pipeline_orchestrator.py` and `core.followup` | **Acceptable mechanical executor / adapter scaffolding** | These adapters are bulky, but they consume and expose Controller-owned state rather than making new domain decisions. |
| RunController mirrors, stage ledger, evidence ledger snapshots, trace fragments, diagnostics, and final packaging | `core/pipeline_orchestrator.py` final trace/outcome packaging and mirror calls | **Observer/trace/projection only** | These should remain projection/packaging surfaces unless a future phase finds they mutate decisions. |
| `proplex` compatibility names, DB names, state keys, CLI/env aliases | repo-wide compatibility surfaces | **Legacy compatibility shim** | Preserve. Do not rename under AG-76D-BD, AG-76D-AD, AG-76D-SCR, or AG-77A unless explicitly licensed. |

## Adapter-Debt Map

AG-76D intentionally added adapter scaffolding inside `core/pipeline_orchestrator.py`
to avoid behavior changes while moving authority into Controller-owned state.
That debt is now visible and should be considered maintainability debt, not a
reason to reopen product behavior.

| Adapter/scaffolding | Safe plumbing? | Bulky but behavior-preserving? | Consolidation posture |
| --- | --- | --- | --- |
| Router/query-preparation contract build and runtime-posture attachment | Yes | Moderate | Can later be moved into a small adapter helper that receives already-computed Router/query facts and returns the same state/trace. |
| Retrieval-loop pass descriptor, execution envelope, result summary, and prior-summary carryover | Yes | High | Good AG-76D-AD candidate after parity tests. Keep actual search executor, provider selection, and depth choice closed. |
| Weak/failure gate build/execute and trace fallback | Yes | Moderate | Can later be extracted into a helper that builds the same `WeakFailureGateState` and consumes the same handoff. |
| Analyst/Author handoff build/execute before Author call and final trace rebuild after AnswerContract visibility | Yes | High | Can later be consolidated carefully, but must not alter prompt text, Author inputs, Analyst behavior, or citation behavior. |
| Citation/source-list handoff build/execute and trace fragment insertion | Yes | Moderate | Safe future extraction if source ID/order/citation telemetry parity is locked. |
| Economist handoff build/execute before and after AnswerContract refs | Yes | Moderate | Safe future extraction if Economist prompt, preflight, skip, and exposure behavior remain byte-for-byte equivalent at stable inputs. |
| Follow-up initial state build/execute/prompt-context metadata refresh | Yes | Moderate | Too new to consolidate immediately; preserve until follow-up tests and current-state history settle. |
| Conflict/source-class/recovery projections and authoritative-source action adapters | Mixed | High | Do not fold into AG-76D adapter cleanup unless separately scoped; these are older specialized lanes and overlap with AG-77A. |
| Scrutineer/remediation inline block | No | High | Not adapter debt yet. It is hidden authority and needs a Controller-owned contract before cleanup. |

Adapter debt is now a maintainability bottleneck, but it is not the next
product-critical state-modeling bottleneck. It should be burned down after the
next conflict-representation phase unless local churn makes it urgent.

## Contract-Scaffolding Consolidation Candidates

Do not implement consolidation in AG-76D-BD. A future **AG-76D-AD — Adapter Debt
Burn-Down / Contract Scaffolding Consolidation** may consolidate only
behavior-preserving patterns such as:

1. **Repeated `_state_ref` helpers** across Analyst/Author, citation, Economist,
   and follow-up contracts into a small JSON-safe contract-reference utility.
2. **Repeated `to_trace_fragment()` / `to_controller_state()` conventions** into
   a shared passive mixin/helper, provided trace keys and payload shapes remain
   exactly stable.
3. **Repeated explicit no-change booleans** into a shared closed-surface metadata
   builder, provided existing booleans remain present with the same names.
4. **Repeated trace visibility metadata** such as schema version,
   `controller_owned`, sanitized refs, and trace key names.
5. **Repeated build/execute handoff scaffolding** in orchestrator-local adapters,
   provided builders still consume already-computed facts and executors only
   return legacy-compatible values.
6. **Repeated controller-state serialization** for route fields and trace fields,
   provided existing trace/controller payload keys remain stable.

A future adapter-burn-down phase may likely touch:

- `core/pipeline_orchestrator.py`;
- `core/router_query_preparation_contract.py`;
- `core/retrieval_loop_contract.py`;
- `core/weak_failure_gate_contract.py`;
- `core/analyst_author_handoff_contract.py`;
- `core/citation_source_handoff_contract.py`;
- `core/economist_handoff_contract.py`;
- `core/followup_initial_state_contract.py`; and
- new helper modules under `core/` for passive contract refs/trace metadata.

It must not consolidate prompt text, provider/model/search/query behavior,
source ranking/filtering, final-answer prose, citation formatting/selection,
Economist behavior, follow-up behavior, Scrutineer behavior, DB/session/
`RunOutcome` shape, cache behavior, or compatibility names. It should require
parity/static tests for stable trace keys, stable no-change booleans, import
boundaries, and representative fixture parity where available.

## Scrutineer / Remediation Assessment

Scrutineer is a hidden controller today, but it is a parked/rare path rather
than a blocker for the next AG-77A design phase.

Current characteristics:

- It runs only in the medium/high synthesis block and only when complexity is
  `high` after the synthesis evaluator path reaches the Scrutineer block.
- It calls the Scrutineer model, parses JSON flags, counts high-severity flags,
  applies a hard-coded high-flag threshold, filters only `SINGLE-SOURCE` and
  `TEMPORAL DRIFT` categories for remediation, asks the Researcher model for
  remediation queries, applies a local novelty filter, may run remediation
  search, may rebuild the final evidence bundle, and may re-run Analyst
  synthesis.
- It later injects Scrutineer flags into Author prompt context as directives to
  hedge, omit, note uncertainty, or caveat silently.
- It is not represented by a Controller-owned Scrutineer/remediation state, and
  the run/skip/remediate/direct-to-Author posture is not subordinate to a named
  AG-76D contract.

Does it override Controller/AnswerContract posture? It can influence retrieval,
Analysis, and Author input after the main retrieval/evidence chain, but it does
not currently replace the AnswerContract object or citation/source-list contract.
Because it can still alter downstream evidence and Author directives, it remains
real hidden authority.

Tests currently guard related subordination indirectly rather than directly:

- conflict-resolution tests guard that ordinary next queries do not become
  conflict-resolving queries;
- retrieval-batch and continuation-spine tests guard lane separation;
- AG-76D handoff tests guard protected-surface non-change flags for the newly
  transferred normal-flow contracts.

There is no dedicated static/runtime-free test proving Scrutineer remediation is
subordinate to a Controller-owned Scrutineer handoff, because that contract does
not yet exist.

A future **AG-76D-SCR** should define a passive Scrutineer/remediation handoff
state if this lane is promoted from parked/rare to near-term cleanup. It should
own Scrutineer admission/run/skip posture, flag-count thresholds, searchable flag
category posture, remediation query identity, novelty/blocker facts,
remediation dispatch authorization, re-synthesis authorization, Author exposure
identity, and AnswerContract/handoff refs. It must keep prompt text,
final-answer/citation behavior, provider/model/search behavior, Scrutineer model
behavior, and remediation behavior closed unless separately licensed.

## AG-77A Readiness Assessment

The repo is ready to pivot to **AG-77A — Source Conflict Representation Model**.

Why AG-77A is now more valuable than further AG-76D authority transfer:

1. The main AG-76D normal-flow chain now has Controller-owned state for the
   major handoffs from Router/query preparation through follow-up initialization.
2. Existing conflict machinery already has consumers and dispatch guards:
   AnswerContract accepts conflict fields, evidence-integration checkpoint reads
   conflict availability, conflict-resolution lifecycle decides whether bounded
   conflict resolution can run, and retrieval-batch/continuation tests guard
   separation between ordinary and conflict-resolving queries.
3. The remaining conflict producer is intentionally narrow. It recognizes only a
   bounded class of explicit effective-date tension from sanitized evidence. It
   does not yet model richer source conflict representation across claim type,
   source class, source authority, evidence centrality, contradiction shape,
   recency/currentness, or source-to-source disagreement.
4. Source conflict representation is a product-critical state-modeling gap: weak
   or conflicting sources can affect correctness even when AG-76D handoffs are
   Controller-visible.
5. Scrutineer remains hidden authority, but it is Deep/rare and can be parked
   while AG-77A defines the conflict state that Scrutineer/remediation should
   eventually consume or subordinate itself to.

AG-77A should not implement adapter cleanup, Scrutineer remediation, prompt
changes, provider/model/search changes, final-answer/citation behavior changes,
DB/session changes, or live validation. It should define the Source Conflict
Representation Model and the minimal static/fixture tests needed to prove
ordinary next queries, conflict-resolving queries, source-class recovery, weak
corpus recovery, and Scrutineer/remediation remain distinct lanes.

## Phase Taxonomy for Remaining Candidates

| Candidate | Taxonomy |
| --- | --- |
| Scrutineer/remediation handoff contract | Core authority transfer |
| AG-76D adapter helper extraction and shared contract refs | Adapter-debt cleanup |
| Trace/mirror/current-state projection extraction | Mechanical extraction |
| Prompt, final-answer, citation, Economist, provider/search, follow-up, or Scrutineer behavior changes | Behavior repair |
| AG-77A Source Conflict Representation Model | Architecture design |

## Recommendation: Exactly One Next Phase

Recommended next phase: **AG-77A — Source Conflict Representation Model**.

Rationale: the normal-flow AG-76D authority-transfer set is sufficiently
complete, adapter debt is visible but behavior-preserving, and Scrutineer is a
real hidden controller but parked enough not to preempt the next source-conflict
state-modeling gap. AG-77A should define richer conflict representation before
adapter cleanup or Scrutineer handoff work so those later phases can subordinate
to the right conflict state rather than inventing another local policy surface.

Parked after AG-77A:

- **AG-76D-SCR** if Scrutineer/remediation becomes active near-term work or AG-77A
  finds it needs Scrutineer-owned conflict inputs.
- **AG-76D-AD** for adapter debt cleanup once source-conflict representation is
  stable enough that helper extraction will not obscure new state boundaries.

## Closed Surfaces

Closed throughout AG-76D-BD and recommended closed for AG-77A unless separately
licensed:

- runtime behavior;
- prompts and prompt semantics;
- model/provider/search/query behavior;
- provider routing, provider selection, and search depth;
- source ranking/filtering;
- Author/final-answer/citation behavior;
- Economist behavior;
- follow-up behavior;
- Scrutineer behavior;
- DB/session/`RunOutcome` shape;
- LLM cache implementation;
- live validation;
- package/CLI/env/session/database compatibility renames; and
- broad orchestrator rewrite.

## Tests and Static Checks

No tests were added. This was a docs/review phase and no runtime or Python code
changed. The review used offline inspection and repository static checks only.
No live ScryRaven/proplex/scryraven product-path commands, provider calls, model
calls, search calls, local DBs, secrets, raw traces, raw provider payloads,
private logs, caches, or local output packets were used.

## Stop Conditions for Future Work

Stop future AG-77A / AG-76D-SCR / AG-76D-AD work if it appears to require:

- prompt/model/provider/search changes;
- Author/final-answer/citation behavior changes;
- Economist, follow-up, or Scrutineer behavior changes outside an explicitly
  licensed phase;
- DB/session/`RunOutcome` changes;
- LLM cache implementation;
- live validation;
- adapter cleanup while doing AG-77A design;
- broad orchestrator rewrite;
- compatibility renames; or
- more than one next-phase recommendation.

## Final Decision Record

AG-76D-BD finds that the main normal-flow Controller authority-transfer campaign
is complete enough to pivot. Remaining authority in `core/pipeline_orchestrator.py`
is concentrated in specialized or protected lanes: Scrutineer/remediation,
synthesis-evaluator supplemental search, image/tier prompt assembly,
provider/search mechanical execution, and older source-class/conflict recovery
adapters. Adapter debt is real and should be burned down later with parity tests,
but it is not the most important next product-state gap.

Final decision: proceed next with **AG-77A — Source Conflict Representation
Model**. Do not start AG-76D-AD or AG-76D-SCR first unless AG-77A planning or
review explicitly changes that priority.
