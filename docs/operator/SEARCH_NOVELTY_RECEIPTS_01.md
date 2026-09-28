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

Continuation calibration is pending offline verification and the authorized
maximum ten submissions. It uses same-state merged-main controls from `016d3198`
and the candidate treatment, including reconstructed PR #660 failed-Read history
in both arms. No conclusion about efficacy is established by implementation.
