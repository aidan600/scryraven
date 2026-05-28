# AG-71A IRS Evidence Chain-of-Custody Diagnostic

Date: 2026-05-28

Scope: Architecture Groove / Prove Mode, diagnostic-only. No runtime repair was
performed.

Branch: `codex/ag71a-irs-evidence-custody-diagnostic`

## Phase Goal

Diagnose the IRS 2026 business standard mileage-rate failure as an evidence
chain-of-custody problem and identify the first custody transition where the
best plausible official/current IRS candidate disappears, is rejected, or is
not review-visible.

Goal status: met for repo-visible evidence. The first repo-proven failure is at
the provider/source acquisition boundary: the live summaries prove recovery was
admitted, execution was attempted, and candidates returned, but they do not
provide a durable review-visible plausible official/current IRS candidate that
can be tracked into readability, source-class classification, fit, Controller
preservation, context exposure, or citation.

Diagnosed first failure layer: provider/source acquisition limit.

Recommended next phase: AG-72R provider/search allocation review.

Note: the current local `main` already includes the AG-72R diagnostic record.
This AG-71A custody record preserves that lineage and does not reopen repair.

## Inputs Inspected

- `docs/architecture/SCRYRAVEN_CURRENT_STATE.md`
- `docs/validation/AG69F_BOUNDED_LIVE_CONTROLLER_LIFECYCLE_VALIDATION.md`
- `docs/validation/AG69F_CONTROLLER_LIFECYCLE_FORCED_CORRIDOR_VALIDATION.md`
- `docs/validation/AG70A_LIVE_FAILURE_SPLIT_DIAGNOSIS_SSA_ADMISSION.md`
- `docs/validation/AG70B_IRS_CANDIDATE_FIT_READABLE_VISIBILITY.md`
- `docs/validation/AG70C_BOUNDED_LIVE_REVALIDATION.md`
- `docs/validation/AG71A_IRS_OFFICIAL_CURRENT_ACQUISITION_QUERY_STRATEGY_REVIEW.md`
- `docs/validation/AG72R_PROVIDER_SEARCH_ALLOCATION_REVIEW.md`
- `docs/validation/AG68H_LIVE_DISPATCH_RECLASSIFICATION.md`
- `docs/validation/AG68I_CROSS_CASE_DISPATCH_ARBITRATION_VISIBILITY.md`
- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- Existing offline tests covering official/current acquisition, official
  numeric/rule handling, source-class recovery, authority lifecycle,
  candidate fit/readability, recovered candidate visibility,
  Controller/AnswerContract source obligations, Analyst/Author posture, and
  citation-source-fit guardrails.

Code surfaces inspected for ownership and diagnostics only:

- `core/source_class_recovery_lifecycle.py`
- `core/source_class_recovery_executor.py`
- `core/recovered_evidence_visibility.py`
- `core/authority_lifecycle_candidate_visibility.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/answer_contract_runtime_handoff.py`
- `core/answer_contract_pipeline_adapter.py`
- `core/pipeline_orchestrator.py`

## Tests And Harnesses Used

Focused offline checks:

```text
py -m pytest -q tests/test_ag71a_irs_acquisition_query_strategy_review.py tests/test_ag70b_irs_candidate_fit_readable_visibility.py tests/test_authority_lifecycle_candidate_visibility_ag69d.py tests/test_authority_lifecycle_forced_corridor_validation_ag69f.py --basetemp C:\tmp\ag71a-custody-focused-1
```

Result: 33 passed.

```text
py -m pytest -q tests/test_official_numeric_source_grounding_ag48a.py tests/test_official_canonical_recovery_candidate_acquisition_ag50e.py tests/test_official_canonical_recovery_evidence_acceptance_ag52a.py tests/test_official_canonical_recovery_candidate_visibility_ag52b.py tests/test_ag17_recovered_evidence_visibility.py --basetemp C:\tmp\ag71a-custody-focused-2
```

Result: 60 passed.

```text
py -m pytest -q tests/test_answer_contract_pipeline_adapter.py tests/test_answer_contract_runtime_handoff.py tests/test_answer_contract_controller.py tests/test_source_hierarchy_answer_contract_invariants_ag57a.py tests/test_ag59ab_controller_owned_insufficiency_analyst_author_obedience.py --basetemp C:\tmp\ag71a-custody-focused-3
```

Result: 59 passed, 1 xfailed.

```text
py -m pytest -q tests/test_ag72r_provider_search_allocation_review.py tests/test_source_class_recovery_lifecycle.py tests/test_source_class_recovery_executor.py tests/test_source_class_recovery_controller.py tests/test_source_class_recovery_trace.py --basetemp C:\tmp\ag71a-custody-focused-4
```

Result: 40 passed.

## Candidate Custody Table

