# ScryRaven Current Truth

Status: Part B product decision complete; repository reset prepared for review
Repository: aidan600/scryraven
Preferred local checkout: C:\Users\aidan\ScryRaven

## Approved product state

Part B remains the approved product decision. The first supported product
promise is a single-component factual research answer grounded in acquired
public-web source material. The selected future responsibility boundary is:

Research
→ Analyst
→ Author

with bounded Analyst-directed follow-up returning to Research when acquired
evidence exposes an important unresolved information need.

The walking skeleton is not implemented.

## Repository state after this reset

The active tree is intentionally a small foundation:

- root AGENTS.md, PRODUCT.md, and CURRENT.md;
- the minimal Cursor pointer to root guidance;
- ordinary repository hygiene and development configuration;
- the general operator credential doorman at
  scripts/run_brokered_command_once.py;
- one neutral Linkup transport surface at core/linkup_transport.py;
- a minimal non-executable scryraven namespace; and
- focused offline tests for the retained surfaces.

The reset does not run ScryRaven and makes no live provider, model, search, or
Fetch call. The walking skeleton remains unimplemented and no production
ResearchState, AnalystResult, AuthorMaterial, support-reference, or active
evidence-reference contract has been created.

## Retired v1 active estate

The former v1 application and runtime are no longer active in the filesystem.
This includes the old SearchOS, SearchPlanner, SearchJudgment, QueryPlan,
SearchWorkPlan, EvidenceLedger, FinalAnswerPacket, RunKernel, RunAuthority,
D-prime, Cross, Sufficiency, Scrutineer, graph, scheduler, recovery,
provider-proxy, pricing/cap/attempt-authority, and alternate CLI/UI estates.
Their callers, compatibility machinery, exclusive tests, configuration, and
current documentation were removed with them.

Git history preserves the implementation history. The annotated immutable tag
v1-final-implementation points to the verified final v1 baseline
bdefe506ffb58df491e31156771f4e0712e3dd2b. No active archive, legacy copy, or
fallback tree was created.

## Retained donor boundary

core/linkup_transport.py carries only:

- one Linkup standard search request using standard depth and searchResults;
- query and bounded result-count construction;
- mechanical credential-header construction;
- bounded title, URL, and discovery-context normalization;
- one direct Linkup Fetch request for a selected URL; and
- readable returned-material extraction mechanically associated with that URL.

It deliberately carries no routing, retry, cap, cost, model, evidence,
custody, semantic, authority, answer, or lifecycle behavior.

## Next authorized repository work

After human review and merge of this reset, the next potential product work is
implementation of the approved Research → Analyst → Author walking skeleton.
That work has not begun in this reset.
