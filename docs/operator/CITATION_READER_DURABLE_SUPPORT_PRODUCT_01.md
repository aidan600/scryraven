# Citation Reader / Durable Support Product 01

OUTCOME: Met over the authorized bounded implementation and PRODUCT observations.

## Baseline and tested revision

- Phase worktree: `C:\Users\aidan\sr-phases\citation-reader-durable-support-product-01`
- Branch: `codex/citation-reader-durable-support-product-01`
- Exact merged baseline: `6b3dac8761133dd27868852cd7d2337a9b9e9883` (PR #671).
- Runtime tested: `30889acc1783608dae653e8e05d0b023fe5e1ae7`.
- Later changes are documentation and evidence reporting only.

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
uncredentialed inspection server uses port 7445.

## Offline verification

The full suite passed: `823 passed`. The only warning was inability to write the
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
No runtime changes were made after the tested revision.

`CURRENT.md` and `docs/architecture/RESEARCH.md` describe the resulting state.
Push, PR creation, merge and historical-checkout aftercare were not performed.

## Local evidence and handoff

Exact public/synthetic evidence is preserved outside Git in:

- `C:\tmp\scryraven-citation-reader-product-01-20261007\`: ordinary session database,
  body-free turn diagnostics, normalized observer evidence, mechanics reports,
  browser check results and screenshots. No raw provider payloads or credentials.
- Phase `local-evals/candidates/citation-reader-product-01-web/` and
  `local-evals/candidates/citation-reader-product-01-pdf/`: sanitized candidates,
  exact selected Evidence, answer, coordinates, hashes and provenance. These are
  phase-local because the canonical corpus in the primary checkout is excluded.

Review this local branch against the exact baseline. Publication requires explicit
human authority; this bundle does not grant merge authority.
