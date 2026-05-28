# AG-74F Recovery Runner Extraction

Date: 2026-05-28

## Scope

AG-74F is a recovery runner extraction / orchestrator dispatch compatibility
pullout. It moves the mechanical source-class recovery dispatch seam out of
`core/pipeline_orchestrator.py` and into a dedicated runner.

No provider/search allocation implementation was opened. No provider routing,
provider selection, provider depth/search-depth, provider escalation, provider
swap, new provider, Linkup, query strategy, source constraint, retrieval
ranking/filtering, source-class/currentness classifier, candidate-fit, prompt,
Author, citation formatting, final-answer, follow-up, Scrutineer, Economist,
direct IRS hardcoding, live validation, raw/private data, or output packet
surface was opened.

## AG-74E Prerequisite Verification

Current `main` contained AG-74E / PR #18 before implementation:

```text
429f11f Merge pull request #18 from aidan600/codex/ag74e-recovery-executor-orchestrator-checkpoint
6f6ba24 Add AG-74E recovery executor checkpoint
```

Required AG-74D/AG-74E artifacts were present:

- `docs/architecture/AG74E_RECOVERY_EXECUTOR_ORCHESTRATOR_PLUMBING_CHECKPOINT.md`
- `docs/architecture/AG74D_CONTROLLER_RECOVERY_RETRY_STOP_LOOP.md`
- `core/controller_recovery_decision.py`
- `core/source_class_recovery_executor.py`
- `tests/test_ag74e_recovery_executor_orchestrator_checkpoint.py`
- `tests/test_ag74d_controller_recovery_retry_stop_loop.py`

Verified repo facts:

- `core/source_class_recovery_executor.py` consults
  `build_controller_recovery_decision(...)` and
  `controller_recovery_executor_allows_attempt(...)` before spending an action
  or mechanically suppressing an existing action for missing parameters.
- The AG-74E checkpoint says AG-75A is safe under boundary.
- The AG-74E checkpoint names `pipeline_orchestrator.py` recovery dispatch
  compatibility plumbing as the next demolition-only target.

## Extraction

Moved from `core/pipeline_orchestrator.py` into
`core/source_class_recovery_runner.py`:

- the `authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS` dispatch check;
- the call into `execute_source_class_recovery_action(...)`;
- the mechanical non-dispatch projection through
  `record_source_class_recovery_execution_blocked_if_needed(...)`;
- source-class recovery execution result projection;
- URL/chunk counter delta calculation for the orchestrator.

`pipeline_orchestrator.py` now keeps only a compatibility handoff:

```text
run_source_class_recovery_dispatch(SourceClassRecoveryRunnerContext(...))
```

It still passes the same sanitized runtime facts and dependencies:
`process_search_queries`, passages, seen URLs, images, include/exclude domains,
current providers, Exa domain filter, entity hint, embedding helpers, provider
diagnostics, retrieval pass records, and the existing error type.

## Decision Ownership

`ControllerRecoveryDecision` remains the only owner of covered official/current
retry, stop, continue, and `request_provider_search_review` decisions.

`core/source_class_recovery_runner.py` is mechanical. It does not build a
Controller recovery decision and does not call
`controller_recovery_executor_allows_attempt(...)`. Those checks remain inside
`core/source_class_recovery_executor.py`, where AG-74D/AG-74E placed them.

`request_provider_search_review` remains a Controller decision output only.
The runner treats it as a non-source-class dispatch value and does not allocate
providers, change providers, change search depth, issue queries, or trigger
provider/search escalation.

## Behavior Parity Evidence

AG-74F preserves:

- action lookup semantics in the existing executor;
- Controller action envelope validation in the existing executor;
- provider role `source_class_recovery`;
- existing action queries;
- existing action search depth;
- include/exclude domain behavior;
- injected `process_search_queries` behavior;
- provider diagnostics and retrieval pass record behavior;
- result count and new URL count reporting;
- trace/export field names and compatibility surfaces.

The new runner returns only:

- `source_class_recovery_execution`;
- `total_urls_delta`;
- `total_chunks_delta`.

The orchestrator adds those deltas exactly where it previously updated
`total_urls_fetched` and `total_chunks_embedded`.

## Trace / Export Compatibility

AG-74F did not add new top-level `controller_*` execution-trace payload keys.
The executor still writes the AG-74D/AG-74E neutral fields such as:

- `recovery_decision`
- `recovery_retry_allowed`
- `recovery_decision_trace`

Observer/export surfaces remain unchanged:

- `core/runtime_trace_projection_assembly.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/recovered_evidence_visibility.py`
- `core/authority_lifecycle_candidate_visibility.py`

