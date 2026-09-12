# ScryRaven

ScryRaven researches public-web factual questions with related answer needs and
writes one cited answer from source material it receives and reads. Research finds
promising sources with Exa Search and selects useful extractive highlights for
Analyst. Missing context can trigger acquisition of fuller source text. Analyst
interprets support, qualifications and gaps; Author writes from its findings,
source references and supporting material.

See `CURRENT.md` for implementation, demonstrations and limits. `PRODUCT.md` owns
approved product intent.

## Run

Use Python 3.10 or later from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m scryraven "What is the maximum allowed weight of a ten-pin bowling ball?"
```

## Reading Room

Launch the local browser product from the same environment:

```powershell
python -m scryraven.reading_room
```

Open [http://127.0.0.1:7331](http://127.0.0.1:7331) in your browser. Keep the terminal
running; Ctrl+C stops the server. It binds only to `127.0.0.1`. If the port is busy,
choose another with `--port 7339`. There is no remote bind option.

The Reading Room uses the same default per-user database as the saved-session CLI.
To keep your durable research in a chosen location, pass the path at launch:

```powershell
python -m scryraven.reading_room --database "D:\My Research\sessions.sqlite3"
```

Missing parent directories are created. Use the same path when restarting or when
opening these sessions from the CLI. The database holds your conversation and saved
source material; browser storage holds none of it.

Choose **New research**, ask a question, and use the composer for follow-ups. Submit
with the arrow or Ctrl+Enter / Command+Enter; plain Enter adds a line. Research runs
in the HTTP request, with an indeterminate working state and no token streaming.
Completed answers, including limited results, are saved. A failed attempt keeps
the question available to edit and leaves completed conversation intact.

Click **[1]** to inspect the exact material saved with that historical answer, or
**Sources** for its publication overview. Evidence opens beside the answer on a
wide screen, as an overlay on a laptop, and as a full sheet on a narrow screen.
Long material can be expanded in full. **Open original publication** opens a new
tab; the saved selections remain available when the original site changes.

Each session's **…** menu offers **Rename** and **Delete**. Rename preserves all
research and requires no model call. Delete requires confirmation and permanently
removes that session and its saved material. History, reopening, and both actions
require no provider calls. Starting new questions uses the same provider environment
and `ResearchSession` path as the CLI. An open form expires when the server restarts;
reload the page before submitting it again.

Flask supplies routing, escaping templates and the local HTTP server. All assets
are local; no frontend framework or build step is needed. This is a local,
single-user application, not a hosted service. JavaScript enhances the evidence
sheet, working state and keyboard interactions; ordinary history, reading and
forms also work without it, with expandable source disclosures.

## Single-answer views and follow-ups

Add `--html C:\tmp\answer.html` to save a self-contained local answer view
(the destination directory must exist). Open that file in a browser. The view
shows the question and answer, with compact numbered citations. Clicking a citation
opens the source's selected material; each source also links to the original
publication. Source disclosures can be opened directly without JavaScript.
No server, account, hosted deployment or saved session is required.

For follow-ups in the same process:

```powershell
python -m scryraven "According to the BIPM SI Brochure, what is the largest SI prefix?" --session
```

After each answer, enter the next question at the prompt. Blank input or EOF ends
the session. Every question gets fresh Research, Analyst and Author decisions and
fresh research limits. Research can inspect actual retained sources without another
provider call, or acquire additional material. Previous answers help interpret
follow-up intent but cannot support facts or citations. This mode saves nothing
between processes. `--html` remains an isolated single-answer option.

The equivalent sequential Python API accepts the same optional model, search,
fetch and limits arguments as `run`:

```python
from scryraven.session import ResearchSession

session = ResearchSession()
first = session.ask("According to the BIPM SI Brochure, what is the largest SI prefix?")
followup = session.ask("And what is the smallest one?")
```

`session.turns` exposes completed questions, answers and copied Analyst history;
`session.acquisitions` exposes immutable actual Evidence, including full parents;
`session.source_ids` exposes canonical identities. Each Result's `evidence` is the
acquisition corpus at that turn, while `selected_evidence` and citations describe
only its current supporting material. Failed turns leave committed state intact;
valid partial/unable answers are completed turns. `run(question)` remains isolated.

## Saved local sessions

Create a durable session, record the printed session ID, and reopen it later:

```powershell
python -m scryraven "According to the BIPM, what SI prefixes were added in 2022?" --create-session
python -m scryraven --list-sessions
python -m scryraven "Which two of those are for factors smaller than one?" --resume SESSION_ID
python -m scryraven --resume SESSION_ID
```

Create/resume with a question accepts interactive follow-ups until blank input or
EOF. Resume without a question prints the historical transcript and source list,
without calling models or providers. `--html` does not accompany session options.
Use `--database C:\tmp\my-session-test\sessions.sqlite3` with persistent options
to choose an explicit database; missing parent directories are created.

The default is `%LOCALAPPDATA%\ScryRaven\sessions.sqlite3` on Windows, outside the
repository. macOS uses `~/Library/Application Support/ScryRaven/sessions.sqlite3`;
other platforms use `$XDG_DATA_HOME/scryraven/sessions.sqlite3` or
`~/.local/share/scryraven/sessions.sqlite3`. Only local single-user storage is
provided. This database contains questions, answers and source text in plaintext;
there is no encryption at rest, cloud sync or authentication. Keep it out of Git.
Tests and validation use explicit external temporary paths, not your default store.

Persistence belongs to the application API, independently of the CLI:

```python
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.presentation import render_html

