# AG-36 Weak-Corpus Recovery Active Gate

AG-36 promotes `recover_weak_corpus` into the active evidence-integration
checkpoint gate. Weak-corpus recovery still uses the existing eligibility
controller and bounded recovery retrieval path; the new authority boundary is
that eligible recovery only executes when the checkpoint decision is
`recover_weak_corpus`.

The active gate now promotes four actions:

- `recover_missing_source_class`, when source-class lifecycle is eligible.
- `recover_weak_corpus`, when weak-corpus recovery eligibility is approved.
- `stop_sufficient`, as terminal stop posture only.
- `stop_insufficient_with_caveat`, as terminal stop posture only.

Weak-corpus lifecycle blockers remain authoritative. If the weak-corpus
controller blocks recovery, a checkpoint recommendation of `recover_weak_corpus`
does not override the blocker. Terminal stop recommendations also block
weak-corpus recovery and record `recover_weak_corpus` in
`blocked_or_skipped_actions` with `blocked_by_terminal_stop`.

When the checkpoint recommends another non-promoted action such as
`retrieve_targeted`, `resolve_conflict`, `request_social_signal_check`, or
`run_scrutineer_review`, AG-36 does not dispatch substitute flows. The packet
records `recover_weak_corpus` as skipped with `checkpoint_action_not_approved`
when weak-corpus recovery was otherwise eligible.

If weak-corpus recovery is otherwise eligible but the checkpoint selects
`recover_missing_source_class`, AG-36 also records `recover_weak_corpus` as
skipped with `checkpoint_action_not_approved`. In that case, the unpromoted
weak-corpus recovery path does not itself block AG-33 source-class recovery.
Source-class lifecycle and eligibility still decide whether
`recover_missing_source_class` can execute.

This preserves the one-checkpoint-decision / one-promoted-action contract. The
checkpoint may choose weak-corpus recovery or source-class recovery, but the
orchestrator must not execute both.

Trace packets continue to use the AG-35 active-gate vocabulary:
`checkpoint_decision_count`, `checkpoint_action_name`,
`promoted_action_name`, `executed_action_name`,
`blocked_or_skipped_actions`, `gate_reason`, and
`runtime_behavior_changed`. When weak-corpus recovery executes, both
`promoted_action_name` and `executed_action_name` are
`recover_weak_corpus`, and `runtime_behavior_changed=true`.

AG-36 intentionally does not implement targeted retrieval continuation,
conflict-resolution execution, social provider integration, Scrutineer
invocation changes, provider routing changes, search-depth changes, search
budget increases, legal/source-domain tuning, prompt changes, or
Analyst/Economist/Author handoff changes.
