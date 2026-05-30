# AG-76C-BD Orchestrator Burn-Down Review

> 2026-05-30 BD-R2 update: this document is the historical AG-76C-BD review.
> Its AG-76C-RT next-phase selection has been completed by AG-76C-RT and
> AG-76C-RT-C, followed by AG-76C-OP and AG-76C-PE. The current durable
> next-phase selection is AG-76C-KB-C, recorded in
> `docs/architecture/AG76C_BD_R2_POST_RT_OP_PE_BURNDOWN.md` and
> `core/pipeline_decision_registry.py`.


Date: 2026-05-28

## Scope And Non-Goals

AG-76C-BD is an Architecture Groove / Prove Mode burn-down review and
next-seam selection phase for `core/pipeline_orchestrator.py`.

The phase is review, registry, docs, and static tests only. It does not extract
another runtime seam and does not change runtime behavior.

Closed surfaces remain closed: Controller decision behavior, provider routing
or depth, provider swaps, Linkup policy, query strategy, source constraints,
retrieval ranking/filtering, source-class/currentness classifier behavior,
candidate-fit semantics, final evidence selection semantics, final answer
prose, Author behavior, Author prompt semantics, citation formatting, citation
selection, prompt behavior, follow-up behavior, Scrutineer, Economist, live
validation, IRS hardcoding, source-specific official resolver implementation,
raw/private data, and destructive git.

## AG-76C-FE/CS/DP Prerequisite Verification

Current local `main` contained AG-76C-DP / PR #28 before AG-76C-BD work:

```text
ff7006c Merge pull request #28 from aidan600/codex/ag76c-dp-diagnostics-projection-handoff-extraction
a453210 Extract source-class diagnostics projection handoff
```

Required AG-76C-DP artifacts were present:

- `docs/architecture/AG76C_DP_DIAGNOSTICS_PROJECTION_HANDOFF_EXTRACTION.md`
- `core/source_class_recovery_projection_handoff.py`

Current local `main` contained AG-76C-CS / PR #27:

```text
22facfe Merge pull request #27 from aidan600/codex/ag76c-cs-runner-owned-recovered-candidate-stream
aff12c1 Extract runner-owned recovered candidate stream
```

Required AG-76C-CS artifacts were present:

- `docs/architecture/AG76C_CS_RUNNER_OWNED_RECOVERED_CANDIDATE_STREAM.md`
- `core/source_class_recovery_candidate_stream.py`

Current local `main` contained AG-76C-FE / PR #26:

```text
341d524 Merge pull request #26 from aidan600/codex/ag76c-fe-final-evidence-bundle-extraction
5fa7814 Update AG-69 guards for final evidence builder
ec56a49 Extract final evidence bundle builder
```

Required AG-76C-FE artifacts were present:

- `docs/architecture/AG76C_FE_FINAL_EVIDENCE_BUNDLE_EXTRACTION.md`
- `core/final_evidence_bundle_builder.py`

AG-76B registry artifacts were present:

- `docs/architecture/AG76B_PIPELINE_DECISION_REGISTRY.md`
- `core/pipeline_decision_registry.py`

Static inspection confirms `pipeline_orchestrator.py` no longer owns:

- final evidence/source-ID packaging;
- recovered/source-class candidate stream assembly;
- recovered/source-class diagnostics/projection handoff.

## Completed AG-76C+ Seam Summary

| phase | old orchestrator responsibility | replacement owner | status |
| --- | --- | --- | --- |
| AG-76C-FE | final evidence/source-ID packaging, evidence block, cached prefix, Author evidence block, final source telemetry inputs | `core.final_evidence_bundle_builder` | extracted_complete |
| AG-76C-CS | recovered/source-class candidate stream scan and allocation candidate append | `core.source_class_recovery_candidate_stream` | extracted_complete |
| AG-76C-DP | recovered/source-class diagnostics and projection input handoff | `core.source_class_recovery_projection_handoff` | extracted_complete |

## Remaining Pipeline Orchestrator Seam Inventory

The orchestrator still contains several kinds of responsibility:

- Controller-approved execution plumbing that is acceptable for now.
- Passive trace/projection/export attachment clutter.
- Persistence/outcome compatibility packaging.
- Decision-sensitive behavior that must stay closed.
- Follow-up/AnswerContract state packaging that should wait for a Controller
  state phase.

AG-76C-BD classifies each seam with these exact categories:

1. `extracted_complete`
2. `pure_plumbing`
3. `mechanical_candidate_for_extraction`
4. `decision_authority_still_local`
5. `protected_behavior_surface`
6. `defer_until_controller_state_ready`
7. `intentionally_remaining_for_now`

