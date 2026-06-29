# AG-DOC-SEMANTIC-COVERAGE-CHECKPOINT-01

## Status

Status: docs/source checkpoint for the post-Pro-review semantic coverage
doctrine after PR #342 / `AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01`.

Baseline: `main@c46ed06` (`c46ed0617bfd3b449ca43d1634c13b3b52b2a8fe`).

Proof class: `docs_source_checkpoint`.

Product path affected: none. This checkpoint changes repo documentation and one
docs-posture assertion only. It does not edit product code, create runtime
packets, create reducers, run live providers, call the broker, run retrieval,
call models, execute Author, create a FinalAnswerPacket, or create Author input.

The immediate next implementation gate is
`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`.

## Recent Merged Phases

The current semantic-coverage baseline includes these merged phases:

1. PR #337 / `AG-SEARCH-RESULT-CANDIDATE-PACKET-01`: added
   `SearchResultCandidatePacket` as non-evidence discovery lineage.
2. PR #338 / `AG-FETCH-READ-CONTENT-REFERENCE-01`: added
   `FetchReadContentPacket` / `SanitizedContentReference` as bounded readable
   content identity.
3. PR #339 / `AG-EVIDENCE-LEDGER-CANDIDATE-CUSTODY-01`: added EvidenceLedger
   candidate/content custody from fetch/read packet lineage.
4. PR #340 / `AG-ANALYST-EVIDENCE-RELATIVE-REPORT-01`: added
   `EvidenceRelativeAnalysisPacket` / embedded `analyst_report` as proposal-only
   evidence-relative meaning.
5. PR #341 / `AG-ANALYSIS-GAP-FOLLOWUP-SEARCH-01`: added
   `FollowupSearchIntentPacket` / `AnalysisGapSearchProposal` as proposal-only
   follow-up search intent.
6. PR #342 / `AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01`: proved that
   ComponentCoverage can reduce meaningful support only after
   SemanticObservation admission exists.

## Current Semantic Chain

```text
SearchExecutorHandoff
-> SearchResultCandidatePacket
-> FetchReadContentPacket / SanitizedContentReference
-> EvidenceLedger candidate/content custody
-> EvidenceRelativeAnalysisPacket / analyst_report
-> FollowupSearchIntentPacket / AnalysisGapSearchProposal
-> ComponentCoverage reliability proof
-> next: SemanticObservation admission bridge
-> ComponentCoverage reduction
```

The chain is useful, but it is not yet admitted semantic support. The current
packet chain alone does not let ComponentCoverage consume meaningful support.

Semantic posture progression:

```text
lineage
-> custody
-> proposal
-> admitted meaning
-> coverage
-> readiness
-> FAP-safe material
-> prose
```

Every semantic stage must preserve component lineage and source-obligation
lineage from the accepted answer contract through coverage, readiness,
FinalAnswerPacket material, and Author-safe prose.

## Doctrine To Preserve

1. `SearchResultCandidatePacket` is non-evidence discovery lineage.
2. `FetchReadContentPacket` / `SanitizedContentReference` is bounded
   readable-content identity, not semantic support.
3. EvidenceLedger candidate/content custody is custody, not component
   satisfaction.
4. `EvidenceRelativeAnalysisPacket` / `analyst_report` is proposal-only
   evidence-relative meaning.
5. `FollowupSearchIntentPacket` is proposal-only follow-up search intent, not
   search authorization or query planning.
6. PR #342 showed that the current chain needs admitted `SemanticObservation`
   before ComponentCoverage can consume support.
7. The next phase should bridge Analyst support findings into
   `SemanticObservation` admission and immediately prove ComponentCoverage
   consumption.
8. The next bridge must not create another durable proposal packet unless a
   reducer/consumer absolutely requires it and the phase stops for review.
9. Broker is local/private validation plumbing for Codex/ChatGPT/operator runs,
   not installed-product authority and not product follow-up policy.
