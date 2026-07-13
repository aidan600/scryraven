Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG74B_CONTROLLER_AUTHORITY_DISPOSITION).

# AG-74B Controller Authority Disposition

Date: 2026-05-28

## Scope

Architecture Groove / Prove Mode. AG-74B is limited to Controller-owned
authority candidate disposition and the first final-evidence/final-citation
custody subordination through `ControllerEvidenceLedger`.

No provider/search/query/depth/routing, source-class/currentness classifier,
candidate-fit, prompt, Author, citation-formatting, final-prose,
final-answer, follow-up, Scrutineer, Economist, live validation, direct IRS
hardcoding, raw/private data, DB/cache/log/full-trace, or output-packet surface
was opened.

## AG-74A Prerequisite Verification

Local `main` contained AG-74A through:

```text
4421c92 Merge pull request #13 from aidan600/codex/ag74a-controller-evidence-ledger-contract
2c6c0a7 Add AG-74A controller evidence ledger
```

Required AG-74A artifacts were present:

- `docs/history/architecture/phases/AG74A_CONTROLLER_EVIDENCE_LEDGER_CONTRACT.md`
- `core/controller_evidence_ledger.py`
- `tests/test_ag74a_controller_evidence_ledger.py`

AG-74A's Demolition Ledger identified the next target as
`core/pipeline_orchestrator.py` local final evidence/citation custody around
`final_top_evidence`, `_apply_recovered_evidence_visibility`, final source ID
assignment, final answer source telemetry, and post-hoc visibility exports.

AG-73A/B/C/D/E validation docs remained present.

## Targeted Legacy Path

The selected seam is the existing runtime projection assembly boundary:

```text
pipeline_orchestrator.py final_top_evidence/source telemetry
  -> attach_passive_runtime_projection_traces(...)
  -> authority_candidate_passport_projection
  -> provider_result_represented_candidate_bridge
  -> official_canonical_recovery_visibility_export
```

Before AG-74B, final evidence/citation observability could be read from
`final_top_evidence`, final source telemetry, or official/canonical visibility
export counts without a Controller-owned final custody status.

## ControllerEvidenceLedger Ownership

`ControllerEvidenceLedger` now owns a runtime custody summary:

```text
controller_evidence_ledger.ControllerEvidenceLedger.final_evidence_citation_custody
```

The summary classifies final evidence/citation custody as:

- `controller_complete` only when final evidence/citation observations have
  represented authority candidates, candidate dispositions, and selected
  authority evidence in ledger state;
- `legacy_gap_observed` when final evidence/citation success exists without
  Controller-visible candidate/passport/selected-evidence custody;
- `missing_controller_disposition` when represented authority candidates lack
  ledger disposition;
- `not_observed` when no final evidence/citation surface is present.

Final evidence/citation counts are explicitly marked non-authoritative for
custody completion:

```text
legacy_success_counts_are_authoritative: false
```

## Mechanical Executor / Helper

`core/pipeline_orchestrator.py` remains executor/plumbing. It still assembles
`final_top_evidence`, assigns final source IDs, and calls the existing runtime
projection assembly seam. AG-74B did not change evidence selection, source ID
assignment, Author input, citation formatting, final prose, provider/search
behavior, source-class semantics, or candidate-fit semantics.

The new runtime helper lives outside the orchestrator:

- `build_controller_evidence_ledger_trace(...)`
- `CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY`
- `attach_passive_runtime_projection_traces(...)` attaches and mirrors the
  ledger trace into the checkpoint packet.

## Observer / Projection / Export

The following remain observational inputs:

- `authority_candidate_passport_projection`
- `provider_result_represented_candidate_bridge`
- `official_canonical_recovery_visibility_export`
- final answer source telemetry

They can observe final evidence/citation survival, but custody completeness is
owned by `ControllerEvidenceLedger`.

## Old Code Deleted, Bypassed, Or Subordinate

Old code deleted: none.

