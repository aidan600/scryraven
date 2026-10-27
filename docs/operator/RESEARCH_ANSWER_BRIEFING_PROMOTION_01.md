# Research–Answer Briefing Promotion 01

Historical promotion record: merged in [PR #679](https://github.com/aidan600/scryraven/pull/679)
at `33511b268d9b07ab10bc0725d488132fb5e3f324`. The original review disposition
was **A — approve for PR publication**, with required offline checks passed and
merge authority retained by the human. Candidate and publication references below
describe that original review, not a pending promotion. Current implementation is
in `CURRENT.md` and `docs/architecture/RESEARCH.md`.

## Outcome and exact scope

The human and product architect approved the simplified Research–Answer
relationship. This phase independently reviewed the implementation, verified it
offline and prepared one production PR. It commissioned no new experiment,
prompt tuning, live validation or architecture redesign.

| Identity | Value |
| --- | --- |
| Exact clean source | `codex/research-answer-convergence-01` at `980c7db06a23d0f6f0ed7a95cee6df020fe7f0a5` |
| Promotion branch | `codex/research-answer-briefing-promotion-01`, created directly from that source |
| Verified remote main / merge base | `7afc75df4f28e9c3bb12dacfe729d7678c45a6ac` |
| PR target | `main`; non-draft; human merge decision after independent review |
| Tested implementation | Exact source above; final runtime is unchanged by promotion |

The cumulative history contains operational repair `c21d427`, briefing runtime
`a30950b`, its report `c2cd186`, exposure diagnostics `aa28de7`, scalar-calculator
clarification `5796f94`, briefing-needs correction `a92a438`, and convergence
reports `1b0838a` / `980c7db`. No history was rewritten or experimental code imported.
Promotion adds documentation only. The published SHA and PR URL are recorded in
the final delivery receipt and GitHub PR, avoiding a self-referential commit ID.

## Independent code review

Three read-only reviews covered architecture, mechanical integrity and
operational/security scope against remote `main`. No consequential defect or
unauthorized boundary change was found. No runtime fix was requested.

- One `ResearchDecision` and `research_episode` replace the structured
  Understanding ledger, separate delegated assessment and duplicated handoff
  accounts. Initial and delegated Research use the same investigative contract.
- Research maintains one provisional, replaceable briefing. Null preserves an
  unchanged account. The convergence correction instructs Research to incorporate
  newly resolved findings, remove obsolete needs and retain unresolved ones.
- Initial Answer receives that actual briefing and selected originals. It may
  adopt adequate findings, challenge interpretation, inspect retained originals,
  calculate or request consequential further Research. Delegated results resume
  the same native Answer interaction with the latest briefing and originals.
- Briefing prose is fallible analysis, never Evidence, citation membership or a
  binding verdict. Exact exposed source/version/range custody and actual Answer
  delivery still govern citations. Mechanical validity does not prove entailment.
- Operation-specific Search/Read/Find shapes remove irrelevant fields. One compact
  acquisition history replaces overlapping worker receipts. Obsolete contracts,
  callers and tests are removed without dormant compatibility machinery.
- Existing sessions, historical support, follow-up semantics, Answer-local tools,
  bounded correction, shared deadlines/acquisition/physical-request limits and
  honest partial/failure behavior survive. Briefings remain turn-local and absent
  from durable session records and body-free logs. Opt-in source-bearing forensic
  exposure events record the actual supplied briefing.

No analyst, verifier, semantic checker, Answer bypass, model router, independent
decision-maker, persistent semantic lifecycle or alternate product path was added.
Removal is complete for the superseded Understanding/delegated-assessment machinery.

Rejected one-pass commits `48757c5` / `95e22ff`, mixed-provider batching
`7f50c37`, and parallel semantic-lane commits `ea00f94` / `5d8059e` are not
ancestors of this candidate. Review also found no corresponding runtime changes.
Existing approved same-provider Exa transport overlap predates this promotion.

## Inherited operational repair

The cumulative diff intentionally includes `c21d427`:

- Definite missing configuration disables only the affected acquisition provider
  for the current turn. Repeated suppressed requests do not spend another external
  attempt; limitations retain safe provider/failure codes. Other providers, local
  Read/Find, PDFs, retained material and premise-only answers remain available.
  Transient/access/rate-limit failures do not disable a provider; a new turn starts
  fresh. Entirely unavailable routes yield control without a model-only loop.
- The isolated forensic Reading Room launcher uses the existing credential
  doorman and explicit personal-plan backend, with no API fallback or startup
  inference. Its private child checks configuration presence, records safe
  booleans/profile/revision and verifies bind/readiness. The exact-run stop helper
  and PrepareOnly path remain operator infrastructure. No new credential system
  or product semantic authority is introduced.

Primary changed code is `scryraven/research.py`, with supporting acquisition,
model-packet/tool-description, safe diagnostics and forensic-launcher changes.
Session persistence, AnswerLibrary and citation resolver implementations are
unchanged. Related regression fixtures adapt to the surviving contracts.

## Offline verification

The complete source implementation passed **1028 tests, four environment skips**
in 24.58 seconds using the repository `.venv`, disabled automatic pytest plugins,
and an external `sitecustomize` guard denying external sockets and DNS while
allowing loopback fixture servers. The guard was explicitly checked before pytest.
No ScryRaven/model/acquisition provider call was made in this phase.

The first attempt hit Windows sandbox temporary-directory access/cleanup errors
(936 passed, 93 failed, three skipped, 114 teardown errors). Repeating with
TEMP/TMP and pytest storage under the authorized external root passed without a
code change. The failed-run log is preserved alongside the successful run.

The four existing environment skips are `test_forensic_launcher.py:255`,
`test_forensic_reading_room_01.py:156` and `:181`, and
`test_reading_room.py:557`, all for unavailable Windows links/junctions.

Ruff (`python -m ruff check .`) and compilation
(`python -m compileall -q core scryraven scripts tests`), Git whitespace checks
and all six configured pre-commit hooks passed: merge conflicts, end-of-file,
trailing whitespace, YAML, Ruff and detect-secrets. The final PR and delivery
receipt identify the published revision.

API- and plan-shaped injected fixtures exercise the ordinary implementation:

| Contract | Regression evidence |
| --- | --- |
| Initial briefing plus actual originals; acquired-evidence updates; unresolved needs; valid null continuity | `tests/test_research_briefing.py` |
| Delegation, revised briefing and same native Answer history; calculator and retained local tools | `tests/test_research_briefing.py`, `tests/test_research_first_resumable.py`, `tests/test_answer_calculator_runtime_01.py`, `tests/test_answer_library.py` |
| Actual-source citations, invalid references and bounded schema/citation correction; honest failure | `tests/test_research_first_resumable.py`, `tests/test_research_briefing.py`, `tests/test_answer_missing_citation_correction_01.py`, `tests/test_answer_correction_efficiency_01.py` |
| Durable reopen, genuine follow-ups and historical exact support | `tests/test_research_briefing.py`, `tests/test_persistent_sessions.py`, `tests/test_durable_support_reader.py`, `tests/test_prior_cited_preexposure.py` |
| Provider suppression, launcher custody and diagnostic isolation | `tests/test_provider_availability.py`, `tests/test_forensic_plan_launcher.py`, `tests/test_forensic_reading_room_01.py` |

The sole PR workflow, `.github/workflows/ci.yml`, is unchanged: dependency setup,
pre-commit and pytest only, without product submissions or provider credentials.
Its transports/authentication are synthetic fixtures; launcher tests use
PrepareOnly. Dependency and hook downloads are development tooling, not product
provider validation. The local network guard is external verification tooling,
not a new runtime restriction.

Logs and guard: `C:\tmp\scryraven-research-answer-briefing-promotion-01`.
Final promotion edits are documentation only; no material code change follows
the tested source implementation. Current documentation explicitly distinguishes
the approved branch design from deployment pending merge. Historical phase
authorization and counts remain historical, rather than being rewritten.

## Existing PRODUCT evidence and limits

The nine ordinary convergence cases remain at
`C:\tmp\scryraven-research-answer-convergence-01`, particularly
`batch-3/REVIEW_BUNDLE.md`, each batch checkpoint, the ledger and each run's exact
answer/originals/briefing/reopen receipts. They were not rerun or altered.
They used 37 physical requests, 29 external attempts and 475.986 product seconds.
Latest live runtime was `a92a43899341c8a0a46a9bece25d690c4c313db7`; Batch 3
observed it at documentation checkpoint `1b0838a`.

The cases show useful compact briefing adoption, targeted Klamath delegation,
developed Waymo comparison, honest sparse/community partials and genuine
retained-source follow-up. Their limitations remain:

- Klamath missed an unacquired October 2025 construction milestone and a smaller
  supplied-source geographic qualification. This phase does not tune completeness.
- Heidi used repeated sparse searches; Waymo had overlapping local reads and a
  long developed Answer. No new economy/latency tuning is included.
- Correction of a consequential mistaken briefing and stopping after failed
  community materialization are not newly demonstrated. General completeness,
  semantic correctness, long-session reliability and causal cost/latency gains
  remain unproved. Exact citations alone do not certify factual correctness.

The preserved `C:\tmp\scryraven-luna-answer-screen-01/REPORT.md` is a four-case
reconstructed-packet fixed-evidence screen at source `980c7db`, not ordinary
end-to-end PRODUCT evidence. Luna/high matched the compact lookup and retained
follow-up, was acceptable but materially weaker on Waymo and failed Klamath's
reporting-cutoff judgment. It does not justify replacing Sol/medium; shipped
assignments remain unchanged. No screen or convergence evidence was rerun,
deleted or relabeled as a holdout. Sanitized development cases remain ignored in
`local-evals/`; actual case corpora are not published in this PR.

## Publication boundary

After all checks pass, the brief authorizes one push and one non-draft PR into
`main`. It authorizes no merge, rebase, reset, squash, cherry-pick, force-push,
branch deletion or main modification. The final handoff supplies the exact
published commit and PR URL for independent ChatGPT review. The human retains the
merge decision. No successor campaign or automatic next phase is commissioned.
