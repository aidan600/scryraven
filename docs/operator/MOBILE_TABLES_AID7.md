# AID-7: Read / Table for mobile prose comparisons

This change builds directly on approved PDF candidate
`804ae6d52a50ab874d69f4b15e1a40a81aa0be2c`, kept as a separate ancestor commit.
Aidan reported native iPhone Safari PDF saving on its Blinky preview. That
reported check applies to AID-5; the combined candidate needs a new device check.
No push, PR, deployment or hosting configuration change is authorized here.
AID-6 Sources scrolling is outside this change.

## Behavior and boundaries

At the Reading Room's existing phone breakpoint (760px), simple prose tables
default to Read. Each full-width row section uses its original first cell as a
heading, then shows each remaining cell beneath its column label. Read / Table
buttons retain the current row when the layout changes. Table mode provides a
real semantic grid, pinned row names, keyboard-focusable horizontal overflow and
a visible cue for offscreen columns. At 320/390/430px, one full prose attribute
fits next to its row name; readers can scroll to the same attribute across rows
without horizontally panning each line of a paragraph.

The enhancement keeps a single table and the original cell descendants. It does
not reconstruct answer text or duplicate citation, link or image nodes/IDs.
Repeated column labels contain only checked, noninteractive header formatting
and are hidden from assistive technology. The original header row and explicit
table/row/header/cell semantics remain available. Row headings are also exposed
as headings in Read. The switch uses ordinary buttons with `aria-pressed`, and
the overflow region supports native keyboard scrolling without a live region.
Horizontal movement repositions an open citation preview or dismisses it when
its anchor leaves the visible table. Saved-passage navigation retains the exact
original citation and the existing Back to answer behavior.

Classification is presentation-only: a non-title cell must contain sustained
prose (120 characters and 18 words). Compact numeric cells stay grids.
Only rectangular tables with one unambiguous header row and short nonempty row
titles get Read. Spans, nested tables, footers, ambiguous labels, interactive or
image-bearing headers and unknown semantics stay in their original scrollable
grid. Existing explicit fallback header scopes are preserved. Long prose in a
fallback still receives readable column widths. With JavaScript unavailable,
the original scrollable table remains. Markdown's existing content/security
rules, including its disabled raw HTML/image syntax, are unchanged; an injected
DOM image control separately checks that the layout preserves existing images.

Screen rules are isolated from print. Print hides the switch, scroll cue and
repeated labels and restores the grid regardless of the selected screen view.
The protected AID-5 print document does not load the table enhancement. Its
stylesheet, template and print-button script remain byte-for-byte unchanged.

## Synthetic device retest

Use the same private transfer/import and Python setup described in
`IOS_SAFARI_PRINT_AID5.md`. To keep a previously imported AID-5 branch untouched,
fetch the combined bundle without a destination ref and choose a new local
device-check branch in a clean checkout:

```powershell
git bundle verify C:\Downloads\aid-5-aid-7-download-candidate.bundle
git fetch C:\Downloads\aid-5-aid-7-download-candidate.bundle refs/heads/codex/aid-5-ios-safari-print
git switch -c aid-5-aid-7-device-check FETCH_HEAD
git rev-parse HEAD
```

Compare HEAD with the supplied combined candidate SHA, then run:

```powershell
.venv\Scripts\python.exe tests\serve_print_fixture.py --host <PC_LAN_IP> --port 7332 --tables
```

On Linux/macOS use the environment's `bin/python`. Open the printed URL in
iPhone Safari through the existing private test setup or the same private Wi-Fi.
The `--tables` mode supplies three cheeses and six actual paragraph-length cells,
bold/emphasis/code, an in-cell saved-passage citation and a unique linked final
cell marker. Both source destinations are local synthetic pages. The runner
creates a disposable database, disables live I/O/dictation, blocks mutations and
cleans up on Ctrl+C. Omitting `--tables` retains the approved AID-5 sample.

For the existing private Blinky preview proxy, `--source-origin
https://<existing-private-preview-host>` makes the synthetic source links in the
saved PDF return to that preview instead of the phone's localhost. It sets only
fixture link URLs, performs no connection, and does not create/configure a
preview, change binding or relax trusted-host checks. Keep the proxy's existing
Host forwarding arrangement. No preview or hosting change was made in this task.

1. Record iPhone/iOS/Safari version. In Read, scroll through the entire Brie
   flavour paragraph, including its final sentence, then the serving paragraph.
2. Choose Table. Compare Flavour and texture for Brie and Cheddar, pan to Serving
   and keeping, and compare those same rows. Confirm row names and the column
   cue stay useful, then switch back to Read without losing row context.
3. Tap the saved-passage citation inside Brie's flavour cell in each view. Check
   the exact highlighted passage, then Back to answer: the citation, row, view
   and horizontal position should survive. Check preview actions too.
4. Tap **Download PDF** and save the attachment. Reopen from Files and verify the
   complete final cell and its marker/link appear once, all columns are present,
   and the link opens the local source while the server runs. See the
   [PDF renderer setup](IOS_SAFARI_PRINT_AID5.md#download-pdf).
5. With VoiceOver, inspect row headings and table header/cell navigation. Check
   that visual labels do not cause duplicate announcements. Try landscape,
   larger text, and the original AID-5 sample as a combined regression check.

Aidan reviewed the combined table preview on iOS 27.0.1. The separate Download
PDF action and VoiceOver remain to be checked on the updated candidate. The
earlier browser checks below used Chromium and synthetic fixtures.

## Checks actually run

Linux system Chromium **151.0.7922.173** through Playwright exercised 320, 390,
430 and 1440px layouts. The full paragraph fixtures were visually reviewed in
Read, both horizontal scroll positions in Table, desktop and the two-page grid
PDF. The final table module passed **12 checks**, with **10 WebKit skips**:

```sh
PLAYWRIGHT_BROWSERS_PATH=/tmp/scryraven-browsers .venv/bin/python -m pytest tests/test_reading_room_tables_browser.py --basetemp /tmp/aid7-tables-final -q -rs
```

An expanded regression selection passed **152 checks**, with **30 WebKit skips**
before the final single-paragraph edge case was added and checked above:

```sh
PLAYWRIGHT_BROWSERS_PATH=/tmp/scryraven-browsers .venv/bin/python -m pytest tests/test_reading_room_tables_browser.py tests/test_reading_room_print_browser.py tests/test_citation_preview_browser.py tests/test_answer_presentation.py tests/test_durable_support_reader.py tests/test_citation_reader_presentation.py tests/test_hosted_reading_room.py tests/test_reading_room.py --basetemp /tmp/aid7-regression-final -q -rs
```

Coverage includes complete cells and formatting, same-node links/images and
citations, no duplicate IDs/AT labels, Read/Table switching, pinned row context,
offscreen cues, keyboard scrolling and previews, exact saved-passage return,
compact/complex/no-script fallbacks, owner protection and print/PDF text and
link counts from both views. PDF checks use explicit print media with
`page.pdf()`; they do not operate a native print/save sheet. Both fixture modes
passed loopback GET/HEAD, source-link, rejected write/foreign Host and Ctrl+C
cleanup checks; custom preview origins persisted/rendered without contacting
them. Ruff, JavaScript syntax, compilation, whitespace and configured pre-commit
hooks passed. No live model/provider call or production database was used.

WebKit was unavailable because browser download hosts were blocked by this
environment's network policy. No Firefox, native Windows or native iPhone check
is claimed for this table change. The entire repository suite was not rerun;
the earlier AID-5 handoff records its non-green full-suite result and baseline
reproductions. No general green full-suite result is claimed here.
