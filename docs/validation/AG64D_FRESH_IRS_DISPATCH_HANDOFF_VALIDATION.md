# AG-64D Fresh IRS Dispatch-Handoff Validation

## Purpose

AG-64D ran one fresh bounded IRS-only live ProPlex validation to classify
whether AG-64ABC's offline-proven dispatch-handoff fix executes the intended
IRS/high-signal official-current recovery action in the live product path.

This was classification-only. No runtime, prompt, provider, routing, depth,
citation, Author, Analyst, Economist, Scrutineer, follow-up, or source-ranking
behavior was changed.

## Query And Command

Exact live query:

```text
What is the current IRS standard mileage rate for business use of a car in 2026, and what official source supports it? Keep the answer concise.
```

Sanitized command shape:

```text
py -m proplex "<exact IRS query>" --mode Balanced --output output\ag64d_irs_dispatch_live_report.md
```

Live budget used: 1 of 1.

## Offline Validation

Focused checks passed before the live run:

```text
160 passed
```

Covered suites:

- AG-64ABC controller-owned official/current recovery;
- controller loop spine dispatch;
- source-class recovery executor and lifecycle;
- official/current query acquisition and execution admission;
- source classifier and source-class recovery controller;
- recovered evidence visibility.

Lightweight hygiene also passed:

```text
py -m ruff check core tests docs
All checks passed.
```

## Live Classification

The final answer itself succeeded on official IRS evidence: it cited the IRS
Newsroom release for the 2026 business standard mileage rate and IRS Notice
2026-10, and it answered 72.5 cents per mile effective January 1, 2026.

However, the repaired AG-64ABC dispatch handoff was not exercised in this live
run. Report-visible diagnostics showed:

```text
admission_considered=true
admission_eligible=false
admission_used=false
admission_skip_reason=official_canonical_acquisition_path_not_visible
source_class_recovery_eligible=false
source_class_recovery_used=false
source_class_recovery_execution_attempted=false
source_class_recovery_skip_reason=no_recovery_queries
recovery_query_count=0
recovery_query_previews=[]
final_evidence_official_or_canonical_count=5
final_citation_official_or_canonical_count=2
final_evidence_survival_status=visible
final_citation_survival_status=visible
next_failure_layer=admission_not_used
behavior_changed=false
```

## Required Answers

1. Did the intended IRS/high-signal official-current recovery query execute?
   No. The specific high-signal IRS recovery query did not appear, no recovery
   query was present, and source-class recovery execution was not attempted.
2. Was an official IRS/current source acquired?
   Yes, but through the ordinary product evidence path rather than the repaired
   recovery dispatch path.
3. Was it accepted / visible in evidence?
   Yes for final evidence and citations; not through recovered evidence.
4. Was it cited in the final answer?
   Yes. The final answer cited official IRS sources.
5. Did the answer posture remain safe if acquisition or citation failed?
   Yes. In this run acquisition and citation succeeded; the answer was concise
   and official-source-bound.
6. What is the next failure layer?
   For AG-64D's dispatch-handoff question, the live run is unproven rather than
   a dispatch success. The report-visible layer is `admission_not_used` /
   `official_canonical_acquisition_path_not_visible`, with no recovery query
   created because official/current evidence was already visible.

## Decision Outcome

AG-64D does not prove the AG-64ABC final dispatch-handoff fix in live product
execution. The product answer succeeded, but the intended IRS recovery action
did not execute.

Per the phase decision tree, if the intended IRS recovery query does not
execute, the next recommendation is a focused dispatch/lifecycle validation or
repair surface. Given this run acquired official IRS evidence before recovery,
the next phase should first ensure the validation corridor actually reaches a
missing-official-current obligation state before repairing behavior.

## Local Packet

Detailed local packet:

```text
output/ag64d_irs_dispatch_live_packet.md
```

Detailed live report:

```text
output/ag64d_irs_dispatch_live_report.md
```

Both are under ignored `output/` and must not be committed.

No raw provider payloads, raw prompts, DB rows, private logs, caches, full raw
traces, `.env`, or secrets were inspected or included.
