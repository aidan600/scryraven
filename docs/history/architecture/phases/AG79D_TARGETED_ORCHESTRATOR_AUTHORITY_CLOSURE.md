Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG79D_TARGETED_ORCHESTRATOR_AUTHORITY_CLOSURE).

# AG-79D — Targeted Orchestrator Authority Closure

Date: 2026-06-03.

Mode/scope: Architecture review / static audit / targeted fixture-guard phase. This phase was behavior-preserving and docs-only. It did not run live ScryRaven/proplex/scryraven product paths, provider calls, model calls, search calls, prompt changes, retrieval changes, citation changes, Author changes, Analyst changes, Scrutineer/remediation changes, synthesis-evaluator supplemental-search changes, Economist changes, DB/session/`RunOutcome` changes, cache changes, or a broad `core/pipeline_orchestrator.py` rewrite.

> Status note, AG-95E: This document is a historical Controller-era closure for
> source-class recovery dispatch. Current source-class dispatch uses
> `authority_lifecycle.recovery_action` consumed by
> `SourceClassRecoveryRunner`; ControllerLoopSpine source-class dispatch output
> and ControllerRecoveryDecision are diagnostic/compatibility surfaces, not
> runner authority.

## Executive verdict

AG-79D closes the current Controller-authority transfer audit line at classification depth.

The remaining orchestrator-adjacent surfaces are now understood as one of five categories:

1. **Controller-owned handoff / controlled:** retrieval stop/continue, weak-corpus recovery, source-class/authoritative-source recovery, conflict-resolution retrieval, continuation-spine gates, final evidence identity handoffs, citation/source-list identity, Analyst/Author handoff packaging, weak/failure-card gate posture, conflict labels, indirect-inference labels, and SCR-R1 / SES-R1 runtime handoff trace identity.
2. **Protected legacy behavior intentionally left alone:** Brave recon rewrite, low entity-utilization disambiguation retry, query replacement/entity correction, `_finalize_retrieval_queries`, recency merge, official-bias insertion, query ordering, retrieval ranking/filtering, provider selection where not already supplied by a Controller-owned handoff, final evidence selection, prompt text, Author notes/prose, and citation formatting.
3. **Trace/projection only:** source-class observability projections, conflict-state projections, runtime trace/export attachment, Controller mirror fields, provider diagnostics, final-output metadata, and passive SCR/SES handoff trace fragments.
4. **Consciously parked future cleanup:** AG-76D-AD adapter cleanup is now appropriate as maintainability cleanup, but it is not a prerequisite for AG-80A and should not alter behavior.
5. **Active hidden authority requiring an immediate future repair:** none found for this closure pass. Recon/disambiguation and query-finalization/recency remain real runtime authorities, but AG-79D classifies them as protected legacy behavior rather than defects to repair in the next phase because changing them would choose product behavior.

AG-78G remains live-gated. AG-80A implementation playbook/docs should happen next. Roadmap v4 should wait until AG-80A so it can incorporate this closure verdict and the resulting implementation-playbook boundaries.

## Matrix of remaining orchestrator-adjacent surfaces

