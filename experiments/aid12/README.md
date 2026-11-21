# AID-12 simple lookup latency

The [opening-request analysis](opening-request.md) is the current follow-up.
The stopping experiment below is retained as negative evidence, including
the hidden correction that a plausible cited highlight failed to establish.

The 50% median elapsed-time target is unresolved. The offline candidate can
remove a scripted redundant Research round, with exact citations preserved.
The closest documented clean lookup already performed the three model requests
and one provider dispatch needed by this candidate. There is no evidence yet
that redundant rounds account for half of current median latency.

Base and control are `8ecf38816a0aea2f146c5af0b600e28decc2a66f`, identical to
`main` when fetched. The candidate adds one instruction in
[stopping.py](stopping.py), applied explicitly in an isolated local experiment
process. It reaches every ordinary Research decision in a turn before Answer,
including decisions after acquisition and on follow-up turns. Delegated Research
uses its separately computed prompt, and Answer uses its ordinary prompt.
Both arms retain the two semantic roles, source custody, validation and provider
configuration. The ordinary Research prompt cache family changes with the
treatment. Startup rejects any prompt other than the registered control and
requires exactly one insertion marker. The registered candidate prompt SHA-256
is `1ec71483e1b6d0c26c2ad621416e37731e996cd3340fc428c4cd95b72ae67092`.

## Evidence for the candidate

[CURRENT.md](../../CURRENT.md) records a historical 304.796-second, ten-turn
flight split between Research model time (65.0%), Answer model time (25.4%)
and external I/O (9.5%). [Latency Consumption 01](../../docs/operator/LATENCY_CONSUMPTION_01.md)
also showed that eliminating a redundant Research round after exposing exact
prior citations saved wall time on two follow-ups. That treatment is already
in the base. Its different models, mixed workloads and cache conditions make
it background evidence.

