# RunAuthority Implementation Guide

Status: Recommended AG-89+ authority-collapse implementation guidance
Suggested repo path: `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md`

## Purpose

Use this guide for AG-89+ phases that collapse duplicate runtime authority into a
single accountable RunAuthority / RunKernel path. It supersedes the legacy
Controller passive-contract ladder for authority-collapse work. The goal is not
to preserve old hidden authority behind nicer wrappers; the goal is to make the
intended runtime consumer consume the new authority and to retire, demote,
bypass, subordinate, or schedule retirement of the old authority path.

For ordinary setup, docs, UI, or non-authority work, start from the
[Codex Guidance Map](CODEX_GUIDANCE_MAP.md) and the
[Architecture Groove Playbook](ARCHITECTURE_GROOVE_PLAYBOOK.md).

## Core doctrine

### Current implemented baseline

As of AG-94C, the implemented runtime authority baseline is:

```text
RunAuthorityContract -> EvidenceLedger -> SearchJudgment -> SufficiencyJudgment
-> FinalAnswerPacket -> AuthorExecutor
```

RunKernel / RunAuthority owns run-level meaning and canonical authority.
Executors perform bounded work. Reducers commit observations into canonical
RunState / EvidenceLedger / FinalAnswerPacket state. Trace, export, report, and
projection surfaces observe canonical state and must not re-decide it.

Legacy Controller/lifecycle surfaces may remain only as passive mirrors,
compatibility executors, bounded adapters, RunAuthority-subordinated lanes, or
explicitly scheduled retirement surfaces. `core/pipeline_orchestrator.py` is a
coordination shell with remaining authority debt and is a target surface for
bounded strangulation phases. In ordinary product behavior phases it may be
closed for scope safety; in orchestrator-strangulation phases, touching it can
be the point. `core/pipeline_orchestrator.py` line delta `0` is a
scope-control fact, not architecture success.

For source-class recovery dispatch after AG-95C/AG-95E, the current runtime
consumer is `SourceClassRecoveryRunner`, and it dispatches only from canonical
`authority_lifecycle.recovery_action`. `ControllerLoopSpine` source-class
dispatch fields, `authorized_spine_action`, official/canonical admission
booleans, lifecycle eligibility booleans, reports, exports, and
`ControllerRecoveryDecision` are diagnostic or compatibility surfaces for this
lane. They must not be restored as source-class runner dispatch authority.

### No orchestrator brain

The orchestrator should coordinate lifecycle flow and call bounded executors. It
must not regain policy ownership by rebuilding decisions from local variables,
shadow summaries, trace mirrors, prompt-only instructions, or compatibility
wrappers.

### One accountable RunAuthority / RunKernel path

Each governing decision must have one accountable owner. For AG-89+ work, the
preferred direction is a RunAuthority / RunKernel path that owns run-state
transitions, action authorization, query planning, evidence custody, and final
answer readiness through canonical state instead of scattered loop-spine logic.

### Bounded executors

Executors may perform bounded work: acquire observations, call a provider when
licensed, format a projection, persist a record, or render an output. They should
not decide policy that belongs to RunAuthority. Executor observations flow back
into canonical state; policy does not flow from trace or projections back into
runtime decisions.

## Canonical state direction

Authority-collapse phases should move toward these canonical owners:

- **RunState** records the current run posture, next authorized action, lifecycle
  status, and stop/continue basis.
- **EvidenceLedger** records evidence candidate custody, source obligations,
  official/current-source posture, and evidence observations.
- **QueryPlan** owns query intent, finalized/current queries, ordinary,
  recon/researcher, recency, continuation, supplemental, remediation, and query
  mutation authority where those producers feed retrieval-loop query identity.
  Source-class recovery action queries currently remain owned by the
  Controller/RunAuthority recovery action envelope unless a future phase
  explicitly routes them through QueryPlan.
- **FinalAnswerPacket** owns final evidence selection, citation eligibility,
  Author-facing posture, answer readiness, caveats, and handoff fields needed to
  write the final answer.

