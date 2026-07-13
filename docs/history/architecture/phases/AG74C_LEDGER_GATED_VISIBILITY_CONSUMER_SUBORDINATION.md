Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG74C_LEDGER_GATED_VISIBILITY_CONSUMER_SUBORDINATION).

# AG-74C Ledger-Gated Visibility Consumer Subordination

Date: 2026-05-28

## Scope

Architecture Groove / Prove Mode. AG-74C is limited to ledger-gated visibility
consumer subordination for official/canonical recovery export and diagnostics.
It is not an IRS repair, not a final-answer behavior phase, not an
Author/citation-formatting phase, and not a provider/search/query/classifier/fit
repair.

No live validation was used.

## AG-74B Prerequisite Verification

Local `main` contained AG-74B through:

```text
713a80e Merge pull request #14 from aidan600/codex/ag74b-controller-authority-disposition
6497520 Add AG-74B controller authority custody disposition
```

Required AG-74A/AG-74B artifacts were present:

- `docs/history/architecture/phases/AG74B_CONTROLLER_AUTHORITY_DISPOSITION.md`
- `docs/history/architecture/phases/AG74A_CONTROLLER_EVIDENCE_LEDGER_CONTRACT.md`
- `core/controller_evidence_ledger.py`
- `tests/test_ag74b_controller_authority_disposition.py`
- `tests/test_ag74a_controller_evidence_ledger.py`

Verified repo facts:

- `CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY` exists.
- `ControllerEvidenceLedger.final_evidence_citation_custody` exists.
- `runtime_trace_projection_assembly.attach_passive_runtime_projection_traces`
  attaches and mirrors the ledger trace.
- AG-74B identifies the post-hoc official/canonical visibility aggregate
  success path as the next deletion/subordination target.

## Targeted Old Aggregate Success Path

The targeted seam was:

```text
official_canonical_recovery_visibility_export
  -> final_evidence_official_or_canonical_count
  -> final_citation_official_or_canonical_count
  -> final_evidence_survival_status/final_citation_survival_status
  -> likely_next_failure_layer / next_failure_layer Markdown diagnostics
```

Before AG-74C, that export could show final evidence/citation survival without
showing the Controller-owned ledger custody status beside it. That allowed
readers to confuse final evidence/citation survival with complete
Controller-owned custody.

## ControllerEvidenceLedger Ownership

`ControllerEvidenceLedger.final_evidence_citation_custody` is the sole custody
completion owner. The only custody-complete state is:

```text
status == "controller_complete"
```

AG-74C makes `official_canonical_recovery_visibility_export` consume and expose
that state when present:

- `controller_evidence_ledger_available`
- `final_evidence_citation_custody_owner`
- `final_evidence_citation_custody_status`
- `final_evidence_citation_custody_complete`
- `ledger_final_evidence_observed_count`
- `ledger_final_citation_observed_count`
- `legacy_gap_observed`
- `ledger_legacy_gap_types`
- `aggregate_success_counts_are_authoritative_for_custody`
- `aggregate_success_custody_interpretation`
- `next_failure_layer_custody_interpretation`

Runtime projection assembly now refreshes the official/canonical visibility
export after attaching the ledger trace, so the checkpointed diagnostics carry
the ledger-gated custody interpretation.

## Observational Export Fields

These fields remain observational only:

- `final_evidence_official_or_canonical_count`
- `final_citation_official_or_canonical_count`
- `final_evidence_survival_status`
- `final_citation_survival_status`
- `likely_next_failure_layer`
- `next_failure_layer`

They may report survival or recovery-lane status, but they cannot report
Controller-owned custody completion without
`final_evidence_citation_custody_status == "controller_complete"`.

## Old Aggregate Language Subordinated

AG-74C did not delete final evidence/citation counts because those fields are
existing diagnostic observations and final-answer behavior is closed. Instead,
the old aggregate success language is explicitly subordinated:

- the export states `aggregate_success_counts_are_authoritative_for_custody:
  false`;
- the export supplies `aggregate_success_custody_interpretation`;
- Markdown diagnostics display ledger custody fields directly beside aggregate
  final evidence/citation observations;
