Status: historical
Authority: none
Default-read: no
Historical-scope: Controller-era current-state rollup preserved as historical provenance.
Superseded-by: docs/architecture/SCRYRAVEN_CURRENT_STATE.md

# ScryRaven Current State

> **AG-94G supersession banner:** This file is a current-looking historical
> rollup and still contains Controller-era and orchestrator-untouched language.
> For AG-89+ authority doctrine, use
> `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md` and
> `docs/architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md` and
> `docs/architecture/AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md`. Treat
> `core/pipeline_orchestrator.py` as a coordination shell with remaining
> authority debt: closed when a product phase keeps it out of scope, licensed
> when a phase opens it, and a target surface when a phase explicitly strangles
> orchestrator authority.

## AG-80A — Implementation Playbook / Controller Authority Docs (2026-06-03)

Status: complete/readiness for review. AG-80A adds `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` as a documentation-only implementation guide for future Codex phases after the Controller-authority closure line. No runtime code, prompt, provider/search/retrieval, citation, Author, DB/session/RunOutcome, cache, or live-validation behavior changes are authorized or made by this phase.

The playbook records the closed authority model: Controller decides, orchestrator executes, and trace/projection/export layers observe. It defines the expected phase pattern of passive contract first, behavior-preserving runtime wiring second, and optional behavior activation only when a future phase explicitly licenses the behavior change. It also gives checklists for stable JSON-safe handoff schemas, trace fragments, no-change flags, fixture/static tests, safe `core/pipeline_orchestrator.py` touches, protected-surface guards, full-suite/CI expectations, and live-validation stop rules.

Current classifications from AG-79D remain in force: Controller-owned/controlled surfaces are listed for already-closed gates and handoffs; Brave recon rewrite, disambiguation retry, residual query/finalization behavior, retrieval ranking/filtering, final evidence selection, citation formatting, prompt text, Author prose, and SCR/SES runtime behavior beyond approved handoff trace identity remain protected legacy behavior; trace/projection/export surfaces remain observer-only; AG-76D-AD adapter cleanup remains parked; and AG-78G remains live-gated.

Recommended next phase: Roadmap v4 / Project Source refresh. No roadmap v4 work is included in AG-80A.


## AG-79D — Targeted Orchestrator Authority Closure (2026-06-03)

Status: complete/readiness for review. AG-79D adds `docs/history/architecture/phases/AG79D_TARGETED_ORCHESTRATOR_AUTHORITY_CLOSURE.md` as a docs-only targeted audit of the remaining orchestrator and orchestrator-adjacent decision surfaces after AG-76D-SCR-R1 and AG-76D-SES-R1 runtime trace wiring.

Executive verdict: the current Controller-authority transfer audit line is closed at classification depth. Retrieval stop/continue, weak-corpus recovery, source-class/authoritative-source recovery, conflict-resolution retrieval, scout/expander/evaluator/ordinary continuation gates, final evidence identity handoff, citation/source-list identity, Analyst/Author handoff packaging, weak/failure-card posture, conflict labels, indirect-inference labels, and SCR/SES runtime handoff trace identity are controlled or trace-classified.

Protected legacy behavior intentionally left alone includes Brave recon rewrite, low entity-utilization disambiguation retry, query replacement/entity correction, `_finalize_retrieval_queries`, recency merge, official-bias insertion, query ordering, provider/search/depth behavior where no Controller-owned handoff already supplies it, retrieval ranking/filtering, final evidence selection, citation formatting, prompt text, Author notes/prose, Scrutineer/remediation behavior, and synthesis-evaluator supplemental-search behavior. AG-79D found no active hidden-authority surface requiring an immediate future repair; remaining local runtime authorities are classified as protected legacy behavior or trace/projection-only identity rather than changed in this phase.

AG-76D-AD adapter cleanup is now appropriate as later behavior-preserving maintainability cleanup, but it should not run before the implementation-doc refresh unless AG-80A schedules it. AG-80A implementation playbook/docs is recommended next. Roadmap v4 should wait until AG-80A. AG-78G remains live-gated; no live validation is authorized by this state.


## AG-76D-SES — Controller-Owned Synthesis-Evaluator Supplemental-Search Handoff Contract (2026-06-02)

Status: implemented/readiness for review. AG-76D-SES adds `core/synthesis_evaluator_supplemental_search_handoff_contract.py`, `tests/test_ag76d_ses_synthesis_evaluator_supplemental_search_handoff_contract.py`, and `docs/history/architecture/phases/AG76D_SES_CONTROLLER_OWNED_SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF.md` as a minimal passive contract and fixture/static test phase for the synthesis-evaluator supplemental-search handoff.

The contract records synthesis-evaluator run eligibility and run gate posture, completeness posture (`skipped`, `sufficient`, `insufficient`, `parse_failed`), deficiency identity/text, supplemental query identity and source evaluator decision refs, supplemental-search admission posture, supplemental provider role/list/depth as already-computed protected legacy posture, supplemental evidence identity, final evidence rebuild identity, Analyst re-run admission posture, Author note identity for `hedge_appropriately_where_data_is_missing`, and compact AnswerContract / AnalystAuthorHandoff / CitationSourceHandoff refs. Serialization is JSON-safe under the stable `synthesis_evaluator_supplemental_search_handoff` trace key.

