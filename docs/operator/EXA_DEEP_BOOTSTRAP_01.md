# Exa Deep Bootstrap 01

Disposition: **PROMOTE for review; bounded mixed efficiency evidence.**

The authorized question was whether one managed discovery burst near the start
of a fresh research turn could avoid later Search/Research work while preserving
ScryRaven's evidence and Answer boundaries. Four ordinary product runs met the
promotion gate: Passport collapsed a dependent discovery trajectory, and MD-80
materially reduced generic Search. BIPM stayed correct and bounded. This does not
establish a general speedup, lower context cost or greater reliability.

## Candidate and authority

The approved first version is unchanged: on `session_turn == 1` with no retained
acquisitions entering the turn, the first executed generic Exa Search is Deep;
later generic Searches are Auto. Other turns remain Auto. Only generic Search
execution consumes the bootstrap. Existing Serper, LinkUp static Read, local
Read/Find and Answer retain their roles. Direct transport callers default to Auto.

The implementation adds a bounded `search_type` transport argument, one private
run-local closure and sanitized provider-mode timing metadata. Request,
ResearchDecision, AnswerDecision, AcquisitionLibrary, model settings, prompts,
ordinary budgets, sessions and citation semantics are unchanged. No semantic
router, critic, planner, depth classifier, feature flag or persistent bootstrap
state was added. No explicit removal was required.

