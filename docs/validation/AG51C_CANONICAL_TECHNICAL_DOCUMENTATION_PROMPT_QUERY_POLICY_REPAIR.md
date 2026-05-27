# AG-51C Canonical Technical Documentation Prompt/Query-Policy Repair

## Phase Purpose

AG-51C repairs the repo-tracked prompt/query-policy surface so canonical
technical documentation questions are not treated as academic-paper retrieval
merely because they are technical, software, database, API, or engineering
adjacent.

The phase does not claim that source-trust is generally fixed. It only repairs
and validates the offline prompt/query-policy contract for canonical technical
documentation.

## Licensed Surface

Opened:

- router prompt wording around `is_academic`;
- researcher query-policy wording for canonical technical documentation;
- narrow prompt-adjacent policy for canonical technical documentation recovery;
- offline tests for fake-router/prompt-policy, recovery-query policy, and
  academic-domain-filter guards.

Still closed:

- live validation by default;
- provider routing, provider selection, provider depth/search-depth, provider
  escalation, and provider integration;
- new providers;
- source-specific documentation adapters, resolvers, or catalogs;
- broad source ranking, filtering, source-fit, or evidence acceptance;
- citation survival/selection;
- Analyst, Economist, Author, Scrutineer, and final-answer behavior;
- raw runtime prompts, raw provider payloads, DB rows, logs, caches, secrets,
  `.env`, and full traces.

## Source-Layer Boundary Handling

Referenced Project Source context was provided inline in the prompt.

Inputs used:

- repo-tracked files in the local checkout;
- inline Project Source rules in the phase prompt;
- verified local git/GitHub state;
- explicitly scoped local output-quality packets under `output/`.

Scoped local packets were available and read:

- `output/ag50f_output_quality_review_packet.md`
- `output/ag52a_output_quality_review_packet.md`
- `output/ag52b_output_quality_review_packet.md`
- `output/ag51a_output_quality_review_packet.md`

No AG-51C local packet was created.

No Project Source files were assumed to exist in the repo unless repo-tracked.
No raw provider payloads, raw runtime prompts, DB rows, private logs, caches,
secrets, `.env` contents, or full traces were inspected.

## Verified Git/GitHub State

Before changing files:

- `git switch main`: already on `main`.
- `git pull --ff-only origin main`: already up to date.
- `git status -sb`: clean `main`.
- `git log --oneline -12`: top commit was
  `40600ff Merge pull request #94 from aidan600/codex/ag51b-source-acquisition-architecture-review`.
- `git rev-parse HEAD`: `40600ffe4b78761dbdab1614efbbc3ffb7ac77b5`.
- `git ls-remote origin refs/heads/main`: matched local HEAD.

Branch:

- `codex/ag51c-canonical-technical-docs-prompt-query-policy-repair`

AG-51B was present on local and remote `main`.

## AG-51B Recommendation Summary

AG-51B recommended exactly one next licensed surface:

**prompt/query-policy repair for the canonical technical documentation versus
academic-paper policy boundary.**

The rationale was repo-visible and concrete:

- router prompt policy could classify engineering/static technical topics as
  academic;
- academic routing prefers Exa when available;
- academic Exa calls can receive `ACADEMIC_DOMAINS`;
- `ACADEMIC_DOMAINS` includes paper/literature domains such as `arxiv.org`,
  not canonical technical docs domains;
- source-class recovery inherits the provider list and Exa domain filter;
- prior live packets showed official/reference documentation recovery queries
  but accepted recovered candidate domains remained `arxiv.org`.

## Rule 0 Failure Analysis

General failure class:

Canonical technical documentation questions can be misclassified or steered as
academic/peer-reviewed retrieval because the topic is technical or
engineering-adjacent. That can cause the source-trust recovery path to find
arXiv/paper sources instead of official/canonical docs.

Blast radius:

- router prompt policy;
- researcher query policy;
- recovery prompt-adjacent policy;
- source-class obligation wording for canonical technical docs.

Rules applied:

- prompt/query-policy was licensed and changed;
- provider routing/depth, new providers, adapters, evidence acceptance,
  citation, Author, and final-answer behavior remained closed;
- PostgreSQL was used as one fixture only;
- sibling canonical-doc cases were included;
- explicit academic/peer-reviewed requests remain academic;
- no live validation was run.

