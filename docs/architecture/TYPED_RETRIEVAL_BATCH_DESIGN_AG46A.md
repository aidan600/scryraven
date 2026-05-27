# AG-46A Typed Retrieval Batch Design

## Status

Design only. This phase does not implement runtime behavior.

AG-46A defines what the controller would be authorizing when the active
checkpoint action is `retrieve_targeted`: one bounded controller-owned
retrieval action that may carry multiple typed retrieval lanes in its plan,
without creating orphan dispatch paths, provider roles, new query generation,
or a targeted retrieval executor.

This document does not change `controller_loop_spine.py`,
`pipeline_orchestrator.py`, `ordinary_continuation_spine_gate.py`, provider
selection, routing, search depth, prompts, persistence, handoffs, final answer
behavior, legal/current-primary source repair, social runtime integration,
Scrutineer integration, or live-call behavior.

## 1. Problem Statement

`retrieve_targeted` is no longer a purely abstract controller action. The
controller spine can now actively authorize bounded ordinary continuation
queries from evaluator, expander, and scout lanes when the checkpoint selects
`retrieve_targeted` and the targeted retrieval lifecycle is eligible.

The remaining design gap is that `retrieve_targeted` still names a broad
retrieval action. It does not yet describe the typed contents of the retrieval
work being authorized. Without that shape, a future broad promotion could blur
ordinary continuation, source-class recovery, weak-corpus recovery, conflict
resolution, social side packets, legal/current repair, or provider/depth policy
into one generic retrieval path.

AG-46A resolves the shape question only. It defines a controller-owned
`RetrievalBatch` and typed `RetrievalBatchLane` representation. The batch is a
future authorization object, not an executor.

## 2. Current Post-AG-45C State

The active controller loop has one evidence-integration checkpoint decision and
at most one promoted action.

Currently promoted or actively authorized actions:

- `stop_sufficient`
- `stop_insufficient_with_caveat`
- `recover_missing_source_class`
- `recover_weak_corpus`
- `resolve_conflict`, when real conflict facts and resolving queries exist
- bounded evaluator ordinary continuation through `retrieve_targeted`
- bounded expander ordinary continuation through `retrieve_targeted`
- bounded scout ordinary continuation through `retrieve_targeted`

Ordinary continuation lanes now pass through
`core/ordinary_continuation_spine_gate.py` before scheduling:

- evaluator `new_queries` are represented as `evaluator_next_queries`
- expander `component_queries` are represented as
  `expander_component_queries`
- scout `directed_queries` are represented as `scout_directed_queries`

The active spine authorizes bounded ordinary continuation only when:

- checkpoint action is `retrieve_targeted`;
- targeted retrieval lifecycle is eligible;
- no terminal stop blocks the path;
- the ordinary continuation candidate is one of the bounded evaluator,
  expander, or scout source paths;
- ordinary next queries are non-empty;
- conflict resolving queries are empty for the ordinary lane.

Even then, the trace preserves that no targeted executor exists:
`targeted_retrieval_executor_dispatched` remains `false`.

## 3. Why Broad Retrieve Targeted Promotion Is Not Ready

Broad `retrieve_targeted` promotion is not ready without a batch shape because
the action name alone cannot answer these questions:

- Which typed query lane is authorized?
- Which lane generated or owns the query text?
- Which evidence obligation does the lane address?
- Which higher-priority recovery or resolution lane blocked ordinary
  continuation?
- Whether multiple candidate lanes are alternatives, blockers, or planned
  contents of one action?
- Whether ordinary next queries are being kept separate from conflict resolving
  queries?
- Whether provider policy and search depth are being reused rather than
  changed by the controller?

Promoting broad `retrieve_targeted` first would risk two unsafe outcomes:

- multiple retrieval paths could appear to be independently authorized after
  one checkpoint decision;
- a generic executor/provider role could be inferred before the controller has
  defined the typed evidence obligations it is authorizing.

The batch shape prevents those errors by making `retrieve_targeted` one
controller-owned action whose typed lanes are contents of the same action, not
separate dispatch owners.

## 4. Proposed Typed Retrieval Batch Object

`RetrievalBatch` is the future controller authorization packet for one bounded
retrieval action.

Recommended shape:

```yaml
RetrievalBatch:
  batch_id: string
  action_name: retrieve_targeted
  batch_reason: string
  checkpoint_action_name: string
  authorized_action_name: string | null
  batch_status: planned | authorized | blocked | consumed | skipped
  batch_blockers: list[string]
  lanes: list[RetrievalBatchLane]
  constraints:
    one_checkpoint_decision: true
    one_promoted_action_at_most: true
    one_dispatch_owner: controller_loop_spine
    terminal_stops_before_bounded_retrieval: true
    lifecycle_blockers_authoritative: true
    no_provider_policy_change: true
    no_depth_policy_change: true
    no_query_generation: true
    no_prompt_change: true
    no_targeted_executor: true
    no_retrieve_targeted_provider_role: true
  authorization:
    authorized_by: controller_loop_spine
    checkpoint_decision_count: 1
    promoted_action_name: retrieve_targeted | null
    executor_dispatched: false
    dispatch_authorized: boolean
    allowed_lane_ids: list[string]
    blocked_lane_ids: list[string]
  trace:
    ordinary_continuation_candidate_trace_key: ordinary_continuation_candidate
    targeted_lifecycle_trace_keys: list[string]
    source_class_lifecycle_trace_key: string | null
    weak_corpus_lifecycle_trace_key: string | null
    conflict_lifecycle_trace_key: string | null
  handoff_summary:
    action_name: retrieve_targeted
    approved_query_count: integer
    lane_types: list[string]
    evidence_obligations: list[string]
    provider_policy: reuse_existing
    depth_policy: reuse_existing
```

The controller authorizes the batch as one action. Lanes inside the batch are
not actions. A batch may contain several typed lanes in future planning traces,
but only the controller spine may mark the batch authorized, and only a future
bounded executor contract may consume it.

For AG-46A, this object is documentation only. No runtime dataclass is added.

## 5. Proposed Typed Lane Object

`RetrievalBatchLane` represents one typed query source and evidence obligation
inside a `RetrievalBatch`.

Recommended shape:

```yaml
RetrievalBatchLane:
  lane_id: string
  lane_type: string
  lane_source: string
  query_provenance: string
  query_generation_owner: evaluator | expander | scout | source_class_controller | weak_corpus_controller | conflict_controller | future_adapter
  approved_queries: list[string]
  prior_queries: list[string]
  conflict_resolving_queries: list[string]
  contract_gap_addressed: string | null
  evidence_obligation: string
  source_class_obligations: list[string]
  currentness_obligations: list[string]
  provider_policy: reuse_existing | blocked_if_change_required
  depth_policy: reuse_existing | blocked_if_change_required
  status: candidate | authorized | blocked | future_non_authorized | consumed | skipped
  blockers: list[string]
  used: boolean
  trace_visibility:
    sanitized_queries: true
    raw_prompt: false
    raw_provider_payload: false
    private_runtime_state: false
```

Lane fields preserve three separate responsibilities:

- query provenance: where the query came from;
- query ownership: which upstream component produced or owns the query text;
- evidence obligation: what gap or recovery need the lane is meant to satisfy.

The lane object must never become a provider request, routing directive, depth
directive, prompt instruction, persistence record, or final-answer handoff by
itself.

## 6. Lane Taxonomy And Authorization Status

Required lane taxonomy:

| Lane type | Current status | Relationship to batch |
| --- | --- | --- |
| `ordinary_evaluator_gap_queries` | Currently bounded-spine authorized when checkpoint selects `retrieve_targeted` and lifecycle is eligible | Ordinary continuation lane sourced from evaluator `new_queries`; query provenance remains `evaluator_next_queries`. |
| `ordinary_expander_component_queries` | Currently bounded-spine authorized when checkpoint selects `retrieve_targeted` and lifecycle is eligible | Ordinary continuation lane sourced from expander `component_queries`; query provenance remains `expander_component_queries`. |
| `ordinary_scout_directed_queries` | Currently bounded-spine authorized when checkpoint selects `retrieve_targeted` and lifecycle is eligible | Ordinary continuation lane sourced from scout `directed_queries`; query provenance remains `scout_directed_queries`. |
| `source_class_recovery_queries` | Current separate promoted action, not ordinary retrieval | Future batch-plan representation may list it as a higher-priority recovery lane, but current action identity remains `recover_missing_source_class`. |
| `weak_corpus_recovery_queries` | Current separate promoted action, not ordinary retrieval | Future batch-plan representation may list it as a higher-priority recovery lane only if weak-corpus action identity and precedence remain intact. |
| `conflict_resolving_queries` | Current separate promoted action, not ordinary retrieval | Future batch-plan representation may list it as a higher-priority resolution lane; ordinary next queries must never populate this field. |
| `future_social_signal_queries` / `social_signal_lane` | Future, non-authorized | May appear only as a blocked or future side-packet lane. It is not ordinary evidence and not runtime-integrated. |
| `future_legal_current_primary_adapter_lane` | Future, non-authorized | May appear only as a blocked future adapter lane. It must not repair legal/current-primary source acquisition in this phase. |

