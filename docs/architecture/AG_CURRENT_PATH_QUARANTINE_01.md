# AG-CURRENT-PATH-QUARANTINE-01

Status: active quarantine and proof-class cleanup for the current path registry.

Proof class: `docs_only` plus phase-focused docs-posture/static guards.

Product-facing progress type: quarantine/docs-process work.

Product path affected: none. This phase changes repo-visible documentation and
guardrail tests only. It does not create a runtime product layer, packet,
reducer, semantic authority surface, provider/search/fetch/read/retrieval
behavior, citation behavior, Author behavior, or answer behavior.

Actual user-facing app delta: none. The ordinary product path and installed
behavior do not change in this phase.

User-facing/reviewable output delta: repo-visible classification, consumer-seam,
proof-class, old-path treatment, and non-proof doctrine only. No new user-facing
answer output is introduced.

Non-product exception leash: this phase is allowed only because it quarantines
existing ambiguity and blocks future proof-layer drift. It must not add runtime
behavior or another harness. The mandatory next product-path checkpoint is
`AG-FIXTURE-DOGFOOD-INTEGRATION-01`.

Existing machinery reused: current docs, current runtime/test seams, existing
AuthorProseFinalization static guards, and existing phase-focus tests.

New machinery introduced: this registry doc and phase-focused docs/static
guardrails only.

Why this is not reinventing an existing surface: it classifies and links
existing surfaces from normal entry points instead of creating a new runtime
authority, packet, reducer, projection, provider path, citation path, or Author
path.

Live validation: not run and not licensed for this phase.

## Current Authoritative Path

The current path is the RunKernel-governed chain below. Earlier stages create
accepted contract/search intent. Later stages convert sanitized candidates and
bounded content into custody, admitted meaning, coverage, readiness, a hardened
FinalAnswerPacket, and finally prose-only output.

```text
SearchPlanner / initial_answer_contract
-> Scout
-> SearchPlannerRevision
-> current_answer_contract
-> SearchExecutorHandoff
-> SearchResultCandidatePacket
-> FetchReadContentPacket / SanitizedContentReference
-> EvidenceLedger candidate/content custody
-> EvidenceRelativeAnalysisPacket / AnalystReport
-> FollowupSearchIntentPacket / AnalysisGapSearchProposal
-> RunKernel follow-up search authorization and fixture-backed reentry
-> SemanticObservation admission
-> ComponentCoverage reduction
-> ScrutineerReview
-> Specialist source-bound calculation
-> SufficiencyReadiness
-> hardened FinalAnswerPacket
-> AuthorProseFinalization
```

This path is authoritative only at each stage's bounded responsibility. It is
not proof of ordinary-query execution, live source acquisition quality, citation
rendering, source-obligation satisfaction, product correctness, or
product-quality prose.

## Classification Vocabulary

Use these labels in future phase summaries and reviews:

| Classification | Meaning |
| --- | --- |
| current authority path | Current RunKernel/RunAuthority-governed path or accepted state consumed by the named next stage. |
| current passive/supporting projection | Current support state, projection, helper, or doc that is useful but does not itself decide authority. |
| fixture-only proof | Test fixture proof that validates a seam without live providers or ordinary user-query product proof. |
| offline harness | Offline executable harness or bridge for structure/proof only, not live or product authority. |
| live-search-only validation | Licensed or license-ready search-only validation that may emit sanitized candidates only. |
| product-facing dry-run proof | Offline human-readable product-shaped output that is reviewable but not live/product correctness proof. |
| legacy/passive/historical | Retained compatibility/history surface. It must not be treated as current authority unless reopened. |
| closed/protected unless separately licensed | Safety-sensitive behavior kept out of scope until a phase explicitly licenses it. |

## Current-Path Registry

