# ScryRaven Current Truth

Status: first single-component walking skeleton implemented; live acceptance incomplete
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
The retained doorman and Linkup transport tests pass.

The required two-topic live acceptance condition has not been met. Eight ordinary
CLI invocations used the retained doorman with sanitized output outside the repo;
that work item's live execution allowance is exhausted. There is no product
accounting subsystem and no further live execution is authorized by that brief.

On the last live-tested revision, 512a3bb2683f3fb6eed10b03aa57ef2ff9a09227:

- Bowling completed with a cited 16-pound maximum from three directly acquired
  secondary sources (Big League Shirts, Flybowling, and EFX). Analyst selected
  all three; a failed fourth read created no evidence. No Analyst follow-up was
  needed. The answer also included secondary-source historical/rationale claims
  beyond the question. Independent reading of the cited EFX page confirms those
  claims are present there; that does not establish their primary-source quality.
- Chess acquired two sources (chess-teacher.com and ppqty.com). Analyst supported
  queen/rook/bishop/knight and handed both snapshots to Author, but citation
  resolution failed with malformed_citation_reference. No user-facing answer was
  emitted. A successful cited transfer-topic answer has not been demonstrated.

Earlier live evidence demonstrated a complete natural Analyst -> Research adaptive
cycle on bowling: initial material concerned static weight, Analyst requested the
total-weight rule, Research directly read USBC manuals, and Author cited selected
support. That observation used 5b62ff13364db1e625f22074a82b1bc4b2465871, before the
final Research prompt/FAST-role change. A separate earlier chess run returned an
honest run-bounded limitation after Research prematurely stopped without reads.
Those observations do not establish the final configuration's reliability.

After live execution stopped, an offline scenario reproduced the citation failure
code with a bracket-ended source title. The final code validates unresolved Author
markers before rendering escaped source metadata, preserving valid bracketed titles
and still rejecting broken aliases. The full offline suite and repository hooks
pass. This final citation repair has not been exercised live, and its causal role
in the observed chess failure is not proved because raw Author output was not kept.

Two independent source checks were used: the USBC manual confirms the 16.00-pound
rule; the cited EFX article supports the bowling answer's secondary-source claims.
Neither check was inserted into product evidence. Pulse files remain outside the
repository. Final relevant PRODUCT evidence remains outstanding. The remaining human
decision is whether to license additional live verification of this same work item;
no next phase has begun.

## Provisional implementation choices and limitations

- One OpenAI Responses transport with configurable FAST and SMART model roles;
  defaults are gpt-4.1-mini without a reasoning option for Research and Author,
  and gpt-5.4/medium for Analyst.
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
