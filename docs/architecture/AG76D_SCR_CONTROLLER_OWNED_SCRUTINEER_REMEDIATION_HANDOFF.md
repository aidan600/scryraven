# AG-76D-SCR — Controller-Owned Scrutineer / Remediation Handoff Contract

Date: 2026-06-02

## Phase type

Licensed protected-surface authority-transfer groundwork; minimal passive contract implementation with fixture/static tests.

AG-76D-SCR is intentionally passive. It adds a Controller-owned representation contract for Scrutineer/remediation handoff facts, but it does not wire that contract into the runtime Scrutineer block and does not change Scrutineer behavior, remediation behavior, prompts, provider/search/depth/query behavior, retrieval behavior, Analyst behavior, Author prose, citation behavior, DB/session/`RunOutcome` shape, cache behavior, or the runtime pipeline.

## Relationship to AG-79C

AG-79C identified Scrutineer/remediation as the highest remaining active hidden-authority cluster in `core/pipeline_orchestrator.py`: run gate, high-flag threshold, searchable category filter, remediation query generation, novelty filtering, remediation provider/depth selection, re-synthesis trigger, and Author directive insertion were orchestrator-local and final-answer-governing.

AG-76D-SCR follows that audit by adding only a passive handoff schema and fixture/static tests. The legacy orchestrator remains the executor; this phase represents the facts a future Controller-owned handoff should own before any behavior is licensed.

## Purpose

The purpose is to represent Scrutineer/remediation handoff facts without runtime behavior change:

- Scrutineer run eligibility and run-gate facts.
- Scrutineer skipped/running/completed posture.
- Scrutineer flag identities, high-severity flag count, and high-flag threshold posture.
- Searchable and non-searchable category posture.
- Remediation query identity, source Scrutineer flag IDs, and novelty/filter outcome.
- Remediation dispatch authorization, provider role, provider list, search-depth posture, and Linkup depth override as already-computed protected legacy facts.
- Remediation evidence identity and final evidence bundle identity when supplied.
- Re-synthesis / re-analysis admission posture.
- Author directive identity for hedge/omit/caveat/pass-flags-directly metadata.
- Compact AnswerContract, AnalystAuthorHandoff, and CitationSourceHandoff refs when available.

## Contract schema summary

The passive module is `core/scrutineer_remediation_handoff_contract.py`.

Stable schema and trace constants:

- Schema version: `AG76D-SCR.v1`.
- Trace key: `scrutineer_remediation_handoff`.
- Future consumer: `future_controller_owned_scrutineer_remediation_handoff`.

Primary state object:

- `ScrutineerRemediationHandoffState`.

Descriptor objects:

- `ScrutineerAdmissionDescriptor`.
- `ScrutineerFlagDescriptor`.
- `RemediationQueryDescriptor`.
- `RemediationDispatchDescriptor`.
- `RemediationEvidenceDescriptor`.
- `RemediationResynthesisDescriptor`.
- `ScrutineerAuthorDirectiveDescriptor`.
- `ScrutineerRemediationExecutionEnvelope`.

Stable enum families:

- `ScrutineerRunPosture`: `skipped`, `running`, `completed`.
- `RemediationFilterPosture`: `admitted`, `rejected_duplicate`, `rejected_empty`, `rejected_not_novel`, `not_evaluated`.
- `RemediationDispatchPosture`: `authorized`, `not_authorized`, `skipped`, `completed`.
- `ResynthesisAdmissionPosture`: `admitted`, `not_admitted`, `triggered`, `skipped`.
- `AuthorDirectiveKind`: `hedge`, `omit`, `caveat`, `pass_flags_directly`.

## Run eligibility / admission posture

`ScrutineerAdmissionDescriptor` records whether Scrutineer was eligible, which run gate was represented, complexity/mode/contract/requested/needed facts when available, skip reason when applicable, and an explicit `changes_scrutineer_behavior = false` serialization field. It packages legacy facts; it does not decide whether Scrutineer should run.

## Flag threshold and category posture

`ScrutineerFlagDescriptor` records flag ID, category, severity, challenge text identity, searchable posture, source IDs, and metadata. The top-level state separately records `flag_count`, `high_severity_flag_count`, `high_severity_flag_threshold`, `searchable_categories`, and `non_searchable_categories`.

The threshold and category filter are represented as posture only. The contract does not choose the threshold, decide which categories are searchable, or alter existing flag handling.

## Remediation query identity and novelty/filter posture

`RemediationQueryDescriptor` records query ID, query text identity, originating Scrutineer flag IDs, novelty/filter posture, optional novelty score, and optional rejection reason. It marks `changes_query_filtering_behavior = false` so admitted/rejected states are observations of already-computed or fixture facts, not a new novelty policy.

## Remediation dispatch provider/depth posture

`RemediationDispatchDescriptor` records dispatch posture, authorization, provider role, provider names, search depth, Linkup depth override, and result-count posture when those facts are available. It marks provider/depth as protected legacy posture and serializes `changes_provider_search_depth_behavior = false`.

This phase does not alter provider selection, search selection, depth selection, Linkup behavior, query finalization, retrieval ranking/filtering, or provider diagnostics.

## Remediation evidence / final evidence identity posture

