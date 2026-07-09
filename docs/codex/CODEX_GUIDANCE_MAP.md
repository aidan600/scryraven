# Codex Guidance Map

Status: Task-specific routing map for future Codex tasks
Suggested repo path: `docs/codex/CODEX_GUIDANCE_MAP.md`

Repo-root `AGENTS.md` is the always-loaded standing instruction file for
ScryRaven tasks. Use this map to choose the smallest relevant task-specific
guidance surface before starting a phase. Do not assume ChatGPT Project Sources
are repo files; use repo-visible files and the current phase prompt.

## Start here for ordinary work

- **Ordinary setup, tests, UI, docs, and bounded implementation:** read
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- **Reusable phase prompt shape:** read
  [PHASE_BRIEF_TEMPLATE.md](PHASE_BRIEF_TEMPLATE.md).
- **Capability inventory / reuse-first gate:** before implementing new code,
  phases touching mature authority or product surfaces must use the inventory
  table in [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md)
  and [PHASE_BRIEF_TEMPLATE.md](PHASE_BRIEF_TEMPLATE.md), classify each
  relevant surface as `REUSE`, `ADAPT`, `UPGRADE`, `RETIRE`, or `REPLACE`, and
  stop for inventory if an existing current capability may already own the
  responsibility. This applies especially near D-prime / DPrime, Analyst /
  EvidenceRelativeAnalysisPacket, source authority/obligation, citation
  eligibility or citation-source handoff, SufficiencyReadiness, FAP, Author,
  SemanticObservation, ComponentCoverage, RunKernel authority, follow-up /
  recovery, SearchPlanner/query planner/model-assisted planning,
  FastModel/SmartModel, Scrutineer, multi-source, multi-component,
  EvidenceLedger, fetch/read, provider acquisition, evidence triage, and
  source/answer gateway readiness. Generic dogfood, query-planning, and
  provider-acquisition phases must also inventory the current generic
  single-relation dogfood path before implementation.
- **Local Windows sandbox and publication rule:** read
  [CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md](CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md).
  Codex edits and tests in the workspace sandbox; exact-approved Git commands
  publish.
- **Provider-related phase classification:** every phase touching provider
  acquisition, provider runtime wiring, broker/doorman scripts, or provider
  record capture must classify itself as exactly one of
  `product provider/runtime integration` or
  `testing/operator broker-doorman work`. Product provider/runtime integration
  phases close broker/doorman scripts except as explicitly licensed test
  fixtures; the ordinary product path must use a product-owned provider
  adapter/service or fail closed with a product-provider-route blocker, and the
  broker/doorman must not become the default runtime provider route.
  Testing/operator broker-doorman phases close ordinary product behavior files;
  broker output remains sanitized provider-record material only and is not
  source custody, evidence, citation eligible, source-obligation satisfaction,
  or answer material.
- **Generic provider-proxy broker operator flow:** read
  [../operator/GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md](../operator/GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md)
  and [../operator/BROKER_REACTIVATION_RUNBOOK.md](../operator/BROKER_REACTIVATION_RUNBOOK.md)
  when a phase separately licenses a trusted-local brokered provider call.
  The reusable helper is `scripts/run_provider_proxy_broker_once.py`; it starts
  the private broker locally, generates a temporary token, delegates to the
  generic client, writes sanitized output under `output/`, and stops the broker.
  Sanitized broker output is not source custody, evidence, citation eligible,
  or source-obligation satisfaction; bounded `provider_extracted_text` remains
  provider record material until a downstream product path admits it under its
  own custody/readability/candidate-fit gates.
- **Proof class and actual app delta questions:** read
  [PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md](PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md).
- **Current path registry and quarantine classifications:** read
  [../architecture/AG_CURRENT_PATH_QUARANTINE_01.md](../architecture/AG_CURRENT_PATH_QUARANTINE_01.md)
  when a phase needs to distinguish current authority path, passive/supporting
  projections, fixture-only proof, offline harnesses, live-search-only
  validation, product-facing dry-run proof, legacy/historical surfaces, and
  closed surfaces.
- **Validation buckets, high-custody tiers, and timeout reporting:** read
  [VALIDATION_BUCKETS.md](VALIDATION_BUCKETS.md) and
  [CI_VALIDATION_ERGONOMICS.md](CI_VALIDATION_ERGONOMICS.md). Choose the
  smallest valid bucket, report the exact command, and do not run full pytest
  unless the phase requires it. Use `semantic_lane` for durable semantic
  producer/reducer/sufficiency validation and `semantic_search_lane` for
  SearchJudgment/QueryPlan semantic-gap consumer validation.
- **Test additions, promotions, demotions, or retirements:** read
  [TEST_CLASSIFICATION_LIBRARY.md](TEST_CLASSIFICATION_LIBRARY.md) and
  [VALIDATION_BUCKETS.md](VALIDATION_BUCKETS.md). Classify new tests before
  adding them to permanent bucket manifests.
- **Developer commands and project overview:** read the repo `README.md`,
  `.github/workflows/ci.yml`, `scripts/check.ps1`, `scripts/test.ps1`,
  `scripts/lint.ps1`, `pytest.ini`, `ruff.toml`, and `.pre-commit-config.yaml`
  as relevant to the task.