AG-76D-SES is passive and fixture/static only. It does not wire into the supplemental-search block, does not touch `core/pipeline_orchestrator.py`, and does not change evaluator behavior, prompt behavior, supplemental query generation, provider/search/depth behavior, retrieval/ranking/filtering behavior, final evidence selection or rebuild behavior, Analyst re-run behavior, Author note/prose behavior, citation behavior, DB/session/`RunOutcome` shape, cache behavior, live validation, or provider/model/search calls.

AG-76D-SCR-R1 is complete/readiness for review: Scrutineer/remediation has behavior-preserving runtime trace wiring, so this file no longer recommends AG-76D-SCR-R1 as the next phase. Remaining hidden-authority surfaces are residual orchestrator-local query/recon/recency and final-assembly decisions documented in AG-79C plus any future separately licensed runtime consumption of passive handoff contracts. AG-78G remains live-gated.

Recommended next phase: AG-79D targeted orchestrator authority repair or another explicitly licensed passive handoff/runtime-consumption phase. Do not recommend cache implementation.



## AG-76D-SCR — Controller-Owned Scrutineer / Remediation Handoff Contract (2026-06-02)

Status: implemented/readiness for review. AG-76D-SCR adds `core/scrutineer_remediation_handoff_contract.py`, `tests/test_ag76d_scr_scrutineer_remediation_handoff_contract.py`, and `docs/history/architecture/phases/AG76D_SCR_CONTROLLER_OWNED_SCRUTINEER_REMEDIATION_HANDOFF.md` as a minimal passive contract and fixture/static test phase for Scrutineer/remediation handoff representation.

The contract records Scrutineer run eligibility/admission posture, skipped/running/completed posture, flag count and high-severity threshold posture, searchable/non-searchable category posture, remediation query identity and source flag IDs, novelty/filter results, remediation dispatch authorization with provider-role/depth facts as already-computed protected legacy posture, remediation evidence/final-evidence identity, re-synthesis admission posture, Author directive identity, and compact AnswerContract / AnalystAuthorHandoff / CitationSourceHandoff refs. Serialization is JSON-safe under the stable `scrutineer_remediation_handoff` trace key.

AG-76D-SCR is passive and fixture/static only. It does not wire into the runtime Scrutineer block, does not touch `core/pipeline_orchestrator.py`, and does not change Scrutineer behavior, prompt behavior, remediation query generation, provider/search/depth/query behavior, retrieval behavior, Analyst behavior, Author prompt/prose behavior, citation behavior, DB/session/`RunOutcome` shape, cache behavior, live validation, or provider/model/search calls.

AG-76D-SCR-R1 status: complete/readiness for review. Scrutineer/remediation no longer remains merely parked behind AG-76D-SCR; behavior-preserving runtime trace wiring exists, while prompts, provider/search/depth, retrieval, Analyst, Author, citation, DB/session/RunOutcome, cache, and live validation behavior remain closed. Synthesis-evaluator supplemental search is now covered by AG-76D-SES at passive contract depth. AG-78G remains live-gated.

Recommended next phase: AG-79D targeted orchestrator authority repair or another explicitly licensed passive handoff/runtime-consumption phase. Do not recommend cache implementation.


## AG-79C — Orchestrator Decision Audit (2026-06-02)

Status: complete/readiness for review. AG-79C adds `docs/history/architecture/phases/AG79C_ORCHESTRATOR_DECISION_AUDIT.md`, a docs-only static audit of broad local domain decisions in `core/pipeline_orchestrator.py` and orchestrator-adjacent Controller, recovery, final-assembly, citation, Author, adapter, and trace/projection paths.

Executive verdict: retrieval stop/continue, weak-corpus recovery, source-class recovery, targeted/ordinary continuation spine authorization, conflict-resolution retrieval, citation/source-list identity, and Analyst/Author handoff packaging have meaningful Controller-owned handoff coverage where their decisions are consumed. Provider/search/depth/query behavior that AG-79B classified remains behavior-preserving and not runtime-wired. Final evidence/citation/Author identity has stronger handoff visibility, while prompt text, prompt semantics, citation formatting, source ordering, Author prose, and legacy final evidence selection remain protected legacy behavior.

Highest remaining active hidden-authority cluster: Scrutineer/remediation. Its run gate, flag threshold, searchable category filter, remediation query generation, novelty filtering, provider/depth selection, re-synthesis trigger, and Author directive insertion can search, re-synthesize, caveat, omit, or alter Author context without a dedicated Controller-owned remediation handoff. AG-76D-SCR is elevated as the exactly one recommended next phase.

