# AG-95A Authority Surface Inventory And Demolition Plan

Status: architecture inventory and demolition plan.

Validation boundary: repo-visible code, repo-tracked docs, and static inspection
only. No live ScryRaven/proplex provider, model, search, retrieval, secret,
`.env`, DB row, raw provider payload, raw prompt, private log, cache, full raw
trace, local output packet, or private artifact access was used.

## 1. Executive verdict

Yes, the authority system is too sprawled.

The dangerous concentration is not the canonical RunAuthority spine itself. The
sprawl is concentrated in the recovery and final-custody compatibility belt
around it:

- source-obligation handoffs;
- official/current/legal recovery admission;
- weak-corpus arbitration;
- source-class lifecycle and dispatch;
- candidate/passport/custody projections;
- final evidence and citation-survival projections;
- post-final visibility/export/report hydration.

The system is locally repairable because the intended owner chain is visible and
mostly consumed at runtime. The repair path is not a giant rewrite. It is a
series of small deletions and demotions where compatibility surfaces stop
re-deciding, stop hydrating control-looking projections, or become adapters that
only translate canonical state.

The blunt problem: AG-94H-F and AG-94H-G fixed real bugs, but they also left
more named surfaces that sound authoritative. Future phases must delete or
demote an old authority surface whenever they add or strengthen a new one.

## 2. Intended authority spine

Target owner chain:

```text
RunAuthorityContract
-> EvidenceLedger
-> SearchJudgment
-> SufficiencyJudgment
-> FinalAnswerPacket
-> AuthorExecutor
-> Author-facing evidence/citation custody
```

Current compatibility reality:

```text
RunAuthorityContract
-> EvidenceLedger
-> SearchJudgment
-> source-class / official-canonical compatibility belt
-> ControllerEvidenceLedger compatibility custody
-> ControllerRecoveryDecision / ControllerLoopSpine compatibility dispatch
-> SourceClassRecoveryRunner / Executor
-> FinalEvidenceBundle
-> FinalAnswerPacket
-> final authority citation survival guard
-> Author-facing evidence/citation custody
```

`ControllerEvidenceLedger` is not the desired long-term owner. It is a
subordinate compatibility custody ledger retained because older recovery and
final-citation surfaces still consume its event vocabulary and legacy-gap
diagnostics. `authority_custody_satisfaction.py` is useful short-term shared
predicate glue from AG-94H-F, but the durable owner should be EvidenceLedger /
FinalAnswerPacket custody, not another standalone truth object.

## 3. Authority surface inventory table

