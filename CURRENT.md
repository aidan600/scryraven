# ScryRaven Current Truth

Status: the local Reading Room browser product operates durable sessions, with
deterministic HTTP and real-browser acceptance of conversation, exact historical
Evidence, follow-ups, rename/delete, working/failure states and responsive layouts.
Browser-shell validation used zero live research/provider calls. Local durable
sessions retain their earlier ordinary three-turn BIPM/BIPM/NASA demonstration
across separate processes, followed by exact provider-free historical inspection.
Compact citations and inspection of
selected Evidence retain their earlier product demonstrations. The semantic product
path remains Research -> Analyst -> Author. Explicit prompt caching reduced effective
input units by 23.62% on the bounded three-turn retained-context workload.
Repository: aidan600/scryraven
Preferred local checkout: C:\Users\aidan\ScryRaven

## Active product path

Exactly Research, Analyst, and Author retain semantic authority. Research directs
public-web acquisition toward the question; Analyst interprets support,
qualifications, conflicts, and unresolved gaps; Author writes from Analyst findings
and supplied supporting material. FAST and SMART remain internal role labels, both
configured by default as gpt-5.6-luna / medium. There is no user-facing
Fast/Balanced/Deep mode, generalized model/provider routing, or alternate-provider
fallback.

The ordinary CLI uses one fixed acquisition policy: Exa Search with query-guided
extractive highlights, Research selection of actual material, Analyst
interpretation, and Author writing from supported findings and supporting context.
Search metadata is navigation. A concrete missing-context need can trigger Exa
Contents full text with full verbosity and a fresh crawl. Provider-returned text
may establish a claim when the received text supplies the material context; generated
summaries and answers are excluded. Source selection and sufficiency remain semantic
judgments, not transport verdicts.

Successful full-text acquisition is retained once per exact URL for the run or
session. Bodies up to 32,000 characters are exposed directly; larger
bodies use exact extracted
packets up to 32,000 characters, with one optional 48,000-character expansion for a
concrete gap. Packet bounds describe received extraction, not original-document
pages or locations. Same-URL material versions share one source identity.

Each question gets fresh existing bounds: up to three Analyst assessments, up to six
navigation actions before each assessment, and an earned second two-call search round
for a specific unresolved same-need gap. Those limits are operational ceilings, not
semantic sufficiency rules.

## Session follow-ups

`ResearchSession.ask(question)` uses the same production path as isolated
`run(question)`. The ordinary CLI adds `--session`: answer the initial question,
then accept follow-ups until blank input or EOF. The CLI's `--html` remains a
single-answer artifact; the Reading Room renders complete durable conversations.
Ordinary single-answer HTML and each Result's citation/inspection data remain intact.
The constructor and `--session` remain ephemeral; the durable API and CLI options
below opt into local persistence.

Completed questions/answers supply conversation context only. Prior Analyst output,
posture and limitations supply separate, non-evidentiary semantic history. Each
turn starts with fresh Research orientation, no inherited Analyst verdict, and no
automatically selected evidence. Research can inspect actual retained highlights or
use `read` to inspect a retained full parent locally, select current relevant
material, and acquire more when needed. Only current selected Evidence supports
Analyst findings; only current coverage findings support Author claims.

Immutable acquisitions, including full parents of large-source packets, survive
successful turns. Canonical source and material IDs remain stable; new acquisitions
receive noncolliding IDs, with same-URL versions grouped under their original source.
Numeric citations remain answer-local. Retained parents can yield different exact
packets for a new question without provider I/O; packet expansion and research
limits apply afresh per turn. Failed turns discard staged acquisitions and semantic
history. Valid partial/unable Results count as completed turns.

Safe session trace facts identify the turn, entering retained-source count, reused
material, source identity allocation, and new acquisition count. Conversation history
is not copied into diagnostics. Deterministic fake-model/provider tests exercise
reuse, fresh acquisition, reference rejection, large-source reinspection, failure
isolation, and the ordinary multi-turn CLI. They prove mechanics, not live model
relevance or fidelity. The ordinary live session demonstrated retained-highlight
reuse; retained full-parent reinspection and different large-source packets remain
verified offline only.

