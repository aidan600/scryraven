# AG-14 Revised Active Source-Class Recovery Live Validation

Scope: bounded live validation of the AG-13 revised active
answer-contract source-class recovery slot. No runtime behavior, provider
routing, provider selection, search-depth policy, prompts, source
ranking/filtering, persistence schema, weak-corpus ownership, retrieval-stop
ownership, or downstream handoff behavior was changed.

Run date: May 22, 2026 local CLI date.

## Offline Gate

| Gate item | Result | Notes |
|---|---|---|
| Updated main | pass | `git pull --ff-only origin main` was already up to date at `375e88a`. |
| AG-11 on main | pass | Main includes merge commit `515ed24`, PR #16, for the active official source-class recovery pilot. |
| AG-12 on main | pass | Main includes merge commit `c1e66f9`, PR #17, for active pilot live validation. |
| AG-13 on main | pass | Main includes merge commit `375e88a`, PR #18, for active recovery timing/blocker revision. |
| PR #13 status | pass | GitHub reports PR #13 closed and `merged=false`. |
| Tracked truth/output files | pass | `git ls-files output` and tracked truth-packet checks returned no tracked output or truth-review packet. |
| Ruff | pass | `py -m ruff check .`. |
| Diff check | pass | `git diff --check`. |
| AG-13/AG-11/AG-10/AG-8 focused tests | pass | 38 passed after rerun with `--basetemp=C:\tmp\.pytest-tmp-ag14-focused`; first attempt hit only local repo `.pytest-tmp`/cache permissions after 37 passed. |
| AG-4/5/7 runtime handoff/validation | pass | 18 passed. |
| Source-class guardrails | pass | Controller/lifecycle/trace/executor: 35 passed; broader source-class recovery suite: 43 passed. |
| Weak-corpus guardrails | pass | Controller/recovery: 14 passed. |
| Retrieval-stop guardrails | pass | Controller/shadow: 23 passed. |
| Full offline pytest | pass | 1005 passed, 1 deselected with `--basetemp=C:\tmp\.pytest-tmp -o cache_dir=C:\tmp\pytest_cache_ag14`. |

Stage 1 was clean. No protected-surface test failed, no source-class recovery
behavior was changed outside AG-13, and no design decision was required before
live validation.

## Live Budget

Approved budget: up to 6 successful live ProPlex CLI/harness runs.

Used budget: 6 successful live CLI runs, 0 reserve runs.

Command shape: `py -m proplex "<query>" --mode Balanced --output C:\tmp\ag14_case_<case>.md`.

Raw local artifacts were not committed. The CLI appended ignored local telemetry
under `output/`, full local reports were written under `C:\tmp`, and the local
truth-review packet was written under ignored `output/`.

## Queries Run

| Case | Query |
|---|---|
| A | As of today, what are the current U.S. Department of Transportation rules for automatic airline refunds, and what passenger rights or deadlines matter in 2026? |
| B | What is the current status of the FTC click-to-cancel rule, what would it require, and what court or implementation deadlines matter? |
| C | What are the current FDA rules or enforcement posture for compounded semaglutide after the Ozempic/Wegovy shortage ended, and what should patients or clinics be careful about? |
| D | Which subscription billing platform should a small SaaS company consider if it wants to reduce compliance risk under current click-to-cancel or negative-option rules, while still choosing a practical billing tool? |
| E | What did the original EPA acid rain allowance trading program require when it launched, and how did the initial requirements work? |
| F | A protein bar has 220 calories per 60g, and another has 170 calories per 45g. Which is more calorie-dense, and by how much? |

## Recovery Telemetry

| Case | Expected posture | Considered | Eligible | Used | Attempt count | Missing active classes | Reason / skip reason | Provider role / depth |
|---|---|---:|---:|---:|---:|---|---|---|
| A | official/current legal | yes | yes | yes | 1 | `current_primary_or_official` | `answer_contract_current_primary_gap:current_primary_or_official` | `source_class_recovery` / `basic` |
| B | current legal/status | yes | no | no | 0 | `official_current_rules` | `blocked_by_weak_corpus_recovery`; blockers also included `blocked_by_iteration_budget` | n/a |
| C | current regulatory/public-health | yes | yes | yes | 1 | `legal_or_regulatory_text`, `official_current_rules` | `answer_contract_legal_text_gap:legal_or_regulatory_text,official_current_rules` | `source_class_recovery` / `basic` |
| D | recommendation with legal constraint | yes | no | no | 0 | none | `blocked_by_iteration_budget`; blockers included `not_recommended` | n/a |
| E | historical/archival legal-primary control | yes | no | no | 0 | none | `blocked_by_weak_corpus_recovery`; blockers included `not_recommended`, `blocked_by_iteration_budget` | n/a |
| F | quantitative negative control | yes | no | no | 0 | none | `blocked_by_iteration_budget`; blockers included `not_recommended` | n/a |

