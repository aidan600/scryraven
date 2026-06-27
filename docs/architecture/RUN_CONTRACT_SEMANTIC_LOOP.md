# Run-Contract Semantic Loop

## 1. Status

Status: Current doctrine after AG-SEARCH-PLANNER-REVISION-01 and before
SearchExecutor handoff.

Proof class: `docs_architecture_update`.

Previous baseline: PR #328 / AG-SCOUT-DISAMBIGUATION-RUNTIME-01. This PR:
AG-SEARCH-PLANNER-REVISION-01 adds RunKernel-authorized planner revision from a
Scout DisambiguationReport. The planner revision consumes Scout report output,
stores revision state/projection/history, and the planner revision emits passive
amendment candidates. Scout hints remain non-evidence, non-citation, and
non-source-obligation satisfaction. current_answer_contract changes only
through existing admission/application path. SearchExecutor,
fetch/read/retrieval remain closed. The post-merge next gate is
AG-SEARCH-EXECUTOR-HANDOFF-01.
SearchPlannerRevision exact posture: PR #328 / AG-SCOUT-DISAMBIGUATION-RUNTIME-01; AG-SEARCH-PLANNER-REVISION-01; planner revision consumes Scout report; planner revision emits passive amendment candidates; Scout hints remain non-evidence, non-citation, and non-source-obligation satisfaction; current_answer_contract changes only through existing admission/application path; SearchExecutor, fetch/read/retrieval remain closed; post-merge next gate is AG-SEARCH-EXECUTOR-HANDOFF-01.
Historical Scout exact posture: PR #327 / AG-SEARCH-PLANNER-MODEL-01; AG-SCOUT-DISAMBIGUATION-RUNTIME-01; RunKernel-authorized; report-only; Serper-shaped; fake injected adapters only; No live Serper/search/provider/model/fetch/read/retrieval calls were run; Scout hints are not evidence; not citations; not source-obligation satisfaction; Scout does not mutate contracts; Scout does not revise planner output; post-merge next gate is AG-SEARCH-PLANNER-REVISION-01.
Historical SearchPlannerModel exact posture: PR #327 / AG-SEARCH-PLANNER-MODEL-01; AG-SEARCH-PLANNER-RUNTIME-01; AG-SEARCH-PLANNER-MODEL-01 adds an explicit injected fail-closed model adapter; No live model calls or live validation were run; AG-SCOUT-DISAMBIGUATION-RUNTIME-01; Scout hints are not evidence; post-merge next gate is AG-SEARCH-PLANNER-REVISION-01.

This document connects the AG-SEM semantic accountability lane with the
component/search/X-axis lane proved through the offline blocked
FinalAnswerPacket / Author handoff.

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

## 2. The Integrated Product Loop

Intended runtime loop:

```text
1. User query arrives.
2. RunKernel starts a seed contract / run contract with minimal known obligations.
3. SemanticProducer / SearchPlanner proposes question meaning, semantic slots, answer components, ambiguity posture, and initial requirements.
4. RunKernel validates and accepts or rejects canonical contract state.
5. If ambiguity needs cheap exploration, RunKernel authorizes Scout.
6. Scout searches bounded cheap disambiguation dimensions and reports a DisambiguationReport.
7. Planner consumes Scout report and proposes revised/final ComponentSearchPlan and contract amendments.
8. RunKernel validates/reduces the amended contract state.
9. RunKernel authorizes SearchExecutor from the accepted plan/contract.
10. SearchExecutor reports candidate/search/fetch/read/admission observations.
11. EvidenceLedger records custody and source-obligation state.
12. SemanticObservation / ComponentCoverage record evidence-relative semantic support.
13. ContractAmendmentRecord may propose new/changed obligations when meaning/evidence changes.
14. RunKernel admits/applies allowed amendments through reducers.
15. SufficiencyJudgment consumes contract/custody/semantic/binding state and decides readiness.
16. FinalAnswerPacket packages safe Author handoff.
17. Author writes prose only from FAP-safe material.
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

The next product problem is upstream: user query meaning, accepted answer
contract, planner/scout revision, authorized SearchExecutor work, semantic
observations, component coverage, contract amendments, Sufficiency, FAP, and
Author handoff in one governed loop.

## 3. Ownership Boundaries

| Surface | Owner boundary |
| --- | --- |
| RunKernel / RunAuthority | Owns canonical run authority, action authorization, reducer gating, accepted contract state, and contract mutation/application authority. |
| SemanticProducer / SearchPlanner | Proposes query meaning, semantic slots, answer components, material ambiguities, and component search requirements. It does not mutate the accepted contract directly. |
| Scout | Performs bounded cheap disambiguation reconnaissance when RunKernel authorizes it. Reports dimensions, candidate interpretations, likely official/current targets, and URLs/hints. It does not decide final plan or mutate contract. |
| SearchPlanner revision | Consumes Scout report and proposes revised plan/amendments. It does not own authority. |
| SearchExecutor | Performs bounded search/fetch/read/admission work when authorized. It does not decide answerability/readiness. |
| EvidenceLedger | Owns evidence custody and source-obligation state. |
| SemanticObservation | Records evidence-relative semantic observations. |
| ComponentCoverage | Owns component support/coverage reduction. |
| ContractAmendmentRecord / admission / future application | Provides the proposal/admission/application pathway for adding, superseding, satisfying, failing, blocking, or declaring not-applicable requirements. |
| AnswerContractAuthorityMap | Passive authority map over components, custody, binding, readiness, and FAP state. It does not mutate the contract. |
| SufficiencyJudgment | Owns answerability/readiness decision. |
| FinalAnswerPacket | Owns Author-safe handoff. |
| Author | Prose-only; no custody, support, readiness, citation, or contract authority. |

## 4. Contract Mutation Discipline

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

AG-SEM-08 admits amendment proposals, but it does not apply or mutate the
accepted contract. Future implementation must decide whether to add an amendment
application reducer or an equivalent accepted-contract versioning path. That
future path must be RunKernel-authorized, typed, versioned, and test-proved
through the real consumer.

## 5. Semantic Accountability Discipline

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
- semantic observation
- component coverage
- semantic blocker
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
integration doctrine for connecting that semantic authority to
ComponentSearchPlan, Scout, SearchExecutor, EvidenceLedger, Sufficiency,
FinalAnswerPacket, and Author.

## 6. Shadow/Passive Surface Warning

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

## 7. Immediate Roadmap

1. `AG-RUN-CONTRACT-SEMANTIC-LOOP-DOCS-01` - completed baseline.
2. `AG-RUN-CONTRACT-MUTATION-LOOP-01` - this phase implements RunKernel-owned
   admitted-amendment application into `current_answer_contract`.
3. `AG-SEARCH-PLANNER-RUNTIME-01` - completes the RunKernel-authorized
   SearchPlanner proposal seam: an explicitly injected adapter can produce a
   passive QMR-compatible proposal plus subordinate component-search
   requirements, while live model/search/fetch/read/retrieval behavior remains
   closed and amendments remain deferred.
4. `AG-SEARCH-PLANNER-MODEL-01` - adds an explicit injected fail-closed model adapter
   and prompt/input contract behind the same SearchPlanner runtime seam. Tests use
   fake injected model callables, and no live model calls or live validation were
   run.
5. `AG-SCOUT-DISAMBIGUATION-RUNTIME-01` - adds a RunKernel-authorized,
   report-only, Serper-shaped Scout DisambiguationReport runtime with fake
   injected adapters only.
6. `AG-SEARCH-PLANNER-REVISION-01` - planner revision consumes Scout report and
   emits passive amendment candidates through existing amendment admission and
   application.
7. `AG-SEARCH-EXECUTOR-HANDOFF-01` - RunKernel authorizes real
   search/fetch/read/admission path.
8. `AG-LIVE-XAXIS-VALIDATION-01` - bounded live validation only after the
   upstream runtime loop is real.
9. `AG-PARTIAL-ANSWER-READINESS-01` - later policy layer.

AG-SEARCH-PLANNER-RUNTIME-01 completes the first fail-closed SearchPlanner
proposal runtime seam. AG-SEARCH-PLANNER-MODEL-01 adds an explicit injected
fail-closed model adapter behind that seam. Planner model output remains
proposal-only and is consumed through existing RunKernel planner and contract
reducers. PR #327 / AG-SEARCH-PLANNER-MODEL-01 is the previous baseline.
AG-SEARCH-PLANNER-MODEL-01 adds an explicit injected fail-closed model adapter.
No live model calls or live validation were run.
Previous baseline: PR #328 / AG-SCOUT-DISAMBIGUATION-RUNTIME-01.
AG-SEARCH-PLANNER-REVISION-01 adds RunKernel-authorized planner revision from a
Scout DisambiguationReport. The planner revision consumes Scout report output,
stores revision state/projection/history, and the planner revision emits passive
amendment candidates. Scout hints remain non-evidence, non-citation, and
non-source-obligation satisfaction. current_answer_contract changes only
through existing admission/application path. SearchExecutor,
fetch/read/retrieval remain closed. Author, citations, partial answers, and
live validation remain closed. The post-merge next gate is
AG-SEARCH-EXECUTOR-HANDOFF-01.

The runtime contract vocabulary is merge-stable: `initial_answer_contract`
remains the immutable AG-SEM-05 accepted genesis contract, while
`current_answer_contract` is the latest active accepted contract after
RunKernel applies an admitted amendment. Sufficiency consumers prefer
`current_answer_contract` and fall back to `initial_answer_contract` when no
application has occurred.