| Surface / file / function | Current role | Category | Decides anything? | Should decide anything? | Duplicate or overlaps with | Current consumers | Deletion or demotion blocker | Recommended AG-95 action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `core/run_kernel.py::RunKernel` | Canonical action authorization and RunState reduction spine. | OWNER | yes | yes | controller loop spine, retrieval stop checkpoint wrappers | `pipeline_orchestrator.py`, bounded runtimes, reducers | none for owner; only old consumers still bypass pieces | Keep; no new parallel RunKernel helper. |
| `core/run_authority_contract.py::RunAuthorityContract` | Canonical source requirement / obligation contract. | OWNER | yes | yes | AnswerContract compatibility, source-class gap triggers | EvidenceLedger, QueryPlan hints, final packet adapters, search judgment inputs | old AnswerContract fields still feed compatibility paths | Keep; future phases should delete AnswerContract obligation fallbacks once consumers read contract/ledger directly. |
| `core/evidence_ledger.py::EvidenceLedger` | Canonical candidate custody, requirements, links, official/current custody projection, custody gaps. | OWNER | yes | yes | ControllerEvidenceLedger, authority candidate passport, official-current custody projections | RunKernel reducers, SearchJudgment, sufficiency, final packet adapter | legacy recovery decisions still consume ControllerEvidenceLedger and trace fields | Keep; make more consumers read this before deleting compatibility ledgers. |
| `core/controller_evidence_ledger.py::build_controller_evidence_ledger` | Legacy event ledger for represented candidates, selected evidence, final citations, legacy gaps. | COMPATIBILITY_SHIM | yes | no, except compatibility custody while old consumers remain | EvidenceLedger, FinalAnswerPacket, final evidence citation custody projection | ControllerRecoveryDecision, visibility export, tests, post-final diagnostics | ControllerRecoveryDecision and visibility export still consume its legacy gap vocabulary | Protect short term; schedule demotion after recovery decision reads EvidenceLedger/FinalAnswerPacket custody directly. |
| `core/run_authority_search_judgment.py::RunSearchJudgment` | Canonical search/recovery recommendation and iterative source-gap posture. | OWNER | yes | yes | source-class recommendation flags, controller loop spine gates | search judgment runtime, consumer adapter, authoritative source action | source-class recovery still translates judgment into legacy recommendation fields | Keep; delete duplicate recommendation flags after source-class dispatch consumes judgment/canonical recovery permission. |
| `core/run_authority_search_judgment_consumers.py::apply_search_judgment_to_source_class_recovery_recommendation` | Translates canonical SearchJudgment into old source-class recommendation fields. | ADAPTER | yes, narrowly as translation | no policy beyond canonical projection | source-class recommendation, authoritative source action | `authoritative_source_action.py`, tests | source-class lifecycle expects recommendation-shaped packet | Keep as adapter; demote with explicit "translation-only" comments in later phase if touched. |
| `core/run_authority_sufficiency.py::RunSufficiencyJudgment` | Canonical final answer sufficiency / answer posture. | OWNER | yes | yes | useful-content gate, weak/failure gate, final packet readiness | FinalAnswerPacket runtime adapter, orchestrator final answer path | post-Author outcome guard can still downgrade readiness | Keep; post-Author guards must feed back as packet observations or remain explicit compatibility exceptions. |
| `core/final_answer_packet.py::FinalAnswerPacket` | Canonical final evidence, citation eligibility, source obligations, caveats, Author input refs, readiness. | OWNER | yes | yes | final evidence bundle, final citation survival, citation source handoff contract | final answer runtime, Author execution runtime, post-author projection | final evidence selection still built outside packet; citation survival guard is post-packet | Keep; future phases should move final citation-survival readiness into packet observation/reduction. |
| `core/final_evidence_bundle_builder.py::build_final_evidence_bundle` | Builds final source ids, ordered sources, Author evidence slice, final evidence block. | ADAPTER | yes, final evidence identity selection shape | yes until packet consumes canonical final-evidence selection | FinalAnswerPacket evidence records, final citation survival visibility repair | pipeline final evidence path, final answer assembly | final evidence selection/prompt parity is safety-sensitive | Protect for now; no deletion until packet owns final-evidence selection identity directly. |
| `core/final_answer_runtime_adapter.py::build_final_answer_packet` | Converts ledger, sufficiency, AnswerContract, and legacy fields into FinalAnswerPacket. | COMPATIBILITY_SHIM | yes | no, except packet assembly translation | RunAuthorityContract, EvidenceLedger, SufficiencyJudgment, AnswerContract | pipeline final answer packet runtime | legacy fallbacks still required for old tests and traces | Demote when packet inputs are all canonical; delete AnswerContract fallback branches after coverage proves unused. |
| `core/final_answer_runtime_assembly.py` | Assembles Author and citation runtime payloads from packet plus legacy scope. | COMPATIBILITY_SHIM | partially | no, should assemble only | FinalAnswerPacket, final evidence bundle, citation source handoff | pipeline final answer path | Author prompt/payload parity sensitive | Keep; later make it packet-only. |
| `core/final_authority_citation_survival.py::build_final_authority_citation_survival_projection` | Checks selected authority evidence identity survives as final citation. | PROTECTED_FOR_NOW | yes | yes, short term guard; long term packet-owned | FinalAnswerPacket citation eligibility, ControllerEvidenceLedger final citation custody, official source survival projections | pipeline post-Author outcome guard, AG-94H-G tests | final citation survival was just repaired; packet does not yet own this observation | Keep in AG-95B; schedule fold into FinalAnswerPacket/readiness after packet consumes post-Author citation observation. |
| `core/final_authority_citation_survival.py::ensure_selected_authority_evidence_visible_to_author` | Appends missing selected authority evidence into Author evidence payload. | PROTECTED_FOR_NOW | yes | yes, until final bundle/packet owns it | final evidence bundle, Author evidence slice | pipeline Author evidence path | Author evidence parity and citation survival regression risk | Keep; future demotion target after final evidence bundle always includes selected authority evidence. |
| `core/authority_custody_satisfaction.py::authority_custody_satisfaction_for_source_class` | Shared custody-backed satisfaction predicate; demotes aggregate/status observability. | PROTECTED_FOR_NOW | yes | yes, short term; long term owner should be ledger/packet | EvidenceLedger, ControllerEvidenceLedger, official-current custody, candidate passport, final packet | authoritative source action, query acquisition, execution admission, tests | AG-94H-F bug fix depends on this shared predicate | Keep short term; AG-95B should not delete. Future fold into EvidenceLedger/FinalAnswerPacket satisfaction projection. |
| `core/authoritative_source_action.py::build_authoritative_source_obligation_state_and_action` | Composes bridge, query acquisition, execution admission, authority lifecycle arbitration, and lifecycle trace. | COMPATIBILITY_SHIM | yes | no, should translate SearchJudgment/EvidenceLedger recovery permission | bridge, query acquisition, admission, source-class lifecycle, authority lifecycle | orchestrator adapter, pipeline source-class recovery path | too many downstream fields consume its trace; behavior-sensitive | Demote gradually; mark as compatibility action handoff, not owner. |
| `core/authoritative_source_action.py::_authority_runtime_arbitration` | Computes recovery-needed/allowed, weak-corpus ownership, execution state. | PROTECTED_FOR_NOW | yes | no long term | SearchJudgment, source-class lifecycle, execution admission, ControllerLoopSpine | authoritative source action, spine, visibility export | recovery dispatch still reads `authority_lifecycle_required_recovery_allowed` | Keep until canonical recovery permission replaces it. Then delete/demote. |
| `core/authority_lifecycle_runtime_arbitration.py::build_authority_runtime_arbitration` | Pure arbitration helper for required recovery and blockers. | COMPATIBILITY_SHIM | yes | no long term | authoritative source action, source-class controller | authoritative source action, admission/acquisition blockers | spine and ControllerRecoveryDecision still consume its fields | Protected until a canonical recovery permission object exists. |
| `core/authority_lifecycle_contract.py::AuthorityLifecycle` | Lifecycle model for requirement, action, execution, candidate fit, final posture. | COMPATIBILITY_SHIM | yes | no long term as a separate owner | EvidenceLedger, FinalAnswerPacket, source-class lifecycle, ControllerEvidenceLedger | projections, action trace, tests | many fields are the shared vocabulary for current compatibility belt | Keep for now; eventually split into packet/ledger-owned projections. |
| `core/official_source_obligation_bridge.py::apply_official_source_obligation_bridge` | Bridges official/current obligation facts into source-class recommendation and custody-aware missing classes. | ADAPTER | yes, mutates recommendation | no, should be one-way bridge from ledger/contract | source-class recommendation, authority custody satisfaction | `authoritative_source_action.py`, pipeline post-final bridge, tests | source-class recommendation still lacks native canonical obligation input | Demote once lifecycle consumes RunAuthorityContract/EvidenceLedger directly. |
| `core/official_canonical_recovery_query_acquisition.py::apply_official_canonical_recovery_query_acquisition` | Can promote/add recovery queries and acquisition plan for official/canonical obligations. | PROTECTED_FOR_NOW | yes | yes until QueryPlan owns recovery queries | QueryPlan, source-class recovery query generation, authoritative source action | authoritative source action, tests | query identity and provider/search behavior sensitive | Do not touch in AG-95B unless docs-only. Future QueryPlan migration required. |
| `core/official_canonical_recovery_execution_admission.py::build_official_canonical_recovery_execution_admission` | Admits one official/canonical recovery execution slot. | COMPATIBILITY_SHIM | yes | no long term; should consume canonical recovery permission | authority lifecycle arbitration, source-class controller, weak-corpus controller | authoritative source action, source-class lifecycle, tests | source-class lifecycle and spine still use admission flags | Protect until canonical recovery permission replaces admission flag. |
| `core/official_canonical_recovery_candidate_acquisition.py::build_official_canonical_recovery_candidate_acquisition_trace` | Post-dispatch candidate acquisition visibility and next-failure diagnostics. | DIAGNOSTIC | no runtime dispatch | no | authority candidate passport, visibility export | visibility export, tests | useful diagnostics; not a runtime owner | Keep diagnostic; avoid feeding it back into control. |
| `core/official_canonical_recovery_visibility_export.py::build_official_canonical_recovery_visibility_export` | Report/export projection with status, next-failure, candidate, custody, and hydrated decision fields. | DIAGNOSTIC | yes, in projection hydration | no | ControllerRecoveryDecision, ControllerEvidenceLedger, candidate/passport, survival projections | reports, output-quality packets, tests | current helper can hydrate control-looking `controller_recovery_decision` when runtime field absent | AG-95B top target: stop building/hydrating recovery decisions in export; only display existing runtime decision or diagnostic absence. |
| `core/source_class_recovery.py::build_source_class_recovery_recommendation` | Detects source-class obligations and builds recovery query candidates/recommendation. | PROTECTED_FOR_NOW | yes | yes until QueryPlan/SearchJudgment fully owns recovery query intent | RunAuthorityContract, SearchJudgment, official query acquisition | pipeline retrieval and source-class recovery path | query generation/source classification closed for AG-95B | Do not delete; future QueryPlan/source-obligation migration. |
| `core/source_class_authority_status_normalization.py` | Normalizes status-only supported authority classes into missing classes when queries exist. | COMPATIBILITY_SHIM | yes | no long term | source-class recommendation, authoritative source action | source-class controller, authoritative source action | AG-94H-B repair; still needed by source-class lifecycle | Keep until missing classes come from canonical contract/ledger inputs. |
| `core/source_class_recovery_controller.py::decide_source_class_recovery` | Legacy active controller deciding source-class recovery eligibility and blockers. | PROTECTED_FOR_NOW | yes | no long term | SearchJudgment recovery permission, official admission, weak-corpus controller | source-class lifecycle, tests | runner/spine still consume lifecycle fields | Demote after canonical recovery permission exists and runner consumes it. |
| `core/source_class_recovery_lifecycle.py::record_source_class_recovery_lifecycle` | Records active source-class lifecycle and calls controller decision. | COMPATIBILITY_SHIM | yes | no long term | source-class controller, authority lifecycle arbitration | authoritative source action, pipeline pregates, tests | broad trace consumers expect lifecycle shape | Keep as adapter; later make trace-only after dispatch reads canonical permission. |
| `core/controller_loop_spine.py::build_controller_loop_spine_result` | Arbitrates at most one dispatch among source-class, weak-corpus, conflict, targeted, terminal gates. | PROTECTED_FOR_NOW | yes | no long term | RunKernel action authorization, SearchJudgment, source-class lifecycle, weak-corpus controller | pipeline dispatch, runner, tests | runner consumes `authorized_spine_action`; many recovery paths depend on it | Not AG-95B first target; plan later demotion after diagnostics hydration is removed. |
| `core/source_class_recovery_runner.py::run_source_class_recovery_dispatch` | Mechanical dispatcher; executes source-class recovery only when spine authorizes. | ADAPTER | yes, mechanical gate | yes as bounded executor caller | ControllerLoopSpine, ControllerRecoveryDecision, source-class executor | pipeline source-class recovery block | still checks controller recovery decision and provider allocation first | Keep; ensure policy moves out, not into runner. |
| `core/source_class_recovery_executor.py::execute_source_class_recovery_action` | Bounded executor around provider/search callable with controller gate. | ADAPTER | yes, execution guard | yes for bounded execution only | runner, ControllerRecoveryDecision | source-class runner, tests | provider/search behavior sensitive | Keep; do not change in AG-95B. |
| `core/controller_recovery_decision.py::build_controller_recovery_decision` | Legacy retry/stop table using ControllerEvidenceLedger, source obligation, lifecycle, budget, candidate state. | PROTECTED_FOR_NOW | yes | no long term | EvidenceLedger, SearchJudgment, ControllerLoopSpine, final citation custody | runner, provider-search allocation, visibility export | runner/executor still consume it; visibility export also hydrates it | Runtime path protected for now; remove export hydration in AG-95B. |
| `core/weak_corpus_controller.py::decide_weak_corpus_recovery` | Decides weak-corpus recovery scheduling. | PROTECTED_FOR_NOW | yes | yes only until sufficiency/search posture owns weak recovery | SourceClass recovery, retrieval stop, controller loop spine | pipeline weak-corpus block, spine, tests | weak-corpus behavior and search scheduling sensitive | Keep; later subordinate to canonical search/sufficiency posture. |
| `core/retrieval_stop_controller.py::decide_retrieval_stop_with_kernel_action` | Legacy stop/continue decision under RunKernel checkpoint. | PROTECTED_FOR_NOW | yes | no long term | RunState/SearchJudgment stop posture, retrieval loop locals | pipeline retrieval loop, retrieval stop trace projection | high behavior sensitivity; affects search loop | Future dedicated strangler, not AG-95B. |
| `core/targeted_retrieval_controller.py` | Targeted retrieval continuation lifecycle and gating. | PROTECTED_FOR_NOW | yes | no long term | QueryPlan/SearchJudgment continuation permission, controller loop spine | pipeline pregates/spine, tests | query/continuation behavior sensitive | Keep; later canonical continuation permission. |
| `core/conflict_resolution_controller.py` | Conflict-resolution retrieval lifecycle and gate. | PROTECTED_FOR_NOW | yes | yes until conflict posture canonical owner exists | Sufficiency/SearchJudgment conflict posture, controller loop spine | pipeline/spine, tests | conflict retrieval behavior sensitive | Keep; do not mix with AG-95B. |
| `core/authority_candidate_passport.py::build_authority_candidate_passport_projection` | Candidate-level authority passport/custody projection from candidate and selected evidence facts. | DIAGNOSTIC | yes, custody projection can satisfy helper | no as standalone owner | EvidenceLedger, ControllerEvidenceLedger, final evidence citation custody | ControllerEvidenceLedger, authority custody satisfaction, visibility export, tests | `authority_custody_satisfaction` still accepts passport as proof | Keep, but mark as custody evidence projection; future fold into EvidenceLedger candidate records. |
| `core/authority_candidate_passport_validation.py` | Classifies passport export quality. | DIAGNOSTIC | no | no | authority candidate passport | tests/report diagnostics | none | Keep diagnostic-only. |
| `core/official_current_source_custody.py::OfficialCurrentSourceCustodyState` | Requirement/candidate custody projection for official/current classes. | ADAPTER | yes | yes as subordinate custody projection | EvidenceLedger, authority custody satisfaction | EvidenceLedger, bridge, tests | used by AG-94H-F satisfaction proof | Keep as subordinate projection; eventual EvidenceLedger internal detail. |
| `core/legal_current_authority_fit.py::build_legal_current_primary_authority_fit` | Legal/current fit for provided facts. | ADAPTER | yes, fit classification | yes, bounded fit only | source-class fit, official/current custody | authoritative source action | source classification semantics sensitive | Keep; do not broaden. |
| `core/final_evidence_citation_custody_projection.py::build_final_evidence_citation_custody_projection` | Projects final evidence/citation custody from packet and ledger. | DIAGNOSTIC | no runtime | no | FinalAnswerPacket, ControllerEvidenceLedger, final citation survival | tests, visibility/export | useful for audits; not runtime owner | Keep diagnostic; avoid control consumers. |
| `core/official_source_survival_projection.py::build_official_source_survival_projection_trace` | Legacy official/canonical survival counts and classification. | DIAGNOSTIC | no runtime | no | final authority citation survival, visibility export | reports/tests | counts can sound like custody but are aggregates | Demote/rename later as aggregate diagnostic; not AG-95B first. |
| `core/official_source_survival_diagnostics.py::classify_official_source_survival` | Diagnostic classification of official source survival. | DIAGNOSTIC | no | no | official source survival projection, final citation survival | tests/report diagnostics | none | Keep diagnostic-only; do not feed runtime. |
| `core/session_output_projection.py::build_execution_trace_projection` | Serializes execution trace/log entries and packet refs. | DIAGNOSTIC | no | no | runtime trace projection, final answer packet trace fragment | output packaging, tests | persistence/output shape sensitive | Keep; only projection cleanup later. |
| `core/runtime_trace_projection_assembly.py::attach_passive_runtime_projection_traces` | Attaches passive projection traces, including old ControllerEvidenceLedger visibility. | DIAGNOSTIC | no | no | ControllerEvidenceLedger, final evidence/citation refs | post-author packaging, tests | output trace shape sensitive | Keep; later ensure all attached projections are marked diagnostic/passive. |
| `core/runtime_trace_export_attachment.py::attach_runtime_trace_export_compatibility_payloads` | Adds compatibility payloads for reports/output. | DIAGNOSTIC | no | no | visibility export, source-class validation packet | output packaging | report shape sensitive | Keep; avoid new authority labels. |
| `core/post_author_output_projection.py::build_post_author_trace_packaging_from_scope` | Post-Author trace/output packaging and compatibility handoffs. | COMPATIBILITY_SHIM | partially, can assert packet divergence | no policy; yes integrity guard | FinalAnswerPacket, AnswerContract compatibility ledger, source-class recomputation | pipeline final return path | persistence/output shape and packet guard consumers | Keep; later delete AnswerContract compatibility projection branches. |
| `core/pipeline_orchestrator.py` authority/citation/recovery sections | Coordinates canonical chain and active compatibility islands. | PROTECTED_FOR_NOW | yes, through local gates and call order | no long term | almost every surface above | CLI/runtime pipeline | broad rewrite would touch provider/search/query/Author behavior | Treat as target surface but not AG-95B first. |
| `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` | Legacy Controller-handoff guidance. | STALE_SCAFFOLD | no runtime | no | current RunAuthority guide | humans/Codex guidance | already has AG-94G note; body intentionally legacy | Do not rewrite now; keep as historical/explicit legacy only. |
| `docs/product/AG81B_ANSWER_QUALITY_RUBRIC_AND_OUTPUT_CONTRACT.md` | Current-looking product doc still says Controller/AnswerContract owns posture. | STALE_SCAFFOLD | no runtime | no | RunAuthority guide, AG-94C/G | humans | product doc is useful but stale on authority routing | Flag for doc refresh; no AG-95A edit to preserve one-doc scope. |
| `docs/product/AG81B_R1_ANSWER_WORTHINESS_AND_GOLDEN_EXAMPLES.md` | Product examples with AG-94G routing note. | DIAGNOSTIC | no runtime | no | current authority docs | humans | already routed away from Controller doctrine | Keep. |
| `docs/architecture/AG74*` through `AG79*` Controller docs | Historical controller-era phase records. | STALE_SCAFFOLD | no runtime | no | current AG-94G/RunAuthority docs | humans/tests sometimes grep strings | historical record should remain, but not current doctrine | Do not bulk rewrite; only front-matter if a current task is confused by one. |

