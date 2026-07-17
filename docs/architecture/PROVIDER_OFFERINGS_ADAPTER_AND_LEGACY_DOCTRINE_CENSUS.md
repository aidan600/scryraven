# Provider Offerings, Adapter, and Legacy-Doctrine Census

Status: current decision census
Authority: owner-approved provider acquisition target doctrine
Default-read: no
Applies-to: provider offerings, installed adapters, current consumers, provider-material authority, and migration dispositions
Does-not-authorize: implementation, live calls, provider selection changes, or claims that target capabilities are installed
Verified-against-runtime: e444c2e098e90b18c67bea34d057718a61b586d7
Vendor-documentation-checked: 2026-07-16

## 1. Outcome and boundary

This is the read-only, offline census for
`PROVIDER-OFFERINGS-ADAPTER-AND-LEGACY-DOCTRINE-CENSUS-01`. It separates what
vendors offer, what ScryRaven has adapted, what an ordinary product can reach,
what material receives authority, and what the owner has selected as target
doctrine. The original census changed none of those runtime facts; this current
owner now records the completed semantic Scout and ordinary provider-synthesis
retirement without changing the dated vendor-offering section or the selected
target doctrine. **Basis: OWNER_DECISION, CURRENT_RUNTIME.**

The source-of-truth order is:

1. current code and tests for current execution;
2. the owner-approved phase decision for target doctrine;
3. current official vendor documentation for dated vendor offerings; and
4. historical repository documents for migration evidence and rationale only.

Historical rules are not retained merely because they exist. Target rules are
not described as installed. **Basis: OWNER_DECISION.**

This census uses these non-equivalent states:

| State | Meaning |
| --- | --- |
| **Vendor offered** | The dated official vendor documentation describes the operation or variant. |
| **Adapter installed** | Current repository code can construct the request and normalize a response. |
| **Ordinary enabled** | A current supported product composition includes the adapter, conditionally if configured. |
| **Ordinary reachable** | A current product execution can reach the callsite when its key, gate, and request conditions are satisfied. |
| **Authority granted** | Returned material is permitted to affect queries, evidence, analysis, or final-answer custody; this is narrower than reachability and is stated per row. |

`RETAIN`, `REPLACE`, `RETIRE`, and `DEFER_PENDING_PROOF` below are target
dispositions, not completed runtime changes. **Basis: OWNER_DECISION.**

## 2. Dated external offerings

All vendor facts in this section were checked against official documentation on
2026-07-16. No provider API was called. Volatile pricing, quotas, and latency
claims are intentionally excluded from target policy. **Basis:
DATED_VENDOR_DOCUMENTATION.**

