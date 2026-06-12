# AG-94H-E Authority Lifecycle / Source-Class Recovery Parity Audit

Status: audit complete, offline reproduction added.

Phase type: architecture audit, static trace audit, and synthetic offline
reproduction. Runtime behavior was not repaired in this phase.

Validation boundary: repo-visible code, repo-tracked docs, the sanitized live
field summary from the phase prompt, and synthetic fixtures only. No live
ScryRaven/proplex provider, model, search, or retrieval calls were run. No
secrets, `.env`, API keys, DB rows, raw provider payloads, raw prompts, private
logs, caches, full raw traces, local output packets, or private artifacts were
inspected.

## Executive Verdict

AG-94H-E is not a local ordering bug. It is a systemic control-plane truth-owner
problem whose first concrete divergence is **legacy aggregate leakage**.

Exact classification: **B. Legacy aggregate leakage**.

The first divergent predicate is:

```text
core/authoritative_source_action.py::_evidence_fits_for_source_classes()
```

That helper converts `source_class_satisfaction_status=satisfied_strong` or a
positive `source_class_strong_satisfaction_counts` value into
`AuthorityEvidenceFit.authoritative(...)`. Then
`_build_authoritative_obligation_state()` evaluates the requirement as
fulfilled, and `_authority_runtime_arbitration()` sets:

```text
required_recovery=false
authority_lifecycle_recovery_needed=not_needed
authority_lifecycle_required_recovery_allowed=false
authority_lifecycle_execution_state=not_requested
```

This can happen while the source-class recovery lifecycle independently sees:

```text
source_class_recovery_recommended=true
active_source_class_recovery_eligible=true
active_source_class_recovery_missing_classes includes legal/current official classes
active_source_class_recovery_queries exist
```

The contradiction is real because `ControllerEvidenceLedger` and the
official-source bridge treat the same legacy aggregate/status signals as
non-custodial observability, not as selected authority evidence custody. In
other words, one lane says "legacy aggregate strong means satisfied," while the
custody lane says "legacy aggregate strong is not candidate/passport custody."

## Live Symptom Summarized

The sanitized live result after AG-94H-D had all of the recovery shape needed by
the source-class lane:

- source-class recovery eligible and active-source-class recovery eligible;
- missing classes included `legal_or_regulatory_text` and
  `official_current_rules`;
- source-class recovery queries existed;
- provider role was `source_class_recovery`;
- search depth was `basic`;
- attempt count was `1`;
- source-class recovery execution was not attempted;
- candidate acquisition was not attempted;
- final evidence/citation custody was `legacy_gap_observed`.

At the same time:

- `authoritative_source_action_trace.action_decision` was approved;
- source-class lifecycle summary said eligible, not used, not attempted, no
  blockers;
- `authority_lifecycle_recovery_needed=not_needed`;
- `authority_lifecycle_required_recovery_allowed=false`;
- `controller_recovery_decision=stop_legacy_custody_gap`;
- `controller_recovery_allowed_executor_action=no_recovery_executor_action`;
- the spine did not dispatch `RECOVER_MISSING_SOURCE_CLASS`;
- the runner projected
  `source_class_recovery_executor_dispatch_not_authorized`.

AG-94H-D did not move this blocker because its checkpointless dispatch repair is
intentionally gated by `authority_lifecycle_required_recovery_allowed=true`.
The live run failed before that precondition.

## Exact First Divergence

The first divergence is inside authority lifecycle obligation evaluation:

```text
authoritative_source_action._required_source_classes()
-> authoritative_source_action._evidence_fits_for_source_classes()
-> AuthoritativeSourceObligationState.evaluate()
-> AuthoritativeSourceObligationState.missing_authority_requirements()
-> authoritative_source_action._authority_runtime_arbitration()
```

The responsible predicate is:

```python
if _positive_count(strong_counts, source_class) or status == "satisfied_strong":
    fits.append(AuthorityEvidenceFit.authoritative(...))
```

