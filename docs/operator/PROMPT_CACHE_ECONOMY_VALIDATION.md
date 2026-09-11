# Prompt-cache economy PRODUCT validation

Outcome: the primary candidate earned the 20% threshold with a **23.62% reduction**
in effective input units. One session / three `ResearchSession.ask` calls completed
on 2026-09-11; no repair or rerun occurred. The live runtime is recorded by commit
`65bdcd1` (its file hashes match the captured running code). Later documentation
changes do not change that runtime.

## Historical baseline and bounded execution

The historical baseline belongs to `IN_MEMORY_FOLLOWUP_VALIDATION.md`, merged in
PR #634 at `50642e768a7e0dd662d12ffb88ab03b1cd227a7e`. Local main was clean and matched
current GitHub main before this branch began. The old implementation was not rerun.

The existing credential broker invoked a sequential caller of the public
`ResearchSession.ask` API with production OpenAI and Exa transports, using unchanged
gpt-5.6-luna / medium defaults for both roles. Exact questions, in order:

1. "According to the BIPM, what four SI prefixes were added in 2022, and what power-of-ten factor and symbol does each represent?"
2. "Which two of those are for factors smaller than one?"
3. "According to NASA, how long is a day on Mars?"

The pass-through observers recorded answers, selected public material, citations,
input equality/identity audits and returned usage. They did not seed evidence,
choose actions, change logical model inputs or perform independent source checks.
Independent source checks: **zero**. An initial sandbox broker invocation could not
read its private environment and never launched the target; it used no live calls.
The same broker then ran under the authorized execution identity. No file permissions
were changed and the controlling agent did not read the environment file.

## Cache configuration and reuse rationale

