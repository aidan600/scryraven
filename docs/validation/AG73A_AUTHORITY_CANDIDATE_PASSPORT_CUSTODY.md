# AG-73A Authority Candidate Passport Custody Diagnostic

Date: 2026-05-28

Scope: Architecture Groove / Prove Mode, diagnostic-only. No runtime repair was
performed.

Branch: `codex/ag73a-authority-candidate-passport-custody`

## Phase Goal

Create candidate-level diagnostic custody visibility for represented
official/current authority candidates so a future repair phase can prove where
a plausible official/current candidate is first lost, rejected, hidden, or
promoted.

Goal status: met for offline represented candidates. AG-73A adds a passive,
sanitized Authority Candidate Passport projection and focused offline tests. It
does not prove the live IRS first-failure layer because no live provider/model
search calls, raw provider payloads, raw prompts, DB rows, private logs, caches,
full raw traces, secrets, or ignored output packets were inspected.

Diagnostic decision tree classification for the live IRS lineage:
`inconclusive`.

Recommended next phase: `stop for architecture decision`.

## Inputs Inspected

- `docs/architecture/SCRYRAVEN_CURRENT_STATE.md`
- `docs/validation/AG70C_BOUNDED_LIVE_REVALIDATION.md`
- `docs/validation/AG70B_IRS_CANDIDATE_FIT_READABLE_VISIBILITY.md`
- `docs/validation/AG71A_IRS_OFFICIAL_CURRENT_ACQUISITION_QUERY_STRATEGY_REVIEW.md`
- `docs/validation/AG71A_IRS_EVIDENCE_CHAIN_OF_CUSTODY_DIAGNOSTIC.md`
- `docs/validation/AG72R_PROVIDER_SEARCH_ALLOCATION_REVIEW.md`
- `core/source_class_recovery_executor.py`
- `core/official_canonical_recovery_candidate_acquisition.py`
- `core/recovered_evidence_visibility.py`
- `core/authority_lifecycle_candidate_visibility.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/answer_contract_runtime_handoff.py`
- `core/pipeline.py`
- `core/pipeline_orchestrator.py` for inspection only
- Existing tests covering official/current acquisition, IRS numeric/rule
  handling, authority lifecycle, recovered candidate visibility, candidate
  fit/readability, AnswerContract handoff, Analyst/Author posture, and citation
  handoff.

## Passport Invariant

A represented candidate relevant to a required official/current source
obligation must not disappear silently. It must either:

1. promote to final authority evidence / citation eligibility;
2. carry an explicit rejection/drop reason; or
3. carry an explicit lost/hidden disposition that names the first missing stage.

`assert_authority_candidate_passport_integrity()` fails if any represented
candidate has `represented_without_durable_disposition`.

## Field Contract

The projection lives in `core/authority_candidate_passport.py` and returns
`authority_candidate_passport_ag73a_v1` records. Each passport is sanitized and
diagnostic-only. It may include:

- identity and obligation fields: `candidate_id`, `requirement_id`,
  `required_source_class`, `required_authority`;
- safe source metadata: `source_url`, `normalized_domain`, `title`;
- provider/retrieval fields: `provider_name`, `provider_role`, `query_preview`,
  `retrieval_pass_id`, `provider_returned`, `provider_rank_or_position`,
  `accepted_url`, `deduped_against_candidate_id`;
- readability/classification fields: `readability_status`,
  `readable_text_available`, `source_tier`, `source_class`,
  `classification_reason`, `official_domain_signal`, `currentness_signal`,
  `temporal_anchor_required`, `temporal_anchor_observed`,
  `claim_value_extraction_status`;
- fit/disposition fields: `fit_state`, `satisfies_authority`,
  `mismatch_reason`, `rejection_reason`, `rejection_owner`,
  `final_disposition`, `first_missing_stage`;
- downstream visibility fields: `controller_visible`,
  `answer_contract_visible`, `context_packet_visible`, `analyst_visible`,
  `author_visible`, `citation_eligible`, `cited_in_final_answer`.

The projection does not include raw provider payloads, raw prompts, full raw
traces, secrets, API keys, DB rows, caches, private logs, or unrelated output
artifacts. Source text is consumed only to determine whether readable text is
available; it is not exported in the passport.

## Decision Tree

For each represented candidate:

1. If it is selected authority evidence, mark it promoted unless a supplied
   downstream surface explicitly shows it missing before AnswerContract,
   context packet, Analyst/Author, or citation.
2. If it has an existing structured lifecycle rejection, preserve that reason
   and derive the first missing stage from the reason.
3. If official-looking evidence has no readable text, classify the first
   missing stage as readability.
4. If official-looking readable evidence does not match the required source
   class, classify the first missing stage as source-class classification.
5. If classified official/current evidence is rejected for fit/currentness,
   preserve that rejection reason.
6. If a candidate appears accepted but no Controller/AnswerContract custody is
   visible, classify the first missing stage as Controller/AnswerContract.
7. If none of the above applies, flag a silent-drop integrity failure.

## Aggregate Reconciliation

Passport counts reconcile with existing aggregate diagnostics by comparing:

- returned/evaluated candidate count;
- official/canonical candidate count;
- rejected candidate count;
- accepted/readable authority evidence count;
- final-selected authority evidence count.

Unknown or not-observable aggregate fields are ignored. Known aggregate fields
must match the passport-derived counts for `passport_counts_reconcile=true`.

## Fixture Coverage

Added `tests/test_ag73a_authority_candidate_passport_custody.py`.

Covered custody states:

- provider found a plausible official IRS candidate but readability failed;
- readable official-looking candidate was misclassified;
- classified official/current candidate was rejected by fit/currentness;
- accepted candidate was lost before Controller/AnswerContract;
- final-selected authority evidence failed context exposure;
- promoted authority evidence remained citation eligible and cited when all
  downstream surfaces were visible;
