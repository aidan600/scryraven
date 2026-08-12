# ScryRaven Active Technical-Debt Register

Status: current
Authority: canonical:active-technical-debt-register
Default-read: no
Applies-to: confirmed current defects and maintenance liabilities deferred outside their discovery or review phase
Does-not-authorize: implementation, priority, roadmap sequencing, live calls, provider changes, or scope expansion
Update-trigger: confirmed new debt, materially changed evidence or disposition, or an in-scope resolving change
ID-policy: monotonic TD identifiers; never reuse a retired identifier
Next-ID: TD-0004

## Purpose

This document is the canonical active-only inventory of confirmed technical
debt. It is not the product roadmap, a feature backlog, or an exhaustive
historical audit, and it does not authorize repairing an item.

[Current Roadmap](roadmap/CURRENT_ROADMAP.md) remains the sole owner of priority
and phase order. GitHub Issues are optional execution and discussion surfaces;
when used, they must link back to the register item rather than become a
competing canonical inventory.

## Admission Rule

An item may be added only when all of the following are true:

1. Concrete current evidence exists.
2. The problem affects the current repository, supported workflow, product
   path, validation integrity, security/privacy posture, cost, reliability, or
   maintainability.
3. The issue is outside the discovering phase's licensed scope or cannot safely
   be resolved there.
4. The consequence and a bounded future repair question can be named.
5. The item is not already represented by an existing active TD identifier.

Do not admit feature ideas, unimplemented roadmap capabilities, optional
improvements, vague suspicions, aesthetic preferences, historical code with no
current consumer, speculative refactors, or every TODO or compatibility marker
in the repository.

## Lifecycle Rule

- IDs are monotonic and never reused.
- New confirmed debt is added in the phase that discovers it when the register
  is licensed.
- Discovery does not authorize repair.
- A PR that fully resolves an item removes that active entry in the same diff.
- The resolving PR body and final bundle must name the removed TD identifier.
- When only part of an item is resolved, update its evidence, consequence, or
  repair boundary rather than deleting it.
- Git history and the resolving PR preserve closure history; do not retain a
  permanent crossed-out archive in this active register.

## Entry Schema

```text
## TD-0000 — Short title

Status: OPEN
Category:
Discovered-in:
Affected-surfaces:

Evidence:
- ...

Consequence:
- ...

Why-deferred:
- ...

Repair-boundary:
- ...

Repair-trigger:
- ...

Tracking:
- Issue: none
- Repair phase: unscheduled
```

Do not add severity, estimates, assigned owners, dates, or priority scores
unless a repository-wide owner for those fields is established separately.

## TD-0001 — Provider-routing fixture availability drift

Status: OPEN
Category: validation-integrity
Discovered-in: PR #509 / SEARCHOS-OPERATING-MODEL-AND-ROADMAP-REALIGNMENT-01
Affected-surfaces:
- `tests/helpers/offline_ordinary_pipeline.py`
- `tests/test_provider_capability_routing_foundation_01.py`

Evidence:
- The shared offline ordinary-pipeline harness supplies
  `provider_availability={"tavily": True}`.
- The routing suite separately configures Linkup-only, Tavily-only,
  all-provider, Exa academic, and unavailable-provider scenarios.
- At baseline `91d04571f8ad21bc221b8ce0fe301e9ce10b83ab` and PR #509 head
  `7918540eee12019320749eaf306059710f887ef2`, the suite produced the
  identical result: 9 failed and 7 passed, with the same nine failing node IDs
  and exception classes.

Consequence:
- The routing suite cannot truthfully exercise its intended provider-
  availability matrix.
- Unrelated phases encounter baseline-red noise.
- Real routing regressions may be harder to distinguish from fixture drift.

Why-deferred:
- Runtime and test-fixture semantics were outside the docs-only PR #509 scope.

Repair-boundary:
- Determine whether the shared harness availability, individual test setup, or
  current availability-composition contract owns the incorrect assumption.
- Do not change production routing merely to satisfy the fixture.

Repair-trigger:
- Before the next phase that changes provider routing, provider availability,
  provider profiles, or escalation policy, or before this suite is again used
  as a required green merge gate.

