# AG-96C3 Query Shape, Contract Resolution, and Authority Ownership Design

## 1. Status and scope

Status: architecture/design only.

AG-96C3 defines how ScryRaven should eventually decide what kind of search
work a user request needs before search execution. It describes the future
RunKernel / RunAuthority decision layer that can fill a `SearchWorkPlan` with
query shape, effective contract, component posture, source obligations,
provider jobs, follow-up authority, stop/escalate/refuse posture, and bounded
quantitative work planning.

This phase makes no runtime behavior changes. It does not implement runtime
query classification, runtime contract resolution, `SearchWorkPlan`
construction, `QueryPlan` behavior changes, provider/search/ranking/citation
changes, Author or Analyst behavior changes, `mode_policy.py` changes, prompt
changes, or live validation.

Closed for this phase:

- runtime behavior;
- prompt behavior;
- provider/search/ranking/filtering/citation behavior;
- query generation/runtime behavior;
- `QueryPlan` runtime behavior;
- `mode_policy.py`;
- `SearchWorkPlan` runtime construction or consumption;
- `QuantWorkUnit` runtime activation;
- Analyst, Author, Economist, and Scrutineer behavior;
- `core/pipeline_orchestrator.py`;
- live ScryRaven/proplex provider, model, search, or retrieval calls.

## 2. Authority vocabulary clarification

The future design must not describe RunKernel, RunAuthority, SearchJudgment, and
SufficiencyJudgment as four competing peer authorities. They are different
layers in one authority chain:

| Term | Future meaning |
| --- | --- |
| RunKernel | Active runtime governor/executive. It authorizes bounded actions and reduces executor observations into canonical run state. |
| RunAuthority | Authority doctrine, contract, and state chain that RunKernel enforces. It owns the run contract, obligations, allowed depth, follow-up posture, and stop/escalate/refuse posture. |
| SearchJudgment | Search, follow-up, redundancy, source-gap, and recovery judgment surface under the RunAuthority chain. It judges whether more search is warranted, not whether final prose is ready. |
| SufficiencyJudgment | Answer-readiness, insufficiency, conflict, source-bound numeric unknown, and fail-closed judgment surface under the RunAuthority chain. It judges whether final answering is allowed and under what posture. |

Preferred future wording:

- `follow_up_authority` = RunAuthority chain;
- specific judgment owner for search continuation/source-gap recovery =
  SearchJudgment;
- specific judgment owner for final readiness/insufficiency posture =
  SufficiencyJudgment;
- runtime authorization = RunKernel authorizes an action based on those
  judgments.

Rejected wording:

- RunKernel, RunAuthority, SearchJudgment, and SufficiencyJudgment as four peer
  authorities;
- Analyst, Author, Economist, Scout, or Scrutineer as follow-up authorizers;
- QueryPlan as source obligation, provider/depth, or final sufficiency
  authority;
- trace/projection fields as a second policy engine.

## 3. Query-shape classification design

The future query-shape assessment layer should run before search execution when
enough request context is available, and it should be explicitly allowed to
defer some shape conclusions until first-pass evidence exists. Its output should
eventually populate `SearchWorkPlan.query_shape`, components, source
obligations, provider jobs, quant work units, budget posture, and stop
conditions. AG-96C3 does not implement this layer.

### Inputs available before search

Pre-search assessment may use only safe, repo-visible runtime facts that are
already available before provider/search execution:

- user query text as a bounded request reference, not stored raw in traces;
- requested UI mode or user-requested mode;
- current date/time facts already provided to the run;
- route facts such as intent, report type, query type, core topic, primary
  entity, entities, academic/news hints, image mode, and complexity posture;
- include/exclude domain hints explicitly supplied by the user;
- current `RunAuthorityContract` source requirements when already synthesized;
- existing mode policy snapshot as a passive input, not as a new policy engine;
- safe static configuration such as known mode names and schema vocabulary.

### Inputs that may require first-pass evidence

Some shape signals cannot be decided reliably before search. The future layer
should mark these as tentative and let SearchJudgment/SufficiencyJudgment
confirm or repair them after evidence exists:

- whether sources actually conflict;
- whether a lower-tier bridge source can lead to official/current custody;
- whether an apparent official/current page is answer-bearing;
- whether numeric values are source-bound, current, comparable, and entity
  bound;
