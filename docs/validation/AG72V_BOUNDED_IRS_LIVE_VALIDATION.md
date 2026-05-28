# AG-72V Bounded IRS Official/Current Live Validation Gate

Scope: Review Lane live-validation gate. This phase ran exactly two approved
product-path ScryRaven/proplex validations to classify the remaining IRS
official/current acquisition sublayer. No behavior repair was made.

Branch: `codex/ag72v-bounded-irs-live-validation`

Base commit: `5426e1d` (`Merge pull request #5 from aidan600/codex/ag72r-provider-search-allocation-review`)

## Budget

Approved live ScryRaven/proplex budget: exactly 2 product-path runs.

Actual product-path live runs used: 2.

A prior mechanical key preflight failure stopped before the product pipeline
started and used 0 product-path live runs. No additional live queries,
independent browser/search checks, raw provider payloads, raw prompts, DB rows,
private logs, caches, full raw traces, secrets, or `.env` contents were
inspected.

## Harness

The gate reused the AG-70C IRS forced-corridor command shape: compatibility CLI,
Balanced mode, and the IRS secondary-domain corridor. Public `scryraven` aliases
remain supported, but the documented live harness still used `py -m proplex`.

Case 1:

```powershell
py -m proplex "<case 1 query>" --mode Balanced --include-domains taxfoundation.org,hrblock.com,shrm.org --output output\ag72v_case1_irs_business_mileage_live_report.md
```

Case 2:

```powershell
py -m proplex "<case 2 query>" --mode Balanced --include-domains taxfoundation.org,hrblock.com,shrm.org --output output\ag72v_case2_irs_medical_moving_mileage_live_report.md
```

## Exact Queries

1. `What is the current IRS standard mileage rate for business use of a car in 2026, and what official source supports it? Keep the answer concise.`
2. `What is the current IRS standard mileage rate for medical or moving purposes in 2026, and what official source supports it? Keep the answer concise.`

## Result Table

| Case | Final answer result | Final cited URLs | AG-72V category |
| --- | --- | --- | --- |
| Business mileage | Refused to verify the 2026 IRS business standard mileage rate because the needed official IRS source was not in the retrieved corpus. | `shrm.org/in/topics-tools/news/benefits-compensation/irs-lowers-standard-mileage-rate-2021` | 5. source-specific IRS/federal resolver likely |
| Medical or moving mileage | Refused to verify the 2026 medical/moving standard mileage rate because no official IRS source supporting that rate was present. | `npr.org`, `politico.com`, `cbsnews.com` IRS-adjacent news/legal-settlement items | 5. source-specific IRS/federal resolver likely, with an admission-path anomaly |

## Sanitized Diagnostic Table

| Field | Case 1 business | Case 2 medical/moving |
| --- | --- | --- |
| `admission_used` | true | false |
| `admission_skip_reason` | none | `official_canonical_acquisition_path_not_visible` |
| `source_class_recovery_execution_attempted` | true | true |
| `recovery_query_count` | 2 | 2 |
| `recovery_query_previews` | IRS official documentation reference manual; IRS reference documentation official docs | IRS official documentation reference manual; IRS reference documentation official docs |
| `recovered_result_count` | 98 | 65 |
| `accepted_url_count` | 13 | 3 |
| `recovered_candidate_domain_preview` | hrblock.com; taxfoundation.org; files.taxfoundation.org; media.hrblock.com; shrm.org | cbsnews.com; shrm.org; apnews.com |
| `candidate_acquisition_provider_result_count` | 24 | 12 |
| `candidate_acquisition_provider_accepted_url_count` | 24 | 5 |
| `candidate_acquisition_provider_new_source_count` | 17 | 5 |
| `candidate_acquisition_result_status` | `provider_results_returned` | `provider_results_returned` |
| `accepted_readable_authority_evidence_count` | 0 | 0 |
| `final_selected_authority_evidence_count` | 0 | 0 |
| `official_canonical_candidate_visible` | false | false |
| `recovered_candidate_source_fit_status` | `no_matching_source_fit` | `no_matching_source_fit` |
| `recovered_candidate_selected_readable_count` | 0 | 0 |
| `citation_eligibility_state` | `explained_ineligible` | `explained_ineligible` |
| `final_evidence_survival_status` | `not_visible` | `not_visible` |
| `final_citation_survival_status` | `not_visible` | `not_visible` |
| `next_failure_layer` | `canonical_candidate_returned_not_accepted` | `admission_not_used` |

## Classification Decision

Primary decision category: 5. source-specific IRS/federal resolver likely.

The live diagnostics do not support a simple provider-acquisition-zero result:
both cases had provider results, accepted URLs, and recovered results. The
diagnostics also do not show accepted/readable or final-selected authority that
then failed downstream citation or answer use.

The strongest shared signal is that both IRS sibling queries failed to surface
IRS/federal authority in the visible recovered-domain previews. Case 1 clustered
around secondary tax/payroll domains, while case 2 clustered around news and
secondary domains. Both answers correctly refused to overclaim because no
official/current IRS authority reached accepted/readable or final-selected
evidence.

Case 2 additionally shows an admission-path anomaly
(`official_canonical_acquisition_path_not_visible`) even though source-class
recovery execution and candidate acquisition still report attempted provider
results. That should be reviewed as part of the next design/diagnostic branch,
but it does not change the cross-case result: neither sibling query surfaced
IRS/federal authority.

## Cross-Case Diagnosis

Both cases fail the IRS-source-class surface rather than diverging into a
query-specific success/failure split. The shared live layer is not downstream
citation/final-answer behavior because no accepted/readable or final-selected
official/current IRS authority existed for the Author to cite.

The issue is also not proven to require provider routing, provider depth,
provider selection, provider swaps, prompt changes, retrieval ranking/filtering,
or final-answer changes. The next action should be design/diagnostic, not an
immediate behavior repair.

## Local Packet

Detailed local packet:

```text
output/ag72v_bounded_irs_live_validation_packet.md
```

Detailed live reports:

```text
output/ag72v_case1_irs_business_mileage_live_report.md
output/ag72v_case2_irs_medical_moving_mileage_live_report.md
```

Before live validation, `git check-ignore -v` confirmed all three paths are
ignored by `.gitignore` through `output/`. The packet and reports remain local,
ignored, and untracked.

## Closed Surfaces

No changes were made to provider routing, provider selection, provider depth,
search depth, provider swaps, new providers, retrieval ranking/filtering,
prompts, citation behavior, final-answer behavior, Author posture,
Analyst/Economist/Author handoffs, direct IRS hardcoding, broad
`core/pipeline_orchestrator.py` domain logic, follow-up behavior,
Streamlit/product behavior, package/CLI/env compatibility, state keys, or DB
compatibility names.

## Recommendation

Recommended next branch: AG-72B source-specific IRS/federal resolver design
review.

That branch should decide whether ScryRaven needs a bounded source-specific
IRS/federal resolver strategy or additional sanctioned diagnostics before any
provider-depth, provider-allocation, provider-swap, query-generation, prompt,
ranking/filtering, citation, or final-answer repair is attempted.
