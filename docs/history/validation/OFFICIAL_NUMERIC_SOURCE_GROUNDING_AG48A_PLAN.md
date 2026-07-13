Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (OFFICIAL_NUMERIC_SOURCE_GROUNDING_AG48A_PLAN).

# Official Numeric Source Grounding AG-48A Validation Plan

Date: May 24, 2026

Status: offline diagnostic validation plan. No live validation is authorized by
this document.

## Purpose

Future validation should classify official/current numeric and status-source
failures using sanitized artifacts only. The goal is to identify the failure
layer before any repair phase changes retrieval, ranking, prompts, Economist,
handoffs, or final-answer behavior.

## Test Question Classes

Use a balanced set of question shapes. Do not overfit to one source, agency,
vendor, or example.

| Class | Expected source obligation |
| --- | --- |
| Tax/retirement/benefit thresholds | Official source required for exact limits, phaseouts, eligibility, dates, and amounts. |
| Government program amounts | Official source required for payment levels, benefits, credits, deadlines, and legal effect. |
| Current mission/status questions | Official source required for exact status and milestone claims; reputable news acceptable for chronology and context. |
| Cost/TCO comparisons | Source coverage needed for major variables on both sides; official/current sources required for incentives, credits, and regulated rates when they determine dollar values. |
| Policy/incentive/deadline questions | Official/current source required for eligibility, date, amount, and legal-effect claims. |
| Technical canonical-reference questions | Canonical documentation should anchor normative technical behavior; secondary sources may explain. |

## Required Sanitized Trace Fields

A future local output-quality packet should include only compact, sanitized
fields such as:

- question class and whether official/current/canonical source was required;
- whether the source need was detected as an obligation;
- whether a fitting official/current/canonical source was acquired;
- whether it was accepted as relevant evidence;
- whether it survived into final evidence;
- whether it was cited in the final answer;
- source classes and source ids, not raw provider payloads;
- source titles/domains/URLs only when already visible in final answer or
  sanitized source sections;
- whether numeric values were extracted;
- whether values were source-bound by entity, metric, unit, period, and source
  id;
- whether final answer values mismatched source-bound values;
- whether a missing-evidence caveat was present;
- whether Economist was eligible;
- whether Economist ran;
- sanitized description of the evidence Economist received;
- whether Economist produced valid source-bound values;
- whether Analyst/Author used or distorted those values;
- dispatch/projection summary fields sufficient to confirm protected surfaces
  remained unchanged.

## Local Output-Quality Packet Contents

The ignored local packet should contain:

- the exact validation question text;
- final answer text or short excerpts only if already local and needed for
  review;
- final citation list visible to the user;
- sanitized source-fit notes;
- sanitized numeric value table with expected value, observed value, unit,
  period, source id, and mismatch label;
- sanitized Economist eligibility/run/use notes;
- sanitized Scout/source-class notes when scout-directed continuation occurred;
- bottleneck classification;
- recommended next lane;
- reviewer decision and rationale;
- deletion criteria.

The packet must stay under ignored `output/` or `outputs/` paths and must not be
committed unless a later phase explicitly scopes a sanitized summary.

## What Not To Inspect Or Commit

Do not inspect or commit:

- secrets, `.env`, API keys, credentials, local auth files, or DB rows;
- raw provider payloads;
- raw prompts;
- raw model messages;
- full raw traces;
- caches;
- generated reports outside the intended ignored packet;
- unredacted logs;
- output packets under `output/` or `outputs/`.

Do not run live validation unless a later phase explicitly grants budget and
scope.

## Classification Decision Rules

Classify the earliest material failure layer that explains the product failure,
then record downstream symptoms separately.

1. If official/current/canonical evidence was required but the need was not
   detected, classify `source_need_not_detected`.
2. If the need was detected but no fitting source was acquired, classify
   `official_current_source_not_acquired`.
3. If a fitting source was acquired but not accepted, classify
   `official_current_source_acquired_not_accepted`.
4. If it was accepted but not visible in final evidence, classify
   `official_current_source_not_visible_in_final_evidence`.
5. If it was visible but not cited for exact claims, classify
   `official_current_source_visible_not_cited`.
6. If the right source was cited but values were wrong, absent, or unbound,
   classify numeric extraction/source-bound value failure.
7. If correct source-bound values existed but the final answer distorted them,
   classify Author synthesis/value preservation failure.
8. If the numeric-sensitive query was eligible for Economist but Economist did
   not run, classify Economist invocation/preflight failure.
9. If Economist ran without the needed source-bound evidence, classify
   Economist evidence-use failure.
10. If Economist produced valid source-bound values that were ignored or
    distorted downstream, classify downstream handoff/synthesis failure.
11. If required evidence was missing and the answer clearly caveated or refused
    unsupported numbers, record correct caveat posture. This may still point to
    acquisition/survival work if the product goal requires a complete answer.

## Next-Work Mapping

| Bottleneck | Recommended next work |
| --- | --- |
| Need not detected, source not acquired, source not accepted, source not visible | AG-48B source acquisition/survival diagnostics or repair design. |
| Source visible but not cited | Citation/source-fit survival diagnostics. |
| Values absent, wrong, unbound, or mismatched before final synthesis | Numeric extraction/source-bound value diagnostics. |
| Economist eligible but skipped | Economist invocation/preflight diagnostics. |
| Economist ran with weak/wrong evidence | Economist handoff/use diagnostics. |
| Correct source-bound values distorted in final answer | Author synthesis/value preservation diagnostics. |
| Missing evidence caveated correctly | No action if caveat is acceptable; otherwise source acquisition/survival work. |

## Protected-Surface Guardrails

Validation must confirm no changes to:

- provider routing, provider selection, provider depth, provider escalation;
- prompts;
- source classification runtime behavior;
- source ranking or runtime dominance;
- evidence visibility behavior;
- Economist execution or handoff behavior;
- Analyst/Author handoff behavior;
- final-answer posture/runtime behavior;
- controller action execution/runtime authority;
- legal/current adapter implementation.

## Phase Exit Criteria

An AG-48 validation round is ready to inform repair work only when each case has:

- question class;
- expected source obligation;
- sanitized source lifecycle classification;
- sanitized value extraction/source-binding classification;
- sanitized Economist eligibility/run/use classification;
- final synthesis/caveat classification;
- one recommended next lane;
- a statement that no raw/private/generated artifacts were committed.
