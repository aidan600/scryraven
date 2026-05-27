# AG-50B Official/Canonical Recovery Execution Admission

## Phase Purpose

AG-50B makes one bounded source-class recovery execution attempt admissible
when a required official/current/canonical obligation is unsatisfied and the
AG-50A generic recovery query path is visible.

The goal is narrow: move the PostgreSQL MVCC failure past "recovery query
exists but recovery execution is blocked by ordinary iteration budget" when no
higher-priority controller owner blocks the path.

## Opened Protected Surface

Opened surface:

- source-class recovery admission, controller timing, and recovery-attempt budget
  semantics.

Still protected:

- provider routing, provider selection, provider depth/search depth, provider
  escalation, provider roles, source ranking/filtering, returned-source
  classification, prompts, Economist/Analyst/Author/Scrutineer handoffs, final
  answer behavior, and source-specific domains or rules.

## Behavior Change

New helper:

- `core.official_canonical_recovery_execution_admission.build_official_canonical_recovery_execution_admission`

New trace key:

- `official_canonical_recovery_execution_admission_trace`

The helper admits a bounded recovery-specific slot only when all are true:

- the obligation is required, not preferred or unknown;
- the required source class is official/current/canonical;
- the source class is unsatisfied;
- an AG-50A-style official/canonical acquisition path is visible;
- a recovery query is visible;
- prior source-class recovery attempts have not exhausted the hard cap;
- terminal stop, weak-corpus ownership, conflict ownership, provider/depth
  blockers, and other controller blockers do not own the path.

The source-class lifecycle now accepts this admission as a narrow
official/canonical source-class slot when ordinary iteration budget is
exhausted. The existing source-class recovery executor remains the only executor
used.

## Trace Fields

The AG-50B trace emits:

- `admission_considered`
- `admission_eligible`
- `admission_used`
- `admission_skip_reason`
- `admission_blockers`
- `admission_source`
- `admission_acquisition_path_visible`
- `required_source_classes`
- `unsatisfied_required_source_classes`
- `recovery_query_available`
- `recovery_query_count`
- `recovery_query_previews`
- `prior_recovery_attempt_count`
- `max_recovery_attempts`
- `ordinary_iteration_budget_remaining`
- `recovery_slot_available`
- `source_class_recovery_execution_admitted`
- `source_class_recovery_attempt_expected`
- protected-surface invariants for provider/depth/ranking/final-answer behavior.

## Live Budget Used

Approved query:

`Explain how PostgreSQL MVCC works, why it improves read/write concurrency, and what tradeoffs it creates. Do not assume the reader is a database expert.`

Budget used:

- Baseline live run before AG-50B changes: 1 of 1
- Post-repair live rerun: 1 of 1
- Total live ProPlex runs: 2 of 2
- Extra exploratory runs: 0

## Independent Source Check

Status: available and used.

External search query used before and after:

`site:postgresql.org MVCC read write concurrency PostgreSQL documentation`

Best obvious source candidates:

- `https://www.postgresql.org/docs/current/mvcc-intro.html`
- `https://www.postgresql.org/docs/current/mvcc.html`

The independent check confirmed that PostgreSQL's own documentation is the
canonical source class for the validation query.

## Before / After Source-Quality Comparison

Before AG-50B:

- Final answer cited arXiv sources only.
- No `postgresql.org` source survived into final citations.
- Answer was broadly reasonable, but canonical source grounding was weak.
- Allowed CLI artifacts did not expose AG-49/AG-50 runtime trace fields.

After AG-50B:

- Final answer still cited arXiv sources only.
- No `postgresql.org` source survived into final citations.
- Answer quality did not materially improve.
- The post run used 14 calls versus 13 calls in baseline, but that is not
  treated as proof of source-class recovery execution.
- Allowed CLI artifacts still did not expose AG-50B admission or execution trace
  fields, because raw logs, DB rows, caches, provider payloads, prompts, and
  full traces were not inspected.

## Recovery Execution Admission

Offline tests prove the new controller path:

- required canonical obligation plus AG-50A query plus exhausted ordinary
  iteration budget admits one source-class recovery slot;
- required official/current obligation plus AG-50A query also admits;
- preferred-only, conceptual, unknown, already satisfied, terminal stop,
  weak-corpus ownership, conflict ownership, prior-attempt, missing-query, and
  hard-cap cases block.

Live recovery execution admission was not directly observable from allowed
artifacts. This phase therefore claims the offline admission repair and records
the live visibility gap explicitly.

## Canonical/Official Source Acquisition

Canonical PostgreSQL source acquisition did not visibly improve in final
citations. Candidate return and accepted/readable source facts remain unknown
from allowed live artifacts.

## Answer Quality

The before and after answers were both broadly correct and readable, but both
were weakly grounded for a canonical PostgreSQL technical-reference question
because neither cited PostgreSQL documentation.

## Remaining Failure Layer

Remaining visible layer:

- live AG-50B trace visibility is unavailable from the CLI report/cost surface;
- if admission/execution is confirmed in a future visible trace, the next likely
  downstream layer is candidate return, final-evidence preservation, or
  citation/source-fit.

## Protected Surfaces Not Touched

AG-50B did not intentionally change:

- provider routing;
- provider selection;
- provider depth/search depth;
- provider escalation;
- provider roles;
- query text generation beyond consuming existing AG-50A queries;
- source ranking/filtering;
- returned-source classification;
- prompts;
- Economist behavior;
- Analyst behavior;
- Author behavior;
- Scrutineer behavior;
- final-answer behavior;
- `retrieve_targeted` promotion;
- source-specific rules or domains.

The helper contains no hard-coded PostgreSQL, SQLite, SSA, IRS, or NASA domain
branches.

## Local Output Packet

Local packet path:

`output/ag50b_output_quality_review_packet.md`

Ignored/untracked confirmation:

- `git check-ignore -v output/ag50b_output_quality_review_packet.md` matched
  `.gitignore:39:output/`
- `git ls-files output` returned no tracked files

The local packet was not committed.

## Tests

Added:

- `tests/test_official_canonical_recovery_execution_admission_ag50b.py`

Regression suites run:

- AG-50B focused tests;
- AG-50A query acquisition tests;
- AG-49A/B/C tests;
- AG-48A/B/C official-source diagnostic tests;
- source-class recovery controller/lifecycle/executor/trace tests;
- controller-loop spine and retrieval-stop tests;
- evidence-integration checkpoint/gate tests;
- AG-47C retrieval batch projection consistency tests;
- ruff and diff checks.

Full pytest note:

- `py -m pytest -q -p no:cacheprovider --basetemp C:\tmp\ag50b-full` completed
  the suite except for `test_pytest_tmp_path_hardening.py`, which expects the
  workspace-local `.pytest-tmp` path and therefore fails with an explicit
  external basetemp.
- `py -m pytest -q -p no:cacheprovider` was then blocked by repeated Windows
  `PermissionError` cleanup failures on `.pytest-tmp`.

## Next Recommended Phase

Recommended next phase:

- expose the new AG-50B sanitized trace fields in the CLI/local packet path or
  otherwise make live admission/execution visible from allowed artifacts;
- if execution is then confirmed but PostgreSQL docs still do not appear, scope
  the next repair to candidate return, evidence preservation, or citation
  source-fit rather than final-answer rewriting.
