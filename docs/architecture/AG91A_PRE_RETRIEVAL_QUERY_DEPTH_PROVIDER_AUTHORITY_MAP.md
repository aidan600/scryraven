# AG-91A Pre-Retrieval Query / Depth / Provider Authority Map

Status: docs-first architecture/static audit; no runtime behavior change; no live validation

Branch: `ag-91a-pre-retrieval-query-depth-provider-authority-map`
Base: `main`

## 1. Purpose and non-goals

AG-91A maps the protected pre-retrieval query/depth/provider surface that remains
in `core/pipeline_orchestrator.py` after the AG-90 orchestrator burn-down. This
phase is intentionally an authority map and migration charter, not a burn-down or
behavior phase.

This document answers which decisions still live in the orchestrator, which are
already represented by `QueryPlan`, which are provider/depth policy decisions,
which are live-call or side-effect boundaries, and which legacy authority paths
must be deleted, demoted, bypassed, or subordinated in later implementation
phases.

Closed for AG-91A:

- runtime behavior changes;
- prompt text changes;
- query text/order changes;
- `QueryPlan` mutation changes;
- provider routing/selection changes;
- search-depth changes;
- retrieval execution changes;
- embedding cadence changes;
- ranking/filtering/final-evidence/citation/Author changes;
- persistence/cache/ProjectSource side effects;
- live provider/model/search calls.

Protected means high-custody and parity-sensitive, not forbidden. Future phases
may touch protected query/provider/depth surfaces only when they can prove exact
consumed-authority parity and explicitly retire the old authority path.

## 2. Current line count and static callsite inventory

### 2.1 Orchestrator line count

Static command: `wc -l core/pipeline_orchestrator.py`

- `core/pipeline_orchestrator.py`: **5,069** lines.

### 2.2 `ask_model(...)` callsites

Static command: AST walk over `core/pipeline_orchestrator.py` for calls whose
function name or attribute is `ask_model`.

| Line | Surface | Phase classification | Protected status | Notes |
|---:|---|---|---|---|
| 1720 | Router intent/report/query-type classification | Pre-retrieval live model call | Protected live model call | Produces `router_text`, then normalized by `build_router_query_preparation_state(...)`. |
| 1740 | Router retry/entity correction | Pre-retrieval live model call | Protected live model call | Fires when normalized router state has no entities. |
| 1873 | Session-title generation | Pre-retrieval-adjacent live model call | Protected live model call | User-visible title, not query authority. |
| 1933 | Recon rewriter/query replacement | Pre-retrieval live model call | Protected live model call | Consumes Brave recon context and may replace initial queries plus canonical subject. |
| 2039 | Researcher initial query planner | Pre-retrieval live model call | Protected live model call | Runs only when recon did not seed `queries`. |
| 3520 | Expander continuation query generation | Retrieval-loop live model call | Protected live model call | Query continuation, not initial pre-retrieval, but shares `QueryPlan` boundary. |
| 3612 | Gap evaluator continuation query generation | Retrieval-loop live model call | Protected live model call | Query continuation and retrieval-stop boundary. |
| 4274 | Economist preflight gate | Post-retrieval live model call | Protected live model call | Out of AG-91A implementation scope except inventory completeness. |
| 4667 | Author final response | Final-answer live model call | Protected live model call | Closed surface. |

Remaining pre-retrieval `ask_model(...)` callsites are therefore lines **1720,
1740, 1873, 1933, and 2039**.

### 2.3 `embed_texts(...)` callsites

Static command: AST walk over `core/pipeline_orchestrator.py` for calls whose
function name or attribute is `embed_texts`.

| Line | Surface | Phase classification | Protected status | Notes |
|---:|---|---|---|---|
| 2169 | Embedding kickoff for `_embed_topic` | Pre-retrieval live embedding call | Protected live embedding/action boundary | Uses entities/primary entity/core topic/query and configured embedding provider/model/base URL. |

### 2.4 Provider/depth selector callsites

Static command: AST walk plus `rg` for `select_providers`,
`merge_search_provider_overrides`, `choose_retrieval_search_depth`, and
`choose_supplemental_search_depth`.

