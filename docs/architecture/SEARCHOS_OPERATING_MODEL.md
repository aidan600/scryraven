# SearchOS Operating Model

Status: current architecture; unified front-half Phases 1-2 installed
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

## Unified Front-Half Rebaseline (Phases 1-3 Installed)

On 2026-08-11 the maintainer selected **Option C modified into a unified
iterative loop** as the SearchOS front-half architecture. Phases 1, 2, and 3
are now installed in ordinary product execution. Exception-by-exception Scout /
PlannerRevision repair is retired from the ordinary front half, including its
routine initial ContractAmendment return lane. SearchWorkPlan and QueryProduction
are retired as ordinary semantic/query compatibility carriers. Rich Planner
compatibility is reduced to current real AnswerContract, QueryPlan, and SearchOS
consumers. [ScryRaven Current
State](SCRYRAVEN_CURRENT_STATE.md) remains the exclusive owner of detailed
installed truth.

The installed authority shape is:

```text
User request
-> compact model-owned SearchPlanner semantic proposal
-> deterministic semantic compiler
-> uncertainty-aware AnswerContract
-> QueryPlan
   - exact executable query
   - provider-neutral discovery job class
   - component/slot lineage
-> core.routing
-> DISCOVER
-> SearchJudgment
   - refine or escalate discovery
   - request READ
   - propose bounded factual InterpretationBinding
   - request clarification
   - semantic handoff
   - honest unresolved blocker
```

There is no ordinary `ScoutDisambiguation -> PlannerRevision -> initial routine
ContractAmendment -> return to ordinary search` lane. Search-assisted ambiguity
handling belongs inside this same acquisition loop; components do not receive
separate ambiguity pipelines.

### Installed authority boundaries

- **SearchPlanner** owns semantic interpretation only.
- The **deterministic semantic compiler** mechanically constructs lawful state
  after a semantic proposal.
- **AnswerContract** owns canonical requested obligations, constraints, stable
  slots, and explicit unresolved factual slots.
- **QueryPlan** is the sole exact executable-query identity and carries the
  provider-neutral discovery job class plus component and plural semantic-slot
  lineage. One physical query may serve multiple semantic obligations.
- **`core.routing`** selects provider and operation.
- **SearchJudgment** is the unified acquisition judgment after `DISCOVER` or
  `READ`.
- **RunKernel** owns admission and canonical state.
- **InterpretationBinding** is a small append-only, RunKernel-admitted filling
  of an already-declared factual slot.
- **EvidenceLedger, Analyst, D-prime, Sufficiency, FinalAnswerPacket, and
  Author** retain their existing downstream authorities.

SearchJudgment may propose a factual binding, but it may not create or redefine
components, change requested scope, facts, or obligations, select providers,
admit its own binding, admit evidence, claim support, decide Sufficiency, or
author an answer.

### Installed uncertainty behavior

The runtime distinguishes clear semantic intent, acquisition uncertainty,
factually resolvable identity/currentness/version/terminology uncertainty, true
user-intent ambiguity, and mixed uncertainty both within one component and
across multiple components. Every accepted semantic slot remains a distinct
obligation keyed by component and semantic-slot identity; semantic cardinality
is not inferred from the number of physical discovery jobs.

The bounded binding map is `entity -> identity_alias`,
`variant|time_period -> currentness_version`,
`source_basis -> document_lineage`, and materially unresolved
`unknown_or_other -> externally_verifiable_terminology`. An explicit default
`unknown_or_other` subject remains stable and takes standard discovery; the
last mapping does not turn unspecified stable meaning into uncertainty.

- A clear request, such as the default `rel_tol` and `abs_tol` values for
  `math.isclose()` in the official Python documentation, takes ordinary
  discovery without a special ambiguity pipeline.
- A factually orientable request, such as a recent Galloway controversy, may
  use bounded orientation discovery or READ to support binding Scott Galloway
  only when contextual and current fit strongly dominates materially plausible
  alternatives. Popularity alone is insufficient.
- For a truly ambiguous request such as "Tell me about Mercury," explicit
  user-confirmation posture withholds provider dispatch and records typed,
  slot-local clarification when the planet, element, automobile/brand, or
  other meanings remain materially plausible.
- In mixed requests, stable components may discover/read while factually
  unresolved components orient/bind/discover and materially ambiguous
  components request clarification, all within one component worklist.
- Within one component, all material unresolved factual slots independently
  remain active even when one physical orientation query serves them together.
  Binding or clarification targets exactly one slot. A component may hand off
  only after every relevant material slot is stable/resolved or has its own
  admitted factual binding; any pending or confirmation-required slot blocks
  that handoff without erasing or suppressing its peers.

### Installed provider-neutral job direction

The installed QueryPlan job vocabulary is exactly `orientation`,
`standard_discovery`, and `deep_discovery`. These name acquisition need, not a
provider brand; `core.routing` remains the sole provider mapper. Initial jobs
are derived only from the accepted AnswerContract. Orientation reuses the
existing lightweight-disambiguation route, standard discovery reuses ordinary
route derivation, and deep discovery sets the existing
`general_deep_requested` policy input. It reaches the existing authorization
and requester blocks; this phase installs no premium license or new Deep
executor. No new provider preference
or economics policy is encoded in QueryPlan. Later comparative calibration may
change code-owned mapping without changing the job vocabulary. `READ` remains
a separate known-URL capability and may assist orientation without
automatically becoming semantic support.

