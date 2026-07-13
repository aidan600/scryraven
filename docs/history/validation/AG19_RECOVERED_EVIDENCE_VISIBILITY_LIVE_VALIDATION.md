Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG19_RECOVERED_EVIDENCE_VISIBILITY_LIVE_VALIDATION).

# AG-19 Recovered Evidence Visibility Live Validation

Scope: bounded live validation of AG-17 recovered-evidence visibility using a
rotated six-query set. No runtime code, provider routing, provider selection,
search-depth policy, source ranking/filtering, prompt semantics, persistence
schema, or active controller behavior was changed.

Mode: Architecture Groove / Prove Mode, Path B.

Run date: May 22, 2026 local CLI date.

## Offline Gate Summary

Main was fast-forward clean at `fbea9e8`, the AG-18 merge commit. Main includes:

- AG-17 recovered evidence visibility boundary: merge `8e5f230`.
- AG-18 quantitative contradiction guard: merge `fbea9e8`.

PR #13 was confirmed through GitHub metadata as closed and `merged=false`.

No `output/` files are tracked by git. `git ls-files output` returned no paths
before and after live validation.

Offline gate results:

| Check | Result |
|---|---|
| `py -m ruff check .` | pass |
| `git diff --check` | pass |
| AG-18 quantitative guard tests | 12 passed |
| AG-17 recovered evidence visibility tests | 17 passed |
| AG-15 source-class recovery diagnostics tests | 11 passed |
| Runtime handoff/validation tests | 18 passed |
| Source-class recovery tests | 78 passed |
| Weak-corpus tests | 14 passed |
| Retrieval-stop tests | 23 passed |
| Quantitative/pre-analyst/Economist safety tests | 125 passed |
| Full offline pytest | 1045 passed, 1 deselected |

The first focused AG-18/AG-17/AG-15 attempt hit the known Windows
`.pytest-tmp` / `.pytest_cache` permission issue after 33 tests had passed.
Rerunning with `--basetemp=C:\tmp\.pytest-tmp-ag19-focused -o
cache_dir=C:\tmp\pytest_cache_ag19_focused` passed. The first full-suite
attempt used a phase-specific temp folder name and failed only
`test_tmp_path_uses_workspace_local_base`, which expects an exact
`.pytest-tmp` path segment. Rerunning with `--basetemp=C:\tmp\.pytest-tmp -o
cache_dir=C:\tmp\pytest_cache_ag19` passed.

## Live Budget

Budget used: 6 successful live ProPlex CLI runs out of 6 approved.

No reserve runs were used.

Command shape:

```powershell
py -m proplex "<query>" --mode Balanced --output output\ag19_case_outputs_tmp\<case>.md
```

Temporary case reports were written only under
`output/ag19_case_outputs_tmp/`, then copied into the local untracked
output-quality review packet and deleted. The packet remains at:

`output/ag19_output_quality_review_packet.md`

## Exact Queries Run

| Case | Query |
|---|---|
| A | As of today, what are the current U.S. DOT rules for airline passengers who use wheelchairs, including mishandled wheelchair obligations, complaint rights, and any 2026 deadlines or enforcement milestones? |
| B | What is the current legal status of the FTC noncompete rule, what would it have required, and what court or agency deadlines matter now? |
| C | What is the current FDA enforcement posture for laboratory developed tests after the LDT final rule, and what deadlines or phase-in milestones matter for labs? |
| D | Which cookie-consent or consent-management platform should a small SaaS company consider if it wants to reduce GDPR/ePrivacy compliance risk while keeping implementation simple? |
| E | What did OSHA's original hazard communication standard require when it was first issued, and how did the initial requirements work? |
| F | A snack has 140 calories per 28g, and another has 210 calories per 55g. Which is more calorie-dense, and by how much? |

## Per-Case Active Recovery

| Case | Considered | Eligible | Used | Reason / skip reason | Missing classes | Result / new URLs | Role / depth |
|---|---:|---:|---:|---|---|---:|---|
| A | yes | yes | yes | `answer_contract_legal_text_gap:legal_or_regulatory_text,official_current_rules` | `legal_or_regulatory_text`, `official_current_rules` | 16 / 10 | `source_class_recovery` / `basic` |
| B | yes | no | no | `blocked_by_weak_corpus_recovery` | `official_current_rules`, `legal_or_regulatory_text` | 0 / 0 | n/a |
| C | yes | no | no | `blocked_by_weak_corpus_recovery` | `legal_or_regulatory_text`, `official_current_rules` | 0 / 0 | n/a |
| D | yes | no | no | `blocked_by_weak_corpus_recovery`; blockers also included `not_recommended`, `blocked_by_iteration_budget` | none | 0 / 0 | n/a |
| E | yes | no | no | `blocked_by_iteration_budget`; blockers also included `not_recommended` | none | 0 / 0 | n/a |
| F | yes | no | no | `blocked_by_weak_corpus_recovery`; blockers also included `not_recommended`, `blocked_by_iteration_budget` | none | 0 / 0 | n/a |

## Per-Case Recovered-Source Quality

