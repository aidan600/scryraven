# SearchOS Operating Model

Status: current target architecture
Authority: canonical:searchos-operating-model
Default-read: no
Applies-to: SearchOS architecture and SearchOS-facing provider, acquisition, navigation, and recovery work
Does-not-authorize: implementation, live calls, provider claims, or activation of planned capabilities

## Product Boundary

ScryRaven is a research application. It is responsible for source provenance,
evidence sufficiency, source hierarchy, currentness, logical construction,
component coverage, citations, and grounded final answers.

**SearchOS** names ScryRaven's search, source-acquisition, navigation, and
recovery subsystem. It is not a project, repository, package, CLI,
environment-variable, or compatibility rename. Existing names such as
`proplex`, `python -m proplex`, and `PROPLEX_*` remain compatibility surfaces.

ScryRaven is not a browser, a general local scraper, anti-bot infrastructure, a
DNS or redirect-attestation service, or an application for any particular
provider. SearchOS should use providers through narrow, provider-neutral
contracts while retaining ScryRaven's own research judgments.

## Root Run Authority

RunKernel / RunAuthority is the root authority for a run. It accepts and
administers the AnswerContract, owns canonical run state, authorizes work and
judgments, reduces observations, enforces budgets, authorizes recovery, and
enforces the terminal posture decided by Sufficiency from canonical facts.

Narrower owners remain subordinate:

- SearchPlanner proposes meaning, components, obligations, and search needs.
- Query design proposes executable strategies and queries.
- QueryPlan owns admitted query identity, ordering, roles, and lineage.
- `core.routing` selects providers and operations.
- Adapters execute completed routes mechanically.
- EvidenceLedger owns custody.
- SemanticObservation and ComponentCoverage own support judgments.
- Sufficiency decides whole-run readiness and final posture from canonical
  facts; RunKernel consumes and enforces that decision.
- FinalAnswerPacket packages Author-safe material.
- Author writes prose only.

Sufficiency does not independently mutate or terminate run state.

## Minimum Shared Provider Contract

SearchOS is designed around the minimum shared search result:

```text
title
URL
bounded relevant context
provider/result identity
optional date or scalar metadata
```

A provider may return richer extracted content with a search result. That is an
optional optimization, not a universal dependency and not proof that a complete
page was returned.

## Material Levels

1. **Direction material**: reconnaissance hints used for query or venue
   direction; never evidence.
2. **Search-result material**: a candidate plus bounded source material; not
   presumed complete.
3. **Read-source material**: fuller known-URL material eligible for custody and
   semantic review.
4. **Navigation material**: outbound exact URLs derived from a source;
   candidates only until separately read.

Material does not gain evidence, citation, source-obligation, or answer
authority merely because a provider returned it.

## Provider-Neutral Operations

The target SearchOS vocabulary is:

- **`RECON`**: non-evidence direction for entity, alias, jurisdiction,
  currentness, official venue, and query refinement.
- **`SEARCH`**: candidate URLs plus bounded provider context.
- **`READ_PAGE`**: fuller material for one known URL.
- **`NAVIGATE`**: one exact next URL derived from a read source; it remains a
  candidate until separately read.
- **`MAP_SITE`**: bounded topology and candidate URLs; never evidence.
- **`CRAWL_SITE`**: bounded page collection with one identity and custody
  record per page.

These are target architectural operations. They do not rename installed runtime
enum values. Linkup Fetch and Tavily Extract are peer implementations of
`READ_PAGE`; neither is a distinct research authority. A provider-reported URL
is useful optional metadata, not network-path attestation.

## Iterative SearchOS Loop

The shared target loop is:

```text
find candidate
-> inspect available material
-> accept if sufficient
   OR perform a known-URL read
   OR follow one bounded breadcrumb
   OR revise the query
-> custody
-> semantic evaluation
-> judge remaining gaps
```

Search results need not contain a complete page. A successful read that lacks
the needed information is source insufficiency, not a transport failure: return
to search, another source, or bounded navigation rather than extracting the
same page repeatedly.

## Installed One-Hop Navigation Boundary

The ordinary product now consumes the existing navigation foundation at a
maximum depth of one. Only a fresh candidate-origin READ may expose bounded,
safe same-site Markdown links. SearchJudgment sees URL-free navigation refs and
may copy one exact current ref; the existing navigation selection, acquisition,
FetchRead, EvidenceLedger, and SearchOS custody owners execute the destination.
Navigation-origin custody may return to the ordinary judgment and semantic /
final-answer path, but it is never a link-extraction input.

Recursive navigation, navigation-origin child extraction, depth greater than
one, navigation-specific physical reuse, cross-slot navigation reuse, and
recursive-navigation limit calibration are not installed and are not part of
the one-hop MVP. They have no ordinary product caller. If later licensed, they
must reuse the existing URL-selection, acquisition, and custody owners rather
than introduce a parallel navigation path.

[SearchOS Iterative Judgment Direction](SEARCHOS_ITERATIVE_JUDGMENT_DIRECTION.md)
records the approved iterative-judgment convergence direction for the active
roadmap checkpoint beneath this durable target subsystem doctrine. It does not
replace current code, tests, or [ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md)
as installed truth, and it does not authorize BUILD.

## Planned Post-Analysis Recovery Boundary

Canonical post-analysis SearchOS recovery is not installed. The approved
direction preserves every terminal slot as immutable and represents an
admitted recovery cycle with a new, purpose-bound slot revision linked to the
prior terminal slot.

