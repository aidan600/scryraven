# Run-Contract Semantic Loop

Status: current
Authority: canonical:run-contract-semantic-loop
Default-read: no
Applies-to: integrated query-to-answer authority and proposal/reduction flow
Does-not-authorize: live calls, arbitrary-query claims, direct worker mutation, additional Specialist capabilities, or calculator scope expansion
Verified-against-runtime: c1f7e9f0e5b54277f696b2a8703bf00a1322fee8
Update-trigger: merged change to the integrated ordinary semantic loop

## Responsibility

This document owns the integrated authority flow from a user query to an
ordinary `RunOutcome`. Installed-state scope belongs to
[ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md), current sequence belongs
to [Current Roadmap](../roadmap/CURRENT_ROADMAP.md), D-prime role boundaries
belong to [D-prime Architecture](DPRIME_ARCHITECTURE.md), and the bounded
multi-component implementation belongs to
[Multi-Component Synthesis Runtime Architecture](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md).

The durable rule is:

```text
Workers propose.
RunKernel authorizes and reduces.
```

The zero-candidate-URL-transport predecessor remains historically grounded at
runtime/test commit `48a309124764d813cf27081bf5871d5a9612db79`.

Semantic understanding is not deterministic contract authority, and the
contract is not a substitute for semantic understanding. SearchPlanner,
Analyst, D-prime, Cross-Component Analyst, synthesis D-prime, Scrutineer, and
other semantic workers emit bounded proposals or validations. RunKernel owns
action authorization, accepted contract state, canonical reduction, admission,
blocking, challenge, and recovery authorization.

## Integrated Ordinary Loop

The current loop is one authority flow, not a phase chronology:

1. A user query enters the ordinary product path.
2. SearchPlanner proposes question meaning, semantic slots, answer components,
   ambiguity posture, and search/source requirements.
3. RunKernel validates and admits the immutable `initial_answer_contract`.
4. When bounded disambiguation is useful, RunKernel may authorize Scout.
5. Scout returns reconnaissance and search-direction hints only; its output is
   not evidence, a citation, or contract mutation.
6. SearchPlannerRevision consumes Scout context and proposes amendments.
7. RunKernel admits and applies valid amendments into
   `current_answer_contract`.
8. The contract-bound SearchExecutorHandoff remains search intent, not search
   execution or evidence. Its historical pre-search origin is distinct from the
   ordinary post-discovery reference handoff below.
9. Provider-neutral DISCOVER returns sanitized candidate URLs, titles,
   snippets/excerpts, and bounded scalar lineage metadata. Each admitted
   provider-result occurrence receives a text-free
   `retrieval.DiscoverySourceResultIdentity` before URL deduplication, passage
   chunking, or ranking; bounded provider material remains in
   `retrieval.DiscoveryResultMaterialStore`. Existing ranking, filtering, and
   selection remain authoritative and no initial-planning,
   planner-disambiguation, discovery, recovery, ranking, or candidate-selection
   step opens a candidate source URL.
10. RunKernel authorizes a reference-only revision-1 ordinary
    SearchExecutorHandoff after the initial DISCOVER selection, then the
    existing `RunKernel.SearchResultCandidatePacket` owner consumes its exact
    identity/material refs under origin `ordinary_query_provider`. The packet is
    URL/material provenance and a non-evidence handoff, not a material need.
    It is reachable in unflagged Fast/Balanced/Deep composition, does not use
    `live_search_validation`, and causes no provider call, READ, Focused Extract,
    exact-URL cap charge, or transport. Fetch/read may produce bounded sanitized
    content only after a separate current need, exact lineage validation,
    RunKernel READ or Focused Extract authorization, `core.routing` selection,
    and the guarded PRODUCT executor. No ordinary material-need producer is
    currently installed.
11. EvidenceLedger records candidate/content custody and provenance-labeled
    partial lineage for observed fields; it does not invent unobserved source
    metadata. Custody is not admitted meaning or component satisfaction.
12. Evidence-relative analysis proposes what the custodied material means,
    including findings, caveats, contradictions, and gaps.
13. RunKernel admits eligible proposal-stage meaning as SemanticObservation
    state.
