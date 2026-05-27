# AG-23 Controller State Map

Status: M1 / AG-23 architecture map. Classification: docs-only.

This note maps the controller-shaped components currently present in the
ProPlex/FauxPlex runtime. It is descriptive only. It does not authorize runtime
behavior changes, provider changes, prompt changes, persistence schema changes,
Analyst/Economist/Author handoff changes, social runtime integration, or legal
source tuning.

## Scope Read

Primary files inspected:

- `core/pipeline_orchestrator.py`
- `core/run_controller.py`
- `core/source_class_recovery.py`
- `core/source_class_recovery_controller.py`
- `core/source_class_recovery_controller_mirror.py`
- `core/source_class_recovery_executor.py`
- `core/source_class_recovery_lifecycle.py`
- `core/weak_corpus_controller.py`
- `core/retrieval_stop_controller.py`
- `core/answer_contract_controller.py`
- `core/answer_contract_pipeline_adapter.py`
- `core/answer_contract_loop_harness.py`
- `core/answer_contract_runtime_handoff.py`
- `core/controller_state_mirror.py`
- `core/stage_ledger_mirror.py`
- relevant controller, source-class, weak-corpus, retrieval-stop, and
  answer-contract tests
- `docs/validation/AG22_OFFICIAL_SOURCE_DOMAIN_RECOVERY_LIVE_VALIDATION.md`
  from the local AG-22 validation branch
- local `codex/social-signal-v0-schema-scoring` branch, corresponding to draft
  social-signal PR work

No live calls were made for this phase.

## Current Shape

The current architecture is not yet a clean controller action loop. It is a
procedural orchestrator with several controller-shaped islands:

- Active recovery decisions exist for weak-corpus recovery and source-class
  recovery.
- Source-class recovery has the clearest action split: a pure decision, a
  lifecycle recorder that creates an active `RetrievalAction`, and a
  dependency-injected executor.
- Retrieval-stop logic is a pure decision boundary, but runtime use is partly
  shadow and partly limited active terminal telemetry for legacy stop cases.
- Answer-contract logic defines the broad action vocabulary and an offline loop
  shape, but runtime mainly uses it as a passive adapter and fulfillment handoff.
- `RunController`, `ControllerState`, `EvidenceRegistry`, `StageLedger`, and
  mirror helpers are passive state mirrors. They do not own runtime authority.
- Planned-vs-observed diagnostics, run plans, and task ledgers are post-hoc
  diagnostics only.
- Social signal exists only in the draft PR branch as an offline schema/scoring
  and passive controller adapter. It is not merged or runtime-wired.

## Controller Action Inventory

