Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG79A_PASSIVE_TO_ACTIVE_CONTROLLER_AUTHORITY_AUDIT).

# AG-79A — Passive-to-Active Controller Authority Audit

Date: 2026-06-02

Mode: Architecture Groove / Prove Mode. Scope: docs/static audit only. No live ScryRaven/proplex/scryraven product-path commands, provider calls, model calls, search calls, prompt changes, runtime code changes, citation changes, Author changes, Scrutineer changes, Economist changes, DB/session/RunOutcome changes, cache changes, or `core/pipeline_orchestrator.py` edits were licensed or performed.

## 1. Executive verdict

Controller-visible is not the same as Controller-governing. The repo now has substantial Controller-owned representation, trace visibility, and AnswerContract-visible posture across the AG-76D, AG-77, and AG-78 campaigns, but authority is uneven:

- **Runtime-governing today:** retrieval stop/continue terminal posture, targeted/source-class/weak-corpus/conflict-retrieval admission decisions, and some final handoff executors that return legacy-compatible Author/citation values from Controller-owned state.
- **Final-answer-governing today:** the strongest proof is narrow and handoff-local: Analyst/Author handoff packaging, citation/source-list handoff execution, weak/failure-card gate output, and AG-78E inferred-vs-direct presentation labels. AG-77D and AG-78D activate AnswerContract posture metadata but explicitly do not change final prose, prompts, citation behavior, or Author behavior by themselves.
- **Passive or trace-only today:** many contracts record already-computed local facts, protected-surface no-change flags, or AnswerContract trace fragments without controlling provider/search/depth/query strategy, source ranking/filtering, prompt assembly, Scrutineer/remediation, supplemental search, or broad orchestrator branching.
- **Highest remaining hidden-authority cluster:** provider/search/depth/query strategy and final evidence/citation/Author assembly still contain old orchestrator/provider/local helper authority. Scrutineer/remediation remains real hidden authority, but it is parked/rare and not the highest-risk repair blocker for the next non-live phase.

**Selected next phase:** AG-79B targeted authority repair. The first target should be provider/search/depth/query selection plus final assembly handoff boundaries, because this is the largest active path where Controller posture can still be bypassed by local/orchestrator/downstream logic.

**AG-78G decision:** AG-78G remains live-gated. This audit found useful non-live repair targets and no live dogfood license was granted.

**AG-76D-AD decision:** AG-76D-AD adapter cleanup should not preempt targeted repair. Adapter/trace debt is visible, but it did not block this authority review and does not block a narrow repair phase.

## 2. Surface matrix

