# ScryRaven Current Truth

Status: Part B product decision complete; repository reset pending
Repository: `aidan600/scryraven`
Preferred local checkout: `C:\Users\aidan\ScryRaven`

## Current product state

Part B has established the initial ScryRaven product promise and selected the first walking-skeleton design sufficiently for implementation preparation.

The walking skeleton is **not yet implemented**.

The existing v1 application remains physically present in the repository until the separately reviewed repository-reset work is completed. Its presence does not make it current product architecture.

`PRODUCT.md` owns the approved product behavior.

## Selected first-slice responsibility boundary

The selected initial design has three semantic responsibilities:

```text
Research
→ Analyst
→ Author
```

with bounded feedback from Analyst back to Research when acquired evidence reveals a consequential unresolved information need.

### Research

Research decides how to investigate the current information need.

It may form or revise searches, inspect discovery clues semantically, select candidates for direct reading, reject poor leads, and investigate a specific semantic gap identified by Analyst.

Poor discovery remains inside Research.

Discovery-result material guides navigation but is not final answer evidence.

### Analyst

Analyst semantically interprets acquired source material in the context of the original question.

It determines answer-relevant findings, preserves material qualifications and conflicts, identifies supporting evidence, may identify evidence still useful for continued analysis, and may state a specific unresolved semantic information need for Research.

Analyst authors the semantic gap.

Research authors the research action.

There is no separate Sufficiency owner or mandatory semantic reviewer in the selected first-slice design.

### Author

Author receives the original question, answer-relevant finding or limitation, the explanation needed for faithful writing, and selected acquired supporting material with source identity.

Author explains the supported result.

It does not normally receive discovery snippets, research history, rejected pages, or the complete Analyst corpus, and it does not perform a second research process.

Ordinary deterministic application code sequences these responsibilities and resolves evidence references and citations mechanically.

## First supported scope

The first supported scope is a single-component factual research question answerable through public web research.

The intended first product demonstrations are:
```text
STRAIGHT
discover
→ useful lead
→ direct read
→ supported Analyst finding
→ selected Author material
→ cited answer
```
```text
ADAPTIVE
poor discovery or inadequate acquired evidence
→ revised research or Analyst-requested follow-up
→ new acquired evidence
→ supported answer
```
```text
UNSUPPORTED
reasonable bounded research
→ acquired evidence still does not establish the answer
→ honest limitation
```

The demonstrations should cover more than one ordinary factual topic. The bowling-ball maximum-weight question remains a reasonable canonical straight-path example.

These are product behaviors to demonstrate, not a new evaluation framework.

## Provisional implementation hypotheses

The following are current implementation hypotheses, not product invariants:

- use an ordinary sequential bounded research loop;
- keep small per-run research information in ordinary in-memory application data if that makes the loop clearer;
- try the FAST configuration for search/query/navigation work;
- try the SMART configuration for evidence interpretation;
- try FAST with low or no deep reasoning for answer writing;
- initially use narrow Linkup discovery and direct-fetch mechanics carried forward from v1;
- represent successful direct acquisition as immutable local evidence snapshots with stable local and source identity;
- let Analyst distinguish answer-support references from evidence that remains useful for another analysis pass;
- build a small explicit Author handoff from Analyst-selected supporting evidence;
- keep candidate counts, read sizes, navigation limits, exact reference shapes, prompts, model assignments, and model-call counts easy to change.

None of those choices is protected architecture merely because it is tried first.

## Retained infrastructure and donors

The general credential broker / doorman remains retained infrastructure for running approved credentialed local commands without exposing the private environment to the controlling coding agent. It is not product reasoning architecture.

The selected v1 code donors are limited to narrow mechanical behavior from:

- Linkup standard discovery/search-result request and response handling; and
- Linkup direct Fetch request, response, and selected-URL read handling.

The surrounding v1 search, routing, authorization, retry-budget, custody, and control-plane systems are not donors by association.

Tavily search/extract and other provider implementations are not selected active donors for the first implementation and remain available through Git history if later evidence justifies reconsideration.

## Ideas selected for simple reimplementation

The following concepts survive, but their v1 implementations do not:

- adaptive question-directed research and semantic candidate triage;
- FAST / SMART as simple configurable model-role concepts;
- model-based Analyst evidence interpretation;
- separate answer writing from evidence interpretation;
- immutable acquired evidence with simple source/provenance continuity;
- answer-support references and active-analysis evidence references;
- a small explicit Analyst-to-Author material handoff; and
- finite ordinary application control for adaptive research.

## v1 mechanisms not carried forward

The future active product tree does not carry forward the v1 implementations of:

- SearchOS, SearchPlanner, QueryPlan, SearchWorkPlan, and their authority/state machinery;
- EvidenceLedger custody/admission/lifecycle machinery;
- FinalAnswerPacket and associated readiness, eligibility, authority, and materialization machinery;
- RunKernel / RunAuthority and controller/reducer/checkpoint architecture;
- graphs, schedulers, leases, grants, reservations, and component-work machinery;
- D-prime;
- Cross / the v1 multi-component runtime;
- separate Sufficiency machinery;
- Scrutineer;
- source-class and generalized recovery/control-plane systems;
- architecture-level pricing, token, cost, and attempt-authorization systems;
- obsolete v1 alternate product, dogfood, compatibility, and runtime paths; or
- tests, configuration, and active documentation whose only purpose is preserving retired v1 architecture.

Git history, not a dormant active-tree fallback, preserves that implementation history.

## Deferred next product capability

Multi-component research remains the immediate next product capability after the single-component walking skeleton works.

It is not implemented or prebuilt during the repository reset.

## Next authorized repository work

After this Part B `PRODUCT.md` / `CURRENT.md` decision is reviewed and merged, the next authorized repository work is a repository reset and preparation work item.

That reset should retire the old v1 active-tree application estate, preserve the Part A operating system and explicitly selected infrastructure/donors, preserve Git history and an immutable final-v1 tag, and leave a small coherent foundation for walking-skeleton implementation.

The reset must not perform live ScryRaven/provider/model/search calls and must not begin substantive implementation of the walking skeleton.

Walking-skeleton implementation is a later work item, only after the reset has been reviewed and merged.
