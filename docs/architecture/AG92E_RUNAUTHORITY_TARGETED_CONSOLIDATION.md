# AG-92E RunAuthority Targeted Consolidation

Status: implemented as a behavior-preserving consolidation pass
Validation boundary: offline static and focused authority tests
Live validation: not run
Provider/model/search calls: not run

## What moved

AG-92E extracts orchestration-local fact assembly from
`core/pipeline_orchestrator.py` into bounded adapters and lifecycle helpers:

- `core/run_authority_search_judgment_adapter.py`
  builds `RunSearchJudgmentInput` from compact runtime facts.
- `core/run_authority_sufficiency_adapter.py`
  builds `RunSufficiencyJudgmentInput` from compact finalization facts.
- `core/evidence_ledger_lifecycle.py`
  wraps repeated EvidenceLedger authorize/execute/reduce/projection callsites.
- `core/run_authority_projection_refs.py`
  centralizes canonical RunAuthority SearchJudgment and SufficiencyJudgment
  projection checks and compact refs.

The orchestrator still coordinates lifecycle order: build input, authorize,
execute bounded runtime action, reduce observation, and pass the reduced
projection to the next consumer.

## Behavior intentionally preserved

No runtime behavior change is intended. The extracted builders preserve the same
payload fields that the orchestrator previously assembled inline:

- contract and EvidenceLedger projections;
- retrieval observations, helper proposals, and budget facts for SearchJudgment;
- SearchJudgment projection/history, AnswerContract compatibility facts, final
  evidence facts, conflict facts, weak/failure facts, and budget facts for
  SufficiencyJudgment;
- EvidenceLedger reductions from contract requirements, pre-recovery runtime
  facts, final evidence, and post-final source-obligation facts.

The phase does not change provider routing, retrieval behavior, query ordering,
Author prose style, citation formatting, prompt content, smart-model defaults,
or live validation posture.

## Compatibility debt left in place

This phase does not delete source-class recovery lifecycle, retrieval
stop/continue, AnswerContract compatibility facts, legacy final packet fallbacks,
weak/failure/conflict/inference fact sources, or post-author/session projection
compatibility surfaces. Those paths remain active because they still protect
existing runtime lanes and require focused tests before deletion or demotion.

## Roadmap v10 input

Roadmap v10 should treat the RunAuthority chain as active and runtime-consumed,
with AG-92E reducing orchestration bulk rather than changing authority semantics.
Remaining consolidation debt is now clearer: source-class recovery dispatch
permission, retrieval stop/continue authority, AnswerContract final-readiness
fallbacks, and weak/failure/conflict/inference posture inputs still need focused
cleanup phases or explicit retirement criteria.

## Why not delete legacy fallbacks yet

Source-class recovery and retrieval continuation still execute through legacy
compatibility surfaces. FinalAnswerPacket consumes canonical SufficiencyJudgment
when present, but legacy packet fallbacks remain compatibility lanes for callers
that do not yet provide a canonical sufficiency projection. Deleting those paths
would require broader lane coverage and behavior validation than AG-92E licenses.
