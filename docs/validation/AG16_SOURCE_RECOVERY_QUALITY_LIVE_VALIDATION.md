# AG-16 Source Recovery Quality Live Validation

Scope: bounded live validation of AG-15 recovered-source quality diagnostics and
source-class recovery query/classification improvements.

Mode: Architecture Groove / Prove Mode, Path B.

## Offline Gate Summary

Main was fast-forward clean at `af89a28`, the AG-15 merge commit. Main includes:

- AG-13 active recovery timing/blocker revision: `375e88a`
- AG-14 revised active source-class recovery live validation summary: `6eee08d`
- AG-15 source-class recovery quality diagnostics: `af89a28`

PR #13 was confirmed closed and unmerged through GitHub metadata.

No `output/` files are tracked by git. `git ls-files output` returned no paths
before and after live validation.

Offline gate results:

| Check | Result |
|---|---|
| `py -m ruff check .` | pass |
| `git diff --check` | pass |
| AG-15 focused tests | 11 passed |
| AG-13 focused tests | 11 passed |
| AG-11 focused tests | 12 passed |
| AG-10 focused tests | 6 passed |
| AG-8 focused tests | 9 passed |
| Runtime handoff/validation tests | 18 passed |
| Source-class recovery guardrail tests | 78 passed |
| Weak-corpus tests | 14 passed |
| Retrieval-stop tests | 23 passed |
| Quantitative/pre-analyst safety tests | 125 passed |
| Full offline pytest | 1016 passed, 1 deselected |

The first full-suite attempt used a phase-specific temp folder name and failed
only `test_tmp_path_uses_workspace_local_base`, which expects an exact
`.pytest-tmp` path segment. Rerunning with `--basetemp=C:\tmp\.pytest-tmp`
passed.

## Live Budget

Budget used: 6 successful live ProPlex CLI runs out of 6 approved.

No reserve runs were used.

Command shape:

```powershell
py -m proplex "<query>" --mode Balanced --output output\ag16_case_outputs_tmp\<case>.md
```

Temporary case reports were written only under
`output/ag16_case_outputs_tmp/`, then copied into the local untracked
output-quality review packet and deleted. The packet remains at:

`output/ag16_output_quality_review_packet.md`

## Exact Queries Run

| Case | Query |
|---|---|
| A | As of today, what are the current U.S. Department of Transportation rules for automatic airline refunds, and what passenger rights or deadlines matter in 2026? |
| B | What is the current status of the FTC click-to-cancel rule, what would it require, and what court or implementation deadlines matter? |
| C | What are the current FDA rules or enforcement posture for compounded semaglutide after the Ozempic/Wegovy shortage ended, and what should patients or clinics be careful about? |
| D | Which subscription billing platform should a small SaaS company consider if it wants to reduce compliance risk under current click-to-cancel or negative-option rules, while still choosing a practical billing tool? |
| E | What did the original EPA acid rain allowance trading program require when it launched, and how did the initial requirements work? |
| F | A protein bar has 220 calories per 60g, and another has 170 calories per 45g. Which is more calorie-dense, and by how much? |

This phase reused the AG-14 query set because AG-15 directly targeted the
AG-14 recovery-quality failure class. This exact query set should now be
retired by default.

## Per-Case Active Recovery

| Case | Considered | Eligible | Used | Reason | Skip reason | Missing classes | Role | Depth |
|---|---:|---:|---:|---|---|---|---|---|
| A | yes | yes | yes | `answer_contract_current_primary_gap:current_primary_or_official` | null | `current_primary_or_official` | `source_class_recovery` | `basic` |
| B | yes | yes | yes | `answer_contract_current_primary_gap:current_primary_or_official` | null | `official_current_rules`, `current_primary_or_official` | `source_class_recovery` | `basic` |
| C | yes | yes | yes | `answer_contract_legal_text_gap:legal_or_regulatory_text,official_current_rules` | null | `legal_or_regulatory_text`, `official_current_rules` | `source_class_recovery` | `basic` |
| D | yes | no | no | `blocked_by_iteration_budget` | `blocked_by_iteration_budget` | none | null | null |
| E | yes | no | no | `blocked_by_weak_corpus_recovery` | `blocked_by_weak_corpus_recovery` | none | null | null |
| F | yes | no | no | `blocked_by_weak_corpus_recovery` | `blocked_by_weak_corpus_recovery` | none | null | null |

