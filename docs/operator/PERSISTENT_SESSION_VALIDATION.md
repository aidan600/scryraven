# Durable local session PRODUCT validation

Outcome: **met** in the primary attempt on 2026-09-11 (Pacific time). One logical
session completed three public questions in three separate Python processes.
A fourth process inspected the saved history without external calls. Live runtime:
`286c5721763ff49354fc811ad04dbf2c7737aa8d`. Subsequent changes are documentation only.

## Baseline and execution

Local main was clean and matched current remote main at
`1629271302ac19157786623b80a328a7993a488c`, containing PR #635. Work used the ordinary
checkout on `codex/persistent-research-sessions-01`.

The existing credential broker launched each live caller separately. Each called
the public `ResearchSession.create/open/ask` API with production OpenAI and Exa
transports, unchanged gpt-5.6-luna / medium defaults and the existing prompt-cache
strategy. Observers counted calls and compared public state/inputs; they did not
seed evidence, choose Research actions or alter prompts/requests. An offline
scripted rehearsal checked only the observer and used a different temporary DB.

The first sandbox broker invocation could not read its private environment and
launched no target. The authorized execution identity then ran the broker.
No credentials/environment contents were read by the controlling agent, and no
machine permissions changed. This consumed no extra live ask call or attempt.

| Turn / process | Exact question | Search | Contents | Research / Analyst / Author |
| --- | --- | ---: | ---: | --- |
| 1 / 44916 | According to the BIPM, what four SI prefixes were added in 2022, and what power-of-ten factor and symbol does each represent? | 1 | 0 | 3 / 1 / 1 |
| 2 / 22072 | Which two of those are for factors smaller than one? | 0 | 0 | 2 / 1 / 1 |
| 3 / 42808 | According to NASA, how long is a day on Mars? | 1 | 0 | 3 / 1 / 1 |

Session ID: `043af9dee3824a3d966dc8064a3fee4c`. Processes A and B had exited before
their successors started. Each successor loaded exact prior conversation, Analysis,
posture, stop reason and actual acquisition material from the SQLite database.
All three answers were supported. Total: 14 model calls, two Search calls, zero
Contents calls. Independent source checks: zero. One of at most two allowed logical
attempts was used, with three of at most six allowed ask calls. No repair, retry or
reassurance rerun occurred after success.

## Answers, identity and historical provenance

| Turn | Result | Selected material | Canonical corpus after | Answer-local references |
| --- | --- | --- | --- | --- |
| 1 | ronna R 10^27; ronto r 10^-27; quetta Q 10^30; quecto q 10^-30 | E1, E2 | E1, E2 | E1 = 1; E2 = 2 |
| 2 | ronto and quecto are the factors below one | unchanged persisted E1 | E1, E2 | E1 = 1 |
| 3 | a sol is about 24.6 Earth hours; mean solar day 24 h 39 min 35.244 s | new E3, E4 | E1, E2, E3, E4 | E3 = 1; E4 = 2 |

Actual acquired sources, all `provider_highlights`:

- E1: [BIPM Resolution 3](https://www.bipm.org/en/cgpm-2022/resolution-3), 1,726 characters.
- E2: [BIPM SI prefixes](https://www.bipm.org/en/measurement-units/si-prefixes), 1,429 characters.
- E3: [NASA Mars facts](https://science.nasa.gov/mars/facts/), 995 characters.
- E4: [NASA GISS Mars24 technical notes](https://www.giss.nasa.gov/tools/mars24/help/notes.html), 697 characters.

These links identify received material, not independent checks. The BIPM tables
supplied the four names, symbols and factors. NASA's selected material supplied the
rounded duration and the more precise mean solar-day value. Review against selected
material and final Analyst coverage identified no material answer/provenance error.

Research and Analyst received exact restored conversation and separate semantic
history; Author received conversation and current coverage. Every conversation entry
contained only question/answer fields. The first Analyst assessment of each turn
had no inherited current-turn verdict. Current Author material matched actual
selected Evidence; prior answers were not promoted into it.

Inspection process 44044 opened the database with model/search/fetch callbacks that
fail if called. The complete state matched the last saved snapshot. All three
historical turns matched their original answers, Analysis, selected Evidence,
Citation records and CitationUse spans. Re-rendered HTML matched the original
rendered text exactly. No historical packet was regenerated. The inspection used
zero model/provider calls.

## Persistence and safety proof

`SessionStore` is an application interface with one standard-library SQLite backend.
The default Windows path is `%LOCALAPPDATA%\ScryRaven\sessions.sqlite3`, outside
the checkout. This observation used only the explicit external packet database.
Version 1 stores opaque session ID, UTC timestamps, display title and revision,
plus the complete conversation/semantic history, acquired corpus and historical
presentation snapshot. No traces, credentials, raw provider payloads, hidden
reasoning, model corrections, cache keys/state or lexical indexes are stored.

All Evidence fields survive: id, source_id, URL, title, exact content, acquisition,
parent_id, start_char and end_char. Per-turn Citation material references resolve
only against that turn's exact saved selected Evidence. CitationUse retains number,
start and end. Analysis retains decision, coverage/findings/support references,
active references, explanation and next-need fields.

One SQLite transaction advances the snapshot and revision; memory advances only
after commit succeeds. Offline tests inject a SQLite COMMIT failure after the row
UPDATE and verify rollback of both durable state and in-memory state. Separate
handles demonstrate that a stale writer receives `session_conflict`, preserving
the newer history and discarding its own attempted state. Failed model, provider
and citation attempts leave prior committed state intact. Corrupt Evidence,
Analysis, citations, ranges/identities, metadata and incompatible schema versions
fail safely without being repaired or passed to Research.

Deterministic tests also cover same-URL versions and fresh noncolliding identities,
multiple/repeated answer-local citations, partial/unable results, ephemeral
`ResearchSession()` and isolated `run()`. Synthetic large-source tests prove exact
historical view retention and different new views from a saved full parent with no
refetch. Large-source restart reuse remains offline evidence only.

Verification passed: `python -m pytest -q` (295 tests), `python -m ruff check .`,
and `pre-commit run --all-files` using the repository Python and external temp/cache
roots. The stale pre-commit cache was replaced with a fresh external tool cache;
no machine-wide configuration or permission changes were made. PR #635 fake
transport tests still verify cache layout and `store=False`. Research prompts,
models/reasoning, retrieval/ranking, source mechanics and transports are unchanged.

## Custody and limits

The exact sanitized packet and temporary database remain at
`C:\tmp\scryraven-persistent-session-live-01\`. A sanitized clean-control candidate
is preserved under ignored `local-evals/` with development/candidate status. The
corpus contains no database. Neither the corpus nor validation DB is published.
No ScryRaven session DB was created in the repository or real user-data store.
An unrelated ignored `proplex.db`, predating this work, was left untouched.

Persistence is local, single-user and plaintext: no encryption at rest, cloud
sync, authentication, uploads, vector database or web/desktop shell. Complete
snapshots are rewritten per commit; arbitrary long-session performance is unproved.
Cache hits after restart are opportunistic and not required for correctness.
This one control does not establish universal semantic/provider reliability.
