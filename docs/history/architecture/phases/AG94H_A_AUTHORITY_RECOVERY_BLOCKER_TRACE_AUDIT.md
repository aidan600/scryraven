Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG94H_A_AUTHORITY_RECOVERY_BLOCKER_TRACE_AUDIT).

# AG-94H-A Authority Recovery Blocker Trace Audit

Status: audit complete.
Phase type: deep offline audit, trace provenance, synthetic fixture
reproduction.
Validation boundary: repo-visible code, repo-tracked docs, and synthetic
fixtures only. No live provider, model, search, retrieval, secret, `.env`, DB
row, raw provider payload, raw prompt, private log, cache, full raw trace, local
output packet, or private artifact access was used.

## Executive Verdict

The remaining weak-corpus block is not owned by
`core/official_canonical_recovery_execution_admission.py` alone.

The CLI runtime path does call official/canonical recovery execution admission,
but the last observed offline block is owned by the source-class lifecycle and
controller loop spine:

```text
authoritative_source_action_orchestrator_adapter
-> authoritative_source_action._authority_runtime_arbitration
-> official_canonical_recovery_execution_admission
-> source_class_recovery_lifecycle.record_source_class_recovery_lifecycle
-> source_class_recovery_controller.decide_source_class_recovery
-> controller_loop_spine._build_source_class_checkpoint_gate_trace
```

The audit fixture produces Task 2 result **D**:
official/canonical admission succeeds, but the source-class lifecycle blocks
later and `source_class_recovery_execution_attempted` remains false.

The root provenance split is that admission and visibility can infer required
legal/current classes from `source_class_satisfaction_status`, while
authority-lifecycle arbitration, query-acquisition planning, and the
source-class controller require those classes to be present in
`missing_expected_source_classes`, `source_class_gap_candidates`,
`unfulfilled_source_classes`, or `partial_source_classes`. If the class is
status-only, report/export diagnostics can rehydrate it after the fact, while
the controller decision that needed it saw an empty missing-class list.

Decision: **B. Focused behavior repair needed**. Do not patch in this audit.

## Sanitized Post-PR138/139 Live Rerun Signal

Sanitized query:

```text
What official legal or regulatory source currently lists which preservatives or
additives are permitted in infant formula sold in Denmark? Answer from
official/current regulatory sources if available.
```

Sanitized live facts supplied in the phase prompt:

- `admission_considered=true`
- `admission_eligible=false`
- `admission_used=false`
- `admission_skip_reason=existing_runtime_blocker`
- `admission_blockers=weak_corpus_recovery_owns_path; blocked_by_corpus_weak`
- `admission_acquisition_path_visible=true`
- required classes included `legal_or_regulatory_text` and
  `official_current_rules`
- source obligation status was `official_current_required_unmet`
- recovery queries existed; query fallback no longer injected U.S. legal terms
- acquisition repair was considered but blocked by an existing runtime blocker
- source-class recovery execution was not attempted
- `official_authority_acquisition_plan` was empty
- `weak_corpus_coexistence_reason=unknown`

## Why This Is An Audit Rather Than Another Fix

AG-94F-R1 already repaired the standalone admission rule: structured
unsatisfied strong authority classes plus executable recovery queries should
subordinate weak-corpus blockers. The post-PR live signal contradicted that
rule, so this phase traced field provenance instead of assuming that the
standalone helper was still the owner.

The audit found multiple compatibility lanes and projection surfaces with
similar field names. A behavior fix before identifying the runtime consumer
would risk repairing a diagnostic while the controller still blocks execution.

## Field Provenance Map

