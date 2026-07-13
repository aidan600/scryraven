Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG76C_BD_R2_POST_RT_OP_PE_BURNDOWN).

# AG-76C-BD-R2 Post-RT/OP/PE Burn-Down Refresh

Date: 2026-05-30

Mode: Architecture Groove / Prove Mode

Scope: repo-only, GitHub-only, offline, non-runtime burn-down refresh.

## 1. Phase Scope

AG-76C-BD-R2 refreshes the durable decision surface after the completed
AG-76C-RT, AG-76C-RT-C, AG-76C-OP, and AG-76C-PE phases. This phase inspects
repo-visible docs, registry metadata, static tests, and the final orchestrator
tail. It does not run ScryRaven/proplex product paths, provider/model/search
calls, live validation, local DB inspection, private trace review, raw prompt
inspection, or generated artifact review.

The only licensed outputs are documentation, registry metadata, and static tests
that keep stale next-phase selections from pointing at completed work.

## 2. Completed Phase Summary

| Phase | Repo-visible completion signal | Durable interpretation |
| --- | --- | --- |
| AG-76C-RT — Runtime Trace / Export Attachment Compatibility Extraction | `core.runtime_trace_export_attachment` owns the passive runtime trace/export attachment helper, and the orchestrator imports `attach_runtime_trace_export_compatibility_payloads(...)`. | Complete; do not keep selecting RT as next. |
| AG-76C-RT-C — Runtime Trace Test Compatibility Shim Retirement | No separate durable architecture doc is present, but the branch history includes the shim-retirement merge and RT tests now target the extracted helper directly. | Complete as a test-surface cleanup; record in registry metadata. |
| AG-76C-OP — Outcome / Persistence Packaging Extraction | `core.outcome_persistence_packaging` owns execution-log/session/SQLite row and `RunOutcome` packaging. | Complete; packaging shape remains protected. |
| AG-76C-PE — Persistence Side-Effect Execution Handoff | `core.persistence_side_effects` owns JSONL append, completed-log append, policy journal append, KB trigger append, and SQLite/session execution. | Complete; side-effect ordering and non-fatal warning behavior remain protected. |

## 3. Registry / Doc / Test Staleness Found And Fixed

BD-R2 found these stale durable-surface items:

1. `core.pipeline_decision_registry` still selected `AG-76C-RT` as the exact
   next extraction phase.
2. The burn-down seam ledger still described runtime trace projection/export
   attachment as a mechanical candidate instead of completed RT work.
3. The final evidence/source telemetry and persistence seam still said to defer
   behind AG-76C-RT, even though OP and PE have completed the packaging and
   side-effect split.
4. Static burn-down tests still asserted that AG-76C-RT was the selected next
   phase.
5. No AG-76C-BD-R2 architecture record existed; the existing
   `AG76C_BD_ORCHESTRATOR_BURN_DOWN_REVIEW.md` remains a historical BD record
   whose selected next phase was correct at that time but stale after RT/OP/PE.

BD-R2 fixed those items by:

- recording `AG-76C-RT`, `AG-76C-RT-C`, `AG-76C-OP`, and `AG-76C-PE` as the
  completed post-burn-down phases in the registry;
- changing the selected next concrete phase to exactly one phase:
  `AG-76C-KB-C — KB Review Persistence Context Construction Extraction /
  Reduction`;
- marking the RT and OP/PE seams as extracted/complete in the burn-down seam
  ledger;
- adding a KB review persistence context handoff seam as the sole P0 mechanical
  candidate;
- updating static tests so stale RT selection cannot silently reappear; and
- adding this BD-R2 architecture record.

## 4. Updated Current Objectives

Current objectives after RT/RT-C/OP/PE are:

1. Keep extracted trace/export attachment, outcome packaging, and persistence
   side-effect execution as passive helpers.
2. Avoid reopening JSONL, SQLite, session, `RunOutcome`, trace/export,
   provider/search, prompt, Author, citation, classifier, candidate-fit, or
   Controller decision behavior.