## Recovered-Source Quality

| Case | Status | Tier counts | Class counts | Official/primary recovered | Accepted URLs | Promoted sources | Final official/legal/primary counts | Interpretation |
|---|---|---|---|---:|---:|---:|---|---|
| A | `promoted_but_not_final` | `{"secondary":27,"unknown":15}` | `{"issuer_filings_or_company_materials":2}` | 1 | 8 | 4 | 0 / 0 / 0 | Recovery found at least one official/primary source but it did not survive into final evidence. |
| B | `no_relevant_sources` | `{"secondary":57,"unknown":13}` | `{}` | 0 | 8 | 6 | 0 / 0 / 0 | Recovery fired but did not recover usable official/current legal material. |
| C | `secondary_only` | `{"secondary":66,"unknown":22}` | `{}` | 0 | 8 | 2 | 0 / 0 / 0 | Recovery fired but added only secondary material. |
| D | `unknown` | `{}` | `{}` | 0 | 0 | 0 | 0 / 0 / 0 | Recovery did not run; skip was safe for the recommendation control. |
| E | `unknown` | `{}` | `{}` | 0 | 0 | 0 | 3 / 1 / 0 | Recovery did not overfire as a current-rules case. |
| F | `unknown` | `{}` | `{}` | 0 | 0 | 0 | 0 / 0 / 0 | Recovery did not run for the quantitative control. |

## Answer Quality

| Case | Compact grade | Output-quality result |
|---|---|---|
| A | D+ / fail source quality | The answer states current DOT refund rules but cites only secondary or unrelated news sources; recovered official/primary material was not final evidence. |
| B | C- / partial diagnostics, fail source quality | The answer caveats missing live-status evidence, but relies on a single Guardian opinion/context source and lacks FTC/Federal Register/court evidence. |
| C | C- / partial diagnostics, fail source quality | The answer gives reasonable cautionary framing, but lacks FDA/official legal-regulatory evidence for a regulatory/public-health query. |
| D | D / safe skip, poor recommendation answer | Active recovery did not hijack the recommendation case, but the answer does not actually recommend a billing platform and uses weak legal evidence. |
| E | C / safe partial | The answer avoids pretending secondary material is original legal text, but does not answer the launch-requirements question. |
| F | F / fail quantitative consistency | The answer contradicts itself: opening prose names the 220/60g bar, while the calculation/conclusion correctly name the 170/45g bar. |

## Quantitative Consistency Result

Case F reported:

- `quantitative_consistency_status`: `contradiction_detected`
- `quantitative_consistency_check_attempted`: `true`
- `quantitative_consistency_computed_winner`: `item_b`
- `quantitative_consistency_stated_winner`: `item_a`
- `quantitative_consistency_reason`: `stated_winner_contradicts_normalized_values`
- normalized values: `item_a = 3.666667 calories/g`; `item_b = 3.777778 calories/g`

The shadow diagnostic caught the repeated stated-winner contradiction. Because
the contradiction reached final user-facing prose, AG-16 fails the quantitative
control even though the diagnostic behaved as intended.

## Safety And Leak Result

No runtime behavior, provider routing, provider selection, search-depth policy,
prompt semantics, source ranking/filtering, persistence schema, or active
controller behavior was changed.

No raw live logs, raw provider payloads, raw prompts, execution rows, DBs,
caches, full traces, or `output/` files are committed by this phase.

The local output-quality review packet is ignored under `output/`, and the
temporary case-report directory was deleted after the packet was built.

## Result

Source-class recovery diagnostics improved explainability, but not final answer
quality. When recovery fired live:

- A recovered at least one official/primary source, but that material did not
  survive into final evidence.
- B and C failed to recover official/legal/primary material.
- The final answers still relied on secondary or unsuitable evidence for
  official/current/legal/regulatory questions.

Overall AG-16 is a partial source-recovery diagnostics pass and a quantitative
control fail.

## AG-17 Recommendation

Do not run another rotated live validation yet and do not broaden active
controller behavior.

AG-17 should be a protected source-ranking/filtering design decision if the next
goal is to make recovered official/legal/primary material survive into final
evidence. A separate quantitative-answer guard phase is also justified because
the shadow diagnostic caught Case F but final prose still exposed the
contradiction.
