Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG67B_FORCED_CORRIDOR_LIVE_CLASSIFICATION).

# AG-67B Forced-Corridor Live Classification

Scope: classification-only. One bounded ProPlex live run was used after focused
offline tests passed. No provider routing, provider selection, provider depth,
retrieval/ranking/filtering behavior, prompt behavior, citation behavior,
final-answer behavior, Author, Analyst, Economist, Scrutineer, follow-up, or
legal-answer behavior was changed.

## Purpose

AG-67B tested whether the real product path can be made to exercise the
missing-authoritative-source recovery corridor rather than merely succeeding
through ordinary acquisition. AG-64D showed that ordinary official IRS evidence
can reach the answer without proving missing-source recovery. Therefore,
ordinary acquisition success was not counted as recovery success in this phase.

## Pre-Live Feasibility Checkpoint

A. Mechanism: the existing CLI `--include-domains` option bounded ordinary
acquisition to lower-tier context domains, while the existing source-class
recovery executor can add controller-provided official recovery domain
constraints such as `irs.gov` and federal domains to the recovery pass.

B. Missing-authoritative state proof: report diagnostics can show
`admission_used=true` plus `recovery_query_count>0`; AG-50B only admits when an
unsatisfied required official/current/canonical class is visible and a recovery
query is available. In the actual run, the missing-official corridor was visible
through secondary-only final evidence, no final official/canonical evidence, and
nonzero recovery queries.

C. Recovery readiness/admission proof:
`admission_considered`, `admission_eligible`, `admission_used`, and
`source_class_recovery_eligible`.

D. Dispatch proof: `source_class_recovery_used` and
`source_class_recovery_execution_attempted`.

E. Recovered-evidence visibility proof: `recovered_result_count`,
`accepted_or_readable_official_or_canonical_count`,
`recovered_candidate_selected_readable_count`, and final official/canonical
evidence/citation counts.

F. Ordinary acquisition classification: `admission_used=false` with
`admission_skip_reason=existing_source_class_satisfied` plus positive final
official/canonical evidence or citation counts is ordinary acquisition only, not
recovery success.

G. Why the command was not merely ordinary acquisition: the exact fixed IRS
query was run through an ordinary lower-tier allow-list, and only the recovery
path had the existing official-domain expansion needed to reach `irs.gov`.

Pre-live checkpoint: passed.

## Live Query And Command

Exact live query:

```text
What is the current IRS standard mileage rate for business use of a car in 2026, and what official source supports it? Keep the answer concise.
```

Sanitized command shape:

```text
py -m proplex "<exact IRS query>" --mode Balanced --include-domains taxfoundation.org,hrblock.com,shrm.org --output output\ag67b_forced_corridor_live_report.md
```

Live budget used: 1 of 1.

## Live Result

The final answer did not retrieve or cite an official IRS source. It safely
reported that the retrieved corpus could not verify the 2026 IRS business
standard mileage rate and cited only secondary/context sources from Tax
Foundation and SHRM.

Sanitized report-visible diagnostics:

```text
admission_considered=true
admission_eligible=false
admission_used=false
admission_skip_reason=official_canonical_acquisition_path_not_visible
source_class_recovery_eligible=false
source_class_recovery_used=false
source_class_recovery_execution_attempted=false
source_class_recovery_skip_reason=blocked_by_iteration_budget
recovery_query_count=2
recovery_query_previews=IRS official documentation reference manual; IRS reference documentation official docs
recovered_result_count=0
accepted_url_count=0
final_evidence_official_or_canonical_count=0
final_citation_official_or_canonical_count=0
candidate_return_status=not_attempted
candidate_acquisition_considered=false
candidate_acquisition_eligible=false
candidate_acquisition_used=false
acquisition_query_count=0
acquisition_attempted=false
recovered_candidate_source_fit_status=not_evaluated
recovered_candidate_selected_readable_count=0
final_evidence_survival_status=not_visible
final_citation_survival_status=not_visible
likely_next_failure_layer=admission_not_used
next_failure_layer=admission_not_used
behavior_changed=false
```

## Classification

| Field | Classification |
| --- | --- |
| reliable_forced_corridor_available | yes |
| pre_live_feasibility_checkpoint_passed | yes |
| live_budget_used | 1/1 |
| ordinary_authoritative_source_already_present | no |
| missing_authoritative_source_state_forced | yes |
| authoritative_recovery_bridge_visible | unknown |
| authoritative_recovery_query_created | yes |
| recovery_execution_admitted | no |
| recovery_dispatch_authorized_or_attempted | no |
| recovered_evidence_visible | not_applicable |
| final_answer_citation_or_use | no |
| ordinary_acquisition_counted_as_recovery_success | no |
| next_failure_layer | admission_not_used / official_canonical_acquisition_path_not_visible |

## Conclusion

The forced corridor was useful: it prevented ordinary official IRS acquisition
from masking the result. The live product path did not prove AG-64ABC/IRS
dispatch recovery fixed. It reached a missing-official-source classification
surface with recovery queries visible, but the official/canonical execution
admission path did not use the recovery slot, source-class recovery dispatch was
not attempted, and no recovered evidence became visible.

Next recommended failure layer: focused controller/action-readiness or
admission-path visibility. Provider/search allocation review should remain
closed until a future run proves actual recovery dispatch executed and failed to
acquire an authoritative source.

## Local Packet

Detailed local packet:

```text
output/ag67b_forced_corridor_live_packet.md
```

Detailed live report:

```text
output/ag67b_forced_corridor_live_report.md
```

Both are ignored under `output/` and must not be committed. No `.env`, API
keys/secrets, raw provider payloads, raw prompts, DB rows, private logs, caches,
full raw traces, or unrelated generated output were inspected or included.
