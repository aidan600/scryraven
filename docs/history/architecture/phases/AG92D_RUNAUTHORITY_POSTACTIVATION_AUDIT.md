Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG92D_RUNAUTHORITY_POSTACTIVATION_AUDIT).

# AG-92D RunAuthority Post-Activation Audit

Status: Audit complete
Phase type: Static/runtime-structure audit
Validation boundary: Offline static inspection plus focused authority tests
Live validation: Not run
Provider/model/search calls: Not run

## 1. Executive summary

The RunAuthority activation chain is real and runtime-consumed:

```text
RunAuthorityContract
  -> EvidenceLedger
  -> SearchJudgment
  -> SufficiencyJudgment
  -> FinalAnswerPacket
  -> AuthorExecutor
```

The chain is not trace-only. `RunKernel` authorizes each action, reducers store
canonical state, `pipeline_orchestrator.py` calls the executors in the intended
order, and the final Author executor receives the prepared packet authority
block instead of rebuilding final authority locally.

The highest-risk remaining architecture debt is the compatibility shell around
source-class recovery and continuation:

- source-class recovery lifecycle still owns concrete dispatch permission and
  controller-state mutation in several lanes;
- retrieval stop/continue logic still makes active runtime decisions;
- weak-corpus, failure-card, conflict, and indirect-inference postures still
  exist as pre-RunAuthority facts that are consumed by SufficiencyJudgment;
- AnswerContract remains a broad compatibility projection for legacy consumers.

The safest next consolidation is not deletion of compatibility paths. It is a
targeted extraction and demotion pass that preserves behavior while moving
orchestrator callsite assembly and duplicate projections behind smaller adapters.
The recommended next phase is AG-92E targeted consolidation before Roadmap v10 is
made the active source.

## 2. Implemented chain verification

### Contract synthesis

- Owner: `RunKernel.RunAuthorityContract`.
- Canonical state object: `RunKernelState.run_contract`.
- Authorized action / observation: `authorize_run_contract_synthesis()` in
  `core/run_kernel.py`; runtime executor
  `execute_run_contract_synthesis_action()` in
  `core/run_authority_contract_runtime.py`.
- Reducer: `reduce_run_authority_observation()` stores the contract projection
  with `owner="RunKernel.RunAuthorityContract"`, `canonical=True`, and
  `trace_only=False`.
- Runtime consumer:
  - `core/pipeline_orchestrator.py` runs synthesis before query production.
  - `core/evidence_ledger.py` converts the contract projection into ledger
    requirements.
  - `core/query_production_runtime.py` consumes contract source hints and emits
    QueryPlan admission metadata with `origin="run_authority_contract"`.
  - `core/final_answer_runtime_adapter.py` reads the contract, but suppresses
    contract-only source obligations when SufficiencyJudgment is present.
- Tests proving consumption:
  `tests/test_runauthority_contract_synthesis_ag92a.py` covers RunKernel
  reduction, EvidenceLedger consumption, AnswerContract fallback consumption,
  FinalAnswerPacket consumption, QueryPlan hints, smart-model fallback/repair,
  and a static guard that keeps the synthesis brain out of the orchestrator.
- Old authority demoted/bypassed: AnswerContract source-class facts are now
  populated from EvidenceLedger first, then RunAuthorityContract, then legacy
  aggregate/source-tier fallback.

### EvidenceLedger

- Owner: `RunKernel.EvidenceLedger`.
- Canonical state object: `RunKernelState.evidence_ledger`.
- Authorized action / observation: `authorize_evidence_ledger_reduction()` plus
  observation builders in `core/evidence_ledger.py` and the runtime adapter in
  `core/evidence_ledger_runtime.py`.
- Reducer: `reduce_evidence_ledger()` applies requirements, candidate custody,
  aggregate observations, obligation links, and final evidence references.
- Runtime consumer:
  - SearchJudgment authorization requires a reduced RunAuthorityContract and at
    least one EvidenceLedger requirement.
  - SufficiencyJudgment authorization requires the same ledger-backed contract.
  - AnswerContract runtime handoff prefers ledger facts over legacy aggregates.
  - FinalAnswerPacket adapter reads ledger custody and final evidence identity.
