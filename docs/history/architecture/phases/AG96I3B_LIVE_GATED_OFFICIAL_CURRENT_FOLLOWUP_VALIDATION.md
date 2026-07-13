Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I3B_LIVE_GATED_OFFICIAL_CURRENT_FOLLOWUP_VALIDATION).

# AG-96I3B Live-gated Official/Current Follow-up Validation

## Status

AG-96I3B opens the first tightly gated live-validation harness for the
AG-96I3A follow-up provider-job seam:

```text
provider_job_kind=official_current_candidate_acquisition
```

The harness is not product answer behavior. It validates that a
RunKernel-authorized official/current follow-up action can be consumed by a
bounded live adapter, sanitized to candidate-level facts, and then handed back
to the existing AG-96I3A provider-job execution seam. The downstream answer
contract remains:

```text
RunAuthorityContract
-> EvidenceLedger
-> SufficiencyJudgment
-> FinalAnswerPacket
```

No separate follow-up answer contract, EvidenceLedger, sufficiency doctrine, or
FinalAnswerPacket authority was added.

## Live Gate Opened

Runtime added:

- `core.followup_provider_job_live_validation_runtime`;
- `scripts/ag96i3b_live_followup_validation.py`;
- offline tests in
  `tests/test_ag96i3b_live_gated_followup_provider_job_validation.py`.

The live gate requires:

- explicit `live_validation_authorized=True`;
- a RunKernel-authorized
  `ActionType.FOLLOWUP_PROVIDER_JOB_EXECUTE` action;
- `provider_job_kind=official_current_candidate_acquisition`;
- the existing AG-96I3A `bounded_provider_job_offline` execution seam;
- either `authorized_query_ref` or sanitized `authorized_query`, and executable
  sanitized query text for the actual provider/search call.

The live adapter records validation counters separately, then feeds only
sanitized candidate facts into `execute_followup_provider_job_action(...)`.
RunKernel remains the owner of canonical follow-up execution state. The adapter
does not mutate action inputs and cannot mark evidence satisfied, sufficiency
ready, packet ready, citation eligible, Author activated, or product answer
behavior changed.

## Exact Budget

The approved AG-96I3B budget was:

- provider/search calls: at most 1;
- fetch/read attempts: 0 in the implemented candidate-acquisition gate;
- model calls: 0;
- AuthorExecutor calls: 0;
- retries: 0.

The adapter calls the configured search function once and does not loop or
retry. The implemented default live surface is the existing
`core.search_providers.brave_reconnaissance` search wrapper because it returns
title/URL-level search results and has no retry decorator. If `BRAVE_API_KEY` is
not already present in the process environment, the harness stops as
configuration missing. It does not inspect `.env` or print secret values.

## Exact Query

The only approved validation query was:

```text
What is the current IRS standard mileage rate for business use of a car in 2026, and what official source supports it? Keep the answer concise.
```

The query is passed as sanitized `authorized_query` on the sealed follow-up
candidate. The adapter does not generate, expand, mutate, or route query text.

## What Stayed Closed

AG-96I3B did not open:

- AuthorExecutor;
- Author prompts or prose;
- citation rendering or citation formatting;
- product final-answer activation;
- provider routing policy;
- provider selection policy outside the explicit validation harness default;
- query generation or mutation;
- retrieval ranking or filtering policy;
- fetch/read execution;
- source-class recovery executor policy reuse as follow-up authority;
- `core/pipeline_orchestrator.py` domain logic;
- new providers;
- package, CLI, or environment renames;
- secrets, `.env`, raw provider payloads, raw snippets, raw page text, raw
  prompts, model response text, DB rows, cache rows, private logs, full traces,
  or committed output packets.

## Live Validation Result

The local validation command was run once after the focused offline suites
passed:

```powershell
py scripts\ag96i3b_live_followup_validation.py
```

Result:

```text
live_validation_status=config_missing_not_run
provider_config_available=false
provider_search_call_count=0
fetch_read_attempt_count=0
model_call_count=0
author_executor_call_count=0
```

The existing Brave search configuration was not available in the environment.
The harness stopped before provider/search execution, did not inspect `.env`,
and did not retain or print any secret value. Because no live provider result
was available, no candidate URL/title/domain was acquired in the local packet.

## Sanitized Result Summary

The local packet records:

- candidate URL: none;
- title: none;
- domain: none;
- source class: `unknown`;
- currentness signal: `not_evaluated`;
- fetchability/readability: `not_evaluated`;
- stop reason: `provider_config_missing`.

No raw provider payload, raw page text, raw snippets, prompt text, model output,
API key, `.env` value, DB row, cache row, private log, or full trace was
retained.

## EvidenceLedger / Sufficiency / Packet Posture

Because configuration was missing, the live gate stopped before a provider-job
execution observation was produced. The local validation packet records:

- follow-up execution state: not reached;
- EvidenceLedger intake: not reached;
- SufficiencyJudgment recheck: not reached;
- FinalAnswerPacket preparation: not reached;
- Author activation: false;
- citation rendering: false;
- product answer behavior changed: false.

Offline tests prove the positive path with fake search results: sanitized live
candidate facts reduce through the same RunKernel-owned provider-job execution
state, the same EvidenceLedger intake mode
`bounded_provider_job_offline_followup_intake`, the same SufficiencyJudgment
recheck posture, and the same FinalAnswerPacket closure.

## Output Packet

The local ignored packet path is:

```text
output/ag96i3b_live_followup_official_current_validation_packet.md
```

Ignore verification:

```text
.gitignore:39:output/ output/ag96i3b_live_followup_official_current_validation_packet.md
```

The packet begins with:

```text
LOCAL/UNTRACKED — DO NOT COMMIT
```

The committed repository contains only this architecture note, the runtime
harness, the script, and offline tests. The local output packet remains ignored
and must not be committed.

## Recommended Next Phase

Recommended next phase: rerun the same AG-96I3B gate only after an existing
search configuration is available in the environment, or add a similarly
tightly bounded validation gate for a fetch/read continuation only if the
RunKernel provider-job seam explicitly authorizes fetch/read. The next phase
should keep the same answer contract, EvidenceLedger, SufficiencyJudgment, and
FinalAnswerPacket authority, and should continue to forbid query generation,
provider routing changes, Author/citation/product behavior, raw payload
retention, and `pipeline_orchestrator.py` domain logic.
