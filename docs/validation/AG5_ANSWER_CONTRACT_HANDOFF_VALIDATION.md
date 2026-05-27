# AG-5 Answer-Contract Handoff Validation

Status: offline/replay gate passed; bounded live validation completed.

Scope: validate whether `answer_contract_fulfillment_handoff` is compact, safe, useful, and behavior-preserving without changing runtime behavior, provider routing, prompts, search policy, source filtering/ranking, or persistence schema.

## Offline/Replay Cases

| Case | Answer contract family | Handoff present | Expected action/posture | Observed action/posture | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| current_official_rules_gap | legal_or_regulatory_primary_text | yes | recover missing official/current source class | `recover_missing_source_class`; partial legal/regulatory posture | pass | Captures `official_current_rules` gap and approved source-class action history. |
| developing_event_orientation | developing_event_orientation | yes | caveated developing-event posture | `stop_insufficient_with_caveat`; unsettled guidance remains unfulfilled | pass | Uses existing retrieval-stop decision vocabulary. |
| official_tax_rules_satisfied | legal_or_regulatory_primary_text | yes | official/legal evidence satisfied; no approved recovery | skipped source-class recovery with `not_recommended`; primary-text-grounded posture | pass | No approved behavior change. |
| quantitative_comparison_satisfied | quantitative_comparison_or_model | yes | quantitative obligations fulfilled | fulfilled quantitative posture; no social or Scrutineer action | pass | No raw quantitative packet or Economist framework material. |
| recommendation_social_optional | recommendation_decision_support | yes | recommendation posture; social optional | fulfilled recommendation posture; social summary `relevant_optional` | pass | Social is not treated as factual authority. |
| explicit_social_signal_partial | social_media_or_social_sentiment_answer | yes | social signal central, unavailable/partial | partial social-signal posture; `social_signal` unfulfilled | pass | Provider integration is not attempted. |
| weak_evidence_social_partial | social_media_or_social_sentiment_answer | yes | weak/social evidence caveat | stronger independent evidence unfulfilled; central social summary | pass | Avoids overclaiming from weak evidence. |
| historical_archival_gap | historical_or_archival_answer | yes | recover missing primary/archival source class | `recover_missing_source_class`; historical posture | pass | Captures archival/legal source-class gap compactly. |
| conceptual_negative_control | conceptual_explainer | yes | behavior preserved; no approved recovery/social/Scrutineer action | search calls, author prompts, final report, trace schema, and SQLite columns unchanged except handoff trace key | pass | Disabled-handoff comparison confirms no runtime behavior change. |

## Safety Checks

- Handoff payloads are bounded at 4,500 bytes in the AG-5 replay tests.
- Evidence references are capped at five compact references.
- Protected markers are rejected from handoff payloads, including raw provider diagnostics, raw prompts, raw evidence dumps, quantitative packet material, Economist framework material, task ledger material, and controller diagnostics.
- Behavior preservation is checked against a disabled handoff path for search calls, author prompts, final report, execution trace key diff, JSONL row keys, and SQLite `RUN_COLUMNS`.

## Live Validation

Budget used: 8 successful live CLI runs, 0 retries.

Raw live reports and raw execution rows were not committed. Validation used only compact fields from the AG-5 appended execution rows.

Safety result: pass. Every live execution row had a compact handoff, no protected-marker leak, and no social provider integration attempt. Handoff size range was 1,685 to 2,172 bytes.

Calibration result: mixed. The handoff is safe enough for further live calibration, but not ready for active behavior promotion.

| Case | Expected family/action | Observed inferred family/action/posture | Result | Notes |
| --- | --- | --- | --- | --- |
| A. EU AI Act GPAI obligations | current official/legal; show official/current evidence status | developing_event_orientation; skipped source-class recovery; fulfilled directional posture | partial | Safe and compact, but official/legal source-class need was not explicit in the handoff. |
| B. EC high-risk AI guidelines | developing event or current official; mark unsettled points | developing_event_orientation; `stop_insufficient_with_caveat`; `current_primary_or_official` unfulfilled | pass | Good caveated posture for unsettled/current guidance. |
| C. EV charger tax credit | current official/legal; prefer IRS/official evidence | developing_event_orientation; `stop_insufficient_with_caveat`; `current_primary_or_official` unfulfilled | partial | Captures a current-primary gap, but family is not official/legal. |
| D. Bread calorie density | quantitative comparison; no social/Scrutineer | quantitative_comparison_or_model; fulfilled quantitative posture | pass | No protected quantitative/Economist material in handoff. |
| E. Cursor vs VS Code/Copilot | recommendation; social optional | quantitative_comparison_or_model; fulfilled quantitative posture | fail calibration | Router/comparison metadata pushed the handoff into quantitative posture, losing recommendation/social-optional framing. |
| F. Cursor social sentiment | social central; social unavailable/partial if no provider | social_media_or_social_sentiment_answer; `stop_insufficient_with_caveat`; `social_signal` unfulfilled; social status `not_checked` | partial | Correctly treats social as central and unfulfilled, but provider-unavailable status is not explicit. |
| G. Bluesky vs X among journalists | weak evidence or social; avoid overclaiming | quantitative_comparison_or_model; fulfilled quantitative posture | fail calibration | Comparative metadata overrode weak/social-evidence posture. |
| H. Leaded gasoline phase-down history | historical/archival or legal primary text | conceptual_explainer; `stop_insufficient_with_caveat`; no unfulfilled historical/archival item | fail calibration | Safe artifact, but not useful enough for historical/archival obligations. |

Redactions: none were needed in the committed note because raw outputs, raw prompts, provider payloads, evidence dumps, and full transcripts are omitted.

Recommended AG-6 direction: design revision plus targeted validation for family/posture mapping before active behavior promotion. The next phase should not promote the handoff into behavior-changing decisions until recommendation, weak/social, historical/archival, and official/legal family calibration improves.

## Consumer / Decision / Deletion Criteria

Consumer: AG-5 phase review and AG-6 planning.

Decision: whether the runtime handoff is ready for broader live calibration, active behavior promotion, more validation, or design revision.

Deletion criteria: this note may be replaced by a later phase summary once AG-6 records the promotion or revision decision.
