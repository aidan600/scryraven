# Concurrent Exa Search 01

Status: promoted bounded executor change.

Production base: `2d589a7339a3a95fc11641dd1e4365a6cb87a14b`.

Branch: `codex/concurrent-exa-search-01`.

## Scope

Research remains the only semantic owner. This change overlaps network transport
for ordinary generic Exa Search requests that Research has already emitted as
independent requests in one route.

A maximal contiguous group of two or three `kind == "search"` requests may call
Exa concurrently. Deep or Auto is assigned on the coordinating thread before
dispatch, in original `request_index` order. Results are admitted serially in
that order, so candidate IDs, Evidence IDs, source IDs, catalog order, and
novelty follow request order rather than finish order. A failed first Deep still
consumes the fresh-turn bootstrap. One failure does not cancel another
already-dispatched Search, and a concurrent failure is not retried serially.

Groups larger than three are split into groups of at most three, then a
remainder. If the whole group cannot be reserved against the existing external
attempt limit of 16, or the run deadline has already expired, that request uses
the ordinary serial path. The per-request timeout is the run time remaining when
the group is reserved. Workers do not allocate IDs, mutate `AcquisitionLibrary`,
or race the external-attempt counter.

Still serial, and not established as concurrent behavior:

- Search followed by Read, or Read followed by Search, across the boundary
- lexical Search
- Read with Read
- Find
- mixed providers

Exa still requests six results and Dynamic/high Highlights. The Research prompt,
Answer prompt, `ResearchDecision`, and `AnswerDecision` are unchanged. Limits
remain 12 semantic attempts, 16 external attempts, and 300 seconds.

## Live campaign

Four fresh single-turn ordinary product runs. Two frozen reserve questions were
not used because the first four runs already supplied enough successful groups.
Effective configuration, from the existing user model file, was GPT-6 Luna /
high / Fast for Research and GPT-6.1 Sol / high / Standard for Answer. That file
was not modified.

| Run | Question | Posture | Stop | Semantic | External | Turn seconds | Groups |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | St. Dorothy's Rest executive director | supported | supported | 9 | 10 | 135.171 | 0 |
| 2 | MD-80 versus Boeing 777-300 cost per passenger mile | partial | not_established | 12 | 16 | 163.672 | 2 |
| 3 | Caltrain versus Hyundai Ioniq 5 | partial | research_bound | 10 | 16 | 223.047 | 4 |
| 4 | Commercial success of Shoresy | supported | supported | 3 | 2 | 67.328 | 1 |

Run 1 stayed serial because Research did not emit a same-route generic Search
pair. Its Search-then-Read and Read-then-Search routes did not overlap. Run 3
stopped at the ordinary external-attempt limit after a partial answer. No run
exceeded 12 semantic attempts or 16 external attempts.

Recorded `research_completed_elapsed_seconds` matched whole-turn elapsed in each
run because the completed diagnostic is emitted at the end of the turn.

## Performance

Overlap is observed overlapping Exa transport: the sum of the group's transport
durations minus the wall span from the earliest start to the latest end. It is
not a guaranteed user-visible speedup.

| Run | Route | Requests | Summed transport | Group span | Measured overlap | Statuses | Modes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MD-80 | 1 | 2 | 16.578 | 14.953 | 1.625 | ok, ok | deep, auto |
| MD-80 | 8 | 2 | 4.952 | 2.531 | 2.421 | ok, ok | auto, auto |
| Caltrain | 1 | 2 | 14.376 | 12.266 | 2.110 | ok, ok | deep, auto |
| Caltrain | 2 | 2 | 9.906 | 5.812 | 4.094 | ok, ok | auto, auto |
| Caltrain | 3 | 2 | 4.921 | 2.890 | 2.031 | ok, ok | auto, auto |
| Caltrain | 7 | 2 | 5.250 | 3.078 | 2.172 | ok, ok | auto, auto |
| Shoresy | 1 | 2 | 11.344 | 9.281 | 2.063 | ok, ok | deep, auto |

Seven successful groups across three runs. Aggregate measured overlap: 16.516
seconds. Median group overlap: 2.110 seconds. Maximum: 4.094 seconds. Minimum:
1.625 seconds. Every live group was a pair; no live route emitted three
contiguous generic Searches. In each Deep group the Deep and Auto requests
started at the same elapsed time, and the first request index was Deep.

Several second requests in a pair recorded known candidates after the first
request had been admitted, including one known candidate on MD-80 route 1 and
four on MD-80 route 8. That is serial novelty at admission time.

## Quality and custody

All four turns completed. Postures were supported or partial, as the acquired
Evidence warranted. There were no research or answer corrections and no reading
rejections. Every citation source resolved to selected Evidence, and cited
material IDs were members of that selection. No concurrent group showed a
duplicate-admission failure or a missing request result.

No live Deep request failed, so bootstrap consumption on a failed concurrent
Deep was not re-observed in product. Offline tests cover that case.

## Provider and cost

No rate limiting, transport failure, or malformed response occurred on a
concurrent Exa call. Every recorded acquisition status in the campaign was ok.

Estimated spend, using the frozen Exa auto/deep request prices and the frozen
OpenAI short-context snapshot, plus conservative Serper and LinkUp ceilings:

| Run | Estimated USD |
| --- | --- |
| St. Dorothy's Rest | 0.1335 |
| MD-80 | 0.2393 |
| Caltrain | 0.2879 |
| Shoresy | 0.0496 |
| Campaign | 0.7103 |

The $2 ceiling was not reached. No extra source-check or provider-only calls
were made.

## Limits

This does not establish universal latency improvement, perfect parallelism,
lower model cost, better answer quality, mixed-provider concurrency, or
parallel semantic execution. Read, lexical Search, Find, and mixed routes remain
serial. Live evidence did not include a three-Search group or a provider error
inside a concurrent group.
