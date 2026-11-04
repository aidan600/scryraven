# Private Preview V2 offline resource verification

The production application factory, Waitress, hosted admission, independent
OpenAIModel instances, the ordinary Research/Answer loop, attachment validation,
diagnostic recording and SQLite persistence run in one measured child process.
The client runs in a separate parent process. Signed synthetic RS256 Access
tokens pass through the real hosted verifier, with an offline JWKS response.
Only model and acquisition transport replies are scripted. A socket guard rejects
every non-loopback connection. No real credentials, production database, private
conversation, provider, model, search or identity service is used.

Run from the repository with its development and hosted dependencies installed:

```powershell
# This existing disposable directory supplies Waitress in the local test setup.
# Omit PYTHONPATH when requirements-hosted.txt is installed in the environment.
$env:PYTHONPATH = 'C:/tmp/sr-waitress'
.venv/Scripts/python.exe scripts/offline_private_preview_stress.py --output C:/tmp/scryraven-private-preview-v2-stress-NEW
```

The output directory must be new and outside the repository. It contains only
synthetic research, the public test JWKS, child stdout/stderr, sampled metrics,
and `result.json`. The report records the checkout revision and whether local
changes existed. Rerun against the final reviewed runtime when implementation
changes affect the measured path.

## Workload and observed behavior

Two scenarios each submit five ordinary multipart questions over actual Waitress
HTTP, with eight HTTP threads and four research workers:

1. Four independent conversations owned by Alice reach a synthetic Answer barrier
   simultaneously. A fifth Alice conversation is accepted as Queued.
2. Four independent conversations split between Alice and Bob reach the same
   barrier. A fifth Bob conversation is accepted as Queued.

For each scenario, releasing one Answer completes that job and starts the queued
job automatically. The other three remain Researching. Releasing the remaining
barriers completes all five. Another ordinary submission causes no interruption.
Authenticated status responses reveal only that owner's conversations.

Every question includes a six-page, 396,000-character text PDF (397,902 original
bytes) and a 1536×1024 RGB PNG (4,726,046 original bytes). Each role receives the
actual image input. Research acquires three 31,000-character synthetic original
sources and selects those plus a 32,000-character exact PDF view. Each Answer
receives 125,000 source characters, close to the unchanged 128,000-character
attention allowance. The largest encoded model request is 6,441,549 bytes.
Barriers hold four assembled large Answer payloads concurrently. JSON encoding
and decoding remain exercised; no simulated network delay is interpreted as
provider performance.

All ten answers reopen through owner-authenticated HTTP. Each has four citations,
one committed turn, the original PDF and image bytes, immutable accepted settings
and a saved run receipt. Ten distinct model instances execute forty synthetic
Responses requests. Every accepted job completes. No unexpected failure or
submission-caused interruption occurs in these scenarios.

## Measured local result

Frozen-runtime measurement: `C:/tmp/scryraven-private-preview-v2-stress-feb7a91`,
at clean commit `feb7a91bb84afff4ed009e43767a70a0a20ee9f4`. The exact
`result.json` records that SHA and `working_tree_has_changes=false`; sampled
counters remain in `samples.json`. Subsequent evidence-documentation changes do
not change the measured runtime.

The measured child runs Python 3.12.14 on Windows 11 (build 26300), on a host
reporting sixteen logical CPUs. Its process affinity is restricted to two
available logical CPUs. Native Windows process counters measure only the child;
the HTTP client, image generation and signed-token creation are excluded.

| Measurement | Observed |
| --- | ---: |
| OS peak working set, including startup | 226,721,792 bytes (216.22 MiB) |
| OS peak committed process memory | 211,169,280 bytes (201.39 MiB) |
| Maximum sampled resident memory | 205,271,040 bytes (195.76 MiB) |
| Maximum sampled private memory | 189,927,424 bytes (181.13 MiB) |
| CPU time during measured server interval | 9.015625 seconds |
| Measured wall interval | 7.359 seconds |
| Average CPU, where one full core is 100% | 122.51% |
| Peak CPU over approximately one second | 155.91% |
| Peak CPU between nominal 100 ms samples | 186.35% |
| Final synthetic SQLite database | 57,589,760 bytes (54.92 MiB) |
| Completion | 10 completed; zero failed/interrupted |

Sampling is nominally every 100 ms; Python scheduling and the Windows CPU clock
are granular, and CPU/wall snapshots are not atomic. The approximately one-second
peak and total CPU time are more useful than the short-interval peak.
OS high-water memory catches allocations missed between samples. Measurement
includes production forensic recording and database writes. Startup is included
in OS memory high-water marks and excluded from the CPU/wall interval.

## Limits

This is production-equivalent application mechanics under deterministic offline
transport, not a Railway container measurement. Two-core Windows affinity does
not reproduce Railway Linux CPU throttling, and no 2-GB memory cap is applied to
the local process. The service configuration remains one process, one replica,
2-vCPU limit and 2-GB memory limit; this phase changes none of those settings.

The probe is a bounded workload, not a maximum-load or long-duration capacity
guarantee. It does not exercise every attachment-size combination, very long
histories, all source-corpus sizes, real provider bodies, live diagnostics growth,
or every model continuation. The PNG contains deterministic synthetic RGB noise;
its dimensions, decode, validation, custody and base64 costs are real, but its
visual content is not a provider-quality evaluation. The large source answers are
scripted and establish no semantic research reliability.

The measured elapsed time does not establish real provider latency or Fast-tier
benefit. Usage counters are synthetic; no billed-cost estimate is inferred.
Live four-job provider capacity, deployed Linux memory/CPU peaks and behavior
under the actual Railway limits remain untested. The separate focused and full
offline suites cover queue bounds, dynamic settings, quotas, retries, restart
recovery and access-control attacks beyond this resource probe.
