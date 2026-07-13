Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG77B_CONTROLLER_OWNED_CONFLICT_ARBITRATION).

# AG-77B Controller-Owned Conflict Arbitration

Date: 2026-06-01

Phase type: architecture design with minimal pure contract implementation and fixture/static tests.

## Purpose

AG-77B adds a pure Controller-owned arbitration contract that consumes AG-77A
`SourceConflictRepresentation` state and returns deterministic,
ledger-compatible arbitration posture. The contract is passive Controller-visible
state only. It does not change runtime behavior, Author exposure, final-answer
behavior, citation formatting/selection/source ordering, prompt text,
provider/model/search/query behavior, retrieval ranking/filtering, source-class
recovery, weak-corpus recovery, Scrutineer/remediation, Economist/follow-up,
DB/session/`RunOutcome` shape, cache behavior, or `core/pipeline_orchestrator.py`.

The product principle is that ScryRaven should not require 100% certainty for
every ordinary answer, but it also should not falsely balance weak noise against
strong official/current/legal/canonical/source-bound obligations. Lower-tier
evidence may remain useful Controller context, but it cannot satisfy stronger
obligations.

## Existing AG-77A Representation Consumed

AG-77B consumes the inert AG-77A types from `core/source_conflict_model.py`:

- `SourceConflictRepresentation`
- `SourceConflictGroup`
- `SourceConflictRecord`
- claim/source/value/currentness/centrality/obligation/contradiction metadata
  already represented by AG-77A

The arbitration module imports AG-77A model types only. It does not rewrite,
delete, collapse, or mutate represented claims or source refs.

## Arbitration Schema Summary

`core/source_conflict_arbitration.py` defines:

- `SourceConflictArbitrationInput`
  - wraps the AG-77A representation and optional Controller references;
  - records the arbitration schema version;
  - is Controller-owned.
- `SourceConflictRecordArbitration`
  - record-level disposition, answer-posture recommendation, reason, preserved
    claim/source IDs, optional preferred claim ID, non-satisfying/background
    claim IDs, unresolved/blocking flags, obligation impact, centrality,
    contradiction shape, preserved claim payloads, and inert no-runtime-change
    metadata.
- `SourceConflictGroupArbitration`
  - group aggregation of record arbitrations, group disposition, answer posture,
    unresolved/blocking/report-both counts, source IDs, claim IDs, and
    ledger-compatible metadata.
- `SourceConflictArbitrationState`
  - top-level Controller state with input/arbitration schema versions, group
    arbitrations, top-level answer posture, counters, Controller/ledger flags,
    and explicit behavior-no-change flags.

The public helper is `arbitrate_source_conflicts(...)`, which accepts either a
`SourceConflictArbitrationInput` or a `SourceConflictRepresentation`.

## Disposition Enum Summary

`SourceConflictArbitrationDisposition` values:

- `no_conflict`
- `ignore_non_material_conflict`
- `prefer_claim_a`
- `prefer_claim_b`
- `report_both`
- `report_both_by_scope`
- `unresolved_blocking`
- `unresolved_nonblocking`
- `needs_more_evidence`
- `background_only`

A preference disposition chooses Controller posture only; it does not delete the
non-preferred claim and does not alter AG-77A state.

## Answer-Posture Enum Summary

`SourceConflictAnswerPosture` values:

- `no_answer_impact`
- `qualified_answer`
- `partial_answer`
- `insufficient_for_authoritative_answer`
- `source_bound_value_unresolved`

These are passive recommendations for a later integration phase, not active
runtime/final-answer instructions.

## Minimum Arbitration Rules

1. **Equal official/current sources conflict**
   - Do not choose a winner.
   - Mark unresolved.
   - If central and obligation-impacting, block authoritative posture.
2. **Official/current vs secondary**
   - Prefer official/current for authority-bound claims when scope/currentness
     match.
   - Preserve secondary evidence as context/background if useful.
   - Explicitly mark lower-tier evidence as non-satisfying for the stronger
     obligation.
3. **Current vs stale**
   - Prefer current when source class, jurisdiction, and scope are compatible.
   - Preserve stale evidence as superseded/deprioritized/background.
4. **Jurisdiction/scope mismatch**
   - Do not pick a global winner.
   - Report both by scope when material.
5. **Source-bound numeric conflict**
   - Preserve both values, units, source identities, and effective periods.
   - If central and same scope/effective period, mark the source-bound value
     unresolved.
   - Do not flatten values into one scalar.
6. **Peripheral/background conflict**
   - Preserve internally if useful.
   - Do not block answer posture.
   - Do not force Author exposure.
7. **No conflict / empty representation**
   - Return no-conflict / no-answer-impact aggregate posture.

