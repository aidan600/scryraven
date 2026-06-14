# AG-96B0 Official Search Stack Doctrine

## 1. Status and scope

Status: architecture/design doctrine plus static adapter inventory.

AG-96B0 is a docs/design phase for ScryRaven's official-source search-stack
strategy before any AG-96B1 runtime implementation. It uses repo-visible files
only.

This phase made no runtime behavior changes, ran no live validation, made no
provider calls, and made no provider routing changes. It does not change search
depth, provider selection, provider order, prompt prose, final-answer behavior,
source-specific resolvers, package names, CLI names, environment names, or
`core/pipeline_orchestrator.py`.

Pricing and current provider-market facts are out of scope for this repo-static
phase unless already present in repo-tracked docs. No web browsing was used.

## 2. Diagnosis: what AG-96A1-A5 proved

Static repo inspection found AG-96A0 and AG-96A2 architecture docs, plus AG-96A2
through AG-96A5 test coverage. The test-backed shape proves the following
current design facts:

- Official/current recovery can execute through the existing source-class
  recovery lane.
- Authority Acquisition Decision / corridor policy exists for
  `hard_corridor`, `soft_corridor`, and `discovery_corridor`.
- Hard-corridor authority/domain planning can reach provider dispatch when the
  decision authorizes provider domain constraints.
- Hard domains are not merely trace fields: AG-96A5 tests show domains such as
  `uscis.gov` and `ssa.gov` can reach lifecycle action metadata and then
  provider-facing `include_domains` / `exa_domain_filter` construction.
- Final admission can work when answer-bearing official evidence is found:
  AG-96A4 fixtures admit official USCIS/SSA answer-bearing candidates.
- Generic official pages must fail candidate fit: AG-96A4 fixtures reject
  generic USCIS/SSA pages that are official but not answer-bearing.
- The remaining issue is provider/search-stack acquisition quality, not simply
  lost hard-domain constraints before provider dispatch.

That last point matters. Post-AG96A4 dogfood suggested USCIS and SSA planning
could identify the right official corridor, while selected search still failed
to retrieve answer-bearing official pages. AG-96A5 makes the likely next
failure layer provider/search-stack strategy: provider jobs, mode budget, index
diversity, query shaping, bridge-only discovery, evidence-gap-driven follow-up
search, and final evidence admission boundaries.

## 3. What remains unproven

AG-96B0 does not prove:

- whether any specific provider would have found the answer-bearing USCIS or
  SSA page in live search;
- whether Exa, Linkup, Brave, or Tavily is best for official acquisition;
- whether cheap scout providers are needed;
- whether Balanced/Deep evidence-gap loops should be implemented yet;
- whether discovery-corridor international authority search needs a separate
  design;
- whether provider pricing, rate limits, index quality, or current product
  behavior favors any provider.

Those require runtime implementation, live validation, provider-specific
experiments, or product/cost decisions outside this docs-only phase.

## 4. Provider jobs, not provider hierarchy

AG-96B0 doctrine is provider jobs, not provider hierarchy. ScryRaven should
select provider surfaces for the job they are being asked to do, not by a fixed
global ranking such as "Provider A before Provider B forever."

The relevant jobs are:

| Job | Purpose | Final evidence posture |
| --- | --- | --- |
| Scout / disambiguation / query-shaping | Cheaply identify entity, agency, title, form, table, document ID, likely official URL, or missing search term before a heavier official acquisition attempt. | Bridge-only unless fetched/read/admitted under canonical custody. |
| Direct official candidate search | Retrieve official/current candidate URLs under hard, soft, or discovery corridor constraints. | Candidate only until fetched/read and candidate-fit succeeds. |
| Semantic recall | Find conceptually relevant official or canonical pages when exact keyword search is brittle. | Candidate only until fetched/read and admitted. |
| Fetch/read/extract | Convert candidate URLs or provider raw content into readable source text and chunks. | Eligible only if source custody, readability, source class, currentness, and candidate-fit gates pass. |
| Provider answer/deep/synthesis products | Provider-generated answer or deep/research output, often with cited sources. | Bridge/context only; not final official evidence by itself. |

