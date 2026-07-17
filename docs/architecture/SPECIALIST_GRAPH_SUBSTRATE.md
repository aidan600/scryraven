# Specialist Graph Substrate

Status: current
Authority: canonical:specialist-graph-substrate
Default-read: no
Applies-to: generic Specialist proposals, registry resolution, execution policy, work, results, scheduling, and D-prime consumption
Does-not-authorize: additional product capabilities, calculator scope expansion, provider or model calls, retrieval, recursion, parallel Specialist work, admission, FAP, Author, or live validation
Verified-against-runtime: 72251c126770e41a9b52105d860154d1cfef811b
Update-trigger: merged change to Specialist proposal, registry, policy, work, result, scheduling, or validator-consumption contracts

## Responsibility

This document owns the installed generic Specialist graph substrate. Installed
state is summarized in [ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md),
phase order belongs to [Current Roadmap](../roadmap/CURRENT_ROADMAP.md), and the
ordinary bounded consumer belongs to
[Multi-Component Synthesis Runtime Architecture](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md).
The one installed calculator product belongs to
[Quantitative Specialist Product Activation](AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md).

The substrate lets an existing semantic role propose a bounded need, lets
RunKernel bind that proposal to exact current authority, resolves an explicitly
registered deterministic capability under an injected execution policy, runs
one governed work item, and routes its bounded result through the appropriate
D-prime input. It does not make a Specialist result admitted truth.

## Installed Contract

The installed sequence is:

```text
exact parsed Specialist proposal candidate from one role response
-> generic schema/envelope/safety validation
-> capability-specific exact contract-instance validation when installed
-> RunKernel current artifact, input, target, registry, and policy binding
-> registry resolution plus execution-policy decision
-> Scheduler V3 Specialist lease in a separate compatibility pool
-> either one registered deterministic capability execution or a typed nonexecution disposition
-> immutable proposal disposition and optional result identity plus validator lifecycle
-> one `specialist_need_handoff` component or synthesis D-prime input
-> ordinary RunKernel graph/admission flow
```

Component Analyst, Cross-Component Analyst, and full Scrutineer may emit the
same optional proposal shape. The nested mapping is candidate JSON only, not
work authority, and must explicitly carry
`schema_version: specialist_need_proposal_v1`. Generic S0 requires the exact
supported version and exact generic envelope, including a target containing
only `target_kind` and `target_key`; unknown fields and top-level target aliases
are rejected rather than discarded. No version, target, posture, recursion
depth, or parent value is synthesized or defaulted. A proposal names a bounded
question, capability requirement, optional capability hint, exact target,
input/output schema refs,
input artifact refs, assumptions, caveats, nonclaims, advisory budget posture,
and a nonrecursive parent posture. An optional capability-generic
`capability_request` is canonical-JSON bounded to 16 KiB, depth 6, 64 mapping
keys, 64 list items, and 1,000 characters per string. It rejects raw/private
material, provider/model/search/retrieval fields, executable expressions, and
caller-authored graph, lease, admission, FAP, or Author authority.

The parser preserves the exact candidate only in transient worker/driver scope;
it is omitted from the retained semantic-role artifact. Generic S0 owns schema,
envelope, bounded JSON, raw/private-material rejection, and authority
exclusions. An installed capability owner may then require a stricter exact
proposal instance without moving its operator or source semantics into S0.
RunKernel alone admits the validated proposal, binding it to the originating
completed role action and artifact, exact input digest, current AnswerContract,
current component or graph target revision, registry digest, and
execution-policy digest. Caller-supplied authority cannot replace these
canonical bindings.

## Registry And Execution Policy

The registry is capability-generic. Each descriptor has a stable capability
ID, version, requirement, input/output schema refs, deterministic resource and
executor classes, and a descriptor digest. A candidate capability hint is
advisory; resolution deterministically selects from compatible enabled
descriptors under policy. Unknown, disabled, or schema-incompatible
capabilities fail closed with a typed proposal posture.

The generic default registry and policy remain closed. The ordinary CLI/UI
product path separately composes the fixed S1 registry and policy containing
only `specialist.source_bound_calculation` version `1.0.0`. Generic substrate
tests still inject inert deterministic capabilities to prove reuse, and the
Scheduler/driver contain no calculator-specific capability branch.

That product additionally supplies a repository-owned model-visible proposal
contract only to ordinary component and Cross-Component Analyst inputs. Its
declarative schema facts are shared with product validation; the generic
proposal schema, registry, scheduler, and handoff remain the existing consumers
and are adapted rather than shadowed. D-prime, selective, Scrutineer, and
nonqualifying inputs do not acquire the product contract.

## Scheduler V3 And Budget Separation

Scheduler V3 is an upgrade of the existing RunKernel scheduler and is selected
when a Specialist registry and execution policy are injected into an ordinary
bounded run. The fixed ordinary CLI/UI composition supplies the S1 product
registry/policy; generic closed-default and no-need behavior remains
V2-compatible.

Specialist work uses its own compatibility pool:

- limit `0` or `1` per run;
- serial, main-thread execution only;
- maximum one in flight;
- no recursion;
- no provider transport or model request;
- no token or model-cost accounting;
- no consumption of the five semantic role caps or their 22-unit envelope.

Canonical ready-work ordering gives eligible component Specialist work priority
before a later synthesis need. The one unit cannot be spent twice: later
optional exhaustion remains visible and nonblocking, while later required
exhaustion safely blocks through the existing lifecycle.