| Surface | Module(s) | Claimed owner | Represented? | Trace-visible? | AnswerContract-visible? | Downstream-consumed? | Runtime-governing? | Final-answer-governing? | Known tests | Protected surfaces touched | Hidden-authority risk | Recommended next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. AnswerContract controller / runtime handoff | `core/answer_contract_controller.py`; `core/answer_contract_runtime_handoff.py`; `core/answer_contract_pipeline_adapter.py` | Controller / AnswerContract | yes | yes | yes | partial | partial | partial | `tests/test_answer_contract_controller.py`; `tests/test_answer_contract_runtime_handoff.py`; `tests/test_answer_contract_pipeline_adapter.py`; calibration/runtime tests | no runtime change in AG-79A | Medium: runtime handoff can expose posture while final prompt/source assembly still uses local facts | AG-79B: prove and narrow which AnswerContract fields are consumed by final assembly |
| 2. RunController / controller state | `core/run_controller.py`; `core/controller_state_mirror.py`; controller envelope/reducer/spine modules | Controller | yes | yes | partial | partial | partial | no | `tests/test_run_controller_skeleton.py`; `tests/test_controller_state_mirror.py`; AG-25 to AG-31 controller tests | none | Medium: trace/state container is broad but many fields are observational | AG-79B should distinguish mutable runtime gates from state mirror telemetry |
| 3a. AG-76D retrieval stop / continue | `core/retrieval_stop_controller.py`; active/shadow wrappers in `core/pipeline_orchestrator.py` | Controller | yes | yes | partial | yes | yes | partial | `tests/test_retrieval_stop_controller.py`; `tests/test_ag76d_rl_controller_authority.py`; `tests/test_ag76d_rl_controller_owned_retrieval_loop_contract.py` | none | Medium: active wrapper can fall back and ordinary loops still carry local stop assumptions | Add fixture proof for every orchestrator stop/continue branch in AG-79B |
| 3b. AG-76D router / query preparation | `core/router_query_preparation_contract.py`; orchestrator router/query block | Controller-owned contract over existing router facts | yes | yes | partial | partial | partial | no | `tests/test_ag76d_rq_router_query_preparation_contract.py` | none | High: provider override, finalized query order, depth, recency merge, and query generation can still be local/orchestrator-owned | AG-79B first repair target |
| 3c. AG-76D retrieval loop | `core/retrieval_loop_contract.py`; orchestrator retrieval loop | Controller-owned contract over already-authorized passes | yes | yes | partial | partial | partial | no | `tests/test_ag76d_rl_controller_owned_retrieval_loop_contract.py`; `tests/test_ag76d_rl_controller_authority.py` | none | High: provider/depth/ranking/filtering decisions are not fully subordinated | AG-79B should make pass authorization and provider/depth ownership explicit |
| 3d. AG-76D weak / off-topic / failure-card gate | `core/weak_failure_gate_contract.py`; `core/failure_card.py`; orchestrator weak/failure block | Controller-owned handoff | yes | yes | partial | yes | partial | yes | `tests/test_ag76d_wg_controller_owned_weak_failure_gate_contract.py` | none | Medium: old weak/off-topic transitions can still feed the contract as precomputed facts | AG-79B fixture proof for failure-card/final-answer consumption boundaries |
| 3e. AG-76D Analyst / Author handoff | `core/analyst_author_handoff_contract.py`; orchestrator Author context assembly | Controller-owned handoff | yes | yes | yes | yes | partial | yes | `tests/test_ag76d_aa_controller_owned_analyst_author_handoff_contract.py` | none | High: final prompt/context assembly still combines many local inputs before/around the handoff | AG-79B should target final assembly subordination |
| 3f. AG-76D citation / source-list handoff | `core/citation_source_handoff_contract.py`; final source telemetry; evidence bundle modules | Controller-owned handoff | yes | yes | yes | yes | partial | yes | `tests/test_ag76d_cit_controller_owned_citation_source_handoff_contract.py`; `tests/test_ag76c_final_evidence_bundle_builder.py` | none | High: source/citation eligibility, ordering, and evidence bundle assembly have local inputs | AG-79B should prove citation/source-list handoff is authoritative after final evidence selection |
| 3g. AG-76D Economist handoff | `core/economist_handoff_contract.py`; orchestrator Economist path | Controller-owned handoff | yes | yes | yes | partial | partial | partial | `tests/test_ag76d_eco_controller_owned_economist_handoff_contract.py` | none | Medium: Economist preflight/skip/output-use facts are represented, but old quantitative branches can feed them | Leave closed unless AG-79B evidence shows final assembly bypass |
| 3h. AG-76D follow-up initial state | `core/followup_initial_state_contract.py`; follow-up trace/context state | Controller-owned initial state | yes | yes | partial | partial | no | no | `tests/test_ag76d_fu_followup_controller_initial_state.py` | none | Low/Medium: state is initialization/trace-heavy, not an active current-run governor | Add missing fixture only if follow-up repair becomes target |
| 4a. AG-77 source-conflict representation | `core/source_conflict_model.py` | Controller-owned representation | yes | yes | no | yes by AG-77B/C | no | no | `tests/test_ag77a_source_conflict_representation_model.py` | none | Low: representation is intentionally inert | No repair except fixture coverage if downstream branch consumes raw conflicts |
| 4b. AG-77 source-conflict arbitration | `core/source_conflict_arbitration.py` | Controller | yes | yes | partial | yes by runtime handoff/activation | partial | partial | `tests/test_ag77b_source_conflict_arbitration.py` | none | Medium: arbitration posture can be represented without governing source ranking or final prose | AG-79B should verify final assembly respects activated conflict posture where licensed |
| 4c. AG-77 conflict runtime handoff | `core/source_conflict_arbitration_runtime_handoff.py`; runtime trace | Controller / AnswerContract visibility | yes | yes | yes | yes by AG-77D | no | no | `tests/test_ag77c_conflict_arbitration_runtime_handoff.py` | none | Medium: handoff is visible but not a behavior gate | Keep as visibility; do not claim active authority without fixture proof |
| 4d. AG-77 conflict answer-posture activation | `core/source_conflict_answer_posture_activation.py` | Controller / AnswerContract posture | yes | yes | yes | partial | partial | partial | `tests/test_ag77d_conflict_arbitration_answer_posture_activation.py` | none | Medium: activation records posture but docs say no final prose/prompt/citation change | AG-79B should add static proof around final-answer consumption if this posture is selected |
| 5a. AG-78 indirect inference contract | `core/indirect_inference_contract.py` | Controller-owned contract | yes | yes | no | yes by AG-78C/D/E | no | no | `tests/test_ag78b_indirect_inference_contract.py` | none | Low: intentionally inert representation | No repair unless inference detection is later licensed |
| 5b. AG-78 indirect inference runtime handoff | `core/indirect_inference_runtime_handoff.py` | Controller / AnswerContract visibility | yes | yes | yes | yes by AG-78D/E | no | no | `tests/test_ag78c_indirect_inference_runtime_handoff.py` | none | Medium: runtime-visible is not final-governing | Keep closed; require fixture proof before broader consumption claims |
| 5c. AG-78 indirect inference answer-posture activation | `core/indirect_inference_answer_posture_activation.py` | Controller / AnswerContract posture | yes | yes | yes | yes by AG-78E | partial | partial | `tests/test_ag78d_indirect_inference_answer_posture_activation.py` | none | Medium: posture metadata explicitly avoids final prose/prompt/citation changes | AG-79B final assembly proof if indirect posture should govern |
| 5d. AG-78 indirect inference Author / presentation handoff | `core/indirect_inference_author_presentation_handoff.py` | Controller-owned presentation handoff | yes | yes | partial | yes | partial | yes, for labeling | `tests/test_ag78e_indirect_inference_author_presentation.py` | none | Low/Medium: labels govern presentation metadata, not inference detection or citation selection | Keep live-gated; do not run AG-78G |
| 6a. Source-class recovery | `core/source_class_recovery*.py`; official/canonical recovery modules; orchestrator lifecycle | Controller / specialized recovery lane | yes | yes | partial | yes | yes | partial | source-class recovery tests including AG-68C/E/G; answer-contract source-class tests | none | Medium: active recovery admission exists, but candidate acquisition/ranking and dispatch details still have local/provider authority | AG-79B can include provider/depth/query ownership proof; otherwise leave closed |
| 6b. Weak-corpus recovery | `core/weak_corpus_controller.py`; weak-corpus recovery modules/tests | Controller | yes | yes | partial | yes | yes | partial | `tests/test_weak_corpus_controller.py`; `tests/test_weak_corpus_recovery.py`; evidence weak-corpus tests | none | Medium: recovery gate is active, but search/query/provider behavior remains separate | AG-79B provider/search/depth/query target |
| 6c. Conflict-resolution retrieval | `core/conflict_resolution_controller.py`; `core/conflict_resolution_executor.py`; orchestrator lifecycle | Controller / executor | yes | yes | partial | yes | yes | partial | `tests/test_conflict_resolution_controller.py`; `tests/test_conflict_resolution_executor.py`; conflict integration tests | none | Medium: conflict lane dispatch is guarded, but ordinary retrieval can still proceed without becoming conflict-resolving | Keep lane separation tests; add final-consumption proof only if selected |
| 6d. Authoritative-source action adapters | `core/authoritative_source_action*.py`; official/canonical recovery adapter modules | Adapter over Controller/source-class recovery state | yes | yes | partial | partial | partial | partial | authoritative-source adapter/projection/recovery tests | none | Medium: adapter debt and source action traces can obscure ownership but do not block review | Do not choose AG-76D-AD unless repair is blocked |
| 7. Scrutineer / remediation | Scrutineer/remediation inline path in `core/pipeline_orchestrator.py`; no dedicated Controller-owned handoff found | Orchestrator/local hidden controller | partial | partial | no | yes | yes on rare path | yes on rare path | indirect only; no dedicated Controller-subordination test | none | High: run gate, thresholds, category filter, remediation search, re-synthesis, and Author directives are local | Not first target unless project chooses AG-76D-SCR; AG-79B remains selected |
| 8. Synthesis-evaluator supplemental search | evaluator/supplemental blocks in `core/pipeline_orchestrator.py` | Orchestrator/local evaluator path | partial | partial | no | yes | yes | partial | indirect continuation/spine tests; no dedicated Controller-owned supplemental handoff found | none | High: completeness checks, triggers, Author notes, and re-analysis/re-synthesis can bypass Controller posture | Include in AG-79B if provider/search/depth/query repair reaches evaluator supplemental lane |
| 9. Provider/search/depth/query selection | `core/search_providers.py`; `core/routing.py`; `core/controller_provider_search_allocation.py`; `core/targeted_retrieval_controller.py`; orchestrator provider/depth/query code | Mixed: Controller allocation exists; legacy provider/orchestrator still active | partial | yes | partial | yes | yes | indirect | `tests/test_ag75a_controller_provider_search_allocation_gate.py`; `tests/test_targeted_retrieval_controller.py`; provider diagnostics tests | none | Very high: provider selection, depth, query strategy, ranking/filtering, candidate fit, and accepted-readable authority can override Controller posture | AG-79B first targeted repair |
| 10. Final evidence bundle / citation / Author output assembly | `core/final_evidence_bundle_builder.py`; `core/citation_source_handoff_contract.py`; `core/analyst_author_handoff_contract.py`; final assembly in `core/pipeline_orchestrator.py` | Mixed: handoffs are Controller-owned, assembly remains orchestrator-heavy | yes | yes | yes | yes | partial | yes/partial | AG-76C final evidence tests; AG-76D AA/CIT tests; AG-78E presentation tests | none | Very high: final evidence selection, Author notes, prompt context, and citation assembly may ignore passive posture | AG-79B final assembly proof/repair alongside provider/query target |
| 11. `pipeline_orchestrator.py` branches that may still make domain decisions | `core/pipeline_orchestrator.py` | Orchestrator/local unless delegated | partial | partial | partial | yes | yes | yes | many static/fixture tests, no single authority matrix test | not edited | Very high: branch density remains the main bypass risk | AG-79B targeted static fixtures; do not broad-rewrite |