## 4. Overlapping truth-owner findings

1. **Source obligation satisfaction**
   - Decision: whether official/current/legal/canonical obligation is satisfied.
   - Competing surfaces: EvidenceLedger, ControllerEvidenceLedger,
     `authority_custody_satisfaction`, authoritative source action,
     official execution admission, official query acquisition, final packet.
   - Owner should be: EvidenceLedger for custody before final packet;
     FinalAnswerPacket for final Author/readiness custody.
   - Demote/delete: standalone satisfaction predicates and aggregate-status
     interpretations after all consumers read ledger/packet satisfaction.
   - Product impact: false satisfaction launders weak/secondary evidence into
     official/legal answers.

2. **Recovery permission**
   - Decision: whether to spend a bounded official/current/legal recovery
     attempt.
   - Competing surfaces: SearchJudgment consumer, authoritative source action,
     authority lifecycle arbitration, official execution admission,
     source-class controller, ControllerRecoveryDecision, ControllerLoopSpine.
   - Owner should be: SearchJudgment/EvidenceLedger-derived canonical recovery
     permission under RunKernel.
   - Demote/delete: ControllerLoopSpine and admission/source-class flags after
     runner consumes canonical permission.
   - Product impact: one lane can say "recover" while another says "not needed"
     or "dispatch not authorized", producing expensive non-action.

