# ScryRaven

ScryRaven researches public-web factual questions with related answer needs and
writes one cited answer from source material it receives and reads. Research finds
promising sources with Exa Search and selects useful extractive highlights for
Analyst. Missing context can trigger acquisition of fuller source text. Analyst
interprets support, qualifications and gaps; Author writes from its findings, short
exact support anchors and supporting material.

See `CURRENT.md` for implementation, demonstrations and limits. `PRODUCT.md` owns
approved product intent.

## Run

Use Python 3.10 or later from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m scryraven "What is the maximum allowed weight of a ten-pin bowling ball?"
```

The process needs `OPENAI_API_KEY` and `EXA_API_KEY`. The product does not load
`.env`. Optional independent role configuration:

| Variable | Default |
| --- | --- |
| `SCRYRAVEN_FAST_MODEL` | `gpt-5.6-luna` (Research and Author) |
| `SCRYRAVEN_FAST_REASONING` | `medium` |
| `SCRYRAVEN_SMART_MODEL` | `gpt-5.6-luna` (Analyst) |
| `SCRYRAVEN_SMART_REASONING` | `medium` |

An empty reasoning value omits that API option. One OpenAI Responses transport
uses structured output and Pydantic parsing. No model has built-in web tools.

## Acquisition and evidence

The fixed path is Exa Search (`auto`, six results, query-guided highlights up to
4,000 characters per result), then Exa Contents text only when context is missing
(`verbosity: full`, `maxAgeHours: 0`). Generated summaries and answers are excluded.
Search metadata remains navigation. Actual highlights may support only meaning
established by their text; extractive does not mean complete, contiguous or free
of extraction artifacts. Authority, applicability and sufficiency are judgments.

Research selects highlights in its existing navigation call, without another
relevance call or full-text acquisition. Fuller context is appropriate for missing
definitions, conditions, captions, chronology, connected passages, version context,
or broader page/discussion questions. `context_needed` records the concrete gap.
An older governing source can remain applicable; unrequested editions and
hypothetical exceptions do not automatically expand a narrow question.

Successful full-text acquisitions are immutable and retained in run-local memory.
Bodies up to 32,000 characters are exposed directly. Larger sources produce one
mechanical packet of exact slices up to 32,000 characters, using structure, lexical
matches and recoverable excerpt phrases. One optional expansion up to 48,000
characters addresses a concrete gap. These are provisional economics choices,
not semantic sufficiency thresholds. There is no conversational document browser.

Different material versions at the same exact URL remain immutable and share
source identity. Views carry exact parent bounds; highlights never acquire guessed
offsets. Multiple versions/views are not independent corroboration. Analyst and
Author receive selected context grouped by source. Short support quotes help
preserve significant quantities, conditions, time comparisons and epistemic
language through paraphrase. Quote/reference validation does not decide meaning.
Citations resolve to the publication URL.

The existing provisional loop permits three Analyst assessments, each preceded by
up to six navigation actions. Each semantic need allows two Search calls initially.
Actual evidence assessed by Analyst and a specific unresolved same-need gap can
earn one further round of two calls; there is no third round. Unused initial
allowance expires. Assessment of new evidence in round two closes remaining search
allowance for that need. Existing candidate reads survive. Failures spend search
allowance; empty or omitted material cannot earn a return. These are ceilings,
not targets. Need identity remains a semantic judgment.

Research can nominate useful explicit links from acquired material. Mechanics
validate occurrence and URL syntax, including escaped Markdown punctuation.
Invalid optional links are rejected individually. There is no automatic crawling;
the linked source must be acquired before it supports findings.

## Observations and checks

Answers appear on stdout. `--trace` adds compact diagnostics on stderr: model
roles, Research choices, source identities/sizes, acquisitions, packet bounds,
selected material, Analyst findings/anchors/gaps and citation resolution. Per-stage
body characters include repeated submissions; they are not tokens or dollars.
Raw payloads, credentials and hidden reasoning are excluded.
`--trace-evidence` also exposes exact selected supporting material and provenance;
unseen full parents remain out of the trace. Use public questions for observations.

Execution errors exit 1 with a safe stage/code. Supported, partial and unable
postures exit 0. An honest limit is not proof of nonexistence.

Agents must use the existing doorman for credentialed commands and must not read
`.env` or keys. An operator may configure `.env` using `.env.example`. For an
authorized observation use fresh external output filenames:

```powershell
New-Item -ItemType Directory -Force C:\tmp\scryraven-observation | Out-Null
python scripts/run_brokered_command_once.py --repo-root C:\Users\aidan\ScryRaven --repo-env --stdout C:\tmp\scryraven-observation\answer.txt --stderr C:\tmp\scryraven-observation\trace.txt --status C:\tmp\scryraven-observation\status.json --timeout-seconds 1200 --target-current-python -- -m scryraven "What is the maximum allowed weight of a ten-pin bowling ball?" --trace
```

The doorman owns only secret custody and process plumbing; the product does not
import it. Keep observation packets outside the repository.

```powershell
python -m pytest -q
python -m ruff check .
pre-commit run --all-files
```

Offline tests inject external transports into the ordinary application and do not
prove model judgment. CI runs offline without provider credentials/calls. Persistent
sessions, scheduling, generalized routing/recovery, vector databases, semantic
compression and calculation remain absent. Old providers are not dormant fallbacks.