Ordinary continuation lanes are:

- `ordinary_evaluator_gap_queries`
- `ordinary_expander_component_queries`
- `ordinary_scout_directed_queries`

Higher-priority recovery or resolution lanes are:

- `source_class_recovery_queries`
- `weak_corpus_recovery_queries`
- `conflict_resolving_queries`

Future non-authorized lanes are:

- `future_social_signal_queries` / `social_signal_lane`
- `future_legal_current_primary_adapter_lane`

## 7. Precedence And Blocking Model

The batch model preserves current checkpoint precedence. A batch does not allow
ordinary continuation to outrank terminal, recovery, or resolution actions.

Precedence:

1. Terminal stops win before bounded retrieval:
   `stop_sufficient` and `stop_insufficient_with_caveat`.
2. Source-class recovery wins before ordinary continuation when checkpoint
   promoted and lifecycle-authorized.
3. Weak-corpus recovery wins before ordinary continuation when checkpoint
   promoted and lifecycle-authorized.
4. Conflict resolution wins before ordinary continuation when checkpoint
   promoted and lifecycle-authorized.
5. Ordinary evaluator/expander/scout continuation may be authorized only when
   no higher-priority action owns the checkpoint path.

Blocking rules:

- A blocked higher-priority lane may be visible in trace, but it must not
  authorize a substitute ordinary lane.
- An authorized ordinary lane must record blockers from source-class,
  weak-corpus, conflict, terminal, social, Scrutineer, clarification,
  provider-policy, depth-policy, currentness, and legal-source surfaces when
  any of those surfaces own the path.
- `ordinary_next_queries` remain separate from `conflict_resolving_queries`.
- Unapproved lanes do not dispatch substitutes.
- Multiple candidate lanes inside a future batch are contents of one
  controller action, not multiple promoted actions.

## 8. Trace And Handoff Representation

Trace should answer what the controller authorized without changing runtime
handoffs.

Batch trace should include:

- checkpoint action name;
- authorized action name;
- promoted action name;
- batch status and blockers;
- allowed and blocked lane IDs;
- lane type, source, provenance, approved query count, and blockers;
- lifecycle reason for every blocked lane;
- `executor_dispatched=false` until a later executor phase exists;
- `targeted_retrieval_executor_dispatched=false`;
- `used=false` until a later executor consumes the batch.

Handoff summary should remain compact and sanitized:

- no raw prompts;
- no raw provider payloads;
- no private runtime state;
- no Analyst/Economist/Author handoff schema change;
- no final-answer content change.

Future handoff exposure, if any, should be a summary reference to the
controller-authorized retrieval action, not a new downstream contract.

## 9. Provider, Depth, And Query Generation Boundaries

The typed retrieval batch is dispatch authorization only.

It may record:

- provider policy is reusable;
- depth policy is reusable;
- query generation is complete before authorization;
- approved queries came from an allowed provenance;
- a lane is blocked because provider, depth, or query-generation changes would
  be required.

It must not:

- select providers;
- create a `retrieve_targeted` provider role;
- change provider routing;
- change search depth;
- generate new queries;
- modify prompts;
- alter source filters or domain policy;
- repair legal/current-primary source acquisition.

If a future implementation requires any of those changes, it must stop rather
than implement the batch.

## 10. Relationship To Economist And Scout

