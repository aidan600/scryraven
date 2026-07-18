# DISCOVER-RESULT-CANDIDATE-HANDOFF-CONVERGENCE-01

Status: completed Build
Mode: BUILD
Proof class: offline_product_path_proof
Depends-on: INITIAL-DISCOVERY-SELECTIVE-FETCH-RETIREMENT-01
Starting-runtime/test: 48a309124764d813cf27081bf5871d5a9612db79
Runtime/test commit: cfd8daed12ed4a0cccaf1bc9e6de1b5019e1ea35
Does-not-authorize: live calls, candidate-page fetching, exact-URL READ or
Focused Extract, provider-routing redesign, Serper planner disambiguation, Map,
Crawl, evidence admission, citation authority, or final-answer authority

## Outcome

Canonical unflagged Fast, Balanced, and Deep discovery now carries every
admitted provider-result occurrence from the provider boundary through existing
QueryPlan, ProviderPlan, retrieval, ranking/filtering, and selection owners into
the existing `RunKernel.SearchResultCandidatePacket`. The installed ordinary
origin is `ordinary_query_provider`, packet revision 1. It is a bounded
non-evidence URL/material-provenance handoff and performs zero candidate-page or
exact-URL transport.

The runtime/test implementation is exactly
`cfd8daed12ed4a0cccaf1bc9e6de1b5019e1ea35`.

## Authority And Reuse Census

| Surface | Disposition | Installed responsibility |
| --- | --- | --- |
| QueryPlan and QueryPlan item refs | `REUSE` | retain authorized query, role, iteration, and query-plan membership |
| ProviderPlan, record, and route refs | `REUSE` | retain the completed provider choice and provider-neutral DISCOVER route |
| retrieval scheduling and dispatch refs | `ADAPT` | carry the exact retrieval action and deterministic provider-call ordinal into result identity |
| existing ranking/filtering and candidate selection | `REUSE` | choose the URL representative and selected order without rewriting provider rank |
| `retrieval.DiscoverySourceResultIdentity` | `UPGRADE` | immutable text-free identity for one ordered provider-result occurrence before URL deduplication, chunking, or ranking |
| `retrieval.DiscoveryResultMaterialStore` | `UPGRADE` | run-local bounded custody of normalized provider-returned candidate material and occurrence/contributor lineage |
| `RunKernel.SearchExecutorHandoff` | `ADAPT` | ordinary post-discovery, reference-only branch; no replacement owner or search execution |
| `RunKernel.SearchResultCandidatePacket` | `ADAPT` | canonical ordinary-origin revision-1 packet under the existing packet owner |
| default-disabled injected-candidate/live-validation seam | `RETAIN NONORDINARY` | remains separate and is not the ordinary packet origin |
| selected-candidate acquisition trigger | `RETAIN CLOSED` | preserve the predecessor's retirement: URL provenance alone still creates no material need, READ, or Focused Extract work |

No shadow planner, AnswerContract, result registry, ranker, packet, validation
state, or acquisition route was added.

## Result Identity And Material Contract

`retrieval.DiscoverySourceResultIdentity` is created for each provider-returned
result occurrence at deterministic result reduction, before URL deduplication,
passage chunking, relevance ranking, or final selection. It binds the run and
request, QueryPlan and item refs, query digest/role, retrieval role and
iteration, retrieval-action ref, ProviderPlan/record/route refs, provider and
DISCOVER operation facts, provider-call ordinal, provider-result rank,
normalized URL/domain/date, and a bounded material ref/digest/class. The
identity contains no provider text or raw payload.

`retrieval.DiscoveryResultMaterialStore` is the run-local material owner. It
retains the normalized provider-returned title, snippet or excerpt/summary,
URL/domain/date, bounded material, and immutable identity/material bindings.
The material remains DISCOVER output with `provider_returned_snippet` or
`provider_returned_excerpt` posture. It is not fetched/read content,
EvidenceLedger custody, citation material, or source-obligation satisfaction.

The installed exact caps are:

| Bound | Exact value and behavior |
| --- | --- |
| provider results admitted per call | existing mode policy: Fast 5, Balanced 6, Deep 8; applied before result identity reduction |
| result identities per run | 80; later occurrences close with run-cap overflow telemetry |
| canonical bytes per identity | 4,096 UTF-8 bytes; oversized identities close before admission |
| provider material per occurrence | 20,000 characters; stable prefix retained with original/retained counts and truncation telemetry |
| packet candidates | existing `top_chunks`: Fast 8, Balanced 20, Deep 40; absolute packet cap 40 |
| contributor refs per selected URL | 8 retained refs plus total, overflow count, and digest of the complete contributing sequence |
| candidate title/snippet projection | 220/500 characters |
| canonical RunKernel result-ref state | at most 16 KiB, with no provider text, chunks, embeddings, or raw payload |
| selected refs in the compact RunKernel projection | first 8 refs plus retained/overflow counts and a digest over the full selected order |

All result identities and duplicate occurrence material remain available in the
run-local store. Canonical RunKernel state is reference-only and bounded; it is
not a preview or copy of provider material.

## Ordering, Ranking, And Duplicate Rules

Provider-call ordinals are reserved before concurrent submission. Result
reduction follows deterministic submission order, never completion order.
Within each provider response, `provider_result_rank` is the original one-based
returned position before relevance ranking. Existing passage/chunk scores and
RRF/credibility rules remain the relevance owner; they do not overwrite
provider rank. `selected_candidate_rank` is the separate one-based order of the
existing final candidate selection.

