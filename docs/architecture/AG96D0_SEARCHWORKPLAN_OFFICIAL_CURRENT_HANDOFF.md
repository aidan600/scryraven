# AG-96D0 SearchWorkPlan Official/Current Handoff

## Status

AG-96D0 adds a shared official/current acquisition handoff at
`core/search_work_official_current_handoff.py`.

The handoff consumes AG-96C10 `search_work_shadow_lane_projection` packets or
AG-96C9 `query_plan_work_shadow_projection` packets and exposes official/current
acquisition needs as source-obligation-driven work. It is JSON-safe and
execution-free.

## Why This Replaces Mode-Specific Official Repair

The durable need is not "Fast mode needs a special official repair seam." The
durable need is that SearchWorkPlan-visible source obligations can say required
official/current, legal/current-primary, canonical-documentation, or
source-bound numeric evidence is still missing.

AG-96D0 starts moving that durable role to the mode-neutral SearchWork shadow
lane. Fast-specific official acquisition remains compatible for now, but its
future demotion path is to become a legacy executor/recovery path that consumes
source-obligation handoff state instead of owning the need.

## Source Obligation, Not Provider Shortcut

Official/current remains a source obligation and evidence custody requirement.
The handoff may expose:

- component IDs;
- source obligation IDs;
- strictness;
- required source classes;
- provider-job kinds as hints only;
- stop/fail/qualify posture if obligations remain unsatisfied;
- a bounded source-class recovery-compatible recommendation.

It may not select a provider, generate query text, choose search depth, execute
search or retrieval, bypass SearchJudgment or SufficiencyJudgment, or change
final-answer/citation behavior.

## Active Now

The new builder marks:

- `source_obligation_driven: true`;
- `mode_specific_official_executor: false`;
- `provider_selected: false`;
- `query_text_generated: false`;
- `search_executed: false`;
- `retrieval_executed: false`;
- `final_answer_behavior_changed: false`.

It maps visible SearchWork needs into existing recovery/source-class vocabulary:

- `official_current` -> `official_current_rules`;
- `legal_current_primary` -> `legal_or_regulatory_text` and
  `current_primary_or_official`;
- `canonical_documentation` -> `primary_source_documents`;
- `source_bound_numeric` -> `sourced_numeric_values`.

The embedded recommendation contains no recovery queries. Provider-job kinds are
only job hints from SearchWorkPlan shadow state.

## Deferred

Deferred phases must separately license any runtime consumption that would:

- execute provider/search/retrieval calls;
- generate or mutate executable query text;
- change QueryPlan admission, ordering, or depth;
- change provider routing;
- change prompts;
- change final-answer or citation behavior;
- delete or rewrite the old Fast official lane.

## Existing Recovery Machinery Stays Subordinate

Existing source-class recovery and official bridge blockers remain authoritative.
When blockers are supplied, the handoff still exposes missing source obligations
but marks recovery escalation as blocked and the embedded recovery recommendation
as not recommended.

Lower-tier, secondary, community, social, or aggregate bridge material cannot
satisfy required official/current obligations in this handoff. Such material can
be recorded only as rejected diagnostic context.

## Provider/Search Execution Remains Closed

AG-96D0 is a projection and handoff phase. It adds no orchestrator planning
logic, no provider role, no official executor, no search depth change, no query
generation, and no live validation. Provider/search/retrieval/prompt/final-answer
modules do not import the handoff.
