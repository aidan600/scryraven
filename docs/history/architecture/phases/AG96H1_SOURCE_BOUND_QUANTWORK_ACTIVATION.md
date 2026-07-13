Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96H1_SOURCE_BOUND_QUANTWORK_ACTIVATION).

# AG-96H1 Source-Bound QuantWork Activation

## Status

AG-96H1 activates a bounded offline QuantWorkUnit runtime packet for
source-bound numeric questions.

No live provider, model, search, retrieval, fetch, OCR, prompt, citation-format,
or Author-prose behavior is changed. The runtime does not use arbitrary formula
execution, `eval`, `exec`, shell calculation, subprocesses, notebooks, or model
reasoning.

## Why H1 Follows G3/G4

AG-96E2 made QueryPlan consume SearchWork metadata only to allocate already
existing query strings. AG-96F1 recorded provider-job execution handoff. AG-96G1
bridged retrieved candidates into EvidenceLedger custody. AG-96G2 made
SufficiencyJudgment consume that custody, while intentionally leaving
source-bound numeric values unknown until extraction/calculation existed.
AG-96G3/G4 carried that unknown posture into FinalAnswerPacket and the
packet-derived Author authority payload.

H1 closes only the next gap:

```text
RunAuthorityContract
-> SearchWork / QueryPlan
-> provider-job execution handoff
-> retrieved candidate fixture
-> EvidenceLedger custody
-> QuantWorkUnit runtime packet
-> SufficiencyJudgment final_evidence_facts
-> FinalAnswerPacket / Author payload
```

## Existing Posture Audit

Before H1, `SearchWorkPlan` could represent `QuantWorkUnit` records, but they
were passive planning objects. Provider-job handoff could carry
source-bound-numeric work to an existing query, and EvidenceLedger could custody
a candidate for `sourced_numeric_values`. G2 then treated that custody as
necessary but not sufficient: if extraction had not executed, a satisfied
source-bound numeric requirement became `source_bound_numeric_unknowns`.

G3/G4 already forwarded those unknowns through `final_packet_inputs`,
`FinalAnswerPacket.source_bound_numeric_unknowns`, and the Author authority
payload. That protected final answers from presenting a numeric value as known
merely because a candidate or aggregate source count existed.

## Source-Bound Numeric Meaning

For H1, source-bound numeric means a requested numeric variable or calculation
may become direct-answer eligible only when every input value is:

- named by the QuantWorkUnit required variables;
- extracted from compact, safe structured fixture metadata or tiny fixture
  passage text;
- bound to a candidate ref already custodied by EvidenceLedger;
- not lower-tier, contextual, uncustodied, aggregate-only, ambiguous, or
  conflicting;
- unit-compatible for the requested whitelisted calculation.

Name similarity alone is not enough. A fact for `other_rate` cannot satisfy
`rate`.

## Planning Versus Runtime

`core/search_work_plan.py` remains representational. `QuantWorkUnit` still says
what numeric work is planned and which calculations are allowed; it does not
execute extraction or calculation.

The runtime consumer is `core/quant_work_unit_runtime.py`. It consumes
QuantWorkUnit projections plus EvidenceLedger-custodied candidate refs and emits
trace-safe machine-readable packets. The packet records ids, variables,
extracted values, unresolved values, calculation status, source refs, blockers,
high-stakes posture, and behavior-boundary flags. It omits raw prompts, raw
provider payloads, raw model output, raw/full text, secrets, DB rows, caches,
private logs, and full traces.

## Extraction And Calculation Boundaries

Extraction is deliberately narrow:

- structured fixture fields such as `numeric_facts`, `source_bound_values`, and
  `extracted_values` are preferred;
- compact fixture passage text may be parsed only for simple `name=value unit`
  test fixtures;
- packet traces store text hash/length, not raw text;
- values must be tied to custodied candidate ids.

Allowed calculations are:

- identity / direct value;
- difference;
- ratio;
- percent_change;
- sum;
- average.

Everything else blocks. Missing variables, missing required units, incompatible
units, ambiguous values, lower-tier values, uncustodied values, aggregate-only
counts, and high-stakes missing exact values keep the numeric unknown posture.

## Sufficiency Update

SufficiencyJudgment now consumes QuantWorkUnit packets through
`final_evidence_facts`. A successful packet clears the matching
source-bound-numeric unknown by component/source-obligation/requirement refs.
Blocked or unresolved packets remain visible as `source_bound_numeric_unknowns`.

Numeric success does not satisfy unrelated official/current, legal/current,
canonical, or other required source obligations.

## FinalAnswerPacket And Author Payload

`FinalAnswerPacket` now carries `source_bound_numeric_resolutions` alongside the
existing `source_bound_numeric_unknowns`. The Author-facing authority payload
receives resolved values, calculation result, source refs, unresolved values,
mandatory caveats, prohibited upgrades, and behavior-boundary flags.

This is an authority-payload addition only. It does not rewrite Author prose
style or citation formatting.

## Deferred

Still deferred:

- Balanced/Deep follow-up loops;
- live dogfood and source-quality validation;
- broader unit normalization and dimensional analysis;
- richer extraction outside compact safe fixture metadata;
- product/UX polish for how resolved calculations should be presented;
- provider routing, provider selection, search depth, query generation,
  retrieval ranking/filtering, citation formatting, and Author prose redesign.
