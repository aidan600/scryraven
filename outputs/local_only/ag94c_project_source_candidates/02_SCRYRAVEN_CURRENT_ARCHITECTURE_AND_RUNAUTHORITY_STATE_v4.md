PROJECT SOURCE CANDIDATE — NOT A REPO AUTHORITY DOC

# ScryRaven Current Architecture And RunAuthority State v4

This is upload-ready candidate text for ChatGPT Project Sources. It does not
update ChatGPT memory automatically.

## Current Authority Doctrine

ScryRaven is the public project name. Historical compatibility names remain
supported where already present: `proplex`, `python -m proplex`, `PROPLEX_*`,
`proplex.db`, and `proplex_*` state keys.

The active runtime authority doctrine is RunKernel / RunAuthority first:

```text
RunAuthorityContract -> EvidenceLedger -> SearchJudgment -> SufficiencyJudgment
-> FinalAnswerPacket -> AuthorExecutor
```

RunKernel / RunAuthority owns run-level meaning and canonical authority.
Executors perform bounded work. Reducers commit observations into canonical
RunState, EvidenceLedger, and FinalAnswerPacket state. Trace, export, report,
and projection surfaces observe canonical state and must not re-decide it.

`core/pipeline_orchestrator.py` is a coordination shell. It may coordinate
lifecycle flow, call bounded executors, and attach trace fragments, but it
should not become a domain brain.

Legacy Controller/lifecycle surfaces may remain only as passive mirrors,
compatibility executors, bounded adapters, RunAuthority-subordinated lanes, or
explicitly scheduled retirement surfaces.

## Current Compatibility Islands

Active compatibility lanes still exist and should be changed only in focused
phases:

- source-class/authoritative-source recovery dispatch;
- retrieval stop/continue;
- Controller loop spine dispatch arbitration;
- weak-corpus recovery;
- conflict-resolution retrieval;
- Economist, Scrutineer, and synthesis-evaluator supplemental behavior.

These are not naming-cleanup targets. They are protected behavior or active
compatibility authority until a phase explicitly scopes demotion or retirement.

## Current Product Lane

AG-94B repaired the custody/export/report failure enough that the live path can
reach official-current recovery execution and provider/candidate acquisition.
The next product-behavior issue remains official-source acquisition quality
unless a later audit finds a blocking authority issue.

## Operating Rules

- Do not run live provider/model/search/retrieval calls unless the phase
  explicitly scopes them.
- Do not access secrets, `.env`, raw provider payloads, raw prompts, DB rows,
  private logs, caches, full raw traces, or local output packets unless safely
  scoped.
- Do not rename packages, CLIs, env vars, DB names, public APIs, or session keys
  during architecture doctrine cleanup.
- Do not delete historical AG docs just because their vocabulary is old.