| Action or component | Active / passive / shadow | Input state | Output state | Executor location | Tests | Known limitations |
| --- | --- | --- | --- | --- | --- | --- |
| `weak_corpus_recovery` | Active, limited | `WeakCorpusRecoveryControllerInput`: corpus state, weak flag, iteration, max iterations, prior attempt flag, readable passage count, recovery queries | `WeakCorpusRecoveryDecision`; trace fields `weak_corpus_recovery_decision`, reason, blockers; active `RetrievalAction` when approved | `core/pipeline_orchestrator.py` changes `current_queries`, advances iteration, and reuses normal retrieval loop with provider role `weak_corpus_recovery` | `tests/test_weak_corpus_controller.py`, `tests/test_weak_corpus_recovery.py`, answer-contract adapter/handoff tests | First-iteration only, one attempt, no separate executor module, Fast/no-budget blocks, action execution still lives inside orchestrator control flow. It also owns the path before generic source-class recovery unless a bounded official/legal answer-contract gap qualifies. |
| `source_class_recovery` | Active, limited | Source-class recommendation, evidence signals, corpus state, weak-corpus ownership flags, current search depth, iteration budget, answer-contract slot flag, provider/depth reuse flags, phase flags | `SourceClassRecoveryDecision`; `active_source_class_recovery_*` lifecycle fields; active `RetrievalAction` with provider role `source_class_recovery`; result/new URL counts after execution | Decision in `core/source_class_recovery_controller.py`; lifecycle/action record in `core/source_class_recovery_lifecycle.py`; execution in `core/source_class_recovery_executor.py`; orchestrator calls executor post-main-retrieval before final evidence selection | `tests/test_source_class_recovery_controller.py`, `tests/test_source_class_recovery_lifecycle.py`, `tests/test_source_class_recovery_executor.py`, `tests/test_source_class_recovery_trace.py`, AG10/AG11/AG13 source-class tests | One bounded attempt, reuses current providers and search depth, does not choose providers or escalate depth, blocks on provider policy/depth changes, remains embedded in orchestrator timing. AG-22 live validation did not demonstrate final official/legal source quality from allowed artifacts. |
| `source_class_recovery_recommendation` | Shadow/passive recommendation | Query/router metadata, anchor packet, source tier/domain telemetry, official evidence flag | `source_class_recovery_recommended`, missing classes, reason, queries, optional official domain constraints | `core/source_class_recovery.py`; recorded passively by `core/source_class_recovery_controller_mirror.py` | `tests/test_source_class_recovery.py`, `tests/test_source_class_recovery_controller_mirror.py`, source-class trace tests | Recommendation is not an executor. It can propose queries and constraints, but lifecycle/controller still decides whether action is eligible. |
| `source_class_recovery_candidate_v2` | Shadow diagnostic | Existing `execution_trace`, including source-class satisfaction, budget pressure, active recovery fields, answer class, evidence sufficiency | Nested `source_class_recovery_candidate_v2` diagnostic payload | `core/source_class_recovery.py`; orchestrator nests it after `execution_trace` assembly | `tests/test_source_class_recovery_trace.py` candidate-v2 tests | Diagnostic only. It must not alter retrieval, provider policy, source filtering, prompts, or handoff. |
| `retrieval_stop_shadow` | Shadow | Evaluator sufficiency, iteration, max iterations, prior/next queries, query source, weak-corpus completion flags | `retrieval_stop_shadow_*` telemetry with decision, reason, blockers, next query count, alignment | Helper functions in `core/pipeline_orchestrator.py` call `core/retrieval_stop_controller.py` around existing legacy branches | `tests/test_retrieval_stop_controller.py`, `tests/test_retrieval_stop_shadow.py`, answer-contract runtime handoff tests | Mirrors legacy behavior and alignment. It has no authority to continue or stop by itself. |
| `retrieval_stop_active_terminal` | Active terminal telemetry, limited | Same compact stop input, but only at legacy no-query or budget-exhausted branches | `retrieval_stop_active_*` telemetry when the controller returns expected terminal decision | `core/pipeline_orchestrator.py` helper functions `_build_retrieval_stop_active_stop_no_queries_telemetry` and `_build_retrieval_stop_active_stop_budget_exhausted_telemetry` | `tests/test_retrieval_stop_shadow.py`, `tests/test_retrieval_stop_controller.py`, `tests/test_answer_contract_runtime_handoff.py` | Active only for already-terminal legacy branches. It does not own the whole retrieval loop, continuation dispatch, scout/expander/evaluator decisions, or recovery sequencing. |
| `answer_contract_controller` action vocabulary | Pure/offline action model; runtime passive | `AnswerControllerState`: active contract, evidence summary, missing information, action history, recovery attempts, stop state, caps | `AnswerControllerActionResult`, updated action history/recovery attempts/missing info/stop state, `AnswerContractFulfillment` | Pure functions in `core/answer_contract_controller.py`; offline executor harness in `core/answer_contract_loop_harness.py`; runtime uses adapter/handoff, not a live action loop | `tests/test_answer_contract_controller.py`, `tests/test_answer_contract_loop_harness.py`, `tests/test_answer_contract_pipeline_adapter.py`, `tests/test_answer_contract_runtime_handoff.py` | Defines broad future actions (`retrieve_targeted`, `recover_weak_corpus`, `recover_missing_source_class`, `resolve_conflict`, `request_social_signal_check`, `run_scrutineer_review`, stops), but runtime does not yet use this as the central scheduler. Social action currently records provider-unavailable skip only. |
| `answer_contract_runtime_handoff` | Passive runtime handoff | Runtime facts after retrieval/synthesis: router metadata, evidence sufficiency, source tiers, source-class lifecycle, weak-corpus flags, retrieval-stop telemetry, query history, final evidence | `answer_contract_fulfillment_handoff` trace fragment and attached `RunController.state.answer_contract_*` fields | `core/answer_contract_runtime_handoff.py`; orchestrator calls it before source-class recovery to surface answer-contract gaps and after final evidence to attach handoff | `tests/test_answer_contract_runtime_handoff.py`, pipeline adapter and loop harness tests | Does not call providers, prompts, retrieval, storage, or routing. It replays existing decisions into answer-contract action history; it is not a runtime executor. |
| `request_social_signal_check` | Future action; current main branch has passive/skip vocabulary only; PR #26 has offline passive adapter | Main branch: answer contract social relevance and evidence social status. PR #26: social relevance, explicit request, provider/API flags, optional offline packet, platform policy, raw storage policy | Main branch: skipped action with `social_provider_not_integrated_ag1` or handoff social summary. PR #26: `SocialSignalControllerDecision`, `social_signal_status`, Author-safe digest, evidence-boundary flags | Main branch: `core/answer_contract_controller.py` only. PR #26 branch: `core/social_signal_controller.py`, `core/social_signal_schema.py`, `core/social_signal_scoring.py` | Main branch: answer-contract controller/loop tests. PR #26: `tests/test_social_signal_controller.py`, schema/scoring/fixture harness tests | Not runtime-wired. PR #26 is draft/unmergeable against main and also changes source-class files and removes some AG20/AG21 validation/test files. Social signal must remain side-packet discussion/perception evidence, not ordinary factual evidence or official/primary evidence repair. |
| `controller_state_mirror` | Passive telemetry | Already-computed run metadata | Mutated `RunController.state` metadata fields | `core/controller_state_mirror.py`; orchestrator calls near outcome assembly | `tests/test_controller_state_mirror.py` | No authority, no trace-fragment authority, static import guards prevent routing/retrieval/provider/persistence coupling. |
| `stage_ledger_mirror` | Passive telemetry | Already-computed query iteration maps, provider iteration lists, provider diagnostics, retrieval pass records | `RunController.ledger` query/provider records and facts | `core/stage_ledger_mirror.py`; orchestrator calls after run body | `tests/test_stage_ledger_mirror.py` | Records facts only. Does not decide, retrieve, route, or persist. |
| `source_class_recovery_controller_mirror` | Passive/shadow telemetry | Already-built source-class recommendation and evidence signals | Passive `ControllerDecision` and optional shadow `RetrievalAction` named `source_class_recovery_recommendation` | `core/source_class_recovery_controller_mirror.py`; orchestrator calls at trace assembly | `tests/test_source_class_recovery_controller_mirror.py`, source-class trace tests | Mirrors recommendation only and intentionally has no active execution authority. |
| `planned_observed_diagnostics` / `RunPlan` / `TaskLedger` | Passive diagnostics | Existing `execution_trace`, optional run plan/task ledger | Nested `controller_diagnostics` payload with run plan, task ledger, planned-vs-observed status | `core/planned_observed_diagnostics.py`; orchestrator nests compact payload after trace assembly | `tests/test_controller_diagnostics_trace_contract.py` and diagnostics utilities | Post-hoc only. No prompt, provider, routing, persistence, or runtime authority. |
| `RunController` / `ControllerState` / `EvidenceRegistry` / `StageLedger` | Passive state containers | Explicit calls from mirror/lifecycle/handoff helpers | Snapshots of state, evidence, ledger, and trace fragments | `core/run_controller.py` | Controller state, stage ledger, weak/source-class/answer-contract tests | Container only. Current runtime does not expose it as the authoritative action loop state. |

