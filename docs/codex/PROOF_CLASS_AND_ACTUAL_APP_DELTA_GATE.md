# Proof Class and Actual App Delta Gate

Status: Codex-facing implementation guardrail.
Use when: drafting Codex phase briefs, implementing authority/custody/semantic/provider/Author phases, reviewing final bundles, or distinguishing product-path work from component harness work.

## Purpose

ScryRaven phases must not claim more than they prove.

A component harness can prove a seam, but it does not improve the product until
the ordinary runtime consumes that seam.

This document makes the proof class and actual product delta explicit before
implementation starts and again in the final bundle.

## Phase Mode Gate

Build / Proof / Repair is the active phase operating system. Every phase must
declare exactly one delivery intent:

```text
Mode: BUILD | PROOF | REPAIR
```

"Prove Mode" is retired as a global workflow label. Proof is only a phase mode
under Build / Proof / Repair, and it is an exception with a leash, non-claims, a
named blocker, and a mandatory next Build/product checkpoint.

Phase mode is delivery intent: whether the phase is building product-path answer
flow, proving a bounded technical question, or repairing an integrity defect.
Proof class is evidence type: what kind of validation the phase can honestly
claim. Both must be stated because a strong proof class can still be non-product
work until a Build phase consumes it.

BUILD is the default mode. Its purpose is to move ScryRaven closer to answering
real user questions, and its usable-answer verdict must be YES. Definition of
done requires a user-style input, local command, API path, app path, or
reviewable answer artifact that did not exist before. Valid Build outputs
include ordinary-query dry-run output, reviewable AuthorProse answer packets,
CLI/app-visible answer output, source/citation behavior that affects answer
output, product-path repair that makes user-answer flow more honest, or deletion
or quarantine of a legacy path blocking answer flow. A BUILD phase may be larger
than one seam when that is the smallest useful vertical slice. New packets,
registries, doctrine, proofs, fixture-only proofs, or refactors are not valid as
sole Build outputs unless they move a user query closer to answer text through a
runtime consumer.

PROOF mode is an explicit exception. Its purpose is to reduce uncertainty before
a Build phase, and its usable-answer verdict must be NO-BUT-JUSTIFIED. A Proof
phase must answer a named technical question, explain why Build mode cannot
happen first, set an exact timebox/scope cap, state what product decision it
unlocks, state what cannot be claimed, identify throwaway/fixture-only/proof-only
code, and name a mandatory next Build phase. No second Proof phase for the same
blocker is allowed without explicit user approval. A PROOF phase must not be
described as forward product progress unless and until a Build phase consumes it.

REPAIR mode fixes an integrity defect in an existing product-moving path or in
the operating system that governs product-moving work. The usable-answer verdict
must be YES when the repair restores or improves product-path behavior. For
repo-doc/process repair only, the verdict may be NO-BUT-JUSTIFIED, but the phase
must name the product-moving failure it prevents and the next Build/product
checkpoint it protects. Definition of done requires removing the defect, adding a
regression guard when practical, making the product-moving path or operating
system more honest, and avoiding broad cleanup or new architecture.

Universal review question: did this make ScryRaven closer to producing a usable
answer? Allowed verdicts are YES, NO-BUT-JUSTIFIED, and NO-NOT-JUSTIFIED. Reject
or request changes for NO-NOT-JUSTIFIED.

Skeptical outside-reviewer question:

```text
Is this finally building the app, or is it building convincing apparatus around the app?
```

A phase brief is invalid if a skeptical reviewer could fairly describe the
deliverable as "a nice collection of harnesses" and the ordinary product path
still cannot demonstrate the claimed behavior.

Current repo-doc posture: after #352 through #355, the next gate is tightly
scoped limited live validation, not another proof layer.

## Surface vocabulary

Use precise vocabulary instead of the retired active phrase protected surface:

- **licensed surface:** explicitly opened by the phase brief.
- **target surface:** the thing this phase is meant to inspect, change, reduce,
  move, simplify, retire, or strangle.
- **high-custody surface:** important/risky behavior requiring narrow scope,
  named tests, and stop conditions.
- **closed-this-phase surface:** do not touch in this phase.
- **historical surface:** retained as record, not current doctrine or product
  path.
- **strangler target:** a surface to reduce, bypass, demote, subordinate, or
  delete over time.

