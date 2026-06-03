# Controller Authority Implementation Playbook

Status: AG-80A repo-tracked implementation guidance
Phase type: documentation-only playbook; no runtime behavior change; no live validation

## Purpose

This playbook is the durable implementation guide for ScryRaven phases after the
Controller-authority closure line documented by AG-79D. It explains how future
phases should add, wire, test, and classify Controller-owned handoffs without
accidentally moving protected legacy behavior, prompts, provider/search behavior,
retrieval behavior, citation behavior, or Author prose.

Use this file when a phase proposes to convert an orchestrator-local decision
surface into a Controller-owned handoff, or when a phase needs to decide whether
a surface is Controller-owned, protected legacy behavior, trace/projection-only,
parked cleanup, or live-gated validation work.

## Controller authority model

The closed authority model is deliberately simple:

1. **Controller decides.** The Controller owns final-answer-governing policy and
   handoff decisions that have been explicitly transferred to it. A Controller
   contract may declare stable state, action posture, no-change posture,
   authorization posture, trace identity, and the specific executor/runtime
   inputs it is allowed to govern.
2. **Orchestrator executes.** `core/pipeline_orchestrator.py` may execute a
   Controller decision by calling a tiny adapter, passing a lifecycle handoff to
   an existing executor, or attaching a trace fragment. It must not recreate the
   same decision locally in new domain-specific branches.
3. **Trace, projection, and export layers observe.** Trace fragments,
   diagnostics projections, export packaging, and review artifacts may expose
   what the Controller decided or what protected legacy runtime already did. They
   must not call providers/search, mutate prompts, rerank/filter retrieval,
   select citations, alter final evidence, or change Author instructions.

The implementation rule of thumb is: **authority flows from Controller to
executor; facts flow from runtime to trace/projection/export.** If a proposed
change reverses that flow, the phase needs a narrower scope or a new explicit
license.

## Standard phase pattern

Controller-authority work should normally progress through three distinct phase
classes.

### 1. Passive contract

A passive contract phase defines a stable representation of a handoff without
changing runtime behavior. It should:

- add a small Controller-owned contract module or equivalent schema;
- serialize to JSON-safe controller state;
- reserve a stable trace key;
- record no-change and skipped/disabled posture explicitly;
- add fixture and static tests that prove stable serialization and protected
  boundaries;
- document exactly which runtime behavior remains untouched.

A passive contract must not wire execution into the live path unless the phase
brief explicitly licenses runtime consumption.

### 2. Behavior-preserving runtime wiring

A runtime wiring phase may attach the passive handoff to the existing lifecycle
when it is explicitly licensed and behavior-preserving. It should:

- call one tiny adapter or builder from `core/pipeline_orchestrator.py`;
- feed already-computed runtime facts into the handoff;
- pass Controller-owned state into an existing executor only where the executor
  already performed the same action;
- attach the trace fragment under the reserved key;
- prove unchanged answer/runtime behavior through fixture tests, static guards,
  and targeted runtime handoff tests.

Behavior-preserving means the same prompts, provider/search calls, retrieval
ranking/filtering, citation behavior, Author prose, persistence shape, cache
behavior, and live behavior remain intact.

### 3. Optional behavior activation

A Controller handoff may change behavior only in a later phase whose brief
explicitly licenses activation. The brief must name:

- the Controller decision being activated;
- the old protected legacy behavior being displaced;
- the executor or runtime callsite allowed to consume the decision;
- the fixtures that prove activation and negative-control no-change behavior;
- the live-validation plan if live evidence is required.

Without that explicit license, a Controller-owned handoff remains passive or
behavior-preserving even if its schema appears capable of governing behavior.

## Adding a Controller-owned handoff

Use this checklist for new handoffs.

### Stable schema

- Give the handoff a stable, descriptive name and trace key.
- Prefer compact dataclasses or typed structures with predictable field order.
- Use explicit posture strings instead of implicit booleans where future states
  are likely.
- Include source IDs, decision refs, evidence refs, or handoff refs rather than
  raw prompts, raw provider payloads, private traces, cache contents, or DB rows.
- Keep schema additions append-only where possible; avoid renaming existing keys
  unless the phase is explicitly a migration.

### JSON-safe Controller state

- Serialization must return JSON-safe primitives: dicts, lists, strings,
  numbers, booleans, and nulls.
- Normalize sets, tuples, enums, exceptions, paths, datetimes, and model-specific
  objects before they enter trace state.
- Bound large text fields. Prefer IDs, counts, posture, snippets already visible
  to review, or redacted summaries.
- Make skipped/no-op state as serializable and reviewable as active state.

### Trace fragment

