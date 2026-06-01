# AG-76D-FU — Follow-up as Controller Initial State

Date: 2026-06-01
Status: Production-active narrow authority transfer for follow-up initial state

## Phase Type

AG-76D-FU is a core authority transfer with narrow follow-up prompt/context
repair. It moves the follow-up/session initialization seam into deterministic
Controller-owned state while preserving the existing normal follow-up pipeline.

## Licensed Behavior Surface

Licensed surfaces:

- follow-up initialization;
- follow-up prompt/context construction metadata;
- saved-context sufficiency for the scoped follow-up seam;
- source-obligation refresh when a follow-up introduces a stronger obligation;
- Controller-owned trace visibility for prior-context reuse and refreshed
  obligation posture.

Closed surfaces remain closed: provider/model/search routing, Author/final-answer
behavior, citation behavior, Economist behavior, Scrutineer behavior,
DB/session schema, cache behavior, package/CLI/env names, and live validation.

## Previously Local Follow-up Decisions

Before AG-76D-FU, `core.followup` assembled saved report context, prior source
excerpts, evaluator output, and source-obligation refresh as local follow-up
runtime logic. The old runtime adapter could decide whether saved context was
sufficient, whether a search was needed, and how the source-obligation note was
inserted into the follow-up prompt without an explicit Controller-owned initial
state describing those facts.

## Controller-owned FollowUpInitialControllerState

AG-76D-FU adds `core.followup_initial_state_contract` with
`FollowUpInitialControllerState` and passive descriptor dataclasses for:

- prior report/session/run refs;
- prior evidence/source refs;
- prior ledger refs;
- prior AnswerContract/posture refs when available;
- new follow-up query identity and intent;
- saved-context reuse decision;
- refreshed source obligations;
- new stronger-obligation detection;
- insufficiency/partiality carryover posture;
- prompt/context hash and inclusion metadata;
- trace visibility; and
- explicit closed-surface non-change booleans.

The contract stores hashes, lengths, counts, and sanitized refs. It does not
include raw prompts, raw provider payloads, local traces, DB rows, private logs,
output packets, secrets, or caches.

## Saved-context Reuse Decision Model

The contract uses three reuse postures:

- `reuse_as_sufficient_context` when no stronger obligation is introduced, or
  when saved evidence actually satisfies the new required source class;
- `reuse_as_background_only` when saved context can help orient the answer but a
  new stronger source obligation is not yet satisfied;
- `do_not_reuse_as_sufficient`, reserved for callers that need an explicit hard
  no-sufficiency posture.

Saved report context is never automatically sufficient merely because it exists.

## New Stronger-obligation Detection Model

The deterministic detector maps follow-up wording to stronger obligation types:

- `official_current`;
- `legal_current_primary`;
- `canonical`;
- `academic`;
- `source_bound_quantitative`.

The detector reuses deterministic source-obligation helpers and source-class
fit evaluation. It does not invoke provider/model/search behavior.

## Refreshed Source-obligation Behavior

When a follow-up introduces a required source class and the saved context lacks
that class, the Controller-owned handoff marks saved context as background only,
sets `source_obligation_status` to `saved_context_insufficient`, and returns
legacy-compatible follow-up queries through the existing normal pipeline. The
search provider and query execution path remain the existing follow-up path.

If saved context already contains the required source class, the saved context
may remain sufficient and no retrieval is forced.

## Insufficiency / Partiality Carryover Rules

When a stronger follow-up obligation is not satisfied by saved context, the
prompt note states that saved context is insufficient for the new obligation and
that missing official/current/canonical/legal/academic/source-bound evidence must
remain caveated. This is a narrow prompt/context repair so the synthesis step
receives Controller-owned posture rather than an ad hoc saved-context claim.

## Mechanical Executor / Handoff Boundary

`core.followup` remains the mechanical executor. It still performs memory search,
the existing evaluator call, existing web retrieval, image context assembly,
synthesis prompt construction, and model invocation. It now builds
`FollowUpInitialControllerState` and consumes
`execute_followup_initial_state_handoff(...)` for legacy-compatible values.

## Behavior Preserved

AG-76D-FU preserves:

- simple follow-up behavior;
- saved-context reuse when no stronger obligation is introduced;
- saved-context sufficiency when saved evidence actually satisfies the stronger
  source class;
- provider/model/search routing and execution paths;
- Author/final-answer/citation behavior;
- Economist and Scrutineer behavior;
- DB/session/RunOutcome shape, with only additive in-memory/diagnostic fields;
- package/CLI/env compatibility names.

## Behavior Intentionally Changed

The only intentional behavior change is the licensed follow-up initialization
repair: saved context that lacks a newly required stronger source class is no
longer treated as silently sufficient. The prompt note now identifies the
Controller-owned saved-context decision and insufficiency carryover posture.

## Production-active vs Shadow-only Paths

The contract is production-active for follow-up initial-state authority and for
legacy-compatible handoff values consumed by the existing follow-up pipeline. It
is not a replacement retrieval, provider, Author, citation, Economist,
Scrutineer, DB, cache, or live-validation path.

## Tests Added / Updated

Added `tests/test_ag76d_fu_followup_controller_initial_state.py` covering:

1. prior refs and upstream AnswerContract/posture/ledger refs;
2. simple follow-up saved-context reuse;
3. stronger obligation detection and refreshed obligation routing;
4. saved context satisfying stronger obligations when the right source class is
   present;
5. prompt/context use of Controller-owned state;
6. trace visibility;
7. additive output shape and closed-surface booleans;
8. static protected-import guard; and
9. orchestrator/session authority guard.

Existing AG-61A and authoritative-source follow-up tests continue to verify
source-obligation refresh and protected prompt redaction.

## Trace Compatibility and Additive Visibility

`build_followup_diagnostics(...)` now includes additive
`followup_initial_controller_state` trace data. Existing diagnostic fields remain
present, including route, source-obligation, query count, source-card parity, and
provider diagnostics.

## Protected Surfaces Kept Closed

The new contract imports deterministic source-obligation/source-class helpers
only. It imports no provider/model/search/Author/final-answer/citation/Economist/
Scrutineer/DB/cache/live surfaces and records explicit non-change booleans in
trace.

## Stop Conditions

AG-76D-FU would have stopped if it required provider routing changes, broad query
generation changes, Author/citation/final-answer changes, Economist or
Scrutineer behavior changes, DB schema changes, broad chat memory/UX redesign,
live validation, cache implementation, source-specific hardcoding, package/env
renames, or a broad rewrite. None were required.

## AG-76D Set Completion

AG-76D-FU completes the main normal-flow AG-76D authority-transfer set currently
identified in the phase chain: retrieval stop/continue, router/query
preparation, retrieval loop, weak/failure gate, Analyst/Author handoff,
citation/source-list handoff, Economist handoff, and follow-up initial state.

## Recommended Next Phase

Recommended next phase: **AG-76D-BD — Controller Authority Transfer Burn-Down /
Adapter Debt Review**. The main normal-flow AG-76D set is now represented in
Controller-owned contracts, so the next highest-value step is a focused review of
remaining adapter debt, hidden authority seams, and any candidates for later
Scrutineer/remediation or AG-77A source-conflict modeling.
