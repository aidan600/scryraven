# AG-LIVE-PLAN-01 Bounded Live Product Validation Plan

Status: planning/readiness audit only. No live provider, model, search,
retrieval, fetch/read, broker, `.env`, private adapter, DB/cache, private log,
raw prompt, raw model response, or raw provider payload access was used.

Proof class: `docs_only` plus live-readiness audit.

Actual app delta: none.

## Go/No-Go Decision

AG-LIVE-BOUND-01 is **not ready to run** from the current repo-visible product
entrypoints.

Entrypoint classification: **E. no safe product-live entrypoint exists yet**.

The ordinary CLI, `python -m proplex`, does call ordinary `run_pipeline()`, but
it is not a safe AG-LIVE-BOUND-01 entrypoint because it:

- loads local dotenv state before command execution;
- has no single-run sanitized validation packet writer;
- has no pre-dispatch cap enforcement for search dispatches, fetch/read
  operations, Author calls, or retries;
- relies on provider/model/search credentials outside the repo-visible broker
  boundary;
- can fan out through ordinary query/provider/retrieval logic;
- cannot disable built-in provider/model retry wrappers for a zero-retry live
  proof;
- leaves `Balanced` component-gap recovery as an explicitly offline-only path
  that requires an injected offline recovery adapter.

Existing broker-visible scripts are component or discovery harnesses, not a
bounded ordinary product run:

| Surface | Classification | Readiness finding |
| --- | --- | --- |
| `python -m proplex` | ordinary product path candidate | Real product path, but not capped or packetized for AG-LIVE-BOUND-01. |
| `scripts/request_live_validation_broker.py` | broker client | Sanitized local broker client only; no product command is visible here. |
| `scripts/ag96i3e_brokered_provider_neutral_discovery_validation.py` | provider discovery component | Can spend one provider/search call, but has no fetch/read, Author, FAP, or final citation path. |
| `scripts/ag96i3b_live_followup_validation.py` | follow-up provider-job harness | Uses a fixture spine and `max_fetch_read_attempts: 0`; not ordinary product path. |
| `scripts/ag96i3af6a_brokered_author_lane_smoke.py` | Author component harness | Tests Author/model custody only; no search/fetch/product recovery path. |

## Smallest Bridge Phase

Recommended bridge: **AG-LIVE-BRIDGE-01 bounded product-live runner dry-run**.

That bridge should add a repo-visible runner or broker job that is inert by
default and can prove its argument/cap/redaction behavior offline before any
live use. It should not change normal CLI or Streamlit behavior.

Future bridge command shape:

```powershell
py scripts\ag_live_bound_01_bounded_product_runner.py `
  --query "According to the official Python 3 documentation, what are the default values for rel_tol and abs_tol in math.isclose()?" `
  --mode Balanced `
  --include-domains docs.python.org `
  --output output\ag_live_bound_01_packet.json `
  --max-scryraven-runs 1 `
  --max-search-dispatches 2 `
  --max-fetch-read-operations 3 `
  --max-author-model-calls 1 `
  --max-smart-search-judgment-model-calls 0 `
  --max-independent-manual-source-checks 1 `
  --max-retries 0 `
  --confirm-live-product-run
```

The bridge must fail closed before any live call if the output path is not
ignored, if caps cannot be enforced, if credentials would need to be printed or
inspected, if raw/private/full-trace material would be retained, or if the run
would require provider routing/depth/query/citation/Author changes.

## Broker Boundary

The repo-visible broker path is suitable for requesting allowlisted local jobs
and receiving sanitized broker responses. It is not currently proven as a
product-path executor.

- The broker is proven for a sanitized client boundary plus component/discovery
  shapes, including provider discovery and Author-lane smoke.
- The visible broker template does not expose a real ordinary `run_pipeline()`
  job that enforces AG-LIVE-BOUND-01 caps.
