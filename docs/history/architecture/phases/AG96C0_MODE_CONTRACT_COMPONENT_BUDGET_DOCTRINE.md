Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96C0_MODE_CONTRACT_COMPONENT_BUDGET_DOCTRINE).

# AG-96C0 Mode Contract, Component, and Budget Doctrine

## 1. Status and scope

Status: architecture/design doctrine only.

AG-96C0 creates a repo-tracked doctrine for ScryRaven's Fast, Balanced, and Deep
product modes before additional Fast validation, Balanced/Deep loop work, or
provider/search runtime changes. It uses repo-visible files and the current phase
brief only.

This phase makes no runtime behavior changes, runs no live validation, makes no
provider/model/search calls, adds no providers, changes no query generation, and
does not alter `core/mode_policy.py`, `core/pipeline_orchestrator.py`,
final-answer/citation behavior, Author prompt/prose, provider routing, search
depth, source-specific resolvers, package names, CLI names, or environment
compatibility names.

Closed surfaces for this phase include all runtime behavior, provider routing,
query/depth policy, live ScryRaven/proplex calls, secrets, `.env`, raw provider
payloads, raw prompts, DB rows, private logs, caches, full raw traces, local
output packets, broad historical rewrites, and AG-96B2 dogfood implementation.

Post-#342 checkpoint note:
`AG-DOC-SEMANTIC-COVERAGE-CHECKPOINT-01` preserves AG-96C0 as historical mode
budget doctrine, but the current semantic-coverage rule is sharper: modes change
budget and review depth, not semantic authority. Fast has no Scrutineer in MVP.
Balanced uses Scrutineer only on red flags. Deep requires Scrutineer and
post-Scrutineer response budget. Deep allows max 3 follow-up loops by default
and max 4 only with explicit RunKernel extra recovery authorization. Follow-up
limits are ceilings, not targets, and logical depth plus authorized query fanout
matters more than raw query count. `SearchWorkPlan` remains legacy/passive/closed
unless explicitly reopened; the current next implementation is
`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`.

## 2. Why AG-96C0 exists

AG-96B0 and AG-96B1 clarified the official-source acquisition lane:

- provider work should be selected by job, not by a permanent provider
  hierarchy;
- provider snippets, scout output, and provider answer/deep material may
  discover hints, but they do not satisfy final evidence or citation
  obligations until canonical custody admits an answer-bearing source;
- AG-96B1 implemented a narrow Fast official lane repair inside the existing
  source-class recovery action, including one bounded retry from a concrete
  bridge hint after answer-bearing candidate-fit rejection.

That work is useful, but it is too narrow to become the durable architecture for
all modes. The stale mental model:

```text
Fast = deterministic
Balanced = more searches
Deep = even more searches
```

is wrong for ScryRaven's next architecture steps. Fast is not outside reasoning
authority. All modes are governed by RunKernel / RunAuthority. What changes by
mode is the answer contract, reasoning depth, follow-up authority, budget shape,
and output-depth target.

Current fixed mode caps are also too crude for multipart or component questions.
A two-component comparison can fail because a global query cap starves one side,
even when each component only needs shallow work. Conversely, a single difficult
component may require deeper reasoning than Fast should pursue.

Core doctrine:

```text
Modes control reasoning depth, follow-up authority, and budget shape.
Query components control breadth.
Source obligations control evidence requirements.
Providers are selected by job.
```

## 3. Current documentation audit

Repo inspection found a strong set of partial doctrines, but no single component-
aware mode/budget doctrine.

AG-96B0 already says provider jobs are not a hierarchy. It distinguishes scout /
disambiguation, direct official candidate search, semantic recall,
fetch/read/extract, and provider answer/deep/synthesis products as different
jobs with different final-evidence posture. It also says Fast is
recipe-bounded, while Balanced and Deep are judgment-bounded, and that
Balanced/Deep follow-up search should be evidence-gap-driven, not provider-
driven. AG-96C0 preserves the provider-job and bridge-only doctrine while
correcting the over-narrow implication that Fast is durable architecture because
it is deterministic.

AG-31 already separates mode-owned hard caps from controller-owned
marginal-value allocation. `docs/history/architecture/phases/CONTROLLER_BUDGET_SEMANTICS_AG31.md`
and `core/controller_budget_semantics.py` show that the controller budget gate
mirrors current mode caps, reasons about central gaps, redundancy, conflict,
source-class recovery, weak-corpus recovery, and targeted retrieval, but does
not execute retrieval, alter prompts, choose providers, tune depth, or change
runtime search behavior.

