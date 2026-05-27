# Provider Role and Cost Audit - Phase 13B

Date: 2026-05-13

## Status

This is a Phase 13B external/provider-role audit note. It is docs-only, diagnostic, and not production policy.

It does not authorize provider routing changes, telemetry semantics changes, retrieval behavior changes, prompt changes, source-filtering changes, eval policy changes, or production procurement decisions. Approximate cost figures below are directional Deep Research normalizations, not contract quotes.

## Source Basis

This document combines three inputs:

- Local repo provider-flow audit from the current workspace, especially `core/routing.py`, `core/search_providers.py`, and `core/cost_accounting.py`.
- Deep Research provider/cost report facts exported 2026-05-13 and supplied by the user in chat for this revision.
- Current official provider pricing and capability docs as cited in the Deep Research source appendix.

The Deep Research report file itself is not repo-local in this workspace. The facts from that report were supplied by the user and should be replaced or supplemented with repo-local report excerpts/citations later if the project wants this document to carry direct appendix citations.

All annual API-cost/TCO figures in this note are Deep Research normalization estimates. They are directional planning numbers, not vendor quotes, not committed budgets, and not sufficient for procurement or implementation without a pricing refresh.

## Executive Summary

The current provider stack is directionally sensible: Tavily is the default broad/news/ordinary retrieval provider, Exa is a semantic/general/academic specialist, Linkup is reserved for higher-cost high-mode/deep/sourcedAnswer escalation, and Brave is optional reconnaissance rather than normal evidence retrieval.

The main gap is not an obvious provider swap. The main gap is provider cost, role, attempt, and overlap telemetry. Current cost accounting can record successful provider calls, but provider prices are set to `0.0`, failed provider attempts are logged separately, retries can create more HTTP attempts than cost telemetry shows, follow-up provider/depth telemetry is incomplete, and result overlap/yield is not measured.

Raw SERP providers are often cheaper in the Deep Research normalization, but they shift integration and citation burden to FauxPlex. Cheaper retrieval only helps if the returned URLs become citable, non-duplicative, fetchable, and good enough to reduce expensive downstream synthesis or escalation.

## Current Repo Provider-Flow Summary

### Tavily

Tavily is the default broad retrieval provider. `core/routing.py` falls back to `["tavily"]` when a provider selection would otherwise be empty. News, current-events, event, ordinary, and quantitative paths all use Tavily when available unless suppressed by an explicit route.

Tavily search calls are implemented in `core/search_providers.py` with `include_answer=False`, `include_images=True`, `include_raw_content=True`, and depth configured by the caller. Successful calls can be counted through `CostAccumulator.record_search_call`, but Tavily provider cost is currently `0.0` in `core/cost_accounting.py`.

### Exa

Exa is the semantic/general/academic specialist. `core/routing.py` sends academic paths to Exa when available and includes Exa after Tavily/Linkup for ordinary non-quantitative retrieval. The routing code explicitly drops Exa from comparison and quantitative paths in favor of Tavily/Linkup.

Exa calls use `search_and_contents` with neural search and returned text. The code bounds wall-clock wait with an executor timeout because the SDK path does not expose the same per-request timeout shape. Successful calls can be counted, but Exa provider cost is currently `0.0`.

### Linkup

Linkup is treated as premium-ish escalation. `core/routing.py` allows Linkup when complexity is high, when there is an explicit provider override, or when premium search escalation is active. It can also be used for deep precision context and sourced-answer paths elsewhere in the pipeline.

Linkup search supports depth, output type, domain constraints, date bounds, structured output, and `sourcedAnswer`. Successful calls can be counted, but Linkup provider cost is currently `0.0`.

### Brave

Brave is optional reconnaissance only, not normal evidence retrieval. `core/search_providers.py` describes it as lightweight entity/term resolution and returns titles, URLs, snippets, and age without full fetch, chunking, or embedding.

Brave can be counted as a search call when a cost accumulator is passed, but Brave provider cost is currently `0.0`.

### Absent Providers

The pasted audit context says Serper, DataForSEO, Bright Data, Firecrawl, Jina, SerpApi, and Bing have no repo integration. The local code search from the prior pass was consistent with that summary: normal retrieval integration is limited to Tavily, Exa, Linkup, and Brave.

## Pricing and Capability Facts

These facts come from the user-supplied Deep Research report summary. The annual API-cost/TCO column is a Deep Research normalization estimate for comparison only. It is directional, not a contract quote, and requires refresh before procurement or implementation.

