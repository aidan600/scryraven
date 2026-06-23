# AG-SEM-09 Sufficiency Semantic Consumption

Status: Canonical authority consumption. Fifth canonical semantic authority bridge.

## Proof Class

`offline_product_path_proof`

## Scope

AG-SEM-09 consumes canonical AG-SEM-05 accepted initial answer contract, AG-SEM-07
component coverage history, and AG-SEM-08 contract amendment admission history inside
the **real** RunAuthority Sufficiency judgment path.

The product-path delta is limited to Sufficiency input assembly, deterministic
judgment, model repair guards, and Sufficiency projection pass-through. Semantic
blockers are enforced in `build_deterministic_sufficiency_judgment` and preserved
by `validate_or_repair_sufficiency_judgment`.

This phase consumes semantic state in Sufficiency only. It does not mutate accepted
contracts, apply amendments, invalidate coverage, authorize follow-up, decide
SearchJudgment, activate QueryPlan/SearchWorkPlan, create Author input, change
search/provider behavior, or change FinalAnswerPacket behavior.

## What Was Not Built

- No new RunKernel action, stage, or observation
- No new RunState semantic-consumption state/projection/history fields
- No standalone pre-Sufficiency reducer or storage bridge
- No `core/pipeline_orchestrator.py` changes

## Actual App Delta

- New bounded runtime module
  [`core/sufficiency_semantic_state_consumption_runtime.py`](../core/sufficiency_semantic_state_consumption_runtime.py)
  builds compact `semantic_state_facts` and evaluates deterministic semantic overlays.
- [`core/run_authority_sufficiency_adapter.py`](../core/run_authority_sufficiency_adapter.py)
  assembles `semantic_state_facts` into `RunSufficiencyJudgmentInput`.
- [`core/run_authority_sufficiency_validation.py`](../core/run_authority_sufficiency_validation.py)
  applies semantic blockers in deterministic judgment and model repair guards.
- [`core/run_authority_sufficiency_runtime.py`](../core/run_authority_sufficiency_runtime.py)
  passes canonical RunKernel semantic state into the adapter during the main
  sufficiency handoff only.
- [`core/run_kernel.py`](../core/run_kernel.py) passes
  `semantic_consumption` and `semantic_state_facts_summary` through
  `_canonical_sufficiency_judgment_projection`.

## Runtime Consumer

`RunKernel.RunAuthoritySufficiencyJudgment` is the immediate consumer. Semantic
facts affect actual Sufficiency judgment input, deterministic decision, repair
guards, and canonical projection.

## Semantic Blocker Rules

Coverage-derived blockers (from latest per-component coverage history):

- missing required component coverage blocks direct answer
- required component not satisfied / partial / unsupported blocks direct answer
- stale coverage blocks finalization
- conflicted coverage blocks finalization
- remaining unknowns block direct answer
- follow-up need required/blocked blocks finalization without follow-up authorization
- unsatisfied/partial/unknown source obligation blocks direct answer
- missing/unreadable/stale/unknown content availability blocks direct answer
- evidence not custodied blocks direct answer
- weak-only evidence basis blocks direct answer

Amendment-derived blockers (from admission history):

- material amendments requiring confirmation/scenario/authority block finalization
  unless `user_confirmation_posture` is explicit confirmation, labeled scenario, or
  explicit user authority
- blocked amendment candidates block finalization
- rejected amendments with ordinary rejection reasons do not block by themselves
- weakening/removal without explicit user authority blocks finalization
- candidate invalidated coverage refs make linked coverage suspect without mutating
  coverage records
- candidate new contract version/digest remain candidate-only

Semantic `required_caveats` and `prohibited_upgrades` merge into Sufficiency
`mandatory_caveats` and `prohibited_upgrades`.

## Projection Fields

`RunSufficiencyJudgment.to_projection()` adds:

- `semantic_consumption` — blocker summary, digest, suspect component ids, candidate
  contract versions (candidate-only)
- `semantic_state_facts_summary` — compact digest and blocker codes

## Closed Surfaces

No follow-up authorization, no search/provider/retrieval/fetch/read behavior, no
citation behavior, no Author behavior, no FinalAnswerPacket behavior, no accepted
contract mutation, no amendment application, no coverage invalidation or stale
marking, no live validation, and no `core/pipeline_orchestrator.py` changes.

## Relationship To Prior AG-SEM Phases

- Consumes AG-SEM-05 accepted initial answer contract
- Consumes AG-SEM-07 `component_coverage_history`
- Consumes AG-SEM-08 `contract_amendment_admission_history`
- Does not mutate any upstream canonical semantic state

## Validation

New tests are classified as `phase_focus`.

- `tests/test_ag_sem_09_sufficiency_semantic_consumption.py`
- regression: AG-SEM-05 through AG-SEM-08, AG-92C sufficiency, AG-91H RunKernel
- touched-file `ruff check`, `pre-commit`, and `git diff --check`