AG-46A already sketches typed retrieval lanes and component query provenance.
`docs/architecture/TYPED_RETRIEVAL_BATCH_DESIGN_AG46A.md` defines future
`RetrievalBatch` / `RetrievalBatchLane` shapes that keep query provenance,
query ownership, evidence obligation, provider policy, and depth policy
separate. That document is a close ancestor of this phase's component-aware
planning shape.

AG-91A maps the pre-retrieval query/depth/provider authority surface. It says
`QueryPlan` should own query identity and admission, future ProviderPlan /
ProviderAuthority should own provider/depth inputs, and RunAuthority should own
lifecycle/action authorization. AG-96C0 uses that same separation: components
and obligations describe work; provider jobs and depth policy remain owned by
their proper authorities in future runtime phases.

`core/mode_policy.py` still encodes simple global caps as a passive snapshot:
Fast has `max_queries=2`, `results_per_query=5`, `top_chunks=8`,
`max_iterations=1`, and `search_depth="basic"`; Balanced has `max_queries=2`,
`results_per_query=6`, `top_chunks=20`, `max_iterations=2`, and
`search_depth="basic"`; Deep has `max_queries=3`, `results_per_query=8`,
`top_chunks=40`, `max_iterations=3`, and `search_depth="advanced"`. AG-96C0 does
not change those values.

The reference query docs already imply that some comparisons belong in
Balanced/Deep because the answer needs assumptions, units, ranges, and
source-bound evidence. `docs/evals/reference_query_library.md` classifies
`compare cost per passenger mile MD-80 vs 777-300` as Balanced/Deep, with expected
evidence for costs, capacity, fuel burn, utilization, assumptions, units, and
source-bound ranges. It classifies `average electricity price Germany vs France
2026` as Balanced/Deep, with country, period, consumer class, and unit
definitions. `docs/eval_queries.md` marks those records as manual review aids,
not live-query instructions.

AG-81B already defines a user-facing Fast/Balanced/Deep output contract. Fast is
direct and concise but still preserves central caveats. Balanced gives a short
answer plus evidence basis. Deep adds audit depth, source maps, conflicts, gaps,
and quantitative assumptions where useful. AG-96C0 adds the planning and budget
doctrine beneath that output contract.

The missing doctrine is component-aware breadth plus mode-specific depth and
follow-up authority.

## 4. Durable mode contract

| Mode | Definition |
| --- | --- |
| Fast | Direct answer contract. RunKernel still governs the run, but the contract is shallow: answer the question with minimal necessary search, minimal iteration, shorter output posture, and no open-ended exploration. It can decompose obvious multipart questions enough to avoid starving components, but it should not pursue deeper inference layers. |
| Balanced | Explanatory answer contract. RunKernel may reason over first-pass evidence, identify source gaps, authorize targeted follow-up, and develop the next layer of the answer. This is where one-hop inference, normalization, comparison, and moderate exposition belong. |
| Deep | Research/reconciliation contract. RunKernel may perform multi-hop reasoning, compare source families, red-team assumptions, handle conflicts/currentness, build ranges/sensitivity where useful, and continue through a larger bounded loop. Output may be long, but length is not the goal; resolved depth is the goal. |

Additional mode posture:

- Fast is direct, constrained, and low-budget. It is still governed by
  RunKernel / RunAuthority. It may refuse, qualify, or indicate that a task
  belongs in Balanced/Deep when the task requires deeper inference,
  normalization, reconciliation, multi-hop derivation, or open-ended
  exploration.
- Balanced is not "exactly N searches." It may authorize follow-up only when a
  named evidence/source gap justifies the spend, and it should stop when
  sufficiency, budget, or mode depth says to stop.
- Deep is not "long output." It is a larger bounded research/reconciliation
  contract. A Deep answer can be short if the resolved answer is simple and
  well-supported.

## 5. Breadth vs depth

Definitions:

- Breadth: the number of components or subquestions requiring coverage.
- Depth: the number of reasoning/search layers permitted for each component.
- Source obligation: the evidence requirement attached to a component, such as
  official/current, primary, canonical, peer-reviewed, date-bound, source-bound
  numeric, or conflict-resolution evidence.
