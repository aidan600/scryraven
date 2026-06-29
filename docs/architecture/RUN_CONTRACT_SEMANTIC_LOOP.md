# Run-Contract Semantic Loop

## 1. Status

Status: Current doctrine after PR #342 /
`AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01` and
`AG-DOC-SEMANTIC-COVERAGE-CHECKPOINT-01`, refreshed after
`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`,
`AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01`,
`AG-SCRUTINEER-REVIEW-01`, and
`AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01`, and
`AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01`, and
`AG-FINAL-ANSWER-PACKET-HARDENING-01`, and
`AUTHOR-PROSE-ONLY-FINALIZATION-01`.

Proof class: `docs_architecture_update`.

The front half is now coherent through SearchExecutorHandoff:

```text
SearchPlanner
-> initial_answer_contract
-> Scout
-> SearchPlannerRevision
-> amendment admission/application
-> current_answer_contract
-> SearchExecutorHandoff
```

`SearchExecutorHandoff` consumes `current_answer_contract` when present and
uses explicit `initial_answer_contract` fallback only when no current contract
exists. It creates offline executable search intent only: query-intent records,
search-task records, and a search work packet. It does not call providers,
execute live search, fetch/read content, run retrieval, admit EvidenceLedger
custody, create citations, satisfy source obligations, decide Sufficiency,
create FinalAnswerPacket state, create Author input, or make a partial answer
ready.

SearchExecutorHandoff exact posture: PR #330 / AG-SEARCH-EXECUTOR-HANDOFF-01;
handoff consumes current_answer_contract when present; Scout/revision material
is search direction only; handoff creates search task records and a search work
packet; no live search/provider/fetch/read/retrieval calls were run; no
EvidenceLedger/citations/source-obligation satisfaction; next implementation
gate after AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01 is
AG-LIVE-XAXIS-VALIDATION-01A.

Historical SearchPlannerRevision exact posture: PR #329 /
AG-SEARCH-PLANNER-REVISION-01; planner revision consumes Scout report; planner
revision emits passive amendment candidates; Scout hints remain non-evidence,
non-citation, and non-source-obligation satisfaction; current_answer_contract
changes only through existing admission/application path; SearchExecutor,
fetch/read/retrieval remain closed; post-merge next gate was
AG-SEARCH-EXECUTOR-HANDOFF-01.

Historical Scout exact posture: PR #327 / AG-SEARCH-PLANNER-MODEL-01; AG-SCOUT-DISAMBIGUATION-RUNTIME-01; RunKernel-authorized; report-only; Serper-shaped; fake injected adapters only; No live Serper/search/provider/model/fetch/read/retrieval calls were run; Scout hints are not evidence; not citations; not source-obligation satisfaction; Scout does not mutate contracts; Scout does not revise planner output; post-merge next gate is AG-SEARCH-PLANNER-REVISION-01.
Historical SearchPlannerModel exact posture: PR #327 / AG-SEARCH-PLANNER-MODEL-01; AG-SEARCH-PLANNER-RUNTIME-01; AG-SEARCH-PLANNER-MODEL-01 adds an explicit injected fail-closed model adapter; No live model calls or live validation were run; AG-SCOUT-DISAMBIGUATION-RUNTIME-01; Scout hints are not evidence; post-merge next gate is AG-SEARCH-PLANNER-REVISION-01.

This document connects the AG-SEM semantic accountability lane with the
component/search/X-axis lane proved offline through blocked FinalAnswerPacket /
Author handoff, while preventing the new SearchExecutorHandoff records from
being mistaken for evidence or product correctness.

The governing discipline is:

```text
Semantic producer / planner understands.
RunKernel governs.
AnswerContract records obligations and statuses.
Workers propose observations or amendments.
RunKernel validates/reduces.
EvidenceLedger records custody.
SemanticObservation admission promotes proposal-stage meaning into admitted meaning.
ComponentCoverage consumes admitted meaning and custody bindings.
Sufficiency decides readiness.
Hardened FinalAnswerPacket consumes SufficiencyReadiness and packages an
Author-safe handoff.
AuthorProseFinalization consumes hardened FAP only and writes prose-only
state/projection/history.
```

The deterministic contract is not a substitute for semantic understanding.
Semantic understanding is not a substitute for contract authority. RunKernel is
not the LLM reasoner; it is the authority hub and reducer owner.

## 2. First Live Validation Boundary

