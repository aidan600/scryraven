# AG-96C7 RunKernel Shadow SearchWorkPlan Construction

## 1. Status and scope

Status: RunKernel-authorized shadow construction only.

AG-96C7 adds a RunKernel action/observation seam for constructing
`SearchWorkPlan` into canonical `RunState` and trace projection after a reduced
RunAuthority contract. It does not add a production runtime callsite and does
not make the constructed plan affect executable query identity, provider
selection, search depth, retrieval, prompts, citations, final answers,
`mode_policy.py`, or `core/pipeline_orchestrator.py`.

No live provider, model, search, retrieval, or validation calls are part of this
phase.

## 2. Relationship to AG-96C6

AG-96C6 introduced `core/search_work_plan_construction.py`, a passive adapter
that turns safe `QueryShapeAssessment`, `ContractResolutionRecord`, and
`SearchWorkPlanConstructionDesignRecord` inputs into a passive
`SearchWorkPlan`.

AG-96C7 keeps that adapter bounded and adds only the action-consuming
observation helper:

```text
RunKernel AuthorizedAction
-> observe_search_work_plan_construction(...)
-> SEARCH_WORK_PLAN_CONSTRUCTED Observation
-> RunKernel.reduce(...)
-> RunState.search_work_plan and trace projection
```

`core/run_kernel.py` does not import the construction adapter. The adapter may
validate a RunKernel action and return an observation, but it does not schedule
providers, build query text, retrieve evidence, call prompts, or mutate
RunKernel directly.

## 3. Added RunKernel vocabulary

AG-96C7 adds:

- stage: `SEARCH_WORK_PLAN_CONSTRUCTION_STAGE =
  "search_work_plan_construction"`
- action type: `ActionType.SEARCH_WORK_PLAN_CONSTRUCT =
  "search_work_plan_construct"`
- observation type: `ObservationType.SEARCH_WORK_PLAN_CONSTRUCTED =
  "search_work_plan_constructed"`

Authorization is via `RunKernel.authorize_search_work_plan_construction(...)`.
It requires an already reduced RunAuthority contract projection. This is a
pre-search shadow construction action; it does not require EvidenceLedger,
SearchJudgment, SufficiencyJudgment, QueryPlan, retrieval, or provider output.

## 4. Canonical state and projection

After reduction, the constructed plan is canonical RunState for this shadow
seam:

- `RunState.search_work_plan`
- `RunState.search_work_plan_projection`
- `RunState.search_work_plan_validation`
- `RunState.projections["search_work_plan_construction"]`

The projection owner is `RunKernel.SearchWorkPlan`. It records
`canonical_state: true`, `trace_only: false`, and `storage_only: false`.

The projection also preserves no-behavior-change flags:

- `search_work_plan_runtime_consumed: false`
- `runtime_consumed_by_query_plan: false`
- `provider_search_behavior_changed: false`
- `query_plan_behavior_changed: false`
- `prompt_behavior_changed: false`
- `final_answer_behavior_changed: false`

This makes the plan visible as canonical state without activating it as a
runtime consumer.

## 5. Observation payload contract

A `SEARCH_WORK_PLAN_CONSTRUCTED` observation must include a constructed
SearchWorkPlan projection in one of these shapes:

- top-level `search_work_plan_projection`; or
- `construction_result.search_work_plan`.

The observation may include validation at top-level `validation` or inside
`construction_result.validation`. RunKernel sanitizes the payload before storing
state and rejects observations that do not contain a SearchWorkPlan projection.

The projection summarizes at least construction identity, schema version,
planning posture, requested mode, effective contract, query shape, component
count, provider job count, quant work unit count, audit job count, stop
condition count, follow-up permission, validation status, and all no-behavior
flags.

## 6. Not runtime activation

This phase is not QueryPlan, search, provider, prompt, citation, or final-answer
activation. A reduced SearchWorkPlan does not:

- schedule QueryPlan admission;
- generate query text;
- choose query order;
- select providers;
- alter provider depth;
- run retrieval;
- satisfy source obligations;
- authorize follow-up search;
- decide final sufficiency;
- change citations or final prose;
- execute QuantWorkUnit calculations;
- activate Balanced or Deep loops.

Any future runtime consumer must be opened by a later scoped phase.

## 7. No-production-consumer boundary

Static tests assert that these production modules do not import
`core.search_work_plan_construction` or call
`observe_search_work_plan_construction`:

- `core/pipeline_orchestrator.py`
- `core/query_plan.py`
- `core/query_plan_runtime_adapter.py`
- `core/query_production_runtime.py`
- `core/mode_policy.py`

Static tests also assert that `core/run_kernel.py` does not import
`core.search_work_plan_construction.py`, and that the construction module does
not import provider/search/retrieval/prompt/QueryPlan/orchestrator surfaces or
call provider/model/fetch functions.

## 8. Authority semantics

RunKernel / RunAuthority owns the construction authorization. SearchWorkPlan is
canonical state after reduction, not trace-only or storage-only. SearchJudgment
remains the search, follow-up, source-gap, and recovery judgment surface.
SufficiencyJudgment remains the final-readiness and insufficiency surface.

Bounded executors cannot authorize follow-up. QueryPlan does not become source
obligation, provider/depth, final sufficiency, or citation authority.
Official/current remains a source obligation and evidence custody requirement,
not a provider hierarchy shortcut.

## 9. Examples covered by tests

The AG-96C7 tests cover:

- authorization and reduction after a RunAuthority contract;
- rejection before a reduced contract exists;
- observation type and stage mismatch rejection;
- rejection when the observation lacks a SearchWorkPlan projection;
- no QueryPlan, query production, retrieval, or provider behavior activation;
- sensitive projection redaction;
- no production consumer imports or calls;
- construction module closed-surface import and call guards;
- continued compatibility with AG-96C6 passive adapter tests.

## 10. Non-goals

AG-96C7 does not change QueryPlan behavior, query generation, query admission or
ordering, provider/search/ranking/filtering/retrieval behavior, prompt behavior,
mode policy, Author/Analyst/Economist/Scrutineer behavior, final answer or
citation behavior, QuantWorkUnit execution, Balanced/Deep loop activation,
official-source validation, social-signal runtime behavior, live calls, or
`core/pipeline_orchestrator.py`.

## 11. Recommended next phase

AG-96C8 should likely be either a behavior-preserving SearchWorkPlan runtime
construction callsite/projection path or a QueryPlan shadow relationship
design/adapter, depending on what AG-96C7 review exposes. Provider/search
behavior should remain closed until a later phase explicitly opens it.

AG-96C8 follow-up note:
`AG96C8_RUNTIME_SHADOW_SEARCHWORKPLAN_CALLSITE.md` wires the behavior-preserving
runtime shadow construction callsite after RunAuthority contract synthesis and
keeps QueryPlan, provider/search, prompt, citation, and final-answer behavior
closed.
