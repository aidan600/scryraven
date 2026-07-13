Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG91I_QUERY_PRODUCTION_EXECUTOR_UNDER_RUNKERNEL).

# AG-91I Query Production Executor under RunKernel

Status: implementation complete; behavior-preserving; no live validation.

## Purpose

AG-91I moves initial pre-retrieval query production behind the AG-91H RunKernel
spine. The orchestrator remains a compatibility shell, but it no longer owns
initial route-posture overrides, recon candidate production, researcher fallback
candidate production, canonical-subject/entity mutation, or candidate-source
selection before QueryPlan admission.

## Runtime Model

`RunKernel.authorize_query_production(...)` emits
`ActionType.QUERY_PRODUCTION` before recon/researcher candidate-generation
behavior runs. `core.query_production_runtime.execute_query_production_action`
requires that authorized action, executes the old bounded candidate-production
behavior, and returns `ObservationType.QUERY_CANDIDATES_PRODUCED`.

The observation reduces into `RunState.projections["query_production"]` with:

- effective route posture: intent, report type, query type, image mode, core
  topic, primary entity, entity list, academic/news overrides, nutrition
  override status, complexity, query/result budgets, search depth, top chunks,
  and max iterations;
- candidate source: `recon`, `researcher`, or `fallback`;
- compact candidate query projection;
- recon fired/skipped status and confidence;
- canonical subject and entity-update projection;
- researcher fallback status;
- compact diagnostics/provenance without raw prompts, raw model responses, raw
  provider payloads, secrets, DB rows, caches, private logs, or output packets.

`pipeline_orchestrator.py` reduces the query-production observation before
authorizing QueryPlan admission. QueryPlan admission consumes the reduced
projection through
`query_plan_admission_inputs_from_query_production_projection(...)`, not stale
or scattered orchestrator-local candidate lists.

## Moved Authority

Old owner: `core/pipeline_orchestrator.py` inline pre-retrieval block.

New action: `ActionType.QUERY_PRODUCTION`.

Executor: `core.query_production_runtime.execute_query_production_action`.

Observation: `ObservationType.QUERY_CANDIDATES_PRODUCED`.

Reducer/state update: `RunKernel.reduce(...)` stores the compact projection at
`RunState.projections["query_production"]`.

Runtime consumer: `execute_query_plan_admission_action(...)` receives candidate
queries, candidate source, max query budget, query type, and effective route
posture from the reduced query-production projection. QueryPlan still finalizes,
deduplicates, applies official/recency behavior, orders, and records execution
queries.

## Behavior Preservation

The executor mechanically preserves:

- nutrition lookup route override;
- focus-academic and force-news route overrides;
- news preferred-domain augmentation;
- Fast/Balanced/Deep complexity and budget selection;
- Balanced anchor packet creation and researcher anchor context formatting;
- recon eligibility, well-scoped skip, Brave API-key availability skip, Brave
  call shape, provider diagnostics, recon context extraction, recon rewriter
  prompt/model kwargs, canonical subject handling, and recon skip diagnostics;
- researcher prompt bytes, model kwargs, JSON parsing, and fallback to
  `core_topic[:300]` when researcher output is empty or invalid;
- candidate order as handed to QueryPlan.

The candidate source now distinguishes fallback observations as `fallback`.
Fallback candidates are still admitted through the existing researcher
QueryPlan path so final query identity/order behavior remains QueryPlan-owned.

## Closed Surfaces

This phase did not intentionally change prompt text, router behavior,
provider/depth policy, retrieval execution, ranking/filtering, recency behavior,
source-class recovery query ownership, evidence custody, final evidence,
citations, Author behavior, persistence/cache behavior, ProjectSource behavior,
or live provider/model/search behavior.

No live validation was run.

## Old Path Retirement

The initial orchestrator-local recon/researcher candidate-production path is
deleted from `pipeline_orchestrator.py`. The orchestrator now authorizes the
query-production action, calls the bounded executor, reduces the observation,
and assigns compatibility locals from the executor result for downstream legacy
consumers.

Remaining orchestrator-owned surfaces include title generation, lifecycle flow,
policy loading, retrieval loop coordination, continuation/recovery branches,
evidence selection, final answer assembly, persistence, and Author execution.
Those surfaces are outside AG-91I and remain deletion targets for later
RunKernel/EvidenceLedger/FinalAnswerPacket phases.

## Tests and Static Guards

`tests/test_query_production_ag91i.py` proves:

- RunKernel emits query-production actions;
- the executor rejects missing or wrong actions;
- query-production observations reduce into RunState;
- QueryPlan admission consumes the reduced projection;
- researcher and recon rewriter prompt bytes and ask-model kwargs are preserved;
- Brave recon call shape and success/failure diagnostics are preserved without
  live calls;
- nutrition/focus/news overrides appear in effective route posture before
  QueryPlan admission;
- QueryPlan remains query order owner;
- stale local candidate lists cannot bypass QueryPlan-admitted current queries;
- raw prompts, raw model responses, raw provider payloads, and secrets are not
  stored in RunState.

Existing AG-91H, QueryPlan, and router-query-preparation static guards were
updated to require the RunKernel query-production action path and to reject the
retired orchestrator-local prompt/search callsites.

## Recommended Next Phase

AG-91J - EvidenceLedger / Source Custody under RunKernel.
