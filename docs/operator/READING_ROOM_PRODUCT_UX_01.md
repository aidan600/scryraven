# Reading Room Product UX 01

Baseline: merged main `0229128b1a8d7a0b78a042327b971fa01a411967`.
Branch: `codex/reading-room-product-ux-01`.
Review artifacts: `C:\tmp\scryraven-reading-room-ux-01`.

## Product behavior

The answer remains the main reading surface. The former persistent controls and
PDF upload workflow are replaced by one compact composer. Its empty footer
measures 75 px at 1440x1000 and 73 px at 390x844; the reading viewport retains
846 and 707 px respectively. Text grows naturally to a bounded scrollable
writing area. Attachment and source-language controls sit inside the composer.
Ctrl/Cmd+Enter submits; Enter adds a line. Draft text survives same-tab navigation
and refresh where browser session storage is available. Files remain selected
when an enhanced submission fails validation; navigating away from an unsent
file selection requires selecting those files again. Native multipart forms work
without JavaScript; drop/paste, automatic status updates and draft storage are
progressive enhancements.

The language menu selects English (default), Match answer language, Spanish,
French, German, Polish, Portuguese, Japanese, Chinese or Arabic. The preference
is saved with the accepted question, belongs to that conversation, and is
snapshotted for its run. It affects subsequent source-description generation.
The existing Answer role produces these descriptions in its normal response;
there is no translation call or click-triggered inference. In previews the
explanation is prominent, followed by the unchanged original title, publisher,
original action and saved-excerpt action. Metadata remains fallible and cannot
establish citation membership. Historical answers are not regenerated. Missing
or invalid descriptions fall back to the source title without invalidating the
answer or triggering correction.

## Attachments and actual model inputs

Picker selection, drop onto the composer, and clipboard image paste feed the
same pending file collection. Chips show filename/type/size, image thumbnails,
and accessible removal controls. Invalid selections block submission; a valid
question is never silently sent with an invalid file omitted.

The server validates every upload before accepting any of them. One short
SQLite transaction accepts the session, question, file references, language,
submission identity, starting revision and queued run together. Failed admission
rolls everything back. Filenames are sanitized display metadata, never paths.

Bounds:

- Four attachments per question; PDFs and images share that count.
- PNG, JPEG and WebP still images: 8 MiB each, 4096 px per side, 16 million pixels.
- 24 MiB aggregate attachments, including explicitly reused image references.
- Existing text PDFs: 20 MiB, 500 pages, two million extracted characters.
- Multipart text fields remain bounded at 256 KiB; questions at 20,000 characters.

Pillow verifies and fully decodes actual image bytes, checks format/dimensions,
and rejects animation and malformed content. PNG/JPEG/WebP originals and their
hash/dimensions are retained in session-owned rows. Preview routes produce
metadata-free PNGs after applying orientation; original download routes preserve
exact bytes. Both routes verify session ownership, return no-store/nosniff
headers, and accept only allocated image IDs. PDFs retain their existing exact
page-text extraction and original download. Scanned PDFs and embedded PDF images
are not analyzed. No SVG, active document, executable, arbitrary format, audio or
video input is added.

Research and Answer receive actual Responses `input_image` blocks whose
`image_url` is a Base64 data URL of the original, alongside non-Evidence image
identity metadata. The API and personal-plan transports preserve these blocks;
no filename-only substitute or fake OCR is used. Images attached now reach both
roles. Older images appear as catalog metadata until an existing local Read or
Answer library_read operation requests an I#; then actual image content reaches
the continuing semantic interaction. An unrelated turn does not automatically
send all previous images. Current image exposure remains bounded to four/24 MiB.

The configured model is never changed to gain vision. A conservative supported
model allowlist includes the selected Terra/Sol models; an unsupported selection
fails with an explicit retained-image error. Provider rejection remains a real
failure, with no API or billing fallback. The existing plan payload still omits
unsupported service overrides; no equivalent plan service tier is claimed.

