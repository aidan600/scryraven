Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (CONTROLLER_ACTION_ENVELOPE_AG25).

# AG-25 Controller Action Envelope And Registry

Status: M2 / AG-25 architecture interface. Classification: pure/offline
representation layer.

This phase adds a shared controller action envelope and registry in
`core/controller_action_envelope.py`. The layer represents existing
controller-shaped decisions and future action slots without changing runtime
retrieval, providers, prompts, source ranking, persistence, handoff behavior, or
action-loop ownership.

## Goal

AG-23 found that ProPlex already has several controller-shaped islands, but they
use related separate shapes. AG-25 defines one compact JSON-safe action envelope
that can describe those decisions consistently:

- weak-corpus recovery;
- source-class recovery, including the limited official/legal recovery slot;
- retrieval-stop terminal and shadow decisions;
- answer-contract action history items;
- future social-signal side-packet action descriptors.

The envelope is descriptive. It is not a scheduler, reducer, executor, or source
of live runtime authority.

## Envelope Shape

Each `ControllerActionEnvelope` serializes to a plain JSON-safe dictionary with:

- `schema_version`;
- `name`;
- `status`: `approved`, `blocked`, `skipped`, `shadow`, `completed`, `failed`,
  or `informational`;
- `authority`: `active`, `passive`, `shadow`, or `future`;
- `reason`, `skip_reason`, and `blockers`;
- compact `input_summary`;
- compact `approved_work`;
- `executor` identity as a string, if an existing executor/owner exists;
- `side_effect_class`: `none`, `retrieval`, `stop`, `handoff_only`,
  `social_side_packet`, or `review_only`;
- compact `output_delta`;
- `trace_keys`;
- `handoff_boundary`: `hidden`, `sanitized_summary_only`,
  `ordinary_evidence_eligible`, or `final_answer_posture_only`;
- `safety_notes`;
- compact `metadata`.

The serializer removes keys such as `raw_*`, `prompt`, `provider_payload`,
`full_trace`, `db_row`, `cache`, `secret`, and `api_key` from nested payloads.
It converts enums, tuples, sets, dataclasses, and mappings into deterministic
plain JSON-safe values.

## Registry

The registry maps action names to ownership and boundaries. Required AG-25
actions are:

| Action | Current authority | Side effect | Executor/owner | Handoff boundary | Notes |
| --- | --- | --- | --- | --- | --- |
| `recover_weak_corpus` | active | retrieval | existing orchestrator weak-corpus branch | ordinary evidence eligible | One first-pass attempt; provider/depth/prompt choices remain unchanged. |
| `recover_missing_source_class` | active | retrieval | `core.source_class_recovery_executor:execute_source_class_recovery_action` | ordinary evidence eligible | One bounded attempt; reuses current providers and depth. |
| `retrieve_targeted` | passive | retrieval | existing orchestrator retrieval loop | ordinary evidence eligible | Answer-contract vocabulary only; not the runtime scheduler. |
| `stop_sufficient` | shadow | stop | existing synthesis branch | final answer posture only | Retrieval-stop sufficient branch remains shadow/passive. |
| `stop_insufficient_with_caveat` | active, limited | stop | existing terminal no-query/budget branches | final answer posture only | Active only for already-terminal legacy branches. |
| `request_social_signal_check` | future | social side packet | none | sanitized summary only | Placeholder only; no social runtime integration. |
| `run_scrutineer_review` | passive | review only | existing Scrutineer boundary, not controller-dispatched | sanitized summary only | Does not change Scrutineer policy. |
| `handoff_to_analyst` | passive | handoff only | existing Analyst/Author boundary | sanitized summary only | Descriptive only; protected handoff remains unchanged. |

The registry also includes the remaining answer-contract vocabulary so action
history items can be represented without a KeyError:

- `diagnose_question`;
- `set_or_update_answer_contract`;
- `inspect_evidence_state`;
- `identify_missing_information`;
- `generate_targeted_queries`;
- `resolve_conflict`;
- `decompose_quantitative_question`;
- `ask_user_clarification`.

## Adapter Coverage

`envelope_from_source_class_recovery_decision` maps
`SourceClassRecoveryDecision` into `recover_missing_source_class`.

