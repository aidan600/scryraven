Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG94H_B_AUTHORITY_RECOVERY_LIFECYCLE_REPAIR).

# AG-94H-B Authority Recovery Lifecycle Repair

Status: implemented as an offline fixture-backed behavior repair.

Validation boundary: repo-visible code, repo-tracked docs, and synthetic fixtures
only. No live ScryRaven/proplex provider, model, search, retrieval, secret,
`.env`, DB row, raw provider payload, raw prompt, private log, cache, full raw
trace, local output packet, or private artifact access was used.

## Executive Verdict

AG-94H-B repairs the AG-94H-A lifecycle/controller gap. Status-only supported
strong authority classes are now normalized into the active source-class
lifecycle control input before weak-corpus arbitration. In the repaired
full-handoff fixture, official/canonical admission succeeds, authority lifecycle
recovery is allowed, the active source-class lifecycle is eligible and pending,
and the controller loop spine dispatches the source-class executor when the
checkpoint names the recovery action.

The repair is bounded. It does not generate queries, retrieve, route providers,
change provider order, change search depth, rank/filter sources, alter prompts,
change citations, or change final-answer behavior.

## AG-94H-A Audit Finding Being Repaired

AG-94H-A found result D:

- official/canonical admission could infer required classes from
  `source_class_satisfaction_status`;
- `authority_lifecycle_required_recovery_allowed` and the source-class
  lifecycle/controller path could still see no missing class;
- weak corpus could retain ownership through
  `blocked_by_weak_corpus_recovery`;
- `source_class_recovery_execution_attempted` stayed false because dispatch
  never reached the executor.

The root mismatch was that status-only strong authority obligations were visible
to admission/export but absent from active lifecycle control input.

## Exact Normalization Rule

Append a status-only class to `missing_expected_source_classes` only when all of
these conditions hold:

- `source_class_recovery_recommended=true`;
- executable `source_class_recovery_queries` already exist;
- the class is one of:
  `official_current_rules`, `legal_or_regulatory_text`,
  `current_primary_or_official`, `primary_source_documents`,
  `archival_primary_text`;
- `source_class_satisfaction_status` says the class is non-strong, such as
  `expected_but_only_secondary`, `satisfied_weak`, `weakly_satisfied`, or
  `unsatisfied`;
- `source_class_strong_satisfaction_counts` has no positive count for the
  class;
- no status source says `satisfied_strong`.

Unsupported status keys are ignored. Strongly satisfied classes are ignored. No
query means no promotion.

## Files And Functions Changed

- `core/source_class_authority_status_normalization.py`
  - New pure helper for bounded status-only strong authority normalization.
- `core/authoritative_source_action.py`
  - `_required_source_classes()` now reads the normalization helper so
    authority lifecycle arbitration sees the same supported status-only
    obligations as admission.
  - `build_authoritative_source_obligation_state_and_action()` passes
    satisfaction status/count observability into the lifecycle input when the
    recommendation packet lacks those maps.
  - Existing terminal/conflict facts are forwarded to the source-class
    lifecycle controller.
- `core/source_class_recovery_controller.py`
  - `build_source_class_recovery_controller_input()` appends normalized
    status-only supported strong authority classes before
    `decide_source_class_recovery()`.
  - Terminal stop and conflict ownership are explicit lifecycle blockers.
- `core/source_class_recovery_lifecycle.py`
  - `record_source_class_recovery_lifecycle()` accepts and forwards terminal
    stop and conflict ownership facts.
- `tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py`
  - Converted the AG-94H-A D-result fixture into AG-94H-B behavior regression
    coverage and added negative controls.

## Why This Is Not A Broad Orchestrator Or Controller Rewrite

The repair does not touch `core/pipeline_orchestrator.py` and does not redesign
the controller loop spine. It changes only the lifecycle/controller input
construction and the authoritative-source required-class extraction needed for
the existing source-class lifecycle consumer to receive the same authority
obligation that admission already recognized.

The old path is subordinated rather than bypassed: `decide_source_class_recovery`
still decides eligibility, and the controller loop spine still requires an
approved recovery checkpoint before dispatch.

## Why Weak Corpus Still Matters

Weak corpus still blocks ordinary or unsupported cases:

- no strong authority status keys;
- unsupported status-only source classes;
- supported class already satisfied strongly;
- supported class with no recovery queries;
- terminal stop;
- conflict ownership;
- provider policy blocker;
- search-depth escalation blocker;
- prior attempt cap.

Weak corpus no longer owns the path only when a supported stronger authority
obligation remains unsatisfied and executable source-class recovery queries
already exist.

## Query-Acquisition Plan Status After Repair

For the status-only AG-94H-B fixture, native `source_class_recovery_queries` are
the active path. `official_authority_acquisition_plan` remains empty because
query acquisition still requires explicit visible
`missing_expected_source_classes` before it plans additional query variants.

That emptiness is diagnostic-only for this repair. It does not block lifecycle
approval when native source-class recovery queries already exist. Explicit
missing-class fixtures still produce a non-empty official-authority acquisition
plan through the existing query-acquisition lane.

## Diagnostics Changed

No new report/export diagnostic fields were added.

The meaningful diagnostic change is that existing active lifecycle fields now
reflect the control input actually consumed by the source-class controller:

- `active_source_class_recovery_missing_classes` includes normalized supported
  status-only classes;
- `active_source_class_recovery_eligible=true`;
- `active_source_class_recovery_skip_reason=null`;
- `active_source_class_recovery_official_canonical_admitted=true`;
- `authority_lifecycle_required_recovery_allowed=true`;
- `authority_lifecycle_weak_corpus_may_own_path=false`.

## Protected And Closed Surfaces Kept Closed

Kept closed:

- live provider/model/search/retrieval calls;
- secrets, `.env`, API keys, DB rows, raw provider payloads, raw prompts,
  private logs, caches, full raw traces, local output packets, and private
  artifacts;
- provider swap, provider integration, provider order, routing, selection,
  search depth, and search budget changes;
- ranking/filtering overhaul;
- Author prose, prompt, final-answer, and citation behavior;
- package, CLI, env, database, and session renames;
- broad `core/pipeline_orchestrator.py` rewrite.

`core/pipeline_orchestrator.py` line delta: `0`.

## Tests And Checks Run

Passed locally:

- `py -m pytest -q tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py`
  - `12 passed`
- `py -m pytest -q tests/test_ag94f_r1_weak_corpus_official_authority_admission.py`
  - `18 passed`
- `py -m pytest -q tests/test_ag93e8_r1_weak_corpus_official_acquisition_handoff.py`
  - `8 passed`
- `py -m pytest -q tests/test_ag94b_cli_official_current_recovery_trace_custody.py`
  - `6 passed`
- `py -m pytest -q tests/test_source_class_recovery.py tests/test_source_class_recovery_controller.py tests/test_official_canonical_recovery_execution_admission_ag50b.py`
  - `75 passed`

No live calls were run.

## Recommended Next Validation

Run exactly one live rerun of `food_regulatory_non_us`.

Success signal:

- source-class lifecycle is eligible and official/canonical admitted;
- `source_class_recovery_execution_attempted` moves past false if executor
  dispatch occurs;
- if provider/candidate acquisition still fails, classify that next blocker
  without running the full rotating set.
