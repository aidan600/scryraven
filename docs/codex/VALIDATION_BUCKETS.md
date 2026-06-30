# Validation Buckets

Status: Codex-visible reference for choosing validation scope.

ScryRaven validation is tiered so ordinary pull requests stay fast while
high-custody phases can still request broader proof explicitly. Choose the
smallest bucket that can prove the current change.

Use [TEST_CLASSIFICATION_LIBRARY.md](TEST_CLASSIFICATION_LIBRARY.md) when a phase
adds, promotes, demotes, or retires tests.

| Bucket | Use when | Contents | Default routing |
| --- | --- | --- | --- |
| `docs_only` | Docs, runbooks, prompts, or operator-only markdown/text changed, with no code, test, manifest, script, or workflow changes. | Changed-file pre-commit and diff checks. No pytest by default. | Pull requests only when changed files are documentation/operator-only. |
| `fast_pr` | Ordinary code PR validation. | Tiny sentinel set from `tests/buckets/fast_pr.txt`; target under about 3 minutes after dependency setup/cache. It is not the full Author lane. | Default pull-request bucket for non-docs-only changes. |
| `phase_focus` | Local/Codex phase-specific proof. | The current phase test plus immediate producer/consumer tests chosen by the phase prompt. | Not a GitHub default bucket. Run locally with exact pytest node IDs or paths. |
| `semantic_lane` | Semantic producer, semantic reducer, semantic sufficiency, component coverage, and semantic projection validation. | Durable semantic manifest in `tests/buckets/semantic_lane.txt`, including AG-SEM reducer contracts, semantic sufficiency consumption, ordinary semantic producer atomicity, and structural guards. | Manual `workflow_dispatch` or explicitly phase-licensed validation only. Not a default PR bucket. |
| `semantic_search_lane` | SearchJudgment and QueryPlan consumers of semantic missing assessments and semantic component gaps. | Durable semantic-search manifest in `tests/buckets/semantic_search_lane.txt`, including AG-GAP, SearchJudgment, and QueryPlan semantic-gap consumer tests. | Manual `workflow_dispatch` or explicitly phase-licensed validation only. Not a default PR bucket. |
| `author_lane` | Comprehensive Author-lane custody validation. | `tests/buckets/author_lane.txt`, including the former inline AF/U/V/W/X/Y/Z/AC/AD/AE/AF4/AF5 custody set and adjacent RunKernel/final-answer files. | Manual `workflow_dispatch` or explicitly phase-licensed validation only. |
| `full` | Complete offline suite. | `python -m pytest -q` using the configured tracked test root. Generated outputs, local review mirrors, caches, logs, secrets, and other local artifacts must not be collected. | Push to `main` and manual serious validation only. |

`semantic_lane` and `semantic_search_lane` are not default `fast_pr` scope because
they are domain validation sweeps, not tiny broad sentinels. Run them when a
phase changes semantic record construction, ordinary semantic producer handoff,
semantic sufficiency consumption, ledger-qualified coverage integrity,
SearchJudgment consumption of semantic missing assessments, or QueryPlan handling
of semantic component gaps. `fast_pr` remains the ordinary PR tax.

Run `author_lane` when a phase touches FinalAnswerPacket, Author payload, Author
prompt/materialization, Author invocation/execution, citation handoff, or final
response behavior. This lane is high-custody and comparatively expensive; it is
not default PR tax. Run `full` for push-to-main, manual serious validation, or a
phase that explicitly needs the complete offline suite.

## Generated-output Collection Hygiene

`full` is an offline tracked-test sweep, not a request to collect generated local
artifacts. Root pytest collection should be constrained by repo test configuration
to `tests/`; generated directories such as `output/`, `local_output/`,
`local_outputs/`, `cache/`, `caches/`, `logs/`, `private_logs/`, `secrets/`, and
`output/local_review/` are not validation inputs and must not be committed or
collected.

The validation bucket runner also disables python-dotenv for its pytest
subprocesses so local `.env` files are not read during offline collection. The
runner uses ignored `.pytest_cache/basetemp/<bucket>` storage as pytest basetemp
by default; set `SCRYRAVEN_PYTEST_BASETEMP` to override that for a local
environment.

