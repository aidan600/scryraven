Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG_SEM_11B_ORDINARY_SEMANTIC_PRODUCER_HARDENING).

# AG-SEM-11B Ordinary Semantic Producer Hardening

Status: Hardening phase after AG-SEM-11 (PR #277).

## Proof Class

`offline_product_path_proof`, qualified to the AG-CHECK-01 single-component offline
fixture only.

## P2 Gap Memo Summary

P2 identified producer-boundary test gaps for skip integrity and a ledger projection
parity risk (F15). AG-SEM-11B fixes F15 by deriving preflight ledger facts from
`run_kernel.state.evidence_ledger.to_projection()` inside
`execute_ordinary_semantic_producer_handoff_from_scope`, not from
`runtime_scope["evidence_ledger_projection"]`.

## Actual App Delta

- `execute_ordinary_semantic_producer_handoff_from_scope` uses the current RunKernel
  EvidenceLedger projection for all semantic producer preflight.
- `preflight_ordinary_semantic_producer_bundle` returns specific `skipped_reason`
  values on `OrdinarySemanticProducerHandoffResult` for designed negative paths.
- Producer-boundary tests prove skip integrity for classifier, multipart, bindability,
  and coverage-preflight failures without orphan canonical semantic state.
- Final satisfied-coverage authority remains
  `ledger_qualification_blockers_for_satisfied_coverage` (AG-SEM-07); observed
  disposition is coverage-preflight-only (no bindability early-reject).

## Architecture (unchanged from AG-SEM-11)

- One late pre-Sufficiency handoff in `core/pipeline_orchestrator.py`.
- All-or-none AG-SEM-05/06/07 commit after full preflight.
- No compensating rollback or demotion.
- No new RunKernel authority.

## Skipped Reason Values

Return-only on `OrdinarySemanticProducerHandoffResult` /
`OrdinarySemanticProducerPreflightResult` (and tests). These are not RunState,
projection, trace, telemetry, JSONL, or user-visible output fields.

Designed preflight negative paths:

- `query_shape_classifier_unavailable`
- `multipart_assessment`
- `bindable_passage_missing`
- `contract_preflight_failed`
- `admission_preflight_failed`
- `coverage_preflight_failed`
- `preflight_failed` (unexpected fallback only)

Handoff-only prerequisite/idempotence skips:

- `canonical_semantic_state_already_present`
- `search_work_plan_missing`

## Closed Surfaces

Unchanged from AG-SEM-11: AG-SEM-08, FAP/Author semantic payloads, SearchJudgment /
QueryPlan activation, provider/search/retrieval behavior, Balanced/Deep loops, live
validation, second fixture, `fast_pr` promotion.

## Validation

Validation bucket: `phase_focus`.

```powershell
python -m pytest -q tests/test_ag_sem_11_ordinary_semantic_producer_vertical_slice.py tests/test_ag_sem_05_initial_answer_contract_acceptance.py tests/test_ag_sem_06_semantic_observation_admission.py tests/test_ag_sem_07_component_coverage_reduction.py tests/test_ag_sem_09_sufficiency_semantic_consumption.py tests/test_ag_check_01_offline_ordinary_authority_path.py
python -m ruff check core/ordinary_semantic_producer_runtime.py tests/test_ag_sem_11_ordinary_semantic_producer_vertical_slice.py
```

## Prior Doc

Baseline vertical slice: [AG_SEM_11_ORDINARY_SEMANTIC_PRODUCER_VERTICAL_SLICE.md](AG_SEM_11_ORDINARY_SEMANTIC_PRODUCER_VERTICAL_SLICE.md)