Two provider occurrences with the same normalized URL receive distinct
identities and distinct bounded material records. Existing relevance/RRF and
URL filtering choose the ordinary representative. The selected record retains
up to eight contributing occurrence refs plus overflow facts and a full digest;
duplicates are not silently collapsed into a fabricated provider occurrence or
renumbered rank.

## Ordinary Handoff And Packet

Revision 1 is the immutable initial ordinary post-DISCOVER selection snapshot.
It is produced before this composition's later SearchPlanner/AnswerContract
admission, source-class/conflict recovery, and synthesis. At that exact snapshot
point the main RunKernel does not yet have an accepted AnswerContract or source
obligation. Its `answer_contract_ref` is therefore empty rather than
manufactured. This does not negate later accepted contract lineage or contract-
bound historical SearchExecutor flows. Later recovery results keep truthful
identities in the same run-local store but do not mutate revision 1; a later
canonical packet revision is a separate checkpoint.

The ordinary `RunKernel.SearchExecutorHandoff` branch has origin
`ordinary_query_provider` and execution mode
`post_discovery_reference_handoff_only`. It binds current QueryPlan/ProviderPlan
membership, selected query items, completed provider records/routes, retrieval
actions, the complete result-identity set, and selected result refs. It creates
no provider call and does not recreate SearchPlanner tasks.

RunKernel authorizes the exact ref-only action, and the ordinary runtime then
builds the packet through the sole `RunKernel.SearchResultCandidatePacket`
owner. Packet id/digest, compact handoff id/digest, full selected-ref digest,
identity-set ref, and selected-candidate-input digest are rederived and checked
at execution and reduction. Stale QueryPlan/ProviderPlan/AnswerContract refs,
mutated packets or handoffs, duplicate action replay, and unknown or authority-
bearing fields fail closed.

The unflagged CLI composition reaches this path in Fast, Balanced, and Deep.
The ordinary packet is persisted in canonical trace and JSONL state; affected
scalar telemetry retains SQLite parity. It does not use
`live_search_validation`, and that separate seam does not become ordinary
authority.

## Closed Surfaces And Telemetry

The packet and RunKernel projection explicitly record that provider calls were
already completed and that the handoff caused no provider call, acquisition
proposal, READ work order, Focused Extract work order, exact-URL cap charge,
exact-URL transport, or fetched URL. Candidate presence remains a structural
nontrigger.

Telemetry meanings are exact:

- `provider_results_returned_count` is the number returned before per-call
  limiting; `provider_results_within_call_limit_count` is the bounded prefix;
  `provider_call_result_overflow_count` is the remainder.
- `source_result_identities_created` is the admitted occurrence count.
  `provider_results_rejected` counts invalid URLs plus identity-byte-cap
  overflow; `provider_results_truncated` counts per-call plus run-cap overflow.
- `duplicate_normalized_url_count` and compatibility field
  `provider_results_deduplicated` count duplicate URL occurrences; they do not
  mean their identities or material were discarded.
- `material_chars_retained` and `material_truncation_count` describe only the
  bounded provider-returned material store.
- `candidate_packets_created` is one for a successful ordinary handoff and
  `selected_candidates_handed_off` is its selected record count.
- `discover_candidate_urls_admitted` counts provider-returned DISCOVER URL
  admissions. `urls_fetched` counts separate exact-URL fetch/read transports
  and remains zero for this handoff.

Serper `lightweight_disambiguation` remains excluded from this ordinary packet
origin. Planner-disambiguation acquisition remains a later checkpoint. The
public ScryRaven name is unchanged; compatibility names including `proplex`,
`python -m proplex`, `PROPLEX_*`, `proplex.db`, and `proplex_*` remain supported.
Any compatibility rename is deferred.

## Verification And Nonproofs

Focused offline tests cover identity creation before chunking, caps and
telemetry, deterministic concurrent ordering, duplicate contributors, rank
separation, current plan/contract validation, mutation/replay rejection,
RunKernel state bounds and closed fields, unflagged Fast/Balanced/Deep packet
creation, zero exact-URL transport, JSONL packet/trace persistence, affected-
scalar SQLite telemetry parity, Serper exclusion, and all ordinary discovery/
recovery caller closure. SQLite does not store the full packet. No live
provider, model, search, fetch/read, or retrieval call was made.

This Build does not prove provider quality, live availability, currentness,
coverage, latency, price, reliability, answer-quality improvement, exact-URL
acquisition, READ or Focused Extract product consumption, final custody,
EvidenceLedger admission, citation correctness, source-obligation satisfaction,
Sufficiency, FinalAnswerPacket, Author behavior, Serper connection, Map, Crawl,
package rename, arbitrary-query behavior, or complete-app correctness.

## Sole Active Next

The sole active next checkpoint is
[`EXACT-URL-ACQUISITION-AND-FINAL-CUSTODY-CONVERGENCE-01`](EXACT_URL_ACQUISITION_AND_FINAL_CUSTODY_CONVERGENCE_01.md).
It must install a real independent current-material-need producer, genuinely
product-consumed exact-URL READ, and final custody without turning candidate
selection into an automatic acquisition trigger.

Planner disambiguation, site-topology selection, and Crawl page custody remain
queued in that order after exact-URL/final-custody convergence.
