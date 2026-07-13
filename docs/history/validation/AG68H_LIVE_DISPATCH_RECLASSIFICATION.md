Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG68H_LIVE_DISPATCH_RECLASSIFICATION).

# AG-68H Live Dispatch Reclassification

Scope: bounded classification-only live validation after the AG-68G product
call-site repair. Two ProPlex live runs were used. No provider routing,
provider selection, provider depth, retrieval/ranking/filtering behavior,
query wording beyond the two fixed validation queries, prompt behavior,
citation/final-answer behavior, Author, Analyst, Economist, Scrutineer,
follow-up, or legal-answer behavior was changed.

## Purpose

AG-68H tested whether AG-68G moved the forced official/current recovery path
from admitted/eligible into actual source-class recovery execution in live
product runs.

Ordinary authoritative-source acquisition remained separate from missing-source
recovery success.

## Live Queries And Commands

Case 1 exact live query:

```text
What is the current Social Security taxable maximum wage base for 2026, and what official source supports it? Keep the answer concise.
```

Case 1 sanitized command shape:

```text
py -m proplex "<exact SSA query>" --mode Balanced --include-domains shrm.org,payroll.org,adp.com --output output\ag68h_case1_ssa_forced_corridor_live_report.md
```

Case 2 exact live query:

```text
What is the current IRS standard mileage rate for business use of a car in 2026, and what official source supports it? Keep the answer concise.
```

Case 2 sanitized command shape:

```text
py -m proplex "<exact IRS query>" --mode Balanced --include-domains taxfoundation.org,hrblock.com,shrm.org --output output\ag68h_case2_irs_forced_corridor_live_report.md
```

Live budget used: 2 of 2.

## Sanitized Result

Case 1, SSA, did not reach source-class recovery execution. Unlike the AG-68F
SSA result, admission was not used in AG-68H because a terminal stop was already
approved. The live product path therefore still did not prove dispatch movement
for the SSA sibling official/current corridor.

Case 2, IRS, no longer reproduced the AG-68F weak-corpus admission blocker.
It reached source-class recovery execution and returned candidates, but no
official/current evidence survived into final evidence or citations.

## SSA Diagnostics

```text
official_canonical_recovery_visibility_status=visible
admission_considered=true
admission_eligible=false
admission_used=false
admission_skip_reason=existing_runtime_blocker
admission_blockers=terminal_stop_approved
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
likely_next_failure_layer=admission_not_used
next_failure_layer=admission_not_used
behavior_changed=false
```

## IRS Diagnostics

```text
official_canonical_recovery_visibility_status=visible
admission_considered=true
admission_eligible=true
admission_used=true
admission_skip_reason=none
admission_blockers=[]
source_class_recovery_eligible=true
source_class_recovery_used=true
source_class_recovery_execution_attempted=true
source_class_recovery_skip_reason=none
source_class_recovery_provider_role=source_class_recovery
recovery_query_count=2
recovered_result_count=113
accepted_url_count=10
candidate_official_or_canonical_count=0
accepted_or_readable_official_or_canonical_count=2
final_evidence_official_or_canonical_count=0
final_citation_official_or_canonical_count=0
candidate_return_visibility_status=visible
candidate_return_status=candidates_returned
candidate_acquisition_considered=true
candidate_acquisition_eligible=true
candidate_acquisition_used=true
acquisition_attempted=true
candidate_acquisition_provider_result_count=23
candidate_acquisition_provider_accepted_url_count=12
candidate_acquisition_provider_new_source_count=11
candidate_acquisition_result_status=provider_results_returned
candidate_visibility_export_status=visible
official_canonical_candidate_visible=false
recovered_candidate_source_fit_status=not_evaluated
recovered_candidate_source_fit_count=0
recovered_candidate_selected_readable_count=0
accepted_readable_visibility_status=visible
final_evidence_survival_status=not_visible
final_citation_survival_status=not_visible
likely_next_failure_layer=candidate_returned_no_official_canonical_visible
next_failure_layer=canonical_candidate_returned_not_accepted
behavior_changed=false
```

## AG-68F vs AG-68H

| Field | AG-68F SSA | AG-68H SSA |
| --- | --- | --- |
| admission_used | true | false |
| admission_skip_reason | none | existing_runtime_blocker |
| admission_blockers | [] | terminal_stop_approved |
| source_class_recovery_execution_attempted | false | false |
| source_class_recovery_used | false | false |
| candidate_return_status | not_attempted | not_attempted |
| recovered_result_count | 0 | 0 |
| final official/current evidence visible | no | no |
| final official/current citation survived | no | no |
| next_failure_layer | execution_not_attempted | admission_not_used |

| Field | AG-68F IRS | AG-68H IRS |
| --- | --- | --- |
| admission_used | false | true |
| admission_skip_reason | existing_runtime_blocker | none |
| admission_blockers | weak_corpus_recovery_owns_path; blocked_by_corpus_weak | [] |
| source_class_recovery_execution_attempted | false | true |
| source_class_recovery_used | false | true |
| candidate_return_status | not_attempted | candidates_returned |
| recovered_result_count | 0 | 113 |
| final official/current evidence visible | no | no |
| final official/current citation survived | no | no |
| next_failure_layer | admission_not_used | canonical_candidate_returned_not_accepted |

## Case Classifications

| Field | SSA case 1 | IRS case 2 |
| --- | --- | --- |
| reliable_forced_corridor_available | yes | yes |
| live_budget_used | 1/2 | 2/2 |
| ordinary_authoritative_source_already_present | no | no |
| missing_authoritative_source_state_forced | yes | yes |
| authoritative_recovery_bridge_visible | yes | yes |
| authoritative_recovery_query_created | yes | yes |
| recovery_execution_admitted | no | yes |
| recovery_dispatch_authorized_or_attempted | no | yes |
| source_class_recovery_execution_attempted | no | yes |
| source_class_recovery_used | no | yes |
| recovered_result_count | 0 | 113 |
| candidate_return_status | not_attempted | candidates_returned |
| candidate_acquisition_considered | no | yes |
| candidate_acquisition_used | no | yes |
| recovered_evidence_visible | no | no |
| final_answer_citation_or_use | no | no |
| ordinary_acquisition_counted_as_recovery_success | no | no |
| next_failure_layer | admission_not_used | canonical_candidate_returned_not_accepted |

## Cross-Case Decision

AG-68G did not move the SSA live product call-site failure layer into actual
recovery dispatch. The SSA case now failed earlier at admission due to
`terminal_stop_approved`.

The IRS case reached dispatch, returned candidates, and then failed before
official/current evidence became visible in final evidence or citations. This
is not ordinary acquisition success.

Provider/search allocation review remains premature as a cross-case action:
one case dispatched and the other did not. The next recommended action is
focused generalization/arbitration repair before provider review, with separate
attention to the IRS recovered-evidence visibility/source-fit layer.

## Local Packet

Detailed local packet:

```text
output/ag68h_live_dispatch_reclassification_packet.md
```

Detailed live reports:

```text
output/ag68h_case1_ssa_forced_corridor_live_report.md
output/ag68h_case2_irs_forced_corridor_live_report.md
```

The packet and reports are ignored under `output/` and must not be committed.
No `.env`, API keys/secrets, raw provider payloads, raw prompts, DB rows,
private logs, caches, full raw traces, or unrelated generated output were
inspected or included.
