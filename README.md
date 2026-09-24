# ScryRaven

ScryRaven researches public-web questions and writes cited answers from actual
source material. One Research semantic loop owns interpretation, evolving needs,
acquisition direction and stopping. Mechanical Search / Read / Find execute its
choices. A fresh Evidence-first Answer independently determines what the selected
sources justify. Generated Research state and prior answers are never Evidence.
The CLI, sessions and Reading Room use this same ordinary path.

See `CURRENT.md` for implementation, demonstrations and limits. `PRODUCT.md` owns
approved product intent.

## Run

Use Python 3.10 or later from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Model execution requires `OPENAI_API_KEY`, and ordinary web Search requires
`EXA_API_KEY` in the process environment. `SERPER_API_KEY` is required only when
Research invokes alternate lexical/community/current discovery;
`LINKUP_API_KEY` is required only when external known-URL Read is invoked.
ScryRaven does **not** load `.env`. With the applicable variables supplied:

```powershell
python -m scryraven "What is the maximum allowed weight of a ten-pin bowling ball?"
```

The ordinary runtime uses GPT-6 Luna / high for Research and GPT-6 Sol / medium
for Answer. Exa supplies ordinary general Search; Research can select Serper for
lexical/community/current discovery; LinkUp Fetch supplies external known-URL
Read. There is no architecture selector, Analyst checkpoint,
separate old Author handoff or fallback engine.
See [research architecture](docs/architecture/RESEARCH.md) for the promoted contract.

## Reading Room

**Direct launch:** from the repository root and activated environment above, with
`OPENAI_API_KEY` for model execution and `EXA_API_KEY` for ordinary web Search in
the process environment. Supply `SERPER_API_KEY` when Research invokes alternate
lexical/community/current discovery and `LINKUP_API_KEY` when it invokes external
known-URL Read:

```powershell
python -m scryraven.reading_room
```

