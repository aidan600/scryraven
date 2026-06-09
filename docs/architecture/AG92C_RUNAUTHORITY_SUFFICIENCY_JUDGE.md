# AG-92C RunAuthority Sufficiency Judge

Status: implemented as RunAuthority behavior activation; no live validation

## Purpose

AG-92C activates a canonical final sufficiency judgment before
FinalAnswerPacket preparation. The judgment decides whether the active
RunAuthority contract has been fulfilled enough for final answering, whether an
answer must be partial or caveated, whether source-bound numeric values remain
unknown, and whether conflicts, inference labels, weak corpus posture, or
failure-card posture constrain final output.

Core doctrine:

- RunAuthority decides final sufficiency.
- EvidenceLedger supplies custody facts.
- RunAuthorityContract supplies obligations and posture law.
- SearchJudgment supplies recovery/search outcome and budget posture.
- AnswerContract/source-obligation handoff remains a compatibility fact source.
- FinalAnswerPacket consumes the reduced sufficiency projection.
- Author writes from packet-derived posture and does not decide sufficiency.

## Previous Owners

Before AG-92C, final readiness still came from scattered local and compatibility
facts:

- `evidence_sufficient` / `is_sufficient`;
- `synth_was_insufficient`;
- weak corpus and failure-card payload flags;
- local source-obligation projections;
- AnswerContract fulfillment handoff state;
- FinalAnswerPacket adapter readiness inference;
- local mandatory caveat and prohibited-upgrade assembly.

Those facts still exist as compatibility inputs, but when a canonical
RunAuthority sufficiency projection exists, FinalAnswerPacket treats it as the
decisive readiness/posture authority.

## New Owner

The new owner is `RunKernel.RunAuthoritySufficiencyJudgment`.

Modules:

- `core/run_authority_sufficiency.py`
- `core/run_authority_sufficiency_prompt.py`
- `core/run_authority_sufficiency_runtime.py`
- `core/run_authority_sufficiency_validation.py`

RunKernel vocabulary:

- stage: `SUFFICIENCY_JUDGMENT_STAGE`
- action: `ActionType.SUFFICIENCY_JUDGMENT_DECIDE`
- observation: `ObservationType.SUFFICIENCY_JUDGMENT_DECIDED`
- state: `RunState.sufficiency_judgment`
- projection: `RunState.sufficiency_judgment_projection`
- history: `RunState.sufficiency_judgment_history`

Trace derives from `RunState.to_trace_projection()`.

## Decision And Posture Vocabulary

Decision values:

- `READY_DIRECT`
- `READY_WITH_CAVEATS`
- `PARTIAL_ANSWER_AUTHORIZED`
- `INSUFFICIENT_EVIDENCE`
- `BLOCK_FINALIZATION`
- `RECOVERY_REQUIRED_BUT_EXHAUSTED`
- `CONFLICT_BLOCKED`
- `INFERENCE_ONLY_WITH_LABELING`
- `SOURCE_BOUND_NUMERIC_UNKNOWN`
- `DEFER_TO_LEGACY_COMPATIBILITY`

Final answer postures:

- `direct_answer`
- `answer_with_caveats`
- `partial_answer`
- `insufficient_answer`
- `failure_card`
- `blocked`

The projection records contract fulfillment, required-obligation satisfaction,
missing/partial/satisfied obligations, unresolved conflicts, indirect inference
claims, source-bound numeric unknowns, weak/thin evidence, failure-card
authorization, final-answer allowance, mandatory caveats, prohibited upgrades,
readiness reasons, and packet-ready inputs.

## Input Model

The sufficiency input is compact and sanitized. It includes:

- contract id, selected templates, source requirements, inference/conflict/
  numeric/final-posture policy;
- EvidenceLedger candidate count, requirement count, requirement statuses,
  custody gaps, compatibility facts, and compact candidate records;
- SearchJudgment decision, classifications, gaps, insufficient posture, target
  classes, and recent history decisions;
- AnswerContract/source-obligation compatibility facts;
- final evidence and author evidence counts;
- conflict and indirect-inference posture facts;
- weak corpus, synthesis-insufficient, and failure-card facts;
- iteration/recovery/budget facts.

It excludes raw prompts, raw model output, raw provider payloads, DB rows,
caches, logs, full traces, output packets, local private artifacts, and secrets.

