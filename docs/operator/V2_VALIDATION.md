# V2 implementation and development validation

## Outcome: not met

The branch implements and exercises a real V2 candidate through the ordinary
CLI/session application, with two semantic contracts, Exa acquisition, exact
citations, retained actual Evidence and durable follow-ups. It did **not**
establish the intended general research capability. Interpretation, scope,
qualification preservation, source sufficiency and nonprogress failures remained
after the coherent source-first repair. Live work stopped at ten top-level
submissions, before the numerical reserve was exhausted. Seven of the eight
frozen campaign classes were exercised; F08 was not run.

The baseline's ordinary Research -> Analyst -> Author path and Reading Room
default remain unchanged. V2 is available through the explicit `--v2` candidate
entrypoint; this work does not establish a production replacement decision.

## Starting point and tested revisions

The ordinary checkout began at the approved baseline
`533f45df9271978e0591fb35aa8da2b1917255b2`, on work branch
`codex/v2-adaptive-research-01`. No stopped experimental branch or old temporary
harness supplied the implementation scaffold. Mechanical Evidence, transport,
citation, presentation and session components were reused deliberately.

| Live submissions | Tested checkpoint | Change represented |
| --- | --- | --- |
| 001–002 | `92bc8c325300ea1ea22a11200b23c208dba0bdbe` | Initial coherent V2 candidate. |
| 003–004 | `858cfb601aea2f7f86fd91c3a676ec8590ff977a` | Exact-material reads local; explicit full-source acquisition. |
| 005–007 | `779e9e4cded84f28ac92942d0a7600821709cf66` | Specific exposure-contract correction feedback. |
| 008–010 | `4ce05905a03e13b7dffe8f4df30a4f57519c1ead` | Independent literal source reading in the Answer contract; no generated Research cautions; exact local view preservation and merged overlapping Find regions. |

The JSONL runner records byte hashes of relevant source files alongside each
revision. Runs 008, 009 and 010 all record the same `scryraven/v2.py` SHA-256,
`5f878ffe694c7f3de5695fe1f9af488f7350bdd4d31dfed10c4aae9ae20bafe6`, which matches
the checkpoint blob. Windows line-ending differences in several existing files
were checked against their recorded current bytes and checkpoint text; they do
not represent different implementations.

Final observer-isolation, compact-trace and durable citation-validation repairs
were made **after** run 010. Observer events are deep-copied and observer exceptions
cannot interrupt research. The small `answer_decision` trace keeps only
source-reading references; exact literal passages remain in the optional
observer's `answer_reading` event. Neutral partial turns now require citations
when saved, matching the existing live result boundary. These repairs change no
semantic prompt, model or provider. They have offline coverage and no additional live
submission. Documentation and these mechanical repairs must not be described as
live-tested at an invented later revision.

## Frozen questions and execution boundary

The exact questions and rubrics are in [V2_CAMPAIGN.md](V2_CAMPAIGN.md), frozen
before campaign submissions. Manifest SHA-256:
`bdcc3c1c7b09b00c8b7dadf45573f5d0d7636b31f7272b792c1ee2d3d27f7e0c`.
Questions remained fixed; routes, queries and sources were not prescribed.
Runtime inputs contained no expected identity, decisive URL, evaluation rubric,
or scripted decision. These are development observations, not held-out evaluation.

All submissions used GPT-5.6 Luna / medium and the existing Exa transport through
the credential broker. The standard envelope remained 12 semantic attempts,
16 external attempts and 120 seconds. No model/provider comparison or escalation
was performed. A submission means one real question or follow-up, including
unsuccessful development results; model attempts are counted separately.

The initial sandbox broker invocation for 001 returned
`environment_file_permission_denied` with `target_launch_attempted=false` and
`target_launch_succeeded=false`. It consumed zero product submissions and zero
provider calls. The same authorized broker invocation then ran successfully;
the controlling agent did not read the environment file, change its permissions,
or copy credentials. The prelaunch status remains preserved separately.

The runner invoked ordinary `ResearchSession.ask` with the V2 engine. Run 003
used the ordinary `python -m scryraven --v2` CLI and created a durable session;
004 resumed that session in a fresh process. Runs 001–002 also used a persisted
seed/follow-up sequence. Observers recorded normalized public data without
steering routes, selecting Evidence, changing prompts, or reading provider
payloads. Independent external source-verification calls: zero.

## Submission ledger

`S/F` means Exa Search / full-source fetch attempts. A mechanically rejected
unknown URL is not an external attempt. Local Read/Find does not consume external
allowance. Posture below is the product's returned posture, not the campaign
review verdict.