## Current Productization Posture

Current compact posture: PR #352 current-path quarantine is complete, PR #353
fixture dogfood AuthorProse packets are complete, PR #354 partial scenario
contract-origin repair is complete, and PR #355 ordinary-query local dry-run to
AuthorProse is complete. The next gate is tightly scoped limited live validation,
not another proof layer. Build / Proof / Repair mode must be declared in phase
briefs: Build is the default product-moving mode, Proof is an exception that
requires NO-BUT-JUSTIFIED plus a mandatory next Build checkpoint, and Repair
must fix a named integrity defect.

Historical baseline, not current posture: ScryRaven was post-PR #342 /
post-AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01. That completed baseline
included the earlier offline X-axis proof through blocked FAP / Author handoff,
a coherent front half through SearchExecutorHandoff, and the semantic-coverage
packet chain through ComponentCoverage reliability proof:

```text
SearchPlanner
-> initial_answer_contract
-> Scout
-> SearchPlannerRevision
-> amendment admission/application
-> current_answer_contract
-> SearchExecutorHandoff
```

RunKernel / RunAuthority remains the root authority. AnswerContractAuthorityMap
owns the answer-component authority mapping. ComponentPlan is legacy/compat
input terminology for subordinate component-search planning; ComponentSearchPlan
is the preferred subordinate name. ComponentPlan, ComponentSearchPlan,
SearchWork, QueryPlan, and SearchExecutorHandoff are work-description or
handoff surfaces only; they do not decide answerability, source-obligation
satisfaction, final readiness, citation eligibility, partial-answer readiness,
or Author handoff.

`AG_CURRENT_PATH_QUARANTINE_01.md` is the current registry for proof class,
consumer seams, current/legacy/passive/closed status, old-path treatment,
human-reviewable output posture, explicit non-proofs, and live-validation
status. It is quarantine/classification only and does not prove product
behavior.

Historical completed baseline retained for context: PR #318 completed
ComponentSearchPlan naming / subordination cleanup; PR #319 /
AG-OFFLINE-SEARCH-EXECUTOR-BRIDGE-01 completed the offline RunKernel-owned
SearchExecutor bridge and completed offline SearchExecutor bridge scaffolding;
PR #320 adds EvidenceLedger component-scoped source custody;
AG-COMPONENT-EVIDENCE-CITATION-BINDING-01 extends component
evidence/citation binding; PR #322 completed SufficiencyJudgment and
FinalAnswerPacket component readiness; and PR #323 completed the offline X-axis
end-to-end proof through blocked FAP / Author handoff.
The historical Offline SearchExecutor bridge is offline and inert, does not
perform live provider/search/fetch/read/retrieval work, does not admit
EvidenceLedger custody or satisfy source obligations, keeps candidate
observations non-evidence, and is not user-facing runtime search.

`SearchExecutorHandoff` consumes `current_answer_contract` when present and
creates offline executable search intent only: query-intent records, search-task
records, and a search work packet. It does not perform live provider/search/
fetch/read/retrieval work, admit EvidenceLedger custody, create citations,
satisfy source obligations, decide Sufficiency, prepare a FinalAnswerPacket,
create Author input, or prove product correctness.

SearchExecutorHandoff exact posture: PR #330 / AG-SEARCH-EXECUTOR-HANDOFF-01; handoff consumes current_answer_contract when present; Scout/revision material is search direction only; handoff creates search task records and a search work packet; no live search/provider/fetch/read/retrieval calls were run; no EvidenceLedger/citations/source-obligation satisfaction; next implementation gate after AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01 is AG-LIVE-XAXIS-VALIDATION-01A.
Historical SearchPlannerRevision exact posture: PR #329 / AG-SEARCH-PLANNER-REVISION-01; planner revision consumes Scout report; planner revision emits passive amendment candidates; Scout hints remain non-evidence, non-citation, and non-source-obligation satisfaction; current_answer_contract changes only through existing admission/application path; SearchExecutor, fetch/read/retrieval remain closed; post-merge next gate was AG-SEARCH-EXECUTOR-HANDOFF-01.
Historical Scout exact posture: PR #327 / AG-SEARCH-PLANNER-MODEL-01; AG-SCOUT-DISAMBIGUATION-RUNTIME-01; RunKernel-authorized; report-only; Serper-shaped; fake injected adapters only; No live Serper/search/provider/model/fetch/read/retrieval calls were run; Scout hints are not evidence; not citations; not source-obligation satisfaction; Scout does not mutate contracts; Scout does not revise planner output; post-merge next gate is AG-SEARCH-PLANNER-REVISION-01.
Historical SearchPlannerModel exact posture: PR #327 / AG-SEARCH-PLANNER-MODEL-01; AG-SEARCH-PLANNER-RUNTIME-01; AG-SEARCH-PLANNER-MODEL-01 adds an explicit injected fail-closed model adapter; No live model calls or live validation were run; AG-SCOUT-DISAMBIGUATION-RUNTIME-01; Scout hints are not evidence; post-merge next gate is AG-SEARCH-PLANNER-REVISION-01.
SearchPlanner runtime exact posture: AG-SEARCH-PLANNER-RUNTIME-01 completes the
merge-stable planner runtime posture; AG-SEARCH-PLANNER-MODEL-01 remains an
explicit injected fail-closed model-adapter boundary; no live model/search/
provider/fetch/read/retrieval calls are implied by that completion.