- A live product path would need model credentials and search/fetch provider
  credentials outside the Author adapter surface.
- Codex should not run AG-LIVE-BOUND-01 through the broker today.
- After AG-LIVE-BRIDGE-01, the user should run the live command manually from a
  private shell or through an allowlisted broker job that returns only the
  sanitized packet.

## Query Candidates

Primary query:

```text
According to the official Python 3 documentation, what are the default values for rel_tol and abs_tol in math.isclose()?
```

Why this is low risk: it is stable programming documentation, public, not
medical, legal, financial, political, safety-critical, private, or news-driven.

Expected source class: canonical public product documentation.

Expected answer components:

- `rel_tol` default value.
- `abs_tol` default value.

Likely initially missing component: `abs_tol`, because summaries often mention
relative tolerance first and omit the absolute tolerance default.

Manual independent check: the official Python documentation page for
`math.isclose()` under `docs.python.org`.

Fit with existing surfaces: ordinary search providers can discover
`docs.python.org`, ordinary fetch/snippet handling can extract bounded text, and
Author can cite a single canonical URL.

Backup query:

```text
According to the official Python 3 documentation, what are the default values for start and step in itertools.count()?
```

Why this is low risk: it is stable programming documentation and asks only for
two exact API defaults.

Expected source class: canonical public product documentation.

Expected answer components:

- `start` default value.
- `step` default value.

Likely initially missing component: `step`, because short search snippets often
foreground the starting value.

Manual independent check: the official Python documentation page for
`itertools.count()` under `docs.python.org`.

Fit with existing surfaces: same ordinary search/fetch/Author/citation surfaces
as the primary query; no new provider, route, depth, or query-generation behavior
is needed.

No live web browsing or provider search was used to choose these candidates.

## Live-Call Budget

AG-LIVE-BOUND-01 caps:

| Budget item | Cap |
| --- | ---: |
| ScryRaven runs | 1 |
| Search dispatches | 2 |
| Fetch/read operations | 3 |
| Author model calls | 1 |
| Optional smart SearchJudgment/model calls | 0 |
| Independent manual source checks | 1 |
| Retries | 0 |

Current enforcement gaps:

- `python -m proplex` has no cap flags for search dispatches or fetch/read
  operations.
- Provider/model helpers have retry wrappers that cannot be disabled by the
  current CLI.
- The ordinary CLI writes a report, not a validation packet with explicit cap
  counts and retention booleans.
- `Balanced` component-gap recovery is offline-only and blocks without an
  injected offline adapter.
- Existing broker-visible jobs do not run ordinary product `run_pipeline()`
  under these caps.

## Output Packet

Planned local untracked packet path:

```text
output/ag_live_bound_01_packet.json
```

The packet must include:

```text
LOCAL/UNTRACKED — DO NOT COMMIT
```

Allowed packet fields:

- exact query;
- run id;
- mode;
- capped call counts;
- final answer;
- final cited URLs;
- bounded sanitized excerpts already allowed by existing content envelopes;
- component binding summary;
- EvidenceLedger, ComponentCoverage, Sufficiency, FAP, and Author posture
  summary;
- no-retention booleans;
- redaction status.

Forbidden packet fields:

- `.env` contents;
- API keys;
- broker tokens;
- raw provider payloads;
- raw prompts;
- raw model requests;
- raw model responses;
- private logs;
- DB/cache rows;
- full raw traces;
- unrelated generated artifacts.

## Success Criteria

AG-LIVE-BOUND-01 should count as success only if one capped ordinary product run
proves all of the following:

- the run executed under the planned caps;
- one initially missing component was recovered, or the system produced the
  expected fail-closed reason;
- the recovered claim is exact and visible in bounded Author material;
- the recovered Source ID or URL is FAP citation-eligible;
- the final answer cites the right source;
- the answer does not include unsupported claims;
- retention posture is clean;
- no second run or retry was needed.

`status: completed` alone is not success.

