Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96C6_SEARCHWORKPLAN_CONSTRUCTION_ADAPTER_SKELETON).

# AG-96C6 SearchWorkPlan Construction Adapter Skeleton

## 1. Status and scope

Status: passive adapter skeleton only, not runtime-consumed.

AG-96C6 adds a behavior-preserving construction adapter at
`core/search_work_plan_construction.py`. The adapter accepts explicit safe
structured inputs, validates the passive AG-96C4 records, and constructs a
passive AG-96C2 `SearchWorkPlan` for unit tests and future design proof.

This phase does not wire the adapter into runtime execution. It does not change
query generation, `QueryPlan` behavior, provider/search behavior, prompts,
final answers, citation behavior, `mode_policy.py`, RunKernel state, or
`core/pipeline_orchestrator.py`. It does not run providers, search, retrieval,
models, prompts, QuantWorkUnit calculations, audit remediation, or live
validation.

## 2. Relationship to AG-96C2/C3/C4/C5

AG-96C2 introduced the passive `SearchWorkPlan` contract.

AG-96C3 defined query-shape assessment and contract resolution as future
RunKernel / RunAuthority-owned pre-search decisions.

AG-96C4 added passive records:

- `QueryShapeAssessment`
- `ContractResolutionRecord`
- `SearchWorkPlanConstructionDesignRecord`
- candidate records for components, source obligations, provider jobs, quant
  work, audits, and deferred social/perception signals

AG-96C5 designed the future runtime construction seam and named AG-96C6 as the
next passive adapter skeleton. AG-96C6 implements only that skeleton. It proves
record-to-plan mapping in offline tests, but it does not activate the future
RunKernel runtime consumer described by AG-96C5.

## 3. Construction input record

`SearchWorkPlanConstructionInput` records:

- construction identity and requested-mode source;
- `QueryShapeAssessment`;
- `ContractResolutionRecord`;
- `SearchWorkPlanConstructionDesignRecord`;
- safe route facts;
- an inert RunAuthorityContract reference;
- an inert current-date reference;
- passive mode policy snapshot;
- safe user domain hints;
- sanitized metadata;
- `passive=True`.

The input record is JSON-safe. Serialization omits sensitive/raw/private keys,
including raw prompts, raw provider payloads, raw model responses, secrets,
tokens, `.env`-style material, DB rows, private logs, caches, full traces, and
local output packets.

## 4. Construction result record

`SearchWorkPlanConstructionResult` records:

- construction identity;
- constructed passive `SearchWorkPlan`;
- validation for assessment, contract resolution, construction design, and plan;
- warnings;
- `constructed=True`;
- `runtime_consumed=False`;
- `behavior_changed=False`;
- `prompt_behavior_changed=False`;
- `provider_search_behavior_changed=False`;
- `query_plan_behavior_changed=False`;
- sanitized metadata.

The result is a proof object, not an execution authorization.

## 5. Passive record to SearchWorkPlan mapping

| SearchWorkPlan field | Passive source |
| --- | --- |
| `requested_mode` | `ContractResolutionRecord.requested_mode`, requested-mode source, mismatch posture, rationale |
| `effective_contract` | `ContractResolutionRecord.effective_contract`, output posture, follow-up depth, mismatch posture |
| `query_shape` | `QueryShapeAssessment.query_shape_kinds`, component count, ambiguity and normalization notes |
| `components` | `ComponentCandidate` records |
| component source obligations | `SourceObligationCandidate` records matching component IDs or candidate links |
| `provider_jobs` | `ProviderJobCandidate` records |
| `quant_work_units` | `QuantWorkCandidate` records, planning only |
| `synthesis_jobs` | Empty in this skeleton |
| `audit_jobs` | `AuditJobCandidate` records, bounded and passive |
| `budget` | Requested mode plus passive mode policy snapshot metadata |
| `follow_up_authority` | `ContractResolutionRecord.allowed_follow_up_depth` and allowed authorizers |
| `stop_conditions` | `QueryShapeAssessment.stop_condition_candidates` and contract mismatch posture |
| `final_sufficiency_policy` | Existing `SearchWorkPlan` default authority-chain policy |
| `authority_refs` | Safe inert construction, assessment, resolution, design, and RunAuthorityContract IDs |
| `metadata` | Sanitized construction facts only |

