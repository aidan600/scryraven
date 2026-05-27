# AG-68I Cross-Case Dispatch Arbitration And Candidate Visibility

Scope: offline classification plus one in-scope repair. No live ProPlex run,
provider/model/search call, provider routing, provider selection, provider
depth, retrieval/ranking/filtering behavior, query wording, prompt behavior,
citation/final-answer behavior, Author, Analyst, Economist, Scrutineer,
follow-up, or legal-answer behavior was changed.

## Purpose

AG-68I split the two AG-68H live failure layers:

- SSA stopped before recovery admission because `terminal_stop_approved` was an
  existing runtime blocker.
- IRS passed admission and source-class recovery execution, returned
  candidates, but source-fit/visibility remained `not_evaluated` so no
  official/current recovered evidence survived.

The phase-shape rule allowed both repairs only if both symptoms shared one root
cause or the second change was mechanical fallout from the first.

## Classification

The two surfaces are independent.

SSA is an admission/arbitration surface. The terminal-stop fact is consumed by
official/canonical recovery execution admission before source-class recovery
execution can be authorized.

IRS is a post-dispatch recovered-evidence visibility/source-fit surface. The
recovery slot is already admitted and executed, and the failure is that a
legacy `missing_expected_source_class:*` lifecycle reason kept source-fit from
running even when explicit lifecycle/action facts said the official/canonical
recovery slot had been admitted.

AG-68I repaired the IRS visibility/source-fit surface only. SSA remains
classified as a precise terminal-stop admission blocker and is recommended as
the next architecture phase if SSA live validation is not the immediate
priority.

## Repair

`core/recovered_evidence_visibility.py` now permits recovered-evidence
source-fit evaluation when the lifecycle has all of these explicit runtime
control facts:

- `active_source_class_recovery_official_canonical_admitted=true`;
- at least one missing source class is present;
- `active_source_class_recovery_action_envelope.action_type` is
  `recover_missing_source_class`;
- `active_source_class_recovery_action_envelope.allowed_action=true`;
- the action envelope contains required source classes.

This uses controller/action/lifecycle facts, not trace/projection-only fields.
It does not change provider routing, provider depth, search, ranking,
filtering, query wording, prompts, citation selection, or final-answer
behavior.

## Preserved Behavior

- SSA terminal-stop admission remains fail-closed in the offline fixture.
- Weak-corpus ownership remains fail-closed unless existing controller policy
  explicitly permits coexistence.
- Ordinary authoritative acquisition remains ordinary and is not counted as
  recovery success.
- Lower-tier evidence does not satisfy official/current authority.
- `pipeline_orchestrator.py` was not changed.
- Provider/search review remains closed because SSA did not dispatch in AG-68H
  and IRS failed after candidate return, not at provider acquisition.

## Offline Proof

Added `tests/test_ag68i_dispatch_arbitration_candidate_visibility.py`.

The focused tests prove:

- independent SSA/IRS surfaces cannot both be repaired in this phase;
- a shared-root-cause repair would require an explicit shared seam;
- SSA terminal-stop admission reproduces
  `admission_used=false` with `terminal_stop_approved`;
- without the terminal stop, the same official/current admission facts admit;
- the IRS-style post-dispatch fixture reproduces source-fit `not_evaluated`
  when the explicit official/canonical lifecycle/action fact is absent;
- with that fact present, official/current recovered candidates become visible
  recovered evidence;
- protected routing/query/prompt/final-answer surfaces remain untouched.

## Validation

Offline commands passed:

```text
py -m pytest tests/test_ag68i_dispatch_arbitration_candidate_visibility.py
py -m pytest -p no:cacheprovider tests/test_authoritative_source_live_dispatch_reclassification_ag68h.py tests/test_source_class_recovery_live_product_dispatch_callsite_ag68g.py tests/test_authoritative_source_two_case_live_reclassification_ag68f.py tests/test_source_class_recovery_live_offline_dispatch_parity_ag68e.py tests/test_source_class_recovery_dispatch_execution_ag68c.py tests/test_official_canonical_admission_path_visibility_ag68a.py tests/test_authoritative_source_named_action_extraction.py tests/test_ag64abc_controller_owned_official_current_recovery.py
py -m pytest -p no:cacheprovider --basetemp C:\tmp\ag68i_pytest_tmp tests/test_controller_loop_spine.py tests/test_source_class_recovery_lifecycle.py tests/test_source_class_recovery_executor.py tests/test_source_class_recovery_controller.py tests/test_official_canonical_recovery_query_acquisition_ag50a.py tests/test_official_canonical_recovery_execution_admission_ag50b.py tests/test_official_canonical_recovery_execution_dispatch_ag50d.py tests/test_ag17_recovered_evidence_visibility.py tests/test_source_class_recovery_trace.py tests/test_source_class_recovery_diagnostics_l1.py
py -m pytest -p no:cacheprovider tests/test_authoritative_source_obligations.py tests/test_authoritative_source_answer_contract_projection.py tests/test_authoritative_source_recovery_delegation.py tests/test_authoritative_source_official_canonical_adapter_migration.py tests/test_authoritative_source_followup_numeric_migration.py tests/test_legal_current_authority_fit_adapter.py tests/test_official_canonical_recovery_candidate_visibility_ag52b.py
py -m ruff check core tests docs
git diff --check
```

One first attempt at the AG-17/source-class trace group failed during pytest
temporary-directory cleanup under repo-local `.pytest-tmp` on Windows. The same
tests passed with external `--basetemp C:\tmp\ag68i_pytest_tmp`.

## Next Step

Recommended next phase: SSA terminal-stop/arbitration repair, or AG-68J bounded
live classification only if IRS candidate visibility validation is the priority.
