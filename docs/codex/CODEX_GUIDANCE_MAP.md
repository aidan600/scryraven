# Coding Agent Guidance Map

Status: current
Authority: canonical:task-routing
Default-read: yes

Root `AGENTS.md` is the always-loaded vendor-neutral contract. This map is a
router, not an installed-state summary, roadmap, architecture body, or phase
history. Read only the smallest owner set needed for the task.

## Smallest Default Read Path

1. Read root `AGENTS.md`.
2. Read this routing map.
3. Read [ScryRaven Current State](../architecture/SCRYRAVEN_CURRENT_STATE.md).
4. Read one exact concern-specific architecture owner routed below.
5. Read [Current Roadmap](../roadmap/CURRENT_ROADMAP.md) only for prioritization
   or phase selection.
6. Read validation or operator documents only when the phase licenses them and
   they are relevant.

The root [README](../../README.md) owns setup and public usage. It is not a
default architecture authority. Historical documents are read only when a
current owner routes to them or a phase explicitly targets history. ChatGPT
Project Sources are external context, not repository files, and their filenames
must not be treated as paths in this repository.

## Temporal Owners

| Concern | Exclusive owner |
| --- | --- |
| Current installed product state, supported envelope, not-installed list, and explicit nonproofs | [ScryRaven Current State](../architecture/SCRYRAVEN_CURRENT_STATE.md) |
| Current priority, sequence, and checkpoint definitions | [Current Roadmap](../roadmap/CURRENT_ROADMAP.md) |

Do not infer current status or next work from completed phase chronology in a
deep contract, workflow guide, PR record, or historical document.

## Phase Operation

| Task | Canonical owner |
| --- | --- |
| Build / Proof / Repair workflow, Path B, phase sizing, convergence, validation-job separation, acceptance ownership, review loop, and final bundle | [Architecture Groove Playbook](ARCHITECTURE_GROOVE_PLAYBOOK.md) |
| Execution profiles, causal clusters, checkpoints, surface licensing, and delegation posture | [Agentic Coding Operating Profile](AGENTIC_CODING_OPERATING_PROFILE.md) |
| Compact phase prompt | [Phase Brief Template](PHASE_BRIEF_TEMPLATE.md) |
| Conditional proof, live, harness, migration, or delegation fields | [Phase Brief Addenda](PHASE_BRIEF_ADDENDA.md) |
| Bundled internal milestones | [Execution Plan Template](EXECUTION_PLAN_TEMPLATE.md) |
| Proof class, product delta, consumer seam, and nonproofs | [Proof Class and Actual App Delta Gate](PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md) |
| Test classification and promotion | [Test Classification Library](TEST_CLASSIFICATION_LIBRARY.md) |
| Validation scope and commands | [Validation Buckets](VALIDATION_BUCKETS.md) and [CI Validation Ergonomics](CI_VALIDATION_ERGONOMICS.md) |
| Windows sandbox, Git, push, and draft PR | [Windows Sandbox Publication Rule](CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md) |

The phase brief declares `Mode: BUILD | PROOF | REPAIR`. Build is the default;
Proof is an explicit exception with a named blocker and mandatory next Build
checkpoint; Repair fixes a named integrity defect. Do not copy these manuals or
completed-phase chronology into phase briefs.

## Architecture Owners

