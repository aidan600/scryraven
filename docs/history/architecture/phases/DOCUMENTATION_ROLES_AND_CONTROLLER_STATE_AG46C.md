Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (DOCUMENTATION_ROLES_AND_CONTROLLER_STATE_AG46C).

# Documentation Roles And Controller State After AG-46C

## Status

Architecture hygiene note only. This document clarifies where different kinds
of ProPlex/FauxPlex documentation belong and summarizes the current controller
state after AG-46C.

It does not authorize runtime behavior changes, provider/routing/depth/query
changes, prompt changes, handoff changes, live validation, output packet
commits, or broad roadmap/status documents.

## 1. Documentation Layer Roles

Repo architecture docs under `docs/architecture/` record durable architecture
decisions, boundaries, invariants, diagnostic contracts, and phase outcomes
that future implementation phases must preserve.

Repo validation docs under `docs/validation/` record durable validation plans,
validation results, reference case definitions, pass/fail expectations, and
sanitized summaries that should remain reviewable after the phase ends.

ChatGPT Project Sources are compact operating memory for the assistant across
future chats. They should carry only the current canonical project state,
standing instructions, and immediately relevant phase guidance. They are the
right surface when the goal is to refresh working context rather than create a
new durable repo artifact.

Local output-quality review packets under ignored `output/` paths are temporary
review material for answer/source quality, especially after approved live
validation. They may contain sanitized final answers, cited URLs, visible source
sections, CLI-visible telemetry, and reviewer notes. They are not roadmap docs,
architecture docs, validation docs, or Project Sources, and they must remain
untracked unless a later phase explicitly asks for a sanitized committed
summary.

## 2. Decision Rule

Use this placement rule before adding new broad documentation:

| Need | Destination |
| --- | --- |
| Durable architecture decision, invariant, state boundary, or diagnostic contract | `docs/architecture/` |
| Durable validation plan, validation result, reference case, or sanitized validation summary | `docs/validation/` |
| Current operating memory for future chats and phase prompts | ChatGPT Project Source patch or replacement |
| Temporary answer/source-quality review material | Local ignored `output/` packet |

If a proposed document is mostly "what the assistant should remember next
time," prefer a compact Project Source refresh over another repo-tracked
roadmap or status document.

If a proposed document is mostly "what reviewers need to inspect for this live
run," prefer an ignored local output-quality packet and a short final bundle
summary over a committed repo note.

## 3. Current Controller State After AG-46C

AG-46A defined the typed retrieval-batch shape as architecture. AG-46B added a
pure passive retrieval-batch projection trace. AG-46C extracted the runtime
trace projection assembly boundary so the orchestrator attaches passive
projection traces through `core/runtime_trace_projection_assembly.py`.

The active controller state is:

- `stop_sufficient` and `stop_insufficient_with_caveat` remain terminal stop
  actions.
- `recover_missing_source_class`, `recover_weak_corpus`, and
  `resolve_conflict` remain separate higher-priority promoted actions.
- Bounded ordinary continuation from evaluator, expander, and scout may be
  represented under `retrieve_targeted` when the checkpoint selects it and the
  targeted retrieval lifecycle is eligible.
- The retrieval-batch projection is passive runtime visibility only. It
  describes existing sanitized trace facts and may mirror into the checkpoint
  packet.
- `targeted_retrieval_executor_dispatched` remains `false`.
- No `retrieve_targeted` provider role exists.
- Provider policy, routing, search depth, query generation, prompts,
  persistence, final-answer behavior, and protected handoffs remain unchanged.

AG-46C did not make retrieval batches executable. It clarified assembly
ownership for passive trace projection.

## 4. Legal/Current Side-track Status After L2A/L2B

L2A classified AG-41 legal/current-primary failures as a legal source-quality
side track rather than a controller-loop regression.

L2B defined a durable legal/current source-quality diagnostic contract and
validation plan. It did not implement legal-source repair, source-specific
resolvers, provider routing changes, search-depth changes, query/domain tuning,
source-ranking changes, source-classification behavior changes, prompt changes,
evidence-visibility changes, final-answer changes, controller authority
changes, or protected handoff changes.

L2C remains the future live-validation step, and it requires explicit live
validation approval and budget before running. Local L2C output-quality packets
must stay ignored and untracked unless a later phase explicitly scopes a
sanitized committed summary.

## 5. Recommended Next Main-lane Phase

The next main-lane phase should be AG-46D retrieval batch authorization
readiness.

AG-46D should stay on the retrieval-batch authorization path: proving readiness
for bounded authorization semantics and trace/contract clarity before any
executor or provider-facing behavior exists.

It should not be diverted into broad status-doc creation when the only need is
to refresh active assistant memory. In that case, prepare a compact Project
Source patch or replacement instead.

## 6. Non-authorization List

This note does not authorize:

- runtime retrieval behavior changes;
- targeted retrieval executor creation;
- `retrieve_targeted` provider role creation;
- provider selection, routing, depth, or escalation changes;
- query-generation changes;
- prompt changes;
- ranking, source-filtering, or domain-policy changes;
- persistence or schema changes;
- Analyst, Economist, Author, or Scrutineer handoff changes;
- final-answer behavior changes;
- legal/current-primary source repair;
- legal/current live validation without explicit approval;
- social runtime integration;
- output-quality packet commits;
- broad roadmap, checkpoint, or status docs when a compact Project Source
  refresh is the correct surface.
