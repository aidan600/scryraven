Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG49B_OFFICIAL_SOURCE_OBLIGATION_CANDIDATE_VISIBILITY_VALIDATION).

# AG-49B Official Source Obligation / Candidate Visibility Diagnostic Validation

Status: completed bounded diagnostic validation

## Scope

AG-49B added passive, runtime-visible, sanitized diagnostics for official,
current, and canonical source obligation detection plus candidate-stage
visibility. It did not attempt to improve retrieval, source ranking, source
classification, query generation, prompts, Economist/Analyst/Author behavior,
or final-answer behavior.

## Validation Mode And Budget

Mode: `diagnostic_validation`

Approved live ProPlex runs used:

- Baseline SSA run before AG-49B code changes: 1
- Baseline SQLite run before AG-49B code changes: 1
- Post-instrumentation SSA rerun: 1
- Post-instrumentation SQLite rerun: 1
- Total live ProPlex runs used: 4 of 4
- Extra exploratory live runs: 0

Approved independent public source checks used:

- SSA before: 1
- SQLite before: 1
- SSA after: 1
- SQLite after: 1
- Total independent external checks used: 4 of 4

## Queries

1. What are the 2026 vs 2025 Social Security COLA, taxable maximum,
   earnings-test limits, and SSI federal payment amounts?
2. Explain how SQLite write-ahead logging works, why it improves concurrency,
   and when WAL mode is a bad idea. Include the main tradeoffs without assuming
   the reader is a database expert.

## Instrumentation Added

New helper:

- `core.official_source_obligation_candidate_visibility.build_official_source_obligation_candidate_visibility_traces`

Runtime attachment:

- `core.runtime_trace_projection_assembly.attach_passive_runtime_projection_traces`
  now attaches `official_source_obligation_trace` and
  `official_source_candidate_visibility_trace`, and mirrors both into the
  evidence-integration checkpoint packet when present.

The candidate-visibility trace emits compact fields including:

- `obligation_status`
- `obligation_reason`
- `obligation_source`
- `obligation_required_or_preferred`
- `obligation_trigger_terms`
- `candidate_query_visibility_status`
- `candidate_query_count`
- `candidate_query_previews`
- `candidate_query_official_intent_status`
- `candidate_official_source_visibility_status`
- `candidate_official_source_count`
- `candidate_official_source_domain_previews`
- `accepted_or_readable_visibility_status`
- `accepted_or_readable_official_source_count`
- `final_evidence_survival_status`
- `final_citation_survival_status`
- `likely_visibility_gap`
- `unknown_fields`
- `behavior_changed=false`

## Before / After Diagnostic Visibility

Before AG-49B, the local packet could review final answers and AG-49A
source-survival fields, but the front half remained hard to localize:

- SSA baseline final answer cited only CBS News and gave approximate/wrong 2026
  values.
- SQLite baseline final answer cited arXiv sources rather than canonical SQLite
  documentation.
- Final reports did not expose obligation status, candidate query intent,
  candidate official/canonical visibility, or accepted/readable visibility.

After AG-49B:

- SSA post run exposed `obligation_status=required`,
  `candidate_query_visibility_status=none_visible`,
  `candidate_official_source_visibility_status=unknown`, and
  `likely_visibility_gap=no_candidate_query_visible`.
- SQLite post run exposed `obligation_status=required` for canonical technical
  documentation from sanitized query terms, while AG-49A still treated the
  source obligation as not required. Its AG-49B gap was
  `obligation_detection_gap`.
- Candidate official/canonical source visibility remained `unknown` where no
  directly observable candidate-return facts existed.
- Accepted/readable visibility now remains `unknown` unless a direct accepted
  or active recovered-source fact is available. The live post traces exposed a
  default recovered-count overclaim; final offline code fixed that without an
  extra live rerun.

AG-49B improved failure localization. Success did not depend on final answer
quality improving.

## Final Answer Quality

SSA final answer quality improved incidentally in the post run: it cited SSA
pages and corrected the main 2026 values for COLA, taxable maximum,
earnings-test limits, and individual/couple SSI standards. It still omitted the
SSI essential-person amount requested by the query.

SQLite final answer quality did not improve. The post run still did not cite
canonical SQLite documentation and gave only a broad caveated explanation.

These answer-quality changes are not AG-49B's success criterion.

## Independent Source Checks

External tool availability: available non-secret web/search tooling.

SSA check query:

`site:ssa.gov 2026 Social Security COLA taxable maximum earnings test SSI federal payment amounts 2025`

Best obvious public source candidates:

- SSA 2026 COLA fact sheet
- SSA SSI federal payment amounts page
- SSA contribution and benefit base page
- SSA retirement test exempt amounts page

SQLite check query:

`site:sqlite.org WAL write ahead logging concurrency when not use WAL`

Best obvious public source candidates:

- SQLite Write-Ahead Logging documentation
- SQLite database file format documentation
- SQLite temporary files documentation
- SQLite WAL-mode file format documentation

The independent checks were review-only. They did not drive unscoped runtime
changes.

## Known Limitations

- AG-49B does not make candidate-return URLs/domains/classes visible unless
  those facts are already directly available in sanitized runtime artifacts.
- AG-49B does not backfill candidate-stage facts from final evidence or final
  citations.
- AG-49B does not repair source acquisition, query generation, provider depth,
  source classification, citation selection, or final synthesis.
- Existing final evidence/citation source-class counts can still disagree with
  visible final citations; AG-49B reports that symptom but does not fix it.

## Next Recommended Repair Lane

Recommended next lane: scoped official/current/canonical obligation and
candidate-query exposure design.

Rationale:

- SSA post diagnostics point to no visible candidate query despite required
  official/current source obligation.
- SQLite post diagnostics point to canonical obligation not being represented
  by the existing runtime source-class expectation.
- Candidate official/canonical return visibility remains unknown unless a
  later phase exposes direct sanitized candidate-return facts.

Any repair would likely touch protected surfaces such as source-obligation
runtime expectation, query generation, or source-class recovery trigger design,
so it should be scoped in a separate phase.

## Local Packet

Local packet path:

`output/ag49b_output_quality_review_packet.md`

Ignored/untracked confirmation:

- `git check-ignore -v output/ag49b_output_quality_review_packet.md` matched
  `.gitignore:39:output/`
- `git ls-files output` returned no tracked files

The local packet was not committed.

## Protected-Surface Confirmation

AG-49B did not intentionally change:

- provider routing, provider selection, provider depth, provider escalation, or
  provider roles;
- query generation;
- prompt behavior;
- source ranking or runtime source-classification behavior;
- evidence visibility beyond passive diagnostic attachment;
- Economist, Analyst, Author, or Scrutineer behavior;
- final-answer behavior;
- controller dispatch or runtime authority;
- legal/current adapters;
- source-specific SSA or SQLite hacks.

The implementation does not expose secrets, `.env`, raw provider payloads, raw
prompts, DB rows, caches, private logs, full raw traces, or unrelated generated
packets.
