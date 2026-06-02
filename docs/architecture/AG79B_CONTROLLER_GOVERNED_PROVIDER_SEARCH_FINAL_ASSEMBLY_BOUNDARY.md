# AG-79B — Controller-Governed Provider/Search and Final Assembly Boundary Repair

Date: 2026-06-02.

Phase type: targeted authority repair / static fixtures / behavior-preserving boundary hardening.

## Relationship to AG-79A

AG-79A found that ScryRaven has many Controller-visible contracts, but provider/search/depth/query selection and final evidence/citation/Author assembly remained the largest active paths where Controller posture could still be bypassed by local/orchestrator/downstream facts. AG-79B follows that audit without changing product behavior: it adds a static authority-boundary helper and fixture tests that classify these facts as Controller-owned, explicitly protected legacy behavior, or consciously parked hidden authority.

## Exact authority boundary repaired or proved

AG-79B proves the boundary between already-computed Controller/runtime handoff facts and downstream provider/search/final-assembly consumers. The new static helper rejects fixture states where:

- an effective provider list differs from a Controller-owned provider list;
- an effective search depth differs from Controller-owned retrieval/depth posture;
- citation/source-list handoff identity is not derived from final evidence identity;
- Author handoff identity is not derived from final evidence identity;
- inferred conclusions are presented as direct source statements;
- weak, secondary, or lower-tier evidence satisfies stronger official/current/legal/canonical/source-bound obligations.

The helper is not wired into `core/pipeline_orchestrator.py`, so runtime behavior remains unchanged.

## Provider/search/depth/query boundary classification

Controller-owned:

- Provider list where a Controller-owned provider/search allocation posture is present.
- Search depth where a Controller-owned retrieval/depth posture is present.
- Query order where the query source is a Controller-owned router/query-preparation or retrieval-loop handoff.
- Recovery query dispatch when sourced from targeted retrieval, source-class recovery, weak-corpus recovery, or conflict-resolution Controller decisions.

Explicitly protected legacy behavior:

- Existing provider selection when no Controller-owned provider list exists.
- Existing search depth when no Controller-owned retrieval/depth posture exists.
- Existing recency merge behavior, including ordering semantics already produced by the legacy query path.
- Existing query-generation policy, ranking/filtering, citation ordering, and Author prose.

Consciously parked hidden authority:

- Synthesis-evaluator or supplemental search triggers when reachable but not yet proven Controller-owned by an active handoff.
- Broad orchestrator-local domain decisions outside this phase's provider/search/final-assembly boundary.
- Scrutineer/remediation authority, which remains out of scope for AG-79B.

## Final evidence/citation/Author assembly boundary classification

Controller-owned:

- Final evidence identity used by the citation/source-list handoff.
- Ordered source list identity when derived from the final evidence bundle.
- Author evidence/context identity when derived from final evidence identity.
- Existing Controller-owned insufficiency labels where already licensed.
- AG-77 conflict posture labels where already licensed.
- AG-78 direct-vs-inferred presentation labels where already licensed.
- Strong obligation non-satisfaction by weak/secondary/lower-tier evidence.

Explicitly protected legacy behavior:

- Existing final evidence selection, source ID assignment, citation formatting, source ordering, prompt text, and Author prose.
- Existing final evidence bundle builder behavior.

Consciously parked hidden authority:

- Any final prompt/source assembly branch that is not yet represented by a Controller-owned handoff and is not repaired in this phase.
- Full orchestrator decision audit of local domain branching.

## What is Controller-owned

AG-79B treats the following as Controller-owned when the corresponding posture/handoff exists:

- provider allocation posture;
- retrieval/depth posture;
- router/query-preparation source of ordered queries;
- recovery dispatch posture for source-class, weak-corpus, targeted, and conflict-resolution retrieval;
- final evidence identity consumed by citation/source-list and Author handoffs;
- insufficiency, conflict, and indirect-inference presentation labels already licensed by AG-76D, AG-77, and AG-78.

## What remains explicitly protected legacy behavior

AG-79B preserves and documents the following legacy behavior rather than changing it:

- provider routing and provider choice when not supplied by a Controller-owned handoff;
- search depth policy when not supplied by a Controller-owned handoff;
- query generation and recency merge behavior;
- retrieval ranking/filtering;
- final evidence selection;
- citation formatting, citation selection, and source ordering;
- prompt text, prompt semantics, Author notes, and Author prose.

## What remains consciously parked hidden authority

The following hidden-authority surfaces remain parked for a later phase:

- synthesis-evaluator supplemental-search triggers if reachable;
- Scrutineer/remediation run gates, query generation, dispatch, re-synthesis, and Author directives;
- broad `core/pipeline_orchestrator.py` local domain decisions not covered by this static boundary fixture;
- adapter debt that does not block this boundary proof.

## Tests added

AG-79B adds:

- `tests/test_ag79b_provider_search_authority_boundary.py`
- `tests/test_ag79b_final_assembly_authority_boundary.py`

These tests prove provider-list and search-depth no-bypass behavior in static fixtures; classify query order, recency merge, recovery query dispatch, and supplemental search; prove final evidence identity feeds citation/source-list and Author handoff identity; preserve insufficiency/conflict/inference labels; prevent inferred-as-direct laundering; prevent weak evidence from satisfying stronger source obligations; enforce protected imports; and guard that `core/pipeline_orchestrator.py` is untouched.

## Protected surfaces kept closed

Closed in AG-79B:

- provider/model/search behavior;
- provider swaps or new providers;
- search depth policy;
- query generation;
- retrieval ranking/filtering;
- prompt text and prompt semantics;
- citation formatting, citation selection, and source ordering;
- Author prose;
- Scrutineer/remediation behavior;
- Economist behavior;
- DB/session/RunOutcome shape;
- cache implementation;
- live validation;
- broad `core/pipeline_orchestrator.py` rewrite.

## Stop conditions

AG-79B would stop rather than continue if the repair required changing provider routing, provider selection, search depth, query generation, ranking/filtering, citation selection, Author prose, prompts, Scrutineer/remediation, Economist behavior, DB/session/RunOutcome, cache behavior, live behavior, a broad orchestrator rewrite, or a product decision about provider/search/citation/Author quality. None of those stop conditions were triggered.

## AG-78G live-gate decision

AG-78G remains live-gated. AG-79B did not run live validation, live product-path commands, provider/model calls, or search calls.

## AG-76D-AD adapter cleanup decision

AG-76D-AD remains parked. Adapter debt did not block this static boundary proof and should not preempt targeted authority repair unless a later phase proves it blocks safe repair.

## Recommended next phase

Recommended next phase: **AG-79C — Orchestrator Decision Audit**.

Rationale: AG-79B proves the targeted provider/search/final-assembly boundary without touching runtime behavior. AG-79A and AG-79B still leave broad local domain decisions, supplemental search, and Scrutineer/remediation as parked hidden-authority surfaces. AG-79C should audit those orchestrator decision points before any behavior-changing work is considered.