| Line | Surface | Owner today | Protected status | Notes |
|---:|---|---|---|---|
| 785-797 | `choose_retrieval_search_depth(...)` definition | Orchestrator local function | Protected provider/depth policy | Returns advanced for explicit escalation or high complexity; otherwise base depth. |
| 799-810 | `choose_supplemental_search_depth(...)` definition | Orchestrator local function | Protected provider/depth policy | Same base policy for synthesis-gap supplemental retrieval. |
| 1805-1822 | Initial complexity/budget/search-depth matrix | Orchestrator local branch | Protected product policy | Seeds `max_queries`, `results_per_query`, `search_depth`, `top_chunks`, `max_iterations`. |
| 2172-2176 | Provider availability inputs | Orchestrator local environment snapshot | Protected provider input | Reads only presence of Tavily/Linkup/Exa keys; do not inspect secrets. |
| 3181-3185 | Main-loop depth selection | Orchestrator local callsite | Protected provider/depth policy | Computes effective depth consumed by retrieval dispatch. |
| 3192-3199 | Main-loop provider override merge and provider selection | `core.routing` plus orchestrator callsite | Protected provider policy | Merges user/scout overrides with availability, then selects ordered providers. |
| 3489-3494 | Scout continuation provider override | `core.routing` plus orchestrator callsite | Protected provider policy | Forces available Exa/Linkup preference for Scout-directed continuation. |
| 3572-3576 | Expander continuation provider selection | `core.routing` plus orchestrator callsite | Protected provider policy | Seeds next pass providers for component queries. |
| 4556-4557 | Legacy review dependency injection for provider/depth selectors | Orchestrator coordinator | Protected call-shape boundary | Passes selector functions into `legacy_review_runtime_stage`. |
| `core/legacy_review_runtime_stage.py` 250-255 | Supplemental depth/provider selection | Legacy review runtime stage | Protected provider/depth policy | Uses injected selectors for supplemental retrieval. |

### 2.5 `QueryPlan`-related callsites

Static command: AST walk plus `rg` for `query_authority`, `QueryPlan`, and
adapter methods.

| Line(s) | Surface | Existing authority object | Notes |
|---:|---|---|---|
| 1988-1996 | Build `QueryPlanRuntimeAdapter` | `QueryPlan` via adapter | Created after router/recon/canonical subject updates. |
| 1998-2006 | Local `_finalize_retrieval_queries(...)` facade | `QueryPlanRuntimeAdapter.finalize(...)` | Compatibility wrapper in orchestrator; should be deleted/demoted later. |
| 2056 | Initial/recon query finalization | `QueryPlan` | Applies query admission and optional official bias. |
| 2067-2069 | Recency merge | `QueryPlan` | `authorize_recency_merge(...)` records the inserted recency query and output order. |
| 2070-2072 | Final max-query cap/no-bias finalization | `QueryPlan` | Applies cap after recency merge. |
| 3175-3180 | Execution-query admission and `queries_by_iteration` projection | `QueryPlan` | Runtime retrieval consumes ordered queries from adapter-maintained state. |
| 3240 | Disambiguation retry finalization | `QueryPlan` | Entity-correction role. |
| 3311-3315 | Weak-corpus recovery finalization | `QueryPlan` | Recovery role with official bias. |
| 3454-3461 | Scout continuation finalization | `QueryPlan` | Continuation role. |
| 3532-3534 | Expander continuation finalization | `QueryPlan` | Continuation role. |
| 3633-3635 | Evaluator continuation finalization | `QueryPlan` | Continuation role. |
| `core/legacy_review_runtime_stage.py` 242 | Supplemental finalization | `QueryPlan` | Supplemental role. |
| `core/legacy_review_runtime_stage.py` 379 | Scrutineer remediation finalization | `QueryPlan` | Remediation role after novelty filter. |
| 4850-4855 | QueryPlan trace merge | `QueryPlan.to_trace_fragment()` | Trace projection, not a new authority. |

### 2.6 Recon/router/title/nutrition/query-rewrite callsites

