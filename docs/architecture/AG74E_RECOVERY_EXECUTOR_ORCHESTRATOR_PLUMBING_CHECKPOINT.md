# AG-74E Recovery Executor / Orchestrator Plumbing Checkpoint

Date: 2026-05-28

## Scope

AG-74E is a recovery executor / orchestrator plumbing retirement checkpoint.
It proves that official/current recovery spend, retry, stop, continue, and
provider-search-review decisions are owned by `ControllerRecoveryDecision`, and
it subordinates one remaining executor parameter gate.

No provider/search allocation implementation was opened. No provider routing,
provider selection, provider depth/search-depth, provider escalation, provider
swap, new provider, Linkup, query strategy, source constraint, retrieval
ranking/filtering, source-class/currentness classifier, candidate-fit, prompt,
Author, citation formatting, final-answer, follow-up, Scrutineer, Economist,
direct IRS hardcoding, live validation, raw/private data, or output packet
surface was opened.

## AG-74D Prerequisite Verification

Local `main` contained AG-74D through:

```text
adb79b3 Merge pull request #17 from aidan600/codex/ag74d-controller-recovery-retry-stop-loop
5bbef0e Keep AG-74D executor trace contract-compatible
92773f4 Add AG-74D controller recovery decision loop
```

Required AG-74A through AG-74D artifacts were present before implementation:

- `docs/architecture/AG74A_CONTROLLER_EVIDENCE_LEDGER_CONTRACT.md`
- `docs/architecture/AG74B_CONTROLLER_AUTHORITY_DISPOSITION.md`
- `docs/architecture/AG74C_LEDGER_GATED_VISIBILITY_CONSUMER_SUBORDINATION.md`
- `docs/architecture/AG74D_V_RECOVERY_LANE_SUCCESS_VOCABULARY_RETIREMENT.md`
- `docs/architecture/AG74D_CONTROLLER_RECOVERY_RETRY_STOP_LOOP.md`
- `core/controller_recovery_decision.py`
- `core/source_class_recovery_executor.py`
- `tests/test_ag74d_controller_recovery_retry_stop_loop.py`

The worktree was clean on `main`; no local branch cleanup was pending. The
phase branch was created from `adb79b3`.

Verified AG-74D repo facts:

- `core/controller_recovery_decision.py` defines
  `ControllerRecoveryDecision`.
- `core/source_class_recovery_executor.py` consults
  `build_controller_recovery_decision(...)` and
  `controller_recovery_executor_allows_attempt(...)` before spending an
  existing action.
- `core/official_canonical_recovery_visibility_export.py` exposes canonical
  Controller recovery decision fields.
- The AG-74A, AG-74B, AG-74C, AG-74D-V, and AG-74D docs remain present.

## Gate Inventory

Inspected recovery spend/retry/stop/continue/escalation surfaces:

- `core/controller_recovery_decision.py`
- `core/source_class_recovery_executor.py`
- `core/source_class_recovery_lifecycle.py`
- `core/source_class_recovery_controller.py`
- `core/pipeline_orchestrator.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/runtime_trace_projection_assembly.py`
- `core/official_canonical_recovery_candidate_acquisition.py`
- `core/recovered_evidence_visibility.py`
- `core/authority_lifecycle_candidate_visibility.py`
- `core/authority_lifecycle_execution.py`
- `core/answer_contract_runtime_handoff.py`
- source-class recovery dispatch/execution tests
- official/canonical recovery visibility tests
- runtime trace projection and controller diagnostics trace contract tests

Classified gates:

- `ControllerRecoveryDecision`: official/current retry, stop, continue, and
  `request_provider_search_review` owner.
- `source_class_recovery_executor` active-action gate: mechanical action lookup
  and envelope validation.
- `source_class_recovery_executor` parameter gate: formerly returned before
  the AG-74D decision when queries or search depth were missing; now
  subordinate to the Controller recovery decision trace.
- `pipeline_orchestrator.py` source-class dispatch branch: legacy compatibility
  plumbing that calls the executor only for the authorized spine action.
- `official_canonical_recovery_visibility_export`: observer/export only; it
  builds and publishes the Controller decision fields.
- retrieval-stop active/shadow telemetry: outside AG-74E recovery executor
  spend authority; retained as existing terminal/continuation controller
  telemetry.
- provider/search review surface: decision value only, not implementation.

## Decision Ownership

No covered official/current recovery path can silently spend, retry, stop,
continue, or request provider/search review without `ControllerRecoveryDecision`.

The only remaining narrow suppression gate found in AG-74E was the executor
parameter check for missing recovery queries or missing search depth. That gate
is now reached after `build_controller_recovery_decision(...)` updates the
neutral executor trace fields. If the Controller decision permits retry but the
approved action is unexecutable, the executor records:

```text
active_source_class_recovery_skip_reason:
  controller_recovery_decision_allowed_but_executor_action_unexecutable
active_source_class_recovery_blockers:
  missing_executor_queries
  missing_executor_search_depth
```

This is mechanical parameter validation. It is not a retry, stop, continue,
success, escalation, provider allocation, or provider-search implementation
decision.

## Old Path Subordinated

Old targeted path:

```text
source_class_recovery_executor:
  if not queries or search_depth is None:
      return attempted=False
```

New ownership:

```text
ControllerRecoveryDecision
  -> neutral executor trace fields
  -> controller_recovery_executor_allows_attempt(...)
  -> mechanical executor parameter validation
  -> process_search_queries only if executable
```

`ControllerRecoveryDecision.old_path_subordinated` now includes:

- `source_class_recovery_executor_action_gate`
- `source_class_recovery_executor_parameter_gate`
- `official_canonical_recovery_visibility_export`