The implementation follows the current official
[OpenAI prompt-caching guide](https://developers.openai.com/api/docs/guides/prompt-caching)
and [Responses API contract](https://developers.openai.com/api/reference/python/resources/responses/methods/create),
checked on 2026-09-11. It sends `prompt_cache_options={"mode":"explicit","ttl":"30m"}`
and places `prompt_cache_breakpoint={"mode":"explicit"}` on `input_text` blocks.

- The original instructions, including the unchanged JSON-only suffix, occupy a
  developer block with a breakpoint. Each role/subphase reuses its exact prompt
  and Structured Outputs schema across actions or turns.
- The user material remains one complete JSON object split at JSON boundaries.
  Object fields are deterministic; array order and every string are preserved.
  Complete semantic history comes first (conversation context for Author), with
  stable content boundaries after each entry. The latest two entries retain
  breakpoints, so the prior turn's endpoint survives an append. History is never
  promoted to Evidence and no earlier entry is discarded.
- Research navigation also marks the prefix through conversation/history, date,
  phase, question, current need and provisional answer needs. Repeated navigation
  actions can reuse this prefix while candidates and action state change.
- All current candidate/Evidence bodies, previous analysis, acquisition/action
  state and corrections follow those prefixes. No implicit tail writes occur.
  Other stages do not write their one-use question/Evidence/answer-writing tails.

There are at most four markers per request. Prefixes below the API's minimum are
left unpadded; all three Author calls returned zero writes and reads in this run.
`store=False`, Structured Outputs and response parsing remain unchanged. No
`previous_response_id`, Conversations API, persistence or server-held session is used.

Keys have the form `sr-v1:<stage>:<phase>:<32-hex digest>`. The digest derives from
layout version, namespace, model, reasoning, stage, phase, full instructions and
schema, never the changing question or correction. There is no registry. The default
namespace is `scryraven`; this candidate used the fresh namespace
`prompt-cache-economy-01-primary-20260911`. Namespace isolation changes no semantic
input or production key strategy. Keys separate reuse groups; they do not guarantee
cache routing. No prewarming or candidate-to-candidate cache contamination occurred.

## Token classes and economic decision

Input includes cache reads and writes. Reasoning is included in output.
Ordinary uncached = input - cached input - cache write.
Effective input units = ordinary uncached + 1.25 * cache write + 0.10 * cached input.

| Run / turn | Input | Cache reads | Cache writes | Ordinary | Output | Reasoning | Effective units |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Historical total | 41,294 | 10,186 | 30,236 | 872 | 2,820 | 590 | 39,685.60 |
| Candidate 1 | 14,206 | 1,963 | 3,740 | 8,503 | 1,137 | 201 | 13,374.30 |
| Candidate 2 | 9,730 | 3,435 | 2,247 | 4,048 | 595 | 127 | 7,200.25 |
| Candidate 3 | 16,685 | 8,011 | 1,053 | 7,621 | 942 | 332 | 9,738.35 |
| Candidate total | 40,621 | 13,409 | 7,040 | 20,172 | 2,674 | 660 | **30,312.90** |

Calculation: `20,172 + 1.25 * 7,040 + 0.10 * 13,409 = 30,312.9`.
Improvement: `(39,685.6 - 30,312.9) / 39,685.6 = 23.6174%`.
This is below the 31,748.5 acceptance target. Cache-read share rose from 24.67% to
33.01%; cache-write share fell from 73.22% to 17.33%.

The 9,372.7-unit measured difference decomposes arithmetically into 673 fewer total
input tokens, 5,799 fewer units of write premium, and 2,900.7 more units of cache-read
discount. This is a token-class comparison, not proof that changing live selections
had no influence. Total input fell only 1.63%; rich material was not truncated.

| Call | Turn | Family | Input | Read | Write | Ordinary | Output | Reasoning |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | Research orientation | 833 | 0 | 0 | 833 | 231 | 0 |
| 2 | 1 | Research navigation | 2,077 | 0 | 1,963 | 114 | 226 | 16 |
| 3 | 1 | Research navigation | 5,506 | 1,963 | 0 | 3,543 | 221 | 134 |
| 4 | 1 | Analyst | 3,681 | 0 | 1,777 | 1,904 | 354 | 51 |
| 5 | 1 | Author | 2,109 | 0 | 0 | 2,109 | 105 | 0 |
| 6 | 2 | Research orientation | 1,325 | 0 | 1,153 | 172 | 199 | 51 |
| 7 | 2 | Research navigation | 3,909 | 1,658 | 704 | 1,547 | 118 | 30 |
| 8 | 2 | Analyst | 3,072 | 1,777 | 390 | 905 | 234 | 46 |
| 9 | 2 | Author | 1,424 | 0 | 0 | 1,424 | 44 | 0 |
| 10 | 3 | Research orientation | 1,607 | 1,153 | 229 | 225 | 238 | 92 |
| 11 | 3 | Research navigation | 4,190 | 2,048 | 595 | 1,547 | 220 | 25 |
| 12 | 3 | Research navigation | 6,580 | 2,643 | 0 | 3,937 | 162 | 78 |
| 13 | 3 | Analyst | 3,271 | 2,167 | 229 | 875 | 278 | 137 |
| 14 | 3 | Author | 1,037 | 0 | 0 | 1,037 | 44 | 0 |

Navigation reads grew from 1,963 tokens within turn 1 to 2,643 within turn 3.
Across turns, orientation reused 1,153 history-prefix tokens and Analyst reused
2,167 instruction/history tokens. The production observer records only safe counters
and labels; unknown or inconsistent counts do not fabricate ordinary usage.
Effective units and aggregates are calculated by the validation caller, not priced
by product runtime. No dollar prices or metrics service were added.

## Behavioral evidence and limits

| Turn | Result / support | Search | Contents | Research / Analyst / Author | Corpus after |
| --- | --- | ---: | ---: | --- | --- |
| 1 | Supported: ronna R 10^27, ronto r 10^-27, quetta Q 10^30, quecto q 10^-30; E1/E2 | 1 | 0 | 3 / 1 / 1 | E1, E2 |
| 2 | Supported: ronto and quecto; unchanged retained E1 | 0 | 0 | 2 / 1 / 1 | E1, E2 |
| 3 | Supported: 24 h 39 min 35 s, about 1.027 Earth days; new NASA E3 | 1 | 0 | 3 / 1 / 1 | E1, E2, E3 |

Total model/provider counts match the historical 14 / 2 Search / 0 Contents.
Turn 2 resolved "those" from conversation, selected actual unchanged BIPM Evidence,
and made fresh decisions in all three roles. Turn 3 preserved BIPM acquisitions but
selected and cited only new NASA E3. Numeric references remained answer-local.

Actual acquired sources (identities, not independent checks):

- E1: [BIPM Resolution 3](https://www.bipm.org/en/cgpm-2022/resolution-3), 1,726 characters.
- E2: [BIPM SI-prefix table](https://www.bipm.org/en/measurement-units/si-prefixes), 1,429 characters.
- E3: [NASA/JPL Mars at a Glance](https://www.jpl.nasa.gov/news/press_kits/insight/landing/facts/mars-at-a-glance/), 140 characters.

All selected material was provider highlights. The BIPM table supplied the factors
and symbols; the NASA excerpt directly supplied the reported duration. Answers were
reviewed against current findings and selected text; no material semantic/citation
failure was identified. NASA's selected source and published precision differed from
the historical GISS source, as did the second BIPM publication. This is an ordinary
variable product run, not an exact source replay or a general reliability claim.

Every serialized logical material object matched its pre-transport input, every
instruction/schema matched, and every intended conversation/semantic history input
was exact. Prior answers had only conversation fields and were never Evidence.
Analyst/Author source hashes matched acquired material; Author received current
coverage. No protected semantic surface, model/reasoning default, ranking or provider
policy changed. PRODUCT.md is unchanged; CURRENT.md records the measured bounded result.

Offline checks passed: `python -m pytest -q` (248 tests), `python -m ruff check .`,
and `pre-commit run --all-files`. Tests use fake Responses to cover lossless layout,
prefix order/append boundaries, family separation, API payload, optional/malformed
usage, correction retries, parsing and ordinary run/session compatibility. Temp and
cache roots were external under `C:\tmp`; no machine-wide permissions changed.

The exact sanitized packet stays external at
`C:\tmp\scryraven-prompt-cache-economy-01\`, including caller, broker output/status,
answers, exact public selected material, per-call counters and input identity audits.
No raw live packet, full prompt, private payload, credential or hidden reasoning is
published. A sanitized development clean-control candidate is preserved only in the
ignored local evaluation corpus. The observation does not prove arbitrary long
sessions, cache behavior on other models, or universal semantic/provider reliability.