| Line(s) | Surface | Current owner | Notes |
|---:|---|---|---|
| 1712-1724 | Router model call | Orchestrator callsite + model provider | Live call; raw output normalized by router contract. |
| 1727-1731 | Router state normalization | `RouterQueryPreparationState` builder | Passive deterministic contract for router facts. |
| 1733-1752 | Router retry model call and normalization | Orchestrator callsite + router contract | Retry is triggered by orchestrator-local emptiness check. |
| 1754-1765 | Router fields copied into locals | Orchestrator locals | Duplicate authority risk: local mutable copies of contract fields. |
| 1767-1771 | Nutrition override | Orchestrator local branch + nutrition detector | Overrides `report_type` to quantitative comparison when detected. |
| 1773-1776 | Focus/news forced overrides | Orchestrator local branch | Mutates `is_academic` and `intent` after router contract. |
| 1864-1879 | Session-title generation | Orchestrator live callsite | Not query identity; still a live model action. |
| 1881-1973 | Brave recon invocation and recon rewriter | Orchestrator live search/model callsites | May set `queries`, `recon_fired`, `canonical_subject_resolved`, and `primary_entity`. |
| 1975-1986 | Canonical subject/entity-list merge | Orchestrator local branch | Mutates entity facts before building `QueryPlan`. |
| 2008-2052 | Research planner fallback | Orchestrator live model callsite | Produces initial `queries` only when recon did not. |
| 2073-2098 | Runtime posture attached to router contract | `with_router_query_runtime_posture(...)` | Projection of already-computed routing/query/budget facts. |

## 3. Decision inventory table

Legend:

- **Protected status**: high-custody parity surface, not forbidden.
- **Behavior-changing?**: whether moving ownership can accidentally alter output
  or live call shape.
- **Projection-only?**: safe only if it serializes already-computed facts and is
  not consumed as policy.

