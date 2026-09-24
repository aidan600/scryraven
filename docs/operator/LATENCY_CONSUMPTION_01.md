# ScryRaven Latency Consumption 01

## Outcome and tested boundary

**The staged comparisons support KEEP HIGH, STANDARD, and PROMOTE PRIOR-CITED
INITIAL EXPOSURE.** The source-free presentation correction is independently
verified offline. These decisions concern fixed Research execution and one
bounded follow-up attention change; Answer remains GPT-6 Sol / medium / Standard.
The 28 staged Reading Room submissions and one final default-path follow-up used
29 of the authorized 30. The staged comparison revision was
`ea20fd4072c14218ba9d96b883057e47653e90b2` on
`codex/latency-consumption-01`, descended from the clean expected `main` at
`82fa75de35a165574369680f3c13e0ea56ea7c55`. All 12 credential-broker
staged invocations recorded that revision and identical hashes for the nine
selected runtime/caller source files. The final default-path canary exercised
implementation revision `95cdbdd` after promotion. No provider request was made
outside ScryRaven.

The development-only campaign caller at checkpoint `ea20fd4` submitted fixed
public questions through the ordinary Reading Room HTTP route,
`ResearchSession`, and SQLite store. It was removed from the final product tree
after the comparisons. Its explicit
experimental `ModelConfig` fixed Answer at Sol / medium / `default`; only the
specified Research effort, Research service tier, or prior-cited exposure flag
varied by stage. Every model call's requested and returned service tiers were
recorded in body-free dogfood diagnostics. Source material, prompts, raw provider
responses, and hidden reasoning were excluded from those logs. Public answers,
citations, and a whitelisted decision/route trajectory were saved separately.
The existing credential doorman supplied secrets; the controller never read
`.env` or raw SQLite rows.

## Stage 0 — source-free disclosure

Before, a supported source-free answer about a future British Museum visitor
total could say it was derived from assumptions the user had not supplied.
`SessionTurn` does not retain Answer's `support_basis`, so citation absence alone
cannot prove premise provenance. CLI, standalone HTML, and Reading Room now say
**“No external sources were used for this answer.”** for source-free supported
or partial turns. The British Museum regression and premise-only presentation
checks passed offline before live comparisons. C1 was not repeated live.

## Stage A — Luna / high versus Luna / medium

Research alone changed reasoning effort. Both arms used Luna, explicit Standard
processing, unchanged Research prompt/schema, providers and limits, and
Sol / medium / Standard Answer. The initial six submissions per arm were
sequential and used isolated arm stores/logs. R2a and R2b shared one session
inside each arm.

| Initial six-turn total | High | Medium |
| --- | ---: | ---: |
| Turn wall time | 146.047 s | 104.250 s |
| Research time / calls | 90.094 s / 16 | 60.234 s / 14 |
| Semantic / external attempts | 22 / 13 | 20 / 11 |
| Research input / cached / cache-write tokens | 95,800 / 26,553 / 2,287 | 76,849 / 23,010 / 2,294 |
| Research output / reasoning tokens | 7,253 / 3,705 | 4,437 / 1,528 |
| Approx. Research cost | $0.010874 | $0.007890 |

Medium initially saved 29.860 Research seconds (33.1%), 41.797 total seconds
(28.6%), and about $0.002984 Research cost (27.4%). Both arms answered the
premise calculation, BIPM seed/follow-up, Anker missing-premise case, and first
Passport case usefully. Both BIPM follow-ups selected one local Read. Different
valid source choices were not counted as failures. R5 medium used one official
St. Dorothy's announcement and gave a useful but narrower qualifications answer;
high connected the new appointment to independent Aldersgate history and staff
material. The announcement's “ten years as executive director” appears in
tension with Aldersgate's 2018 appointment record; this is a source chronology
question, not a demonstrated second medium-only failure.

The authorized paired R4 repeat exposed a consequential Research difference:

| R4 repeat | High | Medium |
| --- | ---: | ---: |
| Result | Supported: Passport, 17,325–18,920 lb | Partial: wrong CT7 line, range unestablished |
| Turn wall / Research time | 28.187 / 15.842 s | 93.219 / 62.937 s |
| Research / semantic / external attempts | 3 / 4 / 2 | 11 / 12 / 15 |
| Research input / output / reasoning tokens | 16,459 / 1,525 / 901 | 142,753 / 5,520 / 2,506 |
| Approx. Research cost | $0.001928 | $0.015274 |

