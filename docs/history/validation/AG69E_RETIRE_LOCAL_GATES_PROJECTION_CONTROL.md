Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG69E_RETIRE_LOCAL_GATES_PROJECTION_CONTROL).

# AG-69E Retire Local Gates / Projection-as-Control Paths

Scope: offline lifecycle/controller/projection-control work only. No live
ProPlex runs, provider/model/search calls, provider routing, provider
selection, provider depth, retrieval/ranking/filtering policy, prompt wording,
citation rendering, final-answer behavior, legal answer behavior, follow-up
behavior, direct IRS/SSA special casing, or broad pipeline orchestration change
was made.

## Goal

Remove, downgrade, or prove projection-only status for legacy local gates and
projection-as-control paths now superseded by controller-owned
`AuthorityLifecycle`.

## Decision Records

### 1. Reconnaissance Review

AG-69A through AG-69D established lifecycle ownership for arbitration,
execution, candidate fit, and final evidence visibility. Remaining legacy
control risk was concentrated in small post-handoff places:

- `controller_loop_spine` still read legacy source-class eligibility/envelope
  fields while an `authority_lifecycle` was present.
- `authority_lifecycle_execution` could copy legacy `candidate_return_status`
  into lifecycle candidate state.
- `authority_lifecycle_candidate_visibility` could let legacy
  `accepted_url_count` / `recovered_result_count` / source-fit counters imply
  lifecycle candidate truth.
- `recovered_evidence_visibility` could still block post-execution visibility
  using legacy `active_source_class_recovery_*`, blocker, reason, duplicate
  attempt, and quality fields even when lifecycle execution had occurred.

### 2. Pre-Implementation Decision

Keep `pipeline_orchestrator.py` as plumbing and do not add domain logic there.
Make lifecycle-present branches derive control from `authority_lifecycle`
state; keep legacy fields only as compatibility projections/exports with named
consumers and deletion criteria.

### 3. Post-Implementation Self-Review

Implemented scoped downgrades:

- `controller_loop_spine` derives source-class dispatch eligibility,
  official/canonical admission, and recovery-action approval from
  `AuthorityLifecycle` when present.
- `authority_lifecycle_execution` derives candidate-return status from
  lifecycle execution counts instead of legacy `candidate_return_status`.
- `authority_lifecycle_candidate_visibility` prefers lifecycle execution
  counts over legacy recovered/accepted/source-fit counters when lifecycle is
  present.
- `recovered_evidence_visibility` uses lifecycle execution/action/source-class
  state when lifecycle is present, and no longer lets legacy used/provider-role,
  weak-corpus blocker, duplicate-attempt, reason, or quality fields block that
  lifecycle-owned visibility path.
- `core/authority_lifecycle_compatibility_fields.py` records retained
  compatibility fields, replacements, named consumers, and deletion/promotion
  criteria. It is documentation/test metadata only and is not imported by the
  runtime pipeline.

### 4. Validation Decision

Validation remained offline. Focused AG-69E tests poison legacy projection
fields while preserving lifecycle state and prove terminal-stop, weak-corpus,
execution, candidate-return, source-fit, final-evidence, and visibility/export
fields cannot independently control when lifecycle state exists.

### 5. Final Recommendation Review

This phase reduces non-lifecycle decision ownership. The next layer to open
should be AG-69F review of any remaining final citation/synthesis visibility
survival issues, not provider/search/prompt behavior.

## Legacy Field Audit

| Field | Status | AuthorityLifecycle replacement | Current named consumers | Deletion / promotion criterion |
| --- | --- | --- | --- | --- |
| `terminal_stop_approved` | Retained as pre-lifecycle fact and diagnostic projection | `authority_lifecycle.terminal_stop_state`, `authority_lifecycle_terminal_stop_may_preempt` | orchestrator adapter fact builder, runtime arbitration, checkpoint trace tests | Retire after checkpoint stop decisions emit requirement-bound lifecycle terminal state/blockers directly. |
| `weak_corpus_recovery_owns_path` | Downgraded to legacy blocker/projection | `authority_lifecycle.weak_corpus_state`, `authority_lifecycle_weak_corpus_may_own_path` | runtime arbitration blocker filter, targeted retrieval diagnostics, weak-corpus tests | Retire after weak-corpus recovery emits lifecycle ownership state instead of blocker strings. |
| `blocked_by_weak_corpus_recovery` | Downgraded to legacy blocker/projection | lifecycle weak-corpus state/blockers | runtime arbitration filter, source-class compatibility tests, diagnostics | Retire after all recovery blockers carry lifecycle owner and requirement id. |
| `active_source_class_recovery_eligible` | Retained as compatibility handoff/projection | lifecycle recovery action plus `authority_lifecycle_required_recovery_allowed` | executor action lookup, visibility export, trace summary, offline tests | Retire after executor lookup consumes lifecycle recovery action directly. |
| `active_source_class_recovery_used` | Downgraded to execution projection | `authority_lifecycle.execution_state.state == attempted` | visibility export, planned/observed diagnostics, task ledger, tests | Retire after exports/diagnostics read lifecycle execution state directly. |
| `active_source_class_recovery_execution_attempted` | Downgraded to execution projection | `authority_lifecycle.execution_state.state == attempted` | visibility export, lifecycle trace compatibility, AG-68/69 tests | Retire after execution exports consume lifecycle execution state. |
| `accepted_url_count` | Downgraded to visibility/export projection | lifecycle execution/candidate-fit accepted URL counts | visibility export, source-class diagnostics, provider diagnostics tests | Retire after accepted/readable diagnostics consume lifecycle candidate-fit projection. |
| `recovered_result_count` | Downgraded to visibility/export projection | lifecycle execution recovered result count | visibility export, source-class diagnostics, AG-50 tests | Retire after result diagnostics consume lifecycle execution state. |
| `candidate_return_status` | Downgraded to visibility/export projection | lifecycle candidate-fit return status | visibility export, AG-50 tests | Retire after exports read lifecycle candidate-fit state. |
| `recovered_visibility_source_fit_*` | Downgraded to visibility/export projections | lifecycle candidate-fit state, selected evidence, structured rejections | visibility export, AG-52 tests, AG-69 tests | Retire after report diagnostics consume lifecycle candidate-fit fields directly. |

The full retained-field manifest lives in
`core/authority_lifecycle_compatibility_fields.py`.

## Protected Surfaces

Remained closed:

- provider routing, provider selection, provider depth;
- retrieval, ranking, filtering;
- prompt wording;
- citation rendering and final-answer behavior;
- Author, Analyst, Economist, Scrutineer, legal answer, and follow-up behavior;
- direct IRS/SSA special casing;
- live validation.
