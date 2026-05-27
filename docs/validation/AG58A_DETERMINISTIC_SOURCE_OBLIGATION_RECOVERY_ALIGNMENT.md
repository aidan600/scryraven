# AG-58A Deterministic Source-Obligation and Recovery Alignment

## Phase Purpose

AG-58A aligns deterministic source-obligation, source-class satisfaction,
recovery-query, and recovered-evidence visibility helpers with the AG-57A /
AG-57B source hierarchy and AnswerContract ownership contract.

This is a deterministic helper/test phase. It does not rewrite prompts, change
provider behavior, alter routing/depth, change citation behavior, or change
final-answer posture.

## Licensed Surface

Opened:

- deterministic source-obligation helper behavior;
- source-class expected/required class alignment;
- official/current/canonical recovery-query alignment;
- recovered-evidence visibility and source-fit classification semantics;
- source-class satisfaction/status diagnostics;
- offline tests and this validation note.

Closed:

- Router and Researcher prompt changes;
- provider routing, provider selection, provider depth, provider integration,
  and new providers;
- source ranking/filtering redesign;
- recovery execution/provider behavior;
- citation behavior and final-answer posture;
- Analyst, Economist, Author, Scrutineer, follow-up, and weak-corpus behavior;
- `core/pipeline_orchestrator.py`;
- live validation;
- raw runtime prompts, raw provider payloads, DB rows, logs, caches, secrets,
  `.env`, and full traces.

## AG-57A / AG-57B Baseline

Baseline `main` included AG-57B at merge commit `91c6fe9`, which also includes
AG-57A. The relevant inherited invariants are:

- the source class required by the claim outranks a generally better but
  non-authoritative source class;
- canonical technical docs govern current software, database, API, package,
  SDK, browser, protocol, project behavior, reference semantics, release
  behavior, documented behavior, configuration, and options unless the user
  explicitly asks for academic literature;
- explicit peer-reviewed, literature review, arXiv, empirical study, and
  benchmark-literature requests remain academic;
- official/current numeric, legal/current-primary, and source-bound rule
  claims are not satisfied by secondary-only evidence;
- ordinary conceptual explainers do not force official/current/canonical
  recovery;
- mixed canonical plus academic obligations remain a strict xfail.

## Deterministic Helper Changes

`core/source_class_recovery.py` now reuses the existing canonical technical docs
policy helper when determining expected source classes. Canonical technical docs
requests such as PostgreSQL MVCC, SQLite WAL, Python dataclasses, MDN Fetch API,
and Kubernetes configuration now preserve a `primary_source_documents`
obligation in the deterministic recovery/observability helper.

For canonical technical documentation gaps, `primary_source_documents` recovery
queries now use generic official/reference documentation phrasing instead of
generic primary-source/archive phrasing.

Declared source-class metadata is no longer enough to strongly satisfy a
required source class when the candidate is secondary, community, social,
content-mill, or low-trust commercial. Those candidates may remain visible as
secondary-only diagnostic evidence, but they do not satisfy official/current,
legal/current, or canonical documentation obligations.

Secondary articles that discuss canonical documentation are labeled
`expected_but_only_secondary` when canonical docs are required, preserving the
missing required class without overstating the source fit.

## Tests Added Or Changed

Added:

- `tests/test_ag58a_deterministic_source_obligation_recovery_alignment.py`

Coverage includes:

- canonical technical docs positive cases;
- explicit academic negative controls;
- official/current numeric and rule secondary-only controls;
- legal/current-primary AnswerContract recovery ownership;
- ordinary conceptual explainer negative control;
- weak/no-good evidence stop posture preservation;
- recovered-evidence visibility rejection for secondary/social declared classes;
- official/canonical recovered candidate visibility;
- unknown candidate-stage fields remaining unknown;
- AG-50A canonical docs query alignment;
- AG-57A mixed canonical plus academic strict xfail preservation;
- secondary-only AnswerContract handoff posture;
- protected-surface static guards.

## Mixed Canonical Plus Academic Gap

The mixed obligation shape remains unresolved by design:

```text
What do the docs say, and what do studies show?
```

AG-58A does not add multi-source AnswerContract representation and does not
repair the strict AG-57A xfail. That remains a product/modeling decision for a
future phase.

## Validation Decision

No live validation was used.

Offline tests are sufficient because this phase changes only deterministic
source-obligation/recovery helper semantics and source-fit diagnostics. Live
provider/model/search validation remains closed.

## Next Recommended Surface

The next licensed surface should stay in deterministic Controller /
AnswerContract source-obligation handoff if more gaps are found.

Do not open provider routing/depth, retrieval ranking/filtering, prompt
rewrites, citation selection, Author behavior, or final-answer posture from
AG-58A alone. If the mixed canonical plus academic xfail must be repaired,
stop for a product/modeling phase first.
