Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG50D_OFFICIAL_CANONICAL_RECOVERY_EXECUTION_DISPATCH_REPAIR).

# AG-50D Official/Canonical Recovery Execution Dispatch Repair

## Phase Purpose

AG-50D repairs the bounded dispatch/lifecycle seam after AG-50B admission and
AG-50C allowed-artifact visibility showed:

- `admission_used=true`
- `source_class_recovery_eligible=true`
- `source_class_recovery_used=false`
- likely next layer `execution_not_attempted`

The phase goal was not answer quality. It was to ensure the existing
source-class recovery executor is actually dispatched once for an admitted,
eligible official/current/canonical recovery slot unless a hard blocker owns the
path.

## Decision Tree Branch Taken

Step 1 classified the local cause as:

**B. lifecycle action created but executor not called.**

The lifecycle already created a controller-approved `source_class_recovery`
action when AG-50B admission supplied the official/canonical slot. The
orchestrator executor call, however, was keyed only off checkpoint-spine
authorization for `recover_missing_source_class`. A stale or alternate
non-terminal checkpoint action could leave an admitted lifecycle action pending.

## Seam Repaired

The repaired seam is the controller-spine/lifecycle handoff:

- lifecycle now records whether the active source-class recovery action was
  backed by an AG-50B official/canonical admission slot;
- the controller-loop spine authorizes that exact admitted slot when lifecycle
  is eligible and no terminal stop owns the path;
- the existing `execute_source_class_recovery_action` remains the only executor;
- allowed-artifact export now reports execution-attempt and candidate-return
  status from sanitized fields.

## Behavior Change

For a required official/current/canonical obligation with an AG-50A recovery
query and AG-50B admission:

- ordinary iteration budget exhaustion no longer prevents the one bounded
  source-class recovery executor dispatch;
- lifecycle provenance records
  `active_source_class_recovery_official_canonical_admitted`;
- execution records
  `active_source_class_recovery_execution_attempted`;
- allowed artifacts expose `source_class_recovery_execution_attempted`,
  `candidate_return_status`, and AG-50D `next_failure_layer`.

Terminal stop, weak-corpus ownership, conflict ownership, hard recovery cap,
missing query, already-satisfied source class, preferred-only obligation, and
unknown/not-required obligation cases remain blocked or skipped.

## Protected Surfaces Not Touched

AG-50D did not intentionally change:

- provider routing;
- provider selection;
- provider depth/search-depth policy;
- provider escalation;
- provider roles;
- query wording or query generation;
- prompts;
- source ranking/filtering;
- returned-source classification;
- Economist behavior;
- Analyst behavior;
- Author behavior;
- Scrutineer behavior;
- final-answer behavior;
- source-specific PostgreSQL, SQLite, SSA, or other domain rules.

## Tests

Added:

- `tests/test_official_canonical_recovery_execution_dispatch_ag50d.py`

Coverage includes:

- required canonical obligation with AG-50A query dispatches the existing
  source-class recovery executor;
- required official/current obligation dispatches under the same bounded slot;
- preferred and unknown obligations do not force execution;
- already satisfied source class does not force execution;
- terminal, weak-corpus, conflict, prior-attempt, and missing-query blockers are
  preserved;
- ordinary iteration budget exhaustion does not block the AG-50B slot;
- lifecycle and visibility export report execution-attempt consistently;
- candidate-return and accepted/readable facts remain unknown unless directly
  visible;
- no new provider role or executor is introduced;
- pure helpers avoid protected imports.

Required regression suites run successfully; see final phase bundle for command
results.

## Live Validation Budget Used

Approved live query:

`Explain how PostgreSQL MVCC works, why it improves read/write concurrency, and what tradeoffs it creates. Do not assume the reader is a database expert.`

Budget used:

- Live ProPlex runs: 1 of 2 approved
- Second live run: not used, because the first run moved past dispatch and the
  remaining failure layer is outside AG-50D scope
- Independent external source checks: 1 of 2 approved

## Live Result

Allowed CLI artifacts after AG-50D exposed:

- `admission_considered=true`
- `admission_eligible=true`
- `admission_used=true`
- `source_class_recovery_eligible=true`
- `source_class_recovery_used=true`
- `source_class_recovery_execution_attempted=true`
- `source_class_recovery_provider_role=source_class_recovery`
- `recovery_query_previews=canonical documentation PostgreSQL MVCC`
- `recovered_result_count=0`
- `accepted_url_count=0`
- `candidate_return_status=zero_candidates`
- `next_failure_layer=execution_attempted_zero_candidates`

Final citations remained:

- `https://arxiv.org/pdf/1201.0228`
- `https://arxiv.org/pdf/1208.4179`

No PostgreSQL official documentation survived into citations.

## Source-Quality Evaluation Summary

The final answer was broadly readable and mostly correct, but source grounding
remained weak for a canonical PostgreSQL technical-reference question. The
obvious canonical sources from the independent check were PostgreSQL current
documentation pages:

- `https://www.postgresql.org/docs/current/mvcc.html`
- `https://www.postgresql.org/docs/current/mvcc-intro.html`

ProPlex did not cite those pages. The AG-50D diagnostics show this is no longer
an execution-dispatch failure; the recovery executor ran and returned zero
candidates from allowed artifact visibility.

## Next Failure Layer After AG-50D

`execution_attempted_zero_candidates`

## Recommended Next Phase

Open the protected surface:

- source-class recovery candidate acquisition/provider-depth behavior for the
  already-admitted official/current/canonical recovery slot.

Why this surface is next:

- AG-50D proves admission and execution dispatch now occur.
- The existing executor attempted the recovery query.
- Sanitized allowed artifacts report zero recovered candidates.
- No PostgreSQL canonical documentation reached final evidence or citations.

Smallest safe next behavior change:

- For one already-admitted official/current/canonical source-class recovery
  execution slot, repair candidate acquisition enough to return at least one
  canonical/official candidate when the generic recovery query targets an
  obvious canonical documentation source class.

Suggested live success criterion:

- Same PostgreSQL MVCC query.
- Allowed artifacts show `source_class_recovery_execution_attempted=true`,
  `recovered_result_count>0`, and either a PostgreSQL official/canonical
  candidate returned or a precise sanitized blocker explaining why acquisition
  could not return one.