| Surface | Runtime effect today | Authority classification | Evidence / seam inspected | AG-79D verdict | Future action |
| --- | --- | --- | --- | --- | --- |
| Brave recon rewrite | Can perform a Brave recon search, call the recon rewriter, replace pass-1 retrieval queries, and update the canonical subject/entity when confidence is medium/high. | Protected legacy behavior. | `core/pipeline_orchestrator.py` recon block and `extract_recon_context`; recon diagnostics remain trace-visible. | Not Controller-owned. Intentionally left unchanged because owning it would change query-generation/retrieval behavior. | Candidate for a later explicitly licensed query-authority repair, not AG-80A. |
| Low entity-utilization retry | Can issue disambiguation retry queries after first-pass utilization is below threshold. | Protected legacy behavior with trace visibility. | Utilization anchor/rate, `should_retry_retrieval`, `build_disambiguation_queries`, `provider_role="disambiguation_retry"`. | Not Controller-owned. Left closed because it changes retrieval behavior. | Missing static fixture could freeze it as protected legacy if a later repair targets query authority. |
| Query replacement / entity correction | Recon canonical subject can prepend entity list and become `primary_entity`; finalized query lists can incorporate the corrected entity. | Protected legacy behavior. | Canonical-subject merge and router-query runtime posture projection. | Runtime-governing but intentionally preserved. | Later Controller-owned query-source handoff only if product behavior change is licensed. |
| `_finalize_retrieval_queries` | Normalizes, de-duplicates, adds entity/topic anchoring, and can insert official-bias wording. | Protected legacy behavior. | Nested orchestrator helper around `finalize_retrieval_queries`. | Protected legacy; no behavior change. | Do not repair in AG-80A; document as legacy query policy. |
| Recency merge | Prepends an anchor/year news query for current/news-like obligations and preserves max-query ordering. | Protected legacy behavior. | `should_merge_recency_queries`, `_extract_year`, `current_queries` reorder, router-query runtime posture. | Protected legacy; no Controller takeover in this phase. | Possible future query-policy handoff only with explicit behavior license. |
| Official bias insertion | Adds official/canonical wording where legacy query policy requests it. | Protected legacy behavior. | `include_official_bias=True` on initial/recovery finalization and `wants_official_source_bias` posture in router contract. | Protected legacy; trace-visible through router-query posture. | Keep closed. |
| Query ordering | Pass-1, recency, scout, expander, evaluator, weak-corpus, source-class, and conflict paths preserve local ordering unless a Controller-owned continuation/recovery decision supplies authorized next queries. | Mixed: Controller-owned where continuation/recovery handoffs authorize; protected legacy otherwise. | Router query preparation, retrieval loop, continuation spine gates, weak-corpus/source-class/conflict lifecycle traces. | Controlled enough for current closure; initial/recon query ordering remains protected legacy. | Fixture guard optional in a later query-authority phase. |
| Scout directed continuation | Can schedule directed scout queries and force component providers. | Controller-owned continuation gate for continue/stop; provider override is protected legacy. | `_decide_retrieval_loop_stop_continue` plus `_authorize_scout_continuation_before_scheduling`. | Query continuation cannot bypass the continuation gate; provider override remains legacy. | No immediate repair. |
| Expander component continuation | Can schedule component queries. | Controller-owned continuation gate. | `_decide_retrieval_loop_stop_continue` plus `_authorize_expander_continuation_before_scheduling`. | Controlled. | No immediate repair. |
| Gap evaluator continuation | Can schedule evaluator `new_queries`. | Controller-owned continuation gate. | Evaluator stop snapshot, `_decide_retrieval_loop_stop_continue`, `_authorize_evaluator_continuation_before_scheduling`. | Controlled. | No immediate repair. |
| Ordinary continuation spine | Decides whether ordinary continuation remains available after source-class, weak-corpus, and conflict lifecycles. | Controller-owned loop spine. | Evidence-integration checkpoint, `ControllerLoopSpineInput`, targeted retrieval lifecycle trace. | Controlled. | Maintain. |
| Source-class recovery | Can admit official/canonical/source-class recovery. | Controller-owned handoff; adapter is mechanical. | Authoritative-source action adapter, source-class recovery lifecycle, execution-admission traces. | Controlled. | AG-76D-AD cleanup now appropriate as no-behavior maintainability cleanup, not next. |
| Weak-corpus recovery | Can schedule bounded weak-corpus recovery searches. | Controller-owned handoff. | `build_weak_corpus_recovery_controller_input`, `decide_weak_corpus_recovery`, loop-spine promotion. | Controlled. | Maintain. |
| Conflict-resolution retrieval | Can admit resolving queries for conflicts. | Controller-owned handoff. | Runtime conflict projection, conflict-resolution controller/lifecycle/executor, continuation-spine facts. | Controlled. | Maintain. |
| Scrutineer/remediation runtime handoff | Scrutineer/remediation behavior remains legacy, but SCR-R1 records run, remediation, re-synthesis, evidence, and Author directive identity. | Trace/projection only over protected legacy behavior. | `runtime_scrutineer_remediation_trace_fragment` and SCR-R1 fixtures. | No longer an unclassified hidden surface; trace wiring is behavior-preserving and not runtime-governing. | Do not change behavior in AG-80A. |
| Synthesis-evaluator supplemental-search runtime handoff | Supplemental behavior remains legacy, but SES-R1 records completeness, supplemental queries, dispatch, evidence, final-evidence rebuild, Analyst re-run, and Author note identity. | Trace/projection only over protected legacy behavior. | SES runtime collector and SES-R1 fixtures. | No longer an unclassified hidden surface; trace wiring is behavior-preserving and not runtime-governing. | Do not change behavior in AG-80A. |
| Final evidence bundle identity | Selects final evidence via existing bundle builder and rebuilds after supplemental/remediation passages. | Protected legacy selection; Controller-visible identity handoff. | `build_final_evidence_bundle`, final evidence refs, ledger snapshot. | Selection behavior protected; identity handoff controlled. | Maintain. |
| Citation/source-list handoff | Executes ordered source/source URL handoff after final assembly. | Controller-owned identity handoff over protected citation formatting. | `build_citation_source_handoff_state` and `execute_citation_source_handoff`. | Controlled for identity; formatting/order semantics protected legacy. | Maintain. |
| Analyst/Author handoff | Packages analysis, evidence, source, Author prompt, notes, and gate refs. | Controller-owned packaging/handoff over protected prompt/prose. | `build_analyst_author_handoff_state`. | Controlled for identity and refs; Author prose remains protected. | Maintain. |
| Author notes/directives | Includes weak/failure, supplemental hedge, Scrutineer flags/directives, recency, nutrition/quantitative, image/context, conflict, and inference notes. | Mixed: Controller-owned where from weak/failure, conflict, indirect-inference, SCR/SES trace identity; protected legacy for note text/prose. | Author prompt assembly, weak-failure gate, source recency, SCR/SES trace refs. | No unclassified side channel remains. Note text remains closed. | Maintain. |
| Conflict labels | Surface conflicts without collapsing them into unsupported certainty. | Controller-owned / AG-77 runtime visible. | Conflict state projection and AnswerContract fields. | Controlled. | Maintain. |
| Indirect inference labels | Prevent indirect/model-derived inference from being presented as direct source statements. | Controller-owned / AG-78 runtime visible. | AG-78 labels in AnswerContract/final assembly handoff. | Controlled. | Maintain; AG-78G still live-gated. |
| Weak/off-topic/failure-card labels | Controls weak corpus, off-topic, and failure-card displayability posture. | Controller-owned handoff. | Weak-failure gate contract and failure-card payload. | Controlled. | Maintain. |
| Trace/projection/export | Exports execution trace, compatibility packets, source-class validation packet, telemetry, and metadata. | Trace/projection only. | Runtime trace assembly and `attach_runtime_trace_export_compatibility_payloads`. | No observer/export layer inspected here was found to mutate provider/search/query/final-answer decisions. | Maintain; AG-76D-AD may simplify adapters later. |

