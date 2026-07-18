# Provider Capability And Acquisition Routing

Status: current
Authority: canonical:provider-capability-acquisition-routing
Default-read: yes
Applies-to: current ordinary DISCOVER routing, shared acquisition contracts,
ProviderPlan projection, retained RunKernel post-discovery routing, provider
target-safety eligibility, mechanical dispatch, and selected-candidate
nontrigger behavior
Does-not-authorize: live calls, provider-quality claims, provider-failure retry, provider synthesis, new product requesters, or downstream evidence/final authority
Verified-against-runtime: c1f7e9f0e5b54277f696b2a8703bf00a1322fee8
Update-trigger: change to capability vocabulary, catalog, request/artifact
contracts, provider selection, target-safety eligibility, adapter bounds,
product consumption, or provider-material authority

## Purpose And Ownership

`core.routing` is the sole provider-capability policy owner. It owns capability
compatibility, provider availability and preference consumption, operation and
variant selection, route-time alternative selection, typed blocks, and general
Linkup Deep authorization compatibility. For untrusted dynamic content targets,
it also consumes a code-owned provider-operation target-safety eligibility
snapshot. Capability, availability, target-safety eligibility, code-owned
preference, and requester preference remain separate facts.

`core.network_target_safety` is the pure target policy owner. It owns static
target parsing, bounded typed resolver snapshots, and admission,
final-pretransport, and posttransport observed-target decisions. It performs no
provider selection and no transport. RunKernel consumes those decisions through
its existing acquisition chain rather than through a parallel safety
controller.

`core.acquisition_contracts` owns immutable bounded requests, job identity,
operation limits, normalized artifacts, lineage, and execution results.
`core.acquisition_adapters` consumes one completed route decision and remains
mechanical: it constructs one selected provider request, normalizes bounded
material, or returns a typed failure/block. It does not select, substitute,
reorder, or retry providers.

For post-discovery source-obligation work, RunKernel now owns proposal
admission, capability/work-order/route/execution/terminal state, active slots,
deduplication, exhaustion, and separate custody authorization.
`core.acquisition_control` derives capability from admitted provider-neutral
facts. `core.authorized_acquisition_runtime` validates the exact current
RunKernel authorization and is the only PRODUCT caller of the still-independent
low-level `dispatch_acquisition()` dispatcher. The complete ownership contract
is [RunKernel Post-Discovery Acquisition
Control](RUNKERNEL_POST_DISCOVERY_ACQUISITION_CONTROL.md).

ProviderPlan records completed DISCOVER decisions. Retrieval scheduling and
dispatch carry those decisions without policy.
`retrieval.DiscoverySourceResultIdentity` owns one immutable text-free identity
per ordered provider-result occurrence before URL deduplication, chunking, or
ranking. `retrieval.DiscoveryResultMaterialStore` owns the bounded run-local
provider material and duplicate-contributor lineage. Existing ranking and
selection now feed the ordinary origin of the canonical
`RunKernel.SearchResultCandidatePacket`. Ordinary discovery never opens a
candidate URL to rank, filter, select, or populate that packet. The orchestrator
composes one boolean provider-
availability snapshot from configured credential presence, or from explicitly
injected offline-test facts, and passes it to ProviderPlan. Callables, transport
objects, and ordered provider preferences do not establish availability. The
same snapshot remains available to the retained future READ controller, but
candidate selection alone creates no proposal and never reaches it. The
SearchResultCandidatePacket, FetchReadContentPacket, SanitizedContentReference,
and EvidenceLedger owners remain unchanged.

Target-safety eligibility is not inferred from availability, an installed
adapter, a callable, configuration, environment, requester preference, or a
provider name. A preferred provider may be excluded before dispatch when it is
unavailable or target-safety ineligible, and an already cataloged available and
eligible alternative may then be selected. Once any provider adapter is
invoked, no provider fallback, retry, capability switch, or eligibility-driven
redispatch is permitted.