| Decision surface | Current owner | Current code surface / function / line range | Runtime consumer | Existing authority object, if any | Desired owner | Protected status | Behavior-changing or projection-only? | QueryPlan should own? | ProviderPlan / future ProviderAuthority should own? | RunAuthority should own? | Old authority path to delete/demote/bypass | First possible implementation phase | Parity tests required |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Router intent/report/query type | Orchestrator live callsite plus `RouterQueryPreparationState` normalization | `pipeline_orchestrator.py` 1712-1724, 1727-1731; `router_query_preparation_contract.py` 177-248 | Query planner, budgets, provider selection, evidence/source-class logic, trace | `RouterQueryPreparationState` passive contract | Router executor emits observation; RunAuthority authorizes action; QueryPlan consumes only query-relevant facts | Protected live model call and product classifier | Behavior-changing if prompt/call shape/field precedence changes | No, except query-type/entity facts used to initialize QueryPlan | Yes for provider/depth inputs derived from router fields | Yes for action authorization | Demote mutable local router field copies to consumed contract fields | AG-91B for boundary inventory/contract consumption; later router executor phase | Exact router call-shape fixture; normalized-field parity; downstream budget/provider/query parity |
| Router retry / entity correction | Orchestrator decides retry when no entities | `pipeline_orchestrator.py` 1733-1752; contract retry provenance in `router_query_preparation_contract.py` 196-248 | Entity list, primary entity, disambiguation, embedding topic, QueryPlan init | `RouterQueryPreparationState.router_retry_provenance`; QueryPlan only records later disambiguation finalization | RunAuthority authorizes retry; Router executor performs retry; QueryPlan admits resulting query-affecting observations | Protected live model call | Behavior-changing if retry trigger, prompt, or fallback precedence changes | Partially: entity-correction query admission belongs to QueryPlan, retry action does not | No | Yes | Delete orchestrator-local `if not ...entities` retry authority after executor/authorization exists | AG-91D after AG-91B boundary tightening | Retry/no-retry trigger parity; raw-call shape parity; entity fallback/retry normalization parity |
| Recon invocation | Orchestrator local gating and Brave callsite | `pipeline_orchestrator.py` 1881-1903; diagnostics 1904-1918, 1957-1972 | Recon rewriter, provider diagnostics, query source, canonical subject | None for action authorization; provider diagnostics list is local | RunAuthority authorizes recon action; Recon executor performs search; ProviderAuthority owns recon-provider availability/input policy | Protected live search call | Behavior-changing if gate, API key availability, num_results, query text, diagnostics, or exception handling changes | No, only subsequent rewritten queries should be admitted | Yes for recon provider/input policy | Yes | Delete/demote `_recon_qt`/`_well_scoped`/env-gated local recon branch once authorized action exists | AG-91D or AG-91E, after query boundary parity | Recon gate matrix parity; Brave call-shape parity; diagnostics success/failure parity; no live calls in unit tests |
| Recon rewrite / query replacement | Orchestrator local parse and assignment | `pipeline_orchestrator.py` 1919-1957, 1975-1986 | Initial queries, `recon_fired`, `canonical_subject_resolved`, `primary_entity`, entities, QueryPlan adapter init | QueryPlan finalizes rewritten query text after assignment but does not own replacement admission yet | QueryPlan owns admission of recon rewrite candidates; RunAuthority owns model action | Protected live model + query mutation | Behavior-changing if replacement/admission/primary-entity precedence changes | Yes | No | Yes for action | Delete direct `queries = rqq` and direct `primary_entity = csub` as independent authority; replace with QueryPlan/contract admission | AG-91B should start here as passive/admission boundary; AG-91D can collapse action | Exact rewritten-query text/order parity; recon confidence/canonical subject parity; QueryPlan trace consumed, not trace-only |
| Session-title generation | Orchestrator live callsite | `pipeline_orchestrator.py` 1864-1879 | Session metadata/output | None | RunAuthority/session executor authorizes title action; orchestrator coordinates | Protected live model call, but not query/provider authority | Behavior-changing if prompt/call/fallback changes | No | No | Yes | Demote from pre-retrieval query block; do not mix into QueryPlan work | Not AG-91B; separate session/lifecycle action phase if needed | Title call-shape and fallback parity |
| Strategy complexity / mode budget | Orchestrator local matrix | `pipeline_orchestrator.py` 1798-1822; posture projection 2073-2098 | Query caps, results per query, base search depth, top chunks, max iterations, effort | Router contract projects budget seed facts; no consumed authority object | Future ProviderPlan/RunAuthority split: RunAuthority owns lifecycle budget; ProviderPlan owns search budget/depth inputs | Protected product/provider policy | Behavior-changing if any numeric cap changes | QueryPlan should consume max-query caps but not own strategy policy | Yes for search/result/depth inputs | Yes for run budget authorization | Delete/demote local matrix after consumed plan exists; avoid trace-only budget plan | AG-91C | Golden budget matrix parity for Fast/Balanced/High; downstream query cap/depth/provider parity |
| Search-depth selection | Orchestrator local function and callsite | `choose_retrieval_search_depth(...)` 785-797; main-loop call 3181-3185 | Main retrieval dispatch | QueryPlan trace marks depth policy unchanged only | Future ProviderPlan/ProviderAuthority | Protected provider/depth policy | Behavior-changing if depth string or escalation semantics change | No | Yes | Possibly RunAuthority authorizes retrieval action with depth | Delete local function or subordinate it behind consumed ProviderPlan decision | AG-91C | Depth matrix parity by complexity/base/iteration/explicit escalation; retrieval dispatch call-shape parity |
| Supplemental-depth selection | Orchestrator local function passed into helper | `choose_supplemental_search_depth(...)` 799-810; injection 4557; helper use `legacy_review_runtime_stage.py` 250 | Supplemental retrieval dispatch | None beyond injected function | Future ProviderPlan/ProviderAuthority | Protected provider/depth policy | Behavior-changing if supplemental search depth changes | No | Yes | Yes for action authorization | Delete/demote function injection once ProviderPlan/authorized retrieval action carries depth | AG-91C or AG-91E | Supplemental depth parity; legacy-review dependency call-shape parity |
| Provider availability inputs | Orchestrator reads env-key presence | `pipeline_orchestrator.py` 2172-2176 | `select_providers(...)`, override merge, recon gate | None | ProviderAuthority input snapshot | Protected provider input and secret-adjacent boundary | Behavior-changing if key names, booleans, timing, or fallback changes | No | Yes | RunAuthority may reference provider availability snapshot | Delete local `available_keys` dict as authority after ProviderAuthority snapshot is consumed | AG-91C | Availability boolean parity without reading secret values; no `.env`/secret inspection |
| Provider selection / provider role inputs | `core.routing.select_providers(...)` plus orchestrator callsites | `routing.py` 107-173; `pipeline_orchestrator.py` 3192-3199, 3489-3494, 3572-3576; helper use `legacy_review_runtime_stage.py` 251-255 | Main retrieval, Scout/Expander continuation, supplemental retrieval, diagnostics | None; provider diagnostics initialized locally | ProviderAuthority/ProviderPlan owns ordered provider decisions and role inputs | Protected provider routing | Behavior-changing if order, override, suppression, Linkup gating, or fallback changes | No | Yes | Yes for authorized retrieval action | Delete direct callsites or subordinate to consumed ProviderPlan; preserve `core.routing` as policy implementation if desired | AG-91C | Provider matrix/order parity; override and availability parity; provider-role diagnostics parity |
| QueryPlan initial observation | Orchestrator builds adapter after local entity/recon mutations | `pipeline_orchestrator.py` 1988-1996; `query_plan_runtime_adapter.py` 194-212 | Query finalization/admission/trace | `QueryPlan` | QueryPlan should be initialized from authoritative router/recon observations, not mutable locals | Protected query authority | Behavior-changing if init facts differ | Yes | No | No except lifecycle | Delete/demote local pre-init entity mutation as independent source | AG-91B | QueryPlan initial facts parity; trace and consumed query parity |
| Query finalization | QueryPlan via orchestrator facade | `pipeline_orchestrator.py` 1998-2006, 2056, 2070-2072; `query_plan.py` 254-414 | `current_queries`, retrieval loop, trace | `QueryPlan` | QueryPlan | Protected query text/order | Behavior-changing if text/order/dedup/budget/official bias changes | Yes, already | No | No | Delete local `_finalize_retrieval_queries` wrapper once callsites call adapter/plan directly or consume authorized plan | AG-91B | Exact query text/order/dedup/cap parity; QueryPlan trace consumed by retrieval loop |
| Recency merge | Orchestrator decides gate/text; QueryPlan merges order | Gate/text in `pipeline_orchestrator.py` 2060-2067; authorization in `query_plan.py` 417-437 | `current_queries`, trace, router posture | `QueryPlan` owns merge admission/order after local gate/text construction | QueryPlan should own query mutation/admission; source/date policy helper may remain subordinate | Protected query mutation | Behavior-changing if inserted query text/order changes | Yes | No | No | Delete local recency query insertion as independent mutation; make QueryPlan consume gate facts or own mutation | AG-91B | Exact recency gate/text/order parity across news/current/person cases |
| Official/current/canonical bias insertion | QueryPlan finalization plus weak-corpus seed helper | `query_plan.py` 326-386; `_weak_corpus_recovery_seed_queries(...)` 900-902; calls 2056, 3311-3315 | Initial/recovery query text; official-current source recovery expectations | QueryPlan records official bias metadata; `OfficialCurrentSourceCustodyState` owns custody satisfaction | QueryPlan owns query bias mutation; OfficialCurrentSourceCustody owns custody satisfaction | Protected query/source-custody boundary | Behavior-changing if query insertion changes; projection-only for custody metadata | Yes | No | No | Delete any non-QueryPlan official query insertion not subordinated to QueryPlan | AG-91B for initial/recovery query boundary; separate official/current phase for custody | Query bias text/order parity; custody metadata remains unsatisfied unless custody owner satisfies it |
| Query ordering | QueryPlan plus local list assignments | `query_plan.py` 205-236, 388-414; `pipeline_orchestrator.py` 2056-2072, 3175-3180, 3388, 3566, 3714 | Retrieval loop and `queries_by_iteration` | `QueryPlan` | QueryPlan | Protected query order | Behavior-changing | Yes | No | No | Delete local `current_queries = ...` authority where not directly consuming QueryPlan-approved list | AG-91B | Exact per-iteration `queries_by_iteration` parity and retrieval dispatch ordering parity |
| Weak-corpus recovery seed queries | Orchestrator deterministic helper plus QueryPlan finalization | `_weak_corpus_recovery_seed_queries(...)` 812-923; call 3302-3315; decision 3317-3388 | Weak-corpus controller and recovery retrieval pass | `QueryPlan` finalizes recovery; `WeakCorpusRecoveryDecision` authorizes recovery | QueryPlan owns query admission; weak-corpus controller/RunAuthority owns recovery action | Protected recovery query behavior | Behavior-changing if seeds/order/cap/official bias changes | Yes for admission; seed generation may become QueryPlan-adjacent policy only if explicitly licensed | No, except retrieval action inputs | Yes | Delete/demote seed helper from orchestrator or make it a subordinate pure candidate producer consumed by QueryPlan | Not first; AG-91B can map boundary, later recovery phase | Seed text/order/cap/near-duplicate parity; weak-corpus decision parity |
| Conflict-resolution query inputs | Conflict/evidence-state controllers, orchestrator lifecycle builders | `pipeline_orchestrator.py` 2350, 2549, 2785, 3017, 3895, 4030-4034; conflict controller modules | Evidence integration/checkpoint/ordinary continuation | `ConflictResolutionDecision`, evidence-state summaries; not QueryPlan for pre-retrieval | ConflictResolutionController/RunAuthority; QueryPlan only if queries are scheduled for retrieval | Protected retrieval-continuation surface | Mostly projection until scheduled; behavior-changing if retrieval queries change | Only scheduled conflict retrieval queries should be admitted | Possibly for conflict retrieval provider/depth | Yes | Keep out of AG-91B except ensure no duplicate pre-retrieval query owner | Later conflict-resolution authority phase | Lifecycle/query handoff parity; no accidental scheduling/provider changes |
| Embedding kickoff / embedding cadence | Orchestrator local branch and live callsite | `pipeline_orchestrator.py` 2164-2169 | Retrieval ranking/embedding similarity and downstream search dispatch | None | RunAuthority authorizes embedding action; Embedding executor performs call; QueryPlan may provide topic/query identity but not embedding cadence | Protected live embedding/action boundary | Behavior-changing if topic, provider/model/base URL, timing, or count changes | QueryPlan may own text identity if embedding topic is query-derived; not cadence | No | Yes | Delete direct local embedding call after authorized embedding action exists | AG-91E | Embedding call-shape parity; `_embed_topic` text parity; no embedding count/cadence changes |
| Retrieval state initialization | Orchestrator local variable block | `pipeline_orchestrator.py` 2105-2163 plus provider diagnostics initialized before router and state updated throughout | Retrieval loop, lifecycle controllers, traces | Several controller/default projection helpers, but no single RunState authority | RunAuthority/RunState | Protected lifecycle/action boundary | Projection-only if defaults copied; behavior-changing if consumed state initialization changes | QueryPlan owns query state only | ProviderAuthority owns provider diagnostics seed if provider-specific | Yes | Delete/demote ad-hoc local runtime state as RunState becomes consumed | AG-91E or later RunAuthority phase | Default-state parity; trace defaults parity; no side-effect reordering |
| Provider diagnostics initialization | Orchestrator local list and diagnostic builders | list initialized before pre-retrieval; recon diagnostics 1904-1918/1957-1970; provider attempts later | Trace/output/provider visibility | `core.provider_diagnostics` builders; no ProviderAuthority | ProviderAuthority/RunAuthority diagnostic ledger, projection-only consumers | Protected provider observability | Projection-only if already-computed attempts are serialized; behavior-changing if diagnostics affect routing | No | Yes | Yes for ledger lifecycle | Demote local list accumulation to provider diagnostic ledger only after parity fixtures | AG-91C/AG-91E | Diagnostic count/order/fields parity; failure-type parity |

