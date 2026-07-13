Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG52B_OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_VISIBILITY_CLASSIFICATION).

# AG-52B Official/Canonical Recovery Candidate Visibility Classification

## Phase Purpose

AG-52B classified and narrowly repaired the allowed-artifact visibility layer
before AG-52A evidence acceptance. The product-quality goal was to distinguish
true provider zero candidates from candidate visibility/export gaps, and to
expose compact sanitized candidate visibility fields for admitted
official/current/canonical recovery slots.

## Licensed Protected Surface

Opened:

- candidate acquisition and sanitized candidate visibility before evidence
  acceptance for admitted official/current/canonical recovery slots.

Still closed:

- provider routing, provider selection, provider depth/search-depth, provider
  escalation, and provider pricing policy;
- query wording/generation and prompt behavior;
- broad returned-source classification outside this recovery slot;
- evidence acceptance/source-fit/ranking behavior beyond preserving AG-52A
  handoff fields;
- citation survival/selection, Author behavior, final-answer wording, and new
  provider integration;
- source-specific PostgreSQL hacks.

## Source-Layer Boundary Handling

Referenced Project Source context was provided inline in the prompt.

Repo files read first:

- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/history/validation/AG52A_OFFICIAL_CANONICAL_RECOVERY_EVIDENCE_ACCEPTANCE_SOURCE_FIT.md`
- `docs/history/validation/AG50F_OFFICIAL_CANONICAL_CANDIDATE_ACQUISITION_LIVE_CLASSIFICATION.md`
- `docs/history/validation/AG50E_OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_ACQUISITION_REPAIR.md`

Additional relevant repo files inspected:

- `core/official_canonical_recovery_candidate_acquisition.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/recovered_evidence_visibility.py`
- `core/source_class_recovery.py`
- `core/source_class_recovery_diagnostics.py`
- `core/source_class_recovery_executor.py`
- `core/source_class_recovery_lifecycle.py`
- `proplex/__main__.py`
- focused AG-50A/B/C/D/E, AG-52A, source-class recovery, diagnostics, and
  runtime projection tests.

Local packets:

- `output/ag50f_output_quality_review_packet.md` was available.
- `output/ag52a_output_quality_review_packet.md` was available.
- `output/ag52b_output_quality_review_packet.md` was created and remains local
  and ignored.

No Project Source files were assumed to exist in the repo unless repo-tracked.

GitHub/repo state verified before work:

- `git switch main`: already on `main`.
- `git pull --ff-only origin main`: already up to date.
- `git status -sb`: clean `main`.
- `git log --oneline -12`: top commit was
  `cd370a8 Merge pull request #91 ... AG-52A`.
- `git rev-parse HEAD`: `cd370a80b26f48b28fe3cea5be137d4caa13b3c9`.
- `git ls-remote origin refs/heads/main`: matched local HEAD.

## Rule 0 Failure Analysis

General failure class:

- Live official/canonical recovery execution could not distinguish provider zero
  candidates from candidate visibility/export gaps before evidence acceptance.

Blast radius:

- Source-class recovery candidate acquisition visibility and allowed-artifact
  export for admitted official/current/canonical recovery slots.

Rules applied:

- The patch was scoped to already-admitted official/current/canonical recovery
  slots.
- It did not change provider behavior, query generation, prompts, evidence
  acceptance behavior, citation behavior, Author behavior, or final-answer
  behavior.
- Product-quality success was clear allowed-artifact classification of
  candidate acquisition/visibility before AG-52A acceptance.

Valid cases protected:

- ordinary source-class recovery unrelated to official/current/canonical
  obligations;
- source-class recovery paths with true zero candidates;
- existing AG-52A acceptance/source-fit behavior;
- ordinary provider diagnostics;
- final citation and Author behavior;
- local packet safety and redaction boundaries.

## AG-50F Baseline

AG-50F observed:

- `recovered_result_count=11`
- `candidate_return_status=candidates_returned`
- `official_canonical_candidate_visible=false`
- `accepted_or_readable_official_or_canonical_count=0`
- `final_evidence_official_or_canonical_count=0`
- `final_citation_official_or_canonical_count=0`
- final cited URLs were arXiv PDFs, not PostgreSQL documentation.

AG-50F could not expose returned candidate URLs/domains, so it could not prove
whether PostgreSQL documentation was returned and rejected or never returned.

## AG-52A Baseline

