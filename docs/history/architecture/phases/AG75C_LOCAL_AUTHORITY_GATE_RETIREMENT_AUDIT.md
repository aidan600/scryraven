Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG75C_LOCAL_AUTHORITY_GATE_RETIREMENT_AUDIT).

# AG-75C Local Authority Gate Retirement Audit

Date: 2026-05-28

## Scope

AG-75C is a local authority gate retirement audit and deletion wave for the
post-AG-75A-Z provider/search allocation corridor. It is not provider expansion,
query repair, classifier/currentness repair, candidate-fit repair, prompt work,
Author/citation/final-answer behavior work, IRS hardcoding, live validation, or
a broad `pipeline_orchestrator.py` rewrite.

The licensed protected surface is local authority gate retirement: static and
focused dynamic audit, deletion/subordination of obsolete local gates, extraction
of mechanical helper code out of `pipeline_orchestrator.py`, and tests proving
Controller-owned state remains the decision owner.

## AG-75A-Z Prerequisite Verification

Current `main` contained AG-75A-Z / PR #23 before implementation:

```text
db03310 Merge pull request #23 from aidan600/codex/ag75a-z-allocation-candidate-disposition-selection
8c25417 Make AG-75A-Z allocation candidates operational
92c1428 Add AG-75A-Z allocation candidate selection activation
```

Required artifacts were present:

- `docs/history/architecture/phases/AG75A_Z_ALLOCATION_CANDIDATE_DISPOSITION_SELECTION.md`
- `core/allocation_candidate_selection_activation.py`
- `core/allocation_result_candidate_custody.py`
- `core/controller_recovery_decision.py`
- `core/controller_evidence_ledger.py`
- `core/source_class_recovery_runner.py`
- `core/pipeline_orchestrator.py`
- `tests/test_ag75a_z_allocation_candidate_selection_activation.py`

AG-75A-Z states that it is the final AG-75A suffix. Its tests prove allocation
candidates enter the existing selector only through Controller authorization,
custody admission, classifier/currentness visibility, lower-tier rejection, and
existing fit rules.

## Audited Seam Inventory

Required classification values used below:

1. already subordinate plumbing
2. still local authority
3. delete now
4. bypass/subordinate now
5. extract next
6. intentionally mechanical helper

