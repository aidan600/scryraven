# Search Novelty Receipts 01

Initial experiment (before the focused continuation below): implementation and
bounded calibration completed. Campaign signal:
**MIXED / INCONCLUSIVE**. No stopping improvement is established.

## Implementation and semantics

Starting merged main: `016d3198e4ecabf3b68171ddbaea1c97cace87c6`.
Implementation/offline/live-tested revision:
`8c678813ff61660bf8c3055b007553ab24c17b11`.
Branch: `codex/search-novelty-receipts-01`. Subsequent review documentation does
not change production behavior. This work grants no merge authority.

Each successful Exa Search or Serper lexical Search returns this body-free shape:

```json
{
  "provider": "exa",
  "kind": "search",
  "returned_candidate_count": 6,
  "new_candidate_count": 2,
  "known_candidate_count": 4,
  "returned_material_count": 6,
  "new_material_count": 6,
  "new_candidate_material_count": 2,
  "refreshed_known_candidate_material_count": 4,
  "exact_reused_material_count": 0
}
```

This example is the final receipt at both frozen decision points. Candidate
identity uses the library's existing exact observed URL key and admission check.
Counts are unique candidate identities and unique material IDs, measured against
the library before the request. New material partitions by whether its candidate
was already known. Exact reuse preserves `_retain`'s URL/text/acquisition-kind
identity. Duplicate provider slots do not inflate counts; distinct new versions
for one candidate remain separate material IDs. Navigation without admissible
highlights creates no material count. Serper's material counts remain zero.

The ordered `search_novelty_receipts` list survives intervening routes within one
turn. New turns, including reopened sessions, start empty. It is neither Evidence,
Answer input nor durable session state. `last_route` still carries concrete refs.
There is no score, threshold, suppression, stop recommendation or additional
semantic owner. Research alone judges expected value and sufficiency.

Production changes are confined to acquisition accounting, turn-local Research
packet/history, its compact prompt explanation, volatile serialization order and
allowlisted body-free diagnostics. No provider, Answer prompt/serialization/cache
family, model setting, budget, timeout, Read/Find, citation or UI behavior changed.
The Research instruction/cache family changes; the stable prefix and explicit
breakpoints do not. There were no explicit removal obligations.

## Offline verification

- Focused acquisition/history/cache/failed-Read checks: 113 passed.
- Focused history/Reading Room/privacy/forensic/timing checks: 62 passed (overlap
  with the preceding checks and full suite).
- Full offline suite: 585 passed. An initial sandboxed run had four filesystem
  permission failures in forensic-launcher tests; the permission-adjusted full
  rerun passed without changing those tests or production code.
- Ruff, all configured pre-commit hooks and `git diff --check`: passed.
- A synthetic credential-bearing invalid URL in a test has an explicit
  detect-secrets allowlist annotation; it contains no real credential.

Tests establish six-new and four-known/two-new searches, duplicates and rejected
entries, exact reused/refreshed/new candidate material, navigation-only results,
Serper admission, empty/failed/denied requests, Read/Find survival, continued
research with zero candidate novelty, next-turn/reopen reset, Answer/session
exclusion, unchanged external accounting, diagnostic allowlisting, exact stable
packet prefix and Evidence bytes, volatile ordering and unknown-field retention.

## Frozen calibration

Exactly four OpenAI Research submissions, two per state, used production
`gpt-6-luna`, high reasoning and Fast service. All four returned Fast and valid
structured ResearchDecision objects. No transport failures, replacement draws,
Exa/Serper/LinkUp calls, Answer calls or end-to-end product runs occurred. Returned
routes were not executed. No production behavior was tuned after the results.

| Case/draw | Preserved historical decision | New decision | Assessment |
| --- | --- | --- | --- |
| A/1 | Qualified answer proposal | Another audience/demographic Search with media-kit terms | Near-equivalent route; no clear improvement |
| A/2 | Qualified answer proposal | Qualified audience-profile answer proposal | Preserves useful supported scope |
| B/1 | Read modeled-cost analysis plus comparability Search | Full FAA Read C122 plus targeted Form 41 Search | Preserves consequential unresolved lead |
| B/2 | Same historical decision | Two cost-comparability Searches | Preserves unresolved cost/load-factor need; no direct FAA Read |

