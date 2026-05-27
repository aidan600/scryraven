# AG-69B Controller Runtime Arbitration

Scope: controller/runtime arbitration for terminal stop, weak corpus, recovery
permission, and explicit insufficient/partial posture. No live ProPlex run,
provider/model/search call, provider routing, provider selection, provider
depth, retrieval/ranking/filtering behavior, prompt wording, citation/final
answer behavior, legal answer behavior, follow-up behavior, or broad pipeline
orchestration change was made.

## Goal

Route required authoritative recovery arbitration through the controller-owned
`AuthorityLifecycle` contract so terminal-stop and weak-corpus gates cannot
preempt unmet required authority recovery unless the lifecycle records a
requirement-bound hard blocker or an explicit insufficient/partial posture.

## Decision Records

### 1. Reconnaissance Review

AG-68H/AG-68I localized the SSA-style failure before dispatch: terminal stop
was consumed as a runtime blocker before required official/current recovery
could execute. Existing controller code had two relevant gates:

- admission blocked on raw `terminal_stop_approved` or weak-corpus facts;
- the controller spine let terminal/weak checkpoint actions outrank
  source-class recovery dispatch.

### 2. Pre-Implementation Decision

Add a small pure runtime arbitration helper that builds an `AuthorityLifecycle`
from sanitized controller facts. Use that lifecycle as the control input for
terminal/weak/recovery permission arbitration. Keep `pipeline_orchestrator.py`
closed; do not change provider, retrieval, prompt, citation, or final-answer
behavior.

### 3. Post-Implementation Self-Review

`core/authority_lifecycle_runtime_arbitration.py` now builds the lifecycle and
exposes explicit control fields:

- `authority_lifecycle_required_recovery_allowed`;
- `authority_lifecycle_terminal_stop_may_preempt`;
- `authority_lifecycle_weak_corpus_may_own_path`;
- `authority_lifecycle_insufficient_partial_posture_explicit`;
- `authority_lifecycle_projection_used_as_control_input=false`.

`core/authoritative_source_action.py` filters terminal/weak admission blockers
through this lifecycle and attaches the lifecycle trace to the active
source-class recovery lifecycle. `core/controller_loop_spine.py` preserves
required recovery dispatch over terminal/weak checkpoint choices when the
lifecycle says recovery remains allowed.

### 4. Validation Decision

Validation remained offline. Focused tests prove terminal stop and weak corpus
cannot preempt required authoritative recovery without a requirement-bound
controller blocker or explicit insufficient/partial posture. Broader
authoritative-source/controller tests passed after updating older AG-68
assertions from raw fail-closed behavior to controller-owned arbitration.

### 5. Final Recommendation Review

The SSA-style AG-68H failure family is addressed at the arbitration layer. The
next layer to open should be post-dispatch source-fit/final evidence survival
if live validation later shows candidates return but do not survive into final
evidence/citations. Provider/search review remains closed until both cases
prove dispatch and acquisition failure rather than arbitration failure.

## Protected Surfaces

Remained closed:

- provider routing, provider selection, provider depth;
- retrieval, ranking, filtering;
- prompt wording;
- citation and final-answer behavior;
- Author, Analyst, Economist, Scrutineer, legal answer, and follow-up behavior;
- broad `core/pipeline_orchestrator.py` rewrites;
- live validation.
