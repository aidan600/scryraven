Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (SOURCE_CLASS_CONTROLLER_GATE_AG33).

# AG-33 Source-Class Controller Gate

## Mode And Scope

AG-33 promotes the AG-32 evidence-integration checkpoint from a shadow
recommendation into the active final approval gate for exactly one runtime path:
source-class recovery executor dispatch.

This phase does not make the checkpoint an executor. The orchestrator remains
the executor and continues to run approved actions through the existing
source-class recovery machinery. The controller checkpoint is the approval gate
that the orchestrator must consult before dispatching the source-class recovery
executor.

Runtime behavior changed narrowly: source-class recovery executor dispatch is
now gated by the checkpoint decision.

## Dispatch Rule

The AG-33 dispatch rule is intentionally small and closed:

1. If source-class lifecycle is eligible and the checkpoint action is
   `recover_missing_source_class`, the source-class recovery executor runs as
   before.
2. If source-class lifecycle is eligible and the checkpoint action is anything
   else, the source-class recovery executor does not run.
3. If source-class lifecycle blocks source-class recovery, that lifecycle
   blocker wins. A checkpoint action of `recover_missing_source_class` cannot
   override lifecycle ineligibility.

The non-dispatching checkpoint actions include `stop_sufficient`,
`stop_insufficient_with_caveat`, `retrieve_targeted`, `recover_weak_corpus`,
`resolve_conflict`, `ask_user_clarification`,
`request_social_signal_check`, and `run_scrutineer_review`.

AG-33 does not dispatch any of those alternate actions as substitutes. It only
gates whether source-class recovery executor dispatch is allowed.

## Trace Visibility

The active gate trace must make runtime authority explicit:

- `controller_gate_active`
- `gated_action`
- `checkpoint_action_name`
- `lifecycle_eligible`
- `lifecycle_blockers`
- `executor_dispatched`
- `gate_reason`
- `runtime_behavior_changed`

`gated_action` is `recover_missing_source_class`. `checkpoint_action_name`
records the actual AG-32 checkpoint decision. `executor_dispatched` records
whether the source-class recovery executor actually ran. `gate_reason` records
the stable reason for the gate outcome, including lifecycle blocker precedence.

## Protected Surfaces

AG-33 remains out of scope for:

- provider routing changes
- search-depth changes
- search-budget cap increases
- legal-source tuning
- social runtime provider integration
- targeted retrieval dispatch
- weak-corpus recovery dispatch
- conflict-resolution dispatch
- user clarification flow
- Scrutineer policy or invocation behavior
- Analyst, Economist, Author, or Scrutineer handoff changes
- prompt rewrites
- live calls

The gate is deliberately limited to source-class recovery executor dispatch so
future controller actions can be promoted independently.
