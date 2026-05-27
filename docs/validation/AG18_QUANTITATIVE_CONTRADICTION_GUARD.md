# AG-18 Quantitative Contradiction Guard

## What became active

AG-18 promotes the existing narrow two-item normalized quantitative consistency
diagnostic from shadow-only detection to a deterministic final-output guard. If
the diagnostic proves that final prose states the opposite calorie-density winner
from the normalized calculation, the final report is replaced before it is
returned or logged as user-facing output.

## Exact scope

The guard applies only when all of these are true:

- `quantitative_consistency_status == "contradiction_detected"`
- exactly two normalized calorie/gram items are available
- computed winner and stated winner are both present and disagree
- normalized values are finite and non-tied

The guard does not apply to correct prose, no detected stated winner, tied
normalized values, non-calorie normalized comparisons, multi-item comparisons,
non-quantitative queries, or source-class recovery cases.

## Streaming boundary

When `author_stream_display` is wired and the query is an exact two-item
calorie/gram comparison candidate, the Author stream is consumed internally
instead of being sent chunk-by-chunk to the UI. The completed answer is then
checked by the deterministic guard before normal return/log/session output.
`RunOutcome.author_streamed` is `False` for this buffered candidate path so the
UI can render the corrected final report through its normal non-streamed display
path. Non-target streaming behavior is unchanged.

## Why no model call is used

The safe correction is fully determined by user-provided figures and arithmetic:
calories divided by grams, then multiplied by 100 for the per-100g view. No
Author, Analyst, Economist, router, retrieval provider, prompt rewrite, or
post-Author LLM correction pass is needed.

## Trace fields

Named consumer: execution-trace review, AG-18 validation, and future bounded live
validation triage.

Decision enabled: reviewers can see whether a contradiction was detected, whether
the guard changed final output, and why a guard did or did not apply.

Fields:

- `quantitative_consistency_guard_applied`
- `quantitative_consistency_guard_reason`
- `quantitative_consistency_guard_output_mode`
- `quantitative_consistency_original_status`
- `quantitative_consistency_guard_final_answer_replaced`

Deletion or promotion criterion: keep the fields while the guard remains narrow
and under validation. If future phases broaden quantitative guards, promote the
fields into a shared quantitative final-output guard telemetry contract or remove
them after equivalent replacement telemetry exists.

Validation tests:

- `tests/test_ag18_quantitative_contradiction_guard.py`
  - contradictory streamed candidate is buffered and returns/logs corrected text
  - correct streamed candidate is buffered and remains unchanged
  - non-quantitative streaming continues to use the raw stream callback
- existing AG-15 quantitative consistency diagnostics
- AG-17 recovered-evidence visibility tests
- source-class recovery, weak-corpus, retrieval-stop, answer-contract runtime,
  calculations, pre-analyst, and Economist safety suites

## Protected surfaces preserved

AG-18 does not change source-class recovery behavior, recovered evidence
visibility, provider routing, provider selection, retrieval depth, source
ranking/filtering, prompt semantics, persistence schema, Economist code
execution, Analyst/Economist/Author handoff, or raw quantitative packet exposure.

## AG-19 recommendation

AG-19 should be bounded live validation of recovered-evidence visibility with
rotated queries, while keeping quantitative contradiction validation offline
unless a separate live budget is approved.
