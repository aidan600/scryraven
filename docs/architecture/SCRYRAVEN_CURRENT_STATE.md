# ScryRaven Current State

Status: current
Authority: canonical:current-installed-state
Default-read: yes
Applies-to: current ordinary product implementation and explicit nonproofs
Does-not-authorize: live calls, arbitrary-query claims, roadmap execution, or closed-surface changes
Verified-against-runtime: 7626f1628a18bfb70c7abe58b120dc84001f2e71
Update-trigger: merged change to installed product behavior, supported envelope, or explicit nonproofs

## Purpose And Source-Of-Truth Rule

This document is the sole repository owner of temporal installed-state truth.
Code and focused tests remain the executable authority; when they disagree with
this summary, treat the summary as stale and repair it. Deep architecture owners
define contracts and rationale, while the roadmap owns sequence. Neither makes a
capability installed merely by describing it.

## Supported Ordinary Entrypoints And Query Boundary

The public CLI is the current supported executable interface. Both
`python -m scryraven` and the compatible `python -m proplex` entrypoint consume
the backend pipeline and the installed path described below. Bounded
multi-component behavior applies only to the named query class
`ordinary-bounded-multicomponent-factual-synthesis-v1`. Nonqualifying and
single-component requests retain their established direct ordinary path. The
ordinary CLI/backend composition no longer injects or executes the legacy
Economist callable.

One deterministic query-shape assessment now qualifies explicit bullet,
contiguous numbered, and bounded repeated-imperative requests containing two
through five distinct factual components plus a separated request-level
synthesis directive. It preserves component order and the exact directive
through AnswerContract, scheduler context, and Cross-Component Analyst input.
Malformed or ambiguous structured candidates remain unselected, and the
existing general multipart fallback remains separate and does not grant route
eligibility. Fast, Balanced, and Deep consume this same parser and route
pipeline.

The legacy Streamlit shell, its home-page UI, and saved-thread Streamlit
follow-up are not ordinary product consumption. The retained `ui/` source is
reference and migration material pending separately licensed physical cleanup,
and `app.py` is a fail-closed retirement tombstone. No current UI framework is
selected. Future UI work must consume transport-neutral application services;
future conversation and follow-up product work must likewise be transport-neutral
and explicitly activated.

Nothing here proves arbitrary-query multi-component support or widens any
provider, model, search, retrieval, or live-validation license.

## Installed Capability Table

The identifiers below are documentation sentinels, not runtime flags or public
configuration.