3. **Weak corpus ownership**
   - Decision: whether weak corpus may own the path or must yield to stronger
     authority recovery.
   - Competing surfaces: weak-corpus controller, official execution admission,
     authoritative source action blocker filters, source-class controller,
     retrieval stop controller.
   - Owner should be: canonical search/sufficiency posture, with weak-corpus
     controller as a bounded executor/adapter.
   - Demote/delete: weak-corpus hard blockers from official/legal recovery
     admission once canonical recovery permission exists.
   - Product impact: the system can stop at weak material while recoverable
     official/legal material was explicitly required.

4. **Source-class recovery dispatch**
   - Decision: whether source-class recovery executor is actually called.
   - Competing surfaces: source-class lifecycle, ControllerLoopSpine,
     ControllerRecoveryDecision, runner context.
   - Owner should be: one RunKernel-authorized recovery permission consumed by
     the runner.
   - Demote/delete: ControllerLoopSpine as final dispatch truth owner.
   - Product impact: diagnostics can say recovery was eligible while no executor
     ran.

5. **Candidate acquisition/candidate fit success**
   - Decision: whether an official/current/legal candidate was acquired, fit,
     readable, accepted, and represented.
   - Competing surfaces: authority candidate passport, authority lifecycle
     candidate visibility, official candidate acquisition trace,
     ControllerEvidenceLedger, EvidenceLedger.
   - Owner should be: EvidenceLedger candidate custody, with passport as a
     projection/input record.
   - Demote/delete: passport aggregate reconciliation as authority proof after
     EvidenceLedger candidate records cover the same identity.
   - Product impact: aggregate counts can look like accepted authority while no
     selected readable candidate exists.