Medium followed early material about CT7 engines powering the Saab 340B test
aircraft, then pursued CT7 horsepower through repeated searches and Reads. It
reached the semantic-attempt bound without establishing the requested base
engine's takeoff-thrust range. Its 56 retained public acquisitions had no
Passport mention. High acquired GE's account that distinguishes the modified
Passport engine from the CT7 flight-test path, then GE Passport datasheets.
This was a material evidence-directed identity/stopping failure. Across all
seven draws, medium took 197.469 wall / 123.171 Research seconds and about
$0.023164 Research cost; high took 174.234 / 105.936 seconds and about
$0.012802. **Decision: KEEP HIGH.** Low effort was not tested.

## Stage B — Standard versus Fast mode

Research effort stayed Luna / high. FST1, FST2, and FST3 ran as sequential
Standard/Fast pairs. All nine Standard Research calls returned `default`;
all 14 Fast Research calls returned `fast`, with no observed downgrade. Every
Answer call requested and returned `default`.

| Case | Standard wall / Research | Fast wall / Research | Standard / Fast Research calls | Standard / Fast external attempts |
| --- | ---: | ---: | ---: | ---: |
| FST1 premise-only | 7.704 / 3.282 s | 8.063 / 2.906 s | 1 / 1 | 0 / 0 |
| FST2 Passport | 23.016 / 9.718 s | 49.656 / 35.267 s | 3 / 5 | 2 / 7 |
| FST3 St. Dorothy's | 38.359 / 23.938 s | 57.375 / 35.435 s | 5 / 8 | 6 / 11 |
| **Three-pair total** | **69.079 / 36.938 s** | **115.094 / 73.608 s** | **9 / 14** | **8 / 18** |

The three first Research calls collectively took 8.923 s Standard versus
7.843 s Fast, a 1.080 s Fast advantage; individual first calls varied in both
directions. Later trajectories varied: Fast used more semantic and acquisition
rounds on FST2/FST3, so total turn latency does not isolate service speed.
Results remained useful: both FST1 calculations matched; both FST2 answers
identified Passport and GE's 17,325–18,920 lb range; both FST3 answers
identified Spelman and qualifications from the official announcement. Fast
FST2 additionally noted an older, different GE datasheet range. There was no
demonstrated material Fast quality regression, but no consistent material
latency gain either.

Standard Research used 50,164 input (16,029 cached), 3,471 output (1,534
reasoning) tokens and cost about $0.005309. Fast used 120,007 input (22,961
cached; 1,939 cache-write), 10,314 output (6,355 reasoning) tokens and cost
about $0.030279 at Fast rates. These are realized trajectory costs, not a
same-token price comparison; route and cache differences contributed. **Decision:
STANDARD.**

## Stage C — immediately prior cited Evidence

Research stayed Luna / high / Standard and Answer stayed Sol / medium /
Standard. One ordinary BIPM seed and one ordinary parkrun seed were committed
through Reading Room. After connections closed, each seed database file was
copied byte-for-byte before the control or treatment follow-up. The BIPM seed
was reused separately for the direct BIPM and unrelated Euclid pairs. The
recorded seed/copy SHA-256 matches were:

- BIPM: `5129cd0416d08db53a6fc6d44ed7e23d2734eb35891c1f325052ba22bf75a736`.
- parkrun: `8c21b5af1a6f94e428645a15db353cd3ab3125bd225e5b330da1b3474ac4f19f`.

No SQLite rows were edited or inspected. The treatment supplied only exact
material cited by the immediately previous completed answer on the first
Research call; Research still chose its own current Answer Evidence.

| Follow-up | Control: first input / first Research | Treatment: first input / first Research | Control → treatment total Research; wall | Research calls / local Reads |
| --- | ---: | ---: | ---: | ---: |
| BIPM direct | 3,028 tokens / 3.765 s | 3,293 / 3.922 s | 6.968 → 3.922 s; 11.312 → 8.203 s | 2 / 1 → 1 / 0 |
| parkrun direct | 4,420 / 4.719 s | 10,096 / 4.797 s | 9.719 → 4.797 s; 23.265 → 14.391 s | 2 / 2 → 1 / 0 |
| Euclid unrelated | 3,038 / 2.391 s | 3,303 / 2.719 s | 5.345 → 5.969 s; 9.281 → 10.437 s | 2 / 0 → 2 / 0 |

The direct treatments removed the local-read semantic round trip and saved
3.046 and 4.922 Research seconds (3.109 and 8.874 wall seconds). The first
call carried 265 more tokens for BIPM and 5,676 more for parkrun; it cost only
0.157 and 0.078 more seconds respectively. The unrelated treatment added 265
first-call tokens and 1.156 wall seconds, but still searched ESA, used the same
two Research calls, and cited newly acquired ESA material. All six follow-ups
gave materially correct, qualified answers. The parkrun treatment preserved
the 5k arm's-reach rule, the junior-course distinction, and the start/finish
adult requirement with its exceptional-circumstances qualification.