- Provider job: the kind of search, acquisition, fetch/read, scout,
  disambiguation, semantic recall, or reconciliation work selected to satisfy a
  component obligation.

Multipart questions should not starve simply because a mode has a global query
cap. Component count should influence budget allocation. Mode should control how
deeply each component may be pursued.

Breadth and depth are independent enough that both have to be represented:

- a shallow multipart question may need one small search per obvious component;
- a single official/current lookup may need little breadth but strict source
  obligation handling;
- a quantitative comparison may need moderate breadth across inputs and
  moderate or deep normalization;
- a conflict-heavy policy question may need limited breadth but Deep-style
  reconciliation.

## 6. SearchWorkPlan doctrine

Future runtime work should converge on a planning shape like this:

```yaml
SearchWorkPlan:
  mode_contract:
    mode: Fast | Balanced | Deep
    answer_contract: direct | explanatory | research_reconciliation
    reasoning_depth: shallow | moderate | deep
    follow_up_authority: none_or_minimal | gap_driven | larger_bounded_loop
    output_depth_target: short | compact_explanatory | resolved_depth
  query_components:
    - component_id: string
      user_facing_subquestion: string
      source_obligation: string
      corridor_or_source_class_need: string
      required_search_jobs:
        - scout_or_disambiguation
        - direct_candidate_search
        - semantic_recall
        - fetch_read_extract
        - reconciliation
      per_component_budget:
        minimum_viable_budget: qualitative_budget
        cap: qualitative_budget
      mode_depth_allowance: shallow | moderate | deep
      stop_escalate_refuse_condition: string
  global_budget_cap: qualitative_or_existing_mode_cap
  rebalancing_policy: string
  final_sufficiency_policy: string
```

This is doctrine/design, not runtime implementation. It does not add a
`SearchWorkPlan` class, change `QueryPlan`, change retrieval batch code, alter
mode caps, or authorize provider/search calls.

## 7. Component-aware budget doctrine

Future budget policy should have these layers:

- Base mode budget: the coarse mode-owned budget shape that keeps Fast,
  Balanced, and Deep distinct.
- Per-component minimum viable budget: enough work for each central component to
  avoid starvation.
- Per-component cap: a component cannot consume the whole run merely because it
  remains difficult.
- Global cap: the run still has an overall ceiling for cost, latency, provider
  calls, fetches, reads, and iteration.
- Rebalancing policy: unused budget from satisfied or irrelevant components may
  move to unresolved central components when the selected mode permits more
  depth.
- Final sufficiency policy: stop when component sufficiency is met, budget is
  exhausted, or the needed inference exceeds the selected mode.

This phase intentionally avoids hard numeric commitments except when auditing
the current `core/mode_policy.py` snapshot. Future implementation should replace
or subordinate crude global query caps with component-aware budget policy, but
AG-96C0 does not change runtime caps.

Practical budget principles:

- Fast may allocate a tiny viable amount across obvious components, but should
  refuse or qualify once the answer requires deeper inference or reconciliation.
- Balanced should spend on central source gaps with moderate expected value, not
  on generic "try more search" impulses.
- Deep may spend through a larger bounded loop when additional work improves
  source quality, reconciliation, sensitivity, currentness, or conflict
  handling.
- No mode should treat provider diversity as a reason by itself to spend more
  budget. The evidence gap names the job; the job selects the provider surface.

## 8. Mode behavior examples

### Simple official/current lookup

Example: "What is the current filing fee for Form A-100?"

- Fast: direct answer if admitted official/current evidence is found quickly;
  otherwise limited insufficiency, not a broad search tour.
- Balanced: may explain source class and date/effective-date relevance, and may
  authorize targeted follow-up if first-pass evidence finds only a generic
  official page.
- Deep: may compare official notices, current fee tables, archived/stale pages,
  and conflicting effective-date signals if those conflicts matter.

### Multipart factual comparison

Example: "Compare Brave vs Safari privacy defaults on iOS."

- Fast: cover the obvious components enough to avoid one-sided starvation, but
  keep the answer direct and shallow.
- Balanced: decompose by product and platform, distinguish defaults from
  optional settings, and perform one-hop comparison.
- Deep: map source families, platform/version caveats, official docs versus
  technical analysis, and unresolved source conflicts.

