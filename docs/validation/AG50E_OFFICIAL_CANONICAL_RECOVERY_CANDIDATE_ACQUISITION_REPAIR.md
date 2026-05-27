# AG-50E Official/Canonical Recovery Candidate Acquisition Repair

## Phase Purpose

AG-50E repairs the bounded candidate-acquisition visibility seam after AG-50D
proved that an admitted official/current/canonical recovery slot reaches the
existing source-class recovery executor but can still return zero candidates.

The phase goal is not final answer quality. It is to make the already-admitted
slot show one of two outcomes:

- recovered candidates are visible; or
- zero candidates are accompanied by a precise sanitized blocker.

## Acquisition Seam Repaired

New helper:

- `core.official_canonical_recovery_candidate_acquisition`

Tiny executor attachment:

- `core.source_class_recovery_executor.execute_source_class_recovery_action`
  now updates the active source-class lifecycle trace after the existing
  injected acquisition call returns.

Allowed-artifact export:

- `core.official_canonical_recovery_visibility_export` now renders the AG-50E
  candidate-acquisition fields and zero-candidate blocker.

The helper consumes lifecycle fields, execution counts, and sanitized provider
diagnostics. It does not call providers, route providers, choose depth,
rank/filter sources, classify returned sources, alter prompts, or affect final
answer behavior.

## Protected Surface Opened

Opened surface:

- existing-provider official/canonical recovery candidate acquisition for the
  already-admitted recovery slot.

Still closed:

- new provider integration;
- provider swap;
- broad provider routing policy;
- broad search-depth policy;
- source ranking/filtering;
- returned-source classification;
- citation survival;
- Economist, Analyst, Author, Scrutineer, and final-answer behavior;
- source-specific rules or domains.

## Candidate Acquisition Result

Offline fixtures prove both bounded outcomes:

- a required canonical recovery execution with an AG-50A-style query can return
  `recovered_result_count > 0` and `candidate_return_status=candidates_returned`;
- a required official/current recovery execution can return an
  official/current visible candidate;
- zero-candidate execution now exposes a sanitized blocker such as
  `provider_returned_zero_results`.

## Live Validation

Live validation not used because offline tests were sufficient for this phase.

The phase changed trace/export behavior around a deterministic executor seam.
Focused fixtures could prove both success paths without spending live search
budget or inspecting raw traces, DB rows, caches, provider payloads, prompts, or
logs.

## Recovered Result Count

Fixtures moved `recovered_result_count` from `0` to `>0` for both:

- canonical candidate acquisition; and
- official/current candidate acquisition.

The zero-candidate fixture preserves `recovered_result_count=0` and adds
`zero_candidate_blocker_kind=provider_returned_zero_results`.

## Canonical Candidate Visibility

Canonical candidates became visible in fixture path through:

- `candidate_return_status=candidates_returned`;
- `official_canonical_candidate_visible=true`;
- `recovered_source_tier_counts` and recovered quality diagnostics from the
  existing source-class recovery path.

## Next Failure Layer

For successful fixture acquisition:

- `likely_next_failure_layer=official_canonical_candidate_visible`.

For zero-candidate fixture acquisition:

- `candidate_return_status=zero_candidates`;
- `zero_candidate_blocker=provider_returned_zero_results`;
- `next_failure_layer=execution_attempted_zero_candidates`.

If live output later shows recovered candidates that are accepted/readable but
not cited, the next protected surface to open should be citation survival or
citation-source fit. If candidates are not accepted/readable, the next surface
should be evidence acceptance/source fit. If candidates remain zero with a
specific provider/depth blocker, that later phase should decide whether to open
provider depth or routing explicitly.