- Reserve one stable top-level trace key for the handoff.
- Trace should explain what decision was available, which lifecycle branch it
  applied to, and whether runtime consumed it.
- Trace fragments are evidence for review; they are not a second runtime policy
  engine.
- Projection/export code may copy or summarize the fragment, but must not use it
  to mutate final-answer behavior.

### No-change flags

Every handoff should expose no-change posture where applicable. Examples:

- skipped because the lifecycle branch did not run;
- disabled because the Controller did not authorize activation;
- no supplemental search requested;
- no remediation admitted;
- no Analyst/Author re-run admitted;
- no citation/source-list override requested;
- legacy runtime posture recorded only for trace.

No-change state is as important as active state because it proves a handoff can
be safely present without causing hidden runtime effects.

### Fixture and static tests

At minimum, add tests for:

- canonical active and skipped/no-change fixture serialization;
- JSON safety and stable trace key shape;
- protected-import guards for providers/search, prompt modules, DB/session/cache,
  or other forbidden dependencies;
- negative-control tests proving no prompt/provider/retrieval/citation/Author
  behavior is changed by merely constructing the handoff.

### Runtime wiring limits

If runtime wiring is licensed, the handoff may be threaded only through the
smallest necessary adapter/callsite. It must not introduce broad orchestration
rewrites, new query planning, new search calls, new ranking/filtering, new prompt
text, new citation selection, or persistence schema changes.

## Touching `core/pipeline_orchestrator.py` safely

`core/pipeline_orchestrator.py` is allowed to execute Controller decisions, but
it is not where new domain authority should be invented. Safe touches are small,
mechanical, and reviewable.

Allowed orchestrator touch patterns:

1. **Tiny adapter call.** Build or normalize a handoff with already-available
   inputs. The adapter should live outside the orchestrator when possible.
2. **Lifecycle handoff.** Thread Controller-owned state through an existing
   lifecycle point without changing whether that lifecycle point runs.
3. **Executor call.** Pass Controller-authorized posture into the executor that
   already owns the effect, without adding a new local branch that makes the same
   decision again.
4. **Trace attachment.** Attach the serialized handoff under its stable trace key
   after the relevant branch completes or is skipped.

Forbidden orchestrator touch patterns:

- new domain decision logic that chooses provider/search/depth/query behavior;
- local replacements for Controller decisions;
- prompt rewrites or new Author side-channel directives;
- broad rewrites of retrieval, final evidence selection, citation assembly, or
  persistence/session code;
- changes whose only proof is live behavior rather than fixture/static tests.

A useful review question is: **could this diff be summarized as an adapter call,
lifecycle handoff, executor call, or trace attachment?** If not, stop and split
the phase.

## Protected surfaces

The following surfaces remain closed unless a phase brief explicitly licenses a
change and names the expected behavior delta:

- prompts and prompt semantics;
- provider, model, search, depth, and query behavior;
- retrieval ranking, filtering, deduplication, and final evidence selection;
- citation behavior, citation formatting, and source-list identity;
- Author prose, Author notes, and final-answer wording behavior;
- Analyst, Economist, Scrutineer, and follow-up handoffs except where the phase
  owns the exact handoff being changed;
- DB, session, `RunOutcome`, persistence schema, and report packaging shape;
- cache behavior and cache keys;
- live validation, provider calls, model calls, and search calls;
- raw prompts, raw provider payloads, secrets, private logs, DB rows, caches,
  and full raw traces.

Protected does not mean unimportant. It means the surface is either deliberately
legacy-compatible, requires its own phase, or requires live validation and cannot
be changed incidentally.

## Current classifications after AG-79D

AG-79D closed the Controller-authority transfer audit line at classification
depth. Use these classifications until a later phase explicitly refreshes them.

### Controller-owned or Controller-controlled surfaces

The following are Controller-owned or controlled by already-established
Controller gates/handoffs:

- retrieval stop/continue posture;
- weak-corpus recovery posture;
- source-class and authoritative-source recovery posture;
- conflict-resolution retrieval posture;
- scout, expander, evaluator, and ordinary continuation gates;
- final evidence identity handoff;
- citation/source-list identity handoff;
- Analyst/Author handoff packaging;
- weak/failure-card answer posture;
- conflict labels and indirect-inference labels;
- Scrutineer/remediation runtime handoff trace identity after the SCR runtime
  wiring phase;
- synthesis-evaluator supplemental-search runtime handoff trace identity after
  the SES runtime wiring phase.

### Protected legacy behavior

The following remain protected legacy behavior rather than hidden authority that
should be changed opportunistically:

- Brave recon rewrite;
- low entity-utilization disambiguation retry;
- query replacement/entity correction;
- `_finalize_retrieval_queries`;
- recency merge;
- official-bias insertion;
- query ordering;
- provider/search/depth behavior where no Controller-owned handoff already
  supplies it;
