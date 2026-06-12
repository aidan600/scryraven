# AG-94H-C Recovery Executor Dispatch Authorization Audit

Status: audit complete.
Phase type: deep offline audit, fixture reproduction, no behavior fix.
Validation boundary: repo-visible code, repo-tracked docs, sanitized live signal
from the phase prompt, and synthetic fixtures only.

No live ScryRaven/proplex provider, model, search, or retrieval calls were run.
No secrets, `.env`, API keys, DB rows, raw provider payloads, raw prompts,
private logs, caches, full raw traces, local output packets, or private
artifacts were inspected.

## Executive Verdict

The exact owner of the observed
`source_class_recovery_executor_dispatch_not_authorized` skip reason is
`core/source_class_recovery_runner.py`. The runner writes that reason only when
it receives no `authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS` after
provider-search allocation declines to run.

The upstream owner of that missing authorization is the controller loop spine.
In the offline reproduction, source-class lifecycle is eligible, official/current
obligation is unmet, recovery queries exist, and the authority lifecycle says
recovery is approved, but the spine does not produce
`RECOVER_MISSING_SOURCE_CLASS` when the checkpoint packet does not approve or
allow the official/canonical fallback. The runner then records the exact live
skip reason.

Classification: **D. Spine authorization gap.**

There is a second important finding: `STOP_LEGACY_CUSTODY_GAP` currently is an
execution block in `ControllerRecoveryDecision`. That was safe when the decision
table was preventing aggregate final evidence/citation counts from being
mistaken for successful custody, but it is now overbroad after AG-94H-B because
the lifecycle can be eligible before candidate acquisition has even been
attempted. Legacy custody gaps should block final success, not a bounded
official/current recovery attempt when budget is available and no hard blocker
exists.

Recommended next decision: **focused behavior repair**.

## Sanitized Live Signal

Prompt query class: `food_regulatory_non_us`.

Prompt query:

```text
What official legal or regulatory source currently lists which preservatives or
additives are permitted in infant formula sold in Denmark? Answer from
official/current regulatory sources if available.
```

Sanitized observed facts:

- Admission considered, but not eligible or used:
  `admission_considered=true`, `admission_eligible=false`,
  `admission_used=false`, `admission_skip_reason=existing_source_class_satisfied`.
- Required and unsatisfied classes included `legal_or_regulatory_text` and
  `official_current_rules`.
- Active source-class recovery missing classes included those same two classes.
- `source_obligation_status=official_current_required_unmet`.
- Official/canonical source-class recovery was not admitted in the final
  diagnostic projection.
- Recovery queries existed and were Denmark/authority-shaped.
- `source_class_recovery_eligible=true`.
- `source_class_recovery_execution_attempted=false`.
- `source_class_recovery_skip_reason=source_class_recovery_executor_dispatch_not_authorized`.
- Candidate acquisition was not attempted:
  `candidate_return_status=not_attempted`,
  `candidate_acquisition_considered=false`,
  `candidate_acquisition_eligible=false`,
  `candidate_acquisition_used=false`, `acquisition_attempted=false`.
- `controller_recovery_decision=stop_legacy_custody_gap`.
- `controller_recovery_allowed_executor_action=no_recovery_executor_action`.
- `controller_recovery_retry_allowed=false`.
- `candidate_state_summary=selected_complete_official_current_evidence_exists`.
- Ledger legacy gap types included final evidence/citation without candidate
  passport custody, without final selected authority evidence, and a provider
  result to final evidence parallel path.

## Field Provenance Map

