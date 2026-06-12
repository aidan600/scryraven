# AG-95H Remaining Source-Class Compatibility Trace Diet

Status: implemented as offline test/helper compatibility cleanup. No live
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

`ControllerLoopSpine` source-class fields are diagnostic compatibility output.
They must not be used as source-class runner dispatch authority.

## Remaining Assertion And Consumer Inventory

| Surface | Remaining old-key use before AG-95H | Classification | AG-95H disposition |
| --- | --- | --- | --- |
| `tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py` | Four direct assertions on `authorized_dispatch` and `official_canonical_dispatch_fallback` in the checkpoint-gap test. | Move/delete from product-callsite coverage. | Deleted from AG68E. Equivalent checkpoint-gap/fallback compatibility now lives in focused ControllerLoopSpine coverage. |
| `tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py` | Three direct assertions on stale/refreshed `authorized_dispatch` and `source_class_executor_dispatched`. | Move/delete from product-callsite coverage. | Deleted from AG68G. Product-callsite tests now prove lifecycle authority, runner execution, captured queries, and recovered passage state. |
| `tests/test_authority_lifecycle_execution_ag69c.py` | No direct assertions on the three AG-95H target keys remained. | Preserve. | No assertion deletion needed. AG69C stays focused on AuthorityLifecycle execution state and runner dispatch. |
| `tests/helpers/authoritative_source_forced_corridor.py` | Test helper consumed `spine.authorized_dispatch` to decide whether to call the source-class executor. | Delete/replace because it used a compatibility key as test-only dispatch authority. | Replaced with `run_source_class_recovery_dispatch()` and canonical lifecycle authorization. |
| `tests/test_controller_loop_spine.py` | Existing compatibility packet tests for source-class old keys. | Preserve and focus. | Added the AG-95H compatibility test for checkpoint-gap, stale checkpoint, refreshed checkpoint, fallback, and demotion markers. |
| `core/pipeline_orchestrator.py` | No remaining source-class reads of `authorized_dispatch`, `source_class_executor_dispatched`, or `official_canonical_dispatch_fallback` were found. | Preserve no-op audit result. | Runtime orchestrator unchanged. |

## Moved, Deleted, Or Preserved

Moved into focused ControllerLoopSpine compatibility coverage:

- AG68E synthetic/product checkpoint-gap `authorized_dispatch` checks.
- AG68E licensed checkpoint-exception
  `official_canonical_dispatch_fallback` check.
- AG68G stale checkpoint `authorized_dispatch is None` check.
- AG68G refreshed checkpoint `authorized_dispatch` and
  `source_class_executor_dispatched` checks.

Deleted from product-callsite tests:

- 7 direct AG68E/AG68G old-key assertions.
- AG68E's private legacy checkpoint-reason helper, which existed only for the
  deleted old-key checkpoint-gap test.

Preserved:

- ControllerLoopSpine compatibility packet assertions, because those tests own
  the diagnostic packet contract.
- AG68E/AG68G/AG69C product-callsite runner assertions on canonical
  `authority_lifecycle.recovery_action`, lifecycle execution state, offline fake
  query capture, and recovered passage state.

## Why Old-Key Assertions Remain

Old-key assertions remain only in ControllerLoopSpine-focused compatibility
coverage and static guards. They remain to prove the diagnostic packet shape and
the explicit AG-95F demotion markers:

- `source_class_spine_trace_role=diagnostic_compatibility`
- `source_class_spine_dispatch_authority=false`
- `source_class_runner_dispatch_authority=authority_lifecycle.recovery_action`

No AG68E/AG68G/AG69C product-callsite test now directly asserts
`authorized_dispatch`, `source_class_executor_dispatched`, or
`official_canonical_dispatch_fallback`.

## Orchestrator Audit Result

`core/pipeline_orchestrator.py` has no remaining source-class old-key residue
for the AG-95H target keys:

- `authorized_dispatch`
- `source_class_executor_dispatched`
- `official_canonical_dispatch_fallback`

No provider/search/query/Author/final-answer behavior changed.

## Bonus Cleanup Result

Attempted: yes.

What changed:

- The forced-corridor helper stopped building ControllerLoopSpine solely to
  decide whether to execute source-class recovery.
- The helper now calls `SourceClassRecoveryRunner`, letting the canonical
  lifecycle authorization decide execution.
- Obsolete helper imports and the AG68E legacy checkpoint helper were removed.

What was left alone:

- AG69C had no now-unused old-key helper code after AG-95G.
- `core/pipeline_orchestrator.py` had no AG-95H source-class old-key residue to
  remove.
- Historical AG-95D/E/F/G bodies were not rewritten wholesale; current guidance
  now routes through AG-95H.

## Net LOC Impact

Final branch impact after implementation, validation, and AG-95H documentation:
`+255/-102`, net `+153` LOC. The runtime/orchestrator line impact is `0`; the
net growth is the required AG-95H architecture note and compact guidance
routing.

## Recommended Next Cleanup/Deletion Phase

AG-95I should inventory remaining ControllerLoopSpine source-class compatibility
packet consumers outside AG68E/AG68G/AG69C. The safest next deletion target is a
controller-loop packet field diet that names each remaining consumer of
`authorized_dispatch`, `source_class_executor_dispatched`,
`executor_dispatched`, and `executed_action_name`, then retires only
source-class-specific diagnostics whose consumers have moved to canonical
AuthorityLifecycle or RunAuthority state.
