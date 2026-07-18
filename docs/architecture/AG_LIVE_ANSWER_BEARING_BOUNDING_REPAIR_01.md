# AG-LIVE-ANSWER-BEARING-BOUNDING-REPAIR-01

Status: historical predecessor repair record; direct public transport retired,
offline injected-fixture regression only.

Mode: REPAIR.

Repair verdict target: YES.

Current execution class: VALIDATION. This record preserves what the predecessor
phase established; it does not license another public fetch/read or establish
current product reachability.

## Named Defect

PR #359 consumed the live #358 `travel.state.gov` fetch/read/custody output and
failed honestly at `gate_5_evidence_relative_analysis_proposal` with
`semantic_support_fail_source_content_insufficient`.

The defect was bounded readable-content selection. The #358 path retained a
safe deterministic prefix, but that prefix was not answer-bearing for the target
component:

```text
adult U.S. passport book renewal fee
```

Component claim under test only:

```text
adult U.S. passport book renewal fee is $130
```

This is not final answer text and is not a product correctness claim.

## Prior Context

- #357 proved live candidate acquisition for the rank-1 official source.
- #358 proved selected public source survival through fetch/read into
  `FetchReadContentPacket`, `SanitizedContentReference`, and EvidenceLedger
  candidate/content custody.
- #359 proved the semantic-support gate fails closed when bounded content is
  not answer-bearing.

## Opened Surfaces

- bounded readable-content selection / excerpting for fetched source content;
- #358 source-survival fixture shape where needed to exercise the repaired
  selector offline;
- #359 semantic-support harness only to verify that the repaired bounded content
  no longer fails at source-content-insufficient;
- focused docs/tests for this repair.

## Closed Surfaces

- provider/search/broker calls: 0;
- model calls: 0;
- broad retrieval;
- ranking/filtering of search candidates;
- prompt behavior;
- raw HTML/raw headers/raw cookies/raw page text retention;
- semantic-support permissiveness;
- direct RunKernel state mutation;
- source-obligation satisfaction;
- citation eligibility/rendering;
- SufficiencyReadiness;
- FinalAnswerPacket;
- Author/AuthorProse;
- answer text;
- product correctness claims.

## Retired Live Budget

The predecessor phase used the following bounded live posture. It is historical
evidence only and is no longer licensed. The direct opener is now a typed fail-
closed tombstone; current URL fetch/read calls are `0`, and an explicitly
injected sanitized fixture may be consumed at most once.

- URL: `https://travel.state.gov/en/passports/apply/help/fees.html`
- allowed final host: `travel.state.gov`
- max fetched bytes: 1 MB, matching #358
- retries: 0
- raw HTML retained: false
- raw headers/cookies retained: false
- historical output path: `output/ag_live_answer_bearing_bounding_repair_01/`

## Repair Posture

The repair changes source-bound content selection rather than weakening semantic
support. The selector prefers a coherent answer-bearing window when the anchors
are present later in the same sanitized source. It consumes sanitized readable
text only, stays under the existing 2,000-character `FetchReadContentPacket`
bounded-text cap, and records safe metadata such as matched anchors, missing
anchors, selected-window offsets, window digest, and selector strategy.

Anti-anchor-laundering rule:

```text
one contiguous source-derived window
```

The selector must not stitch unrelated distant fragments together merely to
satisfy anchors. If the anchors only appear in disconnected regions without a
coherent local context, the selector records missing anchors and downstream
semantic support remains fail-closed.

## Historical Outcomes

Success at that predecessor checkpoint meant the repaired bounded content
included the target-component anchors in a coherent local source-derived
context, and #359 advanced past
`semantic_support_fail_source_content_insufficient`.

Acceptable first remaining blocker:

```text
gate_6_semantic_observation_admission
```

That outcome means the bounded content selection defect is repaired, while the
CLI path still lacks a valid RunKernel consumer/state seam for admission. It
does not create SemanticObservation, ComponentCoverage, readiness, citations,
FAP, Author, or answer text by implication.

## Explicit Non-Proofs

- no current public fetch/read, DNS, redirect, final-target, or connected-peer
  proof;
- no production provider-operation target-safety eligibility;
- no current READ, Focused Extract, final custody, or semantic admission;
- no final answer text;
- no answer correctness or product correctness;
- no source-obligation satisfaction;
- no citation eligibility or citation rendering;
- no SufficiencyReadiness;
- no FinalAnswerPacket;
- no Author or AuthorProse behavior;
- no provider/search/broker/model behavior.

## Current Supersession

The historical mandatory next checkpoint was:

```text
AG-LIVE-SEMANTIC-SUPPORT-COVERAGE-REPLAY-01
```

That sequencing is superseded. The canonical target-safety repair retired the
local opener, and production untrusted exact-URL routing remains blocked because
no Linkup/Tavily operation has sufficient committed public-target guarantees or
observable final-target lineage to be truthfully eligible. This is not an
inherent-unsafety claim. Offline fixtures may preserve selector regression
coverage only; they do not reactivate READ, Focused Extract, custody, semantic
admission, Sufficiency, FAP, or Author.
