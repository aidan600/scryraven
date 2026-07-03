# ScryRaven MVP Friend Runbook

Status: short friend-shareable MVP/demo runbook for the fixed MVP demo and
live dogfood slices.

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
entry planning. The fixed live dogfood slice is not friend-level or general MVP,
and product correctness remains unclaimed.

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

The generic live dogfood path is default-off and requires a supported query plus
explicit live confirmation:

```powershell
py -m proplex --mvp-single-relation-live-dogfood-run --query "What is the current USCIS Form N-400 paper filing fee?" --confirm-live-dogfood
```

The command first consumes the generic relation plan. If the planner rejects the
query, it blocks before live calls and does not retain unsupported query text.
For a planned query, the live search seed, component refs, source-obligation
refs, source-authority posture requirement ref, and D-prime relation-intake
posture come from the relation plan rather than from the fixed passport dogfood
path.

Fetch/read attempts use a local, packet-visible acquisition-priority policy over
the already-sanitized provider candidates. The policy may prefer
official/source-of-record-looking candidates under the existing fetch/read cap,
but it is acquisition only: it does not decide source authority, satisfy source
obligations, make candidates citation-eligible, claim correctness, or use
provider snippets as evidence. PDF-looking candidates may be attempted, but PDF
parsing/support remains closed and PDF content type failures remain diagnostic
until a later PDF phase opens that surface.

If all selected official/source-of-record-looking public-web candidates return
HTTP 4xx under the existing fetch/read cap, the run reports
`BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX`. That
is an HTTP source-survival blocker, not source authority, evidence support,
citation eligibility, source-obligation satisfaction, PDF support, FAP/Author,
or product correctness.

Without D-prime confirmation, the command may acquire bounded live
search/fetch/read/custody status and then stops with:

```text
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
```

To license one product-route D-prime review for the same run, pass:

```powershell
py -m proplex --mvp-single-relation-live-dogfood-run --query "What is the current USCIS Form N-400 paper filing fee?" --confirm-live-dogfood --confirm-live-dprime-review
```

This generic dogfood path is still single-relation only. It is not arbitrary
answering, not general supported-query live answering, not multi-component
planning, not RunKernel DAG scheduling, not FAP/Author, not friend-level/general
MVP readiness, and not product correctness. Fake-provider test PASS is not live
validation PASS.

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

Live dogfood is not the default demo. It requires an explicitly licensed run,
explicit confirmation flags, and the private local broker/operator boundary for
provider credentials.

Run the narrow live dogfood entrypoint only for the fixed MVP question:

```powershell
py -m proplex --mvp-live-dogfood-run --confirm-live-dogfood
```

That command is capped to the current live dogfood slice. It uses at most one
licensed provider/search call, up to five provider results, and up to three
fetch/read attempts for the fixed query. It writes sanitized retained artifacts
under `output/mvp_live_dogfood_01/<run-id>/` and then consumes those artifacts
through the existing MVP live status path. Without the separate D-prime review
confirmation below, it is expected to stop at
`BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING`.

To license the one-shot product-route D-prime review in the same fixed-query
dogfood run, pass the separate review confirmation:

```powershell
py -m proplex --mvp-live-dogfood-run --confirm-live-dogfood --confirm-live-dprime-review
```

That route allows at most one D-prime/model-review call, no follow-up loops, and
no Author/model calls. It does not support arbitrary queries, does not claim
friend-level MVP readiness, does not claim general supported-query MVP
readiness, does not claim product correctness, and does not open
Economist/Specialist routing, Scrutineer remediation, AuthorProse, or broad
model-provider routing. Its packet identifies the fixed query as a canonical
dogfood example of the first supported-query-class concept, not as arbitrary
query support.

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
