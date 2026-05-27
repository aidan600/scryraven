# L2B Legal/current Source-quality Diagnostic Contract

## Status

Architecture and diagnostic-contract design only. This phase does not implement
provider routing, provider selection, provider depth, provider escalation,
query-generation behavior, domain tuning, ranking, source classification,
evidence visibility, prompts, final-answer behavior, protected handoffs,
controller runtime authority, or source-specific legal APIs/resolvers.

Background research and planning artifacts informed the taxonomy, but repo
architecture and L2A control this contract. The L2A triage classifies AG-41
legal/current-primary failures as a source-quality side track rather than a
controller-loop regression.

## 1. Legal/current Source-quality Standard

Legal/current source quality is claim-sensitive. The required source class is
determined by what the answer would claim, not by generic source reputation.

For current legal rules, deadlines, compliance duties, eligibility,
applicability, agency requirements, stayed/enjoined status, or court status, a
confident answer needs visible and cited official/current/primary support. The
support may be an official agency page, official guidance or FAQ, a government
register notice, statutory or regulatory text, a court order/opinion/docket, a
regulator press release, or an official legal publication such as EUR-Lex,
GovInfo, eCFR, Federal Register, or legislation.gov.uk.

Official/current/primary sources differ from reputable news or commentary:

- Official/current/primary sources are issued by the legal authority, regulator,
  legislature, court, government publisher, or recognized official publication
  system responsible for the rule, action, docket, legal text, or status.
- Reputable news can establish that an event was reported and can explain public
  chronology, but it cannot by itself satisfy current legal-effect claims.
- Secondary legal analysis can explain interpretation, risk, and context, but it
  is not current law and must not displace an available official legal source.
- Academic or legal commentary can help interpret doctrine or compare views, but
  it should not satisfy current deadline, compliance, eligibility, or status
  obligations.

Good enough for ProPlex/FauxPlex means a general research assistant can provide
source-aware orientation without claiming to be a professional legal research
platform. It should prefer official/current/primary sources, cite them when
found, preserve date/status uncertainty, downgrade when only secondary support
is available, and avoid personalized legal advice or confident compliance
instructions without official/current support.

## 2. Good-enough Policy Without Specialized Legal APIs

ProPlex can answer normally when all of these are true:

- The question is not asking for personalized legal advice.
- The current provider stack returned a required official/current/primary source
  class for the central legal/current claim.
- The required source is visible in final evidence and cited for the legal claim.
- Date/status fields central to the claim are present or their absence is not
  material.
- Secondary sources, if used, are context rather than the legal authority.

ProPlex must caveat when:

- An official/current source is required but was not found in the available
  source set.
- Official sources are stale, archived, withdrawn, superseded, or ambiguous.
- The question has unresolved jurisdiction uncertainty.
- A proposed/final/effective/stayed/enjoined distinction is central but not
  resolved by official evidence.
- Reputable news establishes a reported legal/regulatory event, but official
  legal effect has not been confirmed.
- Secondary analysis is the best available support for a current-law claim.

ProPlex should downgrade, refuse, or mark the answer under-supported when:

- The user asks for personalized legal advice or direct compliance instructions.
- A deadline, eligibility, obligation, court status, injunction status, or
  current legal-effect claim lacks required official/current support.
- Court status is central but no docket, order, opinion, or reliable docket
  mirror is available.
- Only secondary commentary is available for a current legal requirement.

When official/current support is missing, the user-visible posture should be
bounded and factual, for example:

> I found reporting or analysis, but I did not find a current official source in
> the available source set. I can summarize what those sources say, but I would
> not treat this as a confirmed statement of the current legal requirement.

The diagnostic contract should distinguish "not found in this source set" from
"does not exist." Source-class failures should block confident claims about
current law, deadlines, compliance, eligibility, court status, agency
requirements, or current legal effect.

## 3. Question Taxonomy

| Question type | Meaning | Confident-answer rule |
| --- | --- | --- |
| Current legal rule / official requirement | The user asks what rule, duty, eligibility limit, deadline, or compliance requirement applies now. | Requires official/current legal or agency support. |
| Legal/regulatory current event | The user asks what happened in a legal/regulatory institution, agency, legislature, court, or enforcement setting. | News may support chronology; legal effect requires official/current support. |
| Court case / injunction / docket status | The user asks whether a case, order, injunction, stay, appeal, or docket status changes legal reality. | Requires court order/opinion/docket or reliable docket mirror. |
| Agency guidance or enforcement action | The user asks about agency guidance, FAQs, enforcement posture, press releases, consent orders, or rulemaking status. | Requires agency/regulator source or official register/docket where relevant. |
| Statutes / regulations / legal text | The user asks what a statute, regulation, rule text, legal instrument, or official publication says. | Requires statutory/regulatory/legal text or official legal publication. |
| Secondary legal analysis / news | The user asks for interpretation, commentary, comparison, news coverage, or legal analysis viewpoints. | Can use secondary sources for interpretation, not current-law authority. |

## 4. Required Source Classes by Question Type

