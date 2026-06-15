# AG-96I2A Follow-up Authorization Sealing

## Status

AG-96I2A consumes the passive AG-96I1 / AG-96I1A
`FollowupDeliberationCheckpoint` records into canonical RunKernel follow-up
authorization state. The consumed state can seal or deny follow-up candidates,
but every seal is non-executable in this phase.

No provider, search, retrieval, fetch/read, routing, search-depth, query
generation, ranking/filtering, Author prose, citation formatting, live dogfood,
or `core/pipeline_orchestrator.py` domain behavior is changed.

## Why This Follows AG-96I1A

AG-96I1 defined a passive grammar for follow-up deliberation records. AG-96I1A
clarified that Fast may do passive micro-hop validation but may not authorize
Balanced or Deep follow-up work.

AG-96I2A adds the missing runtime consumption seam:

```text
FollowupDeliberationCheckpoint
-> validation
-> RunKernel follow-up authorization consumption
-> canonical sealed/denied follow-up state
-> derived trace/projection
```

This prevents the checkpoint from remaining a trace-only projection while still
stopping before provider-job execution.

## New Runtime State

The canonical consumed state is schema-versioned as
`followup_authorization_ag96i2a_v1` and is produced by
`core.followup_authorization_runtime.consume_followup_deliberation_checkpoint`.
It records:

- checkpoint and run identity;
- input checkpoint hash;
- validation status and fail-closed errors;
- selected sealed candidate IDs;
- denied candidate IDs;
- consumed stop, caveat/refuse, reasoning-hop, and budget records;
- denied budget debits and planned future debits;
- selected-mode-insufficient, `needs_balanced_or_deep`, and `needs_deep`
  posture;
- Deep assumption audit when present;
- redaction posture and no-raw-payload flags;
- behavior-boundary flags proving no provider/search/retrieval execution.

RunKernel stores this as `RunState.followup_authorization_state` through the
`FOLLOWUP_AUTHORIZATION_STAGE` reducer and exposes trace derived from that state.

## Mode Handling

Fast checkpoints may be consumed. Their micro-hop validation, caveat/refuse,
stop, and selected-mode-insufficient posture are preserved. Fast seals no
authorization candidates and cannot create provider execution permission.

Balanced checkpoints may seal valid targeted repair candidates as
`sealed_non_executable`. Balanced `needs_deep`, repeated failed recovery,
budget exhaustion, and decorative-search blocks remain stop or denial posture.
Balanced still cannot seal macro diagnosis or reconciliation support.

Deep checkpoints may seal valid macro or reconciliation candidates as
`sealed_non_executable`. The Deep assumption audit is preserved for later
SufficiencyJudgment or FinalAnswerPacket phases. Deep still cannot execute
provider jobs in AG-96I2A.

## Execution Gate

Every sealed candidate and the aggregate consumed state carry:

```json
{
  "execution_permission": false,
  "executable_in_current_phase": false,
  "provider_execution_licensed": false,
  "reason": "provider_execution_not_licensed_in_ag96i2a"
}
```

`request_followup_provider_execution` fails closed with this reason. RunKernel
also rejects any follow-up authorization observation whose gate claims current
execution permission.

## Budget Semantics

AG-96I2A preserves planned and denied budget debits from the checkpoint but does
not spend real provider budget. The consumed state marks planned debits as
future-phase-only and records that no provider/search/fetch/read cost was
incurred. Provider-cost accounting remains deferred.

## Bridge-only Provider Output

Provider answer context, bridge hints, and deep products remain bridge-only.
They may be preserved as context on a sealed non-executable candidate, but the
consumed state records that bridge-only provider output cannot satisfy final
evidence or citation eligibility.

## No-live Boundary

This phase is offline only. It does not call providers, search engines, retrieval
dispatchers, fetch/read units, model prompts, arbitrary code execution, or live
dogfood. It does not connect sealed state to provider-job executors.

## Follow-on AG-96I2B

AG-96I2B adds the next bounded seam:
[AG96I2B_FOLLOWUP_FIXTURE_DISPATCH.md](AG96I2B_FOLLOWUP_FIXTURE_DISPATCH.md).
It consumes sealed non-executable AG-96I2A candidates through a fixture-only
execution gate and reduces sanitized fixture observations into canonical
RunKernel follow-up execution state. EvidenceLedger intake, real provider-job
dispatch, real budget/cost accounting, live validation, provider capability
evaluation, conversational Follow-up Turn Contract behavior, prior-answer reuse
policy, and any user-facing follow-up search implementation remain deferred.