| Field | Producer | Consumer and runtime effect | Classification |
| --- | --- | --- | --- |
| `active_source_class_recovery_eligible` | `record_source_class_recovery_lifecycle()` from `decide_source_class_recovery()`; overridden for authority lifecycle control in `controller_loop_spine` when authority lifecycle is present | Consumed by controller loop spine for source-class dispatch eligibility, by `ControllerRecoveryDecision` budget-state fallback, and by visibility export | Runtime control field before export; diagnostic projection in reports |
| `active_source_class_recovery_official_canonical_admitted` | `authoritative_source_action` passes official/canonical admission into source-class lifecycle | Consumed by controller loop spine official/canonical fallback, `ControllerRecoveryDecision`, and export | Runtime control field before export |
| `active_source_class_recovery_missing_classes` | `source_class_recovery_lifecycle` from normalized controller input; export can rehydrate from admission/required classes | Consumed by action envelope, decision source-class derivation, and visibility export | Runtime control in lifecycle; visibility/export rehydration risk after export |
| `source_class_recovery_execution_attempted` | Visibility alias of `active_source_class_recovery_execution_attempted` | Used in diagnostics and candidate-return projection | Diagnostic projection alias |
| `source_class_recovery_skip_reason` | Visibility alias of `active_source_class_recovery_skip_reason` | Reports the last lifecycle/runner/executor block reason | Diagnostic projection of a runtime block |
| `controller_recovery_decision` | `build_controller_recovery_decision()` in orchestrator/runner path; export hydrates if absent | Provider-search allocation gate and source-class executor consume the runtime decision; export may build a projection-only copy | Runtime control when passed to runner/executor; diagnostic when hydrated by export |
| `controller_recovery_allowed_executor_action` | `ControllerRecoveryDecision.to_trace_fields()` from `_allowed_executor_action()` | Provider-search allocation checks for `record_provider_search_review_request`; source-class executor uses `retry_allowed` rather than this string | Runtime control for allocation; diagnostic explanation for other decisions |
| `controller_recovery_retry_allowed` | `ControllerRecoveryDecision` decision table | `controller_recovery_executor_allows_attempt()` lets the mechanical executor spend the action only when true if the controller gate is authoritative | Runtime control field |
| `candidate_state_summary` | `_candidate_state_summary()` in `controller_recovery_decision.py` | Direct input to `_decide()`; can return selected-complete from final aggregate counts before candidate-acquisition status is evaluated | Runtime control inside decision table; over-trusting aggregate risk |
| `ledger_custody_status` | `ControllerEvidenceLedger.final_evidence_citation_custody.status`; export can mirror as `final_evidence_citation_custody_status` | `ControllerRecoveryDecision` stops on `legacy_gap_observed` or architecture-stops on missing disposition | Runtime control field when ledger is in the trace |
| `legacy_gap_types` | `ControllerEvidenceLedger` legacy gap events; export mirrors as `ledger_legacy_gap_types` | Any non-empty list makes `_decide()` return `STOP_LEGACY_CUSTODY_GAP` before unmet-obligation retry logic | Runtime control field when present; diagnostic in export |
| `source_obligation_status` | Direct trace field, or derived in `ControllerRecoveryDecision` and visibility export from required/unsatisfied/admitted classes | Decision table uses `*_unmet` to allow retry only after legacy gap, hard blocker, and candidate-state checks | Mixed runtime control and diagnostic projection |
| `authorized_spine_action` | `ControllerLoopDispatchAuthorization.authorized_action_name` assigned in `pipeline_orchestrator.py` | `source_class_recovery_runner` executes source-class recovery only when it equals `recover_missing_source_class` | Runtime control field |
| `provider_search_allocation_trace` | `record_provider_search_allocation_if_controller_authorized()` | Visibility export and allocation-result custody projection observe it; not produced unless `ControllerRecoveryDecision` requests provider-search review | Runtime handoff/diagnostic field for allocation lane |
| `allocation_execution_authorized` | `allocation_result_candidate_custody` projection from provider-search allocation execution trace | `allocation_candidate_selection_activation` requires true before admitting allocation candidates into selection corridor | Runtime handoff/custody projection |
| `allocation_execution_attempted` | `allocation_result_candidate_custody` projection from provider-search allocation execution trace | Visibility/export and candidate custody diagnostics observe whether bounded allocation actually ran | Post-allocation diagnostic/control-adjacent projection |
| `candidate_return_status` | Candidate acquisition defaults, authority lifecycle execution sync, or visibility export fallback | Decision table uses it after final aggregate counts; export can return `not_attempted` when execution never ran | Post-dispatch diagnostic; can coexist with over-trusting final aggregate candidate state |