10. Modes change budget and review depth, not semantic authority.
11. Fast has no Scrutineer in MVP.
12. Balanced uses Scrutineer only on red flags.
13. Deep requires Scrutineer and post-Scrutineer response budget.
14. Deep allows max 3 follow-up loops by default and max 4 only with explicit
   RunKernel extra recovery authorization.
15. Follow-up limits are ceilings, not targets.
16. Follow-up policy is based on logical depth, loop budget, query fanout, and
   RunKernel approval, not one-query-per-proposal.
17. Specialist MVP is deferred and should start as source-bound
   calculation/economist-style reasoning only, not broad legal or technical
   interpretation.
18. The AG-96 followup stack, offline SearchExecutor bridge, SearchWorkPlan
   shadow, old Analyst/Economist/Scrutineer paths, source-class recovery
   bridges, and broad pipeline orchestrator paths are legacy/passive/closed
   unless explicitly reopened.
19. Partial answer readiness remains premature until ComponentCoverage,
   Sufficiency, FAP, and Author-safe prerequisites are coherent.
20. Component and source-obligation lineage must survive every promotion from
   accepted answer contract through Author-safe material.

## Packet And Bridge Budget Rule

A new packet or bridge is justified only when it:

- crosses a trust/raw-data boundary;
- becomes durable reducer input;
- needs stable downstream IDs/digests consumed by more than one stage;
- records canonical or reducer-admitted state;
- prevents raw/private/provider material from leaking forward;
- or removes a named blocker for an existing consumer.

A new packet or bridge is suspect when it:

- restates lineage already present upstream;
- exists only to say closed flags remain false;
- is consumed only by its own tests;
- creates another proposal layer without reduction;
- has no immediate consumer in the same or next phase.

For `AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`, the bridge is justified only
if it proves this immediate consumer path:

```text
EvidenceRelativeAnalysisPacket support finding
-> RunKernel-authorized SemanticObservation admission
-> ComponentCoverage reduction
```

It is not justified if it proves only:

```text
EvidenceRelativeAnalysisPacket support finding
-> new packet
-> future consumer later
```

## What PR #342 Proved

The `component_coverage_reliability_report` fixture proof showed:

- the current packet chain constructs cleanly through validators without live
  provider/search/fetch/read/retrieval/model execution;
- candidate lineage, bounded readable content identity, EvidenceLedger custody,
  Analyst proposal meaning, and FollowupSearchIntent proposals are all upstream
  of canonical ComponentCoverage support;
- ComponentCoverage reduction rejects support until at least one admitted
  `SemanticObservation` exists;
- search candidate, fetch/read, ledger custody, and Analyst proposal fields are
  not enough to claim satisfied coverage;
- blocked/follow-up-required posture is visible in Analyst gap and
  FollowupSearchIntent records, but stable gap-to-ComponentCoverage blocker
  lineage is still incomplete.

The missing bridge is therefore not "one more proposal." The missing bridge is
controlled promotion from proposal-stage support into admitted semantic meaning,
with ComponentCoverage consuming that admitted meaning immediately.

## Next Implementation Gate

`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` should be a minimal consumer bridge.

Required proof shape:

- consume `EvidenceRelativeAnalysisPacket` support findings and their
  EvidenceLedger/fetch-read custody bindings;
- require RunKernel authorization before any `SemanticObservation` is admitted;
- preserve accepted answer contract component lineage;
- preserve source-obligation and custody lineage;
- reduce ComponentCoverage from admitted `SemanticObservation` and bound content;
- keep FollowupSearchIntent proposal-only and non-authorizing;
- keep blocked/follow-up gap lineage visible, with stable blocker linkage only
  if it can be solved without packet sprawl;
- prove no FAP, Author input, Author call, Sufficiency decision, live provider
  behavior, broker call, retrieval, model call, or product correctness claim.

Stop conditions for that phase:

- a new durable packet looks necessary before a reducer/consumer can consume it;
- product code outside the licensed bridge/reducer path is required;
- live validation, broker, retrieval, provider, model, secrets, private logs,
  raw payloads, raw prompts, DB/cache rows, traces, or output packets are needed;
