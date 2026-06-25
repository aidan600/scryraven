# Broker Reactivation Runbook

Status: local operator guidance for the private ScryRaven live broker. This is
documentation only; it does not authorize committing private broker files,
tokens, provider keys, `.env` contents, raw prompts, raw provider payloads, raw
model responses, private logs, DB rows, cache rows, or full traces.

Known local broker script:

```text
C:\Users\aidan\ScryRavenLiveBroker\scryraven_live_broker.py
```

Known local broker URL:

```text
http://127.0.0.1:8765/run
```

Tracked broker client:

```text
scripts/request_live_validation_broker.py
```

Shared validation-profile source:

```text
core/validation_profiles.py
```

Required local environment variables:

```text
SCRYRAVEN_BROKER_TOKEN
SCRYRAVEN_BROKER_MAX_RUNS
```

## Restart Broker

Run from a private PowerShell shell that already has the one-shot broker token
loaded. Do not paste the token into chat or commit it.

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

$env:SCRYRAVEN_BROKER_MAX_RUNS = "1"
py C:\Users\aidan\ScryRavenLiveBroker\scryraven_live_broker.py
```

If the broker runs in a separate terminal, keep that terminal open while making
the broker request.

## Check Job Id

Before asking Codex to run the tracked client, confirm the private broker copy
contains the intended allowlisted job id:

```powershell
$JobId = "<job-id>"
Select-String -Path C:\Users\aidan\ScryRavenLiveBroker\scryraven_live_broker.py -Pattern $JobId -SimpleMatch
```

If the command returns no match, do not run the broker client. It would fail
closed as `unknown_job_id`.

## Broker Client Command Shape

Run from the repository root in a shell that can see `SCRYRAVEN_BROKER_TOKEN`:

```powershell
py scripts\request_live_validation_broker.py `
  --job-id <job-id> `
  --profile AG-LIVE-SMOKE `
  --confirm-live-provider-call `
  --output output\<sanitized-broker-response>.json
```

The tracked client sends an `approved_validation_profile` request shape derived
from `core/validation_profiles.py`. The private broker should treat `job_id` as
its one-run allowlist/fuse and the profile request as product-owned constraints:
profile name, query/domain/mode constraints, `RunConfig.cap_policy` values,
retention posture, packet schema, and expected packet criteria. The private
broker must not accept arbitrary commands from the client.

Use only sanitized broker output under `output/`. Do not paste or commit tokens,
secrets, `.env` contents, provider keys, raw prompts, raw provider payloads, raw
model responses, private logs, DB rows, cache rows, or full traces.

## Codex Acknowledgement Template

Paste this shape to Codex after the private broker has been manually updated and
restarted:

```text
Broker acknowledgement for <phase/job>:

The private broker is running locally at:
http://127.0.0.1:8765/run

Broker script:
C:\Users\aidan\ScryRavenLiveBroker\scryraven_live_broker.py

Use only the tracked client:
py scripts\request_live_validation_broker.py --job-id <job-id> --profile <AG-LIVE-profile> --confirm-live-provider-call --output output\<sanitized-broker-response>.json

Budget:
- max broker requests: 1
- max model/provider/search/fetch/retrieval calls: <phase-approved budget>
- retries: 0

Rules:
- Do not read `.env`.
- Do not print or request secrets.
- Do not call provider APIs directly.
- Do not run search/fetch/retrieval unless explicitly budgeted.
- Do not accept arbitrary commands from the tracked client.
- Dispatch only approved validation profiles from `core/validation_profiles.py`.
- Use only sanitized broker output under `output/`.
- If the broker returns `unknown_job_id`, token error, missing config, max-runs exhausted, or any provider/model error, fail closed and do not retry.
```

## Fail Closed Rules

Fail closed and do not retry when any of these are true:

- `SCRYRAVEN_BROKER_TOKEN` is missing from the shell running the tracked client.
- The job id is not allowlisted in the private broker.
- The broker returns `unknown_job_id`, token error, missing config, or
  `max_runs_exhausted`.
- The broker reports any provider/model/search/fetch/retrieval error.
- The requested action would require direct provider API calls from Codex.
- The requested action would require reading `.env`, secrets, provider keys,
  private logs, DB/cache rows, raw prompts, raw provider payloads, raw model
  responses, or full traces.

Codex may not see `SCRYRAVEN_BROKER_TOKEN` if it runs in a different shell from
the broker or the operator terminal. If Codex cannot see the token, either run
the broker client manually from the token-loaded shell or relaunch Codex from
that shell. Do not paste the token into chat.

Private broker files are local/private operational files and should not be
committed to the ScryRaven repository.
