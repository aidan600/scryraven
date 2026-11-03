# Private dogfood deployment 01

This guide covers offline deployment readiness for the product owner and two
invited testers. The hosted application has passed offline integration and browser
checks. Live provider/model compatibility, custom-domain TLS, Access login,
Railway volume behavior and backup recovery still require operator verification
during activation.

## Release and topology

Use one Railway Hobby service, one replica, one mounted persistent volume, and
one Python process. Configure the service in the Railway dashboard using the
settings below. `python -m scryraven.wsgi` runs Waitress with
eight HTTP threads by default; ResearchJobManager still has two research workers
and eight waiting admissions. Do not launch multiple WSGI processes, replicas,
workers, a development reloader or a second Reading Room against this database.
The existing OS database-owner lock prevents overlapping managers; startup fails
instead of interrupting another live owner. Restart marks outstanding work
interrupted and never automatically repeats model or acquisition calls.

Promote a reviewed full Git revision explicitly, including the Run Settings and
private hosted deployment changes. Use an extracted `git archive` of
that exact revision as the deployment source. Record the source SHA, built image
digest when available, dependency versions and Railway deployment ID in the
private operator record. Do not upload the ordinary checkout containing ignored
personal material. No build needs `.git`,
local evaluation artifacts, local credentials, a personal model file or a personal
Reading Room database. Docker's allowlisted context excludes databases/logs/keys.

Install Python 3.13 and `requirements-hosted.txt` (which includes the ordinary API
requirements). The Dockerfile does this. Local personal-plan/OpenRouter launch
and Run Settings remain available through the existing local entrypoint.

## Required Railway dashboard settings