- Tests proving consumption:
  `tests/test_evidence_ledger_ag91j.py` verifies candidate identity, custody,
  helper-assessment non-promotion, aggregate insufficiency, official/current
  gaps, AnswerContract consumption, FinalAnswerPacket consumption, and static
  guards.
- Old authority demoted/bypassed: aggregate source counts and source-tier
  summaries are compatibility observations; they cannot satisfy strong source
  requirements without linked eligible candidates.

### SearchJudgment

- Owner: `RunKernel.RunAuthoritySearchJudgment`.
- Canonical state object: `RunKernelState.search_judgment` and
  `RunKernelState.search_judgment_history`.
- Authorized action / observation: `authorize_search_judgment()` and
  `execute_run_authority_search_judgment_action()`.
- Reducer: `reduce_run_authority_observation()` stores the reduced projection
  with canonical owner fields, search action, reasons, required recovery classes,
  insufficient search posture, blocked duplicate queries, and continuation
  flags.
- Runtime consumer:
  - `core/pipeline_orchestrator.py` builds `RunSearchJudgmentInput` after
    pre-recovery EvidenceLedger reduction.
  - `core/run_authority_search_judgment_consumers.py` consumes only a reduced
    canonical projection and translates it into source-class recovery facts.
  - `core/authoritative_source_action.py` applies the judgment before and after
    legacy AnswerContract gap handling.
  - `core/source_class_recovery_controller.py` and
    `core/controller_loop_spine.py` still execute the recovery lifecycle, but
    they receive RunAuthority-derived lifecycle requirements when the judgment
    demands recovery.
- Tests proving consumption:
  `tests/test_runauthority_iterative_search_judgment_ag92b.py` verifies reduced
  projection storage, authorization gating, official/legal/canonical/source-bound
  recovery, duplicate query blocking, satisfied-ledger stop, runtime consumer
  promotion into recovery action, smart fallback/repair, raw-material exclusion,
  and static guards.
- Old authority demoted/bypassed: legacy recovery can still execute, but
  required recovery for RunAuthority source gaps is introduced by the reduced
  SearchJudgment, not by local orchestrator booleans.

### SufficiencyJudgment

- Owner: `RunKernel.RunAuthoritySufficiencyJudgment`.
- Canonical state object: `RunKernelState.sufficiency_judgment` and
  `RunKernelState.sufficiency_judgment_history`.
- Authorized action / observation: `authorize_sufficiency_judgment()` and
  `execute_run_authority_sufficiency_judgment_action()`.
- Reducer: `reduce_run_authority_observation()` stores final answer action,
  final readiness, final answer posture, missing obligations, mandatory caveats,
  prohibited answer upgrades, conflict posture, inference posture, and source
  citation posture.
- Runtime consumer:
  - `core/pipeline_orchestrator.py` builds `RunSufficiencyJudgmentInput` after
    final EvidenceLedger reduction.
  - `core/final_answer_runtime_adapter.py` validates the canonical sufficiency
    projection, converts its obligations into packet source obligations,
    overwrites legacy final readiness, and imports final answer posture.
  - `core/final_answer_packet_runtime.py` marks the packet observation with
    `sufficiency_judgment_consumed=True`.
- Tests proving consumption:
  `tests/test_runauthority_sufficiency_judge_ag92c.py` verifies required-source
  obligations, source-bound unknown behavior, insufficient and sufficient stop
  actions, ordinary-explainer non-overblocking, unresolved conflict, indirect
  inference, weak/failure-card posture propagation, final packet consumption,
  smart fallback/repair, raw-material exclusion, and static guards.
- Old authority demoted/bypassed: legacy readiness fields can still be observed,
  but when SufficiencyJudgment is present the packet adapter overwrites legacy
  readiness/posture and skips duplicate legacy contract obligations.

### FinalAnswerPacket

- Owner: `RunKernel.FinalAnswerPacket`.
- Canonical state object: `RunKernelState.final_answer_packet` and
  `RunKernelState.final_answer_authority_projection`.