## 4. Duplicate authority map

### 4.1 QueryPlan vs local query mutation

`QueryPlan` already authorizes finalization, deduplication, official bias,
recency merge ordering, per-iteration ordering, recovery, continuation,
supplemental, and remediation roles. The orchestrator still owns several
pre-admission mutations: `queries = rqq` after recon rewrite, canonical-subject
entity merging, recency gate/text construction, and direct `current_queries = ...`
scheduling. AG-91B should reduce this duplication by ensuring every query text
that can be retrieved is admitted through a consumed `QueryPlan` boundary before
retrieval scheduling.

### 4.2 Router/recon rewrite vs QueryPlan admission

Router and recon produce facts that affect query identity: entities, primary
entity, query type, recon rewritten queries, canonical subject, and confidence.
The router contract is passive and deterministic, while recon replacement is
still a local orchestrator assignment before `QueryPlan` exists. This creates an
old authority path where a live model/search branch can mutate query identity
outside the plan, then the plan only finalizes the already-mutated list. Future
work should make router/recon outputs observations and make `QueryPlan` the
admission point for query-affecting changes.

### 4.3 Search-depth local logic vs provider/depth policy

The initial strategy matrix sets base `search_depth`; local functions choose main
and supplemental effective depth; retrieval and legacy review consume those
strings. `QueryPlan` explicitly marks depth policy unchanged, which is a useful
trace posture but not consumed depth authority. AG-91C should introduce or map a
ProviderPlan/ProviderAuthority that owns provider/depth inputs without changing
the existing policy matrix.

