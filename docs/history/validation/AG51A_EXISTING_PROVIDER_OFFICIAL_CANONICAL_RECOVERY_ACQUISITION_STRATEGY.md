Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG51A_EXISTING_PROVIDER_OFFICIAL_CANONICAL_RECOVERY_ACQUISITION_STRATEGY).

# AG-51A Existing-Provider Official/Canonical Recovery Acquisition Strategy

## Phase Purpose

AG-51A repaired one recovery-only acquisition/search strategy seam for the
already-admitted official/current/canonical recovery slot. The product-quality
goal was to improve the chance that existing providers acquire the right
official/canonical candidate before AG-52A evidence acceptance/source-fit.

## Licensed Protected Surface

Opened:

- existing-provider recovery acquisition/depth/search strategy for already
  admitted official/current/canonical recovery slots.

Still closed:

- new provider integration;
- provider swap or broad provider routing;
- ordinary/default retrieval behavior;
- broad query generation outside this recovery path;
- prompt behavior;
- broad returned-source classification;
- evidence acceptance/ranking beyond a tiny sanity guard;
- citation survival/selection, Author behavior, and final-answer behavior;
- source-specific PostgreSQL hacks.

## Source-Layer Boundary Handling

Referenced Project Source context was provided inline in the prompt.

Repo files read first:

- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/history/validation/AG52B_OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_VISIBILITY_CLASSIFICATION.md`
- `docs/history/validation/AG52A_OFFICIAL_CANONICAL_RECOVERY_EVIDENCE_ACCEPTANCE_SOURCE_FIT.md`
- `docs/history/validation/AG50F_OFFICIAL_CANONICAL_CANDIDATE_ACQUISITION_LIVE_CLASSIFICATION.md`
- `docs/history/validation/AG50E_OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_ACQUISITION_REPAIR.md`

Additional relevant repo files inspected:

- `core/official_canonical_recovery_query_acquisition.py`
- `core/official_canonical_recovery_candidate_acquisition.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/source_class_recovery.py`
- `core/source_class_recovery_executor.py`
- `core/source_class_recovery_lifecycle.py`
- `core/source_class_recovery_diagnostics.py`
- `core/recovered_evidence_visibility.py`
- `core/official_canonical_recovery_execution_admission.py`
- `core/pipeline_orchestrator.py`, read only to verify the existing adapter
  attachment point.
- focused AG-50A/B/C/D/E, AG-52A/B, source-class recovery, diagnostics, and
  runtime projection tests.

Local packets:

- `output/ag50f_output_quality_review_packet.md` was available.
- `output/ag52a_output_quality_review_packet.md` was available.
- `output/ag52b_output_quality_review_packet.md` was available.
- `output/ag51a_output_quality_review_packet.md` was created and remains local
  and ignored.

No Project Source files were assumed to exist in the repo unless repo-tracked.

GitHub/repo state verified before work:

- `git switch main`: already on `main`.
- `git pull --ff-only origin main`: already up to date.
- `git status -sb`: clean `main`.
- `git log --oneline -12`: top commit was
  `7421fd4 Merge pull request #92 ... AG-52B`.
- `git rev-parse HEAD`: `7421fd4df2758b48abb331adfcd00aca745104b8`.
- `git ls-remote origin refs/heads/main`: matched local HEAD.

Branch:

- `codex/ag51a-existing-provider-official-canonical-recovery-acquisition-strategy`

## Rule 0 Failure Analysis

General failure class:

- Existing provider recovery returns candidates, but not the required
  official/current/canonical candidate for the admitted source-trust
  obligation.

Blast radius:

- Source-class recovery acquisition/search strategy for admitted
  official/current/canonical recovery slots.

Rules applied:

- The repair was scoped to the already-admitted official/current/canonical
  recovery path.
- The repair did not change ordinary provider routing, broad query generation,
  prompts, evidence acceptance/ranking, citation behavior, Author behavior, or
  final-answer behavior.
- Product-quality success would be movement of official/current/canonical
  candidates into the recovered candidate set and allowed artifacts.
- The source-class-fit sanity guard was a preflight guard, not the main repair.

Valid cases protected:

- ordinary retrieval with no official/current/canonical obligation;
- ordinary source-class recovery unrelated to official/canonical obligations;
- source-class recovery where secondary sources are appropriate;
- provider-cost/depth increases outside the recovery slot;
- broad provider routing or default retrieval behavior;
- citation/Author behavior.

## Baselines

