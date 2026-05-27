# AG-67A Forced Authoritative Recovery Validation

Scope: offline validation only. No ProPlex live run, provider call, model call,
external source check, raw prompt, raw provider payload, DB row, cache, private
log, or full trace was used.

## Purpose

AG-67A preserves the AG-64D caveat: an answer can acquire official IRS evidence
through ordinary retrieval without proving that the missing-authoritative-source
recovery path executed. The validation harness therefore classifies ordinary
authoritative-source presence separately from missing-source recovery readiness,
admission, dispatch, and recovered-evidence visibility.

## Harness

The offline harness lives in the test-only helper
`tests/helpers/authoritative_source_forced_corridor.py`. No production/runtime
code was added for validation-only logic.

It constructs two forced corridors:

- official/current: IRS 2026 standard mileage rate style obligation;
- canonical docs: PostgreSQL MVCC documentation style obligation.

Both corridors begin with ordinary evidence marked as
`expected_but_only_secondary`, so lower-tier context exists but does not satisfy
the official/current or canonical authority requirement. The same AG-66B named
authoritative-source action seam then runs the existing bridge, query
acquisition, execution admission, lifecycle readiness, controller-loop spine,
and dependency-injected source-class recovery executor.

The ordinary-success negative control marks the ordinary source class as
`satisfied_strong`. In that case the harness reports
`ordinary_authoritative_source_already_present: true` and does not count that as
recovery execution success.

## Classification

The output includes:

- `ordinary_authoritative_source_already_present`
- `missing_authoritative_source_state_forced`
- `authoritative_recovery_query_created`
- `recovery_execution_admitted`
- `recovery_dispatch_authorized`
- `recovered_evidence_visible`
- `final_answer_citation_or_use`
- `next_failure_layer`

`final_answer_citation_or_use` is always `not_applicable_offline` in AG-67A.
Citation survival and answer use remain live-validation questions for a
separate user-approved phase.

## Cleanup Audit

No bridge/shadow field was retired in AG-67A. Named consumers still exist for
the legacy compatibility fields, including AnswerContract runtime handoff,
evidence integration checkpoint, source-class recovery lifecycle/export,
controller-loop spine traces, recovered-evidence visibility diagnostics, and
AG-64/65/66 tests.

Fields retained as compatibility or trace/export surface include:

- `missing_expected_source_classes`
- `source_class_recovery_recommended`
- `source_class_recovery_shadow_mode`
- `source_class_recovery_queries`
- `source_class_recovery_query_count`
- `bridge_used`
- `acquisition_repair_used`
- `admission_used`
- `active_source_class_recovery_*`
- `official_source_obligation_bridge_trace`
- `official_canonical_recovery_query_acquisition_trace`
- `official_canonical_recovery_execution_admission_trace`

The controller/action seam remains the control owner. Projection and trace
fields are observed by tests and exports but are not used as control inputs.

## Boundary

AG-67A is forced-corridor validation, not production cleanup. It does not
change provider routing, provider selection, search depth,
retrieval, ranking, filtering, query wording beyond existing adapters, prompts,
citations, final-answer behavior, Author, Analyst, Economist, Scrutineer, legal
answer behavior, or follow-up behavior.

If this offline corridor passes, the recommended next action is a separately
approved bounded live validation design. AG-67A itself must not claim that
AG-64ABC / IRS dispatch recovery is live-proven fixed.
