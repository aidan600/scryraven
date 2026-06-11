PROJECT SOURCE CANDIDATE — NOT A REPO AUTHORITY DOC

# ScryRaven Source Hierarchy, RunAuthority, And Evidence Posture v4

This is upload-ready candidate text for ChatGPT Project Sources. It does not
update ChatGPT memory automatically.

## Source And Evidence Authority

Current source/evidence authority should be read through the RunAuthority chain:

```text
RunAuthorityContract -> EvidenceLedger -> SearchJudgment -> SufficiencyJudgment
-> FinalAnswerPacket -> AuthorExecutor
```

EvidenceLedger is the canonical custody and obligation owner. Aggregate source
counts, source-tier summaries, visibility exports, and survival counts are
observations or compatibility projections. They cannot satisfy official/current,
legal/current-primary, canonical-doc, source-bound numeric, or user-document
requirements unless canonical custody records support them.

SearchJudgment can require or block source-gap recovery. Source-class recovery
and authoritative-source action lanes are compatibility execution lanes that
consume RunAuthority judgments, not independent final authority.

SufficiencyJudgment owns final answer readiness, required obligations,
mandatory caveats, prohibited upgrades, conflict posture, inference posture, and
source-bound unknown posture for canonical lanes.

FinalAnswerPacket owns final evidence selection references, citation eligibility,
Author-facing posture, answer readiness, and the Author payload. AuthorExecutor
must consume the packet-derived payload rather than rebuild final authority.

## Projection Posture

Trace, report, export, and projection modules may summarize canonical state for
debugging, compatibility, diagnostics, JSONL output, or output-quality packets.
They must not:

- call providers or search;
- call models;
- mutate prompts;
- select or rerank evidence;
- select citations;
- alter Author prose;
- override RunKernel, EvidenceLedger, SufficiencyJudgment, or FinalAnswerPacket.

Diagnostic labels such as likely failure layer, source survival count, and
legacy ControllerEvidenceLedger visibility are observer fields unless a future
phase explicitly promotes them.

## Historical Docs

Older docs that say "Controller decides, orchestrator executes" are historical
unless a phase explicitly selects legacy Controller-handoff maintenance. For
AG-89+ and AG-94+ authority work, use the RunAuthority doctrine.
