# AG-69F Controller Lifecycle Forced-Corridor Validation

Scope: offline forced-corridor lifecycle validation and classification only.
No live ProPlex runs, provider/model/search calls, provider routing, provider
selection, provider depth, retrieval/ranking/filtering changes, prompt wording,
citation/final-answer behavior, Author/Analyst/Economist/Scrutineer/follow-up
behavior, legal answer behavior, direct IRS/SSA special casing, or broad
pipeline orchestration changes were made.

> Status note, AG-95E: This document records historical
> Controller/ControllerLoopSpine-era behavior. For current source-class recovery
> dispatch, use AG-95C/AG-95D/AG-95E:
> `SourceClassRecoveryRunner` dispatches from canonical
> `authority_lifecycle.recovery_action`; `authorized_spine_action`,
> ControllerLoopSpine, and ControllerRecoveryDecision are
> diagnostic/compatibility surfaces for source-class dispatch, not runner
> authority.

## Goal

Validate the end-to-end controller-owned `AuthorityLifecycle` through forced
official/current/canonical/current-primary corridors and classify the remaining
failure layer, if any.

North star:

- Controller decides.
- Orchestrator executes.
- Trace/projection/export layers observe.

## Decision Records

### 1. Reconnaissance Review

AG-69A through AG-69E already established the lifecycle contract, terminal/weak
arbitration, execution entrypoint/blocker lifecycle, recovered-candidate
fit/final-evidence visibility, and projection-as-control retirement. The
remaining AG-69F question was not a new repair question; it was whether forced
corridors could be classified without any forbidden lifecycle state.

The existing local surfaces were sufficient:

- `core/authority_lifecycle_contract.py`
- `core/authority_lifecycle_runtime_arbitration.py`
- `core/authority_lifecycle_execution.py`
- `core/authority_lifecycle_candidate_visibility.py`
- `core/controller_loop_spine.py`
- `core/recovered_evidence_visibility.py`
- `core/official_canonical_recovery_visibility_export.py`

### 2. Validation Design Decision

Add a pure sanitized classifier,
`core/authority_lifecycle_forced_corridor_classification.py`, and focused
offline tests. The classifier consumes already-built lifecycle projections and
returns a compact packet for review. It does not dispatch retrieval, choose a
provider, rank/filter sources, alter prompts, cite sources, or change final
answers.

The validation harness forces the lifecycle corridors with fake/offline source
fixtures and existing lifecycle helpers. No live validation is authorized or
used.

### 3. Post-Harness Self-Review

The classifier records, per corridor:

- required authority and `requirement_id`;
- existing evidence fit and lower-tier context state;
- recovery needed/action state;
- terminal stop and weak-corpus states;
- execution state and structured execution blocker;
- candidate acquisition/return/fit state;
- selected authority evidence or structured candidate rejection;
- final evidence state and explanation;
- citation eligibility projection;
- final posture;
- exactly one lifecycle terminal path;
- forbidden lifecycle state codes, if any;
- remaining failure layer.

Static guards confirm the classifier imports no provider/search/prompt/Author
surfaces and is not imported by `pipeline_orchestrator.py`.

### 4. Validation Result Decision

Offline validation passed. Each forced corridor produced exactly one terminal
path and no forbidden lifecycle state.

| Case | Required Authority | Terminal Path | Lifecycle Outcome | Remaining Failure Layer |
| --- | --- | --- | --- | --- |
| SSA-style terminal stop | `official_current_rules` | `approved_action_executed` | Terminal stop remains observed but cannot preempt lifecycle-allowed recovery. | none for lifecycle |
| SSA-style weak corpus | `official_current_rules` | `approved_action_executed` | Weak-corpus path remains observed but cannot own the path while required recovery is lifecycle-allowed. | none for lifecycle |
| Executor not dispatched | `official_current_rules` | `controller_hard_blocker` | Approved recovery that does not dispatch records a requirement-bound `controller/lifecycle` execution blocker. | blocked by controller lifecycle |
| IRS-style returned secondary candidate | `official_current_rules` | `approved_action_executed` | Candidate return triggers requirement-bound fit and structured rejection; final evidence absence is explained. | candidate fit / visibility layer |
| IRS-style returned accepted candidate at capacity | `official_current_rules` | `approved_action_executed` | Returned candidate cannot vanish; non-selection produces explained final-evidence absence. | final evidence visibility layer |
| Canonical technical docs | `primary_source_documents` | `approved_action_executed` | Returned canonical fixture becomes selected authority evidence and final evidence visible. | none for lifecycle |
| Legal/current-primary offline fixture | `legal_or_regulatory_text` | `approved_action_executed` | Current-primary/legal authority can be represented offline and become selected authority evidence. | none for lifecycle |
| Lower-tier context fallback | `official_current_rules` | `controller_insufficient_partial_posture` | Lower-tier evidence remains context/partial and does not satisfy the required authority. | controller insufficient/partial posture |
| Legacy projection/export poison | `official_current_rules` | `approved_action_executed` | Runtime classification follows lifecycle execution state, not poisoned legacy projection/export fields. | none for lifecycle |

### 5. Final Recommendation Review

AG-69F validates the controller-owned lifecycle offline. No provider/search,
prompt, citation, or Author repair is justified by this phase. If product/live
behavior remains uncertain, the next step should be an explicitly approved live
validation gate, not an unscoped repair.

Recommended next opening surface if live/product evidence shows a remaining
failure: bounded citation survival / source-claim fit, or
follow-up-as-AnswerContract starting-state integration, depending on the live
failure layer. Keep provider routing, retrieval/ranking/filtering, prompt
wording, and final-answer behavior closed until such evidence exists.

## Live Validation Recommendation

Live validation is recommended only as a separate review gate if offline proof
is considered insufficient for product confidence. It was not used in AG-69F.

Proposed live gate, if approved later:

- Exact queries:
  - `What is the current Social Security taxable maximum wage base for 2026, and what official source supports it? Keep the answer concise.`
  - `What is the current IRS standard mileage rate for business use of a car in 2026, and what official source supports it? Keep the answer concise.`
- Maximum ProPlex runs: 2 total, one per query.
- Local ignored output packet path:
  `output/ag69f_controller_lifecycle_forced_corridor_live_packet.md`
- Redaction plan: include final answers, cited URLs, visible source sections,
  compact sanitized lifecycle/export fields, and unavailable-telemetry notes
  only. Exclude `.env`, API keys/secrets, DB rows, raw provider payloads, raw
  prompts, full traces, private logs, caches, and unrelated generated outputs.
- Decision the live run will make: whether lifecycle-selected authority
  evidence survives into product-visible final evidence/citations, or whether
  the remaining failure layer is acquisition/provider result, candidate fit,
  final evidence visibility, citation survival/source-claim fit, or Author
  evidence-bound posture.
- Stop condition: stop after the two approved runs or immediately if the run
  would require provider/search/prompt/citation/final-answer behavior changes.

## Protected Surfaces

Remained closed:

- provider routing, provider selection, provider depth;
- retrieval, ranking, filtering;
- prompt wording;
- citation rendering and final-answer behavior;
- Author, Analyst, Economist, Scrutineer, legal answer, and follow-up behavior;
- direct IRS/SSA special casing;
- broad `core/pipeline_orchestrator.py` changes;
- live validation.

## Behavior Changes

Runtime behavior changed: no.

Added behavior is limited to an offline sanitized classifier and tests. The
classifier is not imported by `pipeline_orchestrator.py` and has no control
path into provider/search/prompt/citation/final-answer behavior.
