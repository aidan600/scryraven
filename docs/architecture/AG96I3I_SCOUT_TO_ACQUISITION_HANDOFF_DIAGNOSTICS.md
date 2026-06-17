# AG-96I3I Scout-to-acquisition Handoff Diagnostics

## Status

AG-96I3I adds an offline diagnostic handoff from provider-result scout
observations to a later acquisition layer:

```text
core.followup_scout_acquisition_handoff
```

The AG-96I3E brokered provider-neutral discovery runner now includes:

```text
scout_to_acquisition_handoff_diagnostics
```

No live validation was run for this phase. The helper does not call providers,
start a broker, fetch/read pages, inspect `.env`, read secrets, invoke models,
activate Author, create citation eligibility, admit EvidenceLedger records, or
change product behavior.

## Fixture Provenance: Why One Serper Run Was A Scout Success

After AG-96I3H, a manually authorized brokered Serper diagnostic for:

```text
IRS 2026 standard mileage rates business use car notice announcement
```

returned a rank-1 official IRS result:

```text
https://www.irs.gov/tax-professionals/standard-mileage-rates
```

The existing AG-96I3D result-set diagnostics kept
`official_current_candidate_count=0` because the runner did not fetch/read the
page and therefore could not verify currentness. That was correct for the
official/current evidence boundary, but the summary was too coarse for
operations: it collapsed "official source found, currentness unverified" into
"provider result set lacked official/current candidate."

AG-96I3I preserves that distinction. A rank-1 official source with:

```text
candidate_fit_status=official_currentness_unverified
currentness_signal=currentness_not_verified_by_diagnostic
```

is a scout win and a verification candidate. It is not final evidence.

This example is fixture provenance and a historical trigger for the diagnostic
shape. Durable doctrine remains generic: a scout result may expose an
official-looking candidate whose current support for the exact claim is still
unverified until a later fetch/read layer supplies sanitized page observation.

## Handoff Contract

The handoff packet is sanitized and diagnostic:

- `schema_version=ag96i3i_scout_to_acquisition_handoff_diagnostics_v1`
- `record_type=scout_to_acquisition_handoff_diagnostics`
- `canonical_state=false`
- `trace_only=false`
- `storage_only=false`
- `verification_candidates[]`
- `scout_result_outcome`
- `recommended_next_step`
- `stop_more_scout_spending_recommended`
- `evidence_boundary`
- raw/private redaction posture

Verification candidates carry only sanitized values such as rank, title, URL,
domain, source class/tier, currentness signal, candidate fit status, provider
name, query reference, and freshness policy context. They are always marked:

```text
final_evidence=false
citation_eligible=false
required_next_step=fetch_read_currentness_verification
```

The packet distinguishes:

- `official_current_candidate_verified_by_diagnostic`
- `official_candidate_currentness_unverified`
- `bridge_only_no_official_candidate`
- `no_official_candidate_visible`

Existing AG-96I3D diagnostics remain backward-compatible. The old field can
still say `official_current_candidate_count=0`; the new handoff field explains
whether an official URL was visible but still needs verification.

## Why Official/current Requires Fetch/read Verification

Search result metadata can identify promising official domains and artifact
titles. It cannot prove that the page text currently supports the user's exact
claim. A SERP title can be stale, ambiguous, redirected, changed, or merely a
landing page that points elsewhere.

Official/current evidence therefore requires a later acquisition step that can:

- fetch/read the candidate;
- verify the page text and currentness;
- supersede it with a better official source;
- or reject it with a reason.

Scout does not answer. Scout does not create final evidence. Scout does not
create citation eligibility. Scout can produce verification candidates and
acquisition hints.

## Freshness Policy Travels With The Handoff

For known-year official/current artifact searches, narrow recent freshness may
be forbidden because the canonical source may be older than recent SEO summaries
while still authoritative. The historical Serper diagnostic above is one
fixture instance of that broader pattern.

The handoff carries:

- `freshness_intent`
- `freshness_window`
- `provider_freshness_policy`
- `over_narrow_recent_window_forbidden`
- `freshness_rationale`

This prevents the next layer from losing the reason the scout omitted a recent
provider filter.

## Accounting For Scout Candidates

Primary/fetch-read acquisition should account for scout handoff candidates. It
should not be judged only by whether it independently rediscovers the same URL.
The correct question is whether the next layer did one of the accountable
things:

- used the scout candidate and verified it;
- used the scout candidate as a clue and superseded it with a better official
  source;
- rejected the scout candidate with a reason;
- or reported that no official handoff candidate existed.

This keeps acquisition accountable without turning a scout URL into a hard
domain corridor, `includeDomains` filter, `site:` filter, or source-specific
resolver.

## Spending Posture

When a rank-1 official-currentness-unverified candidate is visible, more scout
spending is usually the wrong next move. AG-96I3I marks:

```text
scout_result_outcome=official_candidate_currentness_unverified
handoff_priority=high
recommended_next_step=fetch_read_currentness_verification
stop_more_scout_spending_recommended=true
```

The next phase should spend effort on verification, not another unconstrained
scout call for the same shaped query.

## Preparation For Later Fetch/read Continuation

AG-96I3I prepares a later fetch/read continuation seam by making the handoff
explicit, bounded, and non-authoritative. A future phase can consume the
verification candidates, perform currentness verification, and report whether
each scout candidate was used, superseded, or rejected.

That future phase must remain separate from this scout diagnostic. This phase
does not change:

- product provider routing;
- provider selection policy;
- product query generation;
- fetch/read behavior;
- Author or citation behavior;
- EvidenceLedger authority;
- SufficiencyJudgment authority;
- FinalAnswerPacket authority;
- `core/pipeline_orchestrator.py` domain logic;
- include-domain or `site:` filtering;
- source-specific resolution.