Synthesis-evaluator supplemental search remains active hidden authority and should eventually receive its own Controller-owned handoff, but it is parked behind AG-76D-SCR because Scrutineer/remediation has the higher concentrated final-answer risk. AG-76D-AD adapter cleanup remains parked because adapter debt does not block safe review or the next handoff design. AG-78G remains live-gated; AG-79C ran no live validation, product-path commands, provider/model calls, or search calls.

Recommended next phase: AG-76D-SCR — Controller-owned Scrutineer/remediation handoff contract.


## AG-79B — Controller-Governed Provider/Search and Final Assembly Boundary Repair (2026-06-02)

Status: implemented/readiness for review. AG-79B adds `docs/history/architecture/phases/AG79B_CONTROLLER_GOVERNED_PROVIDER_SEARCH_FINAL_ASSEMBLY_BOUNDARY.md`, `core/provider_search_final_assembly_authority_boundary.py`, and focused static fixture tests for provider/search/depth/query authority plus final evidence/citation/Author assembly authority.

Exact boundary repaired or proved: already-computed Controller-owned provider allocation, retrieval/depth posture, query-source/recovery-dispatch posture, final evidence identity, citation/source-list identity, Author context identity, AG-77 conflict labels, AG-78 direct-vs-inferred labels, and insufficiency/source-obligation labels are classified and tested so they cannot be silently bypassed in the new static boundary fixtures. Where no Controller-owned posture exists, existing provider choice, search depth, recency merge, query generation, final evidence selection, citation ordering/formatting, prompt text, and Author prose are explicitly protected legacy behavior rather than changed. Supplemental search, Scrutineer/remediation, and broad orchestrator-local domain decisions remain consciously parked hidden authority.

AG-79B is behavior-preserving authority-boundary hardening only. It does not change runtime behavior, prompts, provider/search/retrieval behavior, citation behavior, Author behavior, Scrutineer/remediation behavior, Economist behavior, DB/session/RunOutcome shape, cache behavior, live validation, or `core/pipeline_orchestrator.py`.

AG-78G remains live-gated unless explicitly authorized. AG-76D-AD remains parked because adapter debt did not block this boundary proof.

Recommended next phase: AG-79C — Orchestrator Decision Audit.


## AG-79A — Passive-to-Active Controller Authority Audit (2026-06-02)

Status: complete/readiness for review. AG-79A adds `docs/history/architecture/phases/AG79A_PASSIVE_TO_ACTIVE_CONTROLLER_AUTHORITY_AUDIT.md`, a docs/static audit distinguishing Controller-visible state from Controller-governing authority across AnswerContract, RunController, AG-76D handoffs, AG-77 conflict posture, AG-78 indirect inference posture, recovery lanes, Scrutineer/remediation, synthesis-evaluator supplemental search, provider/search/depth/query selection, final evidence/citation/Author assembly, and `core/pipeline_orchestrator.py` domain branches.

Executive verdict: many Controller-owned states are represented, trace-visible, and sometimes AnswerContract-visible, but only a narrower set is proven runtime-governing or final-answer-governing today. Retrieval stop/continue, targeted/source-class/weak-corpus/conflict-retrieval admission, weak/failure-card handoff output, citation/source-list handoff execution, Analyst/Author handoff packaging, and AG-78E presentation labeling have the strongest consumption evidence. Router/query preparation, retrieval loop descriptors, many RunController trace fields, AG-77C/AG-78C runtime handoffs, provider diagnostics, Scrutineer/remediation trace, supplemental search trace, and adapter mirrors remain passive, advisory, or trace-only unless consumed by a runtime gate or final handoff.

Highest hidden-authority risk remains in provider/search/depth/query selection and final evidence/citation/Author assembly, with Scrutineer/remediation and synthesis-evaluator supplemental search also carrying real hidden authority. AG-79A selects exactly one next phase: AG-79B targeted authority repair. AG-78G remains live-gated, and AG-76D-AD adapter cleanup should not preempt targeted repair because adapter debt did not block the review or safe repair planning.

AG-79A is docs/static-audit only. It does not change runtime behavior, prompts, provider/search/retrieval behavior, citation behavior, Author behavior, Scrutineer/remediation behavior, Economist behavior, DB/session/RunOutcome shape, cache behavior, live validation, or `core/pipeline_orchestrator.py`.

Recommended next phase: AG-79B — targeted authority repair for provider/search/depth/query selection and final assembly handoff boundaries.

## AG-78E — Author / Presentation for Inferred-vs-Direct Claims (2026-06-02)

Status: implemented/readiness for review. AG-78E adds `core/indirect_inference_author_presentation_handoff.py`, a narrow Author/final-answer presentation handoff that consumes already-activated AG-78D posture metadata and labels claim presentation as `directly_sourced`, `inferred_from_sourced_premises`, `speculative_or_unsupported`, `blocked_by_premise_conflict`, or `range_bound_or_source_bound`. The handoff preserves premise source IDs and bridge relationship source IDs while explicitly preventing citation laundering: premise/bridge sources support premises and bridge relationships, not direct source-statement of an inferred conclusion.

