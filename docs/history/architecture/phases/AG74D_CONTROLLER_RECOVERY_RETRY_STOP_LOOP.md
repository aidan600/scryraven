Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG74D_CONTROLLER_RECOVERY_RETRY_STOP_LOOP).

# AG-74D Controller Recovery Retry/Stop Loop

Date: 2026-05-28

## Scope

Architecture Groove / Prove Mode. AG-74D is limited to the
Controller-owned recovery retry/stop loop for official/current/canonical source
obligations.

This phase adds a pure Controller recovery decision table, exposes the decision
through official/canonical visibility diagnostics, and makes the existing
source-class recovery executor gate subordinate to that Controller decision.

No provider/search implementation, provider routing, provider selection,
provider depth/search-depth, provider escalation, provider swap, new provider,
query strategy, source constraint, retrieval ranking/filtering,
source-class/currentness classifier, candidate-fit, prompt, Author, citation
formatting, final-answer, follow-up, Scrutineer, Economist, direct IRS
hardcoding, live validation, raw/private data, DB/cache/log/full-trace,
output-packet, or destructive git surface was opened.

## AG-74D-V Prerequisite Verification

Local `main` contained AG-74D-V through:

```text
1d5a56a Merge pull request #16 from aidan600/codex/ag74d-v-recovery-lane-success-vocabulary-retirement
187080b Retire recovery-lane success vocabulary
```

Required artifacts were present before implementation:

- `docs/history/architecture/phases/AG74D_V_RECOVERY_LANE_SUCCESS_VOCABULARY_RETIREMENT.md`
- `docs/history/architecture/phases/AG74C_LEDGER_GATED_VISIBILITY_CONSUMER_SUBORDINATION.md`
- `docs/history/architecture/phases/AG74B_CONTROLLER_AUTHORITY_DISPOSITION.md`
- `docs/history/architecture/phases/AG74A_CONTROLLER_EVIDENCE_LEDGER_CONTRACT.md`
- `core/controller_evidence_ledger.py`
- `core/official_canonical_recovery_visibility_export.py`
- `tests/test_ag74d_v_recovery_lane_success_vocabulary_retirement.py`
- `tests/test_ag74c_ledger_gated_visibility_consumer_subordination.py`
- `tests/test_ag74b_controller_authority_disposition.py`
- `tests/test_ag74a_controller_evidence_ledger.py`

Verified repo facts:

- `ControllerEvidenceLedger.final_evidence_citation_custody` exists.
- Misleading recovery-lane terminal success vocabulary was retired in AG-74D-V.
- `official_canonical_recovery_visibility_export` exposes ledger custody status.
- Recovery-lane observations remain explicitly non-custody observations.

## Targeted Old Recovery Decision Path

The targeted seam is the narrow official/current source-class recovery executor
gate:

```text
Controller-approved source_class_recovery action
  -> source_class_recovery_executor._source_class_recovery_action(...)
  -> execute_source_class_recovery_action(...)
  -> existing provider/search runner
```

Before AG-74D, the executor gate verified that a `source_class_recovery` action
was active and controller-approved, then executed the already-approved action.
It did not consult a Controller-owned final retry/stop decision table based on
ledger custody and source-obligation state.

AG-74D does not rewrite the orchestrator or recovery runner. It inserts a pure
decision table before the mechanical executor spends the existing action.

## Controller Recovery Decision Table

The table lives in `core/controller_recovery_decision.py`:

```text
build_controller_recovery_decision(runtime_trace)
```

It returns exactly one of:

- `stop_sufficient`
- `stop_insufficient`
- `stop_legacy_custody_gap`
- `retry_recovery`
- `request_provider_search_review`
- `continue_downstream`
- `stop_for_architecture_decision`

The decision record includes:

- `schema_version`
- `decision_owner: ControllerEvidenceLedger`
- `requirement_id`
- `required_source_class`
- `ledger_custody_status`
- `source_obligation_status`
- `candidate_state_summary`
- `recovery_budget_state`
- `decision`
- `decision_reason`
- `allowed_executor_action`
- `provider_search_review_requested`
- `retry_allowed`
- `retry_reason`
- `stop_reason`
- `architecture_stop_reason`
- `legacy_gap_types`
- `old_path_subordinated`
- protected-surface parity flags

## State-To-Decision Mapping

Ledger/source-obligation mappings:

- `controller_complete` final evidence/citation custody with
  `custody_complete: true` -> `continue_downstream`, no retry.
- satisfied official/current obligation with no unmet class ->
  `stop_sufficient`, no retry.
- `legacy_gap_observed` or ledger legacy gap types ->
  `stop_legacy_custody_gap`, not success.
- `missing_controller_disposition` ->
  `stop_for_architecture_decision`, not aggregate success.
- no plausible official/current candidate acquired with retry budget available
  -> `retry_recovery`.
- no plausible official/current candidate acquired after retry budget is not
  available -> `request_provider_search_review`.
- candidate acquired but unreadable ->
  `stop_insufficient` with allowed action
  `record_readability_post_provider_issue`.
- candidate readable but misclassified ->
  `stop_insufficient` with allowed action `record_classification_issue`.
- candidate classified but fit/currentness rejected ->
  `stop_insufficient` with allowed action `record_fit_currentness_issue`.
- exhausted recovery budget with unmet official/current obligation ->
  `stop_insufficient`.
- selected/complete official/current evidence already exists ->
  `continue_downstream`, no retry.
- unknown or contradictory state ->
  `stop_for_architecture_decision`.

`request_provider_search_review` is only a Controller decision record. AG-74D
does not implement provider escalation, provider allocation, provider depth, or
provider routing changes.

## Mechanical Executor

`core/source_class_recovery_executor.py` remains the mechanical executor. It
still:

- validates that the existing `source_class_recovery` action has a Controller
  envelope;
- uses the existing action's queries, provider role, search depth, and domain
  constraints;
- calls the existing `process_search_queries` runner only when the Controller
  decision permits `retry_recovery`;
- records returned result counts and candidate-acquisition diagnostics.

The executor does not choose providers, routes, depth, query strategy,
classification, candidate fit, final citations, or final answer behavior.

## Observer / Export Surface

`core/official_canonical_recovery_visibility_export.py` remains observational.
It now includes:

- `controller_recovery_decision_trace`
- `controller_recovery_decision`
- `controller_recovery_decision_reason`
- `controller_recovery_retry_allowed`
- `controller_recovery_allowed_executor_action`
- `controller_recovery_provider_search_review_requested`
- `controller_recovery_old_path_subordinated`

`core/runtime_trace_projection_assembly.py` already refreshes the visibility
export after attaching `ControllerEvidenceLedger`, so AG-74D decisions observe
ledger-backed final custody state without changing final answer/citation
surfaces.

## Old Gate Handling

Old gate classification:

- `source_class_recovery_executor` active-action gate: subordinate to
  Controller recovery decision.
- existing `process_search_queries` runner: mechanical executor only.
- `official_canonical_recovery_visibility_export`: observer/export only.
- `pipeline_orchestrator.py` call site: still legacy plumbing and next
  deletion target, but not expanded in AG-74D.
- retrieval-stop telemetry and broad continuation gates: still legacy and next
  deletion targets outside this narrow phase.

No old code was deleted in AG-74D. The old executor gate is more deletable
because retry/stop/post-provider-review decisions now have a pure Controller
owner and tests prove the executor can be denied by that decision even when an
old active recovery action exists.

## Behavior Parity Evidence

AG-74D changes the narrow recovery executor admission behavior only when the
Controller recovery table says the existing recovery action must not be spent.
It does not change provider/search/query/depth/routing behavior, final
evidence selection, source ID assignment, Author input, citation formatting, or
final prose.

Focused proof:

- `test_ag74d_controller_complete_custody_stops_retry_and_continues_downstream`
- `test_ag74d_satisfied_obligation_without_unmet_class_is_stop_sufficient`
- `test_ag74d_legacy_gap_and_missing_disposition_are_not_success`
- `test_ag74d_no_candidate_retries_until_budget_then_requests_review`
- `test_ag74d_candidate_failure_layers_do_not_generic_provider_escalate`
- `test_ag74d_exhausted_budget_with_unmet_obligation_stops_insufficient`
- `test_ag74d_unknown_or_contradictory_state_stops_for_architecture`
- `test_ag74d_visibility_export_exposes_controller_recovery_decision`
- `test_ag74d_executor_gate_is_subordinate_to_controller_decision`
- `test_ag74d_static_guards_keep_provider_and_final_answer_surfaces_closed`

Retained parity tests:

- `test_ag74d_v_runtime_projection_preserves_final_answer_citation_surfaces`
- `test_ag74c_runtime_projection_refreshes_export_with_ledger_and_preserves_outputs`
- AG-68C source-class recovery dispatch tests.

## Protected Surfaces Kept Closed

No provider routing, provider selection, provider depth/search-depth, provider
escalation implementation, provider swap, new provider, Linkup, query strategy,
source constraint, retrieval ranking/filtering, source-class/currentness
classifier, candidate-fit semantics, prompt, Author, citation formatting,
final-answer, follow-up, Scrutineer, Economist, direct IRS hardcoding, live
provider/model/search call, raw provider payload, raw prompt, secret, DB row,
cache, private log, full trace, ignored local packet, destructive git, merge,
rebase, reset, force-push, branch deletion, or `main` alteration was opened.

## Demolition Ledger

Old recovery decision path targeted:

`source_class_recovery_executor` active source-class recovery action gate.

New Controller-owned recovery decision owner:

`core/controller_recovery_decision.py`, owned by
`ControllerEvidenceLedger` state and source-obligation facts.

Executor/helper that remains mechanical:

`core/source_class_recovery_executor.py`.

Observer/export surface:

`core/official_canonical_recovery_visibility_export.py` and existing runtime
projection assembly refresh.

Old code deleted, bypassed, or subordinated:

- deleted: none;
- bypassed: none;
- subordinated: executor active-action gate now consults
  `ControllerRecoveryDecision` before spending the action.

Tests proving Controller decision ownership:

- `test_ag74d_controller_complete_custody_stops_retry_and_continues_downstream`
- `test_ag74d_legacy_gap_and_missing_disposition_are_not_success`
- `test_ag74d_executor_gate_is_subordinate_to_controller_decision`

Tests proving behavior parity or intended narrow behavior change:

- `test_ag74d_static_guards_keep_provider_and_final_answer_surfaces_closed`
- `test_ag74d_v_runtime_projection_preserves_final_answer_citation_surfaces`
- AG-68C source-class recovery dispatch tests.

Remaining old consumer/path to delete next:

- `pipeline_orchestrator.py` local lifecycle assembly around source-class
  recovery dispatch;
- broad retrieval-stop active/shadow telemetry gates;
- legacy recovery-lane observation fields that still require downstream
  diagnostic fixture compatibility.

Net complexity impact:

Small positive complexity trade. AG-74D adds one pure decision table and one
executor consult. It moves retry/stop decisions out of implicit local action
availability and into a testable Controller record, making the executor gate
more deletable.

If no code was deleted, why the old path is still more deletable:

The old action gate is now a mechanical enforcement point. Its decision inputs
and outputs are represented by `ControllerRecoveryDecision`, so a later phase
can delete or simplify the local gate without rediscovering retry/stop
semantics in `pipeline_orchestrator.py`.

## Recommended Next Phase

AG-75A should handle provider/search allocation review implementation if the
Controller records `request_provider_search_review`. That phase should remain
separate from AG-74D and should explicitly license any provider/search changes.
