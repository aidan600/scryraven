# D-prime Architecture

Status: current
Authority: canonical:dprime-role-contract
Default-read: no
Applies-to: component and synthesis D-prime role boundaries
Does-not-authorize: model calls, retrieval, admission, contract mutation, FAP, Author, or product Specialist activation
Verified-against-runtime: 4292320b5583772f3f31ce2dab4c6f0e2c989ed8
Update-trigger: merged change to component or synthesis D-prime authority or ordinary consumption

## Responsibility

This document owns the durable role contract for component and synthesis
D-prime. Installed-state claims belong to
[ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md), phase order belongs to
[Current Roadmap](../roadmap/CURRENT_ROADMAP.md), and the complete bounded
multi-component path belongs to
[Multi-Component Synthesis Runtime Architecture](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md).
Generic Specialist result boundaries belong to
[Specialist Graph Substrate](SPECIALIST_GRAPH_SUBSTRATE.md).

D-prime is an evidence-relative validation role. It reviews one nominated
proposal against the exact evidence, component, synthesis, dependency, scope,
currentness, source-obligation, blocker, and caveat refs bound into its input.
It does not choose the proposal, admit the result, or render an answer.

## Current Role Split

| Role | Owns | Must not do |
| --- | --- | --- |
| Component Analyst | Proposes what bounded custodied evidence supports for one answer component. | Validate or admit its own proposal, authorize recovery, or render. |
| Component D-prime | Validates the nominated component proposal against its bound evidence and component obligations. | Act as first-pass Analyst, invent a claim, admit support, mutate the AnswerContract, or render. |
| Cross-Component Analyst | Proposes dependencies, contradictions, constraints, synthesis nodes, missing components, caveats, and recovery needs over admitted refs. | Validate or admit its own synthesis, authorize recovery, or render. |
| Synthesis D-prime | Validates nominated synthesis against current admitted component, synthesis, edge, blocker, and caveat refs. | Invent synthesis, act as Cross-Component Analyst, admit graph state, or render. |
| Full Scrutineer | Adversarially challenges a component, synthesis, edge, subgraph, or whole-case posture when triggered. | Replace the first-pass Analyst, manufacture a replacement case, admit state, or render. |
| RunKernel | Performs structural validation and alone admits, blocks, challenges, or authorizes bounded recovery. | Manufacture semantic output or delegate canonical admission to a worker. |

The ordinary bounded multi-component path consumes both component D-prime and
synthesis D-prime. Cross-component synthesis and ComponentWorkGraph V1
admission are installed for the supported class; they are not future D-prime
checkpoints.

Durable mnemonic:

```text
D-prime verifies the claim.
Scrutineer attacks the case.
```

The existing narrow deterministic same-component multi-source Scrutineer gate
is a supporting gate, not the full SmartModel Scrutineer role. Deterministic
schema checks also do not replace evidence-relative D-prime judgment.

## Proposal, Validation, And Admission

The authority sequence is always:

```text
Analyst proposal
-> D-prime evidence-relative validation
-> deterministic schema, identity, lineage, and digest checks
-> RunKernel admission, block, challenge, or recovery authorization
```

For synthesis, the same separation applies:

```text
Cross-Component Analyst synthesis proposal
-> synthesis D-prime validation
-> deterministic graph, identity, revision, and cycle checks
-> RunKernel graph/synthesis admission
```

Workers propose or validate. They do not mutate canonical state. A validator-
valid result remains candidate state until RunKernel consumes the exact current
lineage and reduces an authority decision. No role may validate its own
proposal, and no D-prime result may bypass RunKernel admission.

Every review is bound to the exact input and lineage it evaluated. A stale
AnswerContract, component revision, graph revision, synthesis revision,
evidence ref, proposal digest, or lease cannot authorize current state. A
schema-valid response with mismatched identity fails closed rather than being
reinterpreted or rebound.

## Evidence-Relative Review

D-prime keeps semantic support separate from evidential adequacy:

```text
semantic support: what does the bounded source material actually support?
evidential adequacy: is that support current, representative, scoped, and
appropriate enough for the nominated claim?
```

Custody, readability, bounded content, preflight success, model agreement, and
`directly_supports` labels are not admitted support by themselves. A D-prime
review may support, partially support, abstain, challenge, identify a
contradiction, preserve caveats, or propose a follow-up need. A follow-up need
is not search authorization.

Non-negotiable negative controls include:

- unrelated official text must not produce support;
- correct source with the wrong component or scope must not produce support;
- wrong currentness or effective date must not be upgraded;
- missing answer-bearing content must abstain;
- contradiction must remain challenge or contested posture;
- model output without exact selector, proposition, component, and lineage
  binding must fail closed;
- deterministic preflight and model review must each fail closed when the
  other is absent or invalid.

## Supporting Single-Relation Capability

The bounded single-relation D-prime machinery remains a reusable supporting
lane. It includes evidence-frame preflight, negative controls, strict one-shot
review, proposal validation, RunKernel admission, SemanticObservation and
ComponentCoverage materialization, source-obligation authority,
citation-source handoff, a single-lane answer path, follow-up re-entry, and
same-lane multi-source scrutiny.

Those surfaces preserve useful evidence-relative and anti-laundering controls,
but their historical chronology does not define the current D-prime
architecture. Work near these responsibilities should prefer reuse or adaptation
over rebuilding source-obligation or citation-readiness machinery.
Same-component multi-source review also does not prove cross-component
synthesis; the ordinary bounded multi-component owner defines that installed
path.

The proposal-only cross-component rationale remains available in
[Cross-Component Analyst Workbench](CROSS_COMPONENT_ANALYST_WORKBENCH.md).

## Downstream And Future Boundaries

D-prime has no direct FinalAnswerPacket or Author authority. It cannot decide
Sufficiency, package claims, create citation eligibility, render citations,
write prose, or claim correctness. Those downstream owners consume only
RunKernel-admitted state.

The generic Specialist graph substrate provides the outcome of a proposed need
to component or synthesis D-prime under one top-level
`specialist_need_handoff` namespace. The handoff carries either a bounded
result or a typed policy, capability, target, budget, failure, blocked, or
contested availability posture. Only no proposal omits it. The nominated claim,
evidence, component, graph, and admitted input bindings remain ordinary
D-prime inputs. RunKernel independently rederives the exact current D-prime
role, action, artifact, target, and handoff-bearing input digest before
exactly-once consumption; it does not trust a caller-supplied route or status.
A Specialist outcome preserves exact lineage, cannot validate itself, and
cannot bypass D-prime or RunKernel.

The deterministic source-bound calculator remains an installed bounded
supporting capability. It is not registered or activated as an ordinary
Specialist by the generic substrate phase.

## Nonproofs

This contract does not prove arbitrary-query support, live model quality,
provider correctness, retrieval quality, citation correctness, answer quality,
or product correctness. Live calls remain separately licensed.