AG-78E is additive presentation labeling only. It does not change provider/model/search/query behavior, retrieval ranking/filtering, source-class/currentness semantics, AG-78B evaluator semantics, AG-78D posture activation semantics, AG-77 conflict arbitration behavior, DB/session/RunOutcome shape, cache behavior, Scrutineer/remediation, Economist/follow-up, broad pipeline orchestration, live validation, or inference-opportunity detection. `core/pipeline_orchestrator.py` remains untouched.

Recommended next phase: AG-78F — Indirect Inference Presentation Burn-Down / Dogfood Prep.


## AG-78D — Indirect Inference Answer Posture Activation (2026-06-01)

Status: complete/readiness for review. AG-78D activates bounded Controller / AnswerContract posture metadata from the already-visible AG-78C `indirect_inference_runtime_handoff` state. It preserves evaluator-authoritative AG-78B posture and recommendation while making direct, inferred, speculative/unsupported, conflict-blocked, range/source-bound, and lower-tier non-satisfaction effects visible to AnswerContract/controller traces.

AG-78D did not change final-answer prose, Author prompts, citation behavior, provider/search/query/retrieval behavior, source-class/currentness semantics, AG-77 conflict arbitration, Scrutineer/remediation, Economist/follow-up behavior, DB/session/RunOutcome shape, cache behavior, live validation, or inference-opportunity detection.

Recommended next phase: AG-78E — Author / Presentation for Inferred-vs-Direct Claims.

## AG-78B — Minimal Indirect Inference Contract with Fixture Tests (2026-06-01)

Status: implemented/readiness for review. AG-78B adds `core/indirect_inference_contract.py`, a minimal inert Controller-visible contract for representing direct target claims, inferred target claims from sourced premises, caveated/range-bound/blocked inference paths, unsupported claims, and speculative/model-assumed bridges. The contract carries target claim identity, premise/source identity, bridge type and strength, mode/depth policy, AG-77-derived premise conflict impact, source-bound numeric posture, lower-tier non-satisfaction posture, and JSON-safe Controller/trace serialization under `indirect_inference_contract`.

AG-78B is contract/fixture-test only. It does not execute runtime inference, change final-answer prose, alter Author prompts or Author exposure, change citation behavior, change provider/search/query/retrieval behavior, alter source-class/currentness semantics, change AG-77 conflict arbitration, affect Scrutineer/remediation, affect Economist/follow-up behavior, change DB/session/RunOutcome shape, implement cache behavior, or touch `core/pipeline_orchestrator.py`.

Recommended next phase: AG-78C — Runtime / AnswerContract Visibility for Indirect Inference.


## AG-78A — Controller-Owned Indirect Evidence / Inference Posture Design (2026-06-01)

Status: architecture design complete/readiness for review. AG-78A defines the Controller-owned design for indirect evidence / inference posture: direct evidence, conflict-arbitrated evidence, and inferred-from-sourced-premises answer-path families; a target-claim / sourced-premise / inference-bridge model; bridge-type taxonomy; Fast/Balanced/Deep inference-depth policy; confidence and posture inheritance; source-class/source-bound numeric handling; and AG-77 conflict interaction.

AG-78A is docs/design-only. It does not change runtime behavior, final-answer prose, Author prompts, Author exposure, citation behavior, prompt semantics, provider/search/query behavior, retrieval ranking/filtering, source-class/currentness detection semantics, conflict arbitration behavior, Scrutineer/remediation, Economist/follow-up, DB/session/RunOutcome shape, cache behavior, or `core/pipeline_orchestrator.py`.

Recommended next phase: AG-78B — Minimal Indirect Inference Contract with Fixture Tests. AG-78B should be an inert Controller-visible contract starting with Balanced one-hop inference from sourced premises through explicit valid bridges, if accepted in review.

## AG-77D — Conflict Arbitration Answer Posture Activation (2026-06-01)

Status: implemented/readiness for review. AG-77D activates already-visible AG-77C `source_conflict_arbitration` posture inside Controller / AnswerContract posture metadata through the additive `source_conflict_answer_posture_activation` trace fragment. The activation is limited to central unresolved official/current authoritative insufficiency, source-bound numeric unresolved values, and official/current vs secondary lower-tier non-satisfaction. Peripheral/background conflicts remain nonblocking/no-answer-impact posture metadata.

AG-77D does not change final-answer prose, Author prompts, Author evidence exposure, citation behavior, source ordering, prompt semantics, provider/search/query behavior, retrieval behavior, Scrutineer/remediation, Economist/follow-up, DB/session/RunOutcome shape, cache behavior, or AG-78 indirect inference behavior. `core/pipeline_orchestrator.py` remains untouched.

Recommended next phase: AG-78A — Controller-Owned Indirect Evidence / Inference Posture Design.

## AG-77C — Conflict Arbitration Runtime / AnswerContract Integration (2026-06-01)

