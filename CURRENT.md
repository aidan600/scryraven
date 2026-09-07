# ScryRaven Current Truth

Status: multi-component authoritative research implemented and live demonstrated
Repository: aidan600/scryraven
Preferred local checkout: C:\Users\aidan\ScryRaven

## Implemented

PRODUCT.md remains the approved product charter; the multi-component research work
item authorizes extending its first slice to questions with several answer needs.
The ordinary entrypoint remains `python -m scryraven "<public-web question>"`.
The semantic responsibilities remain Research -> Analyst -> Author, followed by
mechanical citation resolution. No separate planner or source-quality owner exists.

Before its first search, Research makes a compact orientation: answer needs,
likely authoritative publishers/source types, the material sought, temporal
requirements, and an initial focus. This is a revisable run-local hypothesis, with
no fixed component count, persistence, component IDs, graph, scheduling, or lifecycle.
The original question
remains authoritative. Research chooses Linkup standard searches with source
ownership in mind and reevaluates discovery candidates for relevance, directness,
actual publisher, currency, accessibility, and duplication. Authority is contextual;
secondary material is useful when it explains, corroborates, guides discovery,
synthesizes, or is the best obtainable evidence. There is no domain list, ranking
formula, deterministic source admission rule, or provider routing.

Temporal orientation distinguishes applicable rules/versions/periods from recent
publication. Research infers the question's time target and what establishes fit,
then reevaluates candidate edition, governing status, effective period, supersession,
or event timing. An older source may remain applicable; a newer page may be only
commentary. Analyst judges applicability from acquired material and can return a
semantic temporal gap. There is no fixed freshness window, age penalty, date ranker,
or requirement that every source carry an explicit date.

Only successful direct Linkup Fetch calls create immutable evidence snapshots with
stable run-local IDs, URLs, titles, and readable text. Duplicate candidate aliases
and exact previously acquired URLs do not create another snapshot. All successful
acquisitions remain in memory. Research examines newly acquired text and selects
relevant IDs for Analyst; omitted source identities remain available for restoration
without another Fetch. Later Research calls receive source metadata, not every
previous body. Relevance selection does not establish claim support.

Analyst receives the original question, provisional answer needs, its previous
assessment, and deliberately selected acquired text. Prior Analyst support and
active conflict/context evidence are retained for reassessment during follow-up.
Analyst may correct Research's interpretation, merge or add answer needs, and
returns coverage with supported/qualified/unresolved portions, supported findings
and evidence references, and limitations. It selects one semantic next_need when
further research is useful; Research authors the actual search/read action.
An overall supported decision cannot coexist with an explicitly unresolved portion.
References must resolve to the evidence actually submitted to Analyst.

Author receives coverage findings, qualifications/limitations, and only the acquired
sources supporting those findings. It must retain claim conditions and avoid
incidental claims from the larger source body. Mechanical code validates and renders
citations to selected acquired sources; it does not decide whether passages prove
claims. A completed run is supported, partial, or unable. Partial results preserve
supported portions and identify what this run did not establish, including at the
local execution bound. All three completed postures exit 0; execution errors exit 1.
Discovery snippets/context never become Analyst or Author evidence.

## Live demonstrated

The following ordinary CLI observations completed with real OpenAI model calls,
Linkup standard discovery, and direct Fetch through the doorman on runtime revision
0cbdd73d9a5e0890503658bef3946d9713aa280c. The trace confirmed FAST gpt-5.4-mini/medium
and SMART gpt-5.4/medium. Every final citation resolved to directly acquired,
Analyst-selected support. Subsequent delivery changes are documentation only.

