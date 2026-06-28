# Run-Contract Semantic Loop

## 1. Status

Status: Current doctrine after PR #330 /
`AG-SEARCH-EXECUTOR-HANDOFF-01` and PR2 of
`AG-LIVE-XAXIS-VALIDATION-01A`.

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
SemanticObservation records evidence-relative meaning.
ComponentCoverage records component support.
SufficiencyJudgment decides readiness.
FinalAnswerPacket packages Author-safe handoff.
Author writes prose only.
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
15. EvidenceRelativeAnalysisPacket / AnalystReport records evidence-relative meaning.
16. SpecialistAnalysisPacket records specialized analysis when needed.
17. ScrutineerReview reviews support, conflicts, drift, and gaps.
18. ComponentCoverageRecord proposals bind admitted observations to components.
19. ContractAmendmentRecord proposals add/revise/supersede obligations when evidence changes meaning.
20. SufficiencyJudgment consumes contract/custody/semantic/coverage/amendment state and decides readiness.
21. FinalAnswerPacket packages Author-safe material.
22. Author writes prose only from FAP-safe material.
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
| SearchResultCandidatePacket | Future packet for sanitized result candidates. It is not EvidenceLedger custody and does not satisfy obligations. |
| FetchReadContentPacket / SanitizedContentReference | bounded readable-content handoff after SearchResultCandidatePacket and before EvidenceLedger custody. It is not evidence, not citation-eligible, and does not satisfy source obligations. |
| EvidenceLedger fetch/read candidate custody | RunKernel-authorized reducer that admits FetchReadContentPacket / SanitizedContentReference packet, candidate, reference, status, URL/domain/title, and bounded-content count/digest lineage into EvidenceLedger candidate/content custody. It is not semantic support, citation eligibility, source-obligation satisfaction, ComponentCoverage, Sufficiency, FinalAnswerPacket material, Author input, partial readiness, or product correctness. |
| EvidenceLedger | Owns evidence custody and source-obligation state after admissible sanitized content exists. |
| SemanticObservation | Records evidence-relative semantic observations. |
| EvidenceRelativeAnalysisPacket / AnalystReport | Future evidence-relative analysis report that consumes admitted custody/content and records meaning, caveats, conflicts, and gaps without final prose authority. |
| SpecialistAnalysisPacket | Future specialist analysis packet when quantitative, legal, technical, or other specialist reasoning is needed. |
| ScrutineerReview | Future review packet for support, conflicts, drift, and gap review. |
| AnalysisGapSearchProposal | Future proposal from Analyst/Specialist/Scrutineer back to RunKernel when analysis reveals a search gap. It is a proposal, not a dispatch. |
| ComponentCoverageRecord | Owns component support/coverage proposals and reduction after admitted evidence-relative observations exist. |
| ContractAmendmentRecord / admission / application | Provides the proposal/admission/application pathway for adding, superseding, satisfying, failing, blocking, or declaring not-applicable requirements. |
| AnswerContractAuthorityMap | Passive authority map over components, custody, binding, readiness, and FAP state. It does not mutate the contract. |
| SufficiencyJudgment | Owns answerability/readiness decision after prerequisite custody, semantic, coverage, and amendment inputs exist. |
| FinalAnswerPacket | Owns Author-safe handoff. |
| Author | Prose-only; no custody, support, readiness, citation, or contract authority. |

Existing Analyst, Economist, and Scrutineer runtime surfaces are not yet a
coherent new RunKernel/current_answer_contract second-half semantic
architecture. Treat them as legacy, passive, bounded, or specialized surfaces
until a future phase wires an evidence-relative Analyst/Specialist/Scrutineer
packet chain into the current contract loop.

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

## 8. Immediate Roadmap

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
6. `AG-ANALYST-EVIDENCE-RELATIVE-REPORT-01` - define
   `EvidenceRelativeAnalysisPacket` / `AnalystReport` over admitted
   custody/content, with `AnalysisGapSearchProposal` for analysis-discovered
   gaps.
7. `AG-PARTIAL-ANSWER-READINESS-01` - later, only after the
   Analyst/Specialist/Scrutineer/Sufficiency/FAP prerequisites exist as a
   coherent evidence-relative chain.

The historical broad `AG-LIVE-BOUND-01` product-run plan is later planning
history. It is not the immediate post-#330 validation plan and must not be used
to claim search-only candidate validation, source custody, citations,
Sufficiency, FAP, Author behavior, or product correctness.

The runtime contract vocabulary remains merge-stable: `initial_answer_contract`
is the immutable AG-SEM-05 accepted genesis contract, while
`current_answer_contract` is the latest active accepted contract after
RunKernel applies admitted amendments. SearchExecutorHandoff and the first live
validation must prefer `current_answer_contract`.
