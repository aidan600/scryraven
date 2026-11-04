# Dogfood Answer Feedback 01

The hosted private preview supports short participant comments beneath each
completed answer. Before this change, an ordinary participant could only submit
a follow-up question. Now Feedback on this answer provides an immediately usable
plain-text field, Send feedback, chronological saved comments, UTC timestamps and
Remove controls. Comments go to the administrator, independently of research.

## Storage and identity

SQLite schema 6 adds `answer_feedback` and its session index. Each record contains
`feedback_id`, `session_id`, `turn_index`, `author_id`, `created_at` and `text`.
`turn_index` is the existing immutable 1-based completed-turn identity: ordinary
commits append turns and reject changes to the historical prefix. No new answer
identity, research authority or answer lifecycle is introduced.

Feedback mutations authorize the session owner inside the same short transaction
that checks the completed answer and inserts/deletes the record. They do not
change session metadata, payload, revision, jobs or the durable submission ledger.
They do not require idle research. A session deletion removes ordinary feedback
within its existing deletion transaction. Older schemas migrate additively;
historical conversation, attachment and citation bytes are not rewritten.

Text is limited to 2,000 characters before trimming. Empty/whitespace-only text,
ASCII controls other than tab/CR/LF, and unpaired Unicode surrogates are rejected.
Stored comments are rendered through ordinary Jinja escaping, never Markdown or
trusted HTML. SQLite also enforces the text-length bound. Reads use insertion
order, including when server time moves backward.

## HTTP and browser behavior

Only hosted mode enables feedback. The existing signed Cloudflare Access identity,
trusted host, ownership checks, same-origin checks, form-body limits and security
headers remain in force. Feedback POSTs accept only their exact named fields,
one occurrence each, and form-encoded content. The server supplies author,
timestamp and answer association; forged extra fields are rejected.

CSRF tokens bind principal, session and answer action (plus comment identity for
removal). They use revision zero because a completed answer remains the same when
later research advances the session. Tokens retain the existing lifetime and
single-use replay protection. Administrator access to tester conversations
remains read only, including feedback mutations. Administrators can participate
in their own conversations under the ordinary ownership rule.

Ordinary native forms redirect back to the answer's feedback section. JavaScript
progressively enhances submission/removal by replacing only that section, keeping
the follow-up draft, selected attachments and other feedback drafts in place.
Removing a comment preserves the same answer's unsent comment. Completion polling
defers page reload while feedback is being edited or sent and offers the existing
completion link. Research itself continues normally. No rating, category, modal,
analytics, moderation model or external feedback service is added.

## Administrator export

The existing session ZIP and `scryraven-session-export-1` format remain. The
`session.json` object adds `answer_feedback`, with complete stored fields and
`provenance: authenticated_participant`, plus an `answer_feedback_provenance`
description of the server-verified author, timestamp, stable turn index and
non-Evidence status. Existing `state`, jobs, attachments and available diagnostic
files keep their original structure and custody. Sessions without comments export
an empty array. Older exports remain readable without the optional new keys.

The export includes feedback only for answers in its loaded session snapshot.
If a concurrent follow-up completes after that snapshot was loaded, its new answer
and comments appear in a later export; comments cannot point outside the exported
answer list. The export retains the existing limitation that diagnostics may be
absent due to retention or write limits. Previously downloaded exports and backups
are unaffected by deleting an ordinary comment or session.

## Verification and limits

Focused storage tests cover persistence, restart/reopen, concurrency and clock
ordering, multiple/historical answers, active research, unchanged payloads and
quotas, author checks before private-body decoding, malformed text, exact answer
and comment association, deletion and schema 1–5 migration.

Hosted HTTP tests exercise real signed synthetic identities, ordinary form routes,
SQLite persistence and ZIP exports. They cover owner/admin/cross-user boundaries,
identity/action/answer-bound CSRF, replay/origin rejection, malformed and duplicate
fields, the text bound, literal HTML, quota independence and active follow-up
completion. A feedback sentinel is absent from both actual Research and Answer
packets of the scripted ordinary follow-up.

Real Edge checks cover 1440px desktop and 390px/320px touch layouts, keyboard
interaction, multiple comments, reload, historical answer association, literal
HTML, removal, administrator inspection, follow-up draft/file preservation,
feedback editing during research completion, and native forms with JavaScript
disabled. Existing browser/source custody and local Reading Room checks remain
in the full offline suite.

Run offline verification using the installed development dependencies and external
temporary storage:

```powershell
$env:TEMP = 'C:/tmp'
$env:TMP = 'C:/tmp'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:PYTHONPATH = 'C:/tmp/sr-preview-v2/offline-guard;C:/tmp/sr-waitress'
$env:SCRYRAVEN_REVIEW_OUTPUT = 'C:/tmp/sr-answer-feedback-01/screenshots'
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --tb=short -rs --basetemp C:/tmp/sr-answer-feedback-suite-NEW
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m compileall -q scryraven
node --check scryraven/static/reading_room.js
.venv/Scripts/python.exe -m pre_commit run --all-files
git diff --check
```

The external guard rejects external Python sockets/DNS; browser fixtures also
reject external requests. Its local path and the optional Waitress dependency
path are development-environment aids, not runtime dependencies. The final review
receipt, exact tested revision, suite output and synthetic screenshots are kept
under `C:/tmp/sr-answer-feedback-01/`.

No model, provider, Railway, production database, private conversation or
credential access is licensed or used. Hosted deployment remains unobserved.
Research/Answer prompts, decision schemas, provider routing, source selection and
citation behavior are unchanged. The local Reading Room shares only additive
storage compatibility; it has no feedback UI or usable mutation route. No
explicit removal was requested. This branch is for local review only.
