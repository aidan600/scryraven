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
| `fast_pr` | Ordinary code PR validation. | Full-suite collection guard followed by the tiny execution-sentinel set from `tests/buckets/fast_pr.txt`; target under about 3 minutes after dependency setup/cache. It collects, but does not execute, the full suite and is not the full Author lane. | Default pull-request bucket for non-docs-only changes. |
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

In short: `fast_pr = full-suite collection guard + tiny execution sentinels`.
The guard prevents missing imports and other collection failures outside the
tiny manifest from passing ordinary PR validation without adding full-suite
execution to that bucket.

Run `author_lane` when a phase touches FinalAnswerPacket, Author payload, Author
prompt/materialization, Author invocation/execution, citation handoff, or final
response behavior. This lane is high-custody and comparatively expensive; it is
not default PR tax. Run `full` for push-to-main, manual serious validation, or a
phase that explicitly needs the complete offline suite.

## Validation consequence classes

Every expensive validation item named by a phase brief or final bundle must use
exactly one consequence class:

```text
HANDOFF_GATE
MERGE_GATE
DIAGNOSTIC_ONLY
```

`HANDOFF_GATE` must complete before Codex returns its final bundle. It should
normally be local, focused, deterministic prepublication proof. Hosted
asynchronous CI must not be classified as a handoff gate.

`MERGE_GATE` must reach its required conclusion before the maintainer merges,
but it may remain pending when Codex returns. Normal exact-head PR CI is a merge
gate unless the phase states otherwise. Strategy/Review, not a waiting Codex
task, owns later inspection.

`DIAGNOSTIC_ONLY` records repository health, timing, attribution, or exploratory
evidence. It blocks neither handoff nor merge unless later review attributes the
result to the candidate under an already stated causal rule; it must not
silently expand the active phase.

A candidate-only broad run against a known-red or unattributed baseline is not
automatically a merge gate merely because it is red. It may be a merge gate only
when the phase defines paired baseline/candidate attribution or an exact
branch-attributable causal rule tied to the licensed changed surface. Silence,
elapsed time, a pending status, or the absence of a visible workflow record
proves nothing.

For each expensive check, report:

```text
Check:
Command or workflow:
Classification:
Decision it makes:
Required terminal state:
Inspection owner:
```

## Review-Loop Validation Ramp

Move expensive proof to the point where it answers a decision instead of
repeating it throughout the inner loop. This ramp is intended to reduce repeated
lane execution and hosted-CI churn, especially across several narrow review
corrections; it does not weaken final-candidate proof.

### 1. Implementation or narrow review continuation

While work is still changing, run the newly failing reproduction and the exact
node IDs or phase-focus test file owned by the correction. Add immediate
producer/consumer tests only when the change crosses that seam. Run targeted
Ruff, compile, formatting, or equivalent checks only for changed executable
files, and changed-file documentation checks for changed docs.

Do not normally run durable lanes, full or partitioned pytest,
`pre-commit --all-files`, hosted exact-head CI, unrelated documentation guards,
or the entire original phase validation bundle in this loop. A review verdict B
defaults to this narrow posture. Repeat broader validation only when the
correction changes the proof boundary or another runtime owner, invalidates
earlier evidence, or the reviewer explicitly declares a new final candidate.

### 2. Coherent implementation checkpoint

After the causal runtime/test cluster is complete but before final publication,
run the full `phase_focus` proof, immediate owning producer/consumer tests, and
targeted static checks. Review the complete branch diff for neighboring failures
and resolve known blockers before paying final-candidate validation cost. Do not
automatically run every durable lane at this checkpoint.

### 3. Final PR candidate

Once, after all known implementation and review blockers are closed, run:

- `fast_pr` for an ordinary non-docs PR;
- only the durable lane or lanes directly affected by changed authority;
- applicable documentation guards;
- `pre-commit --all-files` when appropriate for a runtime PR;
- applicable local handoff gates;
- exact-head hosted CI as a merge gate after publication; and
- a final complete-diff review.

Route FinalAnswerPacket, Author, accepted prose, or response-finalization changes
to `author_lane`; semantic production, reduction, component coverage, or semantic
sufficiency changes to `semantic_lane`; and SearchJudgment or QueryPlan
semantic-gap consumption to `semantic_search_lane`. Docs-only workflow changes
have no runtime lane by default. Selecting multiple durable lanes requires an
explicit reason tied to changed authority; topic proximity is insufficient.

