# AG-69A Controller Authority Lifecycle Contract

Scope: offline model/contract/test work only. No live ProPlex runs, provider
calls, provider routing, provider selection, provider depth, retrieval,
ranking, filtering, prompt wording, citation/final-answer behavior, legal
answer behavior, follow-up behavior, or broad pipeline orchestration changes
were made.

## Goal

Define a controller-owned lifecycle contract for required
`AuthorityRequirement` state. The contract must represent the AG-68 failure
families without patching IRS/SSA behavior directly.

## Decision Records

### 1. Reconnaissance Review

AG-68H and AG-68I split the live failure families into independent surfaces:

- SSA-style failure: `terminal_stop_approved` blocked official/current recovery
  before source-class recovery execution.
- IRS-style failure: recovery dispatched and returned candidates, but candidate
  source-fit/final evidence/citation visibility did not complete.

Existing obligation models already represent requirement, evidence fit, and
satisfaction. They did not provide one controller-owned lifecycle object that
can reject forbidden cross-layer states.

### 2. Pre-Implementation Decision

Add a pure model module, `core/authority_lifecycle_contract.py`, and focused
tests. Do not wire the contract into runtime dispatch in this phase. The
contract validates lifecycle state and projections; orchestrator/executor
behavior remains unchanged.

### 3. Post-Implementation Self-Review

The new model exposes:

- `AuthorityLifecycle`;
- `AuthorityLifecycleState`;
- `AuthorityLifecycleStep`;
- `AuthorityLifecycleBlocker`;
- `AuthorityLifecycleAction`;
- `AuthorityLifecycleExecution`;
- `AuthorityLifecycleCandidateFit`;
- `AuthorityLifecycleProjection`.

It also models existing evidence fit, lower-tier context, recovery need,
terminal stop state, weak-corpus state, candidate acquisition/return/source-fit,
satisfaction, final evidence, citation eligibility, final posture, and explicit
controller blockers.

### 4. Validation Decision

Validation is offline only. Focused tests prove the required forbidden states
and AG-68 failure families can be represented by the contract. Broader
authoritative-source/controller tests should be run only as offline regression
checks.

### 5. Final Recommendation Review

Next phase should decide whether and where this contract becomes the runtime
authority lifecycle handoff. Recommended opening surface: controller/admission
arbitration for terminal-stop versus required authoritative recovery. Keep
provider, retrieval, prompt, citation, and final-answer behavior closed until
the controller lifecycle is wired and observed.

## Protected Surfaces

Remained closed:

- provider routing, provider selection, provider depth;
- retrieval, ranking, filtering;
- prompt wording;
- citation and final-answer behavior;
- Author, Analyst, Economist, Scrutineer, legal answer, and follow-up behavior;
- broad `core/pipeline_orchestrator.py` changes;
- live validation.