## 3. Hidden-authority map

### 3.1 Scrutineer / remediation

| Hidden authority point | Current classification | Bypass risk | Recommended AG-79B/next handling |
| --- | --- | --- | --- |
| Run gate | Orchestrator/local | Can decide whether post-synthesis review runs without a Controller-owned Scrutineer state | Keep closed in AG-79B unless selected subtarget; AG-76D-SCR only if elevated |
| Flag threshold | Orchestrator/local | Hard-coded severity threshold can trigger remediation independently of AnswerContract posture | Document and add missing fixture if Scrutineer becomes repair target |
| Searchable category filter | Orchestrator/local | Only selected categories are remediation-searchable | Same as above |
| Remediation query generation | Researcher/Scrutineer path, not Controller-owned | Can create new retrieval intent after main Controller retrieval | Same as above |
| Novelty filter | Orchestrator/local | Can block/allow remediation queries outside Controller state | Same as above |
| Remediation provider/depth selection | Provider/orchestrator | Can dispatch search with local depth/provider policy | Covered by AG-79B provider/search/depth/query repair if included |
| Re-synthesis trigger | Orchestrator/local | Can rerun Analyst synthesis based on local remediation outcome | Missing Controller-owned test/contract |
| Author directive insertion | Orchestrator/local | Can hedge/omit/caveat final Author context independently | Missing Controller-owned final assembly proof |