| Provider | Capability facts from Deep Research | Approx annual API-cost/TCO normalization | Cost and integration gotchas | Current repo status |
| --- | --- | --- | --- | --- |
| Tavily | AI-native search with basic, fast, ultra-fast, and advanced paths; domain filters; news, general, and finance support; raw content and images. | USD 5k-8k/year for 1M standard jobs/year on basic/fast/ultra-fast; USD 10k-16k/year if the standard path is mostly advanced depth. | Advanced depth and extract/crawl costs are separate from the basic search path. | Integrated default broad/news/ordinary retrieval. |
| Exa | Search with text/highlights bundled for up to 10 results; Contents, Answer, and Deep Search. Best fit is semantic, docs, code, academic, and research-style retrieval. | Approx USD 7k/year for standard search; approx USD 12k/year for deep search; contents and summaries add more. | Contents, summaries, answer, and deep features can move cost beyond ordinary search assumptions. | Integrated semantic/general/academic specialist; excluded from quantitative paths. |
| Linkup | Fast, standard, and deep search; `sourcedAnswer`; structured output; fetch. Best fit is premium escalation. | Approx USD 5.5k/year for fast/standard under assumptions; approx USD 55k/year if deep becomes standard. | Deep mode is expensive; async research is separate and pricier. | Integrated high/deep/sourcedAnswer escalation. |
| Brave Search API | Independent web index; web, news, images, answers; LLM-grounding support. Best fit is cheap reconnaissance, index diversity, and secondary validation. | Approx USD 5k/year for Search at USD 5/1k requests. | Search output still needs app-owned fetch, cleaning, ranking, dedupe, and citation decisions for evidence use. | Integrated reconnaissance helper only. |
| Firecrawl | Search plus optional full-page scrape; web, news, images; GitHub, research, and PDF categories; browser/crawl tooling. Best fit is consolidating search plus scrape/crawl/browser functionality. | Approx USD 2.1k/year for 1M standard-search baseline under Deep Research assumptions; higher if scraping result pages inline. | Full-page scrape, crawl, browser, and extract actions can dominate cost if used inline. | No repo integration found. |
| Serper | Google SERP wrapper with news, scholar, shopping, maps, videos, and autocomplete. Very cheap. | Approx USD 750/year at public Standard-pack unit rate for 1M queries/year. | Requires app-owned fetch, content cleaning, ranking, dedupe, and citation logic. | No repo integration found. |
| DataForSEO | Multi-engine SERP infrastructure with Standard, Priority, and Live modes. Very cheap. | Approx USD 600/year in Standard queue or USD 2k/year in Live mode. | Higher integration overhead; Standard queue versus Live mode is a latency/cost tradeoff. | No repo integration found. |
| Bright Data SERP API | SERP extraction, parsing, unlocking, async collection, and enterprise trust/compliance posture. Strong scale/unblocking/compliance fit; scraping-centric. | Approx USD 1.5k/year baseline. | Scraping-centric integration and compliance review are part of the real TCO. | No repo integration found. |
| SerpApi | Broad engine coverage, structured JSON, legal shield, and ZeroTrace enterprise options. | Approx USD 9.2k/year extrapolated at public Big Data unit rate; real high-volume cost may be custom. | Broad capability but relatively weak on cost versus Serper, DataForSEO, and Bright Data. | No repo integration found. |

## Normalized Scenario Model

Use symbolic variables until pricing is refreshed from official vendor pages and stored with an observed date. The point of the model is to separate role, depth, attempts, extraction, answer endpoints, and duplicate waste.

Definitions:

- `C(provider, role, depth, unit_basis)` = estimated provider request cost for one billable unit.
- `N_queries` = generated search query count.
- `N_followups` = follow-up search count.
- `N_extracts` = fetch/extract/page/action count.
- `N_success` = successful provider request count.
- `N_failed` = failed provider request count.
- `N_retries` = retry attempts beyond the first attempt.
- `N_attempts = N_success + N_failed + N_retries`.
- `D` = provider depth multiplier, such as basic, advanced, standard, live, or deep.
- `A` = answer/synthesis endpoint multiplier or fee.
- `O` = overlap ratio versus previous result URLs or domains.
- `Y` = unique citable source yield.

Cheap probe loop:

`cost_probe_loop = N_queries * C(provider, cheap_probe, depth=basic_or_standard, unit_basis=query)`

Probe + extract:

`cost_probe_extract = (N_queries * C(provider, cheap_probe, depth=basic_or_standard, unit_basis=query)) + (N_extracts * C(provider, targeted_fetch_extract, depth=page_or_browser, unit_basis=page_or_action))`

Ordinary retrieval:

`cost_ordinary = sum(C(provider, ordinary_retrieval, depth=D, unit_basis=request_or_credit) for each selected provider/query)`

Premium escalation:

`cost_premium = cost_ordinary + sum(C(provider, premium_deep_escalation, depth=deep_or_advanced, unit_basis=request_or_credit) for each escalation)`

If an answer endpoint is used during escalation:

`cost_premium_with_answer = cost_premium + (N_answer_calls * C(provider, answer_endpoint, depth=D, unit_basis=answer_or_credit) * A)`

Follow-up search:

`cost_followup = (N_followups * C(provider, followup_search, depth=D, unit_basis=request_or_credit)) + followup_extract_cost + downstream_model_cost`

Near-duplicate waste:

`waste_near_duplicate = total_provider_cost * O`

Useful provider spend should be read alongside yield:

`cost_per_unique_citable_source = total_provider_cost / max(Y, 1)`

High overlap, low `Y`, or repeated follow-up queries with similar text indicate repeated spend without new citation value.

## Provider-Role Hypothesis Table

These are hypotheses for future diagnostics, not routing recommendations.

| Role | Candidate providers | Why it might fit | Required validation before action |
| --- | --- | --- | --- |
| Cheap probe | Brave, Serper, DataForSEO Standard/Live | Low-cost or index-diverse discovery can test whether cheaper SERP-style probes produce useful candidate URLs. | URL yield, source quality, citation usefulness, duplicate rate, queue latency, compliance posture, and integration effort. |
| Ordinary retrieval | Tavily, Exa, Brave | Tavily is the current default; Exa can contribute semantic/document discovery; Brave can add index diversity if evidence quality is proven. | Cost per successful citable source, depth sensitivity, overlap across generated queries, and fetchability. |
| Targeted fetch/extract | Firecrawl, Jina Reader, Linkup fetch, Tavily extract | Fetch/extract can pair with cheap probes when search returns URLs but not enough clean content. | Page/action/token costs, extraction quality, paywall behavior, latency, raw-content safety, and citation traceability. |
| Semantic discovery | Exa | Current semantic/general/academic specialist and Deep Research fit for docs, code, academic, and research-style retrieval. | Unique source discovery over Tavily, academic/domain-constrained yield, and quantitative-path exclusion impact. |
| Source-constrained retrieval | Tavily, Exa, Linkup, possibly Brave Goggles/DataForSEO query strategy | Existing providers support include/exclude domain constraints in different forms; SERP providers may approximate constraints through query strategy. | Whether constrained retrieval improves citation precision enough to offset extra calls and integration complexity. |
| Premium/deep escalation | Linkup deep, Exa Deep Search, Tavily advanced, Firecrawl deep crawl/browser workflows | Deep paths may improve hard retrieval cases but can dominate total cost. | Escalation reason quality, marginal source yield, deep-mode cost blowup, duplicate answer risk, and latency. |
| Answer/synthesis endpoint | Linkup sourced answer, Exa Answer, Tavily-style answer features | Answer endpoints can provide diagnostic context with source links. | Diagnostic only; must not replace Author/Analyst. Measure duplication, citation traceability, and downstream synthesis impact. |

## Hidden Costs and Gotchas

Credits can hide unit cost. Provider plans may charge by request, credit, depth, page, browser action, extraction, token volume, or bundled package, so each estimate needs a unit basis and observed date.

Answer endpoints can duplicate work already assigned to Analyst, Economist, or Author. They may be useful as evidence context, but using them as synthesis endpoints risks paying twice and blurring provenance.

Deep modes dominate cost when they become the default path. Linkup deep, Exa Deep Search, Tavily advanced, and crawl/browser workflows need explicit escalation reasons and depth telemetry.

Raw SERP providers externalize work to FauxPlex: URL normalization, dedupe, fetch, extraction, cleaning, ranking, citation selection, freshness detection, source-quality filtering, and failure handling.

Rate limits and queue latency matter. A low unit price can still be a poor fit if queue mode is too slow, live mode changes the price, or rate limits force retries and fallbacks.

Compliance and privacy posture differs across web search, SERP scraping, extraction, browser automation, answer endpoints, and enterprise data products. Cheap unit price is not sufficient for provider selection.

Pricing changes quickly. Any implementation or procurement phase should refresh observed provider pricing and capability docs before converting this diagnostic model into estimates, code, or vendor policy.

## Recommended Telemetry Fields

- `provider_role`
- `provider_cost_class`
- `query_similarity_to_previous`
- `result_url_overlap_with_previous`
- `new_domain_count`
- `new_source_count`
- `unique_citable_source_count`
- `escalation_reason`
- `skipped_near_duplicate_query_count`
- `provider_request_cost_estimate`
- `provider_successful_request_count`
- `provider_failed_request_count`
- `provider_unit_cost_basis`
- `provider_pricing_observed_date`
- `provider_depth`
- `provider_fetch_or_extract_count`
- `provider_answer_endpoint_used`
- `provider_raw_content_received`

## Explicit Non-Recommendations

- No provider swap yet.
- No routing change yet.
- No new cheap SERP integration yet.
- No answer endpoint as an Author or Analyst replacement.
- No live eval based on this doc alone.
- No production provider pricing policy from this doc alone.
- No prompt, retrieval, source filtering, Analyst, Economist, Author, telemetry, SQLite, replay, summarizer, or weak-corpus behavior change.

## Suggested Next Branch

Suggested branch: `phase-13c-provider-role-cost-telemetry`

Lane: Review Lane

Scope: diagnostics-only implementation after this document is reviewed.

The next phase should add telemetry that can answer provider role and cost questions without changing live routing or provider behavior.
