# ScryRaven Repository Working-Agent Contract

Status: canonical vendor-neutral standing guidance for repository-working coding agents

This file governs Codex and other coding agents, including tools such as Cursor where they honor repository instructions.

Do not create a separate duplicate operating constitution for each coding tool. Tool-specific configuration should remain minimal and point toward this contract where practical.

## 1. Start from current truth

Before substantive work, read:

```text
PRODUCT.md
CURRENT.md
```

`PRODUCT.md` owns approved product intent.

`CURRENT.md` owns mutable factual project state.

Inspect current code, tests, Git state, and relevant evidence as needed.

Historical architecture and prior implementation are not requirements merely because they exist.

## 2. Work from a human-approved outcome

Substantial work must have one coherent approved outcome or consequential engineering question.

Prefer:

```text
one unresolved outcome
-> implementation
-> verification
-> ordinary PRODUCT observation when applicable
-> in-scope repair
-> one final review bundle
```

over:

```text
one seam
-> one artifact
-> one PR
-> another prerequisite phase
```

A coherent work item may contain multiple local commits, tests, diagnoses, and repairs.

Do not stop for ordinary debugging while the next correction is in scope and directly serves the approved outcome.

## 3. Implementation autonomy

Within an existing approved responsibility, choose ordinary implementation details autonomously.

You may:

- inspect relevant repository state;
- refactor locally;
- add or remove private helpers;
- modify implementation-specific structures;
- write focused tests;
- delete obsolete implementation-specific tests;
- create local checkpoint commits;
- perform authorized ordinary PRODUCT observations;
- make bounded in-scope repairs;
- update `CURRENT.md` with factual state.

Do not ask the human to decide routine engineering details.

## 4. Architecture STOP boundary

STOP before introducing a new critical-path:

- responsibility;
- independent decision-maker;
- mandatory restriction;
- persistent lifecycle;
- authority boundary;
- alternate product path.

Also STOP when resolution would:

- materially change the promised outcome;
- violate an explicit exclusion;
- require a consequential product trade-off;
- require unlicensed private-data or credential access;
- require destructive or otherwise unauthorized Git behavior;
- exhaust the reasonable authorized execution envelope without reaching a decision.

"Cleaner," "more extensible," "more correct architecture," or possible future usefulness is not sufficient authority.

Explain the blocking fact and the simplest alternatives.

## 5. Development boundaries are not product states

Do not turn workflow conditions such as:

```text
not licensed in this work item
future work
not implemented yet
testing permission
review required
```

into permanent product:

- runtime gates;
- state fields;
- user-facing blockers;
- schemas;
- authority objects;
- tested contracts.

A work item may simply stop with functionality not yet implemented.

Product restrictions require product justification and authority.

## 6. Tests protect surviving promises

Tests protect approved product and safety behavior.

They do not grant permanence to implementation shape.

When an authorized simplification or deletion breaks a test, ask:

```text
What surviving approved promise does this test protect?
```

If no surviving promise exists, update or delete the test with the implementation.

Do not create process tests whose main purpose is preserving exact governance wording.

Use focused tests where they materially reduce implementation risk.

## 7. Explicit REMOVE

`REMOVE` creates a removal obligation.

Remove applicable:

- runtime code;
- callers;
- compatibility machinery existing solely for the removed behavior;
- obsolete tests;
- obsolete configuration;
- current documentation.

Do not substitute:

- deprecation;
- bypass;
- feature flags;
- dormant compatibility;
- "keep just in case."

If any intended removal remains, the final bundle must say:

```text
REMOVAL INCOMPLETE
```

and identify exactly what remains and why.

## 8. Proof versus PRODUCT evidence

Harnesses, mocks, fixtures, and offline proofs may diagnose and accelerate development.

They cannot complete a PRODUCT obligation that claims behavior through the ordinary product.

A product-path test must not secretly perform the production owner's missing work.

For product-facing work, final completion evidence normally exercises:

```text
ordinary entrypoint
-> actual production path
-> real downstream consumer
-> claimed product result
```

at the level appropriate to the approved outcome.

Offline proof remains appropriate for deterministic mechanics, regressions, and fast iteration.

## 9. Live PRODUCT execution

A coherent critical-path work item includes enough pre-authorized ordinary PRODUCT execution to investigate, repair, and decide the promised outcome without repeatedly returning to the human for permission.

