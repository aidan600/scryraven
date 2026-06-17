\# Cursor Composer Workflow for ScryRaven



Status: Project workflow guidance for using Cursor as an alternate local implementation agent.



\## Purpose



Cursor may be used as a local implementation worker for ScryRaven, especially with Composer 2.5, when the phase is small enough to review through a normal GitHub pull request.



This document does not replace AGENTS.md, docs/codex/CODEX\_GUIDANCE\_MAP.md, or docs/codex/ARCHITECTURE\_GROOVE\_PLAYBOOK.md. It adds Cursor-specific workflow and command hygiene expectations.



\## Default model posture



Use Composer 2.5 as the normal Cursor worker for:



\- docs-only phases;

\- tests and static guards;

\- offline helper modules;

\- diagnostic packet helpers;

\- small refactors with no production behavior change;

\- read-only audits when cost matters.



Use stronger models only for:



\- short architecture triage;

\- hard bug diagnosis;

\- PR self-review;

\- high-custody design review;

\- explicit user-approved escalation.



Do not use expensive models as the default long-running implementation worker unless the user explicitly approves the cost.



\## Good Cursor task candidates



Good candidates:



\- read-only continuity audits;

\- docs refreshes;

\- fixture/test additions;

\- static guard tightening;

\- narrow offline adapters;

\- deterministic helper functions;

\- draft PR preparation;

\- small follow-up fixes requested by review.



Poor default candidates:



\- provider routing or provider selection changes;

\- prompt, Author, citation, or final-answer behavior;

\- EvidenceLedger, SufficiencyJudgment, FinalAnswerPacket, or RunAuthority activation unless explicitly scoped;

\- SearchWorkPlan or QueryPlan activation;

\- broad core/pipeline\_orchestrator.py work;

\- live validation or live provider/search/model/fetch/read calls;

\- package, CLI, environment, database, or public API rename work.



\## Standard Cursor workflow



For implementation phases:



1\. Start from updated main.

2\. Create a phase branch.

3\. Read AGENTS.md and docs/codex/CODEX\_GUIDANCE\_MAP.md.

4\. Read only task-relevant repo docs, modules, and tests.

5\. Implement inside the phase scope.

6\. Run focused offline tests first.

7\. Run the smallest broader offline suite required by repo guidance.

8\. Commit only expected files.

9\. Push and open a draft PR only when explicitly authorized.

10\. Return a final bundle.

11\. ChatGPT reviews the PR.

12\. The user decides merge, focused fix, or abandon.



Cursor must not merge.



\## Review surface



The preferred review surface is a draft pull request.



A Cursor phase is not considered reviewable until one of these exists:



\- a draft PR with final bundle in the body; or

\- a local review packet pasted to ChatGPT containing branch, status, diff stat, changed files, tests run, and patch.



Draft PR is preferred because it lets ChatGPT review the actual GitHub diff.



\## Command hygiene



Cursor must follow .cursor/rules/scryraven-command-hygiene.mdc.



Important reminders:



\- use PowerShell-native commands;

\- prefer git -C C:\\Users\\aidan\\ScryRaven;

\- do not mix Bash heredocs with PowerShell;

\- write temp files under $env:TEMP, not the repo;

\- show staged files before committing;

\- do not ask for broad allowlisting;

\- do not amend after push;

\- do not merge, rebase, reset, clean, force-push, or delete branches.



\## Publication behavior



Cursor may push and open a draft PR only when the phase prompt explicitly authorizes publication.



Allowed publication shape:



&#x20;   git -C $Repo push -u origin <phase-branch>

&#x20;   gh pr create --draft --base main --head <phase-branch>



Not allowed unless explicitly authorized:



\- merge;

\- squash merge;

\- rebase;

\- force-push;

\- reset;

\- clean;

\- branch deletion;

\- marking a draft PR ready for review.



\## Safety boundaries



No live ScryRaven/proplex/scryraven provider, model, search, retrieval, fetch/read, or validation calls unless explicitly scoped.



Do not access:



\- .env;

\- secrets or API keys;

\- raw provider payloads;

\- raw prompts;

\- DB rows;

\- private logs;

\- caches;

\- full raw traces;

\- local output packets;

\- unrelated generated artifacts;

\- private artifacts.



\## Success criteria for Composer 2.5 trial



Composer 2.5 becomes a trusted alternate worker only after several successful phases.



A successful Cursor/Composer phase has:



\- no closed-surface drift;

\- no live calls;

\- no secrets/private artifact access;

\- no shell-command hygiene mistakes;

\- expected files only;

\- focused tests passing;

\- a clean draft PR or review packet;

\- no more than one focused review fix.



Until then, Cursor is an experimental local worker, not the default replacement for Codex.



\## Recommended usage pattern



Use Cursor for bounded local work when Codex usage is constrained or when comparing agent behavior.



Use Codex as the default for serious architecture-sensitive production phases unless Composer has already proven reliable on similar work.



Use ChatGPT as the review/governance layer in both cases.