`AG-LIVE-XAXIS-VALIDATION-01A` PR1 introduced the RunKernel-owned
search-only validation seam. PR1 is offline-governed: fake provider result
metadata is injected in tests, no live provider is called, and no broker is
invoked. PR2 adds broker/direct invocation scaffolding only: the shared request,
cap, normalizer, redaction, and output-packet shapes can represent a future
licensed broker or trusted-local provider call, but PR2 does not run live
validation, call a broker, fetch/read, retrieve, or admit evidence. Durable
broker contact should use the generic provider-proxy contract, not a
phase-specific broker job.
`AG-LIVE-XAXIS-VALIDATION-01A-LIVE-RUN-01` adds an inert trusted-local harness
for preparing the repo-visible request packet and optional broker envelope from
deterministic current-contract plus SearchExecutorHandoff state. The harness may
also reduce an operator-supplied sanitized provider-result JSON file through the
existing RunKernel validation path. When actual provider contact is separately
licensed, it should use the generic provider-proxy broker contract and sanitized
provider-result JSON, not a phase-specific broker job. The harness does not call
providers, call a broker, load credentials, fetch/read, retrieve, admit evidence,
create citations, decide Sufficiency, create FinalAnswerPacket state, create
Author input, make partial-answer readiness claims, or claim product correctness.

`broker_invoked` and `live_provider_called` are PR2 execution facts. They are
not downstream evidence, citation, source-obligation, Sufficiency,
FinalAnswerPacket, Author, partial-readiness, or product-correctness authority.
`raw_provider_payload_retained` and `raw_search_response_retained` remain false
in every mode.

That validation must consume these two current authorities directly:

- `current_answer_contract`
- `SearchExecutorHandoff`

It may produce sanitized `SearchResultCandidate` records only. Those records are
candidate discovery output, not evidence.

The first live validation must not claim or perform any of the following:

- fetch/read content;
- `EvidenceLedger` admission or custody;
- citations or citation eligibility;
- source-obligation satisfaction;
- `SufficiencyJudgment`;
- `FinalAnswerPacket`;
- Author input or Author prose;
- partial-answer readiness;
- product correctness or product answer correctness.

`provider_preference_hint` is only a hint carried by offline search intent. Live
provider authority must come from an explicit RunKernel-authorized validation
action and an explicit PR2 `provider_authorized` value. Existing provider
wrappers in `core/search_providers.py`, including the Serper wrapper, may be
reused only behind a governed live-search-validation adapter that enforces
action authorization, budget, redaction, sanitized output, and closed
fetch/read/evidence/citation/FAP/Author surfaces.

`core/offline_search_executor_bridge.py` is legacy/offline scaffolding for the
old X-axis proof path. For the new handoff-consuming live path it must be
demoted, retired, or ignored; it is not the live SearchExecutorHandoff consumer.

## 3. Integrated Product Loop

Current implemented front half:

```text
1. User query arrives.
2. RunKernel starts a seed contract / run contract with minimal known obligations.
3. SearchPlanner proposes question meaning, semantic slots, answer components, ambiguity posture, and initial requirements.
4. RunKernel validates and accepts initial_answer_contract.
5. If ambiguity needs cheap exploration, RunKernel authorizes Scout.
6. Scout reports bounded disambiguation dimensions and search-direction hints.
7. SearchPlannerRevision consumes the Scout report and proposes revisions/amendments.
8. RunKernel admits/applies allowed amendments into current_answer_contract.
9. SearchExecutorHandoff creates offline executable search intent from current_answer_contract and planner/revision direction.
```

Required second-half semantic loop:

```text
10. RunKernel authorizes search-only live validation from current_answer_contract and SearchExecutorHandoff.
11. Live validation emits sanitized SearchResultCandidate records only.
12. A later packet phase creates SearchResultCandidatePacket.
13. A fetch/read phase creates FetchReadContentPacket / SanitizedContentReference.
14. EvidenceLedger records candidate/content custody only from sanitized,
    admissible fetch/read packet references.
15. EvidenceRelativeAnalysisPacket / AnalystReport records proposal-only
    evidence-relative meaning after EvidenceLedger custody.
16. FollowupSearchIntentPacket / AnalysisGapSearchProposal can translate
    Analyst gap proposals into proposal-only follow-up search intent; this is
    reviewable structure, not authorization, not a query plan, and not
    SearchExecutorHandoff/search dispatch/evidence.
17. ComponentCoverage reliability proof showed that the packet chain can expose
    support and blocker posture, but meaningful ComponentCoverage reduction
    requires admitted SemanticObservation.
18. `AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` turns source-bound Analyst
    support proposals into RunKernel-authorized admitted semantic observations
    without adding another durable proposal packet.
19. `AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01` is the first governed
    remediation loop: RunKernel owns follow-up search authorization, creates a
    bounded authorized work identity/query bundle, and fixture-backed reentry
    proves the future product path without live providers through
    SearchResultCandidatePacket, FetchReadContentPacket, EvidenceLedger,
    EvidenceRelativeAnalysisPacket, SemanticObservation, and ComponentCoverage.
20. ComponentCoverage consumes admitted observations plus evidence/custody
    bindings and preserves component/source-obligation lineage.
21. `AG-SCRUTINEER-REVIEW-01` records RunKernel-reduced ScrutineerReview
    posture over support, conflicts, drift, gaps, coverage, and remediation
    state when mode policy requires it.
22. `AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01` records RunKernel-reduced
    Specialist source-bound deterministic calculation state when already
    source-bound numeric inputs exist. Specialist records calculation posture
    only; it is not product authority and does not decide ComponentCoverage,
    Sufficiency, FinalAnswerPacket, Author, citations, source obligations,
    contract mutation, or product correctness.
23. ContractAmendmentRecord proposals add/revise/supersede obligations when evidence changes meaning.
24. `AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01` records
    RunKernel.SufficiencyReadiness as the pre-FAP readiness reducer. It consumes
    current contract, ComponentCoverage, admitted SemanticObservation refs,
    ScrutineerReview posture, Specialist calculation posture, and follow-up
    budget posture, then decides component-level and answer-level readiness.
    It supports `full_answer_ready`, `partial_answer_ready`, `blocked`,
    `followup_required`, `contested`, `insufficient_evidence`, and
    `not_applicable`. It does not create FinalAnswerPacket, Author input,
    citation eligibility, source-obligation satisfaction,
    current_answer_contract mutation, live calls, or product correctness.
25. `AG-FINAL-ANSWER-PACKET-HARDENING-01` opens the hardened FAP handoff
    surface. It consumes SufficiencyReadiness, uses the existing canonical
    `final_answer_packet` stage/state slot, preserves
    full/partial/blocked/follow-up/contested/insufficient/not-applicable
    posture, defers citation eligibility/rendering, preserves
    source-obligation posture without satisfying source obligations, and does
    not execute Author or create prose.
26. `AUTHOR-PROSE-ONLY-FINALIZATION-01` records
    RunKernel.AuthorProseFinalization as the prose-only finalization surface.
    It consumes hardened FAP only plus AuthorProsePolicy, writes
    `author_prose_state`, `author_prose_projection`, and
    `author_prose_history`, and keeps old Author execution, model/provider
    calls, citation rendering, source-obligation satisfaction,
    current_answer_contract mutation, legacy `author_observation` /
    `final_answer_outcome`, and product-correctness claims closed.
```

PR #323 proved this offline blocked X-axis after a component-shaped plan already
exists:

```text
Component contract / ComponentSearchPlan
-> AnswerContractAuthorityMap
-> Offline SearchExecutor bridge
-> EvidenceLedger component custody
-> AnswerContractAuthorityMap binding_status
-> SufficiencyJudgment component readiness
-> FinalAnswerPacket blocked Author handoff
```

That proof remains useful history, but it is not the immediate post-#330 live
path. The new path starts from `current_answer_contract` and
`SearchExecutorHandoff`, then produces only candidate search results before any
fetch/read, custody, analysis, sufficiency, FAP, or Author work is licensed.

## 4. Ownership Boundaries

