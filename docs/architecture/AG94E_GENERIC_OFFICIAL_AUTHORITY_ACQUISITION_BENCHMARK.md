# AG-94E Generic Official Authority Acquisition Benchmark

Status: implemented as an offline multi-family benchmark with one bounded
generic source-obligation recognition repair.

Validation boundary: repo-visible code, docs, and synthetic fixtures only. No
live provider, model, search, retrieval, secret, `.env`, DB row, raw provider
payload, raw prompt, private log, cache, full trace, local output packet, or
private artifact access was used.

## Executive Verdict

AG-94E confirms that the official-source acquisition problem is generic, not a
REAL ID/TSA problem. The new benchmark covers current government rules,
food/product safety regulation, tax numeric rates, canonical technical docs,
legal/regulatory primary text, official product release/status material,
issuer-primary disclosures, and an ordinary explainer control.

Before the repair, explicit food/regulatory approved-list, current
statute/regulation, and official product release/changelog requests could fail
to become source-class recovery obligations. AG-94E adds one bounded generic
repair in `core/source_class_recovery.py`: explicit legal/regulatory primary
requests and official product release/status requests are now classified as
strong source obligations, and legal/regulatory presence is not considered
satisfied by generic secondary-only domains.

No domain registry, source-specific adapter, provider swap, provider ordering,
search-depth change, Author prose change, citation behavior change, or
`pipeline_orchestrator.py` rewrite was introduced.

## Why AG-94E Exists And Why It Is Not REAL ID/TSA

AG-94D diagnosed a live-shaped official-source acquisition failure using an
airport-ID fixture, but that fixture was only a regression support artifact.
AG-94E generalizes the question: when the user asks for official/current,
regulatory, canonical, legal-primary, issuer-primary, or source-bound numeric
evidence, does the system treat lower-tier material as a lead instead of
satisfaction and seek the strongest available authority?

The benchmark includes one airport/REAL-ID-style row, marked regression-only.
It is not the design target and it does not add TSA/DHS terms, domains, or
adapters.

## Generic Authority Family Taxonomy

| Family | Source obligation expected | Evidence that can satisfy | Lower-tier role | Must not satisfy | Acquisition posture | Missing-authority posture |
| --- | --- | --- | --- | --- | --- | --- |
| Current government rule / eligibility / official guidance | `official_current_rules` | Current official guidance, rule text, notice, or agency-primary eligibility/access material | Lead/context only | News, explainers, community posts, stale archives | Seek current official or agency-primary authority | State official current authority is missing |
| Food or product safety regulation / approved list | `legal_or_regulatory_text` | Current regulator-primary rule text, approved list, legal act, official guidance, or canonical register entry | Lead/context only | Manufacturer summaries, trade press, news, blogs | Seek regulator/legal-primary current authority | Do not treat secondary approved-list claims as enough |
| Tax / official numeric rate / official threshold | `official_current_rules` | Tax authority notice, official table, form instruction, or current agency page | Lead/context only | Tax blogs, news summaries, calculators, forum posts | Seek official source-bound numeric authority | Numeric value remains insufficient without official authority |
| Canonical technical docs / package behavior | `primary_source_documents` | Canonical project docs, reference manual, release docs, or maintainer-primary docs | Lead/context only | Q&A pages, blogs, academic papers, tutorials | Seek canonical docs/reference source | Explain canonical documentation was not acquired |
| Legal or regulatory primary/current rule | `legal_or_regulatory_text` | Primary legal text, regulator rule text, official register, code, or current status from court/regulator primary material | Lead/context only | Law firm alerts, news, explainers, summaries | Seek legal/regulatory primary authority | Caveat missing primary legal authority |
| Official product status / release / changelog | `primary_source_documents` | Official release notes, changelog, status page, support matrix, or maintainer-primary announcement | Lead/context only | News, forum posts, mirrors, third-party trackers | Seek official product-primary status source | Say official product status was not acquired |
| Issuer / filing / primary corporate disclosure | `issuer_filings_or_company_materials` | Issuer filing, earnings release, investor presentation, annual/quarterly report, or company-primary disclosure | Lead/context only | Analyst articles, finance news, quote pages, social posts | Seek issuer-primary disclosure | Company-reported value is insufficient without issuer-primary evidence |
| Ordinary explainer control | `none` | Ordinary reputable context can be sufficient | Ordinary evidence, not merely a lead | Not applicable unless user asks for official/current/primary authority | Do not over-require official sources | No official-source insufficiency should be introduced |

This taxonomy uses authority roles/classes only. It does not define correct
domains for any family.

## Benchmark Fixture Matrix

New focused suite:
`tests/test_ag94e_generic_official_authority_acquisition_benchmark.py`.

