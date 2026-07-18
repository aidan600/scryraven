# RunKernel Post-Discovery Acquisition Control

Status: current
Authority: canonical:runkernel-post-discovery-acquisition-control
Default-read: yes
Applies-to: post-discovery source-obligation acquisition proposals, capability decisions, provider-neutral work orders, routes, execution, terminal receipts, and custody authorization
Does-not-authorize: initial DISCOVER redesign, live calls, provider-failure retry, Focused Extract product activation, Map selection, Crawl custody, general Deep, or downstream evidence/final authority
Verified-against-runtime: RUNKERNEL-ACQUISITION-CONTROL-FOUNDATION-01 phase implementation
Update-trigger: change to post-discovery acquisition ownership, contracts, RunKernel transitions, guarded PRODUCT execution, capability derivation, operation identity, or custody authorization

## Purpose And Boundary

RunKernel is the canonical controller for post-discovery acquisition tied to a
current AnswerContract source obligation. Workers and deterministic product
surfaces may propose a need, but a proposal is advisory candidate state. It is
not a tool choice, provider choice, work order, execution grant, evidence
admission, or source-obligation result.

This owner begins after candidate or explicit-root facts exist. Initial
DISCOVER planning, QueryPlan, ProviderPlan, retrieval scheduling, and provider
selection remain under their existing owners. The direct selective page-fetch
work inside `core.pipeline` is also not migrated or proved by this foundation;
it remains a DISCOVER-internal path outside this document's installed
source-obligation control claim. A future exact-URL/final-custody checkpoint
must either migrate each genuinely product-consumed exact-URL path or state its
separate ownership explicitly.

The installed proof is offline. The ordinary source-custody composition is
default-disabled, `RunConfig.enable_ordinary_live_source_custody` and
`RunConfig.enable_ordinary_live_main_runkernel_coverage` default to false, and
the default CLI exposes no activation for them. No live provider, model,
search, fetch/read, map, crawl, or retrieval call is authorized by this
architecture.

## Exclusive Ownership

| Owner | Installed responsibility | Explicitly does not own |
| --- | --- | --- |
| RunKernel | proposal admission; canonical acquisition-control state; action authorization; accepted capability, work-order, route, execution, terminal, deduplication, exhaustion, active-slot, and custody-authorization state | capability heuristics outside the bounded evaluator; provider selection; transport; evidence, citation, Sufficiency, FAP, Author, or answer authority |
| `core.acquisition_control` | immutable post-discovery contracts; current lineage snapshot; deterministic provider-neutral capability derivation; operation identity; hard-bound derivation; typed terminal-receipt construction | provider catalog, provider availability, provider preference, transport, retries, or downstream authority |
| `core.routing` | provider compatibility and eligibility; code-owned provider order; operation, variant, and output selection; route-time alternative; typed route blocks | acquisition need, material-shape judgment, transport failure fallback, or custody |
| `core.authorized_acquisition_runtime` | sequencing executors for authorized actions and the only guarded PRODUCT call to `dispatch_acquisition()` | canonical state, capability policy, provider policy, or downstream custody meaning |
| `core.acquisition_adapters` | low-level `AcquisitionRequest` construction/validation, one selected-provider transport, and bounded normalization | RunKernel state, capability or provider selection, fallback, evidence admission, or final authority |
| ordinary orchestration | request the next RunKernel action, invoke the named executor, submit the observation, and propagate terminal state | capability tables, provider selection, semantic material-shape policy, URL ranking, Map-to-Crawl rules, retry, or fallback |
| existing custody owners | `FetchReadContentPacket`, `SanitizedContentReference`, and EvidenceLedger custody reduction after an exact READ custody authorization | acquisition capability, route, transport, source-obligation satisfaction, citation, or final authority |

The low-level `dispatch_acquisition()` remains intentionally usable without a
RunKernel in typed-runtime and validation tests. Ordinary PRODUCT code reaches
it only through `execute_authorized_acquisition_work_order()`, which proves the
current authorization and state immediately before mechanical dispatch.

## Installed Authority Chain

```text
nonauthoritative AcquisitionNeedProposalV1
-> RunKernel ACQUISITION_CAPABILITY_DECIDE authorization
-> deterministic AcquisitionCapabilityDecisionObservationV1
-> RunKernel reduction
-> RunKernel ACQUISITION_WORK_ORDER_ADMIT authorization
-> provider-neutral AcquisitionWorkOrderV1
-> RunKernel reduction and one active obligation slot
-> RunKernel ACQUISITION_ROUTE authorization
-> core.routing ProviderRouteDecision
-> AcquisitionRouteObservationV1
-> RunKernel route reduction
-> RunKernel ACQUISITION_EXECUTE authorization
-> guarded PRODUCT executor
-> mechanical acquisition adapter
-> AcquisitionExecutionObservationV1
-> RunKernel execution reduction
-> RunKernel ACQUISITION_TERMINAL_REDUCE authorization
-> AcquisitionTerminalReceiptV1 and active-slot release
-> RunKernel ACQUISITION_CUSTODY_CONSUME authorization, when licensed
-> AcquisitionCustodyAuthorizationV1
-> existing custody consumer
```

