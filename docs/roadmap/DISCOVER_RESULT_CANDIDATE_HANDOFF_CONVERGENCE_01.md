# DISCOVER-RESULT-CANDIDATE-HANDOFF-CONVERGENCE-01

Status: sole active next checkpoint
Mode: BUILD
Proof class: offline_product_path_proof
Depends-on: INITIAL-DISCOVERY-SELECTIVE-FETCH-RETIREMENT-01
Starting-runtime/test: 48a309124764d813cf27081bf5871d5a9612db79
Does-not-authorize: live calls, candidate-page fetching, exact-URL READ or Focused Extract, provider-routing redesign, Serper planner disambiguation, Map, Crawl, evidence admission, citation authority, or final-answer authority

## Outcome

Converge normalized provider-returned DISCOVER candidates through the existing
QueryPlan, ProviderPlan, ranking/filtering, and candidate-selection owners into
a canonical ordinary `SearchResultCandidatePacket`. The handoff must preserve
truthful provider-result lineage without restoring candidate-page transport or
creating a parallel SearchPlanner, AnswerContract, SearchExecutorHandoff, or
candidate-admission authority.

## Installed Starting Point

- Ordinary Fast, Balanced, Deep/high-complexity, planner-assisted, and recovery
  discovery ranks only provider-returned title, snippet/excerpt, URL, and scalar
  metadata. It performs zero separate candidate-URL transport before selection.
- Candidate selection alone is URL provenance and does not create an
  acquisition need, work order, route, cap charge, or exact-URL transport.
- `SearchResultCandidatePacket` remains a durable non-evidence handoff, but the
  canonical ordinary DISCOVER path does not populate it.
- The existing default-disabled structured-input seam must not be used to
  synthesize missing task, provider-call, rank, or material-label facts from
  ranked passage chunks.
- The canonical handoff must not synthesize packet fields; every populated
  field must retain its truthful provider-result owner and lineage.
- RunKernel post-selection acquisition control and mechanical adapters remain
  installed but ordinary READ and Focused Extract are not activated.

## Required Build

1. Identify the existing canonical owner of provider-result identity before
   passage chunking and define the smallest provider-neutral selected-candidate
   handoff contract consumed by the existing packet owner.
2. Preserve exact QueryPlan/ProviderPlan query and provider lineage, original
   provider result position, selected URL/title/date/source metadata, and the
   truthful distinction between provider-returned snippet and excerpt/summary.
3. Support multi-query and multi-provider discovery without collapsing provider
   identity, renumbering provider rank, or allowing completion order to become
   authority.
4. Populate the existing `SearchResultCandidatePacket` through one ordinary
   consumer. Do not create a shadow packet, validation state, planner, ranking
   owner, or candidate-admission route.
5. Keep selected candidates non-evidence and nontriggers for READ or
   FOCUSED_EXTRACT. No packet field may imply that a candidate page was fetched.
6. Retain the structural zero-candidate-URL-transport guard across canonical
   initial discovery and all recovery variants.

## Verification

- Offline Fast, Balanced, and Deep product composition populates a truthful
  packet from normalized provider results with zero candidate-page transport.
- Multi-query/provider tests preserve task, provider-call, rank, URL, material
  type, and deterministic selection lineage without synthetic fields.
- Candidate selection alone still produces zero acquisition proposal, work
  order, route, cap charge, or exact-URL transport.
- QueryPlan, ProviderPlan, provider routing, ranking/filtering, RunKernel
  acquisition control, and packet meaning remain under their current owners.
- No live call, exact-URL READ, Focused Extract, Serper connection, Map, Crawl,
  EvidenceLedger admission, citation, Sufficiency, FAP, or Author claim occurs.

## Mandatory Following Sequence

After this Build completes:

1. `EXACT-URL-ACQUISITION-AND-FINAL-CUSTODY-CONVERGENCE-01`
2. `PLANNER-DISAMBIGUATION-ACQUISITION-CONVERGENCE-01`
3. `SITE-TOPOLOGY-SELECTION-AUTHORITY-01`
4. `CRAWL-PAGE-CUSTODY-CONVERGENCE-01`

Exact-URL convergence remains blocked until canonical ordinary DISCOVER has
populated a selected-candidate packet from truthful provider-result lineage.
