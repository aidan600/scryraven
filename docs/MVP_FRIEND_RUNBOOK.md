# ScryRaven MVP Friend Runbook

Status: short friend-shareable MVP/demo runbook for the fixed offline MVP demo;
former live dogfood commands are compatibility surfaces with blocked exact-URL
acquisition.

## What It Does Today

ScryRaven can take one fixed fixture question through the current D-prime
product status path: retained source candidate, bounded fetch/read handoff,
EvidenceLedger custody, D-prime review, RunKernel admission, ComponentCoverage,
answer-path consumption, Author answer text, and source display. The MVP demo is
offline and deterministic; it is for reviewing the shape of the product output,
not for proving the real-world answer is correct or for answering arbitrary
queries.

Current MVP packets also carry the first supported-query-class boundary:
`mvp-current-source-of-record-single-fact-v1`. That boundary is documented in
[`docs/architecture/MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md`](architecture/MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md).
It defines the current source-of-record single-fact lookup concept and keeps
arbitrary query planning, friend-level/general MVP readiness, and product
correctness unclaimed.

## Offline MVP Demo

Run:

```powershell
py -m proplex --mvp-demo
```

The only supported demo question is:

> What is the current adult U.S. passport book renewal fee by mail?

If another query is supplied, the command returns
`BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED`. That blocker means the offline MVP demo
is a fixed deterministic fixture. Arbitrary query answering is not supported
yet; use the no-live query plan dry run below for conservative supported-class
entry planning. The former fixed live dogfood slice is retained only as a
blocked compatibility surface; it is not friend-level or general MVP, and
product correctness remains unclaimed.

The command requires no secrets. It writes a sanitized review packet under
`output/mvp_demo_01/` and prints a compact human view with:

- answer or blocker;
- source display when the answer path is consumed;
- Scrutineer, multi-source, and follow-up state in compact form;
- explicit caveats and non-claims.

## No-Live Query Plan Dry Run

Run:

```powershell
py -m proplex --mvp-query-plan-status --query "What is the current filing fee for small claims in Example County?"
```

The command requires no secrets and makes no live/model calls. For conservative
supported-class queries, it writes a sanitized single-relation planning packet
under `output/mvp_query_plan_01/` and prints the packet path. The packet carries
the supported-query-class boundary, a generic relation plan, a
D-prime relation-intake-shaped candidate, and future ComponentWorkNode-liftable
metadata.

Unsupported queries block before relation planning and do not retain the
unsupported query text. This is not generic answering, generic live supported
query execution, source-authority adjudication, FAP/Author output,
friend-level/general MVP readiness, or product correctness.

## Generic Single-Relation Live Dogfood

The generic live dogfood command remains a default-off compatibility and
operator surface:

```powershell
py -m proplex --mvp-single-relation-live-dogfood-run --query "What is the current USCIS Form N-400 paper filing fee?" --confirm-live-dogfood
```

It still consumes the generic relation plan and fails closed on unsupported
queries. Explicit confirmation does not create provider-operation eligibility
or license an untrusted exact-URL transport.

Current production posture is fail-closed for exact targets. ScryRaven lacks
sufficient committed public-target guarantees or observable final-target
lineage to assert that Linkup Fetch or Tavily READ/Focused Extract is eligible
for untrusted exact URLs. This is an evidence gap, not a claim that either
provider is inherently unsafe. Provider availability, configuration, a
preferred provider name, or an offline fixture cannot change that posture.

The two CLI-reachable local webpage openers are retired typed tombstones. There
is no direct `urllib`, `requests`, `httpx`, browser, or replacement local
webpage downloader. Fixed provider API endpoints and explicitly authorized
local broker/model endpoints remain outside the dynamic content-target policy,
but that exclusion does not make a dynamic exact-URL payload eligible.

Accordingly, this command must not be presented as a working live extraction,
READ, fetch/read fallback, custody, D-prime, semantic, FAP, or Author path. It
may still demonstrate planning, DISCOVER candidate mechanics, typed blocking,
and bounded offline fixtures. Those fixtures prove mechanics only and do not
activate production READ, Focused Extract, final custody, semantic admission,
or product correctness.

## How To Read It

`Decision: PASS` means the offline demo reached the current MVP answer-output
path. It does not mean the fee is correct today.

`Sources` shows the source-display entries produced by the consumed D-prime
source-display surface. It is reviewable source display, not a correctness
claim.

`Challenge State` shows whether Scrutineer, multi-source posture, or follow-up
logic participated. For the default demo, Scrutineer is not invoked because it
is a single-source lane.

## Live Dogfood

The former fixed live-dogfood command remains visible for compatibility and
historical packet review:

```powershell
py -m proplex --mvp-live-dogfood-run --confirm-live-dogfood
```

It no longer describes a licensed public fetch/read path. Its local webpage
opener is a typed fail-closed tombstone, and the current production provider-
mediated route has no target-safety-eligible Linkup/Tavily operation for an
untrusted exact URL. Explicit confirmation flags and provider credentials do
not change either fact. Do not invoke this command expecting provider READ,
local webpage transport, custody, semantic admission, D-prime review, or answer
completion.

Prior sanitized live packets remain predecessor evidence only. They do not
establish current provider eligibility or authorize a replay against the public
network.

Do not paste or commit `.env` contents, API keys, broker tokens, raw provider
payloads, raw prompts, raw model responses, private logs, DB/cache rows, or full
traces.

After separately retained sanitized live artifacts exist, this no-live status
command can consume them without making live calls:

```powershell
py -m proplex --mvp-live-dogfood-status --query "What is the current adult U.S. passport book renewal fee by mail?"
```

It writes a sanitized packet under `output/mvp_live_dogfood_01/` and records the
answer or named blocker. Product correctness remains unclaimed.