- ComponentCoverage cannot consume the admitted observation in the same phase.

## Mode Policy Snapshot

Modes change budget and review depth, not semantic authority. RunKernel remains
the authorization/reduction owner across Fast, Balanced, and Deep.

- Fast has no Scrutineer in MVP.
- Balanced uses Scrutineer only on red flags.
- Deep requires Scrutineer and post-Scrutineer response budget.
- Deep allows max 3 follow-up loops by default.
- Deep allows max 4 follow-up loops only with explicit RunKernel extra recovery
  authorization.
- Follow-up loop limits are ceilings, not targets.
- Query fanout inside an authorized proposal group is allowed.
- Logical depth matters more than raw query count.

## Broker Clarification

Broker is local/private validation plumbing for Codex/ChatGPT/operator runs.
Installed product architecture should not depend on broker as authority.

- ScryRaven / RunKernel owns authorization and policy.
- The broker owns credential isolation and sanitized I/O only.
- The broker must not own phase policy, query policy, citation policy,
  ComponentCoverage, Sufficiency, FAP, Author, or answer policy.
- Broker output remains sanitized candidate/provider output unless a separate
  licensed phase maps it through a RunKernel-owned reducer.

## Specialist And Scrutineer Placement

Scrutineer is review depth, not semantic authority. It is absent from Fast MVP,
red-flag-triggered in Balanced, and required in Deep with preserved
post-Scrutineer response budget.

Specialist MVP is deferred. When it starts, it should begin as
source-bound calculation/economist-style reasoning only. It should not begin as
broad legal, technical, policy, or interpretive authority.

The next bridge comes before Scrutineer or Specialist because ComponentCoverage
already exists as the immediate consumer and currently lacks admitted meaning to
consume.

## Legacy Demotions

These surfaces are legacy/passive/closed unless a later phase explicitly
reopens them:

- AG-96 followup stack;
- offline SearchExecutor bridge;
- SearchWorkPlan shadow;
- old Analyst/Economist/Scrutineer paths;
- source-class recovery bridges;
- broad pipeline orchestrator paths.

Partial answer readiness remains premature until ComponentCoverage,
Sufficiency, FAP, and Author-safe prerequisites are coherent.

## Project Source Refresh Recommendations

The ChatGPT Project Sources are not assumed to be repo files. This section is a
copy-pasteable refresh packet for external Project Source maintenance, not a
claim that any external source was updated.

### Source: `02_ARCHITECTURE_AUTHORITY`

Update purpose: record current authority ownership from proposal through prose.

Exact bullet points to add/replace:

- RunKernel owns authorization/reduction.
- Semantic producer/planner may propose, not canonically satisfy.
- Analyst/Specialist/Scrutineer produce proposal-stage meaning/review.
- `SemanticObservation` admission is the controlled promotion from proposal to
  admitted meaning.
- ComponentCoverage consumes admitted meaning and evidence/custody bindings.
- Sufficiency decides readiness.
- FAP packages Author-safe material.
- Author writes prose only from FAP-safe material.
- Broker is not product authority.

Stale language to remove or demote:

- any wording that treats Analyst possible-support as canonical support;
- any wording that treats custody, source-obligation candidate IDs, or search
  candidates as component satisfaction;
- any wording that makes broker, provider snippets, or project-source text a
  product authority surface.

Next-phase implication:

- `AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` must prove
  RunKernel-authorized admission and ComponentCoverage consumption in the same
  bridge.

### Source: `03_MODE_SEMANTIC_COVERAGE`

Update purpose: align mode doctrine with semantic authority and review depth.

Exact bullet points to add/replace:

- Modes change budget and review depth, not semantic authority.
- Fast has no Scrutineer in MVP.
- Balanced uses Scrutineer on red flags.
- Deep requires Scrutineer.
- Deep has max 3 follow-up loops by default, max 4 only with explicit RunKernel
  extra recovery authorization.
- Follow-up loop limits are ceilings, not targets.
- Query fanout inside an authorized proposal group is allowed.
- Logical depth matters more than raw query count.