AG-50F:

- `recovered_result_count=11`
- `candidate_return_status=candidates_returned`
- `official_canonical_candidate_visible=false`
- `accepted_or_readable_official_or_canonical_count=0`
- `final_evidence_official_or_canonical_count=0`
- `final_citation_official_or_canonical_count=0`
- final cited URLs were arXiv PDFs, not PostgreSQL docs
- returned candidate URLs/domains were unavailable

AG-52A:

- Offline fixtures showed returned official/canonical candidates can now be
  source-fit recognized and preserved into accepted/readable evidence.
- Live: `recovered_result_count=0`
- Live: `candidate_return_status=zero_candidates`
- Live: `zero_candidate_blocker_kind=candidate_visibility_not_exported`
- Live: `recovered_candidate_source_fit_status=not_evaluated`
- final citation remained arXiv-only

AG-52B:

- Candidate/provider counts became visible.
- Existing provider returned candidates.
- `recovered_candidate_domain_preview=arxiv.org`
- `official_canonical_candidate_visible=false`
- `recovered_candidate_source_fit_status=not_evaluated`
- final citations remained arXiv-only

Interpretation:

- The next live layer was acquisition/search strategy, not AG-52A evidence
  acceptance or citation survival.

## Implementation Hypothesis

The recovery query strategy was too weak and too single-variant. In particular,
AG-52B showed a broad `canonical documentation PostgreSQL` preview, which lost
the target technical concept and still surfaced arXiv candidates. The expected
first repair was a generic documentation acquisition profile for the admitted
canonical technical documentation path.

## Code-Level Diagnosis

Relevant seams:

- `apply_official_canonical_recovery_query_acquisition` adds recovery-only
  source-seeking queries when a required official/current/canonical source
  obligation is unsatisfied.
- `record_source_class_recovery_lifecycle` turns the approved recommendation
  into one existing `source_class_recovery` action.
- `execute_source_class_recovery_action` executes the existing provider path
  with the approved query list, provider role, provider list, and search depth.
- `build_recovery_source_quality_diagnostics` and AG-52B export helpers expose
  sanitized candidate domains/counts.

The weak point was upstream of provider execution: one
`canonical documentation` query could satisfy the old intent guard and prevent
the recovery path from adding stronger generic documentation variants.

## Acquisition/Search Strategy Change Made

Changed:

- `core/official_canonical_recovery_query_acquisition.py`

Behavior:

- A lone `canonical documentation` query no longer completes the canonical
  technical documentation acquisition profile.
- The recovery-only helper adds generic variants:
  - `official documentation <subject>`
  - `reference documentation <subject>`
- The subject builder now preserves entity plus topic when both are available,
  such as `PostgreSQL MVCC`, rather than selecting only a terse primary entity.

Unchanged:

- existing provider role;
- provider selection;
- provider package/integration;
- search depth;
- ordinary retrieval/query behavior;
- prompts;
- returned-source classification beyond existing sanity guard coverage;
- evidence acceptance/ranking;
- citation selection;
- Author/final-answer behavior.

No PostgreSQL domain, exact MVCC URL, or forced citation was hardcoded.

## Why The Change Is Inside Scope

The patch changes only the generic recovery query list for already-admitted
official/current/canonical obligations. It does not call providers, choose new
providers, alter provider routing, alter ordinary retrieval, inspect secrets,
rank/filter evidence, or affect final synthesis/citation behavior.

## Source-Class-Fit Sanity Guard

Offline sanity guard:

- `tests/test_official_canonical_recovery_acquisition_strategy_ag51a.py::test_ag51a_source_class_fit_sanity_guard_recognizes_canonical_docs`

Result:

- Existing source-class helpers recognize a clear docs/reference/manual
  candidate as `primary_source_documents`.

No broad returned-source classification repair was needed or attempted.

## Tests Added Or Changed

Added:

- `tests/test_official_canonical_recovery_acquisition_strategy_ag51a.py`

Changed:

- `tests/test_official_canonical_recovery_query_acquisition_ag50a.py`

Coverage:

- positive official/canonical acquisition strategy for an admitted canonical
  technical documentation obligation;
- weak `canonical documentation` query no longer blocks official/reference
  documentation variants;
- existing full official/reference profile is not duplicated;
- fixture candidate-domain movement from secondary/arXiv to official docs when
  the existing provider sees the new recovery query;
- secondary-only candidates remain a non-success and do not masquerade as
  official/canonical;
