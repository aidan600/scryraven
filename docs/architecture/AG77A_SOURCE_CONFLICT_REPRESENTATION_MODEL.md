# AG-77A Source Conflict Representation Model

Date: 2026-06-01
Phase type: Architecture design with minimal inert contract implementation
Mode: Architecture Groove / Prove Mode

## Purpose

AG-77A defines a passive, Controller-visible source-conflict representation
model for ScryRaven. The model preserves conflicting source claims without
choosing a winner, changing final-answer behavior, changing citation behavior,
or changing retrieval/provider/search/query behavior.

This phase prepares a richer representation surface for AG-77B conflict
arbitration. AG-77A itself performs no arbitration.

## Existing Conflict Machinery Inspected

The existing conflict surfaces are intentionally narrow:

- `core/conflict_state_producer.py` produces compact runtime conflict facts from
  sanitized evidence. It recognizes only bounded conflict state such as explicit
  effective-date tension, conflict notes, claims in tension, evidence refs, and
  resolving-query candidates. It does not own source hierarchy, source identity
  preservation beyond compact refs, broad jurisdiction/scope tension, or numeric
  source-bound conflict records.
- `core/conflict_resolution_controller.py` owns the passive decision contract for
  conflict-resolution retrieval. It separates `resolving_queries` from ordinary
  `next_queries`, applies lifecycle/budget/provider/depth blockers, and remains
  a dispatcher contract rather than a representation model.
- `core/conflict_resolution_executor.py` executes an already-approved bounded
  conflict-resolution action. It is an execution lane and is not changed by
  AG-77A.
- `core/answer_contract_runtime_handoff.py` carries conflict facts into runtime
  answer-contract state through fields such as `conflicts_present`,
  `conflict_notes`, and `resolving_queries`; AG-77A does not change those fields.
- `core/controller_evidence_ledger.py`, when present, provides Controller-visible
  evidence ledger concepts, but AG-77A does not require a ledger schema or
  runtime ledger integration.
- `core/final_evidence_bundle_builder.py` assigns final source IDs and packages
  final evidence/source-list facts mechanically. AG-77A does not change final
  evidence selection, source ordering, citation formatting, or Author evidence.
- Existing source-class recovery, weak-corpus recovery, Scrutineer/remediation,
  and ordinary retrieval lanes remain separate controller or runtime surfaces.

Conclusion: AG-77A should add a passive representation model that can preserve
richer conflict facts for the Controller and future ledger snapshots, while
leaving existing conflict detection, conflict-resolution dispatch, source-class
recovery, weak-corpus recovery, Scrutineer/remediation, and final answer behavior
unchanged.

## New Source Conflict Representation Model

AG-77A adds `core/source_conflict_model.py` as an inert contract module. It
contains dataclasses/enums only, plus small fixture/static construction helpers.
The module imports only Python standard-library data-shaping utilities and does
not import runtime behavior modules.

The top-level shape is:

```text
SourceConflictRepresentation
  -> SourceConflictGroup[]
      -> SourceConflictRecord[]
          -> SourceConflictClaim claim_a
          -> SourceConflictClaim claim_b
              -> SourceConflictSourceRef
              -> SourceConflictValue
```

All records expose `winner_chosen = false`, `controller_visible = true`, and
`ledger_compatible = true` by default. Serialization helpers produce JSON-safe
`to_controller_state()` and `to_trace_fragment()` payloads.

## Field / Schema Summary

### `SourceConflictSourceRef`

Carries source identity and provenance:

- `source_id`, `url`, `title`, `domain`;
- `source_class`, `source_tier`, `publisher`, `issuer`;
- `retrieved_at`, `observed_at`, `published_at`, `updated_at`, `effective_date`;
- `currentness_label`;
- `jurisdiction`, `scope`;
- `evidence_position`, `evidence_hash`, `text_hash`;
- `authority_weight_hint`, explicitly marked non-arbitrating in serialization.

### `SourceConflictClaim`

Carries one source-bound claim:

- `claim_id`, `claim_text`, `claim_summary`, `normalized_claim_key`;
- `observed_value`, `observed_unit`;
- `date_or_period`, `effective_period_start`, `effective_period_end`;
- `jurisdiction`, `scope`;
- `source_ref`;
- `source_class`, `source_tier`, `currentness_label`;
- `confidence_label`, `posture_label` when already available;
- `source_bound` for quantitative or otherwise source-bound claims.

### `SourceConflictRecord`

Carries one unresolved pairwise conflict:

- `conflict_id`;
- `contradiction_shape` values such as direct value conflict, effective-date
  tension, stale/current tension, jurisdiction/scope mismatch,
  source-class/authority mismatch, source-bound numeric conflict, and ambiguous
  or partial conflict;
- `claim_a` and `claim_b`;
- `centrality`;
- `unresolved_state`;
- `obligation_impact` and optional obligation detail;
- `lower_tier_cannot_satisfy_stronger_obligation`;
- Controller/ledger visibility flags;
- `winner_chosen = false`.

### `SourceConflictGroup`

Groups records and exposes summaries:

- `group_id`, `records`;
- `involved_source_ids`;
- `involved_source_classes`;
- `involved_claim_keys`;
- `unresolved_count`;
- `highest_obligation_impact`;
- `controller_visible`, `ledger_compatible`, `arbitration_ready`;
- `final_answer_behavior_changed = false`.

