# Provider Capability And Acquisition Routing

Status: current
Authority: canonical:provider-capability-acquisition-routing
Default-read: yes
Applies-to: current ordinary acquisition routing, shared acquisition contracts, ProviderPlan projection, scheduling, mechanical dispatch, and selected-candidate READ custody
Does-not-authorize: live calls, provider-quality claims, provider-failure retry, provider synthesis, new product requesters, or downstream evidence/final authority
Verified-against-runtime: 280277fcf50243c9e915a2b9344fa7779ff78d4d
Update-trigger: change to capability vocabulary, catalog, request/artifact contracts, provider selection, adapter bounds, product consumption, or provider-material authority

## Purpose And Ownership

`core.routing` is the sole provider-capability policy owner. It owns capability
compatibility, provider eligibility and preference, operation and variant
selection, route-time fallback selection, typed blocks, and general Linkup Deep
authorization compatibility.

`core.acquisition_contracts` owns immutable bounded requests, job identity,
operation limits, normalized artifacts, lineage, and execution results.
`core.acquisition_adapters` consumes one completed route decision and remains
mechanical: it constructs one selected provider request, normalizes bounded
material, or returns a typed failure/block. It does not select, substitute,
reorder, or retry providers.

ProviderPlan records completed DISCOVER decisions. Retrieval scheduling and
dispatch carry those decisions without policy. The orchestrator composes one
boolean provider-availability snapshot from configured credential presence, or
from explicitly injected offline-test facts, and passes that same snapshot to
ProviderPlan and selected-candidate READ. Callables, transport objects, and
ordered provider preferences do not establish availability. Existing
SearchResultCandidatePacket, FetchReadContentPacket, SanitizedContentReference,
and EvidenceLedger owners retain source custody.

Runtime/test provenance:
`280277fcf50243c9e915a2b9344fa7779ff78d4d`.

## Capability Status Matrix

Availability is runtime-specific; the status below describes installed policy
and consumers, not credential presence or live availability.

| Capability | Cataloged | Adapter installed | Typed-runtime reachable | Ordinary-product enabled | Ordinary-product reachable | Ordinary-product consumed |
| --- | --- | --- | --- | --- | --- | --- |
| `DISCOVER` | yes | yes | yes | yes | yes | yes, through current ProviderPlan, scheduler, dispatch, continuation, supplemental, and recovery consumers |
| `READ` | yes | yes | yes | yes | yes | yes, through selected-candidate source custody |
| `FOCUSED_EXTRACT` | yes | yes | yes | no | no requester | no |
| `MAP_SITE` | yes | yes | yes | no | no requester | no |
| `CRAWL_SITE` | yes | yes | yes | no | no requester | no |
| General Linkup Deep | yes | mechanical support yes | authorized runtime only | no | no qualifying current requester | no |
| Scrutineer Deep | yes | yes | yes | yes, behind existing remediation gates | yes | preserve existing bounded consumer |
| `PROVIDER_SYNTHESIS` | yes, as disabled surfaces | disabled | blocked | no | no | no |

Adapter installation or validation-constructed dispatch is not ordinary product
consumption. No product requester was manufactured for focused extraction, site
mapping, site crawling, or general Linkup Deep.

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
| `READ` | Linkup Fetch | Tavily Extract if Linkup is unavailable before dispatch | one caller-selected URL; 20,000 retained characters maximum |
| `FOCUSED_EXTRACT` | Tavily Extract | none | caller-selected URLs only; 2,000-character focus maximum; 20 URLs maximum; bounded text |
| `MAP_SITE` | Tavily Map | none | explicit same-site root; normalize/deduplicate; 100 URLs maximum; topology only |
| `CRAWL_SITE` | Tavily Crawl | none | one job; depth 2; 10 pages; 20,000 characters/page; 100,000 aggregate; exact domain/path scope |
| General Deep | Linkup `deep/searchResults` | none | explicit authorization; one query per mechanical job from at most two authorized queries; five results/query maximum |
| Scrutineer Deep | existing Linkup `deep/searchResults` path | existing policy only | unchanged novel-query/remediation gates |
| `PROVIDER_SYNTHESIS` | none | none | blocked before transport |

