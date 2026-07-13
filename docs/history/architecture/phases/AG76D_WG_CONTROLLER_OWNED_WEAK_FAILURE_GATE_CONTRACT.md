Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG76D_WG_CONTROLLER_OWNED_WEAK_FAILURE_GATE_CONTRACT).

# AG-76D-WG Controller-Owned Weak / Off-topic / Failure-card Gate Contract

Date: 2026-05-31

Phase type: **core authority transfer**

Mode: Architecture Groove / Prove Mode

## Licensed Protected Surface

AG-76D-WG opens only the Controller-owned weak/off-topic/failure-card gate
contract/state seam, the already-computed weak/off-topic/failure-card gate facts,
the mechanical executor/handoff for those facts, additive trace/controller
visibility, and minimal `core/pipeline_orchestrator.py` adapter changes.

It does **not** repair weak-corpus, off-topic, no-good-evidence, failure-card,
Analyst, Author, final-answer, citation, prompt, provider/search, retrieval,
source-class, Economist, Scrutineer, follow-up, DB/session, or `RunOutcome`
behavior.

## Previously Local / Orchestrator-owned Decisions

Before this phase, `pipeline_orchestrator.py` and local helpers retained scoped
weak/failure gate authority at these seams:

- corpus posture was classified in the orchestrator by calling
  `classify_corpus_state(...)`, then forced by the orchestrator when
  `forced_corpus_state` was configured;
- weak corpus posture was derived by `is_weak_corpus_state(...)` in the
  orchestrator;
- weak-corpus recovery considered/used/skip/queries/decision/reason/blockers
  were copied into trace and downstream handoff by the orchestrator after the
  weak-corpus controller decision;
- pre-Analyst off-topic / weak / failure-card admission posture was decided by
  the local `_pre_analyst_retrieval_gate(...)` helper and immediately consumed by
  the orchestrator;
- failure-card `show`, `reason`, and payload shape were assembled in the
  orchestrator from `failure_card_should_show(...)` and
  `failure_card_reason(...)`;
- useful-content, `response_displayable`, `evidence_sufficient`, and
  `answer_class` were computed locally and then passed onward by the
  orchestrator;
- trace visibility for these facts was broad legacy field emission, not a named
  Controller-owned weak/failure gate state.

## New Controller-owned Contract / State

AG-76D-WG adds `core.weak_failure_gate_contract` with:

- `WEAK_FAILURE_GATE_SCHEMA_VERSION` and `WEAK_FAILURE_GATE_TRACE_KEY`;
- `AnalystGateDescriptor` for already-computed Analyst skip/admission posture;
- `FailureCardGateDescriptor` for already-computed failure-card show/reason and
  payload facts;
- `WeakFailureGateState` for Controller-owned weak/off-topic/failure-card gate
  state;
- `WeakFailureGateExecutionEnvelope` for legacy-output handoff;
- `build_analyst_gate_descriptor(...)`;
- `build_failure_card_gate_descriptor(...)`;
- `build_weak_failure_gate_state(...)`;
- `execute_weak_failure_gate_handoff(...)`.

The contract is passive and deterministic. It copies, normalizes, references,
and exposes already-computed gate facts. It does not call providers, models,
search, prompts, Analyst, Author, citation, final-answer, Economist,
Scrutineer, follow-up, DB/session persistence, `RunOutcome`, caches, or live
validation surfaces.

## Mechanical Executor / Handoff Boundary

`execute_weak_failure_gate_handoff(...)` is the mechanical handoff. It returns
legacy-compatible values from `WeakFailureGateState`:

- failure-card payload;
- useful-content and useful-content reason;
- `response_displayable`, `evidence_sufficient`, and `answer_class`;
- Analyst skip reason, fast-path posture, and pre-Analyst gate signals.

The handoff does not decide gate posture. It contains no calls to
`failure_card_should_show(...)`, `failure_card_reason(...)`,
`evaluate_useful_content(...)`, or `classify_answer_outcome(...)`.

## Relationship to RetrievalLoopState

When a `RetrievalLoopState` is available, the weak/failure gate contract stores a
`retrieval_loop_ref` by calling its `to_controller_state()` method. This is an
opaque upstream reference for Controller visibility only. The weak/failure gate
contract does not change retrieval-loop provider selection, depth, query order,
pass execution, pass summaries, or stop/continue behavior.

## Relationship to RetrievalStopDecision

`RetrievalStopDecision` remains the stop/continue authority. AG-76D-WG can store
an optional `retrieval_stop_decision_ref` if supplied, but it does not
reimplement stop/continue decisions, redundancy checks, budget checks,
sufficiency checks, or weak-corpus recovery completion checks.

## Relationship to RouterQueryPreparationState

When `RouterQueryPreparationState` is available, the weak/failure gate contract
stores a `router_query_preparation_ref` by calling its `to_controller_state()`
method. This is an upstream reference only. Router/query-preparation authority
remains owned by AG-76D-RQ.

## Behavior Preserved

