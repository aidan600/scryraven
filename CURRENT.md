# ScryRaven Current Truth

## Ordinary product architecture

The ordinary product supersedes Research -> Analyst -> Author with the
accepted clean-room Research semantic loop -> mechanical Search / lexical Search /
Read / Find ->
Research reassessment -> fresh Evidence-first Answer. `scryraven.research.run`,
`ResearchSession.ask`, the CLI and Reading Room share this single path. There is
no architecture selector, Analyst checkpoint, old Author handoff or fallback.

Research owns interpretation, compact revisable understanding, consequential
needs, acquisition direction, attention and stopping. Generated state is never
Evidence. Answer independently assesses selected actual source material and
explicit user-supplied premises against the current/original request. Research
may select no Evidence when the requested operation needs no external fact.
Answer may invoke a bounded deterministic local arithmetic calculator, including
dependent calculations, while the same Answer role remains the sole semantic
owner. Calculator results are derived computation, not Evidence or citation
aliases. Externally factual numeric inputs retain the ordinary selected-Evidence
and citation requirements; explicit user premises retain their conditional basis.
The calculator and its Responses continuation are verified offline and exercised
by live Answer calls over frozen Evidence. This does not establish end-to-end
research reliability or general calculator-use reliability.

Ordinary non-lookup analytical answers now default to developed treatment: they
orient the reader to the conclusion early, then substantially explain important
supported relationships, representative evidence, calculations and consequential
qualifications. Development is substantial but non-exhaustive, with a soft
roughly two-page editorial ceiling rather than a length rule or fixed outline.
Simple lookups remain direct and compact. Quantitative answers explain how inputs
determine the result; comparisons retain what each supplied quantity represents,
including observed versus modeled status. Partial answers explain which gaps a
missing input would resolve and which incompatibilities would remain. Reading
selection supports the complete synthesis. No coverage schema or additional actor
is introduced. The default promotes a preference that yielded two developed
answers in a frozen direct-Answer probe. Exa Evidence-Objective Search 01 later
exercised it in three completed ordinary answers and one separately recovered
frozen-packet Answer; this bounded evidence does not establish general reliability.

Ordinary runtime selects semantic Research and Answer roles through
`ModelConfig.research` and `ModelConfig.answer`. Tracked package-owned shipped
defaults in `scryraven/model_roles.defaults.json` are GPT-6 Luna / high / Fast for
Research and GPT-6.1 Sol / medium / Fast for Answer. An optional complete per-user
`model_roles.json` outside the checkout controls active ordinary model IDs,
reasoning and service tiers. The precedence is explicit injected `ModelConfig`,
then the user file, then shipped defaults. Windows uses
`%LOCALAPPDATA%\ScryRaven\model_roles.json`, falling back to
`~/AppData/Local/ScryRaven/model_roles.json` for an absent, empty or relative root.
macOS uses `~/Library/Application Support/ScryRaven/model_roles.json`; Unix uses
`$XDG_CONFIG_HOME/scryraven/model_roles.json` with `~/.config/scryraven/model_roles.json`
as the absent, empty or relative-root fallback.

`built_in_model_config()` reads shipped defaults; `default_model_config()`,
`ModelConfig()` and `OpenAIModel()` resolve one coherent effective snapshot with
strict validation. A present invalid user file fails locally without fallback
or provider I/O. The loader creates no settings file. Full explicit injection
bypasses both files; partial injection resolves the missing role from effective
ordinary settings. CLI, Reading Room, sessions and direct `run()` construct a
fresh ordinary model per turn. Editing the user file affects the next turn in
the same process without any source edit, commit or PR; an explicitly retained
model keeps its resolved snapshot. The external file is the current user/operator
settings boundary, with no settings UI, write API or watcher.

Offline mocked transport checks cover those ordinary surfaces and between-turn
amendments, actual resolved-model telemetry and model/effort-sensitive cache
identity. The unchanged shipped Research role retains its baseline cache family;
the shipped Answer model change produces a distinct family. This cleanup used
zero live calls and establishes no GPT-6.1 Sol quality or latency result.
These are reversible configuration values, not architectural requirements or a
semantic router. Compatible injected configurations may vary in quality and
validation coverage; there is no automatic premium escalation or model fallback.
Exa supplies ordinary general
Search. Research can explicitly select Serper lexical/community/current
discovery for a needed source class. Serper
candidates and snippets guide navigation only;
they are not Evidence. LinkUp static Fetch supplies external known-URL Read when
Research selects one. Exa Contents has no ordinary Read authority; there is no
search or Read fallback or provider router. Limits remain 12 semantic attempts,
16 external attempts and 128,000 characters of current attention. The ordinary
hard run ceiling is 300 seconds, with 180 seconds reserved for terminal Answer
once Evidence exists. Each underlying model request remains capped at 120
seconds, and one unchanged Answer Evidence packet has a 120-second total
Answer-stage allowance.
Calculator tool stops and their model continuations consume no additional semantic
attempts or Answer validation corrections. They remain subject to the whole-run,
Answer-stage and per-request time bounds.
These limits provide diagnostic and completion headroom, not an acceptable-latency
target. No semantic
verifier or additional semantic owner exists.

