# FinalAnswerPacket / Author Boundary

Status: current
Authority: canonical:fap-author-boundary
Default-read: no
Applies-to: ordinary FinalAnswerPacket packaging, Author rendering, and blocked FAP terminal behavior
Does-not-authorize: new claims, evidence interpretation, synthesis creation, citation upgrade, or Author execution when FAP is blocked
Verified-against-runtime: 4e095c7db287ab29fbe748bdd5c24cf4f2545e15
Update-trigger: merged change to FAP packaging, Author input, rendering, or blocked terminal behavior

## Responsibility

This document owns the installed boundary among Sufficiency,
FinalAnswerPacket (FAP), Author, and blocked terminal behavior. The complete
semantic authority flow belongs to
[Run-Contract Semantic Loop](RUN_CONTRACT_SEMANTIC_LOOP.md), and the bounded
multi-component producer path belongs to
[Multi-Component Synthesis Runtime Architecture](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md).

The authority sequence is:

```text
RunKernel-admitted direct and synthesized state
-> Sufficiency readiness decision
-> FinalAnswerPacket authority packaging
-> Author rendering
-> deterministic quantitative finalization validation
-> RunOutcome
```

Sufficiency decides whether admitted state is ready, partial, blocked,
contested, insufficient, follow-up-required, or not applicable. Graph admission
alone is not answer readiness.

## FinalAnswerPacket Contract

FAP is a constrained authority manifest, not a planner, Analyst, validator, or
repair layer. It packages admitted and readiness-approved material for Author.

FAP may package:

- admitted direct component claims;
- admitted synthesis;
- required caveats and uncertainty posture;
- source and evidence bindings already authorized upstream;
- not-claimed and prohibited-upgrade boundaries;
- rendering and mode references; and
- a claim-scoped quantitative finalization authority manifest; and
- readiness and support posture references.

FAP must not:

- create, repair, reinterpret, or validate a claim or synthesis;
- glue unadmitted component outputs;
- decide what evidence means or which source is authoritative;
- create citation eligibility or satisfy source obligations;
- remove blockers or required caveats;
- upgrade weak or contested support; or
- package material that Sufficiency did not authorize.

FAP packaging does not itself prove answer correctness, citation correctness,
or source-obligation satisfaction.

## Author Contract

Author is a constrained communication layer over FAP-authorized material.

```text
Author may improve presentation.
Author may not improve truth posture.
```

Author may choose clear wording, structure the response, follow mode and
rendering rules, preserve required caveats, pass through authorized sources,
and explain synthesis that is already admitted and packaged.

For quantitative propositions, Author receives exact transient renderings and
fixed instructions prohibiting calculation, conversion, estimation,
interpolation, unsupported rounding, rescaling, aggregation, and new numeric
conclusions. Its response is buffered until the shared deterministic validator
binds each numeric assertion to the current manifest. Accepted comma grouping
does not broaden subject, metric, unit, sign, scale, percent, precision, or
claim authority.

Author must not reinterpret evidence, resolve conflicts, decide source
authority, drop caveats, upgrade support, invent missing context, introduce new
claims, create missing synthesis, repair evidence, satisfy a missing source
obligation, or create authority absent from FAP.

## Blocked FAP Terminal

When FAP readiness is blocked, Author does not run. No Author input is derived
and no Author model call is made.

For the installed ordinary blocked-readiness case, the product returns a
deterministic sanitized non-Author `RunOutcome` rather than relabeling the case
as an Author answer or raising `PipelineError`. The exported terminal posture is
blocked/insufficient even when upstream diagnostics preserved a partial-answer
lineage.

The safe summary may include sanitized readiness reasons, missing obligations,
component counts, and evidence posture. It must not contain prompts, raw model
or provider material, raw evidence, credentials, private logs, full traces,
chain of thought, or unsupported answer claims. Pre-FAP execution facts such as
recovery, conflict, weak-corpus, and source-class posture may remain available
as safe diagnostics.

This normalization is narrow. Malformed packets, broken identity or lineage,
invariant failures, infrastructure failures, and unrelated internal failures
remain errors. They must not be relabeled as ordinary insufficiency.

## Ordinary And Supporting Surfaces

The ordinary product path currently consumes Sufficiency, FAP, Author,
`RunOutcome`, and CLI-visible output for supported direct and bounded
multi-component cases. That ordinary behavior is the current product contract.

[Final Answer Packet Hardening](AG_FINAL_ANSWER_PACKET_HARDENING_01.md) and
[Author Prose-Only Finalization](AUTHOR_PROSE_ONLY_FINALIZATION_01.md) preserve
useful bounded hardening, packet-posture, and prose-only supporting contracts.
They do not define the only current product path and must not be used to demote
ordinary FAP/Author consumption to future work. Older FAP, Author, and follow-up
phase records remain compatibility or historical context unless a current
owner explicitly reuses them.

The current ordinary AuthorExecutor, hardened AuthorProseFinalization, and
follow-up AF5B finalizer all consume
[Quantitative Finalization Containment](AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md).
Rejected prose creates no successful finalization, is not displayed or edited,
and does not trigger an Author retry.

## Source Gateway

A presentation layer may make already authorized claims inspectable through a
chain such as:

```text
answer claim
-> admitted component or synthesis
-> FAP authorization
-> source binding
-> bounded source material
```

This is presentation and inspectability direction. It is not an installed
source-authority engine, citation eligibility engine, citation renderer, or
source-obligation satisfaction path unless current code and focused tests
separately establish that exact behavior. This phase changes none of those
runtime surfaces.

## Nonproofs

This contract does not prove arbitrary-query readiness, live product behavior,
citation rendering, source-obligation satisfaction, broad Author quality, or
product correctness. It does not authorize changes to citations, prompts,
models, providers, source ranking, FAP runtime, or Author runtime.
