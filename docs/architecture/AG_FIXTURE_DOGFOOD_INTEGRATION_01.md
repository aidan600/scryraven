# AG-FIXTURE-DOGFOOD-INTEGRATION-01

Status: product-facing dry-run dogfood output for deterministic fixture scenarios.

Proof class: product-facing dry-run proof plus phase-focused integration tests.

Product path affected: offline fixture dogfood path only. This does not change
ordinary live user-query execution or installed product behavior.

## Command

Generate local, ignored review packets with:

```powershell
py scripts/ag_fixture_dogfood_integration_01.py
```

The default output directory is:

```text
output/ag_fixture_dogfood_integration_01/
```

Tests use `tmp_path`; generated review packets remain local/untracked by
default.

## Scenarios

- `01_full_supported`: candidate/content/custody through Analyst support,
  SemanticObservation admission, ComponentCoverage, Specialist, Scrutineer,
  SufficiencyReadiness, hardened FAP, and AuthorProse.
- `02_partial_unresolved`: the deterministic planner fixture emits one
  supported component plus `component:optional-context` before initial contract
  acceptance; only the first component receives fixture coverage, so
  AuthorProse preserves partial posture without direct contract mutation.
- `03_contested_weak_evidence`: supported custody/coverage with weak or stale
  Specialist inputs; Sufficiency, FAP, and AuthorProse preserve contested
  posture.

## Reviewable Output

Each JSON and Markdown packet records:

- input scenario;
- current-path surfaces consumed or marked not applicable;
- candidate/content/custody refs;
- component coverage summary;
- follow-up, Scrutineer, and Specialist posture;
- SufficiencyReadiness status;
- hardened FAP status;
- final AuthorProse output;
- caveats, blockers, or contested posture;
- explicit non-proofs.

The packets are output-only review packaging. They are valid only because they
record outputs from existing current-path reducers/builders/runtimes; they do
not introduce a new authority surface.

## Explicit Non-Proofs

This phase does not prove:

- ordinary live user-query execution;
- live source acquisition quality;
- real-source fetch/read survival;
- messy-live-evidence semantic support;
- citation rendering;
- citation eligibility in user-visible output;
- source-obligation satisfaction;
- product correctness;
- product-quality Author prose;
- live validation.

Old FAP/Author/follow-up/sufficiency/AG-89D/AG-91K/AG-92C/AG-96/pipeline/
offline bridge surfaces remain legacy/passive/historical or closed.

Mandatory next product-path checkpoint:
`AG-LOCAL-DRYRUN-QUERY-TO-AUTHORPROSE-01`.