Tavily Research, Linkup Research, `sourcedAnswer`, and `structured` outputs are
not installed acquisition operations.

Linkup-only remains valid for general/domain-targeted DISCOVER and preferred
READ when configured. Provider subsets create no fan-out, and domain targeting
grants no social interpretation or authority.

## READ Product Consumption And Fallback

The selected-candidate ordinary source-custody path is:

```text
SearchResultCandidatePacket
-> selected candidate URL
-> completed READ route decision
-> exactly one Linkup Fetch or Tavily Extract adapter
-> normalized bounded read artifact
-> existing FetchReadContentPacket
-> existing EvidenceLedger custody reduction
```

Linkup Fetch is preferred. Tavily Extract is selected only when the explicit
composition snapshot says Linkup is unavailable before dispatch. Injecting a
Linkup callable or transport cannot make Linkup available. Once Linkup is
selected, transport failure, malformed output, unreadable status, empty
material, or URL mismatch returns a typed failure and makes zero Tavily calls.

After route/request validation and transport resolution, selected-candidate
READ marks the current `RunCapPolicy` fetch/read budget exactly once immediately
before the provider call. `RunCapExceeded` remains the product terminal and is
not converted into a source-custody failure. Absence of a cap policy preserves
uncapped ordinary behavior.

Linkup Fetch carries the product's explicit `render_javascript=false` posture
as `renderJs=false` and records it in the request trace. Minimal Linkup or Tavily
material can succeed with only requested/attempted identity; missing or invalid
page HTTP status and unreported redirect/canonical lineage remain unknown.
Explicit provider-reported redirect and canonical facts survive unchanged.

The adapter does not admit evidence. The existing FetchReadContentPacket and
EvidenceLedger custody reducer continue to decide only their existing bounded
custody facts; this phase changes no semantic support, citation, source-
obligation, Sufficiency, FinalAnswerPacket, or Author authority.

## Dormant Typed Capabilities

`FOCUSED_EXTRACT`, `MAP_SITE`, and `CRAWL_SITE` require
`typed_runtime_only=true` and exact bounded requests. Ordinary routing returns
`capability_not_ordinary_product_enabled` because no deterministic current
PRODUCT requester exists.

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
and unchanged.

## Product Roots And Residual Compatibility

Current PRODUCT consumers:

- ordinary main, continuation, supplemental, and recovery DISCOVER work through
  ProviderPlan, scheduling, and dispatch;
- selected-candidate READ/source custody through the ordinary pipeline; and
- the generic single-relation acquisition root, which now supplies a completed
  `core.routing` decision from explicit availability before provider-specific
  callables are invoked; a provider preference cannot authorize itself.

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

## Authority Closure

Provider response keys cannot create evidence, citation, obligation
satisfaction, component coverage, Sufficiency, FinalAnswerPacket, Author,
social, or final-answer authority. Raw/private response fields are rejected.
Domain constraints and provider identity grant no source-of-record, official,
social, trust, sampling, representativeness, or correctness authority.

Provider synthesis remains disabled and unreachable. Fallback candidates remain descriptive
and never dispatch after provider failure. Every migrated PRODUCT acquisition
operation has exactly one selected provider or blocks with zero transport.

## Next Checkpoint And Nonproofs

The combined adapter/runtime repair is complete. The sole active next is
`BOUNDED-FINAL-CUSTODY-CONVERGENCE-01`, applied only to currently product-
consumed DISCOVER and READ artifacts. It does not manufacture consumers for
dormant capabilities.

This offline repair proves no live provider quality, availability, coverage,
currentness, latency, price, reliability, or answer improvement. It does not
prove evidence correctness, final-custody convergence, social authority,
Sufficiency, FinalAnswerPacket, Author behavior, or complete-app correctness.
No live provider, model, search, fetch, map, crawl, or retrieval call was made.
