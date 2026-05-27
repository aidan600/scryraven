# AG-52A Official/Canonical Recovery Evidence Acceptance, Source-Fit, And Ranking Repair

## Phase Purpose

AG-52A repaired the next source-trust layer after AG-50F: evidence
acceptance/source-fit/ranking for already-returned recovery candidates in an
admitted official/current/canonical recovery slot.

The product-quality goal was narrow: when an admitted recovery slot has a
returned candidate satisfying the required official/current/canonical source
class, preserve that candidate into accepted/readable evidence. Citation
selection, Author behavior, provider routing, provider depth, prompt behavior,
and query generation remained closed.

## Source-Layer Boundary Handling

Referenced Project Source context was provided inline in the prompt.

Repo files read first:

- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/validation/AG50F_OFFICIAL_CANONICAL_CANDIDATE_ACQUISITION_LIVE_CLASSIFICATION.md`
- `docs/validation/AG50E_OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_ACQUISITION_REPAIR.md`

Local packet `output/ag50f_output_quality_review_packet.md` was available.

No Project Source files were assumed to exist in the repo unless repo-tracked.

GitHub/repo state verified before work:

- local `main` was up to date with `origin/main`
- HEAD: `9eb2074d7d2b7b0ccaee443ec046a864473a72c6`
- expected merge present: `9eb2074 Merge pull request #90 ... AG-50F`
- `git ls-remote origin refs/heads/main` matched local HEAD

## Licensed Protected Surface

Opened:

- evidence acceptance, source-fit, and ranking for already-returned candidates
  in an admitted official/current/canonical source-class recovery slot

Still closed:

- provider routing, provider selection, provider depth/search-depth, provider
  escalation, and provider pricing policy
- query wording/generation
- prompt behavior
- broad returned-source classification or broad ranking outside this recovery
  slot
- citation survival or citation selection
- Economist, Analyst, Author, Scrutineer, and final-answer behavior
- new provider integration
- source-specific PostgreSQL hacks

## Rule 0 Failure Analysis

General failure class:

- Recovered candidate set exists, but required official/current/canonical source
  class does not enter accepted/readable evidence.

Blast radius:

- Source-class recovery evidence selection and source-fit ranking for admitted
  official/current/canonical recovery slots.

Rules applied:

- Scope was limited to already-admitted recovery candidates.
- Provider behavior, query generation, prompts, citations, Author behavior, and
  final-answer behavior were not changed.
- Product-quality success for this phase is movement into accepted/readable
  evidence. Final citation improvement is downstream and was not required.

Valid cases protected:

- ordinary conceptual/no-obligation queries;
- secondary-only recovered candidate sets;
- zero recovered candidates;
- mirror/unofficial docs and keyword-only matches;
- broad ranking outside the source-class recovery path.

## Implementation Hypothesis And Diagnosis

Existing code already had the right structural seam:

- `core.source_class_recovery_executor.execute_source_class_recovery_action`
  appends recovered candidates to `all_passages`;
- `core.recovered_evidence_visibility.apply_recovered_evidence_visibility_boundary`
  can reserve a qualifying recovered source into final readable evidence;
- `core.pipeline_orchestrator` already calls the visibility boundary through a
  small adapter after `filter_top_evidence`.

The bottleneck was narrower:

- the visibility boundary admitted only answer-contract gap reasons, so
  AG-50A/50E official-canonical recovery reasons were blocked as
  `reason_not_answer_contract_gap`;
- canonical technical documentation was not always recognized as a strong
  primary/canonical source fit when it appeared as a generic docs/manual/
  reference page rather than an already-classed official source;
- the allowed export could not report source-fit candidate counts, selected
  readable counts, or compact rejection reasons.

## Behavior Change Made

Changed modules:

- `core/recovered_evidence_visibility.py`
- `core/source_class_recovery.py`
- `core/source_class_recovery_lifecycle.py`
- `core/source_class_recovery_diagnostics.py`
- `core/official_canonical_recovery_visibility_export.py`

Behavior:

- An admitted official/canonical recovery slot whose reason starts with
  `official_canonical_recovery_query_acquisition` can use the existing recovered
  evidence visibility boundary.
- Generic canonical technical documentation source-fit signals are recognized
  for primary-source documentation when the candidate is a docs/manual/reference
  surface with technical context and is not secondary, mirror, unofficial, or
  rehosted.
- Declared source-class labels on recovered candidates are honored when they
  match known source-class observability buckets.