Current official documentation describes Deep's iterative retrieval and separates
selected results from synthesis. The Highlights guide represents Highlights as
extractive source passages. Only exact source-bound Highlights enter the existing
custody path; separation markers and the size guard remain. Generated answers,
summaries, output/grounding, confidence and provider reasoning are excluded.
Auto's internal routing is not inferred from vendor descriptions or the deprecated
`resolvedSearchType` field. Sources:
[Search](https://exa.ai/docs/reference/search),
[Deep](https://exa.ai/docs/search/deep-search),
[Highlights](https://exa.ai/docs/search/highlights).

## Frozen execution and wave

Baseline: PR #666, `f3f4cf565a06934ec51e71bfa104583ba91f75fb`.
Live-tested candidate: `0da7f2843eebf7c2be8052e04ec32f5e9c20a59f`.
Runs W1-A through W1-D occurred October 1, 2026, Pacific time. Each used fresh
ordinary `ResearchSession.ask`, the existing credential broker and effective
Luna / high / Fast Research with GPT-6.1 Sol / high / Standard Answer. User
settings were not edited. The controller did not read credentials or `.env`.

Questions, comparators, source/config hashes, current public documentation and
scoring were frozen before calls in ignored
`local-evals/runs/exa-deep-bootstrap-01/`. The corpus is outside the isolated
worktree and survives its cleanup. No fresh Auto baseline or prior provider
experiment was rerun.

Only Wave 1 ran. No candidate repair was needed or earned: the initial objectives
already expressed the broad evidence needs, and no custody, timeout, redundant
first-route or mechanical-delivery defect was observed. Further Research
retention/Find behavior in MD-80 is outside the licensed bootstrap refinements.
No prompt tuning or further live call occurred.

## Case ledger

R/A are semantic model calls. Physical submissions include calculator
continuations. Generic total is Deep plus Auto. Reads are external/local.
Durations are seconds. First consequential availability is source material, not
necessarily an answer or a comparable scalar.

| Case | Quality | R/A | Physical | Deep/Auto | Lexical | Reads E/L | Find | External | Wall | Deep |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BIPM | Correct supported lookup | 2/1 | 3 | 1/0 | 0 | 0/0 | 0 | 1 | 23.282 | 4.328 |
| Passport | Correct supported relationship and range | 2/1 | 3 | 1/0 | 0 | 0/0 | 0 | 1 | 21.640 | 6.828 |
| Dorothy | Supported appointment and qualified background | 9/1 | 10 | 1/2 | 3 | 7/0 | 0 | 13 | 123.875 | 7.844 |
| MD-80 | Honest partial; no matched subtraction | 11/1 | 13 | 1/3 | 1 | 3/2 | 5 | 8 | 161.938 | 12.515 |

| Case | First decision proxy | Deep available / next Research start | Consequential material | Research s | Answer s | Acquisition s |
|---|---:|---:|---|---:|---:|---:|
| BIPM | 2.844 | 7.188 / 7.188 | Complete BIPM lookup at 7.188 | 6.469 | 12.422 | 4.328 |
| Passport | 3.578 | 10.406 / 10.406 | Relationship and GE range at 10.406 | 6.500 | 8.265 | 6.828 |
| Dorothy | 2.234 | 10.078 / 10.078 | Role context at 10.078; appointee qualifications 54.187; appointment 66.453 | 44.032 | 52.766 | 27.015 |
| MD-80 | 2.485 | 15.000 / 15.000 | Qualified MD-80 model and 777 study leads at 15.000; no matched scalar | 82.048 | 46.938 | 32.859 |

The first-decision proxy is model-return time. Existing events do not timestamp
the subsequent validation separately; first acquisition start provides its later
bound. This precision limit is preserved in the summaries.

| Case/role | Input | Cached | Cache write | Ordinary uncached | Output | Reasoning |
|---|---:|---:|---:|---:|---:|---:|
| BIPM R | 7,254 | 1,936 | 1,936 | 3,382 | 414 | 79 |
| BIPM A | 2,382 | 0 | 1,594 | 788 | 637 | 338 |
| Passport R | 7,141 | 3,805 | 55 | 3,281 | 623 | 295 |
| Passport A | 2,730 | 1,594 | 0 | 1,136 | 462 | 323 |
| Dorothy R | 138,421 | 17,347 | 59 | 121,015 | 6,011 | 2,926 |
| Dorothy A | 6,425 | 1,594 | 0 | 4,831 | 2,835 | 1,552 |
| MD-80 R | 321,362 | 21,195 | 57 | 300,110 | 12,748 | 8,617 |
| MD-80 A | 53,986 | 3,188 | 0 | 50,798 | 2,465 | 1,550 |

MD-80's Answer counters aggregate two physical requests in one semantic attempt,
including a successful calculator continuation. Reasoning is part of output and
is not charged twice. Physical receipts and requested/returned tiers are retained.

## Actual frontier and use

**BIPM:** The first batch included BIPM's December 2022 announcement and SI
resolution/prefix material. Research selected the announcement and Answer returned
ronna/R/10^27, quetta/Q/10^30, ronto/r/10^-27 and quecto/q/10^-30. No consequential
requested fact was omitted, and no unsupported material claim was observed.

**Passport:** First Deep returned NASA's `hybrid-engine-tested` publication and
GE's `Passport-engine-datasheet-2021.pdf` together. Their actual Highlights
established the modified Passport relationship and 17,325–18,920 lb takeoff
range. Research recognized and selected them on its next call. A CT7 result was
not substituted for the controlling HyTEC relationship. No later Search or Read
was necessary. No consequential requested fact was omitted.

**Dorothy:** Deep returned Ashley Boaeuf's older profile, the organization's
about page, the open job page and 2026 search profile; it returned four selected
results despite a six-result request. Research explicitly recognized that these
did not establish the 2026 selection. The appointee's LinkedIn and New England
Conference material came through later Auto. Serper and LinkUp ultimately exposed
the official Instagram post identifying John Michael Spelman as incoming director.
Answer preserved camp leadership, accreditation, denominational/DEI experience and
the incomplete status of educational listings. It did not treat old Ashley data
as the appointment. No Deep appointee/appointment-frontier benefit is credited.

**MD-80:** Deep exposed the airline-cost study, a fleet-replacement analysis
giving modeled MD-80 CASM, Aircraft Commerce 777 guide/fuel material, a broad
EUROCONTROL/IATA B777 table and PlanePHD navigation. These were actual cost,
metric and variant opportunities, not merely overlapping URLs. Research
recognized the modeled MD-80 value and its incompatibility, read the sources,
then pursued official data and repeated local study inspection. Later Auto
also supplied the secondary 2013 MD-80 CASM table; it was not in the Deep batch.
The final selected packet contained only study views. Answer correctly explained
seat versus passenger denominators, combined 777 variants, unmatched scope and
missing occupancy, and calculated 8.0 cents/seat-km as 12.87 cents/seat-mile. It
did not subtract incompatible numbers. However, acquired MD-80 model/2013 cost
leads were shelved and omitted from the final Answer. This is a coverage/retention
limit; the bootstrap did not solve it. No material unsupported claim or repeated
attributable quality regression was observed.

Exact source identities, Highlight arrays, selected Evidence, final answers,
ordered public queries/types, role usage, timings, calculator receipts and
adjudication remain in the ignored bundle. Every admitted Highlight acquisition
was checked against its exact per-source provider strings and separator.

## Exact historical comparisons

All four primary comparators are the matching `q1`–`q4` ordinary observations
under `local-evals/runs/exa-evidence-objective-search-01/`, live-tested at
`d14ada1b8d4209337809562fbf134ab2e29710d5`. Their precise UTC dates, artifact
locators, hashes and original metrics are frozen in `historical-comparators.json`.
They used the same effective models, objective formulation, six-result
Dynamic/high request and Highlight custody, with Auto throughout. Runtime
revisions, index/time, stochastic retrieval and routes, caches and provider
responses differ. These are descriptive mechanism observations, not causal
estimates or a synthetic pooled baseline.

| Case | Prior R -> candidate R | Prior generic -> candidate generic | Prior external -> candidate external | Prior wall -> candidate wall |
|---|---:|---:|---:|---:|
| BIPM | 2 -> 2 | 1 -> 1 | 1 -> 1 | 27.344 -> 23.282 |
| Passport | 4 -> 2 | 2 -> 1 | 5 -> 1 | 65.531 -> 21.640 |
| Dorothy | 9 -> 9 | 7 -> 3 | 15 -> 13 | 181.891 -> 123.875 |
| MD-80 | 11 -> 11 | 10 -> 4 | 12 -> 8 | 204.656 interrupted -> 161.938 completed |

BIPM's first acquisition tax was 4.328 - 1.297 = **3.031 seconds**, with no
continued-research pathology. Whole-run differences also include model timing.

Passport's prior GE range arrived after a dependent second Search at 8.625
seconds; candidate received relationship and range together at 10.406 seconds.
It was not earlier in wall time. The benefit is eliminating that dependent
discovery and three later Reads, with two fewer Research calls.

Dorothy's historical qualifications appeared at 62.047 seconds but its failed
Reads did not establish appointment. Candidate qualifications arrived at 54.187
and appointment at 66.453. This later ordinary-route improvement earns no
first-Deep appointment credit, despite fewer generic Searches.

MD-80's historical study was already available in the first route at 6.250
seconds, and its secondary MD-80 cost table appeared at 49.625. Candidate Deep
provided a different, explicitly modeled MD-80 cost lead and the study together
at 15.000; it did not reproduce the complete historical empirical frontier.
Four rather than ten generic Searches is meaningful Search-trajectory savings,
but Research stayed eleven calls and input rose from 257,021 to 321,362 tokens
(about 25%). Its five Finds consumed the remaining trajectory. The historical
ordinary Answer was interrupted by its reservation wrapper; the separately
authorized frozen-packet recovery is a quality reference only and is not pooled
into an ordinary run or a comparable whole-run timing/cost.

## Adjudication and economics

Wave 1 classification: **MIXED BUT PLAUSIBLE**, with a clear Passport collapse
and meaningful MD-80 generic-Search reduction, yet no demonstrated general
Research-call/context-cost win. The promotion gate is **met** under its explicit
one-or-more benefit definition for Passport and MD-80. Dorothy is not needed to
meet it. BIPM remains correct/bounded; custody is unchanged; no repeated material
quality regression attributable to bootstrap or new semantic actor is established.
The avoided Passport trajectory and MD-80 Search reduction justify bounded review
of the observed first-Deep tax, not a universal economic guarantee.

| Case | Model usage estimate $ | Exa reported estimate $ | Provider envelope $ | Total consumed envelope $ |
|---|---:|---:|---:|---:|
| BIPM | 0.013544 | 0.012 | 0.012 | 0.038878 |
| Passport | 0.008420 | 0.012 | 0.012 | 0.037298 |
| Dorothy | 0.068747 | 0.026 | 0.111 | 0.240441 |
| MD-80 | 0.199773 | 0.033 | 0.068 | 0.480319 |

Four runs used 29 physical model submissions and 23 external attempts. Model
usage plus reported Exa estimates totaled approximately $0.3735; adding the
conservative lexical/static-Fetch allowances yields approximately $0.4935.
The more conservative consumed campaign envelope was $0.796936, below $6.
These are estimates/allowances, not account billing receipts. The wrapper
settled each physical submission once, held no pending semantic output reserves,
and did not block the MD-80 calculator continuation. Campaign-only ceilings are
absent from runtime code. Pricing snapshots:
[Exa](https://exa.ai/docs/admin/pricing),
[OpenAI](https://developers.openai.com/api/docs/pricing).

Current Exa pricing lists Deep at $0.012 and 4–15 seconds, Auto at $0.007 for
up to ten results. Vendor benchmark claims are not product evidence. There is
no account-usage query or production cost estimator.

## Verification, preservation and limits

Focused transport/bootstrap/latency/novelty tests and full pytest passed; full
suite: 738 passed. Ruff and `git diff --check` passed. Offline checks exercise
default Auto compatibility, one Deep then Auto across routes, retained/follow-up
negative controls, other-route behavior, no generic Search, failure consumption,
independent runs, exact Highlight custody, generated-output exclusion and safe
mode telemetry. AST hashes confirm the three contracts unchanged. A no-network
campaign check completed two calculator continuations without pending reserves.

The initial test-launcher attempts had Windows execution-identity/temp-directory
conflicts. The verified full run used approved execution with a fresh accepted
`C:\tmp` test base and no shared cache; no unrelated product repair was made.

Only documentation was added after the live-tested runtime checkpoint; no
subsequent runtime or prompt change lacks product observation. CURRENT.md and
the architecture record describe the behavior that would be true after merge.
The dirty primary checkout, prior reports, prior experiments and the frozen
October 1 retrospective were preserved. Useful sanitized candidates are kept
under ignored `local-evals/candidates/` with development status and exact hashes.
No exact evidence was deleted.

Limits: four reused public development questions, one draw each, live-index drift,
stochastic retrieval/selection, tiny corpus, historical timing/confounding and
MD-80's interrupted historical Answer. No universal stopping, economic or
reliability claim is made. No follow-up/new-problem classifier was tested or added.

[Linkup pricing](https://www.linkup.so/pricing) advertises a distinct Research
capability. It remains a plausible separately authorized managed-discovery
comparator; no call or integration occurred. This candidate earned review without
a provider substitution. No sibling experiment or next phase is started.

Publication authority applies only because the bounded promotion gate was met.
One PR is authorized; merge and main changes are not. Branch:
`codex/exa-deep-bootstrap-01`. The PR and Git history identify the final head;
the live-tested runtime revision above remains the evidence reference.