Valid cases protected:

- real academic literature questions about technical topics;
- peer-reviewed medical/scientific/engineering literature requests;
- ordinary conceptual explainers where official docs are not required;
- non-technical official/current source-class recovery;
- downstream citation and Author flows.

## Prompt/Query-Policy Diagnosis

Before AG-51C, `DEFAULT_SYSTEM["router"]` told the router to set
`is_academic` true for engineering and other broad technical/scientific
domains, or where peer-reviewed evidence is more authoritative than news or
general web sources. It did not distinguish:

- academic engineering research, where peer-reviewed papers may be appropriate;
- canonical technical reference questions, where official/current/project docs
  are primary evidence.

The flag is operational. `select_providers` sends academic general queries to
Exa when available, and `pipeline_orchestrator.py` passes `ACADEMIC_DOMAINS` to
Exa when `is_academic` is true. Source-class recovery reused that
`exa_domain_filter`. Thus an admitted `primary_source_documents` recovery slot
for canonical technical documentation could remain constrained to an academic
paper-domain universe.

## Changes Made

Changed `core/prompts.py`:

- router prompt now says to set `is_academic` true for explicit
  peer-reviewed/academic literature/papers/arXiv/empirical requests;
- router prompt now says not to set `is_academic` true solely because a topic
  is technical, software, database, API, engineering-adjacent, or static;
- router prompt now identifies named software/database/language/browser API/
  package/SDK/protocol/project behavior questions as canonical documentation
  cases unless the user explicitly asks for academic literature;
- researcher prompt now prefers official/reference/canonical documentation
  query terms for canonical technical documentation questions and avoids
  paper/arXiv/academic-literature terms unless explicitly requested.

Added `core/canonical_technical_docs_policy.py`:

- pure deterministic helper for canonical technical documentation context;
- pure explicit academic-literature request helper;
- academic-literature domain-filter recognition for the existing academic
  domain-filter set;
- no provider calls, routing, depth, ranking, prompts, persistence, or final
  answer behavior.

Changed `core/source_class_recovery_executor.py`:

- when a controller-approved source-class recovery action is for canonical
  technical documentation (`primary_source_documents` plus official/reference/
  docs technical context), and the inherited Exa domain filter is an academic
  literature domain filter, the executor suppresses that inherited academic
  domain filter for the recovery call;
- provider list, provider role, search depth, result cap, include/exclude
  domains, ranking, evidence acceptance, and final answer behavior are
  unchanged.

This is intentionally a narrow prompt-adjacent policy guard, not broad provider
routing or depth policy.

## Why This Is Inside Prompt/Query-Policy

The repair changes what the repo-tracked prompts instruct and prevents an
academic-paper domain filter from applying to an admitted canonical-doc recovery
slot solely because a technical topic was marked academic.

It does not:

- select a different provider;
- add or remove providers;
- alter search depth;
- add source-specific domains or adapters;
- inspect raw provider payloads;
- rank or accept evidence differently;
- alter citation survival/selection;
- alter Analyst, Economist, Author, Scrutineer, or final-answer behavior.

`core/pipeline_orchestrator.py` was not changed.

## Tests Added Or Changed

Added:

- `tests/test_ag51c_canonical_technical_docs_prompt_query_policy.py`

Coverage:

- router prompt static guard for canonical technical docs versus academic
  literature;
- researcher prompt static guard for official/reference/canonical docs query
  wording;
- canonical technical docs positive cases:
  - PostgreSQL MVCC;
  - SQLite WAL;
  - Python dataclasses;
  - Fetch API credentials / browser API style docs;
- explicit academic negative controls:
  - peer-reviewed PostgreSQL MVCC papers;
  - recent arXiv database concurrency papers;
- recovery query previews remain official/reference documentation oriented;
- admitted canonical technical-doc recovery suppresses inherited academic
  domain filters;
- explicit academic recovery keeps academic domain filters;
- non-technical official/current recovery remains unaffected;
- static protected-surface guards:
  - no source-specific docs domains;
  - no import of routing, retrieval, prompts, search providers, or
    `pipeline_orchestrator.py` in the new helper/executor path;
  - `pipeline_orchestrator.py` unchanged by the AG-51C policy hook.

Existing focused slices also covered:

- AG-50A query acquisition;
- AG-50B execution admission;
- AG-50C visibility export;
- AG-50D execution dispatch;
- AG-50E candidate acquisition;
- AG-51A acquisition strategy;
- AG-52A evidence acceptance/source-fit;
- AG-52B candidate visibility;
- source-class recovery, executor, lifecycle, diagnostics, and trace;
- routing provider matrix compatibility.

## Positive Canonical-Doc Cases

Covered offline:

- PostgreSQL MVCC-style recovery remains canonical technical documentation and
  gets official/reference documentation queries.
- SQLite WAL mode gets the same treatment, proving the repair is not a
  PostgreSQL-only hardcode.
- Python dataclasses and Fetch API credentials are recognized by the helper as
  sibling canonical technical documentation contexts.

## Explicit Academic Negative Controls

Covered offline:

- `peer-reviewed papers about PostgreSQL MVCC performance` is explicit academic
  literature and is not classified as canonical technical documentation.
- `recent arXiv papers about database concurrency` remains explicit academic
  literature.
- An explicit academic recovery query keeps the academic domain filter.

## Academic-Domain-Filter Guard Result

Offline fake-executor harness:

- canonical docs recovery slot:
  - missing source class: `primary_source_documents`;
  - queries: official/reference documentation for PostgreSQL MVCC;
  - inherited Exa filter: `ACADEMIC_DOMAINS`;
  - observed filter passed to fake search: `None`.
- explicit academic recovery slot:
  - query: peer-reviewed database concurrency/MVCC papers;
  - inherited Exa filter: `ACADEMIC_DOMAINS`;
  - observed filter passed to fake search: `ACADEMIC_DOMAINS`.
- non-technical official/current recovery:
  - missing source class: `official_current_rules`;
  - inherited Exa filter: `ACADEMIC_DOMAINS`;
  - observed filter passed to fake search: `ACADEMIC_DOMAINS`.

## Mid-Phase Review Gates

Gate 1 - Reconnaissance:

- Repo was clean and updated at expected AG-51B merge `40600ff`.
- Router prompt, researcher prompt, `is_academic` interpretation, routing, Exa
  domain filtering, recovery query acquisition, source-class recovery executor,
  and source-class obligation wording were mapped.
- `is_academic` is prompted in `core/prompts.py`, parsed/used in
  `core/pipeline_orchestrator.py`, and connected to provider selection and
  `ACADEMIC_DOMAINS`.
- Canonical docs obligations are expressed through source-class expectation,
  official-source obligation visibility, AG-51A query acquisition, and
  `primary_source_documents`.
- Implementation path: prompt wording plus narrow prompt-adjacent domain-filter
  guard.
- Licensed surface: prompt/query-policy.
- Closed surfaces remained closed.
- `pipeline_orchestrator.py` was expected to need no change.

Gate 2 - Pre-implementation decision:

- Bottleneck: technical/canonical docs questions could be treated as academic
  solely due to technical/engineering wording, carrying paper-domain filtering
  into recovery.
- Changes selected: router/researcher prompt wording, pure canonical-docs
  policy helper, and a narrow executor guard for inherited academic domain
  filters on canonical-doc recovery.
- Tests selected: positive canonical docs, sibling canonical docs, explicit
  academic negatives, recovery query previews, academic-domain-filter guard,
  and protected-surface static checks.
- Stop packet would be required for provider routing/depth, new providers,
  adapters, evidence acceptance, citation/Author, raw data, or live validation.

Gate 3 - Post-implementation self-review:

- The change addressed the intended prompt/query-policy seam.
- Patch stayed inside the licensed surface.
- Provider routing/depth remained unchanged.
- Citation/Author/final-answer behavior remained unchanged.
- Canonical docs and explicit academic controls are both covered.
- PostgreSQL is only one fixture among sibling cases.
- Unknown live behavior remains unknown.

Gate 4 - Validation decision:

- No live validation was run.
- Offline prompt/query-policy tests are sufficient because this phase repairs
  the policy contract first.
- Prior live packets already establish the arXiv-only symptom.
- Live runs would muddy context before the policy contract is merged and
  reviewed.

Gate 5 - Final recommendation review:

- Phase result: offline prompt/query-policy repair completed.
- Next failure layer: live product effect remains unvalidated after policy
  repair.
