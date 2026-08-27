# RunKernel Component DAG, Scheduling, And Concurrency

Status: current
Authority: canonical:component-dag-scheduling-concurrency
Default-read: no
Applies-to: ComponentWorkGraph, semantic-work scheduling, leases, batches, and runtime concurrency
Does-not-authorize: new providers, adaptive width, Local parallelism, graph-bound parallelism, or mode-budget selection
Verified-against-runtime: 540141acaaaf041bda303edd62211dd6a11958bc
Update-trigger: merged change to graph, scheduler, lease, dispatch, or concurrency behavior

## Responsibility

This document owns the current component DAG, scheduling, lease, batch, and
concurrency contract. Role and synthesis semantics belong to
[Multi-Component Synthesis Runtime Architecture](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md),
and integrated authority flow belongs to
[Run-Contract Semantic Loop](RUN_CONTRACT_SEMANTIC_LOOP.md).

ComponentWorkGraph V1 is installed for
`ordinary-bounded-multicomponent-factual-synthesis-v1`. The V0 graph
compatibility implementation has been retired; its historical provenance is not
the ordinary executor, scheduler, or answer path.

## Graph Contract

Multi-component work is a RunKernel-owned acyclic dependency graph, not a
caller-authored checklist. Component and synthesis nodes are first-class,
identity-bearing, revision-bound, challengeable graph objects. The graph may
represent direct component output, component-to-synthesis and
synthesis-to-synthesis dependencies, subset synthesis, multiple synthesis
groups, bounded layered synthesis, blockers, stale revisions, challenges, and
recovery state.

The installed bounds are:

- 1–5 component nodes;
- 1–4 synthesis nodes;
- maximum synthesis depth 2;
- at most one missing-component recovery and graph/AnswerContract amendment;
- no recovery beyond the five-component cap.

Supporting-premise nodes and user-facing answer-target nodes have distinct
support matrices. A supporting premise requires exact direct depth-zero
coverage, although it may later be an exact premise for an inferred target.
An answer target may be direct-only, inferred-only, or direct-or-inferred as
accepted by its contract. Fast/Balanced admit semantic depth 1; Deep admits
depth 2. Recovery generation is a separate SearchOS policy: Fast 0, Balanced 1,
Deep 2.

Boundary B graph transition authority comes only from the existing
ContractAmendment application. Graph V1 retains identity, advances revision,
adds the admitted searched-premise node, binds exact target/dependency changes,
and derives an affected-only closure. Fresh Cross-Component Analyst and
synthesis D-prime work runs only for that closure; unaffected current admitted
synthesis is carried forward under exact RunKernel authority. Replay lookup
precedes stale graph/current-state rejection and cannot create a second
transition, resynthesis round, lease, or canonical reduction.

An empty edge set means no edge is admitted; it does not prove semantic
independence. Structural edges come from accepted request structure. The
Cross-Component Analyst proposes semantic edges and synthesis. Synthesis
D-prime validates nominated relations. RunKernel alone admits canonical graph
state.

`AnswerContract` and `ComponentWorkGraph` remain distinct:

```text
AnswerContract component = an obligation the run owes the user
ComponentWorkNode = the governed lane for one obligation
synthesis node = subordinate derived reasoning used to fulfill obligations
```

A synthesis node does not automatically become an AnswerContract component.

## Canonical Ready Work

RunKernel derives ready semantic work from the current accepted
AnswerContract, graph revision, admitted artifacts, recovery state, selective
closure, exact role caps, and active leases. Callers do not nominate the next
role, logical key, packet, provider class, width, or work item.

Scheduler V2 batch membership is the contiguous prefix of canonical ready-work
order that:

- has one role and one parallel class;
- fits the role's remaining cap and the compatibility envelope;
- fits the provider-derived effective width;
- preserves distinct work, component, packet, and logical identities; and
- stops at the first incompatible intervening item.

The scheduler never skips intervening work to create a larger batch, never
mixes roles in a batch, and never introduces an all-Analyst or all-D-prime stage
barrier. Physical completion order cannot choose canonical work order.

Scheduler V3 is the same RunKernel scheduler with a separate deterministic
Specialist compatibility pool. The fixed ordinary CLI/UI product composition
injects the S1 quantitative registry and policy; generic closed-default and
no-need runs remain V2-compatible. Specialist work is always serial, maximum
one in flight, nonrecursive, and excluded from the active direct-path semantic
role caps, provider transport accounting, and the 17-unit active envelope.
Canonical ready-work ordering gives an eligible component calculation priority
over a later synthesis calculation for the one-unit pool.

The quantitative model-visible proposal contract and source catalogs remain
transient role/adapter inputs. RunKernel binds the accepted proposal and exact
current input digest, but scheduler ready work, leases, batches, actions, and
canonical graphs do not retain the contract, full catalogs, or source material.

Every full Cross graph construction or reproof has exact packet-reconstruction
authority. The ordinary path may pass the exact transient Cross packet.
RunKernel reads only its current in-memory scheduler context, requires one
packet per current component, checks current IDs/revisions/digests and the
existing initialization or recovery packet-digest authority, and independently
reconstructs the complete Cross packet. Missing or inconsistent authority fails
before graph reduction; the temporary `deepcopy` is not a new state field,
projection, action, observation, cache, lease fact, or retained packet.

