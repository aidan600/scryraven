# AG-96I2B Follow-up Fixture Dispatch

## Status

AG-96I2B adds the next runtime seam after AG-96I2A:

```text
sealed follow-up candidate
-> gated fixture-only execution request
-> sanitized fixture execution observation
-> RunKernel canonical follow-up execution state
-> derived follow-up execution projection
-> EvidenceLedger intake remains deferred
```

This phase is offline and fixture-only. It does not call live providers, search,
retrieval, fetch/read, prompts, models, provider-job executors, citation
formatters, Author paths, or `core/pipeline_orchestrator.py` domain logic.

## Why This Follows AG-96I2A

AG-96I2A made passive `FollowupDeliberationCheckpoint` records runtime-consumed
by RunKernel and sealed valid candidates as `sealed_non_executable`. AG-96I2B
keeps those seals non-provider-executable, but proves the future execution
adapter shape by consuming one sealed candidate through an explicit fixture-only
gate.

The new records live in `core.followup_execution_runtime` and are
schema-versioned as `followup_execution_ag96i2b_v1`:

- `FollowupExecutionRequest`;
- `FollowupExecutionResult`;
- `FollowupExecutionObservation`;
- `FollowupExecutionConsumptionRecord`.

They preserve run/checkpoint identity, AG-96I2A consumption identity, sealed
candidate identity, provider-job kind, component and source-obligation links,
expected EvidenceLedger custody update, planned budget debit, fallback posture,
bridge-only status, sanitized fixture summary, no-live flags, gate details, and
redaction posture.

## Fixture-only Dispatch

The default execution mode is `disabled`. The only accepted execution mode in
AG-96I2B is `fixture_only`, and it requires an explicit sanitized fixture result
payload.

The gate records:

- provider execution remains unlicensed;
- no live provider call executed;
- no search executed;
- no retrieval executed;
- no fetch/read executed;
- no model called;
- no provider-job executor connected;
- no EvidenceLedger evidence admitted.

Any live/provider/search/retrieval/fetch/model or non-fixture execution mode
fails closed before an observation is produced.

## RunKernel Consumption

RunKernel now has a bounded follow-up fixture execution action and reducer:

```text
RunKernel.authorize_followup_fixture_execution(...)
-> core.followup_execution_runtime.execute_followup_fixture_action(...)
-> RunKernel.reduce(...)
-> RunState.followup_execution_state
-> RunState.followup_execution_projection
-> RunState.followup_execution_history
```

The projection is derived from canonical `RunState.followup_execution_state`.
The existing AG-96I2A `followup_authorization_state` remains intact. The reducer
rejects observations that claim live provider/search/retrieval/fetch/model work,
EvidenceLedger mutation, EvidenceLedger evidence admission, or a non-fixture
execution gate.

## Mode Handling

Fast remains posture-only. Fast seals no candidates through AG-96I2A. If a
malicious Fast sealed candidate is supplied to the fixture executor, AG-96I2B
rejects it fail-closed.

Balanced sealed meso targeted-repair candidates may be fixture-executed only in
`fixture_only` mode. Balanced `needs_deep`, denied, macro diagnosis, and
reconciliation-support states remain unexecutable.

Deep sealed meso or macro/reconciliation candidates may be fixture-executed only
in `fixture_only` mode. Deep assumption audit remains available on the
authorization state, but AG-96I2B does not perform real reconciliation and does
not admit evidence.

## Budget Semantics

AG-96I2B preserves the planned debit from the sealed candidate, but fixture
execution does not incur provider/search/fetch/read cost, does not debit a live
provider account, and does not add real provider-cost accounting. Real cost
accounting remains deferred to a later provider execution phase.

## Bridge-only Rule

Bridge-only fixture results are recorded as `fixture_bridge_only`. They cannot
satisfy final evidence, cannot create citation eligibility, cannot mutate
EvidenceLedger, and preserve the fallback posture from the sealed candidate.

## Deferred To AG-96I2C And Later

Deferred work includes EvidenceLedger intake for follow-up execution
observations, real provider-job execution, live dogfood, provider/cost
evaluation, provider capability evaluation, and the conversational Follow-up
Turn Contract. AG-96I2B is only the gated fixture dispatch seam.
