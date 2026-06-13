# AG-95N/O/P Final Authority Visibility, Recovery Decision, Projection Burn-Down

Status: implemented as offline runtime/test/doc cleanup. No live ScryRaven or
proplex provider, model, search, retrieval, secrets, `.env`, raw traces, DB
rows, caches, local output packets, raw prompts, or raw provider payloads.

## Checklist

- N: collapsed post-Author recovered visibility/citation handoff into
  FinalEvidenceBundle and FinalAnswerPacket-facing helpers.
- O: audited ControllerRecoveryDecision/provider allocation; retained only for
  diagnostic/provider-review compatibility.
- P: kept touched trace/export/report/projection surfaces observer-only.

## Deleted/Replaced

- Deleted pipeline post-final reads of `recovered_visibility_used` and
  `recovered_visibility_missing_source_class`.
- Replaced pipeline selected-authority visibility/citation survival assembly
  with bundle-consuming helpers in `final_authority_citation_survival`.
- Replaced pipeline post-final source-class telemetry/bridge assembly with
  `build_post_final_source_class_projection_handoff(...)`.
- Compressed stale AG-95A demolition-plan sprawl into a routing stub.

## Preserved

- Source-class dispatch still consumes `AuthorityLifecycle.recovery_action` in
  `SourceClassRecoveryRunner`.
- ControllerRecoveryDecision remains in the runner/provider-allocation lane only
  for bounded provider-review compatibility.
- Final authority citation survival guard behavior is unchanged.
- Trace/export/report projections observe state and do not manufacture absent
  recovery decisions.

## Owner/Consumer

- Recovered visibility handoff owner: `FinalEvidenceBundle`.
- Final evidence/citation compatibility owner: `FinalAnswerPacket`.
- Runtime consumers: Author evidence attachment, citation-survival observation,
  post-final EvidenceLedger reduction, and post-author projection packaging.
- Old path retirement: pipeline compatibility reads deleted; provider-review
  ControllerRecoveryDecision path scheduled behind a future canonical action.

## LOC Impact

- `core/pipeline_orchestrator.py`: +30/-131, net -101.
- Runtime: +342/-134, net +208.
- Tests: +85/-2, net +83.
- Docs: +116/-429, net -313.
- Total: +543/-565, net -22.

## Behavior And Validation

Behavior preserved: provider routing/selection, query generation, ranking,
filtering, search depth, Author prose, final-answer posture, citation policy,
persistence shape, and live behavior.

Focused pytest batch passed: 113 tests covering final bundle visibility,
citation survival, projection handoff, recovered visibility, FinalAnswerPacket,
recovery dispatch, provider allocation, visibility export, and trace/session
projection. Final ruff result is recorded in the phase bundle.

## Blocker, SCRY-02, Next

Blocker: deleting ControllerRecoveryDecision/provider allocation would change
bounded provider-review behavior until RunAuthority/QueryPlan owns a canonical
provider-review action.

SCRY-02 active naming inventory: `proplex`, `python -m proplex`, `PROPLEX_*`,
`proplex.db`, and `proplex_*` remain compatibility names; historical
ProPlex/FauxPlex/Foplex references were preserved.

Next target: canonical provider-review allocation action, then retire
ControllerRecoveryDecision from provider-allocation inputs and downstream
allocation-result custody projections.
