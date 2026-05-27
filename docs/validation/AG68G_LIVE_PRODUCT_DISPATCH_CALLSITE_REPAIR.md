# AG-68G Live Product Dispatch Call-Site Repair

Scope: offline live-equivalent product dispatch repair only. No live ProPlex
run, provider/model/search call, provider routing, provider selection,
provider depth, retrieval/ranking/filtering behavior, query wording, prompt
behavior, citation/final-answer behavior, Author, Analyst, Economist,
Scrutineer, follow-up, or legal-answer behavior was changed.

## Purpose

AG-68G investigated the AG-68F SSA forced-corridor shape:

```text
admission_used=true
source_class_recovery_eligible=true
source_class_recovery_used=false
source_class_recovery_execution_attempted=false
candidate_return_status=not_attempted
next_failure_layer=execution_not_attempted
```

The phase used the SSA official/current numeric-rule corridor as the primary
offline repair target because it isolates admitted and eligible source-class
recovery that still did not reach the product executor call site.

## Diagnosis

The live/product path can decide an evidence-integration checkpoint before the
authoritative-source action handoff has recorded the admitted source-class
recovery lifecycle. Those earlier continuation gates used the default
source-class lifecycle, so a stale checkpoint such as `retrieve_targeted` could
remain the product call-site control input even after the later
authoritative-source handoff produced:

```text
official/canonical recovery admitted
active_source_class_recovery_eligible=true
active_source_class_recovery_action_envelope.allowed_action=true
recovery queries visible
```

The result was a product-path divergence: the controller/action lifecycle was
ready, but the executor call site still saw a checkpoint action that did not
authorize `recover_missing_source_class`.

## Repair

`pipeline_orchestrator.py` now refreshes a previously decided checkpoint only
when all of these explicit runtime-control facts are true:

- official/canonical recovery execution is admitted;
- the active source-class recovery lifecycle is eligible;
- the lifecycle contains an approved `recover_missing_source_class` action
  envelope with at least one required source class;
- the existing checkpoint is not a terminal stop;
- the lifecycle is not blocked by weak-corpus ownership, corpus weakness, or a
  terminal-stop blocker.

The refreshed checkpoint is rebuilt through the existing
`_build_evidence_integration_snapshot_from_runtime` and
`decide_evidence_integration_checkpoint` path. The product call site still
executes the existing `execute_source_class_recovery_action` only when the
controller spine authorizes `RECOVER_MISSING_SOURCE_CLASS`.

This does not use trace/projection-only fields as dispatch inputs.

## Offline Product-Path Proof

The AG-68G fixture drives the live-equivalent product chain:

```text
authoritative-source action/orchestrator adapter
-> stale product checkpoint
-> controller loop spine
-> refreshed checkpoint with admitted lifecycle
-> product executor call-site condition
-> execute_source_class_recovery_action with injected offline search
```

It proves the SSA-style path now reaches:

```text
admission_used=true
source_class_recovery_eligible=true
controller spine authorizes recover_missing_source_class
source_class_recovery_execution_attempted=true
source_class_recovery_used=true
captured recovery queries unchanged
```

## Preserved Behavior

- IRS-style weak-corpus ownership remains fail-closed.
- Terminal stop checkpoints remain fail-closed.
- Invalid lifecycle action envelopes do not trigger checkpoint refresh.
- Checkpoint exception refresh is not allowed without official/canonical
  admission.
- Ordinary authoritative acquisition remains ordinary only and does not count
  as source-class recovery success.
- Public forced-corridor helper shapes remain stable.
- Provider/search review remains closed until a bounded live classification
  proves dispatch executes and acquisition then fails.

## Changed Files

```text
core/pipeline_orchestrator.py
tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py
docs/validation/AG68G_LIVE_PRODUCT_DISPATCH_CALLSITE_REPAIR.md
```

## Validation

Focused and relevant offline tests passed. The AG-17/source-class trace group
required an external Windows basetemp because the repo-local `.pytest-tmp`
directory hit a permission cleanup error on first attempt.

```text
py -m pytest -p no:cacheprovider tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py
py -m pytest -p no:cacheprovider tests/test_authoritative_source_two_case_live_reclassification_ag68f.py
py -m pytest -p no:cacheprovider tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py
py -m pytest -p no:cacheprovider tests/test_source_class_recovery_dispatch_execution_ag68c.py
py -m pytest -p no:cacheprovider tests/test_authoritative_source_forced_corridor_live_reclassification_ag68d.py
py -m pytest -p no:cacheprovider tests/test_authoritative_source_forced_corridor_live_reclassification_ag68b.py
py -m pytest -p no:cacheprovider tests/test_official_canonical_admission_path_visibility_ag68a.py
py -m pytest -p no:cacheprovider tests/test_authoritative_source_named_action_extraction.py
py -m pytest -p no:cacheprovider tests/test_ag64abc_controller_owned_official_current_recovery.py
py -m pytest -p no:cacheprovider tests/test_controller_loop_spine.py
py -m pytest -p no:cacheprovider tests/test_source_class_recovery_lifecycle.py tests/test_source_class_recovery_executor.py tests/test_source_class_recovery_controller.py
py -m pytest -p no:cacheprovider tests/test_official_canonical_recovery_query_acquisition_ag50a.py tests/test_official_canonical_recovery_execution_admission_ag50b.py tests/test_official_canonical_recovery_execution_dispatch_ag50d.py
py -m pytest -p no:cacheprovider --basetemp C:\tmp\ag68g_pytest_tmp tests/test_ag17_recovered_evidence_visibility.py tests/test_source_class_recovery_trace.py tests/test_source_class_recovery_diagnostics_l1.py
py -m pytest -p no:cacheprovider tests/test_authoritative_source_obligations.py tests/test_authoritative_source_answer_contract_projection.py tests/test_authoritative_source_recovery_delegation.py
py -m pytest -p no:cacheprovider tests/test_authoritative_source_official_canonical_adapter_migration.py tests/test_authoritative_source_followup_numeric_migration.py tests/test_legal_current_authority_fit_adapter.py
```

## Next Step

AG-68H should run a bounded forced-corridor live classification with at most two
runs: the SSA admitted-and-eligible corridor and, if useful, the IRS corridor to
confirm weak-corpus ownership remains classified separately.
