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
- Do not add every new test to `fast_pr`; only true execution sentinels belong
  in its manifest.
- Do not run full pytest unless the phase requires it.
- Do not respond to timeouts by expanding CI scope or rerunning monolithic
  commands repeatedly. Split the command or report the timeout with the exact
  command and bucket.

## PR validation buckets

- `docs_only` is used for docs/runbooks/prompts/operator-only markdown/text
  changes and runs changed-file pre-commit/diff checks without pytest by
  default.
- `fast_pr` is used for ordinary code pull requests. It first performs a
  full-suite collection guard, then executes the tiny execution-sentinel
  manifest in `tests/buckets/fast_pr.txt`. The full suite is collected but not
  executed.
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

## Consequence and hosted-CI posture

Classify every expensive check as `HANDOFF_GATE`, `MERGE_GATE`, or
`DIAGNOSTIC_ONLY` using [VALIDATION_BUCKETS.md](VALIDATION_BUCKETS.md). Local
focused deterministic proof is the normal handoff gate. Hosted asynchronous CI
is never a handoff gate; normal exact-head PR CI is a merge gate and may remain
pending when Codex returns its final bundle.

After publication, take exactly one hosted-CI status snapshot and return
immediately. Record the exact PR head, timestamp, current status, and workflow
run ID if already visible; otherwise record `run not yet visible in the single
authorized snapshot`. Do not wait, sleep, poll again, use `gh run watch`, chase
status by rewriting the PR, or dispatch duplicate workflows. Strategy/Review
owns later inspection.

A separately dispatched hosted `full` run is unauthorized by default. An
explicitly licensed dispatch must be classified separately as `MERGE_GATE` or
`DIAGNOSTIC_ONLY`. Candidate-only known-red or unattributed broad validation is
not automatically a merge gate; require paired baseline/candidate attribution
or an exact branch-attributable causal rule tied to the licensed changed
surface.

## Partitioned broad-validation runner

For separately authorized exceptional broad validation, use
`scripts/validation/run_partitioned_pytest.py` instead of repeatedly retrying a
known monolithic timeout. Candidate-only mode is the cheaper choice when the
candidate must be independently green. Paired baseline/candidate parity is
more expensive and is reserved for cases where shared, baseline-only, and
candidate-only attribution is needed.

The runner distinguishes candidate regression from infrastructure-invalid
execution. A timeout, invalid pytest process, failed import-isolation probe,
malformed required artifact, or exact-path cleanup failure is neither green nor
red; it requires a valid rerun or infrastructure repair outside the semantic
verdict.

For candidate-only partitioned full validation, use the canonical wrapper:

```powershell
python scripts/validation/run_bucket.py full --partitioned
```

This defaults to 4 partitions and 2 maximum processes and delegates to the
existing partitioned runner with `--repository <repo-root> --candidate HEAD`.
Use `scripts/validation/run_partitioned_pytest.py` directly for paired
baseline/candidate parity and advanced runner options.

Ordinary PR routing remains unchanged: PRs use `docs_only` or `fast_pr`, and
full/parity validation is not a pull-request default. CI adoption of the local
partitioned runner is deferred until one separately authorized real broad-run
dogfood records duration, process validity, attribution usefulness, cleanup
reliability, and compute overhead.

## Reporting rule

- Distinguish test failure from command timeout.
- Report the exact command, result, timeout if any, and split chunks used.
- Do not broaden runtime implementation just to solve validation ergonomics.