Research packet presentation now keeps the stable `conversation_context`,
`current_date`, `phase`, `question` prefix and its Research-context cache
breakpoint. Present volatile fields follow the deliberate order
`working_understanding`, `catalog`, `last_route`, `failed_external_reads`, `evidence`,
`answer_missing_information`, `pending_delivery`, `budget`, then
`output_correction` last. Unknown fields remain lossless in deterministic order.
Generated understanding and navigation precede the latest route and exact
Evidence, placing current source material near the decision edge. Both Research
and Answer serialize identifying metadata before each Evidence item's unchanged
exact content. Evidence membership, array order, logical fields and body bytes
are unchanged; Answer's top-level packet order remains unchanged. This layout
promotion has no demonstrated quality or latency effect. `ResearchDecision`
no longer contains `purpose`: executable route intent remains in structured
requests and compact working state. This adds no semantic owner or memory and
does not change the separate Research/Answer cache families.

Research now presents the logical acquisition catalog to the model as lossless
compact column-labeled tables. Material tables keep full field names, every
value, row order and absent-versus-null distinctions. The catalog also includes
a `documents` collection of user-document metadata without body text. The
previously tested representation reduced repeated Research catalog characters by
28.75% and reconstructed packet characters by 8.98% across 35 historical states
(8.57% counting the added instruction per call). User-document prompt
clarifications change the Research and Answer instruction-derived cache families.
The stable cache breakpoint remains unchanged. This efficiency evidence does not
establish better Research judgment, stopping, retention or general reliability.
See `docs/operator/CATALOG_TABLE_INTEGRATION_01.md`.

Research receives an ordered, turn-scoped mechanical history of failed external
Reads, including existing candidate identity, provider, effective fetch strategy,
requested mode, fixed safe failure code and measured elapsed seconds. This history
survives intervening routes and is navigation state, not Evidence. It resets for
each user turn, is absent from Answer packets and is not durable session state.
Successful acquisition remains represented by retained materials/catalog. Changing
only Read focus does not change the `static_fetch` strategy. There is no automatic
retry suppression or new provider strategy. The small Research prompt explanation
changes its instruction-derived cache-family hash; Answer's cache family, the
stable packet prefix and breakpoint mechanics remain unchanged. Offline tests
establish receipt mechanics and privacy, not improved stopping, retry choices,
latency or LinkUp reliability; no live validation was performed for this change.

Search novelty is mechanically measured for safe acquisition diagnostics and
forensic analysis only. Each successful Exa or lexical/Serper Search reports
provider/kind and eight numeric counts: returned/new/known candidates,
returned/new material, new-candidate material, refreshed-known-candidate material
and exact reused material. Identity, admission, duplicate handling and Serper's
navigation-only role are unchanged. Body-free diagnostics contain no query,
URL, title, highlights or source body. The diagnostic receipt is excluded from
Research's `last_route`; no cumulative Search history or replacement novelty
field enters Research or Answer, and session persistence is unchanged.

Both model-facing experiments were **MIXED / INCONCLUSIVE** and were not promoted.
Their history, including the second campaign's lost-draw limitation, remains in
`docs/operator/SEARCH_NOVELTY_RECEIPTS_01.md`. The model-facing history, helper,
accumulation and expected-yield prompt paragraph are removed. Research's prompt,
packet ordering and cache family are restored to merged-main PR #660 behavior;
`failed_external_reads` is unchanged. The final diagnostic-only disposition used
zero live calls; no third campaign ran. Telemetry describes acquisition movement,
not relevance, usefulness or sufficiency. No stopping, answer-quality, latency or
cost improvement is established.

Ordinary generic Exa Search uses six results and `contents.text=false`.
On `session_turn == 1` with no retained acquisitions entering the turn, the first
executed generic Exa Search uses `type=deep`; every later generic Search uses
`type=auto`. Other turns and retained-entry turns use Auto throughout. Read,
Find, lexical Search or Answer may come first; only execution of generic Search
consumes this run-local bootstrap, including a failed executed attempt. Direct
`search_exa()` callers still default to Auto. Query-specific Highlights use provider-native Dynamic
allocation with `dynamic=true`, `verbosity=high` and the
`Exa-Beta: dynamic-highlights-2026-08-28` header; no fixed `maxCharacters` is
requested. Actual returned source selections retain `provider_highlights` custody,
explicit separation and the existing size guard. Serper discovery and LinkUp
known-URL Read are unchanged. The initial integration received offline
verification; Exa Evidence-Objective Search 01 subsequently exercised the same
request mechanics in four ordinary product runs. No universal answer-quality,
latency or cost improvement is established.

A contiguous group of two or three ordinary generic Exa Searches inside one
Research route may send those Exa requests concurrently. Deep or Auto is assigned
before dispatch in original request order, including inside that group, and a
failed Deep still consumes the bootstrap. After transport settles, admission,
identity, catalog order, and novelty run serially in that same request order.
One Search failure does not cancel another already-dispatched Search. A run of
more than three generic Searches is divided into groups of at most three. If the
whole group cannot be reserved against the existing 16-attempt external budget,
or the run deadline has already expired, those requests stay on the serial path.
Read, Find, lexical Search, and any mixed route stay serial. Transport workers
do not allocate IDs or mutate the acquisition library. Body-free
`search_concurrency_groups` diagnostics record the route span, summed transport,
and overlap, without query or payload text.

