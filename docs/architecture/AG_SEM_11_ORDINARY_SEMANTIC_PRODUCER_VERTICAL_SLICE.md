# AG-SEM-11 Ordinary Semantic Producer Vertical Slice

Status: Narrow ordinary product-path activation for a single offline fixture.

## Proof Class

`offline_product_path_proof`, qualified to the AG-CHECK-01 single-component
fixture only:

> What is the current official rule for Example Program?

This is not broad ordinary semantic behavior, Balanced/Deep activation, or live
product proof.

## Scope

AG-SEM-11 adds one late, transactional pre-Sufficiency handoff that builds
passive AG-SEM-01..03 proposals from ordinary offline runtime facts and commits
them through existing AG-SEM-05/06/07 reducers immediately before real
Sufficiency judgment.

The handoff is all-or-none: AG-SEM-05, AG-SEM-06, and AG-SEM-07 reduce together
or not at all. Partial canonical semantic state is prevented by preflight only;
this phase does not implement rollback or compensating mutation.

## Actual App Delta

- New bounded runtime module `core/ordinary_semantic_producer_runtime.py`:
  - pure proposal builders from `search_work_plan`, `final_top_evidence`, and
    `evidence_ledger_projection`
  - preflight dry-runs of `build_initial_answer_contract_acceptance_state`,
    `build_semantic_observation_admission_state`, and
    `build_component_coverage_reduction_state` before any live reduce
  - `execute_ordinary_semantic_producer_handoff_from_scope` transactional
    executor
- One orchestrator callsite in `core/pipeline_orchestrator.py` immediately
  before `execute_sufficiency_judgment_handoff_from_scope`
- New tests in
  `tests/test_ag_sem_11_ordinary_semantic_producer_vertical_slice.py`
- AG-CHECK-01 regression update: bounded excerpt text may appear in canonical
  trace via admitted semantic content references

No new RunKernel actions, stages, RunState fields, or pre-Sufficiency semantic
storage bridge were added.

## Bounded Content Source

`SanitizedContentReference.bounded_text` comes from the first bindable passage in
`runtime_scope["final_top_evidence"]`:

| Field | Source |
|-------|--------|
| `bounded_text` | passage `text`, truncated to `MAX_BOUNDED_TEXT_CHARS` |
| `source_title` | passage `title` |
| `source_url` | passage `url` |
| `source_id` | passage `source_id` |
| `evidence_ref_id` | EvidenceLedger candidate matched by URL/custody |

EvidenceLedger identity alone is insufficient without a bindable passage
excerpt.

## Runtime Consumer

The intended downstream consumer is the existing real Sufficiency path:

`execute_sufficiency_judgment_handoff_from_scope` →
`build_semantic_state_facts_for_sufficiency`.

## Closed Surfaces

- AG-SEM-08 contract amendment admission
- FinalAnswerPacket / Author semantic payloads
- SearchJudgment / QueryPlan activation
- Balanced / Deep semantic loops
- Provider / search / retrieval behavior changes
- Compensating rollback or undo of canonical semantic state

## Validation

Validation bucket: `phase_focus` (not `fast_pr`).

```powershell
python -m pytest -q tests/test_ag_sem_11_ordinary_semantic_producer_vertical_slice.py tests/test_ag_sem_05_initial_answer_contract_acceptance.py tests/test_ag_sem_06_semantic_observation_admission.py tests/test_ag_sem_07_component_coverage_reduction.py tests/test_ag_sem_09_sufficiency_semantic_consumption.py tests/test_ag_check_01_offline_ordinary_authority_path.py
```

## Next Gate

Semantic authority handoff into FinalAnswerPacket / Author only after this
producer path is stable on the bounded offline slice.

Hardening phase: [AG_SEM_11B_ORDINARY_SEMANTIC_PRODUCER_HARDENING.md](AG_SEM_11B_ORDINARY_SEMANTIC_PRODUCER_HARDENING.md)