6. **Final selected authority evidence**
   - Decision: whether accepted authority evidence is selected into final
     evidence.
   - Competing surfaces: final evidence bundle, ControllerEvidenceLedger,
     FinalAnswerPacket, authority lifecycle selected records.
   - Owner should be: FinalAnswerPacket, fed by EvidenceLedger-selected
     candidate identity.
   - Demote/delete: final evidence aggregate counts and legacy selected counts
     as proof.
   - Product impact: accepted official evidence can disappear before Author and
     still leave misleading success counts.

7. **Final citation custody / survival**
   - Decision: whether selected authority evidence survived as a final citation.
   - Competing surfaces: FinalAnswerPacket citation eligibility,
     final authority citation survival guard, final evidence citation custody
     projection, official source survival projection, session output source ids.
   - Owner should be: FinalAnswerPacket after it consumes post-Author citation
     observations; short term guard remains protected.
   - Demote/delete: aggregate survival projections as proof.
   - Product impact: weak fallback citations can mask missing official/legal
     citation survival.

8. **Answer readiness**
   - Decision: whether final answer is complete, partial, insufficient, or
     blocked.
   - Competing surfaces: SufficiencyJudgment, FinalAnswerPacket readiness,
     useful-content/failure-card gate, authority citation survival outcome
     guard.
   - Owner should be: SufficiencyJudgment plus FinalAnswerPacket readiness.
   - Demote/delete: post-Author readiness downgrades after citation observation
     is packet-owned.
   - Product impact: the answer can look ready before citation custody proves it.

