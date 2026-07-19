# EXACT-URL-NETWORK-TARGET-SAFETY-OWNER-01

Status: completed Repair
Mode: REPAIR
Proof class: offline_product_path_proof
Starting-runtime/test: d14b790f625812799d7b20e09b7e86a2c59e907d
Runtime/test checkpoint: c1f7e9f0e5b54277f696b2a8703bf00a1322fee8
Applies-to: untrusted dynamic content-target URLs entering post-discovery
acquisition control, provider routing, guarded execution, and observed-target
reduction
Does-not-authorize: live calls, exact-URL READ activation, Focused Extract
production, final custody, semantic admission, planner disambiguation, Map,
Crawl, provider synthesis, or a new local webpage downloader

## Outcome

This repair installs `core.network_target_safety` as the one pure policy owner
for untrusted dynamic content targets. The owner performs no DNS lookup and no
transport. It consumes typed, immutable resolver snapshots supplied by a
caller and returns a stage-bound typed decision. RunKernel adapts its existing
capability, work-order, route, execution, terminal, slot-release, exhaustion,
and custody chain; no parallel safety controller or execution chain exists.

The repair does not activate production exact-URL acquisition. Current
repository evidence does not establish any Linkup or Tavily operation as
eligible for the `untrusted_exact_url` target class. That is an evidence gap,
not a claim that either provider is inherently unsafe.

## Canonical Policy And Snapshot Contract

The policy owns conservative parsing and canonicalization for HTTP(S) content
targets, literal-address classification, bounded resolver-snapshot validation,
and stage-specific decisions. It rejects malformed or ambiguous host syntax
and prohibited address classes, including loopback, link-local, private,
reserved, multicast, and unspecified targets. Hostname decisions require a
bounded resolver snapshot when the stage requires resolution.

Resolver snapshots retain only the bounded facts needed for review: schema and
policy versions, canonical host, resolution status, address classifications,
public addresses when allowed, digests for nonpublic addresses, counts, and a
snapshot digest. They retain no unrestricted DNS response, private resolver
payload, credentials, headers, cookies, or transport material.

The three exact stages are:

1. `admission_pre_route`
2. `final_pretransport`
3. `posttransport_observed_target`

A decision is permission only for the exact target, transport mode, resolver
snapshot, policy version, lineage, and stage it binds. It grants no provider,
evidence, citation, custody, semantic, or answer authority.

## Gate 1: Admission Before Work Exists

Gate 1 evaluates every proposed exact target before work-order admission,
provider route selection, and active-slot reservation. A block produces the
existing typed admission/capability decision with the target-safety blocker.

Because no operation has been admitted, a Gate 1 safety block creates:

- no work order;
- no route or provider selection;
- no active slot;
- no RunCap charge;
- no execution authorization or claim;
- no adapter invocation or transport;
- no terminal receipt; and
- no exhausted operation identity.

Gate 1 therefore does not terminalize an operation.

## Gate 2: Sole Blocked-Before-Claim Execution Posture

After an accepted work order and route exist, the guarded executor performs a
fresh `final_pretransport` decision immediately before transport. It binds the
current target, resolver snapshot, admission decision, transport mode, and
current RunKernel lineage.

Gate 1 is not silently reused as Gate 2 proof. A changed normalized target,
policy digest, transport mode, or resolver-snapshot digest blocks at Gate 2.

Gate 2 is the sole narrowly permitted blocked execution result that does not
consume the one-use execution claim. A Gate 2 block occurs before:

- RunCap charge;
- execution claim;
- adapter invocation; and
- provider transport.

The executor returns a typed blocked execution observation rather than throwing
from the cap callback. The existing RunKernel execution and terminal reducers
then settle the authorization, release the active slot, and deterministically
exhaust the admitted unsafe operation identity. A retry, provider switch, or
capability switch remains unlicensed.

## Gate 3: Observed Target Before Success Or Custody

When provider transport was attempted, Gate 3 evaluates every actually
observed resolved, redirected, provider-reported, final, or canonical content
target before:

- successful artifact admission;
- successful execution reduction;
- terminal success; and
- custody authorization.

A prohibited observed target produces a typed posttransport target-safety
failure. The already-attempted provider transport, single RunCap charge, and
single execution claim remain recorded exactly once, but no successful
artifact or custody authorization is admitted.

Observation extraction retains at most 100 unique target records and examines
at most 200 raw response items. Crossing either bound is itself a canonical
posttransport safety failure; an over-bound target cannot be hidden behind
normalization failure or duplicate records.

Missing observations remain missing; the repair does not manufacture a
redirect, resolved, final, canonical, peer-address, or DNS fact.

## Requested A And Observed B

The requested URL A and an observed URL B remain separate facts. B is not
rejected merely because it differs from A. Each observed B is evaluated in
this order:

1. network-target safety under the canonical owner; then
2. source-lineage and applicability under the existing acquisition/custody
   boundary.

