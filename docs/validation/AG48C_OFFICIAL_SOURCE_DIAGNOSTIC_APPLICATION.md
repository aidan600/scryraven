# AG-48C Official Source Diagnostic Application

Date: May 24, 2026

Status: offline diagnostic application and next-lane decision.

## 1. Scope and Non-Authorization

AG-48C applies the AG-48A and AG-48B diagnostic contracts to existing committed
AG-47B and AG-47D review documents.

This phase:

- does not run live validation;
- does not inspect local output packets under `output/` or `outputs/`;
- does not inspect raw traces, logs, DB rows, caches, provider payloads,
  prompts, secrets, or generated packets;
- does not change runtime behavior;
- does not tune examples, providers, routing, depth, query generation, source
  ranking, source classification, evidence visibility, prompts, Economist,
  Analyst, Author, final answers, or controller dispatch.

The purpose is to classify what the committed review docs make visible and to
choose the first product-quality implementation lane that can improve future
diagnosis without overfitting these cases.

## 2. Source Artifacts Used

Committed AG-47 review artifacts:

- `docs/validation/AG47B_ACTIVE_BATCH_OUTPUT_QUALITY_REVIEW_R1.md`
- `docs/validation/AG47B_OUTPUT_QUALITY_REVIEW_ADDENDUM.md`
- `docs/validation/AG47D_POST_FIX_OUTPUT_TRACE_SANITY_REVIEW_R1.md`

Committed AG-48 diagnostic artifacts:

- `docs/architecture/OFFICIAL_NUMERIC_SOURCE_GROUNDING_AG48A.md`
- `docs/validation/OFFICIAL_NUMERIC_SOURCE_GROUNDING_AG48A_PLAN.md`
- `core/official_numeric_source_grounding.py`
- `tests/test_official_numeric_source_grounding_ag48a.py`
- `docs/architecture/OFFICIAL_SOURCE_ACQUISITION_SURVIVAL_AG48B.md`
- `docs/validation/OFFICIAL_SOURCE_ACQUISITION_SURVIVAL_AG48B_PLAN.md`
- `core/official_source_survival_diagnostics.py`
- `tests/test_official_source_survival_diagnostics_ag48b.py`

No ignored local packet was used.

## 3. Classification Method

AG-48A is used for the broad product-quality bottleneck:

- source need not detected;
- official/current source not acquired;
- source acquired but not accepted;
- accepted source not visible in final evidence;
- visible source not cited;
- correct source cited but wrong value extracted;
- correct source-bound value distorted in final answer;
- Economist eligible not invoked;
- Economist invoked with weak/wrong evidence;
- Economist correct but ignored/distorted downstream;
- correctly caveated missing evidence.

AG-48B is used for source acquisition/survival stage:

- `obligation_not_detected`
- `no_candidate_query`
- `no_official_candidates_returned`
- `official_candidate_rejected_or_unreadable`
- `official_candidate_misclassified`
- `accepted_source_dropped_before_final_evidence`
- `final_evidence_source_not_cited`
- `citation_survived_but_value_extraction_failed`
- `answer_correctly_caveated_missing_source`
- `not_a_source_acquisition_failure`

Classification discipline:

- classify the earliest material bottleneck only when the committed docs support
  it;
- record downstream symptoms separately when useful;
- mark AG-48B stage as `not observable from committed review doc` when
  candidate/acquisition/acceptance/final-evidence facts are insufficient;
- do not infer provider failure from absent final citations;
- do not infer query-generation failure unless candidate-query absence is
  visible;
- do not infer source-classification failure unless candidate presence plus
  misclassification is visible;
- do not infer Economist failure unless eligibility/run/evidence-use facts are
  visible;
- do not infer Author synthesis failure unless source-bound values existed
  upstream.

## 4. Decision Table

