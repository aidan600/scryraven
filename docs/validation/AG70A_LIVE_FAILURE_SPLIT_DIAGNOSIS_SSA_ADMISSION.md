# AG-70A Live Failure Split Diagnosis / SSA Admission Repair

Scope: Architecture Groove / Prove Mode, Path B. This phase performs a
repo-grounded split diagnosis of the two AG-69F-LV live failures and repairs
only the SSA-style admission/query-surfacing lane.

Branch: `codex/ag70a-live-failure-split-diagnosis-ssa-admission`

Base commit: `f857169` (`Merge pull request #131 from aidan600/codex/ag69f-bounded-live-lifecycle-validation`)

No live ProPlex/provider/model/search validation was used in AG-70A. The local
ignored AG-69F-LV packet was read as sanitized review material only and was not
committed.

## Decision Records

### 1. Reconnaissance Review

AG-69A through AG-69F established controller-owned authority lifecycle
ownership for requirement modeling, terminal/weak arbitration, recovery
execution, recovered-candidate fit/visibility, projection-as-control retirement,
and offline forced-corridor classification. The AG-69F-LV committed validation
doc and local sanitized packet show two different remaining surfaces:

- SSA 2026 wage base: required official/current recovery was not admitted.
- IRS 2026 mileage rate: required recovery was admitted, execution was reached,
  and candidates returned, but candidate fit/visibility did not yield accepted
  readable official/current evidence.

The local packet was marked `LOCAL/UNTRACKED - DO NOT COMMIT`, ignored by git,
and contained compact sanitized diagnostics only.

### 2. Split-Diagnosis Decision

The two AG-69F-LV failures do not share a proven root cause.

| Query | Admission | Execution | Candidates | Candidate fit/visibility | Remaining layer |
| --- | --- | --- | --- | --- | --- |
| SSA 2026 taxable maximum wage base | `admission_used=false`, `recovery_query_count=0` | `source_class_recovery_execution_attempted=false` | none | not evaluated | admission/query surfacing |
| IRS 2026 standard mileage rate | `admission_used=true`, `recovery_query_count=2` | `source_class_recovery_execution_attempted=true` | `recovered_result_count=114`, `accepted_url_count=11` | `candidate_official_or_canonical_count=1`, accepted/readable official/canonical count `0` | candidate fit / visibility |

Evidence: SSA fails before an executable recovery action exists
(`official_canonical_acquisition_path_not_visible`,
`missing_executable_recovery_query`). IRS already has an admitted recovery action
and returned candidates, then fails at
`canonical_candidate_returned_not_accepted`.

### 3. Pre-Implementation Repair Decision

Chosen repair lane: SSA-style lifecycle admission/query surfacing.

The narrow root cause repaired here is that lifecycle-valid upstream recovery
query candidates can be visible in answer-contract evidence state, but remain
passive diagnostics unless promoted into the source-class recovery
recommendation. Admission must spend recovery only from that lifecycle-owned
executable query path, not from trace/export previews.

Repair summary:

- surface answer-contract `next_queries` as recovery query candidates in
  `AuthoritativeSourceActionFacts`;
- promote generic upstream official/current/canonical candidates into
  `source_class_recovery_queries` during official/canonical query acquisition;
- keep passive candidate previews out of execution admission until promoted into
  the lifecycle-owned recommendation;
- preserve the structured `missing_executable_recovery_query` lifecycle blocker
  when no executable query can be produced.

### 4. Post-Implementation Self-Review

Changed runtime files are limited to:

- `core/authoritative_source_action.py`
- `core/authoritative_source_action_orchestrator_adapter.py`
- `core/official_canonical_recovery_query_acquisition.py`
- `core/official_canonical_recovery_execution_admission.py`

The change does not call providers, route providers, choose provider depth,
rank/filter retrieval results, alter prompts, classify returned candidates,
render citations, or change final-answer behavior. It does not special-case SSA
or IRS; the promotion rule is generic for official/current/canonical query
intent.

### 5. Validation Result Decision

Focused AG-70A offline tests prove:

- SSA-shaped required official/current recovery promotes a generic upstream
  query candidate into an executable lifecycle recovery query.
- Required recovery with upstream candidates does not end as
  `missing_executable_recovery_query`.
- Query surfacing feeds official/canonical acquisition path visibility and
  admission.
- Admission does not use passive projection previews as source of truth.
- No-query recovery records a requirement-bound controller/lifecycle blocker.
- Terminal-stop and weak-corpus gates cannot preempt lifecycle-allowed recovery.
- Lower-tier evidence remains context/partial and does not satisfy the
  official/current requirement.
- IRS candidate-fit/visibility behavior is not repaired in this phase.
- Protected provider/search/prompt/citation/final-answer surfaces remain closed.

AG-69A-F and AG-69F-LV remain coherent: AG-70A opens the AG-69F-LV recommended
SSA admission/arbitration follow-up while leaving the IRS next layer for a later
candidate-fit/visibility phase.

### 6. Final Recommendation Review

AG-70A should be reviewed as an SSA-style admission/query-surfacing repair only.
The next layer for IRS, if opened later, is candidate fit / accepted-readable
visibility for an official/canonical candidate that was returned but not
accepted or selected. Provider routing, provider selection, provider depth,
retrieval ranking/filtering, prompt wording, citation rendering, and final-answer
behavior should remain closed unless a later phase explicitly opens them.

## Surfaces Left Untouched

- provider routing, provider selection, provider depth;
- retrieval ranking/filtering;
- prompt wording;
- citation rendering and final-answer behavior;
- Author, Analyst, Economist, Scrutineer, legal-answer, and follow-up behavior;
- direct IRS/SSA special casing;
- IRS candidate-fit/visibility repair;
- broad `core/pipeline_orchestrator.py` domain logic;
- live validation.

## Tests Added/Changed

Added:

- `tests/test_ag70a_live_failure_split_diagnosis_ssa_admission.py`

Relevant existing AG-69A-F, AG-50/52/68, and official/current lifecycle tests
remain the regression set for this repair.