The work-item brief controls the actual finite runway.

When an explicitly live-authorized work item does not state another finite runway, **up to five ordinary PRODUCT runs may be used as an optional operational starting default**.

Five runs is:

- not constitutional law;
- not an acceptance threshold;
- not a target to consume;
- not automatically renewed by renaming or continuing the work item;
- not an automatic ceiling when the work-item brief explicitly authorizes a different finite runway.

Use fewer when sufficient.

Do not invent:

- per-provider accounting bureaucracy;
- token-budget systems;
- dollar-cost accounting for ordinary development queries;
- artificial model/search/read caps that prevent the authorized product test itself.

After a deterministic failure, normally make a reasoned correction and relevant offline checks before another PRODUCT run.

Same-code repetition is appropriate only for an authorized variability check or plausible transient external failure.

## 10. Credential and privacy boundary

For agent-operated commands requiring repository credentials or private environment values, use the existing repository credential-broker / doorman mechanism.

The broker's job is secret custody and process plumbing.

It must not become product architecture or decide:

- product semantics;
- model/provider policy;
- search policy;
- retries;
- evidence authority;
- answer policy.

The controlling agent must not read or expose:

- `.env` contents;
- API keys or credentials;
- unapproved private data.

Use approved sanitized outputs for review.

Do not invent a new credential system during ordinary feature work.

## 11. Git and publication

Default local repository:

```text
C:\Users\aidan\ScryRaven
```

Default workflow is one ordinary checkout and one work-item branch.

Worktrees are opt-in exceptions.

Preserve unrelated user work.

Do not:

- merge;
- rebase;
- force-push;
- destructively reset;
- destructively clean;
- alter `main`;
- delete branches;

without explicit authority for that operation.

Local checkpoint commits are allowed when the work-item brief permits implementation.

Push and PR creation require publication authority from the work item or human.

A PR is a review surface, not merge authority.

Do not create a new PR merely because an internal milestone completed.

## 12. `CURRENT.md` delivery obligation

A PR that materially changes any fact owned by `CURRENT.md` must update `CURRENT.md` in the same PR.

This includes material changes to:

- product behavior;
- active product path;
- implemented versus demonstrated capability;
- representative success/failure frontier;
- active work state that must survive handoff;
- an in-force architectural decision.

Do not churn `CURRENT.md` for changes that alter none of its facts.

During branch work, repository-working agents may record implementation and execution facts in `CURRENT.md`.

Before review, make the branch version describe the state that would be true after merge.

Do not invent a future merge SHA.

ChatGPT checks `CURRENT.md` claims against available evidence during review.

The human retains product-intent and consequential-decision authority.

Replace stale facts; do not append chronology.

Git and PR history preserve chronology.

Writing a claim into `CURRENT.md` does not authorize that claim.

## 13. Final bundle

Lead with whether the requested outcome actually happened.

Use:

```text
OUTCOME:
Met / not met / inconclusive.

EVIDENCE:
Before -> after.
Tested revision.
Ordinary PRODUCT evidence where required.
Relevant focused checks.
Material final-code changes not covered by that evidence.

SCOPE AND REMOVAL:
Responsibilities or restrictions added/deleted and their authorization.
Explicit removal: complete or REMOVAL INCOMPLETE.

CURRENT TRUTH AND LIMITS:
Whether CURRENT.md was updated.
Remaining failures, uncertainty, and unproved claims.

HANDOFF:
Branch/head/PR state.
Specific review or human decision required.
```

Do not use test count, code volume, or architectural sophistication as the headline.

Do not recommend an automatic next phase.

## 14. Post-merge local aftercare

When the human has approved the merge and aftercare is explicitly authorized, the local coding agent may:

- verify that the reviewed change was merged;
- preserve unrelated and uncommitted work;
- return the ordinary checkout to the approved updated baseline using safe Git operations;
- remove the exact completed local branch only if branch deletion was explicitly authorized;
- report final repository status.

STOP if the checkout is dirty in an unexplained way, has unrelated divergence, or cannot be reconciled safely.

Do not use aftercare to:

- reset away work;
- force anything;
- rebase without authority;
- delete unrelated branches;
- clean unrelated files;
- start the next work item.