| Fixture | Family | Synthetic provider/source shape | Expected current AG-94E layer |
| --- | --- | --- | --- |
| REAL ID / airport accepted-ID regression-only | Current government rule | Secondary lead plus synthetic official current guidance | `official_source_acquisition_quality_satisfied` |
| Danish baby-formula additive approved list | Food/product safety regulation | Secondary/trade/manufacturer leads only | `provider_or_query_failed_to_return_official_candidate` after the AG-94E recognition repair |
| Current statute/regulation security-deposit rule | Legal/regulatory primary | Secondary legal explainers only | `provider_or_query_failed_to_return_official_candidate` after the AG-94E recognition repair |
| 2026 tax mileage/rate fixture | Tax numeric rate | Synthetic official current candidate with failed readability | `official_candidate_readability_or_passport_failed` |
| Package cache invalidation docs | Canonical technical docs | Secondary tutorial plus synthetic canonical docs | `official_source_acquisition_quality_satisfied` |
| Canonical docs provider forwarding drop | Canonical technical docs | Synthetic provider bridge has unrepresented canonical docs result | `provider_result_forwarding_or_filtering_dropped_official_candidate` |
| Canonical docs wrong primary kind | Canonical technical docs | Official-looking guidance, but not canonical docs | `candidate_source_fit_rejected_official_candidate` |
| Product version release/changelog status | Official product status | Secondary release-news lead plus synthetic release note | `official_source_acquisition_quality_satisfied` after the AG-94E recognition repair |
| Issuer quarterly primary disclosure | Issuer/filing primary | Secondary finance lead plus issuer-primary release | EvidenceLedger satisfies issuer-primary obligation; official/canonical export remains diagnostic-only for this family |
| Canonical docs accepted then final projection missing | Canonical technical docs | Candidate fit accepts docs but final authority count is zero | `accepted_official_candidate_lost_after_acquisition` |
| Coffee bitterness explainer | Ordinary control | Ordinary secondary explainer | No official-source overrequirement |

All rows use synthetic records only, with `.example` URLs. No live web,
provider, search, retrieval, raw provider payload, or local output packet is
used.

## Lower-Tier-As-Lead Vs Lower-Tier-As-Satisfaction Rule

For official/current/legal/canonical/source-bound/issuer-primary obligations,
secondary, news, community, social, or explanatory sources may provide context,
entity hints, vocabulary, or lead material. They cannot satisfy the stronger
source obligation.

The benchmark proves this through EvidenceLedger fixtures for
`official_current_rules`, `legal_or_regulatory_text`,
`primary_source_documents`, and `issuer_filings_or_company_materials`.
Lower-tier candidates can be linked as custody observations, but the
requirement remains unsatisfied.

## What The Benchmark Proves About Current Behavior

The benchmark proves the following offline facts:

- Strong authority candidates can be accepted and projected when the obligation
  is recognized and the candidate fits.
- Secondary-only provider results now reach a provider/query failure layer for
  legal/regulatory approved-list and current-statute cases instead of staying at
  source-obligation non-recognition.
- Official-looking but wrong-kind candidates fail at source fit.
- Unreadable official-looking candidates fail at readability/passport.
- Accepted authority candidates missing from final authority projection are
  classified as final custody/projection loss.
- Issuer-primary obligations are recognized and can satisfy EvidenceLedger, but
  the official/canonical visibility export is not a complete issuer-family
  success metric.
- Ordinary explainer controls do not over-require official authority.

## Gaps Found, Classified A-I

| Code | Meaning | AG-94E finding |
| --- | --- | --- |
| A | Source obligation not recognized | Proven before repair for food/regulatory approved list, current statute/regulation, and official product release/changelog. Repaired generically for explicit legal/regulatory primary and official product status requests. |
| B | Acquisition plan too generic / authority intent weak | Still a follow-up risk. AG-94E did not rewrite broad legal/query templates or provider strategy. |
| C | Secondary/news treated as satisfying stronger obligation | Not found after the repair in the benchmark. EvidenceLedger keeps lower-tier material as unsatisfied for strong obligations. |
| D | Official candidate not preserved from provider result to candidate acquisition | Diagnosable through the canonical-docs provider bridge fixture. No provider forwarding behavior was changed. |
| E | Official candidate rejected by source fit | Diagnosable and correct for wrong primary kind in the canonical-docs fixture. |
| F | Official candidate unreadable/passport failed | Diagnosable through the unreadable tax-rate official candidate. |
| G | Accepted official evidence lost before EvidenceLedger/final authority | Diagnosable through accepted canonical docs with final authority count zero. No custody behavior changed. |
| H | Ordinary control over-required official authority | Not found. Ordinary explainer control remains no-recovery. |
| I | Diagnostic-only gap, no behavior proof | Issuer-primary success is EvidenceLedger-visible, but official/canonical export fields are not a complete issuer-family metric. |

