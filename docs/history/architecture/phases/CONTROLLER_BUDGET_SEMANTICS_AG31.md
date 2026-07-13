Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (CONTROLLER_BUDGET_SEMANTICS_AG31).

# AG-31 Controller Budget Semantics And Marginal-Value Action Gate

Status: M4 / AG-31 architecture contract. Classification: pure/offline
controller budget semantics layer.

## Goal

AG-31 adds `core/controller_budget_semantics.py`, a pure offline gate that
separates mode-owned hard caps from controller-owned marginal-value allocation
decisions. It answers one passive question:

Should the controller recommend spending one more bounded AG-25 action, skipping
because the action is redundant or low value, stopping sufficient, stopping
insufficient with a caveat, or reserving the action for a more central missing
obligation?

The gate does not execute retrieval, call providers, alter prompts, persist
data, choose routing, tune depth, or change runtime search behavior.

## Budget Model

`ControllerBudgetState` serializes as `controller_budget_state_ag31_v1` and
contains:

- `ControllerBudgetHardCaps`: mode, max iterations, max queries, results per
  query, top chunks, search depth, live-call cap, provider routing boundary, and
  depth routing boundary;
- `ControllerBudgetSpent`: already-spent retrieval iterations, targeted
  retrieval actions, weak-corpus attempts, source-class attempts,
  conflict-resolution actions, social side-packet requests, and live calls;
- `ControllerBudgetAllowance`: controller reserves for retrieval actions,
  targeted retrieval, weak-corpus recovery, source-class recovery,
  conflict-resolution, clarification, social side-packet placeholder, and
  live-call placeholder;
- derived `ControllerBudgetRemaining` fields for hard-cap remaining and each
  bounded reserve;
- answer-contract and evidence-state facts used for marginal-value reasoning.

Hard caps are built from `core.mode_policy.ModePolicy` through
`ControllerBudgetHardCaps.from_mode_policy()`. AG-31 mirrors those caps; it does
not modify them.

## Marginal-Value Criteria

`MarginalValueDecision` records:

- proposed AG-25 action;
- contract family and obligation;
- missing contract items;
- centrality;
- evidence gap severity;
- redundancy risk;
- conflict risk;
- expected value;
- cost tier;
- remaining allowance;
- approved/skipped/blocked status;
- rationale;
- stop reason when not spending.

More search is approved only when a specific contract/evidence obligation is
central, evidence gap severity is material, expected value is material, the
action has bounded reserve, and redundancy risk is not high. The gate rejects
generic "weak answer" spending.

## Supported Actions

AG-31 supports these AG-25 action names:

- `retrieve_targeted`;
- `recover_missing_source_class`;
- `recover_weak_corpus`;
- `resolve_conflict`;
- `stop_sufficient`;
- `stop_insufficient_with_caveat`;
- `ask_user_clarification`;
- `request_social_signal_check`.

The gate does not define a competing action vocabulary. Tests prove every
supported action is registered by AG-25.

## AG-27 Alignment

The gate imports AG-27 budget descriptors and returns the AG-27 budget class
names:

- `retrieval_iteration_budget`;
- `weak_corpus_recovery_budget`;
- `source_class_recovery_budget`;
- `answer_contract_recovery_action_budget`;
- `social_side_packet_budget_placeholder`;
- `live_call_budget_placeholder`.

These remain descriptor/alignment fields. AG-31 does not claim runtime budget
ownership and does not allocate live calls.

## Protected Boundaries

Provider routing and depth remain protected boundaries:

- `provider_routing_boundary=orchestrator_owned`;
- `depth_routing_boundary=mode_or_orchestrator_owned`.

`request_social_signal_check` remains future/side-packet only. It cannot satisfy
factual, official, legal, current-primary, primary, or ordinary evidence gaps.
It does not allocate provider budget or live-call budget.

Weak-corpus recovery remains bounded by a one-action reserve in the offline
state. Once the reserve or mode iteration hard cap is exhausted, the gate blocks
another weak-corpus spend instead of creating a side loop.

## Fixture Coverage

Focused AG-31 tests cover:

1. Balanced simple question stops after sufficient evidence.
2. Balanced official/current/legal gap approves one bounded source-class
   recovery action.
3. Balanced redundant-query case skips spending.
4. Deep conflicting-evidence case approves a conflict-resolution action.
5. Exhausted-budget case blocks spending and allows insufficient stop with
   caveat.
6. Weak-corpus recovery remains bounded.
7. Social signal remains side-packet only and cannot satisfy legal/official
   evidence.
8. Fast mode has no search reserve but can approve safe clarification.
9. AG-25 action-name compatibility and AG-27 budget descriptor alignment.
10. Static import guard against providers, prompts, persistence, orchestrator,
    live calls, raw logs, and caches.

## What Did Not Change

AG-31 does not:

- change `mode_policy.py` caps;
- change `pipeline_orchestrator.py`;
- call providers, models, prompts, retrieval, routing, caches, DBs, logs, or
  persistence;
- read secrets, raw logs, raw prompts, raw provider payloads, generated output
  packets, caches, or DB rows;
- change provider routing, provider selection, search depth, source ranking, or
  filtering;
- change weak-corpus, source-class, retrieval-stop, answer-contract, Analyst,
  Economist, Author, or Scrutineer runtime behavior;
- wire social signal into runtime.

## Remaining Before Runtime Promotion

Future phases can use this passive gate as review material for runtime
promotion, but still need:

1. parity fixtures proving the gate's recommendations match current runtime
   timing before any authority moves;
2. an explicit runtime owner for retrieval continuation budget;
3. a decision on whether weak-corpus timing remains orchestrator-owned or moves
   behind a standalone executor;
4. a live-call policy separate from AG-31;
5. social provider/API policy behind side-packet boundaries;
6. official/legal diagnostics before provider, depth, domain, ranking, prompt,
   or legal-source tuning.

## Bottom Line

AG-31 gives the controller a pure/offline way to explain why one more bounded
action is worth spending, why it should be skipped, or why the answer should
stop with sufficient evidence or an explicit caveat. Runtime search behavior
remains unchanged.
