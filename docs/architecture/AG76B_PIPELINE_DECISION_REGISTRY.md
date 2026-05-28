# AG-76B Pipeline Decision Registry / Final Evidence Ownership Blueprint

Date: 2026-05-28

## Scope And Non-Goals

AG-76B is an Architecture Groove / Prove Mode registry and demolition-control
phase for the final evidence bundle and source-ID area of `pipeline_orchestrator.py`.

The goal is not immediate raw line deletion. The goal is to make the next
deletion safe and inevitable by naming the replacement owner, contract, parity
tests, protected surfaces, and old orchestrator responsibility to remove.

AG-76B does not change runtime behavior. It does not change final-answer prose,
Author behavior, citation formatting, citation selection, final evidence
selection semantics, provider routing, provider selection/depth/escalation,
query strategy, source-class/currentness classifier semantics, candidate-fit
semantics, prompt behavior, Scrutineer, Economist, follow-up behavior, live
validation, direct IRS handling, or broad `pipeline_orchestrator.py` logic.

The only code artifact added in AG-76B is the passive registry module
`core/pipeline_decision_registry.py`. It is not wired into runtime behavior.

## AG-75C Prerequisite Verification

Current local `main` contains AG-75C / PR #24:

```text
7777198 Merge pull request #24 from aidan600/codex/ag75c-local-authority-gate-retirement-audit
1991f6b Update AG-75C static guard expectations
041a5e6 Retire AG-75C recovered evidence local gate
```

Required AG-75C evidence was present before AG-76B edits:

- `docs/architecture/AG75C_LOCAL_AUTHORITY_GATE_RETIREMENT_AUDIT.md` exists.
- `core/recovered_evidence_visibility.py` defines
  `apply_controller_recovered_evidence_visibility(...)`.
- `core/pipeline_orchestrator.py` no longer defines
  `_apply_recovered_evidence_visibility(...)`.
- AG-75C explicitly names final evidence bundle construction, source ID
  assignment, evidence block assembly, Author handoff, and final source telemetry
  as the next major target.

AG-75C line of inheritance:

```text
Final evidence pool construction | core/pipeline_orchestrator.py around
deps.filter_top_evidence(...) and source ID assignment | Builds Author evidence
surface and source IDs locally | still local authority | ... | AG-76B/AG-76C
burn-down with explicit final evidence registry license.
```

## Pipeline Decision Registry

AG-76B adds `core/pipeline_decision_registry.py` with immutable dataclasses and
constants only:

- `PipelineDecisionRegistryEntry`
- `FinalEvidenceOwnershipResponsibility`
- `FinalEvidenceReplacementContract`
- `PIPELINE_DECISION_REGISTRY`
- `FINAL_EVIDENCE_OWNERSHIP_BLUEPRINT`
- `FINAL_EVIDENCE_REPLACEMENT_CONTRACT`
- `NEXT_EXTRACTION_RECOMMENDATION`

The registry is intentionally not imported by `pipeline_orchestrator.py`.