The bounded live observation at `dfca5658049cd1f492fadcae70b972169ddcad15`
answered the four 2022 BIPM prefix additions, then the elliptical question "Which two
of those are for factors smaller than one?", then NASA's day length on Mars. All
three turns reached supported results with fresh Research, Analyst and Author calls.
Search/Contents/model-call counts were 1/0/5, 0/0/4 and 1/0/5. Turn 1 retained BIPM
sources E1 and E2; turn 2 selected unchanged E1 without provider acquisition; turn 3
added NASA E3, selected only E3, and preserved E1/E2. Current findings and citations
resolved to actual selected source material. Input audits kept prior answers in
non-evidentiary conversation context, with no source IDs, and Author received the
current Analyst coverage. No repair or second live session was required.

This is one successful ordinary session, not general conversational reliability.
All selected live material was provider highlights. No independent source checks
were performed. The sanitized validation record is in
`docs/operator/IN_MEMORY_FOLLOWUP_VALIDATION.md`; exact live artifacts stay external
and a useful sanitized clean control is preserved only in the ignored local corpus.

## Local durable sessions

`ResearchSession.create/open` use the application-level `SessionStore` boundary,
with one standard-library SQLite implementation. The default database is per-user
application data outside the checkout (`%LOCALAPPDATA%\ScryRaven\sessions.sqlite3`
on Windows). Callers and tests can inject an explicit path. The CLI exposes
`--create-session`, `--resume ID`, `--list-sessions` and `--database PATH`.
Opening without a question reads the saved transcript without model/provider I/O.

Schema version 1 stores session identity, UTC creation/update times, display title,
revision, and a complete product-state snapshot. Each completed turn preserves its
question, answer, Analysis, posture, stop reason, selected Evidence, Citation
records and CitationUse character spans. Actual acquisitions retain every Evidence
field, including full source content, IDs and canonical-source relationships.
Historical exact views retain their IDs, parent relationships, ranges and content;
they are audit/presentation snapshots, never automatically current Evidence.
Existing CLI/HTML renderers can render saved `SessionTurn` objects directly.

All completed-turn state commits in one transaction with a revision check. Failed
model/citation turns and failed database commits leave the prior durable and
in-memory state intact. Stale writers receive `session_conflict`; there is no
semantic merge. Invalid reconstructed records and incompatible schema versions
fail safely. No credentials, raw responses, corrections, diagnostic traces, prompt
cache keys or provider cache state enter the session schema.

Offline tests demonstrate process-object replacement, restored conversation and
semantic history, retained-evidence reuse, stable/noncolliding IDs including
same-URL versions, exact historical citation numbering and material, fresh large
views from a persisted full parent without refetch, failure rollback and conflicts.
Disposable lexical indexes are rebuilt, not persisted. The ordinary isolated and
ephemeral paths and PR #635 fake-transport cache regressions remain covered.

The bounded ordinary observation at `286c5721763ff49354fc811ad04dbf2c7737aa8d`
used three separate processes for the BIPM prefix question, the elliptical
below-one follow-up, and NASA's Mars day length. Search/Contents/model-call counts
were 1/0/5, 0/0/4 and 1/0/5. Turn 2 reused unchanged persisted BIPM E1 while E1/E2
remained intact. Turn 3 acquired and cited only new NASA E3/E4 while preserving
E1/E2. Each turn had fresh Research, Analyst and Author decisions. A fourth process
restored the entire session and all old answers, selected material, citations,
CitationUse spans and rendered HTML exactly, with zero model/provider calls.

One logical validation attempt and three ask calls succeeded; no repair or rerun
was used. All live material was provider highlights. This proves the bounded
restart path, not general conversational reliability or live full-parent reuse.
The record is `docs/operator/PERSISTENT_SESSION_VALIDATION.md`. The temporary
database and exact packet remain external under `C:\tmp`; a sanitized development
clean-control candidate, without the database, is preserved in ignored local-evals.