14. ComponentCoverage reduces admitted meaning plus custody bindings against
    current AnswerContract obligations.
15. Nonqualifying and single-component requests continue through the direct
    ordinary semantic lane.
16. Requests qualifying for
    `ordinary-bounded-multicomponent-factual-synthesis-v1` enter the bounded
    multi-component lane: component Analyst proposes, component D-prime
    validates, and RunKernel admits component state into ComponentWorkGraph V1.
17. Cross-Component Analyst proposes dependencies and synthesis; synthesis
    D-prime validates nominated synthesis; RunKernel admits canonical graph and
    synthesis state.
18. Full Scrutineer adversarially challenges the case when its installed
    triggers require review.
19. In the fixed CLI/UI product composition, component and ordinary Cross-
    Component Analyst receive one repository-owned model-visible quantitative
    proposal contract whose declarative fields, fixed values, operator policies,
    and bounds are also consumed by runtime validation. A conforming typed
    source-bound quantitative need may become one RunKernel-
    governed deterministic work item. Its exact source-literal result or typed
    nonexecution disposition becomes one unified handoff for component or
    synthesis D-prime. Synthesis inputs carry two-hop claim-to-evidence lineage.
    A required predispatch reconstruction failure publishes that failed handoff
    pending and unconsumed before the ordinary path safely blocks without
    running D-prime.
    Cross input reproof is unconditional: the ordinary caller may supply its
    exact transient packet, while RunKernel independently reconstructs from
    current scheduler-owned component Analyst packets. Missing reconstruction
    authority fails before graph reduction and retains no new packet or catalog.
20. At most one bounded missing-component recovery may amend the
    AnswerContract, re-enter ordinary research, admit the recovered component,
    and resume the governed graph.
21. Recovery invalidates and recomputes only the affected synthesis closure;
    unaffected admitted synthesis is deterministically carried forward under a
    new RunKernel authority binding.
22. Sufficiency decides readiness from admitted state. FinalAnswerPacket then
    packages only admitted, readiness-approved material and projects
    claim-scoped quantitative rendering authority.
23. Author renders a ready packet. Its candidate prose is buffered until the
    deterministic quantitative finalization validator binds every numeric
    assertion to the current packet manifest. Rejected prose is not displayed,
    reduced, rewritten, or retried. A blocked packet reaches the installed
    sanitized non-Author terminal. The product returns `RunOutcome`, including
    CLI-visible output when applicable.

Every semantic call in the selected multi-component loop is scheduled from
canonical ready work and carries exact RunKernel lease lineage. The driver does
not nominate the next role. Transport-only workers may overlap only within the
installed hosted initial-component width; canonical observations, admission,
graph mutation, recovery, selective recomputation, readiness, packaging, and
rendering reduce deterministically on the main thread.

## Ordinary Discovery Result Handoff

The ordinary provider-result boundary is deliberately split by owner:

- `retrieval.DiscoverySourceResultIdentity` creates one immutable text-free
  identity per returned occurrence before URL deduplication, chunking, or
  ranking and binds QueryPlan, ProviderPlan, route, call, original result rank,
  retrieval action, URL, and material refs;
- `retrieval.DiscoveryResultMaterialStore` retains the bounded normalized
  provider-returned material and duplicate-contributor lineage;
- existing relevance/chunk/RRF and URL-selection code chooses the representative
  and selected rank without rewriting provider-result rank; and
- RunKernel authorizes and reduces the compact handoff and existing canonical
  packet refs, without copying material or creating acquisition authority.

Concurrent provider completion order is not authority: provider-call ordinals
are reserved before submission and results reduce in submission order. Duplicate
URLs retain distinct identities/material and up to eight contributor refs plus
overflow facts and a full digest.

Exact bounds are 5/6/8 provider results per call and 8/20/40 selected candidates
for Fast/Balanced/Deep, 80 identities per run, 4,096 canonical bytes per
identity, 20,000 material characters per occurrence, 8 contributor refs, and a
16 KiB reference-only canonical RunKernel projection. That state contains no
provider text, chunks, embeddings, or raw payload. The ordinary packet identity
binds an ordered aggregate of its candidate-record digests; RunKernel retains
only that aggregate in the compact packet ref.