## Required Classification Table

| seam_name | current_location | current_owner | target_owner | classification | protected_surface_risk | current tests | missing parity tests | extraction difficulty | recommended next action | priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AG-76C-FE final evidence/source-ID packaging | `core/final_evidence_bundle_builder.py` | final evidence builder | final evidence builder | extracted_complete | final answer, Author, citation | `tests/test_ag76c_final_evidence_bundle_builder.py` | none | complete | keep completed | P0 |
| AG-76C-CS runner-owned recovered/source-class candidate stream | `core/source_class_recovery_candidate_stream.py` | candidate stream helper | candidate stream helper | extracted_complete | classifier, candidate fit | `tests/test_ag76c_cs_runner_owned_candidate_stream.py` | none | complete | keep completed | P0 |
| AG-76C-DP source-class diagnostics/projection handoff | `core/source_class_recovery_projection_handoff.py` | projection handoff helper | projection handoff helper | extracted_complete | trace/export fields, classifier | `tests/test_ag76c_dp_diagnostics_projection_handoff.py` | none | complete | keep completed | P0 |
| router/researcher/query preparation handoff | `pipeline_orchestrator.py` lines 2785-3275 and 4274-4341 | orchestrator plus routing/query helpers | future Controller retrieval preparation contract | protected_behavior_surface | provider routing, query strategy, prompt behavior | router/retrieval tests | full router/query parity | high | keep closed | P3 |
| source obligation / AnswerContract initialization and handoff | lines 3402-4072, 4962-5030, 6705-6769 | AnswerContract plus orchestrator fact packaging | AnswerContract / Controller state handoff helper | defer_until_controller_state_ready | AnswerContract semantics, final posture, citations | `tests/test_answer_contract_runtime_handoff.py` | multi-stage fact-package parity | medium | defer AG-76C-AC | P2 |
| source-class recovery runner dispatch handoff | lines 5159-5279 | ControllerRecoveryDecision plus runner | `core.source_class_recovery_runner` | pure_plumbing | provider allocation surface | AG-74F tests | static Controller-approved action proof | low | leave as dispatch plumbing | P2 |
| provider/retrieval execution loop | lines 4274-4938 | orchestrator with Controller allocation gates | future runner only after provider/search license | protected_behavior_surface | provider/search/query/ranking | AG-75A allocation tests | provider loop parity | high | keep closed | P3 |
| source-class recovery lifecycle / projection handoff | `source_class_recovery_projection_handoff.py`, lines 6650-6661 | projection handoff helper | projection handoff helper | extracted_complete | trace/export fields | AG-76C-DP tests | none | complete | no BD action | P0 |
| recovered evidence visibility boundary | `core/recovered_evidence_visibility.py` | ControllerRecoveryDecision plus visibility helper | visibility helper | extracted_complete | candidate fit, final evidence selection | AG-75C, AG-76C-CS tests | none | complete | keep subordinated | P1 |
| final evidence bundle builder handoff | builder plus lines 5364, 5943, 6124, 6265 | final evidence builder | final evidence builder | extracted_complete | final answer, Author, citations, fit | AG-76C-FE tests | none | complete | keep extracted | P0 |
| final evidence/source telemetry and persistence handoff | lines 6438-6561 and 6970-7273 | orchestrator plus evidence registry/db/logging helpers | future `core.run_outcome_persistence_handoff` | mechanical_candidate_for_extraction | trace fields, JSONL/SQLite, RunOutcome | evidence registry and controller state tests | JSONL/SQLite/RunOutcome parity | medium | defer behind RT | P1 |
| runtime trace projection/export attachment | lines 6930-6967 | orchestrator calls observer helpers after trace assembly | future `core.runtime_trace_export_attachment_handoff` | mechanical_candidate_for_extraction | trace/export fields, citation selection | runtime projection/export and DP tests | attachment sequence, candidate_v2, diagnostics parity | low | select AG-76C-RT | P0 |
| controller evidence ledger projection/handoff | ledger plus projection helpers | ControllerEvidenceLedger plus observers | ControllerEvidenceLedger | intentionally_remaining_for_now | trace fields, Controller behavior | AG-74A and diagnostics tests | ledger projection parity if moved | low | keep interpretation in ledger | P1 |
| Analyst prompt/context handoff | lines 5658-6159 | orchestrator Analyst prompt assembly | explicit Analyst prompt contract only | protected_behavior_surface | prompt, Analyst, Author | AG-59AB tests | exact prompt/context parity | high | keep closed | P3 |
| Author prompt/evidence handoff | lines 6167-6419 | orchestrator Author prompt assembly | explicit Author contract only | protected_behavior_surface | Author, final answer, citations | AG-76C-FE tests | exact Author prompt parity | high | keep closed | P3 |
| citation/source-list handoff | lines 1913-1945, 6265-6283, 6438-6445 | orchestrator citation telemetry and source-list consumers | explicit citation subsystem only | protected_behavior_surface | citation selection/formatting, final prose | AG-76C-FE tests | citation/source-list parity | high | keep closed | P3 |
| weak-corpus/off-topic/failure-card gates | lines 1436-1759, 4430-4550, 6473-6501 | orchestrator plus weak-corpus/failure-card helpers | Controller state representation after blueprint | decision_authority_still_local | weak-corpus, failure-card, prompt behavior | weak-corpus controller tests | weak/off-topic/failure-card parity | high | review-only blueprint if selected later | P2 |
| Scrutineer/remediation handoff | lines 5981-6159, 6296-6315 | orchestrator Scrutineer/remediation path | explicit Scrutineer contract only | protected_behavior_surface | Scrutineer, provider, Author | diagnostics tests | remediation prompt/provider parity | high | keep closed | P3 |
| Economist preflight / Economist handoff | lines 1771-2556 and 5452-5645 | orchestrator quantitative/Economist handoff | explicit Economist contract only | protected_behavior_surface | Economist, Analyst, Author | diagnostics tests | Economist preflight parity | high | keep closed | P3 |
| follow-up/session state handoff | lines 2678-2680, 3489-4219, 7135-7249 | orchestrator continuation/session compatibility plumbing | AnswerContract / Controller initial state after AG-76A decision | defer_until_controller_state_ready | follow-up, Controller behavior | controller state tests | follow-up state parity | medium | AG-76A should wait | P2 |
| JSONL/SQLite/persistence/outcome packaging | final tail delegates packaging to `core.outcome_persistence_packaging` and side-effect execution to `core.persistence_side_effects` | `core.outcome_persistence_packaging`; `core.persistence_side_effects` | `core.outcome_persistence_packaging`; `core.persistence_side_effects` | extracted_complete | JSONL/SQLite, RunOutcome, trace fields | `tests/test_ag76c_op_outcome_persistence_packaging.py`, `tests/test_ag76c_pe_persistence_side_effects.py`, plus existing controller/evidence tests | none for extracted packaging and side-effect seams | complete | Next target: reduce passive KB persistence context handoff after exact KB payload parity | P1 |