| Field | Producer / module | Immediate inputs | Control or diagnostic | Runtime effect and staleness |
| --- | --- | --- | --- | --- |
| `admission_considered` | `build_official_canonical_recovery_execution_admission` | obligation facts from explicit facts or merged recommendation/runtime trace | control inside admission; exported diagnostic later | Affects `admission_eligible`; export copies nested packet. Not canonical RunAuthority. |
| `admission_eligible` | same admission helper | considered, required status, unsatisfied classes, acquisition path, recovery queries, slot, blockers | control | Becomes `admission_used`; export is diagnostic. |
| `admission_used` | same admission helper | `admission_eligible` | control in `authoritative_source_action`; diagnostic in export | Feeds `official_canonical_source_class_slot_available`; report may not prove executor dispatch. |
| `admission_skip_reason` | same admission helper `_skip_reason` | admission predicates and blockers | diagnostic/control explanation | Does not dispatch by itself; can be stale if export reads an older packet. |
| `admission_blockers` | same admission helper `_admission_blockers` | existing blockers, recommendation blockers, runtime trace blockers, weak-corpus coexistence, authority lifecycle blocker | control | Blocks admission. Weak blockers are filtered only when admission sees supported unsatisfied classes plus queries or lifecycle allows recovery. |
| `admission_acquisition_path_visible` | same admission helper | recommendation path flag/reason/trigger fields, query-acquisition trace, native source-class recommendation visibility | control predicate | True means a path is visible, not that execution is allowed. |
| `required_source_classes` | admission helper; report export also recomputes in `_source_obligation_custody_fields` | admission facts, acquisition facts, trace required fields, action envelope | mixed | In reports this is projection. It may include classes the source-class controller did not receive. |
| `unsatisfied_required_source_classes` | admission helper; report export also recomputes | admission satisfaction evaluation plus trace active missing fields | mixed | In reports this can be rehydrated from admission even when lifecycle input was empty. |
| `source_obligation_status` | visibility export `_source_obligation_status_for_export`; controller decision has separate derivation | required/unsatisfied/admitted/lifecycle fields | diagnostic projection | Sounds authoritative but does not itself authorize recovery. |
| `acquisition_repair_considered` | `apply_official_canonical_recovery_query_acquisition` | obligation facts | query-acquisition control for repair lane; exported diagnostic | Only matters if repair can mutate the recommendation. |
| `acquisition_repair_eligible` | same query-acquisition helper | required status, acquisition classes, intents/promoted queries, blockers | query-acquisition control | False prevents query-acquisition repair from adding queries. |
| `acquisition_repair_used` | same query-acquisition helper | eligible plus executable queries | query-acquisition control | Mutates recommendation only when true. Native recovery queries can exist anyway. |
| `acquisition_repair_skip_reason` | same query-acquisition helper `_skip_reason` | acquisition predicates and blockers | diagnostic explanation | `existing_runtime_blocker` can coexist with native source-class queries. |
| `official_authority_acquisition_plan` | query-acquisition helper via `build_official_authority_acquisition_plan` | `acquisition_classes`, subject, context | repair-lane diagnostic/control only if repair uses it | Empty when `acquisition_classes` is empty. Not the native source-class query list. |
| `source_class_recovery_queries` | native source-class recommendation, SearchJudgment consumer, query-acquisition repair, lifecycle trace; export previews combine several sources | recommendation queries, active lifecycle queries, admission previews | control before export; diagnostic in export | Report query visibility does not prove the lifecycle had matching missing classes. |
| `weak_corpus_coexistence_reason` | admission or query-acquisition helper | weak corpus present, supported classes, executable queries, no surviving weak blockers | diagnostic | Remains unknown when the layer computing it does not see classes/queries or still has weak blockers. |
| `source_class_recovery_eligible` | visibility alias of `active_source_class_recovery_eligible` | source-class lifecycle trace | diagnostic alias | Runtime control field is active lifecycle eligibility. |
| `source_class_recovery_used` | visibility alias of `active_source_class_recovery_used` | lifecycle/executor trace | diagnostic alias | Execution uses active lifecycle fields. |
| `source_class_recovery_execution_attempted` | visibility alias of `active_source_class_recovery_execution_attempted` | lifecycle/executor trace; sync helper | diagnostic alias | Indicates executor attempt, not admission. |
| `source_class_recovery_skip_reason` | visibility alias of `active_source_class_recovery_skip_reason` | source-class controller decision | diagnostic alias | Priority can hide `no_missing_expected_source_class` behind `blocked_by_weak_corpus_recovery`. |
| `candidate_return_status` | authority lifecycle candidate fit / execution sync; export can derive `not_attempted` | execution attempted flag and recovered result count | post-dispatch diagnostic; used by recovery-decision projection | Not a source-class dispatch input. |
| `candidate_acquisition_considered` | recovery candidate acquisition defaults/executor sync | source-class execution candidate-acquisition lane | post-dispatch diagnostic | False when source-class execution never attempted. |
| `candidate_acquisition_eligible` | same candidate acquisition lane | candidate acquisition predicates | post-dispatch diagnostic | Not a pre-dispatch weak-corpus owner. |
| `candidate_acquisition_used` | same candidate acquisition lane | candidate acquisition eligibility | post-dispatch diagnostic | False when no source-class execution. |
| `acquisition_attempted` | authority lifecycle execution sync / candidate acquisition defaults | source-class execution and candidate acquisition | post-dispatch diagnostic | False when controller/spine did not dispatch. |
| `controller_recovery_decision` | runtime `build_controller_recovery_decision`; visibility export can hydrate if absent | lifecycle/ledger/candidate/export fields | runtime control when passed to runner; projection in report if hydrated | Report field may be `hydrated_authoritative_lifecycle_projection`, not an actual runtime trace packet. |
| `authority_lifecycle_required_recovery_allowed` | `build_authority_runtime_arbitration().to_trace_fields()` | required recovery, recovery action allowed, recovery queries, hard blockers, insufficient posture | control | Filters weak blockers and drives spine fallback. Not canonical RunAuthority; controller-owned compatibility. |
| `authority_lifecycle_weak_corpus_may_own_path` | same arbitration helper | weak corpus used/present and not required recovery allowed | control | If true, weak blockers survive filters. |
| `authority_lifecycle_execution_state` | same arbitration helper from `AuthorityLifecycleExecution` | recovery action allowed and hard blockers | control/diagnostic | `not_requested` can occur even while admission later sees required classes. |
| `authority_lifecycle_execution_blocked` | same arbitration helper | execution state | control for admission/spine | Admission treats lifecycle execution blocker as hard. |
| `authority_lifecycle_execution_blocker` | same arbitration helper | explicit lifecycle blockers | control/diagnostic | May be absent when the block is a weak-corpus ownership cycle rather than explicit blocker. |

