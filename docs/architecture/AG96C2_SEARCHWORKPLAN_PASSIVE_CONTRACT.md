# AG-96C2 SearchWorkPlan Passive Contract

## 1. Status and scope

Status: passive contract and data model only.

AG-96C2 adds `core/search_work_plan.py` as a repo-tracked, JSON-safe
SearchWorkPlan schema for future RunKernel-governed search-work planning. It
also adds focused offline tests for the passive model.

This phase makes no runtime behavior changes. It does not change prompt
behavior, provider selection, provider routing, search depth, query generation,
retrieval, ranking, citation behavior, Author behavior, mode policy, or
`core/pipeline_orchestrator.py`. It does not wire SearchWorkPlan into RunKernel,
QueryPlan, EvidenceLedger, SearchJudgment, SufficiencyJudgment,
FinalAnswerPacket, AuthorExecutor, or any runtime loop. No live validation,
provider call, model call, search call, retrieval call, secret access, private
log inspection, DB inspection, cache inspection, raw prompt inspection, raw
provider payload inspection, full trace inspection, or local output packet
inspection was performed.

The module is side-effect free by construction: it defines dataclasses, enums,
serialization helpers, and validation helpers. Constructing a SearchWorkPlan is
not authorization to execute it.

## 2. Doctrine recap

AG-96C0 and AG-96C1 establish the durable doctrine this model represents:

- All modes are RunKernel / RunAuthority governed.
- Modes control reasoning depth, follow-up authority, and budget shape.
- Query components control breadth.
- Source obligations control evidence requirements.
- Providers are selected by job.
- Executors are bounded workers, not authority owners.
- Official/current is a source obligation and search constraint, not a separate
  mode-specific executor family.
- Final source/evidence authority remains:
  `RunAuthorityContract -> EvidenceLedger -> SearchJudgment ->
  SufficiencyJudgment -> FinalAnswerPacket -> AuthorExecutor`.

The SearchWorkPlan contract makes that doctrine explicit as data without
activating any runtime consumer.

## 3. Data model overview

### SearchWorkPlan

`SearchWorkPlan` is the top-level passive contract. It records schema version,
requested mode, effective contract, query shape, components, provider jobs,
quant work units, synthesis jobs, audit jobs, budget posture, follow-up
authority, final sufficiency policy, stop conditions, authority references,
passive planning posture, and sanitized metadata.

Its serialized form includes explicit no-change flags:

- `runtime_consumed: false`
- `prompt_behavior_changed: false`
- `provider_search_behavior_changed: false`

### RequestedModeDescriptor and EffectiveContractDescriptor

The requested mode records what the user or UI selected: Fast, Balanced, Deep,
Auto, or unresolved. The effective contract records the shape a future
RunKernel/RunAuthority resolver may choose:

- `direct_constrained` for Fast-shaped work;
- `explanatory` for Balanced-shaped work;
- `research_reconciliation` for Deep-shaped work;
- `auto_unresolved` for future unresolved posture.

Mode mismatch is represented as posture, such as possible, selected mode
insufficient, qualify/refuse, or escalation suggested. AG-96C2 does not implement
a ContractResolver.

### QueryShapeDescriptor

`QueryShapeDescriptor` records query shape, not live classification. Supported
kinds include simple lookup, multipart, comparative, quantitative comparison,
official/current lookup, legal/current primary, canonical documentation,
source-bound numeric, ambiguous entity, time-sensitive, conflict-likely,
normalization-required, and mode-mismatch-possible.

### SearchWorkComponent

`SearchWorkComponent` represents component-level breadth. It carries a stable
component ID, user-facing subquestion, entities, anchors, source obligations,
required provider job kinds, per-component budget, mode depth allowance, local
stop conditions, dependencies, and sanitized metadata.

Validation rejects duplicate component IDs and references to missing components.
Component budgets can be numeric or qualitative; when both minimum and cap are
numeric, validation rejects a minimum that exceeds the cap.

### SourceObligation

`SourceObligation` records evidence requirements. Supported kinds include
official/current, legal/current primary, canonical documentation,
source-bound numeric, peer-reviewed, reputable secondary, conflict resolution,
date-bound currentness, user document, and ordinary/no-special-obligation.

Official/current is represented as an obligation and search constraint. It is
not a separate official executor family and does not imply a provider hierarchy.

### ProviderJob

`ProviderJob` records acquisition work by job kind, not by provider hierarchy.
Supported job kinds include scout disambiguation, direct candidate search,
official candidate acquisition, semantic recall, fetch/read/extract, bridge hint
discovery, conflict/currentness check, canonical extraction, and reconciliation
support.

Provider names are not required to construct a provider job. Optional provider
metadata is inert and sanitized; it is not policy.

### QuantWorkUnit

`QuantWorkUnit` is the passive home for future Economist-derived capability. It
records target metric, component IDs, required variables, source-bound values
needed, unsupported values, allowed calculations, assumptions needed, high-stakes
quant posture, direct-use eligibility, and synthesis requirement.

