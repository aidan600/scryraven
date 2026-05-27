# AG-21 Official Source Recovery Live Validation

Scope: bounded live validation of AG-20 official-source recovery query quality
and weak-corpus/source-class ownership behavior. No runtime code, provider
routing, provider selection, search-depth policy, source ranking/filtering,
prompt semantics, persistence schema, recovered-visibility behavior, or active
controller behavior was changed.

Mode: Architecture Groove / Prove Mode, Path B.

Run date: May 22, 2026 local CLI date.

## Offline Gate Summary

Main was fast-forward clean at `35d3a8b`, the AG-20 merge commit. Main includes
AG-20 official source recovery quality via:

- `35d3a8b` - merge PR #25 from
  `aidan600/codex/ag-20-official-source-recovery-quality`
- `bd9f00c` - `feat: improve official source recovery quality`

PR #13 was confirmed through GitHub metadata as closed and `merged=false`.

No `output/` files are tracked by git. `git ls-files output` returned no paths
before live validation. The review packet path is ignored by the `.gitignore`
`output/` rule.

Offline gate results:

| Check | Result |
|---|---|
| `py -m ruff check .` | pass |
| `git diff --check` | pass |
| AG-20 official source recovery quality tests | 9 passed |
| AG-18 quantitative guard tests | 12 passed |
| AG-17 recovered evidence visibility tests | 17 passed |
| AG-15 source-class recovery diagnostics tests | 11 passed |
| Runtime handoff/validation tests | 18 passed |
| Source-class recovery tests | 78 passed |
| Weak-corpus tests | 14 passed |
| Retrieval-stop tests | 23 passed |
| Quantitative/pre-analyst/Economist safety tests | 229 passed |
| Full offline pytest | 1054 passed, 1 deselected |

The first AG-20 focused test attempt hit the known Windows `.pytest-tmp` and
`.pytest_cache` permission issue after 4 tests passed and 5 setup errors. The
same gate passed when rerun with `--basetemp=C:\tmp\.pytest-tmp-ag21 -o
cache_dir=C:\tmp\pytest_cache_ag21`. The remaining focused gates and full
offline suite used `C:\tmp` basetemp/cache paths.

## Live Budget

Budget used: 3 successful live ProPlex CLI runs out of 3 approved.

No reserve runs were used.

Command shape:

```powershell
py -m proplex "<query>" --mode Balanced --output output\ag21_case_outputs_tmp\<case>.md
```

Temporary case reports were written only under
`output/ag21_case_outputs_tmp/`. After the local output-quality review packet
was built, that temporary directory was deleted. The packet remains local and
ignored at:

`output/ag21_output_quality_review_packet.md`

## Exact Queries Run

| Case | Query |
|---|---|
| A | As of today, what are the current U.S. DOT rules for airline passengers who use wheelchairs, including mishandled wheelchair obligations, complaint rights, and any 2026 deadlines or enforcement milestones? |
| B | What is the current legal status of the FTC noncompete rule, what would it have required, and what court or agency deadlines matter now? |
| C | What is the current FDA enforcement posture for laboratory developed tests after the LDT final rule, and what deadlines or phase-in milestones matter for labs? |

This phase reused exactly three AG-19 queries because AG-20 directly targeted
those failures. These exact queries should now be retired by default.

## Per-Case Active Recovery

| Case | Considered | Eligible | Used | Reason / skip reason | Missing classes | Result / new URLs | Role / depth |
|---|---:|---:|---:|---|---|---:|---|
| A | yes | yes | yes | `answer_contract_legal_text_gap:legal_or_regulatory_text,official_current_rules` | `legal_or_regulatory_text`, `official_current_rules` | 58 / 8 | `source_class_recovery` / `basic` |
| B | yes | yes | yes | `answer_contract_legal_text_gap:legal_or_regulatory_text,official_current_rules` | `legal_or_regulatory_text`, `official_current_rules` | 14 / 4 | `source_class_recovery` / `basic` |
| C | yes | yes | yes | `answer_contract_legal_text_gap:legal_or_regulatory_text,official_current_rules` | `legal_or_regulatory_text`, `official_current_rules` | 44 / 6 | `source_class_recovery` / `basic` |

Case B also ran weak-corpus recovery first
(`weak_corpus_recovery_decision=run_weak_corpus_recovery`), but AG-20's narrow
exception allowed source-class recovery to run afterward. This is an ownership
improvement over AG-19's B/C blocker shape.

## Per-Case Recovery-Query / Hint Table