- retrieval ranking/filtering;
- final evidence selection;
- citation formatting;
- prompt text;
- Author notes/prose;
- Scrutineer/remediation behavior beyond the approved handoff/trace identity;
- synthesis-evaluator supplemental-search behavior beyond the approved
  handoff/trace identity.

### Trace/projection-only surfaces

The following are observer surfaces unless a future phase explicitly elevates
them:

- trace export and runtime trace fragments;
- diagnostics projections;
- review/report export packaging;
- session metadata summaries;
- handoff identity projections that expose Controller state without consuming it
  for new runtime effects.

### Parked adapter cleanup

AG-76D-AD adapter cleanup is appropriate as later behavior-preserving
maintainability cleanup. It should remain parked unless a phase brief schedules
it or a future repair cannot safely distinguish adapter translation from
Controller-owned action authority.

### Live-gated AG-78G

AG-78G remains live-gated. It must not run as a side effect of implementation,
static testing, docs refresh, or local validation. It requires a dedicated live
validation plan before any provider/model/search calls are made.

## Required test patterns

Future implementation phases should select from these test patterns based on
phase class.

### Contract tests

Use for passive contracts and schema changes:

- active fixture serialization;
- skipped/no-change fixture serialization;
- JSON-safety checks;
- stable trace key checks;
- protected-import checks;
- schema compatibility or append-only checks when existing fixtures exist.

### Runtime handoff tests

Use when behavior-preserving runtime wiring is licensed:

- prove the handoff is attached on active and skipped lifecycle paths;
- prove existing executor behavior is still reached through the same runtime
  branch;
- prove no new provider/search/query/depth behavior is introduced;
- prove final evidence, citations, Author notes/prose, and persistence shape are
  unchanged unless activation is explicitly licensed.

### Static protected-import guards

Guard passive contracts, adapters, trace/projection modules, and tests against
forbidden dependencies. Typical forbidden imports include provider/search
clients, prompt execution surfaces, DB/session objects, cache backends, and live
validation harnesses unless the phase explicitly owns that dependency.

### Static orchestrator-touch guards

When `core/pipeline_orchestrator.py` changes, add or update static guards that
make the allowed touch pattern obvious. Guards should catch broad rewrites,
provider/search call additions, prompt mutation, citation mutation, persistence
shape changes, and new domain decision branches outside the licensed handoff.

### Full-suite / CI expectations

- Run the targeted tests for the new or changed handoff.
- Run the static guards that protect closed surfaces.
- Run the project’s normal offline test suite or the documented CI subset unless
  the phase brief scopes a smaller docs-only change.
- Do not run live provider/model/search validation as a substitute for offline
  contract and guard coverage.

## Live validation rules

Live validation is disabled by default. A phase may run live validation only when
its brief supplies all of the following:

1. **Exact query class.** The class of query or the exact query text to run.
2. **Run cap.** Maximum number of ScryRaven/proplex runs.
3. **Provider/search cap.** Maximum provider, model, and search calls or an
   equivalent bounded command that enforces the cap.
4. **Packet path.** The local ignored output-quality review packet path and, if
   durable history is needed, the committed validation doc path.
5. **Redaction plan.** Explicit exclusions for secrets, raw prompts, raw provider
   payloads, DB rows, caches, full traces, private logs, and unrelated generated
   output.
6. **Stop condition.** The condition that ends validation, including budget
   exhaustion, protected-surface uncertainty, or discovery that the requested
   behavior requires a new phase.

If any item is missing, do not run live validation. Treat the missing item as a
stop condition and keep the phase offline.

## Phase design checklist

Before implementation, write the phase in one of these forms:

- **Passive contract:** schema + JSON-safe state + trace key + no-change posture
  + fixture/static tests + docs.
- **Behavior-preserving wiring:** passive handoff already exists + tiny adapter
  call + lifecycle handoff + executor call if needed + trace attachment + static
  orchestrator/protected-surface guards.
- **Behavior activation:** explicit Controller decision + named legacy behavior
  displaced + runtime consumer + negative controls + live-validation plan if
  required.
- **Trace/projection/export only:** observer-only change + guard proving no
  provider/search/runtime mutation.
- **Adapter cleanup:** behavior-preserving maintainability cleanup + tests proving
  no authority movement.

If the work cannot fit one of these forms, it probably needs a roadmap/design
refresh before code changes.

## Recommended next step

After AG-80A, the recommended next repo-planning step is **Roadmap v4 / Project
Source refresh**. Do not treat that recommendation as approval to change runtime
behavior, prompts, provider/search/retrieval behavior, citations, Author prose,
or live validation.
