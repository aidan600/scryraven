# AG-76D-CIT Controller-Owned Citation / Source-list Handoff Contract

Date: 2026-05-31

Phase type: core authority transfer.

## Licensed protected surface

AG-76D-CIT opens only the citation/source-list handoff seam: final evidence
identity, source IDs, source-ID to URL/title/domain mapping, duplicate URL reuse
facts, ordered source-list identity, citation-eligible source references, final
citation observations, and references to final evidence bundle,
ControllerEvidenceLedger, AnswerContract/runtime handoff, and
AnalystAuthorHandoffState/Author prompt-input metadata.

Closed surfaces remain citation formatting, citation selection, final-answer
prose, Author prompt text, Analyst behavior, provider/model/search/query
behavior, source-class/currentness classifier behavior, candidate-fit semantics,
retrieval ranking/filtering, Economist/Scrutineer/follow-up behavior,
DB/session/SQLite/RunOutcome shape, package/CLI/env compatibility names, runtime
cache implementation, live validation, and source-specific hardcoding.

## Previously local/orchestrator-owned state

Before AG-76D-CIT, source IDs and ordered Sources-list lines were mechanically
built by `core.final_evidence_bundle_builder`, but the downstream citation
handoff posture remained split across local orchestrator variables and helper
outputs:

- `unique_source_urls`, `ordered_sources`, `final_top_evidence`,
  `evidence_block`, and `cached_prefix` came from the final evidence bundle;
- `author_evidence` and `author_evidence_block` were attached later for Author
  inputs;
- `_final_answer_source_citation_telemetry(...)` collected final answer citation
  observations in `pipeline_orchestrator.py`;
- `build_final_source_telemetry_inputs(...)` packaged observer inputs after the
  Author pass;
- `AnalystAuthorHandoffState` received selected/final evidence and ordered
  source counts, but no dedicated citation/source-list handoff contract owned the
  complete seam.

## New Controller-owned contract/state

AG-76D-CIT adds `core.citation_source_handoff_contract` with a passive,
deterministic `CitationSourceHandoffState`. The state contains:

- `SourceIdentityDescriptor` for final source identity, source-ID mapping, and
  duplicate URL reuse facts;
- `OrderedSourceListDescriptor` for ordered source-line identity and hash;
- `CitationEligibilityDescriptor` for final, selected, and Author evidence refs
  plus citation-eligible source IDs;
- `CitationObservationDescriptor` for already-computed final answer citation
  telemetry and observation refs;
- `AuthorSourceInputDescriptor` for evidence block, cached prefix, and Author
  evidence block identity without prompt text;
- references to final evidence bundle, ControllerEvidenceLedger-compatible
  final-evidence snapshot state, AnswerContract/runtime handoff, and
  AnalystAuthorHandoffState.

The contract is production-active as a narrow handoff adapter: the orchestrator
builds the state from already-computed values, consumes
`execute_citation_source_handoff(...)`, and adds one sanitized trace fragment.
It does not assign source IDs, format source lines, select citations, alter
prompt text, or rewrite final-answer behavior.

## Mechanical executor/handoff boundary

The final evidence bundle builder remains the mechanical executor for stable
source-ID assignment, URL deduplication/reuse, ordered source-line construction,
`evidence_block`, `cached_prefix`, and Author evidence slicing/block assembly.
The new citation/source contract copies those already-computed values, exposes
Controller-owned identity/refs, and returns legacy-compatible
`unique_source_urls`, `ordered_sources`, and final citation telemetry.

Final citation observation scanning remains the existing orchestrator helper.
AG-76D-CIT packages the result; it does not change the scanner or the citation
syntax it recognizes.

## Relationship to final evidence bundle builder

`FinalEvidenceBundle` remains the source of final evidence, source IDs,
ordered source lines, evidence block, and cached prefix. AG-76D-CIT stores a
`final_evidence_bundle_ref` with counts and hashes/lengths sufficient to tie the
citation/source-list handoff back to that builder output without duplicating the
builder's decisions.

## Relationship to ControllerEvidenceLedger

The contract stores a ControllerEvidenceLedger-compatible reference describing
final evidence snapshot visibility. It does not change ledger custody,
disposition, selected evidence, or final evidence decisions.