## Orchestrator Glue That Is Not Yet Controller Action

The following runtime behavior is still mostly orchestrator-owned:

- Router, researcher query generation, provider selection, search-depth choice,
  retrieval execution, disambiguation retry, scout, expander, evaluator,
  Analyst, Economist, Scrutineer, Author, supplemental retrieval, DB/logging,
  and final trace assembly.
- The retrieval loop stores local variables such as `current_queries`,
  `iteration`, `is_sufficient`, `all_passages`, `provider_diagnostics`,
  `retrieval_pass_records`, `seen_urls`, and `collected_images`. Controller
  helpers observe or update slices of this state but do not own the loop.
- Answer-contract handoff is attached near the end of the run. It describes
  fulfillment and replays existing controller decisions; it does not dispatch
  future actions in runtime.

## Answer-Contract Lifecycle Map

1. Router-shaped metadata is converted to an `AnswerContract` by
   `draft_answer_contract_from_router_metadata`.
2. Runtime or fixture evidence facts are converted to `EvidenceStateSummary`.
   Runtime conversion happens through `RuntimeAnswerContractFacts` and
   `PipelineAnswerContractFacts`.
3. Existing controller decisions can be replayed into answer-contract action
   history:
   - source-class decisions become `recover_missing_source_class`;
   - weak-corpus decisions become `recover_weak_corpus`;
   - retrieval-stop decisions become `retrieve_targeted`, `stop_sufficient`, or
     `stop_insufficient_with_caveat`.