- Authorized action / observation: `authorize_final_answer_packet_prepare()` and
  `execute_final_answer_packet_prepare_action_from_scope()`.
- Reducer: `reduce_run_authority_observation()` stores the packet and an
  `author_payload_ref` with `status="author_input_ready"`.
- Runtime consumer:
  - `authorize_author_execution()` refuses to create an Author action unless
    the canonical packet and ready author payload ref exist.
  - `core/final_answer_packet.py` converts packet state into an Author payload
    with eligible source IDs, missing obligations, final answer posture,
    sufficiency decision, mandatory caveats, and prohibited upgrades.
  - `core/final_answer_runtime_assembly.py`,
    `core/post_author_output_projection.py`, and
    `core/session_output_projection.py` project packet refs for compatibility and
    export surfaces.
- Tests proving consumption:
  `tests/test_final_answer_author_runkernel_ag91k.py` and
  `tests/test_runauthority_sufficiency_judge_ag92c.py` verify packet reduction,
  missing-obligation blocking, source-bound citation posture, post-author
  RunKernel packet reference, and packet consumption of SufficiencyJudgment.
- Old authority demoted/bypassed: post-author AnswerContract projections hide
  RunAuthority contract requirements from reappearing as local final authority,
  and the packet adapter demotes legacy final inputs when canonical sufficiency
  is present.

### AuthorExecutor

- Owner: `RunKernel.AuthorExecutor`.
- Canonical state object: `RunKernelState.author_observation` and
  `RunKernelState.author_outcome`.
- Authorized action / observation: `authorize_author_execution()` and
  `execute_author_action()`.
- Reducer: `reduce_run_authority_observation()` stores sanitized author outcome
  and observation metadata without raw prompt or raw report payload.
- Runtime consumer:
  - The Author executor validates action/payload alignment.
  - The prompt is assembled from the packet authority block and packet answer
    requirements.
  - Session and post-author projections reference the RunKernel packet rather
    than reauthorizing final answer posture.
- Tests proving consumption:
  `tests/test_final_answer_author_runkernel_ag91k.py` verifies Author gating,
  packet-derived prompt input, raw-prompt exclusion, and static absence of old
  direct Author model calls in `pipeline_orchestrator.py`.
- Old authority demoted/bypassed: the old local Author path is replaced by a
  packet-authorized action. Compatibility projections remain after execution but
  are trace/export surfaces, not Author authority.

## 3. Orchestrator containment review

Current `core/pipeline_orchestrator.py` line count is 4,849 lines.

Approximate normalized line count before AG-91J was 4,545 lines
(`db64c7c^`). The AG-91J through AG-92C net change in the orchestrator is
approximately +304 lines, with `git diff --numstat db64c7c^ HEAD -- core/pipeline_orchestrator.py`
showing 393 insertions and 89 deletions.

Approximate checkpoint line counts:

| Checkpoint | Commit | Lines |
| --- | --- | ---: |
| Before AG-91J | `db64c7c^` | 4,545 |
| AG-91J | `db64c7c` | 4,617 |
| AG-91K | `b1c9705` | 4,590 |
| AG-92A | `a460638` | 4,650 |
| AG-92B | `aba9b76` | 4,762 |
| AG-92B repair | `39128b6` | 4,758 |
| AG-92C / HEAD | `2ab55be` / HEAD | 4,849 |

New callsites and classification:

| Callsite / addition | Classification | Audit note |
| --- | --- | --- |
| RunAuthorityContract synthesis and reduction before query production | Lifecycle handoff | Correct placement. The orchestrator authorizes and reduces; contract policy lives in the runtime module and reducer. |
| Query production `run_contract_projection` argument | Adapter/coordination | Contract hints are passed into QueryPlan admission without local query-order authority. |
| EvidenceLedger reduction from RunAuthorityContract | Lifecycle handoff | Required for authority collapse. It gives the ledger canonical requirements. |
| EvidenceLedger reduction from runtime/source-class facts before recovery | Lifecycle handoff | Correctly prepares SearchJudgment, but the input assembly block is bulky. |
| AnswerContract projection built from ledger/contract facts | Trace/projection plus compatibility | Still needed for legacy consumers. It should remain subordinate to ledger/contract. |
| SearchJudgment input assembly, execution, and reduction | Lifecycle handoff with extraction candidate | Policy lives outside the orchestrator, but the orchestrator assembles many facts. Extracting a builder would reduce domain-shaped surface area. |
| Authoritative-source action adapter consumption of SearchJudgment | Adapter/coordination | Good direction: adapter is mechanical, while recovery lifecycle remains an old active surface. |
| Final contract and EvidenceLedger reductions | Lifecycle handoff | Correctly refreshes canonical state before sufficiency. |
| SufficiencyJudgment input assembly, execution, and reduction | Lifecycle handoff with extraction candidate | Runtime logic is outside the orchestrator; fact gathering is large enough to merit extraction. |
| FinalAnswerPacket prepare/execute/reduce block | Lifecycle handoff | Correctly centralizes final packet preparation under RunKernel. |
| AuthorExecutor authorize/execute/reduce block | Lifecycle handoff | Correctly gates Author on packet readiness. |
| Post-final EvidenceLedger reduction | Trace/projection plus lifecycle refresh | Useful for final evidence custody, but should be wrapped to keep repeated ledger-call shape out of the orchestrator. |
| Smart-model flag/provider-option packaging | Coordination with future cost risk | Flags default off; central option packaging would make future live validation safer. |
| Retrieval dispatch checkpoint reconciliation | Trace/projection | Reconciliation is projection work, but it touches a sensitive continuation surface. |

Overall containment finding: the orchestrator grew primarily as a coordination
shell rather than as a renewed domain brain. The new validators, deterministic
judges, prompt/render logic, and reducers live outside the orchestrator, and
static tests guard that boundary. The top concern is not hidden policy logic in
the orchestrator; it is the volume of inline fact assembly and repeated
projection plumbing.

Top extraction opportunities:

1. Extract SearchJudgment input construction from orchestrator locals into a
   dedicated adapter/builder with static guards.
2. Extract SufficiencyJudgment input construction the same way.
3. Wrap EvidenceLedger reduction callsites behind named lifecycle helpers for
   contract, pre-recovery runtime, final runtime, and post-final evidence.
4. Centralize final packet/Author handoff callsite assembly into a small
   RunKernel finalization adapter.
5. Centralize RunAuthority projection references and smart-model option
   packaging to reduce local boolean drift.

## 4. Compatibility surface inventory

| Surface | What it still does | Still runtime authority? | Subordinate to RunAuthority? | Delete/demote status |
| --- | --- | --- | --- | --- |
| AnswerContract runtime handoff | Builds legacy-compatible facts, source-class status, weak/conflict/inference refs, and final packet inputs. | Partly. It still shapes compatibility facts but no longer owns final readiness when sufficiency exists. | Yes for source facts: EvidenceLedger first, RunAuthorityContract next, legacy aggregate fallback last. | Demote later in a focused phase; do not delete yet. |
| Source-class recovery lifecycle | Mutates controller state and records concrete recovery/retrieval lifecycle decisions. | Yes. It still participates in dispatch permission. | Partly. SearchJudgment can require recovery, but lifecycle/controller gates still execute. | Requires focused consolidation phase. |
| Retrieval stop/continue | Produces stop/continue decisions for iteration/evaluator-style lanes and stop projections. | Yes. It can still stop or continue retrieval. | Partly. SearchJudgment governs RunAuthority source-gap search posture, but old stop gates remain active. | Not deletable yet; demote lane by lane. |
| Weak corpus/failure-card posture | Records weak evidence and failure-card state that affect search and answer posture. | Yes as upstream facts. | Consumed by SufficiencyJudgment and packet posture. | Demote later after sufficiency inputs are canonicalized. |
| Conflict posture | Carries unresolved conflict state into AnswerContract/Sufficiency. | Yes as upstream fact source. | Consumed by SufficiencyJudgment; final answer posture is canonical downstream. | Risky to touch without focused tests and answer-quality review. |
| Indirect inference posture | Carries inference/unsupported-claim posture into final answer inputs. | Yes as upstream fact source. | Consumed by SufficiencyJudgment and final packet. | Preserve until direct RunAuthority inference inputs exist. |
| Final-answer packet legacy inputs | Preserve legacy AnswerContract/evidence/obligation fields for packet assembly and compatibility. | Partly. Fallbacks exist when canonical sufficiency is absent. | Yes when SufficiencyJudgment exists; readiness and posture are overwritten. | Safe Tier 2 cleanup after tests prove sufficiency is always present in intended lanes. |
| Source-obligation projections | Export source requirements/obligations to older surfaces. | Mostly compatibility/export. | EvidenceLedger and SufficiencyJudgment are canonical owners. | Demote/centralize in Tier 1/Tier 2. |
| Post-author/session projections | Build session packets and post-author refs for output/export. | No final authority, if RunKernel packet is present. | Yes. They reference RunKernel final packet and raise on local divergence. | Keep, but centralize references and static guards. |
| QueryPlan/query production handoffs | Produce query candidates/order and attach contract source hints. | QueryPlan still owns query production order. | RunAuthorityContract supplies hints and metadata but does not reorder locally. | Preserve; future query-authority cleanup can be separate. |