## Deterministic And Smart Paths

Deterministic sufficiency always runs where wired.

The optional smart-model path is controlled by
`RunConfig.run_authority_sufficiency_smart_model`, default `False`. When enabled,
the executor uses injected `ask_model`, strict JSON, prompt hash/length metadata,
and deterministic validation/repair. FinalAnswerPacket consumption does not
depend on smart sufficiency.

The prompt frames the model as a careful research director deciding whether the
committed run contract is fulfilled enough for final answering. It explicitly
says the model is not an Author, citation formatter, search executor, provider
router, or unbounded judgment layer.

## Validation And Repair

Validation enforces:

- a model cannot mark `READY_DIRECT` while required EvidenceLedger gaps remain;
- source-bound numeric unknowns remain unknown without source-bound custody;
- aggregate counts and citation presence do not satisfy custody;
- lower-tier, stale, off-topic, helper-only, or context-only evidence cannot
  satisfy stronger obligations;
- required caveats and prohibited upgrades from contract/search/evidence state
  are restored when omitted;
- unresolved conflicts cannot become direct confident claims;
- inferred conclusions cannot be presented as directly sourced;
- invalid model JSON falls back to deterministic sufficiency.

Unsafe model output is repaired to deterministic authority or falls back without
storing raw model output.

## FinalAnswerPacket Consumption

`core/pipeline_orchestrator.py` now coordinates only:

1. build compact sufficiency input after final evidence ledger reduction;
2. authorize sufficiency judgment;
3. execute the bounded sufficiency executor;
4. reduce the observation into RunKernel;
5. pass `sufficiency_judgment_projection` into FinalAnswerPacket preparation.

`core/final_answer_runtime_adapter.py` consumes the reduced projection. When it
is present and canonical, the adapter:

- uses sufficiency packet inputs for readiness status and reasons;
- adds sufficiency source obligations, mandatory caveats, prohibited upgrades,
  and claim postures;
- bypasses the run-contract-only missing-obligation fallback so the old local
  packet readiness inference cannot override a reduced sufficiency judgment;
- carries a compact sufficiency ref and final answer posture into the
  packet-derived Author authority block.

The old local fields remain compatibility inputs. They are no longer the
decisive authority when sufficiency state exists.

## Opened Surfaces

AG-92C intentionally opens:

- RunAuthority sufficiency prompt behavior;
- final sufficiency/readiness decision;
- FinalAnswerPacket posture payload;
- mandatory caveat and prohibited-upgrade authority payload;
- source-obligation satisfaction merge semantics;
- conflict, indirect-inference, source-bound numeric, weak-corpus, and
  failure-card final-posture handoff;
- static guards preserving prompt/validator ownership outside the orchestrator.

## Closed Surfaces

AG-92C keeps closed:

- live validation;
- live provider/model/search/retrieval calls during implementation and tests;
- new provider integration;
- broad retrieval/search/ranking/query ordering behavior;
- Author prose style and citation formatting style;
- UI/UX, hosted/deployment/cache behavior;
- secrets, `.env`, raw provider payloads, raw prompts, raw model responses,
  DB rows, private logs, caches, full raw traces, output packets, and private
  artifacts.

No live validation was run.

## Behavior Changes

Intentional changes:

- final sufficiency is reduced into canonical RunKernel state before packet
  preparation;
- FinalAnswerPacket readiness and Author posture now consume the reduced
  sufficiency projection;
- missing official/current/legal/canonical/source-bound obligations produce
  partial/insufficient posture instead of direct posture;
- satisfied EvidenceLedger custody prevents false missing-obligation posture;
- source-bound numeric unknowns, conflicts, inference labels, weak-corpus, and
  failure-card constraints are preserved in packet/Author authority payloads.

Compatibility preserved:

- local `evidence_sufficient`, `is_sufficient`, weak/failure flags,
  AnswerContract projections, and source-obligation projections remain inputs;
- Author prose/citation style is unchanged;
- FinalAnswerPacket still emits legacy citation/source handoff projections.

## Remaining Work

AG-92D should consolidate remaining final-readiness compatibility branches and
continue orchestrator authority cleanup. In particular, post-Author projections
and late weak/failure output classification still carry compatibility-era
readiness facts that are now subordinate to sufficiency when present.
