# ScryRaven Current State

Status: current-state redirect stub refreshed after PR #317 on main `4416cbc`.

This file used to contain a long Controller-era rollup under a current-looking
filename. That body is preserved as historical record at
`docs/architecture/historical/SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md`.

For current authority doctrine and Codex routing, read:

- `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md`
- `docs/architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md`
- `docs/architecture/AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md`

Current summary:

- ScryRaven is the public project name.
- RunAuthority / RunKernel is the current authority direction.
- `core/pipeline_orchestrator.py` is a coordination shell with remaining
  authority debt.
- In ordinary product behavior phases the orchestrator may be closed for scope
  safety.
- In orchestrator-strangulation phases the orchestrator is a licensed target
  surface.
- `pipeline_orchestrator.py` line delta `0` is a scope-control fact, not
  architecture success.
- Recent main includes PR #312 guarded blocked-FAP Author input derivation,
  PR #313 safe blocked-FAP failure observability summaries, PR #314
  component-level blocked-FAP summary telemetry for blocked semantic
  multipart/source-bound numeric cases, PR #315 offline ComponentPlan /
  component executor contract preservation into passive SearchWork/query-work
  and scorekeeping surfaces, and PR #317 RunKernel-owned passive
  AnswerContractAuthorityMap. PR #318 completes ComponentSearchPlan naming and
  subordination cleanup without runtime SearchExecutor wiring.
- The current next implementation target is the Offline SearchExecutor bridge.
- No live validation is part of the current posture.
- AnswerContractAuthorityMap owns answer-component authority mapping.
- ComponentPlan is legacy/compat input terminology; ComponentSearchPlan is the
  preferred subordinate component-search planning name.
- ComponentPlan / ComponentSearchPlan are useful but passive and subordinate;
  they do not decide answerability, source-obligation satisfaction, final
  readiness, citation eligibility, or Author handoff.