When B is safe and applicable, an operation may remain successful and preserve
both A and B. When B is safe but inapplicable, the result is a typed
lineage/applicability failure, not a safety failure. When B is prohibited, the
result is the Gate 3 posttransport safety failure. Tavily's existing
provider-reported selected-result identity check remains distinct from
redirect, final, and canonical applicability.

## Provider Target-Safety Eligibility

`core.routing` treats provider target-safety eligibility as a pre-dispatch
input separate from:

- capability compatibility;
- provider availability;
- code-owned preference order; and
- requester preference.

An unavailable or target-safety-ineligible preferred provider may be excluded
before dispatch, after which an already cataloged available and eligible
route-time alternative may be selected. Once any provider adapter is invoked,
there is no provider fallback, retry, capability switch, or transport-time
eligibility reconsideration.

The current code-owned production matrix for untrusted exact targets is:

| Provider operation | Production eligibility | Repository-grounded reason |
| --- | --- | --- |
| Linkup Fetch `READ/known_url` | false | sufficient committed public-target guarantees and observable final-target lineage are not established |
| Tavily Extract `READ/basic` | false | sufficient committed public-target guarantees and observable final-target lineage are not established |
| Tavily Extract `FOCUSED_EXTRACT/query_focused` | false | sufficient committed public-target guarantees and observable final-target lineage are not established |
| Tavily Map `MAP_SITE/bounded` | false | sufficient committed public-target guarantees and observable final-target lineage are not established |
| Tavily Crawl `CRAWL_SITE/bounded` | false | sufficient committed public-target guarantees and observable final-target lineage are not established |

This matrix does not say that Linkup or Tavily is inherently unsafe. It says
only that ScryRaven cannot truthfully assert eligibility from committed
repository guarantees and observable target lineage. Offline injected fixtures
may prove filtering, route-alternative mechanics, and guarded execution; they
do not alter production eligibility or prove live provider behavior.
The installed offline execution fixture accepts tamper-evident JSON response
data only. It has no provider-callback field, never installs default transports,
and is internally bound to the one already-selected adapter slot.

## Endpoint Exclusions

The policy governs dynamic content targets, not fixed service infrastructure.
These remain outside the untrusted target class:

- fixed Linkup and Tavily provider API endpoints;
- ordinary fixed DISCOVER provider endpoints;
- an explicitly configured and authorized local provider broker endpoint; and
- an explicitly configured and authorized local model endpoint.

Exclusion does not grant those endpoints new authority. Their existing
configuration, confirmation, secret-handling, and one-shot transport rules
remain unchanged.

## Direct Opener Disposition

The two CLI-reachable local webpage openers are retired:

| Surface | Disposition |
| --- | --- |
| `proplex.mvp_live_dogfood_run.fetch_public_url_once` | typed fail-closed tombstone; no urllib opener or transport |
| `proplex.mvp_single_relation_live_dogfood_run.fetch_public_url_once` | typed fail-closed tombstone; no urllib opener or transport |

The former live source-survival validation opener in
`scripts/ag_live_source_survival_fetch_read_custody_01.py` is also a typed
fail-closed tombstone. That harness is now `VALIDATION`, accepts only an
explicit injected fixture, and is structurally `PRODUCT-unreachable`. An
injected result proves downstream validation mechanics only. No replacement
local webpage downloader was added.

## Telemetry And Persistence

Canonical acquisition state retains bounded policy refs, decision refs,
snapshot refs, stage and transport posture, blocker codes, classification
counts, provider-eligibility refs, and aggregate safety counters. It records
zero cap, claim, adapter, and transport for Gate 1 and Gate 2 blocks. Gate 3
failures preserve the one attempted transport, cap charge, and claim without a
successful artifact or custody admission.

The repair does not destructively reinterpret historical rows or persist
unrestricted resolver results. Existing `urls_fetched` semantics remain actual
separate attempted exact-URL transport; discovery-only candidate admission does
not increment it.

## Verification Boundary And Nonproofs

Offline tests may prove static parsing, typed resolver snapshots, Gate ordering,
slot release, exhaustion, A/B preservation, applicability separation,
provider-eligibility filtering, endpoint exclusion, opener retirement, and
bounded telemetry. They do not prove live DNS behavior, connected-peer binding,
provider redirect behavior, provider quality, source correctness, final
custody, semantic support, citation eligibility, Sufficiency, FAP, Author, or
complete-app correctness. No live provider, model, search, DNS, fetch/read,
Map, Crawl, or retrieval call was made for this repair.

## Roadmap Exit

Installed by this candidate:

```text
canonical network-target safety owner
```

Still blocked:

```text
EXACT-URL-ACQUISITION-AND-FINAL-CUSTODY-CONVERGENCE-01
pending at least one truthfully eligible provider operation
```

Still queued, without advancement:

```text
PLANNER-DISAMBIGUATION-ACQUISITION-CONVERGENCE-01
SITE-TOPOLOGY-SELECTION-AUTHORITY-01
CRAWL-PAGE-CUSTODY-CONVERGENCE-01
```
