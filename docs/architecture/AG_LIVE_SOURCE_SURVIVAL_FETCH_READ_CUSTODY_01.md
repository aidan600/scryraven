# AG-LIVE-SOURCE-SURVIVAL-FETCH-READ-CUSTODY-01

Status: retired direct transport; offline injected-fixture validation harness
only.

Mode: PROOF.

Usable-answer verdict target: NO-BUT-JUSTIFIED.

Proof class: component_harness_proof (offline injected fixture only).

Execution class: VALIDATION.

Fetcher authority: injected-fixture-only.

Product reachability: PRODUCT-unreachable.

Product-facing progress type: offline source-survival/custody reducer
validation; no live component proof.

## Retired Transport Disposition

The former local dynamic webpage opener is a typed fail-closed tombstone with
block code `validation_dynamic_content_opener_retired`. It performs no DNS,
urllib opener construction, redirect following, socket connection, or webpage
transport. No replacement downloader was added.

This harness may continue only through an explicitly injected sanitized
`FetchReadResult` fixture. The injection seam is validation-only and
structurally unreachable from PRODUCT. It proves downstream packet and custody
mechanics, not source survival on the public network.

## Fixture Input

This phase consumes the existing #357 local output:

```text
output/ag_limited_live_search_candidate_01/sanitized_provider_results.json
output/ag_limited_live_search_candidate_01/search_result_candidate_packet.json
output/ag_limited_live_search_candidate_01/validation_packet.json
```

The fixture flow selects the rank-1 `travel.state.gov` candidate from the prior
packet:

```text
https://travel.state.gov/en/passports/apply/help/fees.html
```

If the prior packet is missing, invalid, or rank 1 is not `travel.state.gov`,
the harness fails closed with `prior_candidate_packet_missing_or_mismatched`.

## Bounds

- max ScryRaven validation runs: 1
- provider/search/broker/model calls: 0
- URL fetch/read calls: 0
- injected fixture executions: at most 1
- selected URL: exact rank-1 `travel.state.gov` URL from #357 output
- fixture redirect facts: bounded to the existing packet shape; not observed by
  this harness
- fixture final host: must remain within the existing validation packet rules
- fixture fetched-byte fact: bounded to the existing 1 MB validation ceiling
- max sanitized readable text retained in the review packet: 8,000 characters
- current `FetchReadContentPacket` bounded text cap: 2,000 characters
- raw HTML retained: false
- raw response headers retained: false
- raw cookies retained: false
- EvidenceLedger candidate/content custody admissions: max 1
- SemanticObservation, ComponentCoverage, Sufficiency/FAP/Author/AuthorProse,
  citation eligibility/rendering, and source-obligation satisfaction: 0
- retries: 0

## Commands And Expected Block

Prepare the request packet without any fetch/read:

```powershell
py scripts\ag_live_source_survival_fetch_read_custody_01.py prepare-request `
  --candidate-packet output\ag_limited_live_search_candidate_01\search_result_candidate_packet.json `
  --validation-packet output\ag_limited_live_search_candidate_01\validation_packet.json `
  --output-dir output\ag_live_source_survival_fetch_read_custody_01
```

The historical fetch command no longer licenses or performs a public read. With
no injected fixture it returns a typed source-survival failure with zero
attempted calls and `validation_dynamic_content_opener_retired`:

```powershell
py scripts\ag_live_source_survival_fetch_read_custody_01.py fetch-read-custody `
  --candidate-packet output\ag_limited_live_search_candidate_01\search_result_candidate_packet.json `
  --validation-packet output\ag_limited_live_search_candidate_01\validation_packet.json `
  --output-dir output\ag_live_source_survival_fetch_read_custody_01 `
  --confirm-fetch-read
```

Output path:

```text
output/ag_live_source_survival_fetch_read_custody_01/
```

## Boundary

Candidate acquisition already passed in `AG-LIMITED-LIVE-SEARCH-CANDIDATE-01`.
This retained harness tests only whether explicitly injected bounded sanitized
content can enter
`FetchReadContentPacket` / `SanitizedContentReference` and EvidenceLedger
candidate/content custody.

EvidenceLedger custody is lineage/custody only. It does not satisfy source
obligations, does not create semantic support, does not create citation
eligibility, does not reduce ComponentCoverage, does not decide Sufficiency,
does not create FinalAnswerPacket or Author material, and does not prove product
correctness.

## Explicit Non-Proofs

- no live DNS, public URL fetch/read, redirect, final-target, canonical-target,
  or connected-peer proof
- no provider-operation target-safety eligibility proof
- not semantic support from fixture content
- no ComponentCoverage
- no SufficiencyReadiness
- no FinalAnswerPacket authority
- no Author or AuthorProse behavior
- no citation eligibility or citation rendering
- no source-obligation satisfaction
- no answer text
- no answer correctness or product correctness
- no product-quality prose
- no roadmap activation or mandatory next Build selection

The current roadmap and exact-URL safety owner supersede the historical live
validation sequencing. Production exact-URL acquisition remains blocked on a
truthfully eligible provider operation.
