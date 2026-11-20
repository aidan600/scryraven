# AID-12 simple lookup latency

The 50% median elapsed-time target is unresolved. The offline candidate can
remove a scripted redundant Research round, with exact citations preserved.
The closest documented clean lookup already performed the three model requests
and one provider dispatch needed by this candidate. There is no evidence yet
that redundant rounds account for half of current median latency.

Base and control are `8ecf38816a0aea2f146c5af0b600e28decc2a66f`, identical to
`main` when fetched. The candidate is the single initial Research instruction
in [stopping.py](stopping.py), applied explicitly in an isolated local
experiment process. The control uses that revision's ordinary initial Research
prompt. Both use the same delegated Research prompt, Answer prompt, two semantic
roles, source custody, validation and provider configuration. The initial
Research prompt cache family changes with the treatment. The production tree
and its defaults, `CURRENT.md`, legacy runner and shared benchmark files need
no edits for this comparison.

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
Even eliminating the entire Search duration would save only 6.5%. The candidate
targets the extra serial Research request and any redundant acquisition when
the existing Research model already sees a directly sufficient passage.
If the necessary steps took the same 12.547 s as in the canary, a 50% reduction
would require an untreated turn of at least 25.094 s whose remaining time was
all avoidable. These are illustrative bounds using historical timings. A
three-request control leaves no request to remove by this mechanism. Bypassing
either model, prefetching based on question shape, and treating navigation-only
metadata as evidence would change the product contract or the provider workload.

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

The seven other pairs cover insufficient scope, wrong identity, conflicting
records, multipart work with separate support, native calculation, Answer-led
delegated Research, and an invalid citation. Each arm completes nine of ten
scripted turns and rejects the intentionally invalid citation without saving
an answer. All real inference and acquisition counts are zero. The replay
shows that these decisions can flow through the product intact. It supplies no
rate of real model stopping, false shortcuts, answer correctness, or latency.

Two isolated replay runs passed 20/20. Existing focused checks covering
instrumentation, Research, handoffs, Answer calculation/finalization and Reading
Room passed 91/91. The full Linux suite at the unchanged base recorded 1,556
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
questions and existing review obligations. Open them in the evaluation phase
and record the question and rubric hashes before the first paired submission.
Do not disclose case labels or rubrics to ScryRaven.

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

## Live measurement and cost

1. **Screen with four control submissions.** Use the ordinary local Reading Room
   and its body-free `--dogfood-log`. Run D01–D04 once each at the pinned control.
   Review the exact saved sources and the ordered timings. Count a round as
   avoidable only if the evidence available before it already supports the full
   answer and later work adds no material evidence, qualification or resolution.
   Estimate an optimistic per-case duration by subtracting only those redundant
   Research and acquisition intervals from elapsed time. If the median still
   exceeds half of the pilot median, stop the paid comparison of this mechanism
   for the 50% target. Keep the pilot separate from the paired analysis.
2. **Compare paired arms only if separately authorized and the pilot supports
   proceeding.** Use the existing credential doorman with the same API account,
   machine, local Reading Room, provider configuration, default limits and
   browser in both arms. Use an explicit `ModelConfig` with
   `gpt-6.1-terra` / medium Research and `gpt-6.2-sol` / medium Answer,
   both API Standard (`default`). Verify requested and returned model and tier
   receipts per request. Keep the sending path ordinary. For the candidate
   process only, set `research.RESEARCH_PROMPT =
   initial_research_prompt(research.RESEARCH_PROMPT)` before starting the
   existing `reading_room.create_app` and `serve`, as in replay. Record revision,
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
   if the UI only provides progress before the finished answer. Use physical
   model-call durations by role and union of dispatched external acquisition
   intervals from the dogfood log to profile model versus provider time. Keep
   queue, browser polling, local tooling, and unexplained remainder visible.
   Avoid counting concurrent provider time twice or attributing nested Research
   to both roles. Record model calls, continuations, provider dispatches,
   fallback routes, failures and missing telemetry.
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