| Surface | Owner boundary |
| --- | --- |
| RunKernel / RunAuthority | Owns canonical run authority, action authorization, reducer gating, accepted contract state, and contract mutation/application authority. |
| SemanticProducer / SearchPlanner | Proposes query meaning, semantic slots, answer components, material ambiguities, and component search requirements. It does not mutate the accepted contract directly. |
| Scout | Performs bounded cheap disambiguation reconnaissance when RunKernel authorizes it. Reports dimensions, candidate interpretations, likely official/current targets, and URLs/hints. It does not decide final plan, mutate contract, or create evidence. |
| SearchPlannerRevision | Consumes Scout report and proposes revised plan/amendments. It does not own authority. |
| SearchExecutorHandoff | Creates offline executable search intent only. It does not execute providers, fetch/read, custody, citations, sufficiency, FAP, Author, or partial-answer readiness. |
| Live search validation adapter | Future governed adapter that may execute provider search only when RunKernel authorizes a validation action. It emits sanitized SearchResultCandidate records only in the first live slice. |
| SearchResultCandidatePacket | Durable packet for sanitized result candidates. It preserves non-evidence discovery lineage, is not EvidenceLedger custody, and does not satisfy obligations. |
| FetchReadContentPacket / SanitizedContentReference | bounded readable-content handoff after SearchResultCandidatePacket and before EvidenceLedger custody. It is not evidence, not citation-eligible, and does not satisfy source obligations. |
| EvidenceLedger fetch/read candidate custody | RunKernel-authorized reducer that admits FetchReadContentPacket / SanitizedContentReference packet, candidate, reference, status, URL/domain/title, and bounded-content count/digest lineage into EvidenceLedger candidate/content custody. It is not semantic support, citation eligibility, source-obligation satisfaction, ComponentCoverage, Sufficiency, FinalAnswerPacket material, Author input, partial readiness, or product correctness. |
| EvidenceLedger | Owns evidence custody and source-obligation state after admissible sanitized content exists. |
| SemanticObservation | Controlled RunKernel-authorized promotion from proposal-stage meaning into admitted evidence-relative semantic observations. |
| EvidenceRelativeAnalysisPacket / AnalystReport | Current standalone proposal-only evidence-relative analysis packet with embedded `analyst_report`; it consumes EvidenceLedger fetch/read custody IDs/digests and injected offline Analyst proposal records, is not SemanticObservation admission, and does not create ComponentCoverage, citation eligibility, source-obligation satisfaction, Sufficiency, FinalAnswerPacket, Author input, readiness, search dispatch, or final prose authority. |
| FollowupSearchIntentPacket / AnalysisGapSearchProposal | Current proposal-only gap-to-search-intent posture from validated `EvidenceRelativeAnalysisPacket` / `analyst_report.analysis_gap_proposals`. It is not search authorization, not a query plan, does not create SearchExecutorHandoff, does not dispatch search, does not create evidence, and RunKernel/SearchPlanner/SearchExecutorHandoff authorization remains required before any executable search work exists. |
| Specialist source-bound calculation | RunKernel-reduced deterministic calculation state over already source-bound numeric inputs. Specialist is source-bound calculation only, not broad legal, medical, technical, or generic expert reasoning. It preserves input/formula/unit/caveat/blocker lineage and keeps ComponentCoverage, Sufficiency, FinalAnswerPacket, Author, citation eligibility, source-obligation satisfaction, contract mutation, and product correctness closed. |
| ScrutineerReview | RunKernel-reduced supervisory review/sign-off layer for Analyst work product, not product authority. It can require remediation and reference FollowupSearchIntent proposal refs, but it does not authorize search or run remediation. Fast has no Scrutineer in MVP, Balanced uses Scrutineer on red flags and should preserve remediation budget when invoked, and Deep requires Scrutineer later without full Deep orchestration in this phase. |
| AnalysisGapSearchProposal | Current reviewable proposal record inside `FollowupSearchIntentPacket`. It carries gap lineage, hints, and structural review readiness only; it is a proposal, not a dispatch. |
| ComponentCoverageRecord | Owns component support/coverage proposals and reduction after admitted evidence-relative observations and custody bindings exist. |
| ContractAmendmentRecord / admission / application | Provides the proposal/admission/application pathway for adding, superseding, satisfying, failing, blocking, or declaring not-applicable requirements. |
| AnswerContractAuthorityMap | Passive authority map over components, custody, binding, readiness, and FAP state. It does not mutate the contract. |
| SufficiencyReadiness | RunKernel-owned pre-FAP readiness reducer. It produces component-level and answer-level readiness (`full_answer_ready`, `partial_answer_ready`, `blocked`, `followup_required`, `contested`, `insufficient_evidence`, `not_applicable`) plus safe FAP handoff preview refs and caveats. It does not create FinalAnswerPacket, Author input, citation eligibility, source-obligation satisfaction, current_answer_contract mutation, live calls, or product correctness. |
| SufficiencyJudgment | Owns answerability/readiness decision after prerequisite custody, semantic, coverage, and amendment inputs exist. |
| FinalAnswerPacket | RunKernel-owned hardened FAP handoff. It consumes SufficiencyReadiness and writes the canonical `final_answer_packet` stage/state slot without using old AG-92C/AG-96 FAP/Author authority. It preserves full/partial/blocked/follow-up/contested/insufficient/not-applicable posture, preserves citation requirements while deferring citation eligibility/rendering, preserves source-obligation posture without satisfying source obligations, and does not execute Author or create prose. |
| AuthorProseFinalization | Prose-only finalization surface. It consumes hardened FAP only and policy knobs for style/format/brevity/source-pass-through/uncertainty, writes AuthorProse state/projection/history, and has no custody, support, readiness, citation, source-obligation, product-correctness, or contract authority. |
| Author | Legacy/old Author execution remains closed unless explicitly reopened. |

Historical broad Analyst, Economist, and Scrutineer runtime surfaces are not yet
a coherent new RunKernel/current_answer_contract second-half semantic
architecture. Treat them as legacy, passive, bounded, or specialized surfaces.
The current Scrutineer MVP is limited to RunKernel-reduced review state over the
completed Analyst/admission/coverage/remediation path.

## 5. Contract Mutation Discipline

Contract update rule:

```text
Workers may propose.
RunKernel alone reduces.
```

Contract updates should be typed. Examples:

- `add_requirement`
- `add_component`
- `revise_component`
- `add_disambiguation_requirement`
- `resolve_disambiguation_requirement`
- `add_source_obligation`
- `add_fetch_read_obligation`
- `mark_requirement_satisfied`
- `mark_requirement_failed`
- `mark_requirement_blocked`
- `mark_requirement_not_applicable`
- `supersede_requirement`
- `add_review_or_redteam_obligation`
- `add_caveat`
- `prohibit_upgrade`

AG-SEM-08 admits amendment proposals, and AG-RUN-CONTRACT-MUTATION-LOOP-01
applies admitted amendments through RunKernel into `current_answer_contract`.
Future second-half phases may propose additional amendments, but only RunKernel
may admit/apply them into accepted contract state.

## 6. Semantic Accountability Discipline

The contract is partly deterministic and partly semantic.

The system needs a semantic understanding layer because:

- a user query is not just a checklist;
- material ambiguity changes what counts as a correct answer;
- components and obligations depend on interpreted meaning;
- evidence may reveal new requirements, conflicts, stale assumptions, missing
  dimensions, or caveats;
- Sufficiency needs semantic support/coverage, not just candidate/source
  presence.

Use these terms precisely:

- semantic proposal
- canonical semantic state
- search result candidate
- sanitized content reference
- evidence-relative analysis
- semantic observation
- component coverage
- semantic blocker
- analysis gap search proposal
- contract amendment candidate
- required caveat
- prohibited upgrade

Historical semantic lane references:

- `AG_SEM_01_PASSIVE_SEMANTIC_CONTRACT_FOUNDATION.md`
- `AG_SEM_02_SANITIZED_CONTENT_REFERENCE_AND_SEMANTIC_OBSERVATION.md`
- `AG_SEM_04_CONTRACT_AMENDMENT_RECORD.md`
- `AG_SEM_05_INITIAL_ANSWER_CONTRACT_ACCEPTANCE.md`
- `AG_SEM_07_COMPONENT_COVERAGE_REDUCTION.md`
- `AG_SEM_08_CONTRACT_AMENDMENT_ADMISSION.md`
- `AG_SEM_09_SUFFICIENCY_SEMANTIC_CONSUMPTION.md`
- `AG_SEM_11_ORDINARY_SEMANTIC_PRODUCER_VERTICAL_SLICE.md`
- `AG_SEM_11B_ORDINARY_SEMANTIC_PRODUCER_HARDENING.md`

Treat those as lane history and supporting doctrine. This document is the current
integration doctrine for connecting semantic authority to `current_answer_contract`,
SearchExecutorHandoff, live search-result candidates, future fetch/read content,
EvidenceLedger, Analyst/Specialist/Scrutineer packets, SufficiencyJudgment,
FinalAnswerPacket, and Author.

## 7. Shadow/Passive Surface Warning

Passive/shadow surfaces are allowed only when explicitly licensed as passive
docs/tests/instrumentation.

They are not product readiness.

A future phase must not treat these as sufficient:

- dataclass exists;
- trace key exists;
- test fixture exists;
- passive projection exists;
- shadow query-plan field exists;
- prompt describes policy but runtime owner does not consume it.

Runtime success requires:

- intended runtime owner consumes it;
- RunKernel or the correct owner authorizes/reduces/acts;
- focused test proves the real consumer path.

## 8. SemanticObservation Admission Bridge

The ComponentCoverage reliability proof is complete, and
`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` now supplies the minimal
controlled promotion from Analyst support proposal to admitted SemanticObservation.
The bridge is justified because ComponentCoverage consumes it immediately.

The bridge is not a new durable proposal packet. It consumes validated
`EvidenceRelativeAnalysisPacket` support findings plus bounded fetch/read
content and EvidenceLedger custody refs, obtains RunKernel authorization, and
reduces the existing SemanticObservation admission runtime.

ComponentCoverage reduction remains separate. The bridge admits meaning; it does
not create ComponentCoverage by itself. ComponentCoverage must consume the
admitted observation and content binding through its own reducer.

The packet/bridge budget rule: no new packet or bridge unless it crosses a
trust/raw-data boundary, becomes durable reducer input, needs stable downstream
IDs/digests consumed by more than one stage, records canonical or
reducer-admitted state, prevents raw/private/provider material from leaking
forward, or removes a named blocker for an existing consumer. A packet or bridge
is suspect if it only restates lineage, only says closed flags remain false, is
only consumed by its own tests, creates another proposal layer without
reduction, or has no immediate consumer in the same or next phase.

The completed bridge proof is:

```text
EvidenceRelativeAnalysisPacket support finding
-> RunKernel-authorized SemanticObservation admission
-> ComponentCoverage reduction
```

