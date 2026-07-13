# Multi-Component Synthesis Runtime Architecture

Status: current
Authority: canonical:bounded-multicomponent-runtime
Default-read: no
Applies-to: ordinary bounded multi-component component, synthesis, recovery, scheduling, and finalization architecture
Does-not-authorize: arbitrary-query claims, live calls, width expansion, Specialist activation, or roadmap execution
Verified-against-runtime: 276d2e7b7608df8c2e26ad7a49125e1a422798f1
Update-trigger: merged change to the bounded ordinary multi-component runtime

## Responsibility And Supported Boundary

This document is the deep canonical owner for the installed bounded ordinary
multi-component runtime. Temporal installed-state summaries belong to
[ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md); current sequence belongs
to [Current Roadmap](../roadmap/CURRENT_ROADMAP.md). Concern-specific details
are owned by [D-prime Architecture](DPRIME_ARCHITECTURE.md),
[Run-Contract Semantic Loop](RUN_CONTRACT_SEMANTIC_LOOP.md),
[RunKernel Component DAG, Scheduling, And Concurrency](RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md),
and [FinalAnswerPacket / Author Boundary](FAP_AUTHOR_BOUNDARY.md).

The installed query class is:

```text
ordinary-bounded-multicomponent-factual-synthesis-v1
```

It does not imply arbitrary-query multi-component support. Nonqualifying and
single-component requests retain the established direct ordinary lane.

## Lane Selection

Lane selection occurs before canonical semantic production. The direct and
bounded multi-component lanes are not both run and compared afterward.

Direct ordinary lane:

```text
accepted component structure + bounded sanitized content refs
+ EvidenceLedger facts
-> ordinary semantic producer
-> RunKernel semantic admission
-> SemanticObservation / ComponentCoverage
-> Sufficiency / FinalAnswerPacket / Author / RunOutcome
```

Qualifying bounded multi-component lane:

```text
accepted explicit factual component structure and synthesis directive
-> component Analyst proposal
-> component D-prime validation
-> RunKernel component admission
-> SemanticObservation / ComponentCoverage / ComponentWorkNode
-> ComponentWorkGraph V1
-> Cross-Component Analyst synthesis proposal
-> synthesis D-prime validation
-> full Scrutineer challenge when triggered
-> RunKernel graph/synthesis admission
-> Sufficiency / FinalAnswerPacket / Author / RunOutcome
```

Broad or legacy Analyst prose is not relabeled as typed component authority.
Component finals are not handed to Author for ungoverned glue.

## Role Ownership

| Role | Owns | Must not do |
| --- | --- | --- |
| Planner / semantic producer | Proposes query meaning, answer components, search/source requirements, and structural request relationships. | Admit claims, validate its own proposals, or manufacture evidence. |
| Component Analyst | Uses the configured SmartModel role to propose what bounded custodied evidence supports for one component. | Validate or admit its proposal, dispatch recovery, or render. |
| Component D-prime | Validates the nominated component proposal against exact evidence, component, scope, source-obligation, currentness, and caveat refs. | Act as first-pass Analyst, invent or admit a claim, dispatch search, or render. |
| Cross-Component Analyst | Proposes dependencies, contradictions, constraints, synthesis nodes, missing components, caveats, and recovery needs. | Validate or admit its synthesis, authorize recovery, or render. |
| Synthesis D-prime | Validates nominated synthesis against current admitted component, synthesis, edge, blocker, and caveat refs. | Invent synthesis, act as Cross-Component Analyst, admit state, or render. |
| Full Scrutineer | Adversarially challenges component, synthesis, edge, subgraph, or whole-case posture when triggered. | Replace first-pass analysis, manufacture a replacement case, admit state, or render. |
| RunKernel | Derives ready work; owns exact batches, leases, caps, settlement, canonical reduction, admission, block/challenge, and recovery authorization. | Manufacture semantic output or accept caller-authored scheduler authority. |
| Sufficiency | Decides readiness from admitted state. | Invent or repair synthesis. |
| FinalAnswerPacket | Packages admitted, readiness-approved direct and synthesized material. | Generate, repair, validate, or reinterpret claims or synthesis. |
| Author | Renders packet-authorized material and may explain admitted synthesis. | Create synthesis, glue unadmitted outputs, repair evidence, or upgrade support. |

