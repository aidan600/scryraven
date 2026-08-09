# SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01

Status: completed Build
Mode: BUILD
Proof class: offline_product_path_proof
Starting-runtime: 607c381f71f0a6606afd7d856e034bf00d402b42
Runtime/test commit: 2d346a73251f28a1187fb2958028db51117bf0c0
Does-not-authorize: live calls, post-result query dispatch, permanent mode
budgets, provider-policy changes, READ, navigation, recovery redesign, evidence
or citation changes, Author changes, or source-obligation semantic changes

## Outcome

The ordinary initial `run_pipeline()` path now consumes one converged,
provider-neutral planning chain:

```text
human utterance plus bounded safe/supplied context
-> selected fast-model SearchPlanner
-> structured semantic and provider-neutral query-strategy proposal
-> deterministic schema, safety, bounds, and lineage validation
-> passive QuestionMeaningRecord proposal
-> RunKernel initial AnswerContract acceptance
-> accepted component and source-obligation refs
-> optional bounded non-evidence Scout report
-> optional SearchPlannerRevision proposal
-> existing amendment admission/application when contractual
-> active contract-bound SearchWorkPlan requirements
-> QueryPlan exact-query admission
-> ordinary first DISCOVER
-> unchanged core.routing provider selection
```

SearchPlanner proposals remain passive. RunKernel initial AnswerContract
acceptance remains the sole initial semantic authority. QueryPlan remains the
sole exact executable-query authority. Malformed required planner/revision
output and unresolved required truthful-targeting ambiguity fail before query
production and create no search dispatch.

Ordinary initial semantic planning uses the selected fast-model SearchPlanner.
The model owns question interpretation, warranted one-to-five component
decomposition, ambiguity assessment, source-need proposal, and provider-neutral
query-strategy proposal. Five components is a ceiling, not a target.
Deterministic machinery validates, binds, admits, and executes the proposal but
does not manufacture semantic planning.

No live provider, model, search, recon, fetch/read, or retrieval call was made.

## Owner Map And Dispositions

| Concern | Current owner | Disposition |
| --- | --- | --- |
| model-owned passive QuestionMeaningRecord and query-strategy proposal | ordinary `core.search_planner_model_adapter.SearchPlannerModelAdapter`, then `core.search_planner_runtime.execute_search_planner_action` plus deterministic validation | `UPGRADE` |
| initial AnswerContract acceptance | `RunKernel.authorize_initial_answer_contract_acceptance` and `RunKernel.reduce(INITIAL_ANSWER_CONTRACT_ACCEPTED)` | `REUSE` |
| current AnswerContract state | `RunKernel.state.current_answer_contract` with `initial_answer_contract` as the accepted initial root | `REUSE` |
| accepted component/source-obligation refs | accepted AnswerContract projections consumed by `initial_query_strategies_from_planner_state` | `REUSE` |
| Scout report | `core.scout_disambiguation_runtime.execute_scout_disambiguation_action`, only through an explicitly injected response-only adapter | `ADAPT` |
| SearchPlannerRevision | `core.search_planner_revision_runtime.execute_search_planner_revision_action` and explicit effect classification | `ADAPT` |
| contract-amendment admission/application | existing RunKernel authorization/reduction invoked by `_admit_and_apply_revision_amendment` | `REUSE` |
| SearchWorkPlan | `construct_contract_bound_search_work_plan` under RunKernel SearchWorkPlan construction authorization/reduction | `UPGRADE` |
| QueryPlan | `QueryPlanRuntimeAdapter` / `QueryPlan.admit_initial_component_strategies` | `UPGRADE` |
| SearchWorkPlan-to-QueryPlan binding | `initial_strategy_search_work_bindings` | `ADAPT` |
| ordinary query production | `core.query_production_runtime.execute_initial_query_strategy_convergence` and the retained authorized `execute_query_production_action` projection shell | `ADAPT` |
| exact ordinary callsite | `core.pipeline_orchestrator.run_pipeline`, beginning at `execute_initial_query_strategy_convergence` and continuing through QueryPlan admission | `ADAPT` |
| first search handoff | `query_authority.admit_execution_queries` immediately before the existing main retrieval authorization/scheduler path | `REUSE` |
| passive/shadow SearchWork paths | legacy passive construction helpers and tests remain nonordinary; `run_search_work_shadow_lane` is removed from the ordinary callsite | `SUBORDINATE` |
| downstream provider selection | `core.routing` through existing ProviderPlan/scheduler/dispatch consumers | `REUSE UNCHANGED` |

