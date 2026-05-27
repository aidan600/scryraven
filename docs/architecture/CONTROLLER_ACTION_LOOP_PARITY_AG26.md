# AG-26 Offline Controller Action-Loop Parity Harness

Status: M3 / AG-26 architecture harness. Classification: pure/offline
representational parity layer.

## Goal

AG-26 adds `core/controller_action_loop_parity.py`, an offline harness that
replays already-shaped controller facts through the AG-25
`ControllerActionEnvelope`. The harness proves that current controller-shaped
decisions can be represented as ordered envelopes and compact action history
without making the controller drive live runtime.

The harness accepts synthetic fixture facts and compact trace-shaped controller
snapshots or decisions. It does not consume live logs, DB rows, caches, raw
provider payloads, raw prompts, generated output packets, or secrets.

## Output Shape

`ControllerActionLoopParityResult` returns:

- ordered `ControllerActionEnvelope` records;
- compact action history derived from those envelopes;
- a replay status:
  - `replayed`;
  - `replayed_with_known_gaps`;
  - `not_representable`;
  - `no_actions`;
- known parity gaps with metadata;
- optional answer-contract fulfillment when the input includes passive
  answer-contract pipeline facts;
- metadata stating that the replay is offline only, has no live side effects,
  and changes no runtime behavior.

The envelope remains the only action representation. The result wrapper is a
review artifact, not a scheduler, reducer, executor, or runtime authority model.

## Replayable In AG-26

Weak-corpus recovery is replayable from a
`WeakCorpusRecoveryControllerInput` snapshot or a precomputed
`WeakCorpusRecoveryDecision`. The harness recomputes the current pure decision
when a snapshot is provided, then emits `recover_weak_corpus` through the AG-25
adapter. Approved, blocked, and skipped paths preserve the current one-attempt
budget and orchestrator-ownership metadata.

Source-class recovery is replayable from a
`SourceClassRecoveryControllerInput` snapshot or a precomputed
`SourceClassRecoveryDecision`. The harness emits
`recover_missing_source_class` envelopes for approved, blocked, and skipped
decisions. The approved envelope preserves provider role, search depth, missing
classes, queries, and attempt count. Blocked and skipped envelopes have no
executor side effect.

Retrieval-stop decisions are replayable from a
`RetrievalStopControllerInput` snapshot or a precomputed
`RetrievalStopDecision`. Active terminal no-query and budget-exhausted facts
emit `stop_insufficient_with_caveat` envelopes with stop side-effect class.
Shadow or informational facts emit envelopes with no side effect and no runtime
authority.

Answer-contract action history is replayable by passing existing
`AnswerControllerActionResult` records or passive `PipelineAnswerContractFacts`.
Those records are converted to AG-25 envelopes without changing fulfillment
semantics. The harness can include the passive fulfillment handoff produced by
the existing answer-contract adapter.

Social signal is replayable only as the AG-25
`request_social_signal_check` placeholder. It remains `authority=future` and
`side_effect_class=social_side_packet`; it is not ordinary evidence eligible and
cannot satisfy official, legal, current-primary, primary, or factual evidence
classes.

## Scenarios Covered

The AG-26 tests cover:

- weak-corpus recovery approved;
- weak-corpus recovery blocked and skipped;
- source-class recovery approved;
- official/legal source-class recovery with AG-22 limitation note;
- source-class recovery blocked and skipped;
- retrieval-stop active terminal no-query and budget-exhausted;
- retrieval-stop shadow/informational continue;
- answer-contract action history replay;
- social-signal future side-packet placeholder.

## Known Gaps

Official/legal/current-primary source-class recovery is represented, but remains
a known limited action. AG-22 did not prove final official/current-primary source
quality from allowed artifacts, so AG-26 records
`official_legal_recovery_limited_ag22` as a parity gap when those classes or
answer-contract legal/official gap reasons are replayed.

Retrieval-stop active authority remains limited to already-terminal legacy
branches. If future fixtures ask the harness to treat active retrieval-stop as a
continuation dispatcher or active sufficient-evidence synthesis owner, the
harness records a known gap because current runtime still owns those branches
outside the controller.

Weak-corpus recovery is still executed inside `pipeline_orchestrator.py` at
runtime. AG-26 represents the action envelope and history only; it does not add
a weak-corpus executor contract.

Source-class recovery has an executor boundary today, but AG-26 does not change
provider selection, search depth, source-specific official/legal adapters,
ranking, filtering, prompt semantics, recovered-evidence visibility, or final
evidence selection.

Social signal remains future/side-packet only. There is no runtime provider
wiring, no raw social packet handoff, and no ordinary factual evidence merge.

Answer-contract remains a passive replay and handoff layer for this phase. The
harness does not promote `decide_answer_controller_action` into runtime loop
authority.

## What Did Not Change

AG-26 does not:

- import or call `pipeline_orchestrator.py`;
- call providers, models, prompts, retrieval, routing, persistence, caches, DBs,
  or logging;
- read `.env`, secrets, raw logs, generated output packets, raw prompts, raw
  provider payloads, caches, or DB rows;
- change provider routing, provider selection, search depth, source ranking, or
  filtering;
- change weak-corpus, source-class, retrieval-stop, answer-contract, Analyst,
  Economist, Author, or Scrutineer runtime behavior;
- change persistence schemas;
- wire social signal into runtime.

## Remaining For Runtime Promotion

Before any controller-loop runtime promotion, the architecture still needs:

1. a reducer for shared controller state;
2. explicit executor contracts for weak-corpus recovery and terminal
   retrieval-stop handling;
3. budget ownership across retrieval, weak-corpus recovery, source-class
   recovery, answer-contract actions, and stop policy;
4. evidence-boundary ownership for recovered evidence, official/legal sources,
   social side packets, Analyst context, and Author handoff;
5. sanitized diagnostics for official/legal recovery quality and visibility;
6. fixture parity against current orchestrator timing before any live runtime
   authority moves from orchestrator branches into a controller loop.

## Bottom Line

AG-26 proves representational parity for the current controller-shaped islands
through the AG-25 action envelope. Runtime remains orchestrator-led. The next
phase should use this parity harness as the review boundary for a controller
state reducer and explicit executor contracts, not as runtime authority by
itself.
