# AG-47B Active Batch Dispatch Live Output Quality Review R1

Date: May 24, 2026

Branch: `codex/ag47b-active-batch-output-quality-review-r1`

Base commit: `2fc45da` (`Merge pull request #71 from aidan600/codex/ag47a-active-batch-dispatch-ordinary-continuation`)

Scope: validation/review only. No runtime code, provider routing, provider selection, search depth, query generation, prompts, final-answer behavior, handoffs, legal/current-primary adapter behavior, social integration, or persistence behavior was changed.

## Live Budget

Budget used: 4 live ProPlex CLI runs out of 4 maximum.

No reruns were used. No live provider/model/search calls were run outside the four approved CLI commands.

Command shape:

```powershell
py -m proplex "<query>" --mode Balanced --output output\ag47b_case_outputs_tmp\<case>.md
```

The generated full case reports stayed under ignored `output/`. The local output-quality packet was created at:

`output/ag47b_output_quality_review_packet.md`

That packet is local/untracked and ignored by the repo `output/` rule.

## Exact Queries

| Case | Query |
|---|---|
| Q1 | Compare the 5-year total cost of ownership for a 2026 Toyota RAV4 Hybrid versus a Tesla Model Y for a driver in California who drives 12,000 miles per year. Include purchase price assumptions, fuel/electricity, maintenance, insurance if available, incentives or tax credits if relevant, and explain the biggest uncertainty. |
| Q2 | What are the current IRS contribution limits and income phaseouts for Roth IRA contributions in 2026, and how do they differ from 2025? Use current official sources where possible. |
| Q3 | What is the current status of NASA Artemis II, what changed most recently, and what are the next concrete milestones to watch? |
| Q4 | I am choosing between Obsidian, Notion, and Capacities for a personal knowledge base in 2026. Compare offline support, export/lock-in risk, AI features, collaboration, mobile experience, and which type of user each is best for. |

## Commands Used

```powershell
py -m proplex "Compare the 5-year total cost of ownership for a 2026 Toyota RAV4 Hybrid versus a Tesla Model Y for a driver in California who drives 12,000 miles per year. Include purchase price assumptions, fuel/electricity, maintenance, insurance if available, incentives or tax credits if relevant, and explain the biggest uncertainty." --mode Balanced --output output\ag47b_case_outputs_tmp\q1.md
py -m proplex "What are the current IRS contribution limits and income phaseouts for Roth IRA contributions in 2026, and how do they differ from 2025? Use current official sources where possible." --mode Balanced --output output\ag47b_case_outputs_tmp\q2.md
py -m proplex "What is the current status of NASA Artemis II, what changed most recently, and what are the next concrete milestones to watch?" --mode Balanced --output output\ag47b_case_outputs_tmp\q3.md
py -m proplex "I am choosing between Obsidian, Notion, and Capacities for a personal knowledge base in 2026. Compare offline support, export/lock-in risk, AI features, collaboration, mobile experience, and which type of user each is best for." --mode Balanced --output output\ag47b_case_outputs_tmp\q4.md
```

CLI-visible usage:

| Case | Elapsed | Calls | Cost |
|---|---:|---:|---:|
| Q1 | 166.0s | 19 | `$0.3477` |
| Q2 | 84.3s | 12 | `$0.1820` |
| Q3 | 39.1s | 13 | `$0.0060` |
| Q4 | 127.3s | 13 | `$0.2594` |

## High-Level Outcomes

| Case | Outcome |
|---|---|
| Q1 | Partial. Toyota-side purchase/MPG evidence was usable, but the answer did not produce a complete Tesla-side five-year TCO because final cited Tesla price, efficiency, electricity, maintenance, insurance, and incentive evidence was missing. |
| Q2 | Good. Answer used official IRS sources and directly compared 2026 and 2025 contribution limits and phaseouts. |
| Q3 | Weak. Answer caveated retrieval limitations, but final source fit was poor for a NASA current-status question and no official NASA source appeared in final citations. |
| Q4 | Acceptable. Answer covered all requested dimensions; source quality was mixed, with some primary Capacities docs and several secondary comparison sources. |

## Sanitized Trace Summary

| Case | Dispatch | Projection / readiness | Search summary | Recovery / protected-surface signal |
|---|---|---|---|---|
| Q1 | Authorized `ordinary_scout_directed_queries`; 4 authorized queries; blockers `[]`; provider/depth/query-generation policies `reuse_existing`; targeted executor false. | Projection authorized same scout lane; source-class lane blocked by `not_recommended`, `blocked_by_iteration_budget`; readiness true and protected flags true. | 6 sanitized search attempts; providers Tavily/Exa; role `main_retrieval`; visible depth `basic`. | `retrieve_targeted` provider role false; source-class/weak-corpus/conflict used false. |
| Q2 | Not authorized; selected lane none; blockers include `no_selected_authorized_lane`, `dispatch_not_authorized_by_spine`, `readiness_not_ready`, `authorized_lane_count_not_one`. | Projection blocked with source-class/currentness/legal-current blockers; readiness false but protected flags true. | 2 sanitized search attempts; provider Tavily; role `main_retrieval`; visible depth `basic`. | `retrieve_targeted` provider role false; targeted executor false; source-class/weak-corpus/conflict used false. |
| Q3 | Dispatch trace authorized `ordinary_evaluator_gap_queries`; 2 authorized queries; targeted executor false; no `retrieve_targeted` provider role. | Top-level projection summary reported `blocked` with selected lane null and source-class/currentness/news blockers, while dispatch/readiness summary reported evaluator ordinary lane ready/authorized. This disagreement needs follow-up. | 5 sanitized search attempts; providers Brave/Tavily; roles `recon`, `main_retrieval`; visible depth `basic`. | Protected flags visible as true; source-class/weak-corpus/conflict used false. |
| Q4 | Authorized `ordinary_expander_component_queries`; 2 authorized queries; blockers `[]`; targeted executor false. | Projection authorized same expander lane; source-class lane blocked by `not_recommended`, `blocked_by_iteration_budget`; readiness true and protected flags true. | 4 sanitized search attempts; provider Tavily; role `main_retrieval`; visible depth `basic`. | `retrieve_targeted` provider role false; source-class/weak-corpus/conflict used false. |

