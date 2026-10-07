# Citation Reader / Durable Support Product 01

OUTCOME: Met over the authorized bounded implementation and PRODUCT observations.

## Baseline and tested revision

- Phase worktree: `C:\Users\aidan\sr-phases\citation-reader-durable-support-product-01`
- Branch: `codex/citation-reader-durable-support-product-01`
- Exact merged baseline: `6b3dac8761133dd27868852cd7d2337a9b9e9883` (PR #671).
- Ordinary PRODUCT runtime tested: `30889acc1783608dae653e8e05d0b023fe5e1ae7`.
- PR #672's subsequent focused Reader presentation fix was verified offline
  against the retained turns; it made no new PRODUCT/model/search calls.

The historical primary checkout was excluded throughout this implementation.
The external credential file was passed by path to the phase's existing doorman;
the controller did not open, parse, print or copy its values. The operator guide
now records that human-approved source for future phase worktrees.

## Before -> after

Before, terminal Sol semantic answers were frozen and Luna copied literal
passages for source-group localization. Validated spans existed only in forensic
observations; durable Reader inspection showed generic saved material.

Now, code resolves the frozen answer and every citation occurrence first. It
partitions **all exact cited saved text** into addressable regions, without
ranking or preselection. Luna returns only U-to-S ID lists. Code validates every
occurrence, resolves IDs into exact material-relative character coordinates and
UTF-8 SHA-256 material/passage hashes, then persists these coordinates in that
CitationUse. Temporary IDs and model-written quotations are absent from product
state. No Sol semantic ownership, source-completion policy, acquisition policy,
concurrency or budget behavior changed.

Malformed, missing, empty, unknown, duplicate or cross-source selections enter
the existing legacy Sol AnswerDecision/source_readings fallback. This path still
gets the completed Evidence packet without the discarded semantic draft. Failed
localization does not publish that draft with generic inspection. Old saved turns,
legacy-fallback turns and existing no-progress provisional completions without
coordinates retain generic source inspection.

The Reader displays the clicked occurrence's exact retained support first,
expandable surrounding context second, and full saved material third. The original
publication or PDF action appears above the support. Source-overview inspection
remains generic. Reading never fetches a new publication or calls a localizer.

## Ordinary PRODUCT evidence

Two turns used actual Reading Room forms and the production ResearchSession path,
with ordinary configured models: Research and localization `gpt-6-luna` high,
Answer `gpt-6.1-sol` high. No engine/model override, injected acquisition,
predetermined answer or support binding was used. The PDF was a synthetic input
uploaded through the ordinary PDF form, not a substituted downstream result.

| Observation | Result | Cited materials -> full regional packet | Occurrences -> durable selected regions | Legacy fallback | Elapsed |
| --- | --- | --- | --- | --- | --- |
| Public FAA battery conditions, quantity limit and gate-check exception | Supported, distinct capacity/approval/exception passages | 2 materials, 8,271 chars -> 80 regions | 5 -> 12 | None | 47.813 s |
| Three-page Cedar Field Station synthetic visitor bulletin, age/guide conditions and weather override | Supported; booking and guide do not override closure | 3 materials, 901 chars -> 20 regions | 9 -> 19 | None | 29.047 s |

Each turn made two Research calls, one Sol semantic Answer call and one Luna
localization call. Localization did not consume a semantic attempt. The exact
concatenation of regional exposures matched every character of the cited saved
material. Every persisted region passed its source, range and both hash checks.
Different occurrences of the same numbered source retained different passages,
including conditions and noncontiguous qualifications.

A separate Reading Room process opened the persisted database without credentials.
Browser checks at 1,920 px and 390 px clicked **every one of the 14 occurrences**,
compared rendered support character-for-character to the saved coordinate slices,
expanded context, checked support/context/full-material order and generic source
overview, and observed no JavaScript errors or horizontal overflow. Those checks
made only local GET requests. The original PDF action returned bytes exactly
equal to the uploaded file. A separate synthetic Reader control also exercised
1,440 px, 1,920 px and 390 px layouts and repeated-source behavior.

The credentialed observation server was intentionally stopped after both turns.
Its broker status records target exit 1 from that termination, with no timeout;
both ordinary turn diagnostics independently record completed revisions. The
uncredentialed inspection server used port 7445. Both temporary inspection
servers were stopped after verification; all exact artifacts remain saved.

## Offline verification

The original phase's full suite passed: `823 passed`. The only warning was inability to write the
pytest cache previously created under a different execution identity; it did not
affect tests. A fresh phase-specific external basetemp avoided that identity's
old temporary-directory deletion conflict.

Focused checks protect exhaustive exact-text partitioning (Unicode, CRLF and
long unbroken text), repeated occurrences, noncontiguous conditions, wrong-source
and wrong-version rejection, per-use completeness, malformed-ID legacy fallback,
coordinate-only persistence, hash/range corruption rejection, historical generic
inspection without payload rewriting, PDF-view custody and original-source
rendering. Existing Sol semantic, deadline, no-progress, calculator and legacy
literal-reading checks survive. Ruff, Git whitespace checks and all configured
pre-commit hooks passed.

### Focused Reader presentation review fix

The former 470 px inspector and 1,700 px companion breakpoint were replaced by a
560–780 px Reader alongside the Answer from 1,024 px. The history column yields
while the Reader is open on laptops and returns on close; wider desktops retain
it. Below 1,024 px, the Reader fills the screen. Exact selected text is highlighted
within readable retained source prose. Each PDF support excerpt labels the page
or page range already present on its saved Evidence view, independently of the
overall source group's page locator. Coordinates, source selection and custody
are unchanged. Standalone HTML shares the highlighting and only reveals the
clicked occurrence's support; manual source overview remains generic.

Six focused tests protect exact escaped source text, nearby context, mechanical
PDF locators, use isolation, generic inspection and standalone rendering. The
full revised suite passed: `829 passed`; Ruff, pre-commit and `git diff --check`
passed. No backend architecture, persistence, session schema, model, prompt,
Search, fallback or localization changes were made for this fix.

An uncredentialed local Reading Room process reopened the existing web/PDF
turns. Offline browser checks at 320, 390, 760, 900, 1,024, 1,280, 1,366, 1,440
and 1,920 px verified every occurrence's exact highlights, page locators, context,
full saved material and generic overview. Desktop Reader widths were 560, 640,
683, 720 and 780 px, with Answer text widths of 408–714 px. Mobile filled the
viewport. Keyboard opening, original-action focus, Escape/close and return to
the originating citation or Sources control passed. Standalone HTML passed at
1,440 and 390 px. No horizontal overflow or JavaScript errors were observed;
inspection used local GET requests only. These are offline presentation checks,
not a third ordinary PRODUCT observation.

## Scope, removal and limits

The normal quote-copy localization schema, prompt and validator loop were removed.
Legacy Sol literal-reading machinery remains because its fallback is explicitly
required. No new semantic actor, publication alternative, product restriction,
preselection, concurrency or acquisition responsibility was introduced.

This demonstrates exact custody, persistence and Reader consumption over two
ordinary turns; it does not establish general semantic localization reliability
or a general latency improvement. Deterministic hashes validate identity, not
entailment. Saved material may be provider highlights or retained views rather
than the entire original publication; the Reader discloses this distinction.
The subsequent presentation changes were verified offline as described above;
the two ordinary observations remain evidence for the earlier runtime revision.

`CURRENT.md` and `docs/architecture/RESEARCH.md` describe the resulting state.
The branch is published for review in PR #672. Merge and historical-checkout
aftercare were not performed.

## Local evidence and handoff

Exact public/synthetic evidence is preserved outside Git in:

- `C:\tmp\scryraven-citation-reader-product-01-20261007\`: ordinary session database,
  body-free turn diagnostics, normalized observer evidence, mechanics reports,
  browser check results and screenshots. No raw provider payloads or credentials.
- Phase `local-evals/candidates/citation-reader-product-01-web/` and
  `local-evals/candidates/citation-reader-product-01-pdf/`: sanitized candidates,
  exact selected Evidence, answer, coordinates, hashes and provenance. These are
  phase-local because the canonical corpus in the primary checkout is excluded.
- `C:\tmp\scryraven-citation-reader-presentation-fix-20261007\`: offline browser
  checks, screenshots, standalone HTML and exact expectations derived from the
  already retained turns. These local artifacts are not tracked or uploaded.

Review PR #672 against the exact baseline. Publication and the focused presentation
fix were explicitly authorized; this bundle does not grant merge authority.