store = SQLiteSessionStore()  # Or SQLiteSessionStore(an_explicit_test_path).
session = ResearchSession.create(store=store)
first = session.ask("According to the BIPM, what SI prefixes were added in 2022?")
session_id = session.session_id
# A later process, with no old session or provider cache required:
reopened = ResearchSession.open(session_id, store=SQLiteSessionStore())
metadata = store.list_sessions()  # ID, times, title, revision (completed-turn count).
old_turn = reopened.turns[0]      # No model or provider call.
html = render_html(old_turn.question, old_turn)
followup = reopened.ask("Which two of those are for factors smaller than one?")
```

`create/open` accept the ordinary constructor's model/search/fetch/limits options
for future questions. An optional `title` on `create` sets the display label;
otherwise the first committed question supplies it without a model call.
`SessionStore` is a small create/load/list/commit interface with one SQLite backend.

Each saved `SessionTurn` exposes question, answer, Analysis, posture, stop reason,
`selected_evidence`, `citations` and `citation_uses`. Citation records preserve
answer-local numbers, canonical source IDs, titles, URLs and exact selected material;
CitationUse records preserve the numeric markers' character spans. Historical
packets are saved exactly, including targeted-view IDs, parents, bounds and content.
They are not regenerated for display or automatically reused as current support.

All actual acquisitions, including complete large-source parents, retain their
original IDs and source relationships across restart. Future Research may select
them or derive new exact views locally. Prior answers remain conversation context;
Analysis remains semantic history. Each question still receives fresh Research,
Analyst and Author decisions. Storage contains no traces, credentials, raw model
responses, corrections, lexical indexes or cache state. Prompt caching is unchanged
and cache expiration does not prevent reopening.

Schema version 1 stores metadata and a validated complete session snapshot in one
SQLite row. Each completed turn atomically updates the snapshot and revision. A
failed turn or failed commit preserves the previous durable and in-memory state.
`SessionStoreError` reports a fixed code; `SessionConflictError` reports
`session_conflict` if another handle has advanced the session. Reopen to inspect
the newer state before asking again; histories are never merged automatically.
Incompatible schema versions and corrupt product records fail safely. Complete
snapshots are rewritten on commit; very long-session performance is unproved.

The bounded production restart observation and its limits are recorded in
[`PERSISTENT_SESSION_VALIDATION.md`](docs/operator/PERSISTENT_SESSION_VALIDATION.md).

## Model configuration

The process needs `OPENAI_API_KEY` and `EXA_API_KEY`. The product does not load
`.env`. Optional independent role configuration:

| Variable | Default |
| --- | --- |
| `SCRYRAVEN_FAST_MODEL` | `gpt-5.6-luna` (Research and Author) |
| `SCRYRAVEN_FAST_REASONING` | `medium` |
| `SCRYRAVEN_SMART_MODEL` | `gpt-5.6-luna` (Analyst) |
| `SCRYRAVEN_SMART_REASONING` | `medium` |

An empty reasoning value omits that API option. One OpenAI Responses transport
uses structured output and Pydantic parsing. No model has built-in web tools.

## Acquisition and evidence

The fixed path is Exa Search (`auto`, six results, query-guided highlights up to
4,000 characters per result), then Exa Contents text only when context is missing
(`verbosity: full`, `maxAgeHours: 0`). Generated summaries and answers are excluded.
Search metadata remains navigation. Actual highlights may support only meaning
established by their text; extractive does not mean complete, contiguous or free
of extraction artifacts. Authority, applicability and sufficiency are judgments.

Research selects highlights in its existing navigation call, without another
relevance call or full-text acquisition. Fuller context is appropriate for missing
definitions, conditions, captions, chronology, connected passages, version context,
or broader page/discussion questions. `context_needed` records the concrete gap.
An older governing source can remain applicable; unrequested editions and
hypothetical exceptions do not automatically expand a narrow question.

Successful full-text acquisitions are immutable and retained by the run/session.
Bodies up to 32,000 characters are exposed directly. Larger sources produce one
mechanical packet of exact slices up to 32,000 characters, using structure, lexical
matches and recoverable excerpt phrases. One optional expansion up to 48,000
characters addresses a concrete gap. These are provisional economics choices,
not semantic sufficiency thresholds. A later turn can inspect a new exact packet
from the same retained full parent without fetching it again, including after a
durable session reopens. There is no shared document store or history compression.

Different material versions at the same exact URL remain immutable and share
source identity. Views carry exact parent bounds; highlights never acquire guessed
offsets. Multiple versions/views are not independent corroboration. Analyst and
Author receive selected context grouped by source. Analyst owns preservation of
significant quantities, conditions, time comparisons and epistemic language through
paraphrase; Author preserves that meaning in the answer. Reference validation does
not decide meaning or mechanically check paraphrase.
Citations receive stable numbers in order of first validated use, reusing the same
number for the same canonical source. Source titles appear once in the CLI source
list and in the local view's disclosures, rather than repeatedly in answer prose.
When source-title metadata is absent, a PDF's filename is labeled as a publication
file; other sources use their hostname. No title is generated from evidence text.
The view groups exact `result.selected_evidence` items under each cited source;
it neither regenerates excerpts nor presents unselected material. This is
source-level support, not a claim-to-sentence proof map. Extracted-text slice
offsets are not original PDF page coordinates; no page or section anchors are
invented. Original publication links remain separate from the selected material.
The renderer escapes source/question text and disables raw model HTML. A small
Markdown parser handles answer structure; fixed local CSS and JavaScript are
restricted by a content security policy. The view loads no remote resources.

The existing provisional loop permits three Analyst assessments, each preceded by
up to six navigation actions. Each semantic need allows two Search calls initially.
Actual evidence assessed by Analyst and a specific unresolved same-need gap can
earn one further round of two calls; there is no third round. Unused initial
allowance expires. Assessment of new evidence in round two closes remaining search
allowance for that need. Existing candidate reads survive. Failures spend search
allowance; empty or omitted material cannot earn a return. These are ceilings,
not targets. Need identity remains a semantic judgment.

Research can nominate useful explicit links from acquired material. Mechanics
validate occurrence and URL syntax, including escaped Markdown punctuation.
Invalid optional links are rejected individually. There is no automatic crawling;
the linked source must be acquired before it supports findings.

## Observations and checks

Answers and a compact source list appear on stdout. `--trace` adds compact diagnostics on stderr: model
roles, Research choices, source identities/sizes, acquisitions, packet bounds,
selected material, Analyst findings/gaps and citation resolution. Per-stage
body characters include repeated submissions; they are not tokens or dollars.
Raw payloads, credentials and hidden reasoning are excluded.
`--trace-evidence` also exposes exact selected supporting material, citations and provenance;
unseen full parents remain out of the trace. Use public questions for observations.
Session diagnostics also identify the turn, retained source count, reused material,
new acquisitions and source identity reuse/allocation. Prior conversation is not
added as a diagnostic payload. Numeric source references start afresh in each answer.

Execution errors exit 1 with a safe stage/code. Supported, partial and unable
postures exit 0. An honest limit is not proof of nonexistence.

Agents must use the existing doorman for credentialed commands and must not read
`.env` or keys. An operator may configure `.env` using `.env.example`. For an
authorized observation use fresh external output filenames:

```powershell
New-Item -ItemType Directory -Force C:\tmp\scryraven-observation | Out-Null
python scripts/run_brokered_command_once.py --repo-root C:\Users\aidan\ScryRaven --repo-env --stdout C:\tmp\scryraven-observation\answer.txt --stderr C:\tmp\scryraven-observation\trace.txt --status C:\tmp\scryraven-observation\status.json --timeout-seconds 1200 --target-current-python -- -m scryraven "What is the maximum allowed weight of a ten-pin bowling ball?" --trace
```

The doorman owns only secret custody and process plumbing; the product does not
import it. Keep observation packets outside the repository.
The broker closes stdin, so the interactive CLI stops after the initial answer
under it. An authorized automated multi-turn observation can call the public
`ResearchSession.ask` API sequentially from a brokered caller.

Private-child configuration failures retain status `private_child_configuration_failed`.
The status file's `safe_error_code` can identify `private_session_missing`,
`environment_file_unavailable`, `invalid_environment_assignment`,
`invalid_environment_name`, or `invalid_environment_value`; unrecognized failures
keep the generic code. These categories expose no parser line numbers, variable
names, values, or raw exceptions. Parsing and target execution are unchanged.

```powershell
python -m pytest -q
python -m ruff check .
pre-commit run --all-files
```

Offline tests inject external transports into the ordinary application and do not
prove model judgment. CI runs offline without provider credentials/calls.
Scheduling, generalized routing/recovery, vector databases, uploads, desktop
wrappers, semantic compression and calculation remain absent. Old providers are not
dormant fallbacks.