- `next_failure_layer` remains a recovery-lane observation through
  `next_failure_layer_custody_interpretation`.

## Legacy Gap Visibility

`legacy_gap_observed` remains visible in the official/canonical export and
Markdown diagnostics. When ledger status is `legacy_gap_observed`, aggregate
final evidence/citation survival is displayed as observed final surface
survival plus a ledger gap, not as custody success.

## Behavior Parity Evidence

AG-74C changes export/diagnostic semantics only. It does not mutate
`final_top_evidence`, `final_answer_source_ids_used`, final answer text, Author
inputs, citation formatting, provider/search behavior, query behavior, source
classification, or candidate fit.

Focused parity proof:

- `test_ag74c_runtime_projection_refreshes_export_with_ledger_and_preserves_outputs`

Related retained proof:

- `test_ag74b_runtime_projection_attaches_ledger_and_preserves_final_outputs`
- AG-74A ledger neutrality and static-guard tests
- AG-50C export behavior-neutrality/static-guard tests

## Protected Surfaces Kept Closed

No provider routing, provider selection, provider depth/search-depth, provider
escalation, provider swap, new provider, Linkup, query strategy, source
constraint, retrieval ranking/filtering, prompt, source-class/currentness
classifier, candidate fit, Author, citation formatting, final-answer,
follow-up, Scrutineer, Economist, direct IRS hardcoding, live provider/model/
search, raw/private data, DB/cache/log/full-trace, output-packet, or destructive
git surface was opened.

Protected-surface grep matches are expected historical docs, closed-surface
assertions, or sanitization/static-guard fixtures unless separately reviewed.

## Old Code To Delete Next

Next deletion should remove or fold the remaining duplicate recovery-lane
success labels that can read like completion:

- `source_survived_to_citation`;
- `canonical_source_cited`;
- legacy `final_evidence_survival_status` / `final_citation_survival_status`
  display sites that do not also display ledger custody status;
- remaining consumers that read `next_failure_layer` or aggregate final counts
  as a custody outcome.

Deletion should remain outside final-answer, Author, citation-formatting,
provider/search/query, classifier, and candidate-fit behavior.

## Demolition Ledger

Old aggregate success path targeted:

`official_canonical_recovery_visibility_export` aggregate final evidence and
citation survival diagnostics.

New ledger-owned custody status owner:

`ControllerEvidenceLedger.final_evidence_citation_custody`.

Old code/language deleted, bypassed, deprecated, or subordinated:

- aggregate final evidence/citation counts are explicitly non-authoritative for
  custody;
- recovery-lane `next_failure_layer` fields are explicitly marked not to be
  Controller custody status;
- diagnostics Markdown now displays ledger custody status and legacy gaps.

Tests proving consumers no longer infer custody from aggregate counts alone:

- `test_ag74c_export_counts_are_observational_until_ledger_controller_complete`
- `test_ag74c_controller_complete_is_only_exported_custody_completion`

Tests proving final answer/citation behavior parity:

- `test_ag74c_runtime_projection_refreshes_export_with_ledger_and_preserves_outputs`
- `test_ag74b_runtime_projection_attaches_ledger_and_preserves_final_outputs`

Remaining old consumer/path to delete next:

`likely_next_failure_layer`, `next_failure_layer`, `source_survived_to_citation`,
and `canonical_source_cited` should be split or renamed so recovery-lane success
cannot be read as final custody completion.

Net complexity impact:

Small positive complexity trade. AG-74C adds a compact export adapter and one
runtime refresh at the existing projection assembly seam. No final-answer path
is touched. The old aggregate path is now more deletable because tests can
prove whether a consumer is reading ledger custody or only old survival counts.

Why no code was deleted:

The aggregate fields still support existing diagnostics and historical
validation docs. Deleting them would risk broad export/report churn outside this
phase. They are now subordinate, so a later phase can delete or rename them with
clear fixture coverage.

## Recommended Next Phase

Delete or rename the remaining recovery-lane success vocabulary in the
official/canonical diagnostics export so `source_survived_to_citation` and
`canonical_source_cited` cannot be mistaken for Controller-owned custody
completion. Keep final-answer, Author, citation-formatting, provider/search/
query, classifier, and candidate-fit behavior closed.