Concurrent Exa Search 01 met its promotion gate on four fresh ordinary
single-turn sessions from base `2d589a7339a3a95fc11641dd1e4365a6cb87a14b`.
Effective settings were GPT-6 Luna / high / Fast for Research and GPT-6.1 Sol /
high / Standard for Answer. Seven successful concurrent Search groups occurred
across three of the four runs. Aggregate measured overlap was 16.516 seconds,
and the largest single group was 4.094 seconds. The St. Dorothy's turn produced
no same-route Search pair and remained serial. No concurrent group returned a
provider failure, rate limit, or malformed response. Completed postures were
supported, partial, and research-bound partial, and citations resolved to
selected Evidence. Estimated campaign spend was $0.71, under the $2 ceiling.
Two predetermined reserve questions were not run. Measured overlap is observed
concurrent transport, not a guaranteed user-visible speedup, a lower model cost,
or better answer quality. See `docs/operator/CONCURRENT_EXA_SEARCH_01.md`.

Exa Deep Bootstrap 01 met its bounded promotion gate in four ordinary fresh
sessions at `0da7f2843eebf7c2be8052e04ec32f5e9c20a59f`, without a prompt repair.
The effective settings were Luna / high / Fast Research and Sol 6.1 / high /
Standard Answer; user settings were not changed. BIPM remained correct with two
Research calls and one Search; Deep took 4.328 seconds versus a preserved Auto
acquisition's 1.297 seconds. Passport obtained the NASA relationship and GE range
in one Deep batch, reducing the observed trajectory from four Research calls,
two generic Searches and three Reads to two Research calls and one Search.
MD-80 used four generic Searches rather than ten, but still used eleven Research
calls, more Research input and repeated local Find; its honest partial Answer
omitted acquired unmatched MD-80 cost leads after Research shelved them.
Dorothy's final supported selection relied on later lexical discovery and Read;
its first Deep batch did not find the appointee and earns no appointment-frontier
credit. Historical observations differ in revision, time/index, stochastic routes,
cache behavior and completion; these are descriptive comparisons, not causal
latency or cost estimates. The MD-80 historical ordinary Answer was interrupted
by its campaign wrapper, and its separate recovery is only a frozen-packet
quality reference. No general Research-call, context-cost or reliability gain is
established. See `docs/operator/EXA_DEEP_BOOTSTRAP_01.md`.

Deep retains only the existing source-bound Highlight custody. Generated provider
answers, summaries, output/grounding, confidence and reasoning are excluded.
Body-free acquisition timing and dogfood diagnostics report the requested
`provider_search_type` (`auto` or `deep`), without query or payload additions.
Request, ResearchDecision, AnswerDecision and budgets are unchanged by Deep.
There is no depth decision field, semantic router, feature flag or persistent
bootstrap state. User-document custody does not consume or disable that bootstrap.

Research formulates ordinary generic Exa queries as concise natural-language
evidence objectives describing what source material should establish, retaining
consequential known entity, relationship, source-class, time, scope, applicability
and comparison constraints. Useful proper nouns, exact terminology, quotations
and source constraints remain available; lexical/community/current navigation
retains its separate lane. That formulation change added no mechanical query rewrite, semantic owner,
schema, provider/model router, or custody change. That prompt changes
Research's instruction-derived cache family.

Four fresh ordinary treatment sessions produced twenty generic queries:
eighteen objective-aligned, one acceptable neutral and one misdirected candidate
confirmation. BIPM stayed a correct one-Search lookup; Passport established the
applicable GE relationship and published range. St. Dorothy's remained a weaker
honest partial after failed Reads, with appointment/chronology unestablished.
MD-80 Research preserved comparability qualifications but its Answer was
interrupted by the ignored campaign reservation wrapper. A separately authorized
Answer-only recovery reused the exact Evidence and saved arithmetic without
Research or acquisition. It completed through unchanged production Answer
validation as a partial preserving denominator, aircraft variant, period/operator,
cost scope and estimated-versus-reported qualifications, without a clean scalar.
The trace lacked the original provider continuation envelope, so this was a fresh
Answer-only frozen-packet invocation, not a byte-exact HTTP resume or fifth
end-to-end product run. Historical efficiency is mixed and noncausal; no repeated
attributable material formulation-quality regression was established. The human
accepted mixed efficiency with valid recovery, satisfying the bounded promotion
gate. See `docs/operator/EXA_EVIDENCE_OBJECTIVE_SEARCH_01.md`; no general stopping,
quality, latency or cost improvement is claimed.

Dynamic Highlights Context Allocation 01 remains formally **INCONCLUSIVE** under
its original whole-product promotion gate. Nine provider-only calls showed uneven
allocation without a repeated custody failure. The five product runs did not
establish whole-product superiority: MD-80's extra Research cost had no shown
allocation cause, and St. Dorothy's omitted chronology in Answer after relevant
material arrived. Later architecture adjudication separated that downstream
outcome from retrieval-mechanism evidence and selected Dynamic/high for this
integration. See `docs/operator/DYNAMIC_HIGHLIGHTS_INTEGRATION_01.md`; sanitized
experiment evidence remains under ignored `local-evals/runs/dynamic-highlights-01/`.

