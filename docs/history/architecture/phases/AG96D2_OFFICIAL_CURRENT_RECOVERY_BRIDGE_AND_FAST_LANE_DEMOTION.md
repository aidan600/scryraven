Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96D2_OFFICIAL_CURRENT_RECOVERY_BRIDGE_AND_FAST_LANE_DEMOTION).

# AG-96D2 Official/Current Recovery Bridge And Fast Lane Demotion Prep

## Status

AG-96D2 adds
`core/search_work_official_current_recovery_bridge.py`, a pure compatibility
bridge from SearchWork official/current handoff projections to the bounded
source-class recovery vocabulary used by existing recovery surfaces.

The chain is now:

```text
AG-96D0 SearchWork official/current handoff
-> AG-96D1 lane-visible handoff projection
-> AG-96D2 recovery-compatible bridge result
```

## What The Bridge Does

The bridge accepts either the AG-96D1 lane projection or the AG-96D0 handoff
projection. It exposes missing expected source classes, source-obligation-driven
trigger fields, blocker state, and no-execution flags in a JSON-safe shape.

The bridge vocabulary is intentionally familiar to existing source-class
recovery consumers:

- `missing_expected_source_classes`;
- `source_class_recovery_recommended`;
- `source_class_recovery_shadow_mode`;
- `source_class_recovery_reason`;
- `source_class_recovery_trigger_fields`;
- `source_class_recovery_queries`;
- `source_class_recovery_query_count`.

The query fields remain empty. AG-96D2 does not create executable recovery
queries, select providers, choose depth, run search, run retrieval, or change
prompt, citation, or final-answer behavior.

## Blocker Authority

Existing blockers remain authoritative. If the caller supplies budget, terminal
stop, active recovery, provider policy, depth, query-generation, weak-corpus, or
other recovery-ownership blockers, the bridge still shows the missing
official/current classes but marks the bridge ineligible and does not recommend
recovery execution.

This keeps the bridge subordinate to the existing recovery lifecycle rather than
turning SearchWork visibility into an execution grant.

## Source Obligation Boundaries

Official/current, legal/current-primary, canonical documentation, and
source-bound numeric needs remain source obligations. Lower-tier, secondary,
community, social, or aggregate material can appear only as diagnostic rejected
material. It cannot satisfy required official/current obligations and cannot
bypass SearchJudgment or SufficiencyJudgment.

## Fast Official Lane Posture

The old Fast official lane remains runtime compatibility/fallback for now.
AG-96D2 does not delete, rewrite, import, or depend on
`core/fast_official_lane.py`, and it introduces no new Fast-specific official
executor.

The intended future posture is that durable official/current need belongs to
SearchWork source obligations and the handoff bridge. Fast-specific machinery
can later be demoted behind that source-obligation-owned need when a future
phase explicitly licenses runtime consumption and retirement.

## Deferred

Still deferred:

- provider/search activation;
- executable query text generation;
- QueryPlan admission, ordering, or depth consumption;
- provider routing changes;
- prompt changes;
- final-answer and citation behavior changes;
- live validation;
- deletion or runtime rewrite of the old Fast official lane.
