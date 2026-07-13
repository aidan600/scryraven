Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG73B_AUTHORITY_PASSPORT_RUNTIME_VISIBILITY).

# AG-73B Authority Passport Runtime Visibility Promotion

Date: 2026-05-28

Scope: Review Lane diagnostic runtime visibility/export attachment only. No
live validation, runtime repair, provider/search changes, query strategy
changes, prompt changes, classifier changes, fit changes, Controller decision
changes, AnswerContract decision changes, Author/citation/final-answer changes,
or direct IRS hardcoding were performed.

## Phase Goal

Promote the AG-73A Authority Candidate Passport from an offline helper into
sanitized runtime-visible trace/export/validation surfaces so future validation
can classify where represented official/current candidates are rejected, lost,
hidden, or promoted.

Goal status: met for represented offline/runtime-shaped candidates.

## Exposed Surface

The projection is exposed at:

- `authority_candidate_passport_projection` on the runtime execution trace;
- the same key mirrored into the evidence-integration checkpoint packet when
  that packet is present;
- `authority_candidate_passport_projection` and compact summary fields inside
  `official_canonical_recovery_visibility_export`;
- the official/canonical recovery diagnostics Markdown summary through compact
  passport availability, count, disposition, and first-missing-stage fields.

The surface is trace/export/validation-only. It is not read by retrieval,
provider routing, source classification, candidate fit, Controller decisions,
AnswerContract decisions, context assembly, Analyst, Author, citation, or final
answer behavior.

## Consumer

Primary consumer: bounded validation and diagnostic review phases that need
candidate-level custody visibility for represented official/current authority
candidates.

Secondary consumer: future repair gates that need to decide whether to open a
candidate acquisition, readability, source-class classification, fit/currentness,
Controller/AnswerContract custody, context exposure, or citation-surface seam.

## Decision Enabled

For each represented candidate, the passport names the final disposition and
the first missing stage when a candidate is rejected, lost, hidden, or promoted.
This lets validation distinguish:

- represented official/current candidate unreadable;
- represented candidate misclassified;
- represented candidate rejected by fit/currentness;
- accepted candidate lost before Controller/AnswerContract visibility;
- final-selected candidate missing from context/Analyst/Author/citation
  surfaces when those passive surface facts are supplied;
- promoted final authority evidence.

## Deletion Or Promotion Criterion

Keep this projection while AG-73/AG-74 validation needs per-candidate custody
diagnostics. Promote it into a durable runtime diagnostics contract only if live
validation proves that report-visible candidate custody is required for ongoing
operations. Delete it, or fold it into narrower lifecycle/export tests, once
existing visibility exports provide equivalent candidate-level disposition and
first-missing-stage facts.

## Sanitization Boundary

The projection reuses the AG-73A sanitized field contract. It may expose
candidate IDs, safe URL/domain/title metadata, compact provider role/name,
bounded query previews, classification/readability/fit/disposition summaries,
and passive downstream surface visibility facts.

It must not expose raw provider payloads, raw prompts, secrets, API keys, DB
rows, private logs, caches, full raw traces, ignored local output packets, or
source text bodies. Source text may only be consumed to determine whether
readable text exists.

## Tests

Added `tests/test_ag73b_authority_passport_runtime_visibility.py`.

The tests prove:

- runtime attachment creates the passport trace and mirrors it into the
  checkpoint packet;
- official/current recovery fixtures produce a sanitized passport surface;
- the official/canonical visibility export carries the passport projection;
- the export and Markdown surface include candidate disposition and first
  missing stage summaries;
- protected raw/private material and source text bodies do not leak through the
  passport/export surfaces;
- final evidence inputs are not mutated by the attachment;
- static guards keep provider/search/prompt/classifier/orchestrator behavior
  surfaces closed.

Related regression coverage remains in:

- `tests/test_ag73a_authority_candidate_passport_custody.py`;
- `tests/test_official_canonical_recovery_visibility_export_ag50c.py`;
- `tests/test_ag17_recovered_evidence_visibility.py`;
- `tests/test_authority_lifecycle_candidate_visibility_ag69d.py`;
- `tests/test_answer_contract_runtime_handoff.py`;
- `tests/test_official_numeric_source_grounding_ag48a.py`.

## Behavior Changes

Runtime answer behavior changed: no.

Provider/search/query/prompt/classifier/fit/Controller/AnswerContract/context
packet/Analyst/Author/citation/final-answer behavior changed: no.

The only runtime plumbing change is a passive attachment call that passes
already-computed represented recovered and final evidence facts into
`attach_passive_runtime_projection_traces()`.

## Protected Surfaces Kept Closed

- provider routing, selection, depth, escalation, swaps, and new providers;
- Linkup or other provider escalation policy;
- query strategy and source constraints;
- prompts;
- retrieval, ranking, and filtering;
- source-class/currentness classifiers;
- candidate fit and acceptance decisions;
- Controller and AnswerContract runtime decisions;
- context packet, Analyst, Author, citation, and final answer behavior;
- follow-up and Scrutineer behavior;
- direct IRS hardcoding;
- broad `pipeline_orchestrator.py` domain logic;
- package/CLI/env compatibility behavior;
- live ScryRaven/proplex/scryraven provider/model/search calls.

## Recommended Next Seam

Run a separately licensed bounded validation phase only if product confidence
requires live classification. The next decision seam should use the passport
surface to choose between candidate acquisition/provider-result shaping,
readability, source-class classification, fit/currentness,
Controller/AnswerContract custody, context exposure, and citation survival.