| Marker | Installed behavior for the supported class |
| --- | --- |
| `MC-P1-ORDINARY` | Component Analyst and component D-prime feed RunKernel component admission; ComponentWorkGraph V1, Cross-Component Analyst, synthesis D-prime, and the full Scrutineer posture when triggered feed canonical graph/synthesis admission. The result is consumed by ordinary Sufficiency, FinalAnswerPacket, Author, RunOutcome, and CLI-visible output, with safe blocked non-Author terminal behavior where required. |
| `MC-P2-DYNAMIC-RECOVERY` | One bounded missing-component recovery may amend the AnswerContract, re-enter ordinary research, admit the recovered component, and resume the governed graph. |
| `MC-P3-SELECTIVE-RECOMPUTE` | Recovery invalidates and recomputes only the affected synthesis closure while exact unaffected admitted synthesis is carried forward under new deterministic authority. |
| `MC-P4-SCHEDULER-LEASES` | RunKernel owns semantic-work scheduling and exact work/budget leases, including grant-first dispatch, pretransport spend commitment, cancellation accounting, and terminal zero-active-lease enforcement. |
| `MC-P5A-HOSTED-W2` | Scheduler V2 permits hosted OpenAI/OpenRouter initial component Analyst and D-prime width 2. Local and unsupported/conservative execution remain width 1. Batch grant, cancellation, dispatch spend, and child-action publication are atomic; transport-only workers may overlap, while canonical reduction remains deterministic on the main thread. |
| `MC-P5A-STRICT-ONE-SHOT` | Provider-faithful transport is strict one-shot: at most one provider request per child, no SDK retry, and no endpoint, provider, or model fallback. Unsupported providers fail closed with zero requests. |
| `MC-P5A-SAMPLING-COMPAT` | OpenRouter and Local chat transport internally own temperature `0.3`; OpenAI Responses omits temperature; caller-authored temperature is rejected. |
| `MC-P5A-MAIN-THREAD-COST` | Response-bearing model cost is recorded on the main thread before deterministic canonical reduction. |
| `SPECIALIST-S0-GENERIC` | Component Analyst, Cross-Component Analyst, and full Scrutineer may emit one exact candidate mapping under `specialist_need_proposal_v1`. Generic S0 rejects missing/stale schema, unknown envelope/target fields, raw/private material, authority claims, aliases, recursion, and invalid posture before RunKernel admission; it never normalizes them into validity. RunKernel alone binds a valid candidate to current authority. Invalid candidates retain only a bounded receipt and create no Specialist work or derived authority; required/unclassified cases block while optional cases contribute nothing. Closed defaults register and enable no product capability. |
| `SPECIALIST-S1-QUANTITATIVE` | The ordinary CLI composes one fixed product registry/policy for `specialist.source_bound_calculation` on the named bounded multi-component class. Component and ordinary Cross-Component Analyst receive exact contract `quantitative_specialist_proposal_contract.v2`; before work creation the current contract instance, role input/artifact, target, source aliases, fixed fields, and capability request are re-proved and validated. Malformed proposals create no work, spend, lease, batch, dispatch, result, handoff, or downstream Specialist authority. Required malformed needs block dependent claims; optional malformed needs permit only independently supported continuation. Valid behavior remains one serial unit with component-before-synthesis priority, deterministic execution, canonical `result_unit`, and existing D-prime custody. |
| `QUANT-FINALIZATION-CONTAINMENT` | The ordinary `AuthorExecutor`, deterministic `AuthorProseFinalization`, and guarded follow-up response finalizer each use one claim-scoped quantitative authority manifest and the same deterministic post-prose validator. Direct source-explicit propositions and exact completed S1 propositions remain eligible only through their complete source or Specialist/D-prime lineage. Generic D-prime admission alone grants no numeric authority. Unsupported arithmetic, conversion, unit, precision, sign, scale, percentage, rate, subject, result, or same-value proposition reuse fails before successful finalization, without sentence surgery or automatic Author retry. |
| `PROVIDER-CAPABILITY-ROUTING` | `core.routing` owns one deterministic capability catalog and route policy. Ordinary `run_pipeline()` records one capability-compatible provider or a typed block in ProviderPlan, carries the decision through scheduling, and dispatches mechanically. General/domain-targeted discovery is Linkup `standard/searchResults` first with Tavily as a descriptive fallback; exact academic/technical/semantic discovery selects Exa; explicit Serper/Brave roles remain candidate-only. |

The shared parser keeps factual numeric assertions inspectable when they appear
under source/reference headings, in Markdown bullets, brackets, accounting
parentheses, compact currency or compact currency-rate forms, or bounded
hyphenated-cardinal forms. Only rows matching a bounded affirmative
reference-only grammar are omitted; ambiguous reference-noun rows remain
inspectable. Numeric-looking nontransport surfaces that the bounded exact parser
does not normalize, including factual word ordinals and unconsumed superscript
or subscript digits, receive an enum-only unsupported marker and fail closed.
Accounting currency parentheses retain a negative sign posture rather than
collapsing to positive.

## Current Ordinary Multi-Component Flow

For a qualifying request, the ordinary entrypoint selects the bounded class,
derives component work, and runs component Analyst and D-prime work under
RunKernel-owned scheduler leases. The ordinary CLI product composition uses
Scheduler V3; generic closed-default and no-need runs remain V2-compatible.
RunKernel admits component state;
Cross-Component Analyst proposes synthesis; synthesis D-prime validates it; and
RunKernel admits canonical graph/synthesis state. Scrutineer may trigger the one
bounded recovery and selective recomputation cycle. The resulting admitted state
continues through ordinary Sufficiency, FinalAnswerPacket, Author, RunOutcome,
and CLI output, or reaches the safe blocked non-Author terminal when required.

Hosted width-2 overlap is limited to eligible initial component transport.
Canonical mutation, graph reduction, synthesis, recovery, selective
recomputation, Scrutineer, Sufficiency, FinalAnswerPacket, and Author remain
serial on the main product thread.

In the fixed ordinary product composition, typed quantitative Specialist work
is inserted between its originating proposal and the applicable D-prime review.
It remains serial on the main thread, consumes no semantic-envelope unit, and
has no admission or answer authority. Exact Scrutineer synthesis-leaf
remediation requires fresh synthesis D-prime and fresh Scrutineer review. A
failed predispatch reconstruction retains no input or result, returns its
reservation with zero spent units, and exposes one typed handoff. Optional
failure remains visible to D-prime and continues; required failure leaves the
handoff pending because D-prime does not run, then reaches the existing safe
non-Author terminal.

