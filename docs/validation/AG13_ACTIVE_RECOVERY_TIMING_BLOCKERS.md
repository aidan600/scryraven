# AG-13 Active Recovery Timing And Blocker Revision

Scope: offline design/revision phase for the AG-11 active official/current/legal
source-class recovery pilot. No live validation was run.

## Diagnosis

AG-12 showed that the active answer-contract source-class trigger was safe but
too late to be useful in several official/current/legal cases.

- Cases A and C reached `blocked_by_iteration_budget` because the AG-11
  answer-contract gap trigger is evaluated after the main retrieval loop, just
  before synthesis. By that point Balanced live runs had already spent both
  main retrieval iterations, so the existing source-class lifecycle treated the
  active recovery action as budget-blocked.
- Cases B and D reached `blocked_by_weak_corpus_recovery` because weak-corpus
  recovery is evaluated during the first retrieval iteration and already owned
  the recovery path before the source-class lifecycle evaluated the AG-11 gap.
- Negative controls E, F, G, and H did not expose useful official/current/legal
  source-class gaps. Their blockers were safe telemetry outcomes rather than
  evidence that source-class recovery should have run.

Root cause: trigger timing and recovery ownership ordering. The official/current
answer-contract gap can be detected only after runtime handoff/fulfillment is
built from retrieval facts, but the old lifecycle allowed it to run only when
normal main-loop iteration room remained.

## Revision

AG-13 adds a narrow reserved answer-contract source-class slot to the existing
source-class recovery controller and lifecycle.

The slot is available only when all of these are true:

- the orchestrator is in a multi-iteration mode (`Balanced` or `Deep`);
- the recommendation reason is one of the AG-11 answer-contract reasons:
  `answer_contract_official_gap`,
  `answer_contract_legal_text_gap`, or
  `answer_contract_current_primary_gap`;
- no source-class recovery attempt has already been recorded;
- the existing weak-corpus, weak-corpus-recovery, provider-policy,
  search-depth, retrieve-to-anchor, no-query, post-Analyst, and Author-phase
  blockers do not apply.

The change does not add a provider or retrieval path. It still records and
executes the existing `source_class_recovery` action through the existing
lifecycle and executor.

## Preserved Caps And Blockers

Preserved:

- provider role remains `source_class_recovery`;
- current search depth is reused;
- provider list is reused from the latest retrieval pass;
- query cap remains the existing source-class recovery cap;
- additive merge behavior is unchanged;
- duplicate attempt prevention remains active;
- weak-corpus recovery ownership remains a blocker;
- true weak corpus remains blocked unless weak-corpus recovery clears ownership;
- Fast/no-slot iteration budget exhaustion remains blocked;
- generic source-class gaps cannot use the answer-contract slot;
- provider routing, provider selection, search-depth policy, prompts,
  source ranking/filtering, persistence schema, Analyst/Economist/Author
  handoff, Scrutineer behavior, and social provider integration were not
  changed.

## Offline Tests

Added `tests/test_answer_contract_source_class_recovery_ag13.py`.

Positive controls:

- official/current/legal secondary-only evidence can spend the Balanced main
  retrieval loop and still execute one existing source-class recovery attempt
  before synthesis;
- legal/regulatory text gaps can use the reserved answer-contract slot;
- current-primary/official developing-status gaps preserve search depth while
  using the slot.

Blocker and negative controls:

- duplicate source-class recovery attempts are still blocked;
- true weak-corpus ownership still blocks the answer-contract slot;
- iteration-budget exhaustion still blocks when no reserved slot is available;
- conceptual sufficient evidence does not trigger AG-11 recovery;
- recommendation with legal/tax constraints does not hijack recovery;
- social provider-unavailable cases do not trigger official/current recovery;
- historical/archival cases do not trigger the AG-11 official/current/legal
  pilot;
- bread calorie-density remains quantitative with no recovery.

Existing source-class controller, lifecycle, trace, executor, weak-corpus,
retrieval-stop, runtime handoff, AG-11, AG-10, and AG-8 suites remain the
behavior-preservation gate.

## Live Validation Recommendation

AG-14 should run bounded live validation of the same AG-12 set or a close
variant. Expected useful signal: at least one official/current/legal or
current-primary case executes one `source_class_recovery` provider-role attempt
with reused search depth and improved official/current/legal evidence quality.

If AG-14 still produces zero useful source-class recovery executions, the next
step should be design reconsideration rather than broader promotion. If weak
corpus continues to block otherwise good official/current/legal cases, replacing
weak-corpus recovery for those cases would require an explicit protected
ownership decision.

## Artifact Safety

No truth-review packet was created. No raw live output was created or committed.
No files under `output/` were committed.
