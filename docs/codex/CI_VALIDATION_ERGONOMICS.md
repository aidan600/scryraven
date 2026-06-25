# CI Validation Ergonomics

Status: Codex-visible validation guidance for tiered validation.

Use this file to keep phase prompts compact. Phase prompts should name unusual
validation needs, not restate the standing validation ladder.

For the bucket reference table and promotion rules, read
[VALIDATION_BUCKETS.md](VALIDATION_BUCKETS.md). For new-test classification and
promotion posture, read
[TEST_CLASSIFICATION_LIBRARY.md](TEST_CLASSIFICATION_LIBRARY.md).

## Bucket selection

- Choose the smallest valid bucket.
- Report the exact bucket and command used.
- Ordinary PR test execution targets the fast bucket: `fast_pr` should stay
  under about 3 minutes after dependency setup/cache.
- For PRs, `fast_pr` is the normal target unless the phase explicitly licenses
  `author_lane` or `full`.
- Do not add every new test to `fast_pr`; only true sentinels belong there.
- Do not run full pytest unless the phase requires it.
- Do not respond to timeouts by expanding CI scope or rerunning monolithic
  commands repeatedly. Split the command or report the timeout with the exact
  command and bucket.

## PR validation buckets

- `docs_only` is used for docs/runbooks/prompts/operator-only markdown/text
  changes and runs changed-file pre-commit/diff checks without pytest by
  default.
- `fast_pr` is used for ordinary code pull requests and runs the tiny manifest
  in `tests/buckets/fast_pr.txt`.
- `semantic_lane` is not a default PR bucket. Use it through manual
  `workflow_dispatch` or when a phase explicitly licenses semantic producer,
  reducer, sufficiency, component coverage, or semantic projection validation.
- `semantic_search_lane` is not a default PR bucket. Use it through manual
  `workflow_dispatch` or when a phase explicitly licenses SearchJudgment or
  QueryPlan semantic-gap consumer validation.
- `author_lane` is not a default PR bucket. Use it only through manual
  `workflow_dispatch` or when a phase explicitly licenses it.
- `full` is not a default PR bucket. It is for pushes to `main` and manual
  serious validation.

## Focused phase validation

- Run the phase-specific test file first.
- Run immediate producer/consumer tests next.
- Prefer exact test node IDs or file paths over broad test globs when proving a
  narrow custody change.
- Name this as `phase_focus` in the phase prompt or final bundle.
- When the phase touches durable semantic producer/reducer/sufficiency
  contracts, run `python scripts/validation/run_bucket.py semantic_lane`.
- When the phase touches SearchJudgment or QueryPlan semantic-gap consumption,
  run `python scripts/validation/run_bucket.py semantic_search_lane`.

## Impacted custody slice

- Use when a phase touches a chain such as AC/AD/AE/AF4/AF4B2/AF4C.
- Build the slice from the custody chain and its closest producer/consumer
  tests.
- If a monolithic command times out, split it into smaller chunks.
- Do not rerun the same monolithic timeout repeatedly.

## Full suite

- Run on push to `main`.
- Run via `workflow_dispatch` with `validation_scope=full` when PR check
  visibility is confusing or when a reviewer asks.
- Use `workflow_dispatch` with `validation_scope=fast_pr` to rerun the PR fast
  bucket manually.
- Do not make full-suite pytest the default PR tax.

## Reporting rule

- Distinguish test failure from command timeout.
- Report the exact command, result, timeout if any, and split chunks used.
- Do not broaden runtime implementation just to solve validation ergonomics.