9. **Report/export truth**
   - Decision: whether diagnostics are merely diagnostics or reconstructed
     decisions.
   - Competing surfaces: official canonical recovery visibility export,
     runtime trace projection assembly, post-author output projection,
     session output projection.
   - Owner should be: none; these are DIAGNOSTIC only.
   - Demote/delete: visibility export hydration of `ControllerRecoveryDecision`.
   - Product impact: humans and tests can chase a report-only decision while the
     runtime consumed a different field.

## 5. Dirty dishes list

### A. Can delete or demote in AG-95B

- Demote `official_canonical_recovery_visibility_export` from decision hydrator
  to pure observer: remove or quarantine the path that calls
  `build_controller_recovery_decision()` when no runtime decision trace exists.
- Rename/export-mark hydrated controller decision fields as absent diagnostic
  fields instead of `controller_recovery_decision`.
- Add focused tests proving visibility export does not manufacture recovery
  decisions and does not import/control runtime owners beyond reading existing
  trace payloads.
- Add a narrow diagnostic-only marker to official source survival projections if
  touched by the same test update.

### B. Needs one blocker resolved first

- Delete or demote `ControllerEvidenceLedger` runtime decision authority after
  `ControllerRecoveryDecision` reads EvidenceLedger/FinalAnswerPacket custody
  directly.
