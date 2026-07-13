Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG6_ANSWER_CONTRACT_CALIBRATION).

# AG-6 Answer-Contract Family/Posture Calibration

Status: offline calibration revision implemented; targeted tests passed.

Scope: revise passive answer-contract family/posture drafting and compact handoff
status rendering for AG-5 calibration failures. This phase did not change runtime
retrieval behavior, provider routing, prompts, source ranking/filtering,
persistence schema, social provider integration, or active behavior promotion.

## Design Revision

- Explicit social-media, social-sentiment, and social-platform adoption signals
  now outrank broad quantitative/comparison metadata.
- Historical/archival cues such as original rules, phase-down requirements, and
  change over time now outrank broad comparison metadata.
- Current legal/regulatory obligations, tax-credit rules, enforcement, IRS, and
  AI Act-style official/legal cues now outrank broad comparison metadata.
- Recommendation/decision-support cues such as choosing, practical tradeoffs,
  reviews, and user-experience evidence now outrank broad quantitative metadata.
- Genuine quantitative comparison metadata remains quantitative when no stronger
  social, historical, legal/current-official, or recommendation signal is present.
- Central social-signal handoffs with no configured social provider now render
  `status=provider_unavailable` even when the runtime path only passively adapts
  already-computed facts.

## Targeted Coverage

Added AG-6 tests for:

- Cursor vs VS Code/Copilot recommendation vs quantitative disambiguation.
- Recommendation with numeric budget constraints remaining recommendation.
- Bluesky vs X among journalists social-platform adoption vs quantitative
  disambiguation.
- Social-platform numeric active-user comparison remaining quantitative.
- Leaded gasoline phase-down historical/archival recognition.
- Conceptual history-context explainer remaining conceptual.
- EU AI Act and EV charger tax-credit legal/current-official obligation surfacing.
- Explicit social runtime handoff provider-unavailable status.
- Bread calorie-density quantitative negative control.

## Promotion Decision

AG-6 makes the handoff suitable for another bounded live validation pass focused
on family/posture calibration. It does not make the handoff ready for active
behavior promotion. Active behavior should remain blocked until a later phase
shows that calibrated handoff fields can safely drive behavior-changing
decisions without protected-surface leakage or downstream regressions.

## Consumer / Decision / Deletion Criteria

Consumer: AG-6 phase review and the next bounded live validation phase.

Decision: whether the revised passive calibration is strong enough to replay
against fresh live rows before any active behavior promotion is considered.

Deletion criteria: this note may be replaced by a later phase summary once live
calibration either confirms or revises these family/posture rules.
