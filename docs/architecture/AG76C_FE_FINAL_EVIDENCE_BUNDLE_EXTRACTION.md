# AG-76C-FE Final Evidence Bundle / Source-ID Assignment Replacement Extraction

Date: 2026-05-28

## Scope And Non-Goals

AG-76C-FE is an Architecture Groove / Prove Mode extraction phase for final
evidence bundle construction and source-ID assignment in
`core/pipeline_orchestrator.py`.

The licensed scope is parity-preserving extraction only:

- final evidence bundle construction;
- recovered/Controller-selected evidence insertion handoff;
- stable source-ID assignment;
- `ordered_sources` construction;
- `evidence_block` construction;
- `cached_prefix` construction;
- supplemental and remediation evidence bundle rebuilds;
- `author_evidence` slicing;
- `author_evidence_block` packaging;
- final source telemetry and final evidence snapshot input packaging.

This phase does not change final-answer prose, Author behavior, Author prompt
semantics, citation formatting, citation selection, final evidence selection
semantics, provider/search behavior, query behavior, classifier/currentness
behavior, candidate-fit behavior, Scrutineer behavior, Economist behavior,
follow-up behavior, live validation, direct IRS handling, or broad
`pipeline_orchestrator.py` domain logic.

## AG-76B Prerequisite Verification

Current local `main` contained AG-76B / PR #25 before implementation:

```text
739812b Merge pull request #25 from aidan600/codex/ag76b-pipeline-decision-registry-final-evidence-blueprint
f829eda Add AG-76B pipeline decision registry
```

Required AG-76B artifacts were present:

- `docs/architecture/AG76B_PIPELINE_DECISION_REGISTRY.md`
- `core/pipeline_decision_registry.py`
- `tests/test_ag76b_pipeline_decision_registry.py`

Required registry evidence was present:

- `core.pipeline_decision_registry.NEXT_EXTRACTION_PHASE == "AG-76C-FE"`.
- The registry names `core.final_evidence_bundle_builder` as replacement owner.
- The AG-76B doc identifies final evidence bundle construction and source-ID
  assignment as the next extraction.

Required AG-75C artifacts remained present:

- `docs/architecture/AG75C_LOCAL_AUTHORITY_GATE_RETIREMENT_AUDIT.md`
- `core/recovered_evidence_visibility.py` defines
  `apply_controller_recovered_evidence_visibility(...)`.
- `core/pipeline_orchestrator.py` no longer defines
  `_apply_recovered_evidence_visibility(...)`.

## Old Orchestrator Responsibility Replaced

AG-76C-FE replaced the old `pipeline_orchestrator.py` responsibility for:

- initial final evidence sort/filter/recovered-visibility handoff;
- local `unique_source_urls`, `ordered_sources`, `next_source_id`, and
  `p["source_id"]` loops;
- `evidence_block` and `cached_prefix` assembly;
- supplemental evidence refresh/rebuild;
- remediation evidence refresh/rebuild;
- `author_evidence` slicing and `author_evidence_block` assembly;
- final evidence snapshot argument packaging.

The old local source-ID loops are no longer present in
`pipeline_orchestrator.py`.

## New Builder Module And Function Contract

New owner:

```text
core.final_evidence_bundle_builder
```

New data contracts:

- `FinalEvidenceBundle`
- `FinalEvidenceBundleInputs`
- `FinalEvidenceSourceIdentity`
- `FinalEvidenceSourceTelemetry`

New helper contract:

- `build_final_evidence_bundle(...)`
- `assign_stable_source_ids(...)`
- `build_ordered_sources(...)`
- `build_evidence_block(...)`
- `build_cached_prefix(...)`
- `slice_author_evidence(...)`
- `build_author_evidence_block(...)`
- `attach_author_evidence(...)`
- `build_final_source_telemetry_inputs(...)`

The builder is mechanical. It uses injected filter, plausible-domain, and
recovered-visibility callables and does not import the Pipeline Decision
Registry, Author, citation, provider, query, classifier, candidate-fit, or
orchestrator runtime surfaces.

## Builder Input Contract

`FinalEvidenceBundleInputs` carries:

- `all_passages`;
- `top_chunks`;
- complexity-derived `max_domain_chunks`;
- existing `filter_top_evidence` callable;
- existing `is_plausible_domain` callable;
- `current_date`;
- `query`;
- `active_source_class_recovery_lifecycle`;
- existing recovered-evidence visibility callable;
- existing `reserve_limit`, defaulting to `1`.

The builder sorts `all_passages` by the existing score key before calling the
injected filter, matching the old orchestrator sequence.

## Builder Output Contract

`FinalEvidenceBundle` returns:

- `final_top_evidence` with stable `source_id` values written onto passages;
- `unique_source_urls`;
- `ordered_sources`;
- `evidence_block`;
- `cached_prefix`;
- `author_evidence`, once `attach_author_evidence(...)` is called;
- `author_evidence_block`, once `attach_author_evidence(...)` is called;
- `final_source_telemetry`.

`FinalEvidenceSourceTelemetry` packages:

- final source IDs observed on the final evidence bundle;
- unique source URL count;
- ordered source lines;
- final evidence count;
- final-answer source telemetry copy, when supplied;
- final evidence snapshot payload for `record_final_evidence_snapshot(...)`.

## Source-ID Assignment Parity Rules

AG-76C-FE preserves the old source-ID behavior:

- first unique URL receives the first integer source ID;
- duplicate URLs reuse the first assigned source ID;
- `source_id` is written onto each final evidence passage;
- plausible URLs are included in `ordered_sources` in first occurrence order;
- implausible and empty URLs still receive IDs but are omitted from
  `ordered_sources` when the injected plausible-domain predicate rejects them;
- missing URL still raises `KeyError`, matching the prior direct `p["url"]`
  access.

## Evidence And Author Block Parity Rules

The builder preserves exact current text formats:

- final evidence block entries:
  `[Source N] {title}\nURL: {url}\nExcerpt: {text[:1200]}`;
- block separator: two newlines;
- cached prefix:
  `<evidence_block>\n{evidence_block}\n</evidence_block>\n\nToday is {current_date}.\nUser's Original Prompt: {query}\n`;
- Author evidence slicing: `final_top_evidence[:precision_count]`;
- Author precision evidence block uses the same evidence block entry format;
- Sources-list lines remain `- [N] [Title](URL)`.

Author prompt placement remains in `pipeline_orchestrator.py` and was not
changed.

## Supplemental And Remediation Rebuild Parity

Supplemental and Scrutineer remediation paths now call
`build_final_evidence_bundle(...)` after extending `all_passages`.

The builder performs the same sequence as the old duplicated blocks:

1. sort `all_passages` by score descending;
2. call existing `filter_top_evidence`;
3. call existing recovered-evidence visibility helper;
4. assign source IDs;
5. rebuild `ordered_sources`, `evidence_block`, and `cached_prefix`;
6. append the existing Linkup block only under the same orchestrator condition.

Provider/search/query behavior around supplemental and remediation work remains
unchanged.

## Final Source Telemetry Parity Rules

Final-answer source citation telemetry calculation remains in the orchestrator.
AG-76C-FE only packages already-computed observer inputs through
`build_final_source_telemetry_inputs(...)`.

`record_final_evidence_snapshot(...)` still receives:

- the current `final_top_evidence` object;
- `list(seen_urls)`;
- `list(collected_images)`.

Source-class observability, runtime projection, official/canonical export, and
ControllerEvidenceLedger interpretation remain observer/ledger surfaces.

## Protected Surfaces Kept Closed

AG-76C-FE kept closed:

- final answer prose behavior;
- Author behavior and Author system prompt selection;
- Author prompt semantics beyond mechanical block source relocation;
- citation formatting and citation selection;
- final evidence selection semantics;
- provider routing, provider selection, provider depth, provider escalation,
  provider swaps, and new providers;
- query strategy and source-constraint repair;
- retrieval ranking/filtering behavior;
- source-class/currentness classifier semantics;
- candidate-fit semantics;
- Scrutineer behavior;
- Economist behavior;
- follow-up behavior;
- direct IRS hardcoding;
- live validation;
- raw/private data, DB rows, caches, logs, secrets, full traces, and output
  packets.

## Remaining Orchestrator Responsibilities

`pipeline_orchestrator.py` remains responsible for:

- computing existing phase-local runtime values;
- deciding whether supplemental/remediation paths run under existing behavior;
- calling provider/search/model surfaces already present before AG-76C-FE;
- splicing returned evidence strings into the existing Author prompt position;
- calling Author;
- computing final-answer source telemetry from the final report;
- passing builder-packaged snapshot inputs to existing observers;
- recording runtime trace, export, persistence, and outcome payloads.

It no longer owns final source-ID loops or final evidence block assembly for the
extracted seam.

## Line-Count Delta

`core/pipeline_orchestrator.py` line count:

- before AG-76C-FE: 7001
- after AG-76C-FE: 6973
- delta: -28 lines

The small line-count delta reflects replacing three duplicated loops with
structured calls while keeping compatibility plumbing and prompt placement in
the orchestrator.

## Demolition Ledger

1. Old block removed or replaced:
   final evidence/source-ID construction blocks at the initial, supplemental,
   remediation, Author evidence, and final snapshot handoff sites were replaced
   by builder calls.
2. New builder module/function contract:
   `core.final_evidence_bundle_builder` owns mechanical bundle construction,
   source-ID assignment, text block formatting, Author evidence packaging, and
   snapshot input packaging.
3. Old local source-ID loops removed or subordinated:
   `pipeline_orchestrator.py` no longer contains `next_source_id`, the local
   `unique_source_urls = {}` loop, or local `p["source_id"] = ...` assignment.
4. Behavior parity tests:
   `tests/test_ag76c_final_evidence_bundle_builder.py` proves final evidence
   order, source IDs, duplicate reuse, ordered sources, evidence block,
   cached prefix, Author evidence slice/block, telemetry/snapshot payloads,
   supplemental/remediation rebuilds, static orchestrator loop removal, and
   protected-surface import/call closure.
5. Remaining orchestrator responsibilities:
   prompt placement, model/provider execution, final report production,
   final-answer source telemetry calculation, trace/export/persistence, and
   compatibility handoff.
6. Next deletion target:
   runner-owned recovered/source-class candidate stream and remaining
   orchestrator compatibility plumbing around final evidence consumers.
7. Net complexity impact:
   one mechanical builder added; three duplicated source-ID/evidence rebuild
   blocks removed from the orchestrator; static ownership guard added.
8. Pipeline line-count delta:
   -28 lines in `core/pipeline_orchestrator.py`.

## Next Deletion Target

The next deletion target is not Author/citation behavior. The next safe target
is a runner-owned recovered/source-class candidate stream or another narrow
compatibility-plumbing seam that keeps ControllerEvidenceLedger and
AnswerContract as decision owners while trace/projection/export remain
observers.
