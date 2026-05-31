# AG-76D-AA Controller-Owned Analyst / Author Handoff Contract

Date: 2026-05-31

Phase type: **core authority transfer**

Mode: Architecture Groove / Prove Mode

## Licensed Protected Surface

AG-76D-AA opens only the Controller-owned Analyst/Author handoff contract/state
seam, already-computed Analyst admission/skip facts, Analyst evidence/context
package identity, unsupported/weak/failure-card directive posture, Author
evidence handoff identity, Author prompt input metadata, Controller /
AnswerContract posture visibility, selected/final evidence visibility, additive
trace/controller visibility, and minimal `core/pipeline_orchestrator.py` adapter
changes.

It does **not** repair Analyst behavior, Author behavior, final-answer prose,
citation formatting/selection, prompt text, provider/model/search/query
behavior, retrieval behavior, source-class/currentness/candidate-fit semantics,
Economist behavior, Scrutineer behavior, follow-up behavior, DB/session/SQLite
or `RunOutcome` shape, compatibility package/CLI/env/database names, live
validation, or LLM workflow caching.

## Previously Local / Orchestrator-owned Handoff State

Before this phase, `pipeline_orchestrator.py` and local helpers retained scoped
Analyst/Author handoff authority at these seams:

- Analyst run/skip posture was consumed from the pre-Analyst gate locally and
  immediately used to choose either the unsupported-retrieval directive, direct
  Author handoff, estimate-from-priors Analyst pass, or normal Analyst pass.
- Analyst evidence/context package identity was assembled by local closures that
  sliced `final_top_evidence`, built the Analyst cached prefix, and measured the
  context package.
- Unsupported retrieval directive state and related Author notes were assembled
  inline when the pre-Analyst gate skipped Analyst.
- Weak evidence / failure-card posture was visible through local `corpus_weak`
  and failure-card variables before and after AG-76D-WG, but the Analyst/Author
  handoff did not have a named Controller-owned package for that posture.
- Author precision evidence, ordered sources, Author prompt metadata, Author
  system prompt key, and Author effort were assembled and consumed inline.
- Final/selected evidence identity, source telemetry references, and
  AnswerContract/runtime posture entered Analyst/Author handoffs as local
  variables rather than a single Controller-owned handoff state.

## New Controller-owned Analyst/Author Handoff Contract

AG-76D-AA adds `core.analyst_author_handoff_contract` with these passive
Controller-owned dataclasses:

- `AnalystAuthorHandoffState`
- `AnalystAdmissionDescriptor`
- `AnalystEvidenceContextDescriptor`
- `UnsupportedDirectiveDescriptor`
- `AuthorEvidenceHandoffDescriptor`
- `AuthorPromptInputDescriptor`
- `AnalystAuthorExecutionEnvelope`

The builder `build_analyst_author_handoff_state(...)` consumes facts the runtime
has already computed and copies their identities into a deterministic state. The
executor `execute_analyst_author_handoff(...)` mechanically returns the legacy
Analyst admission and Author prompt-key/effort values for the orchestrator.

The contract stores hashes/lengths for prompt/context blocks where identity is
needed, but it does not import prompt modules or own prompt text.

## Mechanical Executor / Handoff Boundary

Production-active:

- `pipeline_orchestrator.py` builds `AnalystAuthorHandoffState` after the legacy
  Author prompt metadata is assembled and consumes `AnalystAuthorExecutionEnvelope`
  for the already-computed Author system prompt key and Author effort.
- After final source telemetry, AnswerContract/runtime handoff, and
  `WeakFailureGateState` are available, the orchestrator rebuilds the same
  Controller-owned state with richer upstream references and emits the additive
  `analyst_author_handoff_contract` trace packet.

The executor boundary remains mechanical. Model calls, prompt strings,
retrieval, final answer generation, citation behavior, source list generation,
DB/session persistence, and `RunOutcome` packaging stay in their pre-existing
paths.

Shadow-only: none introduced.

Test-only:

- Offline parity/static tests in
  `tests/test_ag76d_aa_controller_owned_analyst_author_handoff_contract.py`.

Inactive replacement infrastructure: none.

## Relationship to WeakFailureGateState

When `WeakFailureGateState` is available, `AnalystAuthorHandoffState` stores a
`weak_failure_gate_ref` by calling `to_controller_state()`. The Analyst/Author
handoff contract also records unsupported, weak-evidence, and failure-card
directive posture as already-computed facts. It does not reclassify weak corpus,
change failure-card show/reason/payload behavior, or change AG-76D-WG authority.

## Relationship to RetrievalLoopState

When `RetrievalLoopState` is available, the contract stores a
`retrieval_loop_ref` by calling `to_controller_state()`. This is an upstream
visibility reference only. The contract does not choose queries, providers,
search depth, retrieval budgets, retrieval pass stop/continue posture, ranking,
filtering, or recovery behavior.

## Relationship to RouterQueryPreparationState

When `RouterQueryPreparationState` is available, the contract stores a
`router_query_preparation_ref` by calling `to_controller_state()`. Router/query
preparation authority remains owned by AG-76D-RQ; AG-76D-AA only exposes that
posture at the Analyst/Author handoff seam.

