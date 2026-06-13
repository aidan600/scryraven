# AG-95I ControllerLoopSpine Packet Field Diet

Status: implemented as offline runtime/test/doc cleanup. No live
ScryRaven/proplex provider, model, search, retrieval, secret, `.env`, DB row,
raw provider payload, raw prompt, private log, cache, full raw trace, local
output packet, or private artifact access was used.

## Current Doctrine

Source-class recovery dispatch authority is:

```text
AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

ControllerLoopSpine may still produce shared active-gate compatibility fields,
but those fields are not source-class runner dispatch authority.

## Consumer Inventory And Disposition

| Consumer | Target keys | Classification | AG-95I action |
| --- | --- | --- | --- |
| `core/controller_loop_spine.py` source-class gate packet | `source_class_executor_dispatched`, `official_canonical_dispatch_fallback`, AG-95F demotion markers | delete now | Deleted packet keys and constants. The gate now exposes shared `executor_dispatched`, `gated_action`, `gate_reason`, and `spine_authorization_source` only. |
| `ControllerLoopDispatchAuthorization.to_dict()` and `ControllerLoopSpineResult.to_dict()` | `source_class_executor_dispatched` | delete now | Deleted the source-class-specific property/serialization alias. |
| ControllerLoopSpine combiner/invariant internals | `source_class_executor_dispatched`, source-class use of `executor_dispatched` | rewrite/preserve shared active gate | Replaced the source-specific alias with `gated_action == recover_missing_source_class and executor_dispatched`. Preserved generic `executor_dispatched` because weak-corpus, conflict, terminal-stop, and targeted-retrieval tests still share the active-gate contract. |
| `tests/test_controller_loop_spine.py` | all source-class-specific packet fields, source-class `authorized_dispatch`, repeated source-class `executed_action_name` checks | delete/rewrite | Replaced preservation tests with absence guards. Rewrote fallback checks to `spine_authorization_source` and shared active-gate helpers. |
| AG64/AG68/AG69/AG70/AG93/AG94/AG95 source-class tests | `source_class_executor_dispatched`, source-class `authorized_dispatch` | delete/rewrite | Deleted redundant spine-dispatch assertions. Kept canonical lifecycle, runner execution, captured query, provider-role, gate-reason, and blocked-action assertions. |
| AG20/AG22 older source-class packet tests | source-class `executed_action_name` | delete now | Removed redundant source-class `executed_action_name` assertions; provider-role and lifecycle execution checks remain. |
| AG35/AG36/AG37 active-gate invariant tests and helpers | `executed_action_name`, `executor_dispatched` | preserve as non-source-class active-gate compatibility | Preserved. These suites validate the shared active-gate packet contract across weak-corpus, conflict, terminal-stop, targeted retrieval, and source-class-adjacent arbitration. |
| `core/pipeline_orchestrator.py` | old source-class keys | preserve no-op audit result | Confirmed no source-class old-key residue remains; only weak-corpus and conflict result properties remain. |
| `core/source_class_recovery_runner.py` | old packet keys, `authorized_dispatch`, `executed_action_name`, `executor_dispatched` | rewrite/static guard | Runner continues to read `authority_lifecycle.recovery_action`; static guard now proves it does not depend on ControllerLoopSpine packet fields. |
| AG-95F/G/H docs and Codex guidance | old-key doctrine text | rewrite to current guidance | Compressed AG-95F/G/H as historical notes and routed current packet doctrine through AG-95I. Updated Codex guidance and RunAuthority guide. |
| AG94/AG95D/E and validation notes | old-key historical references | preserve as historical doc only | Left untouched as historical phase records. They are not current routing guidance. |

## Fields Deleted, Replaced, Or Preserved

Deleted from ControllerLoopSpine runtime packets/results:

- `source_class_executor_dispatched`
- `official_canonical_dispatch_fallback`
- `source_class_spine_trace_role`
- `source_class_spine_dispatch_authority`
- `source_class_runner_dispatch_authority`

Replaced:

- `official_canonical_dispatch_fallback` assertions now use
  `spine_authorization_source == "official_canonical_admission"` where the
  source-class gate reason still matters.
- Source-class-specific dispatch aliases now derive internally from shared
  active-gate state instead of being serialized.

Preserved:

- `authorized_dispatch` remains only as a generic `ControllerLoopSpineResult`
  compatibility property and is no longer asserted as source-class runner
  dispatch proof.
- `executed_action_name` and `executor_dispatched` remain shared active-gate
  compatibility fields, not source-class runner authority.
- `weak_corpus_executor_dispatched`,
  `conflict_resolution_executor_dispatched`, and
  `targeted_retrieval_executor_dispatched` remain non-source-class active-gate
  compatibility surfaces.

## Blockers And Boundaries

No blocker prevented deleting a runtime/test field family. The remaining shared
active-gate fields cannot be deleted in this phase without expanding into
weak-corpus, conflict, terminal-stop, targeted-retrieval, and AG35-AG37 active
gate contract changes. Provider routing/selection/depth, query text, ranking,
Author/final-answer/citation behavior, live calls, secrets, private artifacts,
DB rows, caches, output packets, and broad orchestrator refactor remained
closed.

## Static Guard

`tests/test_ag95f_controller_loop_spine_source_class_trace_demotion.py` now
proves that `SourceClassRecoveryRunner` does not read ControllerLoopSpine
packet fields, including the retired source-class keys and the shared
`executor_dispatched` / `executed_action_name` active-gate fields.

## Net LOC Impact

Runtime LOC: +16/-38, net -22.
Test LOC: +138/-191, net -53.
Docs LOC: +156/-268, net -112.
Total LOC: +310/-497, net -187.

## Next Cleanup Phase

AG-95J/K consumes the immediate follow-up: it inventories shared active-gate
compatibility and old source-class lifecycle/admission booleans, removes
source-class-adjacent duplicate assertions, and preserves only active-gate
coverage that still belongs to weak-corpus, conflict, terminal-stop, targeted
retrieval, or retrieval-batch projection contracts.