Verdict: real hidden authority, but not the selected first repair because it appears rare/parked and the broader provider/search/depth/query plus final assembly path is more central and active.

### 3.2 Synthesis-evaluator supplemental search

| Hidden authority point | Current classification | Bypass risk | Recommended AG-79B/next handling |
| --- | --- | --- | --- |
| Completeness checks | Evaluator/orchestrator | Can decide insufficiency/completeness separately from Controller posture | Add static fixtures to prove handoff or subordinate trigger |
| Supplemental search triggers | Orchestrator/local | Can launch search outside explicit Controller-owned provider/depth/query state | Include in AG-79B provider/search/depth/query repair |
| Author notes | Orchestrator/local | Can affect final presentation context | Include in final assembly proof |
| Re-analysis or re-synthesis triggers | Orchestrator/local | Can alter downstream analysis after Controller stop/continue | Add missing fixture proof |

### 3.3 Orchestrator-local helper decisions

| Hidden authority point | Current classification | Bypass risk | Recommended AG-79B/next handling |
| --- | --- | --- | --- |
| Retrieval stop wrappers | Partial active Controller, wrapper-local fallback | Active decision can become shadow/fallback on exceptions or unexpected decision | Add fixture/static proof for fallback boundaries |
| Weak/failure gate transitions | Controller-owned handoff over local facts | Local weak/off-topic facts still feed the gate | Add fixture proof for every final branch |
| Final prompt or Author context assembly | Mixed | Author prompt/context can combine local notes, Scrutineer directives, evidence snapshots, and handoff state | AG-79B final assembly target |
| Source/citation assembly | Mixed | Local final evidence and telemetry can govern source/citation lists before handoff execution | AG-79B final assembly target |
| Domain branches not clearly delegated | Orchestrator/local | Any branch can override Controller posture if not trace-bound to a Controller state | AG-79B static authority matrix test |