Status: implemented/readiness for review. AG-77C is a protected-surface, no-prose-change integration that makes AG-77B source-conflict arbitration posture visible to Controller / AnswerContract runtime state and trace under the stable `source_conflict_arbitration` key. It consumes AG-77A `SourceConflictRepresentation` and AG-77B `SourceConflictArbitrationState` without changing final-answer prose, Author exposure, citation behavior, prompt semantics, provider/search/query behavior, retrieval behavior, Scrutineer/remediation, Economist/follow-up, DB/session/RunOutcome, cache behavior, or AG-78 inference behavior.

Historical AG-77C next-phase note: AG-77D was recommended after AG-77C because AG-77A representation, AG-77B arbitration, and AG-77C Controller / AnswerContract runtime visibility were present, while final-answer behavior remained intentionally inactive.

Status: Active repo-local handoff note for near-term Codex architecture phases.
Classification: docs-only; not an authorization for runtime behavior changes.

## Public Identity

The public project name is **ScryRaven**. The GitHub repository is
`aidan600/scryraven`, and the preferred local path is `C:\Users\aidan\ScryRaven`.

Earlier private or working names included ProPlex, FauxPlex, and FauxPlexity.
Historical docs may continue to use those names. The public CLI module is
`python -m scryraven`; `proplex`, `python -m proplex`, `PROPLEX_*`,
`proplex.db`, and `proplex_*` remain compatibility names unless a later hard
rename phase explicitly changes them.

## Recent Phase State


## AG-77B Controller-Owned Conflict Arbitration

AG-77B is complete as an architecture design with minimal pure contract
implementation. It adds `core/source_conflict_arbitration.py`, a passive
Controller-owned arbitration contract that consumes AG-77A
`SourceConflictRepresentation` objects and emits deterministic,
ledger-compatible arbitration posture without mutating AG-77A state.

The contract implements record/group/top-level arbitration dataclasses and enums
for dispositions, answer-posture recommendations, and arbitration reasons. It
handles equal official/current conflicts, official/current versus secondary
conflicts, current versus stale conflicts, jurisdiction/scope mismatches,
source-bound numeric conflicts, peripheral/background conflicts, empty/no-conflict
state, Controller/trace serialization, and static lane/protected-surface guards.

AG-77B remains inert. It does not change final-answer behavior, Author exposure,
citation behavior, prompt text, provider/model/search/query behavior, retrieval
ranking/filtering, source-class recovery, weak-corpus recovery, Scrutineer/
remediation, Economist/follow-up behavior, DB/session/`RunOutcome` shape, cache
behavior, AG-78 indirect inference, or `core/pipeline_orchestrator.py`.

AG-77C has completed runtime / AnswerContract visibility integration. Historical next-phase note: AG-77D was the follow-on activation phase.

## AG-77A Source Conflict Representation Model

AG-77A is complete as an architecture design with minimal inert contract
implementation. It adds a passive Controller-visible source-conflict
representation model in `core/source_conflict_model.py` and fixture/static tests
covering source identity preservation, source hierarchy preservation,
stale/current and effective-date tension, jurisdiction/scope mismatch,
source-bound numeric conflicts, Controller/ledger serialization, protected
surface import guards, lane distinction, no pipeline rewrite, and no
winner/arbitration helper exposure.

The model represents conflicts without choosing a winning source and does not
change final-answer behavior, citation behavior, prompts, provider/model/search/
query behavior, retrieval ranking/filtering, source-class recovery, weak-corpus
recovery, Scrutineer/remediation, Economist/follow-up behavior, DB/session/
`RunOutcome` shape, cache behavior, or `core/pipeline_orchestrator.py`.

AG-77B and AG-77C completed passive arbitration plus runtime / AnswerContract visibility before AG-77D activation.

## AG-76D-BD Controller Authority Transfer Burn-Down

AG-76D-BD is complete as a docs-only architecture review / burn-down ledger.
The main AG-76D normal-flow authority-transfer chain is complete enough to
pivot: retrieval stop/continue, Router/query-preparation posture, retrieval-loop
pass posture, weak/off-topic/failure-card gate posture, Analyst/Author handoff
posture, citation/source-list handoff identity, Economist handoff posture, and
follow-up initial state are represented by Controller-owned contracts/state.

Remaining hidden authority is concentrated in parked or specialized lanes, most
notably Scrutineer/remediation and synthesis-evaluator supplemental search.
Adapter debt in `core/pipeline_orchestrator.py` is real maintainability debt,
but it is behavior-preserving scaffolding rather than the next product-critical
state-modeling gap.

AG-77A has now completed the source-conflict representation pivot. AG-76D-SCR, AG-76D-AD, and AG-76C-LC remain parked unless later evidence changes that priority.

## AG-76D-FU Follow-up Initial State

AG-76D-FU is implemented as a production-active narrow authority transfer. It
adds `core.followup_initial_state_contract.FollowUpInitialControllerState` as
the Controller-owned source of truth for follow-up prior report/session refs,
prior evidence/source refs, prior ledger and AnswerContract/posture refs when
available, new follow-up intent, saved-context reuse decisions, refreshed source
obligations, stronger obligation detection, insufficiency/partiality carryover,
and additive trace visibility.

