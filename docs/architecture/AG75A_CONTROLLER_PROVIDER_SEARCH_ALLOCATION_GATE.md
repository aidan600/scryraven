# AG-75A Controller Provider/Search Allocation Gate

Date: 2026-05-28

## Scope

AG-75A opens only a Controller-owned provider/search allocation gate for
official/current acquisition failure states. It is not generic provider
escalation, not IRS repair, not provider swapping, not new provider
integration, not query strategy repair, and not final-answer/citation/Author
behavior work.

The implemented action is record-only. It records that provider/search
allocation review is required for a later, separately licensed phase. It does
not execute provider calls, change provider routing, change search depth, add
providers, retry queries, or use live validation.

## AG-74F Prerequisite Verification

Current `main` contained AG-74F / PR #19 before implementation:

```text
4452079 Merge pull request #19 from aidan600/codex/ag74f-recovery-runner-extraction
1030d48 Update spine dispatch guard for recovery runner
a3daf78 Add AG-74F recovery runner extraction
```

Required AG-74F artifacts were present:

- `docs/architecture/AG74F_RECOVERY_RUNNER_EXTRACTION.md`
- `core/source_class_recovery_runner.py`
- `core/controller_recovery_decision.py`
- `core/source_class_recovery_executor.py`
- `tests/test_ag74f_recovery_runner_extraction.py`
- `tests/test_ag74e_recovery_executor_orchestrator_checkpoint.py`
- `tests/test_ag74d_controller_recovery_retry_stop_loop.py`

Verified repo facts:

- `core/source_class_recovery_runner.py` is the recovery runner boundary for
  source-class recovery dispatch.
- `core/pipeline_orchestrator.py` delegates to
  `run_source_class_recovery_dispatch(SourceClassRecoveryRunnerContext(...))`
  and no longer owns detailed source-class recovery executor dispatch logic.
- `ControllerRecoveryDecision` emits `request_provider_search_review`.
- No local/orchestrator helper independently implemented provider/search
  allocation before AG-75A.

## Controller Authorization

The only Controller action that authorizes AG-75A provider/search allocation is:

```text
ControllerRecoveryDecision.decision == "request_provider_search_review"
```

The gate also requires:

- `provider_search_review_requested is True`;
- `allowed_executor_action == "record_provider_search_review_request"`;
- `decision_reason == "no_candidate_acquired_provider_search_review_needed"` or
  `candidate_state_summary == "no_plausible_official_current_candidate_acquired"`.

No legacy aggregate failure, recovery-lane observation, final answer failure,
citation absence, readability failure, classifier/currentness failure,
candidate-fit rejection, context exposure failure, follow-up state, or generic
no-answer state can trigger allocation without that Controller decision.

## Mechanical Execution

New owner:

- `core/controller_provider_search_allocation.py`

Mechanical runner:

- `core/source_class_recovery_runner.py`

The runner receives an explicit `ControllerRecoveryDecision` in
`SourceClassRecoveryRunnerContext` and calls
`record_provider_search_allocation_if_controller_authorized(...)` before any
source-class recovery search execution. If the decision is
`request_provider_search_review`, the runner records:

- `provider_search_allocation_trace`;
- `recovery_decision` / `recovery_decision_trace` compatibility fields;
- a source-class recovery skip reason:
  `controller_recovery_decision_requested_provider_search_review`.

The runner returns no URL/chunk deltas and does not call
`process_search_queries(...)` for this action.

## Local Escalation Prevention

`core/pipeline_orchestrator.py` remains handoff/plumbing only. It passes the
Controller decision into the runner context, but it does not import the
allocation helper, does not write `provider_search_allocation_trace`, and does
not branch on provider/search allocation.

`core/source_class_recovery_executor.py` remains closed for provider/search
allocation. It does not record the AG-75A allocation trace and does not execute
provider/search review.

The allocation helper has no provider call surface. It does not call
`process_search_queries`, select providers, route providers, change depth, or
alter query strategy.

## Explicit Non-Allocation States

Tests prove these are not provider/search allocation cases:

- controller-complete final evidence/citation custody;
- `continue_downstream`;
- `stop_sufficient`;
- `stop_legacy_custody_gap`;
- `missing_controller_disposition` /
  `stop_for_architecture_decision`;
- candidate acquired but unreadable;
- candidate readable but misclassified;
- candidate classified but fit/currentness rejected;
- exhausted budget with `stop_insufficient`;
- context exposure failure;
- Analyst/Author/citation-surface failure;
- final answer/citation behavior issues;
- any state where `ControllerRecoveryDecision` is absent.

## Provider/Search Behavior

Provider/search behavior is preserved. AG-75A implements only:

```text
record_provider_search_review_request
```

The record is bounded and diagnostic:

- no provider calls;
- no new providers;
- no provider swaps;
- no Linkup escalation;
- no search-depth change;
- no deep/unlimited search default;
- no query change;
- no retrieval ranking/filtering change;
- no classifier/currentness/candidate-fit change.