Revision 1 is the immutable initial post-DISCOVER selection before the ordinary
composition's later SearchPlanner/AnswerContract admission and subsequent
source recovery/synthesis. The main RunKernel has no accepted AnswerContract or
source obligation at this exact snapshot point, so the ordinary origin keeps
the contract ref empty rather than manufacturing one. This timing does not
negate the accepted `initial_answer_contract` used by later loop stages or the
contract-bound historical SearchExecutor branch. Later recovery identities do
not mutate revision 1. The
unflagged CLI/backend path reaches this origin in Fast, Balanced, and Deep, but
candidate presence remains a nontrigger: provider-call-caused-by-handoff,
acquisition proposal, READ/Focused Extract work order, exact-URL cap charge,
transport, and fetched-URL count all remain closed/zero. Serper lightweight
disambiguation is excluded.

The historical AG-LIVE-XAXIS-VALIDATION-01A seam still accepts sanitized
SearchResultCandidate records only. Its provider_preference_hint is only a hint;
it creates no fetch/read, EvidenceLedger, citations, source-obligation
satisfaction, Sufficiency, FinalAnswerPacket, Author, partial-answer readiness,
or product correctness authority.

## Meaning And Authority Distinctions

| Stage | What it establishes | What it does not establish |
| --- | --- | --- |
| Search candidate | A sanitized provider-returned discovery candidate tied to authorized search intent. | A separate exact-URL transport, readability, custody, evidence, citation eligibility, material need, or support. |
| Readable content | Bounded sanitized content obtained from a candidate. | Custody, semantic support, or source-obligation satisfaction. |
| EvidenceLedger custody | Canonical possession and lineage for candidate/content material. | Meaning, coverage, readiness, or answer authority. |
| Semantic proposal | Analyst- or worker-proposed interpretation, gap, amendment, or validation. | Admitted meaning or canonical mutation. |
| SemanticObservation | RunKernel-admitted evidence-relative meaning. | ComponentCoverage or final readiness by itself. |
| ComponentCoverage | Admitted support/blocker posture against current components and obligations. | Whole-answer readiness or packet packaging. |
| ComponentWorkGraph admission | Current direct and synthesized graph authority. | Sufficiency or answer readiness. |
| Sufficiency | Whether admitted state is ready, partial, blocked, contested, insufficient, or not applicable. | New claims, synthesis, or prose. |
| FinalAnswerPacket | An authority manifest packaging readiness-approved material. | Evidence interpretation, support repair, or prose rendering. |
| Author | Presentation of packet-authorized material. | New claims, synthesis, evidence, support, or authority. |
| Quantitative finalization validation | Deterministic claim/literal binding before accepted prose. | Semantic equivalence inference, calculation, conversion, claim admission, or prose repair. |

These boundaries prevent common laundering errors: provider-returned snippets
and excerpts are not fetched/read page content; search candidates are not
evidence or acquisition need; fetch/read content is not semantic support; custody is not coverage;
Analyst proposal is not RunKernel authority; graph admission is not readiness;
and readable prose is not product correctness.

## Contract Mutation And Recovery

The `initial_answer_contract` is immutable genesis state.
`current_answer_contract` is the latest accepted contract after RunKernel
applies admitted amendments. SearchExecutorHandoff and every downstream
contract-bound reducer prefer the current contract.

Workers may propose typed changes such as adding or revising a component,
adding a source or fetch/read obligation, adding a caveat, marking an
obligation satisfied/failed/blocked/not-applicable, or prohibiting an upgrade.
Only RunKernel may admit and apply those changes.

Follow-up and recovery proposals are not dispatch. RunKernel owns their exact
work identity, budget, duplicate-work checks, current-contract lineage, and
ordinary research re-entry. The installed multi-component recovery is bounded
to one missing component and one graph/contract amendment, remains within the
five-component graph cap, and leads to affected-only recomputation.

## Specialist And Supporting Calculation Capabilities

The generic Specialist substrate remains closed by default and owns typed
proposal, registry, policy, work/disposition/result, separate-budget, unified-
handoff, and D-prime consumption contracts. The ordinary CLI/UI path composes
the fixed product registry/policy for `specialist.source_bound_calculation`.