That predicate is in
`core/authoritative_source_action.py::_evidence_fits_for_source_classes()`.

Because the fit is authoritative, `missing_authority_requirements()` returns an
empty tuple. `_authority_runtime_arbitration()` then computes:

```python
required_recovery = bool(requirement is not None)  # False
recovery_action_allowed = bool(
    required_recovery and recommendation.get("source_class_recovery_recommended")
)  # False
```

That is the exact split between:

- source-class recommendation/eligibility/action decision: recovery approved;
- authority lifecycle arbitration: recovery not needed and not allowed.

## Hypothesis Results

| Hypothesis | Result | Finding |
| --- | --- | --- |
| A. `_build_authoritative_obligation_state()` decides no requirement is missing because observability reports `satisfied_strong` or strong counts. | Confirmed | It builds requirements from missing/source-class fields, then evaluates them as fulfilled because `_evidence_fits_for_source_classes()` creates authoritative fits. |
| B. `_evidence_fits_for_source_classes()` converts legacy/status-only strong counts into `AuthorityEvidenceFit.authoritative`. | Confirmed | This is the first responsible predicate. |
| C. `_authority_runtime_arbitration()` sets required recovery false because `missing_authority_requirements()` is empty. | Confirmed | It only treats missing requirements as required recovery. |
| D. `recovery_action_allowed` becomes false even though source-class recovery is recommended, because it is gated by `required_recovery`. | Confirmed | The recommendation remains approved by the source-class lifecycle, but authority lifecycle has no approved recovery action. |
| E. `lifecycle.update(authority_arbitration.to_trace_fields())` overwrites or conflicts with source-class lifecycle fields. | Confirmed as a conflict projection, not the first divergence | It overlays authority lifecycle fields onto an already eligible source-class lifecycle without reconciling the two. |
| F. `sync_authority_lifecycle_execution_from_source_class_trace()` turns the dispatch block into an authority lifecycle execution blocker after the fact. | Confirmed as downstream projection | The runner calls the execution-block projection only after the spine does not authorize dispatch. |
| G. `ControllerRecoveryDecision` stops on legacy gap because recovered result count is zero/unknown and candidate acquisition was not attempted. | Partly confirmed | The stop is driven by `legacy_gap_observed` plus failure to subordinate the gap; subordination fails because authority lifecycle did not approve required recovery. |

## Field Provenance Map