The [historical research-defaults canary](../../docs/operator/RESEARCH_DEFAULTS_CONSOLIDATION_01.md#production-verification-and-one-canary)
gives the closest documented breakdown for an economical fresh lookup.
Terra/medium made two Research requests (4.344 s and 2.688 s), Sol/medium made
one Answer request (4.703 s), and Exa Lite Search took 0.812 s of the 12.547 s
total. The requests returned `default` through the personal-plan adapter.
A [later browser run](../../docs/operator/READING_ROOM_PRODUCT_UX_01.md#bounded-live-result-and-resources)
observed 12.344 s from submission to completion on a similar question with
the same request counts. Both used the earlier Answer generation and different
revisions. They are historical live data for profiling, with zero observations
of the specified Standard API control or candidate.

In that canary, measured model requests accounted for 93.5% of elapsed time.
Search occupied 6.5%. The candidate targets an extra serial Research request
and redundant acquisition when the Research model already sees a directly
sufficient passage. The observed efficient path has no extra round for it to
remove. Even granting zero Search and overhead, holding the observed model
request durations fixed leaves 11.735 s. A 50% reduction through deletion alone
would require an untreated turn of at least 23.470 s for that model-only floor,
or 25.094 s if all 12.547 s of the necessary path remain.

The observed model calls depend on each other in order. As a scale check, even
deleting the longest physical model request (4.703 s) and all Search time (0.812 s)
would save about 44.0% in that turn, and the deleted request would be Answer.
This arithmetic uses one earlier configuration and fixed per-call durations.
It does not bound how the registered models themselves will behave or generalize
to a current cohort. The evidence supports profiling avoidable work before a
paid comparison. It has not identified a second lever that can plausibly halve
the already-efficient path within this experiment's constraints.

Research remains responsible for judging the entity, period, scope, material
qualifications and completeness of exact acquired text. When evidence is weak
or conflicting, or more support is required, ordinary acquisition remains
available. Answer continues to review the originals, inspect, calculate, or
delegate for a consequential information need.

## Offline result

Run the opt-in replay with the existing development dependencies:

```sh
PYTHONPATH=tests PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q experiments/aid12
```

The tests exercise Reading Room POST, job processing, native strict Responses,
and durable SQLite reopening. Network connections are blocked. Transports,
decisions, returned tiers and sources are fixtures. Across three direct cases
in each arm, the scripted control used 11 physical model requests and 4
acquisition dispatches, versus 9 and 3 in the candidate. The already-efficient
case stayed at 2 Research + 1 Answer and 1 Search. The other two skipped,
respectively, a redundant local reread and a redundant external Read plus the
Research request needed after each. The selected literal support was identical
for each pair.

The seven other initial pairs cover insufficient scope, wrong identity, conflicting
records, multipart work with separate support, native calculation, Answer-led
delegated Research, and an invalid citation. Each arm completes nine of ten
scripted turns and rejects the intentionally invalid citation without saving
an answer. All real inference and acquisition counts are zero. The replay
shows that these decisions can flow through the product intact.

### Counterfactual early stops

Four further pairs replay the same premature stop and the same overconfident
Answer in both arms. The ordinary validators publish the answer with a working
citation and exact saved passage for each of four fixture errors. These are a
wrong entity, an ambiguous entity, a truncated qualification, and unresolved
conflict between credible authorities. Passage offsets and exact text custody
establish what was cited. Whether it supports the claim remains an evidence
judgment, even when Answer marks its posture as supported.
The incompatible second excerpt reaches Answer in the ambiguous and conflicting
cases. Their saved citation groups contain the cited authority alone, so a
review of those groups would miss the other excerpt the model saw.

Three paths in each arm start with the same apparent answer in a permit
register highlight. Only the full original reveals a retroactive correction.

| Scripted path | Published fee | Research requests | Answer requests | Provider dispatches |
| --- | ---: | ---: | ---: | ---: |
| Early stop after highlight | 7 credits, superseded | 2 | 1 | 1 |
| Ordinary Research Read | 9 credits, with the correction passage | 3 | 1 | 2 |
| Early stop with Answer-led recovery | 9 credits, with the correction passage | 4 | 2 | 2 |

The two correct paths reopen the exact correction passage, including when
delegated recovery groups the original highlight and full text under one
citation number. The last path adds two physical requests compared with doing
the Read during ordinary Research. The responses were fixed to exercise these
paths. There is no estimate of how often either model will stop early, recover,
or give a materially wrong answer.

Two isolated runs passed all 48 current experiment checks. Existing focused
checks covering instrumentation, Research, handoffs, Answer
calculation/finalization and Reading Room passed 91/91. The full Linux suite
at the unchanged base recorded 1,556
passed, 207 skipped and 18 failed. Nine failures require the Windows personal-plan
vault. The other nine assert exact request timeouts that shrink by a small
amount between dispatch checks on this clock. That suite ran before the
experiment files were added. One replay started concurrently with another
pytest invocation and saw a 400 on its first fixture with the shared configured
temp path. Both reruns used a dedicated base temp directory and passed.

## Frozen questions for a separately authorized live run

Every case is a fresh, attachment-free conversation. Submit the exact question
text. The pilot questions and the evaluation positives are fixed below. The
right column identifies the expected fact and an authoritative source class for
review. The reviewer verifies each against an original before adjudication.

| ID | Exact question | Expected fact and source |
| --- | --- | --- |
| D01 | According to the BIPM SI Brochure, what is the largest SI prefix? | Quetta, BIPM |
| D02 | On what date did NASA launch Voyager 1? | 5 September 1977, NASA |
| D03 | In what U.S. state is Great Basin National Park? | Nevada, NPS |
| D04 | On what date did the United Nations Charter enter into force? | 24 October 1945, UN |
| P01 | What exact value does NIST give for the speed of light in vacuum in metres per second? | 299,792,458 m/s, NIST |
| P02 | What moment magnitude does the USGS assign to the 1964 Great Alaska Earthquake? | 9.2, USGS |
| P03 | On what date was the North Atlantic Treaty signed? | 4 April 1949, NATO treaty text or history |
| P04 | In which lunar mare did Apollo 11 land? | Mare Tranquillitatis (Sea of Tranquility), NASA |
| P05 | When was Unicode Standard version 15.0 first released? | 13 September 2022, Unicode Consortium release |
| P06 | Which RFC specifies HTTP Semantics in the IETF's June 2022 core HTTP specifications? | RFC 9110, IETF or RFC Editor publication |
| P07 | On what date did ESA launch Gaia? | 19 December 2013, ESA mission documentation |
| P08 | Under Article I, Section 3 of the U.S. Constitution, how many Senators does each state have? | Two, National Archives or Congress transcription |

The negative cases were written and frozen in earlier campaigns, independent
of the treatment. Their exact question text was held out while writing the
candidate and offline fixtures. The pinned sources below identify the verbatim
questions and existing review obligations. Before the first paired submission,
recheck the registered digests. Send only exact question text to ScryRaven.

| ID | Coverage | Frozen question locator |
| --- | --- | --- |
| N01 | Apparently simple identity and scope ambiguity | V2 F07 |
| N02 | Competing evidence and version disambiguation | V2 F06 |
| N03 | Multipart answer | V2 F08 |
| N04 | Calculation | Latency FST1 |
| N05 | Citation-heavy technical synthesis | V2 F05 |
| N06 | Material exception to an apparently simple rule | V2 F03 |

V2 refers to the JSON manifest in
[`docs/operator/V2_CAMPAIGN.md` at the base](https://github.com/aidan600/scryraven/blob/8ecf38816a0aea2f146c5af0b600e28decc2a66f/docs/operator/V2_CAMPAIGN.md)
(blob `a89919ec69c5443e7e690db5b3239b88c5b32511`). Select each case's
`question` and use its `rubric` for review. Latency FST1 refers to the string
bound to `STAGE_B_CASES["FST1"]` (`R1`) in
[`scripts/latency_consumption_01.py` at `ea20fd4`](https://github.com/aidan600/scryraven/blob/ea20fd4072c14218ba9d96b883057e47653e90b2/scripts/latency_consumption_01.py)
(blob `e78babcaab53ba52260c9f0e4d6e084e4bcb9a47`). Extract the string from the
file without executing the historical caller. Review the result against the
stipulated inputs and deterministic arithmetic.

Offline verification resolved both Git blobs, each V2 case as an independent
turn with a nonempty rubric, F06's explicit conflict obligation, and the FST1
AST binding as a string literal. The following SHA-256 values hash UTF-8,
compact sorted-key JSON objects keyed by case ID with verbatim question strings
or the existing rubric arrays as values. This verifies the locators and wording.
Independent factual adjudication against original public material belongs to
the separately authorized run.

| Registered content | SHA-256 |
| --- | --- |
| D01–D04 pilot questions | `c635d48bceb9578400989540ae3cbc4332e9067ee2db815a4710a75cac56d3b7` |
| All 18 questions | `0ba89a458577078bfbf264585644882e405815b42ef15f14eb3328d55afe6cac` |
| Five V2 negative rubrics | `3f4418f4d8390fef5beaf3fbe54e6ea89211f73c5e99a9ce1f0fb86df631f9b0` |

## Live measurement and cost

1. **Screen with four separately authorized control submissions.** Use the
   ordinary local Reading Room and run D01–D04 once each at the pinned control.
   Capture body-free timings with `--dogfood-log`. Use the existing local
   `--forensic-log` for these public questions to capture the exact exposure at
   the proposed return point and the later evidence. Keep those artifacts in
   isolated local storage. Join by session and attempted turn. An independent
   reviewer compares the pre-stop packet, full originals and later evidence.
   Count a round as redundant only if the earlier packet establishes the full
   answer and later work adds no material evidence, qualification or resolution.
   An apparently complete highlight with a later correction is required work.
   A missing packet or incomplete timing cannot support a pilot decision.

   Use [timing.py](timing.py) to profile each complete receipt. Supply reviewed
   ordinary Research request durations from the corresponding ordered forensic
   events and removable external requests by `(route_index, request_index)`.
   For each turn, the route-only estimate subtracts those Research durations
   and only the reduction in the union of external intervals. The more
   optimistic model-only floor makes all provider, local, queue and browser
   time free and keeps the measured durations of the remaining Research and
   Answer requests. Compare each estimate's median across the same four draws
   with half the baseline submit-to-render median. A model-only median above
   that threshold rules out reaching it by the covered deletions at fixed
   retained model timings on these draws. Advance to the paid paired comparison
   only if the route-only median also reaches the threshold and adjudication
   establishes that the proposed skipped work was redundant. Keep the pilot
   separate from paired results.
2. **Compare paired arms only if separately authorized and the pilot supports
   proceeding.** Use the existing credential doorman with the same API account,
   machine, local Reading Room, provider configuration, default limits and
   browser in both arms. Use an explicit `ModelConfig` with
   `gpt-6.1-terra` / medium Research and `gpt-6.2-sol` / medium Answer,
   both API Standard (`default`). Verify requested and returned model and tier
   receipts per request. Keep the sending path ordinary. For the candidate
   process only, set `research.RESEARCH_PROMPT =
   ordinary_research_prompt(research.RESEARCH_PROMPT)` before starting the
   existing `reading_room.create_app` and `serve`, as in replay. A prompt
   registration mismatch aborts candidate setup. Record revision,
   prompt and manifest hashes and reserve one fresh database and log per arm.
   Keep browser polling, cache conditions and provider settings comparable and
   retain the reported cache and tier differences.
3. **Pair in short alternating blocks.** Run P01–P08 in order with alternating
   control-first and candidate-first pairs, then reverse the case sequence and
   swap each case's arm order for the second observation. Run N01–N06 once in
   alternating pairs and repeat N01 and N02 in reversed order. Run one job at a
   time with no automatic retries or case substitutions. Maximum scope is 52
   submissions including the four control pilot draws, 32 positive evaluation
   draws and 16 negative evaluation draws. The repeat schedule is fixed before
   any live results.
4. **Measure submit to rendered answer with working citations.** Time from
   the actual composer submission to the browser's first rendered finished
   answer and citation(s), using one monotonic observer across page navigation.
   For source-free and honest partial/unable controls, time to the appropriate
   terminal render and record its posture. Record admission and commit
   separately. Time to first useful content is secondary. Mark it unavailable
   if the UI only provides progress before the finished answer. Sum durations
   from `physical_model_calls` by role. Answer's enclosing semantic span and
   `research_tool_seconds` already include delegated work. Use the union of
   dispatched external `acquisitions` intervals, one interval per logical
   operation, for time on the external path. A dual Read's provider legs are
   counted separately for cost. Keep worker remainder (including local work)
   and browser timing separate. Record model calls, continuations, provider
   dispatches, fallback routes, failures and missing telemetry.
5. **Review before unblinding.** An independent reviewer checks the saved
   answers and literal excerpts against original public material and the frozen
   obligations, with arm, timings and order hidden. Check fact, entity, time,
   scope, qualifiers, completeness, citation coverage and links, and exact
   citation reopening. Record answer-support failures separately from operational
   failures. Report submission and correct/cited completion denominators,
   per-pair results, each arm's median and nearest-rank p95, and the ratio of
   positive medians. Show the paired full-completion latency subset with its
   denominator and all missing or failed results explicitly. An arm producing
   no correct, cited completion within the common deadline has not hit the
   target for that draw. Claim the bounded median outcome only if the paired
   positive set completes correctly with working citations, the candidate
   median is at most half the control median, and the negatives show no material
   treatment-caused regression. With 16 positive observations per arm, p95 is
   the slowest observation and is descriptive.

No separately billed calls were made. A dollar estimate requires account
access to both specified Standard API models, their effective input, cache-read,
cache-write and output rates, the account's acquisition prices by provider and
operation, and pilot receipts. For each role sum the metered token categories
times their corresponding rates. Reasoning tokens are part of output. Multiply
charged dispatch counts by each provider's rate, including each charged leg of
a dual Read. Calculate a range using the paired counts and pilot variability,
show remaining uncertainty from unseen negative routes and missing receipts,
and record actual charges only when independently available. The authorization
decision can then cover a stated dollar ceiling and the exact bounded round.