A whole-run recovery lease will be distinct from local SearchOS action
reservations and budgets. Prior histories and expenditure remain cumulative.
QueryPlan retains sole ownership of exact query identity, admission, and
material query equivalence. SearchOS reports slot and cycle facts, exhaustion,
blockers, and lawful-novel-work posture; Sufficiency decides the whole-run
final posture. A terminal SearchOS slot or `HANDOFF_UNRESOLVED` is not by
itself a whole-run insufficiency decision.

The canonical
[SearchOS post-analysis recovery and inference direction](SEARCHOS_POST_ANALYSIS_RECOVERY_AND_INFERENCE_DIRECTION.md)
owns the detailed authorization basis, internal PR boundaries, inference
direction, and legacy-retirement sequence. This operating-model summary does
not install the transition.

## Query And Primary-Source Strategy

Query design is part of the SearchOS MVP. It should support:

- exact entities and aliases;
- official or canonical-source pursuit;
- currentness and date windows;
- historical versus current variants;
- exact document, release, filing, rule, or policy families;
- domain constraints;
- secondary corroboration;
- contradiction and independent-source checks; and
- nonredundant recovery queries tied to active gaps.

Primary-source pursuit is a query and source-hierarchy strategy, not a provider
identity shortcut. The installed initial SearchPlanner-to-QueryPlan path and
initial and in-loop SearchJudgment reuse those concerns without making provider
identity an authority shortcut. Legacy Scout disambiguation has no forward
ordinary SearchOS authority.

## Provider Responsibility Boundary

ScryRaven owns:

- request construction and basic URL hygiene;
- provider and capability selection;
- authorization and cost limits;
- attempt accounting;
- request-to-response binding;
- bounded response validation;
- provenance and custody; and
- evidence, citation, and answer decisions.

The provider owns DNS, remote connections, redirects, rendering, scraping,
anti-bot handling, and provider-side network security. ScryRaven does not
require DNS snapshots, connected-IP proof, redirect-chain attestation, or
mandatory final or canonical URLs before accepting bounded provider-returned
material.

The network-attestation model introduced in PR #507 was reverted by PR #508.
This operating model records the corrected responsibility boundary without
repeating the rollback mechanics.

## Adaptive Retrieval Target

Adaptive retrieval is approved but uninstalled:

- one provider request per recorded attempt;
- preserve every attempt;
- at most one alternate or stronger attempt after a typed retrieval-quality
  failure;
- no retry after a usable success merely to compare providers;
- no repeated extraction when a successfully read page simply lacks the needed
  information; and
- after source insufficiency, return to search, another source, or bounded
  navigation.

The exact typed failure policy and budgets belong to later implementation
phases. This target does not activate provider-failure fallback today.

## Provider-Change Layers

Provider change belongs in three layers:

1. **Adapters** own provider request and response mechanics.
2. **Versioned provider profiles** own capabilities, limits, optional outputs,
   cost model, and availability facts.
3. **Routing policy** owns current preferences, alternatives, attempt limits,
   mode budgets, and escalation order.

Changing a provider's price, preference, limit, or optional field should not
require rewriting RunKernel, custody, or research authority. Provider profiles
and versioned routing-policy configuration are target owners only; they are not
installed by this document.

## Later Boundaries

- Preserve the pure PDF text-layer parser, but do not describe it as a complete
  PDF acquisition path.
- Map may later become an optional navigation plugin if it reuses existing
  URL-selection authority.
- Crawl is not required for the core MVP.
- Social-domain acquisition remains provider-pluggable, but grants no
  representativeness, sampling, trust, identity, or sentiment authority.
- Conversation is a later transport-neutral follow-up service. It re-enters
  SearchOS only when new work is required.
- UI remains later and must consume transport-neutral product services.

Provider Deep/Research, social specialization, conversation, and UI are not
core SearchOS MVP prerequisites.

## Anti-Side-Quest Gates

Every future phase brief and phase that changes SearchOS-facing provider,
acquisition, navigation, or recovery behavior must answer:

1. What ordinary-user product capability changes?
2. Which AnswerContract need or real consumer requires it?
3. Is this ScryRaven's responsibility or the provider's?
4. Which existing owner is reused, adapted, upgraded, retired, or replaced?
5. Is the concept durable research authority or volatile provider
   configuration?
6. How does it advance query design, search, reading, navigation, custody,
   recovery, sufficiency, or answers?
7. What observed requirement or documented provider boundary justifies it?
8. What stop condition would prove it is disproportionate or belongs
   elsewhere?
9. What is installed versus merely planned?

> No SearchOS infrastructure may be added merely to compensate for an imagined
> provider limitation or hypothetical transport. A current product need and an
> observed or documented provider boundary must both exist.

These gates apply only to SearchOS-facing work. They do not replace the
project-wide workflow owners.

## Temporal Owners

[ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md) owns installed truth.
[Provider Capability and Acquisition Routing](PROVIDER_CAPABILITY_AND_ACQUISITION_ROUTING.md)
owns installed provider selection, adapters, and routing boundaries.
[RunKernel Post-Discovery Acquisition Control](RUNKERNEL_POST_DISCOVERY_ACQUISITION_CONTROL.md)
owns the installed post-discovery control chain. [Current
Roadmap](../roadmap/CURRENT_ROADMAP.md) alone owns priority and phase order.
Nothing in this target architecture installs a capability or authorizes work.
