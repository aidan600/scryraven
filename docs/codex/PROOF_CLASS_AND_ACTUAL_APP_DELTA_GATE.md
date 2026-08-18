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

Current priority and checkpoint selection belong exclusively to
`docs/roadmap/CURRENT_ROADMAP.md`; completed chronology in this guardrail does
not select another proof or infrastructure phase.

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

## Three-level testing model

Use this top-level taxonomy before selecting a focused seam:

```text
Whole product:
supported user input
-> ordinary ScryRaven pipeline
-> user-visible result or honest blocker

Front half:
user query
-> SearchPlanner
-> QueryPlan
-> SearchOS discovery and READ
-> EvidenceLedger/canonical custody handoff

Back half:
fixed known-good canonical evidence/custody
-> Analyst
-> D-prime
-> graph admission/recomputation
-> Sufficiency
-> FinalAnswerPacket
-> Author
```

Focused sub-surface tests remain valid within these three levels. They are
subordinate seams, not separate truth systems. The default repair loop is:

```text
product evidence
-> existing half-specific localization
-> smallest repair
-> another product pulse
```

A component harness must not become a prerequisite for a safe product pulse
merely because it offers more detailed information.

## Required proof classes and evidence ladder

Every implementation phase must identify one proof class:

```text
STATIC_CONTRACT_PROOF
OFFLINE_COMPONENT_PROOF
OFFLINE_PRODUCT_PATH_PROOF
MODEL_IN_THE_LOOP_COMPONENT_PROOF
LIVE_COMPONENT_PROOF
ORDINARY_CLI_PRODUCT_PROOF
FULL_PRODUCT_PROOF
```

The ladder is cumulative only where the executed consumer supports the stronger
claim. Definitions:

- `STATIC_CONTRACT_PROOF`: repository text, schema, or static contract checks;
  no executed component or product behavior.
- `OFFLINE_COMPONENT_PROOF`: one component boundary with fictional, fake, or
  response-only dependencies; no ordinary product claim.
- `OFFLINE_PRODUCT_PATH_PROOF`: supported user-style input through the ordinary
  product consumer with offline dependencies and a visible result or honest
  blocker.
- `MODEL_IN_THE_LOOP_COMPONENT_PROOF`: a real model reaches the named component
  boundary, without establishing live acquisition or ordinary-product behavior.
- `LIVE_COMPONENT_PROOF`: the named component uses its explicitly licensed live
  model, provider, search, or READ dependency; it is still not product proof.
- `ORDINARY_CLI_PRODUCT_PROOF`: a supported input traverses the ordinary CLI
  pipeline and produces its user-visible result or honest blocker within the
  licensed envelope.
- `FULL_PRODUCT_PROOF`: the claimed supported product boundary is exercised
  end to end. One bounded CLI pulse does not by itself prove broad correctness,
  stability, or the entire supported envelope.

Compact mapping from active older terms:

| Older term | Current evidence class |
| --- | --- |
| `docs_only`, `schema_or_passive_record` | `STATIC_CONTRACT_PROOF` |
| `component_harness_proof` | `OFFLINE_COMPONENT_PROOF` |
| `offline_product_path_proof` | `OFFLINE_PRODUCT_PATH_PROOF` |
| `offline_product_path_projection_proof` | `OFFLINE_PRODUCT_PATH_PROOF`, retaining the projection qualifier and nonproofs |
| `live_component_proof` | `LIVE_COMPONENT_PROOF`; use `MODEL_IN_THE_LOOP_COMPONENT_PROOF` when only a real-model component boundary ran |
| `live_product_proof` | `ORDINARY_CLI_PRODUCT_PROOF` for the ordinary CLI; `FULL_PRODUCT_PROOF` only when the full claimed supported boundary ran |

Do not rename runtime fields, packet schemas, persisted values, test marks, or
historical records solely for terminology consistency. Retain a narrower legacy
label when a coherent active-owner migration would create ambiguity, and define
its current mapping instead. A phase must not use broader completion language
than its evidence class supports.

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
Technical-debt register disposition:
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
- **Technical-debt register disposition** records exactly one of these postures:
  `No change`; `Added TD-XXXX: <title>`; `Updated TD-XXXX: <reason>`; or
  `Removed TD-XXXX: <resolving change>`.
- **Bridge or exit condition** states how a harness/passive proof becomes
  product-path work later, or how it will be fixtureized/retired.

When a phase discovers confirmed current debt outside its scope, check the
[active technical-debt register](../TECH_DEBT_REGISTER.md) for duplication. If
the register is licensed, add or update the item. If it is not licensed, report
the proposed entry in the final bundle for maintainer disposition without
automatically widening scope. Discovery does not authorize repair. A PR that
resolves an item removes its active entry in the same diff and names the TD
identifier in its final bundle. Use `No change` when no item was added, updated,
or removed.

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

## Harness prerequisite and consumption rule

A harness is allowed only with a short, PR-based consumption leash. Every new
harness, fixture, replay seam, evaluator, preparation layer, proof-only script,
packet-only demo, or other non-product scaffold must carry exactly one label:

```text
PRODUCT-PATH-REGRESSION
SEAM-DIAGNOSTIC
INTEGRATION-STAGING
EXPLORATORY-PROOF-ONLY
SHADOW-PRODUCT-HARNESS
```

The existing meanings remain: product-path regression guards are durable;
seam diagnostics and integration staging are temporary; exploratory proof is
non-product learning; and a shadow product harness is a failure unless
explicitly authorized for review-only diagnosis.

Before implementation, the scaffold must establish:

```text
Harness label:
Observed failure or approved hard prerequisite:
Exact unresolved distinction:
Existing owners already tried:
Demonstrated observability or reproducibility gap:
Production-owned boundary injected or observed:
Named immediate consumer:
Why the dependency cannot reasonably be completed in the consumer phase:
Decision the harness will make:
Duplicate-observation check:
Maximum infrastructure PRs before consumption:
Durable ownership, integration, replacement, or removal condition:
Mandatory next supported-product checkpoint:
Forbidden interpretation:
```

A future consumer is acceptable only when it is the approved immediate
successor, the dependency is real, no equivalent seam exists, no second
infrastructure phase intervenes, and the intended evidence and exit condition
are explicit. The default maximum is one infrastructure PR before consumption;
an architectural review must explicitly change that sequence.

Installation alone does not complete the objective:

```text
named consumer uses it
-> evidence is produced
-> a product or architecture decision changes
```

After one non-product infrastructure PR, its immediate successor should consume,
convert, integrate, replace, or remove the scaffold. An unconsumed scaffold is
historical/proof-only debt and cannot be cited as product progress. Hidden
harness drift is a stop condition. A safe product pulse does not require a
component harness merely because the harness would offer finer diagnosis.

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

`live_product_proof` requires a licensed ordinary product-path command and the
completed live-validation addendum. Do not treat private-data / redaction
boundary, raw-retention posture, or sanitized output path as optional; those
fields remain required by the addendum and are separate concerns. Hard
provider/model/search/read/embedding attempt, token, and dollar ceilings are
policy requirements only when that addendum requires them, not a default
live-product budget.

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
