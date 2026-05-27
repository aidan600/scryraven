# AG-15 Source-Class Recovery Quality Diagnostics

Scope: offline diagnostics and narrow deterministic fixes only. No live
validation was run. No provider routing, provider selection, search-depth
policy, prompt semantics, persistence schema, source ranking/filtering, or
handoff redesign was changed.

## AG-14 Diagnosis

AG-14 proved that the AG-13 reserved active source-class recovery slot can
execute exactly one existing `source_class_recovery` attempt with provider role
`source_class_recovery` and preserved search depth. The remaining failure was
source quality and promotion visibility: the trace recorded only attempted
result/new URL counts before final evidence filtering, while final
official/legal/primary counts were recomputed later from final evidence. That
made these cases indistinguishable:

- recovery found only secondary/news sources;
- recovery found official/legal sources but they were not accepted;
- recovery accepted official/legal sources but final filtering did not expose
  them;
- recovery exposed sources but final source-class counts did not reflect them.

Case F exposed a separate quantitative consistency risk: deterministic
normalization can compute the correct denser item while final prose names the
other item.

## Fixed vs. Diagnosed

Fixed:

- Added compact recovered-source quality diagnostics on the existing active
  source-class recovery lifecycle trace.
- Added post-filter recovered-source visibility diagnostics after final evidence
  selection.
- Improved narrow legal/regulatory source-class recognition for CFR/eCFR,
  Federal Register, GovInfo, and Code of Federal Regulations text cues.
- Adjusted deterministic source-class recovery query templates for
  `official_current_rules`, `legal_or_regulatory_text`, and
  `current_primary_or_official` to emphasize official sources, agency guidance,
  Federal Register, GovInfo, CFR/eCFR, current rules, and enforcement status.
- Added a narrow shadow quantitative consistency diagnostic for two-item
  calories-per-gram comparisons.

Diagnosed only:

- No source ranking/filtering behavior was changed. If a live run finds official
  recovered sources with `recovered_promoted_source_count == 0`, AG-16 should
  treat that as a bounded source-ranking/filtering design decision rather than
  silently changing global ranking.

## Recovery Source Quality Measurement

New compact lifecycle fields:

- `recovered_source_tier_counts`
- `recovered_source_class_counts`
- `recovered_official_or_primary_count`
- `recovered_accepted_url_count`
- `recovered_promoted_source_count`
- `recovery_source_quality_status`

Statuses:

- `official_or_primary_found`
- `secondary_only`
- `no_relevant_sources`
- `classification_mismatch`
- `promoted_but_not_final`
- `unknown`

Named consumer: AG-15/AG-16 validation and source-class recovery trace review.

Decision enabled: distinguish official/legal/primary recovery success from
secondary-only recovery, accepted-but-not-final visibility, and classification
mismatch before considering protected ranking/filtering changes.

Deletion/promotion criterion: remove or promote these fields only after bounded
live validation proves whether recovered official/legal sources are accepted and
visible to final evidence often enough to support a smaller permanent metric or
a protected source-ranking/filtering design phase.

Validation tests:

- DOT official recovered source increments official recovered counts.
- FDA official recovered source increments official recovered counts.
- Federal Register, GovInfo, and eCFR recovered sources increment legal
  recovered counts.
- Secondary-only recovery stays `secondary_only` with zero official/legal count.
- Accepted recovered official source is visible in post-recovery telemetry.
- Provider role and search depth remain `source_class_recovery` / preserved
  existing depth.

## Classification and Query Construction

Classification improvement was narrow and source-class specific. AG-15 did not
change global ranking/filtering. CFR/eCFR, Federal Register, GovInfo, and Code
of Federal Regulations cues now support legal/regulatory source-class strength
when paired with authority domains or official source tiers.

Query construction changed only inside existing deterministic source-class
recovery helper templates. The templates remain capped by the existing recovery
query limit and still use the existing executor/provider/depth path.

## Promotion/Merge Status

Recovered passages are still merged additively. No pinning, boosting, or global
filtering change was made. `recovered_promoted_source_count` now shows whether
accepted recovered sources survived final evidence selection. If official/legal
sources are recovered but this count remains zero in live validation, that is an
AG-16 source-ranking/filtering design decision.

## Quantitative Consistency Guard

AG-15 added shadow diagnostics for simple two-item normalized comparisons. The
guard can use structured `normalize_per_100g` calculation inputs when available
or a deterministic query parse for patterns like `220 calories / 60g` vs.
`170 calories / 45g`. It computes normalized calories per gram, identifies the
computed winner, and flags when final prose names the other item as denser.

This does not rewrite Author prompts and does not alter Author behavior. A
correction mechanism remains out of scope.

Validation tests:

- `220 calories / 60g` vs. `170 calories / 45g` flags when prose names the
  220/60 bar as denser.
- The same comparison passes when prose names the 170/45 bar.
- Structured `normalize_per_100g` calculation inputs are used when present.

## Negative Controls

AG-15 preserved the existing controls for recommendation-with-legal-constraint,
historical/archival requests, social-provider-unavailable cases, bread/protein
bar quantitative cases, weak-corpus ownership, and retrieval-stop ownership.

## AG-16 Recommendation

Recommended next phase: bounded live validation of improved recovery quality.
If live telemetry shows `official_or_primary_found` with
`recovered_promoted_source_count == 0`, AG-16 should stop for a protected
source-ranking/filtering design decision. If live telemetry shows
`secondary_only`, AG-16 should focus on query/provider result quality. If the
quantitative contradiction recurs, run a separate quantitative-answer guard
phase rather than changing Author prompts inside source-class recovery.

No output-quality review packet, raw live output, or `output/` file should be
committed for AG-15.
