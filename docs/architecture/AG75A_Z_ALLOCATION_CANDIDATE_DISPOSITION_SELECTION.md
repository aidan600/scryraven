# AG-75A-Z Allocation Candidate Disposition / Selection Activation

Date: 2026-05-28

## Scope

AG-75A-Z connects admitted AG-75A-Y allocation-result candidates to the
existing downstream candidate disposition and selected-evidence corridor. It is
not provider expansion, query repair, source-class/currentness classifier
repair, candidate-fit repair, final-answer behavior, Author behavior, citation
formatting, IRS hardcoding, broad orchestrator work, or live validation.

## AG-75A-Y Prerequisite Verification

Current `main` contained AG-75A-Y / PR #22 before implementation:

```text
3dbd0b1 Merge pull request #22 from aidan600/codex/ag75a-y-allocation-result-candidate-custody
3b41e07 Add AG-75A-Y allocation result candidate custody
```

Required AG-75A-X / AG-75A-Y artifacts were present:

- `docs/architecture/AG75A_Y_ALLOCATION_RESULT_CANDIDATE_CUSTODY.md`
- `docs/architecture/AG75A_X_CONTROLLER_AUTHORIZED_EXISTING_PROVIDER_ALLOCATION_EXECUTION.md`
- `core/allocation_result_candidate_custody.py`
- `core/controller_provider_search_allocation.py`
- `core/authority_candidate_passport.py`
- `core/provider_result_represented_visibility.py`
- `core/controller_evidence_ledger.py`
- `tests/test_ag75a_y_allocation_result_candidate_custody.py`

AG-75A-Y allocation-result candidates were already visible through the
provider-result bridge, Authority Candidate Passport, and
ControllerEvidenceLedger projections. `core/pipeline_orchestrator.py` remained
handoff/plumbing only and did not own allocation-result custody or
candidate-selection logic.

## Activation Path

The new helper lives at:

```text
core/allocation_candidate_selection_activation.py
```

It builds:

```text
allocation_candidate_selection_activation.AllocationCandidateSelectionActivation
```

Allocation-result candidates enter the downstream disposition/selection path as
follows:

```text
AG-75A-X sanitized allocation_result_summaries
  -> AG-75A-Y allocation_result_candidate_custody represented_candidate_inputs
  -> Authority Candidate Passport candidate disposition
  -> ControllerEvidenceLedger CandidateDispositioned / AuthorityEvidenceSelected
  -> AG-75A-Z activation projection
```

The activation projection reads only existing custody facts. It does not
classify, fit, rank, retrieve, prompt, cite, write final prose, or append final
evidence.

## Bypass Prevention

Activation requires all of the following existing facts:

- AG-75A-Y candidate custody admitted a candidate from a Controller-authorized
  AG-75A-X execution.
- The allocation execution lineage still records
  `ControllerRecoveryDecision` as allocation owner.
- Authority Candidate Passport exposes source-class/currentness state.
- Authority Candidate Passport exposes candidate-fit state.
- ControllerEvidenceLedger records a candidate disposition.
- Selection is present only when ControllerEvidenceLedger exposes
  `AuthorityEvidenceSelected`.

Missing classifier/currentness state blocks activation with
`missing_classifier_currentness_state`. Missing fit blocks with
`missing_candidate_fit_state`. Missing ledger disposition blocks with
`missing_controller_evidence_ledger_disposition`.

Lower-tier or secondary allocation results remain blocked with:

```text
lower_tier_or_secondary_not_satisfying_official_current_obligation
```

Allocation results cannot satisfy official/current obligations merely because
the allocation execution was Controller-authorized.

## Observational Only

The following remain observational only:

- admitted candidate counts;
- eligibility counts;
- activated disposition counts;
- selected evidence candidate counts;
- blocked reason counts;
- final-answer and citation parity flags;
- raw-payload exposure flags;
- official/canonical visibility export projections.

These fields do not change final evidence, citations, final answer prose,
Author behavior, provider policy, classifier behavior, or candidate-fit
behavior.

## Preserved Behavior

Existing behavior preserved:

- ControllerRecoveryDecision remains the only authority that permitted
  allocation execution.
- ControllerEvidenceLedger remains the custody/disposition owner.
- Existing source-class/currentness classifier semantics are consumed, not
  changed.