| Surface | Primary repo surfaces | Classification | Consumer/treatment |
| --- | --- | --- | --- |
| SearchPlanner / initial answer contract | `core/search_planner_runtime.py`, `core/initial_answer_contract_acceptance_runtime.py`, AG-SEM docs/tests | current authority path | Produces accepted initial contract state for RunKernel-governed amendment/application. No provider/model/live proof. |
| Scout | `core/scout_disambiguation_runtime.py`, `core/scout.py` | current authority path within bounded reconnaissance | Consumed by SearchPlannerRevision as search direction. Scout hints are not evidence, citations, or obligation satisfaction. |
| SearchPlannerRevision | `core/search_planner_revision_runtime.py` | current authority path as proposal/admission input | Proposes amendments; RunKernel admission/application owns accepted `current_answer_contract`. |
| `current_answer_contract` | RunKernel accepted contract state | current authority path | Consumed by SearchExecutorHandoff and downstream contract-bound reducers. |
| SearchExecutorHandoff | `core/search_executor_handoff_runtime.py` | current authority path for search intent | Consumed by search-only validation/handoff-shaped downstream candidate lineage. It does not execute search. |
| AG-LIVE-XAXIS validation harness | `scripts/ag_live_xaxis_validation_01a_live_run_01_harness.py`, live validation docs | live-search-only validation / offline harness | Can reduce supplied sanitized provider result JSON when licensed. It may produce sanitized candidates only. |
| SearchResultCandidatePacket | `core/search_result_candidate_packet.py`, `tests/test_ag_search_result_candidate_packet_01.py` | current authority path, fixture-only proof | Consumed by FetchReadContentPacket. Search candidates are not evidence. |
| FetchReadContentPacket / SanitizedContentReference | `core/fetch_read_content_reference.py`, `tests/test_ag_fetch_read_content_reference_01.py` | current authority path, fixture-only proof | Consumed by EvidenceLedger candidate custody. Fetch/read content is not semantic support. |
| EvidenceLedger candidate/content custody | `core/evidence_ledger_candidate_custody.py`, `core/evidence_ledger_runtime.py`, `tests/test_ag_evidence_ledger_candidate_custody_01.py` | current authority path for custody only | Consumed by EvidenceRelativeAnalysisPacket and SemanticObservation admission lineage. Custody is not component satisfaction. |
| EvidenceRelativeAnalysisPacket / AnalystReport | `core/evidence_relative_analysis_packet.py`, `tests/test_ag_analyst_evidence_relative_report_01.py` | current authority path as proposal-only analysis | Consumed by FollowupSearchIntent and SemanticObservation admission eligibility. Analyst proposal is not RunKernel authority. |
| FollowupSearchIntentPacket / AnalysisGapSearchProposal | `core/analysis_gap_followup_search_packet.py`, `tests/test_ag_analysis_gap_followup_search_01.py` | current authority path as proposal-only gap intent | Consumed by RunKernel follow-up authorization. It is not authorization, query plan, dispatch, evidence, or coverage. |
| Follow-up authorization / reentry | `core/followup_search_authorization_runtime.py`, `tests/test_ag_followup_search_authorization_reentry_01.py` | current authority path with fixture-only reentry proof | RunKernel authorizes bounded work identity/query bundle. Fixture reentry exercises candidate/read/custody/analysis/admission/coverage without live dispatch. |
| SemanticObservation admission | `core/semantic_observation_admission_bridge.py`, `core/semantic_observation_admission_runtime.py`, `tests/test_ag_semantic_observation_admission_bridge_01.py` | current authority path | Consumed immediately by ComponentCoverage. It admits meaning but does not create coverage by itself. |
| ComponentCoverage | `core/component_coverage_reduction_runtime.py`, `core/component_coverage_record.py`, `tests/test_ag_component_coverage_reliability_proof_01.py` | current authority path with fixture-only proof | Consumes admitted SemanticObservation and custody bindings. It is coverage, not final readiness. |
| ScrutineerReview | `core/scrutineer_review_runtime.py`, `tests/test_ag_scrutineer_review_01.py` | current authority path as supervisory review | Consumed by SufficiencyReadiness. Scrutineer sign-off is not product correctness. |
| Specialist source-bound calculation | `core/specialist_source_bound_calculation_runtime.py`, `tests/test_ag_specialist_source_bound_calculation_01.py` | current authority path for source-bound calculation only | Consumed by SufficiencyReadiness when numeric posture matters. Specialist calculation is not answer authority. |
| SufficiencyReadiness | `core/sufficiency_readiness_runtime.py`, `tests/test_ag_sufficiency_partial_answer_readiness_01.py` | current authority path | Consumed by hardened FinalAnswerPacket. It is readiness, not final answer prose. |
| Hardened FinalAnswerPacket | `core/final_answer_packet_hardening_runtime.py`, `tests/test_ag_final_answer_packet_hardening_01.py` | current authority path | Consumed by AuthorProseFinalization. Hardened FAP is not product correctness and does not render citations. |
| AuthorProseFinalization | `core/author_prose_finalization_runtime.py`, `core/author_prose_policy.py`, `tests/test_author_prose_only_finalization_01.py` | current authority path and product-facing dry-run proof | Consumes hardened FAP only and emits human-readable prose. It does not execute old Author, render citations, satisfy source obligations, or prove product-quality prose. |
| AuthorProseConformanceReview | `core/author_prose_conformance_runtime.py` | current passive/supporting projection / dogfood-only proof | Testing/dogfood review only; not production-blocking authority. |
| Old final-answer packet runtime paths | `core/final_answer_packet_runtime.py`, `core/final_answer_runtime_adapter.py`, old `core/final_answer_packet.py` usage where not explicitly supporting hardened FAP | legacy/passive/historical | Retained for compatibility and old tests. Current FAP authority is `core/final_answer_packet_hardening_runtime.py`. |
| Old Author execution paths | `core/author_execution_runtime.py`, `core/runtime_prompt_assembly.py`, broad old Author helpers | legacy/passive/historical and closed unless licensed | Must not be invoked by AuthorProseFinalization. |
| Old follow-up Author/FAP paths | `core/followup_author_*`, `core/followup_final_answer_packet_runtime.py`, AG-96 follow-up author lane | legacy/passive/historical | Retained for history/compat tests. Not current FAP or AuthorProse authority. |
| Old sufficiency judgment surfaces | `core/run_authority_sufficiency*.py`, `tests/test_runauthority_sufficiency_judge_ag92c.py`, related AG-92 docs | legacy/passive/historical | Current readiness path is SufficiencyReadiness, not old SufficiencyJudgment authority. |
| Old AG-89D / AG-91K / AG-92C / AG-96 tests | `tests/test_final_answer_packet_ag89d.py`, `tests/test_final_answer_author_runkernel_ag91k.py`, AG-92/AG-96 tests | legacy/passive/historical or sentinel compatibility | They may guard compatibility/history but do not prove the current AuthorProse path. |
| `core/pipeline_orchestrator.py` | broad product coordination shell | legacy/passive/historical and closed for this phase | Coordination shell with remaining authority debt. This phase does not change it or use it as proof. |
| `core/offline_search_executor_bridge.py` | old X-axis bridge | offline harness / legacy/passive/historical | Useful history for old proof shape. It is not the current SearchExecutorHandoff-consuming live path. |
| Historical docs | `docs/architecture/historical/*`, older AG-89/AG-91/AG-92/AG-96 docs | legacy/passive/historical | Retained as phase record. Current doctrine should route through this doc and the current-state/guidance docs. |
| Provider routing/search/fetch/read/retrieval/citation/Author behavior | provider wrappers, retrieval modules, citation rendering, old Author execution | closed/protected unless separately licensed | No behavior change and no live validation in this phase. |