### 4.4 Provider availability local logic vs provider routing

Provider availability is currently an orchestrator-local environment snapshot,
while provider routing lives in `core.routing.select_providers(...)`. This split
is acceptable as implementation detail but duplicate as authority: availability,
override filtering, suppression, Linkup gating, and ordered provider selection
are all provider-policy inputs. The target is one consumed provider decision per
retrieval action, with `core.routing` either retained as the policy function
behind ProviderAuthority or demoted behind a compatibility adapter.

### 4.5 Embedding kickoff local branch vs retrieval action boundary

Embedding is a live pre-retrieval action triggered directly by the orchestrator
after query/entity setup. It is not currently authorized by RunAuthority, and it
is not tied to a consumed QueryPlan/ProviderPlan action. AG-91E should treat this
as an action-authorization seam: same `_embed_topic`, same provider/model/base
URL, same cadence, but performed only as an authorized embedding action.

### 4.6 Title/recon/router/model calls vs runtime action ownership

The router, router retry, title generator, recon rewriter, researcher, Expander,
Evaluator, Economist, and Author are all live model callsites. AG-91A's
pre-retrieval focus includes only router/router retry/title/recon rewriter and
researcher as nearby live call boundaries. These actions should not be hidden
inside new helpers unless the helper is an executor for an explicitly authorized
action and call-shape parity is proven.

