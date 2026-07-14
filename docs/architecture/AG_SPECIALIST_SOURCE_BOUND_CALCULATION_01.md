# Quantitative Specialist Product Activation

Status: current
Authority: canonical:quantitative-specialist-product-activation
Default-read: no
Applies-to: ordinary source-bound calculator capability, model-visible proposal contract, transient numeric source catalogs, evidence-quality projection, literal binding, numeric provenance, product registry/policy, claim alignment, and D-prime handoff
Does-not-authorize: search, acquisition, provider/model calls, estimates, arbitrary formulas, recursion, parallelism, direct admission, FAP, Author, or live validation
Verified-against-runtime: 9e19d54b20036512509955e3176fb0386282796d
Update-trigger: merged change to the ordinary quantitative Specialist proposal contract, evidence bridge, source catalogs, parser, product composition, or validator handoff

Installed runtime class: quantitative-specialist-product-activation-s1

## Responsibility And Product Consumer

This document is the sole current owner of the installed quantitative
Specialist. The generic proposal, registry, scheduling, result, and validator
contracts belong to [Specialist Graph Substrate](SPECIALIST_GRAPH_SUBSTRATE.md).
Current installed-state scope belongs to
[ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md), and phase sequence belongs
to [Current Roadmap](../roadmap/CURRENT_ROADMAP.md).

The ordinary `python -m proplex` CLI and home-page UI compose one fixed product
registry and execution policy into their normal `RunDeps`. There is no public
toggle. Diagnostics and dry-run surfaces remain closed. Activation is limited
to `ordinary-bounded-multicomponent-factual-synthesis-v1`; nonqualifying and
single-component requests preserve their established ordinary behavior.

## Installed Capability

The one product descriptor is:

| Field | Installed value |
| --- | --- |
| Capability ID | `specialist.source_bound_calculation` |
| Version | `1.0.0` |
| Requirement | `source_bound_quantitative_calculation` |
| Input schema | `specialist.source_bound_calculation.request.v1` |
| Output schema | `specialist.source_bound_calculation.result.v1` |
| Executor | deterministic local adapter, no provider transport |

The product registry contains only that descriptor, and the fixed product
policy enables only that capability with a zero-or-one serial Specialist unit.
The generic registry, adapter interface, Scheduler V3 resolution, and unified
D-prime handoff are reused without a calculator-specific scheduler or driver
branch.

## Model-Visible Proposal Contract

Repository code owns one declarative proposal contract with schema version
`quantitative_specialist_proposal_contract.v1` and contract digest
`b69fead70bd52a48d833a54e925132c4a9b251be81760cda952aaadc70a873be`.
The same declarative facts build the model-visible contract and drive runtime
proposal/request validation: allowed, required, optional, fixed, and prohibited
fields; operand fields; all eight operator/role policies; numeric-literal and
generic request bounds; and noncommutative role semantics. Contract drift,
instance-digest drift, stale fixed values, extra fields, or unsupported roles
fail closed.

The fixed proposal facts are requirement
`source_bound_quantitative_calculation`, capability hint
`specialist.source_bound_calculation`, input schema
`specialist.source_bound_calculation.request.v1`, output schema
`specialist.source_bound_calculation.result.v1`, recursion depth `0`, and null
Specialist parent. Component Analyst receives the contract at the top level of
its ordinary input packet, bound to the exact component target and sole
`component_evidence` alias. It may return at most one sibling
`specialist_need_proposal` alongside the ordinary component fields.
Cross-Component Analyst receives the same contract at the top level, bound to
the rule that the target equal a `synthesis_key` proposed in the same artifact
and to the exact `component_01`, `component_02`, ... aliases in its source
catalog. It may return at most one top-level sibling proposal beside
`synthesis_proposals`, never nested inside a synthesis proposal.

The contract is present only at the two proposal-producing ordinary role
surfaces. Component D-prime receives the exact ordinary component input without
it; synthesis D-prime, selective Cross-Component Analyst, Scrutineer, and
nonqualifying paths do not receive it. Those exclusions preserve role and
product boundaries rather than creating another proposal authority.

## Source Catalogs And Literal Binding

Repository code derives transient local source catalogs from ordinary role
inputs. The ordinary evidence bridge treats the structured candidate record as
primary and passage metadata as an exact fallback for source class, source
tier, currentness, fact disposition, readability, conflict/contradiction, and
canonical three-letter currency. Missing facts remain `unknown`: an accepted
fact does not manufacture a clear conflict posture, graph admission does not
upgrade source quality, and a malformed currency value is not truncated into a
code. The bridge copies only those safe structured facts and the bounded
passage projection; it does not copy a complete candidate, provider payload,
full page, private artifact, raw prompt, or response.

Component Analyst receives a `component_evidence` alias with bounded source
posture, evidence/custody refs, lineage completeness, and a digest of the
bounded material. Cross-Component Analyst receives deterministic
`component_01`, `component_02`, and later aliases for current admitted
component claims. Its model catalog and the later execution catalog are built
from the same underlying component evidence and have identical nonmaterial
fields and `posture_digest`; only the execution catalog adds `source_material`.
The model catalog contains no bounded claim or evidence text. Each synthesis
entry binds:

```text
nominated admitted component claim
-> exact literal occurrence in that claim
-> underlying current component evidence containing the same literal
```

This two-hop proof is mandatory. Source quality is inherited from the underlying
component evidence; admission of a component claim cannot cleanse weak,
unknown, stale, conflicting, or incomplete source posture.

| Product posture | Required source facts | Calculator consequence |
| --- | --- | --- |
| `authoritative_current_clear` | Explicit acceptable currentness, independently strong canonical source class and source tier, explicitly clear conflict posture, and complete evidence/custody lineage. | Eligible for ordinary literal binding and calculation, subject to all other request and claim-alignment checks. |
| `contested_source_posture` | Lineage is complete, but currentness, class, tier, or conflict is weak, adverse, or unknown. | Spent result is contested; source quality is never upgraded by fact acceptance or graph admission. |
| `incomplete_lineage` | Evidence/custody identity is absent or does not match, regardless of other favorable fields. | Calculation is blocked for missing lineage. |

The retained proposal uses local aliases and exact literal text only; it cannot
carry component, node, graph, lease, URL, field-path, source text, provider,
prompt, response, search, retrieval, or canonical authority material. Full
source material is reconstructed only in driver-local adapter execution scope.
The proposal contract, full source catalogs, source material, and complete
candidate records are absent from canonical RunKernel projections, scheduler
ready-work/leases/batches/actions, Specialist work and result records, graphs,
observations, logs, and traces. Retained input refs may carry only bounded
identity and source-posture facts needed for validation.

## Request, Parser, And Calculation Contract

The closed request schema, owned by the same declarative proposal-contract
facts consumed by runtime validation, contains request kind, calculation kind, a bounded
formula label, expected output unit and precision posture, two to eight
operands, one claim binding, and bounded assumptions/caveats. Each operand
uses a local key, source alias, exact source numeric literal, operator-specific
role, and optional occurrence/pair key. Unknown fields fail closed.

Supported deterministic operators and roles are:

| Operator | Required roles |
| --- | --- |
| `sum` | two or more `term` operands |
| `difference` | one `minuend`, one `subtrahend` |
| `product` | two or more `factor` operands |
| `ratio` | one `numerator`, one `denominator` |
| `percentage` | one `numerator`, one `denominator` |
| `percentage_point_difference` | one `minuend`, one `subtrahend` |
| `simple_rate` | one `numerator`, one `denominator` |
| `weighted_average` | at least two complete `value`/`weight` pairs |

Parser `source_bound_numeric_literal_parser.v1` uses `Decimal` and a closed
grammar for sign, dot-decimal or canonical comma grouping, an optional single
scale word, explicit percent or bounded units, and currency code. A currency
symbol is accepted only with an exact structured catalog currency fact.
Locale ambiguity, expressions, words-as-numbers, duplicated scales,
non-finite values, and arbitrary code fail closed. Units and precision are
derived deterministically; missing or incompatible units, denominator zero,
unsupported formulas, weak/stale/conflicting sources, missing lineage, and
literal-binding ambiguity block or contest the result.

The product adapter calls the pure `evaluate_source_bound_calculation` seam.
That seam owns normalized deterministic arithmetic facts shared with the old
record builder. The legacy RunKernel calculation reducer remains compatibility
support only and is not called by ordinary S1 execution.

## Claim Alignment And Authority

A completed calculation is useful only when the nominated proposed-result
literal occurs exactly in the nominated claim and reparses to the same
`Decimal`, derived unit, and compatible precision. The result records
`source_explicit` input provenance, `derived_deterministic` output provenance,
operator/formula/parser facts, assumptions, caveats, blockers, and exact
lineage. Non-exact alignment is contested and spent; execution success alone
is not semantic support.

Component or synthesis D-prime receives the result only through the generic
`specialist_need_handoff` and must validate its use against the ordinary
nominated claim and evidence or admitted-input refs. The Specialist cannot
validate or admit its own result and has no ComponentCoverage, Sufficiency,
FinalAnswerPacket, Author, citation, source-obligation, search, acquisition, or
contract-mutation authority.

## Scheduling And Lifecycle

The separate Specialist budget remains zero or one unit, serial and
nonrecursive. Canonical ready-work order gives an eligible component
calculation priority before a later synthesis calculation. Spending the unit
at component scope therefore makes later optional synthesis work unavailable
and later required synthesis work safely blocks through the existing typed
lifecycle. Optional failure remains visible and nonblocking; required failure
or exhaustion reaches the safe non-Author terminal after active work drains.

## Unsupported And Nonproofs

S1 does not support estimates, number invention, arbitrary formula strings,
unit or currency conversion, source acquisition, social-source analysis, more
than one Specialist unit, recursion, parallel Specialist execution, or global
capability arbitration. It does not prove live correctness, arbitrary-query
coverage, broad quantitative reasoning quality, answer quality, or production
stability.

The next roadmap checkpoint is separately licensed quantitative live
validation. That checkpoint must not be inferred from these offline product-
path proofs or from capability availability.
