# AG-22 Official Source Domain Recovery Live Validation

Scope: bounded live validation after PR #28 merged AG-22 official-source
domain-constrained recovery into `main`.

Non-goals: no runtime code changes, prompt changes, provider routing or
selection changes, search-depth changes, source ranking or filtering changes,
handoff changes, persistence schema changes, or domain/query tuning based on
live results.

Run date: May 22, 2026 local CLI date.

## Base And PR Merge Commit

Validation branch:
`codex/ag-22-official-source-live-validation`

Base `main` commit and PR #28 merge commit:

`e647d23a7f320dbcec275e02e79c9cd43969eab5` -
`Merge pull request #28 from aidan600/codex/ag-22-official-source-domain-recovery-lane`

Before the live runs, `main` was updated with `git pull` and was already up to
date. The validation branch and `main` both pointed at the PR #28 merge commit.

## Offline Gate Summary

No `output/` files are tracked by git. `git ls-files output` returned no paths
before live validation. The temporary case reports are ignored by the
`.gitignore` `output/` rule.

| Check | Result |
|---|---|
| `git status -sb` before gate | clean validation branch |
| `git ls-files output` | no tracked paths |
| `py -m ruff check .` | pass |
| `git diff --check` | pass |
| `py -m pytest tests\test_ag22_official_source_domain_recovery_lane.py --basetemp C:\tmp\ag22_pytest_tmp -o cache_dir=C:\tmp\ag22_pytest_cache` | 18 passed |

## Live Budget Used

Budget used: 3 successful live ProPlex CLI runs out of 3 approved.

No reserve runs were available or used. No extra live searches, provider calls,
model calls, or ad hoc probes were run outside the three approved CLI commands.

CLI-visible summaries:

| Case | Result | Calls | Cost | Elapsed |
|---|---|---:|---:|---:|
| A | report written | 15 | `$0.0027` | 42.9s |
| B | report written | 17 | `$0.3473` | 204.6s |
| C | report written | 16 | `$0.0059` | 53.7s |

Total CLI-visible live usage: 48 calls and `$0.3559`.

Temporary case reports were written under:

`output/ag22_live_validation_tmp/`

That temporary directory was deleted after the validation note was written.

Only the generated case reports and CLI-visible command summaries were used for
this validation note. Raw execution logs, DBs, caches, provider payloads,
prompts, traces, private logs, `.env`, API keys, and unrelated generated outputs
were not inspected.

## Exact Queries

| Case | Query |
|---|---|
| A | As of today, what are OSHA’s current Hazard Communication Standard requirements after the 2024 final rule, including the major compliance deadlines and what changed for labels, safety data sheets, and chemical classifications? |
| B | As of today, which EU AI Act obligations are already in force, which phased deadlines still matter for providers and deployers of high-risk AI systems, and what does the current legal text require? |
| C | As of today, what duties and enforcement milestones apply to small user-to-user services under the UK Online Safety Act and Ofcom codes, and what official legal or regulator sources control the answer? |

## Telemetry Availability Note

The generated markdown reports did not expose the internal source-class recovery
telemetry requested by the rubric. The validation therefore cannot directly
confirm whether active recovery was considered, eligible, used, which recovery
query was issued, what domain constraints were applied, which providers ran for
recovery, or what internal `recovery_source_quality_status` value was recorded.

Because the allowed artifacts were insufficient for those internal metrics, this
document marks those cells as "not visible from allowed artifacts" instead of
opening raw logs, DBs, caches, traces, provider payloads, or private telemetry.

## Per-Case Active Recovery

| Case | Considered | Eligible | Used | Recovery reason / missing classes | Recovery query text |
|---|---|---|---|---|---|
| A | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts |
| B | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts |
| C | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts |

## Per-Case Domain Constraint / Provider / Depth

| Case | Official domain constraints | Provider role | Search depth | Recovery providers |
|---|---|---|---|---|
| A | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts |
| B | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts |
| C | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts |

## Per-Case Recovered Source Quality

| Case | `recovery_source_quality_status` | Recovered tier counts | Recovered source class counts | Recovered official/legal/current-primary count | Accepted URL count | Promoted source count | Final official/legal/primary counts |
|---|---|---|---|---:|---:|---:|---|
| A | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | observable final citations: 0 official/legal/current-primary URLs |
| B | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | observable final citations: 0 official/legal/current-primary URLs |
| C | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | 2 final cited secondary URLs | not visible from allowed artifacts | observable final citations: 0 official/legal/current-primary URLs |