## Lease And Budget Authority

Every semantic call carries an exact RunKernel lease bound to current work,
input packet digest, role, logical evaluation key, graph/contract revision, and
the relevant recovery or selective-closure lineage. A lease cannot be rebound
to different work or a new authority revision.

The active direct-path envelope is derived from the ordinary role caps:

| Role | Unit cap |
| --- | ---: |
| Component Analyst | 5 |
| Cross-Component Analyst | 2 |
| Synthesis D-prime | 8 |
| Scrutineer | 2 |

The 17-unit active parent total is the sum of that mapping; callers cannot author
a second total. A retained ComponentDprime compatibility cap grants no ordinary
work. Grant moves units from remaining to reserved; dispatch moves them to spent.

Predispatch cancellation may return an exact granted reservation once. For a
V2 batch, cancellation returns the full still-granted batch atomically; partial
refund is invalid. Postdispatch transport failure, output failure, artifact
failure, and stale-result rejection remain spent. Returned units are cumulative
audit facts, not a fourth live allocation bucket.

For required Specialist work, predispatch input-reconstruction failure returns
the exact V3 reservation, records one failed disposition and unified handoff,
and then reaches `blocked_required_specialist_work` with zero active leases and
zero Specialist spent units. Optional reconstruction failure records the same
availability facts without blocking the ordinary path.

AnswerContract, graph, recovery-target, and selective-closure reducers derive
lease invalidation from the independently validated candidate state. Affected
granted work is cancelled and returned; affected dispatch-committed work is
stale-rejected and remains spent; unrelated leased work remains current. A
caller-authored transition label or digest cannot create cancellation
authority.

Completed and blocked scheduler states require zero active leases. Completion
with either a granted reservation or dispatch-committed lease is a non-mutating
error. Required-work exhaustion reaches ordinary Sufficiency/FAP handling and
the safe blocked terminal only after active sibling work drains.

## Atomic Batch Lifecycle

RunKernel atomically grants one exact batch and all of its leases. Before any
mutation, the main thread reconstructs and validates every private child
descriptor against the granted work.

Dispatch then atomically:

1. verifies that the batch is still the current contiguous ready prefix;
2. commits every reservation to spent;
3. binds every descriptor to its exact lease and logical key; and
4. publishes the complete contiguous ordered child-action set.

No child action or logical key becomes visible before that commitment. A
precommit defect publishes no child action, consumes no logical key, and
returns the complete batch. After commitment, failures remain spent and all
submitted siblings are drained before terminalization.

## Installed Concurrency

The canonical provider normalizer derives only these execution classes:

| Configured provider class | Backend class | Effective width |
| --- | --- | ---: |
| OpenAI or OpenRouter | `hosted_api` | 2 |
| Local OpenAI-compatible | `local_openai_compatible` | 1 |
| Unknown or unsupported | `conservative_unknown` | 1 |

Width 2 applies only to eligible independent initial Component Analyst waves.
Local and unknown/conservative execution use width 1. Cross-Component Analyst,
synthesis D-prime, Scrutineer, recovery, selective Cross-Component Analyst,
affected synthesis validation, and all graph-bound work remain serial.

The width-2 hosted posture is a compatibility cap, not measured provider
capacity, adaptive rate-limit policy, user-configurable concurrency, or routing
authority. The retired Scheduler V1 schema is not accepted; current scheduling
uses V2 or V3.

## Worker Boundary And Determinism

Workers perform configured synchronous transport and pure normalization only.
They receive no RunKernel, mutable RunState, graph, EvidenceLedger, admission
state, recovery authority, `CostAccumulator`, FAP/Author state, persistence
writer, or trace writer.

Canonical artifacts, identities, digests, role observations, lease settlement,
component admission, graph reduction, recovery, selective recomputation,
Sufficiency, FAP, Author, persistence, trace mutation, and response-bearing
cost recording remain on the main product thread. Results are collected by
canonical batch index, so transport completion order cannot alter admission,
graph, accounting, or answer order.

Provider-attempt accounting is separate from product cost accounting. A
provider request attempt may be spent without a response; model cost is
recorded only from response-bearing bounded usage facts, exactly once on the
main thread before artifact reduction.

## Mode Doctrine

Mode may change bounded budgets. Mode does not change semantic authority,
admission ownership, truth standards, lease lineage, or deterministic reduction
order. This contract does not select permanent Fast/Balanced/Deep width, depth,
or semantic-call budgets.

## Nonproofs

This contract does not prove live provider capacity, adaptive concurrency,
Local parallelism, graph-bound parallelism, arbitrary-query scheduling, live
quantitative correctness, broad Specialist capability quality, or product
correctness. It does not authorize new providers, endpoint changes, mode-budget
selection, additional product capabilities, or live calls.

Proposal semantics and historical V0 rationale remain available in
[Cross-Component Analyst Workbench](CROSS_COMPONENT_ANALYST_WORKBENCH.md), but
that history does not override this installed execution contract.