## Consumer-Seam Matrix

| Lane | Producer | Consumer | RunKernel owner | Proof class | Current/legacy status | Human-reviewable product output | Explicit non-proofs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SearchPlanner to initial contract | SearchPlanner proposal | RunKernel contract acceptance | RunKernel / accepted contract state | component/offline structural proof | current authority path | no | no live model/provider proof, no product correctness |
| Scout | RunKernel-authorized Scout | SearchPlannerRevision | RunKernel authorizes Scout; revision proposes | component/offline proof | current authority path within reconnaissance | no | Scout hints are not evidence, citations, or source-obligation satisfaction |
| SearchPlannerRevision to current contract | Revision/amendment proposals | RunKernel admission/application | RunKernel | component/offline proof | current authority path | no | proposals are not accepted contract until admitted/applied |
| SearchExecutorHandoff | Current answer contract plus planner direction | Search-only validation / candidate packet lineage | RunKernel-gated handoff state | offline product-path projection proof | current authority path for intent only | no | no search execution, fetch/read, custody, citations, Sufficiency, FAP, Author |
| Search result candidates | Search-only validation or fixture candidate builder | SearchResultCandidatePacket / FetchReadContentPacket | RunKernel-owned validation when licensed | live-search-only validation or fixture-only proof | current path upstream of evidence | no | search candidates are not evidence or product correctness |
| SearchResultCandidatePacket | Sanitized candidates | FetchReadContentPacket | packet validation/reducer path | fixture-only proof | current authority path | no | no evidence, citation eligibility, source-obligation satisfaction |
| FetchReadContentPacket | Candidate-bound bounded content refs | EvidenceLedger custody | packet validation/reducer path | fixture-only proof | current authority path | no | fetch/read content is not semantic support or citation eligibility |
| EvidenceLedger custody | Fetch/read packet refs | Analyst packet and SemanticObservation lineage | RunKernel-authorized custody | fixture-only proof | current authority path for custody | no | custody is not component satisfaction, coverage, Sufficiency, FAP, Author |
| EvidenceRelativeAnalysisPacket | EvidenceLedger-bound Analyst proposal records | FollowupSearchIntent and SemanticObservation admission eligibility | proposal validation; RunKernel later admits meaning | fixture-only proof | current proposal path | no | Analyst proposal is not RunKernel authority or admitted support |
| FollowupSearchIntent | Analyst gap proposals | RunKernel follow-up authorization | RunKernel authorizes bounded work identity | fixture-only proof | current proposal path | no | not query plan, dispatch, search execution, evidence, or coverage |
| Follow-up reentry | RunKernel follow-up authorization plus fixture material | Candidate/read/custody/analysis/admission/coverage reducers | RunKernel authorization/reduction | fixture-only proof | current authority path in offline harness | no | no live dispatch, acquisition quality, citations, Sufficiency, FAP, Author |
| SemanticObservation admission | Eligible Analyst support proposal plus custody/content lineage | ComponentCoverage | RunKernel | component_harness_proof | current authority path | no | admission is not coverage by itself, citation eligibility, or source-obligation satisfaction |
| ComponentCoverage | Admitted SemanticObservation plus custody bindings | Scrutineer and SufficiencyReadiness | RunKernel reducer | component_harness_proof | current authority path | no | coverage is not readiness, product correctness, or final answer prose |
| ScrutineerReview | Analyst/admission/coverage/remediation posture | SufficiencyReadiness | RunKernel reducer | component_harness_proof | current authority path | no | Scrutineer sign-off is not product correctness or answer authority |
| Specialist calculation | Source-bound numeric inputs | SufficiencyReadiness | RunKernel reducer | component_harness_proof | current authority path | no | calculation is not answer authority, coverage, citations, or source obligations |
| SufficiencyReadiness | Contract, coverage, admitted meaning, Scrutineer, Specialist, follow-up posture | Hardened FinalAnswerPacket | RunKernel reducer | component_harness_proof | current authority path | structural only | not final answer prose, citation rendering, or source-obligation satisfaction |
| Hardened FinalAnswerPacket | SufficiencyReadiness | AuthorProseFinalization | RunKernel.FinalAnswerPacket | component_harness_proof | current authority path | structural only | not product correctness, old Author execution, citations, or source satisfaction |
| AuthorProseFinalization | Hardened FAP plus AuthorProsePolicy | User-reviewable prose projection | RunKernel.AuthorProseFinalization | product-facing dry-run proof | current authority path | yes, prose-only | does not prove citation rendering, source-obligation satisfaction, product correctness, or product-quality Author prose |
| AuthorProseConformanceReview | AuthorProse projection and FAP projection | Tests/dogfood reviewers | none as production authority | fixture-only proof | current passive/supporting projection | no | not production-blocking authority |
| Old FAP/Author/AG-96 lanes | Historical tests/runtimes | Compatibility tests or historical docs | old or compatibility owner | legacy/offline harness | legacy/passive/historical | maybe old test output only | not current path proof and must not be implied as current consumer |