Current runtime/test provenance:
`6fbca602afac5a00bb6bafa2a6888b6ec31d5065`.
The initial-discovery transport retirement remains historically installed at
`48a309124764d813cf27081bf5871d5a9612db79`.
The mechanical adapter foundation remains historically installed at
`193c5caabe1f97da534f0e601d410acb98d3cdea`.

## Ordinary DISCOVER Result Boundary

Provider-call ordinals are reserved before concurrent submission, and results
reduce in submission order rather than completion order. Within a returned
sequence, `provider_result_rank` is the original one-based provider position.
Existing relevance/chunk/RRF scoring remains separate, and
`selected_candidate_rank` is the final selected order. Duplicate normalized
URLs retain distinct occurrence identities and material; the selected
representative carries up to eight contributor refs plus overflow facts and a
digest of the complete contributor sequence.

The exact bounds are the existing 5/6/8 provider results per call and 8/20/40
selected candidates for Fast/Balanced/Deep, 80 identities per run, 4,096
canonical bytes per identity, 20,000 material characters per occurrence, 8
contributor refs, and a 16 KiB text-free RunKernel reference projection.
Provider result text, chunks, embeddings, and raw payloads do not enter that
projection.

The ordinary `RunKernel.SearchExecutorHandoff` and
`RunKernel.SearchResultCandidatePacket` use origin `ordinary_query_provider`,
revision 1. This is the immutable initial post-DISCOVER selection before later
SearchPlanner/AnswerContract admission and source recovery/synthesis in this
ordinary composition. The main RunKernel has no accepted AnswerContract or
source obligation at that exact snapshot point, so neither is fabricated. This
does not negate later accepted contract lineage or contract-bound historical
SearchExecutor flows. It is reachable through the
unflagged Fast/Balanced/Deep CLI/backend composition and does not use the
separate `live_search_validation` origin. Serper
`lightweight_disambiguation` remains excluded.

The ordinary packet digest binds the ordered candidate-record digests. Its
compact RunKernel ref retains that aggregate digest and lineage/count fields,
not candidate URLs, snippets, or provider text.

## Capability Status Matrix

Availability is runtime-specific; the status below describes installed policy
and consumers, not credential presence or live availability.

| Capability | Cataloged | Adapter installed | Typed-runtime reachable | Ordinary-product enabled | Ordinary-product reachable | Ordinary-product consumed |
| --- | --- | --- | --- | --- | --- | --- |
| `DISCOVER` | yes | yes | yes | yes | yes | yes, through current ProviderPlan, scheduler, dispatch, continuation, supplemental, and recovery consumers |
| `READ` | yes | yes | offline fixture only for untrusted exact targets | no | no ordinary material-need producer and no currently safety-eligible Linkup/Tavily untrusted exact-target route | no; selected candidate and URL provenance alone are a nontrigger |
| `FOCUSED_EXTRACT` | yes | yes | offline fixture only for untrusted exact targets | no | controller returns `focused_extract_requester_not_installed`; Tavily query-focused Extract is also currently target-safety ineligible | no |
| `MAP_SITE` | yes | yes | offline fixture only for untrusted roots | no | controller returns `map_candidate_reentry_not_installed`; Tavily Map is also currently target-safety ineligible | no |
| `CRAWL_SITE` | yes | yes | offline fixture only for untrusted roots | no | controller returns `crawl_page_custody_not_installed`; Tavily Crawl is also currently target-safety ineligible | no |
| General Linkup Deep | yes | mechanical support yes | authorized runtime only | no | no qualifying current requester | no |
| Scrutineer Deep | yes | yes | yes | yes, behind existing remediation gates | yes | preserve existing bounded consumer |
| `PROVIDER_SYNTHESIS` | yes, as disabled surfaces | disabled | blocked | no | no | no |

Adapter installation or validation-constructed dispatch is not ordinary product
consumption or production target-safety eligibility. No product requester was
manufactured for focused extraction, site mapping, site crawling, or general
Linkup Deep.

## Shared Request, Job, And Artifact Contracts

One `AcquisitionRequest` carries only operation-relevant facts:

- capability and completed route decision;
- acquisition job and parent-job identity;
- selected URL(s) or explicit root URL;
- an explicit bounded JavaScript-rendering posture;
- bounded focus text, queries, domains, and paths;
- result, page, depth, per-page, and aggregate limits;
- candidate, query, acquisition-lineage, and obligation references; and
- the completed route's explicit Deep authorization when applicable.

Normalized artifacts distinguish discovery candidates, selected-URL reads,
focused selected-URL extractions, site topology, bounded page collections,
provider failures, and policy/availability blocks. Requested and attempted URLs
are request/dispatch facts. A URL returned by a provider is labeled
`provider_reported_url`; resolved, final, canonical, page-status, and actual
crawl-parent facts remain absent unless the transport/provider supplied them.
`root_url` remains distinct from an observed page parent. Artifacts also retain
provider/operation/variant/output, job lineage, title/timestamp, and bounded
character/digest facts when known.

Requested URL A and every observed URL B remain separate. A reported,
redirected, resolved, final, or canonical B is not rejected merely because it
differs from A. The canonical target policy first evaluates B for network
safety; the existing source-lineage/applicability boundary then evaluates B for
the requested acquisition. Safe and applicable B may remain successful. Safe
but inapplicable B produces a lineage/applicability failure rather than a safety
failure. A prohibited B produces a posttransport safety failure. Missing B is
never manufactured.

Ephemeral execution may carry bounded sanitized text to the existing custody
consumer. Durable traces omit that text and retain no raw HTML, raw provider
payload, credentials, headers, cookies, or unrelated fetched content.

## Installed Provider-Operation Matrix

| Capability | Preferred selected implementation | Route-time alternative | Installed bounds and output |
| --- | --- | --- | --- |
| `DISCOVER(general)` | Linkup `standard/searchResults` | Tavily Search if Linkup is unavailable before dispatch | one selected provider; URL-bound acquisition material |
| `DISCOVER(domain_targeted)` | Linkup `standard/searchResults` with caller constraints | Tavily Search if Linkup is unavailable before dispatch | exact constraints; no domain/social authority |
| `DISCOVER(academic_technical_semantic)` | Exa `neural_with_text/searchResults` | degraded Linkup standard, then Tavily | exact deterministic qualifier only |
| `DISCOVER(lightweight_disambiguation)` | Serper Web Search | none | candidate/query direction only |
| `DISCOVER(independent_index)` | Brave Web Search | none | candidate/query direction only |
| `READ` | Linkup Fetch | Tavily Extract before dispatch if Linkup is unavailable or target-safety ineligible and Tavily is independently available and eligible | one caller-selected URL; 20,000 retained characters maximum |
| `FOCUSED_EXTRACT` | Tavily Extract | none | caller-selected URLs only; 2,000-character focus maximum; 20 URLs maximum; bounded text |
| `MAP_SITE` | Tavily Map | none | explicit same-site root; normalize/deduplicate; 100 URLs maximum; topology only |
| `CRAWL_SITE` | Tavily Crawl | none | one job; depth 2; 10 pages; 20,000 characters/page; 100,000 aggregate; exact domain/path scope |
| General Deep | Linkup `deep/searchResults` | none | explicit authorization; one query per mechanical job from at most two authorized queries; five results/query maximum |
| Scrutineer Deep | existing Linkup `deep/searchResults` path | existing policy only | unchanged novel-query/remediation gates |
| `PROVIDER_SYNTHESIS` | none | none | blocked before transport |

Tavily Research, Linkup Research, `sourcedAnswer`, and `structured` outputs are
not installed acquisition operations.

Linkup-only remains valid for general/domain-targeted DISCOVER. Adapter
installation still records Linkup Fetch as the preferred READ hypothesis and
Tavily Extract as its route-time alternative, but neither operation is currently
production-eligible for an untrusted exact URL. Provider subsets create no
fan-out, and domain targeting grants no social interpretation or authority.

### Current untrusted exact-target eligibility