The adapter is conservative. It does not invent missing candidates or execute
repairs. Incomplete or invalid inputs surface through validation errors and
warnings.

## 6. No-runtime-consumer boundary

AG-96C6 adds no runtime consumer. Static tests assert that the new module does
not import or call runtime/provider/search/prompt modules or functions, and that
existing runtime modules do not import the new adapter.

Closed runtime surfaces remain closed:

- RunKernel mutation;
- QueryPlan construction or modification;
- provider job execution;
- retrieval;
- prompts;
- model calls;
- live calls;
- `mode_policy.py`;
- `core/pipeline_orchestrator.py`.

## 7. QueryPlan relationship

`QueryPlan` remains unchanged. It continues to own executable query identity and
ordering in current runtime lanes. Constructing a passive `SearchWorkPlan` does
not create query text, authorize query admission, choose providers, alter depth
policy, satisfy source obligations, decide final sufficiency, or affect citation
eligibility.

Any future QueryPlan relationship needs a separately licensed adapter phase.

## 8. Authority semantics preserved

The adapter preserves the AG-96C authority model:

- RunAuthority chain remains the authority owner.
- SearchJudgment remains the search, follow-up, source-gap, and recovery
  judgment surface under that chain.
- SufficiencyJudgment remains the final readiness and insufficiency surface.
- bounded executors do not authorize follow-up;
- QueryPlan does not become source-obligation, provider/depth, final
  sufficiency, or citation authority;
- official/current remains a source obligation and evidence custody
  requirement, not a provider hierarchy shortcut.

Social/perception candidates remain deferred warnings/context only. They cannot
satisfy official, legal, factual, canonical, medical, financial, or
source-bound numeric obligations.

## 9. Examples covered by tests

The AG-96C6 tests cover:

- official/current simple lookup construction;
- Balanced downshift to direct constrained work with official/current
  obligation preserved;
- Fast insufficient posture without silent Balanced/Deep budget upgrade;
- MD-80 versus 777 quantitative comparison planning without calculations or
  code execution;
- Deep conflict/currentness audit construction with bounded passive remediation
  posture;
- social/perception candidate deferral;
- sensitive input redaction;
- passive import/call boundary;
- no runtime consumer imports.

## 10. Non-goals

AG-96C6 does not:

- construct `SearchWorkPlan` at runtime;
- integrate with RunKernel;
- integrate with QueryPlan;
- change provider, search, ranking, filtering, retrieval, or citation behavior;
- change prompts;
- change `mode_policy.py`;
- change Author, Analyst, Economist, Scrutineer, or Scout behavior;
- execute QuantWorkUnit calculations;
- activate Balanced or Deep loops;
- validate official-source custody;
- implement social-signal runtime behavior;
- run live provider/model/search/retrieval calls;
- change `core/pipeline_orchestrator.py`.

## 11. Recommended next phase

The recommended next phase is AG-96C7: RunKernel-authorized construction of
`SearchWorkPlan` into canonical RunState or trace projection while still
preserving provider/search, QueryPlan, prompt, citation, and final-answer
behavior. That phase must name the exact runtime consumer, prove the consumer
reads the constructed plan, and keep old authority paths explicitly
subordinated or scheduled for retirement.

AG-96C7 follow-up note:
`AG96C7_RUNKERNEL_SHADOW_SEARCHWORKPLAN_CONSTRUCTION.md` adds the
RunKernel-authorized shadow construction action/observation seam and keeps
production runtime consumption closed.