`AG-LIVE-XAXIS-VALIDATION-01A` PR1 introduced the RunKernel-owned
search-only validation seam. It consumes `current_answer_contract` plus
`SearchExecutorHandoff` directly and produces sanitized `SearchResultCandidate`
records only from injected fake-provider results. PR2 adds broker/direct
invocation scaffolding only: shared request/cap/output schema, provider
allowlist, sanitized candidate normalizer, redaction posture, inert wrappers,
and the same RunKernel reduction path. Durable broker contact should use the
generic provider-proxy contract, not a phase-specific broker job. PR2 does not
run live validation, call a broker, call providers, fetch/read, retrieve, admit
EvidenceLedger custody, create citations, satisfy source obligations, decide
Sufficiency, create FinalAnswerPacket state, create Author input/prose, make
partial-answer readiness claims, or claim product correctness unless a later
phase separately licenses it.
`AG-LIVE-XAXIS-VALIDATION-01A-LIVE-RUN-01` adds an inert trusted-local harness
that prepares the repo-visible request packet and optional broker envelope from
deterministic current-contract plus SearchExecutorHandoff state. When actual
provider contact is separately licensed, the harness should use the generic
provider-proxy broker contract and separately supplied sanitized provider-result
JSON, not a phase-specific broker job. It can reduce sanitized provider-result
JSON through the existing RunKernel path, but it does not call providers, call a
broker, load `.env`, read secrets, fetch/read, retrieve, admit evidence, create
citations, decide Sufficiency, create FinalAnswerPacket state, create Author
input/prose, make partial-answer readiness claims, or claim product correctness.

`broker_invoked` and `live_provider_called` are PR2 execution facts, not
downstream closed-surface flags or evidence/readiness authority. Raw provider
payload and raw search response retention remain false in all modes.

Generic broker operator flow after BROKER-OPERATOR-FLOW-01: use
`scripts/run_provider_proxy_broker_once.py` for future separately licensed
trusted-local provider-proxy calls. The helper and broker contract remain
provider/operation/query/max_results only. Future task-specific harnesses, such
as LIVE-RUN-01, map the returned sanitized generic results after the broker
returns. That mapping does not belong inside the broker.

`provider_preference_hint` is only a hint. Live provider authority must come from
an explicit RunKernel-authorized validation action. Existing provider wrappers
in `core/search_providers.py`, including Serper, may be reused only behind a
new governed live-search-validation adapter. `core/offline_search_executor_bridge.py`
is legacy/offline scaffolding for the old X-axis proof path and should be
demoted, retired, or ignored for the new handoff-consuming live path.

The current second-half semantic-coverage chain is:

```text
SearchResultCandidatePacket
-> FetchReadContentPacket / SanitizedContentReference
-> EvidenceLedger custody
-> EvidenceRelativeAnalysisPacket / AnalystReport
-> FollowupSearchIntentPacket / AnalysisGapSearchProposal
-> ComponentCoverage reliability proof
-> SemanticObservation admission bridge
-> ComponentCoverage reduction
-> AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01 first governed remediation loop
-> AG-SCRUTINEER-REVIEW-01 ScrutineerReview
-> AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01 Specialist source-bound calculation
-> AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01 SufficiencyReadiness
-> AG-FINAL-ANSWER-PACKET-HARDENING-01 hardened FinalAnswerPacket handoff
-> AUTHOR-PROSE-ONLY-FINALIZATION-01 AuthorProseFinalization prose surface
```

`SearchResultCandidatePacket` is now the durable non-evidence candidate handoff
before fetch/read. It preserves sanitized live-search candidate lineage, but
search candidates are not evidence, not citation-eligible, and the packet does
not satisfy source obligations.
`FetchReadContentPacket` / `SanitizedContentReference` is the bounded
readable-content handoff after `SearchResultCandidatePacket` and before
EvidenceLedger custody; it is not evidence, not citation-eligible, and does not
satisfy source obligations.
`AG-EVIDENCE-LEDGER-CANDIDATE-CUSTODY-01` adds the RunKernel-authorized
`FetchReadContentPacket` / `SanitizedContentReference` -> EvidenceLedger
candidate/content custody seam. The custody records preserve packet,
candidate, reference, status, digest, URL/domain/title, and bounded-content
count/digest lineage only; they do not create semantic support, citation
eligibility, source-obligation satisfaction, ComponentCoverage, Sufficiency,
FinalAnswerPacket material, Author input, partial readiness, or product
correctness.
`AG-ANALYST-EVIDENCE-RELATIVE-REPORT-01` introduces
`EvidenceRelativeAnalysisPacket` with embedded `analyst_report` as
proposal-only evidence-relative meaning after EvidenceLedger custody. It
consumes EvidenceLedger fetch/read custody IDs and digests plus injected offline
Analyst proposal records; it is not SemanticObservation admission and does not
create ComponentCoverage, citation eligibility, source-obligation satisfaction,
Sufficiency, FinalAnswerPacket, Author input, readiness, partial-answer
readiness, search dispatch, query plans, or product correctness.
`AG-ANALYSIS-GAP-FOLLOWUP-SEARCH-01` introduces
`FollowupSearchIntentPacket` / `AnalysisGapSearchProposal` as the current
proposal-only gap-to-search-intent posture from validated
`EvidenceRelativeAnalysisPacket` / `analyst_report.analysis_gap_proposals`.
It is not search authorization, not a query plan, does not create
SearchExecutorHandoff, does not dispatch search, does not create evidence, and
RunKernel/SearchPlanner/SearchExecutorHandoff authorization remains required
before any executable search work exists.

`AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01` is complete. Use
`docs/architecture/AG_COMPONENT_COVERAGE_RELIABILITY_PROOF_01.md`,
`docs/architecture/AG_DOC_SEMANTIC_COVERAGE_CHECKPOINT_01.md`, and the
phase-focus `component_coverage_reliability_report` posture when working near
this seam. The proof showed that ComponentCoverage can reduce meaningful support
only after admitted `SemanticObservation` exists; the current packet chain by
itself does not admit semantic support.

`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` is complete, before Scrutineer or
Specialist. It is the controlled promotion from Analyst support proposal to
admitted SemanticObservation and is justified because ComponentCoverage consumes
it immediately. The completed bridge proves:

```text
EvidenceRelativeAnalysisPacket support finding
-> RunKernel-authorized SemanticObservation admission
-> ComponentCoverage reduction
```

It would not have been justified if it proved only:

```text
EvidenceRelativeAnalysisPacket support finding
-> new packet
-> future consumer later
```

The packet/bridge budget rule: no new packet or bridge unless it crosses a
trust/raw-data boundary, becomes durable reducer input, needs stable downstream
IDs/digests consumed by more than one stage, records canonical or
reducer-admitted state, prevents raw/private/provider leakage, or removes a
named blocker for an existing consumer. A packet or bridge is suspect if it only
restates lineage, only says closed flags remain false, is only consumed by its
own tests, creates another proposal layer without reduction, or has no immediate
consumer in the same or next phase.

Broker is local/private validation plumbing, not installed-product authority and
not product follow-up policy. Modes change budget and review depth, not
semantic authority. Follow-up policy should be based on logical depth, loop
budget, query fanout, and RunKernel approval, not one-query-per-proposal. Fast has no
Scrutineer in MVP. Balanced uses Scrutineer on red flags. Deep requires
Scrutineer later and reserves post-Scrutineer response budget; full Deep
orchestration is not part of the Scrutineer MVP. Deep allows max 3 follow-up
loops by default and max 4 only with explicit RunKernel extra recovery
authorization. `AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01` is now complete as
source-bound calculation/economist-style reasoning only.

`AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01` is complete as the first governed
remediation loop. FollowupSearchIntent remains proposal-only; RunKernel owns
follow-up search authorization; the authorized work identity/query bundle is not
live dispatch. Fixture-backed reentry proves the future product path without
live providers through SearchResultCandidatePacket, FetchReadContentPacket,
EvidenceLedger, EvidenceRelativeAnalysisPacket, SemanticObservation, and
ComponentCoverage. Unresolved results remain blocked/follow-up-required/
contested. No Sufficiency/FAP/Author/citation/source-obligation
satisfaction/product correctness is proved.

`AG-SCRUTINEER-REVIEW-01` is complete as the first useful Scrutineer MVP. Use
`docs/architecture/AG_SCRUTINEER_REVIEW_01.md` when working near this seam.
Scrutineer is a supervisory review/sign-off layer for Analyst work product, not
product authority. It reviews Analyst support, admitted SemanticObservation
posture, ComponentCoverage posture, FollowupSearchIntent refs, follow-up
authorization refs, fixture-backed reentry refs, and unresolved blocked/
follow-up/contested posture. Scrutineer can perform initial review and final
verification, require remediation, and point to follow-up proposal refs, but it
does not authorize search and does not run remediation. Follow-up authorization
remains RunKernel-owned through `AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01`.
If Analyst and Scrutineer remain in conflict, contested posture must be
preserved for future FAP/Author. Fast has no Scrutineer in MVP. Balanced uses
Scrutineer on red flags and should preserve remediation budget when Scrutineer
is invoked. Deep requires Scrutineer later, with more remediation budget, but
full Deep orchestration is not part of this phase.

`AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01` is complete as the first useful
Specialist MVP. Use
`docs/architecture/AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md` when working
near this seam. Specialist is source-bound deterministic calculation only, not
product authority and not broad legal, medical, technical, or generic expert
reasoning. RunKernel owns Specialist calculation reduction. Inputs must be
source-bound and lineage-preserving; invalid, stale, contradictory, mixed-unit,
non-numeric, missing-lineage, or unsupported-formula calculations remain blocked
or contested. Scrutineer can review Specialist calculation posture but does not
calculate or authorize it. Specialist does not decide ComponentCoverage,
Sufficiency, FAP, Author, citation eligibility, source-obligation satisfaction,
current_answer_contract mutation, or product correctness. Existing Economist
surfaces remain legacy/passive unless deliberately reused without authority
revival.

`AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01` is complete as the pre-FAP
readiness reducer. Use
`docs/architecture/AG_SUFFICIENCY_PARTIAL_ANSWER_READINESS_01.md` when working
near this seam. SufficiencyReadiness is RunKernel-owned and reduces
component-level and answer-level readiness into `sufficiency_readiness_state`,
`sufficiency_readiness_projection`, and `sufficiency_readiness_history`. It
supports `full_answer_ready`, `partial_answer_ready`, `blocked`,
`followup_required`, `contested`, `insufficient_evidence`, and
`not_applicable` posture. It emits a safe FAP handoff preview of refs, caveats,
and prohibited upgrades only. It does not create FinalAnswerPacket, Author
input, citation eligibility, source-obligation satisfaction,
current_answer_contract mutation, live calls, or product correctness. Old
AG-92C Sufficiency/FAP and AG-96/FAP/Author surfaces remain
legacy/passive/closed unless explicitly reopened.

`AG-FINAL-ANSWER-PACKET-HARDENING-01` is complete as the hardened FAP handoff
surface. Use
`docs/architecture/AG_FINAL_ANSWER_PACKET_HARDENING_01.md` when working near
this seam. The reducer consumes SufficiencyReadiness and writes the existing
canonical `final_answer_packet` stage/state slot:
`state.final_answer_packet`, `state.final_answer_authority_projection`, and
`state.projections["final_answer_packet"]`. It preserves
full/partial/blocked/follow-up/contested/insufficient/not-applicable posture,
including `packet_created: false` for `not_applicable`. It does not use old
AG-92C/AG-96 FAP/Author authority, does not execute Author or create prose,
preserves citation requirements but defers citation eligibility/rendering,
preserves source-obligation posture but does not satisfy source obligations,
does not run live calls, and does not claim product correctness.

`AUTHOR-PROSE-ONLY-FINALIZATION-01` is complete as the prose-only finalization
surface. Use
`docs/architecture/AUTHOR_PROSE_ONLY_FINALIZATION_01.md` when working near this
seam. AuthorProseFinalization consumes hardened FAP only plus
AuthorProsePolicy knobs for
style/format/brevity/source-pass-through/uncertainty, partial-answer,
blocked-answer, and citation-display presentation. It writes
`author_prose_state`, `author_prose_projection`, `author_prose_history`, and
`state.projections["author_prose_finalization"]`. It does not call a model or
provider, does not execute old Author, does not render citations, does not
satisfy source obligations, does not claim product correctness, does not mutate
current_answer_contract, and does not write canonical output to legacy
`author_observation` / `final_answer_outcome`. AuthorProseConformanceReview is
dogfood/testing-only, not production-blocking.

The AG-96 followup stack, offline SearchExecutor bridge, SearchWorkPlan shadow,
old Analyst/Economist/Scrutineer paths, source-class recovery bridges, and broad
pipeline orchestrator paths are legacy/passive/closed unless explicitly
reopened.

Historical broad Analyst, Economist, and Scrutineer surfaces are not yet a
coherent new RunKernel/current_answer_contract second-half semantic
architecture. The current Scrutineer MVP is limited to RunKernel-reduced review
state over the completed Analyst/admission/coverage/remediation path and the
completed hardened FAP -> AuthorProseFinalization path.

Historical roadmap baseline, not the current next gate: the earlier roadmap
order was:
`AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01`,
`AG-LIVE-XAXIS-VALIDATION-01A`,
`AG-SEARCH-RESULT-CANDIDATE-PACKET-01`,
`AG-FETCH-READ-CONTENT-REFERENCE-01`,
`AG-EVIDENCE-LEDGER-CANDIDATE-CUSTODY-01`,
`AG-ANALYST-EVIDENCE-RELATIVE-REPORT-01`,
`AG-ANALYSIS-GAP-FOLLOWUP-SEARCH-01`,
`AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01`,
`AG-DOC-SEMANTIC-COVERAGE-CHECKPOINT-01`, then
`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`,
`AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01`,
`AG-SCRUTINEER-REVIEW-01`,
`AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01`,
`AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01`,
`AG-FINAL-ANSWER-PACKET-HARDENING-01`,
`AUTHOR-PROSE-ONLY-FINALIZATION-01`.

That roadmap has now advanced through the #352-#355 current-path quarantine,
fixture dogfood, partial scenario repair, and ordinary-query local dry-run work.
The current next gate is tightly scoped limited live validation.

AG-BAL-HARDEN and the component executor contract are not live validation: live
provider, model, search, fetch, and retrieval calls remain closed by default
unless a phase explicitly scopes the live query class, budget, redaction plan,
artifact path, decision, and stop condition.

Balanced now has a hardened, default-disabled, one-gap / one-query / one-cycle
offline recovery seam. Recovery mechanics are shared primitives; modes supply
policy and budget envelopes. Project Sources are not repo files unless their
content is explicitly pasted into the current prompt or committed here.