Stale language to remove or demote:

- one-query-per-proposal as a durable follow-up policy;
- any implication that mode policy can bypass RunKernel semantic admission;
- any wording that puts Scrutineer before the SemanticObservation admission
  bridge as the immediate next gate.

Next-phase implication:

- The admission bridge should not encode mode-specific semantic authority.
  Modes may influence budgets/review depth around the bridge later.

### Source: `05_PRODUCTIZATION_ROADMAP`

Update purpose: replace the pre-#342 roadmap with the current semantic-coverage
sequence.

Exact bullet points to add/replace:

- Completed through `AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01`.
- Next implementation is `AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`.
- Then Scrutineer MVP.
- Then source-bound calculation Specialist MVP.
- Then Sufficiency / partial-answer readiness.
- Then FAP hardening.
- Then Author prose-only finalization.
- The SemanticObservation bridge is a conditional consumer bridge, not packet
  sprawl.

Stale language to remove or demote:

- Specialist is next before SemanticObservation admission;
- Scrutineer is next before the admission bridge;
- partial-answer readiness is next now;
- old AG-96 follow-up stack, SearchWorkPlan shadow, offline SearchExecutor
  bridge, source-class recovery bridges, or broad pipeline orchestrator paths
  as current roadmap authority.

Next-phase implication:

- The next PR should be narrow: Analyst support finding -> admitted
  `SemanticObservation` -> ComponentCoverage reduction.

### Source: `08_RUN_CONTRACT_SEMANTIC_LOOP`

Update purpose: make semantic coverage continuous from contract to prose and
name the missing bridge.

Exact bullet points to add/replace:

- Semantic coverage must remain continuous from accepted answer contract through
  candidate/read/custody/analysis/admission/coverage/readiness/FAP/Author.
- Every stage must preserve component lineage and source-obligation lineage.
- Current known missing bridge is Analyst support finding ->
  `SemanticObservation` admission -> ComponentCoverage.
- Blocked/follow-up gap lineage to ComponentCoverage blocker state is also
  still incomplete and should be handled after or within the minimal bridge if
  safe.
- No new durable packet should be added to solve this unless a reducer/consumer
  absolutely requires it and implementation stops for review.

Stale language to remove or demote:

- `FollowupSearchIntentPacket` authorizes search;
- custody is coverage;
- candidate IDs or source-obligation candidate IDs are satisfaction;
- ComponentCoverage reliability proof is still the next gate.

Next-phase implication:

- The next bridge must demonstrate immediate ComponentCoverage consumption, not
  just a new representation for future use.

### Source: Broker / Local Validation Doctrine

Update purpose: clarify broker scope only where a source currently discusses
brokered validation.

Exact bullet points to add/replace:

- Broker is local/private validation plumbing for Codex/ChatGPT/operator runs.
- Installed product architecture should not depend on broker as authority.
- ScryRaven / RunKernel owns authorization and policy.
- Broker owns credential isolation and sanitized I/O only.
- Broker must not own phase policy, query policy, citation policy,
  ComponentCoverage, Sufficiency, FAP, Author, or answer policy.

Stale language to remove or demote:

- broker as product authority;
- broker as validation-profile governor;
- broker as query policy or answer policy;
- broker as citation, Sufficiency, FAP, Author, or ComponentCoverage owner.

Next-phase implication:

- `AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` should stay offline unless a
  later prompt separately licenses live validation.

## Explicit Non-Proofs

This checkpoint does not prove:

- product correctness;
- final answer correctness;
- citation eligibility;
- source-obligation satisfaction;
- Sufficiency readiness;
- partial answer readiness;
- FinalAnswerPacket creation;
- Author input creation;
- Author execution;
- live provider, broker, retrieval, fetch/read, or model behavior.

Required downstream false posture remains:

```text
sufficiency_decided: false
final_answer_packet_created: false
author_input_created: false
author_called: false
product_correctness_claimed: false
search_authorized_from_followup_intent: false
```
