# ScryRaven Current Truth

Status: first single-component walking skeleton implemented
Repository: aidan600/scryraven
Preferred local checkout: C:\Users\aidan\ScryRaven

## Approved and implemented product state

PRODUCT.md remains the approved product charter. The ordinary entrypoint is:

    python -m scryraven "What is the maximum allowed weight of a ten-pin bowling ball?"

The implemented path is Research -> Analyst -> Author -> deterministic citations.
Research chooses and revises Linkup standard searches, interprets discovery clues
as navigation, selects sources, and directly reads them with Linkup Fetch.
Successful reads create immutable run-local evidence snapshots with stable IDs,
source URLs, display titles, and the full readable material returned by Fetch.
Discovery context is never part of the evidence passed to Analyst or Author.

Analyst semantically interprets the acquired collection with a stronger model,
returns supported/research_needed/unable, connects findings to support IDs, and
selects active evidence IDs. A semantic next_need returns to Research; later
analysis sees the expanded collection, including the original snapshots.
Author receives the question, supported findings or limitation, relevant Analyst
explanation, and only selected supporting snapshots. Mechanical code checks
references and renders source links; it does not judge whether passages prove
claims. Unsupported outcomes preserve uncertainty, including when a local
execution bound ends research.

## Verification frontier

The actual application path has focused offline coverage for direct acquisition,
separation of discovery and evidence, selected Author material, successful cited
answers, Analyst-directed follow-up, revised poor discovery and failed reads,
honest limitations, execution bounds, invalid references, model failures, and CLI
use of the same application with real Linkup adapters and injected external calls.
The retained doorman and Linkup transport tests pass. No live product result has
yet been demonstrated on this implementation.

## Provisional implementation choices and limitations

- One OpenAI Responses transport with configurable FAST and SMART model roles;
  defaults are gpt-5.4-mini/low for Research and Author, gpt-5.4/medium for Analyst.
- Small responsibility prompts, Pydantic structured-response parsing, and ordinary
  sequential functions. Three research passes and six navigation actions per pass
  are provisional local defaults, not product restrictions or acceptance criteria.
- Optional --trace emits compact run-local diagnostic JSON on stderr: stage,
  research need, discovery/read outcomes, acquired IDs/URLs/counts, Analyst
  decisions/support/gaps, Author selection, citation resolution, and terminal
  posture/reason. It omits raw prompts, source bodies, provider payloads, and
  hidden model reasoning. It can include the public question and source URLs.
- Full fetched text is kept in memory and sent to Analyst; large corpora can
  exceed model context. No semantic reduction or persistent evidence system exists.
- Provider failures and malformed model/reference responses are reported with
  safe stage/code errors. Malformed structured output gets one local retry with
  safe schema-field diagnostics. Research can choose another search/read within
  its loop; there is no general retry/fallback/recovery system.
- Source interpretation and faithful writing remain model judgments. Offline
  mechanics alone do not establish broad live answer quality.
- Multi-component research, scheduling, parallel research, persistent sessions,
  resumability, UI, provider routing, and generalized recovery are unimplemented.

## Retained boundaries

The general doorman at scripts/run_brokered_command_once.py remains operator-only
credential custody and process plumbing; product code does not import it.
Agent-operated credentialed commands use it and put sanitized outputs outside the
repository. No live-run accounting, token/cost authority, or persistent diagnostic
system is part of the product. CI remains pre-commit plus offline pytest without
live calls or provider secrets.

The old v1 architecture remains removed from the active tree. Git history and
v1-final-implementation preserve it; no old orchestration, authority, evidence
ledger, final-answer packet, scheduler, or fallback tree has been recreated.
The obsolete reset test forbidding an executable CLI has been removed.
