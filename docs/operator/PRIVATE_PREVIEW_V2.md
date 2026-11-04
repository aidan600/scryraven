# Private Preview V2 verification

V2 updates the existing hosted Reading Room while preserving Research/Answer
prompts and semantic ownership, acquisition/ranking, source and citation custody,
Cloudflare identity, ownership isolation, administrator read-only inspection,
attachments, credential handling and unrelated research limits. The local
personal-plan/OpenRouter path retains its existing settings and two workers.
This work does not deploy or alter Railway/Cloudflare.

## Before and after

| Surface | Before | V2 |
| --- | --- | --- |
| Hosted execution | Two workers, one Researching job per owner | Four shared workers; four conversations from one owner can overlap |
| Admission | Eight waiting slots with ambiguous waiting copy | Same eight slots, explicit “Your question is queued.”, automatic start and persistent history status |
| Same conversation | One accepted active question | Preserved |
| Hosted settings | Environment-only role configuration | Durable administrator Settings, tester Standard/Fast choice, no restart |
| Initial hosted defaults | Terra/Medium, Sol/Medium, Standard | Terra/Medium, Sol/Medium, Fast; explicit initial environment overrides remain seeds |
| Preference changes | Snapshot must equal current hosted policy | New admissions use current defaults; accepted jobs and retries keep original snapshots |
| Mobile history | Flex row override disrupts drawer | Column layout, bounded scrolling, fixed viewport menus, focus and dismissal |
| Technical receipts | Above progress, below answers | Collapsed secondary Run details beneath progress/answer |
| Preview explanation | Large composer operator panel | Concise welcome explanation and persistent Privacy & participation entry |

Saved administrator choices override initial environment role/tier configuration
across restarts. A tester's durable processing preference overrides the global
tier only for that tester's future admissions. Model IDs/efforts remain
administrator-owned and validated against the approved exact family. Safe
submission replay and retries keep their original snapshot even after defaults
change. A changed question/files/tier under an existing submission identity is
still rejected rather than silently resubmitted. The hosted operator's existing
billing authorization remains sufficient.

The mobile root cause was the <=760px rule switching the sidebar from grid to
flex without a column direction. V2 also keeps the conversation list's minimum
height bounded, the footer below it and menus outside scroll clipping. The menu
opening click is explicitly owned by the three-dot control; it cannot activate
newly shown Rename/Delete links. Desktop hosted sidebar footer sizing is
independent of the composer footer; the local layout stays unchanged.

Server interruption and storage interruption have fixed accurate messages.
The shared server code can result from shutdown or startup recovery, so it does
not assert a restart. Generic failure does not invent a cause or imply that a
new question canceled earlier work. No submission-caused interruption reproduced
in deterministic concurrent admission or the resource probe.

## Offline evidence

Focused checks exercise four jobs for one user, four jobs across users, a fifth
Queued job and automatic dispatch. A 24-thread admission burst with all four
workers occupied accepts exactly eight waiting jobs and rejects sixteen without
orphan sessions. Per-conversation busy checks, per-job model/usage isolation,
owner-scoped status, daily quota persistence/UTC rollover, settings mutation while
four jobs run and one waits, explicit retries, exact lost-response replay,
identity/CSRF/forged-field attacks, historical schema/payload readability and
restart without replay retain coverage.

Real Edge browser acceptance uses synthetic hosted accounts at 1440px desktop,
768px tablet, 390px and 320px. It covers administrator Luna/High selection and
saved settings, tester processing-only controls, privacy, long history scrolling,
branding/close/new-research/footer geometry, popup bounds, actual touch menu
opening without clickthrough, ArrowDown/Tab/Shift+Tab/Escape focus, outside tap,
rename, deletion confirmation/cancel/delete, and existing thread reading. An
in-document sentinel verifies Queued -> Researching without a page reload.
Completed/failed/interrupted states retain collapsed receipts below their content.
Existing local Settings and 200% zoom browser checks remain in the full suite.

Screenshots are synthetic and kept outside the checkout under
`C:/tmp/sr-preview-v2/screenshots` and the final full-suite screenshot directory.
Representative `preview-v2-history-menu-320.png`,
`preview-v2-admin-settings-390.png`, `preview-v2-history-menu-768.png`,
`preview-v2-queued-390.png` and completed desktop views were visually reviewed.

The [resource report](PRIVATE_PREVIEW_V2_RESOURCES.md) describes actual Waitress,
signed synthetic Access validation, ordinary ResearchSession/OpenAIModel,
protected diagnostics, SQLite, large source contexts and PDF/image attachments
in a separately measured process with two-CPU affinity. All ten jobs completed
with exact persisted answers, citations and attachments. Its measured CPU/memory
are offline observations, not real provider latency or deployed capacity.

Run the complete regression suite with the repository's declared development and
hosted dependencies installed, external temporary storage and no live credentials:

```powershell
$env:TEMP = 'C:/tmp'
$env:TMP = 'C:/tmp'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --tb=short -rs --basetemp C:/tmp/sr-preview-v2-verification-NEW
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m compileall -q scryraven scripts/offline_private_preview_stress.py
node --check scryraven/static/reading_room.js
.venv/Scripts/python.exe -m pre_commit run --all-files
```

The development environment additionally supplies Waitress from its existing
isolated `C:/tmp/sr-waitress` directory and a disposable `sitecustomize.py` guard
that rejects external sockets/DNS while allowing loopback. Hosted browser fixtures
also reject external browser requests. Windows Edge and filesystem-link checks
need the authorized execution context outside the restricted launch sandbox.
The first sandbox pass failed to launch Edge; that is not product evidence.

## Current limits and review

No live provider/model/search calls or production access are part of this phase.
Live four-job capacity, provider latency/rate limits, exact account access and
model compatibility, Railway/Linux memory and CPU peaks under its actual 2-vCPU /
2-GB limits, and long-duration capacity remain untested. No actual billed cost is
inferred from synthetic usage or missing provider data. No new database, replica,
queue service, privacy mode or semantic responsibility is introduced. Preferences
use the existing schema-5 table; there is no migration or history backfill.

The final handoff supplies the exact tested commit and the one PR into main.
Review is for the coherent V2 source change; merge and deployment remain separate
human decisions. Do not initiate deployment from this work item.