| Provider operation | Eligible in production | Reason |
| --- | --- | --- |
| Linkup Fetch `READ/known_url` | no | sufficient committed public-target guarantees and observable final-target lineage are not established |
| Tavily Extract `READ/basic` | no | sufficient committed public-target guarantees and observable final-target lineage are not established |
| Tavily Extract `FOCUSED_EXTRACT/query_focused` | no | sufficient committed public-target guarantees and observable final-target lineage are not established |
| Tavily Map `MAP_SITE/bounded` | no | sufficient committed public-target guarantees and observable final-target lineage are not established |
| Tavily Crawl `CRAWL_SITE/bounded` | no | sufficient committed public-target guarantees and observable final-target lineage are not established |

This code-owned all-false matrix is an eligibility statement about ScryRaven's
committed guarantees and observable lineage. It is not a claim that Linkup or
Tavily is inherently unsafe. Tests may inject a bounded eligibility fixture to
prove filtering, route-time alternative mechanics, and guarded execution. Such
a fixture is not configuration, cannot enter production policy, and proves no
live provider behavior.

## Selected-Candidate Nontrigger And Retained READ Route

The ordinary selected-candidate result is:

```text
SearchResultCandidatePacket
-> selected candidate URL
-> provenance only
-> no independent current material need
-> no AcquisitionNeedProposalV1
-> no work order, route, cap charge, adapter call, or custody
```

If a future canonical surface supplies a separate current material need, the
retained route is:

```text
independent material need + selected URL provenance
-> exact packet/current-lineage validation
-> Gate 1 admission target-safety decision
-> RunKernel capability decision and provider-neutral work order admission, only if allowed
-> RunKernel route authorization
-> core.routing capability + availability + target-safety eligibility decision
-> RunKernel route reduction and execution authorization
-> guarded PRODUCT acquisition executor
-> Gate 2 fresh final-pretransport target-safety decision
-> exactly one eligible Linkup Fetch or Tavily Extract adapter, only if allowed
-> Gate 3 observed-target safety then applicability
-> normalized bounded read artifact, only if both pass
-> RunKernel execution and terminal reduction
-> RunKernel READ custody authorization
-> existing FetchReadContentPacket
-> existing EvidenceLedger custody reduction
```

The flow is installed as guarded machinery, but the production
`untrusted_exact_url` eligibility matrix currently blocks at routing. An
offline fixture can exercise later mechanics without activating production.

The source-custody and main-RunKernel coverage flags default to false. Source
custody returns `not_needed` before provider availability, RunKernel actions,
cap accounting, or transport when no proposal is supplied. Late main coverage
consumes prior custody and cannot reacquire. The historical live source-custody
validation profile is non-executable. This is offline nontrigger proof, not
default live CLI READ consumption or live validation.

Linkup Fetch remains the first code-owned READ hypothesis. It may be selected
only when both available and target-safety eligible. Tavily Extract may be
selected before dispatch when Linkup is unavailable or target-safety ineligible
and Tavily is independently available and eligible. In production both are
currently ineligible for untrusted exact URLs. Injecting a Linkup callable or
transport cannot make Linkup available or eligible. Once any adapter is
invoked, transport failure, malformed output, unreadable status, empty material,
or URL mismatch returns a typed failure and makes zero alternative-provider
calls.
For Tavily READ, a generic provider-reported result URL must normalize to the
one selected URL. A mismatch returns
`read_provider_reported_url_mismatch` before FetchReadContentPacket creation;
a matching provider-reported URL remains explicit through packet and
EvidenceLedger custody. Redirect, final, and canonical fields remain separate
observed facts and may differ when explicitly supplied.

For an independently supplied need, the guarded executor validates current
AnswerContract, component, source-obligation, work-order, route, active-slot,
execution-authorization, routing-policy, and exhaustion state. It marks the
current `RunCapPolicy` fetch/read budget and consumes the one-use RunKernel
execution claim exactly once for an actually attempted provider transport.
Before either occurs, Gate 2 may return the sole typed blocked-before-claim
execution result. That result has zero cap charge, claim, adapter invocation,
or transport and follows the existing terminal slot-release/exhaustion chain;
it is not thrown from the cap callback. `RunCapExceeded` remains reduced
through the acquisition terminal path and its deferred product error is then
re-raised.

