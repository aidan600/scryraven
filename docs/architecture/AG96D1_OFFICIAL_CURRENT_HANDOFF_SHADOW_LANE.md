# AG-96D1 Official/Current Handoff Shadow Lane

## Status

AG-96D1 wires the AG-96D0 official/current acquisition handoff into the
consolidated AG-96C10 SearchWork shadow lane.

The runtime lane now derives:

```text
SearchWorkPlan shadow projection
-> QueryPlan-work shadow projection
-> search_work_official_current_handoff
```

The handoff is stored inside the lane projection only. It remains
source-obligation-driven, JSON-safe, and execution-free.

## Active Projection

`run_search_work_shadow_lane(...)` now includes:

- `search_work_official_current_handoff`;
- `search_work_official_current_handoff_present`;
- `official_current_handoff_need_counts`;
- flags showing source-obligation-driven handoff and no mode-specific official
  executor;
- flags showing no provider selection, query-text generation, search execution,
  retrieval execution, or final-answer behavior change.

The existing `search_work_plan_projection` and
`query_plan_work_shadow_projection` are preserved.

## Behavior Boundary

AG-96D1 does not:

- execute source-class recovery;
- generate query text;
- admit or reorder QueryPlan entries;
- select providers;
- change provider routing or search depth;
- execute search or retrieval;
- change prompts;
- change citations or final-answer behavior;
- change `mode_policy.py`;
- alter the old Fast official lane.

`pipeline_orchestrator.py` still has one pass-through call to
`run_search_work_shadow_lane(...)` and no local official/current planning logic.

## Recovery And Fast Lane Compatibility

Existing recovery blockers and the old Fast official lane remain compatibility
surfaces. The lane exposes a handoff that existing recovery/source-class
vocabulary can understand, but it does not consume that recommendation or grant
recovery execution authority.

Future phases must separately license any consumer that acts on this handoff.
The intended future direction remains demotion of mode-specific official repair
into a source-obligation-driven recovery consumer, not restoration of a
mode-specific official executor.

## Redaction

The lane keeps raw/private fields out of the combined projection, including raw
prompts, raw provider payloads, raw model responses, secrets, tokens, DB rows,
and full traces.
