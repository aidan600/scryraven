# Official Source Acquisition Survival AG-48B

Date: May 24, 2026

Status: architecture and diagnostic contract only.

Scope: AG-48B defines an offline diagnostic layer for classifying where
required official, current, or canonical sources disappear before final answer
synthesis. It does not change retrieval, provider routing, provider selection,
provider depth, query generation, ranking, source classification runtime
behavior, evidence visibility, prompts, Economist behavior, Analyst/Author/
Scrutineer handoffs, final-answer behavior, controller dispatch/runtime
authority, legal/current retrieval repair, source-specific adapters, or live
validation.

## 1. Problem Statement

AG-47C and AG-47D showed that dispatch/projection can look sane while product
answers still fail on official/current/canonical source grounding. In those
cases, the system may have detected the need, generated plausible follow-up
queries, and still lost the source before extraction or synthesis.

AG-48B treats this as a source acquisition and survival diagnosis problem. The
phase asks:

```text
When an official/current/canonical source is required, where does it disappear?
```

This phase diagnoses disappearance stages. It does not repair answer generation,
numeric extraction, retrieval behavior, ranking, classification, evidence
visibility, or handoffs.

## 2. Source Obligation Taxonomy

Use these categories as source-obligation labels in sanitized review artifacts:

| Obligation | Meaning |
| --- | --- |
| Official/current government/legal source | Agency, regulator, legislature, court, statute, regulation, official program, or legal source needed for current rule, eligibility, deadline, legal effect, amount, or status. |
| Canonical technical documentation | Project, vendor, standards, protocol, API, or primary documentation needed for normative technical behavior. |
| Official program/fact-sheet source | Program owner, public authority, benefits administrator, or official fact sheet needed for amounts, dates, eligibility, participation, or program status. |
| Official mission/status source | Mission owner, agency, operator, issuer, or official status page needed for operational status, milestones, dates, or official position. |
| Reputable news/current-event context | High-quality journalism or expert reporting useful for chronology, context, explanation, independent reporting, and current-event framing. |
| Secondary analysis/commentary | Expert analysis, explainers, reviews, trade publications, or community material useful for interpretation, comparison, and user-facing synthesis when exact authority is not required. |

## 3. Acquisition/Survival Stage Model

Classify the earliest material stage where the required source failed to
survive:

1. Source obligation detected.
2. Candidate query generated or available.
3. Provider/search candidates returned.
4. Candidate accepted/readable.
5. Source-class/canonical classification assigned.
6. Included in final evidence.
7. Cited in final answer.

For numeric/status failures, also record whether a cited source survived but the
numeric/status value, unit, period, entity, or binding failed downstream.

## 4. Bottleneck Classes

| Bottleneck | Meaning |
| --- | --- |
| `obligation_not_detected` | Required official/current/canonical source obligation was not recognized. |
| `no_candidate_query` | Obligation was detected, but no candidate query was generated or available. |
| `no_official_candidates_returned` | Queries existed, but no official/current/canonical candidates appeared. |
| `official_candidate_rejected_or_unreadable` | Candidate appeared but was rejected, inaccessible, unreadable, or not accepted. |
| `official_candidate_misclassified` | Candidate appeared but failed source-class/canonical classification. |
| `accepted_source_dropped_before_final_evidence` | Accepted source did not survive into final evidence. |
| `final_evidence_source_not_cited` | Source survived into final evidence but was not cited in the answer. |
| `citation_survived_but_value_extraction_failed` | Correct source was cited, but numeric/status extraction or source binding failed. |
| `answer_correctly_caveated_missing_source` | Required source was missing and the answer caveated/refused instead of fabricating. |
| `not_a_source_acquisition_failure` | No required source obligation existed, or the required source survived the acquisition/citation path. |

## 5. Representative Patterns

These are patterns only. They must not create source-specific adapters, hacks,
ranking rules, query rules, or prompt behavior.

| Pattern | Diagnostic interpretation |
| --- | --- |
| SSA-style program amount/fact-sheet source missing from final evidence | Diagnose whether official program/fact-sheet sources were not detected, not queried, not returned, rejected, misclassified, or dropped before final evidence. |
| IRS-style official source present but numeric extraction/synthesis wrong | If the official source survived and was cited, classify source acquisition as survived and route value errors to numeric extraction/source-bound value work. |
| NASA/Starliner-style current status | Official mission/status source should anchor exact status, dates, and milestones; reputable news may add chronology and context. |
| SQLite-style technical reference | Canonical documentation should anchor normative behavior; secondary explanations can help with accessibility and tradeoffs. |
| TCO-style multi-factor comparison | Official/current sources may be required for incentives, regulated rates, tax credits, eligibility, or program amounts, but not every factor has a single primary source. |

## 6. Good Source Mix Policy

AG-48B does not implement a primary-source-only policy.

Official, primary, or canonical sources should anchor exact status, numbers,
dates, eligibility, deadlines, legal effect, program amounts, or technical
behavior. Reputable news can be high-quality evidence for current-event
chronology, context, explanation, and independent reporting. Secondary analysis
and commentary can be appropriate for interpretation, tradeoffs, comparison, and
user-facing synthesis.

The expected policy is source-fit, not source purity: use authoritative sources
where they determine exact claims, and use reputable context sources where they
add explanatory value.

## 7. Future Sanitized Validation Fields

Future local output-quality packets may add compact fields such as:

- `required_source_obligation`
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

These are future packet fields. AG-48B does not wire them into runtime,
telemetry production, retrieval, synthesis, prompts, or controller behavior.

## 8. Non-Authorization

This document does not authorize:

- live ProPlex/provider/model/search calls;
- provider routing, selection, depth, or escalation changes;
- query-generation changes;
- source-ranking, source-classification, or evidence-visibility behavior
  changes;
- prompt changes;
- Economist, Analyst, Author, Scrutineer, or controller handoff changes;
- legal/current retrieval repair;
- runtime dispatch or controller authority changes;
- source-specific adapters or source-specific special cases;
- committing raw logs, caches, prompts, provider payloads, DB rows, secrets,
  output packets, or full traces.