Durable mnemonic:

```text
D-prime verifies the claim.
Scrutineer attacks the case.
```

The narrow deterministic same-component multi-source Scrutineer gate remains a
supporting capability; it is not the full Scrutineer SmartModel role.
Deterministic code owns schemas, identity/digest binding, cycle checks, budgets,
safety, privacy hygiene, and output validation. It does not replace semantic
analysis, synthesis validation, or scrutiny.

## Graph And AnswerContract

The graph is acyclic, n-capable in durable shape, serial-compatible, and able
to represent bounded synthesis-of-synthesis. Component and synthesis nodes are
first-class, identity-bearing, revision-bound, challengeable, and admissible.
Two components are an installed lower bound, not a durable schema thesis.

The graph supports direct component results, subset synthesis, multiple
synthesis groups, component-to-synthesis and synthesis-to-synthesis edges,
bounded layered synthesis, and node/edge/subgraph/whole-graph challenge.
Structural edges originate in accepted request structure. Cross-Component
Analyst proposes semantic edges; synthesis D-prime validates them; RunKernel
alone admits them. An empty edge set does not prove semantic independence.

`AnswerContract` and the graph remain separate:

```text
AnswerContract component = an obligation the run owes the user
ComponentWorkNode = a governed lane for one answer obligation
synthesis node = subordinate derived reasoning for one or more obligations
```

A synthesis node does not automatically become an AnswerContract component.
Admitted synthesis may become FAP-safe material only after Sufficiency approves
readiness.

ComponentWorkGraph V1 is the installed ordinary graph for the supported class.
It contains component refs, first-class synthesis nodes, structural and
semantic edges, challenge refs, revision/staleness metadata, and bounded depth
and budget posture. ComponentWorkGraph V0 remains historical/review/
compatibility material and is subordinated to V1; it is not silently redefined
or treated as the ordinary executor.

## Current Bounded Envelope

The executable envelope is derived from code and focused tests:

| Bound | Installed value |
| --- | ---: |
| Initial component nodes | 2–5 |
| Total component nodes after recovery | at most 5 |
| Synthesis nodes | 1–4 |
| Maximum synthesis depth | 2 |
| Missing-component recovery | at most 1 |
| Graph/AnswerContract amendment rounds | at most 1 |
| Selective recomputation | affected synthesis closure only |

The one recovery may add exactly one missing component only while remaining
inside the five-component cap. It amends the AnswerContract through RunKernel,
re-enters ordinary research, admits the recovered component, stales the
affected synthesis closure, carries forward exact unaffected admitted
synthesis under new RunKernel authority, recomputes affected synthesis in
topological order, and performs one fresh whole-case Scrutineer review.

Carried nodes preserve semantic lineage but do not reuse a prior validation or
admission as direct authority for a new revision. A sibling carry-forward
projection records the new non-circular authority binding.

The shared semantic-call caps are:

| Role | Cap |
| --- | ---: |
| Component Analyst | 5 |
| Component D-prime | 5 |
| Cross-Component Analyst | 2 |
| Synthesis D-prime | 8 |
| Scrutineer | 2 |

These caps cover initial and authorized continuation work; they are not model
quality claims or permanent mode budgets. Full Scrutineer is triggered by the
installed policy, including Deep mode, contradiction, unresolved dependency,
material caveat, high-stakes quantitative posture, layered synthesis, or a
synthesis-D-prime challenge/follow-up/ambiguous-support result. Fast and
Balanced may skip full Scrutineer only when no trigger applies.

## Scheduling, Leases, And Concurrency

Every semantic call is Scheduler V2-governed. RunKernel derives canonical ready
work and atomically grants the exact contiguous next batch. The driver does not
provide a role, logical key, packet, backend class, or width as its next-work
choice.