It is source-bound and passive. It does not execute calculations, execute code,
call models, call providers, search, retrieve, or decide final numeric answer
posture.

### SynthesisJob

`SynthesisJob` is the passive home for future Analyst-derived bounded synthesis.
It records component IDs, synthesis scope, allowed inputs, unresolved-gap
visibility, output contract, and whether advisory gap signaling is allowed.

Serialized synthesis jobs explicitly state that they do not own source-gap,
search, or remediation authority.

### AuditJob

`AuditJob` is the passive home for future Scrutineer-derived audit work. It
records component IDs, audit scope, claim types, assumptions to test,
source-conflict checks, allowed modes, and remediation permission posture.

Serialized audit jobs explicitly state `bounded: true`, `passive: true`, and
`open_ended_loop: false`. Conditional remediation posture does not authorize a
loop; future authorization must come from RunAuthority/SearchJudgment/
SufficiencyJudgment.

### Budget model

The budget model separates:

- base mode budget posture;
- per-component minimum viable budget;
- per-component cap;
- global cap;
- rebalancing policy;
- budget-exhausted posture.

AG-96C2 does not change current runtime mode caps or hardcode final product
numeric budgets. Test fixtures use small inert values only to prove validation.

### FollowUpAuthority

`FollowUpAuthority` records whether follow-up is allowed, disallowed, or
conditional; the allowed authorizers; and allow/block conditions.

Validation keeps follow-up authority with RunAuthority, RunKernel,
SearchJudgment, and SufficiencyJudgment posture. Bounded executors such as
Analyst, Scout, Economist, Scrutineer, and Author cannot authorize follow-up.

### Stop/Escalate/Refuse conditions

`StopCondition` represents component sufficiency, unsatisfied source
obligation, budget exhaustion, mode mismatch, selected-mode inference overrun,
missing source-bound numeric values, unresolved conflict/currentness, and live
validation not authorized. Outcomes include stop, fail closed, qualify,
escalation suggestion, and refuse.

### FinalSufficiencyPolicy and authority refs

`FinalSufficiencyPolicy` records the final posture and the canonical authority
chain. `AuthorityRef` gives inert references to future authority owners without
mutating them.

## 4. Passive contract examples

### Simple official/current lookup

A Fast-shaped direct plan can contain one component with an
`official_current` source obligation and an
`official_candidate_acquisition` provider job. If the obligation is not
satisfied, the plan can represent fail-closed or qualify posture without
launching more search.

### Multipart factual comparison

A Balanced-shaped comparison can contain separate components for each entity,
each with its own source obligations and per-component budget. This prevents the
future plan from hiding a two-entity comparison inside one crude global query
field where one side can starve.

### Quantitative source-bound comparison

A quantitative aircraft-style cost/passenger-mile plan can contain a
`quantitative_comparison` query shape and a `QuantWorkUnit` with target metric,
required variables, source-bound values needed, unsupported values, allowed
calculations, and assumptions. The unit is a planning record only; it does not
run math.

### Balanced follow-up eligible gap

A Balanced plan can represent a gap such as "generic official page found, but no
answer-bearing official source yet." Follow-up can be conditional and authorized
only by RunAuthority/SearchJudgment/SufficiencyJudgment posture, with budget and
mode mismatch as blockers.

### Deep audit/reconciliation job

A Deep plan can represent a bounded currentness/conflict audit job with
assumptions to test and source-conflict checks. Remediation permission remains
conditional/passive, and no open-ended adversarial loop is implied.

## 5. Explicit non-goals

AG-96C2 does not:

- implement runtime component decomposition;
- implement ContractResolver;
- implement QueryShapeClassifier;
- change QueryPlan runtime behavior;
- change provider selection;
- change `core/mode_policy.py`;
- activate Balanced or Deep loops;
- activate Scrutineer redesign;
- activate QuantWorkUnit runtime behavior;
- change Analyst, Author, Economist, Scout, Scrutineer, citation, or final
  answer behavior;
- validate official-source resilience;
- run live calls.

## 6. Future activation path

Likely future phases:

1. Query-shape and contract-resolution design.
2. SearchWorkPlan runtime construction from RunKernel / RunAuthority.
3. Component-aware query planning and QueryPlan relationship design.
4. QuantWorkUnit activation under source-bound evidence custody.
5. Analyst/Author boundary refinement around synthesis jobs and
   FinalAnswerPacket-derived posture.
6. Scrutineer/AuditJob redesign as bounded Deep-oriented audit over answer,
   evidence, obligations, and assumptions.
7. Official-source validation under shared SearchWorkPlan rather than a
   mode-specific official executor.

Each activation phase must separately name the runtime consumer, the old
authority path being subordinated or retired, the closed surfaces it opens, the
tests required, and any live-validation boundary.