## Offline Reproduction Result

Added `tests/test_ag94h_c_recovery_executor_dispatch_authorization_audit.py`.

The synthetic fixture uses:

- missing classes `legal_or_regulatory_text` and `official_current_rules`;
- `source_obligation_status=official_current_required_unmet`;
- `active_source_class_recovery_eligible=true`;
- `active_source_class_recovery_official_canonical_admitted=false`, matching the
  sanitized live projection;
- approved authority lifecycle recovery action;
- recovery queries and reusable provider/search/depth facts;
- no terminal stop, conflict owner, provider policy blocker, depth blocker, or
  hard cap;
- candidate acquisition not attempted;
- final evidence/citation aggregate counts plus `legacy_gap_observed`;
- no spine authorization passed to the runner.

Observed offline:

- `ControllerRecoveryDecision` returns `stop_legacy_custody_gap`,
  `retry_allowed=false`, and `allowed_executor_action=no_recovery_executor_action`.
- Controller loop spine returns `authorized_dispatch=None` when the checkpoint
  packet does not approve `RECOVER_MISSING_SOURCE_CLASS` or meet the
  official/canonical fallback conditions.
- `run_source_class_recovery_dispatch()` records
  `source_class_recovery_executor_dispatch_not_authorized`.
- Authority lifecycle execution is projected as blocked with the same reason.
- No fake provider/search callable is invoked.

Classification: **D. Spine authorization gap.**

## Classification A/B/C/D/E/F

Chosen classification: **D. Spine authorization gap**.

Reason:

- The observed skip reason is written by the runner only in the absent-spine
  branch.
- `ControllerRecoveryDecision` does not feed the controller loop spine in the
  current handoff. It cannot directly produce the runner's
  `source_class_recovery_executor_dispatch_not_authorized` reason.
- If the runner receives `authorized_spine_action=RECOVER_MISSING_SOURCE_CLASS`,
  it calls the source-class executor. If it receives `None`, it records the live
  skip reason.

Secondary findings, not the exact classification:

- **B-like behavior risk:** `STOP_LEGACY_CUSTODY_GAP` is overbroad as an
  execution block once lifecycle is eligible and official/current obligation is
  unmet.
- **C-like projection risk:** `candidate_state_summary` can infer selected
  complete evidence from final aggregate counts even while candidate acquisition
  was not attempted and the official/current obligation remains unmet.

## Legacy Custody Gap Semantics

`STOP_LEGACY_CUSTODY_GAP` came from the AG-74B/AG-74D custody work. Its original
purpose was to prevent final evidence/citation aggregate counts from being
treated as successful ControllerEvidenceLedger custody when candidate passport,
represented candidate, disposition, or selected authority evidence custody was
missing.

The semantic meaning should be:

```text
Do not trust existing final evidence/citation aggregate counts as custody
completion.
```

The current decision table implements the stronger meaning:

```text
Do not attempt further recovery.
```

`core/controller_recovery_decision.py::_decide()` checks
`legacy_gap_observed` and `legacy_gap_types` before it checks hard blockers,
candidate acquisition state, budget availability, or unmet official/current
obligation retry availability. That makes legacy custody gap a final execution
block.

After AG-94H-B, that priority is no longer correct for the live shape under
audit. Source-class lifecycle can be eligible before candidate acquisition. In
that state, a legacy final-evidence/citation gap should block final success, but
it should not defeat a bounded recovery attempt when all of these are true:

- recovery budget is available;
- lifecycle is eligible;
- source obligation is unmet;
- no terminal/conflict/provider/depth/hard-cap blocker exists;
- candidate acquisition has not been attempted.

## Candidate-State Summary Contradiction

The contradiction is real and is best classified as an over-trusting aggregate
projection.

`_candidate_state_summary()` first checks:

```text
final_selected_authority_evidence_count > 0
or final_evidence_official_or_canonical_count > 0
   and final_citation_official_or_canonical_count > 0
```

If that is true, it returns
`selected_complete_official_current_evidence_exists` before it evaluates
candidate-return or candidate-acquisition fields. Therefore the following can
coexist:

- `source_obligation_status=official_current_required_unmet`;
- `candidate_return_status=not_attempted`;
- `candidate_acquisition_considered=false`;
- `candidate_acquisition_eligible=false`;
- `candidate_acquisition_used=false`;
- `acquisition_attempted=false`;
- `candidate_state_summary=selected_complete_official_current_evidence_exists`.

This is not legitimate evidence that a recovery candidate was acquired. It is a
legacy aggregate/final-survival signal being read as candidate-state control.
It should remain a diagnostic observation unless ControllerEvidenceLedger or
FinalAnswerPacket custody proves selected authority evidence.

## Dispatch Owner Chain

Current runtime path:

```text
source_class_recovery_lifecycle
-> controller_loop_spine
-> ControllerRecoveryDecision
-> provider-search allocation gate
-> source-class recovery runner
-> source-class recovery executor
```

More precisely:

1. `source_class_recovery_lifecycle` records eligibility, missing classes,
   queries, provider role, search depth, action envelope, and authority
   lifecycle execution state.
2. `controller_loop_spine` consumes the lifecycle and checkpoint trace. It is the
   last upstream component that can produce
   `authorized_spine_action=RECOVER_MISSING_SOURCE_CLASS`.
3. `pipeline_orchestrator.py` passes `authorized_spine_action` into
   `SourceClassRecoveryRunnerContext`.
4. `ControllerRecoveryDecision` is built from the active lifecycle when creating
   the runner context. It does not override or subordinate the spine action.
5. The provider-search allocation gate runs first inside the runner, but only
   allocates when the decision is `REQUEST_PROVIDER_SEARCH_REVIEW`.
6. The runner calls `execute_source_class_recovery_action()` only when
   `authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS`.
7. The source-class executor has an additional `ControllerRecoveryDecision`
   gate. If reached with `STOP_LEGACY_CUSTODY_GAP`, it would deny the executor
   with `controller_recovery_decision_denied_executor_action`, not with the live
   `source_class_recovery_executor_dispatch_not_authorized` reason.

Last opportunity to authorize execution: `controller_loop_spine` for the spine
action; `source_class_recovery_runner` is the final mechanical consumer and the
writer of the observed skip reason.

Did the runner receive `authorized_spine_action=RECOVER_MISSING_SOURCE_CLASS`?
No in the offline reproduction, and the live skip reason implies the same.

Why not? The spine did not produce/pass the recovery action because the
checkpoint packet did not approve `RECOVER_MISSING_SOURCE_CLASS` and did not
meet the official/canonical fallback shape consumed by
`_official_canonical_unavailable_checkpoint_allows_fallback()`.

Is there a single owner? Not yet. There are two independent gates:

- spine authorization, consumed by the runner;
- `ControllerRecoveryDecision`, consumed by allocation and by the executor.

They can block the same recovery attempt for different reasons.

## Whether Behavior Repair Is Needed

Yes. A focused behavior repair is needed.

The repair should not change provider order, provider routing, provider
selection, search depth, query generation, ranking/filtering, Author prose,
final-answer behavior, citation behavior, package names, CLI/env/database names,
or broadly rewrite `core/pipeline_orchestrator.py`.

The narrow behavior target should be:

- Make unmet official/current source obligation with eligible lifecycle,
  available recovery budget, no hard blocker, and no candidate acquisition
  attempt subordinate `legacy_gap_observed` for one bounded recovery attempt.
- Ensure the component that owns the recovery permission is the same component
  whose output the runner consumes, or make the subordinate handoff explicit.
- Preserve `legacy_gap_observed` as a final-success block until custody is
  proved by ControllerEvidenceLedger/FinalAnswerPacket, not aggregate counts.
- Prevent `selected_complete_official_current_evidence_exists` from short
  circuiting retry when it is based only on legacy final aggregate counts while
  `candidate_return_status=not_attempted` and source obligation is unmet.

## Recommended Next Phase

Recommended next decision: **focused behavior repair**.

Suggested phase:

```text
AG-94H-D - Recovery Dispatch Authorization Behavior Repair
```

Exact narrow target:

- `core/controller_recovery_decision.py`
- `core/controller_loop_spine.py`
- `core/source_class_recovery_runner.py` and
  `core/source_class_recovery_executor.py` only as consumers to prove the
  handoff, not as provider/search behavior owners
- existing AG-94H-C tests as before/after fixtures

Acceptance criteria:

- With lifecycle eligible, official/current obligation unmet, recovery budget
  available, recovery queries present, no hard blocker, and candidate acquisition
  not attempted, `legacy_gap_observed` blocks final success but does not block
  one bounded recovery attempt.
- `authorized_spine_action=RECOVER_MISSING_SOURCE_CLASS` reaches the runner for
  the approved recovery path, or the architecture chooses one named replacement
  authorization owner consumed by the runner.
- If legacy aggregate final evidence/citation counts are present without
  candidate/passport/selected-evidence custody, they do not produce
  `selected_complete_official_current_evidence_exists` as a retry-stopping
  control state while `candidate_return_status=not_attempted`.
- Hard blockers still win: terminal stop, conflict ownership, provider policy
  change required, search-depth escalation required, hard recovery cap, missing
  recovery query, or unsupported source class.
- No provider/search/depth/query/ranking/Author/citation behavior changes.

## Protected/Closed Surfaces Kept Closed

Kept closed:

- live ScryRaven/proplex provider, model, search, or retrieval calls;
- secrets, `.env`, API keys, DB rows, raw provider payloads, raw prompts,
  private logs, caches, full raw traces, local output packets, private artifacts;
- provider swap, provider integration, provider order, routing, selection,
  search depth, and search budget changes;
- query generation changes;
- ranking/filtering changes;
- Author prose, final-answer, and citation behavior;
- package, CLI, env, database, and session renames;
- broad `core/pipeline_orchestrator.py` rewrite.

`core/pipeline_orchestrator.py` line delta in this audit: `0`.

## Tests/Checks Run

Passed locally:

- `py -m pytest -q tests/test_ag94h_c_recovery_executor_dispatch_authorization_audit.py`
  - `4 passed`
- `py -m pytest -q tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py`
  - `12 passed`
- `py -m pytest -q tests/test_ag94b_cli_official_current_recovery_trace_custody.py`
  - `6 passed`
- `py -m pytest -q tests/test_ag74d_controller_recovery_retry_stop_loop.py`
  - `10 passed`
- `py -m pytest -q tests/test_ag74f_recovery_runner_extraction.py`
  - `5 passed`
- `py -m pytest -q tests/test_ag75a_controller_provider_search_allocation_gate.py`
  - `8 passed`
- `py -m ruff check .`
  - passed
- `py -m pytest -q tests`
  - `2927 passed, 1 deselected, 1 xfailed`
- `py -m pre_commit run --all-files`
  - passed: merge-conflict check, EOF fixer, trailing whitespace, YAML, ruff,
    and detect-secrets

## No-Live Confirmation

No live provider, model, search, or retrieval calls were run. All reproduction
used synthetic fixtures and fake/local callables.
