# AG-28 Runtime Promotion Readiness: Terminal Stop Parity Gate

Status: M4 / AG-28 readiness gate. Classification: pure/offline
architecture proof.

## Goal

AG-28 assesses the smallest plausible future runtime-promotion candidate:
`stop_insufficient_with_caveat` for already-terminal no-query and
budget-exhausted branches.

This phase does not promote runtime behavior. It proves readiness criteria,
negative controls, and remaining blockers using AG-25 envelopes, AG-26 offline
parity replay, and the AG-27 state reducer.

## Candidate Assessed

`stop_insufficient_with_caveat` is the only plausible first candidate because
the two covered branches are already terminal in current runtime flow:

- evaluator found no new queries;
- iteration budget was exhausted.

Both branches can be represented as AG-25 action envelopes with:

- `authority=active`;
- `side_effect_class=stop`;
- `handoff_boundary=final_answer_posture_only`;
- no approved queries;
- no ordinary evidence eligibility;
- no provider, depth, ranking, domain, prompt, persistence, or handoff
  authority.

AG-28 still marks runtime promotion as not performed. The readiness descriptor
records remaining blockers:

- `runtime_promotion_not_in_scope_ag28`;
- `requires_final_pre_promotion_review`;
- `retrieval_loop_timing_still_runtime_owned`.

## Terminal Stop Parity Scenarios

The fixture-only AG-28 tests cover:

1. `terminal_no_query`: evaluator insufficient and no new queries.
2. `terminal_budget_exhausted`: evaluator insufficient, new query facts present,
   but iteration budget exhausted.

For each scenario, tests prove:

- the retrieval-stop snapshot produces a `stop_insufficient_with_caveat` AG-25
  envelope;
- AG-26 replay status is `replayed` with no known gaps;
- AG-27 reduction stops the offline state and sets final-answer posture to
  `answer with caveats`;
- no pending queries, ordinary evidence action, official/legal/current-primary
  action, social side-packet action, or sanitized handoff action is introduced;
- state deltas are limited to action-history/offline budget/event recording
  plus terminal stop state and final-answer posture;
- no live-call or retrieval-iteration budget counter is allocated.

## Negative Promotion Controls

AG-28 explicitly blocks other first-promotion candidates:

| Action | Blocker |
| --- | --- |
| `retrieve_targeted` | Needs retrieval continuation authority and would dispatch queries. |
| `stop_sufficient` | Sufficient-evidence synthesis remains shadow/passive. |
| `recover_weak_corpus` | Weak-corpus executor is not factored out and output can enter ordinary evidence. |
| `recover_missing_source_class` | Output can enter ordinary evidence; official/legal quality gap remains. |
| `request_social_signal_check` | Future placeholder only; no social provider integration. |

AG-26 already reports runtime-promotion-blocking gaps if active authority is
attempted for `retrieve_targeted` or `stop_sufficient`.

## Evidence Boundary

Terminal stop actions do not:

- admit evidence;
- change source ranking or filtering;
- change provider behavior;
- touch legal/source diagnostics beyond visibility;
- alter Analyst, Economist, Author, or Scrutineer handoffs;
- allocate live-call budget.

AG-27 evidence-boundary assertions for the terminal-stop envelopes allow only
`final_answer_posture_only`. Ordinary evidence, official/legal/current-primary
evidence, social side-packet evidence, and sanitized handoff effects remain
disallowed for the action.

## New Helper

`core/controller_runtime_promotion_readiness.py` adds a compact descriptor-only
readiness matrix. It imports only AG-25 descriptors and emits JSON-safe candidate
facts. It is not a scheduler, executor, reducer, provider router, prompt layer,
persistence layer, or runtime controller loop.

Static tests guard the helper against runtime/provider/persistence/prompt/live
call coupling.

## What Did Not Change

AG-28 does not:

- change `pipeline_orchestrator.py`;
- call providers, models, prompts, retrieval, routing, caches, DBs, logs, or
  persistence;
- read secrets, raw logs, raw prompts, raw provider payloads, generated output
  packets, caches, or DB rows;
- change provider routing, provider selection, search depth, source ranking, or
  filtering;
- change weak-corpus, source-class, retrieval-stop, answer-contract, Analyst,
  Economist, Author, or Scrutineer runtime behavior;
- wire social signal into runtime.

## Remaining Before Actual Runtime Promotion

Before promoting even this narrow terminal-stop candidate, a later phase should:

1. review compatibility against current terminal branch timing;
2. decide whether terminal stop timing remains runtime-owned or moves behind a
   minimal executor boundary;
3. keep `retrieve_targeted`, `stop_sufficient`, recovery actions, and social
   side-packets blocked from the promotion;
4. preserve the final-answer-posture-only evidence boundary;
5. run focused runtime parity tests after the promotion patch.

Recommended next phase: a narrow implementation phase for terminal-stop runtime
promotion only if reviewers accept AG-28 readiness, with explicit fallback and
compatibility tests around the same two terminal scenarios.

## AG-30 Clarification

AG-29 promoted controller-owned terminal-stop metadata for the already-terminal
no-query and budget-exhausted `stop_insufficient_with_caveat` branches only.
In this context, `active` means terminal-stop metadata/posture authority:

- no loop-control ownership;
- no retrieval continuation authority;
- no approval of pending next-query facts;
- no provider, depth, ranking, prompt, persistence schema, or protected handoff
  authority.

Budget-exhausted telemetry may record that pending next-query facts existed, but
approved query count remains zero and continuation dispatch remains owned by the
existing retrieval loop.
