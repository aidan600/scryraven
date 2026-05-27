# AG-49A Official Source Survival Instrumentation Diagnostic Validation

Status: completed bounded diagnostic validation

## Scope

AG-49A added passive, runtime-visible, sanitized official/current/canonical
source-survival diagnostics. It did not attempt to improve answer quality.

## Approved Query

What are the 2026 vs 2025 Social Security COLA, taxable maximum, earnings-test
limits, and SSI federal payment amounts?

## Live Budget Used

- Baseline live run before instrumentation: 1
- Post-instrumentation live rerun: 1
- Total live ProPlex runs used: 2 of 2
- Additional live reruns after offline refinement: 0

## Baseline Summary

The baseline answer supplied the requested 2026 vs 2025 values, but the visible
source mix did not make the source-survival stage diagnosable. It cited a
payroll.org-hosted SSA announcement PDF, secondary/tax-adviser sources,
financial/planning sources, and an SSA publication about work and benefits.

Using AG-48A and AG-48B, the baseline failure was classified as an
official/current numeric source-grounding issue whose exact source-survival
stage was not observable from allowed baseline artifacts. The visible answer did
not distinguish obligation detection, candidate query availability, official
candidate return, acceptance/readability, final-evidence survival, or
final-citation survival.

## Instrumentation Added

New helper:

- `core.official_source_survival_projection.build_official_source_survival_projection_trace`

Runtime attachment:

- `core.runtime_trace_projection_assembly.attach_passive_runtime_projection_traces`
  now attaches `official_source_survival_projection_trace` and mirrors it into
  the evidence-integration checkpoint packet when present.

Sanitized trace bridge:

- `core.pipeline_orchestrator` now exposes compact final-evidence and
  final-citation official/current/canonical counts derived from existing
  source-class observability counts.

The projection emits compact fields including obligation status, candidate
query count, candidate/accepted/final-evidence/final-citation counts when
observable, caveat/numeric/source-bound-value flags when observable,
`unknown_fields`, `missing_stage`, `recommended_next_lane`,
`source_survival_observability_status`, and `behavior_changed=false`.

## Post-Instrumentation Rerun Summary

The post-instrumentation live rerun attached the sanitized projection and
surfaced:

- `final_evidence_official_or_canonical_count = 1`
- `final_citation_official_or_canonical_count = 1`
- `source_bound_value_present = true`
- `candidate_official_or_canonical_count = unknown`
- `accepted_official_or_canonical_count = unknown`
- `behavior_changed = false`

The answer also cited the direct SSA 2026 COLA fact sheet. That answer-quality
change was incidental and is not the AG-49A success criterion.

The live projection exposed one diagnostic bug: source obligation was marked
not required because existing source-class expectation fields did not expose
the official/current obligation. The final code fixes that offline with a
generic public-program numeric obligation inference from safe query-preview
terms while separately reporting `obligation_detected=false` when runtime did
not expose the obligation. No extra live rerun was performed because the live
budget was exhausted.

## Before/After Diagnostic Observability

Before AG-49A, the approved query could only be reviewed from the final answer
and final citations. The failure could not be localized beyond "official/current
source grounding not safely localizable."

After AG-49A, the runtime-visible sanitized projection can show when final
evidence and final citation contain official/current/canonical sources, while
preserving candidate and acceptance facts as `unknown` when they are not safely
available. For the approved query shape, the final code also separates
`source_obligation_required=true` from `obligation_detected=false`, which makes
the source-obligation detection gap explicit.

The new diagnostics made the failure stage clearer. The bounded validation
showed that the direct final-citation path can now be seen, and the remaining
gap is earlier: runtime did not expose the official/current source obligation
for this public-program numeric query.

## Answer Quality

Answer improvement is not the AG-49A success criterion. The post run happened
to cite a better direct SSA source and gave a stronger answer, but this phase
only claims improved diagnostic visibility.

## Behavior Changes

No runtime retrieval or answer behavior was intentionally changed. The new
fields are passive diagnostics only:

- provider policy unchanged;
- provider selection unchanged;
- search depth unchanged;
- query generation unchanged;
- prompt behavior unchanged;
- source ranking unchanged;
- runtime source-classification behavior unchanged;
- Economist, Analyst, Author, Scrutineer, and final-answer behavior unchanged;
- controller dispatch/runtime authority unchanged.

## Protected-Surface Scan

The implementation does not inspect or expose secrets, `.env` contents, raw
provider payloads, raw prompts, DB rows, caches, private logs, full raw traces,
or unrelated generated packets. Sensitive keys are dropped from projection
inputs, protected marker text is redacted, and tests cover protected-value
redaction.

## Local Output-Quality Packet

Local packet path:

`output/ag49a_output_quality_review_packet.md`

Ignored/untracked confirmation:

- `git check-ignore -v output/ag49a_output_quality_review_packet.md` matched
  `.gitignore:39:output/`
- `git ls-files output` returned no tracked files

The packet was not committed.

## Still Not Authorized

AG-49A still does not authorize provider routing, provider selection, provider
depth, provider escalation, query-generation changes, prompt changes, source
ranking changes, runtime source-classification behavior changes, evidence
visibility behavior changes beyond passive diagnostics, Economist/Analyst/
Author/Scrutineer changes, final-answer behavior changes, controller dispatch
authority changes, legal/current adapter implementation, source-specific hacks,
or additional live runs.

## Consumer, Decision, Deletion Criteria

Consumer:

- local output-quality review packet;
- future official/current/canonical source-quality validation;
- AG-48A/B diagnostic classifiers;
- AG-48C next-lane decision follow-up.

Decision enabled:

- distinguish source obligation not detected;
- distinguish candidate query unavailable;
- distinguish official/current/canonical candidate visibility unavailable;
- distinguish candidate accepted/readable status unavailable;
- distinguish accepted source absent from final evidence when safe facts exist;
- distinguish final evidence source not cited;
- distinguish cited source present but value extraction/source binding not
  visible;
- distinguish stage not observable from allowed artifacts.

Deletion or promotion:

- keep if used by AG-49 validation and future official-source quality phases;
- collapse if source-survival diagnostics move into a consolidated controller
  handoff;
- remove or simplify if later validation shows the fields are redundant with an
  existing safe handoff.