- whether a canonical docs page has the requested version or parameter;
- whether a comparison needs normalization beyond obvious units;
- whether ambiguity is solved by first-pass entity evidence;
- whether first-pass evidence creates a new required source obligation.

### Shape signals

Useful query-shape signals include:

- words that imply currentness: current, latest, today, 2026, as of, effective,
  deadline, rate, fee, law, rule;
- source-class cues: official, IRS, SEC, court, statute, API docs, release
  notes, manual, primary source;
- legal/current cues: legal deadline, statute, regulation, court rule, filing,
  compliance, eligibility;
- canonical documentation cues: API, SDK, parameter, version, docs, changelog,
  reference;
- comparison cues: compare, vs, difference, better, cheaper, larger, between;
- multipart cues: several named entities, numbered questions, "and", "for each";
- quantitative cues: cost per, rate, percentage, average, ratio, passenger mile,
  emissions per, per capita;
- source-bound numeric cues: exact value, threshold, taxable maximum, mileage
  rate, fee, official statistic, year-bound figure;
- ambiguity cues: short person/entity names, common acronyms, overloaded product
  names, missing jurisdiction/version/entity;
- conflict-likely cues: volatile policy, unsettled facts, live events, multiple
  effective dates, disputed claims;
- normalization cues: different units, periods, geographies, product versions,
  consumer classes, aircraft configurations, load factors, currencies;
- perception cues: reputation, community reaction, developer sentiment,
  customer complaints, user reports.

### Deterministic heuristic candidates

Future deterministic heuristics may classify obvious shapes without model
reasoning:

- exact current/legal/official phrases map to official/current or
  legal/current-primary obligations;
- API/docs/version terms map to canonical documentation obligations;
- "vs" plus numeric metric terms maps to quantitative comparison plus
  normalization-required;
- fee/rate/threshold/tax/mileage terms with a year map to source-bound numeric
  and time-sensitive/currentness;
- named jurisdictions plus legal terms map to legal/current-primary;
- more than one central entity plus compare/list language maps to multipart
  comparison;
- obvious single fact plus official cue maps to simple official/current lookup;
- common ambiguity markers map to ambiguous entity.

Deterministic classification should be conservative. It may add obligations or
tentative flags, but it must not silently weaken a strong source requirement.

### Model-assisted reasoning candidates

Model-assisted assessment may be useful when the query has ambiguous scope,
implicit components, unclear source obligations, or a mode mismatch that
requires explanation. If used later, it should be bounded by schemas and repair
rules similar to the current RunAuthority judgment validation style:

- produce structured shape candidates, not free-form runtime policy;
- explain component boundaries and source-obligation rationale;
- suggest missing clarifying dimensions such as jurisdiction, version, period,
  unit, entity binding, or population;
- never downgrade official/legal/canonical/source-bound requirements created by
  deterministic rules unless a validator admits the repair;
- never authorize search by itself.

### What remains passive until activated

The following stay passive design vocabulary until a later phase explicitly
activates them:

- runtime `QueryShapeClassifier`;
- runtime `ContractResolver`;
- runtime `SearchWorkPlan` construction;
- new query text generation behavior;
- provider job execution;
- `QuantWorkUnit` execution;
- social/perception evidence jobs;
- Balanced/Deep follow-up loops.

### Required shape vocabulary

The future assessment layer should support at least:

| Shape | Meaning | Typical future effect |
| --- | --- | --- |
| simple lookup | One narrow fact or definition with ordinary evidence needs. | Direct constrained component, small budget, ordinary stop policy. |
| official/current lookup | Current answer requires official/current source custody. | Official/current source obligation and official candidate acquisition job. |
| legal/current-primary | Current legal/regulatory answer requires primary law/rule/court/government source. | Legal/current primary source obligation and fail-closed posture if absent. |
| canonical documentation | Answer should come from canonical docs, manuals, specs, changelogs, or source repositories. | Canonical documentation obligation and canonical extraction job. |
| multipart comparison | Multiple central components or entities must be covered fairly. | Component decomposition and per-component minimum viable budgets. |
| quantitative comparison | Answer requires numeric comparison, ratios, or normalized metrics. | Quant work unit planning, source-bound extraction, normalization notes. |
| source-bound numeric | A number must be extracted from admitted evidence, not invented or inferred loosely. | Source-bound numeric obligation and missing-value stop condition. |
| ambiguous entity | Entity identity is under-specified or overloaded. | Scout/disambiguation provider job or stop/escalate for clarification. |
| time-sensitive/currentness | Currentness, effective date, or recent status materially affects correctness. | Date-bound currentness obligation and currentness/conflict checks. |
| conflict-likely | Sources may disagree or effective dates may conflict. | Reconciliation/audit jobs and caveat/fail-closed stop conditions. |
| normalization-required | Inputs differ by unit, period, jurisdiction, entity binding, version, or definition. | Component assumptions, quant validation, synthesis caveats. |
| social/perception signal needed | Future perception evidence may be useful for reputation or community-sentiment questions. | Deferred SocialSignalJob / CommunitySentimentJob vocabulary only. |

Social signal note: `SocialSignalJob` / `CommunitySentimentJob` is future
perception-evidence vocabulary only. It is not authority for official, legal,
factual, canonical, or source-bound numeric claims, and it is not in scope for
runtime implementation in AG-96C3.

## 4. Contract-resolution design

Future RunKernel should resolve user-requested mode into an effective contract
before search execution. The resolver should decide whether the selected mode
is enough, whether the work can safely collapse to a shallower contract, whether
the answer must be qualified, whether an escalation suggestion is needed, or
whether the run should refuse/fail closed.

The future resolution output should include:

- `requested_mode`: the user/UI requested mode, including source and rationale;
- `effective_contract`: direct constrained, explanatory, research
  reconciliation, or unresolved;
- `mode_mismatch_posture`: none, possible, selected mode insufficient,
  qualify/refuse, or escalate suggested;
- allowed follow-up depth: none/minimal, conditional gap-driven, or larger
  bounded loop;
- output posture: direct, compact explanatory, resolved depth, partial,
  insufficient, or refusal/failure-card posture;
- stop/escalate/refuse posture: when obligations are unsatisfied, the selected
  mode is too shallow, required inference is unsupported, or live validation is
  not authorized.

Contract resolution should keep two ideas separate:

- Requested mode is user intent or UI selection.
- Effective contract is what RunKernel/RunAuthority may safely authorize for
  this run.

Examples:

| Request | Future resolution posture |
| --- | --- |
| Balanced user request that can collapse to Fast-shaped work | Requested mode remains Balanced, but effective contract may be `direct_constrained` when the query is a simple lookup with no special obligations. This should reduce output depth and follow-up posture, not silently remove required evidence. |
| Fast user request that exceeds Fast | Requested mode remains Fast. Effective contract should not silently spend Balanced budget. It should answer only with direct supported material, qualify limits, suggest escalation, or refuse/fail closed when source-bound, legal/current, reconciliation, or deep normalization needs exceed Fast. |
| Deep request needing reconciliation/audit | Requested mode Deep maps to `research_reconciliation`, with component-aware breadth, conflict/currentness checks, audit jobs, larger bounded follow-up, and explicit stop conditions. Deep is not merely longer prose. |
| Simple official/current lookup | May be Fast-shaped in depth, but source obligation remains strict. If official/current evidence is not acquired, posture is qualify/fail closed rather than using lower-tier evidence as final support. |
| MD-80 vs 777-style quantitative comparison | Requested Fast should likely escalate/qualify because source-bound inputs, normalization, assumptions, and calculations exceed direct Fast. Balanced may plan source-bound extraction plus deterministic calculation under assumptions. Deep may add reconciliation, ranges, sensitivity, and audit of assumptions. |

AG-96C3 does not implement a `ContractResolver`.

## 5. SearchWorkPlan fill path

Future runtime phases should eventually use query-shape assessment and
contract-resolution decisions to populate the passive AG-96C2
`SearchWorkPlan` contract before search execution. The intended fill path is:

| SearchWorkPlan field | Future fill source |
| --- | --- |
| `requested_mode` | User/UI mode plus bounded source/rationale. |
| `effective_contract` | RunKernel/RunAuthority contract resolver output. |
| `query_shape` | Query-shape assessment, with tentative flags for first-pass-evidence-dependent signals. |
| `components` | Component decomposition derived from shape, entities, source obligations, and comparison/normalization needs. |
| `source_obligations` | RunAuthorityContract requirements plus shape-derived official/current, legal/current-primary, canonical, date-bound, source-bound numeric, conflict, or ordinary obligations. |
| `provider_jobs` | Provider-neutral jobs selected to satisfy component obligations, such as disambiguation, official candidate acquisition, canonical extraction, fetch/read/extract, conflict/currentness check, or reconciliation support. |
| `quant_work_units` | Source-bound numeric planning records for metrics, required variables, unsupported values, allowed calculations, assumptions, validation needs, and high-stakes posture. |
| `synthesis_jobs` | Bounded Analyst/synthesis work over admitted or explicitly scoped evidence and component outputs. |
| `audit_jobs` | Bounded Deep-oriented claim challenge, currentness audit, conflict reconciliation, or quantitative assumption audit. |
| `budget` | Base mode budget posture, per-component minimum viable budgets, per-component caps, global cap, rebalancing policy, and exhaustion posture. |
| `follow_up_authority` | RunAuthority chain permissions, with SearchJudgment for continuation/source-gap recovery and SufficiencyJudgment for final readiness/insufficiency posture. |
| `stop_conditions` | Source obligation unsatisfied, budget exhausted, mode mismatch, inference overrun, source-bound numeric missing, unresolved conflict/currentness, and live validation not authorized. |
| `final_sufficiency_policy` | SufficiencyJudgment/FinalAnswerPacket policy for required components, source obligations, budget exhaustion, claim posture, caveats, and prohibited upgrades. |

This phase does not construct `SearchWorkPlan` at runtime. The current
`core/search_work_plan.py` model remains passive and unconsumed.

## 6. QuantWorkUnit execution path design

`QuantWorkUnit` is a planning object, not the math executor. It should describe
what numeric work is needed, which components and obligations it belongs to,
which source-bound values are required, which assumptions are unsupported or
missing, and which deterministic calculations are allowed once values are
admitted.

Future bounded work chain:

```text
QuantWorkUnit
-> source-bound value extraction
-> deterministic calculation executor
-> quant validation
-> synthesis job
-> SufficiencyJudgment
-> FinalAnswerPacket
-> Author
```

Future roles:

- `SourceValueExtractor`: extracts values from admitted evidence only. It may
  bind values to source IDs, entities, units, dates, periods, and variable
  names. It must not invent values or use unsupported model memory.
- `CalculationExecutor`: performs only approved deterministic operations over
  source-bound values. It does not choose assumptions, fetch data, run arbitrary
  code, or decide final answer posture.
- `QuantValidator`: checks entity binding, units, time periods, source IDs,
  unsupported values, calculation provenance, high-stakes posture, and whether
  the numeric claim can safely reach synthesis.
- `SynthesisJob` / Analyst: explains meaning, assumptions, uncertainty, and
  limits. It may not launder unsupported numeric assumptions into sourced
  claims.
- `FinalAnswerPacket`: exposes only allowed numeric posture, caveats,
  prohibited upgrades, and citation/evidence eligibility to Author.

Explicitly rejected:

- model-invented numeric values;
- arbitrary code execution;
- Economist or `QuantWorkUnit` as final numeric authority;
- Author doing hidden calculations;
- Analyst laundering unsupported numeric assumptions into sourced claims;
- provider snippets, bridge material, or social/perception evidence becoming
  source-bound numeric authority without canonical custody.

## 7. Authority ownership matrix

