# AG-47B Output Quality Review Addendum

Date: May 24, 2026

Branch: `chatgpt/ag47b-output-quality-addendum`

Base: `57d9c2c` (`Merge pull request #72 from aidan600/codex/ag47b-active-batch-output-quality-review-r1`)

Scope: validation-record correction only. No code, provider routing, provider selection, search depth, query generation, prompts, final-answer behavior, handoffs, legal/current-primary adapter behavior, social integration, persistence behavior, or runtime behavior changed.

## Purpose

This addendum records a post-merge qualitative/web review of the local AG-47B output-quality packet.

It does not replace the AG-47B validation note. It narrows and corrects the interpretation of that note, especially the Q2 Roth IRA case.

Core distinction:

```text
This is useful product-quality evidence.
It is not a reason to derail the controller/batch architecture lane.
```

AG-47B still supports the conclusion that AG-47A active batch dispatch did not visibly introduce protected-surface drift: no `retrieve_targeted` provider role appeared, no targeted executor appeared, and visible provider/depth/query-generation/prompt flags remained unchanged in the four-case review.

However, the answer-quality interpretation needs a correction: Q2 should not be treated as a clean "good" answer because it contained material numeric errors despite official IRS sources being available.

## Post-Merge Review Inputs

Inputs reviewed:

- committed AG-47B validation note: `docs/validation/AG47B_ACTIVE_BATCH_OUTPUT_QUALITY_REVIEW_R1.md`
- local untracked packet: `output/ag47b_output_quality_review_packet.md`
- public current web sources checked during ChatGPT review, including IRS, NASA, Obsidian, Notion, Capacities, and supporting vehicle/electricity references

This addendum does not commit the local packet or any raw provider/model payloads.

## Revised Case Classification

| Case | Original AG-47B read | Revised read | Main issue |
|---|---|---|---|
| Q1 TCO | Partial | Partial / weak but honestly caveated | Retrieval breadth and source fit; Tesla-side evidence missing. |
| Q2 Roth IRA | Good | Material factual/numeric error | Official IRS retrieval/source fit looked good, but answer synthesis/extraction gave wrong 2026 limits and one MFJ phaseout range. |
| Q3 Artemis II | Weak | Core status mostly right, sourcing/citation survival poor | NASA official mission status should have anchored the answer; reputable news can still provide context. |
| Q4 PKM tools | Acceptable | Mostly good with source-coverage caveats | Useful comparison, but some Notion/Obsidian/Capacities claims needed stronger official-source support. |

## Q2 Correction

The AG-47B note characterized Q2 as good because the final answer used official IRS sources and directly compared 2026 and 2025 Roth IRA limits and phaseouts.

Post-merge review found this is too generous.

The generated answer stated:

- 2026 base IRA contribution limit: `$7,000`
- 2026 age 50+ practical limit: `$8,000`
- 2026 married filing jointly Roth IRA phaseout: `$240,000-$250,000`

Current IRS sources instead state:

- 2026 IRA contribution limit increased to `$7,500`
- 2026 age 50+ total is `$8,600`, including a `$1,100` catch-up contribution for those age 50 and over
- 2026 Roth IRA married filing jointly phaseout is `$242,000-$252,000`

Therefore Q2 should be treated as:

```text
Official-source retrieval/source fit succeeded, but answer synthesis / numeric extraction failed.
```

This is an answer-accuracy issue. It is not primarily evidence that AG-47A batch dispatch failed.

Reference URLs checked:

- IRS IRA contribution limits: https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-topics-ira-contribution-limits
- IRS 2026 retirement plan limits release: https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500

## Q3 Source-Mix Clarification

The AG-47B note correctly flagged Q3 as weak for official/current NASA source fit. The final answer used reputable news and local/off-domain sources, and no official NASA mission page appeared in the final citation list.

Post-merge review found the core status claim was mostly right: NASA's official Artemis II mission page identifies Artemis II as launched April 1, 2026, splashed down April 10, 2026, and completed a 9-day crewed lunar flyby.

The issue is not that reputable news is bad by default. The better lesson is:

```text
For current-event/status questions:
  use official/primary sources when they determine status, rules, dates, legal effect, or authoritative claims;
  use reputable journalism for chronology, context, explanation, and independent reporting;
  prefer a mix when both are available.
```

For Artemis II, NASA should have anchored mission status and dates. NBC/NPR/Axios-style reporting could still be useful for context, public reaction, imagery, and explanatory chronology.

Reference URL checked:

- NASA Artemis II mission page: https://www.nasa.gov/mission/artemis-ii/

## Q1 And Q4 Notes

Q1 remains a retrieval breadth/source-fit issue, not a reason to tune provider/routing behavior immediately. The answer appropriately avoided fabricating a complete Tesla-side TCO, but a stronger run should have retrieved and integrated current Tesla pricing/efficiency, California electricity-rate assumptions, and clean-vehicle-credit status.

Q4 remains mostly acceptable for a recommendation/comparison answer. The source mix should improve for official product claims, but the answer was directionally useful and the quality issue is not urgent architecture evidence.

## Follow-Up Priorities

Carry these forward as product-quality backlog / future review priorities:

1. Numeric extraction/synthesis accuracy for official-source financial/tax answers.
2. Source mix and citation survival for official-current status answers.
3. Retrieval breadth for multi-factor comparisons.
4. Projection/dispatch trace consistency for Q3-style evaluator ordinary continuation after currentness/source-class blockers are present.
5. Do not infer provider/routing failure from these four cases alone.

## Non-Actions

Do not immediately add:

- IRS-specific answer logic;
- NASA-specific retrieval logic;
- source-ranking hacks;
- primary-source-only rules;
- legal/current detour;
- prompt rewrites based on one four-query batch;
- provider/routing/depth/query-generation changes.

These would overfit to one small validation round.

## Revised AG-47B Decision

AG-47B remains:

```text
pass_with_followup
```

Revised interpretation:

- AG-47A active batch dispatch remains acceptable from a protected-surface and architecture perspective in this bounded review.
- The output-quality evidence is meaningfully uneven.
- Q2 is a material answer-synthesis/numeric-extraction failure despite official-source availability.
- Q3 is a source-mix/citation-survival issue rather than proof that reputable news is categorically unsuitable.
- These issues should inform later product-quality and answer-contract/extraction work, but should not derail the controller/batch architecture lane.

## Recommended Next Main-Lane Action

Continue with the focused architecture follow-up already identified by AG-47B:

```text
AG-47C — Projection / Dispatch Consistency Follow-up
```

Purpose:

- investigate the Q3-style mismatch where dispatch authorized evaluator ordinary continuation while the top-level projection summary reported blocked/no selected lane;
- keep the scope to trace/projection/dispatch consistency;
- do not patch answer quality or source preference based on one validation batch.