AG-52A repaired offline source-fit/acceptance for already-returned
official/canonical candidates. Its live PostgreSQL run did not exercise that
repaired seam:

- `recovered_result_count=0`
- `candidate_return_status=zero_candidates`
- `zero_candidate_blocker_kind=candidate_visibility_not_exported`
- `recovered_candidate_source_fit_status=not_evaluated`
- final citation remained arXiv-only.

Interpretation: the next live layer was upstream of AG-52A evidence acceptance:
candidate acquisition or sanitized candidate visibility.

## Implementation Hypothesis

The exact bottleneck was that provider diagnostics could already indicate
source-class recovery provider results, while the exported/usable recovered
candidate count could be zero. The allowed report then labeled that case
`zero_candidates`, conflating a true provider-zero result with a candidate
visibility/export gap.

The likely repair was a pure helper/export projection change:

- preserve safe provider result/accepted/new-source counts;
- add candidate acquisition result status;
- add candidate visibility export status and blocker kind;
- preserve AG-52A source-fit handoff fields;
- add capped recovered candidate domain preview when recovered candidate URLs
  are already available as sanitized runtime artifacts.

## Code-Level Diagnosis

Relevant existing seams:

- `execute_source_class_recovery_action` appends usable recovered passages and
  records provider diagnostics.
- `build_official_canonical_recovery_candidate_acquisition_trace` combines
  lifecycle counts, provider diagnostics, and execution result counts.
- `build_official_canonical_recovery_visibility_export` renders allowed report
  fields.
- `build_recovery_source_quality_diagnostics` already sees recovered candidate
  URLs, so capped domains can be exported without raw payloads or result bodies.

AG-52B found that `recovered_result_count=0` plus provider-positive diagnostics
needed a separate visibility status instead of being treated as a true
zero-candidate outcome.

## Visibility/Export Change Made

Changed modules:

- `core/official_canonical_recovery_candidate_acquisition.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/source_class_recovery.py`
- `core/source_class_recovery_lifecycle.py`

New sanitized fields:

- `candidate_acquisition_provider_result_count`
- `candidate_acquisition_provider_accepted_url_count`
- `candidate_acquisition_provider_new_source_count`
- `candidate_acquisition_result_status`
- `candidate_visibility_export_status`
- `candidate_visibility_blocker_kind`
- `recovered_candidate_domain_preview`

Behavior:

- True provider-zero execution remains `candidate_return_status=zero_candidates`
  with `zero_candidate_blocker_kind=provider_returned_zero_results`.
- Provider-positive/export-zero execution becomes
  `candidate_return_status=candidate_visibility_not_exported`, not
  `zero_candidates`.
- Provider-positive/export-visible execution reports
  `candidate_acquisition_result_status=provider_results_returned` and
  `candidate_visibility_export_status=visible`.
- The AG-52A source-fit handoff fields are preserved and not rewritten.
- Candidate domains are capped and sanitized; full URLs, titles, bodies, raw
  traces, and provider payloads are not exported.

This does not hardcode PostgreSQL, the exact MVCC query, or any forced URL.

## Why The Patch Is Inside The Licensed Surface

The patch only projects already-existing safe runtime facts for the admitted
source-class recovery slot. It does not retrieve, route providers, choose depth,
alter query generation, change prompts, rank/filter evidence, alter citation
selection, or change Author/final-answer behavior.

## Tests Added Or Changed

Added:

- `tests/test_official_canonical_recovery_candidate_visibility_ag52b.py`

Changed:

- `tests/test_source_class_recovery_trace.py` to include the new domain-preview
  lifecycle field.

Coverage:

- true zero-candidate classification;
- candidates-returned visibility;
- provider-positive candidate visibility gap;
- official/canonical candidate visibility via safe counts;
- AG-52A source-fit handoff preservation;
- no-admitted-slot negative control;
- raw provider payload redaction;
- protected-surface guard;
- capped recovered candidate domain preview.

## Mid-Phase Review Gates

Gate 1 - Reconnaissance:

- Repo was clean on updated `main` at the expected AG-52A merge.
- Existing seams were executor result attachment, candidate acquisition helper,
  recovery quality diagnostics, and visibility export.
- Implementation path was pure helper/export diagnostics.
- `pipeline_orchestrator.py` was expected to need no change and was not changed.
- AG-52A live showed the next layer was upstream of evidence acceptance.

Gate 2 - Pre-implementation:

- Bottleneck believed present: provider-positive/export-zero cases were
  misreported as `zero_candidates`.
