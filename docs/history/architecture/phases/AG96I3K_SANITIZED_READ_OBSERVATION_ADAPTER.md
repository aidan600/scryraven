Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I3K_SANITIZED_READ_OBSERVATION_ADAPTER).

# AG-96I3K Sanitized Read-Observation Adapter

## Status

AG-96I3K adds a narrow, pure, offline adapter for scout handoff candidates:

```text
core.followup_read_observation_adapter
```

It bridges one step in the scout/read diagnostics lane:

```text
scout handoff candidate (AG-96I3I)
+ caller-supplied fetch/read material
-> sanitized read observation (AG-96I3K)
-> AG-96I3J verifier input
```

The adapter standardizes caller-supplied fetch/read material for a handoff
candidate into a bounded, sanitized read observation. It is the input-shaping
step that precedes AG-96I3J currentness verification.

No live validation was run. The adapter does not fetch pages, call providers,
start a broker, read live URLs, inspect `.env`, read secrets, invoke models,
activate Author, create citation eligibility, or admit EvidenceLedger records.

## What This Phase Is Not

AG-96I3K is only the sanitized read-observation adapter phase. It deliberately
does **not** implement EvidenceLedger admission-review diagnostics. Admission
review belongs to a later AG-96I3L-style phase. The adapter's most advanced
routing outcome is "this observation is ready for AG-96I3J currentness
verification", not "this observation is ready for admission".

## Ephemeral Verifier Input vs Durable Projection

The return shape separates two regions with different retention rules:

- `verifier_input` is **ephemeral**. It may contain bounded, sanitized extracted
  text so AG-96I3J can run term/currentness checks. It exists to feed
  verification only and is directly consumable by
  `core.followup_fetch_read_currentness_verification` as its `read_observation`.
  `as_fetch_read_currentness_verification_input(...)` is the tested accessor for
  this region.
- `durable_projection` must **not** retain raw page text. It preserves only
  bounded identity, status, metadata, comparison posture, counts, redaction
  posture, and diagnostic routing fields. Tests assert that unique raw-text
  sentinels and raw extracted text never appear in `durable_projection`.

## Conservative URL/domain Comparison

URL/domain comparison mirrors the conservative same-domain posture already used
by AG-96I3J. It does not invent source-specific official-domain equivalence,
alias rules, redirect-trust rules, or domain-authority policy. Comparison
postures:

- `candidate_url_match`
- `candidate_domain_match`
- `resolved_url_differs_same_domain` (a redirect within the same candidate
  domain; conservatively acceptable)
- `candidate_url_mismatch` (same domain, materially different URL)
- `candidate_domain_mismatch` (off-candidate domain, attempted or resolved)
- `candidate_identity_unverified` (not enough identity signal to confirm or deny;
  AG-96I3J re-checks identity downstream)

When acceptable equivalence cannot be established conservatively, the adapter
reports a mismatch/uncertain posture rather than silently accepting it.

## Read Posture and Recommended Next Step

`read_posture` summarizes the observation, and `recommended_next_step` routes the
candidate:

| read_posture                 | recommended_next_step                |
| ---------------------------- | ------------------------------------ |
| `read_observation_ready`     | `fetch_read_currentness_verification`|
| `candidate_url_mismatch`     | `reject_candidate`                   |
| `candidate_domain_mismatch`  | `scout_or_query_repair`              |
| `fetch_failed`               | `targeted_fetch_read_retry`          |
| `read_unavailable`           | `targeted_fetch_read_retry`          |
| `empty_extracted_text`       | `targeted_fetch_read_retry`          |
| `not_attempted`              | `targeted_fetch_read_retry`          |

`scout_or_query_repair` is the "return to acquisition" route: an off-candidate
domain implies the wrong door was opened, so re-acquisition is preferable to
rejecting only this read.

## Oversized and Empty Text

Extracted text is whitespace-normalized and bounded by
`max_extracted_text_chars` (default 8000, clamped to `[200, 40000]`). The
`durable_projection` records `extracted_text_char_count` (pre-bound count),
`sanitized_text_char_count` (post-bound count), and `extracted_text_truncated`
so oversized inputs are explicit without retaining the raw text.

## Evidence Boundary

The adapter output is diagnostic and non-authoritative:

```text
final_evidence=false
citation_eligible=false
evidence_ledger_admitted=false
author_activation_allowed=false
```

`evidence_boundary.evidence_ledger_admission_review_performed=false` makes the
sequencing explicit: this phase shapes verifier input; it does not perform
admission review.

## Closed Surfaces Preserved

AG-96I3K does not change:

- provider routing, provider selection, or provider depth;
- query generation, query ordering, or retrieval ranking/filtering;
- `SearchWorkPlan` / `QueryPlan` behavior;
- EvidenceLedger admission/intake;
- `SufficiencyJudgment` / `FinalAnswerPacket` behavior;
- Author or citation behavior;
- prompts;
- live ScryRaven/proplex provider, search, model, or fetch/read calls;
- `core/pipeline_orchestrator.py` domain logic.

No live fetcher is implemented and no network calls are made beyond ordinary git
or GitHub operations used to publish the branch.