Cases A and C each executed exactly one existing source-class recovery attempt
through the reserved AG-13 slot. Both used the preserved provider role
`source_class_recovery` and search depth `basic`. Telemetry showed the existing
Tavily provider path in the live pass; no provider selection behavior was
changed.

## Source Quality And Answer Quality

| Case | Recovery/source result | Source quality improved? | Answer grade | Notes |
|---|---|---|---|---|
| A | Active recovery returned 52 results and 9 new URLs, but final counts remained 0 official, 0 legal/regulatory, 0 primary. | no | partial | The answer caveated missing primary DOT rule text but still asserted current legal rules from secondary/news sources. |
| B | Active recovery was blocked by weak-corpus ownership before execution; final source status was `official_current_rules=expected_but_only_secondary`. | no | partial | Safe no-answer for the requested FTC status, but it did not answer the substantive legal/status question. |
| C | Active recovery returned 18 results and 3 new URLs, but final counts remained 0 official, 0 legal/regulatory, 0 primary. | no | partial | The answer avoided direct medical advice, but the FDA/legal posture still relied on secondary legal/news sources. |
| D | No active recovery; final answer included official/legal constraint sources (`ftc.gov`, `govinfo.gov`, CFPB) plus product-selection evidence. | n/a | pass | Recommendation evidence and legal-compliance evidence stayed distinct; active recovery did not hijack the answer. |
| E | No active current-rules recovery; weak-corpus recovery ran and final answer gave a safe no-answer. | n/a | partial | It did not pretend secondary/off-topic material was original EPA statutory/regulatory text. |
| F | No source-class recovery. | n/a | fail | The math showed the 170 calorie / 45g bar is denser by 0.11 cal/g, but the first sentence incorrectly named the 220 calorie / 60g bar as more dense. |

## Result

Main question: Does the AG-13 reserved answer-contract source-class recovery
slot allow at least one appropriate official/current/legal or current-primary
case to execute exactly one existing `source_class_recovery` attempt while
preserving protected surfaces?

Answer: yes for execution safety, but only partial overall. Cases A and C prove
the revised slot can fire exactly one existing source-class recovery attempt in
appropriate official/current/legal or current-primary cases. The attempts
preserved provider role, search depth, provider selection, prompts, source
ranking/filtering, weak-corpus ownership, retrieval-stop ownership,
persistence schema, and downstream handoff behavior because no runtime code was
changed and the observed live telemetry stayed inside the existing
`source_class_recovery` path.

However, neither successful attempt materially improved final official/current
or legal source quality. The observed benefit was execution telemetry and
reserved-slot behavior, not answer-quality improvement. Case F also exposed an
unrelated quantitative-answer quality failure in the negative control.

## Safety And Leak Check

- No secrets, `.env` values, API keys, credential files, DBs, caches, raw
  provider payloads, raw prompts, or full traces were inspected or committed.
- Raw final reports remained local under `C:\tmp`.
- The local truth-review packet remained under ignored `output/`.
- CLI-generated `output/` files are ignored by `.gitignore`.
- No provider routing, provider selection, search-depth policy, prompts, source
  ranking/filtering, persistence schema, weak-corpus ownership, retrieval-stop
  ownership, or downstream handoff code was changed.

Safety result: pass.

## Overfitting Check

No evidence of overfitting appeared. AG-14 used a rotated query set, did not
reuse the exact AG-12 A-H set, and did not tune code, prompts, providers,
source ranking, or heuristics from live observations.

## AG-15 Recommendation

Recommendation: active pilot revision.

Do not broaden the controller loop yet, and do not roll back to passive-only
based on this run. AG-13 fixed the execution blocker for at least two
appropriate cases, but the source-class recovery attempt still failed to
produce official/current/legal source quality in the final answer. AG-15 should
stay narrow: diagnose why the preserved recovery path does not retrieve or
promote official/current/legal sources when the slot fires, and add a guard or
calibration check for the quantitative negative-control answer contradiction
before any broader controller-loop behavior.
