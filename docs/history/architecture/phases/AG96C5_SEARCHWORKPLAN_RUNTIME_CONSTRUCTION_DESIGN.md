Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96C5_SEARCHWORKPLAN_RUNTIME_CONSTRUCTION_DESIGN).

# AG-96C5 SearchWorkPlan Runtime Construction Design

## 1. Status and scope

Status: design/static only.

AG-96C5 designs how ScryRaven should eventually construct a
`SearchWorkPlan` at runtime from RunKernel / RunAuthority. It does not
construct or consume a plan in runtime code.

This phase makes no runtime behavior changes. It makes no prompt behavior
changes. It makes no provider, search, ranking, filtering, citation, final
answer, Author, Analyst, Economist, Scrutineer, QueryPlan runtime, or
`mode_policy.py` changes. It does not add a runtime constructor, does not wire
`SearchWorkPlan` into RunKernel, QueryPlan, retrieval, provider selection, or
`core/pipeline_orchestrator.py`, and does not run live validation.

Closed surfaces remain closed: runtime behavior, prompt behavior,
provider/search/ranking/filtering, query generation/runtime behavior,
QueryPlan runtime behavior, `mode_policy.py`, `SearchWorkPlan` runtime
construction or consumption, QueryShapeClassifier / ContractResolver runtime
behavior, QuantWorkUnit runtime activation, Analyst/Author/Economist/Scrutineer
behavior, FinalAnswerPacket/citation behavior, new providers, live validation,
and `core/pipeline_orchestrator.py`.

## 2. What exists now

The current AG-96C stack is intentionally staged.

AG-96C0 defines the mode/component/source-obligation/provider-job doctrine:
modes control reasoning depth, follow-up authority, and budget shape; query
components control breadth; source obligations control evidence requirements;
providers are selected by job. Fast, Balanced, and Deep are RunKernel /
RunAuthority-governed answer contracts, not separate provider hierarchies.

AG-96C1 reframes named specialist units as jobs and capabilities. Scout,
Researcher, Expander, Evaluator, Economist, Analyst, Scrutineer, and Author are
not durable peer authorities. Their durable capabilities map into
`SearchWorkPlan` fields, canonical judgments, FinalAnswerPacket, or bounded
executors.

AG-96C2 adds the passive `SearchWorkPlan` data model in
`core/search_work_plan.py`. It defines JSON-safe fields for requested mode,
effective contract, query shape, components, source obligations through
components, provider jobs, quant work units, synthesis jobs, audit jobs, budget,
follow-up authority, stop conditions, final sufficiency policy, authority refs,
and metadata. Serialization explicitly says it is passive and not runtime
consumed.

AG-96C3 designs query-shape assessment and contract resolution as future
RunKernel / RunAuthority-owned pre-search decisions. It also states that
QueryPlan owns executable query identity/order in current lanes and must not
become source-obligation, provider/depth, final sufficiency, or citation
authority.

AG-96C4 adds passive records in `core/query_shape_contract_resolution.py`:
`QueryShapeAssessment`, `ContractResolutionRecord`, candidate records, and
`SearchWorkPlanConstructionDesignRecord`. These records describe future inputs
and fill paths, but they do not classify queries, resolve contracts, construct
`SearchWorkPlan`, call providers/search, mutate RunKernel state, or change
QueryPlan behavior.

The active RunAuthority chain remains:

```text
RunAuthorityContract
-> EvidenceLedger
-> SearchJudgment
-> SufficiencyJudgment
-> FinalAnswerPacket
-> AuthorExecutor
```

`core/pipeline_orchestrator.py` still coordinates many callsites and contains
remaining authority debt, but it is not the future planner.

## 3. Future construction seam

The future `SearchWorkPlan` construction seam belongs under RunKernel /
RunAuthority. The owner should be the RunAuthority chain enforced by RunKernel,
not `pipeline_orchestrator.py`, QueryPlan, a specialist helper, trace, or a
prompt-only instruction.

The seam should consume structured records, not raw prompts, raw model
responses, or raw provider payloads. The preferred inputs are a
`RunAuthorityContract`, `QueryShapeAssessment`, `ContractResolutionRecord`,
safe route facts, safe user-supplied domain hints, current date/freshness
boundary, and a passive mode policy snapshot.

Construction should happen before search execution when enough pre-search
context exists. Some fields should be allowed to remain tentative: conflict
likelihood, answer-bearing official/current custody, source-bound numeric
availability, normalization needs, and ambiguity repairs may require first-pass
evidence. Later SearchJudgment and SufficiencyJudgment phases may repair,
confirm, or qualify those fields after evidence exists.

The future flow should be:

```text
user request + safe routing facts
-> RunAuthorityContract
-> QueryShapeAssessment
-> ContractResolutionRecord
-> SearchWorkPlan construction seam
-> SearchWorkPlan
-> later QueryPlan/provider-job execution phases
```

`pipeline_orchestrator.py` must remain a coordinator. At most, a later scoped
phase may let it call a bounded adapter or pass through an already constructed
RunKernel-authorized plan. It must not rebuild plan fields from local runtime
variables, choose provider/depth/query behavior, or become the planner.

## 4. Allowed future inputs

Allowed future constructor inputs:

| Input | Allowed use |
| --- | --- |
| Requested mode / UI mode | Fill `requested_mode` and help resolve the effective contract. |
| Safe routing facts | Use intent, report type, query type, core topic, primary entity, entities, and currentness/academic hints where already produced. |
| `RunAuthorityContract` source requirements | Preserve official/current, legal/current-primary, canonical, source-bound numeric, conflict, and general source requirements. |
| `QueryShapeAssessment` | Fill query shape, tentative components, source-obligation candidates, provider-job candidates, quant/audit/social candidates, and first-pass evidence-needed flags. |
| `ContractResolutionRecord` | Fill effective contract, mode mismatch posture, output posture, follow-up depth, and stop/escalate/refuse posture. |
| User-supplied include/exclude domain hints | Constrain candidate jobs only when explicitly supplied by the user and sanitized. |
| Current date/freshness boundary | Fill date-bound currentness and freshness posture without running live validation. |
| Passive mode policy snapshot | Inform budget posture from existing UI mode caps without creating a new policy engine. |
| Safe feature flags / schema version | Gate construction shape and compatibility without activating provider/search behavior. |

Explicitly disallowed inputs:

- raw prompts;
- raw provider payloads;
- raw model responses;
- secrets or `.env`;
- DB rows;
- private logs;
- caches;
- full raw traces;
- local output packets.

The constructor should use bounded request references and sanitized route facts.
It should not persist raw user prompts into trace fields beyond existing safe
refs, and it should not inspect private artifacts to infer plan fields.

## 5. Future SearchWorkPlan field fill map

| SearchWorkPlan field | Future source | Notes |
| --- | --- | --- |
| `requested_mode` | Requested mode / UI mode plus `ContractResolutionRecord.requested_mode` | Preserve the requested mode even if the effective contract downshifts or requires qualification. |
| `effective_contract` | `ContractResolutionRecord` under RunAuthority | Records direct constrained, explanatory, research reconciliation, mismatch posture, follow-up depth, and output posture. |
| `query_shape` | `QueryShapeAssessment` | May include tentative flags for first-pass-evidence-dependent shape signals. |
| `components` | `QueryShapeAssessment` component candidates plus safe route facts | Components define breadth and should prevent central entities/subquestions from starving under crude global caps. |
| `source_obligations` | `RunAuthorityContract` source requirements plus `QueryShapeAssessment` obligation candidates | Strong official/legal/canonical/source-bound obligations must not be weakened by classifier output. In the AG-96C2 model, obligations are attached through components. |
| `provider_jobs` | `QueryShapeAssessment` provider-job candidates and component/source-obligation map | Jobs are provider-neutral work kinds. Provider identity remains subordinate and optional. |
| `quant_work_units` | `QueryShapeAssessment` quant candidates and source-bound numeric obligations | Planning only. No calculations, code execution, or unsupported value invention. |
| `synthesis_jobs` | Effective contract plus components, source obligations, and synthesis capability mapping | Analyst-style work remains bounded synthesis over admitted or explicitly scoped material. |
| `audit_jobs` | Deep/reconciliation contract, conflict/currentness flags, quant assumptions, and audit candidates | Scrutineer-style work becomes bounded audit vocabulary, not an open-ended loop. |
| `budget` | Passive mode policy snapshot, effective contract, component count, source obligations, and budget posture candidates | Future values should represent base mode budget, component minimums/caps, global cap, rebalancing, and exhaustion posture. |
| `follow_up_authority` | `ContractResolutionRecord` plus RunAuthority/SearchJudgment/SufficiencyJudgment ownership rules | Bounded executors cannot authorize follow-up. |
| `stop_conditions` | `ContractResolutionRecord`, `QueryShapeAssessment` stop candidates, RunAuthorityContract obligations, and date/freshness boundary | Include unsatisfied obligations, budget exhaustion, mode mismatch, inference overrun, missing source-bound numerics, unresolved conflict/currentness, and live validation not authorized. |
| `final_sufficiency_policy` | SufficiencyJudgment/FinalAnswerPacket policy plus RunAuthorityContract obligations | Describes final readiness posture and prohibited upgrades; does not select citations. |
| `authority_refs` | RunKernel action ID, RunAuthorityContract ID, assessment/resolution IDs, schema refs | References should be inert IDs/projections, not raw traces or payloads. |
| `metadata` | Sanitized schema/version/feature-flag/debug posture | Must remain JSON-safe and omit sensitive/raw/private data. |