It is not success to prove only:

```text
EvidenceRelativeAnalysisPacket support finding
-> new packet
-> future consumer later
```

Broker is local/private validation plumbing, not installed-product authority
and not product follow-up policy. Modes change budget and review depth, not
semantic authority. Follow-up policy should be based on logical depth, loop
budget, query fanout, and RunKernel approval rather than
one-query-per-proposal.

The bridge does not create source-obligation satisfaction, citation eligibility,
Sufficiency, FinalAnswerPacket, Author input, live search, provider calls,
broker calls, retrieval, fetch/read execution, model calls, or product
correctness. FollowupSearchIntent remains proposal-only and non-authorizing.
Blocked/follow-up gap-to-ComponentCoverage blocker lineage remains a downstream
gap unless a later phase solves it without packet sprawl.

`AG-SCRUTINEER-REVIEW-01` now adds the first RunKernel-reduced Scrutineer MVP.
Fast has no Scrutineer in MVP. Balanced uses Scrutineer on red flags and should
preserve remediation budget when Scrutineer is invoked. Deep requires
Scrutineer later and reserves post-Scrutineer response budget, but full Deep
orchestration is not implemented here. Deep allows max 3 follow-up loops by
default and max 4 only with explicit RunKernel extra recovery authorization.

`AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01` now adds the first Specialist MVP as
source-bound deterministic calculation only, not broad legal or technical
interpretation.

The AG-96 followup stack, offline SearchExecutor bridge, SearchWorkPlan shadow,
old Analyst/Economist/Scrutineer paths, source-class recovery bridges, and broad
pipeline orchestrator paths are legacy/passive/closed unless explicitly
reopened.

## 9. Follow-Up Search Authorization Reentry

`AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01` completes the first governed
remediation loop after the SemanticObservation admission bridge.
FollowupSearchIntent remains proposal-only and does not authorize search.
RunKernel owns follow-up search authorization, including mode budget, logical
depth, current-contract lineage, review readiness, duplicate-work checks, and
source-class criteria.

The authorized work identity/query bundle is not live dispatch. It is
SearchExecutorHandoff-style work identity only so existing candidate packet
lineage can reenter the chain. It does not mutate SearchExecutorHandoff state,
call providers, call a broker, run retrieval, perform live fetch/read, admit
evidence by itself, satisfy obligations, or create readiness.

Fixture-backed reentry proves the future product path without live providers:

```text
SearchResultCandidatePacket
-> FetchReadContentPacket
-> EvidenceLedger
-> EvidenceRelativeAnalysisPacket
-> SemanticObservation
-> ComponentCoverage
```

Readable support can reduce through SemanticObservation admission and
ComponentCoverage. Unreadable, stale, insufficient, or contradictory outcomes
remain blocked/follow-up-required/contested without support. No
Sufficiency/FAP/Author/citation/source-obligation satisfaction/product
correctness is proved.

## 10. Scrutineer Review

`AG-SCRUTINEER-REVIEW-01` introduces Scrutineer as a supervisory
review/sign-off layer for Analyst work product, not product authority. It can
perform initial review and final verification over Analyst support,
SemanticObservation admission, ComponentCoverage posture, FollowupSearchIntent
refs, follow-up authorization projection refs, fixture-backed reentry refs, and
unresolved blocked/follow-up/contested posture.

Scrutineer does not authorize search and does not run remediation. It can
require remediation and point to follow-up proposal refs. Follow-up
authorization remains RunKernel-owned through
`AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01`.

If Analyst and Scrutineer remain in conflict, contested posture must be
preserved for future FAP/Author. A signed-off Scrutineer review signs off only
Analyst work product; it does not sign off a final answer and does not claim
product correctness.

Fast has no Scrutineer in MVP. Balanced uses Scrutineer on red flags and should
preserve remediation budget when Scrutineer is invoked. Deep requires
Scrutineer later and more remediation budget, but full Deep orchestration is not
implemented by this phase.

## 11. Specialist Source-Bound Calculation

`AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01` introduces Specialist as a
RunKernel-reduced source-bound deterministic calculation seam. Inputs must be
source-bound and lineage-preserving, with typed numeric values, units, component
ids, input digests, currentness/source-class posture, caveats, and
source/custody/content/SemanticObservation/Analyst refs when available.

Supported operators are `sum`, `difference`, `product`, `ratio`, `percentage`,
`percentage_point_difference`, `simple_rate`, and `weighted_average`.
Invalid, stale, contradictory, mixed-unit, missing-unit, missing-lineage,
non-numeric, denominator-zero, or unsupported-formula calculations remain
blocked, invalid_input, or contested. The runtime does not parse arbitrary
formulas, execute arbitrary code, infer missing values, or calculate from
raw/unbounded text.