### 3.4 Provider/search legacy decisions

| Hidden authority point | Current classification | Bypass risk | Recommended AG-79B/next handling |
| --- | --- | --- | --- |
| Provider selection | Mixed legacy/provider routing plus Controller allocation traces | Can choose providers independently of Controller authority | AG-79B first repair target |
| Search depth | Mixed | Can escalate/de-escalate search without Controller-owned state | AG-79B first repair target |
| Query strategy | Mixed router/evaluator/recovery/local helpers | Can generate or reorder queries outside Controller state | AG-79B first repair target |
| Retrieval ranking/filtering | Local/provider/orchestrator | Can decide accepted evidence independently of Controller posture | AG-79B should at least classify and fixture-prove boundaries |
| Candidate fit / accepted-readable authority | Specialized lanes and local filters | Can admit/reject source candidates after Controller visibility only | AG-79B should target candidate admission proof where provider/depth repair touches it |

## 4. Passive-only / trace-only state list

These states are represented and/or trace-visible but do not currently prove runtime-governing or final-answer-governing authority by themselves:

- AG-77A source-conflict representation.
- AG-77C conflict runtime handoff, except as input to AG-77D posture activation.
- AG-78B indirect inference contract.
- AG-78C indirect inference runtime handoff, except as input to AG-78D/AG-78E.
- Most RunController trace fields and state mirror snapshots.
- Router/query preparation fields that record already-computed provider override, finalized query order, search depth, recency query merge, and runtime posture facts.
- Retrieval loop descriptors where pass/provider/depth values are already computed elsewhere.
- Follow-up initial state metadata.
- Provider diagnostics payloads and trace fragments.
- Authoritative-source action trace fragments where adapters mirror or package existing recovery/action facts.
- Scrutineer/remediation trace flags such as ran/count, because no Controller-owned Scrutineer handoff exists.
- Supplemental search trace flags such as ran/count, because no Controller-owned supplemental-search handoff exists.