| Concern | Read first |
| --- | --- |
| D-prime role and authority (`canonical:dprime-role-contract`) | [D-prime Architecture](../architecture/DPRIME_ARCHITECTURE.md) |
| Integrated query-to-answer semantic loop (`canonical:run-contract-semantic-loop`) | [Run-Contract Semantic Loop](../architecture/RUN_CONTRACT_SEMANTIC_LOOP.md) |
| Component DAG, scheduling, leases, and concurrency (`canonical:component-dag-scheduling-concurrency`) | [RunKernel Component DAG, Scheduling, And Concurrency](../architecture/RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md) |
| FAP packaging, Author rendering, and blocked terminal (`canonical:fap-author-boundary`) | [FinalAnswerPacket / Author Boundary](../architecture/FAP_AUTHOR_BOUNDARY.md) |
| Installed bounded ordinary multi-component runtime (`canonical:bounded-multicomponent-runtime`) | [Multi-Component Synthesis Runtime Architecture](../architecture/MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md) |
| Cross-component Analyst proposal contract | [Cross-Component Analyst Workbench](../architecture/CROSS_COMPONENT_ANALYST_WORKBENCH.md) |
| Analyst Workbench | [Analyst Workbench Full Slice](../architecture/ANALYST_WORKBENCH_FULL_SLICE.md) |
| Scrutineer | [Scrutineer Review](../architecture/AG_SCRUTINEER_REVIEW_01.md) |
| Specialist calculation | [Specialist Source-Bound Calculation](../architecture/AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md) |
| SufficiencyReadiness | [Sufficiency Partial-Answer Readiness](../architecture/AG_SUFFICIENCY_PARTIAL_ANSWER_READINESS_01.md) |
| Hardened FinalAnswerPacket | [Final Answer Packet Hardening](../architecture/AG_FINAL_ANSWER_PACKET_HARDENING_01.md) |
| Author prose finalization | [Author Prose-Only Finalization](../architecture/AUTHOR_PROSE_ONLY_FINALIZATION_01.md) |

## Routed Support

Routed-support documents are neither current-state nor roadmap owners. Read
the exact canonical concern owner first and use supporting material only for
its narrow responsibility:

| Narrow concern | Supporting document |
| --- | --- |
| Current-path/quarantine classification detail | [AG Current Path Quarantine](../architecture/AG_CURRENT_PATH_QUARANTINE_01.md) |
| Historical provenance, only when a current owner or phase explicitly requires it (last resort; not default-read) | [Historical Document Index](../history/INDEX.md) |

## Authority And Orchestration

| Task | Canonical owner |
| --- | --- |
| RunAuthority / RunKernel migration | [RunAuthority Implementation Guide](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md) |
| Orchestrator strangulation and surface vocabulary | [Orchestrator Authority Strangler Map](../architecture/AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md) |
| Authority-vocabulary audit | [Authority Doctrine Detritus Audit](../architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md) |
| Source-class recovery dispatch | [Provider Review Allocation Burndown](../architecture/AG95Q_PROVIDER_REVIEW_ALLOCATION_BURNDOWN.md) |
| Legacy Controller handoff, only when explicitly selected | [Controller Authority Implementation Playbook](CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md) |

`core/pipeline_orchestrator.py` remains a coordination shell with authority
debt. A zero line delta is a scope-control fact, not architecture success.

## Provider And Operator Routing

| Concern | Read first |
| --- | --- |
| Provider acquisition classification | [Generic Provider Proxy/Broker Operator Flow](../operator/GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md) |
| Separately licensed trusted-local broker reactivation | [Broker Reactivation Runbook](../operator/BROKER_REACTIVATION_RUNBOOK.md) |

Provider-facing work must declare product integration or testing/operator
broker-doorman work. Broker output is sanitized provider material only; it is
not evidence custody, citation eligibility, source-obligation satisfaction, or
answer material.

The capability inventory / reuse-first gate also applies to the generic
single-relation dogfood path: route planning, acquisition, source/readiness,
and D-prime integration work to existing owners before adding machinery.

## Live Validation

Live provider, model, search, fetch/read, retrieval, and product validation are
disabled unless the phase completes the live-validation addendum with exact
scope, call cap, budget, redaction boundary, artifact path, decision, and stop
condition. Live-search-only proof is not live product proof.

## Conflict Routing

Direct instructions and the current phase win over older repository prose.
Code/tests and the canonical current-state owner win over mixed-status support
material. Stop when a real conflict requires a product choice, architecture
fork, closed-surface change, live/private access, or destructive Git.