| Decision/work item | Future owner | Bounded executor allowed? | Notes |
| --- | --- | --- | --- |
| Query-shape assessment | RunKernel / RunAuthority contract-resolution layer | Yes, as bounded classifier or model-assisted assessor | Output is structured posture, not search authorization by itself. |
| Effective contract resolution | RunKernel enforcing RunAuthority doctrine | No authority-owning executor | Resolves requested mode vs effective contract and mismatch posture. |
| Component decomposition | SearchWorkPlan under RunAuthority | Yes, as advisory decomposition worker | Components define breadth and prevent one-sided starvation. |
| Source-obligation recognition | RunAuthorityContract, SearchWorkPlan, EvidenceLedger custody path | Yes, as advisory extractor | Strong obligations must not be weakened by model output. |
| Provider-job planning | SearchWorkPlan under RunAuthority | Yes, as planning worker | Jobs are provider-neutral; provider identity is subordinate. |
| Query text generation | QueryPlan admission boundary, fed by bounded candidate generators | Yes | Candidate text may be generated, but executable identity/order remains QueryPlan until replaced by a later scoped phase. |
| Source-bound value extraction | EvidenceLedger/source-value custody path | Yes, SourceValueExtractor | Extracts only from admitted evidence and records source IDs. |
| Deterministic calculation | CalculationExecutor authorized by RunKernel | Yes | Only approved operations over source-bound values. |
| Quant validation | QuantValidator under RunAuthority/SufficiencyJudgment posture | Yes | Validates units, periods, entity binding, sources, unsupported values, and risk posture. |
| Evidence synthesis | SearchWorkPlan synthesis_jobs / bounded Analyst | Yes | Synthesizes admitted or explicitly scoped evidence without owning follow-up authority. |
| Follow-up authorization | RunAuthority chain; SearchJudgment for continuation/source-gap recovery | No authority-owning executor | Analyst/Scout/Economist/Scrutineer may signal gaps but cannot authorize follow-up. |
| Final sufficiency | SufficiencyJudgment under RunAuthority chain | Yes, as bounded judgment executor | Decides readiness, insufficiency, caveats, conflict, and fail-closed posture. |
| Final evidence/citation eligibility | EvidenceLedger and FinalAnswerPacket | No | Author cannot independently select or upgrade citations. |
| Final answer writing | AuthorExecutor consuming FinalAnswerPacket-derived payload | Yes, AuthorExecutor | Writes final prose within packet authority; no hidden calculations or evidence selection. |

## 8. Non-goals

AG-96C3 explicitly does not:

- implement runtime `QueryShapeClassifier`;
- implement runtime `ContractResolver`;
- construct `SearchWorkPlan` at runtime;
- change `QueryPlan` behavior;
- change provider selection, provider routing, provider depth, search depth, or
  retrieval behavior;
- change `mode_policy.py`;
- change prompts;
- change Author, Analyst, Economist, Scrutineer, or Scout behavior;
- activate `QuantWorkUnit`;
- activate Balanced or Deep loops;
- perform official-source validation;
- implement social-signal jobs;
- add providers;
- change `core/pipeline_orchestrator.py`;
- run live calls.

## 9. Relationship to AG-96C2

AG-96C2 created the passive `SearchWorkPlan` data model. AG-96C3 describes the
future pre-search decision layer that may eventually fill that passive model.
The relationship is intentionally one-way in this design phase:

```text
future RunKernel/RunAuthority resolution design
-> eventual SearchWorkPlan construction phase
-> eventual QueryPlan/provider/job execution phases
```

No AG-96C3 field is runtime-consumed today.

## 10. Recommended next phases

1. AG-96C4: passive `QueryShapeAssessment` / `ContractResolution` records, if a
   code contract is needed.
2. AG-96C5: `SearchWorkPlan` runtime construction design from RunKernel, still
   not execution.
3. AG-96D0: official-source validation under shared `SearchWorkPlan`.
4. Later: `QuantWorkUnit` activation design under source-bound evidence custody.
5. Later: `SocialSignalJob` / `CommunitySentimentJob` design.
6. Later: Balanced/Deep follow-up loop activation.

## 11. Known limitations

This design does not prove that the future classification and contract
resolution heuristics are sufficient. It does not decide hard numeric budgets,
provider routing, query text, prompt text, or the exact model-assisted schema.
It intentionally leaves first-pass-evidence-dependent shape repair to future
SearchJudgment/SufficiencyJudgment integration phases.

AG-96C4 follow-up note:
`AG96C4_QUERY_SHAPE_CONTRACT_RESOLUTION_PASSIVE_RECORDS.md` adds passive
query-shape assessment, contract-resolution, and SearchWorkPlan construction
design records. Those records remain schema/validation scaffolding only; they do
not construct `SearchWorkPlan` or change runtime behavior.
