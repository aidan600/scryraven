# AG-76C-CS Runner-Owned Recovered Candidate Stream Extraction

Date: 2026-05-28

## Scope And Non-Goals

AG-76C-CS is an Architecture Groove / Prove Mode extraction phase for the
recovered/source-class candidate stream used by recovered-evidence selection.

The licensed scope is parity-preserving extraction only:

- move source-class recovery candidate stream assembly to a runner-owned helper;
- preserve the existing `retrieval_stage == "source_class_recovery"` inclusion
  rule;
- preserve AG-75A-Y/Z allocation-result candidate inclusion through
  Controller-authorized custody;
- keep `pipeline_orchestrator.py` as handoff/plumbing only;
- keep `core.recovered_evidence_visibility` as the recovered-evidence visibility
  boundary and selector.

This phase does not change provider/search behavior, query strategy,
source-class/currentness classifier behavior, candidate-fit semantics, source
sufficiency decisions, retry/stop/provider allocation decisions, final evidence
selection semantics, final-answer prose, Author behavior, Author prompt
semantics, citation formatting, citation selection, Scrutineer behavior,
Economist behavior, follow-up behavior, live validation, direct IRS handling,
raw/private data handling, or broad `pipeline_orchestrator.py` domain logic.

## AG-76C-FE Prerequisite Verification

Current local `main` contained AG-76C-FE / PR #26 before implementation:

```text
341d524 Merge pull request #26 from aidan600/codex/ag76c-fe-final-evidence-bundle-extraction
5fa7814 Update AG-69 guards for final evidence builder
ec56a49 Extract final evidence bundle builder
```

Required AG-76C-FE artifacts were present:

- `docs/architecture/AG76C_FE_FINAL_EVIDENCE_BUNDLE_EXTRACTION.md`
- `core/final_evidence_bundle_builder.py`
- `tests/test_ag76c_final_evidence_bundle_builder.py`

Required AG-75C artifacts remained present:

- `docs/architecture/AG75C_LOCAL_AUTHORITY_GATE_RETIREMENT_AUDIT.md`
- `core/recovered_evidence_visibility.py` defines
  `apply_controller_recovered_evidence_visibility(...)`
- `core/pipeline_orchestrator.py` no longer defines
  `_apply_recovered_evidence_visibility(...)`

Required runner and allocation custody artifacts were present:

- `core/source_class_recovery_runner.py`
- `core/source_class_recovery_executor.py`
- `core/allocation_result_candidate_custody.py`
- `core/allocation_candidate_selection_activation.py`

AG-76C-FE named runner-owned recovered/source-class candidate stream and
remaining compatibility plumbing as the next deletion target.

## Old Responsibility Replaced

Before AG-76C-CS, `core.recovered_evidence_visibility` assembled the candidate
stream by scanning `all_passages` for `retrieval_stage == "source_class_recovery"`
and appending allocation-result candidates from the AG-75A-Z activation helper.

`pipeline_orchestrator.py` also performed two direct source-class recovery stage
scans for recovery-source diagnostics and passive runtime projection handoff.

AG-76C-CS moved those mechanical scans behind a runner-owned helper.

## New Helper Contract

New module:

```text
core.source_class_recovery_candidate_stream
```

New helper functions:

- `source_class_recovery_passage_candidates(...)`
- `runner_owned_recovered_candidate_stream(...)`
- `is_source_class_recovery_passage(...)`

The helper is mechanical. It assembles candidate records already present in
runner/allocation/custody state. It does not retrieve, route, rank, classify,
evaluate fit, choose final evidence, decide source sufficiency, decide retry or
stop posture, write final answer text, package Author prompts, or format/select
citations.

## Candidate Stream Input Contract

`source_class_recovery_passage_candidates(...)` accepts:

- `all_passages`, preserving existing passage objects and order;
- an optional stage predicate, defaulting to the old
  `retrieval_stage == "source_class_recovery"` behavior.

`runner_owned_recovered_candidate_stream(...)` accepts:

- `all_passages`;
- `lifecycle_trace`;
- an optional allocation candidate source, defaulting to
  `allocation_result_candidates_for_existing_selection_corridor(...)`;
- an optional stage predicate.

No raw provider payloads, prompts, DB rows, logs, caches, or output packets are
required or exposed.

## Candidate Stream Output Contract

The helper returns:

- source-class recovery passage candidates in the same order and shape as the
  old `all_passages` scan;
- allocation-result candidates appended after recovered passage candidates;
- the same allocation candidate records produced by the existing AG-75A-Z
  activation helper;
- no final evidence decision, source sufficiency decision, retry/stop decision,
  Author payload, citation payload, or raw provider payload.

## Allocation Inclusion Rules

Allocation-result candidates still enter only through
`allocation_result_candidates_for_existing_selection_corridor(...)`, which is
backed by `build_allocation_result_candidate_custody_projection(...)`.

Unauthorized, unexecuted, unadmitted, lower-tier, unclassified, or non-current
allocation candidates remain excluded by the existing AG-75A-Y/Z custody and
activation rules.

## Controller Authorization Boundary

Decision ownership remains unchanged:

- `ControllerRecoveryDecision` owns retry/stop/provider-review posture and
  allocation authorization.
- `ControllerEvidenceLedger` owns custody/disposition interpretation.
- `AnswerContract` owns obligation/posture state.
- `AuthorityLifecycle` and the existing recovered-evidence boundary own current
  fit/selection semantics.
- `core.final_evidence_bundle_builder` owns mechanical final evidence packaging.

The new helper only assembles already-authorized candidate records.

## Visibility Boundary Preservation

`core.recovered_evidence_visibility` still owns:

- `apply_controller_recovered_evidence_visibility(...)`;
- `apply_recovered_evidence_visibility_boundary(...)`;
- recovered-evidence duplicate handling;
- source-class match and lower-tier/currentness boundary behavior;
- visibility decision trace fields.

It no longer owns runner candidate stream construction. Its
`recovered_evidence_selection_candidates(...)` compatibility function delegates
to `runner_owned_recovered_candidate_stream(...)`.

## Trace And Export Observer Boundary

Trace/projection/export layers remain observers. The orchestrator now passes
`source_class_recovery_passage_candidates(...)` output into passive projection
handoff instead of constructing the source-class recovery passage stream inline.

No runtime trace projection or official/canonical export helper became a
candidate stream decision owner.

## Protected Surfaces Kept Closed

AG-76C-CS kept closed:

- provider routing, provider selection, provider depth, provider escalation,
  provider swaps, new providers, and Linkup policy;
- query strategy and source-constraint repair;
- retrieval ranking/filtering behavior;
- source-class/currentness classifier behavior;
- candidate-fit semantics;
- final evidence selection semantics;
- final answer behavior;
- Author behavior and Author prompt semantics;
- citation formatting and citation selection;
- prompt behavior;
- follow-up behavior;
- Scrutineer and Economist behavior;
- live validation;
- direct IRS hardcoding;
- raw/private data, DB rows, caches, logs, secrets, full traces, and output
  packets.

## Remaining Orchestrator Responsibilities

`pipeline_orchestrator.py` remains responsible for:

- computing existing phase-local runtime values;
- calling the source-class recovery runner dispatch;
- passing existing `all_passages` and lifecycle state into mechanical helpers;
- invoking final evidence bundle construction;
- passing recovered passage candidates into existing diagnostics/projection
  consumers;
- preserving existing provider/search/model/Author/citation behavior;
- recording runtime trace, export, persistence, and outcome payloads.

It no longer constructs the recovered/source-class candidate stream directly.

## Remaining Visibility Responsibilities

`core.recovered_evidence_visibility` remains responsible for the
recovered-evidence visibility boundary and selection behavior. It no longer
imports the allocation candidate activation helper or performs the
`all_passages` source-class recovery stage scan as the candidate stream owner.

## Line-Count Delta

`core/pipeline_orchestrator.py` line count:

- before AG-76C-CS: 6973
- after AG-76C-CS: 6972
- delta: -1 line

The small delta is expected: this phase moved compatibility stream ownership
behind a named helper while retaining orchestrator handoff sites.

## Behavior Parity Evidence

Added focused parity coverage in
`tests/test_ag76c_cs_runner_owned_candidate_stream.py`:

- runner-owned stream matches the old stage scan order and shape;
- duplicate source-class recovery URLs remain present in old order;
- missing or unrelated retrieval stages remain excluded;
- Controller-authorized allocation candidates append after recovered passages;
- unauthorized allocation candidates are excluded;
- lower-tier allocation candidates still cannot satisfy current official
  obligations;
- `apply_controller_recovered_evidence_visibility(...)` output matches the old
  helper-fed boundary output;
- final evidence bundle output remains unchanged for the recovered visibility
  handoff;
- passive runtime projection receives equivalent runner-owned recovered passage
  input;
- static ownership checks prove the orchestrator no longer contains
  `retrieval_stage` candidate scans and the visibility helper no longer owns
  allocation/stage-scan assembly;
- static protected-surface checks prove the new helper does not call provider,
  query, classifier, fit, Author, final-answer, citation, or raw payload
  surfaces.

Existing AG-75C, AG-75A-Z, and AG-76C-FE tests were also exercised directly
where the local pytest launcher was unavailable.

## Demolition Ledger

1. Old recovered/source-class candidate stream construction path targeted:
   `core.recovered_evidence_visibility.recovered_evidence_selection_candidates`
   and two direct `pipeline_orchestrator.py` source-class recovery passage scans.
2. New runner-owned helper/module contract:
   `core.source_class_recovery_candidate_stream` owns mechanical source-class
   passage extraction and allocation-candidate appending.
3. Old `all_passages` `retrieval_stage` scan:
   moved from visibility candidate stream ownership and subordinated in
   `pipeline_orchestrator.py` diagnostics/projection handoffs.
4. Allocation-result candidate inclusion:
   preserved through `allocation_result_candidates_for_existing_selection_corridor`
   and AG-75A-Y/Z Controller custody.
5. Behavior parity tests:
   `tests/test_ag76c_cs_runner_owned_candidate_stream.py`, plus direct
   execution of relevant AG-75C, AG-75A-Z, and AG-76C-FE tests.
6. Remaining orchestrator responsibilities:
   runtime value production, runner dispatch, final bundle calls, diagnostics,
   projection/export/persistence, Author/final-answer handoff.
7. Remaining `recovered_evidence_visibility.py` responsibilities:
   recovered-evidence visibility boundary and existing selection/fit semantics.
8. Next deletion target:
   a narrow runner-owned compatibility handoff for recovered passage diagnostics
   and passive projection consumers, or another mechanical consumer handoff that
   removes more final evidence compatibility plumbing without touching
   Author/citation/provider/query/classifier/fit behavior.
9. Net complexity impact:
   one small mechanical helper module added; stream ownership removed from
   visibility/orchestrator compatibility code; parity/static tests added.
10. Pipeline line-count delta:
   -1 line in `core/pipeline_orchestrator.py`.

## Next Deletion Target

The next deletion target is not Author, citation, provider/search, query,
classifier, fit, or final-answer behavior. The next safe target is another
narrow runner-owned recovered passage consumer handoff around diagnostics and
passive projection, or a similarly mechanical compatibility seam that keeps
ControllerRecoveryDecision, ControllerEvidenceLedger, AnswerContract, and
AuthorityLifecycle as decision owners.
