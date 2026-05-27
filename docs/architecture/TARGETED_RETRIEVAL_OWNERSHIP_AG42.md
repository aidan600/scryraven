# AG-42 Targeted Retrieval Ownership Design

## Status

Design only. This note does not implement runtime behavior.

AG-42 defines how `controller_loop_spine` should eventually own ordinary
targeted retrieval continuation without reintroducing generic orchestrator
continuation as a competing dispatch authority.

This phase does not change providers, routing, search depth, query generation,
prompts, persistence, handoffs, Scrutineer policy, social signal behavior,
legal-source behavior, source-class recovery, weak-corpus recovery,
conflict-state production, final answer generation, or evidence visibility.

Known side track: official/legal/current-primary source acquisition and citation
survival remain incomplete. CTA/OSHA-style legal source failures are not
controller ownership regressions for AG-42.

## 1. Diagnosis

`retrieve_targeted` exists in the controller vocabulary but is not an active
runtime action.

Current state:

- `AnswerControllerActionName.RETRIEVE_TARGETED` exists in the pure answer
  contract controller.
- `RetrievalStopDecision.CONTINUE_RETRIEVAL` maps to `retrieve_targeted` in
  action envelopes and answer-contract action history.
- `EvidenceIntegrationSnapshot` has targeted-retrieval facts:
  `next_queries_available`, `next_query_redundant`, `prior_query_count`, and
  `next_query_count`.
- `decide_evidence_integration_checkpoint` can recommend `retrieve_targeted`
  when a material gap remains, non-redundant next queries exist, and targeted
  budget remains.
- `controller_loop_spine` intentionally does not authorize
  `retrieve_targeted`; tests assert unpromoted actions do not dispatch
  substitute executors.
- Ordinary continuation still happens inside `pipeline_orchestrator.py` through
  scout, expander, evaluator, redundancy checks, and loop/budget control.

Therefore the missing boundary is not "can the controller name the action?" It
can. The missing boundary is "can the controller be the only active owner of
the next ordinary retrieval dispatch?"

AG-42 should not promote runtime behavior yet. Promotion is not ready while the
orchestrator retrieval loop can still independently set `current_queries`,
increment `iteration`, and continue after a non-terminal post-evidence
decision.

## 2. Current Targeted/Ordinary Continuation Data-Flow Map

Current ordinary continuation flow:

```text
router/recon/researcher query planning
        |
        v
initial current_queries
        |
        v
main retrieval loop in pipeline_orchestrator
        |
        +--> pre-search redundancy stop
        |
        +--> process_search_queries(...)
        |
        +--> first-pass disambiguation retry
        |
        +--> weak-corpus recovery branch
        |
        +--> scout-directed continuation
        |
        +--> expander component queries
        |
        +--> evaluator new_queries / sufficient / no-query / redundant / budget stop
        |
        v
retrieval_stop_shadow / limited active terminal-stop telemetry
        |
        v
runtime answer-contract handoff
        |
        v
evidence-integration checkpoint
        |
        v
controller_loop_spine
        |
        +--> active source-class recovery executor, if authorized
        +--> active conflict-resolution executor, if authorized
        +--> active terminal stop posture
        +--> no retrieve_targeted dispatch today
```

Mapped sources:

| Path | Query source | Current owner | Runtime effect today |
| --- | --- | --- | --- |
| Evaluator `new_queries` | Model evaluator output, then finalized/anchored | Orchestrator | Updates `current_queries`, records retrieval-stop shadow, continues loop if budget remains |
| Scout-directed continuation | `SCOUT_REGISTRY` prompt output `directed_queries` | Orchestrator plus scout prompt | Updates `current_queries`, may force component providers, continues loop |
| Expander component queries | Expander prompt JSON `component_queries` | Orchestrator plus expander prompt | Updates `current_queries`, may force component providers, continues loop |
| Pre-search redundancy stop | Jaccard between pass 1 and next pass | Orchestrator with retrieval-stop shadow mirror | Breaks loop before duplicate pass |
| Evaluator redundancy stop | Jaccard between pass 1 and evaluator queries | Orchestrator with retrieval-stop shadow mirror | Sets sufficient posture and stops continuation |
| No-query stop | Evaluator produced no next queries while insufficient | Orchestrator plus active retrieval-stop terminal telemetry | Stops continuation with caveat posture |
| Budget stop | `iteration >= max_iterations` | Orchestrator plus active retrieval-stop terminal telemetry | Stops continuation with caveat posture |
| Answer-contract `next_queries` | Adapted from pipeline facts / retrieval-stop decisions | Passive answer-contract controller | Represents future targeted action, but does not dispatch |
| Checkpoint `retrieve_targeted` | Derived from `next_queries_available` and budget facts | Checkpoint recommendation only | Explicitly unpromoted by spine |

## 3. Existing Candidate Sources For Targeted Retrieval Authority

Safe candidate inputs already exist:

- `RetrievalStopDecision` from `core/retrieval_stop_controller.py`.
- `EvidenceStateSummary.next_queries`, `prior_queries`, and
  `next_query_redundant` in the answer-contract state.
- `EvidenceIntegrationSnapshot.targeted_retrieval` facts.
- `EvidenceIntegrationBudgetSnapshot.remaining_for_action(RETRIEVE_TARGETED)`.
- `EvidenceIntegrationDecision` when the checkpoint recommends
  `retrieve_targeted`.
- `ControllerActionEnvelope` for retrieval-stop decisions, currently passive or
  shadow.
- `queries_by_iteration` and `disambiguation_queries_by_iteration` as sanitized
  prior-query facts.
- `retrieval_stop_shadow_telemetry` and limited active terminal-stop telemetry.

Candidate sources that should not become AG-42 authority:

- Raw evaluator, scout, or expander prompt text.
- Raw provider payloads, logs, DB rows, caches, private packets, or generated
  traces.
- Final answer text.
- Ordinary `next_queries` treated as conflict `resolving_queries`.
- Source-class missing facts treated as ordinary targeted retrieval when
  source-class recovery is eligible.
- Legal-source repair heuristics.

## 4. Proposed TargetedRetrievalLifecycle / Candidate Shape

`TargetedRetrievalCandidate` should be a compact sanitized object produced from
already-computed continuation facts. It should not generate queries.

Recommended shape:

```python
@dataclass(frozen=True)
class TargetedRetrievalCandidate:
    contract_gap_addressed: str | None
    approved_queries: tuple[str, ...]
    query_provenance: str
    query_generation_owner: str
    prior_queries: tuple[str, ...]
    prior_query_overlap_score: float | None
    redundancy_status: str
    iteration: int
    max_iterations: int
    targeted_budget_remaining: int
    expected_value: str
    evidence_boundary: str
    source_class_blockers: tuple[str, ...]
    weak_corpus_blockers: tuple[str, ...]
    conflict_blockers: tuple[str, ...]
    provider_policy_reusable: bool
    provider_swap_required: bool
    search_depth_reusable: bool
    search_depth_escalation_required: bool
    legal_source_repair_required: bool
    lifecycle_phase: str
    metadata: dict[str, Any]
```

Recommended lifecycle:

```python
@dataclass(frozen=True)
class TargetedRetrievalLifecycle:
    considered: bool
    eligible: bool
    approved: bool
    used: bool
    reason: str | None
    skip_reason: str | None
    blockers: tuple[str, ...]
    candidate: TargetedRetrievalCandidate | None
    provider_role: str | None
    search_depth: str | None
    stage: str | None
    attempt_count: int
```

Stable blocker vocabulary:

- `no_material_contract_gap`
- `no_approved_queries`
- `redundant_with_prior_queries`
- `blocked_by_iteration_budget`
- `blocked_by_source_class_recovery`
- `blocked_by_weak_corpus_recovery`
- `blocked_by_conflict_resolution`
- `blocked_by_provider_policy_change_required`
- `blocked_by_search_depth_policy_change_required`
- `blocked_by_legal_source_repair_required`
- `blocked_by_wrong_phase`
- `already_attempted_for_gap`
- `query_generation_required`

Eligibility should require all of these:

- material contract gap remains;
- non-empty already-approved queries;
- query provenance is one of the allowed ordinary continuation sources;
- query generation is complete before the lifecycle is built;
- query is not redundant with prior queries;
- targeted budget remains;
- no higher-priority source-class, weak-corpus, conflict, terminal, social,
  Scrutineer, or clarification action owns the checkpoint decision;
- provider policy and search depth can be reused without changing routing;
- lifecycle is pre-Analyst / pre-Author;
- legal-source repair is not required.

The candidate should preserve query provenance but should not contain prompts or
raw model outputs. Example provenance values:

- `evaluator_next_queries`
- `scout_directed_queries`
- `expander_component_queries`
- `retrieval_stop_continue`
- `answer_contract_approved_targeted_queries`
- `fixture`

## 5. Boundary From Query Generation, Provider, And Depth Surfaces

Targeted retrieval ownership is dispatch ownership, not query-generation
ownership.

Allowed in AG-42 follow-up implementation:

- sanitize already-produced ordinary next queries;
- deduplicate and cap already-produced queries;
- compare against prior queries for redundancy;
- spend a controller-owned targeted-retrieval budget slot;
- expose approved queries to a bounded executor only when the spine authorizes
  `retrieve_targeted`;
- mark the retrieval pass with an ordinary targeted provider role such as
  `targeted_retrieval`, if and only if that is purely diagnostic and does not
  alter provider selection.

Protected surfaces:

- no prompt changes;
- no new query-generation prompt;
- no changes to scout, expander, evaluator, researcher, router, Analyst,
  Economist, Author, Scrutineer, or social prompts;
- no provider routing changes;
- no search-depth escalation;
- no provider swap;
- no domain filtering changes;
- no legal-source repair;
- no persistence changes;
- no final answer or evidence visibility changes.

If promotion requires changing query generation, stop. The prerequisite would
be a separate query-candidate production phase that emits sanitized
already-approved queries before the lifecycle runs.

If promotion requires provider routing or search-depth changes, stop.
Provider/depth neutrality is a hard eligibility condition, not something the
targeted lifecycle may solve.

## 6. Whether Implementation Is Ready

Not ready for runtime promotion.

Design is ready. A pure/offline candidate and lifecycle can be implemented in a
future phase, but active dispatch should wait until ordinary orchestrator
continuation is made subordinate to `controller_loop_spine`.

Promotion is blocked by these current facts:

- scout, expander, and evaluator branches still directly continue the runtime
  loop;
- `controller_loop_spine` does not recognize `retrieve_targeted` as an
  authorized dispatch;
- no targeted retrieval executor contract exists that can reuse current
  providers/depth while remaining subordinate to the spine;
- current retrieval-stop active behavior only owns terminal stop branches, not
  continue branches;
- checkpoint `retrieve_targeted` is a recommendation only, and tests currently
  assert it does not dispatch.

No legal-source repair is required before targeted retrieval ownership. Legal
repair should remain separate.

## 7. Recommended Implementation Phases

Phase 1 - pure candidate and lifecycle:

- Add `core/targeted_retrieval_controller.py` as pure/offline code.
- Build `TargetedRetrievalControllerInput`, `TargetedRetrievalDecision`, and
  lifecycle trace fields.
- Consume only already-computed next queries, prior queries, budget facts,
  blocker facts, phase facts, and provider/depth neutrality flags.
- Add static guards forbidding providers, prompts, routing, persistence, model
  calls, and orchestrator imports.

Phase 2 - checkpoint and spine representation:

- Extend `ControllerLoopSpineInput` with targeted lifecycle trace.
- Add `RETRIEVE_TARGETED` to spine authorization only after tests prove no
  substitute dispatch and no other active owner remains.
- Keep terminal stops and recovery/conflict lifecycle blockers authoritative.
- Add blocked/skipped trace fields for targeted retrieval.

Phase 3 - bounded executor contract:

- Introduce an executor wrapper that calls the existing search dispatch surface
  with approved queries, current providers, current search depth, current caps,
  and ordinary evidence eligibility.
- The executor must not select providers, choose depth, generate queries, alter
  domains, raise budget, or write prompts.

Phase 4 - orchestrator loop inversion:

- Remove direct continuation authority from scout, expander, and evaluator
  branches.
- Those branches may produce candidate queries, but they must not call
  `continue` or advance `iteration` unless the spine authorizes
  `retrieve_targeted`.
- Make ordinary continuation a single post-checkpoint dispatch branch.

Phase 5 - runtime parity and cleanup:

- Prove old ordinary continuation outcomes through the new action path in
  offline harnesses.
- Retire shadow-only `retrieve_targeted` parity assertions once active parity
  is proven.
- Keep legal-source repair out of scope.

## 8. Required Tests

Tests that prove real authority rather than telemetry:

- Unit: lifecycle approves non-redundant evaluator/scout/expander next queries
  only when material gap, budget, phase, and provider/depth neutrality are all
  satisfied.
- Unit: lifecycle blocks when query generation is required rather than already
  complete.
- Unit: lifecycle blocks provider swap, search-depth escalation, and legal-source
  repair requirements.
- Unit: lifecycle blocks when source-class recovery, weak-corpus recovery, or
  conflict resolution owns the path.
- Unit: ordinary next queries remain ordinary and never become conflict
  resolving queries.
- Spine: `retrieve_targeted` can be promoted only when checkpoint selects it and
  targeted lifecycle is eligible.
- Spine: terminal stops block `retrieve_targeted`.
- Spine: source-class, weak-corpus, and conflict actions remain mutually
  exclusive with `retrieve_targeted`.
- Spine: unapproved `retrieve_targeted` does not dispatch a source-class,
  weak-corpus, conflict, or generic fallback executor.
- Orchestrator static: no continuation branch dispatches search unless guarded
  by `authorized_spine_action == RETRIEVE_TARGETED`.
- Runtime harness: evaluator next queries produce exactly one targeted
  retrieval pass when authorized.
- Runtime harness: scout-directed and expander component queries become
  candidates, not direct dispatch owners.
- Runtime harness: redundancy and budget stops prevent targeted dispatch.
- Runtime harness: provider list and search depth match the reusable current
  policy and are not selected by the targeted controller.
- Regression: current source-class, weak-corpus, conflict, terminal stop, social,
  Scrutineer, handoff, and evidence visibility behavior remains unchanged.

## 9. Stop Conditions

Stop targeted retrieval promotion if any of these occurs:

- ownership requires provider routing changes;
- ownership requires search-depth changes;
- ownership requires prompt or query-generation changes;
- ordinary orchestrator continuation remains a competing active dispatch owner;
- `retrieve_targeted` cannot be cleanly distinguished from source-class
  recovery, weak-corpus recovery, or conflict resolution;
- ordinary `next_queries` must be treated as conflict `resolving_queries`;
- legal-source repair is required;
- lifecycle needs raw traces, raw logs, DB rows, provider payloads, caches,
  prompts, secrets, or private generated packets;
- final answer generation or evidence visibility must change.

## 10. Explicit Legal-Source Answer

Legal-source repair should not happen before targeted retrieval ownership.

They are separable. Targeted retrieval ownership can govern ordinary continuation
using already-approved ordinary next queries while preserving the existing
official/legal/current-primary source-class side track. Legal-source weaknesses
should block only attempts to solve legal repair inside targeted retrieval, not
the controller-loop consolidation itself.