## Answer-Quality Summary

| Case | Source fit | Currentness | Citation quality | Completeness | Posture / risk |
|---|---|---|---|---|---|
| Q1 | Mixed/weak. Toyota evidence fit; Tesla evidence missing. | Mixed. 2026 Toyota evidence visible; Tesla/current incentive inputs absent. | Acceptable for Toyota, insufficient for full TCO. | Incomplete for requested comparison. | Caveats mostly matched missing evidence; moderate overclaim risk on directional Tesla comments. |
| Q2 | Strong. Official IRS pages/releases only. | Strong from visible official-source set. | Good, with one duplicated IRS URL label. | Good. | Low visible overclaim risk. |
| Q3 | Poor for official/current NASA status. | Risky because official NASA source absent. | Weak; secondary/off-domain sources dominate. | Partial. | Caveat helps, but opening status claim is too definitive for visible evidence. |
| Q4 | Acceptable for recommendation context. | Acceptable. | Mixed; primary Capacities docs plus secondary comparisons. | Good. | Low-to-moderate risk around Notion AI/collaboration claims due to secondary sourcing. |

## Protected-Surface Scan

No code was changed. No protected-surface implementation drift was introduced by this validation phase.

Visible sanitized telemetry showed:

- provider roles stayed existing roles such as `main_retrieval` and `recon`;
- no `retrieve_targeted` provider role appeared;
- `targeted_retrieval_executor_dispatched` stayed false in all four cases;
- dispatch/provider/depth/query-generation policies stayed `reuse_existing`;
- protected flags for provider policy, depth policy, query generation, prompts, runtime behavior, targeted executor, retrieve-targeted provider role, orphan dispatch, and ordinary conflict separation were true where visible;
- source-class, weak-corpus, and conflict recovery executions were not used in the four runs.

This validation did not read or commit secrets, API keys, raw provider payloads, raw prompts, full raw traces, DB rows, caches, or unrelated generated outputs.

## Decision

Validation decision: `pass_with_followup`.

AG-47A active batch dispatch appears behavior-preserving in this bounded round: ordinary lanes reused existing retrieval mechanics, no targeted executor was dispatched, and no `retrieve_targeted` provider role appeared.

The round does not qualify as `pass_for_round_1` because answer quality was uneven and Q3 exposed a sanitized trace-consistency rough edge between top-level projection summary and dispatch summary. The observed issues do not yet require an architecture stop: the protected surfaces stayed clean, and the issues look like review/follow-up items rather than evidence that the active-batch architecture is unsafe.

## Known Rough Edges

- Q1 did not deliver a complete Tesla-side five-year TCO despite scout-directed follow-up queries.
- Q2 source list duplicated the IRS IRA contribution URL under two labels.
- Q3 lacked official NASA citations and used secondary/off-domain material for a current-status answer.
- Q3 had a visible projection-vs-dispatch telemetry disagreement: dispatch authorized evaluator ordinary continuation, while top-level projection summary reported a blocked batch with no selected lane.
- Q4 leaned on secondary product-comparison sources for Notion/Obsidian feature claims.

## Recommended Next Action

Run a focused offline/trace review of AG-47A projection/dispatch consistency, especially for Q3-style evaluator ordinary continuation after currentness/source-class blockers are present. Separately, keep answer-quality/source-fit review open before broader rollout, with priority on official/current source acquisition for current-event and product-feature claims.

## Artifact Criteria

Local packet:

- Path: `output/ag47b_output_quality_review_packet.md`
- Consumer: ChatGPT/user review of full answers, citations, visible source sections, and sanitized batch/controller telemetry.
- Decision criterion: decide whether AG-47A live output status is clean enough for round 1 or needs follow-up.
- Deletion criterion: may be deleted after reviewer sign-off or superseded by a later output-quality packet.

Committed validation note:

- Path: `docs/validation/AG47B_ACTIVE_BATCH_OUTPUT_QUALITY_REVIEW_R1.md`
- Consumer: future phase planning and durable validation history.
- Decision criterion: preserve the bounded live outcome and follow-up recommendation without committing full answer text.
- Deletion criterion: retain unless superseded by an explicit later validation summary.