## Architecture guidance

- **General architectural workflow and Path B PR process:**
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- **D-prime evidence-relative model review overview:** read
  `docs/architecture/DPRIME_ARCHITECTURE.md` for the current D-prime authority
  split, allowed/forbidden outputs, negative controls, and post-#392
  RunKernel-admission-missing stop point. For generic dogfood or adapter work
  near D-prime source-obligation authority, citation-source handoff,
  single-lane answer path, follow-up re-entry, same-lane multi-source scrutiny,
  FAP, Author, or readiness, perform the capability inventory / reuse-first gate
  before adding a new surface.
- **Cross-component Analyst Workbench doctrine:** read
  `docs/architecture/CROSS_COMPONENT_ANALYST_WORKBENCH.md` before phases that
  touch multi-component reasoning, ComponentWorkGraph, ComponentWorkNode lift,
  synthesis proposals, synthesis D-prime, graph admission, dependency gaps,
  missing-component proposals, or cross-component recovery. The next safe
  sequence is Cross-Component Analyst Workbench doctrine/contract first,
  ComponentWorkGraph V0 no-execution contract, proposal-only synthesis,
  synthesis D-prime validation, then RunKernel graph admission. Do not build a
  fake graph, scheduler, parallel Analyst, D-prime-as-Analyst, FAP synthesis,
  Author glue, or direct retrieval dispatch path.
- **Analyst Workbench runtime contract:** read
  `docs/architecture/ANALYST_WORKBENCH_FULL_SLICE.md` before phases that touch
  candidate triage, candidate roles, strict support detection,
  contextual/overclaim/qualifier risk, Workbench gap proposals, Workbench
  D-prime dossier refs, Workbench reduction projections,
  `strict_support_missing` follow-up, unreadable official/read-support
  follow-up, D-prime candidate handoff identity, or the Workbench section of
  current-source review reports. Reading the contract authorizes understanding
  the current proposal-only Workbench boundary, follow-up license behavior,
  product PASS requirements, and candidate identity invariant. It does not
  authorize runtime changes, live validation, provider/model/search/fetch/read
  calls, new answer paths, Scrutineer implementation, source-challenge
  recovery, FAP/Author wording changes, or product-correctness claims.
- **Previous AG-SEM posture:** AG-SEM-05 through AG-SEM-10 completed the
  canonical reducer and conditional Sufficiency-consumption chain; AG-SEM-11
  and the later semantic atomicity work moved the ordinary semantic producer
  past the old "next vertical slice" gate. Use
  `docs/architecture/AG_SEM_05_10_COMPLETION_AND_NEXT_GATES.md` as historical
  context, not current next-step doctrine. For historical AG-96 context, read
  `docs/architecture/AG96_CURRENT_STATE_AND_NEXT_CHOICES.md`.
- **Integrated run-contract semantic loop:** read
  `docs/architecture/AG_CURRENT_PATH_QUARANTINE_01.md` for the current path
  registry and consumer-seam matrix, then
  `docs/architecture/AG_DOC_SEMANTIC_COVERAGE_CHECKPOINT_01.md`,
  `docs/architecture/AG_SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_01.md` for the
  post-#342 SemanticObservation admission / ComponentCoverage checkpoint, and
  `docs/architecture/AG_FOLLOWUP_SEARCH_AUTHORIZATION_REENTRY_01.md` for the
  first governed remediation loop, then
  `docs/architecture/AG_SCRUTINEER_REVIEW_01.md` for the supervisory
  Analyst/admission/coverage/remediation review layer, then
  `docs/architecture/RUN_CONTRACT_SEMANTIC_LOOP.md` for the current doctrine
  connecting AG-SEM semantic authority to ComponentSearchPlan, Scout,
  SearchExecutor, EvidenceLedger, SufficiencyJudgment, FinalAnswerPacket, and
  prose-only Author handoff. It cross-references the relevant AG-SEM records:
  `AG_SEM_01_PASSIVE_SEMANTIC_CONTRACT_FOUNDATION.md`,
  `AG_SEM_02_SANITIZED_CONTENT_REFERENCE_AND_SEMANTIC_OBSERVATION.md`,
  `AG_SEM_04_CONTRACT_AMENDMENT_RECORD.md`,
  `AG_SEM_05_INITIAL_ANSWER_CONTRACT_ACCEPTANCE.md`,
  `AG_SEM_07_COMPONENT_COVERAGE_REDUCTION.md`,
  `AG_SEM_08_CONTRACT_AMENDMENT_ADMISSION.md`,
  `AG_SEM_09_SUFFICIENCY_SEMANTIC_CONSUMPTION.md`,
  `AG_SEM_11_ORDINARY_SEMANTIC_PRODUCER_VERTICAL_SLICE.md`, and
  `AG_SEM_11B_ORDINARY_SEMANTIC_PRODUCER_HARDENING.md`.
