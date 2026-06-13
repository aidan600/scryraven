# AG-95J/K Active-Gate And Lifecycle Boolean Diet

Status: implemented as offline runtime/test/doc cleanup. No live
ScryRaven/proplex provider, model, search, retrieval, secret, `.env`, DB row,
raw provider payload, raw prompt, private log, cache, full raw trace, local
output packet, or private artifact access was used.

## Current Doctrine

Source-class recovery dispatch authority remains:

```text
AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

ControllerLoopSpine and the compatibility spine may still expose shared
active-gate packet fields for non-source-class arbitration. Those fields are not
source-class runner dispatch authority. Old source-class lifecycle and admission
booleans are compatibility projections unless a named runtime consumer still
requires them.

## Stage A Inventory

| Field | Deleted or rewritten | Preserved |
| --- | --- | --- |
| `authorized_dispatch` | No new source-class assertion remained in the edited runtime/test set after AG-95I. | Preserved as generic `ControllerLoopSpineResult` compatibility; no runner reads it. |
| `executed_action_name` | No source-class `executed_action_name` assertion remained in the edited source-class tests. | Preserved for weak-corpus and other non-source-class active-gate contract checks. |
| `executor_dispatched` | Removed the source-class gate `executor_dispatched is True` assertion from the AG94H-E parity audit. | Preserved as a shared active-gate packet field for non-source-class arbitration and static guards. |
| `promoted_action_name` | Removed source-class `promoted_action_name == recover_missing_source_class` assertions from AG20/AG22 source-class-adjacent tests. | Preserved where it still proves weak-corpus active-gate promotion. |
| `blocked_or_skipped_actions` | Removed source-class-adjacent blocked/skipped assertions from AG20, AG22, and AG70A. | Preserved for non-source-class active-gate invariant suites and weak/conflict/targeted retrieval coverage. |

## Stage B Inventory

| Boolean family | Deleted or rewritten | Preserved |
| --- | --- | --- |
| `active_source_class_recovery_*` | Rewrote AG20/AG22 source-class success checks from `active_source_class_recovery_used`, `active_source_class_recovery_attempt_count`, and related booleans to `authority_lifecycle.recovery_action` plus nested execution state. Removed duplicate AG94H-E eligibility/provider/attempt/use assertions when canonical action and runner execution already proved the behavior. | Preserved in dedicated lifecycle/projection/export tests where the legacy field itself is the compatibility surface under test. |
| `official_canonical_recovery_execution_*` | Removed redundant AG70A `official_canonical_recovery_execution_admitted` assertions where canonical recovery action or terminal-stop state carried the same proof. | Preserved in admission-path tests where `OfficialCanonicalRecoveryExecutionAdmission` is the unit under test. |
| `authority_lifecycle_required_recovery_allowed` | Rewrote redundant AG20/AG22/AG70A/AG94H-E assertions to canonical recovery-action approval, nested execution state, or terminal-stop state. Updated the compatibility-field metadata so `active_source_class_recovery_eligible` points to `authority_lifecycle.recovery_action.approved` instead of another legacy boolean. | Preserved in older product-callsite and pipeline-adapter tests where runtime helper behavior still consumes or exposes the field. |
| `authority_lifecycle_execution_*` | Removed duplicate AG94H-E flattened execution assertions and rewrote AG70A blocker coverage to nested `authority_lifecycle.execution_state.state`. | Preserved in AG69C/AG69E/AG69F tests that intentionally poison or validate projection compatibility. |

## Deleted And Rewritten Assertions

- Deleted source-class-adjacent active-gate assertions in:
  `tests/test_ag20_official_source_recovery_quality.py`,
  `tests/test_ag22_official_source_domain_recovery_lane.py`,
  `tests/test_ag70a_live_failure_split_diagnosis_ssa_admission.py`, and
  `tests/test_ag94h_e_authority_lifecycle_source_class_parity_audit.py`.
- Rewrote source-class success proof to
  `authority_lifecycle.recovery_action.action_type`,
  `authority_lifecycle.recovery_action.approved`,
  `authority_lifecycle.execution_state.state`, and provider-role/captured-query
  proof.
- Rewrote compatibility metadata in
  `core/authority_lifecycle_compatibility_fields.py` so the replacement for
  `active_source_class_recovery_eligible` names canonical recovery-action
  approval directly.

## Preserved Surfaces

- Non-source-class shared active-gate coverage for weak-corpus, conflict,
  terminal-stop, targeted retrieval, and retrieval-batch projection remains in
  place.
- Projection-poisoning and compatibility-field tests remain where the legacy
  boolean is the subject of the test.
- `core/pipeline_orchestrator.py` was inspected but not edited. Its bounded old
  lifecycle/admission reads still require a separate product-callsite cleanup
  phase because they sit near stale checkpoint refresh and source-class ownership
  summary behavior.

## Terminology Cleanup

- Updated current Codex guidance to route source-class recovery cleanup through
  AG-95I plus AG-95J/K.
- Updated the RunAuthority implementation guide to describe AG-95J/K as the
  active-gate/lifecycle boolean follow-on.
- Replaced current-looking legacy source-of-truth wording in
  `core/authority_lifecycle_compatibility_fields.py` with RunAuthority-owned
  lifecycle wording.

## Blockers And Boundaries

No stop-condition blocker was hit. The exact retained-boundary blocker is
`core/pipeline_orchestrator.py`: changing its remaining
`active_source_class_recovery_eligible`/`active_source_class_recovery_used` and
official-admission reads would cross from assertion cleanup into product-callsite
behavior around stale checkpoint refresh and ownership summaries. Provider
routing/selection/depth, query text/generation, ranking/filtering,
Author/final-answer/citation behavior, live calls, secrets, DB/private logs,
caches, output packets, and broad orchestrator refactor remained closed.

## Net LOC Impact

Runtime LOC: +4/-4, net 0.
Test LOC: +30/-62, net -32.
Docs LOC: +126/-11, net +115.
Total LOC: +160/-77, net +83.

## Next Cleanup Target

Target the remaining bounded product-callsite compatibility reads in
`core/pipeline_orchestrator.py`, especially stale checkpoint refresh and
source-class ownership summaries. That phase should first prove the runtime
consumer can read `AuthorityLifecycle.recovery_action` and nested lifecycle
state without changing provider routing, query generation, ranking, Author
handoff, or citation behavior.
