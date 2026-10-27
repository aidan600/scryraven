# Ordinary Research / Evidence-first Answer architecture

The ordinary topology is initial Luna Research -> Sol Answer with optional
resumable delegated Research. The merged briefing promotion preserves the topology
merged in [PR #677](https://github.com/aidan600/scryraven/pull/677) and passes
Research interpretation alongside originals. [PR #679](https://github.com/aidan600/scryraven/pull/679)
merged this implementation at `33511b268d9b07ab10bc0725d488132fb5e3f324`;
see `docs/operator/RESEARCH_ANSWER_BRIEFING_PROMOTION_01.md` for its review and
verification, and `docs/operator/RESEARCH_ANSWER_BRIEFING_01.md` for the historical design report.
Research -> Analyst -> Author remains retired. There is no production selector,
alternate engine or fallback. `CURRENT.md` distinguishes implementation from
bounded demonstrations and remaining limitations.

## Two semantic contracts

`scryraven.research` has two semantic model contracts: Research and Answer.
Ordinary runtime selects `ModelConfig.research` or `ModelConfig.answer`; the
package ships tracked defaults in `scryraven/model_roles.defaults.json`: GPT-6 Luna /
high / Fast for Research and GPT-6.1 Sol / medium / Fast for Answer. An optional
complete user/operator `model_roles.json` outside the repository overrides all
three execution settings. Explicit injected `ModelConfig` takes precedence over
the user file, which takes precedence over shipped defaults. `built_in_model_config()`
reads shipped values; `default_model_config()`, `ModelConfig()` and `OpenAIModel()`
resolve one coherent effective snapshot. Both files receive the same strict
validation; malformed user settings fail locally without falling back.

Windows uses `%LOCALAPPDATA%\ScryRaven\model_roles.json`, with
`~/AppData/Local/ScryRaven/model_roles.json` as the absent, empty or relative-root
fallback. macOS uses `~/Library/Application Support/ScryRaven/model_roles.json`.
Unix uses `$XDG_CONFIG_HOME/scryraven/model_roles.json`, falling back to
`~/.config/scryraven/model_roles.json` for an absent, empty or relative root.
The loader creates no file and reads no model-value environment overrides.
CLI, Reading Room, sessions and direct `run()` construct a fresh ordinary model
per turn, so a user edit applies to the next turn without restarting the process
or editing source, committing or opening a PR. Explicitly retained model instances
keep their resolved settings. Full injection bypasses both files; partial injection
fills only the missing role from effective settings. Injection is invocation-local
and writes nothing. The external file is the current settings boundary; no UI,
settings endpoint, write API, database settings, watcher or merging layer exists.
These values are reversible product configuration, not architectural requirements
or a model router. Compatible injected configurations may vary in quality and
validation coverage. A bounded latency comparison kept high after medium missed
a controlling Passport identity lead.
The earlier ordinary-route Standard/Fast comparison did not isolate a Fast speed
benefit; a later isolated fixed-packet screen showed a consistent latency benefit
for GPT-6 Sol / medium / Fast and noisier evidence for Luna / high / Fast. The
shipped GPT-6.1 Sol / medium / Fast Answer configuration has offline verification;
Independent Answer Library Access 01 exercised the effective user override
GPT-6.1 Sol / high / Standard, without isolating a model or tier benefit.
Fast may cost more per token, and
there is no runtime cost estimator. Model choices are not
read from environment variables; `.env.example` contains credential placeholders.
No Sol interpretation/decomposition pass precedes Research. Such a pass may be
compared in a separate bounded experiment only if Level-8 or later dogfooding
shows repeated, exact cases of materially recoverable requests with sufficient
conversation context and working acquisition, yet Luna/high misidentifies the
task, loses a user correction, or decomposes the wrong problem. The exact cases
must be preserved. The comparison would test direct Luna Research against one
Sol interpretation/decomposition pass followed by Luna Research; it is not a
production route to prebuild. No tested current case has earned that experiment.

Exa supplies ordinary general Search. Research formulates generic Exa queries as
concise natural-language evidence objectives describing what source material should
establish, preserving consequential already-known entity, relationship,
source-class, time, scope, applicability and comparison constraints. Proper nouns,
exact terminology, quotations and source constraints remain available when part
of the need. Research writes the query directly; no mechanical query transformer,
extra model call, new schema or semantic owner is introduced. Research may select
lexical/community/current discovery through Serper for literal phrases, site
constraints, social/community sources or exact/current navigation when useful. LinkUp static
Fetch supplies ordinary external known-URL Read. There is no automatic search
fallback, Read fallback, provider router, model router,
premium escalation, Scout, specialist hierarchy, verifier, or prose polisher.

For a fresh first session turn (`session_turn == 1`) with no retained acquisitions
entering the turn, a private run-local transport wrapper sends the first executed
generic Exa Search with `type=deep`. It consumes the bootstrap on execution,
including a failed request, and sends subsequent generic Searches with
`type=auto`. Other turns and retained-entry turns use Auto throughout. Earlier
lexical Search, Read or Find does not consume it; an Answer without generic Search
makes no Deep request. Direct `search_exa()` callers default to Auto and its
accepted types are bounded to Auto and Deep. Research selects the ordinary route
and writes the evidence objective; it has no provider-depth field or decision.
There is no fresh-problem classifier, persistent token, feature flag or new
semantic owner. Later unrelated questions and follow-up eligibility are not
classified beyond the existing turn/retained-entry boundary.

A contiguous run of two or three ordinary generic Exa Search requests inside one
Research route may send those Exa calls concurrently. The executor assigns Deep
or Auto before dispatch, in original request order, and admits each result
serially in that same order after every transport in the group has settled.
Finish order does not allocate candidate, Evidence, or source identity and does
not change novelty, which is calculated against library state that already
contains earlier requests from the group. A failed Deep still consumes the
bootstrap. One Search failure does not cancel a sibling that was already
dispatched, and there is no automatic serial retry. A group that cannot be
reserved under the existing external-attempt allowance, or that is reached after
the run deadline has expired, uses the ordinary serial executor. Read, Find,
lexical Search, and any request that breaks the contiguous generic-Search run
stay serial. At most three generic Searches share one transport group. Body-free
diagnostics may record that group's route indexes, transport sum, span, and
overlap. Research still chooses acquisition routes. This transport overlap changes
neither acquisition policy nor the Research prompt and adds no semantic decision-maker.

Both modes request six results, `text=false` and Dynamic/high Highlights with
the existing beta header. Only exact source-bound `results[].highlights[]` enter
the unchanged Highlight custody path, including separate-selection markers and
the size guard. Generated synthesis, summaries, grounding, confidence and provider
reasoning are excluded. Body-free acquisition timing and optional dogfood
diagnostics report the requested `provider_search_type`, not inferred internal
provider routing. They add no query, payload or authentication material.

**Research** owns investigation and provisional interpretation. It returns one
shared `ResearchDecision` in both initial and delegated episodes: `briefing`,
`action` (`research` or `return`), `requests`, `retain`, and `evidence_refs`.
The briefing is a compact account of useful conclusions, source references,
qualifications and consequential unresolved needs. It is proportional freeform
analysis, not a fixed finding ledger or polished user answer. A null update keeps
the latest briefing; new evidence may revise or replace it. No extra model call
prepares the handoff. Search, Read and Find have operation-specific request
shapes; acquisition fills mechanical defaults rather than making the model emit
irrelevant fields. Routes may contain independent requests; dependent follow-ons
wait for the returned material.

`retain` chooses exact originals to repeat in the next Research packet. Shelved
material stays in the catalog and can be selected for Answer or read locally.
`evidence_refs` selects actual exposed material, exact ranges or optional unique
text locators. The runtime reconstructs original text; copied locator text never
becomes Evidence. Initial and delegated returns use the same independently valid
selection admission. Bad selections are reported without discarding good ones
or forcing a repair call. Invalid retain IDs are filtered. Structural/schema
errors receive at most one correction per Research episode, then an honest
operating limitation with available valid work. Limits do not establish support.

**Answer** receives the immutable current question, conversation, operating date,
`research_briefing`, selected exact originals, acquisition/selection limitations,
library navigation and resources. The briefing is fallible analysis, not Evidence
or binding authority. Answer may adopt well-supported findings without repeating
the investigation, scrutinize originals when scope, chronology, applicability,
comparison or contradiction warrants it, and revise or reject Research's account.
Generated references never add citation membership. External factual claims must
remain supportable by actually supplied source material.

Answer writes the conversational response and owns its supported, partial or
unable posture. It develops useful relationships, representative support,
calculations and qualifications for analytical questions; simple lookups stay
compact. User stipulations can support conditional reasoning but beliefs,
assistant history and model recollection do not become external facts. Documents
establish what their supplied text states, not independent outside verification.

Answer may invoke `research(need)` for a consequential gap. The same Research
loop uses the original question, latest briefing, shared library, acquisition
receipts and remaining resources. It returns a revised briefing, exact originals
and honest limitations to the same native Answer interaction. No provisional
final checkpoint, Answer restart, continuing investigator or mandatory tool call
is added. Final `missing_information` describes a limitation only.

Research chooses outside acquisition and suggests initial Evidence; it does not
control Answer's access to the current session's retained originals. Within the
existing Answer attempt, `library_browse`, `library_find` and `library_read` adapt
the same `AcquisitionLibrary`, SourceIndex and exact-view machinery. The initial
catalog and subsequent pages contain at most 24 acquisitions/documents, including
material from earlier turns. Material IDs distinguish versions; shared source
IDs identify their relationship. Metadata is navigation only. Read/Find return
exact acquired text, and only returned material becomes citation-eligible.
Candidate-only links and unacquired portions of a highlight are inaccessible.
No operation can dispatch an external provider, access another session or alter
an original. Exact views may enter the in-memory material map.

Answer chooses whether to inspect; there is no mandatory read stage. The adapter
allows 12 local operations over the continuing Answer, across delegated returns and correction, with 128,000
characters of source attention including initial Evidence. Results normally
contain at most 32,000 characters; an already-admitted provider highlight up to
65,536 characters can be returned whole without inventing page coordinates.
Repeated returned text spends attention again. Large full parents use existing
bounded exact views. Catalog browsing supplies no source text. Local inspection
does not require delegation; a consequential unacquired need may use the Research tool.

These tools coexist with the calculator in the existing Responses continuation.
Both API and plan transports accept only tools declared for that request, with
strict arguments, call identities and opaque reasoning continuity. The existing
whole-turn deadline and physical allowance include all continuations. Safe
receipts record physical requests, usage, elapsed time, local operations, exact
material/source/parent IDs, ranges, content hashes and UTF-8 byte counts. Public
source-body observation remains a separate opt-in diagnostic projection.

The Answer contract is `SemanticAnswerDecision`: posture, `support_basis`,
answer, and `missing_information`. Sol, through the existing Answer model role,
owns meaning, prose, adequacy and citations. It evaluates the briefing against supplied Evidence and cites exact supplied
aliases beside supported factual claims.
A completed valid Answer proceeds directly to deterministic citation resolution
and publication. No model localizes passages, copies `source_readings`, or
regenerates an otherwise valid whole answer for presentation.

The existing schema, posture/need and support-basis checks remain. A missing
required Evidence citation receives the existing single correction; all invalid
primary response categories share that allowance and whole-turn limits.
Invalid aliases, unavailable versions and custody failures reject publication.
Exhausted validation yields operational inability with no rejected prose or support.
There is no terminal partial/reentry checkpoint. A final supported, partial or
unable response completes; unresolved missing information remains a limitation.
Only completed valid source-backed work may publish. Explicit user-premise
derivations can complete without citations even when unrelated originals exist;
mixed factual claims use Evidence and cite their originals. Generated notes,
conversation and prior assistant prose never become Evidence.

New citation uses have no passage coordinates. They open the exact selected
saved source material through the generic Reader, with original publication or
retained PDF/page actions. They make no exact highlighted-support claim.
Historical support coordinates, source snapshots and hash validation remain
readable and render their saved occurrence-specific support without inference.

The same Answer semantic owner may call a bounded deterministic local arithmetic
calculator while preparing a `SemanticAnswerDecision`. It may use numeric values from
selected Evidence, explicit user premises, and prior results from that Answer
attempt. A tool result returns to that Answer role; dependent calls can follow.
The local parser accepts bounded arithmetic expressions only. It computes exact
rational values from decimal literals, returning terminating decimals or
parenthesized exact ratios that can be reused in later expressions.
The calculator interprets neither sources nor provenance and creates no Evidence
item or alias. Results are derived computation. Externally factual quantitative
claims still cite the selected material establishing their inputs, and arithmetic
cannot supply an absent contingent external premise. Research has no calculator
tool. A calculator stop and its model continuation remain inside one Answer
semantic attempt, without using the one validation correction. Each underlying
Responses request still obeys its timeout and the remaining whole-run deadline. Reported per-request usage is aggregated for that semantic
attempt; a missing continuation counter leaves a marked partial aggregate.

## Acquisition, custody, and reversible attention

`scryraven.acquisition.AcquisitionLibrary` retains immutable actual
`Evidence` and supplies an inspectable catalog. Ordinary Search admits source-derived Exa
highlights mechanically. Serper lexical search supplies navigation candidates only:
its snippets never become Evidence. Research can Read an observed candidate URL
through LinkUp to acquire actual source material. Navigation-only metadata is not
admitted as source text.
External Read retains LinkUp's readable source representation as fetched Evidence;
local Read reuses actual retained material or constructs an exact view. A historical
targeted-view ID can be rebuilt from its retained full parent without provider I/O;
the view itself need not persist globally. Direct IDs follow the existing bounded
targeted-view size; longer spans use an explicit parent range that splits into
bounded views. Find locates lexical matches in retained
material, including highlights, without provider I/O. Unscoped Find ranks regions
from actual retained acquisitions on one corpus-wide lexical scale; scoped Find
keeps its source-specific inspection behavior. Ranking is navigation, not a
judgment of relevance or support.
A failed search or local match says nothing about factual nonexistence.

Acquisition retains fixed safe `exa_configuration_missing` and
`serper_configuration_missing` failures. LinkUp transport, Acquisition and
body-free diagnostics preserve `linkup_timeout`, `linkup_connection_failed`,
`linkup_endpoint_access_rejected` (401/403), `linkup_endpoint_rate_limited` (429),
`linkup_endpoint_server_failed` (5xx), `linkup_json_invalid`,
`linkup_response_invalid`, `linkup_material_unavailable`,
`linkup_configuration_missing` and `linkup_transport_failed` (unknown transport
fallback). Endpoint classifications establish only a LinkUp API response, not a
target website status. Unknown injected Read exceptions remain `read_failed`;
invalid injected fetched material remains `unusable_fetch_material`. Raw failure
text, bodies, headers and credentials do not cross these diagnostic boundaries.
A single provider failure does not force a turn-wide fail-fast decision;
Research judges the acquisition result.

Research receives one turn-scoped `acquisition_history` of compact operation
receipts. It records attempted requests, resulting material/candidate IDs, safe
errors and failed external Read details without repeating full originals. This
replaces separate latest-route, failed-Read and delegated prior-history packets.
It helps the investigator avoid repeating unchanged routes; it does not decide
retry policy or establish absence. LinkUp's effective external strategy remains
`static_fetch`; changing only the Read focus does not change that strategy.
The history is not persistent semantic memory. Answer receives actionable
acquisition limitations rather than the full worker operation log. Existing
forensic and body-free diagnostics keep their respective privacy boundaries.

Successful Search and lexical Search produce `search_novelty_receipt` solely for
safe acquisition diagnostics and forensic analysis. Its shape contains `provider`
(`exa`/`serper`), `kind` (`search`/`search_lexical`) and eight numeric counts:

- `returned_candidate_count`, `new_candidate_count`, `known_candidate_count`;
- `returned_material_count`, `new_material_count`;
- `new_candidate_material_count`, `refreshed_known_candidate_material_count`;
- `exact_reused_material_count`.

Candidate identity remains the library's exact observed URL key and existing
public-URL admission check. Counts use unique valid candidate identities and
unique returned material IDs, measured against the library before each request.
`_retain` still compares exact URL, content and acquisition kind. New records
partition by whether the URL was already known; returned preexisting records
count as exact reuse. Duplicate identical slots add no counts; distinct versions
of one URL remain separate material IDs. Empty successful Searches produce zero
counts; failed or denied requests do not produce a success receipt. Serper
remains navigation-only with zero material counts.

Body-free acquisition timing and dogfood diagnostics retain only these counts and
fixed provider/kind values, never queries, URLs, titles, highlights or bodies.
Existing forensic acquisition-result events retain the diagnostic receipt under
the existing privacy boundary. Search novelty counts remain excluded from model
packets, including the compact acquisition history. They are not a stopping rule,
utility score or evidence of relevance. Durable session records are unchanged.

Read's target and mode have explicit mechanical meaning:

| Request | Behavior |
| --- | --- |
| Exact material ID with `auto` | Reread that retained item locally, including highlights. |
| `local` | Inspect available retained material without external acquisition. |
| `full` | Reuse the latest retained full parent for the source or acquire full text if absent. Large parents yield bounded exact views, so one Read need not expose the whole body. |
| Candidate ID or observed URL with `auto` | Reuse an available full parent or acquire source text. |
| `D#` user-document ID | Read retained extracted text locally. No provider I/O and no external attempt. A large document returns bounded exact views, not the whole extraction. |
| `refresh` | Attempt another full-text acquisition while preserving earlier versions. |

An exact targeted-view ID preserves that view when reread, including when a focus
is supplied; focus does not silently replace an addressed view with a different
parent packet. A different range, parent Read, or Find requests other material.
Explicit character ranges identify exact slices of retained full text. Large
parents can provide focused exact views using the existing disposable
`SourceIndex`; repeated inspection is allowed. A refresh returning identical
material may reuse its immutable record. Different received versions preserve
their own material IDs and share the source identity allocated to the same URL.
Find merges overlapping hit regions only within the same immutable parent,
preserving all matched text while reducing duplicate reading context.
Read returns a mechanical receipt for the material actually returned: parent
length, exact ranges, returned characters and whether the entire parent body was
in that packet. Focused large-parent Reads also distinguish lexical hits from
dispersed fallback after a lexical miss. The receipt does not establish what
Research understood or whether the source contains an answer. Research can use
Find, another focus or an exact range to inspect more of a large parent.
Target URLs must be supplied by the user, returned through acquisition, or found
as explicit links in exposed material. These mechanics validate addressability
and custody, not semantic relevance.

A session may also hold user-provided text PDFs. They are durable source custody,
not Evidence until a role receives exact extracted text. The catalog lists each
document as metadata (`D1`, filename, media type, pages, characters,
`user_document`, `visual_analysis=false`, and the count of pages with no
extracted text). That metadata is navigation. It does not establish what the
document says, and it does not claim that omitted visual content says anything.
Read with `target=D1` and Find with `scope=["D1"]` use the retained extraction
locally. Unscoped Find may also inspect retained web material. Exact document
refs use `D1@start:end` over the deterministic extracted text, with real PDF
page indexes. Those refs are accepted as Evidence when actually supplied to Answer.
A document read spends no external attempt and does not consume the Exa Deep
bootstrap. The first eligible generic web Search still uses Deep. Document text
is authoritative for what the document states. It does not by itself verify an
outside-world claim. Web Search and known-URL Read remain available on the same
turn. No OCR, vision model, embedding, or semantic reranker is used.

Three distinctions remain separate:

- Acquired: exact actual material exists in retained custody.
- Exposed: exact material was supplied to a particular model call.
- Assessed: the model accounted for what it means; this is a semantic judgment,
  not something the exposure receipt proves.

Each reading packet prioritizes newly requested material. Research can keep
controlling premises and live contradictions in attention, shelve finished
material, and reactivate retained items through local Read/Find. If requested
material remains undelivered, the loop delivers it before accepting another
external route or an answer proposal. Shelving never deletes acquired Evidence.
Catalogs and indexes are transient navigation, not persisted product truth.

## Completion and resource limits

Initial Research decides when its whole-question investigation is ready for handoff.
Delegated Research decides when to return useful evidence or an honest limitation
for the requested need, judging whether further obtainable material justifies its
expected cost. The continuing Answer independently decides whether to seek more
evidence or complete a supported, partial or unable response from actual Evidence
or explicit user premises. Neither source counts nor budget consumption establishes
sufficiency.

Bounded Level-7 evaluation demonstrated useful aggregate and open-world synthesis
when suitable heterogeneous Evidence reached Answer. It showed restraint against
promoting small self-selected samples into population claims and appropriate use
of representative survey evidence. General open-world reliability remains unproved,
and source-access failures can prevent a fair semantic test. Lexical/community
discovery can identify a relevant URL that ordinary supported Read cannot
materialize; navigation does not become Evidence merely because the source is
relevant. The rejected scope-contract experiment remains historical evidence,
not active design.

Behavior-first Level-8 evaluation demonstrated bounded dynamic multi-component
research across seven completed families, including selective revision and
multi-turn scenario-premise handling. It did not establish arbitrary-length
continuity or general reliability.

`RunLimits` permits 40 physical requests across roles, 16 external acquisition
attempts, a 900-second hard whole-turn ceiling and 128,000 cumulative Answer source
characters. Each underlying model request is capped at 300 seconds and remaining
turn time. No terminal reserve, separate Answer clock or renewed per-tool allowance
exists. Research leaves one physical completion opportunity where feasible.
Local inspection spends no external acquisition attempt. Denied external routes
retain accurate receipts while local Research Read/Find and exact return selection
can continue under remaining shared limits. No semantic return-only mode is added.
Limits never supply support or establish nonexistence.

A5 exact selected passages are reconstructed from one immutable Research-exposed
range, with unique literal or whitespace-only location. Invalid entries yield safe
limitations independently. A6 skips repeated contained views only when one actually
supplied same-version item has exact custody and contains the whole view; it returns
navigation to that old alias without granting a new citation alias. Different
versions, partial overlaps and unions of views are not compacted. Explicit local
rereads remain charged. Initial selection may use the full attention limit; later
Research returns use normal 32,000-character packets or the existing whole-highlight
safety exception. Highlight offsets belong to acquired excerpts, never invented
page coordinates. Source/version/range provenance survives save and reopen.
Automatic unselected-source completion and fit/repacking loops are removed.

When Research reaches its operating bound, presentation discloses that fact even
if the independent Answer supports its conclusion. The bound does not mechanically
change Answer posture.
Safe run traces include monotonic elapsed time, body-free conversation and
retained-library size counts at turn start, Research catalog and active Evidence
character counts at model start, and model return and failure events. Incomplete
provider responses retain only fixed `content_filter` and
`max_output_tokens` classifications; missing, malformed or unknown reasons remain
generic. No raw provider reason or response payload enters the trace.

## Result, session, and presentation boundaries

`scryraven.results.CompletedAnswer` contains the public answer, posture, stop
reason, retained acquisitions, selected exact material, citations, citation-use
spans with optional durable support coordinates/hashes, and safe run trace. It
has no Analyst-shaped interpretation object.
Citation mechanics validate selected material against immutable acquisitions or
exact parent slices, reject unknown/unselected aliases and unresolved answer
links, and assign compact source numbers. Historical citation snapshots contain
the exact selected material, including versions and views. Identity validation is
not semantic entailment checking.

`ResearchSession` receives this native result from the ordinary Research loop.
Every `ask` starts fresh Research briefing and attention over the retained
acquisition library. Research receives the full prior question and answer text
plus citation provenance derived from immutable saved turns. The provenance
identifies the exact source and material each earlier answer cited, including
targeted views, without claiming that the earlier answer was correct. On the
first Research call of a follow-up, the exact actual material cited by the
immediately preceding completed answer is also exposed when it fits the existing
attention limit. A targeted web view is reconstructed from its retained
acquisition parent. A user-document view is reconstructed from that session's
stored extraction and must match it. No new acquisition or persistent memory is
created. No other historical material
is automatically exposed. Research may use, shelve or supplement this Evidence.
Answer continues to receive ordinary conversation without historical provenance
aliases, receives initial selected Evidence and may independently inspect any
legitimate retained material in that session. Prior user
questions may supply explicit premises as task context; prior assistant answers
are never Evidence. Only successful completed results commit session state;
failures leave the previous in-memory and durable snapshot unchanged. A partial
or unable completed answer can be retained honestly.

Durable `SessionTurn` records allow `analysis=None` for a source-first answer;
legacy Analyst-bearing turns retain their actual saved Analysis. No fake
Analysis is manufactured. Completed-turn commits remain revision-checked, with
neutral-turn validation alongside legacy validation. User documents live in an
additive SQLite schema-2 table and are not copied into the turn payload.
Run traces, briefings, indexes, observer records and provider state
are not session persistence fields. Reopening preserves actual Evidence and
historical answer provenance without making past generated text evidentiary.
All prior questions and answers are replayed verbatim for every Research call and
for Answer. Long-session performance remains unproved. There is no
context-compaction lifecycle in the ordinary product.

Ordinary `run`, `ResearchSession.ask`, the CLI (isolated, ephemeral and durable),
and Reading Room all invoke this same loop. There is no `--v2` selector.
Shared terminal/HTML presentation consumes `CompletedAnswer` and saved
`SessionTurn` directly, with no manufactured Analyst result. The only historical
Analysis code is decode-only schema/reference validation in `scryraven.historical`.
Historical judgments are excluded from new model packets. The stopped Investigator
executable harness and its Author adapter are retired to their preserved Git lineage.

New completed turns retain exact cited material snapshots without passage
localization. Historical citation uses with saved support coordinates and hashes
remain validated against their own snapshots; a corrupt material, range or hash
cannot reopen as trusted support. Historical records missing the additive support
field remain readable without payload rewriting.

Reading Room citation links identify their occurrence by the saved answer offset.
The Reader renders exact retained Evidence: that use's support first, expandable
surrounding context second, then the full saved material. The original source
or PDF action remains prominent. Source-overview inspection remains generic.
Reopening and inspection do not invoke models, fetch current publication text,
or generate support coordinates. New answers use the generic saved-material Reader;
historical localized turns retain their original occurrence-specific support.

The Reading Room and CLI disclose that no external sources were used for
completed source-free supported/partial answers. Presentation derives this from
posture and empty citations, which do not establish a user-premise basis; it
adds no persisted premise state.

The model transport keeps exact JSON content and explicit prompt-cache boundaries
for instructions, growing conversation history and stable Research turn context.
Research and Answer have separate cache families; mutable Evidence and corrections
remain outside those stable boundaries. Transport, Exa policy and the credential
broker remain mechanical infrastructure, with no semantic decision authority.

For Research, the stable packet prefix remains `conversation_context`,
`current_date`, `phase`, `question`, followed by its context cache breakpoint.
Volatile fields are `research_briefing`, `catalog`, `acquisition_history`,
`evidence`, `pending_delivery`, `budget`; other fields remain lossless in
stable order and `output_correction` comes last. Exact original content follows
identifying metadata. Prompt/schema changes naturally change cache identities;
there is no compatibility family or cache-derived semantic authority.

## Safe development observations

An optional observer receives normalized public events: bounded structured
decisions, field-specific rejected-decision diagnostics, selected requests and
acquisition outcomes, budget facts, exact acquired/exposed public material,
and exposure IDs, lengths and hashes. It never receives raw provider responses
or hidden reasoning. The small returned trace excludes source bodies; exact
bodies can be captured separately through the observer when an authorized
development observation needs them.

Reading Room's optional `--forensic-log PATH` writes the ordinary observer stream
to a distinct local JSONL file for development review. Its source-bearing events
can reconstruct acquired/exposed material, Research selections, response
rejections, timing and available model telemetry. Each line includes the session,
attempted turn, process run and event sequence. It receives no raw provider
payloads or hidden reasoning, and it feeds nothing back into the engine, session
or presentation. The ordinary DogfoodLog remains body-free. Startup rejects
aliases between both logs and the session database; later forensic write failure
disables only that observer sink.

`scripts/v2_campaign.py` remains a development-only observation caller (its name
identifies historical campaign files). It calls the ordinary session application
with explicit Luna/medium configuration and no engine override. It supplies only the frozen selected
question, never the rubric, expected identities, known URLs or a scripted route.
JSON lines go through the existing doorman's sanitized output boundary. The
doorman handles credentials and process plumbing only. Useful exact public
failures and controls may be captured as development candidates in ignored
`local-evals/` under `docs/operator/LOCAL_EVALUATION_CORPUS.md`; the runtime does
not depend on that corpus.