| seam | file/function | prior local authority risk | classification | action taken in AG-75C | new owner | proof/test | remaining risk | next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Recovered evidence application closure | `core/pipeline_orchestrator.py::_apply_recovered_evidence_visibility` | Built the recovered candidate pool from `all_passages` plus allocation candidates inside the orchestrator before invoking the selector. | bypass/subordinate now | Deleted the local closure and replaced all three call sites with `apply_controller_recovered_evidence_visibility(...)`. | `core.recovered_evidence_visibility` helper plus `ControllerRecoveryDecision`, allocation custody, AuthorityLifecycle candidate fit, and `ControllerEvidenceLedger`. | `test_ag75c_pipeline_orchestrator_no_longer_owns_recovered_pool_gate`; updated AG-75A-Z static test. | The orchestrator still constructs the initial filtered `final_top_evidence` bundle for Author input. | AG-76B/AG-76C should decide whether final evidence bundle construction can move behind a Pipeline Decision Registry entry. |
| Recovered candidate pool construction | old local list comprehension over `all_passages` and allocation helper | Could be read as local candidate inclusion/exposure authority. | bypass/subordinate now | Extracted to `recovered_evidence_selection_candidates(...)`, which only assembles candidates already exposed by source-class recovery stage or allocation custody. | Controller-owned lifecycle/custody state gates eligibility; existing boundary owns selection. | `test_ag75c_controller_visibility_helper_matches_existing_boundary`; `test_ag75c_allocation_candidate_pool_is_controller_custody_owned`. | Source-class recovery passage staging remains represented by `retrieval_stage == source_class_recovery`. | Track as a future runner-owned candidate stream, not an orchestrator closure. |
| Recovered evidence reserve/replace selector | `core/recovered_evidence_visibility.py::apply_recovered_evidence_visibility_boundary` | Selects or rejects recovered evidence for final evidence by matching required source class and cap/replace rules. | intentionally mechanical helper | Left in place; AG-75C adds a higher-level controller handoff helper around it without changing fit semantics. | AuthorityLifecycle candidate fit and `ControllerEvidenceLedger` receive selected/rejected disposition state. | Existing AG-17/AG-22/AG-52 tests plus AG-75C parity helper test. | Fit logic still lives in this helper; broader promotion into a Controller selection registry is future work. | AG-76B/AG-76C Pipeline Decision Registry candidate. |
| Allocation candidate activation | `core/allocation_candidate_selection_activation.py::allocation_result_candidates_for_existing_selection_corridor` | Could admit allocation candidates into recovered-evidence selection. | already subordinate plumbing | Left unchanged; now called from the recovered-evidence helper, not the orchestrator. | `build_allocation_result_candidate_custody_projection(...)` and Controller-authorized allocation execution. | AG-75A-Z tests and AG-75C controller-custody test. | Sanitized candidate shaping remains a small adapter. | Keep until a unified Controller candidate stream replaces it. |
| Source-class recovery runner context | `core/source_class_recovery_runner.py::SourceClassRecoveryRunnerContext` | Large context object can look like local execution authority. | already subordinate plumbing | Left unchanged after audit. It passes dependencies to the runner but does not decide retry/stop/provider allocation. | `ControllerRecoveryDecision` and provider allocation gate. | AG-74F and AG-75A-X/Y/Z tests. | Still temporary compatibility plumbing. | Extract next only if a runner-owned execution context replaces the orchestrator handoff. |
| Final evidence pool construction | `core/pipeline_orchestrator.py` around `deps.filter_top_evidence(...)` and source ID assignment | Builds Author evidence surface and source IDs locally. | still local authority | Not changed because altering it risks final-answer/citation behavior. | None yet; final answer/citation behavior closed. | Existing final-answer/citation parity tests retained; no AG-75C mutation. | This is the largest remaining local authority surface. | AG-76B/AG-76C burn-down with explicit final evidence registry license. |
| Official/canonical visibility export | `core/official_canonical_recovery_visibility_export.py` | Export counts could be misread as custody completion. | already subordinate plumbing | Left unchanged; AG-74C already ledger-gated aggregate success semantics. | `ControllerEvidenceLedger.final_evidence_citation_custody`. | AG-74C export tests. | Legacy recovery-lane labels still exist as observations. | Later vocabulary deletion only, with trace compatibility tests. |
| Runtime trace projection assembly | `core/runtime_trace_projection_assembly.py::attach_passive_runtime_projection_traces` | Projection could become a hidden decision owner if it mutates behavior. | intentionally mechanical helper | Left unchanged; it attaches observer projections and refreshes ledger-gated export. | Observer/export only; ledger owns custody. | AG-74B/AG-74C trace tests. | Broad trace churn remains risky. | Keep observational; add static guards when registry lands. |
| Provider-result represented visibility | `core/provider_result_represented_visibility.py` | Reconciliation labels might be mistaken for decisions. | already subordinate plumbing | Left unchanged; it is passive/sanitized and feeds ledger/passport visibility. | ControllerEvidenceLedger custody events. | AG-73D-V/AG-74A tests. | Aggregate reconciliation remains diagnostic. | Fold into ledger-facing registry if duplicate fields persist. |
| Authority candidate passport | `core/authority_candidate_passport.py` | Passport dispositions could be read as final custody owner. | already subordinate plumbing | Left unchanged; it remains passive projection feeding ledger. | ControllerEvidenceLedger final custody. | AG-73A/AG-74A tests. | Passport still computes durable visibility labels. | Delete duplicate disposition vocabulary after ledger consumers are complete. |
| Authority lifecycle candidate visibility | `core/authority_lifecycle_candidate_visibility.py` | Candidate fit state is material decision-like state. | intentionally mechanical helper | Left unchanged; it records fit/visibility from selector decisions into lifecycle state. | AuthorityLifecycle plus ControllerEvidenceLedger. | AG-69D/E, AG-74A, AG-75A-Z, AG-75C parity tests. | Candidate-fit semantics remain outside AG-75C scope. | Registry phase should name this as fit projection, not provider/search policy. |
| AnswerContract runtime handoff | `core/answer_contract_runtime_handoff.py` | Source-obligation handoff could be interpreted as final evidence authority. | already subordinate plumbing | Left unchanged. | AnswerContract for obligation state; ControllerEvidenceLedger for custody. | AG-74A and AnswerContract tests. | Obligation state still feeds many projections. | Track in AG-76 registry as input state, not selector. |

## Gates Deleted

Deleted from `core/pipeline_orchestrator.py`:

```text
_apply_recovered_evidence_visibility(...)
```

This was the only AG-75C code deletion target. Its three runtime call sites now
call a named recovered-evidence helper.

## Gates Bypassed Or Made Subordinate

The old orchestrator-local recovered candidate pool was made subordinate to:

- `ControllerRecoveryDecision` authorization for provider/search allocation;
- AG-75A-Y allocation-result candidate custody;
- the existing recovered-evidence selector;
- AuthorityLifecycle candidate-fit projection;
- `ControllerEvidenceLedger` selected/dispositioned custody state.

`pipeline_orchestrator.py` no longer imports or calls
`allocation_result_candidates_for_existing_selection_corridor(...)` or
`apply_recovered_evidence_visibility_boundary(...)` directly.

## Gates Left For Next Phase And Why

The final evidence pool construction around `deps.filter_top_evidence(...)`,
source ID assignment, evidence block assembly, Author handoff, and final source
telemetry remains in `pipeline_orchestrator.py`. It is still local authority in
the broad architectural sense, but AG-75C kept it closed because changing it
would risk final answer, Author input, citation formatting, and final prose
behavior.

