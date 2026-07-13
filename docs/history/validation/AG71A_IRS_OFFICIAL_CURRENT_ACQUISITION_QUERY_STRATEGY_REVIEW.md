Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG71A_IRS_OFFICIAL_CURRENT_ACQUISITION_QUERY_STRATEGY_REVIEW).

# AG-71A IRS Official/Current Acquisition Query Strategy Review

Scope: Review Lane diagnostic phase. No live ScryRaven/proplex queries,
provider/model/search calls, provider routing/depth/selection changes, broad
prompt changes, citation/final-answer changes, Author posture changes, direct
IRS hardcoding, package/CLI/env compatibility changes, or broad
`pipeline_orchestrator.py` domain logic changes were made.

Branch: `codex/ag71a-irs-official-current-acquisition-review`

Base commit: `11cef0d` (`Merge pull request #3 from aidan600/codex/scry02-compat-cli-env-aliases`)

## Phase Goal

Diagnose why the IRS 2026 business standard mileage-rate case did not produce
accepted/readable or final official/current IRS authority after recovery was
admitted, execution reached, and candidates returned in AG-70C.

Goal status: met as an offline diagnostic classification, with uncertainty
called out where raw/live evidence is intentionally unavailable.

## Primary Classification

Primary category: provider/source acquisition limits.

Confidence: medium-low. The classification is repo-evidence-based and not
proved by new live validation.

## Secondary Contributing Factors

- Query formulation remains a possible contributor, but the repo already
  produces IRS-specific recovery queries containing the target year, standard
  mileage-rate subject, official notice, and revenue-procedure terms.
- Candidate readability/acceptance remains a possible contributor for the
  exact returned live candidate set, but offline satisfying IRS authority
  candidates are accepted and preserved.
- Source-fit classification and visibility preservation are not the strongest
  current suspects because existing offline fixtures show official/current
  IRS-style candidates can be classified, selected, exported, and made citation
  eligible.

## Evidence

AG-70C classified the live IRS case as:

- recovery admitted;
- execution reached;
- candidates returned;
- no accepted/readable official/current IRS authority survived;
- no final official/current IRS authority was visible;
- the answer correctly refused to overclaim.

AG-64/68/69/70 offline seams show:

- IRS numeric-rule recovery can generate targeted official/current queries:
  `IRS 2026 standard mileage rate business official notice revenue procedure`
  and `IRS 2026 standard mileage rate revenue procedure official current source`.
- IRS official recovery domain constraints include `irs.gov` and federal
  official/legal domains, even when ordinary acquisition is corridor-bounded to
  secondary context domains.
- The source-class recovery executor merges recovery official-domain
  constraints into the recovery pass without changing provider routing or depth.
- A satisfying offline `irs.gov` candidate labeled as
  `official_current_rules` becomes accepted/readable authority evidence and
  final-selected authority evidence.
- Rejected/returned candidate counts are now split from accepted/readable and
  final-selected authority counts, so AG-70C's positive candidate-return signal
  should not be read as proof that readable IRS authority was available.

## Diagnostic Tests Added

Added:

- `tests/test_ag71a_irs_acquisition_query_strategy_review.py`

The tests prove:

- recovery-side official-domain constraints survive an ordinary secondary
  include-domain corridor and include `irs.gov` plus federal official/legal
  domains;
- an offline satisfying IRS official/current candidate survives
  source-fit/visibility into accepted/readable and final-selected authority
  evidence;
- no provider routing, provider selection, provider depth, ranking, prompt,
  citation, final-answer, or Author behavior is changed.

These tests are consumers of the AG-71A decision record only. They should be
kept while the AG-71A/AG-72R diagnostic chain is active, then either retained
as regression coverage for recovery-domain/visibility invariants or folded into
the existing AG-64/69 suites.

## Decision

The strongest offline classification is provider/source acquisition limits:
the lifecycle appears capable of dispatching an IRS-targeted recovery query,
including official IRS recovery domains, and accepting a satisfying
official/current IRS candidate if one reaches the visibility boundary. AG-70C's
live result still did not yield such a candidate in accepted/readable or final
authority evidence.

This does not prove that a provider swap, new provider, or depth change is the
right repair. AG-71A did not run live validation, inspect raw provider payloads,
inspect raw prompts, inspect DB rows, or inspect local output packets. The
result should therefore be treated as "likely provider/source acquisition
limits, not proven beyond offline evidence."

## Closed Surfaces

Remained closed:

- provider swap or new provider integration;
- provider routing, provider selection, and provider depth/search-depth policy;
- retrieval ranking/filtering;
- broad prompt behavior;
- citation behavior and final-answer behavior;
- Author posture;
- Analyst/Economist/Author handoffs;
- direct IRS answer/source hardcoding;
- broad `pipeline_orchestrator.py` domain logic;
- package/CLI/env compatibility behavior;
- live validation/provider/model/search calls.

## Recommended Next Branch

Recommended next branch: AG-72R provider/search allocation review.

Recommended branch shape:

- start as review/diagnostic, not repair;
- use only sanitized report-visible diagnostics unless a later brief explicitly
  authorizes live validation;
- distinguish existing-provider query/acquisition limits from provider result
  filtering and candidate readability before changing provider policy;
- keep citation/final-answer/Author behavior closed until accepted/readable or
  final official/current IRS authority is visible and then fails downstream.

AG-71B scoped query/candidate-fit/visibility repair is not recommended as the
first next branch from offline AG-71A evidence because those seams already pass
the targeted offline probes for satisfying IRS authority. It becomes appropriate
only if AG-72R or a separately approved live diagnostic identifies a concrete
existing-provider query variant, readability, candidate-fit, or visibility
defect.