## 5. Runtime-governing state list

These states have current static/test evidence of controlling at least a runtime gate or handoff result:

- Retrieval stop controller decisions used by active retrieval-stop telemetry and terminal stop posture.
- Targeted retrieval controller decisions gating specialized retrieval candidates.
- Source-class recovery controller/lifecycle decisions gating missing source-class recovery.
- Weak-corpus recovery controller decisions gating weak-corpus recovery posture.
- Conflict-resolution controller/executor decisions gating conflict-resolution retrieval lane behavior.
- Weak/failure gate handoff execution for failure-card/final posture output.
- Citation/source-list handoff execution for ordered source/citation telemetry after final evidence input is selected.
- Analyst/Author handoff execution for legacy-compatible handoff values and Author evidence/context packaging.
- AG-78E Author presentation handoff for inferred/direct/speculative/conflict-blocked/range-bound labeling metadata.

## 6. Final-answer-governing state list

These are final-answer-governing only within narrow, proven boundaries:

- Analyst/Author handoff state governs packaged Author handoff fields after its inputs are assembled.
- Citation/source-list handoff state governs ordered sources/unique URLs/final-answer source telemetry after final evidence is selected.
- Weak/failure gate state governs failure-card/final-posture handoff output.
- AG-78E indirect inference Author presentation handoff governs inferred-vs-direct presentation labeling metadata.
- AG-77D and AG-78D are AnswerContract/final-posture metadata activations, but they are **not** proven to govern final prose, prompt text, citation selection, provider/search behavior, or Author behavior without the downstream handoffs above consuming them.

## 7. Tests that already prove consumption

Existing tests provide useful consumption proof, but mostly at module/fixture boundaries rather than through full orchestrator branches:

- `tests/test_answer_contract_controller.py`
- `tests/test_answer_contract_runtime_handoff.py`
- `tests/test_answer_contract_pipeline_adapter.py`
- `tests/test_run_controller_skeleton.py`
- `tests/test_controller_state_mirror.py`
- `tests/test_retrieval_stop_controller.py`
- `tests/test_ag76d_rl_controller_authority.py`
- `tests/test_ag76d_rq_router_query_preparation_contract.py`
- `tests/test_ag76d_rl_controller_owned_retrieval_loop_contract.py`
- `tests/test_ag76d_wg_controller_owned_weak_failure_gate_contract.py`
- `tests/test_ag76d_aa_controller_owned_analyst_author_handoff_contract.py`
- `tests/test_ag76d_cit_controller_owned_citation_source_handoff_contract.py`
- `tests/test_ag76d_eco_controller_owned_economist_handoff_contract.py`
- `tests/test_ag76d_fu_followup_controller_initial_state.py`
- `tests/test_ag77a_source_conflict_representation_model.py`
- `tests/test_ag77b_source_conflict_arbitration.py`
- `tests/test_ag77c_conflict_arbitration_runtime_handoff.py`
- `tests/test_ag77d_conflict_arbitration_answer_posture_activation.py`
- `tests/test_ag78b_indirect_inference_contract.py`
- `tests/test_ag78c_indirect_inference_runtime_handoff.py`
- `tests/test_ag78d_indirect_inference_answer_posture_activation.py`
- `tests/test_ag78e_indirect_inference_author_presentation.py`
- `tests/test_source_class_recovery_controller.py`
- `tests/test_source_class_recovery_dispatch_execution_ag68c.py`
- `tests/test_weak_corpus_controller.py`
- `tests/test_conflict_resolution_controller.py`
- `tests/test_conflict_resolution_executor.py`
- `tests/test_targeted_retrieval_controller.py`
- `tests/test_ag75a_controller_provider_search_allocation_gate.py`
- `tests/test_ag76c_final_evidence_bundle_builder.py`
- authoritative-source action/projection/recovery tests.