After an attempted provider transport, Gate 3 evaluates observed targets before
successful artifact admission, execution success, terminal success, or custody.
A posttransport safety or applicability failure retains the attempted call, cap
charge, and claim exactly once while admitting no successful artifact or
custody.

Linkup Fetch carries the product's explicit `render_javascript=false` posture
as `renderJs=false` and records it in the request trace. Minimal Linkup or Tavily
fixture material can exercise the typed adapter with requested/attempted
identity; missing page status and unreported redirect/canonical lineage remain
unknown. Production eligibility still requires the code-owned provider
operation posture. Explicit provider-reported redirect and canonical facts
survive unchanged.

The adapter does not admit evidence. The existing FetchReadContentPacket and
EvidenceLedger custody reducer continue to decide only their existing bounded
custody facts; this phase changes no semantic support, citation, source-
obligation, Sufficiency, FinalAnswerPacket, or Author authority.

## Dormant Typed Capabilities

`FOCUSED_EXTRACT`, `MAP_SITE`, and `CRAWL_SITE` remain available to low-level
typed-runtime validation with exact bounded requests and an explicit offline
eligibility fixture. The post-discovery
controller now recognizes their exact material needs but blocks before PRODUCT
routing or transport. Focused Extract returns
`focused_extract_requester_not_installed`; no current ordinary producer binds
exact pre-acquisition focus to current URL/contract/component/obligation facts.
Map returns `map_candidate_reentry_not_installed`; Crawl returns
`crawl_page_custody_not_installed`.

Map output is topology only. Crawl rejects out-of-domain or out-of-path pages
and lineage. Provider-returned page/content excess is deterministically
truncated with an explicit posture; request limits above the global ceilings
block before transport.

## General Linkup Deep Authorization

Fast, Balanced, or Deep mode; high complexity; weak corpus; provider
availability; adapter installation; and detailed-answer posture never authorize
general Deep. A validation-only authorization must prove:

- exact parent standard-acquisition job;
- same acquisition and obligation lineage;
- deterministic sequential-acquisition requirement;
- explicit premium authorization and remaining run budget;
- zero prior general escalation;
- at most two authorized queries and five results per query; and
- mandatory `searchResults` output.

The mechanical adapter accepts one authorized query per job. A valid record is
typed-runtime reachable only; ordinary routing still blocks with
`general_deep_no_ordinary_product_requester`. Scrutineer Deep remains separate
and unchanged. The new post-discovery controller returns the earlier durable
PRODUCT blocker `premium_sequential_acquisition_not_licensed` for a proposed
general premium-sequential need.

## Product Roots And Residual Compatibility

Current PRODUCT consumers:

- ordinary main, continuation, supplemental, and recovery DISCOVER work through
  ProviderPlan, scheduling, and dispatch, using provider-returned material with
  zero separate candidate-URL transport; the immutable initial selection feeds
  the ordinary revision-1 SearchExecutorHandoff and canonical candidate packet;
- no selected-candidate READ/source-custody consumer; the default-disabled
  composition is a nontrigger until an independent material-need producer is
  installed; and
- the generic single-relation acquisition root, which now supplies a completed
  `core.routing` decision from an explicit provider-neutral DISCOVER qualifier
  and availability before provider-specific callables are invoked. Ordinary
  extraction uses `general` or `domain_targeted` without an acquisition-plan
  provider override; a provider preference cannot create its own qualifier or
  authorize itself.

The lower-level `process_search_queries(search_providers=None)` escape is
closed: absence of a completed provider list performs zero transport. It no
longer manufactures Tavily/Linkup/Exa policy from environment or complexity.

Bounded residual compatibility:

- the source-of-record comparison script is VALIDATION and retains explicit
  provider comparisons;