`RemediationEvidenceDescriptor` records remediation evidence IDs, source IDs, URLs, final evidence bundle ID, compact final evidence ref, and evidence count when supplied. It marks `changes_retrieval_or_evidence_behavior = false` and does not rebuild, rank, filter, select, cite, or persist evidence.

## Re-synthesis / re-analysis posture

`RemediationResynthesisDescriptor` records whether re-analysis/re-synthesis was admitted or triggered, why, and compact Analyst/analysis refs where available. It marks `changes_analyst_behavior = false` and does not run or re-run the Analyst.

## Author directive identity posture

`ScrutineerAuthorDirectiveDescriptor` records directive ID, directive kind, source flag IDs, hedge/omit/caveat booleans, and metadata. Serialization explicitly sets `prompt_text_included = false` and `changes_author_prompt_or_prose_behavior = false`.

The contract represents directive identity only. It does not change Author prompt text, Author prose, citation wording, source ordering, or final report assembly.

## AnswerContract / AnalystAuthorHandoff / CitationSourceHandoff refs

`ScrutineerRemediationHandoffState` carries compact refs for:

- `answer_contract_ref`.
- `analyst_author_handoff_ref`.
- `citation_source_handoff_ref`.

These refs are copied into the `handoff_refs` serialization. They are identity links only and do not import or execute those runtime handoffs.

## Serialization and trace key

The contract exposes:

- `to_controller_state()` for JSON-safe Controller state.
- `to_trace_fragment()` for `{ "scrutineer_remediation_handoff": ... }` trace attachment in a future phase.

The module includes explicit no-change flags for prompt, provider, search, query, retrieval, Scrutineer, remediation, Analyst, Author, citation, DB/session/`RunOutcome`, cache, pipeline orchestrator, and live-validation behavior.

## Tests added

Added `tests/test_ag76d_scr_scrutineer_remediation_handoff_contract.py` covering:

1. Run gate facts represented without changing Scrutineer behavior.
2. Skipped/running/completed posture stability and JSON safety.
3. High-flag threshold represented as posture, not hidden local authority.
4. Searchable and non-searchable category posture preservation.
5. Remediation query identity and source Scrutineer flag IDs.
6. Novelty/filter admitted and rejected query posture.
7. Provider/depth facts as already-computed protected legacy posture.
8. Remediation evidence and final evidence bundle identity.
9. Re-synthesis admission without re-running Analyst.
10. Author directive identity without prompt/prose behavior change.
11. AnswerContract / AnalystAuthorHandoff / CitationSourceHandoff refs.
12. JSON-safe Controller and trace serialization round-trip.
13. Static protected-import guard.
14. Static guard that `core/pipeline_orchestrator.py` is not changed in git diff.

## Protected surfaces kept closed

Closed surfaces in this phase:

- Scrutineer prompt text and model behavior.
- Remediation query generation behavior.
- Remediation novelty/filter policy.
- Provider/search/depth/query behavior.
- Retrieval behavior and ranking/filtering.
- Analyst re-synthesis behavior.
- Author prompt/prose behavior.
- Citation formatting, selection, and source ordering behavior.
- Source-class/currentness semantics.
- DB/session/`RunOutcome` shape.
- Cache implementation.
- Live validation, provider/model/search calls, local output packets, and raw provider payloads.
- Broad `core/pipeline_orchestrator.py` rewrite or runtime Scrutineer wiring.

## Stop conditions retained

A future phase should stop rather than continue if Scrutineer behavior must change before being licensed; prompts, provider/search/retrieval, Analyst, Author, citation, DB/session/`RunOutcome`, cache, or pipeline behavior must change; live provider/model/search calls are needed; product decisions are needed about thresholds, searchable categories, novelty policy, provider/depth, re-synthesis admission, or Author directive wording; or broad `core/pipeline_orchestrator.py` edits become necessary.

## Remaining hidden-authority surfaces

After AG-76D-SCR, Scrutineer/remediation still remains runtime-hidden authority because this phase is passive and not wired. The highest remaining runtime risks are:

- Runtime Scrutineer/remediation gating and execution in `core/pipeline_orchestrator.py` until a later licensed wiring phase consumes a Controller-owned handoff.
- Synthesis-evaluator supplemental search, including supplemental retrieval, supplemental provider/depth, Author notes, final evidence rebuilding, and Analyst re-run.
- Residual orchestrator-local query/recon/recency and final assembly decisions documented by AG-79C and not repaired here.

## AG-78G live-gate decision

AG-78G remains live-gated. AG-76D-SCR uses offline source inspection, fixture/static tests, ruff, py_compile, and pytest only. It does not run live ScryRaven/proplex/scryraven product paths, provider/model/search calls, independent source checks, local DB/session inspection, local output packets, raw prompts, or raw provider payloads.

## Recommended next phase

Recommended next phase: `AG-76D-SCR-R1 — Scrutineer/remediation runtime wiring`, only if Strategy explicitly licenses behavior after this passive contract is accepted.

If runtime wiring is not licensed, alternate next candidates are synthesis-evaluator supplemental-search handoff, AG-79D targeted orchestrator authority repair, AG-78G bounded dogfood only if explicitly live-licensed, or AG-76D-AD adapter cleanup only if adapter debt blocks safe repair. Do not recommend cache implementation from this phase.