| decision_name | current_location | current_owner | target_owner | executor/helper | observer/export surface | protected risk | current coverage | status | next_action | priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `final_evidence_bundle_construction` | `core/pipeline_orchestrator.py` lines 5341-5370, 5941-5971, 6138-6171, and 6299-6317 | local `final_top_evidence` assembly | `core.final_evidence_bundle_builder` | `build_final_evidence_bundle(...)` | runtime trace projection and official/canonical export observe only | final answer, Author, citation formatting/selection, final evidence selection, provider/query/classifier/fit surfaces | source-class recovery trace, AG-74B/AG-74C ledger/export parity, AnswerContract handoff, AG-75C recovered visibility parity | blueprint only | AG-76C-FE replacement extraction | P0 |
| `source_id_assignment` | local `unique_source_urls`, `ordered_sources`, `next_source_id`, and `p["source_id"]` loops | `pipeline_orchestrator.py` URL-to-integer loop | `core.final_evidence_bundle_builder` | `assign_stable_source_ids(...)` | final answer source telemetry and source-class observability consume IDs | Author, citation formatting/selection, source identity | source-class recovery trace source-ID parity and source-binding diagnostics | blueprint only | AG-76C-FE replacement extraction | P0 |
| `author_evidence_handoff` | `author_evidence`, `author_evidence_block`, and prompt splice | `pipeline_orchestrator.py` | builder packages; Author consumes | `build_author_evidence_block(...)` | ledger/projection observe handoff outcomes | Author, citation formatting, final answer prose | existing final answer/citation parity tests | mapped | move packaging only; do not change prompt semantics | P0 |
| `final_source_telemetry` | final answer source telemetry, source survival counts, and final evidence mirror snapshot | orchestrator writes observed telemetry | observer/export surfaces after bundle output | trace/projection/export helpers | runtime trace projection, official/canonical export, evidence mirror | citation selection, final answer prose, trace schema churn | runtime trace projection and official/canonical export tests | observer boundary defined | keep telemetry observer-only | P1 |
| `recovered_evidence_visibility_boundary` | `core/recovered_evidence_visibility.py` | ControllerRecoveryDecision plus helper | Controller-approved candidate stream and final builder input | `apply_controller_recovered_evidence_visibility(...)` | AuthorityLifecycle and ControllerEvidenceLedger | candidate-fit semantics, final evidence selection behavior | AG-75C tests | moved in AG-75C | treat as input, not rewrite | P1 |
| `provider_search_allocation_execution` | controller provider allocation and recovery runner modules | ControllerRecoveryDecision | ControllerRecoveryDecision with bounded runner execution | source-class recovery runner | allocation custody/export projections | provider routing/selection/depth | AG-75A and AG-75A-Y tests | already Controller-authorized | no AG-76B change | P2 |
| `candidate_custody_disposition` | allocation custody and activation helpers | ControllerEvidenceLedger plus custody projection | ledger custody with builder input stream | allocation candidate activation helper | runtime trace projection/export | candidate fit and classifier semantics | AG-75A-Y/Z tests | subordinate candidate stream | feed AG-76C-FE as already-custodied input only | P1 |
| `recovery_retry_stop_provider_review_decision` | `core/controller_recovery_decision.py` | ControllerRecoveryDecision | ControllerRecoveryDecision | source-class recovery runner executes approved actions | runtime trace projection | provider routing, query generation, follow-up | AG-74D and AG-74F tests | Controller-owned | no AG-76B change | P2 |
| `trace_projection_export_attachment` | runtime trace projection and official/canonical export modules | observer/export only | observer/export only | `attach_passive_runtime_projection_traces(...)` | execution trace, export, diagnostics | trace schema churn, citation selection | AG-46C/AG-74C tests | must remain passive | add AG-76C-FE parity after extraction | P1 |
| `answer_contract_obligation_handoff` | `core/answer_contract_runtime_handoff.py` | AnswerContract | AnswerContract for obligations; builder consumes state only | `build_runtime_answer_contract_handoff(...)` | ControllerEvidenceLedger `AnswerContractUpdated` events | prompt, citation selection, final answer prose | AnswerContract runtime handoff tests | input state, not selector | do not make final builder decide obligations | P1 |

## Orchestrator Burn-Down Ledger

Already moved out of `pipeline_orchestrator.py` through AG-75C:

- `_apply_recovered_evidence_visibility(...)` deleted.
- Recovered candidate-pool construction now goes through
  `recovered_evidence_selection_candidates(...)`.
- Orchestrator no longer directly imports or calls
  `allocation_result_candidates_for_existing_selection_corridor(...)`.
- Orchestrator no longer directly calls
  `apply_recovered_evidence_visibility_boundary(...)`.
- The three old recovered-visibility call sites now call
  `apply_controller_recovered_evidence_visibility(...)`.

Still in `pipeline_orchestrator.py`:

- Initial `final_top_evidence` construction via `deps.filter_top_evidence(...)`.
- Recovered/Controller-selected evidence insertion handoff into the final bundle.
- Local URL-to-source-ID mapping and `ordered_sources` creation.
- `evidence_block` and `cached_prefix` assembly.
- Supplemental and remediation evidence rebuilds that repeat the same bundle and
  source-ID logic.
- `author_evidence` slicing and `author_evidence_block` packaging.
- Final evidence mirror snapshot and final source telemetry attachment points.

Pure plumbing remaining:

- Passing `all_passages`, `top_chunks`, complexity-derived `max_domain_chunks`,
  lifecycle trace, `current_date`, and `query` into the future builder.
- Passing builder outputs into existing Author prompt placement and observer
  helpers.

Authority still suspected in the orchestrator:

- The local final bundle is still the place where final evidence ordering,
  source identity, and Author-visible evidence surface are materially assembled.
- Final source telemetry can still be misread as custody authority if not
  interpreted through `ControllerEvidenceLedger`.

Next deletion/extraction target:

- `AG-76C-FE — Final Evidence Bundle / Source-ID Assignment Replacement Extraction`.

Expected line-count impact:

- Unknown until extraction, but three duplicated source-ID loops plus repeated
  block assembly should collapse into one builder handoff.

Tests needed before deletion:

- Source-ID parity for unique and duplicate URLs.
- `ordered_sources` parity for plausible and implausible domains.
- `evidence_block`, `cached_prefix`, and `author_evidence_block` exact text
  parity.
- Author precision slicing parity.
- Supplemental/remediation rebuild parity.
- Final evidence snapshot, source telemetry, runtime projection, and export
  parity.
- Static guard proving `pipeline_orchestrator.py` no longer owns
  `unique_source_urls` / `next_source_id` loops after AG-76C-FE.

