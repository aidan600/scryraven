Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG74D_V_RECOVERY_LANE_SUCCESS_VOCABULARY_RETIREMENT).

# AG-74D-V Recovery-Lane Success Vocabulary Retirement

Date: 2026-05-28

## Scope

Architecture Groove / Prove Mode. AG-74D-V is limited to recovery-lane success
vocabulary retirement and ledger-subordination in official/canonical visibility
diagnostics.

This phase is not an IRS repair, not a provider/search/query/depth/routing
phase, not a source-class/currentness classifier phase, not a candidate-fit
phase, not a prompt phase, not an Author/citation-formatting/final-prose phase,
and not a final-answer behavior phase.

No live validation was used.

## AG-74C Prerequisite Verification

Local `main` contained AG-74C through:

```text
8e76089 Merge pull request #15 from aidan600/codex/ag74c-ledger-gated-visibility-consumers
f0bfb4d Add AG-74C ledger-gated visibility export
```

Required artifacts were present:

- `docs/history/architecture/phases/AG74C_LEDGER_GATED_VISIBILITY_CONSUMER_SUBORDINATION.md`
- `docs/history/architecture/phases/AG74B_CONTROLLER_AUTHORITY_DISPOSITION.md`
- `core/controller_evidence_ledger.py`
- `core/official_canonical_recovery_visibility_export.py`
- `tests/test_ag74c_ledger_gated_visibility_consumer_subordination.py`

Verified repo facts:

- `ControllerEvidenceLedger.final_evidence_citation_custody` exists.
- `official_canonical_recovery_visibility_export` exposes ledger custody fields.
- AG-74C names `source_survived_to_citation`, `canonical_source_cited`,
  `final_evidence_survival_status`, `final_citation_survival_status`,
  `likely_next_failure_layer`, and `next_failure_layer` as remaining deletion or
  subordination targets.

## Targeted Old Success Vocabulary And Consumers

The targeted seam was the official/canonical diagnostics export:

```text
official_canonical_recovery_visibility_export
  -> final_evidence_survival_status / final_citation_survival_status
  -> likely_next_failure_layer / next_failure_layer
  -> Markdown diagnostics display
```

Before AG-74D-V, two terminal recovery-lane labels still sounded like custody
success:

- `source_survived_to_citation`
- `canonical_source_cited`

## ControllerEvidenceLedger Ownership

`ControllerEvidenceLedger.final_evidence_citation_custody` remains the only
custody-completion owner. The only custody-complete state is:

```text
status == "controller_complete"
```

Recovery-lane observations, final evidence counts, final citation counts,
survival statuses, and next-failure-layer labels do not own custody completion.

## Observational Fields

These fields remain observational only:

- `final_evidence_official_or_canonical_count`
- `final_citation_official_or_canonical_count`
- `final_evidence_observed`
- `final_citation_observed`
- `final_evidence_survival_status`
- `final_citation_survival_status`
- `likely_next_failure_layer`
- `next_failure_layer`

AG-74D-V adds explicit custody interpretation beside retained survival and
failure-layer fields:

- `final_evidence_survival_status_custody_interpretation`
- `final_citation_survival_status_custody_interpretation`
- `likely_next_failure_layer_custody_interpretation`
- `next_failure_layer_custody_interpretation`

Each interpretation is:

```text
recovery_lane_observation_not_controller_custody_status
```

## Deleted, Renamed, Deprecated, Or Subordinated

Deleted from the official/canonical diagnostics export:

- `source_survived_to_citation`
- `canonical_source_cited`

Renamed in the export to observation vocabulary:

- `source_survived_to_citation` ->
  `recovery_lane_source_citation_observed`
- `canonical_source_cited` ->
  `recovery_lane_canonical_citation_observed`

Subordinated:

- `final_evidence_survival_status`
- `final_citation_survival_status`
- `likely_next_failure_layer`
- `next_failure_layer`

They now display with ledger custody fields and explicit non-custody
interpretation in Markdown diagnostics.