Open [http://127.0.0.1:7331](http://127.0.0.1:7331) in your browser. Keep the terminal
running; Ctrl+C stops the server. It binds only to `127.0.0.1`. If the port is busy,
choose another with `--port 7339`. There is no remote bind option.

**Launch with the private repository `.env`:** use the existing doorman, which
supplies the child process environment without printing or exposing secret values.
From the repository root in PowerShell:

```powershell
$roomLogs = Join-Path $env:TEMP ('scryraven-room-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $roomLogs | Out-Null
$roomProcess = Start-Process .\.venv\Scripts\python.exe -WindowStyle Hidden -PassThru -WorkingDirectory (Get-Location).Path -ArgumentList @(
    'scripts/run_brokered_command_once.py', '--repo-root', ('"{0}"' -f (Get-Location).Path),
    '--repo-env', '--stdout', ('"{0}\stdout.txt"' -f $roomLogs),
    '--stderr', ('"{0}\stderr.txt"' -f $roomLogs), '--status', ('"{0}\status.json"' -f $roomLogs),
    '--timeout-seconds', '28800', '--target-current-python', '--', '-m', 'scryraven.reading_room'
)
```

Open [http://127.0.0.1:7331](http://127.0.0.1:7331). The broker captures output, so
there is no terminal startup banner. This example runs for up to eight hours;
sanitized logs/status are written under `$roomLogs` when it exits or times out.
After any active question finishes, stop this launch from the same PowerShell window:

```powershell
if (-not $roomProcess.HasExited) { taskkill /PID $roomProcess.Id /T /F }
```

This stops that launch's process tree; forced shutdown may leave no logs/status.
Closing the browser tab does not stop the server. See the existing
[doorman operator guidance](docs/operator/BROKERED_COMMAND_SESSION_OPERATOR_FLOW.md)
for credential-custody details. The product itself still does not load `.env`.

The Reading Room uses the same default per-user database as the saved-session CLI.
To keep your durable research in a chosen location, pass the path at launch:

```powershell
python -m scryraven.reading_room --database "D:\My Research\sessions.sqlite3"
```

Missing parent directories are created. Use the same path when restarting or when
opening these sessions from the CLI. The database holds your conversation and saved
source material; browser storage holds none of it. For a doorman launch, append
`'--database', '"D:\My Research\sessions.sqlite3"'` to the target arguments above.

For local latency dogfooding, explicitly choose a separate JSONL file:

```powershell
python -m scryraven.reading_room --dogfood-log "C:\tmp\scryraven-latency-01\turns.jsonl"
```

The file appends one body-free diagnostic record per attempted research turn, across
Reading Room restarts. It records timings, call and acquisition counts, safe usage
numbers and fixed outcome codes. It excludes questions, answers, source bodies,
prompts, URLs and credentials. Parent directories are created when requested.
Without `--dogfood-log`, no diagnostic file is written. An invalid log path stops
launch; if the file later becomes unwritable, Reading Room reports a generic
terminal warning and continues saving research normally. The session database is
still the durable product record, with questions, answers, retained Evidence and
historical citations. For a doorman launch, append
`'--dogfood-log', '"C:\tmp\scryraven-latency-01\turns.jsonl"'` to the target arguments above.

Choose **New research**, ask a question, and use the composer for follow-ups. Submit
with the arrow or Ctrl+Enter / Command+Enter; plain Enter adds a line. Research runs
in the HTTP request, with an indeterminate working state and no token streaming.
Completed answers, including limited results, are saved. A failed attempt keeps
the question available to edit and leaves completed conversation intact.

An answer completed after Research reaches its operating limit says so without
changing its supported, partial or unable status. Source-free conditional answers
are labeled as derived from your assumptions without external sources.

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
the session. Every question gets fresh Research and Answer decisions and
fresh research limits. Research can inspect actual retained sources without another
provider call, or acquire additional material. Research can see which exact retained
material a previous answer cited and reopen it locally, including an exact view
reconstructed from its retained full parent. This citation history guides navigation;
previous answers cannot support facts or citations. This mode saves nothing
between processes. `--html` remains an isolated single-answer option.

The equivalent sequential Python API accepts the same optional model, search,
fetch and limits arguments as `run`:

```python
from scryraven.session import ResearchSession

session = ResearchSession()
first = session.ask("According to the BIPM SI Brochure, what is the largest SI prefix?")
followup = session.ask("And what is the smallest one?")
```

`session.turns` exposes completed questions, answers and historical records;
`session.acquisitions` exposes immutable actual Evidence, including full parents;
`session.source_ids` exposes canonical identities. Each CompletedAnswer's `evidence` is the
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

Each saved `SessionTurn` exposes question, answer, posture, stop reason,
`selected_evidence`, `citations` and `citation_uses`. Citation records preserve
answer-local numbers, canonical source IDs, titles, URLs and exact selected material;
CitationUse records preserve the numeric markers' character spans. Historical
packets are saved exactly, including targeted-view IDs, parents, bounds and content.
They are not regenerated for display or automatically reused as current support.

All actual acquisitions, including complete large-source parents, retain their
original IDs and source relationships across restart. Future Research may select
them or derive new exact views locally, including views cited by earlier turns.
The complete prior question and answer text remains available to each new Research
and Answer call; Research alone receives historical citation IDs as navigation.
Prior answers remain conversation context;
Historical Analysis remains inspectable history; native turns have no Analysis.
Each question receives fresh Research and Answer decisions. Storage contains no
traces, credentials, raw model responses, corrections, lexical indexes or cache
state. Cache expiration does not prevent reopening.

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

The process needs `OPENAI_API_KEY` and `EXA_API_KEY`; Research-selected lexical,
community or current-web discovery needs `SERPER_API_KEY` only when invoked.
External Read needs `LINKUP_API_KEY` when invoked. It does not load `.env`.
The fixed ordinary assignments are GPT-6 Luna / high for Research and GPT-6 Sol /
medium for Answer. The transport retains its existing `ModelConfig` and
`SCRYRAVEN_FAST_*` / `SCRYRAVEN_SMART_*` environment interface: FAST is the
compatibility role for Research, and SMART is the compatibility role for Answer.
Explicit configuration overrides the defaults. There is no model router,
automatic premium escalation or model fallback. One stateless OpenAI
Responses transport uses structured output; no model has built-in web tools.

## Acquisition and evidence

Exa supplies ordinary general Search (`auto`, six results, query-guided highlights
up to 4,000 characters per result). Research may select Serper for lexical,
community or current-web discovery (ten navigation candidates). Serper snippets
are navigation only; Research must Read a useful URL through LinkUp Fetch before
its source material becomes Evidence. LinkUp Fetch acquires ordinary known-URL
readable source material. Generated provider summaries and answers are excluded. Metadata
guides navigation; actual highlights can support only what their text establishes.
Missing conditions, identity, applicability or connected context can require a Read.

Search admits actual source-derived highlights mechanically. Read can acquire a
full source, reread retained material, or select exact views. A `full` Read secures
the full parent but may return bounded exact views when it is large. Each Read
reports the exact text returned and whether a focused lexical lookup matched or
fell back to dispersed windows. Unscoped Find ranks lexical matches across the
retained library on a comparable corpus-wide scale; it remains navigation, not
semantic evidence judgment. Local Read and Find need no provider I/O for retained text.
All results return to Research
for reassessment. Neither source count, failed search nor budget exhaustion proves
support, completeness or nonexistence. The original/current request governs scope.

Actual acquisitions remain immutable and locally rereadable across follow-ups.
Same-URL versions retain their canonical source identity. Large full sources can
provide exact bounded views through the existing source index; shelving attention
does not discard Evidence. New turns begin with fresh Research state and fresh
Answer decisions over actual material, using prior conversation only for referents.

Answer selects literal passages in the same fresh semantic call. Mechanical
membership checks verify those passages against the supplied exact material;
supported and partial evidence answers require at least one validated passage
from every cited source group. These checks do not decide entailment. Valid
citations receive compact source numbers in first-use order. Each answer saves
its selected material and citation-use spans,
so later acquisitions cannot change historical inspection. Views carry exact
parent bounds; highlights never receive guessed offsets or invented page numbers.
Source labels use publication metadata, PDF filenames or hostnames without
generating titles from evidence text.

The established operating limits are 12 semantic attempts, 16 external acquisition
attempts, a 300-second hard run ceiling and 128,000 characters of current Evidence
attention. Local
Read/Find use no external allowance. Corrected model outputs use the same finite
semantic allowance. The loop reserves 180 seconds for terminal Answer once Evidence
exists; each model call remains capped at 120 seconds. The longer ceiling gives
operational diagnostic headroom and is not a product-latency target. The loop
returns an honest operational unable result when it cannot complete a source-grounded answer.
Supported, partial and unable results remain distinct.

SQLite keeps the existing revision-checked atomic snapshot boundary. Native turns
store `analysis: null`; old saved Analysis remains a historical record only.
Reopening does not rerun research, rewrite historical turns or promote generated
history to Evidence. Unknown/corrupt schemas fail safely. The source and answer
renderer escapes untrusted text, disables raw model HTML, and loads only local
assets under the existing content security policy.

## Observations and checks

Answers, a compact posture/operating status, and a source list appear on stdout.
Source-free conditional answers are labeled as derived from user assumptions;
Research operating-bound completion is disclosed separately from answer posture.
`--trace` adds compact diagnostics on stderr: model
roles, public Research choices, acquisition results, body-free conversation,
catalog, retained-library and active Evidence size counts, exposure IDs/lengths/hashes,
answer posture, bounds and citation resolution. Exact source bodies stay outside
the compact trace. These diagnostics contain no private reasoning.
Raw payloads, credentials and hidden reasoning are excluded.
`--trace-evidence` also exposes exact selected supporting material, citations and provenance;
unseen full parents remain out of the trace. Use public questions for observations.
Session diagnostics identify the turn, retained material count, local reuse,
new acquisitions and remaining operating allowance. Prior conversation is not
added as a diagnostic payload. Numeric source references start afresh in each answer.

Execution errors exit 1 with a safe stage/code. Supported, partial and unable
postures exit 0. An honest limit is not proof of nonexistence.

Acquisition preserves fixed safe Exa, Serper and LinkUp configuration-missing
codes and LinkUp material-unavailable codes; other Search/Read exceptions remain
generic safe failures.

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
