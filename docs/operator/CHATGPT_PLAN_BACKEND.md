# Optional production ChatGPT-plan transport

`OpenAIModel` keeps the API backend as its default. Select the optional plan
backend explicitly when constructing the ordinary production model:

```python
from scryraven.model import OpenAIModel
from scryraven.research import run

model = OpenAIModel(backend="chatgpt_plan", plan_account="personal")
result = run("Your research question", model=model)
```

Model-role settings, Research/Answer instructions, strict schemas, exact source custody, deterministic Calculate and native Research continuation and publication remain the
ordinary production implementation. There is no API-key fallback; plan mode
does not read `OPENAI_API_KEY`. `plan_auth=...` permits injection of the same
approved Auth implementation for brokered operation and offline tests. Production
runtime imports no experimental harness or evaluation module.

Selection is currently programmatic. The ordinary CLI has no backend flag,
Reading Room has no visible selector, and `model_roles.json` has no transport
field. Unmodified launches remain API-default. Existing ResearchSession and
Reading Room `create_app(session_options={"model": model})` injection can use the
selected model. The sign-in/models commands below configure access; they do not
select the backend for ordinary research launches.

For isolated local dogfooding, the development launcher explicitly injects
`OpenAIModel(backend="chatgpt_plan", plan_account="personal")` through the ordinary
Reading Room's `session_options`. In Windows PowerShell, from the repository:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\forensic-reading-room.ps1 -PrepareOnly 2>&1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\forensic-reading-room.ps1 -Port 7332 2>&1
```

`-PrepareOnly` makes a fresh manifest without opening credentials or starting a
server. A real launch uses the existing credential doorman and the approved
external `credentials.env` source. The child removes `OPENAI_API_KEY`, requires
nonblank Exa configuration before constructing the model or web server, and
reports optional Serper/LinkUp configuration only as booleans. Missing Exa or an
unavailable plan implementation fails closed with a fixed safe diagnostic.
Startup never authenticates, sends inference or calls an acquisition provider;
the first user question exercises account/model access. The selected plan is the
ChatGPT-plan allowance, with no guaranteed Codex-only credit bucket or reported
billing amount.

Each unique run under `C:\tmp\scryraven-forensic` retains `sessions.sqlite3`,
body-free `turns.jsonl`, source-bearing `observer.jsonl` and `manifest.json`.
The child records its actual checkout revision, effective role configuration,
backend, account label, API-fallback-disabled identity, credential-presence
booleans and server PID. The manifest becomes `ready` only after that child's
server binds. The launcher verifies a localhost HTTP GET before printing ready.
It does not stop another server on a conflicting port; choose another `-Port`.

The launcher waits for the broker, whose default timeout is 86,400 seconds
(`-TimeoutSeconds` can set another finite duration). Broker stdout/stderr are
sanitized and saved at process exit. Startup failure also prints the fixed broker
status when available. A 30-second failed readiness check terminates only the
process tree created by that launch. To stop a successful run, use its printed
command, substituting its exact run directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop-forensic-reading-room.ps1 -RunDirectory 'C:\tmp\scryraven-forensic\EXACT-RUN-NAME' 2>&1
```

The stop script verifies the recorded PID's entrypoint and exact run argument
before stopping it. It preserves all run files. Ordinary non-forensic launches
retain their existing API default and observability behavior.

The base requirements provide urllib3 for both transports' response-body deadline
watchdog. JWT and cryptography authentication dependencies remain optional here.

Install optional dependencies and use the existing official sign-in flow:

```powershell
python -m pip install -r requirements.txt -r requirements-chatgpt-plan.txt
python -m scryraven.chatgpt_plan sign-in --account personal
python -m scryraven.chatgpt_plan models --account personal
```

An already registered `personal` account is reused. The shared implementation
retains the existing Windows CurrentUser DPAPI vault and location under
`%LOCALAPPDATA%\ScryRaven\continuing-worker-chatgpt-plan\`; no credential
migration or second authentication system is introduced. Do not inspect that
vault or print tokens. Agent-operated credentialed commands use the existing
doorman described in `BROKERED_COMMAND_SESSION_OPERATOR_FLOW.md`. This setup
command does not perform inference.

The [official plan preview requirements](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
require streaming with `store=false` and do not support `max_output_tokens`.
The explicit plan backend therefore omits the native 12,000-token output cap;
the ordinary API backend keeps it. This is an operational difference, not an
equivalent cap. Plan mode also omits API explicit cache extensions and service
overrides and promises no equivalent caching or service tier. Keep ordinary
wall-clock and physical-request limits; local SSE framing limits do not limit
server generation, hidden reasoning or account consumption.

Function definitions use the supported developer `additional_tools` input item.
The calculator keeps its original name, strict argument schema and local
executor. Full completed output/function/reasoning items are replayed only in
memory for dependent continuations with `store=false`; no raw envelope or opaque
reasoning content is persisted by the transport. It accepts text reconstructed
from identified completed stream items when the completed terminal has an empty
output list. Conflicting, incomplete, failed or interrupted streams grant no
publication authority. Ordinary final-message selection and validation still
decide whether a completed response is usable.

Usage observers receive only safe provider-reported counters. Absent counters
remain `None`, including on failures; they are never treated as zero. The
transport has no automatic retry or billing fallback. Account allowance/credits
and model access remain account governed. See the official
[completion contract](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
and [function-call packaging](https://developers.openai.com/api/docs/guides/tools-tool-search#add-tools-at-a-specific-point-in-the-input).