### Docs-only posture

A true docs-only PR normally runs changed-file pre-commit hooks, applicable
documentation/link/structure checks, diff checks, and ordinary hosted CI after
publication. It does not run runtime pytest buckets merely because the docs
describe a high-custody runtime surface. A PR is no longer docs-only when it
changes tests, manifests, scripts, workflows, executable configuration, or
generated runtime artifacts.

### Parser and syntax-matrix posture

Keep exhaustive syntax or input-shape matrices at the lowest deterministic owner
that can prove classification. Production consumers should use a small,
representative sentinel set proving that they call the shared validator and
handle acceptance or rejection correctly. Do not automatically multiply every
syntax permutation across every consumer. This policy does not require existing
tests to be deleted or restructured.

### Duplicate execution and exceptional validation

When selected buckets overlap, avoid knowingly executing the same test node
repeatedly. Use a deduplicated union when existing tooling supports it; otherwise
report the overlap and justify the separate processes. This policy does not add
a union runner or change the current runner.

Full-suite validation is not ordinary PR tax, and partitioned broad validation
is exceptional. Either requires explicit phase or reviewer authorization and a
stated decision the run will make. Do not add broad validation to a narrow review
continuation merely for reassurance.

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

For validation routing, read
`docs/architecture/SCRYRAVEN_CURRENT_STATE.md` for current installed state and
`docs/codex/PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md` for proof/product-delta
classification. Read `docs/roadmap/CURRENT_ROADMAP.md` only when phase sequence
matters. `docs/architecture/AG_CURRENT_PATH_QUARANTINE_01.md` is routed support
for its narrow quarantine classifications, not the broad current product-status
owner.

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

The manifest has five entries:

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
- `tests/test_initial_discovery_selective_fetch_retirement_01.py::test_ordinary_discovery_has_a_durable_no_exact_url_transport_boundary`
  prevents canonical `core`/`proplex` modules from regaining direct source-URL
  transport, pins provider HTTP calls to DISCOVER endpoints, and preserves the
  RunKernel pre-transport claim around the sole exact-URL dispatcher.

## Commands

```powershell
python scripts/validation/run_bucket.py fast_pr
python scripts/validation/run_bucket.py semantic_lane
python scripts/validation/run_bucket.py semantic_search_lane
python scripts/validation/run_bucket.py author_lane --collect-only
python scripts/validation/run_bucket.py full
```

## Exceptional partitioned broad validation

`scripts/validation/run_bucket.py` remains the bucket-selection authority.
When a separately authorized candidate-only broad-validation job risks a
monolithic outer timeout, use its partitioned full delegation rather than
adding another bucket or expanding ordinary pull-request validation:

```powershell
python scripts/validation/run_bucket.py full --partitioned --partitions 4 --max-processes 2
```

In partitioned mode, omitted numeric options default to 4 partitions and 2
maximum processes. The bucket runner delegates with the current Python
executable, explicit repository root, and `--candidate HEAD`; it does not own or
reimplement partitioning, worktrees, aggregation, cleanup, timeouts,
attribution, or artifact packets. Ordinary `run_bucket.py full` stays serial.

Use candidate-only mode when the candidate must be green independently. Invoke
the existing partitioned runner directly for paired parity when failures need
baseline attribution:

```powershell
py scripts\validation\run_partitioned_pytest.py --baseline <BASE_SHA> --candidate <CANDIDATE_SHA> --partitions 4 --max-processes 2
```

The runner discovers tracked `tests/test*.py` files from each exact Git tree,
partitions their sorted union by stable round robin, and filters each union
partition for the corresponding ref. A candidate test removal fails closed.
Reviewers may authorize only an exact path, repeatably, for example
`--allow-removed-test tests\test_retired_contract.py`; authorized removals
remain visible in the packet.

This is exceptional offline developer validation. Ordinary PRs remain on
`docs_only` or `fast_pr`; `fast_pr` membership and cost are unchanged. The new
runner's directly owning tests are `phase_focus`, not `fast_pr` sentinels.
