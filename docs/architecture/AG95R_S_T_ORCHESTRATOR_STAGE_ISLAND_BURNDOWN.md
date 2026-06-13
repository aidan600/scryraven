# AG-95R/S/T Orchestrator Stage-Island Burn-Down

Status: completed implementation note.

## Stage Outcomes

- A: active visibility export no longer hydrates or reports
  `ControllerRecoveryDecision` fields. Provider-review visibility observes the
  canonical provider-search allocation request and execution traces instead.
- B: targeted-retrieval source-fit facts, targeted lifecycle assembly, and
  conflict-resolution lifecycle assembly moved out of
  `core/pipeline_orchestrator.py` into bounded runtime adapters.
- C: retrieval-depth policy and weak-corpus seed query construction moved out of
  the orchestrator with exact offline parity tests.
- D: pre-recovery checkpoint, source-class lifecycle, loop-spine refresh,
  targeted lifecycle, and continuation gate reconciliation now run through the
  bounded retrieval authority stage adapter.
- E: current guidance now describes RunAuthority/canonical lifecycle ownership;
  stale controller decision export tests were deleted or rewritten.

## Deleted Or Demoted Old Surfaces

- Deleted active visibility export of `controller_recovery_decision_*` fields.
- Deleted the old AG-74D ControllerRecoveryDecision compatibility test file.
- Demoted `core/controller_recovery_decision.py` to historical/offline
  diagnostic parity only; it has no active orchestrator, runner, allocation, or
  visibility-export consumer.
- Updated the decision registry coverage pointer away from the deleted AG-74D
  table test and toward current runner/export coverage.

## New Bounded Modules

- `core/retrieval_depth_policy.py`
- `core/weak_corpus_recovery_queries.py`
- `core/targeted_retrieval_runtime_adapter.py`
- `core/conflict_resolution_runtime_adapter.py`
- `core/retrieval_authority_stage.py`

These modules are deterministic adapters over existing runtime facts. They do
not call providers or models, assemble prompts, select providers, choose
citations, rank evidence, write persistence, or decide final-answer posture.

## LOC Delta

- `core/pipeline_orchestrator.py`: 4485 -> 3794, delta -691.
- Runtime files: net +24 LOC.
- Tests: net -176 LOC.
- Docs: net +79 LOC including this note.
- Total repo delta for this phase: net -73 LOC.

## Behavior Preserved

- Provider/search/query/routing/depth behavior preserved; no live validation was
  run.
- Weak-corpus seed query order and near-previous-query suppression are pinned by
  parity tests.
- Targeted retrieval, conflict, loop-spine/checkpoint, source-class runner,
  provider allocation, export, and runtime projection focused suites passed.

## Blockers

- None for this phase. Further extraction should stop before Author prose,
  citation policy, final evidence selection, provider choice, routing policy, or
  query text changes unless explicitly licensed.

## SCRY-02 Inventory

- Active compatibility names intentionally preserved: `proplex`,
  `python -m proplex`, `PROPLEX_*`, `proplex.db`, and `proplex_*` state keys.
- Historical ProPlex/FauxPlex/Foplex references remain historical record; one
  current-looking prompt docstring was updated to ScryRaven.

## Next Target

Extract the next remaining final-evidence/Author handoff packaging surface only
after parity tests pin citation identity, source ordering, and final evidence
selection behavior.
