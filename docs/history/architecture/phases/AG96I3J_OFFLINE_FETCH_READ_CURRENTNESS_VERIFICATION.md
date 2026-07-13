Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I3J_OFFLINE_FETCH_READ_CURRENTNESS_VERIFICATION).

# AG-96I3J Offline Fetch/read Currentness Verification

## Status

AG-96I3J adds an offline diagnostic helper for scout handoff candidates:

```text
core.followup_fetch_read_currentness_verification
```

The helper answers a narrow question: given a sanitized scout-to-acquisition
handoff candidate and a caller-supplied sanitized read observation for that
candidate, does the observation appear suitable for later EvidenceLedger
admission review?

No live validation was run. The helper does not call providers, start a broker,
fetch or read live URLs, inspect `.env`, read secrets, invoke models, activate
Author, create citation eligibility, admit EvidenceLedger records, or change
product behavior.

## Generic Verification, Not Source-Specific Logic

One historical fixture used an official-currentness-unverified government page
because AG-96I3I showed that a scout diagnostic could find an official-looking
candidate before read verification existed. That fixture is provenance, not
doctrine. This phase does not implement a source-specific resolver or any
hardcoded answer value. Fixtures verify only generic signals:

- candidate URL/domain match the supplied read observation;
- source identity remains official;
- required terms are present;
- required year and currentness signals are present.

The tests also cover other official pages and software release notes. That mix
keeps the helper centered on the packet contract rather than on one domain or
one claim type.

## Why Read Observation Is Required

Scout can find a promising door. It cannot prove that the page behind the door
currently supports the exact claim. Search-result metadata may be stale,
ambiguous, redirected, or a landing page.

AG-96I3J therefore requires a supplied read observation with sanitized fields
such as attempted URL, resolved URL, domain, fetch/read status, HTTP status,
content type, detected dates, and extracted text. The helper may inspect that
text, but it does not retain raw page text in the output. It emits only bounded
supporting fragments for found terms.

## Packet Contract

The packet is diagnostic and non-authoritative:

```text
schema_version=ag96i3j_fetch_read_currentness_verification_v1
record_type=fetch_read_currentness_verification_diagnostics
canonical_state=false
trace_only=false
storage_only=false
```

Important statuses include:

- `verified_official_current_relevance`
- `official_but_required_terms_missing`
- `official_but_currentness_unclear`
- `official_but_value_terms_missing`
- `fetch_read_failed`
- `read_unavailable`
- `candidate_url_mismatch`
- `candidate_domain_mismatch`
- `candidate_rejected`
- `not_attempted`

Candidate accounting is separated from verification status:

- `used_for_verification`
- `rejected_with_reason`
- `superseded_with_reason` reserved for a later phase
- `not_attempted`

The helper also preserves compact freshness context from AG-96I3G/AG-96I3I
where available. That context explains why the scout job used broad, absent, or
mixed recency rather than a narrow recent filter. The verification layer should
not lose that retrieval prior when deciding whether to retry read acquisition
or seek a better official source.

## Evidence Boundary

Even a verified AG-96I3J packet remains only a suitability observation for
later admission review:

```text
final_evidence=false
citation_eligible=false
evidence_ledger_admitted=false
author_activation_allowed=false
```

The recommended next step for a verified packet is
`evidence_ledger_admission_review`, not admission itself. A later phase may
decide how verified observations become EvidenceLedger candidates, what
additional custody fields are required, and whether any verified observation is
eligible for final citation selection.

## Candidate Accounting

AG-96I3J records whether a handoff candidate was:

- used for verification;
- rejected with a reason;
- not attempted because fetch/read did not produce usable text;
- or, in a future extension, superseded by a better official source.

Supersession is intentionally not implemented in this phase because it can
easily expand into product source-ranking or provider-selection logic. The
packet vocabulary leaves room for that future diagnostic, but this helper only
evaluates the supplied candidate/read-observation pair.

## Closed Surfaces Preserved

AG-96I3J does not change:

- live provider/search behavior;
- broker startup or broker invocation;
- live fetch/read behavior;
- Serper, Brave, Tavily, Linkup, Exa, or OpenAI calls;
- model calls;
- Author or citation behavior;
- EvidenceLedger admission;
- SufficiencyJudgment authority;
- FinalAnswerPacket authority;
- product provider routing;
- product query generation;
- provider selection policy;
- `core/pipeline_orchestrator.py` domain logic;
- include-domain or `site:` filtering;
- source-specific resolution.
