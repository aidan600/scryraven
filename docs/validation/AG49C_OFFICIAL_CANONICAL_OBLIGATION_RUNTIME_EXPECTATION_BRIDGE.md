# AG-49C Official/Canonical Obligation Runtime Expectation Bridge

## Phase Purpose

AG-49C makes AG-49B-style official/current/canonical source obligations visible
to the existing runtime source-class recovery and evidence-obligation input
surface. The phase is a bounded readiness repair: it does not attempt to improve
final answer quality by changing acquisition, prompts, ranking, or synthesis.

## Bridge Seam Chosen

The bridge is `core/official_source_obligation_bridge.py`.

It consumes sanitized obligation facts equivalent to AG-49B's
`OfficialSourceObligationCandidateVisibilityFacts` and can add generic missing
source-class facts to an existing source-class recovery recommendation. The
pipeline calls it only where source-class recovery telemetry is already being
assembled:

- pre-recovery, before `record_source_class_recovery_lifecycle`;
- post-recovery/final telemetry, before the runtime answer-contract handoff and
  final execution trace are assembled.

The durable trace key is `official_source_obligation_bridge_trace`.

## Behavior Change

Required official/current/canonical obligations may now add missing source-class
inputs such as `official_current_rules` or `primary_source_documents` to the
existing recovery/evidence-obligation telemetry.

Preferred, not-required, and unknown obligations do not change recovery inputs.
Existing strong satisfaction and existing runtime blockers remain authoritative.
The bridge deliberately does not generate recovery queries. If a required class
is visible but no existing query is available, candidate-query visibility remains
unknown or empty rather than being invented by AG-49C.

## Why The Seam Is Safe

The bridge maps generic obligation classes to generic source-class facts only.
It has no provider, routing, search-depth, prompt, ranking, filtering,
classification, Economist, Analyst, Author, Scrutineer, or final-answer
dependency.

The active source-class controller still owns eligibility and blockers. In
particular, the bridge preserves weak-corpus ownership, prior-attempt blockers,
budget exhaustion, terminal-stop blockers, provider-policy blockers,
search-depth blockers, retrieve-to-anchor blockers, and no-query blockers.

## Protected Surfaces Not Touched

- Provider routing unchanged.
- Provider selection unchanged.
- Provider depth/search-depth policy unchanged.
- Query-generation prompts unchanged.
- Generated query text unchanged.
- Source ranking/filtering unchanged.
- Runtime source classification for returned sources unchanged.
- Economist behavior unchanged.
- Analyst/Author/Scrutineer handoffs unchanged.
- Final-answer behavior unchanged.
- Controller dispatch authority unchanged.
- `retrieve_targeted` was not promoted.

## Bridge Trace Fields

The bridge trace exposes:

- `bridge_considered`
- `bridge_eligible`
- `bridge_used`
- `bridge_skip_reason`
- `bridge_blockers`
- `bridge_source`
- `bridge_required_source_classes`
- `bridge_candidate_query_available`
- `bridge_candidate_query_count`
- `bridge_candidate_query_previews`
- `bridge_recovery_recommended`
- `bridge_recovery_reason`
- `bridge_added_missing_source_classes`
- `bridge_existing_missing_source_classes`
- `bridge_satisfied_source_classes`
- `behavior_changed`

Candidate-return and accepted/readable facts are not backfilled from final
evidence or final citations.

## Tests

Added:

- `tests/test_official_source_obligation_bridge_ag49c.py`

Covered cases:

- official numeric/status/rule obligations map to `official_current_rules`;
- canonical technical-reference obligations map to `primary_source_documents`
  without source-specific implementation;
- preferred current-event context remains advisory;
- conceptual explainers do not force recovery;
- unknown obligations leave inputs unchanged;
- already satisfied official/canonical classes block bridge use;
- budget and terminal blockers remain authoritative;
- no new provider role, executor, depth policy, generated query text, or
  `retrieve_targeted` promotion is introduced;
- candidate-query visibility remains unknown when not directly visible;
- runtime projection assembly mirrors the bridge trace into the checkpoint.

Regression suites run:

- AG-49A projection tests;
- AG-49B obligation/candidate visibility tests;
- AG-48A/B/C official-source diagnostic tests;
- AG-46C runtime projection assembly tests;
- source-class recovery diagnostics L1 tests;
- AG-47C retrieval-batch projection dispatch consistency tests.

## Live Analyze/Fix Loop Summary

Approved query:

`Explain how SQLite write-ahead logging works, why it improves concurrency, and when WAL mode is a bad idea. Include the main tradeoffs without assuming the reader is a database expert.`

Baseline result:

- The answer did not cite sqlite.org.
- The answer correctly caveated that retrieved evidence was insufficient to
  explain WAL mechanics and tradeoffs.
- The visible citation was an NCBI-hosted C++ wrapper source file, not canonical
  SQLite documentation.
- CLI-visible output did not expose sanitized AG-49A/B packets without reading
  raw logs/traces, which were not inspected.

Post-fix result:

- The answer still did not cite sqlite.org.
- The answer remained appropriately caveated but still lacked canonical SQLite
  documentation.
- Offline AG-49C tests prove the bridge marks the SQLite-style technical query
  as considered, eligible, and used for `primary_source_documents`.
- Full answer-quality repair would require a later source acquisition,
  query-generation, provider, or ranking phase, all outside AG-49C.

Live budget used:

- 2 of 2 approved ProPlex runs.
- 2 of 2 approved independent external source checks.

## Independent Source Checks

Independent public checks used official SQLite documentation:

- `https://www.sqlite.org/wal.html`
- `https://sqlite.org/walformat.html`

These confirmed that canonical SQLite documentation directly covers WAL
mechanics, concurrency, checkpointing, and tradeoffs. The findings were
review-only and did not drive any unscoped runtime behavior change.

## Known Limitations

- The bridge does not acquire sqlite.org by itself.
- The bridge does not generate, rewrite, append, or alter candidate queries.
- Candidate-return and accepted/readable stages remain unknown unless directly
  visible through approved sanitized artifacts.
- CLI-visible live output did not expose AG-49C trace fields, so live trace
  confirmation was bounded to offline tests and the local packet records that
  telemetry gap.

## Promotion / Deletion Criteria

Keep the bridge while AG-49C and follow-on phases need explicit observability
for the obligation-to-runtime-expectation gap.

Promote the bridge if a future controller lane consumes required official or
canonical source classes directly as a first-class runtime expectation.

Delete or collapse it if source-class expectation natively receives the same
official/current/canonical obligation facts.

## Next Recommended Phase

The next lane should decide whether canonical technical obligations may safely
influence existing query-generation or acquisition behavior. That phase would
need explicit approval because improving the SQLite answer now appears to
require a protected surface: query generation, provider acquisition, or ranking.
