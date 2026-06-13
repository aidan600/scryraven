# AG-95M Pipeline Orchestrator Source-Class Authority Helper Extraction

Status: implemented as offline runtime/test/doc cleanup. No live
ScryRaven/proplex provider, model, search, retrieval, secret, `.env`, DB row,
raw provider payload, raw prompt, private log, cache, full raw trace, local
output packet, or private artifact access was used.

## Checklist

1. Inspected source-class authority helper definitions and callsites in
   `core/pipeline_orchestrator.py`.
2. Extracted bounded source-class authority reads to
   `core/source_class_authority_runtime_adapter.py`.
3. Replaced pipeline-local helper calls with imported adapter helpers.
4. Deleted the pipeline-local helper cluster and the stale checkpoint refresh
   read helper that depended on it.
5. Kept the adapter pure read/normalization over canonical
   `AuthorityLifecycle.recovery_action`, `execution_state`, and
   `explicit_blockers`, plus checkpoint terminal-stop parsing.
6. Performed a nearby terminology cleanup in the touched static guard by
   replacing current-looking "protected surfaces" wording with closed-surface
   wording.
7. Preserved active compatibility names and trace keys.
8. Updated static tests to prove the orchestrator does not define the extracted
   helper cluster.
9. Ran focused offline validation.

## Helpers Extracted Or Deleted

Deleted from `core/pipeline_orchestrator.py` and rehomed as public adapter
reads:

- `_source_class_recovery_authority_projection`
- `_source_class_recovery_authority_action`
- `_source_class_recovery_execution_state`
- `_source_class_recovery_action_approved`
- `_source_class_recovery_action_pending`
- `_source_class_recovery_action_attempted`
- `_source_class_recovery_authority_blocker_reasons`

Also extracted `_authoritative_source_checkpoint_refresh_allowed` as
`source_class_recovery_checkpoint_refresh_allowed(...)` because it was a bounded
consumer of the same canonical action/blocker reads and was the remaining local
compatibility helper tying the deleted cluster to checkpoint refresh.

## New Module Boundary

`core/source_class_authority_runtime_adapter.py` is intentionally small and
bounded. It imports only the source-class action constants and the existing
checkpoint action parser. It does not import provider, search, query,
Author/citation, ranking, prompt, persistence, or executor modules.

The adapter does not schedule work, mutate lifecycle traces, create retrieval
queries, choose providers, choose depth, rank/filter evidence, change final
answer posture, or call the source-class runner. Runtime dispatch authority
remains:

```text
AuthorityLifecycle.recovery_action
-> SourceClassRecoveryRunner
-> SourceClassRecoveryExecutor
```

## Orchestrator LOC

`core/pipeline_orchestrator.py` LOC:

- Before: 4,838
- After: 4,741
- Net: -97

The phase target was net negative and preferably -75 LOC or better. This branch
meets that target.

## LOC Accounting

- Runtime LOC: +180/-114, net +66
  - `core/pipeline_orchestrator.py`: +17/-114, net -97
  - `core/source_class_authority_runtime_adapter.py`: +163/-0, net +163
- Test LOC: +53/-17, net +36
- Docs LOC: +147/-0, net +147
- Total LOC: +380/-131, net +249

## Behavior Preserved

The pipeline still reads canonical `authority_lifecycle.recovery_action` for
source-class product callsites. The source-class runner remains the runtime
consumer for recovery dispatch and still executes only from canonical recovery
action state. The extraction did not change provider/search/query routing,
query generation, ranking/filtering, Author prose, final-answer posture,
citation behavior, or live validation behavior.

## Test And Static Proof

Updated
`tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py` to:

- import checkpoint refresh reads from the new adapter;
- assert `core/pipeline_orchestrator.py` defines none of the extracted helper
  cluster;
- assert the adapter does not import high-custody provider/search/query/Author
  modules;
- continue proving query strings, source-class dispatch, terminal-stop handling,
  and projection-only envelope rejection are preserved.

Focused validation:

```powershell
py -m pytest -q tests\test_source_class_recovery_live_product_dispatch_callsite_ag68g.py
```

Result: 9 passed.

Focused AG-95L/source-class/pipeline batch:

```powershell
py -m pytest -q tests\test_source_class_recovery_live_product_dispatch_callsite_ag68g.py tests\test_source_class_recovery_live_offline_dispatch_parity_ag68e.py tests\test_authoritative_source_named_action_extraction.py tests\test_authority_lifecycle_runtime_arbitration_ag69b.py tests\test_targeted_retrieval_runtime_ag43b.py tests\test_scout_continuation_spine_gate_ag45c.py tests\test_authority_lifecycle_execution_ag69c.py tests\test_ag95e_stale_dispatch_doctrine_cleanup.py tests\test_ag95d_recovery_dispatch_sanity_audit.py tests\test_ag95f_controller_loop_spine_source_class_trace_demotion.py
```

Result: 98 passed.

Ruff result: pending at note creation; final bundle records the completed result.

## Naming Hygiene And SCRY-02 Inventory

No current-looking ProPlex, FauxPlex, Foplex, or legacy-authority naming was
added. No package, CLI, env, state-key, or DB compatibility names were renamed:
`proplex`, `python -m proplex`, `PROPLEX_*`, `proplex.db`, and `proplex_*`
remain compatibility surfaces.

Touched compatibility residue intentionally preserved and recorded for future
SCRY-02 inventory:

- `legacy_runtime_branch` function argument and trace value used by evidence
  checkpoint traces;
- `protected_surface` trace key emitted by the authoritative-source action
  compatibility handoff.

These are active compatibility shapes, not safe rename targets for AG-95M.

## Next Cleanup Target

The next narrow target should be the post-Author recovered-visibility and final
authority citation survival handoff. That work should make FinalAnswerPacket or
final-evidence-bundle state own selected authority evidence visibility, but it
must be a separate high-custody phase because it can affect Author evidence
visibility and citation survival.