## Surfaces now closed / controlled

- Retrieval stop/continue is Controller-owned at the active stop/continue seam.
- Scout, expander, evaluator, and ordinary continuation branches are controlled by Controller continuation gates before scheduling next queries.
- Weak-corpus recovery is controlled by a Controller recovery decision and loop-spine action promotion.
- Source-class / authoritative-source recovery is controlled by a named action seam and execution-admission traces.
- Conflict-resolution retrieval is controlled by conflict-controller lifecycle and loop-spine facts.
- Final evidence identity is handed to citation/source-list and Analyst/Author handoff contracts even while selection behavior remains legacy.
- Citation/source-list handoff identity is Controller-visible and executed through a dedicated handoff contract.
- Analyst/Author handoff identity, final evidence refs, Author note presence, weak/failure gate refs, source telemetry refs, and AnswerContract refs are Controller-visible.
- Conflict labels, indirect-inference labels, weak/off-topic/failure-card labels, Scrutineer trace refs, and synthesis-evaluator supplemental-search trace refs are classified and visible.
- Runtime trace/export layers inspected in this pass are trace/projection only and were not found to mutate runtime decisions.

## Protected legacy behavior intentionally left alone

AG-79D intentionally leaves these product behaviors unchanged and closed:

- Brave recon dispatch, recon rewriter prompt/model call, recon confidence handling, and recon query replacement.
- Low entity-utilization disambiguation retry, utilization threshold policy, and retry query generation.
- Canonical-subject/entity correction from recon.
- `_finalize_retrieval_queries`, query anchoring, query de-duplication, official-bias insertion, and max-query truncation.
- Recency merge behavior, recency query ordering, and year/news-query construction.
- Provider selection, provider overrides, and search depth where no Controller-owned handoff already supplies them.
- Retrieval ranking/filtering, evidence scoring, diverse top-evidence filtering, and final evidence selection.
- Supplemental-search runtime behavior and Scrutineer/remediation runtime behavior; SCR-R1 and SES-R1 only trace those behaviors.
- Citation formatting, source ordering semantics, prompt text, Author prose, Author note text, Analyst behavior, Economist behavior, cache behavior, DB/session/`RunOutcome` shape, and live validation.

