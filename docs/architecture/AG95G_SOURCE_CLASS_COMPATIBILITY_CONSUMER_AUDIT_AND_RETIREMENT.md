# AG-95G Source-Class Compatibility Consumer Audit And Retirement

Status: implemented as offline consumer audit, safe rewrite, and cleanup. No
live ScryRaven/proplex provider, model, search, retrieval, secret, `.env`, DB
row, raw provider payload, raw prompt, private log, cache, full raw trace, local
output packet, or private artifact access was used.

## Current Doctrine

Source-class recovery dispatch authority remains:

```text
AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

`ControllerLoopSpine` source-class keys are diagnostic compatibility output.
They may explain older spine-era state, but they must not authorize source-class
runner execution.

## Consumer Inventory

Checklist:

- [x] `source_class_executor_dispatched`
- [x] `executor_dispatched`
- [x] `authorized_dispatch`
- [x] `executed_action_name`
- [x] `official_canonical_dispatch_fallback`
- [x] `source_class_spine_trace_role`
- [x] `source_class_spine_dispatch_authority`
- [x] `source_class_runner_dispatch_authority`

| Consumer | Keys | Classification | Action taken |
| --- | --- | --- | --- |
| `core/controller_loop_spine.py` source-class gate producer | `source_class_executor_dispatched`, `executor_dispatched`, `official_canonical_dispatch_fallback`, demotion markers | preserve as diagnostic compatibility | Preserved. AG-95F requires these trace keys until compatibility consumers are retired. |
| `core/controller_loop_spine.py` combined active-gate/invariant assembly | `source_class_executor_dispatched`, `executor_dispatched`, `executed_action_name` | blocked pending later consumer-retirement phase | Preserved. The same combiner still arbitrates weak-corpus, conflict, terminal-stop, and targeted-retrieval checkpoint traces. |
| `core/controller_loop_spine.py` result/authorization dataclasses | `authorized_dispatch`, `executed_action_name`, `source_class_executor_dispatched` | preserve as diagnostic compatibility | Preserved as the typed projection of the trace packet. |
| `core/pipeline_orchestrator.py::_build_targeted_retrieval_lifecycle_from_runtime` | `source_class_executor_dispatched` | rewrite to canonical runner/lifecycle authority | Removed the old-key read. Source-class path ownership now uses lifecycle use/eligibility and checkpoint action only. |
| Current AG-95 static guards | `authorized_spine_action`, `source_class_executor_dispatched`, demotion markers | rewrite to canonical runner/lifecycle authority | Added an AG-95D guard preventing `pipeline_orchestrator.py` from reading `source_class_executor_dispatched`. |
| Current controller-loop tests | all listed ControllerLoopSpine keys | preserve as diagnostic compatibility | Preserved. These tests cover the compatibility packet contract and non-source-class active-gate behavior. |
| AG-68/AG-69 source-class runner tests | `authorized_dispatch`, `source_class_executor_dispatched`, `official_canonical_dispatch_fallback` | preserve as diagnostic compatibility | Preserved where they explicitly check checkpoint refresh or trace compatibility; dispatch proof remains canonical runner/lifecycle assertions. |
| Historical AG-20 through AG-94 docs/tests | `executor_dispatched`, `executed_action_name`, `authorized_dispatch`, source-class executor fields | blocked pending later consumer-retirement phase | Preserved as historical or broad active-gate coverage. Bulk rewrite would exceed the source-class compatibility lane. |
| AG-95D/E/F docs and current Codex guidance | demotion markers and old compatibility key references | preserve as diagnostic compatibility | Preserved because they document the migration history and current demotion contract. |

## Key-by-Key Audit

| Key | Repo consumers found | Classification | AG-95G disposition |
| --- | --- | --- | --- |
| `source_class_executor_dispatched` | `core/controller_loop_spine.py`, `core/pipeline_orchestrator.py`, controller-loop/source-class tests, AG-95D/E/F docs, one validation note | rewrite one runtime consumer; preserve diagnostics elsewhere | Removed from `pipeline_orchestrator.py`; preserved in `controller_loop_spine.py` and compatibility tests/docs. |
| `executor_dispatched` | `core/controller_loop_spine.py`, generic active-gate tests/docs, targeted-retrieval code/docs with non-source-class meaning | preserve diagnostic compatibility | No source-class deletion safe yet because the key is generic active-gate vocabulary shared with weak-corpus, conflict, terminal-stop, and targeted-retrieval tests. |
| `authorized_dispatch` | `ControllerLoopSpineResult`, source-class and non-source-class tests, helper diagnostics, AG-95 docs | preserve diagnostic compatibility | Preserved as a typed diagnostic projection; runner dispatch remains proven through lifecycle/runner fields. |
| `executed_action_name` | `core/controller_loop_spine.py`, active-gate invariant tests/docs, continuation/weak-corpus/conflict tests | blocked pending later consumer-retirement phase | Preserved because it is a shared active-gate invariant, not source-class-only state. |
| `official_canonical_dispatch_fallback` | `core/controller_loop_spine.py`, `tests/test_controller_loop_spine.py`, AG-68E parity fixture | preserve diagnostic compatibility | Preserved as compatibility evidence for checkpoint exception/fallback paths; not consumed by the runner. |
| `source_class_spine_trace_role` | `core/controller_loop_spine.py`, AG-95F tests/docs/current guidance | preserve diagnostic compatibility | Preserved as the explicit demotion marker. |
| `source_class_spine_dispatch_authority` | `core/controller_loop_spine.py`, AG-95F tests/docs/current guidance | preserve diagnostic compatibility | Preserved as the explicit `False` authority marker. |
| `source_class_runner_dispatch_authority` | `core/controller_loop_spine.py`, AG-95F tests/docs/current guidance | preserve diagnostic compatibility | Preserved to route readers to `authority_lifecycle.recovery_action`. |

## Old Surface Status

- Deleted from active runtime consumption:
  `pipeline_orchestrator.py` no longer reads
  `ControllerLoopSpineResult.source_class_executor_dispatched` while building
  targeted-retrieval ownership.
- Demoted/preserved:
  `source_class_executor_dispatched`, `executor_dispatched`,
  `authorized_dispatch`, `executed_action_name`, and
  `official_canonical_dispatch_fallback` remain ControllerLoopSpine diagnostic
  compatibility fields.
- Preserved as explicit demotion markers:
  `source_class_spine_trace_role`,
  `source_class_spine_dispatch_authority`, and
  `source_class_runner_dispatch_authority`.

## What Could Not Be Deleted

The ControllerLoopSpine trace keys could not be deleted yet because
controller-loop tests, AG-68/AG-69 compatibility fixtures, and the combined
active-gate invariant machinery still validate the packet shape. The combiner
also serves non-source-class lanes that remain out of scope for AG-95G.

## Recommended Next Deletion Target

Retire direct source-class assertions on `authorized_dispatch` and
`source_class_executor_dispatched` from AG-68/AG-69 compatibility tests after a
dedicated trace-contract diet proves equivalent coverage through
`source_class_recovery_dispatch_authority`,
`source_class_recovery_dispatch_authorized`, and
`authority_lifecycle.execution_state`.

## Net LOC Impact

Runtime cleanup impact: -4 LOC in `core/pipeline_orchestrator.py`.

Overall branch impact: +115/-6 LOC before formatting, for net +109 LOC. The net
growth is the required AG-95G audit note and short guidance follow-ups; the code
path itself shrank and no new abstraction, projection, lifecycle, or guard
surface was added.
