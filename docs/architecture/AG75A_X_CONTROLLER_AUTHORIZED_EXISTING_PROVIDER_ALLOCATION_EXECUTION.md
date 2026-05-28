# AG-75A-X Controller-Authorized Existing-Provider Allocation Execution

Date: 2026-05-28

## Scope

AG-75A-X implements a narrow Controller-authorized existing-provider allocation
execution path for ScryRaven. It is not generic provider escalation, not IRS
repair, not live validation, not provider integration, not a provider swap, not
provider-depth policy repair, not query strategy repair, and not final-answer,
Author, citation, or prompt behavior work.

## AG-75A Prerequisite Verification

Current `main` contained AG-75A / PR #20 before implementation:

```text
11884c9 Merge pull request #20 from aidan600/codex/ag75a-controller-provider-search-allocation-gate
01b24e4 Add AG-75A controller provider search allocation gate
```

Required AG-75A artifacts were present:

- `docs/architecture/AG75A_CONTROLLER_PROVIDER_SEARCH_ALLOCATION_GATE.md`
- `core/controller_provider_search_allocation.py`
- `core/source_class_recovery_runner.py`
- `core/controller_recovery_decision.py`
- `tests/test_ag75a_controller_provider_search_allocation_gate.py`

The AG-75A doc states that the allocation path was record-only and that actual
bounded provider/depth execution required a separately licensed follow-up.
`core/pipeline_orchestrator.py` remained a handoff that constructs
`SourceClassRecoveryRunnerContext(...)` and calls
`run_source_class_recovery_dispatch(...)`; it did not own provider/search
allocation logic.

## Controller Authorization

The exact Controller decision authorizing AG-75A-X execution is:

```text
ControllerRecoveryDecision.decision == "request_provider_search_review"
```

The helper also requires:

- `provider_search_review_requested is True`
- `allowed_executor_action == "record_provider_search_review_request"`
- `decision_reason == "no_candidate_acquired_provider_search_review_needed"` or
  `candidate_state_summary == "no_plausible_official_current_candidate_acquired"`

This keeps execution acquisition-failure-specific. Local helper state,
orchestrator state, generic no-answer states, citation/final-answer issues,
readability failures, classification failures, candidate-fit/currentness
rejections, context exposure failures, and Author/citation-surface failures do
not authorize allocation execution.

## Bounded Profile

Implemented profile:

```text
bounded_existing_source_class_recovery_profile_v1
```

The profile uses only the existing injected `process_search_queries` boundary,
the existing `search_providers` supplied to the recovery runner context,
existing source-class recovery action or lifecycle queries, existing source-class
recovery action or lifecycle search depth, and provider role
`source_class_recovery`.

The profile does not add providers, swap providers, add Linkup escalation, set
deep or unlimited depth, change global provider routing, change query strategy,
change source constraints, alter ranking/filtering, alter classifiers, alter
candidate fit, or call provider APIs directly.

## Mechanical Execution Owner

Code that executes the profile mechanically:

- `core/controller_provider_search_allocation.py`
  - `ProviderSearchAllocationExecutionContext`
  - `execute_provider_search_allocation_if_controller_authorized(...)`
  - `record_provider_search_allocation_if_controller_authorized(...)`
- `core/source_class_recovery_runner.py`
  - `_provider_search_allocation_execution_context(...)`
  - `run_source_class_recovery_dispatch(...)`

The runner extracts existing action/lifecycle query, provider-role, and
search-depth values, then passes them to the allocation helper. The helper calls
only the already-injected `process_search_queries` callable. It uses copied URL
and image sets plus local provider diagnostics, records sanitized counts, and
does not append returned passages into `all_passages` or retrieval pass records.

## Trace And Export

AG-75A-X preserves the AG-75A record at:

```text
provider_search_allocation_trace.ProviderSearchAllocation
```

The bounded execution result is nested under the same neutral trace envelope:

```text
provider_search_allocation_trace.provider_search_allocation_execution_trace
provider_search_allocation_trace.ProviderSearchAllocationExecution
```

The official/canonical visibility export projects the sanitized execution result
at:

```text
provider_search_allocation_execution_trace
```

Sanitized fields include authorization, profile name, execution mode,
attempt/executed booleans, unexecutable reason, provider role, search depth,
query count, result count, new URL count, policy-preservation flags, closed
surface flags, final-answer/citation parity flags, and
`raw_payload_exposed: false`.

No raw provider payloads, raw prompts, secrets, DB rows, private logs, caches,
full traces, local output packets, or generated artifacts are exported.

## What Prevents Generic Escalation

Execution remains impossible unless
`build_provider_search_allocation_record(...)` succeeds from a
`ControllerRecoveryDecision`. A matching spine value, local lifecycle fields,
active action record, provider helper, or orchestrator handoff cannot execute
allocation alone.