| Run | Case | Posture | Semantic attempts | S/F | Seconds | Review finding |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 001 | F01: BIPM prefixes | supported | 3 | 1/0 | 11.313 | Useful authoritative fact with exact citations. |
| 002 | F02: retained comparison | supported | 3 | 0/1 | 14.531 | Correct answer; unnecessarily fetched material already retained as an exact highlight. |
| 003 | F01: ordinary CLI seed | supported | 3 | 1/0 | 7.844 | Useful answer through the actual CLI and durable-session path. |
| 004 | F02: resumed comparison | supported | 7 | 0/0 | 21.766 | Actual retained reuse; four rejected decisions before a valid local reading route. |
| 005 | F03: rule and exception | supported | 3 | 2/0 | 18.703 | Material scope broadening and omitted qualification despite acquired/exposed support. |
| 006 | F04: future visitor total | unable | 2 | 0/0 | 6.812 | Recognized the future actual-result boundary and stopped promptly. |
| 007 | F05: HTTP explanation | supported | 11 | 4/2 | 90.172 | Useful technical answer with minor qualifier loss and poor economy; real full-parent/local-view use. |
| 008 | F03: repaired rerun | supported | 4 | 2/0 | 24.922 | Material scope/qualification problem remained; source-reading reference correction did not establish semantic fidelity. |
| 009 | F06: update reception | partial | 3 | 3/0 | 28.734 | Early selected coverage became a broad positive player-reception conclusion; consequential research remained obtainable. |
| 010 | F07: identity then qualifications | partial | 11 | 15/1 | 74.265 | Exposed departure chronology was lost; repeated candidate-centered acquisition ended without applicable identity. |
| — | F08: revised multi-component structure | not run | — | — | — | No demonstrated result. |

Total: **10 top-level submissions**, 50 semantic attempts and 32 external
attempts: 28 searches and four full-source fetches. The sum of recorded run
durations is 299.062 seconds. CLI run 003 duration is inferred from its final
120-second budget remainder; the others use the runner's elapsed measurement.
This is a sum of submission runtimes, not total engineering wall time.

Safe returned usage counters were captured for nine runner submissions, covering
47 semantic attempts. The CLI's three attempts have no usage packet and are not
treated as zero tokens:

| Counter | Nine-submission recorded sum |
| --- | ---: |
| Input tokens | 398,241 |
| Cached input tokens | 46,321 |
| Cache-write tokens | 4,228 |
| Ordinary uncached input tokens, by subtraction | 347,692 |
| Output tokens | 24,589 |
| Reasoning tokens | 5,289 |

Cache read/write counters are input subclasses; reasoning tokens are included in
output. These are transport usage observations, not a dollar-cost estimate or
quality score. No price comparison or runtime cost-policy system was introduced.

## First consequential losses and repairs

**Retained reuse and contract feedback.** Run 002 asked to read exact retained
material E2 with `auto`, but the executor fetched fuller text E7 despite the
retained highlight containing the required factors. The action contract was
corrected: exact E IDs reread locally, while explicit `full` obtains the full
parent when needed. Run 004 then completed with zero external acquisition and
two local reads. Its first four Research outputs were nevertheless rejected with
the combined `unexposed_reference_or_action_shape` code; the fifth Research call
selected the local readings, text reached the sixth call, and the seventh call
answered. Exact rejected fields were not captured in that run and cannot be
reconstructed. Later feedback identifies offending fields and records only the
schema-valid public decision, without raw model output.

**Scope and qualification.** In 005, actual E7 distinguished children walking,
jogging or running at 5k events from children volunteering under a close-proximity
rule. It also qualified junior accompaniment with exceptional circumstances.
Research broadened the running rule into a universal participation restriction.
Research recognized the junior qualification, but the final answer omitted it.
The exact controlling source was supplied to both semantic owners; acquisition
or missing exposure does not explain this failure. A generated final caution
asserting no 5k exception could also carry an upstream verdict into finalization.

**One coherent repair.** The final boundary no longer carries generated Research
findings or factual cautions. Controlling material travels as exact Evidence.
Within the same Answer call, the output now selects literal source passages before
writing the answer. Mechanical checks accept only supplied material references
and matching passages, tolerating whitespace only; corrections consume the same
allowance. This changes the two existing contracts without adding a verifier,
claim database, new semantic owner, or post-answer polisher. Coupled mechanical
repairs preserve an addressed exact view even when focus is supplied and merge
overlapping Find hits from the same immutable parent.

Run 008 repeated F03 after this repair. One answer reading referenced material
outside the selected packet and was corrected under the same contract. The completed answer still
broadened the 5k rule and did not preserve the material supervision qualification.
Literal source membership was demonstrated; faithful application was not.

**Technical explanation and local inspection.** Run 007 acquired full RFC 9110
and RFC 9111 parents, performed three local Finds and five successful local Reads,
and exposed exact subsequent views. This is actual product evidence for repeated
full-parent inspection, not just a fixture. Early retrieval returned a homepage,
then no results; two invented/unobserved URL requests were rejected. Large
overlapping packets made the route expensive. The final explanation was useful,
but generalized response `no-cache` without preserving its unqualified form's
scope and added an incidental `no-store` contrast without its supplied
`must-understand` exception. This case was not rerun after the coherent repair.

