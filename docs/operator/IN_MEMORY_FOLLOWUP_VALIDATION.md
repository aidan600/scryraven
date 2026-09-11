# In-memory follow-up PRODUCT validation

Outcome: the bounded retained-context capability was demonstrated on 2026-09-11
through one ordinary ResearchSession, with no repair or rerun. The live-tested
revision is `dfca5658049cd1f492fadcae70b972169ddcad15`. Final follow-up changes to
this record and CURRENT.md document the observation; they do not change runtime code.

## Execution and exact questions

The existing credential broker ran a sequential caller of the public
`ResearchSession.ask` API in one process. It used the production OpenAI transport,
Exa transport, Research, Analyst, Author, session state and citation mechanics.
Pass-through observers counted requests and recorded safe input identity facts and
returned usage; they did not change requests, choose evidence, seed the corpus or
script model behavior. Both model roles used gpt-5.6-luna / medium.

1. "According to the BIPM, what four SI prefixes were added in 2022, and what
   power-of-ten factor and symbol does each represent?"
2. "Which two of those are for factors smaller than one?"
3. "According to NASA, how long is a day on Mars?"

| Turn | Result | Search | Contents | Research calls | Analyst calls | Author calls |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | Supported: ronna R 10^27, ronto r 10^-27, quetta Q 10^30, quecto q 10^-30 | 1 | 0 | 3 | 1 | 1 |
| 2 | Supported: ronto and quecto are the factors below one | 0 | 0 | 2 | 1 | 1 |
| 3 | Supported: mean Mars solar day (sol), 24 h 39 min 35.244 s; approximately 24 h 40 min | 1 | 0 | 3 | 1 | 1 |

Total: one session, three ask calls, two Search calls, zero Contents calls and
14 model calls. Each turn had fresh Research orientation and a fresh Analyst and
Author call. Live execution stopped after this primary success. Independent source
checks: zero.

## Retained identity and current evidence

| Turn | Entering canonical IDs | Selected material / support / citation IDs | New IDs | Corpus after | Answer-local numbers |
| --- | --- | --- | --- | --- | --- |
| 1 | None | E1, E2 | E1, E2 | E1, E2 | E1 = 1; E2 = 2 |
| 2 | E1, E2 | E1 | None | E1, E2 | E1 = 1 |
| 3 | E1, E2 | E3 | E3 | E1, E2, E3 | E3 = 1 |

The retained acquisition count was 2 after turn 1, 2 after turn 2, and 3 after turn
3. All three acquisitions were actual `provider_highlights`, with these URLs:

- E1: [BIPM Resolution 3 of the 27th CGPM](https://www.bipm.org/en/cgpm-2022/resolution-3).
- E2: [BIPM announcement of the new SI prefixes](https://www.bipm.org/en/-/2022-12-19-si-prefixes).
- E3: [NASA GISS Mars24 technical notes](https://www.giss.nasa.gov/tools/mars24/help/notes.html).

These links identify the material actually acquired; no independent page checks
were made. The acquired E1 table contained all four prefixes, their symbols and
factors. E2 also contained those facts and the adoption date used in the first
answer. Turn 2 selected the exact unchanged E1 material, with zero new acquisitions.
E1/E2 remained intact through turn 3, whose findings and citations used only E3.
The received NASA passage supplied the mean solar-day duration and distinguished
the sidereal day. The final answer retained the mean/sol scope and its precision.
Answer claims were reviewed against current Analyst findings and selected material;
no material fidelity error was identified in this observation.

## Conversation and semantic-history audit

All intended model inputs received the exact completed question/answer history.
Conversation entries had only `question` and `answer` fields, with no source or
evidence ID. Input audits recorded field names, counts, hashes and equality checks,
not complete conversation/model payloads. Prior answers were not in Evidence bodies
or support references. Research and Analyst also received separate prior semantic
history; the first Analyst assessment of each turn had no inherited current-turn
`previous_analysis` verdict.

Actual Analyst/Author evidence content hashes matched the selected acquired
material. Every support reference resolved to current Evidence. Author received
the exact current Analyst coverage and its supporting material; the rendered
citations resolved to those sources and current selected items. This confirms the
observed handoffs, not a general semantic verifier.

## Returned token/cache counters

| Turn | Input | Cached input | Cache write | Output | Reasoning |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 13,285 | 1,658 | 10,782 | 1,203 | 243 |
| 2 | 9,723 | 3,435 | 6,276 | 651 | 140 |
| 3 | 18,286 | 5,093 | 13,178 | 966 | 207 |
| Total | 41,294 | 10,186 | 30,236 | 2,820 | 590 |

These are sums of returned counters, including repeated context submissions.
Cached input is included in input; reasoning is included in output. A separate
cache-creation counter was not returned. No caching/request-layout, model-default,
reasoning, provider or ranking policy changed. No cache optimization was performed.

## Evidence custody and limits

The external packet is `C:\tmp\scryraven-in-memory-followup-live-01\`.
It contains the caller, execution manifest, broker-sanitized outputs, exact public
selected material, findings/answers, per-turn traces and identity audits, usage,
artifact hashes and the final review bundle. It contains no environment file,
credentials, raw private provider payloads or hidden reasoning. A sanitized
multi-turn clean-control candidate was preserved in the ignored local evaluation
corpus with development status; no corpus contents are published.

This single live control demonstrates retained-highlight reuse and unrelated new
acquisition. Full-parent reuse, different exact large-source packets and failed-turn
isolation retain their deterministic offline evidence. It does not establish
general conversational reliability, universal provider reliability, or semantic
fidelity across other questions. Sessions remain in-memory only, with no
persistence, vector database, generalized RAG, uploads, compression or fourth
semantic owner.
