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

## Fast Micro-hop Validation

Fast remains RunAuthority-governed. Fast is not "non-reasoning": it may perform
passive micro-hop validation over already-available sanitized record facts.

Fast micro-hop validation may inspect and classify:

- evidence custody status;
- source class / source tier fit;
- bridge-only provider output status;
- currentness gaps;
- source-bound numeric unknown or resolution status;
- citation and final-answer posture gaps;
- whether selected Fast mode is sufficient;
- whether the final posture should be direct, caveated, insufficient, refused,
  or escalated to Balanced/Deep.

Fast micro-hop records are validation and posture records only. They do not
create AG-96I1 follow-up authorization candidates, do not recommend provider-job
execution, and do not grant Fast the Balanced/Deep meso or macro deliberation
surface.

Mode boundary:

| Mode | Micro validation | Meso targeted repair | Macro run diagnosis |
| --- | --- | --- | --- |
| Fast | yes | no new AG-96I1A behavior; separately licensed narrow direct repair seams may exist outside this grammar | no |
| Balanced | yes | yes, bounded | no |
| Deep | yes | yes, larger bounded | yes, capped |

Fast can classify bridge-only evidence, numeric unknowns, citation/final-answer
posture gaps, caveat/refusal posture, and selected-mode insufficiency. When a
gap requires contract-shape or conflict/reconciliation work, Fast records
`selected_mode_insufficient` / `needs_balanced_or_deep` rather than pretending to
run Deep-only reconciliation.

AG-96I1A does not change runtime Fast behavior, provider routing, provider
selection, search depth, query generation, retrieval execution, retrieval
ranking/filtering, Author prose, citation formatting, or final-answer style.

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
- mark `selected_mode_insufficient` / `needs_balanced_or_deep` when Fast
  encounters work that requires Balanced or Deep rather than Fast micro
  validation.

## Bridge-only Provider Output Rule

Provider answer, deep product, synthesis, and bridge hints remain bridge/context
only. They may produce candidate URLs, terms, or hypotheses for later
fetch/read/admission, but they cannot satisfy final evidence, source-bound
numeric values, citation eligibility, or final-answer posture by themselves.

## Deferred To AG-96I2

AG-96I2A consumes these passive checkpoints into canonical RunKernel
sealed/denied follow-up authorization state while keeping every seal
non-executable. See
[AG96I2A_FOLLOWUP_AUTHORIZATION_SEALING.md](AG96I2A_FOLLOWUP_AUTHORIZATION_SEALING.md).

Still deferred after AG-96I2A:

- runtime-gated execution of sealed follow-up jobs;
- live dogfood;
- provider/cost evaluation;
- provider capability registry backed by real provider behavior;
- new providers or provider routing changes;
- search-depth, query-generation, retrieval ranking/filtering, Author prose, or
  citation formatting changes.

## Deferred: Conversational Follow-up Search / Follow-up Turn Contract

AG-96I1 and AG-96I1A concern in-run follow-up deliberation:

```text
first-pass evidence
-> gap detected
-> bounded provider-job recommendation / authorization candidate
```

They do not handle a later user turn such as:

- "What about California?"
- "Is that still true today?"
- "Compare that to Canada."
- "Find a better source."
- "Can you say that more simply?"

That conversational follow-up surface is deferred. The future desired shape is:

```text
new user turn
-> classify relationship to prior answer
-> decide whether prior EvidenceLedger / FinalAnswerPacket can be reused
-> amend or create RunAuthorityContract
-> create new/extended SearchWork components
-> re-check source obligations and currentness
-> run normal mode-bounded policy
```

A conversational follow-up must not inherit prior evidence as automatically
sufficient. Prior evidence can be reused only when:

- entity, scope, and time window still match;
- currentness has not become stale for the new claim;
- prior source obligations still apply;
- the new question does not add a new component or stricter obligation;
- prior FinalAnswerPacket did not mark the evidence caveated, partial, or
  citation-ineligible.

AG-96I1A documents this deferred boundary only. It does not implement
conversational follow-up search, prior-answer reuse, Follow-up Turn Contract
runtime behavior, or any new SearchWork execution path.
