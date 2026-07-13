Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96G3_G4_FINAL_ANSWER_CLOSURE_E2E_TRIPWIRES).

# AG-96G3/G4 Final Answer Closure And Offline E2E Tripwires

## Status

AG-96G3/G4 closes the downstream final-answer authority gap left intentionally
open by AG-96G2.

AG-96G2 made provider-job EvidenceLedger custody govern
`SufficiencyJudgment` and emit packet-ready `final_packet_inputs`. G3/G4 makes
those inputs materially constrain `FinalAnswerPacket` and the packet-derived
Author payload.

No live provider, model, search, retrieval, fetch, or validation calls are part
of this phase.

## Why G3/G4 Follows G2

The AG-96 spine now reaches sufficiency:

```text
SearchWork / QueryPlan
-> provider-job execution handoff
-> provider-job EvidenceLedger bridge
-> SufficiencyJudgment
```

Before G3/G4, G2 posture could reach packet construction only partially. Some
Author-facing fields still depended on legacy packet obligation projections,
evidence presence, or older final-answer compatibility facts. That left a risk
that sufficiency posture was visible in trace but not consumed by the runtime
consumer that writes the final answer.

G3/G4 closes that by making `FinalAnswerPacket` consume G2
`final_packet_inputs` as packet authority.

## Packet Authority

`FinalAnswerPacket` now carries G2-derived:

- sufficiency decision and final-answer posture;
- final-answer allowed status;
- required-obligation satisfaction;
- readiness status and reasons;
- claim postures;
- missing, partial, and satisfied obligations;
- source-bound numeric unknowns;
- mandatory caveats;
- prohibited upgrades;
- behavior-boundary flags.

Blocked sufficiency remains fail-closed: a blocked packet cannot produce Author
input.

Citation eligibility remains packet-owned. When G2 reports missing or partial
strict obligations, evidence that does not align with a satisfied G2 obligation
class is exposed as citation-ineligible rather than becoming a citation upgrade
by presence alone.

## Author Payload Authority

The Author path continues to receive the existing prompt surface, but it now
also receives a packet-derived, machine-readable authority payload. The payload
includes:

- citation-eligible source IDs;
- citation-ineligible evidence refs and reasons;
- missing, partial, and satisfied source obligations;
- source-bound numeric unknowns;
- mandatory caveats;
- prohibited upgrades;
- final-answer readiness and posture;
- claim posture.

The authority block appended to the existing Author prompt is still generated
from `FinalAnswerPacket`. This phase does not redesign Author prose, prompt
style, source-list formatting, or citation display formatting.

## Offline Tripwires

The AG-96G3/G4 tripwire tests exercise the no-live spine with synthetic
fixtures:

```text
SearchWork projection / QueryPlan existing-query allocation
-> provider-job execution handoff
-> provider-job EvidenceLedger bridge/reduction
-> deterministic SufficiencyJudgment
-> FinalAnswerPacket
-> Author input payload
```

The cases cover:

- official/current satisfied;
- aggregate-only official/current insufficiency;
- lower-tier/context evidence for strict official/current need;
- legal/current-primary satisfied;
- canonical documentation satisfied;
- source-bound numeric custody without extraction;
- mixed multipart satisfied plus missing obligations;
- missing provider-job/G1 bridge payload;
- blocked sufficiency.

The tests also assert redaction of raw prompts, raw provider payloads, raw model
responses, raw text/full text/snippets, secrets, tokens, DB rows, and full
traces.

## Closed Surfaces

This phase does not change:

- provider routing or provider selection;
- search depth;
- query generation;
- retrieval execution, ranking, or filtering;
- QuantWorkUnit extraction or calculation;
- Balanced/Deep follow-up activation;
- Fast official lane runtime behavior;
- Author prose style;
- citation formatting style;
- live validation.

`core/pipeline_orchestrator.py` remains a pass-through coordination surface for
this phase; final-answer decision logic stays in `FinalAnswerPacket` and its
bounded runtime adapters.

## Deferred

Still deferred:

- source-bound numeric extraction and calculation authority;
- QuantWorkUnit activation;
- Balanced/Deep follow-up loops;
- live dogfood and source-quality validation;
- any citation display or Author prose redesign.
