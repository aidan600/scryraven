# AG-DOC-TEST-SANITY-01 Validation Audit

Status: Compact repo-visible audit for Codex guidance and validation-lane
sanitation.

## Purpose

This sanitation pass refreshed Codex routing guidance after PR #299 /
AG-BAL-HARDEN and checked validation-lane shape without changing product
runtime behavior.

Branch: `codex/ag-doc-test-sanity-01-codex-guidance-validation-audit`
Baseline: `3f412751ac85ae55e68e362c592fab70839d7f84`

## Bucket Snapshot

| Bucket | Manifest entries | Collected tests | Posture |
| --- | ---: | ---: | --- |
| `fast_pr` | 4 | 4 | Tiny PR sentinel set; no AG-BAL-HARDEN promotion made. |
| `semantic_lane` | 8 | 137 | Durable semantic producer/reducer/sufficiency lane. |
| `semantic_search_lane` | 4 | 50 | Includes the durable AG-BAL recovery product-path sentinel. |
| `author_lane` | 41 | 144 | High-custody Author lane; intentionally expensive and not PR default. |

AG-BAL-HARDEN routing is correctly split:

- `semantic_search_lane` owns QueryPlan/SearchJudgment recovery authorization,
  one-cycle/idempotency containment, and poisoned-adapter hardening checks.
- `author_lane` owns the recovered fact/source identity reaching
  FinalAnswerPacket-owned Author material.

No bucket promotions, demotions, or new lanes were made. No duplicate manifest
entries were found in the audited buckets.

## Collection Hygiene

Pre-change local full collection could walk generated/private-style top-level
directories such as `output`, `local_output`, `cache`, `logs`, `private_logs`,
and `secrets`, and the local `py` launcher was blocked before Python startup.

Post-change:

- `pytest.ini` constrains root collection to `tests/` and excludes generated,
  cache, log, secret, local-output, and local-review directories.
- `scripts/validation/run_bucket.py` disables python-dotenv for pytest
  subprocesses so `.env` is not read during offline collection.
- `scripts/validation/run_bucket.py` uses ignored
  `.pytest_cache/basetemp/<bucket>` storage by default, avoiding local
  access-denied temp roots.
- `full --collect-only` reports `forbidden_path_match_count=0`.

## Commands

Final commands used the cached Python 3.11.9 runtime with
`.venv\Lib\site-packages` on `PYTHONPATH` because local `py` points at an
access-denied Store Python 3.13 executable.

| Command | Result |
| --- | --- |
| `git diff --check` | Pass; line-ending warnings only. |
| `py scripts\validation\run_bucket.py fast_pr` | Blocked before repo code: Store Python access denied. |
| `python scripts\validation\run_bucket.py fast_pr` equivalent | Pass: 4 passed in 6.94s. |
| `python scripts\validation\run_bucket.py semantic_lane --collect-only` equivalent | Pass: 137 collected in 1.16s. |
| `python scripts\validation\run_bucket.py semantic_search_lane --collect-only` equivalent | Pass: 50 collected in 0.50s. |
| `python scripts\validation\run_bucket.py author_lane --collect-only` equivalent | Pass: 144 collected in 1.67s. |
| `python scripts\validation\run_bucket.py full --collect-only` equivalent | Pass: 4635/4636 collected, 1 deselected, forbidden path matches 0, in 1.64s. |
| `python scripts\validation\run_bucket.py semantic_search_lane` equivalent | Pass: 50 passed in 3.18s. |
| `pre-commit run --files ...` | Pass with `PRE_COMMIT_HOME=.pytest_cache\pre-commit`; default user cache was read-only. |

## Recommendations

- Keep `fast_pr` tiny; do not promote AG-BAL-HARDEN detail tests into ordinary
  PR tax without a new broad, cheap sentinel rationale.
- Keep one durable AG-BAL recovery product-path sentinel in
  `semantic_search_lane`.
- Keep one recovered fact/source Author-materialization sentinel in
  `author_lane`; call out that the lane is high-custody and costly.
- Use phase prompts to name proof class, opened/closed surfaces, exact bucket
  command, exact phase-focus tests, whether full offline is required, and what
  is intentionally not run.
- AG-LIVE-BOUND-01 can proceed from a repo-doc/test-routing standpoint; live
  provider/model/search/fetch validation remains closed until explicitly scoped.

Known limitation: this pass did not execute the full offline suite and did not
repair pre-existing full-suite behavioral failures.