### 777 vs MD-80 cost per passenger mile

Example: "Compare cost per passenger mile MD-80 vs 777-300."

- Fast: should likely classify the task as beyond direct Fast if no direct
  answer-bearing sources exist. It may provide a bounded caveat or suggest
  Balanced/Deep rather than constructing a fragile estimate.
- Balanced: may search for aircraft inputs, such as costs, capacity, fuel burn,
  utilization, and unit definitions, then compute a normalized comparison under
  explicit assumptions.
- Deep: may compare source families, reconcile assumptions, present ranges and
  sensitivity, and red-team assumptions such as load factor, maintenance cost,
  fuel price, route profile, fleet age, and configuration.

### Average electricity price Germany vs France

Example: "average electricity price Germany vs France 2026."

- Fast: may answer only if a direct, current, same-definition source supports
  both countries; otherwise it should qualify the missing definition or mode
  mismatch.
- Balanced: should identify components for Germany, France, period, consumer
  class, and unit, and avoid mixing household, industrial, wholesale, and retail
  prices.
- Deep: may compare official statistical and market sources, reconcile period
  and consumer-class definitions, and present ranges or definition-specific
  answers where one average would be misleading.

### Broad conceptual explainer

Example: "What causes auroras at mid latitudes?"

- Fast: concise mechanism and one or two central facts from authoritative
  sources.
- Balanced: a clear causal chain, event examples if useful, and modest caveats.
- Deep: additional source-family comparison or current-event context only if the
  user asks for research depth or the evidence situation is unsettled.

## 9. Relationship to AG-96B1 Fast official lane

AG-96B1 is a narrow Fast repair path and validation harness inside the existing
source-class recovery action. It implemented a bounded official-lane helper and
one bridge-hint retry after answer-bearing candidate-fit rejection. It also
preserved the rule that bridge hints are not final evidence or citation
support.

AG-96B1 must not become the pattern for separate mode-specific official
executors. The long-term target is one shared acquisition/search-work core with
mode-specific budget/depth policy and component/source-obligation inputs.

Official/current is a source obligation and search constraint, not a separate
mode-specific pipeline.

## 10. Relationship to Balanced/Deep judgment loops

Balanced/Deep runtime loops should not be implemented until this doctrine is
reviewed.

Balanced/Deep should authorize follow-up search only when evidence gaps justify
it. Follow-up search should be gap-driven, not provider-driven. The loop remains:

```text
reason over current evidence
-> identify a specific component/source gap
-> authorize targeted follow-up search if mode and budget permit
-> fetch/read candidates
-> update evidence, search judgment, and sufficiency judgment
-> stop, refuse, or continue within budget
```

Balanced/Deep should use the same shared acquisition core as Fast, with larger
or different budget policy. They should not use provider answer/deep output as
final evidence unless canonical fetch/read/admission separately satisfies source
custody and citation obligations.

## 11. Relationship to current mode_policy.py

`core/mode_policy.py` is a passive/current-state snapshot of the UI mode caps
already assigned elsewhere. AG-96C0 does not change it.

Current caps remain:

| Mode | Search depth | Max queries | Results per query | Top chunks | Max iterations |
| --- | --- | ---: | ---: | ---: | ---: |
| Fast | basic | 2 | 5 | 8 | 1 |
| Balanced | basic | 2 | 6 | 20 | 2 |
| Deep | advanced | 3 | 8 | 40 | 3 |

Future runtime work should replace or subordinate crude global query caps with
a component-aware budget policy. That future work must be separately scoped,
tested, and reviewed. Do not change code in AG-96C0.

## 12. Deferred work

Deferred explicitly:

- runtime component decomposition;
- `SearchWorkPlan` implementation;
- `core/mode_policy.py` changes;
- Balanced/Deep runtime loops;
- AG-96B2 live dogfood;
- provider bake-off;
- new provider integration;
- final-answer/citation rewrite;
- Author prompt/prose changes;
- broad `core/pipeline_orchestrator.py` work;
- source-specific resolvers;
- provider routing/selection/depth changes;
- query generation changes;
- runtime official/current acquisition changes;
- package/CLI/env rename work.

If a future phase requires any deferred surface above, it should be named
directly with tests, stop conditions, live-call boundaries, and final-bundle
requirements.