The same provider may fit more than one job. The same job may be filled by more
than one provider over time. AG-96B0 deliberately avoids a provider bake-off.

## 5. Static provider capability inventory

Inspection boundary: repo code and repo docs only. Capabilities below are
apparent from code, not from external provider documentation or marketing.
Where a capability is not clear from code, it is marked unclear.

Cross-cutting routing/fetch/scout surfaces inspected:

- `core/routing.py::select_providers` appears to own the central provider
  selection matrix for Tavily, Linkup, and Exa by query type, intent,
  complexity, report type, academic posture, overrides, and premium escalation.
- `core/provider_plan.py::ProviderPlan` records provider/depth facts selected by
  existing policy for main retrieval, continuation, supplemental retrieval, and
  Scrutineer remediation roles. It records and projects facts; it does not call
  providers.
- `core/pipeline_orchestrator.py` currently seeds provider availability from
  `TAVILY_API_KEY`, `LINKUP_API_KEY`, and `EXA_API_KEY`, then delegates to
  `ProviderPlan` / `select_providers`. This file was inspected only to locate
  current ownership and was not changed.
- `core/pipeline.py::process_search_queries` is the provider-facing dispatcher
  for Tavily, Linkup `searchResults`, and Exa in normal retrieval and
  source-class recovery.
- `core/source_class_recovery_executor.py` applies hard-corridor official
  domains to `include_domains` and `exa_domain_filter` before calling
  `process_search_queries(..., provider_role="source_class_recovery")`.
- `core/retrieval.py::fetch_page`, `fetch_url_text`, and `chunk_text` provide
  fetch/read/extract behavior after candidates are selected for fetching.
- `core/scout.py::run_scout` is a model-based evidence scout, not a web-search
  provider scout. Brave's code surface is separate and lightweight.

### Tavily

Code locations inspected:

- `core/search_providers.py::search_web_results`
- `core/pipeline.py::process_search_queries`
- `core/routing.py::select_providers`
- `core/provider_plan.py`
- `core/source_class_recovery_executor.py`
- `docs/architecture/AG51B_SOURCE_ACQUISITION_ARCHITECTURE_REVIEW.md`
- `tests/test_ag96a5_official_authority_search_execution.py`

Surfaces/functions/classes/configs found:

- `search_web_results(...)` posts to Tavily search.
- `process_search_queries(...)` uses Tavily when `search_providers` contains
  `"tavily"` or when no explicit provider list is supplied and fallback chooses
  Tavily.
- `select_providers(...)` commonly returns Tavily for news, quantitative, and
  default general retrieval paths when available.
- Source-class recovery can pass its `provider_role="source_class_recovery"`
  through the same `process_search_queries(...)` path.

Apparent supported controls:

- `search_depth`;
- `include_domains`;
- `exclude_domains`;
- `max_results`;
- `topic` inferred as news/general;
- raw content requested by `include_raw_content=True`;
- image inclusion;
- cost accounting phase/provider logging.

Plausible job fit based only on repo code:

- Direct official candidate search.
- Fetch/read assist through Tavily raw content when full fetch is skipped or
  falls back.
- Existing default official-source lane when current routing selects or inherits
  Tavily.

Unclear or missing capabilities:

- No separate Tavily official-acquisition role is visible in code.
- No repo-static proof that Tavily will retrieve USCIS/SSA answer-bearing pages.
- No repo-static proof of provider-side ranking behavior under domain filters.

Cautions:

- Tavily may remain the existing direct official path if current wiring supports
  it best, but AG-96B0 must not assert Tavily is permanently the default.
- A Tavily depth change would be a runtime search-depth change and belongs in a
  later implementation phase.

### Exa

Code locations inspected:

- `core/search_providers.py::search_exa_results`
- `core/search_providers.py::get_exa_client`
- `core/pipeline.py::process_search_queries`
- `core/routing.py::select_providers`
- `core/provider_plan.py`
- `core/source_class_recovery_executor.py`
- `docs/architecture/AG51B_SOURCE_ACQUISITION_ARCHITECTURE_REVIEW.md`
- `tests/test_ag96a5_official_authority_search_execution.py`

Surfaces/functions/classes/configs found:

- `search_exa_results(...)` calls Exa `search_and_contents`.
- The request uses `type="neural"` and `text=True`.
- `process_search_queries(...)` calls Exa only when `"exa"` is selected and
  `EXA_API_KEY` is present.
- `select_providers(...)` prefers Exa for academic general queries when
  available and includes Exa in default general retrieval for low/medium/high
  where available.
- Source-class recovery can merge hard-corridor official domains into
  `exa_domain_filter`.

Apparent supported controls:

- `include_domains`;
- `exclude_domains`;
- `start_published_date`;
- `end_published_date`;
- `num_results`;
- text content retrieval;
- no depth parameter visible in repo code.

Plausible job fit based only on repo code:

- Semantic recall candidate.
- Direct official candidate search when include-domain constraints are supplied.
- Candidate text source through Exa's returned text.

Unclear or missing capabilities:

- No repo-static proof that Exa is better or worse than Tavily/Linkup for
  official acquisition.
- No visible Exa-specific official-source mode beyond include/exclude domain
  and date controls.
- No depth equivalent is visible.

Cautions:

- Exa should be treated as a semantic recall candidate, not assumed as the
  default fallback.
- Existing academic routing can make Exa useful for literature, but prior docs
  warn that academic-domain filters can be the wrong source universe for
  canonical or official pages.

### Linkup

Code locations inspected:

- `core/search_providers.py::search_linkup_results`
- `core/pipeline.py::process_search_queries`
- `core/pipeline.py::fetch_linkup_precision_block`
- `core/routing.py::select_providers`
- `core/provider_plan.py`
- `core/source_class_recovery_executor.py`
- `docs/architecture/AG51B_SOURCE_ACQUISITION_ARCHITECTURE_REVIEW.md`
- `tests/test_provider_diagnostics.py`
- `tests/test_ag96a5_official_authority_search_execution.py`

Surfaces/functions/classes/configs found:

- `search_linkup_results(...)` supports `output_type="searchResults"` and
  `output_type="sourcedAnswer"`.
- Normal retrieval uses Linkup `searchResults` through `process_search_queries`.
- `fetch_linkup_precision_block(...)` uses Linkup `sourcedAnswer` with
  `depth="deep"` for high complexity only and returns an Author-context block.
- `select_providers(...)` includes Linkup mainly for high complexity or explicit
  override/premium escalation.

Apparent supported controls:

- `depth` values passed by code include `fast`, `standard`, and `deep`;
- `outputType` values include `searchResults`, `sourcedAnswer`, and a
  structured schema branch in adapter code;
- `includeDomains`;
- `excludeDomains`;
- `fromDate`;
- `toDate`;
- `maxResults`;
- `includeInlineCitations` and `includeSources` for `sourcedAnswer`.

Plausible job fit based only on repo code:

- Direct official candidate search through `searchResults`.
- Provider answer/deep/synthesis bridge through `sourcedAnswer`.
- Possible scout or bridge source when the output is treated as non-final
  candidate discovery.

Unclear or missing capabilities:

- The repo does not show Linkup `sourcedAnswer` wired into source-class recovery
  as final evidence.
- The repo does not prove Linkup `deep` or `sourcedAnswer` would find
  USCIS/SSA answer-bearing official pages.
- It is unclear from code whether Linkup has any distinct "research" product
  beyond the `sourcedAnswer` and `searchResults` surfaces used here.

Cautions:

- Linkup `searchResults` must be distinguished from Linkup
  `sourcedAnswer`/deep behavior.