## Per-Case Recovered Visibility

| Case | Considered | Eligible | Used | Reserved count | Notes |
|---|---|---|---|---:|---|
| A | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | Final report says the retrieved items were mostly EPA ethylene oxide material and unrelated AP health stories, not OSHA hazard communication. |
| B | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | Final report cites an "analyst baseline legal synthesis" rather than an official EU URL or current legal text source. |
| C | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | not visible from allowed artifacts | Final report says the corpus lacks the actual Ofcom codes, relevant statutory provisions, and official guidance. |

## Per-Case Answer Quality

| Case | Grade | Concrete source-use note |
|---|---|---|
| A | fail source quality | The final answer does not answer from OSHA, Federal Register, eCFR/CFR, GovInfo, or comparable official/current legal material. It explicitly says the retrieved items are mostly unrelated and suggests a narrower follow-up query. |
| B | partial content answer, fail source quality | The final answer gives a plausible EU AI Act timeline and obligations, but the source list contains only "Regulation (EU) 2024/1689 ... analyst baseline legal synthesis from the provided record" and "Analyst baseline legal synthesis"; it does not cite or link `eur-lex.europa.eu` or other official current legal text. |
| C | safe caveat, fail source quality | The final answer correctly refuses a definitive legal/regulator answer from the retrieved corpus, but its only cited URLs are BBC and The Guardian. It explicitly says the controlling Online Safety Act text and Ofcom codes/guidance were not retrieved. |

## Safety And Leak Result

No runtime code, prompts, provider routing, provider selection, search-depth
policy, source ranking/filtering, handoff behavior, or persistence schema was
changed.

No secrets, `.env` values, API keys, DBs, caches, raw provider payloads, raw
prompts, full traces, private logs, historical output packets, unrelated
generated outputs, or `output/` files are committed by this phase.

Safety result: pass.

## Interpretation

Validation classification: failure on observable final source quality, with
internal AG-22 recovery telemetry inconclusive from the allowed artifacts.

Strong success was not met. The generated reports do not show
`recovery_source_quality_status=official_or_primary_found` for any case, and no
final answer visibly cites an official legal/current-primary URL.

Partial success was not demonstrated from the allowed artifacts. There is no
visible evidence that official-domain constraints retrieved useful official
URLs that were later blocked by classification, visibility, or final evidence.

Observable failure shape:

| Case | Design signal |
|---|---|
| A | U.S. OSHA/HCS official-source retrieval failed at the final-answer level. This is consistent with the "U.S. provider/depth/domain issue remains" signal, but the internal recovery path is not visible. |
| B | EU AI Act answer content improved relative to a refusal, but final source quality did not show official EU legal text. This is consistent with possible EU official-domain or provider-depth weakness, but not enough telemetry is exposed to isolate it. |
| C | UK Online Safety Act answer stayed secondary-only and explicitly lacked Ofcom/statutory material. This is consistent with possible regulator-domain expansion needs such as Ofcom, but no domain changes should be made from this phase alone. |

Likely next action: expose or generate a sanitized validation packet for
source-class recovery diagnostics in future live validation runs, so the
rubric can be answered without opening raw logs, DBs, caches, provider payloads,
prompts, or full traces.

## Recommendation

Do not proceed directly to source docs refresh based on this live result. The
observable final answers did not demonstrate official/legal/current-primary
source survival.

Open an AG-22 follow-up focused on sanitized telemetry exposure plus live
provider/depth/domain diagnostics. The follow-up should preserve the validation
boundary: first make the recovery metrics visible in a safe artifact, then run a
bounded validation before deciding whether provider depth, EU/UK domain support,
or regulator-domain expansion is warranted.

Move to AG-2 offline validation harness only after deciding what sanitized
signals it should assert. The current live reports do not expose enough
structured recovery state for a meaningful offline acceptance contract.

Do not pause source-class recovery solely from this run. The live observable
outcome is poor, but the internal recovery attempt and domain-constraint
behavior were not visible from the allowed artifacts, so disabling the lane
would be premature.