## Local browser Reading Room

`python -m scryraven.reading_room` launches the Flask/Werkzeug local HTTP shell at
`http://127.0.0.1:7331`. `--database PATH` uses a chosen SQLiteSessionStore location;
omitting it uses the existing per-user default. `--port` changes the local port.
The launch path binds only to loopback, without a debugger or reloader. It is a
local single-user server, not a hosted deployment. No frontend build, background
jobs, queue, WebSockets, alternate research engine or browser persistence exists.

Browser questions use ordinary `ResearchSession.create/open(...).ask(question)`;
completed turns commit only through SessionStore. New research navigation creates
no empty session. The first submission creates one, and a failed first turn removes
only its still-empty record with a revision guard. Prior completed state survives
failures and stale writers are not merged. Partial/unable results render as
completed answers with restrained limitation context. While an HTTP request runs,
the browser acknowledges work without claiming stages, progress percentages or
streaming results. One-use signed forms prevent duplicate submissions; a restart
expires open forms, which can be reloaded without losing saved history.

SessionStore now owns metadata-only rename and permanent delete. Rename leaves the
completed-turn revision and serialized research payload unchanged; a concurrent
ask preserves the latest title. Delete checks the displayed completed-turn revision
and requires a confirmation form. Stale/deleted pages return safely to history or
retain an unsaved question in the new-research view. Neither operation calls a model.

The shared deterministic presentation module renders safe Markdown and source
material for both standalone HTML and the Reading Room. Every browser citation
destination contains its historical turn index. Its inspector reads only that
saved SessionTurn's Citation.materials, never the session's later acquisition
corpus. Multiple selected materials remain separate; all three acquisition types
have human-readable labels and long material is available in full. Ordinary
bracketed numbers and answer-authored local links cannot impersonate citations.

The answer uses a bounded reading measure, a quiet session sidebar and a multiline
composer. Evidence docks on wide screens, overlays laptop layouts, and fills a
narrow screen. The history drawer, citation interaction, focus return, source
overview, full-material expansion, rename, delete confirmation and reduced-motion
behavior use ordinary HTML/CSS with small JavaScript enhancements. Native forms and
source disclosures remain available without JavaScript.

HTTP protection includes trusted loopback hostnames, Origin checks, signed
action-bound forms, a restrictive CSP, frame denial, bounded errors, and no remote
assets. Local same-origin referrers preserve native form Origin headers; external
publication links use `noopener noreferrer`. Questions, titles, Markdown and saved
Evidence remain untrusted display data. No provider errors or request payloads are
exposed as browser diagnostics.

Offline regression and browser acceptance use only synthetic material and explicit
external disposable databases. The browser pass exercised 1440px desktop, 1920px
docked evidence, and 390px narrow layouts, including real form submission through
the application, failure/limited results, historical [1] collisions, later same-URL
material, rename/delete and process restart/reopen. This demonstrates presentation
and session mechanics, not new evidence of live research quality. Arbitrary long
history performance and simultaneous multi-user operation remain unproved.

## OpenAI transport economics

The GPT-5.6 Responses transport uses explicit-only prompt caching with a 30-minute
TTL. Unchanged instructions and Structured Outputs contracts define deterministic
cache families. Complete local material is serialized as one JSON object across
content blocks: growing history first, stable navigation context next, then current
candidates, Evidence, decisions and corrections. Up to four explicit breakpoints
preserve instruction, history and navigation prefixes; volatile tails incur ordinary
input charges instead of cache writes. No text is summarized, compressed or omitted.
Optional in-process usage observations expose token classes, family and breakpoint
labels without prompts or provider payloads. Missing counters remain unknown.