Case A uses run `20260927-200208-927589c2e2c1`, session
`a85afe306c1b4a3eb08b2985803543d1`, turn 3: acquisition event 57,
model-start event 59, exposure event 60 and historical decision event 62.
Its three Search receipts have new/known candidate counts 4/2, 5/1 and 2/4.

Case B uses run `20260924-162747-84ca18fe82ca`, session
`7757bee8dd7e453c8aacb83e40c07bce`, turn 1: acquisition event 75,
model-start event 77 (Research call 9), exposure event 78 and decision event 80.
This is the specified seventh Search query, in route 8; artifact indexing is
recorded rather than assuming the informal R8 label was the next model call.
E42/C122 is the new FAA operating-cost lead. Its seven Search receipts have
new/known candidate counts 6/0, 4/2, 3/3, 4/2, 3/3, 1/5 and 2/4.
Every Search at both states returned six newly retained highlight records and
zero exact reused records. Thus repeated URLs did not imply repeated exact text.

Reconstruction used read-only access to the two authorized session databases and
observer logs. Offline replay through AcquisitionLibrary matched every recorded
acquisition result, every exact ordered Evidence exposure, and historical catalog
and conversation character counts through the chosen decisions. Source text,
conversation and working understanding were not rewritten. Only top-level novelty
history was added to the reconstructed historical packet; historical last_route
was preserved. Failed-Read history was absent in those older packets and was not
retroactively added. The new current production Research prompt was used.

Limits: full historical packets were not logged. Catalog identity was checked by
replay and character counts, not an original saved packet hash. Budget timing is
reconstructed from rounded model-start counters; original sub-millisecond
precision is unavailable. Treatment packet and observer hashes, event references,
receipts, decisions, safe usage and adjudication are preserved locally. These
are frozen decision observations, not ordinary-product completion evidence.
Historical A already chose to answer, so the results do not establish an
improvement from the new prompt/receipt combination. Four calls are not
reliability proof; no general quality, cost or latency claim follows.

## Safe campaign totals and custody

Total model-call wall time: 29.735 seconds (A: 6.594 and 7.266;
B: 6.875 and 9.000). Reported tokens: 118,668 input, 7,075 cached input,
3,331 cache-write, 108,262 ordinary uncached, 3,946 output, including 2,299
reasoning tokens. Only token counters are retained, never hidden reasoning.

