# FinalAnswerPacket / Author Boundary

Status: current
Authority: canonical:fap-author-boundary
Default-read: no
Applies-to: ordinary FinalAnswerPacket packaging, Author rendering, and blocked FAP terminal behavior
Does-not-authorize: new claims, evidence interpretation, synthesis creation, citation upgrade, or Author execution when FAP is blocked
Verified-against-runtime: d3df96994f72b371f6a2451677784376ac3f7cb9
Update-trigger: merged change to FAP packaging, Author input, rendering, or blocked terminal behavior

## Responsibility

This document owns the installed boundary among Sufficiency,
FinalAnswerPacket (FAP), Author, mechanical finalization, and blocked terminal
behavior.

```text
RunKernel-admitted state
-> ComponentCoverage
-> Sufficiency whole-run readiness
-> FinalAnswerPacket packaging
-> Author rendering
-> mechanical citation/output finalization
-> RunOutcome
```

Sufficiency computes whether the admitted run is ready, caveated, partial,
insufficient, or blocked. FAP does not repeat that decision. Graph or component
admission alone is not whole-answer readiness.

FAP is the final semantic-authority boundary because it is the last structured
container defining what Author may use. It is not a semantic adjudicator.
Author is the final semantic actor.

## Semantically Stupid, Mechanically Strict

FAP packages the authorized world. It may enforce mechanical integrity such as:

```text
current component/revision/digest
exact Analyst and semantic-observation refs
exact ComponentCoverage refs
exact content/evidence/citation lineage
stale or foreign rejection
required Specialist result/handoff authority
packet shape, privacy, and boundedness
```

FAP must not decide from prose:

```text
which number matters
whether an integer is a version, section, rank, or count
whether a token is a unit
whether an ordinal is substantive
whether two propositions mean the same thing
whether source prose semantically supports admitted claim prose
which supplied context Author must mention
```

Those meaning-bearing judgments belong upstream to Component Analyst, Cross when
applicable, and RunKernel admission of their exact current output.

## Direct-Source Packaging

For an admitted direct-source component, FAP packages:

- the admitted claim and its exact current claim ref;
- Analyst context, caveats, nonclaims, and uncertainty;
- semantic-observation and ComponentCoverage refs;
- exact evidence and citation lineage; and
- useful bounded source context.

Direct-source numbers are ordinary admitted claim content. FAP does not create or
require a separate `direct_source_numeric` PRODUCT authority row merely because
claim text contains digits. It does not parse the claim to decide which digits
are meaningful or compare claim-text numeric signatures against source prose.

A bad upstream semantic judgment is not rescued by a weaker deterministic
reader inside FAP. FAP still rejects wrong, stale, foreign, missing, or
mechanically inconsistent lineage.

## Bounded Evidence Context

The installed semantic-materialization path retains up to 2,000 characters of
digest-verified packet-owned authority material. Author presentation of that
material is independently capped at 600 characters.

These surfaces serve different purposes:

```text
authority material = mechanical provenance and useful bounded context
Author presentation = concise model-visible evidence context
```

Extra context is a resource, not an output checklist. Its presence does not
create new claims, authorize every visible fact, or require Author to mention
every sentence or numeric literal.

## Derived Quantitative Work

A source-stated literal remains ordinary direct-source evidence.

A genuinely new calculated, converted, aggregated, rescaled, or otherwise
derived result requires complete exact Specialist authority before Author may
use it. The installed hard path is:

```text
semantic owner identifies calculation need
-> code validates and binds the request
-> Specialist executes the bounded calculation
-> semantic owner consumes the result
-> RunKernel admits exact result lineage
-> FAP verifies specialist_derived_numeric authority
-> Author may render the result
```

Missing, stale, mismatched, unconsumed, or incomplete Specialist authority
blocks the derived result. Specialist execution success alone is not semantic
support.

The retained prose quantitative parser and evaluator may report diagnostics in
validation contexts. They have no PRODUCT authority over FAP readiness, Author
output, citations, canonical state, RunOutcome, or retry behavior.

## Inferred And Multi-Component Packaging

Sufficiency may authorize current direct component entries and, for genuine
N>=2 work, admitted synthesis entries. FAP packages only the exact current
entries and lineage Sufficiency authorizes.

An admitted inference remains labeled as inference. FAP must not copy it into a
direct-source entry, invent missing premises, flatten caveats, or upgrade its
support posture.

The currently installed bounded N>=2 path retains synthesis D-prime before
synthesis admission. That installed role does not give D-prime direct FAP or
Author authority; FAP consumes only RunKernel-admitted current state.

## Author Contract

Author is a constrained communication layer over FAP-supplied claims, context,
citations, caveats, and Specialist-derived authority.

```text
Author may improve presentation.
Author may not improve truth posture.
```

Author may organize the response, choose clear wording, preserve caveats,
explain admitted synthesis, and restate numbers from admitted direct-source
claims and packet-owned evidence context.

Author must not search, add evidence, invent missing context, repair support,
resolve conflicts, upgrade inferred or contested claims, satisfy missing source
obligations, or create new calculations or conversions without exact Specialist
authority.

## Post-Author Mechanics

After Author, ordinary PRODUCT code may enforce only genuinely mechanical
requirements, including:

- nonempty required answer presence;
- citation placeholder resolution and authorized citation identity;
- foreign-citation rejection;
- private/control-material protection;
- serialization, envelope, encoding, and size limits.

Post-Author code does not reinterpret free-form prose for semantic acceptance.
There is no deterministic prose theorem prover, second semantic model, Author
retry/revision loop, semantic repair loop, or second FAP.

A retained evaluator may disagree with Author prose in validation. That
observation cannot change PRODUCT success or output.

## Blocked FAP Terminal

When FAP mechanical readiness is blocked, Author does not run. No Author input
or Author model call is created.

The ordinary product may return a deterministic sanitized non-Author
`RunOutcome` for an expected blocked-readiness case. That summary may contain
safe reason codes, counts, refs, and posture, but never prompts, raw model or
provider material, raw evidence, credentials, private logs, database rows, or
full traces.

Malformed packets, broken identity, invariant failures, infrastructure failures,
and unrelated exceptions remain errors; they must not be relabeled as ordinary
insufficiency.

## Nonproofs

This boundary does not prove arbitrary-query readiness, semantic correctness,
retrieval quality, citation selection quality, broad Author quality, or product
reliability. It defines who may decide what and prevents FAP or post-Author code
from becoming another semantic actor.