Each action binds its expected observation type. Reduction revalidates the
canonical predecessor and recomputes deterministic outputs where applicable.
A work order alone is not executable, a completed route alone is not
executable, and mismatched or stale revisions are not executable.

## Contract Postures

### `AcquisitionNeedProposalV1`

The proposal binds run/request identity, the current AnswerContract,
source-obligation and component revision, requested material shape, exact
candidate/URL/root facts, optional bounded focus and domain/path scope, prior
receipts, and an optional advisory capability. Its fixed producer posture is
`nonauthoritative_need_proposal`.

Provider, preference, operation, variant, output, availability, adapter, and
transport identity are forbidden. Evidence admission, source/citation
authority, obligation satisfaction, Sufficiency, FAP, Author, answer text, and
executable free-form tool instructions are also forbidden. Unknown fields and
authority-shaped nested fields fail closed.

### `AcquisitionCapabilityDecisionObservationV1`

The deterministic evaluator records the proposal ref, independently derived
capability, advisory match status, exact prerequisite booleans, material-shape
interpretation, operation identity, terminal decision status, and typed block.
It records that provider availability and mode/complexity were not consulted.
An advisory conflict blocks with `advisory_capability_conflict`; the proposal's
capability is never copied into authority.

### `AcquisitionWorkOrderV1`

An accepted decision may become one provider-neutral work order with exact
contract/component/obligation lineage, selected URL or root facts, bounded
focus and path/domain scope, code-owned hard limits, parent job refs, operation
identity, and the current routing-policy ref. Its fixed posture is
`acquisition_execution_only`. It contains no selected provider, adapter, or
downstream authority.

### Route, execution, terminal, and custody records

`AcquisitionRouteObservationV1` is the first post-discovery control contract
that may name a selected provider. It binds the work order, completed
`ProviderRouteDecision`, exact routing policy, boolean availability snapshot,
and selected-or-blocked result.

`AcquisitionExecutionObservationV1` binds the exact work-order/route pair,
execution result and artifact refs, call counts, terminal status, and typed
failure/block. It fixes provider-failure fallback, capability switching, and
downstream authority to false.

`AcquisitionTerminalReceiptV1` records one completed, failed, or blocked
operation and releases its source-obligation active slot. Retrying a terminally
failed or blocked identity is unlicensed and the operation is exhausted.

`AcquisitionCustodyAuthorizationV1` is a separate, one-time permission for the
named custody consumer. This foundation authorizes it only for a completed
READ receipt with current AnswerContract, component, and source-obligation
lineage. It grants no downstream authority.

## Canonical State And Guards

RunKernel's `runkernel_acquisition_control_state_v1` owns:

- proposals, capability decisions, work orders, routes, execution
  authorizations, and execution observations by immutable identity;
- one active operation per source obligation;
- terminal receipts by operation identity;
- exhausted operation identities;
- custody authorizations by receipt; and
- a bounded event history plus fixed no-fallback/no-capability-switch posture.

Before capability admission or execution, RunKernel reconstructs current
pre-acquisition lineage from the accepted AnswerContract and
SearchExecutorHandoff. The snapshot has no source-satisfaction authority.
Stale contract, component revision, source-obligation, or prior-receipt lineage
blocks. Work-order routing-policy drift blocks. The guarded executor also
requires the exact canonical work order, exact selected route, exact active
execution authorization, current authority-snapshot digest, active source-
obligation slot, no terminal receipt, and an unexhausted operation.
The execution authorization is a one-use RunKernel-owned claim consumed in the
final pre-transport callback, after the existing cap marker and before the
provider callable. A second claim or execution authorization is rejected before
transport. If contract, component, obligation, or routing-policy lineage
supersedes an admitted work order before execution, a typed terminal
work-order invalidation receipt releases and exhausts the old identity so the
current lineage is not stranded behind its active slot.

Operation identities are deterministic:

| Capability | Identity facts beyond contract/component/obligation lineage |
| --- | --- |
| `READ` | selected candidate digest plus normalized exact URL, or a controller-derived explicit-known-URL digest plus that normalized URL |
| `FOCUSED_EXTRACT` | sorted normalized URL set plus bounded-focus digest |
| `MAP_SITE` | normalized exact site root |
| `CRAWL_SITE` | normalized root plus digest of allowed/excluded domains and path scope |

The controller permits no recursive invocation, fan-out, post-failure provider
switch, or post-failure capability switch.

## Deterministic Capability Status

