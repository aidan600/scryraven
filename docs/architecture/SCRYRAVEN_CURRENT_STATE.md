# ScryRaven Current State

Status: current
Authority: canonical:current-installed-state
Default-read: yes
Applies-to: current ordinary product implementation and explicit nonproofs
Does-not-authorize: live calls, arbitrary-query claims, roadmap execution, or closed-surface changes
Verified-against-runtime: bba0d16313944b742251298b4fc929b4ceb55d76
Update-trigger: merged change to installed product behavior, supported envelope, or explicit nonproofs

## Purpose And Source-Of-Truth Rule

This document is the sole repository owner of temporal installed-state truth.
Code and focused tests remain the executable authority; when they disagree with
this summary, treat the summary as stale and repair it. Deep architecture owners
define contracts and rationale, while the roadmap owns sequence. Neither makes a
capability installed merely by describing it.

## Supported Ordinary Entrypoints And Query Boundary

The ordinary ScryRaven application pipeline, including the compatible
`python -m proplex` CLI, consumes the installed path described below. Bounded
multi-component behavior applies only to the named query class
`ordinary-bounded-multicomponent-factual-synthesis-v1`. Nonqualifying and
single-component requests retain their established direct ordinary path.

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
| `SPECIALIST-S0-GENERIC` | Component Analyst, Cross-Component Analyst, and full Scrutineer may emit one typed Specialist need proposal. With an explicitly injected registry and policy, RunKernel-owned Scheduler V3 can execute at most one registered deterministic capability from a separate serial compatibility pool and route one unified result-or-disposition handoff through component or synthesis D-prime. Predispatch reconstruction failure refunds once and creates the failed handoff; optional work remains nonblocking and required work safely blocks. Closed defaults register and enable no product capability. |
| `SPECIALIST-S1-QUANTITATIVE` | The ordinary CLI and home-page UI compose one fixed product registry/policy for `specialist.source_bound_calculation` on the named bounded multi-component class. Component and ordinary Cross-Component Analyst receive one repository-owned model-visible proposal contract whose schema facts also drive validation, and may nominate exact source literals through repository-owned transient catalogs. Candidate-primary source posture fails closed unless currentness, class, tier, conflict, and lineage are explicitly acceptable; synthesis inherits that posture. The deterministic adapter preserves source-explicit inputs, two-hop synthesis lineage, canonical `result_unit`, precision, assumptions, caveats, and exact claim alignment before the applicable D-prime reviews and consumes the handoff. The contract and source material are not retained in canonical projections. One serial Specialist unit gives eligible component work priority before later synthesis work. |
| `QUANT-FINALIZATION-CONTAINMENT` | Every active accepted-prose route consumes one claim-scoped quantitative authority manifest and the same deterministic post-prose validator. Direct source-explicit propositions and exact completed S1 propositions remain eligible only through their complete source or Specialist/D-prime lineage. Generic D-prime admission alone grants no numeric authority. Unsupported arithmetic, conversion, unit, precision, sign, scale, percentage, rate, subject, result, or same-value proposition reuse fails before successful finalization, without sentence surgery or automatic Author retry. |

## Current Ordinary Multi-Component Flow

For a qualifying request, the ordinary entrypoint selects the bounded class,
derives component work, and runs component Analyst and D-prime work under
RunKernel-owned scheduler leases. The ordinary CLI/UI product composition uses
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
validation. Missing source posture is not treated favorably, and component
admission cannot upgrade underlying evidence. Contract, full catalog, and source
material retention remains closed outside the transient role/adapter scope.

At finalization, FinalAnswerPacket projects current numeric authority by claim,
not as a global value/unit allowlist. Ordinary Author receives fixed no-
calculation/no-conversion instructions and exact transient renderings. Candidate
prose is buffered and deterministically validated before display or successful
Author reduction. Hardened AuthorProse and follow-up AF5B finalization consume
the same validator. A failed check creates no accepted AuthorProse or final
answer outcome and does not trigger a model retry.

Cross input reproof is unconditional. The ordinary caller may prove the exact
transient packet directly; RunKernel independently reconstructs it from current
scheduler-owned component Analyst packets and their existing scheduler
authority digest. Missing or stale reconstruction authority fails before graph
reduction, and no packet, contract, catalog, or source material is newly
retained or exported.

## Not Installed

- Arbitrary-query multi-component support.
- Social-source acquisition or a Social Awareness specialist.
- Additional product Specialists, arbitrary formulas, estimates, or unit/currency conversion.
- Adaptive provider concurrency or Local component parallelism.
- Graph-bound, synthesis, recovery, selective, or Scrutineer parallelism.
- Permanent Fast/Balanced/Deep graph or semantic-call budgets.
- Hosted or Local capacity characterization.
- Final UI/productization work.

## Not Proved

- Broad live end-to-end product correctness or competitive answer quality.
- Live quantitative correctness or broad quantitative reasoning quality.
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
