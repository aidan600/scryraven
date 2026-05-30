# ScryRaven Current State

Status: Active repo-local handoff note for near-term Codex architecture phases.
Classification: docs-only; not an authorization for runtime behavior changes.

## Public Identity

The public project name is **ScryRaven**. The GitHub repository is
`aidan600/scryraven`, and the preferred local path is `C:\Users\aidan\ScryRaven`.

Earlier private or working names included ProPlex, FauxPlex, and FauxPlexity.
Historical docs may continue to use those names. The public CLI module is
`python -m scryraven`; `proplex`, `python -m proplex`, `PROPLEX_*`,
`proplex.db`, and `proplex_*` remain compatibility names unless a later hard
rename phase explicitly changes them.

## Recent Phase State

SCRY-00 is merged on `main`. It added manual CI `workflow_dispatch`, updated
first-contact labels, refreshed active Codex docs/templates for the public
ScryRaven identity, preserved `proplex` compatibility names, and made no
runtime behavior changes.

AG-70C split the current official/current validation state:

- SSA 2026 wage-base lifecycle succeeded. No immediate SSA repair is indicated.
- IRS 2026 business mileage-rate remains at accepted-readable official/current
  authority visibility / candidate fit. The answer correctly avoided
  overclaiming when final official/current IRS authority evidence was not
  visible.


## AG-76C-BD-R2 Durable Decision Surface

As of 2026-05-30, the current AG-76C durable decision surface is
`AG-76C-BD-R2 — Post-RT/OP/PE Burn-Down Refresh`. The completed post-burn-down
phases are `AG-76C-RT`, `AG-76C-RT-C`, `AG-76C-OP`, and `AG-76C-PE`. The repo no
longer selects those completed phases as the next extraction target.

Exactly one next concrete phase is selected: `AG-76C-KB-C — KB Review
Persistence Context Construction Extraction / Reduction`. Its scope is a
parity-preserving extraction or reduction of the inline
`KbReviewPersistenceContext(...)` construction at the tail of
`core/pipeline_orchestrator.py`. LLM workflow caching is recorded only as future
design work (`AG-76C-LC`) and is not implemented or licensed by BD-R2.

## Near-Term Roadmap

1. SCRY-01: keep repo-tracked current-state docs compact and aligned after the
   ScryRaven migration.
2. AG-71A: run a diagnostic IRS official/current acquisition and query strategy
   review.
3. AG-71B / AG-71C: only open conditional follow-up repair phases if AG-71A
   identifies a separately scoped repair surface.
4. SCRY-02: introduce public CLI/env aliases while preserving `proplex`
   compatibility surfaces.

AG-71A is diagnostic. It should classify where the IRS official/current
authority acquisition problem lives and should not repair behavior unless a
separate phase explicitly scopes the repair.

## Closed Surfaces for AG-71A

Unless separately licensed by the phase brief, AG-71A must not change or open:

- provider swaps or new provider integration;
- provider depth/search-depth changes;
- broad prompt rewrites;
- citation or final-answer behavior;
- Author posture repair;
- direct IRS hardcoding;
- broad `pipeline_orchestrator.py` domain logic;
- live calls;
- provider routing or provider selection;
- retrieval, ranking, or filtering behavior;
- controller lifecycle behavior.

Do not open broad citation survival, Author posture repair, provider swap, or
new provider integration merely because IRS lacked a final official/current
citation in AG-70C.