`core.query_production_runtime` and the exact ordinary `run_pipeline()` callsite
are both `ADAPT`. The ordinary initial pass now has one candidate-generation
chain. The legacy Brave/recon-rewriter/researcher chain is product-unreachable.
The prior runtime functions `brave_reconnaissance`,
`_build_recon_rewriter_prompt`, and `_build_researcher_prompt`, their model calls,
and the empty/invalid researcher `core_topic[:300]` fallback were removed from
this owner. Direct ordinary `execute_query_production_action` composition was
replaced by `execute_initial_query_strategy_convergence`. Compatibility
QueryPlan methods for legacy recon/researcher candidate admission remain
repository-visible but cannot be reached from this ordinary initial callsite.

## Installed Now

- With no explicit planner adapter, ordinary `run_pipeline()` constructs the
  existing `SearchPlannerModelAdapter` with `deps.ask_model`,
  `deps.clean_json_response`, the selected fast provider/model, and the selected
  reasoning posture. Exactly one logical bounded initial planner invocation is
  made.
- A transient non-retained wrapper supplies the current `local_url` as
  `base_url`, the current `or_api_key`, the current run `CostAccumulator`, and
  `cost_phase="search_planner"` to the existing model helper. These facts are
  absent from adapter fields, prompts, planner/contract state, SearchWorkPlan,
  QueryPlan, traces, retained metadata, and errors.
- OpenAI retains the selected provider/model; OpenRouter receives the configured
  key; Local receives the configured base URL. Missing OpenRouter credentials
  and missing or invalid Local endpoints fail before QueryPlan or search.
- The planner contributes one logical `search_planner` model-call accounting
  entry without double-counting. The existing underlying helper retry and
  endpoint-fallback policy is unchanged, so this does not claim exactly one
  provider request.
- The model owns the intended question, the distinction between request and
  context, one-to-five warranted components, material ambiguities, source needs,
  supported component dependencies, and provider-neutral query candidates.
- Deterministic validation enforces schema, identifiers, the five-component
  ceiling, accepted references, dependency/source lineage, safe authority
  closure, and query bounds/nonredundancy. It does not replace the model's
  semantic topology with deterministic query-shape output.
- `DeterministicSearchPlannerAdapter` is an explicitly injected
  validation-only/offline fixture. It is neither the ordinary default nor a
  fallback after model/configuration/JSON/schema/strategy failure.
- `RunDeps` declares typed optional `search_planner_adapter`,
  `scout_disambiguation_adapter`, and `search_planner_revision_adapter` seams.
  `SEARCHOS-REQUIRED-SCOUT-ORDINARY-COMPOSITION-01` composes the ordinary
  provider-neutral Scout and FAST PlannerRevision defaults when no adapter is
  injected; injected seams remain bounded offline/test overrides.
- Invalid or unavailable model planning fails closed before accepted planner
  state, initial AnswerContract acceptance, SearchWorkPlan activation,
  QueryPlan admission, or first search dispatch.
- Deterministic SearchPlanner proposal validation binds every candidate strategy
  to an accepted required component and accepted source-obligation refs.
- One active SearchWorkPlan is built after accepted contract and revision
  authority converge, then consumed by initial QueryPlan allocation.
- Every accepted required component receives an intentional distinct primary
  QueryPlan item; no small global total silently truncates component coverage.
- A second initial candidate requires a recorded distinct accepted need. It is
  dispatched immediately only with separate immediate-wave proof; otherwise it
  is retained with its justification for later SearchJudgment.
- Exact and materially equivalent candidates are rejected deterministically;
  bounded contributor lineage is retained on the surviving QueryPlan item.
- Model-planner provider/model selection claims are rejected. Explicit
  response-only compatibility proposals cannot affect unchanged routing.
- Optional recon has an explicit unavailable posture. Required identity or
  jurisdiction ambiguity needed for truthful targeting fails closed.
- SearchPlannerRevision classifies query-direction-only, contractual-pending,
  and no-effect outcomes. SearchPlannerRevision query-direction-only changes
  cannot mutate the AnswerContract. A contractual revision reaches planning
  only after existing amendment admission and application.
- The ordinary first DISCOVER wave consumes exact QueryPlan text/order/role and
  retains compact SearchWorkPlan requirement bindings.

## Initial Query Allocation Policy

Initial-query allocation policy version:
`searchos_initial_query_allocation_policy_v1`

| Field | Provisional default |
| --- | ---: |
| `primary_query_target_per_required_component` | 1 |
| `initial_candidate_ceiling_per_required_component` | 2 |
| `immediate_dispatch_target_per_required_component` | 1 |
| `recon_candidate_ceiling_per_affected_component` | 5 |
| `redundancy_rejection_enabled` | true |
| `required_component_floor_enabled` | true |

