Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG76C_RT_RUNTIME_TRACE_EXPORT_ATTACHMENT).

# AG-76C-RT Runtime Trace / Export Attachment Compatibility Extraction

Date: 2026-05-30

## Scope

AG-76C-RT extracted the passive runtime trace/export/checkpoint attachment tail
from `core/pipeline_orchestrator.py` into
`core.runtime_trace_export_attachment`.

This phase is an orchestrator-strangling extraction. It does not repair or
change Controller decisions, provider/search behavior, query strategy,
classification, candidate fit, prompt behavior, final answer prose, Author
behavior, citation formatting, follow-up, Scrutineer, Economist, or live
validation behavior.

## Extracted Seam

The extracted seam owns the legacy tail that attaches already-computed observer
payloads after the main `execution_trace` has been assembled:

- passive runtime projection traces through the existing
  `attach_passive_runtime_projection_traces(...)` boundary;
- `retrieval_budget_pressure_shadow`;
- `source_class_recovery_candidate_v2`;
- `source_class_recovery_validation_l1`;
- size-guarded `controller_diagnostics`;
- the final `execution_trace` attachment to the session payload.

The helper preserves the legacy field names and assignment order for this tail.
Existing projection helpers continue to mirror their own checkpoint/export
payloads; AG-76C-RT only centralizes the compatibility handoff that was still
inline in the orchestrator.

## New Helper Contract

`core.runtime_trace_export_attachment.attach_runtime_trace_export_compatibility_payloads(...)`
receives already-computed runtime inputs and returns a
`RuntimeTraceExportAttachmentResult` containing:

- the same mutated `execution_trace` mapping;
- the source-class recovery validation packet needed by the legacy execution log
  compatibility path.

The helper may assemble, normalize, attach, or preserve runtime trace/export and
checkpoint compatibility fields from facts it is given. It is observer-only: it
must not decide source sufficiency, recovery admission, provider selection,
provider routing, query strategy, classification, candidate fit, citation
eligibility, final answer posture, prompt contents, or Author behavior.

## What Remains In `core/pipeline_orchestrator.py`

`core/pipeline_orchestrator.py` still assembles the large runtime trace from
local pipeline facts and still owns substantial execution plumbing. After
AG-76C-RT, the passive attachment tail is a handoff:

1. build the base `execution_trace` from already-computed local facts;
2. call `attach_runtime_trace_export_compatibility_payloads(...)`;
3. carry the returned validation packet into the legacy execution log entry.

The orchestrator no longer owns inline assembly for the extracted compatibility
payloads.

## Parity Evidence

Focused AG-76C-RT tests compare the helper against a legacy inline sequence with
deterministic builders. They assert parity for:

- execution trace output;
- session `execution_trace` attachment;
- `source_class_recovery_candidate_v2` preservation;
- `source_class_recovery_validation_l1` preservation;
- `retrieval_budget_pressure_shadow` preservation;
- size-guarded `controller_diagnostics` preservation.

Static tests also assert that the helper does not import protected provider,
search, prompt, final-evidence, routing, or answer-contract behavior modules,
and that the orchestrator delegates the attachment tail instead of owning the
legacy inline calls.

## Protected Surfaces Kept Closed

AG-76C-RT did not change:

- Controller decision behavior;
- AnswerContract behavior;
- ControllerEvidenceLedger behavior beyond existing projection helper use;
- ControllerRecoveryDecision behavior;
- AuthorityLifecycle behavior;
- provider routing, provider selection, provider depth, escalation, swaps, or
  provider set;
- query strategy, source constraints, retrieval ranking/filtering;
- source-class/currentness classifier semantics;
- candidate-fit semantics;
- prompt behavior;
- final answer prose;
- Author behavior;
- citation formatting or citation selection;
- follow-up, Scrutineer, or Economist behavior;
- weak-corpus recovery policy;
- package, CLI, environment variable, DB-name, or state-key compatibility names.

## Next Deletion Target

The next safe deletion target is the remaining persistence/outcome compatibility
packaging around execution-log/session/run-outcome payload assembly in
`core/pipeline_orchestrator.py`, after a dedicated phase defines parity tests for
JSONL/SQLite/session/outcome field shape. Provider/search/query/prompt/final
answer surfaces remain closed.
