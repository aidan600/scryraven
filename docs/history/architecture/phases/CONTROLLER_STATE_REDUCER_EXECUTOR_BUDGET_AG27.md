Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (CONTROLLER_STATE_REDUCER_EXECUTOR_BUDGET_AG27).

# AG-27 Controller State Reducer, Executor Descriptors, And Budget Contracts

Status: M4 / AG-27 architecture contract. Classification: pure/offline
representation layer.

## Goal

AG-27 adds `core/controller_state_reducer.py`, a pure offline reducer that
applies AG-25 `ControllerActionEnvelope` records to JSON-safe controller-state
snapshots. It exposes state deltas, executor descriptors, budget effects, and
evidence-boundary assertions for review without changing runtime behavior.

The reducer is not a scheduler, executor, provider router, prompt layer,
persistence layer, source ranker, or runtime controller loop. It does not
promote the controller into live authority.

## Snapshot Shape

`ControllerStateSnapshot` serializes as
`controller_state_snapshot_ag27_v1` with these state fields:

- `iteration`;
- `action_history`;
- `recovery_attempts`;
- `budget_counters`;
- `budget_events`;
- `pending_queries`;
- `ordinary_evidence_action_names`;
- `ordinary_evidence_candidate_count`;
- `official_legal_current_primary_action_names`;
- `social_side_packet_action_names`;
- `social_side_packet_status`;
- `sanitized_handoff_action_names`;
- `stopped`;
- `stop_reason`;
- `final_answer_posture`;
- `executor_events`;
- `evidence_boundary_events`;
- `metadata`.

The serializer removes raw, prompt, provider payload, cache, DB, secret, token,
and API-key shaped keys from nested payloads.

## Reducer Result Shape

`ControllerStateReducerResult` serializes as
`controller_state_reducer_result_ag27_v1` with:

- `before` and `after` snapshots;
- `applied_actions`;
- `budget_effects`;
- `evidence_boundary_assertions`;
- `executor_effects`;
- `state_delta`;
- `warnings`;
- metadata stating `offline_only=true`, `uses_ag25_action_envelope=true`,
  `runtime_behavior_changed=false`, `live_side_effects=false`, and
  `controller_drives_runtime=false`.

## Actions Covered

The reducer consumes AG-25 envelopes for:

- `recover_weak_corpus`;
- `recover_missing_source_class`;
- `retrieve_targeted`;
- `stop_sufficient`;
- `stop_insufficient_with_caveat`;
- `request_social_signal_check`;
- `run_scrutineer_review`;
- passive and handoff-only answer-contract actions such as
  `set_or_update_answer_contract`, `identify_missing_information`,
  `decompose_quantitative_question`, `handoff_to_analyst`, and
  `ask_user_clarification`.

Approved weak-corpus and source-class recovery actions increment their offline
recovery-attempt counters and add pending approved queries. Targeted retrieval
actions increment the offline retrieval-iteration budget and add pending
queries. Stop actions update only stop state and final answer posture. Social
signal remains a future side-packet placeholder. Scrutineer and handoff-only
actions are recorded as sanitized handoff/review descriptors only.

## Executor Descriptors

`controller_executor_descriptors()` exposes one descriptor per AG-25 action:

- active runtime-owned descriptors for currently active recovery actions;
- active terminal runtime-owned descriptors for already-terminal stop branches;
- passive descriptors for answer-contract, review, and handoff actions;
- shadow descriptors for shadow stop/synthesis vocabulary;
- future placeholder descriptors for social signal and future interaction
  actions.

Each descriptor includes action name, current authority, side-effect class,
executor identity from AG-25 when one exists, handoff boundary, promotion
blockers, and `runtime_behavior_changed=false`.

Weak-corpus recovery is explicitly marked as not yet factored into a standalone
executor. Retrieval continuation and terminal stop timing remain owned by the
current runtime control flow.

## Budget Classes

`controller_budget_descriptors()` exposes these budget classes:

- `retrieval_iteration_budget`;
- `weak_corpus_recovery_budget`;
- `source_class_recovery_budget`;
- `answer_contract_recovery_action_budget`;
- `social_side_packet_budget_placeholder`;
- `live_call_budget_placeholder`.

Budget effects are reducer-local accounting events. They do not claim runtime
budget ownership. Live-call budget remains zero in AG-27.

## Evidence Boundaries

`controller_evidence_boundary_descriptors()` and reducer result assertions cover:

- ordinary evidence eligibility;
- official/legal/current-primary evidence;
- social side-packet evidence;
- final answer posture only;
- sanitized handoff only.

Social signal is explicitly excluded from ordinary evidence and from
official/legal/current-primary repair. Stop actions can update final answer
posture only. Sanitized handoff actions must not expose raw packets, raw
prompts, or provider payloads.

Official/legal/current-primary evidence is recorded only when an ordinary
evidence-eligible action explicitly references one of the official/legal/current
primary classes.

## AG-25 And AG-26 Compatibility

AG-27 uses AG-25 envelopes as the only action representation. It does not add a
competing action envelope.

AG-26 replay results can be passed directly to `reduce_controller_state()`.
Focused tests prove weak-corpus recovery, source-class recovery, retrieval stop,
targeted retrieval, answer-contract actions, and social placeholders reduce into
expected offline state transitions.

## L1 Diagnostics Compatibility

L1 source-class recovery diagnostics remain aligned with the AG-25
`recover_missing_source_class` action projection. AG-27 tests compare the L1
`ag25_action` fields against the AG-26/AG-25 envelope and prove that legal text
recovery reduces to:

- ordinary evidence eligible;
- official/legal/current-primary action recorded;
- source-class recovery budget event recorded;
- no provider/depth/domain tuning.

## Social Side-Packet Boundary

`request_social_signal_check` remains future-only. The reducer records the
side-packet placeholder and social status, but it does not:

- call a provider;
- allocate live-call budget;
- merge social data into ordinary evidence;
- satisfy factual, official, legal, current-primary, or weak-corpus evidence;
- expose raw social packets/comments to Author.

## What Did Not Change

AG-27 does not:

- change `pipeline_orchestrator.py` behavior;
- import or call runtime orchestration;
- call providers, models, prompts, retrieval, routing, caches, DBs, logs, or
  persistence;
- read secrets, raw logs, raw prompts, raw provider payloads, generated output
  packets, caches, or DB rows;
- change provider routing, provider selection, search depth, source ranking, or
  filtering;
- change weak-corpus, source-class, retrieval-stop, answer-contract, Analyst,
  Economist, Author, or Scrutineer runtime behavior;
- wire social signal into runtime.

## Remaining Before Runtime Promotion

Runtime controller-loop promotion still needs:

1. fixture parity against current orchestrator timing across more trace-shaped
   end-to-end cases;
2. a standalone weak-corpus executor abstraction, or an explicit decision to
   keep that timing orchestrator-owned;
3. a runtime-safe owner for retrieval iteration budget and terminal stop timing;
4. live-call budget policy and provider gates;
5. social provider policy/API integration behind side-packet boundaries;
6. official/legal diagnostics proving where recovery quality fails before any
   provider, depth, domain, ranking, or prompt tuning;
7. protected handoff review for Analyst/Economist/Author/Scrutineer surfaces.

## Bottom Line

AG-27 gives the architecture a reducer and contract layer that can explain what
AG-25/AG-26 actions would do to controller state offline. It keeps runtime
authority exactly where it is today.
