Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG94H_D_RECOVERY_DISPATCH_AUTHORIZATION_REPAIR).

# AG-94H-D Recovery Dispatch Authorization Repair

Status: implemented as a focused offline behavior repair.

Validation boundary: repo-visible code, repo-tracked docs, and synthetic
fixtures only. No live ScryRaven/proplex provider, model, search, retrieval,
secret, `.env`, DB row, raw provider payload, raw prompt, private log, cache,
full raw trace, local output packet, or private artifact access was used.

> Status note, AG-95E: This document records historical
> Controller/ControllerLoopSpine-era behavior. For current source-class recovery
> dispatch, use AG-95C/AG-95D/AG-95E:
> `SourceClassRecoveryRunner` dispatches from canonical
> `authority_lifecycle.recovery_action`; `authorized_spine_action`,
> ControllerLoopSpine, and ControllerRecoveryDecision are
> diagnostic/compatibility surfaces for source-class dispatch, not runner
> authority.

## Executive Verdict

AG-94H-D repairs the dispatch authorization gap found by AG-94H-C. An
authority-lifecycle-approved official/current source-class recovery can now
authorize `RECOVER_MISSING_SOURCE_CLASS` through the controller loop spine even
when the ordinary checkpoint packet is empty or unavailable.

The repair preserves custody safety. `legacy_gap_observed` still means final
evidence/citation aggregates cannot prove final custody success. It no longer
prevents one bounded existing recovery attempt when lifecycle recovery is
approved, the official/current obligation is unmet, queries exist, budget is
available, candidate acquisition has not been attempted, and no hard blocker
owns the path.

## AG-94H-C Audit Finding Being Repaired

AG-94H-C found that
`source_class_recovery_executor_dispatch_not_authorized` is written by
`core/source_class_recovery_runner.py` when provider-search allocation does not
run and the runner receives no
`authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS`.

The missing upstream authorization was in `core/controller_loop_spine.py`.
Lifecycle recovery could be eligible and authority-approved while the ordinary
checkpoint packet was empty, causing the spine to return no authorized dispatch.

AG-94H-C also found that `ControllerRecoveryDecision` treated
`STOP_LEGACY_CUSTODY_GAP` as an execution block before checking whether an
approved official/current recovery attempt was still available.

## Exact Behavior Change

`core/controller_loop_spine.py` now has a narrow checkpointless dispatch path
for authority-lifecycle-approved source-class recovery. It requires:

- authority lifecycle control of recovery;
- required recovery allowed;
- approved authority recovery action;
- approved source-class action envelope;
- lifecycle eligibility;
- supported official/current missing source class;
- unmet source obligation;
- existing source-class recovery queries;
- available recovery slot;
- no prior executed source-class/candidate acquisition attempt;
- no authority lifecycle execution blocker;
- no non-lifecycle blocker such as conflict, provider policy, search-depth, or
  hard-cap ownership.

`active_source_class_recovery_attempt_count` is not treated as proof that
execution already happened when `recovery_slot_available=true`,
`active_source_class_recovery_execution_attempted=false`,
`active_source_class_recovery_used=false`,
`authority_lifecycle_execution_attempted=false`,
`candidate_return_status=not_attempted`, and `acquisition_attempted=false`.
True prior attempts, explicit `recovery_slot_available=false`,
`already_attempted` blockers, execution-attempted flags, and candidate
acquisition-attempted flags still block dispatch/retry.

When those predicates hold, the spine records
`spine_authorization_source=authority_lifecycle_required_recovery` and returns
`RECOVER_MISSING_SOURCE_CLASS`.

`core/controller_recovery_decision.py` now subordinates
`legacy_gap_observed` only for the same bounded recovery shape. The decision
payload preserves:

- `legacy_gap_observed=true`;
- `legacy_gap_subordinated_for_recovery_attempt=true`;
- `legacy_gap_final_success_block_preserved=true`;
- `controller_recovery_retry_reason=official_current_obligation_unmet_retry_available`.

## Why This Is Not A Provider/Search/Query Repair

No provider routing, provider order, provider selection, search depth, query
generation, query text, source ranking, source filtering, source classification,
or candidate-fit behavior changed.

The positive fixture uses a fake local callable to prove that the existing
bounded source-class recovery executor is reached exactly once. It does not run
live search and does not add a provider lane.

## Why Legacy Custody Gap Still Blocks Final Success