## Sessions, Evidence and presentation

Immutable acquisitions, canonical source identities, exact versions/views,
literal Answer readings, deterministic citations and historical selected-material
snapshots survive. Follow-ups start fresh Research/Answer decisions and can reread
retained actual Evidence without external acquisition. The first Research call of
a follow-up receives the exact actual material cited by the immediately preceding
completed answer when it fits the existing attention limit. No earlier library
material is automatically exposed. Research may use, shelve or supplement that
material; it is not automatic Answer support. Research also receives historical
citation provenance derived from saved turns: answer-local citation numbers,
canonical source IDs and exact material IDs are navigation, not Evidence or a
claim that the prior answer was correct. A cited targeted view can be reconstructed
locally from its retained full parent. Answer sees ordinary conversation without
historical provenance aliases. Research chooses the source identities for Answer
through its ordinary exact Evidence selection. Immediately before explicit or
forced terminal Answer handoff, mechanics append omitted exact material already
exposed during the current turn from those same stored canonical source IDs.
Seed refs retain their order; appended document views follow source character
start and web material follows acquisition/Evidence-ID order, within selected
source order. Completion is all-or-nothing within the existing 128,000-character
Evidence allowance: an over-limit proposal leaves the seed packet unchanged.
No semantic ranking, version preference, summarization or new owner is involved.
Provisional Answer no-progress compares the effective completed packet; Research
reentry attention still uses its ordinary seed choice. Literal readings, citation
validation and saved source snapshots use the completed packet actually supplied
to Answer. A body-free trace receipt records seed/appended refs, final content
characters and completion status; no durable session state is added.
Unscoped Find ranks actual retained acquisition regions on
a comparable corpus-wide lexical scale rather than interleaving by acquisition
order;
lexical rank does not establish semantic relevance or support. Read gives a
mechanical receipt for the exact text returned, including parent coverage and
focused lexical hit or fallback status. `full` identifies the full-parent custody
target; a large parent may expose bounded exact views in one Read. Safe traces
include body-free conversation, catalog, retained-corpus and active-Evidence
size counts. Conversation supplies
non-evidentiary task context for intent, discourse, corrections and follow-up
meaning. Explicit premises in prior user questions may remain task inputs, while
user beliefs and narration are not automatically stipulated premises. Prior
assistant answers are discourse context only; they cannot silently become
premises. A user's explicit adoption of a prior assistant value can define a new
scenario premise without verifying that value externally.
Research chooses and acquires Evidence. Selected-source completion widens only
within chosen source identities. The primary semantic Answer,
`SemanticAnswerDecision`, has posture, `support_basis`, answer, and
`missing_information`, and no `source_readings`. Sol, on the existing Answer
model role, owns meaning, prose, adequacy, and citations. Luna, using the
existing Research model-role settings as transport only, performs
non-authoritative exact support localization on stage `localize`. That stage is
not a Research decision and is not a third persistent model role. Deterministic
checks validate literal custody. Localization does not consume
`semantic_attempts` and runs at most once per accepted terminal semantic Answer.
A consequential `missing_information` Answer returns to Research before any
localization when budget and no-progress rules allow another round. Unchanged
selection still publishes that provisional answer without localization.
User-premise answers with no Evidence, and unable answers, skip localization.

A terminal evidence-backed supported or partial Answer is localized only after
its semantic decision and individual citation occurrences are frozen. Code
partitions the entire cited saved material into exact addressable regions without
ranking, clipping or selecting support. Luna receives the final answer,
citation-use contexts and every region; it returns only a use-ID to region-ID
mapping. Every occurrence must bind to at least one valid region from its own
source. Unknown IDs, malformed mappings, duplicate regions and insufficient
bindings discard the semantic decision for publication and fall back once to the
existing `AnswerDecision`, `ANSWER_PROMPT`, and `source_readings` path on the same
completed Evidence packet, with no hint from the discarded answer or localizer.
That fallback is a semantic Answer request and receives a fresh Answer-stage
ceiling bounded by remaining whole-run time. Its one-correction behavior is
unchanged. If it fails, the turn keeps the operational inability message and
`answer_validation_exhausted` trace.

Successful normal localization resolves temporary IDs into use-specific support
coordinates, exact material references, and SHA-256 material/passage hashes.
These coordinates are durable; Luna quotations and temporary use/region IDs are
not. Reopen validates ranges, source membership and exact hashes against retained
Evidence without model or provider I/O. Reading Room citation clicks display that
occurrence's exact support first, expandable surrounding context second, and
full saved material third, with the original publication or PDF action prominent.
Old turns and legacy-fallback turns without coordinates retain generic saved-source
inspection. This presentation fallback does not change new-answer publication
eligibility. Two ordinary Reading Room turns at runtime revision
`30889acc1783608dae653e8e05d0b023fe5e1ae7` exercised public-web and uploaded-PDF
material. All fourteen citation occurrences retained exact support, with no
legacy fallback. A fresh process without credentials reopened both sessions;
desktop/mobile Reader clicks matched every occurrence's exact saved support.
Offline checks cover malformed/insufficient binding fallback, old-turn generic
inspection and corrupted coordinate/hash rejection. This bounded sample does
not establish general semantic localization reliability. The phase evidence is
recorded in `docs/operator/CITATION_READER_DURABLE_SUPPORT_PRODUCT_01.md`.