### `SourceConflictRepresentation`

A top-level trace/controller state container with:

- `groups`;
- schema version;
- unresolved counts;
- Controller and ledger visibility flags;
- `runtime_behavior_changed = false`;
- `final_answer_behavior_changed = false`;
- `winner_chosen = false`.

## How Conflicting Source Identities Survive

Each `SourceConflictRecord` stores two complete `SourceConflictClaim` objects.
Each claim owns its own `SourceConflictSourceRef`. Group serialization exposes
both the nested source refs and a deduped `involved_source_ids` list. No helper
collapses the claims into one value or one source.

This directly supports the AG-77A requirement that two official/current sources
with incompatible claims both survive representation in one group.

## How Hierarchy Is Preserved Without Flattening

Hierarchy is represented as data, not as a decision:

- each source ref carries `source_class` and `source_tier`;
- each claim mirrors its source class/tier for claim-level inspection;
- `SourceConflictObligationImpactDetail` can state a required source class/tier;
- `lower_tier_cannot_satisfy_stronger_obligation` remains explicit.

This lets the Controller observe that secondary evidence conflicts with an
official/current obligation without allowing the secondary source to satisfy the
stronger obligation through flattening. AG-77A still does not choose the official
source as the winner.

## How Stale / Current and Effective-Date Tension Are Represented

Currentness is represented at both source and claim level through
`SourceConflictCurrentness`. Effective-date information is preserved through
source-level `effective_date` and claim-level `date_or_period`,
`effective_period_start`, and `effective_period_end`.

Records can carry both `stale_vs_current` and `effective_date_tension` shapes
when both dimensions matter.

## How Jurisdiction / Scope Mismatch Is Represented

Source refs and claims both carry `jurisdiction` and `scope`. A record can carry
`jurisdiction_scope_mismatch` without choosing a globally correct source. This
supports cases where two sources are plausible within different jurisdictions or
scopes and the Controller must preserve that distinction for later arbitration.

## How Source-Bound Numeric Conflicts Are Represented

`SourceConflictValue` preserves the observed value, unit, value kind, and
optional normalized value. `SourceConflictClaim.source_bound` marks values that
must remain tied to their source. Records can carry the
`source_bound_numeric_conflict` shape and the
`affects_source_bound_quantitative` obligation impact.

This prevents a numeric conflict from being flattened into an unbound scalar.

## Controller Visibility and Ledger Compatibility

`to_controller_state()` returns JSON-safe dictionaries containing groups,
records, claims, source refs, unresolved state, obligation impact, and inert
metadata. `to_trace_fragment()` wraps the same state under
`source_conflict_representation`.

The model is ledger-compatible because it uses stable IDs, hashes, source refs,
claim keys, explicit unresolved state, and JSON-safe values without requiring a
DB/session/RunOutcome schema change.

## Lanes Kept Distinct

AG-77A does not merge or modify these lanes:

1. **Ordinary next-query generation** remains separate from conflict-resolution
   queries in existing retrieval/router/answer-contract surfaces.
2. **Conflict-resolution queries** remain owned by the existing conflict-state
   and conflict-resolution controller/executor lane.
3. **Source-class recovery** remains in the source-class recovery lane.
4. **Weak-corpus recovery** remains in the weak-corpus recovery lane.
5. **Scrutineer/remediation** remains a separate runtime/protected surface.

The new model imports none of those lane modules and does not change
`core/pipeline_orchestrator.py`.

## Tests Added

AG-77A adds `tests/test_ag77a_source_conflict_representation_model.py` with
fixture/static tests for:

1. two conflicting official/current sources both surviving representation;
2. official/current versus secondary hierarchy preservation;
3. stale/current and effective-date tension preservation;
4. jurisdiction/scope mismatch without a winner;
5. source-bound numeric values, units, source identities, and effective periods;
6. Controller-visible / ledger-compatible unresolved state serialization;
7. protected-surface import guards;
8. lane-distinction and no-pipeline-rewrite guards;
9. no winner/arbitration helper exposure.

## Protected Surfaces Kept Closed

AG-77A does not change:

- Author/final-answer behavior;
- citation behavior;
- prompt text;
- provider/model/search/query behavior;
- retrieval ranking/filtering;
- source-class recovery behavior;
- weak-corpus recovery behavior;
- Scrutineer/remediation behavior;
- Economist/follow-up behavior;
- DB/session/RunOutcome shape;
- cache behavior;
- `core/pipeline_orchestrator.py`.

## Stop Conditions

AG-77A would stop rather than proceed if implementation required winner
selection, arbitration, final-answer behavior changes, citation changes, prompt
changes, provider/search/query changes, retrieval ranking/filtering changes,
source-class recovery behavior changes, Scrutineer/remediation changes,
Economist/follow-up changes, DB/session/RunOutcome changes, cache work, live
validation, broad orchestrator rewrites, or any model that could not preserve
both conflicting sources.

No stop condition was encountered.

## Expected AG-77B Follow-Up

Recommended next phase: **AG-77B — Controller-Owned Conflict Arbitration**.

AG-77B should consume this passive representation and define Controller-owned
arbitration rules. AG-77B may decide how to evaluate source class/tier,
currentness, effective periods, jurisdiction/scope, and obligation impact, but
it should do so in a separately licensed phase with explicit behavior-change
boundaries and tests.