The repair does not reinterpret legacy aggregate final evidence/citation counts
as ControllerEvidenceLedger or FinalAnswerPacket custody. When legacy custody
gap is present, final success remains blocked until selected authority evidence
custody is proved by the canonical custody path.

The only changed meaning is execution priority: a legacy final-custody gap no
longer prevents a still-unused, lifecycle-approved, official/current recovery
attempt that may acquire the missing custody evidence.

## How Spine Authorization Now Reaches The Runner

The controller loop spine now produces `authorized_dispatch` and
`executed_action_name` as `recover_missing_source_class` for the approved
checkpointless lifecycle shape. The runner already consumes
`authorized_spine_action`; no provider/search behavior was moved into the spine.

The source-class recovery runner still blocks when `authorized_spine_action` is
absent, preserving the existing dispatch contract.

## How ControllerRecoveryDecision Now Permits One Bounded Recovery Attempt

`ControllerRecoveryDecision` now checks whether the legacy gap can be
subordinated for a bounded recovery attempt. That predicate requires the unmet
official/current obligation, available budget, supported missing classes,
approved action envelope, lifecycle approval, existing recovery queries,
not-attempted candidate acquisition, no prior executed recovery attempt, and no
hard blocker.

If the predicate is false, `STOP_LEGACY_CUSTODY_GAP` remains the decision.

## Candidate-State Summary Repair

`_candidate_state_summary()` no longer returns
`selected_complete_official_current_evidence_exists` from legacy final aggregate
counts when all of these are true:

- source obligation is unmet;
- candidate acquisition was not attempted;
- ledger custody is `legacy_gap_observed` or legacy gap types are present.

Those counts remain observable diagnostics. They are not treated as selected
candidate custody in the retry/stop decision.

## Files/Functions Changed

- `core/controller_loop_spine.py`
  - `_build_source_class_checkpoint_gate_trace()`
  - `_authority_lifecycle_approved_checkpointless_source_class_dispatch()`
- `core/controller_recovery_decision.py`
  - `build_controller_recovery_decision()`
  - `_decide()`
  - `_candidate_state_summary()`
  - `_legacy_gap_subordinated_for_bounded_recovery_attempt()`
- `core/official_canonical_recovery_visibility_export.py`
  - `_controller_decision_visibility_input()`
- `tests/test_ag94h_c_recovery_executor_dispatch_authorization_audit.py`
  - converted AG-94H-C audit assertions into AG-94H-D behavior-repair tests.

## Protected/Closed Surfaces Kept Closed

Kept closed:

- live provider/model/search/retrieval calls;
- secrets, `.env`, API keys, DB rows, raw provider payloads, raw prompts,
  private logs, caches, full raw traces, local output packets, private
  artifacts;
- provider swap, provider integration, provider order, routing, selection,
  search depth, and search budget changes;
- query generation or query text changes;
- ranking/filtering/source-classification overhaul;
- Author prose, prompt, final-answer, and citation behavior;
- package, CLI, env, database, and session renames;
- broad `core/pipeline_orchestrator.py` rewrite.

`core/pipeline_orchestrator.py` line delta: `0`.

## Tests/Checks Run

Passed locally:

- `py -m pytest -q tests/test_ag94h_c_recovery_executor_dispatch_authorization_audit.py`
  - `16 passed`
- `py -m pytest -q tests/test_ag74d_controller_recovery_retry_stop_loop.py`
  - `10 passed`
- `py -m pytest -q tests/test_ag74f_recovery_runner_extraction.py`
  - `5 passed`
- `py -m pytest -q tests/test_ag75a_controller_provider_search_allocation_gate.py`
  - `8 passed`
- `py -m pytest -q tests/test_controller_loop_spine.py`
  - `42 passed`
- `py -m pytest -q tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py`
  - `12 passed`
- `py -m pytest -q tests/test_ag94b_cli_official_current_recovery_trace_custody.py`
  - `6 passed`
- `py -m pytest -q tests/test_authority_lifecycle_execution_ag69c.py`
  - `8 passed`

No live calls were run.

## Recommended Next Validation

Run exactly one live rerun of `food_regulatory_non_us`.

Success signal:

- `source_class_recovery_eligible=true`;
- authorized spine dispatch reaches `RECOVER_MISSING_SOURCE_CLASS`;
- `source_class_recovery_execution_attempted=true` or the authority lifecycle
  executor entrypoint is reached;
- `candidate_acquisition_considered` moves past false if execution reaches
  candidate acquisition;
- if provider/candidate acquisition fails, classify that next blocker without
  running a rotating set.
