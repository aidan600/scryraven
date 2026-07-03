# Source Authority Posture

Status: active contract for `ANALYST-SOURCE-AUTHORITY-POSTURE-PACKET-01`.

## Purpose

Source authority is an Analyst-owned, evidence-relative posture. The contract in
`core/source_authority_posture_packet.py` gives future planning and D-prime
relation work a stable vocabulary for source class, issuer/owner, document type,
primary/derivative posture, officialness/canonicality, directness, currentness,
scope match, claim specificity, conflict/qualification posture, recommended
source use, limitations, caveats, and Analyst rationale.

This is a schema/profile/contract phase. It is not an authority engine.

## Ownership

The Analyst owns first-pass source-authority interpretation.

Planner may later reference source-authority requirements, but Planner must not
invent source-authority policy.

Scrutineer audits Analyst posture. Scrutineer does not perform first-pass source
synthesis.

Evidence-class adapters may later feed Analyst posture. They do not bypass
Analyst, become source authority, or become Scrutineer.

## Not A Domain List

Source authority is not a domain allowlist, blocked-domain list, source-ranking
algorithm, authority score, numeric threshold, or shortcut from source class or
document type to recommended use. `recommended_source_use` is valid only as an
Analyst-declared posture with supporting fields and rationale.

Official/source-of-record examples may validate as `authority` only when the full
posture supports that recommendation. Source class alone is insufficient.

## Recommended Use

`authority` means the source may bear authority for the claim if the full
Analyst-declared posture supports that use.

`corroboration` means the source may support consistency but should not be
treated as the source of authority.

`context` means the source may help explain background but should not authorize
the answer component.

`directionality` means the source may indicate user experience, sentiment, or
lead direction, but not factual truth or authority.

`ignore` means the source should not be used for this answer component.

## Social And Review Evidence

Social/forum/review evidence is directionality or context at most until a future
adapter handles aggregation, representativeness, dissent, and reliability
posture. A single social/forum/review comment must not be laundered into
consensus, reliability evidence, or authority-bearing support.

The current packet encodes this as both a required nonclaim and a validation
rule. Social/forum/review source classes validate only as `directionality` or
`ignore`.

## Boundaries

Product correctness remains unclaimed.

This phase does not implement query-to-relation planning.

This phase does not wire source-authority packets into live dogfood, D-prime
review, Scrutineer, FAP, Author, or source-class adapters.

This phase does not add live/provider/model/fetch/read calls.

## Current Consumer Posture

The current supported-query boundary may point at this contract by phase id so a
future query-to-relation planning phase can reference Analyst-owned
source-authority posture without inventing policy. That pointer is metadata only;
the fixed-query boundary still does not consume source-authority posture packets
or claim source-authority support.
