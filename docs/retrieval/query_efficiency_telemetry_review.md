# Query-Efficiency Telemetry Review Guide - Phase 14

Date: 2026-05-13

## Status

This guide is docs-only. It explains how to review existing query-efficiency telemetry in local JSONL traces and related summaries. It is not production policy and does not authorize runtime changes.

This guide does not authorize routing changes, retrieval changes, provider selection changes, search-depth changes, query-generation changes, prompt changes, source filtering or ranking changes, Analyst behavior changes, Economist behavior changes, Author behavior changes, telemetry semantics changes, replay changes, summarizer changes, SQLite behavior changes, or weak-corpus behavior changes.

Provider overlap/yield, query similarity, provider role, provider depth, and provider attempt diagnostics are review signals only. They must not become gates, skips, suppressions, source-ranking inputs, query rewrites, or provider-routing policy without a separate behavior-changing Review Lane pass, Rule 0 failure analysis, tests, replay evidence, and explicit approval.

Provider cost estimates remain disabled/null in current telemetry. Do not infer dollar spend from provider attempts, depth, or role fields alone.

Existing weak-corpus retrieval gating is separate and out of scope. Economist code execution remains categorically prohibited. Economist output must not enable Analyst skip, and raw `quantitative_packet` or raw Economist framework content must not be passed to Author.

## Useful JSONL Fields

Use the rich JSONL execution trace as the primary source for query-efficiency review. The relevant fields are diagnostic context, not policy levers:

- `queries_per_iteration`: search queries issued by retrieval pass.
- `queries_iter1`, `queries_iter2`: compact first/second pass query views in some quality records.
- `disambiguation_queries_by_iteration`: additional entity-disambiguation search attempts.
- `weak_corpus_recovery_considered`, `weak_corpus_recovery_used`, `weak_corpus_recovery_skip_reason`, `weak_corpus_recovery_queries`: weak-corpus recovery diagnostics; review separately from ordinary query-efficiency candidates.
- `providers_by_iteration` and `pass_providers`: provider mix by pass.
- `provider_diagnostics`: per-provider attempt diagnostics.
- `provider_successful_attempts_by_provider`, `provider_failed_attempts_by_provider`, `provider_attempts_by_role`: aggregate attempt counts lifted from provider diagnostics.
- `iterations_run`: number of retrieval loop iterations completed.
- `total_chunks_embedded` and `retrieval_yield_chunks`: chunk-yield proxies.
- `urls_fetched`: fetched URL count.
- `supplemental_ran` and `delta_urls_supplemental`: synthesis-gap supplemental search diagnostics.
- `waste_flags` and `query_redundancy_skipped`: existing diagnostic flags; do not promote them to production gates from one run.
- `source_tier_counts`, `source_domain_counts`, `top_source_domains`, and `unique_source_domain_count`: source-shape context for judging whether overlap was useful or wasteful.
- `corpus_state`, `corpus_weak`, `utilization_rate`, and `useful_content`: evidence-health context. These fields should not be conflated with provider policy.
- `followup_diagnostics`: chat follow-up route, query count, search outcome, and provider diagnostics.

For offline summaries, `scripts/aggregate_run_quality.py` can summarize existing local logs without running ProPlex, Streamlit, providers, models, or search APIs.

## SQLite Summary Fields

SQLite run rows are compact summaries intended for UI and aggregate views. They are useful for broad filtering, but they do not replace JSONL for per-run query-efficiency review.

Relevant compact fields include:

- `retrieval_yield_chunks`
- `urls_fetched`
- `iterations_run`
- `corpus_state`
- `total_latency_seconds`
- `total_cost_usd`
- `kb_score`, `kb_fired`, and `useful_content`

SQLite does not preserve the full provider diagnostic list, query lists, overlap counts, follow-up route shadows, or detailed safety handoff context. Use JSONL when reviewing why a pass used extra queries or why a provider attempt had low marginal yield.

## Provider Role, Depth, And Attempt Diagnostics

Each provider diagnostic record describes one call-site-level attempt. Read these fields together:

- `provider`: the provider name, such as `tavily`, `exa`, `linkup`, or `brave`.
- `provider_role`: the call-site role, such as `main_retrieval`, `supplemental_search`, `scrutineer_remediation`, `chat_followup_search`, or `linkup_precision_sourced_answer`.
- `cost_phase`: the broad cost/accounting phase, not a dollar estimate.
- `query_count` and `query_preview`: the query shape for that attempt. `query_preview` is truncated.
- `iteration`: retrieval loop iteration when available.
- `depth`: provider-specific depth, such as Tavily `basic` or `advanced`, or Linkup `fast`, `standard`, or `deep`.
- `output_type`: normal search results versus answer-style outputs such as `sourcedAnswer`.
- `max_results`: requested result cap.
- `answer_endpoint_used` and `raw_content_requested`: capability hints.
- `success`, `failure_type`, `result_count`, and `image_count`: attempt outcome.
- `logical_attempt_count`: summary weight for aggregate counts.

Provider diagnostics are not hidden retry accounting and not cost estimates. A successful attempt can still produce low useful yield, and a failed attempt can still be important for reliability review.

## Raw Overlap Vs Accepted Overlap

Raw overlap and accepted overlap answer different questions:

- `raw_url_count`: all URL-bearing results returned by the provider attempt.
- `raw_unique_url_count`: distinct raw URLs in that provider attempt.
- `raw_url_overlap_count`: raw URLs already seen before this pass.
- `raw_domain_count`: distinct domains in raw results.
- `raw_domain_overlap_count`: raw domains already seen before this pass.
- `accepted_url_count`: plausible, not-yet-seen URLs admitted for downstream retrieval processing.
- `accepted_url_overlap_count`: overlap among admitted URLs versus pre-pass seen URLs. This should usually be low because already-seen URLs are filtered before acceptance.

