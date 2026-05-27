# AG-69D Recovered Candidate Fit / Visibility Integration

Scope: offline controller-owned post-execution candidate-fit and final-evidence
visibility integration only. No live ProPlex runs, provider/model/search calls,
provider routing, provider selection, provider depth, retrieval/ranking/filtering
policy, prompt wording, citation rendering, final-answer behavior, legal answer
behavior, follow-up behavior, or broad pipeline orchestration change was made.

## Goal

Make `AuthorityLifecycle` the source of truth after source-class recovery
execution returns accepted/readable candidates. A returned candidate must become
requirement-bound candidate fit or a structured requirement-bound rejection, and
returned/accepted candidates that do not become final authority evidence must
produce an explained final-evidence absence.

## Decision Records

### 1. Reconnaissance Review

AG-69C already recorded `execution_state=attempted` and projected result counts
into `authority_lifecycle`. The gap was post-execution: recovered visibility
could report candidate-return counters while `candidate_fit.fit_state` stayed
`not_evaluated`, leaving no requirement-bound explanation for why returned
candidates did or did not survive as final authority evidence.

### 2. Pre-Implementation Decision

Add a pure lifecycle-owned candidate-fit/visibility processor and route the
existing recovered-evidence visibility boundary through it. Keep
`pipeline_orchestrator.py` as plumbing and do not move provider, retrieval,
ranking, filtering, prompt, citation, or final-answer behavior into this phase.

### 3. Post-Implementation Self-Review

`core/authority_lifecycle_candidate_visibility.py` now records:

- candidate return status;
- accepted URL count;
- requirement-bound candidate fit state;
- selected authority evidence records;
- structured requirement-bound candidate rejections;
- final evidence state and explanation;
- citation eligibility as a lifecycle projection.

Legacy recovered-visibility fit strings and counts are projected from the
lifecycle candidate-fit state when an `authority_lifecycle` is present.

### 4. Validation Decision

Validation remained offline. Focused AG-69D tests prove returned candidates
cannot remain unevaluated, accepted URLs alone do not satisfy authority,
matching candidates become selected authority evidence, rejected candidates get
structured lifecycle rejection records, lower-tier/context evidence remains
context only, and the real executor path with fake candidates reaches the
post-execution visibility handoff.

### 5. Final Recommendation Review

The IRS-style recovered-candidate visibility gap is now represented at the
controller lifecycle layer. The next failure layer to open should be final
citation/synthesis visibility if future offline or approved live validation
shows selected final authority evidence still does not survive to citations.

## Protected Surfaces

Remained closed:

- provider routing, provider selection, provider depth;
- retrieval, ranking, filtering;
- prompt wording;
- citation rendering and final-answer behavior;
- Author, Analyst, Economist, Scrutineer, legal answer, and follow-up behavior;
- broad `core/pipeline_orchestrator.py` domain logic;
- direct IRS/SSA special casing;
- live validation.