The follow-up runtime remains the mechanical executor. Saved report context can
still be reused for ordinary clarifications, but a new official/current/legal/
canonical/academic/source-bound quantitative obligation cannot silently inherit
sufficiency from prior context. The only intentional behavior change is the
narrow prompt/context initialization repair that carries this Controller-owned
posture into synthesis.

Historical next phase from AG-76D-FU was AG-76D-BD — Controller Authority
Transfer Burn-Down / Adapter Debt Review, which is now complete. Do not advance
AG-76C-LC beyond design-only cache work from this state note.

SCRY-00 is merged on `main`. It added manual CI `workflow_dispatch`, updated
first-contact labels, refreshed active Codex docs/templates for the public
ScryRaven identity, preserved `proplex` compatibility names, and made no
runtime behavior changes.

AG-70C split the current official/current validation state:

- SSA 2026 wage-base lifecycle succeeded. No immediate SSA repair is indicated.
- IRS 2026 business mileage-rate remains at accepted-readable official/current
  authority visibility / candidate fit. The answer correctly avoided
  overclaiming when final official/current IRS authority evidence was not
  visible.


## AG-76C-BD-R2 Durable Decision Surface

As of 2026-05-30, the current AG-76C durable decision surface is
`AG-76C-BD-R2 — Post-RT/OP/PE Burn-Down Refresh`. The completed post-burn-down
phases are `AG-76C-RT`, `AG-76C-RT-C`, `AG-76C-OP`, and `AG-76C-PE`. The repo no
longer selects those completed phases as the next extraction target.

Exactly one next concrete phase is selected: `AG-76C-KB-C — KB Review
Persistence Context Construction Extraction / Reduction`. Its scope is a
parity-preserving extraction or reduction of the inline
`KbReviewPersistenceContext(...)` construction at the tail of
`core/pipeline_orchestrator.py`. LLM workflow caching is recorded only as future
design work (`AG-76C-LC`) and is not implemented or licensed by BD-R2.

## Near-Term Roadmap

1. SCRY-01: keep repo-tracked current-state docs compact and aligned after the
   ScryRaven migration.
2. AG-71A: run a diagnostic IRS official/current acquisition and query strategy
   review.
3. AG-71B / AG-71C: only open conditional follow-up repair phases if AG-71A
   identifies a separately scoped repair surface.
4. SCRY-02: introduce public CLI/env aliases while preserving `proplex`
   compatibility surfaces.

AG-71A is diagnostic. It should classify where the IRS official/current
authority acquisition problem lives and should not repair behavior unless a
separate phase explicitly scopes the repair.

## Closed Surfaces for AG-71A

Unless separately licensed by the phase brief, AG-71A must not change or open:

- provider swaps or new provider integration;
- provider depth/search-depth changes;
- broad prompt rewrites;
- citation or final-answer behavior;
- Author posture repair;
- direct IRS hardcoding;
- broad `pipeline_orchestrator.py` domain logic;
- live calls;
- provider routing or provider selection;
- retrieval, ranking, or filtering behavior;
- controller lifecycle behavior.

Do not open broad citation survival, Author posture repair, provider swap, or
new provider integration merely because IRS lacked a final official/current
citation in AG-70C.

## AG-76D-RQ Router / Query-Preparation Authority Transfer

As of 2026-05-31, `AG-76D-RQ — Controller-Owned Router / Query Preparation
Contract` is complete. Router/query-preparation posture is now represented by
`RouterQueryPreparationState` in `core.router_query_preparation_contract`, and
`pipeline_orchestrator.py` consumes normalized Router/query-preparation facts
from that contract after handoff instead of remaining the sole owner of intent,
report type, query type, entity fallback/retry, routing override provenance,
retrieval budget seeds, recency merge posture, official-source bias posture, and
query text/order visibility.

Existing Router prompts, Researcher prompts, query generation, query
finalization, provider routing/depth, retrieval ranking/filtering,
AnswerContract behavior, Author/final-answer/citation behavior, DB/schema,
JSONL/session/SQLite payloads, and `RunOutcome` shape remain protected.

AG-76D-RL — Controller-Owned Retrieval Loop Contract is implemented on the
phase branch. Broader retrieval-loop pass posture is now represented by
`RetrievalLoopState`, `RetrievalPassDescriptor`, `RetrievalExecutionEnvelope`,
and `RetrievalPassResultSummary` in `core.retrieval_loop_contract`. The main
retrieval pass uses a mechanical handoff adapter that consumes the descriptor and
passes already-computed queries, provider list, depth, and budget facts to the
existing search executor without changing provider/search/query behavior.

Existing provider routing/selection/depth, query generation/finalization,
RetrievalStopDecision stop/continue ownership, RouterQueryPreparationState
router/query-preparation ownership, retrieval ranking/filtering, source-class
recovery, weak-corpus/failure-card behavior, Author/final-answer/citation
behavior, DB/session/RunOutcome shape, and compatibility names remain protected.

