Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG95L_PIPELINE_PRODUCT_CALLSITE_COMPATIBILITY_READ_DIET).

# AG-95L Pipeline Product-Callsite Compatibility Read Diet

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

`core/pipeline_orchestrator.py` may coordinate product callsites, but it must not
rebuild source-class recovery authority from flattened compatibility booleans,
old action envelopes, or stale admission summaries.

## Pipeline Consumer Inventory

| Pipeline consumer | Previous read | AG-95L disposition |
| --- | --- | --- |
| `_targeted_retrieval_currentness_source_fit_facts()` | `active_source_class_recovery_missing_classes`, blockers, and reason | Replaced with `authority_lifecycle.recovery_action.required_source_classes`, recovery-action reason, and canonical explicit blockers. |
| `_build_targeted_retrieval_lifecycle_from_runtime()` source-class ownership summary | `active_source_class_recovery_used` / `active_source_class_recovery_eligible` and flattened blockers | Replaced ownership with canonical recovery-action approval or attempted execution. Replaced blockers with canonical explicit blocker reasons. |
| `_authoritative_source_checkpoint_refresh_allowed()` stale checkpoint refresh | `official_canonical_recovery_execution_admitted`, `active_source_class_recovery_eligible`, and `active_source_class_recovery_action_envelope` | Replaced with canonical `authority_lifecycle.recovery_action` action type, approval, required source classes, pending execution, and canonical blockers. |
| Evidence-integration checkpoint exception fallback | `official_canonical_recovery_execution_admitted` | Replaced with canonical source-class recovery-action approval. |
| Post-final official-source obligation bridge | flattened active source-class blockers | Replaced with canonical explicit blocker reasons. |
| Post-final recovered-visibility reserve adjustment | flattened missing-class read | Replaced with canonical recovery-action required source classes while preserving the legacy output key expected by post-Author packaging. |
| Runner product callsite | `run_source_class_recovery_dispatch()` | Preserved. The runner already consumes canonical `authority_lifecycle.recovery_action`; AG-95L tests continue to prove that. |
| Author evidence and citation survival callsites | `ensure_selected_authority_evidence_visible_to_author()` and final authority citation survival projection | Preserved. These are high-custody Author/citation behavior surfaces and were inspected only to verify AG-95L did not change final-answer behavior. |

## Reads Deleted, Replaced, Or Preserved

Deleted or replaced:

- Removed the stale checkpoint refresh dependency on
  `official_canonical_recovery_execution_admitted`.
- Removed the stale checkpoint refresh dependency on
  `active_source_class_recovery_eligible`.
- Removed the stale checkpoint refresh dependency on
  `active_source_class_recovery_action_envelope`.
- Replaced source-class ownership summary reads of
  `active_source_class_recovery_used` and `active_source_class_recovery_eligible`
  with canonical recovery-action approval and execution state.
- Replaced source-class blocker, reason, and missing-class summary reads with
  canonical AuthorityLifecycle action/blocker reads.
- Rewrote AG68 product-callsite assertions away from official admission,
  eligibility, required-recovery booleans, and legacy envelope proof.
- Added `compatibility_runtime_values()` on the lifecycle adapter and moved the
  pipeline callsite to that current terminology. `legacy_runtime_values()`
  remains as a compatibility wrapper for existing consumers.

Preserved:

- `active_source_class_recovery_missing_classes` remains as a legacy output key
  in post-final handoff data. Its value now comes from canonical recovery-action
  required source classes in the touched product-callsite path.
- `recovered_visibility_used` and `recovered_visibility_missing_source_class`
  remain in the post-final visibility reserve block. That decision is tied to
  Author evidence and citation survival behavior and was not changed in this
  phase.
- `official_canonical_recovery_execution_admission_trace` remains attached as a
  compatibility trace. The pipeline no longer gates stale checkpoint refresh or
  exception fallback on the admission boolean.
- Shared ControllerLoopSpine active-gate compatibility remains for weak-corpus,
  conflict, terminal-stop, targeted retrieval, and older invariant coverage.

## High-Custody Surfaces Inspected

- Provider/search/query routing: inspected only through fake offline product
  callsite tests. No provider order, provider selection, search depth, query
  wording, ranking, or filtering behavior was changed.
- Author/citation behavior: inspected
  `core/final_authority_citation_survival.py` callsites in the pipeline and
  preserved them unchanged. No Author prompt, final-answer posture, citation
  eligibility, or citation survival behavior changed.
- Recovered-evidence visibility: inspected
  `core/recovered_evidence_visibility.py` and
  `core/authority_lifecycle_candidate_visibility.py`; preserved the visibility
  decision fields because changing them would affect post-execution evidence
  visibility/citation custody.

## Terminology Cleanup

- Replaced the pipeline callsite for `legacy_runtime_values()` with
  `compatibility_runtime_values()`.
- Updated the adjacent adapter docstring from legacy runtime values to lifecycle
  adapter compatibility runtime values.
- Kept historical method/field names where they are existing compatibility API.

## Exact Blockers

No stop-condition blocker was hit.

The deliberate preservation boundary is the post-Author recovered-visibility
decision (`recovered_visibility_used` and
`recovered_visibility_missing_source_class`). Removing that family requires a
separate FinalAnswerPacket or final-evidence-bundle ownership phase because it
can alter Author evidence visibility or citation survival behavior.

## Net LOC Impact

Runtime LOC: +121/-49, net +72.
Test LOC: +76/-88, net -12.
Docs LOC: +158/-4, net +154.
Total LOC: +355/-141, net +214.

## Validation

Focused offline check run:

```powershell
py -m pytest -q tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py tests/test_authoritative_source_named_action_extraction.py tests/test_authority_lifecycle_runtime_arbitration_ag69b.py tests/test_targeted_retrieval_runtime_ag43b.py tests/test_scout_continuation_spine_gate_ag45c.py
```

Result: 63 passed.

Additional focused check:

```powershell
py -m pytest -q tests/test_ag95e_stale_dispatch_doctrine_cleanup.py tests/test_ag95d_recovery_dispatch_sanity_audit.py tests/test_ag95f_controller_loop_spine_source_class_trace_demotion.py tests/test_authority_lifecycle_execution_ag69c.py tests/test_authority_lifecycle_candidate_visibility_ag69d.py tests/test_authoritative_source_forced_corridor_validation.py
```

Result: 56 passed.

Ruff check: `py -m ruff check .`

Result: All checks passed.

No live validation was run.

## Next Cleanup Target

Target the post-Author recovered-visibility and final authority citation survival
handoff. The goal should be to make FinalAnswerPacket or final evidence bundle
state own selected authority evidence visibility so the pipeline no longer needs
to read `recovered_visibility_*` compatibility fields after Author execution.