Specialist is not product authority. A successful Specialist calculation does
not create ComponentCoverage, Sufficiency, FinalAnswerPacket, Author input,
citation eligibility, source-obligation satisfaction, current_answer_contract
mutation, or product correctness. Scrutineer can review Specialist calculation
posture and flag unsupported calculation, stale input, contradiction, or missing
source-bound lineage, but Scrutineer does not calculate or authorize Specialist
output. Existing Economist surfaces remain legacy/passive unless deliberately
reused without authority revival.

## 12. Sufficiency Readiness

`AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01` introduces
RunKernel.SufficiencyReadiness as the pre-FAP readiness reducer.
SufficiencyReadiness is RunKernel-owned. It produces component-level and
answer-level readiness from the current answer contract, ComponentCoverage,
admitted SemanticObservation refs, ScrutineerReview posture, Specialist
calculation posture, and follow-up budget posture.

The reducer writes `sufficiency_readiness_state`,
`sufficiency_readiness_projection`, and `sufficiency_readiness_history`. It
supports `full_answer_ready`, `partial_answer_ready`, `blocked`,
`followup_required`, `contested`, `insufficient_evidence`, and `not_applicable`
posture. It emits a safe `fap_handoff_preview` containing refs, caveats, and
prohibited upgrades only.

SufficiencyReadiness does not create FinalAnswerPacket, Author input, answer
prose, citation eligibility, source-obligation satisfaction,
current_answer_contract mutation, live calls, provider/broker/retrieval/
fetch/read/model behavior, or product correctness. Old AG-92C Sufficiency/FAP
and AG-96/FAP/Author surfaces remain legacy/passive/closed unless explicitly
reopened.

## 13. FinalAnswerPacket Hardening

`AG-FINAL-ANSWER-PACKET-HARDENING-01` opens the hardened FAP handoff surface as
RunKernel.FinalAnswerPacket. It consumes SufficiencyReadiness and writes the
existing canonical `final_answer_packet` stage/state slot:
`state.final_answer_packet`, `state.final_answer_authority_projection`, and
`state.projections["final_answer_packet"]`.

The reducer maps `full_answer_ready`, `partial_answer_ready`, `blocked`,
`followup_required`, `contested`, `insufficient_evidence`, and
`not_applicable` into `full_answer_packet_ready`,
`partial_answer_packet_ready`, `blocked_answer_packet`,
`followup_required_packet`, `contested_answer_packet`,
`insufficient_evidence_packet`, and `not_applicable`. For `not_applicable`, it
records a no-packet posture with `packet_created: false` and no normal
`packet_id`.

The hardened FAP does not use old AG-92C/AG-96 FAP/Author authority, does not
execute Author or create prose, does not create executable Author input, does
not mutate `current_answer_contract`, does not run live calls, and does not
claim product correctness. It preserves citation requirements but defers
citation eligibility/rendering. It preserves source-obligation posture but does
not satisfy source obligations. AuthorProseFinalization now consumes this
hardened FAP surface.

## 14. AuthorProseFinalization

AUTHOR-PROSE-ONLY-FINALIZATION-01 adds AuthorProseFinalization as the
prose-only finalization surface. It consumes hardened FAP only and applies
AuthorProsePolicy knobs for
style/format/brevity/source-pass-through/uncertainty, partial-answer,
blocked-answer, and citation-display presentation.

RunKernel authorizes `AUTHOR_PROSE_FINALIZE`, reduces
`AUTHOR_PROSE_FINALIZED`, and writes `author_prose_state`,
`author_prose_projection`, `author_prose_history`, and
`projections["author_prose_finalization"]`. It does not write canonical output
to legacy `author_observation` / `final_answer_outcome`.

The surface does not call a model or provider, does not execute old Author,
does not render citations, does not satisfy source obligations, does not claim
product correctness, and does not mutate current_answer_contract.

AuthorProseConformanceReview is dogfood/testing-only. It checks for authority
laundering in tests and dogfood review, but it is not production-blocking.

## 15. Immediate Roadmap

1. `AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01` - this docs phase. It records that
   SearchExecutorHandoff is search intent only, defines the second-half
   packet/report chain, and narrows the next live step to search-result
   candidate validation.
2. `AG-LIVE-XAXIS-VALIDATION-01A` - search-only live validation. PR1 consumes
   `current_answer_contract` plus `SearchExecutorHandoff` directly, authorizes
   a fake-provider validation action, and emits sanitized
   `SearchResultCandidate` records only. PR2 adds broker/direct live
   invocation scaffolding. LIVE-RUN-01 adds the inert request-packet and
   broker-envelope harness but does not run provider or broker transport unless
   separately licensed. No fetch/read, custody, citations, source-obligation
   satisfaction, Sufficiency, FAP, Author, partial-answer readiness, or product
   correctness claims.