3. Reduce the remaining final-tail inline construction that is still local to
   `pipeline_orchestrator.py`: the large `KbReviewPersistenceContext(...)`
   handoff into `execute_persistence_side_effects(...)`.
4. Require exact KB execution-record, KB trigger-entry, warning, guard,
   non-fatal-error, ordering, SQLite, and `RunOutcome` parity before any KB-C
   implementation can land.
5. Record LLM workflow caching only as a future design-only concern.

## 5. Current Orchestrator Responsibility Map

| Area | Current owner after BD-R2 | BD-R2 classification |
| --- | --- | --- |
| Final evidence/source-ID packaging | `core.final_evidence_bundle_builder` | extracted_complete |
| Runner-owned recovered/source-class candidate stream | `core.source_class_recovery_candidate_stream` | extracted_complete |
| Source-class diagnostics/projection handoff | `core.source_class_recovery_projection_handoff` | extracted_complete |
| Runtime trace/export attachment tail | `core.runtime_trace_export_attachment` | extracted_complete |
| Outcome/log/session/SQLite/RunOutcome packaging | `core.outcome_persistence_packaging` | extracted_complete |
| JSONL/completed-log/policy-journal/KB-trigger/SQLite side effects | `core.persistence_side_effects` | extracted_complete |
| KB review persistence context construction | `pipeline_orchestrator.py` inline `KbReviewPersistenceContext(...)` field list | mechanical_candidate_for_extraction; selected next |
| Source-class recovery runner dispatch | orchestrator passes Controller-approved action into runner | pure_plumbing |
| Controller evidence ledger interpretation | `ControllerEvidenceLedger` plus observer/export helpers | intentionally_remaining_for_now |
| AnswerContract initialization / handoff | AnswerContract plus orchestrator fact packaging | defer_until_controller_state_ready |
| Follow-up/session compatibility handoff | orchestrator compatibility plumbing | defer_until_controller_state_ready |
| Router/researcher/query preparation | routing/query helpers and orchestrator behavior | protected_behavior_surface |
| Provider/retrieval execution loop | orchestrator with Controller allocation gates | protected_behavior_surface |
| Analyst, Scrutineer, Economist, Author, citation/source-list handoffs | orchestrator and behavior-specific contracts | protected_behavior_surface |
| Weak-corpus/off-topic/failure-card gates | orchestrator plus weak-corpus/failure-card helpers | decision_authority_still_local |

## 6. KbReviewPersistenceContext Assessment

`KbReviewPersistenceContext` construction is the next smallest/highest-value
seam because the remaining work is a passive final-tail handoff rather than a
behavioral decision. The inline field list is large, duplicative of the
persistence side-effect boundary, and mechanically testable with synthetic inputs.
It can reduce `pipeline_orchestrator.py` without changing KB review-agent
behavior, provider/model/search behavior, prompt behavior, final answer behavior,
citation behavior, DB schema, JSONL/session/SQLite shapes, or `RunOutcome`
fields.

No better smaller seam was identified. The alternatives are riskier:

- provider/retrieval/query seams touch protected routing, search depth, and query
  strategy;
- Analyst/Scrutineer/Economist/Author/citation seams touch prompt or final-answer
  behavior;
- AnswerContract and follow-up/session handoffs require Controller-state design
  choices; and
- LLM workflow caching requires a safety contract before any implementation.

## 7. Next Selected Phase

Exactly one next concrete phase is selected:

`AG-76C-KB-C — KB Review Persistence Context Construction Extraction /
Reduction`.

KB-C purpose: extract or reduce the large inline
`KbReviewPersistenceContext(...)` construction at the tail of
`core/pipeline_orchestrator.py` while preserving exact KB execution-record and
trigger-entry behavior.

KB-C may:

- add a passive KB context / KB record builder near `core.persistence_side_effects`;
- move `KbReviewPersistenceContext` construction out of `pipeline_orchestrator.py`;
- preserve exact KB execution-record payload;
- preserve exact KB trigger-entry payload;
- preserve `kb_review_agent(...)` guard and positional argument order;
- preserve non-fatal error behavior;
- preserve write order: execution JSONL append -> completed log -> policy journal
  -> KB trigger -> SQLite; and