## 6. QueryPlan relationship

`SearchWorkPlan` describes work shape, components, source obligations, provider
jobs, quant/synthesis/audit posture, budget posture, follow-up authority, stop
conditions, and final sufficiency policy.

`QueryPlan` currently owns executable query identity/order in existing lanes.
It admits query candidates from researcher/recon, continuation, recovery,
supplemental, remediation, recency, and related compatibility paths before
retrieval consumes query text. It also records that provider and depth policy
are unchanged.

`SearchWorkPlan` should not trample QueryPlan by implication. A constructed
plan should not mean query text exists, query ordering is chosen, provider
search is scheduled, search depth changes, or QueryPlan caps are modified.

Future activation should make QueryPlan consume `SearchWorkPlan`-derived
candidate jobs only through a named adapter/seam, for example a future
`SearchWorkPlanQueryPlanAdapter` or equivalent RunKernel-authorized admission
adapter. That adapter should translate plan components/provider jobs into
candidate query-production work only in a separately licensed phase.

Query text generation and query ordering remain closed until a later phase
explicitly opens them. QueryPlan must not become source-obligation authority,
provider/depth authority, final sufficiency authority, or citation authority.
Those remain with RunAuthorityContract, `SearchWorkPlan` work shape,
EvidenceLedger/SearchJudgment/SufficiencyJudgment, FinalAnswerPacket, and the
bounded provider/job execution surfaces licensed later.

## 7. Old authority paths to subordinate later

| Current or legacy path | Current status | Future posture | Activation requirement |
| --- | --- | --- | --- |
| Legacy Scout query-shaping signals | Keep as compatibility for now | Future subordinate to `SearchWorkPlan.query_shape`, components, and provider jobs | Requires separate activation phase to replace named Scout authority with bounded job output. |
| Researcher/recon query production | Keep as compatibility for now | Future subordinate candidate producer fed by `SearchWorkPlan` job/component posture | Requires separate adapter phase; query text generation remains closed now. |
| Expander/Evaluator continuation signals | Keep as compatibility for now | Future subordinate advisory gap/component signals under SearchJudgment and `SearchWorkPlan.follow_up_authority` | Requires separate activation phase proving follow-up authorization moves to the RunAuthority chain. |
| Current query production / QueryPlan admission boundary | Keep as current runtime authority for executable query identity/order | Future subordinate consumer of plan-derived candidate jobs through a named adapter | Requires behavior-preserving or shadow adapter before any behavior change. |
| Source-class recovery / official-current repair seam | Keep as compatibility/current lane for now | Future subordinate to `SearchWorkPlan.source_obligations`, provider jobs, EvidenceLedger custody, and SearchJudgment recovery decisions | Requires official-source validation phase under shared `SearchWorkPlan`. |
| Weak-corpus recovery | Keep as compatibility/current lane for now | Future subordinate to plan stop conditions, budget posture, and SearchJudgment gap/redundancy decisions | Requires separate activation phase because it touches recovery/search behavior. |
| Synthesis evaluator supplemental search | Keep as compatibility/passive handoff for now | Future demotion candidate into synthesis/audit job signal only; follow-up authorization remains RunAuthority/SearchJudgment | Requires separate activation phase and tests that supplemental search no longer self-authorizes. |
| Economist quantitative planning posture | Keep as compatibility/runtime helper plus passive handoff for now | Future subordinate to `quant_work_units`, source-bound value custody, and QuantValidator/CalculationExecutor design | Requires QuantWorkUnit activation phase. |
| Analyst gap signals | Keep as bounded synthesis output for now | Future advisory only to SearchJudgment/SufficiencyJudgment, never self-authorizing follow-up | Requires separate activation phase around synthesis job boundaries. |
| Scrutineer remediation signals | Keep as compatibility/runtime review path for now | Future subordinate audit/remediation signal under `audit_jobs` and RunAuthority authorization | Requires separate Deep audit/remediation activation phase. |
| `pipeline_orchestrator.py` coordination callsites | Keep as coordinator for now; no changes in AG-96C5 | Future demotion from local decision accumulation to adapter calls and pass-through of RunKernel-owned state | Requires scoped orchestrator-strangulation phases; no new orchestrator brain logic. |

These paths should not be deleted in this design phase. Future activation must
name the exact old path, exact consumer, retirement status, and proof before
changing behavior.

