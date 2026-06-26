# ScryRaven Current State

Status: current-state redirect stub refreshed for PR #319 /
`AG-OFFLINE-SEARCH-EXECUTOR-BRIDGE-01`.

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
  and scorekeeping surfaces, PR #317 RunKernel-owned passive
  AnswerContractAuthorityMap, and PR #318 ComponentSearchPlan naming and
  subordination cleanup. PR #319 / AG-OFFLINE-SEARCH-EXECUTOR-BRIDGE-01
  completes the offline RunKernel-owned SearchExecutor bridge.
- The completed Offline SearchExecutor bridge is offline and inert, does not
  perform live provider/search/fetch/read/retrieval work, does not admit
  EvidenceLedger custody or satisfy source obligations, keeps candidate
  observations non-evidence, and is not user-facing runtime search.
- The next gate is AG-COMPONENT-SCOPED-SOURCE-CUSTODY-01, which should consume
  bridge observations for EvidenceLedger component-scoped source requirements,
  candidate links, custody gaps, and satisfied/unsatisfied source-obligation
  state.
- No live validation is part of the current posture.
- AnswerContractAuthorityMap owns answer-component authority mapping.
- ComponentPlan is legacy/compat input terminology; ComponentSearchPlan is the
  preferred subordinate component-search planning name.
- ComponentPlan / ComponentSearchPlan are useful but passive and subordinate;
  they do not decide answerability, source-obligation satisfaction, final
  readiness, citation eligibility, or Author handoff.
