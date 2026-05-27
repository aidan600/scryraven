# AG-9 Live Re-Validation

Status: offline gate passed; bounded live validation completed; compact validation summary committed. The full truth-review packet is local and untracked only.

Scope: validation-only after AG-8. No runtime behavior, provider routing, prompt semantics, source ranking/filtering, persistence schema, social provider integration, Scrutineer policy, Analyst/Economist/Author handoff, or active behavior decision was changed.

Base: updated `main` at `c14294293f206bca6eb4ba1d4ca81b85d824fd3e`, including AG-5, AG-6, AG-7, and AG-8 merge history.

## Offline Gate

| Check | Result | Notes |
| --- | --- | --- |
| `git pull --ff-only origin main` | pass | Already up to date. |
| Main-history confirmation | pass | Recent main history includes AG-5 runtime handoff validation, AG-6 family/posture calibration, AG-7 post-calibration live re-validation, and AG-8 official/current legal calibration. |
| `py -m ruff check .` | pass | No lint failures. |
| `git diff --check` | pass | No whitespace failures before live/doc generation. |
| `py -m pytest tests/test_answer_contract_calibration_ag8.py` | pass, 9 passed | Initial run emitted a repo-local `.pytest_cache` access warning; no test failure. |
| `py -m pytest --basetemp=C:\tmp\.pytest-tmp -o cache_dir=C:\tmp\pytest_cache_ag9 tests/test_answer_contract_runtime_validation.py` | pass, 9 passed | AG-7/AG-5 runtime validation. |
| `py -m pytest --basetemp=C:\tmp\.pytest-tmp -o cache_dir=C:\tmp\pytest_cache_ag9 tests/test_answer_contract_runtime_handoff.py` | pass, 9 passed | AG-4 runtime handoff. |
| `py -m pytest --basetemp=C:\tmp\.pytest-tmp -o cache_dir=C:\tmp\pytest_cache_ag9 tests/test_answer_contract_controller.py tests/test_answer_contract_pipeline_adapter.py tests/test_answer_contract_loop_harness.py` | pass, 32 passed | AG-1/2/3 controller, adapter, and loop harness. |
| `py -m pytest --basetemp=C:\tmp\.pytest-tmp -o cache_dir=C:\tmp\pytest_cache_ag9` | pass, 970 passed, 1 deselected | Full offline suite; source-class, weak-corpus, and retrieval-stop focused coverage included by full suite. |

Offline stop conditions: none. No protected-surface leak tests failed, no schema change appeared necessary, no provider-routing/prompt/source-ranking behavior change was made, and no design decision was required to proceed.

## Live Validation

Budget used: 8 successful live ProPlex CLI runs out of 8 approved, 0 reserve runs, 0 live retries.

Live path: `py -m proplex "<query>" --mode Balanced --output output\ag9_live_revalidation\<case>.md`. Temporary full reports stayed under ignored `output/`; only this compact sanitized validation summary is committed.

Queries run: A-H exactly as approved in the phase brief.

### Telemetry / Handoff Results

| Case | Observed posture | Source-class status | Social signal | Action/skip summary | Telemetry grade |
| --- | --- | --- | --- | --- | --- |
| A | primary-text-grounded explanation | legal_or_regulatory_text: expected_but_only_secondary | none | recover_missing_source_class: blocked_by_iteration_budget (blocked_by_iteration_budget) | partial |
| B | directional answer with uncertainty markers | none | none | recover_missing_source_class: blocked_by_iteration_budget (blocked_by_iteration_budget) | partial |
| C | answer with caveats | legal_or_regulatory_text: expected_but_only_secondary | none | stop_insufficient_with_caveat: weak_corpus_recovery_completed (no_useful_new_query) | pass |
| D | recommendation with tradeoffs | official_current_rules: expected_but_only_secondary | social_signal_relevance=relevant_optional; status=not_checked | recover_missing_source_class: blocked_by_iteration_budget (blocked_by_iteration_budget) | partial |
| E | answer with caveats | none | social_signal_relevance=central; status=provider_unavailable | stop_insufficient_with_caveat: weak_corpus_recovery_completed (no_useful_new_query) | pass |
| F | social-signal answer with authority caveat | none | social_signal_relevance=central; status=provider_unavailable | recover_missing_source_class: blocked_by_iteration_budget (blocked_by_iteration_budget) | pass |
| G | answer with caveats | none | none | stop_insufficient_with_caveat: weak_corpus_recovery_completed (no_useful_new_query) | pass |
| H | answer with caveats | none | none | stop_insufficient_with_caveat: redundant_with_prior_queries (redundant_next_query) | pass |