| Review case | Observed failure or success | Evidence visible in committed docs | AG-48A bottleneck | AG-48B source-survival stage | Confidence | Likely next lane | What not to infer |
|---|---|---|---|---|---|---|---|
| AG-47B Q1 TCO / RAV4 Hybrid vs Tesla Model Y | Partial and caveated; Toyota-side evidence was usable, but Tesla-side price, efficiency, electricity, maintenance, insurance, and incentive evidence was missing from final cited support. | AG-47B note says final cited Tesla-side evidence was missing, completeness was incomplete, and caveats mostly matched missing evidence. Addendum says this is retrieval breadth and source fit, not a reason to tune provider/routing. | `answer_correctly_caveated_missing_evidence` as the supported posture; downstream symptom is missing current/source-fit coverage for Tesla and incentives. | `not observable from committed review doc` | Medium | `official_source_survival_instrumentation` | Do not infer no candidate query, no returned Tesla/current candidates, provider failure, source-classification failure, or Economist failure. |
| AG-47B Q2 Roth IRA 2026 vs 2025 | Material numeric error despite official IRS source availability and citation. | Addendum says official IRS retrieval/source fit looked good, but the answer gave wrong 2026 IRA limits and one MFJ phaseout range. | `correct_source_cited_wrong_number_extracted` | `citation_survived_but_value_extraction_failed` | High | `numeric_extraction_economist_diagnostics` | Do not infer source acquisition failure, provider failure, or Author distortion unless a source-bound upstream value is shown. |
| AG-47B Q3 Artemis II current status | Core status was mostly right, but official NASA status source did not appear in final citations; reputable news may provide context but should not replace the official status anchor. | AG-47B note says no official NASA source appeared in final citations and secondary/off-domain sources dominated. Addendum says NASA should have anchored mission status and dates. | Official/current source missing from final citation path; exact AG-48A layer before citation is not localizable from committed docs. | `not observable from committed review doc` | Medium | `official_source_survival_instrumentation` | Do not infer the NASA source was not queried, not returned, rejected, misclassified, or dropped after acceptance. |
| AG-47B Q4 Obsidian / Notion / Capacities | Mostly acceptable comparison, with source-coverage caveats for official product claims. | AG-47B note says answer covered requested dimensions, had some primary Capacities docs and several secondary sources. Addendum says the quality issue is not urgent architecture evidence. | `no_official_numeric_grounding_bottleneck_detected` for the committed product-quality decision; product-claim source fit remains a low-priority caveat. | `not_a_source_acquisition_failure` for this lane at current evidence strength. | Medium | `no_implementation_yet` | Do not infer a general product-source policy failure or source-ranking defect from this acceptable case. |
| AG-47D Q1 Social Security / SSA 2026 vs 2025 | Failed product goal; no official SSA source survived into the final answer and no requested 2026/2025 numeric values were answered, but the answer avoided unsupported numbers. | AG-47D note says no official SSA source survived, final citation was CBS 2027 COLA reporting, no requested values were extracted, and hallucination risk was low because unsupported numbers were refused. | `answer_correctly_caveated_missing_evidence` plus a material upstream official-source survival gap. | `not observable from committed review doc` | High for product failure; low for exact stage | `official_source_survival_instrumentation` | Do not infer source was not acquired, not accepted, misclassified, or dropped before final evidence; the committed note does not expose those stage facts. |
| AG-47D Q2 Boeing Starliner crewed operations | Failed product goal; answer correctly refused off-topic evidence, but the current Starliner official/news source mix did not survive. | AG-47D note says no useful final cited Starliner source list, poor currentness, low hallucination risk due to refusal, and obvious official NASA/Boeing status sources were not retrieved or preserved. | `answer_correctly_caveated_missing_evidence` with official/current status survival unresolved. | `not observable from committed review doc` | High for missing anchor; low for exact stage | `official_source_survival_instrumentation` | Do not infer query-generation failure, weak-corpus recovery defect, provider failure, or classification failure from the final caveat alone. |
| AG-47D Q3 California heat pump vs gas furnace + AC | Useful with caveats; mostly answered requested dimensions, but no fully source-bound five-year cost model emerged and sources were mostly secondary/proxy. | AG-47D note says California/incentive/cost sources were visible, source fit was mixed, incentive availability remained uncertain, and precise five-year math was avoided. | `numeric_value_not_source_bound` for the cost-model symptom, with upstream official/current incentive survival not localizable. | `not observable from committed review doc` | Medium | `official_source_survival_instrumentation` | Do not infer Economist eligibility/run failure or Author distortion; the committed doc does not show source-bound values existed upstream. |
| AG-47D Q4 SQLite WAL | Acceptable conceptual answer, but canonical SQLite documentation should have anchored the technical reference. | AG-47D note says the answer cited general WAL/storage papers rather than SQLite primary documentation and should ideally cite SQLite primary documentation for WAL behavior. | Canonical source missing from final citation path; exact AG-48A layer before citation is not localizable from committed docs. | `not observable from committed review doc` | Medium | `source_fit_citation_survival` | Do not infer SQLite docs were not queried, not returned, misclassified, or dropped from final evidence. |