AG-76C-FE is safe to open if it remains a parity-preserving extraction and keeps
Author/citation/final-answer/provider/query/classifier/fit behavior closed.

## Final Evidence / Source-ID Ownership Blueprint

| responsibility | decision owner | mechanical builder | observer/export surface | Author/citation consumer | remaining orchestrator handoff |
| --- | --- | --- | --- | --- | --- |
| Final evidence source collection | ControllerEvidenceLedger and Controller-approved recovery/allocation state | `core.final_evidence_bundle_builder` | runtime trace projection | Author receives packaged evidence only | pass `all_passages` and lifecycle state |
| Final evidence ordering | existing `filter_top_evidence` ordering contract until separately licensed | builder preserves current order | final evidence mirror snapshot | Author/citation consume stable ordered bundle | pass caps and dependency callables |
| Recovered/Controller-selected evidence insertion | ControllerRecoveryDecision and recovered evidence helper | builder calls existing helper | AuthorityLifecycle and ledger | Author sees only final packaged result | pass lifecycle trace |
| Source identity preservation | final evidence identity registry contract | builder | final source telemetry observes mapping | citation surfaces rely on IDs | consume immutable mapping output |
| Source ID assignment | final evidence identity registry contract | `assign_stable_source_ids(...)` | final answer source telemetry | Author evidence and Sources list consume assigned IDs | no local loop after AG-76C-FE |
| Stable source ordering | final evidence identity registry contract | builder | source-class observability telemetry | ordered Sources list preserves first URL occurrence | consume `ordered_sources` output |
| Author evidence block packaging | AnswerContract and existing Author prompt contract for consumption | builder | Author handoff telemetry observes only | Author prompt consumes packaged block unchanged | splice returned block into existing prompt position |
| Final source telemetry | ControllerEvidenceLedger custody for interpretation | trace/projection/export helpers | official/canonical export and final answer telemetry | no Author decision ownership | pass builder output to observers |
| Citation eligibility inputs | AnswerContract and ControllerEvidenceLedger | builder exposes source identity inputs | official/canonical export | citation selection remains closed | do not decide citation eligibility locally |
| Trace/export observation | ControllerEvidenceLedger for custody interpretation | runtime trace projection assembly | execution trace and export packets | no Author/citation behavior ownership | call existing observer helpers |
| ControllerEvidenceLedger references | ControllerEvidenceLedger | builder passes observable final evidence records | ledger trace and export | no direct behavior change | preserve ledger attachment points |
| AnswerContract obligation/posture references | AnswerContract | builder reads obligation state as input only | AnswerContract runtime handoff trace | Author prompt posture remains unchanged | continue existing handoff calls |

## Exact Old Responsibility To Replace

Replace the `pipeline_orchestrator.py` responsibility spanning:

- lines 5341-5370: initial sort/filter, recovered-evidence insertion, source-ID
  assignment, `ordered_sources`, `evidence_block`, and `cached_prefix`.
- lines 5941-5971: supplemental evidence refresh repeats the same bundle and
  source-ID assembly.
- lines 6138-6171: remediation evidence refresh repeats the same bundle and
  source-ID assembly.
- lines 6299-6317: `author_evidence`, `author_evidence_block`, and Sources-list
  prompt insertion consume the locally assigned source IDs.

This old responsibility also feeds final evidence mirror snapshot,
source-class observability, final answer source telemetry, and
official/canonical visibility export observations later in the pipeline.

## Replacement Owner / Module / Helper Contract

Recommended owner:

```text
core.final_evidence_bundle_builder
```

Recommended helpers:

```text
build_final_evidence_bundle(...)
assign_stable_source_ids(...)
build_author_evidence_block(...)
```

The builder is mechanical. It should not decide provider/search policy, source
class/currentness classification, candidate fit, prompt posture, Author behavior,
citation formatting, citation selection, or final answer prose.

## Input Contract

AG-76C-FE builder inputs should include:

- `all_passages`, already sorted or sortable by existing score semantics.
- `top_chunks`.
- complexity-derived `max_domain_chunks`.
- `deps.filter_top_evidence`.
- `deps.is_plausible_domain`.
- `active_source_class_recovery_lifecycle`.
- `current_date`.
- `query`.
- Author `precision_count`.

The builder may accept dependency callables so AG-76C-FE can preserve current
filtering and plausible-domain behavior without importing provider/query/Author
surfaces.

## Output Contract

AG-76C-FE builder outputs should include:

- `final_top_evidence` with stable `source_id` values assigned.
- `unique_source_urls`: URL to integer source-ID mapping.
- `ordered_sources`: current Sources-list lines, preserving first plausible URL
  occurrence and current formatting.
