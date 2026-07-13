Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96A2_AUTHORITY_ACQUISITION_POLICY).

# AG-96A2 Authority Acquisition Policy

## Problem Statement

Fast mode must quickly find official/current primary sources for knowable
ground-truth items such as rates, filing fees, forms, notices, agency rules, and
regulatory status. Hard-domain shortcuts are allowed when provenance is strong:
for example, IRS mileage-rate questions may go first to IRS, and SEC filing
questions may go first to SEC.

The failure mode AG-96A2 prevents is different. ScryRaven must not turn a small,
hand-maintained set of official domains into the universal repair pattern for
every official-source miss. A preferred domain can be a useful shortcut, but an
incomplete domain table must not become an answer key.

## Core Abstraction

Official authority acquisition is an Authority Acquisition Decision. The
decision chooses one corridor:

- `hard_corridor`: provider domain constraints may be used.
- `soft_corridor`: candidate authorities or domains may guide query terms and
  ordering, but must not silently become provider hard filters.
- `discovery_corridor`: the system should discover the competent authority
  without forcing a known-domain shortcut.

## Corridor Policy

Hard corridor is reserved for explicit or very strong authority cues, including
named agencies, official domains, forms, filing systems, notices, bulletins,
statute venues, regulations, or similarly strong source-venue signals.

Soft corridor is for high-confidence known authority-family candidates where
the likely venue is useful but not strong enough to cage retrieval. Soft
candidates may influence authority query terms, acquisition ordering, or
diagnostics, with an escape path.

Discovery corridor is for unknown, off-list, non-U.S., ambiguous,
role-described, or jurisdiction-conflicted authority questions. Role hints such
as "official regulator," "competent authority," "legal source," or
"government source" guide discovery; they do not force hard domains.

## Decision Fields

AG-96A2 should implement or prepare for these machine-readable fields near the
existing official authority acquisition plan:

- `decision_type` and corridor strength.
- Authority basis and provenance.
- Explicit authority cues, when available.
- Jurisdiction and jurisdiction basis, when inferable.
- Candidate authorities, domains, and venues.
- Disqualifying jurisdiction signals.
- Confidence fields for hard and soft candidates.
- Widening or fallback posture.
- Diagnostics or rejection summary when already near an existing diagnostic
  seam.

## Failure Modes

- Authority overconstraint: a shortcut blocks the correct official source.
- U.S. regulator gravity: U.S. agencies dominate non-U.S. questions due to
  keyword overlap.
- Near-list false positives: words like workplace, food, consumer finance, or
  securities trigger the wrong known family.
- Stale official-source success: an official page is found but is not current
  enough for the obligation.
- Generic official-page success: a government page is found but does not answer
  the required source obligation.
- Readable-page bias: easy-to-read pages displace canonical notices, rules,
  forms, filings, or legal text.
- Citation laundering: secondary summaries are treated as if they supply the
  official authority.
- Family-table creep: every dogfood miss adds another hardcoded domain.
- Discovery starvation: hard or soft shortcuts prevent unknown authority
  discovery.
- Trace-only authority: a decision is recorded but not consumed by the runtime
  acquisition path.

## Fast / Balanced / Deep Contract

Fast is precision-first official/current acquisition. It may use strong hard
corridors and one bounded discovery escape, but should prefer strict
insufficiency over secondary-source overclaim when official/current authority
remains unsatisfied.

Balanced may consider more candidate authorities and official venues. Secondary
sources may be used as discovery bridges, not as substitutes for the required
official/current authority.

Deep may perform broader authority mapping, jurisdiction comparison, conflict
analysis, and currentness analysis.

## AG-96A2 Implementation Slice

AG-96A2 should implement the smallest consumed decision/corridor policy slice:

- Add or extend the existing official authority acquisition plan with an
  Authority Acquisition Decision.
- Distinguish hard, soft, and discovery corridors.
- Preserve hard corridors for explicit or strong authority provenance.
- Keep soft family matches out of provider hard-domain filters.
- Put unknown, off-list, non-U.S., ambiguous, and role-only questions into
  discovery posture.
- Prove hard, soft, and discovery behavior with offline tests.
- Prove off-list resilience and near-list restraint.
- Keep diagnostics sufficient to explain why a domain was hard, soft, or
  discovery-only.

## Deferred Work

AG-96A2 does not implement:

- A comprehensive official-domain catalog.
- Denmark, EU, Canada, or other one-off domain fixes.
- Source-specific adapters.
- New providers.
- Provider swaps.
- Broad ranking or reranking redesign.
- Final-answer, Author prose, or citation behavior changes.
- Live validation.

## Review Checklist

- Is the decision consumed by the runtime acquisition path, not trace-only?
- Are hard domains limited to strong provenance?
- Do off-list and non-U.S. fixtures avoid forced U.S. known-domain constraints?
- Does near-list overlap avoid caging search in the wrong domain?
- Did `core/pipeline_orchestrator.py` remain a coordinator rather than a domain
  brain?
- Was live validation not run?