With an empty Evidence packet, a supported or partial conditional derivation may
use only explicit user premises, empty source readings and no Evidence citations.
An answer mixing user premises with external factual support uses the evidence
basis and cites its external claims. An Answer that declares both supported
posture and a consequential `missing_information` need is corrected as an
Answer-shape error; it does not create a Research round trip or mechanically
change the posture. Literal-reading corrections on the legacy path identify the
failed reference and reading/passage indexes without copying the rejected
passage into the correction or safe trace. Localization passage rejections use
the same boundary: a safe trace event plus a `source_body=True` observer record.
Ordinary traces, dogfood records, sessions and presentation remain body-free for
that diagnostic.
Neither path promotes user premises or prior assistant prose into Evidence.

Durable SQLite sessions retain atomic revision-checked commits, reopen/history,
rename/delete and failure isolation. Native turns use `analysis: null` in the
backward-readable snapshot schema. Historical Analysis is retained and
validated only on serialization/reopen; it never controls new research or becomes
Evidence. Historical turns and citations are not rewritten on reopening.
The synthetic pre-supersession fixture exercises mixed historical/native sessions.

The session store is schema 2. A version-1 database gains the additive
`session_documents` table and advances `PRAGMA user_version` to 2 without
rewriting existing session payloads. Opening a current database does not rewrite
those payloads. An unknown newer schema still fails as `incompatible_session_store`
without being rewritten. Each text PDF belongs to one session as `D1`, `D2`, and
so on. The row stores the original PDF blob, filename, SHA-256, page count, and
the deterministic pypdf page extraction. The same SHA-256 uploaded again into
that session returns the existing document and does not allocate another ID.
Another session can hold its own copy. Attaching a document does not create a
turn or advance the completed-turn revision, including a blank session at
revision 0. Deleting the session deletes its document rows and PDF blobs.
Selected exact document views may be saved with a completed turn; the extracted
parent is not copied into every turn payload. A document citation's displayed
page locator lists those exact selected pages. Contiguous pages compact into a
run, and unselected pages between them are not included. Stored `page_start`
and `page_end` remain the coarse bounds of the citation group.

Extraction uses `pypdf>=6.19,<7` (this verification used 6.19.0). The bounds are
20 MiB, 500 pages, and 2,000,000 extracted characters. There is no OCR, image
analysis, or vision-model path. The product states that it analyzes extracted
PDF text only and that images and scanned content are not analyzed. Pages with
no extracted text are counted, not described as images. Encrypted, malformed,
empty, and over-limit PDFs are rejected with fixed messages. Research sees
document metadata in the catalog, not the PDF bytes or the whole extraction.
Local Read and Find use the retained text, spend no external attempt, and do not
consume the Exa Deep bootstrap. A large document uses the existing bounded
packet and exact-view limits. Document text is Evidence of what that document
states. Web Search, Serper, and LinkUp remain available on the same turn.
Body-free diagnostics may count documents, pages, characters, local Read size,
and Find region counts. They do not record filenames, queries, or page text.
No Jev, Clef, embedding, or vector index is part of this path.

Offline verification on this branch was `771 passed`, `ruff check .`, and
`git diff --check`. Four ordinary product turns, brokered with the repository
credential doorman and frozen synthetic or public text, then confirmed custody
and citations: a direct document fact with zero external attempts; a later-page
fiscal-year and exclusion qualification retained from the extracted text; a
new-process follow-up on the same `D1` without re-upload; and a PDF claim of a
1948 WHO founding compared with `https://www.who.int/about` and
`https://www.who.int/about/history` after one external Exa search. The first
Research call on a fresh document session received no document body. Campaign
external attempts were 1. Two frozen reserve cases were not run. Search width
remains 6. Semantic, external, time, and attention limits remain 12, 16, 300
seconds, and 128,000 characters. Targeted and expansion packets remain 32,000
and 48,000 characters.

