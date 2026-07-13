Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG47D_POST_FIX_OUTPUT_TRACE_SANITY_REVIEW_R1).

# AG-47D Post-Fix Output/Trace Sanity Review R1

Date: May 24, 2026

Branch: `codex/ag47d-post-fix-output-trace-sanity-r1`

Base commit: `32d06a8` (`Merge pull request #74 from aidan600/codex/ag47c-projection-dispatch-consistency`)

Phase commit: the commit containing this validation note.

Scope: validation/review only. No runtime code, provider routing, provider
selection, search depth, query generation, prompts, final-answer behavior,
handoffs, legal/current-primary adapter behavior, social integration, or
persistence behavior was changed.

## Live Budget

Budget used: 4 live ProPlex CLI runs out of 4 maximum.

No reruns were used. No live provider/model/search calls were run outside the
four approved CLI commands.

Command shape:

```powershell
py -m proplex "<query>" --mode Balanced --output output\ag47d_case_outputs_tmp\<case>.md
```

Full final answers and detailed sanitized per-case notes were written to the
local ignored packet:

`output/ag47d_output_trace_sanity_packet.md`

The packet was confirmed ignored by `.gitignore` and is not tracked.

## Exact Queries

| Case | Query |
|---|---|
| Q1 | What are the 2026 Social Security cost-of-living adjustment, taxable maximum, earnings test exempt amounts, and maximum monthly SSI federal payment amounts, and how do they compare with 2025? Use official SSA sources where possible. |
| Q2 | What is the current status of Boeing Starliner crewed operations, what changed most recently, and what milestones must happen before NASA flies another crew on Starliner? |
| Q3 | For a California homeowner replacing a failing gas furnace and central AC in 2026, compare the 5-year cost and practical tradeoffs of installing a heat pump system versus a new gas furnace plus AC. Include equipment assumptions, energy costs, incentives or rebates if relevant, maintenance, comfort, and biggest uncertainty. |
| Q4 | Explain how SQLite write-ahead logging works, why it improves concurrency, and when WAL mode is a bad idea. Include the main tradeoffs without assuming the reader is a database expert. |

## Commands Used

```powershell
py -m proplex "What are the 2026 Social Security cost-of-living adjustment, taxable maximum, earnings test exempt amounts, and maximum monthly SSI federal payment amounts, and how do they compare with 2025? Use official SSA sources where possible." --mode Balanced --output output\ag47d_case_outputs_tmp\q1.md
py -m proplex "What is the current status of Boeing Starliner crewed operations, what changed most recently, and what milestones must happen before NASA flies another crew on Starliner?" --mode Balanced --output output\ag47d_case_outputs_tmp\q2.md
py -m proplex "For a California homeowner replacing a failing gas furnace and central AC in 2026, compare the 5-year cost and practical tradeoffs of installing a heat pump system versus a new gas furnace plus AC. Include equipment assumptions, energy costs, incentives or rebates if relevant, maintenance, comfort, and biggest uncertainty." --mode Balanced --output output\ag47d_case_outputs_tmp\q3.md
py -m proplex "Explain how SQLite write-ahead logging works, why it improves concurrency, and when WAL mode is a bad idea. Include the main tradeoffs without assuming the reader is a database expert." --mode Balanced --output output\ag47d_case_outputs_tmp\q4.md
```

CLI-visible usage:

| Case | Elapsed | Calls | Cost |
|---|---:|---:|---:|
| Q1 | 34.0s | 18 | `$0.0076` |
| Q2 | 45.9s | 16 | `$0.0025` |
| Q3 | 173.9s | 20 | `$0.4024` |
| Q4 | 79.6s | 15 | `$0.1566` |

## High-Level Outcomes

| Case | Outcome |
|---|---|
| Q1 | Failed product goal. Dispatch/projection were clean, but no official SSA source survived and no requested 2026/2025 numeric values were answered. |
| Q2 | Failed product goal. The answer correctly refused to answer from off-topic retrieval, but the current Starliner official/news source mix did not survive. |
| Q3 | Useful with caveats. It answered most requested dimensions and avoided over-precise five-year math, but source fit was mostly secondary/proxy and no fully source-bound 5-year cost model emerged. |
| Q4 | Acceptable conceptual answer. It was clear and concise, though it cited general WAL/storage papers rather than SQLite primary documentation. |

## Sanitized Trace Summary

| Case | Dispatch | Projection/readiness | Search/recovery |
|---|---|---|---|
| Q1 | Authorized `ordinary_scout_directed_queries`; 4 authorized queries; blockers `[]`; targeted executor false; no `retrieve_targeted` provider role. | Projection selected same scout lane with `projection_reconciled_with_dispatch=true`; source-class/currentness blockers remained visible as non-selected blocker state; readiness true. | 6 search attempts; providers Tavily/Exa; role `main_retrieval`; source-class/weak-corpus/conflict used false. |
| Q2 | Dispatch not considered/authorized; blocked reason `not_evaluated`; targeted executor false; no `retrieve_targeted` provider role. | Projection authorized separate `weak_corpus_recovery_queries`; no ordinary dispatch/projection contradiction. | 7 search attempts; providers Brave/Tavily; roles `recon`, `main_retrieval`, `disambiguation_retry`, `weak_corpus_recovery`; weak-corpus recovery used true. |
| Q3 | Authorized `ordinary_scout_directed_queries`; 4 authorized queries; blockers `[]`; targeted executor false; no `retrieve_targeted` provider role. | Projection selected same scout lane with `projection_reconciled_with_dispatch=true`; source-class blocker remained non-selected; readiness true. | 6 search attempts; providers Tavily/Exa; role `main_retrieval`; source-class/weak-corpus/conflict used false. |
| Q4 | Authorized `ordinary_expander_component_queries`; 2 authorized queries; blockers `[]`; targeted executor false; no `retrieve_targeted` provider role. | Projection selected same expander lane with `projection_reconciled_with_dispatch=true`; source-class blocker remained non-selected; readiness true. | 4 search attempts; provider Exa; role `main_retrieval`; source-class/weak-corpus/conflict used false. |