The installed quantitative adapter accepts only exact selected literals from
transient component or synthesis catalogs. Synthesis operands require proof
through the admitted component claim to the same literal in underlying current
component evidence. Decimal arithmetic, unit/precision derivation, and exact
claim alignment are deterministic. Estimates, arbitrary formulas, conversions,
number invention, and acquisition remain unsupported.

The model-visible quantitative proposal contract is versioned and digest-bound;
the same declarative field, operator, and bound facts are consumed by runtime
validation before Specialist work creation. The parsed proposal must supply the
exact generic instance schema and is retained only transiently; unknown fields,
fixed-value drift, target/source mismatch, and malformed requests are not
softened. Missing source posture is not treated favorably, and component
admission cannot upgrade underlying evidence. Contract, full catalog, and source
material retention remains closed outside the transient role/adapter scope.

At finalization, FinalAnswerPacket projects current numeric authority by claim,
not as a global value/unit allowlist. Ordinary Author receives fixed no-
calculation/no-conversion instructions and exact transient renderings. Candidate
prose is buffered and deterministically validated before display or successful
Author reduction. Deterministic AuthorProse and the guarded follow-up response
finalizer consume the same validator. A failed check creates no accepted
AuthorProse or final answer outcome and does not trigger a model retry.

The guarded follow-up response-finalization capability remains installed
internal supporting machinery; its availability does not establish ordinary
saved-thread product consumption. The old saved-thread Streamlit follow-up path
through `ui.pages_followup` and `core.followup` is legacy and retired from
ordinary product use. It is not a current consumer of the guarded finalizer or
the shared validator. Any future conversation or follow-up activation must
consume the shared accepted-prose validator through transport-neutral
application services and must be explicitly activated.

The hardened `SufficiencyReadiness -> HardenedFinalAnswerPacket ->
AuthorProseFinalization` route preserves two component-scoped quantitative
authority classes. Hardened direct source-explicit numeric authority requires
exact current component, semantic-observation, content, coverage,
evidence-custody, proposition-fingerprint, and complete literal-signature
binding. Completed component S1 authority preserves the installed capability
and version, result and handoff identities and digests, canonical component
target, exact claim-material binding, canonical `result_unit` and precision,
and terminal consumption by the applicable component D-prime. Generic D-prime
admission alone remains nonauthority for arithmetic, conversion, aggregation,
comparison, or same-value proposition reuse. Deterministic AuthorProse accepts
valid bound direct-source and component S1 numeric claims and fails atomically
on unsupported quantitative prose.

The current hardened FinalAnswerPacket owner packages component entries only.
It does not project synthesis entries and does not install a hardened synthesis
sidecar. Ordinary synthesis-origin S1 authority remains owned by the ordinary
ComponentWorkGraph / synthesis D-prime / ordinary FinalAnswerPacket path.

Cross input reproof is unconditional. The ordinary caller may prove the exact
transient packet directly; RunKernel independently reconstructs it from current
scheduler-owned component Analyst packets and their existing scheduler
authority digest. Missing or stale reconstruction authority fails before graph
reduction, and no packet, contract, catalog, or source material is newly
retained or exported.

## Component-Gap Recovery Eligibility And Custody

Every supported mode now resolves the recovery-related slice of one shared
mode-policy envelope. The installed values are temporary compatibility values,
not permanent mode design: `Balanced` preserves the existing one-cycle,
offline-only, existing-candidate-query eligibility; `Fast` is recovery-closed in
this phase; and `Deep` is recovery-closed pending a later explicit mode-policy
decision. Unsupported modes resolve the same envelope shape with
`mode_supported=false` and fail closed. No permanent mode budget was selected.
This contained recovery posture was installed at
`ffd6796e37fac468c826afd29767aafe1e235f41` and remains unchanged by the later
Specialist proposal-admission repair.

Every resolved envelope enters the same mode-neutral coordinator and recovery
primitive. Closed Fast and Deep values return an unrecorded non-applicable
result before adapter invocation, so they create no component-gap recovery
history or projection; unsupported mode returns an unrecorded blocked result.
Eligible Balanced execution requires an explicitly composed offline adapter.
The primitive then uses RunKernel authorization and admits recovered evidence
and component coverage through RunKernel's canonical EvidenceLedger and semantic
component-coverage state. Only the canonically committed recovered passages
return to the orchestrator. Initial and post-recovery final evidence,
selected-authority Author evidence, and Author prompt material consume the same
ordinary typed materialization handoff and its existing mechanical owners;
recovery supplies none of those authority fields. Sufficiency runs again from
the current canonical state before FAP can package material, and Author can run
only from the resulting FAP payload.