AG-76D-WG preserves:

- corpus-state classification and forced corpus-state semantics;
- `corpus_weak` semantics;
- weak-corpus recovery considered/used/skip/queries/decision/reason/blockers;
- off-topic / no-good-evidence / displayability posture;
- failure-card show/reason/payload shape;
- useful-content and answer-outcome classification;
- Analyst skip/admission behavior and unsupported-retrieval directive text;
- Author/final-answer/citation behavior and handoff facts;
- existing trace fields, JSONL/session/SQLite payloads, DB/session behavior, and
  `RunOutcome` shape;
- provider/model/search/query/retrieval behavior;
- package/CLI/env/database compatibility names.

Runtime behavior changes are expected to be none except authority ownership and
additive trace/controller visibility.

## Production-active vs Shadow-only Paths

Production-active:

- `AnalystGateDescriptor` wraps the already-computed pre-Analyst and
  post-Economist gate posture before the orchestrator consumes it;
- `WeakFailureGateState` wraps final weak/off-topic/failure-card,
  useful-content, and answer-outcome facts before the orchestrator persists or
  returns them;
- `execute_weak_failure_gate_handoff(...)` mechanically returns the existing
  legacy outputs;
- `weak_failure_gate_contract` trace is added to execution trace as additive
  Controller visibility.

Shadow-only: none introduced for AG-76D-WG.

Test-only:

- offline parity/static tests in
  `tests/test_ag76d_wg_controller_owned_weak_failure_gate_contract.py`.

Inactive replacement infrastructure: none.

## Tests Added / Updated

Added `tests/test_ag76d_wg_controller_owned_weak_failure_gate_contract.py`,
covering:

1. Controller ownership and descriptor visibility.
2. Weak-corpus parity fields.
3. Off-topic / no-good-evidence / displayability parity.
4. Failure-card show/reason/payload parity.
5. Useful-content / answer-outcome parity.
6. Analyst/Author/final-answer/citation non-change static guard.
7. Mechanical executor/handoff behavior.
8. Orchestrator authority guard for the moved seam.
9. RetrievalLoopState reference integration.
10. Trace compatibility and additive visibility.
11. Protected-surface and no-live/product-path guards.

## Trace Compatibility and Additive Visibility

Existing weak/off-topic/failure-card trace fields remain present, including
`corpus_state`, `corpus_state_forced`, `corpus_weak`, `useful_content`,
`useful_content_reason`, `response_displayable`, `evidence_sufficient`,
`answer_class`, weak-corpus recovery fields, Analyst skip fields, and
`failure_card`.

AG-76D-WG adds one sanitized trace packet: `weak_failure_gate_contract`. It
contains Controller-owned descriptors, copied legacy facts, upstream references,
and explicit booleans proving the contract did not change Analyst, Author,
citation, final-answer, prompt, provider/search, or DB/RunOutcome behavior.

The packet is additive and does not include secrets, `.env`, DB rows, raw
prompts, raw provider payloads, local output packets, caches, or live-run data.

## Analyst / Author / Final-answer / Citation Non-change Note

Analyst skip/admission posture is copied into `AnalystGateDescriptor` after the
existing pre-Analyst and post-Economist gate facts are computed. The existing
unsupported-retrieval directive, Author notes, Author system prompt key,
final-answer source telemetry, citation telemetry, and final report generation
paths remain unchanged.

## Protected Surfaces Kept Closed

Kept closed:

- Analyst behavior changes;
- Author behavior changes;
- final-answer behavior changes;
- citation formatting/selection changes;
- prompt text changes;
- provider routing/selection/depth changes;
- query generation/finalization changes;
- retrieval ranking/filtering changes;
- source-class classifier/currentness and candidate-fit semantics;
- Economist, Scrutineer, and follow-up behavior;
- DB/session/SQLite/`RunOutcome` shape changes;
- package/CLI/env/session/database compatibility renames;
- LLM workflow cache implementation;
- live validation and provider/model/search calls.

## Stop Conditions

Stop instead of continuing if parity would require changing Analyst, Author,
final-answer, citation, prompt/model-call, provider/search/query/retrieval,
source-class, DB/session/SQLite/`RunOutcome`, weak-corpus/failure-card behavior,
live validation, LLM caching, compatibility names, or a broad rewrite beyond the
named weak/failure gate contract/handoff.

## Recommended Next Phase

Recommended next core authority transfer:

`AG-76D-AA — Controller-Owned Analyst / Author Handoff Contract`.

Rationale: after Router/query-preparation, retrieval stop/continue,
retrieval-loop posture, and weak/off-topic/failure-card gate authority have named
Controller-owned contracts, the next high-risk local authority seam is the
Analyst/Author handoff: analysis admission, Author-facing notes, and final-answer
handoff inputs remain large orchestrator-local surfaces. Citation/source-list
handoff (`AG-76D-CIT`) remains a viable later phase, but AA is the more direct
successor because WG explicitly preserved and now references Analyst/Author
handoff posture without owning it.