- The visibility decision now exports sanitized source-fit status, fit
  candidate count, selected readable count, and rejection reason buckets.

The implementation did not hardcode PostgreSQL, the exact MVCC query, or a
forced URL.

## Tests Added Or Changed

Added:

- `tests/test_official_canonical_recovery_evidence_acceptance_ag52a.py`

Coverage:

- positive canonical documentation candidate acceptance;
- source-fit preference/replacement over weaker secondary evidence at final
  evidence cap;
- no-obligation negative control;
- zero-candidate negative control;
- mirror/unofficial docs negative control;
- secondary-only negative control;
- sanitized source-fit export fields;
- static guard against source-specific PostgreSQL terms and protected-surface
  terms in the new helper surfaces.

Existing relevant tests run:

- AG-17 recovered evidence visibility;
- AG-50A query acquisition;
- AG-50B execution admission;
- AG-50C visibility export;
- AG-50D execution dispatch;
- AG-50E candidate acquisition;
- source-class recovery helper/executor/lifecycle/trace/diagnostics tests.

## Mid-Phase Review Gates

Gate 1 — Reconnaissance:

- Repo was clean on the AG-52A branch from updated `main`.
- Existing seams were executor append, pure visibility boundary, and export.
- Likely implementation path was a pure helper/export repair.
- `pipeline_orchestrator.py` was expected to need no change; it ultimately was
  not changed.

Gate 2 — Pre-implementation:

- Exact bottleneck: official-canonical admitted recovery reasons were not
  eligible for the recovered-evidence visibility boundary, and canonical docs
  source-fit was too weak.
- Decision-tree branch: candidates can be returned but not recognized/ranked/
  accepted/readable; AG-50F did not expose URLs, so tests had to preserve
  zero/unknown cases.
- Fix stayed inside evidence acceptance/source-fit/ranking.

Gate 3 — Post-implementation self-review:

- Offline tests prove the intended seam.
- No protected-surface drift was found.
- `pipeline_orchestrator.py` gained no domain decision logic.
- Unknowns were preserved for zero candidates and not-evaluated source fit.
- Positive, negative-control, unknown-preservation, and protected-surface tests
  exist.

Gate 4 — Validation decision:

- One post-repair live run was used because offline tests proved the seam but
  the approved PostgreSQL query could classify whether the live bottleneck moved
  downstream.
- Exact query:
  `Explain how PostgreSQL MVCC works, why it improves read/write concurrency, and what tradeoffs it creates. Do not assume the reader is a database expert.`
- Live ProPlex runs used: 1 of 2.
- Independent source checks used: 0 of 1, because AG-50F already established
  PostgreSQL documentation as the obvious canonical source class.
- Local packet: `output/ag52a_output_quality_review_packet.md`.

Gate 5 — Final recommendation:

- Offline phase result: repaired and merge-ready.
- Live result: did not exercise the repaired seam because recovered candidates
  were zero / candidate visibility was not exported.
- Next failure layer: existing-provider recovered-candidate acquisition or
  candidate-visibility before evidence acceptance.
- Merge was not performed.

## AG-50F Baseline

AG-50F observed:

- `recovered_result_count=11`
- `candidate_return_status=candidates_returned`
- `official_canonical_candidate_visible=false`
- `accepted_or_readable_official_or_canonical_count=0`
- `final_evidence_official_or_canonical_count=0`
- `final_citation_official_or_canonical_count=0`
- final cited URLs were arXiv PDFs, not PostgreSQL documentation

AG-50F could not expose returned candidate URLs, so AG-52A did not assume
PostgreSQL docs were returned and rejected.

## Live Validation Result

Post-repair live report:

- `output/ag52a_live_report.md`
- ProPlex runs: 1 of 2
- independent source checks: 0 of 1

Final cited URLs:

- `https://arxiv.org/pdf/1201.0228`

Sanitized official/canonical diagnostics:

- `recovered_result_count=0`
- `accepted_url_count=0`
- `candidate_return_status=zero_candidates`
- `zero_candidate_blocker_kind=candidate_visibility_not_exported`
- `official_canonical_candidate_visible=unknown`
- `recovered_candidate_source_fit_status=not_evaluated`
- `recovered_candidate_source_fit_count=0`
- `recovered_candidate_selected_readable_count=0`
- `accepted_or_readable_official_or_canonical_count=0`
- `final_evidence_official_or_canonical_count=0`
- `final_citation_official_or_canonical_count=0`
- `likely_next_failure_layer=recovery_executed_no_candidate_visibility`
- `next_failure_layer=execution_attempted_zero_candidates`