## Relationship to AnswerContract / Runtime Handoff

When runtime AnswerContract handoff facts are available, AG-76D-AA stores an
opaque `answer_contract_ref` for Controller visibility. The contract does not
change AnswerContract source obligations, evidence sufficiency, fulfillment
state, final evidence selection, final-answer posture, or downstream persistence.

## Behavior Preserved

AG-76D-AA preserves:

- Analyst run/skip behavior and skip reason;
- Analyst evidence/context package ordering and identity;
- unsupported retrieval directive behavior and Author-note inclusion;
- weak evidence and failure-card directive posture;
- Author precision evidence handoff identity;
- selected/final evidence identity and source telemetry references;
- Author prompt input metadata, Author system prompt key, and Author effort;
- existing prompt text and prompt source references;
- final-answer prose and citation/source-list behavior;
- existing trace fields, with only additive `analyst_author_handoff_contract`
  visibility;
- provider/model/search/query/retrieval behavior;
- DB/session/SQLite/`RunOutcome` shape;
- compatibility package/CLI/env/session/database names.

Runtime behavior changes are expected to be none except authority ownership and
additive trace/controller visibility.

## Trace Compatibility and Additive Visibility

Existing trace fields remain present, including Analyst skip fields,
pre-Analyst gate signals, Author system prompt key, final answer source
telemetry, failure-card payload, weak/failure gate trace, AnswerContract runtime
trace, context measurement, and final evidence snapshot attachments.

AG-76D-AA adds one sanitized trace packet: `analyst_author_handoff_contract`. It
contains Controller-owned descriptors, copied legacy handoff facts, upstream
references, evidence identity, hashes/lengths for prompt/context packages, and
explicit booleans proving the contract did not change Analyst, Author,
final-answer, citation, prompt text, provider/search/query, DB/session/RunOutcome,
or cache behavior.

The packet is additive and does not include secrets, `.env`, DB rows, raw
provider payloads, local output packets, caches, or live-run data. Prompt text is
not included in the contract trace.

## Prompt Text Non-change Note

Prompt text remains in `pipeline_orchestrator.py` and existing prompt sources.
The new contract does not import `core.prompts`, `DEFAULT_SYSTEM`, or any prompt
behavior module. It records Author prompt and Analyst context package identity
with hashes/lengths only and does not construct or modify prompt strings.

## Final-answer / Citation Non-change Note

Final-answer generation, final-answer prose, citation formatting/selection,
source-list behavior, final source telemetry scanners, and citation/source-list
input assembly are not opened by this phase. The contract records identity and
counts for ordered sources, selected evidence, final evidence, and source
telemetry references only.

## Protected Surfaces Kept Closed

Kept closed:

- Analyst behavior changes;
- Author behavior changes;
- final-answer behavior changes;
- citation formatting/selection changes;
- prompt text changes;
- provider/model/search/query behavior changes;
- retrieval ranking/filtering/source-class/currentness/candidate-fit changes;
- Economist, Scrutineer, and follow-up behavior;
- DB/session/SQLite/`RunOutcome` shape changes;
- package/CLI/env/session/database compatibility renames;
- LLM workflow cache implementation;
- live validation and provider/model/search calls.

## Stop Conditions

Stop instead of continuing if parity would require changing Analyst behavior,
Author behavior, final-answer prose, citation formatting/selection, prompt text
or model-call behavior, provider/search/query/retrieval behavior, source-class
classifier/currentness or candidate-fit semantics, Economist/Scrutineer/follow-up
behavior, DB/session/SQLite/`RunOutcome` shape, live validation, LLM caching,
compatibility names, or a broad rewrite beyond the named Analyst/Author handoff
contract.

## Tests Added / Updated

Added `tests/test_ag76d_aa_controller_owned_analyst_author_handoff_contract.py`,
covering:

1. Controller ownership, schema, and additive trace visibility.
2. Analyst run/skip parity and skip-reason parity.
3. Analyst evidence/context package identity, ordering, and metadata parity.
4. Unsupported retrieval, weak evidence, and failure-card directive parity.
5. Author evidence handoff, selected/final evidence identity, and source
   telemetry reference parity.
6. Author prompt input metadata parity without prompt text.
7. Prompt text non-change/static prompt-source guard.
8. Trace compatibility and additive behavior flags.
9. Static protected-import guard.
10. Orchestrator authority guard for the moved seam.
11. Protected-surface/no-live/product-path guards.
12. Upstream contract integration with `WeakFailureGateState`,
    `RetrievalLoopState`, `RouterQueryPreparationState`, and runtime
    AnswerContract references.

## Recommended Next Phase

Recommended next core authority transfer:

`AG-76D-CIT — Controller-Owned Citation / Source-list Handoff Contract`.

Rationale: after AG-76D-AA, the remaining high-risk core handoff seam is the
citation/source-list handoff where selected evidence, final evidence, source
telemetry, ordered sources, and answer text meet citation/source-list behavior.
That phase should own identity/handoff posture without changing citation
formatting or final-answer prose.
