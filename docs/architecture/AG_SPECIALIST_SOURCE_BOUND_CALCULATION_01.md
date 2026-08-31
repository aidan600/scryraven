# Quantitative Specialist Product Activation

Status: current
Authority: canonical:quantitative-specialist-product-activation
Default-read: no
Applies-to: ordinary source-bound calculator capability, model-visible proposal contract, transient numeric source catalogs, evidence-quality projection, literal binding, numeric provenance, product registry/policy, claim alignment, and D-prime handoff
Does-not-authorize: search, acquisition, provider/model calls, estimates, arbitrary formulas, recursion, parallelism, direct admission, FAP, Author, or live validation
Verified-against-runtime: 72251c126770e41a9b52105d860154d1cfef811b
Update-trigger: merged change to the ordinary quantitative Specialist proposal contract, evidence bridge, source catalogs, parser, product composition, or validator handoff

Installed runtime class: quantitative-specialist-product-activation-s1

## Responsibility And Product Consumer

This document is the sole current owner of the installed quantitative
Specialist. The generic proposal, registry, scheduling, result, and validator
contracts belong to [Specialist Graph Substrate](SPECIALIST_GRAPH_SUBSTRATE.md).
Current installed-state scope belongs to
[ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md), and phase sequence belongs
to [Current Roadmap](../roadmap/CURRENT_ROADMAP.md). Final accepted-prose
numeric containment belongs to
[Quantitative Finalization Containment](AG_S1_QUANTITATIVE_FINALIZATION_CONTAINMENT_01.md).

The ordinary public CLI composes one fixed product registry and execution policy
into its normal `RunDeps`. The former home-page UI consumer belongs to the
legacy Streamlit shell and is not ordinary product consumption. There is no
public toggle. Diagnostics and dry-run surfaces remain closed. Activation is
limited to `ordinary-bounded-multicomponent-factual-synthesis-v1`;
nonqualifying and single-component requests preserve their established ordinary
behavior.

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
`quantitative_specialist_proposal_contract.v2` and contract digest
`294bc7e9b7f658c07e02ee05f7beddbfffc96cf08733eb1fae4e98485e813900`.
Each model-produced proposal instance must separately carry generic instance
schema `specialist_need_proposal_v1`; the two schema versions are not
interchangeable.
The same declarative facts build the model-visible contract and drive runtime
proposal/request validation: allowed, required, optional, fixed, and prohibited
fields; operand fields; all eight operator/role policies; numeric-literal and
generic request bounds; and noncommutative role semantics. Contract drift,
instance-digest drift, stale fixed values, extra fields, or unsupported roles
fail closed.

The exact proposal field sets are:

- allowed: `schema_version`, `local_need_id`, `capability_requirement`,
  `candidate_capability_hint`, `bounded_question`, `target`, `posture`,
  `input_schema_ref`, `expected_output_schema_ref`, `input_artifact_refs`,
  `assumptions`, `caveats`, `nonclaims`, `advisory_budget_posture`,
  `recursion_depth`, `specialist_parent_ref`, `capability_request`;
- required: `schema_version`, `local_need_id`, `capability_requirement`,
  `candidate_capability_hint`, `bounded_question`, `target`, `posture`,
  `input_schema_ref`, `expected_output_schema_ref`, `recursion_depth`,
  `specialist_parent_ref`, `capability_request`;
- optional: `input_artifact_refs`, `assumptions`, `caveats`, `nonclaims`,
  `advisory_budget_posture`.

The fixed proposal facts are schema `specialist_need_proposal_v1`, requirement
`source_bound_quantitative_calculation`, capability hint
`specialist.source_bound_calculation`, input schema
`specialist.source_bound_calculation.request.v1`, output schema
`specialist.source_bound_calculation.result.v1`, recursion depth `0`, and null
Specialist parent. For S1 the capability hint is required and exact, not
advisory. Component Analyst receives the contract at the top level of
its ordinary input packet, bound to the exact component target and the supplied
ordered `component_evidence_set` local aliases (`component_evidence_01`,
`component_evidence_02`, ...). It may return at most one sibling
`specialist_need_proposal` alongside the ordinary component fields.
Cross-Component Analyst receives the same contract at the top level, bound to
the rule that the target equal a `synthesis_key` proposed in the same artifact
and to the exact `component_01`, `component_02`, ... aliases in its source
catalog. It may return at most one top-level sibling proposal beside
`synthesis_proposals`, never nested inside a synthesis proposal.

The contract is present only at the two proposal-producing ordinary role
surfaces. A bounded Component Analyst-resume continuation binds an exact
Specialist result back to its originating Analyst case; it is not a third
proposal surface. Component Analyst is the sole ordinary component validator
and consumer. Synthesis D-prime, selective Cross-Component Analyst,
Scrutineer, and nonqualifying paths do not receive the contract. Those
exclusions preserve role and product boundaries rather than creating another
proposal authority.

## Exact Proposal Admission

