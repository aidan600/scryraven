# Official Numeric Source Grounding AG-48A

Date: May 24, 2026

Status: architecture and diagnostic contract only.

Scope: AG-48A defines an offline diagnostic contract for official/current
numeric and status-source failures. It does not change provider routing,
provider selection, search depth, query generation, ranking, prompts, source
classification, evidence visibility, controller dispatch, Economist behavior,
Analyst handoff, Author behavior, final-answer posture, or live validation.

## 1. Problem Statement

AG-47A through AG-47D left the controller/batch-dispatch lane in a good
architecture state: ordinary evaluator, expander, and scout continuation can be
represented and authorized without creating a new provider role or executor, and
AG-47C reconciled the visible projection/dispatch trace inconsistency observed
in AG-47B.

That trace correctness is not the same as product answer correctness. Recent
review still found official/current numeric and status answers failing after the
batch-dispatch architecture looked sane. AG-48A treats those failures as a
source-grounding and value-preservation diagnosis problem, not as proof that
batch dispatch is broken.

The core diagnostic question is:

```text
When a numeric/current/status answer fails, did the failure occur at source
need detection, source acquisition, source acceptance, source survival into
final evidence, citation/source fit, numeric extraction, Economist
invocation/use, or final synthesis?
```

## 2. Failure-Layer Taxonomy

Use these labels to classify sanitized review artifacts. They are diagnostic
labels, not runtime control-flow states.

| Layer | Diagnostic label | Meaning | Typical next lane |
| --- | --- | --- | --- |
| Source need detection | `source_need_not_detected` | The question required an official/current or canonical source, but the sanitized trace did not show that need as an obligation. | source acquisition/survival lane |
| Acquisition | `official_current_source_not_acquired` | The answer turned on exact current status, dates, eligibility, legal effect, program amounts, or numeric thresholds, but no fitting official/current source was acquired. | source acquisition/survival lane |
| Acceptance | `official_current_source_acquired_not_accepted` | A fitting official/current source appeared in sanitized acquisition evidence but was not accepted as relevant evidence. | source acquisition/survival lane |
| Survival | `official_current_source_not_visible_in_final_evidence` | A fitting source was acquired and accepted, but it did not survive into the final evidence set visible to synthesis/review. | source acquisition/survival lane |
| Citation/source fit | `official_current_source_visible_not_cited` | The source survived into final evidence but was not cited or was displaced by weaker source fit. | source-fit/citation survival lane |
| Numeric extraction | `correct_source_cited_wrong_number_extracted` | The cited source was appropriate, but the extracted value, range, date, unit, or comparison was wrong or absent. | numeric extraction/source-bound value lane |
| Source-bound value | `numeric_value_not_source_bound` | A value was extracted, but the sanitized artifact did not show a stable binding to the cited source, unit, period, or entity. | numeric extraction/source-bound value lane |
| Final synthesis | `correct_number_extracted_but_distorted_final` | The source-bound value was available upstream, but the final answer restated, rounded, compared, or scoped it incorrectly. | Author synthesis/value preservation lane |
| Economist invocation | `economist_eligible_not_invoked` | The query was numeric-sensitive and Economist was eligible, but sanitized telemetry showed it did not run. | Economist invocation/preflight lane |
| Economist evidence use | `economist_invoked_with_weak_or_wrong_evidence` | Economist ran, but the sanitized terms of the evidence it received lacked the source-bound values needed for the answer. | Economist handoff/use lane |
| Economist downstream use | `economist_correct_but_ignored_or_distorted_downstream` | Economist produced valid source-bound values, but Analyst/Author did not preserve them. | Author synthesis/value preservation lane |
| Correct caveat | `answer_correctly_caveated_missing_evidence` | The answer declined or caveated because required evidence was missing. This is a product incompleteness signal, but not a hallucination failure. | source acquisition/survival lane or no action if caveat behavior is the desired endpoint |

## 3. Numeric/Status Question Types

AG-48A covers question families where exact source grounding matters:

- tax, retirement, and benefit thresholds;
- government program amounts, eligibility amounts, payment levels, credits, and
  phaseouts;
- current mission, operational, outage, investigation, launch, filing, or
  program status questions;
- cost, total cost of ownership, and multi-factor comparison questions;
- policy, incentive, deadline, eligibility, legal-effect, and effective-date
  questions;
- technical reference questions where canonical docs determine the answer.

The taxonomy is intentionally source-agnostic. It must not create IRS-specific,
SSA-specific, NASA-specific, Tesla-specific, heat-pump-specific, or
SQLite-specific behavior.

## 4. Source Expectations

AG-48A does not create a primary-source-only policy.

Reputable news and expert secondary sources can be high-quality evidence for
current-event context, chronology, explanation, practical interpretation,
independent reporting, tradeoffs, and user-facing synthesis. They are often the
right complement to official sources.