| Need facts | Derived result | Current PRODUCT disposition |
| --- | --- | --- |
| one packet-bound selected URL with `full_page_or_unknown` or `ordinary_single_page`, or one provider-neutral `explicit_known_url` with no manufactured candidate identity | `READ` | accepted when all current-lineage, hard-bound, duplicate, active-slot, and exhaustion checks pass |
| one to twenty exact URLs, exact obligation/component-bound focus, and a narrow-section/field/table/rule shape, or a prior too-broad/truncated READ | `FOCUSED_EXTRACT` | recognized, then terminally blocked with `focused_extract_requester_not_installed` |
| exact HTTP(S) site root and `site_topology` | `MAP_SITE` | recognized, then terminally blocked with `map_candidate_reentry_not_installed` |
| exact root, allowed root domain, bounded path scope, explicit multi-page need, and `bounded_multi_page` | `CRAWL_SITE` | recognized, then terminally blocked with `crawl_page_custody_not_installed` |
| `premium_sequential_acquisition` | neutral premium-sequential sentinel | terminally blocked with `premium_sequential_acquisition_not_licensed` |

Provider availability, provider features, requested mode, complexity, weak
corpus, and desire for more detail never determine capability. Scrutineer Deep
is a separate existing bounded consumer and is unchanged.

Focused Extract was not accelerated in this foundation. The current ordinary
repository supplies post-READ anchor hints for bounded text selection, but no
pre-acquisition producer supplies the complete exact URL/focus/current-lineage/
material-shape proposal required by the controller. No producer, model call,
ranking rule, or prompt redesign was invented.

Map and Crawl are recognized only far enough to produce their exact durable
blockers. No Map or Crawl route, transport, topology selection, candidate
manufacture, multi-page custody, or EvidenceLedger meaning change is installed.

## Routing Policy And Execution Boundary

`core.routing` exposes a stable code-owned policy ref with revision
`runkernel_post_discovery_acquisition_control_01`, selection algorithm
`first_reachable_code_owned_preference_v1`, and a digest over the provider
catalog and post-discovery preference table. The work order, route
authorization, route observation, and execution authorization bind that ref.

Current post-discovery preferences are Linkup Fetch then route-time Tavily
Extract for READ; Tavily Extract for Focused Extract; Tavily Map for Map; and
Tavily Crawl for Crawl. Only READ currently reaches routing in PRODUCT. An
unavailable preferred provider may yield a route-time alternative before
dispatch. Transport failure never causes fallback.

The policy is not configurable through TOML, YAML, JSON, a database,
environment, prompt, provider preference, or user option. Provider ordering is
not URL relevance.

## Ordinary Selected-Candidate READ

When the explicitly enabled ordinary source-custody composition runs, the
installed path is:

```text
SearchResultCandidatePacket selected candidate
-> packet/current-lineage-bound READ proposal
-> RunKernel capability decision and reduction
-> RunKernel-admitted provider-neutral READ work order
-> RunKernel route authorization
-> core.routing Linkup Fetch or route-time Tavily Extract decision
-> RunKernel route reduction
-> RunKernel execution authorization
-> execute_authorized_acquisition_work_order()
-> exactly one mechanical adapter dispatch
-> RunKernel execution and terminal reductions
-> RunKernel READ custody authorization
-> existing FetchReadContentPacket
-> existing EvidenceLedger custody reduction
```

The guarded executor invokes the existing `RunCapPolicy` fetch/read marker
exactly once immediately before transport. The existing rendering posture,
truthful requested/attempted/provider-reported URL lineage, Tavily selected-URL
binding, unknown content-type/status posture, normalized bounds, and no-failure-
fallback behavior remain intact.

The custody authorization is rechecked immediately before packet creation.
Neither the controller nor its artifacts grant evidence, citation,
source-obligation satisfaction, component coverage, Sufficiency, FAP, Author,
social, or final-answer authority.

## Next Checkpoints

The explicit maintainer sequencing decision installed this foundation before
the previously active final-custody checkpoint, because final custody must not
converge around multiple post-discovery decision/execution authorities.

The sole active next checkpoint is
[`EXACT-URL-ACQUISITION-AND-FINAL-CUSTODY-CONVERGENCE-01`](../roadmap/EXACT_URL_ACQUISITION_AND_FINAL_CUSTODY_CONVERGENCE_01.md).
It must converge genuinely product-consumed DISCOVER and READ exact-URL
acquisition and custody, and may activate Focused Extract only through a real
exact producer and existing or explicitly bounded custody semantics. It must
not absorb Map selection or Crawl page custody.

Map topology selection follows separately in
[`SITE-TOPOLOGY-SELECTION-AUTHORITY-01`](../roadmap/SITE_TOPOLOGY_SELECTION_AUTHORITY_01.md).
Crawl page custody has a distinct owner and rollback boundary and therefore
follows under
[`CRAWL-PAGE-CUSTODY-CONVERGENCE-01`](../roadmap/CRAWL_PAGE_CUSTODY_CONVERGENCE_01.md).

## Nonproofs

This foundation proves the complete selected-candidate READ authority chain in
offline product-path composition. It does not prove default CLI activation,
live provider behavior, provider quality, final-custody convergence, Focused
Extract product use, Map selection, Crawl custody, general Deep, initial
DISCOVER control, evidence correctness, source-obligation satisfaction,
Sufficiency, FAP, Author, answer quality, or complete-app correctness.
