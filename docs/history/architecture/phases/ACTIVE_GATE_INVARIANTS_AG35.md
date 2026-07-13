Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (ACTIVE_GATE_INVARIANTS_AG35).

# AG-35 Active Gate Invariants

AG-35 hardens the AG-33 and AG-34 active checkpoint boundary without promoting
new actions. The AG-32 evidence-integration checkpoint may recommend exactly
one action. The runtime active gate may promote at most one action from that
recommendation.

The active gate contract is:

1. The active packet carries one checkpoint decision.
2. `recommended_action_name` and `checkpoint_action_name` identify the
   checkpoint recommendation.
3. `promoted_action_name` identifies the single runtime-promoted action, or
   remains `None` when no action is promoted.
4. `executed_action_name` identifies a bounded executor that actually ran, or
   remains `None` when the promotion is terminal posture only or blocked.
5. `blocked_or_skipped_actions` records stable rationales for checkpoint actions
   that do not execute and for source-class recovery when it is blocked by a
   terminal stop or non-recovery checkpoint action.

AG-35 promoted three checkpoint actions through the active gate:

- `recover_missing_source_class`, when source-class lifecycle is eligible.
- `stop_sufficient`, as terminal stop posture only.
- `stop_insufficient_with_caveat`, as terminal stop posture only.

Lifecycle blockers remain authoritative. A checkpoint recommendation of
`recover_missing_source_class` cannot run the source-class recovery executor
when the existing lifecycle says the executor is blocked.

Terminal stop decisions block downstream bounded executor dispatch. For
`stop_sufficient` and `stop_insufficient_with_caveat`, the active packet records
`terminal_stop_approved=true`, `executor_dispatch_blocked=true`, and no
`executed_action_name`.

AG-36 later promoted `recover_weak_corpus` through the same active-gate
vocabulary. The remaining checkpoint recommendations stay unpromoted:
`retrieve_targeted`, `resolve_conflict`, `ask_user_clarification`,
`request_social_signal_check`, and `run_scrutineer_review`. They do not
dispatch substitute retrieval, clarification, social, conflict-resolution, or
Scrutineer flows.

`runtime_behavior_changed=true` is reserved for active gate packets. Passive
answer-contract handoff references remain shadow references with
`runtime_behavior_changed=false`.

The AG-35 trace fields are retained only while the AG-33/AG-34 active gate is
the runtime authority boundary. If a later phase replaces this gate with a
central action scheduler, these fields should either become the scheduler's
native decision/execution vocabulary or be deleted with equivalent invariant
tests moved to the new boundary.
