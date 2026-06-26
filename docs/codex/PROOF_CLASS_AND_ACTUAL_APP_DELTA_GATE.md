# Proof Class and Actual App Delta Gate

Status: Codex-facing implementation guardrail.
Use when: drafting Codex phase briefs, implementing authority/custody/semantic/provider/Author phases, reviewing final bundles, or distinguishing product-path work from component harness work.

## Purpose

ScryRaven phases must not claim more than they prove.

A component harness can prove a seam, but it does not improve the product until the ordinary runtime consumes that seam.

This document makes the proof class and actual product delta explicit before implementation starts and again in the final bundle.

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

## Required phase fields

Every phase brief and final bundle should include:

```text
Proof class:
Product path affected:
Runtime consumer:
Actual app delta:
Non-proofs:
Bridge or exit condition:
```

Definitions:

- **Proof class** states what kind of evidence the phase actually produces.
- **Product path affected** states whether ordinary `run_pipeline()`, CLI/product execution, UI product execution, or only a harness/test/script is affected.
- **Runtime consumer** names the actual function/module that consumes the new authority, schema, state, or output.
- **Actual app delta** states what the ordinary app can do after the phase that it could not do before.
- **Non-proofs** states what the phase explicitly does not prove.
- **Bridge or exit condition** states how a harness/passive proof becomes product-path work later, or how it will be fixtureized/retired.

When validation scope matters, keep the phase prompt compact but explicit:

```text
Validation bucket:
Exact bucket command(s):
Exact phase_focus test path(s) or node id(s):
Full offline required:
Intentionally not run:
```

This lets future prompts rely on repo-visible validation guidance instead of
repasting the whole lane doctrine.

## Required pre-phase questions

Before implementation, answer:

```text
What can the actual app do after this phase that it could not do before?
Does this affect the ordinary user-query path, or only a component/test harness?
What runtime function consumes the new state?
Is the consumer in run_pipeline()/ordinary product execution, CLI execution, a fixture harness, or a standalone script?
What old authority path is removed, demoted, bypassed, or subordinated?
What exact test or command proves the claim?
What does this phase explicitly not prove?
```

If the answer is vague, stop and run an integration or authority-path audit before continuing.

## Harness rule

A harness is allowed, but only with a short leash.

A good harness phase must state:

```text
This is a harness.
It does not affect the product path yet.
It proves this exact interface/invariant.
The next step is integrate, fixtureize, or retire.
```

No component proof should get more than one or two phases without a product-path checkpoint.

Default checkpoint:

```text
Does run_pipeline() consume this, or not?
```

Component proofs may be valuable, but they must not be described as product-path completion unless `run_pipeline()` or the ordinary runtime path consumes them.

Hidden harness drift is a stop condition.

## Author harness recovery lesson

AG-CHECK-01 proved ordinary `run_pipeline()` already consumes packet-constrained Author authority through:

```text
FinalAnswerPacket -> AuthorExecutor -> RunOutcome
```

The AF4B2 -> AF4C -> AF4D -> AF5A -> AF5B lane is a component harness / reference lab. It is partially shared and bridgeable, but it is not the ordinary product path today.

Correct posture:

```text
The AF4B2 -> AF5B lane is not the ordinary product path.
Do not promote it by implication.
When future phases touch Author payload/materialization/execution/finalization,
harvest its lessons deliberately.
```

Avoid both bad reactions:

```text
Bad reaction A: "The harness was fake, throw it away."
Bad reaction B: "We spent time on it, so install it."
```

The right reaction is:

```text
Treat it as a stricter Author-custody reference lab.
Harvest its invariants when a real Author-facing product phase opens.
```

## Harness lessons worth preserving

When a future Author-facing product phase opens, consider deliberately harvesting:

- bounded Author evidence content;
- explicit invocation construction;
- explicit model-request assembly;
- fake/mock-live/live/brokered adapter accounting;
- sanitized candidate response and finalization posture;
- no raw prompt/provider/model retention;
- broker/private adapter remains credential plumbing only.

Do not deepen the Author harness by default.

## Semantic-contract phase example

For the current AG-SEM-05 through AG-SEM-10 completion checkpoint and next gates,
see
`docs/architecture/AG_SEM_05_10_COMPLETION_AND_NEXT_GATES.md`.

For AG-SEM-01 Passive Semantic Contract Foundation:

```text
Proof class: schema_or_passive_record
Product path affected: no runtime product behavior yet
Runtime consumer: none yet; future RunAuthority/Sufficiency consumers named but closed
Actual app delta: repo gains passive semantic contract records/invariants for future authority work
Non-proofs: no product behavior, no Balanced loop, no Author change, no live proof
Bridge or exit condition: later canonical reducer accepts answer components into ordinary RunAuthority chain
```

## Docs/test sanitation example

For AG-DOC-TEST-SANITY-01:

```text
Proof class: docs_only plus validation-routing / test-collection sanitation
Product path affected: none
Runtime consumer: none
Actual app delta: none; repo-visible guidance and offline collection routing improve
Non-proofs: no live validation, no product recovery behavior change, no full-suite repair
Bridge or exit condition: AG-LIVE-BOUND-01 can use shorter repo-doc-backed prompts
```

For AG-SEM-02:

```text
Proof class: schema_or_passive_record
Product path affected: no runtime product behavior yet
Runtime consumer: none yet; future SemanticObservation admission reducer named but closed
Actual app delta: repo gains sanitized content-reference and SemanticObservation schemas
Non-proofs: no canonical coverage, no Sufficiency consumer, no provider/search behavior, no Author behavior
Bridge or exit condition: later observation admission and coverage reducer phases
```

## Review checks

During PR/final-bundle review, explicitly check:

- What proof class does the PR actually establish?
- Does the claimed completion language match that proof class?
- What can the actual app do now that it could not do before?
- Is the new authority object consumed by the runtime path it governs?
- Is the runtime consumer in ordinary `run_pipeline()`/product execution, CLI execution, a fixture harness, or a standalone script?
- Did the PR merely add trace/projection/storage?
- What old authority path was deleted, demoted, bypassed, or subordinated?
- If this is a harness, what is the bridge, fixtureize, or retire exit condition?
- Did live validation remain explicitly licensed and gated?

## Live proof classes

Live validation remains default-off.

`live_component_proof` requires a licensed component harness, call cap, redaction plan, output packet path, and stop condition.

`live_product_proof` requires a licensed ordinary product-path command, exact query or query class, run cap, provider/model/search/fetch/read budget, redaction plan, output packet path, decision the run will make, and stop condition.

A live component proof is not a live product proof.

## Hard stops

Stop if:

- proof class is missing;
- actual app delta is vague;
- runtime consumer is unnamed;
- product completion is claimed from a component harness;
- trace/projection/storage is treated as runtime consumption;
- a harness continues beyond one or two phases without a product-path checkpoint;
- live validation is implied rather than explicitly licensed;
- secrets, `.env`, raw provider payloads, raw prompts, raw model responses, private logs, DB/cache rows, or full traces are required.
