# CI Validation Ergonomics

Status: Codex-visible validation guidance for high-custody phases.

Use this file to keep phase prompts compact. Phase prompts should name unusual
validation needs, not restate the standing validation ladder.

## PR fast custody lane

- Used for `pull_request` events.
- Intended to prove representative high-custody seams quickly.
- Not the full suite.
- Kept in `.github/workflows/ci.yml` so review PRs get a predictable visible
  check.

## Focused phase validation

- Run the phase-specific test file first.
- Run immediate producer/consumer tests next.
- Prefer exact test node IDs or file paths over broad test globs when proving a
  narrow custody change.

## Impacted custody slice

- Use when a phase touches a chain such as AC/AD/AE/AF4/AF4B2/AF4C.
- Build the slice from the custody chain and its closest producer/consumer
  tests.
- If a monolithic command times out, split it into smaller chunks.
- Do not rerun the same monolithic timeout repeatedly.

## Full suite

- Run near the end locally when feasible.
- Run on push to `main`.
- Run via `workflow_dispatch` with `validation_scope=full` when PR check
  visibility is confusing or when a reviewer asks.
- Use `workflow_dispatch` with `validation_scope=fast` to rerun the PR fast
  custody lane manually.

## Reporting rule

- Distinguish test failure from command timeout.
- Report the exact command, result, timeout if any, and split chunks used.
- Do not broaden runtime implementation just to solve validation ergonomics.
