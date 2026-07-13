Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I3F_PROVIDER_NEUTRAL_OFFICIAL_CURRENT_QUERY_SHAPING).

# AG-96I3F Provider-neutral Official/current Query Shaping

## Status

AG-96I3F adds an offline query-shaping diagnostic layer for official/current
candidate acquisition. It prepares bounded search query variants for later
brokered discovery runs without calling providers, adding source domains,
fetching pages, reading private data, or changing product query generation.

The implementation is:

```text
core.followup_official_current_query_shaping
```

The helper emits sanitized packets only. Query variants are diagnostic inputs
for a future authorized discovery run; they are not evidence, citations, or
final-answer authority.

## Why The Human-style IRS Query Was Vulnerable

After AG-96I3E merged, one-call brokered diagnostics were run manually against
Brave, Tavily, and Linkup using the same unconstrained user-style query:

```text
What is the current IRS standard mileage rate for business use of a car in 2026,
and what official source supports it? Keep the answer concise.
```

The top five results from those surfaces did not contain a canonical
official/current IRS candidate. Tavily surfaced a county-hosted PDF/mirror-like
result, while the other result sets were secondary/accountant/blog-style
bridges. AG-96I3D correctly diagnosed that the provider result sets lacked an
official/current candidate; the failure was not the diagnostic layer.

The weak point was query shape. The query asked the search engine for the answer,
which is attractive to SEO explainers and summaries. Official/current discovery
needs to ask for the artifact that would contain the answer.

## Query Shaping Is Not A Hard Corridor

Query shaping adds source-class and artifact-class language such as:

- `official`
- `current`
- `notice`
- `announcement`
- `newsroom`
- `bulletin`
- `rule`
- `guidance`
- `form instructions`
- `fee schedule`
- `filing fee`
- `final rule`
- `release`
- `table`

These terms change the shape of the provider-neutral query. They do not hand the
provider a source-specific corridor.

The following remain invalid for first discovery proof:

```text
includeDomains=["irs.gov"]
site:irs.gov
hardcoded URL or slug resolvers
provider-specific syntax
source-specific branches such as "if this domain, do that"
```

`includeDomains=["irs.gov"]` proves only that a provider can search inside a
domain already supplied by the runtime. It does not prove that the provider can
discover the official/current source from a neutral authorized query. First
discovery remains:

```text
job first -> provider second -> diagnostics always
```

## Scout Versus Official/current Shaping

Scout/disambiguation and official/current shaping answer different questions.

Scout asks:

```text
What might the user mean?
```

Official/current shaping asks:

```text
Given a scoped target, what official/current artifact would contain the answer?
```

For ambiguous phrases, the helper produces a hypothesis packet with multiple
candidate interpretations and keeps:

```text
canonical_subject_status=unresolved
```

LLM prior knowledge or local heuristics may seed possible interpretations, such
as recognizing that `PoE` could mean Path of Exile, Power over Ethernet, or
another phrase. That does not promote a canonical subject. Promotion requires
evidence or explicit caller resolution.

When the caller explicitly supplies a resolved canonical subject, the helper can
skip scout and shape official/current artifact queries for that subject.

## Packet Boundary

The AG-96I3F packet includes:

- original authorized query;
- acquisition mode;
- provider job kind;
- query shape mode;
- bounded query variants;
- shaping reasons;
- preserved target terms;
- artifact terms used;
- prohibited-constraint posture;
- domain-constraint status;
- canonical-subject status;
- live/provider/fetch/model/Author flags fixed to false;
- raw/private redaction posture.

The helper may preserve target facts, years, entities, document type, and user
intent already present in the authorized query. It may use explicit
bridge-hint-derived terms only when the caller passes them as such. It must not
invent answer values, use live result text to mutate query text, or add source
domains in `discovery_unconstrained` mode.

## Example Offline Shapes

For a scoped query like:

```text
What is the current IRS standard mileage rate for business use of a car in 2026?
```

Allowed artifact-oriented variants include shapes like:

```text
IRS 2026 standard mileage rates business use car official current
IRS 2026 standard mileage rates business use car notice announcement
IRS 2026 standard mileage rates business use car newsroom table
```

For an ambiguous query like:

```text
latest PoE patch
```

The helper emits scout hypotheses rather than a resolved canonical subject. A
later caller can resolve the subject explicitly, for example to `Path of Exile
latest patch notes`, and then ask for official/current artifact shaping.

## Preparation For Later Brokered Live Tests

AG-96I3F does not run brokered validation. A later approved phase can feed one
or more shaped variants into the AG-96I3E brokered runner and compare the same
AG-96I3D result-set diagnostics:

- whether official/current candidates were visible;
- candidate rank and selected domain;
- whether bridge-only posture remained;
- whether any domain constraint was absent, invalid, or earned by a separate
  authority decision.

The shaped query still does not create final evidence. Final evidence requires a
later separately authorized fetch/read/admission path through the existing
authority chain:

```text
RunAuthorityContract
-> EvidenceLedger
-> SufficiencyJudgment
-> FinalAnswerPacket
-> AuthorExecutor
```

No live validation was run for AG-96I3F.