## Relationship to AnswerContract/runtime handoff

When runtime AnswerContract state is available, AG-76D-CIT stores a sanitized
reference to it through the same `to_controller_state`, `to_trace_fragment`, or
`execution_trace_fragment` conventions used by nearby AG-76D contracts. It does
not change AnswerContract decision semantics.

## Relationship to AnalystAuthorHandoffState

AG-76D-CIT references `AnalystAuthorHandoffState` and copies the sanitized
Author prompt-input metadata ref from it. Prompt text remains excluded. The
relationship proves the citation/source-list handoff and the Author
source-input metadata point at the same final/selected/Author evidence surfaces
without changing Author prompt behavior.

## Behavior preserved

AG-76D-CIT preserves:

- source IDs;
- duplicate URL source-ID reuse/deduping;
- ordered source lines;
- `evidence_block` and `cached_prefix`;
- Author evidence/source inputs;
- final citation observations;
- final-answer text/prose;
- citation formatting and citation selection;
- existing trace fields, with the new trace additive only;
- DB/session/SQLite/RunOutcome shapes;
- provider/model/search/query behavior;
- cache behavior and compatibility names.

## Production-active vs shadow-only paths

Production-active:

- `CitationSourceHandoffState` construction in `pipeline_orchestrator.py` after
  final citation telemetry exists;
- mechanical execution envelope returning legacy-compatible source/citation
  handoff values;
- additive `citation_source_handoff_contract` trace fragment.

Shadow-only: none introduced by this phase.

Test-only: static import/protected-surface guards and offline parity fixtures in
`tests/test_ag76d_cit_controller_owned_citation_source_handoff_contract.py`.

Inactive replacement infrastructure: none.

## Tests added/updated

Added `tests/test_ag76d_cit_controller_owned_citation_source_handoff_contract.py`
covering source-ID parity, duplicate URL reuse, ordered-source parity, Author
source-input identity, final citation observation parity, Controller-owned
visibility, ledger/AnswerContract compatibility, AnalystAuthorHandoff
integration, trace compatibility, static protected-import guard, orchestrator
authority guard, protected-surface guard, no-live/product-path guard, and final
answer fixture parity via stable handoff inputs when provider-generated final
text is not fixture-stable offline.

## Trace compatibility and additive visibility

The new trace packet key is `citation_source_handoff_contract`. It is sanitized,
contains no raw prompt text, provider payloads, DB rows, or live output packets,
and is additive. Existing trace fields such as final answer source telemetry
remain present and unchanged.

## Citation formatting/selection non-change note

The contract explicitly records `did_change_citation_formatting = False` and
`did_change_citation_selection = False`. It has no citation formatter or
citation selector and imports no Author, prompt, provider, search, Economist,
Scrutineer, follow-up, DB/session, RunOutcome, cache, or live-validation
surfaces.

## Final-answer non-change note

The contract stores citation/source-list handoff identity after the final answer
has been generated and citation telemetry has been observed. It cannot change
final-answer prose or Author prompt text.

## Protected surfaces kept closed

AG-76D-CIT keeps closed provider/search/query/model behavior, final evidence
selection, citation formatting/selection, Author behavior and prompt text,
Analyst behavior, Economist, Scrutineer, follow-up, DB/session/RunOutcome/cache,
live validation, and source-specific hardcoding.

## Stop conditions

Stop instead of extending AG-76D-CIT if citation formatting/selection,
final-answer prose, Author prompt text, source-ID assignment, source ordering,
final evidence selection, provider/search/query/model behavior,
ControllerEvidenceLedger or AnswerContract decision semantics,
DB/session/SQLite/RunOutcome shape, live validation, LLM caching, package/env
renaming, source-specific hardcoding, or a broad orchestrator rewrite becomes
necessary.

## Recommended next phase

Recommended next phase: **AG-76D-ECO — Controller-Owned Economist Handoff
Contract**.

Rationale: after AG-76D-CIT, the citation/source-list handoff is
Controller-visible and contract-owned. Economist preflight/output/analysis
handoff remains a higher-risk core authority seam than AG-77A follow-on design
because it can affect analysis material, Author notes, and quantitative packet
posture while still being separable from citation formatting and provider/search
behavior.