AG-76D-WG — Controller-Owned Weak / Off-topic / Failure-card Gate Contract is
implemented on the phase branch. Weak/off-topic/failure-card gate facts are now
represented by `WeakFailureGateState`, `AnalystGateDescriptor`,
`FailureCardGateDescriptor`, and `WeakFailureGateExecutionEnvelope` in
`core.weak_failure_gate_contract`. The orchestrator builds the Controller-owned
state from already-computed gate facts and then consumes a mechanical handoff,
while existing weak-corpus, off-topic, failure-card, useful-content,
answer-outcome, Analyst skip, Author/final-answer/citation, trace, DB/session,
and `RunOutcome` behavior remain protected.

AG-76D-AA — Controller-Owned Analyst / Author Handoff Contract is implemented
on the phase branch. Analyst/Author handoff posture is now represented by
`AnalystAuthorHandoffState`, `AnalystAdmissionDescriptor`,
`AnalystEvidenceContextDescriptor`, `UnsupportedDirectiveDescriptor`,
`AuthorEvidenceHandoffDescriptor`, `AuthorPromptInputDescriptor`, and
`AnalystAuthorExecutionEnvelope` in `core.analyst_author_handoff_contract`. The
orchestrator builds Controller-owned state from already-computed Analyst
admission, Analyst evidence/context identity, unsupported/weak/failure-card
directive posture, Author evidence handoff identity, Author prompt input
metadata, final evidence/source telemetry references, and upstream Controller /
AnswerContract posture, then consumes a mechanical handoff for already-computed
Author prompt-key/effort metadata.

Existing Analyst behavior, Author behavior, prompt text, final-answer prose,
citation/source-list behavior, provider/model/search/query behavior, retrieval
behavior, source-class/currentness/candidate-fit semantics, Economist,
Scrutineer, follow-up, DB/session/RunOutcome shape, cache behavior, and
compatibility names remain protected. Runtime behavior changes are expected to
be none except authority ownership and additive `analyst_author_handoff_contract`
trace/controller visibility.

AG-76D-CIT — Controller-Owned Citation / Source-list Handoff Contract is
implemented on the phase branch. Citation/source-list handoff posture is now
represented by `CitationSourceHandoffState`, `SourceIdentityDescriptor`,
`OrderedSourceListDescriptor`, `CitationEligibilityDescriptor`,
`CitationObservationDescriptor`, `AuthorSourceInputDescriptor`, and
`CitationSourceExecutionEnvelope` in `core.citation_source_handoff_contract`.
The orchestrator builds Controller-owned state from already-computed final
evidence, source IDs, duplicate URL reuse, ordered source lines, evidence block,
cached prefix, Author evidence block, final citation observations, final
evidence bundle refs, ControllerEvidenceLedger-compatible refs, AnswerContract
runtime refs, and `AnalystAuthorHandoffState` refs, then consumes a mechanical
handoff for legacy-compatible source/citation values.

Existing source-ID assignment, source-ID reuse/deduping, source ordering,
citation formatting/selection, Author prompt text, final-answer prose, final
evidence selection, provider/model/search/query behavior, DB/session/RunOutcome
shape, cache behavior, and compatibility names remain protected. Runtime
behavior changes are expected to be none except authority ownership and additive
`citation_source_handoff_contract` trace/controller visibility.

AG-76D-ECO — Controller-Owned Economist Handoff Contract is implemented on the
phase branch. Economist handoff posture is now represented by
`EconomistHandoffState`, `EconomistAdmissionDescriptor`,
`EconomistPreflightDescriptor`, `SourceBoundQuantitativePacketDescriptor`,
`UnsupportedQuantitativeValueDescriptor`, `EconomistOutputDescriptor`,
`EconomistAnalystExposureDescriptor`, `EconomistAuthorExposureDescriptor`,
`EconomistSafetyDescriptor`, and `EconomistExecutionEnvelope` in
`core.economist_handoff_contract`. The orchestrator builds Controller-owned
state from already-computed Economist admission/run/block/unavailable facts,
preflight posture, source-bound quantitative packet identity, unsupported /
missing / model-derived value posture, Economist output identity,
Analyst/Author exposure facts, AnswerContract refs, `AnalystAuthorHandoffState`
refs, and `CitationSourceHandoffState` refs, then consumes a mechanical handoff
for legacy-compatible Economist handoff values.

Existing Economist prompt text, Economist behavior, quantitative policy,
source-bound numeric policy, model-generated code-execution blocking,
Analyst/Author/final-answer/citation behavior, provider/model/search/query
behavior, DB/session/RunOutcome shape, cache behavior, and compatibility names
remain protected. Runtime behavior changes are expected to be none except
authority ownership and additive `economist_handoff_contract` trace/controller
visibility.

