# Economist Shadow Telemetry Promotion Policy

Status: legacy/superseded Phase 10 policy note retained for compatibility-field
interpretation. Classification: docs-only / policy-only.

This document clarifies the requirements that would have to be satisfied before
any future promotion of Economist shadow telemetry could even be considered. It
does not authorize implementation, does not change current behavior, and does
not create a promotion path by itself. Legacy Economist ordinary execution was
subsequently retired.

## Current Post-Retirement Status

At `7bbfff0f604096e3437bfdadc3dd8b81ec56b57c`, ordinary CLI/backend execution
has no Economist runtime stage, preflight, dependency injection, or execution
callsite. Retained skip-candidate, eligibility, alignment, handoff, and trace
fields are passive legacy compatibility data. They do not represent a dormant
runtime, a feature flag, or a current promotion path.

This note is therefore superseded as a promotion roadmap. Its prohibitions and
evidence cautions remain useful when reading historical traces or directly
testing the isolated legacy implementation. Any proposal to add a future
bounded Specialist must begin as a new separately licensed phase and must not
claim to promote these fields back into an Economist runtime stage.

## Status / Scope

This pass is limited to policy documentation. It makes no source, test, prompt,
routing, retrieval, provider-selection, source-filtering, Analyst, Economist,
Author, telemetry-emission, summarizer, replay, or weak-corpus gate changes.

The current ordinary runtime does not execute the Economist. Retained Economist
shadow telemetry is diagnostic compatibility data only.

## Current Compatibility-Field Policy

All Economist skip candidate, skip eligibility, and alignment fields are
diagnostic only:

- `economist_pre_analyst_skip_candidate_shadow` is diagnostic only.
- `economist_skip_eligible_shadow` is diagnostic only.
- `economist_skip_shadow_alignment` is diagnostic only.

These fields may be logged, summarized, replayed, and reviewed for readiness.
They must not affect runtime control flow, stage ordering, prompt selection,
retrieval behavior, provider selection, source filtering, Analyst behavior,
Economist behavior, Author behavior, summarizer behavior, replay behavior, or
weak-corpus gate behavior.

## Forbidden Current Behavior

The following behavior is forbidden under current policy:

- No Economist-driven Analyst skip.
- No Analyst skip because an Economist packet is valid.
- No direct Economist-to-Author handoff.
- No Economist output as Author-facing analysis.
- No Author access to raw `quantitative_packet`.
- No Author access to raw Economist framework.
- No Author access to raw `economist_v1` JSON.
- No resurrection of raw `QUANTITATIVE FRAMEWORK` handoff.
- No Economist code execution.
- No treating summarizer output as runtime policy.
- No conflating forbidden post-Economist Analyst skip with the separate existing
  weak-corpus retrieval gate.

## Shadow Labels Are Not Authorization

Shadow labels describe observations for offline review. They are not approvals,
feature flags, routing decisions, skip decisions, or policy grants.

Labels such as `candidate_shadow_only`, `eligible_shadow_only`, and
`candidate_and_posthoc_eligible` mean that a diagnostic condition was observed
in shadow telemetry. They do not permit Analyst skip, direct Author handoff, raw
packet/framework/JSON exposure, code execution, or any other runtime behavior
change.

SQLite compact summaries and summarizer readiness output are review aids only.
They must not be treated as runtime policy or as a substitute for full replay
and safety evidence.

## Legacy Hypothetical Promotion Prerequisites

These pre-retirement prerequisites are retained as historical safety context,
not as an approved sequence. They do not provide a current promotion route. Any
separately licensed future proposal would at minimum have to address:

- Multiple clean cross-domain runs.
- Negative controls.
- No marker leaks.
- High-stakes cases blocked.
- Code execution blocked.
- Missing retrieval sufficiency blocked.
- No Author raw packet, raw framework, or raw JSON leaks.
- Stable telemetry fields.
- Stable reason fields.
- Replay evidence.
- Explicit user approval.
- Separate Rule 0 planning.
- Separate behavior-changing implementation approval.

Meeting these prerequisites would only make a future proposal reviewable. It
would not implement, enable, or authorize promotion by itself.

## Disallowed Shortcuts

The following are not enough to justify behavior promotion:

- One clean shadow run.
- One clean domain.
- A valid packet.
- `eligible_shadow_only`.
- `candidate_shadow_only`.
- `candidate_and_posthoc_eligible`.
- Summarizer readiness output alone.
- SQLite compact summaries alone.
- Performance or latency benefit without safety evidence.

No single label, run, summary, or efficiency argument can override the live
shadow-only policy.

## Required Future Test Evidence

Before any future behavior-changing implementation is proposed, the evidence
plan must document and then implement tests for:

- Positive cases.
- Negative controls.
- High-stakes cases.
- Invalid or missing packet cases.
- Author leak cases.
- Replay fixture cases.
- Weak-corpus separation cases.

This document records required future evidence only. It does not add, modify,
or approve tests in this pass.

## Weak-Corpus Gate Separation

The existing weak-corpus retrieval gate is a separate pre-Analyst retrieval and
corpus-quality behavior. It must not be conflated with forbidden
post-Economist Analyst skip.

Economist shadow telemetry must not modify weak-corpus gate inputs, outputs,
thresholds, reason fields, prompts, replay behavior, or routing behavior. A
future policy discussion about Economist telemetry promotion must explicitly
prove that weak-corpus gate behavior remains separate and unchanged unless a
separate approved pass scopes that change.

## Approval And Implementation Requirements

This policy document does not authorize implementation. It does not change
current behavior and does not create a promotion path by itself. There is no
current Economist runtime stage to promote.

Any future behavior change requires explicit approval and a separate
behavior-changing pass. That separate pass must include Rule 0 planning,
implementation approval, a test plan, replay evidence, leak checks,
high-stakes controls, code-execution controls, and weak-corpus separation
checks before any runtime promotion is attempted.

## Checks For This Docs-Only Pass

This docs-only pass should change only this policy document. It should not
change source code, tests, fixtures, prompts, runtime telemetry, replay logic,
or weak-corpus gate behavior.

Expected new telemetry fields: none.