- no-obligation/no-admitted-slot negative control;
- source-class-fit sanity guard;
- provider/depth preservation;
- provider-surface and protected-surface static guards.

## Mid-Phase Review Gates

Gate 1 - Reconnaissance:

- Repo was clean and updated at the expected AG-52B merge.
- Existing seams were query acquisition, lifecycle action creation, executor
  dispatch, and sanitized visibility export.
- Implementation path was a recovery-only query strategy helper change.
- `pipeline_orchestrator.py` was expected to need no change and was not
  changed.
- AG-52B showed the next live layer was acquisition/search strategy rather than
  evidence acceptance.

Gate 2 - Pre-implementation:

- Bottleneck believed present: a weak/broad single-variant canonical docs query
  allowed existing providers to return academic/secondary candidates.
- Decision-tree branch: existing-provider acquisition/search strategy repair.
- Fix attempted: add generic official/reference documentation query variants
  and preserve entity+topic subject specificity.
- Source-fit sanity guard: clear docs/reference/manual candidate must be
  recognized by existing helpers.
- Stop packet would be required for new providers, provider swap, broad query
  generation, source-specific PostgreSQL handling, raw provider payloads,
  evidence acceptance, citation, Author, or final-answer changes.

Gate 3 - Post-implementation self-review:

- The change addressed the intended acquisition/search seam.
- It stayed inside the licensed surface.
- No protected-surface drift occurred.
- `pipeline_orchestrator.py` gained no new domain decision logic.
- Unknown/non-success cases were preserved rather than backfilled.
- Positive, negative-control, source-class-fit sanity, unknown/no-obligation,
  and protected-surface tests exist.

Gate 4 - Validation decision:

- One post-change live validation run was used because offline fixtures cannot
  prove live source acquisition.
- Exact query:
  `Explain how PostgreSQL MVCC works, why it improves read/write concurrency, and what tradeoffs it creates. Do not assume the reader is a database expert.`
- ProPlex live runs used: 1 of 2.
- Independent source checks used: 0 of 1, because AG-50F already established
  PostgreSQL docs as the canonical baseline.
- Local packet: `output/ag51a_output_quality_review_packet.md`.
- The second live run was not used because the first run did not reveal a
  concrete non-blind in-scope second repair; another run would have been a
  wording retry.

Gate 5 - Final recommendation:

- Phase result: offline acquisition strategy repair completed; live candidate
  acquisition did not move to official/canonical docs.
- Next failure layer: existing-provider acquisition/search still failing after
  first-pass generic documentation query repair, or an unobserved
  pre-accepted-candidate filtering/fit issue before AG-52A.
- Next protected surface: AG-51B only if scoped to a concrete existing-provider
  acquisition/search refinement or allowed pre-accepted-candidate classification;
  otherwise decide on new provider integration or source-specific official
  adapters.
- Phase is merge-ready as a bounded offline repair plus honest live
  non-success classification.
- Merge was not performed.

## Live Validation Result

Live command wrote:

- `output/ag51a_live_report.md`

Final cited URLs:

- `https://arxiv.org/pdf/1201.0228`
- `https://arxiv.org/pdf/1208.4179`

Sanitized official/canonical diagnostics:

- `recovery_query_count=2`
- `recovery_query_previews=official documentation PostgreSQL MVCC concurrency tradeoffs; reference documentation PostgreSQL MVCC concurrency tradeoffs`
- `recovered_result_count=5`
- `accepted_url_count=1`
- `recovered_candidate_domain_preview=arxiv.org`
- `candidate_acquisition_provider_result_count=12`
- `candidate_acquisition_provider_accepted_url_count=1`
- `candidate_acquisition_provider_new_source_count=1`
- `candidate_acquisition_result_status=provider_results_returned`
- `candidate_visibility_export_status=visible`
- `official_canonical_candidate_visible=false`
- `candidate_official_or_canonical_count=0`
- `accepted_or_readable_official_or_canonical_count=0`
- `final_evidence_official_or_canonical_count=0`
- `final_citation_official_or_canonical_count=0`
- `recovered_candidate_source_fit_status=not_evaluated`
- `likely_next_failure_layer=candidate_returned_no_official_canonical_visible`
- `next_failure_layer=canonical_candidate_returned_not_accepted`

## Before / After Result

Before:

- AG-52B query preview was broad and recovered domains were `arxiv.org`.
- Official/canonical candidate visibility remained false.

After:

- Query previews moved to explicit official/reference documentation variants.
- Provider result count rose to 12.
- Accepted recovered domain preview remained `arxiv.org`.
- No official/current/canonical candidate reached AG-52A source-fit.
- Final citations remained arXiv-only.

## Remaining Failure Layer

AG-51A improved and proved one generic recovery-only acquisition strategy
offline, but the live run still did not acquire a visible official/canonical
candidate. The remaining layer is:

- existing-provider acquisition/search still failing after first-pass
  official/reference documentation variants; or
- an unobserved provider-result-to-accepted-candidate filtering/classification
  gap before AG-52A.

## Next Licensed Surface Recommendation

Recommended next action:

- Open AG-51B only if it is scoped to a concrete, non-blind existing-provider
  acquisition/search refinement or an allowed sanitized classification of
  provider results before accepted recovered candidates.
- If no such refinement is identified, make an explicit architecture decision
  about new provider integration or source-specific official adapters.
- Do not open citation survival/selection or Author behavior until an
  official/current/canonical candidate becomes accepted/readable or reaches
  final evidence and then fails citation.

## Why Closed Surfaces Were Not Changed

No changes were made to:

- `core/pipeline_orchestrator.py`;
- provider integration, provider selection, provider routing, or provider
  packages;
- search depth;
- broad query generation outside the admitted recovery path;
- prompts;
- evidence acceptance/source-fit/ranking behavior;
- citation survival/selection;
- Economist, Analyst, Author, Scrutineer, or final-answer behavior.

## Commands And Results

- `git switch main`: already on `main`.
- `git pull --ff-only origin main`: already up to date.
- `git status -sb`: clean before branching.
- `git log --oneline -12`: confirmed AG-52B merge at top.
- `git rev-parse HEAD`: `7421fd4df2758b48abb331adfcd00aca745104b8`.
- `git ls-remote origin refs/heads/main`: matched local HEAD.
- `git switch -c codex/ag51a-existing-provider-official-canonical-recovery-acquisition-strategy`: branch created.
- `py -m pytest --basetemp C:\tmp\ag51a-pytest tests\test_official_canonical_recovery_acquisition_strategy_ag51a.py tests\test_official_canonical_recovery_query_acquisition_ag50a.py`: 28 passed.
- `py -m pytest --basetemp C:\tmp\ag51a-pytest tests\test_official_canonical_recovery_candidate_acquisition_ag50e.py tests\test_official_canonical_recovery_candidate_visibility_ag52b.py tests\test_official_canonical_recovery_evidence_acceptance_ag52a.py`: 25 passed.
- `py -m pytest --basetemp C:\tmp\ag51a-pytest tests\test_official_canonical_recovery_acquisition_strategy_ag51a.py tests\test_official_canonical_recovery_query_acquisition_ag50a.py tests\test_official_canonical_recovery_execution_admission_ag50b.py tests\test_official_canonical_recovery_execution_dispatch_ag50d.py tests\test_official_canonical_recovery_candidate_acquisition_ag50e.py tests\test_official_canonical_recovery_candidate_visibility_ag52b.py tests\test_official_canonical_recovery_evidence_acceptance_ag52a.py tests\test_official_canonical_recovery_visibility_export_ag50c.py tests\test_source_class_recovery.py tests\test_source_class_recovery_executor.py tests\test_source_class_recovery_lifecycle.py tests\test_source_class_recovery_trace.py tests\test_source_class_recovery_diagnostics_l1.py tests\test_ag15_source_class_recovery_quality_diagnostics.py tests\test_runtime_trace_projection_assembly_ag46c.py`: 197 passed.
- `py -m ruff check core tests`: passed.
- `py -m proplex "<exact query>" --mode Balanced --output output\ag51a_live_report.md`: completed, 1 live run used, report written.
- `py -m pytest`: attempted full offline suite, but setup failed repeatedly on
  the known Windows `.pytest-tmp` cleanup permission issue
  (`PermissionError: [WinError 5] Access is denied:
  '\\?\C:\Users\aidan\ProPlex\.pytest-tmp'`). The AG-51A/recovery-focused
  slice above passed before this attempt.

The focused pytest runs emitted a Windows cache warning for `.pytest_cache`
access, but the focused tests passed.

## Local Packet Safety

Local packet:

- `output/ag51a_output_quality_review_packet.md`

Required checks:

- `git check-ignore -v output/ag51a_output_quality_review_packet.md`
- `git ls-files output`

The packet remains untracked and must not be committed.

Merge was not performed.