None of these report/export fields is canonical EvidenceLedger custody by
itself. EvidenceLedger and RunAuthority projections are inputs to some lanes,
but the fields above are mostly compatibility-lane control fields or
diagnostic projections.

## Offline Reproduction Result

Added `tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py`.

The fixture uses a synthetic non-U.S. food/product-safety legal-regulatory
query, weak corpus, no terminal stop, no conflict ownership, no provider/depth
policy blocker, no hard budget cap, and executable recovery queries.

The key fixture shape is:

- `source_class_recovery_recommended=true`
- recovery queries exist
- `source_class_satisfaction_status` contains `legal_or_regulatory_text` and
  `official_current_rules` with secondary-only/unsatisfied status
- `missing_expected_source_classes=[]`
- `official_canonical_acquisition_path_visible=true`

Observed result:

- admission sees required/unsatisfied classes from status keys and returns
  `admission_used=true`
- query-acquisition repair is considered but not used, with an empty official
  authority acquisition plan because `acquisition_classes=[]`
- source-class lifecycle sees no missing expected class, preserves weak-corpus
  ownership, and emits
  `active_source_class_recovery_skip_reason=blocked_by_weak_corpus_recovery`
- controller loop spine emits `gate_reason=blocked_by_lifecycle`
- `source_class_recovery_execution_attempted=false`
- visibility export rehydrates `active_source_class_recovery_missing_classes`
  from admission/export fields even though lifecycle saw an empty list

Task 2 classification: **D. source-class lifecycle blocks later after admission
succeeds.**

This does not prove the live `admission_used=false` was impossible. It proves
that the repo-visible full handoff can produce the remaining weak-corpus block
after admission, and that report/export fields can make the lifecycle inputs
look richer than they were at control time.

## Weak-Corpus Blocker Ownership Chain

Where blockers are first introduced:

1. `core/authoritative_source_action.py::_acquisition_blockers` introduces
   `weak_corpus_recovery_owns_path` and `blocked_by_corpus_weak` for
   query-acquisition repair when weak corpus is present and weak-corpus query
   acquisition is not allowed.
2. `core/authoritative_source_action.py::_admission_blockers` introduces the
   same blockers for admission, then filters them through
   `AuthorityRuntimeArbitration.filter_blockers`.
3. `core/official_canonical_recovery_execution_admission.py::_admission_blockers`
   can also append weak-corpus blockers from existing/recommendation/runtime
   blocker lists or direct `corpus_weak`/`weak_corpus_recovery_used` facts.