- Existing candidate-fit semantics are consumed, not changed.
- Existing final answer, Author, and citation behavior remain closed.
- `pipeline_orchestrator.py` remains handoff/plumbing only.
- Raw provider payloads, prompts, secrets, DB rows, logs, caches, full traces,
  and ignored output packets remain unexposed.

## Final Answer / Citation Parity Evidence

AG-75A-Z adds only projection/export fields:

```text
final_answer_behavior_changed: false
citation_behavior_changed: false
raw_payload_exposed: false
```

Focused tests assert selected allocation candidates do not create final evidence
or citations directly, and the official/canonical export continues to report
unchanged final evidence/citation counts for offline fixtures.

## Protected Surfaces Kept Closed

Closed surfaces kept closed:

- provider routing, selection, depth, and escalation policy;
- new providers, provider swaps, and Linkup escalation changes;
- query strategy and source constraints;
- retrieval ranking/filtering;
- source-class/currentness classifier behavior;
- candidate-fit behavior;
- prompt, Author, citation formatting, final prose, final answer, follow-up,
  Scrutineer, and Economist behavior;
- direct IRS hardcoding or source-specific official resolver implementation;
- live ScryRaven/proplex/scryraven provider/model/search calls;
- secrets, raw provider payloads, raw prompts, DB rows, private logs, caches,
  full traces, ignored local output packets, and unrelated generated artifacts.

## AG-75C Audit Readiness

The provider/search allocation corridor is complete enough for an AG-75C audit
of allocation authorization, bounded execution, candidate custody, downstream
disposition activation, and protected-surface closure. It is not complete enough
to delete final-answer/citation legacy paths or change provider/search policy.

## Demolition Ledger

1. Old admitted-but-non-selectable allocation candidate path targeted:
   AG-75A-Y allocation-result candidates could enter custody while remaining
   non-selectable for downstream disposition review.
2. New downstream disposition/selection activation path:
   `core/allocation_candidate_selection_activation.py` reads existing
   passport and ControllerEvidenceLedger disposition/selection state.
3. Controller authorization source:
   AG-75A-X execution lineage derived from `ControllerRecoveryDecision`.
4. ControllerEvidenceLedger disposition/selection owner:
   `CandidateDispositioned` and `AuthorityEvidenceSelected` ledger events.
5. Observer/export surface:
   `runtime_trace_projection_assembly` attaches the neutral activation trace,
   and `official_canonical_recovery_visibility_export` exposes sanitized counts
   and blocked reasons.
6. Old code upgraded, bypassed, or subordinated:
   AG-75A-Y admitted custody remains; AG-75A-Z makes the old
   admitted-but-not-activation-visible path subordinate to ledger disposition.
7. Tests proving Controller authorization is required:
   `test_ag75a_z_controller_recovery_decision_authorization_required`.
8. Tests proving classifier/fit/ledger bypass is impossible:
   `test_ag75a_z_candidate_cannot_bypass_classifier_currentness_fit_or_ledger`.
9. Tests proving lower-tier allocation results cannot satisfy official/current
   obligations:
   `test_ag75a_z_lower_tier_and_rejected_fit_cannot_satisfy_obligation`.
10. Tests proving final answer/citation behavior parity:
    `test_ag75a_z_selected_only_through_existing_ledger_selection_corridor` and
    `test_ag75a_z_raw_payloads_and_protected_surfaces_stay_closed`.
11. Remaining old path to delete next:
    `pipeline_orchestrator.py` construction of
    `SourceClassRecoveryRunnerContext(...)` and local final evidence/citation
    assembly remain future demolition targets.
12. Whether provider/search allocation corridor is complete enough for AG-75C
    audit:
    yes, for audit of authorization, bounded execution, custody admission,
    downstream activation, and protected-surface closure.
13. Net complexity impact:
    one small pure activation helper, one projection assembly hook, one export
    projection, and focused tests. The new code lowers ambiguity without
    opening classifier, fit, provider, or final-answer surfaces.

## Recommended Next Phase

Run AG-75C as an audit phase over the provider/search allocation corridor from
ControllerRecoveryDecision through bounded execution, candidate custody,
activation projection, and protected-surface closure. Keep deletion of
`pipeline_orchestrator.py` handoff/final evidence legacy paths as a separate
mechanical phase.
