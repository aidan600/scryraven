Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG68F_TWO_CASE_FORCED_CORRIDOR_LIVE_RECLASSIFICATION).

# AG-68F Two-Case Forced-Corridor Live Reclassification

Scope: classification-only. Two bounded ProPlex live runs were used after
focused offline tests passed. No provider routing, provider selection, provider
depth, retrieval/ranking/filtering behavior, prompt behavior,
citation/final-answer behavior, Author, Analyst, Economist, Scrutineer,
follow-up, or legal-answer behavior was changed.

## Purpose

AG-68F tested whether AG-68E's live/offline dispatch parity repair moves the
forced official/current corridor from admitted and eligible but not executed
into actual source-class recovery execution. The phase used the repeated IRS
forced corridor and one sibling official/current numeric-rule corridor for the
SSA 2026 taxable maximum wage base.

Ordinary official-source acquisition remained separate from missing-source
recovery success.

## Live Queries And Commands

Case 1 exact live query:

```text
What is the current IRS standard mileage rate for business use of a car in 2026, and what official source supports it? Keep the answer concise.
```

Case 1 sanitized command shape:

```text
py -m proplex "<exact IRS query>" --mode Balanced --include-domains taxfoundation.org,hrblock.com,shrm.org --output output\ag68f_case1_irs_forced_corridor_live_report.md
```

Case 2 exact live query:

```text
What is the current Social Security taxable maximum wage base for 2026, and what official source supports it? Keep the answer concise.
```

Case 2 sanitized command shape:

```text
py -m proplex "<exact SSA query>" --mode Balanced --include-domains shrm.org,payroll.org,adp.com --output output\ag68f_case2_ssa_forced_corridor_live_report.md
```

Live budget used: 2 of 2.

## Sanitized Result

Case 1, IRS, did not retrieve or cite an official IRS standard-mileage-rate
source. Unlike AG-68B and AG-68D, the live path did not preserve admission:
weak-corpus ownership blocked source-class recovery before dispatch.

Case 2, SSA, retrieved only non-official payroll-industry sources and did not
retrieve or cite an official SSA/IRS source for the 2026 taxable maximum wage
base. Recovery admission remained visible, but source-class recovery execution
was not attempted.

## IRS Diagnostics

```text
official_canonical_recovery_visibility_status=visible
admission_considered=true
admission_eligible=false
admission_used=false
admission_skip_reason=existing_runtime_blocker
admission_blockers=weak_corpus_recovery_owns_path; blocked_by_corpus_weak
source_class_recovery_eligible=false
source_class_recovery_used=false
source_class_recovery_execution_attempted=false
source_class_recovery_skip_reason=blocked_by_weak_corpus_recovery
source_class_recovery_provider_role=unknown
recovery_query_count=2
recovered_result_count=0
accepted_url_count=0
candidate_return_status=not_attempted
candidate_acquisition_considered=false
candidate_acquisition_eligible=false
candidate_acquisition_used=false
acquisition_attempted=false
recovered_candidate_selected_readable_count=0
final_evidence_official_or_canonical_count=0
final_citation_official_or_canonical_count=0
final_evidence_survival_status=not_visible
final_citation_survival_status=not_visible
likely_next_failure_layer=admission_not_used
next_failure_layer=admission_not_used
behavior_changed=false
```

## SSA Diagnostics

```text
official_canonical_recovery_visibility_status=visible
admission_considered=true
admission_eligible=true
admission_used=true
admission_skip_reason=none
admission_blockers=[]
source_class_recovery_eligible=true
source_class_recovery_used=false
source_class_recovery_execution_attempted=false
source_class_recovery_skip_reason=none
source_class_recovery_provider_role=source_class_recovery
recovery_query_count=2
recovered_result_count=0
accepted_url_count=0
candidate_return_status=not_attempted
candidate_acquisition_considered=false
candidate_acquisition_eligible=false
candidate_acquisition_used=false
acquisition_attempted=false
recovered_candidate_selected_readable_count=0
final_evidence_official_or_canonical_count=0
final_citation_official_or_canonical_count=0
final_evidence_survival_status=not_visible
final_citation_survival_status=not_visible
likely_next_failure_layer=execution_not_attempted
next_failure_layer=execution_not_attempted
behavior_changed=false
```

## AG-67B vs AG-68B vs AG-68D vs AG-68F IRS

| Field | AG-67B | AG-68B | AG-68D | AG-68F case 1 |
| --- | --- | --- | --- | --- |
| admission_used | false | true | true | false |
| admission_skip_reason | official_canonical_acquisition_path_not_visible | none | none | existing_runtime_blocker |
| source_class_recovery_eligible | false | true | true | false |
| source_class_recovery_used | false | false | false | false |
| source_class_recovery_execution_attempted | false | false | false | false |
| recovered_result_count | 0 | 0 | 0 | 0 |
| candidate_return_status | not_attempted | not_attempted | not_attempted | not_attempted |
| final official/canonical evidence count | 0 | 0 | 0 | 0 |
| final official/canonical citation count | 0 | 0 | 0 | 0 |
| next_failure_layer | admission_not_used | execution_not_attempted | execution_not_attempted | admission_not_used |

## Case Classifications

| Field | IRS case 1 | SSA case 2 |
| --- | --- | --- |
| reliable_forced_corridor_available | yes | yes |
| live_budget_used | 1/2 | 2/2 |
| ordinary_authoritative_source_already_present | no | no |
| missing_authoritative_source_state_forced | yes | yes |
| authoritative_recovery_bridge_visible | yes | yes |
| authoritative_recovery_query_created | yes | yes |
| recovery_execution_admitted | no | yes |
| recovery_dispatch_authorized_or_attempted | no | no |
| source_class_recovery_execution_attempted | no | no |
| source_class_recovery_used | no | no |
| recovered_result_count | 0 | 0 |
| candidate_return_status | not_attempted | not_attempted |
| candidate_acquisition_considered | no | no |
| candidate_acquisition_used | no | no |
| recovered_evidence_visible | no | no |
| final_answer_citation_or_use | no | no |
| ordinary_acquisition_counted_as_recovery_success | no | no |
| next_failure_layer | admission_not_used | execution_not_attempted |

## Cross-Case Decision

Neither case reached `source_class_recovery_execution_attempted=true`.
Therefore AG-68E did not move the live failure layer into actual recovery
dispatch for these forced official/current corridors.

Provider/search allocation review remains premature because actual recovery
dispatch did not execute and fail to acquire authoritative candidates. The next
recommended action is focused live/product dispatch repair, with attention to
why the repeated IRS corridor is now blocked by weak-corpus ownership while the
SSA sibling corridor remains admitted but not executed.

## Local Packet

Detailed local packet:

```text
output/ag68f_two_case_forced_corridor_live_packet.md
```

Detailed live reports:

```text
output/ag68f_case1_irs_forced_corridor_live_report.md
output/ag68f_case2_ssa_forced_corridor_live_report.md
```

The packet and reports are ignored under `output/` and must not be committed.
No `.env`, API keys/secrets, raw provider payloads, raw prompts, DB rows,
private logs, caches, full raw traces, or unrelated generated output were
inspected or included.
