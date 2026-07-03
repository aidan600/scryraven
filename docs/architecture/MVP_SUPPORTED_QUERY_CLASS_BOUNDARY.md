# MVP Supported Query-Class Boundary

Status: current BUILD boundary for the first product-consumed supported-query
class metadata.

## Current Product Status

ScryRaven is not friend-level MVP and is not a general supported-query MVP. The
current product-visible path is an offline fixed-fixture demo, a default-off
fixed-query live dogfood slice, a default-off no-live single-relation planning
dry run for conservative supported-class queries, and a default-off generic
single-relation live dogfood slice that must consume the relation plan before
live acquisition. Product correctness remains unclaimed.

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

The fixed demo/live packet consumers record this boundary as metadata only. The
no-live planning dry run consumes the boundary to reduce a conservative
supported-class query into one relation-plan packet. The generic single-relation
live dogfood path may consume that relation plan under explicit live
confirmation and caps, but only for one planned relation. Arbitrary query
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

## Generic Single-Relation Live Dogfood

The default-off generic live dogfood entrypoint is:

```text
python -m proplex --mvp-single-relation-live-dogfood-run --query "<supported query>" --confirm-live-dogfood [--confirm-live-dprime-review]
```

It must consume the relation plan from
`core/generic_query_to_relation_planning.py` before live acquisition. The live
search query seed, component id/text, source-obligation id/text, search
requirement id/text, source-authority posture requirement ref, and D-prime
relation-intake posture come from that plan, not from the fixed passport
dogfood constants.

This path is generic single-relation dogfood only. It does not open arbitrary
answering, multi-component planning, RunKernel DAG scheduling or budget leases,
source-class adapters, social/review aggregation, FAP/Author, friend-level or
general MVP readiness, source-obligation satisfaction by the packet alone, or
product correctness.

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