## Quarantine Rules

Future phases should use the classifications above rather than reviving old
surfaces by implication.

- If a runtime has no current consumer, label it passive, fixture-only,
  historical, or legacy. Do not invent a consumer.
- If a test proves only fixture construction, label it fixture-only proof.
- If a harness reduces supplied sanitized search output but does not call a
  provider, label it offline harness or live-search-only validation, depending
  on the actual run license and execution facts.
- If output is human-readable but built from offline/fixture inputs, label it
  product-facing dry-run proof, not product correctness.
- If a surface touches provider routing, provider depth, retrieval ranking,
  prompts, citation behavior, source-obligation satisfaction, old Author
  execution, or live validation, keep it closed unless the phase explicitly
  licenses that exact behavior.

## Docs-Posture Guardrails

Future docs must not imply any of the following:

- search candidates are evidence;
- fetch/read content is semantic support;
- EvidenceLedger custody is component satisfaction;
- Analyst proposal is RunKernel authority;
- Scrutineer sign-off is product correctness;
- Specialist calculation is answer authority;
- SufficiencyReadiness is final answer prose;
- hardened FAP is product correctness;
- AuthorProseFinalization proves citation rendering;
- AuthorProseFinalization satisfies source obligations;
- fixture-only proof is product readiness;
- live-search-only proof is product correctness.