- Golf: "Under the official Rules of Golf, how many clubs may a player carry,
  what is the penalty in stroke play for carrying more than the allowed number,
  and when may a damaged club be replaced during a round?" Research recognized
  three needs, sought R&A/USGA governing text, and treated the current applicable
  rule as the temporal target. One search led to current R&A Rule 4 (C5 -> E1)
  and a 2026 R&A local-rule article (C2 -> E2). Research omitted the newer article
  as unnecessary ancillary context. Analyst supported all three needs from E1;
  only E1 reached Author. The answer gave the club limit, stroke-play penalty
  and cap, and damaged-club replacement conditions, with citations beside each
  portion and the conditional take-out-of-play procedure preserved. No follow-up
  was needed. Acquired source identities:
  E1: https://www.randa.org/rog/the-rules-of-golf/rule-4
  E2: https://www.randa.org/en/articles/new-and-updated-model-local-rules-for-2026
- Pluto: "According to authoritative sources, what is Pluto's orbital period,
  what is its average distance from the Sun, and which IAU criterion prevents
  Pluto from being classified as a planet?" Research grouped the two orbital
  facts together and separated the IAU definition need. It expected maintained
  NASA/JPL data and the still-applicable IAU 2006 resolution. It revised poor
  secondary discovery before reading authoritative sources. The first NASA Fetch
  returned a maintenance page (E1), which Research omitted. Analyst supported the
  IAU component (E2) and requested only the missing orbital facts. Research then
  acquired NASA Science (E3); the next Analyst pass retained E2 and combined E2/E3
  into full support. Author cited NASA for 248 years and approximately 5.9 billion
  km/39 AU, and IAU for the uncleared-orbit criterion. This demonstrates natural
  Analyst-directed follow-up, earlier support continuity, unusable successful-Fetch
  triage, and retaining an applicable 2006 primary source rather than requiring
  recent publication. Acquired source identities:
  E1: https://nssdc.gsfc.nasa.gov/planetary/factsheet/plutofact.html
  E2: https://www.iau.org/IAU/Iau/News/PR2006/iau-2006-general-assembly-resolution-votes.aspx
  E3: https://science.nasa.gov/dwarf-planets/pluto/facts/
- Five-component transfer: "For the James Webb Space Telescope, which space agencies
  are partners, when was it launched, where does it operate, what is its primary
  mirror diameter, and which wavelength region was it designed to observe?"
  Research recognized five needs, distinguishing a historical launch event,
  current mission operation/partnership, and fixed design specifications. It
  acquired NASA's fact sheet (E1) and mirror-resource page (E2), supporting four
  components. Analyst requested only the missing partner agencies; Research acquired
  NASA's mission overview (E3). The combined analysis supported all five. Author
  cited E3 for the partners, E1 for launch/mirror/wavelength facts, and E1/E2/E3 for
  the operating location. All three sources reached Author; some corroborating
  overlap remains. The selected acquired passages visibly support each component.
  E1: https://science.nasa.gov/mission/webb/fact-sheet/
  E2: https://science.nasa.gov/3d-resources/james-webb-space-telescope-mirror/
  E3: https://science.nasa.gov/mission/webb/about-overview/

The selected acquired passages were inspected from sanitized --trace-evidence
output outside the repository, without additional product source requests. R&A
Rule 4 and the IAU resolution were also independently opened for source/support
review; an independent USGA Rule 4 request returned HTTP 403. No external reviewer
material was inserted into the product corpus. Final golf/Pluto answers used only
the responsible authorities; the transfer answer used NASA mission material.
The work item used six of ten authorized PRODUCT invocations, including three
earlier golf observations used for diagnosis/repair. Three of four authorized
independent research-source checks were used; OpenAI's official model documentation
was separately consulted for API compatibility. These observations do not establish
broad reliability. No further PRODUCT runs are planned in this work item.

## Offline demonstrated

The real application with injected external calls covers:

- Three components supported by one source without a search per component, or by
  different sources combined into one answer; official/direct candidate selection
  is a scripted model judgment rather than proof of live source-quality behavior.
- A missing component returning through Analyst -> Research, with prior support
  preserved, duplicate URLs skipped, and a combined later analysis.