`SourceClassRecoveryRunnerContext(...)` remains temporary compatibility
plumbing. It is not the best first deletion target because AG-75C found a
smaller, safer gate in recovered-evidence candidate-pool construction.

## Pipeline Orchestrator Pure Plumbing Remaining

For the scoped seam, `pipeline_orchestrator.py` now only:

- computes the existing `final_top_evidence` bundle with unchanged filtering;
- passes `final_top_evidence`, `all_passages`, lifecycle trace, and cap values
  into `apply_controller_recovered_evidence_visibility(...)`;
- receives the bounded final evidence list back;
- continues existing source ID assignment and Author evidence-block assembly.

No new provider/search, classifier, fit, final-answer, Author, or citation logic
was added to the orchestrator.

## AG-76B / AG-76C Burn-Down Tracking

Track these after AG-75C:

- Pipeline Decision Registry entry for final evidence bundle construction.
- Runner-owned candidate stream for source-class recovery results, replacing
  `retrieval_stage == source_class_recovery` as the durable candidate exposure
  signal.
- Deletion or registry ownership of duplicate passport/visibility/export
  disposition vocabulary.
- Static guard that trace/projection/export helpers remain observers.
- Optional deletion of old recovery-lane success vocabulary once consumers are
  ledger-gated.

## Tests Proving Controller Ownership

- `test_ag75c_allocation_candidate_pool_is_controller_custody_owned`
- `test_ag75c_pipeline_orchestrator_no_longer_owns_recovered_pool_gate`
- `test_ag75a_z_controller_authorization_and_custody_are_required`
- `test_ag75a_z_classifier_currentness_gate_is_required_before_fit`
- `test_ag75a_z_lower_tier_candidates_never_satisfy_official_current`

## Tests Proving Behavior Parity

- `test_ag75c_controller_visibility_helper_matches_existing_boundary`
- `test_ag75a_z_allocation_candidate_enters_existing_selection_corridor`
- `test_ag75a_z_existing_fit_rules_reject_non_matching_allocation_candidate`
- Existing AG-74B/AG-74C final answer/citation parity tests remain unchanged.

## Protected Surfaces Kept Closed

No provider routing, provider selection, provider depth/search-depth, provider
escalation, provider swap, new provider, Linkup, query strategy, source
constraint, retrieval ranking/filtering, source-class/currentness classifier,
candidate-fit semantics, prompt, Author, citation formatting, final-answer,
follow-up, Scrutineer, Economist, direct IRS hardcoding, live validation,
raw/private data, DB/cache/log/full-trace, output-packet, or destructive git
surface was opened.

No live ScryRaven/proplex/scryraven provider/model/search calls were run. No
independent web/source checks were run. No local output packet was created.

## Demolition Ledger

1. Old local authority gates found:
   `pipeline_orchestrator.py::_apply_recovered_evidence_visibility(...)`,
   local recovered candidate pool construction, and broader final evidence pool
   construction.
2. Gates deleted:
   `_apply_recovered_evidence_visibility(...)`.
3. Gates bypassed or made subordinate:
   recovered candidate pool construction now lives behind
   `apply_controller_recovered_evidence_visibility(...)` and
   `recovered_evidence_selection_candidates(...)`.
4. Gates left for next phase and why:
   final evidence bundle construction remains because final-answer/citation
   behavior was closed.
5. New Controller-owned decision owners:
   `ControllerRecoveryDecision`, AG-75A-Y allocation custody,
   AuthorityLifecycle candidate fit, AnswerContract obligation state, and
   `ControllerEvidenceLedger`.
6. Mechanical helpers that remain:
   `apply_controller_recovered_evidence_visibility(...)`,
   `recovered_evidence_selection_candidates(...)`,
   `apply_recovered_evidence_visibility_boundary(...)`, and
   `SourceClassRecoveryRunnerContext(...)`.
7. Observer/export surfaces that remain observational:
   runtime trace projection assembly, official/canonical visibility export,
   provider-result represented visibility, and authority candidate passport.
8. Tests proving Controller ownership:
   AG-75C ownership/static tests and retained AG-75A-Z custody tests.
9. Tests proving behavior parity:
   AG-75C boundary parity test and retained final answer/citation parity tests.
10. Net complexity impact:
    one local closure deleted from the orchestrator; one named helper added near
    the existing boundary; tests now make the next deletion target more obvious.
11. Next deletion target:
    final evidence bundle construction and source ID assignment, but only under
    a phase that explicitly licenses final evidence registry ownership without
    changing final answer/citation behavior.

## Recommendation

AG-75C met the deletion-wave requirement. The system is ready to open a
Pipeline Decision Registry phase for final evidence bundle ownership if that
phase explicitly protects Author/citation/final-answer behavior. If the registry
is not yet licensed, run one more focused deletion wave against runner-owned
candidate streaming before touching final evidence construction.