## Bounded Repair Implemented

Repair: generic source-obligation recognition in `core/source_class_recovery.py`.

Old behavior:

- Explicit food/product approved-list regulation wording could fail to produce
  a legal/regulatory source obligation.
- "What does the current statute or regulation require..." wording could fail
  to produce a legal/regulatory source obligation.
- Official product release note/changelog support-status wording could fail to
  produce a canonical/primary-document obligation.
- Once `legal_or_regulatory_text` was expected by this path, generic
  secondary-only domain context could be considered present by the fallback
  branch.

New behavior:

- Explicit official legal/regulatory primary requests, current
  statute/regulation requirement requests, and approved-list regulation requests
  produce a `legal_or_regulatory_text` obligation.
- Official product release note, changelog, support matrix, status page, or
  version-support requests produce a `primary_source_documents` obligation.
- Legal/regulatory presence requires official evidence or legal-authority
  domain signal; secondary-only domains do not satisfy it.

Runtime consumer:

- `build_source_class_recovery_recommendation()` consumes the new recognition
  and emits missing source classes plus existing generic recovery queries.

Proof tests:

- `tests/test_ag94e_generic_official_authority_acquisition_benchmark.py`
  passes across more than four unrelated authority families, including the
  non-US/non-transport Danish food-regulation fixture.

Closed behavior:

- No domain registry.
- No source-specific adapter.
- No provider swap/order/depth/search-budget change.
- No broad query-template rewrite.
- No Author/prose/citation change.

## Behavior Changes Kept Closed

AG-94E did not change:

- provider routing, provider selection, provider order, search depth, search
  budget, or provider integration;
- source-specific domain mappings or curated authority registries;
- TSA/DHS, IRS, Danish regulator, package-docs, issuer-filing, or other
  source-specific adapters;
- broad query templates beyond reusing existing recovery-query generation after
  recognition;
- ranking/filtering, citation behavior, Author prose, prompts, final answer
  formatting, package/CLI/env/database names, or session state names;
- `core/pipeline_orchestrator.py`.

## Domain Registry Decision

Not introduced.

AG-94E did not expand `core/official_authority_venue_soft_domains.json` and did
not add a new curated domain mapping. The benchmark intentionally uses roles
and synthetic `.example` source records instead of "correct domain" answers.

## Source-Specific Adapter Decision

Not introduced.

No REAL-ID/TSA/DHS, IRS, Danish food-regulator, package-specific docs,
corporate-filing, or other corridor-specific adapter was added.

## Provider / Live Decision

Not used.

No live ScryRaven/proplex provider, model, search, retrieval, or external web
call was run.

## Overfit Guard

The AG-94E benchmark guard asserts:

- at least eight task fixtures;
- at least six authority families;
- one non-US/non-transport fixture;
- one canonical technical-docs fixture;
- one ordinary explainer control;
- REAL ID / airport / transport-style rows are at most one and must be marked
  regression-only;
- behavior-change proof spans at least four unrelated authority families;
- the benchmark imports no live provider/search/orchestrator path and contains
  no source-specific authority domains in fixture records.

## Decision Packet For AG-94F

1. Did source obligation recognition fail generically?
   - Yes before AG-94E. Repaired for explicit legal/regulatory primary and
     official product status/release/changelog requests.
2. Did acquisition/query intent fail generically?
   - Partly unresolved. Recognition now opens the existing generic acquisition
     path. AG-94E did not prove or change provider/query depth, provider hints,
     or broad query templates.
3. Did the system treat secondary/news as satisfying stronger obligations?
   - Not after the repair in the benchmark. EvidenceLedger leaves lower-tier
     records unsatisfied for strong obligations.
4. Did official candidates fail to survive provider-result/candidate acquisition?
   - The fixture-backed diagnostic can classify this as a forwarding/drop layer.
     No generic runtime provider forwarding failure was proven from live data.
5. Did source fit reject official candidates generically?
   - Source fit correctly rejects wrong-kind authority candidates in the
     canonical-docs fixture.
6. Did readability/passport block official candidates?
   - Yes, and the benchmark classifies this separately from provider/query miss.
7. Did EvidenceLedger/final authority lose accepted official evidence?
   - The fixture can classify accepted candidate loss before final authority.
     No live custody regression was proven.
8. Did ordinary control cases over-require official sources?
   - No.
9. Is a generic repair justified now?
   - Yes, one bounded generic source-obligation recognition repair was
     implemented. Broader query/provider tuning is not justified in AG-94E.
10. What is the next smallest phase?
   - AG-94F should be a tiny rotating offline-plus-licensed-live validation or
     bounded repair phase focused on whether newly recognized legal/regulatory
     and product-status obligations acquire actual official/canonical sources,
     without repeating one corridor as the design target.

