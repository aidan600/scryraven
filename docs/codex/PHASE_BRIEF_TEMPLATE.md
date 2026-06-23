# Codex Phase Brief Template

Status: Recommended repo-tracked template
Suggested repo path: `docs/codex/PHASE_BRIEF_TEMPLATE.md`

Copy this for future phases and fill in only phase-specific details.
Keep prompts compact. Standing workflow, boundary, safety, and publication rules
belong in repo docs such as `AGENTS.md`, `CODEX_GUIDANCE_MAP.md`, and
`ARCHITECTURE_GROOVE_PLAYBOOK.md`; phase prompts should not restate the whole
operating manual. Include only the phase-specific goal, read files, scope,
tests, validation, stop conditions, and final-bundle requirements.

```text
<PHASE NAME>
Architecture Groove / Prove Mode, Path B approved.

Read:
docs/codex/CODEX_GUIDANCE_MAP.md
docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md

Also read when relevant:
- docs/codex/EXECUTION_PLAN_TEMPLATE.md for bundled multi-step phases
- docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md for AG-89+ authority-collapse phases
- docs/codex/PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md for proof-class or actual-app-delta questions
- docs/codex/TEST_CLASSIFICATION_LIBRARY.md and docs/codex/VALIDATION_BUCKETS.md for test additions, promotions, demotions, or retirements
- docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md only for legacy Controller-handoff maintenance when explicitly selected

Repository:
C:\Users\aidan\ScryRaven

Naming note:
- ScryRaven is the public project name for this repository.
- Historical docs may still mention earlier working names such as ProPlex,
  FauxPlex, and FauxPlexity.
- The `proplex` package, `python -m proplex`, and `PROPLEX_*` environment names
  remain compatibility surfaces unless a phase explicitly removes them.

Start state:
- Start from updated main.
- Confirm main includes the previous merged phase.

Suggested branch:
codex/<phase-branch-name>

Phase-end publication:
- Use docs/codex/CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md.
- Use workspace sandbox for implementation, tests, inspection, and file edits.
- For Git metadata or publication, request approval for the exact command only.
- Do not request Full Access or repair auth/ACL/sandbox during the phase.
- After implementation, tests, and self-review, exact-approved commands may push the completed phase branch and create a pull request into main.
- Do not merge, squash, rebase, force-push, delete remote branches, delete non-temporary branches, reset, clean destructively, or alter main. Exact-approved deletion of a local temporary cleanup branch is allowed only under docs/codex/CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md.

Primary outcome:
<One sentence: what this phase must accomplish.>

Required proof, product, and validation posture:
Proof class:
Product path affected:
Runtime consumer:
Actual app delta:
Validation bucket:
Test classification / promotion posture:
New tests:
Fast_pr promotion rationale, if any:
Non-proofs:
Bridge or exit condition:

New tests must be classified before being added to permanent bucket manifests.

Rule 0 failure_analysis:
- General failure class:
  ...
- Blast radius:
  ...
- Rules that apply:
  ...
- Valid cases this could accidentally block/degrade:
  ...
- Telemetry/process signals:
  ...
- Simplest positive test:
  ...
- Simplest negative-control test:
  ...

In scope:
- ...

Autonomy / decision-point policy:
- Proceed autonomously for relevant file inspection, scoped implementation, in-scope tests, in-scope test fixes, docs cross-link fixes caused by the phase, formatting/pre-commit fixes, final-bundle preparation, and PR creation when explicitly authorized.
- Stop for product choices, unresolved architecture forks, unlicensed or closed-surface changes, live validation, secrets/private data, destructive git, merge/rebase/force-push, broad scope expansion, or unresolved failing tests that imply a design decision.

Out of scope:
- live calls unless separately approved
- provider routing changes unless explicitly scoped
- prompt rewrites unless explicitly scoped
- source ranking/filtering changes unless explicitly scoped
- persistence schema changes unless explicitly scoped
- safety-sensitive surface redesign unless explicitly scoped
- social provider integration unless explicitly scoped
- destructive git
- merge

Live validation, if approved:
- Live validation is disabled unless this section is explicitly filled in.
- Max live ScryRaven/proplex provider/model/search calls:
  ...
- Exact commands/harness:
  ...
- Decision the live run will make:
  ...
- Committed validation doc path, if any:
  docs/validation/...
- Local output-quality review packet path:
  output/ag##_output_quality_review_packet.md
- Do not call this a truth packet or truth review packet.
- Confirm packet ignored/untracked:
  git check-ignore -v output/ag##_output_quality_review_packet.md
  git ls-files output
- Do not include secrets, raw provider payloads, raw prompts, DB rows, caches, full traces, private logs, or unrelated generated outputs.
- If independent source-quality review is approved, use the "Independent qualitative source check" section below.

Independent qualitative source check, if explicitly approved:
- Purpose:
  Add a bounded ScryRaven-independent review layer for live validation. The goal is to compare ScryRaven output against the obvious public source landscape, not to silently change runtime behavior.
- When to use:
  Use for source-quality, official/current/canonical, numeric/status/date, legal/current, citation-fit, or source-survival validation where deterministic tests alone cannot tell whether ScryRaven found and used the right sources.
- Approval fields:
  - Enabled:
    yes | no
  - Max independent external source checks per validation query:
    ...
  - Max independent external search queries total:
    ...
  - Approved external-check tool or method:
    available non-secret web/search/browser tool | other explicit method | unavailable
  - Exact validation query or queries to compare against:
    ...
- Allowed review activity:
  - Run only the approved number of independent external source checks.
  - Use only available non-secret public web/search/browser tooling.
  - Search for the obvious best available official, primary, canonical, current, or otherwise authoritative public sources for the approved validation query.
  - Compare those external findings with ScryRaven's final answer, cited URLs, visible source sections/snippets, and sanitized telemetry.
  - Record public URLs/titles/domains when useful for review.
- Required qualitative judgments:
  - Did ScryRaven acquire the obvious best source or source class?
  - If acquired, did the source survive into the visible evidence/citation surface?
  - If cited, was it the right source for the specific claim?
  - Were exact numeric values, dates, thresholds, statuses, eligibility rules, or canonical technical details extracted/restated accurately?
  - Did ScryRaven rely on reputable secondary/news sources where an official/current/canonical source was required?
  - Did ScryRaven ignore useful reputable secondary/news context where no official source was required?
  - Is the failure layer most likely acquisition, preservation, source classification, citation selection, extraction/restatement, synthesis/answer posture, or unclear?
- Required packet fields:
  - validation query;
  - ScryRaven final answer identifier/report path;
  - ScryRaven final cited URLs;
  - independent external search query used;
  - best obvious external source candidates found;
  - source type for each candidate, such as official, primary, canonical, reputable secondary, news/context, or unclear;
  - whether each candidate was acquired by ScryRaven;
  - whether each acquired candidate survived into visible evidence/citations;
  - numeric/status/date/canonical-claim comparison notes;
  - qualitative source-fit judgment;
  - likely failure layer;
  - confidence level and uncertainty notes;
  - if unavailable, explicit reason the independent check could not be performed.
- Source-quality evaluation form:
  Use this form for each approved validation query and for each before/after run being compared.

  Query:
  Mode:
  Before or after:
  Run/report identifier:

  1. Deterministic / telemetry review
  - Required source class:
    official | primary | canonical | current | reputable secondary | news/context | unclear
  - Source class required by the user question?
    yes | no | partial | unclear
  - ScryRaven acquired required source class?
    yes | no | partial | unclear
  - Required source survived into visible evidence/citations?
    yes | no | partial | unclear
  - Numeric/status/date/canonical value present?
    yes | no | not applicable
  - Numeric/status/date/canonical value accurately restated?
    yes | no | partial | unclear | not applicable
  - Existing diagnostic classifier result:
    ...
  - Relevant sanitized telemetry fields:
    ...

  2. Independent qualitative source check
  - External search query used:
    ...
  - Best obvious external source candidates:
    - URL/title/domain/source type:
      ...
  - Did ScryRaven find the best obvious source?
    yes | no | partial | unclear
  - Did ScryRaven cite the best obvious source?
    yes | no | partial | unclear
  - Did ScryRaven use the source for the right claim?
    yes | no | partial | unclear
  - Did ScryRaven over-rely on secondary/news when official/current/canonical was required?
    yes | no | unclear | not applicable
  - Did ScryRaven wrongly undervalue useful reputable secondary/news context?
    yes | no | unclear | not applicable

  3. Final-answer quality
  - Answer correctness:
    correct | mostly correct | mixed | incorrect | unclear
  - Source-grounding adequacy:
    strong | acceptable | weak | failed | unclear
  - Citation/source-fit:
    strong | acceptable | weak | failed | unclear
  - User-trust risk:
    low | medium | high
  - Answer posture:
    confident appropriately | too confident | too hedged | caveated appropriately | unclear

  4. Failure localization
  - Most likely failure layer:
    acquisition | preservation | source classification | citation selection | extraction/restatement | synthesis/posture | telemetry gap | unclear
  - Evidence for that localization:
    ...
  - Would repair require a safety-sensitive or closed-surface change?
    yes | no | unclear
  - If yes, which surface:
    provider routing | provider depth | query generation | prompt behavior | source ranking | Economist | Analyst/Author handoff | final answer behavior | other
  - Recommended next action:
    no action | more instrumentation | scoped repair | stop for design decision
- Review-only boundary:
  This authorizes source-quality comparison only. It does not authorize provider routing changes, provider selection changes, provider depth/search-depth changes, query-generation changes, prompt changes, source ranking changes, source filtering changes, Economist behavior changes, Analyst/Author/Scrutineer handoff changes, or final-answer behavior changes.
- No repair by implication:
  If the independent check reveals a likely fix outside the scoped phase surface, stop and return a STOP packet. Do not patch closed or unlicensed surfaces merely because the external check found a better source.
- If no external search tool is available:
  Mark the independent qualitative source check as unavailable. Do not invent external findings, do not infer search results from memory, and do not treat the missing qualitative layer as a deterministic pass.

Bounded live before/after loop, if explicitly approved:
- Purpose:
  Allow one tightly scoped live before/after cycle. The phase brief must choose one mode:
  - Diagnostic validation mode: success means the new diagnostics or instrumentation make the failure stage clearer. The post-instrumentation answer may remain wrong or unchanged.
  - Repair mode: success means one scoped fix tied to the diagnosed failure layer improves the output.
- Mode for this phase:
  diagnostic_validation | repair
- Exact approved query or queries:
  ...
- Budget:
  - up to 2 exact user queries;
  - each query may be run once before the instrumentation/fix and once after it;
  - total maximum: 4 live ScryRaven/proplex runs;
  - independent qualitative source checks, if approved, must stay within their separate explicit cap;
  - no exploratory extra runs without explicit user approval.
- Required workflow:
  1. Run baseline live output for the approved query or queries.
  2. Create a local untracked output-quality packet under `output/`.
  3. If approved, perform the independent qualitative source check for the same query or queries and record sanitized findings in the local packet.
  4. Classify the failure using deterministic tests, existing diagnostics, sanitized telemetry, and any approved independent source-check findings.
  5. Implement one scoped instrumentation change or fix tied to the diagnosed failure layer and approved mode.
  6. Rerun the same query or queries once.
  7. If approved and still within cap, repeat the independent qualitative source check against the post-change output.
  8. Compare before/after in the final bundle.
  9. Stop.
- Diagnostic validation mode success criterion:
  The before/after comparison should show whether the new sanitized fields, trace projection, review packet, or source-check comparison makes the failure easier to localize. Do not treat unchanged answer quality as phase failure if observability improved.
- Repair mode success criterion:
  The before/after comparison should show whether the scoped fix improved source acquisition, source survival, citation/source-fit, extraction accuracy, or answer posture without violating closed or unlicensed surfaces.
- The local output packet must not be committed.
- Do not inspect or expose:
  - secrets;
  - `.env`;
  - raw provider payloads;
  - raw prompts;
  - DB rows;
  - caches;
  - private logs;
  - full raw traces.
- Do not change provider routing, provider selection, search depth, prompt behavior, Economist behavior, Author behavior, source ranking, or final-answer behavior unless the phase explicitly scopes that exact surface.
- If the instrumentation or fix requires a safety-sensitive or closed-surface change not already scoped, stop and return a STOP packet.

Required validation cases:
1. ...
2. ...
3. ...

Testing expectations:
- Name the required validation tier:
  `docs_only` | `fast_pr` | `phase_focus` | `author_lane` | `full`
- Choose the smallest valid bucket and report the exact command.
- For ordinary PRs, prefer `fast_pr`; do not use `author_lane` or `full` unless
  this phase explicitly licenses it.
- Do not add every new test to `fast_pr`.
- Do not repeatedly rerun monolithic timeouts; split the command or report the
  timeout.
- ruff or touched-file lint/format checks
- diff check
- focused new tests
- relevant existing tests

Final bundle:
Use the final bundle format from docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md.

If live validation used an independent qualitative source check, include:
- whether it was approved and enabled;
- external-check cap and actual checks used;
- whether the external-check tool was available;
- compact findings by validation query;
- best obvious external source candidates found;
- whether ScryRaven acquired/cited/preserved those candidates;
- numeric/status/date/canonical extraction comparison;
- likely failure layer;
- whether any safety-sensitive or closed-surface change would be needed for repair;
- confirmation that independent findings were review-only and did not drive unscoped runtime changes.

Return one final phase bundle only after implementation, tests, in-scope fixes, self-review, and optional phase-end PR creation.
```
