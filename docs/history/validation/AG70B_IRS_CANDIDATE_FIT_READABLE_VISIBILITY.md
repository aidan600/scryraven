Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG70B_IRS_CANDIDATE_FIT_READABLE_VISIBILITY).

# AG-70B IRS Candidate Fit / Accepted-Readable Visibility Repair

Scope: Architecture Groove / Prove Mode, Path B. Offline implementation only.
No live ProPlex/provider/model/search validation was used. Provider routing,
provider selection, provider depth, retrieval ranking/filtering, prompt wording,
citation rendering, final-answer behavior, Author/Analyst/Economist/Scrutineer
behavior, broad `pipeline_orchestrator.py` logic, and direct IRS hardcoding
remained closed.

Branch: `codex/ag70b-irs-candidate-fit-readable-visibility`

Base commit: `b89cc15` (`Merge pull request #132 from aidan600/codex/ag70a-live-failure-split-diagnosis-ssa-admission`)

## IRS Live Failure Restatement

AG-69F-LV showed the IRS 2026 business standard mileage rate case reached
recovery admission and execution:

- recovery admitted: yes;
- execution attempted: yes;
- candidates returned: yes;
- `recovered_result_count=114`;
- `accepted_url_count=11`;
- `candidate_official_or_canonical_count=1`;
- `accepted_or_readable_official_or_canonical_count=0`;
- `candidate_official_or_canonical_count` could be positive while
  `official_canonical_candidate_visible=false`;
- `recovered_candidate_source_fit_status=no_matching_source_fit`;
- `recovered_candidate_selected_readable_count=0`;
- `recovered_candidate_rejection_reasons=already_visible`;
- final official/current evidence count: 0;
- final official/current citation count: 0;
- remaining layer: candidate fit / visibility.

## AG-70B-R Diagnosis Summary

The IRS lane is independent from the AG-70A SSA admission/query-surfacing lane.
The failure is between recovered candidate visibility/source-fit and export
classification. A positive returned/evaluated lifecycle candidate count is not
proof that readable official/current authority evidence is available or
selected.

## Decision Records

### 1. Reconnaissance Review

Repo-visible code was sufficient for the repair. `recovered_evidence_visibility`
dropped duplicate recovered sources as `already_visible` before distinguishing
whether the visible duplicate satisfied the required authority. The lifecycle
projection then exposed rejected returned candidates through legacy candidate
count fields that downstream export readers could misread as accepted/readable
authority availability.

The local AG-69F-LV packet was read because it exists under ignored `output/`,
is marked `LOCAL/UNTRACKED - DO NOT COMMIT`, and contains sanitized
product-visible diagnostics only. It was not committed.

### 2. Seam Decision: Export vs Visibility vs Lifecycle

Chosen seam: D, a small combination of A/B/C.

- A: split export semantics so returned/evaluated and rejected lifecycle
  candidates are visible separately from accepted/readable authority evidence.
- B: clarify duplicate visibility reasons before treating `already_visible` as
  a requirement-bound rejection.
- C: keep rejected lifecycle candidates in returned/evaluated counts, but do
  not export them as accepted/readable authority evidence.

This keeps ownership lifecycle-centered: controller decides, visibility applies
the boundary, export observes.

### 3. Pre-Implementation Repair Decision

The repair stays in pure helper modules:

- `core/recovered_evidence_visibility.py`;
- `core/authority_lifecycle_candidate_visibility.py`;
- `core/official_canonical_recovery_visibility_export.py`.

No provider/search, prompt, citation, final-answer, Author, or broad
orchestrator changes were needed or justified.

### 4. Post-Implementation Self-Review

Behavior changed:

- duplicate recovered candidates now distinguish:
  - `already_visible_authority_satisfying`;
  - `already_visible_duplicate_lower_tier_context`;
  - `already_visible_not_authority_satisfying`;
  - corresponding `duplicate_visible_*` partial-identity cases;
- lifecycle projection now emits separate returned/evaluated, rejected,
  accepted/readable authority, and final-selected authority counts;
- the official/canonical recovery visibility export includes those split counts,
  a count-basis field, and lifecycle citation eligibility;
- rejected lifecycle candidates remain structured rejections with final evidence
  `explained_absent`;
- valid authority candidates blocked only by final-evidence capacity remain
  `matched_not_selected`, distinct from `no_matching_source_fit`.

### 5. Validation Result Decision

Offline validation passed for focused AG-70B tests and relevant AG-70A,
AG-69D/F, AG-50/52, and AG-68I regression lanes. The recurring pytest cache
warning is local filesystem cache-write noise; test assertions passed.

### 6. Final Recommendation Review

Provider/search review is not justified yet. The offline repair addresses the
post-execution semantic ambiguity shown by AG-70B-R without changing acquisition
or search behavior. Recommended next action is review and then a separately
approved bounded live validation gate if product confidence requires checking
whether the clarified diagnostics now localize the IRS lane more honestly.

## Tests Added / Changed

Added:

- `tests/test_ag70b_irs_candidate_fit_readable_visibility.py`

The suite proves:

- counted-but-not-readable candidates remain returned/evaluated while
  accepted/readable authority evidence is 0;
- lower-tier visible duplicates do not masquerade as official/current
  availability;
- rejected lifecycle count is not accepted/readable evidence;
- capacity-blocked valid authority evidence remains `matched_not_selected`;
- citation eligibility is `explained_ineligible` when final authority evidence
  is absent;
- legacy export fields are lifecycle projections, not independent truth
  sources;
- AG-70A SSA admission/query surfacing is not touched;
- protected provider/search/prompt/citation/final-answer/Author surfaces and
  broad `pipeline_orchestrator.py` logic remain closed.

## Remaining Unknowns

This phase did not run live validation and did not inspect raw provider
payloads, raw prompts, DB rows, private logs, caches, full traces, `.env`, or
secrets. It therefore does not prove that a future live IRS run will acquire a
better official/current source. It only repairs the lifecycle-owned visibility
and export semantics for returned/rejected versus accepted/readable authority
evidence.

## Live Validation Recommendation

Live validation is recommended next only as a separate approved gate. It should
rerun the exact IRS query and inspect sanitized product-visible diagnostics to
confirm whether the next remaining layer is still candidate fit/visibility,
acquisition/provider result quality, final evidence survival, citation
survival/source-claim fit, or no remaining lifecycle-layer failure.