## Closed Surfaces

Closed surfaces remain closed:

- broad provider strategy rewrite;
- new providers or provider swaps;
- unlimited/deep search by default;
- uncontrolled Linkup escalation;
- query strategy and source constraints;
- retrieval ranking/filtering;
- source-class/currentness classifier semantics;
- candidate-fit semantics;
- prompt, Author, citation formatting, final-answer, follow-up, Scrutineer, and
  Economist behavior;
- direct IRS hardcoding or source-specific resolver implementation;
- live ScryRaven/proplex/scryraven provider/model/search calls;
- raw provider payloads, raw prompts, DB rows, private logs, caches, secrets,
  full traces, and ignored local output packets.

## Behavior Parity Evidence

AG-75A does not change final-answer, citation, Author, prompt, or provider
execution behavior. The record includes explicit parity flags:

- `final_answer_behavior_unchanged: True`
- `citation_behavior_unchanged: True`
- `provider_policy_unchanged: True`
- `provider_selection_unchanged: True`
- `search_depth_policy_unchanged: True`
- `query_strategy_unchanged: True`

Focused tests also assert that the AG-75A helper and runner do not import or
call final-answer surfaces.

## Trace / Export Compatibility

AG-75A does not add new top-level `controller_*` execution-trace payload keys.
The new execution-trace key is neutral:

```text
provider_search_allocation_trace
```

`core/official_canonical_recovery_visibility_export.py` whitelists a sanitized
projection at:

```text
provider_search_allocation_trace
```

The projection contains only bounded review-plan fields and parity booleans. It
does not expose raw provider payloads, prompts, secrets, URLs from private logs,
or provider output packets.

## Tests

AG-75A added:

- `tests/test_ag75a_controller_provider_search_allocation_gate.py`

Updated compatibility tests:

- `tests/test_ag74f_recovery_runner_extraction.py`
- `tests/test_ag74e_recovery_executor_orchestrator_checkpoint.py`

Coverage includes:

- Controller decision authorizes provider/search allocation;
- runner/helper records the action mechanically;
- allocation does not run without `ControllerRecoveryDecision`;
- non-acquisition failure states do not allocate;
- no provider/search execution occurs during allocation recording;
- orchestrator and executor do not implement allocation;
- final-answer/citation behavior remains closed;
- sanitized export observes the record.

## Demolition Ledger

1. Old provider/search escalation or allocation path targeted:
   the previous absence of an allocation owner after
   `request_provider_search_review`.
2. New Controller-owned provider/search allocation owner:
   `ControllerRecoveryDecision` authorizes;
   `core/controller_provider_search_allocation.py` records.
3. Mechanical runner/helper that executes or records the action:
   `run_source_class_recovery_dispatch(...)` calls
   `record_provider_search_allocation_if_controller_authorized(...)`.
4. Observer/export surface:
   neutral `provider_search_allocation_trace` in runtime trace and
   `official_canonical_recovery_visibility_export`.
5. Old code deleted, bypassed, or subordinated:
   no old provider escalation path was present; orchestrator/provider helpers
   are subordinated because they cannot allocate without the Controller decision.
6. Tests proving Controller authorization is required:
   `test_ag75a_controller_decision_records_bounded_provider_search_allocation`
   and
   `test_ag75a_absent_controller_recovery_decision_does_not_allocate`.
7. Tests proving non-acquisition failures do not allocate:
   `test_ag75a_non_acquisition_failure_states_do_not_allocate`.
8. Tests proving provider/search implementation stayed within license:
   `test_ag75a_static_guards_keep_allocation_out_of_orchestrator_and_executor`
   and the record-only assertions in the allocation test.
9. Tests proving final answer/citation behavior parity:
   `test_ag75a_final_answer_and_citation_surfaces_remain_closed`.
10. Remaining old code/path to delete next:
    `pipeline_orchestrator.py` construction of
    `SourceClassRecoveryRunnerContext(...)`.
11. Net complexity impact:
    one small helper and one runner hook; no new provider execution path; lower
    ambiguity because `request_provider_search_review` now has an explicit,
    bounded owner instead of being an unhandled decision value.

## Next Deletion Target

Delete or shrink the remaining `pipeline_orchestrator.py` runner handoff:

```text
pipeline_orchestrator.py
  -> SourceClassRecoveryRunnerContext(...)
  -> run_source_class_recovery_dispatch(...)
```

That deletion should remain mechanical and must not reopen provider/search
routing logic inside the orchestrator.

## Recommended Next Phase

Open a follow-up provider/search allocation execution phase only if it is
separately licensed to choose a bounded existing provider role or search-depth
profile. That phase should continue to consume
`ControllerRecoveryDecision == request_provider_search_review` and should not
add providers, swap providers, change query strategy, or perform live
validation without a separate live budget.