## 5. Duplicate state / duplicate owner map

| Representation | Canonical | Compatibility / trace | Deletion candidate | Unresolved |
| --- | --- | --- | --- | --- |
| Source requirements | RunAuthorityContract and EvidenceLedger requirements | AnswerContract source classes, OfficialCurrentSourceCustody summaries, QueryPlan metadata | Aggregate source-tier satisfaction fallback | None for final authority; query-production ownership remains separate. |
| Source obligations | EvidenceLedger obligation links and SufficiencyJudgment missing obligations | AnswerContract fulfillment/source-obligation projections | Duplicate packet legacy obligation fallbacks when sufficiency always exists | Exact retirement order needs tests. |
| Missing/partial/satisfied classes | EvidenceLedger requirement statuses; SufficiencyJudgment final status | AnswerContract missing/partial/present facts; source-class lifecycle fields | Aggregate-only class satisfaction | Recovery lifecycle still uses old status fields. |
| Final evidence identity | EvidenceLedger final evidence refs plus FinalAnswerPacket eligible source IDs | final evidence bundle, citation handoffs, session projection refs | Local packet fallback in session projection after canonical path is universal | Need careful export compatibility review. |
| Citation eligibility | FinalAnswerPacket authority block | Citation runtime handoffs and source refs | Legacy citation eligibility derived outside packet | None if packet ref remains present. |
| Final readiness | SufficiencyJudgment and FinalAnswerPacket | `evidence_sufficient`, `is_sufficient`, `synth_was_insufficient`, weak/failure flags | Legacy readiness fallback once sufficiency is mandatory | Need lane coverage proof before deletion. |
| Final answer posture | SufficiencyJudgment final answer posture | AnswerContract notes, weak/failure/conflict/inference postures, Author notes | Duplicate caveat/posture synthesis outside sufficiency | Product quality review still needed. |
| Recovery permission | SearchJudgment for RunAuthority-required source-gap recovery | Source-class recovery lifecycle and controller spine dispatch facts | Local booleans that duplicate judgment output | Actual dispatch authority remains shared. |
| Insufficiency posture | SufficiencyJudgment for final answer; SearchJudgment for search loop | retrieval stop projection, weak/failure card, legacy AnswerContract flags | Duplicate packet fallback fields | Needs lane-by-lane demotion. |
| Conflict/inference posture | SufficiencyJudgment once final input is built | Scrutineer/conflict handoffs, indirect inference handoffs | Duplicate final posture restatement outside packet | Requires focused behavior tests and answer-quality evaluation. |

## 6. Test guard review

Tests that correctly guard new authority:

- `tests/test_evidence_ledger_ag91j.py` guards ledger custody, aggregate
  non-promotion, missing official/current gaps, AnswerContract consumption,
  FinalAnswerPacket consumption, and static import/surface boundaries.