- Next protected surface to open, if desired: one bounded post-policy live
  classification phase using sanitized fields, not provider/depth/adapters by
  default.
- Phase is merge-ready after review.
- Merge was not performed.

## Commands And Results

- `git switch main`: already on `main`.
- `git pull --ff-only origin main`: already up to date.
- `git status -sb`: clean before branching.
- `git log --oneline -12`: confirmed AG-51B merge at top.
- `git rev-parse HEAD`: `40600ffe4b78761dbdab1614efbbc3ffb7ac77b5`.
- `git ls-remote origin refs/heads/main`: matched local HEAD.
- `git switch -c codex/ag51c-canonical-technical-docs-prompt-query-policy-repair`:
  branch created.
- `py -m pytest --basetemp C:\tmp\ag51c-pytest tests\test_ag51c_canonical_technical_docs_prompt_query_policy.py`:
  8 passed.
- Focused recovery/router slice:
  `py -m pytest --basetemp C:\tmp\ag51c-pytest tests\test_ag51c_canonical_technical_docs_prompt_query_policy.py tests\test_official_canonical_recovery_query_acquisition_ag50a.py tests\test_official_canonical_recovery_acquisition_strategy_ag51a.py tests\test_source_class_recovery_executor.py tests\test_source_class_recovery_lifecycle.py tests\test_source_class_recovery.py tests\test_official_canonical_recovery_candidate_visibility_ag52b.py tests\test_official_canonical_recovery_evidence_acceptance_ag52a.py tests\test_routing.py`:
  138 passed.
- Adjacent recovery/trace slice:
  `py -m pytest --basetemp C:\tmp\ag51c-pytest tests\test_official_canonical_recovery_execution_admission_ag50b.py tests\test_official_canonical_recovery_visibility_export_ag50c.py tests\test_official_canonical_recovery_execution_dispatch_ag50d.py tests\test_official_canonical_recovery_candidate_acquisition_ag50e.py tests\test_source_class_recovery_trace.py tests\test_source_class_recovery_diagnostics_l1.py tests\test_ag15_source_class_recovery_quality_diagnostics.py tests\test_runtime_trace_projection_assembly_ag46c.py`:
  97 passed.
- `py -m ruff check core tests`: passed.
- `git diff --check`: passed with line-ending warnings only.
- `py -m pytest`: attempted full default suite; failed at setup because
  Windows could not remove workspace `.pytest-tmp`
  (`PermissionError: [WinError 5] Access is denied`).
- `py -m pytest --basetemp C:\tmp\.pytest-tmp\ag51c`:
  1672 passed, 1 deselected, 1 warning.

The full-suite warning was the existing Windows `.pytest_cache` access warning.

## Live Validation

No live validation was used.

Reasons:

- this phase repairs prompt/query-policy and should be validated offline first;
- prior live packets already establish the repeated arXiv-only symptom;
- live provider/model runs would add noise before the policy contract is
  reviewed;
- no concrete offline decision was blocked on live data.

## Protected-Surface Confirmation

No changes were made to:

- `core/pipeline_orchestrator.py`;
- provider selection, routing, depth, escalation, or provider integration;
- new providers;
- source-specific adapters, resolvers, catalogs, or hardcoded docs domains;
- broad source ranking/filtering;
- evidence acceptance/source-fit/ranking;
- citation survival/selection;
- Analyst, Economist, Author, Scrutineer, or final-answer behavior.

## Remaining Failure Layer

AG-51C repairs the offline prompt/query-policy contract. It does not prove live
source acquisition is fixed. The remaining failure layer is live product effect
after policy repair: whether canonical technical docs now become visible
accepted recovered candidates and survive downstream.

## Next Licensed Surface Recommendation

Recommended next licensed surface, if the user wants live product confirmation:

- one bounded post-policy live classification phase using the same PostgreSQL
  MVCC query and sanitized candidate/provider/source-class fields;
- do not open provider routing/depth, adapters, citation, or Author behavior by
  default.

If that later live classification shows:

- docs still do not become visible candidates, consider provider routing/depth
  or source-specific adapter architecture as the next licensed surface;
- docs become accepted/readable but fail citation, open citation survival/source
  claim fit;
- docs become cited correctly, close this corridor or move to another dogfood
  source-trust case.

Merge was not performed.