### 4.7 Router contract vs mutable local router fields

`RouterQueryPreparationState` records normalized router facts, retry provenance,
runtime posture, budget seed facts, recency posture, official-bias posture, and
query order facts. The orchestrator still copies `intent`, `report_type`,
`query_type`, `primary_entity`, and `entities_list` into mutable locals, applies
nutrition/focus/news/recon overrides, and then writes runtime posture back into
the contract. Future phases should make the contract or successor authority the
consumed source of these facts instead of a trace-visible mirror.

## 5. Target ownership proposal

Target authority model for the pre-retrieval surface:

1. **QueryPlan owns query identity, mutations, ordering, and admission.**
   Candidate producers may remain router/recon/researcher/Scout/Expander/
   Evaluator/weak-corpus/Scrutineer surfaces, but retrieved query text must be
   admitted by QueryPlan and consumed from QueryPlan-authorized output.
2. **Future ProviderPlan / ProviderAuthority owns provider/depth plan inputs.**
   It should represent provider availability booleans, provider-role inputs,
   search-depth selection, overrides, suppression, and ordered provider lists.
   Initial implementation should preserve `core.routing` behavior exactly.
3. **RunAuthority owns lifecycle/action authorization.** Router, router retry,
   recon search, recon rewrite, researcher query planning, embedding kickoff,
   retrieval execution, supplemental retrieval, and remediation retrieval should
   be authorized actions rather than local branches.
4. **Executors perform authorized actions.** Executors may call existing
   provider/model/search/embedding functions only with the same prompt text,
   query text, provider/model/effort/base URL/API-key/JSON/streaming/reasoning
   shape, and only when the action authorization permits it.
5. **The orchestrator remains a compatibility shell and callsite coordinator.**
   It may bridge old callsites while migration proceeds, but it must not retain
   duplicate ownership of query mutation, provider/depth policy, or lifecycle
   action decisions.
6. **Projection helpers remain deterministic and subordinate.** Trace fragments
   should serialize consumed authority decisions, not become alternate policy
   engines.

## 6. Implementation sequence recommendation

### AG-91B — QueryPlan pre-retrieval boundary tightening

Recommended first because it directly addresses the highest duplicate owner:
recon/router/researcher/local query mutation vs consumed QueryPlan admission.
AG-91B should be behavior-preserving and should not alter query text/order. It
should delete or demote the orchestrator-local `_finalize_retrieval_queries(...)`
facade and make pre-retrieval query candidates flow through explicit QueryPlan
admission records. It should prove that retrieval consumes the same ordered
queries as before.

### AG-91C — Provider/search-depth plan authority map or ProviderPlan seed

After QueryPlan boundaries are tightened, introduce a passive or
behavior-preserving ProviderPlan/ProviderAuthority seed for availability,
provider-role inputs, ordered providers, search-depth, override posture, and
supplemental-depth posture. Do not change `core.routing` semantics.

### AG-91D — Recon/router rewrite admission collapse

Collapse the recon/router rewrite old authority path by turning recon rewrite and
router retry outputs into observations consumed by QueryPlan and/or Router
contract successor state. Live calls must keep exact call shape and gating.

### AG-91E — Embedding/retrieval action authorization boundary

Move embedding kickoff and retrieval dispatch scheduling behind RunAuthority
style authorized actions while preserving embedding topic text, provider/model
call shape, retrieval dispatch arguments, provider diagnostics, and cadence.

## 7. Stop conditions for future implementation

Future implementation must stop if any of the following occurs:

- exact query text/order parity cannot be tested;
- provider/depth behavior would change accidentally;
- live callsite shape would change without explicit phase license;
- a helper would become a new pre-retrieval mini-orchestrator;
- the old authority path is not deleted, demoted, bypassed, or subordinated;
- QueryPlan/ProviderPlan authority is only trace-visible and not consumed;
- tests require live provider/model/search/embedding calls for a docs/static or
  behavior-preserving phase;
- provider availability work requires inspecting secret values, `.env`, raw
  provider payloads, private logs, caches, DB rows, or full raw traces;
- a phase changes prompt text, query text/order, provider order, depth strings,
  embedding cadence, retrieval ranking/filtering, citation formatting, Author
  behavior, persistence ordering, cache behavior, or ProjectSource retrieval
  without explicit scope.

## 8. AG-91B compact implementation seed prompt

> You are working in ScryRaven on branch
> `ag-91b-queryplan-pre-retrieval-boundary-tightening` from `main`.
>
> Implement the first behavior-preserving slice recommended by
> `docs/architecture/AG91A_PRE_RETRIEVAL_QUERY_DEPTH_PROVIDER_AUTHORITY_MAP.md`:
> tighten the pre-retrieval QueryPlan boundary without changing runtime behavior,
> query text/order, provider/depth policy, prompts, live call shapes, retrieval,
> embedding cadence, ranking/filtering, citation, Author behavior, persistence,
> cache, or ProjectSource behavior.
>
> Scope:
>
> - focus only on pre-retrieval query candidate admission around router/recon/
>   researcher/finalization/recency;
> - make retrieved query text consumed from QueryPlan-authorized output;
> - demote or delete the local `_finalize_retrieval_queries(...)` facade if exact
>   parity can be proven;
> - do not create a new helper that owns router/recon/provider/depth behavior;
> - do not change `QueryPlan` semantics unless tests prove exact old/new parity;
> - do not move or alter live `ask_model(...)`, `brave_reconnaissance(...)`,
>   `embed_texts(...)`, `select_providers(...)`, or search-depth call shapes.
>
> Required tests/checks:
>
> - exact initial/recon/researcher query text and order parity;
> - recency merge text/order parity;
> - official-bias insertion parity and custody metadata still not satisfying
>   official/current custody;
> - retrieval loop consumes the same `current_queries` and
>   `queries_by_iteration`;
> - no live provider/model/search/embedding calls;
> - `python -m py_compile core/pipeline_orchestrator.py`;
> - `git diff --check`.
>
> Stop if exact query parity cannot be asserted, if ProviderPlan/RunAuthority work
> becomes necessary, if prompt/live-call shape changes, or if QueryPlan authority
> would be trace-visible but not consumed.

## 9. Explicit do-not-touch surfaces for AG-91B unless separately licensed

- Router prompt text, retry prompt text, recon rewriter prompt text, researcher
  prompt text, Expander/Evaluator prompts, Economist prompt, Author prompts.
- `ask_model(...)`, `brave_reconnaissance(...)`, `embed_texts(...)`, provider
  search, Linkup, Scout, supplemental, Scrutineer remediation, Economist, and
  Author live-call shapes.
- Provider availability, `select_providers(...)`, provider order, provider role,
  Linkup gating, Tavily suppression, provider diagnostics semantics.
- Search-depth and supplemental-depth logic.
- Embedding topic text, provider/model/base URL, and embedding cadence.
- Retrieval execution, ranking/filtering, passage merge order, source-class
  recovery execution, conflict-resolution execution, final evidence bundle,
  citations, Author behavior, persistence, cache, ProjectSource retrieval.

## 10. Static audit commands used

- `wc -l core/pipeline_orchestrator.py`
- Python AST walk over `core/pipeline_orchestrator.py` for `ask_model`,
  `embed_texts`, `select_providers`, `brave_reconnaissance`,
  `build_query_plan_runtime_adapter`, `merge_recency`, and depth selector calls.
- `rg -n "def choose_retrieval_search_depth|choose_retrieval_search_depth|supplemental.*depth|search_depth" core -g '*.py'`
- `rg -n "finalize_supplemental|finalize_remediation|choose_supplemental_search_depth" core -g '*.py'`
- Line-range inspection with `nl -ba` for the pre-retrieval block,
  `core/query_plan.py`, `core/query_plan_runtime_adapter.py`, `core/routing.py`,
  `core/router_query_preparation_contract.py`, and
  `core/legacy_review_runtime_stage.py`.

No live ScryRaven/proplex/provider/model/search calls were run for this audit.
