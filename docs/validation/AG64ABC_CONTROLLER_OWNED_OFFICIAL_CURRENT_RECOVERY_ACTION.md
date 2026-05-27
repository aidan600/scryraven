# AG-64ABC Controller-Owned Official/Current Recovery Action

## Purpose

AG-64ABC extracted the official/current/canonical missing-source-class recovery
action into a controller-owned envelope, attempted and then focused-fix repaired
deterministic official/current numeric-rule acquisition helpers inside that
path, and ran bounded live reclassification after offline validation passed.

## Licensed Surfaces

Opened:

- controller-owned missing-source-class recovery action envelope;
- existing source-class recovery executor seam;
- deterministic official/current numeric-rule acquisition helpers for IRS, SSA,
  federal agency threshold/status/rule pages, and sibling official-current
  cases;
- offline tests, bounded live validation, and this compact validation note.

Closed:

- new providers, provider swaps, provider routing, provider depth, and provider
  pricing policy;
- broad retrieval ranking/filtering redesign;
- citation behavior, Author/final-answer posture, Economist behavior,
  Scrutineer policy, follow-up behavior, and weak-corpus policy;
- mixed canonical plus academic modeling;
- raw prompts, raw provider payloads, DB rows, private logs, caches, full
  traces, `.env`, and secrets.

## Implementation Summary

`SourceClassRecoveryActionEnvelope` now records the controller-owned recovery
action in compact trace-safe form. The lifecycle attaches the envelope to the
existing `source_class_recovery` action, and the executor validates that the
envelope is present and approved before spending the bounded recovery slot.

Official/current numeric-rule query acquisition now adds deterministic variants
for IRS mileage-rate notices, SSA contribution-and-benefit-base queries, DOL
federal minimum wage queries, USCIS N-400 fee queries, and general federal
agency eligibility/threshold/status/rule queries. A focused PR fix tightened the
intent-satisfaction check so generic `official current source ...` text does
not suppress required IRS/SSA/federal-agency numeric-rule variants. Existing
provider routing, search depth, ranking, citation, and final-answer behavior
remain unchanged.

A second focused PR fix localized the remaining IRS live failure to two
offline-reproducible gates: the IRS mileage-rate question could be represented
as `primary_source_documents` only, and weak-corpus/corpus-weak admission
blockers could preempt the official/current slot before the repaired IRS query
was visible. The source-class classifier now treats current/year-bound official
agency numeric rate/fee/threshold/status questions as
`official_current_rules`; execution admission and the controller allow
weak-corpus coexistence only for unsatisfied official/current/legal classes
when an official/legal recovery query is visible. Broad weak-corpus policy,
providers, routing, depth, ranking, citation, and final-answer behavior remain
unchanged.

A final offline-only dispatch fix addressed the last live-classified handoff
gap: when official/current recovery is admitted, eligible, unblocked, and backed
by an approved controller envelope, the controller loop now authorizes
`recover_missing_source_class` only when no competing checkpoint action owns the
turn. Explicit checkpoint actions and unavailable/error checkpoints remain
fail-closed.

## Offline Validation

Focused and inherited gates passed:

- source hierarchy and answer-contract invariants;
- AG-58A through AG-61A preservation suites;
- runtime AnswerContract handoff and adapter suites;
- official numeric grounding, obligation bridge, query acquisition, execution
  admission/dispatch, candidate acquisition, visibility/export, recovered
  evidence visibility, and source-class recovery suites;
- new AG-64ABC controller-envelope and numeric-rule acquisition tests.

Final focused offline result:

```text
307 passed, 1 xfailed
```

Focused PR-fix validation also passed:

```text
11 passed
43 passed
18 passed, 1 xfailed
```

Focused post-live-blocker validation passed:

```text
15 passed
61 passed
32 passed, 1 xfailed
```

Focused dispatch-handoff validation also passed:

```text
20 passed
96 passed
32 passed, 1 xfailed
1779 passed, 1 deselected, 1 xfailed
```

The AG-57A mixed canonical plus academic xfail remains parked.

## Live Validation

Bounded live runs used: 4 of 4.
Independent official public-source checks used: 2 of 4.
Optional live queries used: 0. The third run was a focused IRS-only
reclassification after the generic-query blocker fix. The fourth run was a
final IRS-only classification after CI was green and the offline dispatch
ownership fix had landed.

Detailed live outputs are local/untracked only:

```text
output/ag64abc_official_current_recovery_live_packet.md
```

The detailed packet and live reports are ignored under `output/` and are not
committed.

Compact classification:

- IRS 2026 standard mileage rate: safe insufficiency after official/current
  acquisition/source-fit failure. Controller-owned recovery ran, but the
  obvious official IRS source did not survive into usable/cited evidence.
- SSA 2026 taxable maximum wage base: pass. Official SSA source was acquired,
  cited, and used correctly.
- Focused IRS rerun after the generic-query blocker fix: still failed, but the
  live report showed `admission_not_used` with weak-corpus/corpus-weak blockers
  and canonical-documentation-flavored recovery previews. The intended
  high-signal IRS query is proven offline but was not visible in this live
  execution path.
- No additional live run was used for the second focused fix. Offline fixtures
  now prove that the IRS query is represented as `official_current_rules`,
  weak-corpus does not preempt the official/current slot, and live-style
  recovery previews include the high-signal IRS notice/revenue-procedure query.
  Product effect remains unvalidated after this second focused fix.
- Final IRS-only rerun after the CI fix: official/current recovery was visible,
  admission became eligible/used, and the high-signal IRS
  notice/revenue-procedure query appeared in report-visible previews. The
  source-class recovery executor still did not attempt recovery, no official IRS
  source survived to final citation, and the final answer preserved safe
  insufficiency posture.
- No additional live run was used for the dispatch-handoff fix. Offline fixtures
  now prove the admitted IRS official/current action reaches source-class
  recovery execution while checkpoint ownership guards remain intact. Product
  effect remains unvalidated after this offline-only fix because the AG-64ABC
  live budget is exhausted.

## Hygiene

No raw provider payloads, raw prompts, DB rows, private logs, caches, full raw
traces, `.env`, or secrets were inspected or included in committed artifacts.

## Next Action

If the IRS failure remains important, the next licensed surface should be a
fresh bounded validation phase that verifies the repaired dispatch handoff in
product. If the intended IRS query executes but providers still fail obvious
official/current sources, AG-65R provider/search allocation or source-specific
official-source adapter review is recommended before adding providers.