Tracking:
- Issue: none
- Repair phase: unscheduled

## TD-0002 — Analyst Workbench injected-runner availability drift

Status: OPEN
Category: validation-integrity
Discovered-in: PR #509 / SEARCHOS-OPERATING-MODEL-AND-ROADMAP-REALIGNMENT-01
Affected-surfaces:
- `tests/test_current_source_record_analyst_workbench_01.py`
- `proplex/mvp_single_relation_live_dogfood_run.py`

Evidence:
- Analyst Workbench tests inject a provider proxy runner but supply an
  environment containing no configured provider credential facts.
- The current product runner derives provider availability only from configured
  provider credential/configuration keys.
- The test path therefore blocks during provider routing before reaching the
  intended injected proxy and Workbench assertions.
- At baseline `91d04571f8ad21bc221b8ce0fe301e9ce10b83ab` and PR #509 head
  `7918540eee12019320749eaf306059710f887ef2`, the suite produced the
  identical result: 23 failed and 4 passed, with the same 23 failing node IDs
  and exception classes.

Consequence:
- The suite no longer truthfully reaches the product slice it claims to guard.
- Workbench and D-prime regressions may be obscured by an earlier routing block.
- Unrelated phases encounter baseline-red validation noise.

Why-deferred:
- Runtime and test-fixture semantics were outside the docs-only PR #509 scope.

Repair-boundary:
- Determine whether the test environment, injected-runner test contract, or
  current product-route availability requirement owns the incorrect
  assumption.
- Do not bypass production provider routing merely to preserve a stale test
  seam.

Repair-trigger:
- Before the next phase that changes the current-source single-relation product
  runner, Analyst Workbench product consumption, provider availability, or the
  associated required validation bucket.

Tracking:
- Issue: none
- Repair phase: unscheduled

## TD-0003 - Semantic skip-reason structural-guard classification drift

Status: OPEN
Category: validation-integrity
Discovered-in: SEARCHPLANNER-SPARSE-UNCERTAINTY-AWARE-PLANNING-01
Affected-surfaces:
- `tests/test_semantic_lane_structural_guards.py`
- `core/query_production_runtime.py`
- `tests/buckets/semantic_lane.txt`

Evidence:
- The semantic-lane structural guard treats the literal
  `search_work_plan_missing` as exclusive to the semantic producer core, except
  for two enumerated nonproducer files.
- `core/query_production_runtime.py` independently uses that literal as the
  value of `QueryStrategyConvergenceFailureCode.SEARCH_WORK_PLAN_MISSING`.
- At starting SHA `f3c5cd37a144009f2dc80325aa7d90c75d8e211b` and candidate
  checkpoint `ad995968f6c98f68afb7f31cc2dcb82ca5e0ed45`, the exact structural
  node produced the same result: 1 failed, with the unchanged QueryProduction
  failure-code declaration as the only reported conflict.
- The complete candidate semantic lane was otherwise 158 passed and 4 skipped.

Consequence:
- The durable `semantic_lane` cannot currently produce a green result on its
  own starting baseline.
- Unrelated semantic phases encounter baseline-red validation noise.
- The guard does not distinguish a producer `skipped_reason` from an
  independently owned QueryStrategy safe failure code with the same value.

Why-deferred:
- QueryStrategy diagnostic identity and semantic structural-guard ownership are
  outside the sparse SearchPlanner/AnswerContract Phase-1 outcome.
- Renaming the runtime code or weakening the guard without an owner decision
  could change diagnostic compatibility or conceal a real authority leak.

Repair-boundary:
- Decide whether QueryProduction lawfully shares the literal, should use a
  distinct safe failure code, or should be an explicit structural-guard
  exception.
- Preserve runtime behavior and producer skip-reason ownership; do not change
  QueryProduction semantics merely to make the string scan pass.

Repair-trigger:
- Before the next phase that changes QueryProduction diagnostic identity,
  semantic producer skip reasons, the semantic structural guard, or again
  requires a green `semantic_lane` merge gate.

Tracking:
- Issue: none
- Repair phase: unscheduled
