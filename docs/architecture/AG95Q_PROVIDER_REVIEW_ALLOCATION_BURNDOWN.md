# AG-95Q Provider-Review Allocation Burndown

Status: implemented as offline runtime/test/doc cleanup. No live ScryRaven or
proplex provider, model, search, retrieval, secrets, `.env`, raw traces, DB
rows, caches, local output packets, raw prompts, or raw provider payloads.

## Before

- Provider-review allocation was runtime-gated by
  `ControllerRecoveryDecision == request_provider_search_review`.
- `pipeline_orchestrator.py` built that decision and passed it into
  `SourceClassRecoveryRunner`.
- Allocation custody admitted only `allocation_owner == "ControllerRecoveryDecision"`.
- Runner tests asserted ControllerRecoveryDecision executor projections.

## After

- New owner: `RunAuthorityProviderReviewAllocation`, derived from canonical
  RunAuthority/SearchJudgment-fed lifecycle state.
- Runtime consumer: `SourceClassRecoveryRunner` calls
  `record_provider_search_allocation_if_authority_authorized(...)`, which builds
  the provider-review request from lifecycle state.
- Existing provider/query/depth inputs still come from the existing
  source-class recovery action and runner execution context.
- `ControllerRecoveryDecision` remains diagnostic/export compatibility only; its
  stale `to_executor_trace_fields()` projection was deleted.

## Deleted Or Demoted

- Deleted pipeline `build_controller_recovery_decision(...)` import/call.
- Deleted runner `controller_recovery_decision` context field/read.
- Deleted `ControllerRecoveryDecision.to_executor_trace_fields()`.
- Demoted old allocation owner literals, trace modes, schema names, static
  guards, registry entries, and tests to canonical provider-review wording.

## Behavior Preserved

- No provider routing, provider choice, query text, ranking/filtering, search
  depth, Author prose, citation policy, final-answer posture, persistence shape,
  or live behavior was intentionally changed.
- Bounded provider-review execution still uses existing source-class recovery
  queries/provider role/depth and sanitized result summaries.
- Allocation custody still does not satisfy official/current obligations or
  mutate final evidence/citations by itself.

## LOC Deltas

- Runtime: +256/-108, net +148.
- Tests: +90/-151, net -61.
- Registry: +12/-12, net 0.
- Docs including this note: +84/-8, net +76.
- `core/pipeline_orchestrator.py`: +0/-4, net -4.
- Total including this note: +442/-279, net +163.

## Blockers And SCRY-02

- Blocker: total net LOC is positive because the canonical request checks are
  now explicit in `controller_provider_search_allocation.py`; further reduction
  should extract only if another consumer appears.
- SCRY-02 inventory unchanged: `proplex`, `python -m proplex`, `PROPLEX_*`,
  `proplex.db`, and `proplex_*` remain active compatibility names.

## Next Target

- Retire remaining ControllerRecoveryDecision provider-review diagnostic/export
  fields after visibility-export tests can observe canonical provider-review
  request fields directly.
