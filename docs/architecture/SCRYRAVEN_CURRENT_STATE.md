# ScryRaven Current State

Status: current
Authority: canonical:current-installed-state
Default-read: yes
Applies-to: current ordinary product implementation and explicit nonproofs
Does-not-authorize: live calls, arbitrary-query claims, roadmap execution, or closed-surface changes
Runtime-audit-through: d3df96994f72b371f6a2451677784376ac3f7cb9
Update-trigger: merged change to installed product behavior, supported boundaries, evidence classification, or explicit nonproofs

## Source Of Truth

This document is the sole repository owner of temporal installed-state truth.
Current code and focused tests remain executable authority. When they disagree
with this summary, treat this document as stale and repair it rather than
inventing a compatibility interpretation.

The roadmap owns sequence. Concern-specific architecture documents own durable
contracts. Historical phase documents and PR chronology are provenance only.

## Supported Ordinary Surface

The supported ordinary executable surface is the backend CLI through:

```text
python -m scryraven
python -m proplex   # compatibility surface
```

The legacy Streamlit shell and saved-thread Streamlit follow-up are not current
ordinary product paths. Retained `ui/` source is reference and migration
material. No replacement UI framework is selected.

The installed bounded multi-component route is limited to the named query class
`ordinary-bounded-multicomponent-factual-synthesis-v1`. Nothing in this document
claims arbitrary-query decomposition or broad product reliability.

## Installed Ordinary Authority Path

```text
request
-> SearchOS acquisition and lawful handoff
-> Component Analyst case
-> RunKernel exact binding and admission
-> ComponentCoverage
-> Sufficiency whole-run readiness
-> FinalAnswerPacket packaging
-> Author
-> mechanical citation/output finalization
-> RunOutcome
```

### SearchOS

SearchOS owns semantic planning, provider-neutral acquisition, DISCOVER, READ,
navigation/recovery, custody, and lawful handoff. It does not decide claim
support, component admission, whole-run readiness, or final prose.

Provider-returned material remains candidate or source material until the
installed custody and admission owners accept it. Candidate presence, citation
presence, and telemetry do not create support.

### Component Analyst And RunKernel

Component Analyst owns what one component's bounded evidence means: support,
applicability, claim or lawful no-claim posture, caveats, nonclaims,
contradictions, uncertainty, missing premise, calculation need, and self-audit.

RunKernel owns canonical mechanics: exact request/run/action identity,
contract/component/evidence refs, digests and revisions, stale/foreign rejection,
replay/exactly-once behavior, graph legality, Specialist binding, and canonical
admission. It may reject malformed or impossible state; it does not reinterpret
natural-language support.

### ComponentCoverage And Sufficiency

ComponentCoverage records whether an individual requested component is ready
from current admitted semantic state and lawful evidence custody.

Sufficiency then computes whole-run readiness over canonical facts. It asks
whether all required answer targets and source obligations are fulfilled,
whether blocking conflicts or unknowns remain, and whether direct, caveated,
partial, insufficient, or blocked output is authorized. It does not reread
source prose or second-guess the Analyst.

The ordinary configuration uses the deterministic Sufficiency path. A legacy
optional smart-model adapter exists behind an explicit disabled-by-default
configuration flag and is not required for ordinary readiness.

### FinalAnswerPacket And Author

FinalAnswerPacket is semantically stupid and mechanically strict. It packages
the admitted claims, Analyst context, caveats/nonclaims, evidence and citation
lineage, and useful bounded source context that Sufficiency authorized.

FAP may reject wrong, stale, foreign, malformed, or missing mechanical lineage.
It does not decide from prose which numbers matter, whether an integer is a
version or rank, whether a token is a unit, whether two propositions mean the
same thing, or which supplied context Author must mention.

Direct-source numbers are ordinary admitted claim content. They do not require a
separate `direct_source_numeric` PRODUCT authority row. Genuinely derived or
calculated results still require complete exact `specialist_derived_numeric`
authority.

