# Estimate From Priors Branch Ordering

Status: Repo-local documentation only. This note is not an active Project
Source, not runtime policy, and not authorization for behavior changes.

## Current Observed Behavior

`ESTIMATE_FROM_PRIORS` is a live, forceable corpus state. It is defined as a
`CorpusState` value, can be selected through the forced corpus-state path, and
has active prompt keys for both `analyst_estimate_from_priors` and
`author_estimate_from_priors`.

Current branch ordering treats `ESTIMATE_FROM_PRIORS` as weak corpus. Because it
is included in the weak-corpus state set, the pre-Analyst weak-corpus gate runs
before the later `analyst_estimate_from_priors` branch can execute. In the
current orchestrator path, Analyst estimate-from-priors is therefore
unreachable.

Author estimate-from-priors can still be selected after the pre-Analyst gate.
That creates the current behavior shape: Analyst estimate-from-priors is blocked,
while Author estimate-from-priors may be used alongside an unsupported-retrieval
directive.

## Why This Matters

The UI and product surface may imply that allowing estimate-from-priors will
produce estimate behavior. Today, the cost is lower because no Analyst
estimate-from-priors model call runs. That may be desirable from a spend-control
perspective, but it can reduce product utility for sparse, non-high-stakes
quantitative comparisons where a carefully labeled estimate might be useful.

The unreachable Analyst prompt branch is also a maintenance risk. Prompt text,
handoff expectations, and tests can drift when a branch exists but is not
exercised by the orchestrator.

## Safety Boundaries

This note does not authorize changing runtime behavior. In particular:

- Do not make `ESTIMATE_FROM_PRIORS` globally non-weak from this note.
- Do not bypass weak-corpus gating.
- Do not enable Economist from `ESTIMATE_FROM_PRIORS` without separate approval.
- Do not enable Analyst skip from Economist output.
- Do not pass raw `quantitative_packet`, raw Economist framework, or raw
  `economist_v1` JSON to Author.
- Do not weaken high-stakes guards.

## Current Test Anchor

Current branch ordering is pinned by:

- `test_estimate_from_priors_currently_hits_pre_analyst_weak_gate_before_estimate_analyst`

That test records the current evidence as behavior, not as authorization to make
estimate-from-priors reachable.

## Useful Telemetry

Existing fields useful for branch-order review include:

- `corpus_state`
- `corpus_state_forced`
- `corpus_weak`
- `analyst_skipped`
- `analyst_skip_reason`
- `post_retrieval_fast_path_used`
- `analyst_model_called`
- `economist_ran`
- `author_quant_content_source`
- Author raw-marker tripwires:
  - `author_received_raw_quant_packet`
  - `author_received_economist_framework`
  - `author_received_analyst_packet_marker`

## Telemetry Gaps For Future Review

Future diagnostics-only work could make the branch path easier to audit by
adding fields such as:

- `author_system_prompt_key`
- `estimate_from_priors_requested`
- `estimate_from_priors_blocked_by_pre_analyst_gate`

These would be diagnostics only unless a separate behavior-changing pass is
approved.

## Future Work Categories

- no-change: keep current branch ordering and test anchor unchanged.
- docs-only: clarify current behavior in repo-local notes or future approved
  Project Source refreshes.
- test-only: add focused coverage for current Author prompt selection, no raw
  handoff, or continued Analyst EFP unreachability.
- diagnostics-only: add explicit trace fields for requested EFP path, blocking
  reason, and selected Author system key.
- behavior-risk Review Lane implementation: consider any reachability change
  only through a separate Review Lane pass with Rule 0 planning, positive and
  negative controls, high-stakes controls, raw-handoff leak checks, and explicit
  approval.

## Explicit Non-Authorization

This note does not authorize any runtime, prompt, routing, retrieval,
weak-corpus, Analyst, Economist, Author, telemetry, SQLite, JSONL, replay, or
summarizer changes.
