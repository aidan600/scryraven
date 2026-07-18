# CRAWL-PAGE-CUSTODY-CONVERGENCE-01

Status: queued after site-topology selection authority
Mode: BUILD
Proof class: offline_product_path_proof
Depends-on: SITE-TOPOLOGY-SELECTION-AUTHORITY-01
Split reason: Crawl page custody changes source-identity and custody contracts; Map selection changes topology and URL-selection authority
Does-not-authorize: live calls, unbounded crawl, candidate manufacture, aggregate false sources, automatic Map-to-Crawl, general Deep, or downstream authority by assertion

## Outcome

Activate bounded `CRAWL_SITE` beneath the installed RunKernel acquisition chain
and converge each returned page through an explicit page-level custody contract
without treating the page collection as one source or manufacturing search
candidates.

## Installed Starting Point

- The controller recognizes an exact root, exact allowed root domain, bounded
  path scope, explicit multi-page need, and `bounded_multi_page` material shape,
  then returns `crawl_page_custody_not_installed` before routing.
- `core.routing` and the Tavily adapter already support bounded Crawl with
  code-owned ceilings: depth 2, 10 pages, 20,000 retained characters per page,
  and 100,000 aggregate retained characters.
- `AcquisitionArtifactKind.BOUNDED_PAGE_COLLECTION` retains individual
  `AcquisitionPageArtifact` records with requested/attempted/provider-reported/
  resolved/final/canonical/parent identity when observed.
- No ordinary Crawl requester, page-level custody packet, or EvidenceLedger
  consumption semantics are installed.

## Required Build

1. Identify one ordinary producer of the exact root/domain/path scope and
   explicit multi-page source-obligation need. A Map receipt may be a parent
   fact, but Map must never trigger Crawl automatically.
2. Replace the Crawl blocker only for that admitted producer and execute exactly
   one bounded Crawl work order through the existing RunKernel chain.
3. Define one page-level custody contract whose records bind the Crawl work
   order, route, terminal receipt, collection digest, page ordinal, exact page
   identity, observed lineage, truncation posture, and current contract/
   component/obligation. Preserve absent provider facts as unknown.
4. Give each page its own source identity. Do not represent the collection as a
   single source, reuse the site root as every page's source, or create synthetic
   `SearchResultCandidatePacket` candidates.
5. Extend the existing custody/EvidenceLedger owners only through a named
   reducer and named ordinary consumer. The reducer may record bounded custody;
   it must not assert semantic support, citation eligibility, source-obligation
   satisfaction, completeness, or answer authority.
6. Preserve the code-owned Crawl ceilings and reject cross-domain, out-of-path,
   malformed-parent, excess, stale, duplicate, active-conflict, and exhausted
   state before custody.

## Verification

- Exact qualifying need derives Crawl; incomplete root/domain/path/multi-page
  facts remain blocked without transport.
- One authorized route and one mechanical Crawl dispatch occur, with no
  recursion, fan-out, fallback, or capability switch.
- Every admitted page binds to the canonical collection and keeps separate
  requested, attempted, provider-reported, redirect/final/canonical, parent,
  content-type/status, and truncation facts as available.
- Cross-domain and out-of-path pages fail closed; provider excess is bounded
  exactly as the installed adapter contract specifies.
- Page custody creates no synthetic search candidate and no aggregate false
  source.
- Zero live calls, zero general Deep, zero provider synthesis, zero raw/private
  payload retention, and no citation/final-answer authority.
- Acquisition control, routing, Crawl adapter, page custody, EvidenceLedger,
  and actual ordinary consumer tests pass offline.

## Stop Conditions

Stop for a product decision if the intended consumer needs page ranking,
collection-level truth, cross-page synthesis, citation aggregation,
source-obligation satisfaction, or changed EvidenceLedger meaning beyond
bounded per-page custody. Do not hide any of those decisions in normalization
or orchestration.
