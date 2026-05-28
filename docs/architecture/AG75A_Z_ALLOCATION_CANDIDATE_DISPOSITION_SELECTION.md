# AG-75A-Z Allocation Candidate Disposition / Selection Activation

Date: 2026-05-28

## Scope

AG-75A-Z is the final AG-75A suffix. It operationally connects admitted
AG-75A-Y allocation-result candidates into the existing recovered-evidence
disposition/selection corridor. It does not add a new passive projection,
advisory wrapper, or diagnostic-only surface.

Closed surfaces remain closed: provider expansion, provider routing/depth,
Linkup escalation, query repair, classifier/currentness repair, candidate-fit
repair, prompt/Author/final prose/citation formatting, IRS hardcoding, live
validation, raw/private data, and broad orchestrator domain logic.

## AG-75A-Y Prerequisite Verification

Current `main` contained AG-75A-Y / PR #22 before implementation:

```text
3dbd0b1 Merge pull request #22 from aidan600/codex/ag75a-y-allocation-result-candidate-custody
3b41e07 Add AG-75A-Y allocation result candidate custody
```

Required artifacts were present:

- `docs/architecture/AG75A_Y_ALLOCATION_RESULT_CANDIDATE_CUSTODY.md`
- `docs/architecture/AG75A_X_CONTROLLER_AUTHORIZED_EXISTING_PROVIDER_ALLOCATION_EXECUTION.md`
- `core/allocation_result_candidate_custody.py`
- `core/controller_provider_search_allocation.py`
- `core/authority_candidate_passport.py`
- `core/provider_result_represented_visibility.py`
- `core/controller_evidence_ledger.py`
- `tests/test_ag75a_y_allocation_result_candidate_custody.py`

AG-75A-Y already admitted sanitized allocation-result summaries into provider
bridge, Authority Candidate Passport, and ControllerEvidenceLedger custody
surfaces. The remaining gap was operational: admitted allocation candidates were
not part of the recovered-evidence candidate pool consumed by the existing
selector.

## Old Authority Seam

The old blocking seam was:

```text
pipeline_orchestrator.py
  -> _apply_recovered_evidence_visibility(...)
  -> recovered_passages = all_passages where retrieval_stage == source_class_recovery
  -> apply_recovered_evidence_visibility_boundary(...)
```

AG-75A-X deliberately did not append allocation results to `all_passages`.
AG-75A-Y admitted those results into custody, but the old local recovered
evidence pool only read `all_passages`. That made admitted allocation-result
candidates represented but non-selectable.

AG-75A-Z subordinates that old local pool construction by adding one tiny
handoff:

```text
allocation_result_candidates_for_existing_selection_corridor(...)
```

The helper returns custody-admitted allocation candidates as recovered-evidence
candidate inputs. It does not select, fit, classify, rank, cite, or write final
answer content.

## Operational Path

The operational path is now:

```text
ControllerRecoveryDecision request_provider_search_review
  -> AG-75A-X bounded existing-provider allocation execution
  -> AG-75A-Y allocation_result_candidate_custody
  -> allocation_result_candidates_for_existing_selection_corridor(...)
  -> apply_recovered_evidence_visibility_boundary(...)
  -> authority_lifecycle candidate_fit selected/rejected records
  -> Authority Candidate Passport final_disposition
  -> ControllerEvidenceLedger CandidateDispositioned / AuthorityEvidenceSelected
```

This is an operational connection because allocation candidates can now become
selected final authority evidence through the already-existing recovered
evidence boundary when current classifier/currentness and fit rules accept
them.

## Bypass Prevention

Allocation candidates cannot enter the selector unless all are true:

- AG-75A-X execution lineage is authorized by `ControllerRecoveryDecision`;
- AG-75A-Y custody admits the allocation result;
- source-class classification is visible and not unknown;
- currentness state is visible and not unknown;
- the candidate is not lower-tier/secondary.

Candidate fit is still performed by
`apply_recovered_evidence_visibility_boundary(...)`. ControllerEvidenceLedger
then records selected/rejected custody from the existing passport/lifecycle
facts. The helper cannot independently create `AuthorityEvidenceSelected`,
`promoted_final_authority_evidence`, final citations, or final prose.