## 5. Cross-Case Read

Only one case is clearly localized past source survival: AG-47B Q2 Roth IRA.
The committed docs support that official IRS sources survived and were cited,
but numeric values were wrong. That case points to
`numeric_extraction_economist_diagnostics`.

Most official/current/canonical failures are not localized beyond missing final
evidence, missing final citation, or a correct caveat over missing/off-topic
evidence:

- AG-47B Q1: missing Tesla/current inputs in final cited support;
- AG-47B Q3: no official NASA final citation;
- AG-47D Q1: no official SSA source survived into the final answer;
- AG-47D Q2: official/news Starliner source mix did not survive;
- AG-47D Q3: no fully source-bound California cost model;
- AG-47D Q4: no SQLite primary citation.

The committed docs deliberately preserve only bounded review summaries and
sanitized trace snippets. They do not expose enough candidate-query, candidate
return, acceptance, source-classification, final-evidence, final-citation, or
Economist handoff facts to distinguish source not acquired from source acquired
but dropped.

## 6. Next-Lane Options

Allowed lane names:

- `official_source_survival_instrumentation`
- `numeric_extraction_economist_diagnostics`
- `author_source_bound_synthesis`
- `source_fit_citation_survival`
- `no_implementation_yet`

Decision rule application:

- Because most official/current/canonical failures cannot be localized beyond
  missing final evidence/citation or caveated missing evidence, the first lane
  should be `official_source_survival_instrumentation`.
- `numeric_extraction_economist_diagnostics` is clearly relevant for the Roth
  IRA case, but it should follow once future sanitized packets can show whether
  required official/current sources survived and whether Economist received
  source-bound values.
- `author_source_bound_synthesis` is not first because the committed docs do
  not show correct source-bound values existed upstream and were distorted by
  final synthesis.
- `source_fit_citation_survival` is relevant for SQLite and official-status
  source anchoring, but the committed docs usually do not show whether the
  canonical/official source reached final evidence before citation.
- `no_implementation_yet` is too passive because the pattern is recurring and
  AG-48B already identified the missing sanitized fields needed to localize it.

## 7. Final Recommendation

Recommended next implementation phase:

`official_source_survival_instrumentation`

Why this lane comes first:

The current committed review artifacts show recurring official/current/canonical
source failures, but they do not expose enough sanitized acquisition,
acceptance, final-evidence, final-citation, or Economist-handoff facts to pick a
repair lane responsibly. Instrumentation comes first because it creates the
minimum observable bridge between review outcomes and later implementation
authority.

What this recommendation does not authorize:

- provider routing, provider selection, provider depth, or provider escalation
  changes;
- query-generation changes;
- source-ranking or source-classification runtime behavior changes;
- evidence visibility behavior changes;
- prompt changes;
- Economist, Analyst, Author, Scrutineer, or controller handoff changes;
- final-answer behavior changes;
- source-specific special cases;
- live validation;
- inspection or commitment of local output packets, raw traces, logs, DB rows,
  caches, provider payloads, prompts, or secrets.

Minimum acceptance criteria for the next phase:

- add sanitized fields that identify required source obligation, obligation
  detection, candidate-query availability, official/canonical candidate counts,
  accepted official/canonical counts, final-evidence counts, final-citation
  counts, caveat posture, numeric mismatch, and source-bound value presence;
