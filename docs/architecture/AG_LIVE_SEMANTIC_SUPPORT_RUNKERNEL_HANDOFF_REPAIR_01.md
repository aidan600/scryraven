# AG-LIVE-SEMANTIC-SUPPORT-RUNKERNEL-HANDOFF-REPAIR-01

Status: historical predecessor repair record; direct public transport retired,
offline injected-fixture regression only.

Mode: REPAIR.

Repair verdict target: YES.

Current execution class: VALIDATION. This record preserves the predecessor
in-process handoff proof; it does not license another public fetch/read or make
that proof current production exact-URL or semantic activation.

## Named Defect

PR #360 repaired answer-bearing bounded content selection and moved the live
semantic-support replay from:

```text
semantic_support_fail_source_content_insufficient
gate_5_evidence_relative_analysis_proposal
```

to:

```text
semantic_support_fail_semantic_observation_admission
gate_6_semantic_observation_admission
```

The remaining defect is a RunKernel state/consumer seam. The standalone #359
CLI can load safe packets and projections, but serialized packets/projections are insufficient
as RunKernel state. They cannot prove the accepted contract,
EvidenceLedger custody, SemanticObservation admission, or ComponentCoverage
authorization state needed by the existing bridge and reducer.

## Repair

The repair replays from the earliest available stateful current-path boundary:

```text
#357 sanitized provider results
-> #357 ordinary-query front half in process
-> RunKernel live_search_validation reduction
-> SearchResultCandidatePacket while preserving the real RunKernel
-> #360 repaired fetch/read bounded-content selector
-> EvidenceLedger custody on the same RunKernel
-> EvidenceRelativeAnalysisPacket
-> SemanticObservation admission bridge
-> RunKernel ComponentCoverage reducer
```

The handoff objects carry a real `RunKernel` in memory only. They are not JSON
serialized, not written to output packets, and not a projection-to-state
rehydration path. The old packet/projection-only #359 CLI path remains
fail-closed at gate 6 when `run_kernel=None`.

## Opened Surfaces

- RunKernel in-process replay/handoff for an injected predecessor
  candidate/source-survival fixture to the semantic-support boundary.
- #357 current-path candidate acquisition replay from existing sanitized
  provider results only.
- #360 repaired bounded fetch/read fixture selection.
- Offline SemanticObservation admission through the existing bridge.
- Offline ComponentCoverage reduction through existing RunKernel
  authorization/reducer.
- Small harness/script/tests/docs needed to validate this seam.

## Closed Surfaces

- provider/search/broker calls: 0
- model calls: 0
- broad retrieval
- ranking/filtering of search candidates
- prompt behavior
- raw HTML/raw headers/raw cookies/raw page text retention
- projection-to-RunKernel rehydration
- direct RunKernel state mutation
- source-obligation satisfaction
- citation eligibility/rendering
- SufficiencyReadiness
- FinalAnswerPacket
- Author/AuthorProse
- answer text
- product correctness claims

## Retired Live Budget

The following was the predecessor live posture. It is no longer licensed. The
direct opener is now a typed fail-closed tombstone; current public URL
fetch/read calls are `0`, while one explicitly injected sanitized fixture may
exercise the downstream handoff.

- provider/search/broker calls: 0
- model calls: 0
- historical URL fetch/read calls: max 1
- public URL fetch/read calls: 0
- injected fixture executions: max 1
- selected URL: `https://travel.state.gov/en/passports/apply/help/fees.html`
- allowed final host: `travel.state.gov`
- max fetched bytes: 1 MB
- raw HTML retained: false
- raw headers/cookies retained: false
- retries: 0
- SemanticObservation admissions: max 1
- ComponentCoverage reductions: max 1
- citation/source-obligation/Sufficiency/FAP/Author counts: 0

## Historical Outcomes

Pass:

```text
runkernel_handoff_repair_pass
```

At the predecessor checkpoint, the replay preserved a real RunKernel from #357
sanitized-provider-result reduction through EvidenceLedger custody, admitted
exactly one SemanticObservation through the existing bridge, and reduced exactly one
ComponentCoverage record through RunKernel. Current offline fixtures may guard
those mechanics only; they do not establish current production acquisition or
semantic admission.

Acceptable partial:

```text
runkernel_handoff_repair_partial
runkernel_handoff_repair_fail_semantic_observation_admission
runkernel_handoff_repair_fail_component_coverage
```

These outcomes must report the first failed gate and must not bypass admission,
rehydrate projections, mutate RunKernel state, or loosen semantic support.

Fail:

```text
runkernel_handoff_repair_fail_candidate_replay
runkernel_handoff_repair_fail_source_survival
runkernel_handoff_repair_fail_analysis_packet
validation_not_run_operator_blocked
validation_inconclusive
```

## Explicit Non-Proofs

- no current public fetch/read, DNS, redirect, final-target, or connected-peer
  proof
- no production provider-operation target-safety eligibility
- no current READ, Focused Extract, final custody, or semantic activation
- no final answer text
- no answer correctness or product correctness
- no source-obligation satisfaction
- no citation eligibility or citation rendering
- no SufficiencyReadiness
- no FinalAnswerPacket
- no Author or AuthorProse behavior
- no provider/search/broker/model behavior
- no product-quality prose

## Current Supersession

The historical next checkpoint was:

```text
AG-LIVE-SUFFICIENCY-FAP-AUTHORPROSE-01
```

That sequencing is superseded. The canonical target-safety repair retired the
local opener, and production untrusted exact-URL routing remains blocked because
no Linkup/Tavily operation has sufficient committed public-target guarantees or
observable final-target lineage to be truthfully eligible. This is not an
inherent-unsafety claim. Offline fixtures may retain in-process handoff
regression coverage only; they do not reactivate READ, Focused Extract, custody,
semantic admission, citation eligibility, source-obligation satisfaction,
Sufficiency, FAP, or Author.
