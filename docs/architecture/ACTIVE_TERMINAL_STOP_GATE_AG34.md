# AG-34 Active Terminal Stop Gate

## Mode And Scope

AG-34 promotes the AG-32 evidence-integration checkpoint into the active stop
gate for closed terminal checkpoint decisions at the post-retrieval seam.

The controller checkpoint now owns only stop approval for
`stop_sufficient` and `stop_insufficient_with_caveat`. The orchestrator remains
the executor and synthesis owner.

## Runtime Behavior

If the checkpoint action is `stop_insufficient_with_caveat`, AG-34 blocks
additional bounded recovery/retrieval executor dispatch and records final answer
posture as `insufficient_with_caveat`.

If the checkpoint action is `stop_sufficient`, AG-34 blocks additional bounded
recovery/retrieval executor dispatch and records final answer posture as
`sufficient`.

If the checkpoint action is `recover_missing_source_class` and the existing
source-class lifecycle is eligible, AG-33 behavior is preserved and the
source-class executor may run.

If the checkpoint action is any other non-stop action, AG-34 does not dispatch it
as a substitute. Targeted retrieval, weak-corpus recovery, conflict resolution,
social signal checks, clarification, and Scrutineer review remain unpromoted at
this seam.

## Trace Visibility

The active checkpoint packet now includes:

- `controller_stop_gate_active`
- `checkpoint_action_name`
- `terminal_stop_approved`
- `final_answer_posture`
- `executor_dispatch_blocked`
- `blocked_executor_types`
- `runtime_behavior_changed`
- `gate_reason`

The blocked executor types are limited to:

- `source_class_recovery`
- `targeted_retrieval`
- `weak_corpus_recovery`
- `conflict_resolution`

## Protected Surfaces

AG-34 does not change provider routing, search depth, legal-source tuning,
prompts, live-call behavior, social runtime integration, Scrutineer policy,
Analyst/Economist/Author handoffs, or budget caps.