| Stage | Owner | Input fields consumed | Output fields emitted | Role | May say recovery needed/eligible/allowed/executed/satisfied | Downstream treatment |
| --- | --- | --- | --- | --- | --- | --- |
| 1. RunAuthorityContract / source requirement signal | `core/run_authority_contract.py::RunAuthorityContract` and `source_class_facts_from_run_contract_projection()` | `source_requirements`, strictness, required source class/currentness | contract projection, required/missing source-class facts | Canonical RunAuthority owner for source requirements | May declare a source class required; does not execute recovery | Consumed by EvidenceLedger, QueryPlan hints, compatibility source-class facts |
| 2. RunAuthoritySearchJudgment / recommendation signal | `core/run_authority_search_judgment.py`; consumer in `core/run_authority_search_judgment_consumers.py::apply_search_judgment_to_source_class_recovery_recommendation()` | canonical search judgment decision, target source classes, recommended queries, existing recommendation | `source_class_recovery_recommended`, `missing_expected_source_classes`, `source_class_recovery_queries`, `run_authority_search_judgment_consumed` | Canonical judgment consumed through compatibility lane | May recommend or block source-class recovery; may set advisory `authority_lifecycle_required_recovery_allowed` on recommendation | Treated as control input by authoritative-source action and source-class lifecycle |
| 3. AuthoritativeSourceAction shaping | `core/authoritative_source_action.py::build_authoritative_source_obligation_state_and_action()` | recommendation, source-class observability, SearchJudgment projection, obligation facts, blockers, budget facts | action trace, action decision, active lifecycle, authority lifecycle trace, admission/acquisition traces | RunAuthority-subordinated compatibility control lane | May approve source-class action via lifecycle; may say authority recovery needed/allowed through arbitration | Consumed by orchestrator handoff, controller loop spine, visibility export |
| 4. OfficialSourceObligationBridge | `core/official_source_obligation_bridge.py::apply_official_source_obligation_bridge()` | required official/current classes, status/count observability, existing custody projection | `missing_expected_source_classes` additions, bridge trace, `official_current_source_custody` | Bridge/control adapter with custody-aware demotion of aggregates | May make required classes visible and recovery recommended; does not prove satisfaction from aggregate counts | Recommendation output feeds authoritative action and lifecycle; trace is diagnostic/control-adjacent |
| 5. OfficialCanonicalQueryAcquisition | `core/official_canonical_recovery_query_acquisition.py::apply_official_canonical_recovery_query_acquisition()` | required classes, unsatisfied classes, visible missing classes, existing queries, blockers | acquisition trace, optional added/promoted recovery queries, acquisition plan | Query-acquisition compatibility control lane | May add queries and mark acquisition repair used; may say existing source class satisfied | Recommendation output feeds lifecycle; plan/export is diagnostic if native queries already exist |
| 6. OfficialCanonicalExecutionAdmission | `core/official_canonical_recovery_execution_admission.py::build_official_canonical_recovery_execution_admission()` | required classes, status/count observability, recovery queries, attempt cap, blockers, authority lifecycle trace | `admission_used`, required/unsatisfied classes, recovery slot, admission blockers | Execution admission compatibility control lane | May allow one official/canonical recovery slot; currently may treat legacy strong aggregate as satisfied | Feeds `official_canonical_source_class_slot_available` into source-class lifecycle |
| 7. AuthorityLifecycleArbitration | `core/authoritative_source_action.py::_authority_runtime_arbitration()` and `core/authority_lifecycle_runtime_arbitration.py::build_authority_runtime_arbitration()` | obligation state missing requirements, recommendation, recovery queries, blockers, terminal/weak-corpus facts | `authority_lifecycle`, `authority_lifecycle_recovery_needed`, `authority_lifecycle_required_recovery_allowed`, execution state | Controller-owned compatibility control | May say recovery needed, allowed, blocked, or not requested; may declare existing evidence satisfying | Treated as control by admission, source-class lifecycle overlay, controller decision, and spine |
| 8. SourceClassRecoveryLifecycle | `core/source_class_recovery_lifecycle.py::record_source_class_recovery_lifecycle()` and `core/source_class_recovery_controller.py::decide_source_class_recovery()` | recommendation, missing classes, queries, weak corpus, budget, provider/depth facts, official slot | `active_source_class_recovery_eligible`, missing classes, queries, action envelope, provider role, attempt count | Legacy active compatibility controller | May say recovery eligible and approved pending executor; does not know candidate custody | Treated as control by spine, runner, controller decision, export |
| 9. Authority execution sync | `core/authority_lifecycle_execution.py::sync_authority_lifecycle_execution_from_source_class_trace()` and `source_class_recovery_execution_blocked_if_needed()` | authority lifecycle, source-class execution/runner results, dispatch authorization | execution attempted/blocked fields, candidate return status after attempted execution, skip reason | Projection/control-adjacent execution sync | May project executed or blocked after dispatch/non-dispatch | Consumed by export, controller decision, diagnostics; runner mutates trace on non-dispatch |
| 10. ControllerRecoveryDecision | `core/controller_recovery_decision.py::build_controller_recovery_decision()` | ledger custody, source obligation status, classes, lifecycle approval, authority lifecycle allowed/action, budget, candidate status | `controller_recovery_decision`, retry flag, allowed executor action, legacy gap subordination flag | ControllerEvidenceLedger-owned recovery decision table | May allow retry or stop; may preserve legacy gap as final success block | Consumed by provider-search allocation and source-class executor gate; visibility export may hydrate a projection |
| 11. ControllerLoopSpine | `core/controller_loop_spine.py::build_controller_loop_spine_result()` and `_build_source_class_checkpoint_gate_trace()` | checkpoint trace, source-class lifecycle, authority lifecycle required recovery, action envelope, blockers, slot, candidate attempt state | `authorized_dispatch`, gate trace, `source_class_executor_dispatched` | Legacy active compatibility dispatch authority | May dispatch `RECOVER_MISSING_SOURCE_CLASS`; cannot dispatch checkpointless path without authority lifecycle required recovery allowed | Runner consumes `authorized_spine_action` as final mechanical dispatch input |
| 12. SourceClassRecoveryRunner | `core/source_class_recovery_runner.py::run_source_class_recovery_dispatch()` | lifecycle trace, controller decision, authorized spine action, provider-search allocation result | execution result, non-dispatch blocker projection | Bounded dispatcher/executor caller | May execute only when spine action is `RECOVER_MISSING_SOURCE_CLASS`; otherwise records dispatch-not-authorized | Calls source-class executor or records block; no policy repair |
| 13. SourceClassRecoveryExecutor | `core/source_class_recovery_executor.py::execute_source_class_recovery_action()` | controller action, lifecycle trace, controller recovery decision, provider/search callable | attempted execution, result counts, candidate acquisition fields, authority execution sync | Bounded executor with controller gate | May execute recovery and project attempted/candidate status | Mutates lifecycle trace; does provider/search only when called by runner |

