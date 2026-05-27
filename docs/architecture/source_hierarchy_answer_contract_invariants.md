# Source Hierarchy and Answer-Contract Invariants

Status: AG-57A invariant baseline. This is an engineering contract and test
map, not a runtime behavior repair.

## Purpose

ProPlex can look grounded because it cites something while still missing the
source class required by the claim. AG-57A records the source hierarchy and the
controller ownership rule before broader prompt or deterministic repairs:

```text
Source insufficiency ownership belongs to the Controller and AnswerContract.
Analyst, Economist, Author, Scrutineer, and follow-up surfaces must obey the
controller-authorized source obligation and final posture.
```

This document is repo-facing. It does not assume any ChatGPT Project Source
file exists in the repository.

## Claim-Sensitive Source Hierarchy

The controlling rule is:

```text
The source class required by the claim outranks a generally better source class
that is not authoritative for that claim.
```

Use this hierarchy when reviewing source obligations and future repairs:

| Claim shape | Required source posture |
| --- | --- |
| Current product, project, API, package, SDK, browser, database, pricing, policy, status, release, changelog, or official announcement claims | Official/current/canonical documentation or official pages anchor the claim. |
| Current law, regulation, agency guidance, court/procedural status, eligibility, statutory threshold, deadline, or jurisdiction-sensitive requirement | Primary/legal/regulatory or official/current sources anchor the claim. |
| Explicit paper, literature review, peer-reviewed evidence, empirical study, causal claim, benchmark methodology, or independent performance comparison | Academic literature is required or central. |
| Ordinary explainer, background, developing-event context, expert interpretation, or non-primary overview | Reputable secondary sources can be sufficient unless an embedded claim requires an official/current/primary source. |
| Practical project or community usage signal | Trusted community sources are directional unless the project treats that surface as official or canonical. |
| Social/forum evidence | Directional only. It must not satisfy factual, official, legal, medical, financial, or source-bound numeric obligations. |
| Weak, off-topic, or no-good evidence | Trigger bounded recovery if the missing required source class is reachable; otherwise return a controller-authorized insufficient-evidence posture. |

## Ownership Invariants

- The Controller and AnswerContract own source-obligation fulfillment,
  insufficiency, stop posture, and partial/insufficient final posture.
- Analyst and Author do not turn missing required source classes into confident
  final claims by adding weak or off-topic citations.
- Author citation pressure does not make secondary, community, or social sources
  authoritative for official/current/legal/canonical claims.
- Economist keeps numeric values source-bound. Missing source-bound values
  should abort, caveat, or surface unavailability according to the existing
  quantitative contract.
- Follow-up must not treat stale saved report context as sufficient for a new
  current/official/canonical/source-bound obligation.
- Public/final surfaces must not expose raw prompts, raw provider payloads,
  raw evidence dumps, raw quantitative packets, `economist_v1`, full traces,
  private diagnostics, local packets, secrets, or database rows.

## Test Matrix

AG-57A encodes the baseline in
`tests/test_source_hierarchy_answer_contract_invariants_ag57a.py`.

| Family | Encoded as |
| --- | --- |
| Canonical technical docs | PostgreSQL MVCC, SQLite WAL, Python dataclasses, MDN Fetch credentials, and Kubernetes configuration policy-helper invariants. |
| Explicit academic literature | Peer-reviewed, literature review, empirical study, and arXiv negative controls for canonical-doc defaults. |
| Mixed canonical plus academic | Strict xfail documenting the current lack of multi-source obligation representation. |
| Official/current numeric or rule claims | Official-source obligation bridge requires `official_current_rules` even when secondary sources are present. |
| Legal/current-primary | AnswerContract family and recovery action require legal/regulatory or official/current source classes. |
| Ordinary conceptual explainers | Negative control: concept explanations do not force official recovery when reputable secondary evidence is enough. |
| Weak/no-good evidence | Weak corpus reaches insufficient/caveated stop posture when recovery is spent. |
| Quantitative/Economist | Official numeric diagnostics preserve caveated missing-evidence and source-bound value lanes without behavior changes. |
| Author citation/source fit | Fulfillment handoff downgrades secondary-only support for official-current claims and records Analyst/Author warnings. |
| Leakage and boundary guards | Public handoff redacts protected prompt, trace, provider, and quantitative packet markers. |

## Current Known Gap

The mixed question shape is not represented as a first-class multi-source
contract yet:

```text
What do the docs say, and what do studies show?
```

The current contract taxonomy can represent canonical technical docs and
explicit academic requests through nearby policy seams, but it does not yet
express simultaneous canonical and academic obligations as independent source
classes. AG-57A therefore records this as a strict xfail and a next product
decision rather than changing prompts, routing, source recovery, or final answer
behavior.

## Closed Surfaces

AG-57A does not authorize changes to:

- runtime prompts;
- provider routing, selection, depth, or integration;
- source ranking, filtering, or runtime classification;
- citation selection or final-answer posture;
- Analyst, Economist, Author, Scrutineer, follow-up, or weak-corpus behavior;
- broad `core/pipeline_orchestrator.py` domain logic;
- live validation or provider/model/search calls.

## Recommended Sequencing

Use the AG-57A tests and this document to choose the next licensed surface:

| Finding | Recommended next phase |
| --- | --- |
| Prompt wording alone causes canonical docs to collapse into academic routing | AG-57B Router/Researcher prompt contract repair. |
| Deterministic obligation or recovery policy fails to preserve required source classes | AG-58A deterministic source-obligation alignment. |
| Insufficient-evidence or citation posture requires protected handoff/final-answer changes | AG-59A/B insufficiency and final-posture repair. |
| Mixed-source representation remains ambiguous | Stop for a product/modeling decision before repair. |

No local packet is required or committed for AG-57A. Live validation remains
unused.