Raw overlap is pre-acceptance provider output. It helps identify repeated provider returns, same-domain clustering, or redundant generated queries.

Accepted overlap is post-filter context. It helps check whether downstream admission prevented duplicated URLs from re-entering evidence processing.

Do not treat raw overlap as automatic waste. It may show that providers agree on an important source, that fresh coverage is concentrated on a few official domains, or that entity-collision recovery is deliberately revisiting known anchors.

## New Source And Domain Yield

Use `new_source_count` and `new_domain_count` as marginal-yield signals:

- `new_source_count`: accepted URLs from the attempt that survived into new passages after snippet/full-page processing and filtering.
- `new_domain_count`: accepted domains not seen before the pass.
- `accepted_domain_count`: distinct domains among accepted URLs.

High `new_source_count` usually means the attempt produced citable or at least processable new evidence. High `new_domain_count` usually means the attempt diversified source coverage.

Low `new_source_count` can mean the attempt found duplicates, thin content, low-credibility results, unreadable pages, low embedding relevance, or sources filtered before passage creation. It is a review cue, not a verdict.

## Why High Overlap Is Not Automatically Waste

High overlap can be useful when it supports:

- Corroboration across providers or query formulations.
- Freshness checks where a few sources dominate current coverage.
- Official-source needs where one agency, regulator, company, venue, or standards body is the correct anchor.
- Entity-collision recovery where retrieval intentionally tests whether the same-name results are on target.
- Weak-corpus recovery, which is an existing separate retrieval gate and should be reviewed under its own policy.
- Safety-sensitive synthesis where repeated source agreement may be better than broad but weak diversity.

A candidate for human review is stronger when high overlap appears together with low `new_source_count`, low `new_domain_count`, high query similarity, no special route reason, no weak-corpus recovery context, no freshness/official-source requirement, and no visible quality benefit.

## Review Examples

### High Overlap / Low Yield: Human Review Only

Pattern:

- `query_similarity_max` is high against the prior pass.
- `raw_url_overlap_count` or `raw_domain_overlap_count` is high.
- `new_source_count` is `0` or near zero.
- `new_domain_count` is `0` or near zero.
- `provider_role` is ordinary `main_retrieval`, not a specific recovery or supplemental role.
- `corpus_state` does not explain the extra pass.

Interpretation: mark as a candidate for human query-efficiency review. Do not throttle, demote a provider, suppress sources, rewrite future queries, or change routing from this pattern alone.

### High Overlap But Justified

Pattern:

- High raw overlap appears alongside `weak_corpus_recovery_used`, disambiguation queries, latest/freshness pressure, official-source requirements, or entity-collision risk.
- `new_source_count` may be low, but the repeated source is the expected authoritative anchor.
- Follow-up diagnostics may show freshness, contradiction, source-constraint, or ambiguity cues.

Interpretation: keep as justified or at least unresolved until a reviewer checks the run context. High overlap may be exactly what a careful retrieval pass should produce.

### Low Overlap / High Yield: Do Not Flag

Pattern:

- `raw_url_overlap_count` and `raw_domain_overlap_count` are low.
- `new_source_count` and `new_domain_count` are high.
- Source tiers/domains look relevant to the query.
- The pass improves evidence coverage or citation diversity.

Interpretation: do not flag for query-efficiency waste. This is the positive-control shape for useful retrieval expansion.

## Forbidden Interpretations

These interpretations are explicitly forbidden from this guide and from the current telemetry alone:

- No throttling from overlap, yield, query-similarity, provider-role, provider-depth, or provider-attempt diagnostics.
- No provider demotion or promotion.
- No source suppression or source ranking.
- No routing changes.
- No retrieval-depth changes.
- No query-generation or query-rewrite changes.
- No prompt changes.
- No Analyst behavior changes.
- No Economist behavior changes.
- No Author behavior changes.
- No telemetry-semantics, JSONL, SQLite, replay, or summarizer behavior changes.
- No weak-corpus behavior changes.
- No production policy from one run, one example, one provider attempt, or one aggregate telemetry pattern.
- No dollar-cost inference while provider cost estimates are disabled/null.

## Future Work

### Fast Lane Script/Test Summary Candidates

These are docs, tests, or offline-script candidates only. They should not change runtime behavior:

- Add synthetic tests for provider-diagnostics aggregation buckets: overlap, query similarity, role, depth, and new-source yield.
- Extend `scripts/aggregate_run_quality.py` to print yield by provider role and depth from existing JSONL.
- Add an offline summary for high-overlap/low-yield candidates, clearly labeled as human-review candidates only.
- Add an offline summary for justified-overlap contexts, such as weak-corpus recovery, disambiguation, freshness cues, official-source expectations, and follow-up route shadows.
- Add docs examples that map reference-query library `telemetry_probes` to existing JSONL fields.

### Review Lane Behavior-Risk Candidates

These require separate approval, Rule 0 failure analysis, and behavior-changing implementation review before any code change:

- Any runtime throttling, query cap reduction, provider suppression, provider routing change, or depth reduction based on overlap/yield.
- Any query-generation change that uses query similarity, provider overlap, or marginal yield as a control-flow input.
- Any source filtering, ranking, or citation-selection change based on provider overlap/yield.
- Any promotion of follow-up route shadows into active route changes.
- Any use of provider role/depth diagnostics as provider-selection policy.

Rule 0 failure-analysis proposal for any behavior-risk candidate: establish repeated evidence across a stratified set of approved historical rows that the proposed change would have reduced redundant work without harming source quality, freshness, official-source coverage, entity disambiguation, weak-corpus handling, or answer sufficiency. Include positive and negative controls, replay evidence, and explicit rollback criteria before implementation.