## 8. Missing fixture/static tests

The following missing tests prevent stronger claims that Controller-visible posture is Controller-governing:

1. A static AG-79B authority fixture mapping every `pipeline_orchestrator.py` domain branch to either a Controller-owned state, an explicitly local closed surface, or an accepted temporary hidden-authority exception.
2. Provider/search/depth/query fixture tests proving provider lists, search depth, query order, recency query merge, supplemental queries, and recovery queries cannot bypass Controller-owned posture.
3. Retrieval stop branch fixtures for active decision, fallback, unexpected decision, and terminal no-query/budget-exhausted paths.
4. Weak/failure-card fixtures proving local weak/off-topic facts do not override Controller handoff outputs after the handoff executes.
5. Final evidence/citation/Author assembly fixtures proving final prompt context, Author notes, citation/source ordering, and evidence bundle selection consume Controller-owned handoff state rather than parallel local facts.
6. AG-77D final-consumption fixtures proving unresolved official/current conflict posture reaches final answer posture where behavior is licensed.
7. AG-78D/AG-78E final-consumption fixtures proving inferred-vs-direct labels are preserved into final Author/presentation surfaces without citation laundering.
8. Scrutineer/remediation static fixtures proving run gate, threshold, category filter, remediation query generation, novelty filtering, remediation dispatch, re-synthesis, and Author directive insertion are either Controller-owned or explicitly hidden.
9. Synthesis-evaluator supplemental-search fixtures proving completeness checks, supplemental triggers, Author notes, and re-analysis/re-synthesis triggers are Controller-subordinate.
10. Authoritative-source adapter fixtures proving adapter trace debt does not obscure active authority in source-class recovery and official/canonical recovery paths.

## 9. First recommended targeted repair phase

Select exactly one next phase: **AG-79B targeted authority repair**.

Recommended AG-79B target:

- Provider/search/depth/query selection authority, including router/query-preparation, retrieval-loop pass authorization, supplemental search, recovery-query dispatch boundaries, and targeted retrieval provider/depth blockers.
- Final evidence/citation/Author assembly proof where those provider/query decisions feed final evidence and presentation.

Why not AG-76D-SCR first: Scrutineer/remediation is real hidden authority, but it is parked/rare and does not outrank the central provider/search/depth/query plus final assembly path.

Why not AG-76D-AD first: adapter debt exists, but it did not block this audit and does not block targeted repair.

Why not AG-78G first: live dogfood is not licensed and useful non-live repair targets exist.

## 10. AG-78G live-gate decision

AG-78G remains live-gated. AG-79A found non-live authority repair targets and did not receive explicit live dogfood authorization. No live validation, provider/model calls, or search calls were used.

## 11. AG-76D-AD preemption decision

AG-76D-AD should not preempt repair. Adapter/trace debt is a maintainability issue and may be a later cleanup phase, but AG-79A did not find that it blocks authority review or safe targeted repair.

## 12. Closed surfaces and no-live statement

Closed in AG-79A:

- Runtime behavior.
- Prompt behavior.
- Provider/search/retrieval behavior.
- Citation behavior.
- Author behavior.
- Scrutineer/remediation behavior.
- Economist behavior.
- DB/session/RunOutcome shape.
- Cache implementation.
- Live validation.
- Broad `core/pipeline_orchestrator.py` rewrite.

No live ScryRaven/proplex/scryraven product-path command was run. No provider, model, or search call was run.
