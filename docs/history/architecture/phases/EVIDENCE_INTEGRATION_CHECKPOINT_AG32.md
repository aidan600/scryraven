Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (EVIDENCE_INTEGRATION_CHECKPOINT_AG32).

# AG-32 Evidence Integration Checkpoint

## Mode And Scope

AG-32 adds a shadow-only evidence-integration checkpoint at the post-retrieval
decision seam. It does not execute actions, call providers, route models, change
search depth, raise budget caps, tune legal sources, integrate social providers,
or alter Analyst/Economist/Author/Scrutineer handoffs.

## Runtime Shape

The intended future active shape is:

1. Router drafts a compact answer contract.
2. Retrieval/scout gathers evidence.
3. The orchestrator builds a sanitized `EvidenceIntegrationSnapshot`.
4. `decide_evidence_integration_checkpoint` recommends exactly one AG-25 action:
   `stop_sufficient`, `stop_insufficient_with_caveat`, `retrieve_targeted`,
   `recover_weak_corpus`, `recover_missing_source_class`, `resolve_conflict`,
   `ask_user_clarification`, `request_social_signal_check`, or
   `run_scrutineer_review`.
5. AG-32 records the result for parity only.
6. Existing orchestrator behavior continues unchanged.

The checkpoint is placed after the pre-recovery answer-contract handoff has
updated source-class recovery recommendation facts, after source-class lifecycle
decision construction, and before source-class recovery executor execution.

## Payload

`EvidenceIntegrationSnapshot` contains only compact facts:

- contract family, obligations, and required source classes
- fulfilled, partial, unfulfilled, and missing contract items
- evidence availability, sufficiency, reference count, and source-class presence
- weak-corpus state and whether recovery remains available
- source-class recovery recommendation, missing classes, and blockers
- material conflict state
- targeted-retrieval availability and redundancy
- social signal request/status as a side-packet placeholder only
- Scrutineer requested/needed plus mode and contract allow flags
- AG-31-shaped budget remaining fields and AG-27 budget/evidence-boundary labels

`EvidenceIntegrationDecision` returns one `action_name` only, plus reason,
contract gap addressed, expected value, budget rationale, and blocked/skipped
action rationale for non-selected actions.

## Consumers

The trace packet is consumed by parity assertions under
`evidence_integration_checkpoint_shadow`.

The final answer-contract fulfillment handoff can also carry a compact
`evidence_integration_checkpoint` reference. That reference is safe handoff
metadata only; it is not included in prompts and does not affect runtime control
flow.

## Promotion Or Deletion

Promote the payload when the next runtime-promotion phase makes this checkpoint
the active dispatcher gate after post-retrieval evidence integration.

Delete or collapse it if the next runtime-promotion phase does not consume the
checkpoint as an active gate or answer-contract handoff input.

## Protected Surfaces

AG-32 preserves these surfaces:

- provider routing and search-depth selection remain orchestrator-owned
- search-budget caps are not increased
- legal/current-primary recovery remains unchanged
- social signal remains a future side-packet placeholder only
- Scrutineer policy and handoff behavior are not changed
- raw prompts, provider payloads, DB rows, caches, private logs, and generated
  output packets are not read or emitted by the checkpoint