Checked against official Railway documentation on November 2, 2026. Legacy
[Config as Code](https://docs.railway.com/config-as-code) is unavailable to new
services and ends for existing users on December 1, 2026. The obsolete file is
removed; this service uses dashboard configuration, with no Config as Code or
TypeScript infrastructure project.

Create an **Empty Service** in the Hobby project. Leave its GitHub repository
source disconnected and PR environments disabled. Configure these values before
the first application deployment:

| Dashboard location | Required setting |
| --- | --- |
| Service **Settings > Build** | Build the repository-root `Dockerfile`; Railway detects it automatically. Keep the source root at `/` and leave Custom Build Command empty. Confirm Dockerfile use in the build log. |
| **Settings > Deploy > Custom Start Command** | `python -m scryraven.wsgi` (also the Dockerfile's CMD). |
| **Settings > Deploy > Pre-Deploy Command** | Empty; the app initializes/migrates SQLite at startup with the volume mounted. |
| **Settings > Deploy > Healthcheck Path** | `/healthz`. |
| **Settings > Deploy**, healthcheck timeout | **60 seconds**. Leave Railway's supplied `PORT` available to the app. |
| **Settings > Scale > Regions** | One region and **one replica total**. Do not add replicas or additional application services. |
| Service **Settings**, restart policy | **On Failure**, maximum **5 restarts**. Hobby permits this finite policy. |
| **Settings > Deploy > Serverless** | **Enable Serverless off**; keep the service running for research jobs and hourly diagnostic retention. Leave any cron schedule empty. |
| Project canvas/command palette, **Create a volume**, select this service | One **new empty volume**, mount path **`/data`**. In the service **Variables** tab set `SCRYRAVEN_DATA_DIR=/data`, plus the protected variables below. |
| **Settings > Source** | No GitHub source for this manual-upload service. If a repository is already connected, use **Disable** for autodeploy; do not deploy from a moving branch tip. |

Railway documents [Dockerfile detection](https://docs.railway.com/builds/dockerfiles),
[start commands](https://docs.railway.com/deployments/start-command),
[build/deploy controls](https://docs.railway.com/overview/advanced-concepts),
[health checks](https://docs.railway.com/deployments/healthchecks),
[restart policies](https://docs.railway.com/deployments/restart-policy),
[Serverless controls](https://docs.railway.com/pricing/cost-control), and
[volume attachment](https://docs.railway.com/volumes). Railway supplies
`RAILWAY_VOLUME_MOUNT_PATH` automatically after attachment; do not substitute a
manually invented value for a real volume. Hosted startup checks the data path
against that mount. Volume-backed redeployments can have brief downtime.

During separately authorized activation, review the dashboard's staged changes
with **Details**. Hold **Alt** while clicking **Deploy** to commit settings
without triggering a redeploy. Then manually upload only the extracted reviewed
archive with `railway up <archive-directory> --path-as-root`, explicitly selecting
the existing project, service and environment. This command
builds and deploys immediately; it is not a preparation-only command. Repeat the
same review and manual upload for each promoted revision. No merge or push to
`main` should trigger deployment. Railway's **Deploy Latest Commit** command uses
the connected branch's current tip, so it is not this revision-promotion path.
See [manual source upload](https://docs.railway.com/cli/up),
[staged settings](https://docs.railway.com/deployments/staged-changes), and
[autodeploy controls](https://docs.railway.com/deployments/github-autodeploys).
After activation, verify the effective settings in the deployment details and
record them with the promoted SHA. Offline preparation does not apply dashboard
settings or perform a deployment.

## Volume and configuration

Mount a **new empty volume** at `/data`, and set `SCRYRAVEN_DATA_DIR=/data`.
Never upload or mount the owner's personal sessions database. Hosted startup
rejects any database containing unowned sessions. This is a refusal, not an
ownership backfill or a personal-data import tool. A hosted database may be
restored from its own protected backup, preserving ownership.

The volume contains `sessions.sqlite3`, its transient SQLite/owner-lock sidecars,
`diagnostics/`, and transient protected export spools. SQLite holds conversations,
source identity, immutable acquired material, historical citation snapshots,
original PDFs/images, job/settings/usage snapshots, ownership and quota counters.
Schema 5 additively adds nullable ownership and an independent UTC daily admission
ledger to schema 4; legacy payloads and attachments are not rewritten. Local
unowned sessions continue working locally. The hosted app excludes them entirely.

Set these through protected Railway service variables, never tracked files:

| Variable | Required value or policy |
| --- | --- |
| `SCRYRAVEN_MODE` | `hosted` |
| `SCRYRAVEN_HOSTNAME` | `dogfood.scryraven.com` (default) |
| `SCRYRAVEN_DATA_DIR` | `/data`, on the mounted volume |
| `CF_ACCESS_ISSUER` | Exact `https://TEAM.cloudflareaccess.com`, no trailing slash |
| `CF_ACCESS_AUD` | Audience tag of this specific Access application |
| `SCRYRAVEN_ADMIN_EMAIL` | One explicit owner email |
| `SCRYRAVEN_TESTER_EMAILS` | Two exact invited email addresses, comma separated |
| `SCRYRAVEN_BILLING_AUTHORIZED` | Explicit operator approval: `true` |
| `OPENAI_API_KEY` | Operator-owned API credential, supplied externally |
| `EXA_API_KEY` | Ordinary general Search credential |
| `SERPER_API_KEY` | Alternate lexical/community/current discovery credential |
| `LINKUP_API_KEY` | External known-URL Read credential |

The app never loads `.env`. The agent's offline tests use synthetic placeholders
and do not inspect real environment values. For agent-operated credentialed
commands use the existing repository doorman, as required by `AGENTS.md`.

Optional operator controls:

| Variable | Default |
| --- | --- |
| `PORT` | `8080`; Railway supplies its assigned listening port |
| `SCRYRAVEN_BIND_HOST` | `0.0.0.0`; use `127.0.0.1` for local verification |
| `SCRYRAVEN_HTTP_THREADS` | `8`, permitted range 4–32 |
| `SCRYRAVEN_RESEARCH_MODEL` / `SCRYRAVEN_ANSWER_MODEL` | Shipped role identifiers, ignoring personal model files |
| `SCRYRAVEN_RESEARCH_REASONING` / `SCRYRAVEN_ANSWER_REASONING` | Shipped efforts; empty omits effort |
| `SCRYRAVEN_API_PROCESSING` | `standard`; optional `fast` may cost more |
| `SCRYRAVEN_SUBMISSIONS_PER_DAY` | `20` per identity per UTC day |
| `SCRYRAVEN_FORENSIC_DAYS` | `30` |
| `SCRYRAVEN_FORENSIC_MAX_BYTES` | `1073741824` (1 GiB total diagnostic budget) |

Hosted forms cannot select backend/model/effort/tier/limits, supply keys, change
billing authorization or set ownership. Such fields are rejected server-side.
Every dispatch uses a job-owned OpenAI API configuration. Operator configuration
changes do not silently reroute retries: a retry must match the current hosted
policy; otherwise submit a new question. Admission and explicit retries count
against the durable daily quota; exact submission replay does not. Failed or
interrupted accepted questions still count. Deleting a conversation or restarting
does not reset the quota. The existing ceilings remain 40 physical model requests,
16 external attempts, 900 whole-turn seconds, and 128,000 cumulative Answer source
characters. These are technical ceilings, **not guaranteed dollar limits**.
The shared waiting queue can fill; users should wait for capacity rather than
retrying repeatedly. At most one active research job per hosted owner prevents
one user from occupying both active slots across conversations.

## Access, hostname and origin verification

Create a Cloudflare Access self-hosted application for exactly
`dogfood.scryraven.com`, covering every path. Configure an Allow policy for the
owner and the two invited identities through the chosen identity provider; do not
enable public registration, Bypass, wildcard email domains, or a service-token
alternative for testers. Configure a suitable Access session duration and
revocation procedure. Signed email claims identify users; removing an email from
the application allowlist revokes app admission after the service configuration
is restarted, independently of an existing Access browser session. Reassigning a
permitted email address would reassign its stored research identity, so treat
email ownership changes as an operator account-custody decision.

Add Railway's custom domain, follow its displayed DNS target instructions in
Cloudflare, enable Cloudflare proxying so Access actually executes, and verify
custom-domain TLS with Full (strict) encryption. Do not assume the Railway public
domain is protected by Cloudflare. Avoid publishing it to testers. If Railway
permits removing unused public domains without breaking the custom-domain route,
remove them after verification. Application verification remains required either
way: the app checks the `Cf-Access-Jwt-Assertion` signature against the pinned
team's HTTPS JWKS endpoint, RS256 algorithm, issuer, audience, expiration, issued
time, application token type and explicit email allowlist. Email/forwarded headers
without a valid signed token have no authority. Key retrieval has timeouts, a
bounded response and a short cache; a missing key or expired cache during an
outage denies access. No token or raw identity-service response is logged.

The app trusts only its configured hostname for data routes. The Railway
`healthcheck.railway.app` Host can reach only `/healthz`; it cannot reach data
even with a valid JWT. Forwarded host/protocol/user headers are ignored. Hosted
CSRF checks use the configured HTTPS origin and identity-bound signed forms.
`/healthz` is intentionally unauthenticated, returns only `{"status":"ok"}`,
does not contact inference/search/identity services, and performs diagnostic
retention maintenance. It proves process readiness, not external service health.

After activation, verify from an unauthenticated client, a tester session and the
owner session. Check the protected domain and direct Railway origin, including
requests to `/`, `/jobs/status`, exact session URLs, original PDFs/images and
exports. Send a forged email header and spoofed forwarded headers. Send an origin
request with the intended Host/SNI through an appropriate operator-only probe.
Every data request without a valid app JWT must be denied. A valid token for a
different app/team or an expired token must be denied. Never paste tokens into
shared terminals/logs, URLs, screenshots or review artifacts. A valid bearer token
is itself a credential; possession permits its identity until expiry/revocation.
Hostname protection alone is never the authorization mechanism.

Test both invited users simultaneously, each with independent browser profiles.
Verify each can create/reopen/rename/delete only their own sessions; supplying
the other's URL or form fields must not reveal material. Verify two active jobs,
a third queued job, private status, and the administrator's read-only view at
`/admin`. The owner can research in their own conversations but cannot mutate
another user's conversation, including through crafted HTTP requests.

## Diagnostics and exports

Hosted diagnostics are always separate from application output. The private
`diagnostics/` directory contains one source-bearing forensic JSONL and one
body-free summary per job, keyed by internal session/job IDs. Records include
authenticated owner, session, job, process run and sequence. They use the
existing normalized observer and body-free TurnDiagnostics projection: no raw
provider payloads, hidden reasoning, API keys or authentication tokens are added.
Research decisions/source material in forensic files remain sensitive.

Cleanup occurs hourly in the production process, and on startup, requests,
health checks and diagnostic writes. Files
older than the configured age are removed; oldest completed-job diagnostic
groups are removed earlier to satisfy the actual byte budget. Each forensic
file is additionally capped at 64 MiB (or the smaller total budget). An active
job is not evicted; recording stops at its limits. Its summary records truncation
when space permits. Write failure affects diagnostic recording, not a completed
answer. Records can be absent because of retention, limits or storage failure;
exports make no completeness promise. The administrator sees measured diagnostic
file counts/bytes, limits, recording availability and database bytes. Monitor
actual volume usage in Railway as well: the ordinary database is not size-pruned,
and backup/export space also consumes storage. No fixed size per question is
assumed. Unknown files/links in the diagnostic directory are counted but never
followed or deleted by retention.

Only the owner can export a selected session from `/admin`. A ZIP includes the
session's validated conversation/acquisitions/citation state, owner metadata,
job configuration/usage receipts, original attachments, extracted document text,
and currently available diagnostic files for that exact session. There is no
public raw-log directory, general log-download endpoint or tester export route.
Export spools may temporarily consume volume space. Store downloaded exports in
protected operator storage. Before importing useful exact failures into local
evaluation, sanitize them and follow `docs/operator/LOCAL_EVALUATION_CORPUS.md`;
permission to read tester research does not make private tester text public.
Session deletion removes ordinary session custody; retained diagnostic copies
may persist until retention. Tell testers this before they submit private data.

## Backup, restore and rollback

Configure Railway volume backups and a private off-volume recovery copy according
to the chosen operator retention policy. Record backup timestamps/revisions and
restrict download access. Treat backups as containing every user's private
research. Diagnostic cleanup does not clean older backups or downloaded exports.

For a consistent manual snapshot, put the beta into operator maintenance, stop
admissions, wait for workers to finish (or accept explicitly interrupted work),
and stop the single service. Take a volume snapshot including the database and
diagnostics; do not copy a live SQLite main file alone and omit journal/WAL files.
An online database-only backup may use Python's `sqlite3.Connection.backup()` to
a separate protected destination; copy diagnostics separately and disclose that
they may have changed during capture. Confirm disk space before producing a
backup. No credentials are stored in this database or diagnostic export format.

Restore with the service stopped: preserve the existing volume first, restore the
hosted database and optional diagnostic directory from one identified backup,
preserve private permissions and the external identity allowlist, then launch the
reviewed compatible revision with the same volume/configuration. SQLite's owner
sidecar file is not a running lock; only the OS lock matters. Startup interrupts
unfinished jobs without retry. Verify both owners' session lists, a historical
citation, original attachments and quotas with synthetic canaries before reopening
admission. Actually rehearse this on an isolated volume before relying on it.

Rollback runtime by explicitly promoting a previously reviewed compatible image.
Do not run an older schema-4 binary against a schema-5 database; use a compatible
revision or an identified pre-upgrade backup, accepting any later data loss only
through an explicit owner decision. Never reset the live volume to hide a failure.

## Activation checklist after review

Offline verification of the reviewed runtime at
`c0ab0997753a38abd488c8eadb464d075b4b6491` passed 1,404 tests with no skips using
the repository Python 3.12.14 environment, declared dependency versions including
pypdf 6.19.0/Pillow 12.3.0 and isolated Waitress 3.0.2. The full suite includes
signed synthetic JWTs, actual local Waitress startup/HTTP, mocked ordinary API
research, owner-scoped routes, concurrent per-user dispatch, quotas, additive
migration, historical citations, restart, forensic retention and idle cleanup.
Seven hosted Edge checks use separate users at 1440/390/320px with external
requests blocked; local product browser/200% zoom checks also pass. Fifteen hosted
screenshots were reviewed under `C:\tmp\scryraven-private-dogfood-01\screenshots`.
Ruff, compilation, JavaScript syntax, whitespace and all six repository hooks
pass. No semantic research surfaces were changed. No production database,
credentials, unrelated forensic files or live services were accessed. The Docker
daemon was unavailable, so the Python 3.13 Linux image build/run remains unverified.

The full offline command was:

```powershell
$env:PYTHONPATH = 'C:/tmp/sr-waitress' # Disposable Waitress-only test dependency.
.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp C:/tmp/scryraven-private-dogfood-01/verified-full-suite
```

For another checkout, install `requirements-dev.txt`, `requirements-hosted.txt`
and Playwright into one compatible environment and use its Python interpreter.
Do not share native-wheel target directories between Python versions. These
offline results establish integration mechanics, not live login/provider quality
or operational recovery on Railway.

1. Review the combined changes, select and record the exact source SHA.
2. Create one empty Hobby service and new `/data` volume; apply the dashboard
   settings above with one replica and no GitHub autodeploy or PR environments.
3. Set protected identity, model/provider, quota and retention configuration.
4. Configure the exact Cloudflare Access app/policy, custom DNS and TLS.
5. Manually upload the reviewed source archive; confirm health and application
   denial at every origin.
6. Verify login, owner isolation, admin read/export, two-user research and queueing.
7. Rehearse restart and backup/restore with synthetic conversations and citations.
8. Check actual provider compatibility/charges, storage usage and tester privacy
   disclosure before inviting the two testers.

Configuration references: [Cloudflare signed JWT validation](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/),
[Railway health checks](https://docs.railway.com/deployments/healthchecks),
[Railway volumes](https://docs.railway.com/volumes),
[Waitress arguments](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html).
