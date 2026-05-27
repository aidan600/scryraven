# AG-50C Recovery Execution Visibility in Allowed Live Artifacts

## Phase Purpose

AG-50C exposes AG-50B official/canonical recovery admission and source-class
recovery execution state in allowed live artifacts so the next repair can be
chosen without reading raw logs, DB rows, caches, provider payloads, prompts, or
full traces.

## Opened Surface

Opened surface:

- allowed-artifact telemetry/report export only.

Still protected:

- provider routing, provider selection, provider depth/search depth, provider
  escalation, provider roles, recovery query wording, source ranking/filtering,
  returned-source classification, prompts, Economist/Analyst/Author/Scrutineer
  handoffs, final-answer behavior, and source-specific rules or domains.

## Behavior Change

New helper:

- `core.official_canonical_recovery_visibility_export`

New allowed artifact section:

- `Official / Canonical Source Recovery Diagnostics`

The helper consumes already-sanitized runtime trace fields and renders a compact
diagnostic section for CLI report output. It also attaches a sanitized passive
projection under:

- `official_canonical_recovery_visibility_export`

The CLI appends the diagnostic section to the emitted report text. The underlying
pipeline final answer is unchanged.

## Live Budget Used

Approved query:

`Explain how PostgreSQL MVCC works, why it improves read/write concurrency, and what tradeoffs it creates. Do not assume the reader is a database expert.`

Budget used:

- Post-implementation live run: 1 of 1
- Baseline run: 0, per AG-50C brief
- Extra exploratory runs: 0

Independent qualitative source check:

- Not used.
- Disabled by default for AG-50C because this phase validates visibility/export,
  not source-quality truth.

## Live Artifact Visibility Result

The generated CLI report exposed the new diagnostic section from allowed
artifacts. The visible fields included:

- `admission_considered: true`
- `admission_eligible: true`
- `admission_used: true`
- `source_class_recovery_eligible: true`
- `source_class_recovery_used: false`
- `source_class_recovery_provider_role: source_class_recovery`
- `recovery_query_count: 1`
- `recovery_query_previews: canonical documentation PostgreSQL MVCC`
- `recovered_result_count: 0`
- `accepted_url_count: 0`
- `final_evidence_official_or_canonical_count: 0`
- `final_citation_official_or_canonical_count: 0`
- `likely_next_failure_layer: execution_not_attempted`
- `behavior_changed: false`

Unknowns were preserved for fields that were not safely observable:

- `candidate_official_or_canonical_count`
- `accepted_or_readable_official_or_canonical_count`
- `accepted_readable_visibility_status`

## Answer Quality Observation

The final answer remained broadly readable but still cited arXiv sources rather
than PostgreSQL documentation. AG-50C did not attempt to improve final answer
quality.

Final cited URLs visible in the report:

- `https://arxiv.org/pdf/1208.4179`
- `https://arxiv.org/html/2411.10005`

## Protected Surfaces Not Touched

AG-50C did not intentionally change:

- provider routing;
- provider selection;
- provider depth/search depth;
- provider escalation;
- provider roles;
- recovery query wording;
- query generation;
- source ranking/filtering;
- returned-source classification;
- prompts;
- Economist behavior;
- Analyst behavior;
- Author behavior;
- Scrutineer behavior;
- final-answer behavior;
- source-specific rules or domains.

## Local Output Packet

Local packet path:

`output/ag50c_output_quality_review_packet.md`

Ignored/untracked confirmation:

- `git check-ignore -v output/ag50c_output_quality_review_packet.md` matched
  `.gitignore:39:output/`
- `git ls-files output` returned no tracked files

The local packet must not be committed.

## Next Recommended Phase

Recommended next phase:

- Investigate why the allowed artifact shows AG-50B admission was used and
  source-class recovery was eligible, but source-class recovery execution was not
  attempted.

That phase should stay scoped to the execution-dispatch/lifecycle boundary
unless a new brief explicitly opens provider acquisition, ranking, citation
selection, or final-answer behavior.
