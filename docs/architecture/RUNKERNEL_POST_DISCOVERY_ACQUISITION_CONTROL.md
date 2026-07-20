# RunKernel Post-Discovery Acquisition Control

Status: current
Authority: canonical:runkernel-post-discovery-acquisition-control
Default-read: yes
Applies-to: ordinary post-DISCOVER result-reference handoff plus post-discovery source-obligation acquisition proposals, capability decisions, provider-neutral work orders, routes, execution, terminal receipts, and custody authorization
Does-not-authorize: initial DISCOVER redesign, live calls, provider-failure retry, Focused Extract product activation, Map selection, Crawl custody, general Deep, or downstream evidence/final authority
Verified-against-runtime: 39573c29bc2394e798e507fc795d70197da20f10
Update-trigger: change to post-discovery acquisition ownership, contracts, RunKernel transitions, guarded PRODUCT execution, capability derivation, operation identity, or custody authorization

## SEARCHOS-READ-SOURCE-AND-CUSTODY-01 Architecture Checkpoint

Mode: BUILD

Outcome: the ordinary main RunKernel consumes the immutable revision-1
post-DISCOVER packet, derives exact current material-need bindings, obtains one
strict subordinate SearchJudgment READ assessment for each policy-admitted
eligible source-obligation slot, and—only for a valid `REQUEST_READ_PAGE`
nomination—reuses the installed acquisition chain through canonical
EvidenceLedger custody. The phase ends at custody.

The implementation classification is:

| Surface | Current owner and ordinary consumer | Action |
| --- | --- | --- |
| Revision-1 candidate handoff | RunKernel ordinary handoff; main pipeline immediately after initial DISCOVER | ADAPT to carry the already-accepted active AnswerContract ref while preserving revision 1 and reference-only candidate records |
| Candidate-to-need lineage | discovery occurrence store, current QueryPlan, active SearchWorkPlan, and active AnswerContract; subordinate READ assessor | UPGRADE with immutable `SelectedCandidateMaterialNeedBindingV1` records derived under RunKernel authorization |
| READ judgment | SearchJudgment model selection facts and the main pipeline | ADAPT as a separate strict subordinate contract; no deterministic answer, repair, fallback, or dependence on the legacy full-SearchJudgment enable flag |
| Acquisition | RunKernel acquisition authority, routing, guarded executor, and adapters | REUSE after an exact binding-backed `AcquisitionNeedProposalV1`; one provider attempt and no post-dispatch provider fallback |
| READ custody | FetchReadContentPacket and EvidenceLedger custody reducers | REUSE in the main RunKernel; same normalized URL reuses one current canonical artifact without duplicate transport |
| Full SearchJudgment input | existing full-judgment input adapter | ADAPT with a phase-owned filtered projection so new READ lineage and custody cannot influence baseline full-judgment decisions |
| Legacy ordinary-live wrappers and flags | compatibility-only child-kernel paths | RETIRE as authority for this feature; they remain compatible but are not consulted by the ordinary main path |

Binding derivation is exact and text-free:

```text
selected candidate
-> every current matching discovery occurrence
-> exact current QueryPlan item
-> exact active SearchWorkPlan component / search requirement / source obligation
-> exact active AnswerContract component
```

Multiple contributors for one normalized URL therefore create multiple
bindings without duplicating the selected candidate. Any stale packet,
contract, plan, contributor, component, requirement, obligation, candidate, or
URL relationship fails closed before a model call.

A source-obligation ID may govern more than one accepted component. The
acquisition snapshot aggregates every current SearchWorkPlan occurrence before
building `source_obligations_by_id`, compares the complete governed descriptor
after removing only component-local lineage, and rejects any semantic conflict.
One canonical obligation ref then lists all associated component refs in
deterministic order. Bindings and assessment slots remain component-specific:
two components sharing one obligation produce two distinct
component/obligation slots that reference the same canonical obligation ref.

The subordinate assessment runs after the revision-1 handoff and before source
recovery or synthesis. A policy-admitted slot with eligible bindings receives
exactly one logical model assessment; a slot with none receives zero. The only
successful decisions are `NO_READ` and `REQUEST_READ_PAGE` with at most one
binding nomination. Transport failure, malformed model output, invalid
nomination, or stale lineage becomes a typed failure and never a deterministic
READ decision.

Eight active eligible slots is the supported checkpoint envelope. Admission is
all-or-nothing: a successful binding state has
`policy_admitted_slot_ids == slot_order` and an empty
`policy_deferred_slot_ids`. A ninth slot raises
`search_judgment_read_assessment_slot_budget_exceeded` before RunKernel issues
the first assessment action. The ordinary run stops there; no partial
assessment, proposal, acquisition, full SearchJudgment, recovery, synthesis, or
Author path executes.

