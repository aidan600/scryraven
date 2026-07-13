# Run-Contract Semantic Loop

Status: current
Authority: canonical:run-contract-semantic-loop
Default-read: no
Applies-to: integrated query-to-answer authority and proposal/reduction flow
Does-not-authorize: live calls, arbitrary-query claims, direct worker mutation, or product Specialist activation
Verified-against-runtime: 56b78b24015a75ff964b83ffcc77c4a18f24fb58
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
8. SearchExecutorHandoff derives contract-bound search intent; it is not search
   execution or evidence.
9. Separately authorized acquisition may return sanitized search-result
   candidates. Candidates are discovery records, not readable content or
   evidence.
10. Fetch/read produces bounded sanitized content references from authorized
    candidates. Readable content is not semantic support.
11. EvidenceLedger records candidate/content custody and exact lineage. Custody
    is not admitted meaning or component satisfaction.
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
19. A typed Specialist need from component Analyst, Cross-Component Analyst,
    or full Scrutineer may, only under an injected registry and policy, become
    one RunKernel-governed deterministic work item. Its bounded result or exact
    typed nonexecution disposition becomes one unified handoff for component or
    synthesis D-prime; a required predispatch reconstruction failure publishes
    that failed handoff pending and unconsumed before the ordinary path safely
    blocks without running D-prime.
20. At most one bounded missing-component recovery may amend the
    AnswerContract, re-enter ordinary research, admit the recovered component,
    and resume the governed graph.
21. Recovery invalidates and recomputes only the affected synthesis closure;
    unaffected admitted synthesis is deterministically carried forward under a
    new RunKernel authority binding.
22. Sufficiency decides readiness from admitted state. FinalAnswerPacket then
    packages only admitted, readiness-approved material.
23. Author renders a ready packet, or a blocked packet reaches the installed
    sanitized non-Author terminal. The product returns `RunOutcome`, including
    CLI-visible output when applicable.

Every semantic call in the selected multi-component loop is scheduled from
canonical ready work and carries exact RunKernel lease lineage. The driver does
not nominate the next role. Transport-only workers may overlap only within the
installed hosted initial-component width; canonical observations, admission,
graph mutation, recovery, selective recomputation, readiness, packaging, and
rendering reduce deterministically on the main thread.

## Meaning And Authority Distinctions

| Stage | What it establishes | What it does not establish |
| --- | --- | --- |
| Search candidate | A sanitized discovery candidate tied to authorized search intent. | Readability, custody, evidence, citation eligibility, or support. |
| Readable content | Bounded sanitized content obtained from a candidate. | Custody, semantic support, or source-obligation satisfaction. |
| EvidenceLedger custody | Canonical possession and lineage for candidate/content material. | Meaning, coverage, readiness, or answer authority. |
| Semantic proposal | Analyst- or worker-proposed interpretation, gap, amendment, or validation. | Admitted meaning or canonical mutation. |
| SemanticObservation | RunKernel-admitted evidence-relative meaning. | ComponentCoverage or final readiness by itself. |
| ComponentCoverage | Admitted support/blocker posture against current components and obligations. | Whole-answer readiness or packet packaging. |
| ComponentWorkGraph admission | Current direct and synthesized graph authority. | Sufficiency or answer readiness. |
| Sufficiency | Whether admitted state is ready, partial, blocked, contested, insufficient, or not applicable. | New claims, synthesis, or prose. |
| FinalAnswerPacket | An authority manifest packaging readiness-approved material. | Evidence interpretation, support repair, or prose rendering. |
| Author | Presentation of packet-authorized material. | New claims, synthesis, evidence, support, or authority. |

These boundaries prevent common laundering errors: search candidates are not
evidence; fetch/read content is not semantic support; custody is not coverage;
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

The generic Specialist substrate is installed but closed by default. It adds
typed proposal, registry, policy, work/disposition/result, separate-budget,
unified-handoff, and D-prime consumption contracts without registering a
product capability. Specialist results and nonexecution dispositions are
proposal-stage inputs and have no direct admission, Sufficiency,
FinalAnswerPacket, Author, or citation authority.

The deterministic source-bound calculator is an installed bounded supporting
capability. It operates only on already source-bound numeric inputs and
preserves formula, units, assumptions, caveats, blockers, and source lineage.
It does not decide ComponentCoverage, Sufficiency, FinalAnswerPacket, Author,
citations, contract mutation, or product correctness. Its existence does not
activate the calculator through the generic Specialist substrate.

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

Passive packets, projections, fixtures, and traces are not product readiness.
A new packet or bridge requires a real trust/custody boundary, durable reducer
input, stable identity consumed downstream, raw/private hygiene boundary, or a
named blocker removed for an existing consumer.

## Nonproofs

This contract does not prove arbitrary-query support, live acquisition quality,
messy-source semantic correctness, citation rendering, source-obligation
satisfaction, broad answer quality, or product correctness. It does not license
new providers, prompts, retrieval behavior, source ranking, Author behavior, or
product Specialist activation.
