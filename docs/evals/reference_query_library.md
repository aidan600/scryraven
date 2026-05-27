# Reference Query Library

Status: Phase 11a-doc. Classification: docs-only / eval-design-only.

This artifact is a human review aid. It does not authorize code, prompt,
routing, retrieval, provider-selection, source-filtering, Analyst, Economist,
Author, telemetry, replay, summarizer, SQLite, or weak-corpus behavior changes.

## Purpose

- Provide a human-readable review library for difficult and diverse searches.
- Help reviewers compare ProPlex output quality, parity gaps, differentiation
  opportunities, and failure classes.
- Keep reference-query review separate from benchmark harnesses, scoring,
  replay, and production policy.

This file is not a benchmark harness, scorer, replay layer, or production
policy file.

## Non-goals

- No golden answers.
- No raw transcripts.
- No expected final answer text.
- No competitor imitation.
- No live query instructions.
- No query-specific production routing, filtering, or synthesis rules.

## Review Workflow

1. Add or maintain a reference query.
2. Record the category and intended challenge.
3. Record expected evidence shape, not the expected answer.
4. Add compact comparison notes only after separately approved live comparisons.
5. Classify failures by general mechanism.
6. Map any follow-up work to retrieval, synthesis, UX, telemetry, test-only, or
   no-change.
7. Require separate Rule 0 analysis and explicit approval for any future
   behavior-changing fix.

## Reference Query Schema

| Field | Meaning |
| --- | --- |
| `id` | Stable record ID, such as `RQ-001`. |
| `status` | Lifecycle state: `active`, `refresh_needed`, `retired`, or `draft`. |
| `query` | The reference query text. |
| `category` | Primary category from `docs/eval_queries.md`. |
| `secondary_tags` | Optional compact tags for cross-cutting traits. |
| `freshness_requirement` | `none`, `low`, `medium`, `high`, `date_bound`, or `inherited`. |
| `query_type_hint` | Human hint such as `person`, `news`, `product`, `academic`, `quantitative`, `concept`, `place`, `ambiguous`, or `followup`. |
| `report_type_hint` | Human hint such as `summary`, `how_to`, `comparison`, `technical`, `broad_overview`, or `followup`. |
| `mode_coverage` | Suggested review modes, such as `Fast`, `Balanced`, `Deep`, or `followup_thread`. |
| `intended_challenge` | What the query is meant to stress. |
| `expected_evidence_shape` | Expected source pattern, not expected answer text. |
| `source_expectations` | Notes about source tier, diversity, recency, or official-source needs. |
| `quality_observation_prompts` | Reviewer prompts for judging answer quality without scoring against a golden answer. |
| `telemetry_probes` | General telemetry fields or diagnostics worth inspecting. |
| `likely_failure_classes` | Stable likely failure labels from the taxonomy below. |
| `comparison_notes` | Compact qualitative notes after approved comparisons, or `not_run`. |
| `parity_notes` | Notes about parity gaps or no-change cases. |
| `differentiation_notes` | Notes about valid ways ProPlex may differ. |
| `mapped_work_type` | `retrieval`, `synthesis`, `UX`, `telemetry`, `test-only`, `no-change`, or `unset`. |
| `forbidden_uses` | Record-specific reminders of disallowed uses. |
| `added_at` | Date the record was added or imported. |
| `reviewed_at` | Most recent review date, or `not_reviewed`. |

`freshness_requirement: inherited` is for follow-up records. It means the
record inherits freshness from the approved prior thread/context; it is not a
standalone live-query freshness instruction.

`comparison_notes: not_run` means no approved comparison has been performed or
summarized. It is not a pass, fail, stale, parity, or approval-to-run marker.

## Comparison-output Handling Rules

Allowed:

- Compact qualitative notes.
- Source-shape observations.
- Citation and UX observations.
- Uncertainty and caveat observations.
- Parity and differentiation notes.

Allowed compact `comparison_notes` example:

`reviewed YYYY-MM-DD; approved manual comparison; source_shape=<brief>; observation=<brief>; parity=<parity_gap|valid_differentiation|mixed_case|no_change>; failure_classes=[...]; no_behavior_authorized`

Forbidden:

- Raw outputs.
- Raw transcripts.
- Golden answers.
- Expected final answer text.
- Full model outputs.
- Provider payloads.
- Raw prompts.
- Exact competitor wording as a target.
- Numeric correct answers.
- Query-specific production rules.

## Parity vs Differentiation

- `parity_gap`: ProPlex misses a general capability users reasonably expect,
  such as current official evidence, clear caveats, or readable citations.
- `valid_differentiation`: ProPlex differs in tone, structure, source selection,
  or caution in a way that is useful, safe, and not merely a defect.
- `mixed_case`: A review shows both a parity gap and a valid differentiation
  opportunity. Split any follow-up into general mechanisms.
- `no_change`: The observed difference should not drive work, usually because it
  reflects competitor style, unsupported evidence, or a query-specific quirk.

## Failure Taxonomy

- `retrieval.entity_collision`
- `retrieval.low_utilization`
- `retrieval.stale_corpus`
- `retrieval.source_tier_mismatch`
- `retrieval.official_source_missing`
- `retrieval.generic_news_dominance`
- `synthesis.unsourced_claim`
- `synthesis.overconfident_weak_evidence`
- `synthesis.numeric_unsupported`
- `synthesis.entity_conflation`
- `ux.failure_copy_jargon`
- `ux.citation_scanability`
- `ux.export_markdown`
- `ux.table_readability`
- `followup.context_drift`
- `telemetry.missing_diagnostic`
- `test_only.regression_guard`
- `no_change.competitor_style_difference`

## Failure-to-work-type Mapping

- `retrieval`: Use when the main failure is finding, ranking, freshness,
  source-tier selection, entity disambiguation, or corpus utilization.
- `synthesis`: Use when adequate evidence exists but the answer overclaims,
  conflates entities, omits caveats, or introduces unsupported numeric or factual
  claims.
- `UX`: Use when the answer is materially correct enough but hard to scan,
  poorly cited, overly jargony in failure mode, difficult to export, or poorly
  formatted for the report type.
- `telemetry`: Use when reviewers cannot diagnose the mechanism from existing
  logs or summary fields.
- `test-only`: Use for regression guards around already-correct behavior or
  documented contracts, without changing runtime behavior.
- `no-change`: Use when the observation is only a competitor style difference,
  a one-off preference, or unsupported by enough evidence to justify work.

## Maintenance / Review Status Guidance

- `active`: Usable as a human review aid if otherwise appropriate.
- `refresh_needed`: Stale, placeholder, or date-bound record needs human
  refresh before review.
- `retired`: No longer useful or superseded.
- `draft`: Incomplete or not ready.
- `reviewed_at: not_reviewed`: No human review has occurred.

## Manual Review Batch Guidance

- Smallest useful batch: 3 records, capped at 5.
- Include one high/date-bound record, one medium/current product or policy
  record, and one evergreen negative control.
- Avoid follow-up records unless an approved, scrubbed prior thread exists.

## Reference Query Records

Each record below is seeded from `docs/eval_queries.md`. Records intentionally
avoid expected final answers, model outputs, provider payloads, raw prompts, raw
comparison transcripts, and query-specific production rules.

