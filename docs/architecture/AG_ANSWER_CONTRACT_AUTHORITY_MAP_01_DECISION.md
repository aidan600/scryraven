# AG-ANSWER-CONTRACT-AUTHORITY-MAP-01 Decision

Status: implemented as a passive RunKernel-owned schema/projection surface after
PR #317 on main `4416cbc`. No runtime SearchExecutor wiring,
provider/search/fetch/retrieval behavior, Author behavior, prompt behavior,
citation behavior, partial-answer readiness, or live validation is licensed by
this note. Current integrated doctrine after PR #323 is
`RUN_CONTRACT_SEMANTIC_LOOP.md`.

## Decision

`AG-ANSWER-CONTRACT-AUTHORITY-MAP-01` established a RunKernel-owned passive
AnswerContractAuthorityMap before runtime SearchExecutor wiring.

AnswerContractAuthorityMap ties:

- required answer components;
- delegated component-scoped search work;
- evidence, citation, and source obligations;
- SemanticObservation / ComponentCoverage support;
- SufficiencyJudgment answerability;
- FinalAnswerPacket Author-safe payload readiness;
- prose-only Author handoff.

## Recent Main Context

- PR #312 `AG-LIVE-BLOCKED-FAP-GUARD-01`: blocked FinalAnswerPacket is guarded
  before Author input derivation.
- PR #313 `AG-LIVE-BLOCKED-FAP-SAFE-SUMMARY-01`: safe blocked-FAP summaries are
  attached to failure observability.
- PR #314 `AG-PARTIAL-ANSWER-BLOCKED-SUMMARY-01`: component-level blocked-FAP
  summary telemetry exists for blocked semantic multipart/source-bound numeric
  cases.
- PR #315 `AG-COMPONENT-EXECUTOR-CONTRACT-01`: offline ComponentPlan /
  component executor contract preserves planned components into passive
  SearchWork/query-work/scorekeeping, without wiring runtime model, search,
  fetch, retrieval, or Author behavior.
- PR #317 `AG-ANSWER-CONTRACT-AUTHORITY-MAP-01`: RunKernel owns a passive
  AnswerContractAuthorityMap that observes component work, evidence custody,
  semantic coverage, Sufficiency, FinalAnswerPacket readiness, and Author-safe
  handoff posture without activating runtime SearchExecutor behavior.
- PR #318 `AG-COMPONENT-SEARCHPLAN-SUBORDINATION-01`: ComponentPlan /
  ComponentSearchPlan naming and subordination cleanup is complete. Runtime
  SearchExecutor wiring remains out of scope, and no live validation was run.
- PR #319 `AG-OFFLINE-SEARCH-EXECUTOR-BRIDGE-01`: the offline
  RunKernel-owned SearchExecutor bridge is complete. It is offline/inert and
  not user-facing runtime search; it does not perform live provider/search/
  fetch/read/retrieval work, admit EvidenceLedger custody, or satisfy source
  obligations. Candidate observations remain non-evidence.
- PR #320 `AG-COMPONENT-SCOPED-SOURCE-CUSTODY-01`: EvidenceLedger
  component-scoped source custody is added from offline bridge output. Candidate
  links remain non-evidence until fetched/read/admitted by a later phase, and
  source obligations are unsatisfied/pending rather than satisfied by candidate
  presence.
- PR #321 `AG-COMPONENT-EVIDENCE-CITATION-BINDING-01`: the existing
  AnswerContractAuthorityMap per-component binding status consumes
  EvidenceLedger component-scoped custody while preserving candidate links and
  custody gaps as non-authorizing blockers.
- PR #322 `AG-SUFFICIENCY-FAP-COMPONENT-READINESS-01`: existing
  SufficiencyJudgment and FinalAnswerPacket owners consume passive
  binding/custody inputs into component-aware blocked readiness without making
  those inputs readiness authorities.
- PR #323 `AG-OFFLINE-XAXIS-E2E-01`: the offline X-axis end-to-end proof runs
  through blocked FAP / Author handoff after a component-shaped plan already
  exists. It does not enable partial answers and does not enable live
  validation.

## Authority Hierarchy

- RunKernel / RunAuthority remains root authority.
- AnswerContractAuthorityMap is owned by RunKernel and maps answer-component
  obligations to subordinate work and readiness owners.
- ComponentPlan is legacy/compat input terminology for subordinate
  component-search planning.
- ComponentSearchPlan is the preferred subordinate component-search planning
  name.
- Offline SearchExecutor bridge observations preserve delegated
  component-scoped work for the next custody phase, but SearchExecutor surfaces
  must not decide answerability.
- EvidenceLedger owns evidence custody, source obligations, and citation
  eligibility inputs.
- SemanticObservation / ComponentCoverage owns component support.
- SufficiencyJudgment owns answerability.
- FinalAnswerPacket owns Author-safe payload readiness.
- Author remains prose-only and consumes safe handoff material; it does not
  decide evidence custody, component support, answerability, or readiness.