The supported ordinary CLI composition still supplies no component-gap recovery
adapter. It therefore cannot complete this recovery cycle: required missing
coverage remains fail-closed and a blocked FAP does not call Author. No live
recovery composition, provider call, generated recovery query, accepted contract
amendment, permanent Deep recovery behavior, or permanent Fast/Balanced/Deep
recovery budget profile was installed.

## Retired Legacy Economist Ordinary Execution

Legacy Economist execution is retired from the ordinary CLI/backend product
path. The ordinary orchestrator no longer gates, preflights, schedules, or calls
the Economist, and current dependency composition does not inject
`run_economist_step`. Configuring `OPENAI_API_KEY` does not restore that path.
The former quantitative-preflight Author note is likewise absent. That
retirement did not itself change Linkup acquisition; current Linkup
`searchResults` eligibility is now owned by the later provider-capability
routing foundation below. The separate provider-synthesis precision path is
retired.

The `RunDeps.run_economist_step` field remains optional and unread as an
isolated compatibility shape. The legacy implementation, its direct
source-binding and code-execution safety tests, retained Streamlit references,
and passive handoff/trace fields remain repository-visible legacy material.
Ordinary traces identify retirement explicitly, keep `economist_ran` false and
`economist_seconds` zero, and do not produce an Economist packet. Those fields
are compatibility data, not a dormant execution route or future authority.

This retirement installs no replacement economic Specialist. The existing S1
`specialist.source_bound_calculation` capability remains the only installed
bounded quantitative Specialist: it performs deterministic calculations from
exact selected source literals inside the named bounded multi-component class.
It does not provide broad economic analysis, arbitrary formulas, estimates,
acquisition, or general quantitative reasoning.

## Installed Provider-Capability Routing

Runtime/test commit `7626f1628a18bfb70c7abe58b120dc84001f2e71`
replaced the ordinary provider-name-first selector with one provider-neutral
capability decision. `core.routing` is the sole policy owner;
`ProviderPlan`, retrieval scheduling, dispatch, and `run_pipeline()` are
ordinary consumers. Each acquisition job has exactly one selected provider or
a typed blocked decision. Empty or unavailable selection does not manufacture
Tavily, fallback candidates never dispatch, and ordinary selection no longer
creates a Tavily/Linkup/Exa ensemble.

General and domain-targeted discovery select Linkup
`standard/searchResults` when available and otherwise select compatible Tavily
Search. Academic/technical/semantic discovery selects Exa exactly, with Linkup
standard and Tavily recorded only as degraded alternatives when applicable.
Explicit Serper lightweight-disambiguation and Brave independent-index roles
remain candidate-only. News, quantitative posture, mode, and generic complexity
do not create a provider identity or promote Linkup to deep. Exact include and
exclude domains are preserved without granting social authority.

Provider availability records booleans only for Tavily, Linkup, Exa, Serper,
and Brave. Provider material remains non-authoritative acquisition material
until existing downstream custody acts. Provider synthesis remains disabled,
and Scrutineer-authorized `deep/searchResults` remediation remains the only
current ordinary Linkup Deep boundary. The full contract is owned by
[Provider Capability And Acquisition Routing](PROVIDER_CAPABILITY_AND_ACQUISITION_ROUTING.md).

## Retired Legacy Semantic Scout And Ordinary Provider Synthesis

Legacy semantic Scout ordinary execution is retired. The ordinary product does
not select a Scout prompt, make a Scout model call, create Scout QueryPlan
candidates, consult a Scout continuation gate, or schedule Scout retrieval.
The Scout-specific QueryPlan finalizer, scheduler stage
`scout_directed_continuation`, provider role `scout_continuation`, and hard-coded
`exa/linkup` override are absent from their current ordinary owners. Evaluator,
expander, generic QueryPlan admission, RunKernel continuation authority,
retrieval-stop policy, disambiguation, weak-corpus recovery, and source-class
recovery remain installed.

`core.scout` now exposes only fixed inert import compatibility for the retained
`core.pipeline` re-export and bounded validation composition: `run_scout`
returns no result and performs no prompt lookup, model call, parsing, or query
production. Ordinary CLI composition does not inject the optional legacy Scout
or Linkup precision dependencies. Retained Scout execution/session fields are
passive compatibility projections for persistence, review, and aggregate
consumers: ordinary values are fixed false, empty, retired, or zero, and the
retired gate projection is not supplied to current continuation, retrieval-
authority, or dispatch decisions.

