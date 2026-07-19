# AG-LIVE-ANSWER-BEARING-BOUNDING-REPAIR-01

Status: active product-path repair phase.

Mode: REPAIR.

Repair verdict target: YES.

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
- #358 source-survival harness where needed to use the repaired selector;
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

## Live Budget

The repair may use one public fetch/read only after offline tests pass and only
with `--confirm-fetch-read-repair`.

- URL: `https://travel.state.gov/en/passports/apply/help/fees.html`
- allowed final host: `travel.state.gov`
- max fetched bytes: 1 MB, matching #358
- retries: 0
- raw HTML retained: false
- raw headers/cookies retained: false
- output path: `output/ag_live_answer_bearing_bounding_repair_01/`

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

## Expected Outcomes

Success means the repaired bounded content includes the target-component anchors
in a coherent local source-derived context, and #359 advances past
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

- no final answer text;
- no answer correctness or product correctness;
- no source-obligation satisfaction;
- no citation eligibility or citation rendering;
- no SufficiencyReadiness;
- no FinalAnswerPacket;
- no Author or AuthorProse behavior;
- no provider/search/broker/model behavior.

## Mandatory Next Checkpoint

If the repair succeeds and #359 advances past source-content-insufficient, the
mandatory next checkpoint is:

```text
AG-LIVE-SEMANTIC-SUPPORT-COVERAGE-REPLAY-01
```

Mode depends on the first remaining blocker: REPAIR for a RunKernel
consumer/state seam fix, PROOF for a bounded replay through existing
SemanticObservation and ComponentCoverage machinery, or BUILD only if the phase
moves all the way to SufficiencyReadiness -> hardened FAP -> AuthorProse
reviewable answer packet.