The single tuning owner is
`core.initial_query_allocation_policy.InitialQueryAllocationPolicy` and its
`DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY`. Explicit code composition may use
`with_tuning`; no environment or uncontrolled user override is installed.
Changing a default does not change SearchPlanner schema, AnswerContract meaning,
QueryPlan authority, provider adapters, evidence, or citation semantics.

The legacy global low/medium/high `2 / 2 / 3` values were not preserved as
SearchOS product-allocation policy. They remain only in unchanged downstream
retrieval-loop posture and do not truncate the initial required-component floor.
No global `N + 5` research cap or global five-query recon cap was installed.
The provisional recon value is per affected component, and each admitted recon
candidate must address a distinct unresolved dimension.

Focused proof reports:

```text
Required component count: 5
Primary queries admitted: 5
Secondary candidates prepared: 0 in the five-primary case; 1 in the prepared-secondary case
Secondary candidates immediately dispatched: 0 by default; 1 only in the explicit distinct official/current case
Distinct justification for each secondary: accepted official-current source obligation
Duplicate candidates rejected: exact and materially equivalent cases
Recon-affected components/dimensions: 1 component / 1 identity dimension in the injected-recon case
Recon candidates admitted: 1 in the injected-recon case
Proof no required component was globally truncated: five accepted required components produced five ordered first-wave QueryPlan primaries
Proof no post-result follow-up was implemented: prepared secondary remains outside current_queries and names SearchJudgment as later authorizer
Ordinary default planner invocations: exactly 1 logical selected-fast-model SearchPlanner invocation
Planner transport matrix: selected OpenAI provider/model; exact OpenRouter key; exact Local base URL
Planner cost accounting: 1 search_planner phase model-call entry; 0 double-counted entries
Planner connection retention: 0 credential, endpoint, or accumulator objects in governed retained surfaces
Messy narrated one-intent request: 1 model-proposed and accepted component; 1 model-proposed first query dispatched
Bounded supplied-context fixture: reference and summary reached the planner; 0 evidence/custody/source-satisfaction/citation authority
Model multipart ceiling fixture: 5 model-proposed components; 5 accepted dependency-preserving refs; 5 ordered QueryPlan primaries
Invalid/unavailable model fixtures: 0 QueryPlan admissions; 0 search dispatches; 0 deterministic or legacy fallbacks
Injected typed path: response-only planner -> Scout direction -> revision -> QueryPlan -> first offline search
```

## SearchWorkPlan And QueryPlan Split

SearchWorkPlan owns current accepted contract refs; component and
source-obligation requirement refs; provider-neutral job kinds; compact planner,
revision, policy, and requirement digests; and existing stop/budget posture. It
is active (`passive=false`, `runtime_consumed=true`) and influences QueryPlan
allocation without storing complete query text.

QueryPlan owns admitted executable query text, exact identity, role, order,
iteration, finalization, and dispatch lineage. Each initial item retains compact
accepted-component, source-obligation, provider-neutral job, SearchWorkPlan, and
requirement refs. Prepared secondaries remain canonical QueryPlan candidates but
do not cross the immediate execution boundary in this phase.

## Recon And Revision Posture

Recon is need-based for entity identity, alias/rename, jurisdiction,
currentness, official domain, or canonical publication venue. It does not run
for every component. `SEARCHOS-REQUIRED-SCOUT-ORDINARY-COMPOSITION-01`
composes `OrdinaryScoutDisambiguationAdapter` whenever the ordinary pipeline has
no injected Scout adapter. It consumes only policy-bounded sanitized queries;
each query binds a distinct unresolved dimension and the policy ceiling is
checked per affected component before adapter execution.

The ordinary provider-neutral Scout adapter maps each authorized candidate to
`core.routing` `DISCOVER(lightweight_disambiguation)`, accepts only the selected
lawful route, and calls the existing cap-aware `search_scout_results` once per
candidate. Its report records real dispatch as `execution_status=executed` and
`not_live=false`; injected response-only fixtures retain
`executed_by_fake_adapter` and `not_live=true`. A blocked lawful route is
distinct from an executed empty result: optional recon retains the admitted
primary, while required truthful-targeting recon fails closed.

Scout reports remain non-evidence: they do not enter EvidenceLedger, support,
custody, citations, FinalAnswerPacket, Analyst evidence, Author material, or
source-obligation satisfaction. They do not activate READ, Focused Extract, Map,
Crawl, Deep, or fallback. The legacy Brave recon path is not an ordinary
fallback.

The ordinary FAST `SearchPlannerRevisionModelAdapter` receives only canonical
lineage-bound Scout directional context: report/component/dimension/hint refs
and bounded title/domain/hint-kind/currentness/interpretation/confidence
fields. Snippets, links, raw provider payloads, evidence authority, citation
authority, and source-obligation satisfaction do not cross that boundary.
Query-direction-only revision is explicitly non-contractual. Contractual
revision remains passive until the existing amendment-admission owner accepts
it and the existing application owner creates the current derived contract.
Unsupported, stale, or multiple contractual candidates do not affect planning
or dispatch.