4. `core/source_class_recovery_controller.py::decide_source_class_recovery`
   introduces `blocked_by_weak_corpus_recovery` or `blocked_by_corpus_weak`
   for the active source-class lifecycle.
5. `core/official_canonical_recovery_visibility_export.py` does not introduce
   runtime blockers, but copies and re-labels them for diagnostics.

Layer classification:

- source-class recommendation blockers: recommendation fields can carry
  `active_source_class_recovery_blockers` and
  `source_class_recovery_candidate_v2_blockers`
- existing admission blockers: `AuthoritativeSourceActionFacts` can carry
  `existing_admission_blockers`, but the orchestrator adapter currently does
  not populate them from a live output file
- authoritative-source action admission blockers: yes, `_admission_blockers`
  produces them
- AuthorityRuntimeArbitration lifecycle blockers: yes, via
  `weak_corpus_may_own_path` preserving weak blockers
- controller loop spine blockers: spine consumes lifecycle and reports
  `blocked_by_lifecycle`; it does not invent the weak blocker
- source-class lifecycle skip reasons: yes, source-class controller owns the
  active `blocked_by_weak_corpus_recovery` skip reason
- visibility/export-derived labels: yes, export copies/rehydrates fields and
  can hydrate `controller_recovery_decision`

Last opportunity to subordinate before
`source_class_recovery_execution_attempted=true`:

1. `authoritative_source_action._authority_runtime_arbitration` can make
   `authority_lifecycle_required_recovery_allowed=true`, causing weak blockers
   to be filtered.
2. `official_canonical_recovery_execution_admission` can admit the official slot.
3. `source_class_recovery_controller.decide_source_class_recovery` is the last
   practical gate before controller loop spine. It can suppress weak-corpus
   ownership only if it sees a strong missing class plus an answer-contract,
   official-canonical, or RunAuthority recovery slot.
4. After lifecycle emits `active_source_class_recovery_eligible=false`, the
   controller loop spine only blocks dispatch.

## Authority Lifecycle Circularity Audit

The circular dependency exists in a status-only required-class shape:

1. Required authority is visible in `source_class_satisfaction_status`, but not
   in `missing_expected_source_classes` / `unfulfilled_source_classes` /
   `partial_source_classes`.
2. `authoritative_source_action._required_source_classes` returns empty.
3. `_authority_runtime_arbitration` sets `required_recovery=false`,
   `recovery_action_allowed=false`, and
   `authority_lifecycle_required_recovery_allowed=false`.
4. Because weak corpus is present and required recovery is not allowed,
   `authority_lifecycle_weak_corpus_may_own_path=true`.
5. Query-acquisition repair has `acquisition_classes=[]` and can report
   `existing_runtime_blocker`.
6. Admission can still infer required classes from status keys and succeed, but
   `record_source_class_recovery_lifecycle` passes the original empty missing
   class list to the source-class controller.
7. `decide_source_class_recovery` sees no missing expected class, does not treat
   the official-canonical slot as usable, and preserves weak-corpus blockers.
8. The spine blocks with `blocked_by_lifecycle`.

Smallest conceptual break:

- Normalize structured strong authority obligations into the source-class
  lifecycle control input before weak-corpus arbitration and before
  source-class controller eligibility.
- In practical terms, the focused repair should make status-only
  official/current/legal required classes visible to
  `authoritative_source_action._required_source_classes`,
  query-acquisition `acquisition_classes`, and
  `source_class_recovery_controller` missing-class input, then prove that weak
  corpus still blocks ordinary non-authority queries.

Do not implement this as a broad orchestrator rewrite.

## Acquisition-Plan Emptiness Audit

`official_authority_acquisition_plan` is attached to the query-acquisition
repair lane, not to native source-class recovery execution.

`apply_official_canonical_recovery_query_acquisition` builds the plan from
`acquisition_classes`, and `acquisition_classes` is the intersection of:

- unsatisfied required classes;
- `missing_expected_source_classes`; and
- supported source-class context.

When the class is visible only through `source_class_satisfaction_status`,
`acquisition_classes=[]`, so the plan has:

```text
source_classes_required=[]
query_variants=[]
hard_domains=[]
soft_candidate_domains=[]
venue_families=[]
```

