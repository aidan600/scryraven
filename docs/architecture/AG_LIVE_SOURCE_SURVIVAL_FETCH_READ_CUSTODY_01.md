# AG-LIVE-SOURCE-SURVIVAL-FETCH-READ-CUSTODY-01

Status: live source-survival / fetch-read / EvidenceLedger custody validation
harness.

Mode: PROOF.

Usable-answer verdict target: NO-BUT-JUSTIFIED.

Proof class: live_component_proof.

Product-facing progress type: live component source-survival validation with
explicit live license.

## Prior Input

This phase consumes the existing #357 local output:

```text
output/ag_limited_live_search_candidate_01/sanitized_provider_results.json
output/ag_limited_live_search_candidate_01/search_result_candidate_packet.json
output/ag_limited_live_search_candidate_01/validation_packet.json
```

It must select the rank-1 `travel.state.gov` candidate from the prior packet:

```text
https://travel.state.gov/en/passports/apply/help/fees.html
```

If the prior packet is missing, invalid, or rank 1 is not `travel.state.gov`,
the harness fails closed with `prior_candidate_packet_missing_or_mismatched`.

## Caps

- max ScryRaven validation runs: 1
- provider/search/broker/model calls: 0
- URL fetch/read calls: 1
- selected URL: exact rank-1 `travel.state.gov` URL from #357 output
- max redirects: 2
- allowed final host: `travel.state.gov`, with same official `state.gov`
  redirects recorded if they occur
- max fetched bytes: 1 MB
- max sanitized readable text retained in the review packet: 8,000 characters
- current `FetchReadContentPacket` bounded text cap: 2,000 characters
- raw HTML retained: false
- raw response headers retained: false
- raw cookies retained: false
- EvidenceLedger candidate/content custody admissions: max 1
- SemanticObservation, ComponentCoverage, Sufficiency/FAP/Author/AuthorProse,
  citation eligibility/rendering, and source-obligation satisfaction: 0
- retries: 0

## Commands

Prepare the request packet without any fetch/read:

```powershell
py scripts\ag_live_source_survival_fetch_read_custody_01.py prepare-request `
  --candidate-packet output\ag_limited_live_search_candidate_01\search_result_candidate_packet.json `
  --validation-packet output\ag_limited_live_search_candidate_01\validation_packet.json `
  --output-dir output\ag_live_source_survival_fetch_read_custody_01
```

Run the one licensed public fetch/read and reduce through existing custody
machinery:

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
This phase tests source survival only: whether that candidate survives one public URL fetch/read,
becomes bounded sanitized readable content, and enters
`FetchReadContentPacket` / `SanitizedContentReference` and EvidenceLedger
candidate/content custody.

EvidenceLedger custody is lineage/custody only. It does not satisfy source
obligations, does not create semantic support, does not create citation
eligibility, does not reduce ComponentCoverage, does not decide Sufficiency,
does not create FinalAnswerPacket or Author material, and does not prove product
correctness.

## Explicit Non-Proofs

- not semantic support from fetched content
- no ComponentCoverage
- no SufficiencyReadiness
- no FinalAnswerPacket authority
- no Author or AuthorProse behavior
- no citation eligibility or citation rendering
- no source-obligation satisfaction
- no answer text
- no answer correctness or product correctness
- no product-quality prose

mandatory next Build/product checkpoint: live evidence-relative semantic support
over the fetched content if source survival / fetch-read / EvidenceLedger
candidate-content custody passes; otherwise targeted REPAIR of the first broken
fetch/read/custody seam.