- Partial success at a research bound, with two cited supported portions and an
  explicit unresolved replacement condition reaching Author.
- Unavailable primary material followed by useful secondary evidence; Analyst
  correcting a bad component hypothesis; restoration of an omitted acquisition
  without another Fetch.
- Successful but irrelevant acquisitions retained in the run and omitted from
  Analyst/Author; Author receiving only supporting evidence rather than all active
  Analyst context; discovery remaining separate from evidence.
- Invalid candidate selection and local correction, malformed structured output,
  invalid/withheld evidence references, inconsistent overall support, unavailable
  sources, execution bounds, model failures, and citation grammar/identity checks.
- CLI use of the actual application and real Linkup adapters with only external
  calls injected, plus retained Linkup transport and operator doorman tests.
- Current but not recent governing material versus fresh commentary and superseded
  official material; a named historical period; and a latest-event question where
  recency matters. These scenarios exercise handoffs with scripted model judgments.

Existing single-component, transport, citation, and doorman protections remain.
Tests were adapted to explicit Research orientation/relevance calls and component
coverage; the obsolete assumption that every successful acquisition reaches Analyst
was replaced. No prompt-wording or governance-wording tests were added.
Partial success at a bound, secondary-source fallback, component revision and
restoration of omitted acquisitions are demonstrated offline; the three final live
observations all ended fully supported. Live temporal coverage includes an older
applicable definition and varied temporal needs, not a broad supersession benchmark.

## Provisional choices

- One OpenAI Responses transport, with configurable FAST and SMART roles. Defaults
  are gpt-5.4-mini for Research/Author and gpt-5.4 for Analyst, both at medium reasoning.
  The FAST default replaced gpt-4.1-mini after live source-selection and writing failures.
- Small Pydantic values, sequential functions, one initial Research orientation,
  and Research relevance selection before each Analyst pass when acquisitions exist.
  The local calendar date accompanies model material to avoid guessed currency.
- Three research passes and six navigation actions per pass are provisional local
  defaults, not per-component limits, acceptance thresholds, or work-item budgets.
- The trace reports compact source expectations, current need, revised orientation,
  temporal expectations, configured model roles, queries and candidate-selection
  summaries, acquired/omitted/forwarded IDs, coverage, semantic gaps, Author selection,
  citation resolution, and terminal posture/reason.
  It omits raw prompts, provider payloads, source bodies, credentials, and hidden
  reasoning. Optional --trace-evidence adds only the exact selected acquired bodies
  for completed-run review without extra source requests. Public questions and URLs
  may appear in diagnostics; observation files remain outside the repository.
- Malformed structured output gets one local correction with safe diagnostics;
  invalid candidate aliases get one Research correction using valid current aliases.
  Other invalid references or model/transport failures report safe stage/code errors.

## Limitations and retained boundaries

Source discovery, relevance, authority, coverage, and writing remain model judgments.
An official publisher can still return old or adjacent material, and relevant pages
can contain substantial boilerplate. Research triage reduces context but does not
compress source text: a large selected corpus or difficult primary document can
still exceed model context. Exact URL deduplication is mechanical; semantic duplicate
selection depends on Research. The sequential local bound can end with partial
support. Broad reliability, arbitrary question breadth, and difficult primary-source
acquisition are not established by a few observations.

Persistent sessions, resumability, parallel research, schedulers, UI, provider
routing/fallback, generalized recovery, and semantic compression remain unimplemented.
The old v1 machinery remains removed. No evidence ledger, final-answer packet,
source-quality subsystem, authority registry, or new semantic owner was introduced.

The retained scripts/run_brokered_command_once.py is operator-only credential custody
and process plumbing; product code does not import it. Agent-operated credentialed
commands use it, with sanitized outputs outside the repository. CI remains ordinary
pre-commit and offline pytest, without live calls or provider credentials. Work-item
PRODUCT-run and independent-review allowances are not runtime code or state.