- keep all fields compact and review-safe, with no raw provider payloads,
  prompts, full traces, caches, DB rows, or output packets committed;
- prove through offline tests that the fields can localize AG-48B stages without
  changing runtime answer behavior;
- preserve protected surfaces: providers, routing, depth, query generation,
  source classification, source ranking, prompts, handoffs, evidence visibility,
  controller authority, and final answers;
- show that existing AG-48A and AG-48B classifiers still pass unchanged.

## 8. Next-Phase Codex Brief

Phase name:

`AG-49A - Official Source Survival Instrumentation`

Goal:

Add offline, sanitized source-survival instrumentation to future validation
artifacts so official/current/canonical source failures can be localized to
AG-48B stages before any repair changes are authorized.

Exact allowed changes:

- add or extend validation-only packet construction code to emit sanitized
  source-survival fields when those facts are already available to the review
  path;
- add compact field names aligned with AG-48B:
  `required_source_obligation`, `source_obligation_required`,
  `obligation_detected`, `candidate_query_count`,
  `candidate_official_or_canonical_count`,
  `accepted_official_or_canonical_count`,
  `final_evidence_official_or_canonical_count`,
  `final_citation_official_or_canonical_count`, `candidate_misclassified`,
  `caveat_present`, `numeric_value_mismatch`, and source-bound value presence;
- add offline tests with synthetic sanitized records covering every AG-48B
  disappearance stage and AG-48A numeric/caveat interactions;
- update validation documentation to describe consumers, decision criteria, and
  deletion criteria for the new sanitized fields;
- keep the fields absent, `unknown`, or explicitly not observable when the
  review path does not already have sanitized facts.

Exact non-goals:

- no live validation;
- no source acquisition fix;
- no retrieval implementation change;
- no provider routing, provider selection, provider depth, provider escalation,
  or provider-role change;
- no query-generation change;
- no source ranking or source-classification runtime behavior change;
- no prompt rewrite;
- no Economist, Analyst, Author, Scrutineer, or controller handoff change;
- no final-answer behavior change;
- no source-specific special cases;
- no legal/current adapter implementation change;
- no raw telemetry, prompt, provider payload, DB row, cache, log, secret, or
  generated output packet inspection or commitment.

Files likely to change:

- validation packet/review code that already assembles sanitized source and
  citation summaries;
- `docs/validation/` for the AG-49A plan and exit report;
- `tests/` for pure offline instrumentation and classifier-compatibility tests.

Tests required:

- offline unit tests for all AG-48B source-survival stages using sanitized
  fixture rows;
- offline tests proving unknown/unavailable fields stay unknown instead of
  forcing an exact stage;
- regression tests for AG-48A and AG-48B classifiers;
- static guards proving the instrumentation tests do not import providers,
  prompts, routing, runtime source classifiers, DB access, log readers, caches,
  or packet paths;
- `git diff --check`, targeted pytest, and ruff for touched tests.

Stop conditions:

- required facts are available only in raw traces, provider payloads, prompts,
  logs, caches, DB rows, secrets, or ignored output packets;
- implementation would change provider/routing/depth/query behavior;
- implementation would change source ranking, source classification runtime
  behavior, evidence visibility, prompts, handoffs, controller authority, or
  final answers;
- implementation requires source-specific rules;
- tests require invented facts rather than synthetic sanitized fixtures.

Protected surfaces:

- provider routing, selection, depth, escalation, and roles;
- query generation;
- source ranking and runtime source classification;
- prompts and raw prompt exposure;
- Economist, Analyst, Author, Scrutineer, and controller handoffs;
- final answer posture and content;
- evidence visibility behavior;
- legal/current adapters;
- raw telemetry, provider payloads, DB rows, caches, logs, secrets, ignored
  packets, and full traces.

Expected behavior change:

None for user-facing answers and runtime control flow. The only expected change
is richer sanitized diagnostic output in future validation artifacts, enabling a
later repair phase to choose between acquisition, acceptance, final-evidence
survival, citation survival, numeric extraction, and synthesis lanes.
