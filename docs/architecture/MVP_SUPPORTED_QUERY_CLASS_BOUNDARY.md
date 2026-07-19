# MVP Supported Query-Class Boundary

Status: current BUILD boundary for the first product-consumed supported-query
class metadata.

## Current Product Status

ScryRaven is not friend-level MVP and is not a general supported-query MVP. The
current product-visible path is an offline fixed-fixture demo and a default-off
no-live single-relation planning dry run for conservative supported-class
queries. The former fixed-query and generic live dogfood commands remain
compatibility surfaces, but production untrusted exact-URL acquisition is
blocked and their local webpage openers are retired. Product correctness
remains unclaimed.

The fixed passport-fee query is a canonical dogfood vector for the first class
concept. It is not the architecture, not arbitrary query answering, and not a
planner.

## Boundary Contract

Profile id:

```text
mvp-current-source-of-record-single-fact-v1
```

Human description: a current public factual lookup with one answer component, a
source-of-record or official/primary source expectation, and a compact answer
that can be traced to source-bound evidence.

Supported query shape:

- asks for one current factual value, status, requirement, deadline, or fee;
- expects a public source-of-record, official, primary, or authority-bearing
  source;
- has one answer component or can be safely reduced to one answer component by a
  later planner;
- requires source display plus caveat/nonclaim output;
- does not require broad synthesis, social sentiment, advice, personal data, or
  multi-hop interpretation.

The fixed demo and predecessor live packet consumers record this boundary as
metadata only. The no-live planning dry run consumes the boundary to reduce a
conservative supported-class query into one relation-plan packet. The generic single-
relation dogfood compatibility path may consume that plan for planning and
typed blocking, but explicit confirmation does not create a target-safety-
eligible provider operation or license public fetch/read. Arbitrary query
answering, natural-language query classification, generic live supported-query
answering beyond the single-relation dogfood slice, friend-level/general MVP
readiness, source-authority posture over evidence, broad product-comparison
support, social/review authority, and product correctness remain
false/unclaimed.

The boundary's source-of-record expectation is represented for planning by
reference to the Analyst-owned source-authority posture contract in
[`SOURCE_AUTHORITY_POSTURE.md`](SOURCE_AUTHORITY_POSTURE.md). The planner may
carry the requirement by reference, but it does not create source-authority
posture over evidence.

Future FAP/Author rendering and multi-component lift constraints are documented
in [`FAP_AUTHOR_BOUNDARY.md`](FAP_AUTHOR_BOUNDARY.md) and
[`RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md`](RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md).
Those docs are doctrine only and do not open planner, FAP, Author, concurrency,
budget-lease, or model-routing implementation.

## Explicitly Out Of Class

- broad research synthesis;
- product comparisons and reliability questions;
- social/forum/review sentiment as authority;
- medical, legal, financial, or safety advice;
- subjective recommendations;
- private/personal data questions;
- multi-hop inference or speculative claims;
- multi-component synthesis;
- questions requiring source-class adapters not yet built;
- questions requiring Analyst source-authority posture beyond the simple
  source-of-record boundary;
- questions requiring Scrutineer expansion;
- questions requiring Author/FAP redesign.

## Current Entry-Planning Gate

Arbitrary query answering is not supported yet. The current no-live planning dry
run lets a user-style query enter through:

```text
python -m proplex --mvp-query-plan-status --query "<query>"
```

For supported-class queries, it emits a generic single-relation plan and
D-prime relation-intake-shaped candidate packet. For unsupported queries, it
blocks before relation planning and does not retain the unsupported query text.
It makes no live calls, model calls, source-authority adjudication, FAP/Author
changes, generic live answering, or product correctness claim.

## Generic Single-Relation Dogfood Compatibility

The former default-off generic live dogfood entrypoint remains visible for
compatibility:

```text
python -m proplex --mvp-single-relation-live-dogfood-run --query "<supported query>" --confirm-live-dogfood [--confirm-live-dprime-review]
```

It consumes the relation plan from
`core/generic_query_to_relation_planning.py` before any later acquisition
decision. It may demonstrate planning, DISCOVER candidate mechanics, and typed
blocking. Its retained provider DISCOVER path may also receive URL-bound
provider-extracted material and pass it through the pre-existing bounded
custody, Workbench, semantic, and D-prime mechanics. Explicit confirmation does
not turn that DISCOVER material into an authorized untrusted exact-URL
operation.

Current repository evidence establishes no production-eligible Linkup Fetch or
Tavily READ/Focused Extract operation for untrusted exact URLs because
sufficient committed public-target guarantees or observable final-target
lineage are not established. That evidence gap does not mean either provider is
inherently unsafe. Availability, configuration, preference, or an injected
offline fixture cannot create eligibility.

Both CLI-reachable local webpage openers are retired typed tombstones, and no
replacement local downloader exists. Fixed provider API endpoints and
explicitly authorized local broker/model endpoints remain outside the dynamic
content-target policy; a dynamic exact-URL payload does not inherit that
exclusion.

This repair therefore does not open production READ, Focused Extract, direct
fetch/read fallback, exact-URL final custody, arbitrary answering,
multi-component planning, RunKernel DAG scheduling or budget leases,
source-class adapters, social/review aggregation, FAP/Author, friend-level or
general MVP readiness, source-obligation satisfaction, or product correctness.
The retained DISCOVER-content custody and semantic/D-prime flow predates this
repair; its continued presence is not exact-URL activation or live proof.
Offline fixtures prove mechanics only.

This is not a global ranking system, source-authority policy, approved-domain
list, retrieval/filtering layer, evidence support decision, citation-eligibility
decision, source-obligation satisfaction, answer readiness, or correctness
claim. Provider rank remains preserved in diagnostics, fetch/read priority rank
is diagnostic, and PDF parsing/support remains closed.

## Roadmap Preserved

The boundary does not replace these later phases:

- `ANALYST-SOURCE-AUTHORITY-POSTURE-PACKET-01`
- `COMPONENT-MODEL-ROLE-ROUTING-MATRIX-01`
- `FAP-AUTHOR-BOUNDARY-INSPECTION-01`
- `FAP-OUTPUT-INSPECTION-AND-RENDERING-CONTRACT-01`
- `RUN-KERNEL-COMPONENT-DAG-AND-CONCURRENCY-BUDGET-01`

Social/review evidence handling, broad product comparison/reliability questions,
source-authority modules, Scrutineer expansion, and Author/FAP rendering work are
post-boundary work.
