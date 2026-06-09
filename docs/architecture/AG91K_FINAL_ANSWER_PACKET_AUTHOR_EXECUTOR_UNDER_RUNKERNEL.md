# AG-91K FinalAnswerPacket / Author Executor Under RunKernel

Status: implementation note; high-custody authority migration; no live validation

## Purpose

AG-91K moves the decisive final-answer and Author execution seam under
RunKernel authority. The orchestrator still coordinates surrounding lifecycle
work, but it no longer owns the Author model call, Author provider/model/effort
selection, or the final packet readiness handoff.

Target doctrine:

- RunKernel owns final answer readiness and Author execution authorization.
- EvidenceLedger owns evidence/source custody.
- FinalAnswerPacket owns citation eligibility, missing obligations, mandatory
  caveats, prohibited upgrades, final posture, and packet-derived Author input.
- The Author executor writes prose from a packet-derived payload and does not
  decide source sufficiency, citation eligibility, final evidence eligibility,
  missing obligations, or final posture.
- Trace/export derives from RunState where migrated state exists.

## Old Authority Owners

Before AG-91K, `core/pipeline_orchestrator.py` still owned the decisive Author
runtime seam after AG-90B extraction:

- Author system prompt selection via `select_author_system_prompt`;
- Author effort selection;
- Author provider/model selection;
- final packet helper invocation as local pre-Author plumbing;
- streaming `ask_model(author_prompt, _author_system, ...)`;
- stream accumulation and display buffering;
- post-Author quantitative consistency guard invocation;
- final-answer packet trace and citation/source compatibility handoff inputs
  flowing from local packet variables.

The AG-76D Analyst/Author handoff also still returned Author key/effort values
into local variables after packet preparation, which left a compatibility handoff
able to overwrite packet-derived Author settings.

## New RunKernel Model

`core.run_kernel` now adds:

- `FINAL_ANSWER_PACKET_STAGE`;
- `AUTHOR_EXECUTION_STAGE`;
- `ActionType.FINAL_ANSWER_PACKET_PREPARE`;
- `ActionType.AUTHOR_EXECUTE`;
- `ObservationType.FINAL_ANSWER_PACKET_PREPARED`;
- `ObservationType.AUTHOR_OUTPUT_OBSERVED`;
- `RunState.final_answer_packet`;
- `RunState.author_observation`;
- `RunState.final_answer_outcome`;
- `RunState.final_answer_authority_projection`.

Reducer semantics:

- reducing `FINAL_ANSWER_PACKET_PREPARED` stores the packet projection and
  packet-derived Author payload reference in canonical RunState;
- `authorize_author_execution(...)` refuses to issue an Author action until a
  packet-ready payload has been reduced;
- reducing `AUTHOR_OUTPUT_OBSERVED` stores compact output telemetry and hashes in
  RunState without storing raw prompt text or raw model response text.

Trace projection now exposes final-answer packet state, Author observation, final
answer outcome, and final-answer authority projection from RunState.

## Bounded Executors

`core.final_answer_packet_runtime` validates the RunKernel packet-preparation
action, chooses the legacy-equivalent Author system key, effort, provider, and
model, builds the existing `FinalAnswerPacket`, derives the Author input payload,
and returns a sanitized observation. It does not call models, providers, search,
retrieval, persistence, or citation formatting.

`core.author_execution_runtime` validates the RunKernel Author action, checks
the packet-derived payload aligns with the authorized action, resolves the
system prompt by packet key, calls `ask_model` with the packet prompt/provider/
model/effort, preserves existing stream-display buffering semantics, applies the
existing quantitative consistency guard, and returns final prose plus compact
telemetry. It does not decide source sufficiency, citation eligibility, missing
obligations, final evidence eligibility, or final posture.

## FinalAnswerPacket Changes

`FinalAnswerPacket` now records:

- `readiness_status`;
- `readiness_reasons`;
- packet-derived Author provider/model in `FinalAnswerAuthorInputPayload`.

Readiness is `author_ready` for supported packet state and
`insufficient_authorized` when missing evidence, weak/failure posture,
synthesis insufficiency, or missing/unsatisfied source obligations are explicitly
packet-visible. `blocked` packets cannot produce Author input.

The packet builder now also accepts AnswerContract-like source obligation
projection when available and preserves those missing obligations as mandatory
caveats. EvidenceLedger projection remains the preferred custody source when
available, including ledger candidate/requirement/gap counts and the prohibited
upgrade for uncustodied final evidence.

## Runtime Consumers

`pipeline_orchestrator.py` now:

- authorizes packet preparation through RunKernel;
- calls `execute_final_answer_packet_prepare_action_from_scope(...)`;
- reduces the packet observation;
- authorizes Author execution only after packet readiness;
- calls `execute_author_action(...)`;
- reduces the Author observation;
- keeps the AG-76D post-Analyst handoff as compatibility metadata without
  overwriting packet-derived Author settings.

`core.post_author_output_projection` validates the local packet against
RunKernel final-answer state when available and passes a
`run_kernel_final_answer_ref` into packet-derived citation/source handoff
assembly.

`core.session_output_projection` prefers `RunState.final_answer_packet` for the
`final_answer_packet` trace fragment when RunKernel state exists. The old local
packet fragment remains a compatibility fallback only.

## Compatibility-Only Surfaces

The following remain compatibility/projection surfaces:

- AG-76D Analyst/Author handoff prompt/input metadata;
- AG-76D citation/source handoff shape;
- local `final_answer_packet` object passed through post-Author projection for
  object methods, guarded against RunKernel packet-id divergence;
- legacy source telemetry fields and session/output compatibility keys.

These surfaces are downstream of packet state for AG-91K and do not authorize
the Author call.

## Protected Surfaces

Opened by AG-91K:

- FinalAnswerPacket readiness and Author payload schema;
- Author-facing packet authority block payload;
- Author prompt/payload execution boundary;
- Author system key, effort, provider/model authority boundary;
- post-Author quantitative guard placement;
- final packet trace/projection derivation;
- static guards around the old orchestrator-owned Author call.

Kept closed:

- live provider/model/search calls;
- broad provider/search/retrieval/query strategy changes;
- retrieval ranking/filtering changes;
- hosted/cache/deployment behavior;
- secrets, `.env`, raw provider payloads, raw prompts, DB rows, private logs,
  caches, full raw traces, local output packets, and private artifacts;
- broad final answer style/prose rewrite.

## Remaining Work

AG-92A should move more prompt and contract synthesis into accountable
RunAuthority state so AnswerContract can feed FinalAnswerPacket earlier and more
directly. AG-92B can then move iterative search judgment under RunAuthority.
AG-92C or a focused follow-up can retire more compatibility-only citation/source
and Analyst/Author handoff projections once all consumers read canonical
RunState directly.