The canonical SearchOS state owns plural semantic obligations independently of
physical component/source slots. QueryPlan items and SearchOS physical slots
carry plural references; no singular compatibility field is an alternate
semantic authority. SearchWorkPlan and QueryProduction are retired ordinary
compatibility carriers and do not change that installed ownership.

Phase-3 carrier consolidation is installed. Post-rebase inert Scout,
PlannerRevision, SearchWorkPlan, and official-current SearchWork compatibility
detritus is removed where zero current consumer existed. Next product work is
owned by the
[Current Roadmap](../roadmap/CURRENT_ROADMAP.md). Nothing in this section
authorizes a live call.

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

The SearchOS vocabulary is:

- **`DISCOVER job_class=orientation`**: non-evidence direction for entity,
  alias, jurisdiction, currentness, official venue, and query refinement.
- **`DISCOVER job_class=standard_discovery`**: ordinary candidate URL
  acquisition plus bounded provider context.
- **`DISCOVER job_class=deep_discovery`**: deeper candidate acquisition when
  the component's acquisition need warrants it.
- **`READ_PAGE`**: fuller material for one known URL.
- **`NAVIGATE`**: one exact next URL derived from a read source; it remains a
  candidate until separately read.
- **`MAP_SITE`**: bounded topology and candidate URLs; never evidence.
- **`CRAWL_SITE`**: bounded page collection with one identity and custody
  record per page.

The three DISCOVER job classes are installed runtime enum values owned by
QueryPlan and consumed by the unified loop. `RECON` and `SEARCH` may remain
compatibility implementation terms, but they are not separate durable pipelines
or competing query authorities. Cheap orientation is represented only by
`DISCOVER job_class=orientation` inside the unified acquisition loop.

READ and bounded one-hop navigation are installed under their existing owners;
Map and Crawl remain non-product capabilities. Linkup Fetch and Tavily Extract
are peer implementations of `READ_PAGE`; neither is a distinct research
authority. A provider-reported URL is useful optional metadata, not network-path
attestation.

## Iterative SearchOS Loop

The installed shared loop is:

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

### Factual binding, clarification, and slot-local progress

SearchJudgment may propose one bounded factual filling only for an already
declared unresolved material slot of kind entity, variant, time period, or
source basis. The value must be one of the accepted candidate values and must
cite exact current candidate or READ-custody basis. RunKernel validates and
append-only admits `searchos_interpretation_binding_v1`; exact replay is
idempotent, while a conflicting second binding or changed component/slot scope
fails closed. The base AnswerContract never changes. An effective semantic-slot
view is an acquisition-planning projection only and is not evidence, support,
coverage, satisfaction, citation, or final-answer authority.

Slots marked `user_confirmation_required` do not bind or dispatch. They record
typed clarification and remain local to their component. Stable and factually
orientable peers continue through the same worklist, with independent candidate
ancestry, budget, and cursor state. An empty initial orientation result records
exact provider/query/action lineage and may refine orientation once within the
existing policy before reaching an honest unresolved or exhausted posture.

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

[SearchOS First-Wave And Iterative-Judgment
Cutover](SEARCHOS_FIRST_WAVE_AND_ITERATIVE_JUDGMENT_CUTOVER.md) owns the
installed first-wave boundary, candidate continuity, iterative SearchJudgment,
candidate READ, semantic handoff, and unresolved-slot terminal. [ScryRaven
Current State](SCRYRAVEN_CURRENT_STATE.md) owns installed one-hop and current
product truth.

## Installed Post-Analysis Recovery And Inference Boundary

Boundary A existing-component/source-obligation recovery and Boundary B
searched-premise recovery are installed under one append-only whole-run
SearchOS lease/cycle owner. Every terminal slot and cycle record remains
immutable. Local reservations and budgets remain distinct from the whole-run
lease, and histories and expenditure remain cumulative without resets.

QueryPlan retains sole ownership of exact query identity, admission, and
material query equivalence. SearchOS searches direct premises and reports slot,
cycle, expenditure, exhaustion, and blocker facts. It does not author,
validate, admit, or render an inference. Component/Cross-Component Analyst,
synthesis D-prime, RunKernel Graph V1, Sufficiency, FAP, and Author retain those
separate responsibilities.

The installed ceilings are semantic inference depth 1 for Fast and Balanced
and 2 for Deep; searched recovery generation is 0, 1, and 2 respectively.
Exact replay is resolved before currentness rejection and creates no new
amendment, cycle, graph, final packet, or Author work. Sufficiency remains the
sole whole-run final-posture owner. A terminal SearchOS slot or
`HANDOFF_UNRESOLVED` is not by itself a whole-run insufficiency decision.

The canonical
[SearchOS post-analysis recovery and inference direction](SEARCHOS_POST_ANALYSIS_RECOVERY_AND_INFERENCE_DIRECTION.md)
owns the detailed authorization basis, internal PR boundaries, inference
direction, and legacy-retirement sequence. This operating-model summary records
the installed transition; executable authority remains in the ordinary owners
named above.

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