Semantic interpretation of Scout hints and revision of the plan remains
model-driven. Deterministic code may validate and admit the revision but may
not semantically rewrite the plan.

The planner input boundary preserves the complete normalized user utterance up
to 12,000 characters plus bounded safe context, route/run references, and
future supplied-context/document references or summaries. Those context facts
remain planning-only and are not independently parsed into components or
promoted to evidence. This phase does not implement document ingestion.

## Preserved Unchanged

- `core.routing` remains the sole provider selector; capability and provider
  selection remain separate.
- Provider availability, adapters, one-shot dispatch accounting, claim/use,
  replay prevention, and no-silent-switch behavior are unchanged.
- Requested/provider-reported/redirect/final/canonical URL facts and basic URL
  hygiene are unchanged.
- Selected-candidate READ nontrigger and ordinary pre-selection local-page-fetch
  retirement remain intact.
- Source-obligation schema, kinds, meaning, strengthening/weakening rules,
  satisfaction, coverage, and citation policy are unchanged.
- Recovery, continuation, supplemental, remediation, weak-corpus, and later
  search query producers are unchanged.
- EvidenceLedger, Sufficiency, FinalAnswerPacket, citations, Analyst evidence,
  Author, and final-answer authority are unchanged.
- TD-0001 and TD-0002 remain unchanged.

## Still Planned

- Post-result SearchJudgment must inspect the first result set per component and
  authorize an additional query only when the accepted component or
  source-obligation need remains unmet and the proposed query is materially
  nonredundant.
- Permanent Fast/Balanced/Deep follow-up willingness, provider and query
  calibration, post-result iteration, gap recovery, and stop policy.
- Ordinary READ/source custody, Focused Extract activation if separately
  justified, bounded navigation, and final SearchOS integration/live shakeout.

## Closed Surfaces

Provider routing/availability and provider adapters;
source-obligation schema/kinds/meaning/satisfaction/coverage/citation policy;
READ/navigation/fallback; recovery/continuation/supplemental/remediation;
EvidenceLedger/citations/Analyst/Author/final authority; permanent mode budgets;
live validation and phase-time external calls; secrets, raw prompts/provider
payloads, private traces, caches, and artifacts all remained closed.

## Nonproofs

This offline product-path proof proves model ownership and context plumbing,
not semantic quality on arbitrary real-world requests. That quality remains a
later licensed calibration obligation. It also does not prove live provider
availability, comparative provider quality, result sufficiency, answer-quality
improvement, post-result judgment, READ or custody, navigation,
recovery/stopping, source-obligation satisfaction, evidence/citation
correctness, Author behavior, broad product correctness, latency,
provider-reported token/cost accuracy, or production stability.

## READ-Phase Carry-Forward Requirements

`SEARCHOS-READ-SOURCE-AND-CUSTODY-01` must later:

1. Census ordinary and compatibility webpage-opening callsites.
2. Retire, isolate, or keep product-unreachable any direct local arbitrary
   webpage opener that would bypass provider-mediated READ.
3. Preserve pure parsers that consume already-authorized supplied content.
4. Use response-only Linkup/Tavily offline fixtures incapable of live contact.
5. Keep `core.routing` as provider selector: derive `READ_PAGE` first, then
   select Linkup Fetch or Tavily Extract.
6. Preserve one selected provider call per recorded attempt, one claim/use
   posture, replay protection, and no silent provider switch after invocation.
7. Preserve the requested URL separately from optional provider-reported,
   observed redirect, final, canonical, status, or parent facts.
8. Treat missing provider-reported/final/canonical URL facts as unknown rather
   than failure.
9. Enforce bounded basic URL hygiene for malformed URLs, embedded credentials,
   localhost, obvious literal loopback addresses, and obvious literal
   private-network addresses before paid-provider submission.
10. Avoid DNS snapshots, connected-IP proof, redirect-chain attestation, or
    provider-network-path ownership.

These are approved next-checkpoint constraints, not active technical-debt
entries. Useful PR #507 controls are preserved where already installed, carried
forward to READ where applicable, and not added as technical debt.

## Next Checkpoint

The active next checkpoint is
`SEARCHOS-READ-SOURCE-AND-CUSTODY-01`. It begins from exact QueryPlan-authorized
DISCOVER queries, unchanged `core.routing`, the selected-candidate READ
nontrigger, and the carry-forward controls above. It must not implement
post-result secondary-query judgment as a side effect of READ convergence.

Technical-debt register disposition: No change.