- `tests/test_final_answer_author_runkernel_ag91k.py` guards packet preparation,
  Author gating, packet-derived prompt input, post-author RunKernel reference,
  and absence of old direct Author model callsites in the orchestrator.
- `tests/test_runauthority_contract_synthesis_ag92a.py` guards contract
  synthesis, ledger consumption, QueryPlan handoff, packet consumption, and
  smart fallback/repair.
- `tests/test_runauthority_iterative_search_judgment_ag92b.py` guards canonical
  search judgment, required recovery actions, duplicate query blocking, runtime
  consumer promotion, and raw-material exclusion.
- `tests/test_runauthority_sufficiency_judge_ag92c.py` guards canonical final
  sufficiency, source-bound unknowns, weak/failure/conflict/inference posture,
  packet consumption, and raw-material exclusion.

Tests that still guard old behavior intentionally:

- AG20 and AG22 official/current recovery tests still protect source-class
  recovery quality, weak-domain handling, duplicate attempts, and domain
  constraints.
- AG32 checkpoint/runtime seam tests still protect evidence integration
  checkpoint decisions, weak/source/conflict/budget decisions, side packets, and
  no-live-call boundaries.
- AG44/AG45 continuation tests still protect ordinary, evaluator, expander,
  scout, and targeted continuation ownership.
- `tests/test_controller_loop_spine.py` still guards source/conflict dispatch
  through the spine rather than local orchestrator recomputation.
- AG68 projection-only tests guard that projection envelopes do not become
  dispatch control inputs.

Tests updated or behavior-adapted during AG-92B/C:

- SearchJudgment tests now expect RunAuthority to promote required source-class
  recovery into the legacy lifecycle instead of leaving recovery entirely local.
- Sufficiency tests now expect FinalAnswerPacket to consume canonical sufficiency
  and demote legacy missing/inference fallbacks.

Tests likely to become stale after consolidation:

- Tests that assert exact legacy AnswerContract source-class shape may need
  rewrites once AnswerContract is reduced to compatibility-only export.
- Recovery lifecycle tests that assert controller-state field names may need a
  new RunAuthority-facing assertion layer.
- Final packet fallback tests should be split into "canonical lane" and
  "legacy compatibility lane" before deleting fallbacks.
- Projection-only guard tests should remain, but may need updated fixture names
  if projection refs are centralized.

## 7. Risk review

- Too many new modules: The AG-91J/K and AG-92A/B/C sprint added a healthy
  authority separation, but also several narrowly scoped runtime/projection
  modules. The separation is justified, but central projection naming and
  callsite helpers should be tightened before product work expands it further.
- Too many projections: AnswerContract, source-obligation projections,
  post-author projections, session projections, recovery lifecycle telemetry,
  and RunAuthority projections overlap. The risk is future contributors reading
  the wrong projection as canonical.
- Orchestrator growth: Net +304 lines since before AG-91J is not catastrophic,
  but the orchestrator is now a large coordination shell. Inline input assembly
  should be extracted while policy is still clearly outside it.
- Prompt/model surface expansion: Contract, SearchJudgment, and
  SufficiencyJudgment each have optional smart-model paths. Their defaults are
  off, but enabling them expands prompt, cost, repair, and latency surfaces.
- Cost/latency from future smart-model flags: SearchJudgment and
  SufficiencyJudgment are especially sensitive because they can run near
  retrieval/finalization boundaries. Cache and budget policy should be explicit
  before live use.
- Interaction with live validation: This audit did not run live validation.
  Official/current recovery reliability and prompt quality must be validated in
  a separate product or dogfood lane.
- Source-bound numeric behavior: Final answer and post-author numeric
  consistency remain sensitive. RunAuthority can require source-bound unknowns,
  but downstream numeric correction/guard surfaces still deserve protected
  review.
- Official/current recovery reliability: SearchJudgment now demands recovery,
  but actual dispatch still depends on source-class lifecycle and controller
  gates. Reliability is only as strong as that compatibility bridge.
- Final answer over-caveating or under-caveating: SufficiencyJudgment centralizes
  posture, but legacy weak/failure/conflict/inference facts still feed it. The
  duplicate posture sources can produce excessive or insufficient caveats unless
  answer-quality evaluation catches it.