Unexecutable allocation is recorded when required existing inputs are missing:
process-search runner, source-class provider role, existing queries, existing
search depth, or existing search providers.

## What Remains Record-Only

The AG-75A allocation record remains visible and subordinate. It still records
the Controller-approved provider/search review action. When execution inputs are
missing, AG-75A-X records a sanitized unexecutable execution result rather than
inventing queries, changing depth, selecting providers, or escalating.

## Old Path Subordinated

The old AG-75A record-only helper is upgraded, not removed. It now owns the
record plus optional bounded execution trace. `pipeline_orchestrator.py` remains
only the context handoff and is still the next demolition target.

## Non-Execution States

Tests cover non-execution for:

- absent `ControllerRecoveryDecision`
- wrong `allowed_executor_action`
- decision values other than `request_provider_search_review`
- controller-complete final evidence/citation custody
- `continue_downstream`
- `stop_sufficient`
- `stop_legacy_custody_gap`
- `stop_for_architecture_decision` / missing controller disposition
- candidate acquired but unreadable
- candidate readable but misclassified
- candidate classified but fit/currentness rejected
- exhausted budget with `stop_insufficient`
- context exposure failure
- Analyst/Author/citation-surface failure
- final-answer/citation behavior issue
- local/orchestrator helper state without Controller authorization

## Behavior Preservation

Ordinary source-class recovery runs still use the existing executor and preserve
provider/query/depth behavior. The AG-75A-X path does not change global provider
selection, search depth, provider routing, query generation, source constraints,
ranking/filtering, source classification, candidate fit, final answer, Author,
or citation formatting.

Final answer and citation behavior remain unchanged: the allocation helper and
runner do not import or call final-answer builders, and bounded allocation
execution does not append returned passages into final-answer/citation inputs.

## Protected Surfaces Kept Closed

Closed surfaces kept closed:

- new providers and provider swaps
- broad provider routing policy
- broad provider-depth policy
- uncontrolled Linkup escalation
- deep/unlimited default search
- query strategy and source constraints
- retrieval ranking/filtering
- source-class/currentness classifier semantics
- candidate-fit semantics
- prompt, Author, citation formatting, final-answer, follow-up, Scrutineer, and
  Economist behavior
- direct IRS hardcoding or source-specific resolver implementation
- live ScryRaven/proplex/scryraven provider/model/search calls
- secrets, raw provider payloads, raw prompts, DB rows, private logs, caches,
  full traces, ignored local output packets, and unrelated artifacts

## Demolition Ledger

1. Old record-only path targeted:
   `record_provider_search_allocation_if_controller_authorized(...)`.
2. New bounded execution owner and mechanical runner/helper:
   `execute_provider_search_allocation_if_controller_authorized(...)` behind
   `run_source_class_recovery_dispatch(...)`.
3. Controller authorization source:
   `ControllerRecoveryDecision.decision == "request_provider_search_review"`
   with `allowed_executor_action == "record_provider_search_review_request"`.
4. Observer/export surface:
   neutral `provider_search_allocation_trace` plus sanitized
   `provider_search_allocation_execution_trace` export.
5. Old code deleted, upgraded, bypassed, or subordinated:
   AG-75A record-only helper upgraded; orchestrator remains subordinated
   handoff/plumbing only.
6. Tests proving Controller authorization is required:
   AG-75A-X allocation execution, absent-decision, wrong-action, and
   non-acquisition matrix tests.
7. Tests proving non-acquisition failures do not execute allocation:
   `test_ag75a_non_acquisition_failure_states_do_not_allocate`.
8. Tests proving provider/search execution stayed within license:
   bounded execution assertions and static guards for no provider imports,
   provider swaps, broad routing, new providers, unbounded depth, prompts, raw
   payload exposure, or final-answer calls.
9. Tests proving ordinary runs preserve existing provider/query/depth behavior:
   AG-74F runner parity tests.
10. Tests proving final answer/citation behavior parity:
    static closed-surface assertions in the AG-75A-X test file.
11. Remaining old code/path to delete next:
    `pipeline_orchestrator.py` construction of
    `SourceClassRecoveryRunnerContext(...)`.
12. Net complexity impact:
    one small execution context, one bounded helper, one runner extraction
    helper, and sanitized export projection; lower ambiguity for
    `request_provider_search_review` without reopening provider policy.

## Recommended Next Phase

Delete or shrink the remaining orchestrator handoff into the recovery runner:

```text
pipeline_orchestrator.py
  -> SourceClassRecoveryRunnerContext(...)
  -> run_source_class_recovery_dispatch(...)
```

Any future phase that wants allocation results to feed candidate selection,
citations, or final answers needs a separate license because AG-75A-X records
bounded execution observability only and keeps final-answer/citation behavior
closed.