## Legacy Gap Visibility

`legacy_gap_observed` remains visible in the export and Markdown diagnostics.
When final evidence/citation observations are present but ledger custody status
is `legacy_gap_observed`, diagnostics show the positive recovery-lane
observation and the Controller-owned gap together.

## Behavior Parity Evidence

AG-74D-V changes diagnostic/export vocabulary only. It does not mutate
`final_top_evidence`, `final_answer_source_ids_used`, final output preview,
Author inputs, citation formatting, provider/search behavior, query behavior,
source classification, candidate fit, or final-answer behavior.

Focused parity proof:

- `test_ag74d_v_runtime_projection_preserves_final_answer_citation_surfaces`

Related retained proof:

- `test_ag74c_runtime_projection_refreshes_export_with_ledger_and_preserves_outputs`
- `test_ag74b_runtime_projection_attaches_ledger_and_preserves_final_outputs`

## Protected Surfaces Kept Closed

No provider routing, provider selection, provider depth/search-depth, provider
escalation, provider swap, new provider, Linkup, query strategy, source
constraint, retrieval ranking/filtering, prompt, source-class/currentness
classifier, candidate fit, Author, citation formatting, final-answer,
follow-up, Scrutineer, Economist, direct IRS hardcoding, live provider/model/
search, raw/private data, DB/cache/log/full-trace, output-packet, or destructive
git surface was opened.

## Old Code Or Consumer To Delete Next

Remaining old vocabulary should be retired from legacy forced-corridor test
helpers and historical validation scaffolds when those fixtures are next
touched. The field names `likely_next_failure_layer` and `next_failure_layer`
also remain old diagnostic field names; a later phase can rename them to
explicit observation fields after downstream fixture churn is licensed.

The next true behavior phase remains the full AG-74D Controller-owned recovery
retry/stop loop.

## Demolition Ledger

Old recovery-lane success vocabulary/path targeted:

`official_canonical_recovery_visibility_export` terminal success labels in
`likely_next_failure_layer`, `next_failure_layer`, and Markdown diagnostics.

New ledger-owned custody status owner:

`ControllerEvidenceLedger.final_evidence_citation_custody`.

Old code/language deleted, renamed, deprecated, or subordinated:

- deleted the old terminal success string values from the official/canonical
  export;
- renamed them to recovery-lane observation values;
- added custody interpretation fields beside retained survival/failure-layer
  observations;
- kept aggregate final evidence/citation counts observational.

Tests proving consumers no longer infer custody from old success vocabulary
alone:

- `test_ag74d_v_renames_success_labels_to_recovery_lane_observations`
- `test_ag74d_v_retained_survival_fields_require_ledger_custody_interpretation`
- `test_ag74d_v_static_export_deletes_old_terminal_success_values`

Tests proving final answer/citation behavior parity:

- `test_ag74d_v_runtime_projection_preserves_final_answer_citation_surfaces`
- retained AG-74B and AG-74C projection parity tests.

Remaining old consumer/path to delete next:

- legacy forced-corridor fixture value `canonical_source_cited`;
- old field names `likely_next_failure_layer` and `next_failure_layer`;
- any downstream consumer that still treats recovery-lane observations as
  completion instead of reading ledger custody status.

Net complexity impact:

Small positive complexity trade. AG-74D-V adds three interpretation fields and
renames two misleading terminal string values. It removes the export's old
success wording and makes the remaining diagnostic fields more deletable by
pinning custody interpretation to the ledger.

If no code was deleted, why the old path is still more deletable:

The old terminal string values were deleted from the export. The retained field
names remain only because broad downstream diagnostic fixture churn is outside
this phase; they are now explicitly subordinate to ledger custody status.

## Recommended Next Phase

Run the full AG-74D Controller-owned recovery retry/stop loop phase. Keep
final-answer, Author, citation-formatting, provider/search/query, classifier,
and candidate-fit behavior closed unless that next phase explicitly opens them.
