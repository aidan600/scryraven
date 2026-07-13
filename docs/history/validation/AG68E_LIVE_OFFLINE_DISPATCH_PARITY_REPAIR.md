Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG68E_LIVE_OFFLINE_DISPATCH_PARITY_REPAIR).

# AG-68E Live/Offline Dispatch Parity Repair

Scope: offline parity repair only. No live ProPlex run, provider/model/search
call, provider routing, provider selection, provider depth,
retrieval/ranking/filtering behavior, query wording, prompt behavior,
citation/final-answer behavior, Author, Analyst, Economist, Scrutineer,
follow-up, or legal-answer behavior was changed.

> Status note, AG-95E: This document records historical
> Controller/ControllerLoopSpine-era behavior. For current source-class recovery
> dispatch, use AG-95C/AG-95D/AG-95E:
> `SourceClassRecoveryRunner` dispatches from canonical
> `authority_lifecycle.recovery_action`; `authorized_spine_action`,
> ControllerLoopSpine, and ControllerRecoveryDecision are
> diagnostic/compatibility surfaces for source-class dispatch, not runner
> authority.

## Purpose

AG-68E investigated why AG-68C offline dispatch tests passed while the AG-68D
live forced corridor still reported:

```text
admission_used=true
source_class_recovery_eligible=true
source_class_recovery_used=false
source_class_recovery_execution_attempted=false
next_failure_layer=execution_not_attempted
```

## Diagnosis

The parity gap was in checkpoint reason handling.

AG-68C's synthetic helper used an unavailable checkpoint with:

```text
reason=checkpoint_unavailable
```

The controller spine explicitly allowed the official/canonical admitted
fallback through that reason. The live/product exception path can carry:

```text
reason=checkpoint_exception
```

That reason was not included in the same licensed official/canonical fallback,
so the live/product path could remain admitted and eligible but still fail to
authorize the source-class recovery executor.

## Repair

The product path now annotates a checkpoint exception with the explicit runtime
control fact
`official_canonical_checkpoint_exception_fallback_allowed=true` only after the
authoritative-source action handoff has admitted official/canonical recovery
and the answer-contract handoff object is structurally present. The controller
spine treats `checkpoint_exception` as fallback-eligible only when that control
fact is present. The fallback still requires:

- no terminal stop;
- eligible source-class recovery lifecycle;
- `active_source_class_recovery_official_canonical_admitted=true`;
- an approved explicit controller action envelope;
- no competing checkpoint action.

This preserves the controller rule: controller decides, orchestrator executes.
The repair does not use trace/projection-only fields as control inputs.
Checkpoint exceptions without this explicit control fact remain fail-closed.

## Product-Path Parity Proof

The AG-68E fixture drives the live-equivalent control chain:

```text
authoritative-source action result
-> orchestrator adapter handoff
-> controller loop spine
-> product executor call-site condition
-> execute_source_class_recovery_action with injected offline search
```

The repaired fixture proves:

```text
admission_used=true
source_class_recovery_eligible=true
recovery queries visible
authorized_dispatch=recover_missing_source_class
source_class_executor_dispatched=true
source_class_recovery_execution_attempted=true
```

The AG-68E tests also preserve:

- ordinary authoritative acquisition remains ordinary only;
- terminal stops remain fail-closed;
- invalid action envelopes remain fail-closed;
- weak-corpus ownership remains fail-closed;
- public forced-corridor helper shapes remain stable;
- the pipeline source-class executor call site remains a single tiny gate.

## Changed Files

```text
core/controller_loop_spine.py
core/pipeline_orchestrator.py
tests/test_controller_loop_spine.py
tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py
docs/history/validation/AG68E_LIVE_OFFLINE_DISPATCH_PARITY_REPAIR.md
```

## Validation

Focused tests passed with external pytest basetemps and cache disabled where
used:

```text
py -m pytest tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py
py -m pytest tests/test_controller_loop_spine.py
py -m pytest tests/test_source_class_recovery_dispatch_execution_ag68c.py
py -m pytest tests/test_authoritative_source_forced_corridor_live_reclassification_ag68d.py
py -m pytest tests/test_authoritative_source_forced_corridor_live_reclassification_ag68b.py
py -m pytest tests/test_official_canonical_admission_path_visibility_ag68a.py
py -m pytest tests/test_authoritative_source_named_action_extraction.py
py -m pytest tests/test_ag64abc_controller_owned_official_current_recovery.py
py -m pytest tests/test_source_class_recovery_lifecycle.py tests/test_source_class_recovery_executor.py tests/test_source_class_recovery_controller.py
py -m pytest tests/test_official_canonical_recovery_query_acquisition_ag50a.py tests/test_official_canonical_recovery_execution_admission_ag50b.py tests/test_official_canonical_recovery_execution_dispatch_ag50d.py
py -m pytest tests/test_ag17_recovered_evidence_visibility.py tests/test_source_class_recovery_trace.py tests/test_source_class_recovery_diagnostics_l1.py
py -m pytest tests/test_authoritative_source_obligations.py tests/test_authoritative_source_answer_contract_projection.py tests/test_authoritative_source_recovery_delegation.py
py -m pytest tests/test_authoritative_source_official_canonical_adapter_migration.py tests/test_authoritative_source_followup_numeric_migration.py tests/test_legal_current_authority_fit_adapter.py
py -m ruff check core tests docs
git diff --check
```

## Next Step

AG-68F should run one bounded forced-corridor live classification to verify
whether the repaired live/product parity path now reaches
`source_class_recovery_execution_attempted=true`. Provider/search review remains
closed until a live forced corridor proves dispatch executes and then fails to
acquire authoritative candidates.