Native `source_class_recovery_queries` can still exist because they come from
the source-class recommendation, SearchJudgment consumer, or native query
generation path.

Classification: **secondary future repair / misleading diagnostic**, not the
primary active execution blocker. It becomes a real blocker only when the system
depends on query-acquisition repair to create the executable queries.

## Export / Report Diagnostic Consistency Audit

The official/canonical recovery visibility report mixes:

- admission payload from
  `official_canonical_recovery_execution_admission_trace`
- query-acquisition payload from
  `official_canonical_recovery_query_acquisition_trace`
- source-obligation custody fields recomputed in visibility export
- active source-class lifecycle fields
- authority lifecycle trace fields
- controller recovery decision fields, sometimes hydrated by export
- candidate acquisition/candidate return fields from lifecycle defaults or
  post-execution sync
- final evidence/citation survival fields

Fields that sound authoritative but can be projection-only or stale:

- `source_obligation_status`
- `required_source_classes`
- `unsatisfied_required_source_classes`
- `active_source_class_recovery_missing_classes` in the visibility export
- `controller_recovery_decision` when
  `controller_recovery_decision_projection_source=hydrated_authoritative_lifecycle_projection`
- `candidate_return_status=not_attempted`
- `official_authority_acquisition_plan`
- `source_class_recovery_queries` in export previews

The audit test proves one concrete inconsistency:

```text
lifecycle.active_source_class_recovery_missing_classes == []
export.active_source_class_recovery_missing_classes ==
  ["legal_or_regulatory_text", "official_current_rules"]
```

The export value is useful for review, but it is not what the lifecycle
controller consumed.

## Exact Modules / Functions That Own The Remaining Block

Primary remaining block:

- `core/source_class_recovery_controller.py::decide_source_class_recovery`
  emits `blocked_by_weak_corpus_recovery` when the controller input lacks a
  strong missing authority class.
- `core/source_class_recovery_lifecycle.py::record_source_class_recovery_lifecycle`
  passes the recommendation-derived missing-class list into the controller and
  records the resulting active lifecycle.
- `core/controller_loop_spine.py::_build_source_class_checkpoint_gate_trace`
  blocks dispatch once lifecycle eligibility is false.

Upstream provenance split:

- `core/authoritative_source_action.py::_required_source_classes` does not read
  `source_class_satisfaction_status` keys.
- `core/authoritative_source_action.py::_authority_runtime_arbitration` can
  therefore set `authority_lifecycle_required_recovery_allowed=false` while
  admission later sees required classes.
- `core/official_canonical_recovery_query_acquisition.py` requires visible
  `missing_expected_source_classes` for `acquisition_classes`.

Projection masking:

- `core/official_canonical_recovery_visibility_export.py::_source_obligation_custody_fields`
  rehydrates required/missing fields from admission/export inputs.

## Does Official Admission Participate In The CLI Runtime Path?

Yes.

`core/pipeline_orchestrator.py` calls
`build_authoritative_source_action_orchestrator_handoff`, which calls
`build_authoritative_source_action_facts_from_orchestrator_state`, then
`build_authoritative_source_obligation_state_and_action`. That function calls
`_try_execution_admission`, which delegates to
`build_official_canonical_recovery_execution_admission`.

The admission result is not the final dispatch owner. Its `admitted` boolean is
passed into `record_source_class_recovery_lifecycle` as
`official_canonical_source_class_slot_available`, then source-class lifecycle
and controller loop spine still decide whether execution is attempted.

## Do Report Diagnostics Match Admission Inputs?

Not reliably.

Admission inputs are the recommendation, runtime trace, obligation facts, and
existing blockers supplied at the action handoff. Visibility report fields are
assembled later from admission payload, acquisition payload, lifecycle fields,
and export recomputation.

In the audit fixture:

- admission input sees required classes through `source_class_satisfaction_status`
- source-class lifecycle input does not see missing expected classes
- visibility export later reports active missing classes by rehydrating them
  from admission/export fields

This means report fields can be more complete than the control input that
actually blocked dispatch.

If a live report shows `admission_used=false` while also showing required
classes and recovery queries, the next repair should first verify whether those
required classes and queries were present in the nested admission payload or
only in the broader visibility export.

