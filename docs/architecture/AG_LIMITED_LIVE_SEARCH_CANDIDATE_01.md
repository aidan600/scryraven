# AG-LIMITED-LIVE-SEARCH-CANDIDATE-01

Status: limited live-search candidate validation harness.

Mode: PROOF.

Usable-answer verdict target: NO-BUT-JUSTIFIED.

Proof class: live_component_proof.

Product-facing progress type: live-search-only validation with explicit live
license.

Exact validation query:

```text
current adult U.S. passport book renewal fee official
```

User-facing question represented:

```text
What is the current adult U.S. passport book renewal fee?
```

## Caps

These caps are phase-local licensed budget, not the global live-search
validation default. Ordinary/default live validation remains at 2 results per
task unless a phase explicitly passes a separately licensed cap.

- max ScryRaven validation runs: 1
- max search tasks: 1
- max provider search calls total: 1
- provider: serper
- operation: search.query
- max results: 5
- model calls: 0
- broker calls: max 1 tracked loopback generic provider-execution call
- fetch/read calls: 0
- retrieval calls: 0
- EvidenceLedger admissions from live content: 0
- citation eligibility decisions: 0
- source-obligation satisfaction decisions: 0
- Sufficiency/FAP/Author/AuthorProse from live evidence: 0
- retries: 0
- raw provider payload retained: false
- raw search response retained: false

## Commands

Prepare the request/review packet without any provider call:

```powershell
py scripts\ag_limited_live_search_candidate_01.py prepare-request `
  --query "current adult U.S. passport book renewal fee official" `
  --output-dir output\ag_limited_live_search_candidate_01
```

Only the separate trusted-local broker helper may perform the one licensed
provider call:

```powershell
py scripts\run_provider_proxy_broker_once.py `
  --provider serper `
  --operation search.query `
  --query "current adult U.S. passport book renewal fee official" `
  --max-results 5 `
  --timeout-seconds 30 `
  --retry-cap 0 `
  --cost-ceiling-usd 0.05 `
  --output output\ag_limited_live_search_candidate_01\sanitized_provider_results.json `
  --broker-url http://127.0.0.1:8765/run `
  --env-file <PRIVATE-ENV-FILE> `
  --confirm-provider-call
```

Reduce sanitized provider results without any provider call:

```powershell
py scripts\ag_limited_live_search_candidate_01.py reduce-results `
  --query "current adult U.S. passport book renewal fee official" `
  --provider-results output\ag_limited_live_search_candidate_01\sanitized_provider_results.json `
  --output-dir output\ag_limited_live_search_candidate_01
```

Output path:

```text
output/ag_limited_live_search_candidate_01/
```

Retained `01B` local artifacts can be preflighted without live calls or
fetch/read:

```powershell
py scripts\ag_limited_live_search_candidate_01.py preflight-retained-artifacts `
  --repo-root <REPOSITORY-ROOT>
```

The preflight checks only:

```text
output/ag_live_ordinary_search_candidate_01b/sanitized_provider_results.json
output/ag_live_ordinary_search_candidate_01b/search_candidate_packet.json
output/ag_live_ordinary_search_candidate_01b/search_result_candidate_packet.json
```

It returns a sanitized metadata summary with exactly one decision:
`PASS`, `BLOCKED_LOCAL_ARTIFACT_MISSING`,
`BLOCKED_LOCAL_ARTIFACT_UNREADABLE`,
`BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH`, `BLOCKED_OUTPUT_BOUNDARY`,
`BLOCKED_RAW_OR_PRIVATE_FIELD`, `BLOCKED_RETENTION_FLAG`, or
`BLOCKED_CANDIDATE_LINEAGE`. It reports repo-relative paths, existence,
readability, JSON top-level keys, candidate count, raw-retention flags, and
candidate-lineage status only. It does not print full artifact contents and does
not read alternate-checkout artifact contents.

`prepare-request`, `reduce-results`, and `preflight-retained-artifacts` do not
call providers, brokers, models, fetch/read, retrieval, EvidenceLedger,
citations, Sufficiency, FAP, Author, or AuthorProse. The broker remains private
credential plumbing and returns sanitized provider-result records only.

## Decision

This run decides whether the current ordinary-query/SearchExecutorHandoff path
can acquire sanitized live official/current candidate results for the approved
query and reduce them into `SearchResultCandidatePacket` without raw/private
leakage or old-path revival.

Passing candidate acquisition means exactly one provider call was attempted and
completed by the trusted-local broker helper, raw retention stayed false, at
least one plausible official/current government source appeared in the top 5,
and `SearchResultCandidatePacket` built and validated from sanitized results.

This phase validates candidate acquisition only, not source survival.

## Explicit Non-Proofs

- no answer text from live search candidates
- no source survival proof
- no fetch/read proof
- no EvidenceLedger custody from live content
- no semantic support
- no citation eligibility or citation rendering
- no source-obligation satisfaction
- no Sufficiency, FAP, Author, or AuthorProse proof from live evidence
- no installed product behavior proof
- no product correctness

Mandatory next Build/product checkpoint: targeted live source-survival /
fetch-read / evidence-custody phase if candidate acquisition passes, or a
targeted acquisition repair if live candidate acquisition fails.
