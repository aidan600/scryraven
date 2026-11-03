# Reading Room Run Settings 01

Outcome: implementation met. The original OpenAI Standard and Fast checks demonstrated them through
the ordinary browser product; OpenRouter's optional live turn failed at
authentication, so live model compatibility remains unproved. Final receipts are
recorded in the review bundle at
`C:\tmp\scryraven-run-settings-01`. That original implementation built from
`99ef3e113b164835dc694bedb26355c01386cb72` in an explicitly requested isolated
worktree. The UX simplification uses the ordinary checkout from merged reference
`5148a7c50e22b99e8abbb9321e31c1fc87bbd142` and permits zero live requests.
The installed launcher, personal model profile, credentials and
persistent production sessions database are not changed during development.

## Product behavior and execution

The compact composer summary opens an accessible Run Settings dialog. It shows
the backend and exact Research/Answer identifiers and efforts before submission.
Separate suggestion menus open with the current identifier intact. Editable exact
identifiers remain bounded data, never
URLs or executable/routing instructions. Reasoning default omits the parameter;
`none`, `low`, `medium`, `high`, `xhigh` and `max` remain exact requested values.
Unsupported selections fail without substitution. Plan model membership and
published effort support are checked against the authenticated account catalog.

Initial launch reads the genuinely effective injected or existing personal
`model_roles.json` configuration, falling back to shipped values only when that
file is absent. The file is never overwritten. Saved Reading Room preferences
then take precedence for new submissions. An inherited mixed API tier profile
is displayed exactly and requires an explicit uniform Standard/Fast choice.
Paid inference requires explicit saved authorization for each billed backend in
this trusted local Reading Room. Run Settings offers authorization and revocation;
the existing database preferences retain this choice across browser/server restarts.
Authorization is checked at admission, retry, and before each paid dispatch.
Revocation prevents subsequent paid dispatches; it cannot undo a request already
sent. No per-question confirmation is required. PDFs, images, conversation and source
text used in inference are disclosed as supplied to the chosen provider.

Each accepted question atomically saves its frozen `RunSettings` with its job:
backend; both exact model identifiers/efforts; OpenAI processing choice; physical
request, external-attempt, elapsed-time and attention limits. New submissions use
40 physical requests for all backends as an internal technical ceiling. The UI
does not offer a request allowance. External-attempt, time and attention limits
remain unchanged. These bounds use the existing physical dispatch accounting,
including native tool continuations. They are resource limits, not a promised
dollar cap or usage target. Older accepted jobs and retries keep their exact
original allowances.