- **Recovery-adjacent Balanced / AG-BAL-HARDEN work:** read
  `core/component_gap_recovery_runtime.py`,
  `core/component_gap_recovery_coordinator.py`,
  `core/run_kernel.py` around `commit_recovered_semantic_delta`,
  `core/run_config.py` around `compose_component_gap_recovery_deps`,
  `tests/test_ag_bal_01_component_gap_recovery.py`, and the durable
  `tests/buckets/semantic_search_lane.txt` and
  `tests/buckets/author_lane.txt` manifests. Keep product runtime live calls
  closed by default. Use `semantic_search_lane` for durable QueryPlan/
  SearchJudgment recovery-path proof and `author_lane` for recovered
  fact/source Author-materialization proof when explicitly licensed.
- **AG-89+ RunAuthority / authority-collapse work:**
  [RUNAUTHORITY_IMPLEMENTATION_GUIDE.md](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md).
- **Current source-class recovery dispatch doctrine:** use
  `docs/architecture/AG95C_CANONICAL_RECOVERY_PERMISSION_DISPATCH_CONSOLIDATION.md`,
  `docs/architecture/AG95D_RECOVERY_DISPATCH_SANITY_AUDIT_AND_CLEANUP_TARGET_SWEEP.md`,
  `docs/architecture/AG95E_STALE_DISPATCH_DOCTRINE_AND_FIXTURE_CLEANUP.md`,
  `docs/architecture/AG95F_CONTROLLER_LOOP_SPINE_SOURCE_CLASS_TRACE_DEMOTION.md`,
  `docs/architecture/AG95G_SOURCE_CLASS_COMPATIBILITY_CONSUMER_AUDIT_AND_RETIREMENT.md`,
  `docs/architecture/AG95H_REMAINING_SOURCE_CLASS_COMPATIBILITY_TRACE_DIET.md`,
  and
  `docs/architecture/AG95I_CONTROLLER_LOOP_SPINE_PACKET_FIELD_DIET.md`,
  followed by
  `docs/architecture/AG95J_K_ACTIVE_GATE_AND_LIFECYCLE_BOOLEAN_DIET.md`,
  followed by
  `docs/architecture/AG95L_PIPELINE_PRODUCT_CALLSITE_COMPATIBILITY_READ_DIET.md`,
  `docs/architecture/AG95M_PIPELINE_ORCHESTRATOR_SOURCE_CLASS_AUTHORITY_HELPER_EXTRACTION.md`,
  `docs/architecture/AG95N_O_P_FINAL_AUTHORITY_VISIBILITY_RECOVERY_DECISION_PROJECTION_BURNDOWN.md`,
  and
  `docs/architecture/AG95Q_PROVIDER_REVIEW_ALLOCATION_BURNDOWN.md`.
  Current runner dispatch authority is canonical
  `authority_lifecycle.recovery_action` consumed by
  `SourceClassRecoveryRunner`; `authorized_spine_action`,
  ControllerRecoveryDecision, and ControllerLoopSpine shared active-gate fields
  are diagnostic/compatibility surfaces for source-class dispatch. AG-95I is
  the current ControllerLoopSpine packet-field diet: it retires the
  source-class-specific packet aliases/markers and leaves only shared
  active-gate compatibility where weak-corpus, conflict, terminal-stop, or
  targeted-retrieval coverage still needs it. AG-95J/K is the follow-on boolean
  diet: it removes source-class-adjacent shared active-gate assertions and
  rewrites redundant lifecycle/admission booleans to canonical
  AuthorityLifecycle recovery-action or runner execution proof. AG-95L/M/N-O-P
  are the current pipeline burn-down chain: L rewrites product callsite reads to
  canonical AuthorityLifecycle action/blocker state, M extracts bounded
  source-class authority reads, N/O/P moves final visibility/citation handoff
  to FinalEvidenceBundle/FinalAnswerPacket observation, and AG-95Q moves
  provider-review allocation runtime ownership to canonical
  RunAuthority/SearchJudgment-fed lifecycle state consumed by the provider
  allocation helper. AG-95R/S/T retires ControllerRecoveryDecision from active
  visibility export; current export coverage observes canonical provider-review
  allocation fields. AG-95F/G/H
  are historical setup phases; use AG-95I through AG-95Q for the current packet,
  lifecycle, provider-review allocation, and pipeline product-callsite
  compatibility contract.
- **Orchestrator strangulation and phase-boundary vocabulary:** read
  `docs/architecture/AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md` after the
  RunAuthority guide when a phase touches `core/pipeline_orchestrator.py`,
  controller/orchestrator cleanup, or the licensed/closed/target/historical
  surface vocabulary.
- **Current authority doctrine / stale Controller vocabulary audit:** read
  `docs/architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md` after the
  RunAuthority guide when a phase touches authority, projection/export/report
  meaning, controller/orchestrator cleanup, or naming debt.
- **AG-89 architecture inventory and doctrine:** start with
  `docs/architecture/AG89A_RUN_KERNEL_ORCHESTRATOR_RETIREMENT_ACCOUNTABILITY_INVENTORY.md`
  and then read later AG-89 docs relevant to the phase (`AG89B` if present,
  `AG89C`, `AG89D`, `AG89E`).
- **Legacy Controller-handoff maintenance only when explicitly selected:**
  [CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md](CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md).

