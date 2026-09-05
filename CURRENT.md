# ScryRaven Current Truth

Status: transitional current state before Part B  
Repository: `aidan600/scryraven`  
Preferred local checkout: `C:\Users\aidan\ScryRaven`

## Current repository state

Part A installation baseline / final v1 implementation baseline:

```text
bdefe506ffb58df491e31156771f4e0712e3dd2b
```

This is the final v1 implementation baseline from which the Development Operating System transition is being installed.

The ScryRaven v1 application implementation remains physically present in the active repository tree.

Part A changes repository governance and current-truth surfaces only. It does not redesign, replace, or remove the application.

The authoritative current repository revision is the Git revision containing this file.

Do not maintain a hard-coded "current main SHA" here; Git owns that fact.

No repository clean-room reset has been authorized.

No v2 implementation has begun.

## Current architectural posture

The v1 implementation lineage has been retired as the presumptive architecture for future ScryRaven development.

This retirement does **not** currently mean deleting the implementation.

The repository remains available for deliberate inspection during Part B.

> **v1 is currently available as evidence for deliberate inspection; it is not ambient architectural authority.**

Historical implementation, tests, architecture documents, closed PRs, Git commits, and repository history may be consulted when a specific question makes them relevant.

Their existence does not create a preservation requirement for the rebuild.

## Recent experiment

The recent thin-corridor / strangler experiment was closed without merge.

It established some offline feasibility but did not establish sufficient repeatable ordinary PRODUCT evidence to justify adopting the experimental architecture.

The experiment therefore does not define the future ScryRaven architecture.

## Current authorization boundary

No active-tree reset, donor selection, ScryRaven v2 architecture, or ScryRaven v2 implementation is currently authorized.

`PRODUCT.md` is intentionally transitional until Part B establishes the initial future product promise.

## Current objective

The current transition sequence is:

1. install the new Development Operating System and remove v1 workflow/architecture material from ambient authority;
2. conduct Part B: a first-principles ScryRaven product/MVP review, with the old implementation available for deliberate inspection;
3. only after Part B, decide what repository reset, active-tree cleanup, donor selection, reuse, or rebuild should occur.

The transition boundary is:

> **Part A removes v1's ambient authority.**

> **Part B deliberately reviews the product and decides the future MVP.**

> **Only afterward may a separately authorized repository reset/rebuild remove or reuse v1 implementation.**

Do not collapse those steps.

## Current uncertainty

The future MVP boundary, walking skeleton, active product path, architecture, and donor set remain intentionally undecided.

Those are Part B decisions.

Git and PR history preserve implementation chronology.

This file preserves current truth.

Replace stale facts rather than accumulating historical layers.