### Answer-Quality Results

| Case | Answer-quality grade | Compact rationale |
| --- | --- | --- |
| A | partial | Broadly useful legal timeline, but official/legal citation quality is poor and source gap is not caveated. |
| B | partial | Distinguishes settled/uncertain status, but relies on a single secondary source and may conflate guideline status with machinery-scope negotiations. |
| C | fail | Safely caveats missing IRS/federal guidance, but does not answer the requested tax-rule question. |
| D | partial | Recommendation shape is right, but tax eligibility and product recommendation sourcing are weak. |
| E | pass | Correctly reports no direct social sentiment signal and warns against overtrusting generic AI-agent chatter. |
| F | pass | Correctly refuses overclaiming and identifies evidence needed for responsible social/platform adoption judgment. |
| G | partial | Safe but incomplete; does not provide original rule text or detailed change history. |
| H | pass | Correct normalized calculation and no unnecessary official/social posture. |

## Safety / Leak Result

- Protected material scan: pass. A local `rg` scan over temporary AG-9 reports found no API-key/secret/raw-prompt/provider-payload/internal-trace markers; the only hits were false positives from `FatSecret` citation URLs in case H.
- Raw live reports, raw provider payloads, raw prompts, raw execution rows, JSONL logs, DBs, caches, and full internal traces are not committed.
- No secrets/env/API keys were read, printed, copied, or edited. The CLI loaded its existing configuration internally.
- Social provider integration was not attempted.
- Scrutineer did not run in any live case.
- Economist ran in no AG-9 live case according to compact telemetry; Economist code execution was not requested, and Author did not receive raw quantitative packet or Economist framework material.
- Handoff compactness range: 1435 to 2027 bytes.

## AG-8 Readout

AG-8 improved official/current posture signals compared with AG-7, but the live results do not yet justify broader live validation or first active behavior planning. Case A now carries a primary-text-grounded posture, and case C records unfulfilled legal/official classes, but source-class satisfaction and final answer caveating still diverge from answer quality. Case D keeps recommendation posture as desired, while still missing official tax-source evidence.

The most important finding is not a new behavior bug to patch inside AG-9; it is a review/design gap: the compact handoff can say a legal/primary obligation is fulfilled even when source-class telemetry says the available evidence is only secondary, and final answers can be useful but under-cited for official/current legal claims.

## Main Questions

| Question | AG-9 answer |
| --- | --- |
| Did AG-8 fix official/current legal posture for live cases? | Partial. It improved posture and gap telemetry, but live official/current cases still show secondary-only source evidence and answer caveating gaps. |
| Are final user-facing answers factually useful and appropriately sourced/caveated? | Mixed. E, F, and H pass; A, B, D, and G are partial; C fails answer quality because it does not answer the requested tax-rule details. |
| Does the handoff explain the answer's strengths/gaps? | Partial. It is compact and useful in C, E, F, G, and H, but A and D show source-class/handoff mismatch or weak gap surfacing. |
| Is the system ready for broader live validation, another calibration revision, or first active behavior planning? | Another calibration/design revision. Broader live validation and active behavior planning should wait. |

## Overfitting Check

Codex saw no evidence of AG-9 overfitting because no runtime code or heuristic was tuned from live observations. The bounded eight-case set is too small to prove generality, and the observed issues should be treated as calibration/design findings for AG-10 rather than query-specific fixes.

## Truth Review Packet

Packet path: `output/ag9_truth_review_packet.md` on the local machine only. It is intentionally untracked because it includes full final user-facing answer text. Do not commit truth-review packets to repo history.

## AG-10 Recommendation

AG-10 should be another calibration/design revision before broader live validation or active behavior planning. Focus areas: make official/current legal source-class gaps visible when evidence is secondary-only, prevent handoff fulfilled-items from contradicting source-class status, and improve answer-level caveats when official/primary evidence is missing. Broader live validation should wait until those issues are resolved offline.

## Consumer / Decision / Deletion Criteria

Consumer: AG-9 phase review, ChatGPT truth review, and AG-10 planning.

Decision: whether AG-8 fixed official/current legal posture enough for broader validation or active planning. Decision from this packet: not yet; run another calibration/design revision.

Deletion criteria: this note and packet can be superseded after AG-10 records either a revised source-class/contract calibration or an explicit decision to broaden live validation.