- explicit provider preference fields in generic acquisition remain for
  OPERATOR/VALIDATION callers but are resolved through `core.routing` first;
- the lower-level Linkup `deep/sourcedAnswer` helper is LEGACY/VALIDATION-only
  and absent from the ordinary orchestrator; and
- retired saved-thread execution remains inert.

These surfaces do not own current PRODUCT provider policy.

## Infrastructure Endpoint Exclusions And Local Opener Retirement

The untrusted dynamic content-target policy applies to payload target URLs, not
the fixed endpoint used to reach a provider service. Fixed Linkup/Tavily API
endpoints and ordinary fixed DISCOVER endpoints remain mechanical transport
infrastructure. Explicitly authorized local broker and model endpoints likewise
remain under their existing configuration, confirmation, and secret-handling
contracts rather than being reclassified as untrusted webpage targets.

The two CLI-reachable local webpage helpers are typed fail-closed tombstones,
and the former source-survival validation opener is fixture-only and
PRODUCT-unreachable. No replacement local webpage downloader exists. Provider
API clients remain mechanical; a dynamic content target carried in their
payload remains a separately validated fact.

## Authority Closure

Provider response keys cannot create evidence, citation, obligation
satisfaction, component coverage, Sufficiency, FinalAnswerPacket, Author,
social, or final-answer authority. Raw/private response fields are rejected.
Domain constraints and provider identity grant no source-of-record, official,
social, trust, sampling, representativeness, or correctness authority.

Provider synthesis remains disabled and unreachable. Fallback candidates remain descriptive
and never dispatch after provider failure. Every migrated PRODUCT acquisition
operation has exactly one selected provider or blocks with zero transport.

The code-owned post-discovery routing-policy ref has revision
`exact_url_network_target_safety_owner_01`, algorithm revision
`first_reachable_and_target_safety_eligible_preference_v1`, and a digest over
the catalog, preference table, and eligibility-policy posture. Work order,
route, and execution bind it. No configuration, environment, prompt, or user
preference owns provider order or production eligibility.

## Next Checkpoint And Nonproofs

The explicit maintainer sequencing override placed RunKernel post-discovery
acquisition control before final-custody convergence. The controller and
mechanical adapters remain installed, while historical pre-selection source
fetching and the false selected-candidate trigger are retired.
[`DISCOVER-RESULT-CANDIDATE-HANDOFF-CONVERGENCE-01`](../roadmap/DISCOVER_RESULT_CANDIDATE_HANDOFF_CONVERGENCE_01.md)
now supplies truthful provider-result lineage to the ordinary branch of the
existing canonical `SearchResultCandidatePacket`, with zero candidate-page
transport and no ranked-passage reconstruction.

[`EXACT-URL-NETWORK-TARGET-SAFETY-OWNER-01`](../roadmap/EXACT_URL_NETWORK_TARGET_SAFETY_OWNER_01.md)
installs the pure safety owner, three gates, provider-operation eligibility,
and local-opener retirement. It does not reactivate
[`EXACT-URL-ACQUISITION-AND-FINAL-CUSTODY-CONVERGENCE-01`](../roadmap/EXACT_URL_ACQUISITION_AND_FINAL_CUSTODY_CONVERGENCE_01.md),
which remains blocked until at least one provider operation is truthfully
eligible for untrusted exact URLs. Planner disambiguation remains queued after
exact-URL convergence; Map selection and Crawl page custody remain later.

This offline Build proves no live provider quality, availability, coverage,
currentness, latency, price, reliability, or answer improvement. It does not
prove evidence correctness, final-custody convergence, social authority,
Sufficiency, FinalAnswerPacket, Author behavior, Serper connection, Focused
Extract, Map, Crawl, live DNS/peer binding, live provider target lineage,
compatibility rename, or complete-app correctness.
The direct selective page-fetch lane inside `core.pipeline` is retired rather
than governed by the post-discovery controller. No live provider, model,
search, DNS, fetch, map, crawl, or retrieval call was made.
