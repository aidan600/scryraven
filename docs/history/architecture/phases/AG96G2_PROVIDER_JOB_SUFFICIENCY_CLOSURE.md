Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96G2_PROVIDER_JOB_SUFFICIENCY_CLOSURE).

# AG-96G2 Provider-Job Sufficiency Closure

## Status

AG-96G2 makes AG-96G1 provider-job EvidenceLedger custody govern the existing
RunAuthority SufficiencyJudgment path.

This is a sufficiency/readiness phase. It does not change provider routing,
provider selection, search depth, query generation, retrieval execution,
retrieval ranking/filtering, prompts, citation formatting, Author prose,
FinalAnswerPacket schema, QuantWorkUnit extraction/calculation, Balanced/Deep
follow-up activation, Fast official lane behavior, or live validation.

## Why G2 Follows G1

AG-96F1 recorded how SearchWork provider-job hints reached already-authorized
query strings. AG-96G1 converted those provider-job handoffs plus retrieved
candidate records into RunKernel-owned EvidenceLedger custody:

```text
SearchWork component
-> source obligation
-> provider-job execution record
-> retrieved candidate
-> EvidenceLedger source requirement / custody status
```

Before G2, that custody could be visible in EvidenceLedger trace without
materially changing final sufficiency posture. G2 closes that gap by making the
existing deterministic SufficiencyJudgment consume the post-G1 EvidenceLedger
projection.

## Runtime Path

The runtime path remains the existing RunKernel chain:

```text
provider-job G1 bridge payload
-> execute_evidence_ledger_reduction_action(...)
-> RunKernel.reduce(...)
-> RunState.evidence_ledger
-> build_sufficiency_judgment_input_from_runtime(...)
-> build_deterministic_sufficiency_judgment(...)
-> execute_sufficiency_judgment_handoff_from_scope(...)
-> RunKernel.reduce(...)
```

`pipeline_orchestrator.py` stays a pass-through caller. It does not contain new
sufficiency domain logic.

## Matching Rules

SufficiencyJudgment now matches RunAuthorityContract obligations to
EvidenceLedger requirements through conservative, trace-safe keys:

- exact requirement id;
- normalized requirement id;
- component id;
- source obligation id;
- provider-job id;
- origin/provider-job execution refs;
- compatible requirement kind, source class, tier, and currentness.

Provider-job-derived EvidenceLedger requirements are preferred over a bare
contract skeleton requirement when they carry richer custody status. The matcher
does not infer satisfaction from citation presence, aggregate source counts, or
unrelated same-family evidence.

## Obligation Posture

EvidenceLedger `satisfied` requirements become satisfied SufficiencyJudgment
obligations when the requirement is a trace-safe match. `unsatisfied`,
`unknown`, `not_observable`, and `partially_satisfied` requirements remain
missing or partial.

Aggregate-only official/current, legal/current-primary, canonical, or
source-bound evidence cannot satisfy strict custody because it lacks candidate
identity, candidate/source fit, and provider-job lineage. Lower-tier,
context-only, stale, unreadable, or off-class candidates likewise cannot satisfy
strict official/current, legal/current-primary, canonical, or source-bound
requirements.

Source-bound numeric custody remains separate from numeric extraction. A
candidate-level source-bound numeric requirement can establish source custody,
but the numeric value remains unknown until a future QuantWorkUnit or extraction
phase produces a value/calculation signal. SufficiencyJudgment records
`source_bound_numeric_unknowns` and blocks direct numeric-answer readiness.

## Final Packet Inputs

SufficiencyJudgment `final_packet_inputs` now carry packet-ready machine-readable
posture:

- decision and final-answer posture;
- readiness status and reasons;
- required-obligation satisfaction;
- missing, partial, and satisfied obligations;
- source-bound numeric unknowns;
- mandatory caveats;
- prohibited upgrades;
- behavior-boundary flags confirming no provider/search/retrieval/prompt/
  citation/Author/quant execution change.

FinalAnswerPacket and Author remain downstream consumers. This phase does not
redesign FinalAnswerPacket selection or write Author prose.

## Deferred

Still deferred:

- FinalAnswerPacket schema redesign;
- Author prose/citation-format changes;
- provider routing, provider selection, search depth, and query generation;
- retrieval execution, ranking, or filtering changes;
- source-bound numeric extraction/calculation;
- Balanced/Deep follow-up loop activation;
- Fast official lane runtime demotion;
- live validation.
