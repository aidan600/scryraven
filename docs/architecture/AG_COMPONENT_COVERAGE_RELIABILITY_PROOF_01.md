# AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01

Status: phase-focus fixture proof and near-surface doctrine refresh.

Proof class: `component_harness_proof`.

Product path affected: none. This phase uses offline fixtures and existing
validators/reducers only. It does not change ordinary `run_pipeline()` behavior,
does not run live providers, does not call the broker, does not run retrieval,
does not execute fetch/read, does not call models, does not create a
FinalAnswerPacket, and does not create Author input.

## Result

Current next gate is ComponentCoverage reliability proof, not another standalone
proposal packet. The current chain through `FollowupSearchIntentPacket` is useful
but must prove consumption before another layer is added:

```text
SearchExecutorHandoff
-> SearchResultCandidatePacket
-> FetchReadContentPacket / SanitizedContentReference
-> EvidenceLedger candidate/content custody
-> EvidenceRelativeAnalysisPacket / analyst_report
-> FollowupSearchIntentPacket / AnalysisGapSearchProposal
-> ComponentCoverage reliability proof
```

The fixture proof uses a compact `component_coverage_reliability_report` artifact.
It shows that a supportable ComponentCoverage posture can be reduced only after a
fixture-only `SemanticObservation/admission bridge` is supplied. The packet chain
by itself does not admit semantic support. It also shows that a blocked or
follow-up-required posture is visible in Analyst gap and FollowupSearchIntent
records, but there is not yet stable gap-to-ComponentCoverage blocker lineage.

Recommended next phase: if product work continues on this lane, add a minimal
`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` before Scrutineer or Specialist.

## Packet Budget Rule

The packet budget rule: no new packet unless it crosses a trust/raw-data
boundary, becomes durable reducer input, needs stable downstream IDs/digests,
records canonical state, or prevents raw/private leakage.

A packet is suspect if it only restates lineage, only says closed flags remain
false, is only consumed by its own tests, or creates another proposal layer
without reduction.

This phase must not create a product packet named `ReadinessPacket`,
`CoverageProofPacket`, or similar. The fixture report is a test/proof artifact,
not product state.

## Broker, Modes, And Follow-Up

Broker is local/private validation plumbing, not installed-product authority and
not product follow-up policy. It must not decide evidence, coverage, Sufficiency,
FAP, Author, or query dispatch.

Modes change budget and review depth, not authority. Follow-up policy should be
based on logical depth, loop budget, RunKernel approval, and query fanout, not
one-query-per-proposal.

- Fast has no Scrutineer in MVP.
- Balanced uses Scrutineer on red flags.
- Deep requires Scrutineer and reserve post-Scrutineer response budget.
- Deep allows max 3 follow-up loops by default.
- Deep allows max 4 only with explicit RunKernel extra recovery authorization.

Specialist MVP is deferred and should start as source-bound
calculation/economist-style reasoning, not broad legal or technical
interpretation.

## Legacy Demotions

The AG-96 followup stack, offline SearchExecutor bridge, SearchWorkPlan shadow,
old Analyst/Economist/Scrutineer paths, source-class recovery bridges, and broad
pipeline orchestrator paths are legacy/passive/closed unless a later phase
explicitly reopens them.

The current FollowupSearchIntent posture is proposal-only. It is not search
authorization, not a query plan, not SearchExecutorHandoff, not evidence, not
ComponentCoverage, and not Sufficiency/FAP/Author readiness.

## Non-Proofs

This phase explicitly does not prove:

- final answer correctness;
- citation eligibility;
- source-obligation satisfaction;
- Sufficiency readiness;
- FinalAnswerPacket creation;
- Author input creation;
- Author execution;
- live provider, broker, retrieval, live fetch/read, or model behavior.

Required downstream false posture remains:

```text
final_answer_packet_created: false
author_input_created: false
author_called: false
product_correctness_claimed: false
```
