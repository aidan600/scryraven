Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG50A_OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_REPAIR).

# AG-50A Official/Canonical Recovery Query Acquisition Repair

## Phase Purpose

AG-50A is the first scoped behavior repair after AG-49A/B/C diagnostics and
runtime expectation bridge work. It tests whether required
official/current/canonical obligations that already reach the source-class
recovery input surface can produce a generic source-seeking recovery query.

## Opened Protected Surface

Opened surface:

- recovery/candidate query acquisition behavior only for already-detected
  required official/current/canonical obligations.

Still protected:

- provider routing, provider selection, provider depth/search depth, provider
  escalation, provider roles, source ranking/filtering, returned-source
  classification, prompts, Economist/Analyst/Author/Scrutineer handoffs, and
  final-answer behavior.

## Behavior Change

New helper:

- `core.official_canonical_recovery_query_acquisition.apply_official_canonical_recovery_query_acquisition`

The helper consumes sanitized AG-49B/AG-49C-style obligation facts plus the
existing source-class recovery recommendation. When a required unsatisfied
official/current/canonical source class is already visible to recovery and no
generic official/canonical query intent is visible, it appends a generic query
such as:

- `canonical documentation <topic>`
- `official current source <topic>`

It preserves existing recovery queries and blockers, does not set provider or
depth fields, and emits:

- `official_canonical_recovery_query_acquisition_trace`

## Trace Fields

The AG-50A trace includes:

- `acquisition_repair_considered`
- `acquisition_repair_eligible`
- `acquisition_repair_used`
- `acquisition_repair_skip_reason`
- `acquisition_repair_blockers`
- `acquisition_repair_source`
- `required_source_classes`
- `existing_recovery_query_count`
- `added_recovery_query_count`
- `added_recovery_query_previews`
- `generic_query_intent`
- `source_specific_terms_present`
- `provider_policy_unchanged`
- `depth_policy_unchanged`
- `ranking_unchanged`
- `final_answer_behavior_unchanged`
- `behavior_changed`

## Live Budget Used

Approved live query:

`Explain how PostgreSQL MVCC works, why it improves read/write concurrency, and what tradeoffs it creates. Do not assume the reader is a database expert.`

Budget used:

- Baseline live run before AG-50A changes: 1 of 1
- Post-repair live rerun: 1 of 1
- Total live ProPlex runs: 2 of 2
- Extra exploratory runs: 0

The baseline ProPlex run completed but the CLI failed while writing the report
because the output directory did not exist. No extra baseline rerun was
performed because the live budget was already spent.

## Independent Source Check

Status: available and used.

External search query used before and after:

`site:postgresql.org MVCC read write concurrency PostgreSQL documentation`

Best obvious public candidates were PostgreSQL's current MVCC introduction and
official versioned PostgreSQL MVCC/concurrency-control documentation. The
review-only check confirmed the expected source class was canonical PostgreSQL
documentation.

## Before / After Source-Quality Comparison

Before AG-50A:

- Required source class was visible as `primary_source_documents`.
- AG-49B candidate query visibility was `none_visible`.
- AG-49A localized the gap to `candidate_query_generation`.
- Full final answer and full cited URLs were unavailable due the report-write
  failure; sanitized preview showed a non-canonical citation beginning with
  `https://ar...`.

After AG-50A:

- AG-50A emitted `canonical documentation PostgreSQL MVCC`.
- AG-49B candidate query visibility became `visible`.
- AG-49B candidate query intent became `visible`.
- AG-49A moved the missing stage from `candidate_query_generation` to
  `candidate_acquisition`.
- The final answer still cited only `https://arxiv.org/html/2411.10005`.
- PostgreSQL canonical documentation did not survive into visible citations.

## Answer Quality

Answer quality did not materially improve. The post-repair answer was broadly
reasonable, but it still cited an arXiv paper instead of PostgreSQL
documentation for canonical PostgreSQL MVCC behavior.

AG-50A therefore claims only query acquisition repair:

- the generic canonical query was emitted and visible;
- candidate return, acceptance/readability, ranking, citation selection, and
  final-answer behavior remain unproven or unchanged.

## Remaining Failure Layer

The remaining visible layer is downstream of AG-50A:

- active source-class recovery did not execute in the post run because the
  source-class controller reported `blocked_by_iteration_budget`;
- candidate official/canonical return visibility remained `unknown`;
- accepted/readable official/canonical source visibility remained `unknown`;
- final canonical citation count remained `0`.

The next repair should not be final-answer rewriting. It should decide whether
to adjust controller timing/budget ownership, provider acquisition/depth, or
ranking/citation selection in a separately scoped phase.

## Protected Surfaces Not Touched

AG-50A did not intentionally change:

- provider routing;
- provider selection;
- provider depth or search-depth policy;
- provider escalation;
- provider roles;
- source ranking/filtering;
- returned-source classification;
- prompt behavior;
- Economist behavior;
- Analyst behavior;
- Author behavior;
- Scrutineer behavior;
- final-answer behavior;
- `retrieve_targeted` promotion;
- source-specific rules or domains.

The helper contains no hard-coded source domains or source-specific branches
for the validation query or prior SQLite positive-control class.

## Local Output Packet

Local packet path:

`output/ag50a_output_quality_review_packet.md`

Ignored/untracked confirmation:

- `git check-ignore -v output/ag50a_output_quality_review_packet.md` matched
  `.gitignore:39:output/`
- `git ls-files output` returned no tracked files

The packet must not be committed.

## Next Recommended Phase

Recommended next phase:

- Scope controller timing/budget or acquisition execution for official/current/
  canonical source-class recovery queries.

If that does not acquire the canonical source, a later phase may need to
consider provider depth/acquisition or ranking/citation selection. Those
surfaces remain outside AG-50A.