## Rule Examples

### Equal official/current conflict

Two official/current sources disagree on a central official-current deadline.
AG-77B returns `unresolved_blocking` with
`insufficient_for_authoritative_answer`, preserves both claim/source IDs, and
leaves `preferred_claim_id` unset.

### Official/current vs secondary

An official/current claim conflicts with a secondary claim under an official
current obligation. AG-77B returns `prefer_claim_a` or `prefer_claim_b` for the
official/current claim, preserves the secondary claim, records it as
background/context, and marks it as non-satisfying for the stronger obligation.

### Current vs stale

A current and stale source of the same authority/scope disagree. AG-77B prefers
the current claim, preserves the stale claim, and marks the stale claim as
background/deprioritized evidence.

### Jurisdiction/scope mismatch

US federal and EU member-state claims disagree because their scope differs.
AG-77B returns `report_both_by_scope`, leaves `preferred_claim_id` unset, and
preserves both jurisdiction/scope values.

### Source-bound numeric conflict

Two source-bound datasets provide different numeric values for the same scope and
effective period. AG-77B returns `unresolved_blocking` with
`source_bound_value_unresolved`, preserving both values, units, source IDs, and
effective periods.

### Peripheral/background conflict

A peripheral contradiction has no obligation impact. AG-77B returns
`background_only`, preserves both claims internally, does not block posture, and
does not require Author exposure.

## Controller-Visible / Ledger-Compatible Serialization

Every arbitration dataclass has `to_controller_state()` and `to_trace_fragment()`
helpers. Top-level trace serialization is wrapped under
`source_conflict_arbitration`. Serialized state is JSON-safe and includes:

- schema versions;
- group/record dispositions;
- answer-posture recommendations;
- preserved source and claim IDs;
- obligation impact, centrality, and contradiction shape;
- Controller-visible and ledger-compatible flags;
- explicit no-change flags for runtime/final-answer/citation/prompt/provider-
  search-query behavior.

## AG-77A Immutability Guarantee

AG-77B reads AG-77A records, claims, source refs, values, scopes, currentness,
and obligation metadata. It writes no fields back to AG-77A objects. Tests
serialize/deepcopy AG-77A representation state before arbitration and assert the
representation, group, and record serializations remain identical afterward.

## Lanes Kept Distinct

AG-77B does not merge with or alter these lanes:

1. ordinary next-query generation;
2. conflict-resolution retrieval/controller/executor;
3. source-class recovery;
4. weak-corpus recovery;
5. Scrutineer/remediation.

The arbitration module does not import conflict-resolution controller/executor,
source-class recovery, weak-corpus, Scrutineer/remediation, provider/search/query,
or pipeline orchestration modules. It does not generate resolving queries or run
searches.

## Evidence Preservation Is Not Author Exposure

AG-77B may preserve lower-tier, stale, background, or non-preferred evidence in
Controller state. That preservation is not an instruction to expose the evidence
to the Author, cite it, reorder citations, or alter final answers. Exposure and
runtime integration are parked for a later licensed phase.

## No AG-78 Indirect Inference Implementation

AG-77B does not implement premise-bridge reasoning, indirect inference,
premise-chain APIs, or inference helpers. Cases with no direct source for A may
still have useful later answers, but that work belongs to AG-78 and remains
outside this phase.

## Tests Added

`tests/test_ag77b_source_conflict_arbitration.py` covers:

- equal official/current conflict;
- official/current vs secondary;
- current vs stale;
- jurisdiction/scope mismatch;
- source-bound numeric conflict;
- peripheral/background conflict;
- Controller-visible / ledger-compatible JSON-safe serialization;
- AG-77A immutable consumption;
- static protected-import guard;
- retrieval/recovery lane distinction;
- no AG-78 indirect inference APIs;
- no `pipeline_orchestrator.py` rewrite.

## Protected Surfaces Kept Closed

AG-77B intentionally does not touch runtime/final-answer/Author/citation/prompt/
provider/search/query/retrieval/recovery/Scrutineer/remediation/Economist/
follow-up/DB/session/`RunOutcome`/cache/orchestrator behavior.

## Stop Conditions

Future AG-77B follow-up work should stop if implementation requires any of the
closed surfaces above, live validation, runtime integration, retrieval behavior,
provider/model/search calls, or AG-78 indirect inference/product decisions beyond
the rules in this document.

## Expected AG-77C Follow-up

Recommended next phase after AG-77B succeeds: **AG-77C — Conflict Arbitration
Runtime / AnswerContract Integration**. AG-77C should decide whether and how this
passive Controller-owned posture becomes an active runtime/AnswerContract input,
with explicit authorization for any behavior changes before implementation.