"Protected" is retired as active phase-control vocabulary because it can imply
"do not touch." When a surface is important and risky but intended to be changed,
call it a high-custody target or strangler target, not protected.

## Required proof classes

Every implementation phase must identify one proof class:

```text
docs_only
schema_or_passive_record
component_harness_proof
offline_product_path_proof
offline_product_path_projection_proof
live_component_proof
live_product_proof
```

A phase must not use broader completion language than its proof class supports.

## Product-Facing Progress Default

Default to product-path integration or product-facing dogfood output that reuses
existing machinery. A non-product phase must carry a short leash: it must name
the current-path consumer or blocker it clarifies/removes, explain why product
path work is not licensed or safe in that phase, and name the mandatory next
product-path checkpoint.

Another harness, proof, packet, projection, registry, or passive record is not
progress by default. It is allowed only when it has a named current-path consumer
or removes a named blocker for an existing current-path consumer. If that
consumer or blocker cannot be named, stop before implementation.

Hard stop: do not add another harness, proof, packet, projection, registry, or
passive record without a named current-path consumer or named blocker removal.

## Current authority and product-consumed distinction

Do not let "current authority path" imply that the ordinary product path consumes
or demonstrates the behavior. Use the narrower labels below:

- **current internal authority path:** canonically owned or reduced by
  RunKernel/RunAuthority or another named current authority, but not necessarily
  product-visible.
- **current product-consumed path:** consumed by ordinary CLI/app/product flow.
- **fixture-only proof:** fixture-backed proof of a seam, not product-consumed.
- **offline harness / proof-only harness:** offline scaffold or script, not live
  and not product-consumed unless the ordinary path consumes it.
- **integration-staging harness:** temporary scaffold while wiring a named product
  consumer.
- **product-facing dry-run proof:** reviewable output through a local/dry-run
  path; useful but not live product correctness.
- **live product path:** explicitly licensed live product execution that reaches
  the claimed product output.
- **historical/proof-only debt:** retained proof or harness history that must not
  be cited as current product progress.

A surface can be current internal authority while still having only fixture-only,
offline-harness, or product-facing-dry-run proof. Use current product-consumed
path only when ordinary product/CLI/app flow actually consumes the behavior.

## Execution-surface classes

Classify the exact command or invoked branch, not merely the Python module that
contains it, as one of:

```text
PRODUCT
OPERATOR
VALIDATION
LEGACY
```

`PRODUCT` is the supported ordinary user-query execution path. Representative
commands and consumers include `python -m scryraven "<query>"`, the supported
compatibility invocation `python -m proplex "<query>"`, and ordinary
`run_pipeline()` consumption. Only PRODUCT execution can independently
establish an actual application behavior delta.

`OPERATOR` is an explicit status, dogfood, provider-decision, diagnostic,
inspection, or operational branch for a maintainer or operator. Human-readable
OPERATOR output is not ordinary product output.

`VALIDATION` includes tests, dry-runs, fixtures, harnesses, brokers, replay
tools, collection checks, validation buckets, and validation-only scripts. A
VALIDATION surface may exercise a real product consumer and support offline
product-path proof, but the validation root itself is not a user product
entrypoint.

`LEGACY` is a retired, tombstoned, compatibility-reference, or historical
execution surface that is not current product consumption. A LEGACY surface
cannot establish current product behavior.

Every final bundle must list each executed root command with:

```text
Command:
Execution surface class:
Proof class supported:
Product consumer reached, if any:
Claim permitted:
Claim forbidden:
```

Human-readable output from operator, validation, demo, dry-run, fixture, or
legacy execution is not ordinary product execution merely because it is
readable.

## Required phase fields

Every phase brief and final bundle should include:

```text
Proof class:
Product-facing progress type:
Product path affected:
Runtime consumer:
Actual consumer seam:
Actual app delta:
User-facing/reviewable output delta:
Non-product exception leash:
Mandatory next product-path checkpoint:
Existing machinery reused:
New machinery introduced:
Why this is not reinventing an existing surface:
Old path treatment:
Human-reviewable product output:
Non-proofs:
Live validation status:
Bridge or exit condition:
```

Definitions:

- **Proof class** states what kind of evidence the phase actually produces.
- **Product-facing progress type** states whether the phase is product-path
  integration, product-facing dry-run/dogfood output, quarantine/docs-process
  work, fixture-only proof with a leash, offline harness proof with a leash,
  live-search-only validation, or live product proof.
