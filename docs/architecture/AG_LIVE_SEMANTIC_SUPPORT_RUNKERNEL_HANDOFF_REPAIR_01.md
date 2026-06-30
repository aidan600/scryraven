# AG-LIVE-SEMANTIC-SUPPORT-RUNKERNEL-HANDOFF-REPAIR-01

Status: active product-path repair phase.

Mode: REPAIR.

Repair verdict target: YES.

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

- RunKernel in-process replay/handoff for the live candidate/source-survival to
  semantic-support boundary.
- #357 current-path candidate acquisition replay from existing sanitized
  provider results only.
- #360 repaired bounded fetch/read content selection.
- SemanticObservation admission through the existing bridge.
- ComponentCoverage reduction through existing RunKernel authorization/reducer.
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

## Live Budget

- provider/search/broker calls: 0
- model calls: 0
- URL fetch/read calls: max 1
- selected URL: `https://travel.state.gov/en/passports/apply/help/fees.html`
- allowed final host: `travel.state.gov`
- max fetched bytes: 1 MB
- raw HTML retained: false
- raw headers/cookies retained: false
- retries: 0
- SemanticObservation admissions: max 1
- ComponentCoverage reductions: max 1
- citation/source-obligation/Sufficiency/FAP/Author counts: 0

## Outcomes

Pass:

```text
runkernel_handoff_repair_pass
```

The replay preserved a real RunKernel from #357 sanitized-provider-result
reduction through EvidenceLedger custody, admitted exactly one
SemanticObservation through the existing bridge, and reduced exactly one
ComponentCoverage record through RunKernel.

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

- no final answer text
- no answer correctness or product correctness
- no source-obligation satisfaction
- no citation eligibility or citation rendering
- no SufficiencyReadiness
- no FinalAnswerPacket
- no Author or AuthorProse behavior
- no provider/search/broker/model behavior
- no product-quality prose

## Mandatory Next Checkpoint

If this repair passes, the next checkpoint is:

```text
AG-LIVE-SUFFICIENCY-FAP-AUTHORPROSE-01
```

Likely mode: BUILD. Citation eligibility and source-obligation satisfaction
must remain explicitly licensed; this repair does not silently open them.
