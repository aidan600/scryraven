# AG-20 Official Source Recovery Quality

Mode: Architecture Groove / Prove Mode, Path B.

Scope: offline-only source-class recovery query quality and a narrow
weak-corpus/source-class ownership boundary revision for current
legal/regulatory questions.

## Outcome Classification

AG-20 classified the AG-19 failures as bounded A/B:

- Outcome A, query-template / official-source hint issue, applied to AG-19 Case
  A. Source-class recovery executed, but deterministic queries were too generic
  to reliably aim at official/legal/current-primary DOT material.
- Outcome B, narrow weak-corpus/source-class ownership issue, applied to AG-19
  Cases B and C. Current legal/regulatory cases with explicit official/legal
  source-class gaps could be blocked by weak-corpus recovery before the existing
  source-class recovery lane made one official-source attempt.

No offline fixture indicated Outcome C provider/routing/search-depth failure.
No offline fixture indicated Outcome D ranking/filtering/final-evidence failure.
Outcome E did not apply because the A/B fixes were testable with deterministic
offline fixtures.

## AG-19 Diagnosis

Diagnosis used the committed AG-19 validation summary only:
`docs/validation/AG19_RECOVERED_EVIDENCE_VISIBILITY_LIVE_VALIDATION.md`.

- A-style failure: source-class recovery fired with provider role
  `source_class_recovery` and preserved `basic` depth, but recovered
  secondary/unknown results and produced `recovery_source_quality_status =
  no_relevant_sources`.
- B/C-style failure: weak-corpus recovery owned the path before
  source-class recovery could execute, even though the answer contract still
  needed official/current/legal evidence.
- D/E/F controls: no source-class overfire was observed for recommendation,
  historical, or quantitative controls.

No `output/` artifact or AG-19 output-quality packet was inspected or copied.

## Query Construction Changes

Changed only deterministic source-class recovery query construction in
`core/source_class_recovery.py`.

- `official_current_rules` queries now include official-source and primary legal
  retrieval terms: official source, current rule, agency guidance, Federal
  Register, CFR/eCFR, GovInfo, final rule, compliance date, enforcement status,
  and official requirements.
- `legal_or_regulatory_text` queries now include statute/regulation text,
  CFR/eCFR, Code of Federal Regulations, Federal Register, GovInfo, final rule,
  docket, compliance date, and regulation text terms.
- `current_primary_or_official` queries now include current official primary
  source, agency guidance, Federal Register, enforcement status, final rule,
  court status, and compliance date terms.
- Query hints are ordinary search terms, not `site:` routing directives.

## Official-Source Target Hints

Added a pure deterministic helper that recognizes common public-authority
contexts and appends compact official-source terms:

- DOT / transportation / airline-passenger contexts:
  `transportation.gov`, `DOT`, `14 CFR Part 382`, `Air Carrier Access Act`.
- FTC / noncompete / negative-option contexts:
  `ftc.gov`, `Federal Register`, `final rule`, `court status`.
- FDA / LDT / medical-device contexts:
  `fda.gov`, `Federal Register`, `enforcement discretion`, `final rule`.
- OSHA hazard-communication contexts:
  `osha.gov`, `29 CFR 1910.1200`, `Federal Register`.
- IRS tax-credit contexts:
  `irs.gov`, forms, instructions, Internal Revenue Bulletin.
- CFPB consumer-finance contexts:
  `consumerfinance.gov`, rule, guidance.
- SEC / issuer-filing contexts:
  `sec.gov`, EDGAR, issuer filing.

The helper does not change provider routing, provider selection, search depth,
provider APIs, prompts, ranking, filtering, persistence, or visibility.

## Weak-Corpus Boundary

AG-20 changed the source-class controller only for this narrow condition:

- the recommendation reason uses an answer-contract source-class gap;
- the missing class intersects `official_current_rules`,
  `legal_or_regulatory_text`, or `current_primary_or_official`;
- weak-corpus recovery already ran and did not leave useful official/legal
  authority signals in compact evidence signals;
- source-class recovery has not already run;
- the existing answer-contract source-class slot is available;
- recovery queries already exist;
- provider role remains `source_class_recovery`;
- current search depth is reused.

Generic weak-corpus candidates without an answer-contract official/legal gap
remain weak-corpus-owned. Duplicate source-class attempts remain blocked.

## Protected Surfaces

Preserved:

- provider routing and provider selection;
- search-depth policy;
- prompt semantics;
- source ranking/filtering;
- persistence schema;
- Analyst/Economist/Author handoff;
- recovered-evidence visibility;
- AG-18 quantitative contradiction guard;
- live validation budget.

## Tests

Added `tests/test_ag20_official_source_recovery_quality.py`.

Positive fixtures:

- DOT-style current official/legal query generates stronger
  Federal Register/CFR/eCFR/GovInfo/transportation.gov/14 CFR Part 382 queries
  and recovers a `transportation.gov` official fixture through
  `source_class_recovery`.
- FTC-style current legal-status query generates FTC/Federal Register/final
  rule/court-status query terms and recovers a Federal Register fixture.
- FDA LDT-style regulatory query generates FDA/Federal Register/enforcement
  discretion terms and recovers an FDA fixture.
- Legal/regulatory text gap includes CFR/eCFR/GovInfo/Federal Register terms.
- Provider role remains `source_class_recovery`; search depth remains `basic`.

Weak-corpus boundary fixtures:

- FTC-style current legal/status weak-corpus case gets exactly one
  source-class recovery attempt.
- True weak-corpus case without an official/legal answer-contract gap remains
  weak-corpus-owned.
- Weak-corpus case with official evidence does not spend the exception.
- Duplicate source-class recovery attempt remains blocked.

Negative controls:

- Recommendation with legal/compliance constraint does not become
  answer-contract official-current recovery.
- Historical OSHA hazard-communication request does not become current-official
  recovery.
- Quantitative calorie-density request does not trigger source-class recovery.

Existing AG-17 and AG-18 tests remain the protected-surface checks for recovered
visibility and quantitative guard behavior.

## AG-21 Recommendation

AG-21 should be bounded live validation with rotated current legal/regulatory
queries that test:

- whether the strengthened deterministic queries recover official/legal/current
  primary sources;
- whether the narrow weak-corpus exception improves B/C-style answers;
- whether recovered official/legal sources surface without invoking protected
  ranking/filtering or recovered-visibility redesign.

If AG-21 shows official sources still cannot be retrieved through the existing
provider role and preserved depth, the next phase should stop for a
provider/retrieval design review rather than widening AG-20 heuristics.