Reading Room and CLI use the same session application and store. The existing
safe Markdown/source renderer, browser security, local assets, transport,
credential doorman and exact-content prompt-cache mechanics remain in place.
Reading Room can explicitly append one body-free JSONL diagnostic record per
attempted question with `--dogfood-log PATH`. The default remains off. The local
log records turn timing, model usage when returned, call/correction counts,
per-request acquisition timing and safe sizes, keyed by session ID and attempted
turn. It is separate from the durable research-session schema and contains no
question, answer, prompt or source text. An unusable explicit log path prevents
launch; a later write failure disables only diagnostics while the completed
research session remains intact. The same diagnostics supported ordinary live
latency observations. Opt-in `--forensic-log PATH` adds a separate local,
development-only JSONL sink for the ordinary engine's observer events. It may
retain acquired and exposed source text, selected readings, rejected attempted
passages and Research decisions, correlated by session, attempted turn, process
run and event sequence. It does not capture raw provider payloads or hidden
reasoning. The body-free dogfood projection and durable session schema are
unchanged; a forensic write failure disables only that sink. Log paths that
alias one another or the session database are rejected at launch. The
development launcher creates isolated runs under `C:\tmp\scryraven-forensic`;
cleanup selects one exact child run explicitly. This instrumentation makes
ordinary failures reconstructable and does not repair source-reading failures.
Explicit forensic observation also records each Answer calculator expression and
its deterministic result or error in sequence. Ordinary traces and dogfood
diagnostics retain only body-free calculator counts/status and request usage;
Answer continuations aggregate reported provider usage within their one semantic
attempt and mark partial usage when a continuation has no reported counters.
Both surfaces disclose that no external sources were used for source-free
supported/partial completed answers without inferring a user-premise basis from
empty citations. They disclose a Research operating-bound completion without
changing Answer's supported/partial/unable posture. Known safe Exa and Serper
configuration errors retain their fixed codes through Acquisition. LinkUp retains
`linkup_timeout`, `linkup_connection_failed`, `linkup_endpoint_access_rejected`
(401/403), `linkup_endpoint_rate_limited` (429), `linkup_endpoint_server_failed`
(5xx), `linkup_json_invalid`, `linkup_response_invalid`,
`linkup_material_unavailable`, `linkup_configuration_missing` and the unknown
transport fallback `linkup_transport_failed` through Acquisition and body-free
diagnostics. Endpoint codes describe the LinkUp API, not the target website.
Unrecognized injected Read failures remain `read_failed`. No raw provider failure
body, exception text, headers or credentials enter these receipts or diagnostics.
`ModelConfig.research` and `ModelConfig.answer` hold the resolved OpenAI role
settings from effective user configuration or shipped defaults. Explicit injected
`ModelConfig` remains available. Obsolete FAST/SMART model environment overrides are removed;
`.env.example` holds credential placeholders only, and the product does not load `.env`.

## Bounded evidence and limits

Selected-Source Completion Product 01 met its bounded mechanical gate at runtime
revision `4c0c447216895115b0aaa7dbf59653ebe2b61db9`. Two ordinary durable-session
observations used five Research calls, two Answer calls and four external attempts.
The PDF run completed the selected `D1` packet with its exposed page-5 table of
contents and whitespace-only page-11 range. Research itself selected page 8;
Answer retained the proposed conservation transfer, up-to-$2.5 million scale,
hiking/program access and conditional status alongside the broader turnaround.
This does not demonstrate a completion-caused rescue of page-8 coverage. The web
run appended a previously exposed 495-character ABC7 highlight to its selected
full article. Answer preserved diagnosis uncertainty, geographic risk scope and
California's separate wildlife-associated risk; that ABC7 group was not cited.
No material regression attributable to completion was observed. Both turns passed
ordinary literal-reading/citation validation; their cited exact-material snapshots
persisted unchanged after reopen. The PDF Answer prose did not disclose extracted-text-only coverage
or its two textless pages; the separate disclosure limitation was not repaired.
No third run, untreated control, independent source checking or model judge was
used. Overflow and missing-information reentry were verified offline, not exercised
live. General coverage, currentness and reliability remain unproved. Exact local
evidence is under ignored `local-evals/runs/answer-selected-source-completion-product-01-20261006/`.

Answer Coverage Retention used unchanged development packets and the production
Answer prompt, schema, model transport, calculator, validation and finalization.
The promoted prompt retained both the MD-80 replacement-model versus historical
777 distinction and the CASM/load-factor relationship in two draws. Both refused
unsupported empirical subtraction and explained why occupancy alone cannot fix
incompatible cost figures. Rich comparison, simple lookup, partial evidence,
assumption-policy negative and quantitative controls preserved material quality.
The lookup stayed one sentence; the quantitative control used the calculator and
returned the correct $2,112 (8.4%) bill reduction. This is bounded direct-Answer
evidence, not an ordinary research run or a universal coverage guarantee. Earlier
prompt variants showed omissions and variability. Production support-basis
semantics remain unchanged; the separate finding that Answer-chosen numerical
assumptions are not user premises remains unresolved. See
`docs/operator/ANSWER_COVERAGE_RETENTION.md` for scope, provenance and limits.

The preceding ten-turn latency flight took 304.796 seconds: Research model time
was 65.0%, Answer model time 25.4%, and external I/O 9.5%.

Latency Consumption 01 kept Luna / high Research after bounded effort comparisons
with Sol / medium / Standard Answer fixed. In the initial
six-case effort comparison, high took 90.094 Research seconds and 146.047 wall
seconds; medium took 60.234 and 104.250 seconds. A paired Passport repeat changed
the decision: high found the controlling 17,325–18,920 lb base-engine range in
15.842 Research seconds, while medium pursued the CT7 aircraft-engine tangent
for 62.937 seconds and returned a partial answer without the range.

The three-case Standard/Fast comparison kept Standard processing. It returned the
requested tier for every Research call, yet Fast took 73.608 Research seconds and
115.094 wall seconds against Standard's 36.938 and 69.079 seconds, with greater
token use and estimated cost. Answer remained Standard.
Routes and cache outcomes differed, so these totals do not isolate service speed.
In a later isolated fixed-packet screen, Sol / medium / Fast showed a consistent
latency benefit. Luna / high / Fast evidence was noisier; the Fast default is a
pragmatic, reversible operational choice, not a universal speedup. Fast may cost
more per token. No runtime cost estimator is implemented.