The Specialist work node binds the accepted proposal, canonical target,
contract and graph refs, capability descriptor, exact RunKernel authorization
action, batch/lease lineage, and Specialist budget ref. It retains only the
bounded-input digest, input-schema ref, lineage refs, and reconstruction ref;
the component or synthesis input packet itself is not retained.
Grant, cancellation, dispatch, staleness, failure, blocked, contested, and
completion postures remain RunKernel-governed and terminally accounted.

## Disposition, Result, And Validator Lifecycle

An invalid candidate is never appended as a proposal and receives no work node,
ready work, lease, batch, dispatch, adapter invocation, result, or D-prime
handoff. RunKernel retains only a bounded rejection receipt containing safe
schema posture, required/optional or unclassified fail-closed posture, a safe
local target when valid, one rejection category, and authorized contract digest
refs. The malformed candidate and malformed values are not retained. Required
rejections block dependent work through the existing scheduler terminal;
optional rejections contribute no authority and allow only independently
supported ordinary work to continue. Missing or invalid posture is not inferred
as optional.

Every admitted, policy-denied, capability-denied, or target-denied proposal
receives an immutable sibling disposition. The
disposition preserves the original proposal digest, origin and exact target,
required/optional posture, capability and policy resolution, availability,
assumptions, caveats, nonclaims, and any typed nonexecution reason. Availability
postures are result available, unavailable by policy/capability/target/budget,
failed, blocked, or contested. Optional pool exhaustion creates no second
lease, adapter call, model call, or accounting unit; required exhaustion still
blocks the ordinary path.

A Specialist result contains only bounded output, assumptions, caveats,
blockers, confidence and execution posture, exact work/proposal/capability
lineage, and explicit zero-authority declarations. It has no component or
synthesis admission, SemanticObservation, ComponentCoverage, Sufficiency,
FinalAnswerPacket, Author, citation, or source-obligation authority.

Disposition and result identities are immutable. Validator-consumption fields
carry a separate lifecycle on the disposition, unified handoff, and any result:
pending, consumed by component D-prime, consumed by synthesis D-prime,
contested, or rejected. Stable refs and identity digests do not include that
mutable lifecycle.

Component and synthesis D-prime receive Specialist material only under the
single top-level `specialist_need_handoff` namespace. It carries either a
bounded result or the typed reason the proposed need was unavailable. Only the
absence of a proposal omits the handoff. Ordinary nominated claims, evidence,
component refs, graph refs, and admitted input refs remain unchanged. RunKernel
independently rederives the current D-prime role, action, artifact, target, and
exact handoff-bearing input digest before allowing exactly-once consumption;
caller-supplied route or validation status is not trusted.

For the installed quantitative capability, the result also carries exact
source-literal binding, deterministic parser/operator/unit/precision facts,
and claim alignment. Synthesis calculation lineage proves the literal through
the admitted component claim to the same underlying current component evidence.
Only the applicable D-prime may decide whether those facts support the nominated
claim; successful arithmetic cannot validate itself.

## Scrutineer Boundary

S0 permits automatic remediation only for an exact current synthesis leaf.
The completed result is attached to that leaf, prior D-prime/admission
authority is cleared, and the graph requires fresh synthesis D-prime validation
and a fresh full Scrutineer pass. Component, edge, subgraph, graph, and
whole-case Scrutineer targets are retained as typed rejected or unsupported
proposals. They do not trigger structural rewrite, broad recomputation, or
silent fallback.

## Privacy And Authority Boundaries

Retained Specialist artifacts are bounded projections only. Immediately before
dispatch commitment, the driver reconstructs the exact component or synthesis
input from current canonical owners and verifies its digest. Reconstruction
failure cancels and refunds the exact reservation once, leaves zero Specialist
spent units, publishes no Specialist execution action, creates no result, and
never starts the adapter. Both optional and required proposals receive exactly
one failed disposition and unified handoff. The optional handoff remains visible
to D-prime and nonblocking. The required handoff remains pending and unconsumed
because D-prime does not run; Scheduler V3 reaches
`blocked_required_specialist_work` before the existing safe non-Author terminal.
The transient packet exists only in
driver-local execution scope. It is absent from RunKernel, scheduler
leases/batches/actions, the Specialist work plane, observations, graphs, logs,
and traces. Raw prompts,
raw model or provider payloads, private logs, full traces, database rows,
caches, secrets, and private artifacts are neither accepted nor retained.
Capability adapters stay in injected runtime scope and are not serialized into
RunKernel state.

The S1 model-visible proposal contract, complete source catalogs, source
material, exact parsed candidate, and full evidence candidate records follow
the same nonretention boundary. After scheduler-driven semantic work becomes
terminal, the in-memory exact role-packet context is released and only already
authorized packet, registry, and policy digests remain. Delayed D-prime
consumption re-proves the current completed action/artifact, target, exact input
digest, and safe handoff digest without retaining the source-bearing role
packet. Bounded retained refs may preserve only the safe identity and source-
posture facts needed for exact result validation.

The ordinary Cross graph boundary applies unconditional input reproof before
any quantitative proposal can enter graph state. An exact transient packet may
be checked directly; RunKernel rederives from its current scheduler-owned
component Analyst packets. Missing authority fails closed, and this temporary
argument threading creates no new Specialist, scheduler, graph, or retained
packet authority.

The substrate grants no provider, model, search, fetch/read, retrieval, or
publication authority. It introduces no hidden fallback, recursive Specialist
proposal, parallel Specialist execution, or arbitrary-query support.

## Nonproofs

Offline tests prove generic contract reuse, provenance-labeled partial lineage
for observed fields, ordinary bounded quantitative consumption, closed generic
defaults, typed rejection, and deterministic scheduling. They do not prove
complete source lineage, live calculator correctness, answer quality, broad
quantitative reasoning, additional capability coverage, arbitrary-query
support, or useful hosted/Local capacity.