If root collection starts walking those directories, fix the collection route or
report the blocker. Do not delete user output directories to make validation
pass.

## AG-BAL / AG-BAL-HARDEN Routing

AG-BAL recovery proof is intentionally split by invariant:

- `semantic_search_lane` owns the durable offline product-path recovery sentinel
  for QueryPlan/SearchJudgment authorization and one-cycle recovery budget
  containment.
- `author_lane` owns the recovered factual text and recovered source identity
  reaching FinalAnswerPacket-owned Author material after semantic coverage
  succeeds.

Keep additional AG-BAL-HARDEN phase-detail tests in `phase_focus` unless they
become cheap durable sentinels with a clear owner and cost posture.

## Required New-Test Classification

Adding a test requires stating whether it is `phase_focus`, a `fast_pr` sentinel
candidate, `semantic_lane`, `semantic_search_lane`, `author_lane`, or full-only
before adding it to any permanent bucket manifest.

New tests start as `phase_focus` unless explicitly justified otherwise. Use the
required fields in [TEST_CLASSIFICATION_LIBRARY.md](TEST_CLASSIFICATION_LIBRARY.md),
including the proof class, surface guarded, high-custody or closed-this-phase
surface if any, runtime/product path guarded, expected cost, promotion posture,
demotion or retirement condition, and why the test is or is not a `fast_pr`
candidate.

## Required Validation Reporting Fields

Phase validation summaries must state:

- proof class;
- product-facing progress type;
- actual consumer seam;
- actual user-facing app delta;
- user-facing/reviewable output delta;
- non-product exception leash, when applicable;
- mandatory next product-path checkpoint, when applicable;
- existing machinery reused;
- new machinery introduced;
- why the work is not reinventing an existing surface;
- old path treatment;
- explicit non-proofs;
- whether the output is human-reviewable product output or structural proof only;
- whether live validation was run;
- whether live validation was prohibited, not licensed, or separately licensed.

For current-path and quarantine work, use
`docs/architecture/AG_CURRENT_PATH_QUARANTINE_01.md` to classify surfaces as
current internal authority path, current product-consumed path,
passive/supporting projection, fixture-only proof, offline harness,
integration-staging harness, product-facing dry-run proof, legacy/passive/
historical, historical/proof-only debt, or closed-this-phase unless explicitly
licensed.

Do not add a test to `fast_pr` merely because the phase added it. A promoted
`fast_pr` entry must be a cheap broad sentinel, not a phase-detail test.

## Promotion Rules

- New tests do not automatically enter `fast_pr`.
- `fast_pr` only gets true sentinels: cheap tests that prove a broad contract
  boundary would catch a serious regression.
- Detailed custody or domain tests belong in their domain bucket, such as
  `semantic_lane`, `semantic_search_lane`, or `author_lane`, or in a
  phase-specific local command.
- Phase prompts must name the validation tier they require.
- Full-suite pytest is not the default PR tax.
- For PRs, `fast_pr` is the normal non-docs target unless the phase explicitly
  licenses `author_lane` or `full`.

## Current `fast_pr` Sentinels

The manifest has four entries:

- `tests/test_run_kernel_ag91h.py::test_run_kernel_start_creates_run_state_with_request_identity`
  keeps a minimal RunKernel authority/start-state sentinel.
- `tests/test_final_answer_author_runkernel_ag91k.py::test_run_kernel_authorizes_and_reduces_final_answer_packet_preparation`
  proves the final-answer/Author authority path without running the wider Author
  custody chain.
- `tests/test_ag96i3af5c_offline_author_lane_e2e_smoke.py::test_af5c_offline_author_lane_e2e_smoke_exposes_final_answer_output`
  keeps one offline Author-lane end-to-end smoke proof.
- `tests/test_ag96i3af6a_broker_alignment.py::test_af6a_fake_mode_has_sanitized_output_without_model_call_budget`
  keeps one cheap broker-alignment fake/deferred sentinel with no live model
  budget.

## Commands

```powershell
python scripts/validation/run_bucket.py fast_pr
python scripts/validation/run_bucket.py semantic_lane
python scripts/validation/run_bucket.py semantic_search_lane
python scripts/validation/run_bucket.py author_lane --collect-only
python scripts/validation/run_bucket.py full
```