| Stage | Observed status | Evidence | Rejection/drop reason | Durable/review-visible? |
| --- | --- | --- | --- | --- |
| Acquisition / retrieval | Recovery admitted and executed; candidates returned. No durable repo-visible plausible official/current IRS candidate identity is available in committed summaries. | AG-69F-LV and AG-70C show admitted recovery, execution attempted, candidates returned, and no final official/current IRS authority. AG-70B records legacy aggregate candidate ambiguity. AG-71A/AG-72R show satisfying offline IRS candidates survive if acquired. | Provider/source acquisition did not yield a review-visible satisfying official/current IRS candidate. | Aggregate result counts are durable; per-candidate identity is not available in committed summaries. |
| Readability | Not reached for a live official/current IRS candidate. | AG-70C shows no accepted/readable official/current IRS authority. Offline AG-71A and AG-69D fixtures show a readable `irs.gov` authority candidate can survive. | No durable candidate to read. | Durable as aggregate absence only. |
| Source-class classification | Not proved for a concrete live IRS candidate. | AG-70B records that legacy official/canonical candidate counts could be positive while accepted/readable evidence remained zero. AG-71A shows synthetic `official_current_rules` IRS candidates classify and survive. | No review-visible live candidate to classify. | Aggregate ambiguity is durable; concrete classification is unavailable. |
| Candidate fit / acceptance | No accepted/readable official/current IRS authority survived. | AG-70B and AG-70C split returned/evaluated candidates from accepted/readable and final-selected authority evidence. Focused tests prove structured rejection or promotion occurs once a candidate reaches this boundary. | Current evidence points upstream of fit for the live case; downstream synthetic candidates are either selected or rejected with reasons. | Yes for offline seams; no concrete live candidate identity. |
| Controller / AnswerContract preservation | Not reached for a live official/current IRS candidate. | AnswerContract and lifecycle tests preserve unfulfilled official/current obligations and block citation laundering over secondary-only evidence. | No accepted/partially accepted IRS authority evidence to preserve. | Yes for insufficiency state. |
| Context-packet / Analyst exposure | Analyst receives insufficiency posture, not official/current IRS evidence. | AG-59AB and AnswerContract runtime handoff tests preserve partial/unfulfilled official/current posture and warnings. | No preserved official/current IRS evidence existed to expose. | Yes for insufficiency warnings. |
| Analyst / Author / citation surface | No downstream citation issue is proven. | AG-70C says the IRS answer correctly refused to overclaim because no official IRS 2026 notice/news release was in the evidence set. AG-59AB prompt guardrails block citation laundering. | No official/current IRS authority citation was available. | Yes for final posture and insufficiency. |

## Required Diagnostic Decision Tree

1. Did any retrieval/provider candidate include a plausible official IRS source?
   No durable repo-visible plausible official/current IRS candidate identity is
   proven. Candidates returned, but the committed summaries do not identify a
   trackable IRS authority candidate.

2. If yes, was it readable?
   Not reached. No concrete live official/current IRS candidate is available
   for readability review.

3. If readable, was it classified as official/current?
   Not reached for the live candidate. Offline fixtures prove that an
   `irs.gov` candidate labeled `official_current_rules` can classify and
   survive.

4. If classified, was it accepted by candidate fit?
   Not reached for a concrete live candidate. Repo-visible summaries show zero
   accepted/readable official/current IRS authority.

5. If accepted or partially accepted, did Controller/AnswerContract preserve it?
   Not reached. Existing tests show accepted synthetic authority evidence and
   insufficiency states are preserved.

6. If preserved, did the context packet expose it to Analyst?
   Not reached for official/current IRS evidence. Insufficiency posture is
   exposed and durable.

7. If exposed, did Author receive and cite it?
   Not reached. The final answer correctly refused to cite unavailable
   official/current IRS authority.

8. If it failed at any point, what exact transition rejected, dropped, or hid it?
   The first failed transition is acquisition/retrieval to durable candidate
   custody: provider/search execution returned candidates, but no durable
   review-visible plausible official/current IRS candidate identity entered the
   candidate-readability/fit chain.

9. Was there any silent drop where a candidate disappeared without a durable reason?
   Inconclusive at the raw provider-result to durable candidate identity
   boundary because committed summaries intentionally expose counts, not raw
   candidate identities. No downstream silent drop was found once a candidate
   is represented in the offline lifecycle seams.

10. What is the diagnosed first failure layer?
    provider/source acquisition limit.

11. What is the recommended next phase?
    AG-72R provider/search allocation review.

## Silent-Drop Finding

Overall finding: inconclusive.

No silent drop was found after a candidate reaches the repo-visible lifecycle
seams: focused tests show official/current IRS-style candidates are selected
into final authority evidence or rejected with structured reasons. The
unresolved custody gap is earlier: committed live summaries do not expose the
raw provider candidate identities needed to prove whether a specific IRS
candidate silently disappeared before candidate readability/fit.

## Why AG-71A Did Not Repair

This phase was diagnostic-only. Repairing the diagnosed boundary would require
opening at least one protected surface: query/source constraints, provider
allocation, provider depth, provider result shaping, candidate readability/fit,
or visibility/custody behavior. None of those repairs were licensed.

## Why Live Validation Was Not Used

Default live validation was disabled. No live ScryRaven/proplex/scryraven
product-path command, provider/model/search call, independent web check, or
local ignored output packet was used. The diagnostic uses only repo docs,
offline tests, synthetic fixtures, and committed validation summaries.

## Protected Surfaces Kept Closed

- runtime behavior repair;
- query strategy and source constraints;
- provider routing, provider selection, provider depth, provider swap, and new
  provider integration;
- retrieval ranking/filtering;
- source-class classification behavior;
- candidate fit/acceptance behavior;
- Controller/AnswerContract behavior;
- context-packet construction behavior;
- Analyst, Author, citation, and final-answer behavior;
- direct IRS hardcoding;
- broad `core/pipeline_orchestrator.py` domain logic;
- package/CLI/env compatibility behavior;
- follow-up behavior;
- live validation and independent source checks.

## Passive Instrumentation

None added.

Consumer: not applicable.

Decision enabled: not applicable.

Deletion or promotion criterion: not applicable.