| Case | Active recovery query text | AG-20 hints appeared? |
|---|---|---|
| A | `U.S. Department of Transportation legal regulatory text statute regulation CFR eCFR Code of Federal Regulations transportation.gov DOT 14 CFR Part 382 Air Carrier Access Act`; `U.S. Department of Transportation Federal Register GovInfo final rule docket compliance date regulation text transportation.gov DOT 14 CFR Part 382 Air Carrier Access Act` | yes - DOT, transportation.gov, 14 CFR Part 382, Air Carrier Access Act, Federal Register, CFR/eCFR/GovInfo terms |
| B | `FTC noncompete rule legal regulatory text statute regulation CFR eCFR Code of Federal Regulations ftc.gov Federal Register final rule court status`; `FTC noncompete rule Federal Register GovInfo final rule docket compliance date regulation text ftc.gov Federal Register final rule court status` | yes - FTC, ftc.gov, Federal Register, final rule, court-status terms |
| C | `FDA legal regulatory text statute regulation CFR eCFR Code of Federal Regulations fda.gov Federal Register enforcement discretion final rule`; `FDA Federal Register GovInfo final rule docket compliance date regulation text fda.gov Federal Register enforcement discretion final rule` | yes - FDA, fda.gov, Federal Register, enforcement-discretion, final-rule terms |

## Per-Case Recovered-Source Quality

| Case | Status | Tier counts | Class counts | Official/primary recovered | Accepted URLs | Promoted sources | Final official/legal/primary counts | Interpretation |
|---|---|---|---|---:|---:|---:|---|---|
| A | `no_relevant_sources` | `{"secondary":49,"unknown":9}` | `{}` | 0 | 7 | 2 | `0 / 0 / 0` | Query hints were right-shaped, but live retrieval still returned no useful official/legal/current-primary source. |
| B | `no_relevant_sources` | `{"unknown":14}` | `{}` | 0 | 4 | 0 | `0 / 0 / 0` | AG-20 fixed the weak-corpus ownership blocker, but retrieval still found no official/legal/current-primary source. |
| C | `no_relevant_sources` | `{"secondary":25,"unknown":19}` | `{}` | 0 | 5 | 3 | `0 / 0 / 0` | Recovery executed with FDA/Federal Register hints, but retrieved no qualifying official/legal/current-primary material. |

## Per-Case Recovered Visibility

| Case | Considered | Eligible | Used | Reason | Reserved count | Reserved source IDs | Drop reason |
|---|---:|---:|---:|---|---:|---|---|
| A | yes | no | no | `no_relevant_sources` | 0 | none | `no_relevant_sources` |
| B | yes | no | no | `no_relevant_sources` | 0 | none | `no_relevant_sources` |
| C | yes | no | no | `no_relevant_sources` | 0 | none | `no_relevant_sources` |

No case recovered a qualifying official/legal/current-primary source, so AG-21
does not expose a recovered-visibility failure. There was no qualified
recovered source for AG-17 visibility to reserve.

## Per-Case Answer Quality

| Case | Compact grade | Source quality improved? | Answer-quality note |
|---|---|---|---|
| A | D / fail source quality | no | The answer gives a detailed DOT/Part 382 narrative, but cites unrelated secondary/news items instead of DOT, Federal Register, eCFR/CFR, GovInfo, or comparable official/legal material. |
| B | C- / safe caveat, fail source quality | no | The answer avoids inventing a legal status from weak retrieval, but does not answer the rule status, substance, or deadline question. |
| C | D+ / unsupported legal-regulatory answer | no | The answer gives a confident enforcement-posture and phase-in table, but cites unrelated FDA/news items rather than FDA/Federal Register/current legal material. |

## Safety And Leak Result

No runtime code or protected surface was changed. No provider routing,
provider selection, search-depth policy, source ranking/filtering, prompt
semantics, persistence schema, Analyst/Economist/Author handoff design,
recovered visibility behavior, quantitative guard behavior, or controller-loop
behavior was edited.

No secrets, `.env` values, API keys, credential files, DBs, caches, raw provider
payloads, raw prompts, full traces, raw execution rows, raw live logs, or
`output/` files are committed by this phase. The local output-quality review
packet is ignored under `output/`; the temporary case-report directory was
deleted after the packet was built.

Safety result: pass.

## Result

AG-21 is an ownership/query-shape improvement but a provider/retrieval failure.

AG-20's deterministic official-source hints appeared in all three active
recovery query texts, and source-class recovery fired for A/B/C. The B-style
weak-corpus/source-class boundary improved because weak-corpus recovery no
longer prevented the single official/legal source-class attempt.

However, all three recovery attempts still ended with
`recovery_source_quality_status=no_relevant_sources`, recovered zero
official/legal/current-primary sources, reserved zero recovered sources into
final evidence, and did not materially improve final answer source quality.
The current preserved provider role/depth could not retrieve official sources
even when the query text looked right.

There is no evidence of overfitting in this phase: live validation reused only
the three approved AG-19 target queries, made no runtime changes from live
observations, and did not tune provider routing, search depth, prompts, source
ranking, or visibility behavior. The reused queries should now be retired.

## AG-22 Recommendation

AG-22 should be a provider/retrieval design review, not another offline
official-source heuristic patch and not a broader controller-loop expansion.

Recommended next question:

Can the existing live providers/search-depth path actually retrieve official
DOT/FTC/FDA/Federal Register/eCFR/GovInfo sources for current legal-regulatory
queries when given right-shaped official-source queries, or does the
source-class recovery lane need a provider/depth/retrieval design decision?

Do not broaden active controller behavior or revise recovered visibility until
a live or deterministic case recovers qualifying official/legal/current-primary
material that then fails to survive into final evidence.