That adapter operates only on exact literals selected through repository-owned
transient component or synthesis catalogs. It uses deterministic Decimal
parsing and operator-specific roles, derives units and precision, and records
claim alignment. Synthesis operands prove the literal through each admitted
component claim to underlying current evidence. Component work has priority
over a later synthesis need for the single serial unit. Results and
nonexecution dispositions remain proposal-stage inputs and have no direct
ComponentCoverage, Sufficiency, FinalAnswerPacket, Author, citation, source-
obligation, search, acquisition, contract-mutation, or product-correctness
authority. Estimates, arbitrary formulas, conversions, and number invention
remain unsupported.

Source posture comes from the structured candidate first and exact passage
fallbacks second. Missing class, tier, currentness, or conflict remains unknown;
neither fact acceptance nor component admission supplies a favorable default.
Synthesis inherits the underlying component evidence posture. The proposal
contract, full catalogs, and source material do not enter canonical RunKernel,
scheduler, graph, result, log, or trace projections.

## Live And Operator Boundaries

Live provider, model, search, fetch/read, retrieval, and product work is
separately licensed. An operator procedure or available adapter does not grant
that authority. Search-only live proof is not product proof.

When live work is relevant, use
[Validation Buckets](../codex/VALIDATION_BUCKETS.md), the live-safety rules in
[Build / Proof / Repair Playbook](../codex/ARCHITECTURE_GROOVE_PLAYBOOK.md), and
the applicable owner under `docs/operator/`. Provider contact remains behind a
licensed product or generic provider-proxy boundary; it is not licensed by this
architecture contract.

## Supporting And Historical Context

[Cross-Component Analyst Workbench](CROSS_COMPONENT_ANALYST_WORKBENCH.md)
preserves the proposal-only role rationale and V0 provenance. The bounded
single-relation D-prime, hardened FinalAnswerPacket, and AuthorProse surfaces
remain reusable or historical support where their exact contracts apply. They
do not override the ordinary integrated loop or create parallel authority.

Historical merge-stable SearchExecutor record: PR #330 / AG-SEARCH-EXECUTOR-HANDOFF-01; handoff consumes current_answer_contract when present; Scout/revision material is search direction only; handoff creates search task records and a search work packet; no live search/provider/fetch/read/retrieval calls were run; no EvidenceLedger/citations/source-obligation satisfaction; next implementation gate after AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01 is AG-LIVE-XAXIS-VALIDATION-01A.
That verbatim record describes the historical pre-search handoff only. Its old
gate clause is not current roadmap authority, and it does not turn the new
ordinary post-discovery reference handoff into search execution.

Passive packets, projections, fixtures, and traces are not product readiness.
A new packet or bridge requires a real trust/custody boundary, durable reducer
input, stable identity consumed downstream, raw/private hygiene boundary, or a
named blocker removed for an existing consumer.

## Nonproofs

This contract does not prove arbitrary-query support, live acquisition quality,
messy-source semantic correctness, citation rendering, source-obligation
satisfaction, broad answer quality, or product correctness. It does not license
new providers, prompts, retrieval behavior, source ranking, Author behavior,
additional Specialist capabilities, or calculator scope expansion. Installed
offline activation does not prove live calculator correctness, exact-URL READ,
Focused Extract, final custody, Serper connection, Map, Crawl, compatibility
rename, or broad quantitative reasoning quality. No live provider, model,
search, DNS, fetch/read, Map, Crawl, or retrieval call was made for the completed
`EXACT-URL-NETWORK-TARGET-SAFETY-OWNER-01` Repair. That Repair installed the
canonical pure safety policy and stage-bound RunKernel decisions without
activating READ, Focused Extract, final custody, semantic admission, or planner
disambiguation. `EXACT-URL-ACQUISITION-AND-FINAL-CUSTODY-CONVERGENCE-01` is now
blocked until at least one provider operation is truthfully eligible for
untrusted exact URLs. Current Linkup/Tavily eligibility remains unasserted due
to insufficient committed public-target guarantees or observable final-target
lineage, not because either provider is declared inherently unsafe.
