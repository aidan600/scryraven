# Quantitative Specialist Product Activation

Status: current
Authority: canonical:quantitative-specialist-product-activation
Default-read: no
Applies-to: ordinary source-bound calculator capability, transient numeric source catalogs, literal binding, numeric provenance, product registry/policy, claim alignment, and D-prime handoff
Does-not-authorize: search, acquisition, provider/model calls, estimates, arbitrary formulas, recursion, parallelism, direct admission, FAP, Author, or live validation
Verified-against-runtime: cb286ac91a0c7a24c364d5e992961c229c819eb4
Update-trigger: merged change to the ordinary quantitative Specialist capability, source catalogs, parser, product composition, or validator handoff

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

## Source Catalogs And Literal Binding

Repository code derives transient local source catalogs from ordinary role
inputs. Component Analyst receives a `component_evidence` alias with bounded
source posture, evidence/custody refs, lineage completeness, and a digest of
the bounded material. Cross-Component Analyst receives deterministic
`component_01`, `component_02`, and later aliases for current admitted
component claims. Each synthesis entry binds:

```text
nominated admitted component claim
-> exact literal occurrence in that claim
-> underlying current component evidence containing the same literal
```

This two-hop proof is mandatory. The retained proposal uses local aliases and
exact literal text only; it cannot carry component, node, graph, lease, URL,
field-path, source text, provider, prompt, response, search, retrieval, or
canonical authority material. Source material is reconstructed transiently
immediately before dispatch and is not retained in RunKernel state, scheduler
records, results, logs, or traces.

## Request, Parser, And Calculation Contract

The closed request schema contains request kind, calculation kind, a bounded
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
