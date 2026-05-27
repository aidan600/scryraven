# AG-11 Active Official Source-Class Recovery Pilot

Scope: promote one bounded active behavior. A calibrated answer-contract
official/current/legal source-class gap can now authorize one existing
source-class recovery attempt before synthesis.

## Active Behavior

AG-11 builds a pre-recovery runtime answer-contract handoff from already
computed retrieval facts and source-class observability. If that handoff shows
an unfulfilled/partial gap for an eligible official/current/legal source class,
the gap is merged into the existing source-class recovery recommendation.

Eligible answer-contract source classes:

- `official_current_rules`
- `legal_or_regulatory_text`
- `current_primary_or_official`

The existing source-class lifecycle still owns caps, blockers, provider role,
search depth, action recording, attempt count, and executor handoff.

## Caps And Blockers

AG-11 reuses existing source-class recovery blockers:

- prior source-class recovery attempt blocks another attempt
- weak-corpus recovery ownership blocks source-class recovery
- weak corpus state blocks source-class recovery when weak-corpus recovery does
  not clear ownership
- retrieval iteration budget exhaustion blocks recovery
- provider policy or search-depth escalation requirements block recovery
- retrieve-to-anchor, post-Analyst, and Author-phase blockers still apply
- missing recovery queries still block execution

Provider role remains `source_class_recovery`. Search depth remains the current
search depth supplied to the existing lifecycle. Provider selection, prompt
semantics, ranking/filtering, additive merge behavior, persistence schema,
Analyst/Economist/Author handoff, social providers, and Scrutineer policy are
unchanged.

## Reason Codes

New active-pilot reason codes in the existing recovery reason path:

- `answer_contract_official_gap`
- `answer_contract_legal_text_gap`
- `answer_contract_current_primary_gap`

Existing blocker codes remain unchanged, including `not_recommended`,
`blocked_by_weak_corpus_recovery`, `blocked_by_iteration_budget`, and
`already_attempted`.

New trace field: `active_source_class_recovery_reason`.

- Named consumer: AG-11/AG-12 phase review and controller diagnostics review.
- Decision enabled: distinguish answer-contract-driven recovery from older
  query/source-class recommendation recovery when the active action fires.
- Deletion/promotion criterion: remove if the active pilot is reverted; promote
  into the durable source-class lifecycle contract if AG-12 live validation
  confirms the reason is needed for review.
- Validation link: `tests/test_answer_contract_source_class_recovery_ag11.py`
  and `tests/test_source_class_recovery_trace.py`.

## Tests

Added AG-11 tests for:

- official/current gap authorizes exactly one existing recovery action
- legal/regulatory text gap authorizes exactly one existing recovery action
- current-primary gap preserves existing provider role and search depth
- official evidence already present does not trigger recovery
- conceptual sufficient evidence does not trigger recovery
- recommendation with legal/tax constraint does not hijack recovery
- weak-corpus ownership blocks the answer-contract trigger
- retrieval budget exhaustion blocks the answer-contract trigger
- prior source-class recovery prevents duplicate attempts
- social provider-unavailable remains social-only and does not trigger recovery
- bread calorie-density quantitative control does not trigger recovery
- helper imports do not introduce provider routing, prompts, persistence, or
  live provider dependencies

## Still Passive

Candidate-v2 diagnostics, broad controller ownership, live validation, social
provider integration, Scrutineer expansion, Analyst skip behavior, Economist
shortcuts, and downstream handoff redesign remain passive or unchanged.

## AG-12 Readout

AG-11 supports AG-12 as bounded live validation of this active pilot only:
verify whether official/current/legal answer-contract gaps trigger a single
useful existing source-class recovery attempt without widening provider,
search-depth, prompt, or ownership behavior. It does not support broader live
validation or broader controller promotion yet.
