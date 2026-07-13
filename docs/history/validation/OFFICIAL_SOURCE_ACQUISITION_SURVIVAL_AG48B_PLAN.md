Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (OFFICIAL_SOURCE_ACQUISITION_SURVIVAL_AG48B_PLAN).

# Official Source Acquisition Survival AG-48B Validation Plan

Date: May 24, 2026

Status: offline diagnostic validation plan. No live validation is authorized by
this document.

## Purpose

Future validation should classify where required official/current/canonical
sources disappear using sanitized artifacts only. The goal is to decide the next
repair lane without changing retrieval, ranking, source classification, prompts,
handoffs, evidence visibility, or final-answer behavior in AG-48B.

## Validation Question Classes

| Class | Expected source obligation |
| --- | --- |
| Government/legal current rules | Official/current government or legal source required for eligibility, legal effect, effective dates, deadlines, amounts, and rules. |
| Program amounts and fact sheets | Official program/fact-sheet source required for benefit amounts, payment levels, thresholds, credits, and public program status. |
| Mission or operational status | Official mission/status source required for exact status, milestones, dates, and official position; reputable news may add context. |
| Canonical technical reference | Canonical documentation required for normative technical behavior, limits, API semantics, or documented tradeoffs. |
| Current-event explanation | Reputable news may be sufficient for chronology and context, but official/primary sources are required for exact legal/current/status effects. |
| Multi-factor comparison or TCO | Official/current sources required for incentives, regulated rates, tax credits, eligibility, or program amounts; reputable market and expert sources may cover other factors. |

## Sanitized Packet Fields

A later local output-quality packet should include compact fields only:

- `question_type`
- `required_source_obligation`
- `source_obligation_required`
- `obligation_detected`
- `candidate_query_count`
- `candidate_official_or_canonical_count`
- `accepted_official_or_canonical_count`
- `final_evidence_official_or_canonical_count`
- `final_citation_official_or_canonical_count`
- `candidate_misclassified`
- `missing_stage`
- `caveat_present`
- `numeric_value_mismatch`
- `recommended_next_lane`
- source classes, source ids, domains, and URLs only when already visible in
  final answer or sanitized source sections

Do not include raw provider payloads, raw prompts, raw model messages, full raw
traces, DB rows, secrets, caches, or unredacted logs.

## Classification Rules

Classify the earliest material disappearance stage:

1. If no official/current/canonical source was required, classify
   `not_a_source_acquisition_failure`.
2. If the source obligation was required but not detected, classify
   `obligation_not_detected`.
3. If the obligation was detected but no candidate query existed, classify
   `no_candidate_query`.
4. If candidate queries existed but no official/current/canonical candidates
   returned, classify `no_official_candidates_returned`.
5. If missing candidates were clearly caveated and there was no numeric/status
   value mismatch, classify `answer_correctly_caveated_missing_source`.
6. If candidates returned but no official/current/canonical candidate was
   accepted, classify `official_candidate_rejected_or_unreadable`.
7. If candidate classification was the blocker, classify
   `official_candidate_misclassified`.
8. If an accepted source did not reach final evidence, classify
   `accepted_source_dropped_before_final_evidence`.
9. If final evidence included the source but the final answer did not cite it,
   classify `final_evidence_source_not_cited`.
10. If the citation survived but the value, status, unit, period, entity, or
    binding failed, classify `citation_survived_but_value_extraction_failed`.
11. Otherwise classify `not_a_source_acquisition_failure` and route no action
    for this lane.

## Later Local Output-Quality Packet

In a later live/local validation phase, the ignored local packet should include:

- exact validation question text;
- final answer text or short excerpts only if already local and needed for
  review;
- final citation list visible to the user;
- sanitized source-obligation classification;
- sanitized candidate/acquisition/acceptance/final-evidence/final-citation
  counts;
- sanitized notes explaining the selected missing stage;
- caveat and numeric/status mismatch flags;
- recommended next lane;
- protected-surface summary;
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

## Decision Rules For Next Phase

| Diagnostic outcome | Recommended next phase |
| --- | --- |
| `obligation_not_detected` | Source-obligation detection design. |
| `no_candidate_query` | Candidate-query availability design. |
| `no_official_candidates_returned` | Source acquisition design, without changing provider/routing/depth until explicitly scoped. |
| `official_candidate_rejected_or_unreadable` | Acceptance/readability diagnostics. |
| `official_candidate_misclassified` | Source-class/canonical classification diagnostics. |
| `accepted_source_dropped_before_final_evidence` | Evidence survival/visibility diagnostics. |
| `final_evidence_source_not_cited` | Citation/source-fit survival diagnostics. |
| `citation_survived_but_value_extraction_failed` | Numeric/status extraction and source-bound value diagnostics. |
| `answer_correctly_caveated_missing_source` | No action if caveat is acceptable; otherwise source acquisition/survival work. |
| `not_a_source_acquisition_failure` | No action for AG-48B. |

## Protected-Surface Checks

Validation and tests must confirm no changes to:

- provider routing, provider selection, provider depth, or provider escalation;
- query generation;
- source ranking;
- source classification runtime behavior;
- evidence visibility behavior;
- prompts;
- Economist behavior;
- Analyst/Author/Scrutineer handoffs;
- final-answer behavior;
- controller dispatch/runtime authority;
- legal/current retrieval repair;
- live validation behavior.

## Phase Exit Criteria

AG-48B is complete when the repo contains:

- this validation plan;
- the architecture contract;
- a pure/offline helper with no protected-surface imports;
- fixture tests for each bottleneck class and caveat/source-mix behavior;
- required local checks showing AG-48B and nearby AG-48A guardrails still pass.
