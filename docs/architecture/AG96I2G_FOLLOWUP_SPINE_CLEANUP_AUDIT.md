# AG-96I2G Follow-up Spine Cleanup Audit

## Status

AG-96I2G audits and cleans the fixture-only follow-up spine introduced by
AG-96I2A through AG-96I2F. It opens no new product behavior.

Current fixture chain:

```text
followup_authorization_state
-> followup_execution_state
-> followup_evidence_intake_state
-> EvidenceLedger projection
-> followup_sufficiency_recheck_state
-> sufficiency_judgment_projection
-> followup_final_answer_packet_state
-> final_answer_packet / final_answer_authority_projection
-> followup_author_gate_state
```

No live providers, search, retrieval, fetch/read, model calls, provider-job
executors, Author execution, citation rendering, product final-answer behavior,
or `core/pipeline_orchestrator.py` domain logic are opened.

## Owner and Consumer Map

| State or projection | Source-of-truth owner | Runtime consumer |
| --- | --- | --- |
| `followup_authorization_state` | `RunKernel.FollowupAuthorization` | `authorize_followup_fixture_execution` |
| `followup_execution_state` | `RunKernel.FollowupFixtureExecution` | `authorize_followup_evidence_intake` |
| `followup_evidence_intake_state` | `RunKernel.FollowupEvidenceIntake` | `authorize_followup_sufficiency_recheck` |
| EvidenceLedger projection | `RunKernel.EvidenceLedger` | sufficiency recheck and packet preparation |
| `followup_sufficiency_recheck_state` | `RunKernel.FollowupSufficiencyRecheck` | packet preparation |
| `sufficiency_judgment_projection` | `RunKernel.RunAuthoritySufficiencyJudgment` | packet preparation |
| `followup_final_answer_packet_state` | `RunKernel.FollowupFinalAnswerPacket` | Author gate authorization |
| `final_answer_packet` | `RunKernel.FinalAnswerPacket` | Author gate adapter |
| `final_answer_authority_projection` | `RunKernel.FinalAnswerPacket` | Author gate adapter |
| `followup_author_gate_state` | `RunKernel.FollowupAuthorGate` | fixture audit endpoint only |

Adapter records remain untrusted observations until RunKernel validates the
authorized binding and re-derives the canonical state.

## Consolidated or Deleted

- Added `core.followup_fixture_boundaries` for repeated fixture-only no-live,
  Author/citation/product-closed, provenance, and redaction helpers.
- Replaced duplicate local redaction/provenance builders in AG-96I2B through
  AG-96I2F runtime modules with the shared helper.
- Replaced repeated RunKernel follow-up closed-flag loops with local
  stage-specific tuples and one checker.
- Deleted duplicate local flag-list helper bodies where the shared tuples now
  express the same boundary.
- Added one end-to-end fixture spine test from Balanced authorization through
  Author gate.

No runtime state fields, public exports, adversarial tests, or phase documents
were deleted outright.

## Intentionally Left Alone

- Existing AG-96I2A through AG-96I2F focused tests remain because they cover
  useful spoofing, binding, source-class, bridge-only, digest, and closed-surface
  regressions.
- Fixture helper duplication inside older test files remains for readability and
  to avoid a broad test refactor during a safety audit phase.
- `core/pipeline_orchestrator.py` remains untouched.
- FinalAnswerPacket and Author gate projections retain their current explicit
  fields because later fixture or activation phases may need those references.

## Parked

RunKernel has accumulated a long follow-up reducer section. AG-96I2G only
centralizes repeated closed-flag validation. A later phase should consider:

```text
AG-96I2H: RunKernel follow-up reducer extraction / module split
```

That phase should be mechanical, preserve reducer semantics, and keep
RunKernel as the authority owner unless it explicitly relicenses ownership
movement.

## Next Recommended Phase

Do not open Author execution or product answer activation by implication.
Recommended next work is either the parked AG-96I2H reducer extraction, or a
separate fixture-only Author observation phase with explicit Author-execution,
prompt/prose, citation-rendering, and product-answer boundaries.