## Why `weak_corpus_coexistence_reason` Remained Unknown

`weak_corpus_coexistence_reason` is computed separately in admission and
query-acquisition repair. It is non-null only when that specific layer sees:

- weak corpus present;
- supported official/current/legal/canonical classes;
- executable recovery queries; and
- no surviving weak-corpus blockers.

It is not recomputed from the final exported
`required_source_classes`/`source_class_recovery_queries` preview. Therefore it
can remain unknown when the export later shows required classes and queries,
because the layer that owned the reason did not see the same complete input or
still had weak-corpus blockers.

## Why `admission_acquisition_path_visible=true` Can Coexist With Block

`admission_acquisition_path_visible` is only one admission predicate. It can be
true because a native source-class recommendation or path flag is visible, while
`admission_used` remains false due to blockers. Even when admission succeeds,
the source-class lifecycle can still block if the controller input does not
contain the same required/missing class.

## Decision: B Focused Repair

Chosen option: **B. Focused behavior repair needed.**

Reason:

- The official admission helper participates in the CLI path.
- The full handoff fixture shows the remaining block can be owned after
  admission by source-class lifecycle/controller loop spine.
- The smallest conceptual fix is not a broad architecture decision, but it is
  also not a safe one-line audit change. It changes which status-only
  authority classes become control-visible.

## Recommended Next Prompt

```text
You are working in aidan600/scryraven.

Phase: AG-94H-B focused authority recovery lifecycle repair.

Use repo-visible files only. No live provider/model/search/retrieval calls. Do
not alter provider order, depth, query budgets, ranking/filtering, Author prose,
citations, package names, CLI/env/DB/session names, or rewrite
pipeline_orchestrator.py.

Implement the smallest behavior repair that makes status-only supported strong
authority obligations visible to the active source-class lifecycle before
weak-corpus arbitration. Specifically trace and repair the mismatch where
official/canonical admission and visibility can infer required classes from
source_class_satisfaction_status, but authoritative_source_action
_required_source_classes, query-acquisition acquisition_classes, and
source_class_recovery_controller missing-class input require
missing_expected_source_classes / unfulfilled / partial classes.

Start from tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py. Convert
the D-result fixture so admission, authority lifecycle, source-class lifecycle,
and controller loop spine all agree on legal_or_regulatory_text and
official_current_rules as missing required classes, and
source_class_recovery_execution_attempted can become true when the existing
executor seam is authorized. Preserve negative controls where no strong
authority obligation exists, no recovery query exists, terminal stop/conflict
/provider/depth/hard-cap blockers exist, or weak corpus is the only issue.

Do not run live calls. Run the AG-94H-A test, AG-94F-R1 admission tests,
AG-93E8-R1 acquisition handoff tests, AG-94B CLI trace-custody tests, and ruff.
```

## Protected / Closed Surfaces Kept Closed

Kept closed:

- live ScryRaven/proplex provider, model, search, or retrieval calls;
- secrets, `.env`, API keys, DB rows, raw provider payloads, raw prompts,
  private logs, caches, full raw traces, local output packets, private
  artifacts;
- provider swap, new provider integration, provider order, routing, selection,
  search depth, and search budget changes;
- ranking/filtering overhaul;
- Author prose, prompt, final-answer, citation behavior;
- package, CLI, env, database, and session renames;
- broad `core/pipeline_orchestrator.py` rewrite.

## Tests / Checks Run

- `py -m pytest -q tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py`
  - 3 passed
- `py -m pytest -q tests/test_ag94f_r1_weak_corpus_official_authority_admission.py`
  - 18 passed
- `py -m pytest -q tests/test_ag93e8_r1_weak_corpus_official_acquisition_handoff.py`
  - 8 passed
- `py -m pytest -q tests/test_ag94b_cli_official_current_recovery_trace_custody.py`
  - 6 passed
- `py -m ruff check .`
  - passed
- `py -m pytest -q tests`
  - 2914 passed, 1 deselected, 1 xfailed
- `py -m pre_commit run --all-files`
  - passed

`py -m pytest -q` at repo root was attempted and blocked during collection by
duplicate test module names under the local generated review artifact
`output/local_review/ag94g_review_20260611_153544/files/tests`. The tracked
test suite under `tests/` passed.

No live calls were run. Runtime behavior was not changed.
