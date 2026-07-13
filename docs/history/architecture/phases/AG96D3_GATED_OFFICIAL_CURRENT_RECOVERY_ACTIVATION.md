Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96D3_GATED_OFFICIAL_CURRENT_RECOVERY_ACTIVATION).

# AG-96D3 Gated Official/Current Recovery Activation

## Status

AG-96D3 makes the SearchWork official/current recovery bridge visible to the
existing source-class recovery recommendation lifecycle.

This is a controlled behavior phase. It does not add a mode-specific official
executor, does not change Fast official lane runtime behavior, and does not
execute provider/search/retrieval work directly.

## D0 -> D1 -> D2 -> D3 Chain

AG-96D0 introduced `core/search_work_official_current_handoff.py`, a
source-obligation-driven handoff from QueryPlan-work shadow projection to
official/current, legal/current-primary, canonical-documentation, and
source-bound numeric recovery vocabulary.

AG-96D1 wired that handoff into the consolidated SearchWork shadow lane. The
lane stores `search_work_official_current_handoff` inside
`search_work_shadow_lane_projection` while keeping QueryPlan, provider/search,
retrieval, prompts, citations, and final answers unchanged.

AG-96D2 added `core/search_work_official_current_recovery_bridge.py`, a
recovery-compatible bridge result exposing missing expected source classes,
source-obligation-driven trigger fields, reason, blockers, and no-execution
flags. It remained projection-only.

AG-96D3 adds
`core/search_work_official_current_recovery_activation.py` and consumes it from
the existing authoritative-source action seam. The orchestrator adapter passes
the existing `run_kernel.state.projections["search_work_shadow_lane_projection"]`
as a fact; `pipeline_orchestrator.py` does not gain local official/current
planning logic.

## Activated Runtime Behavior

When the SearchWork lane exposes an official/current handoff and the bridge is
eligible, the activation helper merges bridge visibility into the existing
source-class recovery recommendation shape:

- missing expected source classes are appended;
- source-obligation trigger fields are appended;
- source-obligation-driven recommendation posture is marked when eligible;
- existing recommendation fields are preserved;
- existing `source_class_recovery_queries` are left unchanged.

Existing official/canonical query acquisition, execution admission, lifecycle,
and `SourceClassRecoveryRunner` remain the owners of query repair, admission,
dispatch, provider/search execution, and blocker enforcement.

## Blocker Behavior

Activation is allowed only when the bridge is present, bridge-eligible, missing
expected source classes exist, and no existing ownership blocker prevents the
recovery lifecycle from proceeding.

When blockers such as terminal stop, prior attempt, conflict-resolution
ownership, provider policy change, search-depth escalation, author/post-analyst
phase, or redundant-query posture are present, the helper preserves
missing-class visibility but does not turn on a SearchWork-driven recovery
recommendation. Those same ownership blockers are also passed to the older
official-source obligation bridge so it cannot re-promote an official/current
recommendation after the D3 gate declines activation.

## Execution Boundary

AG-96D3 does not:

- generate executable query text in the SearchWork bridge or activation helper;
- execute search, retrieval, provider calls, or model calls;
- alter QueryPlan admission, order, or production output;
- alter provider routing or search depth policy;
- alter prompts, final answers, citations, or Author behavior.

Provider/search execution remains owned by the existing recovery lifecycle:
official/canonical query acquisition may add queries only through its existing
repair path, execution admission decides whether the path is eligible, and the
source-class lifecycle/runner remain the dispatch boundary.

## Fast Official Lane

The Fast official lane remains compatibility/fallback. AG-96D3 does not import,
call, delete, or rewrite `core/fast_official_lane.py`, and it introduces no new
Fast-specific official executor.

Future demotion remains deferred until a later phase explicitly licenses
runtime retirement or subordination of the old Fast official lane.

## Deferred

Still deferred:

- provider-job execution redesign;
- QueryPlan consumption of SearchWork source-obligation work;
- provider routing and depth-policy changes;
- prompt changes;
- final-answer and citation behavior changes;
- live validation;
- Fast-lane runtime demotion or deletion.