- Approved decisions become `status=approved`, `authority=active`,
  `side_effect_class=retrieval`, with the source-class executor identity,
  approved queries, provider role, search depth, attempt count, and active
  source-class trace keys.
- Blocked decisions become `status=blocked`, with blockers and no executor side
  effect.
- No-action decisions become `status=skipped`, with skip reason and no executor
  side effect.
- Official/legal/current-primary source-class cases carry an AG-22 limitation
  note.

`envelope_from_weak_corpus_recovery_decision` maps
`WeakCorpusRecoveryDecision` into `recover_weak_corpus`.

- Approved decisions remain distinct from source-class recovery.
- The envelope preserves one-attempt, iteration budget, prior-attempt, readable
  passage, and orchestrator ownership signals as sanitized metadata when a
  snapshot is provided.

`envelope_from_retrieval_stop_decision` maps `RetrievalStopDecision` into:

- `retrieve_targeted` for `continue_retrieval`;
- `stop_sufficient` for `proceed_to_synthesis`;
- `stop_insufficient_with_caveat` for no-query, budget-exhausted, redundant,
  after-recovery, or blocked terminal decisions.

Active terminal stop envelopes use `side_effect_class=stop` and
`handoff_boundary=final_answer_posture_only`. Shadow envelopes stay
`authority=shadow`, `status=informational`, and `side_effect_class=none`.

`envelope_from_answer_contract_action_result` and
`envelopes_from_answer_contract_action_history` map
`AnswerControllerActionResult` records without changing fulfillment semantics.

`social_signal_placeholder_envelope` represents the future
`request_social_signal_check` action as a side-packet descriptor only.

## Social Signal Boundary

Social signal is represented only as a future placeholder descriptor in AG-25.
It is not runtime-wired and does not call a social provider.

The boundary is explicit:

- `request_social_signal_check` uses `side_effect_class=social_side_packet`;
- it may produce only an Author-safe social/perception side-packet in a future
  phase;
- it is not ordinary evidence eligible;
- it cannot satisfy `official_current_rules`, `legal_or_regulatory_text`,
  `current_primary_or_official`, primary evidence, or ordinary factual evidence.

The helper `action_can_satisfy_evidence_class` returns false for those evidence
classes and true only for explicit social side-packet classes.

## Official/Legal Recovery Boundary

Official/legal/current-primary recovery remains a limited subtype of
`recover_missing_source_class`.

AG-25 does not tune legal-source retrieval, providers, domains, search depth,
ranking, prompts, or final evidence selection. It preserves the AG-22 limitation:
the live validation did not demonstrate final official/current-primary source
quality from allowed artifacts, and internal recovery telemetry was not visible
enough to isolate the failure point.

The envelope records this as a safety note when the source-class recovery
decision targets official/legal/current-primary source classes or an
answer-contract official/legal gap.

## What Did Not Change

AG-25 does not:

- import or call `pipeline_orchestrator.py`;
- import or call provider modules;
- import Streamlit;
- import persistence modules;
- change retrieval execution;
- change provider routing or search depth;
- change prompts;
- change source filtering or ranking;
- change Analyst, Economist, Scrutineer, or Author handoff behavior;
- integrate social runtime behavior;
- alter persistence schemas.

## Known M3 Gaps

The shared envelope is now available, but the runtime is still orchestrator-led.
M3 still needs:

1. an offline action-loop parity harness that replays current behavior through
   envelopes;
2. a reducer for controller state;
3. explicit executor contracts for weak-corpus and terminal retrieval-stop
   actions;
4. budget ownership rules across retrieval, recovery, and stop actions;
5. shared evidence-boundary ownership for recovered evidence, social side
   packets, and final handoff;
6. sanitized validation packets for source-class recovery diagnostics before
   legal-source tuning.

## Validation

Focused AG-25 tests cover:

- registry coverage for required actions;
- source-class approved, blocked, and skipped adapter behavior;
- weak-corpus adapter identity and budget metadata;
- active and shadow retrieval-stop boundaries;
- answer-contract action-history envelopes;
- social placeholder evidence boundaries;
- static no-import guard for protected runtime/provider/persistence modules;
- deterministic JSON-safe serialization.

Relevant existing controller tests remain the compatibility gate.
