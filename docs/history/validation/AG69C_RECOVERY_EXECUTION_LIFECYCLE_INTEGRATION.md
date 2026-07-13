Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG69C_RECOVERY_EXECUTION_LIFECYCLE_INTEGRATION).

# AG-69C Recovery Execution Lifecycle Integration

Scope: offline controller/lifecycle execution integration only. No live
ProPlex runs, provider/model/search calls, provider routing, provider
selection, provider depth, retrieval/ranking/filtering behavior, prompt
wording, citation/final-answer behavior, legal answer behavior, follow-up
behavior, or broad pipeline orchestration change was made.

## Goal

Integrate lifecycle-approved authoritative recovery with the existing
source-class recovery executor boundary. Once the controller/lifecycle approves
required authoritative recovery, the approval now becomes either a real
executor entrypoint attempt or a structured requirement-bound lifecycle
execution blocker.

## Decision Records

### 1. Reconnaissance Review

AG-69B made terminal-stop and weak-corpus arbitration defer to lifecycle-owned
recovery permission. The remaining gap was execution state: the nested
`authority_lifecycle` could remain pending while legacy flags were mutated, and
non-dispatch paths could report only `attempted=false`.

### 2. Pre-Implementation Decision

Keep the orchestrator as plumbing. Add a lifecycle execution bridge that is
called by the existing executor entrypoint and by the orchestrator's
non-dispatch branch. Do not change provider routing, retrieval, ranking,
filtering, prompt wording, candidate source-fit, evidence visibility, citation,
or final-answer behavior.

### 3. Post-Implementation Self-Review

`core/authority_lifecycle_execution.py` now owns lifecycle execution
projection. The real `execute_source_class_recovery_action` entrypoint marks
AuthorityLifecycle execution as `attempted`. If approved recovery cannot be
dispatched, the bridge records a structured requirement-bound blocker with:

- `requirement_id`;
- `blocker_reason`;
- `blocker_owner=controller/lifecycle`;
- `recovery_may_be_retried`;
- `final_posture_must_be_insufficient_partial`.

Legacy fields such as
`active_source_class_recovery_execution_attempted` are projected from the
lifecycle execution state when AuthorityLifecycle is present.

### 4. Validation Decision

Validation remained offline. Focused AG-69C tests prove real-path executor
entrypoint reachability with a spy, structured blockers, projection derivation,
terminal/weak preservation, and state distinction. AG-69A, AG-69B, AG-68, and
official/canonical recovery slices passed.

### 5. Final Recommendation Review

This phase should be reviewed as a controller-owned execution lifecycle bridge.
The next layer to open remains post-execution candidate/source-fit and final
evidence/citation survival, not provider/search/prompt behavior.

## Protected Surfaces

Remained closed:

- provider routing, provider selection, provider depth;
- retrieval, ranking, filtering;
- prompt wording;
- candidate source-fit evaluation;
- recovered evidence visibility behavior;
- citation and final-answer behavior;
- Author, Analyst, Economist, Scrutineer, legal answer, and follow-up behavior;
- broad `core/pipeline_orchestrator.py` domain logic;
- live validation.
