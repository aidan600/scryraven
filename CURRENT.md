# ScryRaven Current Truth

Status: first single-component walking skeleton implemented; two-topic live completion demonstrated
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

Two different questions completed the ordinary CLI on the same final runtime
revision, d969088577206421b931231cd331183af4f1f40d, using real model calls,
Linkup discovery, and Fetch through the retained doorman. Both exited 0 with
posture supported, Analyst-selected acquired material reaching Author, successful
deterministic citation resolution, and a user-visible cited answer. Subsequent
publication changes are factual documentation only.

- Chess: "When a pawn reaches the farthest rank in chess, what pieces may it
  promote to?" Research selected C2, C3, and C6 and acquired three sources.
  Analyst selected E1, E2, and E3; Author cited all three for queen, rook, bishop,
  or knight of the same color. The acquired passages visibly support this rule
  and the answer's additional promotion/underpromotion explanation.
  E1: https://grokipedia.com/page/Promotion_(chess)
  E2: https://kingdomofchess.com/pawn-promotion-in-chess/
  E3: https://greenchess.net/rules.php?item=promotion
- Bowling: "What is the maximum allowed weight of a ten-pin bowling ball?"
  A failed C1 read created no evidence; C2, C3, and C4 produced E1, E2, and E3.
  Analyst selected all three, and Author emitted a cited 16-pound (7.26 kg)
  maximum. The acquired passages support the limit and the answer's additional
  historical/rationale claims. Those extra claims are secondary-source material,
  not a demonstration of primary-source quality.
  E1: https://bigleagueshirts.com/blogs/resources/how-do-you-choose-the-best-bowling-ball-weight
  E2: https://www.flybowling.com/blog/the-ultimate-guide-to-bowling-ball-dimensions-in-2026.html
  E3: https://efx.co/blogs/news/what-is-the-heaviest-bowling-ball-weight-guide

Evidence aliases are local to each run. Every rendered citation matched a directly
acquired, selected source URL; no unresolved alias remained. The selected acquired
snapshots were inspected from sanitized --trace-evidence output outside the repo,
without additional source requests. Neither final run needed Analyst follow-up or
candidate-selection correction. The current citation repair is now exercised live.

Research rejects malformed or unknown read selections before any Fetch and supplies
current valid aliases for one local correction by Research. Repeated invalid
selection fails clearly. Code does not guess replacement candidates or judge
relevance. Correction, repeated failure, and stale aliases from an earlier discovery
set are covered offline through the actual application; correction was not needed
in the final live observations. Safe diagnostics distinguish empty, malformed, and
unknown aliases without retaining rejected model output.

Earlier ordinary live evidence demonstrated a natural Analyst -> Research adaptive
cycle on bowling: Analyst requested the total-weight rule after seeing static-weight
material, Research read USBC manuals, and Author cited the selected support. That
observation used 5b62ff13364db1e625f22074a82b1bc4b2465871, before the final FAST-role
configuration. Final offline adaptive coverage preserves the original question and
acquired snapshots across follow-up and includes correction of a stale candidate
alias. These observations do not establish broad live reliability.

The whole-system review retained three semantic responsibilities and ordinary
run-local mechanics. The explicit citation grammar validates selected IDs before
rendering source metadata; offline adversarial coverage includes grouped and
malformed aliases, bracketed titles/prose, and invalid link/code presentation.
The offline suite, Ruff, pre-commit, and production import/parse checks pass.

Completion used two of the five newly authorized PRODUCT invocations, bringing the
historical work-item total to twelve. Live execution stopped after both topics
succeeded. No live accounting subsystem or next capability was added. Pulse files
remain outside the repository.

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
  --trace-evidence optionally adds the exact selected acquired snapshots for
  support inspection after completion, without additional source requests.
- Full fetched text is kept in memory and sent to Analyst; large corpora can
  exceed model context. No semantic reduction or persistent evidence system exists.
- Provider failures and malformed model/reference responses are reported with
  safe stage/code errors. Malformed structured output gets one local retry with
  safe schema-field diagnostics; invalid read selections get one local correction
  with current candidate aliases. Research can choose another search/read within
  its loop; there is no general retry/fallback/recovery system.
- Source interpretation and faithful writing remain model judgments. Offline
  mechanics and two successful live topics do not establish broad answer quality.
  Both final runs used secondary sources, and answers can include more explanation
  than the narrow question requires.
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
