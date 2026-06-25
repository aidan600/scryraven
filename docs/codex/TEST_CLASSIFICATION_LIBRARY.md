# Test Classification Library

Status: Codex-visible reference for classifying new tests before they enter
permanent validation surfaces.

Use this with [VALIDATION_BUCKETS.md](VALIDATION_BUCKETS.md) whenever a phase
adds, promotes, demotes, or retires tests.

## Default Rule

New tests start as `phase_focus` unless the phase explicitly justifies another
bucket.

Do not add a new test to a permanent bucket manifest until the phase brief or
PR notes classify it with the fields below. Promotion to `fast_pr`,
`semantic_lane`, `semantic_search_lane`, `author_lane`, or `full` must be
deliberate, cheap enough for the chosen bucket, and tied to the proof class the
phase actually claims.

## Bucket Classes

| Bucket | Meaning |
| --- | --- |
| `docs_only` | No test is added or run by default because only docs, prompts, runbooks, or operator text changed. |
| `fast_pr` | Cheap broad sentinels for ordinary PR confidence. These are not phase-detail tests. |
| `phase_focus` | Local phase proof for the exact changed seam and its immediate producer/consumer surface. |
| `semantic_lane` | Durable semantic producer, reducer, sufficiency, component coverage, and semantic projection validation. Not ordinary PR tax. |
| `semantic_search_lane` | Durable SearchJudgment and QueryPlan validation for semantic missing assessments and semantic component gaps. Not ordinary PR tax. |
| `author_lane` | Detailed Author custody coverage and related high-custody workflow tests. |
| `full` | Complete offline suite. This is not ordinary PR tax. |

## Required New-Test Classification

Every new test needs this classification before it is added to a permanent
bucket manifest:

```text
Test path/node id:
Proof class:
Validation bucket:
Protected surface guarded:
Runtime/product path guarded:
Expected cost:
Promotion posture:
Demotion/retirement condition:
Why not fast_pr, or why fast_pr if promoted:
```

Field guidance:

- **Test path/node id** names the exact pytest path or node id.
- **Proof class** must use the proof classes in
  [PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md](PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md).
- **Validation bucket** is one of `docs_only`, `fast_pr`, `phase_focus`,
  `semantic_lane`, `semantic_search_lane`, `author_lane`, or `full`.
- **Protected surface guarded** names the custody, contract, authority,
  semantic, or operator surface the test protects.
- **Runtime/product path guarded** states whether ordinary product execution,
  CLI execution, a component harness, a reducer, a fixture, docs, or no runtime
  path is guarded.
- **Expected cost** should be concrete enough to explain why the test belongs in
  the chosen bucket.
- **Promotion posture** states whether the test stays local, is a sentinel
  candidate, belongs in a domain lane, or is full-only.
- **Demotion/retirement condition** names when the test should be removed,
  narrowed, fixtureized, or replaced.
- **Why not fast_pr, or why fast_pr if promoted** must explain either why the
  test is too detailed or costly for ordinary PR tax, or why it is a cheap broad
  sentinel worth promoting.

## Fast PR Sentinel Rule

`fast_pr` entries must remain cheap broad sentinels. They should protect a
contract boundary where a serious regression would be caught quickly.

Do not use `fast_pr` for phase-detail tests, exhaustive custody checks,
long-running end-to-end coverage, semantic record build-out, or tests whose
main value is explaining a single phase's implementation detail.

## Semantic Record Guidance

The following tests normally belong in `phase_focus` first:

- `QuestionMeaningRecord` tests.
- `SemanticObservation` tests.
- `ComponentCoverageRecord` tests.
- `ContractAmendmentRecord` tests.
- Canonical reducer tests.
- Sufficiency coverage-consumption tests.

Promote one of these to `fast_pr` only when it has become a cheap broad sentinel
for a runtime-consumed contract. Otherwise keep it as phase-focused proof or
move it into `semantic_lane` when durable semantic validation owns it.

## Author Custody Detail

Author custody detail tests belong in `author_lane` unless the phase
deliberately chooses exactly one cheap broad sentinel for `fast_pr`.

The sentinel must be inexpensive, stable, and representative of a broad
contract boundary. Detailed Author invocation construction, materialization,
adapter accounting, finalization, prompt/content-shape, or high-custody
end-to-end tests should stay out of ordinary PR tax unless explicitly promoted
with a clear cost and sentinel rationale.

## Full Suite Posture

The `full` suite is not ordinary PR tax. Use it for push-to-main, manual serious
validation, or explicitly licensed phases that need complete offline coverage.

Do not route a test to `full` merely because it is expensive. Expensive tests
still need an owner, retirement posture, and a reason they are not represented
by cheaper focused or sentinel coverage.