The exact candidate is preserved transiently from the parsed role response and
is not read back from a normalized semantic artifact. Before RunKernel may
create work, the ordinary product path independently reproduces the current
role input from runtime authority, checks the completed role artifact and its
input digest, validates the current contract schema, contract digest, and exact
instance digest, and then applies the executable S1 proposal and request
validators.

For a component proposal, the exact target must equal the current accepted
component, the contract target, and the current Component Analyst input; every
operand alias must be one supplied `component_evidence_01`,
`component_evidence_02`, ... local alias. For a synthesis proposal, the key
must be unique in the same Cross-Component Analyst artifact, the graph node must
have been created from that artifact at the current revision, and every operand
alias must be in that exact artifact's current `component_01`, `component_02`,
... catalog. Missing, stale, extra, cross-artifact, target-mismatched, or unknown
aliases fail before work creation.

Capability-request validation now occurs at admission as well as at execution.
Admission validates request/operator kind, exact request/operand/claim-binding
field sets, bounds, operand count and roles, local-key uniqueness, occurrence
and pair-key rules, and forbidden formula/code/authority/URL/path/provider/
search/prompt/response material. Execution still exclusively owns numeric
parsing, literal occurrence in reconstructed source material, source-quality
sufficiency, two-hop evidence matching, calculation, unit derivation, and
claim-value alignment.

An invalid candidate produces only a bounded RunKernel rejection receipt and no
accepted proposal, Specialist-ready work, budget spend, lease, batch, dispatch,
adapter call, result, handoff, or Specialist-derived downstream authority. A
required invalid proposal blocks its dependent claim and cannot reach FAP or
Author as supported. An optional invalid proposal contributes zero authority;
independently supported ordinary claims may continue, while a calculation-
dependent claim still fails ordinary D-prime/readiness without the missing
result. Valid component and synthesis proposals retain the existing one-unit,
serial execution and D-prime handoff behavior.

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

Component Analyst receives an exact bounded `component_evidence_set` whose
members have safe packet-local aliases and bounded source posture. It receives
no canonical evidence/custody refs, lineage identities, or material digests.
Its initial and resume packets do not contain a `quantitative_source_catalog`;
after an accepted component proposal, Specialist dispatch reconstructs the
material catalog from that exact current evidence set, with one source-local
key per member.
Cross-Component Analyst receives deterministic `component_01`,
`component_02`, and later aliases for current admitted component claims. Its
model catalog and the later execution catalog are built from the same underlying
component evidence and have identical nonmaterial fields and `posture_digest`;
only the execution catalog adds `source_material`. The model catalog contains
no bounded claim or evidence text. Each synthesis entry binds:

```text
nominated admitted component claim
-> exact literal occurrence in that claim
-> underlying current component evidence containing the same literal
```

This two-hop proof is mandatory. Source quality is inherited from the underlying
component evidence; admission of a component claim cannot cleanse weak,
unknown, stale, conflicting, or incomplete source posture.

## Exact Cross Input Reproof

Cross input reproof is unconditional before a Cross-Component Analyst artifact
can create or reprove a ComponentWorkGraph. The ordinary caller may supply the
exact transient Cross packet while it exists. RunKernel instead independently
reconstructs the complete packet from the current scheduler-owned component
Analyst packets and checks those packets against the existing initialization or
recovery authority digest. The retained artifact `input_packet_digest` must
equal the digest of that exact packet.

Missing, empty, malformed, incomplete, cross-run, stale-component, or
digest-inconsistent reconstruction authority fails closed before graph
reduction. There is no structural-only fallback and no caller assertion can
substitute for reproduction. A temporary `deepcopy` function argument is
allowed; no component packet, transient Cross packet, proposal contract,
catalog, or source material is newly retained or exported.

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

The installed bounded result contract emits its canonical unit as
`bounded_result["result_unit"]`. Finalization may accept the legacy `unit` field
only when `result_unit` is absent and the legacy value is nonempty and
normalizable. When both are present, normalized agreement retains
`result_unit` as canonical and records compatibility agreement; disagreement
fails closed. Compatibility does not change the installed adapter contract.

Component or synthesis D-prime receives the result only through the generic
`specialist_need_handoff` and must validate its use against the ordinary
nominated claim and evidence or admitted-input refs. The Specialist cannot
validate or admit its own result and has no ComponentCoverage, Sufficiency,
FinalAnswerPacket, Author, citation, source-obligation, search, acquisition, or
contract-mutation authority.

When that exact claim is supported and admitted, the ordinary component or
synthesis path carries a bounded Specialist authority ref, applicable D-prime
ref, and D-prime consumption ref into FAP. Finalization may classify only the
exact claim whose claim-material digest contains the matching result literal as
`specialist_derived_numeric`; the claim's complete literal signature is then
validated atomically. Execution success, value equality, an unused result, or a
valid result attached to a different proposition cannot create rendering
authority.

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

The current strategic decision gate is owned exclusively by
`docs/roadmap/CURRENT_ROADMAP.md`. Capability availability and these offline
product-path proofs do not authorize live validation, do not select work, and do
not establish live correctness.
