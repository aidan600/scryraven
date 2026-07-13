Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG73D_V_PROVIDER_RESULT_REPRESENTED_VISIBILITY).

# AG-73D-V Provider Result to Represented Candidate Visibility Bridge

Date: 2026-05-28

## Scope

Review Lane Batch Mode, diagnostic bridge only. This phase added sanitized
provider-result to represented-candidate visibility. It did not repair runtime
behavior, did not change provider routing/selection/depth/escalation, did not
change query strategy, retrieval, ranking, filtering, classification, fit,
Controller, AnswerContract, context, Analyst, Author, citation, or final-answer
behavior, and did not run live validation.

## AG-73C Prerequisite Verification

AG-73C was present on current `main` before implementation:

- recent log included `168be91 Merge pull request #10 from
  aidan600/codex/ag73c-bounded-irs-custody-validation`;
- `docs/history/validation/AG73C_BOUNDED_IRS_CUSTODY_VALIDATION.md` existed;
- `tests/test_ag73c_bounded_irs_custody_validation.py` existed;
- `core/authority_candidate_passport_validation.py` existed;
- `core/authority_candidate_passport.py` and the AG-73A/AG-73B validation docs
  remained present;
- the AG-73C doc identified the still-unobservable boundary as
  `provider-result to represented authority candidate`.

## Inputs Inspected

- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/architecture/SCRYRAVEN_CURRENT_STATE.md`
- `docs/history/validation/AG73A_AUTHORITY_CANDIDATE_PASSPORT_CUSTODY.md`
- `docs/history/validation/AG73B_AUTHORITY_PASSPORT_RUNTIME_VISIBILITY.md`
- `docs/history/validation/AG73C_BOUNDED_IRS_CUSTODY_VALIDATION.md`
- `core/authority_candidate_passport.py`
- `core/authority_candidate_passport_validation.py`
- `core/runtime_trace_projection_assembly.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/recovered_evidence_visibility.py`
- `core/authority_lifecycle_candidate_visibility.py`
- `core/source_class_recovery_executor.py`
- `core/official_canonical_recovery_candidate_acquisition.py`
- `core/answer_contract_runtime_handoff.py`
- `core/pipeline.py`
- `core/pipeline_orchestrator.py` for passive attachment context only
- related AG-73A, AG-73B, AG-73C, provider diagnostics, recovery visibility,
  source-class recovery, official/current acquisition, authority lifecycle,
  visibility export, and AnswerContract handoff tests.

## Existing Sanitized Provider-Result Facts

Before AG-73D-V, ScryRaven already exposed aggregate provider/acquisition facts:

- `provider_diagnostics` attempt records;
- `result_count`, `accepted_url_count`, raw/accepted overlap counts, and
  provider-role summaries;
- source-class recovery aggregate fields such as
  `candidate_acquisition_provider_result_count`,
  `candidate_acquisition_provider_accepted_url_count`, and
  `active_source_class_recovery_result_count`;
- represented candidate/passport facts after a candidate becomes recovered,
  fit-evaluated, rejected, selected, or exported.

Those aggregate facts did not include sanitized per-result identity, so AG-73C
could not prove whether a specific provider result became represented. AG-73D-V
adds bounded `provider_result_summaries` to provider diagnostics. The summaries
include URL/domain/title/rank/query/provider metadata and durable acceptance or
non-representation reasons. They exclude snippets, source text, raw provider
payloads, raw prompts, secrets, API keys, DB rows, private logs, caches, full
raw traces, and local output packets.

## Bridge Field Contract

The bridge lives in `core/provider_result_represented_visibility.py` and exposes
`provider_result_represented_candidate_bridge` records with:

- `bridge_schema_version`
- `provider_result_id`
- `provider_name`
- `provider_role`
- `retrieval_pass_id`
- `query_preview`
- `provider_rank_or_position`
- `source_url`
- `normalized_domain`
- `title`
- `source_tier`
- `source_class`
- `provider_returned`
- `represented_candidate_id`
- `passport_candidate_id`
- `represented_candidate_visible`
- `passport_visible`
- `bridge_disposition`
- `non_representation_reason`
- `first_missing_stage`
- `aggregate_reconciliation_status`
- `diagnostic_only`
- `sanitized`
- `behavior_changed`

Allowed bridge dispositions are:

- `represented_passport_matched`
- `represented_candidate_without_passport`
- `not_represented_with_reason`
- `lower_tier_not_authority_satisfying`
- `unobservable_without_raw_or_live_data`

## Tests And Harnesses Used

Added `tests/test_ag73d_v_provider_result_represented_visibility.py`.

Focused run:

```text
py -m pytest -q tests/test_ag73d_v_provider_result_represented_visibility.py --basetemp C:\tmp\ag73d-v-focused
```

Result: 7 passed.

Touched Python lint:

```text
py -m ruff check core\provider_diagnostics.py core\pipeline.py core\provider_result_represented_visibility.py core\runtime_trace_projection_assembly.py core\official_canonical_recovery_visibility_export.py tests\test_ag73d_v_provider_result_represented_visibility.py
```

Result: passed.

## Reconciliation Behavior

The bridge indexes represented passports and represented candidates by
candidate ID and normalized URL. Each sanitized provider result resolves to
exactly one review-visible disposition:

- URL/candidate match to a passport: `represented_passport_matched`;
- URL/candidate match to represented evidence without a passport:
  `represented_candidate_without_passport`;
- no representation but a durable diagnostic reason such as duplicate URL:
  `not_represented_with_reason`;
- secondary/lower-tier evidence that cannot satisfy an official/current
  obligation: `lower_tier_not_authority_satisfying`;
- no sanitized per-result identity or no reason:
  `unobservable_without_raw_or_live_data`.

Aggregate reconciliation compares known provider-result summary counts and
provider/acquisition aggregate counts with bridge record counts. If only
aggregate counts exist, the boundary remains explicitly unobservable rather
than inferred.

## Durable Non-Representation Reasons

Provider summaries produced by `core/pipeline.py` carry durable passive reasons
for non-representation when observable:

- `duplicate_seen_url`;
- `duplicate_provider_url`;
- `non_plausible_url` for URL-bearing but non-plausible provider items.

Lower-tier/non-authority-satisfying results get
`lower_tier_or_secondary_not_satisfying_official_current_obligation`.

## Still Unobservable

Without separately licensed live/raw/private inspection, AG-73D-V still cannot
classify historical live IRS provider results that were never committed as
sanitized per-result summaries. Aggregate-only provider counts remain visible
as `aggregate_provider_count_exceeds_visible_bridge_records` with the boundary
`provider-result to represented authority candidate`.

## Why Live Validation Was Not Used

Live validation was explicitly out of scope. No live ScryRaven/proplex/
scryraven product-path command, provider/model/search call, independent web
check, raw provider inspection, DB inspection, private-log read, cache read,
full-trace inspection, or local ignored output packet was used.

## Why Runtime Behavior Did Not Change

The new code is diagnostic-only:

- provider diagnostics now include sanitized provider-result summaries;
- the bridge is attached by the existing passive runtime projection assembly;
- the visibility export mirrors the bridge for review;
- returned passages, provider routing, retrieval decisions, ranking/filtering,
  classification, fit, Controller decisions, AnswerContract decisions, context,
  Analyst, Author, citation, and final-answer behavior are not read from or
  changed by the bridge.

`behavior_changed` remains `False` on the provider-result summaries, bridge
projection, and visibility export.

## Protected Surfaces Kept Closed

- provider routing, selection, depth, escalation, swaps, Linkup changes, and new
  providers;
- query strategy and source constraints;
- retrieval, ranking, filtering, source-class classification, currentness
  classification, candidate fit, and acceptance behavior;
- Controller and AnswerContract runtime decisions;
- context packet, Analyst, Author, citation, final-answer, follow-up, and
  Scrutineer behavior;
- direct IRS hardcoding and source-specific IRS resolver implementation;
- broad `core/pipeline_orchestrator.py` domain logic;
- package, CLI, and env compatibility behavior;
- raw/private/protected material.

## Decision Usefulness

Chosen next useful action:

```text
request separately licensed one-run live custody validation
```

Reason: the provider-result to represented-candidate boundary is now observable
when sanitized provider-result summaries exist. The historical AG-73C live IRS
lineage still lacks committed sanitized per-result provider facts, so a
separately licensed one-run live custody validation is the narrowest way to
populate the new bridge and classify the live boundary without repair.

## Remaining Rough Edges

- Historical aggregate-only validation artifacts remain unclassified at the
  per-result boundary because AG-73D-V did not inspect raw/live/private data.
- The bridge intentionally records compact URL/title/domain summaries only; it
  does not expose snippets, source bodies, raw provider payloads, or raw result
  objects.
- The bridge is a diagnostic visibility contract, not a durable product
  decision surface. Promote or retire it after AG-73D/AG-74/AG-75 validation
  determines whether ongoing report-visible custody diagnostics are needed.
