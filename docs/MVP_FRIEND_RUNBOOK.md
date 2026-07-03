# ScryRaven MVP Friend Runbook

Status: short friend-shareable MVP/demo runbook for
LICENSED-LIVE-DOGFOOD-AND-MVP-POLISH-01.

## What It Does Today

ScryRaven can take one fixed fixture question through the current D-prime
product status path: retained source candidate, bounded fetch/read handoff,
EvidenceLedger custody, D-prime review, RunKernel admission, ComponentCoverage,
answer-path consumption, Author answer text, and source display. The MVP demo is
offline and deterministic; it is for reviewing the shape of the product output,
not for proving the real-world answer is correct or for answering arbitrary
queries.

## Offline MVP Demo

Run:

```powershell
py -m proplex --mvp-demo
```

The only supported demo question is:

> What is the current adult U.S. passport book renewal fee by mail?

If another query is supplied, the command returns
`BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED`. That blocker means the offline MVP demo
is a fixed deterministic fixture. Arbitrary query answering requires the
live/ordinary product path, which remains blocked by
`BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING`.

The command requires no secrets. It writes a sanitized review packet under
`output/mvp_demo_01/` and prints a compact human view with:

- answer or blocker;
- source display when the answer path is consumed;
- Scrutineer, multi-source, and follow-up state in compact form;
- explicit caveats and non-claims.

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

Live dogfood is not the default demo. It requires an explicitly licensed run and
the private local broker/operator boundary for provider credentials. Do not
paste or commit `.env` contents, API keys, broker tokens, raw provider payloads,
raw prompts, raw model responses, private logs, DB/cache rows, or full traces.

After separately retained sanitized live artifacts exist, this status command
can consume them without making live calls:

```powershell
py -m proplex --mvp-live-dogfood-status --query "What is the current adult U.S. passport book renewal fee by mail?"
```

It writes a sanitized packet under `output/mvp_live_dogfood_01/` and records the
answer or named blocker. Product correctness remains unclaimed.
