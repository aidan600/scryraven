Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I3N_FOLLOWUP_SUFFICIENCY_RECHECK_AFTER_M2_INTAKE).

# AG-96I3N Follow-Up Sufficiency Recheck After M2 Intake

## Status

AG-96I3N opens one bounded runtime consumer after AG-96I3M2:

```text
AG-96I3M2 follow-up EvidenceLedger intake state
+ canonical EvidenceLedger projection
-> existing RunKernel-governed follow-up Sufficiency recheck lane
-> RunKernel.FollowupSufficiencyRecheck state/projection
```

The activation is an allowlist and validation extension only. It does not create
a new Sufficiency owner or a new recheck lane.

## Runtime Boundary

The existing `RunKernel.authorize_followup_sufficiency_recheck` action now
accepts `ag96i3m2_admission_review_followup_intake` when the intake state is
canonical, runtime EvidenceLedger intake occurred, downstream final-answer and
Author surfaces remain closed, and the EvidenceLedger projection digest binds
the authorized action to the canonical ledger projection.

The recheck runtime still rebuilds the canonical recheck record during
RunKernel reduction. Mutated action/observation bindings or stale
EvidenceLedger projection digests are rejected before canonical state changes.

## Preserved Summaries

For AG-96I3M2 intake, the recheck state/projection carries only bounded,
sanitized summaries already present in the intake state:

- `ag96i3m2_admission_review_candidate`
- `ag96i3m2_evidence_ledger_intake_binding`
- `evidence_ledger_observation_id`
- EvidenceLedger counts
- source requirement statuses
- custody gap summaries
- official/current custody status

Raw provider payloads, raw prompts, raw page text, traces, private logs, caches,
DB rows, and secrets remain out of scope.

## Closed Surfaces Preserved

AG-96I3N does not change provider routing, provider selection, provider depth,
query generation, query ordering, retrieval ranking/filtering, SearchWorkPlan,
QueryPlan, citation behavior, FinalAnswerPacket preparation, Author behavior,
prompts, live provider/search/model/fetch/read behavior, or
`core/pipeline_orchestrator.py` domain logic.

The phase keeps:

```text
final_answer_packet_deferred=true
author_activation_allowed=false
citation_eligible=false
citation_behavior_changed=false
product_answer_behavior_changed=false
live_validation_not_run=true
```
