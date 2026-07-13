Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG73E_ONE_RUN_IRS_LIVE_CUSTODY_VALIDATION).

# AG-73E One-Run IRS Live Custody Validation

Date: 2026-05-28

## Scope

Validation gate / Review Lane Batch Mode. This phase ran exactly one live
ScryRaven product-path custody validation and performed no repair.

Closed surfaces included provider routing, provider selection, provider depth,
provider escalation, provider swaps, new providers, Linkup behavior, query
strategy, source constraints, retrieval/ranking/filtering behavior,
classification behavior, candidate fit/currentness behavior,
Controller/AnswerContract decisions, context packet behavior, Analyst behavior,
Author behavior, citation/final-answer behavior, follow-up behavior,
Scrutineer behavior, direct IRS hardcoding, source-specific IRS resolver
implementation, package/CLI/env compatibility changes, and broad
`core/pipeline_orchestrator.py` domain logic.

## AG-73D-V Prerequisite Verification

AG-73D-V was present on local `main` before this branch:

- recent log included `e5ed563 Merge pull request #11 from
  aidan600/codex/ag73d-v-provider-result-represented-visibility`;
- `docs/history/validation/AG73D_V_PROVIDER_RESULT_REPRESENTED_VISIBILITY.md` exists;
- `tests/test_ag73d_v_provider_result_represented_visibility.py` exists;
- `core/provider_result_represented_visibility.py` exists;
- `core/provider_diagnostics.py` exposes sanitized `provider_result_summaries`;
- `core/runtime_trace_projection_assembly.py` attaches
  `provider_result_represented_candidate_bridge`;
- `core/official_canonical_recovery_visibility_export.py` exports the bridge
  and the AG-73A/B passport surfaces;
- AG-73A/B/C docs and test surfaces remained present.

## Exact Query

```text
What is the IRS 2026 business standard mileage rate?
```

## Command / Harness

```powershell
py -m scryraven "What is the IRS 2026 business standard mileage rate?" --mode Balanced --output output\ag73e_irs_live_custody_validation_packet.md
```

The run used the current repo/runtime provider, search, and model
configuration. No include-domain corridor, provider override, extra retry, or
ad hoc external source check was added.

## Live Budget Used

- Product-path runs: exactly 1.
- Independent web/source checks: 0.
- Ad hoc provider/model/search calls outside the product run: 0.

CLI-visible telemetry for the single product run:

```text
[proplex] 26.1s | 15 calls | $0.0798 | execution_log.jsonl updated
```

## Local Packet

Local ignored output packet:

```text
output/ag73e_irs_live_custody_validation_packet.md
```

The packet begins with `LOCAL/UNTRACKED - DO NOT COMMIT`. `git check-ignore -v`
confirmed it is ignored by the repo `output/` rule, and `git ls-files output`
returned no tracked output files.

The packet contains sanitized CLI-visible final-answer, citation, and diagnostic
summaries only. It does not include `.env`, API keys/secrets, raw provider
payloads, raw prompts, DB rows, private logs, caches, full raw traces, or
unrelated generated output.

## Sanitized Final Answer Summary

The final answer stated that the IRS 2026 business standard mileage rate is
72.5 cents per mile, effective January 1, 2026, and identified IRS IR-2025-128
and Internal Revenue Bulletin 2026-04 / Notice 2026-10 as the supporting IRS
authority.

## Final Cited URLs

- `https://www.irs.gov/newsroom/irs-sets-2026-business-standard-mileage-rate-at-725-cents-per-mile-up-25-cents`
- `http://irs.gov/irb/2026-04_IRB`

## Official / Canonical Visibility Summary

Sanitized export fields reported:

- `official_canonical_recovery_visibility_status`: visible
- `admission_used`: false
- `source_class_recovery_execution_attempted`: false
- `recovered_result_count`: 0
- `accepted_url_count`: 0
- `candidate_acquisition_provider_result_count`: 0
- `accepted_readable_authority_evidence_count`: 0
- `final_selected_authority_evidence_count`: 0
- `final_evidence_official_or_canonical_count`: 5
- `final_citation_official_or_canonical_count`: 2
- `final_evidence_survival_status`: visible
- `final_citation_survival_status`: visible
- `next_failure_layer`: admission_not_used
- `behavior_changed`: false

## Authority Candidate Passport Summary

Sanitized passport fields reported:

- `authority_candidate_passport_available`: true
- `authority_candidate_passport_schema_version`:
  authority_candidate_passport_ag73a_v1
- `authority_candidate_passport_count`: 0
- `authority_candidate_passport_integrity_status`: complete
- `authority_candidate_passport_final_dispositions`: []
- `authority_candidate_passport_first_missing_stages`: []

The passport projection was present but had no represented candidate records.
That is a diagnostic rough edge, not the chosen first-failure classification,
because the final official/current IRS evidence and final IRS citations reached
the answer surface.

## Provider-Result Bridge Summary

Sanitized bridge fields reported:

- `provider_result_bridge_available`: true
- `provider_result_bridge_schema_version`:
  provider_result_represented_visibility_ag73d_v1
- `provider_result_bridge_record_count`: 18
- `provider_result_bridge_disposition_counts`: not_represented_with_reason=6
- `provider_result_bridge_aggregate_reconciliation_status`:
  aggregate_provider_count_exceeds_visible_bridge_records
- `provider_result_bridge_unobservable_boundary`: provider-result to
  represented authority candidate

AG-73D-V populated during the live run. The bridge still showed an aggregate
reconciliation rough edge, but this did not prevent the official/current IRS
evidence from reaching final answer/citation.

## First-Failure Classification

Chosen classification:

```text
official/current IRS evidence reached final answer correctly
```

## Evidence For Classification

- The final answer made the exact 2026 business mileage-rate claim.
- The final answer cited two IRS URLs.
- The official/canonical export reported `final_evidence_official_or_canonical_count: 5`.
- The official/canonical export reported `final_citation_official_or_canonical_count: 2`.
- The official/canonical export reported final evidence and final citation
  survival as visible.

## Remaining Unobservable Boundary

Not applicable to the chosen first-failure classification. The remaining rough
edge is diagnostic: provider-result bridge aggregate reconciliation still
reported `provider-result to represented authority candidate` as unobservable,
and the authority candidate passport count remained zero.

## Recommended Next Phase

No immediate IRS repair; proceed to AG-74A controller evidence ledger work.

## Why No Repair Was Performed

This phase was licensed for one-run live custody validation only. The live run
already reached final official/current IRS evidence and IRS citations, and all
runtime behavior surfaces remained closed.

## Protected Surfaces Kept Closed

No code behavior was changed. No provider/search/query/depth/routing/prompt,
classification, candidate-fit, Controller, AnswerContract, context, Analyst,
Author, citation, final-answer, follow-up, Scrutineer, IRS hardcoding,
source-specific resolver, broad orchestrator, package/CLI/env compatibility, or
raw/private material surfaces were opened.

## Rough Edges

- The visibility export's official/canonical recovery lane reports
  `admission_not_used` even though final IRS evidence and citations were
  visible.
- The authority candidate passport projection was present with zero passports.
- The provider-result bridge populated but aggregate reconciliation reported
  `aggregate_provider_count_exceeds_visible_bridge_records`.
- These rough edges support AG-74A controller evidence ledger work rather than
  an immediate IRS repair.