Scout is a typed directed retrieval lane. Its current purpose is to support
Economist or quantitative disambiguation by producing directed queries that can
clarify evidence requirements.

Scout is not a special Economist bypass. It is not a separate dispatch owner.
It does not get its own provider authority inside the batch.

In a future batch, ordinary evaluator, expander, and scout lanes may be listed
under the same controller-authorized `retrieve_targeted` action. The scout lane
would remain:

- `lane_type: ordinary_scout_directed_queries`
- `lane_source: scout`
- `query_provenance: scout_directed_queries`
- `query_generation_owner: scout`
- `provider_policy: reuse_existing`
- `depth_policy: reuse_existing`

AG-46A does not implement multi-lane execution, parallel execution, or
Economist-specific dispatch behavior.

## 11. Relationship To Source-Class Recovery

Source-class recovery is currently a separate promoted action:
`recover_missing_source_class`.

The batch design may represent source-class recovery as a higher-priority lane
in future planning traces, but it must preserve:

- current action identity;
- source-class lifecycle blockers;
- source-class executor authorization;
- precedence before ordinary continuation;
- source-class query ownership;
- source-class source obligations.

An ordinary `retrieve_targeted` lane must be blocked when source-class recovery
owns the path. It must not consume source-class recovery queries or relabel
missing source-class work as ordinary retrieval.

## 12. Relationship To Conflict Resolution

Conflict resolution is currently a separate promoted action:
`resolve_conflict`.

Conflict lanes may appear in future batch planning only as higher-priority
resolution lanes. They must preserve:

- current action identity;
- conflict lifecycle blockers;
- conflict executor authorization;
- precedence before ordinary continuation;
- `conflict_resolving_queries` as a separate field;
- no copying from ordinary `next_queries`.

If real conflict facts and resolving queries exist, ordinary continuation is
blocked. A future batch may show that blocking relationship, but it must not
collapse conflict resolution into ordinary `retrieve_targeted`.

## 13. Non-Goals

AG-46A does not do any of the following:

- runtime behavior changes;
- new core dataclasses;
- `controller_loop_spine` behavior changes;
- `pipeline_orchestrator` behavior changes;
- `ordinary_continuation_spine_gate` behavior changes;
- broad `retrieve_targeted` promotion;
- targeted executor creation;
- `retrieve_targeted` provider role creation;
- provider changes;
- routing changes;
- search-depth changes;
- query-generation changes;
- prompt changes;
- persistence changes;
- final-answer changes;
- Analyst/Economist/Author handoff changes;
- social runtime integration;
- Scrutineer runtime integration;
- legal/current-primary repair;
- live calls;
- multi-lane, parallel, or concurrent retrieval execution.

## 14. Stop Conditions For Future Implementation

Stop instead of implementing if a future batch phase requires:

- provider/routing/depth/prompt changes;
- query-generation changes;
- a new targeted executor before an executor contract phase;
- a `retrieve_targeted` provider role;
- runtime dispatch changes outside the scoped phase;
- broad fact-assembly extraction;
- legal/current-source repair;
- social or Scrutineer integration;
- Analyst/Economist/Author handoff changes;
- merging ordinary next queries with conflict resolving queries;
- changing evaluator, expander, or scout continuation semantics;
- implementing multi-lane, parallel, or concurrent retrieval execution.

## 15. Minimal Next Implementation Candidates

Minimal future candidates after this design:

1. Add a pure `RetrievalBatch` trace builder that consumes existing sanitized
   spine, lifecycle, and ordinary candidate traces without changing runtime
   behavior.
2. Add unit tests proving lane taxonomy, precedence, and no-provider/no-depth
   boundaries in pure code.
3. Extend spine trace representation to include an optional batch summary only
   when the checkpoint action is `retrieve_targeted`, while preserving the
   current executor behavior.
4. In a later and separate phase, define a bounded executor contract that can
   consume one authorized batch without selecting providers, changing depth,
   generating queries, or introducing a `retrieve_targeted` provider role.
5. Only after the executor contract exists, consider orchestrator inversion so
   evaluator, expander, and scout produce candidate lanes but do not independently
   advance retrieval.

The first implementation candidate should remain pure and trace-only. Active
multi-lane execution is intentionally out of scope.