- `evidence_block`: current final evidence block string.
- `cached_prefix`: current cached-prefix seed string.
- `author_evidence`: precision-sliced final evidence.
- `author_evidence_block`: current Author precision evidence block string.
- trace/export observer payload inputs.

## Source-ID Assignment Requirements

- Assign the first integer ID when a URL first appears in `final_top_evidence`.
- Reuse the same integer ID for duplicate URLs.
- Write `source_id` on each final evidence passage exactly as current behavior
  does.
- Include only plausible domains in `ordered_sources` while preserving IDs for
  all URLs.
- Do not renumber after Author evidence slicing.
- Keep source IDs stable across `evidence_block`, `ordered_sources`,
  `author_evidence_block`, final answer telemetry, and projection/export
  observers.

## Final Evidence Ordering Requirements

- Preserve existing `deps.filter_top_evidence(...)` behavior.
- Preserve current score sorting before filtering.
- Preserve recovered-evidence reserve/replace output from
  `apply_controller_recovered_evidence_visibility(...)`.
- Preserve supplemental/remediation rebuild behavior.
- Do not change final evidence selection semantics in AG-76C-FE.

## Author Handoff Boundary

The replacement may package evidence strings and source lists. It may not change:

- Author prompt placement;
- Author system prompt selection;
- Author model/provider call;
- Author citation instructions;
- final answer prose behavior;
- citation formatting or citation selection.

The orchestrator should remain responsible only for splicing returned package
fields into the already-existing prompt shape until a later phase licenses more.

## Trace / Export Observer Boundary

Trace/projection/export surfaces observe final bundle output. They do not own
source identity assignment, final evidence selection, Author handoff behavior, or
citation behavior.

`ControllerEvidenceLedger` remains the custody interpreter. Final source counts
and export fields remain observations subordinate to ledger custody.

## Required Parity Tests For AG-76C-FE

Before deleting the old orchestrator loops, AG-76C-FE must add focused parity
tests proving:

1. Unique URLs receive source IDs `[1, 2, 3, ...]` in first final-evidence order.
2. Duplicate URLs reuse their first assigned source ID.
3. Implausible domains still receive source IDs but do not appear in
   `ordered_sources`.
4. `evidence_block` text matches the current `[Source N]`, title, URL, and
   1200-character excerpt formatting.
5. `cached_prefix` text matches current `<evidence_block>` plus date/query
   formatting.
6. `author_evidence` precision slicing remains unchanged for thin and non-thin
   bodies.
7. `author_evidence_block` text matches current formatting.
8. Supplemental evidence refresh produces the same rebuilt bundle and IDs.
9. Remediation evidence refresh produces the same rebuilt bundle and IDs.
10. `record_final_evidence_snapshot(...)` receives the same final evidence.
11. Final answer source telemetry keys remain unchanged.
12. Runtime trace projection and official/canonical export outputs remain
    schema-compatible.
13. Static guard confirms `pipeline_orchestrator.py` no longer contains the
    local `unique_source_urls` / `next_source_id` loops after extraction.

## Protected Surfaces Kept Closed

AG-76B kept closed:

- final answer prose behavior;
- Author behavior;
- citation formatting behavior;
- citation selection behavior;
- final evidence selection behavior;
- provider routing, selection, depth, escalation, new providers, provider swaps;
- query strategy/source-constraint repair;
- source-class/currentness classifier semantics;
- candidate-fit semantics;
- prompt behavior;
- follow-up behavior;
- Scrutineer and Economist behavior;
- live validation;
- direct IRS hardcoding;
- raw/private data, secrets, DB rows, caches, logs, full traces, and output
  packets;
- broad `pipeline_orchestrator.py` rewrite.

## Deletion Plan For AG-76C-FE

1. Add `core/final_evidence_bundle_builder.py` with a pure builder output
   dataclass and helper functions.
2. Port current source-ID and evidence-block formatting exactly into the helper.
3. Add parity tests before wiring the helper into `pipeline_orchestrator.py`.
4. Replace the initial final bundle block with one builder call.
5. Replace supplemental/remediation rebuild blocks with the same builder call.
6. Replace local Author evidence slicing/block assembly with builder output.
7. Keep prompt placement, Author behavior, final answer behavior, citation
   formatting/selection, provider/query/classifier/fit behavior unchanged.
8. Add static guard proving local source-ID loops are gone from the orchestrator.
9. Run targeted final evidence/source-ID, AnswerContract handoff, trace
   projection, official/canonical export, and final-answer/citation parity tests.

## Recommended Next Phase

Recommended next phase:

```text
AG-76C-FE — Final Evidence Bundle / Source-ID Assignment Replacement Extraction
```

AG-76C-FE should be licensed as a parity-preserving extraction only. It should
not change Author/citation/final-answer behavior, final evidence selection
semantics, provider/search/query behavior, classifier/currentness behavior, or
candidate-fit semantics.