In two copied-session direct follow-ups, initial exposure of prior-cited exact
Evidence reduced Research
calls from four to two, local Reads from three to zero, Research time from 16.687
to 8.719 seconds, and wall time from 34.577 to 22.594 seconds. An unrelated
Euclid follow-up still acquired new ESA material; treatment added 1.156 wall
seconds in that negative control. These are bounded observations, not general
latency or reliability guarantees. That campaign promoted no packet/catalog,
route-width or acquisition concurrency change. A final ordinary default-path
BIPM follow-up
at implementation revision `95cdbdd` answered from prior-cited Evidence in one
Research call with no acquisition; Research and Answer returned Standard service.
The sanitized campaign artifacts are under
`C:\tmp\scryraven-latency-consumption-01`; see
`docs/operator/LATENCY_CONSUMPTION_01.md` for the adjudication and ledger.

Packet Efficiency Promotion 01 follows an 18-call frozen-packet screen: Layout
and purpose removal each preserved the consequential obligation in 6/6 decisions.
In ordinary-product confirmation, both independent treatments and their
combination supported the exercised Passport dependency and retained parkrun
follow-up; each parkrun arm used prior-cited Evidence without Search/Read/Find.
The prior Passport Control draw remained partial, while the independent Layout,
purpose-removal and Combined draws established the requested Passport range.
These separate stochastic draws do not show that the treatments caused the
Passport difference, guarantee fewer calls or establish a general latency win.
The sanitized confirmation is under
`C:\tmp\scryraven-packet-confirmation-01`.

On the frozen Answer screen, GPT-6 Sol / medium produced 12/12 acceptable draws.
In the ordinary product-path Research screen with that Answer role fixed, GPT-6
Luna / high met every exercised Research obligation. The Elytra post-Evidence
dependency redirect was unexercised because both relevant sources arrived in the
initial Search batch, so the registered 6/6 screen was formally inconclusive.
No material Luna / high Research-layer failure was demonstrated. These bounded
observations do not establish universal reliability.

The LinkUp primary Read change is supported by bounded known-URL evidence: 4/4
rescues of demonstrated Exa Read problems, 8/8 task-sufficient ordinary controls
with no observed material control regression, corrected integrated validation at
3/3, and three supported source-bound product canaries. A no-URL control answered
from acquired Exa Search highlights without an unnecessary Read; deterministic
tests establish the Exa Search / LinkUp external Read composition. These results
do not establish universal provider superiority or general product reliability.

The Research-selectable Serper lane completed one ordinary St. Dorothy's Rest
observation at `884c69a917aa19528574da42fdae2a8b85ba86b1`: Research chose
three lexical searches among seven Exa searches, then used two LinkUp Reads.
The Serper-discovered official Instagram post was fetched through LinkUp and
cited for the director selection. The final supported answer used that fetched
post and acquired Exa highlights for qualifications. The run used seven semantic
attempts and 12 external attempts. This shows one successful source-class route,
not general semantic-selection reliability or Level-7 synthesis.

Foundation 01 established four valid frozen Levels 1–3 cases; its NPS comparison
was excluded for evaluator/source ambiguity. Foundation 02 established three
frozen Level-4 bounded synthesis cases, including Anker missing-premise restraint.
Recursive 01 produced correct shortcuts but was inconclusive for dependency
change. Recursive 01B established three counted Level-5 transitions (G1 Passport,
G2 Sentinel-1, G7 Elytra); G3–G6 were correct unexercised shortcuts. These are
bounded development observations, not universal or general recursive reliability.

The exact public packets remain external under
`C:\tmp\scryraven-luna-foundation-01-20260919`,
`C:\tmp\scryraven-luna-foundation-02-20260919`,
`C:\tmp\scryraven-luna-recursive-01-20260919`, and
`C:\tmp\scryraven-luna-recursive-01b-20260919`.
The accepted lineage was `codex/luna-capability-recursive-01b` at
`b72defe1fa05568175a6a39a91b858a0783d6504`, descended from production baseline
`533f45df9271978e0591fb35aa8da2b1917255b2`.

Supersession offline verification covers ordinary routing, retained follow-ups,
backward-readable persistence, exact citations, CLI, Reading Room and failures.
The full offline suite, Ruff, pre-commit and browser acceptance at 1440, 1920 and
390 pixels passed. Mainline Semantic Supersession 01 acceptance is **Met**.
Six ordinary live submissions, all Luna / medium, used 19 semantic attempts,
ten external Searches and one local retained Read. The initial five ran at
`d544cef780186f63e08d29d390653e84fd279f05`; the single authorized Anker confirmation
ran at `97c3c77aa501a9cf0d37c2a4e21f9fde37455cae` with identical runtime code and
prompts. JWST multi-need compatibility, the durable BIPM pair and a counted
Passport Level-5 dependency transition passed. BIPM's reopened follow-up acquired
nothing externally and preserved the first turn and all six acquired materials
exactly. Those accepted obligations were not rerun for closure.