- aggregate counts reconciled with existing visibility export fields;
- secondary/lower-tier evidence did not satisfy an official/current obligation;
- duplicate and claim-extraction rejections carried durable reasons;
- represented candidates without durable disposition failed integrity;
- protected/raw material was sanitized out of the projection;
- static import/source guards kept provider, prompt, orchestration, Author,
  citation, and final-answer surfaces closed.

Focused offline validation run:

```text
py -m pytest -q tests/test_ag73a_authority_candidate_passport_custody.py --basetemp C:\tmp\ag73a-passport-focused
```

Result: 12 passed.

Touched-area lint:

```text
py -m ruff check core\authority_candidate_passport.py tests\test_ag73a_authority_candidate_passport_custody.py
```

Result: passed.

Broader offline safety set:

```text
py -m pytest -q tests/test_ag73a_authority_candidate_passport_custody.py tests/test_ag71a_irs_acquisition_query_strategy_review.py tests/test_official_numeric_source_grounding_ag48a.py tests/test_authority_lifecycle_candidate_visibility_ag69d.py tests/test_ag70b_irs_candidate_fit_readable_visibility.py tests/test_ag17_recovered_evidence_visibility.py tests/test_answer_contract_runtime_handoff.py tests/test_ag59ab_controller_owned_insufficiency_analyst_author_obedience.py tests/test_source_hierarchy_answer_contract_invariants_ag57a.py tests/test_official_canonical_recovery_visibility_export_ag50c.py tests/test_official_canonical_recovery_candidate_visibility_ag52b.py --basetemp C:\tmp\ag73a-focused-suite-rerun
```

Result: 130 passed, 1 xfailed.

Additional AG-72R/acquisition/acceptance/AnswerContract adapter checks:

```text
py -m pytest -q tests/test_ag72r_provider_search_allocation_review.py tests/test_official_canonical_recovery_candidate_acquisition_ag50e.py tests/test_official_canonical_recovery_evidence_acceptance_ag52a.py tests/test_answer_contract_pipeline_adapter.py --basetemp C:\tmp\ag73a-extra-focused
```

Result: 25 passed.

## Secondary Evidence Rule

Secondary, trusted-community, social/forum, context, or analysis-tier evidence
is never marked as satisfying an official/current obligation by the passport.
It may remain visible as context, but its passport has
`satisfies_authority=false` and a durable rejection/disposition reason when the
required class is official/current authority.

## What AG-73A Can Prove Offline

For represented synthetic or fixture candidates, AG-73A can now prove:

- plausibly official/current candidate acquired but unreadable;
- readable official-looking candidate misclassified;
- classified official/current candidate rejected by fit/currentness;
- accepted candidate missing before Controller/AnswerContract custody;
- final-selected authority evidence missing from context exposure;
- Analyst/Author/citation-surface missing when explicitly supplied;
- promoted final authority evidence with citation eligibility;
- aggregate/passport count reconciliation;
- lower-tier evidence remaining non-satisfying for official/current
  obligations;
- durable silent-drop detection for represented candidates.

## What Remains Unprovable Without Live/Raw Inspection

AG-73A still cannot prove whether the AG-70C/AG-71A/AG-72R live IRS failure was
caused by:

- no plausible official IRS candidate acquired;
- a plausible IRS candidate acquired but unreadable;
- readable IRS evidence misclassified;
- classified IRS evidence rejected by fit/currentness;
- accepted IRS evidence lost before Controller/AnswerContract;
- downstream context, Analyst/Author, or citation-surface failure.

The raw provider-result to represented-candidate boundary remains unprovable
from committed docs and offline fixtures alone.

## Silent-Drop Finding

No silent-drop path remains for represented candidates covered by the passport
projection: integrity fails if a represented candidate lacks promotion,
rejection, or an explicit lost/hidden disposition.

A silent-drop path may still exist before representation, at the live/raw
provider-result to sanitized candidate boundary. AG-73A intentionally did not
inspect raw provider payloads or run live validation, so that boundary remains
inconclusive.

## Passive Instrumentation Added

Added `core/authority_candidate_passport.py`.

Consumer: AG-73A diagnostic tests and future AG-73B/AG-74 repair gates.

Decision enabled: identify the first visible custody stage where a represented
official/current authority candidate is rejected, hidden, lost, or promoted.

Deletion or promotion criterion: promote into the runtime visibility export if
future live validation requires report-visible per-candidate custody; otherwise
delete or fold into lifecycle visibility tests once existing lifecycle/export
diagnostics expose equivalent durable candidate dispositions.

Runtime behavior changed: no.

## Protected Surfaces Kept Closed

- runtime behavior repair;
- provider swaps or new providers;
- provider routing, provider selection, provider depth, provider escalation,
  and search-budget behavior;
- query strategy and source constraints;
- prompt behavior;
- retrieval, ranking, filtering, source-class classification, currentness
  classification, candidate fit, acceptance, preservation, citation
  eligibility, and final answer posture;
- Controller/AnswerContract runtime behavior;
- context-packet, Analyst, Author, citation, final-answer, and follow-up
  behavior;
- direct IRS hardcoding;
- broad `core/pipeline_orchestrator.py` domain logic;
- package/CLI/env compatibility behavior;
- live validation and independent source checks.

## Recommended Next Phase

Recommended next phase: `stop for architecture decision`.

Reason: AG-73A supplies the missing offline custody projection for represented
candidates, but the live IRS first-failure layer remains inconclusive without a
separately licensed live/diagnostic budget or an architecture decision to expose
candidate passports in product-visible diagnostics.