`user_images` is the minimal additional Answer support basis. It permits visual
observations only when an actual image was supplied, without fabricated page
coordinates, quotations or Evidence aliases. External claims still use the
existing Evidence and strict citation resolver. An image catalog entry alone
cannot justify visual observations or establish citation membership.

## Local execution and recovery

Each accepted submission redirects immediately to its durable conversation/run.
Two local worker threads call ordinary ResearchSession.ask; eight further
admissions may wait. Each conversation permits only one queued/researching job.
The runner does not choose searches, plan research, or create another semantic
path. Existing per-turn engine resources remain unchanged.

The sidebar and conversation expose queued, researching, completed, failed and
interrupted states. Polling reports actual lifecycle transitions; it invents no
steps or percentages. Completion elsewhere announces a link back to the answer.
Returning to the active conversation displays its saved question/files and
current status. Completion focuses the actual answer while preserving a new
unsent draft. Native no-JavaScript pages offer a refresh action.

Submission identity is durable and explicit. Identical replay returns the same
run, including after completion. A changed payload under an accepted identity is
rejected. After an uncertain connection, the browser retains the identity. A
confirmed content conflict offers the originally accepted conversation and an
explicit action to allocate a new submission for the edited draft; nothing is
silently re-executed.

No SQLite write transaction spans inference or acquisition. The ordinary final
revision check, completed turn, Evidence/citations and completed job state are
committed in one transaction. Intervening completed turns cause a conflict rather
than overwrite. Rename changes metadata and survives worker completion. Deletion
and standalone attachment mutation are rejected while research is active.

A failed run preserves its question and accepted attachments. Retry is an
explicit new admission of the exact saved question/files/language and original
starting revision; stale retries require reviewing the changed conversation.
Unexpected errors expose fixed safe codes only. Storage failures interrupt the
lifetime truthfully once storage is available, without an automatic retry.

An OS lock on the database's `.reading-room.lock` sidecar gives one local Reading
Room server custody of that database, before startup interruption recovery. Its
existence is not a lock: Windows/POSIX release ownership on process exit. A second
server cannot interrupt the first or bypass concurrency by choosing another port.
Shutdown denies admissions and late commits, marks pending jobs interrupted, and
retains ownership while any worker is still exiting. Already dispatched external
calls cannot be forcibly canceled safely in an embedded process. Ordinary
process exit ends daemon workers. Restart exposes interrupted work and performs
zero inference until the user explicitly retries. Work does not survive server
exit. This is not a distributed queue or automatic resumption system.

## Verification

Deterministic tests exercise decoded image rejection, API/plan content blocks,
both semantic roles, retained image inspection, no fabricated Evidence authority,
exact PDF citations, atomic admission, durable language, old snapshots, replay,
queue bounds, two blocked workers, rename/delete behavior, revision conflicts,
failure/retry, storage interruption, shutdown/late commits, competing processes
and abrupt-exit lock recovery. Controlled Events replace arbitrary sleeps for
research concurrency tests. CLI and ordinary text research regressions remain
in the complete offline suite.

Headless Edge checks exercise real server-rendered pages, picker/drop/clipboard,
removal, validation, draft preservation, multiline growth, keyboard/focus, narrow
layout, multilingual previews and historical source reopening. The complete
browser workflow submits an image and PDF to A, navigates to B, submits B while A
is blocked, refreshes A, releases A, observes completion in B and reopens A with
exact originals and older turns intact. Real 200% browser zoom uses
chrome.tabs.setZoom in a disposable test extension/profile, not a CSS assertion;
reported zoom is 2, devicePixelRatio 2 and effective layout width 628 px. All touch
controls remain at least 44 px. No frontend framework was added.

Screenshots and `ui-measurements.json` are in the external review bundle:
`desktop-reading.png`, `mobile-reading.png`, desktop/mobile attachment and Polish
citation previews, and `desktop-zoom-200.png`.

The frozen implementation passed all 1,128 offline tests, including 14 actual
headless Edge checks, plus Ruff, Python compilation, JavaScript syntax,
whitespace checks and all six configured hooks. The licensed live validation
has not yet run at this implementation checkpoint.
