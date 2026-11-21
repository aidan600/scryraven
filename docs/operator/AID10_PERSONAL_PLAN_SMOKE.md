# AID-10 personal-plan smoke

Run one public development question once with the control and once with
the hardened Research guidance. Both arms request exact `gpt-6-luna` / high
for Research and `gpt-6.2-sol` / medium for Answer. Sol's Answer instructions
are identical. The pilot exercises the ordinary local `ResearchSession.ask`
and native continuation through the repository's existing personal-plan
adapter. It is a transport and failure-diagnosis smoke on a fixed source
packet. The 90% target requires the separately registered held-out evaluation.

## Windows PowerShell 5.1

Use the same Windows account and desktop that already signed in to ScryRaven's
`personal` plan account. The main repository's existing `.venv` supplies Python
and the optional plan dependencies. Use a separate clean checkout of
`codex/aid-10-luna-harness-reliability` for the pilot code. If needed, clone
the branch into a new directory with
`git clone --single-branch --branch codex/aid-10-luna-harness-reliability https://github.com/aidan600/scryraven.git "$env:USERPROFILE\ScryRaven-aid10"`.

From the isolated checkout, run the following once when deliberately exercising
the personal plan. It uses the current Windows user's existing sign-in and
normal plan allowance.

```powershell
& "$env:USERPROFILE\ScryRaven\.venv\Scripts\python.exe" -I .\scripts\aid10_plan_smoke.py --run-personal-plan-smoke
```

The console prints the run directory, revision and source-fixture digest,
followed by one JSON summary per attempted arm. Each summary includes
`processing: "plan-default"`, `acquisition: "frozen_fixture"`, the requested and returned model for each
physical Responses call, a returned tier when the adapter reports one,
dispatch count, answer posture, citation count, and a fixed failure code when
applicable. Plan requests omit the service-tier override. A null tier means
unreported. Exit code 0 requires a completed posture and exact successful
receipts for both role identities in each arm. Use the saved answers and
source traces for semantic review, including any partial or unsupported
result. A network policy denial stops the pair.

Local files are under the printed
`%LOCALAPPDATA%\ScryRaven-aid10-plan-smokes\d07-…` directory. Each arm has an
independent SQLite session, normalized events, body-free dispatch and usage
logs, and a source-bearing outcome. Console output omits the answers and
source text. The transport keeps authorization, raw provider envelopes,
and opaque reasoning out of those files.

## Frozen evidence and bounds

The checked-in [public source fixture](../../scripts/fixtures/aid10_plan_smoke.json)
is a standalone U.S./Canada version of development obligation D07. It leaves
the original manifest and its held-out cases alone. Search and lexical Search
return fixture navigation leads for the case's known subjects. Read grants
only the supplied excerpt for each exact fixture URL. Unknown routes fail
locally. The independent manufacturer excerpts let a reviewer check both
the automotive engine's identity and the aircraft lookalike. [American Honda 2024 specifications](https://hondanews.com/en-US/honda-automobiles/releases/release-7b0d03d783f6d642dbbefc6b2a130141-2024-honda-passport-specifications-features) · [Honda Canada 2024 specifications](https://hondanews.ca/en-CA/hci-automobiles/releases/release-1128768177ab00a73471b1938c15f800-2024-passport-specifications) · [GE Aerospace Passport](https://www.geaerospace.com/commercial/aircraft-engines/passport)

- Each arm runs in a fresh isolated Python process with its own database.
  The ordinary app has 90 seconds, six physical Responses requests and five
  frozen acquisition attempts per arm. The parent enforces a 100-second
  process timeout per arm. Each Responses request also has a 45-second
  ceiling, reduced by the remaining turn budget.
- The only outbound requests allowed are from the personal-plan adapter's own
  HTTP session. It can send up to six Responses requests and, if normal
  existing-auth refresh needs them, one token refresh and one JWKS lookup per
  arm. There is no extra catalog request, provider call, redirect, API-key
  inference, model substitution or automatic rerun. The worker receives only
  mechanical Windows environment values.
- Route and model authorization stay within the existing personal-plan
  implementation. The launcher supplies explicit roles and keeps the
  original checkout and user model settings out of the pilot.

## Offline verification

From the isolated checkout, the existing venv can run this command without
the personal sign-in:

```powershell
& "$env:USERPROFILE\ScryRaven\.venv\Scripts\python.exe" -m pytest -q tests/test_aid10_plan_smoke.py
```

The test substitutes synthetic streaming responses and forbids sockets.
It checks the real plan adapter's request shaping, native continuation,
per-call receipts, exact cited materials, the second arm's isolation, the
physical limits and refusal paths. It exercises normal absence of a returned
tier, a reported tier, and a wrong returned model that fails before publication.
The HTTP gate tests reject Exa, LinkUp, OpenRouter and a separate API caller
even at the identical Responses URL. The live command and Windows sign-in
were not exercised during preparation.