**Reception and premature stopping.** Run 009 correctly established the release
window and acknowledged incomplete coverage. It nevertheless interpreted selected
early reporting, reviews and promotional summaries as predominantly positive
player reception. Direct player-feedback highlights E3 were acquired and exposed
to Research **and** supplied in the answer packet; their full dated context was
not fetched. At Answer dispatch, nine semantic attempts, 13 external attempts
and about 105 seconds remained, despite Research naming unresolved player-context and
first-month coverage needs. The partial final answer stated important sample
limitations but still generalized positive reception and improved sentiment.
The loss is interpretation/sufficiency and stopping, not a lack of any player
material or exhausted budget. No representative sentiment claim was independently
verified by the development reviewer.

**Identity and failure to revise.** In 010, actual diocesan minutes E15 explicitly
reported that the earlier director had left, with interim arrangements and a
later search contemplated. This material was exposed at Research attempt three.
The next understanding omitted it, retained other sources, and continued toward
an appointment search. Later decisions repeatedly investigated Ashley as a
possible new permanent appointee despite the departure text, an interim listing
and older appointment dates. E15 never entered the final packet. The partial
answer centered the former director's biography while acknowledging current
identity remained unresolved. No correct replacement identity or decisive hidden
URL was given to the runtime or supplied as evaluation gold.

This run consumed 16 external attempts, but the first loss preceded exhaustion:
an exposed controlling premise did not revise the interpretation and attention.
Increasing the ceiling would not explain or repair that observed loss. Cautious
final wording does not establish successful recursive identity research.

## Why execution stopped

The numerical ceiling leaves 40 submissions unused. It is a ceiling, not a quota.
The repaired wave still showed the same fundamental interpretation, scope and
nonprogress family. A final coherent refinement was not spent: the evidence did
not identify a reasoned general repair beyond repeating the excluded prompt,
salience, schema or preserved-state interventions. No additional actor, router,
premium model, provider replacement, source-count gate or speculative subsystem
was introduced to continue the campaign.

The design did not establish the intended capability within this development
envelope. The required handoff is a human architecture review of the concrete
failures and whether to retain, revise or retire this candidate. This record does
not authorize another phase, further live submissions, or production promotion.

## Verification, exact evidence and delivery limits

The final full offline suite passed **471 tests** in 8.14 seconds with
`python -m pytest -q -p no:cacheprovider --basetemp C:\tmp\scryraven-v2-tests-final-02`.
This run includes all three post-live mechanical repairs described above.
Scoped Ruff checks passed for `scryraven`, the campaign runner and V2 tests.
`git diff --check` passed; Windows line-ending notices were warnings only.
The checks cover acquisition, exact views, repeated local inspection, exposure,
citation custody, malformed contracts, budget/deadline behavior, neutral durable
turns, historical provenance, rollback, CLI integration and observer isolation.
They do not establish semantic competence.

Before this work, the ordinary engine had three semantic owners and Analyst-shaped
completed state. The candidate now has Research and source-first Answer, a
mechanical Search/Read/Find executor, neutral `CompletedAnswer`, exact citation
resolution and real session/CLI integration. Source-first durable turns use
`analysis=None`; no fake Analysis is manufactured. The Reading Room keeps its
existing default engine. Prior experimental code remains harmless archaeology;
no explicit repository-wide removal was requested or claimed. Runtime defaults,
model/provider policy and main were not promoted or replaced by this branch.

Exact broker-sanitized run packets, lifecycle statuses, source hashes and the
computed ledger remain under
`C:\tmp\scryraven-v2-campaign-20260917\`. Only normalized public acquisitions,
exact exposures, structured public decisions, answers and safe counters were
inspected. No `.env`, credentials, raw provider payloads, hidden reasoning or
unrelated private logs were read. Session databases are not evaluation artifacts.

Useful failures and diagnostics were preserved as unique DEVELOPMENT candidates
in ignored `local-evals/candidates/`, with exact artifacts and hashes. Captures
include unnecessary retained refetch, repeated contract rejection, scope and
qualification loss, technical local-reading qualification loss, reception
overgeneralization and lost departure chronology. Corpus index entries were not
modified, and preexisting corpus cases were not inspected. Follow-up captures
without separately captured prior conversation are marked not independently
runnable rather than reconstructing missing inputs. Candidate classifications
are development review, not silently promoted adjudicated gold.

All JSONL exposure receipts match the separately captured exact material hashes.
This proves what was supplied, not what was understood. Source bodies returned as
highlights can omit context. Citation validity proves reference custody, not
entailment. The complete frozen campaign was not run on the final checkpoint;
F08, broad reliability, and V2 Reading Room acceptance remain unproved.

`CURRENT.md` is updated in the same branch with the implemented candidate,
observed frontier and stop decision. The work remains on the local work-item
branch for review; no push, PR, merge, main update or aftercare operation is
authorized by this validation record.