- Provider answer text and "sources consulted by Linkup" are not canonical
  ScryRaven evidence custody by themselves.
- Using Linkup deep/answer behavior for final official evidence would be a
  high-custody runtime behavior change and is deferred.

### Brave

Code locations inspected:

- `core/search_providers.py::brave_reconnaissance`
- `core/provider_validation.py`
- `core/routing.py`
- `core/provider_plan.py`
- `proplex/__main__.py`
- `tests/test_search_provider_errors.py`
- `docs/architecture/AG51B_SOURCE_ACQUISITION_ARCHITECTURE_REVIEW.md`

Surfaces/functions/classes/configs found:

- `brave_reconnaissance(...)` uses Brave web search and returns title, URL,
  snippet, and age.
- It is described in code as lightweight search for entity/term resolution only.
- `BRAVE_API_KEY` appears in provider validation and CLI environment notes.

Apparent supported controls:

- query string;
- result count;
- English search language in current code;
- `freshness="pw"` in current code;
- timeout and provider error logging.

Plausible job fit based only on repo code:

- Scout / disambiguation / query-shaping candidate.
- Bridge hint discovery of official URLs, titles, document IDs, agency paths, or
  better query terms.

Unclear or missing capabilities:

- Brave is not visible as a normal `process_search_queries(...)` evidence
  provider.
- No include-domain or exclude-domain control is visible in the
  `brave_reconnaissance(...)` function.
- No fetch/read/extract integration is visible in the Brave function itself.

Cautions:

- Brave Search should be considered primarily as an early scout /
  disambiguation / query-shaping candidate, not as a late normal evidence
  provider.
- Treat Brave results as bridge hints unless a later fetch/read/admission path
  brings the official source into canonical custody.

## 6. Provider-role doctrine

ScryRaven owns query planning, evidence admission, and synthesis. Provider
snippets/search results may discover candidates or bridge hints, but final
evidence and citations must come from canonical admitted source custody.

Provider answer/deep/research products must not satisfy final official evidence
by themselves. If a provider answer names an official URL, title, document ID,
table, form, or agency path, ScryRaven may use that as a bridge hint, fetch/read
the canonical source, and then admit or reject that source under normal custody
rules.

Provider roles:

- Linkup `searchResults`, if selected, is a search-result/candidate surface.
- Linkup `sourcedAnswer`/deep behavior, if used, is a provider answer/deep
  product and must remain citation-ineligible unless canonical sources are
  separately fetched/read/admitted.
- Brave, if present, is an early scout/disambiguation/query-shaping candidate.
- Exa, if present, is a semantic recall candidate and may also perform direct
  official candidate search under explicit domain constraints.
- Tavily may remain the existing direct official path where current wiring
  supports it, but this document does not make Tavily a permanent default.

## 7. Corridor behavior

Official-source acquisition should preserve the corridor model introduced by
AG-96A2.

`hard_corridor`: known or strong official authority. Search may be constrained
to official domains when the Authority Acquisition Decision permits provider
domain constraints. Final evidence must be answer-bearing official/current
evidence.

`soft_corridor`: likely authority hints. Candidate domains, agencies, venues, or
titles may guide query terms, ordering, diagnostics, or bridge-hint handling, but
must not silently become hard provider filters.

`discovery_corridor`: unknown, off-list, international, ambiguous, or
role-described authority discovery. The system should discover the competent
authority and must not force U.S. federal shortcuts merely because a known U.S.
authority family has lexical overlap.

For all corridors, lower-tier sources may be leads, not substitutes, when an
official/current obligation is active.

## 8. Mode contract

Fast is recipe-bounded.

Fast should use a small, deterministic official-source acquisition recipe. It
may have a tiny conditional branch, such as one cheap scout or one bounded retry
after candidate-fit failure. It should answer from admitted official evidence or
refuse quickly. Fast should remain mostly deterministic and productized.

Balanced is judgment-bounded.