4. `decide_answer_controller_stop` applies caps and structured stop checks:
   max iterations, max recovery attempts, sufficient evidence, redundant next
   query, no useful query, and optional marginal-value judgment.
5. `decide_answer_controller_action` chooses the next pure action in the
   offline loop order:
   - stop if evidence is sufficient;
   - request central social signal if needed but unavailable;
   - decompose quantitative question if variables/assumptions are missing;
   - recover weak corpus;
   - resolve conflicts;
   - recover missing source class;
   - run Scrutineer review;
   - stop on redundant next query;
   - retrieve targeted queries;
   - otherwise stop with caveat.
6. `apply_answer_controller_action_result` updates copied state by appending
   action history, incrementing recovery attempts, recording missing
   information, and setting stop state.
7. `build_answer_contract_fulfillment` creates the safe handoff:
   fulfilled/partial/unfulfilled items, evidence references, actions taken,
   actions skipped, revisions, stop reason, final answer posture, warnings, and
   social-signal summary. It redacts protected diagnostic/Economist/quantitative
   material.
8. Runtime calls `build_runtime_answer_contract_handoff` in two places:
   - before active source-class recovery, to let answer-contract official/legal
     gaps add bounded source-class recovery recommendations;
   - after final evidence, to attach `answer_contract_fulfillment_handoff` and
     `RunController.state.answer_contract_*` fields.

Important boundary: the lifecycle exists, but the runtime does not yet let
`decide_answer_controller_action` drive the overall pipeline. The runtime uses
the handoff as an adapter and audit artifact.

## Missing For A Clean Action Loop

The next implementation phases need these pieces before social signal or
further legal-source work should be runtime-wired:

1. A single action envelope shared by all active actions. It should include
   action name, mode, status, preconditions, input snapshot, approved work,
   executor identity, side-effect class, output delta, stable reason, skip
   reason, trace keys, and Author-handoff boundary.
2. A central action registry that maps answer-contract action names to current
   controller decisions and executors. Today, weak-corpus, source-class,
   retrieval-stop, and answer-contract actions use related but separate shapes.
3. A reducer for controller state. Current actions mutate local orchestrator
   variables, `RunController`, lifecycle dictionaries, and trace payloads in
   separate places.
4. Explicit executor contracts. Source-class has one; weak-corpus does not.
   Retrieval-stop terminal handling is inside orchestrator helper functions.
   Social signal has only an offline draft adapter.
5. Budget ownership. Iteration caps, recovery caps, provider call limits,
   depth/provider reuse, and mode policy are still distributed across
   orchestrator branches and helper inputs.
6. Evidence boundary ownership. Social signal, recovered source visibility,
   official/legal source gaps, and weak-corpus evidence repair need one shared
   rule for what can enter ordinary evidence, final citations, Analyst context,
   and Author handoff.
7. Sanitized action validation artifacts. AG-22 showed that generated live
   reports did not expose source-class recovery metrics, so validation could not
   prove whether recovery was considered, eligible, used, constrained, or
   useful without inspecting raw traces/logs.
8. Runtime parity tests for any action-loop extraction. The current tests prove
   local controllers and no-op mirrors, but a central loop needs fixture-based
   parity against current orchestrator behavior before it can become active.
9. Social-status convergence. Main has `SocialSignalRelevance` and
   `social_signal_status` fields in answer-contract state; PR #26 introduces a
   separate social controller vocabulary. These need one adapter boundary before
   runtime integration.

## Social Signal Future Fit

Social signal should fit as `request_social_signal_check` after answer-contract
classification marks social relevance:

- `central`: explicit social-media/social-sentiment questions need either a
  checked side packet or a stable provider-unavailable/blocked status before
  final handoff.