Interpretation:

- The AG-52A repaired path was not exercised by this live run because no
  recovered candidate reached the source-fit/acceptance boundary.
- The live remaining failure is upstream of AG-52A evidence acceptance:
  recovered-candidate acquisition or candidate-visibility export.
- Final citation behavior remained closed and was not changed.

## Before / After Result

Before:

- AG-50F returned candidate count was positive but official/canonical candidate
  visibility was false; returned URLs were unavailable.

After offline:

- Fixture-level canonical documentation candidates are source-fit recognized,
  preferred over secondary candidates, and preserved into accepted/readable
  evidence for admitted official/canonical recovery slots.
- No-obligation, zero-candidate, secondary-only, and mirror/unofficial controls
  preserve non-success.

After live:

- PostgreSQL documentation still did not reach accepted/readable evidence or
  citations.
- The live report classified the issue as zero candidates /
  `candidate_visibility_not_exported`, not as an exercised AG-52A acceptance
  rejection.

## Commands And Results

- `git switch main`: already on main.
- `git pull --ff-only origin main`: already up to date.
- `git status -sb`: clean on `main` before branching.
- `git log --oneline -12`: confirmed AG-50F merge at top.
- `git rev-parse HEAD`: `9eb2074d7d2b7b0ccaee443ec046a864473a72c6`.
- `git ls-remote origin refs/heads/main`: matched local HEAD.
- `git switch -c codex/ag52a-official-canonical-recovery-evidence-acceptance-source-fit`: branch created.
- Focused tests:
  `py -m pytest --basetemp C:\tmp\ag52a-pytest tests\test_official_canonical_recovery_evidence_acceptance_ag52a.py tests\test_ag17_recovered_evidence_visibility.py tests\test_official_canonical_recovery_candidate_acquisition_ag50e.py tests\test_official_canonical_recovery_visibility_export_ag50c.py`
  passed, 49 passed.
- Broader recovery slice:
  `py -m pytest --basetemp C:\tmp\ag52a-pytest tests\test_source_class_recovery.py tests\test_source_class_recovery_executor.py tests\test_source_class_recovery_lifecycle.py tests\test_source_class_recovery_trace.py tests\test_source_class_recovery_diagnostics_l1.py tests\test_official_canonical_recovery_query_acquisition_ag50a.py tests\test_official_canonical_recovery_execution_admission_ag50b.py tests\test_official_canonical_recovery_execution_dispatch_ag50d.py`
  passed, 128 passed.
- Full suite with explicit temp base:
  `py -m pytest --basetemp C:\tmp\ag52a-pytest`
  produced 1648 passed, 1 failed, 1 deselected. The failure was
  `tests/test_pytest_tmp_path_hardening.py::test_tmp_path_uses_workspace_local_base`
  because the explicit `--basetemp` intentionally did not include
  `.pytest-tmp`.
- Default temp cleanup issue:
  `.pytest-tmp` was permission-blocked on Windows; both sandboxed and escalated
  `Remove-Item -LiteralPath .pytest-tmp -Recurse -Force` failed with access
  denied.
- `py -m ruff check core tests`: passed.
- `git diff --check`: passed with line-ending warnings only.

## Local Packet Safety

Local packet:

- `output/ag52a_output_quality_review_packet.md`

It is under ignored `output/` and must not be committed.

## Remaining Failure Layer

AG-52A repaired the offline acceptance/source-fit/ranking contract. The live
PostgreSQL case now points to:

- existing-provider recovered-candidate acquisition or candidate-visibility
  before evidence acceptance;
- possibly a provider/depth/acquisition issue, but AG-52A does not license
  provider or depth changes.

The next licensed surface recommendation is:

- a narrow AG-53A or AG-52B acquisition/visibility classification phase for
  official/canonical recovered candidates, specifically to distinguish provider
  zero results, provider results rejected before candidate acceptance, and
  sanitized candidate URL/domain visibility gaps.

Do not open citation survival or Author behavior until an official/current/
canonical candidate is accepted/readable or final evidence contains it but
citations omit it.

## Protected-Surface Confirmation

No code changed:

- `core/pipeline_orchestrator.py`

No changes were made to:

- providers, routing, depth, escalation, or pricing;
- query generation or prompt behavior;
- citation survival/selection;
- Economist, Analyst, Author, Scrutineer, or final-answer behavior;
- source-specific PostgreSQL handling.

Merge was not performed.