Balanced uses the same official-source acquisition core but with a modest budget
and authority to reason over evidence gaps. RunAuthority/SearchJudgment may
inspect source gaps and authorize targeted follow-up search. Bridge hints are
allowed under citation-ineligible labels. Balanced stops or refuses when budget,
sufficiency, or custody says to stop.

Deep is judgment-bounded with a larger budget.

Deep uses the same official-source acquisition core but may perform broader
official discovery, conflict/currentness checks, and source comparison. It still
operates under explicit provider, cost, fetch, read, query, and follow-up caps.
Final evidence admission remains strict.

Balanced and Deep must not be specified as fixed recipes like "exactly 2
searches" or "exactly 5 searches." They should be specified by budget,
evidence-gap reasoning, authorized targeted follow-up, explicit caps, and
custody-preserving admission.

## 9. Balanced/Deep follow-up search doctrine

Balanced and Deep follow-up search should use this loop:

```text
reason over current evidence
-> identify the specific source gap
-> authorize targeted follow-up search
-> fetch/read candidates
-> update EvidenceLedger / SearchJudgment / SufficiencyJudgment
-> decide whether to stop, refuse, or continue within budget
```

Guardrail: follow-up search in Balanced/Deep must be evidence-gap-driven, not
provider-driven.

Good examples:

- "We are missing the answer-bearing official fee table."
- "We found an official page, but it is generic."
- "We found conflicting currentness signals."
- "We need the official notice/table/update page."

Bad example:

- "Try another provider because we can."

This doctrine permits provider diversity only when the current evidence gap
names the job a provider surface can perform. Provider choice follows from the
gap, not curiosity about the provider.

## 10. Bridge-only source policy

Bridge sources may help discover official candidates. They must not satisfy
final official evidence or citation obligations.

Proposed metadata/eligibility posture:

```text
bridge_only=true
citation_eligible=false
final_evidence_eligible=false
```

Bridge hint types may include:

- `official_url`;
- `official_title`;
- `document_id`;
- `agency_subpath`;
- `query_term`;
- `authority_candidate`;
- `effective_date_hint`.

Examples of bridge-only sources include provider snippets, provider answer/deep
output, secondary explainers, news articles, or scout results that point toward
an official source. The official source still has to be fetched/read, classified,
checked for answer-bearing fit/currentness, and admitted into canonical custody.

## 11. AG-96B1 implementation recommendation

Recommend AG-96B1 as a Fast-only runtime implementation.

AG-96B1 should implement:

- Fast recipe-bounded official-source lane;
- provider roles selected by job and existing adapter capability, not fixed
  provider hierarchy;
- optional early scout/disambiguation when needed and supported;
- direct official candidate search;
- fetch/read;
- candidate-fit;
- one bounded retry from a concrete bridge hint;
- answer from admitted official evidence or refuse.

AG-96B1 must not be framed as "make USCIS and SSA pass." USCIS and SSA may be
useful validation families, but the implementation target is the generic
Fast-mode official-source lane and its custody-preserving failure posture.

AG-96B1 should stop before changing Balanced/Deep runtime loops, provider
answer/deep product admission, source-specific resolvers, final-answer/citation
behavior, or provider bake-off policy.

## 12. Deferred work

Deferred explicitly:

- runtime provider routing changes until AG-96B1;
- provider bake-off;
- live-gated evaluation;
- new provider selection;
- cheap scout provider integration;
- discovery-corridor international authority search;
- Balanced/Deep runtime follow-up loop implementation;
- provider answer/deep/research products;
- final-answer/citation rewrite;
- source-specific official resolvers;
- provider pricing/current-facts evaluation;
- package/CLI/env rename work.

AG-96B0 intentionally leaves implementation choices for AG-96B1 and later
phases. The design decision here is the doctrine: Fast is recipe-bounded;
Balanced and Deep are judgment-bounded; provider work is job-based; bridge
sources are not final evidence; and final official evidence remains governed by
canonical custody.