## Tests

AG-74F added:

- `tests/test_ag74f_recovery_runner_extraction.py`

Updated static and compatibility tests:

- `tests/test_ag74d_controller_recovery_retry_stop_loop.py`
- `tests/test_ag74e_recovery_executor_orchestrator_checkpoint.py`
- `tests/test_authority_lifecycle_execution_ag69c.py`
- `tests/test_authority_lifecycle_projection_control_ag69e.py`
- `tests/test_ordinary_continuation_ownership_ag44a.py`
- `tests/test_ordinary_continuation_seam_ag44b.py`
- `tests/test_source_class_recovery_dispatch_execution_ag68c.py`
- `tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py`
- `tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py`
- `tests/test_source_class_recovery_trace.py`

Evidence covered by tests:

- `pipeline_orchestrator.py` delegates source-class recovery dispatch to the
  runner.
- The runner calls the existing executor without changing provider/search/query
  depth/routing values.
- `ControllerRecoveryDecision` remains the retry/stop/continue/provider-review
  decision owner.
- `request_provider_search_review` remains decision-only.
- Provider/search allocation was not implemented.
- No new top-level `controller_*` trace keys are introduced by the runner path.
- Final answer/citation behavior is not touched by the runner.

## Provider / Search Allocation Closed

Provider/search allocation remains closed. AG-74F did not implement:

- provider routing;
- provider selection;
- provider escalation;
- provider swaps;
- new providers;
- Linkup behavior;
- provider depth/search-depth changes;
- query strategy changes;
- source constraint changes.

## What Became Easier To Delete

`pipeline_orchestrator.py` no longer owns the source-class recovery executor
dispatch branch. Future demolition can delete or replace the runner seam
without expanding orchestrator domain logic.

The remaining compatibility handoff to delete next is:

```text
pipeline_orchestrator.py
  -> SourceClassRecoveryRunnerContext(...)
  -> run_source_class_recovery_dispatch(...)
```

## AG-75A Safety

AG-75A remains safe to open under boundary. The provider/search allocation
phase can now start from a smaller surface because provider/search allocation
cannot be implemented by expanding the old `pipeline_orchestrator.py`
source-class recovery dispatch branch.

## Protected Surfaces Kept Closed

Closed surfaces kept closed:

- provider routing, provider selection, provider depth/search-depth, provider
  escalation, provider swaps, new providers, Linkup;
- query strategy and source constraints;
- retrieval ranking/filtering;
- source-class/currentness classifier semantics;
- candidate-fit semantics;
- prompt, Author, citation, final-answer, follow-up, Scrutineer, Economist;
- direct IRS hardcoding;
- live ScryRaven/proplex/scryraven provider/model/search calls;
- raw provider payloads, raw prompts, DB rows, private logs, caches, secrets,
  full traces, and ignored local output packets.

## Demolition Ledger

1. Old orchestrator dispatch plumbing targeted:
   `pipeline_orchestrator.py` source-class recovery executor dispatch branch.
2. New helper/runner location and responsibility:
   `core/source_class_recovery_runner.py`; mechanical dispatch, blocked-dispatch
   projection, and counter deltas.
3. New Controller-owned decision owner:
   unchanged, `ControllerRecoveryDecision`.
4. Executor/helper that remains mechanical:
   `execute_source_class_recovery_action(...)` and
   `run_source_class_recovery_dispatch(...)`.
5. Observer/export surface:
   existing runtime trace projection and official/canonical recovery visibility
   export surfaces.
6. Old code moved, deleted, bypassed, or subordinated:
   direct executor call, non-dispatch blocked projection, and count delta logic
   moved out of `pipeline_orchestrator.py`.
7. Tests proving behavior parity:
   AG-74F runner parity tests plus retained source-class recovery dispatch and
   trace tests.
8. Tests proving Controller decision ownership remains intact:
   AG-74D/AG-74E decision/executor tests and AG-74F static ownership test.
9. Tests proving provider/search allocation was not implemented:
   AG-74F provider-review decision-only and protected-surface tests.
10. Remaining old code/path to delete next:
    the `pipeline_orchestrator.py` runner handoff and context construction.
11. Whether AG-75A is now safe to open:
    yes, under the established no-orchestrator-expansion boundary.
12. Net complexity impact:
    lower orchestrator complexity; same executor behavior; smaller future
    deletion target.

## Recommended Next Phase

Open AG-75A only if it remains explicitly scoped to provider/search allocation
under the Controller-owned boundary. A smaller demolition follow-up may first
delete or further shrink the `pipeline_orchestrator.py` runner handoff.
