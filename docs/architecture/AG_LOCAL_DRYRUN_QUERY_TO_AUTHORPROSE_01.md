# AG-LOCAL-DRYRUN-QUERY-TO-AUTHORPROSE-01

Status: ordinary-query local dry-run product-path opening.

Proof class: offline product-path dry-run proof plus phase-focused integration
tests.

Product-facing progress type: ordinary-query dry-run product-path integration.

Product path affected: local offline dry-run path only; no live installed
product behavior yet.

## Command

Generate local, ignored review packets with:

```powershell
py scripts/ag_local_dryrun_query_to_authorprose_01.py `
  --query "What is the official current permit threshold for the example program?" `
  --scenario full_supported
```

The default output directory is:

```text
output/ag_local_dryrun_query_to_authorprose_01/
```

Use `--scenario all` to generate every deterministic scenario. Tests use
`tmp_path`; generated review packets remain local/untracked because `output/`
is ignored.

## Scenarios

- `full_supported`: the user-style query enters SearchPlanner, receives
  deterministic offline support, and reaches full-ready SufficiencyReadiness,
  hardened FAP, and AuthorProse.
- `partial_unresolved`: the user-style query enters SearchPlanner with an
  optional context component before initial contract acceptance. Only the
  primary component receives deterministic offline support, so AuthorProse
  preserves partial posture.
- `contested_weak`: the user-style query receives deterministic offline
  candidate/content custody, but weak or stale Specialist posture preserves
  contested posture through SufficiencyReadiness, hardened FAP, and
  AuthorProse.

## Reviewable Output

Each JSON and Markdown packet records:

- original user-style query;
- ordinary query digest plus current-path SearchPlanner query ref;
- selected scenario;
- current-path surfaces consumed;
- fake/offline sanitized provider-result posture;
- SearchResultCandidatePacket, FetchReadContentPacket, content, and custody
  refs;
- EvidenceLedger, EvidenceRelativeAnalysisPacket, SemanticObservation,
  ComponentCoverage, Scrutineer, Specialist, SufficiencyReadiness, hardened FAP,
  and AuthorProse posture where applicable;
- actual current-path outputs from reducers/builders/runtimes;
- what is newly ordinary-query-driven versus inherited deterministic fixture
  behavior;
- caveats, blockers, contested posture, explicit non-proofs, old path treatment,
  live validation status, and mandatory next checkpoint.

The review packet is output-only packaging. AuthorProse text comes from the
existing hardened FAP -> AuthorProseFinalization current path. The packet does
not hand-assemble final answer prose.

## Query Entry

The input begins as a user-style query string supplied to `--query`. The runner
passes that string into the existing SearchPlanner input, which records a
current-path `user_query_ref` and drives the deterministic planner component
question and component search requirement summary. The deterministic fake
provider records, readable content material, Analyst proposal, Specialist
posture, and Scrutineer posture are inherited fixture behavior and are disclosed
as such.

## Explicit Non-Proofs

This phase does not prove:

- live provider, broker, model, search, fetch/read, or retrieval calls;
- real source acquisition quality;
- real-source fetch/read survival;
- messy-live-evidence semantic support;
- citation rendering;
- citation eligibility in user-visible output;
- source-obligation satisfaction;
- installed product behavior;
- product correctness;
- product-quality Author prose;
- natural-language query understanding by a model.

Live validation was not run and is not licensed in this phase. Fake/offline
provider-shaped records do not imply real acquisition, ranking, or source
quality.

## Old Path Treatment

Old Author/FAP/follow-up/sufficiency/AG-89D/AG-91K/AG-92C/AG-96/pipeline/
offline bridge surfaces remain legacy/passive/historical or closed. The runner
uses the current hardened FinalAnswerPacket and AuthorProseFinalization path; it
does not execute old Author or revive old FAP preparation.

## Mandatory Next Checkpoint

Mandatory next checkpoint: tightly scoped limited live validation phase only if this ordinary-query dry-run is honest and reviewable.

The next checkpoint is a tightly scoped limited live validation phase only if
this ordinary-query dry-run is honest and reviewable. Do not start live
validation as part of this phase.
