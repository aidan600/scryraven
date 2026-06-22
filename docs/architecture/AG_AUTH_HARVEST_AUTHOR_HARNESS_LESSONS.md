# AG-AUTH-HARVEST Author Harness Lessons Inventory

Status: Documentation checkpoint / roadmap guardrail.
Date: 2026-06-22

## Purpose

This note preserves lessons from the AF4B2 -> AF4C -> AF4D -> AF5A -> AF5B Author component lane without treating that lane as ordinary product-path completion.

AG-CHECK-01 established that ordinary `run_pipeline()` already consumes packet-constrained Author authority through the existing FinalAnswerPacket -> AuthorExecutor path. It also established that the AF component lane is not directly consumed by ordinary `run_pipeline()` today.

Correct posture:

```text
The AF4B2 -> AF5B lane is not the ordinary product path.
Do not promote it by implication.
When future phases touch Author payload/materialization/execution/finalization,
harvest its lessons deliberately.
```

## Avoided bad reactions

Do not overcorrect in either direction:

```text
Bad reaction A: "The harness was fake, throw it away."
Bad reaction B: "We spent time on it, so install it."
```

The right reaction is:

```text
Treat it as a stricter Author-custody reference lab.
Harvest its invariants when a real Author-facing product phase opens.
```

## What AG-CHECK-01 clarified

Current facts after AG-CHECK-01:

1. Ordinary `run_pipeline()` already has packet-constrained Author authority.
2. AF4B2 -> AF5B is a component harness/reference lab, partially shared and bridgeable, not the ordinary product path.
3. More Author harness work is not the immediate roadmap priority.
4. AG-SEM-01 Passive Semantic Contract Foundation is not blocked by the AF lane.
5. Future Author-facing phases should decide deliberately whether to port, replace, or leave aside AF-stage mechanisms.

## Harness lessons worth preserving

The AF lane remains valuable because it demonstrated useful custody patterns:

| Harness lesson | Future product value |
| --- | --- |
| Bounded Author evidence content bridge | Author should receive scoped answer-bearing material, not a broad unstructured corpus. |
| Explicit invocation construction | Author inputs should be built through inspectable, authorized packets rather than scattered orchestration locals. |
| Explicit model-request assembly | Request construction can be audited through IDs, digests, and retention flags without exposing raw prompt text. |
| Adapter accounting | Fake, mocked-live, brokered-live, and real-live model calls should be distinguishable and budgeted. |
| Sanitized candidate response | Model output can be carried through bounded refs/digests and finalization status without retaining raw provider payloads. |
| Finalization seam | Final output can be reduced into accountable state while keeping raw prompt/model text out of canonical traces. |
| Broker boundary | Private adapters are credential plumbing only, not provider policy, evidence authority, or product logic. |

## How to use this later

Do not install the AF lane merely because it exists.

When a future phase explicitly opens one of these surfaces:

- Author payload;
- Author input materialization;
- Author invocation construction;
- Author model request assembly;
- Author execution;
- Author response finalization;
- FinalAnswerPacket Author-facing authority;
- semantic component claims carried to Author;

then the phase should choose one of these options:

1. keep ordinary `core.author_execution_runtime.execute_author_action` and port selected AF invariants into it;
2. replace a bounded ordinary Author sub-step with an AF-stage module;
3. keep AF as a reference harness only and document why it is not being promoted.

That choice should be made by a licensed Author-facing product phase, not by inertia.

## Immediate roadmap impact

Proceed with semantic-contract work:

```text
AG-SEM-01: QuestionMeaningRecord / answer components / contract lineage
AG-SEM-02: sanitized content-reference + SemanticObservation schema
AG-SEM-03: ComponentCoverageRecord schema
AG-SEM-04: ContractAmendmentRecord schema
```

The content-reference schema belongs with or before SemanticObservation because observations need an allowed, sanitized, evidence-bound thing to point at.

Do not do more Author harness work now unless a specific Author-facing product phase is selected.

## Guardrail for future phases

Every future authority or semantic phase should answer:

```text
Is this new authority consumed by the ordinary product path,
or is it only a component harness/projection/test seam?
```

If it is only a harness, that is acceptable only when the phase is explicitly a harness/proof phase. Otherwise, the phase should either wire the intended runtime consumer or stop for an architecture decision.

## Closed by this note

This note does not authorize:

- production activation of AF4B2 -> AF5B;
- Author prompt or prose changes;
- provider/model/search/fetch/read behavior changes;
- semantic-contract runtime activation;
- FinalAnswerPacket payload changes;
- live validation;
- package/CLI/env renames;
- broad `core/pipeline_orchestrator.py` work.
