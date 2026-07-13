Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG12_ACTIVE_SOURCE_CLASS_RECOVERY_LIVE_VALIDATION).

# AG-12 Active Source-Class Recovery Live Validation

Scope: bounded live validation of the AG-11 active official/current/legal
source-class recovery pilot only. No runtime behavior, provider routing, search
depth, prompts, source ranking/filtering, persistence, weak-corpus ownership,
retrieval-stop ownership, or downstream handoff behavior was changed.

Run date: May 21, 2026 local CLI date.

## Offline Gate

| Gate item | Result | Notes |
|---|---|---|
| Updated main | pass | `git pull --ff-only origin main` was already up to date at `515ed24`. |
| AG-11 on main | pass | Main includes merge commit `515ed24`, PR #16, for AG-11 active official source-class recovery pilot. |
| PR #13 status | pass | GitHub reports PR #13 closed and `merged=false`. |
| Tracked truth/output files | pass | `git ls-files output` and tracked truth-packet checks returned no tracked output or truth-review packet. |
| Ruff | pass | `py -m ruff check .`. |
| Diff check | pass | `git diff --check`. |
| AG-11 focused tests | pass | `tests/test_answer_contract_source_class_recovery_ag11.py`: 12 passed. |
| AG-10 tests | pass | `tests/test_answer_contract_calibration_ag10.py`: 6 passed. |
| AG-8 tests | pass | `tests/test_answer_contract_calibration_ag8.py`: 9 passed. |
| AG-4/5/7 runtime handoff/validation | pass | 18 passed after rerun with `--basetemp=C:\tmp\.pytest-tmp-ag12-runtime`; first attempt hit only local repo temp cleanup permissions. |
| Source-class guardrails | pass | Controller/lifecycle/trace/executor: 30 passed. |
| Weak-corpus guardrails | pass | Controller/recovery: 14 passed. |
| Retrieval-stop guardrails | pass | Controller/shadow: 23 passed. |
| Full offline pytest | pass | 989 passed, 1 deselected with `--basetemp=C:\tmp\.pytest-tmp -o cache_dir=C:\tmp\pytest_cache_ag12`. |

Stage 1 was clean. No protected-surface test failed, no source-class behavior
change was made, and no design decision was required before live validation.

## Live Budget

Approved budget: up to 8 successful live ProPlex CLI/harness runs.

Used budget: 8 successful live CLI runs, 0 reserve runs.

Command shape: `py -m proplex "<query>" --mode Balanced --output C:\tmp\ag12_case_<case>.md`.

Raw local artifacts were not committed. The CLI appended ignored local telemetry
under `output/`, and full local reports were written under `C:\tmp`.

## Queries Run

| Case | Query |
|---|---|
| A | As of today, what are the current EU AI Act obligations and timeline for general-purpose AI model providers, and what compliance or enforcement milestones matter in 2026? |
| B | What are the current federal rules for claiming a tax credit for installing an EV charger at home in 2026, and what deadlines or eligibility limits matter? |
| C | What is currently happening with the European Commission’s high-risk AI guidelines under the AI Act, what is settled, and what remains uncertain? |
| D | Which home EV charger should I buy if I want to stay eligible for a federal tax credit and still choose the best option for my garage? |
| E | What is Reddit, Hacker News, or social media sentiment saying about Cursor’s recent agent features, and how much should I trust that signal? |
| F | Is Bluesky overtaking X as the default place journalists post breaking news in 2026, and what evidence would actually be needed to answer that responsibly? |
| G | What did the original U.S. leaded gasoline phase-down rules require, and how did those requirements change over time? |
| H | A sandwich bread label says 90 calories per 35g, and an artisan loaf says 150 calories per 85g. Which is more calorie-dense, and what explains the difference? |

## Recovery Telemetry

| Case | Expected posture | Considered | Eligible | Used | Missing active classes | Active query count | Reason / skip reason | Provider role / search depth |
|---|---|---:|---:|---:|---|---:|---|---|
| A | official/current legal | yes | no | no | `legal_or_regulatory_text`, `official_current_rules` | 2 | `blocked_by_iteration_budget` | n/a |
| B | official/current tax rules | yes | no | no | `legal_or_regulatory_text`, `official_current_rules` | 2 | `blocked_by_weak_corpus_recovery` | n/a |
| C | developing/current status | yes | no | no | `current_primary_or_official` | 2 | `blocked_by_iteration_budget` | n/a |
| D | recommendation with legal constraint | yes | no | no | `official_current_rules` | 2 | `blocked_by_weak_corpus_recovery` | n/a |
| E | social sentiment | yes | no | no | none | 0 | `blocked_by_weak_corpus_recovery` | n/a |
| F | weak/social evidence | yes | no | no | none | 0 | `blocked_by_iteration_budget` | n/a |
| G | historical/archival legal-primary | yes | no | no | none | 0 | `blocked_by_weak_corpus_recovery` | n/a |
| H | quantitative negative control | yes | no | no | none | 0 | `blocked_by_iteration_budget` | n/a |

