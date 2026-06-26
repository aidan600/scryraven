# ScryRaven Current State

Status: current-state redirect stub refreshed for
`AG-COMPONENT-EVIDENCE-CITATION-BINDING-01`.

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
  completed the offline RunKernel-owned SearchExecutor bridge.
- The completed Offline SearchExecutor bridge is offline and inert, does not
  perform live provider/search/fetch/read/retrieval work, does not admit
  EvidenceLedger custody or satisfy source obligations, keeps candidate
  observations non-evidence, and is not user-facing runtime search.
- PR #320 / AG-COMPONENT-SCOPED-SOURCE-CUSTODY-01 adds EvidenceLedger
  component-scoped source custody from offline bridge output. Candidate links
  remain non-evidence until fetched/read/admitted by a later phase, and source
  obligations are unsatisfied/pending rather than satisfied by candidate
  presence.
- AG-COMPONENT-EVIDENCE-CITATION-BINDING-01 extends the existing
  AnswerContractAuthorityMap per-component binding status to consume
  EvidenceLedger component-scoped custody. Offline candidate links and custody
  gaps appear as component-specific blockers, but custody/candidate presence
  does not bind evidence, citations, source obligations, answer values,
  readiness, partial answer authority, or Author handoff. The post-merge next
  gate is AG-SUFFICIENCY-FAP-COMPONENT-READINESS-01.
- No live validation is part of the current posture.
- AnswerContractAuthorityMap owns answer-component authority mapping.
- ComponentPlan is legacy/compat input terminology; ComponentSearchPlan is the
  preferred subordinate component-search planning name.
- ComponentPlan / ComponentSearchPlan are useful but passive and subordinate;
  they do not decide answerability, source-obligation satisfaction, final
  readiness, citation eligibility, or Author handoff.