Across three pairs, control used six Research calls, 22.032 Research seconds,
43.858 wall seconds, 32,617 Research input and 1,641 output tokens, at about
$0.003071 Research cost. Treatment used four calls, 14.688 Research seconds,
33.031 wall seconds, 24,185 input and 1,078 output tokens, at about $0.002233.
The total first-call packet grew by 6,206 tokens across pairs while whole-turn
input fell by 8,432. **Decision: PROMOTE PRIOR-CITED INITIAL EXPOSURE.** This
is bounded evidence over two useful follow-ups and one unrelated control, not
a guarantee for longer sessions or larger prior citations.

After promotion, one additional ordinary Reading Room follow-up reopened a
byte-for-byte copy of the BIPM seed with no experimental session or model option.
The seed and copy both hashed to
`5129cd0416d08db53a6fc6d44ed7e23d2734eb35891c1f325052ba22bf75a736`.
At `95cdbdd`, the default path completed in 7.343 wall seconds with one
3.609-second Luna/high Research call, 569 characters of cited E1 material in its
first Evidence packet, no local Read or external attempt, and a supported answer
citing E1. Research and Answer both returned `default` processing; Answer stayed
Sol/medium. This validates the final ordinary default wiring on the product path.

## Cost, live ledger, and artifact custody

Approximate Research dollars apply the current [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) for GPT-6 Luna short-context
Standard: $0.10 ordinary uncached input, $0.01 cached input, $0.125 cache
writes, and $0.50 output per million tokens. [Fast mode](https://developers.openai.com/api/docs/guides/fast-mode) costs twice those
rates. The formula uses output tokens once; reported reasoning tokens are a
subset of output tokens. Model usage is provider-reported, and prices may
change. This Research-only approximation excludes fixed Answer and external
provider costs.

| Stage | Submissions | Research calls | Answer calls | External attempts |
| --- | ---: | ---: | ---: | ---: |
| A initial high + medium | 12 | 30 | 12 | 24 |
| A paired R4 repeat | 2 | 14 | 2 | 17 |
| B three Standard/Fast pairs | 6 | 23 | 6 | 26 |
| C two seeds + three follow-up pairs | 8 | 15 | 8 | 8 |
| Final default-path BIPM follow-up | 1 | 1 | 1 | 0 |
| **Total** | **29 / 30 authorized** | **83** | **29** | **75** |

All 29 submissions completed. The dogfood logs show 44 Luna/high/Standard,
25 Luna/medium/Standard, and 14 Luna/high/Fast Research calls; 28
Sol/medium/Standard Answer calls in the staged comparisons and one more in the
final canary. External acquisition consisted of 53 Exa
Searches, six Serper lexical Searches, and 16 LinkUp Reads. Five additional
local Reads used no external attempt. No automatic retry occurred. The paired
R4 repeat consumed two contingency submissions and the final default-path canary
used one more; one authorized submission remained unused. The first sandboxed
canary broker invocation reported `environment_file_permission_denied` and
`target_launch_attempted=false`, so it consumed no submission. The same exact
target ran through the approved credential-broker execution identity.

The complete isolated evidence root is
`C:\tmp\scryraven-latency-consumption-01`. Arm folders
`stage-a-high`, `stage-a-medium`, `stage-a-r4-repeat`,
`stage-b-standard`, `stage-b-fast`, `stage-c-seed`, `stage-c-control`, and
`stage-c-preexposed` hold durable session databases, body-free `turns.jsonl`,
and whitelisted `trajectory.jsonl`. The campaign caller is available for audit
at the live-tested checkpoint `ea20fd4`; it is not a final-tree runtime path.
`final-default-canary` contains the final copied database, dogfood log, and
sanitized broker records; its external caller is `final_canary.py` at the artifact
root. Broker stdout/status files hold sanitized
public answers, citations, hashes, and invocation outcomes. Useful failures
and controls should be retained under the local evaluation corpus policy
before any destructive cleanup; no evidence was deleted in this phase.

## Final configuration and limits for review

The promoted ordinary configuration is **Research GPT-6 Luna / high /
Standard; immediately-prior cited Evidence on the initial follow-up Research
call; Answer GPT-6 Sol / medium / Standard**. The source-free disclosure is
generic because completed session turns do not persist a premise basis.
`CURRENT.md` must state only the final promoted behavior and bounded evidence
after final-code verification. This report does not grant merge authority.

No packet/catalog/working-understanding redesign, acquisition concurrency,
route-width increase, model router, Answer configuration change, source summary,
or generated memory was attempted. Provider timing and source acquisition vary;
these compact comparisons do not establish universal latency or reliability.
The final implementation revision is `95cdbdd`, followed by this report-only
revision. Its full offline suite passed 447 tests; Ruff and Git diff checks
passed. The branch is intended for one review PR and is **NOT MERGED**.