One ordinary three-turn session on the same BIPM/BIPM/NASA questions used 40,621 input
tokens: 13,409 cache reads, 7,040 cache writes and 20,172 ordinary uncached tokens.
At relative rates 1.00 ordinary / 1.25 write / 0.10 read, effective input units were
30,312.9 versus the historical 39,685.6, a 23.62% reduction. There were 14 model calls,
two Exa Search calls and zero Contents calls, matching the historical call counts.
Turn 2 reused unchanged BIPM E1 without acquisition; turn 3 acquired and cited NASA
E3 while preserving E1/E2. All three answers were supported by selected material.
No repair or second session was used. This bounded observation is not a guarantee
for other workloads or cache routing; source selections can vary between runs.

Model/reasoning defaults, semantic prompts, provider/ranking policy and evidence
custody are unchanged. `store=False` remains in force, with no server-side
conversation state. The token formula belongs to validation reporting, not runtime
pricing policy. See `docs/operator/PROMPT_CACHE_ECONOMY_VALIDATION.md` for the tested
revision, exact workload, token classes, source identities and limitations.

## Citations and selected-Evidence inspection

Author still emits validated evidence aliases. Deterministic mechanics reject
malformed, unknown, and unselected aliases, and supported answers still require
valid citation use. After validation, citations receive compact numbers in order of
first use of their canonical source; every later use of that source reuses its
number. Full publication titles no longer interrupt answer prose.

The ordinary CLI prints the numeric answer followed by one compact source list.
`--html PATH` writes a self-contained local view with compact citation links. Each
source disclosure shows the source title, its original public URL, and the exact
selected Evidence items grouped under that canonical source. A missing title falls
back only to clearly labeled URL metadata (a PDF filename or hostname), never to a
generated title or source-text guess.

The disclosure says that it is material ScryRaven used from the source. It is
source-level support context, not a sentence-level proof map. Extracted-text offsets
are never shown as PDF pages, sections, byte offsets, or precise proof passages.
Question, model, and source text are escaped; raw model HTML is disabled; the view
uses fixed local assets protected by a content security policy and loads no remote
resources. Disclosures remain usable without JavaScript.

## Demonstrated product frontier

The fixed Exa path has ordinary-product evidence for Bowling, IPCC Chapter 2, NIST
FIPS 197, and Saturn. Bowling, IPCC, and NIST reached supported answers with the
material qualifications preserved. Saturn remained partial: the NASA/JPL, MPC, and
IAU chronology supported the substantive answer but did not establish the requested
September snapshot. That limitation remains explicit rather than being upgraded into
certainty.

Ordinary presentation controls demonstrated the retained behavior on a short BIPM
SI-prefix answer and on a complex SLAC workplace-AI-policy answer. They showed
stable numeric references, original-publication links, grouped exact selected
material, and source-safe local rendering. The complex SLAC answer did not establish
a general improvement in dense-policy readability or semantic paraphrase fidelity.
Closure cleanup leaves the already observed citation and disclosure mechanics
unchanged, so it does not require another live PRODUCT run.

## Current boundaries and limitations

Citation identity validation is not semantic entailment or fact checking. Analyst
and Author paraphrase remains probabilistic: modal force, scope, qualifications, or
other meaning can still mutate, particularly in dense policy material. Research can
also omit relevant evidence before Analyst sees it. Displayed selected Evidence is
honest, inspectable source-level context, not a guarantee that one displayed span
proves every nearby sentence.

No fourth semantic owner, intermediary semantic representation, semantic verifier or
Reviewer, or post-Author remediation loop is present.
Persistence is local and single-user, without encryption at rest, cloud sync,
accounts/authentication, uploads, a desktop wrapper, history compression or
context eviction. The complete snapshot is rewritten on each commit; arbitrary
long-session performance is unproved. Retained acquisitions belong to their session,
not a shared retrieval service. Prompt caching remains an independent transport
optimization; reopening does not require a provider cache hit.
There is no vector database, crawler, general RAG, calculation system, hosted
service or frontend build stack.

Offline fixtures exercise deterministic mechanics and rendering safety; they do not
prove model judgment or universal provider reliability. The existing broker remains
limited to credentials and process plumbing, not product semantics.