Exactly one next AG-76D phase is recommended: `AG-76D-FU — Follow-up as
Controller Initial State`, because follow-up state remains a coherent
Controller-initial-state seam after the retrieval, Router/query-preparation,
weak/failure gate, Analyst/Author, citation/source-list, and Economist handoff
transfers.

AG-78C — Runtime / AnswerContract Visibility for Indirect Inference is
merged. AG-78C adds a visibility-only `indirect_inference_runtime_handoff`
state/trace layer for already-built AG-78B `InferencePath` objects, preserving
evaluator-authoritative posture and recommendation while exposing direct,
inferred, speculative, AG-77-conflicted, source-bound numeric, and lower-tier
non-satisfaction markers to Controller / AnswerContract consumers.

AG-78D — Indirect Inference Runtime Behavior Activation / Answer Posture Effects
is merged. AG-78D adds bounded
`indirect_inference_answer_posture_activation` metadata from already-visible
AG-78C handoff state for directly sourced, inferred-from-sourced-premises,
speculative/unsupported, blocked-by-premise-conflict, range/source-bound, and
lower-tier-non-satisfying inference paths. Inferred conclusions are marked
`directly_sourced=false` and `requires_inference_label=true` for presentation
phases.

AG-78E — Author / Presentation for Inferred-vs-Direct Claims is merged. AG-78E
adds `indirect_inference_author_presentation_handoff` trace/controller visibility
for direct, inferred, speculative/unsupported, blocked-by-premise-conflict,
range/source-bound, and lower-tier non-satisfaction presentation labels while
preserving citation-laundering boundaries. AG-78D and AG-78E do not change final
answer prose, provider/model/search/query behavior, retrieval behavior,
DB/session/RunOutcome shape, cache behavior, actual inference execution, or broad
pipeline orchestration. `core/pipeline_orchestrator.py` remains outside these phases.

## AG-78F Indirect Inference Presentation Burn-Down / Dogfood Prep

AG-78F is complete as a documentation-only burn-down review. It classifies the
merged AG-78A/B/B-R1/C/D/E indirect-inference stack as ready for later bounded
dogfood, with no runtime product behavior change and no live validation.

The current direct-vs-inferred presentation contract is considered safe enough
for dogfood: `directly_sourced` remains separate from
`inferred_from_sourced_premises`; inferred conclusions require an inference
label; premise and bridge sources remain auditable without being treated as
direct conclusion support; range/source-bound numeric cases preserve unresolved
scalar posture; speculative/unsupported, premise-conflict-blocked, and
lower-tier non-satisfying paths remain prevented from becoming supported
inference.

Trace ergonomics debt remains non-blocking. The handoff sequence is still
understandable as `indirect_inference_contract` →
`indirect_inference_runtime_handoff` →
`indirect_inference_answer_posture_activation` →
`indirect_inference_author_presentation_handoff`. If that layering becomes a
review blocker after dogfood, route to AG-76D-AD adapter debt rather than an
inference behavior phase.

Recommended next phase: `AG-78G — Bounded Indirect-Inference Dogfood`. AG-78G
should run at most six packet-only query classes, with one infrastructure
replacement allowed for a hard cap of seven total ScryRaven/proplex/scryraven
runs; it must not expand provider/model/search/retrieval budgets; it should emit
redacted packets under `output/ag78g_bounded_indirect_inference_dogfood/`; and
it should decide only whether the AG-78 trace/presentation packets preserve
labels, attribution boundaries, numeric posture, and no-promotion guards.

AG-76D-SCR-R1 status: complete/readiness for review. Runtime wiring now packages already-computed legacy Scrutineer/remediation facts through `core/scrutineer_remediation_runtime_handoff.py` and attaches JSON-safe trace state under `scrutineer_remediation_handoff` from `core/pipeline_orchestrator.py`. This is behavior-preserving wiring only: Scrutineer prompts, remediation query generation, novelty filtering, provider/depth selection, retrieval, Analyst re-synthesis, Author prose/directives, citation behavior, DB/session/RunOutcome shape, cache behavior, and live validation remain closed. AG-78G remains live-gated and synthesis-evaluator supplemental search is now covered by AG-76D-SES at passive contract depth.

AG-76D-SES-R1 status: complete/readiness for review. Runtime wiring now packages already-computed legacy synthesis-evaluator supplemental-search facts through `core/synthesis_evaluator_supplemental_search_runtime_handoff.py` and attaches JSON-safe trace state under `synthesis_evaluator_supplemental_search_handoff` from `core/pipeline_orchestrator.py`. This is behavior-preserving wiring only: synthesis-evaluator prompts/model behavior, completeness-evaluator behavior, supplemental query generation, provider/search/depth policy, retrieval/ranking/filtering, final evidence rebuild, Analyst re-run, Author note/prose behavior, citation behavior, Scrutineer/remediation behavior, DB/session/RunOutcome shape, cache behavior, and live validation remain closed. AG-78G remains live-gated. Recommended next phase: AG-79D, or another explicitly licensed passive handoff/runtime-consumption phase.
