# AG-7 Answer-Contract Live Re-Validation

Status: offline gate passed; bounded live validation completed.

Scope: re-validate the runtime `answer_contract_fulfillment_handoff` after AG-6
family/posture calibration. This phase did not promote the handoff into active
behavior decisions and did not change provider routing, prompts, source
ranking/filtering, persistence schema, social provider integration, or protected
runtime behavior.

## Offline Gate

Base: updated `main` at `8617988d016b7516a9162c5156ec0197df588384`.

Results:

| Check | Result | Notes |
| --- | --- | --- |
| `py -m pytest tests/test_answer_contract_calibration_ag6.py` | pass, 9 passed | Initial run emitted a repo-local pytest cache warning. |
| `py -m pytest tests/test_answer_contract_runtime_validation.py` | pass, 9 passed | First run hit the known Windows repo-local `.pytest-tmp` cleanup permission issue after 8 passed; rerun used `--basetemp=C:\tmp\.pytest-tmp-ag7 -o cache_dir=C:\tmp\pytest_cache_ag7`. |
| `py -m pytest tests/test_answer_contract_runtime_handoff.py` | pass, 9 passed | Clean rerun with temp/cache under `C:\tmp`. |
| `py -m pytest tests/test_answer_contract_controller.py tests/test_answer_contract_pipeline_adapter.py tests/test_answer_contract_loop_harness.py` | pass, 32 passed | AG-1/2/3 controller, adapter, and loop harness. |
| `py -m pytest tests/test_weak_corpus_controller.py tests/test_weak_corpus_recovery.py tests/test_source_class_recovery_controller.py tests/test_source_class_recovery_lifecycle.py tests/test_retrieval_stop_controller.py` | pass, 35 passed | Focused protected source-class, weak-corpus, and retrieval-stop guardrail tests. |
| `py -m ruff check .` | pass | No lint failures. |
| `git diff --check` | pass | No whitespace failures. |
| `py -m pytest --basetemp=C:\tmp\.pytest-tmp -o cache_dir=C:\tmp\pytest_cache_ag7` | pass, 961 passed, 1 deselected | A prior full-suite run with `C:\tmp\.pytest-tmp-ag7` failed only because `test_pytest_tmp_path_hardening.py` expects a path part named exactly `.pytest-tmp`. |

Offline stop conditions: none.

## Live Validation

Budget used: 8 successful live CLI runs, 0 retries, 0 reserve runs.

Queries run: A-H primary validation cases only. Reserve cases I-J were not run.

Raw live reports, raw execution rows, raw prompts, raw provider payloads, raw
evidence dumps, and full transcripts were not committed. Live review used only
compact fields from the AG-7 appended execution rows and sanitized report notes.

| Case | Query short name | Expected family/posture | Observed family/posture/action summary | Result | Notes |
| --- | --- | --- | --- | --- | --- |
| A | EU AI Act GPAI obligations | `legal_or_regulatory_primary_text` or `current_official_rules`; official/current obligations explicit | `developing_event_orientation`; directional answer with uncertainty markers; source-class recovery skipped with `blocked_by_iteration_budget`; no unfulfilled official/legal item | partial | Safe and compact, but Router `intent=news` still pulls the handoff out of official/legal posture and no official-source gap is explicit. |
| B | EU high-risk AI guidelines | `developing_event_orientation` or `current_official_rules`; unsettled/current status explicit | `developing_event_orientation`; directional answer with uncertainty markers; source-class recovery skipped with `blocked_by_iteration_budget` | partial | Family/posture fits the developing-event case, but the handoff did not surface that only secondary evidence was found. |
| C | Federal EV charger credit | `legal_or_regulatory_primary_text` or `current_official_rules`; official/tax obligation explicit | `developing_event_orientation`; `stop_insufficient_with_caveat`; `current_primary_or_official` unfulfilled; recovery skipped with `blocked_by_weak_corpus_recovery` | partial | Captures the official-source gap, but family remains current/developing rather than legal/tax. |
| D | Developer tooling recommendation | `recommendation_decision_support`; social optional | `recommendation_decision_support`; recommendation with tradeoffs; social summary `relevant_optional; status=not_checked` | pass | AG-6 fixes the AG-5 recommendation-vs-quantitative failure for this live case. No social provider integration attempted. |
| E | Cursor social sentiment | `social_media_or_social_sentiment_answer`; social central; provider unavailable if no provider | `social_media_or_social_sentiment_answer`; `stop_insufficient_with_caveat`; `social_signal` unfulfilled; social summary `central; status=provider_unavailable` | pass | Correctly treats social evidence as central and unavailable without attempting social-provider integration. |
| F | Bluesky vs X weak/social evidence | `social_media_or_social_sentiment_answer` or weak-evidence posture; avoid overclaiming | `social_media_or_social_sentiment_answer`; partial answer noting social signal unavailable; `social_signal` unfulfilled; social summary `central; status=provider_unavailable` | pass | AG-6 fixes the AG-5 weak/social-vs-quantitative failure for this live case. |
| G | Leaded gasoline phase-down history | `historical_or_archival_answer` or legal primary text; archival/legal obligations explicit | `historical_or_archival_answer`; `stop_insufficient_with_caveat`; `primary_or_archival` unfulfilled; recovery skipped with `blocked_by_weak_corpus_recovery` | partial | Family and source-class gap improved from AG-5, but posture/action remains generic and blocked. |
| H | Bread calorie-density comparison | `quantitative_comparison_or_model`; variables/units/calculation explicit; no social or Scrutineer | `quantitative_comparison_or_model`; bounded quantitative answer with assumptions; quantitative obligations fulfilled | pass | Negative control stayed quantitative. Scrutineer did not run; Economist code execution was not requested. |

## Safety And Compactness

- Handoff size range: 1,653 to 2,155 bytes.
- Protected-marker leak scan: pass; no protected markers found in handoff payloads.
- Social provider integration: not attempted in any live case.
- Scrutineer: did not run in any live case.
- Economist: ran only for the quantitative negative control; Economist code execution was not requested, raw quantitative packet/framework material was not exposed to the handoff, and the Author did not receive raw Economist framework material.
- Behavior preservation: no code changes were made for live results; validation artifacts only.
- Schema/persistence: no SQLite/JSONL schema change.

## Calibration Read

AG-6 materially improved the AG-5 failures for recommendation, explicit social,
weak/social, historical/archival, and the quantitative negative control. The
handoff is useful as a diagnostic/review surface for broader calibration.

AG-6 did not fully solve official/legal current-rule live cases. In A and C,
Router `intent=news` still wins before legal/current-official cues in the
answer-contract family selection. C partially mitigates this by marking
`current_primary_or_official` unfulfilled; A does not surface the official-source
gap even though live evidence was secondary-only.

Overfitting result: no AG-7 code or heuristic tuning was made against live
outputs. The remaining issues are documented for design revision rather than
patched query-by-query.

## AG-8 Recommendation

AG-8 should be another calibration revision, not broader live validation and not
active behavior promotion. The next design target should be official/current
legal posture when Router emits `intent=news`, plus clearer handoff surfacing
when official/legal evidence is absent but the answer text is making official
rule claims.

## Consumer / Decision / Deletion Criteria

Consumer: AG-7 phase review, AG-8 planning, and answer-contract calibration
review.

Decision: whether the runtime handoff is useful enough for broader calibration
review after AG-6. Decision: yes as a diagnostic/review surface, no for active
behavior promotion.

Deletion criteria: this note may be replaced after a later phase records either
an official/current calibration revision or an explicit promotion decision.