## 8. Runtime consumer design

The future construction consumer should be a RunKernel / RunAuthority
construction seam or a bounded adapter called by a RunKernel-authorized flow.
The design target is not a trace writer, not a QueryPlan shortcut, not a
pipeline-local helper, and not a prompt-only planning instruction.

The future consumer should:

- receive only safe structured inputs;
- construct a valid `SearchWorkPlan`;
- reduce or attach the constructed plan as canonical RunKernel/RunAuthority
  state only after a scoped implementation phase licenses that behavior;
- expose sanitized trace/projection from canonical state;
- leave provider/search/query/citation behavior unchanged until a later
  activation phase explicitly opens those surfaces.

SearchWorkPlan should be consumed by later planning/execution stages only after
a scoped activation phase. Trace/projection may summarize it, but trace cannot
be the authority. A future activation phase must prove the runtime consumer
actually consumes `SearchWorkPlan`, not merely stores it, serializes it, or
projects it into trace.

## 9. Staged activation plan

Suggested staged sequence after AG-96C5:

1. AG-96C6: passive or behavior-preserving `SearchWorkPlan` construction
   adapter skeleton. It may validate safe inputs and construct fixtures, but the
   plan is not consumed.
   Follow-up note: `AG96C6_SEARCHWORKPLAN_CONSTRUCTION_ADAPTER_SKELETON.md`
   implements that passive skeleton and keeps runtime consumption closed.
2. AG-96C7: RunKernel-authorized construction of `SearchWorkPlan` into
   RunState/trace, still not affecting search, QueryPlan, providers, prompts,
   citations, or final answers.
3. AG-96C8: component/source-obligation projection into QueryPlan candidate
   generation through a named adapter, behavior-preserving or shadow only.
4. AG-96D0: official-source validation under shared `SearchWorkPlan` rather
   than a mode-specific official executor.
5. Later: component-aware QueryPlan activation, with query text/order surfaces
   explicitly opened and tested.
6. Later: QuantWorkUnit activation under source-bound EvidenceLedger custody and
   bounded calculation/validation executors.
7. Later: Balanced/Deep follow-up loop activation under SearchJudgment and
   SufficiencyJudgment authority.
8. Later: SocialSignalJob / CommunitySentimentJob design and activation, limited
   to directional perception evidence and never official/legal/canonical/source-
   bound factual satisfaction.

Keep phases small and non-spackly: each phase should name one consumer, one
authority movement, the old path status, the closed surfaces opened, and the
offline tests that prove the boundary.

## 10. Acceptance criteria for future activation

Future implementation must prove:

- the exact runtime consumer is named;
- the seam where that consumer reads `SearchWorkPlan` is named;
- the old authority path is deleted, demoted, bypassed, subordinated, or
  scheduled for retirement with a concrete trigger;
- no new `pipeline_orchestrator.py` brain logic is added;
- `SearchWorkPlan` is consumed, not trace-only, storage-only, wrapper-only, or
  test-only;
- the QueryPlan relationship is explicit and preserves executable query
  identity/order ownership until a later phase opens it;
- provider/search/ranking/filtering behavior changes are separately licensed;
- official/current obligations remain source obligations and evidence custody
  requirements, not provider hierarchy or citation shortcuts;
- bounded executors such as Analyst, Scout, Economist, Scrutineer, and Author do
  not authorize follow-up;
- tests prove both consumption by the named runtime consumer and demotion,
  subordination, bypass, or deletion of the old path;
- prompt, provider/search, QueryPlan, mode policy, citation, final answer, and
  live-validation surfaces remain unchanged unless explicitly opened by that
  phase.

## 11. Non-goals

AG-96C5 does not:

- construct `SearchWorkPlan` at runtime;
- implement a `QueryShapeClassifier`;
- implement a `ContractResolver`;
- change QueryPlan behavior;
- change query text generation or query ordering;
- change provider selection, provider routing, search depth, retrieval, ranking,
  filtering, or citation behavior;
- change `mode_policy.py`;
- change prompts;
- change Author, Analyst, Economist, Scrutineer, Scout, or provider behavior;
- activate QuantWorkUnit;
- activate Balanced/Deep loops;
- perform official-source validation;
- implement social-signal jobs;
- add providers;
- touch `core/pipeline_orchestrator.py`;
- run live ScryRaven/proplex provider, model, search, retrieval, or validation
  calls.

## 12. Known limitations

This design does not decide hard numeric component budgets, query-generation
schemas, provider selection, search depth, social/perception evidence design, or
the exact implementation shape of a future RunKernel action. It also does not
prove that current query-shape heuristics are sufficient. Those questions need
their own activation or validation phases.