The same table is represented in passive registry data as
`AG76C_BD_ORCHESTRATOR_SEAM_LEDGER`.

## Next Extraction Candidates Considered

| candidate | decision |
| --- | --- |
| AG-76C-RT - Runtime Trace / Export Attachment Compatibility Extraction | selected |
| AG-76C-PH - Persistence / Outcome Packaging Handoff Extraction | completed by AG-76C-OP packaging and AG-76C-PE side-effect execution handoff |
| AG-76C-AC - AnswerContract / Controller State Handoff Compatibility Extraction | deferred; touches posture and Controller state readiness |
| AG-76C-WG - Weak-Corpus / Off-Topic Gate Mapping Review | deferred; decision-sensitive and better as blueprint first |
| AG-76A - Follow-Up as Initial AnswerContract / Controller State | wait; a safer narrow AG-76C seam remains |

## Selected Next Extraction Phase

Selected phase:

```text
AG-76C-RT - Runtime Trace / Export Attachment Compatibility Extraction
```

## Exact Old Orchestrator Block / Responsibility

Move only the passive attachment tail currently in
`core/pipeline_orchestrator.py` lines 6930-6967:

- call `attach_passive_runtime_projection_traces(...)`;
- attach `retrieval_budget_pressure_shadow`;
- attach `source_class_recovery_candidate_v2`;
- build and attach `SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY` when present;
- build and attach `controller_diagnostics` when within the existing size guard;
- attach finalized `execution_trace` to `new_session`.

Do not move the full `execution_trace` field dictionary in this phase. Do not
rename trace/export fields.

## Replacement Owner / Module / Helper

Recommended replacement owner:

```text
core.runtime_trace_export_attachment_handoff
```

Recommended helper:

```text
attach_runtime_trace_export_compatibility_payloads(...)
```

The helper should orchestrate existing observer helpers and return/pass through
the same `execution_trace` object. It must not select evidence, classify
sources, route providers, choose citations, prompt models, or decide Controller
state.

## Protected Surfaces For Selected Phase

AG-76C-RT must protect:

- `execution_trace` field names and packet shapes;
- runtime trace projection/export field names;
- official/canonical recovery visibility export shape;
- ControllerEvidenceLedger projection fields;
- evidence integration checkpoint mirrored fields;
- `source_class_recovery_candidate_v2` shape;
- `SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY` payload shape;
- `controller_diagnostics` payload and size-guard behavior;
- final answer, Author, citation, provider/search/query/classifier/fit behavior.

## Required Parity Tests For Selected Phase

AG-76C-RT should add tests proving:

- legacy trace attachment sequence parity for a synthetic `execution_trace`;
- runtime trace projection/export key and value parity;
- official/canonical visibility export parity;
- `source_class_recovery_candidate_v2` parity;
- source-class recovery validation packet parity, including `None`/no-update;
- controller diagnostics payload parity, including size-guard omission;
- static guard that `pipeline_orchestrator.py` no longer owns the attachment
  tail after extraction;
- static guard that the new helper imports no provider/search/query/Author/
  citation/final-answer behavior.

Existing suites to reuse:

- `tests/test_runtime_trace_projection_assembly_ag46c.py`
- `tests/test_official_canonical_recovery_visibility_export_ag50c.py`
- `tests/test_controller_diagnostics_trace_contract.py`
- `tests/test_ag76c_dp_diagnostics_projection_handoff.py`

## Stop Conditions For Selected Phase

AG-76C-RT must stop if:

- trace/export field renames would be required;
- provider/search/query/classifier/fit behavior would change;
- Author/citation/final-answer behavior would change;
- Controller decision behavior would change;
- raw provider payloads, raw prompts, DB rows, private logs, caches, full traces,
  output packets, secrets, or API keys would be needed;
- live validation or provider/model/search calls would be needed;
- the phase expands into a broad `pipeline_orchestrator.py` rewrite.

## Why Non-Selected Candidates Were Deferred

AG-76C-PH is a valid future mechanical seam, but JSONL/SQLite/session/RunOutcome
packaging has side effects and UI-visible payload risk. It should follow a
smaller trace attachment extraction.

AG-76C-AC touches AnswerContract semantics and final posture. It should wait
until Controller state handoff boundaries are the explicit phase target.

AG-76C-WG maps local weak/off-topic/failure-card gates. Those gates remain
decision-sensitive; they need a blueprint or Controller-state phase before
runtime extraction.

AG-76A follow-up as initial AnswerContract / Controller state should wait.
AG-76C-BD found a safe narrower AG-76C extraction candidate.

## Closed Surface Confirmation

Author/citation/final-answer surfaces remain closed.

Provider/search/query/classifier/fit surfaces remain closed.

Trace/projection/export layers remain observers. AG-76C-BD does not change trace
field names or telemetry schemas.

## Recommendation To Strategy Chat

Proceed with:

```text
AG-76C-RT - Runtime Trace / Export Attachment Compatibility Extraction
```

Keep the phase narrow. Extract only the passive trace/export attachment tail
from `pipeline_orchestrator.py` into a compatibility helper and prove exact
field parity with static and focused unit tests.

## Codex-Ready Next-Phase Outline

```text
AG-76C-RT - Runtime Trace / Export Attachment Compatibility Extraction

Mode:
Architecture Groove / Prove Mode.

Goal:
Extract the passive runtime trace/export attachment tail from
core/pipeline_orchestrator.py into core.runtime_trace_export_attachment_handoff
without changing runtime behavior or trace/export field names.

Old block:
core/pipeline_orchestrator.py lines 6930-6967:
attach_passive_runtime_projection_traces, retrieval_budget_pressure_shadow,
source_class_recovery_candidate_v2, source-class recovery validation packet,
controller_diagnostics, and new_session execution_trace attachment.

Replacement owner:
core.runtime_trace_export_attachment_handoff.attach_runtime_trace_export_compatibility_payloads(...)

Protected surfaces:
trace/export field names, official/canonical visibility export packet shape,
ControllerEvidenceLedger projection fields, evidence integration checkpoint
mirrors, source_class_recovery_candidate_v2, source-class recovery validation,
controller_diagnostics size guard, final answer, Author, citation, provider,
search, query, classifier, and fit behavior.

Required parity tests:
legacy attachment sequence parity, projection/export parity, candidate_v2 parity,
validation packet parity, controller diagnostics size-guard parity, static guard
that orchestrator no longer owns the attachment tail, and protected import/call
scan for the new helper.

Stop conditions:
field rename, trace schema churn, protected behavior change, live call, raw or
private data requirement, or broad pipeline_orchestrator.py rewrite.
```
