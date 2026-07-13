Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96C4_QUERY_SHAPE_CONTRACT_RESOLUTION_PASSIVE_RECORDS).

# AG-96C4 Query Shape / Contract Resolution Passive Records

## 1. Status and scope

Status: passive records and construction design only.

AG-96C4 adds `core/query_shape_contract_resolution.py` as a passive record layer
for future query-shape assessment, requested-mode contract resolution, and
SearchWorkPlan construction design. The module defines dataclasses, enums,
JSON-safe serialization, and invariant validation. It does not classify queries
at runtime, implement a ContractResolver, construct `SearchWorkPlan`, alter
`QueryPlan`, change `mode_policy.py`, call providers/search/retrieval, change
prompts, change Analyst/Author/Economist/Scrutineer behavior, activate
QuantWorkUnit, activate Balanced/Deep loops, perform official-source
validation, implement social-signal jobs, or touch `core/pipeline_orchestrator.py`.

No live ScryRaven/proplex provider, model, search, or retrieval calls were run.
No secrets, `.env`, raw prompts, raw provider payloads, DB rows, private logs,
caches, full raw traces, local output packets, or private artifacts were needed.

## 2. Relationship to AG-96C2 and AG-96C3

AG-96C2 introduced the passive `SearchWorkPlan` contract. It gave the future
runtime a JSON-safe target shape for mode contracts, query shape, components,
source obligations, provider jobs, quant work units, audit jobs, budgets,
follow-up authority, and stop conditions.

AG-96C3 described the future pre-search decision layer: query-shape assessment
and requested-mode to effective-contract resolution should eventually fill
SearchWorkPlan fields before search execution, while keeping RunKernel /
RunAuthority as the governing chain.

AG-96C4 turns that design vocabulary into passive records:

- `QueryShapeAssessment` records future assessment output.
- `ContractResolutionRecord` records future requested-mode to effective-contract
  resolution.
- `SearchWorkPlanConstructionDesignRecord` records the future handoff path
  without executing it.
- Candidate records describe conceptual future inputs for SearchWorkPlan fields.

These records are not runtime consumers. They are schema and validation
scaffolding for a later construction phase.

## 3. Authority vocabulary

There is one RunAuthority chain. RunKernel is the runtime authorizer enforcing
that chain. SearchJudgment and SufficiencyJudgment are subordinate judgment
surfaces under the RunAuthority chain, not peer authorities competing with it.

Preferred vocabulary:

- RunAuthority chain owns the run contract, obligations, allowed depth,
  follow-up posture, and stop/escalate/refuse posture.
- SearchJudgment owns specific continuation, source-gap, redundancy, and search
  recovery judgment under that chain.
- SufficiencyJudgment owns specific final-readiness, insufficiency, conflict,
  and source-bound numeric unknown judgment under that chain.
- RunKernel authorizes runtime actions based on the chain and reduced state.

Bounded executors such as Analyst, Scout, Economist, Scrutineer, and Author may
produce signals or prose in future scoped phases, but they cannot authorize
follow-up search or mode budget escalation.

## 4. QueryShapeAssessment overview

`QueryShapeAssessment` represents future query-shape assessment output. It can
record:

- schema and assessment identity;
- query-shape kinds such as official/current lookup, quantitative comparison,
  source-bound numeric, conflict-likely, currentness, and normalization required;
- requested mode;
- passive confidence and assessment posture;
- component, source-obligation, provider-job, quant-work, audit-job, and
  social/perception candidates;
- first-pass-evidence-needed flags;
- deterministic and model-assisted signals;
- ambiguity and normalization notes;
- stop-condition candidates;
- sanitized metadata;
- explicit passive/no-runtime-consumption flags.

The record must not store raw prompts, raw provider payloads, raw model
responses, secrets, DB rows, full traces, caches, private logs, or local output
packets. Serialization omits sensitive keys and keeps only JSON-safe primitive
values.

Validation rejects duplicate candidate IDs, missing component references,
attempted downgrades of official/legal/canonical/source-bound obligations, and
social/perception candidates that claim to satisfy official, legal, factual,
medical, financial, canonical, or source-bound numeric obligations.

## 5. ContractResolutionRecord overview

`ContractResolutionRecord` represents future requested-mode to effective-contract
resolution. It can record:

- requested mode;
- effective contract, such as `direct_constrained`, `explanatory`, or
  `research_reconciliation`;
- mode mismatch posture;
- allowed follow-up depth posture;
- output posture;
- stop/escalate/refuse posture;
- authority chain owner;
- SearchJudgment and SufficiencyJudgment owner fields;
- RunKernel as runtime authorizer;
- allowed follow-up authorizers;
- rationale and sanitized metadata;
- explicit passive/no-runtime-consumption flags.

Validation preserves two key mode rules:

- Balanced may downshift to Fast-shaped direct constrained work when the query
  is simple, but required source obligations are not weakened.
- Fast may not silently spend Balanced or Deep budget. If Fast is insufficient,
  the record must say so through selected-mode-insufficient, qualify/refuse, or
  escalation posture rather than hiding a deeper effective contract.

Validation also rejects Analyst, Scout, Economist, Scrutineer, and Author as
follow-up authorizers or authority owners.

## 6. SearchWorkPlanConstructionDesignRecord overview

`SearchWorkPlanConstructionDesignRecord` represents the future construction
handoff without constructing `SearchWorkPlan` at runtime. Its construction
posture is `passive_design_only`.

It records:

- future runtime consumer: RunKernel / RunAuthority construction seam;
- future output: `SearchWorkPlan`;
- inputs needed, such as `QueryShapeAssessment`, `ContractResolutionRecord`,
  RunAuthorityContract source requirements, and safe route facts;
- fields to populate;
- old authority paths to subordinate later;
- closed surfaces;
- activation prerequisites;
- passive/no-runtime-consumption flags.

This record describes the fill path only. It does not execute classification,
resolution, query planning, provider jobs, quant work, audit work, or
SearchWorkPlan construction.

## 7. Candidate records and future fill path

Candidate records are deliberately small:

- `ComponentCandidate` maps conceptually to future `SearchWorkPlan.components`.
- `SourceObligationCandidate` maps conceptually to future source obligations and
  preserves strict official/legal/canonical/source-bound requirements.
- `ProviderJobCandidate` maps conceptually to future provider-neutral
  `provider_jobs`; provider identity remains subordinate to job.
- `QuantWorkCandidate` maps conceptually to future `quant_work_units`; it does
  not execute calculations or code.
- `AuditJobCandidate` maps conceptually to future `audit_jobs`; remediation
  remains conditional/passive and cannot create an open-ended loop.
- `SocialSignalCandidate` / `PerceptionSignalCandidate` is deferred vocabulary
  for perception/community-sentiment need only.

Future fill path:

```text
QueryShapeAssessment + ContractResolutionRecord
-> RunKernel / RunAuthority construction seam
-> SearchWorkPlan fields
-> later QueryPlan/provider/job execution phases
```

AG-96C4 stops at the record layer. It does not construct or consume the plan.

## 8. QuantWorkUnit remains planning only

Quant work remains planning-only. `QuantWorkCandidate` can record target metric,
components, required variables, source-bound values needed, allowed calculations,
and assumptions needed. It explicitly serializes that calculations and code are
not executed.

Future activation must separately design source-bound value extraction,
deterministic calculation execution, quant validation, synthesis, sufficiency,
FinalAnswerPacket exposure, and Author boundaries. Model-invented values,
unsupported assumptions, arbitrary code execution, and Author-side hidden math
remain rejected.

## 9. SocialSignalJob / CommunitySentimentJob deferred note

`SocialSignalCandidate` is deferred vocabulary only. It may represent a future
need for perception evidence, reputation signals, community sentiment, customer
complaints, user reports, or developer reaction.

Social/perception evidence is directional context. It must not satisfy official,
legal, canonical, factual, medical, financial, or source-bound numeric
obligations. It is not an official-source substitute, not a final evidence
authority, and not implemented as a runtime job in AG-96C4.

## 10. Non-goals

AG-96C4 does not:

- implement runtime query classification;
- implement runtime ContractResolver;
- construct or consume SearchWorkPlan at runtime;
- change QueryPlan behavior;
- change provider selection, provider routing, search depth, retrieval, ranking,
  filtering, or citation behavior;
- change `mode_policy.py`;
- change prompts;
- change Author, Analyst, Economist, Scrutineer, Scout, or provider behavior;
- activate QuantWorkUnit;
- activate Balanced/Deep follow-up loops;
- perform official-source validation;
- implement social-signal jobs;
- touch `core/pipeline_orchestrator.py`;
- run live calls.

## 11. Recommended next phases

1. SearchWorkPlan runtime construction design from RunKernel.
2. Official-source validation under shared SearchWorkPlan.
3. Component-aware QueryPlan relationship design.
4. QuantWorkUnit activation design.
5. SocialSignalJob / CommunitySentimentJob design.
6. Balanced/Deep follow-up loop activation.

Each activation phase should name the runtime consumer, old authority paths to
subordinate or retire, opened surfaces, offline tests, and live-validation
boundary if live evidence is required.

AG-96C5 follow-up note:
`AG96C5_SEARCHWORKPLAN_RUNTIME_CONSTRUCTION_DESIGN.md` defines the future
RunKernel / RunAuthority construction seam for the passive records above. It
remains design/static only and does not construct or consume `SearchWorkPlan`.