```yaml
- id: RQ-001
  status: active
  query: "Scott Galloway controversy"
  category: "Person / disambiguation"
  secondary_tags: [person, controversy, ambiguity, recency]
  freshness_requirement: high
  query_type_hint: person
  report_type_hint: summary
  mode_coverage: [Fast, Balanced, Deep]
  intended_challenge: "Disambiguate a public person query with controversy and recency pressure."
  expected_evidence_shape: "Recent, entity-specific sources plus background sources that clearly refer to the same person."
  source_expectations: "Avoid unrelated same-name results; prefer direct reporting and primary context where available."
  quality_observation_prompts: ["Does the answer identify the entity clearly?", "Are caveats tied to source recency and strength?"]
  telemetry_probes: [query_type, primary_entity, utilization_rate, waste_flags, source_date_span]
  likely_failure_classes: [retrieval.entity_collision, retrieval.stale_corpus, synthesis.overconfident_weak_evidence]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No golden answer, raw transcript, competitor wording target, or query-specific routing rule."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-002
  status: active
  query: "Taylor Swift ticket policy Europe 2026"
  category: "Person / disambiguation"
  secondary_tags: [person, policy, Europe, date_bound]
  freshness_requirement: date_bound
  query_type_hint: person
  report_type_hint: summary
  mode_coverage: [Fast, Balanced, Deep]
  intended_challenge: "Combine entity precision with date-bound regional policy evidence."
  expected_evidence_shape: "Current official ticketing, venue, promoter, or regulator sources, with region-specific reporting if needed."
  source_expectations: "Separate official policy details from fan discussion or SEO summaries."
  quality_observation_prompts: ["Does it distinguish Europe-specific policy from global touring information?", "Are dates and policy scope sourced?"]
  telemetry_probes: [query_type, primary_entity, source_date_span, waste_flags]
  likely_failure_classes: [retrieval.official_source_missing, retrieval.source_tier_mismatch, retrieval.stale_corpus]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No expected answer text, ticketing control-flow rule, or raw live comparison transcript."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-003
  status: active
  query: "Sam Altman OpenAI board history summary"
  category: "Person / disambiguation"
  secondary_tags: [person, organization, timeline, governance]
  freshness_requirement: medium
  query_type_hint: person
  report_type_hint: summary
  mode_coverage: [Fast, Balanced, Deep]
  intended_challenge: "Summarize a high-profile governance timeline without flattening source disagreement."
  expected_evidence_shape: "A mix of official posts, reputable reporting, and timeline-oriented sources with clear chronology."
  source_expectations: "Prefer sources that distinguish board events, dates, and roles."
  quality_observation_prompts: ["Is the timeline coherent?", "Are contested or uncertain claims caveated?"]
  telemetry_probes: [query_type, primary_entity, source_count, citation_count, source_date_span]
  likely_failure_classes: [synthesis.entity_conflation, synthesis.unsourced_claim, ux.citation_scanability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No raw prompts, full outputs, or final-answer template."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-004
  status: refresh_needed
  query: "latest on [current major news topic - replace quarterly]"
  category: "News / recency"
  secondary_tags: [news, placeholder, recency, refresh]
  freshness_requirement: high
  query_type_hint: news
  report_type_hint: summary
  mode_coverage: [Fast, Balanced, Deep]
  intended_challenge: "Exercise latest-news behavior with a quarterly refreshed real topic."
  expected_evidence_shape: "Very recent reputable reporting and official statements when applicable."
  source_expectations: "Use an actual approved topic before review; avoid stale generic background dominance."
  quality_observation_prompts: ["Does the corpus match the current topic?", "Is freshness visible and caveated?"]
  telemetry_probes: [intent, query_type, source_date_span, newest_source_age, waste_flags]
  likely_failure_classes: [retrieval.stale_corpus, retrieval.generic_news_dominance, telemetry.missing_diagnostic]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No live query in this pass; no production news-routing rule from this placeholder."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-005
  status: active
  query: "breaking news White House today"
  category: "News / recency"
  secondary_tags: [news, today, institution, recency]
  freshness_requirement: high
  query_type_hint: news
  report_type_hint: summary
  mode_coverage: [Fast, Balanced, Deep]
  intended_challenge: "Test same-day recency, official-source availability, and uncertainty handling."
  expected_evidence_shape: "Recent reputable news plus official White House or agency material when relevant."
  source_expectations: "Avoid generic White House background pages dominating breaking-news evidence."
  quality_observation_prompts: ["Does it avoid overclaiming from early reports?", "Are official and news sources separated clearly?"]
  telemetry_probes: [source_date_span, newest_source_age, waste_flags, retrieval_passes]
  likely_failure_classes: [retrieval.stale_corpus, retrieval.generic_news_dominance, synthesis.overconfident_weak_evidence]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No live query or current-event answer storage in this artifact."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-006
  status: active
  query: "oil and equity markets past week"
  category: "News / recency"
  secondary_tags: [markets, finance, recency, multi_topic]
  freshness_requirement: high
  query_type_hint: news
  report_type_hint: summary
  mode_coverage: [Fast, Balanced, Deep]
  intended_challenge: "Synthesize time-bounded market movement without unsupported numbers."
  expected_evidence_shape: "Recent market summaries, index/oil price references, and clearly dated sources."
  source_expectations: "Prefer sources that state the period, instruments, and market context."
  quality_observation_prompts: ["Are numeric claims source-bound?", "Does it distinguish oil from equity drivers?"]
  telemetry_probes: [source_date_span, numeric_claim_count, citation_count, waste_flags]
  likely_failure_classes: [synthesis.numeric_unsupported, retrieval.stale_corpus, ux.table_readability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No financial golden answer, provider payload, or investment advice template."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-007
  status: active
  query: "Diablo 4 battle pass purchase currency"
  category: "Product / how-to"
  secondary_tags: [product, game, how_to, currency]
  freshness_requirement: medium
  query_type_hint: product
  report_type_hint: how_to
  mode_coverage: [Fast, Balanced]
  intended_challenge: "Find current product mechanics and avoid stale seasonal or platform-specific confusion."
  expected_evidence_shape: "Official support or store documentation, with recent community context only as secondary evidence."
  source_expectations: "Separate official purchase currency from unrelated in-game currencies."
  quality_observation_prompts: ["Does it name the relevant currency category without overexplaining?", "Are seasonal caveats sourced?"]
  telemetry_probes: [query_type, source_tiers, utilization_rate, waste_flags]
  likely_failure_classes: [retrieval.source_tier_mismatch, retrieval.official_source_missing, synthesis.entity_conflation]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No product-specific routing or purchase guidance rule."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-008
  status: active
  query: "most efficient difficulty for leveling in Diablo 4"
  category: "Product / how-to"
  secondary_tags: [game, optimization, how_to, freshness]
  freshness_requirement: medium
  query_type_hint: product
  report_type_hint: how_to
  mode_coverage: [Fast, Balanced]
  intended_challenge: "Handle frequently changing gameplay advice with source-age caveats."
  expected_evidence_shape: "Recent patch-aware guides, official patch notes where relevant, and clearly dated advice."
  source_expectations: "Avoid stale season guidance being presented as current."
  quality_observation_prompts: ["Are patch or season dependencies visible?", "Does the answer avoid false precision?"]
  telemetry_probes: [source_date_span, utilization_rate, waste_flags]
  likely_failure_classes: [retrieval.stale_corpus, synthesis.overconfident_weak_evidence, synthesis.numeric_unsupported]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No expected gameplay answer or query-specific synthesis rule."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-009
  status: active
  query: "how to enable two-factor on GitHub"
  category: "Product / how-to"
  secondary_tags: [product, official_docs, security, how_to]
  freshness_requirement: medium
  query_type_hint: product
  report_type_hint: how_to
  mode_coverage: [Fast, Balanced]
  intended_challenge: "Prefer official documentation and present a clear procedural answer."
  expected_evidence_shape: "GitHub official docs or support pages, possibly supplemented by recent UI-change notes."
  source_expectations: "Official source should dominate; third-party tutorials are lower priority."
  quality_observation_prompts: ["Are steps based on official docs?", "Does it avoid outdated UI paths?"]
  telemetry_probes: [source_tiers, official_source_present, citation_count]
  likely_failure_classes: [retrieval.official_source_missing, retrieval.source_tier_mismatch, ux.citation_scanability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No raw official-doc excerpt dump or hard-coded UI route."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-010
  status: active
  query: "arxiv attention is all you need summary for practitioners"
  category: "Academic / technical"
  secondary_tags: [academic, technical, practitioner_summary, classic_paper]
  freshness_requirement: low
  query_type_hint: academic
  report_type_hint: technical
  mode_coverage: [Balanced, Deep]
  intended_challenge: "Ground a practitioner summary in the original paper and reliable secondary context."
  expected_evidence_shape: "Original arXiv paper plus high-quality explanatory or implementation references."
  source_expectations: "Original paper should be clearly cited; avoid only SEO summaries."
  quality_observation_prompts: ["Does it separate paper claims from later ecosystem interpretation?", "Is technical language accessible?"]
  telemetry_probes: [source_tiers, citation_count, utilization_rate]
  likely_failure_classes: [retrieval.official_source_missing, synthesis.unsourced_claim, ux.citation_scanability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No expected explanation text or paper-summary golden answer."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-011
  status: active
  query: "CRISPR off-target mitigation methods 2025 2026"
  category: "Academic / technical"
  secondary_tags: [academic, biomedical, recency, technical]
  freshness_requirement: date_bound
  query_type_hint: academic
  report_type_hint: technical
  mode_coverage: [Balanced, Deep]
  intended_challenge: "Retrieve recent technical literature and caveat unsettled biomedical evidence."
  expected_evidence_shape: "Recent papers, reviews, and authoritative scientific sources with dates visible."
  source_expectations: "Prefer peer-reviewed or preprint context over generic health summaries."
  quality_observation_prompts: ["Are methods grouped without overstating clinical readiness?", "Are recency and evidence limits clear?"]
  telemetry_probes: [source_date_span, source_tiers, citation_count, waste_flags]
  likely_failure_classes: [retrieval.stale_corpus, retrieval.source_tier_mismatch, synthesis.overconfident_weak_evidence]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No medical advice answer, golden ranking, or query-specific biomedical policy."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-012
  status: active
  query: "compare cost per passenger mile MD-80 vs 777-300"
  category: "Quantitative / comparison"
  secondary_tags: [quantitative, aviation, comparison, units]
  freshness_requirement: low
  query_type_hint: quantitative
  report_type_hint: comparison
  mode_coverage: [Balanced, Deep]
  intended_challenge: "Compare unlike aircraft using clear assumptions, units, and evidence limits."
  expected_evidence_shape: "Technical or industry sources for costs, capacity, fuel burn, utilization, and caveated assumptions."
  source_expectations: "Avoid unsupported single-number comparisons; show source-bound ranges if present."
  quality_observation_prompts: ["Are assumptions explicit?", "Are numeric claims cited and unit-consistent?"]
  telemetry_probes: [numeric_claim_count, citation_count, economist_shadow_fields, waste_flags]
  likely_failure_classes: [synthesis.numeric_unsupported, synthesis.overconfident_weak_evidence, ux.table_readability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No golden calculation, raw Economist packet, or production math shortcut."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-013
  status: active
  query: "average electricity price Germany vs France 2026"
  category: "Quantitative / comparison"
  secondary_tags: [quantitative, energy, comparison, date_bound]
  freshness_requirement: date_bound
  query_type_hint: quantitative
  report_type_hint: comparison
  mode_coverage: [Balanced, Deep]
  intended_challenge: "Compare date-bound country metrics with source definitions and units intact."
  expected_evidence_shape: "Official statistical or market sources with country, period, consumer class, and unit definitions."
  source_expectations: "Distinguish household, industrial, wholesale, and retail prices."
  quality_observation_prompts: ["Does it avoid mixing price definitions?", "Are dates and units visible near numbers?"]
  telemetry_probes: [source_date_span, numeric_claim_count, source_tiers, waste_flags]
  likely_failure_classes: [retrieval.source_tier_mismatch, synthesis.numeric_unsupported, ux.table_readability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No expected numeric answer or query-specific source whitelist."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-014
  status: active
  query: "what causes auroras at mid latitudes"
  category: "Conceptual / broad"
  secondary_tags: [concept, science, explainer]
  freshness_requirement: low
  query_type_hint: concept
  report_type_hint: broad_overview
  mode_coverage: [Fast, Balanced]
  intended_challenge: "Explain a broad science concept while preserving mechanism and caveats."
  expected_evidence_shape: "Authoritative science explainers, agency pages, and optionally recent event examples."
  source_expectations: "Prefer scientific agencies or educational sources over shallow summaries."
  quality_observation_prompts: ["Is the causal chain clear?", "Are event examples separated from the general mechanism?"]
  telemetry_probes: [source_tiers, utilization_rate, citation_count]
  likely_failure_classes: [synthesis.unsourced_claim, retrieval.source_tier_mismatch, ux.citation_scanability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No expected explainer wording or competitor style target."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-015
  status: active
  query: "overview of EU CBAM implementation status"
  category: "Conceptual / broad"
  secondary_tags: [policy, EU, status, regulation]
  freshness_requirement: medium
  query_type_hint: concept
  report_type_hint: broad_overview
  mode_coverage: [Balanced, Deep]
  intended_challenge: "Summarize an evolving policy program with official-source grounding."
  expected_evidence_shape: "European Commission or official EU sources plus reputable analysis for context."
  source_expectations: "Official implementation status should anchor the report."
  quality_observation_prompts: ["Are phases and dates sourced?", "Does it separate current obligations from future milestones?"]
  telemetry_probes: [official_source_present, source_date_span, citation_count]
  likely_failure_classes: [retrieval.official_source_missing, retrieval.stale_corpus, synthesis.overconfident_weak_evidence]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No policy golden answer or production source-filtering rule."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-016
  status: active
  query: "London Marathon 2026 men's winner time"
  category: "Place / event"
  secondary_tags: [event, sports, date_bound, result]
  freshness_requirement: date_bound
  query_type_hint: place
  report_type_hint: summary
  mode_coverage: [Fast, Balanced]
  intended_challenge: "Retrieve an event result with precise entity, date, and numeric value."
  expected_evidence_shape: "Official event results or reputable sports reporting with finish time."
  source_expectations: "Official result source preferred; avoid preview articles after the event."
  quality_observation_prompts: ["Is the result sourced to the correct event year?", "Is the time clearly cited?"]
  telemetry_probes: [official_source_present, source_date_span, numeric_claim_count, waste_flags]
  likely_failure_classes: [retrieval.stale_corpus, retrieval.official_source_missing, synthesis.numeric_unsupported]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No stored expected result, live lookup instruction, or event-specific rule."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-017
  status: active
  query: "state of aviation in Europe May 2026"
  category: "Place / event"
  secondary_tags: [aviation, Europe, date_bound, industry]
  freshness_requirement: date_bound
  query_type_hint: place
  report_type_hint: summary
  mode_coverage: [Balanced, Deep]
  intended_challenge: "Synthesize a regional industry snapshot with time-bound evidence."
  expected_evidence_shape: "Recent aviation industry data, regulator or association sources, and dated reporting."
  source_expectations: "Avoid generic aviation evergreen pages; distinguish Europe from global aviation."
  quality_observation_prompts: ["Are trends tied to May 2026 evidence?", "Are numbers and claims sourced?"]
  telemetry_probes: [source_date_span, source_tiers, numeric_claim_count, waste_flags]
  likely_failure_classes: [retrieval.stale_corpus, retrieval.generic_news_dominance, synthesis.numeric_unsupported]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No industry snapshot golden answer or production routing adjustment."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-018
  status: active
  query: "fictional character from obscure podcast episode title only"
  category: "Ambiguous / thin evidence"
  secondary_tags: [ambiguous, thin_evidence, failure_ux]
  freshness_requirement: none
  query_type_hint: ambiguous
  report_type_hint: summary
  mode_coverage: [Fast, Balanced, Deep]
  intended_challenge: "Exercise weak-corpus honesty and avoid fabricating from thin evidence."
  expected_evidence_shape: "Sparse or uncertain sources; clear indication if evidence does not establish the entity."
  source_expectations: "Do not inflate weak matches into confidence."
  quality_observation_prompts: ["Does the answer stay short and honest when evidence is weak?", "Does it avoid internal jargon?"]
  telemetry_probes: [corpus_weak, utilization_rate, waste_flags, failure_reason]
  likely_failure_classes: [retrieval.low_utilization, synthesis.overconfident_weak_evidence, ux.failure_copy_jargon]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No invented answer, transcript dump, or query-specific failure copy."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-019
  status: active
  query: "single-word query: graphene"
  category: "Ambiguous / thin evidence"
  secondary_tags: [ambiguous, broad, single_word]
  freshness_requirement: none
  query_type_hint: ambiguous
  report_type_hint: broad_overview
  mode_coverage: [Fast, Balanced]
  intended_challenge: "Handle an underspecified single-word query without drifting or overfitting."
  expected_evidence_shape: "Authoritative overview sources, with optional prompt for narrowing if scope remains broad."
  source_expectations: "Prefer broad authoritative sources and avoid arbitrary niche dominance."
  quality_observation_prompts: ["Does it state a useful default scope?", "Does it remain concise enough for ambiguity?"]
  telemetry_probes: [query_type, report_type, utilization_rate, waste_flags]
  likely_failure_classes: [retrieval.generic_news_dominance, synthesis.unsourced_claim, ux.citation_scanability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No query-specific default policy or expected overview text."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-020
  status: active
  query: "What sources contradict that conclusion?"
  category: "Follow-up style"
  secondary_tags: [followup, contradiction, context]
  freshness_requirement: inherited
  query_type_hint: followup
  report_type_hint: followup
  mode_coverage: [followup_thread]
  intended_challenge: "Test whether follow-up handling preserves prior context while seeking contrary evidence."
  expected_evidence_shape: "Sources relevant to the prior thread's conclusion, including countervailing evidence if available."
  source_expectations: "Must depend on an existing approved thread; no standalone live-query instruction in this artifact."
  quality_observation_prompts: ["Does it preserve the prior claim being tested?", "Does it avoid manufacturing contradiction?"]
  telemetry_probes: [thread_id, followup_context_used, citation_count, waste_flags]
  likely_failure_classes: [followup.context_drift, synthesis.unsourced_claim, telemetry.missing_diagnostic]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No raw thread transcript, live run instruction, or expected contradiction answer."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-021
  status: active
  query: "Narrow to peer-reviewed only."
  category: "Follow-up style"
  secondary_tags: [followup, peer_reviewed, source_filtering]
  freshness_requirement: inherited
  query_type_hint: followup
  report_type_hint: followup
  mode_coverage: [followup_thread]
  intended_challenge: "Test follow-up source constraint handling without losing thread context."
  expected_evidence_shape: "Peer-reviewed or clearly scholarly sources relevant to the prior thread."
  source_expectations: "Requires an existing approved thread; should not treat the sentence as standalone topic text."
  quality_observation_prompts: ["Does it narrow source type while preserving the original question?", "Are non-peer-reviewed sources excluded or caveated?"]
  telemetry_probes: [followup_context_used, source_tiers, filter_reason, waste_flags]
  likely_failure_classes: [followup.context_drift, retrieval.source_tier_mismatch, telemetry.missing_diagnostic]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No production source-filtering rule or raw conversation transcript."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-022
  status: active
  query: "Java Indonesia earthquake latest"
  category: "Collision stress"
  secondary_tags: [place, collision, news, recency]
  freshness_requirement: high
  query_type_hint: news
  report_type_hint: summary
  mode_coverage: [Fast, Balanced, Deep]
  intended_challenge: "Disambiguate Java as a place under latest-news pressure."
  expected_evidence_shape: "Recent earthquake monitoring, official geological sources, and reputable reporting about Java, Indonesia."
  source_expectations: "Avoid programming-language sources and stale earthquake pages."
  quality_observation_prompts: ["Does retrieval stay on the place entity?", "Are dates and magnitude/location claims sourced?"]
  telemetry_probes: [primary_entity, query_type, source_date_span, waste_flags]
  likely_failure_classes: [retrieval.entity_collision, retrieval.stale_corpus, synthesis.numeric_unsupported]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No live disaster answer, raw news transcript, or Java-specific routing rule."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-023
  status: active
  query: "Java programming language release timeline"
  category: "Collision stress"
  secondary_tags: [product, collision, timeline, technical]
  freshness_requirement: medium
  query_type_hint: product
  report_type_hint: technical
  mode_coverage: [Fast, Balanced]
  intended_challenge: "Disambiguate Java as a programming language and produce a sourced timeline."
  expected_evidence_shape: "Official Java/OpenJDK release sources plus reliable technical references."
  source_expectations: "Avoid Indonesia or island-related sources."
  quality_observation_prompts: ["Does it stay on the programming-language entity?", "Are version dates sourced and caveated where needed?"]
  telemetry_probes: [primary_entity, query_type, official_source_present, citation_count]
  likely_failure_classes: [retrieval.entity_collision, retrieval.official_source_missing, ux.table_readability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No release-timeline golden answer or hard-coded disambiguation rule."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-024
  status: active
  query: "Cursor IDE auto model list current"
  category: "Misc coverage"
  secondary_tags: [product, AI_tools, current, official_docs]
  freshness_requirement: high
  query_type_hint: product
  report_type_hint: summary
  mode_coverage: [Fast, Balanced]
  intended_challenge: "Find current product behavior for a fast-changing AI developer tool."
  expected_evidence_shape: "Official Cursor docs, changelog, or support pages, with recent community notes only as secondary context."
  source_expectations: "Prefer current official source over stale blog or forum posts."
  quality_observation_prompts: ["Does it distinguish current model availability from old lists?", "Are uncertainty and recency clear?"]
  telemetry_probes: [official_source_present, source_date_span, waste_flags]
  likely_failure_classes: [retrieval.stale_corpus, retrieval.official_source_missing, synthesis.overconfident_weak_evidence]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No current product answer, live lookup instruction, or production provider-selection rule."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed

- id: RQ-025
  status: active
  query: "compare Brave vs Safari privacy defaults iOS"
  category: "Misc coverage"
  secondary_tags: [product, privacy, comparison, iOS]
  freshness_requirement: medium
  query_type_hint: product
  report_type_hint: comparison
  mode_coverage: [Fast, Balanced, Deep]
  intended_challenge: "Compare two products' defaults with platform-specific and source-tier constraints."
  expected_evidence_shape: "Official browser and Apple documentation, privacy policy or support pages, plus reputable technical analysis."
  source_expectations: "Separate defaults from optional settings; distinguish iOS behavior from desktop behavior."
  quality_observation_prompts: ["Are defaults and optional features clearly separated?", "Does the comparison avoid unsupported privacy rankings?"]
  telemetry_probes: [source_tiers, official_source_present, citation_count, waste_flags]
  likely_failure_classes: [retrieval.source_tier_mismatch, synthesis.overconfident_weak_evidence, ux.table_readability]
  comparison_notes: not_run
  parity_notes: unset
  differentiation_notes: unset
  mapped_work_type: unset
  forbidden_uses: "No golden comparison, competitor wording target, or product-specific policy rule."
  added_at: "2026-05-12"
  reviewed_at: not_reviewed
```

## Maintenance Rules

- Do not add raw comparison transcripts.
- Do not add golden answers.
- Keep records compact.
- Retire or refresh date-sensitive queries when stale.
- Do not turn this file into replay output or production policy.
- Do not upload this as a Project Source unless a later durable checkpoint asks
  for consolidation.