Canonical custody remains visible in EvidenceLedger. At both existing full
SearchJudgment input seams, however, the adapter removes only this phase's
candidate-custody records and observation refs. No fetched text is added to
`all_passages`, Analyst inputs, Coverage, source-obligation satisfaction,
citations, FAP, Sufficiency, Author, answer text, or final-answer authority.

## Purpose And Boundary

RunKernel is the canonical controller for post-discovery acquisition tied to a
current AnswerContract source obligation. Workers and deterministic product
surfaces may propose a need, but a proposal is advisory candidate state. It is
not a tool choice, provider choice, work order, execution grant, evidence
admission, or source-obligation result.

This owner begins only after candidate or explicit-root facts exist and a
separate current material need has been established. Initial DISCOVER planning,
QueryPlan, ProviderPlan, retrieval scheduling, provider selection, ranking, and
candidate selection remain under their existing owners. Ordinary initial
discovery now ranks normalized provider-returned candidate material and performs
zero separate candidate-URL transport. It produces a bounded reference-only
ordinary SearchExecutorHandoff and the canonical SearchResultCandidatePacket;
neither is an acquisition proposal or material need. The historical direct selective fetch
inside `core.pipeline` and its `core.retrieval.fetch_page` / `fetch_url_text`
helpers are retired, not migrated under RunKernel.

The installed proof is offline. Candidate selection supplies URL provenance
only and remains a nontrigger. The ordinary main RunKernel now derives current
material-need bindings and invokes the separate model-owned READ assessment;
only its exact `REQUEST_READ_PAGE` nomination may create the proposal that
enters this controller. Compatibility source-custody flags and the retired
`AG-LIVE-SOURCE-CUSTODY` profile are not consulted. No live provider, model,
search, fetch/read, map, crawl, or retrieval call is authorized by this
architecture.

The initial-discovery selective-fetch retirement remains historically grounded
at runtime/test commit `48a309124764d813cf27081bf5871d5a9612db79`.

## Exclusive Ownership

| Owner | Installed responsibility | Explicitly does not own |
| --- | --- | --- |
| `retrieval.DiscoverySourceResultIdentity` / `retrieval.DiscoveryResultMaterialStore` | immutable provider-result occurrence identity before dedup/chunk/rank and bounded run-local provider material | relevance, selection, fetch/read, evidence, or downstream answer authority |
| RunKernel ordinary discovery handoff | authorize and reduce one exact ref-only revision-1 post-DISCOVER action; retain a bounded canonical projection and canonical packet ref | provider calls, QueryPlan/ProviderPlan policy, ranking, selected-candidate acquisition need, or packet material reconstruction |
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

## Ordinary Result-Reference Handoff

At the immutable initial post-DISCOVER selection, RunKernel authorizes one
`ORDINARY_DISCOVERY_CANDIDATE_HANDOFF` action over exact current QueryPlan,
ProviderPlan, retrieval-action, source-result identity-set, selected-ref, and
selected-candidate-input digests. The resulting packet identity also binds a
digest of the ordered candidate-record digests. The provider calls are already
complete. The
executor builds the ordinary-origin revision-1
`RunKernel.SearchExecutorHandoff` and
`RunKernel.SearchResultCandidatePacket`, then RunKernel rederives and reduces
their compact bindings. Duplicate action replay, stale plan/contract membership,
mutated packet or handoff refs, and raw/private or authority-bearing state fail
closed.

This snapshot follows initial AnswerContract acceptance and SearchWorkPlan /
QueryPlan admission but precedes later source recovery and synthesis. Revision
1 therefore carries the exact active AnswerContract ref at packet level while
candidate records remain provenance-only and do not gain singular component or
source-obligation authority fields. Later recovery occurrence identities do not
mutate it. The ordinary branch uses origin `ordinary_query_provider`, not
`live_search_validation`.

The canonical result projection is ref-only and at most 16 KiB. It retains at
most eight selected source-result refs plus overflow facts and a digest over the
complete selected order, together with the identity-set and packet refs. The
run-local retrieval store, not RunKernel, owns provider material. No provider
text, chunk, embedding, or raw payload enters canonical RunKernel state.
Identity/material bounds are 80 occurrences per run, 4,096 canonical bytes per
identity, 20,000 material characters per occurrence, and 8 contributor refs;
the selected packet retains the existing Fast/Balanced/Deep 8/20/40 cap with an
absolute maximum of 40.