Local-only campaign packet:
`C:\Users\aidan\ScryRaven\local-evals\campaigns\search-novelty-receipts-01\`.
It includes reproduction scripts, provenance and hashes, an exclusive submission
ledger, four structured decisions and adjudication. It is Git-ignored. Exact
source-bearing forensic artifacts remain in the two original authorized runs;
no full source bodies or raw provider payloads were duplicated into the review
bundle. Broker-safe launch/status output remains at
`C:\tmp\sr-search-novelty-receipts-01\`.

The A/1 continuation is also preserved as a local diagnostic candidate
`search-novelty-shoresy-continuation-20260928`, with references to the campaign
and frozen artifacts. It is a development candidate, not a proven semantic error
or a self-contained frozen test. The commercial-success candidate was untouched.
No commercial-success sufficiency or Answer-voice work occurred.

## Focused continuation: query attribution and expected marginal yield

Starting PR HEAD: `a392a087ff5527475084ba124d2a1ca7aeec32d2`.
The first experiment above remains MIXED / INCONCLUSIVE. Counts alone could not
identify which evidentiary avenue had returned them, and changed highlight bytes
did not establish informational progress. This continuation replaces the
model-facing `search_novelty_receipts` field with `search_route_receipts`, without
an alias or parallel history. Each entry adds the exact executed query to
provider/kind and six counts: returned/new/known candidates, new-candidate
material, refreshed-known-candidate material and exact reused material. Internal
acquisition receipts and body-free diagnostics retain all eight original counts;
the two model-history material totals are derivable from the partitions.
Diagnostics never receive query text. Answer and session state receive no history.

The novelty-only prompt paragraph is replaced with:

```text
search_route_receipts records earlier Search queries and mechanical candidate/
material returns. Use it with current Evidence, failed_external_reads and the
unresolved need to judge expected marginal yield: does a consequential question
remain, and can this route plausibly improve the answer at reasonable expected
cost? Novelty alone warrants neither continuing nor stopping: new candidates can
be irrelevant; known sources can expose decisive information or consequential
leads. Do not research merely because more material can be found. For a new
empirical dimension, distinguish Evidence that bears on it from adjacent
indicators or proxies when more direct Evidence is reasonably obtainable.
```

Expected marginal yield remains the existing Research owner's semantic judgment.
No numeric mechanism, semantic similarity, new decision field, stopping gate or
suppression is introduced. Existing stopping principles remain. Provider,
Read/Find, Answer, model defaults, budgets, timeouts and session schema stay fixed.

Continuation result: **MIXED / INCONCLUSIVE; architectural decision required**.
The model-facing feature is **not earned for merge**. No further tuning, third
campaign or automatic removal/revert is authorized by this result. PR #661 remains
a review surface, not a merge recommendation.

### Continuation verification and exact shapes

Tested implementation: `b01db48e1d50fc6b1fc68db538ae60eaff70f147`.
Focused acquisition/history/privacy/cache checks: **165 passed**. Full offline
suite: **585 passed**. Ruff, every configured pre-commit hook and diff checks
passed before live submissions. Subsequent tracked changes are documentation only.
Tests retain query attribution across differently worded Searches and Read/Find,
continued acquisition with repeated candidates, attempt counts, next-turn/reopen
reset, Answer/session exclusion and body-free diagnostic query exclusion.
Control serialization was also checked against merged-main code for all three
states: exact input bytes and cache breakpoints match. Answer prompt bytes remain
unchanged. No scores or semantic flags were added.

Model-facing entry (example values):

```json
{
  "query": "the exact executed Search query",
  "provider": "exa",
  "kind": "search",
  "returned_candidate_count": 6,
  "new_candidate_count": 2,
  "known_candidate_count": 4,
  "new_candidate_material_count": 2,
  "refreshed_known_candidate_material_count": 4,
  "exact_reused_material_count": 0
}
```

The unchanged internal `search_novelty_receipt` and body-free diagnostic shape
shown in the first experiment contain no query and additionally retain
`returned_material_count` and `new_material_count`. The latter equals
new-candidate plus refreshed-known material; returned material adds exact reuse.
The exact-reuse field remains present even at zero for unambiguous semantics.
The ordinary model-facing `last_route` still contains concrete requests/refs and
the complete internal accounting; only cumulative history omits derivable totals.

### State selection and paired controls

Controls use the exact merged-main Research prompt at
`016d3198e4ecabf3b68171ddbaea1c97cace87c6`, without the Search history or expected-yield
paragraph. Treatments use the candidate prompt above. Both receive the same
question, conversation, actual Evidence, working understanding, catalog, pending
state and budget, plus the same reconstructed PR #660 failed-Read history.
Treatment alone adds query-attributed history and the ordinary internal novelty
receipt on a Search result in `last_route`. Historical decisions are provenance,
not the paired controls. Draws alternated control then treatment for each pair.

- **A:** `20260925-121921-60961b775260`, session
  `8b902152d5b940679bcf88838ab99c35`, turn 2; model-start event 83, exposure 84,
  decision 86 (Research call 7). This follows the full USA Today/Keeso success
  at result 79 and failed full Reads at results 77 (Dipp/C26) and 82
  (Telegraph/C27), before the broad Search cycle at decision 86. Five Search
  route receipts are supplied to treatment. Both arms receive the two failures,
  with recorded durations 23.578 and 11.797 seconds.
- **B:** `20260927-200208-927589c2e2c1`, session
  `a85afe306c1b4a3eb08b2985803543d1`, turn 4; model-start event 70, exposure 71,
  decision 73. This is the commercial-success decision before market-research
  pushback, with zero current-turn Searches and empty failed-Read history.
  Both arms therefore have no earlier routes; treatment history is empty.
  The named preserved candidate documents turn 5 and its turn-4 prior answer,
  so it was used as provenance, not mistaken for this replay state. Its use
  status is now development; its frozen artifacts and provisional gold were
  not changed. No personal conversation was duplicated into the campaign files.
- **C:** the first experiment's MD-80 state: `20260924-162747-84ca18fe82ca`,
  session `7757bee8dd7e453c8aacb83e40c07bce`, turn 1; model-start 77, exposure 78,
  decision 80. Seven Search receipts are supplied to treatment. Both arms include
  the prior C11 failed full Read (2.922 seconds). The new FAA lead remains E42/C122.

Every reconstructed acquisition result and ordered Evidence exposure matched the
preserved trace; catalog and conversation character counts matched at every
replayed model call. Control/treatment shared state is asserted equal after
removing only candidate Search-history/accounting fields. Packet and prompt
hashes and observer provenance remain in local case records. As in the first
experiment, full historical packets were not logged, and budget timing has only
the recorded rounded precision. Historical failures carry generic `read_failed`;
missing transport details cannot justify inventing more specific current codes.

### Ten-submission result

Exactly **10** OpenAI submissions used Luna / high / Fast. All ten returned Fast
usage records; no transport failure was recorded. **Nine structured decisions
were preserved; one draw is unadjudicable.** No returned route was executed, and
no Exa, Serper, LinkUp, other source provider, Answer or end-to-end turn ran.

| Case/draw | Control | Treatment | Paired assessment |
| --- | --- | --- | --- |
| A/1 | Similar Wayne motivation/emotional-life Search | Answer at supported depth | One favorable treatment observation |
| A/2 | Answer at supported depth | Local validation failed; decision lost | Pair cannot be adjudicated |
| B/1 | Direct commercial-performance Search | Direct performance Search plus full business-article Read | Both address the empirical dimension |
| B/2 | Direct commercial-performance Search | Qualified yes from launch attention and ancillary business activity | Treatment fails the low-yield-justification requirement |
| C/1 | Two comparable-cost Searches | Two comparable-cost Searches | Both preserve unresolved comparison and continuation |

A/control/1 states a desire to strengthen Wayne coverage but offers another
near-equivalent broad route without a distinct consequential missing answer
capability. A/treatment/1 answers while distinguishing creator commentary and
interpretation. B/treatment/2 acknowledges missing financial totals but declares
no remaining need and gives no reason a direct performance route would have low
expected yield; this is negative under the approved rubric despite its qualified
wording. Both C arms engage the FAA aggregate/type-specific limitation and
preserve the unresolved cost/load-factor basis, without novelty-based stopping.

No clear directional improvement satisfying the merge standard is established:
A is incomplete, B has a treatment regression against two direct-acquisition
controls, and C is preserved. This is MIXED / INCONCLUSIVE, not a positive signal.
Even a positive ten-call campaign would be a bounded signal, not reliability proof.

### Lost-draw limitation

The executed local runner applied schema parsing and extra reference/action
checks before saving the structured result. A/treatment/2 hit its generic
`campaign_validation_failed` path. Its decision and exact exception details were
not retained, so the trigger cannot be determined or its action recovered.
In particular, the runner incorrectly required references to belong to the
current packet, while production accepts references exposed earlier in the same
turn. That overly strict check could reject a product-valid decision. It is
not evidence of a model semantic failure or transport failure. The original
executed runner is retained unchanged for audit, and no claim is made that all
ten decisions were preserved. The submission counts against the cap; no
replacement, correction call or third campaign was made. This evidence-capture
defect limits the experiment independently of the observed B treatment regression.

### Safe totals and handoff

| Arm | Seconds | Input | Cached | Cache-write | Ordinary uncached | Output | Reasoning tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Control (5) | 36.297 | 109,331 | 9,733 | 4,465 | 95,133 | 4,943 | 2,664 |
| Treatment (5) | 45.531 | 111,587 | 10,237 | 4,591 | 96,759 | 5,411 | 3,368 |
| Total (10) | 81.828 | 220,918 | 19,970 | 9,056 | 191,892 | 10,354 | 6,032 |

Totals include the unadjudicable draw. Reasoning counts are usage metadata;
no hidden reasoning was saved. These timings do not establish general speed or
cost effects. The original four-call experiment remains separate and unchanged.

Local continuation packet:
`C:\Users\aidan\ScryRaven\local-evals\campaigns\search-novelty-receipts-01\expected-yield-continuation\`.
It retains the preregistered plan/rubric, reconstruction and executed runner,
case/arm packet hashes, supplied route history, ten exclusive submission records,
nine decisions, all ten safe usage/timing records, offline verification and
adjudication. Source bodies remain only at the original authorized forensic paths.
A local diagnostic candidate, `search-route-commercial-premature-stop-20260928`,
references B/treatment/2 and the paired evidence without duplicating full sources.

The old counts-only model-facing field and explanation are completely replaced;
internal novelty accounting survives intentionally. No other removal was requested.
No production behavior changed after seeing live outputs. The same branch and
PR #661 are retained, **NOT MERGED**. Human architectural choice is required:
strip model-facing history and keep diagnostics, abandon/revert the PR, or
pursue a different semantic hypothesis later. None was applied automatically.