Old code made subordinate:

- final evidence/citation visibility counts in
  `official_canonical_recovery_visibility_export`;
- source-survival final evidence/citation telemetry;
- final source telemetry as a custody signal;
- `pipeline_orchestrator.py` final evidence assembly as custody authority.

Those paths still produce behaviorally important final answer/citation inputs,
so deletion is not safe in AG-74B without opening final-answer behavior. They
are now subordinate because runtime custody consumers must consult
`ControllerEvidenceLedger.final_evidence_citation_custody` and receive
`LegacyCustodyGapObserved` when candidate/passport/selection custody is absent.

## Remaining Old Code To Delete Next

Next deletion should target the post-hoc official/canonical visibility aggregate
success path that reports final evidence/citation survival without reading the
ledger custody summary. A future phase can either fold those final survival
fields into a ledger-owned export or delete aggregate success language that
implies custody completion.

## Behavior Parity Evidence

AG-74B adds ledger trace state only. It does not mutate `final_top_evidence`,
`final_answer_source_ids_used`, citations, Author inputs, or final answer text.

Focused parity test:

- `test_ag74b_runtime_projection_attaches_ledger_and_preserves_final_outputs`

Existing adjacent parity tests retained:

- AG-74A ledger regression tests
- AG-73D-V runtime bridge/export test
- AG-46C runtime projection assembly static boundary test

## Demolition Ledger

Legacy decision path targeted:

`pipeline_orchestrator.py` final evidence/citation custody inferred from
`final_top_evidence`, final source telemetry, and official/canonical visibility
export counts.

New Controller-owned owner:

`ControllerEvidenceLedger.final_evidence_citation_custody`.

Executor/mechanical helper:

`pipeline_orchestrator.py` evidence assembly and
`runtime_trace_projection_assembly.attach_passive_runtime_projection_traces`.

Observer/projection/export:

AG-73 passport, AG-73D-V provider bridge, official/canonical visibility export,
and AnswerContract handoff remain observational/sanitized fact producers.

Old code deleted:

None. Deletion would risk final-answer evidence/citation behavior, which is
closed in AG-74B.

Old code bypassed or made subordinate:

Final evidence/citation success counts are subordinate to ledger custody. They
cannot silently imply complete Controller-owned custody.

Remaining old code to delete next:

Post-hoc aggregate visibility success language and any consumers that treat
final evidence/citation counts as custody complete without the ledger status.

Tests proving Controller ownership:

- `test_ag74b_final_evidence_citation_custody_is_controller_complete_when_dispositioned`
- `test_ag74b_final_success_without_candidate_custody_is_legacy_gap_not_complete`
- `test_ag74b_runtime_aggregate_success_has_explicit_ledger_gap`
- `test_ag74b_static_subordinates_old_path_without_protected_surface_drift`

Tests proving behavior parity or intended behavior change:

- `test_ag74b_runtime_projection_attaches_ledger_and_preserves_final_outputs`
- AG-74A behavior-neutrality/static guard tests
- AG-73D-V runtime bridge/export regression

Net complexity impact:

Small positive complexity trade: one ledger trace wrapper and one custody
summary remove ambiguity from a broad legacy visibility path without changing
answer behavior. No line-count deletion occurred, but the next deletion is safer
because consumers can now test against an explicit Controller-owned status.

## Protected Surfaces Kept Closed

Static and focused tests verify no provider/search/query/depth/routing,
Linkup, classifier, candidate-fit, prompt, Author, citation-formatting,
final-answer, follow-up, Scrutineer, Economist, live validation, raw/private
data, DB/cache/log/full-trace, output-packet, or destructive-git surface was
opened.

## Recommended Next Phase

AG-74C should delete or ledger-subordinate the post-hoc official/canonical
visibility aggregate success language so final evidence/citation survival
exports cannot be read as custody completion unless they carry
`ControllerEvidenceLedger.final_evidence_citation_custody`.