No active source-class recovery attempt fired in the live set. Therefore no AG-12
run assigned the active recovery provider role or search depth. The pilot
surfaced official/current/legal/current-primary gaps for A-D, but existing
iteration-budget and weak-corpus ownership blockers prevented execution.

Case D is the only run where the older source-class recommendation path also
recommended recovery (`missing_expected_source_class:official_current_rules`),
but it was still blocked before execution by weak-corpus ownership.

## Handoff And Answer Quality

| Case | Handoff status | Source-class quality | Answer grade | Notes |
|---|---|---|---|---|
| A | unfulfilled `legal_or_regulatory_text`, `official_current_rules`; partial legal posture | no final official/legal/primary source counts | partial | Answer gave a usable legal timeline but explicitly said direct EU primary material was not retrieved. |
| B | unfulfilled `legal_or_regulatory_text`, `official_current_rules`; caveated posture | no final official/legal/primary source counts | partial | Safe no-answer for IRS/tax-credit rules; did not imply eligibility from weak sources. |
| C | unfulfilled `current_primary_or_official`; developing-event posture | no final official/primary source counts | partial | Answer addressed settled/uncertain status from secondary reporting; gap was visible. |
| D | unfulfilled `official_current_rules`, `current_specs_or_availability`, `reputable_reviews`; caveated posture | no final official/legal/primary source counts | partial | Safe no-answer for charger recommendation/tax eligibility; did not hijack into unsupported tax advice. |
| E | unfulfilled `social_signal`; social unavailable warning | no community signal found | pass | No official/current recovery. It warned that retrieved evidence did not support Reddit/HN/social sentiment and avoided percentages. |
| F | unfulfilled `social_signal`; social unavailable warning | no community signal found | pass | No official/current recovery. It refused to overclaim Bluesky vs. X and named the evidence needed. |
| G | unfulfilled `primary_or_archival`; historical caveated posture | official/primary counts present, but no archival source found | partial | Did not overfire AG-11 and did not pretend secondary/general material was original rule text. |
| H | quantitative handoff fulfilled | source-class recovery not relevant | pass | Correctly normalized: sandwich bread 257 cal/100g vs. artisan loaf 176 cal/100g. |

## Result

Main question: Does the active answer-contract official/current/legal recovery
pilot produce one useful existing source-class recovery attempt when
official/current/legal evidence is missing?

Answer: no, not in this bounded live set. The AG-11 pilot behaved safely and
did not overfire into social, weak-evidence, historical, or quantitative
controls. It also surfaced the intended source-class gaps in the official/legal
cases. But it produced zero active recovery executions, so it did not improve
source quality or final answer quality. The observed benefit was telemetry and
handoff visibility only.

This is a partial validation, not a pass for broader active controller
promotion.

## Safety And Leak Check

- No secrets, `.env` values, API keys, credential files, DBs, caches, raw
  provider payloads, raw prompts, or full traces were inspected or committed.
- Raw final reports remained local under `C:\tmp`.
- CLI-generated `output/` files are ignored by `.gitignore`.
- No provider routing, search-depth policy, prompts, source ranking/filtering,
  persistence schema, weak-corpus ownership, retrieval-stop ownership, or
  downstream handoff code was changed.

Safety result: pass.

## AG-13 Recommendation

Recommendation: active pilot revision.

Do not broaden the controller loop yet, and do not roll back to passive-only
based on this run. The active pilot was safe, but it was ineffective live
because existing blockers prevented every official/current/legal/current-primary
gap from becoming an executed recovery attempt. AG-13 should narrowly revise or
diagnose the interaction between answer-contract official/current gaps,
iteration-budget ownership, and weak-corpus ownership, then rerun a bounded
validation set. Broader controller behavior should wait until at least one
useful existing source-class recovery attempt is observed live without protected
surface drift.