Official, primary, or canonical sources are required when the answer turns on:

- exact current status;
- exact date, deadline, phase, milestone, or effective date;
- eligibility, legal effect, program rule, or agency requirement;
- program amount, benefit amount, threshold, cap, phaseout, credit, or penalty;
- canonical technical behavior or documented limits.

Best source mix by case:

| Case shape | Expected source posture |
| --- | --- |
| Exact government amount or threshold | Official source anchors values; reputable explainers may add context. |
| Current mission or operational status | Official source anchors status and milestones; reputable news adds chronology and context. |
| Cost/TCO comparison | Use current source coverage for each major variable; official incentives/rates where they determine eligibility or dollar amounts; reputable market sources for price context where official sources do not exist. |
| Technical reference answer | Canonical docs anchor normative behavior; secondary sources can explain tradeoffs. |
| Recommendation/comparison without exact status or legal effect | Reputable secondary evidence may be enough, with primary sources for central product claims when available. |

## 5. Economist Diagnostic Questions

These questions define what future sanitized review should ask. They do not
change Economist eligibility, preflight, execution, schema validation, or
handoff behavior.

- Was the query numeric-sensitive?
- Was Economist eligible under existing policy?
- Did Economist run?
- What evidence did Economist receive, described only in sanitized source-class,
  source-id, metric, unit, period, and entity terms?
- Did Economist produce source-bound values?
- Were those values valid, cited, and tied to the right source, entity, unit,
  and period?
- Did Analyst/Author use those values?
- Did Analyst/Author distort values, units, periods, caveats, or comparisons?
- Was Economist skipped for a valid reason, such as missing explicit evidence,
  weak corpus, high-stakes blockers, or non-quantitative query shape?

Required guardrail: raw Economist framework text, raw `economist_v1` JSON, raw
`quantitative_packet`, prompts, provider payloads, and full traces remain out of
committed artifacts.

## 6. Scout Diagnostic Questions

These questions define how to review scout-directed retrieval without changing
Scout or controller dispatch.

- Did Scout identify the missing official/current numeric source need?
- Did Scout-directed queries target the right source class in sanitized terms?
- Did the resulting sources enter accepted evidence?
- Did those sources survive into final evidence?
- Were they cited when they determined exact status or numeric values?
- Did Scout add cost without improving source grounding?
- Did Scout produce useful secondary context while still missing the official
  anchor?

AG-48A must not convert these questions into new query-generation rules, source
ranking, source-classification behavior, or provider-depth changes.

## 7. Reference Case Mapping

The cases below are representative patterns only. They are not special cases
and must not create source-specific adapters or tuning.

| Reference pattern | Representative failure layer |
| --- | --- |
| AG-47B Roth IRA | Official IRS source was available and cited, but final values were wrong. Classify as numeric extraction or final synthesis depending on whether source-bound values existed upstream. |
| AG-47D SSA | Official SSA sources were findable, but they did not survive into the final answer; the answer safely refused to state unsupported numbers. Classify as acquisition/survival with correct caveat posture. |
| Artemis/Starliner-style current status | Official NASA source should anchor exact mission/status/milestone claims; reputable news may add context. Classify by whether official source was acquired, survived, and cited. |
| TCO/heat-pump examples | Multi-factor numeric comparisons require source coverage for both sides and current incentives/rates. Classify missing variables separately from bad extracted values. |
| SQLite WAL | Canonical SQLite docs should anchor technical reference behavior; secondary explanations may help users understand tradeoffs. Classify missing canonical citation as source-fit/citation survival. |

## 8. Recommended Next Phase Categories

Future work should depend on the diagnostic outcome:

- Source acquisition/survival lane: use when official/current or canonical
  source needs are not detected, not acquired, not accepted, or do not survive
  into final evidence.
- Economist invocation/preflight lane: use when numeric-sensitive questions are
  eligible for Economist but skipped without a valid sanitized reason.
- Numeric extraction/source-bound value lane: use when the right source is cited
  but values, units, periods, entities, or source bindings are wrong or missing.
- Author synthesis/value preservation lane: use when correct source-bound values
  existed upstream but the final answer distorted or ignored them.
- Source-fit/citation survival lane: use when correct sources were visible but
  not cited, or weaker sources displaced the authoritative anchor.
- No action / caveat behavior acceptable: use only when the product goal is to
  decline or caveat rather than spend more retrieval or synthesis budget.

## 9. Non-Authorization

This document does not authorize:

- live ProPlex/provider/model/search calls;
- provider routing, selection, depth, or escalation changes;
- query-generation changes;
- source-ranking, source classification, or evidence-visibility behavior
  changes;
- prompt changes;
- Economist, Analyst, Author, or controller handoff changes;
- legal/current retrieval repair;
- runtime dispatch or controller authority changes;
- committing raw logs, caches, prompts, provider payloads, DB rows, secrets,
  output packets, or full traces.