The required posture is the inverse:

- search candidates are not evidence;
- fetch/read content is not semantic support;
- EvidenceLedger custody is not component satisfaction;
- Analyst proposal is not RunKernel authority;
- Scrutineer sign-off is not product correctness;
- Specialist calculation is not answer authority;
- SufficiencyReadiness is not final answer prose;
- hardened FAP is not product correctness;
- AuthorProseFinalization does not prove citation rendering;
- AuthorProseFinalization does not satisfy source obligations;
- fixture-only proof is not product readiness;
- live-search-only proof is not product correctness.

## What This Phase Does Not Prove

This phase does not prove:

- ordinary-query execution;
- source acquisition quality;
- fetch/read survival on real sources;
- semantic support from messy live evidence;
- citation rendering;
- citation eligibility in user-visible output;
- source-obligation satisfaction;
- product correctness;
- product-quality Author prose.

## Future Summary Requirements

Future phase briefs, validation notes, and final bundles should state:

- proof class;
- product-facing progress type;
- actual consumer seam;
- actual user-facing app delta;
- user-facing/reviewable output delta;
- non-product exception leash, when applicable;
- mandatory next product-path checkpoint, when applicable;
- existing machinery reused;
- new machinery introduced;
- why the work is not reinventing an existing surface;
- old path treatment;
- explicit non-proofs;
- whether output is human-reviewable product output or structural proof only;
- whether live validation was run;
- whether live validation was prohibited, not licensed, or separately licensed.

For this quarantine sequence, the mandatory next product-path checkpoint is
`AG-FIXTURE-DOGFOOD-INTEGRATION-01`.