The compatibility envelope is the sum of the shared role caps. Every work item
has an exact budget/work lease bound to current contract, graph, input packet,
target, and recovery/selective lineage. Grant reserves units; predispatch
cancellation returns an exact reservation; dispatch commits it to spent.
Postdispatch failure and stale rejection remain spent. Completion and every
blocked terminal require zero active leases.

Batch grant, cancellation, dispatch spend, and child-action publication are
atomic. V2 selects a contiguous ready prefix without skipping intervening work.
Private child descriptors are reconstructed and validated on the main thread
before commitment. Dispatch spends the whole batch and publishes the complete
ordered child-action set together. A precommit defect publishes nothing and
returns all reservations; partial publication or refund is invalid.

Only eligible independent initial component Analyst and component D-prime
waves may overlap, at width 2 for canonical OpenAI/OpenRouter hosted providers.
Local and unsupported/conservative providers use width 1. Cross-Component
Analyst, synthesis D-prime, Scrutineer, recovery, selective recomputation, and
all graph-bound work remain serial.

Workers perform transport and pure normalization only. They never mutate
RunKernel, RunState, graph, EvidenceLedger, admission state, recovery state,
FAP/Author state, persistence, or trace. Canonical artifacts, observations,
admission, graph reduction, settlement, and finalization remain on the main
thread. Results reduce by canonical batch index; physical completion order
cannot choose canonical order.

## Installed Phase 5A Transport Contract

The ordinary selected path uses the repository's canonical provider
normalization and strict provider-faithful one-shot transport:

- OpenAI and OpenRouter normalize to hosted width 2;
- Local normalizes to width 1;
- unsupported identities normalize conservatively to width 1 and fail closed
  with zero provider requests;
- each child makes at most one provider request;
- SDK retries are disabled;
- endpoint, provider, and model fallback or switching are forbidden;
- OpenRouter and Local chat requests use repository-owned temperature `0.3`;
- OpenAI Responses requests omit temperature;
- caller-authored temperature is rejected before a provider request.

The transport retains only bounded safe facts: canonical provider/model
identity, return/failure posture, request-attempt facts, response presence, and
non-negative input/output token counts with observed/estimated posture. It does
not retain raw prompts, raw model responses, raw provider payloads,
credentials, private URLs, headers, private logs, or full traces. Transient
output text exists only long enough for main-thread deterministic reduction.

Workers never receive `CostAccumulator`. Provider-attempt accounting remains
separate from product cost accounting. After a response is received, bounded
usage facts are recorded exactly once on the main thread before artifact
reduction, including malformed or empty response-bearing results. Submission,
executor, credential, configuration, and transport failures with no response
add no model cost. Width and physical completion order do not change aggregate
cost accounting.

This transport contract is not provider-routing policy, pricing policy,
capacity characterization, or authorization to add providers or calls.

## Finalization And Blocked Behavior

Admitted graph state continues through ordinary Sufficiency,
FinalAnswerPacket, Author, `RunOutcome`, and CLI-visible output. Graph admission
alone is not product completion. FAP cannot create synthesis, and Author cannot
glue missing or unadmitted component output.

When required semantic work fails or readiness remains blocked, active sibling
leases drain and the path reaches the installed sanitized non-Author terminal
`RunOutcome`. Malformed or unrelated invariant/infrastructure failures remain
errors rather than being relabeled insufficiency.

## Nonproofs And Routing

Offline focused tests prove the bounded architecture and deterministic product
consumption, not live correctness. This contract does not prove arbitrary-query
support, live model quality, provider throughput, rate-limit capacity,
production traffic stability, more than one recovery, permanent mode budgets,
Local or graph-bound parallelism, citation correctness, answer quality, or
product correctness.

Capacity characterization and Specialist work are routed to
[Current Roadmap](../roadmap/CURRENT_ROADMAP.md). This contract neither designs
nor activates the planned Specialist graph and does not execute roadmap work.
