PROJECT SOURCE CANDIDATE — NOT A REPO AUTHORITY DOC

# ScryRaven Productization Roadmap v11: Authority Doctrine And Official Acquisition

This is upload-ready candidate text for ChatGPT Project Sources. It does not
update ChatGPT memory automatically.

## Current Architecture Baseline

ScryRaven now has a runtime-consumed RunAuthority chain:

```text
RunAuthorityContract -> EvidenceLedger -> SearchJudgment -> SufficiencyJudgment
-> FinalAnswerPacket -> AuthorExecutor
```

This chain is not trace-only. RunKernel authorizes bounded actions, reducers
commit canonical observations, and final Author execution consumes the
FinalAnswerPacket-derived payload.

Legacy Controller and lifecycle surfaces remain where they still protect
compatibility behavior. They are not the default doctrine for new
authority-collapse work.

## Near-Term Roadmap

1. Official-source acquisition quality audit.
   Focus on why official/current recovery can execute yet still acquire weak,
   generic, stale, incomplete, or non-official candidates. Do not mix this with
   doctrine cleanup.

2. Repo-doc doctrine alignment.
   Update current-looking architecture summaries so they point to the
   RunAuthority doctrine and classify old Controller doctrine as historical.

3. Trace/export/report no-redecision guard.
   Add static guards proving projection/report/export modules observe canonical
   state and do not call providers/search/models, mutate prompts, select
   evidence, select citations, or override final answer authority.

4. Active compatibility island demotion.
   Choose one lane at a time: source-class recovery dispatch, retrieval
   stop/continue, Controller loop spine, weak-corpus recovery, or
   conflict-resolution retrieval.

5. Naming compatibility plan.
   Inventory ScryRaven versus legacy `proplex`/`PROPLEX_*` names and create a
   compatibility plan before any rename. Do not rename package, CLI, env, DB, or
   public API surfaces opportunistically.

## Guardrails

- No live provider/model/search/retrieval calls unless a phase explicitly scopes
  budget, query class, redaction, packet path, and stop conditions.
- Protected product behavior includes provider routing, search depth, query
  generation, ranking/filtering, citation behavior, prompt semantics, Author
  prose, and final answer behavior.
- Historical AG docs should be preserved, not bulk rewritten.