- Decision-tree branch: candidate visibility/export gap before AG-52A
  source-fit.
- Fix attempted: add candidate acquisition result status, visibility export
  status/blocker, provider result counts, and tests.
- Stop packet would be required for provider/depth/query/citation/Author
  behavior or raw provider payload access; none was needed.

Gate 3 - Post-implementation self-review:

- The change addressed provider-zero versus visibility-gap classification.
- It stayed inside the licensed surface.
- No protected-surface drift occurred.
- `pipeline_orchestrator.py` gained no logic.
- Unknowns are preserved for no-admission/non-executed paths.
- Positive, negative-control, unknown-preservation, and hard-stop tests exist
  where relevant.

Gate 4 - Validation decision:

- Live validation was used because AG-52B exists to classify a live
  candidate-visibility layer.
- Exact query:
  `Explain how PostgreSQL MVCC works, why it improves read/write concurrency, and what tradeoffs it creates. Do not assume the reader is a database expert.`
- ProPlex live runs used: 2 of 2.
- First run exposed an in-scope domain-visibility ambiguity after provider
  counts became visible.
- Second run was used only after adding capped domain preview and passing
  focused tests.
- Independent source checks used: 0 of 1, because AG-50F already established
  PostgreSQL docs as the canonical baseline.
- Local packet: `output/ag52b_output_quality_review_packet.md`.

Gate 5 - Final recommendation:

- Phase result: visibility/classification link repaired and live layer
  classified.
- Next failure layer: existing-provider acquisition/depth or returned-candidate
  source-class fit before AG-52A evidence acceptance.
- Next protected surface to open should be scoped to acquisition/depth/search
  strategy or returned-candidate source-class fit. Do not open citation/Author
  behavior yet.
- Phase is merge-ready after review.
- Merge was not performed.

## Live Validation Result

First post-change live run:

- `recovered_result_count=5`
- `accepted_url_count=1`
- `candidate_acquisition_provider_result_count=6`
- `candidate_acquisition_result_status=provider_results_returned`
- `candidate_visibility_export_status=visible`
- `candidate_return_status=candidates_returned`
- `official_canonical_candidate_visible=false`
- domain preview unavailable
- citations: `https://arxiv.org/pdf/1201.0228`,
  `https://arxiv.org/pdf/1208.4179`

Second post-change live run:

- `recovered_result_count=12`
- `accepted_url_count=2`
- `recovered_candidate_domain_preview=arxiv.org`
- `candidate_acquisition_provider_result_count=6`
- `candidate_acquisition_provider_accepted_url_count=2`
- `candidate_acquisition_provider_new_source_count=2`
- `candidate_acquisition_result_status=provider_results_returned`
- `candidate_visibility_export_status=visible`
- `candidate_return_status=candidates_returned`
- `official_canonical_candidate_visible=false`
- `recovered_candidate_source_fit_status=not_evaluated`
- `final_citation_official_or_canonical_count=0`
- `likely_next_failure_layer=candidate_returned_no_official_canonical_visible`
- `next_failure_layer=canonical_candidate_returned_not_accepted`

Final cited URLs:

- `https://arxiv.org/html/2605.19988v1`
- `https://arxiv.org/pdf/1901.01973`

## Before / After Result

Before:

- AG-52A live conflated `recovered_result_count=0` with
  `candidate_visibility_not_exported`.
- Candidate/provider result counts and candidate domains were insufficient to
  classify the live layer.

After:

- Provider result counts and candidate acquisition status are visible.
- Provider-positive/export-zero no longer reports `zero_candidates`.
- Capped candidate domains are visible.
- The final live run shows recovered domains as `arxiv.org`, not PostgreSQL
  official documentation.
- AG-52A source-fit remains not evaluated because no official/canonical
  recovered candidate reached that handoff.

## Commands And Results