3. `AG-SEARCH-RESULT-CANDIDATE-PACKET-01` - define and reduce
   `SearchResultCandidatePacket` from sanitized result candidates.
4. `AG-FETCH-READ-CONTENT-REFERENCE-01` - create `FetchReadContentPacket` and
   `SanitizedContentReference` inputs from authorized candidate fetch/read,
   still without claiming readiness.
5. `AG-EVIDENCE-LEDGER-CANDIDATE-CUSTODY-01` - reduce validated
   `FetchReadContentPacket` / `SanitizedContentReference` records into
   EvidenceLedger candidate/content custody, preserving lineage only and still
   without semantic support, citations, source-obligation satisfaction,
   Sufficiency, FAP, Author input, partial readiness, or product correctness.
6. `AG-ANALYST-EVIDENCE-RELATIVE-REPORT-01` - introduce
   `EvidenceRelativeAnalysisPacket` with embedded `analyst_report` over
   EvidenceLedger fetch/read custody. It records proposal-only
   evidence-relative meaning after EvidenceLedger custody, including findings,
   caveats, contradictions, and analysis gap proposals, but it is not
   SemanticObservation admission and does not create ComponentCoverage,
   citation eligibility, source-obligation satisfaction, Sufficiency,
   FinalAnswerPacket, Author input, readiness, search dispatch, or product
   correctness.
7. `AG-ANALYSIS-GAP-FOLLOWUP-SEARCH-01` - introduce
   `FollowupSearchIntentPacket` and `AnalysisGapSearchProposal` as the
   proposal-only gap-to-search-intent posture after Analyst gap proposals. It is
   not search authorization, not a query plan, does not create
   SearchExecutorHandoff, does not dispatch search, does not create evidence,
   and RunKernel/SearchPlanner/SearchExecutorHandoff authorization remains
   required.
8. `AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01` - complete in PR #342. It proved
   that ComponentCoverage can reduce meaningful support only after
   SemanticObservation admission exists, and that the current packet chain alone
   does not admit semantic support.
9. `AG-DOC-SEMANTIC-COVERAGE-CHECKPOINT-01` - memorialize the post-#342
   doctrine, Project Source refresh packet, packet/bridge budget rule, and next
   implementation gate.
10. `AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` - completed implementation.
    Bridges Analyst support findings into RunKernel-authorized
    `SemanticObservation` admission and immediately proves ComponentCoverage
    consumption. It does not add another durable proposal packet.
11. `AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01` - completed implementation.
    Adds the first governed remediation loop: RunKernel authorizes bounded
    follow-up search work from proposal-only FollowupSearchIntent, and
    fixture-backed reentry proves the existing candidate/read/custody/analysis/
    admission/coverage chain without live providers.
12. `AG-SCRUTINEER-REVIEW-01` - completed implementation. Adds
    RunKernel-reduced ScrutineerReview initial review and final verification
    over Analyst/admission/coverage/remediation posture. It does not authorize
    search, run remediation, create Sufficiency/FAP/Author/citation/
    source-obligation satisfaction, or claim product correctness.
13. `AG-SPECIALIST-SOURCE-BOUND-CALCULATION-01` - completed Specialist start
    point for source-bound deterministic calculation only.
14. `AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01` - completed pre-FAP
    RunKernel-owned readiness reduction for full/partial/blocked/follow-up/
    contested/insufficient/not-applicable posture without creating FAP or
    Author input.
15. `AG-FINAL-ANSWER-PACKET-HARDENING-01` - completed hardened FAP handoff.
    It consumes SufficiencyReadiness and preserves
    full/partial/blocked/follow-up/contested/insufficient/not-applicable posture
    without Author prose, citation rendering, source-obligation satisfaction,
    live calls, or product-correctness claims.
16. `AUTHOR-PROSE-ONLY-FINALIZATION-01` - completed prose-only finalization.
    It consumes hardened FAP only, exposes presentation knobs, and keeps model
    calls, old Author execution, citation rendering, source-obligation
    satisfaction, current_answer_contract mutation, legacy output slots, and
    product-correctness claims closed.

The historical broad `AG-LIVE-BOUND-01` product-run plan is later planning
history. It is not the immediate post-#330 validation plan and must not be used
to claim search-only candidate validation, source custody, citations,
Sufficiency, FAP, Author behavior, or product correctness.

The runtime contract vocabulary remains merge-stable: `initial_answer_contract`
is the immutable AG-SEM-05 accepted genesis contract, while
`current_answer_contract` is the latest active accepted contract after
RunKernel applies admitted amendments. SearchExecutorHandoff and the first live
validation must prefer `current_answer_contract`.
