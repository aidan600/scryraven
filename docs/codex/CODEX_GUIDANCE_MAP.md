# Coding Agent Guidance Map

Status: Current task-to-canonical-owner routing map.

Root `AGENTS.md` is the always-loaded vendor-neutral contract. Read only the
smallest additional set below that owns the task. Historical phase narratives
belong in their phase or architecture records, not in this map.

## Phase operation

| Task | Canonical owner |
| --- | --- |
| Build / Proof / Repair workflow, Path B, phase sizing, validation-job separation, acceptance ownership, review loop, final bundle | [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md) |
| Execution profile, convergence evaluation, causal clusters, coherent checkpoints, architectural-surface licensing, delegation posture | [AGENTIC_CODING_OPERATING_PROFILE.md](AGENTIC_CODING_OPERATING_PROFILE.md) |
| Compact phase prompt | [PHASE_BRIEF_TEMPLATE.md](PHASE_BRIEF_TEMPLATE.md) |
| Conditional large-phase, proof, live, harness, migration, or delegation fields | [PHASE_BRIEF_ADDENDA.md](PHASE_BRIEF_ADDENDA.md) |
| Bundled internal milestones | [EXECUTION_PLAN_TEMPLATE.md](EXECUTION_PLAN_TEMPLATE.md) |
| Proof class, product delta, consumer seam, nonproofs | [PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md](PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md) |
| Test classification and promotion | [TEST_CLASSIFICATION_LIBRARY.md](TEST_CLASSIFICATION_LIBRARY.md) |
| Validation scope and commands | [VALIDATION_BUCKETS.md](VALIDATION_BUCKETS.md) and [CI_VALIDATION_ERGONOMICS.md](CI_VALIDATION_ERGONOMICS.md) |
| Windows sandbox, Git, push, draft PR | [CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md](CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md) |

The phase brief declares `Mode: BUILD | PROOF | REPAIR`. Build is the default;
Proof is an explicit exception with a named blocker and mandatory next Build
checkpoint; Repair fixes a named integrity defect. Do not copy these manuals
into each phase brief.

## Capability inventory / reuse-first gate

Before implementing new code near mature authority or product surfaces, use the
inventory in the playbook and addenda. If existing current capability may
already own the responsibility, stop for capability inventory instead of
building a parallel surface.

Classify each surface `REUSE`, `ADAPT`, `UPGRADE`, `RETIRE`, or `REPLACE`:

```text
Surface:
Existing owner module/doc:
Current consumer:
Current status:
Action:
Why not duplicate:
Tests/guards:
```

Trigger surfaces include D-prime / DPrime, Analyst /
EvidenceRelativeAnalysisPacket, source authority, source obligation, citation
eligibility / citation-source handoff, SufficiencyReadiness, FinalAnswerPacket /
FAP, Author, SemanticObservation, ComponentCoverage, RunKernel admission /
RunKernel authority, follow-up / recovery, SearchPlanner / query planner,
model-assisted planning, FastModel / SmartModel, Scrutineer, multi-source,
multi-component, EvidenceLedger, fetch/read, provider acquisition, evidence
triage, and source gateway / answer gateway / readiness.

Generic dogfood, planning, and acquisition work must also inventory the current
generic single-relation dogfood path, model-assisted single-relation planning,
strict accounted FastModel route, OpenAI Responses-backed route, product-owned
provider acquisition, answer-bearing candidate/window selection, source/
readiness gateway, and D-prime authority integration blocker. Prefer `REUSE` /
`ADAPT` / `UPGRADE`; do not rebuild source-obligation or citation-readiness
machinery already owned downstream.

## Current product and architecture state

| Concern | Canonical owner |
| --- | --- |
| Current installed state and next product checkpoint | [../architecture/SCRYRAVEN_CURRENT_STATE.md](../architecture/SCRYRAVEN_CURRENT_STATE.md) |
| Current-path, passive, fixture, harness, dry-run, legacy, and closed classifications | [../architecture/AG_CURRENT_PATH_QUARANTINE_01.md](../architecture/AG_CURRENT_PATH_QUARANTINE_01.md) |
| Multi-component synthesis runtime architecture | [../architecture/MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md](../architecture/MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md) |
| Cross-component Analyst Workbench | [../architecture/CROSS_COMPONENT_ANALYST_WORKBENCH.md](../architecture/CROSS_COMPONENT_ANALYST_WORKBENCH.md) |
| Integrated semantic loop | [../architecture/RUN_CONTRACT_SEMANTIC_LOOP.md](../architecture/RUN_CONTRACT_SEMANTIC_LOOP.md) |
| D-prime authority | [../architecture/DPRIME_ARCHITECTURE.md](../architecture/DPRIME_ARCHITECTURE.md) |
| Analyst Workbench | [../architecture/ANALYST_WORKBENCH_FULL_SLICE.md](../architecture/ANALYST_WORKBENCH_FULL_SLICE.md) |
| FAP / Author boundary | [../architecture/FAP_AUTHOR_BOUNDARY.md](../architecture/FAP_AUTHOR_BOUNDARY.md) |