Author is the final semantic actor. It writes naturally from the bounded world
FAP supplies and may improve presentation but not truth posture. After Author,
ordinary PRODUCT code performs mechanics only: citation-token resolution,
foreign-citation rejection, private/control-material protection, required text,
envelope/serialization, encoding, and size checks. There is no post-Author
semantic gate, semantic repair loop, or Author retry/revision loop.

## Evidence, Source Obligations, And Currentness

EvidenceLedger is the canonical source-custody and source-obligation owner.
Source-class observability and telemetry are helper/diagnostic only and cannot
mint FACT authority, stronger-obligation eligibility, canonical links,
requirement satisfaction, citation eligibility, or FAP readiness.

One source may satisfy multiple obligations when it satisfies each predicate.
Distinct owned obligations remain distinct; same source class alone does not
reconcile them.

Currentness means validity for the proposition's temporal, version,
jurisdiction, or population scope. It is not simple publication recency. An old
historical source may remain valid for a historical claim; official or canonical
material is not automatically current for every proposition.

## N=1 And Multi-Component Status

Ordinary N=1 uses one Component Analyst case, direct RunKernel admission,
ComponentCoverage, Sufficiency, FAP, and Author. It does not schedule Cross,
component D-prime, synthesis D-prime, or Specialist unless differentiated work
actually requires them.

For genuine N>=2 work, the bounded component graph, Cross-Component Analyst,
and synthesis path are installed. The ordinary executable path still retains a
separate synthesis D-prime model call before synthesis admission. That retained
call is installed behavior, not selected permanent architecture. Component
D-prime has no ordinary component producer or consumer.

The deterministic source-bound Specialist is installed for bounded calculations
and conversions that create a new result. Source-stated literals remain ordinary
direct evidence and do not invoke Specialist merely because they contain digits.

## Bounded Q1 Product Evidence

A bounded convergence campaign used the official Python `math.isclose()`
defaults query. Run 04 at branch head
`addf604885ada57d97671734838b41d25971cc36` produced a correct supported cited
answer and traversed:

```text
SearchOS -> READ -> Component Analyst -> RunKernel admission
-> ComponentCoverage -> Sufficiency -> FAP -> Author -> completed RunOutcome
```

The answer cited `docs.python.org`. The run used one Component Analyst and one
Author, with no required component D-prime. Four of five licensed PRODUCT runs
were used; run 05 remained unused.

The final PR #601 correction then removed FAP's direct-source prose numeric gate
and preserved the separation between the 2,000-character digest-verified
authority material and the independently capped 600-character Author
presentation excerpt. That correction was verified offline and merged as
`d3df96994f72b371f6a2451677784376ac3f7cb9`; no additional live Q1 run was made
on the final merged SHA.

This is representative N=1 PRODUCT evidence, not a claim of arbitrary-query
reliability, repeatability, provider superiority, or broad answer quality.

## Queued Non-Blocking Observations

These observations do not invalidate the successful Q1 result and are not the
current strategic gate:

```text
QF-01: supported cited success also showed a low-substance failure_card
QF-02: the successful citation selected Python 3.8 documentation
QF-03: full-anchor match count was 0 while partial-anchor match was 1
```

Investigate them later only if they recur as product-quality blockers.

## Explicit Nonproofs

Current installed state does not prove:

- arbitrary-query planning, retrieval, or answer correctness;
- broad provider, search, READ, or recovery reliability;
- live multi-component synthesis quality;
- general currentness classification quality;
- broad Specialist or quantitative reasoning quality;
- citation selection or rendering quality beyond the bounded observation;
- a current conversation, saved-thread, or UI product; or
- product stability across repeated live runs.

Live calls remain separately licensed. Private prompts, model responses,
provider/search/READ payloads, credentials, logs, database rows, caches, and
full traces remain outside repository documentation and ordinary review
surfaces.