## Lower-Tier Controls

Lower-tier or secondary allocation results are excluded before selector entry.
They cannot satisfy official/current obligations and cannot be promoted by local
or orchestrator helper state.

## Preserved Behavior

Preserved behavior:

- no provider/search policy changed;
- no classifier/currentness semantics changed;
- no candidate-fit semantics changed;
- no new passive projection or export surface was added;
- no raw provider payloads, raw prompts, secrets, DB rows, private logs, caches,
  full traces, or ignored output packets were exposed;
- `pipeline_orchestrator.py` remains a tiny handoff into an existing selector,
  not a selection owner.

## CI Note

PR #23 CI failed before dependency install or tests. The failing step was
`actions/setup-python@v6` on the Windows runner. AG-75A-Z changes the workflow
back to `actions/setup-python@v5`, preserving the existing offline check intent
while avoiding the setup action failure.

## Final Answer / Citation Parity

This phase intentionally connects candidates to the existing final authority
evidence selector. It does not alter final prose, Author behavior, citation
formatting, or citation generation. A selected allocation candidate can affect
the evidence set only through the existing recovered-evidence selection
boundary.

## Demolition Ledger

1. Old admitted-but-non-selectable path targeted:
   AG-75A-Y custody existed, but `pipeline_orchestrator.py` built
   `recovered_passages` only from `all_passages`.
2. New operational activation path:
   `allocation_result_candidates_for_existing_selection_corridor(...)` feeds
   admitted allocation candidates into
   `apply_recovered_evidence_visibility_boundary(...)`.
3. Controller authorization source:
   AG-75A-X `ProviderSearchAllocationExecution` derived from
   `ControllerRecoveryDecision == request_provider_search_review`.
4. ControllerEvidenceLedger owner:
   selected/rejected state is recorded through existing lifecycle/passport
   facts into `CandidateDispositioned` and `AuthorityEvidenceSelected`.
5. Observer/export surface:
   existing passport, bridge, ledger, and official/canonical export only; no new
   AG-75A-Z passive projection/export surface.
6. Old code subordinated:
   `pipeline_orchestrator.py` local recovered candidate pool construction is no
   longer the sole authority on source-class recovery candidates.
7. Tests proving Controller authorization is required:
   `test_ag75a_z_controller_authorization_and_custody_are_required`.
8. Tests proving classifier/fit/ledger bypass is impossible:
   `test_ag75a_z_classifier_currentness_gate_is_required_before_fit`,
   `test_ag75a_z_existing_fit_rules_reject_non_matching_allocation_candidate`,
   and the ledger assertion in
   `test_ag75a_z_allocation_candidate_enters_existing_selection_corridor`.
9. Tests proving lower-tier allocation results cannot satisfy official/current
   obligations:
   `test_ag75a_z_lower_tier_candidates_never_satisfy_official_current`.
10. Tests proving final answer/citation behavior parity:
    `test_ag75a_z_raw_payloads_and_protected_surfaces_stay_closed` and the
    absence of final-answer/citation calls in the helper/custody path.
11. Remaining old path to delete next:
    the `pipeline_orchestrator.py` closure
    `_apply_recovered_evidence_visibility(...)` and local final evidence pool
    construction around `final_top_evidence`.
12. Provider/search allocation corridor complete enough for AG-75C audit:
    yes.
13. Net complexity impact:
    one small operational adapter plus a tiny orchestrator handoff. The previous
    passive activation trace/export was removed.

## AG-75C Opening Target

AG-75C should open with an audit/deletion target:

```text
pipeline_orchestrator.py::_apply_recovered_evidence_visibility
```

Move or delete the local recovered candidate pool and final evidence handoff
into a Controller-owned runner/selection boundary, while preserving
`apply_recovered_evidence_visibility_boundary(...)` as the existing fit/selection
rule and `ControllerEvidenceLedger` as the custody/disposition owner.

There is no reason to create another AG-75A suffix.