## Stop Conditions

Stop before or during AG-LIVE-BOUND-01 if any of these are true:

- no cap-enforced ordinary product entrypoint exists;
- the bridge would invoke a component harness while claiming product proof;
- a live call would be needed to finish planning;
- broker/private adapter access is needed for Codex planning;
- `.env`, credentials, private logs, DB/cache rows, raw prompts, raw provider
  payloads, raw model responses, or full traces would need inspection;
- provider routing, provider depth, provider selection, query generation,
  citation behavior, or Author behavior must change;
- a new provider or provider swap is required;
- the query cannot stay low-stakes and bounded;
- a second run or retry would be needed;
- output would require raw/private/full-trace retention;
- product runtime changes become necessary in the live phase itself.

## Failure Classification

| Bucket | Meaning | Next likely surface |
| --- | --- | --- |
| No safe live entrypoint | No cap-enforced ordinary product command exists. | AG-LIVE-BRIDGE-01 runner/broker job. |
| Broker/adapter unsuitable | Broker can only run component/discovery jobs or would expose private state. | Private broker allowlist plus sanitized product job. |
| Provider/search failure | Search provider errors, auth/config missing, timeout, or no canonical result. | Provider configuration or query fit; no retry in live phase. |
| Fetch/read failure | Canonical URL found but page text cannot be read under cap. | Fetch/read adapter/cap wrapper. |
| Evidence custody failure | Recovered source is not admitted as bounded evidence. | EvidenceLedger/provider-job bridge. |
| Semantic component binding failure | Evidence exists but does not bind to the missing component. | ComponentCoverage/SemanticObservation reducer. |
| Sufficiency remains blocked | Coverage remains missing or suspect after recovery. | Sufficiency semantic overlay. |
| FAP evidence binding failure | Bound evidence does not reach FAP citation eligibility. | FinalEvidenceBundle/FAP handoff. |
| Author materialization failure | Bounded claim/source does not reach Author material. | Author payload/materialization. |
| Citation mismatch | Final answer cites the wrong source or omits the source. | Citation survival/final answer packet. |
| Retention violation | Packet or trace retains forbidden raw/private material. | Packet writer/redaction filter. |
| Cap exhaustion | Any cap is exceeded or cannot be proven. | Bridge cap enforcement. |
| Unlicensed change needed | Success would require provider/routing/query/citation/Author changes. | New explicitly scoped implementation phase. |

## Exact Prompt Seed

```text
Run AG-LIVE-BOUND-01 only after AG-LIVE-BRIDGE-01 provides a cap-enforced ordinary product entrypoint. Use the primary query exactly:

According to the official Python 3 documentation, what are the default values for rel_tol and abs_tol in math.isclose()?

Mode: Balanced.
Domain allowlist: docs.python.org.
Caps: max ScryRaven runs 1; max search dispatches 2; max fetch/read operations 3; max Author model calls 1; max optional smart SearchJudgment/model calls 0; max independent manual source checks 1; max retries 0.
Output packet: output/ag_live_bound_01_packet.json.
Packet marker: LOCAL/UNTRACKED — DO NOT COMMIT.
Do not inspect .env, secrets, raw provider payloads, raw prompts, raw model requests, raw model responses, private logs, DB/cache rows, full raw traces, or unrelated generated artifacts.
Fail closed and do not retry on unknown broker job, missing config, provider/model/search/fetch/read error, cap exhaustion, citation mismatch, retention violation, or any need for unlicensed provider/routing/query/citation/Author behavior changes.
```

## Recommended Final Action

Do not run AG-LIVE-BOUND-01 yet. Run AG-LIVE-BRIDGE-01 first to add and test a
dry-run-first, cap-enforced, sanitized product-live runner or broker job. After
that bridge is reviewed, the user should run the live command manually from a
private shell or through the private broker, and share only the sanitized
`output/ag_live_bound_01_packet.json` if review is needed.
