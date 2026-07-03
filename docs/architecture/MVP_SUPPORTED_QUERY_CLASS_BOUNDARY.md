# MVP Supported Query-Class Boundary

Status: current BUILD boundary for the first product-consumed supported-query
class metadata.

## Current Product Status

ScryRaven is not friend-level MVP and is not a general supported-query MVP. The
current product-visible path is an offline fixed-fixture demo plus a
default-off fixed-query live dogfood slice. Product correctness remains
unclaimed.

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

Current packet consumers record this boundary as metadata only. The metadata
states that arbitrary query planning, natural-language query classification,
query-to-relation planning, friend-level/general MVP readiness, source-authority
posture, broad product-comparison support, social/review authority, and product
correctness are all false/unclaimed.

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

## Future Entry Gate

Arbitrary query answering is not supported yet. Before a user query can enter
the live answer path as part of this class, a future query-to-relation planning
phase must prove that the query can be reduced to one answer component, preserve
the source-of-record expectation, emit explicit caveats/nonclaims, keep hard
exclusions closed, and fail closed without retaining unsupported query text.

The next implementation phase is:

```text
GENERIC-QUERY-TO-RELATION-PLANNING-01
```

## Roadmap Preserved

The boundary does not replace these later phases:

- `ANALYST-SOURCE-AUTHORITY-POSTURE-PACKET-01`
- `COMPONENT-MODEL-ROLE-ROUTING-MATRIX-01`
- `FAP-OUTPUT-INSPECTION-AND-RENDERING-CONTRACT-01`

Social/review evidence handling, broad product comparison/reliability questions,
source-authority modules, Scrutineer expansion, and Author/FAP rendering work are
post-boundary work.
