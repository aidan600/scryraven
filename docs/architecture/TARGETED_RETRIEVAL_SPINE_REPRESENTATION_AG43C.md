# AG-43C Targeted Retrieval Spine Representation

## Status

Design only. This note does not implement runtime behavior.

AG-43C defines the next safe representation step for `retrieve_targeted` after
AG-43A/AG-43B introduced a pure targeted-retrieval lifecycle and passive
runtime observation. It does not add active targeted retrieval dispatch, a
targeted retrieval executor, provider routing changes, search-depth changes,
query-generation changes, prompt changes, persistence changes, legal/current
source repair, or ordinary continuation changes.

## Diagnosis

The current system has enough passive facts to recognize a targeted retrieval
candidate, but not enough authority inversion to execute it safely.

Current facts:

- `decide_evidence_integration_checkpoint` can select `retrieve_targeted`.
- `targeted_retrieval_controller` can mark an ordinary next-query candidate as
  eligible from sanitized, already-computed facts.
- AG-43B runtime wiring records passive lifecycle fields such as
  `targeted_retrieval_candidate_eligible` and
  `targeted_retrieval_candidate_used=false`.
- `controller_loop_spine` still does not authorize `retrieve_targeted`.
- Scout, expander, and evaluator branches in `pipeline_orchestrator` still own
  ordinary continuation by assigning `current_queries`, incrementing
  `iteration`, and continuing the retrieval loop.

That means the missing boundary is not candidate recognition. The missing
boundary is runtime ownership. If the spine promoted `retrieve_targeted` before
old ordinary continuation is subordinate to the spine, the system would have two
possible dispatch owners for the same retrieval pass.

## Recommendation

Represent checkpoint-selected, lifecycle-eligible `retrieve_targeted` as
**blocked by runtime dispatch not inverted**.

Do not represent it as:

- passive eligible only, because AG-43B already proves that and it leaves the
  spine blind to a checkpoint-selected eligible targeted candidate;
- promoted but not executable, because `retrieve_targeted` is not terminal
  posture and promotion would imply the active gate has accepted a non-terminal
  action without a bounded executor contract;
- fully unpromoted, because the next useful step is to make the block explicit
  and testable at the active gate boundary.

The AG-43C representation should therefore be:

- checkpoint decision: `retrieve_targeted`
- targeted lifecycle: considered/eligible facts visible to the spine
- promoted action: `None`
- executed action: `None`
- authorized dispatch: `None`
- blocked/skipped reason: `blocked_by_runtime_dispatch_not_inverted`

This gives the spine an auditable negative decision without adding an executor
or letting old orchestrator continuation count as controller-authorized
dispatch.

## Should The Spine Know Targeted Lifecycle Facts?

Yes, but only as sanitized passive gate input.

`ControllerLoopSpineInput` should be allowed to carry a
`targeted_retrieval_lifecycle_trace` alongside source-class, weak-corpus, and
conflict lifecycle traces. The spine may read the targeted lifecycle fields to
record why `retrieve_targeted` did or did not promote. It must not use those
fields to call retrieval, choose providers, choose search depth, generate
queries, alter ordinary continuation, or authorize a substitute executor.

The lifecycle trace should remain the same passive object produced by
`targeted_retrieval_controller`; it should not import runtime surfaces into the
spine.

## Proposed Trace Shape

The active gate packet should keep the AG-35 vocabulary:

```text
checkpoint_decision_count = 1
checkpoint_action_name = "retrieve_targeted"
promoted_action_name = None
executed_action_name = None
authorized_action_name = None
blocked_or_skipped_actions["retrieve_targeted"] =
    "blocked_by_runtime_dispatch_not_inverted"
```

Add targeted-specific gate fields without changing the passive lifecycle
meaning:

```text
targeted_retrieval_gate_active = true
targeted_retrieval_gated_action = "retrieve_targeted"
targeted_retrieval_lifecycle_considered = true
targeted_retrieval_lifecycle_eligible = true
targeted_retrieval_lifecycle_blockers = []
targeted_retrieval_executor_dispatched = false
targeted_retrieval_dispatch_authorized = false
targeted_retrieval_gate_reason = "blocked_by_runtime_dispatch_not_inverted"
targeted_retrieval_runtime_dispatch_inverted = false
```

If the checkpoint selects `retrieve_targeted` but the lifecycle is blocked, the
spine should report the lifecycle blocker instead:

```text
promoted_action_name = None
executed_action_name = None
blocked_or_skipped_actions["retrieve_targeted"] = <lifecycle reason>
targeted_retrieval_gate_reason = <lifecycle reason>
targeted_retrieval_lifecycle_eligible = false
targeted_retrieval_executor_dispatched = false
```

If another checkpoint action is selected while the targeted lifecycle is merely
eligible, targeted retrieval stays skipped:

```text
blocked_or_skipped_actions["retrieve_targeted"] =
    "checkpoint_action_not_approved"
targeted_retrieval_gate_reason = "checkpoint_action_not_approved"
targeted_retrieval_executor_dispatched = false
```

Terminal stops remain stronger than targeted eligibility:

```text
blocked_or_skipped_actions["retrieve_targeted"] = "blocked_by_terminal_stop"
targeted_retrieval_gate_reason = "blocked_by_terminal_stop"
targeted_retrieval_executor_dispatched = false
```

The passive lifecycle fields remain passive:

```text
targeted_retrieval_candidate_eligible = true | false
targeted_retrieval_candidate_used = false
targeted_retrieval_candidate_queries = ordinary next queries only
targeted_retrieval_candidate_conflict_resolving_queries =
    conflict resolving queries only, never copied from ordinary next queries
```

AG-43C should not set `targeted_retrieval_candidate_used=true`.

## Blocked And Skipped Action Semantics

When the checkpoint selects `retrieve_targeted`, `blocked_or_skipped_actions`
must include `retrieve_targeted` whenever no executor runs.

Reason priority:

1. `blocked_by_terminal_stop`
2. targeted lifecycle reason, such as `blocked_by_source_class_recovery`,
   `blocked_by_weak_corpus_recovery`, `blocked_by_conflict_resolution`,
   `blocked_by_currentness_gap`, `blocked_by_iteration_budget`,
   `no_approved_queries`, or `query_generation_required`
3. `blocked_by_runtime_dispatch_not_inverted` when the checkpoint selects
   `retrieve_targeted` and lifecycle is otherwise eligible
4. `checkpoint_action_not_approved` when another checkpoint action was selected

This preserves one checkpoint decision and at most one promoted action. It also
keeps lifecycle blockers authoritative: the runtime-inversion blocker is used
only after the targeted lifecycle has already said the candidate is eligible.

## Avoiding Substitute Dispatch

Old scout, expander, and evaluator continuation must not be counted as
controller-authorized targeted retrieval.

AG-43C should preserve these boundaries:

- no `RETRIEVE_TARGETED` authorized dispatch value;
- no `authorized_action_name == "retrieve_targeted"`;
- no `executed_action_name == "retrieve_targeted"`;
- no `targeted_retrieval_candidate_used=true`;
- no provider role of `retrieve_targeted`;
- no search call caused by the post-checkpoint spine representation;
- ordinary continuation traces remain ordinary retrieval loop traces, not
  controller-spine dispatch traces.

The old continuation path may still run before the evidence-integration
checkpoint because AG-43C is representation only. It must not be re-labeled as
spine-authorized.

## Required Invariant Tests

Add tests in a later implementation phase that prove:

- A checkpoint-selected `retrieve_targeted` with eligible targeted lifecycle
  produces `promoted_action_name is None`, `executed_action_name is None`, and
  `blocked_or_skipped_actions["retrieve_targeted"] ==
  "blocked_by_runtime_dispatch_not_inverted"`.
- `ControllerLoopDispatchAuthorization.from_trace_packet` does not return
  `retrieve_targeted` as `authorized_action_name`.
- Terminal stop checkpoint actions record `retrieve_targeted` as
  `blocked_by_terminal_stop` and dispatch no bounded executor.
- Source-class, weak-corpus, and conflict selected actions remain mutually
  exclusive with targeted retrieval.
- A lifecycle-blocked targeted candidate reports the lifecycle blocker instead
  of the runtime-inversion blocker.
- Ordinary `next_queries` remain separate from conflict `resolving_queries`.
- Runtime harnesses forcing a checkpoint `retrieve_targeted` do not produce an
  extra search call, a `retrieve_targeted` provider role, source-class recovery,
  weak-corpus recovery, conflict resolution, social signal, Scrutineer, or
  clarification as a substitute.
- Static guards continue to show no targeted executor, no provider/routing/depth
  imports in the spine, and no `retrieve_targeted` dispatch branch in the
  orchestrator.

## Stop Conditions

Return STOP instead of implementing runtime behavior if representation requires:

- active targeted dispatch;
- a targeted retrieval executor;
- provider routing, provider selection, search-depth, prompt, or query
  generation changes;
- treating old scout, expander, or evaluator continuation as
  controller-authorized dispatch;
- merging ordinary `next_queries` with conflict `resolving_queries`;
- ambiguity with source-class recovery, weak-corpus recovery, or conflict
  resolution;
- legal/current-event source repair;
- weakening one-decision, one-promotion, lifecycle-blocker, terminal-stop, or
  no-substitute-dispatch invariants.

## Recommended Next Phase

The next implementation phase, if taken, should be AG-43D:
**targeted retrieval spine block representation**.

Scope for AG-43D:

- pass targeted lifecycle trace into `ControllerLoopSpineInput`;
- add targeted gate trace fields;
- record `retrieve_targeted` in `blocked_or_skipped_actions` with
  `blocked_by_runtime_dispatch_not_inverted` when checkpoint-selected and
  lifecycle-eligible;
- prove no substitute dispatch and no runtime search behavior change.

Out of scope for AG-43D:

- active `retrieve_targeted` promotion;
- executor creation;
- adding `RETRIEVE_TARGETED` to authorized dispatch;
- orchestrator loop inversion;
- provider, routing, depth, query-generation, prompt, legal/current-source, or
  ordinary continuation changes.

Active targeted retrieval promotion is not ready.