- Delete `authority_custody_satisfaction.py` as a standalone predicate after
  EvidenceLedger/FinalAnswerPacket expose a consumed satisfaction projection
  covering selected evidence, passport/candidate identity, and final packet
  custody.
- Demote `ControllerLoopSpine` after `SourceClassRecoveryRunner` consumes a
  canonical recovery permission action instead of `authorized_spine_action`.
- Delete AnswerContract source-obligation fallbacks in final packet assembly
  after RunAuthorityContract/EvidenceLedger coverage is required on the final
  path.
- Move official/canonical recovery query ownership into QueryPlan before
  deleting query-acquisition repair logic.

### C. Keep for now, but rename/comment as diagnostic-only

- `official_source_survival_projection.py`: aggregate survival only; not custody.
- `official_source_survival_diagnostics.py`: classification only; not readiness.
- `authority_candidate_passport_validation.py`: export classification only; not
  final authority satisfaction.
- `runtime_trace_projection_assembly.py`: passive projection assembly only.
- `session_output_projection.py`: output serialization only.

### D. Do not touch yet

- Provider routing, provider selection, provider order, search depth, search
  budget, query generation, source classification, candidate ranking/filtering,
  Author prompt/prose, final answer prose, citation formatting, persistence
  shape, package/CLI/env/session/database names.
- `source_class_recovery.py` query generation and authority-family recognition.
- `retrieval_stop_controller.py` stop/continue runtime behavior.
- `weak_corpus_controller.py` scheduling behavior.
- `final_evidence_bundle_builder.py` Author evidence and source-id shape.
- `final_authority_citation_survival.py` until packet-owned citation observation
  exists.

## 6. Proposed AG-95B phase

Phase name:

```text
AG-95B - Recovery Visibility Export Decision Hydration Demotion
```

Branch name:

```text
codex/ag95b-recovery-visibility-export-decision-hydration-demotion
```

Exact files likely touched:

- `core/official_canonical_recovery_visibility_export.py`
- `tests/test_official_canonical_recovery_visibility_export_ag50c.py`
- `tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py` only if the
  existing audit fixture expects hydrated decision fields from export
- optionally one narrow architecture note addendum if tests reveal stale wording

Deletion/demotion target:

- Remove or demote the export-only call path that builds a
  `ControllerRecoveryDecision` from visibility inputs when no runtime
  `controller_recovery_decision_trace` exists.