| Case | Recovery quality status | Tier counts | Class counts | Official/primary recovered | Accepted URLs | Promoted sources | Final official / legal / primary | Interpretation |
|---|---|---|---|---:|---:|---:|---|---|
| A | `no_relevant_sources` | `{"secondary":10,"unknown":6}` | `{}` | 0 | 9 | 1 | 0 / 0 / 0 | Recovery fired, but did not recover useful official/legal/current-primary material. |
| B | `unknown` | `{}` | `{}` | 0 | 0 | 0 | 0 / 0 / 0 | Source-class recovery was blocked by weak-corpus recovery before execution. |
| C | `unknown` | `{}` | `{}` | 0 | 0 | 0 | 0 / 0 / 0 | Source-class recovery was blocked by weak-corpus recovery before execution. |
| D | `unknown` | `{}` | `{}` | 0 | 0 | 0 | 0 / 0 / 0 | Recovery did not hijack the recommendation-control lane. |
| E | `unknown` | `{}` | `{}` | 0 | 0 | 0 | 4 / 1 / 1 | Current-rules recovery did not overfire; final source-class counts came from normal retrieval, not recovered evidence. |
| F | `unknown` | `{}` | `{}` | 0 | 0 | 0 | 0 / 0 / 0 | No source-class recovery for the quantitative control. |

## Per-Case Recovered Visibility

| Case | Considered | Eligible | Used | Reason | Reserved count | Reserved source IDs | Drop reason |
|---|---:|---:|---:|---|---:|---|---|
| A | yes | no | no | `no_relevant_sources` | 0 | none | `no_relevant_sources` |
| B | no | no | no | `source_class_recovery_not_used` | 0 | none | `source_class_recovery_not_used` |
| C | no | no | no | `source_class_recovery_not_used` | 0 | none | `source_class_recovery_not_used` |
| D | no | no | no | `source_class_recovery_not_used` | 0 | none | `source_class_recovery_not_used` |
| E | no | no | no | `source_class_recovery_not_used` | 0 | none | `source_class_recovery_not_used` |
| F | no | no | no | `source_class_recovery_not_used` | 0 | none | `source_class_recovery_not_used` |

No case recovered a qualifying official/legal/current-primary source. Therefore
AG-19 did not expose a distinct AG-17 visibility failure. The boundary had no
qualified recovered source to reserve.

## Per-Case Answer Quality

| Case | Compact grade | Source quality improved? | Answer-quality note |
|---|---|---|---|
| A | D / fail source quality | no | The answer asserts current DOT wheelchair obligations but cites unrelated DOT/news items and has zero final official/legal/primary sources. |
| B | C- / safe caveat, fail source quality | no | The answer avoids inventing the FTC noncompete status, but does not answer the legal/status question. |
| C | C- / safe caveat, fail source quality | no | The answer avoids inventing FDA LDT posture, but does not answer the enforcement timeline. |
| D | C / safe skip, weak recommendation | n/a | Active recovery did not hijack the recommendation lane; the answer mentions Cookiebot and LiteConsent but stops short of a concrete recommendation. |
| E | C / partial historical answer | n/a | Current-rules recovery did not overfire, but the answer relies on secondary NCBI/PubMed material rather than original OSHA/Federal Register text. |
| F | A- / quantitative final answer consistent | n/a | The final answer correctly identifies Snack A as denser and contains no winner contradiction. |

## Quantitative Consistency Result

Case F reported:

- `quantitative_consistency_check_attempted`: `true`
- `quantitative_consistency_status`: `not_applicable`
- `quantitative_consistency_reason`: `no_stated_winner_detected`
- `quantitative_consistency_computed_winner`: `item_a`
- `quantitative_consistency_stated_winner`: `null`
- normalized values: `item_a = 5.0 calories/g`; `item_b = 3.818182 calories/g`
- `quantitative_consistency_guard_applied`: `false`
- `quantitative_consistency_guard_reason`: `status_not_contradiction`
- `quantitative_consistency_guard_final_answer_replaced`: `false`

The final user-facing answer did not contain a computed/stated winner
contradiction. This live case therefore passes the output-quality negative
control, but it did not exercise the AG-18 replacement path because the Author
did not make the old error in final prose.

## Safety And Leak Result

No runtime code or protected surface was changed. No provider routing,
provider selection, search-depth policy, source ranking/filtering, prompt
semantics, persistence schema, Analyst/Economist/Author handoff design, or
controller-loop behavior was edited.

No secrets, `.env` values, API keys, credential files, DBs, caches, raw provider
payloads, raw prompts, full traces, or raw execution rows were committed. The
local output-quality review packet is ignored under `output/`; `git
check-ignore -v output/ag19_output_quality_review_packet.md` reports the
`.gitignore` `output/` rule, and `git ls-files output` returns no tracked
paths. The temporary `output/ag19_case_outputs_tmp/` directory was deleted after
the packet was built.

Safety result: pass.

## Result

AG-19 is a source-quality failure, not a recovered-visibility failure. The live
set did not produce any recovered official/legal/current-primary source for
AG-17 to reserve. Case A proved the boundary blocks reservation when recovered
source quality is `no_relevant_sources`; Cases B and C showed source-class
recovery was blocked before execution by weak-corpus recovery.

Primary question: not proven. When source-class recovery ran, it did not find
contract-critical official/legal/current-primary material. Therefore recovered
sources could not be reserved into final evidence and did not improve final
source quality or answer quality.

Secondary question: final output passed. Case F contained no calorie-density
winner contradiction. The live run did not prove the guard replacement path,
but offline AG-18 tests passed and the contradictory prose did not reach final
output.

No evidence of overfitting appeared. AG-19 used a rotated query set, made no
runtime-code changes from live observations, and did not tune prompts,
providers, source ranking, search depth, or heuristics.

## AG-20 Recommendation

AG-20 should be a source recovery query/provider quality revision, with special
attention to current legal/regulatory cases that route into off-topic or weak
corpus recovery before official/legal source-class recovery can execute.

Do not broaden the controller loop yet. Do not revise recovered visibility
until a live or deterministic harness case actually recovers qualifying
official/legal/current-primary material that fails to survive final evidence.
Do not roll back to passive-only based on this run.