## Offline Reproduction

Added:

```text
tests/test_ag94h_e_authority_lifecycle_source_class_parity_audit.py
```

The fixture uses only synthetic sanitized fields:

- required source classes:
  `legal_or_regulatory_text`, `official_current_rules`;
- source-class recovery recommended;
- missing expected source classes include both required classes;
- source-class recovery queries exist;
- source-class lifecycle becomes eligible;
- active attempt count is `1`;
- execution attempted and used are false;
- candidate acquisition and acquisition attempted are false;
- ControllerEvidenceLedger/final custody fields show `legacy_gap_observed`;
- legacy observability says both required classes are `satisfied_strong` with
  positive strong counts.

The tests prove:

1. `_evidence_fits_for_source_classes()` emits authoritative fits from legacy
   aggregate/status observability.
2. `AuthoritativeSourceObligationState.missing_authority_requirements()` is
   empty.
3. Source-class lifecycle/action decision remains approved and eligible.
4. `authority_lifecycle_required_recovery_allowed=false` and
   `authority_lifecycle_recovery_needed=not_needed`.
5. Official/canonical admission reports `existing_source_class_satisfied`.
6. `ControllerRecoveryDecision` returns `stop_legacy_custody_gap`.
7. Controller loop spine does not authorize `RECOVER_MISSING_SOURCE_CLASS`.
8. The runner projects
   `source_class_recovery_executor_dispatch_not_authorized` and marks authority
   lifecycle execution blocked after the no-dispatch path.

## Classification: A/B/C/D/E/F

Chosen classification: **B. Legacy aggregate leakage**.

Reason:

- The first responsible function is not the spine, runner, or lifecycle merge.
- The first responsible predicate is the conversion of legacy aggregate/status
  observability into `AuthorityEvidenceFit.authoritative(...)`.
- That predicate lets authority lifecycle declare recovery not needed before
  ControllerEvidenceLedger, official-current custody, candidate passport, or
  final selected authority evidence custody proves selected authority evidence.

Secondary systemic risk:

- **D. Multiple truth-owner conflict** is present as an architecture risk, but
  not the exact phase classification. The bridge/custody lane and authority
  lifecycle lane currently own overlapping satisfaction predicates with
  different custody semantics.

## Why AG-94H-D Did Not Move The Live Blocker

AG-94H-D repaired a later dispatch authorization gap. Its checkpointless path in
`controller_loop_spine.py::_authority_lifecycle_approved_checkpointless_source_class_dispatch()`
requires:

```text
authority_lifecycle_required_recovery_allowed=true
authority lifecycle controls recovery
approved recovery action
eligible source-class lifecycle
queries
unmet source obligation
supported missing source class
available slot
no prior execution/candidate acquisition
no hard blocker
```

The sanitized live run failed the first predicate:

```text
authority_lifecycle_required_recovery_allowed=false
```

Therefore AG-94H-D could not authorize checkpointless dispatch, even though the
source-class lifecycle and action decision were eligible/approved.

## Whether This Is Local Or Systemic

This is systemic, but locally repairable.

It is systemic because several layers can declare satisfaction or recovery
posture:

- source-class lifecycle can say recovery is eligible;
- authoritative source action can say the action is approved;
- authority lifecycle can say recovery is not needed;
- official-source bridge can say legacy aggregate strong is not custody;
- admission can say existing source class is satisfied;
- ControllerEvidenceLedger can say final evidence/citation custody has a legacy
  gap;
- visibility export can hydrate missing/required classes and controller
  decisions after the fact.

It is locally repairable because the first bad predicate is narrow:

- demote legacy `satisfied_strong` and positive strong counts in
  `authoritative_source_action._evidence_fits_for_source_classes()` from
  authority-satisfying evidence to non-custodial aggregate observability unless
  candidate/passport/official-current custody proves the selected authority
  evidence;
- apply the same custody rule to
  `official_canonical_recovery_execution_admission._authority_evidence_fits_for_source_class()`;
- keep the source-class lifecycle and AG-94H-D spine repair unchanged except for
  tests proving the corrected authority lifecycle precondition.

No broad `pipeline_orchestrator.py` rewrite is required to understand or repair
this bug.

## Systemic Complexity / Collapse-Risk Appendix

Answer: the system is showing collapse risk at the recovery-control boundary,
not because there are many files, but because multiple layers can make
overlapping satisfaction and recovery decisions from different evidence
semantics.

Necessary layers:

- RunAuthorityContract;
- EvidenceLedger / ControllerEvidenceLedger custody;
- RunAuthoritySearchJudgment;
- SourceClassRecoveryRunner and SourceClassRecoveryExecutor as bounded executor
  surfaces;
- FinalAnswerPacket / Author handoff for final evidence and answer readiness.

Compatibility scaffolding:

- AuthoritativeSourceAction;
- OfficialSourceObligationBridge;
- OfficialCanonicalQueryAcquisition;
- OfficialCanonicalExecutionAdmission;
- SourceClassRecoveryLifecycle;
- AuthorityLifecycleArbitration;
- ControllerRecoveryDecision;
- ControllerLoopSpine;
- OfficialCanonicalRecoveryVisibilityExport;
- AuthorityCandidatePassportProjection.

Redundant or dangerous layers:

- any authority lifecycle or admission satisfaction predicate that consumes
  legacy aggregate source-class counts/status as authority custody;
- visibility/export hydration that can sound authoritative without being the
  runtime decision trace;
- overlapping source-obligation satisfaction checks split between bridge,
  admission, authority lifecycle, and controller decision.

Smallest next simplification after the bug is understood:

1. Demote legacy aggregate/status observability in authority lifecycle and
   admission to the same non-custodial role already used by
   `OfficialCurrentSourceCustodyState`.
2. Make authority lifecycle satisfaction consume candidate/passport/custody
   proof, or explicitly mark legacy aggregate fits as lower-tier/context-only.
3. Delete or subordinate the duplicate aggregate-satisfaction conversion once
   tests prove the bridge/custody owner is consumed.

Do not start with a broad rewrite. Delete or demote one redundant truth owner at
a time.

### Complexity Matrix