Multi-component Phases 1 through 4 are installed: bounded ordinary
component/synthesis consumption, one dynamic AnswerContract recovery, selective
affected-only recomputation, and RunKernel-owned serial scheduling with exact
work/budget leases through ordinary Sufficiency, FinalAnswerPacket, Author or
the safe blocked terminal, RunOutcome, and CLI output. The recommended next
multi-component BUILD is Phase 5 bounded physical dispatch parallelism through
the installed scheduler. Runtime parallelism remains deferred until that phase;
no permanent Fast/Balanced/Deep semantic-call budgets have been selected.

Older PR-number timelines, completed-phase next-step labels, and the former
post-#352 through #355 limited-live-validation sequence are historical context,
not current routing. Consult the named architecture or historical phase record
when that history is relevant.

## Authority and orchestration

| Task | Canonical owner |
| --- | --- |
| RunAuthority / RunKernel migration | [RUNAUTHORITY_IMPLEMENTATION_GUIDE.md](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md) |
| Orchestrator strangulation and surface vocabulary | [../architecture/AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md](../architecture/AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md) |
| Current authority-vocabulary audit | [../architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md](../architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md) |
| Current source-class recovery dispatch | [../architecture/AG95Q_PROVIDER_REVIEW_ALLOCATION_BURNDOWN.md](../architecture/AG95Q_PROVIDER_REVIEW_ALLOCATION_BURNDOWN.md) |
| Legacy Controller handoff, only when explicitly selected | [CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md](CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md) |

`core/pipeline_orchestrator.py` remains a coordination shell with authority debt.
An unchanged line count is a scope-control fact, not architecture success. It may
be a closed surface in an ordinary phase or a licensed target surface / strangler
target in a dedicated migration.

## Search, evidence, and answer-path routing

| Concern | Read first |
| --- | --- |
| Search planning, Scout, handoff, and recovery | [../architecture/RUN_CONTRACT_SEMANTIC_LOOP.md](../architecture/RUN_CONTRACT_SEMANTIC_LOOP.md) |
| Provider acquisition classification | [../operator/GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md](../operator/GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md) |
| Broker reactivation for separately licensed trusted-local use | [../operator/BROKER_REACTIVATION_RUNBOOK.md](../operator/BROKER_REACTIVATION_RUNBOOK.md) |
| Evidence custody and semantic admission | [../architecture/AG_CURRENT_PATH_QUARANTINE_01.md](../architecture/AG_CURRENT_PATH_QUARANTINE_01.md) |
| Scrutineer | [../architecture/AG_SCRUTINEER_REVIEW_01.md](../architecture/AG_SCRUTINEER_REVIEW_01.md) |
| Specialist calculation | [../architecture/AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md](../architecture/AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md) |
| SufficiencyReadiness | [../architecture/AG_SUFFICIENCY_PARTIAL_ANSWER_READINESS_01.md](../architecture/AG_SUFFICIENCY_PARTIAL_ANSWER_READINESS_01.md) |
| Hardened FinalAnswerPacket | [../architecture/AG_FINAL_ANSWER_PACKET_HARDENING_01.md](../architecture/AG_FINAL_ANSWER_PACKET_HARDENING_01.md) |
| Author prose finalization | [../architecture/AUTHOR_PROSE_ONLY_FINALIZATION_01.md](../architecture/AUTHOR_PROSE_ONLY_FINALIZATION_01.md) |

Provider-facing work must declare either `product provider/runtime integration`
or `testing/operator broker-doorman work`. Broker output is sanitized provider
record material only: it is not source custody, evidence, citation eligible,
source-obligation satisfaction, or answer material.

## Live validation

Live provider, model, search, fetch/read, retrieval, and product validation are
disabled unless the phase completes the live-validation addendum with an exact
query class, call cap, budget, redaction boundary, artifact path, decision, and
stop condition. Live-search-only proof is not live product proof. Use the
playbook for output-quality packet rules.

## Repository and tooling references

- Project commands: root `README.md`, `.github/workflows/ci.yml`,
  `scripts/check.ps1`, `scripts/test.ps1`, `scripts/lint.ps1`, `pytest.ini`,
  `ruff.toml`, and `.pre-commit-config.yaml`.
- Cursor-specific command hygiene: `docs/cursor/CURSOR_COMPOSER_WORKFLOW.md`.
- Current Codex profile adapter: `AGENTIC_CODING_OPERATING_PROFILE.md`.
- Historical architecture records: read only when a current owner routes there
  or the phase explicitly targets that history.

## Conflict routing

Direct instructions and the current phase win over older repository prose.
Current canonical architecture wins over historical status language. The
RunAuthority guide wins for current authority-collapse work; the Controller
playbook applies only to explicitly selected legacy maintenance. Stop if a real
conflict requires a product choice, architecture fork, closed-surface change,
live/private access, or destructive Git.
