# ScryRaven Current Truth

Status: Luna defaults and bounded model-driven discovery implemented and live observed
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

Ordinary CLI observations use the actual OpenAI Responses, Linkup standard discovery
and direct Fetch path through the unchanged doorman. The search-economy work item
used all six authorized PRODUCT invocations. Both FAST and SMART were observed as
`gpt-5.6-luna` / `medium` in every trace; no public override or fallback was needed.
Credentials and private environment contents were not inspected. Sanitized answers,
traces, status and selected evidence remain outside the repository in
`C:\tmp\scryraven-search-economy-luna-01`.

The final runtime revision is ef2cae17cc54a1ac7d0f00e300a2d0789cab0e5b. The canary
and Galloway observations below used e5b8a9570468f409c5ef94cff34957b8a5d8eeba with
the same search policy, prompts, counters and role defaults. The subsequent runtime
change only declares the existing nonempty finding-support requirement in the
structured response schema; those earlier valid findings meet that requirement.
Saturn and the airport transfer exercised the final schema. Canary/Galloway were
not repeated after that schema change; this is a limit on exact-revision coverage.
Subsequent delivery changes are documentation only.

- Canary: "What is the maximum allowed weight of a ten-pin bowling ball?"
  One search, two successful official USBC PDF reads, one Analyst pass, supported
  answer of 16.00 pounds scoped to USBC. The equipment manual supplied the value;
  the 2026 Open Championships rules supplied applicability context. An initial
  observation had used three searches and eight Fetch attempts after inventing
  international/recreational comparison obligations. General orientation/Analyst
  scope guidance was calibrated before the one-search observation.
- Galloway: "latest Scott Galloway controversy" used three searches under N1 across
  three Analyst passes, versus 17 in the baseline diagnostic pulse. Routes moved
  from recent reporting to a named photo dispute, then its primary social-record
  trail. Yield was 6, 4 and 4 new candidates, with 0, 2 and 2 duplicates. Five Fetch
  attempts acquired four sources: a HeapEvents Forbes headline record, PolitiFact,
  Poynter and Snopes; direct Forbes acquisition failed. The answer described the
  July McConnell-photo dispute while explicitly leaving Galloway's exact statement
  and whether this was his latest controversy unresolved. Terminal posture was
  partial/research_bound. Triage initially omitted the two photo fact-checks for
  lacking a substantive Galloway connection, then restored them as context. They
  did not independently establish his role. Poynter republishes the PolitiFact
  report, so those two bodies are not independent corroboration.
- Saturn: the exact question requesting reconciliation of 274, 285 and 293 as of
  September 2026 used three searches under N1, versus 13 in the baseline pulse.
  It acquired individual MPC circulars, broadened to synthesized chronology, then
  followed the specific S/2009 S 2 lead to official material. Each search returned
  six new candidates. Nine successful reads included NASA APOD's August 11 report
  of 293 confirmed moons as of June 2026, the IAU's March announcement of 285,
  five MPC circulars, Wikipedia and SpaceDaily. Analyst retained conflicting dates
  and definitions and gave a qualified 293 answer with the historical transitions.
  It did not establish an official aggregate explicitly dated September 7; the
  terminal posture was partial/research_bound. The first Saturn invocation stopped
  on finding_missing_support after one search and three reads. Declaring minItems=1
  for finding support in the existing schema repaired that output-contract defect;
  the repeat completed on the final runtime revision.
- Transfer: "What is the world's busiest airport in the latest full-year rankings,
  and does the answer change if 'busiest' means aircraft movements rather than
  total passengers?" Two searches and three successful reads supported both
  components. After low-value newsroom results, Research broadened to indexed
  ranking publications and read an ACI-attributed release on PR Newswire. Analyst
  recognized it as preliminary. A follow-up reused N1 and read already discovered
  July Time Out/Economy Middle East coverage without another search. The supported
  answer distinguished Atlanta for passengers from Chicago O'Hare for movements
  in the final 2025 rankings, explicitly disclosing the secondary-source basis.
  Author received only the two final-ranking sources, not the preliminary release.

Both challenging regressions used the exceptional third search with a visible
specific source/incident lead. The ordinary canary and transfer used one and two.
No live run attempted a fourth search; hard rejection and reads after rejection
are proven offline, while live follow-ups demonstrate reuse of spent N1 counts.
The sample does not establish that most future questions will use one or two
searches, or that semantic novelty/need identity will always be judged correctly.

Three independent source checks were used for review only. NASA APOD independently
confirmed its June-2026 293 statement, and Time Out contained the reported final
2025 leaders and figures. The reviewer tool could not open the HeapEvents URL;
that independent check was inconclusive. Acquired sanitized bodies were inspected
separately. No reviewer evidence entered the product corpus. OpenAI's official
model documentation was separately consulted for Responses/schema compatibility.

Earlier ordinary observations on 0cbdd73d9a5e0890503658bef3946d9713aa280c with the
previous defaults demonstrated three-component golf rules, Pluto facts plus its
IAU classification, and five-component Webb mission facts. They demonstrated
shared official evidence, Analyst-directed follow-up, earlier support continuity,
and relevant-source selection. They were not rerun as part of this work item.

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

- One useful discovery followed by a read, second-route yield feedback, an
  exceptional third search, and rejection of an unjustified third or any fourth.