- [Linkup Search](https://docs.linkup.so/pages/documentation/endpoints/search/overview)
  offers `fast`, `standard`, and `deep` search. The documented topology says
  `fast` avoids LLM query reinterpretation, `standard` is a single-iteration
  agentic search with parallel adjacent searches and can scrape one supplied
  URL, and `deep` can chain multiple search/read iterations. Search output can
  be `searchResults`, `sourcedAnswer`, or `structured`; domain/date constraints
  and result/image controls are available.
- [Linkup Fetch](https://docs.linkup.so/pages/documentation/endpoints/fetch/reference)
  accepts one selected webpage URL and returns extracted Markdown, with options
  for images, raw HTML, and JavaScript rendering.
- [Linkup Research](https://docs.linkup.so/pages/documentation/endpoints/research/post)
  is an asynchronous comprehensive-research surface whose outputs are
  `sourcedAnswer` or structured data.
- [Tavily API](https://docs.tavily.com/documentation/api-reference/introduction)
  lists Search, Extract, Crawl, Map, and Research. [Search](https://docs.tavily.com/documentation/api-reference/endpoint/search)
  supports basic/advanced depth, general/news topics, answer/raw-content/image,
  domain, and date controls. [Extract](https://docs.tavily.com/documentation/api-reference/endpoint/extract)
  reads specified URLs with optional query-focused reranking. [Map](https://docs.tavily.com/examples/quick-tutorials/map-api)
  discovers site structure/URLs without returning page content, while
  [Crawl](https://docs.tavily.com/documentation/api-reference/endpoint/crawl)
  traverses a site and extracts bounded content. [Research](https://docs.tavily.com/documentation/api-reference/endpoint/research)
  searches, analyzes, and generates a report.
- [Exa Search](https://exa.ai/docs/reference/search) supports search with
  optional content extraction, domain/date controls, semantic modes, and a
  research-paper category. [Exa Contents](https://exa.ai/docs/reference/get-contents)
  retrieves content for caller-supplied URL IDs/URLs with content, summary,
  metadata, and cache/live controls.
- [Serper](https://serper.dev/) offers real-time Google Search API surfaces,
  including web, image, and news results. This census relies only on its web
  result shape for the installed adapter.
- [Brave Web Search](https://api-dashboard.search.brave.com/api-reference/web/search/get)
  offers web search from Brave's independent index with query, count, freshness,
  and related controls. Brave's other vendor surfaces are outside the installed
  adapter inventory.

## 3. Consolidated required census matrix

The following is the controlling row-level inventory. “None” means no current
repository adapter or consumer was found, not that the vendor lacks the
capability. Historical references are migration evidence only. **Basis by row:
DATED_VENDOR_DOCUMENTATION, CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION; any
inference is explicitly marked.**

| Provider | Vendor endpoint / operation | Dated vendor-offering fact | Current repository adapter | Actual parameters exposed now | Current ordinary product consumer | Validation / operator-only consumer | Returned material class | Authority posture | Current provider role | Current selection rule | Current depth / variant rule | Target role hypothesis | Disposition | Rationale | Required implementation phase | Live comparative proof? | Historical doctrine references |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Linkup | Search `fast/searchResults` | Fast search, no LLM query reinterpretation | `search_linkup_results` | `q`, `depth`, `outputType`, `maxResults`, images, include/exclude domains, from/to date | Main retrieval can reach it only through an explicit low-complexity Linkup override; no automatic selector chooses it | Generic acquisition tests and brokered diagnostics can select it | Search-result name, URL, content | Candidate/source material only after ordinary gates | No distinct current role | Explicit user override can bypass the normal high-complexity Linkup gate | Adapter accepts `fast`; main dispatcher maps low complexity to `fast` | Possible low-cost discovery variant, not selected doctrine | DEFER_PENDING_PROOF | Target doctrine selects standard as the owner-selected target; fast needs quality/cost proof | Provider-capability routing foundation, then comparative proof | Yes | [AG96B0](../history/architecture/phases/AG96B0_OFFICIAL_SEARCH_STACK_DOCTRINE.md) |
| Linkup | Search `standard/searchResults` | Single-iteration agentic acquisition; adjacent parallel searches; one supplied URL may be scraped | `search_linkup_results`; generic acquisition adapter | Same Search controls; `depth=standard`, `outputType=searchResults` | Main retrieval, continuation/supplemental retrieval when selected; generic single-relation product path when explicitly configured | Brokered discovery and source-of-record decision tools | URL-bound provider-extracted content | May become evidence material only through current ranking/custody path; provider name grants no truth | General/domain-targeted search today | Linkup available and high complexity, user override, or premium escalation; main dispatcher defaults medium/high to standard | `standard` except explicit override | Owner-selected target for ordinary general and domain-targeted `DISCOVER`; `OWNER_SELECTED_TARGET_NOT_INSTALLED` | REPLACE | Keep the operation and later replace inherited high-complexity/provider-name gating with capability routing. Provider material remains acquisition material. Comparative proof may revise the policy but is not required to select it. | Provider-capability routing foundation | Yes, before factual comparative quality, coverage, latency, cost, or reliability claims; not required for target selection | [AG91A](../history/architecture/phases/AG91A_PRE_RETRIEVAL_QUERY_DEPTH_PROVIDER_AUTHORITY_MAP.md), [AG91C](../history/architecture/phases/AG91C_PROVIDERPLAN_SEARCH_DEPTH_AUTHORITY_SEED.md) |
| Linkup | Search `deep/searchResults` | Multi-iteration chained discovery and reading | Installed/carryable through `search_linkup_results` | `depth=deep`, `outputType=searchResults`, normal filters | Scrutineer remediation can select deep; legacy saved-thread follow-up carries deep but is not an ordinary product | Tests cover dispatch and operator paths | Multi-page URL-bound provider-extracted content | Current remediation results re-enter evidence integration; no special truth authority | High-complexity remediation/premium search | Scrutineer remediation hard-codes deep when its authorized novel-query path runs and Linkup is selected | Coupled to high-complexity eligibility in routing; not a separate acquisition-requirement decision | Optional premium, triggerable multi-iteration acquisition escalation | DEFER_PENDING_PROOF | Technically reachable, but triggers/custody/cost telemetry are not capability-owned and Deep mode alone must not trigger it | Provider-capability routing foundation, then bounded deep activation phase | Yes | [AG51B](../history/architecture/phases/AG51B_SOURCE_ACQUISITION_ARCHITECTURE_REVIEW.md), [AG91C](../history/architecture/phases/AG91C_PROVIDERPLAN_SEARCH_DEPTH_AUTHORITY_SEED.md) |
| Linkup | Search `sourcedAnswer` | Vendor-written natural-language answer with citations | Installed in `search_linkup_results`; separate precision helper retained for named nonordinary validation | `outputType=sourcedAnswer`, commonly `depth=deep`; structured schema omitted | None; ordinary precision eligibility, call, and Analyst-context injection are retired | Diagnostics and provider-error tests observe the lower-level output type | Provider-written synthesis plus cited sources | No ordinary authority or reachability; generic acquisition rejects it | None | No ordinary selector | Lower-level helper can carry deep sourced answer only in named nonordinary tests | Disabled | RETIRE — completed ordinary retirement | ScryRaven acquires sources/material, not provider answers | Completed with semantic Scout retirement | No; doctrine decision is closed | [AG96B0](../history/architecture/phases/AG96B0_OFFICIAL_SEARCH_STACK_DOCTRINE.md) |
| Linkup | Search `structured` | Vendor-generated JSON under caller schema | Partial request carriage only: payload supports a schema, but no structured-response normalizer or caller was found | `outputType=structured`, `structuredOutputSchema` | None | None found | Provider-generated structured synthesis | No ordinary authority found | None | No installed selector | No installed rule | Disabled | RETIRE | It is a provider synthesis surface, not source acquisition | Provider-synthesis ordinary-product closure guard | No | [AG96B0](../history/architecture/phases/AG96B0_OFFICIAL_SEARCH_STACK_DOCTRINE.md) |
| Linkup | Fetch | Known-URL webpage extraction | None | None | None | None | Caller-selected URL-bound page material | None installed | None | None | None | `READ` leading hypothesis | DEFER_PENDING_PROOF | Operation fits known-URL reading, but custody, errors, rendering, and telemetry need design/validation | Linkup known-URL read adapter | Yes, for bounded live behavior | [AG96I3J](../history/architecture/phases/AG96I3J_OFFLINE_FETCH_READ_CURRENTNESS_VERIFICATION.md), [AG96I3K](../history/architecture/phases/AG96I3K_SANITIZED_READ_OBSERVATION_ADAPTER.md) |
| Linkup | Research | Async provider research producing synthesized output | None | None | None | None | Provider-written research/report | None installed | None | None | None | Disabled | RETIRE | Provider research/report generation is outside source acquisition | Provider-synthesis ordinary-product closure guard | No | [AG96B0](../history/architecture/phases/AG96B0_OFFICIAL_SEARCH_STACK_DOCTRINE.md) |
| Tavily | Search | Search with basic/advanced, general/news, raw content and filters | `search_web_results`; generic acquisition adapter | JSON API key, query, depth, topic, answer false, images true, raw content true, max results, domains; news day window | Main, continuation, supplemental and recovery retrieval; supported single-relation product acquisition | Brokered diagnostics and provider-decision operator | Result URL/snippet plus provider-extracted raw content | May enter current evidence flow after gates; provider identity alone satisfies no obligation | Broad default/news/source-recovery search | News starts with Tavily; general includes it when available; several empty selections fall back to Tavily; source-of-record config defaults to Tavily | Basic/advanced follows ScryRaven complexity/depth policy | Possible fallback `DISCOVER`; not universal default | REPLACE | Preserve possible Search use but remove provider-name defaults and capability conflation | Provider-capability routing foundation | Yes | [AG91A](../history/architecture/phases/AG91A_PRE_RETRIEVAL_QUERY_DEPTH_PROVIDER_AUTHORITY_MAP.md), [AG96B0](../history/architecture/phases/AG96B0_OFFICIAL_SEARCH_STACK_DOCTRINE.md) |
| Tavily | Extract | Read/extract specified URL(s), optionally query-focused | None | None | None | None | URL-bound extracted page material | None installed | None | None | None | Future `READ` / `FOCUSED_EXTRACT` | DEFER_PENDING_PROOF | Differentiated acquisition capability; not a reason for Tavily default search | Tavily Extract/Map/Crawl phase | Yes | [AG96I3J](../history/architecture/phases/AG96I3J_OFFLINE_FETCH_READ_CURRENTNESS_VERIFICATION.md) |
| Tavily | Map | Discover site URLs/structure without content | None | None | None | None | Site URL map | None installed | None | None | None | Future `MAP_SITE` | DEFER_PENDING_PROOF | Needs bounded site/custody contract | Tavily Extract/Map/Crawl phase | Yes | None |
| Tavily | Crawl | Traverse a site and extract bounded content | None | None | None | None | Multi-page site material | None installed | None | None | None | Future bounded `CRAWL_SITE` | DEFER_PENDING_PROOF | Needs scope, loop, cost, robots, and custody policy | Tavily Extract/Map/Crawl phase | Yes | None |
| Tavily | Research | Provider searches/analyzes/generates a report | None | None | None | None | Provider-written research/report | None installed | None | None | None | Disabled | RETIRE | Provider synthesis is ordinary-product disabled | Provider-synthesis ordinary-product closure guard | No | [AG96B0](../history/architecture/phases/AG96B0_OFFICIAL_SEARCH_STACK_DOCTRINE.md) |
| Exa | Search with contents | Search plus content extraction | `search_exa_results`; generic acquisition adapter | `query`, result count, `type=neural`, `text=True`, domains, published-date window | Main, retained continuation, supplemental and recovery retrieval when selected; generic single-relation when configured | Provider-decision and offline tests | Search result URL plus provider-extracted text/score | May enter current evidence flow after gates; no truth from provider identity | Academic specialist and general fan-out | Academic selects Exa when available; general appends it when available; no Scout-specific override remains | No current depth; repository uses legacy SDK `type=neural` | Academic, technical, or semantic `DISCOVER` on exact acquisition signal | REPLACE | Retain specialist hypothesis; remove automatic general fan-out | Provider-capability routing foundation | Yes | [AG51B](../history/architecture/phases/AG51B_SOURCE_ACQUISITION_ARCHITECTURE_REVIEW.md), [AG96B0](../history/architecture/phases/AG96B0_OFFICIAL_SEARCH_STACK_DOCTRINE.md) |
| Exa | Contents for known URLs | Retrieve full content/summaries/metadata for specified URLs | None | None | None | None | URL-bound extracted content | None installed | None | None | None | Possible future `READ`, not selected over leading hypotheses | DEFER_PENDING_PROOF | Vendor offers it, but repository has no adapter and target choice is unresolved | Later acquisition-routing decision only if needed | Yes | None |
| Serper | Web Search | Real-time Google search results | `search_scout_results`; generic acquisition adapter | `q`, `num`, optional Google-style freshness `tbs` | Explicit supported single-relation product can use it for ambiguity/candidate discovery; modern main ProviderPlan does not | Brokered discovery and provider-decision tools/tests | Title, URL, snippet, position/date | Generic acquisition marks observations non-evidence/directional; no direct evidence authority | “Scout” candidate discovery | No main-provider selector; explicit generic-product Scout provider only | Freshness supplied by provider-neutral policy when requested | `DISCOVER(lightweight_disambiguation)` | REPLACE | Keep lightweight job, retire SCOUT vocabulary and keep evidence boundary | Provider-capability routing foundation after semantic Scout retirement | Yes | [AG96I3G](../history/architecture/phases/AG96I3G_PROVIDER_NEUTRAL_SCOUT_FRESHNESS_POLICY.md), [AG96I3H](../history/architecture/phases/AG96I3H_SERPER_CHEAP_SCOUT_DIAGNOSTIC_ADAPTER.md), [AG96I3I](../history/architecture/phases/AG96I3I_SCOUT_TO_ACQUISITION_HANDOFF_DIAGNOSTICS.md) |
| Brave | Web Search | Independent-index web search with freshness controls | `search_scout_results`; `brave_reconnaissance` compatibility alias | `q`, `count`, no text decorations, English, optional freshness | Main ordinary pre-retrieval recon can call Brave for person/news/current/event queries; supported single-relation product can select it | Brokered discovery, follow-up validation, and provider-decision tools/tests | Title, URL, snippet, age | Main recon can shape queries/entity identity but does not directly create evidence; generic observations are non-evidence | Reconnaissance / “Scout” | Key present + qualifying query type + not already well scoped; separate explicit generic-product selection | Legacy alias forces past-week freshness; neutral adapter accepts policy freshness | Optional `DISCOVER(independent_index)` | REPLACE | Keep optional independent-index implementation; replace recon-specific/SCOUT naming and hard-coded freshness coupling | Provider-capability routing foundation after semantic Scout retirement | Yes | [AG91A](../history/architecture/phases/AG91A_PRE_RETRIEVAL_QUERY_DEPTH_PROVIDER_AUTHORITY_MAP.md), [AG96I3G](../history/architecture/phases/AG96I3G_PROVIDER_NEUTRAL_SCOUT_FRESHNESS_POLICY.md) |
| Brave | Answer/context/news-specific vendor surfaces | Not assessed as needed by installed web adapter | None | None | None | None | Potential provider context/answer or specialized results | No installed authority | None | None | None | Not installed; provider synthesis remains disabled | DEFER_PENDING_PROOF | This phase neither inventories unsupported endpoints as installed nor activates them | Only a later separately approved capability decision | Yes if ever proposed | None |

### 3.1 Offered, installed, enabled, reachable, and authoritative are separate

| Surface | Vendor offered | Adapter installed | Ordinary product enabled | Ordinary product reachable | Authority granted now |
| --- | --- | --- | --- | --- | --- |
| Linkup fast/searchResults | Yes | Yes | Conditional through the main dispatcher | Yes, only with configured Linkup plus an explicit low-complexity user override | Candidate/source-material path after ordinary gates |
| Linkup standard/searchResults | Yes | Yes | Yes, conditionally configured | Yes when routing/override selects Linkup | Candidate/source-material path after ordinary gates |
| Linkup deep/searchResults | Yes | Yes | Yes in bounded Scrutineer remediation | Yes when authorized remediation selects Linkup | Remediation material re-enters ordinary evidence integration |
| Linkup sourcedAnswer | Yes | Yes, including a lower-level nonordinary helper | No | No | None; ordinary precision violation closed |
| Linkup structured | Yes | Partial request carriage only | No | No caller found | None |
| Linkup Fetch / Research | Yes | No | No | No | None |
| Tavily Search | Yes | Yes | Yes | Yes when selected or reached through current fallback/default rules | Candidate/source material after ordinary gates |
| Tavily Extract / Map / Crawl / Research | Yes | No | No | No | None |
| Exa Search with contents | Yes | Yes | Yes | Yes when selected | Candidate/source material after ordinary gates |
| Exa known-URL Contents | Yes | No | No | No | None |
| Serper Web Search | Yes | Yes | Explicit single-relation product only; not modern main ProviderPlan | Yes when the explicit product requests ambiguity discovery | Directional candidate/query observations only |
| Brave Web Search | Yes | Yes | Yes in main recon and the explicit single-relation product | Yes under key/query-type/scope gates or explicit product selection | Query/entity shaping only in main recon; no direct evidence |

**Basis: DATED_VENDOR_DOCUMENTATION, CURRENT_RUNTIME, CURRENT_TEST.**

### 3.2 Exa adapter compatibility uncertainty

Current code calls the installed `exa_py` SDK with `type="neural"` and
`text=True`. The current official Search reference presents a newer set of type
values and content controls. **Inference:** the adapter may rely on legacy SDK
compatibility because the current code and current vendor reference use
different vocabulary. This census does not prove incompatibility and does not
change the adapter. **Basis: CURRENT_RUNTIME, DATED_VENDOR_DOCUMENTATION,
INFERENCE.**

## 4. Current adapter matrix

| Adapter | Providers / operations | Installed request surface | Installed response normalization | Not installed or intentionally rejected | Basis |
| --- | --- | --- | --- | --- | --- |
| `core.search_providers.search_web_results` | Tavily Search | Query, basic/advanced, news/general, result limit, domain/date posture, images and raw content | Title, URL, snippet/content/raw content, domain, credibility | Extract, Map, Crawl, Research; answer is requested false | CURRENT_RUNTIME, CURRENT_TEST |
| `core.search_providers.search_linkup_results` | Linkup Search | Query, fast/standard/deep, searchResults/sourcedAnswer/structured, result limit, images, domains, dates, optional schema | Search results or synthesized answer with sources; sourced answer can be mirrored into normalized snippets/raw content | Fetch and Research | CURRENT_RUNTIME, CURRENT_TEST |
| `core.search_providers.search_exa_results` | Exa search-and-contents | Query, result limit, neural search, text, domains, publication dates | Title, URL, text as snippet/raw content, domain, credibility, Exa score | Standalone known-URL Contents adapter | CURRENT_RUNTIME, CURRENT_TEST |
| `core.search_providers.search_scout_results` | Serper and Brave web search | Provider-neutral query, result limit, optional freshness | Candidate URL/title/snippet observations | Evidence admission, provider answer/context, other endpoint types | CURRENT_RUNTIME, CURRENT_TEST |
| `core.generic_product_provider_acquisition` | Tavily/Linkup/Exa extraction and Serper/Brave discovery | One `search` operation, provider/role, query, limits, domains/dates/freshness | Sanitized URL-bound extraction or non-evidence discovery records | Rejects Linkup `sourcedAnswer`; does not make domain constraints authoritative | CURRENT_RUNTIME, CURRENT_TEST |

The generic acquisition adapter is a separate supported single-relation product
and dogfood surface; it is not the main `ProviderPlan`/`run_pipeline` provider
dispatcher. **Basis: CURRENT_RUNTIME.**

## 5. Current ordinary-consumer matrix

| Consumer | Product posture | Providers / material reachable | Gate and selection owner | Downstream effect | Basis |
| --- | --- | --- | --- | --- | --- |
| Ordinary CLI/backend `run_pipeline` main retrieval | Current ordinary product | Tavily, Linkup, Exa search material | `ProviderPlan`, `core.routing`, mode-derived complexity/depth, key availability | Search records are ranked, filtered, fetched at high complexity where applicable, integrated, and may reach final evidence custody | CURRENT_RUNTIME, CURRENT_TEST |
| Ordinary continuation and weak-corpus/source-class recovery | Current ordinary product | Tavily, Linkup, Exa | QueryPlan/RunKernel gates plus ProviderPlan/routing | New material returns through evidence integration; providers do not themselves authorize continuation | CURRENT_RUNTIME, CURRENT_TEST |
| Scrutineer remediation | Current ordinary product | Selected providers; Linkup can receive `deep/searchResults` | Legacy review stage, authorized novel-query dispatch, ProviderPlan/routing | Remediation evidence can cause resynthesis | CURRENT_RUNTIME, CURRENT_TEST |
| Lower-level Linkup precision helper | Nonordinary validation compatibility only | Linkup `deep/sourcedAnswer` in named diagnostics/error tests | Direct test invocation only; no ordinary composition or orchestrator owner | No ordinary downstream effect; provider-written answer cannot enter Analyst context | CURRENT_RUNTIME, CURRENT_TEST |
| Brave pre-retrieval recon | Current ordinary product | Brave web-result observations | Query type, key availability, well-scoped bypass | Observations can drive model rewrite of queries and canonical subject; not direct evidence | CURRENT_RUNTIME, CURRENT_TEST |
| Explicit `--mvp-current-source-of-record-single-fact-run` | Supported, explicit-confirmation single-relation product path | Generic acquisition; Tavily extraction default and Serper ambiguity discovery by default; alternatives are adapter-capable | Product entrypoint and its provider request/config | Sanitized candidates pass through the product's acquisition/custody path | CURRENT_RUNTIME, CURRENT_TEST |
| `--mvp-single-relation-live-dogfood-run` and provider-decision commands | Explicit dogfood/operator, not ordinary main pipeline | Generic acquisition and comparison adapters | Explicit confirmation/operator flags | Diagnostic/product packets; no automatic main-pipeline activation | CURRENT_RUNTIME, CURRENT_TEST |
| Saved-thread `core.followup` provider retrieval | Legacy/non-ordinary because Streamlit product is retired | Tavily/Linkup/Exa and high-complexity deep override | Legacy follow-up parameters | Compatibility/reference behavior only | CURRENT_CANONICAL_DOC, CURRENT_RUNTIME |
| Brokered AG96I3 discovery/follow-up runners | Validation/operator only | Brave, Serper, Tavily, Linkup and selected validation surfaces | Explicit brokered runner and authorization | Sanitized diagnostics; not ordinary product evidence | CURRENT_RUNTIME, CURRENT_TEST, HISTORICAL_DOC |

## 6. Current authority matrix

| Material / decision | Producer | Current authority actually granted | Authority not granted | Target disposition | Basis |
| --- | --- | --- | --- | --- | --- |
| Provider availability | Environment key-presence booleans for Tavily/Linkup/Exa | Input to selection; no key values are needed in canonical state | No provider quality or truth authority | REPLACE with capability availability/install profile | CURRENT_RUNTIME, OWNER_DECISION |
| `ProviderPlanRecord` | `core.provider_plan` delegating to current selectors | Records and supplies already-selected provider/depth facts to dispatch | Does not invent provider policy, call providers, or admit evidence | RETAIN as boundary; adapt to capabilities later | CURRENT_RUNTIME |
| Query candidates from Brave recon or Serper/Brave discovery | Discovery observations | QueryPlan may admit/order retained discovery queries; recon may affect canonical subject | No evidence, citation, sufficiency, or final-answer authority; semantic Scout produces no candidates | Discovery roles REPLACE vocabulary/owner; semantic Scout retirement completed | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Tavily raw content, Linkup search-result content, Exa text | Provider search/extraction adapters | Can be ranked and integrated as source material; at high complexity selected pages may instead be fetched | Provider identity does not satisfy source obligation, candidate fit, truth, or citation eligibility by itself | RETAIN material acquisition; strengthen capability/custody routing | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Linkup `sourcedAnswer` precision context | Linkup lower-level validation helper only | No ordinary authority; former Analyst-context injection is retired | No source custody, evidence, citation, sufficiency, or final-answer authority | RETIRE from ordinary product — completed | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Linkup `structured` / Research and Tavily Research | Vendor synthesis surfaces | None installed for ordinary product | No ordinary-product authority | RETIRE/disabled | DATED_VENDOR_DOCUMENTATION, OWNER_DECISION |
| Source-of-record provider config | Repository config defaults extraction role to Tavily | Selects acquisition provider for the explicit single-relation recovery path | Provider name does not itself establish source-of-record status | REPLACE with source obligation and capability | CURRENT_RUNTIME, OWNER_DECISION |
| Domain/date constraints | Routing/request policy | Constrain discovery/acquisition | Do not create authority, representativeness, trust, sentiment, identity, or obligation satisfaction | RETAIN as constraints under capability owner | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Provider diagnostics/trace | Provider diagnostic builders, ProviderPlan, scheduler and projections | Observe selected role, depth/output, attempts and outcomes | Must not choose providers, admit evidence, or authorize retry | RETAIN as observer; expand only with bounded deep custody/cost facts | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |

## 7. Legacy-doctrine disposition matrix

| Legacy rule or surface | Current fact and exact reachability | Dependencies / tests / telemetry | Target disposition | Replacement or retirement scope | Basis |
| --- | --- | --- | --- | --- | --- |
| Legacy semantic Scout ordinary continuation | No ordinary prompt/model call, query candidate, gate selection, or retrieval dispatch remains | Ordinary orchestrator and focused retirement tests; passive trace/session projections only | RETIRE — completed | Ordinary execution removed; durable generic planning/recovery authority preserved | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Scout-directed query generation | No ordinary producer; prompt text/registry and model/parser path are absent | Inert `core.scout.run_scout` compatibility returns no result without prompt or model access | RETIRE — completed | No replacement semantic role installed; generic query production preserved | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Scout continuation candidacy | No Scout QueryPlan finalizer or ordinary candidacy branch remains | Generic QueryPlan and evaluator/expander continuation tests | RETIRE — completed | Generic QueryPlan admission and retrieval-stop authority preserved | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| `scout_directed_continuation` scheduling | No current scheduler constructs this stage or provider role `scout_continuation` | Scheduler structural and focused retirement tests | RETIRE — completed | Named stage/role removed; passive compatibility projections cannot dispatch | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Hard-coded Scout provider overrides | No Scout-specific `exa,linkup` override is constructed | Scheduler and focused retirement tests | RETIRE — completed | Future provider jobs remain deferred to capability routing | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Current Scout prompt/model invocation | No ordinary prompt registry binding, dependency injection, or model call remains | Inert import compatibility plus ordinary composition and behavioral guards | RETIRE — completed | Compatibility exports perform no execution or query production | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Term `SCOUT` as future capability name | Used both for semantic model helper and provider-neutral lightweight discovery, creating two meanings | Runtime names, scripts, tests, historical AG96I3 docs | RETIRE | Use capability `DISCOVER` with qualifiers such as `lightweight_disambiguation` or `independent_index`; historical names may remain historical | CURRENT_RUNTIME, HISTORICAL_DOC, OWNER_DECISION |
| Tavily source-of-record default | Explicit single-relation recovery config names Tavily extraction default | Config, authorization/product runner and tests | REPLACE | Express source-of-record as obligation; select an acquisition capability/implementation separately | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Tavily-first news | News/current selection seeds Tavily and adds preferred news domains | `core.routing`, query production/retrieval domain policy and tests | REPLACE | Freshness/source obligations choose capability; no inherited provider identity | CURRENT_RUNTIME, OWNER_DECISION |
| Phantom Tavily fallback | Empty or unavailable selections can return `tavily` even when availability is false | Routing tests expose fallback behavior | RETIRE | Fail closed or resolve an installed capability explicitly; no uninstalled phantom provider | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Default multi-provider fan-out | General high/default can select Tavily + Linkup + Exa; lower general can select Tavily + Exa | Routing and provider-allocation tests | REPLACE | One capability plan with explicit diversity/recovery jobs, not automatic provider accumulation | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Linkup high-complexity-only restriction | Non-user Linkup use is usually removed unless complexity is high or premium escalation is explicit | Routing and provider-plan tests | REPLACE | Standard eligibility follows acquisition job; complexity is an input, not provider permission | CURRENT_RUNTIME, OWNER_DECISION |
| Linkup deep coupled to generic complexity | Scrutineer remediation hard-codes deep; Linkup eligibility itself is high-complexity gated | Dispatch/legacy-review tests | REPLACE | Explicit sequential-acquisition trigger plus caps/custody/telemetry | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Linkup depth coupled to ScryRaven mode | Mode maps directly to complexity; Deep maps to high; current high still influences Linkup `searchResults` eligibility and remediation depth, while ordinary precision synthesis is retired | Query production, routing, remediation and follow-up tests | REPLACE | Linkup deep is not an automatic ScryRaven Deep-mode consequence | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Exa automatic general fan-out | General selection appends Exa whenever available | Routing tests | REPLACE | Select only for an academic, technical, or semantic acquisition signal | CURRENT_RUNTIME, OWNER_DECISION |
| Serper lightweight discovery | Adapter and explicit generic-product/broker consumers use “scout” role | AG96I3G/H/I tests and history | REPLACE | `DISCOVER(lightweight_disambiguation)`; candidate-only | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Brave lightweight discovery/recon | Ordinary recon and generic/broker Scout paths use Brave web search | Recon, query-production and AG96I3 tests | REPLACE | Optional `DISCOVER(independent_index)`; keep observations subordinate to query/custody owners | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Provider synthesis surfaces | Linkup sourcedAnswer/structured/Research and Tavily Research remain vendor/lower-level surfaces; none is ordinary reachable | Lower-level precision diagnostics and generic-acquisition rejection tests | RETIRE — ordinary closure completed | Keep provider-written answer/report/structured synthesis disabled in ordinary product | CURRENT_RUNTIME, CURRENT_TEST, DATED_VENDOR_DOCUMENTATION, OWNER_DECISION |
| Provider answers entering ordinary evidence/answer paths | Former Linkup precision Analyst-context injection is absent; lower-level adapter output cannot reach ordinary context without a current consumer | Ordinary product-path retirement and aggregate diagnostics | RETIRE — completed | Source-material-only ordinary acquisition; no provider answer in evidence/analysis payloads | CURRENT_RUNTIME, CURRENT_TEST, OWNER_DECISION |
| Source-of-record as provider-specific role | Config role/default embeds provider identity in acquisition decision | Single-relation recovery config/authorization/operator decision | REPLACE | Source obligation owns requirement; capability routing chooses implementation | CURRENT_RUNTIME, OWNER_DECISION |

### 7.1 Completed semantic Scout retirement inventory

Runtime/test commit `e444c2e098e90b18c67bea34d057718a61b586d7`
retired the complete ordinary-execution cluster, not just the active body of
`core.scout.run_scout`:

1. `SCOUT_REPORT_TYPES`, Scout prompt registry entries and prompt text in
   `core.prompts`;
2. `core.scout` prompt assembly, model invocation, JSON parsing, and eligibility
   behavior; only a fixed inert import-compatibility result remains, and ordinary
   CLI/backend composition injects no Scout dependency;
3. the iteration-one orchestrator candidacy branch, quantitative skip heuristic,
   four-query cap, QueryPlan finalization role, retrieval-stop and continuation
   spine gates;
4. `schedule_scout_continuation_from_pipeline_scope`, stage
   `scout_directed_continuation`, provider role `scout_continuation`, and the
   hard-coded `exa/linkup` override;
5. Scout-specific execution authority from query plan, trace, and session
   projections; retained fired/key/queries/skip/gate/timing fields are fixed
   passive compatibility for persistence, review, and aggregate consumers and
   are not supplied to current retrieval authorization or dispatch;
6. direct ordinary Scout unit/gate tests, replaced by retirement and retained-
   continuation preservation guards; and
7. documentation/history references, preserving historical evidence without
   preserving an ordinary runtime.

Generic QueryPlan admission, RunKernel continuation authority, retrieval-stop
policy, disambiguation, component planning, ordinary recovery and provider
diagnostics remain installed. Passive compatibility fields and the inert
`core.scout` exports have named repository consumers and cannot execute or
authorize ordinary Scout work. **Basis: CURRENT_RUNTIME, CURRENT_TEST,
OWNER_DECISION.**

## 8. Linkup standard/deep decision

Current premium policy lives in `core.routing.should_allow_linkup_provider`: it
permits Linkup for high complexity, an explicit user provider override, or an
explicit premium-search escalation. The policy contains no dated price constant.
It is provider-name/complexity policy rather than a capability-owned acquisition
decision. **Basis: CURRENT_RUNTIME.**

| Property | `standard/searchResults` | `deep/searchResults` |
| --- | --- | --- |
| Vendor acquisition topology | One agentic iteration; adjacent searches may run in parallel; one supplied URL can be scraped; no result-chained later step in the same call | Multiple provider-controlled iterations; later discovery/read steps may depend on earlier results; multiple pages may be found and read |
| Adapter installed | Yes | Yes; the same adapter can carry it |
| Current ordinary reachability | Main/continuation/supplemental and generic acquisition when Linkup is selected | Scrutineer remediation can reach it; legacy saved-thread follow-up is non-ordinary |
| Current coupling | Linkup normally requires high complexity; main dispatcher uses standard at medium/high | Remediation hard-codes deep while routing also normally limits Linkup to high complexity; therefore complexity, mode and depth are indirectly conflated |
| Target posture | Owner-selected target for ordinary general/domain-targeted discovery; `OWNER_SELECTED_TARGET_NOT_INSTALLED` | Default disabled optional premium escalation |
| Target triggers | Ordinary `DISCOVER`, including domain-targeted discovery | Inherently sequential acquisition; multiple unknown pages must be found/read; authorized recovery after bounded standard failure; fragmented material not selectable by URL; explicit premium escalation |
| Non-triggers | Not applicable | ScryRaven Deep mode, generic high complexity, detailed-answer request, news, or social-domain targeting alone |
| Disposition | REPLACE current eligibility with capability routing | DEFER_PENDING_PROOF |

Before any deep activation, one authority must record: acquisition requirement
and trigger; caller/user premium authorization; bounded iteration/page/result
caps; selected domains/dates; provider output type fixed to `searchResults`;
source URL and extraction lineage per returned material; custody/admission result;
attempt, latency and cost-accounting facts without turning volatile prices into
policy; failure/partial-result posture; and proof that no provider synthesis is
present. Comparative live proof is required before a quality or cost claim.
**Basis: OWNER_DECISION; custody/telemetry list is an INFERENCE supported by the
current absence of a capability-owned deep trigger and the target source-material
boundary.**

## 9. Provider-synthesis closure

The ordinary product now accepts sources and source material, not
provider-written answers, reports, or provider-controlled research synthesis.
Accordingly:

- Linkup `sourcedAnswer`, `structured`, and Research are ordinary-disabled
  capabilities;
- Tavily Research is disabled;
- Linkup `deep` is eligible only with `searchResults`, never as a proxy for a
  ScryRaven reasoning mode;
- provider answers must not be copied into snippets/raw content or Analyst/
  Author evidence payloads; and
- URL-bound provider extraction remains possible only through ordinary source
  lineage, readability, candidate-fit, evidence custody and citation rules.

The generic acquisition adapter's rejection of Linkup sourced answers remains
the reusable product-path boundary. The former ordinary Linkup precision block,
eligibility, response processing, and Analyst-context injection are removed.
The lower-level `deep/sourcedAnswer` helper remains explicitly nonordinary for
named offline diagnostic and provider-error tests. **Basis: CURRENT_RUNTIME,
CURRENT_TEST, OWNER_DECISION.**

## 10. Owner-approved target constellation

### `DISCOVER(general)`

Leading implementation: Linkup `standard/searchResults`

Target status: `OWNER_SELECTED_TARGET_NOT_INSTALLED`

Authority boundary: Candidate URLs and provider-extracted context only. Provider
identity grants no source, evidence, claim, citation, Sufficiency,
FinalAnswerPacket, or Author authority.

Empirical posture: No claim that Linkup is objectively the best provider has
been proved. Later licensed comparative evidence may validate, refine, or
replace this policy.

### `DISCOVER(domain_targeted)`

Leading implementation: Linkup `standard/searchResults` with bounded domain
constraints

Target status: `OWNER_SELECTED_TARGET_NOT_INSTALLED`

Authority boundary: Candidate URLs and provider-extracted context only. Bounded
domain constraints and provider identity grant no source, evidence, claim,
citation, Sufficiency, FinalAnswerPacket, Author, domain, or social authority.

Empirical posture: No claim that Linkup is objectively the best provider has
been proved. Later licensed comparative evidence may validate, refine, or
replace this policy.

The remaining target choices retain their existing status:

| Capability | Leading implementation hypothesis | Target authority boundary | Status now | Basis |
| --- | --- | --- | --- | --- |
| `DISCOVER(academic_technical_semantic)` | Exa search with content only when exact signal requires it | Candidate/source material under custody | Hypothesis; current Exa routing is broader | OWNER_DECISION, CURRENT_RUNTIME |
| `DISCOVER(lightweight_disambiguation)` | Serper | Candidate/query direction only | Adapter exists; modern main job not installed | OWNER_DECISION, CURRENT_RUNTIME |
| `DISCOVER(independent_index)` | Brave | Optional candidate/query direction only | Adapter and ordinary recon exist under legacy role | OWNER_DECISION, CURRENT_RUNTIME |
| Fallback `DISCOVER` | Tavily Search | Explicit installed fallback only; no phantom default | Hypothesis; current defaulting is broader | OWNER_DECISION, CURRENT_RUNTIME |
| `READ` known URL | Linkup Fetch leading hypothesis | Caller-selected URL, source-bound extracted material | Not adapted | OWNER_DECISION, DATED_VENDOR_DOCUMENTATION |
| `READ` / `FOCUSED_EXTRACT` | Tavily Extract | Selected URL(s), optional query focus, source-bound material | Not adapted | OWNER_DECISION, DATED_VENDOR_DOCUMENTATION |
| `MAP_SITE` | Tavily Map | URL discovery only | Not adapted | OWNER_DECISION, DATED_VENDOR_DOCUMENTATION |
| bounded `CRAWL_SITE` | Tavily Crawl | Explicit root/scope/caps and page-level custody | Not adapted | OWNER_DECISION, DATED_VENDOR_DOCUMENTATION |
| Premium sequential acquisition | Linkup `deep/searchResults` | Explicit trigger, caps, lineage and cost/custody telemetry | Carryable and remediation-reachable, not target-activated | OWNER_DECISION, CURRENT_RUNTIME |
| Source-of-record requirement | Source obligation, not provider role | Obligation/candidate-fit/custody owners | Current provider-specific config must be replaced | OWNER_DECISION, CURRENT_RUNTIME |
| Provider synthesis/research | No ordinary implementation | Disabled in ordinary product | Ordinary Linkup precision violation closed; lower-level nonordinary helper retained for diagnostics | OWNER_DECISION, CURRENT_RUNTIME, CURRENT_TEST |

Social-domain discovery may use ordinary domain-targeted discovery such as a
`reddit.com` constraint. It grants no social authority, representativeness,
sentiment, identity, or trust posture. **Basis: OWNER_DECISION.**

## 11. Installation profiles and capability overlays

Profile labels are future composition and diagnostic labels; profile labels are
not product modes. Profile labels create no authority and do not create automatic provider fan-out.
Arbitrary valid provider subsets remain supported,
and capability resolution derives from the providers and adapters actually
installed and available. No installation must exactly match a named profile.
Linkup-only remains valid. Comparative proof may revise policy but is not required to select the target.

These deployment profiles describe a future progression, not routing installed
by this census:

| Profile | Providers | Target capabilities | Boundaries |
| --- | --- | --- | --- |
| Minimal: Linkup | Linkup | Linkup `standard/searchResults` for general `DISCOVER`; Linkup `standard/searchResults` for domain-targeted `DISCOVER`. | Linkup-only remains a valid ordinary installation; Serper is not required; known-URL `READ` remains unavailable until the separately licensed Linkup Fetch phase; no provider synthesis; no automatic fan-out. |
| Practical: Linkup + Serper | Linkup + Serper | Linkup general and domain-targeted discovery; Serper lightweight disambiguation and candidate discovery. | Serper remains candidate/query direction only; Serper is not evidence authority; no provider fan-out merely because both providers are configured. |
| Research: Linkup + Serper + Exa + Tavily | Linkup + Serper + Exa + Tavily | Linkup general and domain-targeted discovery; Serper lightweight disambiguation; Exa academic, technical, or semantic discovery when an exact acquisition signal requests it; Tavily explicit fallback discovery and future differentiated site-acquisition implementations. | Exa is not an automatic general co-provider; Tavily is not a universal default; no provider-name source-of-record authority; no automatic provider ensemble. |
| Diversity: Linkup + Serper + Exa + Tavily + Brave | Linkup + Serper + Exa + Tavily + Brave | All Research profile capabilities; Brave as optional independent-index discovery. | Brave is not an ordinary duplicate call; Brave does not become a main evidence or answer provider merely because it is configured; diversity requires an explicit future acquisition job or recovery policy. |

Optional future capability overlays remain separate from the deployment
profiles. They extend a valid provider composition only after their separately
licensed implementation; they do not place noninstalled capabilities in a
current profile:

| Capability overlay | Future composition | Noninstalled boundary |
| --- | --- | --- |
| `known_url_read` | Linkup Fetch and/or other selected URL-reader adapters | Depends on later Linkup Fetch and/or other selected URL-reader adapter phases; no Research/sourcedAnswer and no authority from the extraction provider. |
| `site_acquisition` | Tavily Extract, Map, and bounded Crawl | Depends on Tavily Extract, Map, and Crawl work; no unbounded crawl or automatic site authority. |
| `premium_sequential` | Linkup `deep/searchResults` | Depends on separately licensed triggers, caps, lineage, premium authorization, and custody/telemetry proof; default off, with no mode-only trigger or synthesis output. |

## 12. Exact recommended implementation sequence

Completed prerequisite:
`LEGACY-SEMANTIC-SCOUT-ORDINARY-EXECUTION-RETIREMENT-01` at runtime/test commit
`e444c2e098e90b18c67bea34d057718a61b586d7`.

1. Provider-capability routing foundation: introduce provider-neutral
   acquisition jobs/qualifiers and installation availability; replace Tavily
   phantom/default doctrine, automatic general fan-out, Exa general fan-out,
   Tavily-first news, provider-specific source-of-record, Linkup complexity-only
   eligibility, and mode/depth coupling. Reuse ProviderPlan as the ordinary
   consumed boundary.
2. Linkup known-URL read adapter: implement bounded `READ` through Fetch with
   source/custody lineage and no synthesis.
3. Tavily Extract/Map/Crawl: install distinct `READ`/`FOCUSED_EXTRACT`,
   `MAP_SITE`, and bounded `CRAWL_SITE` capabilities.
4. Acquisition-routing closure if required: retire residual provider-name roles,
   compatibility defaults, or parallel selectors discovered by the preceding
   implementation phases.
5. Bounded final-custody convergence.
6. Separately licensed live comparative validation, including any Linkup deep
   activation decision. Offline census does not license it.
7. Social-source authority and Social Awareness Specialist design/validation.
8. Conversation and UI work through transport-neutral product services.

**Basis: OWNER_DECISION.**

## 13. Unresolved decisions and live-proof register

The following remain deliberately unresolved:

- whether later comparative quality, coverage, latency, and cost evidence should
  cause the owner-selected Linkup-first general-discovery policy to be retained,
  refined, or replaced;
- whether Linkup fast has a useful bounded role;
- exact Linkup deep triggers, caps and premium authorization representation;
- whether Linkup Fetch, Tavily Extract, or Exa Contents should fill each known-
  URL reading subcase;
- the exact Tavily Search fallback posture;
- whether and when provider diversity warrants more than one discovery job;
- current `exa_py type="neural"` compatibility with the vendor's current API/
  SDK vocabulary;
- exact Hosted and Local provider subsets and capability availability; and
- social-source authority, sampling, representativeness, trust and Specialist
  policy.

Every provider-quality, relative-cost, latency, coverage, currentness, deep
utility, known-URL extraction, map, and crawl claim requires separately licensed
bounded live proof. Provider synthesis prohibition, source-obligation ownership,
and semantic Scout retirement are owner decisions and do not require a provider
bake-off. **Basis: OWNER_DECISION, INFERENCE supported by the absence of live
comparative evidence in this audit.**

## 14. Nonproofs

This current census plus the cited offline retirement does not prove or install:

- provider routing, ordering, quality, availability, price, latency or capacity;
- empirical Linkup standard superiority, installed Linkup-first routing, or deep
  activation;
- known-URL reading, focused extraction, site mapping, site crawling or Research;
- evidence correctness, source-obligation satisfaction, citation eligibility,
  final custody or improved answer quality;
- social-source authority or Social Awareness capability;
- live provider, model, search, fetch/read or complete-app behavior; or
- any access to secrets, private data, caches, database rows, logs, traces,
  packets, or unrelated artifacts.

**Basis: OWNER_DECISION, audit execution record.**

## 15. Principal proof classification

```text
Execution surface class:
VALIDATION

Product consumer reached:
ordinary CLI/backend runtime through the cited offline retirement commit; this
document is the canonical projection of that runtime evidence

Claim permitted:
semantic Scout ordinary execution and ordinary Linkup provider synthesis are
retired; retained provider adapters, ordinary consumers, authority posture,
legacy doctrine, and owner-approved target dispositions remain explicitly
inventoried and separated

Claim forbidden:
provider routing changes, Linkup deep activation, known-URL reading, site
mapping or crawling, live provider quality, evidence correctness, or improved
answer quality
```