The reduced state explicitly records one packet and the selected count while
keeping provider-call-caused-by-handoff false, acquisition proposal and READ/
Focused Extract work-order creation false, exact-URL cap charge and transport
false, and `urls_fetched` zero. These fields prove a structural selected-
candidate nontrigger; they do not authorize acquisition.

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
| one packet-bound selected URL plus an independently supplied current `full_page_or_unknown` or `ordinary_single_page` material need, or one separately justified provider-neutral `explicit_known_url` need | `READ` | controller accepts when all current-lineage, hard-bound, duplicate, active-slot, and exhaustion checks pass; the ordinary subordinate SearchJudgment assessment is the installed packet-bound producer |
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
Tavily Crawl for Crawl. READ is the only capability with guarded PRODUCT
routing/execution machinery and an ordinary current-material-need producer.
An unavailable preferred provider may yield a route-time alternative before
dispatch. Transport failure never causes fallback.

The policy is not configurable through TOML, YAML, JSON, a database,
environment, prompt, provider preference, or user option. Provider ordering is
not URL relevance.

## Selected-Candidate Nontrigger And Installed READ Judgment

`SearchResultCandidatePacket` is a durable non-evidence candidate handoff before
fetch/read. It is not evidence, not citation-eligible, and does not satisfy
source obligations. A selected candidate, URL presence, provider-material
shortness/absence, weak corpus, complexity, mode, installed adapter, provider
availability, or a general desire for stronger evidence independently produces
no acquisition need.

```text
SearchResultCandidatePacket selected candidate
-> URL provenance only
-> no independent current material need
-> no AcquisitionNeedProposalV1
-> no work order
-> no route
-> no exact-URL cap charge
-> no exact-URL transport
```

The installed ordinary route begins only when the separate subordinate
SearchJudgment assessment establishes an explicit material need:

```text
current binding + model-owned REQUEST_READ_PAGE + selected URL provenance
-> exact packet/current-lineage validation
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

The main ordinary RunKernel is now the product consumer of that route. The
guarded executor, routing policy, one-use RunKernel pre-transport claim,
`RunCapPolicy` marker, rendering posture, requested/attempted/provider-reported
URL lineage, Tavily selected-URL binding, normalized bounds, and no-failure-
fallback behavior remain intact and are exercised by typed-runtime tests.

The custody authorization is rechecked immediately before packet creation.
Neither the controller nor its artifacts grant evidence, citation,
source-obligation satisfaction, component coverage, Sufficiency, FAP, Author,
social, or final-answer authority.

## Roadmap And Target-Architecture References

The acquisition-control foundation remains installed and retained: RunKernel
owns post-discovery decision and execution authority, truthful discovery-result
candidate handoff remains installed, selected-candidate presence remains a
nontrigger, and the independent subordinate READ judgment now consumes the
ordinary packet and current material-need lineage.

[`DISCOVER-RESULT-CANDIDATE-HANDOFF-CONVERGENCE-01`](../roadmap/DISCOVER_RESULT_CANDIDATE_HANDOFF_CONVERGENCE_01.md)
has populated the existing canonical `SearchResultCandidatePacket` from
truthful provider-result identity/material refs while retaining zero candidate-
page transport and the selected-candidate nontrigger.

The old combined exact-URL/final-custody phase was superseded before
implementation. [Current Roadmap](../roadmap/CURRENT_ROADMAP.md) exclusively
owns phase order. Query strategy/reconnaissance and read-source/custody are now
installed; iterative navigation/retrieval judgment and gap recovery/stopping
remain next. [SearchOS Operating
Model](SEARCHOS_OPERATING_MODEL.md) owns the target search/acquisition operating
boundary.

Focused Extract, Map, and Crawl remain later or separately licensed
capabilities. This documentation repair activates none of them and changes none
of the installed acquisition-control, selected-candidate nontrigger, work-
order, routing, execution, terminal, or custody-authority doctrine above.

## Nonproofs

This owner proves the selected-candidate nontrigger in offline product-path
composition, the bounded ordinary result-reference reduction, the independent
model-owned READ proposal producer, and the typed main-RunKernel chain through
canonical READ custody. It does not prove live provider behavior, provider
quality, downstream semantic evidence use, Focused Extract product use, Serper
connection, Map selection, Crawl custody, general Deep, evidence correctness,
source-obligation
satisfaction, Sufficiency, FAP, Author, answer quality, compatibility rename, or
complete-app correctness. No live provider, model, search, fetch/read, or
retrieval call was made.
