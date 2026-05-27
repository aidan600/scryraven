# Retrieval Budget Pressure Shadow Calibration - Phase 28B

Date: 2026-05-20

## Current Checkpoint And Scope

Current checkpoint for this calibration note: `main` / `origin/main` clean at
`2e1b918` (`feat: add retrieval budget pressure shadow telemetry`).

This is a Fast Lane docs-only calibration note for
`retrieval_budget_pressure_shadow_v1`. It explains how to interpret the
shadow-only retrieval budget pressure payload before any future soft-budget or
extra-pass policy work.

This document does not authorize runtime behavior changes. It does not change
retrieval, routing, provider selection, provider depth, query generation,
prompts, source filtering, source ranking, Analyst behavior, Economist
behavior, Author behavior, SQLite schema, replay fixtures, aggregation logic,
Project Sources, or generated logs.

The telemetry remains human-review and offline-calibration material only.

## Rule 0 Failure Analysis

The primary failure mode is treating shadow diagnostics as policy before they
have been calibrated. A false positive could add cost and latency, duplicate
weak-corpus recovery, chase a stale source-class expectation, continue
retrieval after evaluator sufficiency, or over-search when the final answer
already has sufficient evidence. A false negative could hide genuinely
budget-limited answers where official, primary, community, or quantitative
evidence was still missing at synthesis time.

Cost, novelty, marginal-yield, extra-pass, and answer-impact fields are
calibration signals. They are not safety gates and must not become control-flow
inputs without reviewed post-27B evidence, positive and negative controls, a
separate Rule 0 plan, and explicit approval for behavior-changing work.

The safest immediate use is to inspect aggregate patterns and selected JSONL
rows, looking for repeated overfire and underfire cases before proposing any
active soft-budget behavior.

## Field Reliability Ranking

### High Reliability

These fields are mostly structural or directly derived from existing
controller/budget state. They are suitable for confirming payload presence,
schema health, and hard iteration-budget context:

- `schema_version`
- `shadow_mode`
- `hard_mode_budget.mode`
- `hard_mode_budget.iteration`
- `hard_mode_budget.max_iterations`
- `hard_mode_budget.iterations_run`
- `hard_mode_budget.budget_stop_triggered`
- `hard_mode_budget.budget_stop_reason`
- `hard_mode_budget.budget_pressure_bucket`
- Aggregate `payload_rows`
- Aggregate `malformed_rows`

These still do not authorize behavior. They only establish whether the payload
exists and whether the hard budget state was observed cleanly.

### Medium Reliability

These fields are useful review inputs, but they depend on upstream trace
coverage, source-class heuristics, provider diagnostics, or final citation
shape:

- `last_pass_marginal_yield.new_source_count_last_pass`
- `last_pass_marginal_yield.new_domain_count_last_pass`
- `last_pass_marginal_yield.new_accepted_source_count_last_pass`
- `last_pass_marginal_yield.accepted_overlap_last_pass`
- `last_pass_marginal_yield.provider_attempts_last_pass`
- `remaining_evidence_gaps.evaluator_sufficient`
- `remaining_evidence_gaps.next_query_count`
- `remaining_evidence_gaps.next_query_source`
- `remaining_evidence_gaps.missing_expected_source_classes`
- `remaining_evidence_gaps.official_evidence_found`
- `remaining_evidence_gaps.community_signal_found`
- `remaining_evidence_gaps.corpus_state`
- `remaining_evidence_gaps.pre_analyst_gate_signals`
- `answer_quality_impact.unresolved_gap_count_at_synthesis`
- `answer_quality_impact.answer_outcome`
- `answer_quality_impact.review_flags`
- `answer_quality_impact.final_answer_source_count`
- `answer_quality_impact.final_answer_official_source_count`
- `answer_quality_impact.final_answer_missing_expected_source_class`

Medium reliability means the fields can guide manual review, especially when
cross-checked against the full JSONL trace and final answer. They should not be
used as active policy inputs.

### Directional Only

These fields combine proxies or incomplete calibration assumptions. They are
directional review signals only:

- `cost_state.estimated_cost_usd`
- `cost_state.estimated_cost_available`
- `cost_state.estimated_cost_source`
- `cost_state.estimated_cost_confidence_bucket`
- `last_pass_marginal_yield.query_novelty_score`
- `remaining_evidence_gaps.quant_metric_coverage_valid`
- `extra_pass_judgment.extra_pass_candidate_shadow`
- `extra_pass_judgment.extra_pass_candidate_reasons`
- `extra_pass_judgment.extra_pass_candidate_blockers`
- `extra_pass_judgment.extra_pass_candidate_query_count`
- `extra_pass_judgment.extra_pass_candidate_query_source`
- `extra_pass_judgment.extra_pass_budget_class`
- `answer_quality_impact.budget_limited_answer_shadow`
- `answer_quality_impact.budget_limited_answer_reason`

These fields are the main calibration targets. Reviewers should treat them as
"possible pressure" or "possible missed opportunity" labels, not as evidence
that an extra pass would have improved the answer.

### Deferred Or Not Reliable Yet

These fields are placeholders, deliberately null, or not yet supported by
enough reviewed evidence:

- `cost_state.cost_budget_soft_cap_usd`
- `cost_state.cost_budget_hard_cap_usd`
- `cost_state.cost_budget_spent_ratio`
- `last_pass_marginal_yield.new_official_source_count_last_pass`
- `last_pass_marginal_yield.new_primary_source_count_last_pass`
- `answer_quality_impact.author_budget_caveat_present`
- `answer_quality_impact.user_feedback_rating`
- `answer_quality_impact.manual_eval_score_if_available`

Do not infer missing cost caps, official-source marginal yield, manual quality,
or author caveat behavior from these fields until a later explicitly scoped
telemetry pass defines them.

## Reading Aggregate Output

`scripts/aggregate_run_quality.py` prints a
`Retrieval budget pressure shadow` section for the last configured run window.
It can be used for offline log review without running ProPlex, Streamlit,
providers, models, or live queries.

Read the section in this order:

1. `retrieval_budget_pressure_payload_rows`: count of rows in the window that
   contain a nested `retrieval_budget_pressure_shadow` payload. Low or zero
   counts mean there is not enough post-27B evidence to calibrate.

2. `retrieval_budget_pressure_malformed_rows`: count of malformed, unexpected,
   or schema-mismatched payloads. Any nontrivial rate should block policy
   discussion until the malformed cases are understood.

3. `budget_pressure_bucket_counts`: distribution of `exhausted`, `at_cap`,
   `near_cap`, `room_remaining`, and `unknown`. Start with truly exhausted
   rows before discussing extra-pass behavior.

4. `budget_stop_reason_counts`: reason labels for budget stops. Currently the
   expected hard-stop reason is `iteration_budget_exhausted`; `unknown` should
   be inspected.

5. `extra_pass_candidate_counts`: count of true, false, and missing candidate
   labels. This is a review queue, not an action queue.

6. `extra_pass_reason_counts` and `extra_pass_blocker_counts`: explain why
   candidates did or did not fire. Useful blocker patterns include
   `evaluator_sufficient`, `no_unresolved_gaps`, `no_next_queries`,
   `query_novelty_low`, `last_pass_low_yield`,
   `weak_corpus_recovery_completed`, `corpus_off_topic`, and
   `cost_state_unavailable`.

7. `extra_pass_query_source_counts` and `extra_pass_budget_class_counts`: show
   whether candidate pressure is coming from source-class recovery, evaluator,
   budget, or other query sources, and whether it is tied to exhausted or
   non-exhausted budget classes.

8. `budget_limited_answer_counts` and
   `budget_limited_answer_reason_counts`: identify answers that were possibly
   limited by budget exhaustion plus unresolved gaps. These are directional and
   must be reviewed against the final answer and source evidence.

9. `unresolved_gap_buckets`: distribution of unresolved gap counts at
   synthesis. Rows with high counts are useful for manual review, but a high
   bucket alone does not prove an extra pass would help.

