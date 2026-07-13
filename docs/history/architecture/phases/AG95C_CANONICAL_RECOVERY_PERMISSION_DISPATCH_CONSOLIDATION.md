Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG95C_CANONICAL_RECOVERY_PERMISSION_DISPATCH_CONSOLIDATION).

# AG-95C Canonical Recovery Permission Dispatch Consolidation

Status: implemented as offline authority cleanup. No live ScryRaven/proplex
provider, model, search, retrieval, secret, `.env`, DB row, raw provider
payload, raw prompt, private log, cache, full raw trace, or local output packet
access was used.

## Old Competing Dispatch Owners

Before AG-95C, source-class recovery execution could be shaped by multiple
runtime truth surfaces:

- `RunAuthoritySearchJudgment` promoted missing official/current/legal/canonical
  obligations into source-class recovery recommendation fields.
- `official_canonical_recovery_execution_admission` emitted `admission_used` and
  `source_class_recovery_execution_admitted`.
- `source_class_recovery_controller` and `source_class_recovery_lifecycle`
  emitted `active_source_class_recovery_eligible`, recovery action envelopes,
  and legacy action records.
- `ControllerLoopSpine` emitted `authorized_dispatch`.
- `ControllerRecoveryDecision` could still veto executor execution after the
  runner had dispatched.
- `SourceClassRecoveryRunner` consumed the spine value and ran provider-review
  allocation before source-class execution.

That made dispatch multi-owner: lifecycle could say eligible, official admission
could say admitted, the spine could authorize, and the executor could still deny.

## New Canonical Dispatch Path

Source-class recovery dispatch now flows through one runtime permission:

```text
RunAuthorityContract / EvidenceLedger
-> RunAuthoritySearchJudgment consumer
-> AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

`SourceClassRecoveryRunner` reads
`authority_lifecycle.recovery_action.action_type == recover_missing_source_class`
and the canonical lifecycle execution state. It no longer accepts
`authorized_spine_action` in its context and no longer branches on spine output.

The executor is mechanical: active action lookup, envelope validation, query and
search-depth checks, provider-role checks, execution, and trace projection. It
no longer rebuilds or enforces `ControllerRecoveryDecision`.

## Deleted Or Demoted Surfaces

- Deleted runtime executor veto:
  `controller_recovery_executor_allows_attempt()` was removed.
- Deleted runner dispatch input:
  `SourceClassRecoveryRunnerContext.authorized_spine_action` was removed.
- Deleted runner branch:
  the `authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS` dispatch branch
  was removed.
- Demoted `ControllerLoopSpine` source-class dispatch output:
  retained as compatibility/diagnostic trace for the wider controller loop, not
  consumed by the runner.
- Demoted official/canonical admission booleans:
  retained as AuthorityLifecycle construction input and diagnostics, not runner
  dispatch authorization.
- Demoted source-class lifecycle eligibility booleans:
  retained for trace/action-record compatibility, not runner dispatch
  authorization.
- Demoted `ControllerRecoveryDecision` for source-class execution:
  retained as diagnostic trace and as provider-review allocation input only when
  no canonical source-class recovery action is active.

## Protected For Now

- `ControllerLoopSpine` remains because conflict resolution, weak-corpus,
  terminal stop, targeted retrieval, and older static invariants still consume
  its checkpoint arbitration trace. Deleting it now would change non-source-class
  dispatch behavior.
- `ControllerRecoveryDecision` remains because AG-75 provider/search allocation
  review still uses `request_provider_search_review` and its bounded existing
  provider profile. Deleting it now would remove that protected diagnostic and
  allocation path.

## Non-Authority Diagnostics

Report/export/diagnostic fields such as `admission_used`,
`active_source_class_recovery_eligible`,
`active_source_class_recovery_official_canonical_admitted`,
`source_class_recovery_used`, and controller recovery decision trace fields can
explain outcomes. They cannot authorize source-class dispatch without the
canonical `AuthorityLifecycle.recovery_action`.

## Next Deletion Target

Delete or subordinate `ControllerRecoveryDecision` provider-review allocation
after a canonical provider-review action exists under RunAuthority/QueryPlan.
That should retire the remaining `request_provider_search_review` dependency
without changing provider selection, provider order, search depth, query text,
ranking/filtering, Author prose, or citation behavior.
