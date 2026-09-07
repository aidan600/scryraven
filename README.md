# ScryRaven

ScryRaven answers straightforward single-component public-web factual questions
from source material it acquires and interprets. Research chooses Linkup standard
searches and directly Fetches useful sources. Analyst interprets that material,
selects support, and can send an unresolved semantic need back to Research.
Author writes from the selected findings and evidence; code resolves citations.
Discovery snippets never become answer evidence.

The walking skeleton is implemented, but its required two-topic live acceptance
is incomplete. See `CURRENT.md` for the demonstrated frontier and the final
citation repair that has only offline verification.

## Run

Use Python 3.10 or later from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m scryraven "What is the maximum allowed weight of a ten-pin bowling ball?"
```

The product process needs `OPENAI_API_KEY` and `LINKUP_API_KEY` in its environment.
It does not load `.env` itself. Optional role configuration:

| Variable | Default |
| --- | --- |
| `SCRYRAVEN_FAST_MODEL` | `gpt-4.1-mini` (Research and Author) |
| `SCRYRAVEN_FAST_REASONING` | empty (omitted) |
| `SCRYRAVEN_SMART_MODEL` | `gpt-5.4` (Analyst) |
| `SCRYRAVEN_SMART_REASONING` | `medium` |

An empty reasoning value omits that API option. Models and reasoning settings
are provisional and centralized in `scryraven/model.py`. The single OpenAI
Responses transport uses structured output with Pydantic for mechanical parsing.
No model has built-in web tools; source acquisition goes through Linkup.

An answer or honest limitation appears on stdout. `--trace` adds compact JSON
diagnostics on stderr: research needs, discovery/read outcomes, source URLs,
acquired evidence IDs/counts, Analyst decisions/support/gaps, Author selection,
citation resolution, and terminal stage/reason. It omits raw prompts, provider
payloads, source bodies, credentials, and hidden model reasoning. Trace text can
contain the user's question and source URLs; use public questions for observations.

Execution errors exit with code 1 and a safe stage/code. Supported answers and
honest limitations exit with code 0; the trace distinguishes their posture.
The provisional local loop allows three research passes of up to six navigation
actions each. Analyst still judges acquired evidence at a navigation bound.
Exhaustion is a limitation of the run, never proof that an answer does not exist.

## Agent-operated credentialed runs

Agents must use the retained general doorman; they must not read `.env` or keys.
An operator may prepare `.env` using `.env.example`. The doorman injects it only
into the child process and captures sanitized stdout/stderr outside the checkout.
For an authorized product observation, choose fresh output filenames:

```powershell
New-Item -ItemType Directory -Force C:\tmp\scryraven-observation | Out-Null
python scripts/run_brokered_command_once.py --repo-root C:\Users\aidan\ScryRaven --repo-env --stdout C:\tmp\scryraven-observation\answer.txt --stderr C:\tmp\scryraven-observation\trace.txt --status C:\tmp\scryraven-observation\status.json --timeout-seconds 1200 --target-current-python -- -m scryraven "What is the maximum allowed weight of a ten-pin bowling ball?" --trace
```

The doorman is operator plumbing and is not imported by the product. Do not
commit private environments, provider payloads, or product-pulse outputs.

## Offline checks and current scope

```powershell
python -m pytest -q
python -m ruff check .
pre-commit run --all-files
```

Tests inject external transports into the same application used by the CLI.
CI runs pre-commit and offline pytest without provider credentials or live calls.
`PRODUCT.md` owns approved intent; `CURRENT.md` distinguishes implemented behavior
from live demonstrations and limitations. Multi-component research, persistent
sessions, scheduling, UI, and generalized recovery remain unimplemented. The old
v1 implementation survives only in Git history, not as an active fallback.
