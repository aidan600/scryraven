# D-prime Architecture

Status: current
Authority: canonical:dprime-role-contract
Default-read: no
Applies-to: component and synthesis D-prime role boundaries
Does-not-authorize: model calls, retrieval, admission, contract mutation, FAP, Author, additional Specialist activation, or live validation
Verified-against-runtime: bba0d16313944b742251298b4fc929b4ceb55d76
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
Installed calculator-specific claim alignment belongs to
[Quantitative Specialist Product Activation](AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md).
Final accepted-prose binding belongs to
[Quantitative Finalization Containment](AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md).

D-prime is an evidence-relative validation role. It reviews one nominated
proposal against the exact evidence, component, synthesis, dependency, scope,
currentness, source-obligation, blocker, and caveat refs bound into its input.
It does not choose the proposal, admit the result, or render an answer.

## Current Role Split

| Role | Owns | Must not do |
| --- | --- | --- |
| Component Analyst | Proposes what bounded custodied evidence supports for one answer component and may nominate one exact source-bound quantitative need. | Validate or admit its own proposal, authorize the capability or recovery, or render. |
| Component D-prime | Validates the nominated component proposal against its bound evidence and component obligations, including exact calculator claim alignment when handed off. | Act as first-pass Analyst, invent or calculate a claim, admit support, mutate the AnswerContract, or render. |
| Cross-Component Analyst | Proposes dependencies, contradictions, constraints, synthesis nodes, missing components, caveats, recovery needs, and an exact cross-component quantitative need over admitted refs. | Validate or admit its own synthesis, authorize the capability or recovery, or render. |
| Synthesis D-prime | Validates nominated synthesis against current admitted component, synthesis, edge, blocker, caveat, and two-hop calculator lineage refs. | Invent or calculate synthesis, act as Cross-Component Analyst, admit graph state, or render. |
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

For an admitted quantitative claim, downstream projection may carry the exact
applicable D-prime artifact ref and consumption lineage into FAP. That ref does
not expand D-prime authority: it lets finalization prove that an admitted claim
was reviewed by the applicable validator. Review and admission alone do not
prove that the numeric proposition was explicitly source-stated or calculated
by an authorized Specialist. Finalization therefore omits a generic admitted
numeric proposition unless its complete proposition and literal signature bind
to current FAP source material, or a completed installed Specialist result with
exact claim-material alignment was consumed by the applicable D-prime. Missing,
stale, nonapplicable, or otherwise unaccompanied D-prime lineage cannot authorize
numeric prose.

The generic Specialist graph substrate provides the outcome of a proposed need
to component or synthesis D-prime under one top-level
`specialist_need_handoff` namespace. The handoff carries either a bounded
result or a typed policy, capability, target, budget, failure, blocked, or
contested availability posture. Only no proposal omits it. The nominated claim,
evidence, component, graph, and admitted input bindings remain ordinary
D-prime inputs. A required predispatch reconstruction failure still creates the
failed handoff before the scheduler blocks; it creates no result and remains
pending and unconsumed because D-prime does not run. Optional nonexecution
handoffs remain visible to the applicable D-prime. RunKernel independently
rederives the exact current D-prime
role, action, artifact, target, and handoff-bearing input digest before
exactly-once consumption; it does not trust a caller-supplied route or status.
A Specialist outcome preserves exact lineage, cannot validate itself, and
cannot bypass D-prime or RunKernel.

The deterministic source-bound calculator is registered and activated by the
fixed S1 ordinary product composition for the named bounded multi-component
class. A completed handoff supports the nominated claim only when its exact
calculated value, operator, unit, precision, assumptions, caveats, source-
explicit input lineage, and claim alignment all match. Synthesis use additionally
requires two-hop proof from each admitted component claim to the same exact
literal in underlying current evidence. Execution success alone is insufficient;
non-exact alignment remains contested. D-prime does not rerun arithmetic or
authorize the capability.

The repository-owned model-visible quantitative proposal contract is an input
only to ordinary component and Cross-Component Analyst proposal production. It
is deliberately absent from component and synthesis D-prime input. D-prime
receives the bounded result-or-disposition handoff and ordinary evidence or
admitted-input refs; the contract cannot become validation or admission
authority.

Before synthesis D-prime can receive graph-derived work, Cross input reproof is
unconditional. The ordinary caller may bind the exact transient Cross packet;
RunKernel independently reconstructs it from current scheduler-owned component
Analyst packets. Missing or stale reconstruction authority rejects graph
reduction and retains no packet, contract, catalog, or source material. This
does not add D-prime calculation, proposal, or admission authority.

## Nonproofs

This contract does not prove arbitrary-query support, live model quality,
provider correctness, retrieval quality, citation correctness, live calculator
correctness, broad quantitative reasoning quality, answer quality, or product
correctness. Live calls remain separately licensed.
