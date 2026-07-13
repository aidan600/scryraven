Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG74A_CONTROLLER_EVIDENCE_LEDGER_CONTRACT).

# AG-74A Controller Evidence Ledger Contract

Date: 2026-05-28

## Scope

Architecture Groove / Prove Mode. This phase defines the Controller-owned
Evidence Ledger contract and demolition entry gate. It is contract, tests, and
architecture planning only. It performs no IRS repair and no runtime behavior
change.

## Inputs Inspected

- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/architecture/SCRYRAVEN_CURRENT_STATE.md`
- `docs/history/validation/AG73A_AUTHORITY_CANDIDATE_PASSPORT_CUSTODY.md`
- `docs/history/validation/AG73B_AUTHORITY_PASSPORT_RUNTIME_VISIBILITY.md`
- `docs/history/validation/AG73C_BOUNDED_IRS_CUSTODY_VALIDATION.md`
- `docs/history/validation/AG73D_V_PROVIDER_RESULT_REPRESENTED_VISIBILITY.md`
- `docs/history/validation/AG73E_ONE_RUN_IRS_LIVE_CUSTODY_VALIDATION.md`
- `core/pipeline_orchestrator.py`
- `core/pipeline.py`
- `core/authority_candidate_passport.py`
- `core/provider_result_represented_visibility.py`
- `core/runtime_trace_projection_assembly.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/recovered_evidence_visibility.py`
- `core/authority_lifecycle_candidate_visibility.py`
- `core/answer_contract_runtime_handoff.py`
- AG-73A, AG-73D-V, AnswerContract, official/current visibility, and provider
  diagnostic tests.

## Prerequisite Verification

`main` contained AG-73E through `a915b6f Merge pull request #12 from
aidan600/codex/ag73e-one-run-irs-live-custody-validation`.

Both required docs were present:

- `docs/history/validation/AG73E_ONE_RUN_IRS_LIVE_CUSTODY_VALIDATION.md`
- `docs/history/validation/AG73D_V_PROVIDER_RESULT_REPRESENTED_VISIBILITY.md`

AG-73E records successful final IRS evidence/citation survival:

- final answer identified the 2026 IRS business mileage rate as 72.5 cents per
  mile, effective January 1, 2026;
- final answer cited two IRS URLs;
- `final_evidence_official_or_canonical_count: 5`;
- `final_citation_official_or_canonical_count: 2`;
- final evidence and final citation survival were `visible`.

AG-73E also records the remaining rough edge:

- `final_selected_authority_evidence_count: 0`;
- `authority_candidate_passport_count: 0`;
- provider-result bridge aggregate reconciliation remained
  `aggregate_provider_count_exceeds_visible_bridge_records`;
- final official/current evidence and citations can coexist with incomplete or
  absent candidate/passport custody.

## Contract

The new contract lives in `core/controller_evidence_ledger.py` as
`build_controller_evidence_ledger`.

Ledger event vocabulary:

- `AuthorityRequirementDeclared`
- `RecoveryActionAuthorized`
- `ProviderResultObserved`
- `CandidateRepresented`
- `CandidateReadable`
- `CandidateClassified`
- `CandidateFitEvaluated`
- `CandidateDispositioned`
- `AuthorityEvidenceSelected`
- `FinalEvidenceObserved`
- `FinalCitationObserved`
- `AnswerContractUpdated`
- `ContextExposureRequired`
- `ContextExposureObserved`
- `LegacyCustodyGapObserved`

The ledger is Controller-owned state, not a report export. It owns the custody
disposition vocabulary and records legacy bypasses as explicit gaps. It consumes
already-sanitized facts and does not retrieve, route providers, rank/filter,
classify, fit, prompt, cite, synthesize, persist, or alter runtime behavior.

## AG-73 Fact Mapping

Provider-result bridge facts map as follows:

- bridge records become `ProviderResultObserved`;
- represented bridge records become `CandidateRepresented`;
- `represented_candidate_without_passport` becomes a Controller-visible
  `CandidateDispositioned` event instead of a silent custody hole;
- aggregate bridge non-reconciliation becomes `LegacyCustodyGapObserved`.

Authority passport facts map as follows:

- passports become `CandidateRepresented`;
- readability becomes `CandidateReadable`;
- source tier/class/currentness become `CandidateClassified`;
- fit and satisfaction state become `CandidateFitEvaluated`;
- passport `final_disposition`, `first_missing_stage`, and durable reason
  become `CandidateDispositioned`;
- promoted or matched candidates become `AuthorityEvidenceSelected`.

Final evidence and final citations map as follows:

- final official/current/canonical evidence records become
  `FinalEvidenceObserved`;
- final citation records become `FinalCitationObserved`;
- aggregate visibility export counts become bounded legacy placeholder
  observed events when no per-item sanitized identity is available.

## AnswerContract Mapping

`answer_contract_fulfillment_handoff` maps into `AnswerContractUpdated`.

Mapped fields include:

- `source_obligation_status`;
- `fulfilled_items`;
- `partial_items`;
- `unfulfilled_items`;
- `unfulfilled_source_classes`;
- `partial_source_classes`;
- compact `evidence_used` references, which also become
  `ContextExposureObserved`.

The old handoff remains a producer of sanitized facts. It is subordinate to the
ledger for evidence-custody reconciliation.

## Legacy Custody Gaps

The ledger explicitly records:

- `final_evidence_or_citation_without_candidate_passport_custody`;
- `final_evidence_or_citation_without_final_selected_authority_evidence`;
- `provider_result_bridge_aggregate_not_reconciled`;
- `provider_result_to_final_evidence_custody_parallel_path`.

These are not errors hidden by the ledger. They are demolition map entries:
final answer/citation success can be real while Controller-owned candidate and
passport custody is incomplete.

## Demolition Ledger

Legacy decision path targeted:

`core/pipeline_orchestrator.py` local final evidence/citation custody around
`final_top_evidence`, `_apply_recovered_evidence_visibility`, final source ID
assignment, final answer source telemetry, and post-hoc visibility exports.

New Controller-owned owner:

`ControllerEvidenceLedger`.

Executor/mechanical helper:

`apply_recovered_evidence_visibility_boundary` and source-class recovery
execution remain mechanical helpers. They may execute Controller-approved
actions but should not own final custody reconciliation.

Observer/projection/export:

`authority_candidate_passport`, `provider_result_represented_visibility`, and
`official_canonical_recovery_visibility_export` remain observer/projection/export
inputs.

Old code deleted:

None in AG-74A. Deletion was not licensed because this phase creates the entry
gate and proof fixtures.

Old code bypassed or made subordinate:

- AG-73 provider-result bridge dispositions are subordinate to ledger event
  state.
- AG-73 passport final dispositions are subordinate to ledger event state.
- final evidence/citation survival aggregates are subordinate to ledger state
  and cannot imply complete custody by themselves.
- AnswerContract source-obligation handoff is subordinate to ledger custody
  reconciliation.

Remaining old code that should be deleted next:

- orchestrator-local final evidence selection/citation custody decisions that
  can move into a Controller-approved runner;
- parallel aggregate visibility paths that report final evidence/citation
  success without candidate/passport disposition;
- post-hoc reconciliation logic that only explains the path after final answer
  assembly.

Tests proving Controller ownership:

- `test_ag74a_ledger_contract_declares_required_event_vocabulary`
- `test_ag74a_maps_provider_bridge_passport_final_surfaces_and_answer_contract`
- `test_ag74a_final_evidence_and_citations_survive_with_zero_passport_custody_gap`
- `test_ag74a_represented_official_candidate_gets_controller_visible_disposition`

Tests proving behavior parity or intended no-change:

- `test_ag74a_ledger_sanitizes_protected_material_and_does_not_change_behavior`
- `test_ag74a_static_guards_keep_protected_surfaces_closed`
- related AG-73A, AG-73D-V, and AnswerContract tests.

Net complexity impact:

AG-74A adds one small pure contract and focused tests. It does not reduce line
count yet, but it reduces future deletion risk by making the next orchestrator
authority removal measurable: old paths must produce ledger events or be
classified as legacy gaps.

Why this is not just another wrapper:

The ledger is the owner of custody state and gap classification. Projections
feed it; they do not decide custody completeness. Final evidence/citation
survival is no longer allowed to silently imply candidate/passport custody.

## Protected Surfaces Kept Closed

No provider routing, provider selection, provider depth/search-depth, provider
escalation, provider swap, new provider, Linkup, query strategy, source
constraint, retrieval ranking/filtering, prompt, source-class/currentness
classifier, candidate fit, Author, citation, final-answer, follow-up,
Scrutineer, Economist, IRS hardcoding, live provider/model/search, raw/private
data, DB/cache/log, local output packet, or destructive git surface was opened.

## Live Validation

No live validation was used. No live ScryRaven/proplex/scryraven product-path
command, provider/model/search call, independent web check, or local output
packet was created.

## Recommended Next Phase

AG-74B should subordinate the first orchestrator-local custody path: final
evidence selection and final citation observability around `final_top_evidence`.
The runner should execute Controller-approved evidence selection while
`ControllerEvidenceLedger` becomes the required custody state for official or
current authority evidence.