The first Anker control preserved the central missing-premise restraint: it did not
derive Wh from mAh and distinguished Anker's explicit 99.54 Wh specification.
However, its final Answer and exactly captured cited material did not establish
the voltage-dependent conversion rule required by the frozen Foundation 02
rubric. That first trajectory remains incomplete and preserved. The one unchanged
confirmation acquired and cited FAA's volts-times-ampere-hours rule, establishing
the required Ah unit and voltage dependency, and again treated Anker's independent
99.54 Wh specification separately. It satisfies the complete frozen L4C obligation
without a semantic code, prompt, provider-policy or model-policy repair. The two
trajectories demonstrate bounded acquisition variability, not deterministic
retrieval reliability. No other live rerun or Level-6 work occurred within that
supersession acceptance.
See `docs/operator/MAINLINE_SEMANTIC_SUPERSESSION_01.md` for the evidence and
review bundle. Both public observations are preserved in
`C:\tmp\scryraven-mainline-semantic-supersession-01` and useful sanitized local
evaluation candidates; prior frozen labels and packets remain unchanged.

Level-7 Baseline 01 produced strong bounded evidence that, when suitable
heterogeneous material reaches Answer, ScryRaven can produce useful open-world
synthesis without automatically promoting sampled discussion to population-wide
claims. A representative-survey control supported appropriately stronger
aggregate claims. Eight synthetic Answer diagnostics handled engagement asymmetry,
echo amplification, temporal/version shifts and sparse heterogeneous evidence.
This does not establish general open-world reliability. Several live cases were
blocked earlier by community-source Read/materialization failures.

Reddit/community discovery can surface candidate URLs, but tested generic Read
surfaces did not reliably materialize Reddit thread bodies. Community Read
Forensics 01 found 24 failed Reads across 15 exact Level-7 trace URLs; six sampled
Reddit threads yielded no usable body through LinkUp, Exa Contents, Jina Reader or
plain HTTPS. Reddit remains a known source-access limitation: discovery alone is
not Evidence, and ScryRaven cannot characterize Reddit reception without actual
Reddit material in Evidence. The BasicAF Exa-cache result was an isolated
archival/article recovery observation, not a general alternate Read capability.

At current-revision `b6f059b4d406155fa6ad4a8d3f06bb48d3fed49d`, Level-8
Baseline 02 completed seven of eight behavior-first families. They demonstrated
bounded dynamic decomposition, consequential qualification, selective premise
revision, changing-scope handling, multi-turn follow-up, scenario/user-premise
reasoning, conditional calculation separated from external factual claims, and
identification of bottlenecks outside the named component. C01 had minor Answer
qualification/arithmetic imperfections; C04 had an ancillary provenance gap; C07
did not establish full numerical ten-year pricing; C08 appropriately remained
incomplete rather than naming a historical cumulative-cost winner. No completed
case demonstrated the defined Luna/high Research interpretation/decomposition
failure needed to earn a Sol interpretation stage.

C02 remained operationally unassessable after `answer:model_response_incomplete`
in both Level-8 baselines. An exact current-revision Answer replay at the unchanged
12,000-token cap returned provider status `incomplete` with safe reason
`content_filter`, not `max_output_tokens`. The two historical failure reasons
remain unknown because their safe traces did not preserve the provider reason.
The replay supports no output-cap, prompt, retry or model repair, and it does not
demonstrate a Research or Answer semantic failure.

The ordinary transport now preserves fixed safe incomplete classifications for
`content_filter` and `max_output_tokens` in failure diagnostics. Unknown or
malformed incomplete reasons remain the generic `model_response_incomplete` code.
The run trace records elapsed monotonic time and safe model return/failure events.
The longer hard ceiling does not establish user-perceived latency acceptability;
the bounded latency observations above leave broader dogfood latency unresolved.

Literal-reading and citation validation prove custody/membership, not semantic
entailment. All prior question and answer text remains in every Research and Answer
call without aging or trimming; very long-session performance remains unproved
and no context-compaction lifecycle is implemented. Catalog scaling and caching
remain unproved. General
reliability remains unproved. Level 6 revision/recovery under superseding Evidence
is **not established**. No Sol interpretation/decomposition pass is part of the
ordinary product path or currently earned. Only repeated consequential exact
cases of recoverable Luna/high task-interpretation failures with sufficient
context and working acquisition would justify a bounded comparison.

The synthetic capability ladder has produced bounded evidence through open-world
synthesis and dynamic multi-component research. The project is suitable for
ordinary dogfooding; further reliability evidence is expected primarily from
preserved organic failures rather than additional capability machinery by default.

## Preserved development history

The stopped Investigator and earlier architecture-lab branches remain intact.
The failed Observation/Inference/scope-contract experiment and invalid Sol closure
probe remain historical records, not active semantics. Their executable old-owner
harness is absent from the product tree. Operator campaign scripts, frozen
manifests, external packets and ignored `local-evals/` are development evidence;
ordinary runtime has no dependency on them. No evaluation evidence was deleted.

Current architecture: `docs/architecture/RESEARCH.md`. Earlier V2/baseline and
Investigator architecture documents are explicitly historical snapshots.
