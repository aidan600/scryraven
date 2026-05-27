# AG-7 Answer Quality Review

Status: compact qualitative review of representative AG-7 live answers.

Scope: judge whether selected user-facing answers were useful, appropriately
sourced/caveated, and consistent with the expected answer-contract posture. Raw
reports, full transcripts, raw logs, provider payloads, prompts, evidence dumps,
and full execution rows are not included.

Reviewed cases: A, D, E, F, G, H.

| Case | Expected contract | Observed handoff summary | Answer quality | Citation/source sanity | Handoff vs answer | Compact excerpt | Notes for reviewer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A. EU AI Act GPAI obligations | Official/legal or current-rules posture with explicit official/current obligations | `developing_event_orientation`; directional posture; source-class recovery skipped; no official-source gap surfaced | partial | partial | The answer was more assertive than the handoff justified. It addressed obligations and dates, but relied on secondary political reporting rather than official/legal text. | "baseline Chapter V regime" | Human review should verify the legal timeline against official EU sources before treating this as a good answer. |
| D. Developer tooling recommendation | Recommendation decision support; social signal optional | `recommendation_decision_support`; recommendation with tradeoffs; social optional and not checked | pass | partial | The handoff explained the answer reasonably well. The final answer made a useful directional recommendation and acknowledged that evidence was mostly comparison articles, but it lacked primary product/user-experience evidence. | "Copilot is the safest default" | Reviewer should check whether the tool-specific claims are current and whether primary docs/pricing should be required in future recommendation cases. |
| E. Cursor social sentiment | Social/sentiment answer; central social signal; provider unavailable if no social provider | `social_media_or_social_sentiment_answer`; `social_signal` unfulfilled; provider unavailable | partial | no | The handoff explained the core gap well. The answer correctly said the social signal was not reliable, but the sourced material was mostly unrelated and the answer added an unnecessary model-derived trust range. | "treat any apparent enthusiasm or backlash as anecdotal" | Reviewer should decide whether social-sentiment answers should forbid invented numeric confidence ranges when no social corpus is available. |
| F. Bluesky vs X weak/social evidence | Social or weak-evidence posture; avoid overclaiming; identify stronger evidence needed | `social_media_or_social_sentiment_answer`; social central and provider unavailable; `social_signal` unfulfilled | pass | partial | The final answer matched the handoff: it refused to overclaim and identified the evidence needed to answer responsibly. It did not pretend weak retrieval established platform dominance. | "not enough evidence ... default breaking-news venue" | Reviewer can treat this as a good qualitative pattern for weak/social questions, while noting that no representative social/provider data was available. |
| G. Leaded gasoline phase-down history | Historical/archival or legal-primary posture with primary/archival obligations explicit | `historical_or_archival_answer`; `primary_or_archival` unfulfilled; insufficient-with-caveat stop | partial | partial | The handoff explained the main gap. The answer did not fully answer the original rule-change question, but it caveated retrieval limits and avoided pretending secondary history was primary rule text. | "not the actual rule text or its amendments" | Reviewer should decide whether historical/legal cases should more strongly require Federal Register, EPA, CFR, or statutory sources before answering. |
| H. Bread calorie-density comparison | Quantitative comparison; variables, units, and calculation explicit; no social or Scrutineer | `quantitative_comparison_or_model`; bounded quantitative posture; quantitative obligations fulfilled | pass | yes | The final answer matched the handoff and gave the correct normalized comparison. It used the user-provided numbers directly and did not need social or official evidence. | "257 calories per 100 g ... 176 calories per 100 g" | Reviewer should note that auxiliary nutrition citations were not necessary for the core calculation, but they did not undermine the result. |

## Summary

The best answer-quality results were D, F, and H. E and G were safe but partial:
they recognized weak evidence and avoided major overclaiming, while still missing
important source classes. A is the clearest official/legal quality concern:
the answer sounded useful, but the evidence class was not strong enough for the
legal/current-rule posture.

No code was patched based on these qualitative observations. The recommended
AG-8 direction remains calibration revision before active behavior promotion.