10. `answer_outcome_counts`: shows whether pressure labels cluster around
    `answered`, `partial_answer`, `no_evidence_found`, `off_topic_retrieval`,
    or `declined_by_policy`. Candidate true plus `answered` can be an overfire
    review candidate; candidate false plus `partial_answer` or
    `no_evidence_found` can be an underfire review candidate.

## Overfire Definitions

An overfire is a case where `extra_pass_candidate_shadow` is true but manual
review suggests an active extra pass would likely have been unnecessary or
harmful.

Examples:

- Candidate true when the final answer already has sufficient official or
  primary evidence for the user-visible claim.
- Candidate true because of a stale source-class expectation that no longer
  matches the query, domain, entity, or answer need.
- Candidate true with missing or unknown last-pass yield and missing or unknown
  query novelty, where the candidate label is not supported by enough
  retrieval-shape evidence.
- Candidate true because quantitative coverage is marked missing even though
  the final answer did not require that target metric or correctly declined to
  estimate it.

Overfire review should ask whether the additional pass would have changed the
answer, source quality, citation coverage, or uncertainty handling. If not, the
candidate should remain shadow-only and should not motivate active behavior.

## Underfire Definitions

An underfire is a case where `extra_pass_candidate_shadow` is false but manual
review suggests an additional retrieval pass might plausibly have improved a
budget-limited answer.

Examples:

- Candidate false because `cost_state_unavailable` blocked the candidate,
  despite clear hard budget exhaustion and an unresolved official evidence gap.
- Candidate false after a low-yield pass even though an available
  source-class query would target primary, official, issuer, polling, or other
  expected evidence that the final answer lacked.
- Candidate false because the evaluator emitted no next queries while
  source-class recovery had viable queries for missing expected source classes.
- Candidate false because the evaluator was marked sufficient, but the final
  outcome was `partial_answer` or `no_evidence_found` with unresolved gaps.

Underfire review should separate actual retrieval opportunities from cases
where no safe, specific, nonredundant query was available.

## Minimum Evidence Before Active Soft-Budget Behavior

Before any active soft-budget or extra-pass behavior is even considered, the
project needs all of the following:

- Multiple reviewed post-27B JSONL rows with valid
  `retrieval_budget_pressure_shadow_v1` payloads.
- Low malformed payload rate across the reviewed window.
- Acceptable manually reviewed overfire and underfire rates for
  `extra_pass_candidate_shadow`.
- Reviewed examples across Fast, Balanced, and Deep modes.
- Explicit positive-control tests where budget exhaustion plus unresolved,
  relevant gaps are detected.
- Explicit negative-control tests for evaluator sufficiency, no unresolved
  gaps, weak-corpus recovery completion, off-topic corpus, redundant queries,
  and cases where the final answer already has sufficient evidence.
- Separate Rule 0 planning for any active behavior.
- Explicit approval for behavior-changing implementation.

Aggregate summaries alone are not enough. SQLite summaries alone are not
enough. One clean run, one domain, or one candidate label is not enough.

## Explicit Non-Authorizations

This note does not authorize:

- Active extra retrieval.
- Soft-budget behavior.
- Provider routing, provider selection, provider suppression, or provider depth
  changes.
- Prompt changes.
- Parser changes, source filtering changes, source ranking changes, or citation
  selection changes.
- Weak-corpus behavior changes.
- Analyst behavior changes.
- Economist behavior changes.
- Author behavior changes.
- SQLite or `RUN_COLUMNS` changes.
- Replay fixture changes.
- Aggregation logic changes.
- Live query requirements.
- Streamlit runs.

Any future behavior-changing proposal must be a separate pass with its own
scope, Rule 0 analysis, tests, replay evidence where applicable, rollback
criteria, and explicit approval.

## Recommended Next Step

After this docs-only note, wait for post-27B JSONL rows that naturally include
`retrieval_budget_pressure_shadow_v1`. If logs already exist and the user
explicitly approves analysis, run targeted offline or replay analysis only
against those logs. Do not run live ProPlex queries or Streamlit for this
calibration step.