Ordinary Linkup provider synthesis is also retired. No ordinary eligibility,
call, response-processing, or Analyst-context path uses Linkup
`deep/sourcedAnswer`, so provider-written answers cannot enter ordinary Analyst
input through the former precision block. The lower-level precision helper is
retained only for named offline diagnostics and provider-error validation;
generic acquisition continues to reject `sourcedAnswer`. Ordinary Linkup
`searchResults`, including Scrutineer-authorized `deep/searchResults`
remediation, remains unchanged.

This repair installed no provider-capability routing, provider ordering, Linkup
Fetch, Tavily site acquisition, replacement semantic role, or live validation.

## Not Installed

- Arbitrary-query multi-component support.
- Legacy Economist execution in ordinary CLI/backend runs.
- Legacy semantic Scout execution in ordinary CLI/backend runs.
- Ordinary Linkup provider-written answer synthesis.
- A replacement economic Specialist or broad quantitative reasoning agent.
- Social-source acquisition or a Social Awareness specialist.
- Additional product Specialists, arbitrary formulas, estimates, or unit/currency conversion.
- Adaptive provider concurrency or Local component parallelism.
- Graph-bound, synthesis, recovery, selective, or Scrutineer parallelism.
- Hardened synthesis entries or a hardened synthesis sidecar.
- Permanent Fast/Balanced/Deep graph or semantic-call budgets.
- Hosted or Local capacity characterization.
- A selected current UI framework or final UI/productization work.
- An ordinary saved-thread conversation or follow-up product workflow.
- Linkup Fetch or Tavily Extract, Map, or Crawl acquisition.
- General Linkup Deep activation or provider-failure cross-provider retry.

## Not Proved

- No live validation was performed.
- Arbitrary-query decomposition and broad route qualification remain unproved.
- No acquisition-completeness repair was performed.
- No provider transport adapter or model changed; ordinary provider routing changed.
- No S1 capability, route eligibility, budget, scheduling order, recursion, or
  parallelism expanded.
- No new Specialist capability was added.
- No hardened synthesis path was activated.
- Broad live correctness, answer quality, and production stability remain
  unproved.
- Broad live end-to-end product correctness or competitive answer quality.
- Live quantitative correctness or broad quantitative reasoning quality.
- Broad ordinary quantitative or economic-analysis replacement coverage.
- Arbitrary-query readiness.
- Maximum useful hosted or Local concurrency.
- Production stability across normal user traffic.
- Social representativeness or sentiment correctness.

Installed offline architecture must not be represented as live-product
validation.

## Compatibility And Naming Notes

ScryRaven is the public project name. Compatibility names including `proplex`,
`python -m proplex`, `PROPLEX_*`, `proplex.db`, and `proplex_*` state keys remain
supported. RunKernel / RunAuthority is the current authority direction;
`core/pipeline_orchestrator.py` remains a coordination shell with authority debt,
and this document does not license changes to that surface.

## Canonical Architecture Links

- [Multi-component synthesis runtime architecture](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md) owns the deep installed multi-component contracts.
- [Specialist graph substrate](SPECIALIST_GRAPH_SUBSTRATE.md) owns generic Specialist proposal, registry, policy, work, result, scheduling, and validator-consumption contracts.
- [Quantitative Specialist product activation](AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md) owns the installed calculator registry/policy, model-visible proposal contract, evidence bridge/quality, source catalogs, parser, provenance, claim alignment, and handoff use.
- [D-prime architecture](DPRIME_ARCHITECTURE.md) owns component and synthesis D-prime role boundaries.
- [Run-contract semantic loop](RUN_CONTRACT_SEMANTIC_LOOP.md) owns the integrated query-to-answer proposal and reduction flow.
- [RunKernel component DAG, scheduling, and concurrency](RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md) owns graph, scheduler, lease, batch, and concurrency invariants.
- [Cross-component Analyst Workbench](CROSS_COMPONENT_ANALYST_WORKBENCH.md) owns its concern-specific proposal contract.
- [FAP / Author boundary](FAP_AUTHOR_BOUNDARY.md) owns final packet and prose boundaries.
- [Quantitative finalization containment](AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md) owns claim-scoped numeric projection and accepted-prose validation across active finalizers.
- [RunAuthority implementation guide](../codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md) owns authority-migration procedure.

## Current Roadmap

Prioritization and phase selection are owned exclusively by
[Current Roadmap](../roadmap/CURRENT_ROADMAP.md). Planned capabilities are not
installed-state claims.

## Historical Provenance

The former Controller-era rollup remains at
`docs/history/architecture/SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md`.
Completed phase records and Git history preserve the Phase 1-5A chronology and
rationale. Read them only when a current owner routes to them or a phase
explicitly targets history; they do not override this owner.