Per-backend model selections and OpenAI Standard/Fast choices survive switching
backends and later submissions. The first OpenRouter selection leaves both exact
model fields empty with a neutral provider/model placeholder; configured choices
are preserved. Its [model catalog](https://openrouter.ai/models) is linked directly.
Only explicit supported model identities are accepted; automatic routing remains
unavailable.

The existing ResearchJobManager per-job options factory creates an independent
model instance from the accepted snapshot. Active/queued jobs never reread UI
model preferences. Billing authorization remains separately revocable. Two
workers, eight waiting slots, one active job per conversation,
revision checks, durable commit and idempotency remain. Duplicate requests with
changed settings conflict. Retry copies the original settings, question and
attachments without overwriting newer UI preferences. A historical job without
a snapshot cannot be retried under an invented identity; a new reviewed
submission is available. Server restart still interrupts rather than repeats
paid execution.

The answer, completed job state and available safe usage receipt share the same
SQLite transaction. Run details show requested and reported models, backend,
role efforts, requested/returned tiers, known token counters, and a routed
provider/reported cost when present. Missing values remain unknown. A
provider-reported inference cost is not a complete invoice; actual billing and
API credit balances are unknown. No model price table or speculative spending
estimate is introduced into the product.

## Backend compatibility

| Selection | Routing and credential boundary | Strict contract and tier behavior | Evidence |
| --- | --- | --- | --- |
| ChatGPT personal plan | Existing authenticated plan transport/account catalog; no API key read or inference fallback | Native schema/tools/continuation; API tier/cache/output-limit parameters omitted | Controlled transport, app, image and regression checks; no new paid-plan inference |
| OpenAI API Standard | Existing fixed `https://api.openai.com/v1/responses`; `OPENAI_API_KEY` read only by credentialed process | Explicit `service_tier=default` for both roles, exact reasoning including omitted default | Ordinary browser Luna/none turn completed in 2 requests; exact model and `default` tier returned |
| OpenAI API Fast | Same fixed API route and credential | Explicit `service_tier=fast`; returned tier recorded separately; no retry/downgrade to Standard | Ordinary browser Luna/none turn completed in 2 requests; exact model and `fast` tier returned |
| OpenRouter | Fixed `https://openrouter.ai/api/v1/responses`; only `OPENROUTER_API_KEY` | `provider.require_parameters=true`, `allow_fallbacks=false`; plugins/transforms empty; no model list/fallback, server web tools or schema relaxation | Controlled strict schema/function/reasoning continuation, model mismatch, credential and image checks passed. Single optional live request failed authentication; live compatibility unproved |

OpenRouter requires an explicit provider/model slug and rejects routing/search
modifiers and automatic router identifiers. If a reported model differs from the
selected exact slug, publication fails safely. Missing reported identity stays
unknown. Models must support the unchanged strict research/answer schemas and
native function continuation. Unsupported image capability fails explicitly;
recognized OpenAI image models also work with their `openai/` slugs. General
arbitrary-model vision compatibility is not established.

Malformed OpenRouter structured responses fail as `model_contract_incompatible`
without spending on schema repair, including inside delegated Research. The
first-party OpenAI API retains its existing one-correction Research and Answer
behavior, bounded by the existing correction budget and physical request/run
limits. Answer correction keeps its native tool/opaque continuation; rejected
final prose is not fed back as Evidence or a draft. Existing semantic
citation/source validation and valid native tool continuation survive.
No acquisition-provider routing, prompt, semantic schema or research owner is
changed. No additional execution manager, arbitrary-base-URL client, backend
fallback, premium escalation or automatic replacement run exists.

## Additive storage migration

SQLite schema 4 adds nullable `research_jobs.run_settings` and `run_receipt` JSON
columns, plus the small `app_preferences(name,value)` table for last-used UI
settings, per-backend profiles and billing authorization. No new schema version
is required for the UX simplification. Version 3 migrates with additive ALTER TABLE operations; versions 1/2
continue their existing additive upgrade while creating the current job table.
Existing session payloads, evidence, original attachments, citation identities,
turn revision numbers and historical jobs are preserved. No historical backend,
model, effort, usage or tier is backfilled. Legacy identity is displayed unknown.
No credentials have a storage field. Receipt keys are bounded and allowlisted;
raw provider payloads are rejected. Invalid optional reporting remains unknown
without invalidating a valid answer.

## Verification and limits

The focused suites exercise all backends, exact IDs and omitted/explicit effort,
Standard/Fast distinction, plan parameter omission/catalog rejection, fixed
OpenRouter endpoint/credential isolation, strict function/reasoning continuation,
no OpenRouter incompatibility repair, returned-model mismatch, simultaneous/queued
settings, original retry, tampered duplicate requests, missing credentials,
historical migration/reopening, source/citation custody, new and retained images.
Real Edge checks cover desktop, 390/320px, actual 200% browser zoom, keyboard
dialog operation and first-completion receipts. Actual screenshots are external
review artifacts; their synthetic answers are presentation fixtures.

The UX simplification passed all 1,298 offline regression tests without skips,
including 12 Run Settings real-Edge checks. A separate 119-test focused backend
run covered new 40-request submissions and the 40th/41st physical-dispatch boundary
for every backend, independent saved/revoked authorization, queued and continuation
revocation, strict malformed/duplicate form rejection, exact models/tiers, historical
persistence and original retry allowances. Browser checks include populated-value
suggestion menus, exact custom identifiers, neutral/configured OpenRouter profiles,
saved Standard/Fast choices, desktop, 390/320px, keyboard selection and actual 200%
zoom. Screenshots were visually reviewed. Ruff, Python compilation, JavaScript
syntax, whitespace and all six configured hooks passed. The regression XML and
screenshots are at `C:\tmp\scryraven-run-settings-ux-simplification-01`.

This simplification used zero live model, provider or search requests. The following
live observations belong to the original implementation, not this UX verification.
The original live caller
uses ordinary browser submission -> actual HTTP route -> ResearchJobManager ->
ResearchSession -> Responses transport -> durable answer, without scripting the
model's semantic work. It requests the licensed apple premise question only,
with Luna/none for both roles, six requests per turn and zero external attempts.
A separate pre-dispatch guard enforces the combined 12-request/$2 authorization
using documented pricing and conservative input/output reservations. Those
phase-only guard calculations do not promise a general product dollar ceiling.
No plan allowance was spent. Public OpenRouter catalog/endpoint metadata
established `openai/gpt-6-luna`, Responses, tools, strict outputs, `none` effort
and known rates below the conservative guard before the optional request.

At frozen runtime `89b002475482c28b3548b97347fe26b9c0b6780f`:

| Turn | Result | Physical requests | Input/output tokens | Requested / returned tier |
| --- | --- | --- | --- | --- |
| OpenAI Standard, Luna/none both roles | 8 apples; reopened exact answer and receipt, no sources/citations | 2 | 3,869 / 95 | `default` / `default` for both requests |
| OpenAI Fast, Luna/none both roles | 8 apples; reopened exact answer and receipt, no sources/citations | 2 | 3,861 / 84 | `fast` / `fast` for both requests |
| OpenRouter, `openai/gpt-6-luna`/none both roles | `model_authentication_failed`; exact question/settings saved, no answer committed | 1 | Unknown | Omitted / unreported |

Both OpenAI roles reported the exact requested `gpt-6-luna` model, zero cached
input and zero reasoning tokens. Total known OpenAI input/output was 7,730/179.
The third request used OpenRouter's fixed endpoint and its distinct credential;
credential presence was confirmed only as a boolean inside the brokered child.
Authentication rejection does not establish model or structured-output
compatibility. No credential inspection, repair, retry, substitution or extra
turn followed it. Three turns/five physical requests consumed the entire licensed
turn runway, with zero external acquisition and zero independent source checks.
The pre-dispatch conservative reservation was $0.375396 of $2; this is an upper
resource reservation using above-listed-price rates and request/output bounds,
not an invoice or reported charge. OpenRouter usage and all actual billing remain
unknown. No latency/Fast speed comparison is claimed from this smoke check.

Exact safe receipts, provider-public metadata, callers, broker lifecycle output,
validation SQLite and actual browser screenshots are preserved in the review
directory. The authentication boundary is also a sanitized ignored local
development candidate at
`local-evals/candidates/reading-room-run-settings-01-openrouter-auth-20261101/`.
It is operational diagnostic evidence, not a semantic model failure or gold case.
The focused review fix restores bounded first-party API malformed-output
correction while preserving OpenRouter's fail-closed behavior. That correction
path is covered by offline regression/continuation checks; no additional live
inference, provider call or API spending was authorized or performed for the fix.
The earlier live smoke checks did not exercise malformed-output recovery.

## Installed launcher aftercare: only after merge

Do not run these steps during this phase. The installed external
`%LOCALAPPDATA%\ScryRaven\Reading-Room.ps1` currently embeds a child that starts
with the personal plan. It also deletes `OPENAI_API_KEY` and rejects a ready
record if that key is present. Both exact guards need removal to make already
approved API credentials available; per-job backend selection then belongs to
the application. Keep the startup plan model, doorman, credential source,
database and all other process-identity checks.

After the reviewed phase has merged and local aftercare is authorized:

1. Stop this installation with its own launcher:
   `& "$env:LOCALAPPDATA\ScryRaven\Reading-Room.ps1" -Stop 2>&1`.
2. Back up that one launcher. Remove only the embedded Python line
   `    os.environ.pop('OPENAI_API_KEY', None)`.
3. In `Update-ServerIdentity`, replace exactly
   `$ready.plan_account -ne 'personal' -or $ready.api_key_present -or`
   with `$ready.plan_account -ne 'personal' -or`.
   The ready record may continue reporting the boolean credential presence.
4. Run the existing launcher with `-PrepareOnly 2>&1`; verify its database is
   still `%LOCALAPPDATA%\ScryRaven\sessions.sqlite3` and its broker still reads
   the approved `credentials.env` by path. Do not inspect that file or keys.
5. Launch normally. Existing sessions reopen; Run Settings chooses each job's
   backend. No new conversation database or forensic run is needed to change
   backend. An absent OpenRouter key remains a configuration-unavailable state.

The review directory contains an exact guarded aftercare script for these two
text replacements; it was not executed against the installed launcher. Updating
the launcher does not create credentials or authorize any live request by itself.

## Primary provider references

- [OpenAI Fast mode](https://developers.openai.com/api/docs/guides/fast-mode)
- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
- [GPT-6 Luna parameters/pricing](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [Plan models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [OpenRouter Responses](https://openrouter.ai/docs/api_reference/responses/overview)
- [OpenRouter provider filtering](https://openrouter.ai/docs/guides/routing/provider-selection)
- [OpenRouter tool continuation](https://openrouter.ai/docs/api_reference/responses/tool-calling)

This phase is inference configuration only. Product capability and general
model/provider reliability remain bounded by actual evidence in CURRENT.md and
the final review receipts. The branch stays local; publication requires a later
human decision, and merge/aftercare is not authorized by this review bundle.
