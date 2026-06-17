# AG-96I3L EvidenceLedger Admission-Review Diagnostics

## Status

AG-96I3L adds a pure, offline diagnostic helper:

```text
core.evidence_ledger_admission_review_diagnostics
```

It bridges the next scout/read diagnostics step:

```text
AG-96I3J verified packet
+ AG-96I3K durable sanitized read-observation projection
-> EvidenceLedger admission-review candidate
```

The output answers a narrow custody-readiness question: does the verified
observation contain enough structured, sanitized custody metadata to be eligible
for later EvidenceLedger admission review?

## Diagnostic Boundary

This phase performs admission-review diagnostics only. It does not perform
EvidenceLedger intake, reduce an EvidenceLedger observation, mutate canonical
custody state, create final evidence, create citation eligibility, update
FinalAnswerPacket or SufficiencyJudgment, activate Author behavior, call
providers, run search, fetch/read live pages, invoke models, or change product
behavior.

The packet remains explicitly non-authoritative:

```text
final_evidence=false
citation_eligible=false
evidence_ledger_admitted=false
author_activation_allowed=false
```

Actual EvidenceLedger intake remains deferred to a later licensed phase.

## Inputs

The helper consumes:

- an AG-96I3J fetch/read currentness verification packet;
- an AG-96I3K durable sanitized read-observation projection;
- optional caller-supplied review requirements.

If a caller supplies a full AG-96I3K sanitized read observation, the helper uses
only its `durable_projection`. It does not consume or retain the ephemeral
`verifier_input.text` region.

## Outputs

The diagnostic candidate records:

- candidate, attempted, and resolved URL/domain identity where available;
- AG-96I3J verification status, source identity status, official/source posture,
  currentness posture, relevance posture, and candidate-fit posture;
- AG-96I3K read posture, fetch/read status, content metadata, date signals, and
  text-count metadata;
- custody metadata completeness posture;
- blocker/reason codes and recommended next step;
- a durable projection suitable for traces or reports;
- non-authoritative boundary flags.

Ready candidates use:

```text
admission_review_status=admission_review_candidate_ready
recommended_next_step=evidence_ledger_intake_review_later
```

That next step names a later review/intake phase. It is not admission itself.

## Blocked Cases

The helper emits explicit blockers for missing durable projections, unreadable
read projections, unsuccessful AG-96I3J verification, URL/domain mismatches,
unverified identity, unclear currentness, unclear relevance, unclear source
class or official posture, incomplete custody metadata, and raw-text retention
attempts.

## Closed Surfaces Preserved

AG-96I3L does not change:

- provider routing, provider selection, provider depth, or query behavior;
- retrieval ranking/filtering, SearchWorkPlan, or QueryPlan behavior;
- EvidenceLedger intake or canonical custody mutation;
- SufficiencyJudgment, FinalAnswerPacket, Author, or citation behavior;
- prompts;
- live ScryRaven/proplex provider, search, model, fetch/read, or validation
  calls;
- `core/pipeline_orchestrator.py` domain logic.
