# AG-96I1 Bounded Follow-up Deliberation Records

## Status

AG-96I1 adds passive/offline records for Balanced/Deep bounded follow-up
deliberation. It defines the grammar for gap typing, reasoning hops, provider
job recommendations, authorization candidates, budget decisions,
stop/caveat/refuse posture, sufficiency handoff, and Deep assumption audit.

This phase does not execute follow-up search. It does not change provider
routing, provider selection, search depth, query generation, retrieval ranking
or filtering, Author prose, citation formatting, live behavior, or
`core/pipeline_orchestrator.py` domain logic.

## Why AG-96I1 Follows AG-96H1

AG-96G3/G4 made final-answer closure consume SufficiencyJudgment and
FinalAnswerPacket authority. AG-96H1 then activated only the narrow
source-bound QuantWork packet path, proving that custodied numeric evidence can
resolve a numeric requirement without upgrading unrelated official/current,
legal/current, or canonical obligations.

The next missing capability is not more retrieval. It is the passive authority
grammar for deciding whether a named evidence gap could justify a future bounded
follow-up job:

```text
evidence state
-> gap assessment
-> mode/budget check
-> bounded provider-job recommendation / authorization candidate
-> stop/caveat/refuse fallback
-> later RunKernel execution in a future phase
```

AG-96I1 stops before runtime execution so the records can be validated offline
without turning Balanced or Deep into autonomous browsing.

## Passive Boundary

The checkpoint records are JSON-safe, deterministic, redacted, and
schema-versioned. They explicitly record false capability flags for direct
browsing, direct fetching, arbitrary code execution, citation selection, final
sufficiency override, provider/search behavior changes, retrieval behavior
changes, prompt behavior changes, citation behavior changes, and Author prose
changes.

A `FollowupAuthorizationCandidate` is only a candidate. In AG-96I1 it is not a
RunAuthority seal and not executable runtime permission.

## Gap Taxonomy

AG-96I1 records the canonical follow-up gap types:

- `component_coverage_gap`
- `source_class_gap`
- `official_current_gap`
- `legal_current_primary_gap`
- `canonical_doc_gap`
- `source_bound_numeric_gap`
- `currentness_gap`
- `conflict_reconciliation_gap`
- `entity_ambiguity_gap`
- `weak_corpus_gap`
- `citation_final_answer_posture_gap`
- `contract_shape_gap`

Each follow-up recommendation must name a gap type and, for repairable gaps,
tie it to a component, source obligation, provider-job kind, expected
EvidenceLedger custody update, budget debit, and fallback posture.

## Hop Taxonomy

AG-96I1 records three reasoning-hop levels:

- `micro_verification`: verifies custody, final-answer posture, numeric unknowns,
  citation eligibility, or whether extra work would be decorative.
- `meso_targeted_repair`: recommends one bounded job for a concrete gap, such as
  official/current acquisition, canonical-doc acquisition, source-bound numeric
  support, or fetch/read repair.
- `macro_run_diagnosis`: diagnoses run-level contract shape, source-family
  topology, currentness/conflict reconciliation, and Deep assumptions.

Balanced may produce micro and meso recommendations, but cannot authorize macro
diagnosis. Deep may produce macro diagnosis and reconciliation-support
candidates, still with caps and stop posture.

## Balanced Boundary

Balanced can represent one-hop official/current, canonical, numeric, entity,
weak-corpus, source-class, and citation/final-answer posture repair
recommendations when they are central, concrete, budgeted, and expected to
change EvidenceLedger custody.

Balanced cannot authorize:

- `macro_run_diagnosis`;
- Deep-only reconciliation support;
- repeated recovery for the same failed gap;
- budget debits that starve another unserved central component;
- bridge-only provider answer text as final evidence;
- decorative search after the final-answer posture is already sufficient.

When a gap exceeds Balanced, the checkpoint records `needs_deep`, caveat,
insufficient evidence, or refusal posture rather than opening a hidden research
loop.

## Deep Boundary

Deep can represent macro diagnosis, source-family/currentness/conflict
reconciliation support, assumption audit, fragility, and sensitivity records.
Deep remains bounded: macro hops, follow-up rounds, provider calls, fetch/read
units, and retries are explicit budget dimensions. If Deep reconciliation
remains unresolved after the bounded candidate, the checkpoint stops with a
conflict map, caveat, partial answer, insufficient evidence, or refusal posture.

## Provider Jobs Versus Direct Browsing

AG-96I1 uses provider-job kinds as provider-neutral recommendations:

- `scout_disambiguation`
- `direct_candidate_search`
- `official_current_candidate_acquisition`
- `legal_current_primary_acquisition`
- `canonical_doc_acquisition`
- `semantic_recall`
- `fetch_read_extract`
- `conflict_currentness_check`
- `source_bound_numeric_extraction_calculation_support`
- `reconciliation_support`
- `bridge_hint_discovery`
- `provider_answer_context`

The checkpoint may name a bounded provider job. It may not browse, fetch, call
providers, admit evidence, select citations, or authorize executor recursion.
Future AG-96I2 work must route any executable job through RunAuthority/RunKernel
and then back through EvidenceLedger custody.

## Budget Model

AG-96I1 models budget as multidimensional:

- cost points;
- provider calls;
- fetches;
- read units;
- follow-up rounds;
- meso authorizations;
- macro hops.

Candidate discovery must reserve custody budget when custody is required. A
budget debit is denied when any dimension is exhausted or when the debit would
starve another unserved central component below its minimum viable chance.

## Stop, Caveat, And Refuse

The checkpoint records fallback posture before any future execution:

- stop when the contract is sufficient, the gap is decorative, the same recovery
  already failed, or the source obligation cannot be repaired in mode;
- caveat or partial-answer when central evidence is incomplete but a safe answer
  can be bounded;
- refuse or block when high-stakes legal/current-primary or unsafe unknowns
  cannot be supported;
- mark `needs_deep` when Balanced encounters macro reconciliation or contract
  shape work.

## Bridge-only Provider Output Rule

Provider answer, deep product, synthesis, and bridge hints remain bridge/context
only. They may produce candidate URLs, terms, or hypotheses for later
fetch/read/admission, but they cannot satisfy final evidence, source-bound
numeric values, citation eligibility, or final-answer posture by themselves.

## Deferred To AG-96I2

Still deferred:

- runtime-gated execution of sealed follow-up jobs;
- RunKernel consumption of authorization records;
- live dogfood;
- provider/cost evaluation;
- provider capability registry backed by real provider behavior;
- new providers or provider routing changes;
- search-depth, query-generation, retrieval ranking/filtering, Author prose, or
  citation formatting changes.