- The export may report:
  `controller_recovery_decision_observed=false` and
  `controller_recovery_decision_projection_source=absent_from_runtime_trace`.
- The export must not present a hydrated projection as if it were runtime
  control truth.

Tests to run:

```powershell
py -m pytest -q tests/test_official_canonical_recovery_visibility_export_ag50c.py
py -m pytest -q tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py
py -m pytest -q tests/test_ag94h_c_recovery_executor_dispatch_authorization_audit.py
py -m ruff check .
py -m pytest -q tests
```

Stop conditions:

- If any runtime path consumes export-hydrated `controller_recovery_decision`
  as control.
- If deleting hydration changes source-class recovery execution behavior.
- If tests require provider/search/query/depth/ranking/Author/citation behavior
  changes.
- If the export field is required by a public output schema and cannot be
  renamed/demoted without a product decision.
- If unrelated tests fail for reasons outside this phase.

Why this is the smallest useful cleanup:

- It removes a real pseudo-owner without touching live behavior.
- It attacks the highest-risk diagnostic lie: report/export can rebuild a
  decision after the fact and look more authoritative than the runtime trace.
- It avoids provider/search/query/final-answer behavior while still deleting or
  demoting code, not merely auditing.

## 7. Complexity budget going forward

Every future phase that adds authority, recovery, source-fit, citation, or
answer-readiness code must include this merge-gate checklist:

- What old surface did this replace or demote?
- What code became obsolete?
- What compatibility shim now has a deletion condition?
- What diagnostic fields are temporary?
- What file got simpler?
- What is the net line-count / complexity impact?
- Why is this not another dirty dish?

Additional gate:

- If a phase adds a new `*_trace`, `*_projection`, `*_visibility`, `*_lifecycle`,
  `*_decision`, `*_custody`, `*_satisfaction`, `*_admission`, or `*_guard`
  surface, it must either delete/demote an older surface in the same phase or
  name the exact blocker and the next deletion phase.
- A diagnostic module must not import provider/search clients, call models,
  mutate RunKernel state, or build control decisions from scratch.
- A compatibility shim must name its canonical owner and deletion trigger in
  code or in the phase doc.
- Aggregate counts are never authority custody unless tied to candidate identity,
  selected evidence identity, or FinalAnswerPacket citation identity.

## 8. Final bundle checklist

For AG-95A:

- Files changed: `docs/architecture/AG95A_AUTHORITY_SURFACE_INVENTORY_AND_DEMOLITION_PLAN.md`.
- Lines added/deleted: report from `git diff --numstat` in the final bundle.
- Runtime behavior changed: no.
- Authority owner changed: no.
- Code deleted: no.
- Top AG-95B deletion target: export-hydrated `ControllerRecoveryDecision` in
  `core/official_canonical_recovery_visibility_export.py`.
- Tests run: `py -m ruff check .`; `py -m pytest -q tests`.
- Live validation run: no.

## 9. AG-95B result note

AG-95B removed the export-time `ControllerRecoveryDecision` hydration path from
`core/official_canonical_recovery_visibility_export.py`.
`build_official_canonical_recovery_visibility_export()` no longer imports or
calls `build_controller_recovery_decision()` and no longer manufactures
`controller_recovery_decision`, retry, stop, or provider-review fields when the
runtime trace did not emit a `controller_recovery_decision_trace` or
`recovery_decision_trace`.

The visibility export now has only two postures:

- observed runtime decision: copy the existing runtime-emitted decision trace and
  mark `controller_recovery_decision_observed=true`;
- absent runtime decision: mark
  `controller_recovery_decision_projection_source=absent_from_runtime_trace` and
  `controller_recovery_decision_authority=not_observed_diagnostic_only`.

The demoted pseudo-owner was the report/export fallback that rebuilt a
Controller-looking decision from lifecycle, ledger, candidate, and final-count
diagnostics. Official-source survival projections were also marked
`diagnostic_only` with aggregate count fields explicitly labeled as not custody
or readiness proof.

Still dirty: runtime recovery permission remains split across SearchJudgment,
authoritative source action, authority lifecycle arbitration, official execution
admission, source-class lifecycle, `ControllerRecoveryDecision`, and
`ControllerLoopSpine`. Final citation custody still has a protected short-term
survival guard outside `FinalAnswerPacket`.

Next deletion target: make source-class recovery dispatch consume one canonical
recovery permission, then demote `ControllerLoopSpine`/official admission flags
from dispatch truth to passive diagnostics.