Trace, diagnostics, reports, and exports should be derived from these canonical
records. Trace may expose authority; it must not be the authority.

## Runtime consumption requirement

A new authority is successful only when the intended runtime consumer consumes it.
The final diff and final bundle must identify:

1. the intended consumer;
2. the exact seam where it reads the new authority;
3. the focused test or static check proving that read;
4. the user-visible behavior preserved or intentionally changed by license.

A dataclass, trace key, stored JSON field, prompt-visible note, or test fixture is
not enough unless the phase is explicitly passive, docs-only, or
instrumentation-only.

## Old authority retirement requirement

Every authority-collapse phase must account for the old owner. The old path must
be one of:

- **deleted** — removed because all consumers read canonical authority;
- **demoted** — retained only as trace/projection/export/compatibility output
  derived from canonical state;
- **bypassed** — no longer on the governing runtime path;
- **subordinated** — converted to a bounded executor that obeys canonical state;
- **scheduled for retirement** — retained with a named consumer, reason, and
  concrete deletion trigger.

`future review` is not a sufficient permanent status. If the old path remains,
name why it remains and what evidence will permit removal.

## Behavior-preserving does not mean hidden-authority-preserving

Behavior-preserving means preserving user-visible behavior where possible: answer
content, citations, provider/search budgets, prompt semantics, persistence shape,
cache compatibility, and live behavior unless the phase explicitly licenses a
change.

It does **not** mean preserving old hidden decision authority. An
authority-collapse phase may preserve visible behavior while deleting, demoting,
bypassing, subordinating, or scheduling retirement for the old hidden owner.

## Failure modes

Trace-only, storage-only, wrapper-only, prompt-visible-only, or test-only
authority is failure unless the phase is explicitly passive, docs-only, or
instrumentation-only.

Common failure patterns:

- adding a new authority object but leaving the orchestrator-local branch in
  charge;
- mirroring decisions into trace while executors still read the old variables;
- preserving old aggregate summaries as the actual policy source;
- wrapping old behavior in a helper without changing ownership;
- adding prompts that describe policy while runtime code still decides elsewhere;
- proving only serialization while no runtime consumer reads the new state.

## Surface Boundary Vocabulary

Use these terms for current AG-89+ prompts and reviews:

- **Licensed surface:** a file, module, behavior, or document the current phase
  explicitly allows Codex to inspect or change.
- **Closed surface:** a surface kept out of scope for this phase.
- **Target surface:** a surface intentionally being reduced, moved, simplified,
  or retired over time.
- **Historical surface:** retained as project history, not current doctrine.
- **Safety-sensitive surface:** high-custody behavior such as provider/model
  routing, search depth, prompt semantics, citation behavior, persistence shape,
  or live validation.

The legacy word "protected" should not mean sacred. If an older document says a
surface was protected, read that as a phase boundary from that historical moment
unless current guidance or the phase brief relicenses it. Without an explicit
license, preserve user-visible behavior and confine changes to ownership
collapse, projection cleanup, tests, or docs.

## Implementation checklist

1. Name the governing decision being collapsed.
2. Identify the old owner and every known consumer.
3. Identify the new RunAuthority / RunKernel or canonical-state owner.
4. Identify the runtime consumer that must read the new owner.
5. Implement the smallest ownership change that makes the consumer read it.
6. Delete, demote, bypass, subordinate, or schedule retirement for the old path.
7. Derive trace/projection/export from canonical state.
8. Add focused positive and negative-control tests.
9. Run focused offline checks; do not run live calls unless explicitly scoped.
10. Self-review for wrapper-only, trace-only, prompt-only, and duplicate-owner
    failures.

## Authority-collapse final bundle fields

Every AG-89+ authority-collapse final bundle must include:

- old owner;
- new owner;
- runtime consumer;
- consumption proof;
- old-path retirement status (`deleted`, `demoted`, `bypassed`, `subordinated`,
  or `scheduled for retirement`);
- remaining duplicate-owner risk;
- licensed target surfaces opened, closed surfaces kept closed, and any
  safety-sensitive surfaces affected;
- live validation status;
- user-visible behavior changes, if any.
