# AG-75A-Y Allocation Result Candidate Custody

Date: 2026-05-28

## Scope

AG-75A-Y admits sanitized AG-75A-X allocation execution results into the
existing represented-candidate, provider-result bridge, Authority Candidate
Passport, and ControllerEvidenceLedger custody path.

This phase is not provider/search expansion, IRS repair, classifier/currentness
repair, candidate-fit repair, prompt work, Author work, citation behavior work,
final-answer behavior work, or live validation.

## AG-75A-X Prerequisite Verification

Current `main` contained AG-75A-X / PR #21 before implementation:

```text
66234ee Merge pull request #21 from aidan600/codex/ag75a-x-existing-provider-allocation-execution
f4f3895 Fix AG-75A-X visibility export static guard compatibility
4b9950a Add AG-75A-X bounded provider allocation execution
```

Required AG-75A / AG-75A-X artifacts were present:

- `docs/architecture/AG75A_X_CONTROLLER_AUTHORIZED_EXISTING_PROVIDER_ALLOCATION_EXECUTION.md`
- `docs/architecture/AG75A_CONTROLLER_PROVIDER_SEARCH_ALLOCATION_GATE.md`
- `core/controller_provider_search_allocation.py`
- `core/source_class_recovery_runner.py`
- `core/provider_result_represented_visibility.py`
- `core/authority_candidate_passport.py`
- `core/controller_evidence_ledger.py`
- `tests/test_ag75a_controller_provider_search_allocation_gate.py`

The official/canonical visibility export already exposed the sanitized
AG-75A-X `provider_search_allocation_execution_trace`. `pipeline_orchestrator.py`
remained handoff/plumbing only: it constructs
`SourceClassRecoveryRunnerContext(...)` and calls the runner, while provider
allocation execution remains in `core/controller_provider_search_allocation.py`.

## Allocation Result Object Admitted

AG-75A-X now records bounded `allocation_result_summaries` inside
`provider_search_allocation_trace.provider_search_allocation_execution_trace`.
The summaries are derived from the already-returned allocation result dicts and
include only custody-safe fields such as URL, title, provider role, query
preview, source tier/class when already present, position, and sanitized flags.

The summaries exclude provider text, snippets, raw provider payloads, raw
prompts, secrets, DB rows, private logs, caches, full traces, and local output
packets.

## Candidate/Custody Path Entered

The new helper lives at:

```text
core/allocation_result_candidate_custody.py
```

It builds:

```text
allocation_result_candidate_custody.AllocationResultCandidateCustody
```

That projection exposes:

- `provider_result_bridge_inputs`
- `represented_candidate_inputs`
- `non_represented_results`
- custody counts and non-representation reasons
- `source_obligation_satisfied: false`
- `final_evidence_changed: false`
- `final_citation_changed: false`
- `raw_payload_exposed: false`

`core/runtime_trace_projection_assembly.py` attaches the helper before the
existing Authority Candidate Passport and provider-result bridge projections,
then refreshes it after ControllerEvidenceLedger is attached so the observer can
report whether bridge/passport/ledger surfaces became visible.

Existing custody consumers then read the helper inputs:

- `core/authority_candidate_passport.py` admits
  `represented_candidate_inputs` as ordinary candidate sources.
- `core/provider_result_represented_visibility.py` admits
  `provider_result_bridge_inputs` as ordinary provider-result bridge records.
- `core/controller_evidence_ledger.py` consumes the existing passport and bridge
  projections and records provider/candidate custody events.

## Bypass Prevention

Admission requires the AG-75A-X execution trace to show:

- `allocation_owner == "ControllerRecoveryDecision"`
- `authorized_decision == "request_provider_search_review"`
- `authorized_executor_action == "record_provider_search_review_request"`
- `bounded_profile == "bounded_existing_source_class_recovery_profile_v1"`
- `execution_attempted is True`
- `executed is True`
- positive `result_count`
- at least one sanitized allocation result summary

Local/orchestrator state, a fabricated helper record, a final-answer/citation
problem, readability/classification/fit/context/Author/citation failure states,
or an unexecutable/zero-result allocation execution cannot create custody
inputs.

Allocation results are marked non-satisfying unless an existing downstream
candidate/passport/ledger disposition later selects them. Lower-tier or
secondary allocation results are explicitly marked with:

```text
lower_tier_or_secondary_not_satisfying_official_current_obligation
```

Official-looking results are represented with:

```text
allocation_result_requires_existing_classifier_fit_disposition
```

This prevents returned allocation results from satisfying official/current
obligations merely by existing.

## Observational Only

The following remain observational only:

- allocation execution counts
- allocation result summaries
- custody admission counts
- bridge/passport/ledger visibility booleans
- final-evidence/final-citation parity flags
- official/canonical visibility export fields

None of these fields select final evidence, create final citations, change final
answer prose, alter provider policy, alter source classification, or alter
candidate fit.

## Lower-Tier Controls

Lower-tier/secondary allocation results can enter custody as represented
candidates, but their passport disposition is rejected with source-class/tier
as the first missing stage. The helper and export keep
`source_obligation_satisfied: false`, and ControllerEvidenceLedger records no
selected evidence or final citations from those results.

## Final Answer/Citation Parity Evidence

Tests prove the helper and runner do not call final-answer builders and do not
change final evidence/citation surfaces. The AG-75A-Y helper emits:

```text
final_evidence_changed: false
final_citation_changed: false
```

AG-75A-X regression tests continue to prove allocation execution does not append
returned results to `all_passages`, retrieval pass records, final evidence, or
citations.

## Protected Surfaces Kept Closed

Closed surfaces kept closed:

- provider routing, selection, depth, and escalation policy
- new providers and provider swaps
- Linkup escalation changes
- query strategy and source constraints
- retrieval ranking/filtering
- source-class/currentness classifier semantics
- candidate-fit semantics
- prompt, Author, final prose, final answer, and citation formatting behavior
- follow-up, Scrutineer, and Economist behavior
- direct IRS hardcoding or source-specific official resolver implementation
- live ScryRaven/proplex/scryraven provider/model/search calls
- secrets, raw provider payloads, raw prompts, DB rows, private logs, caches,
  full traces, ignored local output packets, and unrelated artifacts

## Demolition Ledger

1. Old observational-only allocation result path targeted:
   AG-75A-X allocation execution recorded result counts without admitting result
   facts into represented-candidate custody.
2. New custody admission helper/path:
   `core/allocation_result_candidate_custody.py` builds
   `allocation_result_candidate_custody`.
3. Controller authorization source:
   AG-75A-X `ProviderSearchAllocationExecution` fields derived from
   `ControllerRecoveryDecision`.
4. Candidate/custody path entered:
   allocation result summaries become provider-result bridge inputs and
   represented candidate inputs, then flow through Authority Candidate Passport
   and ControllerEvidenceLedger.
5. Observer/export surface:
   official/canonical visibility export exposes allocation-result custody
   availability, admitted/non-represented counts, reasons, and parity flags.
6. Old code upgraded, bypassed, or subordinated:
   AG-75A-X result counts remain, but sanitized summaries and custody admission
   make the old observational-only path subordinate.
7. Tests proving Controller authorization is required:
   AG-75A-Y non-admission tests and AG-75A-X absent/wrong-decision tests.
8. Tests proving allocation results enter represented-candidate/custody path,
   not final evidence directly:
   `test_ag75a_y_authorized_allocation_result_enters_existing_custody_path`.
9. Tests proving lower-tier allocation results cannot satisfy official/current
   obligations:
   `test_ag75a_y_lower_tier_result_cannot_satisfy_official_current_obligation`.
10. Tests proving final answer/citation behavior parity:
    `test_ag75a_y_final_answer_citation_and_classifier_fit_surfaces_stay_closed`
    plus AG-75A-X final-answer/citation static guards.
11. Remaining old path to delete next:
    `pipeline_orchestrator.py` construction of
    `SourceClassRecoveryRunnerContext(...)` remains temporary handoff/plumbing.
12. Net complexity impact:
    one custody helper, one sanitized summary field, two existing projection
    read points, and one assembly attachment. The result removes ambiguity
    around allocation-result custody without opening provider, classifier, fit,
    or final-answer surfaces.

## Recommended Next Phase

Shrink or delete the remaining `pipeline_orchestrator.py` handoff into the
source-class recovery runner/projection assembly boundary, while preserving the
Controller-owned authorization and custody contracts established through
AG-75A-Y.