- **Product path affected** states whether ordinary `run_pipeline()`, CLI/product
  execution, UI product execution, or only a harness/test/script is affected.
- **Runtime consumer** names the actual function/module that consumes the new
  authority, schema, state, or output.
- **Actual consumer seam** names the producer-to-consumer boundary being proved,
  including whether the consumer is current internal authority, current
  product-consumed, passive, fixture-only, offline harness, live-search-only
  validation, product-facing dry-run proof, legacy/passive/historical, or closed
  unless separately licensed.
- **Actual app delta** states what the ordinary app can do after the phase that it
  could not do before.
- **User-facing/reviewable output delta** states what a user or reviewer can newly
  inspect. If the answer is "none," state that plainly.
- **Non-product exception leash** states why this phase is allowed to be
  non-product work, how it is bounded, and what product-path checkpoint follows.
- **Mandatory next product-path checkpoint** names the next checkpoint that must
  convert, integrate, dogfood, or retire the clarified surface. If no checkpoint
  can be named, the phase should stop.
- **Existing machinery reused** names the current runtime/test/doc surfaces this
  phase builds on instead of replacing.
- **New machinery introduced** names every new packet, reducer, harness,
  projection, registry, static test, or doc surface. For docs-only quarantine,
  this should be limited to docs/tests.
- **Why this is not reinventing an existing surface** explains why the change
  consolidates, classifies, integrates, or removes a blocker instead of adding a
  parallel authority or proof lane.
- **Old path treatment** states whether the old path is deleted, demoted,
  bypassed, subordinated, retained as passive/legacy/history, or closed until a
  later licensed phase. If no old path exists, state that explicitly.
- **Human-reviewable product output** states whether the phase emits actual
  human-reviewable product-shaped output, such as prose, or only structural
  proof/projections/packets. Human-readable output is not product correctness
  unless the proof class and validation actually support that claim.
- **Non-proofs** states what the phase explicitly does not prove.
- **Live validation status** states whether live validation was run, prohibited,
  not licensed, or separately licensed with exact scope.
- **Bridge or exit condition** states how a harness/passive proof becomes
  product-path work later, or how it will be fixtureized/retired.

## Build/product-facing Repair substitute-output gate

Every BUILD or product-facing REPAIR phase must include:

```text
Ordinary entrypoint:
User-style demonstration input:
Forbidden substitute outputs:
Product-path pass condition:
Product-path fail condition:
```

Forbidden substitute outputs:

- harness-only path
- fixture-only path
- proof-only script
- replay-only path
- packet-only artifact
- projection-only artifact
- docs-only doctrine
- shadow vertical slice

Pass condition: a user-style input enters through the ordinary product/CLI/app
path and produces the claimed reviewable output.

Fail condition: the ordinary product path cannot consume the change. Stop with a
blocker report instead of demonstrating the behavior beside the product.

## Required pre-phase questions

Before implementation, answer:

```text
What can the actual app do after this phase that it could not do before?
What product-facing progress type is this?
Does this affect the ordinary user-query path, or only a component/test harness?
What runtime function consumes the new state?
Is the consumer in run_pipeline()/ordinary product execution, CLI execution, a fixture harness, or a standalone script?
What user-facing or reviewer-facing output changes?
If this is non-product work, what is the exception leash and mandatory next product-path checkpoint?
What existing machinery is reused?
What new machinery is introduced?
Why is this not reinventing an existing surface?
What old authority path is removed, demoted, bypassed, or subordinated?
Which old path is retained only as passive/legacy/history?
What exact test or command proves the claim?
Does the output qualify as human-reviewable product output or only structural proof?
Was live validation run, prohibited, or not licensed?
What does this phase explicitly not prove?
```

If the actual app delta, consumer seam, exception leash, or next product-path
checkpoint is vague, stop and run an integration or authority-path audit before
continuing.

## Harness label and expiration rule

A harness is allowed, but only with a short leash.

Every new harness, proof-only script, replay path, packet-only demo, or
non-product scaffold must carry exactly one label:

```text
PRODUCT-PATH-REGRESSION
SEAM-DIAGNOSTIC
INTEGRATION-STAGING
EXPLORATORY-PROOF-ONLY
SHADOW-PRODUCT-HARNESS
```

Definitions:

- PRODUCT-PATH-REGRESSION: a harness/test guarding behavior already consumed by
  the ordinary product path. Healthy and durable.
- SEAM-DIAGNOSTIC: temporary harness to isolate a failure or uncertainty at one
  seam. Must name the product seam and exit condition.
- INTEGRATION-STAGING: temporary scaffold used while wiring a real product path.
  Must name ordinary runtime consumer and integration deadline.
- EXPLORATORY-PROOF-ONLY: non-product learning/proof. Must not be named like
  product behavior and must have integrate/reject/delete decision.
- SHADOW-PRODUCT-HARNESS: a product-shaped alternate path beside the product.
  Failure unless explicitly authorized for review-only diagnosis.

Required fields for any new harness/proof-only script/replay path:

```text
Harness label:
Ordinary product path guarded or fed:
Runtime consumer:
Why ordinary product-path work cannot be done directly:
Integration deadline:
Exit condition:
Why this is not a shadow product path:
Forbidden interpretation:
```

A harness created in phase N should be consumed, converted to product-path
regression guard, deleted, or marked historical/proof-only debt by phase N+1. It
may survive to N+2 only if N+1 exposed a specific blocker and N+2 is explicitly
the integration/retirement phase. After N+2, unconsumed harness/proof scaffolding
is historical/proof-only debt by default and must not be cited as product
progress.

A good harness phase must state:

```text
This is a harness.
It does not affect the product path yet.
It proves this exact interface/invariant.
The next step is integrate, fixtureize, or retire.
```

No component proof should get more than one or two phases without a product-path
checkpoint. Hidden harness drift is a stop condition. The right next action is to
integrate existing machinery, dogfood through the product path, or retire/demote
the unused surface.

## Review checks

During PR/final-bundle review, explicitly check:

- What proof class does the PR actually establish?
- What product-facing progress type did it choose?
- Does the claimed completion language match that proof class?
- What actual consumer seam was proved?
- What can the actual app do now that it could not do before?
- What user-facing or reviewable output changed?
- If this is non-product work, what exception leash and mandatory next
  product-path checkpoint keep it from drifting?
- What existing machinery was reused?
- What new machinery was introduced?
- Why is this not reinventing an existing surface?
- Is the new authority object consumed by the runtime path it governs?
- Is the runtime consumer in ordinary `run_pipeline()`/product execution, CLI
  execution, a fixture harness, or a standalone script?
- Did the PR merely add trace/projection/storage?
- What old authority path was deleted, demoted, bypassed, or subordinated?
- What old path was retained as passive/legacy/historical, and is it clearly
  quarantined?
- Is the output human-reviewable product output or structural proof only?
- Was live validation run, prohibited, not licensed, or separately licensed?
- If this is a harness, what is the bridge, fixtureize, or retire exit condition?
- Did live validation remain explicitly licensed and gated?

## Live proof classes

Live validation remains default-off.

`live_component_proof` requires a licensed component harness, call cap,
redaction plan, output packet path, and stop condition.

`live_product_proof` requires a licensed ordinary product-path command, exact
query or query class, run cap, provider/model/search/fetch/read budget,
redaction plan, output packet path, decision the run will make, and stop
condition.

A live component proof is not a live product proof.

## Hard stops

Stop if:

- proof class is missing;
- product-facing progress type is missing;
- actual app delta is vague;
- runtime consumer is unnamed;
- actual consumer seam is unnamed;
- user-facing/reviewable output delta is vague;
- non-product exception leash is missing for non-product work;
- mandatory next product-path checkpoint is missing for non-product work;
- existing machinery reused is unstated;
- new machinery introduced is unstated;
- why-this-is-not-reinventing is unstated;
- product completion is claimed from a component harness;
- product correctness is claimed from fixture/offline proof;
- live product validation is claimed from live-search-only or offline proof;
- citation rendering, source-obligation satisfaction, or AuthorProse product
  proof is claimed from the current fixture/offline chain;
- trace/projection/storage is treated as runtime consumption;
- another harness/proof/packet/projection/passive record is proposed without a
  named current-path consumer or named blocker removal;
- a harness continues beyond one or two phases without a product-path checkpoint;
- live validation is implied rather than explicitly licensed;
- secrets, `.env`, raw provider payloads, raw prompts, raw model responses,
  private logs, DB/cache rows, or full traces are required.
