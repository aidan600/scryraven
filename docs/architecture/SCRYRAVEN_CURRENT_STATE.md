# ScryRaven Current State



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
is implemented and ready for review on the phase branch. AG-78D adds bounded
`indirect_inference_answer_posture_activation` metadata from already-visible
AG-78C handoff state for directly sourced, inferred-from-sourced-premises,
speculative/unsupported, blocked-by-premise-conflict, range/source-bound, and
lower-tier-non-satisfying inference paths. Inferred conclusions are marked
`directly_sourced=false` and `requires_inference_label=true` for future
presentation phases.

AG-78D does not change final-answer prose, Author prompt/exposure/evidence
handoff, citation behavior, provider/model/search/query behavior, retrieval
behavior, DB/session/RunOutcome shape, cache behavior, actual inference
execution, or final inferred-answer presentation. `core/pipeline_orchestrator.py`
remains outside this phase. Recommended next phase: `AG-78E — Final Inferred
Answer Presentation Policy` only after product approval for prose labeling; use
`AG-78D-R1` only if the activation metadata contract needs review adjustment, or
`AG-77E` if conflict presentation should precede inference presentation.
