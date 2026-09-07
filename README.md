# ScryRaven

ScryRaven researches public-web factual questions with several related answer needs
and writes one cited answer from material it actually acquires. Research first
identifies the needs and likely authoritative sources, then chooses Linkup searches
and directly Fetches useful material. It selects relevant acquisitions for Analyst,
which assesses each requested portion and can return one unresolved need for further
research. Author receives supported findings, limitations, and selected evidence.
Supported portions survive even when another portion remains unresolved.
Discovery snippets never become answer evidence. Source authority is contextual;
useful secondary material remains eligible.
Research also distinguishes the applicable period or edition from recent publication;
an older governing source can be the right source for a current question.

See `CURRENT.md` for implemented behavior, ordinary product demonstrations,
offline coverage, and remaining limitations.

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
| `SCRYRAVEN_FAST_MODEL` | `gpt-5.4-mini` (Research and Author) |
| `SCRYRAVEN_FAST_REASONING` | `medium` |
| `SCRYRAVEN_SMART_MODEL` | `gpt-5.4` (Analyst) |
| `SCRYRAVEN_SMART_REASONING` | `medium` |

An empty reasoning value omits that API option. Models and reasoning settings
are provisional and centralized in `scryraven/model.py`. The single OpenAI
Responses transport uses structured output with Pydantic for mechanical parsing.
No model has built-in web tools; source acquisition goes through Linkup.

An answer or honest limitation appears on stdout. `--trace` adds compact JSON
diagnostics on stderr: model roles, provisional answer needs, authority and temporal expectations,
revised orientation, search/selection summaries, discovery/read outcomes, source URLs,
acquired and omitted evidence IDs, Analyst component coverage/support/gaps, Author selection,
citation resolution, and terminal stage/reason. Citation failures identify the
rejected pattern, position, and evidence aliases without retaining the rejected
answer. Invalid Research selections report the validation cause and current valid
candidate aliases. Research gets one local correction opportunity before a repeated
invalid selection terminates the run; rejected selections never reach Fetch.
The trace omits raw prompts, provider payloads, source bodies, credentials, and
hidden model reasoning. Trace text can contain the user's question and source URLs;
use public questions for observations.

For completed-run support inspection, `--trace-evidence` includes the exact acquired
text of Analyst-selected sources in stderr diagnostics. It uses the same run and
makes no extra source requests. Keep this optional material outside the repository
when capturing a product observation through the doorman.

Execution errors exit with code 1 and a safe stage/code. Complete answers, partial
answers, and honest limitations exit with code 0; the trace distinguishes
supported, partial, and unable postures.
The provisional local loop allows three research passes of up to six navigation
actions each. Analyst still judges acquired evidence at a navigation bound.
Exhaustion is a limitation of the run, never proof that an answer does not exist.
Successful acquisitions remain in memory with stable source IDs. Research selects
relevant material; later Analyst passes retain prior support and useful conflict
context. Author receives only the sources supporting the selected findings.

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
from live demonstrations and limitations. Persistent sessions, scheduling, UI,
and generalized recovery remain unimplemented. The old
v1 implementation survives only in Git history, not as an active fallback.