- `relevant_optional`: recommendation questions can use social signal as an
  optional perception/user-experience side packet, but should not block a
  sufficiently grounded factual/recommendation answer.
- `irrelevant`: no action.

The PR #26 offline design is directionally compatible with that slot because it
keeps social signal as sampled public discussion/perception signal, produces an
Author-safe digest, blocks raw packet/comment handoff, and explicitly prevents
ordinary evidence registry merge or factual evidence sufficiency changes.

Runtime integration should wait until the action envelope exists. The future
executor should emit only:

- `social_signal_status`;
- a compact Author-safe digest or provider-unavailable/blocked reason;
- social caveats and confidence;
- action history in the answer-contract handoff.

It should not:

- call a live social provider before policy/API gates exist;
- satisfy official/current/legal/primary evidence gaps;
- repair weak-corpus factual evidence by itself;
- merge raw social packets into ordinary retrieved evidence;
- send raw comments, handles, IDs, source URLs, or raw packets to Author.

## Legal-Source Recovery Position

Legal-source recovery currently sits inside source-class recovery as a limited
official/current/legal source-class action:

- The answer-contract gap trigger can add
  `official_current_rules`, `legal_or_regulatory_text`, or
  `current_primary_or_official` to the source-class recommendation.
- The recommendation can attach official domain constraints for supported
  authority lanes.
- The lifecycle can allow this bounded answer-contract source-class slot even
  when main iteration budget is spent, and can allow a narrow official/legal
  gap after weak-corpus recovery when useful official/legal evidence is still
  absent.
- The executor reuses existing providers and search depth; it does not tune
  providers, increase depth, rerank sources, or change prompts.

AG-22 live validation should be treated as a known limitation, not the main
controller blocker. The observable final reports did not demonstrate final
official/legal/current-primary source quality, and the allowed artifacts did
not expose the internal recovery telemetry needed to isolate whether the issue
was recommendation, action eligibility, provider/depth/domain constraints,
classification, recovered visibility, or final evidence selection.

Therefore legal-source work should not proceed as tuning first. The next legal
step should be sanitized diagnostics that make the current limited action
measurable.

## Recommended Next Phases

### M2 - Action Envelope And Registry

Define a shared action envelope and registry in docs/tests or a tiny pure helper.
Map the existing weak-corpus, source-class, retrieval-stop, and
answer-contract action results into one shape without changing runtime
behavior.

Acceptance target:

- one stable action enum/vocabulary;
- one action status model (`approved`, `blocked`, `skipped`, `shadow`,
  `completed`, `failed`);
- no provider, prompt, persistence, or handoff changes;
- tests proving existing controller decisions can be represented losslessly.

### M3 - Offline Loop Parity Harness

Use the envelope to run an offline action-loop harness from synthetic pipeline
facts and existing trace-shaped facts. Prove that the loop can replay current
weak-corpus, source-class, retrieval-stop, and answer-contract behavior without
driving runtime.

Acceptance target:

- fixture parity for current action histories and fulfillment handoff;
- no live calls;
- no orchestrator behavior changes;
- a clear list of actions still owned by `pipeline_orchestrator.py`.

### S1 - Social Signal As Side-Packet Action

Rebase the useful parts of PR #26 behind the action envelope. Keep it offline
and side-packet only.

Acceptance target:

- social packet schema and Author-safe digest tests;
- adapter from answer-contract social relevance to `request_social_signal_check`;
- no runtime provider integration;
- no ordinary evidence merge;
- no effect on official/legal/weak-corpus recovery.

### L1 - Legal-Source Diagnostics Before Tuning

Add a sanitized validation packet for source-class recovery that can be emitted
or generated without raw logs, prompts, provider payloads, DBs, or caches.

Acceptance target:

- visible fields for considered, eligible, used, missing classes, queries,
  domain constraints, provider role, search depth, recovered quality status,
  recovered visibility, and final source-class counts;
- offline fixture tests for official/legal/current-primary cases;
- only after that, a bounded validation can decide whether provider depth,
  domain support, or regulator-domain expansion is actually needed.

## Bottom Line

The repo already has useful controller components, but the active runtime is
still orchestrator-led. The clean next step is not social runtime wiring or
legal-source tuning. It is a small, explicit action interface that can absorb
the existing weak-corpus, source-class, retrieval-stop, answer-contract, and
future social-signal decisions without changing current behavior.