| Layer | Owner of truth? | Controls runtime? | Observer/export only? | May block recovery? | May allow recovery? | May declare source obligation satisfied? | May consume legacy aggregate counts? | May consume candidate/passport custody? | May consume final evidence/citation survival? | Current overlap/conflict risk | Recommended demotion/deletion/consolidation candidate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RunAuthorityContract | Yes, source requirements | Indirect | No | No | No | No | No | No | No | Low | Keep canonical; ensure projections are consumed downstream. |
| RunAuthoritySearchJudgment | Yes, search/recovery recommendation | Indirect via consumer | No | Yes | Yes | No | No | Limited projection facts | No | Medium | Keep canonical; retire duplicate recommendation flags when consumers read canonical state directly. |
| AuthoritativeSourceAction | Compatibility truth owner | Yes | No | Yes | Yes | Yes, currently via obligation state | Yes, currently dangerous | Not enough | No | High | Demote satisfaction to custody-aware bridge/ledger; keep as handoff adapter. |
| OfficialSourceObligationBridge | Custody-aware bridge | Yes, by mutating recommendation | No | Yes via blockers | Yes, by adding missing classes | Yes, but aggregate strong is demoted | Yes, as aggregate-only diagnostics | Yes through `OfficialCurrentSourceCustodyState` projection | No | Medium | Promote custody semantics; later remove when source-class expectation consumes obligation facts natively. |
| OfficialCanonicalQueryAcquisition | Query repair compatibility owner | Yes | No | Yes | Yes | Yes, currently via local kernel satisfaction | Yes, currently risky | Not enough | No | High | Align satisfaction with bridge custody; later delete if native query generation covers obligations. |
| OfficialCanonicalExecutionAdmission | Execution admission owner | Yes | No | Yes | Yes | Yes, currently via local kernel satisfaction | Yes, currently risky | Not enough | No | High | Align with custody owner; avoid aggregate-satisfied skip without custody. |
| SourceClassRecoveryLifecycle | Legacy active controller | Yes | No | Yes | Yes | No | Only through normalization input | No | No | Medium | Keep as executor-lane lifecycle until RunAuthority dispatch permission replaces it. |
| AuthorityLifecycleArbitration | Controller-owned compatibility truth owner | Yes | No | Yes | Yes | Yes | Yes, exact leak | Not enough | No | Very high | Focused repair target: remove aggregate authority satisfaction or require custody proof. |
| ControllerRecoveryDecision | ControllerEvidenceLedger decision table | Yes | No | Yes | Yes | Yes through source obligation status | Indirect, now guarded for final counts | Yes, through ledger/custody fields | Yes, guarded after AG-94H-D | Medium | Keep short term; demote once RunAuthority/ledger owns retry/stop state consumed by runner. |
| ControllerLoopSpine | Legacy dispatch authority | Yes | No | Yes | Yes | No | No | No | No | High | Next demotion candidate after satisfaction repair: runner should consume canonical recovery permission. |
| SourceClassRecoveryRunner | Bounded dispatcher | Yes, mechanical | No | Yes, no spine action | Yes, calls executor | No | No | No | No | Low | Keep as bounded executor caller; remove policy from context over time. |
| ControllerEvidenceLedger | Yes, custody gap owner | Yes through decision table | No | Yes, final-success gap | Yes when custody supports retry | Yes, with custody semantics | Yes, but as legacy gap/aggregate only | Yes | Yes | Medium | Promote as satisfaction source for authority lifecycle; avoid duplicate legacy lanes. |
| OfficialCanonicalRecoveryVisibilityExport | No | No, except hydrated projection can be reused by humans/tests | Yes | No direct runtime block | No direct runtime allow | Can hydrate satisfied/unmet labels | Yes | Yes if present | Yes | Medium | Mark hydrated decisions/projections clearly; never feed export back as control. |
| AuthorityCandidatePassportProjection | Custody projection, not owner | Indirect if consumed | Mostly projection | Yes if consumed by custody decision | Yes if candidate selected | Yes when tied to ledger/final selected evidence | No | Yes | Yes | Medium | Consolidate with EvidenceLedger/FinalAnswerPacket selected authority evidence. |
| FinalAnswerPacket / Author handoff | Yes for final answer readiness and selected evidence handoff | Yes for final answer | No | Yes for final readiness | Yes for final answer | Yes only with selected evidence/citation custody | No | Yes via packet/ledger references | Yes | Medium | Keep canonical; do not let pre-final aggregates bypass packet custody. |

