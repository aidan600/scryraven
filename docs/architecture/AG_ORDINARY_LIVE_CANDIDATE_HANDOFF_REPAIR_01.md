# AG-ORDINARY-LIVE-CANDIDATE-HANDOFF-REPAIR-01

Status: active ordinary product-path repair phase.

Mode: REPAIR.

Repair verdict target: YES.

## Named Defect

The live chain through `SearchResultCandidatePacket`, fetch/read custody,
SemanticObservation, and ComponentCoverage had been proven in controlled phase
harnesses, but ordinary `core.pipeline_orchestrator.run_pipeline(...)` did not
own the first live-chain handoff seam.

The missing ordinary seam was:

```text
ordinary run_pipeline
-> accepted current answer contract
-> SearchExecutorHandoff
-> live_search_validation_state
-> SearchResultCandidatePacket
```

Without that product-owned seam, ordinary retrieval/provider diagnostics must
remain non-authority and cannot be retroactively promoted into canonical source
candidates.

## Repair

`run_pipeline` now has a default-disabled pre-retrieval bridge guarded by:

```text
enable_ordinary_live_candidate_handoff
```

When enabled with structured offline/fake candidate records, `run_pipeline`
starts a bounded candidate-handoff `RunKernel`, reduces the front-half contract,
reduces `SearchExecutorHandoff`, authorizes/reduces `live_search_validation`,
builds `SearchResultCandidatePacket` from canonical live-validation state, and
publishes only a safe projection in the ordinary execution trace.

The candidate-handoff kernel is intentionally separate from the main answer
kernel so candidate-only contract state does not occupy the ordinary answer
semantic slots before the existing answer-path SemanticObservation and
FinalAnswerPacket flow runs. The runtime consumer is still `run_pipeline`, not a
sidecar phase script, and product code does not import `scripts/ag_*`.

## Opened Surfaces

- `core.pipeline_orchestrator.run_pipeline` / `_run_pipeline_inner`
- `core.live_ordinary_candidate_handoff_runtime`
- default-disabled `RunConfig` candidate handoff fields
- offline/fake structured candidate input in product-path tests
- safe execution-trace projection for review

## Closed Surfaces

- provider routing/provider selection changes
- retrieval/ranking/filtering changes
- prompt behavior
- live provider/search/broker calls
- live fetch/read calls
- model calls
- raw provider payloads, raw search responses, raw prompts, secrets, logs, DB
  rows, caches, or full traces
- EvidenceLedger custody from candidates
- source-obligation satisfaction
- citation eligibility/rendering
- SufficiencyReadiness
- FinalAnswerPacket
- Author/AuthorProse
- answer text or product correctness claims

## Live Budget

- provider/search calls: 0
- broker calls: 0
- fetch/read calls: 0
- model calls: 0
- retrieval calls by the candidate handoff seam: 0
- raw payload retention: false
- retries: 0

## Diagnostics Boundary

Structured candidate inputs are supplied explicitly through product-path config
for tests. Retrieval diagnostics, provider summaries, and ordinary retrieval
results are never used as source-candidate authority for this seam. If the flag
is enabled without structured candidate records, the seam fails closed with a
named missing-input reason.

## Explicit Non-Proofs

- no live provider/search/broker/fetch/model call
- no source survival proof
- no fetch/read custody proof
- no EvidenceLedger custody from candidate records
- no citation eligibility or citation rendering
- no source-obligation satisfaction
- no SufficiencyReadiness
- no FinalAnswerPacket proof
- no Author or AuthorProse behavior
- no answer text or product correctness claim

Mandatory next checkpoint:

```text
AG-ORDINARY-LIVE-SOURCE-CUSTODY-INTEGRATION-01
```

That checkpoint should wire the next proven live-chain seam into the ordinary
path before any Sufficiency, FinalAnswerPacket, Author, or AuthorProse claim.
