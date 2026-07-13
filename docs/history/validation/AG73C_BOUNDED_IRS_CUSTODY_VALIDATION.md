Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG73C_BOUNDED_IRS_CUSTODY_VALIDATION).

# AG-73C Bounded IRS Custody Validation

Date: 2026-05-28

Scope: Validation gate / Review Lane Batch Mode. This phase is offline bounded
validation only. It adds no repair and performs no live ScryRaven/proplex/
scryraven provider, model, search, or product-path run.

## Phase Goal

Use the AG-73A/AG-73B Authority Candidate Passport surfaces to classify, as far
as offline repo-visible evidence allows, the IRS first-failure layer in the
official/current 2026 business standard mileage-rate lineage.

Goal status: met for offline represented candidates and for the live-boundary
proof. Represented candidate failure layers can now be classified from the
AG-73B runtime/export passport fields. The actual live IRS first-failure layer
remains unclassified because committed evidence still contains no sanitized
per-candidate live IRS passport at the provider-result to represented-candidate
boundary.

## AG-73B Prerequisite Verification

AG-73B is present on current `main` before this AG-73C branch:

- recent log includes `78c9a98 Merge pull request #9 from
  aidan600/codex/ag73b-authority-passport-runtime-visibility`;
- `docs/history/validation/AG73B_AUTHORITY_PASSPORT_RUNTIME_VISIBILITY.md` exists;
- `tests/test_ag73b_authority_passport_runtime_visibility.py` exists;
- `core/authority_candidate_passport.py` defines
  `AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY`,
  `build_authority_candidate_passport_projection()`, and
  `build_authority_candidate_passport_trace()`;
- `core/runtime_trace_projection_assembly.py` attaches the passive passport
  projection through `attach_passive_runtime_projection_traces()`;
- `core/official_canonical_recovery_visibility_export.py` exports
  `authority_candidate_passport_available`,
  `authority_candidate_passport_first_missing_stages`, and
  `authority_candidate_passport_projection`;
- `core/pipeline_orchestrator.py` calls the passive projection assembly seam,
  but the passport module itself is not wired into provider/search,
  classification, fit, Controller, AnswerContract, context, Analyst, Author,
  citation, or final-answer decisions.

## Inputs Inspected

- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/architecture/SCRYRAVEN_CURRENT_STATE.md`
- `docs/history/validation/AG70C_BOUNDED_LIVE_REVALIDATION.md`
- `docs/history/validation/AG70B_IRS_CANDIDATE_FIT_READABLE_VISIBILITY.md`
- `docs/history/validation/AG71A_IRS_OFFICIAL_CURRENT_ACQUISITION_QUERY_STRATEGY_REVIEW.md`
- `docs/history/validation/AG71A_IRS_EVIDENCE_CHAIN_OF_CUSTODY_DIAGNOSTIC.md`
- `docs/history/validation/AG72R_PROVIDER_SEARCH_ALLOCATION_REVIEW.md`
- `docs/history/validation/AG73A_AUTHORITY_CANDIDATE_PASSPORT_CUSTODY.md`
- `docs/history/validation/AG73B_AUTHORITY_PASSPORT_RUNTIME_VISIBILITY.md`
- `core/authority_candidate_passport.py`
- `core/runtime_trace_projection_assembly.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/recovered_evidence_visibility.py`
- `core/authority_lifecycle_candidate_visibility.py`
- `core/answer_contract_runtime_handoff.py`
- `core/pipeline.py`
- `core/pipeline_orchestrator.py` for inspection of the passive attachment seam
- related AG-70B, AG-71A, AG-72R, AG-73A, AG-73B, export, recovered-evidence,
  lifecycle, AnswerContract, numeric grounding, projection, and protected
  static-guard tests.

## Tests And Harnesses Used

Added:

- `core/authority_candidate_passport_validation.py`
- `tests/test_ag73c_bounded_irs_custody_validation.py`

Focused AG-73C run:

```text
py -m pytest -q tests/test_ag73c_bounded_irs_custody_validation.py --basetemp C:\tmp\ag73c-focused
```

Result: 11 passed.

Passport/export regression run:

```text
py -m pytest -q tests/test_ag73c_bounded_irs_custody_validation.py tests/test_ag73a_authority_candidate_passport_custody.py tests/test_ag73b_authority_passport_runtime_visibility.py tests/test_official_canonical_recovery_visibility_export_ag50c.py --basetemp C:\tmp\ag73c-passport-export-suite
```

Result: 42 passed.

Related offline validation run:

```text
py -m pytest -q tests/test_ag70b_irs_candidate_fit_readable_visibility.py tests/test_ag71a_irs_acquisition_query_strategy_review.py tests/test_ag72r_provider_search_allocation_review.py tests/test_ag17_recovered_evidence_visibility.py tests/test_authority_lifecycle_candidate_visibility_ag69d.py tests/test_answer_contract_runtime_handoff.py tests/test_official_numeric_source_grounding_ag48a.py tests/test_runtime_trace_projection_assembly_ag46c.py --basetemp C:\tmp\ag73c-related-suite
```

Result: 81 passed.

Touched Python lint:

```text
py -m ruff check core\authority_candidate_passport_validation.py tests\test_ag73c_bounded_irs_custody_validation.py
```

Result: passed.

The new helper is a passive diagnostic adapter. It reads only the sanitized
AG-73B `official_canonical_recovery_visibility_export` passport fields and maps
them to AG-73C validation labels. It is not imported by runtime product paths.

## Passport Fields Used

Classification uses only sanitized passport/export fields:

- `authority_candidate_passport_available`
- `authority_candidate_passport_projection`
- `passports`
- `candidate_id`
- `final_disposition`
- `first_missing_stage`
- `readability_status`
- `readable_text_available`
- `source_tier`
- `source_class`
- `classification_reason`
- `official_domain_signal`
- `currentness_signal`
- `fit_state`
- `satisfies_authority`
- `rejection_reason`
- `controller_visible`
- `answer_contract_visible`
- `context_packet_visible`
- `analyst_visible`
- `author_visible`
- `citation_eligible`
- `cited_in_final_answer`

The adapter does not consume source text bodies, raw provider payloads, raw
prompts, DB rows, private logs, caches, full raw traces, secrets, API keys, or
ignored local output packets.

## Represented Candidate Failure Layers Proven Offline

The AG-73C export-level tests prove that represented candidates can be
classified as:

- plausible official IRS candidate acquired but unreadable;
- readable official-looking candidate misclassified;
- classified official/current candidate rejected by fit/currentness;
- accepted/readable candidate lost before Controller/AnswerContract;
- Controller/AnswerContract saw it but failed to preserve/export it;
- context packet failed to expose it;
- Analyst/Author/citation-surface failure;
- promoted/citation-eligible authority evidence;
- inconclusive when no passport is available for the live boundary.

This reuses the AG-73A per-candidate custody field contract and AG-73B
runtime/export attachment rather than duplicating the full passport fixture
suite.

## IRS Lineage Classification

Chosen classification:

```text
inconclusive because candidate passports still do not cover the live boundary
```

AG-70C showed the IRS live lane reached recovery admission and execution,
returned candidates, and still produced no accepted/readable or final
official/current IRS authority. AG-71A classified the repo-visible chain as a
provider/source acquisition limit, but with medium-low confidence because it
had no raw/live per-candidate identity. AG-72R narrowed that to inconclusive for
the provider/search sublayer because provider allocation, result filtering,
post-provider shaping, search depth, or source-specific resolver strategy all
remain plausible. AG-73A/AG-73B now prove represented candidate custody, but no
committed record contains a sanitized live IRS passport from the AG-70C/AG-71A/
AG-72R lineage.

## Exact Unobservable Boundary

The still-unobservable boundary is:

```text
provider-result to represented authority candidate; offline repo-visible
evidence has aggregate result counts but no sanitized per-candidate live IRS
passport
```

The current passport can classify a candidate only after that candidate is
represented in sanitized lifecycle/recovered/final evidence facts. It cannot,
from committed offline evidence alone, prove whether a live provider returned a
plausible official IRS URL that was never accepted, embedded, source-classified,
made readable, shaped into recovered evidence, or represented as a passport.

## Decision Usefulness

Chosen next useful action:

```text
narrow provider-result-to-represented-candidate visibility bridge
```

Recommended next phase: AG-73D-V, a narrow diagnostic visibility bridge from
sanitized provider-result summaries into represented authority-candidate
passport custody. It should be diagnostic-only unless a later phase separately
licenses repair. If product confidence requires live proof after that bridge,
request a separately licensed one-run live custody validation with an exact
query, call cap, redaction plan, output packet path, and stop condition.

## Why Live Validation Was Not Used

Live validation was explicitly out of scope. No live ScryRaven/proplex/
scryraven product-path command, provider/model/search call, independent web
check, raw provider inspection, DB inspection, private-log read, cache read,
full-trace inspection, or local ignored output packet was used.

## Why No Runtime Behavior Changed

AG-73C added one passive validation helper and one offline test module. The
helper reads an already-exported sanitized passport packet and returns a
classification record for tests/docs. It is not called from runtime pipeline,
provider, search, classifier, fit, Controller, AnswerContract, context,
Analyst, Author, citation, or final-answer code.

## Protected Surfaces Kept Closed

- runtime behavior repair;
- provider routing, selection, depth, escalation, swaps, and new providers;
- Linkup or other provider escalation policy;
- query strategy and source constraints;
- prompts;
- retrieval, ranking, filtering, source-class classification, and currentness
  classification behavior;
- candidate fit and acceptance behavior;
- Controller and AnswerContract runtime decisions;
- context packet, Analyst, Author, citation, and final-answer behavior;
- follow-up and Scrutineer behavior;
- direct IRS hardcoding;
- broad `core/pipeline_orchestrator.py` domain logic;
- package/CLI/env compatibility behavior;
- live ScryRaven/proplex/scryraven provider/model/search calls;
- raw/private/protected material.

Protected-surface grep matches in AG-73C files are expected doc/test mentions
or closed-surface assertions:

- `citation` and `final_answer` appear in the validation label, visible
  passport fields, and docs describing closed downstream surfaces;
- `raw_provider_payload`, `raw_prompt`, `api_key`, and `secret` appear only in
  sanitization guard fixtures or closed-material docs;
- `source_classifier`, `select_providers`, and `author_prompt` appear only in
  static guards asserting the validation helper does not import or reference
  protected behavior surfaces.

No protected-surface drift was found.

## Remaining Rough Edges

- AG-73C can classify represented candidates but still cannot see raw provider
  candidates or URLs that never become represented sanitized candidates.
- The new validation helper intentionally maps only AG-73C decision labels. If
  future passport stages are added, the helper should stay conservative and
  report them as outside the AG-73C decision map until a later phase scopes
  them.
- A future live run would still require a separate live validation budget and a
  redaction/output plan.