## Recommended Next Behavior Repair

Recommended next phase: **AG-94H-F focused authority lifecycle custody repair**.

Narrow behavior target:

- In `core/authoritative_source_action.py`, change
  `_evidence_fits_for_source_classes()` so legacy `satisfied_strong` and
  positive `source_class_strong_satisfaction_counts` do not create
  `AuthorityEvidenceFit.authoritative(...)` without selected candidate/passport
  or official-current custody proof.
- In `core/official_canonical_recovery_execution_admission.py`, align
  `_authority_evidence_fits_for_source_class()` with the same custody rule.
- Preserve the existing bridge behavior that records those aggregate fields as
  candidate aggregate-only / diagnostic observability.
- Keep AG-94H-D's checkpointless dispatch predicates intact; the repair should
  make the correct `authority_lifecycle_required_recovery_allowed=true`
  precondition possible.

Negative controls to preserve:

- strong custody proof should still satisfy authority;
- weak/secondary-only statuses should remain lower-tier context;
- terminal stop, conflict ownership, provider policy/depth blocker, hard cap,
  no query, and unsupported source class should still block recovery;
- no provider/search/depth/query/ranking/Author/final-answer/citation behavior
  changes.

## Recommended Simplification / Demotion Target

First demotion target:

```text
legacy source_class_satisfaction_status / source_class_strong_satisfaction_counts
as authority-satisfying evidence inside AuthorityLifecycleArbitration and
OfficialCanonicalExecutionAdmission
```

Demotion rule:

```text
aggregate status/count observability may be diagnostic or context-only;
candidate/passport/custody proof owns authority satisfaction.
```

Second demotion target after the focused repair:

```text
ControllerLoopSpine as the final recovery dispatch truth owner
```

Do not attempt the second demotion until the satisfaction semantics are aligned.

## Tests / Checks Run

Passed locally:

- `py -m pytest -q tests/test_ag94h_e_authority_lifecycle_source_class_parity_audit.py`
  - `3 passed`
- `py -m pytest -q tests/test_ag94h_c_recovery_executor_dispatch_authorization_audit.py`
  - `18 passed`
- `py -m pytest -q tests/test_authority_lifecycle_execution_ag69c.py`
  - `8 passed`
- `py -m pytest -q tests/test_authority_lifecycle_projection_control_ag69e.py`
  - `9 passed`
- `py -m pytest -q tests/test_ag94h_a_authority_recovery_blocker_trace_audit.py`
  - `12 passed`
- `py -m pytest -q tests/test_ag94b_cli_official_current_recovery_trace_custody.py`
  - `6 passed`
- `py -m ruff check .`
  - passed
- `py -m pytest -q tests`
  - `2944 passed, 1 deselected, 1 xfailed`
- `py -m pre_commit run --all-files`
  - passed: merge-conflict check, EOF fixer, trailing whitespace, YAML, ruff,
    and detect-secrets.

## Closed Surfaces Preserved

Kept closed:

- live ScryRaven/proplex provider, model, search, and retrieval calls;
- secrets, `.env`, API keys, DB rows, raw provider payloads, raw prompts,
  private logs, caches, full raw traces, local output packets, and private
  artifacts;
- provider swap, provider integration, provider order, routing, selection,
  search depth, and search budget changes;
- query generation and query text changes;
- ranking/filtering/source-classification overhaul;
- Author prose, Author prompts, final-answer behavior, and citation behavior;
- package, CLI, env, database, and session renames;
- broad `core/pipeline_orchestrator.py` rewrite.

`core/pipeline_orchestrator.py` line delta in this audit: `0`.