| Question type | Required source classes | Context-only source classes |
| --- | --- | --- |
| Current legal rule / official requirement | Official agency page; official guidance/FAQ; government register; statutory/regulatory text; official legal text. | Reputable news; secondary legal analysis; academic/legal commentary. |
| Legal/regulatory current event | Regulator press release; agency page; government register; court order/opinion/docket where event affects status. | Reputable news for what happened; secondary legal analysis for context. |
| Court case / injunction / docket status | Court docket/order/opinion; official court page; reliable docket mirror such as RECAP/CourtListener where official access is limited. | Reputable news; legal blogs; academic commentary. |
| Agency guidance or enforcement action | Official guidance/FAQ; regulator press release; enforcement action page; consent order; Federal Register or equivalent notice/rule. | News and legal analysis for background. |
| Statutes / regulations / legal text | Statutory/regulatory text; government register; official legal publication; CELEX/ELI/OJ identifiers; eCFR/CFR/USC/GovInfo; legislation.gov.uk. | Treatises, explainers, legal commentary, academic analysis. |
| Secondary legal analysis / news | Reputable news; secondary legal analysis; academic/legal commentary. | Official sources are still required for embedded current-law claims. |

Source classes in this document are diagnostic obligations. They are not an
authorization to add new runtime source classifiers or source-specific adapters.

## 5. Currentness Fields

L2C diagnostics should record which of these fields were needed and which were
visible in sanitized evidence:

- Publication date: when the source or report was published.
- Effective date: when a rule or legal text takes effect.
- Application date: when an obligation starts applying to a class of actors.
- Amendment date: when the text or rule changed.
- Enforcement date: when enforcement starts, changes, pauses, or resumes.
- Compliance deadline: when a user-facing duty, filing, or milestone is due.
- Stayed/enjoined/suspended status: whether enforcement or effect is paused by
  a court, agency, statute, or other authority.
- Superseded/withdrawn/archived status: whether the source is no longer current
  authority.
- Stale-source warning: whether the source predates a likely relevant change or
  lacks an "as of" status for a current question.
- Jurisdiction uncertainty: whether the answer lacks enough jurisdictional scope
  to make a confident legal/current claim.

## 6. Bottleneck Taxonomy

L2C should classify source-quality failures using this stable taxonomy:

1. Source-class need not detected.
2. Recovery not triggered.
3. No official candidates returned.
4. Official candidates rejected or misclassified.
5. Accepted official sources not visible in final evidence.
6. Visible official sources not cited.
7. Source unavailable from current provider stack.
8. Query/domain strategy insufficient.
9. Source-specific official resolver/API likely needed.
10. Final answer posture too confident.

These bottlenecks are diagnostic labels. They should not directly mutate
retrieval behavior, ranking, evidence visibility, final-answer policy, or
controller authority in L2B.

## 7. Reference-case Mapping

| Case | Required source classes | Likely bottleneck class | Diagnostics needed | L2C could justify | L2D could justify | Do not infer yet |
| --- | --- | --- | --- | --- | --- | --- |
| CTA / FinCEN BOI current status | Current official agency/legal source; FinCEN/BOI page; agency notice; official court/order/regulatory source if applicability changed. | 3 and 8 from L2A; possible 7 or 9 only after repeated sanitized proof. | Was official-current required? Was recovery considered/eligible/used? Did FinCEN or official candidates return? Were they accepted, visible, and cited? Was the final posture caveated? | Current provider stack repeatedly returns no FinCEN/official candidates or loses them before final citation. | Bounded agency official-page/guidance resolver only if provider-stack acquisition repeatedly fails. | Do not infer that FinCEN requires a new API from one failure. Do not change prompts or provider routing. |
| OSHA heat illness prevention | Official OSHA guidance/rulemaking/status/enforcement source; Federal Register/eCFR/OSH Act/General Duty Clause material where relevant. | 1, 2, and 8 from L2A; possible 7 or 9 after bounded diagnostics. | Was official OSHA/legal source need detected? Did recovery trigger before caveated stop? Did OSHA, Federal Register, eCFR, Regulations.gov, or legal text candidates appear? Were they accepted and cited? | Current stack can or cannot acquire official OSHA/current/legal text under existing routing and depth. | Federal Register/eCFR or agency-page resolver only if provider-stack acquisition or official-source preservation repeatedly fails. | Do not infer that OSHA requires search-depth escalation or domain tuning in L2B. |
| EU AI Act dates and obligations | Official EU legal text; EUR-Lex/OJ/ELI/CELEX identifiers; Commission/AI Office implementation guidance for current-status questions. | 4 minor from L2A, plus possible 5 or 6/source dominance weakness. | Were EUR-Lex/OJ/CELEX/ELI sources classified as official/legal/current-primary? Did secondary sources displace official EU sources? Were official sources visible and cited for legal claims? | Official EU sources are found but misclassified or not dominant enough in final evidence/citation. | EUR-Lex/Cellar/CELEX resolver only if current stack cannot retrieve or preserve official EU legal text after diagnostics. | Do not infer secondary sources satisfy EU legal-current obligations when official EU text is present. |
| SSDI eligibility positive control | Official federal legal/regulatory sources such as eCFR, Federal Register, SSA official pages, or equivalent current regulatory text. | No material failure in L2A. | Did official federal legal/regulatory sources remain visible and cited? Which source-class signals satisfied the obligation? | Positive control confirms general providers can satisfy official/current source needs in some cases. | No adapter justification unless future L2C shows regression across repeated federal positive controls. | Do not overfit legal-current repair in a way that breaks ordinary official-source success. |