## 8. Consolidation recommendations

### Tier 1 - Safe cleanup/consolidation now

- Extract SearchJudgment and SufficiencyJudgment input builders from
  `pipeline_orchestrator.py`.
- Extract named EvidenceLedger lifecycle helpers for contract, pre-recovery
  runtime, final runtime, and post-final reductions.
- Centralize RunAuthority projection refs and owner/canonical validation helpers.
- Add static tests for orchestrator chain order and for absence of local
  SearchJudgment/SufficiencyJudgment policy in the orchestrator.
- Add a focused final-adapter test proving legacy readiness is ignored whenever
  canonical sufficiency is present.
- Remove stale imports only if discovered by tooling; do not manually clean
  compatibility surfaces yet.

### Tier 2 - Focused behavior-preserving authority cleanup

- Demote AnswerContract final-readiness and final-posture fallbacks in canonical
  RunAuthority lanes.
- Replace source-class recovery permission booleans with a direct
  SearchJudgment-derived recovery permission object while preserving lifecycle
  execution.
- Collapse duplicate weak/failure/conflict/inference posture inputs into a
  single SufficiencyJudgment-facing adapter.
- Retire aggregate source-tier satisfaction as a possible source-class fallback
  once all canonical lanes use EvidenceLedger candidate links.
- Reduce post-author AnswerContract restatement so export/session surfaces point
  to RunKernel packet refs without rebuilding final authority.
- Split tests into canonical RunAuthority assertions and explicit legacy
  compatibility assertions before deleting any fallback.

### Tier 3 - Product behavior / live-validation-dependent work

- Official/current dogfood for recovery reliability.
- Answer-quality evaluation for caveat posture, source-bound unknowns, conflict
  handling, and indirect inference.
- Prompt bakeoffs for Contract, SearchJudgment, and SufficiencyJudgment smart
  modes.
- Cache/cost/latency efficiency work before enabling smart-model flags by
  default.
- UX/demo work only after recovery and final answer posture have product-quality
  evidence.

## 9. Recommended next phase

Recommended next phase: AG-92E targeted consolidation pass.

Rationale: the activation chain is real enough that a Roadmap v10 source refresh
would not be blocked by a missing authority link. However, v10 should not freeze
the current compatibility sprawl as the new baseline. A small targeted AG-92E
can extract orchestrator callsite builders, centralize projection refs, and
demote the safest legacy final-answer fallbacks without changing runtime
behavior. That will make Roadmap v10 clearer and safer.

## 10. Roadmap v10 inputs

Roadmap v10 should say:

- Completed phases: AG-91J EvidenceLedger/source custody under RunKernel;
  AG-91K FinalAnswerPacket and AuthorExecutor under RunKernel; AG-92A
  RunAuthorityContract synthesis; AG-92B iterative SearchJudgment; AG-92C final
  SufficiencyJudgment; AG-92D post-activation audit.
- Current architecture checkpoint: RunAuthority now owns the runtime-consumed
  chain from contract synthesis through final Author execution. The chain is
  canonical and not trace-only.
- Remaining architecture debt: source-class recovery lifecycle, retrieval
  stop/continue, weak/failure/conflict/inference postures, AnswerContract
  compatibility facts, and post-author/session projections still overlap with
  RunAuthority state.
- Next architecture work: AG-92E targeted consolidation before broad product
  lanes.
- Next product lanes after consolidation: official/current recovery dogfood,
  answer-quality evaluation, prompt bakeoffs, smart-mode cache/cost policy, and
  UX/demo readiness.

## Audit conclusion

No stop-condition contradiction was found. FinalAnswerPacket and AuthorExecutor
consume the canonical SufficiencyJudgment-derived packet path, and
SearchJudgment is consumed by the recovery bridge. The important caution is that
SearchJudgment has not deleted old recovery authority; it has subordinated part
of it while source-class lifecycle and controller-spine dispatch remain active.
That is acceptable for AG-92D, but it should be the primary consolidation target
before Roadmap v10 becomes the active source.