## Mechanical Executor Code

Mechanical executor code remains in `core/source_class_recovery_executor.py`.
It still:

- locates an already Controller-approved `source_class_recovery` action;
- validates the Controller action envelope;
- uses the existing action's queries, provider role, search depth, and domain
  constraints;
- calls the injected `process_search_queries` runner only after
  `ControllerRecoveryDecision` allows the attempt and parameters are executable;
- records result counts, candidate acquisition diagnostics, and lifecycle
  execution observations.

It does not choose providers, route providers, change search depth, alter
queries, classify sources, rank/filter retrieval results, decide candidate fit,
alter prompts, choose citations, or affect final-answer behavior.

## Observer / Export Surface

The official/canonical visibility export remains the canonical observer. It
continues to expose:

- `controller_recovery_decision_trace`
- `controller_recovery_decision`
- `controller_recovery_decision_reason`
- `controller_recovery_retry_allowed`
- `controller_recovery_allowed_executor_action`
- `controller_recovery_provider_search_review_requested`
- `controller_recovery_old_path_subordinated`

Executor runtime traces keep AG-74D-compatible neutral keys such as
`recovery_decision`, `recovery_retry_allowed`, and `recovery_decision_trace`.
AG-74E did not add new top-level `controller_*` execution-trace payload keys.

## AG-75A Safety

AG-75A is safe to open after AG-74E, with the following boundary:

- `ControllerRecoveryDecision` is the owner of covered official/current
  recovery retry/stop/continue/provider-search-review decisions.
- `request_provider_search_review` remains a decision value only.
- no local/orchestrator helper independently triggers provider/search
  allocation or escalation.
- no covered executor gate can spend or silently suppress the existing recovery
  action before the Controller recovery decision is recorded.
- provider/search implementation remains closed and untouched.

Remaining legacy plumbing to delete next:

- the `pipeline_orchestrator.py` source-class recovery dispatch branch and
  associated compatibility lifecycle projections, once a smaller runner can
  execute Controller-approved actions directly.

No exact old gate blocks AG-75A.

## Tests

AG-74E added:

- `test_ag74e_executor_parameter_gate_is_subordinate_to_controller_decision`
- `test_ag74e_provider_search_review_is_decision_only_not_executor_allocation`
- `test_ag74e_static_executor_consults_controller_before_parameter_skip`
- `test_ag74e_static_guard_keeps_closed_surfaces_unchanged`

Relevant retained tests include:

- `tests/test_ag74d_controller_recovery_retry_stop_loop.py`
- `tests/test_ag74d_v_recovery_lane_success_vocabulary_retirement.py`
- `tests/test_ag74c_ledger_gated_visibility_consumer_subordination.py`
- `tests/test_source_class_recovery_executor.py`
- `tests/test_official_canonical_recovery_visibility_export_ag50c.py`
- `tests/test_runtime_trace_projection_assembly_ag46c.py`
- `tests/test_controller_diagnostics_trace_contract.py`

## Behavior Parity Evidence

AG-74E changes only a malformed-action executor checkpoint: the same
non-execution result is preserved, but the Controller recovery decision is now
visible before the mechanical parameter block.

Provider/search/query/depth/routing behavior is unchanged:

- no provider lists were edited;
- no provider routing or selection code was added;
- no search-depth policy was changed;
- no query generation or source constraints were changed;
- `process_search_queries` remains injected and is not called in the malformed
  parameter fixture.

Final answer/citation behavior is unchanged:

- no final evidence selection, source ID assignment, Author input, citation
  formatting, or final prose code was edited;
- retained AG-74D-V projection tests continue to cover final answer/citation
  surface parity.

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

1. Old recovery/executor/orchestrator path targeted:
   `source_class_recovery_executor` parameter gate for missing queries or
   missing search depth.
2. New Controller-owned recovery decision owner:
   `ControllerRecoveryDecision`.
3. Executor/helper that remains mechanical:
   `execute_source_class_recovery_action`.
4. Observer/export surface:
   `official_canonical_recovery_visibility_export`.
5. Old code deleted, bypassed, or subordinated:
   the parameter gate was subordinated under the Controller recovery decision
   trace and allow/deny check.
6. Tests proving Controller decision ownership:
   `test_ag74e_executor_parameter_gate_is_subordinate_to_controller_decision`,
   `test_ag74e_static_executor_consults_controller_before_parameter_skip`, plus
   AG-74D retry/stop tests.
7. Tests proving behavior parity or intended narrow behavior change:
   `test_source_class_recovery_executor_runs_eligible_action_equivalently`,
   `test_ag74d_v_runtime_projection_preserves_final_answer_citation_surfaces`,
   and AG-74E protected-surface static guards.
8. Whether AG-75A is safe to open:
   yes.
9. If not safe, exact old gate remaining:
   not applicable.
10. Remaining old consumer/path to delete next:
    `pipeline_orchestrator.py` recovery dispatch compatibility plumbing.
11. Net complexity impact:
    lower decision ambiguity; one fewer silent pre-decision executor return.
12. If no code was deleted, why the old path is more deletable:
    no deletion was needed because the parameter gate is still valid mechanical
    validation; after AG-74E it is ordered under the Controller decision and
    directly named in tests/docs, making future extraction safer.

## Recommended Next Phase

Open AG-75A if its scope remains provider/search-allocation design or
implementation and keeps this AG-74E boundary intact. The next demolition-only
phase, if chosen before AG-75A, should extract the small recovery runner out of
`pipeline_orchestrator.py` so the orchestrator becomes pure compatibility
handoff rather than the dispatch owner.