## Multi-step and bundled phases

- Use [EXECUTION_PLAN_TEMPLATE.md](EXECUTION_PLAN_TEMPLATE.md) when a phase has
  several checkpoints, multiple files/seams, runtime consumers, or authority
  paths to delete/demote/bypass/subordinate.
- Use a tiny plan in the final answer or working notes for small one-seam phases.

## Live validation / dogfood

- Live ScryRaven/proplex provider, model, search, or retrieval calls are disabled
  unless the phase explicitly scopes query class, run cap, provider/model/search
  budget, packet path, redaction plan, decision, and stop condition.
- The post-#330 live-validation path is not a product run.
  `AG-LIVE-XAXIS-VALIDATION-01A` PR1 is a search-only validation seam that
  consumes `current_answer_contract` plus `SearchExecutorHandoff` directly and
  emits sanitized `SearchResultCandidate` records only from injected
  fake-provider results. PR2 is broker/direct invocation scaffolding only and
  remains inert unless live validation is separately licensed. LIVE-RUN-01 is
  the inert request-packet and broker-envelope harness; actual provider contact
  remains separately licensed and trusted-local or broker-private through the
  generic provider-proxy broker contract.
- `AG-LIVE-XAXIS-VALIDATION-01A` must keep fetch/read, EvidenceLedger custody,
  citations, source-obligation satisfaction, Sufficiency, FAP, Author,
  partial-answer readiness, and product correctness closed.
- `provider_preference_hint` is only a hint. Live provider authority requires an
  explicit RunKernel-authorized validation action and a governed live-search
  adapter, even if existing `core/search_providers.py` wrappers are reused.
- Live multi-component/product validation is deferred until the second-half
  chain exists through SearchResultCandidatePacket, FetchReadContentPacket /
  SanitizedContentReference, EvidenceLedger custody, evidence-relative
  Analyst/Specialist/Scrutineer packets, SufficiencyJudgment, and
  FinalAnswerPacket.
- For the historical AG-LIVE-BOUND-01 product-run preflight status and its
  superseded bridge recommendation, see
  [AG_LIVE_PLAN_01_BOUNDED_LIVE_VALIDATION_PLAN.md](AG_LIVE_PLAN_01_BOUNDED_LIVE_VALIDATION_PLAN.md).
- For live validation artifact rules, read the live-validation section in
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).

## PR and final-bundle review

- Use the Path B, bounded-autonomy, surface-boundary, and final-bundle sections
  in [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- If the phase is AG-89+ authority-collapse work, also include the final bundle
  fields from [RUNAUTHORITY_IMPLEMENTATION_GUIDE.md](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md).
- Always report the validation bucket used. For PRs, `fast_pr` is the normal
  non-docs target unless the phase explicitly licenses `author_lane` or `full`.
- Implementation PR docs should use merge-stable phase posture: previous
  completed baseline, this PR completes/introduces the active phase, and
  post-merge next gate. Do not label the active implementation phase as the
  repo's next/current target in docs updated by that same PR.

## Surface Boundary Vocabulary

Use precise phase-boundary words in current prompts and reviews:

- **Licensed surface:** a file, module, behavior, or document the current phase
  explicitly allows Codex to inspect or change.
- **Closed surface:** a surface kept out of scope for this phase.
- **Target surface:** a surface intentionally being reduced, moved, simplified,
  or retired over time.
- **Historical surface:** retained as project history, not current doctrine.
- **Safety-sensitive surface:** high-custody behavior such as provider routing,
  prompt semantics, citation behavior, persistence shape, or live validation.

The legacy word "protected" should not mean sacred. For
`core/pipeline_orchestrator.py`, "line delta: 0" is only a scope-control fact.
It is not architecture success. In ordinary product behavior phases the
orchestrator may be closed for safety; in orchestrator-strangulation phases it
is a target surface.

## Stale-guidance questions

When guidance conflicts:

1. Direct system/developer/user instructions win.
2. The current phase prompt wins over older docs.
3. For AG-89+ authority-collapse, the RunAuthority guide wins over the legacy
   Controller passive-contract ladder.
4. For current-looking architecture summaries that still say "Controller
   decides, orchestrator executes", prefer the AG-94C authority doctrine audit
   and this map's AG-95 source-class dispatch routing. Treat older summaries as
   historical unless a phase explicitly refreshes them.
5. For legacy Controller-handoff maintenance explicitly selected by a phase, the
   Controller playbook may be used within its stated scope.
6. If a conflict would require a product choice, unresolved architecture fork,
   unlicensed or closed-surface change, live validation, secrets/private data,
   or destructive git, stop and ask.

## Bounded-autonomy policy summary

Proceed autonomously for relevant inspection, scoped implementation, in-scope
tests, in-scope test fixes, docs cross-link fixes caused by the phase,
formatting/pre-commit fixes, final-bundle preparation, and PR creation when the
phase brief explicitly authorizes it.

Stop for product choices, unresolved architecture forks, unlicensed or closed
surfaces, live validation, secrets/private data, destructive git,
merge/rebase/force-push, broad scope expansion, or unresolved failing tests that
imply a design decision.