- `git switch main`: already on `main`.
- `git pull --ff-only origin main`: already up to date.
- `git status -sb`: clean before branching.
- `git log --oneline -12`: confirmed AG-52A merge at top.
- `git rev-parse HEAD`: `cd370a80b26f48b28fe3cea5be137d4caa13b3c9`.
- `git ls-remote origin refs/heads/main`: matched local HEAD.
- `git switch -c codex/ag52b-official-canonical-recovery-candidate-visibility-classification`: branch created.
- `py -m pytest --basetemp C:\tmp\ag52b-pytest tests\test_official_canonical_recovery_candidate_visibility_ag52b.py`: 7 passed.
- `py -m pytest --basetemp C:\tmp\ag52b-pytest tests\test_official_canonical_recovery_candidate_acquisition_ag50e.py tests\test_official_canonical_recovery_visibility_export_ag50c.py tests\test_official_canonical_recovery_evidence_acceptance_ag52a.py`: 32 passed.
- `py -m pytest --basetemp C:\tmp\ag52b-pytest tests\test_official_canonical_recovery_execution_dispatch_ag50d.py tests\test_source_class_recovery_executor.py tests\test_source_class_recovery_lifecycle.py tests\test_source_class_recovery_trace.py tests\test_source_class_recovery_diagnostics_l1.py`: 47 passed.
- Initial projection path typo:
  `tests\test_runtime_trace_projection_assembly.py` did not exist, so 0 tests
  were collected.
- Corrected projection/admission slice:
  `py -m pytest --basetemp C:\tmp\ag52b-pytest tests\test_official_canonical_recovery_query_acquisition_ag50a.py tests\test_official_canonical_recovery_execution_admission_ag50b.py tests\test_runtime_trace_projection_assembly_ag46c.py tests\test_planned_observed_diagnostics.py`: 70 passed.
- After domain-preview patch:
  `py -m pytest --basetemp C:\tmp\ag52b-pytest tests\test_official_canonical_recovery_candidate_visibility_ag52b.py tests\test_ag15_source_class_recovery_quality_diagnostics.py tests\test_source_class_recovery_trace.py tests\test_source_class_recovery_executor.py tests\test_official_canonical_recovery_visibility_export_ag50c.py`: 51 passed.
- Final focused slice:
  `py -m pytest --basetemp C:\tmp\ag52b-pytest tests\test_official_canonical_recovery_candidate_visibility_ag52b.py tests\test_official_canonical_recovery_evidence_acceptance_ag52a.py tests\test_official_canonical_recovery_candidate_acquisition_ag50e.py tests\test_official_canonical_recovery_visibility_export_ag50c.py tests\test_official_canonical_recovery_execution_dispatch_ag50d.py tests\test_official_canonical_recovery_query_acquisition_ag50a.py tests\test_official_canonical_recovery_execution_admission_ag50b.py tests\test_source_class_recovery.py tests\test_source_class_recovery_executor.py tests\test_source_class_recovery_lifecycle.py tests\test_source_class_recovery_trace.py tests\test_source_class_recovery_diagnostics_l1.py tests\test_ag15_source_class_recovery_quality_diagnostics.py tests\test_runtime_trace_projection_assembly_ag46c.py`: 189 passed.
- `py -m ruff check core tests`: passed.
- `git diff --check`: passed with line-ending warnings only.
- `git diff --cached --check`: passed.
- `py -m pytest --basetemp C:\tmp\ag52b-pytest`: 1655 passed, 1 failed,
  1 deselected. The failure was
  `tests/test_pytest_tmp_path_hardening.py::test_tmp_path_uses_workspace_local_base`
  because the explicit `--basetemp` intentionally used `C:\tmp\ag52b-pytest`
  rather than `.pytest-tmp`.

## Local Packet Safety

Local packet:

- `output/ag52b_output_quality_review_packet.md`

Required checks:

- `git check-ignore -v output/ag52b_output_quality_review_packet.md`
- `git ls-files output`

The packet must remain untracked and must not be committed.

## Remaining Failure Layer

The remaining live failure layer is no longer candidate-count visibility.
Allowed artifacts show the provider returned candidates, recovered candidate
domains were visible, and the capped recovered domain preview was `arxiv.org`.
No official/current/canonical candidate reached AG-52A source-fit.

Next licensed surface recommendation:

- open a scoped phase for existing-provider acquisition/depth/search strategy
  or returned-candidate source-class fit before AG-52A evidence acceptance.
- keep citation survival/selection and Author/final-answer behavior closed until
  an official/current/canonical candidate becomes accepted/readable or final
  evidence contains it but citations omit it.

## Protected-Surface Confirmation

No code changed:

- `core/pipeline_orchestrator.py`

No changes were made to:

- providers, routing, depth, escalation, or pricing;
- query generation or prompt behavior;
- evidence acceptance/source-fit/ranking behavior;
- citation survival/selection;
- Economist, Analyst, Author, Scrutineer, or final-answer behavior;
- source-specific PostgreSQL handling.

Merge was not performed.