- optionally reduce duplicated fields only where parity tests prove identical
  output.

KB-C must not:

- change KB review-agent behavior;
- change provider/model/search behavior;
- implement LLM caching;
- change prompt behavior;
- change Author/final-answer/citation behavior;
- change DB schema;
- change JSONL/session/SQLite/`RunOutcome` shapes;
- change Controller/AnswerContract decisions; or
- run live validation.

## 8. Required KB-C Parity Tests

If KB-C opens, it must include these parity tests or equivalent stricter guards:

1. Static delegation guard: `pipeline_orchestrator.py` no longer inlines the full
   `KbReviewPersistenceContext` field list.
2. KB execution-record exact parity: synthetic inputs produce equivalent
   `execution_record` keys/values, including truncation, list/dict copies,
   query/provider iteration fields, answer flags, cost, latency, and preview.
3. KB trigger-entry exact parity: frozen timestamp and synthetic flags produce
   equivalent `trigger_entry` fields.
4. Agent-call guard parity: `should_auto_review=False` makes no
   `kb_review_agent` call, while `should_auto_review=True` makes exactly one call
   with the same positional arguments and provider/model/base-url/API-key values.
5. KB warning parity: `recurrence_risk == likely-recurring` with
   `suggested_action.detail` still sets `kb_warning` truncated to the same length.
6. Non-fatal error parity: feedback/review/append/agent exceptions remain
   warning-only.
7. Ordering parity: execution append -> completed log -> policy journal append ->
   KB append -> SQLite write.
8. SQLite/RunOutcome handoff parity: `kb_instrumentation` still mutates
   `execution_log_entry` before SQLite conversion and reaches
   `build_run_outcome(...)`.
9. Static protected-import guard: new helper imports no provider/search/routing/
   prompt/Author/final-answer/citation/classifier/candidate-fit behavior modules.
10. No schema drift guard: no `RUN_COLUMNS`, DB schema, JSONL field, session
    payload, or `RunOutcome` field changes.

## 9. LLM Workflow Cache Note

AG-76C-LC — LLM Workflow Cache Architecture and Safety Contract — is recorded as
a future design-only candidate. BD-R2 does not implement caching and does not
change prompt behavior, model-call behavior, provider/model/version/config
behavior, freshness, evidence digesting, source grounding, citation integrity,
final-answer posture, or runtime outputs.

A future LC phase should first define cache safety, invalidation, evidence
identity, prompt/version binding, source-grounding, and privacy boundaries before
any runtime cache implementation is considered.

## 10. Protected Surfaces Kept Closed

BD-R2 kept closed:

- runtime behavior;
- provider routing, provider selection, provider depth, provider escalation,
  provider swaps, new providers, model calls, and search calls;
- query strategy, retrieval ranking/filtering, prompt behavior, and model-call
  behavior;
- LLM cache implementation;
- final-answer prose, Author behavior, citation formatting/selection,
  classifier/currentness semantics, and candidate-fit semantics;
- Controller/AnswerContract decision behavior;
- follow-up, Scrutineer, Economist, weak-corpus, and failure-card behavior;
- DB schema, JSONL/session/SQLite/`RunOutcome` shapes;
- package/CLI/env compatibility names;
- live validation; and
- raw provider payloads, raw prompts, DB rows, private logs, caches, full raw
  traces, local output packets, credentials, and generated private artifacts.

## 10. KB-C Completion Update (2026-05-30)

AG-76C-KB-C is complete. `core.pipeline_orchestrator` no longer inlines the full
`KbReviewPersistenceContext(...)` field list; passive context, execution-record,
and trigger-entry construction now live in `core.kb_review_persistence_context`.
The side-effect owner remains `core.persistence_side_effects`, preserving write
order, non-fatal warnings, review-agent guard/argument behavior, SQLite handoff,
and `RunOutcome` handoff.

The registry now records AG-76C-KB-C in the completed post-burn-down phases and
recommends exactly one next phase: AG-77A — Source Conflict Representation Model.
LLM workflow caching remains future design-only AG-76C-LC with no implementation.