## 8. L2C Validation Plan Summary

L2C should use the current provider stack only. It should run a small bounded
reference set, collect sanitized diagnostics, and classify bottlenecks rather
than fix them.

L2C should validate:

- The question type and jurisdiction classification needed for each reference
  case.
- Required source classes and must-cite source classes.
- Recovery considered/eligible/used fields.
- Provider role, search depth, provider names, result counts, new URL counts,
  accepted URL counts, and recovered source-class counts from sanitized fields.
- Whether official candidates were absent, rejected/misclassified, accepted but
  not visible, visible but not cited, or cited successfully.
- Whether final answer posture matched source obligations and source failure.

L2C should not run without explicit live-validation approval and budget. It
should not change provider stack, search depth, routing, query/domain strategy,
source ranking, source classification, evidence visibility, prompts, final
answer behavior, or protected handoffs.

## 9. L2D Adapter/resolver Gates

Source-specific resolver/API work is justified only after L2B and L2C show a
repeated, material bottleneck that the current provider stack cannot diagnose or
handle safely.

L2D gates:

- The question type and source obligation are stable across fixtures and live
  validation.
- Sanitized provider diagnostics show no official candidates returned, repeated
  official-source acquisition failures, or identifier-resolution needs.
- The failure is central to final legal/current claims, not merely a nicer source
  preference.
- Existing source-class recovery, weak-corpus recovery, conflict-state, and
  terminal-stop behavior are preserved.
- The proposed resolver has a narrow consumer and a deletion/promotion rule.
- The resolver can operate without exposing secrets, raw prompts, raw provider
  payloads, DB rows, caches, full traces, or generated output packets.

Potential L2D choices should be one bounded prototype at a time. A resolver
should feed a targeted retrieval result or official-source candidate lane, not
become a new default provider or route.

## 10. Candidate Source/API Areas

These are candidate areas only. They are not implementation recommendations in
L2B.

- Federal Register, eCFR, GovInfo, and Congress.gov: candidate official US
  federal rule, regulatory text, statutory text, publication, and legislative
  status sources. They may help OSHA, SSDI-like regulatory text, and federal
  rulemaking cases if L2C proves general search cannot acquire or preserve the
  needed sources.
- CourtListener, RECAP, or court-opinion/docket mirrors: candidate public court
  opinion, order, docket, and docket-entry sources. They may help court
  injunction/status questions where official court pages or dockets are not
  easily acquired by the current stack.
- EUR-Lex and EU legal identifiers such as CELEX, ELI, and OJ: candidate EU
  legal text and identifier sources for EU AI Act and other EU legal-current
  questions. L2C should first separate acquisition from classification and final
  citation survival.
- legislation.gov.uk: candidate UK statutory/instrument text and changes/effects
  source for future UK legal-current coverage.
- Regulator/agency press rooms and guidance pages: candidate source families for
  agency actions, guidance, enforcement, FAQs, and status pages such as FinCEN,
  OSHA, FTC, FDA, SEC, CFPB, or EU Commission/AI Office pages.
- Reputable news/current-event APIs or search sources: candidate event-context
  sources. They may support "what happened" answers, but not legal-effect
  claims without official/current support.

Commercial legal databases, PACER purchasing flows, broad state/local coverage,
and universal legal resolvers are outside the general-assistant L2B scope.

## 11. Non-recommendations

Do not build or change any of the following in L2B:

- New Federal Register, eCFR, GovInfo, Congress.gov, EUR-Lex, CourtListener,
  RECAP, PACER, legislation.gov.uk, news, or agency API adapters.
- A universal legal source framework, professional legal research workflow, or
  commercial legal database integration.
- Provider routing, provider selection, provider depth, provider escalation, or
  domain-list tuning.
- Query-generation behavior, source ranking, source dominance, source
  classification runtime behavior, evidence visibility, final citation behavior,
  prompts, or final-answer posture.
- Controller action execution, runtime scheduling, targeted retrieval runtime
  authority, weak-corpus recovery behavior, source-class recovery runtime
  behavior, or conflict-state behavior.
- Analyst, Economist, Author, or Scrutineer handoff behavior.
- Raw telemetry/prompt/provider-payload exposure, raw logs, caches, DB rows,
  secrets, or generated output packets.
- Live validation or output-quality packet creation without explicit approval.

The L2B outcome should be a durable diagnostic contract and validation design
that lets later phases prove where legal/current source-quality failures occur.