- Reads and partial support after fuse rejection; a paraphrased gap retaining its
  allowance; a new Analyst gap receiving a new reference; returning to an exhausted
  earlier reference without resetting it. Revised component lists do not mint budgets.
- Failed discovery calls spending the fuse, invalid handoff references not silently
  allocating allowance, and empty finding-support lists using local schema correction.

Existing single-component, transport, citation, and doorman protections remain.
Tests were adapted to explicit Research orientation/relevance calls and component
coverage; the obsolete assumption that every successful acquisition reaches Analyst
was replaced. No prompt-wording or governance-wording tests were added.
Partial success at a bound, secondary-source fallback, component revision and
restoration of omitted acquisitions are demonstrated offline. The current live
sample includes supported and honestly partial answers, restoration of contextual
fact-checks, and preliminary versus final annual rankings. It includes an older
applicable definition and varied temporal needs, not a broad supersession benchmark.

## Provisional choices

- One OpenAI Responses transport, with configurable FAST and SMART roles. Defaults
  are gpt-5.6-luna/medium for both FAST (Research/Author) and SMART (Analyst).
  Roles remain independently configurable. There is no silent fallback.
- Small Pydantic values, sequential functions, one initial Research orientation,
  and Research relevance selection before each Analyst pass when acquisitions exist.
  Candidate aliases and compact attempts now survive the whole run. Research search
  actions state evidence target, novelty, expected value and acquirability; a third
  action additionally requires a concrete exceptional lead. Mechanics validate the
  case's presence; Research judges its merits. Returned/new/duplicate candidate
  counts inform that judgment without providing a quality score.
  Analyst reuses an existing need reference for a continuing or paraphrased gap,
  including previously searched subsets. A genuinely different uninvestigated need
  requires an explicit semantic explanation before mechanics assign a new reference.
  Changing text or the provisional component list alone cannot reset the counter.
  References/counts are run-local accounting, not a persistent component lifecycle.
  The local calendar date accompanies model material to avoid guessed currency.
- Three research passes and six navigation actions per pass are provisional local
  defaults, not per-component limits, acceptance thresholds, or work-item budgets.
  A fixed exceptional fuse permits at most three discovery calls per run-local
  semantic need reference, including failed provider calls. One or two is the normal
  expectation. Fetch/read does not spend that allowance; exhaustion is a limitation
  of the run, not evidence of nonexistence.
- The trace reports compact source expectations, current need, revised orientation,
  temporal expectations, configured model roles, queries and candidate-selection
  summaries, acquired/omitted/forwarded IDs, coverage, semantic gaps, Author selection,
  citation resolution, and terminal posture/reason. Discovery events also report
  need reference, attempt, hypothesis, candidate yield and remaining allowance;
  a blocked search reports discovery_fuse_reached and leaves useful reads available.
  It omits raw prompts, provider payloads, source bodies, credentials, and hidden
  reasoning. Optional --trace-evidence adds only the exact selected acquired bodies
  for completed-run review without extra source requests. Public questions and URLs
  may appear in diagnostics; observation files remain outside the repository.
- Malformed structured output gets one local correction with safe diagnostics;
  invalid candidate aliases get one Research correction using valid current aliases.
  Finding support lists require at least one reference in the response schema,
  so an empty list uses that same local structured-output correction path.
  Other invalid references or model/transport failures report safe stage/code errors.

## Limitations and retained boundaries

Source discovery, relevance, authority, coverage, and writing remain model judgments.
An official publisher can still return old or adjacent material, and relevant pages
can contain substantial boilerplate. Research triage reduces context but does not
compress source text: a large selected corpus or difficult primary document can
still exceed model context. Exact URL deduplication is mechanical; semantic duplicate
selection depends on Research. The sequential local bound can end with partial
support. Broad reliability, arbitrary question breadth, and difficult primary-source
acquisition are not established by a few observations. Novelty, new-gap identity
and useful source selection still depend on model judgment: an erroneous semantic
new-gap decision can allocate another allowance. There is no deterministic semantic
similarity check. The mechanical maximum is strict for each assigned reference.
Saturn still read nine sources, including a 311,689-character Wikipedia body; fewer
searches do not by themselves prove economical acquisition or minimal context.

Targeted large-document reading remains the next capability candidate and is
unimplemented. The earlier IPCC pulse acquired roughly 845k/893k characters before
Research relevance failed with model_rate_limited; it did not prove a context-window
overflow. That document path was not changed or rerun. Deterministic calculation
also remains unimplemented; the earlier unnecessary erroneous secondary NASA
radius calculation was not repaired in this phase.

Persistent sessions, resumability, parallel research, schedulers, UI, provider
routing/fallback, generalized recovery, and semantic compression remain unimplemented.
The old v1 machinery remains removed. No evidence ledger, final-answer packet,
source-quality subsystem, authority registry, or new semantic owner was introduced.

The retained scripts/run_brokered_command_once.py is operator-only credential custody
and process plumbing; product code does not import it. Agent-operated credentialed
commands use it, with sanitized outputs outside the repository. CI remains ordinary
pre-commit and offline pytest, without live calls or provider credentials. Work-item
PRODUCT-run and independent-review allowances are not runtime code or state.