## Active hidden authority, if any

No active hidden-authority surface requiring an immediate future repair was found in AG-79D.

The important nuance is that several local runtime authorities still exist. Recon/disambiguation and query-finalization/recency do govern retrieval outcomes, and Scrutineer/remediation plus synthesis-evaluator supplemental search still govern legacy remediation/supplemental behavior. AG-79D does not claim those are Controller-owned. It classifies them as protected legacy behavior or trace/projection-only handoff identity because changing ownership would require product-behavior choices outside this phase.

## Missing fixture/static tests

No tests were added in AG-79D because this was docs-only and no new boundary helper was necessary. Missing tests that could be useful in a later explicitly licensed phase are:

- Recon rewrite / canonical-subject fixture proving it is either protected legacy query authority or Controller-owned query authority once a future handoff exists.
- Low entity-utilization disambiguation retry fixture freezing retry admission, provider role, and query identity without live retrieval.
- `_finalize_retrieval_queries` fixture separating official bias, entity anchoring, recency merge, and query ordering from Controller-owned continuation/recovery queries.
- Scout/expander/evaluator continuation fixture proving scheduled next queries exactly match continuation-gate authorized queries.
- Author-note classification fixture proving every note/directive is classified as Controller-owned handoff, protected legacy text, or trace-only identity.
- Trace/export static guard proving projection/export helpers do not import provider clients, call search/model providers, mutate final evidence, or alter Author prompt state.
- Adapter static guard for AG-76D-AD proving authoritative-source adapter cleanup remains mechanical and behavior-preserving.

## Decisions

- **AG-76D-AD adapter cleanup:** now appropriate as a later behavior-preserving maintainability phase, because the authority seams it would clean up are classified. It should not run inside AG-79D and should not be the next phase unless AG-80A explicitly schedules it.
- **AG-80A implementation playbook/docs:** recommended next. The implementation-doc refresh has been intentionally waiting for the authority-closure pass; AG-79D completes that pass.
- **Roadmap v4:** should wait until AG-80A, so roadmap language can inherit the implementation playbook's closed/protected/parked boundary model.
- **AG-78G:** remains live-gated. No live validation, product-path execution, provider calls, model calls, or search calls were authorized or performed.

## Recommended next phase

Recommended exactly one next phase: **AG-80A — Implementation playbook / docs refresh for the closed Controller-authority boundary**.

AG-80A should be documentation-only unless separately licensed. It should consolidate the current-state note, architecture groove/playbook language, and implementation guidance around the AG-79D verdict: controlled surfaces, protected legacy surfaces, trace/projection-only surfaces, parked adapter cleanup, and live-gated AG-78G.