## Dispatch/Projection Consistency

AG-47C's reconciliation appeared in all three authorized ordinary-lane cases:

- Q1: dispatch selected `ordinary_scout_directed_queries`; final projection selected the same lane and reported `dispatch_trace_authoritative=true`.
- Q3: dispatch selected `ordinary_scout_directed_queries`; final projection selected the same lane and reported `dispatch_trace_authoritative=true`.
- Q4: dispatch selected `ordinary_expander_component_queries`; final projection selected the same lane and reported `dispatch_trace_authoritative=true`.

Q2 did not authorize ordinary dispatch. Its projection selected a separate
weak-corpus recovery lane, so it did not exercise the AG-47C overlay path.

## Answer-Quality Summary

| Case | Source fit | Currentness | Citation quality | Completeness | Posture/risk |
|---|---|---|---|---|---|
| Q1 | Poor for official SSA. | Poor for requested 2026/2025 values. | Poor; final citation was CBS 2027 COLA reporting. | Incomplete. | Low hallucination risk because it refused unsupported numbers, but material numeric/source grounding failure recurred. |
| Q2 | Poor for Starliner. | Poor for requested current status. | No useful final cited Starliner source list. | Incomplete. | Low hallucination risk because it refused off-topic evidence, but source survival failed. |
| Q3 | Mixed. California/incentive/cost sources were visible, but mostly secondary/proxy. | Reasonable but incentive availability remained uncertain. | Acceptable for a caveated practical answer. | Mostly complete except precise 5-year cost. | Posture matched evidence strength. |
| Q4 | Mixed. Conceptual support was useful but not SQLite-primary. | Not a currentness-sensitive query. | Thin but serviceable. | Complete for a short conceptual answer. | Low visible overclaim risk. |

## Protected-Surface Scan

No code was changed. No protected-surface implementation drift was introduced.

Visible sanitized telemetry showed:

- provider roles stayed existing roles such as `main_retrieval`, `recon`,
  `disambiguation_retry`, and `weak_corpus_recovery`;
- no `retrieve_targeted` provider role appeared;
- `targeted_retrieval_executor_dispatched` stayed false;
- dispatch provider/depth/query-generation policies stayed `reuse_existing`;
- protected readiness flags were true in the authorized ordinary-lane cases;
- source-class recovery and conflict resolution did not execute in the four
  runs; weak-corpus recovery executed only in Q2 through the existing lane.

This validation did not read or commit secrets, API keys, raw provider payloads,
raw prompts, full raw traces, DB rows, caches, or unrelated generated outputs.

## Decision

Validation decision: `numeric_extraction_lane_needed`.

AG-47C appears to have fixed the projection/dispatch trace inconsistency for
authorized ordinary lanes in this bounded round. The protected surfaces stayed
clean.

The round does not qualify as `trace_clean_quality_ok` or
`trace_clean_quality_followup` because the official numeric case materially
failed again: the run authorized bounded ordinary follow-up queries, but no
official SSA source survived into the final answer and no requested numeric
values were extracted or compared. This is now recurring product-quality
evidence after the AG-47B Roth IRA numeric failure.

## Known Rough Edges

- Q1 did not retrieve or preserve official SSA program-parameter sources.
- Q1 extracted none of the requested 2026/2025 numeric values.
- Q2 did not retrieve/preserve obvious official NASA/Boeing Starliner status
  sources and answered with an off-topic retrieval caveat.
- Q3 lacked a fully source-bound 5-year California cost model.
- Q4 should ideally cite SQLite primary documentation for WAL behavior.

## Recommended Next Action

Open a focused numeric/source-grounding lane for official-source quantitative
answers. The next work should diagnose why official numeric/current sources
fail to survive into final evidence and why numeric values are not reliably
extracted when official sources are available or requested. Keep provider
routing, provider selection, search depth, query generation, prompts, final
answer behavior, and handoffs unchanged unless a later architecture decision
explicitly scopes those surfaces.

## Artifact Criteria

Local packet:

- Path: `output/ag47d_output_trace_sanity_packet.md`
- Consumer: reviewer inspection of full answers, cited URLs, visible report
  snippets, and sanitized batch/controller telemetry.
- Decision criterion: classify AG-47D and decide whether trace work can move on
  or product-quality lanes must be opened.
- Deletion criterion: may be deleted after reviewer sign-off or superseded by a
  later output/trace packet.

Committed validation note:

- Path: `docs/history/validation/AG47D_POST_FIX_OUTPUT_TRACE_SANITY_REVIEW_R1.md`
- Consumer: durable validation history and next-phase planning.
- Decision criterion: preserve the bounded live outcome without committing full
  answer text or raw trace material.
- Deletion criterion: retain unless superseded by an explicit later validation
  summary.
