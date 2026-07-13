Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG72R_PROVIDER_SEARCH_ALLOCATION_REVIEW).

# AG-72R Provider/Search Allocation Review

Scope: Review Lane diagnostic-first phase. No live ScryRaven/proplex queries,
provider/model/search calls, provider routing/depth/selection changes, provider
swaps, new providers, retrieval ranking/filtering changes, prompt changes,
citation/final-answer changes, Author posture changes, direct IRS hardcoding,
package/CLI/env compatibility changes, or broad `pipeline_orchestrator.py`
domain logic changes were made.

Branch: `codex/ag72r-provider-search-allocation-review`

Base commit: `d8eee52` (`Merge pull request #4 from aidan600/codex/ag71a-irs-official-current-acquisition-review`)

## Phase Goal

Review whether the remaining IRS official/current acquisition failure from
AG-70C and AG-71A should be attributed to provider/source acquisition limits,
provider/search allocation, source acquisition strategy, or still-unproven
query/candidate-fit/visibility behavior.

Goal status: met as an offline repo-visible diagnostic review. The result is
deliberately bounded because AG-72R did not run live validation and did not
inspect raw provider payloads, raw prompts, DB rows, private logs, caches, full
traces, or ignored local output packets.

## Primary Classification

Primary category: inconclusive.

Confidence: medium. Repo-visible evidence can describe the current allocation
and its blind spots, but cannot prove which live sublayer lost the satisfying
IRS official/current source.

## Secondary Contributing Factors

- Existing-provider allocation/query-acquisition limits remain plausible:
  medium/general recovery uses the existing `tavily` plus `exa` allocation when
  all keys are available, while `linkup` remains excluded unless complexity is
  high or an explicit/premium escalation exists.
- Search-depth policy limit remains plausible: Balanced/medium recovery reuses
  `basic` depth and `results_per_query` from the active retrieval pass.
- Provider result filtering or post-provider candidate shaping remains
  plausible: sanitized diagnostics expose provider result counts, accepted URL
  counts, new source counts, recovered domain previews, and source-class counts,
  but not raw provider URLs/content. A provider could have returned a relevant
  IRS page that was not accepted, embedded, source-classified, or visible.
- A source-specific official adapter/resolver strategy remains a possible later
  design branch, but offline evidence does not prove that a generic provider
  allocation cannot acquire IRS authority.
- AG-71B remains a fallback, not the primary next branch, because AG-71A and
  AG-72R offline fixtures show satisfying IRS candidates can survive
  fit/visibility when they reach that boundary.

## Evidence

AG-70C live validation showed the IRS 2026 business mileage-rate query reached
recovery admission and execution, returned candidates, and still produced no
accepted/readable or final official/current IRS authority. The final answer
correctly refused to overclaim.

AG-71A showed, offline, that:

- IRS-specific recovery queries include the target year, standard mileage-rate
  subject, official notice, and revenue-procedure terms.
- Recovery official-domain constraints include `irs.gov` and federal
  official/legal domains.
- A satisfying offline `irs.gov` candidate labeled as
  `official_current_rules` becomes accepted/readable and final-selected
  authority evidence.

AG-72R reviewed the current provider/search seams:

- `core.routing.select_providers` returns `["tavily", "exa"]` for a
  medium/general run when Tavily, Linkup, Exa, and Brave are all available.
  Linkup is only included for high complexity or explicit/premium escalation.
- `core.pipeline_orchestrator.choose_retrieval_search_depth` keeps
  medium/basic retrieval at `basic`; source-class recovery inherits the active
  pass depth.
- `core.source_class_recovery_executor.execute_source_class_recovery_action`
  executes one controller-approved `source_class_recovery` action, reuses the
  selected provider list and search depth, and overlays official-domain
  constraints into `include_domains` and Exa's domain filter.
- `core.pipeline.process_search_queries` then calls the selected providers,
  deduplicates seen URLs, uses snippets/raw content for medium complexity,
  applies source classification and optional embedding filtering, and emits
  sanitized provider diagnostics.
