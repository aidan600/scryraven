# Validation Buckets

Status: Codex-visible reference for choosing validation scope.

ScryRaven validation is tiered so ordinary pull requests stay fast while
high-custody phases can still request broader proof explicitly. Choose the
smallest bucket that can prove the current change.

Use [TEST_CLASSIFICATION_LIBRARY.md](TEST_CLASSIFICATION_LIBRARY.md) when a
phase adds, promotes, demotes, or retires tests.

| Bucket | Use when | Contents | Default routing |
| --- | --- | --- | --- |
| `docs_only` | Docs, runbooks, prompts, or operator-only markdown/text changed, with no code, test, manifest, script, or workflow changes. | Changed-file pre-commit and diff checks. No pytest by default. | Pull requests only when changed files are documentation/operator-only. |
| `fast_pr` | Ordinary code PR validation. | Tiny sentinel set from `tests/buckets/fast_pr.txt`; target under about 3 minutes after dependency setup/cache. It is not the full Author lane. | Default pull-request bucket for non-docs-only changes. |
| `phase_focus` | Local/Codex phase-specific proof. | The current phase test plus immediate producer/consumer tests chosen by the phase prompt. | Not a GitHub default bucket. Run locally with exact pytest node IDs or paths. |
| `author_lane` | Comprehensive Author-lane custody validation. | `tests/buckets/author_lane.txt`, including the former inline AF/U/V/W/X/Y/Z/AC/AD/AE/AF4/AF5 custody set and adjacent RunKernel/final-answer files. | Manual `workflow_dispatch` or explicitly phase-licensed validation only. |
| `full` | Complete offline suite. | `python -m pytest -q` across the repo. | Push to `main` and manual serious validation only. |

## Required New-Test Classification

Adding a test requires stating whether it is `phase_focus`, a `fast_pr`
sentinel candidate, `author_lane`, or full-only before adding it to any
permanent bucket manifest.

New tests start as `phase_focus` unless explicitly justified otherwise. Use the
required fields in
[TEST_CLASSIFICATION_LIBRARY.md](TEST_CLASSIFICATION_LIBRARY.md), including the
proof class, protected surface, runtime/product path guarded, expected cost,
promotion posture, demotion or retirement condition, and why the test is or is
not a `fast_pr` candidate.

Do not add a test to `fast_pr` merely because the phase added it. A promoted
`fast_pr` entry must be a cheap broad sentinel, not a phase-detail test.

## Promotion Rules

- New tests do not automatically enter `fast_pr`.
- `fast_pr` only gets true sentinels: cheap tests that prove a broad contract
  boundary would catch a serious regression.
- Detailed custody tests belong in their domain bucket, such as `author_lane`,
  or in a phase-specific local command.
- Phase prompts must name the validation tier they require.
- Full-suite pytest is not the default PR tax.
- For PRs, `fast_pr` is the normal non-docs target unless the phase explicitly
  licenses `author_lane` or `full`.

## Current `fast_pr` Sentinels

The manifest has four entries:

- `tests/test_run_kernel_ag91h.py::test_run_kernel_start_creates_run_state_with_request_identity`
  keeps a minimal RunKernel authority/start-state sentinel.
- `tests/test_final_answer_author_runkernel_ag91k.py::test_run_kernel_authorizes_and_reduces_final_answer_packet_preparation`
  proves the final-answer/Author authority path without running the wider
  Author custody chain.
- `tests/test_ag96i3af5c_offline_author_lane_e2e_smoke.py::test_af5c_offline_author_lane_e2e_smoke_exposes_final_answer_output`
  keeps one offline Author-lane end-to-end smoke proof.
- `tests/test_ag96i3af6a_broker_alignment.py::test_af6a_fake_mode_has_sanitized_output_without_model_call_budget`
  keeps one cheap broker-alignment fake/deferred sentinel with no live model
  budget.

## Commands

```powershell
python scripts/validation/run_bucket.py fast_pr
python scripts/validation/run_bucket.py author_lane --collect-only
python scripts/validation/run_bucket.py full
```