- SemanticProducer, SearchPlanner, Scout, and SearchExecutor are workers. They
  may propose semantic meaning, component requirements, disambiguation reports,
  search plans, observations, or amendments when RunKernel authorizes the work,
  but they do not mutate accepted contract state.
- Contract mutation must flow through RunKernel-authorized reducers or an
  equivalent accepted-contract versioning path. AG-SEM-08 admits amendment
  proposals but does not yet apply/mutate the accepted contract.

## Non-Goals

- Do not wire ComponentPlan into runtime.
- Do not activate runtime SearchExecutor behavior or user-facing runtime
  search.
- Do not implement partial-answer readiness.
- Do not change provider routing, retrieval, citation behavior, Author
  behavior, caps, prompts, query generation, or persistence shape.
- Do not run live validation.
- Do not access secrets, `.env`, raw provider payloads, raw prompts, raw model
  responses, DB/cache rows, private logs, full traces, output packets, `output/`,
  or unrelated artifacts.
- Do not make ComponentPlan, ComponentSearchPlan, SearchWork, QueryPlan, or
  SearchExecutor top-level authority.

## Near-Term Roadmap

1. Add the AnswerContract authority map.
2. Clean up ComponentSearchPlan naming and subordination. Complete in PR #318.
3. Add the Offline SearchExecutor bridge. Complete in PR #319. The completed
   bridge is offline and inert, does not perform live provider/search/fetch/
   read/retrieval work, does not admit EvidenceLedger custody or satisfy source
   obligations, keeps candidate observations non-evidence, and is not
   user-facing runtime search.
4. Add component-scoped source custody. Complete in PR #320 /
   AG-COMPONENT-SCOPED-SOURCE-CUSTODY-01. EvidenceLedger consumes offline bridge
   observations for component-scoped source requirements, candidate links,
   custody gaps, and unsatisfied/pending source-obligation state. Candidate
   links remain non-evidence until fetched/read/admitted by a later phase, and
   source obligations are unsatisfied/pending rather than satisfied by candidate
   presence.
5. Bind component evidence and citations. Complete in
   AG-COMPONENT-EVIDENCE-CITATION-BINDING-01: the existing
   AnswerContractAuthorityMap per-component binding status consumes
   EvidenceLedger component-scoped custody and preserves offline candidate links
   and custody gaps as component-specific blockers without upgrading custody
   presence into evidence, citation, source-obligation, answer-value,
   readiness, partial-answer, or Author authority.
6. Bind Sufficiency / FinalAnswerPacket component readiness. Complete in PR
   #322 / AG-SUFFICIENCY-FAP-COMPONENT-READINESS-01 using existing
   SufficiencyJudgment and FinalAnswerPacket owners; passive binding/custody
   inputs do not themselves decide readiness.
7. Prove the offline X-axis end-to-end through blocked FAP / Author handoff.
   Complete in PR #323 / AG-OFFLINE-XAXIS-E2E-01. It does not enable partial
   answers and does not enable live validation.
8. Connect the semantic lane and component/search/X-axis lane with the current
   integrated doctrine in
   `docs/architecture/RUN_CONTRACT_SEMANTIC_LOOP.md`. The doctrine is:
   semantic producer / planner understands; RunKernel governs; AnswerContract
   records obligations and statuses; workers propose observations or amendments;
   RunKernel validates/reduces; EvidenceLedger records custody;
   SemanticObservation records evidence-relative meaning; ComponentCoverage
   records component support; SufficiencyJudgment decides readiness;
   FinalAnswerPacket packages Author-safe handoff; Author writes prose only.
9. The post-merge next gate is AG-RUN-CONTRACT-MUTATION-LOOP-01: implement or
   clarify accepted-contract amendment application/status updates through
   RunKernel authority. Bounded live validation is deferred until the upstream
   semantic-contract/planner/scout/search-executor runtime loop exists.
   Partial-answer readiness remains deferred until later policy.

## Semantic Lane Cross-References

- `AG_SEM_01_PASSIVE_SEMANTIC_CONTRACT_FOUNDATION.md`
- `AG_SEM_02_SANITIZED_CONTENT_REFERENCE_AND_SEMANTIC_OBSERVATION.md`
- `AG_SEM_04_CONTRACT_AMENDMENT_RECORD.md`
- `AG_SEM_05_INITIAL_ANSWER_CONTRACT_ACCEPTANCE.md`
- `AG_SEM_07_COMPONENT_COVERAGE_REDUCTION.md`
- `AG_SEM_08_CONTRACT_AMENDMENT_ADMISSION.md`
- `AG_SEM_09_SUFFICIENCY_SEMANTIC_CONSUMPTION.md`
- `AG_SEM_11_ORDINARY_SEMANTIC_PRODUCER_VERTICAL_SLICE.md`
- `AG_SEM_11B_ORDINARY_SEMANTIC_PRODUCER_HARDENING.md`

Passive/shadow surfaces are not product readiness. A dataclass, trace key, test
fixture, passive projection, shadow query-plan field, or prompt-only policy does
not count unless the intended runtime owner consumes it and a focused test proves
the real consumer path.