- `core.official_canonical_recovery_candidate_acquisition`,
  `core.official_canonical_recovery_visibility_export`, and
  `core.source_class_recovery_diagnostics` expose compact counts/statuses but
  intentionally do not reveal raw provider payloads or raw provider URL lists.

## Decision

The AG-71A "provider/source acquisition limits" classification should be
downgraded to inconclusive for the narrower AG-72R provider/search question.
Offline repo evidence proves that the current system dispatches a plausible
IRS-targeted recovery action through existing providers with official-domain
constraints, and that a satisfying IRS candidate would survive downstream
fit/visibility. It does not prove whether the live failure was caused by:

- existing-provider allocation/query limits;
- `basic` search depth/results budget;
- provider result filtering or post-provider shaping;
- missing IRS/federal-agency resolver strategy;
- or an exact live query/candidate readability/visibility issue.

AG-72R therefore should not open a provider policy, provider-depth, provider
swap, new-provider, prompt, citation, final-answer, or Author repair.

## Diagnostic Tests Added

Added:

- `tests/test_ag72r_provider_search_allocation_review.py`

The tests prove:

- medium/general provider policy excludes Linkup without high complexity or
  explicit/premium escalation;
- medium/basic retrieval remains `basic`;
- source-class recovery reuses the existing provider allocation and depth;
- IRS official-domain constraints are overlaid onto the existing allocation
  for both include domains and Exa domain filtering;
- no provider routing, provider selection, provider depth, ranking, prompt,
  citation, final-answer, Author behavior, direct IRS hardcoding, or broad
  `pipeline_orchestrator.py` domain logic is changed.

Consumers:

- this AG-72R decision record;
- the recommended bounded live validation request.

Keep/remove guidance:

- Keep while the AG-72R/AG-72 follow-up chain is active.
- Promote into generic recovery allocation regression coverage if a later live
  gate finds allocation/depth is the actual repair surface.
- Remove or fold into existing AG-71A/source-class recovery tests once the IRS
  acquisition branch is resolved.

## Recommended Next Branch

Recommended next branch: bounded live validation request with exact budget and
decision.

Budget:

- maximum live ScryRaven/proplex runs: 2 total;
- exact first run: the AG-70C IRS query,
  `What is the current IRS standard mileage rate for business use of a car in 2026, and what official source supports it? Keep the answer concise.`;
- second run only if the first run is mechanically invalid or lacks the
  sanitized diagnostics needed for the decision, using the same query and same
  mode/corridor settings;
- no independent browser/search checks;
- no raw provider payloads, raw prompts, DB rows, private logs, caches, full
  traces, secrets, `.env`, or unscoped local output packets.

Decision target:

- If source-class recovery provider diagnostics show zero provider results or
  zero accepted URLs from the official-domain recovery pass, open AG-72A scoped
  existing-provider allocation/query-acquisition repair or a depth/design
  decision, depending on the observed provider/depth counts.
- If provider diagnostics show provider results but recovered/accepted
  visibility remains absent, open a provider result filtering/post-provider
  candidate shaping review.
- If recovered candidates include non-IRS secondary domains while official
  IRS/federal domains are constrained but absent, consider AG-72B
  source-specific official adapter/resolver design review.
- If an IRS official/current candidate reaches accepted/readable or final
  authority evidence and then fails source-fit/visibility/citation, reopen
  AG-71B or the appropriate downstream lifecycle phase.
- If diagnostics remain insufficient, stop for a product/design decision about
  whether to license raw/live diagnostic inspection, provider-depth changes, or
  source-specific resolver design.

## Closed Surfaces

Remained closed:

- provider swaps or new provider integration;
- provider routing, provider selection, and provider depth/search-depth policy;
- Linkup/Tavily/Exa/Brave role policy;
- retrieval ranking/filtering;
- broad prompt behavior;
- citation behavior and final-answer behavior;
- Author posture and Analyst/Economist/Author handoffs;
- direct IRS answer/source hardcoding;
- broad `pipeline_orchestrator.py` domain logic;
- package/CLI/env compatibility behavior;
- live validation/provider/model/search calls.

## Behavior Changes

None. Added behavior is limited to offline diagnostic tests and this decision
record.
