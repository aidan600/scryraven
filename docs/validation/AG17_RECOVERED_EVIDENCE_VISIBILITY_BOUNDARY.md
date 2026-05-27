# AG-17 Recovered Evidence Visibility Boundary

Scope: offline implementation and validation only. No live validation was run.
No provider routing, provider selection, search-depth policy, prompt semantics,
persistence schema, global source ranking/filtering, weak-corpus ownership,
retrieval-stop ownership, or downstream Analyst/Economist/Author handoff
redesign was changed.

## Design Decision

AG-17 adds a small pure recovered-evidence visibility boundary in
`core/recovered_evidence_visibility.py`.

The boundary runs after active source-class recovery execution and after normal
final evidence filtering. It can reserve at most one recovered source by
default, with a hard helper cap of two, when the recovered source is a strong
official/legal/primary match for an answer-contract source-class gap.

This is a bounded post-filter reservation rule. It does not rewrite
`filter_top_evidence`, generic scoring, domain caps, provider weights, provider
routing, provider lists, search depth, prompt semantics, persistence, or
downstream handoff design.

## Reserved-Source Conditions

A recovered source may be reserved only when all of these are true:

- active source-class recovery was used;
- provider role is `source_class_recovery`;
- the active recovery reason starts with `answer_contract_official_gap`,
  `answer_contract_legal_text_gap`, or `answer_contract_current_primary_gap`;
- recovered source quality is not `secondary_only`, `no_relevant_sources`, or
  `classification_mismatch`;
- the source has a strong official/legal/primary/current-primary class signal;
- the strong recovered source class matches the missing contract-critical class;
- the source is not already visible in final evidence;
- the source is not a duplicate of an already-visible source;
- weak-corpus ownership did not block source-class recovery;
- duplicate source-class recovery attempt prevention remains active;
- historical/archival sources are not treated as current-official sources.

If normal final evidence is below the evidence cap, the recovered source is
appended. If normal final evidence is already at cap, the boundary may replace
at most one non-recovered lower-priority source. If no replaceable source
exists, the recovered source is dropped with a stable reason.

## Trace Fields

New compact fields are added through the active source-class recovery lifecycle
trace:

- `recovered_visibility_considered`
- `recovered_visibility_eligible`
- `recovered_visibility_used`
- `recovered_visibility_reason`
- `recovered_visibility_blockers`
- `recovered_visibility_missing_source_class`
- `recovered_visibility_recovered_source_class`
- `recovered_visibility_reserved_count`
- `recovered_visibility_reserved_source_ids`
- `recovered_visibility_reserved_source_classes`
- `recovered_visibility_dropped_source_ids`
- `recovered_visibility_drop_reason`

Named consumer: AG-17 validation, source-class recovery trace review, and
future bounded live validation triage.

Decision enabled: distinguish recovered official/legal/primary sources that
were reserved into final evidence from sources that were dropped because they
were secondary-only, no relevant source, classification mismatch, duplicate,
already visible, class-mismatched, historical/archival current mismatch, or
blocked by cap/no replaceable source.

Deletion/promotion criterion: remove or promote these fields after bounded live
validation proves whether the reservation rule is stable enough to become a
smaller permanent source-quality metric or whether a separate ranking/filtering
design phase is required.

## Handoff Consistency

When a recovered source is reserved, runtime answer-contract handoff receives
the final source-class observability telemetry and a runtime-only lifecycle view
with the reserved missing class removed. The persisted execution trace keeps
the original active recovery missing classes plus the recovered-visibility
decision fields. This keeps the handoff consistent for the reserved source
without redesigning downstream Analyst/Economist/Author behavior.

## Tests

Added `tests/test_ag17_recovered_evidence_visibility.py`.

Positive coverage:

- DOT-style recovered official source for `official_current_rules` is reserved;
- Federal Register, eCFR, and GovInfo-style legal/regulatory recovered sources
  are eligible;
- current-primary/current-official recovered source is reserved;
- already-visible recovered source is not duplicated;
- final-cap pipeline case replaces one lower-priority non-recovered source;
- visibility decision records reason, reserved count, source identity, and
  recovered source class;
- provider role remains `source_class_recovery`;
- search depth remains preserved.

Negative controls:

- `secondary_only` recovery reserves nothing;
- `no_relevant_sources` recovery reserves nothing;
- `classification_mismatch` recovery reserves nothing;
- recommendation-with-legal-constraint is not hijacked without an
  answer-contract reason prefix;
- historical/archival source does not become current-official evidence;
- quantitative non-active case reserves nothing;
- social-provider-unavailable case reserves nothing;
- weak-corpus-owned case reserves nothing;
- duplicate source-class recovery attempt case reserves nothing.

## Protected Surfaces Preserved

Preserved:

- global source ranking/filtering;
- generic scoring;
- domain caps;
- provider routing and provider selection;
- provider role and provider list;
- search-depth policy;
- prompt text and prompt semantics;
- persistence schema and JSONL/SQLite semantics;
- weak-corpus and retrieval-stop ownership;
- Analyst skip, Economist shortcut, and Author prompt behavior;
- quantitative contradiction shadow diagnostic.

## Stop Conditions

Future work should stop for a design-decision packet if passing tests or live
validation requires any of the following:

- broad ranking/filtering change;
- provider routing or provider selection change;
- search-depth policy change;
- prompt rewrite;
- persistence schema change;
- downstream handoff redesign;
- weak-corpus or retrieval-stop ownership redesign;
- live call budget;
- output-quality review packet or raw live output inspection.

## Recommendations

AG-18 should be a separate quantitative contradiction guard phase. AG-17 did
not change Author prompts or add a correction pass for quantitative prose.

AG-19 should be bounded live validation with rotated queries. It should verify
that recovered official/legal/primary reservations survive final evidence and
that secondary-only, no-relevant-source, historical/archival, recommendation,
social, weak-corpus, duplicate-attempt, and quantitative controls remain
blocked.

No output-quality review packet, raw live output, or `output/` file was created
or committed for AG-17.
