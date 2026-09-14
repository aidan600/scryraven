# Investigator behavioral development validation

Outcome: **ARCHITECTURE HYPOTHESIS NOT YET SUPPORTED** (Phase 3 outcome C).
Recommendation: **abandon/rethink Investigator candidate**. Useful factual and
relational answers did not offset repeated failure to change an unproductive
research route. The campaign stopped when another repair appeared necessary after
two interventions. This does not establish that a new semantic actor is necessary
or that the architecture cannot work. No next phase was started.

## Revision and execution boundary

- Clean starting `main`: `25a5cf556043db0a814308b100842b5e7f67bceb`.
- Work branch: `codex/investigator-behavior-proof-01`.
- Wave A tested the starting revision; no repairs during that wave.
- Wave B tested intervention 1: `03adc89d7a3062d4442b1655ba6c22b43443d9da`.
- Rechecks tested final runtime: `08563d39e9217fb79cca861bb26fe63a12f21bdd`.
  Subsequent delivery changes are documentation only.

Explicit development invocations used the actual CandidateHarness /
InvestigatorEngine, OpenAIModel and existing Exa search/fetch transport through
the repository doorman. Provider/model bindings stayed unchanged. Every run kept
16 nonterminal cycles, 16 external acquisition attempts and 128,000 active Evidence
characters. The driver was external under
`C:\tmp\scryraven-investigator-behavior-01\`; no repository campaign runner was added.
Two-turn sequences used ephemeral ResearchSession instances with fresh Investigator
state per submission. Production Research -> Analyst -> Author was not run live.

## Frozen development manifest and consumption

Exactly 14 primary submissions were frozen before the first live call, at
`2026-09-13T23:34:01.191709+00:00`. Manifest SHA-256:
`6537cab21126c8a9f6ca22e95cb927e6ad9b2ab55fb999b69dbc0ea6b4092b3d`.
Selection used the brief and unrelated public topics, without historical or sibling
local-evals inspection. Wording was never revised after execution began.

| ID | Frozen question subject / class | Model attempts | Search / fetch | Result and principal observation |
| --- | --- | ---: | ---: | --- |
| A01 | St. Dorothy's Rest new ED qualifications; known identity failure | 18 | 15 / 0 | Partial at cycle limit; interim/current ambiguity remained, linked role document ignored. |
| A02 | Compare top three scorers from latest completed men's and women's FIFA World Cups; known comparison | 3 | 1 / 0 | Actual comparison, but searches assumed 2022/2023 without establishing latest-completed scope. |
| A03 | Latest Path of Exile 2 league reception; known reception | 6 | 4 / 0 | Partial; positive reception conclusion exceeded largely preview/activity evidence. |
| A04 | ESA Euclid launch date; authoritative fact | 3 | 1 / 0 | Supported 1 July 2023 from ESA. |
| A05 | RAS in British astronomy; new abbreviation | 3 | 1 / 0 | Royal Astronomical Society resolved from context; useful account of its work. |
| A06 | Why total solar eclipses do not occur every new moon; explanation | 3 | 1 / 0 | Supported explanation connecting inclination, nodes and totality conditions. |
| A07 | Under-11 participation and supervision at 5k/junior parkrun; dense rules | 3 | 1 / 0 | Main age/supervision distinctions preserved; an exceptional-circumstances qualification omitted. |
| B01 | Channel Tunnel length according to operator; authoritative fact | 3 | 1 / 0 | Correct 50.5 km; unnecessary undersea detail reconciled differing 37/38 km statements without attribution. |
| B02 | Hubble versus Webb observations and complementarity; new comparison | 3 | 1 / 0 | Useful relational explanation from NASA material. |
| B03 | Critics versus audiences on The Boy and the Heron; new reception | 3 | 1 / 0 | Useful rating/theme comparison; frequency language stronger than sampled comments establish. |
| B04 | Identification and persistence of Greenland's nine-day seismic signal; multi-level investigation | 3 | 1 / 0 | Supported causal synthesis; first acquisition already supplied the deeper mechanism. |
| B05 | British Museum calendar-2027 visitor total; partial/unanswerable | 18 | 14 / 1 | Honest partial answer after excessive repeated acquisition and one failed fetch. |
| B06 | Yellowstone hydrothermal feature types according to NPS; conversation initial | 3 | 1 / 0 | Supported classification; exact source retained for follow-up. |
| B07 | Which of those build terraces, and how; same-session follow-up | 1 | 0 / 0 | Aborted: Locate requested on highlights without a fetched full parent. |
| R01 | Exact B06 repeat, fresh session | 3 | 1 / 0 | Supported; retained source already included terrace formation. |
| R02 | Exact B07 repeat following R01 | 4 | 1 / 1 | Supported after failed fetch and new search; retained highlights were not simply reactivated. |
| R03 | Exact A01 repeat | 16 | 15 / 0 | Operator stopped repeated searches; no terminal analysis or Author answer. |

| Campaign segment | Submissions | Model attempts | Search | Fetch |
| --- | ---: | ---: | ---: | ---: |
| Wave A | 7 | 39 | 24 | 0 |
| Wave B | 7 | 34 | 19 | 1 |
| Targeted rechecks | 3 | 23 | 17 | 1 |
| Total | 17 | 96 | 60 | 2 |

There were 81 Investigator and 15 Author attempts, 15 completed answers, one failed
submission and one operator-stopped submission. The last R03 model attempt was in
flight at shutdown; its completion/usage is unknown and it is counted in full.
The trajectory advanced during process inspection and shutdown; all 15 searches
are counted. No per-run or aggregate ceiling was exceeded. Both fetch attempts
failed; all successful acquisitions were normalized public highlights.

Unused numerical allowance: zero primary submissions, three rechecks/submissions,
304 model calls and 138 external acquisitions. The two-intervention stop rule ended
the campaign despite that allowance. Independent source verification calls: **0**.
Production baseline runs: **0**.

## Interventions and observed limits

**Intervention 1: let received evidence govern target, next action and closure.**
A01 repeated 15 searches while an acquired current job listing linked a detailed
role document; A02 inserted remembered tournament years; A03 promoted topical and
activity evidence into a reception judgment. These supported one general principle:
interpretations are provisional, acquisitions must change what happens next, and
sufficiency depends on evidence matching the requested target and operation.

The prompt now establishes relative time/entity scope, follows concrete leads
through existing Discover/Read actions, changes unproductive routes, distinguishes
answer-bearing evidence from topical material and avoids invented adjacent gaps.
There was no mechanical change. A synthetic linked-current-specification test
checks prompt/date delivery, the existing acquisition route, exact support selection
and unchanged Author input. The relevant 168-test set passed. Scripted behavior
does not prove that a live actor follows the prompt.

Wave B supplied useful new factual/comparison/explanatory answers, but B05 again
exhausted 16 cycles and B07 failed mechanically. Different questions and variable
acquisitions prevent attributing Wave B successes to the intervention. The known
recency/reception cases were not individually rechecked at this revision.

**Intervention 2: make existing action prerequisites and feedback explicit.**
B07 requested lexical Locate on retained provider highlights; the full-parent guard
was correct but its prerequisite was absent from prompt guidance. B05 also repeated
requests after failure while input exposed the last result without its request.
The related hypothesis was that accurate action affordances and immediate request
identity would help the actor choose and interpret its existing actions.

The prompt now distinguishes highlight activation from full-parent Locate/ranges
and explains failed Read behavior. Input assembly includes only the preceding
action in `action_result.request_not_evidence`. It is non-evidentiary context, not a
new history, actor, action, persistence boundary or semantic guard. Tests cover
request identity after success/failure/local inspection, separation from Author and
Evidence, retained-highlight activation, unchanged Locate rejection and rollback.
The relevant 196-test set passed.

R02 avoided the previous abort and answered the follow-up, but fetched/searched
instead of using already available retained text. R03 still repeated 15 identity
searches without pursuing the acquired linked document or resolving the alternative
interpretation. Another repair appeared necessary; no third intervention or further
live submission was made. These rechecks support a narrow recovery observation,
not a general improvement claim.

## Behavioral assessment

Every primary/recheck has a local ten-dimension pass/concern/fail review, a separate
critical-failure field and diagnosis tied to its acquired material. These judgments
are qualitative development observations, not a numeric leaderboard.

| Dimension | Campaign finding |
| --- | --- |
| Question / intent fidelity | Contextual abbreviation and elliptical follow-up understood. A01 identity ambiguity and A02 unverified current scope remained material failures. |
| Trajectory | Straightforward authoritative queries worked. A01/B05/R03 repeated routes that did not resolve the need. |
| Recursion | Deeper synthesis occurred when initial sources supplied it. Following an exposed consequential lead was unreliable; B04 did not require a second acquisition. |
| Evidence quality | ESA/NASA/NPS/operator sources established narrow claims. A03's previews and engagement counts did not establish its reception verdict. |
| Authority / breadth | Narrow authority generally adequate. A03 mixed game-wide reviews, previews and league-specific reception; B03 sampled/duplicate comments cannot establish population frequency. |
| Attention | Retention and some shelving observed; redundant activation and follow-up reacquisition remained. Successful live full-parent inspection and efficient reuse were not demonstrated. |
| Synthesis | A02 compared goals/tie-breaks rather than only listing; B02 explained complementarity; A06/B04 supplied causal relationships. Correct operation alone did not repair wrong temporal scope. |
| Source fidelity | Many numbers/conditions survived. A07 lost the junior supervision exceptional-circumstances qualification; A03 overstated reception; B01 smoothed differing ancillary values. |
| Stopping / economy | Narrow questions often used one search and two Investigator decisions. A01/B05 reached the cycle limit; R03 repeated the same failure after both interventions. |
| Final usefulness | Several answers were directly useful. Wrong scope, unsupported reception, one abort and repeated acquisition prevent treating the candidate as broadly coherent. |

Representative failures were adjudicated against acquired text only. In A01/R03,
the diocesan listing linked an ED search PDF while an official staff page explicitly
identified an interim officeholder. Repeatedly searching for a permanent appointee
did not explore the job-qualifications interpretation or the linked specification.
No outside claim about the actual appointee was used. A02's acquired older scoring
records supported its numbers, but did not establish that those editions were the
latest completed. No replacement leaderboard was researched.

B05 correctly distinguished a future calendar-year total from a forecast and a
financial-year reporting period; the failure was repeated acquisition despite that
limitation. A03's positive verdict relied substantially on features, launch activity
and pre-release discussion, which establish different things from player reception.

**Layer separation:** Investigator owns the above target/trajectory/synthesis and
economy failures. B07 was an action-prerequisite guidance defect, with correct
mechanical rejection. Author separately dropped A03's explicit promotional/sample
qualification and added source-supported wavelength ranges in B02 that were absent
from terminal findings. Author was not edited. The two failed Exa fetches are
provider/transport observations; their underlying cause was not independently
verified, and they do not explain loops dominated by successful searches.

## Scope, verification and safety

No new actor, action kind, scheduler, retrieval/ranking subsystem, database,
lifecycle, provider or model strategy was added. Author and production prompts,
Research/Analyst, Reading Room, session schema, Evidence meaning and historical
citations are unchanged. Attention policy and live limits stayed fixed. There is
no named-entity branching or source-count sufficiency heuristic. No explicit removal
was requested. No architecture expansion is proposed by this change.

Final runtime verification: `tests/test_investigator.py` **60 passed**; full offline
suite **390 passed**, using `-p no:cacheprovider` and the requested external full-suite
basetemp. Final publication lint/hook/diff checks are recorded in the PR. Earlier
Windows temporary-directory permissions caused one test setup error; the focused
suite passed with an external basetemp, without a product change.

Sanitized packets, manifest, per-run reviews, hashes, intervention records and
aggregate ledger remain only in the ignored
`C:\Users\aidan\ScryRaven\local-evals\investigator-behavior-01\` campaign directory.
They preserve exact normalized public Evidence needed for adjudication and compact
schema-validated state/actions, not hidden reasoning. The controlling agent did not
read `.env` or inspect keys. No credentials were exposed; no raw provider payloads,
raw responses, prompts, headers, cache keys, unbounded traces or session databases
were stored in that corpus or committed. Detailed packets are not published.

All used questions are permanently **DEVELOPMENT**, including the initially unseen
Wave B questions. No held-out proof, production superiority or general semantic
reliability is claimed. A02 recency, A03 reception, A07 exception loss and B05 economy
were not individually retested on final runtime. `CURRENT.md` records this frontier;
the architecture document only clarifies the preceding-request feedback now exposed
by the existing loop. `PRODUCT.md` is unchanged.
